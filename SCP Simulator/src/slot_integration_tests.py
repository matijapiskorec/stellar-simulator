import unittest
import os
import re
import pandas as pd
import numpy as np

# Import components from your simulator.
from src.Simulator import Simulator
from src.Network import Network
from src.Mempool import Mempool
from src.Globals import Globals


class DummyEvent:
    def __init__(self, name):
        self.name = name
        self.simulation_params = None


class TestFinalizedStateIntegrity(unittest.TestCase):
    def setUp(self):
        self.sim_duration = 100.0

        # Create the simulator with desired number of nodes.
        self.simulator = Simulator(verbosity=5, n_nodes=60)
        self.simulator._nodes = Network.generate_nodes(n_nodes=self.simulator.n_nodes, topology='ER-SINGLEQUORUMSET')

        self.shared_mempool = Mempool()
        for node in self.simulator._nodes:
            node.attach_mempool(self.shared_mempool)
        self.simulator._mempool = self.shared_mempool  # So that simulator events (like mine) can use it.

        Globals.simulation_time = 0.0

        self.simulator._max_simulation_time = self.sim_duration

    def tearDown(self):
        ledger_log = "ledger_logs.txt"
        if os.path.exists(ledger_log):
            os.remove(ledger_log)
        if os.path.exists(self.shared_mempool.log_path):
            os.remove(self.shared_mempool.log_path)

    def collect_finalized_tx_ids(self, node):
        """
        Given a node, iterate over its ledger slots and build a set
        of all finalized transaction hashes.
        """
        finalized_tx_ids = set()
        for slot_data in node.ledger.slots.values():
            finalized_value = slot_data['value']
            for tx in finalized_value.transactions:
                finalized_tx_ids.add(tx.hash)
        return finalized_tx_ids

    def check_state_for_finalized_txs(self, node, finalized_tx_ids):
        """
        For the given node, check that none of the transactions present
        in key state dictionaries (mempool, nomination_state, balloting_state, commit_ballot_state)
        contain any transaction whose hash is in finalized_tx_ids.
        """
        for tx in node.mempool.transactions:
            self.assertNotIn(tx.hash, finalized_tx_ids,
                             f"Node {node.name} mempool contains a finalized transaction {tx}.")

        # Check nomination state (voted, accepted, confirmed).
        for state in ['voted', 'accepted', 'confirmed']:
            for value in node.nomination_state.get(state, []):
                for tx in value.transactions:
                    self.assertNotIn(tx.hash, finalized_tx_ids,
                                     f"Node {node.name} nomination state '{state}' contains a finalized transaction {tx}.")

        # Check prepare (balloting_state) for all keys.
        for state in ['voted', 'accepted', 'confirmed', 'aborted']:
            for ballot in node.balloting_state.get(state, {}).values():
                for tx in ballot.value.transactions:
                    self.assertNotIn(tx.hash, finalized_tx_ids,
                                     f"Node {node.name} balloting_state '{state}' contains a finalized transaction {tx}.")

        # Check commit_ballot_state
        for state in ['voted', 'accepted', 'confirmed']:
            for ballot in node.commit_ballot_state.get(state, {}).values():
                for tx in ballot.value.transactions:
                    self.assertNotIn(tx.hash, finalized_tx_ids,
                                     f"Node {node.name} commit_ballot_state '{state}' contains a finalized transaction {tx}.")

    def test_state_integrity_after_finalization(self):
        """
        Run the simulator for an extended time and then verify that for each node,
        none of the internal state dictionaries (mempool, nomination state, balloting_state,
        commit_ballot_state) contain any transaction that has been finalized in any slot.
        """
        # Run the simulation.
        self.simulator.run()

        # For each node, collect the finalized transaction IDs from its ledger.
        for node in self.simulator._nodes:
            finalized_tx_ids = self.collect_finalized_tx_ids(node)
            print(f"Node {node.name}: Finalized transactions: {finalized_tx_ids}")

            # Now check each node's state.
            self.check_state_for_finalized_txs(node, finalized_tx_ids)

    def test_slot_progression(self):
        """
        After simulation, ensure that the number of finalized slots (from logs)
        is greater than some expected threshold, e.g., 7.
        This confirms that the externalization phase is progressing.
        """
        self.simulator.run()
        log_file = "ledger_logs.txt"
        df = self._process_ledger_logs(log_file)
        unique_slots = df['Slot'].nunique()
        print(f"Unique slots finalized: {unique_slots}")
        self.assertGreater(unique_slots, 7, "Too few slots finalized according to the log.")

    def _process_ledger_logs(self, file_path):

        def get_transaction_count(line):
            # Look for text within square brackets after 'transactions = '
            pattern = r"transactions\s*=\s*\[(.*?)\]"
            match = re.search(pattern, line)
            if match:
                txs_text = match.group(1)
                tx_ids = set(re.findall(r"Transaction\s+([a-fA-F0-9]+)", txs_text))
                return tx_ids
            return set()

        def get_timestamp(line):
            pattern = r"^\d+\.\d+"
            match = re.match(pattern, line)
            return float(match.group(0)) if match else None

        def get_node_name(line):
            pattern = r"Node\s+([A-Za-z0-9\-]+)"
            match = re.search(pattern, line)
            return match.group(1) if match else None

        def extract_slot(line):
            pattern = r"slot\s+(\d+)"
            match = re.search(pattern, line)
            if match:
                return int(match.group(1))
            return None

        data = []
        with open(file_path, "r") as f:
            for line in f:
                if ("appended SCPExternalize message for slot" not in line and
                        "adopting externalized value for slot" not in line):
                    continue
                node_name = get_node_name(line)
                timestamp = get_timestamp(line)
                tx_ids = get_transaction_count(line)
                slot = extract_slot(line)
                if node_name and slot is not None:
                    data.append({
                        "node name": node_name,
                        "Timestamp": timestamp,
                        "Finalised transactions": tx_ids,
                        "Slot": slot,
                        "Log": line.strip()
                    })
        df = pd.DataFrame(data)
        return df


if __name__ == '__main__':
    unittest.main()

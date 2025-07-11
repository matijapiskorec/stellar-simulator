import io
import unittest
import numpy as np
import time
import logging
import pandas as pd
from src.Mempool import Mempool
from Log import log
from Simulator import Simulator
from Globals import Globals
from Network import Network
import re


class DummyEvent:
    def __init__(self, name):
        self.name = name


class TestSCPSimulatorIntegration(unittest.TestCase):

    def setUp(self):
        """
        Initialize the simulator with a reasonably large number of nodes and appropriate parameters.
        You can try different topologies (e.g. 'ER-SINGLEQUORUMSET', 'HARDCODE') if available.
        """
        self.simulator = Simulator(verbosity=5, n_nodes=60)

        self.simulation_duration = 50.0
        Globals.simulation_time = 0.0
        self.simulator._max_simulation_time = self.simulation_duration

    def test_nomination_phase(self):

        for _ in range(10):
            self.simulator._handle_event(DummyEvent('mine'))

        self.simulator._handle_event(DummyEvent('retrieve_transaction_from_mempool'))
        self.simulator._handle_event(DummyEvent('nominate'))

        # Check that at least one node has a non-empty nomination state for 'voted' or 'accepted'
        nomination_exists = any(
            (len(node.nomination_state.get('voted', [])) > 0 or len(node.nomination_state.get('accepted', [])) > 0)
            for node in self.simulator._nodes
        )

        self.assertTrue(nomination_exists, "No node nominated any value during the nomination phase.")

    def test_full_consensus_pipeline(self):
        """
        Run a full pipeline simulation through the main event loop.
        This test runs the simulator for a fixed period of simulation time, then checks that
        a minimum number of slots have been finalized on every node’s ledger.
        """
        self.simulator.run()

        for node in self.simulator.nodes:
            num_slots = len(node.ledger.slots)
            self.assertGreaterEqual(num_slots, 1, # Check 1 slot finalised
                                    f"Node {node.name} finalized too few slots: {num_slots}")
            print(f"Node {node.name}: Finalized slots: {num_slots}")

    def test_externalization_consistency(self):
        self.simulator.run()

        # Export logs to a temporary file.
        log_file = "ledger_logs.txt"
        df = self._process_ledger_logs(log_file)

        # Group by Slot and extract the set of all transaction hashes per slot.
        slots = df.groupby("Slot")["Finalised transactions"].apply(lambda tx_sets: set().union(*tx_sets))
        # Check that no transaction hash appears in more than one slot.
        tx_occurrences = {}
        for slot, txs in slots.items():
            for tx in txs:
                if tx not in tx_occurrences:
                    tx_occurrences[tx] = []
                tx_occurrences[tx].append(slot)
        duplicates = {tx: slots for tx, slots in tx_occurrences.items() if len(slots) > 1}
        self.assertFalse(duplicates,
                         f"Some transactions appear in multiple slots: {duplicates}")

    def _process_ledger_logs(self, file_path):

        def get_transaction_count(line):
            pattern = r"transactions = \{([^}]+)\}"
            match = re.search(pattern, line)
            if match:
                return set(re.findall(r"Transaction ([a-fA-F0-9]+)", match.group(1)))
            return set()

        def get_timestamp(line):
            pattern = r"^\d+\.\d+"
            match = re.match(pattern, line)
            return float(match.group(0)) if match else None

        def get_node_name(line):
            pattern = r"Node ([A-Za-z0-9\-]+)"
            match = re.search(pattern, line)
            return match.group(1) if match else None

        def extract_slot(line):
            pattern = r"slot[^\d]*(\d+)"
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
                txs = get_transaction_count(line)
                slot = extract_slot(line)
                if node_name and slot is not None:
                    data.append({
                        "node name": node_name,
                        "Timestamp": timestamp,
                        "Finalised transactions": txs,
                        "Slot": slot,
                        "Log": line.strip()
                    })
        df = pd.DataFrame(data)
        return df




class TestSlotFinalization(unittest.TestCase):

    def setUp(self):
        self.simulator = Simulator(verbosity=5, n_nodes=60)
        self.simulator._max_simulation_time = 200.0
        Globals.simulation_time = 0.0

    def test_slots_increase_over_time(self):
        """
        Run the simulation and verify that each node finalizes a number of slots
        that increase with simulation time (i.e. more than 7 slots).
        """
        self.simulator.run()

        # Collect finalized slot counts from all nodes.
        finalized_slots = {}
        for node in self.simulator.nodes:
            num_slots = len(node.ledger.slots)
            finalized_slots[node.name] = num_slots
            print(f"Node {node.name} finalized {num_slots} slots.")
            # We expect each node to finalize more than 7 slots.
            self.assertGreater(num_slots, 7, f"Node {node.name} finalized only {num_slots} slots.")

    def test_mempool_continuously_refilled(self):
        """
        Verify that mining events continue to add transactions into the mempool.
        This ensures that the nomination phase has new transactions to propose.
        """
        mempool = self.simulator._mempool
        initial_count = len(mempool.transactions)
        # Trigger multiple mining events.
        for _ in range(20):
            self.simulator._handle_event(DummyEvent('mine'))
        later_count = len(mempool.transactions)
        print(f"Mempool size increased from {initial_count} to {later_count}.")
        self.assertGreater(later_count, initial_count,
                           "Mempool did not grow after multiple mine events.")

    def test_mempool_refill(self):
        node = self.simulator._nodes[0]
        initial_count = len(node.mempool.transactions)
        log.mempool.info("Initial mempool size for Node %s: %d", node.name, initial_count)

        for _ in range(20):
            self.simulator._handle_event(DummyEvent('mine'))

        new_count = len(node.mempool.transactions)
        log.mempool.info("New mempool size for Node %s after mining: %d", node.name, new_count)
        self.assertGreater(new_count, initial_count, "Mempool did not increase after mine events.")

    def test_log_externalize_slot_progression(self):
        self.simulator.run()
        log_file = "ledger_logs.txt"
        df = self._process_ledger_logs(log_file)
        unique_slots = df['Slot'].nunique()
        print(f"Total unique slots finalized according to log file: {unique_slots}")
        self.assertGreater(unique_slots, 7, "The log indicates too few slots were finalized.")

    def _process_ledger_logs(self, file_path):

        def get_transaction_count(line):
            pattern = r"transactions = \{([^}]+)\}"
            match = re.search(pattern, line)
            if match:
                return set(re.findall(r"Transaction ([a-fA-F0-9]+)", match.group(1)))
            return set()

        def get_timestamp(line):
            pattern = r"^\d+\.\d+"
            match = re.match(pattern, line)
            return float(match.group(0)) if match else None

        def get_node_name(line):
            pattern = r"Node ([A-Za-z0-9\-]+)"
            match = re.search(pattern, line)
            return match.group(1) if match else None

        def extract_slot(line):
            pattern = r"slot[^\d]*(\d+)"
            match = re.search(pattern, line)
            return int(match.group(1)) if match else None

        data = []
        with open(file_path, "r") as f:
            for line in f:
                if ("appended SCPExternalize message for slot" not in line and
                    "adopting externalized value for slot" not in line):
                    continue
                node_name = get_node_name(line)
                timestamp = get_timestamp(line)
                txs = get_transaction_count(line)
                slot = extract_slot(line)
                if node_name and slot is not None:
                    data.append({
                        "node name": node_name,
                        "Timestamp": timestamp,
                        "Finalised transactions": txs,
                        "Slot": slot,
                        "Log": line.strip()
                    })
        df = pd.DataFrame(data)
        return df



class TestSCPSimulatorIntegration2(unittest.TestCase):

    def setUp(self):
        self.simulator = Simulator(verbosity=5, n_nodes=60)

        from src.Network import Network
        self.simulator._nodes = Network.generate_nodes(n_nodes=self.simulator.n_nodes, topology='ER-SINGLEQUORUMSET')

        self.shared_mempool = Mempool()
        # Attach this mempool to every node.
        for node in self.simulator._nodes:
            node.attach_mempool(self.shared_mempool)

        self.simulator._mempool = self.shared_mempool

        Globals.simulation_time = 0.0
        self.simulation_duration = 50.0
        self.simulator._max_simulation_time = self.simulation_duration


    def test_mempool_refill(self):
        node = self.simulator._nodes[0]
        initial_count = len(node.mempool.transactions)
        print(f"Initial mempool size for Node {node.name}: {initial_count}")

        for _ in range(20):
            self.simulator._handle_event(DummyEvent('mine'))
        new_count = len(node.mempool.transactions)
        print(f"New mempool size for Node {node.name} after mining events: {new_count}")

        self.assertGreater(new_count, initial_count, "Mempool did not increase after mine events.")

    def test_state_reset_logging(self):
        node = self.simulator._nodes[0]

        from Transaction import Transaction
        from Value import Value
        from SCPBallot import SCPBallot

        tx = Transaction(time=Globals.simulation_time)
        value = Value(transactions={tx})
        ballot = SCPBallot(counter=1, value=value)

        node.commit_ballot_state['confirmed'][1] = ballot
        node.commit_ballot_state['voted'][1] = ballot

        count_before = len(node.commit_ballot_state['confirmed'])
        print(f"Before reset, Node {node.name} 'confirmed' ballots: {count_before}")

        node.reset_commit_phase_state(ballot)

        count_after = len(node.commit_ballot_state['confirmed'])
        print(f"After reset, Node {node.name} 'confirmed' ballots: {count_after}")

        self.assertEqual(count_after, 0, f"State reset did not clear ballots correctly for Node {node.name}.")

    def test_slot_finalization_progression(self):
        """
        Run the simulator for an extended duration and verify that
        a sufficient number of slots are finalized.
        """
        self.simulator.run()

        log_file = "ledger_logs.txt"
        df = self._process_ledger_logs(log_file)
        unique_slots = df['Slot'].nunique()
        print(f"Unique slots finalized according to log file: {unique_slots}")

        self.assertGreater(unique_slots, 7, "The log indicates too few slots were finalized.")

    def _process_ledger_logs(self, file_path):
        def get_transaction_count(line):
            pattern = r"transactions = \{([^}]+)\}"
            match = re.search(pattern, line)
            if match:
                return set(re.findall(r"Transaction ([a-fA-F0-9]+)", match.group(1)))
            return set()

        def get_timestamp(line):
            pattern = r"^\d+\.\d+"
            match = re.match(pattern, line)
            return float(match.group(0)) if match else None

        def get_node_name(line):
            pattern = r"Node ([A-Za-z0-9\-]+)"
            match = re.search(pattern, line)
            return match.group(1) if match else None

        def extract_slot(line):
            pattern = r"slot[^\d]*(\d+)"
            match = re.search(pattern, line)
            return int(match.group(1)) if match else None

        data = []
        with open(file_path, "r") as f:
            for line in f:
                if ("appended SCPExternalize message for slot" not in line and
                        "adopting externalized value for slot" not in line):
                    continue
                node_name = get_node_name(line)
                timestamp = get_timestamp(line)
                txs = get_transaction_count(line)
                slot = extract_slot(line)
                if node_name and slot is not None:
                    data.append({
                        "node name": node_name,
                        "Timestamp": timestamp,
                        "Finalised transactions": txs,
                        "Slot": slot,
                        "Log": line.strip()
                    })
        df = pd.DataFrame(data)
        return df


if __name__ == '__main__':
    unittest.main()

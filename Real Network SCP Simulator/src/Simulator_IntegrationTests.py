import glob
import unittest
import os
import shutil
from Simulator import Simulator
from Event import Event
from Gillespie import Gillespie
from Network import Network
from collections import defaultdict
import re
import pandas as pd

def get_transaction_count(line):
    pattern = r"transactions = \{([^}]+)\}"
    match = re.search(pattern, line)
    if match:
        return set(re.findall(r"Transaction ([a-fA-F0-9]+)", match.group(1)))
    return set()

def get_value_hash_and_transactions(line):
    # Matches the value hash and transactions within a SCPExternalize message
    hash_match = re.search(r"hash = ([0-9a-fA-F]+)", line)
    txs_match = re.findall(r"Transaction ([0-9a-fA-F]+)", line)
    if hash_match:
        return hash_match.group(1), set(txs_match)
    return None, set()


def get_value_matches(line):
    # Legacy: match generic 'value' occurrences
    return set(re.findall(r"(?i)value ([A-Za-z0-9]+)", line))

def get_timestamp(line):
    pattern = r"^(\d+\.\d+)"
    match = re.match(pattern, line)
    return float(match.group(1)) if match else None

def get_node_name(line):
    pattern = r"Node ([A-Za-z0-9]+)"
    match = re.search(pattern, line)
    return match.group(1) if match else None

def extract_slot(line):
    pattern = r"slot (\d+)"
    match = re.search(pattern, line)
    return int(match.group(1)) if match else None


def process_log_lines(file_path):
    data = []
    with open(file_path, 'r') as f:
        for line in f:
            if ("appended SCPExternalize message for slot" not in line and
                "adopting externalized value for slot" not in line):
                continue
            node = get_node_name(line)
            ts = get_timestamp(line)
            slot = extract_slot(line)
            if node and slot is not None:
                data.append({'node': node, 'timestamp': ts, 'msg': line.strip(), 'slot': slot})
    return pd.DataFrame(data)


def analyze_transaction_duplicates(df):
    occ, msg_types = defaultdict(set), defaultdict(set)
    for _, row in df.iterrows():
        node, slot, msg = row['node'], row['slot'], row['msg']
        prefix = " ".join(msg.split()[:10])
        txs = get_transaction_count(msg)
        for tx in txs:
            occ[tx].add((node, slot))
            msg_types[tx].add(prefix)
    return {tx: {'occurrences': occ[tx], 'msg_types': msg_types[tx]}
            for tx in occ if len({s for (_, s) in occ[tx]}) > 1}


def analyze_value_duplicates(df):
    occ, msg_types = defaultdict(set), defaultdict(set)
    for _, row in df.iterrows():
        node, slot, msg = row['node'], row['slot'], row['msg']
        prefix = " ".join(msg.split()[:10])
        hash_val, _ = get_value_hash_and_transactions(msg)
        if hash_val:
            occ[hash_val].add((node, slot))
            msg_types[hash_val].add(prefix)
    return {v: {'occurrences': occ[v], 'msg_types': msg_types[v]}
            for v in occ if len({s for (_, s) in occ[v]}) > 1}


def analyze_slot_value_mismatches(df):
    slot_results = {}
    for slot, group in df.groupby('slot'):
        val_map = {}
        for _, row in group.iterrows():
            node, msg = row['node'], row['msg']
            hash_val, txs = get_value_hash_and_transactions(msg)
            if not hash_val:
                continue
            if hash_val not in val_map:
                val_map[hash_val] = {'transactions': set(), 'nodes': set()}
            val_map[hash_val]['transactions'].update(txs)
            val_map[hash_val]['nodes'].add(node)
        if len(val_map) > 1:
            slot_results[slot] = val_map
    return slot_results


def check_slot_consensus(df):
    """
    Checks consensus for each slot observed in the DataFrame.

    Returns a dict:
      slot_number -> {
         'consensus': True if exactly one value was externalized,
                       False otherwise,
         'values': set of finalized value hashes
      }
    """
    # Gather values per observed slot
    slot_to_values = defaultdict(set)
    for _, row in df.iterrows():
        hash_val, _ = get_value_hash_and_transactions(row['msg'])
        if hash_val is not None:
            slot_to_values[row['slot']].add(hash_val)

    # Only report slots that actually saw externalize messages
    return {
        slot: {
            'consensus': (len(vals) == 1),
            'values': vals
        }
        for slot, vals in sorted(slot_to_values.items())
    }

class SimulatorIntegrationTest(unittest.TestCase):

    RESULTS_FILE = 'runs_test_results.txt'

    def setUp(self):
        # Ensure logs directory is clean before each test
        logs_dir = './logs'
        if os.path.exists(logs_dir):
            shutil.rmtree(logs_dir)
        os.makedirs(logs_dir)
        # Reset results file
        with open(self.RESULTS_FILE, 'w') as f:
            f.write("# Simulator Runs Test Results\n")

    def get_simulation_param_sets(self, nodes):
        param_sets = []

        # Default setup
        default_params = {
            'mine': {'tau': 5.0, 'tau_domain': nodes},
            'retrieve_transaction_from_mempool': {'tau': 5.0, 'tau_domain': nodes},
            'receive_commit_message': {'tau': 1.0, 'tau_domain': nodes},
            'receive_externalize_msg': {'tau': 1.0, 'tau_domain': nodes},  # 0.1 -> 0.05
            'retrieve_message_from_peer': {'tau': 1.0, 'tau_domain': nodes},
            'receive_prepare_message': {'tau': 1.0, 'tau_domain': nodes},

            'nominate': {'tau': 1.0, 'tau_domain': nodes},
            'prepare_ballot': {'tau': 1.0, 'tau_domain': nodes},
            'prepare_commit': {'tau': 1.0, 'tau_domain': nodes},
            'prepare_externalize_message': {'tau': 1.0, 'tau_domain': nodes}
        }
        param_sets.append(default_params)

        # Communication group sped up by 0.5
        communication_fast_params = {
            'mine': {'tau': 5.0, 'tau_domain': nodes},
            'retrieve_transaction_from_mempool': {'tau': 5.0, 'tau_domain': nodes},
            'receive_commit_message': {'tau': 0.5, 'tau_domain': nodes},
            'receive_externalize_msg': {'tau': 0.5, 'tau_domain': nodes},  # 0.1 -> 0.05
            'retrieve_message_from_peer': {'tau': 0.5, 'tau_domain': nodes},
            'receive_prepare_message': {'tau': 0.5, 'tau_domain': nodes},

            'nominate': {'tau': 1.0, 'tau_domain': nodes},
            'prepare_ballot': {'tau': 1.0, 'tau_domain': nodes},
            'prepare_commit': {'tau': 1.0, 'tau_domain': nodes},
            'prepare_externalize_message': {'tau': 1.0, 'tau_domain': nodes}
        }
        param_sets.append(communication_fast_params)

        # Processing group sped up by 0.5
        processing_fast_params = {
            'mine': {'tau': 5.0, 'tau_domain': nodes},
            'retrieve_transaction_from_mempool': {'tau': 5.0, 'tau_domain': nodes},
            'receive_commit_message': {'tau': 1.0, 'tau_domain': nodes},
            'receive_externalize_msg': {'tau': 1.0, 'tau_domain': nodes},
            'retrieve_message_from_peer': {'tau': 1.0, 'tau_domain': nodes},
            'receive_prepare_message': {'tau': 1.0, 'tau_domain': nodes},

            'nominate': {'tau': 0.5, 'tau_domain': nodes},
            'prepare_ballot': {'tau': 0.5, 'tau_domain': nodes},
            'prepare_commit': {'tau': 0.5, 'tau_domain': nodes},
            'prepare_externalize_message': {'tau': 0.5, 'tau_domain': nodes}
        }
        param_sets.append(processing_fast_params)

        return param_sets

    def log_run_results(self, n_nodes, idx, tx_dups, val_dups, consensus, mismatches):
        with open(self.RESULTS_FILE, 'a') as f:
            f.write(f"\nRun n_nodes={n_nodes}, param_set={idx}\n")
            f.write("Duplicate Transactions across slots:\n")
            if tx_dups:
                for tx, slot_info in tx_dups.items():
                    f.write(f" - TX {tx}:\n")
                    for slot, count in sorted(slot_info.items()):
                        f.write(f"    * Slot {slot}: finalized by {count} nodes\n")
            else:
                f.write(" - None found.\n")
            f.write("Duplicate Values across slots:\n")
            if val_dups:
                for v, info in val_dups.items():
                    slots = sorted(info['occurrences'])
                    msgs = sorted(info['msg_types'])
                    f.write(f" - Value {v}: slots={slots}, msg_types={msgs}\n")
            else:
                f.write(" - None found.\n")
            f.write("Consensus check per slot:\n")
            for slot, info in sorted(consensus.items()):
                f.write(f"Slot : Number {slot}\n")
                f.write(f"Consensus: {'CONSENSUS' if info['consensus'] else 'NO CONSENSUS'}\n")
                f.write(f"Values = {info['values']}\n")

            f.write("Slot value mismatches (if any):\n")
            if mismatches:
                for slot, val_map in sorted(mismatches.items()):
                    f.write(f" - Slot {slot}:\n")
                    for hv, detail in val_map.items():
                        f.write(f"    * Value {hv}: nodes={sorted(detail['nodes'])}, transactions={sorted(detail['transactions'])}\n")
            else:
                f.write(" - None found.\n")

    def clean_log_files(self):
        """Delete specific log files generated by simulator before each run."""
        log_files = [
            "simulator_events_log.txt",
            "simulator_mine_events.txt",
            "ledger_logs.txt"
        ]
        for file_path in log_files:
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except Exception as e:
                    print(f"Error deleting file {file_path}: {e}")

    def test_simulator_multiple_tau_and_nodes(self):
        node_counts = [10, 30, 60]

        for n_nodes in node_counts:
            with self.subTest(n_nodes=n_nodes):
                nodes = Network.generate_nodes(n_nodes=n_nodes, topology='ER')  # pre-generate nodes to assign to params

                # Get all three simulation parameter sets
                param_sets = self.get_simulation_param_sets(nodes)

                for idx, simulation_params in enumerate(param_sets):
                    with self.subTest(param_set=idx):
                        self.clean_log_files()
                        open("ledger_logs.txt", 'w').close()

                        # Now create simulator WITH custom simulation params
                        simulator = Simulator(
                            verbosity=5,
                            n_nodes=n_nodes,
                            max_simulation_time=100,
                            simulation_params=simulation_params
                        )
                        simulator._nodes = nodes  # manually set nodes if needed
                        simulator.run()

                        self.assertGreaterEqual(len(simulator.nodes), (n_nodes//2))

                        # --- Analyze duplicates ---
                        df = process_log_lines("simulator_events_log.txt")
                        tx_dups = analyze_transaction_duplicates(df)
                        val_dups = analyze_value_duplicates(df)
                        #consensus_results = check_slot_consensus(df)
                        consensus = check_slot_consensus(df)
                        mismatches = analyze_slot_value_mismatches(df)
                        self.log_run_results(n_nodes, simulation_params, tx_dups, val_dups, consensus, mismatches)


                # TODO: After running all, add code to collect and check duplicates

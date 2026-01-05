#!/usr/bin/env python3
import os
import sys
import argparse
import multiprocessing
import csv
import json
import re
from collections import defaultdict
import pandas as pd

print(f" Booting {__file__}, argv={sys.argv!r}")

SUMMARY_CSV = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "ER_SCP_scaling_txs_simulation_summary.csv")
)
FIELDNAMES = [
    "node_count",
    "simulation_time",
    "sim_params",
    "total_tx_created",
    "total_slots",
    "total_tx_in_all_slots",
    "avg_txs_per_slot",
    "avg_inter_slot_time",
    "all_tests_passed",
]

def append_summary_row(row: dict):
    os.makedirs(os.path.dirname(SUMMARY_CSV), exist_ok=True)
    write_header = not os.path.isfile(SUMMARY_CSV)
    with open(SUMMARY_CSV, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDNAMES)
        if write_header:
            w.writeheader()
        w.writerow(row)

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
    pattern = r"Node ([A-Z0-9]+)"
    match = re.search(pattern, line)
    return match.group(1) if match else None


def extract_slot_finalisation_times(file_path):
    slot_times = {}
    pattern = re.compile(r"(\d+\.\d+).*?Node [A-Z0-9]+.*?(?:appended|adopting) externalize.*?slot (\d+)", re.IGNORECASE)
    with open(file_path, 'r') as file:
        for line in file:
            m = pattern.search(line)
            if m:
                timestamp = float(m.group(1))
                slot = int(m.group(2))
                # Only record the first externalize seen for each slot
                if slot not in slot_times:
                    slot_times[slot] = timestamp
    # Return sorted list of finalisation times by slot number
    return [slot_times[slot] for slot in sorted(slot_times)]


def process_log_lines(file_path):
    node_data = defaultdict(lambda: {
        "Timestamp of finalisation": None,
        "Finalised transactions": set(),
        "Externalize messages": []
    })
    with open(file_path, 'r') as file:
        lines = file.readlines()
    for line in lines:
        if ('appended SCPExternalize message' not in line
                and 'adopting externalized value for slot' not in line):
            continue
        node_name = get_node_name(line)
        timestamp = get_timestamp(line)
        transactions = get_transaction_count(line)
        if node_name:
            if node_data[node_name]["Timestamp of finalisation"] is None:
                node_data[node_name]["Timestamp of finalisation"] = timestamp
            node_data[node_name]["Finalised transactions"].update(transactions)
            node_data[node_name]["Externalize messages"].append(line.strip())
    df = pd.DataFrame.from_dict(node_data, orient='index')
    df.index.name = "sequence number"
    df = df.reset_index()
    df["No. of finalised transactions"] = df["Finalised transactions"].apply(len)
    return df

def compute_summary_metrics(events_log_path: str):
    # Mining: count unique hashes from "mined to the mempool!" lines
    mined_hashes = set()
    mining_pat = re.compile(r"\[Transaction ([A-Fa-f0-9]+) time = [\d\.]+\] mined to the mempool!")
    with open(events_log_path, 'r') as f:
        for line in f:
            m = mining_pat.search(line)
            if m:
                mined_hashes.add(m.group(1))
    total_tx_created = len(mined_hashes)

    df = process_log_lines(events_log_path)
    total_slots = df["Externalize messages"].apply(len).sum()
    all_finalized = set()
    for s in df["Finalised transactions"]:
        all_finalized.update(s)
    total_tx_in_all_slots = len(all_finalized)

    avg_txs_per_slot = (total_tx_in_all_slots / total_slots) if total_slots else 0.0

    slot_finalisation_times = extract_slot_finalisation_times(events_log_path)
    intervals = [t2 - t1 for t1, t2 in zip(slot_finalisation_times, slot_finalisation_times[1:])]
    avg_inter_slot_time = (sum(intervals) / len(intervals)) if intervals else 0.0

    return (
        total_tx_created,
        total_slots,
        total_tx_in_all_slots,
        avg_txs_per_slot,
        avg_inter_slot_time
    )


def compute_total_tx_created(mine_events_path: str) -> int:
    """
    Count unique transaction hashes in lines like:
      199.88 - MEMPOOL - INFO - Transaction [Transaction aa9ba824 time = 199.8848] mined to the mempool!
    """
    mined_pattern = re.compile(r"\[Transaction\s+([A-Fa-f0-9]+)\s+time\s*=\s*[\d\.]+\]\s+mined to the mempool!")
    hashes = set()
    with open(mine_events_path, "r") as f:
        for line in f:
            m = mined_pattern.search(line)
            if m:
                hashes.add(m.group(1))
    return len(hashes)


ROOT = os.path.abspath(os.path.join(__file__, os.pardir, os.pardir))
SRC = os.path.join(ROOT, "src")
sys.path.insert(0, SRC)
from Simulator import Simulator

import os
import sys
import argparse
import json
import csv


def run_single_sim(run_id, n_nodes, max_sim_time):
    run_dir = os.path.join("../scripts/logs", f"run_{run_id}")
    os.makedirs(run_dir, exist_ok=True)
    cwd = os.getcwd()
    os.chdir(run_dir)
    try:
        sim = Simulator(
            verbosity=1,
            n_nodes=n_nodes,
            max_simulation_time=max_sim_time,
            network_type='HARDCODE',  # Only if your Simulator expects this
        )
        sim.run()
        events_log = "simulator_events_log.txt"
        (total_tx_created, total_slots, total_tx_in_all_slots,
         avg_txs_per_slot, avg_inter_slot_time) = compute_summary_metrics(events_log)

        mine_log = "simulator_mine_events.txt"
        if os.path.isfile(mine_log):
            total_tx_created = compute_total_tx_created(mine_log)
        else:
            total_tx_created = 0

        append_summary_row({
            "node_count": n_nodes,
            "simulation_time": max_sim_time,
            "sim_params": json.dumps({
                "n_nodes": n_nodes,
                "sim_duration": max_sim_time,
                "network_type": "HARDCODE",
            }),
            "total_tx_created": total_tx_created,
            "total_slots": total_slots,
            "total_tx_in_all_slots": total_tx_in_all_slots,
            "avg_txs_per_slot": f"{avg_txs_per_slot:.2f}",
            "avg_inter_slot_time": f"{avg_inter_slot_time:.2f}",
            "all_tests_passed": True,
        })
        print(f"Run {run_id} finished. Logs in {run_dir}")
    except Exception as e:
        print(f"[worker] Exception: {e!r}")
        append_summary_row({
            "node_count": n_nodes,
            "simulation_time": max_sim_time,
            "sim_params": json.dumps({
                "n_nodes": n_nodes,
                "sim_duration": max_sim_time,
                "network_type": "HARDCODE",
            }),
            **dict.fromkeys(FIELDNAMES[3:], 0),
            "all_tests_passed": False,
        })
    finally:
        os.chdir(cwd)

if __name__ == "__main__":
    test_configs = [
        {"n_nodes": 7, "max_sim_time": 1000.0}
    ]
    for run_id, params in enumerate(test_configs, 1):
        print(f"\n=== Running simulation {run_id} ===")
        run_single_sim(run_id, **params)


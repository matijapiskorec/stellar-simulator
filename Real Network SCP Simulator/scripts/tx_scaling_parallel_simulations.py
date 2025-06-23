#!/usr/bin/env python3
import multiprocessing
import os
import sys
import argparse
import csv
import json
import re
from collections import defaultdict
import pandas as pd

print(f" Booting {__file__}, argv={sys.argv!r}")

SUMMARY_CSV = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "simulation_summary.csv")
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
    # Finalisation/slots/adoption/externalize
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

def worker(run_id: int, n_nodes: int, max_sim_time: float, simulation_params: dict) -> bool:
    run_dir = os.path.join("logs", f"run_{run_id}")
    os.makedirs(run_dir, exist_ok=True)
    cwd = os.getcwd()
    os.chdir(run_dir)
    try:
        print("instantiating simulator")
        sim = Simulator(
            verbosity=1,
            n_nodes=n_nodes,
            max_simulation_time=max_sim_time,
            simulation_params=simulation_params
        )
        print("RUNNING SIMULATION!!!")
        sim.run()
        print("RAN SIMULATION!!!")
        events_log = "simulator_events_log.txt"
        print(f"[worker] Parsing events from {events_log}")
        (total_tx_created,
         total_slots,
         total_tx_in_all_slots,
         avg_txs_per_slot,
         avg_inter_slot_time) = compute_summary_metrics(events_log)
        print(f"[worker] → created: {total_tx_created}, slots: {total_slots}, finalised: {total_tx_in_all_slots}")

        mine_log = "simulator_mine_events.txt"
        if os.path.isfile(mine_log):
            total_tx_created = compute_total_tx_created(mine_log)
        else:
            print(f"[worker] Mine log missing: {mine_log} -- will report 0 mined txs")
            total_tx_created = 0

        append_summary_row({
            "node_count": n_nodes,
            "simulation_time": max_sim_time,
            "sim_params": json.dumps(simulation_params),
            "total_tx_created": total_tx_created,
            "total_slots": total_slots,
            "total_tx_in_all_slots": total_tx_in_all_slots,
            "avg_txs_per_slot": f"{avg_txs_per_slot:.2f}",
            "avg_inter_slot_time": f"{avg_inter_slot_time:.2f}",
            "all_tests_passed": True,
        })
        return True
    except Exception as e:
        print(f"[worker] Exception: {e!r}")
        append_summary_row({
            "node_count": n_nodes,
            "simulation_time": max_sim_time,
            "sim_params": json.dumps(simulation_params),
            **dict.fromkeys(FIELDNAMES[3:], 0),
            "all_tests_passed": False,
        })
        return False
    finally:
        os.chdir(cwd)
        print(f"Run {run_id} finished. Logs in {run_dir}")


def main():
    p = argparse.ArgumentParser("Parallel sim runs → summary CSV")
    p.add_argument("--n-nodes", type=int, nargs='+', required=True)
    p.add_argument("--max-simulation-time", type=float, nargs='+', required=True)
    p.add_argument("--simulation-params", type=str, nargs='+', required=True,
                   help="Simulation parameters as a JSON string")
    args = p.parse_args()
    if not (len(args.n_nodes) == len(args.max_simulation_time) == len(args.simulation_params)):
        p.error("Must supply equal counts of --n-nodes, --max-simulation-time, and --simulation-params")

    params = []
    for i, (n, t, sim_json) in enumerate(zip(args.n_nodes, args.max_simulation_time, args.simulation_params)):
        try:
            sim_params = json.loads(sim_json)
        except json.JSONDecodeError as e:
            print(f"Error parsing simulation params JSON at index {i}: {e}")
            sys.exit(1)
        params.append((i + 1, n, t, sim_params))
    cores = min(multiprocessing.cpu_count(), len(params))
    print(f"Launching {len(params)} jobs on up to {cores} cores…")
    with multiprocessing.Pool(cores) as pool:
        print("RUNNING WITH PARAMS = ", params)
        results = pool.starmap(worker, params)
    if not all(results):
        print("❌ Some runs failed—check logs.")
        sys.exit(1)
    print("✅ All simulations complete.")


if __name__ == "__main__":
    main()

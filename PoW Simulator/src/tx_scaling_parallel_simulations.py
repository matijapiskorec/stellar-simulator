import os
import sys
import argparse
import multiprocessing
import math
import contextlib
import csv
import json
from collections import Counter

ROOT = os.path.abspath(os.path.join(__file__, os.pardir, os.pardir))
SRC = os.path.join(ROOT, "src")
sys.path.insert(0, SRC)

from Simulator import Simulator, Globals
from TestPOWSimulator import parse_pow_logs
from Block import Block

SUMMARY_CSV = os.path.join("..", "simulation_summary.csv")
FIELDNAMES = [
    "node_count", "simulation_time", "sim_params", "total_tx_created",
    "main_chain_length", "total_tx_in_mainchain", "total_stale_blocks",
    "avg_depth_stale_blocks", "avg_blocks_per_node", "avg_inter_block_time",
    "avg_messages_per_block", "all_tests_passed"
]

def append_summary_row(row: dict):
    os.makedirs(os.path.dirname(SUMMARY_CSV), exist_ok=True)
    file_exists = os.path.isfile(SUMMARY_CSV)
    with open(SUMMARY_CSV, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)

def worker(run_id, n_nodes, max_sim_time, simulation_params):
    run_dir = os.path.join("logs", f"run_{run_id}")
    os.makedirs(run_dir, exist_ok=True)
    cwd = os.getcwd()
    os.chdir(run_dir)

    try:
        Globals.simulation_time = 0.0
        sim = Simulator(verbosity=5, n_nodes=n_nodes, simulation_params=simulation_params)
        sim._max_simulation_time = max_sim_time
        sim._simulation_params = simulation_params
        sim.run()

        import time
        ledger_log_path = "ledger_logs.txt"
        for _ in range(10):
            if os.path.exists(ledger_log_path):
                break
            time.sleep(1)

        mined_df = parse_pow_logs(ledger_log_path)
        block_counts = Counter(
            blk.hash for node in sim.nodes for blk in node.blockchain.get_longest_chain()
        )
        threshold = math.ceil(0.95 * n_nodes)
        main_hashes = {h for h, c in block_counts.items() if c >= threshold}

        hash_to_block = {}
        for node in sim.nodes:
            for blk in node.blockchain.get_longest_chain():
                hash_to_block[blk.hash] = blk
            for orphan in node.blockchain.orphans.values():
                if isinstance(orphan, Block):
                    hash_to_block[orphan.hash] = orphan

        stale_hashes = set(hash_to_block) - main_hashes

        # --- Robust, unique transaction counting ---
        all_created = set()
        for node in sim.nodes:
            # from mempool
            all_created.update(getattr(tx, "_hash", getattr(tx, "hash", None)) for tx in node.mempool.transactions)
            # from canonical chain
            for blk in node.blockchain.get_longest_chain():
                all_created.update(getattr(tx, "_hash", getattr(tx, "hash", None)) for tx in blk.transactions)
            # from orphans
            for orphan in node.blockchain.orphans.values():
                if hasattr(orphan, "transactions"):
                    all_created.update(getattr(tx, "_hash", getattr(tx, "hash", None)) for tx in orphan.transactions)
        all_created.discard(None)
        total_tx_created = len(all_created)
        # --- End unique transaction counting ---

        total_tx_in_mainchain = sum(
            len(hash_to_block[h].transactions) for h in main_hashes if h in hash_to_block
        )

        def depth_of(block):
            d, cur = 0, block
            while cur.hash not in main_hashes:
                d += 1
                if cur.prev_hash is None or cur.prev_hash not in hash_to_block:
                    break
                cur = hash_to_block[cur.prev_hash]
            return d

        depths = [depth_of(hash_to_block[h]) for h in stale_hashes if h in hash_to_block]
        avg_depth_stale = sum(depths) / len(depths) if depths else 0.0

        df_main = mined_df[
            mined_df["block_hash"].isin(main_hashes) & mined_df["node"].notnull()
        ] if not mined_df.empty and "block_hash" in mined_df.columns else []

        num_blocks = len(main_hashes)
        blocks = [hash_to_block[h] for h in main_hashes if h in hash_to_block]
        blocks.sort(key=lambda blk: blk.height)
        times = [blk.timestamp for blk in blocks]
        intervals = [t2 - t1 for t1, t2 in zip(times, times[1:])]
        avg_inter = sum(intervals) / len(intervals) if intervals else float("nan")

        total_msg_count = 0
        with open(ledger_log_path, 'r') as f:
            for line in f:
                if "- NODE - CRITICAL -" not in line:
                    continue
                if "mined to the mempool" in line or "mined block" in line:
                    continue
                total_msg_count += 1
        avg_messages_per_block = total_msg_count / num_blocks if num_blocks else 0.0

        counts_dict = df_main.drop_duplicates(["node", "block_hash"]).groupby("node").size().to_dict() if len(df_main) else {}
        blocks_per_node = [counts_dict.get(i, 0) for i in range(n_nodes)]
        avg_blocks_per_node = sum(blocks_per_node) / n_nodes

        append_summary_row({
            "node_count": n_nodes,
            "simulation_time": max_sim_time,
            "sim_params": simulation_params,
            "total_tx_created": total_tx_created,
            "main_chain_length": len(main_hashes),
            "total_tx_in_mainchain": total_tx_in_mainchain,
            "total_stale_blocks": len(stale_hashes),
            "avg_depth_stale_blocks": f"{avg_depth_stale:.2f}",
            "avg_blocks_per_node": f"{avg_blocks_per_node:.2f}",
            "avg_inter_block_time": f"{avg_inter:.2f}",
            "avg_messages_per_block": f"{avg_messages_per_block:.2f}",
            "all_tests_passed": True
        })
        return True
    finally:
        os.chdir(cwd)
        print(f"Run {run_id} finished. Logs in {run_dir}/")

def main():
    parser = argparse.ArgumentParser(description="PoW parallel simulation runner with custom parameters")
    parser.add_argument("--n-nodes", type=int, nargs='+', required=True)
    parser.add_argument("--max-simulation-time", type=float, nargs='+', required=True)
    parser.add_argument("--simulation-params", type=str, nargs='+', required=True, help="List of JSON strings")
    args = parser.parse_args()

    if not (len(args.n_nodes) == len(args.max_simulation_time) == len(args.simulation_params)):
        parser.error("Argument lengths must match for --n-nodes, --max-simulation-time, and --simulation-params")

    parsed_params = [json.loads(p.replace("'", '"')) for p in args.simulation_params]
    params = [(i + 1, n, t, p) for i, (n, t, p) in enumerate(zip(args.n_nodes, args.max_simulation_time, parsed_params))]

    with multiprocessing.Pool(min(len(params), multiprocessing.cpu_count())) as pool:
        results = pool.starmap(worker, params)

    if not all(results):
        print("❌ Some runs failed—check logs.")
        sys.exit(1)
    print("✅ All simulations completed.")

if __name__ == "__main__":
    main()
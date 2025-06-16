#!/usr/bin/env python
import os
import sys
import argparse
import multiprocessing
import math
from collections import Counter
import unittest
import contextlib

import os, csv, json

SUMMARY_CSV = os.path.join("..", "simulation_summary.csv")
FIELDNAMES = [
    "node_count",
    "simulation_time",
    "sim_params",
    "total_tx_created",
    "main_chain_length",
    "total_tx_in_mainchain",
    "total_stale_blocks",
    "avg_depth_stale_blocks",
    "avg_blocks_per_node",
    "avg_inter_block_time",
    "avg_messages_per_block",
    "all_tests_passed"
]

def append_summary_row(row: dict):
    """Append a single row to the shared CSV, creating it with headers if necessary."""
    os.makedirs(os.path.dirname(SUMMARY_CSV), exist_ok=True)
    file_exists = os.path.isfile(SUMMARY_CSV)
    with open(SUMMARY_CSV, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)


# adjust path so we can import Simulator, Globals, parse_pow_logs, Block
ROOT = os.path.abspath(os.path.join(__file__, os.pardir, os.pardir))
SRC = os.path.join(ROOT, "src")
sys.path.insert(0, SRC)

from Simulator import Simulator, Globals
from TestPOWSimulator import parse_pow_logs    # adjust import path if necessary
from Block import Block                        # adjust import path if necessary

# adjust path so we can import Simulator, Globals, parse_pow_logs, Block
ROOT = os.path.abspath(os.path.join(__file__, os.pardir, os.pardir))
SRC = os.path.join(ROOT, "src")
sys.path.insert(0, SRC)


class TestPoWSimulator(unittest.TestCase):
    """
    Runs one PoW simulation and verifies chain agreement, tx coverage,
    mining distribution, block sizes, and fork-depth distribution.
    """

    @classmethod
    def setUpClass(cls):
        cls.sim_duration = getattr(cls, "_sim_duration", 50.0)
        cls.n_nodes = getattr(cls, "_n_nodes", 200)
        Globals.simulation_time = 0.0

        cls.sim = Simulator(verbosity=5, n_nodes=cls.n_nodes)
        cls.sim._max_simulation_time = cls.sim_duration
        cls.sim.run()

        cls.mined_df = parse_pow_logs("ledger_logs.txt")

        block_counts = Counter(
            blk.hash
            for node in cls.sim.nodes
            for blk in node.blockchain.get_longest_chain()
        )
        cls.threshold = math.ceil(0.95 * cls.n_nodes)
        cls.main_chain_hashes = {
            h for h, c in block_counts.items() if c >= cls.threshold
        }

        cls.hash_to_block = {}
        for node in cls.sim.nodes:
            for blk in node.blockchain.get_longest_chain():
                cls.hash_to_block[blk.hash] = blk
            for orphan in node.blockchain.orphans.values():
                if isinstance(orphan, Block):
                    cls.hash_to_block[orphan.hash] = orphan
        cls.stale_hashes = set(cls.hash_to_block) - cls.main_chain_hashes

    def extract_tx_hashes(self, blk):
        if isinstance(blk, dict):
            return blk.get("txhash_list", [])
        return [tx._hash for tx in blk.transactions]

    def test_chain_agreement_and_tx_coverage(self):
        confirmed = {
            tx
            for h, blk in self.hash_to_block.items()
            if h in self.main_chain_hashes
            for tx in self.extract_tx_hashes(blk)
        }
        all_created = set()
        for node in self.sim.nodes:
            all_created.update(tx._hash for tx in node.mempool.transactions)
            for blk in node.blockchain.get_longest_chain():
                all_created.update(self.extract_tx_hashes(blk))
            for orphan in node.blockchain.orphans.values():
                if isinstance(orphan, Block):
                    all_created.update(self.extract_tx_hashes(orphan))
                else:
                    all_created.update(orphan.get("txhash_list", []))
        assert all_created, "No transactions produced during simulation"
        coverage = len(confirmed) / len(all_created)
        print(f"\nTransaction coverage: {coverage:.2%}")
        self.assertGreater(
            coverage, 0.5,
            f"Coverage too low: {coverage:.2%}"
        )

    def test_blocks_mined_per_node_and_avg_block_size(self):
        df = self.mined_df
        if df.empty or "block_hash" not in df.columns:
            print("WARNING: No mining/creation events parsed from ledger_logs.txt")
            return
        df_main = df[
            df["block_hash"].isin(self.main_chain_hashes) &
            df["node"].notnull()
        ]
        mined_counts = {i: 0 for i in range(self.n_nodes)}
        for _, row in df_main.drop_duplicates(["node","block_hash"]).iterrows():
            mined_counts[int(row["node"])]+=1
        print("\nBlocks per miner in main chain:")
        for node_id in range(self.n_nodes):
            print(f"  Node {node_id:2d}: {mined_counts[node_id]}")
        zeros = [i for i, cnt in mined_counts.items() if cnt == 0]
        self.assertFalse(
            zeros,
            f"Some nodes have zero main-chain blocks: {zeros}"
        )
        avg_txs = df_main.groupby("block_hash")["txs"].first().mean() if not df_main.empty else 0.0
        print(f"\nAverage txs per main-chain block: {avg_txs:.2f}")
        self.assertGreater(
            avg_txs, 0.0,
            "No transactions in main-chain blocks"
        )

    def test_fork_depth_distribution(self):
        if not self.stale_hashes:
            self.skipTest("No stale forks to analyze")
        self.hash_to_block = {}
        for node in self.sim.nodes:
            for h, entry in node.blockchain.chain.items():
                self.hash_to_block[h] = entry['block']
            for orphan in node.blockchain.orphans.values():
                self.hash_to_block[orphan.hash] = orphan
        def compute_depth(blk):
            depth, cur = 0, blk
            while cur.hash not in self.main_chain_hashes:
                depth += 1
                cur = self.hash_to_block[cur.prev_hash]
            return depth
        depth_counts = Counter(
            compute_depth(self.hash_to_block[h])
            for h in self.stale_hashes
        )
        print("\nFork-depth distribution:")
        for d, n in sorted(depth_counts.items()):
            print(f"  {n:4d} forks of depth {d}")
        max_depth = max(depth_counts.keys())
        self.assertLessEqual(
            max_depth, 5,
            f"Too-deep forks: max depth {max_depth}"
        )

    def compute_avg_messages_per_block(ledger_log_path, n_blocks):
            """
            Counts all protocol messages (lines with '- NODE - INFO -') in ledger_logs.txt
            and returns average per main-chain block.
            """
            total_msg_count = 0
            with open(ledger_log_path, 'r') as f:
                for line in f:
                    if "- NODE - CRITICAL -" not in line:
                        continue
                    # Optionally: exclude mining events or any non-protocol lines
                    if "mined to the mempool" in line or "mined block" in line:
                        continue
                    total_msg_count += 1
            if n_blocks == 0:
                return 0.0
            return total_msg_count / n_blocks


def worker(run_id: int, n_nodes: int, max_sim_time: float) -> bool:
    """Runs PoW tests in its own log folder; returns True if all tests pass."""
    run_dir = os.path.join("logs", f"run_{run_id}")
    os.makedirs(run_dir, exist_ok=True)
    cwd = os.getcwd()
    os.chdir(run_dir)
    try:
        TestPoWSimulator._sim_duration = max_sim_time
        TestPoWSimulator._n_nodes     = n_nodes

        loader = unittest.TestLoader()
        suite  = loader.loadTestsFromTestCase(TestPoWSimulator)
        runner = unittest.TextTestRunner(verbosity=2)

        log_filename = 'test_results.log'

        # Save all prints and TestRunner's errors, etc.
        # everything printed goes to log
        with open(log_filename, 'w') as log_file, \
             contextlib.redirect_stdout(log_file), \
             contextlib.redirect_stderr(log_file): # everything that goes to standard error is logged
            result = runner.run(suite)

        import time
        ledger_log_path = "ledger_logs.txt"
        # Wait up to 2 seconds in 0.2s intervals for the file to appear
        for _ in range(10):
            if os.path.exists(ledger_log_path):
                break
            time.sleep(5)
        else:
            print(f"[WARN] ledger_logs.txt not found after simulation run {run_id}")

        # 2) Now the TestPoWSimulator class has already built:
        #    - sim (the Simulator instance)
        #    - mined_df (parsed ledger_logs.txt)
        sim = TestPoWSimulator.sim
        mined_df = TestPoWSimulator.mined_df
        main_hashes = TestPoWSimulator.main_chain_hashes
        stale_hashes = TestPoWSimulator.stale_hashes

        blocks = [TestPoWSimulator.hash_to_block[h] for h in main_hashes]
        blocks.sort(key=lambda blk: blk.height)


        # 3) Re-compute any “extra” metrics not already on the TestPoWSimulator class:
        #    (a) total_tx_created
        all_created = set()
        for node in sim.nodes:
            # from mempool
            all_created.update(tx._hash for tx in node.mempool.transactions)
            # from canonical chain
            for blk in node.blockchain.get_longest_chain():
                all_created.update(tx._hash for tx in blk.transactions)
            # from orphans
            for orphan in node.blockchain.orphans.values():
                if hasattr(orphan, "transactions"):
                    all_created.update(tx._hash for tx in orphan.transactions)
        total_tx_created = len(all_created)

        #    (b) main_chain_length
        main_chain_length = len(main_hashes)

        """
        #    (c) total_tx_in_mainchain
        total_tx_in_mainchain = 0
        for node in sim.nodes:
            for blk in node.blockchain.get_longest_chain():
                if blk.hash in main_hashes:
                    total_tx_in_mainchain += len(blk.transactions) """

        total_tx_in_mainchain = sum(
            len(TestPoWSimulator.hash_to_block[h].transactions) for h in main_hashes )

        #    (d) total_stale_blocks
        total_stale_blocks = len(stale_hashes)

        #    (e) avg_depth_stale_blocks
        #        (re-compute the depth‐of‐fork logic)
        h2b = {}
        for node in sim.nodes:
            for blk in node.blockchain.get_longest_chain():
                h2b[blk.hash] = blk
            for orphan in node.blockchain.orphans.values():
                h2b[orphan.hash] = orphan

        def depth_of(block):
            d, cur = 0, block
            while cur.hash not in main_hashes:
                d += 1
                # Safeguard for genesis or missing block
                if cur.prev_hash is None or cur.prev_hash not in h2b:
                    break
                cur = h2b[cur.prev_hash]
            return d

        depths = [depth_of(h2b[h]) for h in stale_hashes]
        avg_depth_stale = sum(depths) / len(depths) if depths else 0.0

        if "block_hash" not in mined_df.columns:
            print("Ledger log parsing error: 'block_hash' column missing in mined_df. Columns are:", mined_df.columns)
            print("First few rows:", mined_df.head())
            # Optionally, raise a custom error to help debugging
            raise RuntimeError(
                "parse_pow_logs did not produce expected columns. Check ledger_logs.txt and parse_pow_logs.")

        if "block_hash" not in mined_df.columns or mined_df.empty:
            print("WARNING: No mining/creation events parsed from ledger_logs.txt")
        else:
            #    (f) avg_blocks_per_node (on main chain)
            df_main = mined_df[
                mined_df["block_hash"].isin(main_hashes)
                & mined_df["node"].notnull()
                ]

        # 2) total count
        num_blocks = len(blocks)
        print(f"Total main-chain blocks: {num_blocks}")

        # 3) heights for sanity check
        heights = [blk.height for blk in blocks]
        print(f"Heights on main chain: {heights}")

        # 4) compute inter-block intervals
        times = [blk.timestamp for blk in blocks]
        intervals = [t2 - t1 for t1, t2 in zip(times, times[1:])]

        # 5) average (guarding against a single‐block corner case, though you say you always have >1)
        avg_inter = sum(intervals) / len(intervals) if intervals else float("nan")
        print(f"Average inter-block time: {avg_inter:.3f} seconds")

        avg_messages_per_block = TestPoWSimulator.compute_avg_messages_per_block(ledger_log_path=ledger_log_path, n_blocks=num_blocks)

        #print(f"\nAverage inter-block time: {avg_inter_block_time:.2f} seconds")

        counts_dict = df_main.drop_duplicates(["node", "block_hash"]) \
            .groupby("node") \
            .size() \
            .to_dict()

        blocks_per_node = [counts_dict.get(i, 0) for i in range(n_nodes)]
        avg_blocks_per_node = sum(blocks_per_node) / n_nodes

        # 4) Finally, append to the shared CSV:
        append_summary_row({
            "node_count": n_nodes,
            "simulation_time": max_sim_time,
            "sim_params": json.dumps({
                "n_nodes": n_nodes,
                "sim_duration": max_sim_time,
                "mine": 0.25
            }),
            "total_tx_created": total_tx_created,
            "main_chain_length": main_chain_length,
            "total_tx_in_mainchain": total_tx_in_mainchain,
            "total_stale_blocks": total_stale_blocks,
            "avg_depth_stale_blocks": f"{avg_depth_stale:.2f}",
            "avg_blocks_per_node": f"{avg_blocks_per_node:.2f}",
            "avg_inter_block_time": f"{avg_inter:.2f}",
            "avg_messages_per_block": f"{avg_messages_per_block:.2f}",
            "all_tests_passed": result.wasSuccessful(),
        })

        return result.wasSuccessful()

    finally:
        os.chdir(cwd)
        print(f"Run {run_id} finished. Logs in {run_dir}/test_results.log")


def main():
    parser = argparse.ArgumentParser(
        description="Parallel PoW simulation runs with in-process node-data tests (list sweep)"
    )
    parser.add_argument(
        "--n-nodes",
        type=int,
        nargs='+',
        required=True,
        help="List of node-counts, one per run."
    )
    parser.add_argument(
        "--max-simulation-time",
        type=float,
        nargs='+',
        required=True,
        help="List of max simulation times, one per run."
    )
    args = parser.parse_args()
    if len(args.n_nodes) != len(args.max_simulation_time):
        parser.error(
            "You must supply the same number of --n-nodes and --max-simulation-time values."
        )
    params = [(i+1, n, t) for i, (n, t) in enumerate(zip(args.n_nodes, args.max_simulation_time))]
    cpu_count = multiprocessing.cpu_count()
    pool_size = min(cpu_count, len(params))
    print(f"Launching {len(params)} jobs on up to {pool_size} cores…")

    with multiprocessing.Pool(pool_size) as pool:
        results = pool.starmap(worker, params)

    if not all(results):
        print("One or more runs failed. Check individual logs for details.")
        sys.exit(1)
    print("FINISHED - All simulations and tests complete.")

if __name__ == "__main__":
    main()

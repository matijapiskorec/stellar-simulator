import math
import unittest
from collections import defaultdict, Counter

import numpy as np

from Simulator import Simulator
from Globals import Globals
import unittest
from collections import Counter, defaultdict
from Globals import Globals
from Simulator import Simulator
from Block import Block


class TestForkRate2(unittest.TestCase):
    def setUp(self):
        # small network so test runs quickly
        self.sim_duration = 100.0
        self.n_nodes = 150
        Globals.simulation_time = 0.0

        # Initialize and run the simulator
        self.sim = Simulator(verbosity=0, n_nodes=self.n_nodes)
        self.sim._max_simulation_time = self.sim_duration
        self.sim.run()

        # Collect all seen block hashes (main chains + orphans)
        self.seen_hashes = set()
        for node in self.sim.nodes:
            self.seen_hashes |= set(node.blockchain.chain.keys())
            self.seen_hashes |= set(node.blockchain.orphans.keys())

        # Determine the ≥95%-agreed main chain
        block_counts = Counter(
            blk.hash
            for node in self.sim.nodes
            for blk in node.blockchain.get_longest_chain()
        )
        threshold = math.ceil(0.95 * self.n_nodes)
        self.main_hashes = {h for h, c in block_counts.items() if c >= threshold}

        # Compute stale blocks once, shared by both tests
        self.stale_hashes = self.seen_hashes - self.main_hashes

    def test_stale_block_rate_and_forks_per_sec(self):
        # Compute metrics
        stale_rate = len(self.stale_hashes) / len(self.seen_hashes)
        forks_per_s = len(self.stale_hashes) / self.sim_duration

        print(f"stale_rate={stale_rate:.4%}, forks/sec={forks_per_s: .7%}")

        # Assert within acceptable bounds
        self.assertLessEqual(
            stale_rate, 0.05,
            msg=f"stale rate {stale_rate:.4%} outside expected range"
        )
        self.assertGreaterEqual(
            forks_per_s, 0.001,
            msg=f"forks/sec {forks_per_s:.7%} below expected range"
        )

    def test_fork_depth_distribution(self):
        # If there are no stale blocks, skip distribution
        if not self.stale_hashes:
            self.skipTest("No stale forks to analyze")

        # Helper to compute depth of a stale block
        def compute_depth(blk):
            depth, cur = 0, blk
            while cur.hash not in self.main_hashes:
                depth += 1
                cur = self.hash_to_block[cur.prev_hash]
            return depth

        # Build a map from hash to Block instance
        self.hash_to_block = {}
        for node in self.sim.nodes:
            # 1) every block in the node's full chain store
            for h, entry in node.blockchain.chain.items():
                self.hash_to_block[h] = entry['block']
            # 2) plus anything still sitting in the orphan pool
            for orphan in node.blockchain.orphans.values():
                self.hash_to_block[orphan.hash] = orphan

        # Compute fork-depth counts
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



class TestChainAgreement(unittest.TestCase):
    def setUp(self):
        # smallish network for fast tests
        self.sim_duration = 100.0
        self.n_nodes = 100
        Globals.simulation_time = 0.0

        self.sim = Simulator(verbosity=0, n_nodes=self.n_nodes)
        self.sim._max_simulation_time = self.sim_duration

    def extract_tx_hashes(self, blk):
        # normalize to raw hash strings
        if isinstance(blk, dict):
            return blk.get("txhash_list", [])
        # else assume Block instance
        return [tx._hash for tx in blk.transactions]

    def test_common_chain_and_tx_coverage(self):
        # 1) Run the simulation
        self.sim.run()

        # 2) Extract each node’s best chain (list of block hashes)
        node_chains = [
            [blk.hash for blk in node.blockchain.get_longest_chain()]
            for node in self.sim.nodes
        ]

        # 3) Count per-block how many nodes include it
        block_counts = Counter()
        for chain in node_chains:
            block_counts.update(chain)

        # 4) Show distribution: “X blocks are in exactly k nodes’ chains”
        dist = Counter(block_counts.values())
        print("Blocks shared by k nodes:")
        for k in sorted(dist):
            print(f"  {dist[k]:4d} blocks ⟷ {k:2d} nodes")

        # 5) Pick main chain = blocks present in ≥95% of nodes
        threshold = math.ceil(0.95 * self.n_nodes)
        main_chain_hashes = {h for h, cnt in block_counts.items() if cnt >= threshold}
        print(f"\nBlocks in 95%-agreed main chain: {len(main_chain_hashes)}")

        # 6) Gather confirmed tx-hashes from unique main-chain blocks
        hash_to_block = {}
        for node in self.sim.nodes:
            for blk in node.blockchain.get_longest_chain():
                if blk.hash in main_chain_hashes:
                    hash_to_block.setdefault(blk.hash, blk)

        confirmed = set()
        for blk in hash_to_block.values():
            confirmed.update(self.extract_tx_hashes(blk))


        all_created = set() # These are all txs made over all nodes
        for node in self.sim.nodes:
            # first get all txs that are still in mempool
            all_created.update(tx._hash for tx in node.mempool.transactions)

            # all seen blocks are the blocks from longest chain and orphan chains
            for blk in node.blockchain.get_longest_chain():
                all_created.update(self.extract_tx_hashes(blk))
            for orphan_blk in node.blockchain.orphans.values():
                if isinstance(orphan_blk, Block):
                    all_created.update(self.extract_tx_hashes(orphan_blk)) # returns all txs from block as list
                else:
                    # if it's a dict, pull whatever key you actually use:
                    all_created.update(orphan_blk.get("txhash_list", []))

        if not all_created:
            self.skipTest("No transactions produced during simulation")

        print(f"\nTotal unique txs produced:  {len(all_created)}")
        print(f"Confirmed in main chain:    {len(confirmed)}")

        print("All creates is ", len(all_created))
        print("All confirmed is ", len(confirmed))
        # 8) Compute coverage
        coverage = len(confirmed) / len(all_created)
        print(f"Coverage:                   {coverage:.2%}")

        # 9) Assert a reasonable threshold
        self.assertGreater(
            coverage, 0.5,
            f"Coverage too low: only {coverage:.2%} of txs in 95%-agreed main chain."
        )








import unittest
import math
import pandas as pd
import re
from collections import Counter, defaultdict

def parse_pow_logs(file_path):
    """
    Parses ledger_logs.txt for:
      1) NODE logger mining events:
         "Node <id> mined block <hash> at height <h> with <n> txs: [<tx1>,...]"
      2) BLOCK logger creation events:
         "- BLOCK - INFO - Created Block: prev=<prev>, hash=<hash>, timestamp=<ts>, txs=[...]"
    Returns a DataFrame with columns: node (int or None), block_hash (int), txs (int), time_mined (float).
    """
    entries = []
    with open(file_path, 'r') as f:
        for line in f:
            line = line.rstrip()
            # --- 1) NODE‐mined lines ---
            if "mined block" in line and "in timestamp" in line:
                # split off the trailing simulation time
                try:
                    body, ts_str = line.rsplit(" in timestamp ", 1)
                    ts = float(ts_str)
                except ValueError:
                    # no valid “in timestamp X.Y” at end
                    continue

                m = re.search(
                    r"Node\s+(\d+).*?mined block\s+(\d+)\s+at height\s+(\d+)\s+"
                    r"with\s+(\d+)\s+txs:\s*\[(.*?)\]",
                    body
                )
                if not m:
                    continue

                node_id, blk_hash_s, height_s, n_txs, txlist = m.groups()
                entries.append({
                    "node":       int(node_id),
                    "block_hash": int(blk_hash_s),
                    "height":     int(height_s),
                    "txs":        int(n_txs),
                    "time_mined": ts,
                })
                continue

            # --- 2) BLOCK‐level creation events ---
            if "Created Block:" in line:
                m2 = re.search(
                    r"Created Block: prev=\S+, hash=(\d+), timestamp=(\d+\.\d+), txs=\[(.*?)\]",
                    line
                )
                if not m2:
                    continue
                blk_hash_s, ts_s, txlist = m2.groups()
                entries.append({
                    "node":       None,
                    "block_hash": int(blk_hash_s),
                    "height":     None,
                    "txs":        len([tx for tx in txlist.split(",") if tx.strip()]),
                    "time_mined": float(ts_s),
                })
                continue

    # force these five columns to always exist
    return pd.DataFrame(entries,
                        columns=["node", "block_hash", "height", "txs", "time_mined"])


class TestPoWSimulator(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # 1) Run the simulator once
        cls.sim_duration = 100.0
        cls.n_nodes = 50
        Globals.simulation_time = 0.0

        cls.sim = Simulator(verbosity=5, n_nodes=cls.n_nodes)
        cls.sim._max_simulation_time = cls.sim_duration
        cls.sim.run()

        # 2) Parse both NODE and BLOCK logs
        cls.mined_df = parse_pow_logs("ledger_logs.txt")

        # 3) Compute the ≥95%-agreed main chain
        block_counts = Counter(
            blk.hash
            for node in cls.sim.nodes
            for blk in node.blockchain.get_longest_chain()
        )
        cls.threshold = math.ceil(0.95 * cls.n_nodes)
        cls.main_chain_hashes = {
            h for h, c in block_counts.items() if c >= cls.threshold
        } # all block hashes agreed by 95% of nodes


        # 4) Build a map of all seen Blocks
        cls.hash_to_block = {} #map the hash back to the actual Block objects
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
        # 1) Confirmed txs in the ≥97.5% main chain
        confirmed = {
            tx
            for h, blk in self.hash_to_block.items()
            if h in self.main_chain_hashes
            for tx in self.extract_tx_hashes(blk)
        }

        # 2) All txs ever produced
        all_created = set()
        for node in self.sim.nodes:
            # mempool
            all_created.update(tx._hash for tx in node.mempool.transactions)
            # main chain
            for blk in node.blockchain.get_longest_chain():
                all_created.update(self.extract_tx_hashes(blk))
            # orphans
            for orphan in node.blockchain.orphans.values():
                if isinstance(orphan, Block):
                    all_created.update(self.extract_tx_hashes(orphan))
                else:
                    all_created.update(orphan.get("txhash_list", []))

        assert all_created, "No transactions produced during simulation"

        coverage = len(confirmed) / len(all_created)
        print(f"\nTransaction coverage: {coverage:.2%}")
        self.assertGreater(
            coverage, 0.9,
            f"Coverage too low: {coverage:.2%}"
        )

    def test_blocks_mined_per_node_and_avg_block_size(self):
        df = self.mined_df

        # If nothing parsed, warn and exit
        if df.empty or "block_hash" not in df.columns:
            print("WARNING: No mining/creation events parsed from ledger_logs.txt")
            return

        # 3) Filter to only main-chain blocks *with known node*
        df_main = df[
            df["block_hash"].isin(self.main_chain_hashes) &
            df["node"].notnull()
        ]

        # 4) Count unique blocks per node
        mined_counts = {i: 0 for i in range(self.n_nodes)}
        for _, row in df_main.drop_duplicates(["node","block_hash"]).iterrows():
            mined_counts[int(row["node"])] += 1

        print("\nBlocks per miner in main chain:")
        for node_id in range(self.n_nodes):
            print(f"  Node {node_id:2d}: {mined_counts[node_id]}")

        zeros = [i for i, cnt in mined_counts.items() if cnt == 0]
        self.assertFalse(
            zeros,
            f"Some nodes have zero main-chain blocks: {zeros}"
        )

        # 5) Average txs per main-chain block
        avg_txs = df_main.groupby("block_hash")["txs"].first().mean() if not df_main.empty else 0.0
        print(f"\nAverage txs per main-chain block: {avg_txs:.2f}")
        self.assertGreater(
            avg_txs, 0.0,
            "No transactions in main-chain blocks"
        )

    def test_fork_depth_distribution(self):
        # If there are no stale blocks, skip distribution
        if not self.stale_hashes:
            self.skipTest("No stale forks to analyze")

        # Helper to compute depth of a stale block
        def compute_depth(blk):
            # from the forked block, go back to previous block until you reach the main chain
            # then return how many blocks you had to go back to find how deep they went
            depth, cur = 0, blk
            while cur.hash not in self.main_chain_hashes:
                depth += 1
                cur = self.hash_to_block[cur.prev_hash]
            return depth

        # Build a map from hash to Block instance
        self.hash_to_block = {}
        for node in self.sim.nodes:
            # 1) every block in the node's full chain store
            for h, entry in node.blockchain.chain.items():
                self.hash_to_block[h] = entry['block']
            # 2) plus anything still sitting in the orphan pool
            for orphan in node.blockchain.orphans.values():
                self.hash_to_block[orphan.hash] = orphan

        # Compute fork-depth counts
        depth_counts = Counter(
            compute_depth(self.hash_to_block[h])
            for h in self.stale_hashes # collect all hashes and how deep they go before reaching main chain
        )

        print("\nFork-depth distribution:")
        for d, n in sorted(depth_counts.items()): # print all forks and how deep they went
            print(f"  {n:4d} forks of depth {d}")

        max_depth = max(depth_counts.keys())
        self.assertLessEqual(
            max_depth, 5,
            f"Too-deep forks: max depth {max_depth}"
        )


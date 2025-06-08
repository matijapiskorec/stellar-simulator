import math
import unittest
from collections import defaultdict, Counter
import pandas as pd
import numpy as np
import re
from Simulator import Simulator
from Globals import Globals
import unittest
from collections import Counter, defaultdict
from Globals import Globals
from Simulator import Simulator
from Block import Block


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
            # grab the timestamp at the start
            m_time = re.match(r"^(\d+\.\d+)", line)
            ts = float(m_time.group(1)) if m_time else None

            # 1) NODE-level mining event
            m1 = re.search(
                r"Node (\d+).*?mined block (\S+) at height (\d+) with (\d+) txs: \[(.*?)\]",
                line
            )
            if m1:
                node_id, blk_hash_s, _, n_txs, txlist = m1.groups()
                blk_hash = int(blk_hash_s)              # <— convert to int
                txs = [tx.strip() for tx in txlist.split(",") if tx.strip()]
                entries.append({
                    "node":       int(node_id),
                    "block_hash": blk_hash,
                    "txs":        int(n_txs),
                    "time_mined": ts # extracted timestamp from line
                })
                continue

            # 2) BLOCK-level creation event
            m2 = re.search(
                r"- BLOCK - INFO - Created Block: prev=\S+, hash=(\S+), timestamp=(\S+), txs=\[(.*?)\]",
                line
            )
            if m2:
                blk_hash_s, timestamp_s, txlist = m2.groups()
                blk_hash = int(blk_hash_s)              # <— convert to int here too
                txs = [tx.strip() for tx in txlist.split(",") if tx.strip()]
                entries.append({
                    "node":       None,
                    "block_hash": blk_hash,
                    "txs":        len(txs),
                    "time_mined": ts
                })
                continue

    return pd.DataFrame(entries)


class TestPoWSimulator(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # 1) Run the simulator once
        cls.sim_duration = 50.0
        cls.n_nodes = 200
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
        # 1) Confirmed txs in the ≥95% main chain
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
            coverage, 0.5,
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


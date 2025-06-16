from Network import Network
from Mempool import Mempool
from Log import log
import unittest
from Block import Block

from Node import Node
from Transaction import Transaction
from Blockchain import Blockchain
from unittest.mock import MagicMock, patch
from unittest import mock
from Globals import Globals
import random


class NodeTest(unittest.TestCase):
    def setup(self):
        pass

    def test_create_transaction_adds_to_mempool(self):
        self.node = Node(name="Alice")
        tx = self.node.create_transaction()

        # Check it returned a Transaction
        self.assertIsInstance(tx, Transaction)

        # Check it's in the mempool
        self.assertIn(tx, self.node.mempool.transactions)

        # Check the fee is >= 1 (from lognorm + max)
        self.assertGreaterEqual(tx.fee, 1)

    def test_create_transaction_does_not_add_duplicate(self):
        self.node = Node(name="Alice")
        # Manually create and insert a transaction with known ID
        tx1 = Transaction(fee=50)
        self.node.mempool.add_transaction(tx1)

        # Patch the method to force create the exact same txid
        original_getrandbits = random.getrandbits
        try:
            random.getrandbits = lambda _: int(tx1.hash, 16)
            tx2 = self.node.create_transaction()
        finally:
            random.getrandbits = original_getrandbits

        # Check only one instance is in the mempool
        count = sum(1 for tx in self.node.mempool.transactions if tx.hash == tx1.hash)
        self.assertEqual(count, 1)
        self.assertEqual(tx1.hash, tx2.hash)

    def test_multiple_transactions_have_unique_ids(self):
        self.node = Node(name="Alice")
        tx_ids = set()
        for _ in range(10):
            tx = self.node.create_transaction()
            self.assertNotIn(tx.hash, tx_ids)
            tx_ids.add(tx.hash)

        self.assertEqual(len(tx_ids), 10)

    def test_fee_distribution_range(self):
        self.node = Node(name="Alice")
        for _ in range(100):
            tx = self.node.create_transaction()
            self.assertGreaterEqual(tx.fee, 1)
            self.assertLess(tx.fee, 50000)  # rarely over 10k unless sigma is huge


    def test_receive_new_transactions(self):
        node_a = Node("A")
        node_b = Node("B")
        node_a.peers = [node_b]

        # Add a few txs to B's mempool
        txs = [Transaction(fee=10 * i + 1) for i in range(3)]
        for tx in txs:
            node_b.mempool.add_transaction(tx)

        node_a.receive_txs_from_peer()

        for tx in txs:
            self.assertIn(tx, node_a.mempool.transactions)

    def test_receive_only_new_transactions(self):
        node_a = Node("A")
        node_b = Node("B")
        node_a.peers = [node_b]

        tx_shared = Transaction(fee=100)
        tx_unique = Transaction(fee=200)

        node_a.mempool.add_transaction(tx_shared)
        node_b.mempool.add_transaction(tx_shared)
        node_b.mempool.add_transaction(tx_unique)

        node_a.receive_txs_from_peer()

        self.assertIn(tx_unique, node_a.mempool.transactions)
        self.assertIn(tx_shared, node_a.mempool.transactions)

        # Ensure no duplicates
        tx_ids = [tx.hash for tx in node_a.mempool.transactions]
        self.assertEqual(len(tx_ids), len(set(tx_ids)))

    def test_no_peers(self):
        node = Node("Solo")
        try:
            node.receive_txs_from_peer()
        except Exception as e:
            self.fail(f"receive_txs_from_peer() raised Exception with no peers: {e}")

    def test_peer_with_empty_mempool(self):
        node_a = Node("A")
        node_b = Node("B")
        node_a.peers = [node_b]

        self.assertEqual(len(node_b.mempool.transactions), 0)

        try:
            node_a.receive_txs_from_peer()
        except Exception as e:
            self.fail(f"receive_txs_from_peer() failed on empty mempool: {e}")

        self.assertEqual(len(node_a.mempool.transactions), 0)






    def test_mine_empty_mempool(self):
        self.node = Node(name="Miner1")
        # Initially, no blocks in the chain
        self.assertEqual(len(self.node.blockchain.chain), 0)

        block = self.node.mine()

        # Now exactly one block (genesis) should exist
        self.assertEqual(len(self.node.blockchain.chain), 1)
        # As this is the first block, prev_hash must be None
        self.assertIsNone(block.prev_hash)
        # No transactions in an empty mempool
        self.assertEqual(block.transactions, [])
        # Mempool remains empty after mining
        self.assertEqual(len(self.node.mempool.transactions), 0)

    def test_mine_single_transaction(self):
        self.node = Node(name="Miner1")
        # Add one tx to the mempool
        tx = Transaction(fee=50)
        self.node.mempool.add_transaction(tx)
        self.assertIn(tx, self.node.mempool.transactions)

        block = self.node.mine()

        # That tx should be included
        self.assertEqual(block.transactions, [tx])
        # Mempool is cleared of that tx
        self.assertNotIn(tx, self.node.mempool.transactions)
        # prev_hash still None for the first block
        self.assertIsNone(block.prev_hash)

    def test_mine_multiple_transactions_sorted(self):
        self.node = Node(name="Miner1")
        # Create several txs with distinct fees
        fees = [5, 1, 3, 4, 2]
        txs = [Transaction(fee=f) for f in fees]
        for tx in txs:
            self.node.mempool.add_transaction(tx)

        block = self.node.mine()

        # Transactions in block must be sorted by descending fee
        expected_order = sorted(txs, key=lambda t: t.fee, reverse=True)
        self.assertEqual(block.transactions, expected_order)

        # Mempool should now be empty
        self.assertEqual(self.node.mempool.transactions, [])

    def test_mine_previous_hash_chain_growth(self):
        self.node = Node(name="Miner1")
        # Mine first block
        first = self.node.mine()
        # Mine second block
        second = self.node.mine()

        # Second block's prev_hash must point to first.hash
        self.assertEqual(second.prev_hash, first.hash)

        # Chain length should now be 2
        self.assertEqual(len(self.node.blockchain.chain), 2)








    def test_processs_received_block_adds_direct_connection_to_chain(self):
        self.node = Node(name="Receiver")
        self.node.blockchain = Blockchain(self.node)
        self.peer = Node(name="Sender")
        self.peer.blockchain = Blockchain(self.peer)
        self.node.peers = [self.peer]

        # Create and add genesis to both chains
        genesis = Block(prev_hash=None, transactions=[], height=0)
        self.node.blockchain.add_block(genesis)
        self.peer.blockchain.add_block(genesis)
        self.genesis = genesis

        # Create a block extending genesis
        blk = Block(prev_hash=self.genesis.hash, transactions=[], height=1)

        # Process
        self.node.process_received_block(self.peer, blk)

        # Should end up in the main chain, not in orphans
        self.assertIn(blk.hash, self.node.blockchain.chain)
        self.assertNotIn(blk.hash, self.node.blockchain.orphans)
        # Tip should now be this block
        tip = self.node.blockchain.get_tip()
        self.assertEqual(tip.hash, blk.hash)
        self.assertEqual(tip.height, 1)

    def test_process_received_stores_orphan_block(self):
        self.node = Node(name="Receiver")
        self.node.blockchain = Blockchain(self.node)
        self.peer = Node(name="Sender")
        self.peer.blockchain = Blockchain(self.peer)
        self.node.peers = [self.peer]

        # Create and add genesis to both chains
        genesis = Block(prev_hash=None, transactions=[], height=0)
        self.node.blockchain.add_block(genesis)
        self.peer.blockchain.add_block(genesis)
        self.genesis = genesis

        # Create an orphan (parent not in chain)
        orphan = Block(prev_hash="does_not_exist", transactions=[], height=1)

        # Process
        self.node.process_received_block(self.peer, orphan)

        # Should be in orphans, not in chain
        self.assertIn(orphan.hash, self.node.blockchain.orphans)
        self.assertNotIn(orphan.hash, self.node.blockchain.chain)
        # Tip remains genesis
        tip = self.node.blockchain.get_tip()
        self.assertEqual(tip.hash, self.genesis.hash)
        self.assertEqual(tip.height, 0)





    def test_add_new_block(self):
        self.node = Node(name="Tester")
        self.node.blockchain = Blockchain(self.node)

        # Add genesis block
        self.genesis = Block(prev_hash=None, transactions=[], height=0)
        added = self.node.blockchain.add_block(self.genesis)
        self.assertTrue(added, "Genesis block must be added successfully")

        # Initial chain length is 1 (genesis)
        initial_len = len(self.node.blockchain.chain)

        # Create and add a new block extending genesis
        blk1 = Block(prev_hash=self.genesis.hash, transactions=[], height=1)
        self.node.add_block_and_update_chain(blk1)

        # Chain length increased by 1
        self.assertEqual(len(self.node.blockchain.chain), initial_len + 1)
        # Tip is now blk1
        tip = self.node.blockchain.get_tip()
        self.assertEqual(tip.hash, blk1.hash)
        # No orphans remain
        self.assertFalse(self.node.blockchain.orphans)

    def test_add_duplicate_block(self):
        self.node = Node(name="Tester")
        self.node.blockchain = Blockchain(self.node)

        # Add genesis block
        self.genesis = Block(prev_hash=None, transactions=[], height=0)
        added = self.node.blockchain.add_block(self.genesis)
        self.assertTrue(added, "Genesis block must be added successfully")

        # Add blk1 manually
        blk1 = Block(prev_hash=self.genesis.hash, transactions=[], height=1)
        self.assertTrue(self.node.blockchain.add_block(blk1))

        initial_len = len(self.node.blockchain.chain)

        # Call add_block_and_update_chain with the same block again
        self.node.add_block_and_update_chain(blk1)

        # Chain length should remain unchanged
        self.assertEqual(len(self.node.blockchain.chain), initial_len)
        # Tip should still be blk1
        tip = self.node.blockchain.get_tip()
        self.assertEqual(tip.hash, blk1.hash)
        # No orphans
        self.assertFalse(self.node.blockchain.orphans)

    def test_add_orphan_block(self):
        self.node = Node(name="Tester")
        self.node.blockchain = Blockchain(self.node)

        # Add genesis block
        self.genesis = Block(prev_hash=None, transactions=[], height=0)
        added = self.node.blockchain.add_block(self.genesis)
        self.assertTrue(added, "Genesis block must be added successfully")

        # Create an orphan (parent hash not known)
        orphan = Block(prev_hash="nonexistent", transactions=[], height=1)

        initial_len = len(self.node.blockchain.chain)

        # Attempt to add as orphan via add_block_and_update_chain
        self.node.add_block_and_update_chain(orphan)

        # Chain length remains the same
        self.assertEqual(len(self.node.blockchain.chain), initial_len)
        # Orphan appears in orphans dict
        self.assertIn(orphan.hash, self.node.blockchain.orphans)
        # Tip remains genesis
        tip = self.node.blockchain.get_tip()
        self.assertEqual(tip.hash, self.genesis.hash)


    def test_simple_reorg_adds_and_prunes(self):
            # Instantiate a fresh node and blockchain
            node = Node(name="Tester")
            node.blockchain = Blockchain(node)

            # Add genesis
            genesis = Block(prev_hash=None, transactions=[], height=0)
            assert node.blockchain.add_block(genesis)

            # Build old chain: genesis → A1(tx1) → A2(tx2)
            tx1 = Transaction(fee=10)
            a1 = Block(prev_hash=genesis.hash, transactions=[tx1], height=1)
            node.blockchain.add_block(a1)
            tx2 = Transaction(fee=20)
            a2 = Block(prev_hash=a1.hash, transactions=[tx2], height=2)
            node.blockchain.add_block(a2)
            old_tip = a2

            # Build new, longer chain: genesis → B1(tx3) → B2(tx4) → B3(tx5)
            tx3 = Transaction(fee=30)
            b1 = Block(prev_hash=genesis.hash, transactions=[tx3], height=1)
            node.blockchain.add_block(b1)
            tx4 = Transaction(fee=40)
            b2 = Block(prev_hash=b1.hash, transactions=[tx4], height=2)
            node.blockchain.add_block(b2)
            tx5 = Transaction(fee=50)
            b3 = Block(prev_hash=b2.hash, transactions=[tx5], height=3)
            node.blockchain.add_block(b3)
            new_tip = b3

            # Ensure mempool is empty before reorg
            assert node.mempool.transactions == []

            # Perform reorganization
            node.reorganize_chain(old_tip, new_tip)

            # tx1 and tx2 should be back in mempool
            self.assertIn(tx1, node.mempool.transactions)
            self.assertIn(tx2, node.mempool.transactions)
            # tx3, tx4, tx5 should not be in mempool
            self.assertNotIn(tx3, node.mempool.transactions)
            self.assertNotIn(tx4, node.mempool.transactions)
            self.assertNotIn(tx5, node.mempool.transactions)

    def test_reorg_with_shared_transaction(self):
            # Instantiate a fresh node and blockchain
            node = Node(name="Miner")
            node.blockchain = Blockchain(node)

            # Add genesis
            genesis = Block(prev_hash=None, transactions=[], height=0)
            assert node.blockchain.add_block(genesis)

            # Shared transaction for both branches
            shared = Transaction(fee=99)

            # Old chain: genesis → A1(shared) → A2(tx_old)
            a1 = Block(prev_hash=genesis.hash, transactions=[shared], height=1)
            node.blockchain.add_block(a1)
            tx_old = Transaction(fee=11)
            a2 = Block(prev_hash=a1.hash, transactions=[tx_old], height=2)
            node.blockchain.add_block(a2)
            old_tip = a2

            # New, longer chain: genesis → B1(shared) → B2(tx_new) → B3(tx_new2)
            b1 = Block(prev_hash=genesis.hash, transactions=[shared], height=1)
            node.blockchain.add_block(b1)
            tx_new = Transaction(fee=22)
            b2 = Block(prev_hash=b1.hash, transactions=[tx_new], height=2)
            node.blockchain.add_block(b2)
            tx_new2 = Transaction(fee=33)
            b3 = Block(prev_hash=b2.hash, transactions=[tx_new2], height=3)
            node.blockchain.add_block(b3)
            new_tip = b3

            # Perform reorganization
            node.reorganize_chain(old_tip, new_tip)

            # tx_old should have been returned to mempool
            self.assertIn(tx_old, node.mempool.transactions)
            # shared was in both old and new chains, so should not be in mempool
            self.assertNotIn(shared, node.mempool.transactions)
            # new-chain txs should not be in mempool
            self.assertNotIn(tx_new, node.mempool.transactions)
            self.assertNotIn(tx_new2, node.mempool.transactions)



    def test_identical_chains(self):
        node = Node("node")
        node.blockchain = Blockchain(node)

        # Build common chain: genesis → A1 → A2
        genesis = Block(prev_hash=None, transactions=[], height=0)
        a1 = Block(prev_hash=genesis.hash, transactions=[], height=1)
        a2 = Block(prev_hash=a1.hash, transactions=[], height=2)

        chain1 = [genesis, a1, a2]
        chain2 = [genesis, a1, a2]

        fork_idx = node.find_fork_point(chain1, chain2)
        self.assertEqual(fork_idx, 3)  # No divergence

    def test_fork_at_start(self):
        node = Node("node")
        node.blockchain = Blockchain(node)

        # Completely different chains
        a0 = Block(prev_hash=None, transactions=[], height=0)
        b0 = Block(prev_hash=None, transactions=[], height=0)

        chain1 = [a0]
        chain2 = [b0]

        fork_idx = node.find_fork_point(chain1, chain2)
        self.assertEqual(fork_idx, 0)

    def test_fork_in_middle(self):
        node = Node("node")
        node.blockchain = Blockchain(node)

        # Common prefix: genesis → A1
        genesis = Block(prev_hash=None, transactions=[], height=0)
        a1 = Block(prev_hash=genesis.hash, transactions=[], height=1)

        # Diverge after A1
        a2 = Block(prev_hash=a1.hash, transactions=[], height=2)
        b2 = Block(prev_hash=a1.hash, transactions=[], height=2)

        chain1 = [genesis, a1, a2]
        chain2 = [genesis, a1, b2]

        fork_idx = node.find_fork_point(chain1, chain2)
        self.assertEqual(fork_idx, 2)

    def test_chain_length_mismatch(self):
        node = Node("node")
        node.blockchain = Blockchain(node)

        # Shared chain: genesis → A1
        genesis = Block(prev_hash=None, transactions=[], height=0)
        a1 = Block(prev_hash=genesis.hash, transactions=[], height=1)

        # One chain is a prefix of the other
        chain_short = [genesis, a1]
        a2 = Block(prev_hash=a1.hash, transactions=[], height=2)
        chain_long = [genesis, a1, a2]

        fork_idx = node.find_fork_point(chain_short, chain_long)
        self.assertEqual(fork_idx, 2)  # No divergence, just shorter chain








    def test_syncs_missing_blocks_and_extends_chain(self):
        # Receiver node A and peer node B
        node_a = Node("A")
        node_b = Node("B")
        node_a.blockchain = Blockchain(node_a)
        node_b.blockchain = Blockchain(node_b)

        # Both start with genesis
        genesis = Block(prev_hash=None, transactions=[], height=0)
        node_a.blockchain.add_block(genesis)
        node_b.blockchain.add_block(genesis)

        # Peer B builds full chain: genesis → b1 → b2 → b3
        b1 = Block(prev_hash=genesis.hash, transactions=[], height=1)
        node_b.blockchain.add_block(b1)
        b2 = Block(prev_hash=b1.hash, transactions=[], height=2)
        node_b.blockchain.add_block(b2)
        b3 = Block(prev_hash=b2.hash, transactions=[], height=3)
        node_b.blockchain.add_block(b3)

        # Node A receives only b3 as orphan
        node_a.blockchain.orphans[b3.hash] = b3

        # Perform sync_missing_blocks
        node_a.sync_missing_blocks(peer=node_b, orphan_block=b3)

        # A should now have b1, b2, b3 in its chain
        for blk in (b1, b2, b3):
            self.assertIn(blk.hash, node_a.blockchain.chain)

        # Tip of A should be b3
        tip = node_a.blockchain.get_tip()
        self.assertEqual(tip.hash, b3.hash)
        self.assertEqual(tip.height, 3)

    def test_no_reorg_when_peer_chain_shorter(self):
        # Receiver node A with longer chain, peer B shorter
        node_a = Node("A")
        node_b = Node("B")
        node_a.blockchain = Blockchain(node_a)
        node_b.blockchain = Blockchain(node_b)

        # Both start with genesis
        genesis = Block(prev_hash=None, transactions=[], height=0)
        node_a.blockchain.add_block(genesis)
        node_b.blockchain.add_block(genesis)

        # Node A builds longer chain: genesis → a1 → a2 → a3
        a1 = Block(prev_hash=genesis.hash, transactions=[], height=1)
        node_a.blockchain.add_block(a1)
        a2 = Block(prev_hash=a1.hash, transactions=[], height=2)
        node_a.blockchain.add_block(a2)
        a3 = Block(prev_hash=a2.hash, transactions=[], height=3)
        node_a.blockchain.add_block(a3)
        old_tip = node_a.blockchain.get_tip()

        # Peer B builds shorter chain: genesis → b1 → b2 → b3
        b1 = Block(prev_hash=genesis.hash, transactions=[], height=1)
        node_b.blockchain.add_block(b1)
        b2 = Block(prev_hash=b1.hash, transactions=[], height=2)
        node_b.blockchain.add_block(b2)
        b3 = Block(prev_hash=b2.hash, transactions=[], height=3)
        node_b.blockchain.add_block(b3)

        # Node A receives b3 as orphan
        node_a.blockchain.orphans[b3.hash] = b3

        # Sync
        node_a.sync_missing_blocks(peer=node_b, orphan_block=b3)

        # A should have b1,b2,b3 in chain as orphans connected
        for blk in (b1, b2, b3):
            self.assertIn(blk.hash, node_a.blockchain.chain)

        # But tip remains old a3
        new_tip = node_a.blockchain.get_tip()
        self.assertEqual(new_tip.hash, old_tip.hash)
        self.assertEqual(new_tip.height, old_tip.height)







    def test_returns_all_headers_when_all_missing(self):
        node = Node("TestNode")
        node.blockchain = Blockchain(node)

        # Create 3 blocks not in node's chain
        genesis = Block(prev_hash=None, transactions=[], height=0)
        b1 = Block(prev_hash=genesis.hash, transactions=[], height=1)
        b2 = Block(prev_hash=b1.hash, transactions=[], height=2)

        headers = [genesis, b1, b2]
        missing = node.find_missing_blocks(headers)

        self.assertEqual(missing, [genesis.hash, b1.hash, b2.hash])

    def test_returns_some_missing_blocks(self):
        node = Node("TestNode")
        node.blockchain = Blockchain(node)

        # Add genesis and b1 to chain
        genesis = Block(prev_hash=None, transactions=[], height=0)
        b1 = Block(prev_hash=genesis.hash, transactions=[], height=1)
        b2 = Block(prev_hash=b1.hash, transactions=[], height=2)

        node.blockchain.add_block(genesis)
        node.blockchain.add_block(b1)

        headers = [genesis, b1, b2]
        missing = node.find_missing_blocks(headers)

        self.assertEqual(missing, [b2.hash])  # Only b2 is missing

    def test_returns_empty_when_all_known(self):
        node = Node("TestNode")
        node.blockchain = Blockchain(node)

        genesis = Block(prev_hash=None, transactions=[], height=0)
        b1 = Block(prev_hash=genesis.hash, transactions=[], height=1)

        node.blockchain.add_block(genesis)
        node.blockchain.add_block(b1)

        headers = [genesis, b1]
        missing = node.find_missing_blocks(headers)

        self.assertEqual(missing, [])  # All blocks already known

if __name__ == "__main__":
    unittest.main()

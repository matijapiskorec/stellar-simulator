# test_blockchain.py

import unittest
from Blockchain import Blockchain
from Block import Block  # Assuming you have a Block class defined as before
from Node import Node    # Dummy node for Blockchain creation
from Transaction import Transaction

class TestBlockchain(unittest.TestCase):

    def setUp(self):
        # Setup before every test
        self.node = Node(name="TestNode")
        self.blockchain = Blockchain(self.node)

    def test_initialization(self):
        """Test that blockchain initializes correctly."""
        self.assertEqual(self.blockchain.node, self.node)
        self.assertEqual(self.blockchain.chain, {})
        self.assertEqual(self.blockchain.orphans, {})
        self.assertIsInstance(self.blockchain.chain, dict)
        self.assertIsInstance(self.blockchain.orphans, dict)

    def test_add_block_genesis(self):
        """Adding a Genesis block should succeed."""
        tx = Transaction(fee=10)
        genesis_block = Block(prev_hash=None, transactions=[tx])
        result = self.blockchain.add_block(genesis_block)
        self.assertTrue(result)
        self.assertIn(genesis_block.hash, self.blockchain.chain)
        self.assertEqual(self.blockchain.chain[genesis_block.hash]['block'], genesis_block)
        self.assertEqual(self.blockchain.chain[genesis_block.hash]['children'], [])

    def test_add_block_duplicate_genesis(self):
        """Adding the same Genesis block twice should fail."""
        genesis_block = Block(prev_hash=None, transactions=[Transaction()])
        result1 = self.blockchain.add_block(genesis_block)
        result2 = self.blockchain.add_block(genesis_block)
        self.assertTrue(result1)
        self.assertFalse(result2)

    def test_add_block_normal(self):
        """Adding a child block under a known parent should succeed."""
        genesis_block = Block(prev_hash=None, transactions=[Transaction(fee=1)])
        self.blockchain.add_block(genesis_block)

        child_block = Block(prev_hash=genesis_block.hash, transactions=[])
        result = self.blockchain.add_block(child_block)
        self.assertTrue(result)
        self.assertIn(child_block.hash, self.blockchain.chain)
        self.assertIn(child_block.hash, self.blockchain.chain[genesis_block.hash]['children'])

    def test_add_block_orphan(self):
        """Adding a block with unknown parent should be stored as orphan."""
        orphan_block = Block(prev_hash="nonexistent_hash", transactions=[Transaction(fee=5)])
        result = self.blockchain.add_block(orphan_block)
        self.assertTrue(result)
        self.assertIn(orphan_block.hash, self.blockchain.orphans)


    # Continuing in test_blockchain.py

    def test_connect_orphans_positive(self):
        """Orphan block connects when parent arrives."""
        # Create a transaction and orphan block (child whose parent does not exist yet)
        tx = Transaction(fee=5)
        orphan_block = Block(prev_hash='missing_parent', transactions=[tx])

        # Add orphan block (should be stored as orphan)
        self.blockchain.add_block(orphan_block)
        self.assertIn(orphan_block.hash, self.blockchain.orphans)

        # Now create the missing parent block
        parent_block = Block(prev_hash=None, transactions=[])  # Genesis
        parent_block._hash = 'missing_parent'  # Force its hash to match what orphan expected!

        # Add parent block — orphan should automatically connect
        self.blockchain.add_block(parent_block)

        # Assertions
        self.assertIn(parent_block.hash, self.blockchain.chain)
        self.assertIn(orphan_block.hash, self.blockchain.chain)
        self.assertNotIn(orphan_block.hash, self.blockchain.orphans)
        self.assertIn(orphan_block.hash, self.blockchain.chain[parent_block.hash]['children'])

    def test_connect_orphans_negative(self):
        """No orphan connects if unrelated parent arrives."""
        tx = Transaction(fee=5)
        orphan_block = Block(prev_hash='missing_parent', transactions=[tx])

        # Add orphan block
        self.blockchain.add_block(orphan_block)
        self.assertIn(orphan_block.hash, self.blockchain.orphans)

        # Add a completely unrelated parent (wrong hash)
        unrelated_parent = Block(prev_hash=None, transactions=[])

        self.blockchain.add_block(unrelated_parent)

        # Orphan should still remain in orphans
        self.assertIn(orphan_block.hash, self.blockchain.orphans)
        self.assertNotIn(orphan_block.hash, self.blockchain.chain)

    def test_get_chain_positive(self):
        """get_chain returns full chain from genesis to tip."""
        # Create genesis block
        genesis_block = Block(prev_hash=None, transactions=[])
        self.blockchain.add_block(genesis_block)

        # Create child block
        child_block = Block(prev_hash=genesis_block.hash, transactions=[])
        self.blockchain.add_block(child_block)

        # Create grandchild block
        grandchild_block = Block(prev_hash=child_block.hash, transactions=[])
        self.blockchain.add_block(grandchild_block)

        # Retrieve chain from tip
        chain = self.blockchain.get_chain(grandchild_block.hash)

        # Assertions
        self.assertEqual(len(chain), 3)
        self.assertEqual(chain[0], genesis_block)
        self.assertEqual(chain[1], child_block)
        self.assertEqual(chain[2], grandchild_block)

    def test_get_chain_negative(self):
        """get_chain returns empty list if tip_hash is unknown."""
        unknown_hash = 'nonexistent_block_hash'
        chain = self.blockchain.get_chain(unknown_hash)
        self.assertEqual(chain, [])



    def test_get_leaf_hashes_empty(self):
        """No blocks → no leaf hashes."""
        self.assertEqual(self.blockchain.get_leaf_hashes(), [])

    def test_get_leaf_hashes_single(self):
        """Single genesis → itself is the only leaf."""
        genesis = Block(prev_hash=None, transactions=[])
        self.blockchain.add_block(genesis)

        leaves = self.blockchain.get_leaf_hashes()
        self.assertEqual(leaves, [genesis.hash])

    def test_get_leaf_hashes_fork(self):
        """Two children of genesis → both are leaves."""
        genesis = Block(prev_hash=None, transactions=[])
        self.blockchain.add_block(genesis)

        child1 = Block(prev_hash=genesis.hash, transactions=[])
        child2 = Block(prev_hash=genesis.hash, transactions=[])
        self.blockchain.add_block(child1)
        self.blockchain.add_block(child2)

        leaves = set(self.blockchain.get_leaf_hashes())
        self.assertSetEqual(leaves, {child1.hash, child2.hash})




    # --- Tests for get_longest_chain() ---

    def test_get_longest_chain_empty(self):
        """No blocks → empty longest-chain list."""
        self.assertEqual(self.blockchain.get_longest_chain(), [])

    def test_get_longest_chain_single(self):
        """Single genesis → chain is [genesis]."""
        genesis = Block(prev_hash=None, transactions=[])
        self.blockchain.add_block(genesis)

        chain = self.blockchain.get_longest_chain()
        self.assertEqual(chain, [genesis])

    def test_get_longest_chain_simple_fork(self):
        """ Fork with one branch longer → that branch wins."""
        # Build fork: A → B → D  and  A → C
        A = Block(prev_hash=None, transactions=[Transaction()])
        self.blockchain.add_block(A)

        B = Block(prev_hash=A.hash, transactions=[Transaction()])
        C = Block(prev_hash=A.hash, transactions=[Transaction()])
        self.blockchain.add_block(B)
        self.blockchain.add_block(C)

        D = Block(prev_hash=B.hash, transactions=[Transaction()])
        self.blockchain.add_block(D)

        longest = self.blockchain.get_longest_chain()
        # Expect [A, B, D]
        self.assertEqual(longest, [A, B, D])

    def test_get_longest_chain_tie(self):
        """
        Two equal-length forks → returns one of them.
        We assert only that its length matches the fork length.
        """
        A = Block(prev_hash=None, transactions=[Transaction()])
        self.blockchain.add_block(A)

        B = Block(prev_hash=A.hash, transactions=[Transaction()])
        C = Block(prev_hash=A.hash, transactions=[Transaction()])
        self.blockchain.add_block(B)
        self.blockchain.add_block(C)

        longest = self.blockchain.get_longest_chain()
        # Both forks are length 2; we don’t care which one wins here, only that length=2
        self.assertEqual(len(longest), 2)
        self.assertEqual(longest[0], A)
        self.assertIn(longest[1], {B, C})




    def test_empty_chain(self):
        self.node = Node("node1")
        self.node.blockchain = Blockchain(self.node)
        # No blocks yet → tip is None
        self.assertIsNone(self.node.blockchain.get_tip())

    def test_single_genesis(self):
        self.node = Node("node1")
        self.node.blockchain = Blockchain(self.node)
        genesis = Block(prev_hash=None, transactions=[], height=0)
        self.assertTrue(self.node.blockchain.add_block(genesis))
        tip = self.node.blockchain.get_tip()
        self.assertIsNotNone(tip)
        self.assertEqual(tip.hash, genesis.hash)
        self.assertEqual(tip.height, 0)

    def test_sequential_blocks(self):
        self.node = Node("node1")
        self.node.blockchain = Blockchain(self.node)

        # Genesis → height 0
        genesis = Block(prev_hash=None, transactions=[], height=0)
        self.node.blockchain.add_block(genesis)

        # Next block → height 1
        blk1 = Block(prev_hash=genesis.hash, transactions=[], height=1)
        self.node.blockchain.add_block(blk1)
        tip1 = self.node.blockchain.get_tip()
        self.assertEqual(tip1.hash, blk1.hash)
        self.assertEqual(tip1.height, 1)

        # Next block → height 2
        blk2 = Block(prev_hash=blk1.hash, transactions=[], height=2)
        self.node.blockchain.add_block(blk2)
        tip2 = self.node.blockchain.get_tip()
        self.assertEqual(tip2.hash, blk2.hash)
        self.assertEqual(tip2.height, 2)

    def test_branching_chain(self):
        self.node = Node("node1")
        self.node.blockchain = Blockchain(self.node)
        genesis = Block(prev_hash=None, transactions=[], height=0)
        self.node.blockchain.add_block(genesis)

        # Branch A: height 1
        blkA = Block(prev_hash=genesis.hash, transactions=[], height=1)
        self.node.blockchain.add_block(blkA)

        # Branch B: also height 1 (fork)
        blkB = Block(prev_hash=genesis.hash, transactions=[], height=1)
        self.node.blockchain.add_block(blkB)
        # Tip should be blkA (first inserted at that height)
        tip1 = self.node.blockchain.get_tip()
        self.assertEqual(tip1.hash, blkA.hash)

        # Extend branch B to height 2
        blkB2 = Block(prev_hash=blkB.hash, transactions=[], height=2)
        self.node.blockchain.add_block(blkB2)
        tip2 = self.node.blockchain.get_tip()
        self.assertEqual(tip2.hash, blkB2.hash)
        self.assertEqual(tip2.height, 2)

    def test_ignores_orphans(self):
        self.node = Node("node1")
        self.node.blockchain = Blockchain(self.node)
        genesis = Block(prev_hash=None, transactions=[], height=0)
        self.node.blockchain.add_block(genesis)

        # Create an orphan with no known parent
        orphan = Block(prev_hash="nonexistent", transactions=[], height=10)
        self.node.blockchain.add_block(orphan)

        # Tip remains genesis
        tip = self.node.blockchain.get_tip()
        self.assertEqual(tip.hash, genesis.hash)
        self.assertEqual(tip.height, 0)






    def build_chain(self, length):
        """Helper: create a linear chain of given length (heights 0..length-1)."""
        self.node = Node(name="node1")
        self.node.blockchain = Blockchain(self.node)
        prev = None
        blocks = []
        for h in range(length):
            blk = Block(
                prev_hash=(prev.hash if prev else None),
                transactions=[],
                height=h
            )
            self.node.blockchain.add_block(blk)
            blocks.append(blk)
            prev = blk
        return blocks

    def test_get_locator_for_empty_chain(self):
        self.node = Node(name="node1")
        self.node.blockchain = Blockchain(self.node)
        # No blocks ⇒ locator is empty
        self.assertEqual(self.node.blockchain.get_locator(), [])

    def test_get_locator_for_single_block(self):
        self.node = Node(name="node1")
        self.node.blockchain = Blockchain(self.node)
        # Only genesis
        blocks = self.build_chain(1)
        expected = [blocks[0].hash]
        self.assertEqual(self.node.blockchain.get_locator(), expected)

    def test_get_locator_for_two_blocks(self):
        self.node = Node(name="node1")
        self.node.blockchain = Blockchain(self.node)
        # Heights [0,1] ⇒ locator indices [1,0]
        blocks = self.build_chain(2)
        expected = [blocks[1].hash, blocks[0].hash]
        self.assertEqual(self.node.blockchain.get_locator(), expected)

    def test_get_locator_for_chain_length_8(self):
        self.node = Node(name="node1")
        self.node.blockchain = Blockchain(self.node)
        # Heights 0..7 ⇒ expected locator hashes at indices [7,6,4,0]
        blocks = self.build_chain(8)
        expected = [
            blocks[7].hash,
            blocks[6].hash,
            blocks[4].hash,
            blocks[0].hash,
        ]
        self.assertEqual(self.node.blockchain.get_locator(), expected)

    def test_get_locator_for_chain_length_15(self):
        self.node = Node(name="node1")
        self.node.blockchain = Blockchain(self.node)
        # Heights 0..14 ⇒ indices [14,13,11,7]
        blocks = self.build_chain(15)
        expected = [
            blocks[14].hash,
            blocks[13].hash,
            blocks[11].hash,
            blocks[7].hash,
        ]
        self.assertEqual(self.node.blockchain.get_locator(), expected)

    def test_locator_max_entries_and_decreasing(self):
        self.node = Node(name="node1")
        self.node.blockchain = Blockchain(self.node)
        # Build a longer chain; locator length ≤ 10 and indices strictly decreasing
        blocks = self.build_chain(100)
        loc = self.node.blockchain.get_locator()
        self.assertTrue(1 <= len(loc) <= 10)
        # First entry is the tip
        self.assertEqual(loc[0], blocks[-1].hash)
        # Ensure the sequence of indices is strictly decreasing
        indices = [next(i for i,b in enumerate(blocks) if b.hash == h) for h in loc]
        self.assertEqual(indices, sorted(indices, reverse=True))






    def test_empty_chain_returns_empty(self):
        self.node = Node(name="tester")
        self.node.blockchain = Blockchain(self.node)

        # No blocks at all
        headers = self.node.blockchain.get_headers(locator=[])
        self.assertEqual(headers, [])

    def test_locator_not_found_returns_full_chain(self):
        self.node = Node(name="tester")
        self.node.blockchain = Blockchain(self.node)

        # Build chain of 5 blocks
        blocks = self.build_chain(5)
        # Locator contains a hash not in chain
        headers = self.node.blockchain.get_headers(locator=["unknown_hash"])
        # Should return all blocks in order of longest_chain (genesis→tip)
        expected = blocks  # all blocks
        self.assertEqual(headers, expected)

    def test_locator_at_tip_returns_empty(self):
        self.node = Node(name="tester")
        self.node.blockchain = Blockchain(self.node)

        blocks = self.build_chain(3)  # heights 0,1,2
        locator = [blocks[-1].hash]   # tip hash
        headers = self.node.blockchain.get_headers(locator=locator)
        # Nothing beyond tip
        self.assertEqual(headers, [])

    def test_locator_at_genesis_returns_rest(self):
        self.node = Node(name="tester")
        self.node.blockchain = Blockchain(self.node)

        blocks = self.build_chain(4)  # heights 0,1,2,3
        locator = [blocks[0].hash]    # genesis hash
        headers = self.node.blockchain.get_headers(locator=locator)
        # Should return blocks[1:]
        self.assertEqual(headers, blocks[1:])

    def test_locator_mid_chain(self):
        self.node = Node(name="tester")
        self.node.blockchain = Blockchain(self.node)

        blocks = self.build_chain(10)
        # pick block at height 5
        locator = [blocks[5].hash]
        headers = self.node.blockchain.get_headers(locator=locator)
        # expect blocks[6:10]
        self.assertEqual(headers, blocks[6:])

    def test_multiple_locator_entries(self):
        self.node = Node(name="tester")
        self.node.blockchain = Blockchain(self.node)

        blocks = self.build_chain(8)
        # locator list has unknown, then block4, then block2
        locator = ["bad", blocks[4].hash, blocks[2].hash]
        headers = self.node.blockchain.get_headers(locator=locator)
        # should match blocks[4], so start=5
        self.assertEqual(headers, blocks[5:])

    def test_max_2000_limit(self):
        self.node = Node(name="tester")
        self.node.blockchain = Blockchain(self.node)

        # build chain longer than 2000
        blocks = self.build_chain(2050)
        # locator at height 0 (genesis)
        locator = [blocks[0].hash]
        headers = self.node.blockchain.get_headers(locator=locator)
        # should return next 2000 blocks: blocks[1:2001]
        self.assertEqual(headers, blocks[1:2001])
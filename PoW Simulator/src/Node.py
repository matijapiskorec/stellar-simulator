"""
=========================
Node
=========================

Author: Matija Piskorec, Jaime de Vivero Woods

Last update: May 2025

Node class.

"""
import random
import time

import numpy as np
from Log import log
from Event import Event
from Blockchain import Blockchain
from Block import Block
from Mempool import Mempool
from Globals import Globals
import copy
from Transaction import Transaction

FEE_MEAN_LOG = 3.5      # log‑normal parameters → heavy‑tailed fee distribution
FEE_SIGMA    = 1.2
class Node():
    name = None
    hashrate = None
    ledger = None
    mempool = None
    nomination_round = None

    def __init__(self, name, blockchain=None, mempool=None, hash_rate=1.0):
        self.name = name
        self.blockchain = blockchain if blockchain is not None else Blockchain(self)
        self.slot = 1
        self.hash_rate = hash_rate
        self.mempool = mempool if mempool is not None else Mempool()
        self.peers = []

        # Internal state
        self.received_blocks = set()      # track known block hashes
        self.received_transactions = set()# track known tx hashes
        self.orphan_pool = {}              # optional, in addition to blockchain.orphans

        self.broadcast_flags = []  # Add every message here for other
        self.received_broadcast_msgs = {} # This hashmap (or dictionary) keeps track of all Messages retrieved by each node

        log.node.info('Initialized node %s: blockchain=%s, mempool=%s, hash_rate=%.2f',
                      self.name,
                      self.blockchain,
                      self.mempool,
                      self.hash_rate)

        self.log_path = 'simulator_events_log.txt'

    def __repr__(self):
        return '[Node: %s]' % self.name

    def __eq__(self, name):
        return self.name == name

    # To make Node hashable so that we can store them in a Set or as keys in dictionaries.
    def __hash__(self):
        return hash(self.name)

    # TODO: Not really used now, but just to show that we can have node specific events.
    @classmethod
    def get_events(cls):
        events = [Event('node')]
        log.consensus.info('Sending Node events %s.' %events)
        return events

    def attach_mempool(self, mempool):
        self.mempool = mempool
        return

    def add_peer(self, other: "Node"):
        if other is not self and other not in self.peers:
            self.peers.append(other)


    #### LOGGER FUNCTION
    def log_to_file(self, message):
        with open(self.log_path, 'a') as log_file:
            log_file.write(f"{Globals.simulation_time:.2f} - {message}\n")



    def create_transaction(self) -> Transaction:
        """
        Generate a tx, push it to the mempool, and set a fee equal to
        A log-normal distribution models real-world variables that:

        Are strictly positive (no negative fees),
        Have many small values and a few very large ones,

        Result from multiplicative effects"""
        # 1. Choose a random fee
        fee = max(1, int(random.lognormvariate(FEE_MEAN_LOG, FEE_SIGMA)))

        # 2. Build the Transaction object
        tx = Transaction(fee=fee, timestamp=Globals.simulation_time)
        #tx = Transaction(fee=fee)

        # 3. Insert into local mempool (if duplicate, skip)
        if self.mempool.add_transaction(tx):
            log.node.info("Node %s added new tx %s with fee %s sat",
                          self.name, tx._hash, tx.fee)
            self.log_to_file(f"NODE - INFO - Node {self.name}added new tx {tx._hash} with fee {tx.fee }sat")
        else:
            log.node.debug("Node %s skipped duplicate tx %s",
                           self.name, tx._hash)
            self.log_to_file(f"NODE - INFO - Node {self.name} skipped duplicate tx {tx._hash}")

        return tx


    def receive_txs_from_peer(self):
        """
        receive txs from a peer -> sending node's mempool should be copied and txs not matching should be added
        maybe add a randomised delay ~ delay = rng.exponential(mean=0.05) or store delay avg per node edges
        """
        if not self.peers:
            log.node.warning("Node %s has no peers to receive transactions from", self.name)
            self.log_to_file(f"NODE - WARNING - Node {self.name} has no peers to receive transactions from")
            return

        # 1. Select a random peer
        peer = random.choice(self.peers)
        log.node.info("Node %s pulls txs from peer %s", self.name, peer.name)
        self.log_to_file(f"NODE - INFO - Node {self.name} pulls txs from peer {peer.name}")

        log.node.critical("Node %s pulls txs from peer %s", self.name, peer.name)
        self.log_to_file(f"NODE - CRITICAL - Node {self.name} pulls txs from peer {peer.name}")

        # 2. Simulate network delay (can be expanded later)
        #delay = random.expovariate(1 / 0.05)  # mean 50ms
        #log.node.debug("Simulated delay: %.4f sec for tx transfer", delay)

        # 3. Get all txs from peer's mempool
        peer_txs = peer.mempool.get_all_transactions()

        # 4. Insert only new txs
        added_count = 0
        for tx in peer_txs:
            if self.mempool.add_transaction(tx):
                added_count += 1

        log.node.info("Node %s received %d new txs from %s",
                      self.name, added_count, peer.name)
        self.log_to_file(f"NODE - INFO - Node {self.name} received {added_count} new txs from {peer.name}. Mempool now has size {len(self.mempool.transactions)}")

    def mine(self):
        "Pick top X txs by fee to fill a block - 3000 txs per block (ARBITRARY NUMBER)"
        # Step 1: Retrieve txs from mempool based on fees
        # block size limit is 1mb, assume each tx is 100byte, so max 1000txs per block

        # Step 2: Retrieve the current blockchain tip
        # use hash of current blockchain tip as the previous block hash for the new block to be created
        # Create the new block with previous hash and the selected transactions to it

        # Step 3: Update local Blockchain and Mempool
        # Add new block as tip to chain
        # Remove transactions from mempool
        # 1) Select transactions by descending fee

        # TODO: Add randomised difficulty for different speeds of mine?
        # if random.random() < (node.hashrate / total_hashrate):
        #     mine
        #     block
        # TODO: ADD RANDOMISED TIME DELAY TO LOWER ORPHAN RATE??

        MAX_TXS = 1000
        # Sort by fee-per-byte; here tx.size == 100 so equivalent to fee alone
        sorted_txs = sorted(
            self.mempool.transactions,
            key=lambda tx: tx.fee,
            reverse=True
        )
        selected = sorted_txs[:MAX_TXS]

        # 2) Get the previous hash from the current tip
        tip = self.blockchain.get_tip()
        new_height = (tip.height + 1) if tip else 0
        prev_hash = tip.hash if tip else None

        # 3) Create the new block
        new_block = Block(
            prev_hash=prev_hash,
            transactions=selected,
            height=new_height
        )

        # 4) Add to local blockchain
        added = self.blockchain.add_block(new_block)
        if not added:
            log.node.warning("Node %s: failed to add new block %s", self.name, new_block.hash)
            self.log_to_file(f"NODE - WARNING - Node {self.name} failed to add new block {new_block.hash}")

        # 5) Remove selected txs from mempool
        for tx in selected:
            try:
                self.mempool.transactions.remove(tx)
            except ValueError: # just in case
                log.node.error("Node %s: tx %s missing from mempool during prune", self.name, tx.hash)
                self.log_to_file(f"NODE - ERROR - Node {self.name}: tx {tx.hash} missing from mempool during prune")

        log.node.info(
            "Node %s mined block %s at height %d with %d txs: [%s] in timestamp %s", self.name,
            self.name,
            new_block.hash,
            new_block.height,
            len(selected),
            ", ".join(tx.hash for tx in selected),
            Globals.simulation_time
        )
        self.log_to_file(
            f'NODE - INFO - Node {self.name}: mined block {new_block.hash} '
            f'at height {new_block.height} with {len(selected)} txs: '
            f'[{", ".join(tx.hash for tx in selected)}]'
            f"in timestamp {Globals.simulation_time:.3f}"
        )

        log.node.critical(
            "Node %s mined block %s at height %d with %d txs: [%s] in timestamp %s", self.name,
            self.name,
            new_block.hash,
            new_block.height,
            len(selected),
            ", ".join(tx.hash for tx in selected),
            Globals.simulation_time
        )
        self.log_to_file(
            f'NODE - CRITICAL - Node {self.name}: mined block {new_block.hash} '
            f'at height {new_block.height} with {len(selected)} txs: '
            f'[{", ".join(tx.hash for tx in selected)}]'
            f"in timestamp {Globals.simulation_time:.3f}"
        )

        return new_block


    def receive_block_from_peer(self):
        """retrieve a block from a peer-> sending node's mempool should be copied and if not matching should be added
        maybe add a randomised delay ~ delay = rng.exponential(mean=0.05) or store delay avg per node edges"""

        """
        When a Bitcoin node receives a new block, it does the following:
        1. Checks if the block directly connects to the current tip (previous hash matches).
        1.1If it does, the node adds it directly to its canonical chain.
        
        1.2 If it doesn't, the node will:
        1.2.1 Store it temporarily (as an orphan) if the parent block is unknown.
        1.2.2 Request missing blocks using getheaders, then getdata, to reconstruct the complete chain.
        1.2.3 Once missing blocks arrive, the node checks if the newly obtained chain is longer (heavier work) than its current main chain.
        
        1.2.4 If the new chain is longer, the node performs a chain reorganization:
        1.2.5 It discards blocks from the old chain back to the fork point.
        1.2.6 It adopts the newly discovered longer chain.
        1.2.7 Transactions from discarded blocks are re-added to the mempool if not confirmed in the new chain.
        """
        if not self.peers:
            log.node.warning("Node %s has no peers.", self.name)
            return

        # 1. Get random peer and tip block
        peer = random.choice(self.peers)
        peer_tip_block = peer.blockchain.get_tip()

        if peer_tip_block is None:
            log.node.info("Peer %s has no blocks.", peer.name)
            self.log_to_file(f"NODE - INFO - Peer {peer.name} has no blocks")

            return

        self.process_received_block(peer, peer_tip_block)

        # 2. Simulate latency
        #delay = random.expovariate(1 / 0.05)
        #log.node.debug("Simulated delay: %.4f sec", delay)


    def process_received_block(self, peer, block):
        """ Checks if the block directly connects to the current tip
        (previous hash matches). If it does, the node adds it directly
        to its canonical chain.

        If it doesn't, the node stores it as orphan until parent block
        is known, calls getheaders to sync the missing parent blocks,
        if the new block with missing parents is longer then that one
        is set as the current main chain
        """
        if block.prev_hash in self.blockchain.chain:
            log.node.info("Node %s received directly connectable block %s", self.name, block.hash)
            self.log_to_file(f"NODE - INFO - Node {self.name} received directly connectable block {block.hash}")

            log.node.critical("Node %s received directly connectable block %s", self.name, block.hash)
            self.log_to_file(f"NODE - CRITICAL - Node {self.name} received directly connectable block {block.hash}")

            self.add_block_and_update_chain(block)


        else:
            log.node.info("Node %s received orphan block %s; requesting missing blocks...", self.name, block.hash)
            self.log_to_file(f"NODE - INFO - Node {self.name} received orphan block {block.hash}")
            self.blockchain.orphans[block.hash] = block
            self.sync_missing_blocks(peer, block)

    def add_block_and_update_chain(self, block):
        """Add a block and update canonical chain if needed."""
        added = self.blockchain.add_block(block) # add block to blockchain
        if added: # Track new chain vs old chain to make sure it has the most work
            old_tip = self.blockchain.get_tip() # get current tip after adding
            new_longest_chain = self.blockchain.get_longest_chain() #check what the longest chain is
            new_tip = new_longest_chain[-1]

            if new_tip.hash != old_tip.hash: # If the new heaviest‐chain tip isn’t the same as the tip you were using, you’ve discovered a heavier fork
                self.reorganize_chain(old_tip, new_tip) # roll back the blocks from old_tip to the fork point and adopt the blocks up to new_tip
        else: # False is only returned if its a duplicate Block
            log.node.debug("Block %s already known, skipping", block.hash)
            self.log_to_file(f"NODE - DEBUG - Block {block.hash} already known, skipping")

    def reorganize_chain(self, old_tip, new_tip):
        """Perform chain reorganization, this occurs when a node receives
        a longer chain than the one it was previously using.
        It performs three key steps:

        1. Identifies the fork point between the old and new chains.

        2. Rolls back transactions from blocks being abandoned (old chain
        after fork) and returns them to the mempool.

        3. Removes confirmed transactions from the mempool that are already
        included in the new adopted chain."""
        old_chain = self.blockchain.get_chain(old_tip.hash)
        new_chain = self.blockchain.get_chain(new_tip.hash)

        fork_idx = self.find_fork_point(old_chain, new_chain)

        removed_blocks = old_chain[fork_idx:]
        added_blocks = new_chain[fork_idx:]

        # Revert transactions from removed blocks to mempool
        for blk in removed_blocks:
            for tx in blk.transactions:
                if tx not in self.mempool.transactions:
                    self.mempool.add_transaction(tx) # add txs back into mempool

        # Remove confirmed transactions in the newly adopted blocks
        for blk in added_blocks:
            for tx in blk.transactions:
                if tx in self.mempool.transactions:
                    self.mempool.transactions.remove(tx)

        log.node.info("Node %s reorganized chain: old tip=%s new tip=%s",
                      self.name, old_tip.hash, new_tip.hash)
        self.log_to_file(f"NODE - INFO - Node {self.name.hash} reorganized chain: old tip={old_tip.hash} new tip={new_tip.hash}")

        log.node.critical("Node %s reorganized chain: old tip=%s new tip=%s",
                      self.name, old_tip.hash, new_tip.hash)
        self.log_to_file(f"NODE - CRITICAL - Node {self.name.hash} reorganized chain: old tip={old_tip.hash} new tip={new_tip.hash}")

    def find_fork_point(self, old_chain, new_chain):
        """Find index at which two chains differentiate

        Loop over both chains, comparing their hashes
        Zip iterates over both at the same time (instead of for inside for)
        When a different hash is found, the index of the point, i,
        is returned.
        If no difference is found, then the mismatch is the end of the shorter
        chain out of the 2
        """
        for i, (blk_old, blk_new) in enumerate(zip(old_chain, new_chain)):
            if blk_old.hash != blk_new.hash:
                return i
        return min(len(old_chain), len(new_chain))

    def sync_missing_blocks(self, peer, orphan_block):
        """Fetch missing headers and blocks from peer.
        This allows a node to repair its local blockchain when
        it receives an orphan block — i.e., a block whose parent
        is unknown or missing locally"""

        headers = peer.blockchain.get_headers(locator=self.blockchain.get_locator())  # This returns a sequence of block headers (full blocks in this case) from the peer starting after the latest known block.
        missing_blocks = self.find_missing_blocks(headers) # call find_missing_blocks(headers) to figure out which of those peer blocks it doesn't have

        for blk_hash in missing_blocks: # For each missing block, it fetches it from the peer and adds it to its local blockchain
            blk = peer.blockchain.get_block(blk_hash)
            if blk:
                self.blockchain.add_block(blk)

        # # After adding blocks, the node compares its previous tip (old_tip) to the new tip (new_tip)
        old_tip = self.blockchain.get_tip()
        new_tip = self.blockchain.get_longest_chain()[-1]
        if new_tip.height > old_tip.height: # After adding blocks, the node compares its previous tip (old_tip) to the new tip (new_tip)
            self.reorganize_chain(old_tip, new_tip) # If the peer's chain is longer, the node switches to the longer chain, as per the longest chain rule in PoW.

    def find_missing_blocks(self, headers):
        """Identify missing blocks from headers.
        Take a list of Block instances (typically headers
        received from a peer) and returns a list of block hashes
        that the current node’s blockchain does not yet know about"""
        missing = []
        for header in headers:
            if header.hash not in self.blockchain.chain:
                missing.append(header.hash)
        return missing



"""
=========================
Blockchain
=========================

Author: Jaime de Vivero Woods
Last update: June 2025

Blockchain class.
"""

from Log import log
import numpy as np

class Blockchain():

    def __init__(self,node):
        self._transactions = []
        self.node = node
        self.chain = {} # Map block hash to Block
        self.orphans = {}

        log.blockchain.info('Initialized ledger for node %(node)s!' % self.__dict__)

    def __repr__(self):
        return f"[Blockchain for Node {self.node.name}, blocks={len(self.chain)}]"

    def add_block(self, block):
        """
        Add a block to the chain. Handles genesis, forks, orphans, and re-orgs.
        Returns True if block processed (even if orphaned), False if duplicate.
        """
        # Check if this block is the Genesis block
        if block.prev_hash is None:
            if block.hash in self.chain:
                log.blockchain.warning('Node %s: genesis block already exists', self.node.name)
                return False
            self.chain[block.hash] = {'block': block, 'children': []}
            log.blockchain.info('Node %s: genesis block %s added', self.node.name, block.hash)
            # There might be an orphan block waiting to connect to this genesis block
            self._connect_orphans(block.hash)
            return True

        if block.hash in self.chain:  # Duplicate check
            log.blockchain.debug('Node %s: block %s already known', self.node.name, block.hash)
            return False

        # If the block's previous hash hasn't been seen, set it as orphan until the parent arrives
        if block.prev_hash not in self.chain:
            self.orphans[block.hash] = block
            log.blockchain.info(
                'Node %s: orphaned block %s (missing parent %s)',
                self.node.name, block.hash, block.prev_hash
            )
            return True

        # Normal block additio - If parent block exists:
        # 1. update the parent's list of children
        # 2. Insert the new block in self.chain with no children
        # 3. Check if there are any orphan blocks waiting for the newly uploaded block and add orphan to chain if so
        parent_entry = self.chain[block.prev_hash]
        parent_entry['children'].append(block.hash)
        self.chain[block.hash] = {'block': block, 'children': []}
        log.blockchain.info(
            'Node %s: added block %s under parent %s',
            self.node.name, block.hash, block.prev_hash
        )

        # Connect any waiting orphans
        self._connect_orphans(block.hash)
        return True

    def _connect_orphans(self, parent_hash):
        """
        Recursively attach orphans whose parent has just been added.
        """
        # Find all orphans that have referenced the parent_hash passed as a param and add their hashes to a list
        to_connect = [h for h, blk in self.orphans.items() if blk.prev_hash == parent_hash]
        for h in to_connect:
            orphan = self.orphans.pop(h) # remove block from orphan list
            self.add_block(orphan) # add block into main chain

    def get_chain(self, tip_hash):
        """
        Return the chain (list of Blocks) from genesis to the given tip.
        """
        chain = []
        current = self.chain.get(tip_hash)
        while current is not None:
            block = current['block']
            chain.append(block)
            prev = block.prev_hash
            current = self.chain.get(prev)
        return list(reversed(chain)) # reverse list to go from genesis to tip, instead of tip to genesis

    def get_leaf_hashes(self):
        """
        Return hashes of blocks with no children (true leaf nodes).
        """
        return [
            h for h, entry in self.chain.items()
            if not entry['children']
        ]

    def get_longest_chain(self):
        """
        Identify the longest chain by length - we assume that the difficulty is the same across network
        """
        leaf_hashes = self.get_leaf_hashes()
        longest = []
        for tip in leaf_hashes:
            chain = self.get_chain(tip) # get the chain of blocks for each tip
            if len(chain) > len(longest):
                longest = chain # update longest chain based on size of chain list
        log.blockchain.info(
            'Node %s: longest chain length=%d tip=%s',
            self.node.name, len(longest), longest[-1].hash if longest else None
        )
        return longest

    def get_block(self, block_hash):
        """
        Retrieve a block by its hash
        """
        entry = self.chain.get(block_hash)
        return entry['block'] if entry else None

    def get_tip(self):
        if not self.chain:
            return None
        return max(
            (e['block'] for e in self.chain.values()),
            key=lambda blk: blk.height
        )

    # From blockchain documentation - returns up to 2000 headers
    def get_headers(self, locator):
        """
        Return up to 2000 Block headers (Block instances) starting just
        after the latest match in `locator`. Locator is a list of block
        hashes from your current chain tip backwards.
        """
        longest = self.get_longest_chain()
        # Find the first locator hash in our longest chain
        start = 0
        for loc_hash in locator:
            for i, blk in enumerate(longest):
                if blk.hash == loc_hash:
                    start = i + 1
                    break
            else:
                continue
            break

        return longest[start : start + 2000]


    def get_locator(self):
        """
        Build a block-locator: a list of block hashes from tip backwards,
        doubling the step each time, up to ~10 entries. Used by get_headers.
        """
        chain = self.get_longest_chain()
        locator = []
        step = 1
        idx = len(chain) - 1

        while idx >= 0 and len(locator) < 10:
            locator.append(chain[idx].hash)
            idx -= step
            step *= 2

        return locator

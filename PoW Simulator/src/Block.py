"""
=========================
Block
=========================

Author: Jaime de Vivero Woods
Last update: June 2025

Block class.
"""

from Log import log
from Transaction import Transaction
import time

class Block():
    """
    A PoW Block:
      - prev_hash: hash of parent block
      - transactions: list of Transaction
      - difficulty: current network difficulty
      - timestamp: seconds since epoch
      - nonce: the proof‐of‐work nonce
      - _hash: computed block hash
    """

    def __init__(self, *, prev_hash, transactions=None, timestamp=None, height: int = 0):
        self.prev_hash = prev_hash
        self._transactions = transactions if transactions is not None else []
        self.timestamp = timestamp if timestamp is not None else time.time()
        self._hash = self._compute_hash()
        self.is_canonical = False
        self.height = height

        log.block.info(
            "Created Block: prev=%s, hash=%s, timestamp=%s, txs=%s",
            self.prev_hash, self._hash, self.timestamp, self._transactions
        )

    def __repr__(self):
        return (
            f"[Block  hash={self._hash}  prev={self.prev_hash}  txs={self._transactions}]"
        )

    def __eq__(self, other):
        if not isinstance(other, Block):
            return False
        return (
            self.hash == other.hash and
            self.prev_hash == other.prev_hash and
            set(self._transactions) == set(other._transactions) and
            self.timestamp == other.timestamp
        )

    def __hash__(self):
        return self._hash

    def _compute_hash(self):
        """
        Compute a (Python) hash of the block’s contents.
        Using Python’s hash() for simulation purposes.
        """
        return hash(( self.prev_hash, frozenset(self._transactions), self.timestamp,))

    @property
    def transactions(self):
        return self._transactions

    @transactions.setter
    def transactions(self, tx_list):
        assert all(isinstance(tx, Transaction) for tx in tx_list), \
            "All items in transactions must be Transaction instances"
        self._transactions = tx_list
        self._hash = self._compute_hash()

    @property
    def hash(self):
        return self._hash

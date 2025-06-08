"""
=========================
Transaction
=========================

Author: Jaime de Vivero Woods
Last update: April 2025

Transaction class.
"""

from Log import log
import random
import time

class Transaction():
    """
    A PoW‐simulator transaction:
      - txid: unique identifier (hex string)
      - inputs: list of inputs (can be any payload)
      - outputs: list of outputs (can be any payload)
      - fee: numeric fee used for block selection
      - timestamp: creation time (seconds since epoch)
    """
    def __init__(self, *, fee=0, timestamp=None):
        self.fee = fee
        self._hash = '%x' % random.getrandbits(32)
        self._timestamp = timestamp if timestamp is not None else time.time()
        log.transaction.info('Created transaction with hash %s and time %s', self._hash,self._timestamp)

    def __repr__(self):
        # return '[Transaction %s]' % (self._hash)
        return '[Transaction %s fee={self.fee} time = %.4f]' % (self._hash,self._timestamp)

    @property
    def hash(self):
        return self._hash

    @property
    def timestamp(self):
        return self._timestamp

    def __hash__(self):
        return hash(self._hash)

    def __eq__(self, other):
        return isinstance(other, Transaction) and self._hash == other._hash

"""
=========================
Transaction
=========================

Author: Matija Piskorec
Last update: August 2023

Transaction class.
"""

from src.common.Log import log
import random

class Transaction:
    def __init__(self, data=None, time=None):
        """
        Initializes a Transaction object.

        Args:
            data (object, optional): Data associated with the transaction. Defaults to None.
            time (float, optional): Timestamp of the transaction creation. Defaults to None.
        """

        self._hash = '%x' % random.getrandbits(32)
        self._data = data
        self._time = time

        log.transaction.info('Created transaction with hash %s, data: %s, time: %.4f',
                              self._hash,
                             self._data,
                             self._time)

    def __repr__(self):
        """
        String representation of the Transaction object.
        """
        data_str = str(self._data)[:20] if self._data else 'None'  # Truncate long data strings
        return '[Transaction hash=%s, data=%s, time=%.4f]' % (self._hash, data_str, self._time)

    @property
    def hash(self):
        return self._hash

    @property
    def data(self):
        return self._data

    def __eq__(self, other):
        """
        Defines equality comparison for Transaction objects based solely on hash.
        """
        return isinstance(other, Transaction) and self._hash == other._hash

    def __hash__(self):
        """
        Makes Transaction hashable for use in sets and dictionaries.
        """
        return hash(self._hash)  # Use hash of the hash for immutability


#
# class Transaction():
#
#     def __init__(self,time=None):
#         self._hash = '%x' % random.getrandbits(32)
#         self._time = time
#         log.transaction.info('Created transaction with hash %s and time %s', self._hash,self._time)
#
#     def __repr__(self):
#         # return '[Transaction %s]' % (self._hash)
#         return '[Transaction %s time = %.4f]' % (self._hash,self._time)
#
#     @property
#     def hash(self):
#         return self._hash
#
#     # To make Transaction hashable so that we can store them in a Set or as keys in dictionaries.
#     def __hash__(self):
#         return hash(self._hash)

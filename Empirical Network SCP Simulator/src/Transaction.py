"""
=========================
Transaction
=========================

Author: Matija Piskorec
Last update: August 2023

Transaction class.
"""

from Log import log

import random

class Transaction():
    def __init__(self,time=None):
        self._hash = '%x' % random.getrandbits(32)
        self._time = time if time is not None else time.time()
        log.transaction.info('Created transaction with hash %s and time %s', self._hash,self._time)

    def __repr__(self):
        return '[Transaction %s time = %.4f]' % (self._hash,self._time)

    @property
    def hash(self):
        return self._hash

    # To make Transaction hashable so that we can store them in a Set or as keys in dictionaries
    def __hash__(self):
        return hash(self._hash)

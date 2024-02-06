"""
=========================
Ledger
=========================

Author: Matija Piskorec
Last update: August 2023

Ledger class.
"""

from Log import log

import numpy as np
import random

class Ledger():

    def __init__(self,node):
        self._transactions = []
        self.node = node

        log.ledger.info('Initialized ledger for node %(node)s!' % self.__dict__)

    def __repr__(self):
        return '[Ledger for Node %s, transactions = %s]' % (self.node.name,self._transactions)

    def add(self, transaction):

        # Only add a transaction if it's not already in node's ledger!
        if transaction not in self._transactions:
            self._transactions.append(transaction)
            log.ledger.info('Node %s: transaction %s added!', self.node.name, transaction)
        else:
            log.ledger.info('Node %s: transaction %s already exist!', self.node.name, transaction)
        return

    def get_transaction(self):

        # Get a random transaction from the ledger.
        transaction_random = np.random.choice(self._transactions) if len(self.transactions) > 0 else None

        return transaction_random

    # TODO: With @property we are returning a reference while we would probably want to return a copy!

    @property
    def transactions(self):
        return self._transactions

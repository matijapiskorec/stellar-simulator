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

from SCPExternalize import SCPExternalize

class Ledger():

    def __init__(self,node):
        self._transactions = []
        self.node = node

        self.slots = {}  # Dictionary to store {slot_number: value}

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

    def add_slot(self, slot, externalize_msg: SCPExternalize):
        # Add a transaction to a specific slot with externalize timestamp
        if slot not in self.slots:
            self.slots[slot] = {
                'value': externalize_msg.ballot.value,
                'timestamp': externalize_msg._time
            }
            log.ledger.info('Node %s: transaction %s with timestamp %s added to slot %d!',
                self.node.name, externalize_msg.ballot.value, externalize_msg._time, slot)
        else:
            log.ledger.info('Node %s: transaction for slot %d already exists!',self.node.name, slot)

    def get_slot(self, slot):
        print("SLOTS LOOKS LIKE : ", self.slots)
        return self.slots.get(slot, None)

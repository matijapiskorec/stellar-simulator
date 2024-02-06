"""
=========================
Value
=========================

Author: Matija Piskorec
Last update: August 2023

Value class.
"""

from Log import log
from Transaction import Transaction
from State import State

import random

class Value():

    # For our purposes a value is just a set of transactions.
    # def __init__(self,transactions,**kwargs):
    def __init__(self,**kwargs):

        self._transactions = kwargs['transactions'] if 'transactions' in kwargs else []

        # All transactions have to be of type Transaction - empty list is also allowed!
        assert all([isinstance(transaction,Transaction) for transaction in self._transactions])

        self._hash = hash(frozenset(self._transactions))
        self._state = kwargs['state'] if 'state' in kwargs else State.init

        log.value.info('Created value, hash = %s, state = %s, transactions = %s',
                       self._hash,
                       self._state,
                       self._transactions)

    def __repr__(self):
        return '[Value, hash = %s, state = %s, transactions = %s]' % (self._hash,self._state,self._transactions)

    # TODO: With @property we are returning a reference while we would probably want to return a copy!

    @property
    def transactions(self):
        return self._transactions

    @property
    def state(self):
        return self._state

    @classmethod
    def combine(cls,values):
        """
        Combine a list of values into a single value.
        """
        # TODO: Currently we are combining values by taking the union of transactions!
        if len(values)==0:
            transactions = []
        else:
            transactions = set().union(*[value.transactions for value in values[0]])
        return Value(transactions=transactions)


"""
=========================
Value
=========================

Author: Matija Piskorec
Last update: August 2023

Value class.
"""

from src.common.Log import log
from src.network.Transaction import Transaction
from src.consensus.State import State

class Value:
    # For our purposes, a value is a set of transactions.
    def __init__(self, **kwargs):
        """
        Initializes a Value object.
        """

        self._transactions = set(kwargs['transactions']) if 'transactions' in kwargs else set()

        # Assert transaction type and immutability
        assert all(isinstance(transaction, Transaction) for transaction in self._transactions)
        self._transactions = frozenset(self._transactions)  # Make transaction set immutable

        self._hash = hash(self._transactions)
        self._state = kwargs['state'] if 'state' in kwargs else State.init

        log.value.info('Created value, hash = %s, state = %s, transactions = %s',
                       self._hash,
                       self._state,
                       self._transactions)

    def __repr__(self):
        """
        Defines string representation for the Value object.
        """
        return '[Value, hash = %s, state = %s, transactions = %s]' % (self._hash, self._state, self._transactions)

    # **Properties now return copies!**

    @property
    def transactions(self):
        """
        Returns a copy of the internal transaction set.
        """
        return set(self._transactions)  # Return a copy

    @property
    def state(self):
        """
        Returns a copy of the state.
        """
        return self._state.copy()  # Assuming State object has a copy method

    @property
    def hash(self):
        """
        Returns the hash of the value.
        """
        return self._hash

    def __eq__(self, other):
        """
        Defines equality comparison for Value objects.
        """
        return (self.hash == other.hash and self.state == other.state and set(self.transactions) == set(other.transactions))

    @classmethod
    def combine(cls, values):
        """
        Combines a list of values into a single value.
        """
        # Combine transactions (union of sets)
        transactions = set.union(*(value.transactions for value in values))
        return Value(transactions=transactions)


#
#
# class Value():
#
#     # For our purposes a value is just a set of transactions.
#     # def __init__(self,transactions,**kwargs):
#     def __init__(self,**kwargs):
#
#         self._transactions = kwargs['transactions'] if 'transactions' in kwargs else []
#
#         # All transactions have to be of type Transaction - empty list is also allowed!
#         assert all([isinstance(transaction,Transaction) for transaction in self._transactions])
#
#         self._hash = hash(frozenset(self._transactions))
#         self._state = kwargs['state'] if 'state' in kwargs else State.init
#
#         log.value.info('Created value, hash = %s, state = %s, transactions = %s',
#                        self._hash,
#                        self._state,
#                        self._transactions)
#
#     def __repr__(self):
#         return '[Value, hash = %s, state = %s, transactions = %s]' % (self._hash,self._state,self._transactions)
#
#     # TODO: With @property we are returning a reference while we would probably want to return a copy!
#
#     def __eq__(self, other):
#         return (self.hash == other.hash and self.state == other.state and set(self.transactions) == set(other.transactions))
#
#     @property
#     def transactions(self):
#         return self._transactions
#
#     @property
#     def state(self):
#         return self._state
#
#     @property
#     def hash(self):
#         return self._hash
#
#     @classmethod
#     def combine(cls,values):
#         """
#         Combine a list of values into a single value.
#         """
#         # TODO: Currently we are combining values by taking the union of transactions!
#         if len(values)==0:
#             transactions = []
#         else:
#             transactions = set()
#             for value in values:
#                 transactions.update(value.transactions)
#
#         return Value(transactions=transactions)
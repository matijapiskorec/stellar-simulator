"""
=========================
Ledger
=========================

Author: Matija Piskorec
Last update: August 2023

Ledger class.
"""

# from src.common.Log import log
# import numpy as np
#
# class Ledger():
#     def __init__(self,node):
#         self._transactions = []
#         self.node = node
#
#         log.ledger.info('Initialized ledger for node %(node)s!' % self.__dict__)
#
#     def __repr__(self):
#         return '[Ledger for Node %s, transactions = %s]' % (self.node.name,self._transactions)
#
#     def add(self, transaction):
#
#         # Only add a transaction if it's not already in node's ledger!
#         if transaction not in self._transactions:
#             self._transactions.append(transaction)
#             log.ledger.info('Node %s: transaction %s added!', self.node.name, transaction)
#         else:
#             log.ledger.info('Node %s: transaction %s already exist!', self.node.name, transaction)
#         return
#
#     def get_transaction(self):
#
#         # Get a random transaction from the ledger.
#         transaction_random = np.random.choice(self._transactions) if len(self.transactions) > 0 else None
#
#         return transaction_random
#
#     # TODO: With @property we are returning a reference while we would probably want to return a copy!
#
#     @property
#     def transactions(self):
#         return self._transactions

import numpy as np

from src.common.Log import log
from src.consensus.Value import Value
from src.consensus.State import State

class Ledger:
    def __init__(self, node):
        self.node = node
        self._messages = []

    def add_messages(self, messages):
        """
        Adds messages (a list or single message) to the ledger, avoiding duplicates.
        """
        if type(messages) is not list:
            messages = [messages]

        for message in messages:
            if message not in self._messages:
                self._messages.append(message)
                log.storage.info('Node %s: added message %s', self.node.name, message)
            else:
                log.storage.info('Node %s: message already exists %s', self.node.name, message)
        return

    def get_message(self):
        """
        Returns a random message from the ledger (or None if empty).
        """
        message = np.random.choice(self._messages) if len(self._messages) > 0 else None
        return message

    def get_combined_messages(self):
        """
        Retrieves all messages, combines their voted and accepted values,
        and returns them as separate Value objects. Creates copies before combining.
        """
        messages = self._messages.copy()
        if len(messages) == 0:
            return Value(voted=[]), Value(accepted=[])
        else:
            voted_values = [value for message in messages for value in message.voted]
            accepted_values = [value for message in messages for value in message.accepted]

            return Value.combine(voted_values), Value.combine(accepted_values)

    def finalize_ledger(self):
        """
        Finalizes the ledger state based on stored messages.
        Combines votes and selects the agreed-upon value.

        This implementation assumes simple majority voting. You might need to
        adapt it based on your specific consensus protocol rules.
        """
        voted_values, _ = self.get_combined_messages()  # Get voted values, discard accepted_counts
        voted_counts = voted_values.get_value_counts()

        # Assuming simple majority voting
        winning_value = voted_counts.idxmax() if voted_counts.max() > len(self._messages) // 2 else None

        if not winning_value:
            log.ledger.warning('Ledger finalization: No majority vote found. Ledger state remains undecided!')
        else:
            log.ledger.info('Ledger finalized! Agreed-upon value: %s', winning_value)

            # Update the node's local state with the finalized value
            try:
                new_state = State.from_value(winning_value)  # Retrieve the State object
                self.node.set_local_state(new_state)  # Call the Node's method to update its state
                log.ledger.info('Node %s local state updated to %s', self.node.name, new_state)
            except ValueError:
                log.ledger.error('Failed to update node state: Invalid State value %s', winning_value)





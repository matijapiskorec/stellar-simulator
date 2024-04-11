"""
=========================
Storage
=========================

Author: Matija Piskorec
Last update: August 2023

Storage class.
"""
import numpy as np

from Log import log
from Value import Value

# TODO: Consider merging Storage and Ledger classes within a single super class!

class Storage:
    _messages = None
    # pending = None
    # ballot_history = None

    def __init__(self, node):

        # # TODO: Potential problem with circular imports?!
        # assert isinstance(node, Node)

        self.node = node
        self._messages = []

        # self.pending = list()
        # self.ballot_history = dict()

        log.storage.info('Initialized storage for node %(node)s!' % self.__dict__)

    def __repr__(self):
        return '[Storage for Node %s, messages = %s]' % (self.node.name,self._messages)

    def add_messages(self, messages):

        # If there is only one message as input, convert it to list so that we can iterate over it
        if type(messages) is not list:
            messages = [messages]

        for message in messages:
            # Only add a message if it's not already in node's storage!
            if message not in self._messages:
                self._messages.append(message)
                log.storage.info('Node %s: added message %s', self.node.name, message)
            else:
                log.storage.info('Node %s: message alread exist %s', self.node.name, message)
        return

    def get_message(self):
        # Get a random message from storage.
        message = np.random.choice(self._messages) if len(self._messages) > 0 else None
        return message

    # TODO: With @property we are returning a reference while we would probably want to return a copy!

    @property
    def messages(self):
        return self._messages

    def get_combined_messages(self):
        messages = self._messages.copy()
        if len(messages) == 0:
            return [], []
        else:
            voted_values = [value for message in messages for value in message.voted]
            accepted_values = [value for message in messages for value in message.accepted]
            if len(accepted_values) == 0:
                return Value.combine(voted_values), []

            return Value.combine(voted_values), Value.combine(accepted_values)


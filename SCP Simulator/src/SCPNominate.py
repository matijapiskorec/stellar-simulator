"""
=========================
SCPNominate
=========================

Author: Matija Piskorec, Jaime de Vivero Woods
Last update: July 2024

SCPNominate message class.
"""

from Log import log
from Value import Value
from Message import Message

import random

class SCPNominate(Message):

    def __init__(self,**kwargs):

        assert all([isinstance(vote,Value) for vote in kwargs['voted']])
        assert all([isinstance(accept,Value) for accept in kwargs['accepted']])

        self._voted = kwargs['voted']
        self._accepted = kwargs['accepted']

        log.message.info('Created SCPNominate message, data = %s', self)

    @property
    def voted(self):
        return self._voted

    @property
    def accepted(self):
        return self._accepted


    def parse_message_state(self, message):
        if len(message.voted) == 0 and len(message.accepted) == 0:
            return [], []
        else:
            voted_values = [value for value in message.voted]
            accepted_values = [value for value in message.accepted]
            if len(accepted_values) == 0:
                return [Value.combine(voted_values), []]
            elif len(voted_values) == 0:
                return [[], Value.combine(accepted_values)]

            return [Value.combine(voted_values), Value.combine(accepted_values)]

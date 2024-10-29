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

    # def __init__(self,voted,accepted):
    # def __init__(self,*args):
    def __init__(self,**kwargs):

        # We assume both vote and accepted arrays as inputs!
        # assert len(args) == 2

        # All values have to be of type Value - empty list is also allowed!
        # assert all([isinstance(vote,Value) for vote in voted])
        # assert all([isinstance(accept,Value) for accept in accepted])
        # assert all([isinstance(vote,Value) for vote in args[0]])
        # assert all([isinstance(accept,Value) for accept in args[1]])
        assert all([isinstance(vote,Value) for vote in kwargs['voted']])
        assert all([isinstance(accept,Value) for accept in kwargs['accepted']])

        # Generate unique message id of length UUID_LENGTH (defined in Message superclass)
        # super(SCPNominate,self).generate_id()

        # # Initialize Message superclass
        # super(SCPNominate, self).__init__()

        # self._voted = voted
        # self._accepted = accepted
        # self._voted = args[0]
        # self._accepted = args[1]
        self._voted = kwargs['voted']
        self._accepted = kwargs['accepted']

        # log.message.info('Created SCPNominate message, voted = %s, accepted = %s', self._voted, self._accepted)
        log.message.info('Created SCPNominate message, data = %s', self)

    # def __repr__(self):
    #     return '[SCPNominate message, voted = %s, accepted = %s]' % (self._voted, self._accepted)

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

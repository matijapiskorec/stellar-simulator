"""
=========================
Message
=========================

Author: Matija Piskorec
Last update: August 2023

Message superclass.
"""

from Log import log

import time
import uuid

# CLOCK_SEQ = int(time.time() * 1000000)
UUID_LENGTH = 10

class Message():

    # def __init__(self):

    #     # Generate random message id of length UUID_LENGTH (defined in Message superclass)
    #     self._message_id = uuid.uuid4().hex[:UUID_LENGTH]

    #     self._broadcasted = False
    #     # self.generate_id()

    # def __new__(cls,*args):
    def __new__(cls,**kwargs):
        new = object.__new__(cls)
        # Generate random message id of length UUID_LENGTH (defined in Message superclass)
        new._message_id = uuid.uuid4().hex[:UUID_LENGTH]
        new._broadcasted = kwargs['broadcasted'] if 'broadcasted' in kwargs else False
        return new

    def __repr__(self):
        # return '[SCPNominate message, voted = %s, accepted = %s]' % (self._voted, self._accepted)
        # return '[%s message, data = %s]' % (type(self).__name__, self.__dict__)
        return '[%s message, data = %s]' % (type(self).__name__, self.__dict__)

    def __eq__(self, other):
        # return message._message_id == self._message_id
        if isinstance(other, self.__class__):
            return other._message_id == self._message_id
        else:
            return False

    # def generate_id(self):
    #     # self.message_id = uuid.uuid1(clock_seq=CLOCK_SEQ).hex
    #     self.message_id = uuid.uuid4().hex[:UUID_LENGTH]

    # TODO: With @property we are returning a reference while we would probably want to return a copy!

    @property
    def message_id(self):
        return self._message_id

    @property
    def broadcasted(self):
        return self._broadcasted

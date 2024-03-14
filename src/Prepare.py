"""
=========================
SCPNominate
=========================

Author: Matija Piskorec
Last update: August 2023

SCPNominate message class.
"""

from Log import log
from Value import Value
from Message import Message

# Prepare Message - what should be included?
class Prepare(Message):
    def __init__(self,**kwargs):

        assert all([isinstance(tx,Value) for tx in kwargs['transactions']])
        self._values = kwargs['transactions']
        # self._voted = []
        # self._accepted = []

        log.message.info('Created Prepare message with transactions = %s', self._values)

    @property
    def transactions(self):
        return self._values

    def __repr__(self):
        return '[PrepareMessage, transactions = %s]' % (self._values)

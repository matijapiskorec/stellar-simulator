"""
=========================
SCPNominate
=========================

Author: Matija Piskorec
Last update: August 2023

SCPNominate message class.
"""

from src.common.Log import log
from src.consensus.Value import Value
from src.network.Message import Message

# class SCPNominate(Message):
#
#     # def __init__(self,voted,accepted):
#     # def __init__(self,*args):
#     def __init__(self,**kwargs):
#
#         # We assume both vote and accepted arrays as inputs!
#         # assert len(args) == 2
#
#         # All values have to be of type Value - empty list is also allowed!
#         # assert all([isinstance(vote,Value) for vote in voted])
#         # assert all([isinstance(accept,Value) for accept in accepted])
#         # assert all([isinstance(vote,Value) for vote in args[0]])
#         # assert all([isinstance(accept,Value) for accept in args[1]])
#         assert all([isinstance(vote,Value) for vote in kwargs['voted']])
#         assert all([isinstance(accept,Value) for accept in kwargs['accepted']])
#
#         # Generate unique message id of length UUID_LENGTH (defined in Message superclass)
#         # super(SCPNominate,self).generate_id()
#
#         # # Initialize Message superclass
#         # super(SCPNominate, self).__init__()
#
#         # self._voted = voted
#         # self._accepted = accepted
#         # self._voted = args[0]
#         # self._accepted = args[1]
#         self._voted = kwargs['voted']
#         self._accepted = kwargs['accepted']
#
#         # log.message.info('Created SCPNominate message, voted = %s, accepted = %s', self._voted, self._accepted)
#         log.message.info('Created SCPNominate message, data = %s', self)
#
#     # def __repr__(self):
#     #     return '[SCPNominate message, voted = %s, accepted = %s]' % (self._voted, self._accepted)
#
#     @property
#     def voted(self):
#         return self._voted

class SCPNominate(Message):

    def __init__(self, voted: list[Value], accepted: list[Value]):
        """
        Initializes an SCPNominate message.

        Args:
            voted: A list of Value objects representing voted transactions.
            accepted: A list of Value objects representing accepted transactions.

        Raises:
            AssertionError: If input lists are not of type Value or have different lengths.
        """

        # Validate input lists
        assert len(voted) == len(accepted), "Voted and accepted lists must have the same length."
        assert all(isinstance(vote, Value) for vote in voted), "All voted values must be of type Value."
        assert all(isinstance(accept, Value) for accept in accepted), "All accepted values must be of type Value."

        # Call Message superclass initialization
        super().__init__()

        self._voted = voted
        self._accepted = accepted

        log.message.info('Created SCPNominate message, data = %s', self)

    @property
    def voted(self) -> list[Value]:
        """Returns the list of voted transactions."""
        return self._voted

    @property
    def accepted(self) -> list[Value]:
        """Returns the list of accepted transactions."""
        return self._accepted

    def __repr__(self):
        return f"[SCPNominate message, voted = {self._voted}, accepted = {self._accepted}]"



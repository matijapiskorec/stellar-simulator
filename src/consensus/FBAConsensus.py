"""
=========================
FBAConsensus
=========================

Author: Matija Piskorec
Last update: August 2023

Federated Byzantine Agreement (FBA) consensus class.
"""

from src.common.Log import log
from src.network.Event import Event

class FBAConsensus:

    @classmethod
    def get_events(cls):
        events = [Event('mine'),
                  Event('retrieve_transaction_from_mempool'),
                  Event('nominate'),
                  Event('retrieve_message_from_peer')]

        log.consensus.info('Sending FBAConsensus events %s.' % events)

        return events

    @classmethod
    def __mine(cls):
        log.consensus.info('FBAConsensus: Mine event triggered (not implemented).')
        # TODO: Add Mine()

    @classmethod
    def __gossip(cls):
        # Placeholder for actual gossip logic (removed from core consensus)
        log.consensus.info('FBAConsensus: Gossip event triggered (removed).')

    def mine(self, data):
        raise NotImplementedError("Mining functionality not implemented in FBAConsensus base class.")

    def gossip(self, data):
        raise NotImplementedError("Gossip functionality not implemented in FBAConsensus base class.")

#
# class FBAConsensus:
#
#     @classmethod
#     def get_events(cls):
#
#         # mine - Node should add a new transaction to its ledger.
#         # gossip - Node should send a message to one of its peers.
#
#         # TODO: Add event for a node to retrieve transaction from the mempool!
#         events = [Event('mine'),
#                   Event('retrieve_transaction_from_mempool'),
#                   Event('nominate'),
#                   Event('retrieve_message_from_peer')]
#
#         # # TODO: Remove gossip event from the consensus!
#         # Event('gossip'),
#
#         log.consensus.info('Sending FBAConsensus events %s.' %events)
#
#         return events
#
#     @classmethod
#     def __mine(cls):
#         log.consensus.info('MINE!')
#
#     @classmethod
#     def __gossip(cls):
#         log.consensus.info('GOSSIP!')
#
#     def mine(self, data):
#         raise NotImplementedError()
#
#     def gossip(self, data):
#         raise NotImplementedError()

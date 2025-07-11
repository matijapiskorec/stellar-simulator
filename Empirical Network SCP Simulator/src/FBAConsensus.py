"""
=========================
FBAConsensus
=========================

Author: Matija Piskorec, Jaime de Vivero Woods
Last update: December 2024

Federated Byzantine Agreement (FBA) consensus class.
"""

from Log import log
from Event import Event

class FBAConsensus:

    @classmethod
    def get_events(cls):
        events = [Event('mine'),
                  Event('retrieve_transaction_from_mempool'),
                  Event('nominate'),
                  Event('retrieve_message_from_peer'),
                  Event('prepare_ballot'),
                  Event('receive_prepare_message'),
                  Event('prepare_commit'),
                  Event('receive_commit_message'),
                  Event('prepare_externalize_message'),
                  Event('receive_externalize_msg')]

        log.consensus.info('Sending FBAConsensus events %s.' %events)

        return events

    @classmethod
    def __mine(cls):
        log.consensus.info('MINE!')

    @classmethod
    def __gossip(cls):
        log.consensus.info('GOSSIP!')

    def mine(self, data):
        raise NotImplementedError()

    def gossip(self, data):
        raise NotImplementedError()

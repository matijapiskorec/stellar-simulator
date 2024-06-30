"""
=========================
FBAConsensus
=========================

Author: Matija Piskorec
Last update: August 2023

Federated Byzantine Agreement (FBA) consensus class.
"""

from Log import log
from Event import Event
from SCPNominate import SCPNominate


class FBAConsensus:
    def __init__(self, network):
        self.network = network

    @classmethod
    def get_events(cls):

        # mine - Node should add a new transaction to its ledger.
        # gossip - Node should send a message to one of its peers.

        # TODO: Add event for a node to retrieve transaction from the mempool!
        events = [Event('mine'),
                  Event('retrieve_transaction_from_mempool'),
                  Event('nominate'),
                  Event('retrieve_message_from_peer')]

        # # TODO: Remove gossip event from the consensus!
        # Event('gossip'),

        log.consensus.info('Sending FBAConsensus events %s.' %events)

        return events

    @classmethod
    def __mine(cls):
        log.consensus.info('MINE!')

    @classmethod
    def __gossip(cls):
        log.consensus.info('GOSSIP!')

    def mine(self):
        log.consensus.info('Mining a new block')
        # Implement mining logic here
        for node in self.network.nodes:
            transaction = node.mempool.get_transaction()
            if transaction:
                node.ledger.add_transaction(transaction)
                node.storage.add_message(SCPNominate(voted=[transaction], accepted=[]))
                log.consensus.info(f"Node {node.node_id} mined transaction: {transaction}")

    def gossip(self, data):
        raise NotImplementedError()

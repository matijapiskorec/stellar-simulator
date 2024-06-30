"""
=========================
Event
=========================

Author: Matija Piskorec
Last update: August 2023

Event class.
"""

from Log import log
from Transaction import Transaction

class Event:

    def __init__(self, name, **kvargs):

        self.name = name

        # Simulation parameters - typically tau and node_specific.
        # Some events are parametrized as the average waiting time of the event over all nodes.
        # While other events are parametrized as the average waiting time for each individual node.
        self.simulation_params = kvargs['simulation_params'] if 'simulation_params' in kvargs else None

        # Event parameters - additional data for event handlers to know how to handle the event.
        self.event_params = kvargs['event_params'] if 'event_params' in kvargs else None

        log.event.info('Initialized event %s, simulation_params = %s, event_params = %s.',
                       self.name,
                       self.simulation_params,
                       self.event_params)

    def __repr__(self):
        return '[Event %s, simulation_params = %s]' % (self.name,self.simulation_params)

    def __eq__(self, name):
        return self.name == name

    def simulate_event(self, network):
        if self.name == "create_transaction":
            self.create_transaction(network)
        elif self.name == "process_transaction":
            self.process_transaction(network)
        elif self.name == "consensus_event":
            self.consensus_event(network)
        else:
            log.event.warning(f"Unknown event: {self.name}")

    def create_transaction(self, network):
        transaction_hash = self.simulation_params.get('transaction_hash')
        time_stamp = self.simulation_params.get('time_stamp')
        transaction = Transaction(transaction_hash, time_stamp)
        for node in network.nodes:
            node.mempool.add_transaction(transaction)
        log.event.info(f"Transaction created: {transaction_hash}")

    def process_transaction(self, network):
        for node in network.nodes:
            node.retrieve_transaction_from_mempool()
        log.event.info("Transactions processed by all nodes")

    def consensus_event(self, network):
        # Implement consensus logic here
        for node in network.nodes:
            for transaction in node.mempool.transactions:
                node.nominate(transaction.transaction_hash)
                node.vote(transaction.transaction_hash)
        log.event.info("Consensus event processed for all nodes")

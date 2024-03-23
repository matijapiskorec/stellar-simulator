import sys

from Simulator import Simulator
from Gillespie import Gillespie
from Event import Event
from Network import Network
from Mempool import Mempool
from Log import log

import unittest

from Value import Value


class SimulatorTest(unittest.TestCase):

    def setup(self):
        pass

    def test_initialize_simulator(self):
        # Can we initialize the simulator?
        simulator = Simulator(verbosity=0)
        self.assertTrue(isinstance(simulator,Simulator))

        # # Can we initialize the simulator with different verbosity levels?
        # for i in range(1,6):
        #     simulator = Simulator(verbosity=i)
        #     self.assertTrue(isinstance(simulator,Simulator))

    def test_run_simulator(self):
        verbosity = 0
        n_nodes = 2
        simulator = Simulator(verbosity=verbosity,n_nodes=n_nodes)
        simulator.run()
        # Did we created the right number of nodes?
        self.assertTrue(len(simulator.nodes)==n_nodes)

    def test_gillespie(self):
        events = [Event('mine'),Event('gossip')]
        simulation_params = {'mine':{'tau':1.0,
                                     'tau_domain':None},
                             'gossip':{'tau':3.0,
                                       'tau_domain':None}}

        # Set the simulation parameters of all events for which we have them
        for event in events:
            if event.name in simulation_params:
                event.simulation_params = simulation_params[event.name]

        # Remove events for which we don't have simulation parameters
        events = [event for event in events if event.simulation_params is not None]
        gillespie = Gillespie(events, max_time=10)
        self.assertTrue(isinstance(gillespie,Gillespie))

    def test_generation_of_nodes(self):
        nodes = Network.generate_nodes(n_nodes=5, topology='FULL')

        mempool = Mempool()
        for node in nodes:
            node.attach_mempool(mempool)

        mempool.mine()
        nodes[0].retrieve_transaction_from_mempool()
        nodes[0].nominate()
        # nodes[1].retrieve_message_from_mempool()
        nodes[1].retrieve_message_from_peer()

        mempool.mine()
        mempool.mine()
        nodes[0].retrieve_transaction_from_mempool()
        nodes[0].retrieve_transaction_from_mempool()
        # nodes[1].retrieve_message_from_mempool()
        nodes[1].retrieve_message_from_peer()

        # Newly added transactions should not be visible in the message that was already posted to the mempool!
        # This is true if we are sending a copy of transactions rather than a reference to transactions
        self.assertTrue(len(nodes[1].messages[0]._voted[0]._transactions)==1)

    # Test whether we can calculate priority for each peer in the quorum set
    def test_priority_of_nodes(self):

        for topology in ['FULL','ER']:
            nodes = Network.generate_nodes(n_nodes=5, topology=topology)

            mempool = Mempool()
            for node in nodes:
                node.attach_mempool(mempool)

            for node in nodes:
                log.test.debug('Node %s, all peers in quorum set = %s',node.name,node.quorum_set.get_nodes())
                max_priority = 0
                max_priority_neighbor = None
                for neighbor in node.get_neighbors():
                    priority = node.priority(neighbor)
                    if priority > max_priority:
                        max_priority = priority
                        max_priority_neighbor = neighbor
                    log.test.debug('Node %s, priority of neighbor %s is %s',node.name,neighbor.name,priority)
                    self.assertTrue(isinstance(priority,int))

            self.assertTrue( node.get_highest_priority_neighbor() == max_priority_neighbor )
            self.assertTrue( node.priority(node.get_highest_priority_neighbor()) == max_priority )

    def test_quorum_of_nodes(self):

        nodes = Network.generate_nodes(n_nodes=5, topology='ER')
        for node in nodes:
            log.test.debug('Node %s, quorum_set = %s',node.name,node.quorum_set)
            log.test.debug('Node %s, check_threshold = %s',node.name,node.quorum_set.get_quorum())

    def test_prepare_nomination_msg_correctly_adds_value(self):
        for topology in ['FULL','ER']:
            nodes = Network.generate_nodes(n_nodes=5, topology=topology)
            mempool = Mempool()
            for node in nodes:
                node.attach_mempool(mempool)

            for i in range(5):
                mempool.mine()

            for node in nodes:
                node.prepare_nomination_msg()

            for node in nodes:
                self.assertEqual(type(node.nomination_state['voted'][0]), Value)
                # as extend is used to add new Values the list of
                self.assertTrue(len(node.nomination_state['voted'][0].transactions) == len(node.ledger.transactions))
                self.assertTrue(len(node.storage.messages) > 0)

    def test_prepare_nomination_phase_correctly_adds_many_values(self):
        for topology in ['FULL', 'ER']:
            nodes = Network.generate_nodes(n_nodes=5, topology=topology)
            mempool = Mempool()
            for node in nodes:
                node.attach_mempool(mempool)

            for i in range(5):
                mempool.mine()

            for node in nodes:
                node.prepare_nomination_msg()
                node.prepare_nomination_msg()

            for node in nodes:
                assert all([isinstance(vote, Value) for vote in node.nomination_state['voted']])
                # The second Value in the state should contain all txs from ledger which should now be 2
                self.assertTrue(len(node.nomination_state['voted'][1].transactions) == len(node.ledger.transactions))
                self.assertTrue(len(node.storage.messages) > 0)


if __name__ == "__main__":
    # Comment out if you are running multiple tests and don't want any output!
    log.set_level(5)
    unittest.main()


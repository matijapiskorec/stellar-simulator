import sys

from Simulator import Simulator
from Gillespie import Gillespie
from Event import Event
from Network import Network
from Mempool import Mempool
from Log import log

import unittest

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

if __name__ == "__main__":
    # Comment out if you are running multiple tests and don't want any output!
    log.set_level(5)
    unittest.main()


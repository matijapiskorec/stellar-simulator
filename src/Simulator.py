"""
================================================
Simulator
================================================

Author: Matija Piskorec, Jaime de Vivero Woods
Last update: January 2025

The following class contains command line (CLI) interface for the Stellar Consensus Protocol (SCP) simulator.

Verbosity levels:
    0 - No output!
    1 - Basic output with progress bar.
    2 - Full output for debugging.

Logging levels and verbosity levels (higher includes lower):
1 - CRITICAL
2 - ERROR
3 - WARNING
4 - INFO
5 - DEBUG
"""

import argparse
import time
import sys
import numpy as np

from Log import log
from Node import Node
from Gillespie import Gillespie
from FBAConsensus import FBAConsensus
from Network import Network
from Mempool import Mempool
# import Globals
from Globals import Globals

VERBOSITY_DEFAULT = 5
N_NODES_DEFAULT = 88

class Simulator:
    '''
    Command line (CLI) interface for the simulator.
    '''

    def __init__(self,verbosity=VERBOSITY_DEFAULT,n_nodes=N_NODES_DEFAULT,**kvargs):

        self._verbosity = verbosity
        self._n_nodes = n_nodes

        self._nodes = []

        # TODO: _max_simulation_time should be loaded from the config!
        self._max_simulation_time = 50
        # self._simulation_time = 0

        self._set_logging()

        # Total elapsed time doesn't include initialization!
        self.timeStart = time.time()

    @property
    def verbosity(self):
        return self._verbosity

    @property
    def n_nodes(self):
        return self._n_nodes

    @property
    def nodes(self):
        return self._nodes

    def _set_logging(self):

        # Setting logger and verbosity level
        log_level = log.verbosityDict[self._verbosity]
        if self._verbosity:
            log.set_level(log_level)

    def run(self):

        if self._verbosity:
            log.simulator.info('Started simulation vith verbosity level %s and %s nodes.',
                               self._verbosity, self._n_nodes)

        if self._verbosity:
            log.simulator.debug('Creating %s nodes.', self._n_nodes)

        # self._nodes = Network.generate_nodes(n_nodes=self._n_nodes, topology='FULL')
        # self._nodes = Network.generate_nodes(n_nodes=self._n_nodes, topology='HARDCODE')
        self._nodes = Network.generate_nodes(n_nodes=self._n_nodes, topology='ER')

        self._mempool = Mempool()
        # self._mempool = Mempool(simulation_time=self._simulation_time)
        # self._mempool = Mempool(self._simulation_time)
        for node in self._nodes:
            node.attach_mempool(self._mempool)

        # Run Gillespie algorithm
        if self._verbosity:
            log.simulator.debug('Running Gillespie algorithm.')

        # Simulation parameters for each event
        # tau_domain: None - tau defines a global probability of event
        #             List(Node) - tau defines a node-specific probability of event
        # TODO: Simulation parameters should be loaded from the config!

        """# These are simulation params for HARDCODE - real topology  from Stellar Beat API
        simulation_params = {
            'mine': {'tau': 10.0, 'tau_domain': None},
            # Communication group
            'retrieve_transaction_from_mempool': {'tau': 0.01, 'tau_domain': self._nodes},  # 1 second
            'nominate': {'tau': 0.01, 'tau_domain': self._nodes},
            'receive_commit_message': {'tau': 0.01, 'tau_domain': self._nodes},
            'receive_externalize_msg': {'tau': 0.01, 'tau_domain': self._nodes},
            # Processing group
            'retrieve_message_from_peer': {'tau': 0.01, 'tau_domain': self._nodes},
            'prepare_ballot': {'tau': 0.01, 'tau_domain': self._nodes},
            'receive_prepare_message': {'tau': 0.01, 'tau_domain': self._nodes},
            'prepare_commit': {'tau': 0.01, 'tau_domain': self._nodes},
            'prepare_externalize_message': {'tau': 0.01, 'tau_domain': self._nodes}  # 6 seconds
        }
        """

        simulation_params = {
            'mine': {'tau': 0.01, 'tau_domain': None},
            # Communication group
            'retrieve_transaction_from_mempool': {'tau': 1.0, 'tau_domain': self._nodes},  # 1 second
            'nominate': {'tau': 12.0, 'tau_domain': self._nodes},
            'receive_commit_message': {'tau': 1.0, 'tau_domain': self._nodes},
            'receive_externalize_msg': {'tau': 1.0, 'tau_domain': self._nodes},
            # Processing group
            'retrieve_message_from_peer': {'tau': 13.0, 'tau_domain': self._nodes},
            'prepare_ballot': {'tau': 13.0, 'tau_domain': self._nodes},
            'receive_prepare_message': {'tau': 13.0, 'tau_domain': self._nodes},
            'prepare_commit': {'tau': 13.0, 'tau_domain': self._nodes},
            'prepare_externalize_message': {'tau': 20.0, 'tau_domain': self._nodes}  # 6 seconds
        }

        # ALL SIMULATION EVENTS COULD OCCUR AT ANY POINT, WHEN WE IMPLEMENT BALLOTING WE'LL HAVE TO
        # DISABLE NOMINATE

        # Concatenate events you get from the FBAConsensus and Node class
        self._events = [*FBAConsensus.get_events(), *Node.get_events()]

        # Set the simulation parameters of all events for which we have them
        for event in self._events:
            if event.name in simulation_params:
                event.simulation_params = simulation_params[event.name]
            else:
                if self._verbosity:
                    log.simulator.warning('No simulation parameters for event %s - igoring the event!', event.name)

        # Remove events for which we don't have simulation parameters
        self._events = [event for event in self._events if event.simulation_params is not None]

        # Initialize Gillespie with a collection of events and their probabilities
        # Then query it repeatedly to receive next event

        gillespie = Gillespie(self._events, max_time=self._max_simulation_time)

        while gillespie.check_max_time():
            # event_random, self._simulation_time = gillespie.next_event()
            event_random, Globals.simulation_time = gillespie.next_event()
            # Update time for mempool so that newly mined transactions would have correct timestamps.
            # self._mempool.update_time(self._simulation_time)
            self._handle_event(event_random)
        log.export_logs_to_txt("ledger_logs.txt")

    def _handle_event(self,event):
        """
        Handles an event - chooses a random node to which event applies and send it to node.
        """

        if self._verbosity:
            # log.simulator.info('Handling event %s at simulation time = %.3f',event.name,self._simulation_time)
            log.simulator.info('Handling event %s at simulation time = %.3f',event.name,Globals.simulation_time)

        match event.name:

            case 'mine':

                # Mempool is responsible for handling the mine event
                self._mempool.mine()
                # Globals.mempool.mine()

            case 'retrieve_transaction_from_mempool':

                # Choose a random node which retrieves the transaction from mempool.
                node_random = np.random.choice(self._nodes)

                # Send the event to the respective node and the mempool
                node_random.retrieve_transaction_from_mempool()

            # # TODO: Remove gossip event from the simulator!
            # case 'gossip':

            #     # Choose a random sender node (assuming equal probabilities for all nodes for now)
            #     random_node = np.random.choice(self._nodes)

            #     random_node.gossip()

            case 'nominate':
                random_node = np.random.choice(self._nodes)
                random_node.nominate()

            case 'retrieve_message_from_peer':
                random_node = np.random.choice(self._nodes)
                random_node.receive_message()

            case 'prepare_ballot':
                random_node = np.random.choice(self._nodes)
                random_node.prepare_ballot_msg()

            case 'receive_prepare_message':
                random_node = np.random.choice(self._nodes)
                random_node.receive_prepare_message()

            case 'prepare_commit':
                random_node = np.random.choice(self._nodes)
                random_node.prepare_SCPCommit_msg()

            case 'receive_commit_message':
                random_node = np.random.choice(self._nodes)
                random_node.receive_commit_message()

            case 'prepare_externalize_message':
                random_node = np.random.choice(self._nodes)
                random_node.prepare_Externalize_msg()

            case 'receive_externalize_msg':
                random_node = np.random.choice(self._nodes)
                random_node.receive_Externalize_msg()


if __name__=='__main__':

    # Parsing arguments from the command line
    parser=argparse.ArgumentParser()
    parser.add_argument("--verbosity","-v", type=int, default=VERBOSITY_DEFAULT, help="Verbosity level (0-5).")
    parser.add_argument("--nodes","-n", type=int, default=N_NODES_DEFAULT, help="Number of nodes.")
    args = parser.parse_args()

    simulator = Simulator(verbosity=args.verbosity,n_nodes=args.nodes)

    simulator.run()


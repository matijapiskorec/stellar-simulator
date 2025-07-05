"""
================================================
Simulator
================================================

Author: Matija Piskorec, Jaime de Vivero Woods
Last update: June 2025

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
import copy
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
from SCPExternalize import SCPExternalize

VERBOSITY_DEFAULT = 5
N_NODES_DEFAULT = 50

class Simulator:
    '''
    Command line (CLI) interface for the simulator.
    '''

    def __init__(self,verbosity=VERBOSITY_DEFAULT,n_nodes=N_NODES_DEFAULT, max_simulation_time=50, simulation_params=None, **kvargs):

        self._verbosity = verbosity
        self._n_nodes = n_nodes
        self._nodes = []
        self._max_simulation_time = max_simulation_time

        self._set_logging()

        self.timeStart = time.time()
        # ER_singlequorumset
        self._nodes = Network.generate_nodes(n_nodes=self._n_nodes, topology='BA')

        if simulation_params is not None:
            self.simulation_params = simulation_params
            self.original_simulation_params = copy.deepcopy(simulation_params)

        else:
            self.simulation_params = {
                'mine': {'tau': 1.0, 'tau_domain': self._nodes},  # Faster mining improves tx availability moderately
                'retrieve_transaction_from_mempool': {'tau': 1.0, 'tau_domain': self._nodes},
                # Processing
                'prepare_commit': {'tau': 0.01, 'tau_domain': self._nodes},  # Quickly move to commit stage
                'prepare_externalize_message': {'tau':0.01, 'tau_domain': self._nodes},
                'nominate': {'tau': 0.01, 'tau_domain': self._nodes},  # Very frequent nominations
                'prepare_ballot': {'tau': 0.01, 'tau_domain': self._nodes},  # Rapid ballot preparation
                # Communication
                'retrieve_message_from_peer': {'tau': 0.05, 'tau_domain': self._nodes},  # Very fast message retrieval
                'receive_prepare_message': {'tau': 0.05, 'tau_domain': self._nodes},
                'receive_commit_message': {'tau': 0.05, 'tau_domain': self._nodes},  # Faster message processing
                'receive_externalize_msg': {'tau': 0.001, 'tau_domain': self._nodes} # Ensure externalisation occurs very quick when a node reaches it -ensure s consistency
                # Quick externalize initiation
            }

        for v in self.simulation_params.values():
                if isinstance(v, dict) and v.get('tau_domain') == "self._nodes":
                    v['tau_domain'] = self._nodes

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

    def get_first_externalized_values(self):
        first_externalized = {}

        for node in self._nodes:
            if node.externalize_broadcast_flags:
                first_value = next(iter(node.externalize_broadcast_flags.values()))
                first_externalized[node] = first_value  # Store the first externalized value

        return first_externalized

    def all_nodes_finalized(self):
        check = all(isinstance(node.externalized_slot_counter, SCPExternalize) for node in self._nodes)
        return check

    def run(self):

        if self._verbosity:
            log.simulator.info('Started simulation vith verbosity level %s and %s nodes for simulation time %s.',
                               self._verbosity, self._n_nodes, self._max_simulation_time)

        if self._verbosity:
            log.simulator.debug('Creating %s nodes.', self._n_nodes)

        for node in self._nodes:
            node.attach_mempool(Mempool())

        # Run Gillespie algorithm
        if self._verbosity:
            log.simulator.debug('Running Gillespie algorithm.')


        # Concatenate events you get from the FBAConsensus and Node class
        self._events = [*FBAConsensus.get_events(), *Node.get_events()]

        # Set the simulation parameters of all events for which we have them
        for event in self._events:
            if event.name in self.simulation_params:
                event.simulation_params = self.simulation_params[event.name]
            else:
                if self._verbosity:
                    log.simulator.warning('No simulation parameters for event %s - igoring the event!', event.name)

        # Remove events for which we don't have simulation parameters
        self._events = [event for event in self._events if event.simulation_params is not None]

        gillespie = Gillespie(self._events, max_time=self._max_simulation_time)

        # Run simulation
        while gillespie.check_max_time():
            event_random, Globals.simulation_time = gillespie.next_event()
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
            case 'mine': # CREATE TRANSACTION
                node = np.random.choice(self._nodes)
                node.mempool.mine()

            case 'retrieve_transaction_from_mempool':
                node_random = np.random.choice(self._nodes)
                node_random.retrieve_transaction_from_mempool()

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


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
from SCPExternalize import SCPExternalize

VERBOSITY_DEFAULT = 5
N_NODES_DEFAULT = 50

class Simulator:
    '''
    Command line (CLI) interface for the simulator.
    '''

    def __init__(self,verbosity=VERBOSITY_DEFAULT,n_nodes=N_NODES_DEFAULT, max_simulation_time=25, simulation_params=None, **kvargs):

        self._verbosity = verbosity
        self._n_nodes = n_nodes

        self._nodes = []

        # TODO: _max_simulation_time should be loaded from the config!
        self._max_simulation_time = max_simulation_time
        # self._simulation_time = 0

        self._set_logging()

        # Total elapsed time doesn't include initialization!
        self.timeStart = time.time()
        # ER_singlequorumset
        #self._nodes = Network.generate_nodes(n_nodes=self._n_nodes, topology='HARDCODE', percent_threshold=0.25)
        self._nodes = Network.generate_nodes(n_nodes=self._n_nodes, topology='HARDCODE', percent_threshold=1.0)

        if simulation_params is not None:
            self.simulation_params = simulation_params
        else:
            """
            self.simulation_params = {
                #'mine': {'tau': 1.0, 'tau_domain': self._nodes}, # 1tx per node per time unit
                'mine': {'tau': 10.0, 'tau_domain': self._nodes},
                'retrieve_transaction_from_mempool': {'tau': 5.0, 'tau_domain': self._nodes},
                'nominate': {'tau': 1.0, 'tau_domain': self._nodes},
                'receive_commit_message': {'tau': 0.5, 'tau_domain': self._nodes},
                'receive_externalize_msg': {'tau': 0.5, 'tau_domain': self._nodes},
                'retrieve_message_from_peer': {'tau': 0.5, 'tau_domain': self._nodes},
                'prepare_ballot': {'tau': 1.0, 'tau_domain': self._nodes},
                'receive_prepare_message': {'tau': 0.5, 'tau_domain': self._nodes},
                'prepare_commit': {'tau': 1.0, 'tau_domain': self._nodes},
                'prepare_externalize_message': {'tau': 1.0, 'tau_domain': self._nodes}
            }
            
            
                        self.simulation_params = {
                'mine': {'tau': 10.0, 'tau_domain': self._nodes},
                'retrieve_transaction_from_mempool': {'tau': 1.0, 'tau_domain': self._nodes},
                'nominate': {'tau': 0.02, 'tau_domain': self._nodes},
                'receive_commit_message': {'tau': 0.01, 'tau_domain': self._nodes},
                'receive_externalize_msg': {'tau': 0.01, 'tau_domain': self._nodes},
                'retrieve_message_from_peer': {'tau': 0.01, 'tau_domain': self._nodes},
                'prepare_ballot': {'tau': 0.02, 'tau_domain': self._nodes},
                'receive_prepare_message': {'tau': 0.01, 'tau_domain': self._nodes},
                'prepare_commit': {'tau': 0.02, 'tau_domain': self._nodes},
                'prepare_externalize_message': {'tau': 0.02, 'tau_domain': self._nodes},
            }
                        self.simulation_params = {
                'mine': {'tau': 5.0, 'tau_domain': self._nodes},  # Faster mining improves tx availability moderately
                'retrieve_transaction_from_mempool': {'tau': 0.5, 'tau_domain': self._nodes},
                # Slightly faster tx pickup
                'nominate': {'tau': 0.005, 'tau_domain': self._nodes},  # Very frequent nominations
                'receive_commit_message': {'tau': 0.001, 'tau_domain': self._nodes},  # Faster message processing
                'receive_externalize_msg': {'tau': 0.001, 'tau_domain': self._nodes},  # Faster finalization processing
                'retrieve_message_from_peer': {'tau': 0.001, 'tau_domain': self._nodes},  # Very fast message retrieval
                'prepare_ballot': {'tau': 0.005, 'tau_domain': self._nodes},  # Rapid ballot preparation
                'receive_prepare_message': {'tau': 0.001, 'tau_domain': self._nodes},
                # Fast propagation of prepare msgs
                'prepare_commit': {'tau': 0.005, 'tau_domain': self._nodes},  # Quickly move to commit stage
                'prepare_externalize_message': {'tau': 0.005, 'tau_domain': self._nodes},
                # Quick externalize initiation
            }
                        self.simulation_params = {
                'mine': {'tau': 5.0, 'tau_domain': self._nodes},  # Faster mining improves tx availability moderately
                'retrieve_transaction_from_mempool': {'tau':0.1, 'tau_domain': self._nodes},
                # Processing
                'prepare_commit': {'tau': 0.5, 'tau_domain': self._nodes},  # Quickly move to commit stage
                'prepare_externalize_message': {'tau': 0.5, 'tau_domain': self._nodes},
                'nominate': {'tau': 0.5, 'tau_domain': self._nodes},  # Very frequent nominations
                'prepare_ballot': {'tau': 0.5, 'tau_domain': self._nodes},  # Rapid ballot preparation
                # Communication
                'retrieve_message_from_peer': {'tau': 0.1, 'tau_domain': self._nodes},  # Very fast message retrieval
                'receive_prepare_message': {'tau': 0.1, 'tau_domain': self._nodes},
                'receive_commit_message': {'tau': 0.1, 'tau_domain': self._nodes},  # Faster message processing
                'receive_externalize_msg': {'tau': 0.1, 'tau_domain': self._nodes} # Faster finalization processing
                # Quick externalize initiation
            }
            """
            self.simulation_params = {
                'mine': {'tau': 1.0, 'tau_domain': self._nodes},  # Faster mining improves tx availability moderately
                'retrieve_transaction_from_mempool': {'tau':1.0, 'tau_domain': self._nodes},
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
        print("THE CHECK IS ", check)
        # for node in self._nodes:
            # if not isinstance(node.externalize_broadcast_flags, SCPExternalize):
                # log.simulator.info(f"Node {node.name} has not finalized yet. Flag: {node.externalize_broadcast_flags}")
        return check

    def run(self):

        if self._verbosity:
            log.simulator.info('Started simulation vith verbosity level %s and %s nodes for simulation time %s.',
                               self._verbosity, self._n_nodes, self._max_simulation_time)

        if self._verbosity:
            log.simulator.debug('Creating %s nodes.', self._n_nodes)

        # self._nodes = Network.generate_nodes(n_nodes=self._n_nodes, topology='FULL')
        # self._nodes = Network.generate_nodes(n_nodes=self._n_nodes, topology='HARDCODE')
        #self._nodes = Network.generate_nodes(n_nodes=self._n_nodes, topology='ER')
        #self._nodes = Network.generate_nodes(n_nodes=self._n_nodes, topology='LUNCH')

        #self._mempool = Mempool()
        # self._mempool = Mempool(simulation_time=self._simulation_time)
        # self._mempool = Mempool(self._simulation_time)
        for node in self._nodes:
            node.attach_mempool(Mempool())

        # Run Gillespie algorithm
        if self._verbosity:
            log.simulator.debug('Running Gillespie algorithm.')

        # Simulation parameters for each event
        # tau_domain: None - tau defines a global probability of event
        #             List(Node) - tau defines a node-specific probability of event
        # TODO: Simulation parameters should be loaded from the config!

        # These are simulation params for HARDCODE - real topology  from Stellar Beat API
        """
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


        simulation_params = {
            'mine': {'tau': 1.0, 'tau_domain': None},
            # Communication group
            'retrieve_transaction_from_mempool': {'tau': 1.0, 'tau_domain': self._nodes},  # 1 second
            'nominate': {'tau': 1.0, 'tau_domain': self._nodes},
            'receive_commit_message': {'tau': 1.0, 'tau_domain': self._nodes},
            'receive_externalize_msg': {'tau': 1.0, 'tau_domain': self._nodes},
            # Processing group
            'retrieve_message_from_peer': {'tau':1.0, 'tau_domain': self._nodes},
            'prepare_ballot': {'tau': 1.0, 'tau_domain': self._nodes},
            'receive_prepare_message': {'tau': 1.0, 'tau_domain': self._nodes},
            'prepare_commit': {'tau': 1.0, 'tau_domain': self._nodes},
            'prepare_externalize_message': {'tau': 1.0, 'tau_domain': self._nodes}  # 6 seconds
        }
        
        simulation_params = {
            # EDIT MINE, SO THAT ITS OVER ALL NODES AND EACH NODE HAS LOCAL MEMPOOL
            # having self.nodes as domain affects the poisson distribution, so tau
            # has to be adjusted or total txs will scale based on no. of nodes
            'mine': {'tau': 3.0, 'tau_domain': self._nodes},
            # Communication group
            'retrieve_transaction_from_mempool': {'tau':1.0, 'tau_domain': self._nodes},  # 1 second
            'nominate': {'tau': 1.0, 'tau_domain': self._nodes},
            'receive_commit_message': {'tau': 1.0, 'tau_domain': self._nodes},
            'receive_externalize_msg': {'tau': 0.1, 'tau_domain': self._nodes},
            # Processing group
            'retrieve_message_from_peer': {'tau':1.0, 'tau_domain': self._nodes},
            'prepare_ballot': {'tau': 1.0, 'tau_domain': self._nodes},
            'receive_prepare_message': {'tau': 1.0, 'tau_domain': self._nodes},
            'prepare_commit': {'tau': 1.0, 'tau_domain': self._nodes},
            'prepare_externalize_message': {'tau': 1.0, 'tau_domain': self._nodes}  # 6 seconds
        }"""

        # ALL SIMULATION EVENTS COULD OCCUR AT ANY POINT, WHEN WE IMPLEMENT BALLOTING WE'LL HAVE TO
        # DISABLE NOMINATE

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

        # Initialize Gillespie with a collection of events and their probabilities
        # Then query it repeatedly to receive next event

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

            # TODO: CREATE TRANSACTION
            #  1. TRANSACTION IS RECEIVED BY A NODE (FROM EXTERNAL WALLET)
            # 2. THIS IS VALIDATED (IF ALREADY PRESENT, IS IT DOUBLE SPEND, IS IT IN LEDGER?)
            # 3. IF VALID, IT IS ADDED TO THE LOCAL MEMPOOL (ONLY ONE EXISTING IN SIMULATOR, THERE IS NO GLOBAL)
            # 4. ADD BROADCAST FLAG WITH THE RETRIEVED TXS - OR MESSAGE & FILTER WITHOUT USING BROADCAST FLAG
            # 5. 1-4 HAPPENS IN ONE EVENT IN "CREATE_TX...."

            # GOSSIPING OF TRANSACTON (SEPARATE EVENT)
            # 1. SAME MECHANISM FOR GOSSIPING AS EXISTING, ADD TO BROADCAST FLAG & OTHER RETRIEVES
            # 2. RECEIVING & SENDING NODES ARE SELECTED & TXS FROM BROADCAST FLAGS & 1 RANDOM ONE IS TAKEN BY RECEIVING NODE
            # 3. AFTER RECEIVAL, THE TX IS VALIDATED & IGNORED IF NOT VALID - ADDED TO MEMPOOL OR IGNORED

            case 'mine': # CREATE TRANSACTION

                # Mempool is responsible for handling the mine event
                #self._mempool.mine()
                node = np.random.choice(self._nodes)
                node.mempool.mine()
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


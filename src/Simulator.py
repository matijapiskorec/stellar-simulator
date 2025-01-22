"""
================================================
Simulator
================================================

Author: Matija Piskorec, Jaime de Vivero Woods
Last update: December 2024

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
import numpy as np

from Log import log
from Node import Node
from Gillespie import Gillespie
from FBAConsensus import FBAConsensus
from Network import Network
from Mempool import Mempool
from Globals import Globals
from Transaction import Transaction
from QuorumSet import QuorumSet
from API.NetworkSnapshotsAPIClient import NetworkSnapshotsAPIClient
from ConfigurationManager import ConfigManager

VERBOSITY_DEFAULT = 5
N_NODES_DEFAULT = 60

class Simulator:
    '''
    Command line (CLI) interface for the simulator.
    '''

    def __init__(self,verbosity=VERBOSITY_DEFAULT,n_nodes=N_NODES_DEFAULT,**kvargs):

        self._verbosity = verbosity
        self._n_nodes = n_nodes

        self._nodes = []

        # TODO: _max_simulation_time should be loaded from the config!
        self._max_simulation_time = 100
        # self._simulation_time = 0

        self._set_logging()

        # Total elapsed time doesn't include initialization!
        self.timeStart = time.time()

        self.average_transaction_count = None
        self.inter_ledger_time = 6  # Default to 6 seconds
        self.api_client = NetworkSnapshotsAPIClient()
        self.config_manager = ConfigManager()

    ## used for fetching samples from stellarbeat
    def fetch_and_parse_snapshot(self):
        """Fetch and parse the latest snapshot using NetworkSnapshotsAPIClient."""
        snapshot = self.api_client.get_node_snapshots() # configure at: [...] for time delta for the window of the timestamps to fetch from Stellarbeat
        if not snapshot:
            raise ValueError("Failed to fetch the latest snapshot.")

        self.nodes = []
        self.quorum_sets = []

        for node_data in snapshot:
            node_info = node_data.get("node")
            if node_info:
                # Parse Node data
                node = Node(
                    name=node_info.get("name"),
                    public_key=node_info.get("publicKey"),
                    host=node_info.get("host"),
                    version=node_info.get("versionStr")
                )
                self.nodes.append(node)

                # Parse QuorumSet data
                quorum_data = node_info.get("quorumSet")
                if quorum_data:
                    quorum_set = QuorumSet(
                        threshold=quorum_data.get("threshold"),
                        validators=quorum_data.get("validators"),
                        inner_quorum_sets=quorum_data.get("innerQuorumSets")
                    )
                    self.quorum_sets.append(quorum_set)

        print(f"Parsed {len(self.nodes)} nodes and {len(self.quorum_sets)} quorum sets.")

    def set_average_transaction_count(self, average_tx_count):
        """Set the average transaction count for the simulator."""
        self.average_transaction_count = Transaction(average_tx_count)
        print(f"Average transaction count set to: {self.average_transaction_count.count}")

    def adjust_inter_ledger_time(self, target_time):
        """Adjust inter-ledger time parameter in the simulator."""
        self.inter_ledger_time = target_time
        print(f"Inter-ledger time adjusted to: {self.inter_ledger_time} seconds")

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
        self._nodes = self.fetch_and_parse_snapshot()# Network.generate_nodes(n_nodes=self._n_nodes, topology='ER')

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
        simulation_params = {'mine':{'tau':5.0,
                                     'tau_domain':None},
                             'retrieve_transaction_from_mempool':{'tau':5.0,
                                                      'tau_domain':self._nodes},
                             'nominate':{'tau':5.0,
                                       'tau_domain':self._nodes},
                             'retrieve_message_from_peer':{'tau':2.0,
                                       'tau_domain':self._nodes},
                             'prepare_ballot': {'tau':7.0,
                                       'tau_domain':self._nodes},
                             'receive_prepare_message': {'tau':1.0,
                                       'tau_domain':self._nodes},
                             'prepare_commit': {'tau':7.0,
                                       'tau_domain':self._nodes},
                             'receive_commit_message': {'tau':1.0,
                                       'tau_domain':self._nodes},
                             'prepare_externalize_message': {'tau': 3.0,
                                       'tau_domain':self._nodes},
                             'receive_externalize_msg': {'tau': 1.0,
                                       'tau_domain':self._nodes}
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


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
import time

import numpy as np

from Log import log
from Node import Node
from Gillespie import Gillespie
from POWConsensus import POWConsensus
from Network import Network
from Mempool import Mempool
# import Globals
from Globals import Globals

VERBOSITY_DEFAULT = 5
N_NODES_DEFAULT = 50

class Simulator:
    '''
    Command line (CLI) interface for the simulator.
    '''

    def __init__(self,verbosity=VERBOSITY_DEFAULT,n_nodes=N_NODES_DEFAULT, simulation_params=None,**kvargs):

        self._verbosity = verbosity
        self._n_nodes = n_nodes

        self._nodes = []

        # TODO: _max_simulation_time should be loaded from the config!
        self._max_simulation_time = 5
        # self._simulation_time = 0

        self._set_logging()

        # Total elapsed time doesn't include initialization!
        self.timeStart = time.time()

        self.simulation_params = simulation_params

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
            log.simulator.info(
                'Started simulation with verbosity level %s and %s nodes.',
                self._verbosity, self._n_nodes
            )

        if self._verbosity:
            log.simulator.debug('Creating %s nodes.', self._n_nodes)

        # PoW‐style peer network: Erdős–Rényi with avg degree ≈10 (default)
        # (remove the old topology arg)
        self._nodes = Network.generate_nodes(
            topology='BA',
            n_nodes=self._n_nodes,
            degree=5,  # or pull from self._config if you’ve made it configurable
        )

        # give each node its own mempool
        for node in self._nodes:
            node.attach_mempool(Mempool())

        if self._verbosity:
            log.simulator.debug('Running Gillespie algorithm.')

        """simulation_params = {
            # EDIT MINE, SO THAT ITS OVER ALL NODES AND EACH NODE HAS LOCAL MEMPOOL
            # having self.nodes as domain affects the poisson distribution, so tau
            # has to be adjusted or total txs will scale based on no. of nodes
            'create transaction': {'tau': 1.0, 'tau_domain': self._nodes},
            'retrieve transaction': {'tau': 1.0, 'tau_domain': self._nodes},
            'mine' : {'tau': 5.0, 'tau_domain': self._nodes},
            'receive block': {'tau': 2.5, 'tau_domain': self._nodes},

        }"""
        if self.simulation_params is None:
            self.simulation_params = {
                'create transaction': {'tau': 1.0, 'tau_domain': self._nodes}, # avg tx creation of 1.1 per node
                'retrieve transaction': {'tau': 1.0, 'tau_domain': self._nodes},
                'mine': {'tau': 10.0, 'tau_domain': self._nodes},
                'receive block': {'tau': 0.01, 'tau_domain': self._nodes}
            }

        else:
            for v in self.simulation_params.values():
                if isinstance(v, dict) and v.get('tau_domain') == "self._nodes":
                    v['tau_domain'] = self._nodes

        print("Parsed simulation_params for this run:", self.simulation_params)

        # Concatenate events you get from the FBAConsensus and Node class
        self._events = [*POWConsensus.get_events(), *Node.get_events()]

        # Set the simulation parameters of all events for which we have them
        for event in self._events:
            if event.name in self.simulation_params:
                event.simulation_params = self.simulation_params[event.name]
            else:
                if self._verbosity:
                    log.simulator.warning('No simulation parameters for event %s - igoring the event!', event.name)

        # Remove events for which we don't have simulation parameters
        self._events = [event for event in self._events if event.simulation_params is not None]

        print("Loaded events:")
        for event in self._events:
            print(f"  {event.name} — tau: {event.simulation_params.get('tau')}")

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

            case 'mine': # CREATE TRANSACTION
                # Mempool is responsible for handling the mine event
                #self._mempool.mine()
                node = np.random.choice(self._nodes)
                node.mine()

                #node = np.random.choice(self._nodes)
                #node.mempool.mine()
                # Globals.mempool.mine()
            case 'create transaction':
                node = np.random.choice(self._nodes)
                node.create_transaction()

            case 'retrieve transaction':
                node = np.random.choice(self._nodes)
                node.receive_txs_from_peer()
                # Choose a random node which retrieves the transaction from mempool.
                #node_random = np.random.choice(self._nodes)

                # Send the event to the respective node and the mempool
                #node_random.retrieve_transaction_from_mempool()

            case 'receive block':
                node = np.random.choice(self._nodes)
                node.receive_block_from_peer()



if __name__=='__main__':

    # Parsing arguments from the command line
    parser=argparse.ArgumentParser()
    parser.add_argument("--verbosity","-v", type=int, default=VERBOSITY_DEFAULT, help="Verbosity level (0-5).")
    parser.add_argument("--nodes","-n", type=int, default=N_NODES_DEFAULT, help="Number of nodes.")
    args = parser.parse_args()

    simulator = Simulator(verbosity=args.verbosity,n_nodes=args.nodes)

    simulator.run()


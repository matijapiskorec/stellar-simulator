"""
=========================
SimulatorTest
=========================

Author: Matija Piskorec, Jaime de Vivero Woods, Azizbek Asadov
Last update: Nov 2024

SimulatorTest message class.
"""

import unittest

from src.Simulator import Simulator
from src.Gillespie import Gillespie
from src.Event import Event
from src.Log import log

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


if __name__ == "__main__":
    # Comment out if you are running multiple tests and don't want any output!
    log.set_level(5)
    unittest.main()

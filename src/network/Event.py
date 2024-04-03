"""
=========================
Event
=========================

Author: Matija Piskorec
Last update: August 2023

Event class.
"""

from src.common.Log import log

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

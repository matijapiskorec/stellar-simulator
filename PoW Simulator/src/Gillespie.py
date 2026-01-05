"""
=========================
Gillespie
=========================

Author: Matija Piskorec
Last update: August 2023

Gillespie algorithm class.
"""

from Log import log
from Node import Node
from Event import Event

import numpy as np

class Gillespie:

    def __init__(self, events, max_time):

        self.events = events
        self.max_time = max_time

        assert all([isinstance(event,Event) for event in self.events])
        assert all([event.simulation_params is not None for event in self.events])

        self.time = 0.0

        # Probabilities for each specific event happening to a specific node
        self.node_probabilities = {}

        # Waiting times until a specific event happens
        self.event_lambdas = []
        for event in self.events:

            if event.simulation_params['tau_domain'] is not None:
                tau_domain_len = len(event.simulation_params['tau_domain'])
            else:
                tau_domain_len = 1.0

            self.event_lambdas.append(tau_domain_len*(1.0/event.simulation_params['tau']))

        self.lambda_sum = np.sum(self.event_lambdas)

        # Event probabilities
        self.event_probabilities = self.event_lambdas/self.lambda_sum

        log.gillespie.info('Initialized Gillespie algorithm.')

    def next_event(self):
        # Time increment to the next random event
        time_increment = -np.log(np.random.random()) / self.lambda_sum

        # Time update
        self.time = self.time + time_increment

        # Random event happens
        event_random = np.random.choice(self.events, p=self.event_probabilities)

        # TODO: Events will be handled in the Simulator rather than in Gillespie!
        return [event_random, self.time]

    def check_max_time(self):
        # TODO: If check_max_time is used to stop the simulation, then the last event will happen after max_time!
        return self.time < self.max_time



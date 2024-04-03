"""
=========================
Gillespie
=========================

Author: Matija Piskorec
Last update: August 2023

Gillespie algorithm class.
"""

from src.common.Log import log
from Event import Event

import numpy as np

from src.common.Log import log
from Event import Event

import numpy as np

class Gillespie:

    def __init__(self, events, max_time, sync_events_periods=None):

        self.events = events
        self.max_time = max_time
        self.sync_events_periods = sync_events_periods or {}  # Initialize sync events with empty dict

        assert all([isinstance(event, Event) for event in self.events])
        assert all([event.simulation_params is not None for event in self.events])

        self.time = 0.0
        self.next_sync_event_times = {}  # Store timings for next occurrences of sync events

        # Calculate asynchronous event probabilities
        self.event_lambdas = []
        self.event_probabilities = []
        for event in self.events:
            if not event.is_synchronous:  # Only include asynchronous events
                tau_avg = event.calculate_average_tau()  # Use a method for accurate tau calculation
                self.event_lambdas.append(tau_avg)
            self.event_probabilities.append(0)  # Set initial probabilities to 0 for calculation later

        self.lambda_sum = np.sum(self.event_lambdas)
        self.event_probabilities = np.array(self.event_probabilities)  # Convert to NumPy array for easier handling
        self.update_async_event_probabilities()  # Recalculate probabilities with accurate tau values

        log.gillespie.info('Initialized Gillespie algorithm.')

    def next_event(self):

        if self.time >= self.max_time:
            return None  # Stop simulation if max_time reached

        # Handle synchronous events with fixed periods
        next_sync_event, next_sync_time = self.get_next_sync_event()
        if next_sync_event and next_sync_time <= self.time:
            self.time = next_sync_time
            return next_sync_event

        # Handle asynchronous events
        time_increment = -np.log(np.random.random()) / self.lambda_sum
        self.time += time_increment
        event_random = np.random.choice(self.events, p=self.event_probabilities)

        return [event_random, self.time]

    def update_async_event_probabilities(self):
        self.event_probabilities[:len(self.event_lambdas)] = self.event_lambdas / self.lambda_sum

    def get_next_sync_event(self):
        min_time = min(self.next_sync_event_times.values())  # Find next sync event time
        next_event = None
        for event, time in self.next_sync_event_times.items():
            if time == min_time:
                next_event = event
                self.next_sync_event_times[event] += self.sync_events_periods[event]  # Schedule next occurrence
                break
        return next_event, min_time

    def check_max_time(self):
        return self.time < self.max_time


# class Gillespie:
#
#     def __init__(self, events, max_time):
#
#         self.events = events
#         self.max_time = max_time
#
#         assert all([isinstance(event,Event) for event in self.events])
#         assert all([event.simulation_params is not None for event in self.events])
#
#         self.time = 0.0
#
#         # Probabilities for each specific event happening to a specific node
#         self.node_probabilities = {}
#
#         # Waiting times until a specific event happens
#         self.event_lambdas = []
#         for event in self.events:
#
#             if event.simulation_params['tau_domain'] is not None:
#                 tau_domain_len = len(event.simulation_params['tau_domain'])
#             else:
#                 tau_domain_len = 1.0
#
#             self.event_lambdas.append(tau_domain_len*(1.0/event.simulation_params['tau']))
#
#         self.lambda_sum = np.sum(self.event_lambdas)
#
#         # Event probabilities
#         self.event_probabilities = self.event_lambdas/self.lambda_sum
#
#         log.gillespie.info('Initialized Gillespie algorithm.')
#
#     def next_event(self):
#
#         # TODO: We are assuming that all events are asynchronous, while this is not true!
#         # TODO: - Synchronous events: 1) slot (every 5 seconds), 2) ballot counter timeout
#
#         # Time increment to the next random event
#         time_increment = -np.log(np.random.random()) / self.lambda_sum
#
#         # Time update
#         self.time = self.time + time_increment
#
#         # Random event happens
#         event_random = np.random.choice(self.events, p=self.event_probabilities)
#
#         # TODO: Events will be handled in the Simulator rather than in Gillespie!
#         return [event_random, self.time]
#
#     def check_max_time(self):
#         # TODO: If check_max_time is used to stop the simulation, then the last event will happen after max_time!
#         return self.time < self.max_time
#

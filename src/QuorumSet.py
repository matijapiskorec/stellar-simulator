"""
=========================
Quorum Set
=========================

Author: Matija Piskorec
Last update: August 2023

QuorumSet class.
"""
import math

from Log import log

import numpy as np

THRESHOLD_DEFAULT = 10 # 10% threshold by default

class QuorumSet():

    def __init__(self, node, **kvargs):

        if 'threshold' in kvargs:
            assert type(kvargs['threshold']) in (float, int)
            assert kvargs['threshold'] <= 100 and kvargs['threshold'] > 0  # threshold must be percentile

        # Quorum set knows to which node it belongs to
        self.node = node
        self.threshold = kvargs['threshold'] if 'threshold' in kvargs else THRESHOLD_DEFAULT

        self.nodes = []
        self.inner_sets = [] # will keep to 1 layer of depth for now, rarely gets deeper

        log.quorum.info('Initialized quorum set for Node %s, threshold=%s, nodes=%s.',
                        self.node, self.threshold, self.nodes, self.inner_sets)

    def __repr__(self):
        return '[Quorum Set: threshold=%(threshold)s, nodes=%(nodes)s.' % self.__dict__

    def is_inside(self, node):
        return len(list(filter(lambda x: x == node, self.nodes))) > 0

    # Remove node from quorum set
    def remove(self, node):
        self.nodes = filter(lambda x: x != node, self.nodes)
        return

    # Set quorum to the nodes
    def set(self, nodes, inner_sets):

        # If there is only one node as input, convert it to list so that we can iterate over it
        if type(nodes) is not list:
            nodes = [nodes]

        # TODO: Perform duplicate checks while adding nodes to the quorum!
        self.nodes = nodes
        self.inner_sets = inner_sets if inner_sets is not None else []

        log.quorum.info('Set nodes %s as the quorum set of Node %s.', nodes, self.node)

        return

    def get_node(self):
        # If there are no nodes in the quorum set, return None
        if len(self.nodes) == 0:
            return None
        else:
            # return np.random.choice(self.nodes)
            return np.random.choice([node for node in self.nodes if node != self.node])

    def get_nodes(self):
        return self.nodes.copy()

    def get_inner_sets(self):
        return self.inner_sets.copy()

    # TODO: Check minimum_quorum() method because it looks strange, I don't understand it!
    @property
    def minimum_quorum(self):
        # Minimum number of nodes (round up) required to reach threshold
        return math.ceil((len(self.nodes) + 1) * (self.threshold / 100))

    def get_quorum(self):
        return self.get_nodes(), self.get_inner_sets()

    def check_threshold(self, val, node_statement_counter):
        node_counter = 0
        inner_set_counter = 0

        for node in self.nodes:
            if node in node_statement_counter[val.hash]["voted"] or node in node_statement_counter[val.hash]["accepted"]:
                node_counter += 1

        for set in self.inner_sets:
            for node in set:
                if node in node_statement_counter[val.hash]["voted"] or node in node_statement_counter[val]["acccepted"]:
                    inner_set_counter += 1



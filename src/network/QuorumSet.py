"""
=========================
Quorum Set
=========================

Author: Matija Piskorec
Last update: August 2023

QuorumSet class.
"""
import math

from src.common.Log import log

import numpy as np

THRESHOLD_DEFAULT = 10 # 10% threshold by default

class QuorumSet():
    def __init__(self, node, **kvargs):
        if 'threshold' in kvargs:
            assert type(kvargs['threshold']) in (float, int)
            assert kvargs['threshold'] <= 100 and kvargs['threshold'] > 0  # threshold must be percentile

        # Quorum set knows to which node it belongs to
        self.node = node

        # No input nodes should be of different type than Node
        # TODO: We cannot check for Node instance in QuorumSet class because of circular import!
        # assert len([not isinstance(node,Node) for node in nodes])<1 # Allows for empty list of nodes!

        self.threshold = kvargs['threshold'] if 'threshold' in kvargs else THRESHOLD_DEFAULT

        # TODO: Important otherwise all QuorumSets will share a list of nodes!
        self.nodes = set()

        log.quorum.info('Initialized quorum set for Node %s, threshold=%s, nodes=%s.',
                        self.node, self.threshold, self.nodes)

    def __repr__(self):
        return '[Quorum Set: threshold=%(threshold)s, nodes=%(nodes)s.' % self.__dict__

    def is_inside(self, node):
        return len(list(filter(lambda x: x == node, self.nodes))) > 0

    # Remove node from quorum set
    def remove(self, node):
        self.nodes = filter(lambda x: x != node, self.nodes)
        return

    # # Add nodes to quorum
    # # TODO: Consider removing QuorumSet.add() because we are only using QuorumSet.set()!
    # def add(self, nodes):

    #     # If there is only one node as input, convert it to list so that we can iterate over it
    #     if type(nodes) is not list:
    #         nodes = [nodes]

    #     # No input nodes should be of different type than Node
    #     # TODO: We cannot check for Node instance in QuorumSet class because of circular import!
    #     # assert len([not isinstance(node,Node) for node in nodes])<1 # Allows for empty list of nodes!

    #     for node in nodes:
    #         # Only add the node to the quorum set if it isn't already there!
    #         # Quorum set always contains the node itself, so we allow to add it to the quorum set 
    #         if (node not in self.nodes):
    #             self.nodes.append(node)
    #             log.quorum.info('Added node %s to quorum set of Node %s.', node, self.node)

    #     return

    def add(self, nodes):
        """Adds nodes to the quorum set, removing duplicates."""

        if type(nodes) is not list:
            nodes = [nodes]

        self.nodes.update(nodes)
        log.quorum.info('Added nodes %s to quorum set of Node %s.', nodes, self.node)

    # Set quorum to the nodes
    def set(self, nodes):
        if type(nodes) is not list:
            nodes = [nodes]
        self.nodes = set(nodes)  # Use a set to eliminate duplicates
        log.quorum.info('Set nodes %s as the quorum set of Node %s.', nodes, self.node)

    def get_node(self):
        return list(self.nodes)

    def get_nodes(self):
        # TODO: Should we return self.nodes.copy() instead?
        return self.nodes

    @property
    def minimum_quorum(self):
        # Minimum number of nodes (round up) required to reach threshold
        # return math.ceil((len(self.nodes) + 1) * (self.threshold / 100))
        return math.ceil(len(self.nodes) * (self.threshold / 100)) # should be

    # TODO: Quorum is constructed by a union of all quorum sets of nodes in the quorum set!
    def get_quorum(self):
        # nodes = set().union(*[node.quorum_set.get_nodes() for node in self.node.quorum_set.get_nodes()])
        # return nodes
        return self.nodes


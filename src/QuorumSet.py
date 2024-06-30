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
from typing import List

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
        self.nodes = []

        log.quorum.info('Initialized quorum set for Node %s, threshold=%s, nodes=%s.',
                        self.node, self.threshold, self.nodes)

    def __repr__(self):
        return '[Quorum Set: threshold=%(threshold)s, nodes=%(nodes)s.' % self.__dict__

    def is_inside(self, node):
        return len(list(filter(lambda x: x == node, self.nodes))) > 0

    # Remove node from quorum set
    def remove(self, node_id: int):
        # self.nodes = filter(lambda x: x != node, self.nodes)
        # return
        self.nodes.discard(node_id)
        log.quorum.info(f'Removed node {node_id} from quorum set.')

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

    # Set quorum to the nodes
    def set(self, nodes):

        # If there is only one node as input, convert it to list so that we can iterate over it
        if type(nodes) is not list:
            nodes = [nodes]

        # TODO: Perform duplicate checks while adding nodes to the quorum!
        self.nodes = nodes

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
        # TODO: Should we return self.nodes.copy() instead?
        return self.nodes

    # TODO: Check minimum_quorum() method because it looks strange, I don't understand it!
    @property
    def minimum_quorum(self):
        # Minimum number of nodes (round up) required to reach threshold
        return math.ceil((len(self.nodes) + 1) * (self.threshold / 100))

    # TODO: Quorum is constructed by a union of all quorum sets of nodes in the quorum set!
    def get_quorum(self):
        nodes = set().union(*[node.quorum_set.get_nodes() for node in self.node.quorum_set.get_nodes()])
        return nodes

    def is_quorum_reached(self, votes: set) -> bool:
        return len(votes.intersection(self.nodes)) >= self.threshold

    def add_node(self, node_id: int):
        self.nodes.add(node_id)
        log.quorum.info(f'Added node {node_id} to quorum set.')

    def remove_node(self, node_id: int):
        self.nodes.discard(node_id)


"""
=========================
QuorumSet
=========================

Author: Matija Piskorec
Last update: May 2024
Last update by: Azizbek A.

QuorumSet class.
"""

import math
import numpy as np
from Log import log

THRESHOLD_DEFAULT = 10

class QuorumSet:

    def __init__(self, node, **kvargs):
        """
        Initializes a QuorumSet instance.

        :param node: The node to which the quorum set belongs.
        :param kvargs: Additional keyword arguments for quorum set properties.
        """
        if 'threshold' in kvargs:
            assert type(kvargs['threshold']) in (float, int)
            assert kvargs['threshold'] <= 100 and kvargs['threshold'] > 0  # threshold must be percentile

        # Quorum set knows to which node it belongs to
        self.node = node

        self.threshold = kvargs['threshold'] if 'threshold' in kvargs else THRESHOLD_DEFAULT

        # Initialize the list of nodes in the quorum set
        self.nodes = []

        log.quorum.info('Initialized quorum set for Node %s, threshold=%s, nodes=%s.',
                        self.node.name, self.threshold, self.nodes)

    def __repr__(self):
        return '[Quorum Set: threshold=%s, nodes=%s]' % (self.threshold, self.nodes)

    def is_inside(self, node):
        """
        Checks if a node is inside the quorum set.

        :param node: The node to check.
        :return: True if the node is inside, False otherwise.
        """
        return node in self.nodes

    def remove(self, node):
        """
        Removes a node from the quorum set.

        :param node: The node to remove.
        """
        self.nodes = [n for n in self.nodes if n != node]
        log.quorum.info('Removed node %s from quorum set of Node %s.', node.name, self.node.name)

    def set(self, nodes):
        """
        Sets the quorum set for the node.

        :param nodes: The nodes to set.
        """
        if not isinstance(nodes, list):
            nodes = [nodes]

        self.nodes = nodes

        log.quorum.info('Set nodes %s as the quorum set of Node %s.', nodes, self.node.name)

    def get_node(self):
        """
        Retrieves a random node from the quorum set.

        :return: A random node or None if the quorum set is empty.
        """
        if not self.nodes:
            return None
        return np.random.choice([node for node in self.nodes if node != self.node])

    def get_nodes(self):
        """
        Retrieves the nodes in the quorum set.

        :return: The list of nodes.
        """
        return self.nodes.copy()

    @property
    def minimum_quorum(self):
        """
        Calculates the minimum quorum size.

        :return: The minimum quorum size.
        """
        return math.ceil((len(self.nodes) + 1) * (self.threshold / 100))

    def get_quorum(self):
        """
        Retrieves the quorum for the node.

        :return: The set of nodes in the quorum.
        """
        nodes = set().union(*[node.quorum_set.get_nodes() for node in self.nodes])
        return nodes




# """
# =========================
# Quorum Set
# =========================

# Author: Matija Piskorec
# Last update: August 2023

# QuorumSet class.
# """
# import math

# from Log import log

# import numpy as np

# THRESHOLD_DEFAULT = 10 # 10% threshold by default

# class QuorumSet():

#     def __init__(self, node, **kvargs):

#         if 'threshold' in kvargs:
#             assert type(kvargs['threshold']) in (float, int)
#             assert kvargs['threshold'] <= 100 and kvargs['threshold'] > 0  # threshold must be percentile

#         # Quorum set knows to which node it belongs to
#         self.node = node

#         # No input nodes should be of different type than Node
#         # TODO: We cannot check for Node instance in QuorumSet class because of circular import!
#         # assert len([not isinstance(node,Node) for node in nodes])<1 # Allows for empty list of nodes!

#         self.threshold = kvargs['threshold'] if 'threshold' in kvargs else THRESHOLD_DEFAULT

#         # TODO: Important otherwise all QuorumSets will share a list of nodes!
#         self.nodes = []

#         log.quorum.info('Initialized quorum set for Node %s, threshold=%s, nodes=%s.',
#                         self.node, self.threshold, self.nodes)

#     def __repr__(self):
#         return '[Quorum Set: threshold=%(threshold)s, nodes=%(nodes)s.' % self.__dict__

#     def is_inside(self, node):
#         return len(list(filter(lambda x: x == node, self.nodes))) > 0

#     # Remove node from quorum set
#     def remove(self, node):
#         self.nodes = filter(lambda x: x != node, self.nodes)
#         return

#     # # Add nodes to quorum
#     # # TODO: Consider removing QuorumSet.add() because we are only using QuorumSet.set()!
#     # def add(self, nodes):

#     #     # If there is only one node as input, convert it to list so that we can iterate over it
#     #     if type(nodes) is not list:
#     #         nodes = [nodes]

#     #     # No input nodes should be of different type than Node
#     #     # TODO: We cannot check for Node instance in QuorumSet class because of circular import!
#     #     # assert len([not isinstance(node,Node) for node in nodes])<1 # Allows for empty list of nodes!

#     #     for node in nodes:
#     #         # Only add the node to the quorum set if it isn't already there!
#     #         # Quorum set always contains the node itself, so we allow to add it to the quorum set 
#     #         if (node not in self.nodes):
#     #             self.nodes.append(node)
#     #             log.quorum.info('Added node %s to quorum set of Node %s.', node, self.node)

#     #     return

#     # Set quorum to the nodes
#     def set(self, nodes):

#         # If there is only one node as input, convert it to list so that we can iterate over it
#         if type(nodes) is not list:
#             nodes = [nodes]

#         # TODO: Perform duplicate checks while adding nodes to the quorum!
#         self.nodes = nodes

#         log.quorum.info('Set nodes %s as the quorum set of Node %s.', nodes, self.node)

#         return

#     def get_node(self):
#         # If there are no nodes in the quorum set, return None
#         if len(self.nodes) == 0:
#             return None
#         else:
#             # return np.random.choice(self.nodes)
#             return np.random.choice([node for node in self.nodes if node != self.node])

#     def get_nodes(self):
#         # TODO: Should we return self.nodes.copy() instead?
#         return self.nodes

#     # TODO: Check minimum_quorum() method because it looks strange, I don't understand it!
#     @property
#     def minimum_quorum(self):
#         # Minimum number of nodes (round up) required to reach threshold
#         return math.ceil((len(self.nodes) + 1) * (self.threshold / 100))

#     # TODO: Quorum is constructed by a union of all quorum sets of nodes in the quorum set!
#     def get_quorum(self):
#         nodes = set().union(*[node.quorum_set.get_nodes() for node in self.node.quorum_set.get_nodes()])
#         return nodes


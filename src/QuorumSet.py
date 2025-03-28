"""
=========================
Quorum Set
=========================

Author: Matija Piskorec, Jaime de Vivero Woods
Last update: December 2024
QuorumSet class.
"""
import math
import random
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

        log.quorum.info('Initialized quorum set for Node %s, threshold=%s, nodes=%s, inner sets=%s.',
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
        log.quorum.info('Set nodes %s as the inner sets of Node %s.', inner_sets, self.node)

        return

    def get_node(self):
        # If there are no nodes in the quorum set, return None
        if len(self.nodes) == 0:
            return None
        else:
            return np.random.choice([node for node in self.nodes if node != self.node])

    def get_nodes(self):
        return self.nodes.copy()

    def get_inner_sets(self):
        return self.inner_sets.copy()

    @property
    def minimum_quorum(self):
        # Minimum number of nodes (round up) required to reach threshold
        return math.ceil((len(self.nodes) + 1) * (self.threshold / 100))

    def get_quorum(self):
        return self.get_nodes(), self.get_inner_sets()

    # This function checks if the quorum meets threshold - it checks every node, it doesn't check for nested QuorumSlices
    def check_threshold(self, val, quorum, threshold, node_statement_counter):
        signed_counter = 0

        for node in quorum:
            if node in node_statement_counter[val.hash]["voted"] or node in node_statement_counter[val.hash]["accepted"]:
                signed_counter += 1

        if signed_counter >= threshold:
            return True
        else:
            return False

    def check_prepare_threshold(self, ballot, quorum, threshold, prepare_statement_counter):
        signed_counter = 0
        seen = set()
        if ballot.value not in prepare_statement_counter:
            return False

        # For the ballot provided, iterate over voted, accepted & if counts meet threshold return True
        for state in ('voted', 'accepted'):
            for node in prepare_statement_counter[ballot.value].get(state, set()):
                if node in quorum and node not in seen:
                    seen.add(node)
                    signed_counter += 1

        if signed_counter >= threshold:
            return True
        else:
            return False

    def check_commit_threshold(self, ballot, quorum, threshold, commit_statement_counter):
        signed_counter = 0
        seen = set()
        if ballot.value not in commit_statement_counter:
            return False

        # For the ballot provided, iterate over voted, accepted & if counts meet threshold return True
        for state in ('voted', 'accepted'):
            for node in commit_statement_counter[ballot.value].get(state, set()):
                if node in quorum and node not in seen:
                    seen.add(node)
                    signed_counter += 1

        if signed_counter >= threshold:
            return True
        else:
            return False

    def check_inner_set_blocking_threshold(self, calling_node, val, quorum):
        # Check if any node in the Quorum has issued message "m" - not including the node itself
        count = 0
        for node in quorum:
            if (node != calling_node) and (node in calling_node.statement_counter[val.hash]["voted"]) or (node != calling_node) and (node in calling_node.statement_counter[val.hash]["accepted"]):
                count += 1

        return count

    def get_nodes_with_broadcast_prepare_msgs(self, calling_node, quorum):
        broadcast_nodes = []
        for node in quorum:
            if (node != calling_node) and len(node.ballot_prepare_broadcast_flags) >= 1:
                broadcast_nodes.append(node)

        return broadcast_nodes

    def retrieve_random_peer(self, calling_node):
        flat_list = [node for node in self.nodes if node != calling_node]

        for inner_set in self.inner_sets:

            if hasattr(inner_set, "name"):
                if inner_set != calling_node:
                    flat_list.append(inner_set)

        return random.choice(flat_list) if flat_list else None

    def weight(self, v):
        count = self.nodes.count(v) # Count how many times 'v' appears in slices

        # Include inner quorum sets
        for inner_set in self.inner_sets:
            if isinstance(inner_set, list):
                if v in inner_set:
                    count += 1
            elif v == inner_set:
                count += 1

        # Compute fraction of quorum slices that contain 'v'
        total_slices = len(self.nodes) + len(self.inner_sets)

        if self == v:
            count = total_slices
            return count / total_slices

        if total_slices == 0:
            return 0.0  # Avoid division by zero

        return count / total_slices
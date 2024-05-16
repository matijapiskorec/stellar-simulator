"""
=========================
Network
=========================

Author: Matija Piskorec
Last update: August 2023

Network class. Setup Stellar validator network by initializing nodes and setting their quorum sets based on a predefined topology.
"""

from Log import log
from Node import Node
from QuorumSet import QuorumSet

import networkx as nx

class Network():

    topologies = ['FULL','ER']

    @classmethod
    def generate_nodes(cls,n_nodes=2,topology='FULL'):

        assert n_nodes > 0
        assert topology in cls.topologies

        nodes = []

        # Create nodes
        for i in range(n_nodes):
            nodes.append(Node(str(i)))
            log.network.debug('Node created: %s', nodes[-1])

        log.network.debug('Calculating quorum sets based on the network topology=%s',topology)

        # Generate network topology by altering nodes quorum sets
        match topology:
            case 'FULL':
                # We add all nodes to the quorum set of each node, including the node itself
                for node in nodes:
                    log.network.debug('Adding nodes %s to the quorum set of Node %s', nodes, node)
                    node.set_quorum(nodes)
            case 'ER':
                graph = nx.fast_gnp_random_graph(n_nodes,0.5) # make a random graph - could include all or only a few, some nodes may have many connections and some few or none
                lcc_set = max(nx.connected_components(graph), key=len) # LCC is the main node with the most connections
                missing = list(set(int(node.name) for node in nodes) - lcc_set) # nodes are not included in any quorum set and are considered "missing" in the context of the simulation
                if len(missing) > 0:
                    # Now there are nodes with no quorum set, so they cannot gossip messages!
                    # TODO: Consider removing nodes which are not part of anyone's quorum set!
                    log.network.debug('Nodes %s are not part of the LCC so they are excluded from all quorum sets!',
                                      missing)
                for node in nodes:
                    filtered_nodes = [nodes[edge[1]] for edge in graph.edges(int(node.name))]
                    # Adding the node itself to the set of nodes for the quorum set
                    filtered_nodes.append(node)
                    log.network.debug('Adding nodes %s to the quorum set of Node %s',
                                      filtered_nodes, node)
                    node.set_quorum(filtered_nodes)

        return nodes

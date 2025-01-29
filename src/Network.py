"""
=========================
Network
=========================

Author: Matija Piskorec, Jaime de Vivero Woods
Last update: July 2024

Network class. Setup Stellar validator network by initializing nodes and setting their quorum sets based on a predefined topology.
"""

from Log import log
from Node import Node
from QuorumSet import QuorumSet
import json
import networkx as nx

class Network():

    topologies = ['FULL','ER', 'HARDCODE']

    """ 
    @classmethod
    def parse_all_validators(file_path):
        
        Parse the all_validators.json file and create Node objects with quorum sets.

        :param file_path: Path to the all_validators.json file.
        :return: Dictionary of Node objects indexed by their IDs.
        
        with open(file_path, 'r') as file:
            data = json.load(file)

        nodes = {}

        for validator in data.get("validators", []):
            node_id = validator["name"]
            threshold = validator["threshold"]
            node_list = validator.get("nodes", [])
            inner_sets = validator.get("inner_sets", [])

            # Initialize or retrieve the Node object
            if node_id not in nodes:
                nodes[node_id] = Node(node_id)

            # Set quorum configuration for the Node
            nodes[node_id].set_quorum(threshold, node_list, inner_sets)

        return nodes
    """

    @classmethod
    def parse_all_validators(cls, file_path):
        """
        Parse the all_validators.json file and create Node objects with quorum sets.

        :param file_path: Path to the all_validators.json file.
        :return: Dictionary of Node objects indexed by their IDs.
        """
        with open(file_path, 'r') as file:
            data = json.load(file)

        nodes = {}

        for validator in data:
            node_id = validator["publicKey"]
            quorum_sets = validator.get("quorumSet", [])

            # Initialize or retrieve the Node object
            if node_id not in nodes:
                nodes[node_id] = Node(node_id)

            # Extract quorum set information
            for quorum in quorum_sets:
                threshold = quorum.get("threshold", 1)  # Default threshold to 1 if not present
                node_list = quorum.get("validators", [])
                inner_sets = quorum.get("inner_sets", [])

                nodes[node_id].set_quorum(threshold, node_list, inner_sets)

        return nodes

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
                    node.set_quorum(nodes, [])
            case 'ER':
                # Instead of adding all nodes frpm the graph to QuorumSet, we make a distribution so some also go into inner sets
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

                    if len(filtered_nodes) > 1:
                        filter_distribution = len(filtered_nodes)//2 # Filter nodes for Quorums as half to Quorum and half to inner sets

                        quorum_distribution = filtered_nodes[:filter_distribution]
                        inner_quorum_distribution = filtered_nodes[filter_distribution:]
                        quorum_distribution.append(node)
                        log.network.debug('Adding nodes %s to the quorum set of Node %s', quorum_distribution, node)

                        if len(inner_quorum_distribution) > 1: # If more than 2 nodes filtered, then define 2 inner sets for the QuorumSet
                            inner_set_distribution = len(inner_quorum_distribution) // 2 # Stick to only 2 inner sets per node for now
                            inner_set1 = inner_quorum_distribution[inner_set_distribution:]
                            inner_set2 = inner_quorum_distribution[:inner_set_distribution]
                            inner_set1.append(node)
                            inner_set2.append(node)
                            log.network.debug('Adding nodes %s to inner set 1, and nodes %s to inner set 2 of Node %s', inner_set1, inner_set2, node)
                            node.set_quorum(nodes=quorum_distribution, inner_sets=[inner_set1, inner_set2])

                        else: # In the case where only 2 nodes are added to Quorum only one inner set defined
                            inner_quorum_distribution.append(node)
                            log.network.debug('Adding nodes %s to the inner set of Node %s', inner_quorum_distribution, node)
                            node.set_quorum(nodes=quorum_distribution, inner_sets=inner_quorum_distribution)

                    else: # If only one node filtered then make no inner sets
                        filtered_nodes.append(node)
                        log.network.debug('Adding nodes %s to the quorum set of Node %s',filtered_nodes, node)
                        node.set_quorum(filtered_nodes, [])

            case 'HARDCODE':
                file_path = "all_validators_thresholds.json"

                with open(file_path, 'r') as file:
                    data = json.load(file)  # Load the JSON file

                nodes = []

                for validator_data in data:
                    # Extract the "publicKey" as the node ID
                    node_id = validator_data["publicKey"]

                    # Get the list of "validators"
                    node_list = validator_data.get("validators", [])

                    # Create the Node object
                    node = Node(node_id)

                    # Set the quorum using "validators"
                    node.set_quorum([Node(node) for node in node_list], [])  # No inner sets
                    nodes.append(node)

                    log.network.debug(
                        'Node %s initialized with  %d validators',
                        node_id,
                        len(node_list),
                    )

                return nodes

        return nodes

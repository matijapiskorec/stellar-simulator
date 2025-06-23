"""
=========================
Network
=========================

Author: Matija Piskorec, Jaime de Vivero Woods
Last update: March 2025

Network class. Setup Stellar validator network by initializing nodes and setting their quorum sets based on a predefined topology.
"""
import math

from Log import log
from Node import Node
from QuorumSet import QuorumSet
import json
import networkx as nx

class Network():

    topologies = ['FULL','ER-SINGLEQUORUMSET','ER_singlequorumset','HARDCODE', 'LUNCH']

    @classmethod
    def parse_all_validators(cls, file_path):
        with open(file_path, 'r') as file:
            data = json.load(file)

        nodes = {}

        for validator in data:
            node_id = validator["publicKey"]
            quorum_sets = validator.get("quorumSet", [])

            if node_id not in nodes:
                nodes[node_id] = Node(node_id) # Initalise all nodes

            for quorum in quorum_sets:
                threshold = quorum.get("threshold", 1)  # Default threshold to 1 if not present
                node_list = quorum.get("validators", [])
                inner_sets = quorum.get("inner_sets", [])

                nodes[node_id].set_quorum(threshold, node_list, inner_sets)

        return nodes

    @classmethod
    def generate_nodes(cls,n_nodes=2,topology='FULL', percent_threshold = None):

        assert n_nodes > 0
        assert topology in cls.topologies

        nodes = []

        # Generate network topology by altering nodes quorum sets
        match topology:
            case 'FULL':
                for i in range(n_nodes):
                    nodes.append(Node(i))
                    log.network.debug('Node created: %s', nodes[-1])

                log.network.debug('Calculating quorum sets based on the network topology=%s', topology)
                # We add all nodes to the quorum set of each node, including the node itself
                for node in nodes:
                    log.network.debug('Adding nodes %s to the quorum set of Node %s', nodes, node)
                    node.set_quorum(nodes, [])

                return nodes
            case 'ER-SINGLEQUORUMSET':
                # Create nodes
                for i in range(n_nodes):
                    nodes.append(Node(i))
                    log.network.debug('Node created: %s', nodes[-1])

                node_map = {node.name: node for node in nodes}

                log.network.debug('Calculating quorum sets based on the network topology=%s', topology)
                # Generate a random graph with n_nodes and 50% chance for each edge
                graph = nx.fast_gnp_random_graph(n_nodes, 0.5)
                # Find the largest connected component (LCC)
                lcc_set = max(nx.connected_components(graph), key=len)
                # Identify missing nodes (not in LCC)
                missing = list(set(int(node.name) for node in nodes) - lcc_set)
                if len(missing) > 0:
                    log.network.debug('Nodes %s are not part of the LCC so they are excluded from all quorum sets!',
                                      missing)
                # Exclude nodes that are not in the LCC
                nodes = [node for node in nodes if int(node.name) in lcc_set]
                nodes = [node_map[i] for i in lcc_set]



                # For each node in the remaining (connected) set, build quorum sets
                for node in nodes:
                    # For each node, get its edges from the graph
                    # filtered_nodes = [nodes[edge[1]] for edge in graph.edges(node.name)]
                    filtered_nodes = [nodes[edge[1]] for edge in graph.edges(node.name) if edge[1] < len(nodes)]

                    if len(filtered_nodes) > 1:
                        filter_distribution = len(filtered_nodes) // 2  # Half to quorum, half to inner sets
                        quorum_distribution = filtered_nodes[:filter_distribution]
                        inner_quorum_distribution = filtered_nodes[filter_distribution:]
                        quorum_distribution.append(node)
                        log.network.debug('Adding nodes %s to the quorum set of Node %s', quorum_distribution, node)

                        if len(inner_quorum_distribution) > 1:  # If more than 2 nodes, define 2 inner sets
                            inner_set_distribution = len(inner_quorum_distribution) // 2
                            inner_set1 = inner_quorum_distribution[inner_set_distribution:]
                            inner_set2 = inner_quorum_distribution[:inner_set_distribution]
                            inner_set1.append(node)
                            inner_set2.append(node)
                            log.network.debug('Adding nodes %s to inner set 1, and nodes %s to inner set 2 of Node %s',
                                              inner_set1, inner_set2, node)
                            node.set_quorum(nodes=quorum_distribution, inner_sets=[inner_set1, inner_set2])
                        else:  # Only one inner set defined
                            inner_quorum_distribution.append(node)
                            log.network.debug('Adding nodes %s to the inner set of Node %s', inner_quorum_distribution,
                                              node)
                            node.set_quorum(nodes=quorum_distribution, inner_sets=inner_quorum_distribution)

                    else:  # If no neighbor is found, include the node itself
                        filtered_nodes.append(node)
                        log.network.debug('Adding nodes %s to the quorum set of Node %s', filtered_nodes, node)
                        node.set_quorum(filtered_nodes, [])

                return nodes

            case 'ER_singlequorumset':
                # 1) create all nodes
                nodes = []
                for i in range(n_nodes):
                    nodes.append(Node(i))
                    log.network.debug('Node created: %s', nodes[-1])
                node_map = {int(n.name): n for n in nodes}

                # 2) build random ER-SINGLEQUORUMSET graph & find LCC
                log.network.debug('Building ER_singlequorumset graph with p=0.5')
                graph = nx.fast_gnp_random_graph(n_nodes, 0.5)
                lcc = max(nx.connected_components(graph), key=len)
                missing = [i for i in range(n_nodes) if i not in lcc]
                if missing:
                    log.network.debug('Dropping isolated/excluded nodes: %s', missing)

                # 3) restrict execution to the LCC
                sq_nodes = [node_map[i] for i in lcc]

                # 4) for each node, quorum = its LCC-neighbors + itself
                for node in sq_nodes:
                    idx = int(node.name)
                    nbrs = [nbr for nbr in graph.neighbors(idx) if nbr in lcc]
                    peers = [node_map[n] for n in nbrs]
                    quorum_members = peers + [node]

                    log.network.debug(
                        'Adding nodes %s to the flat quorum of Node %s',
                        [n.name for n in quorum_members], node
                    )
                    # your signature only needs the member list
                    node.set_quorum(nodes=quorum_members, inner_sets=[])

                # 5) return exactly the validators that made it into the LCC
                return sq_nodes

            case 'HARDCODE':
                import math

                PERCENT_THRESHOLD = 0.8

                file_path = "quorumset_05_06_2025.json"
                with open(file_path, 'r') as f:
                    raw = json.load(f)

                data_list = raw["nodes"]

                defined_ids = {entry.get("publicKey") for entry in data_list} # 2) collect all defined publicKeys
                if any(not isinstance(pk, str) for pk in defined_ids):
                    raise RuntimeError(f"All publicKey fields must be strings. Got: {defined_ids}")

                nodes_dict = {pk: Node(pk) for pk in defined_ids} # Initalise all Nodes
                referenced_undefined = set()

                def build_inner_list(inner_json, parent_id): # Helper function to build the inner quorum sets
                    if not isinstance(inner_json, dict):
                        raise RuntimeError(f"innerQuorumSets entry must be a dict. Got {inner_json!r}")
                    result = []
                    for v_id in inner_json.get("validators", []):
                        if v_id not in defined_ids:
                            referenced_undefined.add(v_id)
                            log.network.warning("Dropping undefined validator %s in innerQuorumSets of %s",
                                                v_id, parent_id)
                        else:
                            result.append(nodes_dict[v_id])
                    for sub in inner_json.get("innerQuorumSets", []):
                        result.append(build_inner_list(sub, parent_id))
                    return result

                # 5) second pass: wire up each node
                for entry in data_list:
                    node_id = entry["publicKey"]
                    node = nodes_dict[node_id]

                    q = entry.get("quorumSet")

                    top_level = [] # build top-level list "validators'
                    for v_id in q.get("validators", []):
                        if v_id not in defined_ids:
                            referenced_undefined.add(v_id)
                            log.network.warning("Dropping undefined top-level validator %s of %s", v_id, node_id)
                        else:
                            top_level.append(nodes_dict[v_id])

                    inner_lists = [build_inner_list(inner_json, node_id)
                                   for inner_json in q.get("innerQuorumSets", [])] # build the nested inner-quorum set lists

                    def _flatten(qs): # flatten is used to count all peers across all inner quorum sets
                        flat = []
                        for x in qs:
                            if isinstance(x, list):
                                flat.extend(_flatten(x))
                            else:
                                flat.append(x)
                        return flat

                    total_peers = len(top_level) + len(_flatten(inner_lists))
                    dynamic_thr = math.ceil(total_peers * PERCENT_THRESHOLD)

                    node.quorum_set.threshold = dynamic_thr # calculate dynamically the threshold based on total peers, we can set via PERCENT_THRESHOLD variable
                    node.quorum_set.set(nodes=top_level, inner_sets=inner_lists)

                    log.network.info(
                        "Node %s : dynamic threshold=%d (100%% of %d peers); top=%d, nested_lists=%d",
                        node_id, dynamic_thr, total_peers, len(top_level), len(inner_lists)
                    )

                if referenced_undefined: # if there are isolated nodes here they are logged
                    log.network.info(
                        "Dropped %d undefined nodes: %s",
                        len(referenced_undefined), sorted(referenced_undefined)
                    )

                # 7) return them
                return list(nodes_dict.values())


            case 'LUNCH':
                names = ["Alice", "Bob", "Carol", "Dave", "Elsie", "Fred", "Gwen", "Hank", "Inez", "John"]
                nodes = {name: Node(name) for name in names}  # Use a dictionary for easy access

                # Define the quorum sets based 'Round of Lunch' github
                quorum_sets = {
                    "Alice": ["Bob", "Carol", "Dave"],
                    "Bob": ["Alice", "Carol", "Dave"],
                    "Carol": ["Alice", "Bob", "Dave"],
                    "Dave": ["Alice", "Bob", "Carol"],
                    "Elsie": ["Alice", "Bob", "Carol", "Dave"],
                    "Fred": ["Alice", "Bob", "Carol", "Dave"],
                    "Gwen": ["Alice", "Bob", "Carol", "Dave"],
                    "Hank": ["Alice", "Bob", "Carol", "Dave"],
                    "Inez": ["Elsie", "Fred", "Gwen", "Hank"],
                    "John": ["Elsie", "Fred", "Gwen", "Hank"]
                }

                quorum_thresholds = {
                    "Alice": 2, "Bob": 2, "Carol": 2, "Dave": 2,  # 2 out of 3 → 67%
                    "Elsie": 2, "Fred": 2, "Gwen": 2, "Hank": 2,  # 2 out of 4 → 50%
                    "Inez": 2, "John": 2  # 2 out of 4 → 50%
                }
                for node_name, quorum_members in quorum_sets.items():
                    threshold = quorum_thresholds[node_name]
                    nodes[node_name].set_quorum([nodes[q] for q in quorum_members], [], threshold=threshold)

                return list(nodes.values())

        return nodes

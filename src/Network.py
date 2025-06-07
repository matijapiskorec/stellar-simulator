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

    topologies = ['FULL','ER','ER_singlequorumset','HARDCODE', 'LUNCH']

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
            case 'ER':
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

                # 2) build random ER graph & find LCC
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

            # Replace this snippet into your Network.py under case 'HARDCODE':

            case 'HARDCODE':
                file_path = "quorumset_05_06_2025.json"
                with open(file_path, 'r') as f:
                    raw = json.load(f)

                # 1) pull out raw["nodes"]
                if not isinstance(raw, dict) or "nodes" not in raw:
                    raise RuntimeError(f"HARDCODE loader expected a dict with key 'nodes'. Got: {raw!r}")
                data_list = raw["nodes"]
                if not isinstance(data_list, list):
                    raise RuntimeError(f"'nodes' must be a list. Got: {data_list!r}")

                # 2) record exactly which publicKeys are “real” validators
                defined_ids = {entry.get("publicKey") for entry in data_list}
                if any(not isinstance(pk, str) for pk in defined_ids):
                    raise RuntimeError(f"All publicKey fields must be strings. Got: {defined_ids}")

                # 3) instantiate only your real Nodes
                nodes_dict = {pk: Node(pk) for pk in defined_ids}

                # track any stray IDs we see in innerQuorumSets
                referenced_undefined = set()

                # 4) recursive helper to build nested lists, skipping undefined IDs
                def build_inner_list(inner_json, parent_node_id):
                    if not isinstance(inner_json, dict):
                        raise RuntimeError(f"Each innerQuorumSets entry must be a dict. Got: {inner_json!r}")
                    result = []
                    # (a) validators
                    for v_id in inner_json.get("validators", []):
                        if not isinstance(v_id, str):
                            raise RuntimeError(f"Validator IDs must be strings. Got: {v_id!r}")
                        if v_id not in defined_ids:
                            referenced_undefined.add(v_id)
                            log.network.warning(
                                "Dropping undefined validator %s in innerQuorumSets under node %s",
                                v_id, parent_node_id
                            )
                            continue
                        result.append(nodes_dict[v_id])
                    # (b) recurse deeper
                    for sub in inner_json.get("innerQuorumSets", []):
                        result.append(build_inner_list(sub, parent_node_id))
                    return result

                # 5) second pass: wire up each Node’s QuorumSet
                for entry in data_list:
                    node_id = entry["publicKey"]
                    node = nodes_dict[node_id]

                    qset = entry.get("quorumSet")
                    if not isinstance(qset, dict):
                        raise RuntimeError(f"Entry for {node_id} must have a dict 'quorumSet'. Got: {qset!r}")

                    # threshold is an absolute count in JSON
                    thr = qset.get("threshold")
                    if not isinstance(thr, int):
                        raise RuntimeError(f"'threshold' must be an int for {node_id}. Got: {thr!r}")
                    node.quorum_set.threshold = thr

                    # top‐level validators (usually empty)
                    top_level = []
                    for v_id in qset.get("validators", []):
                        if not isinstance(v_id, str):
                            raise RuntimeError(f"Validator IDs must be strings. Got: {v_id!r}")
                        if v_id not in defined_ids:
                            referenced_undefined.add(v_id)
                            log.network.warning(
                                "Dropping undefined validator %s in top‐level list of node %s",
                                v_id, node_id
                            )
                            continue
                        top_level.append(nodes_dict[v_id])

                    # build nested inner lists
                    inner_lists = [
                        build_inner_list(inner_json, node_id)
                        for inner_json in qset.get("innerQuorumSets", [])
                    ]
                    # ─── INSERT DYNAMIC THRESHOLD CALCULATION HERE ───
                    PERCENT_THRESHOLD = 0.60
                    total_slices = len(top_level) + len(inner_lists)
                    # ceil so that 60% of e.g. 7 slices ≔ ceil(4.2) == 5
                    dynamic_threshold = math.ceil(total_slices * PERCENT_THRESHOLD)
                    # ────────────────────────────────────────────────

                    # set it all
                    node.quorum_set.set(nodes=top_level, inner_sets=inner_lists)
                    log.network.debug(
                        "Node %s initialized: top‐level validators = %d, inner lists = %d",
                        node_id, len(top_level), len(inner_lists)
                    )
                    # threshold is an absolute count in JSON
                    thr = qset.get("threshold")
                    if not isinstance(thr, int):
                        node.quorum_set.threshold = dynamic_threshold
                        raise RuntimeError(f"'threshold' must be an int for {node_id}. Got: {thr!r}")
                    else:
                        node.quorum_set.threshold = thr

                # 6) drop any nodes we created only by accident (referenced but never defined)
                dropped = referenced_undefined
                if dropped:
                    log.network.info(
                        "Dropped %d isolated nodes referenced only in innerQuorumSets: %s",
                        len(dropped), sorted(dropped)
                    )

                final_nodes = [nodes_dict[pk] for pk in sorted(defined_ids)]
                log.network.info("Final network size: %d nodes", len(final_nodes))
                return final_nodes

                # ... handle other topologies as needed ...

                """

            case 'HARDCODE': # fix for HARDCODE TO REMOVE DUPLICATES
                file_path = "quorumset_05_06_2025.json"

                with open(file_path, 'r') as file:
                    data = json.load(file)

                # Use a dictionary to avoid duplicate Node instances.
                nodes_dict = {}

                for validator_data in data:
                    node_id =   validator_data["publicKey"]
                    node_list = validator_data.get("validators", [])
                    threshold = validator_data.get("threshold", 1)

                    # Create or reuse the Node for the validator.
                    if node_id not in nodes_dict:
                        nodes_dict[node_id] = Node(node_id)
                    node = nodes_dict[node_id]

                    # Parse inner quorum sets.
                    inner_quorum_sets = []
                    # Enumerate inner quorum sets to generate a unique ID for each.
                    for idx, inner_set in enumerate(validator_data.get("innerQuorumSets", [])):
                        inner_threshold = inner_set.get("threshold", 1)
                        inner_validators = inner_set.get("validators", [])

                        inner_nodes = []
                        for v in inner_validators:
                            # Create or reuse a Node for each inner validator.
                            if v not in nodes_dict:
                                nodes_dict[v] = Node(v)
                            inner_nodes.append(nodes_dict[v])

                        # Instead of creating a generic Node with "InnerSet-{node_id}",
                        # create a unique inner set identifier (using an index).
                        inner_set_id = f"InnerSet-{node_id}-{idx}"
                        if inner_set_id not in nodes_dict:
                            nodes_dict[inner_set_id] = Node(inner_set_id)
                        # Optionally, you could attach the inner_nodes list to the inner set node
                        # if you want to preserve that information.
                        inner_quorum_sets.append(nodes_dict[inner_set_id])

                    # Set the quorum for the node.
                    # For the top-level quorum nodes, include only those that are in the node_list.
                    top_level_nodes = [nodes_dict[v] for v in node_list if v in nodes_dict]
                    node.set_quorum(nodes=top_level_nodes, inner_sets=inner_quorum_sets, threshold=threshold)

                    log.network.debug('Node %s initialized with %d validators and %d inner quorum sets',
                                      node_id, len(node_list), len(inner_quorum_sets))

                # Return all unique nodes.
                nodes = list(nodes_dict.values())
                return nodes"""


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

"""
=========================
Network
=========================

Author: Matija Piskorec, Jaime de Vivero Woods
Last update: March 2025

Network class. Setup Stellar validator network by initializing nodes and setting their quorum sets based on a predefined topology.
"""

from Log import log
from Node import Node
import json
import networkx as nx

class Network():

    topologies = ['FULL','ER', 'BA']

    @classmethod
    def generate_nodes(cls, n_nodes: int = 50, topology: str = 'FULL', *, degree: int = 10, seed=None):
        """
        Return a connected peer graph according to `topology`:
        - FULL: complete graph (every node peers with every other).
        - ER: random connected Erdős–Rényi G(n,p) with avg degree ≈ `degree`.
        - BA: Barabási–Albert scale-free network with ~`degree` edges per new node.
        """
        assert topology in cls.topologies, f"Unknown topology: {topology}"

        if topology == 'FULL':
            nodes = [Node(i) for i in range(n_nodes)]
            for u in nodes:
                for v in nodes:
                    if u is not v:
                        u.add_peer(v)
            log.network.info(
                "Built FULL graph: n=%d  complete topology",
                n_nodes
            )
            return nodes

        if topology == 'ER':
            p = degree / (n_nodes - 1)
            while True:
                g = nx.fast_gnp_random_graph(n_nodes, p, seed=seed)
                if nx.is_connected(g):
                    break
                seed = None

            nodes = [Node(i) for i in range(n_nodes)]
            for u, v in g.edges():
                nodes[u].add_peer(nodes[v])
                nodes[v].add_peer(nodes[u])

            log.network.info(
                "Built ER_STATIC graph: n=%d  k≈%d  p=%.4f  diameter=%d",
                n_nodes, degree, p, nx.diameter(g)
            )
            return nodes

        if topology == 'BA':
            m = degree
            nodes = [Node(i) for i in range(n_nodes)]
            node_map = {int(n.name): n for n in nodes}

            log.network.info(f"Building BA (Barabási–Albert) graph: n={n_nodes}, m={m}")
            graph = nx.barabasi_albert_graph(n_nodes, m, seed=seed)

            # Identify largest connected component (LCC)
            lcc = max(nx.connected_components(graph), key=len)
            missing = [i for i in range(n_nodes) if i not in lcc]
            if missing:
                log.network.info(f'Dropping isolated/excluded nodes: {missing}')

            # Only keep nodes in the LCC
            ba_nodes = [node_map[i] for i in lcc]
            lcc_graph = graph.subgraph(lcc)

            # Connect peers for each node in LCC
            for node in ba_nodes:
                idx = int(node.name)
                nbrs = [nbr for nbr in lcc_graph.neighbors(idx)]
                for n in nbrs:
                    node.add_peer(node_map[n])  # Add peers (bi-directional)
            # Optionally: ensure symmetric add_peer for undirected network
            for node in ba_nodes:
                for peer in node.peers:
                    if node not in peer.peers:
                        peer.add_peer(node)

            # Log peer degree stats
            peer_degrees = [len(node.peers) for node in ba_nodes]
            avg_degree = sum(peer_degrees) / len(peer_degrees) if peer_degrees else 0

            with open('simulator_events_log.txt', 'a') as f:
                f.write(
                    f"[BA] n_nodes={n_nodes}, LCC_size={len(ba_nodes)}, avg_peer_degree={avg_degree:.2f}\n"
                )

            log.network.info(
                f"Built BA graph: n={n_nodes}  LCC={len(ba_nodes)}  avg_degree={avg_degree:.2f}"
            )
            return ba_nodes



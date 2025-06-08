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

    topologies = ['FULL','ER']

    @classmethod
    def generate_nodes(cls, n_nodes: int = 50, topology: str = 'FULL', *, degree: int = 10, seed=None):
        """
        Return a connected peer graph according to `topology`:
        - FULL: complete graph (every node peers with every other).
        - ER: random connected Erdős–Rényi G(n,p) with avg degree ≈ `degree`.

        This structure is critical for realistic event-driven simulation frameworks
        where nodes act independently but are influenced by their neighbors.
        """
        assert topology in cls.topologies, f"Unknown topology: {topology}"

        # FULL topology: complete, all-to-all connections
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

        # ER topology: Erdős–Rényi random graph
        p = degree / (n_nodes - 1)
        while True:
            g = nx.fast_gnp_random_graph(n_nodes, p, seed=seed)
            if nx.is_connected(g):
                break
            seed = None

        # Wrap into Node objects and add bi-directional edges
        nodes = [Node(i) for i in range(n_nodes)]
        for u, v in g.edges():
            nodes[u].add_peer(nodes[v])
            nodes[v].add_peer(nodes[u])

        log.network.info(
            "Built ER_STATIC graph: n=%d  k≈%d  p=%.4f  diameter=%d",
            n_nodes, degree, p, nx.diameter(g)
        )
        return nodes




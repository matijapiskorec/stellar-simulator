import os
import unittest

from Simulator import Simulator
from Mempool import Mempool
from Network import Network
from Globals import Globals
from SCPExternalize import SCPExternalize

class TestFinalizedIntegration(unittest.TestCase):
    def setUp(self):
        self.sim_duration = 200.0

        self.sim = Simulator(verbosity=5, n_nodes=60)
        self.sim._nodes = Network.generate_nodes(
            n_nodes=self.sim.n_nodes,
            topology='ER-SINGLEQUORUMSET'
        )

        self.shared_mempool = Mempool()
        for n in self.sim._nodes:
            n.attach_mempool(self.shared_mempool)
        self.sim._mempool = self.shared_mempool

        Globals.simulation_time = 0.0
        self.sim._max_simulation_time = self.sim_duration

    def tearDown(self):
        for fn in ("ledger_logs.txt", self.shared_mempool.log_path):
            if os.path.exists(fn):
                os.remove(fn)

    def test_every_node_externalizes_exactly_one_value(self):
        """ Each node should externalize exactly one slot/value during our short sim. """
        self.sim.run()

        first = self.sim.get_first_externalized_values()
        self.assertEqual(
            set(self.sim._nodes),
            set(first.keys()),
            "Every node should have externalized at least one value"
        )

        for v, val in first.items():
            self.assertIsInstance(val, SCPExternalize)
            self.assertEqual(
                val.value,
                v.ledger.slots[val.slot]['value'],
                f"Node {v.name}: mismatch between first‑externalized and ledger"
            )

    def test_nomination_lists_contain_final_value(self):
        """ After finalization, the single nominated Value must appear in voted/accepted/confirmed. """
        self.sim.run()
        first = self.sim.get_first_externalized_values()

        for node, ext in first.items():
            final_val = ext.value
            for phase in ('voted','accepted','confirmed'):
                with self.subTest(node=node.name, phase=phase):
                    self.assertIn(
                        final_val,
                        node.nomination_state[phase],
                        f"Node {node.name} never {phase!r} the final Value"
                    )

    def test_ballots_all_carry_exactly_final_value(self):
        """ No prepare‑ or commit‑ ballots with the wrong Value survive finalization. """
        self.sim.run()
        first = self.sim.get_first_externalized_values()

        for node, ext in first.items():
            final_val = ext.value

            for state in ('voted','accepted','confirmed','aborted'):
                for b in node.balloting_state[state].values():
                    with self.subTest(node=node.name, state=state, ballot=b):
                        self.assertEqual(
                            b.value, final_val,
                            f"Node {node.name}: in prepare‑{state}, ballot {b} has wrong Value"
                        )

            for state in ('voted','accepted','confirmed'):
                for b in node.commit_ballot_state[state].values():
                    with self.subTest(node=node.name, state=state, ballot=b):
                        self.assertEqual(
                            b.value, final_val,
                            f"Node {node.name}: in commit‑{state}, ballot {b} has wrong Value"
                        )

    def test_mempool_and_inflight_do_not_retain_finalized_txs(self):
        """ Once a slot finalizes, no tx in that Value remains in any pre‑finalization state. """
        self.sim.run()
        first = self.sim.get_first_externalized_values()

        for node, ext in first.items():
            final_val = ext.value
            final_hashes = {tx.hash for tx in final_val.transactions}

            # 1) shared mempool
            for tx in self.shared_mempool.transactions:
                with self.subTest(node=node.name, location='mempool', tx=tx):
                    self.assertNotIn(
                        tx.hash,
                        final_hashes,
                        f"Node {node.name}'s shared mempool still contains finalized tx {tx.hash}"
                    )

            # 2) nomination lists
            for phase in ('voted','accepted','confirmed'):
                for val in node.nomination_state[phase]:
                    for tx in val.transactions:
                        with self.subTest(node=node.name, location=f'nom.{phase}', tx=tx):
                            self.assertNotIn(
                                tx.hash,
                                final_hashes,
                                f"Node {node.name} nomination_state[{phase}] still has finalized tx {tx.hash}"
                            )

            # 3) prepare ballots
            for state in ('voted','accepted','confirmed','aborted'):
                for b in node.balloting_state[state].values():
                    for tx in b.value.transactions:
                        with self.subTest(node=node.name, location=f'prep.{state}', tx=tx):
                            self.assertNotIn(
                                tx.hash,
                                final_hashes,
                                f"Node {node.name} prepare_state[{state}] still has finalized tx {tx.hash}"
                            )

            # 4) commit ballots
            for state in ('voted','accepted','confirmed'):
                for b in node.commit_ballot_state[state].values():
                    for tx in b.value.transactions:
                        with self.subTest(node=node.name, location=f'commit.{state}', tx=tx):
                            self.assertNotIn(
                                tx.hash,
                                final_hashes,
                                f"Node {node.name} commit_state[{state}] still has finalized tx {tx.hash}"
                            )

if __name__ == '__main__':
    unittest.main()

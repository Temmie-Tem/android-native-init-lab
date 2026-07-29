from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "workspace/public/src/scripts/revalidation"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import s22plus_fyg8_p286_change_freeze as freeze  # noqa: E402


class P286ChangeFreezeTests(unittest.TestCase):
    def test_exact_candidate_and_d1_requirements_are_frozen(self):
        self.assertEqual(
            tuple(key for key, _ in freeze.CANDIDATE_CHANGE_REQUIREMENTS),
            (
                "parent-runtime-status-gate",
                "bounded-helper-reap",
                "actual-outer-work-probes",
                "helper-dispatch-completion-split",
                "restart-failure-partition",
                "residual-outer-tail-bound",
                "identity-closure-enforcement",
            ),
        )
        self.assertEqual(
            tuple(key for key, _ in freeze.D1_CHANGE_REQUIREMENTS),
            (
                "instance-trace-spelling",
                "immediate-watchdog-disarm",
                "comm-newline-removal",
                "remove-unapproved-endpoint-count",
            ),
        )

    def test_p284_is_inherited_without_a_mutation_path(self):
        inherited = {
            path.as_posix()
            for path in freeze.inherited_direct_source_paths().values()
        }
        mutations = {
            path.as_posix()
            for path in freeze.PLANNED_OVERLAY_SOURCE_PATHS.values()
        }
        self.assertEqual(len(freeze.p284.SOURCE_KEYS), 60)
        self.assertEqual(len(inherited), 55)
        self.assertEqual(len(freeze.GENERATED_SOURCE_KEYS), 5)
        self.assertTrue(inherited.isdisjoint(mutations))

    def test_every_candidate_mutation_is_a_planned_source_key(self):
        result = freeze.validate_freeze(ROOT)
        rows = {
            row["source_key"]: row["path"] for row in result["source_keys"]
        }
        self.assertEqual(result["source_key_counts"]["planned_overlay"], 20)
        self.assertEqual(result["source_key_counts"]["planned_total"], 80)
        for key, path in freeze.PLANNED_OVERLAY_SOURCE_PATHS.items():
            self.assertEqual(rows[key], path.as_posix())

    def test_d1_mutations_are_private_and_do_not_overlap_candidate(self):
        result = freeze.validate_freeze(ROOT)
        self.assertEqual(result["candidate_d1_overlap_count"], 0)
        self.assertTrue(
            all(
                path.startswith(
                    "workspace/private/outputs/"
                    "s22plus_fyg8_p284_stock_outer_d1_v3/"
                )
                for path in result["d1_private_mutation_paths"]
            )
        )
        self.assertNotIn(
            "workspace/public/src/scripts/revalidation/"
            "s22plus_fyg8_p284_stock_outer_d1_spec.py",
            result["d1_private_mutation_paths"],
        )

    def test_actual_mutation_lists_are_checked_against_both_frozen_sets(self):
        candidate = (
            "workspace/public/src/native-init/"
            "s22plus_fyg8_p286_e3_runtime.inc.c"
        )
        d1 = (
            "workspace/private/outputs/"
            "s22plus_fyg8_p284_stock_outer_d1_v3/device_runner.sh"
        )
        result = freeze.validate_declared_mutations(
            candidate_paths=(candidate,),
            d1_paths=(d1,),
        )
        self.assertEqual(result["candidate_paths"], (candidate,))
        self.assertEqual(result["d1_paths"], (d1,))
        with self.assertRaisesRegex(
            freeze.FreezeError,
            "candidate mutation is outside",
        ):
            freeze.validate_declared_mutations(
                candidate_paths=(
                    "workspace/public/src/native-init/"
                    "s22plus_fyg8_p282_e3_runtime.inc.c",
                ),
            )
        with self.assertRaisesRegex(
            freeze.FreezeError,
            "D1 mutation is outside",
        ):
            freeze.validate_declared_mutations(
                d1_paths=(
                    "workspace/public/src/scripts/revalidation/"
                    "s22plus_fyg8_p284_stock_outer_d1_spec.py",
                ),
            )

    def test_freeze_does_not_claim_pre_intent_readiness_early(self):
        result = freeze.validate_freeze(ROOT)
        self.assertFalse(result["pre_intent_ready"])
        self.assertFalse(result["intent_derived"])
        self.assertFalse(result["build_executed"])
        self.assertFalse(result["device_contact"])
        self.assertFalse(result["live_authorized"])
        self.assertIn(
            "workspace/public/src/scripts/revalidation/"
            "s22plus_fyg8_p286_source_contract.py",
            result["missing_planned_overlay_paths"],
        )

    def test_generated_source_rows_are_explicit(self):
        result = freeze.validate_freeze(ROOT)
        generated = {
            row["source_key"]: row["path"]
            for row in result["source_keys"]
            if row["path"].startswith("generated://")
        }
        self.assertEqual(set(generated), freeze.GENERATED_SOURCE_KEYS)


if __name__ == "__main__":
    unittest.main()

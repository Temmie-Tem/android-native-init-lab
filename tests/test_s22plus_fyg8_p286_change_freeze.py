from __future__ import annotations

import subprocess
import sys
import tempfile
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

    def test_payload_and_support_partitions_are_exact(self):
        self.assertEqual(
            set(freeze.PAYLOAD_SOURCE_PATHS),
            {
                "p286_contract_spec",
                "p286_source_contract",
                "p286_source_contract_selector",
                "p286_candidate_intent",
                "p286_e3_runtime_include",
                "p286_classifier_include",
                "p286_trace_contract",
                "p286_userspace_build",
                "p286_candidate_builder",
                "p286_build",
                "p286_boot_only_packager",
            },
        )
        self.assertEqual(
            set(freeze.NON_IDENTITY_SUPPORT_PATHS),
            {
                "p286_change_freeze",
                "p286_freeze_report",
                "p286_candidate_contract",
                "p286_build_repro_check",
                "p286_candidate_static_checker",
                "p286_e2_stock_closure",
                "p286_linked_audit",
                "p286_pre_lto_qualification",
                "p286_decoder_adapter",
            },
        )
        payload_paths = set(freeze.PAYLOAD_SOURCE_PATHS.values())
        support_paths = set(freeze.NON_IDENTITY_SUPPORT_PATHS.values())
        self.assertEqual(len(payload_paths), 11)
        self.assertEqual(len(support_paths), 9)
        self.assertTrue(payload_paths.isdisjoint(support_paths))

    def test_p284_is_inherited_without_a_mutation_path(self):
        inherited = {
            path.as_posix()
            for path in freeze.inherited_direct_source_paths().values()
        }
        payload = {
            path.as_posix() for path in freeze.PAYLOAD_SOURCE_PATHS.values()
        }
        self.assertEqual(len(freeze.p284.SOURCE_KEYS), 60)
        self.assertEqual(len(inherited), 55)
        self.assertEqual(len(freeze.GENERATED_SOURCE_KEYS), 5)
        self.assertTrue(inherited.isdisjoint(payload))

    def test_only_payload_overlays_become_source_keys(self):
        result = freeze.validate_freeze(ROOT)
        rows = {
            row["source_key"]: row["path"] for row in result["source_keys"]
        }
        self.assertEqual(result["source_key_counts"]["planned_payload"], 11)
        self.assertEqual(result["source_key_counts"]["planned_total"], 71)
        self.assertEqual(
            result["source_key_counts"]["bundle_bound_support"],
            9,
        )
        for key, path in freeze.PAYLOAD_SOURCE_PATHS.items():
            self.assertEqual(rows[key], path.as_posix())
        for key, path in freeze.NON_IDENTITY_SUPPORT_PATHS.items():
            self.assertNotIn(key, rows)
            self.assertNotIn(path.as_posix(), rows.values())

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

    def test_declared_change_set_is_bidirectional_and_fail_closed(self):
        actual = (
            "workspace/public/src/scripts/revalidation/"
            "s22plus_fyg8_p286_change_freeze.py"
        )
        result = freeze.validate_declared_change_set(
            derived_paths=(actual,),
            declared_paths=(actual,),
        )
        self.assertEqual(result["git_derived_paths"], (actual,))
        self.assertEqual(result["declared_paths"], (actual,))
        with self.assertRaisesRegex(
            freeze.FreezeError,
            "missing_declarations",
        ):
            freeze.validate_declared_change_set(
                derived_paths=(actual,),
                declared_paths=(),
            )
        with self.assertRaisesRegex(
            freeze.FreezeError,
            "overdeclared",
        ):
            freeze.validate_declared_change_set(
                derived_paths=(),
                declared_paths=(actual,),
            )
        outside = "workspace/public/src/native-init/unfrozen.c"
        with self.assertRaisesRegex(
            freeze.FreezeError,
            "outside the frozen change window",
        ):
            freeze.validate_declared_change_set(
                derived_paths=(outside,),
                declared_paths=(outside,),
            )

    def test_git_derivation_unions_committed_dirty_and_untracked_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)

            def git(*args: str) -> str:
                completed = subprocess.run(
                    ("git", *args),
                    cwd=root,
                    check=True,
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                return completed.stdout.strip()

            git("init", "-q")
            git("config", "user.name", "P286 Freeze Test")
            git("config", "user.email", "p286-freeze@example.invalid")
            (root / "tracked.txt").write_text("base\n", encoding="utf-8")
            git("add", "tracked.txt")
            git("commit", "-q", "-m", "base")
            base = git("rev-parse", "HEAD")

            (root / "committed.txt").write_text("committed\n", encoding="utf-8")
            git("add", "committed.txt")
            git("commit", "-q", "-m", "committed change")
            (root / "tracked.txt").write_text("dirty\n", encoding="utf-8")
            (root / "untracked.txt").write_text("untracked\n", encoding="utf-8")

            self.assertEqual(
                freeze.git_derived_changed_paths(root, base),
                ("committed.txt", "tracked.txt", "untracked.txt"),
            )

    def test_porcelain_rename_includes_both_paths(self):
        self.assertEqual(
            freeze._porcelain_paths(b"R  new-name\0old-name\0"),
            {"new-name", "old-name"},
        )

    def test_freeze_does_not_claim_pre_intent_readiness_early(self):
        result = freeze.validate_freeze(ROOT)
        self.assertFalse(result["pre_intent_ready"])
        self.assertFalse(result["intent_derived"])
        self.assertFalse(result["build_executed"])
        self.assertFalse(result["device_contact"])
        self.assertFalse(result["live_authorized"])
        self.assertEqual(len(result["missing_payload_source_paths"]), 11)
        self.assertEqual(len(result["missing_bundle_bound_support_paths"]), 7)
        self.assertEqual(len(result["missing_planned_paths"]), 18)
        self.assertIn(
            "workspace/public/src/scripts/revalidation/"
            "s22plus_fyg8_p286_source_contract.py",
            result["missing_payload_source_paths"],
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

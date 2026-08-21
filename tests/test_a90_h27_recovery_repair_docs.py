from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "docs/operations/targets/A90_TARGET_CONTRACT.md"
GOAL = ROOT / "GOAL_A90.md"
DESIGN = ROOT / "docs/plans/A90_BOOT_ONLY_F1_MINIMAL_V1_DESIGN_2026-08-20.md"
HANDOFF = ROOT / "docs/plans/A90_H27_POSTROLLBACK_AND_PRESENT_RECOVERY_REVIEW_HANDOFF_2026-08-21.md"
INCIDENT = ROOT / "docs/reports/A90_H27_SELFBUILT_KERNEL_BOOTLOOP_ROLLBACK_INCIDENT_2026-08-21.md"
REVIEW = ROOT / "docs/reports/A90_BOOT_ONLY_F1_MINIMAL_POSTROLLBACK_INDEPENDENT_REVIEW_2026-08-21.json"
H28_INPUT = ROOT / "docs/reports/A90_H28_MINIMAL_F1_QUALIFICATION_INPUT_2026-08-21.json"
MODULE_DIR = ROOT / "workspace/public/src/scripts/server-distro"
sys.path.insert(0, str(MODULE_DIR))


def load(name: str):
    if name in sys.modules:
        return sys.modules[name]
    source = MODULE_DIR / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, source)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


M = load("a90_boot_only_f1_minimal_v1")
A = load("a90_boot_only_f1_adapter_v1")
R = load("a90_h27_postrollback_reconcile_v1")


class RecoveryRepairDocsTest(unittest.TestCase):
    def test_contract_keeps_repair_narrow_and_no_replay(self):
        text = CONTRACT.read_text()
        for token in (
            "a90_h27_postrollback_reconcile_v1.py",
            "UNPROVED_EXTERNAL_CONTINUATION",
            "then remove only the exact\nactive-run guard",
            "candidate guard remains present",
            "--reuse-bound-recovery-or-from-native",
            "not a second rollback attempt or general\nADB authority",
        ):
            self.assertIn(token, text)

    def test_design_report_goal_and_handoff_agree_on_h0_state(self):
        combined = "\n".join(
            path.read_text() for path in (DESIGN, INCIDENT, GOAL, HANDOFF)
        )
        for token in (
            "41-recovery-closed.json",
            "UNPROVED_EXTERNAL_CONTINUATION",
            "already-present",
            "candidate guard",
            "independent full review",
        ):
            self.assertIn(token, combined)
        self.assertIn("no D0, approval, ordinal, F1, or live authority", GOAL.read_text())

    def test_owner_closure_and_journal_include_exact_repair(self):
        self.assertIn(
            "workspace/public/src/scripts/server-distro/a90_h27_postrollback_reconcile_v1.py",
            M.EXECUTION_SOURCE_RELS,
        )
        self.assertEqual(len(M.EXECUTION_SOURCE_RELS), 13)
        self.assertEqual(
            M.execution_closure_sha256(),
            "6ada12070f85d0800ca33b03d233ab8d006e4197bc5b0766f6759a86d63801e4",
        )
        self.assertEqual(
            M.POSTROLLBACK_RECOVERY_PATH[-1], "41-recovery-closed.json"
        )
        self.assertNotEqual(
            M.POSTROLLBACK_RECOVERY_PATH, M.PRETRANSFER_ABORT_PATH
        )

    def test_candidate_and_rollback_use_distinct_fixed_recovery_modes(self):
        artifact = {"path": "/fixed.img", "sha256": "a" * 64, "version": "v"}
        candidate = A.fixed_flash_argv(
            artifact,
            recovery_serial_sha256="b" * 64,
            timeout_sec=90,
            rollback=False,
        )
        rollback = A.fixed_flash_argv(
            artifact,
            recovery_serial_sha256="b" * 64,
            timeout_sec=90,
            rollback=True,
        )
        self.assertIn("--from-native", candidate)
        self.assertIn("--require-stable-adb-baseline", candidate)
        self.assertNotIn("--reuse-bound-recovery-or-from-native", candidate)
        self.assertIn("--reuse-bound-recovery-or-from-native", rollback)
        self.assertNotIn("--from-native", rollback)
        self.assertNotIn("--serial", rollback)

    def test_reconciler_surface_is_terminal_only(self):
        source = (MODULE_DIR / "a90_h27_postrollback_reconcile_v1.py").read_text()
        self.assertLessEqual(len(source.splitlines()), 360)
        self.assertIn("backend.observe(", source)
        self.assertNotIn("backend.flash(", source)
        self.assertNotIn("_release_candidate", source)
        self.assertEqual(R.DECISION, "V2321_HEALTHY_EXTERNAL_ROLLBACK_OUTCOME_UNPROVED")

    def test_h27_review_is_historical_after_candidate_neutral_scope_repair(self):
        review = json.loads(REVIEW.read_text())
        h28_input = json.loads(H28_INPUT.read_text())
        self.assertEqual(review["verdict"], "PASS_GO")
        self.assertEqual(
            review["executionClosureSha256"],
            "e58746ea93270c43a28db5df20695a61a687eec942a5a665f562f4fe5173f077",
        )
        self.assertNotEqual(review["executionClosureSha256"], M.execution_closure_sha256())
        self.assertNotEqual(h28_input["executionClosureSha256"], M.execution_closure_sha256())
        self.assertEqual(review["candidateSha256"], "fa7ab8af8cec027c433653da92eb6cb4ca6f3a02d7624a4f292f61906e8ce500")
        self.assertFalse(review["liveAuthority"])
        self.assertTrue(all(value == 0 for value in review["contacts"].values()))


if __name__ == "__main__":
    unittest.main()

import hashlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
GOAL = ROOT / "GOAL.md"
TARGET = ROOT / "docs/operations/targets/S22PLUS_FYG8_TARGET_CONTRACT.md"
LEDGER = ROOT / "docs/operations/CAMPAIGN_LEDGER_S22PLUS.md"
REPORT = ROOT / (
    "docs/reports/"
    "S22PLUS_FYG8_P318_D1_BASELINE_ROTATION_PREP_H0_2026-08-16.md"
)
SCRIPT = ROOT / (
    "workspace/public/src/scripts/revalidation/"
    "s22plus_fyg8_p318_baseline_rotation_d1.py"
)
BINDING = ROOT / (
    "workspace/public/src/device-action/manifests/"
    "s22plus_fyg8_p318_d1_baseline_rotation_v1.json"
)
READY = ROOT / (
    "workspace/public/src/device-action/manifests/"
    "s22plus_fyg8_p318_process_v2_ready_1.json"
)


class P318BaselineRotationD1DocsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.goal = GOAL.read_text(encoding="utf-8")
        cls.target = TARGET.read_text(encoding="utf-8")
        cls.ledger = LEDGER.read_text(encoding="utf-8")
        cls.report = REPORT.read_text(encoding="utf-8")
        cls.script_bytes = SCRIPT.read_bytes()
        cls.script = cls.script_bytes.decode("utf-8")
        cls.binding_bytes = BINDING.read_bytes()
        cls.binding = json.loads(cls.binding_bytes)

    def test_report_records_scoped_pass_go_and_creates_no_live_authority(self):
        for token in (
            "`PASS_GO_P318_D1_BASELINE_ROTATION_H0_CAPABILITY_V1`",
            "creates no D0, D1,\nF1, recovery, replay, live, A90, or S20+ authority",
            "reviewed manifest digest\nis not live authority",
            "DEVICE-ACTION-D1-P318-BASELINE-ROTATE-V1-APPROVE:dc5d7371",
            "No canonical approval arm, run directory, or private ADB execution snapshot",
            "No device, USB, ADB, reboot, Download, Odin, payload,\npartition",
            "Focused adapter tests pass 16/16",
            "P3.18 164/164, and common Process-v2 120/120",
        ):
            self.assertIn(token, self.report)

    def test_binding_manifest_self_binds_adapter_and_records_review(self):
        self.assertEqual(
            self.binding["schema"],
            "s22plus_fyg8_p318_d1_baseline_rotation_binding_v1",
        )
        self.assertEqual(
            self.binding["independent_review"],
            {
                "status": "pass-go",
                "verdict": "PASS_GO_P318_D1_BASELINE_ROTATION_H0_CAPABILITY_V1",
            },
        )
        self.assertEqual(len(self.binding_bytes), 3129)
        self.assertEqual(
            hashlib.sha256(self.binding_bytes).hexdigest(),
            "dc5d737146ec5974f195fcf749f114e6b592be21dae27ee7fca4a86e64701cdf",
        )
        adapter = self.binding["inputs"]["adapter"]
        self.assertEqual(adapter["size"], len(self.script_bytes))
        self.assertEqual(
            adapter["sha256"], hashlib.sha256(self.script_bytes).hexdigest()
        )
        self.assertFalse(self.binding["candidate_transfer"])
        self.assertFalse(self.binding["partition_payload"])
        self.assertFalse(self.binding["odin"])
        self.assertFalse(self.binding["f1_authorized"])
        self.assertFalse(
            self.binding["historical_topology_is_current_authority"]
        )
        self.assertTrue(self.binding["live_exact_serial_identity_required"])
        self.assertTrue(self.binding["live_topology_continuity_required"])
        d0_runtime = self.binding["inputs"]["pinned_d0_runtime_source"]
        d0_path = ROOT / d0_runtime["path"]
        self.assertEqual(d0_runtime["size"], len(d0_path.read_bytes()))
        self.assertEqual(
            d0_runtime["sha256"], hashlib.sha256(d0_path.read_bytes()).hexdigest()
        )
        self.assertEqual(
            self.binding["run_directory"],
            {
                "path": (
                    "workspace/private/runs/device-action-d1-p318-"
                    "baseline-rotation/p318-baseline-rotation-1"
                ),
                "publication": (
                    "directory-no-replace-then-durable-start-no-replace"
                ),
            },
        )
        self.assertEqual(
            self.binding["run_approval_arm"],
            {
                "path": (
                    "workspace/private/runs/device-action-d1-p318-"
                    "baseline-rotation/p318-baseline-rotation-1.arm.json"
                ),
                "publication": "file-no-replace-fsync-then-directory-fsync",
            },
        )

    def test_ready_and_approval_transitivity_are_exact(self):
        ready = self.binding["inputs"]["ready_manifest"]
        ready_bytes = READY.read_bytes()
        self.assertEqual(ready["size"], 2778)
        self.assertEqual(ready["size"], len(ready_bytes))
        self.assertEqual(ready["sha256"], hashlib.sha256(ready_bytes).hexdigest())
        self.assertIn(
            'AUTHORITY_PREFIX = "DEVICE-ACTION-D1-P318-BASELINE-ROTATE-V1-APPROVE:"',
            self.script,
        )
        self.assertIn(
            "authority = AUTHORITY_PREFIX + binding_manifest_sha256", self.script
        )
        self.assertIn(
            'binding["independent_review"]["status"] != "pass-go"', self.script
        )

    def test_report_records_topology_and_adb_boundaries_without_overclaim(self):
        for token in (
            "historical D0 topology is explicitly not current authority",
            "serial SHA-256 equals the durable exact-target identity before\n   any target-specific topology query",
            "stable inventory digest, selection topology, and both\n   initial and returned-health snapshot topologies remain identical",
            "exactly one ASCII-decimal ADB `transport_id` is explicitly ephemeral",
            "no current unbound local Python module enters the reboot path",
            "live run directory is not caller-selected",
            "arm consumes the approval even if a later host or pre-effect read\nfails",
            "file fsync, atomic no-replace link, and\ndirectory fsync",
            "dynamically loaded libraries and host kernel are not\nbyte-frozen",
            "not a\nhermetic host userspace or signed package-provenance closure",
        ):
            self.assertIn(token, self.report)

    def test_ledger_preserves_pending_then_closes_review_obligation(self):
        pending = (
            "h0-d1-baseline-rotation-11 | H0 | "
            "P318_D1_BASELINE_ROTATION_ADAPTER_IMPLEMENTED_REVIEW_PENDING | "
            "HEALTHY | PROVED | 0/0"
        )
        prior = (
            "h0-d0-stop-requalification-review-10 | H0 | "
            "PASS_GO_P318_D0_STOP_RECEIPT_PROCESS_V2_REQUALIFICATION_"
            "H0_CAPABILITY_V1"
        )
        review = (
            "h0-d1-baseline-rotation-review-11 | H0 | "
            "PASS_GO_P318_D1_BASELINE_ROTATION_H0_CAPABILITY_V1 | "
            "HEALTHY | PROVED | 0/0"
        )
        self.assertEqual(self.ledger.count(pending), 1)
        self.assertEqual(self.ledger.count(prior), 1)
        self.assertEqual(self.ledger.count(review), 1)
        self.assertLess(self.ledger.index(prior), self.ledger.index(pending))
        self.assertLess(self.ledger.index(pending), self.ledger.index(review))

    def test_goal_and_contract_keep_current_limits_and_authority_boundary(self):
        self.assertIn(
            "verified-runtime, fixed-run P3.18 D1 adapter is H0-reviewed and offline ready",
            self.goal,
        )
        self.assertIn("no D0/D1/F1/live authority", self.goal)
        self.assertIn("fresh exact D1 approval", self.goal)
        self.assertLessEqual(len(self.goal.splitlines()), 900)
        self.assertLessEqual(len(self.target.splitlines()), 260)
        for token in (
            "D1 is one exact, transient, no-payload control action",
            "Send the bound action once",
            "Do not turn it into a retry loop or an F1 substitute",
        ):
            self.assertIn(token, self.target)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import stat
import unittest


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / (
    "docs/reports/"
    "S22PLUS_FYG8_P319_PROCESS_V2_INTEGRATION_PREREQUISITES_H0_2026-08-21.md"
)
LEDGER = ROOT / "docs/operations/CAMPAIGN_LEDGER_S22PLUS.md"
GOAL = ROOT / "GOAL.md"
PREREQUISITE = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p319/"
    "process-v2-prerequisite-audit-20260821-02.json"
)
INTEGRATION = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p319/"
    "process-v2-integration-qualification-v1-20260821-02/result.json"
)


class P319ProcessV2IntegrationDocsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = REPORT.read_text(encoding="utf-8")
        cls.ledger = LEDGER.read_text(encoding="utf-8")
        cls.goal = GOAL.read_text(encoding="utf-8")
        cls.prerequisite_bytes = PREREQUISITE.read_bytes()
        cls.integration_bytes = INTEGRATION.read_bytes()
        cls.prerequisite = json.loads(cls.prerequisite_bytes)
        cls.integration = json.loads(cls.integration_bytes)

    def test_report_is_review_pending_and_names_all_current_blockers(self):
        self.assertIn("Status: `IMPLEMENTED_REVIEW_PENDING`", self.report)
        self.assertNotIn("PASS_GO_P319_PROCESS_V2_INTEGRATION", self.report)
        for blocker in (
            "BLOCKED_MISSING_GLOBAL_CONSUMED_REGISTRY",
            "CONSUMED_CANDIDATE_REGISTRY_MISSING",
            "FRESH_BASELINE_MISSING",
            "REQUALIFICATION_REQUIRED",
        ):
            with self.subTest(blocker=blocker):
                self.assertIn(blocker, self.report)
        self.assertIn("first independent full P3.19", self.report)
        self.assertIn("532 tests: 527 passed", self.report)
        self.assertIn("four failed on the four stale", self.report)
        self.assertIn("fresh full selection again ran", self.report)
        self.assertIn("532 tests: 531 passed, zero failed", self.report)
        self.assertIn("same unavailable mount-path", self.report)
        self.assertIn("531/531 is a post-correction result", self.report)
        self.assertIn("not a true description of the original", self.report)

    def test_report_keeps_no_proof_buckets_and_runtime_gate_distinct(self):
        self.assertIn("`NONCAUSAL_SUCCESS_PATH`", self.report)
        self.assertIn("`NO_PROOF_EXPERIMENT_PRECONDITION`", self.report)
        self.assertIn("`NO_PROOF_OBSERVER`", self.report)
        self.assertIn("post-run causal-classification gate", self.report)
        self.assertIn("not an extra pre-approval blocker", self.report)

    def test_private_receipts_are_exact_single_link_mode0400(self):
        expected = (
            (
                PREREQUISITE,
                self.prerequisite_bytes,
                11155,
                "9fa0f994fe30419f10acc2965ed507cf6f1ebd8ac5f7267fef9ac6d8588d4ca0",
            ),
            (
                INTEGRATION,
                self.integration_bytes,
                57123,
                "d0380d7d9dab635fb20aa365b8251023bf286b6ea5c3347b27e1d38330085307",
            ),
        )
        for path, data, size, digest in expected:
            with self.subTest(path=path.name):
                info = path.stat()
                self.assertEqual(len(data), size)
                self.assertEqual(hashlib.sha256(data).hexdigest(), digest)
                self.assertEqual(stat.S_IMODE(info.st_mode), 0o400)
                self.assertEqual(info.st_nlink, 1)

    def test_integration_receipt_is_blocked_and_authority_free(self):
        self.assertEqual(
            self.integration["verdict"],
            "BLOCKED_P319_PROCESS_V2_INTEGRATION_H0",
        )
        self.assertEqual(
            {item["code"] for item in self.integration["blockers"]},
            {
                "BLOCKED_MISSING_GLOBAL_CONSUMED_REGISTRY",
                "CONSUMED_CANDIDATE_REGISTRY_MISSING",
                "FRESH_BASELINE_MISSING",
                "REQUALIFICATION_REQUIRED",
            },
        )
        self.assertTrue(self.integration["source_closure_pass"])
        self.assertTrue(self.integration["runtime_classification_gate_pending"])
        for key in (
            "ready",
            "approval_created",
            "candidate_success",
            "causal_result_allowed",
            "device_contact",
            "d0_authorized",
            "d1_authorized",
            "f1_authorized",
            "replay_authorized",
        ):
            with self.subTest(key=key):
                self.assertFalse(self.integration[key])

    def test_source_key_and_raw_first_boundaries_are_documented_exactly(self):
        comparison = self.integration["components"]["adapter_pin"]["source_keys"]
        self.assertEqual(comparison["pinned"]["count"], 436)
        self.assertEqual(comparison["current"]["count"], 437)
        self.assertEqual(comparison["mismatch_count"], 3)
        self.assertFalse(comparison["required_arming_key_present_pinned"])
        self.assertTrue(comparison["required_arming_key_present_current"])
        projection = self.prerequisite["raw_first_execution_closure"]
        self.assertEqual(
            projection["semantic_projection_omits_only"],
            [
                "all_revalidation_python_files_scanned",
                "subprocess_modules_scanned",
            ],
        )

    def test_append_only_row_opens_only_the_review_29_obligation(self):
        original_rows = [
            line
            for line in self.ledger.splitlines()
            if "| h0-process-v2-integration-prerequisites-29 |" in line
        ]
        correction_rows = [
            line
            for line in self.ledger.splitlines()
            if "| h0-process-v2-integration-prerequisites-followup-29 |" in line
        ]
        self.assertEqual(len(original_rows), 1)
        self.assertEqual(len(correction_rows), 1)
        rows = original_rows
        self.assertIn(
            "P319_PROCESS_V2_INTEGRATION_PREREQUISITES_IMPLEMENTED_REVIEW_PENDING",
            rows[0],
        )
        self.assertIn("Independent review is required", rows[0])
        self.assertNotIn("PASS_GO_", rows[0])
        correction = correction_rows[0]
        self.assertIn(
            "P319_PROCESS_V2_INTEGRATION_VALIDATION_COUNT_CORRECTION_NO_NEW_OBLIGATION",
            correction,
        )
        self.assertIn("original h0-process-v2-integration-prerequisites-29", correction)
        self.assertIn("527 passed, 4 failed", correction)
        self.assertIn("1 separate materialization error", correction)
        self.assertIn("531 passed, zero failed", correction)
        self.assertIn("post-correction result only", correction)
        self.assertIn("opens no new obligation", correction)
        self.assertNotIn("PASS_GO_", correction)
        self.assertNotIn("_REVIEW_PENDING", correction)

    def test_goal_propagates_the_blocked_integration_without_live_authority(self):
        self.assertIn("changed adapter closure now requires requalification", self.goal)
        self.assertIn("runner-consumed global candidate registry", self.goal)
        self.assertIn("`BLOCKED_P319_PROCESS_V2_INTEGRATION_H0`", self.goal)
        self.assertIn("no ready/run manifest", self.goal)


if __name__ == "__main__":
    unittest.main()

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
REPIN_REPORT = ROOT / (
    "docs/reports/"
    "S22PLUS_FYG8_P319_PROCESS_V2_CONTRACT_REPIN_AND_SUITE_CARDINALITY_H0_2026-08-22.md"
)
DOWNLOAD_RECOVERY_REPORT = ROOT / (
    "docs/reports/"
    "S22PLUS_FYG8_P319_DOWNLOAD_REQUEST_RECOVERY_H0_2026-08-23.md"
)
FRESH_BASELINE_REPORT = ROOT / (
    "docs/reports/"
    "S22PLUS_FYG8_P319_FRESH_BASELINE_CAPABILITY_H0_2026-08-24.md"
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
CURRENT_INTEGRATION = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p319/"
    "process-v2-integration-qualification-v1-20260823-04/result.json"
)
CURRENT_PREREQUISITE = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p319/"
    "process-v2-prerequisite-audit-20260823-03.json"
)
REQUEST_RECOVERY_INTEGRATION = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p319/"
    "process-v2-integration-qualification-v1-20260823-02/result.json"
)
REQUEST_RECOVERY_PREREQUISITE = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p319/"
    "process-v2-prerequisite-audit-20260823-02.json"
)
P319_TEST_PATTERN = "test_s22plus_fyg8_p319*.py"
P319_SELECTED_TEST_COUNT = 603
P319_EXECUTABILITY_CLASS = (
    "test_s22plus_fyg8_p319_experiment_executability_closure."
    "P319ExperimentExecutabilityClosureTest."
)
P319_EXECUTABILITY_CLASS_COUNT = 13


def _flatten_tests(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from _flatten_tests(item)
        else:
            yield item


def _p319_selected_test_ids():
    suite = unittest.TestLoader().discover(
        str(ROOT / "tests"), pattern=P319_TEST_PATTERN
    )
    return [test.id() for test in _flatten_tests(suite)]


class P319ProcessV2IntegrationDocsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = REPORT.read_text(encoding="utf-8")
        cls.repin_report = REPIN_REPORT.read_text(encoding="utf-8")
        cls.download_recovery_report = DOWNLOAD_RECOVERY_REPORT.read_text(
            encoding="utf-8"
        )
        cls.fresh_baseline_report = FRESH_BASELINE_REPORT.read_text(encoding="utf-8")
        cls.ledger = LEDGER.read_text(encoding="utf-8")
        cls.goal = GOAL.read_text(encoding="utf-8")
        cls.prerequisite_bytes = PREREQUISITE.read_bytes()
        cls.integration_bytes = INTEGRATION.read_bytes()
        cls.prerequisite = json.loads(cls.prerequisite_bytes)
        cls.integration = json.loads(cls.integration_bytes)
        cls.current_integration_bytes = CURRENT_INTEGRATION.read_bytes()
        cls.current_integration = json.loads(cls.current_integration_bytes)
        cls.current_prerequisite_bytes = CURRENT_PREREQUISITE.read_bytes()
        cls.request_recovery_integration_bytes = REQUEST_RECOVERY_INTEGRATION.read_bytes()
        cls.request_recovery_integration = json.loads(
            cls.request_recovery_integration_bytes
        )
        cls.request_recovery_prerequisite_bytes = REQUEST_RECOVERY_PREREQUISITE.read_bytes()

    def test_report_is_scoped_reviewed_and_names_all_current_blockers(self):
        self.assertIn(
            "Status: `PASS_GO_P319_PROCESS_V2_INTEGRATION_PREREQUISITES_H0_CAPABILITY_V1`",
            self.report,
        )
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
        self.assertIn("After this row, full-tail accounting is 47 total / 33 resolved /", self.report)
        self.assertIn("14 unresolved", self.report)
        self.assertIn("Independent scoped review", self.report)
        selected = _p319_selected_test_ids()
        self.assertEqual(len(selected), P319_SELECTED_TEST_COUNT)
        executability = [
            test_id for test_id in selected if P319_EXECUTABILITY_CLASS in test_id
        ]
        self.assertEqual(len(executability), P319_EXECUTABILITY_CLASS_COUNT)
        self.assertEqual(len(set(executability)), P319_EXECUTABILITY_CLASS_COUNT)
        self.assertIn(
            "Status: `PASS_GO_P319_PROCESS_V2_CONTRACT_REPIN_AND_SUITE_CARDINALITY_H0_CAPABILITY_V1`",
            self.repin_report,
        )
        self.assertIn("49 total / 35 resolved / 14 unresolved", self.repin_report)
        self.assertIn("h0-process-v2-contract-repin-31", self.repin_report)
        self.assertIn(
            "PASS_GO_P319_PROCESS_V2_CONTRACT_REPIN_AND_SUITE_CARDINALITY_H0_CAPABILITY_V1",
            self.repin_report,
        )
        self.assertIn("Ran 532 tests in 166.955s", self.repin_report)
        self.assertIn("531 pass, 0 fail, 1 error", self.repin_report)
        self.assertIn(
            "test_independent_tmp_regeneration_is_byte_identical",
            self.repin_report,
        )
        self.assertIn(
            "/mnt/android-lab-logical/vendor_dlkm/lib/modules/spu_verify.ko",
            self.repin_report,
        )
        self.assertIn("has exactly three\nblockers", self.repin_report)
        self.assertIn("No ready/live authority", self.repin_report)

    def test_report_keeps_no_proof_buckets_and_runtime_gate_distinct(self):
        self.assertIn("`NONCAUSAL_SUCCESS_PATH`", self.report)
        self.assertIn("`NO_PROOF_EXPERIMENT_PRECONDITION`", self.report)
        self.assertIn("`NO_PROOF_OBSERVER`", self.report)
        self.assertIn("post-run causal-classification gate", self.report)
        self.assertIn("not an extra pre-approval blocker", self.report)

    def test_fresh_baseline_reducer_review_is_non_authoritative(self):
        report = self.fresh_baseline_report
        self.assertIn(
            "Status: `PASS_GO_P319_FRESH_BASELINE_REDUCER_H0_CAPABILITY_V1`",
            report,
        )
        self.assertIn("producer_execution_closure_reviewed=false", report)
        self.assertIn("producer_execution_closure_authoritative=false", report)
        self.assertIn("cannot produce or validate a fresh baseline", report)
        self.assertIn("does not clear\n`FRESH_BASELINE_MISSING`", report)
        self.assertIn("h0-fresh-baseline-capability-review-39", self.ledger)

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
            (
                REQUEST_RECOVERY_PREREQUISITE,
                self.request_recovery_prerequisite_bytes,
                12528,
                "4785343654809f5f01c8c055e280102eb2dd834bd6ce2cc1378ce24dee3bec5c",
            ),
            (
                REQUEST_RECOVERY_INTEGRATION,
                self.request_recovery_integration_bytes,
                61592,
                "b376a2c5523335c203df042e30ad8b4eaf08b21e5c8036eecbc67f8ae2712258",
            ),
            (
                CURRENT_PREREQUISITE,
                self.current_prerequisite_bytes,
                12537,
                "ee6a1e79dfcd155f5bcdec95fbea61eea0c0645a8cd3ea2c7d30a04b59d7837c",
            ),
            (
                CURRENT_INTEGRATION,
                self.current_integration_bytes,
                61388,
                "745814926e44763214ed15d3eeb10d2a4c4e8bb591d3b92d96685aa4cf4aff88",
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
        self.assertTrue(self.current_integration["source_closure_pass"])
        self.assertEqual(
            {item["code"] for item in self.current_integration["blockers"]},
            {"FRESH_BASELINE_MISSING"},
        )
        comparison = self.current_integration["components"]["adapter_pin"]["source_keys"]
        self.assertEqual(comparison["mismatch_count"], 0)
        self.assertEqual(comparison["mismatch_keys"], [])
        self.assertTrue(comparison["exact_match"])
        self.assertNotIn(
            "EXECUTABILITY_SOURCE_CLOSURE_BLOCKED",
            {item["code"] for item in self.current_integration["blockers"]},
        )
        self.assertFalse(
            self.current_integration["download_request_cut_recovery_blocked"]
        )
        self.assertTrue(self.current_integration["runner_recovery_closed"])
        self.assertFalse(self.current_integration["runner_ready"])
        self.assertEqual(
            {item["code"] for item in self.request_recovery_integration["blockers"]},
            {"FRESH_BASELINE_MISSING", "REQUALIFICATION_REQUIRED"},
        )

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

    def test_append_only_rows_preserve_and_resolve_only_topic_29(self):
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
        review_rows = [
            line
            for line in self.ledger.splitlines()
            if "| h0-process-v2-integration-prerequisites-review-29 |" in line
        ]
        self.assertEqual(len(original_rows), 1)
        self.assertEqual(len(correction_rows), 1)
        self.assertEqual(len(review_rows), 1)
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
        review = review_rows[0]
        self.assertIn(
            "PASS_GO_P319_PROCESS_V2_INTEGRATION_PREREQUISITES_H0_CAPABILITY_V1",
            review,
        )
        self.assertIn("Independent scoped review resolves only", review)
        self.assertIn("532 = 531 passed + 0 failed + 1 unavailable", review)
        self.assertIn("47 total / 32 resolved / 15 unresolved", review)
        self.assertIn("no ready/run manifest", review)
        self.assertNotIn("_REVIEW_PENDING", review)

    def test_goal_propagates_the_blocked_integration_without_live_authority(self):
        self.assertIn(
            "Status: `PASS_GO_P319_DOWNLOAD_REQUEST_CUT_RECOVERY_H0_CAPABILITY_V1`",
            self.download_recovery_report,
        )
        self.assertIn("50/36/14", self.download_recovery_report)
        self.assertIn("seventeen bound fixtures", self.download_recovery_report)
        self.assertIn("is not review authority", self.download_recovery_report)
        self.assertIn("binds all 437 current source keys", self.goal)
        self.assertIn("independently reviewed H0-only `PASS_GO` under topic 34", self.goal)
        self.assertIn("runner-consumed global candidate registry", self.goal)
        self.assertIn("topic 32 now independently closes", self.goal)
        self.assertIn("`BLOCKED_P319_PROCESS_V2_INTEGRATION_H0`", self.goal)
        self.assertIn("only on `FRESH_BASELINE_MISSING`", self.goal)
        self.assertIn("no ready/run manifest", self.goal)
        self.assertIn("scoped independent H0 `PASS_GO`", self.goal)
        self.assertIn("independently reviewed H0-only prerequisite integration", self.goal)


if __name__ == "__main__":
    unittest.main()

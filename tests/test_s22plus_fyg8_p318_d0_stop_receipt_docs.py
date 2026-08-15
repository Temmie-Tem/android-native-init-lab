from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
GOAL = ROOT / "GOAL.md"
PROCESS = ROOT / "docs/operations/DEVICE_ACTION_PROCESS_V2.md"
LEDGER = ROOT / "docs/operations/CAMPAIGN_LEDGER_S22PLUS.md"
REPORT = ROOT / (
    "docs/reports/"
    "S22PLUS_FYG8_P318_D0_FAIL_CLOSED_RECEIPT_H0_2026-08-16.md"
)
ADAPTER = (
    ROOT / "workspace/public/src/scripts/revalidation/device_action_d0_v2.py"
)


class P318D0StopReceiptDocsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.goal = GOAL.read_text(encoding="utf-8")
        cls.process = PROCESS.read_text(encoding="utf-8")
        cls.ledger = LEDGER.read_text(encoding="utf-8")
        cls.report = REPORT.read_text(encoding="utf-8")
        cls.adapter = ADAPTER.read_text(encoding="utf-8")

    def test_report_has_scoped_pass_go_and_creates_no_live_authority(self):
        for token in (
            "`PASS_GO_P318_D0_FAIL_CLOSED_RECEIPT_H0_CAPABILITY_V1`",
            "creates no D0, D1, F1, recovery, replay, or live\nauthority",
            "No\nreboot or connected retry is authorized by this report.",
            "final_health_observed=false",
            "result_reusable=false",
        ):
            self.assertIn(token, self.report)
        self.assertIn("downstream requalification", self.report)

    def test_common_process_requires_a_nonreusable_post_capture_stop_receipt(self):
        for token in (
            "a retained-family or decoder\nrejection must publish one typed, no-replace `result.json`",
            "final continuity and final\nhealth were not observed",
            "can never satisfy D0 success or\nprepared-run validation",
            "A failure before a complete bounded capture makes no\nsuch raw-evidence claim.",
        ):
            self.assertIn(token, self.process)

    def test_goal_keeps_ready_fail_closed_after_scoped_review(self):
        for token in (
            "three residual P3.17 records",
            "no result receipt",
            "independent H0 `PASS_GO`",
            "ready verification remains fail closed",
        ):
            self.assertIn(token, self.goal)
        self.assertLessEqual(len(self.goal.splitlines()), 900)

    def test_adapter_exposes_distinct_success_and_stop_schemas(self):
        for token in (
            'D0_STOP_RESULT_SCHEMA = "device_action_d0_stop_result_v1"',
            'D0_STOP_VERSION = "device-action-d0-stop-v1"',
            'D0_STOP_VERDICT = "STOP_DEVICE_ACTION_D0_V2_BASELINE_REJECTED"',
            '"baseline-decoder-rejected"',
            '"retained-evidence-present"',
            '"final_target_continuity_observed": False',
            '"final_health_observed": False',
            '"result_reusable": False',
        ):
            self.assertIn(token, self.adapter)
        self.assertEqual(self.adapter.count("def validate_stop_result("), 1)

    def test_append_only_ledger_records_device_stop_before_h0_repair(self):
        device = (
            "live-prerequisites-d0-1 | D0 | RETAINED_BASELINE_HOST_STOP | "
            "HEALTHY | NO_PROOF_OBSERVER | 0/0"
        )
        repair = (
            "h0-d0-stop-receipt-9 | H0 | "
            "P318_D0_FAIL_CLOSED_RECEIPT_IMPLEMENTED_REVIEW_PENDING | "
            "HEALTHY | PROVED | 0/0"
        )
        review = (
            "h0-d0-stop-receipt-review-9 | H0 | "
            "PASS_GO_P318_D0_FAIL_CLOSED_RECEIPT_H0_CAPABILITY_V1 | "
            "HEALTHY | PROVED | 0/0"
        )
        self.assertEqual(self.ledger.count(device), 1)
        self.assertEqual(self.ledger.count(repair), 1)
        self.assertEqual(self.ledger.count(review), 1)
        self.assertLess(self.ledger.index(device), self.ledger.index(repair))
        self.assertLess(self.ledger.index(repair), self.ledger.index(review))


if __name__ == "__main__":
    unittest.main()

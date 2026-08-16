import hashlib
import json
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
READY = ROOT / (
    "workspace/public/src/device-action/manifests/"
    "s22plus_fyg8_p318_process_v2_ready_1.json"
)


class P318D0StopReceiptDocsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.goal = GOAL.read_text(encoding="utf-8")
        cls.process = PROCESS.read_text(encoding="utf-8")
        cls.ledger = LEDGER.read_text(encoding="utf-8")
        cls.report = REPORT.read_text(encoding="utf-8")
        cls.adapter = ADAPTER.read_text(encoding="utf-8")
        cls.ready_bytes = READY.read_bytes()
        cls.ready = json.loads(cls.ready_bytes.decode("ascii"))

    def test_report_has_scoped_pass_go_and_creates_no_live_authority(self):
        for token in (
            "`PASS_GO_P318_D0_FAIL_CLOSED_RECEIPT_H0_CAPABILITY_V1`",
            "creates no D0, D1, F1, recovery, replay, or live\nauthority",
            "does not itself authorize that D1, a new D0,\nreboot, connected retry",
            "final_health_observed=false",
            "result_reusable=false",
        ):
            self.assertIn(token, self.report)
        self.assertIn("downstream independent requalification", self.report)

    def test_downstream_requalification_is_exact_and_independently_approved(self):
        for token in (
            "PASS_GO_P318_D0_STOP_RECEIPT_PROCESS_V2_REQUALIFICATION_H0_CAPABILITY_V1",
            "`375db867fb55`",
            "`2a4d639b55aa`",
            "`d96381c12e23`",
            "`35324f4a4b14`",
            "`082c046f9091`",
            "`0b74986f8531`",
            "`129ad86b934c`",
            "`6b8505bcdd48` to `e1dc1eb07f2c`",
            "P3.18 passes 142/142",
            "common Process-v2 suite\n120/120",
            "does not itself authorize that D1",
        ):
            self.assertIn(token, self.report)
        self.assertEqual(len(self.ready_bytes), 2778)
        self.assertEqual(
            hashlib.sha256(self.ready_bytes).hexdigest(),
            "082c046f90914730172426c16222981039027d9384d3912fb09ee99d081a73d3",
        )
        contract = self.ready["observation"]["acceptance"]["contract"]
        self.assertEqual(
            contract["candidate_static"]["sha256"],
            "2a4d639b55aa21cf8f52dba505e9bc2d9dfd33f20cd3b217a7c482906aeea4df",
        )
        self.assertEqual(
            contract["run_manifest"]["sha256"],
            "d96381c12e23b42b3da414977721cce5c680a7729e3755bbead41ebf1894d819",
        )
        self.assertEqual(
            contract["static_check"]["sha256"],
            "35324f4a4b14f73c3514078f85020e4cd6a5bf73abc08f77cc7d1b4f90f8d2b7",
        )

    def test_common_process_requires_a_nonreusable_post_capture_stop_receipt(self):
        for token in (
            "a retained-family or decoder\nrejection must publish one typed, no-replace `result.json`",
            "final continuity and final\nhealth were not observed",
            "can never satisfy D0 success or\nprepared-run validation",
            "A failure before a complete bounded capture makes no\nsuch raw-evidence claim.",
        ):
            self.assertIn(token, self.process)

    def test_goal_keeps_regenerated_ready_host_only(self):
        for token in (
            "three residual P3.17 records",
            "no result receipt",
            "independent H0 `PASS_GO`",
            "ready is `082c046f9091`",
            "downstream requalification now have\nindependent H0 `PASS_GO`",
            "Fresh post-rotation P3.18 D0 passed",
            "2,097,136-byte marker-free baseline",
            "binding `fd68d3b4713d` is prepared",
            "F1/live remain unauthorized",
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
        requalification = (
            "h0-d0-stop-requalification-10 | H0 | "
            "P318_D0_STOP_RECEIPT_PROCESS_V2_REQUALIFICATION_"
            "IMPLEMENTED_REVIEW_PENDING | HEALTHY | PROVED | 0/0"
        )
        requalification_review = (
            "h0-d0-stop-requalification-review-10 | H0 | "
            "PASS_GO_P318_D0_STOP_RECEIPT_PROCESS_V2_REQUALIFICATION_"
            "H0_CAPABILITY_V1 | HEALTHY | PROVED | 0/0"
        )
        self.assertEqual(self.ledger.count(device), 1)
        self.assertEqual(self.ledger.count(repair), 1)
        self.assertEqual(self.ledger.count(review), 1)
        self.assertEqual(self.ledger.count(requalification), 1)
        self.assertEqual(self.ledger.count(requalification_review), 1)
        self.assertLess(self.ledger.index(device), self.ledger.index(repair))
        self.assertLess(self.ledger.index(repair), self.ledger.index(review))
        self.assertLess(self.ledger.index(review), self.ledger.index(requalification))
        self.assertLess(
            self.ledger.index(requalification),
            self.ledger.index(requalification_review),
        )


if __name__ == "__main__":
    unittest.main()

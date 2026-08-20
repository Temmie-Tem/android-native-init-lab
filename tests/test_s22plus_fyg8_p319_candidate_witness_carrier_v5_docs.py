from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / (
    "docs/reports/"
    "S22PLUS_FYG8_P319_CANDIDATE_WITNESS_CARRIER_V5_H0_2026-08-20.md"
)
GOAL = ROOT / "GOAL.md"
TARGET = ROOT / "docs/operations/targets/S22PLUS_FYG8_TARGET_CONTRACT.md"
LEDGER = ROOT / "docs/operations/CAMPAIGN_LEDGER_S22PLUS.md"


class P319CandidateWitnessCarrierV5DocsTest(unittest.TestCase):
    def test_report_states_exact_h0_pass_boundary(self):
        report = REPORT.read_text(encoding="utf-8")
        self.assertIn("Status: **SCOPED_PASS_GO_H0_CAPABILITY**", report)
        self.assertIn("11,647 bytes", report)
        self.assertIn("05ee3385c8c80010", report)
        self.assertIn("c3b25c4f1eb193f6", report)
        self.assertIn("3cfa39591486e354", report)
        self.assertIn("causal_result_allowed = false", report)
        self.assertIn("No new\n`pdic_max77705.ko`", report)
        self.assertIn("Independent Luna MAX review", report)

    def test_report_distinguishes_v4_and_v5(self):
        report = REPORT.read_text(encoding="utf-8")
        self.assertIn("V4 CRC and encoder bodies\nremain byte-identical", report)
        self.assertIn("does not retain that poll\npayload", report)
        self.assertIn("V5 has magic `MXD5`", report)
        self.assertIn("positions 105 and 106", report)

    def test_goal_points_to_current_receipt_and_no_build(self):
        goal = GOAL.read_text(encoding="utf-8")
        self.assertIn("no-clobber `05ee3385`", goal)
        self.assertIn("independently reviewed plain-CLI current receipt", goal)
        self.assertIn("No successor candidate build exists yet", goal)
        self.assertIn(
            "S22PLUS_FYG8_P319_CANDIDATE_WITNESS_CARRIER_V5_H0_2026-08-20.md",
            goal,
        )

    def test_goal_and_target_contract_line_limits_hold(self):
        self.assertLessEqual(len(GOAL.read_text(encoding="utf-8").splitlines()), 900)
        self.assertEqual(len(TARGET.read_text(encoding="utf-8").splitlines()), 260)

    def test_append_only_ledger_preserves_both_nonresolving_implementation_rows(self):
        ledger = LEDGER.read_text(encoding="utf-8")
        self.assertEqual(ledger.count("h0-candidate-witness-carrier-v5-12"), 1)
        self.assertEqual(
            ledger.count("h0-candidate-witness-carrier-v5-followup-12"), 1
        )
        self.assertEqual(
            ledger.count("h0-candidate-witness-carrier-v5-followup-13"), 1
        )
        row = next(
            line for line in ledger.splitlines()
            if "h0-candidate-witness-carrier-v5-12" in line
        )
        self.assertIn(
            "P319_CANDIDATE_WITNESS_CARRIER_V5_IMPLEMENTED_UNDER_EXISTING_TRANSPORT_REVIEW_OBLIGATION",
            row,
        )
        self.assertNotIn("PASS_GO_", row)
        self.assertIn("0/0", row)
        self.assertIn("h0-candidate-witness-transport-review-7", row)
        successor = next(
            line for line in ledger.splitlines()
            if "h0-candidate-witness-carrier-v5-followup-12" in line
        )
        self.assertIn("11647-byte 3cfa3959 -11 receipt remains", successor)
        self.assertIn("11647 bytes SHA-256 c3b25c4f", successor)
        self.assertNotIn("PASS_GO_", successor)
        default_repair = next(
            line for line in ledger.splitlines()
            if "h0-candidate-witness-carrier-v5-followup-13" in line
        )
        self.assertIn("11647 bytes SHA-256 05ee3385", default_repair)
        self.assertIn("Plain --audit-only verifies -13", default_repair)
        self.assertNotIn("PASS_GO_", default_repair)

    def test_ledger_order_resolves_only_the_transport_topic(self):
        lines = LEDGER.read_text(encoding="utf-8").splitlines()
        pending = next(
            index for index, line in enumerate(lines)
            if "h0-candidate-witness-transport-7" in line
        )
        implementation = next(
            index for index, line in enumerate(lines)
            if "h0-candidate-witness-carrier-v5-12" in line
        )
        successor = next(
            index for index, line in enumerate(lines)
            if "h0-candidate-witness-carrier-v5-followup-12" in line
        )
        default_repair = next(
            index for index, line in enumerate(lines)
            if "h0-candidate-witness-carrier-v5-followup-13" in line
        )
        review = next(
            index for index, line in enumerate(lines)
            if "h0-candidate-witness-transport-review-7" in line
            and " | PASS_GO_" in line
        )
        self.assertLess(pending, implementation)
        self.assertLess(implementation, successor)
        self.assertLess(successor, default_repair)
        self.assertLess(default_repair, review)
        self.assertEqual(sum(
            "h0-candidate-witness-transport-review-7" in line
            and " | PASS_GO_" in line
            for line in lines
        ), 1)


if __name__ == "__main__":
    unittest.main()

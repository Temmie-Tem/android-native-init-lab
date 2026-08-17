import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / (
    "docs/reports/"
    "S22PLUS_FYG8_P319_BEHAVIORAL_RAW_FIRST_BOUNDARY_H0_2026-08-17.md"
)
AUDIT = ROOT / (
    "workspace/public/src/scripts/revalidation/"
    "s22plus_fyg8_raw_first_observer_audit.py"
)
EXPECTED = ROOT / (
    "workspace/public/src/scripts/revalidation/"
    "s22plus_fyg8_consumed_suite_expected_failures.py"
)
LEDGER = ROOT / "docs/operations/CAMPAIGN_LEDGER_S22PLUS.md"


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class P319BehavioralBoundaryDocsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = REPORT.read_text(encoding="utf-8")
        cls.audit = load(AUDIT, "p319_behavioral_boundary_audit_doc")
        cls.expected = load(EXPECTED, "p319_behavioral_boundary_expected_doc")

    def test_report_states_the_h0_only_authority_boundary(self):
        for token in (
            "IMPLEMENTED_REVIEW_PENDING",
            "NO DEVICE OR LIVE AUTHORITY",
            "creates no D0, D1, F1, recovery, replay, device, or live authority",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)

    def test_report_counts_match_the_live_auditor_constants(self):
        # The report is only useful if its numbers cannot drift from the code.
        self.assertIn(
            f"| S22+-scoped, byte-frozen | {self.audit.PRE_BOUNDARY_DEVICE_SOURCE_COUNT} |",
            self.report,
        )
        other = len(self.audit.PRE_BOUNDARY_DEVICE_SOURCES) - (
            self.audit.PRE_BOUNDARY_DEVICE_SOURCE_COUNT
        )
        self.assertIn(
            f"| other-target, membership-only | {other} |", self.report
        )

    def test_report_expected_failure_count_matches_the_manifest(self):
        self.assertIn(
            f"distinct expected failures: "
            f"{len(self.expected.EXPECTED_FAILURES)};",
            self.report,
        )

    def test_report_records_the_withdrawn_objection_and_its_evidence(self):
        for token in (
            "That conclusion was wrong.",
            "2026-08-16T07:24:34Z",
            "ModuleNotFoundError: No module named 'device_action_raw_capture_v1'",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)

    def test_report_records_the_red_acm_control_without_claiming_a_control(self):
        self.assertIn(
            "has no passing positive control, and the\nreason is a real "
            "interface change, not an environment problem",
            self.report,
        )
        self.assertIn("kernel.apparmor_restrict_unprivileged_userns = 1", self.report)
        # A control that was hand-fitted until it passed would be worthless.
        self.assertIn("green by construction rather than by evidence", self.report)
        self.assertNotIn("PASS_P318_CDC_ACM_QEMU_REAL_OBSERVER_H0\n", self.report)

    def test_report_separates_the_plumbing_repairs_from_the_semantic_stop(self):
        for token in (
            "candidate observer guard semantics mismatch",
            "ModuleNotFoundError",
            "`-I`, which implies `-P`",
            "This unit repaired the two plumbing failures and deliberately "
            "stopped at the\nthird.",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)

    def test_report_counts_the_broken_consumers_of_one_migration(self):
        self.assertIn("## Three consumers, one cause", self.report)
        self.assertIn(
            "A passing source-identity gate masked a functional\nbreak in the "
            "primitive it was gating.",
            self.report,
        )

    def test_ledger_records_one_pending_row_for_this_topic(self):
        rows = [
            line
            for line in LEDGER.read_text(encoding="utf-8").splitlines()
            if "h0-raw-first-observer-2 " in line
        ]
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertIn("s22plus-fyg8-p319", row)
        self.assertIn(
            "P319_BEHAVIORAL_RAW_FIRST_BOUNDARY_IMPLEMENTED_REVIEW_PENDING", row
        )
        self.assertIn("| 0/0 |", row)


if __name__ == "__main__":
    unittest.main()

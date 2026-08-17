import importlib.util
import re
import sys
import unittest
from pathlib import Path


COUNT_WORDS = {
    "One": 1,
    "Two": 2,
    "Three": 3,
    "Four": 4,
    "Five": 5,
    "Six": 6,
    "Seven": 7,
    "Eight": 8,
}


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

    def consumers_section(self):
        """Return the section's heading count word and its table rows."""
        section = re.search(
            r"^## (\w+) consumers, one cause$(.*?)(?=^## )",
            self.report,
            re.MULTILINE | re.DOTALL,
        )
        self.assertIsNotNone(section, "consumers section missing")
        table = re.search(
            r"^\| Consumer \| Failure \|\n\|---\|---\|\n((?:\|.*\n)+)",
            section.group(2),
            re.MULTILINE,
        )
        self.assertIsNotNone(table, "consumers table missing")
        return section.group(1), table.group(1).splitlines()

    def test_report_states_what_the_passing_identity_gate_masked(self):
        self.assertIn(
            "A passing source-identity gate masked a functional\nbreak in the "
            "primitive it was gating.",
            self.report,
        )

    def test_report_consumer_count_matches_its_own_table(self):
        # The heading claimed three while the real set was four, so derive the
        # count from the table instead of restating it in prose.
        word, rows = self.consumers_section()
        self.assertIn(word, COUNT_WORDS)
        self.assertEqual(COUNT_WORDS[word], len(rows))

    def test_report_records_the_fourth_consumer_and_its_causal_proof(self):
        for token in (
            "This section first said three. That was an undercount.",
            "s22plus_fyg8_p313_guard_lifetime_fixture.py",
            "P3.13 lifetime receipts did not reopen",
            "PASS_P313_GUARD_LIFETIME_AND_V2_COMPATIBILITY_HOST_ONLY",
            "proved by substitution, not inferred",
            "The file was restored and its\ndigest reverified afterwards.",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)

    def test_report_states_how_the_consumer_count_was_bounded(self):
        # A bound a reviewer can recheck, and an explicit limit on it.
        for token in (
            "The count is bounded rather than asserted",
            "s22plus_fyg8_p318_selector_negative_control.py",
            "not a proof that no fifth consumer exists",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)

    def test_report_explains_why_the_fourth_consumer_stayed_invisible(self):
        for token in (
            "`Ran 0 tests ...\nerrors=1`",
            "discovers `*p318*`",
            "expected invalidations after the common\nlive-observer SOURCE_KEY change",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)

    def test_report_requires_one_shared_guard_fixture_not_two_repairs(self):
        for token in (
            "they must not\nbe repaired separately",
            "write the same synthetic receipt twice",
            "a single shared guard-arming fixture",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)

    def test_ledger_records_the_guard_fixture_invalidation_finding(self):
        rows = [
            line
            for line in LEDGER.read_text(encoding="utf-8").splitlines()
            if "h0-guard-fixture-invalidation-1 " in line
        ]
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertIn("s22plus-fyg8-p319", row)
        self.assertIn(
            "P319_P313_GUARD_FIXTURE_INVALIDATION_UNRECORDED_REVIEW_PENDING", row
        )
        self.assertIn("| 0/0 |", row)
        # The finding is only useful if the row carries its causal proof.
        for token in (
            "PASS_P313_GUARD_LIFETIME_AND_V2_COMPATIBILITY_HOST_ONLY",
            "c41fd1ddf7^",
            "proved by substitution",
        ):
            with self.subTest(token=token):
                self.assertIn(token, row)

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

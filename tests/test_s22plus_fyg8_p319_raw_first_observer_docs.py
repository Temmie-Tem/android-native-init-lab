import contextlib
import hashlib
import importlib.util
import io
from pathlib import Path
import stat
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
REVALIDATION = ROOT / "workspace/public/src/scripts/revalidation"
AUDITOR = REVALIDATION / "s22plus_fyg8_raw_first_observer_audit.py"
REPORT = ROOT / (
    "docs/reports/"
    "S22PLUS_FYG8_P319_RAW_FIRST_OBSERVER_BOUNDARY_H0_2026-08-17.md"
)
TARGET = ROOT / "docs/operations/targets/S22PLUS_FYG8_TARGET_CONTRACT.md"
LEDGER = ROOT / "docs/operations/CAMPAIGN_LEDGER_S22PLUS.md"
GOAL = ROOT / "GOAL.md"
RECEIPT = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p319/"
    "raw-first-observer-audit-20260821-05-population-parse-diagnostic.json"
)
# The previous current receipt is preserved as superseded evidence.  It must
# not be rewritten when the population-diagnostic cut gets its own receipt.
PREVIOUS_CURRENT_RECEIPT = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p319/"
    "raw-first-observer-audit-20260821-04-cross-target-membership-default.json"
)
EARLIER_CURRENT_RECEIPT = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p319/"
    "raw-first-observer-audit-20260821-03-cross-target-membership.json"
)
CROSS_TARGET_PREDECESSOR_RECEIPT = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p319/"
    "raw-first-observer-audit-20260819-02-review-corrections.json"
)
# Superseded when the runner docstring was corrected after independent review.
USB_ROLE_STATE_RECEIPT = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p319/"
    "raw-first-observer-audit-20260819-01-usb-role-state.json"
)
# Superseded when the USB role/state observer joined the closed inventory.  It
# is kept rather than regenerated: its filename names the log-harvest unit, and
# rewriting it would falsify that unit's evidence instead of recording this one.
LOG_HARVEST_RECEIPT = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p319/"
    "raw-first-observer-audit-20260818-06-log-harvest.json"
)
# The approved 10,040-byte `7f9e6f6c` predecessor stays on disk as historical
# evidence.  It is no longer the deterministic regeneration of the current
# auditor, which now detects device acquisition by behavior instead of filename.
PREDECESSOR_RECEIPT = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p319/"
    "raw-first-observer-audit-20260817-01.json"
)


def load_auditor():
    spec = importlib.util.spec_from_file_location(
        "s22plus_fyg8_raw_first_observer_audit_docs_tested", AUDITOR
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class P319RawFirstObserverDocsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.auditor = load_auditor()
        cls.report = REPORT.read_text(encoding="utf-8")
        cls.target = TARGET.read_text(encoding="utf-8")
        cls.ledger = LEDGER.read_text(encoding="utf-8")
        cls.goal = GOAL.read_text(encoding="utf-8")

    def test_private_receipt_is_exact_deterministic_regeneration(self):
        self.assertEqual(
            self.auditor.DEFAULT_OUTPUT.as_posix(),
            "workspace/private/outputs/s22plus_fyg8_p319/"
            "raw-first-observer-audit-20260821-05-population-parse-diagnostic.json",
        )
        expected = self.auditor.encode_receipt(
            self.auditor.audit_sources(REVALIDATION)
        )
        self.assertEqual(RECEIPT.read_bytes(), expected)
        info = RECEIPT.stat()
        self.assertTrue(stat.S_ISREG(info.st_mode))
        self.assertEqual(stat.S_IMODE(info.st_mode), 0o400)
        self.assertEqual(info.st_nlink, 1)
        self.assertEqual(len(expected), 11012)
        self.assertEqual(
            hashlib.sha256(expected).hexdigest(),
            "5f7b2b07af478edb6f1416c8dba98563d305d2e1f8d531492457b3039fcdc352",
        )

    def test_previous_current_receipt_is_preserved_unmodified(self):
        info = PREVIOUS_CURRENT_RECEIPT.stat()
        self.assertTrue(stat.S_ISREG(info.st_mode))
        self.assertEqual(stat.S_IMODE(info.st_mode), 0o400)
        self.assertEqual(info.st_nlink, 1)
        payload = PREVIOUS_CURRENT_RECEIPT.read_bytes()
        self.assertEqual(len(payload), 11012)
        self.assertEqual(
            hashlib.sha256(payload).hexdigest(),
            "d3e5013134c74837b2c36a14f5dfd8ac2ab874707dd5f30a5090002bc2a380da",
        )
        self.assertNotEqual(payload, RECEIPT.read_bytes())

    def test_earlier_current_receipt_is_preserved_unmodified(self):
        info = EARLIER_CURRENT_RECEIPT.stat()
        self.assertTrue(stat.S_ISREG(info.st_mode))
        self.assertEqual(stat.S_IMODE(info.st_mode), 0o400)
        self.assertEqual(info.st_nlink, 1)
        payload = EARLIER_CURRENT_RECEIPT.read_bytes()
        self.assertEqual(len(payload), 11012)
        self.assertEqual(
            hashlib.sha256(payload).hexdigest(),
            "2016f6cb812daa3ee633c65677b7418d80624cd0dd20a6635f9d8c57b2e0108d",
        )
        self.assertNotEqual(payload, PREVIOUS_CURRENT_RECEIPT.read_bytes())

    def test_cross_target_predecessor_receipt_is_preserved_unmodified(self):
        info = CROSS_TARGET_PREDECESSOR_RECEIPT.stat()
        self.assertTrue(stat.S_ISREG(info.st_mode))
        self.assertEqual(stat.S_IMODE(info.st_mode), 0o400)
        self.assertEqual(info.st_nlink, 1)
        payload = CROSS_TARGET_PREDECESSOR_RECEIPT.read_bytes()
        self.assertEqual(len(payload), 10296)
        self.assertEqual(
            hashlib.sha256(payload).hexdigest(),
            "e5689fee2322b22cba04c5ecfc21d00e59de0fe44e1f0834389ee783eee53f7f",
        )
        self.assertNotEqual(payload, EARLIER_CURRENT_RECEIPT.read_bytes())

    def test_superseded_role_state_receipt_is_preserved_unmodified(self):
        info = USB_ROLE_STATE_RECEIPT.stat()
        self.assertEqual(stat.S_IMODE(info.st_mode), 0o400)
        self.assertEqual(
            hashlib.sha256(USB_ROLE_STATE_RECEIPT.read_bytes()).hexdigest(),
            "5cd4258d8cb1ddb01af5c6b96855a8cc2b6e0d979e02187da6845d133e6fcfd4",
        )

    def test_superseded_log_harvest_receipt_is_preserved_unmodified(self):
        info = LOG_HARVEST_RECEIPT.stat()
        self.assertTrue(stat.S_ISREG(info.st_mode))
        self.assertEqual(stat.S_IMODE(info.st_mode), 0o400)
        self.assertEqual(info.st_nlink, 1)
        self.assertEqual(
            hashlib.sha256(LOG_HARVEST_RECEIPT.read_bytes()).hexdigest(),
            "de30f2c861cad89313bed936c967c9fac379a8713faaffb494ef60fd02e50169",
        )

    def test_predecessor_receipt_is_preserved_and_no_longer_authority(self):
        info = PREDECESSOR_RECEIPT.stat()
        self.assertTrue(stat.S_ISREG(info.st_mode))
        self.assertEqual(stat.S_IMODE(info.st_mode), 0o400)
        self.assertEqual(info.st_nlink, 1)
        payload = PREDECESSOR_RECEIPT.read_bytes()
        self.assertEqual(len(payload), 10040)
        self.assertEqual(
            hashlib.sha256(payload).hexdigest(),
            "7f9e6f6c2048b55748532177e1af978b43a23828197f754d587a12eb73351011",
        )
        self.assertNotEqual(payload, RECEIPT.read_bytes())

    def test_behavioral_receipt_is_preserved_after_the_probe_registration(self):
        # Registering the Stage A truncation probe moved the scanned population
        # from 1,717 to 1,718, so this receipt stopped being the regeneration.
        superseded = RECEIPT.parent / (
            "raw-first-observer-audit-20260817-02-behavioral-device-detection.json"
        )
        info = superseded.stat()
        self.assertEqual(stat.S_IMODE(info.st_mode), 0o400)
        self.assertEqual(info.st_nlink, 1)
        payload = superseded.read_bytes()
        self.assertEqual(len(payload), 10330)
        self.assertEqual(
            hashlib.sha256(payload).hexdigest(),
            "1f0751d090729f1ece2c1c290f1306db1abe411957fcf053ba11ae7ce40edd4d",
        )
        self.assertNotEqual(payload, RECEIPT.read_bytes())

    def test_report_has_scoped_pass_and_does_not_grant_live_authority(self):
        for token in (
            "PASS_GO_P319_RAW_FIRST_OBSERVER_BOUNDARY_H0_CAPABILITY_V1; H0 ONLY",
            "PASS_GO_P319_RAW_FIRST_CROSS_TARGET_MEMBERSHIP_H0_CAPABILITY_V1",
            "host-only non-acquiring source",
            "pre-boundary S22+ inventory is still 127",
            "51 target-external membership entries",
            "S20+\nautonomous coordinator; that membership is not an active S22 source",
            "No D0/D1/F1/LIVE authority",
            "NO D0/D1/F1/LIVE AUTHORITY",
            "WRITE_AFTER_PARSE_DEVICE_EVIDENCE_LOSS",
            "294/294",
            "122/122",
            "188 of 209",
            "31 exact inactive legacy observer sources",
            "initial AST subprocess-import checks",
            "fresh direct operator request",
            "Stage B target remain unproved",
            "The required independent changed-closure review is complete",
            "full-tail taxonomy is 45 total / 31 resolved / 14 unresolved",
        ):
            self.assertIn(token, self.report)
        self.assertIn("Its scoped `PASS_GO` applies only", self.report)
        self.assertIn("8,729-byte `61617e20`", self.report)
        self.assertIn("8,828-byte\n`89f93fad`", self.report)
        self.assertIn("9,779-byte `0c8f8d3b`", self.report)
        self.assertIn("9,779-byte `54303f11`", self.report)
        self.assertIn("9,779-byte `60009597`", self.report)
        self.assertIn("9,982-byte `d42eecc0`", self.report)
        self.assertIn("closed inventory freezes `(name,size,sha256)` for 121", self.report)
        self.assertIn("2016f6cb812daa3ee633c65677b7418d80624cd0dd20a6635f9d8c57b2e0108d", self.report)
        self.assertIn("d3e5013134c74837b2c36a14f5dfd8ac2ab874707dd5f30a5090002bc2a380da", self.report)
        self.assertIn("e5689fee2322b22cba04c5ecfc21d00e59de0fe44e1f0834389ee783eee53f7f", self.report)
        self.assertIn("raw-first-observer-audit-20260821-04-cross-target-membership-default.json", self.report)
        self.assertIn("raw-first-observer-audit-20260821-03-cross-target-membership.json", self.report)

    def test_population_diagnostic_successor_is_scoped_pass_and_exit_codes_are_distinct(self):
        for token in (
            "Current population-parse diagnostic successor",
            "Status: **PASS_GO_P319_RAW_FIRST_POPULATION_PARSE_DIAGNOSTIC_H0_CAPABILITY_V1; H0 ONLY; DIAGNOSTIC CLASSIFICATION ONLY; NO D0/D1/F1/LIVE AUTHORITY**",
            "PASS_GO_P319_RAW_FIRST_POPULATION_PARSE_DIAGNOSTIC_H0_CAPABILITY_V1",
            "diagnostic classification only, not an enforcement upgrade",
            "already fail-closed later in the unfiltered `_imports_subprocess()`",
            "diagnostic inconsistency, not a working bypass",
            "UNPARSEABLE_POPULATION_SOURCE",
            "file/line/column",
            "CLI exit `3`",
            "ordinary boundary violation remains exit `2`",
            "1,729 Python files",
            "411 subprocess-import modules",
            "Raw auditor tests pass 20/20",
            "docs tests",
            "taxonomy 39/39",
            "raw-first-observer-audit-20260821-05-population-parse-diagnostic.json",
            "raw-first-observer-audit-20260821-04-cross-target-membership-default.json",
            "raw-first-observer-audit-20260821-03-cross-target-membership.json",
            "raw-first-observer-audit-20260819-02-review-corrections.json",
            "5f7b2b07af478edb6f1416c8dba98563d305d2e1f8d531492457b3039fcdc352",
            "879705ede830fc43a27063621e402991e5fb0c6f37c1ae2f8a84a570cdc102a8",
            "independent changed-closure review is complete",
            "46 total / 32 resolved / 14",
            "No D0/D1/F1/LIVE authority",
        ):
            self.assertIn(token, self.report)
        self.assertNotIn("fail-open repair", self.report.lower())

        bound = self.auditor.load_bound_auditor()
        original_audit = bound.audit_sources
        original_argv = sys.argv

        def run_with(error):
            def raise_error():
                raise error

            bound.audit_sources = raise_error
            sys.argv = [str(AUDITOR), "--audit"]
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = bound.main()
            return code, output.getvalue()

        try:
            population_code, population_output = run_with(
                bound.RawFirstPopulationUnparseableError(
                    "split_invalid.py",
                    message="invalid syntax",
                    lineno=3,
                    offset=12,
                )
            )
            self.assertEqual(population_code, 3)
            self.assertIn("UNPARSEABLE_POPULATION_SOURCE", population_output)
            self.assertIn("split_invalid.py:3:12", population_output)

            boundary_code, boundary_output = run_with(
                bound.RawFirstAuditError("boundary violation")
            )
            self.assertEqual(boundary_code, 2)
            self.assertIn("raw-first observer audit error", boundary_output)
        finally:
            bound.audit_sources = original_audit
            sys.argv = original_argv

    def test_permanent_target_boundary_has_review_triggers(self):
        for token in (
            "S22PLUS_D0_F1_RAW_FIRST_OBSERVER_PRESERVATION",
            "WRITE_AFTER_PARSE_DEVICE_EVIDENCE_LOSS",
            "has no expiry",
            "acquisition, handle ABI, parser signature, or active observer reachability",
        ):
            self.assertIn(token, self.target)
        self.assertEqual(len(self.target.splitlines()), 260)

    def test_goal_records_stage_b_proved_and_the_frontier_moved(self):
        # This test previously pinned "Stage B target are still unproved" and
        # "a fresh direct D0 request remains required".  Stage B has since run
        # and read CONTROL1, so the pin follows the fact rather than freezing a
        # statement that stopped being true.
        self.assertIn("permanent D0/F1 raw-first handle boundary", self.goal)
        self.assertIn("independent H0 PASS_GO", self.goal)
        # This pin first read "read CONTROL1 directly".  An independent review
        # showed Stage B reads the mxim debug dump 0x00-0x10, which does not
        # contain CONTROL1, and that the read consumes a latched REG_VDM_INT.
        self.assertIn(
            "Stage B has since run and read the mxim debug register dump "
            "0x00-0x10",
            self.goal,
        )
        self.assertIn("that dump does not contain CONTROL1", self.goal)
        self.assertIn("it was not side-effect free", self.goal)
        self.assertNotIn("read CONTROL1 directly", self.goal)
        self.assertNotIn("two candidate boots because", self.goal[:1])  # placeholder-safe
        self.assertIn(
            "must not be cited as two candidate boots because the candidate "
            "observer was rejected",
            self.goal,
        )
        self.assertNotIn("Stage B target are still unproved", self.goal)
        self.assertNotIn("a fresh direct D0 request remains required", self.goal)
        self.assertIn(
            "The forward frontier has moved off the connector-side Max77705 "
            "USB2 MUX discriminator to the role chain",
            self.goal,
        )
        # The MUX is demoted, not deleted; the residual-mechanism sentence stays.
        self.assertIn(
            "It preserves the MUX as a source-real but causally unproven "
            "residual mechanism",
            self.goal,
        )
        self.assertIn(
            "S22PLUS_FYG8_P319_STOCK_USERSPACE_CHOREOGRAPHY_H0_2026-08-19.md",
            self.goal,
        )
        self.assertEqual(len(self.goal.splitlines()), 900)

    def test_append_only_pending_row_is_preserved_before_review_row(self):
        pending = "h0-raw-first-observer-1"
        review = "h0-raw-first-observer-review-1"
        self.assertEqual(self.ledger.count(pending), 1)
        self.assertEqual(self.ledger.count(review), 1)
        self.assertLess(self.ledger.index(pending), self.ledger.index(review))
        row = next(line for line in self.ledger.splitlines() if pending in line)
        self.assertIn("P319_RAW_FIRST_OBSERVER_BOUNDARY_IMPLEMENTED_REVIEW_PENDING", row)
        self.assertIn(" | H0 | ", row)
        self.assertIn(" | HEALTHY | PROVED | 0/0 | ", row)
        self.assertIn("no device, ADB, USB, Odin", row)
        self.assertIn("8,729-byte private receipt is 61617e20", row)
        self.assertIn("focused tests pass 287/287", row)
        review_row = next(
            line for line in self.ledger.splitlines() if review in line
        )
        self.assertIn(
            "PASS_GO_P319_RAW_FIRST_OBSERVER_BOUNDARY_H0_CAPABILITY_V1",
            review_row,
        )
        self.assertIn("10,040-byte receipt 7f9e6f6c", review_row)
        self.assertIn("creates no D0, D1, F1", review_row)

    def test_cross_target_membership_review_row_resolves_only_current_topic(self):
        pending = "h0-raw-first-cross-target-membership-27"
        followup = "h0-raw-first-cross-target-membership-followup-27"
        review = "h0-raw-first-cross-target-membership-review-27"
        rows = self.ledger.splitlines()
        self.assertEqual(sum(f" | {pending} | " in line for line in rows), 1)
        self.assertEqual(sum(f" | {followup} | " in line for line in rows), 1)
        self.assertEqual(sum(f" | {review} | " in line for line in rows), 1)
        row = next(line for line in self.ledger.splitlines() if review in line)
        self.assertIn(
            "PASS_GO_P319_RAW_FIRST_CROSS_TARGET_MEMBERSHIP_H0_CAPABILITY_V1",
            row,
        )
        self.assertIn("6d218854492b5ac1191fac171efb12324acf743020406daba2ab75e2edbc7183", row)
        self.assertIn("d3e5013134c74837b2c36a14f5dfd8ac2ab874707dd5f30a5090002bc2a380da", row)
        self.assertIn("no device, ADB, USB, Odin", row)

    def test_population_diagnostic_pending_and_review_rows_are_append_only(self):
        topic = "h0-raw-first-population-diagnostic-28"
        rows = self.ledger.splitlines()
        self.assertEqual(sum(f" | {topic} | " in line for line in rows), 1)
        row_index = next(index for index, line in enumerate(rows) if topic in line)
        pending_row = rows[row_index]
        review_topic = "h0-raw-first-population-diagnostic-review-28"
        self.assertEqual(sum(f" | {review_topic} | " in line for line in rows), 1)
        review_index = next(index for index, line in enumerate(rows) if review_topic in line)
        prior_index = next(
            index
            for index, line in enumerate(rows)
            if " | h0-raw-first-cross-target-membership-review-27 | " in line
        )
        self.assertGreater(row_index, prior_index)
        self.assertGreater(review_index, row_index)
        self.assertTrue(pending_row.startswith("2026-08-21T16:00:00Z | "))
        self.assertIn(
            "P319_RAW_FIRST_POPULATION_PARSE_DIAGNOSTIC_IMPLEMENTED_REVIEW_PENDING",
            pending_row,
        )
        self.assertIn(" | H0 | ", pending_row)
        self.assertIn(" | HEALTHY | PROVED | 0/0 | ", pending_row)
        self.assertIn("Review-pending, not PASS_GO", pending_row)
        self.assertNotIn("PASS_GO_P319_RAW_FIRST_POPULATION_PARSE_DIAGNOSTIC", pending_row)

        row = rows[review_index]
        self.assertTrue(row.startswith("2026-08-21T16:30:00Z | "))
        self.assertIn(
            "PASS_GO_P319_RAW_FIRST_POPULATION_PARSE_DIAGNOSTIC_H0_CAPABILITY_V1",
            row,
        )
        self.assertIn(" | H0 | ", row)
        self.assertIn(" | HEALTHY | PROVED | 0/0 | ", row)
        self.assertIn("UNPARSEABLE_POPULATION_SOURCE", row)
        self.assertIn("5f7b2b07af478edb6f1416c8dba98563d305d2e1f8d531492457b3039fcdc352", row)
        self.assertIn("879705ede830fc43a27063621e402991e5fb0c6f37c1ae2f8a84a570cdc102a8", row)
        self.assertIn("6a055530d9e258dbd3d4c69ff8d546bf92efcb29c7b8e53ba3bffc2ee7fdcb0f", row)
        self.assertIn("raw auditor tests are 28579 bytes/SHA-256", row)
        self.assertIn("pass 20/20", row)
        self.assertIn("exit 3", row)
        self.assertIn("exit 2", row)
        self.assertIn("46 total / 32 resolved / 14", row)
        self.assertIn("Independent scoped H0 review", row)
        self.assertIn("not an enforcement upgrade", row)
        self.assertIn("no D0, D1, F1, LIVE, device, ADB, USB, Odin", row)


if __name__ == "__main__":
    unittest.main()

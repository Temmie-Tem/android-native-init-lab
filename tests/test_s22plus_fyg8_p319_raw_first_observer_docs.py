import hashlib
import importlib.util
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
        expected = self.auditor.encode_receipt(
            self.auditor.audit_sources(REVALIDATION)
        )
        self.assertEqual(RECEIPT.read_bytes(), expected)
        info = RECEIPT.stat()
        self.assertTrue(stat.S_ISREG(info.st_mode))
        self.assertEqual(stat.S_IMODE(info.st_mode), 0o400)
        self.assertEqual(info.st_nlink, 1)
        self.assertEqual(len(expected), 10296)
        self.assertEqual(
            hashlib.sha256(expected).hexdigest(),
            "fb3c70f19527148ebac1904e81fb686a50de075b465ed1f86a97132ddb11ef77",
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
            "NO D0/D1/F1/LIVE AUTHORITY",
            "WRITE_AFTER_PARSE_DEVICE_EVIDENCE_LOSS",
            "294/294",
            "122/122",
            "188 of 209",
            "31 exact inactive legacy observer sources",
            "initial AST subprocess-import checks",
            "fresh direct operator request",
            "Stage B target remain unproved",
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

    def test_permanent_target_boundary_has_review_triggers(self):
        for token in (
            "S22PLUS_D0_F1_RAW_FIRST_OBSERVER_PRESERVATION",
            "WRITE_AFTER_PARSE_DEVICE_EVIDENCE_LOSS",
            "has no expiry",
            "acquisition, handle ABI, parser signature, or active observer reachability",
        ):
            self.assertIn(token, self.target)
        self.assertEqual(len(self.target.splitlines()), 260)

    def test_goal_keeps_stage_a_and_stage_b_unproved(self):
        self.assertIn("permanent D0/F1 raw-first handle boundary", self.goal)
        self.assertIn("Stage B target are still unproved", self.goal)
        self.assertIn("independent H0 PASS_GO", self.goal)
        self.assertIn("a fresh direct D0 request remains required", self.goal)
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


if __name__ == "__main__":
    unittest.main()

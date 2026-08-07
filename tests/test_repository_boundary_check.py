"""Regression tests for the repository boundary check.

No real device identifier appears in this file. Layer 1 is exercised by pointing
the digest table at a synthetic value, which tests the mechanism rather than the
secret.
"""

import hashlib
import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "workspace/public/src/scripts/security/repository_boundary_check.py"

# Synthetic stand-ins with the same shape as a real identifier.
#
# Both are assembled from fragments rather than written as literals, so this
# file contains no serial-shaped token for the check to find. Adding one to the
# checker's approved list instead would weaken the list for a test-only value --
# and for UNKNOWN below it would defeat the assertion outright, since that test
# exists to prove an unapproved token is reported.
SYNTHETIC = "RZZQ" + "12345AB"
UNKNOWN = "R9XYZ" + "12345Q"


def load_module():
    spec = importlib.util.spec_from_file_location("repository_boundary_check_tested", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class RepositoryBoundaryCheckTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def setUp(self):
        self.saved = dict(self.module.KNOWN_IDENTIFIER_DIGESTS)
        self.module.KNOWN_IDENTIFIER_DIGESTS.clear()
        self.module.KNOWN_IDENTIFIER_DIGESTS[
            hashlib.sha256(SYNTHETIC.encode()).hexdigest()
        ] = "DEVICE-TEST-01"

    def tearDown(self):
        self.module.KNOWN_IDENTIFIER_DIGESTS.clear()
        self.module.KNOWN_IDENTIFIER_DIGESTS.update(self.saved)

    def test_detects_bare_identifier(self):
        self.assertEqual(
            self.module.find_known_identifiers(f"Target: {SYNTHETIC}\n"),
            {"DEVICE-TEST-01"},
        )

    def test_detects_identifier_embedded_in_udev_by_id_path(self):
        """The \\b regression.

        A word boundary treats '_' as a word character, so a check written as
        \\bR[0-9A-Z]{10}\\b silently misses this form and reports a clean tree
        while an identifier is still present. Policy section 5.4.
        """
        text = f"/dev/serial/by-id/usb-SAMSUNG_SAMSUNG_Android_{SYNTHETIC}-if00"
        self.assertEqual(
            self.module.find_known_identifiers(text), {"DEVICE-TEST-01"}
        )

    def test_detects_identifier_inside_a_longer_alphanumeric_run(self):
        self.assertEqual(
            self.module.find_known_identifiers(f"XX{SYNTHETIC}YY"),
            {"DEVICE-TEST-01"},
        )

    def test_detects_lowercased_identifier(self):
        self.assertEqual(
            self.module.find_known_identifiers(SYNTHETIC.lower()),
            {"DEVICE-TEST-01"},
        )

    def test_clean_text_reports_nothing(self):
        self.assertEqual(self.module.find_known_identifiers("nothing here\n"), set())

    def test_approved_fixtures_are_not_flagged(self):
        for value in ("RFCM0000000", "RFCT0000000"):
            with self.subTest(value=value):
                self.assertEqual(self.module.find_unknown_candidates(value), set())

    def test_aliases_and_redaction_token_are_not_flagged(self):
        text = "DEVICE-A90-01 DEVICE-S22P-01 REDACTED-DEVICE-SERIAL"
        self.assertEqual(self.module.find_unknown_candidates(text), set())
        self.assertEqual(self.module.find_known_identifiers(text), set())

    def test_all_alphabetic_near_misses_are_not_flagged(self):
        # eleven characters, leading 'R', but no digit
        text = "REASSOCIATE RECOVERABLE REINTERPRET"
        self.assertEqual(self.module.find_unknown_candidates(text), set())

    def test_unrecognised_serial_shaped_token_is_reported(self):
        self.assertEqual(
            self.module.find_unknown_candidates(f"saw {UNKNOWN} today"),
            {UNKNOWN},
        )

    def test_known_identifier_is_not_double_reported_as_unknown(self):
        self.assertEqual(self.module.find_unknown_candidates(SYNTHETIC), set())

    def test_synthetic_gadget_serials_are_not_flagged(self):
        # native init writes these to the USB descriptor; none begins with 'R'
        text = "A90NATIVE001 S22M34RUNTIME01 A90WSTA136 S22O3ACM01"
        self.assertEqual(self.module.find_unknown_candidates(text), set())


class RepositoryBoundaryCheckTreeTest(unittest.TestCase):
    """The tracked tree itself must satisfy the policy."""

    def test_tracked_tree_is_clean(self):
        module = load_module()
        known, unknown = module.check(ROOT)
        self.assertEqual(known, [], "known private identifiers present in the tracked tree")
        self.assertEqual(unknown, [], "unrecognised serial-shaped tokens in the tracked tree")


if __name__ == "__main__":
    unittest.main()

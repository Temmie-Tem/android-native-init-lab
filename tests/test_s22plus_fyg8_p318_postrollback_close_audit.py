import copy
import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(
    "workspace/public/src/scripts/revalidation/"
    "s22plus_fyg8_p318_postrollback_close_audit.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location("p318_postrollback_close_audit", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class P318PostrollbackCloseAuditTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()
        cls.receipt = cls.module.build_receipt()

    def test_closed_receipt_has_exact_terminal_and_no_authority(self):
        receipt = self.receipt
        self.assertEqual(receipt["verdict"], self.module.VERDICT)
        self.assertEqual(receipt["terminal"]["journal_state"], "CLOSED")
        self.assertEqual(receipt["terminal"]["journal_record_count"], 19)
        self.assertEqual(receipt["terminal"]["candidate_transfers"], 1)
        self.assertEqual(receipt["terminal"]["rollback_transfers"], 1)
        self.assertFalse(receipt["terminal"]["recovery_required"])
        self.assertFalse(receipt["scope"]["device_actions"])
        self.assertFalse(receipt["scope"]["device_contact"])
        self.assertFalse(receipt["scope"]["live_authority_created"])

    def test_consumed_execution_sources_are_frozen(self):
        finalizer = self.module._stable_bytes(
            self.module.FINALIZER,
            self.module.FINALIZER_SIZE,
            self.module.FINALIZER_SHA256,
            "fixture finalizer",
        )
        authority = self.module._stable_bytes(
            self.module.AUTHORITY,
            self.module.AUTHORITY_SIZE,
            self.module.AUTHORITY_SHA256,
            "fixture authority",
        )
        self.assertEqual(len(finalizer), 51413)
        self.assertEqual(len(authority), 12635)

    def test_generic_closed_validation_reproduces_the_bounded_gap(self):
        finalizer = self.module._load_finalizer()
        authority = finalizer.load_authority(self.module.AUTHORITY)
        with self.assertRaisesRegex(
            (finalizer.FinalizeError, finalizer.live.F1LiveError),
            "candidate correlation lacks one clean record",
        ):
            finalizer.verify_incident(authority)

    def test_terminal_mutations_fail_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            run = Path(temporary)
            prepared = mock.Mock(binding_sha256="a" * 64, run_dir=run)
            journal = mock.Mock()
            journal.state.return_value = "CLOSED"
            journal.records.return_value = [{} for _ in range(19)]
            result = {
                "schema": "device_action_f1_live_result_v2",
                "verdict": "NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK",
                "outcome_class": "candidate_not_proven_rollback_verified",
                "recovery_required": False,
                "current_state": "CLOSED",
                "approval_binding_sha256": "a" * 64,
                "live_state": {
                    "candidate_completed": True,
                    "rollback_completed": True,
                    "final_verified": True,
                    "candidate_observer_accepted": False,
                    "candidate_observer_classification": "endpoint-timeout",
                },
            }
            self.module._validate_terminal(result, journal, prepared)
            for key, value in (
                ("verdict", "PASS"),
                ("outcome_class", "candidate_proven"),
                ("recovery_required", True),
                ("current_state", "HEALTH_VERIFIED"),
            ):
                with self.subTest(key=key):
                    mutated = copy.deepcopy(result)
                    mutated[key] = value
                    with self.assertRaises(self.module.AuditError):
                        self.module._validate_terminal(mutated, journal, prepared)

    def test_preserved_receipt_is_exact_regeneration(self):
        if not self.module.OUTPUT.exists():
            self.skipTest("private close-audit receipt has not been published yet")
        payload = self.module.encode_receipt(self.receipt)
        self.assertEqual(
            self.module._stable_bytes(
                self.module.OUTPUT,
                len(payload),
                self.module._sha256(payload),
                "preserved close-audit receipt",
                required_mode=0o400,
            ),
            payload,
        )

    def test_existing_receipt_with_widened_mode_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "receipt.json"
            target.write_bytes(self.module.encode_receipt(self.receipt))
            os.chmod(target, 0o600)
            with mock.patch.object(self.module, "OUTPUT", target):
                with self.assertRaisesRegex(
                    self.module.AuditError, "close-audit receipt identity differs"
                ):
                    self.module.write_receipt()
            self.assertEqual(target.stat().st_mode & 0o777, 0o600)

    def test_auditor_has_no_device_command_surface(self):
        source = SCRIPT.read_text(encoding="utf-8")
        for forbidden in (
            "import subprocess",
            "os.system(",
            "Popen(",
            "check_output(",
            "--adb",
            "--approval",
            "--finalize",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()

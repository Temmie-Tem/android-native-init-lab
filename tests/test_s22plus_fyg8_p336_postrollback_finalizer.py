from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / (
    "workspace/public/src/scripts/revalidation/"
    "s22plus_fyg8_p336_postrollback_finalizer.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location("p336_postrollback_tested", SOURCE)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class P336PostrollbackFinalizerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def test_scope_has_no_device_or_transfer_backend(self):
        source = SOURCE.read_text(encoding="utf-8")
        for forbidden in (
            "SamsungOdinBackend(",
            "AdbReadOnlyClient(",
            "adb_client_for_bundle(",
            "execute_prepared(",
            "recover_prepared(",
            "subprocess.run(",
            "subprocess.Popen(",
            ".transfer(",
            ".wait_download(",
            "usb_snapshot(",
        ):
            self.assertNotIn(forbidden, source)

    def test_audit_reconstructs_exact_rollback_cut_without_writes(self):
        before_state = self.module._stable(
            self.module.STATE_PATH, "state", 128 * 1024
        )
        before_head = self.module._stable(
            self.module.TRANSACTION / "journal-head.json", "head"
        )
        value = self.module.finalize(audit_only=True)
        self.assertEqual(value["verdict"], self.module.AUDIT_VERDICT)
        self.assertEqual(value["candidate_transfer_count"], 1)
        self.assertEqual(value["rollback_transfer_count"], 1)
        self.assertEqual(value["stock_proof_class"], "NO_PROOF_OBSERVER")
        self.assertTrue(value["rollback_verified_from_retained_evidence"])
        for key in (
            "created",
            "device_contact",
            "adb_invoked",
            "usb_revalidated",
            "odin_invoked",
            "candidate_transfer",
            "rollback_transfer",
            "live_authorized",
        ):
            self.assertFalse(value[key])
        self.assertEqual(
            before_state,
            self.module._stable(self.module.STATE_PATH, "state", 128 * 1024),
        )
        self.assertEqual(
            before_head,
            self.module._stable(
                self.module.TRANSACTION / "journal-head.json", "head"
            ),
        )

    def test_fixed_run_and_no_second_attempt(self):
        self.assertEqual(
            self.module.RUN_DIR.name, "p336-ready1-prepared-20260904-2"
        )
        self.assertFalse(any(self.module.RUN_DIR.glob("candidate-attempt-02.*")))
        self.assertFalse(any(self.module.RUN_DIR.glob("rollback-attempt-02.*")))


if __name__ == "__main__":
    unittest.main()

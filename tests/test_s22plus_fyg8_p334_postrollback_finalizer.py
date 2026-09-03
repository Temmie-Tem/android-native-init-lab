from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / (
    "workspace/public/src/scripts/revalidation/"
    "s22plus_fyg8_p334_postrollback_finalizer.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location("p334_postrollback_tested", SOURCE)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class P334PostrollbackFinalizerTests(unittest.TestCase):
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
        ):
            self.assertNotIn(forbidden, source)

    def test_audit_reopens_exact_success_and_postrollback_cut(self):
        before_state = self.module._stable(
            self.module.STATE_PATH, "state", 64 * 1024
        )
        before_head = self.module._stable(
            self.module.RUN_DIR / "transaction/journal-head.json", "head"
        )
        value = self.module.finalize(audit_only=True)
        self.assertEqual(value["verdict"], self.module.AUDIT_VERDICT)
        self.assertEqual(value["journal_state"], "CLOSED")
        self.assertTrue(value["result_present"])
        self.assertTrue(value["candidate_observation_proved"])
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
            self.module._stable(self.module.STATE_PATH, "state", 64 * 1024),
        )
        self.assertEqual(
            before_head,
            self.module._stable(
                self.module.RUN_DIR / "transaction/journal-head.json", "head"
            ),
        )

    def test_closed_cut_and_result_are_exact(self):
        self.assertEqual(self.module.EXPECTED_CLOSED_STATE[0], 13_105)
        self.assertEqual(self.module.EXPECTED_CLOSED_HEAD[0], 276)
        payload = self.module._stable(
            self.module.RESULT_PATH, "result", 64 * 1024
        )
        self.assertEqual(
            (len(payload), self.module._sha256(payload)),
            self.module.EXPECTED_RESULT,
        )


if __name__ == "__main__":
    unittest.main()

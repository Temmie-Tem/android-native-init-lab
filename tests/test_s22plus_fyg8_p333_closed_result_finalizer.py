from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import stat
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / (
    "workspace/public/src/scripts/revalidation/"
    "s22plus_fyg8_p333_closed_result_finalizer.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location("p333_closed_finalizer_tested", SOURCE)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class P333ClosedResultFinalizerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def test_scope_is_one_closed_run_and_no_device_backend(self):
        module = self.module
        self.assertEqual(module.CORE_MAX_RECORD, 32 * 1024)
        self.assertEqual(module.MAX_FINAL_RECORD, 64 * 1024)
        self.assertEqual(module.EXPECTED_PRE_STATE[0], 31_285)
        self.assertEqual(module.EXPECTED_FINAL_STATE[0], 32_855)
        self.assertEqual(module.EXPECTED_RESULT[0], 36_652)
        source = SOURCE.read_text(encoding="utf-8")
        for forbidden in (
            "SamsungOdinBackend(",
            "execute_prepared(",
            "recover_prepared(",
            "subprocess.run(",
            "subprocess.Popen(",
            "adb_client_for_bundle(",
            "revalidate=True",
        ):
            self.assertNotIn(forbidden, source)

    def test_state_phase_accepts_only_exact_pre_or_final(self):
        module = self.module
        pre = b"pre"
        final = b"final"
        with (
            mock.patch.object(module, "EXPECTED_PRE_STATE", (len(pre), module._sha256(pre))),
            mock.patch.object(
                module, "EXPECTED_FINAL_STATE", (len(final), module._sha256(final))
            ),
        ):
            self.assertEqual(module._state_phase(pre), "pre")
            self.assertEqual(module._state_phase(final), "final")
            with self.assertRaises(module.FinalizerError):
                module._state_phase(b"foreign")

    def test_result_is_mode0400_single_link_and_no_clobber(self):
        module = self.module
        value = {"closed": True}
        payload = json.dumps(value, indent=2, sort_keys=True).encode() + b"\n"
        with tempfile.TemporaryDirectory() as name:
            path = Path(name) / "live-result.json"

            class Core:
                MAX_RESULT_RECORD = module.MAX_FINAL_RECORD

                @staticmethod
                def _write_exclusive_bounded(target, written, limit):
                    self.assertEqual(limit, module.MAX_FINAL_RECORD)
                    target.write_bytes(
                        json.dumps(written, indent=2, sort_keys=True).encode() + b"\n"
                    )
                    target.chmod(0o400)

            with (
                mock.patch.object(module, "RESULT_PATH", path),
                mock.patch.object(module, "EXPECTED_RESULT", (len(payload), module._sha256(payload))),
            ):
                self.assertTrue(module._publish_result(Core(), value, payload))
                self.assertFalse(module._publish_result(Core(), value, payload))
            self.assertEqual(path.read_bytes(), payload)
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o400)
            self.assertEqual(path.stat().st_nlink, 1)

    def test_audit_reconstructs_exact_closed_run_without_device_effect(self):
        module = self.module
        result = module.finalize(audit_only=True)
        self.assertEqual(result["verdict"], module.AUDIT_VERDICT)
        self.assertEqual(result["state"]["sha256"], module.EXPECTED_FINAL_STATE[1])
        self.assertEqual(result["result"]["sha256"], module.EXPECTED_RESULT[1])
        self.assertTrue(result["console_entry_diagnostic_proved"])
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
            self.assertFalse(result[key])


if __name__ == "__main__":
    unittest.main()

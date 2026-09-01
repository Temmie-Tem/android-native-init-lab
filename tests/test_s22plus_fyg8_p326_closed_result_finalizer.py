from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / (
    "workspace/public/src/scripts/revalidation/"
    "s22plus_fyg8_p326_closed_result_finalizer.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location("p326_closed_finalizer_tested", SOURCE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class P326ClosedResultFinalizerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def test_surface_is_exact_run_and_host_only(self):
        module = self.module
        self.assertEqual(module.EXPECTED_STATE_SIZE, 30_189)
        self.assertEqual(module.EXPECTED_RESULT_SIZE, 33_879)
        self.assertEqual(module.CORE_MAX_RECORD, 32 * 1024)
        self.assertEqual(module.MAX_FINAL_RECORD, 64 * 1024)
        source = SOURCE.read_text(encoding="utf-8")
        for forbidden in (
            "SamsungOdinBackend(",
            "subprocess.run(",
            "subprocess.Popen(",
            "adb_client_for_bundle(",
            "recover_prepared(",
            "execute_prepared(",
            "revalidate=True",
        ):
            self.assertNotIn(forbidden, source)

    def test_exact_closed_run_reconstructs_bidirectional_result(self):
        module = self.module
        value, payload, _live, _prepared, _state = module.reconstruct()
        self.assertEqual(value["current_state"], "CLOSED")
        self.assertEqual(value["verdict"], module.EXPECTED_RESULT_VERDICT)
        self.assertEqual(value["outcome_class"], module.EXPECTED_OUTCOME)
        proof = value["live_state"]["candidate_arrival_proof"]
        self.assertTrue(proof["proof"])
        self.assertTrue(proof["pid1_bidirectional_proof"])
        self.assertTrue(proof["busybox_shell_roundtrip_proof"])
        self.assertEqual(proof["banner_size"], 145)
        self.assertEqual(len(payload), module.EXPECTED_RESULT_SIZE)
        self.assertEqual(module._sha256(payload), module.EXPECTED_RESULT_SHA256)

    def test_publication_is_mode0400_single_link_and_no_clobber(self):
        module = self.module
        payload = b'{"closed":true}\n'
        with tempfile.TemporaryDirectory() as name:
            result = Path(name) / "live-result.json"
            with (
                mock.patch.object(module, "RESULT_PATH", result),
                mock.patch.object(module, "EXPECTED_RESULT_SIZE", len(payload)),
                mock.patch.object(
                    module, "EXPECTED_RESULT_SHA256", module._sha256(payload)
                ),
            ):
                module._publish(payload)
                info = result.lstat()
                self.assertEqual(result.read_bytes(), payload)
                self.assertEqual(stat.S_IMODE(info.st_mode), 0o400)
                self.assertEqual(info.st_nlink, 1)
                with self.assertRaises(module.FinalizerError):
                    module._publish(payload)

    def test_arbitrary_or_oversized_result_is_rejected(self):
        module = self.module
        with tempfile.TemporaryDirectory() as name:
            result = Path(name) / "live-result.json"
            with mock.patch.object(module, "RESULT_PATH", result):
                with self.assertRaises(module.FinalizerError):
                    module._publish(b'{"arbitrary":true}\n')
                with self.assertRaises(module.FinalizerError):
                    module._publish(b"x" * (module.MAX_FINAL_RECORD + 1))
                self.assertFalse(result.exists())

    def test_read_only_journal_never_calls_reopen(self):
        module = self.module

        class Journal:
            reopen = mock.Mock(side_effect=AssertionError("must not reopen"))

            def __init__(self, path, binding):
                self.path = path
                self.binding = binding

            def records(self):
                return [{"state": "CLOSED"}]

        core = mock.Mock(Journal=Journal)
        journal = module._read_only_journal(core, Path("/run/transaction"), "a" * 64)
        self.assertEqual(journal.binding, "a" * 64)
        Journal.reopen.assert_not_called()

    def test_audit_flags_are_zero_effect(self):
        module = self.module
        value = {
            "verdict": module.EXPECTED_RESULT_VERDICT,
            "outcome_class": module.EXPECTED_OUTCOME,
            "current_state": "CLOSED",
            "recovery_required": False,
        }
        payload = json.dumps(value, indent=2, sort_keys=True).encode() + b"\n"
        with (
            mock.patch.object(
                module,
                "reconstruct",
                return_value=(value, payload, mock.Mock(), object(), {}),
            ),
            mock.patch.object(
                module,
                "RESULT_PATH",
                Path(f"/definitely/absent/{os.getpid()}-p326-live-result.json"),
            ),
        ):
            result = module.finalize(audit_only=True)
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

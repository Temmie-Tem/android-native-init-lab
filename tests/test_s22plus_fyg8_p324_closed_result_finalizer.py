import importlib.util
import json
import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / (
    "workspace/public/src/scripts/revalidation/"
    "s22plus_fyg8_p324_closed_result_finalizer.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location("p324_closed_finalizer_tested", SOURCE)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class P324ClosedResultFinalizerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def test_surface_is_exact_run_host_only(self):
        module = self.module
        self.assertEqual(
            module.EXPECTED_BINDING,
            "bb75a3ce58043f3538b69acabfd5ee05cdc4e75f8acd2cb0e3f12e8b52abeb36",
        )
        self.assertEqual(module.EXPECTED_PRE_STATE_SIZE, 29_102)
        self.assertEqual(module.EXPECTED_FINAL_STATE_SIZE, 34_672)
        self.assertEqual(module.EXPECTED_RESULT_SIZE, 38_558)
        self.assertEqual(module.MAX_FINAL_RECORD, 64 * 1024)
        self.assertEqual(module.CORE_MAX_RECORD, 32 * 1024)
        self.assertEqual(module.STATE_PATH, module.RUN_DIR / "live-state.json")
        self.assertEqual(module.RESULT_PATH, module.RUN_DIR / "live-result.json")
        source = SOURCE.read_text()
        self.assertNotIn("SamsungOdinBackend(", source)
        self.assertNotIn("subprocess.run(", source)
        self.assertNotIn("subprocess.Popen(", source)
        self.assertNotIn("adb_client_for_bundle(", source)
        self.assertNotIn("recover_prepared(", source)
        self.assertNotIn("execute_prepared(", source)
        self.assertNotIn("revalidate=True", source)

    def test_state_phase_accepts_only_two_exact_identities(self):
        module = self.module
        pre = b"pre"
        final = b"final"
        with (
            mock.patch.object(module, "EXPECTED_PRE_STATE_SIZE", len(pre)),
            mock.patch.object(module, "EXPECTED_PRE_STATE_SHA256", module._sha256(pre)),
            mock.patch.object(module, "EXPECTED_FINAL_STATE_SIZE", len(final)),
            mock.patch.object(module, "EXPECTED_FINAL_STATE_SHA256", module._sha256(final)),
        ):
            self.assertEqual(module._state_phase(pre), "pre")
            self.assertEqual(module._state_phase(final), "final")
            with self.assertRaises(module.FinalizerError):
                module._state_phase(b"foreign")

    def test_publish_is_mode0400_single_link_and_no_clobber(self):
        module = self.module
        payload = b'{"closed":true}\n'
        with tempfile.TemporaryDirectory() as name:
            result = Path(name) / "live-result.json"
            with (
                mock.patch.object(module, "RESULT_PATH", result),
                mock.patch.object(module, "EXPECTED_RESULT_SIZE", len(payload)),
                mock.patch.object(module, "EXPECTED_RESULT_SHA256", module._sha256(payload)),
            ):
                module._publish_exact(payload)
                self.assertEqual(result.read_bytes(), payload)
                metadata = result.lstat()
                self.assertTrue(stat.S_ISREG(metadata.st_mode))
                self.assertEqual(stat.S_IMODE(metadata.st_mode), 0o400)
                self.assertEqual(metadata.st_nlink, 1)
                with self.assertRaises(module.FinalizerError):
                    module._publish_exact(payload)

    def test_oversized_and_arbitrary_payloads_are_rejected(self):
        module = self.module
        with tempfile.TemporaryDirectory() as name:
            result = Path(name) / "live-result.json"
            with mock.patch.object(module, "RESULT_PATH", result):
                with self.assertRaises(module.FinalizerError):
                    module._publish_exact(b"x" * (module.MAX_FINAL_RECORD + 1))
                with self.assertRaises(module.FinalizerError):
                    module._publish_exact(b'{"arbitrary":true}\n')
                self.assertFalse(result.exists())

    def test_exact_two_link_publication_cut_is_repaired(self):
        module = self.module
        with tempfile.TemporaryDirectory() as name:
            parent = Path(name)
            result = parent / "live-result.json"
            temporary = parent / f".{result.name}.{os.getpid()}.123.tmp"
            temporary.write_bytes(b"complete")
            temporary.chmod(0o400)
            os.link(temporary, result)
            module._repair_publication_cut(result)
            self.assertFalse(temporary.exists())
            self.assertEqual(result.read_bytes(), b"complete")
            self.assertEqual(result.stat().st_nlink, 1)

    def test_stored_lane_loader_never_revalidates_usb(self):
        module = self.module
        prepared = object()
        original = mock.Mock(return_value=("lane", "receipt"))
        live = mock.Mock()
        live._p324_typec_lane_value = original
        live.load_prepared.side_effect = lambda *_args: live._p324_typec_lane_value(
            prepared, revalidate=True
        )
        self.assertEqual(
            module._load_prepared_stored_lane(live), ("lane", "receipt")
        )
        original.assert_called_once_with(prepared, revalidate=False)
        self.assertIs(live._p324_typec_lane_value, original)

    def test_final_state_uses_temporary_dedicated_bound(self):
        module = self.module
        pre = b"pre"
        final = b"final"
        state = {"candidate_arrival_proof": {"proof": False}}
        with tempfile.TemporaryDirectory() as name:
            path = Path(name) / "live-state.json"
            path.write_bytes(pre)
            path.chmod(0o400)
            core = mock.Mock(MAX_RECORD=module.CORE_MAX_RECORD)
            live = mock.Mock(core=core)

            def save(_prepared, value):
                self.assertEqual(core.MAX_RECORD, module.MAX_FINAL_RECORD)
                self.assertEqual(value, state)
                path.unlink()
                path.write_bytes(final)
                path.chmod(0o400)

            live._save_state.side_effect = save
            with (
                mock.patch.object(module, "STATE_PATH", path),
                mock.patch.object(module, "EXPECTED_PRE_STATE_SIZE", len(pre)),
                mock.patch.object(module, "EXPECTED_PRE_STATE_SHA256", module._sha256(pre)),
                mock.patch.object(module, "EXPECTED_FINAL_STATE_SIZE", len(final)),
                mock.patch.object(module, "EXPECTED_FINAL_STATE_SHA256", module._sha256(final)),
            ):
                module._publish_final_state(live, object(), state, final)
            self.assertEqual(core.MAX_RECORD, module.CORE_MAX_RECORD)
            self.assertEqual(path.read_bytes(), final)

    def test_finalize_flags_are_zero_effect(self):
        module = self.module
        value = {
            "verdict": module.EXPECTED_RESULT_VERDICT,
            "outcome_class": module.EXPECTED_OUTCOME,
            "current_state": "CLOSED",
            "recovery_required": False,
        }
        payload = json.dumps(value, indent=2, sort_keys=True).encode() + b"\n"
        state = {"candidate_arrival_proof": {"proof": False}}
        state_payload = json.dumps(state, indent=2, sort_keys=True).encode() + b"\n"
        prepared = object()
        live = mock.Mock()
        with (
            mock.patch.object(
                module,
                "reconstruct",
                return_value=(value, payload, state, state_payload, "pre", prepared, live),
            ),
            mock.patch.object(module, "RESULT_PATH", Path("/definitely/absent/p324-live-result.json")),
        ):
            result = module.finalize(audit_only=True)
        self.assertFalse(result["created"])
        self.assertFalse(result["device_contact"])
        self.assertFalse(result["adb_invoked"])
        self.assertFalse(result["usb_revalidated"])
        self.assertFalse(result["odin_invoked"])
        self.assertFalse(result["candidate_transfer"])
        self.assertFalse(result["rollback_transfer"])
        self.assertFalse(result["live_authorized"])


if __name__ == "__main__":
    unittest.main()

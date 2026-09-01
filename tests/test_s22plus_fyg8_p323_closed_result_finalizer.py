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
    "s22plus_fyg8_p323_closed_result_finalizer.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location("p323_closed_finalizer_tested", SOURCE)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class P323ClosedResultFinalizerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def test_surface_is_exact_run_host_only(self):
        module = self.module
        self.assertEqual(module.EXPECTED_BINDING, "da580d2c6980c8ab8fd87dc799c31ab65e9f0bb084513fe294b8f3ca7c5dbd7c")
        self.assertEqual(module.EXPECTED_RESULT_SIZE, 34_937)
        self.assertEqual(module.MAX_RESULT, 64 * 1024)
        self.assertEqual(module.CORE_MAX_RECORD, 32 * 1024)
        self.assertEqual(module.RESULT_PATH, module.RUN_DIR / "live-result.json")
        source = SOURCE.read_text()
        self.assertNotIn("SamsungOdinBackend(", source)
        self.assertNotIn("subprocess.run(", source)
        self.assertNotIn("subprocess.Popen(", source)
        self.assertNotIn("adb_client_for_bundle(", source)
        self.assertNotIn("recover_prepared(", source)
        self.assertNotIn("execute_prepared(", source)

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

    def test_oversized_payload_is_rejected_before_publication(self):
        module = self.module
        with tempfile.TemporaryDirectory() as name:
            result = Path(name) / "live-result.json"
            with mock.patch.object(module, "RESULT_PATH", result):
                with self.assertRaises(module.FinalizerError):
                    module._publish_exact(b"x" * (module.MAX_RESULT + 1))
                self.assertFalse(result.exists())

    def test_arbitrary_in_bound_payload_is_rejected_by_publisher(self):
        module = self.module
        with tempfile.TemporaryDirectory() as name:
            result = Path(name) / "live-result.json"
            with mock.patch.object(module, "RESULT_PATH", result):
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
            self.assertEqual(result.stat().st_nlink, 2)
            module._repair_publication_cut(result)
            self.assertFalse(temporary.exists())
            self.assertEqual(result.read_bytes(), b"complete")
            self.assertEqual(result.stat().st_nlink, 1)

    def test_mode0644_result_and_publication_cut_are_rejected(self):
        module = self.module
        with tempfile.TemporaryDirectory() as name:
            parent = Path(name)
            result = parent / "live-result.json"
            result.write_bytes(b"complete")
            result.chmod(0o644)
            with self.assertRaises(module.FinalizerError):
                module._repair_publication_cut(result)
        with tempfile.TemporaryDirectory() as name:
            parent = Path(name)
            result = parent / "live-result.json"
            temporary = parent / f".{result.name}.{os.getpid()}.456.tmp"
            temporary.write_bytes(b"complete")
            temporary.chmod(0o644)
            os.link(temporary, result)
            with self.assertRaises(module.FinalizerError):
                module._repair_publication_cut(result)

    def test_finalize_flags_are_zero_effect(self):
        module = self.module
        value = {"verdict": module.EXPECTED_RESULT_VERDICT, "outcome_class": module.EXPECTED_OUTCOME, "current_state": "CLOSED", "recovery_required": False}
        payload = json.dumps(value, indent=2, sort_keys=True).encode() + b"\n"
        prepared = object()
        live = mock.Mock()
        with (
            mock.patch.object(module, "reconstruct", return_value=(value, payload, prepared, live)),
            mock.patch.object(module, "RESULT_PATH", Path("/definitely/absent/p323-live-result.json")),
        ):
            result = module.finalize(audit_only=True)
        self.assertFalse(result["created"])
        self.assertFalse(result["device_contact"])
        self.assertFalse(result["adb_invoked"])
        self.assertFalse(result["odin_invoked"])
        self.assertFalse(result["candidate_transfer"])
        self.assertFalse(result["rollback_transfer"])
        self.assertFalse(result["live_authorized"])


if __name__ == "__main__":
    unittest.main()

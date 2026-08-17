import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / (
    "workspace/public/src/scripts/revalidation/device_action_raw_capture_v1.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "device_action_raw_capture_v1_tested", SCRIPT
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class DeviceActionRawCaptureV1Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def test_command_publishes_mode0400_streams_before_handle_parse(self):
        module = self.module
        with tempfile.TemporaryDirectory() as temporary:
            capture = module.prepare_capture_dir(Path(temporary))
            handle = module.acquire_command(
                ["/bin/sh", "-c", "printf observer"],
                capture,
                "success",
                timeout=2,
                stdout_maximum=64,
                stderr_maximum=64,
            )
            self.assertEqual(
                module.decode_success_stdout(handle, maximum=64), "observer"
            )
            for path in (
                handle.stdout_path,
                handle.stderr_path,
                handle.receipt_path,
            ):
                info = path.lstat()
                self.assertTrue(stat.S_ISREG(info.st_mode))
                self.assertEqual(stat.S_IMODE(info.st_mode), 0o400)
                self.assertEqual(info.st_nlink, 1)

    def test_parser_failure_cannot_remove_already_published_raw(self):
        module = self.module
        with tempfile.TemporaryDirectory() as temporary:
            capture = module.prepare_capture_dir(Path(temporary))
            handle = module.publish_captured_bytes(
                capture, "malformed", stdout=b"not-json"
            )
            with self.assertRaises(json.JSONDecodeError):
                json.loads(module.read_stdout(handle, maximum=64))
            self.assertEqual(handle.stdout_path.read_bytes(), b"not-json")
            self.assertEqual(module.load_handle(handle.receipt_path), handle)

    def test_timeout_and_output_limit_preserve_bounded_partial_raw(self):
        module = self.module
        with tempfile.TemporaryDirectory() as temporary:
            capture = module.prepare_capture_dir(Path(temporary))
            timed = module.acquire_command(
                ["/bin/sh", "-c", "printf before; sleep 2"],
                capture,
                "timeout",
                timeout=0.1,
                stdout_maximum=64,
                stderr_maximum=64,
            )
            self.assertTrue(timed.timed_out)
            self.assertEqual(module.read_stdout(timed, maximum=64), b"before")
            with self.assertRaises(module.RawCaptureError):
                module.require_success(timed)

            limited = module.acquire_command(
                ["/bin/sh", "-c", "printf 123456789"],
                capture,
                "limited",
                timeout=2,
                stdout_maximum=4,
                stderr_maximum=4,
            )
            self.assertTrue(limited.output_exceeded)
            self.assertEqual(module.read_stdout(limited, maximum=4), b"1234")

    def test_no_clobber_and_metadata_tamper_fail_closed(self):
        module = self.module
        with tempfile.TemporaryDirectory() as temporary:
            capture = module.prepare_capture_dir(Path(temporary))
            handle = module.publish_captured_bytes(
                capture, "sealed", stdout=b"first"
            )
            with self.assertRaises(module.RawCaptureError):
                module.publish_captured_bytes(
                    capture, "sealed", stdout=b"second"
                )
            self.assertEqual(handle.stdout_path.read_bytes(), b"first")
            handle.stdout_path.chmod(0o600)
            with self.assertRaises(module.RawCaptureError):
                module.load_handle(handle.receipt_path)

    def test_duplicate_bool_integer_nan_and_nonhandle_inputs_reject(self):
        module = self.module
        with tempfile.TemporaryDirectory() as temporary:
            capture = module.prepare_capture_dir(Path(temporary))
            mutations = (
                ('"timed_out":false', '"timed_out":false,"timed_out":false'),
                ('"timed_out":false', '"timed_out":0'),
                ('"returncode":0', '"returncode":true'),
                ('elapsed', 'elapsed'),
            )
            for index, (old, new) in enumerate(mutations):
                with self.subTest(index=index):
                    handle = module.publish_captured_bytes(
                        capture, f"strict-{index}", stdout=b"x"
                    )
                    original = handle.receipt_path.read_text(encoding="ascii")
                    if old == "elapsed":
                        mutated = re.sub(
                            r'"elapsed_msec":[0-9]+',
                            '"elapsed_msec":NaN',
                            original,
                            count=1,
                        )
                    else:
                        self.assertIn(old, original)
                        mutated = original.replace(old, new)
                    self.assertNotEqual(mutated, original)
                    handle.receipt_path.chmod(0o600)
                    handle.receipt_path.write_text(
                        mutated, encoding="ascii"
                    )
                    handle.receipt_path.chmod(0o400)
                    with self.assertRaises(module.RawCaptureError):
                        module.load_handle(handle.receipt_path)
            with self.assertRaises(module.RawCaptureError):
                module.read_stdout(b"x", maximum=1)

    def test_invocation_and_writer_types_are_strict(self):
        module = self.module
        with tempfile.TemporaryDirectory() as temporary:
            capture = module.prepare_capture_dir(Path(temporary))
            with self.assertRaises(module.RawCaptureError):
                module.acquire_command(
                    "/bin/true",
                    capture,
                    "argv-string",
                    timeout=1,
                    stdout_maximum=1,
                    stderr_maximum=1,
                )
            with self.assertRaises(module.RawCaptureError):
                module.RawCaptureWriter(
                    capture,
                    "bool-bound",
                    stdout_maximum=True,
                    stderr_maximum=1,
                )

    def test_hostile_umask_cannot_remove_mode0400_owner_readability(self):
        module = self.module
        with tempfile.TemporaryDirectory() as temporary:
            capture = module.prepare_capture_dir(Path(temporary))
            previous = os.umask(0o777)
            try:
                handle = module.publish_captured_bytes(
                    capture, "hostile-umask", stdout=b"retained"
                )
            finally:
                os.umask(previous)
            for path in (
                handle.stdout_path,
                handle.stderr_path,
                handle.receipt_path,
            ):
                self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o400)
            self.assertEqual(module.read_stdout(handle, maximum=8), b"retained")

    def test_interruption_is_reraised_only_after_partial_raw_is_published(self):
        module = self.module
        with tempfile.TemporaryDirectory() as temporary:
            capture = module.prepare_capture_dir(Path(temporary))
            real_factory = module.selectors.DefaultSelector
            selector = mock.Mock(wraps=real_factory())
            selector.select = mock.Mock(side_effect=KeyboardInterrupt)
            with mock.patch.object(
                module.selectors, "DefaultSelector", return_value=selector
            ), self.assertRaises(KeyboardInterrupt):
                module.acquire_command(
                    ["/bin/sh", "-c", "printf before; sleep 1"],
                    capture,
                    "interrupted",
                    timeout=2,
                    stdout_maximum=64,
                    stderr_maximum=64,
                )
            handle = module.load_handle(capture / "interrupted.capture.json")
            self.assertEqual(handle.producer_error_type, "KeyboardInterrupt")


if __name__ == "__main__":
    unittest.main()

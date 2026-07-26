import contextlib
import importlib.util
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    ROOT
    / "workspace/public/src/scripts/revalidation/"
    "device_action_usb_trace_sidecar_v1.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "device_action_usb_trace_sidecar_v1_tested", SCRIPT
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class UsbTraceSidecarV1Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def fixture(self):
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name)
        private = root / "workspace/private"
        parent = private / "outputs/run"
        parent.mkdir(parents=True)
        return temporary, private, parent

    def commands(self):
        python = sys.executable
        return {
            "kernel": (
                python,
                "-c",
                "print('usb connect synthetic-serial')",
            ),
            "udev": (
                python,
                "-c",
                "print('ACTION=add\\nSUBSYSTEM=tty\\nID_SERIAL=private')",
            ),
        }

    def test_bounded_capture_is_private_non_authoritative_and_durable(self):
        temporary, private, parent = self.fixture()
        self.addCleanup(temporary.cleanup)
        destination = parent / "host-usb-trace"
        result = self.module.capture(
            destination,
            duration_sec=0.2,
            private_root=private,
            source_commands=self.commands(),
            snapshot_command=(sys.executable, "-c", "print('snapshot')"),
            install_signal_handlers=False,
        )
        self.assertEqual(result["stop_reason"], "duration-expired")
        self.assertTrue(result["non_authoritative"])
        self.assertFalse(result["device_actions"])
        self.assertFalse(result["opens_candidate_acm"])
        self.assertTrue(result["contains_private_usb_identifiers"])
        self.assertTrue(result["public_raw_export_forbidden"])
        self.assertEqual(set(result["sources"]), {"kernel", "udev"})
        self.assertTrue((destination / "kernel.log").read_bytes())
        self.assertTrue((destination / "udev.log").read_bytes())
        self.assertEqual(
            json.loads((destination / "result.json").read_text())["schema"],
            self.module.SCHEMA,
        )
        self.assertEqual(
            set(result["supporting"]),
            {"start", "lsusb_start", "lsusb_end"},
        )
        self.assertIn(
            "snapshot",
            json.loads(
                (destination / "lsusb-start.json").read_text()
            )["stdout_text"],
        )
        self.assertEqual(
            stat_mode(destination / "result.json"),
            0o600,
        )

    def test_existing_or_outside_output_is_rejected(self):
        temporary, private, parent = self.fixture()
        self.addCleanup(temporary.cleanup)
        existing = parent / "existing"
        existing.mkdir()
        with self.assertRaises(self.module.SidecarError):
            self.module.create_output_dir(existing, private)
        outside = Path(temporary.name) / "outside/capture"
        outside.parent.mkdir()
        with self.assertRaises(self.module.SidecarError):
            self.module.create_output_dir(outside, private)

    def test_snapshot_failure_is_diagnostic_only(self):
        value = self.module.bounded_snapshot(("/definitely/missing/lsusb",))
        self.assertFalse(value["available"])
        self.assertEqual(value["error_type"], "FileNotFoundError")

    def test_source_command_does_not_open_acm_or_poll_lsusb(self):
        flattened = "\n".join(
            argument
            for command in self.module.SOURCE_COMMANDS.values()
            for argument in command
        )
        self.assertNotIn("ttyACM", flattened)
        self.assertNotIn("lsusb", flattened)
        self.assertIn("--subsystem-match=usb", flattened)
        self.assertIn("--subsystem-match=tty", flattened)

    def test_cli_duration_is_bounded(self):
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                self.module.parse_args(
                    ["--output-dir", "/tmp/x", "--duration-sec", "59"]
                )
            with self.assertRaises(SystemExit):
                self.module.parse_args(
                    [
                        "--output-dir",
                        "/tmp/x",
                        "--duration-sec",
                        str(self.module.MAX_DURATION_SEC + 1),
                    ]
                )


def stat_mode(path: Path) -> int:
    return os.stat(path).st_mode & 0o777


if __name__ == "__main__":
    unittest.main()

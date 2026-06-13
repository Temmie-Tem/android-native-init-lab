from __future__ import annotations

import contextlib
import io
import json
import stat
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from _loader import load_revalidation


usb_recovery = load_revalidation("usb_recovery_validate.py")


def args_for(tmp: str, **overrides):
    values = {
        "host": "127.0.0.1",
        "port": 54321,
        "timeout": 12.0,
        "recovery_timeout": 1.0,
        "poll_interval": 0.0,
        "cycles": 2,
        "usbnet_helper": "/cache/bin/a90_usbnet",
        "run_id": "run-01",
        "out_dir": tmp,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


class EvidenceHelpers(unittest.TestCase):
    def test_private_writer_enforces_modes_and_rejects_symlink_targets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "bundle" / "out.txt"
            usb_recovery.write_private_text(target, "ok\n")

            self.assertEqual(target.read_text(encoding="utf-8"), "ok\n")
            self.assertEqual(stat.S_IMODE(target.parent.stat().st_mode), usb_recovery.PRIVATE_DIR_MODE)
            self.assertEqual(stat.S_IMODE(target.stat().st_mode), usb_recovery.PRIVATE_FILE_MODE)

            linked = root / "linked.txt"
            linked.symlink_to(target)
            with self.assertRaisesRegex(RuntimeError, "symlink destination"):
                usb_recovery.write_private_text(linked, "blocked")

    def test_send_raw_cmdv1_writes_success_and_expected_disconnect_errors(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            args = args_for(tmp)
            out_dir = Path(tmp)
            with mock.patch.object(usb_recovery, "bridge_exchange", return_value="rebinding\nA90P1 END rc=0 status=ok\n") as bridge:
                ok, error, output_file = usb_recovery.send_raw_cmdv1(args, ["usbacmreset"], "reset-01", out_dir)

            self.assertTrue(ok)
            self.assertEqual(error, "")
            self.assertIn("rebinding", Path(output_file).read_text(encoding="utf-8"))
            bridge.assert_called_once()
            self.assertIn("cmdv1 usbacmreset", bridge.call_args.args)

            with mock.patch.object(usb_recovery, "bridge_exchange", side_effect=RuntimeError("serial disconnected")):
                ok, error, output_file = usb_recovery.send_raw_cmdv1(args, ["run", "/cache/bin/a90_usbnet", "ncm"], "ncm", out_dir)

            self.assertFalse(ok)
            self.assertEqual(error, "serial disconnected")
            self.assertIn("RuntimeError: serial disconnected", Path(output_file).read_text(encoding="utf-8"))

    def test_wait_recovered_and_cmdv1_text_record_success_and_exceptions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            args = args_for(tmp)
            out_dir = Path(tmp)
            result = SimpleNamespace(rc=0, status="ok", text="A90 Linux init\n")
            with mock.patch.object(usb_recovery, "run_cmdv1_command", return_value=result) as run:
                recovered, recovery_sec, rc, status = usb_recovery.wait_recovered(args, out_dir, "after-reset")

            self.assertTrue(recovered)
            self.assertIsNotNone(recovery_sec)
            self.assertEqual((rc, status), (0, "ok"))
            self.assertEqual((out_dir / "commands" / "after-reset-version.txt").read_text(encoding="utf-8"), "A90 Linux init\n")
            run.assert_called_once_with("127.0.0.1", 54321, 12.0, ["version"])

            with mock.patch.object(usb_recovery, "run_cmdv1_command", side_effect=RuntimeError("bridge down")):
                ok, text, rc, status = usb_recovery.cmdv1_text(args, out_dir, "status", ["status"])

            self.assertFalse(ok)
            self.assertEqual(text, "bridge down")
            self.assertIsNone(rc)
            self.assertEqual(status, "exception")
            self.assertIn("RuntimeError: bridge down", (out_dir / "commands" / "status.txt").read_text(encoding="utf-8"))

    def test_recovery_times_filters_missing_values(self) -> None:
        steps = [
            usb_recovery.RecoveryStep("a", ["version"], True, "", "a.txt", True, 0.25, 0, "ok"),
            usb_recovery.RecoveryStep("b", ["version"], False, "err", "b.txt", False, None, None, "timeout"),
        ]
        self.assertEqual(usb_recovery.recovery_times(steps), [0.25])


class MainReportFlow(unittest.TestCase):
    def test_main_writes_report_with_checks_residual_state_and_failure_rc(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            args = args_for(tmp, cycles=1)
            steps = [
                usb_recovery.RecoveryStep("usbacmreset-01", ["usbacmreset"], True, "", "reset.txt", True, 0.1, 0, "ok"),
                usb_recovery.RecoveryStep("usbnet-ncm", ["run", "/cache/bin/a90_usbnet", "ncm"], True, "", "ncm.txt", True, 0.2, 0, "ok"),
                usb_recovery.RecoveryStep("usbnet-off", ["run", "/cache/bin/a90_usbnet", "off"], True, "", "off.txt", True, 0.3, 0, "ok"),
            ]
            captures = [
                (True, "A90 Linux init\n", 0, "ok"),
                (True, "ncm.ifname: ncm0\n", 0, "ok"),
                (True, "ncm0=present tcpctl=running\n", 0, "ok"),
                (True, "A90 Linux init\n", 0, "ok"),
                (True, "selftest fail=0\n", 0, "ok"),
            ]
            with (
                mock.patch.object(usb_recovery, "parse_args", return_value=args),
                mock.patch.object(usb_recovery, "run_step", side_effect=steps) as run_step,
                mock.patch.object(usb_recovery, "cmdv1_text", side_effect=captures) as cmdv1,
                contextlib.redirect_stdout(io.StringIO()),
            ):
                rc = usb_recovery.main()

            report_dir = Path(tmp) / "run-01"
            payload = json.loads((report_dir / "usb-recovery-report.json").read_text(encoding="utf-8"))
            markdown = (report_dir / "usb-recovery-report.md").read_text(encoding="utf-8")

        self.assertEqual(rc, 1)
        self.assertFalse(payload["pass"])
        self.assertEqual(payload["recovered_count"], 3)
        self.assertEqual(payload["max_recovery_sec"], 0.3)
        self.assertTrue(payload["ncm_present_after_ncm_step"])
        self.assertFalse(payload["final_acm_only"])
        self.assertTrue(payload["residual_state"]["cleanup_required"])
        self.assertIn("| `final acm-only` | `FAIL`", markdown)
        self.assertEqual(run_step.call_count, 3)
        self.assertEqual(cmdv1.call_count, 5)


if __name__ == "__main__":
    unittest.main()

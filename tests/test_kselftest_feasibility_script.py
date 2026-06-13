from __future__ import annotations

import os
import stat
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from _loader import load_revalidation


kselftest = load_revalidation("kselftest_feasibility.py")


class PrivateOutputHelpers(unittest.TestCase):
    def test_private_dir_and_text_writer_enforce_modes_and_reject_symlinks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            out_dir = root / "bundle"
            out_file = out_dir / "report.txt"

            kselftest.write_private_text(out_file, "safe\n")

            self.assertEqual(stat.S_IMODE(out_dir.stat().st_mode), kselftest.PRIVATE_DIR_MODE)
            self.assertEqual(stat.S_IMODE(out_file.stat().st_mode), kselftest.PRIVATE_FILE_MODE)
            self.assertEqual(out_file.read_text(encoding="utf-8"), "safe\n")

            symlink_dir = root / "symlink-dir"
            symlink_dir.symlink_to(out_dir, target_is_directory=True)
            with self.assertRaisesRegex(RuntimeError, "non-directory"):
                kselftest.ensure_private_dir(symlink_dir)

            symlink_file = root / "symlink-file"
            symlink_file.symlink_to(out_file)
            with self.assertRaisesRegex(RuntimeError, "symlink destination"):
                kselftest.write_private_text(symlink_file, "blocked")

    def test_safe_filename_replaces_unsafe_characters(self) -> None:
        self.assertEqual(kselftest.safe_filename("cat /proc/self/status"), "cat--proc-self-status")
        self.assertEqual(kselftest.safe_filename("diag.summary_ok"), "diag.summary_ok")


class CaptureAndClassificationHelpers(unittest.TestCase):
    def test_run_capture_records_success_and_failure_without_device_access(self) -> None:
        args = SimpleNamespace(host="127.0.0.1", port=54321)
        success = kselftest.ProtocolResult(
            begin={},
            end={"rc": "0", "status": "ok"},
            text="A90 Linux init\n",
        )

        with tempfile.TemporaryDirectory() as tmp:
            bundle = Path(tmp)
            with mock.patch.object(kselftest, "run_cmdv1_command", return_value=success) as run:
                capture = kselftest.run_capture(args, bundle, "version", ["version"], 1.5, True)

            self.assertTrue(capture.ok)
            self.assertEqual(capture.rc, 0)
            self.assertEqual(capture.status, "ok")
            self.assertEqual(capture.command, "version")
            self.assertEqual(Path(capture.file).read_text(encoding="utf-8"), "A90 Linux init\n")
            run.assert_called_once_with("127.0.0.1", 54321, 1.5, ["version"], retry_unsafe=False)

            with mock.patch.object(kselftest, "run_cmdv1_command", side_effect=RuntimeError("bridge down")):
                failed = kselftest.run_capture(args, bundle, "bad/name", ["diag", "summary"], 2.0, False)

            self.assertFalse(failed.ok)
            self.assertIsNone(failed.rc)
            self.assertEqual(failed.status, "missing")
            self.assertEqual(failed.error, "bridge down")
            self.assertTrue(failed.file.endswith("cmd-bad-name.txt"))
            self.assertEqual(Path(failed.file).read_text(encoding="utf-8"), "bridge down\n")

    def test_classify_adds_unknowns_when_tracefs_or_toybox_markers_are_absent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bundle = Path(tmp)
            filesystems = bundle / "filesystems.txt"
            filesystems.write_text("nodev\tsysfs\nnodev\ttracefs\n", encoding="utf-8")
            userland = bundle / "userland.txt"
            userland.write_text("toybox=ready\n", encoding="utf-8")
            captures = [
                kselftest.CommandCapture("cat-proc-filesystems", "cat /proc/filesystems", False, True, 0, "ok", 0.1, str(filesystems), ""),
                kselftest.CommandCapture("userland-status", "userland status", True, True, 0, "ok", 0.1, str(userland), ""),
            ]

            complete = kselftest.classify(captures)

            complete_names = {item["name"] for item in complete["conditional_or_unknown"]}
            self.assertNotIn("tracefs-dependent-tests", complete_names)
            self.assertNotIn("toybox-backed-shell-probes", complete_names)
            self.assertIn("procfs-readers", {item["name"] for item in complete["safe_candidates"]})
            self.assertIn("watchdog-tests", {item["name"] for item in complete["blocked"]})

            missing = kselftest.classify([])
            missing_names = {item["name"] for item in missing["conditional_or_unknown"]}
            self.assertIn("tracefs-dependent-tests", missing_names)
            self.assertIn("toybox-backed-shell-probes", missing_names)

    def test_render_markdown_includes_manifest_summary_and_capture_table(self) -> None:
        capture = kselftest.CommandCapture(
            "version",
            "version",
            True,
            True,
            0,
            "ok",
            0.1234,
            "/private/cmd-version.txt",
            "",
        )
        manifest = {
            "pass": True,
            "expect_version": "A90 Linux init 0.9.268",
            "version_matches": True,
            "policy": "read-only",
            "mutation_performed": False,
            "failed_mandatory_count": 0,
            "failed_optional_count": 1,
            "classification": {
                "safe_candidates": [{"name": "procfs-readers", "reason": "read-only"}],
                "conditional_or_unknown": [{"name": "tracefs-read-only-inventory", "status": "conditional", "reason": "opt-in"}],
                "blocked": [{"name": "watchdog-tests", "status": "blocked", "reason": "can arm reboot"}],
            },
            "commands": [kselftest.asdict(capture)],
        }

        markdown = kselftest.render_markdown(manifest)

        self.assertIn("- result: `PASS`", markdown)
        self.assertIn("- failed optional commands: `1`", markdown)
        self.assertIn("`procfs-readers`: read-only", markdown)
        self.assertIn("`watchdog-tests` (blocked): can arm reboot", markdown)
        self.assertIn("OK `version` (mandatory) rc=0 status=ok duration=0.123s", markdown)


if __name__ == "__main__":
    unittest.main()

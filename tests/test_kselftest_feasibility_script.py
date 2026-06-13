from __future__ import annotations

import contextlib
import io
import json
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


class MetadataAndMainFlow(unittest.TestCase):
    def test_collect_host_metadata_records_head_dirty_and_status_lines(self) -> None:
        responses = [
            (0, "abc1234\n"),
            (0, " M tests/example.py\n?? new.txt\n"),
        ]

        with mock.patch.object(kselftest, "run_host_command", side_effect=responses) as run_host:
            metadata = kselftest.collect_host_metadata()

        self.assertEqual(metadata["repo"], str(kselftest.REPO_ROOT))
        self.assertEqual(metadata["git_head"], "abc1234")
        self.assertTrue(metadata["git_dirty"])
        self.assertEqual(metadata["git_status_short"], [" M tests/example.py", "?? new.txt"])
        self.assertEqual(run_host.call_args_list[0].args[0], ["git", "rev-parse", "--short", "HEAD"])
        self.assertEqual(run_host.call_args_list[1].args[0], ["git", "status", "--short"])

        with mock.patch.object(kselftest, "run_host_command", side_effect=[(1, "bad"), (1, "bad")]):
            fallback = kselftest.collect_host_metadata()
        self.assertEqual(fallback["git_head"], "unknown")
        self.assertFalse(fallback["git_dirty"])
        self.assertEqual(fallback["git_status_short"], [])

    def test_main_writes_manifest_markdown_and_residual_state_without_device_access(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bundle = Path(tmp) / "bundle"
            args = SimpleNamespace(
                host="127.0.0.1",
                port=54321,
                timeout_scale=1.0,
                expect_version="A90 Linux init 0.9.268",
                bundle_dir=bundle,
            )

            def fake_capture(_args, bundle_dir: Path, name: str, command: list[str], timeout: float, mandatory: bool):
                text = "A90 Linux init 0.9.268\n" if name == "version" else ""
                if name == "cat-proc-filesystems":
                    text = "nodev\ttracefs\nnodev\tpstore\n"
                elif name == "userland-status":
                    text = "toybox=ready\n"
                path = bundle_dir / f"cmd-{kselftest.safe_filename(name)}.txt"
                kselftest.write_private_text(path, text)
                return kselftest.CommandCapture(
                    name=name,
                    command=" ".join(command),
                    mandatory=mandatory,
                    ok=True,
                    rc=0,
                    status="ok",
                    duration_sec=0.01,
                    file=str(path),
                    error="",
                )

            with (
                mock.patch.object(kselftest, "parse_args", return_value=args),
                mock.patch.object(kselftest, "run_capture", side_effect=fake_capture) as run_capture,
                mock.patch.object(kselftest, "collect_host_metadata", return_value={"git_head": "abc1234", "git_dirty": False}),
                contextlib.redirect_stdout(io.StringIO()) as stdout,
            ):
                rc = kselftest.main()

            manifest = json.loads((bundle / "kselftest-feasibility-report.json").read_text(encoding="utf-8"))
            markdown = (bundle / "kselftest-feasibility-report.md").read_text(encoding="utf-8")

        self.assertEqual(rc, 0)
        self.assertIn("PASS bundle=", stdout.getvalue())
        self.assertEqual(run_capture.call_count, len(kselftest.MANDATORY_COMMANDS) + len(kselftest.OPTIONAL_COMMANDS))
        self.assertTrue(manifest["pass"])
        self.assertTrue(manifest["version_matches"])
        self.assertEqual(manifest["failed_mandatory_count"], 0)
        self.assertEqual(manifest["failed_optional_count"], 0)
        self.assertFalse(manifest["mutation_performed"])
        self.assertEqual(manifest["host"], {"git_head": "abc1234", "git_dirty": False})
        self.assertEqual(manifest["residual_state"]["cleanup_required"], False)
        self.assertEqual(manifest["residual_state"]["failed_mandatory_count"], 0)
        self.assertIn("kselftest_feasibility_total", {item["name"] for item in manifest["phase_timers"]})
        self.assertIn("- result: `PASS`", markdown)


if __name__ == "__main__":
    unittest.main()

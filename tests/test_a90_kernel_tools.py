from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from _loader import load_script


kernel_tools = load_script("workspace/public/src/scripts/revalidation/a90_kernel_tools.py")


class A90KernelToolsTests(unittest.TestCase):
    def test_repo_path_keeps_absolute_and_resolves_relative_under_repo_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            absolute = root / "already" / "absolute"
            with mock.patch.object(kernel_tools, "REPO_ROOT", root):
                self.assertEqual(kernel_tools.repo_path("docs/report.md"), root / "docs" / "report.md")
                self.assertEqual(kernel_tools.repo_path(absolute), absolute)

    def test_collect_host_metadata_reports_clean_and_dirty_states(self) -> None:
        def fake_run(command, timeout=10):
            if command[:2] == ["git", "rev-parse"]:
                return 0, "abc123\n"
            if command[:2] == ["git", "status"]:
                return 0, " M tests/foo.py\n?? new.py\n"
            raise AssertionError(command)

        with mock.patch.object(kernel_tools, "REPO_ROOT", Path("/repo")), \
                mock.patch.object(kernel_tools, "run_host_command", side_effect=fake_run):
            metadata = kernel_tools.collect_host_metadata()

        self.assertEqual(metadata["repo"], "/repo")
        self.assertEqual(metadata["git_head"], "abc123")
        self.assertTrue(metadata["git_dirty"])
        self.assertEqual(metadata["git_status_short"], [" M tests/foo.py", "?? new.py"])

    def test_collect_host_metadata_handles_command_failures(self) -> None:
        with mock.patch.object(kernel_tools, "REPO_ROOT", Path("/repo")), \
                mock.patch.object(kernel_tools, "run_host_command", side_effect=[(1, "fatal\n"), (2, "err\n")]):
            metadata = kernel_tools.collect_host_metadata()

        self.assertEqual(metadata["git_head"], "unknown")
        self.assertIsNone(metadata["git_dirty"])
        self.assertEqual(metadata["git_status_short"], [])

    def test_run_capture_returns_success_capture_and_command_string(self) -> None:
        protocol = kernel_tools.ProtocolResult(
            begin={"cmd": "status"},
            end={"cmd": "status", "rc": "0", "status": "ok"},
            text="body",
        )
        args = SimpleNamespace(host="127.0.0.1", port=54321, timeout=9.0)

        with mock.patch.object(kernel_tools, "run_cmdv1_command", return_value=protocol) as run_cmd, \
                mock.patch.object(kernel_tools.time, "monotonic", side_effect=[10.0, 12.5]):
            capture = kernel_tools.run_capture(args, "status", ["status"])

        run_cmd.assert_called_once_with("127.0.0.1", 54321, 9.0, ["status"], retry_unsafe=False)
        self.assertEqual(capture.name, "status")
        self.assertEqual(capture.command, "status")
        self.assertTrue(capture.ok)
        self.assertEqual(capture.rc, 0)
        self.assertEqual(capture.status, "ok")
        self.assertEqual(capture.duration_sec, 2.5)
        self.assertEqual(capture.text, "body")
        self.assertEqual(capture.error, "")

    def test_run_capture_uses_explicit_timeout_and_preserves_exceptions(self) -> None:
        args = SimpleNamespace(host="h", port=1, timeout=9.0)
        with mock.patch.object(kernel_tools, "run_cmdv1_command", side_effect=RuntimeError("bridge down")) as run_cmd, \
                mock.patch.object(kernel_tools.time, "monotonic", side_effect=[1.0, 1.25]):
            capture = kernel_tools.run_capture(args, "bad", ["wifi", "status"], timeout=3.0)

        run_cmd.assert_called_once_with("h", 1, 3.0, ["wifi", "status"], retry_unsafe=False)
        self.assertFalse(capture.ok)
        self.assertIsNone(capture.rc)
        self.assertEqual(capture.status, "missing")
        self.assertEqual(capture.command, "wifi status")
        self.assertEqual(capture.duration_sec, 0.25)
        self.assertIn("bridge down", capture.error)

    def test_capture_to_manifest_truncates_large_text(self) -> None:
        short = kernel_tools.CommandCapture("n", "cmd", True, 0, "ok", 0.1, "short", "")
        self.assertEqual(kernel_tools.capture_to_manifest(short)["text"], "short")

        long_text = "x" * 4100
        manifest = kernel_tools.capture_to_manifest(
            kernel_tools.CommandCapture("n", "cmd", True, 0, "ok", 0.1, long_text, "")
        )
        self.assertEqual(manifest["text_sha256_like"], "omitted-large-text")
        self.assertTrue(manifest["text"].startswith("x" * 4096))
        self.assertTrue(manifest["text"].endswith("[truncated in manifest]\n"))

    def test_strip_cmdv1_text_removes_protocol_noise_and_keeps_payload(self) -> None:
        raw = (
            "a90:/# cmdv1 status\n"
            "A90P1 BEGIN seq=1 cmd=status\n"
            "payload line\n"
            "[done] status\n"
            "run: pid=123\n"
            "[exit 0]\n"
            "A90P1 END seq=1 cmd=status rc=0 status=ok\n"
            "second line\n"
        )
        self.assertEqual(kernel_tools.strip_cmdv1_text(raw), "payload line\nsecond line\n")
        self.assertEqual(kernel_tools.strip_cmdv1_text(""), "\n")

    def test_kernel_config_parsing_and_summary_helpers(self) -> None:
        config = kernel_tools.parse_kernel_config(
            "CONFIG_A=y\n"
            "CONFIG_B=m\n"
            "# CONFIG_C is not set\n"
            "CONFIG_STR=\"hello\"\n"
            "garbage\n"
        )

        self.assertEqual(config, {"CONFIG_A": "y", "CONFIG_B": "m", "CONFIG_C": "n", "CONFIG_STR": "hello"})
        self.assertEqual(kernel_tools.config_state(config, "CONFIG_MISSING"), "unset")
        self.assertTrue(kernel_tools.config_enabled(config, "CONFIG_A"))
        self.assertTrue(kernel_tools.config_enabled(config, "CONFIG_B"))
        self.assertFalse(kernel_tools.config_enabled(config, "CONFIG_C"))
        self.assertEqual(
            kernel_tools.summarize_options(config, ["CONFIG_A", "CONFIG_B", "CONFIG_C", "CONFIG_STR", "CONFIG_MISSING"]),
            {"y": 1, "m": 1, "n": 1, "unset": 1, "value": 1},
        )

    def test_markdown_table_escapes_pipes_and_newlines(self) -> None:
        table = kernel_tools.markdown_table(["A|B", "C"], [["x|y", "line1\nline2"]])
        self.assertEqual(
            table,
            "| A\\|B | C |\n"
            "| --- | --- |\n"
            "| x\\|y | line1<br>line2 |",
        )

    def test_fetch_kernel_config_strips_protocol_and_parses_config(self) -> None:
        args = SimpleNamespace(timeout=4.0)
        text = "A90P1 BEGIN seq=1 cmd=run\nCONFIG_A=y\n# CONFIG_B is not set\nA90P1 END seq=1 cmd=run rc=0 status=ok\n"
        capture = kernel_tools.CommandCapture("config-zcat", "run toybox", True, 0, "ok", 0.1, text, "")

        with mock.patch.object(kernel_tools, "run_capture", return_value=capture) as run_capture:
            returned_capture, config_text, config = kernel_tools.fetch_kernel_config(args)

        run_capture.assert_called_once_with(
            args,
            "config-zcat",
            ["run", "/cache/bin/toybox", "zcat", "/proc/config.gz"],
            timeout=4.0,
        )
        self.assertIs(returned_capture, capture)
        self.assertEqual(config_text, "CONFIG_A=y\n# CONFIG_B is not set\n")
        self.assertEqual(config, {"CONFIG_A": "y", "CONFIG_B": "n"})


if __name__ == "__main__":
    unittest.main()

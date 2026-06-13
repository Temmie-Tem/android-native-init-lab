from __future__ import annotations

import importlib
import json
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from _loader import load_harness


broker_stub = types.ModuleType("a90_broker")
broker_stub.PROTO = "A90B1"
broker_stub.connect_and_call = lambda *_args, **_kwargs: {}
sys.modules.setdefault("a90_broker", broker_stub)

load_harness("module")
storage_io = importlib.import_module("a90harness.modules.storage_io")


class FakeStore:
    def __init__(self, run_dir: Path) -> None:
        self.run_dir = run_dir
        self.text: dict[str, str] = {}

    def write_text(self, rel: str, text: str) -> Path:
        self.text[rel] = text
        path = self.run_dir / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path


def build_ctx(
    tmp: str,
    *,
    profile: str = "smoke",
    timeout: float = 12.5,
):
    root = Path(tmp)
    store = FakeStore(root)
    module_dir = root / "modules" / storage_io.StorageIoModule.name
    module_dir.mkdir(parents=True, exist_ok=True)
    return SimpleNamespace(
        repo_root=Path("/repo"),
        store=store,
        module_dir=module_dir,
        profile=profile,
        host="127.0.0.1",
        port=54321,
        timeout=timeout,
    )


def completed(returncode: int, stdout: str) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(["cmd"], returncode, stdout=stdout)


class PreparePhase(unittest.TestCase):
    def test_prepare_skips_when_host_ncm_ping_fails_without_attempting_storage_io(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ctx = build_ctx(tmp)
            module = storage_io.StorageIoModule()

            with mock.patch.object(storage_io.subprocess, "run", return_value=completed(1, "no route")) as run:
                result = module.prepare(ctx)

        self.assertTrue(result.ok)
        self.assertTrue(result.skipped)
        self.assertIn("SKIP: host NCM path", result.detail)
        self.assertEqual(module._skip_reason, result.detail)
        self.assertEqual(ctx.store.text["modules/storage-io/preflight-ping.txt"], "no route")
        run.assert_called_once_with(
            ["ping", "-c", "1", "-W", "1", "192.168.7.2"],
            cwd=Path("/repo"),
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=5,
        )

    def test_prepare_records_successful_ping_and_keeps_module_active(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ctx = build_ctx(tmp)
            module = storage_io.StorageIoModule()

            with mock.patch.object(storage_io.subprocess, "run", return_value=completed(0, "pong\n")):
                result = module.prepare(ctx)

        self.assertTrue(result.ok)
        self.assertFalse(result.skipped)
        self.assertEqual(result.detail, "host NCM ping ok")
        self.assertEqual(module._skip_reason, "")
        self.assertEqual(ctx.store.text["modules/storage-io/preflight-ping.txt"], "pong\n")


class RunPhase(unittest.TestCase):
    def test_run_returns_skip_without_subprocess_when_prepare_already_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ctx = build_ctx(tmp)
            module = storage_io.StorageIoModule()
            module._skip_reason = "SKIP: no ncm"

            with mock.patch.object(storage_io.subprocess, "run") as run:
                result = module.run(ctx)

        self.assertTrue(result.ok)
        self.assertTrue(result.skipped)
        self.assertEqual(result.detail, "SKIP: no ncm")
        run.assert_not_called()

    def test_run_smoke_builds_storage_iotest_command_with_minimum_bridge_timeout(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ctx = build_ctx(tmp, profile="smoke", timeout=12.5)
            module = storage_io.StorageIoModule()
            module._run_id = "testrun"

            with mock.patch.object(storage_io.subprocess, "run", return_value=completed(0, "storage ok")) as run:
                result = module.run(ctx)

        self.assertTrue(result.ok)
        self.assertEqual(result.detail, "rc=0 sizes=4096")
        command = run.call_args.args[0]
        self.assertEqual(command[:2], [
            sys.executable,
            "/repo/workspace/public/src/scripts/revalidation/storage_iotest.py",
        ])
        self.assertEqual(command[command.index("--bridge-host") + 1], "127.0.0.1")
        self.assertEqual(command[command.index("--bridge-port") + 1], "54321")
        self.assertEqual(command[command.index("--bridge-timeout") + 1], "45.0")
        self.assertEqual(command[command.index("--run-id") + 1], "testrun")
        self.assertEqual(command[command.index("--sizes") + 1], "4096")
        self.assertEqual(command[command.index("--host-dir") + 1], str(ctx.module_dir / "host-files"))
        self.assertEqual(command[command.index("--out-json") + 1], str(ctx.module_dir / "storage-iotest-report.json"))
        self.assertIn("storage ok", ctx.store.text["modules/storage-io/wrapper-output.txt"])

    def test_run_quick_profile_uses_full_size_set_and_reports_nonzero_rc(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ctx = build_ctx(tmp, profile="quick", timeout=88.0)
            module = storage_io.StorageIoModule()
            module._run_id = "testrun"

            with mock.patch.object(storage_io.subprocess, "run", return_value=completed(7, "failed")) as run:
                result = module.run(ctx)

        self.assertFalse(result.ok)
        self.assertEqual(result.detail, "rc=7 sizes=4096,65536,1048576")
        command = run.call_args.args[0]
        self.assertEqual(command[command.index("--bridge-timeout") + 1], "88.0")
        self.assertEqual(command[command.index("--sizes") + 1], "4096,65536,1048576")


class CleanupAndVerifyPhases(unittest.TestCase):
    def test_cleanup_is_skip_aware_or_runs_storage_iotest_clean(self) -> None:
        skipped_module = storage_io.StorageIoModule()
        skipped_module._skip_reason = "SKIP: no ncm"
        skipped = skipped_module.cleanup(SimpleNamespace())
        self.assertTrue(skipped.ok)
        self.assertTrue(skipped.skipped)
        self.assertEqual(skipped.detail, "SKIP: no ncm")

        with tempfile.TemporaryDirectory() as tmp:
            ctx = build_ctx(tmp, timeout=9.0)
            module = storage_io.StorageIoModule()
            module._run_id = "testrun"

            with mock.patch.object(storage_io.subprocess, "run", return_value=completed(0, "clean ok")) as run:
                result = module.cleanup(ctx)

        self.assertTrue(result.ok)
        self.assertEqual(result.detail, "rc=0")
        command = run.call_args.args[0]
        self.assertEqual(command[command.index("--bridge-timeout") + 1], "45.0")
        self.assertEqual(command[command.index("--run-id") + 1], "testrun")
        self.assertEqual(command[-1], "clean")
        self.assertIn("clean ok", ctx.store.text["modules/storage-io/cleanup-output.txt"])

    def test_verify_is_skip_aware_and_requires_report_with_passing_results(self) -> None:
        module = storage_io.StorageIoModule()
        module._skip_reason = "SKIP: no ncm"
        skipped = module.verify(SimpleNamespace())
        self.assertTrue(skipped.ok)
        self.assertTrue(skipped.skipped)

        with tempfile.TemporaryDirectory() as tmp:
            ctx = build_ctx(tmp)
            missing = storage_io.StorageIoModule().verify(ctx)
            self.assertFalse(missing.ok)
            self.assertIn("missing", missing.detail)

            report_path = ctx.module_dir / "storage-iotest-report.json"
            report_path.write_text(json.dumps({"pass": True, "results": [{"path": "file.bin"}]}), encoding="utf-8")
            passed = storage_io.StorageIoModule().verify(ctx)
            self.assertTrue(passed.ok)
            self.assertEqual(passed.detail, "pass=True files=1")

            report_path.write_text(json.dumps({"pass": True, "results": []}), encoding="utf-8")
            empty_results = storage_io.StorageIoModule().verify(ctx)
            self.assertFalse(empty_results.ok)
            self.assertEqual(empty_results.detail, "pass=True files=0")


if __name__ == "__main__":
    unittest.main()

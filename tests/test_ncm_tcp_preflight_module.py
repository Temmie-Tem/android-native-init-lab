from __future__ import annotations

import importlib
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

module_contract = load_harness("module")
ncm_preflight = importlib.import_module("a90harness.modules.ncm_tcp_preflight")


class FakeRecord:
    def __init__(self, ok: bool) -> None:
        self.ok = ok

    def to_dict(self) -> dict[str, bool]:
        return {"ok": self.ok}


class FakeClient:
    def __init__(self, ok: bool = True, output: str = "") -> None:
        self.ok = ok
        self.output = output
        self.calls: list[tuple[str, list[str], float | None]] = []

    def run(self, label: str, command: list[str], *, timeout: float | None = None):
        self.calls.append((label, command, timeout))
        return FakeRecord(self.ok), self.output


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


def build_ctx(tmp: str, *, client: FakeClient | None = None):
    root = Path(tmp)
    store = FakeStore(root)
    module_dir = root / "modules" / ncm_preflight.NcmTcpPreflightModule.name
    module_dir.mkdir(parents=True, exist_ok=True)
    return SimpleNamespace(
        repo_root=Path("/repo"),
        store=store,
        module_dir=module_dir,
        client=client or FakeClient(),
        host="127.0.0.1",
        port=54321,
        timeout=12.5,
    )


def completed(rc: int, stdout: str) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(["cmd"], rc, stdout=stdout)


class PreparePhase(unittest.TestCase):
    def test_prepare_skips_when_host_ncm_ping_fails_without_touching_device(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ctx = build_ctx(tmp, client=FakeClient())
            module = ncm_preflight.NcmTcpPreflightModule()

            with mock.patch.object(ncm_preflight.subprocess, "run", return_value=completed(1, "no route")) as run:
                result = module.prepare(ctx)

        self.assertTrue(result.ok)
        self.assertTrue(result.skipped)
        self.assertIn("SKIP: host NCM path", result.detail)
        self.assertEqual(ctx.store.text["modules/ncm-tcp-preflight/preflight-ping.txt"], "no route")
        self.assertEqual(ctx.client.calls, [])
        run.assert_called_once()

    def test_prepare_requires_trusted_ramdisk_tcpctl_helper_after_ping_ok(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            client = FakeClient(ok=False, output="missing")
            ctx = build_ctx(tmp, client=client)
            module = ncm_preflight.NcmTcpPreflightModule()

            with mock.patch.object(ncm_preflight.subprocess, "run", return_value=completed(0, "pong")):
                result = module.prepare(ctx)

        self.assertFalse(result.ok)
        self.assertFalse(result.skipped)
        self.assertIn("trusted ramdisk tcpctl helper missing", result.detail)
        self.assertEqual(client.calls, [
            ("stat-/bin/a90_tcpctl", ["stat", "/bin/a90_tcpctl"], 12.5),
        ])
        self.assertEqual(
            ctx.store.text["modules/ncm-tcp-preflight/stat-bin-a90_tcpctl.txt"],
            "missing",
        )

    def test_prepare_records_trusted_helper_and_sets_device_binary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            client = FakeClient(ok=True, output="size mode")
            ctx = build_ctx(tmp, client=client)
            module = ncm_preflight.NcmTcpPreflightModule()

            with mock.patch.object(ncm_preflight.subprocess, "run", return_value=completed(0, "pong")):
                result = module.prepare(ctx)

        self.assertTrue(result.ok)
        self.assertFalse(result.skipped)
        self.assertIn("tcpctl=/bin/a90_tcpctl", result.detail)
        self.assertEqual(module._device_binary, "/bin/a90_tcpctl")


class RunCleanupVerifyPhases(unittest.TestCase):
    def test_run_returns_skipped_when_prepare_stored_skip_reason(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ctx = build_ctx(tmp)
            module = ncm_preflight.NcmTcpPreflightModule()
            module._skip_reason = "SKIP: no ncm"

            result = module.run(ctx)

        self.assertTrue(result.ok)
        self.assertTrue(result.skipped)
        self.assertEqual(result.detail, "SKIP: no ncm")

    def test_run_builds_tcpctl_smoke_command_and_requires_all_markers(self) -> None:
        stdout = "\n".join([
            "--- ping ---",
            "pong",
            "OK authenticated",
            "auth=required",
            "--- version ---",
            "--- status ---",
            "--- shutdown ---",
            "shutdown",
            "--- serial-run ---",
            "[done] run",
            "--- bridge-version ---",
            "--- ncm-ping ---",
        ])
        with tempfile.TemporaryDirectory() as tmp:
            ctx = build_ctx(tmp)
            module = ncm_preflight.NcmTcpPreflightModule()

            with mock.patch.object(ncm_preflight.subprocess, "run", return_value=completed(0, stdout)) as run:
                result = module.run(ctx)

        self.assertTrue(result.ok)
        self.assertEqual(result.detail, "rc=0 missing=[]")
        command = run.call_args.args[0]
        self.assertEqual(command[:2], [sys.executable, "/repo/workspace/public/src/scripts/revalidation/tcpctl_host.py"])
        self.assertIn("--device-binary", command)
        self.assertEqual(command[command.index("--device-binary") + 1], "/bin/a90_tcpctl")
        self.assertIn("smoke", command)
        self.assertIn("--ready-timeout", command)
        self.assertTrue(ctx.store.text["modules/ncm-tcp-preflight/wrapper-output.txt"].startswith("$ "))

        missing_stdout = stdout.replace("--- status ---", "")
        with tempfile.TemporaryDirectory() as tmp:
            ctx = build_ctx(tmp)
            module = ncm_preflight.NcmTcpPreflightModule()
            with mock.patch.object(ncm_preflight.subprocess, "run", return_value=completed(0, missing_stdout)):
                failed = module.run(ctx)
        self.assertFalse(failed.ok)
        self.assertIn("--- status ---", failed.detail)

    def test_cleanup_is_noop_or_skip_aware(self) -> None:
        module = ncm_preflight.NcmTcpPreflightModule()
        self.assertEqual(module.cleanup(SimpleNamespace()).detail, "tcpctl smoke performs shutdown")

        module._skip_reason = "SKIP: no ncm"
        skipped = module.cleanup(SimpleNamespace())
        self.assertTrue(skipped.skipped)
        self.assertEqual(skipped.detail, "SKIP: no ncm")

    def test_verify_requires_authenticated_tcpctl_markers_and_rejects_auth_none(self) -> None:
        text = "\n".join([
            "pong",
            "OK authenticated",
            "auth=required",
            "shutdown",
            "[done] run",
        ])
        with tempfile.TemporaryDirectory() as tmp:
            ctx = build_ctx(tmp)
            (ctx.module_dir / "wrapper-output.txt").write_text(text, encoding="utf-8")
            module = ncm_preflight.NcmTcpPreflightModule()

            result = module.verify(ctx)

        self.assertTrue(result.ok)
        self.assertIn("authenticated=True", result.detail)
        self.assertIn("serial_done=True", result.detail)

        with tempfile.TemporaryDirectory() as tmp:
            ctx = build_ctx(tmp)
            (ctx.module_dir / "wrapper-output.txt").write_text(text + "\nauth=none\n", encoding="utf-8")
            failed = ncm_preflight.NcmTcpPreflightModule().verify(ctx)
        self.assertFalse(failed.ok)

        module = ncm_preflight.NcmTcpPreflightModule()
        module._skip_reason = "SKIP: no ncm"
        skipped = module.verify(SimpleNamespace())
        self.assertTrue(skipped.ok)
        self.assertTrue(skipped.skipped)


if __name__ == "__main__":
    unittest.main()

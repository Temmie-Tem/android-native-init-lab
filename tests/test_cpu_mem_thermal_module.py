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
cpu_thermal = importlib.import_module("a90harness.modules.cpu_mem_thermal")


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


def build_ctx(tmp: str, *, profile: str = "smoke", timeout: float = 10.0):
    root = Path(tmp)
    store = FakeStore(root)
    module_dir = root / "modules" / cpu_thermal.CpuMemThermalModule.name
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


def write_report(ctx, run_id: str, payload: dict[str, object]) -> Path:
    path = ctx.module_dir / run_id / "cpu-mem-thermal-report.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def report_payload(*, passed: bool = True, controlled_zombies: bool = True) -> dict[str, object]:
    return {
        "pass": passed,
        "checks": [
            {"name": "controlled zombies", "ok": controlled_zombies},
            {"name": "final selftest", "ok": True},
        ],
    }


class RunPhase(unittest.TestCase):
    def test_run_smoke_builds_bounded_cpu_mem_thermal_command(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ctx = build_ctx(tmp, profile="smoke", timeout=5.0)
            module = cpu_thermal.CpuMemThermalModule()
            module._run_id = "testrun"

            with mock.patch.object(cpu_thermal.subprocess, "run", return_value=completed(0, "thermal ok")) as run:
                result = module.run(ctx)

        self.assertTrue(result.ok)
        self.assertEqual(result.detail, "rc=0 cycles=1 stress_sec=1 mem_size=4M")
        command = run.call_args.args[0]
        self.assertEqual(command[:2], [
            sys.executable,
            "/repo/workspace/public/src/scripts/revalidation/cpu_mem_thermal_stability.py",
        ])
        self.assertEqual(command[command.index("--bridge-host") + 1], "127.0.0.1")
        self.assertEqual(command[command.index("--bridge-port") + 1], "54321")
        self.assertEqual(command[command.index("--bridge-timeout") + 1], "45.0")
        self.assertEqual(command[command.index("--run-id") + 1], "testrun")
        self.assertEqual(command[command.index("--out-dir") + 1], str(ctx.module_dir))
        self.assertEqual(command[command.index("--cycles") + 1], "1")
        self.assertEqual(command[command.index("--stress-sec") + 1], "1")
        self.assertEqual(command[command.index("--stress-workers") + 1], "2")
        self.assertEqual(command[command.index("--mem-size") + 1], "4M")
        self.assertEqual(run.call_args.kwargs["timeout"], 240)
        self.assertIn("thermal ok", ctx.store.text["modules/cpu-mem-thermal/wrapper-output.txt"])

    def test_run_quick_profile_uses_larger_bounds_and_reports_nonzero_rc(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ctx = build_ctx(tmp, profile="quick", timeout=75.0)
            module = cpu_thermal.CpuMemThermalModule()
            module._run_id = "testrun"

            with mock.patch.object(cpu_thermal.subprocess, "run", return_value=completed(4, "failed")) as run:
                result = module.run(ctx)

        self.assertFalse(result.ok)
        self.assertEqual(result.detail, "rc=4 cycles=2 stress_sec=2 mem_size=8M")
        command = run.call_args.args[0]
        self.assertEqual(command[command.index("--bridge-timeout") + 1], "75.0")
        self.assertEqual(command[command.index("--cycles") + 1], "2")
        self.assertEqual(command[command.index("--stress-sec") + 1], "2")
        self.assertEqual(command[command.index("--mem-size") + 1], "8M")


class VerifyPhase(unittest.TestCase):
    def test_verify_fails_when_report_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ctx = build_ctx(tmp)
            module = cpu_thermal.CpuMemThermalModule()
            module._run_id = "testrun"

            result = module.verify(ctx)

        self.assertFalse(result.ok)
        self.assertIn("missing", result.detail)

    def test_verify_accepts_passing_report_with_controlled_zombie_check(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ctx = build_ctx(tmp)
            module = cpu_thermal.CpuMemThermalModule()
            module._run_id = "testrun"
            write_report(ctx, "testrun", report_payload())

            result = module.verify(ctx)

        self.assertTrue(result.ok)
        self.assertEqual(result.detail, "pass=True controlled_zombies=True")

    def test_verify_rejects_failed_report_or_missing_controlled_zombie_check(self) -> None:
        cases = [
            (report_payload(passed=False), "pass=False controlled_zombies=True"),
            (report_payload(controlled_zombies=False), "pass=True controlled_zombies=False"),
            ({"pass": True, "checks": []}, "pass=True controlled_zombies=None"),
        ]
        for payload, detail in cases:
            with self.subTest(detail=detail):
                with tempfile.TemporaryDirectory() as tmp:
                    ctx = build_ctx(tmp)
                    module = cpu_thermal.CpuMemThermalModule()
                    module._run_id = "testrun"
                    write_report(ctx, "testrun", payload)

                    result = module.verify(ctx)

                self.assertFalse(result.ok)
                self.assertEqual(result.detail, detail)


if __name__ == "__main__":
    unittest.main()

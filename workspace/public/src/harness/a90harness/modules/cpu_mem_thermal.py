"""CPU/memory/thermal stability module wrapper."""

from __future__ import annotations

import json
import subprocess
import sys
import time

from a90harness.module import ModuleContext, StepResult, TestModule


class CpuMemThermalModule(TestModule):
    name = "cpu-mem-thermal"
    description = "run bounded CPU/memory/thermal smoke validation through existing helper"
    cycle_label = "v173"
    read_only = False

    def __init__(self) -> None:
        self._run_id = f"v173-cpu-{int(time.time())}"

    def run(self, ctx: ModuleContext) -> StepResult:
        if ctx.profile == "smoke":
            cycles, stress_sec, mem_size = "1", "1", "4M"
        else:
            cycles, stress_sec, mem_size = "2", "2", "8M"
        command = [
            sys.executable,
            str(ctx.repo_root / "workspace/public/src/scripts/revalidation/cpu_mem_thermal_stability.py"),
            "--bridge-host",
            ctx.host,
            "--bridge-port",
            str(ctx.port),
            "--bridge-timeout",
            str(max(ctx.timeout, 45.0)),
            "--run-id",
            self._run_id,
            "--out-dir",
            str(ctx.module_dir),
            "--cycles",
            cycles,
            "--stress-sec",
            stress_sec,
            "--stress-workers",
            "2",
            "--mem-size",
            mem_size,
        ]
        result = subprocess.run(
            command,
            cwd=ctx.repo_root,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=240,
        )
        ctx.store.write_text(f"modules/{self.name}/wrapper-output.txt", "$ " + " ".join(command) + "\n\n" + result.stdout)
        return StepResult("run", result.returncode == 0, f"rc={result.returncode} cycles={cycles} stress_sec={stress_sec} mem_size={mem_size}", 0.0)

    def verify(self, ctx: ModuleContext) -> StepResult:
        report_path = ctx.module_dir / self._run_id / "cpu-mem-thermal-report.json"
        if not report_path.exists():
            return StepResult("verify", False, f"missing {report_path}", 0.0)
        payload = json.loads(report_path.read_text(encoding="utf-8"))
        checks = {item.get("name", ""): item.get("ok") is True for item in payload.get("checks", [])}
        ok = payload.get("pass") is True and checks.get("controlled zombies", False)
        return StepResult(
            "verify",
            ok,
            f"pass={payload.get('pass')} controlled_zombies={checks.get('controlled zombies')}",
            0.0,
        )

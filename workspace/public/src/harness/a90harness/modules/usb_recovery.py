"""USB recovery validation module wrapper."""

from __future__ import annotations

import json
import subprocess
import sys
import time

from a90harness.evidence import read_bounded_json
from a90harness.module import ModuleContext, StepResult, TestModule


class UsbRecoveryModule(TestModule):
    name = "usb-recovery"
    description = "run bounded USB ACM/NCM software recovery validation"
    cycle_label = "v174"
    read_only = False
    requires_usb_rebind = True
    operator_confirm_required = True

    def __init__(self) -> None:
        self._run_id = f"v174-usb-{int(time.time())}"

    def run(self, ctx: ModuleContext) -> StepResult:
        cycles = "1" if ctx.profile == "smoke" else "2"
        command = [
            sys.executable,
            str(ctx.repo_root / "workspace/public/src/scripts/revalidation/usb_recovery_validate.py"),
            "--host",
            ctx.host,
            "--port",
            str(ctx.port),
            "--timeout",
            str(max(ctx.timeout, 12.0)),
            "--recovery-timeout",
            "45",
            "--cycles",
            cycles,
            "--run-id",
            self._run_id,
            "--out-dir",
            str(ctx.module_dir),
        ]
        result = subprocess.run(
            command,
            cwd=ctx.repo_root,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=300,
        )
        ctx.store.write_text(f"modules/{self.name}/wrapper-output.txt", "$ " + " ".join(command) + "\n\n" + result.stdout)
        return StepResult("run", result.returncode == 0, f"rc={result.returncode} cycles={cycles}", 0.0)

    def verify(self, ctx: ModuleContext) -> StepResult:
        report_path = ctx.module_dir / self._run_id / "usb-recovery-report.json"
        if not report_path.exists():
            return StepResult("verify", False, f"missing {report_path}", 0.0)
        payload = read_bounded_json(report_path, max_bytes=2 * 1024 * 1024)
        checks = {item.get("name", ""): item.get("ok") is True for item in payload.get("checks", [])}
        ok = payload.get("pass") is True and checks.get("final version", False) and checks.get("final selftest", False)
        return StepResult(
            "verify",
            ok,
            f"pass={payload.get('pass')} max_recovery={payload.get('max_recovery_sec')}",
            0.0,
        )

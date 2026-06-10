"""Storage I/O module wrapper."""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

from a90harness.evidence import read_bounded_json
from a90harness.module import ModuleContext, StepResult, TestModule


class StorageIoModule(TestModule):
    name = "storage-io"
    description = "run bounded SD storage write/read/hash validation through existing storage_iotest.py"
    cycle_label = "v173"
    read_only = False
    requires_ncm = True
    external_bridge_client = True

    def __init__(self) -> None:
        self._skip_reason = ""
        self._run_id = f"v173-storage-{int(time.time())}"

    def prepare(self, ctx: ModuleContext) -> StepResult:
        result = subprocess.run(
            ["ping", "-c", "1", "-W", "1", "192.168.7.2"],
            cwd=ctx.repo_root,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=5,
        )
        ctx.store.write_text(f"modules/{self.name}/preflight-ping.txt", result.stdout)
        if result.returncode != 0:
            self._skip_reason = "SKIP: host NCM path 192.168.7.2 is not reachable; not attempting sudo or USB rebind"
            return StepResult("prepare", True, self._skip_reason, 0.0, skipped=True)
        return StepResult("prepare", True, "host NCM ping ok", 0.0)

    def run(self, ctx: ModuleContext) -> StepResult:
        if self._skip_reason:
            return StepResult("run", True, self._skip_reason, 0.0, skipped=True)
        sizes = "4096" if ctx.profile == "smoke" else "4096,65536,1048576"
        command = [
            sys.executable,
            str(ctx.repo_root / "workspace/public/src/scripts/revalidation/storage_iotest.py"),
            "--bridge-host",
            ctx.host,
            "--bridge-port",
            str(ctx.port),
            "--bridge-timeout",
            str(max(ctx.timeout, 45.0)),
            "--device-protocol",
            "cmdv1",
            "--run-id",
            self._run_id,
            "run",
            "--sizes",
            sizes,
            "--host-dir",
            str(ctx.module_dir / "host-files"),
            "--out-md",
            str(ctx.module_dir / "storage-iotest-report.md"),
            "--out-json",
            str(ctx.module_dir / "storage-iotest-report.json"),
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
        return StepResult("run", result.returncode == 0, f"rc={result.returncode} sizes={sizes}", 0.0)

    def cleanup(self, ctx: ModuleContext) -> StepResult:
        if self._skip_reason:
            return StepResult("cleanup", True, self._skip_reason, 0.0, skipped=True)
        command = [
            sys.executable,
            str(ctx.repo_root / "workspace/public/src/scripts/revalidation/storage_iotest.py"),
            "--bridge-host",
            ctx.host,
            "--bridge-port",
            str(ctx.port),
            "--bridge-timeout",
            str(max(ctx.timeout, 45.0)),
            "--device-protocol",
            "cmdv1",
            "--run-id",
            self._run_id,
            "clean",
        ]
        result = subprocess.run(
            command,
            cwd=ctx.repo_root,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=120,
        )
        ctx.store.write_text(f"modules/{self.name}/cleanup-output.txt", "$ " + " ".join(command) + "\n\n" + result.stdout)
        return StepResult("cleanup", result.returncode == 0, f"rc={result.returncode}", 0.0)

    def verify(self, ctx: ModuleContext) -> StepResult:
        if self._skip_reason:
            return StepResult("verify", True, self._skip_reason, 0.0, skipped=True)
        report_path = ctx.module_dir / "storage-iotest-report.json"
        if not report_path.exists():
            return StepResult("verify", False, f"missing {report_path}", 0.0)
        payload = read_bounded_json(report_path, max_bytes=4 * 1024 * 1024)
        ok = payload.get("pass") is True and bool(payload.get("results"))
        return StepResult("verify", ok, f"pass={payload.get('pass')} files={len(payload.get('results', []))}", 0.0)

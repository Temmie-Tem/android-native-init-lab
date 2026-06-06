"""Read-only kselftest feasibility module wrapper."""

from __future__ import annotations

import json
import subprocess
import sys

from a90harness.module import ModuleContext, StepResult, TestModule


class KselftestFeasibilityModule(TestModule):
    name = "kselftest-feasibility"
    description = "classify safe kselftest/LTP candidates without running mutating tests"
    read_only = True

    def run(self, ctx: ModuleContext) -> StepResult:
        command = [
            sys.executable,
            str(ctx.repo_root / "workspace/public/src/scripts/revalidation/kselftest_feasibility.py"),
            "--host",
            ctx.host,
            "--port",
            str(ctx.port),
            "--timeout-scale",
            "1",
            "--expect-version",
            ctx.expect_version,
            "--bundle-dir",
            str(ctx.module_dir),
        ]
        result = subprocess.run(
            command,
            cwd=ctx.repo_root,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=max(120.0, ctx.timeout * 12),
        )
        ctx.store.write_text(
            f"modules/{self.name}/wrapper-output.txt",
            "$ " + " ".join(command) + "\n\n" + result.stdout,
        )
        ok = result.returncode == 0
        return StepResult("run", ok, f"rc={result.returncode}", 0.0)

    def verify(self, ctx: ModuleContext) -> StepResult:
        report_path = ctx.module_dir / "kselftest-feasibility-report.json"
        if not report_path.exists():
            return StepResult("verify", False, f"missing {report_path}", 0.0)
        payload = json.loads(report_path.read_text(encoding="utf-8"))
        checks = {
            "pass": payload.get("pass") is True,
            "version_matches": payload.get("version_matches") is True,
            "no_mutation": payload.get("mutation_performed") is False,
            "failed_mandatory_count": payload.get("failed_mandatory_count") == 0,
            "safe_candidates": bool(payload.get("classification", {}).get("safe_candidates")),
            "blocked": bool(payload.get("classification", {}).get("blocked")),
        }
        ok = all(checks.values())
        detail = ", ".join(f"{name}={value}" for name, value in checks.items())
        return StepResult("verify", ok, detail, 0.0)

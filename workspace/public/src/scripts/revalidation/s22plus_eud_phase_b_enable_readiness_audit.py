#!/usr/bin/env python3
"""Host-only readiness audit for the S22+ EUD Phase-B reversible enable gate.

This script does not flash, reboot, write sysfs, install modules, or touch a
connected device by default. It checks that the inert policy draft and active
AGENTS policy are in the expected state, then reuses the EUD gate's host-only
offline and plan modes.

Use --include-read-only-check only when the current Android/root baseline should
also be refreshed. That mode still performs no writes.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import s22plus_eud_phase_b_enable_live_gate as gate


DEFAULT_DRAFT = gate.POLICY_DRAFT
DEFAULT_AGENT_CONTRACT = Path("AGENTS.md")
DEFAULT_GATE = Path("workspace/public/src/scripts/revalidation/s22plus_eud_phase_b_enable_live_gate.py")


def repo_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / ".git").is_dir():
            return parent
    raise RuntimeError(f"could not locate repo root from {current}")


def resolve(root: Path, path: Path) -> Path:
    return path if path.is_absolute() else root / path


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def normalized_text(path: Path) -> str:
    if not path.is_file():
        raise SystemExit(f"required file missing: {path}")
    return " ".join(path.read_text(encoding="utf-8").split())


def marker_status(path: Path, markers: list[str]) -> dict[str, Any]:
    text = normalized_text(path)
    missing = [marker for marker in markers if marker not in text]
    return {
        "path": str(path),
        "required_count": len(markers),
        "missing": missing,
        "complete": missing == [],
    }


def run_command(root: Path, argv: list[str | Path], timeout: float) -> dict[str, Any]:
    completed = subprocess.run(
        [str(part) for part in argv],
        cwd=str(root),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=timeout,
        check=False,
    )
    return {
        "argv": [str(part) for part in argv],
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def fail(message: str, report: dict[str, Any]) -> None:
    report.setdefault("failures", []).append(message)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--draft", type=Path, default=DEFAULT_DRAFT)
    parser.add_argument("--agents", type=Path, default=DEFAULT_AGENT_CONTRACT)
    parser.add_argument("--gate", type=Path, default=DEFAULT_GATE)
    parser.add_argument("--out", type=Path, help="optional JSON report output path")
    parser.add_argument("--expect-agents-inactive", action="store_true", default=True)
    parser.add_argument("--no-expect-agents-inactive", action="store_false", dest="expect_agents_inactive")
    parser.add_argument(
        "--expect-agents-active",
        action="store_true",
        help="require the selected AGENTS file to contain the complete EUD Phase-B live policy",
    )
    parser.add_argument("--assert-default-dryrun-policy-block", action="store_true", default=True)
    parser.add_argument("--no-default-dryrun-check", action="store_false", dest="assert_default_dryrun_policy_block")
    parser.add_argument(
        "--include-read-only-check",
        action="store_true",
        help="also run the EUD gate --read-only-check; this uses ADB/root but performs no writes",
    )
    args = parser.parse_args(argv)
    if args.expect_agents_active:
        args.expect_agents_inactive = False

    root = repo_root()
    agents = resolve(root, args.agents)
    draft = resolve(root, args.draft)
    gate_script = resolve(root, args.gate)
    markers = gate.required_policy_markers()

    report: dict[str, Any] = {
        "generated_at_utc": utc_now(),
        "purpose": "host-only readiness audit for S22+ EUD Phase-B reversible enable",
        "device_action": bool(args.include_read_only_check),
        "device_action_kind": "read-only-adb-root" if args.include_read_only_check else "none",
        "writes_performed": False,
        "reboots_performed": False,
        "flashes_performed": False,
        "sysfs_writes_performed": False,
        "required_markers": markers,
        "agents": marker_status(agents, markers),
        "draft": marker_status(draft, markers),
        "commands": {},
        "failures": [],
    }

    if args.expect_agents_inactive and report["agents"]["complete"]:
        fail("AGENTS.md already contains all EUD Phase-B markers; this audit expected inactive policy", report)
    if args.expect_agents_active and not report["agents"]["complete"]:
        fail(f"AGENTS policy is missing active markers: {report['agents']['missing']}", report)
    if not report["draft"]["complete"]:
        fail(f"exception draft is missing markers: {report['draft']['missing']}", report)

    offline = run_command(root, ["python3", gate_script, "--offline-check"], timeout=20.0)
    report["commands"]["offline_check"] = offline
    if offline["returncode"] != 0:
        fail(f"EUD gate --offline-check failed rc={offline['returncode']}", report)

    plan = run_command(root, ["python3", gate_script, "--print-plan"], timeout=20.0)
    report["commands"]["print_plan"] = plan
    plan_output = f"{plan['stdout']}\n{plan['stderr']}"
    if plan["returncode"] != 0:
        fail(f"EUD gate --print-plan failed rc={plan['returncode']}", report)
    for expected in [
        gate.LIVE_ACK_TOKEN,
        gate.EUD_ENABLE_PARAM,
        gate.EUD_TTY,
        "write 1",
        "write 0",
        "no flash",
        "no reboot",
        "no partition write",
        "no module insertion",
        "--read-only-check",
        "--live",
    ]:
        if expected not in plan_output:
            fail(f"EUD gate --print-plan missing expected text: {expected}", report)

    if args.assert_default_dryrun_policy_block:
        dryrun = run_command(root, ["python3", gate_script], timeout=20.0)
        report["commands"]["default_dryrun"] = dryrun
        combined = f"{dryrun['stdout']}\n{dryrun['stderr']}"
        if dryrun["returncode"] == 0:
            fail("default dry-run unexpectedly passed while AGENTS policy should be inactive", report)
        if "agents_exception missing EUD Phase-B markers" not in combined:
            fail("default dry-run did not fail at the expected AGENTS policy marker gate", report)

    if args.include_read_only_check:
        readonly = run_command(root, ["python3", gate_script, "--read-only-check"], timeout=90.0)
        report["commands"]["read_only_check"] = readonly
        if readonly["returncode"] != 0:
            fail(f"EUD gate --read-only-check failed rc={readonly['returncode']}", report)
        readonly_output = f"{readonly['stdout']}\n{readonly['stderr']}"
        for expected in ["read-only check ok", "enable=0", "ttyEUD0=1"]:
            if expected not in readonly_output:
                fail(f"EUD gate --read-only-check missing expected text: {expected}", report)

    report["result"] = "pass" if not report["failures"] else "fail"
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.out:
        out = resolve(root, args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0 if report["result"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

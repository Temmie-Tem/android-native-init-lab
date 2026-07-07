#!/usr/bin/env python3
"""Host-only readiness audit for the S22+ ramoops DTBO + M13 capture gate.

This script does not flash, reboot, or touch a connected device. It checks that
the active policy and inert exception draft are in the expected state, then
reuses the capture gate's offline checks so hash/manifest drift is caught before
an attended run is considered.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import s22plus_ramoops_dtbo_m13_capture_live_gate as gate
from s22plus_m3_observable_live_gate import EXPECTED_MAGISK_AP_SHA256, EXPECTED_STOCK_BOOT_AP_SHA256
from s22plus_m13_nomodule_configfs_live_gate import (
    EXPECTED_M13_AP_SHA256,
    EXPECTED_M13_BASE_BOOT_SHA256,
    EXPECTED_M13_BOOT_SHA256,
    EXPECTED_M13_INIT_SHA256,
    EXPECTED_M13_KERNEL_SHA256,
    EXPECTED_M13_SOURCE_SHA256,
)
from s22plus_ramoops_dtbo_m18_capture_live_gate import (
    EXPECTED_DTBO_CANDIDATE_AP_SHA256,
    EXPECTED_DTBO_ROLLBACK_AP_SHA256,
    EXPECTED_PATCHED_DTBO_RAW_SHA256,
    EXPECTED_STOCK_DTBO_RAW_SHA256,
    RESTORE_DTBO_ACK_TOKEN,
)


DEFAULT_DRAFT = Path("docs/operations/S22PLUS_RAMOOPS_DTBO_M13_CAPTURE_AGENTS_EXCEPTION_DRAFT_2026-07-08.md")
DEFAULT_AGENT_CONTRACT = Path("AGENTS.md")
DEFAULT_GATE = Path("workspace/public/src/scripts/revalidation/s22plus_ramoops_dtbo_m13_capture_live_gate.py")


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


def required_markers() -> list[str]:
    return [
        "S22+ ramoops DTBO + M13 positive-control",
        "workspace/public/src/scripts/revalidation/s22plus_ramoops_dtbo_m13_capture_live_gate.py",
        EXPECTED_DTBO_CANDIDATE_AP_SHA256,
        EXPECTED_DTBO_ROLLBACK_AP_SHA256,
        EXPECTED_PATCHED_DTBO_RAW_SHA256,
        EXPECTED_STOCK_DTBO_RAW_SHA256,
        EXPECTED_M13_AP_SHA256,
        EXPECTED_M13_BOOT_SHA256,
        EXPECTED_M13_BASE_BOOT_SHA256,
        EXPECTED_M13_KERNEL_SHA256,
        EXPECTED_M13_INIT_SHA256,
        EXPECTED_M13_SOURCE_SHA256,
        EXPECTED_MAGISK_AP_SHA256,
        EXPECTED_STOCK_BOOT_AP_SHA256,
        gate.LIVE_ACK_TOKEN,
        gate.ROLLBACK_BOOT_ACK_TOKEN,
        RESTORE_DTBO_ACK_TOKEN,
        "dtbo.img.lz4",
        "boot.img.lz4",
        "ramoops_region/status=okay",
        "M13 positive-control",
        "pstore",
        "restore stock DTBO",
        "manual download-mode",
        "no vendor_boot",
    ]


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
    parser.add_argument("--assert-default-dryrun-policy-block", action="store_true", default=True)
    parser.add_argument("--no-default-dryrun-check", action="store_false", dest="assert_default_dryrun_policy_block")
    args = parser.parse_args(argv)

    root = repo_root()
    markers = required_markers()
    agents = resolve(root, args.agents)
    draft = resolve(root, args.draft)
    gate_script = resolve(root, args.gate)

    report: dict[str, Any] = {
        "generated_at_utc": utc_now(),
        "purpose": "host-only readiness audit for S22+ ramoops DTBO + M13 capture",
        "device_action": False,
        "required_markers": markers,
        "agents": marker_status(agents, markers),
        "draft": marker_status(draft, markers),
        "commands": {},
        "failures": [],
    }

    if args.expect_agents_inactive and report["agents"]["complete"]:
        fail("AGENTS.md already contains all DTBO+M13 capture markers; this audit expected inactive policy", report)
    if not report["draft"]["complete"]:
        fail(f"exception draft is missing markers: {report['draft']['missing']}", report)

    offline = run_command(root, ["python3", gate_script, "--offline-check"], timeout=20.0)
    report["commands"]["offline_check"] = offline
    if offline["returncode"] != 0:
        fail(f"capture gate --offline-check failed rc={offline['returncode']}", report)

    if args.assert_default_dryrun_policy_block:
        dryrun = run_command(root, ["python3", gate_script], timeout=20.0)
        report["commands"]["default_dryrun"] = dryrun
        expected_message = "AGENTS.md missing ramoops DTBO + M13 authorization markers"
        combined = f"{dryrun['stdout']}\n{dryrun['stderr']}"
        if dryrun["returncode"] == 0:
            fail("default dry-run unexpectedly passed while AGENTS policy should be inactive", report)
        if expected_message not in combined:
            fail("default dry-run did not fail at the expected AGENTS policy marker gate", report)

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

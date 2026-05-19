#!/usr/bin/env python3
"""Host-only regression tests for the V317 live executor guard."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v352-v317-live-executor-regression")
EXECUTOR = Path("scripts/revalidation/wifi_v317_live_executor.py")
APPROVAL_PHRASE = "approve v317 minimal private property namespace proof only; no daemon start and no Wi-Fi bring-up"
WRONG_APPROVAL_PHRASE = "approve v317 minimal private property namespace proof only"


@dataclass(frozen=True)
class ExecutorCase:
    name: str
    args: list[str]
    expected_decisions: tuple[str, ...]
    expected_rc: int
    expected_live_approved: bool
    expected_device_commands: bool
    expected_device_mutations: bool
    expected_step_count: int | None


@dataclass
class ExecutorCaseResult:
    name: str
    status: str
    rc: int
    expected_rc: int
    decision: str
    expected_decisions: list[str]
    pass_value: bool | None
    live_execution_approved: bool | None
    device_commands_executed: bool | None
    device_mutations: bool | None
    step_count: int
    expected_step_count: int | None
    stdout_path: str
    manifest_path: str
    detail: str


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("run")
    return parser.parse_args()


def cases() -> list[ExecutorCase]:
    return [
        ExecutorCase(
            "run-no-approval",
            ["run"],
            ("v317-live-executor-approval-required",),
            1,
            False,
            False,
            False,
            0,
        ),
        ExecutorCase(
            "run-phrase-only",
            ["--approval-phrase", APPROVAL_PHRASE, "run"],
            ("v317-live-executor-approval-required",),
            1,
            False,
            False,
            False,
            0,
        ),
        ExecutorCase(
            "run-flags-only",
            ["--allow-device-mutation", "--assume-yes", "run"],
            ("v317-live-executor-approval-required",),
            1,
            False,
            False,
            False,
            0,
        ),
        ExecutorCase(
            "run-phrase-allow-only",
            ["--approval-phrase", APPROVAL_PHRASE, "--allow-device-mutation", "run"],
            ("v317-live-executor-approval-required",),
            1,
            False,
            False,
            False,
            0,
        ),
        ExecutorCase(
            "run-phrase-assume-only",
            ["--approval-phrase", APPROVAL_PHRASE, "--assume-yes", "run"],
            ("v317-live-executor-approval-required",),
            1,
            False,
            False,
            False,
            0,
        ),
        ExecutorCase(
            "run-wrong-phrase-full-flags",
            ["--approval-phrase", WRONG_APPROVAL_PHRASE, "--allow-device-mutation", "--assume-yes", "run"],
            ("v317-live-executor-approval-required",),
            1,
            False,
            False,
            False,
            0,
        ),
        ExecutorCase(
            "cleanup-no-approval",
            ["cleanup"],
            ("v317-live-executor-approval-required",),
            1,
            False,
            False,
            False,
            0,
        ),
        ExecutorCase(
            "cleanup-phrase-only",
            ["--approval-phrase", APPROVAL_PHRASE, "cleanup"],
            ("v317-live-executor-approval-required",),
            1,
            False,
            False,
            False,
            0,
        ),
        ExecutorCase(
            "cleanup-flags-only",
            ["--allow-device-mutation", "--assume-yes", "cleanup"],
            ("v317-live-executor-approval-required",),
            1,
            False,
            False,
            False,
            0,
        ),
        ExecutorCase(
            "cleanup-phrase-allow-only",
            ["--approval-phrase", APPROVAL_PHRASE, "--allow-device-mutation", "cleanup"],
            ("v317-live-executor-approval-required",),
            1,
            False,
            False,
            False,
            0,
        ),
        ExecutorCase(
            "cleanup-phrase-assume-only",
            ["--approval-phrase", APPROVAL_PHRASE, "--assume-yes", "cleanup"],
            ("v317-live-executor-approval-required",),
            1,
            False,
            False,
            False,
            0,
        ),
        ExecutorCase(
            "cleanup-wrong-phrase-full-flags",
            ["--approval-phrase", WRONG_APPROVAL_PHRASE, "--allow-device-mutation", "--assume-yes", "cleanup"],
            ("v317-live-executor-approval-required",),
            1,
            False,
            False,
            False,
            0,
        ),
        ExecutorCase(
            "plan-current-state",
            ["plan"],
            ("v317-live-executor-plan-ready", "v317-live-executor-readiness-blocked"),
            -1,
            False,
            False,
            False,
            None,
        ),
    ]


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def run_case(case: ExecutorCase, case_dir: Path, repo_dirty: bool) -> ExecutorCaseResult:
    out_dir = case_dir / "executor-output"
    stdout_path = case_dir / "executor-stdout.txt"
    argv = [
        sys.executable,
        str(repo_path(EXECUTOR)),
        "--out-dir",
        str(out_dir),
        *case.args,
    ]
    result = subprocess.run(
        argv,
        cwd=repo_path(Path(".")),
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=240,
    )
    stdout_path.write_text(result.stdout, encoding="utf-8")
    manifest_path = out_dir / "manifest.json"
    manifest = load_json(manifest_path)
    decision = str(manifest.get("decision") or "missing")
    steps = manifest.get("steps") if isinstance(manifest.get("steps"), list) else []

    expected_rc = case.expected_rc
    expected_decisions = case.expected_decisions
    if case.name == "plan-current-state":
        if repo_dirty:
            expected_rc = 1
            expected_decisions = ("v317-live-executor-readiness-blocked",)
        else:
            expected_rc = 0
            expected_decisions = ("v317-live-executor-plan-ready",)

    ok = (
        result.returncode == expected_rc
        and decision in expected_decisions
        and bool(manifest.get("live_execution_approved")) is case.expected_live_approved
        and bool(manifest.get("device_commands_executed")) is case.expected_device_commands
        and bool(manifest.get("device_mutations")) is case.expected_device_mutations
        and (case.expected_step_count is None or len(steps) == case.expected_step_count)
    )
    detail = (
        f"rc={result.returncode} expected_rc={expected_rc} decision={decision} "
        f"live_execution_approved={manifest.get('live_execution_approved')} "
        f"device_commands_executed={manifest.get('device_commands_executed')} "
        f"device_mutations={manifest.get('device_mutations')} steps={len(steps)}"
    )
    return ExecutorCaseResult(
        name=case.name,
        status="pass" if ok else "blocked",
        rc=result.returncode,
        expected_rc=expected_rc,
        decision=decision,
        expected_decisions=list(expected_decisions),
        pass_value=manifest.get("pass"),
        live_execution_approved=manifest.get("live_execution_approved"),
        device_commands_executed=manifest.get("device_commands_executed"),
        device_mutations=manifest.get("device_mutations"),
        step_count=len(steps),
        expected_step_count=case.expected_step_count,
        stdout_path=str(stdout_path),
        manifest_path=str(manifest_path),
        detail=detail,
    )


def decide(results: list[ExecutorCaseResult]) -> tuple[str, bool, str, str, list[str]]:
    blocked = [item.name for item in results if item.status != "pass"]
    if blocked:
        return (
            "v317-live-executor-regression-blocked",
            False,
            "blocked cases: " + ", ".join(blocked),
            "fix V351 executor guard before requesting live approval",
            blocked,
        )
    return (
        "v317-live-executor-regression-pass",
        True,
        "all V351 executor guard cases behave as expected",
        "V317 live proof remains blocked by exact approval phrase",
        ["exact-v317-approval-phrase"],
    )


def build_manifest(args: argparse.Namespace, results: list[ExecutorCaseResult]) -> dict[str, Any]:
    decision, pass_ok, reason, next_step, blockers = decide(results)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "cases": [asdict(item) for item in results],
        "remaining_blockers": blockers,
        "device_commands_executed": False,
        "device_mutations": False,
        "notes": [
            "No approved run/cleanup case is executed.",
            "The plan case may pass on clean HEAD or block on dirty HEAD; both are expected according to tree state.",
        ],
    }


def render_summary(manifest: dict[str, Any]) -> str:
    rows = [
        [
            item["name"],
            item["status"],
            str(item["rc"]),
            item["decision"],
            str(item["live_execution_approved"]),
            str(item["device_commands_executed"]),
            str(item["device_mutations"]),
            item["detail"],
        ]
        for item in manifest["cases"]
    ]
    return "\n".join([
        "# v352 V317 Live Executor Regression",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- device_mutations: `{manifest['device_mutations']}`",
        "",
        "## Remaining Blockers",
        "",
        "\n".join(f"- `{item}`" for item in manifest["remaining_blockers"]) or "- none",
        "",
        "## Cases",
        "",
        markdown_table([
            "case",
            "status",
            "rc",
            "decision",
            "live_ok",
            "device_cmd",
            "device_mut",
            "detail",
        ], rows),
        "",
    ])


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    case_root = store.run_dir / "cases"
    case_root.mkdir(mode=0o700, exist_ok=True)
    host = collect_host_metadata()
    repo_dirty = bool(host.get("git_dirty"))
    results = [run_case(case, case_root / case.name, repo_dirty) for case in cases()]
    manifest = build_manifest(args, results)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

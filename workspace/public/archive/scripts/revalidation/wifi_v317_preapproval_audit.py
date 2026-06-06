#!/usr/bin/env python3
"""Host-only pre-approval audit for the V317 live proof gate."""

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


DEFAULT_OUT_DIR = Path("tmp/wifi/v357-v317-preapproval-audit")
APPROVAL_BLOCKER = "exact-v317-approval-phrase"
EXECUTOR_SCRIPT = "scripts/revalidation/wifi_v317_live_executor.py"
REQUIRED_REGRESSION_CASES = (
    "run-no-approval",
    "run-phrase-only",
    "run-flags-only",
    "run-phrase-allow-only",
    "run-phrase-assume-only",
    "run-wrong-phrase-full-flags",
    "cleanup-no-approval",
    "cleanup-phrase-only",
    "cleanup-flags-only",
    "cleanup-phrase-allow-only",
    "cleanup-phrase-assume-only",
    "cleanup-wrong-phrase-full-flags",
    "plan-current-state",
)


@dataclass(frozen=True)
class AuditStep:
    name: str
    argv: list[str]
    manifest_path: Path
    expected_decision: str


@dataclass
class AuditResult:
    name: str
    status: str
    rc: int
    decision: str
    expected_decision: str
    pass_value: bool | None
    evidence_head: str
    evidence_dirty: bool | None
    remaining_blockers: list[str]
    device_commands_executed: bool | None
    device_mutations: bool | None
    live_execution_approved: bool | None
    stdout_path: str
    manifest_path: str
    checks: list[str]
    failures: list[str]


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("check")
    return parser.parse_args()


def script(path: str) -> str:
    return str(repo_path(Path(path)))


def steps() -> list[AuditStep]:
    return [
        AuditStep(
            "v349-final-readiness",
            [
                sys.executable,
                script("scripts/revalidation/wifi_v317_final_readiness.py"),
                "--out-dir",
                "tmp/wifi/v349-v317-final-readiness",
                "check",
            ],
            Path("tmp/wifi/v349-v317-final-readiness/manifest.json"),
            "v317-final-readiness-awaiting-approval",
        ),
        AuditStep(
            "v350-operator-checklist",
            [
                sys.executable,
                script("scripts/revalidation/wifi_v317_operator_checklist.py"),
                "--out-dir",
                "tmp/wifi/v350-v317-operator-checklist",
                "build",
            ],
            Path("tmp/wifi/v350-v317-operator-checklist/manifest.json"),
            "v317-operator-checklist-ready",
        ),
        AuditStep(
            "v351-live-executor-plan",
            [
                sys.executable,
                script("scripts/revalidation/wifi_v317_live_executor.py"),
                "--out-dir",
                "tmp/wifi/v351-v317-live-executor",
                "plan",
            ],
            Path("tmp/wifi/v351-v317-live-executor/manifest.json"),
            "v317-live-executor-plan-ready",
        ),
        AuditStep(
            "v352-executor-regression",
            [
                sys.executable,
                script("scripts/revalidation/wifi_v317_live_executor_regression.py"),
                "--out-dir",
                "tmp/wifi/v352-v317-live-executor-regression",
                "run",
            ],
            Path("tmp/wifi/v352-v317-live-executor-regression/manifest.json"),
            "v317-live-executor-regression-pass",
        ),
    ]


def load_manifest(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {"present": False, "path": str(resolved)}
    payload = json.loads(resolved.read_text(encoding="utf-8"))
    payload["present"] = True
    payload["path"] = str(resolved)
    return payload


def host_head(manifest: dict[str, Any]) -> str:
    host = manifest.get("host") if isinstance(manifest.get("host"), dict) else {}
    return str(host.get("git_head") or "")


def host_dirty(manifest: dict[str, Any]) -> bool | None:
    host = manifest.get("host") if isinstance(manifest.get("host"), dict) else {}
    value = host.get("git_dirty")
    return bool(value) if value is not None else None


def pass_value(manifest: dict[str, Any]) -> bool | None:
    if "pass" in manifest:
        return bool(manifest.get("pass"))
    if "audit_pass" in manifest:
        return bool(manifest.get("audit_pass"))
    return None


def blockers(manifest: dict[str, Any]) -> list[str]:
    value = manifest.get("remaining_blockers")
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def bool_field(manifest: dict[str, Any], name: str) -> bool | None:
    if name not in manifest:
        return None
    return bool(manifest.get(name))


def regression_case_statuses(manifest: dict[str, Any]) -> dict[str, str]:
    cases = manifest.get("cases")
    if not isinstance(cases, list):
        return {}
    result: dict[str, str] = {}
    for item in cases:
        if not isinstance(item, dict):
            continue
        result[str(item.get("name") or "")] = str(item.get("status") or "")
    return result


def add_common_checks(
    failures: list[str],
    checks: list[str],
    step: AuditStep,
    manifest: dict[str, Any],
    rc: int,
    current_head: str,
) -> None:
    expected = {
        "tool rc": rc == 0,
        "manifest present": bool(manifest.get("present")),
        "decision": manifest.get("decision") == step.expected_decision,
        "pass true": pass_value(manifest) is True,
        "clean head": host_head(manifest) == current_head and host_dirty(manifest) is False,
        "approval blocker only": blockers(manifest) == [APPROVAL_BLOCKER],
        "no device commands": bool_field(manifest, "device_commands_executed") is False,
        "no device mutations": bool_field(manifest, "device_mutations") is False,
    }
    for name, ok in expected.items():
        checks.append(f"{name}={'pass' if ok else 'blocked'}")
        if not ok:
            failures.append(name)


def add_step_specific_checks(failures: list[str], checks: list[str], step: AuditStep, manifest: dict[str, Any]) -> None:
    if step.name == "v350-operator-checklist":
        command = str(manifest.get("executor_run_command") or "")
        ok = EXECUTOR_SCRIPT in command
        checks.append(f"executor preferred={'pass' if ok else 'blocked'}")
        if not ok:
            failures.append("executor preferred")
    if step.name == "v351-live-executor-plan":
        ok = bool_field(manifest, "live_execution_approved") is False
        checks.append(f"live execution not approved={'pass' if ok else 'blocked'}")
        if not ok:
            failures.append("live execution not approved")
    if step.name == "v352-executor-regression":
        statuses = regression_case_statuses(manifest)
        missing = [name for name in REQUIRED_REGRESSION_CASES if statuses.get(name) != "pass"]
        ok = not missing
        checks.append(f"approval matrix cases={'pass' if ok else 'blocked'}")
        if missing:
            failures.append("approval matrix cases missing/pass failed: " + ", ".join(missing))


def run_step(step: AuditStep, transcript_dir: Path, current_head: str) -> AuditResult:
    stdout_path = transcript_dir / f"{step.name}.txt"
    result = subprocess.run(
        step.argv,
        cwd=repo_path(Path(".")),
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=600,
    )
    stdout_path.write_text(result.stdout, encoding="utf-8")
    manifest = load_manifest(step.manifest_path)
    checks: list[str] = []
    failures: list[str] = []
    add_common_checks(failures, checks, step, manifest, result.returncode, current_head)
    add_step_specific_checks(failures, checks, step, manifest)
    return AuditResult(
        name=step.name,
        status="pass" if not failures else "blocked",
        rc=result.returncode,
        decision=str(manifest.get("decision") or "missing"),
        expected_decision=step.expected_decision,
        pass_value=pass_value(manifest),
        evidence_head=host_head(manifest),
        evidence_dirty=host_dirty(manifest),
        remaining_blockers=blockers(manifest),
        device_commands_executed=bool_field(manifest, "device_commands_executed"),
        device_mutations=bool_field(manifest, "device_mutations"),
        live_execution_approved=bool_field(manifest, "live_execution_approved"),
        stdout_path=str(stdout_path),
        manifest_path=str(repo_path(step.manifest_path)),
        checks=checks,
        failures=failures,
    )


def decide(results: list[AuditResult]) -> tuple[str, bool, str, str, list[str]]:
    blocked = [item.name for item in results if item.status != "pass"]
    if blocked:
        return (
            "v317-preapproval-audit-blocked",
            False,
            "blocked pre-approval checks: " + ", ".join(blocked),
            "repair host-only gate evidence before requesting V317 live approval",
            blocked,
        )
    return (
        "v317-preapproval-audit-awaiting-approval",
        True,
        "all host-only V317 gates pass; only the exact approval phrase remains",
        "run V351 executor only after the exact V317 approval phrase is provided",
        [APPROVAL_BLOCKER],
    )


def build_manifest(args: argparse.Namespace, results: list[AuditResult]) -> dict[str, Any]:
    decision, pass_ok, reason, next_step, blockers_value = decide(results)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "steps": [asdict(item) for item in results],
        "remaining_blockers": blockers_value,
        "approval_phrase_required": APPROVAL_BLOCKER,
        "live_execution_approved": False,
        "device_commands_executed": False,
        "device_mutations": False,
        "notes": [
            "This script runs only host-side readiness/checklist/executor-plan/regression tools.",
            "It does not execute V317 live proof, cleanup, daemon start, scan, connect, or Wi-Fi bring-up.",
            "The V351 executor remains the preferred live path after exact approval.",
        ],
    }


def render_summary(manifest: dict[str, Any]) -> str:
    rows = [
        [
            item["name"],
            item["status"],
            str(item["rc"]),
            item["decision"],
            str(item["pass_value"]),
            str(item["evidence_dirty"]),
            "; ".join(item["failures"]) or "none",
        ]
        for item in manifest["steps"]
    ]
    return "\n".join([
        "# v357 V317 Pre-Approval Audit",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- live_execution_approved: `{manifest['live_execution_approved']}`",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- device_mutations: `{manifest['device_mutations']}`",
        "",
        "## Remaining Blockers",
        "",
        "\n".join(f"- `{item}`" for item in manifest["remaining_blockers"]) or "- none",
        "",
        "## Steps",
        "",
        markdown_table(["step", "status", "rc", "decision", "pass", "dirty", "failures"], rows),
        "",
    ])


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    transcript_dir = store.mkdir("transcripts")
    host = collect_host_metadata()
    current_head = str(host.get("git_head") or "")
    results = [run_step(step, transcript_dir, current_head) for step in steps()]
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

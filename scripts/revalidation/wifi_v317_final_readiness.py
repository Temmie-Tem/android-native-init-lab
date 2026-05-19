#!/usr/bin/env python3
"""Final host-only readiness aggregation before V317 live proof."""

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


DEFAULT_OUT_DIR = Path("tmp/wifi/v349-v317-final-readiness")
APPROVAL_BLOCKER = "exact-v317-approval-phrase"


@dataclass(frozen=True)
class ReadinessStep:
    name: str
    argv: list[str]
    manifest_path: Path
    expected_decision: str


@dataclass
class ReadinessResult:
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
    stdout_path: str
    manifest_path: str
    detail: str


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("check")
    return parser.parse_args()


def py_script(path: str) -> str:
    return str(repo_path(Path(path)))


def steps() -> list[ReadinessStep]:
    return [
        ReadinessStep(
            "v344-gate-refresh",
            [
                sys.executable,
                py_script("scripts/revalidation/wifi_v317_gate_refresh.py"),
                "--run-approved-preflight",
                "--out-dir",
                "tmp/wifi/v344-v317-gate-refresh",
                "refresh",
            ],
            Path("tmp/wifi/v344-v317-gate-refresh/manifest.json"),
            "v317-gate-refresh-ready",
        ),
        ReadinessStep(
            "v345-router-regression",
            [
                sys.executable,
                py_script("scripts/revalidation/wifi_post_v317_router_regression.py"),
                "--out-dir",
                "tmp/wifi/v345-post-v317-router-regression",
                "run",
            ],
            Path("tmp/wifi/v345-post-v317-router-regression/manifest.json"),
            "post-v317-router-regression-pass",
        ),
        ReadinessStep(
            "v348-command-contract",
            [
                sys.executable,
                py_script("scripts/revalidation/wifi_v317_handoff_command_contract.py"),
                "--out-dir",
                "tmp/wifi/v348-v317-handoff-command-contract",
                "check",
            ],
            Path("tmp/wifi/v348-v317-handoff-command-contract/manifest.json"),
            "v317-handoff-command-contract-pass",
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


def pass_value(manifest: dict[str, Any]) -> bool | None:
    if "pass" in manifest:
        return bool(manifest.get("pass"))
    if "audit_pass" in manifest:
        return bool(manifest.get("audit_pass"))
    return None


def host_head(manifest: dict[str, Any]) -> str:
    host = manifest.get("host") if isinstance(manifest.get("host"), dict) else {}
    return str(host.get("git_head") or "")


def host_dirty(manifest: dict[str, Any]) -> bool | None:
    host = manifest.get("host") if isinstance(manifest.get("host"), dict) else {}
    value = host.get("git_dirty")
    return bool(value) if value is not None else None


def no_device_execution(manifest: dict[str, Any]) -> bool:
    return not bool(manifest.get("device_commands_executed")) and not bool(manifest.get("device_mutations"))


def run_step(step: ReadinessStep, transcript_dir: Path, current_head: str) -> ReadinessResult:
    stdout_path = transcript_dir / f"{step.name}.txt"
    result = subprocess.run(
        step.argv,
        cwd=repo_path(Path(".")),
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=180,
    )
    stdout_path.write_text(result.stdout, encoding="utf-8")
    manifest = load_manifest(step.manifest_path)
    decision = str(manifest.get("decision") or "missing")
    actual_pass = pass_value(manifest)
    evidence_head = host_head(manifest)
    evidence_dirty = host_dirty(manifest)
    remaining_blockers = manifest.get("remaining_blockers")
    if not isinstance(remaining_blockers, list):
        remaining_blockers = []
    ok = (
        result.returncode == 0
        and bool(manifest.get("present"))
        and decision == step.expected_decision
        and actual_pass is True
        and evidence_head == current_head
        and evidence_dirty is False
        and no_device_execution(manifest)
        and remaining_blockers == [APPROVAL_BLOCKER]
    )
    detail = (
        f"rc={result.returncode} decision={decision} pass={actual_pass} "
        f"head={evidence_head} current_head={current_head} dirty={evidence_dirty} "
        f"remaining_blockers={remaining_blockers}"
    )
    return ReadinessResult(
        name=step.name,
        status="pass" if ok else "blocked",
        rc=result.returncode,
        decision=decision,
        expected_decision=step.expected_decision,
        pass_value=actual_pass,
        evidence_head=evidence_head,
        evidence_dirty=evidence_dirty,
        remaining_blockers=[str(item) for item in remaining_blockers],
        device_commands_executed=manifest.get("device_commands_executed"),
        device_mutations=manifest.get("device_mutations"),
        stdout_path=str(stdout_path),
        manifest_path=str(repo_path(step.manifest_path)),
        detail=detail,
    )


def decide(results: list[ReadinessResult]) -> tuple[str, bool, str, str, list[str]]:
    blocked = [item.name for item in results if item.status != "pass"]
    if blocked:
        return (
            "v317-final-readiness-blocked",
            False,
            "blocked readiness steps: " + ", ".join(blocked),
            "repair blocked readiness evidence before requesting V317 live approval",
            blocked,
        )
    return (
        "v317-final-readiness-awaiting-approval",
        True,
        "all host-only readiness checks pass; live proof remains approval-gated",
        "provide exact V317 approval phrase only if accepting the approved scope",
        [APPROVAL_BLOCKER],
    )


def build_manifest(args: argparse.Namespace, results: list[ReadinessResult]) -> dict[str, Any]:
    decision, pass_ok, reason, next_step, blockers = decide(results)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "steps": [asdict(item) for item in results],
        "remaining_blockers": blockers,
        "live_execution_approved": False,
        "device_commands_executed": False,
        "device_mutations": False,
        "notes": [
            "This aggregator runs only host-side readiness scripts.",
            "It does not execute V317 live proof, daemon start, or Wi-Fi bring-up.",
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
            item["detail"],
        ]
        for item in manifest["steps"]
    ]
    return "\n".join([
        "# v349 V317 Final Readiness",
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
        markdown_table(["step", "status", "rc", "decision", "pass", "detail"], rows),
        "",
    ])


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    transcript_dir = store.run_dir / "transcripts"
    transcript_dir.mkdir(mode=0o700, exist_ok=True)
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

#!/usr/bin/env python3
"""Final host-only readiness aggregation before V382 deploy/live execution."""

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


DEFAULT_OUT_DIR = Path("tmp/wifi/v382-final-readiness")
DEPLOY_APPROVAL_BLOCKER = "exact-v382-deploy-approval-phrase"
LIVE_APPROVAL_BLOCKER = "exact-v373-service-manager-approval-phrase"


@dataclass(frozen=True)
class ReadinessStep:
    name: str
    argv: list[str]
    manifest_path: Path
    expected_decision: str
    expected_pass: bool
    allowed_blockers: tuple[str, ...]
    require_no_device_execution: bool
    require_no_device_mutation: bool
    require_no_daemon_start: bool
    require_no_wifi_bringup: bool


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
    daemon_start_executed: bool | None
    wifi_bringup_executed: bool | None
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
            "v382-deploy-plan",
            [
                sys.executable,
                py_script("scripts/revalidation/wifi_execns_helper_v14_deploy_preflight.py"),
                "--out-dir",
                "tmp/wifi/v382-final-readiness-deploy-plan",
                "plan",
            ],
            Path("tmp/wifi/v382-final-readiness-deploy-plan/manifest.json"),
            "execns-helper-v14-deploy-plan-ready",
            True,
            (),
            require_no_device_execution=True,
            require_no_device_mutation=True,
            require_no_daemon_start=True,
            require_no_wifi_bringup=True,
        ),
        ReadinessStep(
            "v382-deploy-preflight",
            [
                sys.executable,
                py_script("scripts/revalidation/wifi_execns_helper_v14_deploy_preflight.py"),
                "--out-dir",
                "tmp/wifi/v382-final-readiness-deploy-preflight",
                "preflight",
            ],
            Path("tmp/wifi/v382-final-readiness-deploy-preflight/manifest.json"),
            "execns-helper-v14-deploy-blocked",
            False,
            ("remote-helper-v14",),
            require_no_device_execution=False,
            require_no_device_mutation=True,
            require_no_daemon_start=True,
            require_no_wifi_bringup=True,
        ),
        ReadinessStep(
            "v382-live-plan",
            [
                sys.executable,
                py_script("scripts/revalidation/wifi_service_manager_start_only_v382_live_runner.py"),
                "--out-dir",
                "tmp/wifi/v382-final-readiness-live-plan",
                "plan",
            ],
            Path("tmp/wifi/v382-final-readiness-live-plan/manifest.json"),
            "service-manager-start-only-live-plan-ready",
            True,
            (),
            require_no_device_execution=True,
            require_no_device_mutation=True,
            require_no_daemon_start=True,
            require_no_wifi_bringup=True,
        ),
        ReadinessStep(
            "v382-live-noapproval",
            [
                sys.executable,
                py_script("scripts/revalidation/wifi_service_manager_start_only_v382_live_runner.py"),
                "--out-dir",
                "tmp/wifi/v382-final-readiness-live-noapproval",
                "run",
            ],
            Path("tmp/wifi/v382-final-readiness-live-noapproval/manifest.json"),
            "service-manager-start-only-live-approval-required",
            True,
            (),
            require_no_device_execution=True,
            require_no_device_mutation=True,
            require_no_daemon_start=True,
            require_no_wifi_bringup=True,
        ),
        ReadinessStep(
            "v382-result-router-regression",
            [
                sys.executable,
                py_script("scripts/revalidation/wifi_service_manager_start_only_v382_result_router.py"),
                "--out-dir",
                "tmp/wifi/v382-final-readiness-router-regression",
                "regression",
            ],
            Path("tmp/wifi/v382-final-readiness-router-regression/manifest.json"),
            "service-manager-start-only-router-regression-pass",
            True,
            (),
            require_no_device_execution=True,
            require_no_device_mutation=True,
            require_no_daemon_start=False,
            require_no_wifi_bringup=False,
        ),
        ReadinessStep(
            "v382-result-router-noapproval",
            [
                sys.executable,
                py_script("scripts/revalidation/wifi_service_manager_start_only_v382_result_router.py"),
                "--out-dir",
                "tmp/wifi/v382-final-readiness-router-noapproval",
                "--v376-manifest",
                "tmp/wifi/v382-final-readiness-live-noapproval/manifest.json",
                "route",
            ],
            Path("tmp/wifi/v382-final-readiness-router-noapproval/manifest.json"),
            "service-manager-start-only-router-awaiting-approval",
            True,
            (LIVE_APPROVAL_BLOCKER,),
            require_no_device_execution=True,
            require_no_device_mutation=True,
            require_no_daemon_start=False,
            require_no_wifi_bringup=False,
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
    return None


def host_head(manifest: dict[str, Any]) -> str:
    host = manifest.get("host") if isinstance(manifest.get("host"), dict) else {}
    return str(host.get("git_head") or "")


def host_dirty(manifest: dict[str, Any]) -> bool | None:
    host = manifest.get("host") if isinstance(manifest.get("host"), dict) else {}
    value = host.get("git_dirty")
    return bool(value) if value is not None else None


def manifest_blockers(manifest: dict[str, Any]) -> list[str]:
    blockers = manifest.get("remaining_blockers")
    if isinstance(blockers, list):
        return [str(item) for item in blockers]
    checks = manifest.get("checks")
    if isinstance(checks, list):
        return [
            str(check.get("name"))
            for check in checks
            if check.get("severity") in {"blocker", "deploy"} and check.get("status") != "pass"
        ]
    return []


def flag_is_false_or_absent(value: Any) -> bool:
    return not bool(value)


def run_step(step: ReadinessStep, transcript_dir: Path, current_head: str) -> ReadinessResult:
    stdout_path = transcript_dir / f"{step.name}.txt"
    result = subprocess.run(
        step.argv,
        cwd=repo_path(Path(".")),
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=240,
    )
    stdout_path.write_text(result.stdout, encoding="utf-8")
    manifest = load_manifest(step.manifest_path)
    decision = str(manifest.get("decision") or "missing")
    actual_pass = pass_value(manifest)
    evidence_head = host_head(manifest)
    evidence_dirty = host_dirty(manifest)
    blockers = manifest_blockers(manifest)
    device_commands_executed = manifest.get("device_commands_executed")
    device_mutations = manifest.get("device_mutations")
    daemon_start_executed = manifest.get("daemon_start_executed")
    wifi_bringup_executed = manifest.get("wifi_bringup_executed")
    blocker_set_ok = sorted(blockers) == sorted(step.allowed_blockers)
    device_exec_ok = not step.require_no_device_execution or flag_is_false_or_absent(device_commands_executed)
    device_mutation_ok = not step.require_no_device_mutation or flag_is_false_or_absent(device_mutations)
    daemon_ok = not step.require_no_daemon_start or flag_is_false_or_absent(daemon_start_executed)
    wifi_ok = not step.require_no_wifi_bringup or flag_is_false_or_absent(wifi_bringup_executed)
    ok = (
        result.returncode == (0 if step.expected_pass else 1)
        and bool(manifest.get("present"))
        and decision == step.expected_decision
        and actual_pass is step.expected_pass
        and evidence_head == current_head
        and evidence_dirty is False
        and blocker_set_ok
        and device_exec_ok
        and device_mutation_ok
        and daemon_ok
        and wifi_ok
    )
    detail = (
        f"rc={result.returncode} decision={decision} pass={actual_pass} "
        f"head={evidence_head} current_head={current_head} dirty={evidence_dirty} "
        f"blockers={blockers} device_exec={device_commands_executed} "
        f"device_mut={device_mutations} daemon={daemon_start_executed} wifi={wifi_bringup_executed}"
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
        remaining_blockers=blockers,
        device_commands_executed=device_commands_executed,
        device_mutations=device_mutations,
        daemon_start_executed=daemon_start_executed,
        wifi_bringup_executed=wifi_bringup_executed,
        stdout_path=str(stdout_path),
        manifest_path=str(repo_path(step.manifest_path)),
        detail=detail,
    )


def decide(results: list[ReadinessResult]) -> tuple[str, bool, str, str, list[str]]:
    blocked = [item.name for item in results if item.status != "pass"]
    if blocked:
        return (
            "v382-final-readiness-blocked",
            False,
            "blocked readiness steps: " + ", ".join(blocked),
            "repair blocked readiness evidence before requesting V382 deploy approval",
            blocked,
        )
    return (
        "v382-final-readiness-awaiting-deploy-approval",
        True,
        "all host-only readiness checks pass; deploy/live remain approval-gated",
        "provide exact V382 deploy approval phrase only if accepting the approved scope",
        [DEPLOY_APPROVAL_BLOCKER, LIVE_APPROVAL_BLOCKER],
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
        "deploy_execution_approved": False,
        "live_execution_approved": False,
        "device_commands_executed": False,
        "device_mutations": False,
        "daemon_start_executed": False,
        "wifi_bringup_executed": False,
        "required_deploy_approval_phrase": "approve v382 deploy execns helper v14 only; no daemon start and no Wi-Fi bring-up",
        "required_live_approval_phrase": "approve v373 service-manager start-only smoke only; no Wi-Fi HAL start and no Wi-Fi bring-up",
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
        "# V382 Final Readiness",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- deploy_execution_approved: `{manifest['deploy_execution_approved']}`",
        f"- live_execution_approved: `{manifest['live_execution_approved']}`",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- device_mutations: `{manifest['device_mutations']}`",
        f"- daemon_start_executed: `{manifest['daemon_start_executed']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
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
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"device_mutations: {manifest['device_mutations']}")
    print(f"daemon_start_executed: {manifest['daemon_start_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

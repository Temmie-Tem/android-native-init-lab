#!/usr/bin/env python3
"""Host-only V384 pre-approval freshness audit.

The audit verifies that the V384 helper artifact, wrappers, approval phrases,
and no-approval executor behavior are still fresh before an operator runs the
approval-gated deploy/live flow. It executes no bridge command and performs no
device mutation.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v384-preapproval-audit")
EXPECTED_HELPER = Path("tmp/wifi/v384-a90_android_execns_probe-v15/a90_android_execns_probe")
EXPECTED_SHA256 = "dfd543c02ccefbbbcf2fe0eb7ee168b40d40363927a63104c7aef0b9aed0bb16"
DEPLOY_APPROVAL_PHRASE = "approve v384 deploy execns helper v15 only; no daemon start and no Wi-Fi bring-up"
LIVE_APPROVAL_PHRASE = "approve v384 service-manager ptrace-lite crash capture only; no Wi-Fi HAL start and no Wi-Fi bring-up"
REQUIRED_FILES = (
    "stage3/linux_init/helpers/a90_android_execns_probe.c",
    "scripts/revalidation/wifi_execns_helper_v15_deploy_preflight.py",
    "scripts/revalidation/wifi_service_manager_start_only_v384_live_runner.py",
    "scripts/revalidation/wifi_v384_deploy_live_executor.py",
    "scripts/revalidation/wifi_service_manager_runtime_gap_classifier.py",
    "docs/operations/WIFI_V384_PTRACE_LIVE_HANDOFF.md",
    "docs/reports/NATIVE_INIT_V384_SERVICEMANAGER_CRASH_CAPTURE_2026-05-20.md",
    "docs/reports/NATIVE_INIT_V384_DEPLOY_LIVE_EXECUTOR_2026-05-20.md",
    "docs/reports/NATIVE_INIT_V384_PREFLIGHT_READY_2026-05-20.md",
)
PYTHON_FILES = (
    "scripts/revalidation/wifi_execns_helper_v15_deploy_preflight.py",
    "scripts/revalidation/wifi_service_manager_start_only_live_runner.py",
    "scripts/revalidation/wifi_service_manager_start_only_v384_live_runner.py",
    "scripts/revalidation/wifi_service_manager_runtime_gap_classifier.py",
    "scripts/revalidation/wifi_v384_deploy_live_executor.py",
    "scripts/revalidation/wifi_v384_preapproval_audit.py",
)


@dataclass
class Check:
    name: str
    status: str
    severity: str
    detail: str
    evidence: list[str]
    next_step: str


@dataclass
class Step:
    name: str
    command: str
    ok: bool
    rc: int | None
    duration_sec: float
    file: str
    error: str


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--timeout", type=int, default=1800)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("audit")
    return parser.parse_args()


def add_check(checks: list[Check], name: str, status: str, severity: str, detail: str,
              evidence: list[str] | None = None, next_step: str = "") -> None:
    checks.append(Check(name, status, severity, detail, evidence or [], next_step))


def run_process(command: list[str], timeout: int) -> tuple[int | None, str, str, float]:
    started = time.monotonic()
    try:
        result = subprocess.run(
            command,
            cwd=repo_path(Path(".")),
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
        )
        return result.returncode, result.stdout, "", time.monotonic() - started
    except subprocess.TimeoutExpired as exc:
        text = exc.stdout if isinstance(exc.stdout, str) else ""
        return None, text, f"timeout after {timeout}s", time.monotonic() - started
    except Exception as exc:  # noqa: BLE001 - audit preserves unexpected errors
        return None, "", str(exc), time.monotonic() - started


def run_step(store: EvidenceStore, name: str, command: list[str], timeout: int) -> Step:
    rc, text, error, duration = run_process(command, timeout)
    body = "\n".join(["$ " + " ".join(command), text.rstrip() if text else error.rstrip(), f"rc={rc}", ""])
    path = store.write_text(f"steps/{name}.txt", body)
    return Step(name, " ".join(command), rc == 0, rc, duration, str(path.relative_to(store.run_dir)), error)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"present": False, "path": str(path)}
    data = json.loads(path.read_text(encoding="utf-8"))
    data["present"] = True
    data["path"] = str(path)
    return data


def command_false_manifest_ok(manifest: dict[str, Any], expected_decision: str) -> bool:
    return (
        manifest.get("present") is True
        and manifest.get("decision") == expected_decision
        and manifest.get("pass") is True
        and manifest.get("device_commands_executed") is False
        and manifest.get("device_mutations") is False
        and manifest.get("daemon_start_executed") is False
        and manifest.get("wifi_bringup_executed") is False
    )


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    checks: list[Check] = []
    steps: list[Step] = []

    status_step = run_step(store, "git-status", ["git", "status", "--short"], 30)
    steps.append(status_step)
    status_text = store.path(status_step.file).read_text(encoding="utf-8", errors="replace")
    dirty_lines = [line for line in status_text.splitlines() if line and not line.startswith("$") and not line.startswith("rc=")]
    add_check(checks, "git-clean", "pass" if not dirty_lines else "blocked", "blocker", f"dirty_lines={len(dirty_lines)}", dirty_lines[:20], "commit or revert changes before approval execution")

    missing_files = [path for path in REQUIRED_FILES if not repo_path(Path(path)).exists()]
    add_check(checks, "required-files", "pass" if not missing_files else "blocked", "blocker", f"missing={len(missing_files)}", missing_files, "restore required V384 files")

    helper_path = repo_path(EXPECTED_HELPER)
    helper_exists = helper_path.exists()
    helper_sha = sha256_file(helper_path) if helper_exists else ""
    add_check(checks, "helper-v15-artifact", "pass" if helper_exists and helper_sha == EXPECTED_SHA256 else "blocked", "blocker", f"exists={helper_exists} sha={helper_sha}", [str(EXPECTED_HELPER)], "rebuild helper v15 before approval execution")

    if helper_exists:
        strings_step = run_step(store, "helper-strings", ["strings", str(EXPECTED_HELPER)], 30)
        steps.append(strings_step)
        strings_text = store.path(strings_step.file).read_text(encoding="utf-8", errors="replace")
        marker_ok = "a90_android_execns_probe v15" in strings_text
        ptrace_ok = "service_manager_start.capture_mode=ptrace-lite" in strings_text and "capture.scope=service-manager-start-only" in strings_text
        add_check(checks, "helper-v15-marker", "pass" if marker_ok and ptrace_ok else "blocked", "blocker", f"marker={marker_ok} ptrace={ptrace_ok}", [], "inspect helper build artifact")

    phrase_files = [repo_path(Path(path)).read_text(encoding="utf-8", errors="replace") for path in REQUIRED_FILES if repo_path(Path(path)).exists()]
    deploy_phrase_count = sum(text.count(DEPLOY_APPROVAL_PHRASE) for text in phrase_files)
    live_phrase_count = sum(text.count(LIVE_APPROVAL_PHRASE) for text in phrase_files)
    add_check(checks, "approval-phrases", "pass" if deploy_phrase_count >= 3 and live_phrase_count >= 3 else "blocked", "blocker", f"deploy_count={deploy_phrase_count} live_count={live_phrase_count}", [DEPLOY_APPROVAL_PHRASE, LIVE_APPROVAL_PHRASE], "sync V384 approval phrases across wrappers/docs")

    py_step = run_step(store, "py-compile", ["python3", "-m", "py_compile", *PYTHON_FILES], 120)
    steps.append(py_step)
    add_check(checks, "py-compile", "pass" if py_step.ok else "blocked", "blocker", f"rc={py_step.rc}", [py_step.file], "fix Python syntax before approval execution")

    plan_dir = store.run_dir / "executor-plan"
    noapproval_dir = store.run_dir / "executor-noapproval"
    plan_step = run_step(store, "executor-plan", ["python3", "scripts/revalidation/wifi_v384_deploy_live_executor.py", "--out-dir", str(plan_dir), "plan"], args.timeout)
    noapproval_step = run_step(store, "executor-noapproval-full", ["python3", "scripts/revalidation/wifi_v384_deploy_live_executor.py", "--out-dir", str(noapproval_dir), "full"], args.timeout)
    steps.extend([plan_step, noapproval_step])
    plan_manifest = load_json(plan_dir / "manifest.json")
    noapproval_manifest = load_json(noapproval_dir / "manifest.json")
    add_check(checks, "executor-plan", "pass" if command_false_manifest_ok(plan_manifest, "v384-deploy-live-executor-plan-ready") else "blocked", "blocker", f"decision={plan_manifest.get('decision')} pass={plan_manifest.get('pass')}", [str(plan_dir / "manifest.json")], "fix plan mode fail-closed behavior")
    noapproval_ok = command_false_manifest_ok(noapproval_manifest, "v384-deploy-live-executor-approval-required")
    blockers = noapproval_manifest.get("remaining_blockers") if isinstance(noapproval_manifest.get("remaining_blockers"), list) else []
    phrase_blockers_ok = "exact-v384-deploy-approval-phrase" in blockers and "exact-v384-ptrace-live-approval-phrase" in blockers
    add_check(checks, "executor-noapproval", "pass" if noapproval_ok and phrase_blockers_ok else "blocked", "blocker", f"decision={noapproval_manifest.get('decision')} blockers={blockers}", [str(noapproval_dir / "manifest.json")], "fix approval gate before any live execution")

    failed = [check for check in checks if check.severity == "blocker" and check.status != "pass"]
    decision = "v384-preapproval-audit-pass" if not failed else "v384-preapproval-audit-blocked"
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": not failed,
        "reason": "all host-only preapproval checks passed" if not failed else "blocked by " + ", ".join(check.name for check in failed),
        "next_step": "run exact V384 approval-gated executor" if not failed else "resolve blockers before approval execution",
        "host": collect_host_metadata(),
        "checks": [asdict(check) for check in checks],
        "steps": [asdict(step) for step in steps],
        "helper_sha256": helper_sha,
        "required_deploy_approval_phrase": DEPLOY_APPROVAL_PHRASE,
        "required_live_approval_phrase": LIVE_APPROVAL_PHRASE,
        "device_commands_executed": False,
        "device_mutations": False,
        "daemon_start_executed": False,
        "wifi_bringup_executed": False,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    check_rows = [[c["name"], c["status"], c["severity"], c["detail"], c["next_step"]] for c in manifest["checks"]]
    step_rows = [[s["name"], "PASS" if s["ok"] else "FAIL", s["rc"], s["file"]] for s in manifest["steps"]]
    return "\n".join([
        "# V384 Preapproval Audit",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- device_mutations: `{manifest['device_mutations']}`",
        f"- daemon_start_executed: `{manifest['daemon_start_executed']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        "",
        "## Checks",
        "",
        markdown_table(["name", "status", "severity", "detail", "next"], check_rows),
        "",
        "## Steps",
        "",
        markdown_table(["step", "ok", "rc", "file"], step_rows),
        "",
        "## Required Approval Phrases",
        "",
        f"- deploy: `{manifest['required_deploy_approval_phrase']}`",
        f"- live: `{manifest['required_live_approval_phrase']}`",
        "",
    ])


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    store.mkdir("steps")
    manifest = build_manifest(args, store)
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

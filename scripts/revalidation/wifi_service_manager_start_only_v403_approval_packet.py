#!/usr/bin/env python3
"""Generate the V403 service-manager start-only retry approval packet.

This packet is non-mutating. It verifies the V402 private SELinux surface proof,
runs the V403 live runner in plan/preflight/no-approval modes, and records the
exact future approval phrase. It does not start service-manager and it does not
bring up Wi-Fi.
"""

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


DEFAULT_OUT_DIR = Path("tmp/wifi/v403-service-manager-start-only-retry-approval-packet")
DEFAULT_V402_DEPLOY = Path("tmp/wifi/v402-execns-helper-v22-deploy-live-20260520-084231/manifest.json")
DEFAULT_V402_PROOF = Path("tmp/wifi/v402-private-selinux-surface-live-20260520-084832/manifest.json")
DEFAULT_V402_POST = Path("tmp/wifi/v402-private-proof-postflight-20260520-084853/manifest.json")
V403_RUNNER = Path("scripts/revalidation/wifi_service_manager_start_only_v403_live_runner.py")
APPROVAL_PHRASE = (
    "approve v403 service-manager start-only retry only; "
    "no Wi-Fi HAL start and no Wi-Fi bring-up"
)


@dataclass
class Step:
    name: str
    command: str
    rc: int
    ok: bool
    file: str
    manifest: str
    decision: str
    passed: bool


@dataclass
class Check:
    name: str
    status: str
    severity: str
    detail: str
    evidence: list[str]
    next_step: str


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--v402-deploy-manifest", type=Path, default=DEFAULT_V402_DEPLOY)
    parser.add_argument("--v402-proof-manifest", type=Path, default=DEFAULT_V402_PROOF)
    parser.add_argument("--v402-postflight-manifest", type=Path, default=DEFAULT_V402_POST)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("plan")
    subparsers.add_parser("run")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {"present": False, "path": str(resolved)}
    payload = json.loads(resolved.read_text(encoding="utf-8"))
    payload["present"] = True
    payload["path"] = str(resolved)
    return payload


def command_string(command: list[str]) -> str:
    return " ".join(command)


def run_host(command: list[str], timeout: int) -> tuple[int, str]:
    result = subprocess.run(
        command,
        cwd=repo_path("."),
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
    )
    return result.returncode, result.stdout


def run_runner_step(store: EvidenceStore, name: str, runner_command: str, timeout: int) -> Step:
    out_dir = store.path(name)
    command = [
        sys.executable,
        str(repo_path(V403_RUNNER)),
        "--out-dir",
        str(out_dir),
        runner_command,
    ]
    rc, output = run_host(command, timeout)
    rel = f"host/{name}.txt"
    store.write_text(rel, output)
    manifest_path = out_dir / "manifest.json"
    manifest: dict[str, Any] = {}
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    return Step(
        name=name,
        command=command_string(command),
        rc=rc,
        ok=rc == 0,
        file=rel,
        manifest=str(manifest_path),
        decision=str(manifest.get("decision", "missing")),
        passed=bool(manifest.get("pass", False)),
    )


def add_check(checks: list[Check], name: str, ok: bool, severity: str, detail: str,
              evidence: list[str] | None = None, next_step: str = "") -> None:
    checks.append(Check(
        name=name,
        status="pass" if ok else "blocked",
        severity=severity,
        detail=detail,
        evidence=evidence or [],
        next_step=next_step,
    ))


def manifest_bool(manifest: dict[str, Any], key: str) -> bool:
    return bool(manifest.get(key))


def build_checks(v402_deploy: dict[str, Any],
                 v402_proof: dict[str, Any],
                 v402_post: dict[str, Any],
                 steps: list[Step]) -> list[Check]:
    step_by_name = {step.name: step for step in steps}
    checks: list[Check] = []
    add_check(
        checks,
        "v402-helper-v22-deploy-pass",
        v402_deploy.get("decision") == "execns-helper-v22-deploy-pass" and manifest_bool(v402_deploy, "pass"),
        "blocker",
        f"decision={v402_deploy.get('decision')} pass={v402_deploy.get('pass')}",
        [str(v402_deploy.get("path", ""))],
        "V402 helper deploy must pass before V403 start-only retry",
    )
    add_check(
        checks,
        "v402-private-selinux-proof-pass",
        v402_proof.get("decision") == "private-selinux-surface-proof-pass" and manifest_bool(v402_proof, "pass"),
        "blocker",
        f"decision={v402_proof.get('decision')} pass={v402_proof.get('pass')}",
        [str(v402_proof.get("path", ""))],
        "V402 private namespace SELinux proof must pass before V403",
    )
    add_check(
        checks,
        "v402-no-daemon-no-wifi",
        not manifest_bool(v402_deploy, "daemon_start_executed") and
        not manifest_bool(v402_deploy, "wifi_bringup_executed") and
        not manifest_bool(v402_proof, "daemon_start_executed") and
        not manifest_bool(v402_proof, "wifi_bringup_executed"),
        "blocker",
        "V402 evidence must not include daemon or Wi-Fi execution",
        [],
        "inspect V402 manifests before widening scope",
    )
    add_check(
        checks,
        "v402-postflight-ready",
        v402_post.get("decision") == "private-selinux-surface-proof-preflight-ready" and manifest_bool(v402_post, "pass"),
        "blocker",
        f"decision={v402_post.get('decision')} pass={v402_post.get('pass')}",
        [str(v402_post.get("path", ""))],
        "postflight must be clean before V403 approval packet",
    )
    if not steps:
        add_check(checks, "plan-only", True, "info", "plan mode does not run host/device checks", [], "run packet before approval")
        return checks
    add_check(
        checks,
        "v403-runner-plan-ready",
        step_by_name.get("runner-plan") is not None and step_by_name["runner-plan"].decision == "service-manager-start-only-live-plan-ready" and step_by_name["runner-plan"].passed,
        "blocker",
        step_by_name.get("runner-plan").decision if step_by_name.get("runner-plan") else "missing",
        [step_by_name["runner-plan"].manifest] if step_by_name.get("runner-plan") else [],
        "V403 runner plan must render before approval",
    )
    add_check(
        checks,
        "v403-runner-preflight-ready",
        step_by_name.get("runner-preflight") is not None and step_by_name["runner-preflight"].decision == "service-manager-start-only-live-preflight-ready" and step_by_name["runner-preflight"].passed,
        "blocker",
        step_by_name.get("runner-preflight").decision if step_by_name.get("runner-preflight") else "missing",
        [step_by_name["runner-preflight"].manifest] if step_by_name.get("runner-preflight") else [],
        "V403 runner read-only preflight must be ready before approval",
    )
    add_check(
        checks,
        "v403-runner-noapproval-refuses",
        step_by_name.get("runner-noapproval-run") is not None and step_by_name["runner-noapproval-run"].decision == "service-manager-start-only-live-approval-required" and step_by_name["runner-noapproval-run"].passed,
        "blocker",
        step_by_name.get("runner-noapproval-run").decision if step_by_name.get("runner-noapproval-run") else "missing",
        [step_by_name["runner-noapproval-run"].manifest] if step_by_name.get("runner-noapproval-run") else [],
        "run mode must fail closed without exact approval",
    )
    return checks


def blockers(checks: list[Check]) -> list[str]:
    return [check.name for check in checks if check.severity == "blocker" and check.status != "pass"]


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    v402_deploy = load_json(args.v402_deploy_manifest)
    v402_proof = load_json(args.v402_proof_manifest)
    v402_post = load_json(args.v402_postflight_manifest)
    steps: list[Step] = []
    if args.command == "run":
        store.mkdir("host")
        steps = [
            run_runner_step(store, "runner-plan", "plan", args.timeout),
            run_runner_step(store, "runner-preflight", "preflight", args.timeout),
            run_runner_step(store, "runner-noapproval-run", "run", args.timeout),
        ]
    checks = build_checks(v402_deploy, v402_proof, v402_post, steps)
    blocking = blockers(checks)
    pass_ok = not blocking
    if args.command == "plan":
        decision = "v403-service-manager-start-only-retry-approval-packet-plan-ready"
    elif pass_ok:
        decision = "v403-service-manager-start-only-retry-approval-packet-ready"
    else:
        decision = "v403-service-manager-start-only-retry-approval-packet-blocked"
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": "approval packet ready; live start-only still requires separate exact approval" if pass_ok else "blocked by " + ", ".join(blocking),
        "next_step": "operator may approve V403 service-manager start-only retry" if pass_ok and args.command == "run" else "run packet before approval",
        "host": collect_host_metadata(),
        "inputs": {
            "v402_deploy": {"path": v402_deploy.get("path"), "present": v402_deploy.get("present"), "decision": v402_deploy.get("decision"), "pass": v402_deploy.get("pass")},
            "v402_proof": {"path": v402_proof.get("path"), "present": v402_proof.get("present"), "decision": v402_proof.get("decision"), "pass": v402_proof.get("pass")},
            "v402_postflight": {"path": v402_post.get("path"), "present": v402_post.get("present"), "decision": v402_post.get("decision"), "pass": v402_post.get("pass")},
        },
        "steps": [asdict(step) for step in steps],
        "checks": [asdict(check) for check in checks],
        "future_runner": str(V403_RUNNER),
        "required_approval_phrase": APPROVAL_PHRASE,
        "future_command_template": (
            "python3 scripts/revalidation/wifi_service_manager_start_only_v403_live_runner.py "
            "--approval-phrase '" + APPROVAL_PHRASE + "' --apply --assume-yes run"
        ),
        "approved_scope_after_phrase": [
            "bounded service-manager and hwservicemanager start-only retry",
            "private namespace with helper v22 SELinuxfs, Binder, linkerconfig, APEX, and property runtime materialization",
            "ptrace-lite capture for crash/runtime-gap evidence",
            "bounded timeout, termination, reap, and postflight process/Wi-Fi cleanliness checks",
        ],
        "explicitly_not_approved": [
            "Wi-Fi HAL service start",
            "wificond, supplicant, hostapd, cnss-daemon, or cnss_diag start",
            "Wi-Fi scan/connect/link-up/credential/DHCP/routing",
            "rfkill write, ICNSS bind/unbind, module load/unload, firmware mutation, Android partition write",
            "unbounded daemon persistence or boot autostart flag changes",
        ],
        "live_execution_approved": False,
        "device_mutations": False,
        "daemon_start_executed": False,
        "wifi_bringup_executed": False,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    check_rows = [[item["name"], item["status"], item["severity"], item["detail"], "<br>".join(item["evidence"]), item["next_step"]] for item in manifest["checks"]]
    step_rows = [[item["name"], item["rc"], item["decision"], item["passed"], item["manifest"]] for item in manifest["steps"]]
    return "\n".join([
        "# V403 Service-Manager Start-Only Retry Approval Packet",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- live_execution_approved: `{manifest['live_execution_approved']}`",
        f"- device_mutations: `{manifest['device_mutations']}`",
        f"- daemon_start_executed: `{manifest['daemon_start_executed']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        "",
        "## Checks",
        "",
        markdown_table(["name", "status", "severity", "detail", "evidence", "next_step"], check_rows),
        "",
        "## Runner Steps",
        "",
        markdown_table(["name", "rc", "decision", "pass", "manifest"], step_rows) if step_rows else "- none",
        "",
        "## Future Runner",
        "",
        f"- runner: `{manifest['future_runner']}`",
        "- command template:",
        "",
        "```bash",
        manifest["future_command_template"],
        "```",
        "",
        "## Approved Scope After Phrase",
        "",
        "\n".join(f"- {item}" for item in manifest["approved_scope_after_phrase"]),
        "",
        "## Explicitly Not Approved",
        "",
        "\n".join(f"- `{item}`" for item in manifest["explicitly_not_approved"]),
        "",
        "## Required Approval Phrase",
        "",
        f"`{manifest['required_approval_phrase']}`",
        "",
    ])


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args, store)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    store.write_text("approval-packet.md", render_summary(manifest))
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"approval_phrase: {manifest['required_approval_phrase']}")
    print(f"live_execution_approved: {manifest['live_execution_approved']}")
    print(f"device_mutations: {manifest['device_mutations']}")
    print(f"daemon_start_executed: {manifest['daemon_start_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Generate the V405 composite helper/HAL approval packet.

This packet is non-mutating. It builds and audits helper v23 locally, verifies
the V404 readiness packet, checks that helper deploy and composite HAL runner
guards fail closed, and records the exact future approval phrases.

It does not deploy the helper, start service-manager, start Wi-Fi HAL, or bring
up Wi-Fi.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v405-composite-hal-approval-packet")
DEFAULT_V404 = Path("tmp/wifi/v404-private-composite-hal-readiness-packet-fixed-20260520-090542/manifest.json")
DEFAULT_HELPER_ARTIFACT = Path("tmp/wifi/v405-a90_android_execns_probe-v23/a90_android_execns_probe")
HELPER_SOURCE = Path("stage3/linux_init/helpers/a90_android_execns_probe.c")
BUILD_SCRIPT = Path("scripts/revalidation/build_android_execns_probe_helper.sh")
DEPLOY_RUNNER = Path("scripts/revalidation/wifi_execns_helper_v23_deploy_preflight.py")
HAL_RUNNER = Path("scripts/revalidation/wifi_composite_hal_start_only_v405_runner.py")
HELPER_MARKER = "a90_android_execns_probe v23"
HELPER_SHA256 = "64c80e73d791b82e0b9f60b05db1df1781bf5033b1ffd76e323cf52ce3dbc520"
REQUIRED_STRINGS = (
    HELPER_MARKER,
    "wifi-hal-composite-start-only",
    "vendor-wifi-hal-ext",
    "vendor-wifi-hal-legacy",
    "--allow-wifi-hal-start-only",
    "wifi_hal_composite_start.scan_connect_linkup=0",
)
DEPLOY_APPROVAL_PHRASE = (
    "approve v405 deploy execns helper v23 only; "
    "no daemon start and no Wi-Fi bring-up"
)
HAL_APPROVAL_PHRASE = (
    "approve v405 composite Wi-Fi HAL start-only smoke only; "
    "no scan/connect/link-up and no Wi-Fi bring-up"
)


@dataclass
class HostStep:
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
    parser.add_argument("--timeout", type=int, default=240)
    parser.add_argument("--v404-manifest", type=Path, default=DEFAULT_V404)
    parser.add_argument("--helper-artifact", type=Path, default=DEFAULT_HELPER_ARTIFACT)
    parser.add_argument("--skip-build", action="store_true")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("plan")
    subparsers.add_parser("run")
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {"present": False, "path": str(resolved), "decision": "missing", "pass": False}
    payload = json.loads(resolved.read_text(encoding="utf-8"))
    payload["present"] = True
    payload["path"] = str(resolved)
    return payload


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


def command_string(command: list[str]) -> str:
    return " ".join(command)


def strings_text(path: Path) -> str:
    rc, output = run_host(["strings", str(path)], timeout=30)
    return output if rc == 0 else ""


def build_helper(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    artifact = repo_path(args.helper_artifact)
    artifact.parent.mkdir(parents=True, exist_ok=True)
    command = ["bash", str(repo_path(BUILD_SCRIPT)), str(artifact)]
    if args.skip_build and artifact.exists():
        rc = 0
        output = "skip-build: existing artifact reused\n"
    else:
        rc, output = run_host(command, timeout=args.timeout)
    store.write_text("host/build-helper-v23.txt", output)
    strings = strings_text(artifact) if artifact.exists() else ""
    file_rc, file_output = run_host(["file", str(artifact)], timeout=20) if artifact.exists() else (1, "")
    info = {
        "command": command_string(command),
        "rc": rc,
        "ok": rc == 0,
        "file": "host/build-helper-v23.txt",
        "artifact": str(artifact),
        "present": artifact.exists(),
        "sha256": sha256_file(artifact) if artifact.exists() else "",
        "file_output": file_output.strip() if file_rc == 0 else file_output.strip(),
        "marker": HELPER_MARKER if HELPER_MARKER in strings else "<missing>",
        "required_strings_present": {item: item in strings for item in REQUIRED_STRINGS},
    }
    return info


def run_script_step(store: EvidenceStore, name: str, script: Path, script_command: str,
                    timeout: int, extra: list[str] | None = None) -> HostStep:
    out_dir = store.path(name)
    command = [
        sys.executable,
        str(repo_path(script)),
        "--out-dir",
        str(out_dir),
    ]
    if extra:
        command.extend(extra)
    command.append(script_command)
    rc, output = run_host(command, timeout)
    rel = f"host/{name}.txt"
    store.write_text(rel, output)
    manifest_path = out_dir / "manifest.json"
    manifest: dict[str, Any] = {}
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    return HostStep(
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
    checks.append(Check(name, "pass" if ok else "blocked", severity, detail, evidence or [], next_step))


def build_checks(v404: dict[str, Any], helper: dict[str, Any], steps: list[HostStep]) -> list[Check]:
    step_by_name = {step.name: step for step in steps}
    strings_present = helper.get("required_strings_present", {})
    checks: list[Check] = []
    add_check(
        checks,
        "v404-readiness-pass",
        v404.get("decision") == "v404-private-composite-hal-readiness-packet-ready" and bool(v404.get("pass")),
        "blocker",
        f"decision={v404.get('decision')} pass={v404.get('pass')}",
        [str(v404.get("path", ""))],
        "V404 readiness must pass before V405",
    )
    add_check(
        checks,
        "helper-v23-built",
        bool(helper.get("present")) and helper.get("ok") and helper.get("sha256") == HELPER_SHA256,
        "blocker",
        f"present={helper.get('present')} rc={helper.get('rc')} sha={helper.get('sha256')}",
        [str(helper.get("artifact", "")), str(helper.get("file", ""))],
        "build helper v23 before deploy packet",
    )
    add_check(
        checks,
        "helper-v23-strings",
        all(bool(strings_present.get(item)) for item in REQUIRED_STRINGS),
        "blocker",
        json.dumps(strings_present, sort_keys=True),
        [str(helper.get("artifact", ""))],
        "helper v23 must expose composite HAL mode and guard strings",
    )
    if not steps:
        add_check(checks, "plan-only", True, "info", "plan mode does not run host/device checks", [], "run packet before approval")
        return checks
    deploy_plan = step_by_name.get("deploy-plan")
    deploy_preflight = step_by_name.get("deploy-preflight")
    deploy_noapproval = step_by_name.get("deploy-noapproval-run")
    runner_plan = step_by_name.get("hal-runner-plan")
    runner_noapproval = step_by_name.get("hal-runner-noapproval-run")
    add_check(checks, "deploy-plan-ready", deploy_plan is not None and deploy_plan.decision == "execns-helper-v23-deploy-plan-ready" and deploy_plan.passed, "blocker", deploy_plan.decision if deploy_plan else "missing", [deploy_plan.manifest] if deploy_plan else [], "deploy runner plan must render")
    add_check(checks, "deploy-preflight-ready", deploy_preflight is not None and deploy_preflight.decision in {"execns-helper-v23-deploy-preflight-ready", "execns-helper-v23-deploy-preflight-ready-needs-deploy"} and deploy_preflight.passed, "blocker", deploy_preflight.decision if deploy_preflight else "missing", [deploy_preflight.manifest] if deploy_preflight else [], "deploy preflight must be safe before approval")
    add_check(checks, "deploy-noapproval-refuses", deploy_noapproval is not None and deploy_noapproval.decision == "execns-helper-v23-deploy-approval-required" and deploy_noapproval.passed, "blocker", deploy_noapproval.decision if deploy_noapproval else "missing", [deploy_noapproval.manifest] if deploy_noapproval else [], "deploy run must fail closed without exact approval")
    add_check(checks, "hal-runner-plan-ready", runner_plan is not None and runner_plan.decision == "composite-hal-start-only-plan-ready" and runner_plan.passed, "blocker", runner_plan.decision if runner_plan else "missing", [runner_plan.manifest] if runner_plan else [], "HAL runner plan must render")
    add_check(checks, "hal-runner-noapproval-refuses", runner_noapproval is not None and runner_noapproval.decision == "composite-hal-start-only-approval-required" and runner_noapproval.passed, "blocker", runner_noapproval.decision if runner_noapproval else "missing", [runner_noapproval.manifest] if runner_noapproval else [], "HAL runner must fail closed without exact approval")
    return checks


def blockers(checks: list[Check]) -> list[str]:
    return [check.name for check in checks if check.severity == "blocker" and check.status != "pass"]


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    store.mkdir("host")
    v404 = load_json(args.v404_manifest)
    helper = build_helper(args, store)
    store.write_json("helper-v23.json", helper)
    steps: list[HostStep] = []
    if args.command == "run":
        helper_extra = ["--local-helper", str(repo_path(args.helper_artifact)), "--helper-sha256", HELPER_SHA256]
        steps = [
            run_script_step(store, "deploy-plan", DEPLOY_RUNNER, "plan", args.timeout, helper_extra),
            run_script_step(store, "deploy-preflight", DEPLOY_RUNNER, "preflight", args.timeout, helper_extra),
            run_script_step(store, "deploy-noapproval-run", DEPLOY_RUNNER, "run", args.timeout, helper_extra),
            run_script_step(store, "hal-runner-plan", HAL_RUNNER, "plan", args.timeout, ["--helper-sha256", HELPER_SHA256]),
            run_script_step(store, "hal-runner-noapproval-run", HAL_RUNNER, "run", args.timeout, ["--helper-sha256", HELPER_SHA256]),
        ]
    checks = build_checks(v404, helper, steps)
    blocking = blockers(checks)
    pass_ok = not blocking
    if args.command == "plan":
        decision = "v405-composite-hal-approval-packet-plan-ready"
    elif pass_ok:
        decision = "v405-composite-hal-approval-packet-ready"
    else:
        decision = "v405-composite-hal-approval-packet-blocked"
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": "approval packet ready; deploy and HAL start-only still require separate exact approvals" if pass_ok else "blocked by " + ", ".join(blocking),
        "next_step": "operator may approve V405 helper v23 deploy first" if pass_ok and args.command == "run" else "run packet before approval",
        "host": collect_host_metadata(),
        "inputs": {
            "v404": {"path": v404.get("path"), "present": v404.get("present"), "decision": v404.get("decision"), "pass": v404.get("pass")},
        },
        "helper": helper,
        "steps": [asdict(step) for step in steps],
        "checks": [asdict(check) for check in checks],
        "deploy_runner": str(DEPLOY_RUNNER),
        "hal_runner": str(HAL_RUNNER),
        "helper_source": str(repo_path(HELPER_SOURCE)),
        "helper_artifact": str(repo_path(args.helper_artifact)),
        "helper_sha256": HELPER_SHA256,
        "deploy_approval_phrase": DEPLOY_APPROVAL_PHRASE,
        "hal_approval_phrase": HAL_APPROVAL_PHRASE,
        "approval_order": [
            "deploy helper v23 only",
            "run composite Wi-Fi HAL start-only smoke only after deploy/preflight pass",
        ],
        "approved_scope_after_deploy_phrase": [
            "install or verify /cache/bin/a90_android_execns_probe helper v23 only",
            "no service-manager, hwservicemanager, Wi-Fi HAL, or Wi-Fi bring-up execution",
        ],
        "approved_scope_after_hal_phrase": [
            "bounded helper-owned private namespace",
            "servicemanager + hwservicemanager + first HAL candidate vendor.wifi_hal_ext",
            "bounded timeout, cleanup, reap, and postflight cleanliness checks",
        ],
        "explicitly_not_approved": [
            "wificond, supplicant, hostapd, cnss-daemon, or cnss_diag start",
            "Wi-Fi scan/connect/link-up/credential/DHCP/routing",
            "rfkill write, ICNSS bind/unbind, module load/unload, firmware mutation, Android partition write",
            "unbounded daemon persistence or boot autostart",
        ],
        "live_execution_approved": False,
        "device_mutations": False,
        "daemon_start_executed": False,
        "wifi_hal_start_executed": False,
        "wifi_bringup_executed": False,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    check_rows = [[item["name"], item["status"], item["severity"], item["detail"], "<br>".join(item["evidence"]), item["next_step"]] for item in manifest["checks"]]
    step_rows = [[item["name"], item["rc"], item["decision"], item["passed"], item["manifest"]] for item in manifest["steps"]]
    return "\n".join([
        "# V405 Composite Wi-Fi HAL Approval Packet",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- helper_sha256: `{manifest['helper_sha256']}`",
        f"- live_execution_approved: `{manifest['live_execution_approved']}`",
        f"- device_mutations: `{manifest['device_mutations']}`",
        f"- daemon_start_executed: `{manifest['daemon_start_executed']}`",
        f"- wifi_hal_start_executed: `{manifest['wifi_hal_start_executed']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        "",
        "## Checks",
        "",
        markdown_table(["name", "status", "severity", "detail", "evidence", "next_step"], check_rows),
        "",
        "## Host Steps",
        "",
        markdown_table(["name", "rc", "decision", "pass", "manifest"], step_rows) if step_rows else "- none",
        "",
        "## Approval Phrases",
        "",
        f"- deploy: `{manifest['deploy_approval_phrase']}`",
        f"- HAL start-only: `{manifest['hal_approval_phrase']}`",
        "",
        "## Explicitly Not Approved",
        "",
        "\n".join(f"- `{item}`" for item in manifest["explicitly_not_approved"]),
        "",
    ])


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args, store)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"helper_sha256: {manifest['helper_sha256']}")
    print(f"live_execution_approved: {manifest['live_execution_approved']}")
    print(f"device_mutations: {manifest['device_mutations']}")
    print(f"daemon_start_executed: {manifest['daemon_start_executed']}")
    print(f"wifi_hal_start_executed: {manifest['wifi_hal_start_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

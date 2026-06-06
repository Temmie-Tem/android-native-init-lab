#!/usr/bin/env python3
"""Generate V400 toybox-backed SELinuxfs mount approval packet."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import shlex
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore
from wifi_selinuxfs_toybox_mount_live_executor import APPROVAL_PHRASE, DEFAULT_OUT_DIR as DEFAULT_V401_OUT_DIR


DEFAULT_OUT_DIR = Path("tmp/wifi/v400-toybox-selinuxfs-mount-approval-packet")
SELINUX_PROOF = Path("scripts/revalidation/wifi_service_manager_selinux_surface_proof.py")
LIVE_EXECUTOR = Path("scripts/revalidation/wifi_selinuxfs_toybox_mount_live_executor.py")
A90CTL = Path("scripts/revalidation/a90ctl.py")
TOYBOX = "/cache/bin/toybox"


@dataclass
class ToolRun:
    name: str
    argv: list[str]
    rc: int | None
    stdout_path: str
    manifest_path: str
    decision: str
    pass_value: bool | None
    error: str


@dataclass
class CommandRun:
    name: str
    argv: list[str]
    rc: int | None
    stdout_path: str
    error: str


@dataclass
class PacketCheck:
    name: str
    status: str
    detail: str
    evidence: str
    next_step: str


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v401-run-out-dir", type=Path, default=DEFAULT_V401_OUT_DIR)
    parser.add_argument("--v401-cleanup-out-dir", type=Path, default=Path("tmp/wifi/v401-toybox-selinuxfs-mount-cleanup-approved"))
    parser.add_argument("--timeout", type=int, default=360)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("run")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {"present": False, "path": str(resolved)}
    data = json.loads(resolved.read_text(encoding="utf-8"))
    data["present"] = True
    data["path"] = str(resolved)
    return data


def run_process(argv: list[str], timeout: int) -> tuple[int | None, str, str]:
    try:
        result = subprocess.run(
            argv,
            cwd=repo_path(Path(".")),
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
        )
        return result.returncode, result.stdout, ""
    except subprocess.TimeoutExpired as exc:
        text = exc.stdout if isinstance(exc.stdout, str) else ""
        return None, text, f"timeout after {timeout}s"
    except Exception as exc:  # noqa: BLE001 - evidence preserves tool failures
        return None, "", str(exc)


def command_text(argv: list[str]) -> str:
    return " ".join(shlex.quote(item) for item in argv)


def run_tool(store: EvidenceStore, name: str, argv: list[str], timeout: int) -> ToolRun:
    rc, stdout, error = run_process(argv, timeout)
    stdout_path = store.write_text(f"commands/{name}.txt", "$ " + command_text(argv) + "\n" + (stdout or error) + f"\nrc={rc}\n")
    out_dir = Path(argv[argv.index("--out-dir") + 1])
    manifest_path = out_dir / "manifest.json"
    manifest = load_json(manifest_path)
    return ToolRun(
        name=name,
        argv=argv,
        rc=rc,
        stdout_path=str(stdout_path.relative_to(store.run_dir)),
        manifest_path=str(repo_path(manifest_path)),
        decision=str(manifest.get("decision") or "missing"),
        pass_value=bool(manifest.get("pass")) if manifest.get("pass") is not None else None,
        error=error,
    )


def run_plain_command(store: EvidenceStore, name: str, argv: list[str], timeout: int) -> CommandRun:
    rc, stdout, error = run_process(argv, timeout)
    stdout_path = store.write_text(f"commands/{name}.txt", "$ " + command_text(argv) + "\n" + (stdout or error) + f"\nrc={rc}\n")
    return CommandRun(name, argv, rc, str(stdout_path), error)


def script_argv(script: Path, out_dir: Path, *extra: str) -> list[str]:
    return [sys.executable, str(repo_path(script)), "--out-dir", str(repo_path(out_dir)), *extra]


def approval_run_command(args: argparse.Namespace) -> str:
    argv = [
        "python3",
        str(LIVE_EXECUTOR),
        "--out-dir",
        str(args.v401_run_out_dir),
        "--approval-phrase",
        APPROVAL_PHRASE,
        "--apply",
        "--assume-yes",
        "run",
    ]
    return command_text(argv) + "\n"


def approval_cleanup_command(args: argparse.Namespace) -> str:
    argv = [
        "python3",
        str(LIVE_EXECUTOR),
        "--out-dir",
        str(args.v401_cleanup_out_dir),
        "--approval-phrase",
        APPROVAL_PHRASE,
        "--apply",
        "--assume-yes",
        "cleanup",
    ]
    return command_text(argv) + "\n"


def render_rollback_checklist() -> str:
    return """# V401 Toybox SELinuxfs Mount Rollback Checklist

## Before Approved Run

- Confirm V400 packet decision is `toybox-selinuxfs-mount-approval-packet-ready`.
- Confirm bridge control is stable.
- Confirm no `servicemanager`, `hwservicemanager`, `vndservicemanager`, Wi-Fi HAL, wificond, supplicant, hostapd, CNSS, or Wi-Fi link operation is in scope.
- Confirm `/proc/filesystems` contains `selinuxfs`.
- Confirm `/sys/fs/selinux/status` is still absent before mount.
- Confirm `cmdv1 run /cache/bin/toybox mount` works as a read-only inventory command.

## Approved Run Boundary

- The only mutating command is `run /cache/bin/toybox mount -t selinuxfs selinuxfs /sys/fs/selinux`.
- Post-mount checks are read-only: `/proc/mounts`, `stat /sys/fs/selinux/status`, `cat /sys/fs/selinux/enforce`, `xxd -l 64 /sys/fs/selinux/status`.
- No daemon start and no Wi-Fi bring-up are approved.

## Cleanup Boundary

- Cleanup command is limited to `run /cache/bin/toybox umount /sys/fs/selinux`.
- Cleanup should not be run if a later approved service-manager test intentionally depends on the mounted surface.

## If The Run Fails Or Control Is Lost

- Preserve the evidence directory.
- Do not start service-manager or Wi-Fi manually.
- Reconnect control and run read-only SELinux proof.
- Use the approved cleanup command only if the mount needs to be reverted.
"""


def manifest_checks(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    checks = manifest.get("checks")
    if not isinstance(checks, list):
        return {}
    return {str(item.get("name")): item for item in checks if isinstance(item, dict)}


def status(condition: bool) -> str:
    return "pass" if condition else "blocked"


def build_checks(
    runs: list[ToolRun],
    commands: list[CommandRun],
    manifests: dict[str, dict[str, Any]],
    run_command: str,
    cleanup_command: str,
) -> list[PacketCheck]:
    checks: list[PacketCheck] = []
    by_run = {run.name: run for run in runs}
    by_command = {command.name: command for command in commands}
    proof = manifests.get("selinux-proof", {})
    proof_checks = manifest_checks(proof)
    proof_ok = proof.get("decision") == "service-manager-selinux-status-native-missing" and bool(proof.get("pass"))
    checks.append(PacketCheck(
        "v397-proof-current",
        status(proof_ok),
        f"decision={proof.get('decision')} pass={proof.get('pass')}",
        str(proof.get("path", "")),
        "SELinux status surface should still be missing before retry",
    ))
    mount_check = proof_checks.get("native-selinuxfs-mount", {})
    status_check = proof_checks.get("native-selinux-status-page", {})
    checks.append(PacketCheck(
        "kernel-supports-selinuxfs",
        status("proc_filesystems_selinuxfs=True" in str(mount_check.get("detail"))),
        str(mount_check.get("detail")),
        str(proof.get("path", "")),
        "kernel support is required before toybox mount smoke",
    ))
    checks.append(PacketCheck(
        "status-page-currently-missing",
        status(status_check.get("status") == "missing"),
        str(status_check.get("detail")),
        str(proof.get("path", "")),
        "V401 should be the first successful mount/status activation step",
    ))
    inventory = by_command.get("toybox-mount-inventory")
    inventory_text = ""
    if inventory:
        inventory_path = Path(inventory.stdout_path)
        if inventory_path.exists():
            inventory_text = inventory_path.read_text(encoding="utf-8", errors="replace")
    inventory_ok = inventory is not None and inventory.rc == 0 and " on / type " in inventory_text
    checks.append(PacketCheck(
        "toybox-mount-inventory",
        status(inventory_ok),
        f"rc={getattr(inventory, 'rc', None)} contains_root_mount={' on / type ' in inventory_text}",
        getattr(inventory, "stdout_path", ""),
        "toybox mount must be callable through cmdv1 run",
    ))
    expected_runs = {
        "executor-plan": "toybox-selinuxfs-mount-live-executor-plan-ready",
        "executor-run-refusal": "toybox-selinuxfs-mount-live-executor-approval-required",
        "executor-cleanup-refusal": "toybox-selinuxfs-mount-live-executor-approval-required",
    }
    for name, decision in expected_runs.items():
        item = by_run.get(name)
        ok = item is not None and item.rc == 0 and item.decision == decision and item.pass_value is True
        checks.append(PacketCheck(
            name,
            status(ok),
            f"rc={getattr(item, 'rc', None)} decision={getattr(item, 'decision', None)} pass={getattr(item, 'pass_value', None)}",
            getattr(item, "manifest_path", ""),
            f"expected {decision}",
        ))
    run_refusal = manifests.get("executor-run-refusal", {})
    cleanup_refusal = manifests.get("executor-cleanup-refusal", {})
    no_commands = not run_refusal.get("device_commands_executed") and not cleanup_refusal.get("device_commands_executed")
    no_mutation = not run_refusal.get("device_mutations") and not cleanup_refusal.get("device_mutations")
    checks.append(PacketCheck(
        "refusals-before-device-commands",
        status(no_commands and no_mutation),
        f"run_commands={run_refusal.get('device_commands_executed')} cleanup_commands={cleanup_refusal.get('device_commands_executed')} run_mutation={run_refusal.get('device_mutations')} cleanup_mutation={cleanup_refusal.get('device_mutations')}",
        "",
        "no-approval path must be fail-closed",
    ))
    command_ok = APPROVAL_PHRASE in run_command and "--apply" in run_command and "--assume-yes" in run_command and run_command.rstrip().endswith("run")
    cleanup_ok = APPROVAL_PHRASE in cleanup_command and "--apply" in cleanup_command and "--assume-yes" in cleanup_command and cleanup_command.rstrip().endswith("cleanup")
    checks.append(PacketCheck(
        "approval-command-contract",
        status(command_ok),
        run_command.strip(),
        "approval-command.sh",
        "operator must use exact phrase and mutation flags",
    ))
    checks.append(PacketCheck(
        "cleanup-command-contract",
        status(cleanup_ok),
        cleanup_command.strip(),
        "cleanup-command.sh",
        "cleanup remains separately exact-approved",
    ))
    return checks

def render_summary(manifest: dict[str, Any], checks: list[PacketCheck]) -> str:
    rows = [[check.name, check.status, check.detail, check.next_step] for check in checks]
    return "\n".join([
        "# V400 Toybox SELinuxfs Mount Approval Packet",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- live_execution_approved: `{manifest['live_execution_approved']}`",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- device_mutations: `{manifest['device_mutations']}`",
        f"- daemon_start_executed: `{manifest['daemon_start_executed']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        "",
        "## Checks",
        "",
        markdown_table(["check", "status", "detail", "next"], rows),
        "",
        "## Approval Phrase",
        "",
        f"`{APPROVAL_PHRASE}`",
        "",
        "## Approval Command",
        "",
        "```bash",
        manifest["approval_command"].rstrip(),
        "```",
        "",
        "## Cleanup Command",
        "",
        "```bash",
        manifest["cleanup_command"].rstrip(),
        "```",
        "",
    ]) + "\n"


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> tuple[dict[str, Any], list[PacketCheck]]:
    store.mkdir("commands")
    runs: list[ToolRun] = []
    commands: list[CommandRun] = []
    proof_dir = store.run_dir / "selinux-proof"
    executor_plan_dir = store.run_dir / "executor-plan"
    executor_run_refusal_dir = store.run_dir / "executor-run-refusal"
    executor_cleanup_refusal_dir = store.run_dir / "executor-cleanup-refusal"
    runs.append(run_tool(store, "selinux-proof", script_argv(SELINUX_PROOF, proof_dir, "run"), args.timeout))
    commands.append(run_plain_command(
        store,
        "toybox-mount-inventory",
        [sys.executable, str(repo_path(A90CTL)), "run", TOYBOX, "mount"],
        args.timeout,
    ))
    runs.append(run_tool(store, "executor-plan", script_argv(LIVE_EXECUTOR, executor_plan_dir, "plan"), args.timeout))
    runs.append(run_tool(store, "executor-run-refusal", script_argv(LIVE_EXECUTOR, executor_run_refusal_dir, "run"), args.timeout))
    runs.append(run_tool(store, "executor-cleanup-refusal", script_argv(LIVE_EXECUTOR, executor_cleanup_refusal_dir, "cleanup"), args.timeout))
    manifests = {run.name: load_json(Path(run.manifest_path)) for run in runs}
    run_command = approval_run_command(args)
    cleanup_command = approval_cleanup_command(args)
    store.write_text("approval-command.sh", run_command)
    store.write_text("cleanup-command.sh", cleanup_command)
    store.write_text("rollback-checklist.md", render_rollback_checklist())
    checks = build_checks(runs, commands, manifests, run_command, cleanup_command)
    pass_ok = all(check.status == "pass" for check in checks)
    decision = "toybox-selinuxfs-mount-approval-packet-ready" if pass_ok else "toybox-selinuxfs-mount-approval-packet-blocked"
    reason = "V401 toybox SELinuxfs mount smoke is ready for exact approval" if pass_ok else "one or more approval gates failed"
    manifest: dict[str, Any] = {
        "generated_at": now_iso(),
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": "run V401 executor only with exact approval; no daemon or Wi-Fi start",
        "host": collect_host_metadata(),
        "approval_phrase": APPROVAL_PHRASE,
        "approval_command": run_command,
        "cleanup_command": cleanup_command,
        "runs": [asdict(run) for run in runs],
        "commands": [asdict(command) for command in commands],
        "checks": [asdict(check) for check in checks],
        "references": [
            "docs/reports/NATIVE_INIT_V399_SELINUXFS_MOUNT_SMOKE_2026-05-20.md",
            "https://android.googlesource.com/platform/system/core/+/74bf81443fef2ff48bb80cc24b678aff8bdd462a/init/init.cpp",
            "https://android.googlesource.com/platform/external/selinux/+/refs/heads/main/libselinux/src/sestatus.c",
        ],
        "live_execution_approved": False,
        "device_commands_executed": True,
        "device_mutations": False,
        "daemon_start_executed": False,
        "wifi_bringup_executed": False,
        "guardrails": [
            "packet itself is non-mutating",
            "runs fresh read-only SELinux proof",
            "verifies toybox mount inventory through cmdv1 run",
            "verifies V401 executor refusals before device commands",
            "future approved mutation limited to toybox mount -t selinuxfs selinuxfs /sys/fs/selinux",
            "future cleanup limited to toybox umount /sys/fs/selinux",
            "no daemon start",
            "no Wi-Fi HAL/start/scan/connect",
            "no SELinux policy write or enforcement change",
        ],
    }
    return manifest, checks


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest, checks = build_manifest(args, store)
    store.write_json("manifest.json", manifest)
    store.write_json("checks.json", {"checks": [asdict(check) for check in checks]})
    store.write_text("summary.md", render_summary(manifest, checks))
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"live_execution_approved: {manifest['live_execution_approved']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"device_mutations: {manifest['device_mutations']}")
    print(f"daemon_start_executed: {manifest['daemon_start_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Fail-closed V399 SELinuxfs mount live executor.

This executor is intentionally narrow.  Without the exact approval phrase and
both mutation flags, run/cleanup execute no bridge command.  Approved run mounts
only selinuxfs at /sys/fs/selinux and performs read-only verification.  It does
not start service-manager, Wi-Fi HAL, or Wi-Fi bring-up.
"""

from __future__ import annotations

import argparse
import datetime as dt
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import capture_to_manifest, collect_host_metadata, repo_path, run_capture, strip_cmdv1_text
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v399-selinuxfs-mount-live-executor")
APPROVAL_PHRASE = "approve v399 mount selinuxfs runtime surface only; no daemon start and no Wi-Fi bring-up"
APPROVAL_BLOCKER = "exact-v399-selinuxfs-mount-approval-phrase"
SELINUXFS_TARGET = "/sys/fs/selinux"
TOYBOX = "/cache/bin/toybox"


@dataclass
class Step:
    name: str
    command: str
    ok: bool
    rc: int | None
    status: str
    duration_sec: float
    file: str
    skipped: bool
    error: str


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=54321)
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--approval-phrase", default="")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--assume-yes", action="store_true")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("plan")
    subparsers.add_parser("run")
    subparsers.add_parser("cleanup")
    return parser.parse_args()


def approved(args: argparse.Namespace) -> bool:
    return args.approval_phrase == APPROVAL_PHRASE and args.apply and args.assume_yes


def command_plan(command: str) -> list[list[str]]:
    common = [
        ["version"],
        ["status"],
        ["cat", "/proc/mounts"],
        ["stat", SELINUXFS_TARGET],
    ]
    verify = [
        ["stat", "/sys/fs/selinux/status"],
        ["cat", "/sys/fs/selinux/enforce"],
        ["run", TOYBOX, "xxd", "-l", "64", "/sys/fs/selinux/status"],
    ]
    if command == "run":
        return [*common, ["mount", "selinuxfs", SELINUXFS_TARGET, "selinuxfs"], *verify]
    if command == "cleanup":
        return [*common, ["umount", SELINUXFS_TARGET], *verify]
    return [*common, *verify]


def command_text(command: list[str]) -> str:
    return " ".join(command)


def validate_device_command(args: argparse.Namespace, command: list[str]) -> None:
    allowed = {tuple(item) for item in command_plan(args.command)}
    if tuple(command) not in allowed:
        raise RuntimeError(f"unexpected device command: {command_text(command)}")
    if command and command[0] in {"mount", "umount"} and not approved(args):
        raise RuntimeError("mount/umount command requires approval")


def write_step_capture(store: EvidenceStore,
                       name: str,
                       command: list[str],
                       text: str,
                       *,
                       ok: bool,
                       rc: int | None,
                       status: str,
                       duration: float,
                       skipped: bool,
                       error: str = "") -> Step:
    rel = f"steps/{name}.txt"
    body = "$ " + command_text(command) + "\n" + text.rstrip() + "\n"
    path = store.write_text(rel, body)
    return Step(name, command_text(command), ok, rc, status, duration, str(path.relative_to(store.run_dir)), skipped, error)


def execute_device_step(store: EvidenceStore,
                        args: argparse.Namespace,
                        name: str,
                        command: list[str],
                        execute: bool,
                        timeout: float | None = None) -> Step:
    validate_device_command(args, command)
    if not execute:
        return write_step_capture(
            store,
            name,
            command,
            "[plan] not executed",
            ok=True,
            rc=0,
            status="planned",
            duration=0.0,
            skipped=True,
        )
    capture = run_capture(args, name, command, timeout=timeout or args.timeout)
    text = strip_cmdv1_text(capture.text) if capture.text else capture.error
    step = write_step_capture(
        store,
        name,
        command,
        text,
        ok=capture.ok,
        rc=capture.rc,
        status=capture.status,
        duration=capture.duration_sec,
        skipped=False,
        error=capture.error,
    )
    raw_path = store.write_text(f"steps/{name}.raw.txt", capture.text if capture.text else capture.error + "\n")
    data = capture_to_manifest(capture)
    data["file"] = str(raw_path.relative_to(store.run_dir))
    return step


def refusal_manifest(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": "selinuxfs-mount-live-executor-approval-required",
        "pass": True,
        "reason": "exact V399 approval phrase and mutation flags are required",
        "next_step": "review V398 approval packet before approved V399 mount smoke",
        "host": collect_host_metadata(),
        "approval_phrase": APPROVAL_PHRASE,
        "approval_supplied": False,
        "steps": [],
        "remaining_blockers": [APPROVAL_BLOCKER],
        "device_commands_executed": False,
        "device_mutations": False,
        "daemon_start_executed": False,
        "wifi_bringup_executed": False,
    }


def classify_run(args: argparse.Namespace, steps: list[Step]) -> tuple[str, bool, str, str, list[str], bool]:
    if args.command == "plan":
        return (
            "selinuxfs-mount-live-executor-plan-ready",
            True,
            "plan-only; no device commands executed",
            "run only after V398 approval packet and exact V399 approval",
            [APPROVAL_BLOCKER],
            False,
        )
    mount_step = next((step for step in steps if step.command == "mount selinuxfs /sys/fs/selinux selinuxfs"), None)
    umount_step = next((step for step in steps if step.command == "umount /sys/fs/selinux"), None)
    status_step = next((step for step in steps if step.command == "stat /sys/fs/selinux/status"), None)
    if args.command == "run":
        mount_ok = bool(mount_step and mount_step.ok)
        already_mounted = bool(mount_step and "busy" in (mount_step.error + " " + mount_step.status).lower())
        if (mount_ok or already_mounted) and status_step and status_step.ok:
            return (
                "selinuxfs-mount-live-executor-run-pass",
                True,
                "selinuxfs mounted and status page is visible",
                "run V397 proof again, then plan service-manager clean-start packet",
                [],
                True,
            )
        return (
            "selinuxfs-mount-live-executor-run-review",
            False,
            "selinuxfs mount did not produce a visible status page",
            "inspect mount/status evidence and cleanup if needed",
            ["selinuxfs-status-page"],
            True,
        )
    if umount_step and umount_step.ok:
        return (
            "selinuxfs-mount-live-executor-cleanup-pass",
            True,
            "selinuxfs cleanup command completed",
            "rerun V397 proof to confirm post-cleanup state",
            [],
            True,
        )
    return (
        "selinuxfs-mount-live-executor-cleanup-review",
        False,
        "selinuxfs cleanup did not complete cleanly",
        "inspect cleanup evidence manually",
        ["selinuxfs-cleanup"],
        True,
    )


def render_summary(manifest: dict[str, Any]) -> str:
    lines = [
        "# V399 SELinuxfs Mount Live Executor",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- device_mutations: `{manifest['device_mutations']}`",
        f"- daemon_start_executed: `{manifest['daemon_start_executed']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        "",
        "## Approval Phrase",
        "",
        f"`{manifest['approval_phrase']}`",
        "",
        "## Steps",
        "",
    ]
    for step in manifest.get("steps", []):
        lines.append(f"- `{step['name']}` ok=`{step['ok']}` skipped=`{step['skipped']}` command=`{step['command']}`")
    return "\n".join(lines) + "\n"


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    if args.command in {"run", "cleanup"} and not approved(args):
        return refusal_manifest(args)
    execute = args.command in {"run", "cleanup"}
    steps: list[Step] = []
    for index, command in enumerate(command_plan(args.command), start=1):
        name = f"{index:02d}-" + command[0].replace("/", "-")
        steps.append(execute_device_step(store, args, name, command, execute=execute))
    decision, pass_ok, reason, next_step, blockers, mutated = classify_run(args, steps)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "approval_phrase": APPROVAL_PHRASE,
        "approval_supplied": approved(args),
        "steps": [asdict(step) for step in steps],
        "remaining_blockers": blockers,
        "device_commands_executed": execute,
        "device_mutations": mutated,
        "daemon_start_executed": False,
        "wifi_bringup_executed": False,
        "guardrails": [
            "exact approval phrase required before mount/umount",
            "mount command limited to selinuxfs /sys/fs/selinux",
            "cleanup command limited to umount /sys/fs/selinux",
            "no helper deploy",
            "no service-manager or Android daemon start",
            "no Wi-Fi HAL/start/scan/connect",
            "no SELinux policy write or enforcement change",
        ],
    }


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
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"device_mutations: {manifest['device_mutations']}")
    print(f"daemon_start_executed: {manifest['daemon_start_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

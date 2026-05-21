#!/usr/bin/env python3
"""V522 Android handoff wrapper for V521 companion-service recapture.

Live mode temporarily flashes a known Android boot image, boots Android, waits
for boot-complete, runs the V521 read-only companion recapture, then restores
the native init boot image. It does not enable Wi-Fi, scan, connect, link up
interfaces, change credentials, start Wi-Fi daemons directly, or route traffic.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from dataclasses import asdict
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore
from android_hwservice_handoff_v424 import (
    DEFAULT_BOOT_BLOCK,
    DEFAULT_BRIDGE_HOST,
    DEFAULT_BRIDGE_PORT,
    DEFAULT_NATIVE_EXPECT_VERSION,
    DEFAULT_NATIVE_IMAGE,
    DEFAULT_REMOTE_ANDROID_IMAGE,
    StepResult,
    build_step_plan as build_v424_step_plan,
    execute_bridge_step,
    execute_step,
    image_context,
    require_approval,
    step_text,
    wait_for_adb_state,
    write_step,
)
from android_hwservice_settled_handoff_v425 import (
    DEFAULT_BOOT_COMPLETE_TIMEOUT,
    DEFAULT_SETTLE_SLEEP,
    settle_step,
    wait_for_boot_complete,
)


DEFAULT_OUT_DIR = Path("tmp/wifi/v522-android-companion-recapture-handoff")
FORBIDDEN_PLAN_PATTERNS = (
    re.compile(r"\bcmd\s+wifi\b", re.IGNORECASE),
    re.compile(r"\bsvc\s+wifi\b", re.IGNORECASE),
    re.compile(r"\biw\b.*\b(scan|connect|set)\b", re.IGNORECASE),
    re.compile(r"\bwpa_cli\b", re.IGNORECASE),
    re.compile(r"\b(?:ping|curl|wget|nc|netcat|telnet|iperf3?|nslookup|dig|host)\b", re.IGNORECASE),
    re.compile(r"\bip\s+link\s+set\b", re.IGNORECASE),
    re.compile(r"\brfkill\s+(?:un)?block\b", re.IGNORECASE),
    re.compile(r"\b(?:insmod|rmmod|modprobe)\b", re.IGNORECASE),
    re.compile(r">\s*/sys/", re.IGNORECASE),
    re.compile(r"\bsetprop\b", re.IGNORECASE),
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--native-image", type=Path, default=DEFAULT_NATIVE_IMAGE)
    parser.add_argument("--native-expect-version", default=DEFAULT_NATIVE_EXPECT_VERSION)
    parser.add_argument("--android-boot-image", action="append", type=Path, default=[])
    parser.add_argument("--adb", default="adb")
    parser.add_argument("--serial", default="")
    parser.add_argument("--boot-block", default=DEFAULT_BOOT_BLOCK)
    parser.add_argument("--remote-android-image", default=DEFAULT_REMOTE_ANDROID_IMAGE)
    parser.add_argument("--bridge-host", default=DEFAULT_BRIDGE_HOST)
    parser.add_argument("--bridge-port", type=int, default=DEFAULT_BRIDGE_PORT)
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--recovery-timeout", type=int, default=180)
    parser.add_argument("--android-timeout", type=int, default=300)
    parser.add_argument("--boot-complete-timeout", type=int, default=DEFAULT_BOOT_COMPLETE_TIMEOUT)
    parser.add_argument("--settle-sleep", type=int, default=DEFAULT_SETTLE_SLEEP)
    parser.add_argument("--allow-android-boot-flash", action="store_true")
    parser.add_argument("--assume-yes", action="store_true")
    parser.add_argument("--i-understand-native-rollback", action="store_true")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("plan")
    subparsers.add_parser("dry-run")
    subparsers.add_parser("run")
    return parser.parse_args()


def v521_out_dir(store: EvidenceStore) -> Path:
    return store.run_dir / "v521-android-companion-recapture-run"


def v522_step_plan(args: argparse.Namespace, store: EvidenceStore, android_image: Any, native_image: Any) -> list[tuple[str, list[str] | str, int]]:
    base = build_v424_step_plan(args, store, android_image, native_image)
    plan: list[tuple[str, list[str] | str, int]] = []
    for name, command, timeout in base:
        if name == "v423-android-hwservice-inventory":
            plan.append(("wait-boot-complete", "wait_for_boot_complete", args.boot_complete_timeout))
            plan.append(("settle-after-boot-complete", "settle_step", args.settle_sleep + args.timeout))
            v521_command = [
                "python3",
                "scripts/revalidation/native_wifi_android_companion_recapture_v521.py",
                "--out-dir",
                str(v521_out_dir(store)),
                "--adb",
                args.adb,
                "--timeout",
                str(args.timeout),
            ]
            if args.serial:
                v521_command.extend(["--serial", args.serial])
            v521_command.append("run")
            plan.append(("v521-android-companion-recapture", v521_command, max(args.timeout * 12, 420)))
        else:
            plan.append((name, command, timeout))
    return plan


def contains_forbidden_plan_command(plan: list[tuple[str, list[str] | str, int]]) -> list[str]:
    offenders: list[str] = []
    for name, command, _ in plan:
        text = " ".join(command) if isinstance(command, list) else command
        for pattern in FORBIDDEN_PLAN_PATTERNS:
            if pattern.search(text):
                offenders.append(f"{name}: {pattern.pattern}")
    return offenders


def load_v521_result(store: EvidenceStore) -> dict[str, Any]:
    manifest = v521_out_dir(store) / "manifest.json"
    if not manifest.exists():
        return {"decision": "missing", "pass": False, "_path": str(manifest)}
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["_path"] = str(manifest)
    return payload


def execute_plan(args: argparse.Namespace, store: EvidenceStore, execute: bool) -> tuple[list[StepResult], dict[str, Any], str, bool]:
    native_image, android_images, android_image = image_context(args)
    approval_ok, missing_flags = require_approval(args)
    context: dict[str, Any] = {
        "native_image": asdict(native_image),
        "android_images": [asdict(image) for image in android_images],
        "android_image": asdict(android_image) if android_image else None,
        "approval_ok": approval_ok,
        "missing_approval_flags": missing_flags,
        "v521_out_dir": str(v521_out_dir(store)),
    }
    if not native_image.present or not native_image.aligned_4k or not native_image.android_magic or not native_image.native_marker:
        return [], context, "v522-handoff-missing-native-rollback", False
    if android_image is None:
        return [], context, "v522-handoff-missing-android-boot", False
    if android_image.sha256 == native_image.sha256:
        return [], context, "v522-handoff-image-collision", False
    if args.command == "run" and not approval_ok:
        return [], context, "v522-handoff-approval-required", False

    plan = v522_step_plan(args, store, android_image, native_image)
    offenders = contains_forbidden_plan_command(plan)
    if offenders:
        context["forbidden_plan_commands"] = offenders
        return [], context, "v522-handoff-forbidden-command-blocked", False

    steps: list[StepResult] = []
    if args.command == "plan":
        for name, command, _ in plan:
            steps.append(write_step(store, name, command, "[plan] not executed\n", "", 0, 0.0, skipped=True, ok_override=True))
        return steps, context, "v522-handoff-plan-ready", True

    restore_entry = next(item for item in plan if item[0] == "restore-native")
    v521_ok = False
    boot_state: dict[str, Any] = {"props": {}, "samples": [], "boot_completed": False}

    for name, command, timeout in plan:
        if isinstance(command, str) and command.startswith("bridge:"):
            bridge_payload = command.split(" ", 1)[1]
            step = execute_bridge_step(store, args, name, bridge_payload, timeout, execute=execute)
        elif name == "wait-recovery":
            step = wait_for_adb_state(args, {"recovery"}, timeout, execute, store, name)
        elif name == "wait-android":
            step = wait_for_adb_state(args, {"device"}, timeout, execute, store, name)
        elif name == "wait-android-before-rollback":
            step = wait_for_adb_state(args, {"device"}, timeout, execute, store, name)
        elif name == "wait-rollback-recovery":
            step = wait_for_adb_state(args, {"recovery"}, timeout, execute, store, name)
        elif name == "wait-boot-complete":
            step, boot_state = wait_for_boot_complete(args, store, execute)
            if execute and not step.ok:
                steps.append(step)
                continue
        elif name == "settle-after-boot-complete":
            step = settle_step(args, store, execute)
        else:
            step = execute_step(store, name, command, timeout, execute)
        steps.append(step)

        if name == "remote-android-sha" and execute and step.ok and android_image.sha256 not in step_text(store, step):
            return steps, context, "v522-handoff-remote-sha-mismatch", False
        if name == "flash-android-boot" and execute and not step.ok:
            context["emergency_rollback_attempted"] = True
            context["emergency_rollback_reason"] = "flash-android-boot failed"
            restore_name, restore_command, restore_timeout = restore_entry
            rollback_step = execute_step(store, restore_name, restore_command, restore_timeout, execute=True)
            steps.append(rollback_step)
            context["emergency_rollback_ok"] = rollback_step.ok
            return steps, context, "v522-handoff-flash-failed-rollback-attempted", False
        if name == "readback-android-boot" and execute:
            readback_text = step_text(store, step) if step.file else ""
            if not step.ok or android_image.sha256 not in readback_text:
                context["emergency_rollback_attempted"] = True
                context["emergency_rollback_reason"] = "Android boot readback failed or SHA did not match"
                restore_name, restore_command, restore_timeout = restore_entry
                rollback_step = execute_step(store, restore_name, restore_command, restore_timeout, execute=True)
                steps.append(rollback_step)
                context["emergency_rollback_ok"] = rollback_step.ok
                return steps, context, "v522-handoff-readback-failed-rollback-attempted", False
        if name == "v521-android-companion-recapture":
            v521_ok = step.ok
        if execute and not step.ok and name not in {"wait-boot-complete"}:
            return steps, context, f"v522-handoff-failed-{name}", False

    context["boot_state"] = boot_state
    context["v521_result"] = {
        "path": load_v521_result(store).get("_path"),
        "decision": load_v521_result(store).get("decision"),
        "pass": load_v521_result(store).get("pass"),
        "reason": load_v521_result(store).get("reason"),
        "next_step": load_v521_result(store).get("next_step"),
    }
    if execute and not boot_state.get("boot_completed"):
        return steps, context, "v522-handoff-bootcomplete-missing-rollback-complete", False
    if execute and not v521_ok:
        return steps, context, "v522-handoff-v521-capture-failed-rollback-complete", False
    return steps, context, "v522-handoff-pass" if execute else "v522-handoff-dryrun-ready", True


def reason_for(decision: str) -> str:
    return {
        "v522-handoff-plan-ready": "execution plan generated without device mutation",
        "v522-handoff-dryrun-ready": "dry-run recorded all steps without device mutation",
        "v522-handoff-approval-required": "live run refused because approval flags are missing",
        "v522-handoff-missing-native-rollback": "native rollback image is missing or does not contain the expected version marker",
        "v522-handoff-missing-android-boot": "no Android boot candidate passed local safety checks",
        "v522-handoff-image-collision": "Android and native rollback images unexpectedly have the same hash",
        "v522-handoff-forbidden-command-blocked": "handoff plan contains a forbidden active Wi-Fi command pattern",
        "v522-handoff-pass": "Android handoff, V521 recapture, and native rollback completed",
        "v522-handoff-v521-capture-failed-rollback-complete": "V521 Android recapture failed, but native rollback steps completed",
        "v522-handoff-bootcomplete-missing-rollback-complete": "Android boot-complete was not observed, but rollback steps completed",
    }.get(decision, decision)


def render_summary(manifest: dict[str, Any]) -> str:
    step_rows = [
        [
            item["name"],
            "skip" if item["skipped"] else ("ok" if item["ok"] else "fail"),
            str(item["rc"]),
            f"{item['duration_sec']:.3f}s",
            item["file"],
        ]
        for item in manifest["steps"]
    ]
    image_rows = [
        [
            image["path"],
            str(image["present"]),
            str(image["size"]),
            str(image["android_magic"]),
            str(image["native_marker"]),
            image["sha256"][:16] if image["sha256"] else "",
        ]
        for image in manifest["context"]["android_images"]
    ]
    return "\n".join([
        "# V522 Android Companion Recapture Handoff",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- approval_ok: `{manifest['context']['approval_ok']}`",
        f"- missing_approval_flags: `{', '.join(manifest['context']['missing_approval_flags']) or '-'}`",
        f"- v521_out_dir: `{manifest['context']['v521_out_dir']}`",
        "",
        "## Native Rollback Image",
        "",
        markdown_table(
            ["path", "present", "size", "android magic", "native marker", "sha256 prefix"],
            [[
                manifest["context"]["native_image"]["path"],
                str(manifest["context"]["native_image"]["present"]),
                str(manifest["context"]["native_image"]["size"]),
                str(manifest["context"]["native_image"]["android_magic"]),
                str(manifest["context"]["native_image"]["native_marker"]),
                manifest["context"]["native_image"]["sha256"][:16] if manifest["context"]["native_image"]["sha256"] else "",
            ]],
        ),
        "",
        "## Android Boot Candidates",
        "",
        markdown_table(["path", "present", "size", "android magic", "native marker", "sha256 prefix"], image_rows if image_rows else [["-", "-", "-", "-", "-", "-"]]),
        "",
        "## Steps",
        "",
        markdown_table(["step", "status", "rc", "duration", "file"], step_rows if step_rows else [["none", "-", "-", "-", "-"]]),
        "",
        "## V521 Result",
        "",
        "```json",
        json.dumps(manifest["context"].get("v521_result", {}), ensure_ascii=False, indent=2, sort_keys=True),
        "```",
        "",
        "## Guardrails",
        "",
        "- live `run` requires explicit approval flags.",
        "- `plan` and `dry-run` do not reboot, enter recovery, or write boot.",
        "- Android work is limited to V521 read-only companion recapture.",
        "- no Wi-Fi scan/connect/link-up/credential/DHCP/routing.",
        "- no direct Wi-Fi daemon start, rfkill/sysfs write, module load/unload, or property mutation.",
        "",
    ])


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    steps, context, decision, pass_ok = execute_plan(args, store, execute=args.command == "run")
    manifest = {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason_for(decision),
        "host": collect_host_metadata(),
        "context": context,
        "steps": [asdict(step) for step in steps],
        "device_commands_executed": args.command == "run",
        "device_mutations": args.command == "run",
        "boot_partition_write_executed": args.command == "run" and decision != "v522-handoff-approval-required",
        "daemon_start_executed": False,
        "wifi_hal_start_executed": False,
        "wlan_driver_state_write_executed": False,
        "scan_connect_executed": False,
        "wifi_bringup_executed": False,
        "external_ping_executed": False,
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"v521: {manifest['context'].get('v521_result', {})}")
    print(f"device_mutations: {manifest['device_mutations']}")
    print(f"boot_partition_write_executed: {manifest['boot_partition_write_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

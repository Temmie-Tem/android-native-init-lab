#!/usr/bin/env python3
"""V622 Android handoff for same-boot MDM helper timing recapture.

This wrapper temporarily boots a known Android boot image, waits for
`sys.boot_completed=1`, runs the V622 read-only Android timing collector, then
restores the native init boot image. It does not enable Wi-Fi, scan, connect,
start Wi-Fi HALs, write subsystem sysfs nodes, route traffic, use credentials,
or ping externally.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
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
    contains_forbidden_active_wifi,
    execute_bridge_step,
    execute_step,
    image_context,
    reason_for as v424_reason_for,
    require_approval,
    step_text,
    wait_for_adb_state,
    write_step,
)
from android_hwservice_settled_handoff_v425 import (
    DEFAULT_BOOT_COMPLETE_TIMEOUT,
    DEFAULT_SETTLE_SLEEP,
    prop_poll_command,
    settle_step,
    wait_for_boot_complete,
)


DEFAULT_OUT_DIR = Path("tmp/wifi/v622-android-mdm-helper-timing-handoff")


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


def v622_out_dir(store: EvidenceStore) -> Path:
    return store.run_dir / "v622-android-mdm-helper-timing-recapture-run"


def v622_step_plan(args: argparse.Namespace, store: EvidenceStore, android_image: Any, native_image: Any) -> list[tuple[str, list[str] | str, int]]:
    base = build_v424_step_plan(args, store, android_image, native_image)
    plan: list[tuple[str, list[str] | str, int]] = []
    collector_timeout = max(args.timeout * 10, 300)
    for name, command, timeout in base:
        if name == "v423-android-hwservice-inventory":
            plan.append(("wait-boot-complete", prop_poll_command(args), args.boot_complete_timeout))
            plan.append(("settle-after-boot-complete", f"sleep {args.settle_sleep}", args.settle_sleep + args.timeout))
            v622_command = [
                "python3",
                "scripts/revalidation/native_wifi_android_mdm_helper_timing_recapture_v622.py",
                "--out-dir",
                str(v622_out_dir(store)),
                "--adb",
                args.adb,
                "--timeout",
                str(max(15.0, float(args.timeout))),
            ]
            if args.serial:
                v622_command.extend(["--serial", args.serial])
            v622_command.append("run")
            plan.append(("v622-android-mdm-helper-timing-recapture", v622_command, collector_timeout))
        else:
            plan.append((name, command, timeout))
    return plan


def load_v622_result(store: EvidenceStore) -> dict[str, Any]:
    manifest = v622_out_dir(store) / "manifest.json"
    if not manifest.exists():
        return {"decision": "missing", "pass": False, "_path": str(manifest)}
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["_path"] = str(manifest)
    return payload


def build_comparison(store: EvidenceStore, boot_state: dict[str, Any]) -> dict[str, Any]:
    v622 = load_v622_result(store)
    android_summary = v622.get("android_summary") or {}
    timing = android_summary.get("timing") or {}
    boot_complete = bool(boot_state.get("boot_completed"))
    if not boot_complete:
        decision = "v622-handoff-bootcomplete-missing"
        pass_ok = False
        reason = "Android boot-complete gate did not pass before V622"
    elif not v622.get("pass"):
        decision = "v622-handoff-v622-failed-rollback-complete"
        pass_ok = False
        reason = "V622 Android same-boot timing collector failed after rollback completed"
    else:
        decision = str(v622.get("decision") or "v622-handoff-review-required")
        pass_ok = bool(v622.get("pass"))
        reason = str(v622.get("reason") or decision)
    return {
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "boot_complete": boot_complete,
        "boot_props": boot_state.get("props") or {},
        "state": {
            "mdm_launcher_boottime_ms": timing.get("mdm_launcher_boottime_ms"),
            "mdm_helper_boottime_ms": timing.get("mdm_helper_boottime_ms"),
            "service_notifier_180_ms": timing.get("service_notifier_180_ms"),
            "launcher_to_service_notifier_180_ms": timing.get("launcher_to_service_notifier_180_ms"),
            "helper_to_service_notifier_180_ms": timing.get("helper_to_service_notifier_180_ms"),
            "has_service_notifier_pair": android_summary.get("has_service_notifier_pair"),
            "has_wlan_pd": android_summary.get("has_wlan_pd"),
            "has_sysmon_esoc0": android_summary.get("has_sysmon_esoc0"),
        },
        "v622": {
            "path": v622.get("_path"),
            "decision": v622.get("decision"),
            "pass": v622.get("pass"),
            "reason": v622.get("reason"),
            "next_step": v622.get("next_step"),
        },
    }


def execute_plan(args: argparse.Namespace, store: EvidenceStore, execute: bool) -> tuple[list[StepResult], dict[str, Any], str, bool]:
    native_image, android_images, android_image = image_context(args)
    approval_ok, missing_flags = require_approval(args)
    context: dict[str, Any] = {
        "native_image": asdict(native_image),
        "android_images": [asdict(image) for image in android_images],
        "android_image": asdict(android_image) if android_image else None,
        "approval_ok": approval_ok,
        "missing_approval_flags": missing_flags,
        "v622_out_dir": str(v622_out_dir(store)),
        "settle_sleep_sec": args.settle_sleep,
    }
    if not native_image.present or not native_image.aligned_4k or not native_image.android_magic or not native_image.native_marker:
        return [], context, "v622-handoff-missing-native-rollback", False
    if android_image is None:
        return [], context, "v622-handoff-missing-android-boot", False
    if android_image.sha256 == native_image.sha256:
        return [], context, "v622-handoff-image-collision", False
    if args.command == "run" and not approval_ok:
        return [], context, "v622-handoff-approval-required", False

    plan = v622_step_plan(args, store, android_image, native_image)
    offenders = contains_forbidden_active_wifi(plan)
    if offenders:
        context["forbidden_active_wifi_steps"] = offenders
        return [], context, "v622-handoff-active-wifi-command-blocked", False

    steps: list[StepResult] = []
    if args.command == "plan":
        for name, command, _ in plan:
            steps.append(write_step(store, name, command, "[plan] not executed\n", "", 0, 0.0, skipped=True, ok_override=True))
        return steps, context, "v622-handoff-plan-ready", True

    restore_entry = next(item for item in plan if item[0] == "restore-native")
    failure_after_rollback = ""
    skip_collector = False
    boot_state: dict[str, Any] = {"props": {}, "samples": [], "boot_completed": False}
    v622_step_ok = False

    for name, command, timeout in plan:
        if skip_collector and name in {"settle-after-boot-complete", "v622-android-mdm-helper-timing-recapture"}:
            step = write_step(store, name, command, "[skipped] boot-complete gate did not pass\n", "", 0, 0.0, skipped=True, ok_override=True)
            steps.append(step)
            continue

        if isinstance(command, str) and command.startswith("bridge:"):
            step = execute_bridge_step(store, args, name, command.split(" ", 1)[1], timeout, execute)
        elif name in {"wait-recovery", "wait-rollback-recovery"}:
            step = wait_for_adb_state(args, {"recovery"}, timeout, execute, store, name)
        elif name in {"wait-android", "wait-android-before-rollback"}:
            step = wait_for_adb_state(args, {"device"}, timeout, execute, store, name)
        elif name == "wait-boot-complete":
            step, boot_state = wait_for_boot_complete(args, store, execute)
            context["boot_state"] = boot_state
        elif name == "settle-after-boot-complete":
            step = settle_step(args, store, execute)
        else:
            step = execute_step(store, name, command, timeout, execute)
        steps.append(step)

        if name == "remote-android-sha" and execute and step.ok and android_image.sha256 not in step_text(store, step):
            return steps, context, "v622-handoff-remote-sha-mismatch", False
        if name == "flash-android-boot" and execute and not step.ok:
            context["emergency_rollback_attempted"] = True
            context["emergency_rollback_reason"] = "flash-android-boot failed after boot write was requested"
            restore_name, restore_command, restore_timeout = restore_entry
            rollback_step = execute_step(store, restore_name, restore_command, restore_timeout, execute=True)
            steps.append(rollback_step)
            context["emergency_rollback_ok"] = rollback_step.ok
            return steps, context, "v622-handoff-flash-failed-rollback-attempted", False
        if name == "readback-android-boot" and execute:
            readback_text = step_text(store, step) if step.file else ""
            if not step.ok or android_image.sha256 not in readback_text:
                context["emergency_rollback_attempted"] = True
                context["emergency_rollback_reason"] = "Android boot readback failed or SHA did not match"
                restore_name, restore_command, restore_timeout = restore_entry
                rollback_step = execute_step(store, restore_name, restore_command, restore_timeout, execute=True)
                steps.append(rollback_step)
                context["emergency_rollback_ok"] = rollback_step.ok
                return steps, context, "v622-handoff-readback-failed-rollback-attempted", False
        if name == "wait-boot-complete" and execute and not step.ok:
            failure_after_rollback = "v622-handoff-failed-wait-boot-complete-rollback-complete"
            skip_collector = True
            continue
        if name == "v622-android-mdm-helper-timing-recapture":
            v622_step_ok = step.ok
            if execute:
                continue
        if execute and not step.ok:
            return steps, context, f"v622-handoff-failed-{name}", False

    if execute:
        comparison = build_comparison(store, boot_state)
        context["comparison"] = comparison
        if failure_after_rollback:
            return steps, context, failure_after_rollback, False
        if not v622_step_ok:
            return steps, context, "v622-handoff-v622-failed-rollback-complete", False
        return steps, context, comparison["decision"], bool(comparison["pass"])
    return steps, context, "v622-handoff-dryrun-ready", True


def reason_for(decision: str, context: dict[str, Any]) -> str:
    comparison = context.get("comparison") or {}
    if comparison.get("decision") == decision:
        return str(comparison.get("reason") or decision)
    return {
        "v622-handoff-plan-ready": "execution plan generated without device mutation",
        "v622-handoff-dryrun-ready": "dry-run recorded all steps without device mutation",
        "v622-handoff-approval-required": "live run refused because approval flags are missing",
        "v622-handoff-missing-native-rollback": "native rollback image is missing or does not contain the expected version marker",
        "v622-handoff-missing-android-boot": "no Android boot candidate passed local safety checks",
        "v622-handoff-image-collision": "Android and native rollback images unexpectedly have the same hash",
        "v622-handoff-active-wifi-command-blocked": "handoff plan contains a forbidden active Wi-Fi command pattern",
        "v622-handoff-failed-wait-boot-complete-rollback-complete": "Android boot-complete gate failed, and native rollback completed",
        "v622-handoff-v622-failed-rollback-complete": "V622 Android timing collector failed, and native rollback completed",
        "v622-handoff-flash-failed-rollback-attempted": "Android boot flash failed and native rollback was attempted from recovery",
        "v622-handoff-readback-failed-rollback-attempted": "Android boot readback failed and native rollback was attempted from recovery",
    }.get(decision, v424_reason_for(decision))


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
    comparison = manifest["context"].get("comparison") or {}
    state = comparison.get("state") or {}
    state_rows = [[key, str(value)] for key, value in state.items()]
    return "\n".join([
        "# V622 Android MDM Helper Timing Handoff",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- approval_ok: `{manifest['context']['approval_ok']}`",
        f"- missing_approval_flags: `{', '.join(manifest['context']['missing_approval_flags']) or '-'}`",
        f"- v622_out_dir: `{manifest['context']['v622_out_dir']}`",
        "",
        "## Comparison",
        "",
        f"- boot_complete: `{comparison.get('boot_complete', '-')}`",
        f"- v622_decision: `{(comparison.get('v622') or {}).get('decision', '-')}`",
        f"- v622_next_step: `{(comparison.get('v622') or {}).get('next_step', '-')}`",
        "",
        markdown_table(["state", "value"], state_rows if state_rows else [["-", "-"]]),
        "",
        "## Steps",
        "",
        markdown_table(["step", "status", "rc", "duration", "file"], step_rows if step_rows else [["none", "-", "-", "-", "-"]]),
        "",
        "## Guardrails",
        "",
        "- `run` requires explicit approval flags.",
        "- `plan` and `dry-run` do not reboot, enter recovery, or write boot.",
        "- Live mode temporarily flashes Android boot, runs V622 read-only collection, then restores native init.",
        "- No Wi-Fi enable/disable, scan/connect/link-up/credential/DHCP/routing changes.",
        "- No external ping or network reachability probe.",
        "- No direct Wi-Fi daemon start, HAL start, rfkill/sysfs write, module load/unload, or property mutation.",
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
        "reason": reason_for(decision, context),
        "host": collect_host_metadata(),
        "context": context,
        "steps": [asdict(step) for step in steps],
        "device_commands_executed": args.command == "run",
        "device_mutations": args.command == "run" and decision not in {
            "v622-handoff-approval-required",
            "v622-handoff-missing-native-rollback",
            "v622-handoff-missing-android-boot",
            "v622-handoff-image-collision",
            "v622-handoff-active-wifi-command-blocked",
        },
        "daemon_start_executed": False,
        "service_manager_start_executed": False,
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
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"device_mutations: {manifest['device_mutations']}")
    print(f"daemon_start_executed: {manifest['daemon_start_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    print(f"out_dir: {store.run_dir}")
    return 0 if pass_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

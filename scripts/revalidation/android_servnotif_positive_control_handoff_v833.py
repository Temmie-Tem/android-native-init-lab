#!/usr/bin/env python3
"""V833 Android handoff for service-notifier positive control.

Live mode temporarily flashes a known Android boot image, waits for Android
boot-complete, runs the V833 bounded service-notifier positive-control
collector, then restores the native v724 boot image. It does not enable Wi-Fi,
scan, connect, use credentials, request DHCP, alter routes, ping externally, or
start/stop Android Wi-Fi services.
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
    DEFAULT_REMOTE_ANDROID_IMAGE,
    StepResult,
    build_step_plan as build_v424_step_plan,
    contains_forbidden_active_wifi,
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


DEFAULT_OUT_DIR = Path("tmp/wifi/v833-android-servnotif-positive-control-handoff")
DEFAULT_NATIVE_IMAGE = Path("stage3/boot_linux_v725_fasttransport.img")
DEFAULT_NATIVE_EXPECT_VERSION = "A90 Linux init 0.9.244 (v725-fasttransport)"
DEFAULT_LOCAL_HELPER = Path("tmp/wifi/v833-servnotif-helper-build/a90_servnotif_listener_probe")


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
    parser.add_argument("--local-helper", type=Path, default=DEFAULT_LOCAL_HELPER)
    parser.add_argument("--allow-android-boot-flash", action="store_true")
    parser.add_argument("--assume-yes", action="store_true")
    parser.add_argument("--i-understand-native-rollback", action="store_true")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("plan")
    subparsers.add_parser("dry-run")
    subparsers.add_parser("run")
    return parser.parse_args()


def v833_out_dir(store: EvidenceStore) -> Path:
    return store.run_dir / "v833-android-servnotif-positive-control-run"


def v833_step_plan(args: argparse.Namespace, store: EvidenceStore, android_image: Any, native_image: Any) -> list[tuple[str, list[str] | str, int]]:
    base = build_v424_step_plan(args, store, android_image, native_image)
    plan: list[tuple[str, list[str] | str, int]] = [
        (
            "build-v833-helper",
            [
                "scripts/revalidation/build_servnotif_listener_probe_helper.sh",
                str(repo_path(args.local_helper)),
            ],
            max(args.timeout, 120),
        )
    ]
    for name, command, timeout in base:
        if name == "v423-android-hwservice-inventory":
            v833_command = [
                "python3",
                "scripts/revalidation/native_wifi_android_servnotif_positive_control_v833.py",
                "--out-dir",
                str(v833_out_dir(store)),
                "--adb",
                args.adb,
                "--timeout",
                str(args.timeout),
                "--local-helper",
                str(args.local_helper),
            ]
            if args.serial:
                v833_command.extend(["--serial", args.serial])
            v833_command.append("run")
            plan.append(("wait-boot-complete", "wait_for_boot_complete", args.boot_complete_timeout))
            plan.append(("settle-after-boot-complete", "settle_step", args.settle_sleep + args.timeout))
            plan.append(("v833-android-servnotif-positive-control", v833_command, max(args.timeout * 4, 180)))
        else:
            plan.append((name, command, timeout))
    return plan


def load_v833_result(store: EvidenceStore) -> dict[str, Any]:
    manifest_path = v833_out_dir(store) / "manifest.json"
    if not manifest_path.exists():
        return {"decision": "missing", "pass": False, "_path": str(manifest_path)}
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["_path"] = str(manifest_path)
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
        "v833_out_dir": str(v833_out_dir(store)),
        "local_helper": str(repo_path(args.local_helper)),
    }
    if not native_image.present or not native_image.aligned_4k or not native_image.android_magic or not native_image.native_marker:
        return [], context, "v833-handoff-missing-native-rollback", False
    if android_image is None:
        return [], context, "v833-handoff-missing-android-boot", False
    if android_image.sha256 == native_image.sha256:
        return [], context, "v833-handoff-image-collision", False
    if args.command == "run" and not approval_ok:
        return [], context, "v833-handoff-approval-required", False

    plan = v833_step_plan(args, store, android_image, native_image)
    offenders = contains_forbidden_active_wifi(plan)
    if offenders:
        context["forbidden_active_wifi_steps"] = offenders
        return [], context, "v833-handoff-active-wifi-command-blocked", False
    if args.command == "plan":
        steps = [
            write_step(store, name, command, "[plan] not executed\n", "", 0, 0.0, skipped=True, ok_override=True)
            for name, command, _ in plan
        ]
        return steps, context, "v833-handoff-plan-ready", True

    steps: list[StepResult] = []
    restore_entry = next(item for item in plan if item[0] == "restore-native")
    boot_state: dict[str, Any] = {"props": {}, "samples": [], "boot_completed": False}
    failure_after_rollback = ""
    skip_collector = False

    for name, command, timeout in plan:
        if skip_collector and name in {"settle-after-boot-complete", "v833-android-servnotif-positive-control"}:
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

        if name == "build-v833-helper" and execute and not step.ok:
            return steps, context, "v833-handoff-helper-build-failed", False
        if name == "remote-android-sha" and execute and step.ok and android_image.sha256 not in step_text(store, step):
            return steps, context, "v833-handoff-remote-sha-mismatch", False
        if name == "flash-android-boot" and execute and not step.ok:
            context["emergency_rollback_attempted"] = True
            context["emergency_rollback_reason"] = "flash-android-boot failed after boot write was requested"
            restore_name, restore_command, restore_timeout = restore_entry
            rollback_step = execute_step(store, restore_name, restore_command, restore_timeout, execute=True)
            steps.append(rollback_step)
            context["emergency_rollback_ok"] = rollback_step.ok
            return steps, context, "v833-handoff-flash-failed-rollback-attempted", False
        if name == "readback-android-boot" and execute:
            readback_text = step_text(store, step) if step.file else ""
            if not step.ok or android_image.sha256 not in readback_text:
                context["emergency_rollback_attempted"] = True
                context["emergency_rollback_reason"] = "Android boot readback failed or SHA did not match"
                restore_name, restore_command, restore_timeout = restore_entry
                rollback_step = execute_step(store, restore_name, restore_command, restore_timeout, execute=True)
                steps.append(rollback_step)
                context["emergency_rollback_ok"] = rollback_step.ok
                return steps, context, "v833-handoff-readback-failed-rollback-attempted", False
        if name == "wait-boot-complete" and execute and not step.ok:
            failure_after_rollback = "v833-handoff-failed-wait-boot-complete-rollback-complete"
            skip_collector = True
            continue
        if name == "v833-android-servnotif-positive-control" and execute and not step.ok:
            failure_after_rollback = "v833-handoff-v833-failed-rollback-complete"
            continue
        if execute and not step.ok:
            if name in {"wait-android-before-rollback", "reboot-recovery-for-rollback", "wait-rollback-recovery", "restore-native"}:
                return steps, context, f"v833-handoff-failed-{name}", False
            return steps, context, f"v833-handoff-failed-{name}", False

    v833_result = load_v833_result(store)
    context["v833_result"] = {
        "path": v833_result.get("_path"),
        "decision": v833_result.get("decision"),
        "pass": v833_result.get("pass"),
        "reason": v833_result.get("reason"),
        "next_step": v833_result.get("next_step"),
    }
    if execute and failure_after_rollback:
        return steps, context, failure_after_rollback, False
    if execute and not bool(v833_result.get("pass")):
        return steps, context, "v833-handoff-v833-result-review-rollback-complete", False
    return steps, context, "v833-handoff-pass" if execute else "v833-handoff-dryrun-ready", True


def reason_for(decision: str) -> str:
    return {
        "v833-handoff-plan-ready": "execution plan generated without device mutation",
        "v833-handoff-dryrun-ready": "dry-run recorded all steps without device mutation",
        "v833-handoff-approval-required": "live run refused because approval flags are missing",
        "v833-handoff-missing-native-rollback": "native rollback image is missing or does not contain expected v724 marker",
        "v833-handoff-missing-android-boot": "no Android boot candidate passed local safety checks",
        "v833-handoff-image-collision": "Android and native rollback images unexpectedly have the same hash",
        "v833-handoff-active-wifi-command-blocked": "handoff plan contains a forbidden active Wi-Fi command pattern",
        "v833-handoff-helper-build-failed": "V833 static helper build failed before live handoff",
        "v833-handoff-pass": "Android handoff, V833 positive-control, and native rollback completed",
        "v833-handoff-v833-failed-rollback-complete": "V833 collector failed, but native rollback completed",
        "v833-handoff-v833-result-review-rollback-complete": "V833 collector completed with a review/fail decision after rollback",
    }.get(decision, decision)


def render_summary(manifest: dict[str, Any]) -> str:
    step_rows = [
        [step["name"], "skip" if step["skipped"] else ("ok" if step["ok"] else "fail"), str(step["rc"]), f"{step['duration_sec']:.3f}s", step["file"]]
        for step in manifest["steps"]
    ]
    image_rows = [
        [image["path"], image["present"], image["size"], image["android_magic"], image["native_marker"], image["sha256"][:16] if image["sha256"] else ""]
        for image in manifest["context"]["android_images"]
    ]
    return "\n".join([
        "# V833 Android Service-notifier Positive-control Handoff",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- approval_ok: `{manifest['context']['approval_ok']}`",
        f"- v833_out_dir: `{manifest['context']['v833_out_dir']}`",
        "",
        "## Native Rollback Image",
        "",
        markdown_table(["path", "present", "size", "android magic", "native marker", "sha256 prefix"], [[
            manifest["context"]["native_image"]["path"],
            manifest["context"]["native_image"]["present"],
            manifest["context"]["native_image"]["size"],
            manifest["context"]["native_image"]["android_magic"],
            manifest["context"]["native_image"]["native_marker"],
            manifest["context"]["native_image"]["sha256"][:16] if manifest["context"]["native_image"]["sha256"] else "",
        ]]),
        "",
        "## Android Boot Candidates",
        "",
        markdown_table(["path", "present", "size", "android magic", "native marker", "sha256 prefix"], image_rows if image_rows else [["-", "-", "-", "-", "-", "-"]]),
        "",
        "## Steps",
        "",
        markdown_table(["step", "status", "rc", "duration", "file"], step_rows if step_rows else [["none", "-", "-", "-", "-"]]),
    ])


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    steps, context, decision, pass_ok = execute_plan(args, store, execute=args.command == "run")
    manifest = {
        "cycle": "v833",
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason_for(decision),
        "host": collect_host_metadata(),
        "context": context,
        "steps": [asdict(step) for step in steps],
        "device_commands_executed": args.command == "run",
        "device_mutations": args.command == "run" and decision not in {
            "v833-handoff-approval-required",
            "v833-handoff-missing-native-rollback",
            "v833-handoff-missing-android-boot",
            "v833-handoff-image-collision",
            "v833-handoff-active-wifi-command-blocked",
            "v833-handoff-helper-build-failed",
        },
        "boot_image_write_executed": args.command == "run" and decision not in {
            "v833-handoff-approval-required",
            "v833-handoff-missing-native-rollback",
            "v833-handoff-missing-android-boot",
            "v833-handoff-image-collision",
            "v833-handoff-active-wifi-command-blocked",
            "v833-handoff-helper-build-failed",
        },
        "wifi_bringup_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {decision}")
    print(f"pass: {pass_ok}")
    print(f"reason: {manifest['reason']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"boot_image_write_executed: {manifest['boot_image_write_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if pass_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

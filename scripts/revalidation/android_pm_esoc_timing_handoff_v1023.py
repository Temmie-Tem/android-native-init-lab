#!/usr/bin/env python3
"""V1023 Android handoff for early V1022 PM/eSoC timing capture.

This wrapper temporarily flashes a known Android boot image, starts the V1022
read-only sampler immediately after ADB reaches `device`, captures a late
fallback sample after boot-complete, then restores native init v724. It does not
start Wi-Fi, scan/connect, route traffic, ping externally, use credentials,
open eSoC/subsystem device nodes from native, or write GPIO/sysfs/debugfs state.
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
    BOOT_READBACK_BLOCK_SIZE,
    DEFAULT_BOOT_BLOCK,
    DEFAULT_BRIDGE_HOST,
    DEFAULT_BRIDGE_PORT,
    DEFAULT_REMOTE_ANDROID_IMAGE,
    StepResult,
    adb_base,
    contains_forbidden_active_wifi,
    execute_bridge_step,
    execute_step,
    image_context,
    remote_quote,
    require_approval,
    step_text,
    wait_for_adb_state,
    write_step,
)
from android_hwservice_settled_handoff_v425 import (
    DEFAULT_BOOT_COMPLETE_TIMEOUT,
    prop_poll_command,
    wait_for_boot_complete,
)


DEFAULT_OUT_DIR = Path("tmp/wifi/v1023-android-pm-esoc-timing-handoff")
DEFAULT_NATIVE_IMAGE = Path("stage3/boot_linux_v724.img")
DEFAULT_NATIVE_EXPECT_VERSION = "A90 Linux init 0.9.68 (v724)"
DEFAULT_REMOTE_NATIVE_IMAGE = "/tmp/native_init_boot.img"
DEFAULT_EARLY_SAMPLE_COUNT = 48
DEFAULT_EARLY_SAMPLE_SLEEP = 0.25
DEFAULT_LATE_SAMPLE_COUNT = 16
DEFAULT_LATE_SAMPLE_SLEEP = 0.5


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
    parser.add_argument("--remote-native-image", default=DEFAULT_REMOTE_NATIVE_IMAGE)
    parser.add_argument("--bridge-host", default=DEFAULT_BRIDGE_HOST)
    parser.add_argument("--bridge-port", type=int, default=DEFAULT_BRIDGE_PORT)
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--recovery-timeout", type=int, default=180)
    parser.add_argument("--android-timeout", type=int, default=300)
    parser.add_argument("--boot-complete-timeout", type=int, default=DEFAULT_BOOT_COMPLETE_TIMEOUT)
    parser.add_argument("--v1022-timeout", type=int, default=150)
    parser.add_argument("--early-sample-count", type=int, default=DEFAULT_EARLY_SAMPLE_COUNT)
    parser.add_argument("--early-sample-sleep", type=float, default=DEFAULT_EARLY_SAMPLE_SLEEP)
    parser.add_argument("--late-sample-count", type=int, default=DEFAULT_LATE_SAMPLE_COUNT)
    parser.add_argument("--late-sample-sleep", type=float, default=DEFAULT_LATE_SAMPLE_SLEEP)
    parser.add_argument("--allow-android-boot-flash", action="store_true")
    parser.add_argument("--assume-yes", action="store_true")
    parser.add_argument("--i-understand-native-rollback", action="store_true")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("plan")
    subparsers.add_parser("dry-run")
    subparsers.add_parser("run")
    return parser.parse_args()


def v1022_early_out_dir(store: EvidenceStore) -> Path:
    return store.run_dir / "v1022-early-android-pm-esoc-timing"


def v1022_late_out_dir(store: EvidenceStore) -> Path:
    return store.run_dir / "v1022-late-android-pm-esoc-timing"


def v1022_command(args: argparse.Namespace, out_dir: Path, sample_count: int, sample_sleep: float) -> list[str]:
    command = [
        "python3",
        "scripts/revalidation/native_wifi_android_pm_esoc_timing_v1022.py",
        "--out-dir",
        str(out_dir),
        "--adb",
        args.adb,
        "--timeout",
        str(max(20.0, float(args.timeout))),
        "--sample-count",
        str(sample_count),
        "--sample-sleep",
        str(sample_sleep),
        "run",
    ]
    if args.serial:
        command[4:4] = ["--serial", args.serial]
    return command


def push_flash_readback_steps(
    args: argparse.Namespace,
    *,
    role: str,
    image_path: str,
    image_size: int,
    remote_path: str,
) -> list[tuple[str, list[str], int]]:
    remote = remote_quote(remote_path)
    boot_block = remote_quote(args.boot_block)
    count = image_size // BOOT_READBACK_BLOCK_SIZE
    return [
        (f"push-{role}-boot", [*adb_base(args), "push", image_path, remote_path], args.timeout * 4),
        (
            f"remote-{role}-sha",
            [*adb_base(args), "shell", f"sha256sum {remote} 2>/dev/null || toybox sha256sum {remote}"],
            args.timeout,
        ),
        (
            f"flash-{role}-boot",
            [*adb_base(args), "shell", f"dd if={remote} of={boot_block} bs=4M conv=fsync && sync"],
            args.timeout * 4,
        ),
        (
            f"readback-{role}-boot",
            [
                *adb_base(args),
                "shell",
                f"dd if={boot_block} bs={BOOT_READBACK_BLOCK_SIZE} count={count} 2>/dev/null | sha256sum 2>/dev/null || "
                f"dd if={boot_block} bs={BOOT_READBACK_BLOCK_SIZE} count={count} 2>/dev/null | toybox sha256sum",
            ],
            args.timeout * 2,
        ),
    ]


def build_step_plan(args: argparse.Namespace, store: EvidenceStore, android_image: Any, native_image: Any) -> list[tuple[str, list[str] | str, int]]:
    plan: list[tuple[str, list[str] | str, int]] = [
        ("native-bootstatus", ["python3", "scripts/revalidation/a90ctl.py", "bootstatus"], args.timeout),
        ("native-netservice-status", ["python3", "scripts/revalidation/a90ctl.py", "netservice", "status"], args.timeout),
        ("hide-menu", f"bridge:{args.bridge_host}:{args.bridge_port} hide", args.timeout),
        ("native-recovery", f"bridge:{args.bridge_host}:{args.bridge_port} recovery", args.recovery_timeout),
        ("wait-recovery", [*adb_base(args), "devices"], args.recovery_timeout),
    ]
    plan.extend(
        push_flash_readback_steps(
            args,
            role="android",
            image_path=android_image.path,
            image_size=android_image.size,
            remote_path=args.remote_android_image,
        )
    )
    plan.extend(
        [
            ("reboot-android", [*adb_base(args), "shell", "twrp reboot"], args.timeout),
            ("wait-android", [*adb_base(args), "devices"], args.android_timeout),
            (
                "v1022-early-android-pm-esoc-timing",
                v1022_command(args, v1022_early_out_dir(store), args.early_sample_count, args.early_sample_sleep),
                args.v1022_timeout,
            ),
            ("wait-boot-complete", prop_poll_command(args), args.boot_complete_timeout),
            (
                "v1022-late-android-pm-esoc-timing",
                v1022_command(args, v1022_late_out_dir(store), args.late_sample_count, args.late_sample_sleep),
                args.v1022_timeout,
            ),
            ("wait-android-before-rollback", [*adb_base(args), "devices"], args.timeout),
            ("reboot-recovery-for-rollback", [*adb_base(args), "reboot", "recovery"], args.timeout),
            ("wait-rollback-recovery", [*adb_base(args), "devices"], args.recovery_timeout),
        ]
    )
    plan.extend(
        push_flash_readback_steps(
            args,
            role="native",
            image_path=native_image.path,
            image_size=native_image.size,
            remote_path=args.remote_native_image,
        )
    )
    plan.extend(
        [
            ("reboot-native", [*adb_base(args), "shell", "twrp reboot"], args.timeout),
            ("wait-native-bootstatus", f"bridge:{args.bridge_host}:{args.bridge_port} bootstatus", args.recovery_timeout + args.android_timeout),
        ]
    )
    return plan


def load_manifest(path: Path) -> dict[str, Any]:
    manifest = path / "manifest.json"
    if not manifest.exists():
        return {"decision": "missing", "pass": False, "_path": str(manifest)}
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["_path"] = str(manifest)
    return payload


def sha_match_or_missing(step: StepResult, expected_sha: str, store: EvidenceStore) -> bool:
    if not step.ok:
        return False
    if not step.file:
        return False
    return expected_sha in step_text(store, step)


def execute_recovery_restore(
    args: argparse.Namespace,
    store: EvidenceStore,
    native_image: Any,
    execute: bool,
    prefix: str,
) -> list[StepResult]:
    steps: list[StepResult] = []
    restore_plan = push_flash_readback_steps(
        args,
        role=f"{prefix}-native",
        image_path=native_image.path,
        image_size=native_image.size,
        remote_path=args.remote_native_image,
    )
    for name, command, timeout in restore_plan:
        step = execute_step(store, name, command, timeout, execute)
        steps.append(step)
        if execute and not step.ok:
            break
        if execute and name.endswith("sha") and native_image.sha256 not in step_text(store, step):
            step.ok = False
            step.error = "native remote sha mismatch"
            break
        if execute and name.endswith("readback-boot") and native_image.sha256 not in step_text(store, step):
            step.ok = False
            step.error = "native readback sha mismatch"
            break
    return steps


def build_comparison(store: EvidenceStore, boot_state: dict[str, Any], rollback_ok: bool) -> dict[str, Any]:
    early = load_manifest(v1022_early_out_dir(store))
    late = load_manifest(v1022_late_out_dir(store))
    early_decision = str(early.get("decision") or "")
    late_decision = str(late.get("decision") or "")
    early_pass = bool(early.get("pass"))
    late_pass = bool(late.get("pass"))
    useful = early_pass or late_pass
    fd_captured = (
        early_decision == "v1022-android-pm-esoc-fd-timing-captured"
        or late_decision == "v1022-android-pm-esoc-fd-timing-captured"
    )
    if not rollback_ok:
        decision = "v1023-rollback-verification-missing"
        pass_ok = False
        reason = "Android timing handoff did not prove native rollback"
    elif fd_captured:
        decision = "v1023-android-pm-esoc-fd-timing-captured-rollback-complete"
        pass_ok = True
        reason = "V1022 captured Android PM/eSoC fd timing and native rollback completed"
    elif useful:
        decision = "v1023-android-pm-esoc-timing-captured-rollback-complete"
        pass_ok = True
        reason = "V1022 captured Android PM/eSoC timing evidence and native rollback completed"
    else:
        decision = "v1023-android-pm-esoc-timing-incomplete-rollback-complete"
        pass_ok = False
        reason = "V1022 did not capture useful Android PM/eSoC timing evidence, but native rollback completed"
    return {
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "boot_complete": bool(boot_state.get("boot_completed")),
        "boot_props": boot_state.get("props") or {},
        "rollback_ok": rollback_ok,
        "early": {
            "path": early.get("_path"),
            "decision": early.get("decision"),
            "pass": early.get("pass"),
            "reason": early.get("reason"),
            "next_step": early.get("next_step"),
        },
        "late": {
            "path": late.get("_path"),
            "decision": late.get("decision"),
            "pass": late.get("pass"),
            "reason": late.get("reason"),
            "next_step": late.get("next_step"),
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
        "v1022_early_out_dir": str(v1022_early_out_dir(store)),
        "v1022_late_out_dir": str(v1022_late_out_dir(store)),
    }
    if not native_image.present or not native_image.aligned_4k or not native_image.android_magic or not native_image.native_marker:
        return [], context, "v1023-handoff-missing-native-rollback", False
    if android_image is None:
        return [], context, "v1023-handoff-missing-android-boot", False
    if android_image.sha256 == native_image.sha256:
        return [], context, "v1023-handoff-image-collision", False
    if args.command == "run" and not approval_ok:
        return [], context, "v1023-handoff-approval-required", False

    plan = build_step_plan(args, store, android_image, native_image)
    offenders = contains_forbidden_active_wifi(plan)
    if offenders:
        context["forbidden_active_wifi_steps"] = offenders
        return [], context, "v1023-handoff-active-wifi-command-blocked", False

    steps: list[StepResult] = []
    if args.command == "plan":
        for name, command, _timeout in plan:
            steps.append(write_step(store, name, command, "[plan] not executed\n", "", 0, 0.0, skipped=True, ok_override=True))
        return steps, context, "v1023-handoff-plan-ready", True

    boot_state: dict[str, Any] = {"props": {}, "samples": [], "boot_completed": False}
    rollback_ok = False
    android_flash_started = False
    critical_android_write = False

    for name, command, timeout in plan:
        if name == "v1022-late-android-pm-esoc-timing" and execute and not boot_state.get("boot_completed"):
            step = write_step(store, name, command, "[skipped] boot-complete gate did not pass\n", "", 0, 0.0, skipped=True, ok_override=True)
        elif isinstance(command, str) and command.startswith("bridge:"):
            step = execute_bridge_step(store, args, name, command.split(" ", 1)[1], timeout, execute)
            if name == "wait-native-bootstatus" and execute:
                text = step_text(store, step) if step.file else ""
                step.ok = step.ok and "BOOT OK" in text
                if not step.ok:
                    step.error = "native bootstatus did not prove BOOT OK"
        elif name in {"wait-recovery", "wait-rollback-recovery"}:
            step = wait_for_adb_state(args, {"recovery"}, timeout, execute, store, name)
        elif name in {"wait-android", "wait-android-before-rollback"}:
            step = wait_for_adb_state(args, {"device"}, timeout, execute, store, name)
        elif name == "wait-boot-complete":
            step, boot_state = wait_for_boot_complete(args, store, execute)
            context["boot_state"] = boot_state
        else:
            step = execute_step(store, name, command, timeout, execute)
        steps.append(step)

        if name == "flash-android-boot":
            android_flash_started = True
            critical_android_write = True
            context["android_flash_started"] = android_flash_started
        if execute and name == "remote-android-sha" and not sha_match_or_missing(step, android_image.sha256, store):
            context["android_remote_sha_mismatch"] = True
            return steps, context, "v1023-handoff-remote-android-sha-mismatch", False
        if execute and name == "readback-android-boot" and not sha_match_or_missing(step, android_image.sha256, store):
            context["emergency_rollback_attempted"] = True
            context["emergency_rollback_reason"] = "Android boot readback failed or SHA did not match"
            steps.extend(execute_recovery_restore(args, store, native_image, execute=True, prefix="emergency"))
            return steps, context, "v1023-handoff-readback-failed-rollback-attempted", False
        if execute and name == "remote-native-sha" and not sha_match_or_missing(step, native_image.sha256, store):
            context["native_remote_sha_mismatch"] = True
            return steps, context, "v1023-handoff-remote-native-sha-mismatch", False
        if execute and name == "readback-native-boot" and not sha_match_or_missing(step, native_image.sha256, store):
            context["native_readback_sha_mismatch"] = True
            return steps, context, "v1023-handoff-native-readback-mismatch", False
        if name == "wait-native-bootstatus":
            rollback_ok = step.ok

        soft_fail = {
            "v1022-early-android-pm-esoc-timing",
            "v1022-late-android-pm-esoc-timing",
            "wait-boot-complete",
        }
        if execute and not step.ok and name not in soft_fail:
            if critical_android_write and name not in {
                "push-native-boot",
                "remote-native-sha",
                "flash-native-boot",
                "readback-native-boot",
                "reboot-native",
                "wait-native-bootstatus",
            }:
                context["emergency_rollback_attempted"] = True
                context["emergency_rollback_reason"] = f"failed after Android boot write at step {name}"
                steps.extend(execute_recovery_restore(args, store, native_image, execute=True, prefix="emergency"))
            return steps, context, f"v1023-handoff-failed-{name}", False

    comparison = build_comparison(store, boot_state, rollback_ok) if execute else {}
    context["comparison"] = comparison
    context["android_flash_started"] = android_flash_started
    if execute:
        return steps, context, comparison["decision"], bool(comparison["pass"])
    return steps, context, "v1023-handoff-dryrun-ready", True


def reason_for(decision: str, context: dict[str, Any]) -> str:
    comparison = context.get("comparison") or {}
    if comparison.get("decision") == decision:
        return str(comparison.get("reason") or decision)
    return {
        "v1023-handoff-plan-ready": "execution plan generated without device mutation",
        "v1023-handoff-dryrun-ready": "dry-run recorded all steps without device mutation",
        "v1023-handoff-approval-required": "live run refused because approval flags are missing",
        "v1023-handoff-missing-native-rollback": "native rollback image is missing or lacks expected version marker",
        "v1023-handoff-missing-android-boot": "no Android boot candidate passed local safety checks",
        "v1023-handoff-image-collision": "Android and native rollback images unexpectedly have the same hash",
        "v1023-handoff-active-wifi-command-blocked": "handoff plan contains a forbidden active Wi-Fi command pattern",
        "v1023-handoff-remote-android-sha-mismatch": "pushed Android boot image SHA did not match local image",
        "v1023-handoff-readback-failed-rollback-attempted": "Android boot readback failed; native rollback was attempted",
        "v1023-handoff-remote-native-sha-mismatch": "pushed native boot image SHA did not match local rollback image",
        "v1023-handoff-native-readback-mismatch": "native boot readback SHA did not match rollback image",
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
    comparison = manifest["context"].get("comparison") or {}
    collector_rows = [
        ["early", (comparison.get("early") or {}).get("decision", "-"), (comparison.get("early") or {}).get("pass", "-"), (comparison.get("early") or {}).get("path", "-")],
        ["late", (comparison.get("late") or {}).get("decision", "-"), (comparison.get("late") or {}).get("pass", "-"), (comparison.get("late") or {}).get("path", "-")],
    ]
    return "\n".join(
        [
            "# V1023 Android PM/eSoC Timing Handoff",
            "",
            f"- generated: `{manifest['generated_at']}`",
            f"- command: `{manifest['command']}`",
            f"- decision: `{manifest['decision']}`",
            f"- pass: `{manifest['pass']}`",
            f"- reason: {manifest['reason']}",
            f"- approval_ok: `{manifest['context']['approval_ok']}`",
            f"- missing_approval_flags: `{', '.join(manifest['context']['missing_approval_flags']) or '-'}`",
            f"- rollback_ok: `{comparison.get('rollback_ok', '-')}`",
            f"- boot_complete: `{comparison.get('boot_complete', '-')}`",
            "",
            "## V1022 Collectors",
            "",
            markdown_table(["window", "decision", "pass", "manifest"], collector_rows),
            "",
            "## Steps",
            "",
            markdown_table(["step", "status", "rc", "duration", "file"], step_rows if step_rows else [["none", "-", "-", "-", "-"]]),
            "",
            "## Guardrails",
            "",
            "- Live mode temporarily flashes Android boot, runs V1022 read-only collection, then restores native init.",
            "- No native `/dev/subsys_esoc0` retry, `/dev/esoc-*` ioctl, eSoC notify, image response, or BOOT_DONE.",
            "- No Wi-Fi command, scan/connect/link-up, credential use, DHCP/route, or external ping.",
            "- No GPIO/sysfs/debugfs write.",
            "",
        ]
    )


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
            "v1023-handoff-approval-required",
            "v1023-handoff-missing-native-rollback",
            "v1023-handoff-missing-android-boot",
            "v1023-handoff-image-collision",
            "v1023-handoff-active-wifi-command-blocked",
        },
        "android_boot_write_executed": args.command == "run" and bool(context.get("android_flash_started")),
        "native_rollback_required": args.command == "run" and bool(context.get("android_flash_started")),
        "native_rollback_verified": bool((context.get("comparison") or {}).get("rollback_ok")),
        "wifi_command_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "gpio_write_executed": False,
        "esoc_ioctl_executed": False,
        "native_subsys_trigger_executed": False,
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"device_mutations: {manifest['device_mutations']}")
    print(f"native_rollback_verified: {manifest['native_rollback_verified']}")
    print(f"wifi_command_executed: {manifest['wifi_command_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    print(f"out_dir: {store.run_dir}")
    return 0 if pass_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

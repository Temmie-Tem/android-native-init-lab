#!/usr/bin/env python3
"""V435 Android Wi-Fi auto-connect disable handoff.

This wrapper temporarily boots Android, waits for `sys.boot_completed=1`, runs
the bounded V435 Wi-Fi disable proof, then restores the native init boot image.
The only Wi-Fi mutation allowed by the nested collector is
`cmd wifi set-wifi-enabled disabled`; scan/connect, credentials, server
exposure, external probes, routing mutation, rfkill/sysfs writes, and daemon
starts remain blocked.
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


DEFAULT_OUT_DIR = Path("tmp/wifi/v435-android-wifi-autoconnect-disable-handoff")
FORBIDDEN_PLAN_PATTERNS = (
    re.compile(r"\bcmd\s+wifi\s+(?:connect-network|add-network|forget-network|start-scan|force-country-code|set-scan-always-available)\b", re.IGNORECASE),
    re.compile(r"\bsvc\s+wifi\s+enable\b", re.IGNORECASE),
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
    parser.add_argument("--disable-settle-sleep", type=float, default=20.0)
    parser.add_argument("--allow-android-boot-flash", action="store_true")
    parser.add_argument("--assume-yes", action="store_true")
    parser.add_argument("--i-understand-native-rollback", action="store_true")
    parser.add_argument("--allow-wifi-disable", action="store_true")
    parser.add_argument("--i-understand-android-wifi-setting-mutation", action="store_true")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("plan")
    subparsers.add_parser("dry-run")
    subparsers.add_parser("run")
    return parser.parse_args()


def v435_out_dir(store: EvidenceStore) -> Path:
    return store.run_dir / "v435-android-wifi-autoconnect-disable-run"


def disable_approval_ok(args: argparse.Namespace) -> tuple[bool, list[str]]:
    missing: list[str] = []
    if not args.allow_wifi_disable:
        missing.append("--allow-wifi-disable")
    if not args.i_understand_android_wifi_setting_mutation:
        missing.append("--i-understand-android-wifi-setting-mutation")
    return not missing, missing


def v435_step_plan(args: argparse.Namespace, store: EvidenceStore, android_image: Any, native_image: Any) -> list[tuple[str, list[str] | str, int]]:
    base = build_v424_step_plan(args, store, android_image, native_image)
    plan: list[tuple[str, list[str] | str, int]] = []
    collector_timeout = max(args.timeout, int(args.disable_settle_sleep + 240))
    for name, command, timeout in base:
        if name == "v423-android-hwservice-inventory":
            plan.append(("wait-boot-complete", prop_poll_command(args), args.boot_complete_timeout))
            plan.append(("settle-after-boot-complete", f"sleep {args.settle_sleep}", args.settle_sleep + args.timeout))
            v435_command = [
                "python3",
                "scripts/revalidation/wifi_android_autoconnect_disable_v435.py",
                "--out-dir",
                str(v435_out_dir(store)),
                "--adb",
                args.adb,
                "--disable-settle-sleep",
                str(max(0.0, args.disable_settle_sleep)),
            ]
            if args.serial:
                v435_command.extend(["--serial", args.serial])
            if args.allow_wifi_disable:
                v435_command.append("--allow-wifi-disable")
            if args.i_understand_android_wifi_setting_mutation:
                v435_command.append("--i-understand-android-wifi-setting-mutation")
            v435_command.append("run")
            plan.append(("v435-android-wifi-autoconnect-disable", v435_command, collector_timeout))
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


def load_v435_result(store: EvidenceStore) -> dict[str, Any]:
    manifest = v435_out_dir(store) / "manifest.json"
    if not manifest.exists():
        return {"decision": "missing", "pass": False, "_path": str(manifest)}
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["_path"] = str(manifest)
    return payload


def build_comparison(store: EvidenceStore, boot_state: dict[str, Any]) -> dict[str, Any]:
    v435 = load_v435_result(store)
    classification = v435.get("classification") or {}
    boot_complete = bool(boot_state.get("boot_completed"))
    if not boot_complete:
        decision = "v435-handoff-bootcomplete-missing"
        pass_ok = False
        reason = "Android boot-complete gate did not pass"
    elif not v435.get("pass"):
        decision = str(v435.get("decision") or "v435-handoff-disable-failed-rollback-complete")
        pass_ok = False
        reason = str(v435.get("reason") or "V435 disable proof did not pass")
    else:
        decision = str(v435.get("decision") or "v435-handoff-disable-pass")
        pass_ok = True
        reason = str(v435.get("reason") or decision)
    return {
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "boot_complete": boot_complete,
        "boot_props": boot_state.get("props") or {},
        "state": {
            "pre": {
                key: (classification.get("pre") or {}).get(key)
                for key in (
                    "enabled_by_status",
                    "disabled_by_status",
                    "wlan0_has_ip",
                    "default_route_wlan",
                    "route_get_wlan",
                    "connectivity_validated_wifi",
                    "dns_surface_wlan",
                    "global_listener_observed",
                )
            },
            "post": {
                key: (classification.get("post") or {}).get(key)
                for key in (
                    "enabled_by_status",
                    "disabled_by_status",
                    "wlan0_has_ip",
                    "default_route_wlan",
                    "route_get_wlan",
                    "connectivity_validated_wifi",
                    "dns_surface_wlan",
                    "global_listener_observed",
                )
            },
            "route_exposure_gone": classification.get("route_exposure_gone"),
            "connectivity_gone": classification.get("connectivity_gone"),
            "listener_safe": classification.get("listener_safe"),
            "next_gate": classification.get("next_gate"),
        },
        "v435": {
            "path": v435.get("_path"),
            "decision": v435.get("decision"),
            "pass": v435.get("pass"),
            "reason": v435.get("reason"),
        },
    }


def execute_plan(args: argparse.Namespace, store: EvidenceStore, execute: bool) -> tuple[list[StepResult], dict[str, Any], str, bool]:
    native_image, android_images, android_image = image_context(args)
    approval_ok, missing_flags = require_approval(args)
    disable_ok, disable_missing = disable_approval_ok(args)
    context: dict[str, Any] = {
        "native_image": asdict(native_image),
        "android_images": [asdict(image) for image in android_images],
        "android_image": asdict(android_image) if android_image else None,
        "approval_ok": approval_ok,
        "missing_approval_flags": missing_flags,
        "disable_approval_ok": disable_ok,
        "missing_disable_approval_flags": disable_missing,
        "v435_out_dir": str(v435_out_dir(store)),
        "disable_settle_sleep": max(0.0, args.disable_settle_sleep),
    }
    if not native_image.present or not native_image.aligned_4k or not native_image.android_magic or not native_image.native_marker:
        return [], context, "v435-handoff-missing-native-rollback", False
    if android_image is None:
        return [], context, "v435-handoff-missing-android-boot", False
    if android_image.sha256 == native_image.sha256:
        return [], context, "v435-handoff-image-collision", False
    if args.command == "run" and not approval_ok:
        return [], context, "v435-handoff-approval-required", False
    if args.command == "run" and not disable_ok:
        return [], context, "v435-handoff-disable-approval-required", False

    plan = v435_step_plan(args, store, android_image, native_image)
    offenders = contains_forbidden_plan_command(plan)
    if offenders:
        context["forbidden_plan_commands"] = offenders
        return [], context, "v435-handoff-forbidden-command-blocked", False

    steps: list[StepResult] = []
    if args.command == "plan":
        for name, command, _ in plan:
            steps.append(write_step(store, name, command, "[plan] not executed\n", "", 0, 0.0, skipped=True, ok_override=True))
        return steps, context, "v435-handoff-plan-ready", True

    restore_entry = next(item for item in plan if item[0] == "restore-native")
    failure_after_rollback = ""
    skip_collector = False
    boot_state: dict[str, Any] = {"props": {}, "samples": [], "boot_completed": False}
    v435_step_ok = False

    for name, command, timeout in plan:
        if skip_collector and name in {"settle-after-boot-complete", "v435-android-wifi-autoconnect-disable"}:
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
            return steps, context, "v435-handoff-remote-sha-mismatch", False
        if name == "flash-android-boot" and execute and not step.ok:
            context["emergency_rollback_attempted"] = True
            context["emergency_rollback_reason"] = "flash-android-boot failed after boot write was requested"
            restore_name, restore_command, restore_timeout = restore_entry
            rollback_step = execute_step(store, restore_name, restore_command, restore_timeout, execute=True)
            steps.append(rollback_step)
            context["emergency_rollback_ok"] = rollback_step.ok
            return steps, context, "v435-handoff-flash-failed-rollback-attempted", False
        if name == "readback-android-boot" and execute:
            readback_text = step_text(store, step) if step.file else ""
            if not step.ok or android_image.sha256 not in readback_text:
                context["emergency_rollback_attempted"] = True
                context["emergency_rollback_reason"] = "Android boot readback failed or SHA did not match"
                restore_name, restore_command, restore_timeout = restore_entry
                rollback_step = execute_step(store, restore_name, restore_command, restore_timeout, execute=True)
                steps.append(rollback_step)
                context["emergency_rollback_ok"] = rollback_step.ok
                return steps, context, "v435-handoff-readback-failed-rollback-attempted", False
        if name == "wait-boot-complete" and execute and not step.ok:
            failure_after_rollback = "v435-handoff-failed-wait-boot-complete-rollback-complete"
            skip_collector = True
            continue
        if name == "v435-android-wifi-autoconnect-disable":
            v435_step_ok = step.ok
            if execute:
                continue
        if execute and not step.ok:
            return steps, context, f"v435-handoff-failed-{name}", False

    if execute:
        comparison = build_comparison(store, boot_state)
        context["comparison"] = comparison
        if failure_after_rollback:
            return steps, context, failure_after_rollback, False
        if not v435_step_ok:
            return steps, context, "v435-handoff-disable-failed-rollback-complete", False
        return steps, context, comparison["decision"], bool(comparison["pass"])
    return steps, context, "v435-handoff-dryrun-ready", True


def reason_for(decision: str, context: dict[str, Any]) -> str:
    comparison = context.get("comparison") or {}
    if comparison.get("decision") == decision:
        return str(comparison.get("reason") or decision)
    return {
        "v435-handoff-plan-ready": "execution plan generated without device mutation",
        "v435-handoff-dryrun-ready": "dry-run recorded all steps without device mutation",
        "v435-handoff-approval-required": "live run refused because boot/rollback approval flags are missing",
        "v435-handoff-disable-approval-required": "live run refused because Wi-Fi disable approval flags are missing",
        "v435-handoff-missing-native-rollback": "native rollback image is missing or does not contain the expected version marker",
        "v435-handoff-missing-android-boot": "no Android boot candidate passed local safety checks",
        "v435-handoff-image-collision": "Android and native rollback images unexpectedly have the same hash",
        "v435-handoff-forbidden-command-blocked": "handoff plan contains a forbidden Wi-Fi/server/probe command",
        "v435-handoff-failed-wait-boot-complete-rollback-complete": "Android boot-complete gate failed, and native rollback completed",
        "v435-handoff-disable-failed-rollback-complete": "V435 disable proof failed, and native rollback completed",
        "v435-handoff-flash-failed-rollback-attempted": "Android boot flash failed and native rollback was attempted from recovery",
        "v435-handoff-readback-failed-rollback-attempted": "Android boot readback failed and native rollback was attempted from recovery",
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
    flat_rows: list[list[str]] = []
    for phase in ("pre", "post"):
        phase_state = state.get(phase) or {}
        for key, value in phase_state.items():
            flat_rows.append([f"{phase}.{key}", str(value)])
    for key in ("route_exposure_gone", "connectivity_gone", "listener_safe", "next_gate"):
        flat_rows.append([key, str(state.get(key, "-"))])
    return "\n".join(
        [
            "# V435 Boot-complete Android Wi-Fi Auto-connect Disable Handoff",
            "",
            f"- generated: `{manifest['generated_at']}`",
            f"- command: `{manifest['command']}`",
            f"- decision: `{manifest['decision']}`",
            f"- pass: `{manifest['pass']}`",
            f"- reason: {manifest['reason']}",
            f"- approval_ok: `{manifest['context']['approval_ok']}`",
            f"- disable_approval_ok: `{manifest['context']['disable_approval_ok']}`",
            f"- missing_approval_flags: `{', '.join(manifest['context']['missing_approval_flags']) or '-'}`",
            f"- missing_disable_approval_flags: `{', '.join(manifest['context']['missing_disable_approval_flags']) or '-'}`",
            f"- v435_out_dir: `{manifest['context']['v435_out_dir']}`",
            f"- device_commands_executed: `{manifest['device_commands_executed']}`",
            f"- device_mutations: `{manifest['device_mutations']}`",
            f"- wifi_disable_executed: `{manifest['wifi_disable_executed']}`",
            f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
            "",
            "## Comparison",
            "",
            f"- boot_complete: `{comparison.get('boot_complete', '-')}`",
            f"- v435_decision: `{(comparison.get('v435') or {}).get('decision', '-')}`",
            "",
            markdown_table(["state", "value"], flat_rows if flat_rows else [["-", "-"]]),
            "",
            "## Steps",
            "",
            markdown_table(["step", "status", "rc", "duration", "file"], step_rows if step_rows else [["none", "-", "-", "-", "-"]]),
            "",
            "## Guardrails",
            "",
            "- `run` requires boot/rollback approval flags and Wi-Fi disable approval flags.",
            "- The only allowed Wi-Fi mutation is `cmd wifi set-wifi-enabled disabled`.",
            "- No scan/connect, credentials, server exposure, external packet probes, DHCP/routing mutation, rfkill/sysfs write, module load/unload, or property mutation.",
            "",
        ]
    )


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    steps, context, decision, pass_ok = execute_plan(args, store, execute=args.command == "run")
    wifi_disable_executed = any(
        step.name == "v435-android-wifi-autoconnect-disable" and not step.skipped
        for step in steps
    )
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
            "v435-handoff-approval-required",
            "v435-handoff-disable-approval-required",
            "v435-handoff-missing-native-rollback",
            "v435-handoff-missing-android-boot",
            "v435-handoff-image-collision",
            "v435-handoff-forbidden-command-blocked",
        },
        "wifi_disable_executed": wifi_disable_executed,
        "wifi_bringup_executed": False,
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {decision}")
    print(f"pass: {pass_ok}")
    print(f"reason: {manifest['reason']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"device_mutations: {manifest['device_mutations']}")
    print(f"wifi_disable_executed: {manifest['wifi_disable_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"out_dir: {store.run_dir}")
    return 0 if pass_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

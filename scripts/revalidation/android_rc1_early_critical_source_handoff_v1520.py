#!/usr/bin/env python3
"""V1520 bounded Android handoff for early RC1 critical-source sampling.

The runner temporarily boots a known Android boot image, starts the V1520
read-only early sampler immediately after Android ADB appears, then restores
the native v724 boot image. The sampler is read-only and this handoff does not
enable Wi-Fi, scan/connect, use credentials, run DHCP/routes, ping externally,
write PMIC/GPIO/GDSC/eSoC state, or mutate partitions outside the bounded
Android boot/rollback sequence.
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
    adb_base,
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


DEFAULT_OUT_DIR = Path("tmp/wifi/v1520-android-rc1-early-critical-source-handoff")
DEFAULT_NATIVE_IMAGE = Path("stage3/boot_linux_v724.img")
DEFAULT_NATIVE_EXPECT_VERSION = "A90 Linux init 0.9.68 (v724)"
DEFAULT_REPORT_PATH = Path("docs/reports/NATIVE_INIT_V1520_ANDROID_RC1_EARLY_CRITICAL_SOURCE_HANDOFF_2026-06-01.md")
LATEST_POINTER = Path("tmp/wifi/latest-v1520-android-rc1-early-critical-source-handoff.txt")


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
    parser.add_argument("--collector-timeout", type=int, default=120)
    parser.add_argument("--collector-samples", type=int, default=180)
    parser.add_argument("--collector-delay", type=float, default=0.03)
    parser.add_argument("--allow-android-boot-flash", action="store_true")
    parser.add_argument("--assume-yes", action="store_true")
    parser.add_argument("--i-understand-native-rollback", action="store_true")
    parser.add_argument("--write-report", action="store_true")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("plan")
    subparsers.add_parser("dry-run")
    subparsers.add_parser("run")
    return parser.parse_args()


def v1520_out_dir(store: EvidenceStore) -> Path:
    return store.run_dir / "v1520-android-rc1-early-critical-source-run"


def v1520_command(args: argparse.Namespace, store: EvidenceStore) -> list[str]:
    command = [
        "python3",
        "scripts/revalidation/native_wifi_android_rc1_early_critical_source_sample_v1520.py",
        "--out-dir",
        str(v1520_out_dir(store)),
        "--adb",
        args.adb,
        "--timeout",
        str(args.collector_timeout),
        "--samples",
        str(args.collector_samples),
        "--delay",
        str(args.collector_delay),
    ]
    if args.serial:
        command.extend(["--serial", args.serial])
    command.append("run")
    return command


def v1520_step_plan(args: argparse.Namespace, store: EvidenceStore, android_image: Any, native_image: Any) -> list[tuple[str, list[str] | str, int]]:
    base = build_v424_step_plan(args, store, android_image, native_image)
    plan: list[tuple[str, list[str] | str, int]] = []
    for name, command, timeout in base:
        plan.append((name, command, timeout))
        if name == "wait-android":
            plan.append(("v1520-android-early-critical-sampler", v1520_command(args, store), args.collector_timeout + args.timeout))
        if name == "v423-android-hwservice-inventory":
            plan.pop()
    return plan


def load_v1520_result(store: EvidenceStore) -> dict[str, Any]:
    manifest = v1520_out_dir(store) / "manifest.json"
    if not manifest.exists():
        return {"decision": "missing", "pass": False, "_path": str(manifest)}
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["_path"] = str(manifest)
    return payload


def build_comparison(store: EvidenceStore) -> dict[str, Any]:
    v1520 = load_v1520_result(store)
    summary = v1520.get("summary") or {}
    dmesg = summary.get("dmesg") or {}
    matched = summary.get("matched_window") or {}
    return {
        "v1520_path": v1520.get("_path"),
        "v1520_decision": v1520.get("decision"),
        "v1520_pass": v1520.get("pass"),
        "v1520_reason": v1520.get("reason"),
        "sample_count": summary.get("sample_count"),
        "sample_first_uptime": summary.get("sample_first_uptime"),
        "sample_last_uptime": summary.get("sample_last_uptime"),
        "pcie_l0_time": dmesg.get("pcie_l0_time"),
        "pcie_reset_time": dmesg.get("pcie_reset_time"),
        "wlfw_time": dmesg.get("wlfw_time"),
        "bdf_time": dmesg.get("bdf_time"),
        "wlan0_time": dmesg.get("wlan0_time"),
        "has_pre_l0_sample": matched.get("has_pre_l0_sample"),
        "has_post_l0_sample": matched.get("has_post_l0_sample"),
        "sample_before_l0": matched.get("sample_before_l0"),
        "sample_after_l0": matched.get("sample_after_l0"),
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
        "v1520_out_dir": str(v1520_out_dir(store)),
        "collector_samples": args.collector_samples,
        "collector_delay": args.collector_delay,
    }
    if not native_image.present or not native_image.aligned_4k or not native_image.android_magic or not native_image.native_marker:
        return [], context, "v1520-handoff-missing-native-rollback", False
    if android_image is None:
        return [], context, "v1520-handoff-missing-android-boot", False
    if android_image.sha256 == native_image.sha256:
        return [], context, "v1520-handoff-image-collision", False
    if args.command == "run" and not approval_ok:
        return [], context, "v1520-handoff-approval-required", False

    plan = v1520_step_plan(args, store, android_image, native_image)
    offenders = contains_forbidden_active_wifi(plan)
    if offenders:
        context["forbidden_active_wifi_steps"] = offenders
        return [], context, "v1520-handoff-active-wifi-command-blocked", False

    steps: list[StepResult] = []
    if args.command == "plan":
        for name, command, _ in plan:
            steps.append(write_step(store, name, command, "[plan] not executed\n", "", 0, 0.0, skipped=True, ok_override=True))
        return steps, context, "v1520-handoff-plan-ready", True

    restore_entry = next(item for item in plan if item[0] == "restore-native")
    collector_executed = False
    collector_step_ok = False
    rollback_step_seen = False

    for name, command, timeout in plan:
        if isinstance(command, str) and command.startswith("bridge:"):
            step = execute_bridge_step(store, args, name, command.split(" ", 1)[1], timeout, execute)
        elif name == "wait-recovery":
            step = wait_for_adb_state(args, {"recovery"}, timeout, execute, store, name)
        elif name in {"wait-android", "wait-android-before-rollback"}:
            step = wait_for_adb_state(args, {"device"}, timeout, execute, store, name)
        elif name == "wait-rollback-recovery":
            step = wait_for_adb_state(args, {"recovery"}, timeout, execute, store, name)
        else:
            step = execute_step(store, name, command, timeout, execute)
        steps.append(step)

        if name == "remote-android-sha" and execute and step.ok and android_image.sha256 not in step_text(store, step):
            return steps, context, "v1520-handoff-remote-sha-mismatch", False
        if name == "flash-android-boot" and execute and not step.ok:
            context["emergency_rollback_attempted"] = True
            context["emergency_rollback_reason"] = "flash-android-boot failed after boot write was requested"
            restore_name, restore_command, restore_timeout = restore_entry
            rollback_step = execute_step(store, restore_name, restore_command, restore_timeout, execute=True)
            steps.append(rollback_step)
            context["emergency_rollback_ok"] = rollback_step.ok
            return steps, context, "v1520-handoff-flash-failed-rollback-attempted", False
        if name == "readback-android-boot" and execute:
            readback_text = step_text(store, step) if step.file else ""
            if not step.ok or android_image.sha256 not in readback_text:
                context["emergency_rollback_attempted"] = True
                context["emergency_rollback_reason"] = "Android boot readback failed or SHA did not match"
                restore_name, restore_command, restore_timeout = restore_entry
                rollback_step = execute_step(store, restore_name, restore_command, restore_timeout, execute=True)
                steps.append(rollback_step)
                context["emergency_rollback_ok"] = rollback_step.ok
                return steps, context, "v1520-handoff-readback-failed-rollback-attempted", False
        if name == "v1520-android-early-critical-sampler":
            collector_executed = True
            collector_step_ok = step.ok
        if name == "restore-native":
            rollback_step_seen = True
        if execute and not step.ok and name != "v1520-android-early-critical-sampler":
            return steps, context, f"v1520-handoff-failed-{name}", False

    if execute:
        comparison = build_comparison(store)
        context["comparison"] = comparison
        if not rollback_step_seen:
            return steps, context, "v1520-handoff-rollback-not-run", False
        if not collector_executed:
            return steps, context, "v1520-handoff-collector-not-run-rollback-complete", False
        if not collector_step_ok:
            return steps, context, "v1520-handoff-collector-failed-rollback-complete", False
        if comparison.get("v1520_decision") == "v1520-android-good-matched-rc1-critical-source-window-captured":
            return steps, context, "v1520-handoff-matched-rc1-window-rollback-pass", True
        if comparison.get("v1520_decision") == "v1520-android-good-positive-but-adb-sampler-missed-pre-l0":
            return steps, context, "v1520-handoff-adb-sampler-missed-pre-l0-rollback-pass", True
        return steps, context, "v1520-handoff-evidence-captured-rollback-review", True
    return steps, context, "v1520-handoff-dryrun-ready", True


def render_summary(manifest: dict[str, Any]) -> str:
    steps = manifest["steps"]
    context = manifest["context"]
    comparison = context.get("comparison") or {}
    return "\n".join(
        [
            "# V1520 Android RC1 Early Critical Source Handoff",
            "",
            f"- generated: `{manifest['generated_at']}`",
            f"- command: `{manifest['command']}`",
            f"- decision: `{manifest['decision']}`",
            f"- pass: `{manifest['pass']}`",
            f"- reason: {manifest['reason']}",
            f"- evidence: `{manifest['out_dir']}`",
            f"- v1520_out_dir: `{context.get('v1520_out_dir')}`",
            "",
            "## Comparison",
            "",
            markdown_table(["field", "value"], [[key, value] for key, value in comparison.items()] or [["-", "-"]]),
            "",
            "## Steps",
            "",
            markdown_table(
                ["step", "status", "rc", "duration", "file"],
                [
                    [
                        item["name"],
                        "skip" if item["skipped"] else ("ok" if item["ok"] else "fail"),
                        item["rc"],
                        f"{item['duration_sec']:.3f}s",
                        item["file"],
                    ]
                    for item in steps
                ],
            ),
            "",
            "## Safety",
            "",
            "Bounded Android handoff with native rollback. Device mutation is limited to temporary Android boot image flash and rollback to the native image. The collector performs no Wi-Fi HAL start, scan/connect, credential handling, DHCP/routes, external ping, PMIC/GPIO/GDSC write, eSoC notify, global PCI rescan, platform bind/unbind, or partition write beyond the declared boot image handoff/rollback.",
            "",
            "## Next",
            "",
            "- If V1520 captures pre/post L0 samples, compare them against V1518 native no-L0 evidence.",
            "- If early ADB misses pre-L0 while Android reaches L0, move V1521 to an earlier Android boot hook such as a temporary Magisk post-fs-data sampler.",
            "",
        ]
    )


def reason_for(decision: str) -> str:
    reasons = {
        "v1520-handoff-plan-ready": "plan-only handoff; no device command executed",
        "v1520-handoff-dryrun-ready": "dry-run handoff completed without device mutation",
        "v1520-handoff-matched-rc1-window-rollback-pass": "Android matched RC1 pre/post L0 critical-source window captured and native rollback completed",
        "v1520-handoff-adb-sampler-missed-pre-l0-rollback-pass": "Android reached lower chain but early ADB sampler missed pre-L0; native rollback completed",
        "v1520-handoff-evidence-captured-rollback-review": "Android evidence captured and native rollback completed; review child classifier decision",
    }
    return reasons.get(decision) or v424_reason_for(decision)


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    execute = args.command == "run"
    steps, context, decision, pass_ok = execute_plan(args, store, execute=execute)
    manifest = {
        "cycle": "V1520",
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason_for(decision),
        "out_dir": str(store.run_dir),
        "host": collect_host_metadata(),
        "context": context,
        "steps": [asdict(step) for step in steps],
        "device_commands_executed": execute,
        "device_mutations": execute,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "wifi_bringup_executed": False,
        "pmic_gpio_gdsc_write_executed": False,
        "blind_esoc_notify_executed": False,
        "boot_done_spoof_executed": False,
        "global_pci_rescan_executed": False,
        "platform_bind_unbind_executed": False,
        "flash_executed": execute,
        "boot_image_write_executed": execute,
        "partition_write_executed": False,
    }
    summary = render_summary(manifest)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", summary)
    from a90harness.evidence import write_private_text

    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    if args.write_report:
        write_private_text(repo_path(DEFAULT_REPORT_PATH), summary)
    print(f"decision: {manifest['decision']}")
    print(f"pass:     {manifest['pass']}")
    print(f"reason:   {manifest['reason']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest.get("pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())

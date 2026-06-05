#!/usr/bin/env python3
"""V1046 bounded Android handoff for /vendor/etc/init/ RC file capture.

Temporarily boots Android, waits for sys.boot_completed=1, reads RC files
for mdm_helper, ks, per_mgr, per_proxy_helper, and lists all
/vendor/etc/init/ files, then restores native v725-fasttransport boot image.

No Wi-Fi enable/disable, scan/connect, credential/DHCP/routing changes.
No eSoC/subsys open, GPIO write, or sysfs write.
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
from android_hwservice_settled_handoff_v425 import (
    DEFAULT_BOOT_COMPLETE_TIMEOUT,
    DEFAULT_SETTLE_SLEEP,
    prop_poll_command,
    settle_step,
    wait_for_boot_complete,
)


DEFAULT_OUT_DIR = Path("tmp/wifi/v1046-android-vendor-init-rc-handoff")
DEFAULT_NATIVE_IMAGE = Path("stage3/boot_linux_v725_fasttransport.img")
DEFAULT_NATIVE_EXPECT_VERSION = "A90 Linux init 0.9.244 (v725-fasttransport)"

RC_TARGETS = [
    "pm_proxy_helper.rc",
    "hw/init.target.rc",
    "hw/init.r3q.rc",
    "hw/init.samsung.rc",
    "hw/init.qcom.rc",
]

# Additional broad search commands to run after RC_TARGETS
BROAD_SEARCH_CMDS: list[tuple[str, str]] = [
    ("rc-read-init-mdm-sh", "su -c 'cat /vendor/bin/init.mdm.sh 2>&1'"),
    ("rc-grep-ks-bin", "su -c 'grep -rl \"/vendor/bin/ks\" /vendor/etc/init/ /vendor/bin/ 2>&1'"),
    ("rc-grep-mdm-helper-start", "su -c 'grep -r \"start vendor.mdm_helper\\|start mdm_helper\" /vendor/etc/init/ /vendor/bin/ 2>&1'"),
    ("rc-find-ks", "su -c 'find /vendor/bin/ -name \"ks\" -o -name \"ks.sh\" 2>&1'"),
    ("rc-grep-per-proxy-helper", "su -c 'grep -r \"per_proxy_helper\\|pm_proxy_helper\" /vendor/etc/init/ 2>&1'"),
]


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


def rc_adb_command(args: argparse.Namespace, shell_cmd: str) -> list[str]:
    return [*adb_base(args), "shell", shell_cmd]


def build_step_plan(
    args: argparse.Namespace,
    store: EvidenceStore,
    android_image: Any,
    native_image: Any,
) -> list[tuple[str, list[str] | str, int]]:
    base = build_v424_step_plan(args, store, android_image, native_image)
    collector_timeout = max(args.timeout * 6, 180)
    plan: list[tuple[str, list[str] | str, int]] = []
    for name, command, timeout in base:
        if name == "v423-android-hwservice-inventory":
            plan.append(("wait-boot-complete", prop_poll_command(args), args.boot_complete_timeout))
            plan.append(("settle-after-boot-complete", f"sleep {args.settle_sleep}", args.settle_sleep + args.timeout))
            plan.append(("rc-ls-vendor-init", rc_adb_command(args, "su -c 'ls /vendor/etc/init/ 2>&1'"), collector_timeout))
            for rc_file in RC_TARGETS:
                step_name = f"rc-read-{rc_file.replace('/', '-').replace('.', '-')}"
                cmd = rc_adb_command(args, f"su -c 'cat /vendor/etc/init/{rc_file} 2>&1'")
                plan.append((step_name, cmd, collector_timeout))
            for step_name, shell_cmd in BROAD_SEARCH_CMDS:
                plan.append((step_name, rc_adb_command(args, shell_cmd), collector_timeout))
        else:
            plan.append((name, command, timeout))
    return plan


def collect_rc_results(store: EvidenceStore, steps: list[StepResult]) -> dict[str, Any]:
    results: dict[str, Any] = {}
    broad_step_names = {name for name, _ in BROAD_SEARCH_CMDS}
    for step in steps:
        text = step_text(store, step) if step.file else ""
        if step.name == "rc-ls-vendor-init":
            results["vendor_init_ls"] = text
            results["vendor_init_ls_ok"] = step.ok
        elif step.name.startswith("rc-read-"):
            key = step.name[len("rc-read-"):]
            results[key] = text
            results[f"{key}_ok"] = step.ok
        elif step.name in broad_step_names:
            results[step.name] = text
            results[f"{step.name}_ok"] = step.ok
    return results


def execute_plan(
    args: argparse.Namespace,
    store: EvidenceStore,
    execute: bool,
) -> tuple[list[StepResult], dict[str, Any], str, bool]:
    native_image, android_images, android_image = image_context(args)
    approval_ok, missing_flags = require_approval(args)
    context: dict[str, Any] = {
        "native_image": asdict(native_image),
        "android_images": [asdict(image) for image in android_images],
        "android_image": asdict(android_image) if android_image else None,
        "approval_ok": approval_ok,
        "missing_approval_flags": missing_flags,
    }
    if not native_image.present or not native_image.aligned_4k or not native_image.android_magic or not native_image.native_marker:
        return [], context, "v1046-handoff-missing-native-rollback", False
    if android_image is None:
        return [], context, "v1046-handoff-missing-android-boot", False
    if android_image.sha256 == native_image.sha256:
        return [], context, "v1046-handoff-image-collision", False
    if args.command == "run" and not approval_ok:
        return [], context, "v1046-handoff-approval-required", False

    plan = build_step_plan(args, store, android_image, native_image)
    offenders = contains_forbidden_active_wifi(plan)
    if offenders:
        context["forbidden_active_wifi_steps"] = offenders
        return [], context, "v1046-handoff-active-wifi-command-blocked", False

    steps: list[StepResult] = []
    if args.command == "plan":
        for name, command, _ in plan:
            steps.append(write_step(store, name, command, "[plan] not executed\n", "", 0, 0.0, skipped=True, ok_override=True))
        return steps, context, "v1046-handoff-plan-ready", True

    restore_entry = next(item for item in plan if item[0] == "restore-native")
    boot_state: dict[str, Any] = {"props": {}, "samples": [], "boot_completed": False}
    skip_collector = False
    rc_results: dict[str, Any] = {}

    for name, command, timeout in plan:
        rc_step_names = (
            {"settle-after-boot-complete", "rc-ls-vendor-init"}
            | {f"rc-read-{f.replace('/', '-').replace('.', '-')}" for f in RC_TARGETS}
            | {name for name, _ in BROAD_SEARCH_CMDS}
        )
        if skip_collector and name in rc_step_names:
            steps.append(write_step(store, name, command, "[skipped] boot-complete gate did not pass\n", "", 0, 0.0, skipped=True, ok_override=True))
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
            return steps, context, "v1046-handoff-remote-sha-mismatch", False
        if name == "flash-android-boot" and execute and not step.ok:
            context["emergency_rollback_attempted"] = True
            context["emergency_rollback_reason"] = "flash-android-boot failed"
            restore_name, restore_command, restore_timeout = restore_entry
            rollback_step = execute_step(store, restore_name, restore_command, restore_timeout, execute=True)
            steps.append(rollback_step)
            context["emergency_rollback_ok"] = rollback_step.ok
            return steps, context, "v1046-handoff-flash-failed-rollback-attempted", False
        if name == "readback-android-boot" and execute:
            readback_text = step_text(store, step) if step.file else ""
            if not step.ok or android_image.sha256 not in readback_text:
                context["emergency_rollback_attempted"] = True
                context["emergency_rollback_reason"] = "Android boot readback failed or SHA mismatch"
                restore_name, restore_command, restore_timeout = restore_entry
                rollback_step = execute_step(store, restore_name, restore_command, restore_timeout, execute=True)
                steps.append(rollback_step)
                context["emergency_rollback_ok"] = rollback_step.ok
                return steps, context, "v1046-handoff-readback-failed-rollback-attempted", False
        if name == "wait-boot-complete" and execute and not step.ok:
            skip_collector = True
            continue
        non_fatal_rc_steps = (
            {f"rc-read-{f.replace('/', '-').replace('.', '-')}" for f in RC_TARGETS}
            | {name for name, _ in BROAD_SEARCH_CMDS}
            | {"rc-ls-vendor-init"}
        )
        if execute and not step.ok and name not in non_fatal_rc_steps:
            return steps, context, f"v1046-handoff-failed-{name}", False

    if execute:
        rc_results = collect_rc_results(store, steps)
        context["rc_results"] = rc_results
        boot_complete = bool(boot_state.get("boot_completed"))
        if skip_collector or not boot_complete:
            return steps, context, "v1046-handoff-failed-wait-boot-complete-rollback-complete", False
        rc_ok = rc_results.get("mdm_helper.rc_ok", False) or rc_results.get("ks.rc_ok", False)
        if rc_ok:
            return steps, context, "v1046-android-vendor-init-rc-captured", True
        return steps, context, "v1046-android-vendor-init-rc-partial", bool(rc_results.get("vendor_init_ls_ok"))
    return steps, context, "v1046-handoff-dryrun-ready", True


def render_summary(manifest: dict[str, Any]) -> str:
    step_rows = [
        [item["name"], "skip" if item["skipped"] else ("ok" if item["ok"] else "fail"), str(item["rc"]), f"{item['duration_sec']:.3f}s"]
        for item in manifest["steps"]
    ]
    rc_results = manifest["context"].get("rc_results") or {}
    rc_rows = [[k, ("ok" if v else "fail") if isinstance(v, bool) else str(v)[:80]] for k, v in rc_results.items() if k.endswith("_ok")]
    lines = [
        "# V1046 Android /vendor/etc/init/ RC Handoff",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        "",
        "## RC Read Status",
        "",
        markdown_table(["file", "status"], rc_rows if rc_rows else [["-", "-"]]),
        "",
        "## Steps",
        "",
        markdown_table(["step", "status", "rc", "duration"], step_rows if step_rows else [["none", "-", "-", "-"]]),
        "",
        "## Guardrails",
        "",
        "- No Wi-Fi enable/scan/connect/link-up/credential/DHCP/routing changes.",
        "- No eSoC/subsys open, GPIO write, sysfs write, or module load.",
        "- Live mode flashes Android boot, reads RC files read-only, then restores native v725-fasttransport.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    steps, context, decision, pass_ok = execute_plan(args, store, execute=args.command == "run")
    host_meta = collect_host_metadata()
    reason_map = {
        "v1046-handoff-plan-ready": "execution plan generated without device mutation",
        "v1046-handoff-dryrun-ready": "dry-run recorded all steps without device mutation",
        "v1046-handoff-approval-required": "live run refused: approval flags missing",
        "v1046-handoff-missing-native-rollback": "native rollback image missing or invalid",
        "v1046-handoff-missing-android-boot": "no Android boot candidate found",
        "v1046-handoff-image-collision": "Android and native images have same hash",
        "v1046-handoff-active-wifi-command-blocked": "plan contains forbidden Wi-Fi command",
        "v1046-handoff-failed-wait-boot-complete-rollback-complete": "Android boot-complete gate failed; rollback complete",
        "v1046-android-vendor-init-rc-captured": "RC files captured from /vendor/etc/init/; rollback complete",
        "v1046-android-vendor-init-rc-partial": "RC file reads partially succeeded; rollback complete",
    }
    reason = reason_map.get(decision) or v424_reason_for(decision)
    manifest = {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "steps": [
            {
                "name": s.name,
                "command": s.command,
                "ok": s.ok,
                "rc": s.rc,
                "duration_sec": s.duration_sec,
                "file": s.file,
                "skipped": s.skipped,
                "error": s.error,
            }
            for s in steps
        ],
        "context": context,
        "host": host_meta,
    }
    store.write_json("manifest.json", manifest)
    summary_md = render_summary(manifest)
    store.write_text("summary.md", summary_md)
    print(summary_md)
    print(f"decision: {decision}")
    print(f"pass: {pass_ok}")
    return 0 if pass_ok else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())

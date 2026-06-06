#!/usr/bin/env python3
"""V425 boot-complete Android hwservice handoff and comparator.

V425 is a bounded follow-up to V424.  It temporarily boots Android, waits for
`sys.boot_completed=1`, runs the V423 read-only hwservice/lshal inventory, then
rolls back to native init v319.  It does not enable Wi-Fi, scan, connect, link
up interfaces, mutate rfkill/sysfs/properties, start Wi-Fi daemons directly, or
route traffic.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import time
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
    adb_base,
    build_step_plan as build_v424_step_plan,
    contains_forbidden_active_wifi,
    display_command,
    execute_bridge_step,
    execute_step,
    image_context,
    reason_for as v424_reason_for,
    require_approval,
    run_process,
    step_text,
    wait_for_adb_state,
    write_step,
)
from wifi_android_hwservice_inventory_v423 import TARGETED_WAIT_TARGETS


DEFAULT_OUT_DIR = Path("tmp/wifi/v425-android-hwservice-settled-handoff")
DEFAULT_BOOT_COMPLETE_TIMEOUT = 600
DEFAULT_SETTLE_SLEEP = 20
BOOT_COMPLETE_PROPS = (
    "sys.boot_completed",
    "dev.bootcomplete",
    "init.svc.bootanim",
    "init.svc.servicemanager",
    "init.svc.hwservicemanager",
    "init.svc.vendor.wifi_hal_ext",
    "init.svc.vendor.wifi_hal",
    "init.svc.wificond",
    "init.svc.wpa_supplicant",
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


def v423_out_dir(store: EvidenceStore) -> Path:
    return store.run_dir / "v423-android-hwservice-bootcomplete-run"


def latest_manifest(pattern: str) -> dict[str, Any]:
    candidates = sorted(repo_path("tmp/wifi").glob(pattern), key=lambda path: path.stat().st_mtime)
    for candidate in reversed(candidates):
        manifest = candidate / "manifest.json"
        if manifest.exists():
            payload = json.loads(manifest.read_text(encoding="utf-8"))
            payload["_path"] = str(manifest)
            return payload
    return {"_path": "", "decision": "missing", "pass": False}


def prop_poll_command(args: argparse.Namespace) -> list[str]:
    props = " ".join(BOOT_COMPLETE_PROPS)
    return [
        *adb_base(args),
        "shell",
        f"for p in {props}; do echo \"$p=$(getprop $p 2>/dev/null)\"; done",
    ]


def parse_prop_text(text: str) -> dict[str, str]:
    props: dict[str, str] = {}
    for line in text.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key in BOOT_COMPLETE_PROPS:
            props[key] = value.strip()
    return props


def wait_for_boot_complete(args: argparse.Namespace, store: EvidenceStore, execute: bool) -> tuple[StepResult, dict[str, Any]]:
    command = prop_poll_command(args)
    if not execute:
        step = write_step(store, "wait-boot-complete", command, "[dry-run] wait for sys.boot_completed=1\n", "", 0, 0.0, skipped=True, ok_override=True)
        return step, {"props": {}, "samples": [], "boot_completed": False}

    started = time.monotonic()
    deadline = started + args.boot_complete_timeout
    samples: list[dict[str, Any]] = []
    last_text = ""
    last_error = ""
    while time.monotonic() < deadline:
        rc, text, error, _ = run_process(command, min(args.timeout, 30))
        props = parse_prop_text(text)
        sample = {
            "elapsed_sec": round(time.monotonic() - started, 3),
            "rc": rc,
            "props": props,
            "error": error,
        }
        samples.append(sample)
        last_text = text
        last_error = error
        if rc == 0 and props.get("sys.boot_completed") == "1":
            body = json.dumps({"samples": samples, "final_props": props}, indent=2, sort_keys=True) + "\n"
            step = write_step(store, "wait-boot-complete", command, body, "", 0, time.monotonic() - started, ok_override=True)
            return step, {"props": props, "samples": samples, "boot_completed": True}
        time.sleep(3.0)

    body = json.dumps({"samples": samples, "last_text": last_text, "last_error": last_error}, indent=2, sort_keys=True) + "\n"
    step = write_step(
        store,
        "wait-boot-complete",
        command,
        body,
        f"timeout waiting for sys.boot_completed=1 after {args.boot_complete_timeout}s",
        None,
        time.monotonic() - started,
        ok_override=False,
    )
    return step, {"props": samples[-1]["props"] if samples else {}, "samples": samples, "boot_completed": False}


def settle_step(args: argparse.Namespace, store: EvidenceStore, execute: bool) -> StepResult:
    command = f"sleep {args.settle_sleep}; {display_command(prop_poll_command(args))}"
    if not execute:
        return write_step(store, "settle-after-boot-complete", command, "[dry-run] not executed\n", "", 0, 0.0, skipped=True, ok_override=True)
    started = time.monotonic()
    if args.settle_sleep > 0:
        time.sleep(args.settle_sleep)
    rc, text, error, _ = run_process(prop_poll_command(args), min(args.timeout, 30))
    return write_step(store, "settle-after-boot-complete", command, text, error, rc, time.monotonic() - started)


def v425_step_plan(args: argparse.Namespace, store: EvidenceStore, android_image: Any, native_image: Any) -> list[tuple[str, list[str] | str, int]]:
    base = build_v424_step_plan(args, store, android_image, native_image)
    plan: list[tuple[str, list[str] | str, int]] = []
    for name, command, timeout in base:
        if name == "v423-android-hwservice-inventory":
            plan.append(("wait-boot-complete", prop_poll_command(args), args.boot_complete_timeout))
            plan.append(("settle-after-boot-complete", f"sleep {args.settle_sleep}", args.settle_sleep + args.timeout))
            v423_command = [
                "python3",
                "scripts/revalidation/wifi_android_hwservice_inventory_v423.py",
                "--out-dir",
                str(v423_out_dir(store)),
                "--adb",
                args.adb,
            ]
            if args.serial:
                v423_command.extend(["--serial", args.serial])
            v423_command.append("run")
            plan.append((name, v423_command, timeout))
        else:
            plan.append((name, command, timeout))
    return plan


def load_v423_result(store: EvidenceStore) -> dict[str, Any]:
    manifest = v423_out_dir(store) / "manifest.json"
    if not manifest.exists():
        return {"decision": "missing", "pass": False, "_path": str(manifest)}
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["_path"] = str(manifest)
    return payload


def build_comparison(store: EvidenceStore, boot_state: dict[str, Any]) -> dict[str, Any]:
    v423 = load_v423_result(store)
    v422 = latest_manifest("v422-micro-lshal-wait-live-*")
    v407 = latest_manifest("v407-composite-hal-start-only-retry-live-*")
    classification = v423.get("classification") or {}
    matched_targets = classification.get("matched_targets") or []
    full_match = set(matched_targets) >= set(TARGETED_WAIT_TARGETS)
    boot_complete = bool(boot_state.get("boot_completed"))
    v422_decision = str(v422.get("decision") or "")
    v407_decision = str(v407.get("decision") or "")

    if not boot_complete:
        decision = "v425-bootcomplete-missing"
        pass_ok = False
        reason = "Android boot-complete gate did not pass"
    elif full_match:
        decision = "v425-bootcomplete-targets-present-native-gap"
        pass_ok = True
        reason = "boot-complete Android lshal contains all Samsung ISehWifi targets; native private micro query still timed out earlier"
    elif matched_targets:
        decision = "v425-bootcomplete-partial-targets-present"
        pass_ok = True
        reason = "boot-complete Android lshal contains only a subset of Samsung ISehWifi targets"
    elif v423.get("pass"):
        decision = "v425-bootcomplete-no-targets"
        pass_ok = True
        reason = "boot-complete Android inventory ran but target fqinstances were not found"
    else:
        decision = "v425-bootcomplete-inventory-failed"
        pass_ok = False
        reason = "V423 boot-complete Android inventory did not pass"

    return {
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "boot_complete": boot_complete,
        "boot_props": boot_state.get("props") or {},
        "targeted_wait_targets": list(TARGETED_WAIT_TARGETS),
        "matched_targets": matched_targets,
        "v423": {
            "path": v423.get("_path"),
            "decision": v423.get("decision"),
            "pass": v423.get("pass"),
            "reason": v423.get("reason"),
        },
        "v422": {
            "path": v422.get("_path"),
            "decision": v422_decision,
            "pass": v422.get("pass"),
            "micro_query_result": (v422.get("live_result") or {}).get("micro_query_result"),
            "micro_query_reason": (v422.get("live_result") or {}).get("micro_query_reason"),
        },
        "v407": {
            "path": v407.get("_path"),
            "decision": v407_decision,
            "pass": v407.get("pass"),
            "helper_result": (v407.get("live_result") or {}).get("helper_result"),
            "helper_reason": (v407.get("live_result") or {}).get("helper_reason"),
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
        "v423_out_dir": str(v423_out_dir(store)),
    }
    if not native_image.present or not native_image.aligned_4k or not native_image.android_magic or not native_image.native_marker:
        return [], context, "v425-handoff-missing-native-rollback", False
    if android_image is None:
        return [], context, "v425-handoff-missing-android-boot", False
    if android_image.sha256 == native_image.sha256:
        return [], context, "v425-handoff-image-collision", False
    if args.command == "run" and not approval_ok:
        return [], context, "v425-handoff-approval-required", False

    plan = v425_step_plan(args, store, android_image, native_image)
    offenders = contains_forbidden_active_wifi(plan)
    if offenders:
        context["forbidden_active_wifi_steps"] = offenders
        return [], context, "v425-handoff-active-wifi-command-blocked", False

    steps: list[StepResult] = []
    if args.command == "plan":
        for name, command, _ in plan:
            steps.append(write_step(store, name, command, "[plan] not executed\n", "", 0, 0.0, skipped=True, ok_override=True))
        return steps, context, "v425-handoff-plan-ready", True

    restore_entry = next(item for item in plan if item[0] == "restore-native")
    failure_after_rollback = ""
    skip_settled_inventory = False
    boot_state: dict[str, Any] = {"props": {}, "samples": [], "boot_completed": False}
    v423_step_ok = False

    for name, command, timeout in plan:
        if skip_settled_inventory and name in {"settle-after-boot-complete", "v423-android-hwservice-inventory"}:
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
            return steps, context, "v425-handoff-remote-sha-mismatch", False
        if name == "flash-android-boot" and execute and not step.ok:
            context["emergency_rollback_attempted"] = True
            context["emergency_rollback_reason"] = "flash-android-boot failed after boot write was requested"
            restore_name, restore_command, restore_timeout = restore_entry
            rollback_step = execute_step(store, restore_name, restore_command, restore_timeout, execute=True)
            steps.append(rollback_step)
            context["emergency_rollback_ok"] = rollback_step.ok
            return steps, context, "v425-handoff-flash-failed-rollback-attempted", False
        if name == "readback-android-boot" and execute:
            readback_text = step_text(store, step) if step.file else ""
            if not step.ok or android_image.sha256 not in readback_text:
                context["emergency_rollback_attempted"] = True
                context["emergency_rollback_reason"] = "Android boot readback failed or SHA did not match"
                restore_name, restore_command, restore_timeout = restore_entry
                rollback_step = execute_step(store, restore_name, restore_command, restore_timeout, execute=True)
                steps.append(rollback_step)
                context["emergency_rollback_ok"] = rollback_step.ok
                return steps, context, "v425-handoff-readback-failed-rollback-attempted", False
        if name == "wait-boot-complete" and execute and not step.ok:
            failure_after_rollback = "v425-handoff-failed-wait-boot-complete-rollback-complete"
            skip_settled_inventory = True
            continue
        if name == "v423-android-hwservice-inventory":
            v423_step_ok = step.ok
            if execute:
                continue
        if execute and not step.ok:
            return steps, context, f"v425-handoff-failed-{name}", False

    if execute:
        comparison = build_comparison(store, boot_state)
        context["comparison"] = comparison
        if failure_after_rollback:
            return steps, context, failure_after_rollback, False
        if not v423_step_ok:
            return steps, context, "v425-handoff-v423-capture-failed-rollback-complete", False
        return steps, context, comparison["decision"], bool(comparison["pass"])
    return steps, context, "v425-handoff-dryrun-ready", True


def reason_for(decision: str, context: dict[str, Any]) -> str:
    comparison = context.get("comparison") or {}
    if comparison.get("decision") == decision:
        return str(comparison.get("reason") or decision)
    return {
        "v425-handoff-plan-ready": "execution plan generated without device mutation",
        "v425-handoff-dryrun-ready": "dry-run recorded all steps without device mutation",
        "v425-handoff-approval-required": "live run refused because approval flags are missing",
        "v425-handoff-missing-native-rollback": "native rollback image is missing or does not contain the expected version marker",
        "v425-handoff-missing-android-boot": "no Android boot candidate passed local safety checks",
        "v425-handoff-image-collision": "Android and native rollback images unexpectedly have the same hash",
        "v425-handoff-active-wifi-command-blocked": "handoff plan contains a forbidden active Wi-Fi command pattern",
        "v425-handoff-failed-wait-boot-complete-rollback-complete": "Android boot-complete gate failed, and native rollback completed",
        "v425-handoff-v423-capture-failed-rollback-complete": "V423 boot-complete Android inventory failed, and native rollback completed",
        "v425-handoff-flash-failed-rollback-attempted": "Android boot flash failed and native rollback was attempted from recovery",
        "v425-handoff-readback-failed-rollback-attempted": "Android boot readback failed and native rollback was attempted from recovery",
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
    target_rows = [
        [target, "present" if target in set(comparison.get("matched_targets") or []) else "not-seen"]
        for target in TARGETED_WAIT_TARGETS
    ]
    return "\n".join(
        [
            "# V425 Boot-complete Android hwservice Handoff",
            "",
            f"- generated: `{manifest['generated_at']}`",
            f"- command: `{manifest['command']}`",
            f"- decision: `{manifest['decision']}`",
            f"- pass: `{manifest['pass']}`",
            f"- reason: {manifest['reason']}",
            f"- approval_ok: `{manifest['context']['approval_ok']}`",
            f"- missing_approval_flags: `{', '.join(manifest['context']['missing_approval_flags']) or '-'}`",
            f"- v423_out_dir: `{manifest['context']['v423_out_dir']}`",
            "",
            "## Comparison",
            "",
            f"- boot_complete: `{comparison.get('boot_complete', '-')}`",
            f"- v423_decision: `{(comparison.get('v423') or {}).get('decision', '-')}`",
            f"- v422_decision: `{(comparison.get('v422') or {}).get('decision', '-')}`",
            f"- v407_decision: `{(comparison.get('v407') or {}).get('decision', '-')}`",
            "",
            markdown_table(["target", "state"], target_rows),
            "",
            "## Steps",
            "",
            markdown_table(["step", "status", "rc", "duration", "file"], step_rows if step_rows else [["none", "-", "-", "-", "-"]]),
            "",
            "## Guardrails",
            "",
            "- `run` requires explicit approval flags.",
            "- `plan` and `dry-run` do not reboot, enter recovery, or write boot.",
            "- Live mode waits only on read-only Android properties before V423 collection.",
            "- No Wi-Fi scan/connect/link-up/credential/DHCP/routing.",
            "- No direct Wi-Fi daemon start, rfkill/sysfs write, module load/unload, or property mutation.",
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
            "v425-handoff-approval-required",
            "v425-handoff-missing-native-rollback",
            "v425-handoff-missing-android-boot",
            "v425-handoff-image-collision",
            "v425-handoff-active-wifi-command-blocked",
        },
        "wifi_bringup_executed": False,
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {decision}")
    print(f"pass: {pass_ok}")
    print(f"reason: {manifest['reason']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"device_mutations: {manifest['device_mutations']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"out_dir: {store.run_dir}")
    return 0 if pass_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

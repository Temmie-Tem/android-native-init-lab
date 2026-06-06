#!/usr/bin/env python3
"""V445 bounded Android Wi-Fi explicit scan/connect live runner.

V445 is the first runner that may execute explicit Android Wi-Fi scan/connect,
but only after V444 preflight passes.  The top-level handoff refuses to boot or
flash Android if V444 is not ready.  The collector never writes raw SSID, BSSID,
password, passphrase, or PSK values to evidence.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import shlex
import subprocess
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
    display_command,
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
from wifi_android_control_gate_v432 import redact_text
from wifi_android_explicit_connect_preflight_v444 import (
    latest_v443_policy,
    load_json,
    validate_env_against_policy,
)
from wifi_android_reenable_observation_v438 import (
    adb_shell_command,
    capture_phase,
    local_phase_state,
)
from wifi_android_target_policy_v442 import validate_policy


DEFAULT_OUT_DIR = Path("tmp/wifi/v445-android-wifi-explicit-connect-live")


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
    parser.add_argument("--policy", type=Path, default=None)
    parser.add_argument("--enable-settle-sleep", type=float, default=20.0)
    parser.add_argument("--scan-settle-sleep", type=float, default=12.0)
    parser.add_argument("--connect-settle-sleep", type=float, default=35.0)
    parser.add_argument("--cleanup-settle-sleep", type=float, default=25.0)
    parser.add_argument("--allow-android-boot-flash", action="store_true")
    parser.add_argument("--assume-yes", action="store_true")
    parser.add_argument("--i-understand-native-rollback", action="store_true")
    parser.add_argument("--allow-read-wifi-env", action="store_true")
    parser.add_argument("--i-understand-wifi-secret-env", action="store_true")
    parser.add_argument("--allow-explicit-scan-connect", action="store_true")
    parser.add_argument("--i-understand-explicit-wifi-connect", action="store_true")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("plan")
    subparsers.add_parser("dry-run")
    subparsers.add_parser("run")
    subparsers.add_parser("collect")
    return parser.parse_args()


def explicit_approval_ok(args: argparse.Namespace) -> tuple[bool, list[str]]:
    missing: list[str] = []
    if not args.allow_read_wifi_env:
        missing.append("--allow-read-wifi-env")
    if not args.i_understand_wifi_secret_env:
        missing.append("--i-understand-wifi-secret-env")
    if not args.allow_explicit_scan_connect:
        missing.append("--allow-explicit-scan-connect")
    if not args.i_understand_explicit_wifi_connect:
        missing.append("--i-understand-explicit-wifi-connect")
    return not missing, missing


def load_policy(args: argparse.Namespace) -> tuple[dict[str, Any] | None, str, str]:
    return load_json(args.policy or latest_v443_policy())


def read_env_values(approved: bool) -> tuple[dict[str, Any], dict[str, str]]:
    import os

    state: dict[str, Any] = {}
    values: dict[str, str] = {}
    for name in ("A90_WIFI_SSID", "A90_WIFI_PSK"):
        value = os.environ.get(name, "")
        state[name] = {"present": name in os.environ, "length": len(value)}
        if approved:
            values[name] = value
    return state, values


def target_env(policy: dict[str, Any]) -> tuple[dict[str, Any] | None, dict[str, str], dict[str, Any]]:
    targets = policy.get("targets") or []
    if not targets:
        return None, {}, {}
    target = targets[0]
    source_map = {
        "ssid": "A90_WIFI_SSID",
        "credential": "A90_WIFI_PSK" if target.get("security") in {"wpa2", "wpa3"} else "",
    }
    return target, source_map, {"target_count": len(targets)}


def shell_quote(value: str) -> str:
    return shlex.quote(value)


def command_template(target: dict[str, Any]) -> str:
    security = str(target.get("security"))
    parts = ["cmd", "wifi", "connect-network", "$A90_WIFI_SSID", security]
    if security in {"wpa2", "wpa3"}:
        parts.append("$A90_WIFI_PSK")
    if target.get("autojoin") is False:
        parts.append("-d")
    if target.get("metered") is True:
        parts.append("-m")
    if target.get("private") is True:
        parts.append("-p")
    randomization = target.get("mac_randomization")
    if randomization and randomization != "auto":
        parts.extend(["-r", str(randomization)])
    return " ".join(parts)


def raw_connect_command(target: dict[str, Any], env_values: dict[str, str]) -> str:
    security = str(target.get("security"))
    parts = ["cmd", "wifi", "connect-network", shell_quote(env_values["A90_WIFI_SSID"]), security]
    if security in {"wpa2", "wpa3"}:
        parts.append(shell_quote(env_values["A90_WIFI_PSK"]))
    if target.get("autojoin") is False:
        parts.append("-d")
    if target.get("metered") is True:
        parts.append("-m")
    if target.get("private") is True:
        parts.append("-p")
    randomization = target.get("mac_randomization")
    if randomization and randomization != "auto":
        parts.extend(["-r", str(randomization)])
    return " ".join(parts)


def sanitize_scan_results(text: str) -> str:
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        return ""
    return "\n".join(
        [
            "[scan-results redacted]",
            f"line_count={len(lines)}",
            "raw SSID/BSSID fields intentionally omitted",
        ]
    )


def sanitize_networks(text: str, ssid: str) -> tuple[str, str]:
    matched_id = ""
    rows = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        first = line.split(maxsplit=1)[0]
        if first.isdigit() and ssid and ssid in line:
            matched_id = first
        rows.append("<network-row-redacted>")
    return "\n".join(["[saved-networks redacted]", f"row_count={len(rows)}", f"matched_id={matched_id or '-'}"]), matched_id


def run_process(command: list[str], timeout: int) -> tuple[int | None, str, str, float]:
    started = time.monotonic()
    try:
        result = subprocess.run(
            command,
            cwd=repo_path("."),
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
        )
        return result.returncode, result.stdout, "", time.monotonic() - started
    except subprocess.TimeoutExpired as exc:
        text = exc.stdout if isinstance(exc.stdout, str) else ""
        return None, text, f"timeout after {timeout}s", time.monotonic() - started
    except Exception as exc:  # noqa: BLE001
        return None, "", str(exc), time.monotonic() - started


def run_adb_shell_private(
    args: argparse.Namespace,
    store: EvidenceStore,
    name: str,
    shell_command: str,
    display_shell: str,
    timeout: int,
    sanitizer: Any | None = None,
) -> dict[str, Any]:
    command = adb_shell_command(args, shell_command)
    rc, text, error, duration = run_process(command, timeout)
    visible_text = sanitizer(text) if sanitizer else redact_text(text)
    body = "\n".join([f"$ adb shell {display_shell}", visible_text.rstrip() if visible_text else redact_text(error).rstrip(), f"rc={rc}", ""])
    path = store.write_text(f"commands/{name}.txt", body)
    return {
        "name": name,
        "command": f"adb shell {display_shell}",
        "ok": rc == 0,
        "rc": rc,
        "duration_sec": duration,
        "file": str(path.relative_to(store.run_dir)),
        "error": redact_text(error),
    }


def collect_explicit_connect(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    approved, missing = explicit_approval_ok(args)
    policy, policy_path, policy_text = load_policy(args)
    policy_validation = validate_policy(policy, policy_text)
    env_state, env_values = read_env_values(approved)
    env_validation = validate_env_against_policy(policy, env_values) if policy and policy_validation.get("ready") and approved else {"ready": False, "issues": [], "targets": [], "target_count": 0}
    captures: list[dict[str, Any]] = []
    if not approved:
        decision = "v445-explicit-connect-approval-required"
        pass_ok = False
        reason = "explicit scan/connect approval flags are missing"
        classification: dict[str, Any] = {"next_gate": "rerun with explicit approval flags"}
    elif policy is None:
        decision = "v445-explicit-connect-missing-policy"
        pass_ok = False
        reason = "private policy is missing"
        classification = {"next_gate": "run V443/V444 first"}
    elif not policy_validation.get("ready"):
        decision = "v445-explicit-connect-policy-invalid"
        pass_ok = False
        reason = "private policy failed V442 validation"
        classification = {"next_gate": "fix private policy"}
    elif not env_validation.get("ready"):
        decision = "v445-explicit-connect-env-invalid"
        pass_ok = False
        reason = "Wi-Fi env values do not match private policy"
        classification = {"next_gate": "fix env or policy"}
    else:
        target, _, _ = target_env(policy)
        assert target is not None
        captures.extend(asdict(item) for item in capture_phase(args, store, "pre"))
        captures.append(run_adb_shell_private(args, store, "enable-wifi", "cmd wifi set-wifi-enabled enabled", "cmd wifi set-wifi-enabled enabled", args.timeout))
        time.sleep(max(0.0, args.enable_settle_sleep))
        captures.append(run_adb_shell_private(args, store, "start-scan", "cmd wifi start-scan 2>&1 || true", "cmd wifi start-scan", args.timeout))
        time.sleep(max(0.0, args.scan_settle_sleep))
        captures.append(run_adb_shell_private(args, store, "scan-results-redacted", "cmd wifi list-scan-results 2>&1 || true", "cmd wifi list-scan-results", args.timeout, sanitize_scan_results))
        captures.append(
            run_adb_shell_private(
                args,
                store,
                "connect-network",
                raw_connect_command(target, env_values),
                command_template(target),
                args.timeout,
            )
        )
        time.sleep(max(0.0, args.connect_settle_sleep))
        captures.extend(asdict(item) for item in capture_phase(args, store, "post"))
        network_list = run_adb_shell_private(args, store, "list-networks-redacted", "cmd wifi list-networks 2>&1 || true", "cmd wifi list-networks", args.timeout, lambda text: sanitize_networks(text, env_values["A90_WIFI_SSID"])[0])
        captures.append(network_list)
        raw_networks_rc, raw_networks, _, _ = run_process(adb_shell_command(args, "cmd wifi list-networks 2>&1 || true"), args.timeout)
        _, matched_id = sanitize_networks(raw_networks, env_values["A90_WIFI_SSID"])
        forget_ok = False
        if matched_id:
            captures.append(run_adb_shell_private(args, store, "forget-network", f"cmd wifi forget-network {matched_id}", "cmd wifi forget-network <resolved-id>", args.timeout))
            forget_ok = bool(captures[-1].get("ok"))
        else:
            captures.append({"name": "forget-network", "command": "cmd wifi forget-network <resolved-id>", "ok": False, "rc": None, "duration_sec": 0.0, "file": "", "error": "target network id was not found"})
        captures.append(run_adb_shell_private(args, store, "disable-wifi", "cmd wifi set-wifi-enabled disabled", "cmd wifi set-wifi-enabled disabled", args.timeout))
        time.sleep(max(0.0, args.cleanup_settle_sleep))
        captures.extend(asdict(item) for item in capture_phase(args, store, "cleanup"))
        cleanup_state = local_phase_state_from_records(store, captures, "cleanup")
        exposure_removed = (
            bool(cleanup_state.get("disabled_by_status"))
            and not cleanup_state.get("wlan0_has_ip")
            and not cleanup_state.get("default_route_wlan")
            and not cleanup_state.get("route_get_wlan")
            and not cleanup_state.get("connectivity_validated_wifi")
            and not cleanup_state.get("dns_surface_wlan")
            and not cleanup_state.get("global_listener_observed")
        )
        connected_observed = any(
            bool(local_phase_state_from_records(store, captures, "post").get(key))
            for key in ("wifi_connected", "wlan0_has_ip", "connectivity_validated_wifi")
        )
        if not connected_observed:
            decision = "v445-explicit-connect-no-connection"
            pass_ok = False
            reason = "explicit connect did not produce connected/IP/validated evidence"
            next_gate = "inspect Android Wi-Fi connect output"
        elif not forget_ok:
            decision = "v445-explicit-connect-cleanup-forget-failed"
            pass_ok = False
            reason = "connection evidence was observed but target network cleanup forget did not pass"
            next_gate = "inspect list-networks/forget output before retry"
        elif not exposure_removed:
            decision = "v445-explicit-connect-cleanup-not-contained"
            pass_ok = False
            reason = "cleanup did not remove active Wi-Fi exposure"
            next_gate = "rerun cleanup before any further Wi-Fi work"
        else:
            decision = "v445-explicit-connect-cleanup-pass"
            pass_ok = True
            reason = "explicit scan/connect produced Wi-Fi connection evidence and cleanup containment passed"
            next_gate = "V446 explicit connect stability or server binding policy; server exposure still blocked"
        classification = {
            "next_gate": next_gate,
            "connected_observed": connected_observed,
            "forget_ok": forget_ok,
            "cleanup_state": cleanup_state,
            "exposure_removed": exposure_removed,
            "raw_network_list_rc": raw_networks_rc,
        }
    return {
        "generated_at": now_iso(),
        "command": "collect",
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "host": collect_host_metadata(),
        "policy_path": policy_path,
        "policy_validation": policy_validation,
        "env_state": env_state,
        "env_validation": env_validation,
        "classification": classification,
        "captures": captures,
        "guardrails": guardrails(),
        "device_commands_executed": bool(captures),
        "device_mutations": bool(captures),
        "wifi_bringup_executed": bool(captures),
    }


def local_phase_state_from_records(store: EvidenceStore, captures: list[dict[str, Any]], phase: str) -> dict[str, Any]:
    from wifi_android_reenable_observation_v438 import local_phase_state as v438_state

    class Record:
        def __init__(self, payload: dict[str, Any]) -> None:
            self.name = payload.get("name", "")
            self.command = payload.get("command", "")
            self.ok = bool(payload.get("ok"))
            self.rc = payload.get("rc")
            self.duration_sec = float(payload.get("duration_sec", 0.0))
            self.file = payload.get("file", "")
            self.text = ""
            self.error = payload.get("error", "")

    return v438_state(store, [Record(item) for item in captures if item.get("file")], phase)


def v445_out_dir(store: EvidenceStore) -> Path:
    return store.run_dir / "v445-explicit-connect-collector"


def v445_step_plan(args: argparse.Namespace, store: EvidenceStore, android_image: Any, native_image: Any) -> list[tuple[str, list[str] | str, int]]:
    base = build_v424_step_plan(args, store, android_image, native_image)
    plan: list[tuple[str, list[str] | str, int]] = []
    preflight = [
        "python3",
        "scripts/revalidation/wifi_android_explicit_connect_preflight_v444.py",
        "--out-dir",
        str(store.run_dir / "v444-preflight"),
    ]
    if args.policy:
        preflight.extend(["--policy", str(args.policy)])
    if args.allow_read_wifi_env:
        preflight.append("--allow-read-wifi-env")
    if args.i_understand_wifi_secret_env:
        preflight.append("--i-understand-wifi-secret-env")
    preflight.append("run")
    plan.append(("v444-explicit-connect-preflight", preflight, args.timeout * 6))
    collector_timeout = max(args.timeout, int(args.enable_settle_sleep + args.scan_settle_sleep + args.connect_settle_sleep + args.cleanup_settle_sleep + 420))
    for name, command, timeout in base:
        if name == "v423-android-hwservice-inventory":
            plan.append(("wait-boot-complete", prop_poll_command(args), args.boot_complete_timeout))
            plan.append(("settle-after-boot-complete", f"sleep {args.settle_sleep}", args.settle_sleep + args.timeout))
            collector = [
                "python3",
                "scripts/revalidation/wifi_android_explicit_connect_live_v445.py",
                "--out-dir",
                str(v445_out_dir(store)),
                "--adb",
                args.adb,
                "--timeout",
                str(args.timeout),
                "--enable-settle-sleep",
                str(max(0.0, args.enable_settle_sleep)),
                "--scan-settle-sleep",
                str(max(0.0, args.scan_settle_sleep)),
                "--connect-settle-sleep",
                str(max(0.0, args.connect_settle_sleep)),
                "--cleanup-settle-sleep",
                str(max(0.0, args.cleanup_settle_sleep)),
            ]
            if args.serial:
                collector.extend(["--serial", args.serial])
            if args.policy:
                collector.extend(["--policy", str(args.policy)])
            if args.allow_read_wifi_env:
                collector.append("--allow-read-wifi-env")
            if args.i_understand_wifi_secret_env:
                collector.append("--i-understand-wifi-secret-env")
            if args.allow_explicit_scan_connect:
                collector.append("--allow-explicit-scan-connect")
            if args.i_understand_explicit_wifi_connect:
                collector.append("--i-understand-explicit-wifi-connect")
            collector.append("collect")
            plan.append(("v445-explicit-connect-collector", collector, collector_timeout))
        else:
            plan.append((name, command, timeout))
    return plan


def load_v445_result(store: EvidenceStore) -> dict[str, Any]:
    path = v445_out_dir(store) / "manifest.json"
    if not path.exists():
        return {"decision": "missing", "pass": False, "_path": str(path)}
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["_path"] = str(path)
    return payload


def execute_plan(args: argparse.Namespace, store: EvidenceStore, execute: bool) -> tuple[list[StepResult], dict[str, Any], str, bool]:
    native_image, android_images, android_image = image_context(args)
    boot_ok, boot_missing = require_approval(args)
    explicit_ok, explicit_missing = explicit_approval_ok(args)
    context: dict[str, Any] = {
        "native_image": asdict(native_image),
        "android_images": [asdict(image) for image in android_images],
        "android_image": asdict(android_image) if android_image else None,
        "approval_ok": boot_ok,
        "missing_approval_flags": boot_missing,
        "explicit_approval_ok": explicit_ok,
        "missing_explicit_approval_flags": explicit_missing,
        "v445_out_dir": str(v445_out_dir(store)),
    }
    if not native_image.present or not native_image.aligned_4k or not native_image.android_magic or not native_image.native_marker:
        return [], context, "v445-handoff-missing-native-rollback", False
    if android_image is None:
        return [], context, "v445-handoff-missing-android-boot", False
    if android_image.sha256 == native_image.sha256:
        return [], context, "v445-handoff-image-collision", False
    if args.command == "run" and not boot_ok:
        return [], context, "v445-handoff-approval-required", False
    if args.command == "run" and not explicit_ok:
        return [], context, "v445-handoff-explicit-approval-required", False

    plan = v445_step_plan(args, store, android_image, native_image)
    steps: list[StepResult] = []
    if args.command == "plan":
        for name, command, _ in plan:
            steps.append(write_step(store, name, command, "[plan] not executed\n", "", 0, 0.0, skipped=True, ok_override=True))
        return steps, context, "v445-handoff-plan-ready", True

    restore_entry = next(item for item in plan if item[0] == "restore-native")
    failure_after_rollback = ""
    skip_collector = False
    boot_state: dict[str, Any] = {"props": {}, "samples": [], "boot_completed": False}
    collector_step_ok = False
    for name, command, timeout in plan:
        if skip_collector and name in {"settle-after-boot-complete", "v445-explicit-connect-collector"}:
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
        if name == "v444-explicit-connect-preflight" and execute and not step.ok:
            return steps, context, "v445-handoff-preflight-blocked", False
        if name == "remote-android-sha" and execute and step.ok and android_image.sha256 not in step_text(store, step):
            return steps, context, "v445-handoff-remote-sha-mismatch", False
        if name == "flash-android-boot" and execute and not step.ok:
            restore_name, restore_command, restore_timeout = restore_entry
            rollback_step = execute_step(store, restore_name, restore_command, restore_timeout, execute=True)
            steps.append(rollback_step)
            context["emergency_rollback_ok"] = rollback_step.ok
            return steps, context, "v445-handoff-flash-failed-rollback-attempted", False
        if name == "readback-android-boot" and execute:
            readback_text = step_text(store, step) if step.file else ""
            if not step.ok or android_image.sha256 not in readback_text:
                restore_name, restore_command, restore_timeout = restore_entry
                rollback_step = execute_step(store, restore_name, restore_command, restore_timeout, execute=True)
                steps.append(rollback_step)
                context["emergency_rollback_ok"] = rollback_step.ok
                return steps, context, "v445-handoff-readback-failed-rollback-attempted", False
        if name == "wait-boot-complete" and execute and not step.ok:
            failure_after_rollback = "v445-handoff-failed-wait-boot-complete-rollback-complete"
            skip_collector = True
            continue
        if name == "v445-explicit-connect-collector":
            collector_step_ok = step.ok
            if execute:
                continue
        if execute and not step.ok:
            return steps, context, f"v445-handoff-failed-{name}", False
    if execute:
        result = load_v445_result(store)
        context["v445"] = result
        if failure_after_rollback:
            return steps, context, failure_after_rollback, False
        if not collector_step_ok:
            return steps, context, "v445-handoff-collector-failed-rollback-complete", False
        return steps, context, str(result.get("decision") or "v445-handoff-collector-pass"), bool(result.get("pass"))
    return steps, context, "v445-handoff-dryrun-ready", True


def guardrails() -> list[str]:
    return [
        "V444 preflight must pass before Android boot/flash starts",
        "raw Wi-Fi identifiers and credentials are not written to evidence",
        "server exposure and external packet probes remain blocked",
        "cleanup must forget the resolved network and disable Wi-Fi",
        "native v319 rollback is required",
    ]


def reason_for(decision: str, context: dict[str, Any]) -> str:
    v445 = context.get("v445") or {}
    if v445.get("decision") == decision:
        return str(v445.get("reason") or decision)
    return {
        "v445-handoff-plan-ready": "execution plan generated without device mutation",
        "v445-handoff-dryrun-ready": "dry-run recorded all steps without device mutation",
        "v445-handoff-preflight-blocked": "V444 preflight failed before Android boot/flash",
        "v445-handoff-approval-required": "boot/rollback approval flags are missing",
        "v445-handoff-explicit-approval-required": "explicit scan/connect approval flags are missing",
        "v445-handoff-missing-native-rollback": "native rollback image is missing or invalid",
        "v445-handoff-missing-android-boot": "Android boot candidate is missing",
        "v445-handoff-image-collision": "Android and native images have the same hash",
        "v445-handoff-failed-wait-boot-complete-rollback-complete": "Android boot-complete failed and rollback completed",
        "v445-handoff-collector-failed-rollback-complete": "collector failed and rollback completed",
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
        for item in manifest.get("steps", [])
    ]
    capture_rows = [
        [
            item.get("name", "-"),
            "ok" if item.get("ok") else "fail",
            str(item.get("rc")),
            f"{float(item.get('duration_sec') or 0.0):.3f}s",
            str(item.get("file") or "-"),
        ]
        for item in manifest.get("captures", [])
    ]
    return "\n".join(
        [
            "# V445 Bounded Explicit Wi-Fi Connect Live Runner",
            "",
            f"- generated: `{manifest['generated_at']}`",
            f"- command: `{manifest['command']}`",
            f"- decision: `{manifest['decision']}`",
            f"- pass: `{manifest['pass']}`",
            f"- reason: {manifest['reason']}",
            f"- device_commands_executed: `{manifest['device_commands_executed']}`",
            f"- device_mutations: `{manifest['device_mutations']}`",
            f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
            "",
            "## Steps",
            "",
            markdown_table(["step", "status", "rc", "duration", "file"], step_rows if step_rows else [["none", "-", "-", "-", "-"]]),
            "",
            "## Captures",
            "",
            markdown_table(["capture", "status", "rc", "duration", "file"], capture_rows if capture_rows else [["none", "-", "-", "-", "-"]]),
            "",
            "## Guardrails",
            "",
            *[f"- {item}" for item in manifest["guardrails"]],
            "",
        ]
    )


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    if args.command == "collect":
        manifest = collect_explicit_connect(args, store)
    else:
        steps, context, decision, pass_ok = execute_plan(args, store, execute=args.command == "run")
        v445 = context.get("v445") or {}
        device_commands_executed = args.command == "run" and any(
            step.name != "v444-explicit-connect-preflight" and not step.skipped for step in steps
        )
        device_mutations = args.command == "run" and any(
            step.name
            in {
                "hide-menu",
                "native-recovery",
                "push-android-boot",
                "flash-android-boot",
                "readback-android-boot",
                "reboot-android",
                "v445-explicit-connect-collector",
                "reboot-recovery-for-rollback",
                "restore-native",
            }
            and not step.skipped
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
            "guardrails": guardrails(),
            "device_commands_executed": device_commands_executed,
            "device_mutations": device_mutations,
            "wifi_bringup_executed": bool(v445.get("wifi_bringup_executed")),
        }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"device_mutations: {manifest['device_mutations']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""V439 Android Wi-Fi post-reenable observation and cleanup.

V439 follows V438, where Android accepted `cmd wifi set-wifi-enabled enabled`
but did not expose route/DNS/connectivity during the bounded observation
window.  This collector samples the enabled post-reenable state for a longer
window without scan/connect, credentials, traffic probes, routing mutation,
server exposure, daemon starts, sysfs/rfkill writes, or module operations.

Optionally, it performs one cleanup mutation at the end:
`cmd wifi set-wifi-enabled disabled`.
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore
from wifi_android_autoconnect_disable_v435 import DISABLE_COMMAND
from wifi_android_reenable_observation_v438 import (
    CAPTURES,
    CaptureRecord,
    adb_shell_command,
    adb_state,
    capture_command,
    capture_phase,
    local_phase_state,
)


DEFAULT_OUT_DIR = Path("tmp/wifi/v439-android-wifi-post-reenable-observation")
FORBIDDEN_PATTERNS = (
    re.compile(
        r"\bcmd\s+wifi\s+(?:set-wifi-enabled\s+enabled|connect-network|add-network|forget-network|start-scan|force-country-code|set-scan-always-available)\b",
        re.IGNORECASE,
    ),
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
    parser.add_argument("--adb", default="adb")
    parser.add_argument("--serial", default="")
    parser.add_argument("--timeout", type=int, default=25)
    parser.add_argument("--sample-duration", type=float, default=180.0)
    parser.add_argument("--sample-interval", type=float, default=30.0)
    parser.add_argument("--cleanup-disable", action="store_true")
    parser.add_argument("--cleanup-settle-sleep", type=float, default=25.0)
    parser.add_argument("--allow-wifi-disable-cleanup", action="store_true")
    parser.add_argument("--i-understand-android-wifi-cleanup-mutation", action="store_true")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("plan")
    subparsers.add_parser("preflight")
    subparsers.add_parser("run")
    return parser.parse_args()


def validate_command_guard() -> None:
    commands = "\n".join(command for _, command, _ in CAPTURES) + "\n" + DISABLE_COMMAND
    for pattern in FORBIDDEN_PATTERNS:
        if pattern.search(commands):
            raise RuntimeError(f"forbidden Wi-Fi/server/probe command pattern found: {pattern.pattern}")


def approval_ok(args: argparse.Namespace) -> tuple[bool, list[str]]:
    missing: list[str] = []
    if args.cleanup_disable and not args.allow_wifi_disable_cleanup:
        missing.append("--allow-wifi-disable-cleanup")
    if args.cleanup_disable and not args.i_understand_android_wifi_cleanup_mutation:
        missing.append("--i-understand-android-wifi-cleanup-mutation")
    return not missing, missing


def guardrails(args: argparse.Namespace) -> list[str]:
    cleanup = "enabled" if args.cleanup_disable else "disabled"
    return [
        "post-reenable sampling is read-only and does not enable Wi-Fi",
        f"cleanup disable is {cleanup}; if enabled, exactly one cleanup mutation is allowed: cmd wifi set-wifi-enabled disabled",
        "no scan/connect, credentials, DHCP/routing mutation, external packet probes, server exposure, or new listeners",
        "no rfkill/sysfs write, module operation, setprop, direct daemon start, reboot, or flash in this collector",
        "route/DNS/connectivity/listener state is observation evidence only",
    ]


def sample_phase(
    args: argparse.Namespace,
    store: EvidenceStore,
    captures: list[CaptureRecord],
    phase: str,
    elapsed_sec: float,
) -> dict[str, Any]:
    phase_captures = capture_phase(args, store, phase)
    captures.extend(phase_captures)
    state = local_phase_state(store, captures, phase)
    state["phase"] = phase
    state["elapsed_sec"] = round(elapsed_sec, 3)
    return state


def exposure_seen(state: dict[str, Any]) -> bool:
    return any(
        bool(state.get(key))
        for key in (
            "wifi_connected",
            "wlan0_has_ip",
            "default_route_wlan",
            "route_get_wlan",
            "connectivity_validated_wifi",
            "dns_surface_wlan",
        )
    )


def contained_disabled(state: dict[str, Any]) -> bool:
    return (
        bool(state.get("disabled_by_status"))
        and not state.get("wlan0_has_ip")
        and not state.get("default_route_wlan")
        and not state.get("route_get_wlan")
        and not state.get("connectivity_validated_wifi")
        and not state.get("dns_surface_wlan")
        and not state.get("global_listener_observed")
    )


def summarize_samples(samples: list[dict[str, Any]]) -> dict[str, Any]:
    enabled_seen = any(bool(sample.get("enabled_by_status")) for sample in samples)
    disabled_seen = any(bool(sample.get("disabled_by_status")) for sample in samples)
    wifi_connected_seen = any(bool(sample.get("wifi_connected")) for sample in samples)
    exposure = any(exposure_seen(sample) for sample in samples)
    listener_safe = not any(bool(sample.get("global_listener_observed")) for sample in samples)
    first_exposure = next((sample["phase"] for sample in samples if exposure_seen(sample)), "")
    return {
        "enabled_seen": enabled_seen,
        "disabled_seen": disabled_seen,
        "wifi_connected_seen": wifi_connected_seen,
        "exposure_seen": exposure,
        "listener_safe": listener_safe,
        "first_exposure_phase": first_exposure,
        "sample_count": len(samples),
    }


def classify(
    state: str,
    samples: list[dict[str, Any]],
    cleanup_requested: bool,
    cleanup_ok: bool | None,
    cleanup_state: dict[str, Any] | None,
) -> dict[str, Any]:
    summary = summarize_samples(samples)
    cleanup_contained = contained_disabled(cleanup_state or {}) if cleanup_requested else None
    if state == "adb-missing":
        decision = "v439-android-wifi-post-reenable-adb-missing"
        pass_ok = False
        reason = "adb executable is unavailable on host"
        next_gate = "restore ADB availability"
    elif state != "device":
        decision = "v439-android-wifi-post-reenable-waiting-for-android"
        pass_ok = False
        reason = f"Android ADB is not online (state={state or 'missing'})"
        next_gate = "boot Android before V439"
    elif cleanup_requested and cleanup_ok is False:
        decision = "v439-android-wifi-cleanup-disable-failed"
        pass_ok = False
        reason = "cleanup Wi-Fi disable command did not return success"
        next_gate = "review cleanup command output before retry"
    elif cleanup_requested and not cleanup_contained:
        decision = "v439-android-wifi-cleanup-not-contained"
        pass_ok = False
        reason = "cleanup disable ran, but final route/DNS/connectivity/listener containment was not proven"
        next_gate = "rerun cleanup with longer settle or inspect Android connectivity state"
    elif summary["exposure_seen"]:
        decision = "v439-android-wifi-post-reenable-exposure-observed-cleanup-pass" if cleanup_requested else "v439-android-wifi-post-reenable-exposure-observed"
        pass_ok = True
        reason = "post-reenable observation saw Wi-Fi route/DNS/connectivity exposure; cleanup containment passed" if cleanup_requested else "post-reenable observation saw Wi-Fi route/DNS/connectivity exposure"
        next_gate = "V440 exposure-aware stability or cleanup policy confirmation"
    elif summary["enabled_seen"]:
        decision = "v439-android-wifi-post-reenable-enabled-contained-cleanup-pass" if cleanup_requested else "v439-android-wifi-post-reenable-enabled-contained"
        pass_ok = True
        reason = "Android Wi-Fi remained enabled during observation, but route/DNS/connectivity exposure was not observed"
        next_gate = "V440 decide explicit scan/connect gate or keep contained cleanup baseline"
    else:
        decision = "v439-android-wifi-post-reenable-not-enabled-cleanup-pass" if cleanup_requested else "v439-android-wifi-post-reenable-not-enabled"
        pass_ok = True
        reason = "Android Wi-Fi did not report enabled during the post-reenable observation window"
        next_gate = "V440 choose controlled enable retry or return to native-side Wi-Fi work"
    return {
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_gate": next_gate,
        "samples": samples,
        "sample_summary": summary,
        "cleanup_requested": cleanup_requested,
        "cleanup_ok": cleanup_ok,
        "cleanup_state": cleanup_state,
        "cleanup_contained": cleanup_contained,
    }


def run_plan(args: argparse.Namespace) -> dict[str, Any]:
    ok, missing = approval_ok(args)
    return {
        "generated_at": now_iso(),
        "command": "plan",
        "decision": "v439-android-wifi-post-reenable-plan-ready",
        "pass": True,
        "reason": "post-reenable Android Wi-Fi observation and optional cleanup plan generated",
        "host": collect_host_metadata(),
        "approval_ok": ok,
        "missing_approval_flags": missing,
        "sample_duration": max(0.0, args.sample_duration),
        "sample_interval": max(1.0, args.sample_interval),
        "cleanup_disable": args.cleanup_disable,
        "cleanup_command": DISABLE_COMMAND if args.cleanup_disable else "",
        "captures": [{"name": name, "command": command, "timeout": timeout} for name, command, timeout in CAPTURES],
        "guardrails": guardrails(args),
        "device_commands_executed": False,
        "device_mutations": False,
        "wifi_disable_executed": False,
        "wifi_bringup_executed": False,
    }


def run_preflight(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    captures, state = adb_state(args, store)
    ok, missing = approval_ok(args)
    if state == "device" and ok:
        decision = "v439-android-wifi-post-reenable-preflight-ready"
        pass_ok = True
        reason = "Android ADB is online and requested cleanup approval flags are present"
    elif state == "device":
        decision = "v439-android-wifi-post-reenable-approval-required"
        pass_ok = False
        reason = "Android ADB is online, but requested cleanup approval flags are missing"
    else:
        decision = "v439-android-wifi-post-reenable-waiting-for-android"
        pass_ok = False
        reason = f"Android ADB is not online (state={state or 'missing'})"
    return {
        "generated_at": now_iso(),
        "command": "preflight",
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "host": collect_host_metadata(),
        "approval_ok": ok,
        "missing_approval_flags": missing,
        "adb_state": state,
        "captures": [asdict(capture) for capture in captures],
        "guardrails": guardrails(args),
        "device_commands_executed": True,
        "device_mutations": False,
        "wifi_disable_executed": False,
        "wifi_bringup_executed": False,
    }


def run_capture_mode(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    ok, missing = approval_ok(args)
    captures, state = adb_state(args, store)
    samples: list[dict[str, Any]] = []
    cleanup_capture: CaptureRecord | None = None
    cleanup_state: dict[str, Any] | None = None
    if not ok:
        decision = "v439-android-wifi-post-reenable-approval-required"
        pass_ok = False
        reason = "cleanup approval flags are missing"
        classification: dict[str, Any] = {"next_gate": "rerun with explicit cleanup approval flags"}
    elif state != "device":
        decision = "v439-android-wifi-post-reenable-waiting-for-android"
        pass_ok = False
        reason = f"Android ADB is not online (state={state or 'missing'})"
        classification = {"next_gate": "boot Android before V439"}
    else:
        sample_duration = max(0.0, args.sample_duration)
        sample_interval = max(1.0, args.sample_interval)
        started = time.monotonic()
        index = 0
        while True:
            elapsed = time.monotonic() - started
            phase = f"sample-{index:03d}"
            samples.append(sample_phase(args, store, captures, phase, elapsed))
            index += 1
            elapsed = time.monotonic() - started
            if elapsed >= sample_duration:
                break
            time.sleep(min(sample_interval, sample_duration - elapsed))

        cleanup_ok: bool | None = None
        if args.cleanup_disable:
            cleanup_capture = capture_command(store, "cleanup-disable-wifi", adb_shell_command(args, DISABLE_COMMAND), args.timeout)
            captures.append(cleanup_capture)
            cleanup_ok = cleanup_capture.ok
            if args.cleanup_settle_sleep > 0:
                time.sleep(args.cleanup_settle_sleep)
            captures.extend(capture_phase(args, store, "cleanup"))
            cleanup_state = local_phase_state(store, captures, "cleanup")

        classification = classify(state, samples, args.cleanup_disable, cleanup_ok, cleanup_state)
        decision = classification["decision"]
        pass_ok = classification["pass"]
        reason = classification["reason"]

    return {
        "generated_at": now_iso(),
        "command": "run",
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "host": collect_host_metadata(),
        "approval_ok": ok,
        "missing_approval_flags": missing,
        "adb_state": state,
        "sample_duration": max(0.0, args.sample_duration),
        "sample_interval": max(1.0, args.sample_interval),
        "cleanup_disable": args.cleanup_disable,
        "cleanup_settle_sleep": args.cleanup_settle_sleep,
        "classification": classification,
        "captures": [asdict(capture) for capture in captures],
        "cleanup_capture": asdict(cleanup_capture) if cleanup_capture else None,
        "guardrails": guardrails(args),
        "device_commands_executed": True,
        "device_mutations": cleanup_capture is not None,
        "wifi_disable_executed": cleanup_capture is not None,
        "wifi_bringup_executed": False,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    classification = manifest.get("classification", {})
    summary = classification.get("sample_summary") or {}
    captures = manifest.get("captures", [])
    sample_rows: list[list[str]] = []
    for sample in classification.get("samples", []):
        sample_rows.append(
            [
                sample.get("phase", "-"),
                str(sample.get("elapsed_sec", "-")),
                str(sample.get("enabled_by_status", "-")),
                str(sample.get("disabled_by_status", "-")),
                str(sample.get("wifi_connected", "-")),
                str(sample.get("wlan0_has_ip", "-")),
                str(sample.get("default_route_wlan", "-")),
                str(sample.get("route_get_wlan", "-")),
                str(sample.get("connectivity_validated_wifi", "-")),
                str(sample.get("dns_surface_wlan", "-")),
                str(sample.get("global_listener_observed", "-")),
            ]
        )
    cleanup_state = classification.get("cleanup_state") or {}
    cleanup_rows = [
        ["cleanup_requested", classification.get("cleanup_requested", "-")],
        ["cleanup_ok", classification.get("cleanup_ok", "-")],
        ["cleanup_contained", classification.get("cleanup_contained", "-")],
        ["cleanup.enabled_by_status", cleanup_state.get("enabled_by_status", "-")],
        ["cleanup.disabled_by_status", cleanup_state.get("disabled_by_status", "-")],
        ["cleanup.wlan0_has_ip", cleanup_state.get("wlan0_has_ip", "-")],
        ["cleanup.default_route_wlan", cleanup_state.get("default_route_wlan", "-")],
        ["cleanup.route_get_wlan", cleanup_state.get("route_get_wlan", "-")],
        ["cleanup.connectivity_validated_wifi", cleanup_state.get("connectivity_validated_wifi", "-")],
        ["cleanup.dns_surface_wlan", cleanup_state.get("dns_surface_wlan", "-")],
        ["cleanup.global_listener_observed", cleanup_state.get("global_listener_observed", "-")],
    ]
    capture_rows = [
        [
            item["name"],
            "ok" if item.get("ok") else ("plan" if "ok" not in item else "fail"),
            str(item.get("rc", "-")),
            f"{item.get('duration_sec', 0.0):.3f}s" if "duration_sec" in item else "-",
            item.get("file", "-"),
        ]
        for item in captures
    ]
    summary_rows = [[key, str(value)] for key, value in summary.items()]
    return "\n".join(
        [
            "# V439 Android Wi-Fi Post-reenable Observation",
            "",
            f"- generated: `{manifest['generated_at']}`",
            f"- command: `{manifest['command']}`",
            f"- decision: `{manifest['decision']}`",
            f"- pass: `{manifest['pass']}`",
            f"- reason: {manifest['reason']}",
            f"- next_gate: `{classification.get('next_gate', '-')}`",
            f"- approval_ok: `{manifest.get('approval_ok', '-')}`",
            f"- missing_approval_flags: `{', '.join(manifest.get('missing_approval_flags', [])) or '-'}`",
            f"- sample_duration: `{manifest.get('sample_duration', '-')}`",
            f"- sample_interval: `{manifest.get('sample_interval', '-')}`",
            f"- cleanup_disable: `{manifest.get('cleanup_disable', '-')}`",
            f"- device_commands_executed: `{manifest['device_commands_executed']}`",
            f"- device_mutations: `{manifest['device_mutations']}`",
            f"- wifi_disable_executed: `{manifest['wifi_disable_executed']}`",
            f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
            "",
            "## Sample Summary",
            "",
            markdown_table(["item", "value"], summary_rows if summary_rows else [["-", "-"]]),
            "",
            "## Samples",
            "",
            markdown_table(
                [
                    "phase",
                    "elapsed",
                    "enabled",
                    "disabled",
                    "connected",
                    "ip",
                    "default_route",
                    "route_get",
                    "validated",
                    "dns",
                    "listener",
                ],
                sample_rows if sample_rows else [["-", "-", "-", "-", "-", "-", "-", "-", "-", "-", "-"]],
            ),
            "",
            "## Cleanup",
            "",
            markdown_table(["item", "value"], [[str(a), str(b)] for a, b in cleanup_rows]),
            "",
            "## Captures",
            "",
            markdown_table(["name", "status", "rc", "duration", "file"], capture_rows if capture_rows else [["-", "-", "-", "-", "-"]]),
            "",
            "## Guardrails",
            "",
            *[f"- {item}" for item in manifest["guardrails"]],
            "",
        ]
    )


def main() -> int:
    args = parse_args()
    validate_command_guard()
    store = EvidenceStore(repo_path(args.out_dir))
    if args.command == "plan":
        manifest = run_plan(args)
    elif args.command == "preflight":
        manifest = run_preflight(args, store)
    else:
        manifest = run_capture_mode(args, store)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"device_mutations: {manifest['device_mutations']}")
    print(f"wifi_disable_executed: {manifest['wifi_disable_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

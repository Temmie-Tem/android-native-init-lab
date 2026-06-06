#!/usr/bin/env python3
"""V436 read-only Android Wi-Fi disabled persistence check.

V436 verifies the V435 containment result without issuing another disable
command.  It checks whether Android remains Wi-Fi-disabled after a fresh
boot-complete handoff and whether route/DNS/connectivity/listener exposure stays
absent.  It does not enable/disable Wi-Fi, scan, connect, change credentials,
send traffic, mutate routing, start daemons, write sysfs/rfkill, reboot, or
flash.
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
from wifi_android_autoconnect_disable_v435 import (
    CAPTURES,
    CaptureRecord,
    adb_base,
    adb_state,
    capture_phase,
    phase_state,
)


DEFAULT_OUT_DIR = Path("tmp/wifi/v436-android-wifi-disabled-persistence")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--adb", default="adb")
    parser.add_argument("--serial", default="")
    parser.add_argument("--timeout", type=int, default=25)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("plan")
    subparsers.add_parser("preflight")
    subparsers.add_parser("run")
    return parser.parse_args()


def classify(state: str, sample: dict[str, Any]) -> dict[str, Any]:
    route_absent = not sample.get("default_route_wlan") and not sample.get("route_get_wlan")
    connectivity_absent = not sample.get("connectivity_validated_wifi") and not sample.get("dns_surface_wlan")
    listener_safe = not sample.get("global_listener_observed")
    disabled = bool(sample.get("disabled_by_status")) and not bool(sample.get("enabled_by_status"))
    no_wlan_ip = not sample.get("wlan0_has_ip")

    if state == "adb-missing":
        decision = "v436-android-wifi-disabled-persistence-adb-missing"
        pass_ok = False
        reason = "adb executable is unavailable on host"
        next_gate = "restore ADB availability"
    elif state != "device":
        decision = "v436-android-wifi-disabled-persistence-waiting-for-android"
        pass_ok = False
        reason = f"Android ADB is not online (state={state or 'missing'})"
        next_gate = "boot Android before V436"
    elif disabled and no_wlan_ip and route_absent and connectivity_absent and listener_safe:
        decision = "v436-android-wifi-disabled-persistence-pass"
        pass_ok = True
        reason = "Wi-Fi remained disabled after fresh Android boot and exposure stayed absent"
        next_gate = "V437 controlled Android Wi-Fi re-enable plan or native Wi-Fi branch decision"
    elif disabled:
        decision = "v436-android-wifi-disabled-partial-persistence"
        pass_ok = False
        reason = "Wi-Fi reports disabled, but route/DNS/connectivity/listener exposure was not fully absent"
        next_gate = "repeat persistence check or inspect stale Android connectivity state"
    else:
        decision = "v436-android-wifi-disabled-persistence-regression"
        pass_ok = False
        reason = "Wi-Fi did not remain disabled on fresh Android boot"
        next_gate = "return to V435 containment or decide controlled re-disable policy"

    return {
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_gate": next_gate,
        "sample": sample,
        "disabled": disabled,
        "no_wlan_ip": no_wlan_ip,
        "route_absent": route_absent,
        "connectivity_absent": connectivity_absent,
        "listener_safe": listener_safe,
    }


def guardrails() -> list[str]:
    return [
        "read-only Android Wi-Fi disabled persistence check only",
        "no Wi-Fi enable/disable, scan/connect, credentials, DHCP/routing mutation, or external packet probes",
        "no server exposure, rfkill/sysfs write, module operation, setprop, direct daemon start, reboot, or flash in this collector",
        "route/DNS/connectivity/listener state is verified read-only",
    ]


def run_plan(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "generated_at": now_iso(),
        "command": "plan",
        "decision": "v436-android-wifi-disabled-persistence-plan-ready",
        "pass": True,
        "reason": "read-only Android Wi-Fi disabled persistence plan generated",
        "host": collect_host_metadata(),
        "captures": [{"name": name, "command": command, "timeout": timeout} for name, command, timeout in CAPTURES],
        "guardrails": guardrails(),
        "device_commands_executed": False,
        "device_mutations": False,
        "wifi_disable_executed": False,
        "wifi_bringup_executed": False,
    }


def run_preflight(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    captures, state = adb_state(args, store)
    if state == "device":
        decision = "v436-android-wifi-disabled-persistence-adb-online"
        pass_ok = True
        reason = "Android ADB is online; run mode can collect read-only persistence state"
    elif state == "adb-missing":
        decision = "v436-android-wifi-disabled-persistence-adb-missing"
        pass_ok = False
        reason = "adb executable is unavailable on host"
    else:
        decision = "v436-android-wifi-disabled-persistence-waiting-for-android"
        pass_ok = True
        reason = f"Android ADB is not online yet (state={state or 'missing'})"
    return {
        "generated_at": now_iso(),
        "command": "preflight",
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "host": collect_host_metadata(),
        "adb_state": state,
        "captures": [asdict(capture) for capture in captures],
        "guardrails": guardrails(),
        "device_commands_executed": True,
        "device_mutations": False,
        "wifi_disable_executed": False,
        "wifi_bringup_executed": False,
    }


def run_capture_mode(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    captures, state = adb_state(args, store)
    sample: dict[str, Any] = {}
    if state == "device":
        captures.extend(capture_phase(args, store, "sample"))
        sample = phase_state(store, captures, "sample")
    classification = classify(state, sample)
    return {
        "generated_at": now_iso(),
        "command": "run",
        "decision": classification["decision"],
        "pass": classification["pass"],
        "reason": classification["reason"],
        "host": collect_host_metadata(),
        "adb_state": state,
        "classification": classification,
        "captures": [asdict(capture) for capture in captures],
        "guardrails": guardrails(),
        "device_commands_executed": True,
        "device_mutations": False,
        "wifi_disable_executed": False,
        "wifi_bringup_executed": False,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    classification = manifest.get("classification", {})
    sample = classification.get("sample") or {}
    captures = manifest.get("captures", [])
    state_rows = [
        ["enabled_by_status", sample.get("enabled_by_status", "-")],
        ["disabled_by_status", sample.get("disabled_by_status", "-")],
        ["wlan0_has_ip", sample.get("wlan0_has_ip", "-")],
        ["default_route_wlan", sample.get("default_route_wlan", "-")],
        ["route_get_wlan", sample.get("route_get_wlan", "-")],
        ["connectivity_validated_wifi", sample.get("connectivity_validated_wifi", "-")],
        ["dns_surface_wlan", sample.get("dns_surface_wlan", "-")],
        ["global_listener_observed", sample.get("global_listener_observed", "-")],
        ["route_absent", classification.get("route_absent", "-")],
        ["connectivity_absent", classification.get("connectivity_absent", "-")],
        ["listener_safe", classification.get("listener_safe", "-")],
    ]
    evidence_rows: list[list[str]] = []
    for key in ("status_lines", "route_lines", "connectivity_lines"):
        for line in sample.get(key, [])[:24]:
            evidence_rows.append([key, line])
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
    return "\n".join(
        [
            "# V436 Android Wi-Fi Disabled Persistence Check",
            "",
            f"- generated: `{manifest['generated_at']}`",
            f"- command: `{manifest['command']}`",
            f"- decision: `{manifest['decision']}`",
            f"- pass: `{manifest['pass']}`",
            f"- reason: {manifest['reason']}",
            f"- next_gate: `{classification.get('next_gate', '-')}`",
            f"- device_commands_executed: `{manifest['device_commands_executed']}`",
            f"- device_mutations: `{manifest['device_mutations']}`",
            f"- wifi_disable_executed: `{manifest['wifi_disable_executed']}`",
            f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
            "",
            "## State Summary",
            "",
            markdown_table(["item", "value"], [[str(a), str(b)] for a, b in state_rows]),
            "",
            "## Evidence Lines",
            "",
            markdown_table(["source", "line"], evidence_rows if evidence_rows else [["-", "-"]]),
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

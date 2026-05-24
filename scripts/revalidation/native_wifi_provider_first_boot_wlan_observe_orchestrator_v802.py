#!/usr/bin/env python3
"""V802 current-boot orchestrator for provider-first plus boot_wlan observe."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import native_wifi_same_helper_replay_v673 as v673
from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v802-provider-first-boot-wlan-observe-orchestrated")
V802_SCRIPT = "scripts/revalidation/native_wifi_provider_first_boot_wlan_observe_v802.py"
HELPER_SHA256 = "d44cbb538db11a280aa789ccafb008476ac541ec08bb96f549670ae28db7cec6"
HELPER_MARKER = "a90_android_execns_probe v124"
DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.68 (v724)"

ALLOWED_LIVE_ACTIONS = (
    "V641 one-shot clean-DSP reboot",
    "V401 SELinuxfs mount surface",
    "V490 Android SELinux policy-load proof",
    "bounded helper v124 provider-first service74/PeripheralManager/CNSS retry context",
    "bounded a90_wlanbootctl boot-observe after provider-first context",
    "read-only ICNSS/QCA/WLAN focused captures",
    "runner-owned reboot cleanup",
)
FORBIDDEN_ACTIONS = (
    "Wi-Fi HAL, wificond, supplicant, or hostapd start",
    "Wi-Fi scan/connect/link-up",
    "credential use",
    "DHCP, route change, or external ping",
    "qcwlanstate direct write",
    "esoc0 open or hold",
    "bind/unbind, driver_override, or module load/unload",
    "boot image or partition write",
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--host", "--bridge-host", dest="host", default=v673.DEFAULT_HOST)
    parser.add_argument("--port", "--bridge-port", dest="port", type=int, default=v673.DEFAULT_PORT)
    parser.add_argument("--expect-version", default=DEFAULT_EXPECT_VERSION)
    parser.add_argument("--helper", default=v673.DEFAULT_HELPER)
    parser.add_argument("--helper-sha256", default=HELPER_SHA256)
    parser.add_argument("--helper-marker", default=HELPER_MARKER)
    parser.add_argument("--wait-sec", type=float, default=75.0)
    parser.add_argument("--cnss-runtime-sec", type=int, default=30)
    parser.add_argument("--boot-observe-sec", type=int, default=25)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--assume-yes", action="store_true")
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def run_host(command: list[str], *, timeout: float) -> tuple[int, str]:
    proc = subprocess.run(
        command,
        cwd=repo_path(Path(".")),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
        check=False,
    )
    return proc.returncode, proc.stdout


def write_host_output(store: EvidenceStore, name: str, command: list[str], rc: int, output: str) -> str:
    rel = f"host/{name}.txt"
    store.write_text(rel, "$ " + " ".join(command) + "\nrc=" + str(rc) + "\n" + output.rstrip() + "\n")
    return rel


def run_script(store: EvidenceStore, name: str, command: list[str], timeout: float) -> dict[str, Any]:
    rc, output = run_host(command, timeout=timeout)
    return {
        "rc": rc,
        "ok": rc == 0,
        "file": write_host_output(store, name, command, rc, output),
        "output_tail": output.splitlines()[-24:],
    }


def load_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {}
    data = json.loads(resolved.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def build_v802_command(args: argparse.Namespace, out_dir: Path, v490_manifest: Path) -> list[str]:
    return [
        sys.executable,
        V802_SCRIPT,
        "--out-dir",
        str(out_dir),
        "--host",
        args.host,
        "--port",
        str(args.port),
        "--expect-version",
        args.expect_version,
        "--helper",
        args.helper,
        "--helper-sha256",
        args.helper_sha256,
        "--helper-marker",
        args.helper_marker,
        "--v490-manifest",
        str(v490_manifest),
        "--cnss-runtime-sec",
        str(max(10, min(30, args.cnss_runtime_sec))),
        "--boot-observe-sec",
        str(max(5, min(60, args.boot_observe_sec))),
        "--allow-cnss-then-boot-wlan",
        "--assume-yes",
        "run",
    ]


def run_arm(args: argparse.Namespace, store: EvidenceStore, arm_root: Path, v490_manifest: Path) -> dict[str, Any]:
    live_dir = arm_root / "live"
    command = build_v802_command(args, live_dir, v490_manifest)
    result = run_script(store, "v802-live", command, 600.0)
    manifest_path = live_dir / "manifest.json"
    manifest = load_json(manifest_path)
    return {
        **result,
        "manifest": str(manifest_path),
        "decision": manifest.get("decision", ""),
        "pass": manifest.get("pass"),
        "reason": manifest.get("reason", ""),
        "next_step": manifest.get("next_step", ""),
        "live": manifest.get("live") or {},
        "provider_first_context_executed": manifest.get("provider_first_context_executed"),
        "boot_wlan_write_executed": manifest.get("boot_wlan_write_executed"),
        "service_manager_start_executed": manifest.get("service_manager_start_executed"),
        "wifi_hal_start_executed": manifest.get("wifi_hal_start_executed"),
        "scan_connect_executed": manifest.get("scan_connect_executed"),
        "external_ping_executed": manifest.get("external_ping_executed"),
    }


def int_value(value: object) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def arm_live(arm: dict[str, Any] | None) -> dict[str, Any]:
    return (arm or {}).get("live") or {}


def counts_for(arm: dict[str, Any] | None) -> dict[str, int]:
    counts = ((arm_live(arm).get("markers") or {}).get("counts") or {})
    names = (
        "wlan_loading",
        "hdd_state_major",
        "wlan_driver_loaded",
        "wlan_driver_failure",
        "icnss_qmi_connected",
        "fw_ready",
        "wlfw",
        "bdf",
        "wlan0",
        "wiphy",
        "kernel_warning",
        "qcwlanstate",
        "boot_wlan",
        "service_notifier",
    )
    return {name: int_value(counts.get(name)) for name in names}


def helper_for(arm: dict[str, Any] | None) -> dict[str, Any]:
    helper = arm_live(arm).get("helper_result")
    return helper if isinstance(helper, dict) else {}


def checks_for(prep: dict[str, Any] | None, arm: dict[str, Any] | None) -> list[dict[str, Any]]:
    counts = counts_for(arm)
    helper = helper_for(arm)
    return [
        {
            "name": "current-boot-prep-ready",
            "status": "pass" if prep and prep.get("ready") else "blocked",
            "detail": {"ready": bool(prep and prep.get("ready"))},
            "next_step": "restore V641/V401/V490 current-boot prerequisites",
        },
        {
            "name": "v802-arm-produced-manifest",
            "status": "pass" if arm and arm.get("decision") and arm.get("pass") is True else "blocked",
            "detail": {"decision": (arm or {}).get("decision"), "pass": (arm or {}).get("pass"), "manifest": (arm or {}).get("manifest")},
            "next_step": "inspect V802 arm host output",
        },
        {
            "name": "provider-first-context",
            "status": "pass" if arm and arm.get("provider_first_context_executed") else "blocked",
            "detail": {
                "mode": helper.get("mode"),
                "service74_gate": helper.get("service74_gate"),
                "provider_query_exact": helper.get("provider_query_exact"),
                "cnss_retry": helper.get("cnss_retry"),
            },
            "next_step": "repair provider-first context before interpreting boot_wlan",
        },
        {
            "name": "boot-wlan-executed",
            "status": "pass" if arm and arm.get("boot_wlan_write_executed") else "blocked",
            "detail": {"boot_wlan_write_executed": (arm or {}).get("boot_wlan_write_executed")},
            "next_step": "inspect a90_wlanbootctl contract",
        },
        {
            "name": "forbidden-connect-actions",
            "status": "pass" if arm and not arm.get("wifi_hal_start_executed") and not arm.get("scan_connect_executed") and not arm.get("external_ping_executed") else "blocked",
            "detail": {
                "wifi_hal": (arm or {}).get("wifi_hal_start_executed"),
                "scan_connect": (arm or {}).get("scan_connect_executed"),
                "external_ping": (arm or {}).get("external_ping_executed"),
            },
            "next_step": "stop if live proof crossed connection boundary",
        },
        {
            "name": "driver-progression",
            "status": "pass" if any(counts.get(name, 0) for name in ("wlan_driver_loaded", "icnss_qmi_connected", "fw_ready", "wlfw", "bdf", "wlan0", "wiphy")) else "finding",
            "detail": counts,
            "next_step": "if still absent, instrument HDD/PLD boundary in this exact window",
        },
    ]


def decide(command: str, prep: dict[str, Any] | None, arm: dict[str, Any] | None) -> tuple[str, bool, str, str]:
    if command == "plan":
        return (
            "v802-provider-first-boot-wlan-orchestrator-plan-ready",
            True,
            "plan-only; no device command executed",
            "run V802 current-boot prep plus live arm",
        )
    blocked = [check["name"] for check in checks_for(prep, arm) if check["status"] == "blocked"]
    if blocked:
        return "v802-provider-first-boot-wlan-orchestrator-blocked", False, "blocked by " + ", ".join(blocked), "clear blocker before retry"
    if str((arm or {}).get("decision", "")).endswith("netdev-appeared"):
        return (
            "v802-provider-first-boot-wlan-netdev-appeared",
            True,
            str((arm or {}).get("reason", "")),
            "plan link-readiness and scan-only gate before credentials",
        )
    if str((arm or {}).get("decision", "")).endswith("driver-advanced"):
        return (
            "v802-provider-first-boot-wlan-driver-advanced",
            True,
            str((arm or {}).get("reason", "")),
            "classify driver-ready-to-netdev gap before HAL/connect",
        )
    return (
        "v802-provider-first-boot-wlan-hdd-boundary-classified",
        True,
        str((arm or {}).get("reason", "")),
        "instrument HDD/PLD init prerequisites inside provider-first boot_wlan window",
    )


def summarize_arm(arm: dict[str, Any] | None) -> dict[str, Any]:
    if not arm:
        return {}
    live = arm_live(arm)
    reboot = live.get("reboot_cleanup") or {}
    return {
        "decision": arm.get("decision", ""),
        "pass": arm.get("pass"),
        "reason": arm.get("reason", ""),
        "next_step": arm.get("next_step", ""),
        "manifest": arm.get("manifest", ""),
        "rc": arm.get("rc"),
        "ok": arm.get("ok"),
        "provider_first_context_executed": arm.get("provider_first_context_executed"),
        "boot_wlan_write_executed": arm.get("boot_wlan_write_executed"),
        "counts": counts_for(arm),
        "helper": {
            key: helper_for(arm).get(key)
            for key in ("mode", "order", "service74_gate", "provider_query_exact", "initial_cnss_suppressed", "cnss_retry", "cnss_retry_signal")
        },
        "reboot_cleanup": {
            "version_seen": reboot.get("version_seen"),
            "status_healthy": reboot.get("status_healthy"),
            "wait_sec": reboot.get("wait_sec"),
        },
    }


def build_manifest(args: argparse.Namespace, prep: dict[str, Any] | None, arm: dict[str, Any] | None) -> dict[str, Any]:
    decision, pass_ok, reason, next_step = decide(args.command, prep, arm)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "cycle": "v802",
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "helper_marker": args.helper_marker,
        "helper_sha256": args.helper_sha256,
        "cnss_runtime_sec": args.cnss_runtime_sec,
        "boot_observe_sec": args.boot_observe_sec,
        "allowed_live_actions": ALLOWED_LIVE_ACTIONS,
        "forbidden_actions": FORBIDDEN_ACTIONS,
        "prep_v802": prep or {},
        "arm_v802": summarize_arm(arm),
        "checks": [] if args.command == "plan" else checks_for(prep, arm),
        "device_commands_executed": args.command == "run",
        "device_mutations": args.command == "run",
        "provider_first_context_executed": bool(arm and arm.get("provider_first_context_executed")),
        "boot_wlan_write_executed": bool(arm and arm.get("boot_wlan_write_executed")),
        "service_manager_start_executed": bool(arm and arm.get("service_manager_start_executed")),
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "wifi_bringup_executed": False,
        "external_ping_executed": False,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    arm = manifest["arm_v802"]
    rows: list[list[str]] = []
    for section in ("counts", "helper", "reboot_cleanup"):
        for key, value in (arm.get(section) or {}).items():
            rows.append([section, key, json.dumps(value, sort_keys=True) if isinstance(value, (dict, list)) else str(value)])
    check_rows = [
        [check["name"], check["status"], json.dumps(check["detail"], sort_keys=True), check["next_step"]]
        for check in manifest["checks"]
    ]
    return "\n".join([
        "# V802 Provider-first Boot WLAN Observe Orchestrator",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- helper_marker: `{manifest['helper_marker']}`",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- provider_first_context_executed: `{manifest['provider_first_context_executed']}`",
        f"- boot_wlan_write_executed: `{manifest['boot_wlan_write_executed']}`",
        f"- wifi_hal_start_executed: `{manifest['wifi_hal_start_executed']}`",
        f"- scan_connect_executed: `{manifest['scan_connect_executed']}`",
        f"- external_ping_executed: `{manifest['external_ping_executed']}`",
        "",
        "## Checks",
        "",
        markdown_table(["check", "status", "detail", "next"], check_rows) if check_rows else "- plan only",
        "",
        "## Runtime Surface",
        "",
        markdown_table(["surface", "key", "value"], rows) if rows else "- no runtime surface",
        "",
        "## Guardrails",
        "",
        "\n".join(f"- {item}" for item in manifest["forbidden_actions"]),
        "",
    ])


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    prep: dict[str, Any] | None = None
    arm: dict[str, Any] | None = None
    if args.command == "run":
        arm_root = store.run_dir / "arm-v802-provider-first-boot-wlan"
        prep = v673.prep_current_boot(args, store, "v802", arm_root)
        if prep.get("ready"):
            arm = run_arm(args, store, arm_root, Path(str(prep["v490"]["manifest"])))
    manifest = build_manifest(args, prep, arm)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"provider_first_context_executed: {manifest['provider_first_context_executed']}")
    print(f"boot_wlan_write_executed: {manifest['boot_wlan_write_executed']}")
    print(f"wifi_hal_start_executed: {manifest['wifi_hal_start_executed']}")
    print(f"scan_connect_executed: {manifest['scan_connect_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

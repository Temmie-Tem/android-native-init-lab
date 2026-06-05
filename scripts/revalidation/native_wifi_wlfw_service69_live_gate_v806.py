#!/usr/bin/env python3
"""V806 bounded live gate for WLFW QRTR service69 arrival."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v806-wlfw-service69-live-gate")
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 54321
DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.244 (v725-fasttransport)"
DEFAULT_V805_MANIFEST = Path("tmp/wifi/v805-icnss-fw-ready-wlfw-gate-classifier/manifest.json")
V802_ORCHESTRATOR = "scripts/revalidation/native_wifi_provider_first_boot_wlan_observe_orchestrator_v802.py"
A90CTL = "scripts/revalidation/a90ctl.py"

ALLOWED_LIVE_ACTIONS = (
    "hide native menu if active",
    "V802 current-boot prep: clean-DSP reboot, SELinuxfs mount surface, SELinux policy-load proof",
    "helper v124 provider-first service74/PeripheralManager/CNSS retry context",
    "bounded a90_wlanbootctl boot-observe",
    "read-only QRTR/WLFW/ICNSS/QCA/WLAN surface captures inside V802 arm",
    "runner-owned reboot cleanup",
)
FORBIDDEN_ACTIONS = (
    "custom kernel flash or boot image write",
    "partition write outside V802 current-boot prep",
    "Wi-Fi HAL, wificond, supplicant, or hostapd start",
    "Wi-Fi scan/connect/link-up",
    "credential use",
    "DHCP, route change, or external ping",
    "qcwlanstate direct write",
    "esoc0 open or hold",
    "bind/unbind, driver_override, or module load/unload",
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--host", "--bridge-host", dest="host", default=DEFAULT_HOST)
    parser.add_argument("--port", "--bridge-port", dest="port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--expect-version", default=DEFAULT_EXPECT_VERSION)
    parser.add_argument("--v805-manifest", type=Path, default=DEFAULT_V805_MANIFEST)
    parser.add_argument("--cnss-runtime-sec", type=int, default=30)
    parser.add_argument("--boot-observe-sec", type=int, default=30)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {}
    try:
        data = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def int_value(value: object) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


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
        "output_tail": output.splitlines()[-40:],
    }


def v805_ready(args: argparse.Namespace) -> dict[str, Any]:
    manifest = load_json(args.v805_manifest)
    return {
        "manifest": str(repo_path(args.v805_manifest)),
        "decision": manifest.get("decision", ""),
        "pass": bool(manifest.get("pass")),
        "ready": manifest.get("decision") == "v805-wlfw-service69-arrival-gate-selected" and bool(manifest.get("pass")),
    }


def hide_menu(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    command = [
        sys.executable,
        A90CTL,
        "--host",
        args.host,
        "--port",
        str(args.port),
        "--hide-on-busy",
        "hide",
    ]
    return run_script(store, "hide-menu", command, 30.0)


def build_v802_command(args: argparse.Namespace, out_dir: Path) -> list[str]:
    return [
        sys.executable,
        V802_ORCHESTRATOR,
        "--out-dir",
        str(out_dir),
        "--host",
        args.host,
        "--port",
        str(args.port),
        "--expect-version",
        args.expect_version,
        "--cnss-runtime-sec",
        str(max(10, min(30, args.cnss_runtime_sec))),
        "--boot-observe-sec",
        str(max(10, min(60, args.boot_observe_sec))),
        "run",
    ]


def run_v802_arm(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    v802_out = store.run_dir / "v802-provider-first-boot-wlan"
    command = build_v802_command(args, v802_out)
    result = run_script(store, "v802-orchestrator", command, 900.0)
    manifest_path = v802_out / "manifest.json"
    manifest = load_json(manifest_path)
    direct_manifest_path = Path(str(((manifest.get("arm_v802") or {}).get("manifest") or "")))
    direct_manifest = load_json(direct_manifest_path) if str(direct_manifest_path) else {}
    return {
        **result,
        "manifest": str(manifest_path),
        "decision": manifest.get("decision", ""),
        "pass": manifest.get("pass"),
        "reason": manifest.get("reason", ""),
        "next_step": manifest.get("next_step", ""),
        "provider_first_context_executed": manifest.get("provider_first_context_executed"),
        "boot_wlan_write_executed": manifest.get("boot_wlan_write_executed"),
        "service_manager_start_executed": manifest.get("service_manager_start_executed"),
        "wifi_hal_start_executed": manifest.get("wifi_hal_start_executed"),
        "scan_connect_executed": manifest.get("scan_connect_executed"),
        "credential_use_executed": manifest.get("credential_use_executed"),
        "dhcp_route_executed": manifest.get("dhcp_route_executed"),
        "external_ping_executed": manifest.get("external_ping_executed"),
        "arm_v802": manifest.get("arm_v802") or {},
        "direct_manifest": str(direct_manifest_path),
        "direct": direct_manifest,
    }


def direct_live(v802: dict[str, Any]) -> dict[str, Any]:
    direct = v802.get("direct") if isinstance(v802.get("direct"), dict) else {}
    live = direct.get("live") if isinstance(direct.get("live"), dict) else {}
    return live


def signal_summary(v802: dict[str, Any]) -> dict[str, Any]:
    live = direct_live(v802)
    markers = live.get("markers") if isinstance(live.get("markers"), dict) else {}
    counts = markers.get("counts") if isinstance(markers.get("counts"), dict) else {}
    qrtr_services = live.get("qrtr_services_after_boot") if isinstance(live.get("qrtr_services_after_boot"), dict) else {}
    helper = live.get("helper_result") if isinstance(live.get("helper_result"), dict) else {}
    return {
        "qrtr_service69": int_value(qrtr_services.get("69")),
        "qrtr_service74": int_value(qrtr_services.get("74")),
        "qrtr_service180": int_value(qrtr_services.get("180")),
        "wlfw": int_value(counts.get("wlfw")),
        "icnss_qmi_connected": int_value(counts.get("icnss_qmi_connected")),
        "fw_ready": int_value(counts.get("fw_ready")),
        "bdf": int_value(counts.get("bdf")),
        "wiphy": int_value(counts.get("wiphy")) or int(bool(live.get("wiphy_after"))),
        "wlan0": int_value(counts.get("wlan0")) or int(bool(live.get("wlan0_after"))),
        "wlan_loading": int_value(counts.get("wlan_loading")),
        "wlan_driver_loaded": int_value(counts.get("wlan_driver_loaded")),
        "qcwlanstate": int_value(counts.get("qcwlanstate")),
        "service_notifier": int_value(counts.get("service_notifier")),
        "qrtr_rx": int_value(counts.get("qrtr_rx")),
        "qrtr_tx": int_value(counts.get("qrtr_tx")),
        "provider_query_exact": bool(helper.get("provider_query_exact")),
        "service74_gate_open": (helper.get("service74_gate") or {}).get("open") == "1" if isinstance(helper.get("service74_gate"), dict) else False,
        "initial_cnss_suppressed": bool(helper.get("initial_cnss_suppressed")),
        "cnss_retry_started": bool(helper.get("cnss_retry_started")),
        "all_postflight_safe": int_value(helper.get("all_postflight_safe")),
        "reboot_cleanup": live.get("reboot_cleanup") or {},
        "qrtr_services_after_boot": qrtr_services,
        "marker_counts": counts,
    }


def build_checks(command: str, v805: dict[str, Any], hide: dict[str, Any] | None, v802: dict[str, Any] | None) -> list[dict[str, Any]]:
    if command == "plan":
        return [{
            "name": "plan-only",
            "status": "pass",
            "detail": "no device command executed",
            "next_step": "run V806 bounded live gate",
        }]
    signals = signal_summary(v802 or {})
    reboot = signals.get("reboot_cleanup") if isinstance(signals.get("reboot_cleanup"), dict) else {}
    forbidden = {
        "wifi_hal_start_executed": bool((v802 or {}).get("wifi_hal_start_executed")),
        "scan_connect_executed": bool((v802 or {}).get("scan_connect_executed")),
        "credential_use_executed": bool((v802 or {}).get("credential_use_executed")),
        "dhcp_route_executed": bool((v802 or {}).get("dhcp_route_executed")),
        "external_ping_executed": bool((v802 or {}).get("external_ping_executed")),
    }
    return [
        {
            "name": "v805-route-ready",
            "status": "pass" if v805.get("ready") else "blocked",
            "detail": v805,
            "next_step": "complete V805 before V806 live gate",
        },
        {
            "name": "menu-hidden-or-nonblocking",
            "status": "pass" if hide and hide.get("rc") == 0 else "finding",
            "detail": {"rc": (hide or {}).get("rc"), "ok": (hide or {}).get("ok"), "tail": (hide or {}).get("output_tail")},
            "next_step": "if V802 is busy, hide menu and retry once",
        },
        {
            "name": "v802-live-arm-produced",
            "status": "pass" if v802 and v802.get("pass") is True and v802.get("decision") else "blocked",
            "detail": {"decision": (v802 or {}).get("decision"), "pass": (v802 or {}).get("pass"), "manifest": (v802 or {}).get("manifest"), "direct_manifest": (v802 or {}).get("direct_manifest")},
            "next_step": "inspect V802 orchestrator output",
        },
        {
            "name": "provider-first-boot-wlan-executed",
            "status": "pass" if v802 and v802.get("provider_first_context_executed") and v802.get("boot_wlan_write_executed") else "blocked",
            "detail": {
                "provider_first_context_executed": (v802 or {}).get("provider_first_context_executed"),
                "boot_wlan_write_executed": (v802 or {}).get("boot_wlan_write_executed"),
                "signals": {
                    "provider_query_exact": signals.get("provider_query_exact"),
                    "service74_gate_open": signals.get("service74_gate_open"),
                    "initial_cnss_suppressed": signals.get("initial_cnss_suppressed"),
                    "cnss_retry_started": signals.get("cnss_retry_started"),
                    "all_postflight_safe": signals.get("all_postflight_safe"),
                },
            },
            "next_step": "repair provider-first context before interpreting service69",
        },
        {
            "name": "forbidden-connect-actions",
            "status": "pass" if not any(forbidden.values()) else "blocked",
            "detail": forbidden,
            "next_step": "stop if live gate crossed HAL/connect/network boundary",
        },
        {
            "name": "service69-observed",
            "status": "pass" if signals.get("qrtr_service69") or signals.get("wlfw") else "finding",
            "detail": {
                "qrtr_service69": signals.get("qrtr_service69"),
                "wlfw": signals.get("wlfw"),
                "qrtr_services_after_boot": signals.get("qrtr_services_after_boot"),
                "marker_counts": {
                    key: signals.get(key)
                    for key in ("qrtr_rx", "qrtr_tx", "service_notifier", "wlan_loading", "icnss_qmi_connected", "fw_ready", "bdf", "wiphy", "wlan0")
                },
            },
            "next_step": "if absent, classify pre-WLFW publication; if present without FW_READY, classify ICNSS-QMI handshake",
        },
        {
            "name": "postflight-reboot-cleanup",
            "status": "pass" if reboot.get("version_seen") and reboot.get("status_healthy") else "blocked",
            "detail": reboot,
            "next_step": "manually verify native if cleanup health is not proven",
        },
    ]


def decide(command: str, checks: list[dict[str, Any]], v802: dict[str, Any] | None) -> tuple[str, bool, str, str]:
    if command == "plan":
        return (
            "v806-wlfw-service69-live-gate-plan-ready",
            True,
            "plan-only; no device command executed",
            "run V806 bounded live gate",
        )
    blocked = [check["name"] for check in checks if check["status"] == "blocked"]
    if blocked:
        return "v806-wlfw-service69-live-gate-blocked", False, "blocked by " + ", ".join(blocked), "clear live gate blocker"
    signals = signal_summary(v802 or {})
    if signals.get("wlan0"):
        return (
            "v806-wlan0-appeared-before-hal",
            True,
            "provider-first boot_wlan produced wlan0 before HAL/connect boundary",
            "plan link-readiness and scan-only gate before credential use",
        )
    if signals.get("fw_ready") or signals.get("wlan_driver_loaded") or signals.get("wiphy"):
        return (
            "v806-fw-ready-or-driver-advanced",
            True,
            "WLFW/FW_READY path advanced beyond previous gate without crossing HAL/connect boundary",
            "classify driver-ready-to-netdev gap before HAL/connect",
        )
    if signals.get("qrtr_service69") or signals.get("wlfw") or signals.get("icnss_qmi_connected"):
        return (
            "v806-service69-published-qmi-fw-ready-gap",
            True,
            "WLFW service69 or ICNSS-QMI appeared, but FW_READY/netdev did not complete",
            "classify ICNSS-QMI WLFW handshake/BDF gap",
        )
    return (
        "v806-service69-absent-after-provider-first-boot-wlan",
        True,
        "provider-first service74/180 and boot_wlan path executed, but QRTR service69/WLFW/QMI-connected/FW_READY/BDF/netdev remained absent",
        "classify pre-WLFW publication prerequisites rather than repeating provider-first boot_wlan",
    )


def build_manifest(args: argparse.Namespace,
                   v805: dict[str, Any],
                   hide: dict[str, Any] | None,
                   v802: dict[str, Any] | None) -> dict[str, Any]:
    checks = build_checks(args.command, v805, hide, v802)
    decision, pass_ok, reason, next_step = decide(args.command, checks, v802)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "cycle": "v806",
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "inputs": {"v805_manifest": str(repo_path(args.v805_manifest))},
        "allowed_live_actions": ALLOWED_LIVE_ACTIONS,
        "forbidden_actions": FORBIDDEN_ACTIONS,
        "v805": v805,
        "hide": hide or {},
        "v802": v802 or {},
        "signals": signal_summary(v802 or {}) if v802 else {},
        "checks": checks,
        "device_commands_executed": args.command == "run",
        "device_mutations": args.command == "run",
        "provider_first_context_executed": bool(v802 and v802.get("provider_first_context_executed")),
        "boot_wlan_write_executed": bool(v802 and v802.get("boot_wlan_write_executed")),
        "service_manager_start_executed": bool(v802 and v802.get("service_manager_start_executed")),
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "wifi_bringup_executed": False,
        "custom_kernel_flash_executed": False,
        "boot_image_write_executed": False,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    signal_rows = [[key, json.dumps(value, sort_keys=True) if isinstance(value, (dict, list)) else str(value)] for key, value in sorted(manifest.get("signals", {}).items())]
    check_rows = [
        [check["name"], check["status"], json.dumps(check["detail"], sort_keys=True), check["next_step"]]
        for check in manifest["checks"]
    ]
    return "\n".join([
        "# V806 WLFW Service69 Live Gate",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- provider_first_context_executed: `{manifest['provider_first_context_executed']}`",
        f"- boot_wlan_write_executed: `{manifest['boot_wlan_write_executed']}`",
        f"- wifi_hal_start_executed: `{manifest['wifi_hal_start_executed']}`",
        f"- scan_connect_executed: `{manifest['scan_connect_executed']}`",
        f"- external_ping_executed: `{manifest['external_ping_executed']}`",
        "",
        "## Checks",
        "",
        markdown_table(["check", "status", "detail", "next"], check_rows),
        "",
        "## Signals",
        "",
        markdown_table(["signal", "value"], signal_rows) if signal_rows else "- no live signals",
        "",
        "## Guardrails",
        "",
        "\n".join(f"- {item}" for item in manifest["forbidden_actions"]),
        "",
    ])


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    v805 = v805_ready(args)
    hide: dict[str, Any] | None = None
    v802: dict[str, Any] | None = None
    if args.command == "run":
        hide = hide_menu(args, store)
        if v805.get("ready"):
            v802 = run_v802_arm(args, store)
    manifest = build_manifest(args, v805, hide, v802)
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
    print(f"credential_use_executed: {manifest['credential_use_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

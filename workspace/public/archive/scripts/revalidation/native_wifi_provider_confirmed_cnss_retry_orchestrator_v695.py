#!/usr/bin/env python3
"""V695 current-boot orchestrator for provider-confirmed CNSS retry proof."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

import native_wifi_same_helper_replay_v673 as v673
from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v695-provider-confirmed-cnss-retry-orchestrated")
V695_SCRIPT = "scripts/revalidation/native_wifi_provider_confirmed_cnss_retry_v695.py"
V695_APPROVAL = (
    "approve v695 provider-confirmed CNSS retry proof only; "
    "no Wi-Fi HAL start, no scan/connect/link-up, no DHCP and no external ping"
)
HELPER_SHA256 = "7f91a939df2333dde0d92548d236a321d4b0adcce3d02e4d462e9178ac447e36"
HELPER_MARKER = "a90_android_execns_probe v118"

ALLOWED_LIVE_ACTIONS = (
    "V641 one-shot clean-DSP reboot",
    "V401 SELinuxfs mount surface",
    "V490 Android SELinux policy-load proof",
    "bounded helper v118 provider-confirmed CNSS retry proof",
    "read-only cnss2/icnss/QCA6390 focused captures",
    "WLFW QRTR nameservice readback without QMI payload",
    "runner-owned reboot cleanup",
)
FORBIDDEN_ACTIONS = (
    "Wi-Fi HAL or wificond start",
    "supplicant or hostapd start",
    "Wi-Fi scan/connect/link-up",
    "credential use",
    "DHCP, route change, or external ping",
    "sysfs subsystem state write",
    "esoc0 open or hold",
    "boot image or partition write",
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--host", "--bridge-host", dest="host", default=v673.DEFAULT_HOST)
    parser.add_argument("--port", "--bridge-port", dest="port", type=int, default=v673.DEFAULT_PORT)
    parser.add_argument("--expect-version", default=v673.DEFAULT_EXPECT_VERSION)
    parser.add_argument("--helper", default=v673.DEFAULT_HELPER)
    parser.add_argument("--helper-sha256", default=HELPER_SHA256)
    parser.add_argument("--helper-marker", default=HELPER_MARKER)
    parser.add_argument("--wait-sec", type=float, default=75.0)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--assume-yes", action="store_true")
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def int_value(value: object) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def arm_live(arm: dict[str, Any] | None) -> dict[str, Any]:
    return (arm or {}).get("live") or {}


def counts_for(arm: dict[str, Any] | None) -> dict[str, int]:
    counts = arm_live(arm).get("v655_counts") or {}
    keys = (
        "service_notifier_180",
        "service_notifier_74",
        "cnss_daemon_netlink",
        "cnss_daemon_cld80211",
        "cnss_binder_transaction_failed",
        "binder_transaction_failed",
        "kernel_warning",
        "qmi_server_connected",
        "wlfw_start",
        "wlfw_service_request",
        "wlan_pd",
        "bdf_regdb",
        "bdf_bdwlan",
        "wlan_fw_ready",
        "wlan0",
    )
    return {key: int_value(counts.get(key)) for key in keys}


def markers_for(arm: dict[str, Any] | None) -> dict[str, int]:
    counts = ((arm_live(arm).get("markers") or {}).get("counts") or {})
    return {
        key: int_value(counts.get(key))
        for key in ("qrtr_rx", "qrtr_tx", "sysmon_qmi", "service_notifier", "kernel_warning", "wlfw", "bdf", "wlan0")
    }


def peripheral_for(arm: dict[str, Any] | None) -> dict[str, Any]:
    surface = arm_live(arm).get("v695_peripheral_manager_surface")
    return surface if isinstance(surface, dict) else {}


def query_for(arm: dict[str, Any] | None) -> dict[str, Any]:
    surface = arm_live(arm).get("v695_vndservice_query_surface")
    return surface if isinstance(surface, dict) else {}


def query_exact(surface: dict[str, Any]) -> bool:
    return any((phase or {}).get("vendor_qcom_peripheral_manager_seen") == "1" for phase in (surface.get("phases") or {}).values())


def query_ran(surface: dict[str, Any]) -> bool:
    return any((phase or {}).get("begin") == "1" for phase in (surface.get("phases") or {}).values())


def cnss_retry_started(surface: dict[str, Any]) -> bool:
    retry = surface.get("cnss_retry") or {}
    return bool(retry.get("retry_start_order"))


def wifi_advanced(counts: dict[str, int], markers: dict[str, int]) -> bool:
    return any(counts.get(key, 0) > 0 for key in (
        "qmi_server_connected",
        "wlfw_start",
        "wlfw_service_request",
        "wlan_pd",
        "bdf_regdb",
        "bdf_bdwlan",
        "wlan_fw_ready",
        "wlan0",
    )) or any(markers.get(key, 0) > 0 for key in ("wlfw", "bdf", "wlan0"))


def summarize_arm(arm: dict[str, Any] | None) -> dict[str, Any]:
    if not arm:
        return {}
    reboot = arm_live(arm).get("reboot_cleanup") or {}
    peripheral = peripheral_for(arm)
    query = query_for(arm)
    return {
        "decision": arm.get("decision", ""),
        "pass": arm.get("pass"),
        "reason": arm.get("reason", ""),
        "next_step": arm.get("next_step", ""),
        "manifest": arm.get("manifest", ""),
        "rc": arm.get("rc"),
        "ok": arm.get("ok"),
        "counts": counts_for(arm),
        "markers": markers_for(arm),
        "peripheral": peripheral,
        "vndservice_query": query,
        "query_ran": query_ran(query),
        "query_exact_match": query_exact(query),
        "cnss_retry_started": bool(arm_live(arm).get("v695_cnss_retry_started")) or cnss_retry_started(peripheral),
        "reboot_cleanup": {
            "version_seen": reboot.get("version_seen"),
            "status_healthy": reboot.get("status_healthy"),
            "wait_sec": reboot.get("wait_sec"),
        },
    }


def checks_for(prep: dict[str, Any] | None, arm: dict[str, Any] | None) -> list[dict[str, Any]]:
    counts = counts_for(arm)
    markers = markers_for(arm)
    peripheral = peripheral_for(arm)
    query = query_for(arm)
    return [
        {
            "name": "current-boot-prep-ready",
            "status": "pass" if prep and prep.get("ready") else "blocked",
            "detail": {"ready": bool(prep and prep.get("ready"))},
            "next_step": "restore V641/V401/V490 current-boot prerequisites",
        },
        {
            "name": "service74-gate-positive",
            "status": "pass" if counts["service_notifier_180"] > 0 and counts["service_notifier_74"] > 0 else "blocked",
            "detail": {key: counts[key] for key in ("service_notifier_180", "service_notifier_74")},
            "next_step": "do not evaluate provider retry until service74 is positive",
        },
        {
            "name": "peripheral-registration-seen",
            "status": "pass" if query_ran(query) and query_exact(query) else "blocked",
            "detail": query,
            "next_step": "repair provider registration/runtime before interpreting CNSS retry",
        },
        {
            "name": "cnss-retry-started-after-registration",
            "status": "pass" if cnss_retry_started(peripheral) else "blocked",
            "detail": (peripheral.get("cnss_retry") or {}),
            "next_step": "fix helper retry placement after confirmed provider registration",
        },
        {
            "name": "wlfw-bdf-wlan0-progression",
            "status": "pass" if wifi_advanced(counts, markers) else "finding",
            "detail": {"counts": counts, "markers": markers},
            "next_step": "if still absent, keep scan/connect blocked and classify pre-WLFW trigger",
        },
    ]


def decide(command: str, prep: dict[str, Any] | None, arm: dict[str, Any] | None) -> tuple[str, bool, str, str]:
    if command == "plan":
        return (
            "v695-provider-confirmed-cnss-retry-orchestrator-plan-ready",
            True,
            "plan-only; no device command executed",
            "deploy helper v118, then run V695 orchestrated provider-confirmed CNSS retry proof",
        )
    if not prep or not prep.get("ready"):
        return "v695-current-boot-prep-blocked", False, f"prep={prep}", "restore current-boot prerequisites before V695"
    if not arm or not arm.get("decision"):
        return "v695-arm-missing", False, "V695 arm did not produce a manifest", "inspect arm evidence"
    if "blocked" in str(arm.get("decision")):
        return "v695-arm-blocked", False, f"arm={summarize_arm(arm)}", "resolve V695 arm blocker before retry"
    query = query_for(arm)
    peripheral = peripheral_for(arm)
    counts = counts_for(arm)
    markers = markers_for(arm)
    if wifi_advanced(counts, markers):
        return (
            "v695-provider-confirmed-cnss-retry-wifi-surface-advanced",
            True,
            f"WLFW/BDF/wlan0 progression marker moved; counts={counts} markers={markers}",
            "classify wlan0 readiness before scan/connect or external ping",
        )
    if query_ran(query) and query_exact(query) and cnss_retry_started(peripheral):
        return (
            "v695-provider-confirmed-cnss-retry-gap-persists",
            True,
            f"provider registration confirmed and CNSS retry started; counts={counts} markers={markers}",
            "classify the remaining pre-WLFW trigger before Wi-Fi HAL/scan/connect",
        )
    if query_ran(query) and query_exact(query):
        return (
            "v695-provider-confirmed-cnss-retry-withheld",
            True,
            f"provider registration confirmed but retry absent; peripheral={peripheral}",
            "fix helper retry placement after provider query",
        )
    if query_ran(query):
        return (
            "v695-provider-registration-absent-before-retry",
            True,
            f"query={query}",
            "repair provider registration/runtime before retrying CNSS",
        )
    return "v695-vndservice-query-not-executed", False, f"arm={summarize_arm(arm)}", "fix helper query placement"


def build_manifest(args: argparse.Namespace, prep: dict[str, Any] | None, arm: dict[str, Any] | None) -> dict[str, Any]:
    decision, pass_ok, reason, next_step = decide(args.command, prep, arm)
    checks = [] if args.command == "plan" else checks_for(prep, arm)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "cycle": "v695",
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "helper_marker": args.helper_marker,
        "helper_sha256": args.helper_sha256,
        "allowed_live_actions": ALLOWED_LIVE_ACTIONS,
        "forbidden_actions": FORBIDDEN_ACTIONS,
        "prep_v695": prep or {},
        "arm_v695": summarize_arm(arm),
        "checks": checks,
        "device_commands_executed": args.command == "run",
        "device_mutations": args.command == "run",
        "daemon_start_executed": args.command == "run",
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "wifi_bringup_executed": False,
        "external_ping_executed": False,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    arm = manifest["arm_v695"]
    rows: list[list[str]] = []
    for surface_name in ("counts", "markers", "peripheral", "vndservice_query", "reboot_cleanup"):
        for key, value in (arm.get(surface_name) or {}).items():
            rows.append([surface_name, key, json.dumps(value, sort_keys=True) if isinstance(value, (dict, list)) else str(value)])
    check_rows = [
        [check["name"], check["status"], json.dumps(check["detail"], sort_keys=True), check["next_step"]]
        for check in manifest["checks"]
    ]
    return "\n".join([
        "# V695 Provider-confirmed CNSS Retry Orchestrator",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- helper_marker: `{manifest['helper_marker']}`",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- wifi_hal_start_executed: `{manifest['wifi_hal_start_executed']}`",
        f"- scan_connect_executed: `{manifest['scan_connect_executed']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        f"- external_ping_executed: `{manifest['external_ping_executed']}`",
        "",
        "## Checks",
        "",
        markdown_table(["check", "status", "detail", "next"], check_rows) if check_rows else "- plan only",
        "",
        "## Runtime Surface",
        "",
        markdown_table(["surface", "key", "value"], rows) if rows else "- no runtime surface captured",
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
        root = store.run_dir
        arm_root = root / "arm-v695-v118-provider-confirmed-cnss-retry"
        prep = v673.prep_current_boot(args, store, "v695", arm_root)
        if prep.get("ready"):
            arm = v673.run_arm(
                args,
                store,
                "v695",
                V695_SCRIPT,
                V695_APPROVAL,
                arm_root / "live",
                Path(str(prep["v490"]["manifest"])),
            )
    manifest = build_manifest(args, prep, arm)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"wifi_hal_start_executed: {manifest['wifi_hal_start_executed']}")
    print(f"scan_connect_executed: {manifest['scan_connect_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

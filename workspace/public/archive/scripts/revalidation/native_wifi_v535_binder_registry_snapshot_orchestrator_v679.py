#!/usr/bin/env python3
"""V679 current-boot orchestrator for the Binder registry snapshot proof."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path
from typing import Any

import native_wifi_same_helper_replay_v673 as v673
from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v679-v535-binder-registry-snapshot-orchestrated")
V679_APPROVAL = (
    "approve v679 V535 Binder registry snapshot Android userspace-order proof only; "
    "no supplicant, no scan/connect/link-up, no DHCP and no external ping"
)
V679_SCRIPT = "scripts/revalidation/native_wifi_v535_binder_registry_snapshot_v679.py"
HELPER_SHA256 = "a2c72c4157f6ddf089a40b2a5310288f3f0390ceced1f423519dcb8c1a8cc643"
HELPER_MARKER = "a90_android_execns_probe v112"

FORBIDDEN_ACTIONS = (
    "supplicant or hostapd start",
    "Wi-Fi scan/connect/link-up",
    "credential use",
    "DHCP, route change, or external ping",
    "boot image or partition write",
)
ALLOWED_LIVE_ACTIONS = (
    "V641 one-shot clean-DSP reboot",
    "V401 SELinuxfs mount surface",
    "V490 Android SELinux policy-load proof",
    "bounded V679 V535 Binder registry snapshot Android userspace-order proof",
    "runner-owned reboot cleanup",
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


def counts_for(arm: dict[str, Any] | None) -> dict[str, int]:
    live = (arm or {}).get("live") or {}
    counts = live.get("v655_counts") or {}
    keys = (
        "service_notifier_180",
        "service_notifier_74",
        "cnss_binder_transaction_failed",
        "binder_transaction_failed",
        "kernel_warning",
        "qmi_server_connected",
        "wlfw_start",
        "wlfw_service_request",
        "bdf_regdb",
        "bdf_bdwlan",
        "wlan_fw_ready",
        "wlan0",
    )
    return {key: int_value(counts.get(key)) for key in keys}


def markers_for(arm: dict[str, Any] | None) -> dict[str, int]:
    live = (arm or {}).get("live") or {}
    counts = ((live.get("markers") or {}).get("counts") or {})
    return {
        key: int_value(counts.get(key))
        for key in ("qrtr_rx", "qrtr_tx", "sysmon_qmi", "service_notifier", "kernel_warning", "wlfw", "bdf", "wlan0")
    }


def property_surface_for(arm: dict[str, Any] | None) -> dict[str, Any]:
    live = (arm or {}).get("live") or {}
    surface = live.get("v676_property_runtime_surface")
    return surface if isinstance(surface, dict) else {}


def registry_surface_for(arm: dict[str, Any] | None) -> dict[str, Any]:
    live = (arm or {}).get("live") or {}
    surface = live.get("v679_binder_registry_surface")
    return surface if isinstance(surface, dict) else {}


def android_children_started(arm: dict[str, Any] | None) -> bool:
    live = (arm or {}).get("live") or {}
    return bool(live.get("v671_android_userspace_children_started"))


def wifi_advanced(counts: dict[str, int], markers: dict[str, int]) -> bool:
    return any(counts.get(key, 0) > 0 for key in (
        "qmi_server_connected",
        "wlfw_start",
        "wlfw_service_request",
        "bdf_regdb",
        "bdf_bdwlan",
        "wlan_fw_ready",
        "wlan0",
    )) or any(markers.get(key, 0) > 0 for key in ("wlfw", "bdf", "wlan0"))


def summarize_arm(arm: dict[str, Any] | None) -> dict[str, Any]:
    if not arm:
        return {}
    reboot = (arm.get("live") or {}).get("reboot_cleanup") or {}
    registry = registry_surface_for(arm)
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
        "property_surface": property_surface_for(arm),
        "registry_surface": {
            "registry_enabled": registry.get("registry_enabled"),
            "after_retry_captured": registry.get("after_retry_captured"),
            "window_captured": registry.get("window_captured"),
            "failed_transaction_log_captured": registry.get("failed_transaction_log_captured"),
            "child_proc_captured_total": registry.get("child_proc_captured_total"),
        },
        "android_children_started": android_children_started(arm),
        "reboot_cleanup": {
            "version_seen": reboot.get("version_seen"),
            "status_healthy": reboot.get("status_healthy"),
            "wait_sec": reboot.get("wait_sec"),
        },
    }


def decide(command: str, prep: dict[str, Any] | None, arm: dict[str, Any] | None) -> tuple[str, bool, str, str]:
    if command == "plan":
        return (
            "v679-binder-registry-snapshot-orchestrator-plan-ready",
            True,
            "plan-only; no device command executed",
            "run V679 orchestrated live proof",
        )
    if not prep or not prep.get("ready"):
        return (
            "v679-current-boot-prep-blocked",
            False,
            f"prep={prep}",
            "restore V641/V401/V490 current-boot prerequisites",
        )
    if not arm or not arm.get("decision"):
        return (
            "v679-arm-missing",
            False,
            "V679 arm did not produce a manifest",
            "inspect V679 arm evidence",
        )
    if "blocked" in str(arm.get("decision")):
        return (
            "v679-arm-blocked",
            False,
            f"arm={summarize_arm(arm)}",
            "resolve V679 arm blockers before another live attempt",
        )

    counts = counts_for(arm)
    markers = markers_for(arm)
    property_surface = property_surface_for(arm)
    registry = registry_surface_for(arm)
    if wifi_advanced(counts, markers):
        return (
            "v679-wifi-surface-advanced",
            True,
            f"V679 advanced lower Wi-Fi markers; counts={counts} markers={markers} registry={registry}",
            "classify WLFW/BDF/wlan0 and plan first supplicant/scan gate only if wlan0 exists",
        )
    if (
        property_surface.get("property_denial_total") == 0
        and android_children_started(arm)
        and registry.get("after_retry_captured")
        and registry.get("window_captured")
    ):
        return (
            "v679-binder-registry-snapshot-captured",
            True,
            f"counts={counts} markers={markers} property_surface={property_surface} registry={registry}",
            "classify captured Binder debug/registry evidence before another runtime repair or Wi-Fi connect attempt",
        )
    return (
        "v679-review-required",
        False,
        f"arm={summarize_arm(arm)}",
        "inspect V679 helper transcript",
    )


def build_manifest(args: argparse.Namespace, prep: dict[str, Any] | None, arm: dict[str, Any] | None) -> dict[str, Any]:
    decision, pass_ok, reason, next_step = decide(args.command, prep, arm)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "cycle": "v679",
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "helper_marker": args.helper_marker,
        "helper_sha256": args.helper_sha256,
        "allowed_live_actions": ALLOWED_LIVE_ACTIONS,
        "forbidden_actions": FORBIDDEN_ACTIONS,
        "prep_v679": prep or {},
        "arm_v679": summarize_arm(arm),
        "device_commands_executed": args.command == "run",
        "device_mutations": args.command == "run",
        "daemon_start_executed": args.command == "run",
        "wifi_hal_start_executed": bool(args.command == "run" and android_children_started(arm)),
        "scan_connect_executed": False,
        "wifi_bringup_executed": False,
        "external_ping_executed": False,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    arm = manifest["arm_v679"]
    rows: list[list[str]] = []
    for surface_name in ("counts", "markers", "property_surface", "registry_surface"):
        for key, value in (arm.get(surface_name) or {}).items():
            rows.append([surface_name, key, json.dumps(value, sort_keys=True) if isinstance(value, (dict, list)) else str(value)])
    return "\n".join([
        "# V679 V535 Binder Registry Snapshot Orchestrator",
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
        "## Arm",
        "",
        markdown_table(
            ["arm", "decision", "pass", "manifest"],
            [["v679", str(arm.get("decision", "")), str(arm.get("pass", "")), str(arm.get("manifest", ""))]],
        ),
        "",
        "## Runtime Surface",
        "",
        markdown_table(["surface", "key", "value"], rows) if rows else "- no runtime surface captured",
        "",
        "## Guardrails",
        "",
        "- Supplicant, scan/connect, DHCP, route change, credentials, and external ping remain blocked.",
        "- The live arm uses bounded cleanup and reboot verification.",
    ])


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    prep: dict[str, Any] | None = None
    arm: dict[str, Any] | None = None
    if args.command == "run":
        root = store.run_dir
        arm_root = root / "arm-v679-v535-registry"
        prep = v673.prep_current_boot(args, store, "v679", arm_root)
        if prep.get("ready"):
            arm = v673.run_arm(
                args,
                store,
                "v679",
                V679_SCRIPT,
                V679_APPROVAL,
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

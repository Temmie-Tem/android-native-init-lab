#!/usr/bin/env python3
"""V682 bounded cnss2/WLFW progression observer.

This runner reuses the current helper v112 V679 live arm, but routes the
result around cnss2/WLFW progression instead of Binder debugfs. It does not
start supplicant or hostapd, scan/connect, use credentials, run DHCP, change
routes, or ping externally.
"""

from __future__ import annotations

import argparse
import datetime as dt
from pathlib import Path
from typing import Any

import native_wifi_v535_binder_registry_snapshot_orchestrator_v679 as v679
from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v682-cnss2-wlfw-progression-observer")
V682_APPROVAL = (
    "approve v682 cnss2/WLFW progression observer only; "
    "no supplicant, no scan/connect/link-up, no DHCP and no external ping"
)

ALLOWED_LIVE_ACTIONS = (
    "V641 one-shot clean-DSP reboot",
    "V401 SELinuxfs mount surface",
    "V490 Android SELinux policy-load proof",
    "bounded helper v112 Android userspace-order start-only proof",
    "read-only cnss2/icnss/QCA6390 focused captures",
    "WLFW QRTR nameservice readback without QMI payload",
    "runner-owned reboot cleanup",
)
FORBIDDEN_ACTIONS = (
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
    parser.add_argument("--host", "--bridge-host", dest="host", default=v679.v673.DEFAULT_HOST)
    parser.add_argument("--port", "--bridge-port", dest="port", type=int, default=v679.v673.DEFAULT_PORT)
    parser.add_argument("--expect-version", default=v679.v673.DEFAULT_EXPECT_VERSION)
    parser.add_argument("--helper", default=v679.v673.DEFAULT_HELPER)
    parser.add_argument("--helper-sha256", default=v679.HELPER_SHA256)
    parser.add_argument("--helper-marker", default=v679.HELPER_MARKER)
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
    live = (arm or {}).get("live") or {}
    counts = ((live.get("markers") or {}).get("counts") or {})
    return {
        key: int_value(counts.get(key))
        for key in ("qrtr_rx", "qrtr_tx", "sysmon_qmi", "service_notifier", "kernel_warning", "wlfw", "bdf", "wlan0")
    }


def focus_for(arm: dict[str, Any] | None) -> dict[str, Any]:
    live = (arm or {}).get("live") or {}
    surface = live.get("v668_cnss2_focus_surface")
    return surface if isinstance(surface, dict) else {}


def registry_for(arm: dict[str, Any] | None) -> dict[str, Any]:
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
        "wlan_pd",
        "bdf_regdb",
        "bdf_bdwlan",
        "wlan_fw_ready",
        "wlan0",
    )) or any(markers.get(key, 0) > 0 for key in ("wlfw", "bdf", "wlan0"))


def focus_ready(focus: dict[str, Any]) -> bool:
    window = focus.get("window") or {}
    service74 = focus.get("service74_open") or {}
    return (
        service74.get("icnss_device_captured") == "1"
        and service74.get("qca6390_device_captured") == "1"
        and window.get("icnss_device_captured") == "1"
        and window.get("qca6390_device_captured") == "1"
    )


def summarize_arm(arm: dict[str, Any] | None) -> dict[str, Any]:
    if not arm:
        return {}
    reboot = ((arm.get("live") or {}).get("reboot_cleanup") or {})
    registry = registry_for(arm)
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
        "focus_ready": focus_ready(focus_for(arm)),
        "android_children_started": android_children_started(arm),
        "registry": {
            "after_retry_captured": registry.get("after_retry_captured"),
            "window_captured": registry.get("window_captured"),
            "failed_transaction_log_captured": registry.get("failed_transaction_log_captured"),
        },
        "reboot_cleanup": {
            "version_seen": reboot.get("version_seen"),
            "status_healthy": reboot.get("status_healthy"),
            "wait_sec": reboot.get("wait_sec"),
        },
    }


def checks_for(prep: dict[str, Any] | None, arm: dict[str, Any] | None) -> list[dict[str, Any]]:
    counts = counts_for(arm)
    markers = markers_for(arm)
    focus = focus_for(arm)
    registry = registry_for(arm)
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
            "next_step": "do not evaluate WLFW progression until service74 is positive",
        },
        {
            "name": "cnss-retry-observed",
            "status": "pass" if counts["cnss_daemon_netlink"] > 0 and counts["cnss_daemon_cld80211"] > 0 else "blocked",
            "detail": {key: counts[key] for key in ("cnss_daemon_netlink", "cnss_daemon_cld80211")},
            "next_step": "repair CNSS retry observation before WLFW routing",
        },
        {
            "name": "focused-cnss2-sysfs-captured",
            "status": "pass" if focus_ready(focus) else "blocked",
            "detail": focus,
            "next_step": "refresh helper focused capture before drawing cnss2 conclusions",
        },
        {
            "name": "android-userspace-start-only-reached",
            "status": "pass" if android_children_started(arm) else "review",
            "detail": {"android_children_started": android_children_started(arm)},
            "next_step": "inspect helper transcript if Android userspace children were withheld",
        },
        {
            "name": "wlfw-bdf-wlan0-progression",
            "status": "pass" if wifi_advanced(counts, markers) else "finding",
            "detail": {
                "counts": counts,
                "markers": markers,
                "registry_after_retry": registry.get("after_retry_captured"),
                "registry_window": registry.get("window_captured"),
            },
            "next_step": "if still absent, classify the missing cnss2/QMI trigger before scan/connect",
        },
    ]


def decide(command: str, prep: dict[str, Any] | None, arm: dict[str, Any] | None) -> tuple[str, bool, str, str]:
    if command == "plan":
        return (
            "v682-cnss2-wlfw-observer-plan-ready",
            True,
            "plan-only; no device command executed",
            "run V682 bounded live observer with helper v112",
        )
    if not prep or not prep.get("ready"):
        return "v682-current-boot-prep-blocked", False, f"prep={prep}", "restore current-boot prerequisites before V682"
    if not arm or not arm.get("decision"):
        return "v682-arm-missing", False, "V682 arm did not produce a manifest", "inspect arm evidence"
    if "blocked" in str(arm.get("decision")):
        return "v682-arm-blocked", False, f"arm={summarize_arm(arm)}", "resolve live arm blocker before retry"
    counts = counts_for(arm)
    markers = markers_for(arm)
    if wifi_advanced(counts, markers):
        return (
            "v682-cnss2-wlfw-progressed",
            True,
            f"WLFW/BDF/wlan0 progression marker moved; counts={counts} markers={markers}",
            "classify wlan0 readiness before any scan/connect or external ping",
        )
    if counts["service_notifier_74"] > 0 and counts["cnss_daemon_netlink"] > 0 and focus_ready(focus_for(arm)):
        return (
            "v682-cnss2-wlfw-gap-confirmed",
            True,
            f"service74/CNSS/focused sysfs observed, but WLFW/BDF/wlan0 remain absent; counts={counts} markers={markers}",
            "plan V683 to isolate the missing cnss2/QMI trigger before Binder debugfs or scan/connect",
        )
    return (
        "v682-cnss2-wlfw-observer-review",
        False,
        f"arm={summarize_arm(arm)}",
        "inspect V682 helper transcript",
    )


def build_manifest(args: argparse.Namespace, prep: dict[str, Any] | None, arm: dict[str, Any] | None) -> dict[str, Any]:
    decision, pass_ok, reason, next_step = decide(args.command, prep, arm)
    checks = [] if args.command == "plan" else checks_for(prep, arm)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "cycle": "v682",
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "helper_marker": args.helper_marker,
        "helper_sha256": args.helper_sha256,
        "allowed_live_actions": ALLOWED_LIVE_ACTIONS,
        "forbidden_actions": FORBIDDEN_ACTIONS,
        "prep_v682": prep or {},
        "arm_v682": summarize_arm(arm),
        "checks": checks,
        "device_commands_executed": args.command == "run",
        "device_mutations": args.command == "run",
        "daemon_start_executed": args.command == "run",
        "wifi_hal_start_executed": bool(args.command == "run" and android_children_started(arm)),
        "scan_connect_executed": False,
        "wifi_bringup_executed": False,
        "external_ping_executed": False,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    arm = manifest["arm_v682"]
    rows: list[list[str]] = []
    for surface_name in ("counts", "markers", "registry", "reboot_cleanup"):
        for key, value in (arm.get(surface_name) or {}).items():
            rows.append([surface_name, key, str(value)])
    check_rows = [
        [check["name"], check["status"], str(check["detail"]), check["next_step"]]
        for check in manifest["checks"]
    ]
    return "\n".join([
        "# V682 cnss2/WLFW Progression Observer",
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
        markdown_table(["check", "status", "detail", "next"], check_rows),
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
        arm_root = root / "arm-v679-v112-observer"
        prep = v679.v673.prep_current_boot(args, store, "v682", arm_root)
        if prep.get("ready"):
            arm = v679.v673.run_arm(
                args,
                store,
                "v682",
                v679.V679_SCRIPT,
                v679.V679_APPROVAL,
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

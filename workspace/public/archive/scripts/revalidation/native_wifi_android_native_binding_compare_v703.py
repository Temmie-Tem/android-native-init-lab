#!/usr/bin/env python3
"""V703 Android-vs-native ICNSS/QCA/WLFW binding reference classifier.

This classifier is host-only. It consumes existing Android baseline evidence
and V702 native focus evidence to decide whether the next work should target
QCA6390 bind/unbind or the ICNSS/WLFW readiness edge. It does not contact the
device, start daemons, scan/connect, use credentials, run DHCP, change routes,
or ping externally.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v703-android-native-binding-compare")
DEFAULT_V702_MANIFEST = Path("tmp/wifi/v702-cnss2-focus-surface-classifier/manifest.json")
DEFAULT_ANDROID_SUMMARY = Path("tmp/wifi/v204-android-baseline/summary.md")
DEFAULT_ANDROID_SYSFS = Path("tmp/wifi/v204-android-baseline/root-icnss-sysfs-files.txt")
DEFAULT_ANDROID_DMESG = Path("tmp/wifi/v204-android-baseline/root-dmesg-wifi-tail.txt")

FORBIDDEN_ACTIONS = (
    "device command",
    "mount or bind mount",
    "daemon start",
    "service-manager start",
    "Wi-Fi HAL start",
    "supplicant or hostapd start",
    "scan/connect/link-up",
    "credential/DHCP/routing/external ping",
    "sysfs or debugfs write",
    "boot image or partition write",
)

DMESG_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("cnss_daemon_netlink", re.compile(r"netlink_create.*comm:\s*cnss-daemon", re.I)),
    ("cnss_daemon_wlfw_start", re.compile(r"cnss-daemon\s+wlfw_start|wlfw_start:\s*Starting", re.I)),
    ("wlfw_service_request", re.compile(r"wlfw_service_request", re.I)),
    ("service_notifier_wlan_pd", re.compile(r"service-notifier:.*wlan_pd|instance\s+180", re.I)),
    ("icnss_qmi_connected", re.compile(r"icnss_qmi:\s*QMI Server Connected", re.I)),
    ("bdf_regdb", re.compile(r"BDF file\s*:\s*regdb\.bin|regdb\.bin", re.I)),
    ("bdf_bdwlan", re.compile(r"BDF file\s*:\s*bdwlan\.bin|bdwlan\.bin", re.I)),
    ("wlan_fw_ready", re.compile(r"WLAN FW is ready|FW ready event received", re.I)),
    ("wlan_netdev", re.compile(r"\bwlan0\b", re.I)),
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v702-manifest", type=Path, default=DEFAULT_V702_MANIFEST)
    parser.add_argument("--android-summary", type=Path, default=DEFAULT_ANDROID_SUMMARY)
    parser.add_argument("--android-sysfs", type=Path, default=DEFAULT_ANDROID_SYSFS)
    parser.add_argument("--android-dmesg", type=Path, default=DEFAULT_ANDROID_DMESG)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def read_text(path: Path) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    return resolved.read_bytes().replace(b"\0", b"\n").decode("utf-8", errors="replace")


def load_json(path: Path) -> dict[str, Any]:
    text = read_text(path)
    return json.loads(text) if text else {}


def boolish(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "pass", "ready"}


def count_markers(text: str) -> dict[str, Any]:
    counts = {name: 0 for name, _ in DMESG_PATTERNS}
    first_lines = {name: "missing" for name, _ in DMESG_PATTERNS}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        for name, pattern in DMESG_PATTERNS:
            if pattern.search(line):
                counts[name] += 1
                if first_lines[name] == "missing":
                    first_lines[name] = line
    return {"counts": counts, "first_lines": first_lines}


def parse_android_surface(summary: str, sysfs: str, dmesg: str) -> dict[str, Any]:
    sysfs_lines = [line.strip() for line in sysfs.splitlines() if line.strip()]
    markers = count_markers(dmesg)
    netdevs = tuple(name for name in ("wlan0", "swlan0", "p2p0", "wifi-aware0") if f"/net/{name}/" in sysfs)
    return {
        "summary_decision_ready": "decision: `ready-for-readonly-nl80211-probe-plan`" in summary,
        "interface_driver_icnss": "Driver icnss" in summary,
        "icnss_sysfs_lines": len(sysfs_lines),
        "icnss_phy0_visible": "/ieee80211/phy0/" in sysfs,
        "icnss_wlan_netdevs": list(netdevs),
        "wlan0_under_icnss": "/sys/devices/platform/soc/18800000.qcom,icnss/net/wlan0/" in sysfs,
        "rfkill_under_icnss": "/sys/devices/platform/soc/18800000.qcom,icnss/ieee80211/phy0/rfkill" in sysfs,
        "qca6390_driver_reference": (
            "present" if "/a0000000.qcom,cnss-qca6390/driver" in sysfs else "not-captured"
        ),
        "dmesg": markers,
        "wlfw_progression_positive": all(
            markers["counts"].get(name, 0) > 0
            for name in ("cnss_daemon_wlfw_start", "icnss_qmi_connected", "bdf_bdwlan", "wlan_fw_ready")
        ),
    }


def parse_native_surface(v702: dict[str, Any]) -> dict[str, Any]:
    surface = v702.get("surface") if isinstance(v702.get("surface"), dict) else {}
    classification = surface.get("classification") if isinstance(surface.get("classification"), dict) else {}
    dirs = surface.get("dirs") if isinstance(surface.get("dirs"), dict) else {}
    qca_dir = dirs.get("wifi_cnss2_focus_qca6390_device") if isinstance(dirs.get("wifi_cnss2_focus_qca6390_device"), dict) else {}
    net_dir = dirs.get("wifi_cnss2_focus_net_class") if isinstance(dirs.get("wifi_cnss2_focus_net_class"), dict) else {}
    return {
        "v702_decision": v702.get("decision", ""),
        "v702_pass": boolish(v702.get("pass")),
        "icnss_driver_bound": boolish(classification.get("icnss_driver_bound")),
        "qca6390_device_visible": boolish(classification.get("qca6390_device_visible")),
        "qca6390_driver_symlink_visible": boolish(classification.get("qca6390_driver_symlink_visible")),
        "net_class_has_wlan0": boolish(classification.get("net_class_has_wlan0")),
        "debug_icnss_open_error": classification.get("debug_icnss_open_error", ""),
        "wlan0_open_error": classification.get("wlan0_open_error", ""),
        "wlfw_marker": int(classification.get("wlfw_marker") or 0),
        "bdf_marker": int(classification.get("bdf_marker") or 0),
        "wlan0_marker": int(classification.get("wlan0_marker") or 0),
        "dmesg_has_icnss_qmi": boolish(classification.get("dmesg_has_icnss_qmi")),
        "dmesg_has_wlfw": boolish(classification.get("dmesg_has_wlfw")),
        "qca6390_entries": qca_dir.get("entries") or [],
        "native_net_entries": net_dir.get("entries") or [],
    }


def build_checks(android: dict[str, Any], native: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "name": "v702-native-input-ready",
            "status": "pass" if native["v702_pass"] and native["v702_decision"] == "v702-qca6390-platform-binding-gap-classified" else "blocked",
            "detail": {"decision": native["v702_decision"], "pass": native["v702_pass"]},
            "next_step": "refresh V702 focus classifier before comparing Android/native surfaces",
        },
        {
            "name": "android-icnss-netdev-reference-ready",
            "status": "finding" if android["wlan0_under_icnss"] and android["interface_driver_icnss"] else "blocked",
            "detail": {
                "wlan0_under_icnss": android["wlan0_under_icnss"],
                "icnss_wlan_netdevs": android["icnss_wlan_netdevs"],
                "interface_driver_icnss": android["interface_driver_icnss"],
            },
            "next_step": "collect a fresh Android baseline only if this reference disappears",
        },
        {
            "name": "android-wlfw-progression-reference-ready",
            "status": "finding" if android["wlfw_progression_positive"] else "blocked",
            "detail": android["dmesg"]["counts"],
            "next_step": "collect fresh Android dmesg if WLFW/BDF/fw_ready markers are missing",
        },
        {
            "name": "native-icnss-bound-qca-node-visible",
            "status": "finding" if native["icnss_driver_bound"] and native["qca6390_device_visible"] else "blocked",
            "detail": {
                "icnss_driver_bound": native["icnss_driver_bound"],
                "qca6390_device_visible": native["qca6390_device_visible"],
                "qca6390_entries": native["qca6390_entries"],
            },
            "next_step": "do not target generic platform discovery; the relevant nodes already exist",
        },
        {
            "name": "native-wlfw-netdev-missing",
            "status": "finding" if (
                not native["net_class_has_wlan0"]
                and native["wlfw_marker"] == 0
                and native["bdf_marker"] == 0
                and native["wlan0_marker"] == 0
                and not native["dmesg_has_icnss_qmi"]
            ) else "review",
            "detail": {
                "net_class_has_wlan0": native["net_class_has_wlan0"],
                "native_net_entries": native["native_net_entries"],
                "wlfw_marker": native["wlfw_marker"],
                "bdf_marker": native["bdf_marker"],
                "wlan0_marker": native["wlan0_marker"],
                "dmesg_has_icnss_qmi": native["dmesg_has_icnss_qmi"],
            },
            "next_step": "next live gate should observe/trigger ICNSS QMI/WLFW readiness before any Wi-Fi HAL connect",
        },
        {
            "name": "qca6390-driver-link-not-next-target",
            "status": "finding" if (
                native["qca6390_device_visible"]
                and not native["qca6390_driver_symlink_visible"]
                and android["wlan0_under_icnss"]
            ) else "review",
            "detail": {
                "native_qca_driver_symlink_visible": native["qca6390_driver_symlink_visible"],
                "android_qca_driver_reference": android["qca6390_driver_reference"],
                "android_success_netdev_path": "/sys/devices/platform/soc/18800000.qcom,icnss/net/wlan0",
            },
            "next_step": "avoid bind/unbind writes; compare ICNSS/WLFW readiness edge instead",
        },
    ]


def decide(command: str, checks: list[dict[str, Any]]) -> tuple[str, bool, str, str]:
    if command == "plan":
        return (
            "v703-android-native-binding-compare-plan-ready",
            True,
            "plan-only; no device command executed",
            "run V703 host-only classifier over Android baseline and V702 native focus evidence",
        )
    blocked = [check["name"] for check in checks if check["status"] == "blocked"]
    if blocked:
        return (
            "v703-android-native-binding-reference-incomplete",
            False,
            "blocked by " + ", ".join(blocked),
            "refresh missing Android or V702 evidence before changing live behavior",
        )
    findings = {check["name"] for check in checks if check["status"] == "finding"}
    required = {
        "android-icnss-netdev-reference-ready",
        "android-wlfw-progression-reference-ready",
        "native-icnss-bound-qca-node-visible",
        "native-wlfw-netdev-missing",
        "qca6390-driver-link-not-next-target",
    }
    if required <= findings:
        return (
            "v703-android-icnss-wlfw-delta-classified",
            True,
            "Android reaches WLAN netdevs under ICNSS plus WLFW/BDF/fw_ready, while native has ICNSS bound and QCA6390 visible but no ICNSS-QMI/WLFW/BDF/wlan0 progression. QCA6390 child driver-link absence is not enough to justify bind/unbind writes.",
            "plan the next live gate around ICNSS QMI/WLFW readiness progression and keep bind/unbind, Wi-Fi HAL connect, credentials, DHCP, and external ping blocked until wlan0 exists",
        )
    return (
        "v703-android-native-binding-manual-review",
        False,
        "Android/native binding evidence did not match a known safe next target",
        "inspect Android baseline and V702 focus evidence manually",
    )


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    v702 = load_json(args.v702_manifest)
    android = parse_android_surface(
        read_text(args.android_summary),
        read_text(args.android_sysfs),
        read_text(args.android_dmesg),
    )
    native = parse_native_surface(v702)
    checks = [] if args.command == "plan" else build_checks(android, native)
    decision, pass_ok, reason, next_step = decide(args.command, checks)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "cycle": "v703",
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "inputs": {
            "v702_manifest": str(repo_path(args.v702_manifest)),
            "android_summary": str(repo_path(args.android_summary)),
            "android_sysfs": str(repo_path(args.android_sysfs)),
            "android_dmesg": str(repo_path(args.android_dmesg)),
        },
        "android_surface": android,
        "native_surface": native,
        "checks": checks,
        "forbidden_actions": FORBIDDEN_ACTIONS,
        "device_commands_executed": False,
        "device_mutations": False,
        "daemon_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "wifi_bringup_executed": False,
        "external_ping_executed": False,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    check_rows = [
        [check["name"], check["status"], json.dumps(check["detail"], sort_keys=True), check["next_step"]]
        for check in manifest["checks"]
    ]
    android_rows = [[key, json.dumps(value, sort_keys=True)] for key, value in sorted(manifest["android_surface"].items())]
    native_rows = [[key, json.dumps(value, sort_keys=True)] for key, value in sorted(manifest["native_surface"].items())]
    return "\n".join([
        "# V703 Android-vs-Native Binding Compare",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
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
        "## Android Surface",
        "",
        markdown_table(["key", "value"], android_rows),
        "",
        "## Native Surface",
        "",
        markdown_table(["key", "value"], native_rows),
        "",
        "## Guardrails",
        "",
        "\n".join(f"- {item}" for item in manifest["forbidden_actions"]),
        "",
    ])


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args)
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

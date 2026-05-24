#!/usr/bin/env python3
"""V721 host-only Android-vs-native SERVREG/CNSS2 delta classifier.

This classifier compares the Android V622 lower Wi-Fi timeline against the
native V720 same-window service-positive evidence. It does not contact the
device, start daemons, start Wi-Fi HAL, scan/connect, use credentials, run
DHCP, change routes, ping externally, write sysfs, or write boot partitions.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v721-servreg-cnss2-delta")
DEFAULT_ANDROID_V622_MANIFEST = Path(
    "tmp/wifi/v622-android-mdm-helper-timing-handoff-live-20260523-032506/"
    "v622-android-mdm-helper-timing-recapture-run/manifest.json"
)
DEFAULT_NATIVE_V720_SOURCE = Path("tmp/wifi/latest-v720-same-window-cnss2-observer.txt")

FORBIDDEN_ACTIONS = (
    "device command",
    "daemon start",
    "service-manager start",
    "Wi-Fi HAL, wificond, supplicant, or hostapd start",
    "scan/connect/link-up",
    "credential use",
    "DHCP, route change, or external ping",
    "sysfs/debugfs write",
    "esoc0 open/hold",
    "boot image or partition write",
)

TIMELINE_MARKERS = (
    "qrtr_rx",
    "qrtr_tx",
    "sysmon_modem",
    "sysmon_qmi",
    "sysmon_esoc0",
    "service_locator",
    "service_state_up",
    "service_notifier_180",
    "service_notifier_74",
    "wlfw_start",
    "wlan_pd",
    "wlan_pd_ack_180",
    "qmi_server_connected",
    "icnss_qmi",
    "bdf_regdb",
    "bdf_bdwlan",
    "bdf",
    "wlan_fw_ready",
    "wlan0",
    "cnss_diag_netlink",
    "cnss_daemon_netlink",
    "cnss_daemon_cld80211",
    "pd_notifier",
    "qca6390_power",
    "qca6390_mhi_pcie",
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--android-v622-manifest", type=Path, default=DEFAULT_ANDROID_V622_MANIFEST)
    parser.add_argument("--native-v720-source", type=Path, default=DEFAULT_NATIVE_V720_SOURCE)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def read_text(path: Path) -> str:
    resolved = repo_path(path)
    return resolved.read_bytes().replace(b"\0", b"\n").decode("utf-8", errors="replace") if resolved.exists() else ""


def load_json(path: Path) -> dict[str, Any]:
    text = read_text(path)
    if not text:
        return {}
    data = json.loads(text)
    return data if isinstance(data, dict) else {}


def intish(value: object) -> int:
    if isinstance(value, bool):
        return int(value)
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def boolish(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "pass", "ready"}


def resolve_source(source: Path) -> Path:
    resolved = repo_path(source)
    if resolved.is_file() and resolved.name != "manifest.json":
        text = resolved.read_text(encoding="utf-8").strip()
        if text:
            return repo_path(Path(text))
    return resolved


def resolve_v720_manifests(source: Path) -> tuple[Path, Path, Path]:
    target = resolve_source(source)
    if target.is_dir():
        root = target
        top = root / "manifest.json"
    elif target.name == "manifest.json":
        top = target
        root = target.parent
    else:
        root = target.parent
        top = target
    reconcile = root / "reconcile-v719" / "manifest.json"
    return root, top, reconcile


def marker_count(counts: dict[str, Any], *names: str) -> int:
    return sum(intish(counts.get(name)) for name in names)


def first_ts(first: dict[str, Any], marker: str) -> float | None:
    value = first.get(marker)
    if isinstance(value, dict):
        value = value.get("timestamp")
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def delta_ms(first: dict[str, Any], newer: str, older: str) -> float | None:
    newer_ts = first_ts(first, newer)
    older_ts = first_ts(first, older)
    if newer_ts is None or older_ts is None:
        return None
    return round((newer_ts - older_ts) * 1000.0, 3)


def first_line(first: dict[str, Any], marker: str) -> str:
    value = first.get(marker)
    if isinstance(value, dict):
        return str(value.get("line", "missing"))
    return str(value or "missing")


def android_surface(path: Path) -> dict[str, Any]:
    manifest = load_json(path)
    summary = manifest.get("android_summary") if isinstance(manifest.get("android_summary"), dict) else {}
    counts = summary.get("counts") if isinstance(summary.get("counts"), dict) else {}
    first = summary.get("first") if isinstance(summary.get("first"), dict) else {}
    return {
        "manifest": str(repo_path(path)),
        "exists": bool(manifest),
        "decision": manifest.get("decision", ""),
        "pass": boolish(manifest.get("pass")),
        "counts": {name: intish(counts.get(name)) for name in TIMELINE_MARKERS},
        "deltas_ms": {
            "service_locator_to_180": delta_ms(first, "service_notifier_180", "service_locator"),
            "service_180_to_74": delta_ms(first, "service_notifier_74", "service_notifier_180"),
            "service_180_to_wlfw_start": delta_ms(first, "wlfw_start", "service_notifier_180"),
            "service_180_to_wlan_pd": delta_ms(first, "wlan_pd", "service_notifier_180"),
            "wlan_pd_to_qmi": delta_ms(first, "qmi_server_connected", "wlan_pd"),
            "wlan_pd_to_bdf_regdb": delta_ms(first, "bdf_regdb", "wlan_pd"),
            "wlan_pd_to_fw_ready": delta_ms(first, "wlan_fw_ready", "wlan_pd"),
        },
        "first_lines": {name: first_line(first, name) for name in TIMELINE_MARKERS if first_line(first, name) != "missing"},
        "has_service_pair": marker_count(counts, "service_notifier_180") > 0 and marker_count(counts, "service_notifier_74") > 0,
        "has_servreg_wlan_pd": marker_count(counts, "wlan_pd", "wlan_pd_ack_180") > 0,
        "has_wlfw_qmi": marker_count(counts, "wlfw_start", "qmi_server_connected") > 0,
        "has_wlan_ready": marker_count(counts, "bdf_regdb", "bdf_bdwlan", "wlan_fw_ready", "wlan0") > 0,
    }


def native_surface(source: Path) -> dict[str, Any]:
    root, top_path, reconcile_path = resolve_v720_manifests(source)
    top = load_json(top_path)
    reconcile = load_json(reconcile_path)
    service = reconcile.get("service_positive") if isinstance(reconcile.get("service_positive"), dict) else {}
    current = reconcile.get("current_boot") if isinstance(reconcile.get("current_boot"), dict) else {}
    dmesg = service.get("dmesg") if isinstance(service.get("dmesg"), dict) else {}
    counts = dmesg.get("counts") if isinstance(dmesg.get("counts"), dict) else {}
    first = dmesg.get("first_ts") if isinstance(dmesg.get("first_ts"), dict) else {}
    lines = dmesg.get("first_lines") if isinstance(dmesg.get("first_lines"), dict) else {}
    qmi_count = marker_count(counts, "icnss_qmi")
    bdf_count = marker_count(counts, "bdf")
    return {
        "root": str(root),
        "top_manifest": str(top_path),
        "reconcile_manifest": str(reconcile_path),
        "exists": bool(top) and bool(reconcile),
        "top_decision": top.get("decision", ""),
        "top_pass": boolish(top.get("pass")),
        "reconcile_decision": reconcile.get("decision", ""),
        "reconcile_pass": boolish(reconcile.get("pass")),
        "counts": {name: intish(counts.get(name)) for name in TIMELINE_MARKERS} | {
            "qmi_server_connected": qmi_count,
            "bdf_regdb": bdf_count,
            "bdf_bdwlan": bdf_count,
        },
        "deltas_ms": {
            "service_locator_to_180": delta_ms(first, "service_notifier_180", "service_locator"),
            "service_180_to_74": delta_ms(first, "service_notifier_74", "service_notifier_180"),
            "service_180_to_cnss_daemon": delta_ms(first, "cnss_daemon_netlink", "service_notifier_180"),
        },
        "first_lines": {name: str(lines.get(name)) for name in TIMELINE_MARKERS if lines.get(name)},
        "qrtr_ns_observable": boolish(service.get("qrtr_ns_observable")),
        "qrtr_ns_postflight_safe": boolish(service.get("qrtr_ns_postflight_safe")),
        "service74_gate_status": str(service.get("service74_gate_status", "")),
        "kernel_progression": boolish(service.get("kernel_progression")),
        "wlfw_or_wlan0": boolish(service.get("wlfw_or_wlan0")),
        "current_decision": current.get("decision", ""),
        "current_mss_state": current.get("mss_state", ""),
        "current_mdm3_state": current.get("mdm3_state", ""),
        "current_capture_clean": boolish(current.get("capture_clean")),
        "has_service_pair": marker_count(counts, "service_notifier_180") > 0 and marker_count(counts, "service_notifier_74") > 0,
        "has_servreg_wlan_pd": marker_count(counts, "service_state_up", "wlan_pd") > 0,
        "has_wlfw_qmi": qmi_count > 0 or marker_count(counts, "wlfw") > 0,
        "has_wlan_ready": bdf_count > 0 or marker_count(counts, "wlan_fw_ready", "wlan0") > 0,
    }


def build_checks(android: dict[str, Any], native: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "name": "input-evidence-ready",
            "status": "pass" if android["exists"] and native["exists"] and android["pass"] and native["top_pass"] and native["reconcile_pass"] else "blocked",
            "detail": {
                "android": android["decision"],
                "native_top": native["top_decision"],
                "native_reconcile": native["reconcile_decision"],
            },
            "next_step": "refresh Android V622 or native V720 evidence before routing V721",
        },
        {
            "name": "shared-lower-qmi-publication",
            "status": "pass" if android["has_service_pair"] and native["has_service_pair"] else "blocked",
            "detail": {
                "android_180": android["counts"].get("service_notifier_180", 0),
                "android_74": android["counts"].get("service_notifier_74", 0),
                "native_180": native["counts"].get("service_notifier_180", 0),
                "native_74": native["counts"].get("service_notifier_74", 0),
            },
            "next_step": "do not re-debug QRTR service 180/74 publication unless this regresses",
        },
        {
            "name": "qrtr-ns-not-current-blocker",
            "status": "pass" if native["qrtr_ns_observable"] and native["qrtr_ns_postflight_safe"] else "finding",
            "detail": {
                "observable": native["qrtr_ns_observable"],
                "postflight_safe": native["qrtr_ns_postflight_safe"],
                "service74_gate_status": native["service74_gate_status"],
            },
            "next_step": "if false, repair qrtr-ns before CNSS2/SERVREG analysis",
        },
        {
            "name": "android-servreg-wlanpd-continuation",
            "status": "finding" if android["has_servreg_wlan_pd"] and android["has_wlfw_qmi"] and android["has_wlan_ready"] else "blocked",
            "detail": {
                "wlan_pd": android["counts"].get("wlan_pd", 0),
                "wlan_pd_ack_180": android["counts"].get("wlan_pd_ack_180", 0),
                "wlfw_start": android["counts"].get("wlfw_start", 0),
                "qmi_server_connected": android["counts"].get("qmi_server_connected", 0),
                "wlan_fw_ready": android["counts"].get("wlan_fw_ready", 0),
                "wlan0": android["counts"].get("wlan0", 0),
            },
            "next_step": "Android reference is strong enough to compare the missing native continuation",
        },
        {
            "name": "native-servreg-wlanpd-cnss2-gap",
            "status": "finding" if (
                native["has_service_pair"]
                and not native["has_servreg_wlan_pd"]
                and not native["kernel_progression"]
                and not native["has_wlfw_qmi"]
                and not native["has_wlan_ready"]
            ) else "review",
            "detail": {
                "service_state_up": native["counts"].get("service_state_up", 0),
                "wlan_pd": native["counts"].get("wlan_pd", 0),
                "pd_notifier": native["counts"].get("pd_notifier", 0),
                "qca6390_power": native["counts"].get("qca6390_power", 0),
                "icnss_qmi": native["counts"].get("icnss_qmi", 0),
                "wlfw": native["counts"].get("wlfw", 0),
                "wlan0": native["counts"].get("wlan0", 0),
            },
            "next_step": "instrument service-locator/SERVREG indication and CNSS2 callback path before HAL/connect",
        },
        {
            "name": "native-cnss-daemon-started-without-wlfw",
            "status": "finding" if native["counts"].get("cnss_daemon_netlink", 0) > 0 and not native["has_wlfw_qmi"] else "review",
            "detail": {
                "cnss_daemon_netlink": native["counts"].get("cnss_daemon_netlink", 0),
                "cnss_daemon_cld80211": native["counts"].get("cnss_daemon_cld80211", 0),
                "service_180_to_cnss_daemon_ms": native["deltas_ms"].get("service_180_to_cnss_daemon"),
            },
            "next_step": "separate cnss-daemon runtime continuation from kernel SERVREG callback in the next gate",
        },
    ]


def decide(command: str, checks: list[dict[str, Any]], android: dict[str, Any], native: dict[str, Any]) -> tuple[str, bool, str, str]:
    if command == "plan":
        return (
            "v721-servreg-cnss2-delta-plan-ready",
            True,
            "plan-only; no device command executed",
            "run V721 host-only classifier over Android V622 and native V720 evidence",
        )
    blocked = [check["name"] for check in checks if check["status"] == "blocked"]
    if blocked:
        return (
            "v721-servreg-cnss2-delta-blocked",
            False,
            "blocked by " + ", ".join(blocked),
            "refresh missing Android/native evidence before live work",
        )
    findings = {check["name"] for check in checks if check["status"] == "finding"}
    required = {
        "android-servreg-wlanpd-continuation",
        "native-servreg-wlanpd-cnss2-gap",
        "native-cnss-daemon-started-without-wlfw",
    }
    if required <= findings and native["qrtr_ns_observable"]:
        return (
            "v721-servreg-wlanpd-cnss2-event-gap-classified",
            True,
            "Android continues from service 180/74 into WLAN-PD/QMI/BDF/fw_ready/wlan0, while native has qrtr-ns and service 180/74 but no SERVICE_STATE_UP/WLAN-PD/CNSS2/QCA/WLFW progression.",
            "plan V722 as a bounded SERVREG/service-locator indication and CNSS2 callback observer before Wi-Fi HAL or connect",
        )
    if native["has_wlan_ready"] or native["wlfw_or_wlan0"]:
        return (
            "v721-native-wlfw-or-wlan-ready",
            True,
            "native evidence already progressed WLFW/BDF/fw_ready/wlan0",
            "move to wlan0 readiness gate before scan/connect",
        )
    return (
        "v721-servreg-cnss2-delta-review",
        True,
        "evidence is valid but does not match the expected V622/V720 contrast",
        "inspect V721 summary before choosing next gate",
    )


def render_counts(title: str, counts: dict[str, int]) -> str:
    rows = [[marker, str(counts.get(marker, 0))] for marker in TIMELINE_MARKERS]
    return "\n".join([f"## {title}", "", markdown_table(["marker", "count"], rows)])


def render_summary(manifest: dict[str, Any]) -> str:
    android = manifest.get("android") or {}
    native = manifest.get("native") or {}
    check_rows = [
        [check["name"], check["status"], json.dumps(check["detail"], sort_keys=True), check["next_step"]]
        for check in manifest.get("checks", [])
    ]
    delta_rows = [
        [name, str((android.get("deltas_ms") or {}).get(name)), str((native.get("deltas_ms") or {}).get(name))]
        for name in sorted(set((android.get("deltas_ms") or {}).keys()) | set((native.get("deltas_ms") or {}).keys()))
    ]
    source_rows = [
        ["android_manifest", android.get("manifest", "")],
        ["native_root", native.get("root", "")],
        ["native_top_manifest", native.get("top_manifest", "")],
        ["native_reconcile_manifest", native.get("reconcile_manifest", "")],
    ]
    return "\n".join([
        "# V721 SERVREG/CNSS2 Delta Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        f"- external_ping_executed: `{manifest['external_ping_executed']}`",
        "",
        "## Sources",
        "",
        markdown_table(["source", "path"], source_rows),
        "",
        "## Checks",
        "",
        markdown_table(["name", "status", "detail", "next"], check_rows) if check_rows else "- plan only",
        "",
        "## Timing Deltas",
        "",
        markdown_table(["delta", "android_ms", "native_ms"], delta_rows),
        "",
        render_counts("Android Counts", android.get("counts") or {}),
        "",
        render_counts("Native Counts", native.get("counts") or {}),
        "",
        "## Guardrails",
        "",
        "\n".join(f"- {item}" for item in manifest["forbidden_actions"]),
    ])


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    android: dict[str, Any] = {}
    native: dict[str, Any] = {}
    checks: list[dict[str, Any]] = []
    if args.command == "run":
        android = android_surface(args.android_v622_manifest)
        native = native_surface(args.native_v720_source)
        checks = build_checks(android, native)
    decision, pass_ok, reason, next_step = decide(args.command, checks, android, native)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "cycle": "v721",
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "android": android,
        "native": native,
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
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

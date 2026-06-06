#!/usr/bin/env python3
"""V736 host-only service-180 to WLAN-PD/MHI gap classifier.

This classifier compares the current V735 CNSS-only live evidence against the
Android V622 success baseline and the older V627 post-180 observer. It does not
contact the device or perform live Wi-Fi actions.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v736-service180-to-mhi-gap")
DEFAULT_V735_MANIFEST = Path("tmp/wifi/v735-current-cnss-only-observer/manifest.json")
DEFAULT_ANDROID_V622_MANIFEST = Path(
    "tmp/wifi/v622-android-mdm-helper-timing-handoff-live-20260523-032506/"
    "v622-android-mdm-helper-timing-recapture-run/manifest.json"
)
DEFAULT_V627_MANIFEST = Path("tmp/wifi/v627-post-180-observer-live-v2/manifest.json")
LATEST_POINTER = Path("tmp/wifi/latest-v736-service180-to-mhi-gap.txt")

SERVICE_180_RE = re.compile(r"\b180 service\b", re.I)
SERVICE_74_RE = re.compile(r"\b74 service\b", re.I)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v735-manifest", type=Path, default=DEFAULT_V735_MANIFEST)
    parser.add_argument("--android-v622-manifest", type=Path, default=DEFAULT_ANDROID_V622_MANIFEST)
    parser.add_argument("--v627-manifest", type=Path, default=DEFAULT_V627_MANIFEST)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def load_manifest(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {"exists": False, "path": str(resolved)}
    try:
        data = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {"exists": True, "path": str(resolved), "invalid": str(exc)}
    if not isinstance(data, dict):
        return {"exists": True, "path": str(resolved), "invalid": "not-object"}
    data.setdefault("exists", True)
    data.setdefault("path", str(resolved))
    return data


def int_value(value: Any) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        match = re.match(r"\s*(-?\d+)", value)
        if match:
            return int(match.group(1))
    return 0


def bool_key(keys: dict[str, Any], name: str) -> bool:
    return int_value(keys.get(name)) > 0


def count_key(keys: dict[str, Any], name: str) -> int:
    return int_value(keys.get(name))


def get_v735(v735: dict[str, Any]) -> dict[str, Any]:
    live = v735.get("live") or {}
    markers = (live.get("markers") or {}).get("counts") or {}
    first = (live.get("markers") or {}).get("first_lines") or {}
    helper = live.get("helper_result") or {}
    keys = helper.get("keys") or {}
    if not isinstance(keys, dict):
        keys = {}
    readback = live.get("qrtr_readback") or {}
    service_line = str(first.get("service_notifier") or "")
    service_180 = int(SERVICE_180_RE.search(service_line) is not None)
    service_74 = int(SERVICE_74_RE.search(service_line) is not None)
    return {
        "decision": v735.get("decision"),
        "pass": v735.get("pass"),
        "service_line": service_line,
        "service_notifier_180": service_180,
        "service_notifier_74": service_74,
        "markers": markers,
        "helper_order": helper.get("order"),
        "cnss_diag_started": int_value(helper.get("cnss_diag")),
        "cnss_daemon_started": int_value(helper.get("cnss_daemon")),
        "cnss_daemon_pid": helper.get("cnss_daemon_pid"),
        "qmi_attempted": int_value(readback.get("qmi_attempted")),
        "service69_events": int_value(readback.get("service_events")),
        "service69_end_of_list": int_value(readback.get("end_of_list")),
        "icnss_driver_link": bool_key(keys, "wifi_icnss_edge.window.icnss_driver_link.exists"),
        "qca6390_driver_link": bool_key(keys, "wifi_icnss_edge.window.qca6390_driver_link.exists"),
        "wlan0_netdev": bool_key(keys, "wifi_icnss_edge.window.wlan0_netdev.exists"),
        "mhi_devices_count": count_key(keys, "A90_EXECNS_DIR_wifi_icnss_edge_window_mhi_devices_END count"),
        "pci_devices_count": count_key(keys, "A90_EXECNS_DIR_wifi_icnss_edge_window_pci_devices_END count"),
        "qca6390_device_captured": bool_key(keys, "wifi_companion_start.cnss2_focus_window.qca6390_device_captured"),
        "mhi_devices_captured": bool_key(keys, "wifi_companion_start.icnss_edge_window.mhi_devices_captured"),
        "pci_devices_captured": bool_key(keys, "wifi_companion_start.icnss_edge_window.pci_devices_captured"),
        "kernel_warning": int_value(markers.get("kernel_warning")),
    }


def get_android(android: dict[str, Any]) -> dict[str, Any]:
    summary = android.get("android_summary") or {}
    counts = summary.get("counts") or {}
    deltas = summary.get("deltas_ms") or {}
    timing = summary.get("timing") or {}
    return {
        "decision": android.get("decision"),
        "pass": android.get("pass"),
        "counts": counts,
        "deltas_ms": deltas,
        "timing": timing,
        "has_service_pair": bool(summary.get("has_service_notifier_pair")),
        "has_wlan_pd": bool(summary.get("has_wlan_pd")),
        "has_sysmon_esoc0": bool(summary.get("has_sysmon_esoc0")),
    }


def get_v627(v627: dict[str, Any]) -> dict[str, Any]:
    live = v627.get("live") or {}
    observer = live.get("post_180_observer") or {}
    return {
        "decision": v627.get("decision"),
        "pass": v627.get("pass"),
        "counts": observer.get("counts") or {},
        "deltas_ms": observer.get("deltas_ms") or {},
        "post_180_window_sec": observer.get("observed_post_180_window_sec"),
        "readback_service_events": int_value(observer.get("wlfw_qrtr_readback_service_events")),
        "readback_end_of_list": int_value(observer.get("wlfw_qrtr_readback_end_of_list")),
        "readback_qmi_attempted": int_value(observer.get("wlfw_qrtr_readback_qmi_attempted")),
    }


def build_checks(args: argparse.Namespace,
                 v735_raw: dict[str, Any],
                 android_raw: dict[str, Any],
                 v627_raw: dict[str, Any],
                 v735: dict[str, Any],
                 android: dict[str, Any],
                 v627: dict[str, Any]) -> list[dict[str, Any]]:
    if args.command == "plan":
        return [{
            "name": "plan-only",
            "status": "pass",
            "detail": "host-only classifier; no device command executed",
            "next_step": "run V736 against V735/V622/V627 manifests",
        }]
    checks: list[dict[str, Any]] = [
        {
            "name": "inputs-present",
            "status": "pass" if all(item.get("exists") and not item.get("invalid") for item in (v735_raw, android_raw, v627_raw)) else "blocked",
            "detail": {
                "v735": v735_raw.get("path"),
                "android_v622": android_raw.get("path"),
                "v627": v627_raw.get("path"),
            },
            "next_step": "restore missing evidence or rerun prerequisite classifier",
        },
        {
            "name": "current-v735-safe-gate",
            "status": "pass" if v735.get("decision") == "v735-current-cnss-only-service-publication-advance" and v735.get("pass") is True and v735.get("cnss_daemon_started") == 1 and v735.get("qmi_attempted") == 0 and v735.get("kernel_warning") == 0 else "blocked",
            "detail": {
                "decision": v735.get("decision"),
                "pass": v735.get("pass"),
                "cnss_diag": v735.get("cnss_diag_started"),
                "cnss_daemon": v735.get("cnss_daemon_started"),
                "qmi_attempted": v735.get("qmi_attempted"),
                "kernel_warning": v735.get("kernel_warning"),
            },
            "next_step": "rerun V735 if current evidence is not safe",
        },
        {
            "name": "android-reference-complete",
            "status": "pass" if android.get("has_service_pair") and android.get("has_wlan_pd") and int_value((android.get("counts") or {}).get("wlfw_start")) and int_value((android.get("counts") or {}).get("wlan0")) else "blocked",
            "detail": {
                "decision": android.get("decision"),
                "service_pair": android.get("has_service_pair"),
                "wlan_pd": android.get("has_wlan_pd"),
                "wlfw_start": (android.get("counts") or {}).get("wlfw_start"),
                "wlan0": (android.get("counts") or {}).get("wlan0"),
            },
            "next_step": "refresh Android reference before classifying native gap",
        },
        {
            "name": "service180-confirmed",
            "status": "pass" if v735.get("service_notifier_180") == 1 else "blocked",
            "detail": {"line": v735.get("service_line")},
            "next_step": "do not proceed to post-180 analysis if current run did not reach service 180",
        },
        {
            "name": "post180-gap-confirmed",
            "status": "pass" if v735.get("service_notifier_180") == 1 and int_value((v735.get("markers") or {}).get("wlan_pd")) == 0 and v735.get("service69_events") == 0 and int_value((v735.get("markers") or {}).get("mhi")) == 0 else "review",
            "detail": {
                "v735_wlan_pd": (v735.get("markers") or {}).get("wlan_pd"),
                "v735_mhi": (v735.get("markers") or {}).get("mhi"),
                "v735_qca6390": (v735.get("markers") or {}).get("qca6390"),
                "v735_wlfw": (v735.get("markers") or {}).get("wlfw"),
                "v735_service69_events": v735.get("service69_events"),
                "v627_service74": (v627.get("counts") or {}).get("service_notifier_74"),
                "v627_wlan_pd": (v627.get("counts") or {}).get("wlan_pd"),
            },
            "next_step": "classify lower publisher or MHI trigger before HAL/connect",
        },
        {
            "name": "qca-mhi-surface",
            "status": "pass" if v735.get("icnss_driver_link") and v735.get("qca6390_device_captured") and not v735.get("qca6390_driver_link") and v735.get("mhi_devices_count") == 0 and v735.get("pci_devices_count") == 0 else "review",
            "detail": {
                "icnss_driver_link": v735.get("icnss_driver_link"),
                "qca6390_device_captured": v735.get("qca6390_device_captured"),
                "qca6390_driver_link": v735.get("qca6390_driver_link"),
                "mhi_devices_count": v735.get("mhi_devices_count"),
                "pci_devices_count": v735.get("pci_devices_count"),
                "wlan0_netdev": v735.get("wlan0_netdev"),
            },
            "next_step": "if qca6390 is still unbound and MHI/PCI absent, stay below HAL/connect",
        },
    ]
    return checks


def decide(args: argparse.Namespace,
           checks: list[dict[str, Any]],
           v735: dict[str, Any],
           android: dict[str, Any],
           v627: dict[str, Any]) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return (
            "v736-service180-to-mhi-gap-plan-ready",
            True,
            "plan-only; no device command executed",
            "run host-only V736 classifier",
        )
    blocked = [check["name"] for check in checks if check["status"] == "blocked"]
    if blocked:
        return (
            "v736-service180-to-mhi-gap-blocked",
            False,
            "blocked by " + ", ".join(blocked),
            "clear evidence blocker before next live gate",
        )
    android_deltas = android.get("deltas_ms") or {}
    v627_counts = v627.get("counts") or {}
    if (
        v735.get("service_notifier_180") == 1
        and int_value((v735.get("markers") or {}).get("wlan_pd")) == 0
        and v735.get("service69_events") == 0
        and v735.get("mhi_devices_count") == 0
        and not v735.get("qca6390_driver_link")
        and int_value(v627_counts.get("service_notifier_74")) == 0
        and android_deltas.get("service_notifier_180_to_service_notifier_74") is not None
    ):
        return (
            "v736-service180-to-service74-mhi-gap-classified",
            True,
            (
                "native reaches service 180 but not Android's service 74/WLAN-PD/WLFW/MHI path; "
                "qca6390 remains unbound and MHI/PCI devices are absent"
            ),
            "plan V737 as a lower service-74/WLAN-PD publisher trigger classifier before HAL/connect",
        )
    return (
        "v736-service180-to-mhi-gap-review",
        True,
        "evidence is safe but does not match the expected V735/V627/Android delta pattern",
        "inspect manifest deltas before choosing the next live gate",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    checks = [
        [check["name"], check["status"], json.dumps(check["detail"], ensure_ascii=False, sort_keys=True), check["next_step"]]
        for check in manifest.get("checks", [])
    ]
    v735 = manifest.get("v735_summary") or {}
    android = manifest.get("android_v622_summary") or {}
    v627 = manifest.get("v627_summary") or {}
    current_rows = [
        ["v735_decision", v735.get("decision", "")],
        ["v735_service_line", v735.get("service_line", "")],
        ["v735_markers", json.dumps({key: (v735.get("markers") or {}).get(key, 0) for key in ("service_notifier", "wlan_pd", "mhi", "qca6390", "wlfw", "bdf", "wlan0", "kernel_warning")}, sort_keys=True)],
        ["v735_qrtr_readback", json.dumps({key: v735.get(key) for key in ("service69_events", "service69_end_of_list", "qmi_attempted")}, sort_keys=True)],
        ["v735_qca_mhi_surface", json.dumps({key: v735.get(key) for key in ("icnss_driver_link", "qca6390_device_captured", "qca6390_driver_link", "mhi_devices_count", "pci_devices_count", "wlan0_netdev")}, sort_keys=True)],
    ]
    compare_rows = [
        ["android_180_to_74_ms", str((android.get("deltas_ms") or {}).get("service_notifier_180_to_service_notifier_74"))],
        ["android_180_to_wlan_pd_ms", str((android.get("deltas_ms") or {}).get("service_notifier_180_to_wlan_pd"))],
        ["android_180_to_wlfw_start_ms", str((android.get("deltas_ms") or {}).get("service_notifier_180_to_wlfw_start"))],
        ["android_wlan_pd_to_qmi_ms", str((android.get("deltas_ms") or {}).get("wlan_pd_to_qmi_server_connected"))],
        ["v627_post180_window_sec", str(v627.get("post_180_window_sec"))],
        ["v627_service74", str((v627.get("counts") or {}).get("service_notifier_74"))],
        ["v627_wlan_pd", str((v627.get("counts") or {}).get("wlan_pd"))],
        ["v627_wlfw_readback_events", str(v627.get("readback_service_events"))],
    ]
    return "\n".join([
        "# V736 Service-180 to MHI Gap Classifier",
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
        "## Checks",
        "",
        markdown_table(["name", "status", "detail", "next"], checks),
        "",
        "## Current V735",
        "",
        markdown_table(["key", "value"], current_rows),
        "",
        "## Android/V627 Comparison",
        "",
        markdown_table(["key", "value"], compare_rows),
    ])


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    v735_raw = load_manifest(args.v735_manifest)
    android_raw = load_manifest(args.android_v622_manifest)
    v627_raw = load_manifest(args.v627_manifest)
    v735 = get_v735(v735_raw) if args.command == "run" else {}
    android = get_android(android_raw) if args.command == "run" else {}
    v627 = get_v627(v627_raw) if args.command == "run" else {}
    checks = build_checks(args, v735_raw, android_raw, v627_raw, v735, android, v627)
    decision, pass_ok, reason, next_step = decide(args, checks, v735, android, v627)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "cycle": "v736",
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "out_dir": str(repo_path(args.out_dir)),
        "inputs": {
            "v735": {"path": v735_raw.get("path"), "decision": v735_raw.get("decision"), "pass": v735_raw.get("pass")},
            "android_v622": {"path": android_raw.get("path"), "decision": android_raw.get("decision"), "pass": android_raw.get("pass")},
            "v627": {"path": v627_raw.get("path"), "decision": v627_raw.get("decision"), "pass": v627_raw.get("pass")},
        },
        "v735_summary": v735,
        "android_v622_summary": android,
        "v627_summary": v627,
        "checks": checks,
        "device_commands_executed": False,
        "daemon_start_executed": False,
        "service_manager_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "wifi_bringup_executed": False,
        "external_ping_executed": False,
        "boot_or_partition_write_executed": False,
    }


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir.relative_to(repo_path("."))) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"wifi_hal_start_executed: {manifest['wifi_hal_start_executed']}")
    print(f"scan_connect_executed: {manifest['scan_connect_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""V739 host-only MDM3/WLAN-PD lower-trigger delta classifier.

This classifier compares Android lower-surface evidence against the latest V738
native observer. It does not contact the device or perform live Wi-Fi actions.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v739-mdm3-wlanpd-delta")
DEFAULT_ANDROID_V590_MANIFEST = Path(
    "tmp/wifi/v591-android-subsys-state-sample-handoff/"
    "v590-android-subsys-state-sample-run/manifest.json"
)
DEFAULT_ANDROID_V611_MANIFEST = Path(
    "tmp/wifi/v612-android-lower-surface-handoff-20260523-011739/"
    "v611-android-lower-surface-recapture-run/manifest.json"
)
DEFAULT_ANDROID_V622_MANIFEST = Path(
    "tmp/wifi/v622-android-mdm-helper-timing-handoff-live-20260523-032506/"
    "v622-android-mdm-helper-timing-recapture-run/manifest.json"
)
DEFAULT_V614_MANIFEST = Path("tmp/wifi/v614-mdm3-trigger-path-classifier/manifest.json")
DEFAULT_V620_MANIFEST = Path("tmp/wifi/v620-dsp-mdm3-safety-classifier-current-request-20260523/manifest.json")
DEFAULT_V738_MANIFEST = Path("tmp/wifi/v738-modem-wlan-mhi-observer/manifest.json")
LATEST_POINTER = Path("tmp/wifi/latest-v739-mdm3-wlanpd-delta.txt")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--android-v590-manifest", type=Path, default=DEFAULT_ANDROID_V590_MANIFEST)
    parser.add_argument("--android-v611-manifest", type=Path, default=DEFAULT_ANDROID_V611_MANIFEST)
    parser.add_argument("--android-v622-manifest", type=Path, default=DEFAULT_ANDROID_V622_MANIFEST)
    parser.add_argument("--v614-manifest", type=Path, default=DEFAULT_V614_MANIFEST)
    parser.add_argument("--v620-manifest", type=Path, default=DEFAULT_V620_MANIFEST)
    parser.add_argument("--v738-manifest", type=Path, default=DEFAULT_V738_MANIFEST)
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
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.lstrip("-").isdigit():
            return int(stripped)
    return 0


def android_state_summary(manifest: dict[str, Any]) -> dict[str, Any]:
    summary = manifest.get("android_summary") or {}
    selected = summary.get("selected_values") or summary.get("delayed_values") or summary.get("initial_values") or {}
    counts = summary.get("counts") or {}
    deltas = summary.get("deltas_ms") or {}
    return {
        "decision": manifest.get("decision"),
        "pass": manifest.get("pass"),
        "mss_state": summary.get("mss_state") or selected.get("mss_state"),
        "mdm3_state": summary.get("mdm3_state") or selected.get("mdm3_state"),
        "mss_firmware_name": selected.get("mss_firmware_name"),
        "mdm3_firmware_name": selected.get("mdm3_firmware_name"),
        "has_wlan_pd": bool(summary.get("has_wlan_pd")) or int_value(counts.get("wlan_pd")) > 0,
        "has_service_notifier_180": bool(summary.get("has_service_notifier_180")) or int_value(counts.get("service_notifier_180")) > 0,
        "has_service_notifier_74": int_value(counts.get("service_notifier_74")) > 0,
        "has_sysmon_esoc0": bool(summary.get("has_sysmon_esoc0")) or int_value(counts.get("sysmon_esoc0")) > 0,
        "counts": counts,
        "deltas_ms": deltas,
    }


def android_v589_summary(manifest: dict[str, Any]) -> dict[str, Any]:
    state = manifest.get("android_state_sample") or {}
    summary = manifest.get("android_summary") or {}
    counts = summary.get("counts") or {}
    return {
        "decision": manifest.get("decision"),
        "pass": manifest.get("pass"),
        "android_state_sample": state,
        "counts": counts,
    }


def v614_summary(manifest: dict[str, Any]) -> dict[str, Any]:
    android = manifest.get("android_v611") or {}
    native = manifest.get("native_v613") or {}
    return {
        "decision": manifest.get("decision"),
        "pass": manifest.get("pass"),
        "android_mss_state": android.get("mss_state"),
        "android_mdm3_state": android.get("mdm3_state"),
        "native_mss_after_companion": native.get("mss_after_companion"),
        "native_mdm3_after_companion": native.get("mdm3_after_companion"),
        "android_counts": android.get("counts") or {},
        "native_counts": native.get("counts") or {},
    }


def v620_summary(manifest: dict[str, Any]) -> dict[str, Any]:
    checks = manifest.get("causality_checks") or {}
    inferences = manifest.get("inferences") or {}
    android = manifest.get("android_v611") or {}
    return {
        "decision": manifest.get("decision"),
        "pass": manifest.get("pass"),
        "causality_checks": checks,
        "inferences": inferences,
        "android_mss_state": android.get("mss_state"),
        "android_mdm3_state": android.get("mdm3_state"),
        "android_deltas_ms": android.get("deltas_ms") or {},
        "mdm_helper_path": manifest.get("mdm_helper_path") or {},
        "requested_hypothesis_additions": manifest.get("requested_hypothesis_additions") or {},
    }


def v738_summary(manifest: dict[str, Any]) -> dict[str, Any]:
    lower = manifest.get("lower_state") or {}
    surface = manifest.get("mhi_surface") or {}
    markers = surface.get("markers") or {}
    return {
        "decision": manifest.get("decision"),
        "pass": manifest.get("pass"),
        "mss_before": lower.get("mss_before"),
        "mss_after_holder": lower.get("mss_after_holder"),
        "mss_after_companion": lower.get("mss_after_companion"),
        "mdm3_before": lower.get("mdm3_before"),
        "mdm3_after_holder": lower.get("mdm3_after_holder"),
        "mdm3_after_companion": lower.get("mdm3_after_companion"),
        "qrtr_rx_seen": bool(lower.get("qrtr_rx_seen")),
        "qrtr_services": lower.get("qrtr_services") or {},
        "service69_events": int_value((lower.get("qrtr_readback") or {}).get("service_events")),
        "qmi_attempted": int_value((lower.get("qrtr_readback") or {}).get("qmi_attempted")),
        "mhi_devices_count": int_value(surface.get("mhi_devices_count")),
        "pci_devices_count": int_value(surface.get("pci_devices_count")),
        "qca6390_device_captured": bool(surface.get("qca6390_device_captured")),
        "qca6390_driver_link": bool(surface.get("qca6390_driver_link")),
        "wlan0_netdev": bool(surface.get("wlan0_netdev")),
        "markers": markers,
    }


def build_checks(args: argparse.Namespace, raw: dict[str, dict[str, Any]], summaries: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    if args.command == "plan":
        return [{
            "name": "plan-only",
            "status": "pass",
            "detail": "host-only classifier; no device command executed",
            "next_step": "run V739 against existing Android/native manifests",
        }]

    inputs_ready = all(item.get("exists") and not item.get("invalid") for item in raw.values())
    v590 = summaries["android_v590"]
    v611 = summaries["android_v611"]
    v622 = summaries["android_v622"]
    v614 = summaries["v614"]
    v620 = summaries["v620"]
    v738 = summaries["v738"]
    causality = v620.get("causality_checks") or {}
    inferences = v620.get("inferences") or {}
    return [
        {
            "name": "inputs-present",
            "status": "pass" if inputs_ready else "blocked",
            "detail": {name: item.get("path") for name, item in raw.items()},
            "next_step": "restore missing manifest before V739 classification",
        },
        {
            "name": "android-mdm3-online-baseline",
            "status": "pass" if v590.get("mss_state") == "ONLINE" and v590.get("mdm3_state") == "ONLINE" and v611.get("mdm3_state") == "ONLINE" else "blocked",
            "detail": {
                "v590_mss": v590.get("mss_state"),
                "v590_mdm3": v590.get("mdm3_state"),
                "v611_mss": v611.get("mss_state"),
                "v611_mdm3": v611.get("mdm3_state"),
                "v590_firmware": {
                    "mss": v590.get("mss_firmware_name"),
                    "mdm3": v590.get("mdm3_firmware_name"),
                },
            },
            "next_step": "refresh Android lower state if ONLINE baseline is missing",
        },
        {
            "name": "android-wlanpd-wlfw-continuation",
            "status": "pass" if v622.get("has_wlan_pd") and int_value((v622.get("counts") or {}).get("wlfw_start")) and int_value((v622.get("counts") or {}).get("wlan0")) else "blocked",
            "detail": {
                "v622_counts": {name: (v622.get("counts") or {}).get(name, 0) for name in ("service_notifier_180", "service_notifier_74", "wlan_pd", "wlfw_start", "bdf_regdb", "bdf_bdwlan", "wlan0")},
                "v622_deltas_ms": {name: (v622.get("deltas_ms") or {}).get(name) for name in ("service_notifier_180_to_wlan_pd", "service_notifier_180_to_wlfw_start", "wlan_pd_to_qmi_server_connected")},
            },
            "next_step": "do not proceed toward connect until native has this lower continuation",
        },
        {
            "name": "native-v738-mdm3-delta",
            "status": "pass" if v738.get("mss_after_companion") == "ONLINE" and v738.get("mdm3_after_companion") == "OFFLINING" and v738.get("service69_events") == 0 else "blocked",
            "detail": {
                "v738_decision": v738.get("decision"),
                "mss": [v738.get("mss_before"), v738.get("mss_after_holder"), v738.get("mss_after_companion")],
                "mdm3": [v738.get("mdm3_before"), v738.get("mdm3_after_holder"), v738.get("mdm3_after_companion")],
                "qrtr_services": v738.get("qrtr_services"),
                "service69_events": v738.get("service69_events"),
                "mhi_devices_count": v738.get("mhi_devices_count"),
            },
            "next_step": "treat mdm3/WLAN-PD continuation as the active lower blocker",
        },
        {
            "name": "raw-esoc-and-direct-dsp-still-blocked",
            "status": "pass" if v620.get("decision") == "v620-esoc0-notifier-causality-refined" and causality.get("android_service_notifier_before_sysmon_esoc0") is True and causality.get("direct_dsp_warning_present") is True else "review",
            "detail": {
                "v620_decision": v620.get("decision"),
                "causality_checks": causality,
                "inferences": inferences,
                "v614_decision": v614.get("decision"),
            },
            "next_step": "do not repeat raw esoc0 or direct ADSP/CDSP/SLPI boot-node writes",
        },
        {
            "name": "mdm-helper-not-first-notifier-trigger",
            "status": "pass" if v622.get("decision") == "v622-mdm-helper-post-notifier-not-root-trigger" and v620.get("mdm_helper_path") else "review",
            "detail": {
                "v622_decision": v622.get("decision"),
                "v622_timing": {name: (v622.get("deltas_ms") or {}).get(name) for name in ("service_notifier_180_to_wlan_pd", "service_notifier_180_to_service_notifier_74")},
                "mdm_helper_path": v620.get("mdm_helper_path"),
            },
            "next_step": "classify mdm_helper/baseband contract host-only before any start-only proof",
        },
    ]


def decide(args: argparse.Namespace, checks: list[dict[str, Any]]) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return (
            "v739-mdm3-wlanpd-delta-plan-ready",
            True,
            "plan-only; no device command executed",
            "run host-only V739 classifier",
        )
    blocked = [check["name"] for check in checks if check["status"] == "blocked"]
    if blocked:
        return (
            "v739-mdm3-wlanpd-delta-blocked",
            False,
            "blocked by " + ", ".join(blocked),
            "restore missing/contradictory evidence before next gate",
        )
    return (
        "v739-mdm3-online-delta-active-blocker",
        True,
        "Android has mss/mdm3 ONLINE with WLAN-PD/WLFW continuation; native V738 reaches mss ONLINE but leaves mdm3 OFFLINING and no MHI/WLFW",
        "plan V740 as host-only mdm_helper/baseband contract classifier before any live trigger",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    check_rows = [
        [check["name"], check["status"], json.dumps(check["detail"], ensure_ascii=False, sort_keys=True), check["next_step"]]
        for check in manifest.get("checks", [])
    ]
    summary_rows = [
        ["android_v590", json.dumps(manifest.get("android_v590_summary", {}), ensure_ascii=False, sort_keys=True)],
        ["android_v611", json.dumps(manifest.get("android_v611_summary", {}), ensure_ascii=False, sort_keys=True)],
        ["android_v622", json.dumps(manifest.get("android_v622_summary", {}), ensure_ascii=False, sort_keys=True)],
        ["v614", json.dumps(manifest.get("v614_summary", {}), ensure_ascii=False, sort_keys=True)],
        ["v620", json.dumps(manifest.get("v620_summary", {}), ensure_ascii=False, sort_keys=True)],
        ["v738", json.dumps(manifest.get("v738_summary", {}), ensure_ascii=False, sort_keys=True)],
    ]
    return "\n".join([
        "# V739 MDM3/WLAN-PD Lower-trigger Delta Classifier",
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
        markdown_table(["name", "status", "detail", "next"], check_rows),
        "",
        "## Evidence Summary",
        "",
        markdown_table(["item", "value"], summary_rows),
    ])


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    raw = {
        "android_v590": load_manifest(args.android_v590_manifest),
        "android_v611": load_manifest(args.android_v611_manifest),
        "android_v622": load_manifest(args.android_v622_manifest),
        "v614": load_manifest(args.v614_manifest),
        "v620": load_manifest(args.v620_manifest),
        "v738": load_manifest(args.v738_manifest),
    }
    if args.command == "run":
        summaries = {
            "android_v590": android_state_summary(raw["android_v590"]),
            "android_v611": android_state_summary(raw["android_v611"]),
            "android_v622": android_state_summary(raw["android_v622"]),
            "v614": v614_summary(raw["v614"]),
            "v620": v620_summary(raw["v620"]),
            "v738": v738_summary(raw["v738"]),
        }
    else:
        summaries = {name: {} for name in raw}
    checks = build_checks(args, raw, summaries)
    decision, pass_ok, reason, next_step = decide(args, checks)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "cycle": "v739",
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "out_dir": str(repo_path(args.out_dir)),
        "inputs": {
            name: {"path": item.get("path"), "decision": item.get("decision"), "pass": item.get("pass")}
            for name, item in raw.items()
        },
        "checks": checks,
        **{f"{name}_summary": summary for name, summary in summaries.items()},
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

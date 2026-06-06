#!/usr/bin/env python3
"""V813 host-only post-sysmon WLAN-PD/service publication classifier."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v813-post-sysmon-publication-classifier")
LATEST_POINTER = Path("tmp/wifi/latest-v813-post-sysmon-publication-classifier.txt")
DEFAULT_V812_MANIFEST = Path("tmp/wifi/v812-mdm3-wlanpd-service69-observer-rerun/manifest.json")
DEFAULT_V811_MANIFEST = Path("tmp/wifi/v811-wlfw-publication-precondition-classifier/manifest.json")
DEFAULT_V785_MANIFEST = Path("tmp/wifi/v785-android-native-memshare-delta/manifest.json")
DEFAULT_V783_MANIFEST = Path("tmp/wifi/v783-android-native-pil-gap/manifest.json")
DEFAULT_V626_MANIFEST = Path("tmp/wifi/v626-post-180-publication-classifier/manifest.json")
DEFAULT_V739_MANIFEST = Path("tmp/wifi/v739-mdm3-wlanpd-delta/manifest.json")

FORBIDDEN_ACTIONS = (
    "device command",
    "custom kernel flash, boot image write, or partition write",
    "reboot or bootloader handoff",
    "Wi-Fi HAL, wificond, supplicant, hostapd, scan/connect/link-up",
    "credential use",
    "DHCP, route change, or external ping",
    "boot_wlan, qcwlanstate, esoc0, bind/unbind, driver override, or module load/unload",
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v812-manifest", type=Path, default=DEFAULT_V812_MANIFEST)
    parser.add_argument("--v811-manifest", type=Path, default=DEFAULT_V811_MANIFEST)
    parser.add_argument("--v785-manifest", type=Path, default=DEFAULT_V785_MANIFEST)
    parser.add_argument("--v783-manifest", type=Path, default=DEFAULT_V783_MANIFEST)
    parser.add_argument("--v626-manifest", type=Path, default=DEFAULT_V626_MANIFEST)
    parser.add_argument("--v739-manifest", type=Path, default=DEFAULT_V739_MANIFEST)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def resolve(path: Path) -> Path:
    return path if path.is_absolute() else repo_path(path)


def load_json(path: Path) -> dict[str, Any]:
    resolved = resolve(path)
    info: dict[str, Any] = {"path": str(resolved), "exists": resolved.exists()}
    if not resolved.exists() or not resolved.is_file():
        return {"file": info, "data": {}}
    info.update({"is_file": True, "size": resolved.stat().st_size})
    try:
        payload = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {"file": info, "data": {}, "error": str(exc)}
    return {"file": info, "data": payload if isinstance(payload, dict) else {}}


def nested(payload: dict[str, Any], *keys: str, default: Any = None) -> Any:
    current: Any = payload
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return current


def int_value(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def manifest_summary(label: str, path: Path) -> dict[str, Any]:
    entry = load_json(path)
    data = entry["data"]
    return {
        "label": label,
        "file": entry["file"],
        "decision": data.get("decision", ""),
        "pass": bool(data.get("pass")),
        "reason": data.get("reason", ""),
        "next_step": data.get("next_step", ""),
        "data": data,
    }


def build_analysis(args: argparse.Namespace) -> dict[str, Any]:
    inputs = {
        "v812": manifest_summary("v812", args.v812_manifest),
        "v811": manifest_summary("v811", args.v811_manifest),
        "v785": manifest_summary("v785", args.v785_manifest),
        "v783": manifest_summary("v783", args.v783_manifest),
        "v626": manifest_summary("v626", args.v626_manifest),
        "v739": manifest_summary("v739", args.v739_manifest),
    }
    v812_summary = as_dict(nested(inputs["v812"]["data"], "v735_arm", "summary", default={}))
    v812_markers = as_dict(v812_summary.get("markers"))
    v812_qrtr = as_dict(v812_summary.get("qrtr_readback"))
    v785_checks = inputs["v785"]["data"].get("checks")
    v783_checks = inputs["v783"]["data"].get("checks")
    v626_android = as_dict(inputs["v626"]["data"].get("android"))
    v626_native = as_dict(inputs["v626"]["data"].get("native"))
    v739_checks = inputs["v739"]["data"].get("checks")
    android_counts = as_dict(v626_android.get("counts"))
    native_counts = as_dict(v626_native.get("counts"))
    return {
        "inputs": inputs,
        "v812_current": {
            "decision": inputs["v812"]["decision"],
            "pass": inputs["v812"]["pass"],
            "mss": [v812_summary.get("mss_after_holder"), v812_summary.get("mss_after_companion")],
            "mdm3": [v812_summary.get("mdm3_after_holder"), v812_summary.get("mdm3_after_companion")],
            "markers": {
                "qrtr_rx": int_value(v812_markers.get("qrtr_rx")),
                "qrtr_tx": int_value(v812_markers.get("qrtr_tx")),
                "sysmon_qmi": int_value(v812_markers.get("sysmon_qmi")),
                "service_notifier": int_value(v812_markers.get("service_notifier")),
                "wlan_pd": int_value(v812_markers.get("wlan_pd")),
                "wlfw": int_value(v812_markers.get("wlfw")),
                "bdf": int_value(v812_markers.get("bdf")),
                "wlan0": int_value(v812_markers.get("wlan0")),
                "kernel_warning": int_value(v812_markers.get("kernel_warning")),
            },
            "service69_events": int_value(v812_qrtr.get("service_events")),
            "timeouts": int_value(v812_qrtr.get("timeouts")),
            "qmi_attempted": int_value(v812_qrtr.get("qmi_attempted")),
        },
        "prior_classifiers": {
            "v811_decision": inputs["v811"]["decision"],
            "v785_decision": inputs["v785"]["decision"],
            "v783_decision": inputs["v783"]["decision"],
            "v739_decision": inputs["v739"]["decision"],
            "v785_checks": v785_checks if isinstance(v785_checks, list) else [],
            "v783_checks": v783_checks if isinstance(v783_checks, list) else [],
            "v739_checks": v739_checks if isinstance(v739_checks, list) else [],
        },
        "android_vs_native_v626": {
            "android": {
                "sysmon_modem": int_value(android_counts.get("sysmon_modem")),
                "sysmon_esoc0": int_value(android_counts.get("sysmon_esoc0")),
                "sysmon_adsp": int_value(android_counts.get("sysmon_adsp")),
                "sysmon_cdsp": int_value(android_counts.get("sysmon_cdsp")),
                "sysmon_slpi": int_value(android_counts.get("sysmon_slpi")),
                "service_notifier_180": int_value(android_counts.get("service_notifier_180")),
                "service_notifier_74": int_value(android_counts.get("service_notifier_74")),
                "wlan_pd": int_value(android_counts.get("wlan_pd")),
                "wlfw_start": int_value(android_counts.get("wlfw_start")),
                "bdf_regdb": int_value(android_counts.get("bdf_regdb")),
                "wlan0": int_value(android_counts.get("wlan0")),
            },
            "native": {
                "sysmon_modem": int_value(native_counts.get("sysmon_modem")),
                "sysmon_esoc0": int_value(native_counts.get("sysmon_esoc0")),
                "sysmon_adsp": int_value(native_counts.get("sysmon_adsp")),
                "sysmon_cdsp": int_value(native_counts.get("sysmon_cdsp")),
                "sysmon_slpi": int_value(native_counts.get("sysmon_slpi")),
                "service_notifier_180": int_value(native_counts.get("service_notifier_180")),
                "service_notifier_74": int_value(native_counts.get("service_notifier_74")),
                "wlan_pd": int_value(native_counts.get("wlan_pd")),
                "wlfw_start": int_value(native_counts.get("wlfw_start")),
                "bdf_regdb": int_value(native_counts.get("bdf_regdb")),
                "wlan0": int_value(native_counts.get("wlan0")),
                "mdm3_after_companion": v626_native.get("mdm3_after_companion"),
                "mss_after_companion": v626_native.get("mss_after_companion"),
            },
            "deltas_ms": as_dict(v626_android.get("deltas_ms")),
        },
    }


def check_detail_contains(checks: list[Any], needle: str) -> bool:
    for check in checks:
        if not isinstance(check, dict):
            continue
        detail = str(check.get("detail", ""))
        name = str(check.get("name", ""))
        if needle in detail or needle in name:
            return True
    return False


def build_checks(command: str, analysis: dict[str, Any]) -> list[dict[str, Any]]:
    if command == "plan":
        return [{
            "name": "plan-only",
            "status": "pass",
            "detail": "host-only classifier plan; no device command executed",
            "next_step": "run V813 host-only classifier",
        }]
    inputs = analysis["inputs"]
    current = analysis["v812_current"]
    markers = current["markers"]
    prior = analysis["prior_classifiers"]
    v626 = analysis["android_vs_native_v626"]
    android = v626["android"]
    native = v626["native"]
    v785_checks = prior["v785_checks"]
    v783_checks = prior["v783_checks"]
    all_inputs_ready = all(inputs[name]["pass"] for name in ("v812", "v811", "v785", "v783", "v626", "v739"))
    current_sysmon_gap = (
        inputs["v812"]["decision"] == "v812-sysmon-without-service69"
        and markers["sysmon_qmi"] > 0
        and markers["wlan_pd"] == 0
        and markers["wlfw"] == 0
        and markers["wlan0"] == 0
        and current["service69_events"] == 0
        and current["timeouts"] == 0
    )
    memshare_demoted = (
        inputs["v785"]["decision"] == "v785-memshare-common-nonfatal-sibling-sysmon-gap"
        and check_detail_contains(v785_checks, "same_requests=True")
        and check_detail_contains(v785_checks, "first=sysmon_slpi")
    )
    native_post_sysmon_gap = (
        inputs["v783"]["decision"] == "v783-mdm3-wlan-pd-gap-memshare-lead-classified"
        and check_detail_contains(v783_checks, "native_sysmon=1")
        and check_detail_contains(v783_checks, "native_service74=0")
    )
    android_sibling_positive = (
        android["sysmon_modem"] > 0
        and android["sysmon_esoc0"] > 0
        and android["sysmon_adsp"] > 0
        and android["sysmon_cdsp"] > 0
        and android["sysmon_slpi"] > 0
        and android["service_notifier_74"] > 0
        and android["wlan_pd"] > 0
        and android["wlfw_start"] > 0
    )
    native_sibling_absent = (
        native["sysmon_modem"] > 0
        and native["sysmon_esoc0"] == 0
        and native["sysmon_adsp"] == 0
        and native["sysmon_cdsp"] == 0
        and native["sysmon_slpi"] == 0
        and native["service_notifier_74"] == 0
        and native["wlan_pd"] == 0
        and native["wlfw_start"] == 0
    )
    return [
        {
            "name": "required-inputs",
            "status": "pass" if all_inputs_ready else "blocked",
            "detail": {name: {"decision": inputs[name]["decision"], "pass": inputs[name]["pass"]} for name in inputs},
            "next_step": "restore missing prior evidence before routing post-sysmon work",
        },
        {
            "name": "host-only-boundary",
            "status": "pass",
            "detail": "no device command, flash, reboot, HAL, scan/connect, credential use, DHCP, route, or ping",
            "next_step": "preserve V813 as a classifier only",
        },
        {
            "name": "current-v812-gap",
            "status": "pass" if current_sysmon_gap else "blocked",
            "detail": current,
            "next_step": "rerun V812 only if current evidence does not prove sysmon-without-service69",
        },
        {
            "name": "memshare-demoted",
            "status": "pass" if memshare_demoted else "blocked",
            "detail": {
                "v785_decision": inputs["v785"]["decision"],
                "evidence": "Android and native share memshare/CMA failures, but Android continues beyond them",
            },
            "next_step": "do not route next work to memshare-only retry",
        },
        {
            "name": "post-sysmon-native-gap",
            "status": "pass" if native_post_sysmon_gap else "blocked",
            "detail": {
                "v783_decision": inputs["v783"]["decision"],
                "evidence": "native has sysmon but lacks service74/180 continuation in V783 classifier",
            },
            "next_step": "target service-publication inputs instead of boot_wlan/qcwlanstate",
        },
        {
            "name": "android-sibling-sysmon-positive",
            "status": "pass" if android_sibling_positive else "blocked",
            "detail": android,
            "next_step": "refresh Android lower reference if sibling sysmon/service74 positive path is missing",
        },
        {
            "name": "native-sibling-sysmon-absent",
            "status": "pass" if native_sibling_absent else "blocked",
            "detail": native,
            "next_step": "if native sibling sysmon exists, update route away from this classifier",
        },
    ]


def decide(command: str, checks: list[dict[str, Any]]) -> tuple[str, bool, str, str]:
    if command == "plan":
        return (
            "v813-post-sysmon-publication-classifier-plan-ready",
            True,
            "plan-only; no device command executed",
            "run host-only classifier",
        )
    blocked = [check["name"] for check in checks if check["status"] == "blocked"]
    if blocked:
        return (
            "v813-post-sysmon-publication-classifier-blocked",
            False,
            "blocked by " + ", ".join(blocked),
            "restore or refresh required evidence before selecting next live gate",
        )
    return (
        "v813-sibling-sysmon-service-publication-precondition-selected",
        True,
        "V812 reaches QRTR/sysmon without service69; V785 demotes memshare as sole blocker; Android publishes sibling sysmon/service74/WLAN-PD while native lacks sibling sysmon/service74/WLFW",
        "V814 should isolate sibling sysmon/service-publication prerequisites below HAL/connect, without custom-kernel flash",
    )


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    analysis = build_analysis(args)
    checks = build_checks(args.command, analysis)
    decision, pass_ok, reason, next_step = decide(args.command, checks)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "cycle": "v813",
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "analysis": {
            "v812_current": analysis["v812_current"],
            "prior_classifiers": {
                key: value
                for key, value in analysis["prior_classifiers"].items()
                if not key.endswith("_checks")
            },
            "android_vs_native_v626": analysis["android_vs_native_v626"],
        },
        "inputs": {
            name: {
                "path": value["file"]["path"],
                "exists": value["file"]["exists"],
                "decision": value["decision"],
                "pass": value["pass"],
            }
            for name, value in analysis["inputs"].items()
        },
        "checks": checks,
        "device_commands_executed": False,
        "device_mutations": False,
        "custom_kernel_flash_executed": False,
        "boot_image_write_executed": False,
        "partition_write_executed": False,
        "reboot_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "forbidden_actions": FORBIDDEN_ACTIONS,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    check_rows = [
        [check["name"], check["status"], json.dumps(check["detail"], sort_keys=True), check["next_step"]]
        for check in manifest["checks"]
    ]
    input_rows = [
        [name, str(item["exists"]), str(item["pass"]), item["decision"], item["path"]]
        for name, item in manifest["inputs"].items()
    ]
    signal_rows = [
        ["v812_current", json.dumps(manifest["analysis"]["v812_current"], sort_keys=True)],
        ["v626_android", json.dumps(manifest["analysis"]["android_vs_native_v626"]["android"], sort_keys=True)],
        ["v626_native", json.dumps(manifest["analysis"]["android_vs_native_v626"]["native"], sort_keys=True)],
    ]
    return "\n".join([
        "# V813 Post-Sysmon Publication Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        "",
        "## Inputs",
        "",
        markdown_table(["input", "exists", "pass", "decision", "path"], input_rows),
        "",
        "## Checks",
        "",
        markdown_table(["check", "status", "detail", "next"], check_rows),
        "",
        "## Signals",
        "",
        markdown_table(["signal", "value"], signal_rows),
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

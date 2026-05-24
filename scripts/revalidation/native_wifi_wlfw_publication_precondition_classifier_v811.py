#!/usr/bin/env python3
"""V811 host-only WLFW service69 publication precondition classifier."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v811-wlfw-publication-precondition-classifier")
DEFAULT_V810_MANIFEST = Path("tmp/wifi/v810-register-probe-wlfw-fwready-classifier/manifest.json")
DEFAULT_V808_MANIFEST = Path("tmp/wifi/v808-overlap-companion-boot-wlan/manifest.json")
DEFAULT_V739_MANIFEST = Path("tmp/wifi/v739-mdm3-wlanpd-delta/manifest.json")
DEFAULT_V626_MANIFEST = Path("tmp/wifi/v626-post-180-publication-classifier/manifest.json")
DEFAULT_V731_MANIFEST = Path("tmp/wifi/v731-firmware-mounted-modem-holder/manifest.json")
DEFAULT_V733_MANIFEST = Path("tmp/wifi/v733-holder-lower-companion/manifest.json")
DEFAULT_V735_MANIFEST = Path("tmp/wifi/v735-current-cnss-only-observer/manifest.json")
DEFAULT_V738_MANIFEST = Path("tmp/wifi/v738-modem-wlan-mhi-observer/manifest.json")

FORBIDDEN_ACTIONS = (
    "device command",
    "custom kernel flash or boot image write",
    "partition write or reboot",
    "Wi-Fi HAL, wificond, supplicant, or hostapd start",
    "Wi-Fi scan/connect/link-up",
    "credential use",
    "DHCP, route change, or external ping",
    "boot_wlan or qcwlanstate write",
    "esoc0 open or subsystem state write",
    "bind/unbind, driver_override, or module load/unload",
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v810-manifest", type=Path, default=DEFAULT_V810_MANIFEST)
    parser.add_argument("--v808-manifest", type=Path, default=DEFAULT_V808_MANIFEST)
    parser.add_argument("--v739-manifest", type=Path, default=DEFAULT_V739_MANIFEST)
    parser.add_argument("--v626-manifest", type=Path, default=DEFAULT_V626_MANIFEST)
    parser.add_argument("--v731-manifest", type=Path, default=DEFAULT_V731_MANIFEST)
    parser.add_argument("--v733-manifest", type=Path, default=DEFAULT_V733_MANIFEST)
    parser.add_argument("--v735-manifest", type=Path, default=DEFAULT_V735_MANIFEST)
    parser.add_argument("--v738-manifest", type=Path, default=DEFAULT_V738_MANIFEST)
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


def get_nested(payload: dict[str, Any], *keys: str, default: Any = None) -> Any:
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


def manifest_summary(label: str, path: Path) -> dict[str, Any]:
    entry = load_json(path)
    data = entry["data"]
    return {
        "label": label,
        "file": entry["file"],
        "decision": data.get("decision", ""),
        "pass": bool(data.get("pass")),
        "reason": data.get("reason", ""),
        "data": data,
    }


def marker_counts(manifest: dict[str, Any]) -> dict[str, int]:
    counts = get_nested(manifest, "live", "markers", "counts", default={})
    counts = counts if isinstance(counts, dict) else {}
    return {str(key): int_value(value) for key, value in counts.items()}


def summarize_native_run(item: dict[str, Any]) -> dict[str, Any]:
    data = item["data"]
    counts = marker_counts(data)
    qrtr = get_nested(data, "live", "qrtr_readback", default={})
    qrtr = qrtr if isinstance(qrtr, dict) else {}
    return {
        "decision": data.get("decision", ""),
        "pass": bool(data.get("pass")),
        "mss_after_holder": get_nested(data, "live", "mss_after_holder"),
        "mss_after_companion": get_nested(data, "live", "mss_after_companion"),
        "mss_after_wait": get_nested(data, "live", "mss_after_wait"),
        "mdm3_after_holder": get_nested(data, "live", "mdm3_after_holder"),
        "mdm3_after_companion": get_nested(data, "live", "mdm3_after_companion"),
        "mdm3_after_wait": get_nested(data, "live", "mdm3_after_wait"),
        "counts": {
            "qrtr_rx": int_value(counts.get("qrtr_rx")),
            "qrtr_tx": int_value(counts.get("qrtr_tx")),
            "sysmon_qmi": int_value(counts.get("sysmon_qmi")),
            "service_notifier": int_value(counts.get("service_notifier")),
            "wlan_pd": int_value(counts.get("wlan_pd")),
            "wlfw": int_value(counts.get("wlfw")),
            "bdf": int_value(counts.get("bdf")),
            "mhi": int_value(counts.get("mhi")),
            "wlan0": int_value(counts.get("wlan0")),
        },
        "qrtr_service69_events": int_value(qrtr.get("service_events")),
        "qrtr_timeouts": int_value(qrtr.get("timeouts")),
        "qrtr_end_of_list": int_value(qrtr.get("end_of_list")),
    }


def build_analysis(args: argparse.Namespace) -> dict[str, Any]:
    inputs = {
        "v810": manifest_summary("v810", args.v810_manifest),
        "v808": manifest_summary("v808", args.v808_manifest),
        "v739": manifest_summary("v739", args.v739_manifest),
        "v626": manifest_summary("v626", args.v626_manifest),
        "v731": manifest_summary("v731", args.v731_manifest),
        "v733": manifest_summary("v733", args.v733_manifest),
        "v735": manifest_summary("v735", args.v735_manifest),
        "v738": manifest_summary("v738", args.v738_manifest),
    }
    v739_data = inputs["v739"]["data"]
    android_v590 = get_nested(v739_data, "android_v590_summary", default={})
    android_v590 = android_v590 if isinstance(android_v590, dict) else {}
    android_v611 = get_nested(v739_data, "android_v611_summary", default={})
    android_v611 = android_v611 if isinstance(android_v611, dict) else {}
    android_v622 = get_nested(v739_data, "android_v622_summary", default={})
    android_v622 = android_v622 if isinstance(android_v622, dict) else {}
    android_counts = android_v622.get("counts") if isinstance(android_v622.get("counts"), dict) else {}
    v738_summary = get_nested(v739_data, "v738_summary", default={})
    v738_summary = v738_summary if isinstance(v738_summary, dict) else {}
    v626_native = get_nested(inputs["v626"]["data"], "native", default={})
    v626_native = v626_native if isinstance(v626_native, dict) else {}
    v626_qrtr = v626_native.get("qrtr_readback") if isinstance(v626_native.get("qrtr_readback"), dict) else {}
    v808_counts = marker_counts(inputs["v808"]["data"])
    native_runs = {
        name: summarize_native_run(inputs[name])
        for name in ("v731", "v733", "v735", "v738")
    }
    return {
        "inputs": inputs,
        "android_reference": {
            "v739_decision": inputs["v739"]["decision"],
            "v739_pass": inputs["v739"]["pass"],
            "v590_mss_state": android_v590.get("mss_state"),
            "v590_mdm3_state": android_v590.get("mdm3_state"),
            "v611_mss_state": android_v611.get("mss_state"),
            "v611_mdm3_state": android_v611.get("mdm3_state"),
            "v622_mss_state": android_v622.get("mss_state"),
            "v622_mdm3_state": android_v622.get("mdm3_state"),
            "v622_has_service_notifier_180": bool(android_v622.get("has_service_notifier_180")),
            "v622_has_service_notifier_74": bool(android_v622.get("has_service_notifier_74")),
            "v622_has_wlan_pd": bool(android_v622.get("has_wlan_pd")),
            "v622_counts": {
                "wlfw_start": int_value(android_counts.get("wlfw_start")),
                "bdf_regdb": int_value(android_counts.get("bdf_regdb")),
                "bdf_bdwlan": int_value(android_counts.get("bdf_bdwlan")),
                "wlan0": int_value(android_counts.get("wlan0")),
            },
        },
        "native_reference": {
            "v626_mss_after_companion": v626_native.get("mss_after_companion"),
            "v626_mdm3_after_companion": v626_native.get("mdm3_after_companion"),
            "v626_service69_events": int_value(v626_qrtr.get("service_events")),
            "v626_qrtr_timeouts": int_value(v626_qrtr.get("timeouts")),
            "v626_qrtr_end_of_list": int_value(v626_qrtr.get("end_of_list")),
            "v738_mss_after_companion": v738_summary.get("mss_after_companion"),
            "v738_mdm3_after_companion": v738_summary.get("mdm3_after_companion"),
            "v738_service69_events": int_value(v738_summary.get("service69_events")),
            "v738_mhi_devices_count": int_value(v738_summary.get("mhi_devices_count")),
            "native_runs": native_runs,
        },
        "current_overlap": {
            "v808_decision": inputs["v808"]["decision"],
            "v808_pass": inputs["v808"]["pass"],
            "provider_first_context_executed": bool(inputs["v808"]["data"].get("provider_first_context_executed")),
            "boot_wlan_write_executed": bool(inputs["v808"]["data"].get("boot_wlan_write_executed")),
            "counts": {
                "service_notifier": int_value(v808_counts.get("service_notifier")),
                "wlan_pd": int_value(v808_counts.get("wlan_pd")),
                "wlfw": int_value(v808_counts.get("wlfw")),
                "fw_ready": int_value(v808_counts.get("fw_ready")),
                "bdf": int_value(v808_counts.get("bdf")),
                "mhi": int_value(v808_counts.get("mhi")),
                "wlan0": int_value(v808_counts.get("wlan0")),
            },
        },
    }


def build_checks(command: str, analysis: dict[str, Any]) -> list[dict[str, Any]]:
    if command == "plan":
        return [{
            "name": "plan-only",
            "status": "pass",
            "detail": "host-only WLFW precondition classifier; no device command or Wi-Fi action",
            "next_step": "run V811 host-only classifier",
        }]
    inputs = analysis["inputs"]
    android = analysis["android_reference"]
    native = analysis["native_reference"]
    current = analysis["current_overlap"]
    current_counts = current["counts"]
    native_runs = native["native_runs"]
    native_mdm3_states = [
        state
        for run in native_runs.values()
        if run.get("pass")
        for state in (run.get("mdm3_after_companion"), run.get("mdm3_after_wait"), run.get("mdm3_after_holder"))
        if state
    ]
    native_all_mdm3_offlining = bool(native_mdm3_states) and all(state == "OFFLINING" for state in native_mdm3_states)
    native_all_wlfw_absent = all(
        int_value(run["counts"].get("wlfw")) == 0 and int_value(run.get("qrtr_service69_events")) == 0
        for run in native_runs.values()
        if run.get("pass")
    )
    return [
        {
            "name": "v810-input-ready",
            "status": "pass"
            if inputs["v810"]["pass"] and inputs["v810"]["decision"] == "v810-register-probe-gated-by-missing-wlfw-fwready"
            else "blocked",
            "detail": {"decision": inputs["v810"]["decision"], "pass": inputs["v810"]["pass"]},
            "next_step": "complete V810 before V811",
        },
        {
            "name": "android-wlanpd-wlfw-positive-reference",
            "status": "pass"
            if inputs["v739"]["pass"]
            and (
                (android.get("v590_mss_state") == "ONLINE" and android.get("v590_mdm3_state") == "ONLINE")
                or (android.get("v611_mss_state") == "ONLINE" and android.get("v611_mdm3_state") == "ONLINE")
            )
            and android.get("v622_has_wlan_pd")
            and android["v622_counts"].get("wlfw_start")
            and android["v622_counts"].get("wlan0")
            else "blocked",
            "detail": android,
            "next_step": "refresh Android reference if WLAN-PD/WLFW positive path is not proven",
        },
        {
            "name": "native-mdm3-wlanpd-negative-reference",
            "status": "pass"
            if inputs["v739"]["pass"]
            and native.get("v738_mss_after_companion") == "ONLINE"
            and native.get("v738_mdm3_after_companion") == "OFFLINING"
            and int_value(native.get("v738_service69_events")) == 0
            and native_all_mdm3_offlining
            and native_all_wlfw_absent
            else "blocked",
            "detail": native,
            "next_step": "do not widen to HAL/connect until mdm3/WLAN-PD/WLFW advances in native",
        },
        {
            "name": "qrtr-readback-transport-clean-empty",
            "status": "pass"
            if inputs["v626"]["pass"]
            and int_value(native.get("v626_service69_events")) == 0
            and int_value(native.get("v626_qrtr_timeouts")) == 0
            and int_value(native.get("v626_qrtr_end_of_list")) > 0
            else "finding",
            "detail": {
                "v626_decision": inputs["v626"]["decision"],
                "service69_events": native.get("v626_service69_events"),
                "timeouts": native.get("v626_qrtr_timeouts"),
                "end_of_list": native.get("v626_qrtr_end_of_list"),
            },
            "next_step": "treat missing service69 as publication absence, not readback timeout",
        },
        {
            "name": "current-overlap-still-pre-wlfw",
            "status": "pass"
            if current.get("v808_pass")
            and current.get("provider_first_context_executed")
            and current_counts.get("service_notifier") > 0
            and not any(int_value(current_counts.get(name)) for name in ("wlan_pd", "wlfw", "fw_ready", "bdf", "mhi", "wlan0"))
            else "blocked",
            "detail": current,
            "next_step": "if service69/FW_READY appears, route to ICNSS-QMI/BDF classifier",
        },
        {
            "name": "no-live-or-widening-action",
            "status": "pass",
            "detail": {
                "v811_device_commands_executed": False,
                "wifi_hal_start_executed": False,
                "scan_connect_executed": False,
                "external_ping_executed": False,
            },
            "next_step": "keep next live gate below HAL/scan/connect and target mdm3/WLAN-PD/service69 publication",
        },
    ]


def decide(command: str, checks: list[dict[str, Any]]) -> tuple[str, bool, str, str]:
    if command == "plan":
        return (
            "v811-wlfw-publication-precondition-classifier-plan-ready",
            True,
            "plan-only; no device command executed",
            "run V811 host-only classifier",
        )
    blocked = [check["name"] for check in checks if check["status"] == "blocked"]
    if blocked:
        return (
            "v811-wlfw-publication-precondition-classifier-blocked",
            False,
            "blocked by " + ", ".join(blocked),
            "refresh missing host evidence before another live gate",
        )
    return (
        "v811-wlfw-publication-precondition-mdm3-wlanpd-gap-selected",
        True,
        "Android reaches mdm3 ONLINE plus WLAN-PD/WLFW/BDF/wlan0, while native repeatedly reaches mss/QRTR/sysmon/service-notifier surfaces with mdm3 OFFLINING and clean-empty service69 readback; the next blocker is mdm3/WLAN-PD/WLFW publication preconditions, not qcwlanstate/register/HAL/connect",
        "V812 should plan the smallest below-HAL live observer for mdm3/WLAN-PD/service69 publication preconditions using current V401/V490/firmware mounts and no scan/connect",
    )


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    analysis = build_analysis(args)
    checks = build_checks(args.command, analysis)
    decision, pass_ok, reason, next_step = decide(args.command, checks)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "cycle": "v811",
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "analysis": {
            "android_reference": analysis["android_reference"],
            "native_reference": analysis["native_reference"],
            "current_overlap": analysis["current_overlap"],
        },
        "inputs": {
            name: {"path": item["file"]["path"], "exists": item["file"]["exists"], "decision": item["decision"], "pass": item["pass"]}
            for name, item in analysis["inputs"].items()
        },
        "checks": checks,
        "device_commands_executed": False,
        "device_mutations": False,
        "custom_kernel_flash_executed": False,
        "boot_image_write_executed": False,
        "partition_write_executed": False,
        "reboot_executed": False,
        "boot_wlan_write_executed": False,
        "qcwlanstate_write_executed": False,
        "esoc0_access_executed": False,
        "bind_unbind_executed": False,
        "module_load_unload_executed": False,
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
    signal_rows = [
        ["Android reference", json.dumps(manifest["analysis"]["android_reference"], sort_keys=True)],
        ["Native reference", json.dumps(manifest["analysis"]["native_reference"], sort_keys=True)],
        ["Current overlap", json.dumps(manifest["analysis"]["current_overlap"], sort_keys=True)],
    ]
    input_rows = [
        [name, data["decision"], str(data["pass"]), data["path"]]
        for name, data in manifest["inputs"].items()
    ]
    return "\n".join([
        "# V811 WLFW Publication Precondition Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- custom_kernel_flash_executed: `{manifest['custom_kernel_flash_executed']}`",
        f"- wifi_hal_start_executed: `{manifest['wifi_hal_start_executed']}`",
        f"- scan_connect_executed: `{manifest['scan_connect_executed']}`",
        f"- external_ping_executed: `{manifest['external_ping_executed']}`",
        "",
        "## Checks",
        "",
        markdown_table(["check", "status", "detail", "next"], check_rows),
        "",
        "## Evidence Signals",
        "",
        markdown_table(["source", "signals"], signal_rows),
        "",
        "## Inputs",
        "",
        markdown_table(["input", "decision", "pass", "path"], input_rows),
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
    print(f"custom_kernel_flash_executed: {manifest['custom_kernel_flash_executed']}")
    print(f"wifi_hal_start_executed: {manifest['wifi_hal_start_executed']}")
    print(f"scan_connect_executed: {manifest['scan_connect_executed']}")
    print(f"credential_use_executed: {manifest['credential_use_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""V809 host-only ICNSS modules-not-initialized source classifier.

V808 proved that a true provider-first companion overlap with the bounded
``boot_wlan`` trigger still reaches only the HDD/qcwlanstate surface.  This
classifier maps the repeated ``icnss: Modules not initialized just return``
runtime evidence to the Samsung OSRC source path and chooses the next smallest
pre-WLFW blocker without touching the device.
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


DEFAULT_OUT_DIR = Path("tmp/wifi/v809-icnss-modules-not-initialized-source-classifier")
DEFAULT_SOURCE_ROOT = Path("tmp/wifi/v766-icnss-qcacld-patch-apply-build/source")
DEFAULT_V808_MANIFEST = Path("tmp/wifi/v808-overlap-companion-boot-wlan/manifest.json")
DEFAULT_V808_DMESG = Path("tmp/wifi/v808-overlap-companion-boot-wlan/native/dmesg-delta.txt")
DEFAULT_V808_HELPER = Path("tmp/wifi/v808-overlap-companion-boot-wlan/native/overlap-helper-boot-wlan.txt")
DEFAULT_V751_MANIFEST = Path("tmp/wifi/v751-icnss-module-init-classifier/manifest.json")
DEFAULT_V752_MANIFEST = Path("tmp/wifi/v752-cnss-then-boot-wlan/manifest.json")
DEFAULT_V795_MANIFEST = Path("tmp/wifi/v795-lower-window-mdm3-esoc-observer/manifest.json")
DEFAULT_V797_MANIFEST = Path("tmp/wifi/v797-pil-trace-payload/manifest.json")

ICNSS = "drivers/soc/qcom/icnss.c"
ICNSS_QMI = "drivers/soc/qcom/icnss_qmi.c"
HDD_MAIN = "drivers/net/wireless/qualcomm/wcn39xx/qcacld-3.0/core/hdd/src/wlan_hdd_main.c"
HDD_DRIVER_OPS = "drivers/net/wireless/qualcomm/wcn39xx/qcacld-3.0/core/hdd/src/wlan_hdd_driver_ops.c"
PLD_SNOC = "drivers/net/wireless/qualcomm/wcn39xx/qcacld-3.0/core/pld/src/pld_snoc.c"

READ_LIMIT_BYTES = 8 * 1024 * 1024

ANCHORS: dict[str, tuple[str, str]] = {
    "icnss_driver_status_enum": (ICNSS, r"enum driver_modules_status"),
    "icnss_status_initial_uninitialized": (ICNSS, r"current_driver_status\s*=\s*DRIVER_MODULES_UNINITIALIZED"),
    "icnss_status_exported_setter": (ICNSS, r"void cnss_sysfs_update_driver_status"),
    "icnss_status_setter_assigns": (ICNSS, r"current_driver_status\s*=\s*new_status"),
    "icnss_status_setter_exported": (ICNSS, r"EXPORT_SYMBOL\(cnss_sysfs_update_driver_status\)"),
    "icnss_qcwlanstate_show": (ICNSS, r"static ssize_t show_qcwlanstate"),
    "icnss_qcwlanstate_uninitialized_log": (ICNSS, r"Modules not initialized just return"),
    "icnss_qcwlanstate_enabled_log": (ICNSS, r"Modules enabled"),
    "hdd_status_bridge": (HDD_MAIN, r"void hdd_sysfs_update_driver_status"),
    "hdd_status_bridge_calls_icnss": (HDD_MAIN, r"cnss_sysfs_update_driver_status\(status"),
    "hdd_start_modules": (HDD_MAIN, r"int hdd_wlan_start_modules"),
    "hdd_start_sets_enabled": (HDD_MAIN, r"hdd_ctx->driver_status\s*=\s*DRIVER_MODULES_ENABLED"),
    "hdd_start_publishes_enabled": (HDD_MAIN, r"hdd_sysfs_update_driver_status\(DRIVER_MODULES_ENABLED\)"),
    "hdd_driver_load": (HDD_MAIN, r"static int hdd_driver_load"),
    "hdd_driver_load_qcwlanstate_before_pld": (HDD_MAIN, r"before qcwlanstate_create"),
    "hdd_driver_load_pld_init": (HDD_MAIN, r"before pld_init"),
    "hdd_driver_load_register_driver": (HDD_MAIN, r"wlan_hdd_register_driver\(\)"),
    "hdd_driver_load_loaded_marker": (HDD_MAIN, r"driver loaded"),
    "hdd_wlan_boot_cb": (HDD_MAIN, r"static ssize_t wlan_boot_cb"),
    "hdd_wlan_boot_cb_calls_load": (HDD_MAIN, r"if \(hdd_driver_load\(\)\)"),
    "hdd_register_driver": (HDD_DRIVER_OPS, r"int wlan_hdd_register_driver"),
    "hdd_register_driver_calls_pld": (HDD_DRIVER_OPS, r"return pld_register_driver\(&wlan_drv_ops\)"),
    "pld_snoc_register_driver": (PLD_SNOC, r"int pld_snoc_register_driver"),
    "pld_snoc_calls_icnss": (PLD_SNOC, r"return icnss_register_driver\(&pld_snoc_ops\)"),
    "icnss_register_driver": (ICNSS, r"int __icnss_register_driver"),
    "icnss_register_driver_event": (ICNSS, r"icnss_driver_event_post\(ICNSS_DRIVER_EVENT_REGISTER_DRIVER"),
    "icnss_fw_ready_event": (ICNSS, r"static int icnss_driver_event_fw_ready_ind"),
    "icnss_fw_ready_log": (ICNSS, r"WLAN FW is ready"),
    "icnss_fw_ready_calls_probe": (ICNSS, r"icnss_call_driver_probe\(penv\)"),
    "icnss_probe_calls_hdd": (ICNSS, r"priv->ops->probe\(&priv->pdev->dev\)"),
    "wlfw_new_server": (ICNSS_QMI, r"static int wlfw_new_server"),
    "wlfw_new_server_posts_arrive": (ICNSS_QMI, r"ICNSS_DRIVER_EVENT_SERVER_ARRIVE"),
    "icnss_qmi_connected_log": (ICNSS_QMI, r"QMI Server Connected"),
}

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
    parser.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE_ROOT)
    parser.add_argument("--v808-manifest", type=Path, default=DEFAULT_V808_MANIFEST)
    parser.add_argument("--v808-dmesg", type=Path, default=DEFAULT_V808_DMESG)
    parser.add_argument("--v808-helper", type=Path, default=DEFAULT_V808_HELPER)
    parser.add_argument("--v751-manifest", type=Path, default=DEFAULT_V751_MANIFEST)
    parser.add_argument("--v752-manifest", type=Path, default=DEFAULT_V752_MANIFEST)
    parser.add_argument("--v795-manifest", type=Path, default=DEFAULT_V795_MANIFEST)
    parser.add_argument("--v797-manifest", type=Path, default=DEFAULT_V797_MANIFEST)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def resolve(path: Path) -> Path:
    return path if path.is_absolute() else repo_path(path)


def safe_read(path: Path) -> tuple[str, dict[str, Any]]:
    resolved = resolve(path)
    info: dict[str, Any] = {"path": str(resolved), "exists": resolved.exists()}
    if not resolved.exists() or not resolved.is_file():
        return "", info
    data = resolved.read_bytes()[:READ_LIMIT_BYTES]
    info.update({
        "is_file": True,
        "size": resolved.stat().st_size,
        "bytes_read": len(data),
        "truncated": resolved.stat().st_size > len(data),
    })
    return data.decode("utf-8", errors="replace"), info


def load_json(path: Path) -> dict[str, Any]:
    text, info = safe_read(path)
    if not text:
        return {"file": info, "data": {}}
    try:
        payload = json.loads(text)
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


def line_of(text: str, pattern: str) -> int | None:
    regex = re.compile(pattern)
    for index, line in enumerate(text.splitlines(), start=1):
        if regex.search(line):
            return index
    return None


def count_literal(text: str, pattern: str) -> int:
    return text.count(pattern)


def count_regex(text: str, pattern: str) -> int:
    return len(re.findall(pattern, text))


def load_sources(source_root: Path) -> dict[str, dict[str, Any]]:
    root = resolve(source_root)
    loaded: dict[str, dict[str, Any]] = {}
    for relative in sorted(set(path for path, _pattern in ANCHORS.values())):
        text, info = safe_read(root / relative)
        loaded[relative] = {"text": text, "file": info}
    return loaded


def source_order_ok(source: dict[str, Any], first: str, second: str) -> bool:
    anchors = source.get("anchors") if isinstance(source.get("anchors"), dict) else {}
    first_line = get_nested(anchors, first, "line")
    second_line = get_nested(anchors, second, "line")
    return isinstance(first_line, int) and isinstance(second_line, int) and first_line < second_line


def analyze_source(args: argparse.Namespace) -> dict[str, Any]:
    sources = load_sources(args.source_root)
    anchors: dict[str, dict[str, Any]] = {}
    for name, (relative, pattern) in ANCHORS.items():
        text = str(sources.get(relative, {}).get("text") or "")
        anchors[name] = {
            "source": relative,
            "line": line_of(text, pattern),
            "pattern": pattern,
        }
    source = {
        "source_root": str(resolve(args.source_root)),
        "source_files": {relative: item["file"] for relative, item in sources.items()},
        "anchors": anchors,
    }
    derived = {
        "qcwlanstate_is_icnss_status_mirror": all(
            anchors[name]["line"]
            for name in (
                "icnss_status_initial_uninitialized",
                "icnss_status_exported_setter",
                "icnss_qcwlanstate_show",
                "icnss_qcwlanstate_uninitialized_log",
            )
        ),
        "hdd_publishes_enabled_status": all(
            anchors[name]["line"]
            for name in (
                "hdd_status_bridge_calls_icnss",
                "hdd_start_sets_enabled",
                "hdd_start_publishes_enabled",
            )
        ),
        "qcwlanstate_created_before_pld_register_and_driver_loaded": source_order_ok(
            source, "hdd_driver_load_qcwlanstate_before_pld", "hdd_driver_load_register_driver"
        )
        and source_order_ok(source, "hdd_driver_load_register_driver", "hdd_driver_load_loaded_marker"),
        "boot_wlan_invokes_hdd_driver_load": all(
            anchors[name]["line"]
            for name in ("hdd_wlan_boot_cb", "hdd_wlan_boot_cb_calls_load", "hdd_driver_load")
        ),
        "pld_register_chains_to_icnss_register": all(
            anchors[name]["line"]
            for name in (
                "hdd_register_driver_calls_pld",
                "pld_snoc_calls_icnss",
                "icnss_register_driver_event",
            )
        ),
        "wlfw_arrival_and_fw_ready_are_before_hdd_probe": all(
            anchors[name]["line"]
            for name in (
                "wlfw_new_server_posts_arrive",
                "icnss_qmi_connected_log",
                "icnss_fw_ready_log",
                "icnss_fw_ready_calls_probe",
                "icnss_probe_calls_hdd",
            )
        ),
    }
    source["derived"] = derived
    return source


def analyze_v808(args: argparse.Namespace) -> dict[str, Any]:
    manifest_entry = load_json(args.v808_manifest)
    manifest = manifest_entry["data"]
    dmesg_text, dmesg_info = safe_read(args.v808_dmesg)
    helper_text, helper_info = safe_read(args.v808_helper)
    markers = get_nested(manifest, "live", "markers", "counts", default={})
    markers = markers if isinstance(markers, dict) else {}
    helper_result = get_nested(manifest, "live", "helper_result", default={})
    helper_result = helper_result if isinstance(helper_result, dict) else {}
    forbidden = {
        "wifi_hal_start_executed": bool(manifest.get("wifi_hal_start_executed")),
        "scan_connect_executed": bool(manifest.get("scan_connect_executed")),
        "credential_use_executed": bool(manifest.get("credential_use_executed")),
        "dhcp_route_executed": bool(manifest.get("dhcp_route_executed")),
        "external_ping_executed": bool(manifest.get("external_ping_executed")),
        "custom_kernel_flash_executed": bool(manifest.get("custom_kernel_flash_executed")),
        "boot_image_write_executed": bool(manifest.get("boot_image_write_executed")),
    }
    text_counts = {
        "dmesg_modules_not_initialized": count_literal(dmesg_text, "icnss: Modules not initialized just return"),
        "dmesg_wlan_loading": count_literal(dmesg_text, "wlan: Loading driver"),
        "dmesg_driver_loaded": count_literal(dmesg_text, "driver loaded"),
        "dmesg_icnss_qmi_connected": count_literal(dmesg_text, "QMI Server Connected"),
        "dmesg_fw_ready": count_literal(dmesg_text, "WLAN FW is ready"),
        "helper_modules_not_initialized": count_literal(helper_text, "icnss: Modules not initialized just return"),
        "helper_wlan_loading": count_literal(helper_text, "wlan: Loading driver"),
        "helper_driver_loaded": count_literal(helper_text, "driver loaded"),
        "helper_qcwlanstate_off": count_regex(helper_text, r"qcwlanstate[^\n]*=OFF"),
    }
    signals = {
        "provider_first_context_executed": bool(manifest.get("provider_first_context_executed")),
        "boot_wlan_write_executed": bool(manifest.get("boot_wlan_write_executed")),
        "helper_alive_before_boot": bool(get_nested(manifest, "live", "helper_alive_before_boot", default=False)),
        "helper_gate_seen": bool(get_nested(manifest, "live", "helper_gate_seen", default=False)),
        "cnss_retry_started": bool(helper_result.get("cnss_retry_started")),
        "overlap_ok": bool(get_nested(manifest, "live", "overlap_ok", default=False)),
        "wlan_loading": int_value(markers.get("wlan_loading")),
        "wlan_driver_loaded": int_value(markers.get("wlan_driver_loaded")),
        "qcwlanstate": int_value(markers.get("qcwlanstate")),
        "icnss_qmi_connected": int_value(markers.get("icnss_qmi_connected")),
        "fw_ready": int_value(markers.get("fw_ready")),
        "wlfw": int_value(markers.get("wlfw")),
        "bdf": int_value(markers.get("bdf")),
        "wiphy": int_value(markers.get("wiphy")),
        "wlan0": int_value(markers.get("wlan0")),
        "service_notifier": int_value(markers.get("service_notifier")),
        "qrtr_rx": int_value(markers.get("qrtr_rx")),
        "qrtr_tx": int_value(markers.get("qrtr_tx")),
    }
    return {
        "manifest": manifest_entry["file"],
        "dmesg": dmesg_info,
        "helper": helper_info,
        "decision": manifest.get("decision", ""),
        "pass": bool(manifest.get("pass")),
        "reason": manifest.get("reason", ""),
        "signals": signals,
        "text_counts": text_counts,
        "forbidden_flags": forbidden,
        "forbidden_clean": not any(forbidden.values()),
    }


def summarize_manifest(label: str, path: Path) -> dict[str, Any]:
    entry = load_json(path)
    data = entry["data"]
    return {
        "label": label,
        "file": entry["file"],
        "decision": data.get("decision", ""),
        "pass": bool(data.get("pass")),
        "reason": data.get("reason", ""),
    }


def analyze_prior(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "v751": summarize_manifest("v751", args.v751_manifest),
        "v752": summarize_manifest("v752", args.v752_manifest),
        "v795": summarize_manifest("v795", args.v795_manifest),
        "v797": summarize_manifest("v797", args.v797_manifest),
    }


def build_checks(command: str, source: dict[str, Any], v808: dict[str, Any], prior: dict[str, Any]) -> list[dict[str, Any]]:
    if command == "plan":
        return [{
            "name": "plan-only",
            "status": "pass",
            "detail": "host-only source/evidence classifier; no device command or Wi-Fi action",
            "next_step": "run V809 host-only classifier",
        }]
    derived = source.get("derived") if isinstance(source.get("derived"), dict) else {}
    signals = v808.get("signals") if isinstance(v808.get("signals"), dict) else {}
    text_counts = v808.get("text_counts") if isinstance(v808.get("text_counts"), dict) else {}
    prior_ready = all(bool((prior.get(name) or {}).get("pass")) for name in ("v751", "v752", "v795", "v797"))
    absent_after_boot = not any(
        int_value(signals.get(name))
        for name in ("wlan_driver_loaded", "icnss_qmi_connected", "fw_ready", "wlfw", "bdf", "wiphy", "wlan0")
    )
    return [
        {
            "name": "source-status-path-present",
            "status": "pass"
            if derived.get("qcwlanstate_is_icnss_status_mirror")
            and derived.get("hdd_publishes_enabled_status")
            else "blocked",
            "detail": {
                "qcwlanstate_is_icnss_status_mirror": derived.get("qcwlanstate_is_icnss_status_mirror"),
                "hdd_publishes_enabled_status": derived.get("hdd_publishes_enabled_status"),
            },
            "next_step": "refresh staged Samsung OSRC source if status path anchors are missing",
        },
        {
            "name": "source-load-order-present",
            "status": "pass"
            if derived.get("boot_wlan_invokes_hdd_driver_load")
            and derived.get("qcwlanstate_created_before_pld_register_and_driver_loaded")
            else "blocked",
            "detail": {
                "boot_wlan_invokes_hdd_driver_load": derived.get("boot_wlan_invokes_hdd_driver_load"),
                "qcwlanstate_created_before_pld_register_and_driver_loaded": derived.get("qcwlanstate_created_before_pld_register_and_driver_loaded"),
            },
            "next_step": "recheck HDD source order before using qcwlanstate as a driver-loaded proxy",
        },
        {
            "name": "source-register-probe-chain-present",
            "status": "pass"
            if derived.get("pld_register_chains_to_icnss_register")
            and derived.get("wlfw_arrival_and_fw_ready_are_before_hdd_probe")
            else "blocked",
            "detail": {
                "pld_register_chains_to_icnss_register": derived.get("pld_register_chains_to_icnss_register"),
                "wlfw_arrival_and_fw_ready_are_before_hdd_probe": derived.get("wlfw_arrival_and_fw_ready_are_before_hdd_probe"),
            },
            "next_step": "classify PLD/ICNSS register/probe/WLFW gate from source before another live retry",
        },
        {
            "name": "v808-true-overlap-input",
            "status": "pass"
            if v808.get("pass")
            and v808.get("decision") == "v808-overlap-service69-still-absent"
            and signals.get("provider_first_context_executed")
            and signals.get("helper_alive_before_boot")
            and signals.get("boot_wlan_write_executed")
            else "blocked",
            "detail": {
                "decision": v808.get("decision"),
                "pass": v808.get("pass"),
                "provider_first_context_executed": signals.get("provider_first_context_executed"),
                "helper_alive_before_boot": signals.get("helper_alive_before_boot"),
                "boot_wlan_write_executed": signals.get("boot_wlan_write_executed"),
            },
            "next_step": "rerun/repair V808 only if true-overlap evidence is absent",
        },
        {
            "name": "v808-status-still-uninitialized",
            "status": "pass"
            if signals.get("wlan_loading")
            and signals.get("qcwlanstate")
            and text_counts.get("dmesg_modules_not_initialized")
            and absent_after_boot
            else "blocked",
            "detail": {
                "signals": signals,
                "text_counts": text_counts,
                "absent_after_boot": absent_after_boot,
            },
            "next_step": "if driver-loaded/FW_READY/netdev appeared, route to post-FW_READY classifier",
        },
        {
            "name": "prior-boundaries-consistent",
            "status": "pass" if prior_ready else "finding",
            "detail": {
                name: {"decision": item.get("decision"), "pass": item.get("pass")}
                for name, item in prior.items()
            },
            "next_step": "use prior boundaries as supporting evidence only; V808 remains primary",
        },
        {
            "name": "no-widening-or-live-action",
            "status": "pass" if v808.get("forbidden_clean") else "blocked",
            "detail": {
                "v809_device_commands_executed": False,
                "v809_device_mutations": False,
                "v808_forbidden_flags": v808.get("forbidden_flags"),
            },
            "next_step": "remove any HAL/scan/connect/credential/network action from this classifier",
        },
    ]


def decide(command: str, checks: list[dict[str, Any]]) -> tuple[str, bool, str, str]:
    if command == "plan":
        return (
            "v809-icnss-modules-not-initialized-source-classifier-plan-ready",
            True,
            "plan-only; no device command executed",
            "run V809 host-only source/evidence classifier",
        )
    blocked = [check["name"] for check in checks if check["status"] == "blocked"]
    if blocked:
        return (
            "v809-icnss-modules-not-initialized-source-classifier-blocked",
            False,
            "blocked by " + ", ".join(blocked),
            "clear host evidence/source blocker before selecting a live gate",
        )
    return (
        "v809-modules-not-initialized-source-mapped",
        True,
        "ICNSS qcwlanstate OFF is a source-level status mirror: current_driver_status remains below DRIVER_MODULES_ENABLED; V808 true-overlap reached wlan loading/qcwlanstate but not driver-loaded, ICNSS-QMI, FW_READY, BDF, wiphy, or wlan0",
        "V810 should classify the PLD/ICNSS register-to-WLFW/FW_READY boundary from source and existing evidence before any further live retry",
    )


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    source = analyze_source(args)
    v808 = analyze_v808(args)
    prior = analyze_prior(args)
    checks = build_checks(args.command, source, v808, prior)
    decision, pass_ok, reason, next_step = decide(args.command, checks)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "cycle": "v809",
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "inputs": {
            "source_root": str(resolve(args.source_root)),
            "v808_manifest": str(resolve(args.v808_manifest)),
            "v808_dmesg": str(resolve(args.v808_dmesg)),
            "v808_helper": str(resolve(args.v808_helper)),
            "v751_manifest": str(resolve(args.v751_manifest)),
            "v752_manifest": str(resolve(args.v752_manifest)),
            "v795_manifest": str(resolve(args.v795_manifest)),
            "v797_manifest": str(resolve(args.v797_manifest)),
        },
        "source": source,
        "v808": v808,
        "prior": prior,
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
        ["V808 decision", json.dumps({"decision": manifest["v808"].get("decision"), "pass": manifest["v808"].get("pass")}, sort_keys=True)],
        ["V808 signals", json.dumps(manifest["v808"].get("signals", {}), sort_keys=True)],
        ["V808 text counts", json.dumps(manifest["v808"].get("text_counts", {}), sort_keys=True)],
        ["Prior", json.dumps({
            name: {"decision": item.get("decision"), "pass": item.get("pass")}
            for name, item in manifest["prior"].items()
        }, sort_keys=True)],
    ]
    derived_rows = [[key, str(value)] for key, value in manifest["source"]["derived"].items()]
    anchor_rows = [
        [name, anchor["source"], str(anchor["line"]), anchor["pattern"]]
        for name, anchor in manifest["source"]["anchors"].items()
    ]
    return "\n".join([
        "# V809 ICNSS Modules-Not-Initialized Source Classifier",
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
        "## Source Derived Facts",
        "",
        markdown_table(["fact", "value"], derived_rows),
        "",
        "## Source Anchors",
        "",
        markdown_table(["anchor", "source", "line", "pattern"], anchor_rows),
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

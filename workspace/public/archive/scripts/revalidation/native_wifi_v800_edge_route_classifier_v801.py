#!/usr/bin/env python3
"""V801 host-only classifier for the V800 ICNSS edge gap.

This consumes V800, V752, and V720 evidence to avoid over-fitting on the
inactive qca6390 platform node. It does not contact the device.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v801-v800-edge-route-classifier")
DEFAULT_V800_MANIFEST = Path("tmp/wifi/v800-provider-first-icnss-edge-v124-live/manifest.json")
DEFAULT_V752_MANIFEST = Path("tmp/wifi/v752-cnss-then-boot-wlan/manifest.json")
DEFAULT_V720_MANIFEST = Path("tmp/wifi/v720-same-window-cnss2-observer-final-20260524-112922/manifest.json")
LATEST_POINTER = Path("tmp/wifi/latest-v801-v800-edge-route-classifier.txt")


@dataclass(frozen=True)
class Check:
    name: str
    status: str
    severity: str
    detail: str
    next_step: str


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v800-manifest", type=Path, default=DEFAULT_V800_MANIFEST)
    parser.add_argument("--v752-manifest", type=Path, default=DEFAULT_V752_MANIFEST)
    parser.add_argument("--v720-manifest", type=Path, default=DEFAULT_V720_MANIFEST)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    resolved = path if path.is_absolute() else repo_path(path)
    if not resolved.exists():
        return {"_file": str(resolved), "_exists": False}
    data = json.loads(resolved.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        data["_file"] = str(resolved)
        data["_exists"] = True
        return data
    return {"_file": str(resolved), "_exists": True, "_type": type(data).__name__}


def int_value(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def bool_value(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in {"1", "true", "yes", "pass"}
    return bool(value)


def edge_flag(edge: dict[str, Any], phase: str, key: str) -> bool:
    return bool_value(edge.get(f"wifi_icnss_edge.{phase}.{key}"))


def summarize_v800(v800: dict[str, Any]) -> dict[str, Any]:
    arm = v800.get("arm_v700") if isinstance(v800.get("arm_v700"), dict) else {}
    counts = arm.get("counts") if isinstance(arm.get("counts"), dict) else {}
    markers = arm.get("markers") if isinstance(arm.get("markers"), dict) else {}
    peripheral = arm.get("peripheral") if isinstance(arm.get("peripheral"), dict) else {}
    edge = v800.get("icnss_edge_surface") if isinstance(v800.get("icnss_edge_surface"), dict) else {}
    return {
        "exists": bool(v800.get("_exists")),
        "decision": v800.get("decision", ""),
        "pass": bool(v800.get("pass")),
        "helper_marker": v800.get("helper_marker", ""),
        "service180": int_value(counts.get("service_notifier_180")),
        "service74": int_value(counts.get("service_notifier_74")),
        "provider_query_exact": bool(arm.get("query_exact_match")),
        "initial_cnss_suppressed": bool(arm.get("initial_cnss_suppressed")),
        "cnss_retry_started": bool(arm.get("cnss_retry_started")),
        "cnss_retry_signal": ((peripheral.get("children") or {}).get("cnss_daemon_retry") or {}).get("signal", ""),
        "cnss_retry_result": peripheral.get("result", ""),
        "cnss_netlink": int_value(counts.get("cnss_daemon_netlink")),
        "cnss_cld80211": int_value(counts.get("cnss_daemon_cld80211")),
        "binder_fail": int_value(counts.get("binder_transaction_failed")) + int_value(counts.get("cnss_binder_transaction_failed")),
        "icnss_edge_captured": bool(v800.get("icnss_edge_captured")),
        "icnss_driver_bound_open": edge_flag(edge, "service74_open", "icnss_driver_link.exists"),
        "icnss_driver_bound_window": edge_flag(edge, "window", "icnss_driver_link.exists"),
        "qca6390_driver_bound_open": edge_flag(edge, "service74_open", "qca6390_driver_link.exists"),
        "qca6390_driver_bound_window": edge_flag(edge, "window", "qca6390_driver_link.exists"),
        "shutdown_wlan_open": edge_flag(edge, "service74_open", "shutdown_wlan.exists"),
        "shutdown_wlan_window": edge_flag(edge, "window", "shutdown_wlan.exists"),
        "wlan0_open": edge_flag(edge, "service74_open", "wlan0_netdev.exists"),
        "wlan0_window": edge_flag(edge, "window", "wlan0_netdev.exists"),
        "qmi_server_connected": int_value(counts.get("qmi_server_connected")),
        "wlfw": int_value(counts.get("wlfw_start")) + int_value(counts.get("wlfw_service_request")) + int_value(markers.get("wlfw")),
        "bdf": int_value(counts.get("bdf_regdb")) + int_value(counts.get("bdf_bdwlan")) + int_value(markers.get("bdf")),
        "wlan0": int_value(counts.get("wlan0")) + int_value(markers.get("wlan0")),
        "kernel_warning": int_value(counts.get("kernel_warning")) + int_value(markers.get("kernel_warning")),
        "wifi_hal_start_executed": bool(v800.get("wifi_hal_start_executed")),
        "scan_connect_executed": bool(v800.get("scan_connect_executed")),
        "external_ping_executed": bool(v800.get("external_ping_executed")),
    }


def summarize_v752(v752: dict[str, Any]) -> dict[str, Any]:
    live = v752.get("live") if isinstance(v752.get("live"), dict) else {}
    marker_counts = ((live.get("markers") or {}).get("counts") or {})
    return {
        "exists": bool(v752.get("_exists")),
        "decision": v752.get("decision", ""),
        "pass": bool(v752.get("pass")),
        "boot_wlan_write_executed": bool(v752.get("boot_wlan_write_executed")),
        "service_manager_start_executed": bool(v752.get("service_manager_start_executed")),
        "wifi_hal_start_executed": bool(v752.get("wifi_hal_start_executed")),
        "scan_connect_executed": bool(v752.get("scan_connect_executed")),
        "external_ping_executed": bool(v752.get("external_ping_executed")),
        "wlan_loading": int_value(marker_counts.get("wlan_loading")),
        "wlan_driver_loaded": int_value(marker_counts.get("wlan_driver_loaded")),
        "icnss_qmi_connected": int_value(marker_counts.get("icnss_qmi_connected")),
        "fw_ready": int_value(marker_counts.get("fw_ready")),
        "wlfw": int_value(marker_counts.get("wlfw")),
        "bdf": int_value(marker_counts.get("bdf")),
        "wlan0": int_value(marker_counts.get("wlan0")),
        "qca6390": int_value(marker_counts.get("qca6390")),
        "qcwlanstate_after": live.get("qcwlanstate_after", ""),
        "wiphy_after": bool(live.get("wiphy_after")),
        "wlan0_after": bool(live.get("wlan0_after")),
    }


def summarize_v720(v720: dict[str, Any]) -> dict[str, Any]:
    live = v720.get("live") if isinstance(v720.get("live"), dict) else {}
    v719 = live.get("v719") if isinstance(live.get("v719"), dict) else {}
    return {
        "exists": bool(v720.get("_exists")),
        "decision": v720.get("decision", ""),
        "pass": bool(v720.get("pass")),
        "v719_decision": v719.get("decision", ""),
        "v719_reason": v719.get("reason", ""),
    }


def build_analysis(args: argparse.Namespace) -> dict[str, Any]:
    v800 = load_json(args.v800_manifest)
    v752 = load_json(args.v752_manifest)
    v720 = load_json(args.v720_manifest)
    s800 = summarize_v800(v800)
    s752 = summarize_v752(v752)
    s720 = summarize_v720(v720)
    qca_absent_but_not_primary = (
        s800["icnss_driver_bound_window"]
        and not s800["qca6390_driver_bound_window"]
        and s752["wlan_loading"] > 0
        and s752["qca6390"] == 0
    )
    provider_boot_wlan_gap = (
        s800["service74"] > 0
        and s800["provider_query_exact"]
        and s800["cnss_retry_started"]
        and s752["boot_wlan_write_executed"]
        and s752["wlan_loading"] > 0
        and s752["wlan_driver_loaded"] == 0
    )
    return {
        "inputs": {
            "v800": {"path": v800.get("_file"), "exists": v800.get("_exists")},
            "v752": {"path": v752.get("_file"), "exists": v752.get("_exists")},
            "v720": {"path": v720.get("_file"), "exists": v720.get("_exists")},
        },
        "v800": s800,
        "v752": s752,
        "v720": s720,
        "derived": {
            "qca6390_unbound_is_not_primary_target": qca_absent_but_not_primary,
            "provider_context_and_boot_wlan_have_not_been_combined": provider_boot_wlan_gap,
            "wlan_driver_boundary_is_after_boot_wlan": s752["wlan_loading"] > 0 and s752["wlan_driver_loaded"] == 0,
            "safe_to_route_to_provider_first_boot_wlan_observe": provider_boot_wlan_gap and not s800["wifi_hal_start_executed"] and not s800["scan_connect_executed"],
        },
    }


def build_checks(command: str, analysis: dict[str, Any]) -> list[Check]:
    if command == "plan":
        return [Check("plan-only", "pass", "info", "no device command executed", "run host-only classifier")]
    missing = [key for key, item in analysis["inputs"].items() if not item.get("exists")]
    derived = analysis["derived"]
    return [
        Check("inputs", "pass" if not missing else "blocked", "blocker", ",".join(missing), "restore missing evidence"),
        Check("v800-provider-edge", "pass" if analysis["v800"]["icnss_edge_captured"] and analysis["v800"]["service74"] > 0 else "blocked", "blocker", json.dumps(analysis["v800"], sort_keys=True), "refresh V800 if service-positive ICNSS edge is absent"),
        Check("qca6390-disposition", "pass" if derived["qca6390_unbound_is_not_primary_target"] else "review", "finding", json.dumps({"v800": analysis["v800"], "v752": analysis["v752"]}, sort_keys=True), "avoid targeting qca6390 bind until Android proves this node is active on A90"),
        Check("boot-wlan-boundary", "pass" if derived["wlan_driver_boundary_is_after_boot_wlan"] else "blocked", "blocker", json.dumps(analysis["v752"], sort_keys=True), "refresh V752 or equivalent boot_wlan boundary evidence"),
        Check("next-live-shape", "pass" if derived["safe_to_route_to_provider_first_boot_wlan_observe"] else "blocked", "blocker", json.dumps(derived, sort_keys=True), "combine provider-first context with bounded boot_wlan observe"),
        Check("safety", "pass", "blocker", "host-only; no HAL, scan/connect, credentials, DHCP, routes, external ping, reboot, flash, or partition write", "preserve V801 boundary"),
    ]


def decide(command: str, checks: list[Check], analysis: dict[str, Any]) -> tuple[str, bool, str, str]:
    if command == "plan":
        return "v801-v800-edge-route-classifier-plan-ready", True, "plan-only; no device command executed", "run V801 host-only classifier"
    blocked = [check.name for check in checks if check.severity == "blocker" and check.status != "pass"]
    if blocked:
        return "v801-v800-edge-route-classifier-blocked", False, "blocked by " + ", ".join(blocked), "repair input evidence before selecting next live gate"
    if analysis["derived"]["safe_to_route_to_provider_first_boot_wlan_observe"]:
        return (
            "v801-provider-first-boot-wlan-observe-selected",
            True,
            "V800 proves service74/provider/CNSS/ICNSS edge; V752 proves boot_wlan reaches HDD loading but stalls before driver-loaded; qca6390 unbound is not the primary target",
            "V802 should combine provider-first service74/PeripheralManager/CNSS context with bounded boot_wlan observe, still no HAL/scan/connect/DHCP/external ping",
        )
    return "v801-v800-edge-route-review", True, json.dumps(analysis["derived"], sort_keys=True), "review V800/V752 evidence manually"


def render_summary(manifest: dict[str, Any]) -> str:
    analysis = manifest["analysis"]
    rows = []
    for section in ("v800", "v752", "v720", "derived"):
        for key, value in (analysis.get(section) or {}).items():
            rows.append([section, key, json.dumps(value, sort_keys=True) if isinstance(value, (dict, list, bool)) else str(value)])
    check_rows = [[check["name"], check["status"], check["detail"], check["next_step"]] for check in manifest["checks"]]
    return "\n".join([
        "# V801 V800 Edge Route Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- external_ping_executed: `{manifest['external_ping_executed']}`",
        "",
        "## Checks",
        "",
        markdown_table(["check", "status", "detail", "next"], check_rows),
        "",
        "## Analysis",
        "",
        markdown_table(["section", "key", "value"], rows),
        "",
    ])


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    analysis = build_analysis(args)
    checks = build_checks(args.command, analysis)
    decision, pass_ok, reason, next_step = decide(args.command, checks, analysis)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "cycle": "v801",
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "analysis": analysis,
        "checks": [asdict(check) for check in checks],
        "device_commands_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "wifi_bringup_executed": False,
        "external_ping_executed": False,
    }


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args, store)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    repo_path(LATEST_POINTER).write_text(str(store.run_dir) + "\n", encoding="utf-8")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"evidence: {store.run_dir}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

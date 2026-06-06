#!/usr/bin/env python3
"""V1628 host-only classifier for V1627 shutdown-list handoff evidence."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1628-pm-service-shutdown-list-classifier")
DEFAULT_REPORT_PATH = Path("docs/reports/NATIVE_INIT_V1628_PM_SERVICE_SHUTDOWN_LIST_CLASSIFIER_2026-06-02.md")
LATEST_POINTER = Path("tmp/wifi/latest-v1628-pm-service-shutdown-list-classifier.txt")

V1627_DIR = Path("tmp/wifi/v1627-pm-service-shutdown-list-handoff")
V1627_MANIFEST = V1627_DIR / "manifest.json"
V1627_HELPER = V1627_DIR / "test-v1393-helper-result.stdout.txt"
V1627_REPORT = Path("docs/reports/NATIVE_INIT_V1627_PM_SERVICE_SHUTDOWN_LIST_HANDOFF_2026-06-02.md")

KV_RE = re.compile(r"^(?P<key>[A-Za-z0-9_.:-]+)=(?P<value>.*)$")


def rel(path: Path) -> str:
    resolved = repo_path(path)
    try:
        return str(resolved.relative_to(repo_path(".")))
    except ValueError:
        return str(resolved)


def read_text(path: Path, limit: int = 64 * 1024 * 1024) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    return resolved.read_bytes()[:limit].replace(b"\0", b"\\0").decode("utf-8", errors="replace")


def read_json(path: Path) -> dict[str, Any]:
    text = read_text(path)
    if not text:
        return {}
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def parse_kv(text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for raw_line in text.splitlines():
        match = KV_RE.match(raw_line.strip())
        if match:
            result[match.group("key")] = match.group("value").strip()
    return result


def int_value(value: Any, default: int = -1) -> int:
    try:
        return int(str(value).strip(), 0)
    except (TypeError, ValueError):
        return default


def bool_value(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "pass"}


def capture_value(text: str, label: str) -> str:
    start = f"A90_EXECNS_PATH_{label}_BEGIN"
    end = f"A90_EXECNS_PATH_{label}_END"
    i = text.find(start)
    if i < 0:
        return ""
    body = text.find("\n", i)
    j = text.find(end, body)
    if body < 0 or j < 0:
        return ""
    return text[body + 1:j].strip()


def property_requests(helper: dict[str, str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index in range(1, 32):
        name = helper.get(f"wifi_hal_composite_start.property_service_shim.request.{index}.name")
        if not name:
            continue
        rows.append({
            "index": index,
            "name": name,
            "value": helper.get(f"wifi_hal_composite_start.property_service_shim.request.{index}.value", ""),
            "allowed": int_value(helper.get(f"wifi_hal_composite_start.property_service_shim.request.{index}.allowed")),
            "result": helper.get(f"wifi_hal_composite_start.property_service_shim.request.{index}.result", ""),
        })
    return rows


def analyze() -> dict[str, Any]:
    manifest = read_json(V1627_MANIFEST)
    progress = manifest.get("wifi_progress") if isinstance(manifest.get("wifi_progress"), dict) else {}
    helper_text = read_text(V1627_HELPER)
    helper = parse_kv(helper_text)
    requests = property_requests(helper)
    shutdown_requests = [row for row in requests if row["name"] == "vendor.peripheral.shutdown_critical_list"]
    denied_shutdown = [row for row in shutdown_requests if row["allowed"] == 0]
    allowed_shutdown = [row for row in shutdown_requests if row["allowed"] == 1 and row["result"] == "0x00000000"]
    request_pairs = {(row["name"], row["value"]) for row in requests}

    current = {
        "v1627_decision": manifest.get("decision", ""),
        "handoff_pass": bool_value(manifest.get("handoff_pass")),
        "rollback_ok": bool_value((manifest.get("rollback") or {}).get("ok")),
        "strict_wifi_progress": bool_value(manifest.get("strict_wifi_progress")),
        "progress_decision": progress.get("final_decision", ""),
        "provider_trigger": bool_value(progress.get("provider_trigger")),
        "rc1_progress": bool_value(progress.get("rc1_progress")),
        "mhi_progress": bool_value(progress.get("mhi_progress")),
        "wlfw_progress": bool_value(progress.get("wlfw_progress")),
        "wlan0_present": bool_value(progress.get("wlan0_present")),
        "helper_result": helper.get("android_wifi_service_window.result", ""),
        "helper_reason": helper.get("android_wifi_service_window.reason", ""),
        "allow_peripheral_shutdown_list": int_value(helper.get("wifi_hal_composite_start.property_service_shim.allow_peripheral_shutdown_list")),
        "property_root_exists_pre": int_value(helper.get("mdm_helper_provider_readiness.per_mgr_pre_startup_trace.path.dev_properties.exists")),
        "property_root_exists_post": int_value(helper.get("mdm_helper_provider_readiness.per_mgr_post_startup_trace.path.dev_properties.exists")),
        "property_root_captured_pre": int_value(helper.get("pm_service_system_info_surface.per_mgr_pre_startup_trace.dir.dev_properties.captured")),
        "property_root_captured_post": int_value(helper.get("pm_service_system_info_surface.per_mgr_post_startup_trace.dir.dev_properties.captured")),
        "property_root_entries_pre": "u:object_r:vendor_default_prop:s0" in helper_text and "property_info" in helper_text,
        "subsys0_state": capture_value(helper_text, "pm_service_system_info_per_mgr_pre_startup_trace_subsys0_state"),
        "subsys9_state": capture_value(helper_text, "pm_service_system_info_per_mgr_pre_startup_trace_subsys9_state"),
        "esoc0_name": capture_value(helper_text, "pm_service_system_info_per_mgr_pre_startup_trace_esoc0_name"),
        "request_count": int_value(helper.get("wifi_hal_composite_start.property_service_shim.request_count")),
        "shutdown_request_count": len(shutdown_requests),
        "shutdown_allowed_count": len(allowed_shutdown),
        "shutdown_denied_count": len(denied_shutdown),
        "sdx50m_offline_requested": ("vendor.peripheral.SDX50M.state", "OFFLINE") in request_pairs,
        "modem_offline_requested": ("vendor.peripheral.modem.state", "OFFLINE") in request_pairs,
        "startup_exit_code": int_value(helper.get("android_wifi_service_window.per_mgr_startup_trace.exit_code")),
        "startup_signal": int_value(helper.get("android_wifi_service_window.per_mgr_startup_trace.signal")),
        "max_subsys_modem_fd": int_value(helper.get("android_wifi_service_window.per_mgr_startup_trace.max_subsys_modem_fd")),
        "max_subsys_esoc0_fd": int_value(helper.get("android_wifi_service_window.per_mgr_startup_trace.max_subsys_esoc0_fd")),
        "max_vndbinder_fd": int_value(helper.get("android_wifi_service_window.per_mgr_startup_trace.max_vndbinder_fd")),
        "max_hwbinder_fd": int_value(helper.get("android_wifi_service_window.per_mgr_startup_trace.max_hwbinder_fd")),
        "max_binder_fd": int_value(helper.get("android_wifi_service_window.per_mgr_startup_trace.max_binder_fd")),
        "max_socket_fd": int_value(helper.get("android_wifi_service_window.per_mgr_startup_trace.max_socket_fd")),
    }
    checks = {
        "handoff_rollback_ok": current["handoff_pass"] and current["rollback_ok"],
        "property_root_still_materialized": current["property_root_exists_pre"] == 1
        and current["property_root_exists_post"] == 1
        and current["property_root_captured_pre"] == 1
        and current["property_root_captured_post"] == 1
        and current["property_root_entries_pre"],
        "surface_still_offlining": current["subsys0_state"] == "ONLINE"
        and current["subsys9_state"] == "OFFLINING"
        and current["esoc0_name"] == "SDX50M",
        "shutdown_critical_list_allowed": current["allow_peripheral_shutdown_list"] == 1
        and current["shutdown_request_count"] >= 1
        and current["shutdown_allowed_count"] == current["shutdown_request_count"]
        and current["shutdown_denied_count"] == 0,
        "pm_service_still_exits_before_ipc_or_pm_fd": current["startup_exit_code"] == 0
        and current["startup_signal"] == 0
        and current["max_subsys_modem_fd"] == 0
        and current["max_subsys_esoc0_fd"] == 0
        and current["max_vndbinder_fd"] == 0
        and current["max_hwbinder_fd"] == 0
        and current["max_binder_fd"] == 0
        and current["max_socket_fd"] == 0,
        "downstream_absent": not current["provider_trigger"]
        and not current["rc1_progress"]
        and not current["mhi_progress"]
        and not current["wlfw_progress"]
        and not current["wlan0_present"],
    }
    pass_ok = all(checks.values())
    return {
        "cycle": "V1628",
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "host": collect_host_metadata(),
        "inputs": {
            "v1627_manifest": rel(V1627_MANIFEST),
            "v1627_helper": rel(V1627_HELPER),
            "v1627_report": rel(V1627_REPORT),
        },
        "decision": "v1628-shutdown-list-accepted-pm-service-still-exits-before-ipc" if pass_ok else "v1628-shutdown-list-classifier-manual-review",
        "pass": pass_ok,
        "current": current,
        "property_requests": requests,
        "checks": checks,
    }


def render_report(result: dict[str, Any]) -> str:
    current = result["current"]
    checks = result["checks"]
    requests = result["property_requests"]
    return "\n".join([
        "# Native Init V1628 pm-service Shutdown-list Classifier",
        "",
        "## Summary",
        "",
        "- Cycle: `V1628`",
        "- Type: host-only classifier over V1627 rollbackable live evidence",
        f"- Decision: `{result['decision']}`",
        f"- Result: {'PASS' if result['pass'] else 'MANUAL-REVIEW'}",
        "- Reason: V1627 accepts `vendor.peripheral.shutdown_critical_list` writes, but `pm-service` still exits before IPC/PM fd setup",
        "",
        "## Inputs",
        "",
        markdown_table(["input", "path"], [[key, value] for key, value in result["inputs"].items()]),
        "",
        "## Checks",
        "",
        markdown_table(["check", "value"], [[key, value] for key, value in checks.items()]),
        "",
        "## Runtime",
        "",
        markdown_table(["field", "value"], [[key, value] for key, value in current.items()]),
        "",
        "## Property Requests",
        "",
        markdown_table(["index", "name", "value", "allowed", "result"], [
            [row["index"], row["name"], row["value"], row["allowed"], row["result"]]
            for row in requests
        ]),
        "",
        "## Interpretation",
        "",
        "V1627 proves the V1625 allowlist repair worked: the property shim starts with `allow_peripheral_shutdown_list=1`, and the `SDX50M ` / `SDX50M modem ` shutdown-critical-list writes return success.",
        "",
        "The boundary did not advance into IPC or PM ownership.  `pm-service` still exits cleanly before opening binder, vndbinder/hwbinder, sockets, `/dev/subsys_modem`, or `/dev/subsys_esoc0`, and no RC1/MHI/WLFW/`wlan0` progress appears.",
        "",
        "This narrows the immediate blocker away from property-root materialization and the shutdown-critical-list allowlist.  The next gate should classify the next `pm-service` early-exit dependency using the already captured runtime surface and startup trace, before adding any new lower-layer action.",
        "",
        "## Next Gate",
        "",
        "- Recommended cycle: `V1629`",
        "- Type: host-only `pm-service` early-exit dependency classifier",
        "- Focus: compare the accepted property sequence with Android `pm-service` startup requirements and identify the next missing surface before another live boot",
        "- Keep blocked: Wi-Fi HAL start, scan/connect, credentials, DHCP/routes, external ping, PMIC/GPIO/GDSC writes, blind eSoC notify/`BOOT_DONE`, global PCI rescan, platform bind/unbind, and direct scoped `/dev/subsys_esoc0` actor opens",
        "",
        "## Safety Scope",
        "",
        "This classifier is host-only. It performs no device command, flash, reboot, partition write, daemon start, Wi-Fi HAL start, scan/connect, credential handling, DHCP/routes, external ping, PMIC/GPIO/GDSC write, blind eSoC notify/`BOOT_DONE` spoof, pci-msm debugfs write, global PCI rescan, or platform bind/unbind.",
        "",
    ])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT_PATH)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    store = EvidenceStore(args.out_dir)
    result = analyze()
    store.write_json("manifest.json", result)
    write_private_text(args.report_path, render_report(result))
    write_private_text(LATEST_POINTER, f"{rel(args.out_dir / 'manifest.json')}\n")
    print(json.dumps({
        "decision": result["decision"],
        "pass": result["pass"],
        "out_dir": str(args.out_dir),
        "report": rel(args.report_path),
    }, indent=2))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

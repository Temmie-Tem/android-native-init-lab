#!/usr/bin/env python3
"""V1624 host-only classifier for V1623 property-root handoff evidence."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1624-pm-service-property-root-classifier")
DEFAULT_REPORT_PATH = Path("docs/reports/NATIVE_INIT_V1624_PM_SERVICE_PROPERTY_ROOT_CLASSIFIER_2026-06-02.md")
LATEST_POINTER = Path("tmp/wifi/latest-v1624-pm-service-property-root-classifier.txt")

V1623_DIR = Path("tmp/wifi/v1623-pm-service-property-root-handoff")
V1623_MANIFEST = V1623_DIR / "manifest.json"
V1623_HELPER = V1623_DIR / "test-v1393-helper-result.stdout.txt"
V1623_REPORT = Path("docs/reports/NATIVE_INIT_V1623_PM_SERVICE_PROPERTY_ROOT_HANDOFF_2026-06-02.md")

KV_RE = re.compile(r"^(?P<key>[A-Za-z0-9_.:-]+)=(?P<value>.*)$")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


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
    manifest = read_json(V1623_MANIFEST)
    progress = manifest.get("wifi_progress") if isinstance(manifest.get("wifi_progress"), dict) else {}
    helper_text = read_text(V1623_HELPER)
    helper = parse_kv(helper_text)
    requests = property_requests(helper)
    shutdown_requests = [row for row in requests if row["name"] == "vendor.peripheral.shutdown_critical_list"]
    denied_shutdown = [row for row in shutdown_requests if row["allowed"] == 0]
    request_pairs = {(row["name"], row["value"]) for row in requests}

    current = {
        "v1623_decision": manifest.get("decision", ""),
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
        "shutdown_denied_count": len(denied_shutdown),
        "sdx50m_offline_requested": ("vendor.peripheral.SDX50M.state", "OFFLINE") in request_pairs,
        "modem_offline_requested": ("vendor.peripheral.modem.state", "OFFLINE") in request_pairs,
        "startup_exit_code": int_value(helper.get("android_wifi_service_window.per_mgr_startup_trace.exit_code")),
        "startup_signal": int_value(helper.get("android_wifi_service_window.per_mgr_startup_trace.signal")),
        "max_subsys_modem_fd": int_value(helper.get("android_wifi_service_window.per_mgr_startup_trace.max_subsys_modem_fd")),
        "max_subsys_esoc0_fd": int_value(helper.get("android_wifi_service_window.per_mgr_startup_trace.max_subsys_esoc0_fd")),
        "max_vndbinder_fd": int_value(helper.get("android_wifi_service_window.per_mgr_startup_trace.max_vndbinder_fd")),
        "max_socket_fd": int_value(helper.get("android_wifi_service_window.per_mgr_startup_trace.max_socket_fd")),
    }
    checks = {
        "handoff_rollback_ok": current["handoff_pass"] and current["rollback_ok"],
        "property_root_materialized": current["property_root_exists_pre"] == 1
        and current["property_root_exists_post"] == 1
        and current["property_root_captured_pre"] == 1
        and current["property_root_captured_post"] == 1
        and current["property_root_entries_pre"],
        "surface_still_offlining": current["subsys0_state"] == "ONLINE"
        and current["subsys9_state"] == "OFFLINING"
        and current["esoc0_name"] == "SDX50M",
        "shutdown_critical_list_denied": current["shutdown_request_count"] >= 1
        and current["shutdown_denied_count"] == current["shutdown_request_count"],
        "pm_service_still_exits_before_ipc_or_pm_fd": current["startup_exit_code"] == 0
        and current["startup_signal"] == 0
        and current["max_subsys_modem_fd"] == 0
        and current["max_subsys_esoc0_fd"] == 0
        and current["max_vndbinder_fd"] == 0
        and current["max_socket_fd"] == 0,
        "downstream_absent": not current["provider_trigger"]
        and not current["rc1_progress"]
        and not current["mhi_progress"]
        and not current["wlfw_progress"]
        and not current["wlan0_present"],
    }
    pass_ok = all(checks.values())
    return {
        "cycle": "V1624",
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "host": collect_host_metadata(),
        "inputs": {
            "v1623_manifest": rel(V1623_MANIFEST),
            "v1623_helper": rel(V1623_HELPER),
            "v1623_report": rel(V1623_REPORT),
        },
        "decision": "v1624-property-root-materialized-shutdown-critical-list-blocked" if pass_ok else "v1624-property-root-classifier-manual-review",
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
        "# Native Init V1624 pm-service Property-root Classifier",
        "",
        "## Summary",
        "",
        "- Cycle: `V1624`",
        "- Type: host-only classifier over V1623 rollbackable live evidence",
        f"- Decision: `{result['decision']}`",
        f"- Result: {'PASS' if result['pass'] else 'MANUAL-REVIEW'}",
        "- Reason: V1623 fixed `/dev/__properties__` visibility, but `pm-service` still exits before IPC/PM fd setup after denied `vendor.peripheral.shutdown_critical_list` writes",
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
        markdown_table(["index", "name", "value", "allowed", "result"], [[row["index"], row["name"], row["value"], row["allowed"], row["result"]] for row in requests]),
        "",
        "## Interpretation",
        "",
        "V1623 proves the V1621 helper repair worked: `/dev/__properties__` is present and captured inside the private namespace.  That removes missing property-area materialization as the immediate blocker.",
        "",
        "The boundary moved one step forward.  `pm-service` now attempts `vendor.peripheral.shutdown_critical_list` updates, but the shim rejects those writes with permission-denied results.  It still exits cleanly before binder/socket/subsystem fd ownership, and no RC1/MHI/WLFW/`wlan0` progress appears.",
        "",
        "## Next Gate",
        "",
        "- Recommended cycle: `V1625`",
        "- Type: source/build-only property-shim allowlist repair",
        "- Change: enable `vendor.peripheral.shutdown_critical_list` values `SDX50M ` and `SDX50M modem ` for android service-window mode only",
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
    result = analyze()
    store = EvidenceStore(args.out_dir)
    store.write_json("manifest.json", result)
    store.write_text("summary.md", render_report(result))
    write_private_text(args.report_path, render_report(result))
    LATEST_POINTER.parent.mkdir(parents=True, exist_ok=True)
    LATEST_POINTER.write_text(str(args.out_dir) + "\n", encoding="utf-8")
    print(json.dumps({"decision": result["decision"], "pass": result["pass"], "out_dir": rel(args.out_dir)}, indent=2))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

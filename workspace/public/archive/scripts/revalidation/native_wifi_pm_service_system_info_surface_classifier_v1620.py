#!/usr/bin/env python3
"""V1620 host-only classifier for V1619 pm-service system-info surface evidence.

This classifier reads existing host evidence only. It does not contact the
vehicle/device, flash, reboot, start daemons, start Wi-Fi HAL, scan/connect,
use credentials, run DHCP, change routes, ping externally, or write sysfs,
debugfs, GPIO, subsystem, boot, or partition state.
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


DEFAULT_OUT_DIR = Path("tmp/wifi/v1620-pm-service-system-info-surface-classifier")
DEFAULT_REPORT_PATH = Path(
    "docs/reports/NATIVE_INIT_V1620_PM_SERVICE_SYSTEM_INFO_SURFACE_CLASSIFIER_2026-06-02.md"
)
LATEST_POINTER = Path("tmp/wifi/latest-v1620-pm-service-system-info-surface-classifier.txt")

V1619_DIR = Path("tmp/wifi/v1619-pm-service-system-info-surface-handoff")
V1619_MANIFEST = V1619_DIR / "manifest.json"
V1619_HELPER = V1619_DIR / "test-v1393-helper-result.stdout.txt"
V1619_REPORT = Path("docs/reports/NATIVE_INIT_V1619_PM_SERVICE_SYSTEM_INFO_SURFACE_HANDOFF_2026-06-02.md")

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
    return (
        resolved.read_bytes()[:limit]
        .replace(b"\0", b"\\0")
        .decode("utf-8", errors="replace")
    )


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
    values: dict[str, str] = {}
    for raw_line in text.splitlines():
        match = KV_RE.match(raw_line.strip())
        if match:
            values[match.group("key")] = match.group("value").strip()
    return values


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
    start_index = text.find(start)
    if start_index < 0:
        return ""
    body_index = text.find("\n", start_index)
    if body_index < 0:
        return ""
    end_index = text.find(end, body_index)
    if end_index < 0:
        return ""
    return text[body_index + 1:end_index].strip()


def property_requests(helper: dict[str, str]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for index in range(1, 32):
        name = helper.get(f"wifi_hal_composite_start.property_service_shim.request.{index}.name")
        if not name:
            continue
        result.append({
            "index": index,
            "name": name,
            "value": helper.get(f"wifi_hal_composite_start.property_service_shim.request.{index}.value", ""),
            "allowed": int_value(
                helper.get(f"wifi_hal_composite_start.property_service_shim.request.{index}.allowed")
            ),
            "result": helper.get(f"wifi_hal_composite_start.property_service_shim.request.{index}.result", ""),
        })
    return result


def phase_surface(helper: dict[str, str], helper_text: str, phase: str) -> dict[str, Any]:
    prefix = f"pm_service_system_info_surface.{phase}"
    path_prefix = f"mdm_helper_provider_readiness.{phase}.path"
    label_prefix = f"pm_service_system_info_{phase}"
    return {
        "begin": int_value(helper.get(f"{prefix}.begin")),
        "end": int_value(helper.get(f"{prefix}.end")),
        "no_ioctl": int_value(helper.get(f"{prefix}.no_ioctl")),
        "no_subsys_open": int_value(helper.get(f"{prefix}.no_subsys_open")),
        "dev_subsys_modem_exists": int_value(helper.get(f"{path_prefix}.dev_subsys_modem.exists")),
        "dev_subsys_esoc0_exists": int_value(helper.get(f"{path_prefix}.dev_subsys_esoc0.exists")),
        "dev_esoc0_exists": int_value(helper.get(f"{path_prefix}.dev_esoc0.exists")),
        "dev_vndbinder_exists": int_value(helper.get(f"{path_prefix}.dev_vndbinder.exists")),
        "dev_binder_exists": int_value(helper.get(f"{path_prefix}.dev_binder.exists")),
        "dev_hwbinder_exists": int_value(helper.get(f"{path_prefix}.dev_hwbinder.exists")),
        "property_service_socket_exists": int_value(helper.get(f"{path_prefix}.property_service_socket.exists")),
        "dev_properties_exists": int_value(helper.get(f"{path_prefix}.dev_properties.exists")),
        "sys_bus_msm_subsys_devices_exists": int_value(helper.get(f"{path_prefix}.sys_bus_msm_subsys_devices.exists")),
        "sys_bus_esoc_devices_exists": int_value(helper.get(f"{path_prefix}.sys_bus_esoc_devices.exists")),
        "sys_class_esoc_dev_exists": int_value(helper.get(f"{path_prefix}.sys_class_esoc_dev.exists")),
        "subsys0_exists": int_value(helper.get(f"{path_prefix}.subsys0.exists")),
        "subsys9_exists": int_value(helper.get(f"{path_prefix}.subsys9.exists")),
        "esoc0_exists": int_value(helper.get(f"{path_prefix}.esoc0.exists")),
        "dev_filtered_captured": int_value(helper.get(f"{prefix}.dir.dev_filtered.captured")),
        "dev_socket_filtered_captured": int_value(helper.get(f"{prefix}.dir.dev_socket_filtered.captured")),
        "dev_properties_captured": int_value(helper.get(f"{prefix}.dir.dev_properties.captured")),
        "msm_subsys_devices_captured": int_value(helper.get(f"{prefix}.dir.msm_subsys_devices.captured")),
        "esoc_devices_captured": int_value(helper.get(f"{prefix}.dir.esoc_devices.captured")),
        "esoc_class_dev_captured": int_value(helper.get(f"{prefix}.dir.esoc_class_dev.captured")),
        "subsys0_name": capture_value(helper_text, f"{label_prefix}_subsys0_name"),
        "subsys0_state": capture_value(helper_text, f"{label_prefix}_subsys0_state"),
        "subsys9_name": capture_value(helper_text, f"{label_prefix}_subsys9_name"),
        "subsys9_state": capture_value(helper_text, f"{label_prefix}_subsys9_state"),
        "esoc0_name": capture_value(helper_text, f"{label_prefix}_esoc0_name"),
        "esoc0_link": capture_value(helper_text, f"{label_prefix}_esoc0_link"),
        "esoc0_link_info": capture_value(helper_text, f"{label_prefix}_esoc0_link_info"),
    }


def analyze() -> dict[str, Any]:
    manifest = read_json(V1619_MANIFEST)
    progress = manifest.get("wifi_progress") if isinstance(manifest.get("wifi_progress"), dict) else {}
    helper_text = read_text(V1619_HELPER)
    helper = parse_kv(helper_text)
    requests = property_requests(helper)
    request_pairs = {(item["name"], item["value"]) for item in requests}
    pre = phase_surface(helper, helper_text, "per_mgr_pre_startup_trace")
    post = phase_surface(helper, helper_text, "per_mgr_post_startup_trace")

    current = {
        "v1619_decision": manifest.get("decision", ""),
        "handoff_pass": bool_value(manifest.get("handoff_pass")),
        "rollback_ok": bool_value((manifest.get("rollback") or {}).get("ok")),
        "strict_wifi_progress": bool_value(manifest.get("strict_wifi_progress")),
        "progress_decision": progress.get("final_decision", ""),
        "provider_trigger": bool_value(progress.get("provider_trigger")),
        "modem_trigger": bool_value(progress.get("modem_trigger")),
        "rc1_progress": bool_value(progress.get("rc1_progress")),
        "mhi_progress": bool_value(progress.get("mhi_progress")),
        "wlfw_progress": bool_value(progress.get("wlfw_progress")),
        "wlan0_present": bool_value(progress.get("wlan0_present")),
        "helper_result": helper.get("android_wifi_service_window.result", ""),
        "helper_reason": helper.get("android_wifi_service_window.reason", ""),
        "helper_mode": helper.get("android_wifi_service_window.mode", ""),
        "per_mgr_system_info_surface": int_value(helper.get("android_wifi_service_window.per_mgr_system_info_surface")),
        "startup_sample_count": int_value(helper.get("android_wifi_service_window.per_mgr_startup_trace.sample_count")),
        "last_alive_ms": int_value(helper.get("android_wifi_service_window.per_mgr_startup_trace.last_alive_ms")),
        "first_gone_ms": int_value(helper.get("android_wifi_service_window.per_mgr_startup_trace.first_gone_ms")),
        "startup_exit_code": int_value(helper.get("android_wifi_service_window.per_mgr_startup_trace.exit_code")),
        "startup_signal": int_value(helper.get("android_wifi_service_window.per_mgr_startup_trace.signal")),
        "max_subsys_modem_fd": int_value(helper.get("android_wifi_service_window.per_mgr_startup_trace.max_subsys_modem_fd")),
        "max_subsys_esoc0_fd": int_value(helper.get("android_wifi_service_window.per_mgr_startup_trace.max_subsys_esoc0_fd")),
        "max_vndbinder_fd": int_value(helper.get("android_wifi_service_window.per_mgr_startup_trace.max_vndbinder_fd")),
        "max_socket_fd": int_value(helper.get("android_wifi_service_window.per_mgr_startup_trace.max_socket_fd")),
        "pm_proxy_helper_subsys_modem_fd_count": int_value(helper.get("android_wifi_service_window.pm_proxy_helper_subsys_modem_fd_count")),
        "mdm_helper_esoc0_fd_count": int_value(helper.get("android_wifi_service_window.mdm_helper_esoc0_fd_count")),
        "pm_full_contract_seen": int_value(helper.get("android_wifi_service_window.pm_full_contract_seen")),
        "property_request_count": int_value(helper.get("wifi_hal_composite_start.property_service_shim.request_count")),
        "property_hwservicemanager_ready": ("hwservicemanager.ready", "true") in request_pairs,
        "property_sdx50m_offline": ("vendor.peripheral.SDX50M.state", "OFFLINE") in request_pairs,
        "property_modem_offline": ("vendor.peripheral.modem.state", "OFFLINE") in request_pairs,
    }
    checks = {
        "handoff_rollback_ok": current["handoff_pass"] and current["rollback_ok"],
        "system_info_surface_enabled": current["per_mgr_system_info_surface"] == 1,
        "snapshots_complete": pre["begin"] == 1 and pre["end"] == 1 and post["begin"] == 1 and post["end"] == 1,
        "snapshots_read_only": pre["no_ioctl"] == 1 and pre["no_subsys_open"] == 1
        and post["no_ioctl"] == 1 and post["no_subsys_open"] == 1,
        "core_nodes_visible": all(pre[key] == 1 for key in (
            "dev_subsys_modem_exists", "dev_subsys_esoc0_exists", "dev_esoc0_exists",
            "dev_vndbinder_exists", "dev_binder_exists", "dev_hwbinder_exists",
            "property_service_socket_exists", "sys_bus_msm_subsys_devices_exists",
            "sys_bus_esoc_devices_exists", "sys_class_esoc_dev_exists",
            "subsys0_exists", "subsys9_exists", "esoc0_exists",
        )),
        "android_property_area_missing": pre["dev_properties_exists"] == 0 and post["dev_properties_exists"] == 0,
        "surface_reports_modem_online": pre["subsys0_name"] == "modem" and pre["subsys0_state"] == "ONLINE",
        "surface_reports_esoc0_offlining": pre["subsys9_name"] == "esoc0" and pre["subsys9_state"] == "OFFLINING",
        "surface_reports_sdx50m_pcie": pre["esoc0_name"] == "SDX50M"
        and pre["esoc0_link"] == "PCIe"
        and pre["esoc0_link_info"] == "0305_01.01.00",
        "pm_service_exits_before_ipc_or_pm_fd": current["startup_exit_code"] == 0
        and current["startup_signal"] == 0
        and current["max_subsys_modem_fd"] == 0
        and current["max_subsys_esoc0_fd"] == 0
        and current["max_vndbinder_fd"] == 0
        and current["max_socket_fd"] == 0
        and current["pm_full_contract_seen"] == 0,
        "offline_property_decision_observed": current["property_request_count"] == 3
        and current["property_hwservicemanager_ready"]
        and current["property_sdx50m_offline"]
        and current["property_modem_offline"],
        "downstream_absent": not current["provider_trigger"]
        and not current["rc1_progress"]
        and not current["mhi_progress"]
        and not current["wlfw_progress"]
        and not current["wlan0_present"],
    }
    pass_ok = all(checks.values())
    decision = (
        "v1620-pm-service-offline-decision-despite-visible-esoc-surface"
        if pass_ok else
        "v1620-pm-service-system-info-surface-needs-manual-review"
    )
    return {
        "cycle": "V1620",
        "created_at": now_iso(),
        "host": collect_host_metadata(),
        "inputs": {
            "v1619_manifest": rel(V1619_MANIFEST),
            "v1619_helper": rel(V1619_HELPER),
            "v1619_report": rel(V1619_REPORT),
        },
        "decision": decision,
        "pass": pass_ok,
        "current": current,
        "pre_surface": pre,
        "post_surface": post,
        "property_requests": requests,
        "checks": checks,
    }


def render_report(result: dict[str, Any]) -> str:
    current = result["current"]
    checks = result["checks"]
    pre = result["pre_surface"]
    post = result["post_surface"]
    requests = result["property_requests"]
    return "\n".join([
        "# Native Init V1620 pm-service System-info Surface Classifier",
        "",
        "## Summary",
        "",
        "- Cycle: `V1620`",
        "- Type: host-only classifier over V1619 rollbackable live evidence",
        f"- Decision: `{result['decision']}`",
        f"- Result: {'PASS' if result['pass'] else 'MANUAL-REVIEW'}",
        "- Reason: V1619 proves the private namespace exposes the expected eSoC/subsystem/dev-node surface, but `pm-service` still exits cleanly after publishing SDX50M/modem OFFLINE before Binder/PM fd setup",
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
        "## Surface Snapshot",
        "",
        markdown_table(["field", "pre", "post"], [
            ["subsys0", f"{pre['subsys0_name']} {pre['subsys0_state']}", f"{post['subsys0_name']} {post['subsys0_state']}"],
            ["subsys9", f"{pre['subsys9_name']} {pre['subsys9_state']}", f"{post['subsys9_name']} {post['subsys9_state']}"],
            ["esoc0", f"{pre['esoc0_name']} {pre['esoc0_link']} {pre['esoc0_link_info']}", f"{post['esoc0_name']} {post['esoc0_link']} {post['esoc0_link_info']}"],
            ["/dev/subsys_modem", pre["dev_subsys_modem_exists"], post["dev_subsys_modem_exists"]],
            ["/dev/subsys_esoc0", pre["dev_subsys_esoc0_exists"], post["dev_subsys_esoc0_exists"]],
            ["/dev/esoc-0", pre["dev_esoc0_exists"], post["dev_esoc0_exists"]],
            ["binder nodes", f"vnd={pre['dev_vndbinder_exists']} binder={pre['dev_binder_exists']} hw={pre['dev_hwbinder_exists']}", f"vnd={post['dev_vndbinder_exists']} binder={post['dev_binder_exists']} hw={post['dev_hwbinder_exists']}"],
            ["/dev/socket/property_service", pre["property_service_socket_exists"], post["property_service_socket_exists"]],
            ["/dev/__properties__", pre["dev_properties_exists"], post["dev_properties_exists"]],
        ]),
        "",
        "## Property Requests",
        "",
        markdown_table(["index", "name", "value", "allowed", "result"], [[item["index"], item["name"], item["value"], item["allowed"], item["result"]] for item in requests]),
        "",
        "## Interpretation",
        "",
        "V1619 eliminates a missing-device-node explanation for the current `pm-service` boundary.  The private namespace contains `/dev/subsys_modem`, `/dev/subsys_esoc0`, `/dev/esoc-0`, binder nodes, the property-service socket, `/sys/bus/msm_subsys`, `/sys/bus/esoc`, and `/sys/class/esoc-dev`.  The visible sysfs state is internally consistent: `subsys0=modem ONLINE`, `subsys9=esoc0 OFFLINING`, and `esoc0=SDX50M PCIe 0305_01.01.00`.",
        "",
        "The remaining gap is narrower: `pm-service` still exits naturally with code `0` before opening binder, sockets, `/dev/subsys_modem`, or `/dev/subsys_esoc0`, after publishing `vendor.peripheral.SDX50M.state=OFFLINE` and `vendor.peripheral.modem.state=OFFLINE`.  `/dev/__properties__` is absent in this private namespace; Android normally provides the shared property area in addition to the property-service socket.  The next gate should classify whether the missing Android property area or missing initial property values make `libmdmdetect`/`get_system_info` choose the OFFLINE-only path.",
        "",
        "## Next Gate",
        "",
        "- Recommended cycle: `V1621`",
        "- Type: source/build-only property-area/properties parity probe",
        "- Focus: expose a read-only/minimal Android property area or capture exact `property_get` dependencies before changing lower eSoC/RC1 behavior",
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
    print(json.dumps({
        "decision": result["decision"],
        "pass": result["pass"],
        "out_dir": rel(args.out_dir),
    }, indent=2))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

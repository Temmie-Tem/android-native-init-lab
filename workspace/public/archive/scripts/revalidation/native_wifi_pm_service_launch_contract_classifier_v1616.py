#!/usr/bin/env python3
"""V1616 host-only pm-service launch/dependency contract classifier.

This classifier reads existing host evidence only.  It does not contact the
device, start daemons, start Wi-Fi HAL, scan/connect, use credentials, run
DHCP, change routes, ping externally, write sysfs/debugfs/GPIO/subsystem nodes,
or write boot/partitions.
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


DEFAULT_OUT_DIR = Path("tmp/wifi/v1616-pm-service-launch-contract-classifier")
DEFAULT_REPORT_PATH = Path(
    "docs/reports/NATIVE_INIT_V1616_PM_SERVICE_LAUNCH_CONTRACT_CLASSIFIER_2026-06-02.md"
)
LATEST_POINTER = Path("tmp/wifi/latest-v1616-pm-service-launch-contract-classifier.txt")

V1614_DIR = Path("tmp/wifi/v1614-per-mgr-nonstop-context-handoff")
V1614_MANIFEST = V1614_DIR / "manifest.json"
V1614_HELPER = V1614_DIR / "test-v1393-helper-result.stdout.txt"
V1615_REPORT = Path("docs/reports/NATIVE_INIT_V1615_PER_MGR_NONSTOP_CONTEXT_CLASSIFIER_2026-06-02.md")

V862_MANIFEST = Path("tmp/wifi/v862-android-init-service-contract/manifest.json")
V1073_EXTRACT = Path("tmp/wifi/v1073-host-only/vendor-extract/files")
V1073_ANALYSIS = Path("tmp/wifi/v1073-host-only/analysis")
V1081_MANIFEST = Path("tmp/wifi/v1081-pm-service-early-path-classifier/manifest.json")

HELPER_SOURCE = Path("stage3/linux_init/helpers/a90_android_execns_probe.c")
INIT_WRAPPER_SOURCE = Path("stage3/linux_init/v724/90_main.inc.c")

ANDROID_PROP_CANDIDATES = (
    Path("tmp/wifi/v431-android-runtime-gap-handoff-live-su-quote-20260520-152315/v431-android-runtime-gap-run/commands/wifi-props-filtered.txt"),
    Path("tmp/wifi/v431-android-runtime-gap-handoff-live-su-20260520-151844/v431-android-runtime-gap-run/commands/wifi-props-filtered.txt"),
    Path("tmp/wifi/v1331-android-sdx50m-timing-handoff/v1331-android-sdx50m-timing-recapture-run/android-v1331-props-normalized.txt"),
    Path("tmp/wifi/v1555-android-good-minimal-trace-reference/android-postfs-evidence/a90-v1555-android-min-trace-ref/props.txt"),
)

KV_RE = re.compile(r"^(?P<key>[A-Za-z0-9_.:-]+)=(?P<value>.*)$")
NEEDED_RE = re.compile(r"NEEDED\)\s+Shared library:\s+\[(?P<name>[^\]]+)\]")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def rel(path: Path) -> str:
    resolved = repo_path(path)
    try:
        return str(resolved.relative_to(repo_path(".")))
    except ValueError:
        return str(resolved)


def read_text(path: Path, limit: int = 32 * 1024 * 1024) -> str:
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


def parse_property_lines(text: str) -> dict[str, str]:
    props: dict[str, str] = {}
    bracket_re = re.compile(r"^\[(?P<key>[^\]]+)\]:\s+\[(?P<value>[^\]]*)\]$")
    equal_re = re.compile(r"^(?P<key>[A-Za-z0-9_.:-]+)=(?P<value>.*)$")
    for raw_line in text.splitlines():
        line = raw_line.strip()
        bracket = bracket_re.match(line)
        if bracket:
            props[bracket.group("key")] = bracket.group("value")
            continue
        equal = equal_re.match(line)
        if equal:
            props[equal.group("key")] = equal.group("value")
    return props


def property_requests(helper: dict[str, str]) -> list[dict[str, Any]]:
    requests: list[dict[str, Any]] = []
    for index in range(1, 32):
        name = helper.get(f"wifi_hal_composite_start.property_service_shim.request.{index}.name")
        if not name:
            continue
        requests.append({
            "index": index,
            "name": name,
            "value": helper.get(f"wifi_hal_composite_start.property_service_shim.request.{index}.value", ""),
            "allowed": int_value(
                helper.get(f"wifi_hal_composite_start.property_service_shim.request.{index}.allowed")
            ),
            "result": helper.get(f"wifi_hal_composite_start.property_service_shim.request.{index}.result", ""),
        })
    return requests


def parse_needed(dynamic_text: str) -> list[str]:
    return [match.group("name") for match in NEEDED_RE.finditer(dynamic_text)]


def find_android_reference() -> dict[str, Any]:
    scanned: list[str] = []
    best: dict[str, Any] = {"path": "", "props": {}, "online": False}
    for candidate in ANDROID_PROP_CANDIDATES:
        text = read_text(candidate)
        if not text:
            continue
        scanned.append(rel(candidate))
        props = parse_property_lines(text)
        online = (
            props.get("vendor.peripheral.SDX50M.state") == "ONLINE"
            and props.get("vendor.peripheral.modem.state") == "ONLINE"
        )
        if online:
            return {"path": rel(candidate), "props": props, "online": True, "scanned": scanned}
        if not best["path"] and props:
            best = {"path": rel(candidate), "props": props, "online": False}
    best["scanned"] = scanned
    return best


def v862_service(manifest: dict[str, Any], name: str) -> dict[str, Any]:
    contract = manifest.get("android_init_contract") if isinstance(manifest.get("android_init_contract"), dict) else {}
    services = contract.get("services") if isinstance(contract.get("services"), dict) else {}
    service = services.get(name)
    return service if isinstance(service, dict) else {}


def analyze() -> dict[str, Any]:
    v1614_manifest = read_json(V1614_MANIFEST)
    v862_manifest = read_json(V862_MANIFEST)
    v1081_manifest = read_json(V1081_MANIFEST)
    helper_text = read_text(V1614_HELPER)
    helper = parse_kv(helper_text)
    requests = property_requests(helper)
    request_pairs = {(item["name"], item["value"]) for item in requests}
    helper_source = read_text(HELPER_SOURCE)
    wrapper_source = read_text(INIT_WRAPPER_SOURCE)
    dynamic = read_text(V1073_ANALYSIS / "pm-service.dynamic.txt")
    symbols = read_text(V1073_ANALYSIS / "pm-service.symbols.txt")
    strings_text = read_text(V1073_ANALYSIS / "pm-service.strings.txt")
    libmdmdetect_strings = read_text(V1073_ANALYSIS / "libmdmdetect.so.strings.txt")
    libperipheral_strings = read_text(V1073_ANALYSIS / "libperipheral_client.so.strings.txt")
    pm_proxy_helper_rc = read_text(V1073_EXTRACT / "pm_proxy_helper.rc")
    android_ref = find_android_reference()
    progress = v1614_manifest.get("wifi_progress") if isinstance(v1614_manifest.get("wifi_progress"), dict) else {}

    needed = parse_needed(dynamic)
    v862_contract = v862_manifest.get("android_init_contract") if isinstance(v862_manifest.get("android_init_contract"), dict) else {}
    per_mgr = v862_service(v862_manifest, "vendor.per_mgr")
    per_proxy = v862_service(v862_manifest, "vendor.per_proxy")
    props = android_ref.get("props") if isinstance(android_ref.get("props"), dict) else {}

    runtime = {
        "v1614_decision": v1614_manifest.get("decision", ""),
        "v1615_report_exists": repo_path(V1615_REPORT).exists(),
        "handoff_pass": bool_value(v1614_manifest.get("handoff_pass")),
        "rollback_ok": bool_value((v1614_manifest.get("rollback") or {}).get("ok")),
        "progress_decision": progress.get("final_decision", ""),
        "provider_trigger": bool_value(progress.get("provider_trigger")),
        "rc1_progress": bool_value(progress.get("rc1_progress")),
        "mhi_progress": bool_value(progress.get("mhi_progress")),
        "wlfw_progress": bool_value(progress.get("wlfw_progress")),
        "wlan0_present": bool_value(progress.get("wlan0_present")),
        "nonstop_context_trace": int_value(
            helper.get("android_wifi_service_window.per_mgr_nonstop_context_trace")
        ),
        "child_traced": int_value(helper.get("android_wifi_service_window.child.per_mgr.traced")),
        "startup_exit_code": int_value(
            helper.get("android_wifi_service_window.per_mgr_startup_trace.exit_code")
        ),
        "startup_signal": int_value(
            helper.get("android_wifi_service_window.per_mgr_startup_trace.signal")
        ),
        "child_exit_code": int_value(helper.get("android_wifi_service_window.child.per_mgr.exit_code")),
        "child_signal": int_value(helper.get("android_wifi_service_window.child.per_mgr.signal")),
        "last_alive_ms": int_value(
            helper.get("android_wifi_service_window.per_mgr_startup_trace.last_alive_ms")
        ),
        "first_child_done_ms": int_value(
            helper.get("android_wifi_service_window.per_mgr_startup_trace.first_child_done_ms")
        ),
        "first_gone_ms": int_value(
            helper.get("android_wifi_service_window.per_mgr_startup_trace.first_gone_ms")
        ),
        "max_subsys_modem_fd": int_value(
            helper.get("android_wifi_service_window.per_mgr_startup_trace.max_subsys_modem_fd")
        ),
        "max_subsys_esoc0_fd": int_value(
            helper.get("android_wifi_service_window.per_mgr_startup_trace.max_subsys_esoc0_fd")
        ),
        "max_vndbinder_fd": int_value(
            helper.get("android_wifi_service_window.per_mgr_startup_trace.max_vndbinder_fd")
        ),
        "max_socket_fd": int_value(
            helper.get("android_wifi_service_window.per_mgr_startup_trace.max_socket_fd")
        ),
        "pm_full_contract_seen": int_value(helper.get("android_wifi_service_window.pm_full_contract_seen")),
        "subsys_esoc0_open_attempted": int_value(
            helper.get("android_wifi_service_window.subsys_esoc0_open_attempted")
        ),
        "property_request_count": int_value(
            helper.get("wifi_hal_composite_start.property_service_shim.request_count")
        ),
        "property_requests": requests,
        "offline_requests_only": request_pairs == {
            ("hwservicemanager.ready", "true"),
            ("vendor.peripheral.SDX50M.state", "OFFLINE"),
            ("vendor.peripheral.modem.state", "OFFLINE"),
        },
    }

    binary = {
        "pm_service_exists": repo_path(V1073_EXTRACT / "pm-service").exists(),
        "needed": needed,
        "has_binder_dependency": "libbinder.so" in needed,
        "has_qmi_csi_dependency": "libqmi_csi.so" in needed,
        "has_qmi_cci_dependency": "libqmi_cci.so" in needed,
        "has_mdmdetect_dependency": "libmdmdetect.so" in needed,
        "has_peripheral_client_dependency": "libperipheral_client.so" in needed,
        "symbol_get_system_info": "get_system_info" in symbols,
        "symbol_property_set": "property_set" in symbols,
        "symbol_qmi_csi_register": "qmi_csi_register" in symbols,
        "symbol_default_service_manager": "defaultServiceManager" in symbols,
        "string_vndbinder": "/dev/vndbinder" in strings_text,
        "string_service_name": "vendor.qcom.PeripheralManager" in strings_text,
        "string_online": "ONLINE" in strings_text,
        "string_offline": "OFFLINE" in strings_text,
        "string_shutdown_list": "vendor.peripheral.shutdown_critical_list" in strings_text,
        "libmdmdetect_has_sysfs_inputs": all(
            item in libmdmdetect_strings
            for item in ("/sys/bus/msm_subsys/devices", "/sys/bus/esoc/devices", "/dev/subsys_%s")
        ),
        "libperipheral_client_uses_vndbinder": "/dev/vndbinder" in libperipheral_strings,
    }

    init_contract = {
        "per_mgr": per_mgr,
        "per_proxy": per_proxy,
        "per_mgr_running_action": v862_contract.get("per_mgr_running_action", []),
        "sys_shutdown_action": v862_contract.get("sys_shutdown_action", []),
        "pm_proxy_helper_rc_present": bool(pm_proxy_helper_rc),
        "pm_proxy_helper_post_fs_data_start": "on post-fs-data" in pm_proxy_helper_rc
        and "start vendor.per_proxy_helper" in pm_proxy_helper_rc,
        "android_v862_decision": v862_manifest.get("decision", ""),
    }

    current_helper_contract = {
        "has_ioprio_rt4": "apply_peripheral_manager_ioprio_rt4_contract" in helper_source,
        "has_per_proxy_helper": "per_proxy_helper" in helper_source,
        "has_init_svc_per_mgr_running_gate": "init.svc.vendor.per_mgr=running" in helper_source,
        "has_shutdown_critical_list_allow": "vendor.peripheral.shutdown_critical_list" in helper_source,
        "has_property_offline_allow": "vendor.peripheral.SDX50M.state" in helper_source
        and "vendor.peripheral.modem.state" in helper_source,
        "wrapper_can_enable_nonstop_context": (
            "A90_WIFI_TEST_BOOT_ANDROID_SERVICE_WINDOW_PER_MGR_NONSTOP_CONTEXT_TRACE" in wrapper_source
        ),
    }

    android_good = {
        "property_source": android_ref.get("path", ""),
        "scanned_property_sources": android_ref.get("scanned", []),
        "per_mgr_running": props.get("init.svc.vendor.per_mgr") == "running",
        "per_proxy_running": props.get("init.svc.vendor.per_proxy") == "running",
        "per_proxy_helper_state": props.get("init.svc.vendor.per_proxy_helper", ""),
        "sdx50m_state": props.get("vendor.peripheral.SDX50M.state", ""),
        "modem_state": props.get("vendor.peripheral.modem.state", ""),
        "shutdown_critical_list": props.get("vendor.peripheral.shutdown_critical_list", ""),
        "peripherals_online": props.get("vendor.peripheral.SDX50M.state") == "ONLINE"
        and props.get("vendor.peripheral.modem.state") == "ONLINE",
        "has_shutdown_critical_pair": props.get("vendor.peripheral.shutdown_critical_list", "").strip()
        == "SDX50M modem",
    }

    prior_static = {
        "v1081_decision": v1081_manifest.get("decision", ""),
        "v1081_server_setup_not_reached": bool_value(
            ((v1081_manifest.get("analysis") or {}).get("server_setup_not_reached"))
        ),
        "v1081_get_system_info_path": "get_system_info" in json.dumps(
            (v1081_manifest.get("analysis") or {}).get("inferred_path", []),
            ensure_ascii=False,
        ),
    }

    checks = {
        "v1615_current_boundary_valid": runtime["handoff_pass"]
        and runtime["rollback_ok"]
        and runtime["nonstop_context_trace"] == 1
        and runtime["child_traced"] == 0,
        "pm_service_natural_clean_exit": runtime["startup_exit_code"] == 0
        and runtime["startup_signal"] == 0
        and runtime["child_exit_code"] == 0
        and runtime["child_signal"] == 0
        and 0 <= runtime["last_alive_ms"] <= 25
        and 0 <= runtime["first_gone_ms"] <= 60,
        "pm_service_exits_before_ipc_or_pm_fd": runtime["max_subsys_modem_fd"] == 0
        and runtime["max_subsys_esoc0_fd"] == 0
        and runtime["max_vndbinder_fd"] == 0
        and runtime["max_socket_fd"] == 0
        and runtime["pm_full_contract_seen"] == 0
        and runtime["subsys_esoc0_open_attempted"] == 0,
        "current_runtime_only_publishes_offline": runtime["property_request_count"] == 3
        and runtime["offline_requests_only"],
        "binary_has_persistent_server_stack": binary["has_binder_dependency"]
        and binary["has_qmi_csi_dependency"]
        and binary["has_mdmdetect_dependency"]
        and binary["has_peripheral_client_dependency"]
        and binary["symbol_get_system_info"]
        and binary["symbol_property_set"]
        and binary["symbol_qmi_csi_register"]
        and binary["symbol_default_service_manager"]
        and binary["string_service_name"],
        "android_init_contract_known": per_mgr.get("path") == "/vendor/bin/pm-service"
        and per_mgr.get("ioprio") == "rt 4"
        and "start vendor.per_proxy" in init_contract["per_mgr_running_action"]
        and init_contract["pm_proxy_helper_post_fs_data_start"],
        "current_source_models_old_init_gaps": all(current_helper_contract.values()),
        "android_good_keeps_peripheral_online": android_good["per_mgr_running"]
        and android_good["per_proxy_running"]
        and android_good["peripherals_online"]
        and android_good["has_shutdown_critical_pair"],
        "prior_get_system_info_boundary_relevant": prior_static["v1081_server_setup_not_reached"]
        and prior_static["v1081_get_system_info_path"],
        "downstream_wifi_still_absent": not runtime["provider_trigger"]
        and not runtime["rc1_progress"]
        and not runtime["mhi_progress"]
        and not runtime["wlfw_progress"]
        and not runtime["wlan0_present"],
    }

    pass_result = all(checks.values())
    decision = (
        "v1616-pm-service-clean-exit-is-offline-system-info-contract-gap"
        if pass_result
        else "v1616-pm-service-launch-contract-needs-review"
    )
    reason = (
        "Current native pm-service reaches only the offline property publication path and exits cleanly before binder/QMI/PM fd setup, while Android-good keeps per_mgr/per_proxy running with SDX50M/modem ONLINE; the next gap is the mdmdetect/get_system_info input contract, not lower RC1/MHI"
        if pass_result
        else "Existing evidence does not fully prove the pm-service offline system-info contract gap"
    )

    next_gate = {
        "recommended_cycle": "V1617",
        "type": "source/build-only non-ptrace pm-service system-info surface capture",
        "focus": (
            "capture exact libmdmdetect/get_system_info input surfaces around pm-service startup "
            "without ptrace: /sys/bus/msm_subsys/devices, /sys/bus/esoc/devices, "
            "/sys/class/esoc-dev, /dev/subsys_*, /dev/esoc-*, /dev/vndbinder, "
            "private property root and service-manager sockets"
        ),
        "why": (
            "V1616 proves property coverage and old init-contract gaps are not the active blocker; "
            "pm-service is making an OFFLINE-only decision before it reaches its persistent Binder/QMI server path"
        ),
        "hard_gates": [
            "no pm-service syscall ptrace",
            "no mdm_helper ptrace",
            "no direct /dev/subsys_esoc0 open",
            "no Wi-Fi HAL start",
            "no scan/connect/credentials",
            "no DHCP/routes/external ping",
            "no PMIC/GPIO/GDSC direct write",
            "no blind eSoC notify/BOOT_DONE spoof",
            "no global PCI rescan",
            "no platform bind/unbind",
        ],
    }

    return {
        "decision": decision,
        "pass": pass_result,
        "reason": reason,
        "checks": checks,
        "runtime": runtime,
        "binary": binary,
        "init_contract": init_contract,
        "current_helper_contract": current_helper_contract,
        "android_good": android_good,
        "prior_static": prior_static,
        "next_gate": next_gate,
    }


def render_report(manifest: dict[str, Any]) -> str:
    analysis = manifest["analysis"]
    runtime = analysis["runtime"]
    android_good = analysis["android_good"]
    next_gate = analysis["next_gate"]
    binary = analysis["binary"]
    init_contract = analysis["init_contract"]
    helper_contract = analysis["current_helper_contract"]
    prior_static = analysis["prior_static"]
    return "\n".join([
        "# Native Init V1616 pm-service Launch Contract Classifier",
        "",
        "## Summary",
        "",
        "- Cycle: `V1616`",
        "- Type: host-only classifier over V1614/V1615, V862, V1073, V1081, and Android-good property evidence",
        f"- Decision: `{manifest['decision']}`",
        f"- Result: `{'PASS' if manifest['pass'] else 'FAIL'}`",
        f"- Reason: {manifest['reason']}",
        f"- Evidence: `{manifest['out_dir']}`",
        "",
        "## Inputs",
        "",
        markdown_table(
            ["input", "path"],
            [
                ["v1614_manifest", rel(V1614_MANIFEST)],
                ["v1614_helper", rel(V1614_HELPER)],
                ["v1615_report", rel(V1615_REPORT)],
                ["v862_manifest", rel(V862_MANIFEST)],
                ["v1073_extract", rel(V1073_EXTRACT)],
                ["v1073_analysis", rel(V1073_ANALYSIS)],
                ["v1081_manifest", rel(V1081_MANIFEST)],
                ["android_good_props", android_good["property_source"]],
            ],
        ),
        "",
        "## Checks",
        "",
        markdown_table(
            ["check", "value"],
            [[name, str(value)] for name, value in analysis["checks"].items()],
        ),
        "",
        "## Current Native Runtime",
        "",
        markdown_table(
            ["field", "value"],
            [
                ["handoff_pass", str(runtime["handoff_pass"])],
                ["rollback_ok", str(runtime["rollback_ok"])],
                ["nonstop_context_trace", str(runtime["nonstop_context_trace"])],
                ["child_traced", str(runtime["child_traced"])],
                ["startup_exit_code", str(runtime["startup_exit_code"])],
                ["startup_signal", str(runtime["startup_signal"])],
                ["last_alive_ms", str(runtime["last_alive_ms"])],
                ["first_gone_ms", str(runtime["first_gone_ms"])],
                ["max_subsys_modem_fd", str(runtime["max_subsys_modem_fd"])],
                ["max_subsys_esoc0_fd", str(runtime["max_subsys_esoc0_fd"])],
                ["max_vndbinder_fd", str(runtime["max_vndbinder_fd"])],
                ["max_socket_fd", str(runtime["max_socket_fd"])],
                ["property_request_count", str(runtime["property_request_count"])],
                ["provider_trigger", str(runtime["provider_trigger"])],
                ["wlan0_present", str(runtime["wlan0_present"])],
            ],
        ),
        "",
        "## Property Requests",
        "",
        markdown_table(
            ["index", "name", "value", "allowed", "result"],
            [
                [str(item["index"]), item["name"], item["value"], str(item["allowed"]), item["result"]]
                for item in runtime["property_requests"]
            ],
        ),
        "",
        "## Android-good Contrast",
        "",
        markdown_table(
            ["field", "value"],
            [
                ["source", android_good["property_source"]],
                ["init.svc.vendor.per_mgr", str(android_good["per_mgr_running"])],
                ["init.svc.vendor.per_proxy", str(android_good["per_proxy_running"])],
                ["init.svc.vendor.per_proxy_helper", android_good["per_proxy_helper_state"]],
                ["vendor.peripheral.SDX50M.state", android_good["sdx50m_state"]],
                ["vendor.peripheral.modem.state", android_good["modem_state"]],
                ["vendor.peripheral.shutdown_critical_list", android_good["shutdown_critical_list"]],
            ],
        ),
        "",
        "## Binary and Init Contract",
        "",
        markdown_table(
            ["surface", "value"],
            [
                ["pm-service NEEDED", ", ".join(binary["needed"])],
                ["persistent server symbols", str(binary["symbol_qmi_csi_register"] and binary["symbol_default_service_manager"])],
                ["mdmdetect sysfs inputs", str(binary["libmdmdetect_has_sysfs_inputs"])],
                ["service literal", str(binary["string_service_name"])],
                ["per_mgr rc path", str((init_contract["per_mgr"] or {}).get("path", ""))],
                ["per_mgr ioprio", str((init_contract["per_mgr"] or {}).get("ioprio", ""))],
                ["per_proxy start action", ", ".join(init_contract["per_mgr_running_action"])],
                ["pm_proxy_helper post-fs-data", str(init_contract["pm_proxy_helper_post_fs_data_start"])],
            ],
        ),
        "",
        "## Current Helper Coverage",
        "",
        markdown_table(
            ["contract", "modelled"],
            [[name, str(value)] for name, value in helper_contract.items()],
        ),
        "",
        "## Interpretation",
        "",
        (
            "V1616 keeps the V1615 runtime boundary but adds static and Android-good "
            "context.  `pm-service` is capable of a persistent Binder/QMI server path: "
            "the binary imports Binder, QMI CSI/CCI, `libmdmdetect`, "
            "`libperipheral_client`, `get_system_info`, `property_set`, and "
            "`qmi_csi_register`.  The current native run does not reach that path.  It "
            "publishes only `hwservicemanager.ready=true`, "
            "`vendor.peripheral.SDX50M.state=OFFLINE`, and "
            "`vendor.peripheral.modem.state=OFFLINE`, then exits cleanly before any "
            "`/dev/vndbinder`, socket, `/dev/subsys_modem`, or `/dev/subsys_esoc0` fd.  "
            "Android-good evidence instead keeps `vendor.per_mgr` and "
            "`vendor.per_proxy` running and reports SDX50M/modem `ONLINE` plus "
            "`vendor.peripheral.shutdown_critical_list=SDX50M modem `.  Therefore the "
            "active blocker is the system-info/peripheral-state input contract that "
            "makes `pm-service` decide both peripherals are OFFLINE, not RC1/MHI/WLFW."
        ),
        "",
        "Prior V1081 remains relevant: it proved the early stripped-binary boundary "
        f"`{prior_static['v1081_decision']}` where `get_system_info` prevents Binder/QMI setup.  "
        "The current path has advanced from hard failure to OFFLINE-only publication, "
        "but still needs the exact `libmdmdetect` input surface classified.",
        "",
        "## Next Gate",
        "",
        f"- Recommended cycle: `{next_gate['recommended_cycle']}`",
        f"- Type: {next_gate['type']}",
        f"- Focus: {next_gate['focus']}",
        f"- Rationale: {next_gate['why']}",
        "",
        "### Hard Gates",
        "",
        "\n".join(f"- {item}" for item in next_gate["hard_gates"]),
        "",
        "## Safety Scope",
        "",
        "This classifier is host-only. It performs no device command, flash, reboot, "
        "partition write, daemon start, Wi-Fi HAL start, scan/connect, credential "
        "handling, DHCP/routes, external ping, PMIC/GPIO/GDSC write, blind eSoC "
        "notify/`BOOT_DONE` spoof, pci-msm debugfs write, global PCI rescan, or "
        "platform bind/unbind.",
        "",
    ])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    args = parser.parse_args()

    out_dir = repo_path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    store = EvidenceStore(out_dir)
    analysis = analyze()
    manifest = {
        "generated_at": now_iso(),
        "cycle": "V1616",
        "type": "host-only pm-service launch/dependency contract classifier",
        "decision": analysis["decision"],
        "pass": analysis["pass"],
        "reason": analysis["reason"],
        "out_dir": rel(args.out_dir),
        "inputs": {
            "v1614_manifest": rel(V1614_MANIFEST),
            "v1614_helper": rel(V1614_HELPER),
            "v1615_report": rel(V1615_REPORT),
            "v862_manifest": rel(V862_MANIFEST),
            "v1073_extract": rel(V1073_EXTRACT),
            "v1073_analysis": rel(V1073_ANALYSIS),
            "v1081_manifest": rel(V1081_MANIFEST),
            "helper_source": rel(HELPER_SOURCE),
            "init_wrapper_source": rel(INIT_WRAPPER_SOURCE),
        },
        "analysis": analysis,
        "host": collect_host_metadata(),
        "hard_gates": {
            "device_contact_executed": False,
            "daemon_start_executed": False,
            "wifi_hal_start_executed": False,
            "scan_connect_executed": False,
            "credential_use_executed": False,
            "dhcp_route_executed": False,
            "external_ping_executed": False,
            "raw_esoc_ioctl_executed": False,
            "gpio_write_executed": False,
            "sysfs_write_executed": False,
            "boot_or_partition_write_executed": False,
        },
    }

    write_private_text(out_dir / "manifest.json", json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    write_private_text(out_dir / "summary.md", render_report(manifest))
    report_path = repo_path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(render_report(manifest), encoding="utf-8")
    LATEST_POINTER.parent.mkdir(parents=True, exist_ok=True)
    LATEST_POINTER.write_text(str(out_dir) + "\n", encoding="utf-8")
    print(json.dumps({"decision": manifest["decision"], "pass": manifest["pass"]}, indent=2))
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

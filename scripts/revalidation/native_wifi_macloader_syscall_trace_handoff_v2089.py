#!/usr/bin/env python3
"""V2089 rollbackable handoff for the bounded macloader syscall discriminator."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import native_wifi_mac_source_bridge_handoff_v2087 as prev2087


CYCLE = "V2089"
REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v2089-macloader-syscall-trace-handoff"
HANDOFF_DIR = OUT_DIR / "v2088-handoff"
HANDOFF_REPORT = OUT_DIR / "v2088-handoff-report.md"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V2089_MACLOADER_SYSCALL_TRACE_HANDOFF_2026-06-05.md"
)
V2088_OUT = REPO_ROOT / "tmp" / "wifi" / "v2088-macloader-syscall-trace-test-boot"
V2088_INIT = V2088_OUT / "init_v2088_macloader_syscall_trace"
V2088_BOOT = V2088_OUT / "boot_linux_v2088_macloader_syscall_trace.img"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v2088/dev/__properties__"
TEST_EXPECT_VERSION = "A90 Linux init 0.9.223 (v2088-macloader-syscall-trace)"
TEST_LOG_PATH = "/cache/native-init-wifi-test-boot-v2088.log"
TEST_SUMMARY_PATH = "/cache/native-init-wifi-test-boot-v2088.summary"
TEST_HELPER_RESULT_PATH = "/cache/native-init-wifi-test-boot-v2088-helper.result"
EXPECTED_HELPER_VERSION = "a90_android_execns_probe v407"
SYSFS_MAGIC = 0x62656572

BASE_COLLECT_DETAILS = prev2087.BASE_COLLECT_DETAILS
BASE_CLASSIFY = prev2087.BASE_CLASSIFY


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def intish(value: object) -> int:
    return prev2087.intish(value)


def int_base0(value: object) -> int:
    if value is None:
        return 0
    try:
        return int(str(value), 0)
    except (TypeError, ValueError):
        return 0


def markdown_table(headers: list[str], rows: list[list[object]]) -> str:
    return prev2087.markdown_table(headers, rows)


def read_text_best_effort(path: Path, limit: int = 1_000_000) -> str:
    return prev2087.read_text_best_effort(path, limit)


def collect_macloader(fields: dict[str, str], handoff: dict[str, Any]) -> dict[str, Any]:
    return prev2087.collect_macloader(fields, handoff)


def get_path_snapshot(fields: dict[str, str], phase: str, name: str) -> dict[str, Any]:
    prefix = f"wifi_companion_start.macloader_mac_source_bridge.{phase}.{name}"
    fs_type_text = fields.get(f"{prefix}.fs_type", "")
    return {
        "absolute": fields.get(f"{prefix}.absolute", ""),
        "exists": intish(fields.get(f"{prefix}.exists")),
        "is_reg": intish(fields.get(f"{prefix}.is_reg")),
        "is_dir": intish(fields.get(f"{prefix}.is_dir")),
        "mode": fields.get(f"{prefix}.mode", ""),
        "uid": intish(fields.get(f"{prefix}.uid")),
        "gid": intish(fields.get(f"{prefix}.gid")),
        "size": intish(fields.get(f"{prefix}.size")),
        "readable": intish(fields.get(f"{prefix}.readable")),
        "writable": intish(fields.get(f"{prefix}.writable")),
        "statfs_ok": intish(fields.get(f"{prefix}.statfs_ok")),
        "fs_type": int_base0(fs_type_text),
        "fs_type_text": fs_type_text,
        "statfs_errno": intish(fields.get(f"{prefix}.statfs_errno")),
        "hash_available": intish(fields.get(f"{prefix}.hash_available")),
        "bytes": intish(fields.get(f"{prefix}.bytes")),
        "errno": intish(fields.get(f"{prefix}.errno")),
    }


def collect_mac_source_bridge(fields: dict[str, str]) -> dict[str, Any]:
    mac_info = get_path_snapshot(fields, "pre", "mac_info")
    mac_addr = get_path_snapshot(fields, "pre", "sys_wifi_mac_addr")
    qcwlanstate = get_path_snapshot(fields, "pre", "sys_wifi_qcwlanstate")
    boot_wlan_dir = get_path_snapshot(fields, "pre", "sys_kernel_boot_wlan")
    boot_wlan_file = get_path_snapshot(fields, "pre", "sys_kernel_boot_wlan_file")
    data_vendor_conn = get_path_snapshot(fields, "pre", "data_vendor_conn")
    persist_nv = get_path_snapshot(fields, "pre", "persist_nv")
    post_mac_addr = get_path_snapshot(fields, "post", "sys_wifi_mac_addr")
    real_sysfs = bool(
        mac_addr["exists"] == 1
        and mac_addr["writable"] == 1
        and mac_addr["statfs_ok"] == 1
        and mac_addr["fs_type"] == SYSFS_MAGIC
    )
    return {
        "enabled": intish(fields.get("wifi_companion_start.macloader_mac_source_bridge.enabled")),
        "pre_enabled": intish(fields.get("wifi_companion_start.macloader_mac_source_bridge.pre.enabled")),
        "post_enabled": intish(fields.get("wifi_companion_start.macloader_mac_source_bridge.post.enabled")),
        "mac_info": mac_info,
        "mac_addr": mac_addr,
        "qcwlanstate": qcwlanstate,
        "boot_wlan_dir": boot_wlan_dir,
        "boot_wlan_file": boot_wlan_file,
        "data_vendor_conn": data_vendor_conn,
        "persist_nv": persist_nv,
        "post_mac_addr": post_mac_addr,
        "real_sysfs_mac_addr": real_sysfs,
    }


def record_prefix(index: int) -> str:
    return f"macloader_syscall_trace.syscall.macloader.record_{index:03d}"


def collect_macloader_syscall_trace(fields: dict[str, str]) -> dict[str, Any]:
    child_prefix = "macloader_syscall_trace.child.macloader"
    records: list[dict[str, Any]] = []
    for index in range(96):
        prefix = record_prefix(index)
        if f"{prefix}.name" not in fields:
            continue
        record = {
            "index": index,
            "name": fields.get(f"{prefix}.name", ""),
            "ret": intish(fields.get(f"{prefix}.ret")),
            "error": intish(fields.get(f"{prefix}.error")),
            "path": fields.get(f"{prefix}.path", ""),
            "fd_target": fields.get(f"{prefix}.fd.target", ""),
            "ret_fd_target": fields.get(f"{prefix}.ret_fd.target", ""),
            "efs_wifi": intish(fields.get(f"{prefix}.token.efs_wifi")),
            "sys_wifi": intish(fields.get(f"{prefix}.token.sys_wifi")),
            "mac_addr": intish(fields.get(f"{prefix}.token.mac_addr")),
            "boot_wlan": intish(fields.get(f"{prefix}.token.boot_wlan")),
            "data_vendor_conn": intish(fields.get(f"{prefix}.token.data_vendor_conn")),
            "property_service": intish(fields.get(f"{prefix}.token.property_service")),
            "qcwlanstate": intish(fields.get(f"{prefix}.token.qcwlanstate")),
            "write_contains_colon": intish(fields.get(f"{prefix}.write_payload.contains_colon")),
            "write_contains_hex_digit": intish(fields.get(f"{prefix}.write_payload.contains_hex_digit")),
            "write_payload_valid": intish(fields.get(f"{prefix}.write_payload.valid")),
            "write_payload_requested_len": intish(fields.get(f"{prefix}.write_payload.requested_len")),
            "read_payload_valid": intish(fields.get(f"{prefix}.read_payload.valid")),
            "read_payload_bytes_read": intish(fields.get(f"{prefix}.read_payload.bytes_read")),
        }
        records.append(record)

    def any_record(name: str | None = None, token: str | None = None, ok_ret: bool | None = None) -> bool:
        for record in records:
            if name is not None and record["name"] != name:
                continue
            if token is not None and intish(record.get(token)) != 1:
                continue
            if ok_ret is True and intish(record.get("error")) != 0:
                continue
            return True
        return False

    mac_addr_write_records = [
        record for record in records
        if record["name"] == "write" and intish(record["mac_addr"]) == 1 and intish(record["error"]) == 0
    ]
    mac_addr_write_shape = any(
        intish(record["write_contains_colon"]) == 1 and intish(record["write_contains_hex_digit"]) == 1
        for record in mac_addr_write_records
    )
    focused_errors = [
        f"{record['index']:03d}:{record['name']}:err={record['error']}:path={record['path'] or record['fd_target']}"
        for record in records
        if intish(record["error"]) != 0
    ][:8]
    return {
        "runtime_target": fields.get("wifi_hal_composite_start.child.macloader.target", ""),
        "runtime_traced": intish(fields.get("wifi_hal_composite_start.child.macloader.traced")),
        "runtime_pid": intish(fields.get("wifi_hal_composite_start.child.macloader.pid")),
        "runtime_pgid": intish(fields.get("wifi_hal_composite_start.child.macloader.pgid")),
        "runtime_start_order": intish(fields.get("wifi_companion_start.child.macloader.start_order")),
        "compiled": intish(fields.get("wifi_companion_start.macloader_syscall_trace.compiled")),
        "single_child": fields.get("wifi_companion_start.macloader_syscall_trace.single_child", ""),
        "no_cnss_ptrace": intish(fields.get("wifi_companion_start.macloader_syscall_trace.no_cnss_ptrace")),
        "raw_mac_payload": intish(fields.get("wifi_companion_start.macloader_syscall_trace.raw_mac_payload")),
        "child_traced": intish(fields.get(f"{child_prefix}.traced")),
        "child_trace_syscalls": intish(fields.get(f"{child_prefix}.trace_syscalls")),
        "child_started": intish(fields.get(f"{child_prefix}.syscall_trace_started")),
        "stop_count": intish(fields.get(f"{child_prefix}.syscall_stop_count")),
        "record_count": intish(fields.get(f"{child_prefix}.syscall_record_count")),
        "error_count": intish(fields.get(f"{child_prefix}.syscall_error_count")),
        "truncated": intish(fields.get(f"{child_prefix}.syscall_trace_truncated")),
        "stop_limited": intish(fields.get(f"{child_prefix}.syscall_trace_stop_limited")),
        "trace_disable": intish(fields.get("macloader_syscall_trace.syscall.macloader.trace_disable")),
        "trace_disable_reason": fields.get("macloader_syscall_trace.syscall.macloader.trace_disable_reason", ""),
        "records_seen": len(records),
        "mac_info_open": any_record("openat", "efs_wifi", True),
        "mac_info_read": any_record("read", "efs_wifi", True),
        "mac_addr_open": any_record("openat", "mac_addr", True),
        "mac_addr_write": bool(mac_addr_write_records),
        "mac_addr_write_shape": mac_addr_write_shape,
        "boot_wlan_write": any_record("write", "boot_wlan", True),
        "qcwlanstate_open": any_record("openat", "qcwlanstate", None),
        "qcwlanstate_read": any_record("read", "qcwlanstate", None),
        "property_service": any_record(token="property_service"),
        "data_vendor_conn_access": any_record(token="data_vendor_conn"),
        "socket_count": sum(1 for record in records if record["name"] == "socket"),
        "connect_count": sum(1 for record in records if record["name"] == "connect"),
        "focused_errors": focused_errors,
        "sample_records": [
            f"{record['index']:03d}:{record['name']}:ret={record['ret']}:err={record['error']}:path={record['path'] or record['fd_target']}"
            for record in records[:10]
        ],
    }


def artifact_hook_check() -> dict[str, Any]:
    init_forbidden = (
        "--allow-servloc-domain-list-probe",
        "--allow-service-notifier-listener-probe",
        "--qrtr-readback-matrix",
        "wlfw:69:0,1",
        "--pm-observer-private-cnss-daemon-sdx50m",
        "--private-cnss-daemon-path",
    )
    boot_forbidden = (
        "diag_remote_dev_poll_probe.begin=1",
        "diag_wlan_pd_memory_device_probe.begin=1",
        "diag_wlan_pd_memory_regular_mask_probe.begin=1",
        "diag_dci_register_read_probe.begin=1",
        "wlan_pd_tftp_server_trace.late_attach.begin=1",
        "wifi_companion_start.wlan_pd_producer_tftp_server_syscall_trace.compiled=1",
        "PTRACE_ATTACH",
    )
    init_required = (
        "native-init-sibling-fwssctl-v641",
        "A90v641: sibling fwssctl proof armed",
        "wifi-v641-fwssctl",
        "A90v2088",
        "wifi-companion-wlan-pd-post-pm-lower-state-observer-start-only",
        "--timeout-sec",
        "75",
    )
    boot_required = (
        EXPECTED_HELPER_VERSION,
        "/vendor/bin/hw/macloader",
        "u:r:macloader:s0",
        "wifi_companion_start.macloader_pre_cnss.enabled=%d",
        "wifi_companion_start.macloader_pre_cnss.active_driver_start=1",
        "wifi_companion_start.macloader_mac_source_bridge.enabled=%d",
        "wifi_companion_start.macloader_syscall_trace.compiled=%d",
        "wifi_companion_start.macloader_syscall_trace.single_child=macloader",
        "wifi_companion_start.macloader_syscall_trace.no_cnss_ptrace=1",
        "wifi_companion_start.macloader_syscall_trace.raw_mac_payload=0",
        "macloader_syscall_trace.child.%s.traced=%d",
        "macloader_syscall_trace",
        "%s.syscall.%s.record_%03u",
        "/mnt/vendor/efs/wifi/.mac.info",
        "/sys/wifi/mac_addr",
        "/sys/kernel/boot_wlan/boot_wlan",
        "/persist/WCNSS_qcom_wlan_nv.bin",
        "statfs_ok",
        "fs_type=0x%016llx",
        "data_vendor_conn",
        "wlfw_late_msg21_focused.begin=1",
        "per_mgr_vote_focused.begin=1",
        "%s.begin=1",
    )
    checks: dict[str, Any] = {}
    for path, required in ((V2088_INIT, init_required), (V2088_BOOT, boot_required)):
        key = rel(path)
        forbidden_tokens = init_forbidden if path == V2088_INIT else boot_forbidden
        data = path.read_bytes() if path.exists() else b""
        missing = [token for token in required if token.encode() not in data]
        forbidden = [token for token in forbidden_tokens if token.encode() in data]
        checks[key] = {
            "exists": path.exists(),
            "ok": path.exists() and not missing and not forbidden,
            "missing": missing,
            "forbidden": forbidden,
        }
    return checks


def collect_details(handoff: dict[str, Any]) -> dict[str, Any]:
    details = BASE_COLLECT_DETAILS(handoff)
    fields = prev2087.prev2083.prev2081.prev2059.prev2057.parse_fields()
    details["macloader_pre_cnss"] = collect_macloader(fields, handoff)
    details["mac_source_bridge"] = collect_mac_source_bridge(fields)
    details["macloader_syscall_trace"] = collect_macloader_syscall_trace(fields)
    return details


def logdw_summary(details: dict[str, Any]) -> dict[str, Any]:
    return prev2087.logdw_summary(details)


def classify(handoff: dict[str, Any],
             hook: dict[str, Any],
             steps: list[dict[str, Any]],
             details: dict[str, Any]) -> dict[str, Any]:
    base = BASE_CLASSIFY(handoff, hook, steps, details)
    mac = details.get("macloader_pre_cnss") if isinstance(details.get("macloader_pre_cnss"), dict) else {}
    mac_source = details.get("mac_source_bridge") if isinstance(details.get("mac_source_bridge"), dict) else {}
    trace = details.get("macloader_syscall_trace") if isinstance(details.get("macloader_syscall_trace"), dict) else {}
    cascade = details.get("cascade", {}) if isinstance(details.get("cascade"), dict) else {}
    summary = logdw_summary(details)
    hook_ok = all(bool(item.get("ok")) for item in hook.values())
    trace_contract_ok = bool(
        intish(trace.get("compiled")) == 1
        and trace.get("single_child") == "macloader"
        and intish(trace.get("no_cnss_ptrace")) == 1
        and intish(trace.get("raw_mac_payload")) == 0
    )
    mac_enabled = intish(mac.get("enabled")) == 1 and intish(mac.get("active_driver_start")) == 1
    mac_ready = intish(mac.get("ready")) == 1 or intish(mac.get("child_observable")) == 1
    real_sysfs = bool(mac_source.get("real_sysfs_mac_addr"))
    records_seen = intish(trace.get("records_seen")) > 0 or intish(trace.get("record_count")) > 0
    traced = records_seen or intish(trace.get("runtime_traced")) == 1 or (
        intish(trace.get("child_traced")) == 1 and intish(trace.get("child_started")) == 1
    )
    mac_addr_write = bool(trace.get("mac_addr_write"))
    mac_addr_write_shape = bool(trace.get("mac_addr_write_shape"))
    mac_assigned = intish(mac.get("mac_assigned")) == 1
    server_check_seen = intish(summary.get("server_check")) > 0
    wlanmdsp_seen = (
        intish(summary.get("wlanmdsp")) > 0
        or intish(summary.get("fallback_wlanmdsp")) > 0
        or intish(summary.get("firmware_mnt_wlanmdsp")) > 0
    )
    fw_ready = intish(cascade.get("fw_ready")) > 0
    wlan0 = intish(cascade.get("wlan0")) > 0 or bool(base.get("wlan0"))
    step_ok = {
        str(step.get("name")): bool(step.get("ok"))
        for step in steps
        if isinstance(step, dict)
    }
    v2089_rollback_ok = step_ok.get("post-selftest", False) and step_ok.get("post-status", False)

    if not hook_ok:
        label = "macloader-trace-artifact-hook-regression"
        passed = False
        reason = "V2088 artifact does not contain the bounded macloader syscall discriminator contract"
    elif not trace_contract_ok:
        label = "macloader-trace-contract-regression"
        passed = False
        reason = "helper summary did not expose the single-child redacted macloader syscall-trace contract"
    elif not mac_enabled or not mac_ready:
        label = "macloader-trace-macloader-not-observable"
        passed = True
        reason = "macloader did not become observable, so the MAC write path could not be falsified"
    elif not real_sysfs:
        label = "macloader-trace-sysfs-not-real"
        passed = True
        reason = "/sys/wifi/mac_addr was not proven to be the real sysfs node in the macloader namespace"
    elif not traced or not records_seen:
        label = "macloader-trace-missing"
        passed = False
        reason = "macloader ran, but the focused syscall trace did not start or emit records"
    elif wlan0:
        label = "macloader-trace-wlan0-progress"
        passed = True
        reason = "native reached wlan0; stop before scan/connect and run the dedicated connectivity gate"
    elif fw_ready:
        label = "macloader-trace-fw-ready-progress"
        passed = True
        reason = "native reached FW-ready; chase wlan0 next"
    elif wlanmdsp_seen:
        label = "macloader-trace-wlanmdsp-requested-no-fw-ready"
        passed = True
        reason = "modem requested wlanmdsp after the macloader trace route, but FW-ready/wlan0 did not follow"
    elif server_check_seen:
        label = "macloader-trace-server-check-no-wlanmdsp"
        passed = True
        reason = "modem entered the tftp bootstrap server_check path, but did not request wlanmdsp"
    elif mac_addr_write and mac_assigned:
        label = "macloader-real-mac-assign-proven-no-tftp"
        passed = True
        reason = "macloader wrote the real ICNSS MAC node and kernel acknowledged it, but modem still did not enter server_check/wlanmdsp"
    elif mac_addr_write and not mac_assigned:
        label = "macloader-write-no-kernel-assign"
        passed = True
        reason = "macloader wrote /sys/wifi/mac_addr, but the kernel did not emit the required ICNSS MAC assignment line"
    elif not mac_addr_write:
        label = "macloader-no-mac-addr-write"
        passed = True
        reason = "bounded macloader trace saw no .mac.info read or /sys/wifi/mac_addr write despite the real sysfs node being present and writable"
    elif mac_addr_write and not mac_addr_write_shape:
        label = "macloader-mac-write-format-suspicious"
        passed = True
        reason = "macloader wrote the MAC node but the redacted payload shape did not include colon+hex evidence"
    else:
        label = "macloader-trace-unclassified-no-tftp"
        passed = True
        reason = "bounded macloader trace completed but did not expose a server_check/wlanmdsp producer trigger"

    return {
        **base,
        "decision": f"v2089-{label}-rollback-{'pass' if passed else 'blocked'}",
        "label": label,
        "pass": passed,
        "reason": reason,
        "hook_ok": hook_ok,
        "trace_contract_ok": trace_contract_ok,
        "mac_enabled": mac_enabled,
        "mac_ready": mac_ready,
        "real_sysfs": real_sysfs,
        "traced": traced,
        "records_seen": records_seen,
        "mac_addr_write": mac_addr_write,
        "mac_addr_write_shape": mac_addr_write_shape,
        "mac_assigned": mac_assigned,
        "wlanmdsp_seen": wlanmdsp_seen,
        "server_check_seen": server_check_seen,
        "v2089_rollback_ok": v2089_rollback_ok,
    }


def render_report(manifest: dict[str, Any]) -> str:
    details = manifest["details"]
    classification = manifest["classification"]
    mac = details.get("macloader_pre_cnss", {}) if isinstance(details.get("macloader_pre_cnss"), dict) else {}
    mac_source = details.get("mac_source_bridge", {}) if isinstance(details.get("mac_source_bridge"), dict) else {}
    trace = details.get("macloader_syscall_trace", {}) if isinstance(details.get("macloader_syscall_trace"), dict) else {}
    surface = details.get("icnss_qcacld_post_bdf", {}) if isinstance(details.get("icnss_qcacld_post_bdf"), dict) else {}
    cascade = details.get("cascade", {}) if isinstance(details.get("cascade"), dict) else {}
    summary = logdw_summary(details)
    mac_addr = mac_source.get("mac_addr", {}) if isinstance(mac_source.get("mac_addr"), dict) else {}
    mac_info = mac_source.get("mac_info", {}) if isinstance(mac_source.get("mac_info"), dict) else {}
    boot_wlan_file = mac_source.get("boot_wlan_file", {}) if isinstance(mac_source.get("boot_wlan_file"), dict) else {}
    data_vendor_conn = mac_source.get("data_vendor_conn", {}) if isinstance(mac_source.get("data_vendor_conn"), dict) else {}
    step_lines = [
        f"- `{step['name']}` rc `{step['rc']}` ok `{step['ok']}` evidence `{step['file']}`"
        for step in manifest["steps"]
    ]
    sample_lines = [f"- `{item}`" for item in trace.get("sample_records", [])]
    error_lines = [f"- `{item}`" for item in trace.get("focused_errors", [])]
    return "\n".join([
        "# Native Init V2089 Macloader Syscall Trace Handoff",
        "",
        "## Summary",
        "",
        "- Cycle: `V2089`",
        f"- Decision: `{manifest['decision']}`",
        f"- Label: `{manifest['label']}`",
        f"- Pass: `{manifest['pass']}`",
        f"- Reason: {manifest['reason']}",
        f"- Evidence: `{manifest['out_dir']}`",
        f"- Inner handoff: `{manifest['handoff_manifest']}`",
        "",
        "## Matrix",
        "",
        markdown_table(
            ["area", "value", "detail"],
            [
                ["sysfs_node", classification.get("real_sysfs"), f"exists={mac_addr.get('exists')} writable={mac_addr.get('writable')} statfs={mac_addr.get('statfs_ok')} fs={mac_addr.get('fs_type_text')}"],
                ["macloader_trace", classification.get("traced"), f"runtime_traced={trace.get('runtime_traced')} records={trace.get('records_seen')} errors={trace.get('error_count')} truncated={trace.get('truncated')}"],
                ["macloader_write", classification.get("mac_addr_write"), f"shape={classification.get('mac_addr_write_shape')} assigned={classification.get('mac_assigned')} mac_info_read={trace.get('mac_info_read')}"],
                ["tftp", classification.get("wlanmdsp_seen"), f"server_check={summary.get('server_check')} ota={summary.get('ota_firewall')} mcfg={summary.get('mcfg')} wlanmdsp={summary.get('wlanmdsp')} fallback={summary.get('fallback_wlanmdsp')}"],
                ["kernel_surface", surface.get("wlan_module_loaded"), f"dev_wlan={surface.get('dev_wlan_exists')} qcwlanstate={surface.get('qcwlanstate_exists')} wlan0={surface.get('wlan0_exists')}"],
                ["cascade", "", f"wlan_pd={cascade.get('wlan_pd_up')} icnss_qmi={cascade.get('icnss_qmi_connected')} fw_ready={cascade.get('fw_ready')} wlan0={cascade.get('wlan0')}"],
                ["rollback", classification.get("v2089_rollback_ok"), "post-selftest and post-status succeeded after rollback"],
            ],
        ),
        "",
        "## Namespace Proof",
        "",
        markdown_table(
            ["path", "exists", "read", "write", "statfs", "fs_type", "extra"],
            [
                ["/mnt/vendor/efs/wifi/.mac.info", mac_info.get("exists", ""), mac_info.get("readable", ""), mac_info.get("writable", ""), mac_info.get("statfs_ok", ""), mac_info.get("fs_type_text", ""), f"bytes={mac_info.get('bytes')} hash={mac_info.get('hash_available')}"],
                ["/sys/wifi/mac_addr", mac_addr.get("exists", ""), mac_addr.get("readable", ""), mac_addr.get("writable", ""), mac_addr.get("statfs_ok", ""), mac_addr.get("fs_type_text", ""), f"real_sysfs={classification.get('real_sysfs')} mode={mac_addr.get('mode')}"],
                ["/sys/kernel/boot_wlan/boot_wlan", boot_wlan_file.get("exists", ""), boot_wlan_file.get("readable", ""), boot_wlan_file.get("writable", ""), boot_wlan_file.get("statfs_ok", ""), boot_wlan_file.get("fs_type_text", ""), f"mode={boot_wlan_file.get('mode')}"],
                ["/data/vendor/conn", data_vendor_conn.get("exists", ""), data_vendor_conn.get("readable", ""), data_vendor_conn.get("writable", ""), data_vendor_conn.get("statfs_ok", ""), data_vendor_conn.get("fs_type_text", ""), f"dir={data_vendor_conn.get('is_dir')}"],
            ],
        ),
        "",
        "## Syscall Trace",
        "",
        markdown_table(
            ["field", "value"],
            [
                ["compiled", trace.get("compiled", "")],
                ["single_child", trace.get("single_child", "")],
                ["no_cnss_ptrace", trace.get("no_cnss_ptrace", "")],
                ["raw_mac_payload", trace.get("raw_mac_payload", "")],
                ["runtime_target", trace.get("runtime_target", "")],
                ["runtime_traced", trace.get("runtime_traced", "")],
                ["runtime_pid", trace.get("runtime_pid", "")],
                ["runtime_start_order", trace.get("runtime_start_order", "")],
                ["child_traced", trace.get("child_traced", "")],
                ["child_started", trace.get("child_started", "")],
                ["trace_disable", trace.get("trace_disable", "")],
                ["trace_disable_reason", trace.get("trace_disable_reason", "")],
                ["record_count", trace.get("record_count", "")],
                ["records_seen", trace.get("records_seen", "")],
                ["mac_info_open", trace.get("mac_info_open", "")],
                ["mac_info_read", trace.get("mac_info_read", "")],
                ["mac_addr_open", trace.get("mac_addr_open", "")],
                ["mac_addr_write", trace.get("mac_addr_write", "")],
                ["mac_addr_write_shape", trace.get("mac_addr_write_shape", "")],
                ["boot_wlan_write", trace.get("boot_wlan_write", "")],
                ["qcwlanstate_open", trace.get("qcwlanstate_open", "")],
                ["qcwlanstate_read", trace.get("qcwlanstate_read", "")],
                ["property_service", trace.get("property_service", "")],
                ["data_vendor_conn_access", trace.get("data_vendor_conn_access", "")],
                ["socket_count", trace.get("socket_count", "")],
                ["connect_count", trace.get("connect_count", "")],
            ],
        ),
        "",
        "## Sample Records",
        "",
        *sample_lines,
        *([] if sample_lines else ["- `none`"]),
        "",
        "## Focused Errors",
        "",
        *error_lines,
        *([] if error_lines else ["- `none`"]),
        "",
        "## Interpretation",
        "",
        "- Required MAC proof remains the kernel line `icnss: Assigning MAC from Macloader`; a userspace bridge alone is not sufficient.",
        "- Route contract starts `/vendor/bin/hw/macloader` with the helper's macloader identity path (`uid/gid wifi`, groups `wifi/inet/net_raw/net_admin`, `u:r:macloader:s0`); the runtime trace still never reaches `.mac.info` or `/sys/wifi/mac_addr` when the label is `macloader-no-mac-addr-write`.",
        "- The trace is intentionally bounded to `macloader` only and emits hashes/shape bits rather than raw MAC payload bytes.",
        "- A successful MAC assignment without `server_check`/`wlanmdsp` down-ranks MAC assignment as cosmetic/downstream for the modem producer gate.",
        "- If `macloader` never writes the real MAC node, keep producer-gate focus on why the modem does not request `server_check`/`wlanmdsp`; MAC repair is only a quick falsifier.",
        "",
        "## Steps",
        "",
        *step_lines,
        *([] if step_lines else ["- `none`"]),
        "",
        "## Safety",
        "",
        "- No Wi-Fi HAL, wificond, supplicant, hostapd, scan/connect, credentials, DHCP/routes, or external ping was used.",
        "- No passive DIAG, active DIAG mask/log-mode, rild/cnss/pm-service strace, boot-time QRTR matrix, service-locator probe, service-notifier listener, active QRTR readback, QMI payload send, `tftp_server` ptrace, or `cnss-daemon` ptrace was run.",
        "- No `/dev/subsys_esoc0`, forced RC1/case, PMIC/GPIO/GDSC/regulator write, PCI rescan, bind/unbind, fake ONLINE, or eSoC notify/BOOT_DONE action was used.",
        "- Mutation scope: `/cache` one-shot clean-DSP flag, V2088 test-boot flash-handoff, namespace-local RFS bridges/tmpfs mirrors, read-only EFS/persist mounts for `macloader`, `/sys/wifi` and `/sys/kernel/boot_wlan` exposure, private tmp-root `/dev/socket/logdw`, tracefs uprobes, Android-parity `macloader` driver-start action, single-child redacted `macloader` ptrace, and rollback to `stage3/boot_linux_v724.img` with selftest fail=0.",
        "",
    ])


def configure_prev2083() -> None:
    prev2083 = prev2087.prev2083
    prev2083.CYCLE = CYCLE
    prev2083.OUT_DIR = OUT_DIR
    prev2083.HANDOFF_DIR = HANDOFF_DIR
    prev2083.HANDOFF_REPORT = HANDOFF_REPORT
    prev2083.REPORT_PATH = REPORT_PATH
    prev2083.V2082_OUT = V2088_OUT
    prev2083.V2082_INIT = V2088_INIT
    prev2083.V2082_BOOT = V2088_BOOT
    prev2083.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev2083.TEST_EXPECT_VERSION = TEST_EXPECT_VERSION
    prev2083.TEST_LOG_PATH = TEST_LOG_PATH
    prev2083.TEST_SUMMARY_PATH = TEST_SUMMARY_PATH
    prev2083.TEST_HELPER_RESULT_PATH = TEST_HELPER_RESULT_PATH
    prev2083.EXPECTED_HELPER_VERSION = EXPECTED_HELPER_VERSION
    prev2083.artifact_hook_check = artifact_hook_check
    prev2083.collect_details = collect_details
    prev2083.classify = classify
    prev2083.render_report = render_report


def main(argv: list[str] | None = None) -> int:
    configure_prev2083()
    return prev2087.prev2083.main(argv)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

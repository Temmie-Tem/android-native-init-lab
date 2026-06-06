#!/usr/bin/env python3
"""V2072 rollbackable handoff for borrowed-fd WLAN-PD memory-device DIAG."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import native_wifi_diag_dci_wlan_target_mask_handoff_v2069 as prev2069


CYCLE = "V2072"
OUT_DIR = prev2069.prev2065.prev2063.prev2059.prev2057.prev2046.prev2035.prev1998.prev1992.prev.repo_path(
    "tmp/wifi/v2072-diag-wlan-pd-memory-device-handoff"
)
HANDOFF_DIR = OUT_DIR / "v2071-handoff"
HANDOFF_REPORT = OUT_DIR / "v2071-handoff-report.md"
REPORT_PATH = prev2069.prev2065.prev2063.prev2059.prev2057.prev2046.prev2035.prev1998.prev1992.prev.repo_path(
    "docs/reports/NATIVE_INIT_V2072_DIAG_WLAN_PD_MEMORY_DEVICE_HANDOFF_2026-06-04.md"
)
V2071_OUT = prev2069.prev2065.prev2063.prev2059.prev2057.prev2046.prev2035.prev1998.prev1992.prev.repo_path(
    "tmp/wifi/v2071-diag-wlan-pd-memory-device-test-boot"
)
V2071_INIT = V2071_OUT / "init_v2071_diag_wlan_pd_memory_device"
V2071_BOOT = V2071_OUT / "boot_linux_v2071_diag_wlan_pd_memory_device.img"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v2071/dev/__properties__"
TEST_EXPECT_VERSION = "A90 Linux init 0.9.214 (v2071-diag-wlan-pd-memory-device)"
TEST_LOG_PATH = "/cache/native-init-wifi-test-boot-v2071.log"
TEST_SUMMARY_PATH = "/cache/native-init-wifi-test-boot-v2071.summary"
TEST_HELPER_RESULT_PATH = "/cache/native-init-wifi-test-boot-v2071-helper.result"
EXPECTED_HELPER_VERSION = "a90_android_execns_probe v399"

BASE_COLLECT_DETAILS = prev2069.collect_details
BASE_CLASSIFY = prev2069.classify


def rel(path: Path) -> str:
    return prev2069.rel(path)


def intish(value: object) -> int:
    return prev2069.intish(value)


def markdown_table(headers: list[str], rows: list[list[object]]) -> str:
    return prev2069.markdown_table(headers, rows)


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
        "wlan_pd_tftp_server_trace.late_attach.begin=1",
        "wifi_companion_start.wlan_pd_producer_tftp_server_syscall_trace.compiled=1",
        "PTRACE_ATTACH",
        "diag_wlan_pd_memory_device_probe.global_transport_switch=1",
        "diag_wlan_pd_memory_device_probe.usb_pcie_switch=1",
        "diag_wlan_pd_memory_device_probe.broad_mask=1",
        "diag_wlan_pd_memory_device_probe.restore_ioctl_attempted=1",
        "diag_wlan_pd_memory_device_probe.stream_config_attempted=1",
        "diag_wlan_pd_memory_device_probe.qmi_send=1",
        "diag_wlan_pd_memory_device_probe.ptraced=1",
        "diag_dci_register_read_probe.stream_config_attempted=1",
        "diag_dci_register_read_probe.qmi_send=1",
        "diag_dci_register_read_probe.ptraced=1",
        "diag_dci_canary_mask_probe.begin=1",
    )
    init_required = (
        "native-init-sibling-fwssctl-v641",
        "A90v641: sibling fwssctl proof armed",
        "wifi-v641-fwssctl",
        "A90v2071",
        "v2071-diag-wlan-pd-memory-device",
        "wifi-companion-wlan-pd-post-pm-lower-state-observer-start-only",
        "--timeout-sec",
        "75",
    )
    boot_required = (
        EXPECTED_HELPER_VERSION,
        "per_mgr_vote_focused.begin=1",
        "diag_dci_register_read_probe.begin=1",
        "diag_dci_wlan_target_mask_probe.begin=1",
        "diag_dci_wlan_target_mask_probe.cleanup.begin=1",
        "diag_wlan_pd_memory_device_probe.begin=1",
        "diag_wlan_pd_memory_device_probe.mode=query-gated-wlan-pd-memory-device-session-borrowed-dci-fd",
        "diag_wlan_pd_memory_device_probe.fd_borrowed=1",
        "diag_wlan_pd_memory_device_probe.node_created=0",
        "diag_wlan_pd_memory_device_probe.ioctl_query=DIAG_IOCTL_QUERY_PD_LOGGING",
        "diag_wlan_pd_memory_device_probe.ioctl_switch=DIAG_IOCTL_SWITCH_LOGGING",
        "diag_wlan_pd_memory_device_probe.switch_logging_scope=wlan-pd-memory-device-only",
        "diag_wlan_pd_memory_device_probe.req_mode=MEMORY_DEVICE_MODE",
        "diag_wlan_pd_memory_device_probe.pd_mask_name=DIAG_CON_UPD_WLAN",
        "diag_wlan_pd_memory_device_probe.global_transport_switch=0",
        "diag_wlan_pd_memory_device_probe.usb_pcie_switch=0",
        "diag_wlan_pd_memory_device_probe.broad_mask=0",
        "diag_wlan_pd_memory_device_probe.write_attempted=0",
        "diag_wlan_pd_memory_device_probe.stream_config_attempted=0",
        "diag_wlan_pd_memory_device_probe.restore_ioctl_attempted=0",
        "diag_wlan_pd_memory_device_probe.summary.restore_ioctl_attempted=0",
    )
    checks: dict[str, Any] = {}
    for path, required, forbidden in (
        (V2071_INIT, init_required, init_forbidden),
        (V2071_BOOT, boot_required, boot_forbidden),
    ):
        data = path.read_bytes() if path.exists() else b""
        missing = [token for token in required if token.encode() not in data]
        present_forbidden = [token for token in forbidden if token.encode() in data]
        checks[rel(path)] = {
            "exists": path.exists(),
            "ok": path.exists() and not missing and not present_forbidden,
            "missing": missing,
            "forbidden": present_forbidden,
        }
    return checks


def collect_memory_device(fields: dict[str, str]) -> dict[str, Any]:
    prefix = "diag_wlan_pd_memory_device_probe"
    samples = []
    for index in range(32):
        key = f"{prefix}.sample_{index:02d}.bytes"
        if key not in fields:
            continue
        samples.append({
            "index": index,
            "bytes": intish(fields.get(key)),
            "data_type": fields.get(f"{prefix}.sample_{index:02d}.data_type", ""),
            "data_type_name": fields.get(f"{prefix}.sample_{index:02d}.data_type_name", ""),
            "num_data": intish(fields.get(f"{prefix}.sample_{index:02d}.num_data")),
            "first_payload_len": intish(fields.get(f"{prefix}.sample_{index:02d}.first_payload_len")),
            "prefix_hex": fields.get(f"{prefix}.sample_{index:02d}.prefix_hex", ""),
        })
    data: dict[str, Any] = {
        "begin": intish(fields.get(f"{prefix}.begin")),
        "mode": fields.get(f"{prefix}.mode", ""),
        "started": intish(fields.get(f"{prefix}.started")) or intish(fields.get(f"{prefix}.summary.started")),
        "open_ok": intish(fields.get(f"{prefix}.open_ok")) or intish(fields.get(f"{prefix}.summary.open_ok")),
        "fd_borrowed": intish(fields.get(f"{prefix}.fd_borrowed")) or intish(fields.get(f"{prefix}.summary.fd_borrowed")),
        "node_created": intish(fields.get(f"{prefix}.node_created")) or intish(fields.get(f"{prefix}.summary.node_created")),
        "query_attempts": intish(fields.get(f"{prefix}.summary.query_attempts")),
        "query_successes": intish(fields.get(f"{prefix}.summary.query_successes")),
        "query_failures": intish(fields.get(f"{prefix}.summary.query_failures")),
        "query_supported": intish(fields.get(f"{prefix}.summary.query_supported")),
        "first_success_attempt": intish(fields.get(f"{prefix}.summary.first_success_attempt")),
        "first_success_delta_ms": intish(fields.get(f"{prefix}.summary.first_success_delta_ms")),
        "switch_attempted": intish(fields.get(f"{prefix}.summary.switch_attempted")),
        "switch_rc": intish(fields.get(f"{prefix}.summary.switch_rc")),
        "switch_errno": intish(fields.get(f"{prefix}.summary.switch_errno")),
        "switched": intish(fields.get(f"{prefix}.summary.switched")),
        "switch_delta_ms": intish(fields.get(f"{prefix}.summary.switch_delta_ms")),
        "read_calls": intish(fields.get(f"{prefix}.summary.read_calls")),
        "read_records": intish(fields.get(f"{prefix}.summary.read_records")),
        "read_bytes": intish(fields.get(f"{prefix}.summary.read_bytes")),
        "first_read_delta_ms": intish(fields.get(f"{prefix}.summary.first_read_delta_ms")),
        "user_space_records": intish(fields.get(f"{prefix}.summary.user_space_records")),
        "raw_user_space_records": intish(fields.get(f"{prefix}.summary.raw_user_space_records")),
        "other_records": intish(fields.get(f"{prefix}.summary.other_records")),
        "payload_records": intish(fields.get(f"{prefix}.summary.payload_records")),
        "poll_calls": intish(fields.get(f"{prefix}.summary.poll_calls")),
        "poll_ready": intish(fields.get(f"{prefix}.summary.poll_ready")),
        "poll_empty": intish(fields.get(f"{prefix}.summary.poll_empty")),
        "poll_errors": intish(fields.get(f"{prefix}.summary.poll_errors")),
        "read_errors": intish(fields.get(f"{prefix}.summary.read_errors")),
        "read_terminal_error": intish(fields.get(f"{prefix}.summary.read_terminal_error")),
        "samples": samples,
        "rootfs_namespace_only": intish(fields.get(f"{prefix}.summary.rootfs_namespace_only")),
        "sda29_write": intish(fields.get(f"{prefix}.summary.sda29_write")),
        "switch_logging_scope": fields.get(f"{prefix}.summary.switch_logging_scope", ""),
        "global_transport_switch": intish(fields.get(f"{prefix}.summary.global_transport_switch")),
        "usb_pcie_switch": intish(fields.get(f"{prefix}.summary.usb_pcie_switch")),
        "broad_mask": intish(fields.get(f"{prefix}.summary.broad_mask")),
        "write_attempted": intish(fields.get(f"{prefix}.summary.write_attempted")),
        "log_mask_write": intish(fields.get(f"{prefix}.summary.log_mask_write")),
        "event_mask_write": intish(fields.get(f"{prefix}.summary.event_mask_write")),
        "stream_config_attempted": intish(fields.get(f"{prefix}.summary.stream_config_attempted")),
        "qmi_send": intish(fields.get(f"{prefix}.summary.qmi_send")),
        "ptraced": intish(fields.get(f"{prefix}.summary.ptraced")),
        "restore_ioctl_attempted": intish(fields.get(f"{prefix}.summary.restore_ioctl_attempted")),
    }
    data["safe"] = (
        data["rootfs_namespace_only"] == 1
        and data["sda29_write"] == 0
        and data["fd_borrowed"] == 1
        and data["node_created"] == 0
        and data["switch_logging_scope"] == "wlan-pd-memory-device-only"
        and data["global_transport_switch"] == 0
        and data["usb_pcie_switch"] == 0
        and data["broad_mask"] == 0
        and data["write_attempted"] == 0
        and data["stream_config_attempted"] == 0
        and data["qmi_send"] == 0
        and data["ptraced"] == 0
        and data["restore_ioctl_attempted"] == 0
    )
    return data


def collect_details(handoff: dict[str, Any]) -> dict[str, Any]:
    details = BASE_COLLECT_DETAILS(handoff)
    fields = prev2069.prev2065.prev2063.prev2059.prev2057.parse_fields()
    details["diag_wlan_pd_memory_device"] = collect_memory_device(fields)
    return details


def classify(handoff: dict[str, Any],
             hook: dict[str, Any],
             steps: list[dict[str, Any]],
             details: dict[str, Any]) -> dict[str, Any]:
    base = BASE_CLASSIFY(handoff, hook, steps, details)
    memory = details.get("diag_wlan_pd_memory_device") if isinstance(details.get("diag_wlan_pd_memory_device"), dict) else {}
    target = details.get("diag_dci_wlan_target_mask") if isinstance(details.get("diag_dci_wlan_target_mask"), dict) else {}
    cascade = details.get("cascade", {}) if isinstance(details.get("cascade"), dict) else {}
    logdw = details.get("tftp_logdw", {}) if isinstance(details.get("tftp_logdw"), dict) else {}
    summary = logdw.get("summary", {}) if isinstance(logdw.get("summary"), dict) else {}
    hook_ok = all(bool(item.get("ok")) for item in hook.values())
    memory_started = intish(memory.get("begin")) == 1 and intish(memory.get("started")) == 1
    memory_open = intish(memory.get("open_ok")) == 1
    memory_safe = bool(memory.get("safe"))
    memory_query_supported = intish(memory.get("query_successes")) > 0
    memory_switch_attempted = intish(memory.get("switch_attempted")) == 1
    memory_switched = intish(memory.get("switched")) == 1
    memory_payload = intish(memory.get("payload_records")) > 0
    target_clear_ok = bool(target.get("clear_ok"))
    wlanmdsp_seen = intish(summary.get("wlanmdsp")) > 0 or intish(cascade.get("wlanmdsp_tftp")) > 0

    if not hook_ok:
        label = "diag-wlan-pd-memory-artifact-hook-regression"
        passed = False
        reason = "V2071 artifact does not contain the borrowed-fd WLAN-PD memory-device contract tokens"
    elif not memory_safe:
        label = "diag-wlan-pd-memory-safety-regression"
        passed = False
        reason = "memory-device DIAG safety markers were absent or indicated broad/global/USB/PCIE/QMI/ptrace/restore activity"
    elif not memory_started or not memory_open:
        label = "diag-wlan-pd-memory-borrowed-fd-unavailable"
        passed = True
        reason = "borrowed DCI /dev/diag fd was unavailable, so the memory-device query gate could not run"
    elif not memory_query_supported:
        label = "diag-wlan-pd-memory-query-never-ready"
        passed = True
        reason = "WLAN-PD logging query never succeeded, so no SWITCH_LOGGING attempt was made"
    elif not memory_switch_attempted:
        label = "diag-wlan-pd-memory-switch-not-attempted"
        passed = True
        reason = "WLAN-PD query succeeded but the memory-device switch was not attempted"
    elif not memory_switched:
        label = "diag-wlan-pd-memory-switch-rejected"
        passed = True
        reason = "bounded WLAN-PD-only SWITCH_LOGGING was rejected"
    elif not target_clear_ok:
        label = "diag-wlan-pd-memory-target-clear-failed"
        passed = False
        reason = "bounded DCI WLAN target masks were not proven cleared after the memory-device session"
    elif wlanmdsp_seen:
        label = "diag-wlan-pd-memory-wlanmdsp-requested"
        passed = True
        reason = "bounded memory-device DIAG session was active and native requested wlanmdsp"
    elif memory_payload:
        label = "diag-wlan-pd-memory-payload-no-wlanmdsp"
        passed = True
        reason = "bounded memory-device DIAG session returned payload records, but native still made no wlanmdsp request"
    else:
        label = "diag-wlan-pd-memory-switched-no-payload-no-wlanmdsp"
        passed = True
        reason = "bounded memory-device DIAG session switched successfully but produced no payload and no wlanmdsp request"

    return {
        **base,
        "decision": f"v2072-{label}-rollback-{'pass' if passed else 'blocked'}",
        "label": label,
        "pass": passed,
        "reason": reason,
        "hook_ok": hook_ok,
        "memory_started": memory_started,
        "memory_open": memory_open,
        "memory_safe": memory_safe,
        "memory_query_supported": memory_query_supported,
        "memory_switch_attempted": memory_switch_attempted,
        "memory_switched": memory_switched,
        "memory_payload": memory_payload,
        "target_clear_ok": target_clear_ok,
        "wlanmdsp_seen": wlanmdsp_seen,
    }


def render_report(manifest: dict[str, Any]) -> str:
    details = manifest["details"]
    classification = manifest["classification"]
    diag = details.get("diag_dci_register_read", {})
    target = details.get("diag_dci_wlan_target_mask", {})
    memory = details.get("diag_wlan_pd_memory_device", {})
    logdw = details.get("tftp_logdw", {}) if isinstance(details.get("tftp_logdw"), dict) else {}
    summary = logdw.get("summary", {}) if isinstance(logdw.get("summary"), dict) else {}
    cascade = details.get("cascade", {}) if isinstance(details.get("cascade"), dict) else {}
    samples = memory.get("samples", []) if isinstance(memory.get("samples"), list) else []
    step_lines = [
        f"- `{step['name']}` rc `{step['rc']}` ok `{step['ok']}` evidence `{step['file']}`"
        for step in manifest["steps"]
    ]
    return "\n".join([
        "# Native Init V2072 DIAG WLAN-PD Memory-Device Handoff",
        "",
        "## Summary",
        "",
        "- Cycle: `V2072`",
        f"- Decision: `{manifest['decision']}`",
        f"- Label: `{manifest['label']}`",
        f"- Pass: `{manifest['pass']}`",
        f"- Reason: {manifest['reason']}",
        f"- Evidence: `{manifest['out_dir']}`",
        f"- Inner handoff: `{manifest['handoff_manifest']}`",
        "- Comparator: V2059 closed AP-side PerMgr; V2069 showed DCI masks alone had no payload; V2072 tests the V2070 WLAN-PD-only memory-device DIAG session while borrowing the DCI fd.",
        "",
        "## Matrix",
        "",
        markdown_table(
            ["area", "value", "detail"],
            [
                ["route", classification.get("route_ok"), f"hook={classification.get('hook_ok')} memory_safe={classification.get('memory_safe')} target_clear={classification.get('target_clear_ok')}"],
                ["diag_register", diag.get("registered"), f"open={diag.get('open_ok')} proc={diag.get('selected_proc')} mask={diag.get('selected_mask')} rc={diag.get('register_rc')} client={diag.get('client_id')}"],
                ["memory_query", memory.get("query_supported"), f"attempts={memory.get('query_attempts')} success={memory.get('query_successes')} first={memory.get('first_success_delta_ms')}"],
                ["memory_switch", memory.get("switched"), f"attempted={memory.get('switch_attempted')} rc={memory.get('switch_rc')} errno={memory.get('switch_errno')} delta={memory.get('switch_delta_ms')} scope={memory.get('switch_logging_scope')}"],
                ["memory_reads", memory.get("payload_records"), f"records={memory.get('read_records')} bytes={memory.get('read_bytes')} user={memory.get('user_space_records')} raw={memory.get('raw_user_space_records')} other={memory.get('other_records')} errors={memory.get('read_errors')} terminal={memory.get('read_terminal_error')}"],
                ["memory_poll", "", f"calls={memory.get('poll_calls')} ready={memory.get('poll_ready')} empty={memory.get('poll_empty')} errors={memory.get('poll_errors')} first_read={memory.get('first_read_delta_ms')}"],
                ["target_clear", classification.get("target_clear_ok"), f"attempts={target.get('clear_write_attempts')} success={target.get('clear_write_successes')} errors={target.get('clear_write_errors')} log_still_set={target.get('log_clear_set_count')} event_still_set={target.get('event_clear_set_count')} completed={target.get('completed')}"],
                ["tftp_branch", "", f"server_check={summary.get('server_check')} ota={summary.get('ota_firewall')} mcfg={summary.get('mcfg')} wlanmdsp={summary.get('wlanmdsp')}"],
                ["cascade", "", f"wlan_pd={cascade.get('wlan_pd_up')} icnss_qmi={cascade.get('icnss_qmi_connected')} fw_ready={cascade.get('fw_ready')} wlan0={cascade.get('wlan0')}"],
            ],
        ),
        "",
        "## Memory Samples",
        "",
        markdown_table(
            ["idx", "bytes", "type", "name", "num_data", "first_payload_len", "prefix_hex"],
            [[sample.get("index"), sample.get("bytes"), sample.get("data_type"), sample.get("data_type_name"), sample.get("num_data"), sample.get("first_payload_len"), sample.get("prefix_hex")] for sample in samples] or [["none", "", "", "", "", "", ""]],
        ),
        "",
        "## Branch",
        "",
        "- If `diag-wlan-pd-memory-payload-no-wlanmdsp`, decode the memory-device samples offline and choose the next modem-side event/mask.",
        "- If `diag-wlan-pd-memory-switched-no-payload-no-wlanmdsp`, the bounded AP DIAG memory session still does not expose the producer; next step is a separate active modem DIAG logging/mask transport design or structured QMI tracer.",
        "- If `diag-wlan-pd-memory-wlanmdsp-requested`, chase the normal BDF, FW-ready, and `wlan0` cascade.",
        "",
        "## Steps",
        "",
        *step_lines,
        *([] if step_lines else ["- `none`"]),
        "",
        "## Safety",
        "",
        "- No Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping was used.",
        "- DIAG mutation was limited to private rootfs `/dev/diag`, bounded DCI WLAN target masks, and one query-gated WLAN-PD-only `DIAG_IOCTL_SWITCH_LOGGING` to `MEMORY_DEVICE_MODE` on the borrowed DCI fd; no USB/PCIE restore, broad masks, DCI stream config, QMI send, AP-side strace, boot-time QRTR matrix, passive DIAG replay, or ptrace was run.",
        "- No `/dev/subsys_esoc0`, forced RC1/case, PMIC/GPIO/GDSC/regulator write, PCI rescan, bind/unbind, fake ONLINE, or eSoC notify/BOOT_DONE action was used.",
        "- Mutation scope: `/cache` one-shot clean-DSP flag, V2071 test-boot flash-handoff, namespace-local fallback readonly/readwrite RFS bridges, namespace-local persist-RFS tmpfs mirrors, private tmp-root `/dev/socket/logdw`, private tmp-root `/dev/diag`, tracefs uprobes, bounded DCI WLAN target masks, WLAN-PD memory-device DIAG session, and rollback to `stage3/boot_linux_v724.img` with selftest fail=0.",
        "",
    ])


def configure_prev2057() -> None:
    prev2069.prev2065.prev2063.prev2059.prev2057.CYCLE = CYCLE
    prev2069.prev2065.prev2063.prev2059.prev2057.OUT_DIR = OUT_DIR
    prev2069.prev2065.prev2063.prev2059.prev2057.HANDOFF_DIR = HANDOFF_DIR
    prev2069.prev2065.prev2063.prev2059.prev2057.HANDOFF_REPORT = HANDOFF_REPORT
    prev2069.prev2065.prev2063.prev2059.prev2057.REPORT_PATH = REPORT_PATH
    prev2069.prev2065.prev2063.prev2059.prev2057.V2056_OUT = V2071_OUT
    prev2069.prev2065.prev2063.prev2059.prev2057.V2056_INIT = V2071_INIT
    prev2069.prev2065.prev2063.prev2059.prev2057.V2056_BOOT = V2071_BOOT
    prev2069.prev2065.prev2063.prev2059.prev2057.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev2069.prev2065.prev2063.prev2059.prev2057.TEST_EXPECT_VERSION = TEST_EXPECT_VERSION
    prev2069.prev2065.prev2063.prev2059.prev2057.TEST_LOG_PATH = TEST_LOG_PATH
    prev2069.prev2065.prev2063.prev2059.prev2057.TEST_SUMMARY_PATH = TEST_SUMMARY_PATH
    prev2069.prev2065.prev2063.prev2059.prev2057.TEST_HELPER_RESULT_PATH = TEST_HELPER_RESULT_PATH
    prev2069.prev2065.prev2063.prev2059.prev2057.EXPECTED_HELPER_VERSION = EXPECTED_HELPER_VERSION
    prev2069.prev2065.prev2063.prev2059.prev2057.artifact_hook_check = artifact_hook_check
    prev2069.prev2065.prev2063.prev2059.prev2057.collect_details = collect_details
    prev2069.prev2065.prev2063.prev2059.prev2057.classify = classify
    prev2069.prev2065.prev2063.prev2059.prev2057.render_report = render_report


def main(argv: list[str] | None = None) -> int:
    configure_prev2057()
    return prev2069.prev2065.prev2063.prev2059.prev2057.main(argv)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

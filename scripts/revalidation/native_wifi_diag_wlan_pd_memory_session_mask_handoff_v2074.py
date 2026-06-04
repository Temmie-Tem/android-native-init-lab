#!/usr/bin/env python3
"""V2074 rollbackable handoff for WLAN-PD memory-device DIAG session masks."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import native_wifi_diag_wlan_pd_memory_device_handoff_v2072 as prev2072


prev2069 = prev2072.prev2069
CYCLE = "V2074"
OUT_DIR = prev2069.prev2065.prev2063.prev2059.prev2057.prev2046.prev2035.prev1998.prev1992.prev.repo_path(
    "tmp/wifi/v2074-diag-wlan-pd-memory-session-mask-handoff"
)
HANDOFF_DIR = OUT_DIR / "v2073-handoff"
HANDOFF_REPORT = OUT_DIR / "v2073-handoff-report.md"
REPORT_PATH = prev2069.prev2065.prev2063.prev2059.prev2057.prev2046.prev2035.prev1998.prev1992.prev.repo_path(
    "docs/reports/NATIVE_INIT_V2074_DIAG_WLAN_PD_MEMORY_SESSION_MASK_HANDOFF_2026-06-04.md"
)
V2073_OUT = prev2069.prev2065.prev2063.prev2059.prev2057.prev2046.prev2035.prev1998.prev1992.prev.repo_path(
    "tmp/wifi/v2073-diag-wlan-pd-memory-session-mask-test-boot"
)
V2073_INIT = V2073_OUT / "init_v2073_diag_wlan_pd_memory_session_mask"
V2073_BOOT = V2073_OUT / "boot_linux_v2073_diag_wlan_pd_memory_session_mask.img"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v2073/dev/__properties__"
TEST_EXPECT_VERSION = "A90 Linux init 0.9.215 (v2073-diag-wlan-pd-memory-session-mask)"
TEST_LOG_PATH = "/cache/native-init-wifi-test-boot-v2073.log"
TEST_SUMMARY_PATH = "/cache/native-init-wifi-test-boot-v2073.summary"
TEST_HELPER_RESULT_PATH = "/cache/native-init-wifi-test-boot-v2073-helper.result"
EXPECTED_HELPER_VERSION = "a90_android_execns_probe v400"


def rel(path: Path) -> str:
    return prev2072.rel(path)


def intish(value: object) -> int:
    return prev2072.intish(value)


def markdown_table(headers: list[str], rows: list[list[object]]) -> str:
    return prev2072.markdown_table(headers, rows)


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
        "diag_wlan_pd_memory_regular_mask_probe.broad_mask=1",
        "diag_wlan_pd_memory_regular_mask_probe.stream_config_attempted=1",
        "diag_wlan_pd_memory_regular_mask_probe.qmi_send=1",
        "diag_wlan_pd_memory_regular_mask_probe.ptraced=1",
        "diag_dci_register_read_probe.stream_config_attempted=1",
        "diag_dci_register_read_probe.qmi_send=1",
        "diag_dci_register_read_probe.ptraced=1",
        "diag_dci_canary_mask_probe.begin=1",
    )
    init_required = (
        "native-init-sibling-fwssctl-v641",
        "A90v641: sibling fwssctl proof armed",
        "wifi-v641-fwssctl",
        "A90v2073",
        "v2073-diag-wlan-pd-memory-session-mask",
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
        "diag_wlan_pd_memory_device_probe.write_attempted=%d",
        "diag_wlan_pd_memory_device_probe.log_mask_write=%d",
        "diag_wlan_pd_memory_device_probe.event_mask_write=%d",
        "diag_wlan_pd_memory_device_probe.ioctl_query=DIAG_IOCTL_QUERY_PD_LOGGING",
        "diag_wlan_pd_memory_device_probe.ioctl_switch=DIAG_IOCTL_SWITCH_LOGGING",
        "diag_wlan_pd_memory_device_probe.switch_logging_scope=wlan-pd-memory-device-only",
        "diag_wlan_pd_memory_device_probe.req_mode=MEMORY_DEVICE_MODE",
        "diag_wlan_pd_memory_device_probe.pd_mask_name=DIAG_CON_UPD_WLAN",
        "diag_wlan_pd_memory_device_probe.global_transport_switch=0",
        "diag_wlan_pd_memory_device_probe.usb_pcie_switch=0",
        "diag_wlan_pd_memory_device_probe.broad_mask=0",
        "diag_wlan_pd_memory_device_probe.stream_config_attempted=0",
        "diag_wlan_pd_memory_device_probe.restore_ioctl_attempted=0",
        "diag_wlan_pd_memory_regular_mask_probe.begin=1",
        "diag_wlan_pd_memory_regular_mask_probe.mode=session-scoped-user-space-nonhdlc-wlan-log-event-mask-hold-clear",
        "diag_wlan_pd_memory_regular_mask_probe.user_space_data_type_prefix=1",
        "diag_wlan_pd_memory_regular_mask_probe.diag_write_scope=three-wlan-log-three-wlan-event-session-mask-set-hold-clear",
        "diag_wlan_pd_memory_regular_mask_probe.%s.hdlc_toggle_attempted=1",
        "diag_wlan_pd_memory_regular_mask_probe.%s.hdlc_toggle_value=%u",
        "diag_wlan_pd_memory_regular_mask_probe.%s.%s_write_rc=%d",
        "diag_wlan_pd_memory_regular_mask_probe.summary.set_log_write_rc=%d",
        "diag_wlan_pd_memory_regular_mask_probe.summary.set_event_write_rc=%d",
        "diag_wlan_pd_memory_regular_mask_probe.summary.clear_log_write_rc=%d",
        "diag_wlan_pd_memory_regular_mask_probe.summary.clear_event_write_rc=%d",
        "diag_wlan_pd_memory_regular_mask_probe.summary.user_space_data_type_prefix=1",
        "diag_wlan_pd_memory_regular_mask_probe.summary.broad_mask=0",
    )
    checks: dict[str, Any] = {}
    for path, required, forbidden in (
        (V2073_INIT, init_required, init_forbidden),
        (V2073_BOOT, boot_required, boot_forbidden),
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


def collect_regular_mask(fields: dict[str, str]) -> dict[str, Any]:
    prefix = "diag_wlan_pd_memory_regular_mask_probe"
    data = {
        "begin": intish(fields.get(f"{prefix}.begin")),
        "mode": fields.get(f"{prefix}.mode", ""),
        "attempted": intish(fields.get(f"{prefix}.summary.attempted")),
        "hdlc_disable_attempted": intish(fields.get(f"{prefix}.summary.hdlc_disable_attempted")),
        "hdlc_disabled": intish(fields.get(f"{prefix}.summary.hdlc_disabled")),
        "armed": intish(fields.get(f"{prefix}.summary.armed")),
        "clear_attempted": intish(fields.get(f"{prefix}.summary.clear_attempted")),
        "hdlc_enable_attempted": intish(fields.get(f"{prefix}.summary.hdlc_enable_attempted")),
        "hdlc_reenabled": intish(fields.get(f"{prefix}.summary.hdlc_reenabled")),
        "completed": intish(fields.get(f"{prefix}.summary.completed")),
        "log_count": intish(fields.get(f"{prefix}.summary.log_count")),
        "event_count": intish(fields.get(f"{prefix}.summary.event_count")),
        "set_write_attempts": intish(fields.get(f"{prefix}.summary.set_write_attempts")),
        "set_write_successes": intish(fields.get(f"{prefix}.summary.set_write_successes")),
        "set_write_errors": intish(fields.get(f"{prefix}.summary.set_write_errors")),
        "clear_write_attempts": intish(fields.get(f"{prefix}.summary.clear_write_attempts")),
        "clear_write_successes": intish(fields.get(f"{prefix}.summary.clear_write_successes")),
        "clear_write_errors": intish(fields.get(f"{prefix}.summary.clear_write_errors")),
        "set_log_write_rc": intish(fields.get(f"{prefix}.summary.set_log_write_rc")),
        "set_log_write_errno": intish(fields.get(f"{prefix}.summary.set_log_write_errno")),
        "set_event_write_rc": intish(fields.get(f"{prefix}.summary.set_event_write_rc")),
        "set_event_write_errno": intish(fields.get(f"{prefix}.summary.set_event_write_errno")),
        "clear_log_write_rc": intish(fields.get(f"{prefix}.summary.clear_log_write_rc")),
        "clear_log_write_errno": intish(fields.get(f"{prefix}.summary.clear_log_write_errno")),
        "clear_event_write_rc": intish(fields.get(f"{prefix}.summary.clear_event_write_rc")),
        "clear_event_write_errno": intish(fields.get(f"{prefix}.summary.clear_event_write_errno")),
        "hdlc_disable_rc": intish(fields.get(f"{prefix}.summary.hdlc_disable_rc")),
        "hdlc_disable_errno": intish(fields.get(f"{prefix}.summary.hdlc_disable_errno")),
        "hdlc_enable_rc": intish(fields.get(f"{prefix}.summary.hdlc_enable_rc")),
        "hdlc_enable_errno": intish(fields.get(f"{prefix}.summary.hdlc_enable_errno")),
        "packet_type": fields.get(f"{prefix}.summary.packet_type", ""),
        "user_space_data_type_prefix": intish(fields.get(f"{prefix}.summary.user_space_data_type_prefix")),
        "broad_mask": intish(fields.get(f"{prefix}.summary.broad_mask")),
        "stream_config_attempted": intish(fields.get(f"{prefix}.summary.stream_config_attempted")),
        "qmi_send": intish(fields.get(f"{prefix}.summary.qmi_send")),
        "ptraced": intish(fields.get(f"{prefix}.summary.ptraced")),
    }
    data["safe"] = (
        data["attempted"] == 1
        and data["user_space_data_type_prefix"] == 1
        and data["log_count"] == 3
        and data["event_count"] == 3
        and data["broad_mask"] == 0
        and data["stream_config_attempted"] == 0
        and data["qmi_send"] == 0
        and data["ptraced"] == 0
    )
    return data


def collect_details(handoff: dict[str, Any]) -> dict[str, Any]:
    details = prev2072.collect_details(handoff)
    fields = prev2069.prev2065.prev2063.prev2059.prev2057.parse_fields()
    regular = collect_regular_mask(fields)
    memory = details.get("diag_wlan_pd_memory_device")
    if isinstance(memory, dict):
        samples = memory.get("samples") if isinstance(memory.get("samples"), list) else []
        mask_response_records = 0
        for sample in samples:
            if not isinstance(sample, dict):
                continue
            prefix_hex = str(sample.get("prefix_hex", "")).lower()
            if sample.get("data_type_name") == "USER_SPACE_DATA_TYPE" and (
                "7300000003000000010000001f0a0000" in prefix_hex
                or "8200000000b40a" in prefix_hex
            ):
                mask_response_records += 1
        memory["mask_response_records"] = mask_response_records
        memory["useful_payload_records"] = max(
            0,
            intish(memory.get("payload_records")) - mask_response_records,
        )
        memory["safe"] = (
            memory.get("rootfs_namespace_only") == 1
            and memory.get("sda29_write") == 0
            and memory.get("fd_borrowed") == 1
            and memory.get("node_created") == 0
            and memory.get("switch_logging_scope") == "wlan-pd-memory-device-only"
            and memory.get("global_transport_switch") == 0
            and memory.get("usb_pcie_switch") == 0
            and memory.get("broad_mask") == 0
            and memory.get("write_attempted") == 1
            and memory.get("log_mask_write") == 1
            and memory.get("event_mask_write") == 1
            and memory.get("stream_config_attempted") == 0
            and memory.get("qmi_send") == 0
            and memory.get("ptraced") == 0
            and memory.get("restore_ioctl_attempted") == 0
        )
    details["diag_wlan_pd_memory_regular_mask"] = regular
    return details


def classify(handoff: dict[str, Any],
             hook: dict[str, Any],
             steps: list[dict[str, Any]],
             details: dict[str, Any]) -> dict[str, Any]:
    base = prev2072.BASE_CLASSIFY(handoff, hook, steps, details)
    memory = details.get("diag_wlan_pd_memory_device") if isinstance(details.get("diag_wlan_pd_memory_device"), dict) else {}
    regular = details.get("diag_wlan_pd_memory_regular_mask") if isinstance(details.get("diag_wlan_pd_memory_regular_mask"), dict) else {}
    target = details.get("diag_dci_wlan_target_mask") if isinstance(details.get("diag_dci_wlan_target_mask"), dict) else {}
    cascade = details.get("cascade", {}) if isinstance(details.get("cascade"), dict) else {}
    logdw = details.get("tftp_logdw", {}) if isinstance(details.get("tftp_logdw"), dict) else {}
    summary = logdw.get("summary", {}) if isinstance(logdw.get("summary"), dict) else {}
    hook_ok = all(bool(item.get("ok")) for item in hook.values())
    memory_safe = bool(memory.get("safe"))
    regular_safe = bool(regular.get("safe"))
    memory_switched = intish(memory.get("switched")) == 1
    memory_payload = intish(memory.get("payload_records")) > 0
    regular_hdlc_disabled = intish(regular.get("hdlc_disabled")) == 1
    regular_armed = intish(regular.get("armed")) == 1
    regular_cleared = intish(regular.get("clear_write_successes")) == 2 and intish(regular.get("hdlc_reenabled")) == 1
    target_clear_ok = bool(target.get("clear_ok"))
    wlanmdsp_seen = intish(summary.get("wlanmdsp")) > 0 or intish(cascade.get("wlanmdsp_tftp")) > 0
    mask_response_only = intish(memory.get("mask_response_records")) > 0 and intish(memory.get("useful_payload_records")) == 0

    if not hook_ok:
        label = "diag-wlan-pd-memory-session-mask-artifact-hook-regression"
        passed = False
        reason = "V2073 artifact does not contain the session-mask contract tokens"
    elif not memory_safe or not regular_safe:
        label = "diag-wlan-pd-memory-session-mask-safety-regression"
        passed = False
        reason = "session-mask or memory-device safety markers were absent or unsafe"
    elif not memory_switched:
        label = "diag-wlan-pd-memory-session-mask-switch-missing"
        passed = True
        reason = "WLAN-PD memory-device switch did not complete, so regular masks could not be decisive"
    elif not regular_hdlc_disabled:
        label = "diag-wlan-pd-memory-session-mask-hdlc-disable-failed"
        passed = True
        reason = "session-local HDLC disable failed, so normal mask packets were not armed"
    elif not regular_armed:
        label = "diag-wlan-pd-memory-session-mask-not-armed"
        passed = True
        reason = "normal WLAN log/event mask packets were sent but did not both succeed"
    elif not regular_cleared:
        label = "diag-wlan-pd-memory-session-mask-clear-failed"
        passed = False
        reason = "session masks were armed but not proven cleared/restored"
    elif not target_clear_ok:
        label = "diag-wlan-pd-memory-session-mask-target-clear-failed"
        passed = False
        reason = "bounded DCI WLAN target masks were not proven cleared after the memory-device session"
    elif wlanmdsp_seen:
        label = "diag-wlan-pd-memory-session-mask-wlanmdsp-requested"
        passed = True
        reason = "session-scoped WLAN masks were active and native requested wlanmdsp"
    elif mask_response_only:
        label = "diag-wlan-pd-memory-session-mask-mask-response-only-no-wlanmdsp"
        passed = True
        reason = "session-scoped WLAN masks were armed and acknowledged, but memory-device reads contained only app-side mask responses and native still made no wlanmdsp request"
    elif memory_payload:
        label = "diag-wlan-pd-memory-session-mask-payload-no-wlanmdsp"
        passed = True
        reason = "session-scoped WLAN masks yielded memory-device payload records, but native still made no wlanmdsp request"
    else:
        label = "diag-wlan-pd-memory-session-mask-no-payload-no-wlanmdsp"
        passed = True
        reason = "session-scoped WLAN masks were armed and cleared, but produced no payload and no wlanmdsp request"

    return {
        **base,
        "decision": f"v2074-{label}-rollback-{'pass' if passed else 'blocked'}",
        "label": label,
        "pass": passed,
        "reason": reason,
        "hook_ok": hook_ok,
        "memory_safe": memory_safe,
        "regular_safe": regular_safe,
        "memory_switched": memory_switched,
        "regular_hdlc_disabled": regular_hdlc_disabled,
        "regular_armed": regular_armed,
        "regular_cleared": regular_cleared,
        "memory_payload": memory_payload,
        "mask_response_only": mask_response_only,
        "target_clear_ok": target_clear_ok,
        "wlanmdsp_seen": wlanmdsp_seen,
    }


def render_report(manifest: dict[str, Any]) -> str:
    details = manifest["details"]
    classification = manifest["classification"]
    diag = details.get("diag_dci_register_read", {})
    target = details.get("diag_dci_wlan_target_mask", {})
    memory = details.get("diag_wlan_pd_memory_device", {})
    regular = details.get("diag_wlan_pd_memory_regular_mask", {})
    logdw = details.get("tftp_logdw", {}) if isinstance(details.get("tftp_logdw"), dict) else {}
    summary = logdw.get("summary", {}) if isinstance(logdw.get("summary"), dict) else {}
    cascade = details.get("cascade", {}) if isinstance(details.get("cascade"), dict) else {}
    samples = memory.get("samples", []) if isinstance(memory.get("samples"), list) else []
    step_lines = [
        f"- `{step['name']}` rc `{step['rc']}` ok `{step['ok']}` evidence `{step['file']}`"
        for step in manifest["steps"]
    ]
    return "\n".join([
        "# Native Init V2074 DIAG WLAN-PD Memory Session-Mask Handoff",
        "",
        "## Summary",
        "",
        "- Cycle: `V2074`",
        f"- Decision: `{manifest['decision']}`",
        f"- Label: `{manifest['label']}`",
        f"- Pass: `{manifest['pass']}`",
        f"- Reason: {manifest['reason']}",
        f"- Evidence: `{manifest['out_dir']}`",
        f"- Inner handoff: `{manifest['handoff_manifest']}`",
        "- Comparator: V2072 switched WLAN-PD memory-device mode but did not send normal app log/event masks into that memory session. V2074 adds session-local HDLC disable plus `USER_SPACE_DATA_TYPE` normal WLAN masks.",
        "",
        "## Matrix",
        "",
        markdown_table(
            ["area", "value", "detail"],
            [
                ["route", classification.get("route_ok"), f"hook={classification.get('hook_ok')} memory_safe={classification.get('memory_safe')} regular_safe={classification.get('regular_safe')} target_clear={classification.get('target_clear_ok')}"],
                ["diag_register", diag.get("registered"), f"open={diag.get('open_ok')} proc={diag.get('selected_proc')} mask={diag.get('selected_mask')} rc={diag.get('register_rc')} client={diag.get('client_id')}"],
                ["memory_switch", memory.get("switched"), f"attempted={memory.get('switch_attempted')} rc={memory.get('switch_rc')} errno={memory.get('switch_errno')} delta={memory.get('switch_delta_ms')} scope={memory.get('switch_logging_scope')}"],
                ["regular_masks", regular.get("armed"), f"hdlc={regular.get('hdlc_disabled')} set={regular.get('set_write_successes')}/{regular.get('set_write_attempts')} clear={regular.get('clear_write_successes')}/{regular.get('clear_write_attempts')} restored={regular.get('hdlc_reenabled')} completed={regular.get('completed')}"],
                ["regular_rc", "", f"set_log={regular.get('set_log_write_rc')}/{regular.get('set_log_write_errno')} set_event={regular.get('set_event_write_rc')}/{regular.get('set_event_write_errno')} clear_log={regular.get('clear_log_write_rc')}/{regular.get('clear_log_write_errno')} clear_event={regular.get('clear_event_write_rc')}/{regular.get('clear_event_write_errno')}"],
                ["memory_reads", memory.get("useful_payload_records"), f"records={memory.get('read_records')} bytes={memory.get('read_bytes')} user={memory.get('user_space_records')} mask_response={memory.get('mask_response_records')} raw={memory.get('raw_user_space_records')} other={memory.get('other_records')} errors={memory.get('read_errors')} terminal={memory.get('read_terminal_error')}"],
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
        "- If `diag-wlan-pd-memory-session-mask-mask-response-only-no-wlanmdsp`, the active app-mask path is now proven to work but still yields no modem producer logs; next step is a modem-side logging/mask transport or structured modem/QMI tracer.",
        "- If `diag-wlan-pd-memory-session-mask-payload-no-wlanmdsp`, decode the non-mask-response USER_SPACE memory-device payload and select the next narrow modem-side mask/event.",
        "- If `diag-wlan-pd-memory-session-mask-no-payload-no-wlanmdsp`, even a switched WLAN-PD memory session with normal WLAN app masks does not expose the producer; next step is a modem-side active DIAG logging/mask transport or structured modem/QMI tracer.",
        "- If `diag-wlan-pd-memory-session-mask-wlanmdsp-requested`, chase the normal BDF, FW-ready, and `wlan0` cascade.",
        "",
        "## Steps",
        "",
        *step_lines,
        *([] if step_lines else ["- `none`"]),
        "",
        "## Safety",
        "",
        "- No Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping was used.",
        "- DIAG mutation was limited to private rootfs `/dev/diag`, bounded DCI WLAN target masks, one query-gated WLAN-PD-only `DIAG_IOCTL_SWITCH_LOGGING` to `MEMORY_DEVICE_MODE`, session-local `DIAG_IOCTL_HDLC_TOGGLE`, and exactly three WLAN log masks plus three WLAN event masks set during the lower window and cleared during cleanup; no USB/PCIE restore, broad masks, DCI stream config, QMI send, AP-side strace, boot-time QRTR matrix, passive DIAG replay, or ptrace was run.",
        "- No `/dev/subsys_esoc0`, forced RC1/case, PMIC/GPIO/GDSC/regulator write, PCI rescan, bind/unbind, fake ONLINE, or eSoC notify/BOOT_DONE action was used.",
        "- Mutation scope: `/cache` one-shot clean-DSP flag, V2073 test-boot flash-handoff, namespace-local fallback readonly/readwrite RFS bridges, namespace-local persist-RFS tmpfs mirrors, private tmp-root `/dev/socket/logdw`, private tmp-root `/dev/diag`, tracefs uprobes, bounded DIAG masks, WLAN-PD memory-device DIAG session, and rollback to `stage3/boot_linux_v724.img` with selftest fail=0.",
        "",
    ])


def configure_prev2057() -> None:
    prev2069.prev2065.prev2063.prev2059.prev2057.CYCLE = CYCLE
    prev2069.prev2065.prev2063.prev2059.prev2057.OUT_DIR = OUT_DIR
    prev2069.prev2065.prev2063.prev2059.prev2057.HANDOFF_DIR = HANDOFF_DIR
    prev2069.prev2065.prev2063.prev2059.prev2057.HANDOFF_REPORT = HANDOFF_REPORT
    prev2069.prev2065.prev2063.prev2059.prev2057.REPORT_PATH = REPORT_PATH
    prev2069.prev2065.prev2063.prev2059.prev2057.V2056_OUT = V2073_OUT
    prev2069.prev2065.prev2063.prev2059.prev2057.V2056_INIT = V2073_INIT
    prev2069.prev2065.prev2063.prev2059.prev2057.V2056_BOOT = V2073_BOOT
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

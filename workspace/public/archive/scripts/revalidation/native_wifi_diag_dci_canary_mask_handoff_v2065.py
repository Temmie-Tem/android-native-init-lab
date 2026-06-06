#!/usr/bin/env python3
"""V2065 rollbackable handoff for bounded DIAG DCI canary-mask visibility."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import native_wifi_diag_dci_register_read_handoff_v2063 as prev2063


CYCLE = "V2065"
OUT_DIR = prev2063.prev2059.prev2057.prev2046.prev2035.prev1998.prev1992.prev.repo_path(
    "tmp/wifi/v2065-dci-canary-mask-handoff"
)
HANDOFF_DIR = OUT_DIR / "v2064-handoff"
HANDOFF_REPORT = OUT_DIR / "v2064-handoff-report.md"
REPORT_PATH = prev2063.prev2059.prev2057.prev2046.prev2035.prev1998.prev1992.prev.repo_path(
    "docs/reports/NATIVE_INIT_V2065_DCI_CANARY_MASK_HANDOFF_2026-06-04.md"
)
V2064_OUT = prev2063.prev2059.prev2057.prev2046.prev2035.prev1998.prev1992.prev.repo_path(
    "tmp/wifi/v2064-dci-canary-mask-test-boot"
)
V2064_INIT = V2064_OUT / "init_v2064_dci_canary_mask"
V2064_BOOT = V2064_OUT / "boot_linux_v2064_dci_canary_mask.img"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v2064/dev/__properties__"
TEST_EXPECT_VERSION = "A90 Linux init 0.9.211 (v2064-dci-canary-mask)"
TEST_LOG_PATH = "/cache/native-init-wifi-test-boot-v2064.log"
TEST_SUMMARY_PATH = "/cache/native-init-wifi-test-boot-v2064.summary"
TEST_HELPER_RESULT_PATH = "/cache/native-init-wifi-test-boot-v2064-helper.result"
EXPECTED_HELPER_VERSION = "a90_android_execns_probe v396"


def rel(path: Path) -> str:
    return prev2063.rel(path)


def intish(value: object) -> int:
    return prev2063.intish(value)


def markdown_table(headers: list[str], rows: list[list[object]]) -> str:
    return prev2063.markdown_table(headers, rows)


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
        "DIAG_IOCTL_SWITCH_LOGGING",
        "diag_dci_register_read_probe.switch_logging_attempted=1",
        "diag_dci_register_read_probe.stream_config_attempted=1",
        "diag_dci_register_read_probe.qmi_send=1",
        "diag_dci_register_read_probe.ptraced=1",
        "diag_dci_canary_mask_probe.switch_logging_attempted=1",
        "diag_dci_canary_mask_probe.stream_config_attempted=1",
        "diag_dci_canary_mask_probe.qmi_send=1",
        "diag_dci_canary_mask_probe.ptraced=1",
    )
    init_required = (
        "native-init-sibling-fwssctl-v641",
        "A90v641: sibling fwssctl proof armed",
        "wifi-v641-fwssctl",
        "A90v2064",
        "v2064-dci-canary-mask",
        "wifi-companion-wlan-pd-post-pm-lower-state-observer-start-only",
        "--timeout-sec",
        "75",
    )
    boot_required = (
        EXPECTED_HELPER_VERSION,
        "per_mgr_vote_focused.begin=1",
        "per_mgr_vote_focused.mode=cnss-pm-client-register-vote-uprobe-compact",
        "tftp_readwrite_transition.mode=read-only-stat-open-on-change",
        "tftp_ready_before_wlfw_vote.mode=alive-socket-plus-android-order-settle",
        "tftp_logdw_sink.order_timestamps=1",
        "diag_dci_register_read_probe.begin=1",
        "diag_dci_register_read_probe.mode=private-node-rdwr-nonblock-dci-reg-read-with-bounded-canary-mask-set-clear",
        "diag_dci_register_read_probe.switch_logging_attempted=0",
        "diag_dci_register_read_probe.write_attempted=1",
        "diag_dci_register_read_probe.write_scope=bounded-dci-data-canary-mask-set-clear",
        "diag_dci_register_read_probe.stream_config_attempted=0",
        "diag_dci_register_read_probe.log_mask_write=1",
        "diag_dci_register_read_probe.event_mask_write=1",
        "diag_dci_canary_mask_probe.begin=1",
        "diag_dci_canary_mask_probe.mode=bounded-dci-data-write-one-log-one-event-status-clear-no-switch-logging",
        "diag_dci_canary_mask_probe.diag_write_scope=dci-data-only-one-log-one-event-set-clear",
        "diag_dci_canary_mask_probe.switch_logging_attempted=0",
        "diag_dci_canary_mask_probe.stream_config_attempted=0",
        "diag_dci_canary_mask_probe.log_code=0x%x",
        "diag_dci_canary_mask_probe.event_id=%u",
        "diag_dci_canary_mask_probe.summary.completed=%d",
    )
    checks: dict[str, Any] = {}
    for path, required, forbidden in (
        (V2064_INIT, init_required, init_forbidden),
        (V2064_BOOT, boot_required, boot_forbidden),
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


def collect_diag_dci_register_read(fields: dict[str, str]) -> dict[str, Any]:
    prefix = "diag_dci_register_read_probe"
    data = prev2063.collect_diag_dci_register_read(fields)
    data.update({
        "rootfs_namespace_only": intish(fields.get(f"{prefix}.rootfs_namespace_only")),
        "sda29_write": intish(fields.get(f"{prefix}.sda29_write")),
        "switch_logging_attempted": intish(fields.get(f"{prefix}.switch_logging_attempted")),
        "write_attempted": intish(fields.get(f"{prefix}.write_attempted")),
        "write_scope": fields.get(f"{prefix}.write_scope", ""),
        "stream_config_attempted": intish(fields.get(f"{prefix}.stream_config_attempted")),
        "log_mask_write": intish(fields.get(f"{prefix}.log_mask_write")),
        "event_mask_write": intish(fields.get(f"{prefix}.event_mask_write")),
        "qmi_send": intish(fields.get(f"{prefix}.qmi_send")),
        "ptraced": intish(fields.get(f"{prefix}.ptraced")),
    })
    data["safe"] = (
        data["rootfs_namespace_only"] == 1
        and data["sda29_write"] == 0
        and data["switch_logging_attempted"] == 0
        and data["write_attempted"] == 1
        and data["write_scope"] == "bounded-dci-data-canary-mask-set-clear"
        and data["stream_config_attempted"] == 0
        and data["log_mask_write"] == 1
        and data["event_mask_write"] == 1
        and data["qmi_send"] == 0
        and data["ptraced"] == 0
    )
    return data


def collect_diag_dci_canary_mask(fields: dict[str, str]) -> dict[str, Any]:
    prefix = "diag_dci_canary_mask_probe"

    def direct_or_summary(direct: str, summary: str | None = None) -> str | None:
        if direct in fields:
            return fields.get(direct)
        if summary is not None:
            return fields.get(summary)
        return None

    data: dict[str, Any] = {
        "begin": intish(fields.get(f"{prefix}.begin")),
        "mode": fields.get(f"{prefix}.mode", ""),
        "rootfs_namespace_only": intish(fields.get(f"{prefix}.rootfs_namespace_only")),
        "sda29_write": intish(fields.get(f"{prefix}.sda29_write")),
        "switch_logging_attempted": intish(fields.get(f"{prefix}.switch_logging_attempted")),
        "diag_write_attempted": intish(fields.get(f"{prefix}.diag_write_attempted")),
        "diag_write_scope": fields.get(f"{prefix}.diag_write_scope", ""),
        "stream_config_attempted": intish(fields.get(f"{prefix}.stream_config_attempted")),
        "qmi_send": intish(fields.get(f"{prefix}.qmi_send")),
        "ptraced": intish(fields.get(f"{prefix}.ptraced")),
        "completed": intish(direct_or_summary(f"{prefix}.completed", f"{prefix}.summary.completed")),
        "attempted": intish(fields.get(f"{prefix}.summary.attempted")) or intish(fields.get(f"{prefix}.begin")),
        "log_code": direct_or_summary(f"{prefix}.log_code", f"{prefix}.summary.log_code") or "",
        "event_id": intish(direct_or_summary(f"{prefix}.event_id", f"{prefix}.summary.event_id")),
        "write_attempts": intish(fields.get(f"{prefix}.summary.write_attempts")),
        "write_successes": intish(fields.get(f"{prefix}.summary.write_successes")),
        "write_errors": intish(fields.get(f"{prefix}.summary.write_errors")),
        "log_pre_rc": intish(direct_or_summary(f"{prefix}.pre.log_status_rc", f"{prefix}.summary.log_pre_rc")),
        "log_pre_errno": intish(direct_or_summary(f"{prefix}.pre.log_status_errno", f"{prefix}.summary.log_pre_errno")),
        "log_pre_is_set": intish(direct_or_summary(f"{prefix}.pre.log_status_is_set", f"{prefix}.summary.log_pre_is_set")),
        "event_pre_rc": intish(direct_or_summary(f"{prefix}.pre.event_status_rc", f"{prefix}.summary.event_pre_rc")),
        "event_pre_errno": intish(direct_or_summary(f"{prefix}.pre.event_status_errno", f"{prefix}.summary.event_pre_errno")),
        "event_pre_is_set": intish(direct_or_summary(f"{prefix}.pre.event_status_is_set", f"{prefix}.summary.event_pre_is_set")),
        "log_set_write_rc": intish(direct_or_summary(f"{prefix}.set.log_write_rc", f"{prefix}.summary.log_set_write_rc")),
        "log_set_write_errno": intish(direct_or_summary(f"{prefix}.set.log_write_errno", f"{prefix}.summary.log_set_write_errno")),
        "event_set_write_rc": intish(direct_or_summary(f"{prefix}.set.event_write_rc", f"{prefix}.summary.event_set_write_rc")),
        "event_set_write_errno": intish(direct_or_summary(f"{prefix}.set.event_write_errno", f"{prefix}.summary.event_set_write_errno")),
        "log_set_rc": intish(direct_or_summary(f"{prefix}.set.log_status_rc", f"{prefix}.summary.log_set_rc")),
        "log_set_errno": intish(direct_or_summary(f"{prefix}.set.log_status_errno", f"{prefix}.summary.log_set_errno")),
        "log_set_is_set": intish(direct_or_summary(f"{prefix}.set.log_status_is_set", f"{prefix}.summary.log_set_is_set")),
        "event_set_rc": intish(direct_or_summary(f"{prefix}.set.event_status_rc", f"{prefix}.summary.event_set_rc")),
        "event_set_errno": intish(direct_or_summary(f"{prefix}.set.event_status_errno", f"{prefix}.summary.event_set_errno")),
        "event_set_is_set": intish(direct_or_summary(f"{prefix}.set.event_status_is_set", f"{prefix}.summary.event_set_is_set")),
        "log_clear_write_rc": intish(direct_or_summary(f"{prefix}.clear.log_write_rc", f"{prefix}.summary.log_clear_write_rc")),
        "log_clear_write_errno": intish(direct_or_summary(f"{prefix}.clear.log_write_errno", f"{prefix}.summary.log_clear_write_errno")),
        "event_clear_write_rc": intish(direct_or_summary(f"{prefix}.clear.event_write_rc", f"{prefix}.summary.event_clear_write_rc")),
        "event_clear_write_errno": intish(direct_or_summary(f"{prefix}.clear.event_write_errno", f"{prefix}.summary.event_clear_write_errno")),
        "log_clear_rc": intish(direct_or_summary(f"{prefix}.clear.log_status_rc", f"{prefix}.summary.log_clear_rc")),
        "log_clear_errno": intish(direct_or_summary(f"{prefix}.clear.log_status_errno", f"{prefix}.summary.log_clear_errno")),
        "log_clear_is_set": intish(direct_or_summary(f"{prefix}.clear.log_status_is_set", f"{prefix}.summary.log_clear_is_set")),
        "event_clear_rc": intish(direct_or_summary(f"{prefix}.clear.event_status_rc", f"{prefix}.summary.event_clear_rc")),
        "event_clear_errno": intish(direct_or_summary(f"{prefix}.clear.event_status_errno", f"{prefix}.summary.event_clear_errno")),
        "event_clear_is_set": intish(direct_or_summary(f"{prefix}.clear.event_status_is_set", f"{prefix}.summary.event_clear_is_set")),
        "health_pre_rc": intish(direct_or_summary(f"{prefix}.pre.health_rc", f"{prefix}.summary.health_pre_rc")),
        "health_pre_errno": intish(direct_or_summary(f"{prefix}.pre.health_errno", f"{prefix}.summary.health_pre_errno")),
        "health_pre_received_logs": intish(direct_or_summary(f"{prefix}.pre.health_received_logs", f"{prefix}.summary.health_pre_received_logs")),
        "health_pre_received_events": intish(direct_or_summary(f"{prefix}.pre.health_received_events", f"{prefix}.summary.health_pre_received_events")),
        "health_post_rc": intish(direct_or_summary(f"{prefix}.post.health_rc", f"{prefix}.summary.health_post_rc")),
        "health_post_errno": intish(direct_or_summary(f"{prefix}.post.health_errno", f"{prefix}.summary.health_post_errno")),
        "health_post_received_logs": intish(direct_or_summary(f"{prefix}.post.health_received_logs", f"{prefix}.summary.health_post_received_logs")),
        "health_post_received_events": intish(direct_or_summary(f"{prefix}.post.health_received_events", f"{prefix}.summary.health_post_received_events")),
    }
    data["safe"] = (
        data["rootfs_namespace_only"] == 1
        and data["sda29_write"] == 0
        and data["switch_logging_attempted"] == 0
        and data["diag_write_attempted"] == 1
        and data["diag_write_scope"] == "dci-data-only-one-log-one-event-set-clear"
        and data["stream_config_attempted"] == 0
        and data["qmi_send"] == 0
        and data["ptraced"] == 0
    )
    data["writes_ok"] = (
        data["write_attempts"] == 4
        and data["write_successes"] == 4
        and data["write_errors"] == 0
        and data["log_set_write_rc"] > 0
        and data["event_set_write_rc"] > 0
        and data["log_clear_write_rc"] > 0
        and data["event_clear_write_rc"] > 0
    )
    data["status_ok"] = (
        data["log_set_is_set"] == 1
        and data["event_set_is_set"] == 1
        and data["log_clear_is_set"] == 0
        and data["event_clear_is_set"] == 0
    )
    return data


def collect_details(handoff: dict[str, Any]) -> dict[str, Any]:
    details = prev2063.prev2059.collect_details(handoff)
    fields = prev2063.prev2059.prev2057.parse_fields()
    details["diag_dci_register_read"] = collect_diag_dci_register_read(fields)
    details["diag_dci_canary_mask"] = collect_diag_dci_canary_mask(fields)
    return details


def classify(handoff: dict[str, Any],
             hook: dict[str, Any],
             steps: list[dict[str, Any]],
             details: dict[str, Any]) -> dict[str, Any]:
    base = prev2063.prev2059.classify(handoff, hook, steps, details)
    diag = details.get("diag_dci_register_read") if isinstance(details.get("diag_dci_register_read"), dict) else {}
    canary = details.get("diag_dci_canary_mask") if isinstance(details.get("diag_dci_canary_mask"), dict) else {}
    hook_ok = all(bool(item.get("ok")) for item in hook.values())
    diag_started = intish(diag.get("begin")) == 1 and intish(diag.get("started")) == 1
    diag_safe = bool(diag.get("safe"))
    diag_open = intish(diag.get("open_ok")) == 1
    diag_registered = intish(diag.get("registered")) == 1
    canary_started = intish(canary.get("begin")) == 1
    canary_safe = bool(canary.get("safe"))
    canary_completed = intish(canary.get("completed")) == 1
    canary_writes_ok = bool(canary.get("writes_ok"))
    canary_status_ok = bool(canary.get("status_ok"))

    if not hook_ok:
        label = "dci-canary-mask-artifact-hook-regression"
        passed = False
        reason = "V2064 artifact does not contain the bounded DCI canary-mask contract tokens"
    elif not diag_safe or not canary_safe:
        label = "dci-canary-mask-safety-regression"
        passed = False
        reason = "DIAG DCI canary safety markers were absent or indicated forbidden logging-mode, stream, QMI, ptrace, or partition activity"
    elif not diag_started or not diag_open:
        label = "dci-canary-mask-open-failed"
        passed = True
        reason = "private /dev/diag canary probe did not open; active DCI cannot proceed until diag node materialization/open is fixed"
    elif not diag_registered:
        label = "dci-canary-mask-register-failed"
        passed = True
        reason = "DCI support exists, but DIAG_IOCTL_DCI_REG did not return a usable client for the canary mask probe"
    elif not canary_started or not canary_completed:
        label = "dci-canary-mask-not-completed"
        passed = True
        reason = "DCI registered but the bounded canary set/status/clear sequence did not complete"
    elif not canary_writes_ok:
        label = "dci-canary-mask-write-failed"
        passed = True
        reason = "bounded DCI data writes for the canary log/event masks did not all succeed"
    elif not canary_status_ok:
        label = "dci-canary-mask-status-mismatch"
        passed = True
        reason = "bounded DCI canary writes completed, but LOG_STATUS/EVENT_STATUS did not reflect set then clear"
    else:
        label = "dci-canary-mask-set-clear-ok"
        passed = True
        reason = "bounded DCI data writes can set, query, clear, and re-query one log/event canary without logging-mode switch or broad masks"

    return {
        **base,
        "decision": f"v2065-{label}-rollback-{'pass' if passed else 'blocked'}",
        "label": label,
        "pass": passed,
        "reason": reason,
        "hook_ok": hook_ok,
        "diag_started": diag_started,
        "diag_safe": diag_safe,
        "diag_open": diag_open,
        "diag_registered": diag_registered,
        "canary_started": canary_started,
        "canary_safe": canary_safe,
        "canary_completed": canary_completed,
        "canary_writes_ok": canary_writes_ok,
        "canary_status_ok": canary_status_ok,
    }


def render_report(manifest: dict[str, Any]) -> str:
    details = manifest["details"]
    classification = manifest["classification"]
    pm = details.get("per_mgr_vote_focused", {})
    diag = details.get("diag_dci_register_read", {})
    canary = details.get("diag_dci_canary_mask", {})
    logdw = details.get("tftp_logdw", {}) if isinstance(details.get("tftp_logdw"), dict) else {}
    cascade = details.get("cascade", {}) if isinstance(details.get("cascade"), dict) else {}
    procs = diag.get("procs", []) if isinstance(diag.get("procs"), list) else []
    samples = diag.get("samples", []) if isinstance(diag.get("samples"), list) else []
    step_lines = [
        f"- `{step['name']}` rc `{step['rc']}` ok `{step['ok']}` evidence `{step['file']}`"
        for step in manifest["steps"]
    ]
    return "\n".join([
        "# Native Init V2065 DIAG DCI Canary-Mask Handoff",
        "",
        "## Summary",
        "",
        "- Cycle: `V2065`",
        f"- Decision: `{manifest['decision']}`",
        f"- Label: `{manifest['label']}`",
        f"- Pass: `{manifest['pass']}`",
        f"- Reason: {manifest['reason']}",
        f"- Evidence: `{manifest['out_dir']}`",
        f"- Inner handoff: `{manifest['handoff_manifest']}`",
        "- Comparator: V2059 remains the AP-side PerMgr answer; V2065 only validates whether a bounded active DCI canary mask path is viable before selecting modem/WLAN-specific masks.",
        "",
        "## Matrix",
        "",
        markdown_table(
            ["area", "value", "detail"],
            [
                ["route", classification.get("route_ok"), f"hook={classification.get('hook_ok')} diag_safe={classification.get('diag_safe')} canary_safe={classification.get('canary_safe')}"],
                ["diag_register", classification.get("diag_registered"), f"open={classification.get('diag_open')} proc={diag.get('selected_proc')} mask={diag.get('selected_mask')} rc={diag.get('register_rc')} client={diag.get('client_id')}"],
                ["canary_writes", classification.get("canary_writes_ok"), f"attempts={canary.get('write_attempts')} success={canary.get('write_successes')} errors={canary.get('write_errors')} log_set_rc={canary.get('log_set_write_rc')} event_set_rc={canary.get('event_set_write_rc')} log_clear_rc={canary.get('log_clear_write_rc')} event_clear_rc={canary.get('event_clear_write_rc')}"],
                ["canary_status", classification.get("canary_status_ok"), f"pre=log:{canary.get('log_pre_is_set')} event:{canary.get('event_pre_is_set')} set=log:{canary.get('log_set_is_set')} event:{canary.get('event_set_is_set')} clear=log:{canary.get('log_clear_is_set')} event:{canary.get('event_clear_is_set')}"],
                ["health", "", f"pre_logs={canary.get('health_pre_received_logs')} pre_events={canary.get('health_pre_received_events')} post_logs={canary.get('health_post_received_logs')} post_events={canary.get('health_post_received_events')}"],
                ["diag_reads", diag.get("payload_records"), f"records={diag.get('read_records')} bytes={diag.get('read_bytes')} payload={diag.get('payload_records')} bootstrap={diag.get('mask_bootstrap_records')} other={diag.get('other_records')} errors={diag.get('read_errors')} terminal_error={diag.get('read_terminal_error')}"],
                ["tftp_branch", "", f"server_check={logdw.get('summary', {}).get('server_check')} ota={logdw.get('summary', {}).get('ota_firewall')} mcfg={logdw.get('summary', {}).get('mcfg')} wlanmdsp={logdw.get('summary', {}).get('wlanmdsp')}"],
                ["cascade", "", f"wlan_pd={cascade.get('wlan_pd_up')} icnss_qmi={cascade.get('icnss_qmi_connected')} fw_ready={cascade.get('fw_ready')} wlan0={cascade.get('wlan0')}"],
            ],
        ),
        "",
        "## DIAG Support Detail",
        "",
        markdown_table(
            ["proc", "rc", "errno", "support_mask", "nonzero"],
            [[item.get("proc"), item.get("rc"), item.get("errno"), item.get("support_mask"), item.get("support_nonzero")] for item in procs] or [["none", "", "", "", ""]],
        ),
        "",
        "## DIAG Read Samples",
        "",
        markdown_table(
            ["idx", "bytes", "type", "name", "prefix_hex"],
            [[sample.get("index"), sample.get("bytes"), sample.get("data_type"), sample.get("data_type_name"), sample.get("prefix_hex")] for sample in samples] or [["none", "", "", "", ""]],
        ),
        "",
        "## PerMgr Anchor",
        "",
        markdown_table(
            ["field", "value"],
            [
                ["focused_label", pm.get("label", "")],
                ["cnss_register_ret", pm.get("cnss_register_ret_line", "")],
                ["cnss_connect_ret", pm.get("cnss_connect_ret_line", "")],
                ["pm_service", f"entry={pm.get('pm_server_register_entry_hit_count')} match={pm.get('pm_server_register_match_hit_count')} add_client={pm.get('pm_server_register_add_client_call_hit_count')} success={pm.get('pm_server_register_success_return_hit_count')}"],
            ],
        ),
        "",
        "## Branch",
        "",
        "- If `dci-canary-mask-set-clear-ok`, the next step is a targeted active DCI mask list for modem/WLAN PD producer events, still bounded and rollbackable.",
        "- If `dci-canary-mask-write-failed` or `dci-canary-mask-status-mismatch`, repair the DCI mask ABI before selecting any modem/WLAN-specific masks.",
        "- If `dci-canary-mask-register-failed`, repair the DCI registration contract before any heavier logging-mode path.",
        "",
        "## Steps",
        "",
        *step_lines,
        *([] if step_lines else ["- `none`"]),
        "",
        "## Safety",
        "",
        "- No Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping was used.",
        "- DIAG use was limited to a private rootfs `/dev/diag` char node, `DIAG_IOCTL_DCI_SUPPORT`, `DIAG_IOCTL_DCI_REG`, nonblocking reads, `DIAG_IOCTL_DCI_DEINIT`, status queries, and one DCI data canary sequence that set/query/cleared exactly log code `0x0000` and event id `0`.",
        "- No `DIAG_IOCTL_SWITCH_LOGGING`, broad log/event mask, DCI stream config, passive DIAG replay, QMI send, AP-side strace, boot-time QRTR matrix, or ptrace was run.",
        "- No `/dev/subsys_esoc0`, forced RC1/case, PMIC/GPIO/GDSC/regulator write, PCI rescan, bind/unbind, fake ONLINE, or eSoC notify/BOOT_DONE action was used.",
        "- Mutation scope: `/cache` one-shot clean-DSP flag, V2064 test-boot flash-handoff, namespace-local fallback readonly/readwrite RFS bridges, namespace-local persist-RFS tmpfs mirrors, private tmp-root `/dev/socket/logdw`, private tmp-root `/dev/diag`, tracefs uprobes, bounded DCI canary mask set/clear, and rollback to `stage3/boot_linux_v724.img` with selftest fail=0.",
        "",
    ])


def configure_prev2057() -> None:
    prev2063.prev2059.prev2057.CYCLE = CYCLE
    prev2063.prev2059.prev2057.OUT_DIR = OUT_DIR
    prev2063.prev2059.prev2057.HANDOFF_DIR = HANDOFF_DIR
    prev2063.prev2059.prev2057.HANDOFF_REPORT = HANDOFF_REPORT
    prev2063.prev2059.prev2057.REPORT_PATH = REPORT_PATH
    prev2063.prev2059.prev2057.V2056_OUT = V2064_OUT
    prev2063.prev2059.prev2057.V2056_INIT = V2064_INIT
    prev2063.prev2059.prev2057.V2056_BOOT = V2064_BOOT
    prev2063.prev2059.prev2057.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev2063.prev2059.prev2057.TEST_EXPECT_VERSION = TEST_EXPECT_VERSION
    prev2063.prev2059.prev2057.TEST_LOG_PATH = TEST_LOG_PATH
    prev2063.prev2059.prev2057.TEST_SUMMARY_PATH = TEST_SUMMARY_PATH
    prev2063.prev2059.prev2057.TEST_HELPER_RESULT_PATH = TEST_HELPER_RESULT_PATH
    prev2063.prev2059.prev2057.EXPECTED_HELPER_VERSION = EXPECTED_HELPER_VERSION
    prev2063.prev2059.prev2057.artifact_hook_check = artifact_hook_check
    prev2063.prev2059.prev2057.collect_details = collect_details
    prev2063.prev2059.prev2057.classify = classify
    prev2063.prev2059.prev2057.render_report = render_report


def main(argv: list[str] | None = None) -> int:
    configure_prev2057()
    return prev2063.prev2059.prev2057.main(argv)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

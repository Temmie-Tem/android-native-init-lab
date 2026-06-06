#!/usr/bin/env python3
"""V2069 rollbackable handoff for bounded DIAG DCI WLAN target-mask visibility."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import native_wifi_diag_dci_canary_mask_handoff_v2065 as prev2065


CYCLE = "V2069"
OUT_DIR = prev2065.prev2063.prev2059.prev2057.prev2046.prev2035.prev1998.prev1992.prev.repo_path(
    "tmp/wifi/v2069-dci-wlan-target-mask-handoff"
)
HANDOFF_DIR = OUT_DIR / "v2068-handoff"
HANDOFF_REPORT = OUT_DIR / "v2068-handoff-report.md"
REPORT_PATH = prev2065.prev2063.prev2059.prev2057.prev2046.prev2035.prev1998.prev1992.prev.repo_path(
    "docs/reports/NATIVE_INIT_V2069_DCI_WLAN_TARGET_MASK_HANDOFF_2026-06-04.md"
)
V2068_OUT = prev2065.prev2063.prev2059.prev2057.prev2046.prev2035.prev1998.prev1992.prev.repo_path(
    "tmp/wifi/v2068-dci-wlan-target-mask-test-boot"
)
V2068_INIT = V2068_OUT / "init_v2068_dci_wlan_target_mask"
V2068_BOOT = V2068_OUT / "boot_linux_v2068_dci_wlan_target_mask.img"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v2068/dev/__properties__"
TEST_EXPECT_VERSION = "A90 Linux init 0.9.213 (v2068-dci-wlan-target-mask)"
TEST_LOG_PATH = "/cache/native-init-wifi-test-boot-v2068.log"
TEST_SUMMARY_PATH = "/cache/native-init-wifi-test-boot-v2068.summary"
TEST_HELPER_RESULT_PATH = "/cache/native-init-wifi-test-boot-v2068-helper.result"
EXPECTED_HELPER_VERSION = "a90_android_execns_probe v398"


def rel(path: Path) -> str:
    return prev2065.rel(path)


def intish(value: object) -> int:
    return prev2065.intish(value)


def markdown_table(headers: list[str], rows: list[list[object]]) -> str:
    return prev2065.markdown_table(headers, rows)


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
        "diag_dci_wlan_target_mask_probe.switch_logging_attempted=1",
        "diag_dci_wlan_target_mask_probe.stream_config_attempted=1",
        "diag_dci_wlan_target_mask_probe.qmi_send=1",
        "diag_dci_wlan_target_mask_probe.ptraced=1",
        "diag_dci_canary_mask_probe.begin=1",
    )
    init_required = (
        "native-init-sibling-fwssctl-v641",
        "A90v641: sibling fwssctl proof armed",
        "wifi-v641-fwssctl",
        "A90v2068",
        "v2068-dci-wlan-target-mask",
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
        "diag_dci_register_read_probe.mode=private-node-rdwr-nonblock-dci-reg-read-with-bounded-wlan-target-mask-hold-clear",
        "diag_dci_register_read_probe.switch_logging_attempted=0",
        "diag_dci_register_read_probe.write_attempted=1",
        "diag_dci_register_read_probe.write_scope=bounded-dci-data-wlan-target-mask-set-hold-clear",
        "diag_dci_register_read_probe.stream_config_attempted=0",
        "diag_dci_register_read_probe.log_mask_write=1",
        "diag_dci_register_read_probe.event_mask_write=1",
        "diag_dci_wlan_target_mask_probe.begin=1",
        "diag_dci_wlan_target_mask_probe.mode=bounded-dci-data-write-targeted-wlan-log-event-masks-hold-until-cleanup-no-switch-logging",
        "diag_dci_wlan_target_mask_probe.diag_write_scope=dci-data-only-three-wlan-logs-three-wlan-events-set-hold-clear",
        "diag_dci_wlan_target_mask_probe.hold_until_cleanup=1",
        "diag_dci_wlan_target_mask_probe.cleanup.begin=1",
        "diag_dci_wlan_target_mask_probe.summary.completed=%d",
    )
    checks: dict[str, Any] = {}
    for path, required, forbidden in (
        (V2068_INIT, init_required, init_forbidden),
        (V2068_BOOT, boot_required, boot_forbidden),
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
    data = prev2065.prev2063.collect_diag_dci_register_read(fields)
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
        and data["write_scope"] == "bounded-dci-data-wlan-target-mask-set-hold-clear"
        and data["stream_config_attempted"] == 0
        and data["log_mask_write"] == 1
        and data["event_mask_write"] == 1
        and data["qmi_send"] == 0
        and data["ptraced"] == 0
    )
    return data


def collect_wlan_target_mask(fields: dict[str, str]) -> dict[str, Any]:
    prefix = "diag_dci_wlan_target_mask_probe"
    logs = []
    events = []
    for index in range(8):
        name = fields.get(f"{prefix}.log_{index:02d}.name")
        if name is not None:
            logs.append({
                "index": index,
                "name": name,
                "code": fields.get(f"{prefix}.log_{index:02d}.code", ""),
                "pre_is_set": intish(fields.get(f"{prefix}.log_{index:02d}.pre.status_is_set")),
                "set_write_rc": intish(fields.get(f"{prefix}.log_{index:02d}.set.write_rc")),
                "set_is_set": intish(fields.get(f"{prefix}.log_{index:02d}.set.status_is_set")),
                "clear_write_rc": intish(fields.get(f"{prefix}.log_{index:02d}.clear.write_rc")),
                "clear_is_set": intish(fields.get(f"{prefix}.log_{index:02d}.clear.status_is_set")),
            })
        event_name = fields.get(f"{prefix}.event_{index:02d}.name")
        if event_name is not None:
            events.append({
                "index": index,
                "name": event_name,
                "event_id": fields.get(f"{prefix}.event_{index:02d}.event_id", ""),
                "pre_is_set": intish(fields.get(f"{prefix}.event_{index:02d}.pre.status_is_set")),
                "set_write_rc": intish(fields.get(f"{prefix}.event_{index:02d}.set.write_rc")),
                "set_is_set": intish(fields.get(f"{prefix}.event_{index:02d}.set.status_is_set")),
                "clear_write_rc": intish(fields.get(f"{prefix}.event_{index:02d}.clear.write_rc")),
                "clear_is_set": intish(fields.get(f"{prefix}.event_{index:02d}.clear.status_is_set")),
            })
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
        "armed": intish(fields.get(f"{prefix}.armed")) or intish(fields.get(f"{prefix}.summary.armed")),
        "hold_until_cleanup": intish(fields.get(f"{prefix}.hold_until_cleanup")),
        "cleanup_begin": intish(fields.get(f"{prefix}.cleanup.begin")),
        "completed": intish(fields.get(f"{prefix}.completed")) or intish(fields.get(f"{prefix}.summary.completed")),
        "log_count": intish(fields.get(f"{prefix}.log_count")) or intish(fields.get(f"{prefix}.summary.log_count")),
        "event_count": intish(fields.get(f"{prefix}.event_count")) or intish(fields.get(f"{prefix}.summary.event_count")),
        "set_write_attempts": intish(fields.get(f"{prefix}.summary.set_write_attempts")),
        "set_write_successes": intish(fields.get(f"{prefix}.summary.set_write_successes")),
        "set_write_errors": intish(fields.get(f"{prefix}.summary.set_write_errors")),
        "clear_write_attempts": intish(fields.get(f"{prefix}.summary.clear_write_attempts")),
        "clear_write_successes": intish(fields.get(f"{prefix}.summary.clear_write_successes")),
        "clear_write_errors": intish(fields.get(f"{prefix}.summary.clear_write_errors")),
        "log_set_set_count": intish(fields.get(f"{prefix}.summary.log_set_set_count")),
        "log_clear_set_count": intish(fields.get(f"{prefix}.summary.log_clear_set_count")),
        "event_set_set_count": intish(fields.get(f"{prefix}.summary.event_set_set_count")),
        "event_clear_set_count": intish(fields.get(f"{prefix}.summary.event_clear_set_count")),
        "health_pre_received_logs": intish(fields.get(f"{prefix}.summary.health_pre_received_logs")),
        "health_pre_received_events": intish(fields.get(f"{prefix}.summary.health_pre_received_events")),
        "health_post_received_logs": intish(fields.get(f"{prefix}.summary.health_post_received_logs")),
        "health_post_received_events": intish(fields.get(f"{prefix}.summary.health_post_received_events")),
        "logs": logs,
        "events": events,
    }
    total_targets = data["log_count"] + data["event_count"]
    data["safe"] = (
        data["rootfs_namespace_only"] == 1
        and data["sda29_write"] == 0
        and data["switch_logging_attempted"] == 0
        and data["diag_write_attempted"] == 1
        and data["diag_write_scope"] == "dci-data-only-three-wlan-logs-three-wlan-events-set-hold-clear"
        and data["stream_config_attempted"] == 0
        and data["qmi_send"] == 0
        and data["ptraced"] == 0
    )
    data["set_ok"] = (
        total_targets == 6
        and data["set_write_attempts"] == total_targets
        and data["set_write_successes"] == total_targets
        and data["set_write_errors"] == 0
        and data["log_set_set_count"] == data["log_count"]
        and data["event_set_set_count"] == data["event_count"]
    )
    data["clear_ok"] = (
        total_targets == 6
        and data["clear_write_attempts"] == total_targets
        and data["clear_write_successes"] == total_targets
        and data["clear_write_errors"] == 0
        and data["log_clear_set_count"] == 0
        and data["event_clear_set_count"] == 0
    )
    data["health_delta_logs"] = data["health_post_received_logs"] - data["health_pre_received_logs"]
    data["health_delta_events"] = data["health_post_received_events"] - data["health_pre_received_events"]
    return data


def collect_details(handoff: dict[str, Any]) -> dict[str, Any]:
    details = prev2065.prev2063.prev2059.collect_details(handoff)
    fields = prev2065.prev2063.prev2059.prev2057.parse_fields()
    details["diag_dci_register_read"] = collect_diag_dci_register_read(fields)
    details["diag_dci_wlan_target_mask"] = collect_wlan_target_mask(fields)
    return details


def classify(handoff: dict[str, Any],
             hook: dict[str, Any],
             steps: list[dict[str, Any]],
             details: dict[str, Any]) -> dict[str, Any]:
    base = prev2065.prev2063.prev2059.classify(handoff, hook, steps, details)
    diag = details.get("diag_dci_register_read") if isinstance(details.get("diag_dci_register_read"), dict) else {}
    target = details.get("diag_dci_wlan_target_mask") if isinstance(details.get("diag_dci_wlan_target_mask"), dict) else {}
    hook_ok = all(bool(item.get("ok")) for item in hook.values())
    diag_started = intish(diag.get("begin")) == 1 and intish(diag.get("started")) == 1
    diag_safe = bool(diag.get("safe"))
    diag_open = intish(diag.get("open_ok")) == 1
    diag_registered = intish(diag.get("registered")) == 1
    target_started = intish(target.get("begin")) == 1
    target_safe = bool(target.get("safe"))
    target_set_ok = bool(target.get("set_ok"))
    target_clear_ok = bool(target.get("clear_ok"))
    target_completed = intish(target.get("completed")) == 1
    diag_payload = intish(diag.get("payload_records")) > 0
    cascade = details.get("cascade", {}) if isinstance(details.get("cascade"), dict) else {}
    logdw = details.get("tftp_logdw", {}) if isinstance(details.get("tftp_logdw"), dict) else {}
    summary = logdw.get("summary", {}) if isinstance(logdw.get("summary"), dict) else {}
    wlanmdsp_seen = intish(summary.get("wlanmdsp")) > 0 or intish(cascade.get("wlanmdsp_tftp")) > 0

    if not hook_ok:
        label = "dci-wlan-target-mask-artifact-hook-regression"
        passed = False
        reason = "V2068 artifact does not contain the bounded WLAN target-mask contract tokens"
    elif not diag_safe or not target_safe:
        label = "dci-wlan-target-mask-safety-regression"
        passed = False
        reason = "DIAG DCI WLAN target safety markers were absent or indicated logging-mode, stream, QMI, ptrace, or partition activity"
    elif not diag_started or not diag_open:
        label = "dci-wlan-target-mask-open-failed"
        passed = True
        reason = "private /dev/diag target-mask probe did not open"
    elif not diag_registered:
        label = "dci-wlan-target-mask-register-failed"
        passed = True
        reason = "DCI support exists, but DIAG_IOCTL_DCI_REG did not return a usable client for WLAN target masks"
    elif not target_started or not target_set_ok:
        label = "dci-wlan-target-mask-set-failed"
        passed = True
        reason = "bounded WLAN log/event target masks did not all set successfully"
    elif not target_completed or not target_clear_ok:
        label = "dci-wlan-target-mask-clear-failed"
        passed = False
        reason = "bounded WLAN log/event target masks were not proven cleared during cleanup"
    elif wlanmdsp_seen:
        label = "dci-wlan-target-mask-wlanmdsp-requested"
        passed = True
        reason = "bounded WLAN target masks were active and native requested wlanmdsp"
    elif diag_payload:
        label = "dci-wlan-target-mask-payload-seen-no-wlanmdsp"
        passed = True
        reason = "bounded WLAN target masks were active and DCI payload records appeared, but native still made no wlanmdsp request"
    else:
        label = "dci-wlan-target-mask-no-payload-no-wlanmdsp"
        passed = True
        reason = "bounded WLAN target masks were active, but no DCI payload records and no wlanmdsp request appeared"

    return {
        **base,
        "decision": f"v2069-{label}-rollback-{'pass' if passed else 'blocked'}",
        "label": label,
        "pass": passed,
        "reason": reason,
        "hook_ok": hook_ok,
        "diag_started": diag_started,
        "diag_safe": diag_safe,
        "diag_open": diag_open,
        "diag_registered": diag_registered,
        "target_started": target_started,
        "target_safe": target_safe,
        "target_set_ok": target_set_ok,
        "target_clear_ok": target_clear_ok,
        "target_completed": target_completed,
        "diag_payload": diag_payload,
    }


def render_report(manifest: dict[str, Any]) -> str:
    details = manifest["details"]
    classification = manifest["classification"]
    pm = details.get("per_mgr_vote_focused", {})
    diag = details.get("diag_dci_register_read", {})
    target = details.get("diag_dci_wlan_target_mask", {})
    logdw = details.get("tftp_logdw", {}) if isinstance(details.get("tftp_logdw"), dict) else {}
    cascade = details.get("cascade", {}) if isinstance(details.get("cascade"), dict) else {}
    samples = diag.get("samples", []) if isinstance(diag.get("samples"), list) else []
    logs = target.get("logs", []) if isinstance(target.get("logs"), list) else []
    events = target.get("events", []) if isinstance(target.get("events"), list) else []
    step_lines = [
        f"- `{step['name']}` rc `{step['rc']}` ok `{step['ok']}` evidence `{step['file']}`"
        for step in manifest["steps"]
    ]
    return "\n".join([
        "# Native Init V2069 DIAG DCI WLAN Target-Mask Handoff",
        "",
        "## Summary",
        "",
        "- Cycle: `V2069`",
        f"- Decision: `{manifest['decision']}`",
        f"- Label: `{manifest['label']}`",
        f"- Pass: `{manifest['pass']}`",
        f"- Reason: {manifest['reason']}",
        f"- Evidence: `{manifest['out_dir']}`",
        f"- Inner handoff: `{manifest['handoff_manifest']}`",
        "- Comparator: V2059 closed AP-side PerMgr register/vote; V2069 tests whether bounded WLAN-specific DCI masks expose modem/WLAN producer payload without switching DIAG logging mode.",
        "",
        "## Matrix",
        "",
        markdown_table(
            ["area", "value", "detail"],
            [
                ["route", classification.get("route_ok"), f"hook={classification.get('hook_ok')} diag_safe={classification.get('diag_safe')} target_safe={classification.get('target_safe')}"],
                ["diag_register", classification.get("diag_registered"), f"open={classification.get('diag_open')} proc={diag.get('selected_proc')} mask={diag.get('selected_mask')} rc={diag.get('register_rc')} client={diag.get('client_id')}"],
                ["target_set", classification.get("target_set_ok"), f"attempts={target.get('set_write_attempts')} success={target.get('set_write_successes')} errors={target.get('set_write_errors')} log_set={target.get('log_set_set_count')}/{target.get('log_count')} event_set={target.get('event_set_set_count')}/{target.get('event_count')}"],
                ["target_clear", classification.get("target_clear_ok"), f"attempts={target.get('clear_write_attempts')} success={target.get('clear_write_successes')} errors={target.get('clear_write_errors')} log_still_set={target.get('log_clear_set_count')} event_still_set={target.get('event_clear_set_count')} completed={target.get('completed')}"],
                ["health", "", f"pre_logs={target.get('health_pre_received_logs')} post_logs={target.get('health_post_received_logs')} delta_logs={target.get('health_delta_logs')} pre_events={target.get('health_pre_received_events')} post_events={target.get('health_post_received_events')} delta_events={target.get('health_delta_events')}"],
                ["diag_reads", diag.get("payload_records"), f"records={diag.get('read_records')} bytes={diag.get('read_bytes')} payload={diag.get('payload_records')} bootstrap={diag.get('mask_bootstrap_records')} other={diag.get('other_records')} errors={diag.get('read_errors')} terminal_error={diag.get('read_terminal_error')}"],
                ["tftp_branch", "", f"server_check={logdw.get('summary', {}).get('server_check')} ota={logdw.get('summary', {}).get('ota_firewall')} mcfg={logdw.get('summary', {}).get('mcfg')} wlanmdsp={logdw.get('summary', {}).get('wlanmdsp')}"],
                ["cascade", "", f"wlan_pd={cascade.get('wlan_pd_up')} icnss_qmi={cascade.get('icnss_qmi_connected')} fw_ready={cascade.get('fw_ready')} wlan0={cascade.get('wlan0')}"],
            ],
        ),
        "",
        "## Target Logs",
        "",
        markdown_table(
            ["idx", "name", "code", "pre", "set_rc", "set", "clear_rc", "clear"],
            [[item.get("index"), item.get("name"), item.get("code"), item.get("pre_is_set"), item.get("set_write_rc"), item.get("set_is_set"), item.get("clear_write_rc"), item.get("clear_is_set")] for item in logs] or [["none", "", "", "", "", "", "", ""]],
        ),
        "",
        "## Target Events",
        "",
        markdown_table(
            ["idx", "name", "event_id", "pre", "set_rc", "set", "clear_rc", "clear"],
            [[item.get("index"), item.get("name"), item.get("event_id"), item.get("pre_is_set"), item.get("set_write_rc"), item.get("set_is_set"), item.get("clear_write_rc"), item.get("clear_is_set")] for item in events] or [["none", "", "", "", "", "", "", ""]],
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
        "- If `dci-wlan-target-mask-payload-seen-no-wlanmdsp`, decode the DCI samples and choose a narrower modem-side trace point.",
        "- If `dci-wlan-target-mask-no-payload-no-wlanmdsp`, mask-only DCI without `DIAG_IOCTL_SWITCH_LOGGING` still does not expose the producer; the next modem-side step is an explicit logging-mode/mask design gate or structured Frida/QMI tracing.",
        "- If `dci-wlan-target-mask-wlanmdsp-requested`, chase the normal downstream cascade to BDF, FW-ready, and `wlan0`.",
        "",
        "## Steps",
        "",
        *step_lines,
        *([] if step_lines else ["- `none`"]),
        "",
        "## Safety",
        "",
        "- No Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping was used.",
        "- DIAG use was limited to a private rootfs `/dev/diag` char node, `DIAG_IOCTL_DCI_SUPPORT`, `DIAG_IOCTL_DCI_REG`, nonblocking reads, `DIAG_IOCTL_DCI_DEINIT`, status queries, and exactly three WLAN log masks plus three WLAN event masks set during the lower window and cleared during cleanup.",
        "- No `DIAG_IOCTL_SWITCH_LOGGING`, broad log/event mask, DCI stream config, passive DIAG replay, QMI send, AP-side strace, boot-time QRTR matrix, or ptrace was run.",
        "- No `/dev/subsys_esoc0`, forced RC1/case, PMIC/GPIO/GDSC/regulator write, PCI rescan, bind/unbind, fake ONLINE, or eSoC notify/BOOT_DONE action was used.",
        "- Mutation scope: `/cache` one-shot clean-DSP flag, V2068 test-boot flash-handoff, namespace-local fallback readonly/readwrite RFS bridges, namespace-local persist-RFS tmpfs mirrors, private tmp-root `/dev/socket/logdw`, private tmp-root `/dev/diag`, tracefs uprobes, bounded DCI WLAN target masks, and rollback to `stage3/boot_linux_v724.img` with selftest fail=0.",
        "",
    ])


def configure_prev2057() -> None:
    prev2065.prev2063.prev2059.prev2057.CYCLE = CYCLE
    prev2065.prev2063.prev2059.prev2057.OUT_DIR = OUT_DIR
    prev2065.prev2063.prev2059.prev2057.HANDOFF_DIR = HANDOFF_DIR
    prev2065.prev2063.prev2059.prev2057.HANDOFF_REPORT = HANDOFF_REPORT
    prev2065.prev2063.prev2059.prev2057.REPORT_PATH = REPORT_PATH
    prev2065.prev2063.prev2059.prev2057.V2056_OUT = V2068_OUT
    prev2065.prev2063.prev2059.prev2057.V2056_INIT = V2068_INIT
    prev2065.prev2063.prev2059.prev2057.V2056_BOOT = V2068_BOOT
    prev2065.prev2063.prev2059.prev2057.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev2065.prev2063.prev2059.prev2057.TEST_EXPECT_VERSION = TEST_EXPECT_VERSION
    prev2065.prev2063.prev2059.prev2057.TEST_LOG_PATH = TEST_LOG_PATH
    prev2065.prev2063.prev2059.prev2057.TEST_SUMMARY_PATH = TEST_SUMMARY_PATH
    prev2065.prev2063.prev2059.prev2057.TEST_HELPER_RESULT_PATH = TEST_HELPER_RESULT_PATH
    prev2065.prev2063.prev2059.prev2057.EXPECTED_HELPER_VERSION = EXPECTED_HELPER_VERSION
    prev2065.prev2063.prev2059.prev2057.artifact_hook_check = artifact_hook_check
    prev2065.prev2063.prev2059.prev2057.collect_details = collect_details
    prev2065.prev2063.prev2059.prev2057.classify = classify
    prev2065.prev2063.prev2059.prev2057.render_report = render_report


def main(argv: list[str] | None = None) -> int:
    configure_prev2057()
    return prev2065.prev2063.prev2059.prev2057.main(argv)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

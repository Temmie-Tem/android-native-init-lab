#!/usr/bin/env python3
"""V2130 rollbackable handoff for the post-FW_READY boot_wlan edge."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import native_wifi_icnss_event_stats_handoff_v2128 as prev2128


CYCLE = "V2130"
REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v2130-post-fw-ready-boot-wlan-handoff"
HANDOFF_DIR = OUT_DIR / "v2129-handoff"
HANDOFF_REPORT = OUT_DIR / "v2129-handoff-report.md"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V2130_POST_FW_READY_BOOT_WLAN_HANDOFF_2026-06-05.md"
)
V2129_OUT = REPO_ROOT / "tmp" / "wifi" / "v2129-post-fw-ready-boot-wlan-test-boot"
V2129_INIT = V2129_OUT / "init_v2129_post_fw_ready_boot_wlan"
V2129_BOOT = V2129_OUT / "boot_linux_v2129_post_fw_ready_boot_wlan.img"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v2129/dev/__properties__"
TEST_EXPECT_VERSION = "A90 Linux init 0.9.239 (v2129-post-fw-ready-boot-wlan)"
TEST_LOG_PATH = "/cache/native-init-wifi-test-boot-v2129.log"
TEST_SUMMARY_PATH = "/cache/native-init-wifi-test-boot-v2129.summary"
TEST_HELPER_RESULT_PATH = "/cache/native-init-wifi-test-boot-v2129-helper.result"
EXPECTED_HELPER_VERSION = "a90_android_execns_probe v423"

BASE_COLLECT_DETAILS = prev2128.collect_details
BASE_CLASSIFY = prev2128.classify


def intish(value: object) -> int:
    return prev2128.intish(value)


def rel(path: Path) -> str:
    return prev2128.rel(path)


def markdown_table(headers: list[str], rows: list[list[object]]) -> str:
    return prev2128.markdown_table(headers, rows)


def artifact_hook_check() -> dict[str, Any]:
    init_required = (
        "native-init-sibling-fwssctl-v641",
        "A90v641: sibling fwssctl proof armed",
        "wifi-v641-fwssctl",
        "A90v2129",
        "wifi-companion-wlan-pd-post-pm-lower-state-observer-start-only",
        "--timeout-sec",
        "75",
    )
    init_forbidden = (
        "--allow-servloc-domain-list-probe",
        "--allow-service-notifier-listener-probe",
        "--qrtr-readback-matrix",
        "wlfw:69:0,1",
        "--pm-observer-private-cnss-daemon-sdx50m",
        "--private-cnss-daemon-path",
    )
    boot_required = (
        EXPECTED_HELPER_VERSION,
        "post_fw_ready_boot_wlan_trigger",
        "%s.begin=1",
        "%s.active_driver_start=1",
        "%s.path=%s",
        "%s.no_wifi_hal=1",
        "%s.pre.fw_ready_processed=%d",
        "%s.pre.register_driver_posted=%d",
        "%s.gate_ready=%d",
        "%s.executed=1",
        "%s.write_rc=%d",
        "wlan_pd_icnss_ipc_snapshot.%s.icnss_stats.event.register_driver.posted=%d",
        "after_boot_wlan_trigger",
        "wlan_pd_icnss_ipc_snapshot.%s.icnss_stats.event_summary=1",
        "wlfw_late_msg21_focused.begin=1",
        "per_mgr_vote_focused.begin=1",
        "icnss_qcacld_post_bdf_focused",
    )
    boot_forbidden = (
        "diag_remote_dev_poll_probe.begin=1",
        "diag_wlan_pd_memory_device_probe.begin=1",
        "diag_wlan_pd_memory_regular_mask_probe.begin=1",
        "diag_dci_register_read_probe.begin=1",
        "wlan_pd_tftp_server_trace.late_attach.begin=1",
        "wifi_companion_start.wlan_pd_producer_tftp_server_syscall_trace.compiled=1",
        "wifi_companion_start.macloader_syscall_trace.compiled=1",
        "PTRACE_ATTACH",
        "post_bdf_boot_wlan_consumer_gate.begin=1",
        "ota_firewall/ruleset:",
        "tftp_server-android-runtime",
    )
    checks: dict[str, Any] = {}
    for path, required in ((V2129_INIT, init_required), (V2129_BOOT, boot_required)):
        key = rel(path)
        forbidden_tokens = init_forbidden if path == V2129_INIT else boot_forbidden
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


def collect_trigger(fields: dict[str, str]) -> dict[str, Any]:
    prefix = "post_fw_ready_boot_wlan_trigger."
    int_fields = (
        "begin",
        "allowed",
        "active_driver_start",
        "no_wifi_hal",
        "scan_connect",
        "credentials",
        "dhcp_routing",
        "external_ping",
        "no_module_load_unload",
        "no_driver_bind_unbind",
        "stats_read_rc",
        "stats_read_errno",
        "pre.fw_ready_processed",
        "pre.register_driver_posted",
        "pre.register_driver_processed",
        "path.exists",
        "path.writable",
        "path.mode",
        "path.errno",
        "gate_ready",
        "executed",
        "write_value_len",
        "write_rc",
        "open_errno",
        "write_errno",
        "close_errno",
        "duration_ms",
    )
    data: dict[str, Any] = {
        "path": fields.get(prefix + "path", ""),
        "reason": fields.get(prefix + "reason", ""),
    }
    for key in int_fields:
        data[key.replace(".", "_")] = intish(fields.get(prefix + key))
    data["safe"] = (
        data["begin"] == 1
        and data["allowed"] == 1
        and data["active_driver_start"] == 1
        and data["no_wifi_hal"] == 1
        and data["scan_connect"] == 0
        and data["credentials"] == 0
        and data["dhcp_routing"] == 0
        and data["external_ping"] == 0
        and data["no_module_load_unload"] == 1
        and data["no_driver_bind_unbind"] == 1
    )
    return data


def collect_details(handoff: dict[str, Any]) -> dict[str, Any]:
    details = BASE_COLLECT_DETAILS(handoff)
    fields = prev2128.parse_fields(prev2128.read_helper_text())
    details["post_fw_ready_boot_wlan_trigger"] = collect_trigger(fields)
    return details


def classify(handoff: dict[str, Any],
             hook: dict[str, Any],
             steps: list[dict[str, Any]],
             details: dict[str, Any]) -> dict[str, Any]:
    base = BASE_CLASSIFY(handoff, hook, steps, details)
    cascade = details.get("cascade") if isinstance(details.get("cascade"), dict) else {}
    stats = details.get("icnss_stats_numeric") if isinstance(details.get("icnss_stats_numeric"), dict) else {}
    trigger = details.get("post_fw_ready_boot_wlan_trigger") if isinstance(details.get("post_fw_ready_boot_wlan_trigger"), dict) else {}
    hook_ok = all(bool(item.get("ok")) for item in hook.values())
    steps_ok = all(bool(step.get("ok")) for step in steps)
    trigger_safe = bool(trigger.get("safe"))
    trigger_executed = intish(trigger.get("executed")) > 0
    trigger_write_ok = trigger_executed and intish(trigger.get("write_rc")) == 0
    gate_ready = intish(trigger.get("gate_ready")) > 0
    wlan0 = intish(cascade.get("wlan0")) > 0
    fw_ready = intish(cascade.get("fw_ready")) > 0
    register_driver_posted = intish(stats.get("event.register_driver.posted"))
    register_driver_processed = intish(stats.get("event.register_driver.processed"))
    fw_ready_processed = intish(stats.get("event.fw_ready.processed"))
    route_ok = (
        hook_ok
        and steps_ok
        and bool(base.get("shared_server_info_bridge_ok"))
        and intish(base.get("server_info_startup_error_count")) == 0
        and intish(cascade.get("wlan_pd_up")) > 0
        and intish(cascade.get("icnss_qmi_connected")) > 0
        and intish(stats.get("event_summary")) > 0
        and fw_ready_processed > 0
    )

    if not hook_ok:
        label = "post-fw-ready-boot-wlan-artifact-hook-regression"
        passed = False
        reason = "V2129 artifact did not contain the post-FW_READY boot_wlan contract"
    elif not route_ok:
        label = "post-fw-ready-boot-wlan-route-regression"
        passed = False
        reason = "V2130 did not preserve the V2128 route, rollback, or pre-trigger ICNSS prerequisites"
    elif not trigger_safe:
        label = "post-fw-ready-boot-wlan-safety-regression"
        passed = False
        reason = "post-FW_READY boot_wlan trigger safety markers were absent or unsafe"
    elif not gate_ready or fw_ready_processed <= 0:
        label = "post-fw-ready-boot-wlan-gate-not-ready"
        passed = True
        reason = "helper did not observe ICNSS FW_READY processed, so it correctly skipped boot_wlan"
    elif not trigger_executed:
        label = "post-fw-ready-boot-wlan-not-executed"
        passed = True
        reason = "post-FW_READY trigger was enabled but did not execute"
    elif not trigger_write_ok:
        label = "post-fw-ready-boot-wlan-write-failed"
        passed = True
        reason = "post-FW_READY boot_wlan write failed before ICNSS could post REGISTER_DRIVER"
    elif wlan0:
        label = "post-fw-ready-boot-wlan-wlan0-progress"
        passed = True
        reason = "post-FW_READY boot_wlan produced wlan0; stop before scan/connect and run the dedicated connectivity gate"
    elif fw_ready:
        label = "post-fw-ready-boot-wlan-fw-ready-progress"
        passed = True
        reason = "post-FW_READY boot_wlan produced the kernel FW_READY dmesg marker but wlan0 is still absent"
    elif register_driver_processed > 0:
        label = "post-fw-ready-boot-wlan-register-driver-processed-no-wlan0"
        passed = True
        reason = "boot_wlan posted/processed REGISTER_DRIVER, but wlan0 did not appear"
    elif register_driver_posted > 0:
        label = "post-fw-ready-boot-wlan-register-driver-posted-not-processed"
        passed = True
        reason = "boot_wlan posted REGISTER_DRIVER, but the ICNSS event worker did not process it"
    else:
        label = "post-fw-ready-boot-wlan-write-ok-register-driver-not-posted"
        passed = True
        reason = "boot_wlan write returned success, but ICNSS REGISTER_DRIVER stayed 0/0"

    return {
        **base,
        "decision": f"v2130-{label}-rollback-{'pass' if passed else 'blocked'}",
        "label": label,
        "pass": passed,
        "reason": reason,
        "hook_ok": hook_ok,
        "route_ok": route_ok,
        "trigger_safe": trigger_safe,
        "trigger_gate_ready": gate_ready,
        "trigger_executed": trigger_executed,
        "trigger_write_ok": trigger_write_ok,
        "trigger_reason": trigger.get("reason", ""),
        "trigger_duration_ms": trigger.get("duration_ms", 0),
        "icnss_fw_ready_processed": fw_ready_processed,
        "icnss_register_driver_posted": register_driver_posted,
        "icnss_register_driver_processed": register_driver_processed,
    }


def render_report(manifest: dict[str, Any]) -> str:
    details = manifest["details"]
    classification = manifest["classification"]
    cascade = details.get("cascade", {}) if isinstance(details.get("cascade"), dict) else {}
    trigger = details.get("post_fw_ready_boot_wlan_trigger", {}) if isinstance(details.get("post_fw_ready_boot_wlan_trigger"), dict) else {}
    stats = details.get("icnss_stats_numeric", {}) if isinstance(details.get("icnss_stats_numeric"), dict) else {}
    focused = details.get("wlfw_late_msg21_focused", {}) if isinstance(details.get("wlfw_late_msg21_focused"), dict) else {}
    step_lines = [
        f"- `{step['name']}` rc `{step['rc']}` ok `{step['ok']}` evidence `{step['file']}`"
        for step in manifest["steps"]
    ]
    return "\n".join([
        "# Native Init V2130 Post-FW_READY Boot WLAN Handoff",
        "",
        "## Summary",
        "",
        "- Cycle: `V2130`",
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
                ["artifact", classification.get("hook_ok"), f"helper={EXPECTED_HELPER_VERSION}"],
                ["route", classification.get("route_ok"), f"cap_bdf_cal={classification.get('cap_bdf_cal_success')} trigger_safe={classification.get('trigger_safe')}"],
                ["trigger", classification.get("trigger_write_ok"), f"gate={classification.get('trigger_gate_ready')} executed={classification.get('trigger_executed')} reason={classification.get('trigger_reason')} duration_ms={classification.get('trigger_duration_ms')}"],
                ["trigger_pre", "", f"fw_ready_processed={trigger.get('pre_fw_ready_processed')} register_driver={trigger.get('pre_register_driver_posted')}/{trigger.get('pre_register_driver_processed')} path={trigger.get('path')} writable={trigger.get('path_writable')}"],
                ["icnss_events", "", f"fw_ready={classification.get('icnss_fw_ready_processed')} register_driver={classification.get('icnss_register_driver_posted')}/{classification.get('icnss_register_driver_processed')} state={classification.get('icnss_state_hex')}"],
                ["focused_msg", "", f"qmi={classification.get('focused_qmi_hits')} msg21={classification.get('focused_saw_msg21')} msg2b={classification.get('focused_saw_msg2b')} msg37={classification.get('focused_saw_msg37')}"],
                ["cascade", "", f"wlan_pd={cascade.get('wlan_pd_up')} icnss_qmi={cascade.get('icnss_qmi_connected')} wlfw69={cascade.get('wlfw69')} fw_ready={cascade.get('fw_ready')} wlan0={cascade.get('wlan0')}"],
            ],
        ),
        "",
        "## ICNSS Stats",
        "",
        markdown_table(["area", "value", "detail"], prev2128.stats_rows(stats)),
        "",
        "## Focused Indication",
        "",
        markdown_table(["edge", "hits", "detail"], prev2128.focused_rows(focused)),
        "",
        "## Interpretation",
        "",
        "- V2130 changes one thing after V2128: it writes `/sys/kernel/boot_wlan/boot_wlan` only after ICNSS `FW_READY` is already processed.",
        "- This is not a WLAN-PD producer retry; V2128 already proved the producer side reached `FW CONN | FW READY | WLAN FW EXISTS` before the missing `REGISTER_DRIVER` edge.",
        "- Branch target is now exact: does the bounded Android driver-start sysfs write post/process `REGISTER_DRIVER`, and does that yield `wlan0`?",
        "",
        "## Steps",
        "",
        *step_lines,
        *([] if step_lines else ["- `none`"]),
        "",
        "## Safety",
        "",
        "- No Wi-Fi HAL, wificond, supplicant, hostapd, scan/connect, credentials, DHCP/routes, or external ping was used.",
        "- No macloader retry, DIAG, rild/cnss/pm-service strace, boot-time QRTR matrix, QMI payload send, `tftp_server` ptrace, module load/unload, or driver bind/unbind was run.",
        "- No `/dev/subsys_esoc0`, forced RC1/case, PMIC/GPIO/GDSC/regulator write, PCI rescan, bind/unbind, fake ONLINE, or eSoC notify/BOOT_DONE action was used.",
        "- Mutation scope: `/cache` one-shot clean-DSP flag, V2129 test-boot flash-handoff, namespace-local RFS bridges/tmpfs mirrors, one gated `/sys/kernel/boot_wlan/boot_wlan` write after FW_READY, and rollback to `stage3/boot_linux_v724.img` with selftest fail=0.",
        "",
    ])


def configure() -> None:
    prev2128.CYCLE = CYCLE
    prev2128.OUT_DIR = OUT_DIR
    prev2128.HANDOFF_DIR = HANDOFF_DIR
    prev2128.HANDOFF_REPORT = HANDOFF_REPORT
    prev2128.REPORT_PATH = REPORT_PATH
    prev2128.V2127_OUT = V2129_OUT
    prev2128.V2127_INIT = V2129_INIT
    prev2128.V2127_BOOT = V2129_BOOT
    prev2128.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev2128.TEST_EXPECT_VERSION = TEST_EXPECT_VERSION
    prev2128.TEST_LOG_PATH = TEST_LOG_PATH
    prev2128.TEST_SUMMARY_PATH = TEST_SUMMARY_PATH
    prev2128.TEST_HELPER_RESULT_PATH = TEST_HELPER_RESULT_PATH
    prev2128.EXPECTED_HELPER_VERSION = EXPECTED_HELPER_VERSION
    prev2128.ICNSS_STATS_PHASES = (
        "after_boot_wlan_trigger",
        "after_post_listener_window",
        "after_early_listener",
        "after_holder_start",
    )
    prev2128.artifact_hook_check = artifact_hook_check
    prev2128.collect_details = collect_details
    prev2128.classify = classify
    prev2128.render_report = render_report


def main(argv: list[str] | None = None) -> int:
    configure()
    return prev2128.main(argv)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

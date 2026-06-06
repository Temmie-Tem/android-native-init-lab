#!/usr/bin/env python3
"""V2007 rollbackable handoff for post-BDF tail probes."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import native_wifi_post_cap_bdf_branch_handoff_v2005 as prev2005


CYCLE = "V2007"
OUT_DIR = prev2005.prev2000.prev1998.prev1992.prev.repo_path("tmp/wifi/v2007-post-bdf-tail-handoff")
HANDOFF_DIR = OUT_DIR / "v2006-handoff"
HANDOFF_REPORT = OUT_DIR / "v2006-handoff-report.md"
REPORT_PATH = prev2005.prev2000.prev1998.prev1992.prev.repo_path(
    "docs/reports/NATIVE_INIT_V2007_POST_BDF_TAIL_HANDOFF_2026-06-04.md"
)
V2006_OUT = prev2005.prev2000.prev1998.prev1992.prev.repo_path("tmp/wifi/v2006-post-bdf-tail-test-boot")
V2006_INIT = V2006_OUT / "init_v2006_post_bdf_tail"
V2006_BOOT = V2006_OUT / "boot_linux_v2006_post_bdf_tail.img"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v2006/dev/__properties__"
TEST_EXPECT_VERSION = "A90 Linux init 0.9.185 (v2006-post-bdf-tail)"
TEST_LOG_PATH = "/cache/native-init-wifi-test-boot-v2006.log"
TEST_SUMMARY_PATH = "/cache/native-init-wifi-test-boot-v2006.summary"
TEST_HELPER_RESULT_PATH = "/cache/native-init-wifi-test-boot-v2006-helper.result"

prev2000 = prev2005.prev2000
prev1998 = prev2005.prev1998
ORIGINAL_PATCH_PREV_MODULE = prev2005.ORIGINAL_PATCH_PREV_MODULE
ORIGINAL_COLLECT_DETAILS = prev2005.ORIGINAL_COLLECT_DETAILS

TAIL_EVENTS = (
    "wlfw_cal_report_entry",
    "wlfw_cal_report_send_ret",
    "wlfw_cal_report_error_branch",
    "wlfw_cal_report_success_branch",
    "wlfw_cal_report_return",
    "dms_get_wlan_address_entry",
    "dms_get_wlan_address_send_ret",
    "dms_get_wlan_address_valid_mac",
    "dms_get_wlan_address_return",
    "dms_service_request_init_ret",
    "dms_service_request_cond_wait",
    "dms_service_request_send_ret",
    "dms_service_request_success_branch",
    "wlan_send_status_entry",
    "wlan_send_status_send_ret",
    "wlan_send_status_return",
    "wlan_send_version_entry",
    "wlan_send_version_open_success",
    "wlan_send_version_not_found",
    "wlan_send_version_send_ret",
    "wlan_send_version_return",
)


def rel(path: Path) -> str:
    return prev2005.rel(path)


def event(fields: dict[str, str], name: str) -> dict[str, str]:
    return prev2005.event(fields, name)


def hit(events: dict[str, dict[str, str]], name: str) -> int:
    return prev2005.hit(events, name)


def first_event_value(data: dict[str, str], *keys: str) -> str:
    return prev2005.first_event_value(data, *keys)


def is_zero(value: str) -> bool:
    return prev2005.is_zero(value)


def artifact_hook_check() -> dict[str, Any]:
    init_required = (
        "native-init-sibling-fwssctl-v641",
        "A90v641: sibling fwssctl proof armed",
        "wifi-v641-fwssctl",
        "A90v2006",
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
        *init_required,
        "a90_android_execns_probe v372",
        "wlfw_bdf_return",
        "wlfw_cal_report_entry",
        "wlfw_cal_report_return",
        "dms_get_wlan_address_entry",
        "dms_service_request_send_ret",
        "wlan_send_status_entry",
        "wlan_send_version_entry",
        "wlan_pd_firmware_serve_gate.rfs_bridge",
        "server_check.absolute=/vendor/rfs/msm/mpss/readwrite/server_check.txt",
        "readwrite.tmpfs_requested=1",
        "wifi_companion_start.cnss_daemon_argv=/vendor/bin/cnss-daemon -n -l",
        "wlan_pd_icnss_ipc_snapshot",
    )
    boot_forbidden = (
        "wlan_pd_tftp_server_trace.late_attach.begin=1",
        "wifi_companion_start.wlan_pd_producer_tftp_server_syscall_trace.compiled=1",
    )
    checks: dict[str, Any] = {}
    for path, required in ((V2006_INIT, init_required), (V2006_BOOT, boot_required)):
        forbidden_tokens = init_forbidden if path == V2006_INIT else boot_forbidden
        if not path.exists():
            checks[rel(path)] = {"exists": False, "ok": False, "missing": list(required), "forbidden": []}
            continue
        data = path.read_bytes()
        missing = [token for token in required if token.encode() not in data]
        forbidden = [token for token in forbidden_tokens if token.encode() in data]
        checks[rel(path)] = {"exists": True, "ok": not missing and not forbidden, "missing": missing, "forbidden": forbidden}
    return checks


def collect_post_bdf_tail(fields: dict[str, str]) -> dict[str, Any]:
    core_events = {name: event(fields, name) for name in prev2005.CORE_EVENTS}
    cap_events = {name: event(fields, name) for name in prev2005.CAP_EVENTS}
    bdf_events = {name: event(fields, name) for name in prev2005.BDF_EVENTS}
    tail_events = {name: event(fields, name) for name in TAIL_EVENTS}
    cal_success = tail_events["wlfw_cal_report_success_branch"]
    cal_send = tail_events["wlfw_cal_report_send_ret"]
    return {
        "core_events": core_events,
        "cap_events": cap_events,
        "bdf_events": bdf_events,
        "tail_events": tail_events,
        "nonlog_label": fields.get("wlan_pd_cnss_nonlog_control_flow.label", ""),
        "cap_return_rc": first_event_value(cap_events["wlfw_cap_return"], "rc"),
        "bdf_return_rc": first_event_value(bdf_events["wlfw_bdf_return"], "rc"),
        "bdf_send_rc": first_event_value(bdf_events["wlfw_bdf_send_ret"], "send_rc"),
        "bdf_qmi_result": first_event_value(bdf_events["wlfw_bdf_result_log"], "qmi_result"),
        "cal_send_rc": first_event_value(tail_events["wlfw_cal_report_send_ret"], "send_rc"),
        "cal_qmi_result": first_event_value(cal_success, "qmi_result") or first_event_value(cal_send, "qmi_result"),
        "cal_qmi_error": first_event_value(cal_success, "qmi_error") or first_event_value(cal_send, "qmi_error"),
        "cal_return_rc": first_event_value(tail_events["wlfw_cal_report_return"], "rc"),
        "dms_addr_send_rc": first_event_value(tail_events["dms_get_wlan_address_send_ret"], "send_rc"),
        "dms_addr_qmi_result": first_event_value(tail_events["dms_get_wlan_address_send_ret"], "qmi_result"),
        "dms_addr_return_rc": first_event_value(tail_events["dms_get_wlan_address_return"], "rc"),
        "dms_req_init_rc": first_event_value(tail_events["dms_service_request_init_ret"], "rc"),
        "dms_req_send_rc": first_event_value(tail_events["dms_service_request_send_ret"], "send_rc"),
        "dms_req_qmi_result": first_event_value(tail_events["dms_service_request_send_ret"], "qmi_result"),
        "dms_req_qmi_error": first_event_value(tail_events["dms_service_request_send_ret"], "qmi_error"),
        "status_send_rc": first_event_value(tail_events["wlan_send_status_send_ret"], "send_rc"),
        "status_qmi_result": first_event_value(tail_events["wlan_send_status_send_ret"], "qmi_result"),
        "status_return_rc": first_event_value(tail_events["wlan_send_status_return"], "rc"),
        "version_send_rc": first_event_value(tail_events["wlan_send_version_send_ret"], "send_rc"),
        "version_qmi_result": first_event_value(tail_events["wlan_send_version_send_ret"], "qmi_result"),
        "version_return_rc": first_event_value(tail_events["wlan_send_version_return"], "rc"),
    }


def collect_details(handoff: dict[str, Any]) -> dict[str, Any]:
    details = ORIGINAL_COLLECT_DETAILS(handoff)
    fields = prev1998.parse_fields(prev1998.read_helper_text())
    helper = details.get("helper_completion") if isinstance(details.get("helper_completion"), dict) else {}
    if helper:
        helper["version_ok"] = helper.get("result_file_version") == "a90_android_execns_probe v372"
        helper["ok"] = bool(
            helper.get("text_present")
            and helper.get("version_ok")
            and helper.get("probe_run_rc_ok")
            and helper.get("child_exit_code_ok")
            and helper.get("child_signal_ok")
            and helper.get("test_flash_ok")
            and helper.get("rollback_version_ok")
            and helper.get("rollback_selftest_fail_zero")
        )
    details["cascade"] = prev2000.collect_cascade(fields, details)
    details["post_bdf_tail"] = collect_post_bdf_tail(fields)
    return details


def classify(handoff: dict[str, Any],
             hook: dict[str, Any],
             steps: list[dict[str, Any]],
             details: dict[str, Any]) -> dict[str, Any]:
    base = prev1998.ORIGINAL_CLASSIFY(handoff, hook, steps, details)
    trace = details.get("wlanmdsp_trace") if isinstance(details.get("wlanmdsp_trace"), dict) else {}
    bridge = trace.get("rfs_bridge") if isinstance(trace.get("rfs_bridge"), dict) else {}
    helper = details.get("helper_completion") if isinstance(details.get("helper_completion"), dict) else {}
    readwrite = details.get("readwrite_bridge") if isinstance(details.get("readwrite_bridge"), dict) else {}
    cascade = details.get("cascade") if isinstance(details.get("cascade"), dict) else {}
    post = details.get("post_bdf_tail") if isinstance(details.get("post_bdf_tail"), dict) else {}
    cap = post.get("cap_events") if isinstance(post.get("cap_events"), dict) else {}
    bdf = post.get("bdf_events") if isinstance(post.get("bdf_events"), dict) else {}
    tail = post.get("tail_events") if isinstance(post.get("tail_events"), dict) else {}
    cap_bdf_success = (
        hit(cap, "wlfw_cap_success_branch") > 0
        and hit(bdf, "wlfw_bdf_return") > 0
        and is_zero(str(post.get("bdf_return_rc", "")))
    )
    route_ok = (
        bool(base.get("hook_ok"))
        and bool(base.get("prearm_ok"))
        and bool(base.get("rollback_ok"))
        and bool(base.get("light_ok"))
        and (bool(base.get("combined")) or cap_bdf_success)
        and bool(bridge.get("ok"))
        and bool(helper.get("ok"))
        and bool(readwrite.get("ok"))
    )
    if not route_ok:
        label = "post-bdf-tail-route-regression"
        reason = "V2006 did not preserve rollback, light observer, bridge, PM/CNSS, or helper prerequisites"
        passed = False
    elif int(cascade.get("wlan0", 0)) > 0:
        label = "post-bdf-tail-wlan0-progress"
        reason = "V2006 reached wlan0; stop before credentials/scan/connect until a dedicated gated unit"
        passed = True
    elif int(cascade.get("fw_ready", 0)) > 0:
        label = "post-bdf-tail-fw-ready-progress"
        reason = "V2006 crossed into visible FW-ready progress"
        passed = True
    elif hit(cap, "wlfw_cap_success_branch") == 0 or hit(bdf, "wlfw_bdf_return") == 0 or not is_zero(str(post.get("bdf_return_rc", ""))):
        label = "post-bdf-tail-bdf-regression"
        reason = "V2006 did not reproduce V2005's successful cap/BDF path"
        passed = False
    elif hit(tail, "wlfw_cal_report_entry") == 0:
        label = "post-bdf-tail-cal-report-not-called"
        reason = "BDF returned success, but `wlfw_send_cal_report_req` was never entered"
        passed = True
    elif hit(tail, "wlfw_cal_report_send_ret") == 0:
        label = "post-bdf-tail-cal-report-send-blocked"
        reason = "Cal-report helper entered but the WLFW cal-report QMI send did not return"
        passed = True
    elif hit(tail, "wlfw_cal_report_error_branch") > 0 or not is_zero(str(post.get("cal_send_rc", ""))) or not is_zero(str(post.get("cal_qmi_result", ""))) or not is_zero(str(post.get("cal_return_rc", ""))):
        label = "post-bdf-tail-cal-report-error"
        reason = "Cal-report QMI path returned an error or nonzero cal-report rc"
        passed = True
    elif hit(tail, "wlfw_cal_report_return") > 0:
        label = "post-bdf-tail-cal-success-no-fw-ready"
        reason = "WLFW cap, BDF, and cal-report all returned success, but no FW-ready/status/version/wlan0 cascade followed"
        passed = True
    elif hit(tail, "dms_service_request_cond_wait") > 0 and hit(tail, "dms_service_request_send_ret") == 0:
        label = "post-bdf-tail-dms-waits-fw-state"
        reason = "DMS service request is waiting for the WLFW state bit before sending MAC/address data"
        passed = True
    elif hit(tail, "dms_service_request_send_ret") > 0 and (not is_zero(str(post.get("dms_req_send_rc", ""))) or not is_zero(str(post.get("dms_req_qmi_result", "")))):
        label = "post-bdf-tail-dms-request-error"
        reason = "DMS service request sent but returned a nonzero send/result value"
        passed = True
    elif hit(tail, "wlan_send_status_entry") > 0 and hit(tail, "wlan_send_status_send_ret") == 0:
        label = "post-bdf-tail-status-send-blocked"
        reason = "WLAN status helper entered but status QMI send did not return"
        passed = True
    elif hit(tail, "wlan_send_status_return") > 0 and (not is_zero(str(post.get("status_send_rc", ""))) or not is_zero(str(post.get("status_qmi_result", ""))) or not is_zero(str(post.get("status_return_rc", "")))):
        label = "post-bdf-tail-status-error"
        reason = "WLAN status QMI path returned a nonzero value"
        passed = True
    elif hit(tail, "wlan_send_version_not_found") > 0 and hit(tail, "wlan_send_version_open_success") == 0:
        label = "post-bdf-tail-version-file-not-found"
        reason = "WLAN version helper did not open either firmware-version source file"
        passed = True
    elif hit(tail, "wlan_send_version_return") > 0 and (not is_zero(str(post.get("version_send_rc", ""))) or not is_zero(str(post.get("version_qmi_result", ""))) or not is_zero(str(post.get("version_return_rc", "")))):
        label = "post-bdf-tail-version-error"
        reason = "WLAN version QMI path returned a nonzero value"
        passed = True
    else:
        label = "post-bdf-tail-no-fw-ready-after-tail"
        reason = "Post-BDF tail probes did not expose a local error, but FW-ready/wlan0 still did not appear"
        passed = True
    return {
        **base,
        "label": label,
        "decision": f"v2007-{label}-rollback-{'pass' if passed else 'blocked'}",
        "pass": passed,
        "reason": reason,
        "helper_completion_ok": bool(helper.get("ok")),
        "readwrite_bridge_ok": bool(readwrite.get("ok")),
        "rfs_bridge_ok": bool(bridge.get("ok")),
        "route_ok": route_ok,
    }


def event_rows(events: dict[str, dict[str, str]]) -> list[list[str]]:
    return prev2005.event_rows(events)


def render_report(manifest: dict[str, Any]) -> str:
    details = manifest["details"]
    classification = manifest["classification"]
    cascade = details["cascade"]
    post = details["post_bdf_tail"]
    matrix_rows = [
        ["label", classification["label"], classification["reason"]],
        ["helper", classification.get("helper_completion_ok"), details["helper_completion"]["result_file_version"]],
        ["route", classification.get("route_ok"), f"service74={details['service74']} service180={details['service180']} pm_open={details['pm_open_subsys_modem']} holder={details['holder_opened']}"],
        ["bridges", "", f"readonly={classification.get('rfs_bridge_ok')} readwrite={classification.get('readwrite_bridge_ok')}"],
        ["cascade", "", f"wlan_pd={cascade['wlan_pd_up']} icnss_qmi={cascade['icnss_qmi_connected']} wlfw69={cascade['wlfw69']} bdf={cascade['bdf']} fw_ready={cascade['fw_ready']} wlan0={cascade['wlan0']}"],
        ["firmware", "", f"requested_any={cascade['requested_any']} wlanmdsp_tftp={cascade['wlanmdsp_tftp']} pd_load={cascade['pd_load']}"],
        ["cap_bdf", "", f"cap_return_rc={post['cap_return_rc']} bdf_send_rc={post['bdf_send_rc']} bdf_result={post['bdf_qmi_result']} bdf_return_rc={post['bdf_return_rc']}"],
        ["cal", "", f"send_rc={post['cal_send_rc']} qmi_result={post['cal_qmi_result']} qmi_error={post['cal_qmi_error']} return_rc={post['cal_return_rc']}"],
        ["dms", "", f"addr_result={post['dms_addr_qmi_result']} addr_rc={post['dms_addr_return_rc']} req_init={post['dms_req_init_rc']} req_send={post['dms_req_send_rc']} req_result={post['dms_req_qmi_result']}"],
        ["status_version", "", f"status_send={post['status_send_rc']} status_ret={post['status_return_rc']} version_send={post['version_send_rc']} version_ret={post['version_return_rc']}"],
    ]
    step_lines = [
        f"- `{step['name']}` rc `{step['rc']}` ok `{step['ok']}` evidence `{step['file']}`"
        for step in manifest["steps"]
    ]
    return "\n".join([
        "# Native Init V2007 Post-BDF Tail Handoff",
        "",
        "## Summary",
        "",
        "- Cycle: `V2007`",
        f"- Decision: `{manifest['decision']}`",
        f"- Label: `{manifest['label']}`",
        f"- Pass: `{manifest['pass']}`",
        f"- Reason: {manifest['reason']}",
        f"- Evidence: `{manifest['out_dir']}`",
        f"- Inner handoff: `{manifest['handoff_manifest']}`",
        "",
        "## Matrix",
        "",
        prev1998.prev1992.prev.markdown_table(["area", "value", "detail"], [[str(cell) for cell in row] for row in matrix_rows]),
        "",
        "## Core WLFW Events",
        "",
        prev1998.prev1992.prev.markdown_table(["event", "hits", "fetch", "first"], event_rows(post["core_events"])),
        "",
        "## Capability Events",
        "",
        prev1998.prev1992.prev.markdown_table(["event", "hits", "fetch", "first"], event_rows(post["cap_events"])),
        "",
        "## BDF Events",
        "",
        prev1998.prev1992.prev.markdown_table(["event", "hits", "fetch", "first"], event_rows(post["bdf_events"])),
        "",
        "## Tail Events",
        "",
        prev1998.prev1992.prev.markdown_table(["event", "hits", "fetch", "first"], event_rows(post["tail_events"])),
        "",
        "## Interpretation",
        "",
        "- V2007 preserves the V2005 route and narrows the post-BDF tail: cal-report, DMS MAC/address, WLAN status, and WLAN version paths.",
        "- `wlfw_cal_report_return rc=0x0` moves the blocker past WLFW cap/BDF/cal-report; the remaining missing edge is the firmware-ready/status/version indication cascade.",
        "- `dms_get_wlan_address` fails here, but Android-good traces also show `Send DMS get mac address failed` before successful `wlan0`; it is retained as context, not selected as the blocker.",
        "- Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping remain blocked until `wlan0` exists.",
        "",
        "## Steps",
        "",
        *step_lines,
        "",
        "## Safety",
        "",
        "- No Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping was used.",
        "- No rild/cnss/pm-service strace, boot-time QRTR matrix, service-locator probe, service-notifier listener, active QRTR readback, QMI payload send, or tftp_server ptrace was run.",
        "- No direct `/dev/subsys_esoc0` open/control, forced RC1/case, PMIC/GPIO/GDSC/regulator, PCI rescan, platform bind/unbind, fake ONLINE, or eSoC notify/BOOT_DONE action was used.",
        "- Mutation scope: `/cache` one-shot clean-DSP flag, V2006 test-boot flash-handoff, namespace-local RFS tmpfs/symlink bridges, and rollback to `stage3/boot_linux_v724.img` with selftest fail=0.",
        "",
    ])


def patch_prev_module() -> None:
    prev2000.CYCLE = CYCLE
    prev2000.OUT_DIR = OUT_DIR
    prev2000.HANDOFF_DIR = HANDOFF_DIR
    prev2000.HANDOFF_REPORT = HANDOFF_REPORT
    prev2000.REPORT_PATH = REPORT_PATH
    prev1998.CYCLE = CYCLE
    prev1998.OUT_DIR = OUT_DIR
    prev1998.HANDOFF_DIR = HANDOFF_DIR
    prev1998.HANDOFF_REPORT = HANDOFF_REPORT
    prev1998.REPORT_PATH = REPORT_PATH
    prev1998.V1997_OUT = V2006_OUT
    prev1998.V1997_INIT = V2006_INIT
    prev1998.V1997_BOOT = V2006_BOOT
    prev1998.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev1998.TEST_EXPECT_VERSION = TEST_EXPECT_VERSION
    prev1998.TEST_LOG_PATH = TEST_LOG_PATH
    prev1998.TEST_SUMMARY_PATH = TEST_SUMMARY_PATH
    prev1998.TEST_HELPER_RESULT_PATH = TEST_HELPER_RESULT_PATH
    prev1998.artifact_hook_check = artifact_hook_check
    prev1998.collect_details = collect_details
    prev1998.classify = classify
    prev1998.render_report = render_report
    ORIGINAL_PATCH_PREV_MODULE()


def main(argv: list[str] | None = None) -> int:
    prev1998.patch_prev_module = patch_prev_module
    return prev1998.main(argv)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

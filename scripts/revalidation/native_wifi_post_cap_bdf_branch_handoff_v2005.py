#!/usr/bin/env python3
"""V2005 rollbackable handoff for post-cap BDF branch probes."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

import native_wifi_downstream_cascade_handoff_v2000 as prev2000


CYCLE = "V2005"
OUT_DIR = prev2000.prev1998.prev1992.prev.repo_path("tmp/wifi/v2005-post-cap-bdf-branch-handoff")
HANDOFF_DIR = OUT_DIR / "v2004-handoff"
HANDOFF_REPORT = OUT_DIR / "v2004-handoff-report.md"
REPORT_PATH = prev2000.prev1998.prev1992.prev.repo_path(
    "docs/reports/NATIVE_INIT_V2005_POST_CAP_BDF_BRANCH_HANDOFF_2026-06-04.md"
)
V2004_OUT = prev2000.prev1998.prev1992.prev.repo_path("tmp/wifi/v2004-post-cap-bdf-branch-test-boot")
V2004_INIT = V2004_OUT / "init_v2004_post_cap_bdf_branch"
V2004_BOOT = V2004_OUT / "boot_linux_v2004_post_cap_bdf_branch.img"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v2004/dev/__properties__"
TEST_EXPECT_VERSION = "A90 Linux init 0.9.184 (v2004-post-cap-bdf-branch)"
TEST_LOG_PATH = "/cache/native-init-wifi-test-boot-v2004.log"
TEST_SUMMARY_PATH = "/cache/native-init-wifi-test-boot-v2004.summary"
TEST_HELPER_RESULT_PATH = "/cache/native-init-wifi-test-boot-v2004-helper.result"

prev1998 = prev2000.prev1998
ORIGINAL_PATCH_PREV_MODULE = prev2000.ORIGINAL_PATCH_PREV_MODULE
ORIGINAL_COLLECT_DETAILS = prev2000.ORIGINAL_COLLECT_DETAILS

CORE_EVENTS = (
    "wlfw_service_request",
    "wlfw_client_init_instance_retcheck",
    "wlfw_ind_register_qmi",
    "wlfw_fw_mem_cond_wait",
    "wlfw_cap_qmi",
)

CAP_EVENTS = (
    "wlfw_fw_mem_wait_return",
    "wlfw_cap_send_ret",
    "wlfw_cap_send_or_result_error_branch",
    "wlfw_cap_invalid_0x77_branch",
    "wlfw_cap_success_branch",
    "wlfw_cap_rsp_result_error_branch",
    "wlfw_cap_return",
)

BDF_EVENTS = (
    "wlfw_bdf_entry",
    "wlfw_bdf_named_path_ready",
    "wlfw_bdf_open_success",
    "wlfw_bdf_not_found",
    "wlfw_bdf_read_complete",
    "wlfw_bdf_send_call",
    "wlfw_bdf_send_ret",
    "wlfw_bdf_send_error_branch",
    "wlfw_bdf_result_log",
    "wlfw_bdf_return",
)


def rel(path: Path) -> str:
    return prev2000.rel(path)


def intish(value: object) -> int:
    return prev1998.prev1992.prev.intish(value)


def event(fields: dict[str, str], name: str) -> dict[str, str]:
    prefix = f"wlan_pd_cnss_nonlog_control_flow.uprobe.{name}."
    return {
        "name": name,
        "registered": fields.get(prefix + "registered", ""),
        "enabled": fields.get(prefix + "enabled", ""),
        "hit_count": fields.get(prefix + "hit_count", ""),
        "first_hit_line": fields.get(prefix + "first_hit_line", ""),
        "fetch_args": fields.get(prefix + "fetch_args", ""),
        "sample_line_0": fields.get(prefix + "sample_line_0", ""),
        "sample_line_1": fields.get(prefix + "sample_line_1", ""),
    }


def hit(events: dict[str, dict[str, str]], name: str) -> int:
    return intish(events.get(name, {}).get("hit_count"))


def first_value(line: str, key: str) -> str:
    match = re.search(rf"\b{re.escape(key)}=(0x[0-9a-fA-F]+|-?[0-9]+)", line)
    return match.group(1) if match else ""


def first_event_value(data: dict[str, str], *keys: str) -> str:
    line = data.get("first_hit_line", "")
    for key in keys:
        value = first_value(line, key)
        if value:
            return value
    return ""


def is_zero(value: str) -> bool:
    return value in {"", "0", "0x0"}


def artifact_hook_check() -> dict[str, Any]:
    init_required = (
        "native-init-sibling-fwssctl-v641",
        "A90v641: sibling fwssctl proof armed",
        "wifi-v641-fwssctl",
        "A90v2004",
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
        "a90_android_execns_probe v371",
        "wlfw_cap_success_branch",
        "wlfw_cap_return",
        "wlfw_bdf_entry",
        "wlfw_bdf_named_path_ready",
        "wlfw_bdf_open_success",
        "wlfw_bdf_not_found",
        "wlfw_bdf_send_ret",
        "wlfw_bdf_send_error_branch",
        "wlfw_bdf_return",
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
    for path, required in ((V2004_INIT, init_required), (V2004_BOOT, boot_required)):
        forbidden_tokens = init_forbidden if path == V2004_INIT else boot_forbidden
        if not path.exists():
            checks[rel(path)] = {"exists": False, "ok": False, "missing": list(required), "forbidden": []}
            continue
        data = path.read_bytes()
        missing = [token for token in required if token.encode() not in data]
        forbidden = [token for token in forbidden_tokens if token.encode() in data]
        checks[rel(path)] = {"exists": True, "ok": not missing and not forbidden, "missing": missing, "forbidden": forbidden}
    return checks


def collect_post_cap(fields: dict[str, str]) -> dict[str, Any]:
    core_events = {name: event(fields, name) for name in CORE_EVENTS}
    cap_events = {name: event(fields, name) for name in CAP_EVENTS}
    bdf_events = {name: event(fields, name) for name in BDF_EVENTS}
    result_log = bdf_events["wlfw_bdf_result_log"]
    return {
        "core_events": core_events,
        "cap_events": cap_events,
        "bdf_events": bdf_events,
        "nonlog_label": fields.get("wlan_pd_cnss_nonlog_control_flow.label", ""),
        "cap_return_rc": first_event_value(cap_events["wlfw_cap_return"], "rc"),
        "cap_send_rc": first_event_value(cap_events["wlfw_cap_send_ret"], "send_rc"),
        "bdf_first_type": first_event_value(bdf_events["wlfw_bdf_entry"], "bdf_type"),
        "bdf_send_rc": first_event_value(bdf_events["wlfw_bdf_send_ret"], "send_rc"),
        "bdf_error_send_rc": first_event_value(bdf_events["wlfw_bdf_send_error_branch"], "send_rc"),
        "bdf_result_type": first_event_value(result_log, "bdf_type"),
        "bdf_qmi_result": first_event_value(result_log, "qmi_result"),
        "bdf_qmi_error": first_event_value(result_log, "qmi_error"),
        "bdf_return_rc": first_event_value(bdf_events["wlfw_bdf_return"], "rc"),
    }


def collect_details(handoff: dict[str, Any]) -> dict[str, Any]:
    details = ORIGINAL_COLLECT_DETAILS(handoff)
    fields = prev1998.parse_fields(prev1998.read_helper_text())
    helper = details.get("helper_completion") if isinstance(details.get("helper_completion"), dict) else {}
    if helper:
        helper["version_ok"] = helper.get("result_file_version") == "a90_android_execns_probe v371"
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
    details["post_cap_bdf"] = collect_post_cap(fields)
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
    post = details.get("post_cap_bdf") if isinstance(details.get("post_cap_bdf"), dict) else {}
    cap = post.get("cap_events") if isinstance(post.get("cap_events"), dict) else {}
    bdf = post.get("bdf_events") if isinstance(post.get("bdf_events"), dict) else {}
    core = post.get("core_events") if isinstance(post.get("core_events"), dict) else {}
    route_ok = (
        bool(base.get("hook_ok"))
        and bool(base.get("prearm_ok"))
        and bool(base.get("rollback_ok"))
        and bool(base.get("light_ok"))
        and bool(base.get("combined"))
        and bool(bridge.get("ok"))
        and bool(helper.get("ok"))
        and bool(readwrite.get("ok"))
    )
    bdf_return_rc = str(post.get("bdf_return_rc", ""))
    bdf_send_rc = str(post.get("bdf_send_rc", ""))
    bdf_qmi_result = str(post.get("bdf_qmi_result", ""))
    if not route_ok:
        label = "post-cap-bdf-route-regression"
        reason = "V2004 did not preserve rollback, light observer, bridge, PM/CNSS, or helper prerequisites"
        passed = False
    elif int(cascade.get("wlan0", 0)) > 0:
        label = "post-cap-bdf-wlan0-progress"
        reason = "V2004 reached wlan0; stop before credentials/scan/connect until a dedicated gated unit"
        passed = True
    elif int(cascade.get("fw_ready", 0)) > 0 or int(cascade.get("bdf", 0)) > 0:
        label = "post-cap-bdf-visible-downstream-progress"
        reason = "V2004 crossed the post-cap branch into visible BDF/FW-ready progress"
        passed = True
    elif hit(core, "wlfw_cap_qmi") == 0 or hit(cap, "wlfw_cap_success_branch") == 0:
        label = "post-cap-bdf-cap-regression"
        reason = "V2004 did not reproduce V2003's successful WLFW capability branch"
        passed = False
    elif hit(bdf, "wlfw_bdf_entry") == 0:
        label = "post-cap-bdf-not-called"
        reason = "WLFW capability returned success, but `wlfw_send_bdf_download_req` was never entered"
        passed = True
    elif hit(bdf, "wlfw_bdf_not_found") > 0 and hit(bdf, "wlfw_bdf_open_success") == 0:
        label = "post-cap-bdf-file-not-found"
        reason = "BDF helper ran but did not open a candidate BDF/REGDB file"
        passed = True
    elif hit(bdf, "wlfw_bdf_open_success") > 0 and hit(bdf, "wlfw_bdf_send_call") == 0:
        label = "post-cap-bdf-opened-no-send"
        reason = "BDF helper opened a firmware file but did not reach the WLFW BDF QMI send"
        passed = True
    elif hit(bdf, "wlfw_bdf_send_call") > 0 and hit(bdf, "wlfw_bdf_send_ret") == 0:
        label = "post-cap-bdf-send-blocked"
        reason = "BDF download QMI send was entered but did not return in the long window"
        passed = True
    elif hit(bdf, "wlfw_bdf_send_error_branch") > 0 or not is_zero(bdf_send_rc):
        label = "post-cap-bdf-send-error"
        reason = "BDF download QMI send returned through the send-error branch"
        passed = True
    elif hit(bdf, "wlfw_bdf_result_log") > 0 and not is_zero(bdf_qmi_result):
        label = "post-cap-bdf-qmi-result-error"
        reason = "BDF download QMI response carried a nonzero result"
        passed = True
    elif hit(bdf, "wlfw_bdf_return") > 0 and not is_zero(bdf_return_rc):
        label = "post-cap-bdf-return-error"
        reason = "BDF helper returned a nonzero rc after reaching the BDF path"
        passed = True
    elif hit(bdf, "wlfw_bdf_return") > 0:
        label = "post-cap-bdf-success-no-visible-downstream"
        reason = "BDF helper returned success, but no visible BDF/FW-ready/wlan0 cascade followed"
        passed = True
    else:
        label = "post-cap-bdf-branch-incomplete"
        reason = "BDF helper advanced but the discriminator did not capture a final success or error path"
        passed = False
    return {
        **base,
        "label": label,
        "decision": f"v2005-{label}-rollback-{'pass' if passed else 'blocked'}",
        "pass": passed,
        "reason": reason,
        "helper_completion_ok": bool(helper.get("ok")),
        "readwrite_bridge_ok": bool(readwrite.get("ok")),
        "rfs_bridge_ok": bool(bridge.get("ok")),
        "route_ok": route_ok,
    }


def event_rows(events: dict[str, dict[str, str]]) -> list[list[str]]:
    return [
        [name, data.get("hit_count", ""), data.get("fetch_args", ""), data.get("first_hit_line", "")]
        for name, data in events.items()
    ]


def render_report(manifest: dict[str, Any]) -> str:
    details = manifest["details"]
    classification = manifest["classification"]
    cascade = details["cascade"]
    post = details["post_cap_bdf"]
    matrix_rows = [
        ["label", classification["label"], classification["reason"]],
        ["helper", classification.get("helper_completion_ok"), details["helper_completion"]["result_file_version"]],
        ["route", classification.get("route_ok"), f"service74={details['service74']} service180={details['service180']} pm_open={details['pm_open_subsys_modem']} holder={details['holder_opened']}"],
        ["bridges", "", f"readonly={classification.get('rfs_bridge_ok')} readwrite={classification.get('readwrite_bridge_ok')}"],
        ["cascade", "", f"wlan_pd={cascade['wlan_pd_up']} icnss_qmi={cascade['icnss_qmi_connected']} wlfw69={cascade['wlfw69']} bdf={cascade['bdf']} fw_ready={cascade['fw_ready']} wlan0={cascade['wlan0']}"],
        ["firmware", "", f"requested_any={cascade['requested_any']} wlanmdsp_tftp={cascade['wlanmdsp_tftp']} pd_load={cascade['pd_load']}"],
        ["cap_rc", "", f"cap_send_rc={post['cap_send_rc']} cap_return_rc={post['cap_return_rc']}"],
        ["bdf_rc", "", f"type={post['bdf_first_type']} send_rc={post['bdf_send_rc']} qmi_result={post['bdf_qmi_result']} qmi_error={post['bdf_qmi_error']} return_rc={post['bdf_return_rc']}"],
    ]
    step_lines = [
        f"- `{step['name']}` rc `{step['rc']}` ok `{step['ok']}` evidence `{step['file']}`"
        for step in manifest["steps"]
    ]
    return "\n".join([
        "# Native Init V2005 Post-Cap BDF Branch Handoff",
        "",
        "## Summary",
        "",
        "- Cycle: `V2005`",
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
        "## Interpretation",
        "",
        "- `wlfw_bdf_entry`, file open/read, BDF QMI send, QMI result, and BDF return are all captured before the stall when the label is `post-cap-bdf-success-no-visible-downstream`.",
        "- That label moves the blocker past BDF file presence/serve/open and past the WLFW BDF download request itself; the next gate is the post-BDF firmware-ready or host-driver notification path.",
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
        "- Mutation scope: `/cache` one-shot clean-DSP flag, V2004 test-boot flash-handoff, namespace-local RFS tmpfs/symlink bridges, and rollback to `stage3/boot_linux_v724.img` with selftest fail=0.",
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
    prev1998.V1997_OUT = V2004_OUT
    prev1998.V1997_INIT = V2004_INIT
    prev1998.V1997_BOOT = V2004_BOOT
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

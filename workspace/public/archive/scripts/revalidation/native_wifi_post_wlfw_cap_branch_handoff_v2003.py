#!/usr/bin/env python3
"""V2003 rollbackable handoff for post-WLFW-cap branch probes."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

import native_wifi_downstream_cascade_handoff_v2000 as prev2000


CYCLE = "V2003"
OUT_DIR = prev2000.prev1998.prev1992.prev.repo_path("tmp/wifi/v2003-post-wlfw-cap-branch-handoff")
HANDOFF_DIR = OUT_DIR / "v2002-handoff"
HANDOFF_REPORT = OUT_DIR / "v2002-handoff-report.md"
REPORT_PATH = prev2000.prev1998.prev1992.prev.repo_path(
    "docs/reports/NATIVE_INIT_V2003_POST_WLFW_CAP_BRANCH_HANDOFF_2026-06-04.md"
)
V2002_OUT = prev2000.prev1998.prev1992.prev.repo_path("tmp/wifi/v2002-post-wlfw-cap-branch-test-boot")
V2002_INIT = V2002_OUT / "init_v2002_post_wlfw_cap_branch"
V2002_BOOT = V2002_OUT / "boot_linux_v2002_post_wlfw_cap_branch.img"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v2002/dev/__properties__"
TEST_EXPECT_VERSION = "A90 Linux init 0.9.183 (v2002-post-wlfw-cap-branch)"
TEST_LOG_PATH = "/cache/native-init-wifi-test-boot-v2002.log"
TEST_SUMMARY_PATH = "/cache/native-init-wifi-test-boot-v2002.summary"
TEST_HELPER_RESULT_PATH = "/cache/native-init-wifi-test-boot-v2002-helper.result"

prev1998 = prev2000.prev1998
ORIGINAL_PATCH_PREV_MODULE = prev2000.ORIGINAL_PATCH_PREV_MODULE
ORIGINAL_COLLECT_DETAILS = prev2000.ORIGINAL_COLLECT_DETAILS

BRANCH_EVENTS = (
    "wlfw_fw_mem_wait_return",
    "wlfw_cap_send_ret",
    "wlfw_cap_send_or_result_error_branch",
    "wlfw_cap_invalid_0x77_branch",
    "wlfw_cap_success_branch",
    "wlfw_cap_rsp_result_error_branch",
    "wlfw_cap_return",
)

CORE_EVENTS = (
    "wlfw_service_request",
    "wlfw_client_init_instance_retcheck",
    "wlfw_ind_register_qmi",
    "wlfw_fw_mem_cond_wait",
    "wlfw_cap_qmi",
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


def rc_value(data: dict[str, str]) -> str:
    line = data.get("first_hit_line", "")
    return first_value(line, "rc") or first_value(line, "send_rc") or first_value(line, "qmi_result")


def artifact_hook_check() -> dict[str, Any]:
    init_required = (
        "native-init-sibling-fwssctl-v641",
        "A90v641: sibling fwssctl proof armed",
        "wifi-v641-fwssctl",
        "A90v2002",
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
        "a90_android_execns_probe v370",
        "wlfw_fw_mem_wait_return",
        "wlfw_cap_send_ret",
        "wlfw_cap_send_or_result_error_branch",
        "wlfw_cap_invalid_0x77_branch",
        "wlfw_cap_success_branch",
        "wlfw_cap_rsp_result_error_branch",
        "wlfw_cap_return",
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
    for path, required in ((V2002_INIT, init_required), (V2002_BOOT, boot_required)):
        forbidden_tokens = init_forbidden if path == V2002_INIT else boot_forbidden
        if not path.exists():
            checks[rel(path)] = {"exists": False, "ok": False, "missing": list(required), "forbidden": []}
            continue
        data = path.read_bytes()
        missing = [token for token in required if token.encode() not in data]
        forbidden = [token for token in forbidden_tokens if token.encode() in data]
        checks[rel(path)] = {"exists": True, "ok": not missing and not forbidden, "missing": missing, "forbidden": forbidden}
    return checks


def collect_branch(fields: dict[str, str]) -> dict[str, Any]:
    branch_events = {name: event(fields, name) for name in BRANCH_EVENTS}
    core_events = {name: event(fields, name) for name in CORE_EVENTS}
    return {
        "core_events": core_events,
        "branch_events": branch_events,
        "nonlog_label": fields.get("wlan_pd_cnss_nonlog_control_flow.label", ""),
        "cap_return_rc": rc_value(branch_events["wlfw_cap_return"]),
        "cap_send_rc": rc_value(branch_events["wlfw_cap_send_ret"]),
        "cap_rsp_error": rc_value(branch_events["wlfw_cap_rsp_result_error_branch"]),
    }


def collect_details(handoff: dict[str, Any]) -> dict[str, Any]:
    details = ORIGINAL_COLLECT_DETAILS(handoff)
    fields = prev1998.parse_fields(prev1998.read_helper_text())
    helper = details.get("helper_completion") if isinstance(details.get("helper_completion"), dict) else {}
    if helper:
        helper["version_ok"] = helper.get("result_file_version") == "a90_android_execns_probe v370"
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
    details["post_cap_branch"] = collect_branch(fields)
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
    branch = details.get("post_cap_branch") if isinstance(details.get("post_cap_branch"), dict) else {}
    events = branch.get("branch_events") if isinstance(branch.get("branch_events"), dict) else {}
    core = branch.get("core_events") if isinstance(branch.get("core_events"), dict) else {}
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
    if not route_ok:
        label = "post-wlfw-cap-branch-route-regression"
        reason = "V2002 did not preserve rollback, light observer, bridge, PM/CNSS, or helper prerequisites"
        passed = False
    elif int(cascade.get("wlan0", 0)) > 0:
        label = "post-wlfw-cap-branch-wlan0-progress"
        reason = "V2002 reached wlan0; stop before credentials/scan/connect until a dedicated gated unit"
        passed = True
    elif int(cascade.get("fw_ready", 0)) > 0 or int(cascade.get("bdf", 0)) > 0:
        label = "post-wlfw-cap-branch-bdf-fw-progress"
        reason = "V2002 crossed the post-cap branch into BDF/FW-ready progress"
        passed = True
    elif hit(core, "wlfw_cap_qmi") == 0:
        label = "post-wlfw-cap-branch-cap-not-reached"
        reason = "V2002 reproduced the route but did not reach the WLFW capability-send call"
        passed = False
    elif hit(events, "wlfw_cap_send_ret") == 0:
        label = "post-wlfw-cap-send-blocked"
        reason = "WLFW capability qmi_client_send_msg_sync was entered but did not return in the long window"
        passed = True
    elif hit(events, "wlfw_cap_send_or_result_error_branch") > 0:
        label = "post-wlfw-cap-send-or-result-error"
        reason = "WLFW capability send returned into the nonzero send/result error branch"
        passed = True
    elif hit(events, "wlfw_cap_invalid_0x77_branch") > 0:
        label = "post-wlfw-cap-invalid-0x77"
        reason = "WLFW capability response hit the 0x77 special failure branch"
        passed = True
    elif hit(events, "wlfw_cap_rsp_result_error_branch") > 0:
        label = "post-wlfw-cap-response-result-error"
        reason = "WLFW capability response carried a nonzero QMI result"
        passed = True
    elif hit(events, "wlfw_cap_success_branch") > 0 and hit(events, "wlfw_cap_return") > 0:
        label = "post-wlfw-cap-success-no-downstream"
        reason = "WLFW capability QMI returned success but no BDF/FW-ready/wlan0 or wlanmdsp request/load followed"
        passed = True
    else:
        label = "post-wlfw-cap-branch-incomplete"
        reason = "WLFW capability send returned but the branch discriminator did not capture a final success or error path"
        passed = False
    return {
        **base,
        "label": label,
        "decision": f"v2003-{label}-rollback-{'pass' if passed else 'blocked'}",
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
    branch = details["post_cap_branch"]
    matrix_rows = [
        ["label", classification["label"], classification["reason"]],
        ["helper", classification.get("helper_completion_ok"), details["helper_completion"]["result_file_version"]],
        ["route", classification.get("route_ok"), f"service74={details['service74']} service180={details['service180']} pm_open={details['pm_open_subsys_modem']} holder={details['holder_opened']}"],
        ["bridges", "", f"readonly={classification.get('rfs_bridge_ok')} readwrite={classification.get('readwrite_bridge_ok')}"],
        ["cascade", "", f"wlan_pd={cascade['wlan_pd_up']} icnss_qmi={cascade['icnss_qmi_connected']} wlfw69={cascade['wlfw69']} bdf={cascade['bdf']} fw_ready={cascade['fw_ready']} wlan0={cascade['wlan0']}"],
        ["firmware", "", f"requested_any={cascade['requested_any']} wlanmdsp_tftp={cascade['wlanmdsp_tftp']} pd_load={cascade['pd_load']}"],
        ["branch_rc", "", f"cap_send_rc={branch['cap_send_rc']} cap_rsp_error={branch['cap_rsp_error']} cap_return_rc={branch['cap_return_rc']}"],
    ]
    step_lines = [
        f"- `{step['name']}` rc `{step['rc']}` ok `{step['ok']}` evidence `{step['file']}`"
        for step in manifest["steps"]
    ]
    return "\n".join([
        "# Native Init V2003 Post-WLFW-Cap Branch Handoff",
        "",
        "## Summary",
        "",
        "- Cycle: `V2003`",
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
        prev1998.prev1992.prev.markdown_table(["event", "hits", "fetch", "first"], event_rows(branch["core_events"])),
        "",
        "## Branch Events",
        "",
        prev1998.prev1992.prev.markdown_table(["event", "hits", "fetch", "first"], event_rows(branch["branch_events"])),
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
        "- Mutation scope: `/cache` one-shot clean-DSP flag, V2002 test-boot flash-handoff, namespace-local RFS tmpfs/symlink bridges, and rollback to `stage3/boot_linux_v724.img` with selftest fail=0.",
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
    prev1998.V1997_OUT = V2002_OUT
    prev1998.V1997_INIT = V2002_INIT
    prev1998.V1997_BOOT = V2002_BOOT
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

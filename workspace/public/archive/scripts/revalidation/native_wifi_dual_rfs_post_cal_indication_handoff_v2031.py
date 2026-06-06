#!/usr/bin/env python3
"""V2031 rollbackable handoff for dual RFS post-cal WLFW indication probes."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import native_wifi_post_bdf_tail_handoff_v2007 as prev2007


CYCLE = "V2031"
OUT_DIR = prev2007.prev2000.prev1998.prev1992.prev.repo_path(
    "tmp/wifi/v2031-dual-rfs-post-cal-indication-handoff"
)
HANDOFF_DIR = OUT_DIR / "v2030-handoff"
HANDOFF_REPORT = OUT_DIR / "v2030-handoff-report.md"
REPORT_PATH = prev2007.prev2000.prev1998.prev1992.prev.repo_path(
    "docs/reports/NATIVE_INIT_V2031_DUAL_RFS_POST_CAL_INDICATION_HANDOFF_2026-06-04.md"
)
V2030_OUT = prev2007.prev2000.prev1998.prev1992.prev.repo_path(
    "tmp/wifi/v2030-dual-rfs-post-cal-indication-test-boot"
)
V2030_INIT = V2030_OUT / "init_v2030_dual_rfs_post_cal_indication"
V2030_BOOT = V2030_OUT / "boot_linux_v2030_dual_rfs_post_cal_indication.img"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v2030/dev/__properties__"
TEST_EXPECT_VERSION = "A90 Linux init 0.9.197 (v2030-dual-rfs-post-cal-indication)"
TEST_LOG_PATH = "/cache/native-init-wifi-test-boot-v2030.log"
TEST_SUMMARY_PATH = "/cache/native-init-wifi-test-boot-v2030.summary"
TEST_HELPER_RESULT_PATH = "/cache/native-init-wifi-test-boot-v2030-helper.result"
EXPECTED_HELPER_VERSION = "a90_android_execns_probe v382"

prev2000 = prev2007.prev2000
prev1998 = prev2007.prev1998
ORIGINAL_PATCH_PREV_MODULE = prev2007.ORIGINAL_PATCH_PREV_MODULE
ORIGINAL_COLLECT_DETAILS = prev2007.ORIGINAL_COLLECT_DETAILS

IND_EVENTS = (
    "wlfw_worker_second_bdf_branch",
    "wlfw_worker_cal_only_call",
    "wlfw_worker_cal_only_retcheck",
    "wlfw_worker_done_signal",
    "wlfw_worker_post_done_wait",
    "wlfw_worker_handle_ind_call",
    "wlfw_qmi_ind_cb_entry",
    "wlfw_qmi_ind_msg_unknown",
    "wlfw_qmi_ind_decode_0x28_ok",
    "wlfw_qmi_ind_decode_0x2a_ok",
    "wlfw_qmi_ind_decode_0x41_ok",
    "wlfw_qmi_ind_fw_mem_flag",
    "wlfw_qmi_ind_msa_flag",
    "wlfw_qmi_ind_queue_link",
    "wlfw_qmi_ind_cond_signal",
    "wlfw_handle_ind_entry",
    "wlfw_handle_ind_type",
    "wlfw_handle_ind_type_0x28",
    "wlfw_handle_ind_type_0x2a",
    "wlfw_handle_ind_type_0x41",
)


def rel(path: Path) -> str:
    return prev2007.rel(path)


def intish(value: object) -> int:
    return prev1998.prev1992.prev.intish(value)


def event(fields: dict[str, str], name: str) -> dict[str, str]:
    return prev2007.event(fields, name)


def hit(events: dict[str, dict[str, str]], name: str) -> int:
    return prev2007.hit(events, name)


def first_event_value(data: dict[str, str], *keys: str) -> str:
    return prev2007.first_event_value(data, *keys)


def is_zero(value: str) -> bool:
    return prev2007.is_zero(value)


def artifact_hook_check() -> dict[str, Any]:
    init_required = (
        "native-init-sibling-fwssctl-v641",
        "A90v641: sibling fwssctl proof armed",
        "wifi-v641-fwssctl",
        "A90v2030",
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
        EXPECTED_HELPER_VERSION,
        "wlan_pd_firmware_serve_gate.rfs_bridge",
        "android_parity=firmware_mnt_probe_present_firmware_fallback_present",
        "probe.absolute=/vendor/rfs/msm/mpss/readonly/vendor/firmware_mnt/image/wlanmdsp.mbn",
        "fallback.absolute=/vendor/rfs/msm/mpss/readonly/vendor/firmware/wlanmdsp.mbn",
        "server_check.absolute=/vendor/rfs/msm/mpss/readwrite/server_check.txt",
        "readwrite.tmpfs_requested=1",
        "wifi_companion_start.cnss_daemon_argv=/vendor/bin/cnss-daemon -n -l",
        "wlan_pd_icnss_ipc_snapshot",
        "wlfw_cal_report_return",
        "wlfw_worker_cal_only_call",
        "wlfw_worker_done_signal",
        "wlfw_qmi_ind_cb_entry",
        "wlfw_handle_ind_entry",
    )
    boot_forbidden = (
        "wlan_pd_tftp_server_trace.late_attach.begin=1",
        "wifi_companion_start.wlan_pd_producer_tftp_server_syscall_trace.compiled=1",
    )
    checks: dict[str, Any] = {}
    for path, required in ((V2030_INIT, init_required), (V2030_BOOT, boot_required)):
        forbidden_tokens = init_forbidden if path == V2030_INIT else boot_forbidden
        if not path.exists():
            checks[rel(path)] = {
                "exists": False,
                "ok": False,
                "missing": list(required),
                "forbidden": [],
            }
            continue
        data = path.read_bytes()
        missing = [token for token in required if token.encode() not in data]
        forbidden = [token for token in forbidden_tokens if token.encode() in data]
        checks[rel(path)] = {
            "exists": True,
            "ok": not missing and not forbidden,
            "missing": missing,
            "forbidden": forbidden,
        }
    return checks


def patch_bridge_from_fields(details: dict[str, Any], fields: dict[str, str]) -> None:
    trace = details.get("wlanmdsp_trace") if isinstance(details.get("wlanmdsp_trace"), dict) else {}
    bridge = trace.get("rfs_bridge") if isinstance(trace.get("rfs_bridge"), dict) else {}
    bridge.update({
        "android_parity": fields.get("wlan_pd_firmware_serve_gate.rfs_bridge.android_parity", ""),
        "probe_path": fields.get("wlan_pd_firmware_serve_gate.rfs_bridge.probe.host_path", ""),
        "probe_exists": intish(fields.get("wlan_pd_firmware_serve_gate.rfs_bridge.probe.exists")),
        "probe_nonzero": intish(fields.get("wlan_pd_firmware_serve_gate.rfs_bridge.probe.nonzero")),
        "probe_size": fields.get("wlan_pd_firmware_serve_gate.rfs_bridge.probe.size", ""),
        "probe_open_rc": fields.get("wlan_pd_firmware_serve_gate.rfs_bridge.probe.open_rc", ""),
        "probe_open_errno": fields.get("wlan_pd_firmware_serve_gate.rfs_bridge.probe.open_errno", ""),
        "fallback_path": fields.get("wlan_pd_firmware_serve_gate.rfs_bridge.fallback.host_path", ""),
        "fallback_exists": intish(fields.get("wlan_pd_firmware_serve_gate.rfs_bridge.fallback.exists")),
        "fallback_nonzero": intish(fields.get("wlan_pd_firmware_serve_gate.rfs_bridge.fallback.nonzero")),
        "fallback_size": fields.get("wlan_pd_firmware_serve_gate.rfs_bridge.fallback.size", ""),
        "fallback_open_rc": fields.get("wlan_pd_firmware_serve_gate.rfs_bridge.fallback.open_rc", ""),
        "fallback_open_errno": fields.get("wlan_pd_firmware_serve_gate.rfs_bridge.fallback.open_errno", ""),
    })
    bridge["ok"] = (
        bridge.get("android_parity") == "firmware_mnt_probe_present_firmware_fallback_present"
        and bridge.get("probe_exists") == 1
        and bridge.get("probe_nonzero") == 1
        and str(bridge.get("probe_open_rc")) == "0"
        and bridge.get("fallback_exists") == 1
        and bridge.get("fallback_nonzero") == 1
        and str(bridge.get("fallback_open_rc")) == "0"
        and intish(bridge.get("rootfs_namespace_only")) == 1
        and intish(bridge.get("sda29_write")) == 0
    )
    if bridge["ok"]:
        trace["served"] = True
        trace["served_nonzero"] = True
    trace["rfs_bridge"] = bridge
    details["wlanmdsp_trace"] = trace


def collect_post_cal(fields: dict[str, str]) -> dict[str, Any]:
    post_bdf_tail = prev2007.collect_post_bdf_tail(fields)
    ind_events = {name: event(fields, name) for name in IND_EVENTS}
    return {
        **post_bdf_tail,
        "ind_events": ind_events,
        "worker_cal_rc": first_event_value(ind_events["wlfw_worker_cal_only_retcheck"], "rc"),
        "first_ind_msg_id": first_event_value(ind_events["wlfw_qmi_ind_cb_entry"], "msg_id"),
        "first_ind_payload_len": first_event_value(ind_events["wlfw_qmi_ind_cb_entry"], "payload_len"),
        "first_handle_type": first_event_value(ind_events["wlfw_handle_ind_type"], "ind_type"),
        "first_handle_0x28_status": first_event_value(ind_events["wlfw_handle_ind_type_0x28"], "fw_status"),
    }


def collect_details(handoff: dict[str, Any]) -> dict[str, Any]:
    details = ORIGINAL_COLLECT_DETAILS(handoff)
    fields = prev1998.parse_fields(prev1998.read_helper_text())
    helper = details.get("helper_completion") if isinstance(details.get("helper_completion"), dict) else {}
    if helper:
        helper["version_ok"] = helper.get("result_file_version") == EXPECTED_HELPER_VERSION
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
    patch_bridge_from_fields(details, fields)
    details["cascade"] = prev2000.collect_cascade(fields, details)
    details["post_cal_indication"] = collect_post_cal(fields)
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
    post = details.get("post_cal_indication") if isinstance(details.get("post_cal_indication"), dict) else {}
    cap = post.get("cap_events") if isinstance(post.get("cap_events"), dict) else {}
    bdf = post.get("bdf_events") if isinstance(post.get("bdf_events"), dict) else {}
    tail = post.get("tail_events") if isinstance(post.get("tail_events"), dict) else {}
    ind = post.get("ind_events") if isinstance(post.get("ind_events"), dict) else {}
    cap_bdf_cal_success = (
        hit(cap, "wlfw_cap_success_branch") > 0
        and hit(bdf, "wlfw_bdf_return") > 0
        and is_zero(str(post.get("bdf_return_rc", "")))
        and hit(tail, "wlfw_cal_report_return") > 0
        and is_zero(str(post.get("cal_return_rc", "")))
    )
    current_hook = artifact_hook_check()
    current_hook_ok = all(bool(item.get("ok")) for item in current_hook.values())
    lower_route_observed = bool(base.get("lower_route_observed", base.get("combined"))) or cap_bdf_cal_success
    route_ok = (
        current_hook_ok
        and bool(base.get("prearm_ok"))
        and bool(base.get("rollback_ok"))
        and bool(base.get("light_ok"))
        and lower_route_observed
        and bool(cascade.get("cnss_daemon_running"))
        and bool(helper.get("ok"))
        and bool(bridge.get("ok"))
        and bool(readwrite.get("ok"))
    )
    if not route_ok:
        label = "dual-rfs-post-cal-indication-route-regression"
        reason = "V2030 did not preserve rollback, light observer, cnss-daemon, dual RFS bridges, or helper prerequisites"
        passed = False
    elif intish(cascade.get("wlan0")) > 0:
        label = "dual-rfs-post-cal-indication-wlan0-progress"
        reason = "dual RFS post-cal route reached wlan0; stop before credentials/scan/connect until a dedicated gate"
        passed = True
    elif intish(cascade.get("fw_ready")) > 0:
        label = "dual-rfs-post-cal-indication-fw-ready-progress"
        reason = "dual RFS post-cal route crossed into visible FW-ready progress"
        passed = True
    elif not cap_bdf_cal_success:
        label = "dual-rfs-post-cal-indication-cap-bdf-cal-regression"
        reason = "V2030 did not reproduce the successful WLFW cap/BDF/cal-report path"
        passed = False
    elif hit(ind, "wlfw_worker_cal_only_call") == 0:
        label = "dual-rfs-post-cal-indication-worker-branch-changed"
        reason = "The worker no longer took the direct cal-only branch; inspect branch probes before widening scope"
        passed = True
    elif hit(ind, "wlfw_worker_done_signal") == 0:
        label = "dual-rfs-post-cal-indication-worker-no-done-signal"
        reason = "The worker called cal-report but did not signal post-cal completion"
        passed = True
    elif hit(ind, "wlfw_qmi_ind_cb_entry") == 0:
        label = "dual-rfs-post-cal-indication-none-from-modem"
        reason = "After cap/BDF/cal success, cnss-daemon received no WLFW QMI indication from the modem/WLAN PD"
        passed = True
    elif (
        hit(ind, "wlfw_qmi_ind_fw_mem_flag") > 0
        and hit(ind, "wlfw_qmi_ind_queue_link") == 0
        and hit(ind, "wlfw_worker_handle_ind_call") == 0
    ):
        label = "dual-rfs-post-cal-fwmem-only-no-fwready-indication"
        reason = "Only the non-queued WLFW fw-mem indication arrived; no queueable FW-ready/status indication followed cap/BDF/cal"
        passed = True
    elif hit(ind, "wlfw_qmi_ind_queue_link") == 0:
        label = "dual-rfs-post-cal-indication-callback-not-queued"
        reason = "A WLFW QMI indication callback ran, but no decoded queueable indication was linked for the worker"
        passed = True
    elif hit(ind, "wlfw_worker_handle_ind_call") == 0:
        label = "dual-rfs-post-cal-indication-queued-not-drained"
        reason = "WLFW QMI indication was queued, but the worker did not drain it"
        passed = True
    else:
        label = "dual-rfs-post-cal-indication-handled-no-fw-ready"
        reason = "WLFW indication was delivered and handled, but FW-ready/wlan0 still did not appear"
        passed = True
    return {
        **base,
        "label": label,
        "decision": f"v2031-{label}-rollback-{'pass' if passed else 'blocked'}",
        "pass": passed,
        "reason": reason,
        "hook_ok": current_hook_ok,
        "helper_completion_ok": bool(helper.get("ok")),
        "readwrite_bridge_ok": bool(readwrite.get("ok")),
        "rfs_bridge_ok": bool(bridge.get("ok")),
        "route_ok": route_ok,
        "lower_route_observed": lower_route_observed,
        "cap_bdf_cal_success": cap_bdf_cal_success,
    }


def event_rows(events: dict[str, dict[str, str]]) -> list[list[str]]:
    return prev2007.event_rows(events)


def render_report(manifest: dict[str, Any]) -> str:
    details = manifest["details"]
    classification = manifest["classification"]
    cascade = details["cascade"]
    post = details["post_cal_indication"]
    trace = details["wlanmdsp_trace"]
    bridge = trace["rfs_bridge"]
    matrix_rows = [
        ["label", classification["label"], classification["reason"]],
        ["helper", classification.get("helper_completion_ok"), details["helper_completion"]["result_file_version"]],
        ["route", classification.get("route_ok"), f"service74={details['service74']} service180={details['service180']} holder={details['holder_opened']} cnss={cascade.get('cnss_daemon_running')} lower={classification.get('lower_route_observed')}"],
        ["rfs_probe", classification.get("rfs_bridge_ok"), f"path={bridge.get('probe_path')} exists={bridge.get('probe_exists')} size={bridge.get('probe_size')} open_rc={bridge.get('probe_open_rc')}"],
        ["rfs_fallback", classification.get("rfs_bridge_ok"), f"path={bridge.get('fallback_path')} exists={bridge.get('fallback_exists')} size={bridge.get('fallback_size')} open_rc={bridge.get('fallback_open_rc')}"],
        ["readwrite", classification.get("readwrite_bridge_ok"), f"server_check={details['readwrite_bridge']['server_check_exists']} tmpfs={details['readwrite_bridge']['readwrite_tmpfs_requested']}"],
        ["cascade", "", f"wlan_pd={cascade['wlan_pd_up']} icnss_qmi={cascade['icnss_qmi_connected']} wlfw69={cascade['wlfw69']} fw_ready={cascade['fw_ready']} wlan0={cascade['wlan0']} hold={cascade.get('post_up_hold_sec')}"],
        ["wlanmdsp", "", f"requested={cascade.get('requested_wlanmdsp')} tftp_lines={cascade.get('wlanmdsp_tftp')} pd_load={cascade.get('pd_load')} errors={cascade.get('wlanmdsp_error')}"],
        ["cap_bdf_cal", classification.get("cap_bdf_cal_success"), f"cap={post['cap_return_rc']} bdf={post['bdf_return_rc']} cal={post['cal_return_rc']} worker_cal={post['worker_cal_rc']}"],
        ["indication", "", f"cb_hits={post['ind_events']['wlfw_qmi_ind_cb_entry']['hit_count']} first_msg={post['first_ind_msg_id']} len={post['first_ind_payload_len']} handle_type={post['first_handle_type']} fw_status={post['first_handle_0x28_status']}"],
    ]
    step_lines = [
        f"- `{step['name']}` rc `{step['rc']}` ok `{step['ok']}` evidence `{step['file']}`"
        for step in manifest["steps"]
    ]
    return "\n".join([
        "# Native Init V2031 Dual RFS Post-Cal Indication Handoff",
        "",
        "## Summary",
        "",
        "- Cycle: `V2031`",
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
        "## Tail Events",
        "",
        prev1998.prev1992.prev.markdown_table(["event", "hits", "fetch", "first"], event_rows(post["tail_events"])),
        "",
        "## Indication Events",
        "",
        prev1998.prev1992.prev.markdown_table(["event", "hits", "fetch", "first"], event_rows(post["ind_events"])),
        "",
        "## Interpretation",
        "",
        "- V2031 keeps the V2029 dual RFS serve-path bridge and reruns the V2009 post-cal WLFW indication split without `tftp_server` ptrace.",
        "- Same-boot WLFW consumption is proven by successful cap/BDF/cal QMI returns; the live `wlanmdsp.mbn` request/open/OACK edge was observed in V2029 on the exact dual-RFS path, but completed ACK/DATA transfer was not.",
        "- `msg_id=0x2b` is the fw-mem flag/condition path and is not expected to queue a worker indication; a missing queue link is only decisive for queueable `0x28`/`0x2a`/`0x41` indications.",
        "- If `WLFW 69`/FW-ready appears, downstream is healthy and the next bounded gate can chase `wlan0` without Wi-Fi HAL/scan/connect.",
        "- If cap/BDF/cal succeeds but no queueable FW-ready/status indication is delivered, the blocker is either unproven `wlanmdsp.mbn` payload transfer completion or the later modem/WLAN-PD FW-ready publication edge.",
        "",
        "## Steps",
        "",
        *step_lines,
        "",
        "## Safety",
        "",
        "- No Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping was used.",
        "- No rild/cnss/pm-service strace, boot-time QRTR matrix, service-locator probe, service-notifier listener, active QRTR readback, QMI payload send, or `tftp_server` ptrace was run.",
        "- No direct `/dev/subsys_esoc0` open/control, forced RC1/case, PMIC/GPIO/GDSC/regulator, PCI rescan, platform bind/unbind, fake ONLINE, or eSoC notify/BOOT_DONE action was used.",
        "- Mutation scope: `/cache` one-shot clean-DSP flag, V2030 test-boot flash-handoff, namespace-local RFS tmpfs/symlink bridges, and rollback to `stage3/boot_linux_v724.img` with selftest fail=0.",
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
    prev1998.V1997_OUT = V2030_OUT
    prev1998.V1997_INIT = V2030_INIT
    prev1998.V1997_BOOT = V2030_BOOT
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

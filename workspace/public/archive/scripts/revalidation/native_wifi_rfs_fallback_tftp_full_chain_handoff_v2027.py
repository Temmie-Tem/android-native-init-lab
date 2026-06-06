#!/usr/bin/env python3
"""V2027 rollbackable handoff for Android-parity RFS fallback TFTP full-chain tracing."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import native_wifi_tftp_alltask_result_handoff_v2021 as prev2021


CYCLE = "V2027"
OUT_DIR = prev2021.prev2013.prev1998.prev1992.prev.repo_path(
    "tmp/wifi/v2027-rfs-fallback-tftp-full-chain-handoff"
)
HANDOFF_DIR = OUT_DIR / "v2026-handoff"
HANDOFF_REPORT = OUT_DIR / "v2026-handoff-report.md"
REPORT_PATH = prev2021.prev2013.prev1998.prev1992.prev.repo_path(
    "docs/reports/NATIVE_INIT_V2027_RFS_FALLBACK_TFTP_FULL_CHAIN_HANDOFF_2026-06-04.md"
)
V2026_OUT = prev2021.prev2013.prev1998.prev1992.prev.repo_path(
    "tmp/wifi/v2026-rfs-fallback-tftp-full-chain-test-boot"
)
V2026_INIT = V2026_OUT / "init_v2026_rfs_fallback_tftp_full_chain"
V2026_BOOT = V2026_OUT / "boot_linux_v2026_rfs_fallback_tftp_full_chain.img"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v2026/dev/__properties__"
TEST_EXPECT_VERSION = "A90 Linux init 0.9.195 (v2026-rfs-fallback-tftp-full-chain)"
TEST_LOG_PATH = "/cache/native-init-wifi-test-boot-v2026.log"
TEST_SUMMARY_PATH = "/cache/native-init-wifi-test-boot-v2026.summary"
TEST_HELPER_RESULT_PATH = "/cache/native-init-wifi-test-boot-v2026-helper.result"
EXPECTED_HELPER_VERSION = "a90_android_execns_probe v381"


ORIGINAL_COLLECT_DETAILS = prev2021.prev2013.collect_details


def rel(path: Path) -> str:
    return prev2021.rel(path)


def intish(value: object) -> int:
    return prev2021.intish(value)


def hit(events: dict[str, dict[str, str]], name: str) -> int:
    return prev2021.prev2013.hit(events, name)


def is_zero(value: str) -> bool:
    return prev2021.prev2013.is_zero(value)


def artifact_hook_check() -> dict[str, Any]:
    init_required = (
        "native-init-sibling-fwssctl-v641",
        "A90v641: sibling fwssctl proof armed",
        "wifi-v641-fwssctl",
        "A90v2026",
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
        "android_parity=firmware_mnt_probe_absent_firmware_fallback_present",
        "probe.absolute=/vendor/rfs/msm/mpss/readonly/vendor/firmware_mnt/image/wlanmdsp.mbn",
        "fallback.absolute=/vendor/rfs/msm/mpss/readonly/vendor/firmware/wlanmdsp.mbn",
        "server_check.absolute=/vendor/rfs/msm/mpss/readwrite/server_check.txt",
        "readwrite.tmpfs_requested=1",
        "wifi_companion_start.cnss_daemon_argv=/vendor/bin/cnss-daemon -n -l",
        "wlan_pd_icnss_ipc_snapshot",
        "wlfw_cal_report_return",
        "wlfw_worker_cal_only_call",
        "wlfw_qmi_ind_cb_entry",
        "wifi_companion_start.wlan_pd_producer_tftp_server_syscall_trace.early_attach=%d",
        "wlan_pd_tftp_server_trace.early_attach.requested=1",
        "wlan_pd_tftp_server_trace.early_attach.done=1",
        "wlan_pd_tftp_server_trace.late_attach.begin=1",
        "wlan_pd_tftp_server_trace.late_attach.all_tasks=1",
        "wlan_pd_tftp_server_trace.late_attach.task_count=%zu",
        "%s.%s.%s.record_%03u",
        "compactfs",
        ".payload_len=%zu",
        ".error_message=",
        "sendmsg",
        "recvmsg",
        "max_tasks=%u",
        ".token.server_check=%d",
        ".token.ota_firewall=%d",
        ".token.wlanmdsp=%d",
    )
    checks: dict[str, Any] = {}
    for path, required in ((V2026_INIT, init_required), (V2026_BOOT, boot_required)):
        forbidden_tokens = init_forbidden if path == V2026_INIT else ()
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
        bridge.get("android_parity") == "firmware_mnt_probe_absent_firmware_fallback_present"
        and bridge.get("probe_exists") == 0
        and str(bridge.get("probe_open_rc")) == "-1"
        and str(bridge.get("probe_open_errno")) == "2"
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


def collect_details(handoff: dict[str, Any]) -> dict[str, Any]:
    details = ORIGINAL_COLLECT_DETAILS(handoff)
    fields = prev2021.prev2013.prev1998.parse_fields(prev2021.prev2013.prev1998.read_helper_text())
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
    return details


def path_has(paths: dict[str, int], needle: str) -> bool:
    return any(needle in path for path, count in paths.items() if intish(count) > 0)


def classify(handoff: dict[str, Any],
             hook: dict[str, Any],
             steps: list[dict[str, Any]],
             details: dict[str, Any]) -> dict[str, Any]:
    base = prev2021.ORIGINAL_CLASSIFY(handoff, hook, steps, details)
    trace = details.get("wlanmdsp_trace") if isinstance(details.get("wlanmdsp_trace"), dict) else {}
    bridge = trace.get("rfs_bridge") if isinstance(trace.get("rfs_bridge"), dict) else {}
    helper = details.get("helper_completion") if isinstance(details.get("helper_completion"), dict) else {}
    readwrite = details.get("readwrite_bridge") if isinstance(details.get("readwrite_bridge"), dict) else {}
    cascade = details.get("cascade") if isinstance(details.get("cascade"), dict) else {}
    post = details.get("post_cal_indication") if isinstance(details.get("post_cal_indication"), dict) else {}
    cap = post.get("cap_events") if isinstance(post.get("cap_events"), dict) else {}
    bdf = post.get("bdf_events") if isinstance(post.get("bdf_events"), dict) else {}
    tail = post.get("tail_events") if isinstance(post.get("tail_events"), dict) else {}
    tftp_summary = details.get("tftp_summary_fields") if isinstance(details.get("tftp_summary_fields"), dict) else {}
    tftp_trace = details.get("tftp_syscall_trace") if isinstance(details.get("tftp_syscall_trace"), dict) else {}
    fs_success = tftp_trace.get("fs_success_counts") if isinstance(tftp_trace.get("fs_success_counts"), dict) else {}
    fs_errors = tftp_trace.get("fs_error_counts") if isinstance(tftp_trace.get("fs_error_counts"), dict) else {}
    packet_paths = tftp_trace.get("tftp_data_paths") if isinstance(tftp_trace.get("tftp_data_paths"), dict) else {}
    packet_ops = tftp_trace.get("packet_op_counts") if isinstance(tftp_trace.get("packet_op_counts"), dict) else {}
    fallback_success = path_has(fs_success, "readonly/vendor/firmware/wlanmdsp.mbn")
    fallback_packet = path_has(packet_paths, "/readonly/vendor/firmware/wlanmdsp.mbn")
    probe_error = path_has(fs_errors, "readonly/vendor/firmware_mnt/image/wlanmdsp.mbn")
    probe_packet = path_has(packet_paths, "/readonly/vendor/firmware_mnt/image/wlanmdsp.mbn")
    ack_packet_count = max(
        intish(tftp_trace.get("tftp_ack_packet_count")),
        intish(packet_ops.get("ACK")),
    )
    data_packet_count = max(
        intish(tftp_trace.get("tftp_data_packet_count")),
        intish(packet_ops.get("DATA")),
    )
    oack_packet_count = max(
        intish(tftp_trace.get("tftp_oack_packet_count")),
        intish(packet_ops.get("OACK")),
    )
    error_packet_count = max(
        intish(tftp_trace.get("tftp_error_packet_count")),
        intish(packet_ops.get("ERROR")),
    )
    wlanmdsp_seen = (
        bool(trace.get("requested"))
        or bool(tftp_trace.get("wlanmdsp_seen"))
        or bool(tftp_trace.get("tftp_data_wlanmdsp"))
        or intish(tftp_summary.get("requested_wlanmdsp")) > 0
    )
    wlanmdsp_payload_transfer_seen = (
        (fallback_success or fallback_packet)
        and (ack_packet_count > 0 or data_packet_count > 0)
    )
    cap_bdf_cal_success = (
        hit(cap, "wlfw_cap_success_branch") > 0
        and hit(bdf, "wlfw_bdf_return") > 0
        and is_zero(str(post.get("bdf_return_rc", "")))
        and hit(tail, "wlfw_cal_report_return") > 0
        and is_zero(str(post.get("cal_return_rc", "")))
    )
    current_hook = artifact_hook_check()
    current_hook_ok = all(bool(item.get("ok")) for item in current_hook.values())
    route_ok = (
        current_hook_ok
        and bool(base.get("prearm_ok"))
        and bool(base.get("rollback_ok"))
        and bool(base.get("light_ok"))
        and bool(base.get("lower_route_observed"))
        and bool(helper.get("ok"))
        and bool(bridge.get("ok"))
        and bool(readwrite.get("ok"))
        and bool(tftp_trace.get("compiled_ok"))
        and bool(tftp_trace.get("safety_contract_ok"))
        and bool(tftp_trace.get("trace_active"))
    )
    if not route_ok:
        label = "rfs-fallback-tftp-route-regression"
        reason = "V2026 did not preserve rollback, light observer, Android-parity bridges, full chain, or bounded TFTP trace"
        passed = False
    elif intish(cascade.get("wlan0")) > 0:
        label = "rfs-fallback-tftp-wlan0-progress"
        reason = "Android-parity fallback plus full chain reached wlan0; stop before credentials/scan/connect until gated"
        passed = True
    elif intish(cascade.get("fw_ready")) > 0:
        label = "rfs-fallback-tftp-fw-ready-progress"
        reason = "Android-parity fallback plus full chain reached firmware-ready progress"
        passed = True
    elif fallback_success and cap_bdf_cal_success and wlanmdsp_payload_transfer_seen:
        label = "rfs-fallback-wlanmdsp-transfer-post-cal-no-fw-ready"
        reason = "fallback wlanmdsp path opened and exchanged payload packets, and cap/BDF/cal completed, but FW-ready/wlan0 did not follow"
        passed = True
    elif fallback_success and cap_bdf_cal_success:
        label = "rfs-fallback-wlanmdsp-open-oack-only-post-cal-no-fw-ready"
        reason = "fallback wlanmdsp path opened and OACKs were observed, but no ACK/DATA payload transfer was captured before cap/BDF/cal completed without FW-ready/wlan0"
        passed = True
    elif fallback_success and wlanmdsp_payload_transfer_seen:
        label = "rfs-fallback-wlanmdsp-transfer-no-fw-ready"
        reason = "fallback wlanmdsp path opened and exchanged payload packets, but FW-ready/wlan0 did not follow"
        passed = True
    elif fallback_success:
        label = "rfs-fallback-wlanmdsp-open-oack-only-no-fw-ready"
        reason = "fallback wlanmdsp path opened and OACKs were observed, but no ACK/DATA payload transfer was captured before FW-ready/wlan0 stalled"
        passed = True
    elif wlanmdsp_seen or probe_packet or probe_error or fallback_packet:
        label = "rfs-fallback-wlanmdsp-request-serve-incomplete"
        reason = "the modem requested wlanmdsp, but the Android fallback path did not show a successful focused open"
        passed = True
    elif tftp_trace.get("server_check_seen") or tftp_trace.get("ota_firewall_seen") or tftp_trace.get("mcfg_seen"):
        label = "rfs-fallback-initial-tftp-no-wlanmdsp"
        reason = "native reached initial TFTP traffic, but no wlanmdsp request followed under the Android-parity fallback"
        passed = True
    elif intish(tftp_trace.get("tftp_data_record_count")) > 0:
        label = "rfs-fallback-data-no-wlanmdsp"
        reason = "stock tftp_server received modem RRQ/WRQ packets, but none requested wlanmdsp"
        passed = True
    else:
        label = "rfs-fallback-zero-tftp-request"
        reason = "bridges and full chain were present, but no modem TFTP request reached stock tftp_server"
        passed = True
    return {
        **base,
        "label": label,
        "decision": f"v2027-{label}-rollback-{'pass' if passed else 'blocked'}",
        "pass": passed,
        "reason": reason,
        "hook_ok": current_hook_ok,
        "route_ok": route_ok,
        "helper_completion_ok": bool(helper.get("ok")),
        "rfs_bridge_ok": bool(bridge.get("ok")),
        "readwrite_bridge_ok": bool(readwrite.get("ok")),
        "tftp_trace_ok": bool(tftp_trace.get("compiled_ok")) and bool(tftp_trace.get("safety_contract_ok")),
        "tftp_trace_active": bool(tftp_trace.get("trace_active")),
        "fallback_success": fallback_success,
        "fallback_packet": fallback_packet,
        "probe_error": probe_error,
        "probe_packet": probe_packet,
        "wlanmdsp_payload_transfer_seen": wlanmdsp_payload_transfer_seen,
        "tftp_ack_packet_count": ack_packet_count,
        "tftp_data_packet_count": data_packet_count,
        "tftp_oack_packet_count": oack_packet_count,
        "tftp_error_packet_count": error_packet_count,
        "cap_bdf_cal_success": cap_bdf_cal_success,
    }


def rows_to_md(rows: list[list[object]]) -> str:
    return prev2021.rows_to_md(rows)


def render_report(manifest: dict[str, Any]) -> str:
    details = manifest["details"]
    classification = manifest["classification"]
    cascade = details["cascade"]
    post = details["post_cal_indication"]
    tftp_summary = details["tftp_summary_fields"]
    tftp_trace = details["tftp_syscall_trace"]
    trace_summary = tftp_trace.get("summary", {})
    trace = details["wlanmdsp_trace"]
    bridge = trace["rfs_bridge"]
    if classification["label"] == "rfs-fallback-wlanmdsp-transfer-post-cal-no-fw-ready":
        interpretation_lines = [
            "- The Android-parity fallback `readonly/vendor/firmware/wlanmdsp.mbn` path opened and payload packet transfer was observed.",
            "- Cap/BDF/cal still returned success but no FW-ready/`wlan0` followed; the next gate is after successful firmware transfer and WLFW downstream sends.",
        ]
    elif "open-oack-only" in classification["label"]:
        interpretation_lines = [
            "- The Android-parity fallback `readonly/vendor/firmware/wlanmdsp.mbn` path opened and OACKs were observed.",
            "- The trace did not capture any ACK/DATA payload packets, so this run proves request/open/OACK only, not completed `wlanmdsp.mbn` transfer.",
            "- Before escalating deeper into modem/WLAN-PD, close the transfer-completion discriminator with the least intrusive observer available.",
        ]
    elif "wlanmdsp-request" in classification["label"]:
        interpretation_lines = [
            "- The modem requested `wlanmdsp.mbn`, but the successful fallback-path open was not observed.",
            "- Next bounded unit should focus only on the stock `tftp_server` serve/result side for that request.",
        ]
    else:
        interpretation_lines = [
            "- The route stayed rollbackable, but did not prove a completed fallback `wlanmdsp.mbn` transfer.",
            "- Do not return to AP-side RIL/cnss/pm-service captures; the discriminator remains the modem TFTP branch or post-transfer firmware-ready edge.",
        ]
    matrix_rows = [
        ["label", classification["label"], classification["reason"]],
        ["helper", classification.get("helper_completion_ok"), details["helper_completion"]["result_file_version"]],
        ["route", classification.get("route_ok"), f"service74={details['service74']} service180={details['service180']} holder={details['holder_opened']}"],
        ["rfs_probe", bridge.get("probe_exists") == 0, f"path={bridge.get('probe_path')} open_rc={bridge.get('probe_open_rc')} errno={bridge.get('probe_open_errno')}"],
        ["rfs_fallback", classification.get("fallback_success"), f"path={bridge.get('fallback_path')} exists={bridge.get('fallback_exists')} size={bridge.get('fallback_size')} open_rc={bridge.get('fallback_open_rc')}"],
        ["readwrite", classification.get("readwrite_bridge_ok"), f"server_check={details['readwrite_bridge']['server_check_exists']} tmpfs={details['readwrite_bridge']['readwrite_tmpfs_requested']}"],
        ["cascade", "", f"wlan_pd={cascade['wlan_pd_up']} icnss_qmi={cascade['icnss_qmi_connected']} wlfw69={cascade['wlfw69']} fw_ready={cascade['fw_ready']} wlan0={cascade['wlan0']} hold={cascade.get('post_up_hold_sec')}"],
        ["tftp_trace", classification.get("tftp_trace_active"), f"compiled={trace_summary.get('compiled')} attach_rc={trace_summary.get('late_attach_rc')} detach_rc={trace_summary.get('late_detach_rc')} records={tftp_trace.get('record_count')} packet={tftp_trace.get('packet_record_count')} fs={tftp_trace.get('fs_record_count')} stops={trace_summary.get('late_syscall_stop_count')} ms={trace_summary.get('late_duration_ms')} truncated={trace_summary.get('late_syscall_trace_truncated')}"],
        ["packet_ops", tftp_trace.get("packet_op_counts"), f"ack={classification.get('tftp_ack_packet_count')} data={classification.get('tftp_data_packet_count')} oack={classification.get('tftp_oack_packet_count')} error={classification.get('tftp_error_packet_count')}"],
        ["packet_paths", tftp_trace.get("tftp_data_any_named_request"), f"paths={tftp_trace.get('tftp_data_paths')} token={tftp_trace.get('packet_token_hit_counts')}"],
        ["fs_paths", tftp_trace.get("fs_record_count"), f"success={tftp_trace.get('fs_success_counts')} errors={tftp_trace.get('fs_error_counts')} token={tftp_trace.get('fs_token_hit_counts')}"],
        ["initial_branch", "", f"server_check={tftp_trace.get('server_check_seen')} ota_firewall={tftp_trace.get('ota_firewall_seen')} mcfg={tftp_trace.get('mcfg_seen')} mbn_hw={tftp_trace.get('mbn_hw_seen')}"],
        ["wlanmdsp", "", f"summary={tftp_summary.get('requested_wlanmdsp')} trace={tftp_trace.get('wlanmdsp_seen')} fallback_success={classification.get('fallback_success')} payload_transfer={classification.get('wlanmdsp_payload_transfer_seen')} probe_error={classification.get('probe_error')} dmesg={cascade.get('wlanmdsp_tftp')} pd_load={cascade.get('pd_load')}"],
        ["cap_bdf_cal", classification.get("cap_bdf_cal_success"), f"cap={post['cap_return_rc']} bdf={post['bdf_return_rc']} cal={post['cal_return_rc']} worker_cal={post['worker_cal_rc']}"],
    ]
    step_lines = [
        f"- `{step['name']}` rc `{step['rc']}` ok `{step['ok']}` evidence `{step['file']}`"
        for step in manifest["steps"]
    ]
    return "\n".join([
        "# Native Init V2027 RFS Fallback TFTP Full-Chain Handoff",
        "",
        "## Summary",
        "",
        "- Cycle: `V2027`",
        f"- Decision: `{manifest['decision']}`",
        f"- Label: `{manifest['label']}`",
        f"- Pass: `{manifest['pass']}`",
        f"- Reason: {manifest['reason']}",
        f"- Evidence: `{manifest['out_dir']}`",
        f"- Inner handoff: `{manifest['handoff_manifest']}`",
        "",
        "## Matrix",
        "",
        rows_to_md(matrix_rows),
        "",
        "## Interpretation",
        "",
        *interpretation_lines,
        "",
        "## First TFTP Packets",
        "",
        *(f"- `{line}`" for line in tftp_trace.get("first_packet_records", [])),
        *([] if tftp_trace.get("first_packet_records") else ["- `none`"]),
        "",
        "## First TFTP Errors",
        "",
        *(f"- `{line}`" for line in tftp_trace.get("first_error_records", [])),
        *([] if tftp_trace.get("first_error_records") else ["- `none`"]),
        "",
        "## First Focused FS Results",
        "",
        *(f"- `{line}`" for line in tftp_trace.get("first_fs_records", [])),
        *([] if tftp_trace.get("first_fs_records") else ["- `none`"]),
        "",
        "## Steps",
        "",
        *step_lines,
        *([] if step_lines else ["- `none`"]),
        "",
        "## Safety",
        "",
        "- No Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping was used.",
        "- No rild/cnss/pm-service strace, boot-time QRTR matrix, service-locator probe, service-notifier listener, active QRTR readback, or QMI payload send was run.",
        "- The only ptrace was the bounded compact all-task syscall trace of stock `tftp_server`; no AP-side multi-strace was run.",
        "- No `/dev/subsys_esoc0`, forced RC1/case, PMIC/GPIO/GDSC/regulator write, PCI rescan, bind/unbind, fake ONLINE, or eSoC notify/BOOT_DONE action was used.",
        "- Mutation scope: `/cache` one-shot clean-DSP flag, V2026 test-boot flash-handoff, namespace-local RFS tmpfs/symlink bridges, and rollback to `stage3/boot_linux_v724.img` with selftest fail=0.",
        "",
    ])


def configure_prev2021() -> None:
    prev2021.CYCLE = CYCLE
    prev2021.OUT_DIR = OUT_DIR
    prev2021.HANDOFF_DIR = HANDOFF_DIR
    prev2021.HANDOFF_REPORT = HANDOFF_REPORT
    prev2021.REPORT_PATH = REPORT_PATH
    prev2021.V2020_OUT = V2026_OUT
    prev2021.V2020_INIT = V2026_INIT
    prev2021.V2020_BOOT = V2026_BOOT
    prev2021.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev2021.TEST_EXPECT_VERSION = TEST_EXPECT_VERSION
    prev2021.TEST_LOG_PATH = TEST_LOG_PATH
    prev2021.TEST_SUMMARY_PATH = TEST_SUMMARY_PATH
    prev2021.TEST_HELPER_RESULT_PATH = TEST_HELPER_RESULT_PATH
    prev2021.EXPECTED_HELPER_VERSION = EXPECTED_HELPER_VERSION
    prev2021.artifact_hook_check = artifact_hook_check
    prev2021.classify = classify
    prev2021.render_report = render_report
    prev2021.prev2013.collect_details = collect_details


def main(argv: list[str] | None = None) -> int:
    configure_prev2021()
    return prev2021.main(argv)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

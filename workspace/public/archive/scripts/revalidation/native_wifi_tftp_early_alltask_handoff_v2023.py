#!/usr/bin/env python3
"""V2023 rollbackable handoff for native early all-task TFTP tracing."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import native_wifi_tftp_alltask_result_handoff_v2021 as prev2021


CYCLE = "V2023"
OUT_DIR = prev2021.prev2013.prev1998.prev1992.prev.repo_path(
    "tmp/wifi/v2023-tftp-early-alltask-handoff"
)
HANDOFF_DIR = OUT_DIR / "v2022-handoff"
HANDOFF_REPORT = OUT_DIR / "v2022-handoff-report.md"
REPORT_PATH = prev2021.prev2013.prev1998.prev1992.prev.repo_path(
    "docs/reports/NATIVE_INIT_V2023_TFTP_EARLY_ALLTASK_HANDOFF_2026-06-04.md"
)
V2022_OUT = prev2021.prev2013.prev1998.prev1992.prev.repo_path(
    "tmp/wifi/v2022-tftp-early-alltask-test-boot"
)
V2022_INIT = V2022_OUT / "init_v2022_tftp_early_alltask"
V2022_BOOT = V2022_OUT / "boot_linux_v2022_tftp_early_alltask.img"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v2022/dev/__properties__"
TEST_EXPECT_VERSION = "A90 Linux init 0.9.193 (v2022-tftp-early-alltask)"
TEST_LOG_PATH = "/cache/native-init-wifi-test-boot-v2022.log"
TEST_SUMMARY_PATH = "/cache/native-init-wifi-test-boot-v2022.summary"
TEST_HELPER_RESULT_PATH = "/cache/native-init-wifi-test-boot-v2022-helper.result"
EXPECTED_HELPER_VERSION = "a90_android_execns_probe v380"


ORIGINAL_CLASSIFY = prev2021.classify


def rel(path: Path) -> str:
    return prev2021.rel(path)


def intish(value: object) -> int:
    return prev2021.intish(value)


def artifact_hook_check() -> dict[str, Any]:
    init_required = (
        "native-init-sibling-fwssctl-v641",
        "A90v641: sibling fwssctl proof armed",
        "wifi-v641-fwssctl",
        "A90v2022",
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
    for path, required in ((V2022_INIT, init_required), (V2022_BOOT, boot_required)):
        forbidden_tokens = init_forbidden if path == V2022_INIT else ()
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


def classify(handoff: dict[str, Any],
             hook: dict[str, Any],
             steps: list[dict[str, Any]],
             details: dict[str, Any]) -> dict[str, Any]:
    result = ORIGINAL_CLASSIFY(handoff, hook, steps, details)
    trace = details.get("wlanmdsp_trace") if isinstance(details.get("wlanmdsp_trace"), dict) else {}
    helper = details.get("helper_completion") if isinstance(details.get("helper_completion"), dict) else {}
    cascade = details.get("cascade") if isinstance(details.get("cascade"), dict) else {}
    tftp_summary = details.get("tftp_summary_fields") if isinstance(details.get("tftp_summary_fields"), dict) else {}
    tftp_trace = details.get("tftp_syscall_trace") if isinstance(details.get("tftp_syscall_trace"), dict) else {}
    current_hook = artifact_hook_check()
    current_hook_ok = all(bool(item.get("ok")) for item in current_hook.values())
    route_ok = bool(result.get("route_ok")) and current_hook_ok

    if not route_ok:
        label = "tftp-early-route-regression"
        reason = "V2022 did not preserve rollback, light observer, RFS bridges, full chain, or early all-task tftp trace"
        passed = False
    elif intish(cascade.get("wlan0")) > 0:
        label = "tftp-early-wlan0-progress"
        reason = "native reached wlan0; stop before credentials/scan/connect until a dedicated gated unit"
        passed = True
    elif intish(cascade.get("fw_ready")) > 0:
        label = "tftp-early-fw-ready-progress"
        reason = "native crossed into FW-ready progress with the downstream consumer chain running"
        passed = True
    elif (
        trace.get("requested")
        or tftp_trace.get("wlanmdsp_seen")
        or tftp_trace.get("tftp_data_wlanmdsp")
        or intish(tftp_summary.get("requested_wlanmdsp")) > 0
    ):
        label = "tftp-early-wlanmdsp-progress"
        reason = "early tftp trace exposed a native wlanmdsp request/load edge with cnss-daemon running"
        passed = True
    elif tftp_trace.get("server_check_seen") and tftp_trace.get("ota_firewall_seen"):
        label = "tftp-early-servercheck-ota-no-wlanmdsp"
        reason = "native reaches the Android-style server_check and ota_firewall branch, but still never requests wlanmdsp"
        passed = True
    elif tftp_trace.get("server_check_seen"):
        label = "tftp-early-servercheck-only-no-wlanmdsp"
        reason = "native reaches the initial server_check transaction, but does not advance to ota_firewall or wlanmdsp"
        passed = True
    elif tftp_trace.get("mcfg_seen"):
        label = "tftp-early-mcfg-only-no-wlanmdsp"
        reason = "native trace still first exposes mcfg traffic only; initial server_check branch either precedes attach or is skipped"
        passed = True
    elif intish(tftp_trace.get("tftp_data_record_count")) > 0:
        label = "tftp-early-data-no-wlanmdsp"
        reason = "native tftp_server received modem RRQ/WRQ packets, but none requested wlanmdsp"
        passed = True
    else:
        label = "tftp-early-zero-request"
        reason = "bridges, tftp_server, and downstream consumer chain were present, but no modem tftp request reached native tftp_server"
        passed = True

    return {
        **result,
        "label": label,
        "decision": f"v2023-{label}-rollback-{'pass' if passed else 'blocked'}",
        "pass": passed,
        "reason": reason,
        "hook_ok": current_hook_ok,
        "route_ok": route_ok,
        "helper_completion_ok": bool(helper.get("ok")),
        "tftp_trace_ok": bool(tftp_trace.get("compiled_ok")) and bool(tftp_trace.get("safety_contract_ok")),
        "tftp_trace_active": bool(tftp_trace.get("trace_active")),
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

    if classification["label"] == "tftp-early-wlanmdsp-progress":
        interpretation_lines = [
            "- Early all-task tracing reached a native `wlanmdsp` TFTP edge with the full downstream consumer chain running.",
            "- Next bounded unit is downstream-only: follow WLFW 69 / BDF / FW-ready / `wlan0`, still without HAL scan/connect.",
        ]
    elif tftp_trace.get("server_check_seen") and tftp_trace.get("ota_firewall_seen"):
        interpretation_lines = [
            "- Early all-task tracing captured the Android-style initial TFTP branch: `server_check` and `ota_firewall`.",
            "- The branch still does not proceed to `wlanmdsp`; the remaining blocker is after the initial TFTP server handshake.",
        ]
    elif tftp_trace.get("server_check_seen"):
        interpretation_lines = [
            "- Early all-task tracing captured `server_check`, proving the readwrite tmpfs bridge is reached by the modem.",
            "- No `ota_firewall` or `wlanmdsp` request followed in the hold window.",
        ]
    elif tftp_trace.get("mcfg_seen"):
        interpretation_lines = [
            "- Even with immediate post-holder attach, the visible native TFTP branch is still `mcfg` only.",
            "- Because V2021 showed `server_check.txt` created by the modem, this result means the initial transaction either happens before attach completes or the modem takes a native-specific branch before `wlanmdsp`.",
        ]
    else:
        interpretation_lines = [
            "- The route stayed rollbackable, but early tracing did not expose a named modem TFTP request.",
            "- Next bounded unit should re-check attach readiness or server registration without adding heavy AP-side observers.",
        ]

    matrix_rows = [
        ["label", classification["label"], classification["reason"]],
        ["helper", classification.get("helper_completion_ok"), details["helper_completion"]["result_file_version"]],
        ["route", classification.get("route_ok"), f"service74={details['service74']} service180={details['service180']} holder={details['holder_opened']}"],
        ["bridges", classification.get("bridge_or_tftp_path_observed"), f"readonly={classification.get('rfs_bridge_ok')} readwrite={classification.get('readwrite_bridge_ok')}"],
        ["cascade", "", f"wlan_pd={cascade['wlan_pd_up']} icnss_qmi={cascade['icnss_qmi_connected']} wlfw69={cascade['wlfw69']} fw_ready={cascade['fw_ready']} wlan0={cascade['wlan0']} hold={cascade.get('post_up_hold_sec')}"],
        ["tftp_trace", classification.get("tftp_trace_active"), f"compiled={trace_summary.get('compiled')} attach_rc={trace_summary.get('late_attach_rc')} detach_rc={trace_summary.get('late_detach_rc')} records={tftp_trace.get('record_count')} packet={tftp_trace.get('packet_record_count')} fs={tftp_trace.get('fs_record_count')} stops={trace_summary.get('late_syscall_stop_count')} ms={trace_summary.get('late_duration_ms')} truncated={trace_summary.get('late_syscall_trace_truncated')}"],
        ["packet_ops", tftp_trace.get("packet_op_counts"), f"directions={tftp_trace.get('direction_counts')} errors={tftp_trace.get('tftp_error_messages')}"],
        ["packet_paths", tftp_trace.get("tftp_data_any_named_request"), f"paths={tftp_trace.get('tftp_data_paths')} token={tftp_trace.get('packet_token_hit_counts')}"],
        ["fs_paths", tftp_trace.get("fs_record_count"), f"success={tftp_trace.get('fs_success_counts')} errors={tftp_trace.get('fs_error_counts')} token={tftp_trace.get('fs_token_hit_counts')}"],
        ["initial_branch", "", f"server_check={tftp_trace.get('server_check_seen')} ota_firewall={tftp_trace.get('ota_firewall_seen')} mcfg={tftp_trace.get('mcfg_seen')} mbn_hw={tftp_trace.get('mbn_hw_seen')}"],
        ["wlanmdsp", "", f"summary={tftp_summary.get('requested_wlanmdsp')} trace={tftp_trace.get('wlanmdsp_seen')} dmesg={cascade.get('wlanmdsp_tftp')} pd_load={cascade.get('pd_load')}"],
        ["cap_bdf_cal", "", f"cap={post['cap_return_rc']} bdf={post['bdf_return_rc']} cal={post['cal_return_rc']} worker_cal={post['worker_cal_rc']}"],
    ]
    step_lines = [
        f"- `{step['name']}` rc `{step['rc']}` ok `{step['ok']}` evidence `{step['file']}`"
        for step in manifest["steps"]
    ]
    return "\n".join([
        "# Native Init V2023 TFTP Early All-Task Handoff",
        "",
        "## Summary",
        "",
        "- Cycle: `V2023`",
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
        "- Mutation scope: `/cache` one-shot clean-DSP flag, V2022 test-boot flash-handoff, namespace-local RFS tmpfs/symlink bridges, and rollback to `stage3/boot_linux_v724.img` with selftest fail=0.",
        "",
    ])


def configure_prev2021() -> None:
    prev2021.CYCLE = CYCLE
    prev2021.OUT_DIR = OUT_DIR
    prev2021.HANDOFF_DIR = HANDOFF_DIR
    prev2021.HANDOFF_REPORT = HANDOFF_REPORT
    prev2021.REPORT_PATH = REPORT_PATH
    prev2021.V2020_OUT = V2022_OUT
    prev2021.V2020_INIT = V2022_INIT
    prev2021.V2020_BOOT = V2022_BOOT
    prev2021.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev2021.TEST_EXPECT_VERSION = TEST_EXPECT_VERSION
    prev2021.TEST_LOG_PATH = TEST_LOG_PATH
    prev2021.TEST_SUMMARY_PATH = TEST_SUMMARY_PATH
    prev2021.TEST_HELPER_RESULT_PATH = TEST_HELPER_RESULT_PATH
    prev2021.EXPECTED_HELPER_VERSION = EXPECTED_HELPER_VERSION
    prev2021.artifact_hook_check = artifact_hook_check
    prev2021.classify = classify
    prev2021.render_report = render_report


def main(argv: list[str] | None = None) -> int:
    configure_prev2021()
    return prev2021.main(argv)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

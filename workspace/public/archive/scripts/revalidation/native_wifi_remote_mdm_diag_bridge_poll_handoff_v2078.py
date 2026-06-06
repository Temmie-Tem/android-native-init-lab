#!/usr/bin/env python3
"""V2078 rollbackable handoff for remote-MDM DIAG bridge polling."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import native_wifi_diag_wlan_pd_memory_session_mask_handoff_v2074 as prev2074


prev2069 = prev2074.prev2069
CYCLE = "V2078"
OUT_DIR = prev2069.prev2065.prev2063.prev2059.prev2057.prev2046.prev2035.prev1998.prev1992.prev.repo_path(
    "tmp/wifi/v2078-remote-mdm-diag-bridge-poll-handoff"
)
HANDOFF_DIR = OUT_DIR / "v2077-handoff"
HANDOFF_REPORT = OUT_DIR / "v2077-handoff-report.md"
REPORT_PATH = prev2069.prev2065.prev2063.prev2059.prev2057.prev2046.prev2035.prev1998.prev1992.prev.repo_path(
    "docs/reports/NATIVE_INIT_V2078_REMOTE_MDM_DIAG_BRIDGE_POLL_HANDOFF_2026-06-05.md"
)
V2077_OUT = prev2069.prev2065.prev2063.prev2059.prev2057.prev2046.prev2035.prev1998.prev1992.prev.repo_path(
    "tmp/wifi/v2077-remote-mdm-diag-bridge-poll-test-boot"
)
V2077_INIT = V2077_OUT / "init_v2077_remote_mdm_diag_bridge_poll"
V2077_BOOT = V2077_OUT / "boot_linux_v2077_remote_mdm_diag_bridge_poll.img"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v2077/dev/__properties__"
TEST_EXPECT_VERSION = "A90 Linux init 0.9.217 (v2077-remote-mdm-diag-bridge-poll)"
TEST_LOG_PATH = "/cache/native-init-wifi-test-boot-v2077.log"
TEST_SUMMARY_PATH = "/cache/native-init-wifi-test-boot-v2077.summary"
TEST_HELPER_RESULT_PATH = "/cache/native-init-wifi-test-boot-v2077-helper.result"
EXPECTED_HELPER_VERSION = "a90_android_execns_probe v402"


def rel(path: Path) -> str:
    return prev2074.rel(path)


def intish(value: object) -> int:
    return prev2074.intish(value)


def markdown_table(headers: list[str], rows: list[list[object]]) -> str:
    return prev2074.markdown_table(headers, rows)


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
        "diag_remote_dev_query_probe.begin=1",
        "diag_remote_dev_poll_probe.write_attempted=1",
        "diag_remote_dev_poll_probe.log_mask_write=1",
        "diag_remote_dev_poll_probe.event_mask_write=1",
        "diag_remote_dev_poll_probe.stream_config_attempted=1",
        "diag_remote_dev_poll_probe.qmi_send=1",
        "diag_remote_dev_poll_probe.ptraced=1",
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
        "A90v2077",
        "v2077-remote-mdm-diag-bridge-poll",
        "wifi-companion-wlan-pd-post-pm-lower-state-observer-start-only",
        "--timeout-sec",
        "75",
    )
    boot_required = (
        EXPECTED_HELPER_VERSION,
        "per_mgr_vote_focused.begin=1",
        "diag_remote_dev_poll_probe.begin=1",
        "diag_remote_dev_poll_probe.mode=borrowed-private-diag-fd-remote-dev-poll-query-only",
        "diag_remote_dev_poll_probe.fd_borrowed=1",
        "diag_remote_dev_poll_probe.write_attempted=0",
        "diag_remote_dev_poll_probe.log_mask_write=0",
        "diag_remote_dev_poll_probe.event_mask_write=0",
        "diag_remote_dev_poll_probe.stream_config_attempted=0",
        "diag_remote_dev_poll_probe.qmi_send=0",
        "diag_remote_dev_poll_probe.ptraced=0",
        "diag_remote_dev_poll_probe.ioctl=DIAG_IOCTL_REMOTE_DEV",
        "diag_remote_dev_poll_probe.ioctl_number=%d",
        "diag_remote_dev_poll_probe.remote_slot_name=DIAGFWD_MDM",
        "diag_remote_dev_poll_probe.summary.active_count=%u",
        "diag_dci_register_read_probe.begin=1",
        "diag_dci_wlan_target_mask_probe.begin=1",
        "diag_dci_wlan_target_mask_probe.cleanup.begin=1",
        "diag_wlan_pd_memory_device_probe.begin=1",
        "diag_wlan_pd_memory_device_probe.mode=query-gated-wlan-pd-memory-device-session-borrowed-dci-fd",
        "diag_wlan_pd_memory_device_probe.fd_borrowed=1",
        "diag_wlan_pd_memory_device_probe.node_created=0",
        "diag_wlan_pd_memory_device_probe.ioctl_query=DIAG_IOCTL_QUERY_PD_LOGGING",
        "diag_wlan_pd_memory_device_probe.ioctl_switch=DIAG_IOCTL_SWITCH_LOGGING",
        "diag_wlan_pd_memory_device_probe.switch_logging_scope=wlan-pd-memory-device-only",
        "diag_wlan_pd_memory_device_probe.global_transport_switch=0",
        "diag_wlan_pd_memory_device_probe.usb_pcie_switch=0",
        "diag_wlan_pd_memory_device_probe.broad_mask=0",
        "diag_wlan_pd_memory_device_probe.stream_config_attempted=0",
        "diag_wlan_pd_memory_device_probe.restore_ioctl_attempted=0",
        "diag_wlan_pd_memory_regular_mask_probe.begin=1",
        "diag_wlan_pd_memory_regular_mask_probe.mode=session-scoped-user-space-nonhdlc-wlan-log-event-mask-hold-clear",
        "diag_wlan_pd_memory_regular_mask_probe.user_space_data_type_prefix=1",
        "diag_wlan_pd_memory_regular_mask_probe.summary.broad_mask=0",
    )
    checks: dict[str, Any] = {}
    for path, required, forbidden in (
        (V2077_INIT, init_required, init_forbidden),
        (V2077_BOOT, boot_required, boot_forbidden),
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


def collect_remote_dev_poll(fields: dict[str, str]) -> dict[str, Any]:
    prefix = "diag_remote_dev_poll_probe"
    samples = []
    for index in range(64):
        sample_prefix = f"{prefix}.sample_{index:02d}"
        if f"{sample_prefix}.delta_ms" not in fields:
            continue
        samples.append({
            "index": index,
            "delta_ms": intish(fields.get(f"{sample_prefix}.delta_ms")),
            "rc": intish(fields.get(f"{sample_prefix}.rc")),
            "errno": intish(fields.get(f"{sample_prefix}.errno")),
            "remote_dev_mask": fields.get(f"{sample_prefix}.remote_dev_mask", ""),
            "mdm_data_active": intish(fields.get(f"{sample_prefix}.mdm_data_active")),
        })
    data: dict[str, Any] = {
        "begin": intish(fields.get(f"{prefix}.begin")),
        "mode": fields.get(f"{prefix}.mode", ""),
        "fd_borrowed": intish(fields.get(f"{prefix}.fd_borrowed")),
        "write_attempted": intish(fields.get(f"{prefix}.write_attempted")),
        "log_mask_write": intish(fields.get(f"{prefix}.log_mask_write")),
        "event_mask_write": intish(fields.get(f"{prefix}.event_mask_write")),
        "stream_config_attempted": intish(fields.get(f"{prefix}.stream_config_attempted")),
        "qmi_send": intish(fields.get(f"{prefix}.qmi_send")),
        "ptraced": intish(fields.get(f"{prefix}.ptraced")),
        "ioctl": fields.get(f"{prefix}.ioctl", ""),
        "ioctl_number": intish(fields.get(f"{prefix}.ioctl_number")),
        "remote_slot_name": fields.get(f"{prefix}.remote_slot_name", ""),
        "remote_slot": intish(fields.get(f"{prefix}.remote_slot")),
        "poll_interval_ms": intish(fields.get(f"{prefix}.poll_interval_ms")),
        "query_count": intish(fields.get(f"{prefix}.summary.query_count")),
        "success_count": intish(fields.get(f"{prefix}.summary.success_count")),
        "failure_count": intish(fields.get(f"{prefix}.summary.failure_count")),
        "active_count": intish(fields.get(f"{prefix}.summary.active_count")),
        "sample_count": intish(fields.get(f"{prefix}.summary.sample_count")),
        "last_rc": intish(fields.get(f"{prefix}.summary.last_rc")),
        "last_errno": intish(fields.get(f"{prefix}.summary.last_errno")),
        "last_remote_dev_mask": fields.get(f"{prefix}.summary.last_remote_dev_mask", ""),
        "first_active_delta_ms": intish(fields.get(f"{prefix}.summary.first_active_delta_ms")),
        "last_active_delta_ms": intish(fields.get(f"{prefix}.summary.last_active_delta_ms")),
        "samples": samples,
    }
    data["safe"] = (
        data["begin"] == 1
        and data["fd_borrowed"] == 1
        and data["write_attempted"] == 0
        and data["log_mask_write"] == 0
        and data["event_mask_write"] == 0
        and data["stream_config_attempted"] == 0
        and data["qmi_send"] == 0
        and data["ptraced"] == 0
        and data["ioctl"] == "DIAG_IOCTL_REMOTE_DEV"
        and data["ioctl_number"] == 32
        and data["remote_slot_name"] == "DIAGFWD_MDM"
        and data["remote_slot"] == 0
    )
    return data


def collect_details(handoff: dict[str, Any]) -> dict[str, Any]:
    details = prev2074.collect_details(handoff)
    fields = prev2069.prev2065.prev2063.prev2059.prev2057.parse_fields()
    details["diag_remote_dev_poll"] = collect_remote_dev_poll(fields)
    return details


def classify(handoff: dict[str, Any],
             hook: dict[str, Any],
             steps: list[dict[str, Any]],
             details: dict[str, Any]) -> dict[str, Any]:
    base = prev2074.classify(handoff, hook, steps, details)
    poll = details.get("diag_remote_dev_poll") if isinstance(details.get("diag_remote_dev_poll"), dict) else {}
    logdw = details.get("tftp_logdw", {}) if isinstance(details.get("tftp_logdw"), dict) else {}
    summary = logdw.get("summary", {}) if isinstance(logdw.get("summary"), dict) else {}
    cascade = details.get("cascade", {}) if isinstance(details.get("cascade"), dict) else {}
    hook_ok = all(bool(item.get("ok")) for item in hook.values())
    poll_safe = bool(poll.get("safe"))
    query_count = intish(poll.get("query_count"))
    success_count = intish(poll.get("success_count"))
    active_count = intish(poll.get("active_count"))
    wlanmdsp_seen = intish(summary.get("wlanmdsp")) > 0 or intish(cascade.get("wlanmdsp_tftp")) > 0

    if not hook_ok:
        label = "remote-mdm-diag-bridge-poll-artifact-hook-regression"
        passed = False
        reason = "V2077 artifact does not contain the query-only poll contract tokens"
    elif not poll_safe:
        label = "remote-mdm-diag-bridge-poll-safety-regression"
        passed = False
        reason = "remote bridge poll safety markers were absent or unsafe"
    elif query_count <= 1:
        label = "remote-mdm-diag-bridge-poll-insufficient-samples"
        passed = False
        reason = "remote bridge poll did not produce multiple lower-window samples"
    elif active_count > 0 and wlanmdsp_seen:
        label = "remote-mdm-diag-bridge-poll-active-wlanmdsp-requested"
        passed = True
        reason = "MDM DIAG data bridge became active and native requested wlanmdsp"
    elif active_count > 0:
        label = "remote-mdm-diag-bridge-poll-ever-active-no-wlanmdsp"
        passed = True
        reason = "MDM DIAG data bridge became active during the lower window, but native still made no wlanmdsp request"
    elif success_count > 0:
        label = "remote-mdm-diag-bridge-poll-never-active-no-wlanmdsp"
        passed = True
        reason = "remote-device polling succeeded repeatedly but MDM data bridge never became active; remote-MDM mask writes are not a valid next step"
    else:
        label = "remote-mdm-diag-bridge-poll-all-query-failed-no-wlanmdsp"
        passed = True
        reason = "all remote-device poll queries failed; do not send remote masks until the DIAG bridge failure is explained"

    return {
        **base,
        "decision": f"v2078-{label}-rollback-{'pass' if passed else 'blocked'}",
        "label": label,
        "pass": passed,
        "reason": reason,
        "hook_ok": hook_ok,
        "poll_safe": poll_safe,
        "query_count": query_count,
        "success_count": success_count,
        "active_count": active_count,
        "wlanmdsp_seen": wlanmdsp_seen,
    }


def render_report(manifest: dict[str, Any]) -> str:
    details = manifest["details"]
    classification = manifest["classification"]
    poll = details.get("diag_remote_dev_poll", {}) if isinstance(details.get("diag_remote_dev_poll"), dict) else {}
    memory = details.get("diag_wlan_pd_memory_device", {}) if isinstance(details.get("diag_wlan_pd_memory_device"), dict) else {}
    regular = details.get("diag_wlan_pd_memory_regular_mask", {}) if isinstance(details.get("diag_wlan_pd_memory_regular_mask"), dict) else {}
    logdw = details.get("tftp_logdw", {}) if isinstance(details.get("tftp_logdw"), dict) else {}
    summary = logdw.get("summary", {}) if isinstance(logdw.get("summary"), dict) else {}
    cascade = details.get("cascade", {}) if isinstance(details.get("cascade"), dict) else {}
    samples = poll.get("samples", []) if isinstance(poll.get("samples"), list) else []
    step_lines = [
        f"- `{step['name']}` rc `{step['rc']}` ok `{step['ok']}` evidence `{step['file']}`"
        for step in manifest["steps"]
    ]
    sample_rows = [
        [sample.get("index"), sample.get("delta_ms"), sample.get("rc"), sample.get("errno"), sample.get("remote_dev_mask"), sample.get("mdm_data_active")]
        for sample in samples[:12]
    ]
    return "\n".join([
        "# Native Init V2078 Remote-MDM DIAG Bridge Poll Handoff",
        "",
        "## Summary",
        "",
        "- Cycle: `V2078`",
        f"- Decision: `{manifest['decision']}`",
        f"- Label: `{manifest['label']}`",
        f"- Pass: `{manifest['pass']}`",
        f"- Reason: {manifest['reason']}",
        f"- Evidence: `{manifest['out_dir']}`",
        f"- Inner handoff: `{manifest['handoff_manifest']}`",
        "- Comparator: V2076 queried `DIAG_IOCTL_REMOTE_DEV` once and got mask `0x0`. V2078 polls the same query-only ioctl across the lower window before closing the remote-MDM DIAG transport.",
        "",
        "## Matrix",
        "",
        markdown_table(
            ["area", "value", "detail"],
            [
                ["artifact_hook", classification.get("hook_ok"), ""],
                ["remote_poll", poll.get("active_count"), f"safe={poll.get('safe')} query={poll.get('query_count')} success={poll.get('success_count')} failure={poll.get('failure_count')} last_rc={poll.get('last_rc')} last_errno={poll.get('last_errno')} last_mask={poll.get('last_remote_dev_mask')} first_active={poll.get('first_active_delta_ms')} last_active={poll.get('last_active_delta_ms')}"],
                ["memory_switch", memory.get("switched"), f"rc={memory.get('switch_rc')} delta={memory.get('switch_delta_ms')} records={memory.get('read_records')} useful={memory.get('useful_payload_records')} mask_response={memory.get('mask_response_records')}"],
                ["regular_masks", regular.get("armed"), f"hdlc={regular.get('hdlc_disabled')} set={regular.get('set_write_successes')}/{regular.get('set_write_attempts')} clear={regular.get('clear_write_successes')}/{regular.get('clear_write_attempts')} restored={regular.get('hdlc_reenabled')}"],
                ["tftp_branch", "", f"server_check={summary.get('server_check')} ota={summary.get('ota_firewall')} mcfg={summary.get('mcfg')} wlanmdsp={summary.get('wlanmdsp')}"],
                ["cascade", "", f"wlan_pd={cascade.get('wlan_pd_up')} icnss_qmi={cascade.get('icnss_qmi_connected')} fw_ready={cascade.get('fw_ready')} wlan0={cascade.get('wlan0')}"],
            ],
        ),
        "",
        "## Remote Samples",
        "",
        markdown_table(
            ["idx", "delta_ms", "rc", "errno", "mask", "active"],
            sample_rows or [["none", "", "", "", "", ""]],
        ),
        "",
        "## Branch",
        "",
        "- If `remote-mdm-diag-bridge-poll-ever-active-no-wlanmdsp`, a later bounded `USER_SPACE_DATA_TYPE + -MDM` WLAN mask write can target the active interval, under a separate cleanup-verified report.",
        "- If `remote-mdm-diag-bridge-poll-never-active-no-wlanmdsp`, remote-MDM DIAG is closed for this route; pivot to a different modem-side observation path, not another `/dev/diag` remote mask.",
        "- If `remote-mdm-diag-bridge-poll-active-wlanmdsp-requested`, chase the normal BDF, FW-ready, and `wlan0` cascade.",
        "",
        "## Steps",
        "",
        *step_lines,
        *([] if step_lines else ["- `none`"]),
        "",
        "## Safety",
        "",
        "- No Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping was used.",
        "- The new DIAG discriminator was query-only: repeated borrowed private `/dev/diag` `DIAG_IOCTL_REMOTE_DEV` calls, no remote mask write, no USB/PCIE/global DIAG restore, no broad masks, no DCI stream config, no QMI send, no ptrace, no AP-side strace, and no boot-time QRTR matrix.",
        "- Existing V2073 bounded DCI/WLAN-PD session mask cleanup remains in scope; no `/dev/subsys_esoc0`, forced RC1/case, PMIC/GPIO/GDSC/regulator write, PCI rescan, bind/unbind, fake ONLINE, or eSoC notify/BOOT_DONE action was used.",
        "- Mutation scope: `/cache` one-shot clean-DSP flag, V2077 test-boot flash-handoff, namespace-local fallback readonly/readwrite RFS bridges, namespace-local persist-RFS tmpfs mirrors, private tmp-root `/dev/socket/logdw`, private tmp-root `/dev/diag`, tracefs uprobes, bounded DIAG masks, WLAN-PD memory-device DIAG session, and rollback to `stage3/boot_linux_v724.img` with selftest fail=0.",
        "",
    ])


def configure_prev2057() -> None:
    runner = prev2069.prev2065.prev2063.prev2059.prev2057
    runner.CYCLE = CYCLE
    runner.OUT_DIR = OUT_DIR
    runner.HANDOFF_DIR = HANDOFF_DIR
    runner.HANDOFF_REPORT = HANDOFF_REPORT
    runner.REPORT_PATH = REPORT_PATH
    runner.V2056_OUT = V2077_OUT
    runner.V2056_INIT = V2077_INIT
    runner.V2056_BOOT = V2077_BOOT
    runner.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    runner.TEST_EXPECT_VERSION = TEST_EXPECT_VERSION
    runner.TEST_LOG_PATH = TEST_LOG_PATH
    runner.TEST_SUMMARY_PATH = TEST_SUMMARY_PATH
    runner.TEST_HELPER_RESULT_PATH = TEST_HELPER_RESULT_PATH
    runner.EXPECTED_HELPER_VERSION = EXPECTED_HELPER_VERSION
    runner.artifact_hook_check = artifact_hook_check
    runner.collect_details = collect_details
    runner.classify = classify
    runner.render_report = render_report


def main(argv: list[str] | None = None) -> int:
    configure_prev2057()
    return prev2069.prev2065.prev2063.prev2059.prev2057.main(argv)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

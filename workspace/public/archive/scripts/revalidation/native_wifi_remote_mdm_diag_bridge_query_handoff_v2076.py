#!/usr/bin/env python3
"""V2076 rollbackable handoff for remote-MDM DIAG bridge query."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import native_wifi_diag_wlan_pd_memory_session_mask_handoff_v2074 as prev2074


prev2069 = prev2074.prev2069
CYCLE = "V2076"
OUT_DIR = prev2069.prev2065.prev2063.prev2059.prev2057.prev2046.prev2035.prev1998.prev1992.prev.repo_path(
    "tmp/wifi/v2076-remote-mdm-diag-bridge-query-handoff"
)
HANDOFF_DIR = OUT_DIR / "v2075-handoff"
HANDOFF_REPORT = OUT_DIR / "v2075-handoff-report.md"
REPORT_PATH = prev2069.prev2065.prev2063.prev2059.prev2057.prev2046.prev2035.prev1998.prev1992.prev.repo_path(
    "docs/reports/NATIVE_INIT_V2076_REMOTE_MDM_DIAG_BRIDGE_QUERY_HANDOFF_2026-06-05.md"
)
V2075_OUT = prev2069.prev2065.prev2063.prev2059.prev2057.prev2046.prev2035.prev1998.prev1992.prev.repo_path(
    "tmp/wifi/v2075-remote-mdm-diag-bridge-query-test-boot"
)
V2075_INIT = V2075_OUT / "init_v2075_remote_mdm_diag_bridge_query"
V2075_BOOT = V2075_OUT / "boot_linux_v2075_remote_mdm_diag_bridge_query.img"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v2075/dev/__properties__"
TEST_EXPECT_VERSION = "A90 Linux init 0.9.216 (v2075-remote-mdm-diag-bridge-query)"
TEST_LOG_PATH = "/cache/native-init-wifi-test-boot-v2075.log"
TEST_SUMMARY_PATH = "/cache/native-init-wifi-test-boot-v2075.summary"
TEST_HELPER_RESULT_PATH = "/cache/native-init-wifi-test-boot-v2075-helper.result"
EXPECTED_HELPER_VERSION = "a90_android_execns_probe v401"


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
        "diag_remote_dev_query_probe.write_attempted=1",
        "diag_remote_dev_query_probe.log_mask_write=1",
        "diag_remote_dev_query_probe.event_mask_write=1",
        "diag_remote_dev_query_probe.stream_config_attempted=1",
        "diag_remote_dev_query_probe.qmi_send=1",
        "diag_remote_dev_query_probe.ptraced=1",
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
        "A90v2075",
        "v2075-remote-mdm-diag-bridge-query",
        "wifi-companion-wlan-pd-post-pm-lower-state-observer-start-only",
        "--timeout-sec",
        "75",
    )
    boot_required = (
        EXPECTED_HELPER_VERSION,
        "per_mgr_vote_focused.begin=1",
        "diag_remote_dev_query_probe.begin=1",
        "diag_remote_dev_query_probe.mode=borrowed-private-diag-fd-remote-dev-query-only",
        "diag_remote_dev_query_probe.fd_borrowed=1",
        "diag_remote_dev_query_probe.write_attempted=0",
        "diag_remote_dev_query_probe.log_mask_write=0",
        "diag_remote_dev_query_probe.event_mask_write=0",
        "diag_remote_dev_query_probe.stream_config_attempted=0",
        "diag_remote_dev_query_probe.qmi_send=0",
        "diag_remote_dev_query_probe.ptraced=0",
        "diag_remote_dev_query_probe.ioctl=DIAG_IOCTL_REMOTE_DEV",
        "diag_remote_dev_query_probe.ioctl_number=%d",
        "diag_remote_dev_query_probe.remote_slot_name=DIAGFWD_MDM",
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
        (V2075_INIT, init_required, init_forbidden),
        (V2075_BOOT, boot_required, boot_forbidden),
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


def collect_remote_dev_query(fields: dict[str, str]) -> dict[str, Any]:
    prefix = "diag_remote_dev_query_probe"
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
        "remote_mdm_mask_bit": fields.get(f"{prefix}.remote_mdm_mask_bit", ""),
        "rc": intish(fields.get(f"{prefix}.summary.rc", fields.get(f"{prefix}.rc"))),
        "errno": intish(fields.get(f"{prefix}.summary.errno", fields.get(f"{prefix}.errno"))),
        "remote_dev_mask": fields.get(f"{prefix}.summary.remote_dev_mask", fields.get(f"{prefix}.remote_dev_mask", "")),
        "mdm_data_active": intish(fields.get(f"{prefix}.summary.mdm_data_active", fields.get(f"{prefix}.mdm_data_active"))),
        "attempted": intish(fields.get(f"{prefix}.summary.attempted")),
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
    details["diag_remote_dev_query"] = collect_remote_dev_query(fields)
    return details


def classify(handoff: dict[str, Any],
             hook: dict[str, Any],
             steps: list[dict[str, Any]],
             details: dict[str, Any]) -> dict[str, Any]:
    base = prev2074.classify(handoff, hook, steps, details)
    remote = details.get("diag_remote_dev_query") if isinstance(details.get("diag_remote_dev_query"), dict) else {}
    logdw = details.get("tftp_logdw", {}) if isinstance(details.get("tftp_logdw"), dict) else {}
    summary = logdw.get("summary", {}) if isinstance(logdw.get("summary"), dict) else {}
    cascade = details.get("cascade", {}) if isinstance(details.get("cascade"), dict) else {}
    hook_ok = all(bool(item.get("ok")) for item in hook.values())
    remote_safe = bool(remote.get("safe"))
    remote_attempted = intish(remote.get("attempted")) == 1 or intish(remote.get("begin")) == 1
    remote_active = intish(remote.get("mdm_data_active")) == 1
    remote_rc = intish(remote.get("rc"))
    wlanmdsp_seen = intish(summary.get("wlanmdsp")) > 0 or intish(cascade.get("wlanmdsp_tftp")) > 0

    if not hook_ok:
        label = "remote-mdm-diag-bridge-query-artifact-hook-regression"
        passed = False
        reason = "V2075 artifact does not contain the query-only remote bridge contract tokens"
    elif not remote_safe:
        label = "remote-mdm-diag-bridge-query-safety-regression"
        passed = False
        reason = "remote bridge probe safety markers were absent or unsafe"
    elif not remote_attempted:
        label = "remote-mdm-diag-bridge-query-missing"
        passed = False
        reason = "the borrowed-fd DIAG remote-device query did not run"
    elif remote_active and wlanmdsp_seen:
        label = "remote-mdm-diag-bridge-active-wlanmdsp-requested"
        passed = True
        reason = "MDM DIAG data bridge was active and native requested wlanmdsp"
    elif remote_active:
        label = "remote-mdm-diag-bridge-active-no-wlanmdsp"
        passed = True
        reason = "MDM DIAG data bridge is reachable; a later bounded remote-MDM mask write is not off-path, but this query-only run still made no wlanmdsp request"
    elif remote_rc < 0:
        label = "remote-mdm-diag-bridge-query-failed-no-wlanmdsp"
        passed = True
        reason = "DIAG remote-device query failed; do not send remote masks until the bridge failure is explained"
    else:
        label = "remote-mdm-diag-bridge-inactive-no-wlanmdsp"
        passed = True
        reason = "DIAG remote-device query succeeded but MDM data bridge bit was not active; remote-MDM mask writes are not a valid next step"

    return {
        **base,
        "decision": f"v2076-{label}-rollback-{'pass' if passed else 'blocked'}",
        "label": label,
        "pass": passed,
        "reason": reason,
        "hook_ok": hook_ok,
        "remote_safe": remote_safe,
        "remote_attempted": remote_attempted,
        "remote_active": remote_active,
        "wlanmdsp_seen": wlanmdsp_seen,
    }


def render_report(manifest: dict[str, Any]) -> str:
    details = manifest["details"]
    classification = manifest["classification"]
    remote = details.get("diag_remote_dev_query", {}) if isinstance(details.get("diag_remote_dev_query"), dict) else {}
    memory = details.get("diag_wlan_pd_memory_device", {}) if isinstance(details.get("diag_wlan_pd_memory_device"), dict) else {}
    regular = details.get("diag_wlan_pd_memory_regular_mask", {}) if isinstance(details.get("diag_wlan_pd_memory_regular_mask"), dict) else {}
    logdw = details.get("tftp_logdw", {}) if isinstance(details.get("tftp_logdw"), dict) else {}
    summary = logdw.get("summary", {}) if isinstance(logdw.get("summary"), dict) else {}
    cascade = details.get("cascade", {}) if isinstance(details.get("cascade"), dict) else {}
    step_lines = [
        f"- `{step['name']}` rc `{step['rc']}` ok `{step['ok']}` evidence `{step['file']}`"
        for step in manifest["steps"]
    ]
    return "\n".join([
        "# Native Init V2076 Remote-MDM DIAG Bridge Query Handoff",
        "",
        "## Summary",
        "",
        "- Cycle: `V2076`",
        f"- Decision: `{manifest['decision']}`",
        f"- Label: `{manifest['label']}`",
        f"- Pass: `{manifest['pass']}`",
        f"- Reason: {manifest['reason']}",
        f"- Evidence: `{manifest['out_dir']}`",
        f"- Inner handoff: `{manifest['handoff_manifest']}`",
        "- Comparator: V2074 proved WLAN-PD memory-session masks only returned app-side mask responses. V2076 adds one query-only `DIAG_IOCTL_REMOTE_DEV` check before considering any remote-MDM mask transport.",
        "",
        "## Matrix",
        "",
        markdown_table(
            ["area", "value", "detail"],
            [
                ["artifact_hook", classification.get("hook_ok"), ""],
                ["remote_query", remote.get("mdm_data_active"), f"safe={remote.get('safe')} rc={remote.get('rc')} errno={remote.get('errno')} mask={remote.get('remote_dev_mask')} ioctl={remote.get('ioctl')} slot={remote.get('remote_slot_name')}"],
                ["memory_switch", memory.get("switched"), f"rc={memory.get('switch_rc')} delta={memory.get('switch_delta_ms')} records={memory.get('read_records')} useful={memory.get('useful_payload_records')} mask_response={memory.get('mask_response_records')}"],
                ["regular_masks", regular.get("armed"), f"hdlc={regular.get('hdlc_disabled')} set={regular.get('set_write_successes')}/{regular.get('set_write_attempts')} clear={regular.get('clear_write_successes')}/{regular.get('clear_write_attempts')} restored={regular.get('hdlc_reenabled')}"],
                ["tftp_branch", "", f"server_check={summary.get('server_check')} ota={summary.get('ota_firewall')} mcfg={summary.get('mcfg')} wlanmdsp={summary.get('wlanmdsp')}"],
                ["cascade", "", f"wlan_pd={cascade.get('wlan_pd_up')} icnss_qmi={cascade.get('icnss_qmi_connected')} fw_ready={cascade.get('fw_ready')} wlan0={cascade.get('wlan0')}"],
            ],
        ),
        "",
        "## Branch",
        "",
        "- If `remote-mdm-diag-bridge-active-no-wlanmdsp`, a later bounded `USER_SPACE_DATA_TYPE + -MDM` WLAN mask write is source-gated as reachable, but still requires its own explicit report and cleanup checks.",
        "- If `remote-mdm-diag-bridge-inactive-no-wlanmdsp` or `remote-mdm-diag-bridge-query-failed-no-wlanmdsp`, do not send remote masks; pivot to a different modem-side logging transport.",
        "- If `remote-mdm-diag-bridge-active-wlanmdsp-requested`, chase the normal BDF, FW-ready, and `wlan0` cascade.",
        "",
        "## Steps",
        "",
        *step_lines,
        *([] if step_lines else ["- `none`"]),
        "",
        "## Safety",
        "",
        "- No Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping was used.",
        "- The new DIAG discriminator was query-only: one borrowed private `/dev/diag` `DIAG_IOCTL_REMOTE_DEV` call, no remote mask write, no USB/PCIE/global DIAG restore, no broad masks, no DCI stream config, no QMI send, no ptrace, no AP-side strace, and no boot-time QRTR matrix.",
        "- Existing V2073 bounded DCI/WLAN-PD session mask cleanup remains in scope; no `/dev/subsys_esoc0`, forced RC1/case, PMIC/GPIO/GDSC/regulator write, PCI rescan, bind/unbind, fake ONLINE, or eSoC notify/BOOT_DONE action was used.",
        "- Mutation scope: `/cache` one-shot clean-DSP flag, V2075 test-boot flash-handoff, namespace-local fallback readonly/readwrite RFS bridges, namespace-local persist-RFS tmpfs mirrors, private tmp-root `/dev/socket/logdw`, private tmp-root `/dev/diag`, tracefs uprobes, bounded DIAG masks, WLAN-PD memory-device DIAG session, and rollback to `stage3/boot_linux_v724.img` with selftest fail=0.",
        "",
    ])


def configure_prev2057() -> None:
    runner = prev2069.prev2065.prev2063.prev2059.prev2057
    runner.CYCLE = CYCLE
    runner.OUT_DIR = OUT_DIR
    runner.HANDOFF_DIR = HANDOFF_DIR
    runner.HANDOFF_REPORT = HANDOFF_REPORT
    runner.REPORT_PATH = REPORT_PATH
    runner.V2056_OUT = V2075_OUT
    runner.V2056_INIT = V2075_INIT
    runner.V2056_BOOT = V2075_BOOT
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

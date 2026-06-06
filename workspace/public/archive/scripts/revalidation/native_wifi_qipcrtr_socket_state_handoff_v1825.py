#!/usr/bin/env python3
"""V1825 one-run passive QIPCRTR socket-state handoff."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import native_wifi_qrtr_registry_handoff_v1822 as prev1822


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
CYCLE = "V1825"
V1824_OUT = REPO_ROOT / "tmp" / "wifi" / "v1824-qipcrtr-socket-state-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v1824/dev/__properties__"
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1825-qipcrtr-socket-state-handoff"
DEFAULT_REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1825_QIPCRTR_SOCKET_STATE_HANDOFF_2026-06-03.md"
)
TEST_EXPECT_VERSION = "A90 Linux init 0.9.158 (v1824-qipcrtr-socket-state)"
TEST_LOG_PATH = "/cache/native-init-wifi-test-boot-v1824.log"
TEST_SUMMARY_PATH = "/cache/native-init-wifi-test-boot-v1824.summary"
TEST_HELPER_RESULT_PATH = "/cache/native-init-wifi-test-boot-v1824-helper.result"
DMESG_PATTERN = (
    "A90v1824|wlan_pd_qipcrtr_socket_state|QIPCRTR|AF_QIPCRTR|"
    "wlan_pd_qrtr_registry|wlan_pd_post_pm_lower_handoff_klog|"
    "raw_count_|last_|service_locator|service-locator|servloc|domain|"
    "wlan/fw|wlan_fw|qmi-server|qmi_server_connected|pd-mapper|pd_mapper|"
    "subsys|subsystem|pil|q6v5|qmi|QMI|wlfw|WLFW|service_notifier|"
    "service-notifier|service 180|service 74|wlan_pd|qrtr|service 69|"
    "FW ready|BDF|wlan0|cnss-daemon|4080000.qcom,mss|soc:qcom,mdm3"
)

SOCKET_PREFIX = "wlan_pd_qipcrtr_socket_state.net_window"
SOCKET_PROTOCOL_PHASES = ("before_open", "after_open", "after_close")
SOCKET_PROTOCOL_FIELDS = (
    "protocols_open",
    "protocols_error",
    "qipcrtr_present",
    "qipcrtr_line",
    "qipcrtr_size",
    "qipcrtr_sockets",
)


def configure_runner() -> None:
    prev1819 = prev1822.prev1819
    prev1819.CYCLE = CYCLE
    prev1819.V1818_OUT = V1824_OUT
    prev1819.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev1819.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    prev1819.DEFAULT_REPORT_PATH = DEFAULT_REPORT_PATH
    prev1819.TEST_EXPECT_VERSION = TEST_EXPECT_VERSION
    prev1819.TEST_LOG_PATH = TEST_LOG_PATH
    prev1819.TEST_SUMMARY_PATH = TEST_SUMMARY_PATH
    prev1819.TEST_HELPER_RESULT_PATH = TEST_HELPER_RESULT_PATH
    prev1819.DMESG_PATTERN = DMESG_PATTERN
    prev1819.configure_runner()
    runner = prev1819.prev1816.prev1796.runner
    runner.DEFAULT_SOURCE_MANIFEST = V1824_OUT / "manifest.json"
    runner.DEFAULT_TEST_IMAGE = V1824_OUT / "boot_linux_v1824_qipcrtr_socket_state.img"
    runner.LOCAL_PROPERTY_ROOT = V1824_OUT / "property-runtime" / "layout" / "dev" / "__properties__"


def intish(value: object) -> int:
    return prev1822.intish(value)


def field_boolish(value: object) -> bool:
    return prev1822.field_boolish(value)


def socket_protocol_sample(fields: dict[str, str], phase: str) -> dict[str, str]:
    prefix = f"{SOCKET_PREFIX}.{phase}."
    return {
        "phase": phase,
        **{key: fields.get(prefix + key, "") for key in SOCKET_PROTOCOL_FIELDS},
    }


def collect_gate_fields(fields: dict[str, str]) -> dict[str, Any]:
    details = prev1822.collect_gate_fields(fields)
    protocol_samples = [
        socket_protocol_sample(fields, phase)
        for phase in SOCKET_PROTOCOL_PHASES
    ]
    before_sockets = intish(protocol_samples[0].get("qipcrtr_sockets"))
    after_open_sockets = intish(protocol_samples[1].get("qipcrtr_sockets"))
    after_close_sockets = intish(protocol_samples[2].get("qipcrtr_sockets"))
    details.update(
        {
            "qipcrtr_socket_protocol_samples": protocol_samples,
            "qipcrtr_socket_begin": fields.get(f"{SOCKET_PREFIX}.begin", ""),
            "qipcrtr_socket_end": fields.get(f"{SOCKET_PREFIX}.end", ""),
            "qipcrtr_socket_mode": fields.get(f"{SOCKET_PREFIX}.mode", ""),
            "qipcrtr_socket_family": fields.get(f"{SOCKET_PREFIX}.family", ""),
            "qipcrtr_socket_type": fields.get(f"{SOCKET_PREFIX}.type", ""),
            "qipcrtr_socket_open_rc": fields.get(f"{SOCKET_PREFIX}.open.rc", ""),
            "qipcrtr_socket_open_errno": fields.get(f"{SOCKET_PREFIX}.open.errno", ""),
            "qipcrtr_socket_open_error": fields.get(f"{SOCKET_PREFIX}.open.error", ""),
            "qipcrtr_socket_getsockname_rc": fields.get(f"{SOCKET_PREFIX}.getsockname.rc", ""),
            "qipcrtr_socket_getsockname_errno": fields.get(f"{SOCKET_PREFIX}.getsockname.errno", ""),
            "qipcrtr_socket_getsockname_error": fields.get(f"{SOCKET_PREFIX}.getsockname.error", ""),
            "qipcrtr_socket_getsockname_family": fields.get(f"{SOCKET_PREFIX}.getsockname.family", ""),
            "qipcrtr_socket_getsockname_node": fields.get(f"{SOCKET_PREFIX}.getsockname.node", ""),
            "qipcrtr_socket_getsockname_port": fields.get(f"{SOCKET_PREFIX}.getsockname.port", ""),
            "qipcrtr_socket_close_rc": fields.get(f"{SOCKET_PREFIX}.close.rc", ""),
            "qipcrtr_socket_close_errno": fields.get(f"{SOCKET_PREFIX}.close.errno", ""),
            "qipcrtr_socket_close_error": fields.get(f"{SOCKET_PREFIX}.close.error", ""),
            "qipcrtr_socket_no_bind": fields.get(f"{SOCKET_PREFIX}.no_bind", ""),
            "qipcrtr_socket_no_connect": fields.get(f"{SOCKET_PREFIX}.no_connect", ""),
            "qipcrtr_socket_no_send": fields.get(f"{SOCKET_PREFIX}.no_send", ""),
            "qipcrtr_socket_no_lookup_send": fields.get(f"{SOCKET_PREFIX}.no_qrtr_lookup_send", ""),
            "qipcrtr_socket_no_control_payload": fields.get(f"{SOCKET_PREFIX}.no_qrtr_control_payload", ""),
            "qipcrtr_socket_no_service_start": fields.get(f"{SOCKET_PREFIX}.no_service_start", ""),
            "qipcrtr_socket_before_sockets": before_sockets,
            "qipcrtr_socket_after_open_sockets": after_open_sockets,
            "qipcrtr_socket_after_close_sockets": after_close_sockets,
            "qipcrtr_socket_count_rises_while_open": (
                before_sockets >= 0
                and after_open_sockets > before_sockets
                and after_close_sockets <= before_sockets
            ),
        }
    )
    non_actions_ok = all(
        fields.get(f"{SOCKET_PREFIX}.{key}", "") == "1"
        for key in (
            "no_bind",
            "no_connect",
            "no_send",
            "no_qrtr_lookup_send",
            "no_qrtr_control_payload",
            "no_service_start",
        )
    )
    details["qipcrtr_socket_contract_ok"] = (
        details["qipcrtr_socket_begin"] == "1"
        and details["qipcrtr_socket_end"] == "1"
        and details["qipcrtr_socket_mode"] == "passive-open-getsockname-close"
        and non_actions_ok
        and all(item.get("protocols_open") == "1" for item in protocol_samples)
        and all(item.get("qipcrtr_present") == "1" for item in protocol_samples)
    )
    details["qipcrtr_socket_safety_ok"] = non_actions_ok
    details["qipcrtr_socket_opened"] = details["qipcrtr_socket_open_rc"] == "0"
    details["qipcrtr_socket_getsockname_ok"] = details["qipcrtr_socket_getsockname_rc"] == "0"
    details["qipcrtr_socket_closed"] = details["qipcrtr_socket_close_rc"] == "0"
    return details


def actual_publication_progress(details: dict[str, Any]) -> bool:
    return prev1822.actual_publication_progress(details)


def classify_gate(args: Any,
                  test_flash: dict[str, Any],
                  rollback_result: dict[str, Any],
                  evidence_dir: Path) -> tuple[str, bool, str, dict[str, Any]]:
    runner = prev1822.prev1819.prev1816.prev1796.runner
    test_version = runner.fwbase.read_text(evidence_dir, "test-version.stdout.txt")
    helper_fields = runner.fwbase.parse_helper_fields(evidence_dir)
    details = collect_gate_fields(helper_fields)
    version_ok = args.expect_test_version in test_version
    rollback_ok = bool(rollback_result.get("ok"))
    helper_contract_seen = prev1822.prev1819.prev1816.prev1796.field_bool(
        helper_fields,
        "wlan_pd_service_object_visible_trigger.begin",
    )
    safety_ok = (
        prev1822.prev1819.prev1816.prev1796.safety_ok(helper_fields)
        and bool(details.get("devnode_safety_ok"))
        and bool(details.get("lower_safety_ok"))
        and bool(details.get("klog_safety_ok"))
        and bool(details.get("qrtr_registry_safety_ok"))
        and bool(details.get("qipcrtr_socket_safety_ok"))
    )
    details.update(
        {
            "version_ok": version_ok,
            "rollback_ok": rollback_ok,
            "helper_contract_seen": helper_contract_seen,
            "safety_ok": safety_ok,
        }
    )

    if not test_flash.get("ok"):
        return f"{args.cycle.lower()}-test-boot-flash-or-verify-failed", False, "test boot flash/verify failed", details
    if not version_ok:
        return f"{args.cycle.lower()}-test-boot-version-missing", False, "expected V1824 test boot version was not collected", details
    if not rollback_ok:
        return f"{args.cycle.lower()}-rollback-failed", False, "rollback to v724 did not verify", details
    if (
        not helper_contract_seen
        or not details.get("lower_contract_ok")
        or not details.get("klog_contract_ok")
        or not details.get("qrtr_registry_contract_ok")
        or not details.get("qipcrtr_socket_contract_ok")
    ):
        return f"{args.cycle.lower()}-observer-contract-missing", False, "helper result missed service-object, lower, klog, registry, or socket-state observer fields", details
    if not safety_ok:
        details["qipcrtr_socket_label"] = "safety-regression"
        return f"{args.cycle.lower()}-safety-regression", False, "one or more hard-stop safety fields regressed", details

    if actual_publication_progress(details):
        label = "lower-publication-progress"
        reason = "service 74, wlan_pd, service-notifier state, WLFW service 69, MHI, or wlan0 progressed"
    elif not bool(details.get("qipcrtr_socket_opened")):
        label = "qipcrtr-socket-open-fails"
        reason = "AF_QIPCRTR protocol is listed, but passive socket open failed"
    elif (
        bool(details.get("qipcrtr_socket_getsockname_ok"))
        and bool(details.get("qipcrtr_socket_closed"))
        and not bool(details.get("raw_wlan_pd_text_positive"))
        and not bool(details.get("raw_service74_text_positive"))
    ):
        label = "qipcrtr-socket-open-getname-close-passive"
        reason = "AF_QIPCRTR opened, getsockname succeeded, and the socket closed without lookup/control payload while service74 and wlan_pd stayed absent"
    else:
        label = "qipcrtr-socket-state-incomplete"
        reason = "passive AF_QIPCRTR socket-state fields were present but did not match an open/getname/close or open-fail discriminator"

    if prev1822.prev1819.prev1816.prev1814.prev1811.lower_progress(details):
        details["post_pm_lower_state_label"] = "lower-progress"
    elif prev1822.prev1819.prev1816.prev1814.prev1811.prev1808.stable_offlining(details):
        details["post_pm_lower_state_label"] = "stable-mdm3-offlining"
    else:
        details["post_pm_lower_state_label"] = "lower-state-incomplete"
    if not bool(details.get("pm_client_return_fetchargs_seen")):
        details["pm_client_return_label"] = "pm-client-return-fetchargs-missing"
    elif bool(details.get("pm_client_return_nonzero")):
        details["pm_client_return_label"] = "pm-client-return-error"
    else:
        details["pm_client_return_label"] = "pm-client-return-success"
    if bool(details.get("klog_servnotif_positive")) and bool(details.get("service_notifier_still_uninit")):
        details["post_pm_lower_handoff_klog_label"] = "servnotif-klog-progress-still-uninit"
    elif not bool(details.get("klog_any_positive")):
        details["post_pm_lower_handoff_klog_label"] = "servnotif-klog-absent"
    else:
        details["post_pm_lower_handoff_klog_label"] = "post-pm-lower-handoff-klog-review"
    if actual_publication_progress(details):
        details["service74_raw_klog_label"] = "service74-progress"
    elif bool(details.get("raw_service74_text_positive")) and not bool(details.get("klog_service74_positive")):
        details["service74_raw_klog_label"] = "service74-parser-miss"
    elif bool(details.get("klog_service180_positive")) and not bool(details.get("raw_service74_text_positive")):
        details["service74_raw_klog_label"] = "service74-raw-absent"
    else:
        details["service74_raw_klog_label"] = "service74-raw-klog-incomplete"
    details["qipcrtr_socket_label"] = label
    return f"{args.cycle.lower()}-{label}-rollback-pass", True, reason, details


def render_socket_samples(samples: list[dict[str, str]]) -> list[str]:
    lines: list[str] = []
    for item in samples:
        lines.append(
            f"- `{item.get('phase')}` qipcrtr present/size/sockets: `{item.get('qipcrtr_present')}` / `{item.get('qipcrtr_size')}` / `{item.get('qipcrtr_sockets')}`"
        )
    return lines


def render_report(result: dict[str, Any]) -> str:
    gate = result.get("gate", {})
    property_deploy = result.get("property_deploy", {})
    lines = [
        "# Native Init V1825 QIPCRTR Socket-State Handoff",
        "",
        "## Summary",
        "",
        "- Cycle: `V1825`",
        "- Type: one-run rollbackable passive QIPCRTR socket-state discriminator",
        f"- Decision: `{result['decision']}`",
        f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
        f"- Reason: {result['reason']}",
        f"- Evidence: `{result['out_dir']}`",
        f"- Rollback attempt: `{result.get('rollback', {}).get('attempt')}`",
        f"- Rollback ok: `{result.get('rollback', {}).get('ok')}`",
        "",
        "## Gate Label",
        "",
        f"- QIPCRTR socket label: `{gate.get('qipcrtr_socket_label')}`",
        f"- service74 raw label: `{gate.get('service74_raw_klog_label')}`",
        f"- PM-client return label: `{gate.get('pm_client_return_label')}`",
        f"- lower-state label: `{gate.get('post_pm_lower_state_label')}`",
        f"- safety ok: `{gate.get('safety_ok')}`",
        "",
        "## Socket State",
        "",
        f"- mode/family/type: `{gate.get('qipcrtr_socket_mode')}` / `{gate.get('qipcrtr_socket_family')}` / `{gate.get('qipcrtr_socket_type')}`",
        f"- open rc/errno/error: `{gate.get('qipcrtr_socket_open_rc')}` / `{gate.get('qipcrtr_socket_open_errno')}` / `{gate.get('qipcrtr_socket_open_error')}`",
        f"- getsockname rc/family/node/port: `{gate.get('qipcrtr_socket_getsockname_rc')}` / `{gate.get('qipcrtr_socket_getsockname_family')}` / `{gate.get('qipcrtr_socket_getsockname_node')}` / `{gate.get('qipcrtr_socket_getsockname_port')}`",
        f"- close rc/errno/error: `{gate.get('qipcrtr_socket_close_rc')}` / `{gate.get('qipcrtr_socket_close_errno')}` / `{gate.get('qipcrtr_socket_close_error')}`",
        f"- socket counts before/after-open/after-close: `{gate.get('qipcrtr_socket_before_sockets')}` / `{gate.get('qipcrtr_socket_after_open_sockets')}` / `{gate.get('qipcrtr_socket_after_close_sockets')}`",
        f"- count rises only while open: `{gate.get('qipcrtr_socket_count_rises_while_open')}`",
        f"- no bind/connect/send/lookup/control/service-start: `{gate.get('qipcrtr_socket_no_bind')}` / `{gate.get('qipcrtr_socket_no_connect')}` / `{gate.get('qipcrtr_socket_no_send')}` / `{gate.get('qipcrtr_socket_no_lookup_send')}` / `{gate.get('qipcrtr_socket_no_control_payload')}` / `{gate.get('qipcrtr_socket_no_service_start')}`",
        *render_socket_samples(gate.get("qipcrtr_socket_protocol_samples", [])),
        "",
        "## Registry And Publication State",
        "",
        f"- registry readable: `{gate.get('qrtr_registry_readable')}`",
        f"- proc_net_qrtr open counts: `{gate.get('qrtr_registry_proc_net_qrtr_open_counts')}`",
        f"- service-locator/domain/wlan-fw/wlan-pd-domain/qmi-server: `{gate.get('raw_service_locator_counts')}` / `{gate.get('raw_servloc_domain_counts')}` / `{gate.get('raw_wlan_fw_counts')}` / `{gate.get('raw_wlan_pd_domain_counts')}` / `{gate.get('raw_qmi_server_connected_counts')}`",
        f"- service180/service74/wlan_pd raw: `{gate.get('raw_service180_text_counts')}` / `{gate.get('raw_service74_text_counts')}` / `{gate.get('raw_wlan_pd_text_counts')}`",
        f"- precondition pd-mapper/subsys/pil/qmi/wlfw: `{gate.get('raw_pd_mapper_counts')}` / `{gate.get('raw_subsys_counts')}` / `{gate.get('raw_pil_counts')}` / `{gate.get('raw_qmi_counts')}` / `{gate.get('raw_wlfw_counts')}`",
        "",
        "## Lower State",
        "",
        f"- early/late service-notifier state: `{gate.get('service_notifier_early_state')}` / `{gate.get('service_notifier_late_state')}`",
        f"- mdm3/MHI/WLFW69/wlan0: `{gate.get('lower_mdm3_states')}` / `{gate.get('lower_mhi_present')}` / `{gate.get('lower_service69_progress')}` / `{gate.get('lower_wlan0_present')}`",
        f"- PM-client register/connect/return-path rc: `{gate.get('pm_client_register_rc')}` / `{gate.get('pm_client_connect_rc')}` / `{gate.get('pm_init_return_path_rc')}`",
        "",
        "## Property Runtime",
        "",
        f"- Remote root: `{property_deploy.get('remote_property_root')}`",
        f"- Transport: `{property_deploy.get('transport')}`",
        f"- Uploaded files/bytes: `{property_deploy.get('file_count')}` / `{property_deploy.get('bytes')}`",
        f"- property_info SHA verified: `{property_deploy.get('property_info_sha_ok')}`",
        f"- vendor_default_prop SHA verified: `{property_deploy.get('vendor_default_sha_ok')}`",
        "",
        "## Safety Scope",
        "",
        "- The route opened one passive AF_QIPCRTR datagram socket, called `getsockname`, and closed it without bind, connect, send, QRTR lookup, QRTR control payload, or service start.",
        "- The route did not open `/dev/subsys_esoc0`, did not fake ONLINE, and did not write PMIC/GPIO/GDSC controls.",
        "- Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, `boot_wlan`, restart-PD request, forced RC1, eSoC notify, BOOT_DONE spoof, PCI rescan, and platform bind/unbind were not used.",
        "- Mutation scope is private property runtime staging on `/mnt/sdext`, one test boot flash, and rollback to `stage3/boot_linux_v724.img`.",
        "",
        "## Next",
        "",
        "- Stop after this one label; do not proceed to Wi-Fi HAL/scan/connect unless WLFW service 69 and `wlan0` are present.",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    configure_runner()
    runner = prev1822.prev1819.prev1816.prev1796.runner
    runner.deploy_property_root = prev1822.prev1819.prev1816.prev1796.deploy_property_root_serial
    runner.classify_gate = classify_gate
    runner.render_report = render_report
    rc = runner.main(argv)
    prev1822.prev1819.prev1816.prev1796.sanitize_evidence_dir(DEFAULT_OUT_DIR)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())

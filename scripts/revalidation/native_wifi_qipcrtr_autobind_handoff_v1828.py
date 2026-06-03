#!/usr/bin/env python3
"""V1828 one-run QIPCRTR local auto-bind handoff."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import native_wifi_qipcrtr_socket_state_handoff_v1825 as prev1825


REPO_ROOT = Path(__file__).resolve().parents[2]
CYCLE = "V1828"
V1827_OUT = REPO_ROOT / "tmp" / "wifi" / "v1827-qipcrtr-autobind-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v1827/dev/__properties__"
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1828-qipcrtr-autobind-handoff"
DEFAULT_REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1828_QIPCRTR_AUTOBIND_HANDOFF_2026-06-03.md"
)
TEST_EXPECT_VERSION = "A90 Linux init 0.9.159 (v1827-qipcrtr-autobind)"
TEST_LOG_PATH = "/cache/native-init-wifi-test-boot-v1827.log"
TEST_SUMMARY_PATH = "/cache/native-init-wifi-test-boot-v1827.summary"
TEST_HELPER_RESULT_PATH = "/cache/native-init-wifi-test-boot-v1827-helper.result"
DMESG_PATTERN = (
    "A90v1827|wlan_pd_qipcrtr_autobind_state|"
    "wlan_pd_qipcrtr_socket_state|QIPCRTR|AF_QIPCRTR|"
    "wlan_pd_qrtr_registry|wlan_pd_post_pm_lower_handoff_klog|"
    "raw_count_|last_|service_locator|service-locator|servloc|domain|"
    "wlan/fw|wlan_fw|qmi-server|qmi_server_connected|pd-mapper|pd_mapper|"
    "subsys|subsystem|pil|q6v5|qmi|QMI|wlfw|WLFW|service_notifier|"
    "service-notifier|service 180|service 74|wlan_pd|qrtr|service 69|"
    "FW ready|BDF|wlan0|cnss-daemon|4080000.qcom,mss|soc:qcom,mdm3"
)

AUTOBIND_PREFIX = "wlan_pd_qipcrtr_autobind_state.net_window"
AUTOBIND_PROTOCOL_PHASES = ("before_open", "while_bound", "after_close")
AUTOBIND_PROTOCOL_FIELDS = (
    "protocols_open",
    "protocols_error",
    "qipcrtr_present",
    "qipcrtr_line",
    "qipcrtr_size",
    "qipcrtr_sockets",
)


def configure_runner() -> None:
    prev1822 = prev1825.prev1822
    prev1819 = prev1822.prev1819
    prev1819.CYCLE = CYCLE
    prev1819.V1818_OUT = V1827_OUT
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
    runner.DEFAULT_SOURCE_MANIFEST = V1827_OUT / "manifest.json"
    runner.DEFAULT_TEST_IMAGE = V1827_OUT / "boot_linux_v1827_qipcrtr_autobind.img"
    runner.LOCAL_PROPERTY_ROOT = V1827_OUT / "property-runtime" / "layout" / "dev" / "__properties__"


def intish(value: object) -> int:
    return prev1825.intish(value)


def autobind_protocol_sample(fields: dict[str, str], phase: str) -> dict[str, str]:
    prefix = f"{AUTOBIND_PREFIX}.{phase}."
    return {
        "phase": phase,
        **{key: fields.get(prefix + key, "") for key in AUTOBIND_PROTOCOL_FIELDS},
    }


def collect_gate_fields(fields: dict[str, str]) -> dict[str, Any]:
    details = prev1825.collect_gate_fields(fields)
    protocol_samples = [
        autobind_protocol_sample(fields, phase)
        for phase in AUTOBIND_PROTOCOL_PHASES
    ]
    details.update(
        {
            "qipcrtr_autobind_protocol_samples": protocol_samples,
            "qipcrtr_autobind_begin": fields.get(f"{AUTOBIND_PREFIX}.begin", ""),
            "qipcrtr_autobind_end": fields.get(f"{AUTOBIND_PREFIX}.end", ""),
            "qipcrtr_autobind_mode": fields.get(f"{AUTOBIND_PREFIX}.mode", ""),
            "qipcrtr_autobind_family": fields.get(f"{AUTOBIND_PREFIX}.family", ""),
            "qipcrtr_autobind_type": fields.get(f"{AUTOBIND_PREFIX}.type", ""),
            "qipcrtr_autobind_bind_attempted": fields.get(f"{AUTOBIND_PREFIX}.bind_attempted", ""),
            "qipcrtr_autobind_bind_local_autobind": fields.get(f"{AUTOBIND_PREFIX}.bind_local_autobind", ""),
            "qipcrtr_autobind_open_rc": fields.get(f"{AUTOBIND_PREFIX}.open.rc", ""),
            "qipcrtr_autobind_open_errno": fields.get(f"{AUTOBIND_PREFIX}.open.errno", ""),
            "qipcrtr_autobind_open_error": fields.get(f"{AUTOBIND_PREFIX}.open.error", ""),
            "qipcrtr_autobind_getsockname_before_rc": fields.get(f"{AUTOBIND_PREFIX}.getsockname_before_bind.rc", ""),
            "qipcrtr_autobind_getsockname_before_node": fields.get(f"{AUTOBIND_PREFIX}.getsockname_before_bind.node", ""),
            "qipcrtr_autobind_getsockname_before_port": fields.get(f"{AUTOBIND_PREFIX}.getsockname_before_bind.port", ""),
            "qipcrtr_autobind_bind_request_family": fields.get(f"{AUTOBIND_PREFIX}.bind.request.family", ""),
            "qipcrtr_autobind_bind_request_node": fields.get(f"{AUTOBIND_PREFIX}.bind.request.node", ""),
            "qipcrtr_autobind_bind_request_port": fields.get(f"{AUTOBIND_PREFIX}.bind.request.port", ""),
            "qipcrtr_autobind_bind_rc": fields.get(f"{AUTOBIND_PREFIX}.bind.rc", ""),
            "qipcrtr_autobind_bind_errno": fields.get(f"{AUTOBIND_PREFIX}.bind.errno", ""),
            "qipcrtr_autobind_bind_error": fields.get(f"{AUTOBIND_PREFIX}.bind.error", ""),
            "qipcrtr_autobind_getsockname_after_rc": fields.get(f"{AUTOBIND_PREFIX}.getsockname_after_bind.rc", ""),
            "qipcrtr_autobind_getsockname_after_family": fields.get(f"{AUTOBIND_PREFIX}.getsockname_after_bind.family", ""),
            "qipcrtr_autobind_getsockname_after_node": fields.get(f"{AUTOBIND_PREFIX}.getsockname_after_bind.node", ""),
            "qipcrtr_autobind_getsockname_after_port": fields.get(f"{AUTOBIND_PREFIX}.getsockname_after_bind.port", ""),
            "qipcrtr_autobind_close_rc": fields.get(f"{AUTOBIND_PREFIX}.close.rc", ""),
            "qipcrtr_autobind_close_errno": fields.get(f"{AUTOBIND_PREFIX}.close.errno", ""),
            "qipcrtr_autobind_close_error": fields.get(f"{AUTOBIND_PREFIX}.close.error", ""),
            "qipcrtr_autobind_no_connect": fields.get(f"{AUTOBIND_PREFIX}.no_connect", ""),
            "qipcrtr_autobind_no_send": fields.get(f"{AUTOBIND_PREFIX}.no_send", ""),
            "qipcrtr_autobind_no_lookup_send": fields.get(f"{AUTOBIND_PREFIX}.no_qrtr_lookup_send", ""),
            "qipcrtr_autobind_no_control_payload": fields.get(f"{AUTOBIND_PREFIX}.no_qrtr_control_payload", ""),
            "qipcrtr_autobind_no_service_start": fields.get(f"{AUTOBIND_PREFIX}.no_service_start", ""),
            "qipcrtr_autobind_before_sockets": intish(protocol_samples[0].get("qipcrtr_sockets")),
            "qipcrtr_autobind_while_bound_sockets": intish(protocol_samples[1].get("qipcrtr_sockets")),
            "qipcrtr_autobind_after_close_sockets": intish(protocol_samples[2].get("qipcrtr_sockets")),
        }
    )
    non_actions_ok = all(
        fields.get(f"{AUTOBIND_PREFIX}.{key}", "") == "1"
        for key in (
            "no_connect",
            "no_send",
            "no_qrtr_lookup_send",
            "no_qrtr_control_payload",
            "no_service_start",
        )
    )
    details["qipcrtr_autobind_contract_ok"] = (
        details["qipcrtr_autobind_begin"] == "1"
        and details["qipcrtr_autobind_end"] == "1"
        and details["qipcrtr_autobind_mode"] == "local-autobind-getsockname-close"
        and details["qipcrtr_autobind_bind_attempted"] == "1"
        and details["qipcrtr_autobind_bind_local_autobind"] == "1"
        and non_actions_ok
        and all(item.get("protocols_open") == "1" for item in protocol_samples)
        and all(item.get("qipcrtr_present") == "1" for item in protocol_samples)
    )
    details["qipcrtr_autobind_safety_ok"] = non_actions_ok
    details["qipcrtr_autobind_opened"] = details["qipcrtr_autobind_open_rc"] == "0"
    details["qipcrtr_autobind_bound"] = details["qipcrtr_autobind_bind_rc"] == "0"
    details["qipcrtr_autobind_getsockname_after_ok"] = details["qipcrtr_autobind_getsockname_after_rc"] == "0"
    details["qipcrtr_autobind_closed"] = details["qipcrtr_autobind_close_rc"] == "0"
    details["qipcrtr_autobind_local_port_nonzero"] = intish(
        details.get("qipcrtr_autobind_getsockname_after_port")
    ) > 0
    return details


def actual_publication_progress(details: dict[str, Any]) -> bool:
    return prev1825.actual_publication_progress(details)


def classify_gate(args: Any,
                  test_flash: dict[str, Any],
                  rollback_result: dict[str, Any],
                  evidence_dir: Path) -> tuple[str, bool, str, dict[str, Any]]:
    runner = prev1825.prev1822.prev1819.prev1816.prev1796.runner
    test_version = runner.fwbase.read_text(evidence_dir, "test-version.stdout.txt")
    helper_fields = runner.fwbase.parse_helper_fields(evidence_dir)
    details = collect_gate_fields(helper_fields)
    version_ok = args.expect_test_version in test_version
    rollback_ok = bool(rollback_result.get("ok"))
    helper_contract_seen = prev1825.prev1822.prev1819.prev1816.prev1796.field_bool(
        helper_fields,
        "wlan_pd_service_object_visible_trigger.begin",
    )
    safety_ok = (
        prev1825.prev1822.prev1819.prev1816.prev1796.safety_ok(helper_fields)
        and bool(details.get("devnode_safety_ok"))
        and bool(details.get("lower_safety_ok"))
        and bool(details.get("klog_safety_ok"))
        and bool(details.get("qrtr_registry_safety_ok"))
        and bool(details.get("qipcrtr_socket_safety_ok"))
        and bool(details.get("qipcrtr_autobind_safety_ok"))
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
        return f"{args.cycle.lower()}-test-boot-version-missing", False, "expected V1827 test boot version was not collected", details
    if not rollback_ok:
        return f"{args.cycle.lower()}-rollback-failed", False, "rollback to v724 did not verify", details
    if (
        not helper_contract_seen
        or not details.get("lower_contract_ok")
        or not details.get("klog_contract_ok")
        or not details.get("qrtr_registry_contract_ok")
        or not details.get("qipcrtr_socket_contract_ok")
        or not details.get("qipcrtr_autobind_contract_ok")
    ):
        return f"{args.cycle.lower()}-observer-contract-missing", False, "helper result missed service-object, lower, klog, registry, unbound socket, or auto-bind observer fields", details
    if not safety_ok:
        details["qipcrtr_autobind_label"] = "safety-regression"
        return f"{args.cycle.lower()}-safety-regression", False, "one or more hard-stop safety fields regressed", details

    if actual_publication_progress(details):
        label = "lower-publication-progress"
        reason = "service 74, wlan_pd, service-notifier state, WLFW service 69, MHI, or wlan0 progressed"
    elif not bool(details.get("qipcrtr_autobind_opened")):
        label = "qipcrtr-autobind-open-fails"
        reason = "AF_QIPCRTR protocol is listed, but passive socket open failed"
    elif not bool(details.get("qipcrtr_autobind_bound")):
        label = "qipcrtr-autobind-fails"
        reason = "AF_QIPCRTR opened, but local auto-bind failed"
    elif (
        bool(details.get("qipcrtr_autobind_getsockname_after_ok"))
        and bool(details.get("qipcrtr_autobind_local_port_nonzero"))
        and bool(details.get("qipcrtr_autobind_closed"))
        and not bool(details.get("raw_wlan_pd_text_positive"))
        and not bool(details.get("raw_service74_text_positive"))
    ):
        label = "qipcrtr-autobind-gets-local-port-passive"
        reason = "AF_QIPCRTR local auto-bind allocated a local port without lookup/control traffic while service74 and wlan_pd stayed absent"
    elif bool(details.get("qipcrtr_autobind_getsockname_after_ok")):
        label = "qipcrtr-autobind-port-zero"
        reason = "AF_QIPCRTR local auto-bind succeeded, but getsockname still returned port 0"
    else:
        label = "qipcrtr-autobind-state-incomplete"
        reason = "auto-bind fields were present but did not match a bound endpoint or bind-fail discriminator"

    if prev1825.prev1822.prev1819.prev1816.prev1814.prev1811.lower_progress(details):
        details["post_pm_lower_state_label"] = "lower-progress"
    elif prev1825.prev1822.prev1819.prev1816.prev1814.prev1811.prev1808.stable_offlining(details):
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
    details["qipcrtr_autobind_label"] = label
    return f"{args.cycle.lower()}-{label}-rollback-pass", True, reason, details


def render_autobind_samples(samples: list[dict[str, str]]) -> list[str]:
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
        "# Native Init V1828 QIPCRTR Auto-Bind Handoff",
        "",
        "## Summary",
        "",
        "- Cycle: `V1828`",
        "- Type: one-run rollbackable QIPCRTR local auto-bind discriminator",
        f"- Decision: `{result['decision']}`",
        f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
        f"- Reason: {result['reason']}",
        f"- Evidence: `{result['out_dir']}`",
        f"- Rollback attempt: `{result.get('rollback', {}).get('attempt')}`",
        f"- Rollback ok: `{result.get('rollback', {}).get('ok')}`",
        "",
        "## Gate Label",
        "",
        f"- QIPCRTR auto-bind label: `{gate.get('qipcrtr_autobind_label')}`",
        f"- service74 raw label: `{gate.get('service74_raw_klog_label')}`",
        f"- PM-client return label: `{gate.get('pm_client_return_label')}`",
        f"- lower-state label: `{gate.get('post_pm_lower_state_label')}`",
        f"- safety ok: `{gate.get('safety_ok')}`",
        "",
        "## Auto-Bind State",
        "",
        f"- mode/family/type: `{gate.get('qipcrtr_autobind_mode')}` / `{gate.get('qipcrtr_autobind_family')}` / `{gate.get('qipcrtr_autobind_type')}`",
        f"- open rc/errno/error: `{gate.get('qipcrtr_autobind_open_rc')}` / `{gate.get('qipcrtr_autobind_open_errno')}` / `{gate.get('qipcrtr_autobind_open_error')}`",
        f"- before-bind getsockname rc/node/port: `{gate.get('qipcrtr_autobind_getsockname_before_rc')}` / `{gate.get('qipcrtr_autobind_getsockname_before_node')}` / `{gate.get('qipcrtr_autobind_getsockname_before_port')}`",
        f"- bind request family/node/port: `{gate.get('qipcrtr_autobind_bind_request_family')}` / `{gate.get('qipcrtr_autobind_bind_request_node')}` / `{gate.get('qipcrtr_autobind_bind_request_port')}`",
        f"- bind rc/errno/error: `{gate.get('qipcrtr_autobind_bind_rc')}` / `{gate.get('qipcrtr_autobind_bind_errno')}` / `{gate.get('qipcrtr_autobind_bind_error')}`",
        f"- after-bind getsockname rc/family/node/port: `{gate.get('qipcrtr_autobind_getsockname_after_rc')}` / `{gate.get('qipcrtr_autobind_getsockname_after_family')}` / `{gate.get('qipcrtr_autobind_getsockname_after_node')}` / `{gate.get('qipcrtr_autobind_getsockname_after_port')}`",
        f"- close rc/errno/error: `{gate.get('qipcrtr_autobind_close_rc')}` / `{gate.get('qipcrtr_autobind_close_errno')}` / `{gate.get('qipcrtr_autobind_close_error')}`",
        f"- socket counts before/while-bound/after-close: `{gate.get('qipcrtr_autobind_before_sockets')}` / `{gate.get('qipcrtr_autobind_while_bound_sockets')}` / `{gate.get('qipcrtr_autobind_after_close_sockets')}`",
        f"- no connect/send/lookup/control/service-start: `{gate.get('qipcrtr_autobind_no_connect')}` / `{gate.get('qipcrtr_autobind_no_send')}` / `{gate.get('qipcrtr_autobind_no_lookup_send')}` / `{gate.get('qipcrtr_autobind_no_control_payload')}` / `{gate.get('qipcrtr_autobind_no_service_start')}`",
        *render_autobind_samples(gate.get("qipcrtr_autobind_protocol_samples", [])),
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
        "- The route opened one AF_QIPCRTR datagram socket, requested local auto-bind with node/port `0/0`, sampled `getsockname`, and closed it without connect, send, QRTR lookup, QRTR control payload, or service start.",
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
    runner = prev1825.prev1822.prev1819.prev1816.prev1796.runner
    runner.deploy_property_root = prev1825.prev1822.prev1819.prev1816.prev1796.deploy_property_root_serial
    runner.classify_gate = classify_gate
    runner.render_report = render_report
    rc = runner.main(argv)
    prev1825.prev1822.prev1819.prev1816.prev1796.sanitize_evidence_dir(DEFAULT_OUT_DIR)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""V1904 one-run internal-modem service-notifier passive-edge handoff."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import native_wifi_qipcrtr_bound_recv_poll_handoff_v1834 as prev1834


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
CYCLE = "V1904"
V1903_OUT = REPO_ROOT / "tmp" / "wifi" / "v1903-servnotif-passive-edge-observer-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v1903/dev/__properties__"
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1904-servnotif-passive-edge-handoff"
DEFAULT_REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1904_SERVNOTIF_PASSIVE_EDGE_HANDOFF_2026-06-03.md"
)
TEST_EXPECT_VERSION = "A90 Linux init 0.9.172 (v1903-servnotif-passive-edge-observer)"
TEST_LOG_PATH = "/cache/native-init-wifi-test-boot-v1903.log"
TEST_SUMMARY_PATH = "/cache/native-init-wifi-test-boot-v1903.summary"
TEST_HELPER_RESULT_PATH = "/cache/native-init-wifi-test-boot-v1903-helper.result"
DMESG_PATTERN = (
    "A90v1903|wlan_pd_qipcrtr_bound_recv_poll_state|"
    "wlan_pd_qipcrtr_local_node_bind_state|wlan_pd_qipcrtr_autobind_state|"
    "wlan_pd_qipcrtr_socket_state|QIPCRTR|AF_QIPCRTR|"
    "wlan_pd_qrtr_registry|wlan_pd_post_pm_lower_handoff_klog|"
    "raw_count_|last_|service_notifier_new_server|new_server_work|"
    "root_service_service_ind_cb|send_ind_ack|Indication received from|"
    "Connection established between QMI handle|service_locator|service-locator|"
    "servloc|domain|wlan/fw|wlan_fw|qmi-server|qmi_server_connected|"
    "pd-mapper|pd_mapper|subsys|subsystem|pil|q6v5|qmi|QMI|wlfw|WLFW|"
    "service_notifier|service-notifier|service 180|service 74|"
    "wlan_pd|qrtr|service 69|wlanmdsp|FW ready|BDF|wlan0|cnss-daemon|"
    "4080000.qcom,mss|soc:qcom,mdm3"
)


def configure_runner() -> None:
    prev1834.CYCLE = CYCLE
    prev1834.V1833_OUT = V1903_OUT
    prev1834.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev1834.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    prev1834.DEFAULT_REPORT_PATH = DEFAULT_REPORT_PATH
    prev1834.TEST_EXPECT_VERSION = TEST_EXPECT_VERSION
    prev1834.TEST_LOG_PATH = TEST_LOG_PATH
    prev1834.TEST_SUMMARY_PATH = TEST_SUMMARY_PATH
    prev1834.TEST_HELPER_RESULT_PATH = TEST_HELPER_RESULT_PATH
    prev1834.DMESG_PATTERN = DMESG_PATTERN
    prev1834.configure_runner()
    runner = get_runner()
    runner.DEFAULT_SOURCE_MANIFEST = V1903_OUT / "manifest.json"
    runner.DEFAULT_TEST_IMAGE = V1903_OUT / "boot_linux_v1903_servnotif_passive_edge_observer.img"
    runner.LOCAL_PROPERTY_ROOT = V1903_OUT / "property-runtime" / "layout" / "dev" / "__properties__"


def get_runner() -> Any:
    return prev1834.prev1831.prev1828.prev1825.prev1822.prev1819.prev1816.prev1796.runner


def field_bool(fields: dict[str, str], name: str) -> bool:
    return prev1834.prev1831.prev1828.prev1825.prev1822.prev1819.prev1816.prev1796.field_bool(fields, name)


def boolish(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "pass"}


def positive_csv(value: object) -> bool:
    parts = [part.strip() for part in str(value or "").split(",") if part.strip()]
    return bool(parts) and any(prev1834.intish(part) > 0 for part in parts)


def zero_csv(value: object) -> bool:
    parts = [part.strip() for part in str(value or "").split(",") if part.strip()]
    return bool(parts) and all(prev1834.intish(part) == 0 for part in parts)


def dmesg_text(evidence_dir: Path) -> str:
    return get_runner().fwbase.read_text(evidence_dir, "test-v1393-dmesg.stdout.txt")


def count_dmesg(text: str, needle: str) -> int:
    return sum(1 for line in text.splitlines() if needle in line)


def collect_gate_fields(fields: dict[str, str], evidence_dir: Path) -> dict[str, Any]:
    details = prev1834.collect_gate_fields(fields)
    dmesg = dmesg_text(evidence_dir)
    details.update(
        {
            "dmesg_service_notifier_new_server_count": count_dmesg(dmesg, "service_notifier_new_server"),
            "dmesg_new_server_work_count": count_dmesg(dmesg, "new_server_work"),
            "dmesg_root_service_ind_cb_count": count_dmesg(dmesg, "root_service_service_ind_cb"),
            "dmesg_send_ind_ack_count": count_dmesg(dmesg, "send_ind_ack"),
            "dmesg_connection_established_count": count_dmesg(dmesg, "Connection established between QMI handle"),
            "dmesg_state_indication_count": count_dmesg(dmesg, "Indication received from"),
            "servnotif_new_server_positive": positive_csv(details.get("raw_service_notifier_new_server_counts"))
            or count_dmesg(dmesg, "Connection established between QMI handle") > 0,
            "service180_positive": boolish(details.get("klog_service180_positive"))
            or positive_csv(details.get("raw_service180_text_counts")),
            "service74_absent": zero_csv(details.get("raw_service74_text_counts"))
            and not boolish(details.get("raw_service74_text_positive"))
            and not boolish(details.get("klog_service74_positive")),
            "wlan_pd_absent": zero_csv(details.get("raw_wlan_pd_text_counts"))
            and not boolish(details.get("raw_wlan_pd_text_positive")),
            "servnotif_listener_uninit": (
                details.get("servnotif_early_state") == "uninit"
                and details.get("servnotif_late_listener_state") == "uninit"
                and details.get("service_notifier_early_state") == "uninit"
                and details.get("service_notifier_late_state") == "uninit"
            ),
            "wlfw69_absent": details.get("wlfw_service69_seen") in {"", "0"}
            and not boolish(details.get("lower_service69_progress")),
            "wlan0_absent": details.get("wlan0_present") in {"", "0"}
            and not boolish(details.get("lower_wlan0_present")),
            "requested_wlanmdsp_absent": details.get("requested_wlanmdsp") in {"", "0"},
        }
    )
    return details


def classify_gate(args: Any,
                  test_flash: dict[str, Any],
                  rollback_result: dict[str, Any],
                  evidence_dir: Path) -> tuple[str, bool, str, dict[str, Any]]:
    runner = get_runner()
    test_version = runner.fwbase.read_text(evidence_dir, "test-version.stdout.txt")
    helper_fields = runner.fwbase.parse_helper_fields(evidence_dir)
    details = collect_gate_fields(helper_fields, evidence_dir)
    version_ok = args.expect_test_version in test_version
    rollback_ok = bool(rollback_result.get("ok"))
    helper_contract_seen = field_bool(helper_fields, "wlan_pd_service_object_visible_trigger.begin")
    safety_ok = (
        prev1834.prev1831.prev1828.prev1825.prev1822.prev1819.prev1816.prev1796.safety_ok(helper_fields)
        and bool(details.get("devnode_safety_ok"))
        and bool(details.get("lower_safety_ok"))
        and bool(details.get("klog_safety_ok"))
        and bool(details.get("qrtr_registry_safety_ok"))
        and bool(details.get("qipcrtr_socket_safety_ok"))
        and bool(details.get("qipcrtr_autobind_safety_ok"))
        and bool(details.get("qipcrtr_local_bind_safety_ok"))
        and bool(details.get("qipcrtr_bound_recv_safety_ok"))
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
        return f"{args.cycle.lower()}-test-boot-version-missing", False, "expected V1903 test boot version was not collected", details
    if not rollback_ok:
        return f"{args.cycle.lower()}-rollback-failed", False, "rollback to v724 did not verify", details
    if (
        not helper_contract_seen
        or not details.get("lower_contract_ok")
        or not details.get("klog_contract_ok")
        or not details.get("qrtr_registry_contract_ok")
        or not details.get("qipcrtr_socket_contract_ok")
        or not details.get("qipcrtr_autobind_contract_ok")
        or not details.get("qipcrtr_local_bind_contract_ok")
        or not details.get("qipcrtr_bound_recv_contract_ok")
    ):
        return f"{args.cycle.lower()}-observer-contract-missing", False, "helper result missed passive lower, service-notifier, registry, or QIPCRTR observer fields", details
    if not safety_ok:
        details["servnotif_passive_edge_label"] = "safety-regression"
        return f"{args.cycle.lower()}-safety-regression", False, "one or more hard-stop safety fields regressed", details

    if prev1834.actual_publication_progress(details) or not boolish(details.get("requested_wlanmdsp_absent")):
        label = "servnotif-passive-edge-progress-readonly-stop"
        reason = "service74, wlan_pd, service-notifier state, WLFW service69, requested wlanmdsp, MHI, or wlan0 progressed"
    elif (
        boolish(details.get("servnotif_new_server_positive"))
        and boolish(details.get("service180_positive"))
        and boolish(details.get("service74_absent"))
        and boolish(details.get("wlan_pd_absent"))
        and boolish(details.get("servnotif_listener_uninit"))
        and boolish(details.get("wlfw69_absent"))
        and boolish(details.get("wlan0_absent"))
        and boolish(details.get("requested_wlanmdsp_absent"))
    ):
        label = "servnotif-new-server-180-only-stateup-edge-absent"
        reason = "service-notifier new-server/service180 is visible, but service74, wlan_pd, requested wlanmdsp, WLFW69, and wlan0 remain absent with uninit listener state"
    else:
        label = "servnotif-passive-edge-incomplete"
        reason = "bounded passive edge fields were present but did not match a fixed progress or 180-only absence discriminator"

    if prev1834.prev1831.prev1828.prev1825.prev1822.prev1819.prev1816.prev1814.prev1811.lower_progress(details):
        details["post_pm_lower_state_label"] = "lower-progress"
    elif prev1834.prev1831.prev1828.prev1825.prev1822.prev1819.prev1816.prev1814.prev1811.prev1808.stable_offlining(details):
        details["post_pm_lower_state_label"] = "stable-mdm3-offlining"
    else:
        details["post_pm_lower_state_label"] = "lower-state-incomplete"
    if not bool(details.get("pm_client_return_fetchargs_seen")):
        details["pm_client_return_label"] = "pm-client-return-fetchargs-missing"
    elif bool(details.get("pm_client_return_nonzero")):
        details["pm_client_return_label"] = "pm-client-return-error"
    else:
        details["pm_client_return_label"] = "pm-client-return-success"
    details["servnotif_passive_edge_label"] = label
    return f"{args.cycle.lower()}-{label}-rollback-pass", True, reason, details


def render_report(result: dict[str, Any]) -> str:
    gate = result.get("gate", {})
    property_deploy = result.get("property_deploy", {})
    lines = [
        "# Native Init V1904 Service-notifier Passive-edge Handoff",
        "",
        "## Summary",
        "",
        "- Cycle: `V1904`",
        "- Type: one-run rollbackable internal-modem service-notifier passive-edge discriminator",
        f"- Decision: `{result['decision']}`",
        f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
        f"- Reason: {result['reason']}",
        f"- Evidence: `{result['out_dir']}`",
        f"- Rollback attempt: `{result.get('rollback', {}).get('attempt')}`",
        f"- Rollback ok: `{result.get('rollback', {}).get('ok')}`",
        "",
        "## Gate Label",
        "",
        f"- service-notifier passive-edge label: `{gate.get('servnotif_passive_edge_label')}`",
        f"- WLFW QRTR readback label: `{gate.get('qrtr_readback_label')}`",
        f"- service-locator domain label: `{gate.get('servloc_domain_label')}`",
        f"- service-notifier listener label: `{gate.get('servnotif_label')}`",
        f"- PM-client return label: `{gate.get('pm_client_return_label')}`",
        f"- lower-state label: `{gate.get('post_pm_lower_state_label')}`",
        f"- safety ok: `{gate.get('safety_ok')}`",
        "",
        "## Passive Edge Evidence",
        "",
        f"- new-server/service180 positive: `{gate.get('servnotif_new_server_positive')}` / `{gate.get('service180_positive')}`",
        f"- service74/wlan_pd absent: `{gate.get('service74_absent')}` / `{gate.get('wlan_pd_absent')}`",
        f"- listener uninit/WLFW69 absent/wlan0 absent/requested-wlanmdsp absent: `{gate.get('servnotif_listener_uninit')}` / `{gate.get('wlfw69_absent')}` / `{gate.get('wlan0_absent')}` / `{gate.get('requested_wlanmdsp_absent')}`",
        f"- raw service-notifier/new-server/qmi counts: `{gate.get('raw_service_notifier_colon_counts')}` / `{gate.get('raw_service_notifier_new_server_counts')}` / `{gate.get('raw_qmi_handle_counts')}`",
        f"- raw service180/service74/wlan_pd counts: `{gate.get('raw_service180_text_counts')}` / `{gate.get('raw_service74_text_counts')}` / `{gate.get('raw_wlan_pd_text_counts')}`",
        f"- dmesg function-name counts new-server/new-server-work/root-ind/ack: `{gate.get('dmesg_service_notifier_new_server_count')}` / `{gate.get('dmesg_new_server_work_count')}` / `{gate.get('dmesg_root_service_ind_cb_count')}` / `{gate.get('dmesg_send_ind_ack_count')}`",
        f"- dmesg printk counts connection/state-indication: `{gate.get('dmesg_connection_established_count')}` / `{gate.get('dmesg_state_indication_count')}`",
        "",
        "## QMI/QRTR Context",
        "",
        f"- service-locator endpoint/status/result: `{gate.get('servloc_domain_endpoint_node')}`:`{gate.get('servloc_domain_endpoint_port')}` / `{gate.get('servloc_domain_endpoint_status')}` / `{gate.get('servloc_domain_result')}`",
        f"- service-locator domain/name/instance: `{gate.get('servloc_domain_count')}` / `{gate.get('servloc_domain0_name')}` / `{gate.get('servloc_domain0_instance_id')}`",
        f"- service-notifier early qmi/state/indication/result: `{gate.get('servnotif_early_qmi_payload')}` / `{gate.get('servnotif_early_state')}` / `{gate.get('servnotif_early_indication_seen')}` / `{gate.get('servnotif_early_result')}`",
        f"- service-notifier late qmi/state/indication/result: `{gate.get('servnotif_late_listener_qmi_payload')}` / `{gate.get('servnotif_late_listener_state')}` / `{gate.get('servnotif_late_listener_indication_seen')}` / `{gate.get('servnotif_late_listener_result')}`",
        f"- WLFW readback allowed/matrix/qmi-payload/result: `{gate.get('qrtr_readback_allowed')}` / `{gate.get('qrtr_readback_matrix')}` / `{gate.get('qrtr_readback_qmi_payload')}` / `{gate.get('qrtr_readback_result')}`",
        "",
        "## Lower State",
        "",
        f"- early/late response state: `{gate.get('service_notifier_early_state')}` / `{gate.get('service_notifier_late_state')}`",
        f"- mdm3/MHI/WLFW69/wlan0: `{gate.get('lower_mdm3_states')}` / `{gate.get('lower_mhi_present')}` / `{gate.get('lower_service69_progress')}` / `{gate.get('lower_wlan0_present')}`",
        f"- requested `wlanmdsp`/WLFW service69/wlan0 trigger flags: `{gate.get('requested_wlanmdsp')}` / `{gate.get('wlfw_service69_seen')}` / `{gate.get('wlan0_present')}`",
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
        "- The observer stayed on the internal modem route and used rollbackable native test boot plus `stage3/boot_linux_v724.img` rollback.",
        "- It did not use private SDX50M, `/dev/subsys_esoc0`, eSoC notify/BOOT_DONE, PCIe/MHI optimization, GDSC/PMIC/GPIO/regulator writes, forced RC1/case, fake-ONLINE, PCI rescan, or platform bind/unbind.",
        "- It did not use Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, or restart-PD request.",
        "",
        "## Next",
        "",
        "- If this label is 180-only absence, the next unit must target the passive servreg state-up indication source before any mutating restart-PD or connect attempt.",
        "- If this label shows progress, stop and run the smallest WLFW69/`wlan0` prerequisite check before any credential-bearing action.",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    configure_runner()
    runner = get_runner()
    runner.deploy_property_root = prev1834.prev1831.prev1828.prev1825.prev1822.prev1819.prev1816.prev1796.deploy_property_root_serial
    runner.classify_gate = classify_gate
    runner.render_report = render_report
    rc = runner.main(argv)
    prev1834.prev1831.prev1828.prev1825.prev1822.prev1819.prev1816.prev1796.sanitize_evidence_dir(DEFAULT_OUT_DIR)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())

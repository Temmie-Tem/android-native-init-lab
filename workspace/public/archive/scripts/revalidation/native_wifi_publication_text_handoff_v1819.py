#!/usr/bin/env python3
"""V1819 one-run wlan_pd publication text handoff."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import native_wifi_lower_publication_precondition_handoff_v1816 as prev1816


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
CYCLE = "V1819"
V1818_OUT = REPO_ROOT / "tmp" / "wifi" / "v1818-wlan-pd-publication-text-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v1818/dev/__properties__"
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1819-publication-text-handoff"
DEFAULT_REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1819_PUBLICATION_TEXT_HANDOFF_2026-06-03.md"
)
TEST_EXPECT_VERSION = "A90 Linux init 0.9.156 (v1818-wlan-pd-publication-text)"
TEST_LOG_PATH = "/cache/native-init-wifi-test-boot-v1818.log"
TEST_SUMMARY_PATH = "/cache/native-init-wifi-test-boot-v1818.summary"
TEST_HELPER_RESULT_PATH = "/cache/native-init-wifi-test-boot-v1818-helper.result"
DMESG_PATTERN = (
    "A90v1818|wlan_pd_post_pm_lower_handoff_klog|raw_count_|last_|"
    "service_locator|service-locator|service locator|servloc|domain|Domain|"
    "wlan/fw|wlan_fw|wlan fw|qmi-server|qmi_server_connected|"
    "pd-mapper|pd_mapper|subsys|subsystem|pil|q6v5|qmi|QMI|wlfw|WLFW|"
    "service_notifier|service-notifier|service 180|service 74|wlan_pd|"
    "pm_init_pm_client_register|pm_init_pm_client_connect|pm_init_return_path|"
    "qrtr|service 69|FW ready|BDF|wlan0|cnss-daemon|"
    "4080000.qcom,mss|soc:qcom,mdm3|Brought out of reset|modem: loading"
)

PUBLICATION_KEYS = (
    "raw_count_service_locator_text",
    "raw_count_servloc_domain_text",
    "raw_count_wlan_fw_text",
    "raw_count_wlan_pd_domain_text",
    "raw_count_qmi_server_connected_text",
    "last_service_locator",
    "last_servloc_domain",
    "last_wlan_fw",
    "last_wlan_pd_domain",
    "last_qmi_server_connected",
)


def configure_runner() -> None:
    prev1816.CYCLE = CYCLE
    prev1816.V1815_OUT = V1818_OUT
    prev1816.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev1816.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    prev1816.DEFAULT_REPORT_PATH = DEFAULT_REPORT_PATH
    prev1816.TEST_EXPECT_VERSION = TEST_EXPECT_VERSION
    prev1816.TEST_LOG_PATH = TEST_LOG_PATH
    prev1816.TEST_SUMMARY_PATH = TEST_SUMMARY_PATH
    prev1816.TEST_HELPER_RESULT_PATH = TEST_HELPER_RESULT_PATH
    prev1816.DMESG_PATTERN = DMESG_PATTERN
    prev1816.configure_runner()
    prev1816.prev1796.runner.DEFAULT_SOURCE_MANIFEST = V1818_OUT / "manifest.json"
    prev1816.prev1796.runner.DEFAULT_TEST_IMAGE = (
        V1818_OUT / "boot_linux_v1818_wlan_pd_publication_text.img"
    )
    prev1816.prev1796.runner.LOCAL_PROPERTY_ROOT = (
        V1818_OUT / "property-runtime" / "layout" / "dev" / "__properties__"
    )


def intish(value: object) -> int:
    return prev1816.intish(value)


def sample(fields: dict[str, str], phase: str) -> dict[str, str]:
    prefix = f"wlan_pd_post_pm_lower_handoff_klog.{phase}."
    return {"phase": phase, **{key: fields.get(prefix + key, "") for key in PUBLICATION_KEYS}}


def series(samples: list[dict[str, str]], key: str) -> list[int]:
    return [intish(item.get(key)) for item in samples if item.get(key) != ""]


def collect_gate_fields(fields: dict[str, str]) -> dict[str, Any]:
    details = prev1816.collect_gate_fields(fields)
    samples = [sample(fields, phase) for phase in prev1816.prev1814.prev1811.KLOG_PHASES]
    service_locator = series(samples, "raw_count_service_locator_text")
    servloc_domain = series(samples, "raw_count_servloc_domain_text")
    wlan_fw = series(samples, "raw_count_wlan_fw_text")
    wlan_pd_domain = series(samples, "raw_count_wlan_pd_domain_text")
    qmi_server_connected = series(samples, "raw_count_qmi_server_connected_text")
    details.update(
        {
            "publication_samples": samples,
            "raw_service_locator_counts": ",".join(str(value) for value in service_locator),
            "raw_servloc_domain_counts": ",".join(str(value) for value in servloc_domain),
            "raw_wlan_fw_counts": ",".join(str(value) for value in wlan_fw),
            "raw_wlan_pd_domain_counts": ",".join(str(value) for value in wlan_pd_domain),
            "raw_qmi_server_connected_counts": ",".join(str(value) for value in qmi_server_connected),
            "raw_service_locator_positive": prev1816.prev1806.any_positive(service_locator),
            "raw_servloc_domain_positive": prev1816.prev1806.any_positive(servloc_domain),
            "raw_wlan_fw_positive": prev1816.prev1806.any_positive(wlan_fw),
            "raw_wlan_pd_domain_positive": prev1816.prev1806.any_positive(wlan_pd_domain),
            "raw_qmi_server_connected_positive": prev1816.prev1806.any_positive(qmi_server_connected),
        }
    )
    details["publication_text_positive"] = (
        bool(details.get("raw_service_locator_positive"))
        or bool(details.get("raw_servloc_domain_positive"))
        or bool(details.get("raw_wlan_fw_positive"))
        or bool(details.get("raw_wlan_pd_domain_positive"))
        or bool(details.get("raw_qmi_server_connected_positive"))
    )
    details["domain_publication_text_positive"] = (
        bool(details.get("raw_servloc_domain_positive"))
        or bool(details.get("raw_wlan_fw_positive"))
        or bool(details.get("raw_wlan_pd_domain_positive"))
        or bool(details.get("raw_qmi_server_connected_positive"))
    )
    return details


def actual_publication_progress(details: dict[str, Any]) -> bool:
    return (
        prev1816.prev1814.prev1811.lower_progress(details)
        or bool(details.get("klog_service74_positive"))
        or bool(details.get("raw_service74_text_positive"))
        or bool(details.get("raw_wlan_pd_text_positive"))
        or prev1816.prev1814.service_notifier_state_progress(details)
    )


def qmi_context_visible(details: dict[str, Any]) -> bool:
    return (
        bool(details.get("klog_service180_positive"))
        and bool(details.get("raw_qmi_positive"))
        and bool(details.get("raw_subsys_positive"))
        and bool(details.get("raw_pil_positive"))
    )


def classify_gate(args: Any,
                  test_flash: dict[str, Any],
                  rollback_result: dict[str, Any],
                  evidence_dir: Path) -> tuple[str, bool, str, dict[str, Any]]:
    test_version = prev1816.prev1796.runner.fwbase.read_text(evidence_dir, "test-version.stdout.txt")
    helper_fields = prev1816.prev1796.runner.fwbase.parse_helper_fields(evidence_dir)
    details = collect_gate_fields(helper_fields)
    version_ok = args.expect_test_version in test_version
    rollback_ok = bool(rollback_result.get("ok"))
    helper_contract_seen = prev1816.prev1796.field_bool(
        helper_fields,
        "wlan_pd_service_object_visible_trigger.begin",
    )
    safety_ok = (
        prev1816.prev1796.safety_ok(helper_fields)
        and bool(details.get("devnode_safety_ok"))
        and bool(details.get("lower_safety_ok"))
        and bool(details.get("klog_safety_ok"))
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
        return f"{args.cycle.lower()}-test-boot-version-missing", False, "expected V1818 test boot version was not collected", details
    if not rollback_ok:
        return f"{args.cycle.lower()}-rollback-failed", False, "rollback to v724 did not verify", details
    if not helper_contract_seen or not details.get("lower_contract_ok") or not details.get("klog_contract_ok"):
        return f"{args.cycle.lower()}-observer-contract-missing", False, "helper result missed service-object, lower, or klog observer fields", details
    if not safety_ok:
        details["publication_text_label"] = "safety-regression"
        return f"{args.cycle.lower()}-safety-regression", False, "one or more hard-stop safety fields regressed", details

    if actual_publication_progress(details):
        label = "lower-publication-progress"
        reason = "service 74, wlan_pd, service-notifier state, WLFW service 69, MHI, or wlan0 progressed"
    elif (
        qmi_context_visible(details)
        and bool(details.get("raw_service_locator_positive"))
        and not bool(details.get("domain_publication_text_positive"))
        and not bool(details.get("raw_wlan_pd_text_positive"))
        and not bool(details.get("raw_service74_text_positive"))
    ):
        label = "servloc-init-visible-domain-absent"
        reason = "generic service-locator init text was visible with sysmon/QMI context, but wlan_pd/domain-QMI/service74 publication remained absent"
    elif (
        qmi_context_visible(details)
        and not bool(details.get("publication_text_positive"))
        and not bool(details.get("raw_wlan_pd_text_positive"))
        and not bool(details.get("raw_service74_text_positive"))
    ):
        label = "publication-text-absent-with-qmi-context"
        reason = "sysmon/QMI, service 180, subsys, and PIL context were visible, but service-locator/domain-QMI/wlan_pd publication text remained absent"
    elif (
        bool(details.get("publication_text_positive"))
        and not bool(details.get("raw_wlan_pd_text_positive"))
        and not bool(details.get("raw_service74_text_positive"))
    ):
        label = "publication-text-visible-still-no-wlanpd"
        reason = "publication-adjacent text was visible, but service 74 and wlan_pd still did not publish"
    elif bool(details.get("preconditions_visible")):
        label = "publication-text-parser-gap"
        reason = "lower precondition text was visible but did not match fixed publication absence/progress labels"
    else:
        label = "publication-text-incomplete"
        reason = "publication text evidence did not match a fixed label"

    if prev1816.prev1814.prev1811.lower_progress(details):
        details["post_pm_lower_state_label"] = "lower-progress"
    elif prev1816.prev1814.prev1811.prev1808.stable_offlining(details):
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
    details["publication_text_label"] = label
    return f"{args.cycle.lower()}-{label}-rollback-pass", True, reason, details


def render_sample(item: dict[str, str]) -> list[str]:
    return [
        f"- `{item.get('phase')}` service-locator/domain/wlan-fw/wlan-pd-domain/qmi-server: `{item.get('raw_count_service_locator_text')}` / `{item.get('raw_count_servloc_domain_text')}` / `{item.get('raw_count_wlan_fw_text')}` / `{item.get('raw_count_wlan_pd_domain_text')}` / `{item.get('raw_count_qmi_server_connected_text')}`",
        f"- `{item.get('phase')}` last locator/domain/wlan-fw/wlan-pd-domain/qmi-server: `{item.get('last_service_locator')}` / `{item.get('last_servloc_domain')}` / `{item.get('last_wlan_fw')}` / `{item.get('last_wlan_pd_domain')}` / `{item.get('last_qmi_server_connected')}`",
    ]


def render_report(result: dict[str, Any]) -> str:
    gate = result.get("gate", {})
    property_deploy = result.get("property_deploy", {})
    sample_lines = [
        line
        for item in gate.get("publication_samples", [])
        for line in render_sample(item)
    ]
    lines = [
        "# Native Init V1819 Publication Text Handoff",
        "",
        "## Summary",
        "",
        "- Cycle: `V1819`",
        "- Type: one-run rollbackable wlan_pd publication text discriminator",
        f"- Decision: `{result['decision']}`",
        f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
        f"- Reason: {result['reason']}",
        f"- Evidence: `{result['out_dir']}`",
        f"- Rollback attempt: `{result.get('rollback', {}).get('attempt')}`",
        f"- Rollback ok: `{result.get('rollback', {}).get('ok')}`",
        "",
        "## Gate Label",
        "",
        f"- publication text label: `{gate.get('publication_text_label')}`",
        f"- service74 raw label: `{gate.get('service74_raw_klog_label')}`",
        f"- PM-client return label: `{gate.get('pm_client_return_label')}`",
        f"- lower-state label: `{gate.get('post_pm_lower_state_label')}`",
        f"- safety ok: `{gate.get('safety_ok')}`",
        "",
        "## Publication Counters",
        "",
        f"- service-locator/domain/wlan-fw/wlan-pd-domain/qmi-server: `{gate.get('raw_service_locator_counts')}` / `{gate.get('raw_servloc_domain_counts')}` / `{gate.get('raw_wlan_fw_counts')}` / `{gate.get('raw_wlan_pd_domain_counts')}` / `{gate.get('raw_qmi_server_connected_counts')}`",
        f"- positives service-locator/domain/wlan-fw/wlan-pd-domain/qmi-server: `{gate.get('raw_service_locator_positive')}` / `{gate.get('raw_servloc_domain_positive')}` / `{gate.get('raw_wlan_fw_positive')}` / `{gate.get('raw_wlan_pd_domain_positive')}` / `{gate.get('raw_qmi_server_connected_positive')}`",
        f"- publication text positive: `{gate.get('publication_text_positive')}`",
        f"- domain publication text positive: `{gate.get('domain_publication_text_positive')}`",
        f"- service180/service74/wlan_pd raw: `{gate.get('raw_service180_text_counts')}` / `{gate.get('raw_service74_text_counts')}` / `{gate.get('raw_wlan_pd_text_counts')}`",
        f"- precondition pd-mapper/subsys/pil/qmi/wlfw: `{gate.get('raw_pd_mapper_counts')}` / `{gate.get('raw_subsys_counts')}` / `{gate.get('raw_pil_counts')}` / `{gate.get('raw_qmi_counts')}` / `{gate.get('raw_wlfw_counts')}`",
        *sample_lines,
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
    prev1816.prev1796.runner.deploy_property_root = prev1816.prev1796.deploy_property_root_serial
    prev1816.prev1796.runner.classify_gate = classify_gate
    prev1816.prev1796.runner.render_report = render_report
    rc = prev1816.prev1796.runner.main(argv)
    prev1816.prev1796.sanitize_evidence_dir(DEFAULT_OUT_DIR)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())

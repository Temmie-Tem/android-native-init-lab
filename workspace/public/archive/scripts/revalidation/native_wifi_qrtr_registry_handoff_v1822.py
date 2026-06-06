#!/usr/bin/env python3
"""V1822 one-run QRTR/servloc registry handoff."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import native_wifi_publication_text_handoff_v1819 as prev1819


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
CYCLE = "V1822"
V1821_OUT = REPO_ROOT / "tmp" / "wifi" / "v1821-qrtr-servloc-registry-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v1821/dev/__properties__"
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1822-qrtr-registry-handoff"
DEFAULT_REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1822_QRTR_REGISTRY_HANDOFF_2026-06-03.md"
)
TEST_EXPECT_VERSION = "A90 Linux init 0.9.157 (v1821-qrtr-servloc-registry)"
TEST_LOG_PATH = "/cache/native-init-wifi-test-boot-v1821.log"
TEST_SUMMARY_PATH = "/cache/native-init-wifi-test-boot-v1821.summary"
TEST_HELPER_RESULT_PATH = "/cache/native-init-wifi-test-boot-v1821-helper.result"
DMESG_PATTERN = (
    "A90v1821|wlan_pd_qrtr_registry|wlan_pd_post_pm_lower_handoff_klog|"
    "raw_count_|last_|service_locator|service-locator|servloc|domain|"
    "wlan/fw|wlan_fw|qmi-server|qmi_server_connected|pd-mapper|pd_mapper|"
    "subsys|subsystem|pil|q6v5|qmi|QMI|wlfw|WLFW|service_notifier|"
    "service-notifier|service 180|service 74|wlan_pd|qrtr|service 69|"
    "FW ready|BDF|wlan0|cnss-daemon|4080000.qcom,mss|soc:qcom,mdm3"
)

REGISTRY_PHASES = ("after_holder_start", "after_early_listener", "after_post_listener_window")
REGISTRY_LABELS = (
    "proc_net_qrtr",
    "debug_qrtr_nodes",
    "debug_qrtr_services",
    "debug_msm_ipc_router_dump",
)
REGISTRY_FIELDS = (
    "open",
    "errno",
    "error",
    "bytes",
    "truncated",
    "lines",
    "interesting_lines",
    "wlan_text",
    "service_locator_text",
    "wlan_fw_text",
    "wlan_pd_text",
    "service74_text",
    "service180_text",
    "qmi_text",
    "first_interesting",
)


def configure_runner() -> None:
    prev1819.CYCLE = CYCLE
    prev1819.V1818_OUT = V1821_OUT
    prev1819.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev1819.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    prev1819.DEFAULT_REPORT_PATH = DEFAULT_REPORT_PATH
    prev1819.TEST_EXPECT_VERSION = TEST_EXPECT_VERSION
    prev1819.TEST_LOG_PATH = TEST_LOG_PATH
    prev1819.TEST_SUMMARY_PATH = TEST_SUMMARY_PATH
    prev1819.TEST_HELPER_RESULT_PATH = TEST_HELPER_RESULT_PATH
    prev1819.DMESG_PATTERN = DMESG_PATTERN
    prev1819.configure_runner()
    prev1819.prev1816.prev1796.runner.DEFAULT_SOURCE_MANIFEST = V1821_OUT / "manifest.json"
    prev1819.prev1816.prev1796.runner.DEFAULT_TEST_IMAGE = (
        V1821_OUT / "boot_linux_v1821_qrtr_servloc_registry.img"
    )
    prev1819.prev1816.prev1796.runner.LOCAL_PROPERTY_ROOT = (
        V1821_OUT / "property-runtime" / "layout" / "dev" / "__properties__"
    )


def intish(value: object) -> int:
    return prev1819.intish(value)


def field_boolish(value: object) -> bool:
    return str(value) == "1" or value is True


def registry_sample(fields: dict[str, str], phase: str, label: str) -> dict[str, str]:
    prefix = f"wlan_pd_qrtr_registry.{phase}.{label}."
    return {
        "phase": phase,
        "label": label,
        **{key: fields.get(prefix + key, "") for key in REGISTRY_FIELDS},
    }


def series(samples: list[dict[str, str]], key: str, label: str | None = None) -> list[int]:
    return [
        intish(item.get(key))
        for item in samples
        if item.get(key) != "" and (label is None or item.get("label") == label)
    ]


def bool_series(samples: list[dict[str, str]], key: str, label: str | None = None) -> bool:
    return any(
        field_boolish(item.get(key))
        for item in samples
        if item.get(key) != "" and (label is None or item.get("label") == label)
    )


def collect_gate_fields(fields: dict[str, str]) -> dict[str, Any]:
    details = prev1819.collect_gate_fields(fields)
    samples = [
        registry_sample(fields, phase, label)
        for phase in REGISTRY_PHASES
        for label in REGISTRY_LABELS
    ]
    details.update({"qrtr_registry_samples": samples})
    for label in REGISTRY_LABELS:
        safe = label.replace("debug_", "").replace("_", "_")
        details[f"qrtr_registry_{safe}_open_counts"] = ",".join(str(value) for value in series(samples, "open", label))
        details[f"qrtr_registry_{safe}_bytes"] = ",".join(str(value) for value in series(samples, "bytes", label))
        details[f"qrtr_registry_{safe}_lines"] = ",".join(str(value) for value in series(samples, "lines", label))
        details[f"qrtr_registry_{safe}_interesting_lines"] = ",".join(str(value) for value in series(samples, "interesting_lines", label))
        details[f"qrtr_registry_{safe}_wlan_text"] = bool_series(samples, "wlan_text", label)
        details[f"qrtr_registry_{safe}_wlan_fw_text"] = bool_series(samples, "wlan_fw_text", label)
        details[f"qrtr_registry_{safe}_wlan_pd_text"] = bool_series(samples, "wlan_pd_text", label)
        details[f"qrtr_registry_{safe}_service74_text"] = bool_series(samples, "service74_text", label)
        details[f"qrtr_registry_{safe}_qmi_text"] = bool_series(samples, "qmi_text", label)
    details["qrtr_registry_readable"] = bool_series(samples, "open")
    details["qrtr_registry_wlan_text_positive"] = bool_series(samples, "wlan_text")
    details["qrtr_registry_wlan_fw_text_positive"] = bool_series(samples, "wlan_fw_text")
    details["qrtr_registry_wlan_pd_text_positive"] = bool_series(samples, "wlan_pd_text")
    details["qrtr_registry_service74_text_positive"] = bool_series(samples, "service74_text")
    details["qrtr_registry_qmi_text_positive"] = bool_series(samples, "qmi_text")
    details["qrtr_registry_no_lookup_send"] = all(
        fields.get(f"wlan_pd_qrtr_registry.{phase}.no_qrtr_lookup_send", "") == "1"
        for phase in REGISTRY_PHASES
    )
    details["qrtr_registry_no_service_start"] = all(
        fields.get(f"wlan_pd_qrtr_registry.{phase}.no_service_start", "") == "1"
        for phase in REGISTRY_PHASES
    )
    details["qrtr_registry_contract_ok"] = all(
        fields.get(f"wlan_pd_qrtr_registry.{phase}.begin", "") == "1"
        and fields.get(f"wlan_pd_qrtr_registry.{phase}.end", "") == "1"
        for phase in REGISTRY_PHASES
    )
    details["qrtr_registry_safety_ok"] = (
        details["qrtr_registry_no_lookup_send"]
        and details["qrtr_registry_no_service_start"]
        and all(fields.get(f"wlan_pd_qrtr_registry.{phase}.no_esoc0_open", "") == "1" for phase in REGISTRY_PHASES)
        and all(fields.get(f"wlan_pd_qrtr_registry.{phase}.no_fake_online", "") == "1" for phase in REGISTRY_PHASES)
        and all(fields.get(f"wlan_pd_qrtr_registry.{phase}.no_pmic_gpio_gdsc_write", "") == "1" for phase in REGISTRY_PHASES)
    )
    return details


def actual_publication_progress(details: dict[str, Any]) -> bool:
    return prev1819.actual_publication_progress(details)


def classify_gate(args: Any,
                  test_flash: dict[str, Any],
                  rollback_result: dict[str, Any],
                  evidence_dir: Path) -> tuple[str, bool, str, dict[str, Any]]:
    test_version = prev1819.prev1816.prev1796.runner.fwbase.read_text(evidence_dir, "test-version.stdout.txt")
    helper_fields = prev1819.prev1816.prev1796.runner.fwbase.parse_helper_fields(evidence_dir)
    details = collect_gate_fields(helper_fields)
    version_ok = args.expect_test_version in test_version
    rollback_ok = bool(rollback_result.get("ok"))
    helper_contract_seen = prev1819.prev1816.prev1796.field_bool(
        helper_fields,
        "wlan_pd_service_object_visible_trigger.begin",
    )
    safety_ok = (
        prev1819.prev1816.prev1796.safety_ok(helper_fields)
        and bool(details.get("devnode_safety_ok"))
        and bool(details.get("lower_safety_ok"))
        and bool(details.get("klog_safety_ok"))
        and bool(details.get("qrtr_registry_safety_ok"))
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
        return f"{args.cycle.lower()}-test-boot-version-missing", False, "expected V1821 test boot version was not collected", details
    if not rollback_ok:
        return f"{args.cycle.lower()}-rollback-failed", False, "rollback to v724 did not verify", details
    if (
        not helper_contract_seen
        or not details.get("lower_contract_ok")
        or not details.get("klog_contract_ok")
        or not details.get("qrtr_registry_contract_ok")
    ):
        return f"{args.cycle.lower()}-observer-contract-missing", False, "helper result missed service-object, lower, klog, or registry observer fields", details
    if not safety_ok:
        details["qrtr_registry_label"] = "safety-regression"
        return f"{args.cycle.lower()}-safety-regression", False, "one or more hard-stop safety fields regressed", details

    if actual_publication_progress(details):
        label = "lower-publication-progress"
        reason = "service 74, wlan_pd, service-notifier state, WLFW service 69, MHI, or wlan0 progressed"
    elif (
        bool(details.get("qrtr_registry_readable"))
        and (
            bool(details.get("qrtr_registry_wlan_text_positive"))
            or bool(details.get("qrtr_registry_wlan_fw_text_positive"))
            or bool(details.get("qrtr_registry_wlan_pd_text_positive"))
        )
        and not bool(details.get("raw_wlan_pd_text_positive"))
        and not bool(details.get("raw_service74_text_positive"))
    ):
        label = "qrtr-registry-wlan-visible-still-no-service74"
        reason = "read-only QRTR registry text exposed wlan surfaces, but service 74 and wlan_pd still did not publish"
    elif bool(details.get("qrtr_registry_readable")):
        label = "qrtr-registry-wlan-absent"
        reason = "read-only QRTR registry state was readable, but wlan/fw and wlan_pd registry text remained absent"
    else:
        label = "qrtr-registry-unreadable-with-qmi-context"
        reason = "sysmon/QMI context was visible, but read-only QRTR registry state was not readable"

    if prev1819.prev1816.prev1814.prev1811.lower_progress(details):
        details["post_pm_lower_state_label"] = "lower-progress"
    elif prev1819.prev1816.prev1814.prev1811.prev1808.stable_offlining(details):
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
    details["qrtr_registry_label"] = label
    return f"{args.cycle.lower()}-{label}-rollback-pass", True, reason, details


def render_registry_samples(samples: list[dict[str, str]]) -> list[str]:
    def shown(value: str | None) -> str:
        return value if value else "0"

    lines: list[str] = []
    for item in samples:
        if item.get("label") != "proc_net_qrtr":
            continue
        lines.append(
            f"- `{item.get('phase')}` proc_net_qrtr open/bytes/lines/wlan/wlan_pd/service74: `{shown(item.get('open'))}` / `{shown(item.get('bytes'))}` / `{shown(item.get('lines'))}` / `{shown(item.get('wlan_text'))}` / `{shown(item.get('wlan_pd_text'))}` / `{shown(item.get('service74_text'))}`"
        )
    return lines


def render_report(result: dict[str, Any]) -> str:
    gate = result.get("gate", {})
    property_deploy = result.get("property_deploy", {})
    lines = [
        "# Native Init V1822 QRTR Registry Handoff",
        "",
        "## Summary",
        "",
        "- Cycle: `V1822`",
        "- Type: one-run rollbackable QRTR/service-locator registry discriminator",
        f"- Decision: `{result['decision']}`",
        f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
        f"- Reason: {result['reason']}",
        f"- Evidence: `{result['out_dir']}`",
        f"- Rollback attempt: `{result.get('rollback', {}).get('attempt')}`",
        f"- Rollback ok: `{result.get('rollback', {}).get('ok')}`",
        "",
        "## Gate Label",
        "",
        f"- QRTR registry label: `{gate.get('qrtr_registry_label')}`",
        f"- service74 raw label: `{gate.get('service74_raw_klog_label')}`",
        f"- PM-client return label: `{gate.get('pm_client_return_label')}`",
        f"- lower-state label: `{gate.get('post_pm_lower_state_label')}`",
        f"- safety ok: `{gate.get('safety_ok')}`",
        "",
        "## Registry Summary",
        "",
        f"- registry readable: `{gate.get('qrtr_registry_readable')}`",
        f"- registry wlan/wlan-fw/wlan-pd/service74/qmi text: `{gate.get('qrtr_registry_wlan_text_positive')}` / `{gate.get('qrtr_registry_wlan_fw_text_positive')}` / `{gate.get('qrtr_registry_wlan_pd_text_positive')}` / `{gate.get('qrtr_registry_service74_text_positive')}` / `{gate.get('qrtr_registry_qmi_text_positive')}`",
        f"- proc_net_qrtr open/bytes/lines: `{gate.get('qrtr_registry_proc_net_qrtr_open_counts')}` / `{gate.get('qrtr_registry_proc_net_qrtr_bytes')}` / `{gate.get('qrtr_registry_proc_net_qrtr_lines')}`",
        f"- debug qrtr nodes open/bytes/lines: `{gate.get('qrtr_registry_qrtr_nodes_open_counts')}` / `{gate.get('qrtr_registry_qrtr_nodes_bytes')}` / `{gate.get('qrtr_registry_qrtr_nodes_lines')}`",
        f"- debug qrtr services open/bytes/lines: `{gate.get('qrtr_registry_qrtr_services_open_counts')}` / `{gate.get('qrtr_registry_qrtr_services_bytes')}` / `{gate.get('qrtr_registry_qrtr_services_lines')}`",
        f"- no lookup send/service start: `{gate.get('qrtr_registry_no_lookup_send')}` / `{gate.get('qrtr_registry_no_service_start')}`",
        *render_registry_samples(gate.get("qrtr_registry_samples", [])),
        "",
        "## Publication State",
        "",
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
        "- The route did not send QRTR lookup packets, did not start extra services, did not open `/dev/subsys_esoc0`, did not fake ONLINE, and did not write PMIC/GPIO/GDSC controls.",
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
    prev1819.prev1816.prev1796.runner.deploy_property_root = prev1819.prev1816.prev1796.deploy_property_root_serial
    prev1819.prev1816.prev1796.runner.classify_gate = classify_gate
    prev1819.prev1816.prev1796.runner.render_report = render_report
    rc = prev1819.prev1816.prev1796.runner.main(argv)
    prev1819.prev1816.prev1796.sanitize_evidence_dir(DEFAULT_OUT_DIR)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""V1811 one-run WLAN-PD post-PM lower handoff klog discriminator."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import native_wifi_pm_client_return_fetchargs_handoff_v1808 as prev1808
import native_wifi_post_pm_lower_state_observer_handoff_v1806 as prev1806
import native_wifi_wlan_pd_pm_service_count_sample_handoff_v1796 as prev1796


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
CYCLE = "V1811"
V1810_OUT = REPO_ROOT / "tmp" / "wifi" / "v1810-post-pm-lower-handoff-klog-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v1810/dev/__properties__"
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1811-post-pm-lower-handoff-klog-handoff"
DEFAULT_REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1811_POST_PM_LOWER_HANDOFF_KLOG_HANDOFF_2026-06-03.md"
)
TEST_EXPECT_VERSION = "A90 Linux init 0.9.153 (v1810-post-pm-lower-handoff-klog)"
TEST_LOG_PATH = "/cache/native-init-wifi-test-boot-v1810.log"
TEST_SUMMARY_PATH = "/cache/native-init-wifi-test-boot-v1810.summary"
TEST_HELPER_RESULT_PATH = "/cache/native-init-wifi-test-boot-v1810-helper.result"
DMESG_PATTERN = (
    "A90v1810|wlan_pd_post_pm_lower_handoff_klog|"
    "wlan_pd_post_pm_lower_state_observer|pm_init_pm_client_register|"
    "pm_init_pm_client_connect|pm_init_return_path|rc=|arg0=|"
    "wlan_pd_service_object_visible_trigger|wifi_companion_service_notifier|"
    "service_notifier|service-notifier|sysmon_qmi|service 180|service 74|"
    "private_node.subsys|devnode_access|devnode.sdx50m|devnode.modem|"
    "wlan_pd_cnss_nonlog_control_flow|pm_server_uprobe|pm_server_register|"
    "pm-service-init|pm_service_init|pm_service_add_peripheral|first_count=|"
    "second_count=|record=|devnode=|pm-server-register|pm-service|"
    "PeripheralManager|peripheral|vndservicemanager|vndbinder|service-manager|"
    "servicemanager|hwservicemanager|pm_proxy_helper|wlan_pd|wlanmdsp|tftp|"
    "rmt_storage|pd-mapper|qrtr|service 69|wlfw|wlfw_start|"
    "wlfw_service_request|icnss|FW ready|BDF|wlan0|cnss-daemon|"
    "4080000.qcom,mss|soc:qcom,mdm3|Brought out of reset|modem: loading"
)

KLOG_PHASES = (
    "after_holder_start",
    "after_early_listener",
    "after_post_listener_window",
)
KLOG_KEYS = (
    "begin",
    "syslog_available",
    "syslog_errno",
    "count_sysmon_qmi",
    "count_180",
    "count_74",
    "last_sysmon_qmi",
    "last_74",
    "no_esoc0_open",
    "no_fake_online",
    "no_pmic_gpio_gdsc_write",
    "end",
)


def configure_runner() -> None:
    prev1796.CYCLE = CYCLE
    prev1796.V1795_OUT = V1810_OUT
    prev1796.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev1796.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    prev1796.DEFAULT_REPORT_PATH = DEFAULT_REPORT_PATH
    prev1796.TEST_EXPECT_VERSION = TEST_EXPECT_VERSION
    prev1796.TEST_LOG_PATH = TEST_LOG_PATH
    prev1796.TEST_SUMMARY_PATH = TEST_SUMMARY_PATH
    prev1796.TEST_HELPER_RESULT_PATH = TEST_HELPER_RESULT_PATH
    prev1796.DMESG_PATTERN = DMESG_PATTERN
    prev1796.configure_runner()
    prev1796.runner.DEFAULT_SOURCE_MANIFEST = V1810_OUT / "manifest.json"
    prev1796.runner.DEFAULT_TEST_IMAGE = (
        V1810_OUT / "boot_linux_v1810_post_pm_lower_handoff_klog.img"
    )
    prev1796.runner.LOCAL_PROPERTY_ROOT = (
        V1810_OUT / "property-runtime" / "layout" / "dev" / "__properties__"
    )


def intish(value: object) -> int:
    return prev1796.intish(value)


def collect_klog_sample(fields: dict[str, str], phase: str) -> dict[str, str]:
    prefix = f"wlan_pd_post_pm_lower_handoff_klog.{phase}."
    return {"phase": phase, **{key: fields.get(prefix + key, "") for key in KLOG_KEYS}}


def klog_contract_ok(samples: list[dict[str, str]]) -> bool:
    return len(samples) == len(KLOG_PHASES) and all(
        sample.get("begin") == "1" and sample.get("end") == "1"
        for sample in samples
    )


def klog_safety_ok(samples: list[dict[str, str]]) -> bool:
    return all(
        sample.get("no_esoc0_open") == "1"
        and sample.get("no_fake_online") == "1"
        and sample.get("no_pmic_gpio_gdsc_write") == "1"
        for sample in samples
    )


def klog_series(samples: list[dict[str, str]], key: str) -> list[int]:
    return [intish(sample.get(key)) for sample in samples if sample.get(key) != ""]


def collect_gate_fields(fields: dict[str, str]) -> dict[str, Any]:
    details = prev1808.collect_gate_fields(fields)
    samples = [collect_klog_sample(fields, phase) for phase in KLOG_PHASES]
    sysmon_counts = klog_series(samples, "count_sysmon_qmi")
    service180_counts = klog_series(samples, "count_180")
    service74_counts = klog_series(samples, "count_74")
    details.update(
        {
            "klog_samples": samples,
            "klog_contract_ok": klog_contract_ok(samples),
            "klog_safety_ok": klog_safety_ok(samples),
            "klog_sysmon_qmi_counts": ",".join(str(value) for value in sysmon_counts),
            "klog_service180_counts": ",".join(str(value) for value in service180_counts),
            "klog_service74_counts": ",".join(str(value) for value in service74_counts),
            "klog_sysmon_qmi_positive": prev1806.any_positive(sysmon_counts),
            "klog_service180_positive": prev1806.any_positive(service180_counts),
            "klog_service74_positive": prev1806.any_positive(service74_counts),
            "klog_sysmon_qmi_increased": prev1806.series_increases(sysmon_counts),
            "klog_service180_increased": prev1806.series_increases(service180_counts),
            "klog_service74_increased": prev1806.series_increases(service74_counts),
            "service_notifier_early_state": fields.get(
                "wifi_companion_service_notifier_listener.response_curr_state_name",
                "",
            ),
            "service_notifier_late_state": fields.get(
                "wifi_companion_service_notifier_late_listener.response_curr_state_name",
                "",
            ),
            "service_notifier_early_response_success": fields.get(
                "wifi_companion_service_notifier_listener.response_success",
                "",
            ),
            "service_notifier_late_response_success": fields.get(
                "wifi_companion_service_notifier_late_listener.response_success",
                "",
            ),
            "service_notifier_early_indication_seen": fields.get(
                "wifi_companion_service_notifier_listener.indication_seen",
                "",
            ),
            "service_notifier_late_indication_seen": fields.get(
                "wifi_companion_service_notifier_late_listener.indication_seen",
                "",
            ),
        }
    )
    details["klog_servnotif_positive"] = (
        bool(details["klog_service180_positive"])
        or bool(details["klog_service74_positive"])
    )
    details["klog_any_positive"] = (
        bool(details["klog_sysmon_qmi_positive"])
        or bool(details["klog_servnotif_positive"])
    )
    details["klog_any_increased"] = (
        bool(details["klog_sysmon_qmi_increased"])
        or bool(details["klog_service180_increased"])
        or bool(details["klog_service74_increased"])
    )
    details["service_notifier_still_uninit"] = (
        details.get("service_notifier_early_state") == "uninit"
        and details.get("service_notifier_late_state") == "uninit"
        and details.get("service_notifier_early_indication_seen") == "0"
        and details.get("service_notifier_late_indication_seen") == "0"
    )
    return details


def lower_progress(details: dict[str, Any]) -> bool:
    return prev1808.lower_progress(details)


def classify_gate(args: Any,
                  test_flash: dict[str, Any],
                  rollback_result: dict[str, Any],
                  evidence_dir: Path) -> tuple[str, bool, str, dict[str, Any]]:
    test_version = prev1796.runner.fwbase.read_text(evidence_dir, "test-version.stdout.txt")
    helper_fields = prev1796.runner.fwbase.parse_helper_fields(evidence_dir)
    details = collect_gate_fields(helper_fields)
    version_ok = args.expect_test_version in test_version
    rollback_ok = bool(rollback_result.get("ok"))
    helper_contract_seen = prev1796.field_bool(
        helper_fields,
        "wlan_pd_service_object_visible_trigger.begin",
    )
    nonlog_contract_seen = prev1796.field_bool(
        helper_fields,
        "wlan_pd_cnss_nonlog_control_flow.begin",
    )
    late_listener_contract_seen = prev1796.field_bool(
        helper_fields,
        "wifi_companion_service_notifier_late_listener.begin",
    )
    safety_ok = (
        prev1796.safety_ok(helper_fields)
        and bool(details.get("devnode_safety_ok"))
        and bool(details.get("lower_safety_ok"))
        and bool(details.get("klog_safety_ok"))
    )
    details.update(
        {
            "version_ok": version_ok,
            "rollback_ok": rollback_ok,
            "helper_contract_seen": helper_contract_seen,
            "nonlog_contract_seen": nonlog_contract_seen,
            "late_listener_contract_seen": late_listener_contract_seen,
            "safety_ok": safety_ok,
        }
    )

    if not test_flash.get("ok"):
        return f"{args.cycle.lower()}-test-boot-flash-or-verify-failed", False, "test boot flash/verify failed", details
    if not version_ok:
        return f"{args.cycle.lower()}-test-boot-version-missing", False, "expected V1810 test boot version was not collected", details
    if not rollback_ok:
        return f"{args.cycle.lower()}-rollback-failed", False, "rollback to v724 did not verify", details
    if not helper_contract_seen or not nonlog_contract_seen or not late_listener_contract_seen:
        return f"{args.cycle.lower()}-service-object-contract-missing", False, "helper result missed service-object, nonlog, or late listener fields", details
    if not details.get("lower_contract_ok"):
        return f"{args.cycle.lower()}-lower-observer-contract-missing", False, "helper result missed lower-state observer fields", details
    if not details.get("klog_contract_ok"):
        return f"{args.cycle.lower()}-klog-observer-contract-missing", False, "helper result missed post-PM lower handoff klog observer fields", details
    if not safety_ok:
        details["post_pm_lower_handoff_klog_label"] = "safety-regression"
        return f"{args.cycle.lower()}-safety-regression", False, "one or more hard-stop safety fields regressed", details

    if lower_progress(details):
        lower_label = "lower-progress"
    elif prev1808.stable_offlining(details):
        lower_label = "stable-mdm3-offlining"
    else:
        lower_label = "lower-state-incomplete"
    details["post_pm_lower_state_label"] = lower_label

    if not prev1806.pm_vote_boundary_reached(details):
        label = "pm-vote-boundary-incomplete"
        reason = "PM list/register/client-connect boundary was not fully observed in this run"
    elif lower_label == "lower-progress":
        label = "lower-progress"
        reason = "post-PM lower-state sampler observed mdm3/IRQ/MHI/WLFW/wlan0 progress"
    elif not bool(details.get("pm_client_return_fetchargs_seen")):
        label = "pm-client-return-fetchargs-missing"
        reason = "PM client retcheck hits were present but return-value fetchargs were missing or unparsable"
    elif bool(details.get("pm_client_return_nonzero")):
        label = "pm-client-return-error"
        reason = "PM client register/connect return-value fetchargs reported a non-zero return"
    elif bool(details.get("klog_servnotif_positive")) and bool(details.get("service_notifier_still_uninit")):
        label = "servnotif-klog-progress-still-uninit"
        reason = "service-notifier klog count was present while QRTR service-notifier state remained uninit"
    elif bool(details.get("klog_sysmon_qmi_positive")) and not bool(details.get("klog_servnotif_positive")):
        label = "sysmon-klog-progress-servnotif-absent"
        reason = "sysmon_qmi klog count was present, but service-notifier 180/74 klog counts were absent"
    elif not bool(details.get("klog_any_positive")):
        label = "servnotif-klog-absent"
        reason = "PM-client returns were zero and no sysmon/service-notifier klog counts appeared before rollback"
    elif bool(details.get("klog_servnotif_positive")):
        label = "servnotif-klog-progress-state-review"
        reason = "service-notifier klog counts were present but listener state did not match the fixed uninit label"
    else:
        label = "post-pm-lower-handoff-klog-incomplete"
        reason = "post-PM lower handoff klog samples did not match a fixed label"

    if not bool(details.get("pm_client_return_fetchargs_seen")):
        details["pm_client_return_label"] = "pm-client-return-fetchargs-missing"
    elif bool(details.get("pm_client_return_nonzero")):
        details["pm_client_return_label"] = "pm-client-return-error"
    else:
        details["pm_client_return_label"] = "pm-client-return-success"
    details["post_pm_lower_handoff_klog_label"] = label
    return f"{args.cycle.lower()}-{label}-rollback-pass", True, reason, details


def render_klog_sample(sample: dict[str, str]) -> list[str]:
    return [
        f"- `{sample.get('phase')}` counts sysmon/180/74: `{sample.get('count_sysmon_qmi')}` / `{sample.get('count_180')}` / `{sample.get('count_74')}`",
        f"- `{sample.get('phase')}` syslog/errno/safety: `{sample.get('syslog_available')}` / `{sample.get('syslog_errno')}` / `{sample.get('no_esoc0_open')},{sample.get('no_fake_online')},{sample.get('no_pmic_gpio_gdsc_write')}`",
        f"- `{sample.get('phase')}` last sysmon: `{sample.get('last_sysmon_qmi')}`",
        f"- `{sample.get('phase')}` last service74: `{sample.get('last_74')}`",
    ]


def render_report(result: dict[str, Any]) -> str:
    gate = result.get("gate", {})
    property_deploy = result.get("property_deploy", {})
    cycle = str(result.get("cycle", CYCLE))
    lower = gate.get("lower_observer", {})
    klog_lines = [
        line
        for sample in gate.get("klog_samples", [])
        for line in render_klog_sample(sample)
    ]
    lines = [
        f"# Native Init {cycle} Post-PM Lower Handoff Klog Handoff",
        "",
        "## Summary",
        "",
        f"- Cycle: `{cycle}`",
        "- Type: one-run rollbackable WLAN-PD post-PM lower handoff klog discriminator",
        f"- Decision: `{result['decision']}`",
        f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
        f"- Reason: {result['reason']}",
        f"- Evidence: `{result['out_dir']}`",
        f"- Rollback attempt: `{result.get('rollback', {}).get('attempt')}`",
        f"- Rollback ok: `{result.get('rollback', {}).get('ok')}`",
        "",
        "## Gate Label",
        "",
        f"- post-PM lower handoff klog label: `{gate.get('post_pm_lower_handoff_klog_label')}`",
        f"- post-PM lower-state label: `{gate.get('post_pm_lower_state_label')}`",
        f"- PM-client return label: `{gate.get('pm_client_return_label')}`",
        f"- PM-service projection label: `{gate.get('pm_service_devnode_projection_label')}`",
        f"- safety ok: `{gate.get('safety_ok')}`",
        "",
        "## Klog Samples",
        "",
        f"- contract/safety: `{gate.get('klog_contract_ok')}` / `{gate.get('klog_safety_ok')}`",
        f"- sysmon counts positive/increased: `{gate.get('klog_sysmon_qmi_counts')}` / `{gate.get('klog_sysmon_qmi_positive')}` / `{gate.get('klog_sysmon_qmi_increased')}`",
        f"- service 180 counts positive/increased: `{gate.get('klog_service180_counts')}` / `{gate.get('klog_service180_positive')}` / `{gate.get('klog_service180_increased')}`",
        f"- service 74 counts positive/increased: `{gate.get('klog_service74_counts')}` / `{gate.get('klog_service74_positive')}` / `{gate.get('klog_service74_increased')}`",
        *klog_lines,
        "",
        "## Service-notifier State",
        "",
        f"- early/late response state: `{gate.get('service_notifier_early_state')}` / `{gate.get('service_notifier_late_state')}`",
        f"- early/late response success: `{gate.get('service_notifier_early_response_success')}` / `{gate.get('service_notifier_late_response_success')}`",
        f"- early/late indication seen: `{gate.get('service_notifier_early_indication_seen')}` / `{gate.get('service_notifier_late_indication_seen')}`",
        f"- still uninit: `{gate.get('service_notifier_still_uninit')}`",
        "",
        "## PM-client Return Values",
        "",
        f"- register/connect/return-path rc: `{gate.get('pm_client_register_rc')}` / `{gate.get('pm_client_connect_rc')}` / `{gate.get('pm_init_return_path_rc')}`",
        f"- return fetchargs seen/nonzero: `{gate.get('pm_client_return_fetchargs_seen')}` / `{gate.get('pm_client_return_nonzero')}`",
        "",
        "## Lower-state Samples",
        "",
        f"- sample total: `{gate.get('lower_sample_total')}`",
        f"- mdm3 states: `{gate.get('lower_mdm3_states')}`",
        f"- mdm status IRQ totals/increased: `{gate.get('lower_mdm_status_irq_totals')}` / `{gate.get('lower_mdm_status_irq_increased')}`",
        f"- MHI counts/pipes/present: `{gate.get('lower_mhi_device_counts')}` / `{gate.get('lower_mhi_pipe_exists')}` / `{gate.get('lower_mhi_present')}`",
        f"- wlan0 samples/present: `{gate.get('lower_wlan0_exists')}` / `{gate.get('lower_wlan0_present')}`",
        f"- WLFW service69 progress: `{gate.get('lower_service69_progress')}`",
        *prev1806.render_phase("after_holder_start", lower.get("after_holder_start", {})),
        *prev1806.render_phase("post_listener_window", lower.get("post_listener_window", {})),
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
        "- Stop after this one label; do not proceed to Wi-Fi HAL/scan/connect unless lower progress reaches WLFW/wlan0 readiness first.",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    configure_runner()
    prev1796.runner.deploy_property_root = prev1796.deploy_property_root_serial
    prev1796.runner.classify_gate = classify_gate
    prev1796.runner.render_report = render_report
    rc = prev1796.runner.main(argv)
    prev1796.sanitize_evidence_dir(DEFAULT_OUT_DIR)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())

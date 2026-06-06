#!/usr/bin/env python3
"""V1814 one-run service-notifier 74 raw klog handoff."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import native_wifi_post_pm_lower_handoff_klog_handoff_v1811 as prev1811
import native_wifi_post_pm_lower_state_observer_handoff_v1806 as prev1806
import native_wifi_wlan_pd_pm_service_count_sample_handoff_v1796 as prev1796


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
CYCLE = "V1814"
V1813_OUT = REPO_ROOT / "tmp" / "wifi" / "v1813-service74-raw-klog-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v1813/dev/__properties__"
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1814-service74-raw-klog-handoff"
DEFAULT_REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1814_SERVICE74_RAW_KLOG_HANDOFF_2026-06-03.md"
)
TEST_EXPECT_VERSION = "A90 Linux init 0.9.154 (v1813-service74-raw-klog)"
TEST_LOG_PATH = "/cache/native-init-wifi-test-boot-v1813.log"
TEST_SUMMARY_PATH = "/cache/native-init-wifi-test-boot-v1813.summary"
TEST_HELPER_RESULT_PATH = "/cache/native-init-wifi-test-boot-v1813-helper.result"
DMESG_PATTERN = (
    "A90v1813|wlan_pd_post_pm_lower_handoff_klog|raw_count_|last_180|"
    "service_notifier|service-notifier|sysmon_qmi|service 180|service 74|"
    "wlan_pd_post_pm_lower_state_observer|pm_init_pm_client_register|"
    "pm_init_pm_client_connect|pm_init_return_path|rc=|wlan_pd|wlanmdsp|"
    "qrtr|service 69|wlfw|wlfw_start|FW ready|BDF|wlan0|cnss-daemon|"
    "4080000.qcom,mss|soc:qcom,mdm3|Brought out of reset|modem: loading"
)

RAW_KEYS = (
    "raw_count_service_notifier_colon",
    "raw_count_service_notifier_new_server",
    "raw_count_qmi_handle",
    "raw_count_180_service_text",
    "raw_count_74_service_text",
    "raw_count_wlan_pd_text",
    "last_180",
)


def configure_runner() -> None:
    prev1796.CYCLE = CYCLE
    prev1796.V1795_OUT = V1813_OUT
    prev1796.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev1796.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    prev1796.DEFAULT_REPORT_PATH = DEFAULT_REPORT_PATH
    prev1796.TEST_EXPECT_VERSION = TEST_EXPECT_VERSION
    prev1796.TEST_LOG_PATH = TEST_LOG_PATH
    prev1796.TEST_SUMMARY_PATH = TEST_SUMMARY_PATH
    prev1796.TEST_HELPER_RESULT_PATH = TEST_HELPER_RESULT_PATH
    prev1796.DMESG_PATTERN = DMESG_PATTERN
    prev1796.configure_runner()
    prev1796.runner.DEFAULT_SOURCE_MANIFEST = V1813_OUT / "manifest.json"
    prev1796.runner.DEFAULT_TEST_IMAGE = V1813_OUT / "boot_linux_v1813_service74_raw_klog.img"
    prev1796.runner.LOCAL_PROPERTY_ROOT = (
        V1813_OUT / "property-runtime" / "layout" / "dev" / "__properties__"
    )


def intish(value: object) -> int:
    return prev1796.intish(value)


def raw_sample(fields: dict[str, str], phase: str) -> dict[str, str]:
    prefix = f"wlan_pd_post_pm_lower_handoff_klog.{phase}."
    return {"phase": phase, **{key: fields.get(prefix + key, "") for key in RAW_KEYS}}


def series(samples: list[dict[str, str]], key: str) -> list[int]:
    return [intish(sample.get(key)) for sample in samples if sample.get(key) != ""]


def collect_gate_fields(fields: dict[str, str]) -> dict[str, Any]:
    details = prev1811.collect_gate_fields(fields)
    samples = [raw_sample(fields, phase) for phase in prev1811.KLOG_PHASES]
    raw_74 = series(samples, "raw_count_74_service_text")
    raw_180 = series(samples, "raw_count_180_service_text")
    raw_notifier = series(samples, "raw_count_service_notifier_colon")
    raw_new_server = series(samples, "raw_count_service_notifier_new_server")
    raw_qmi_handle = series(samples, "raw_count_qmi_handle")
    raw_wlan_pd = series(samples, "raw_count_wlan_pd_text")
    details.update(
        {
            "raw_klog_samples": samples,
            "raw_service74_text_counts": ",".join(str(value) for value in raw_74),
            "raw_service180_text_counts": ",".join(str(value) for value in raw_180),
            "raw_service_notifier_colon_counts": ",".join(str(value) for value in raw_notifier),
            "raw_service_notifier_new_server_counts": ",".join(str(value) for value in raw_new_server),
            "raw_qmi_handle_counts": ",".join(str(value) for value in raw_qmi_handle),
            "raw_wlan_pd_text_counts": ",".join(str(value) for value in raw_wlan_pd),
            "raw_service74_text_positive": prev1806.any_positive(raw_74),
            "raw_service180_text_positive": prev1806.any_positive(raw_180),
            "raw_service74_text_increased": prev1806.series_increases(raw_74),
            "raw_service180_text_increased": prev1806.series_increases(raw_180),
        }
    )
    return details


def service_notifier_state_progress(details: dict[str, Any]) -> bool:
    return (
        details.get("service_notifier_early_state") != "uninit"
        or details.get("service_notifier_late_state") != "uninit"
        or details.get("service_notifier_early_indication_seen") != "0"
        or details.get("service_notifier_late_indication_seen") != "0"
    )


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
            "safety_ok": safety_ok,
        }
    )

    if not test_flash.get("ok"):
        return f"{args.cycle.lower()}-test-boot-flash-or-verify-failed", False, "test boot flash/verify failed", details
    if not version_ok:
        return f"{args.cycle.lower()}-test-boot-version-missing", False, "expected V1813 test boot version was not collected", details
    if not rollback_ok:
        return f"{args.cycle.lower()}-rollback-failed", False, "rollback to v724 did not verify", details
    if not helper_contract_seen or not details.get("lower_contract_ok") or not details.get("klog_contract_ok"):
        return f"{args.cycle.lower()}-observer-contract-missing", False, "helper result missed service-object, lower, or klog observer fields", details
    if not safety_ok:
        details["service74_raw_klog_label"] = "safety-regression"
        return f"{args.cycle.lower()}-safety-regression", False, "one or more hard-stop safety fields regressed", details

    if (
        prev1811.lower_progress(details)
        or bool(details.get("klog_service74_positive"))
        or service_notifier_state_progress(details)
    ):
        label = "service74-progress"
        reason = "service 74, service-notifier state, WLFW, or wlan0 progressed"
    elif bool(details.get("raw_service74_text_positive")) and not bool(details.get("klog_service74_positive")):
        label = "service74-parser-miss"
        reason = "raw service 74 text was present but exact service 74 parser count remained zero"
    elif (
        bool(details.get("klog_service180_positive"))
        and bool(details.get("raw_service180_text_positive"))
        and not bool(details.get("raw_service74_text_positive"))
    ):
        label = "service74-raw-absent"
        reason = "service 180 was present, but raw service 74 text and exact service 74 count remained absent"
    else:
        label = "service74-raw-klog-incomplete"
        reason = "raw service 74 klog evidence did not match a fixed absence/progress/parser label"

    if prev1811.lower_progress(details):
        details["post_pm_lower_state_label"] = "lower-progress"
    elif prev1811.prev1808.stable_offlining(details):
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
    details["service74_raw_klog_label"] = label
    return f"{args.cycle.lower()}-{label}-rollback-pass", True, reason, details


def render_raw_sample(sample: dict[str, str]) -> list[str]:
    return [
        f"- `{sample.get('phase')}` raw notifier/new/qmi: `{sample.get('raw_count_service_notifier_colon')}` / `{sample.get('raw_count_service_notifier_new_server')}` / `{sample.get('raw_count_qmi_handle')}`",
        f"- `{sample.get('phase')}` raw 180/74/wlan_pd: `{sample.get('raw_count_180_service_text')}` / `{sample.get('raw_count_74_service_text')}` / `{sample.get('raw_count_wlan_pd_text')}`",
        f"- `{sample.get('phase')}` last 180: `{sample.get('last_180')}`",
    ]


def render_report(result: dict[str, Any]) -> str:
    gate = result.get("gate", {})
    property_deploy = result.get("property_deploy", {})
    raw_lines = [
        line
        for sample in gate.get("raw_klog_samples", [])
        for line in render_raw_sample(sample)
    ]
    lines = [
        "# Native Init V1814 Service-notifier 74 Raw Klog Handoff",
        "",
        "## Summary",
        "",
        "- Cycle: `V1814`",
        "- Type: one-run rollbackable service-notifier 74 raw klog discriminator",
        f"- Decision: `{result['decision']}`",
        f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
        f"- Reason: {result['reason']}",
        f"- Evidence: `{result['out_dir']}`",
        f"- Rollback attempt: `{result.get('rollback', {}).get('attempt')}`",
        f"- Rollback ok: `{result.get('rollback', {}).get('ok')}`",
        "",
        "## Gate Label",
        "",
        f"- service74 raw klog label: `{gate.get('service74_raw_klog_label')}`",
        f"- lower handoff klog label: `{gate.get('post_pm_lower_handoff_klog_label')}`",
        f"- PM-client return label: `{gate.get('pm_client_return_label')}`",
        f"- lower-state label: `{gate.get('post_pm_lower_state_label')}`",
        f"- safety ok: `{gate.get('safety_ok')}`",
        "",
        "## Raw Klog Counters",
        "",
        f"- raw service-notifier/new-server/qmi counts: `{gate.get('raw_service_notifier_colon_counts')}` / `{gate.get('raw_service_notifier_new_server_counts')}` / `{gate.get('raw_qmi_handle_counts')}`",
        f"- raw service180/service74/wlan_pd counts: `{gate.get('raw_service180_text_counts')}` / `{gate.get('raw_service74_text_counts')}` / `{gate.get('raw_wlan_pd_text_counts')}`",
        f"- raw service74 positive/increased: `{gate.get('raw_service74_text_positive')}` / `{gate.get('raw_service74_text_increased')}`",
        f"- exact service180/service74 counts: `{gate.get('klog_service180_counts')}` / `{gate.get('klog_service74_counts')}`",
        *raw_lines,
        "",
        "## Service-notifier And Lower State",
        "",
        f"- early/late state: `{gate.get('service_notifier_early_state')}` / `{gate.get('service_notifier_late_state')}`",
        f"- early/late indication seen: `{gate.get('service_notifier_early_indication_seen')}` / `{gate.get('service_notifier_late_indication_seen')}`",
        f"- mdm3/MHI/WLFW69/wlan0: `{gate.get('lower_mdm3_states')}` / `{gate.get('lower_mhi_present')}` / `{gate.get('lower_service69_progress')}` / `{gate.get('lower_wlan0_present')}`",
        "",
        "## PM-client Return Values",
        "",
        f"- register/connect/return-path rc: `{gate.get('pm_client_register_rc')}` / `{gate.get('pm_client_connect_rc')}` / `{gate.get('pm_init_return_path_rc')}`",
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
    prev1796.runner.deploy_property_root = prev1796.deploy_property_root_serial
    prev1796.runner.classify_gate = classify_gate
    prev1796.runner.render_report = render_report
    rc = prev1796.runner.main(argv)
    prev1796.sanitize_evidence_dir(DEFAULT_OUT_DIR)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())

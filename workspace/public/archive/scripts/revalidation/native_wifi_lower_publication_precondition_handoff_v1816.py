#!/usr/bin/env python3
"""V1816 one-run lower publication precondition handoff."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import native_wifi_service74_raw_klog_handoff_v1814 as prev1814
import native_wifi_post_pm_lower_state_observer_handoff_v1806 as prev1806
import native_wifi_wlan_pd_pm_service_count_sample_handoff_v1796 as prev1796


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
CYCLE = "V1816"
V1815_OUT = REPO_ROOT / "tmp" / "wifi" / "v1815-lower-publication-precondition-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v1815/dev/__properties__"
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1816-lower-publication-precondition-handoff"
DEFAULT_REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1816_LOWER_PUBLICATION_PRECONDITION_HANDOFF_2026-06-03.md"
)
TEST_EXPECT_VERSION = "A90 Linux init 0.9.155 (v1815-lower-publication-precondition)"
TEST_LOG_PATH = "/cache/native-init-wifi-test-boot-v1815.log"
TEST_SUMMARY_PATH = "/cache/native-init-wifi-test-boot-v1815.summary"
TEST_HELPER_RESULT_PATH = "/cache/native-init-wifi-test-boot-v1815-helper.result"
DMESG_PATTERN = (
    "A90v1815|wlan_pd_post_pm_lower_handoff_klog|raw_count_|last_wlfw|"
    "pd-mapper|pd_mapper|subsys|subsystem|pil|q6v5|qmi|QMI|wlfw|WLFW|"
    "service_notifier|service-notifier|service 180|service 74|wlan_pd|"
    "pm_init_pm_client_register|pm_init_pm_client_connect|pm_init_return_path|"
    "qrtr|service 69|FW ready|BDF|wlan0|cnss-daemon|"
    "4080000.qcom,mss|soc:qcom,mdm3|Brought out of reset|modem: loading"
)

PRECONDITION_KEYS = (
    "raw_count_pd_mapper_text",
    "raw_count_subsys_text",
    "raw_count_pil_text",
    "raw_count_qmi_text",
    "raw_count_wlfw_text",
    "last_wlan_pd",
    "last_pd_mapper",
    "last_subsys",
    "last_pil",
    "last_qmi",
    "last_wlfw",
)


def configure_runner() -> None:
    prev1796.CYCLE = CYCLE
    prev1796.V1795_OUT = V1815_OUT
    prev1796.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev1796.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    prev1796.DEFAULT_REPORT_PATH = DEFAULT_REPORT_PATH
    prev1796.TEST_EXPECT_VERSION = TEST_EXPECT_VERSION
    prev1796.TEST_LOG_PATH = TEST_LOG_PATH
    prev1796.TEST_SUMMARY_PATH = TEST_SUMMARY_PATH
    prev1796.TEST_HELPER_RESULT_PATH = TEST_HELPER_RESULT_PATH
    prev1796.DMESG_PATTERN = DMESG_PATTERN
    prev1796.configure_runner()
    prev1796.runner.DEFAULT_SOURCE_MANIFEST = V1815_OUT / "manifest.json"
    prev1796.runner.DEFAULT_TEST_IMAGE = (
        V1815_OUT / "boot_linux_v1815_lower_publication_precondition.img"
    )
    prev1796.runner.LOCAL_PROPERTY_ROOT = (
        V1815_OUT / "property-runtime" / "layout" / "dev" / "__properties__"
    )


def intish(value: object) -> int:
    return prev1796.intish(value)


def count_csv_positive(value: object) -> bool:
    return any(intish(part) > 0 for part in str(value or "").split(",") if part.strip())


def sample(fields: dict[str, str], phase: str) -> dict[str, str]:
    prefix = f"wlan_pd_post_pm_lower_handoff_klog.{phase}."
    return {"phase": phase, **{key: fields.get(prefix + key, "") for key in PRECONDITION_KEYS}}


def series(samples: list[dict[str, str]], key: str) -> list[int]:
    return [intish(item.get(key)) for item in samples if item.get(key) != ""]


def collect_gate_fields(fields: dict[str, str]) -> dict[str, Any]:
    details = prev1814.collect_gate_fields(fields)
    samples = [sample(fields, phase) for phase in prev1814.prev1811.KLOG_PHASES]
    pd_mapper = series(samples, "raw_count_pd_mapper_text")
    subsys = series(samples, "raw_count_subsys_text")
    pil = series(samples, "raw_count_pil_text")
    qmi = series(samples, "raw_count_qmi_text")
    wlfw = series(samples, "raw_count_wlfw_text")
    details.update(
        {
            "precondition_samples": samples,
            "raw_pd_mapper_counts": ",".join(str(value) for value in pd_mapper),
            "raw_subsys_counts": ",".join(str(value) for value in subsys),
            "raw_pil_counts": ",".join(str(value) for value in pil),
            "raw_qmi_counts": ",".join(str(value) for value in qmi),
            "raw_wlfw_counts": ",".join(str(value) for value in wlfw),
            "raw_pd_mapper_positive": prev1806.any_positive(pd_mapper),
            "raw_subsys_positive": prev1806.any_positive(subsys),
            "raw_pil_positive": prev1806.any_positive(pil),
            "raw_qmi_positive": prev1806.any_positive(qmi),
            "raw_wlfw_positive": prev1806.any_positive(wlfw),
        }
    )
    details["preconditions_visible"] = (
        bool(details.get("raw_qmi_positive"))
        or bool(details.get("raw_subsys_positive"))
        or bool(details.get("raw_pil_positive"))
        or bool(details.get("raw_pd_mapper_positive"))
    )
    details["raw_wlan_pd_text_positive"] = count_csv_positive(details.get("raw_wlan_pd_text_counts"))
    return details


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
        return f"{args.cycle.lower()}-test-boot-version-missing", False, "expected V1815 test boot version was not collected", details
    if not rollback_ok:
        return f"{args.cycle.lower()}-rollback-failed", False, "rollback to v724 did not verify", details
    if not helper_contract_seen or not details.get("lower_contract_ok") or not details.get("klog_contract_ok"):
        return f"{args.cycle.lower()}-observer-contract-missing", False, "helper result missed service-object, lower, or klog observer fields", details
    if not safety_ok:
        details["lower_publication_precondition_label"] = "safety-regression"
        return f"{args.cycle.lower()}-safety-regression", False, "one or more hard-stop safety fields regressed", details

    if (
        prev1814.prev1811.lower_progress(details)
        or bool(details.get("klog_service74_positive"))
        or bool(details.get("raw_service74_text_positive"))
        or bool(details.get("raw_wlan_pd_text_positive"))
        or prev1814.service_notifier_state_progress(details)
    ):
        label = "lower-publication-progress"
        reason = "service 74, wlan_pd, service-notifier state, WLFW service 69, MHI, or wlan0 progressed"
    elif (
        bool(details.get("klog_service180_positive"))
        and not bool(details.get("raw_service74_text_positive"))
        and not bool(details.get("raw_wlan_pd_text_positive"))
        and bool(details.get("preconditions_visible"))
    ):
        label = "service74-raw-absent-preconditions-visible"
        reason = "service 180 and lower precondition klogs were visible, but raw service 74 and wlan_pd text remained absent"
    elif bool(details.get("preconditions_visible")):
        label = "precondition-parser-gap"
        reason = "lower precondition text was visible but did not match the fixed service74 absence/progress labels"
    else:
        label = "lower-publication-precondition-incomplete"
        reason = "lower publication precondition evidence did not match a fixed label"

    if prev1814.prev1811.lower_progress(details):
        details["post_pm_lower_state_label"] = "lower-progress"
    elif prev1814.prev1811.prev1808.stable_offlining(details):
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
    if (
        prev1814.prev1811.lower_progress(details)
        or bool(details.get("klog_service74_positive"))
        or bool(details.get("raw_service74_text_positive"))
        or bool(details.get("raw_wlan_pd_text_positive"))
        or prev1814.service_notifier_state_progress(details)
    ):
        details["service74_raw_klog_label"] = "service74-progress"
    elif bool(details.get("raw_service74_text_positive")) and not bool(details.get("klog_service74_positive")):
        details["service74_raw_klog_label"] = "service74-parser-miss"
    elif bool(details.get("klog_service180_positive")) and not bool(details.get("raw_service74_text_positive")):
        details["service74_raw_klog_label"] = "service74-raw-absent"
    else:
        details["service74_raw_klog_label"] = "service74-raw-klog-incomplete"
    details["lower_publication_precondition_label"] = label
    return f"{args.cycle.lower()}-{label}-rollback-pass", True, reason, details


def render_sample(item: dict[str, str]) -> list[str]:
    return [
        f"- `{item.get('phase')}` pd-mapper/subsys/pil/qmi/wlfw: `{item.get('raw_count_pd_mapper_text')}` / `{item.get('raw_count_subsys_text')}` / `{item.get('raw_count_pil_text')}` / `{item.get('raw_count_qmi_text')}` / `{item.get('raw_count_wlfw_text')}`",
        f"- `{item.get('phase')}` last qmi/wlfw/wlan_pd: `{item.get('last_qmi')}` / `{item.get('last_wlfw')}` / `{item.get('last_wlan_pd')}`",
    ]


def render_report(result: dict[str, Any]) -> str:
    gate = result.get("gate", {})
    property_deploy = result.get("property_deploy", {})
    sample_lines = [
        line
        for item in gate.get("precondition_samples", [])
        for line in render_sample(item)
    ]
    lines = [
        "# Native Init V1816 Lower Publication Precondition Handoff",
        "",
        "## Summary",
        "",
        "- Cycle: `V1816`",
        "- Type: one-run rollbackable lower publication precondition discriminator",
        f"- Decision: `{result['decision']}`",
        f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
        f"- Reason: {result['reason']}",
        f"- Evidence: `{result['out_dir']}`",
        f"- Rollback attempt: `{result.get('rollback', {}).get('attempt')}`",
        f"- Rollback ok: `{result.get('rollback', {}).get('ok')}`",
        "",
        "## Gate Label",
        "",
        f"- lower publication label: `{gate.get('lower_publication_precondition_label')}`",
        f"- service74 raw label: `{gate.get('service74_raw_klog_label')}`",
        f"- PM-client return label: `{gate.get('pm_client_return_label')}`",
        f"- lower-state label: `{gate.get('post_pm_lower_state_label')}`",
        f"- safety ok: `{gate.get('safety_ok')}`",
        "",
        "## Precondition Counters",
        "",
        f"- pd-mapper/subsys/pil/qmi/wlfw: `{gate.get('raw_pd_mapper_counts')}` / `{gate.get('raw_subsys_counts')}` / `{gate.get('raw_pil_counts')}` / `{gate.get('raw_qmi_counts')}` / `{gate.get('raw_wlfw_counts')}`",
        f"- positives pd-mapper/subsys/pil/qmi/wlfw: `{gate.get('raw_pd_mapper_positive')}` / `{gate.get('raw_subsys_positive')}` / `{gate.get('raw_pil_positive')}` / `{gate.get('raw_qmi_positive')}` / `{gate.get('raw_wlfw_positive')}`",
        f"- service180/service74/wlan_pd raw: `{gate.get('raw_service180_text_counts')}` / `{gate.get('raw_service74_text_counts')}` / `{gate.get('raw_wlan_pd_text_counts')}`",
        f"- wlan_pd raw positive: `{gate.get('raw_wlan_pd_text_positive')}`",
        "- Broad WLFW text is precondition context only; WLFW service 69 or `wlan0` are the lower-progress gates.",
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
    prev1796.runner.deploy_property_root = prev1796.deploy_property_root_serial
    prev1796.runner.classify_gate = classify_gate
    prev1796.runner.render_report = render_report
    rc = prev1796.runner.main(argv)
    prev1796.sanitize_evidence_dir(DEFAULT_OUT_DIR)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())

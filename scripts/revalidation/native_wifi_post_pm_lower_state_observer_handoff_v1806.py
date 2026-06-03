#!/usr/bin/env python3
"""V1806 one-run WLAN-PD post-PM lower-state observer handoff."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import native_wifi_pm_service_devnode_projection_handoff_v1801 as prev1801
import native_wifi_post_pm_success_wlfw_classifier_v1802 as prev1802
import native_wifi_wlfw_qmi_readiness_classifier_v1803 as prev1803
import native_wifi_wlan_pd_pm_service_count_sample_handoff_v1796 as prev1796


REPO_ROOT = Path(__file__).resolve().parents[2]
CYCLE = "V1806"
V1805_OUT = REPO_ROOT / "tmp" / "wifi" / "v1805-post-pm-lower-state-observer-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v1805/dev/__properties__"
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1806-post-pm-lower-state-observer-handoff"
DEFAULT_REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1806_POST_PM_LOWER_STATE_OBSERVER_HANDOFF_2026-06-03.md"
)
TEST_EXPECT_VERSION = "A90 Linux init 0.9.151 (v1805-post-pm-lower-state-observer)"
TEST_LOG_PATH = "/cache/native-init-wifi-test-boot-v1805.log"
TEST_SUMMARY_PATH = "/cache/native-init-wifi-test-boot-v1805.summary"
TEST_HELPER_RESULT_PATH = "/cache/native-init-wifi-test-boot-v1805-helper.result"
DMESG_PATTERN = (
    "A90v1805|wlan_pd_post_pm_lower_state_observer|"
    "wlan_pd_service_object_visible_trigger|private_node.subsys|"
    "devnode_access|devnode.sdx50m|devnode.modem|access_f_ok|lstat_ok|"
    "char_device|wlan_pd_cnss_nonlog_control_flow|pm_server_uprobe|"
    "pm_server_register|pm-service-init|pm_service_init|pm_service_add_peripheral|"
    "first_count=|second_count=|record=|devnode=|pm-server-register|pm-service|"
    "PeripheralManager|peripheral|vndservicemanager|vndbinder|service-manager|"
    "servicemanager|hwservicemanager|pm_proxy_helper|wlan_pd|wlanmdsp|tftp|"
    "rmt_storage|pd-mapper|qrtr|service 69|wlfw|wlfw_start|"
    "wlfw_service_request|icnss|FW ready|BDF|wlan0|cnss-daemon|"
    "4080000.qcom,mss|soc:qcom,mdm3|Brought out of reset|modem: loading"
)

LOWER_PHASES = {
    "after_holder_start": 1,
    "post_listener_window": 12,
}
LOWER_KEYS = [
    "begin",
    "monotonic_ms",
    "mss_state",
    "mss_crash_count",
    "mdm3_state",
    "mdm3_crash_count",
    "mdm_status_irq_present",
    "mdm_status_irq_parsed",
    "mdm_status_irq_total",
    "mdm_errfatal_irq_present",
    "mdm_errfatal_irq_parsed",
    "mdm_errfatal_irq_total",
    "pci_device_count",
    "mhi_device_count",
    "rpmsg_device_count",
    "msm_subsys_device_count",
    "mhi_pipe_exists",
    "wlan0_exists",
    "no_esoc0_open",
    "no_fake_online",
    "no_pmic_gpio_gdsc_write",
    "end",
]


def configure_runner() -> None:
    prev1796.CYCLE = CYCLE
    prev1796.V1795_OUT = V1805_OUT
    prev1796.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev1796.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    prev1796.DEFAULT_REPORT_PATH = DEFAULT_REPORT_PATH
    prev1796.TEST_EXPECT_VERSION = TEST_EXPECT_VERSION
    prev1796.TEST_LOG_PATH = TEST_LOG_PATH
    prev1796.TEST_SUMMARY_PATH = TEST_SUMMARY_PATH
    prev1796.TEST_HELPER_RESULT_PATH = TEST_HELPER_RESULT_PATH
    prev1796.DMESG_PATTERN = DMESG_PATTERN
    prev1796.configure_runner()
    prev1796.runner.DEFAULT_SOURCE_MANIFEST = V1805_OUT / "manifest.json"
    prev1796.runner.DEFAULT_TEST_IMAGE = (
        V1805_OUT / "boot_linux_v1805_post_pm_lower_state_observer.img"
    )
    prev1796.runner.LOCAL_PROPERTY_ROOT = (
        V1805_OUT / "property-runtime" / "layout" / "dev" / "__properties__"
    )


def intish(value: object) -> int:
    return prev1796.intish(value)


def lower_sample_prefix(phase: str, index: int) -> str:
    return f"wlan_pd_post_pm_lower_state_observer.{phase}.sample_{index:02d}."


def collect_lower_sample(fields: dict[str, str], phase: str, index: int) -> dict[str, str]:
    prefix = lower_sample_prefix(phase, index)
    sample = {"phase": phase, "index": str(index)}
    sample.update({key: fields.get(prefix + key, "") for key in LOWER_KEYS})
    return sample


def collect_lower_phase(fields: dict[str, str], phase: str, count: int) -> dict[str, Any]:
    prefix = f"wlan_pd_post_pm_lower_state_observer.{phase}."
    return {
        "begin": fields.get(prefix + "begin", ""),
        "end": fields.get(prefix + "end", ""),
        "sample_count": fields.get(prefix + "sample_count", ""),
        "interval_ms": fields.get(prefix + "interval_ms", ""),
        "no_esoc0_open": fields.get(prefix + "no_esoc0_open", ""),
        "no_fake_online": fields.get(prefix + "no_fake_online", ""),
        "no_pmic_gpio_gdsc_write": fields.get(prefix + "no_pmic_gpio_gdsc_write", ""),
        "samples": [collect_lower_sample(fields, phase, index) for index in range(count)],
    }


def all_samples(details: dict[str, Any]) -> list[dict[str, str]]:
    samples: list[dict[str, str]] = []
    for phase in LOWER_PHASES:
        samples.extend(details.get("lower_observer", {}).get(phase, {}).get("samples", []))
    return samples


def lower_contract_ok(fields: dict[str, str], details: dict[str, Any]) -> bool:
    if fields.get("wifi_companion_start.wlan_pd_post_pm_lower_state_observer.enabled") != "1":
        return False
    observer = details.get("lower_observer", {})
    for phase, count in LOWER_PHASES.items():
        phase_data = observer.get(phase, {})
        if phase != "after_holder_start" and (
            phase_data.get("begin") != "1"
            or phase_data.get("end") != "1"
            or intish(phase_data.get("sample_count")) != count
        ):
            return False
        if len(phase_data.get("samples", [])) != count:
            return False
        for sample in phase_data.get("samples", []):
            if sample.get("begin") != "1" or sample.get("end") != "1":
                return False
    return True


def lower_safety_ok(details: dict[str, Any]) -> bool:
    observer = details.get("lower_observer", {})
    for phase_data in observer.values():
        for key in ("no_esoc0_open", "no_fake_online", "no_pmic_gpio_gdsc_write"):
            value = phase_data.get(key)
            if value and value != "1":
                return False
        for sample in phase_data.get("samples", []):
            for key in ("no_esoc0_open", "no_fake_online", "no_pmic_gpio_gdsc_write"):
                if sample.get(key) != "1":
                    return False
    return True


def unique_values(samples: list[dict[str, str]], key: str) -> list[str]:
    values: list[str] = []
    for sample in samples:
        value = sample.get(key, "")
        if value and value not in values:
            values.append(value)
    return values


def int_series(samples: list[dict[str, str]], key: str) -> list[int]:
    values: list[int] = []
    for sample in samples:
        text = sample.get(key, "")
        if text == "":
            continue
        values.append(intish(text))
    return values


def series_increases(values: list[int]) -> bool:
    if len(values) < 2:
        return False
    baseline = values[0]
    return any(value > baseline for value in values[1:])


def any_positive(values: list[int]) -> bool:
    return any(value > 0 for value in values)


def service69_progress(fields: dict[str, str]) -> bool:
    if intish(fields.get("wlan_pd_service_object_visible_trigger.wlfw_service69_seen")) > 0:
        return True
    case_0 = prev1803.qrtr_case(fields, 0)
    case_1 = prev1803.qrtr_case(fields, 1)
    return (
        intish(case_0.get("readback.service_events")) > 0
        or intish(case_1.get("readback.service_events")) > 0
    )


def collect_gate_fields(fields: dict[str, str]) -> dict[str, Any]:
    details = prev1801.collect_gate_fields(fields)
    lower_observer = {
        phase: collect_lower_phase(fields, phase, count)
        for phase, count in LOWER_PHASES.items()
    }
    samples = [
        sample
        for phase_data in lower_observer.values()
        for sample in phase_data.get("samples", [])
    ]
    mdm3_states = unique_values(samples, "mdm3_state")
    mdm_status_irq_totals = int_series(samples, "mdm_status_irq_total")
    mdm_errfatal_irq_totals = int_series(samples, "mdm_errfatal_irq_total")
    mhi_device_counts = int_series(samples, "mhi_device_count")
    mhi_pipe_exists = int_series(samples, "mhi_pipe_exists")
    wlan0_exists = int_series(samples, "wlan0_exists")
    details.update(
        {
            "lower_observer_enabled": fields.get(
                "wifi_companion_start.wlan_pd_post_pm_lower_state_observer.enabled",
                "",
            ),
            "lower_observer": lower_observer,
            "lower_sample_total": len(samples),
            "lower_mdm3_states": ",".join(mdm3_states),
            "lower_mdm_status_irq_totals": ",".join(str(value) for value in mdm_status_irq_totals),
            "lower_mdm_status_irq_increased": series_increases(mdm_status_irq_totals),
            "lower_mdm_errfatal_irq_totals": ",".join(str(value) for value in mdm_errfatal_irq_totals),
            "lower_mdm_errfatal_irq_increased": series_increases(mdm_errfatal_irq_totals),
            "lower_mhi_device_counts": ",".join(str(value) for value in mhi_device_counts),
            "lower_mhi_present": any_positive(mhi_device_counts) or any_positive(mhi_pipe_exists),
            "lower_mhi_pipe_exists": ",".join(str(value) for value in mhi_pipe_exists),
            "lower_wlan0_exists": ",".join(str(value) for value in wlan0_exists),
            "lower_wlan0_present": any_positive(wlan0_exists),
            "lower_contract_ok": False,
            "lower_safety_ok": False,
            "lower_service69_progress": service69_progress(fields),
            "pm_init_pm_client_register_call": prev1802.event(fields, "pm_init_pm_client_register_call"),
            "pm_init_pm_client_register_retcheck": prev1802.event(fields, "pm_init_pm_client_register_retcheck"),
            "pm_init_pm_client_connect_call": prev1802.event(fields, "pm_init_pm_client_connect_call"),
            "pm_init_pm_client_connect_retcheck": prev1802.event(fields, "pm_init_pm_client_connect_retcheck"),
        }
    )
    if not details.get("pm_service_devnode_projection_label"):
        if intish(details.get("pm_service_add_peripheral_list_commit_hits")) > 0:
            details["pm_service_devnode_projection_label"] = "list-commit-progress"
        elif details.get("private_node_sdx50m_expected") and details.get("private_node_modem_expected"):
            details["pm_service_devnode_projection_label"] = "projection-visible"
        else:
            details["pm_service_devnode_projection_label"] = "projection-incomplete"
    details["lower_contract_ok"] = lower_contract_ok(fields, details)
    details["lower_safety_ok"] = lower_safety_ok(details)
    return details


def mdm3_left_offlining(details: dict[str, Any]) -> bool:
    states = [
        state.strip()
        for state in str(details.get("lower_mdm3_states") or "").split(",")
        if state.strip()
    ]
    return any(state != "OFFLINING" for state in states)


def pm_vote_boundary_reached(details: dict[str, Any]) -> bool:
    return (
        intish(details.get("pm_service_add_peripheral_list_commit_hits")) > 0
        and intish(details.get("pm_server_success_return_hits")) > 0
        and intish(details.get("pm_init_pm_client_connect_retcheck", {}).get("hit_count")) > 0
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
        return f"{args.cycle.lower()}-test-boot-version-missing", False, "expected V1805 test boot version was not collected", details
    if not rollback_ok:
        return f"{args.cycle.lower()}-rollback-failed", False, "rollback to v724 did not verify", details
    if not helper_contract_seen or not nonlog_contract_seen or not late_listener_contract_seen:
        return f"{args.cycle.lower()}-service-object-contract-missing", False, "helper result missed service-object, nonlog, or late listener fields", details
    if not details.get("lower_contract_ok"):
        return f"{args.cycle.lower()}-lower-observer-contract-missing", False, "helper result missed V1805 lower-state observer fields", details
    if not safety_ok:
        details["post_pm_lower_state_label"] = "safety-regression"
        return f"{args.cycle.lower()}-safety-regression", False, "one or more hard-stop safety fields regressed", details

    if not pm_vote_boundary_reached(details):
        label = "pm-vote-boundary-incomplete"
        reason = "PM list/register/client-connect boundary was not fully observed in this run"
    elif (
        mdm3_left_offlining(details)
        or bool(details.get("lower_mdm_status_irq_increased"))
        or bool(details.get("lower_mhi_present"))
        or bool(details.get("lower_service69_progress"))
        or bool(details.get("lower_wlan0_present"))
    ):
        label = "lower-progress"
        reason = "post-PM lower-state sampler observed mdm3/IRQ/MHI/WLFW/wlan0 progress"
    elif (
        str(details.get("lower_mdm3_states") or "") == "OFFLINING"
        and not bool(details.get("lower_mdm_status_irq_increased"))
        and not bool(details.get("lower_mhi_present"))
        and not bool(details.get("lower_service69_progress"))
        and not bool(details.get("lower_wlan0_present"))
    ):
        label = "stable-mdm3-offlining"
        reason = "PM vote boundary was reached, but compact lower-state samples stayed at mdm3 OFFLINING with no MHI, WLFW service 69, or wlan0"
    else:
        label = "lower-state-incomplete"
        reason = "post-PM lower-state sampler produced rollback-verified evidence outside the fixed progress/stall labels"

    details["post_pm_lower_state_label"] = label
    return f"{args.cycle.lower()}-{label}-rollback-pass", True, reason, details


def render_event(name: str, data: dict[str, str]) -> list[str]:
    return [
        f"- `{name}` hits/registered/enabled: `{data.get('hit_count')}` / `{data.get('registered')}` / `{data.get('enabled')}`",
        f"- `{name}` first hit: `{data.get('first_hit_line')}`",
    ]


def render_phase(name: str, data: dict[str, Any]) -> list[str]:
    samples = data.get("samples", [])
    first = samples[0] if samples else {}
    last = samples[-1] if samples else {}
    phase_begin = data.get("begin") or ("sample-only" if samples else "")
    phase_end = data.get("end") or ("sample-only" if samples else "")
    return [
        f"- `{name}` begin/end/count/interval: `{phase_begin}` / `{phase_end}` / `{data.get('sample_count')}` / `{data.get('interval_ms')}`",
        f"- `{name}` first mdm3/MHI/wlan0/irq: `{first.get('mdm3_state')}` / `{first.get('mhi_device_count')}` pipe `{first.get('mhi_pipe_exists')}` / `{first.get('wlan0_exists')}` / `{first.get('mdm_status_irq_total')}`",
        f"- `{name}` last mdm3/MHI/wlan0/irq: `{last.get('mdm3_state')}` / `{last.get('mhi_device_count')}` pipe `{last.get('mhi_pipe_exists')}` / `{last.get('wlan0_exists')}` / `{last.get('mdm_status_irq_total')}`",
    ]


def render_report(result: dict[str, Any]) -> str:
    gate = result.get("gate", {})
    property_deploy = result.get("property_deploy", {})
    cycle = str(result.get("cycle", CYCLE))
    lower = gate.get("lower_observer", {})
    lines = [
        f"# Native Init {cycle} Post-PM Lower-state Observer Handoff",
        "",
        "## Summary",
        "",
        f"- Cycle: `{cycle}`",
        "- Type: one-run rollbackable WLAN-PD post-PM lower-state discriminator",
        f"- Decision: `{result['decision']}`",
        f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
        f"- Reason: {result['reason']}",
        f"- Evidence: `{result['out_dir']}`",
        f"- Reclassified existing evidence: `{result.get('reclassified_from_existing_evidence', False)}`",
        f"- Rollback attempt: `{result.get('rollback', {}).get('attempt')}`",
        f"- Rollback ok: `{result.get('rollback', {}).get('ok')}`",
        "",
        "## Gate Label",
        "",
        f"- post-PM lower-state label: `{gate.get('post_pm_lower_state_label')}`",
        f"- PM-service projection label: `{gate.get('pm_service_devnode_projection_label')}`",
        f"- helper label: `{gate.get('helper_label')}`",
        f"- PM server label: `{gate.get('pm_server_label')}`",
        f"- lower observer enabled/contract/safety: `{gate.get('lower_observer_enabled')}` / `{gate.get('lower_contract_ok')}` / `{gate.get('lower_safety_ok')}`",
        f"- safety ok: `{gate.get('safety_ok')}`",
        "",
        "## PM Boundary",
        "",
        f"- list commit hits: `{gate.get('pm_service_add_peripheral_list_commit_hits')}`",
        f"- PM register success hits: `{gate.get('pm_server_success_return_hits')}`",
        *render_event("pm_init_pm_client_register_call", gate.get("pm_init_pm_client_register_call", {})),
        *render_event("pm_init_pm_client_connect_retcheck", gate.get("pm_init_pm_client_connect_retcheck", {})),
        "",
        "## Lower-state Samples",
        "",
        f"- sample total: `{gate.get('lower_sample_total')}`",
        f"- mdm3 states: `{gate.get('lower_mdm3_states')}`",
        f"- mdm status IRQ totals/increased: `{gate.get('lower_mdm_status_irq_totals')}` / `{gate.get('lower_mdm_status_irq_increased')}`",
        f"- mdm errfatal IRQ totals/increased: `{gate.get('lower_mdm_errfatal_irq_totals')}` / `{gate.get('lower_mdm_errfatal_irq_increased')}`",
        f"- MHI counts/pipes/present: `{gate.get('lower_mhi_device_counts')}` / `{gate.get('lower_mhi_pipe_exists')}` / `{gate.get('lower_mhi_present')}`",
        f"- wlan0 samples/present: `{gate.get('lower_wlan0_exists')}` / `{gate.get('lower_wlan0_present')}`",
        f"- WLFW service69 progress: `{gate.get('lower_service69_progress')}`",
        *render_phase("after_holder_start", lower.get("after_holder_start", {})),
        *render_phase("post_listener_window", lower.get("post_listener_window", {})),
        "",
        "## Route Health",
        "",
        f"- requested `wlanmdsp`: `{gate.get('requested_wlanmdsp')}`",
        f"- WLFW service 69 seen: `{gate.get('wlfw_service69_seen')}`",
        f"- wlan0 present: `{gate.get('wlan0_present')}`",
        f"- `pm_proxy_helper` ready: `{gate.get('pm_proxy_helper_ready')}`",
        f"- `pm-service` ready: `{gate.get('per_mgr_ready')}`",
        f"- `tftp_server` running: `{gate.get('tftp_running')}`",
        f"- `cnss-daemon` running: `{gate.get('cnss_daemon_running')}`",
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
        "- Stop after this one label; use the lower-state label to choose the next source/build-only step below Wi-Fi HAL/scan/connect.",
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

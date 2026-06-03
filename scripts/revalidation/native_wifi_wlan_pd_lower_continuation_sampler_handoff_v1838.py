#!/usr/bin/env python3
"""V1838 one-run WLAN-PD lower-continuation sampler handoff."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import native_wifi_qipcrtr_bound_recv_poll_handoff_v1834 as prev1834


REPO_ROOT = Path(__file__).resolve().parents[2]
CYCLE = "V1838"
V1837_OUT = REPO_ROOT / "tmp" / "wifi" / "v1837-wlan-pd-lower-continuation-sampler-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v1837/dev/__properties__"
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1838-wlan-pd-lower-continuation-sampler-handoff"
DEFAULT_REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1838_WLAN_PD_LOWER_CONTINUATION_SAMPLER_HANDOFF_2026-06-03.md"
)
TEST_EXPECT_VERSION = "A90 Linux init 0.9.162 (v1837-wlan-pd-lower-continuation-sampler)"
TEST_LOG_PATH = "/cache/native-init-wifi-test-boot-v1837.log"
TEST_SUMMARY_PATH = "/cache/native-init-wifi-test-boot-v1837.summary"
TEST_HELPER_RESULT_PATH = "/cache/native-init-wifi-test-boot-v1837-helper.result"
DMESG_PATTERN = (
    "A90v1837|pm_service_trigger_observer|wlan_pd_after_holder_start|"
    "wlan_pd_after_post_listener_window|pcie_1_gdsc|pcie_0_gdsc|"
    "GPIO135|GPIO142|mdm_status|wlan_pd_qipcrtr_bound_recv_poll_state|"
    "wlan_pd_qipcrtr_local_node_bind_state|wlan_pd_qipcrtr_autobind_state|"
    "wlan_pd_qipcrtr_socket_state|QIPCRTR|AF_QIPCRTR|"
    "wlan_pd_qrtr_registry|wlan_pd_post_pm_lower_handoff_klog|"
    "raw_count_|last_|service_locator|service-locator|servloc|domain|"
    "wlan/fw|wlan_fw|qmi-server|qmi_server_connected|pd-mapper|"
    "pd_mapper|subsys|subsystem|pil|q6v5|qmi|QMI|wlfw|WLFW|"
    "service_notifier|service-notifier|service 180|service 74|"
    "wlan_pd|qrtr|service 69|FW ready|BDF|wlan0|cnss-daemon|"
    "4080000.qcom,mss|soc:qcom,mdm3|ext-SDX50M|MHI"
)

PM_PREFIX = "pm_service_trigger_observer.response_sample"
PM_PHASES = (
    "wlan_pd_after_holder_start",
    "wlan_pd_after_post_listener_window",
)
PM_FIELDS = (
    "begin",
    "pmic_gdsc_focus",
    "monotonic_ms",
    "mdm_status_irq_present",
    "mdm_status_irq_parsed",
    "mdm_status_gpio",
    "mdm_status_count_total",
    "mdm3_state",
    "mdm3_crash_count",
    "debugfs_pinctrl_present",
    "debugfs_gpio_present",
    "debugfs_regulator_present",
    "tlmm_gpio135_debugfs_target_line_seen",
    "tlmm_gpio135_debugfs_target_line_source",
    "tlmm_gpio135_debugfs_target_line",
    "tlmm_gpio142_debugfs_target_line_seen",
    "tlmm_gpio142_debugfs_target_line_source",
    "tlmm_gpio142_debugfs_target_line",
    "pmic_soft_reset_seen",
    "pmic_soft_reset_source",
    "pmic_soft_reset_line",
    "pcie1_gdsc_seen",
    "pcie1_gdsc_source",
    "pcie1_gdsc_line",
    "pcie0_gdsc_seen",
    "pcie0_gdsc_source",
    "pcie0_gdsc_line",
    "pcie_current_link_state",
    "pcie_link_state",
    "pcie_runtime_status",
    "pcie_l23_rdy_poll_timeout",
    "pci_dev_count",
    "mhi_bus_count",
    "mhi_pipe_exists",
    "mhi_pipe_fd_count",
    "mhi_pipe_cmdline_count",
    "ks_process_count",
    "wlan0_exists",
    "gpiochip_line_request_executed",
    "pmic_write_executed",
    "esoc_ioctl_executed",
    "end",
)
POWERUP_FIELDS = (
    "begin",
    "end",
    "error",
    "per_mgr_process_count",
    "per_mgr_thread_count",
    "powerup_thread_count",
    "subsys_esoc0_open_inferred",
    "first_pid",
    "first_tid",
    "first_state",
    "first_comm",
    "first_wchan",
    "first_syscall_parsed",
    "first_syscall_nr",
    "first_syscall_name",
    "first_syscall.path_arg_index",
    "first_syscall.path.valid",
    "first_syscall.path.reason",
)
CHANGE_FIELDS = (
    "mdm_status_count_total",
    "mdm3_state",
    "mdm3_crash_count",
    "pcie_current_link_state",
    "pcie_link_state",
    "pcie_runtime_status",
    "pcie_l23_rdy_poll_timeout",
    "pci_dev_count",
    "mhi_bus_count",
    "mhi_pipe_exists",
    "mhi_pipe_fd_count",
    "mhi_pipe_cmdline_count",
    "ks_process_count",
    "wlan0_exists",
    "tlmm_gpio135_debugfs_target_line",
    "tlmm_gpio142_debugfs_target_line",
    "pmic_soft_reset_line",
    "pcie1_gdsc_line",
    "pcie0_gdsc_line",
)


def prev1796() -> Any:
    return prev1834.prev1831.prev1828.prev1825.prev1822.prev1819.prev1816.prev1796


def runner() -> Any:
    return prev1796().runner


def configure_runner() -> None:
    prev1834.CYCLE = CYCLE
    prev1834.V1833_OUT = V1837_OUT
    prev1834.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev1834.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    prev1834.DEFAULT_REPORT_PATH = DEFAULT_REPORT_PATH
    prev1834.TEST_EXPECT_VERSION = TEST_EXPECT_VERSION
    prev1834.TEST_LOG_PATH = TEST_LOG_PATH
    prev1834.TEST_SUMMARY_PATH = TEST_SUMMARY_PATH
    prev1834.TEST_HELPER_RESULT_PATH = TEST_HELPER_RESULT_PATH
    prev1834.DMESG_PATTERN = DMESG_PATTERN
    prev1834.configure_runner()
    runner().DEFAULT_TEST_IMAGE = V1837_OUT / "boot_linux_v1837_wlan_pd_lower_continuation_sampler.img"


def intish(value: object) -> int:
    return prev1834.intish(value)


def pm_focus_sample(fields: dict[str, str], phase: str) -> dict[str, str]:
    prefix = f"{PM_PREFIX}.{phase}."
    marker_prefix = f"{prefix}powerup_marker."
    sample = {
        "phase": phase,
        **{key: fields.get(prefix + key, "") for key in PM_FIELDS},
    }
    sample.update({
        "powerup_" + key.replace(".", "_"): fields.get(marker_prefix + key, "")
        for key in POWERUP_FIELDS
    })
    return sample


def sample_contract_ok(sample: dict[str, str]) -> bool:
    return (
        sample.get("begin") == "1"
        and sample.get("end") == "1"
        and sample.get("pmic_gdsc_focus") == "1"
        and sample.get("powerup_begin") == "1"
        and sample.get("powerup_end") == "1"
    )


def sample_safety_ok(sample: dict[str, str]) -> bool:
    return (
        sample.get("gpiochip_line_request_executed") == "0"
        and sample.get("pmic_write_executed") == "0"
        and sample.get("esoc_ioctl_executed") == "0"
    )


def sample_has_mhi_wlan0_progress(sample: dict[str, str]) -> bool:
    return (
        intish(sample.get("mhi_bus_count")) > 0
        or sample.get("mhi_pipe_exists") == "1"
        or intish(sample.get("mhi_pipe_fd_count")) > 0
        or intish(sample.get("mhi_pipe_cmdline_count")) > 0
        or sample.get("wlan0_exists") == "1"
    )


def changed_fields(samples: list[dict[str, str]]) -> list[str]:
    if len(samples) < 2:
        return []
    first, last = samples[0], samples[-1]
    changed: list[str] = []
    for key in CHANGE_FIELDS:
        first_value = first.get(key, "")
        last_value = last.get(key, "")
        if first_value and last_value and first_value != last_value:
            changed.append(key)
    return changed


def collect_gate_fields(fields: dict[str, str]) -> dict[str, Any]:
    details = prev1834.collect_gate_fields(fields)
    samples = [pm_focus_sample(fields, phase) for phase in PM_PHASES]
    deltas = changed_fields(samples)
    details.update({
        "pm_focus_samples": samples,
        "pm_focus_sample_count": len(samples),
        "pm_focus_contract_ok": all(sample_contract_ok(sample) for sample in samples),
        "pm_focus_safety_ok": all(sample_safety_ok(sample) for sample in samples),
        "pm_focus_change_fields": deltas,
        "pm_focus_change_count": len(deltas),
        "pm_focus_mhi_wlan0_progress": any(sample_has_mhi_wlan0_progress(sample) for sample in samples),
        "pm_focus_mdm_status_delta": intish(samples[-1].get("mdm_status_count_total")) - intish(samples[0].get("mdm_status_count_total")),
    })
    return details


def inherited_bound_recv_label(details: dict[str, Any]) -> str:
    if prev1834.actual_publication_progress(details):
        return "lower-publication-progress"
    if not bool(details.get("qipcrtr_bound_recv_opened")):
        return "qipcrtr-bound-recv-poll-open-fails"
    if details.get("qipcrtr_bound_recv_bind_skipped") == "1":
        return "qipcrtr-bound-recv-poll-bind-skipped"
    if not bool(details.get("qipcrtr_bound_recv_bound")):
        return "qipcrtr-bound-recv-poll-bind-fails"
    if not bool(details.get("qipcrtr_bound_recv_after_ok")) or not bool(details.get("qipcrtr_bound_recv_port_nonzero")):
        return "qipcrtr-bound-recv-poll-port-missing"
    if bool(details.get("qipcrtr_bound_recv_error")):
        return "qipcrtr-bound-recv-poll-error"
    if bool(details.get("qipcrtr_bound_recv_packet_received")):
        return "qipcrtr-bound-recv-poll-packet-passive"
    if (
        bool(details.get("qipcrtr_bound_recv_poll_timed_out"))
        and bool(details.get("qipcrtr_bound_recv_closed"))
        and not bool(details.get("raw_wlan_pd_text_positive"))
        and not bool(details.get("raw_service74_text_positive"))
    ):
        return "qipcrtr-bound-recv-poll-timeout-passive"
    if bool(details.get("qipcrtr_bound_recv_no_pollin")):
        return "qipcrtr-bound-recv-poll-no-pollin-passive"
    return "qipcrtr-bound-recv-poll-state-incomplete"


def classify_gate(args: Any,
                  test_flash: dict[str, Any],
                  rollback_result: dict[str, Any],
                  evidence_dir: Path) -> tuple[str, bool, str, dict[str, Any]]:
    test_version = runner().fwbase.read_text(evidence_dir, "test-version.stdout.txt")
    helper_fields = runner().fwbase.parse_helper_fields(evidence_dir)
    details = collect_gate_fields(helper_fields)
    version_ok = args.expect_test_version in test_version
    rollback_ok = bool(rollback_result.get("ok"))
    helper_contract_seen = prev1796().field_bool(
        helper_fields,
        "wlan_pd_service_object_visible_trigger.begin",
    )
    safety_ok = (
        prev1796().safety_ok(helper_fields)
        and bool(details.get("devnode_safety_ok"))
        and bool(details.get("lower_safety_ok"))
        and bool(details.get("klog_safety_ok"))
        and bool(details.get("qrtr_registry_safety_ok"))
        and bool(details.get("qipcrtr_socket_safety_ok"))
        and bool(details.get("qipcrtr_autobind_safety_ok"))
        and bool(details.get("qipcrtr_local_bind_safety_ok"))
        and bool(details.get("qipcrtr_bound_recv_safety_ok"))
        and bool(details.get("pm_focus_safety_ok"))
    )
    details.update({
        "version_ok": version_ok,
        "rollback_ok": rollback_ok,
        "helper_contract_seen": helper_contract_seen,
        "safety_ok": safety_ok,
    })

    if not test_flash.get("ok"):
        return f"{args.cycle.lower()}-test-boot-flash-or-verify-failed", False, "test boot flash/verify failed", details
    if not version_ok:
        return f"{args.cycle.lower()}-test-boot-version-missing", False, "expected V1837 test boot version was not collected", details
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
        or not details.get("pm_focus_contract_ok")
    ):
        return f"{args.cycle.lower()}-observer-contract-missing", False, "helper result missed inherited lower observer or new PMIC/GDSC focus sample fields", details
    if not safety_ok:
        details["lower_continuation_label"] = "safety-regression"
        return f"{args.cycle.lower()}-safety-regression", False, "one or more hard-stop safety fields regressed", details

    if prev1834.actual_publication_progress(details) or bool(details.get("pm_focus_mhi_wlan0_progress")):
        label = "mhi-wlfw-wlan0-progress"
        reason = "MHI, WLFW/service publication, service74/wlan_pd, or wlan0 progressed below the lower observer boundary"
    elif intish(details.get("pm_focus_mdm_status_delta")) > 0 or bool(details.get("pm_focus_change_fields")):
        label = "pmic-gdsc-or-mdm-status-progress"
        reason = "read-only PMIC/GDSC, mdm3, IRQ, PCIe, or process-count surface changed during the guarded windows"
    else:
        label = "lower-continuation-static-gap"
        reason = "read-only PMIC/GDSC focus samples remained static and MHI/WLFW/wlan0 stayed absent"

    if prev1834.prev1831.prev1828.prev1825.prev1822.prev1819.prev1816.prev1814.prev1811.lower_progress(details):
        details["post_pm_lower_state_label"] = "lower-progress"
    elif prev1834.prev1831.prev1828.prev1825.prev1822.prev1819.prev1816.prev1814.prev1811.prev1808.stable_offlining(details):
        details["post_pm_lower_state_label"] = "stable-mdm3-offlining"
    else:
        details["post_pm_lower_state_label"] = "lower-state-incomplete"
    details["lower_continuation_label"] = label
    details["qipcrtr_bound_recv_label"] = inherited_bound_recv_label(details)
    return f"{args.cycle.lower()}-{label}-rollback-pass", True, reason, details


def render_pm_samples(samples: list[dict[str, str]]) -> list[str]:
    lines: list[str] = []
    for sample in samples:
        lines.extend([
            f"- `{sample.get('phase')}` begin/focus/end: `{sample.get('begin')}` / `{sample.get('pmic_gdsc_focus')}` / `{sample.get('end')}`",
            f"- `{sample.get('phase')}` mdm3/status/crash: `{sample.get('mdm3_state')}` / `{sample.get('mdm_status_count_total')}` / `{sample.get('mdm3_crash_count')}`",
            f"- `{sample.get('phase')}` PCIe current/link/runtime/L23: `{sample.get('pcie_current_link_state')}` / `{sample.get('pcie_link_state')}` / `{sample.get('pcie_runtime_status')}` / `{sample.get('pcie_l23_rdy_poll_timeout')}`",
            f"- `{sample.get('phase')}` GDSC seen lines: pcie1 `{sample.get('pcie1_gdsc_seen')}` `{sample.get('pcie1_gdsc_line')}`; pcie0 `{sample.get('pcie0_gdsc_seen')}` `{sample.get('pcie0_gdsc_line')}`",
            f"- `{sample.get('phase')}` GPIO/PMIC lines: gpio135 `{sample.get('tlmm_gpio135_debugfs_target_line_seen')}` `{sample.get('tlmm_gpio135_debugfs_target_line')}`; gpio142 `{sample.get('tlmm_gpio142_debugfs_target_line_seen')}` `{sample.get('tlmm_gpio142_debugfs_target_line')}`; pmic `{sample.get('pmic_soft_reset_seen')}` `{sample.get('pmic_soft_reset_line')}`",
            f"- `{sample.get('phase')}` PCI/MHI/KS/wlan0: `{sample.get('pci_dev_count')}` / `{sample.get('mhi_bus_count')}` / `{sample.get('mhi_pipe_exists')}` / `{sample.get('mhi_pipe_fd_count')}` / `{sample.get('mhi_pipe_cmdline_count')}` / `{sample.get('ks_process_count')}` / `{sample.get('wlan0_exists')}`",
            f"- `{sample.get('phase')}` powerup process/thread/subsys-open: `{sample.get('powerup_per_mgr_process_count')}` / `{sample.get('powerup_powerup_thread_count')}` / `{sample.get('powerup_subsys_esoc0_open_inferred')}`",
            f"- `{sample.get('phase')}` line-request/write/esoc-ioctl executed flags: `{sample.get('gpiochip_line_request_executed')}` / `{sample.get('pmic_write_executed')}` / `{sample.get('esoc_ioctl_executed')}`",
        ])
    return lines


def render_report(result: dict[str, Any]) -> str:
    gate = result.get("gate", {})
    property_deploy = result.get("property_deploy", {})
    post = result.get("post_rollback_verification", {})
    lines = [
        "# Native Init V1838 WLAN-PD Lower-Continuation Sampler Handoff",
        "",
        "## Summary",
        "",
        "- Cycle: `V1838`",
        "- Type: one-run rollbackable WLAN-PD lower-continuation sampler discriminator",
        f"- Decision: `{result['decision']}`",
        f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
        f"- Reason: {result['reason']}",
        f"- Evidence: `{result['out_dir']}`",
        f"- Rollback attempt: `{result.get('rollback', {}).get('attempt')}`",
        f"- Rollback ok: `{result.get('rollback', {}).get('ok')}`",
    ]
    if post:
        lines.extend([
            f"- Post-rollback version ok: `{post.get('version_ok')}`",
            f"- Post-rollback selftest fail=0: `{post.get('selftest_fail_zero')}`",
            f"- Post-rollback version evidence: `{post.get('version_stdout_file')}`",
            f"- Post-rollback selftest evidence: `{post.get('selftest_stdout_file')}`",
        ])
    lines.extend([
        "",
        "## Gate Label",
        "",
        f"- lower-continuation label: `{gate.get('lower_continuation_label')}`",
        f"- PM focus contract/safety: `{gate.get('pm_focus_contract_ok')}` / `{gate.get('pm_focus_safety_ok')}`",
        f"- PM focus change fields: `{gate.get('pm_focus_change_fields')}`",
        f"- PM focus mdm-status delta: `{gate.get('pm_focus_mdm_status_delta')}`",
        f"- PM focus MHI/wlan0 progress: `{gate.get('pm_focus_mhi_wlan0_progress')}`",
        f"- QIPCRTR bound poll/recv label: `{gate.get('qipcrtr_bound_recv_label')}`",
        f"- WLFW QRTR readback label: `{gate.get('qrtr_readback_label')}`",
        f"- service-locator domain label: `{gate.get('servloc_domain_label')}`",
        f"- service-notifier label: `{gate.get('servnotif_label')}`",
        f"- lower-state label: `{gate.get('post_pm_lower_state_label')}`",
        f"- safety ok: `{gate.get('safety_ok')}`",
        "",
        "## PMIC/GDSC Focus Samples",
        "",
        *render_pm_samples(gate.get("pm_focus_samples", [])),
        "",
        "## Inherited Lower State",
        "",
        f"- early/late service-notifier state: `{gate.get('service_notifier_early_state')}` / `{gate.get('service_notifier_late_state')}`",
        f"- mdm3/MHI/WLFW69/wlan0: `{gate.get('lower_mdm3_states')}` / `{gate.get('lower_mhi_present')}` / `{gate.get('lower_service69_progress')}` / `{gate.get('lower_wlan0_present')}`",
        f"- service180/service74/wlan_pd raw: `{gate.get('raw_service180_text_counts')}` / `{gate.get('raw_service74_text_counts')}` / `{gate.get('raw_wlan_pd_text_counts')}`",
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
        "- The new V1838 surface only reads PMIC/GDSC, GPIO debugfs text, mdm3, PCIe, MHI, process, and `wlan0` state at two guarded lower-observer phases.",
        "- The inherited route retains bounded QRTR/QMI probes from V1834: WLFW readback without QMI WLFW request payload, service-locator domain-list QMI, and service-notifier listener QMI.",
        "- No Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, direct `/dev/subsys_esoc0` open, fake ONLINE, PMIC/GPIO/GDSC write, eSoC notify, BOOT_DONE spoof, forced RC1, `boot_wlan`, restart-PD request, PCI rescan, or platform bind/unbind was used.",
        "- Mutation scope is private property runtime staging on `/mnt/sdext`, one test boot flash, and rollback to `stage3/boot_linux_v724.img`.",
        "",
        "## Next",
        "",
        "- Do not proceed to Wi-Fi HAL/scan/connect unless WLFW service 69 and `wlan0` are present.",
        "- If the label is `lower-continuation-static-gap`, classify the remaining mdm3/ext-SDX50M prerequisite gap before any next live action.",
        "",
    ])
    return "\n".join(lines)


def record_post_rollback_verification() -> dict[str, Any]:
    out_dir = DEFAULT_OUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    base = runner().fwbase.base
    version_result = base.run_command(
        [
            "bash",
            "-o",
            "pipefail",
            "-lc",
            "python3 scripts/revalidation/a90ctl.py version 2>&1 | sed '/made by /d'",
        ],
        timeout=60.0,
    )
    selftest_result = base.run_command(base.a90ctl_command(["selftest"]), timeout=60.0)
    version_stdout = str(version_result.get("stdout") or "")
    version_stderr = str(version_result.get("stderr") or "")
    selftest_stdout = str(selftest_result.get("stdout") or "")
    selftest_stderr = str(selftest_result.get("stderr") or "")
    (out_dir / "post-rollback-version-filtered.stdout.txt").write_text(version_stdout, encoding="utf-8")
    (out_dir / "post-rollback-version-filtered.stderr.txt").write_text(version_stderr, encoding="utf-8")
    (out_dir / "post-rollback-selftest.stdout.txt").write_text(selftest_stdout, encoding="utf-8")
    (out_dir / "post-rollback-selftest.stderr.txt").write_text(selftest_stderr, encoding="utf-8")
    version_text = version_stdout + "\n" + version_stderr
    selftest_text = selftest_stdout + "\n" + selftest_stderr
    return {
        "version_ok": "A90 Linux init 0.9.68 (v724)" in version_text,
        "selftest_fail_zero": "fail=0" in selftest_text,
        "version_stdout_file": str((out_dir / "post-rollback-version-filtered.stdout.txt").relative_to(REPO_ROOT)),
        "selftest_stdout_file": str((out_dir / "post-rollback-selftest.stdout.txt").relative_to(REPO_ROOT)),
        "version_rc": version_result.get("rc"),
        "selftest_rc": selftest_result.get("rc"),
    }


def update_manifest_with_post_verification(post: dict[str, Any]) -> int:
    manifest_path = DEFAULT_OUT_DIR / "manifest.json"
    if not manifest_path.exists():
        return 1
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["post_rollback_verification"] = post
    if not post.get("version_ok") or not post.get("selftest_fail_zero"):
        manifest["pass"] = False
        manifest["decision"] = f"{CYCLE.lower()}-post-rollback-verification-failed"
        manifest["reason"] = "post-rollback filtered version or selftest fail=0 verification failed"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (DEFAULT_OUT_DIR / "summary.md").write_text(render_report(manifest), encoding="utf-8")
    DEFAULT_REPORT_PATH.write_text(render_report(manifest), encoding="utf-8")
    return 0 if manifest.get("pass") else 1


def main(argv: list[str] | None = None) -> int:
    configure_runner()
    base = runner()
    base.deploy_property_root = prev1796().deploy_property_root_serial
    base.classify_gate = classify_gate
    base.render_report = render_report
    rc = base.main(argv)
    post = record_post_rollback_verification()
    post_rc = update_manifest_with_post_verification(post)
    prev1796().sanitize_evidence_dir(DEFAULT_OUT_DIR)
    return rc or post_rc


if __name__ == "__main__":
    raise SystemExit(main())

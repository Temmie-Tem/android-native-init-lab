#!/usr/bin/env python3
"""V1328 bounded no-write MDM2AP/errfatal/PCIe timing sampler with helper v276."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import native_wifi_late_per_proxy_response_sampler_live_v1242 as base


MDM2AP_TIMING_FLAG = "--pm-observer-late-per-proxy-mdm2ap-errfatal-pcie-timing-sampler"
TIMING_PREFIX = "mdm2ap_timing."
EXPECTED_MIN_TIMING_SAMPLE_COUNT = 120

base.DEFAULT_OUT_DIR = Path("tmp/wifi/v1328-mdm2ap-timing-sampler-live")
base.LATEST_POINTER = Path("tmp/wifi/latest-v1328-mdm2ap-timing-sampler-live.txt")
PLAN_OUT_DIR = Path("tmp/wifi/v1328-mdm2ap-timing-sampler-plan")
PLAN_LATEST_POINTER = Path("tmp/wifi/latest-v1328-mdm2ap-timing-sampler-plan.txt")
base.HELPER_MARKER = "a90_android_execns_probe v276"
base.HELPER_SHA256 = "dad57e135d3b4f0db2f1f95ee04022a3f5610fdbd0ecc6b69c243883689ca66f"
base.CYCLE_LABEL = "v1328"
base.CYCLE_NAME = "V1328"
base.SUMMARY_HEADING = "V1328 MDM2AP Timing Sampler"
base.EVIDENCE_FILE_PREFIX = "v1328"

_ORIGINAL_FORCE = base._force_response_sampler_child_command
_ORIGINAL_COLLECT = base._collect_response_samples
_ORIGINAL_DECIDE = base.decide_v1242
_ORIGINAL_SAMPLE_ROWS = base._sample_rows


def _int_value(value: Any, fallback: int = 0) -> int:
    return base._int_value(value, fallback)


def _force_mdm2ap_timing_child_command(original):
    wrapped = _ORIGINAL_FORCE(original)

    def command(args: Any) -> list[str]:
        result = wrapped(args)
        if MDM2AP_TIMING_FLAG not in result:
            result.append(MDM2AP_TIMING_FLAG)
        return result

    return command


def _collect_response_samples_with_timing(text: str) -> dict[str, Any]:
    result = _ORIGINAL_COLLECT(text)
    keys = base._parse_keys(text)
    timing = {
        key[len(TIMING_PREFIX):]: value
        for key, value in keys.items()
        if key.startswith(TIMING_PREFIX)
    }
    result.update({
        "helper_stdout_truncated": "A90_EXECNS_STDOUT_END truncated=1" in text,
        "timing_emitted": bool(timing),
        "timing_begin": _int_value(timing.get("begin"), 0) == 1,
        "timing_end": _int_value(timing.get("end"), 0) == 1,
        "timing_mode": timing.get("mode", ""),
        "timing_sample_interval_ms": _int_value(timing.get("sample_interval_ms"), 0),
        "timing_sample_count": _int_value(timing.get("sample_count"), 0),
        "timing_pm_service_powerup_seen": _int_value(timing.get("pm_service_powerup_seen"), 0) == 1,
        "timing_max_powerup_thread_count": _int_value(timing.get("max_powerup_thread_count"), -1),
        "timing_gpio142_irq_initial": _int_value(timing.get("gpio142_irq_initial"), -1),
        "timing_gpio142_irq_max": _int_value(timing.get("gpio142_irq_max"), -1),
        "timing_gpio142_irq_delta": _int_value(timing.get("gpio142_irq_delta"), -1),
        "timing_gpio142_first_delta_sample": _int_value(timing.get("gpio142_first_delta_sample"), -1),
        "timing_errfatal_irq_initial": _int_value(timing.get("errfatal_irq_initial"), -1),
        "timing_errfatal_irq_max": _int_value(timing.get("errfatal_irq_max"), -1),
        "timing_errfatal_irq_delta": _int_value(timing.get("errfatal_irq_delta"), -1),
        "timing_errfatal_first_delta_sample": _int_value(timing.get("errfatal_first_delta_sample"), -1),
        "timing_pcie_rc1_transition_seen": _int_value(timing.get("pcie_rc1_transition_seen"), 0) == 1,
        "timing_pcie_rc1_first_transition_sample": _int_value(timing.get("pcie_rc1_first_transition_sample"), -1),
        "timing_pcie_current_link_state_initial": timing.get("pcie_current_link_state_initial", ""),
        "timing_pcie_current_link_state_last": timing.get("pcie_current_link_state_last", ""),
        "timing_pcie_link_state_initial": timing.get("pcie_link_state_initial", ""),
        "timing_pcie_link_state_last": timing.get("pcie_link_state_last", ""),
        "timing_pcie_runtime_status_initial": timing.get("pcie_runtime_status_initial", ""),
        "timing_pcie_runtime_status_last": timing.get("pcie_runtime_status_last", ""),
        "timing_pcie1_gdsc_seen": _int_value(timing.get("pcie1_gdsc_seen"), 0) == 1,
        "timing_pcie1_gdsc_nonzero_seen": _int_value(timing.get("pcie1_gdsc_nonzero_seen"), 0) == 1,
        "timing_pcie1_gdsc_initial": timing.get("pcie1_gdsc_initial", ""),
        "timing_pcie1_gdsc_last": timing.get("pcie1_gdsc_last", ""),
        "timing_pcie1_clkref_seen": _int_value(timing.get("pcie1_clkref_seen"), 0) == 1,
        "timing_pcie1_clkref_initial": timing.get("pcie1_clkref_initial", ""),
        "timing_pcie1_clkref_last": timing.get("pcie1_clkref_last", ""),
        "timing_pcie1_phy_refgen_seen": _int_value(timing.get("pcie1_phy_refgen_seen"), 0) == 1,
        "timing_pcie1_phy_refgen_initial": timing.get("pcie1_phy_refgen_initial", ""),
        "timing_pcie1_phy_refgen_last": timing.get("pcie1_phy_refgen_last", ""),
        "timing_pcie1_pipe_clk_seen": _int_value(timing.get("pcie1_pipe_clk_seen"), 0) == 1,
        "timing_pcie1_pipe_clk_initial": timing.get("pcie1_pipe_clk_initial", ""),
        "timing_pcie1_pipe_clk_last": timing.get("pcie1_pipe_clk_last", ""),
        "timing_gpio102_perst_seen": _int_value(timing.get("gpio102_perst_seen"), 0) == 1,
        "timing_gpio102_perst_initial": timing.get("gpio102_perst_initial", ""),
        "timing_gpio102_perst_last": timing.get("gpio102_perst_last", ""),
        "timing_gpio103_clkreq_seen": _int_value(timing.get("gpio103_clkreq_seen"), 0) == 1,
        "timing_gpio103_clkreq_initial": timing.get("gpio103_clkreq_initial", ""),
        "timing_gpio103_clkreq_last": timing.get("gpio103_clkreq_last", ""),
        "timing_gpio104_wake_seen": _int_value(timing.get("gpio104_wake_seen"), 0) == 1,
        "timing_gpio104_wake_initial": timing.get("gpio104_wake_initial", ""),
        "timing_gpio104_wake_last": timing.get("gpio104_wake_last", ""),
        "timing_pci_dev_initial": _int_value(timing.get("pci_dev_initial"), -1),
        "timing_pci_dev_max": _int_value(timing.get("pci_dev_max"), -1),
        "timing_mhi_bus_max": _int_value(timing.get("mhi_bus_max"), -1),
        "timing_mhi_pipe_seen": _int_value(timing.get("mhi_pipe_seen"), 0) == 1,
        "timing_mhi_pipe_fd_max": _int_value(timing.get("mhi_pipe_fd_max"), -1),
        "timing_mhi_pipe_cmdline_max": _int_value(timing.get("mhi_pipe_cmdline_max"), -1),
        "timing_ks_process_max": _int_value(timing.get("ks_process_max"), -1),
        "timing_pcie_kmsg_initial": _int_value(timing.get("pcie_kmsg_initial"), -1),
        "timing_pcie_kmsg_max": _int_value(timing.get("pcie_kmsg_max"), -1),
        "timing_mhi_kmsg_max": _int_value(timing.get("mhi_kmsg_max"), -1),
        "timing_wlfw_kmsg_max": _int_value(timing.get("wlfw_kmsg_max"), -1),
        "timing_wlan0_seen": _int_value(timing.get("wlan0_seen"), 0) == 1,
        "timing_safety_wifi_hal_start": _int_value(timing.get("safety_wifi_hal_start"), -1),
        "timing_safety_scan_connect": _int_value(timing.get("safety_scan_connect"), -1),
        "timing_safety_credentials": _int_value(timing.get("safety_credentials"), -1),
        "timing_safety_dhcp_route": _int_value(timing.get("safety_dhcp_route"), -1),
        "timing_safety_external_ping": _int_value(timing.get("safety_external_ping"), -1),
        "timing_safety_pmic_write": _int_value(timing.get("safety_pmic_write"), -1),
        "timing_safety_gpio_request": _int_value(timing.get("safety_gpio_request"), -1),
        "timing_safety_direct_esoc_ioctl": _int_value(timing.get("safety_direct_esoc_ioctl"), -1),
    })
    return result


def _sample_rows_with_timing(manifest: dict[str, Any]) -> list[list[Any]]:
    rows = _ORIGINAL_SAMPLE_ROWS(manifest)
    sampler = manifest.get("response_sampler") or {}
    rows.extend([
        ["helper_stdout_truncated", sampler.get("helper_stdout_truncated")],
        ["timing_emitted", sampler.get("timing_emitted")],
        ["timing_end", sampler.get("timing_end")],
        ["timing_mode", sampler.get("timing_mode")],
        ["timing_sample_interval_ms", sampler.get("timing_sample_interval_ms")],
        ["timing_sample_count", sampler.get("timing_sample_count")],
        ["timing_pm_service_powerup_seen", sampler.get("timing_pm_service_powerup_seen")],
        ["timing_max_powerup_thread_count", sampler.get("timing_max_powerup_thread_count")],
        ["timing_gpio142_irq_delta", sampler.get("timing_gpio142_irq_delta")],
        ["timing_gpio142_first_delta_sample", sampler.get("timing_gpio142_first_delta_sample")],
        ["timing_errfatal_irq_delta", sampler.get("timing_errfatal_irq_delta")],
        ["timing_errfatal_first_delta_sample", sampler.get("timing_errfatal_first_delta_sample")],
        ["timing_pcie_rc1_transition_seen", sampler.get("timing_pcie_rc1_transition_seen")],
        ["timing_pcie_rc1_first_transition_sample", sampler.get("timing_pcie_rc1_first_transition_sample")],
        ["timing_pcie_current_link_state_initial", sampler.get("timing_pcie_current_link_state_initial")],
        ["timing_pcie_current_link_state_last", sampler.get("timing_pcie_current_link_state_last")],
        ["timing_pcie1_gdsc_seen", sampler.get("timing_pcie1_gdsc_seen")],
        ["timing_pcie1_gdsc_nonzero_seen", sampler.get("timing_pcie1_gdsc_nonzero_seen")],
        ["timing_pcie1_gdsc_initial", sampler.get("timing_pcie1_gdsc_initial")],
        ["timing_pcie1_gdsc_last", sampler.get("timing_pcie1_gdsc_last")],
        ["timing_pcie1_clkref_seen", sampler.get("timing_pcie1_clkref_seen")],
        ["timing_pcie1_clkref_initial", sampler.get("timing_pcie1_clkref_initial")],
        ["timing_pcie1_clkref_last", sampler.get("timing_pcie1_clkref_last")],
        ["timing_pcie1_phy_refgen_seen", sampler.get("timing_pcie1_phy_refgen_seen")],
        ["timing_pcie1_phy_refgen_initial", sampler.get("timing_pcie1_phy_refgen_initial")],
        ["timing_pcie1_phy_refgen_last", sampler.get("timing_pcie1_phy_refgen_last")],
        ["timing_pcie1_pipe_clk_seen", sampler.get("timing_pcie1_pipe_clk_seen")],
        ["timing_pcie1_pipe_clk_initial", sampler.get("timing_pcie1_pipe_clk_initial")],
        ["timing_pcie1_pipe_clk_last", sampler.get("timing_pcie1_pipe_clk_last")],
        ["timing_gpio102_perst_seen", sampler.get("timing_gpio102_perst_seen")],
        ["timing_gpio102_perst_initial", sampler.get("timing_gpio102_perst_initial")],
        ["timing_gpio102_perst_last", sampler.get("timing_gpio102_perst_last")],
        ["timing_gpio103_clkreq_seen", sampler.get("timing_gpio103_clkreq_seen")],
        ["timing_gpio103_clkreq_initial", sampler.get("timing_gpio103_clkreq_initial")],
        ["timing_gpio103_clkreq_last", sampler.get("timing_gpio103_clkreq_last")],
        ["timing_gpio104_wake_seen", sampler.get("timing_gpio104_wake_seen")],
        ["timing_gpio104_wake_initial", sampler.get("timing_gpio104_wake_initial")],
        ["timing_gpio104_wake_last", sampler.get("timing_gpio104_wake_last")],
        ["timing_pci_dev_max", sampler.get("timing_pci_dev_max")],
        ["timing_mhi_bus_max", sampler.get("timing_mhi_bus_max")],
        ["timing_mhi_pipe_seen", sampler.get("timing_mhi_pipe_seen")],
        ["timing_mhi_pipe_fd_max", sampler.get("timing_mhi_pipe_fd_max")],
        ["timing_ks_process_max", sampler.get("timing_ks_process_max")],
        ["timing_wlfw_kmsg_max", sampler.get("timing_wlfw_kmsg_max")],
        ["timing_wlan0_seen", sampler.get("timing_wlan0_seen")],
        ["timing_safety_wifi_hal_start", sampler.get("timing_safety_wifi_hal_start")],
        ["timing_safety_scan_connect", sampler.get("timing_safety_scan_connect")],
        ["timing_safety_credentials", sampler.get("timing_safety_credentials")],
        ["timing_safety_dhcp_route", sampler.get("timing_safety_dhcp_route")],
        ["timing_safety_external_ping", sampler.get("timing_safety_external_ping")],
        ["timing_safety_pmic_write", sampler.get("timing_safety_pmic_write")],
        ["timing_safety_gpio_request", sampler.get("timing_safety_gpio_request")],
        ["timing_safety_direct_esoc_ioctl", sampler.get("timing_safety_direct_esoc_ioctl")],
    ])
    return rows


def _decision(suffix: str) -> str:
    return f"{base.CYCLE_LABEL}-{suffix}"


def decide_v1328(manifest: dict[str, Any]) -> tuple[str, bool, str, str]:
    if manifest.get("command") == "plan":
        return (
            _decision("mdm2ap-timing-sampler-plan-ready"),
            True,
            "plan-only; no device mutation or live actor executed",
            "run V1328 bounded no-write MDM2AP timing sampler live",
        )

    sampler = manifest.get("response_sampler") or {}
    mode = str(sampler.get("timing_mode") or "")
    sample_count = int(sampler.get("timing_sample_count") or 0)

    if sampler.get("helper_stdout_truncated"):
        return (
            _decision("mdm2ap-timing-stdout-truncated"),
            False,
            "helper stdout hit the capture cap",
            "reduce timing output before live rerun",
        )
    if not sampler.get("timing_emitted") or not sampler.get("timing_end"):
        return (
            _decision("mdm2ap-timing-summary-missing"),
            False,
            "mdm2ap_timing summary did not emit a complete begin/end block",
            "verify helper v276 deploy and timing flag injection",
        )
    if mode != "late-per-proxy-mdm2ap-errfatal-pcie-timing":
        return (
            _decision("mdm2ap-timing-mode-mismatch"),
            False,
            f"unexpected timing mode={mode!r}",
            "verify helper v276 deploy and command flags",
        )
    if sample_count < EXPECTED_MIN_TIMING_SAMPLE_COUNT:
        return (
            _decision("mdm2ap-timing-short-window"),
            False,
            f"timing sample_count={sample_count}; expected at least {EXPECTED_MIN_TIMING_SAMPLE_COUNT}",
            "inspect helper timing sampler window before rerunning live",
        )

    safety_keys = (
        "timing_safety_wifi_hal_start",
        "timing_safety_scan_connect",
        "timing_safety_credentials",
        "timing_safety_dhcp_route",
        "timing_safety_external_ping",
        "timing_safety_pmic_write",
        "timing_safety_gpio_request",
        "timing_safety_direct_esoc_ioctl",
    )
    if any(_int_value(sampler.get(key), -1) != 0 for key in safety_keys):
        return (
            _decision("mdm2ap-timing-safety-violation"),
            False,
            "timing summary reports a forbidden live action",
            "stop and inspect helper safety markers",
        )

    progress = (
        int(sampler.get("timing_gpio142_irq_delta") or 0) > 0 or
        int(sampler.get("timing_errfatal_irq_delta") or 0) > 0 or
        bool(sampler.get("timing_pcie_rc1_transition_seen")) or
        int(sampler.get("timing_pci_dev_max") or 0) > 0 or
        int(sampler.get("timing_mhi_bus_max") or 0) > 0 or
        bool(sampler.get("timing_mhi_pipe_seen")) or
        int(sampler.get("timing_mhi_pipe_fd_max") or 0) > 0 or
        int(sampler.get("timing_ks_process_max") or 0) > 0 or
        int(sampler.get("timing_wlfw_kmsg_max") or 0) > 0 or
        bool(sampler.get("timing_wlan0_seen"))
    )
    if progress:
        return (
            _decision("mdm2ap-timing-progress"),
            True,
            "timing sampler observed MDM2AP/PCIe/MHI/WLFW/wlan0 progress",
            "preserve evidence and classify the first progressed surface before Wi-Fi HAL/connect",
        )
    if sampler.get("timing_pm_service_powerup_seen"):
        return (
            _decision("mdm2ap-timing-full-window-no-transition"),
            True,
            "full timing window saw mdm_subsys_powerup but no GPIO142/errfatal/PCIe/MHI/ks/WLFW/wlan0 transition",
            "classify Android-only SDX50M response prerequisite before any PMIC/GPIO/eSoC mutation",
        )
    return _ORIGINAL_DECIDE(manifest)


base._force_response_sampler_child_command = _force_mdm2ap_timing_child_command
base._collect_response_samples = _collect_response_samples_with_timing
base._sample_rows = _sample_rows_with_timing
base.decide_v1242 = decide_v1328


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "plan":
        base.DEFAULT_OUT_DIR = PLAN_OUT_DIR
        base.LATEST_POINTER = PLAN_LATEST_POINTER
    raise SystemExit(base.main())

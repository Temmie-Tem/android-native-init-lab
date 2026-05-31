#!/usr/bin/env python3
"""V1313 bounded lower-sequence summary sampler with helper v275."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import native_wifi_late_per_proxy_response_sampler_live_v1242 as base


LOWER_SEQUENCE_SUMMARY_FLAG = "--pm-observer-late-per-proxy-lower-sequence-summary-sampler"
SUMMARY_PREFIX = "pm_service_trigger_observer.response_summary."
EXPECTED_MIN_SUMMARY_SAMPLE_COUNT = 81

base.DEFAULT_OUT_DIR = Path("tmp/wifi/v1313-lower-sequence-summary-sampler-live")
base.LATEST_POINTER = Path("tmp/wifi/latest-v1313-lower-sequence-summary-sampler-live.txt")
PLAN_OUT_DIR = Path("tmp/wifi/v1313-lower-sequence-summary-sampler-plan")
PLAN_LATEST_POINTER = Path("tmp/wifi/latest-v1313-lower-sequence-summary-sampler-plan.txt")
base.HELPER_MARKER = "a90_android_execns_probe v275"
base.HELPER_SHA256 = "66e52e7507dd07bcb4071afd04bc60e51d1c6bb7b9cb7363205f1eb4f44d4677"
base.CYCLE_LABEL = "v1313"
base.CYCLE_NAME = "V1313"
base.SUMMARY_HEADING = "V1313 Lower-Sequence Summary Sampler"
base.EVIDENCE_FILE_PREFIX = "v1313"

_ORIGINAL_FORCE = base._force_response_sampler_child_command
_ORIGINAL_COLLECT = base._collect_response_samples
_ORIGINAL_DECIDE = base.decide_v1242
_ORIGINAL_SAMPLE_ROWS = base._sample_rows


def _int_value(value: Any, fallback: int = 0) -> int:
    return base._int_value(value, fallback)


def _force_lower_sequence_summary_child_command(original):
    wrapped = _ORIGINAL_FORCE(original)

    def command(args: Any) -> list[str]:
        result = wrapped(args)
        if LOWER_SEQUENCE_SUMMARY_FLAG not in result:
            result.append(LOWER_SEQUENCE_SUMMARY_FLAG)
        return result

    return command


def _collect_response_samples_with_summary(text: str) -> dict[str, Any]:
    result = _ORIGINAL_COLLECT(text)
    keys = base._parse_keys(text)
    summary = {
        key[len(SUMMARY_PREFIX):]: value
        for key, value in keys.items()
        if key.startswith(SUMMARY_PREFIX)
    }
    result.update({
        "helper_stdout_truncated": "A90_EXECNS_STDOUT_END truncated=1" in text,
        "lower_summary_emitted": bool(summary),
        "lower_summary_begin": _int_value(summary.get("begin"), 0) == 1,
        "lower_summary_end": _int_value(summary.get("end"), 0) == 1,
        "lower_summary_mode": summary.get("mode", ""),
        "lower_summary_sample_count": _int_value(summary.get("sample_count"), 0),
        "lower_summary_powerup_seen": _int_value(summary.get("powerup_seen"), 0) == 1,
        "lower_summary_max_powerup_thread_count": _int_value(summary.get("max_powerup_thread_count"), -1),
        "lower_summary_max_mdm_status_count_total": _int_value(summary.get("max_mdm_status_count_total"), -1),
        "lower_summary_max_pci_dev_count": _int_value(summary.get("max_pci_dev_count"), -1),
        "lower_summary_max_mhi_bus_count": _int_value(summary.get("max_mhi_bus_count"), -1),
        "lower_summary_mhi_pipe_seen": _int_value(summary.get("mhi_pipe_seen"), 0) == 1,
        "lower_summary_max_mhi_pipe_fd_count": _int_value(summary.get("max_mhi_pipe_fd_count"), -1),
        "lower_summary_max_mhi_pipe_cmdline_count": _int_value(summary.get("max_mhi_pipe_cmdline_count"), -1),
        "lower_summary_max_ks_process_count": _int_value(summary.get("max_ks_process_count"), -1),
        "lower_summary_wlan0_seen": _int_value(summary.get("wlan0_seen"), 0) == 1,
        "lower_summary_pcie1_gdsc_zero_seen": _int_value(summary.get("pcie1_gdsc_zero_seen"), 0) == 1,
        "lower_summary_pcie1_gdsc_nonzero_seen": _int_value(summary.get("pcie1_gdsc_nonzero_seen"), 0) == 1,
        "lower_summary_pcie1_gdsc_line": summary.get("pcie1_gdsc_line", ""),
        "lower_summary_pcie0_gdsc_zero_seen": _int_value(summary.get("pcie0_gdsc_zero_seen"), 0) == 1,
        "lower_summary_pcie0_gdsc_nonzero_seen": _int_value(summary.get("pcie0_gdsc_nonzero_seen"), 0) == 1,
        "lower_summary_pcie0_gdsc_line": summary.get("pcie0_gdsc_line", ""),
        "lower_summary_pmic_soft_reset_line": summary.get("pmic_soft_reset_line", ""),
        "lower_summary_tlmm_gpio135_line": summary.get("tlmm_gpio135_line", ""),
        "lower_summary_tlmm_gpio142_line": summary.get("tlmm_gpio142_line", ""),
        "lower_summary_gpiochip_line_request_executed": _int_value(summary.get("gpiochip_line_request_executed"), -1),
        "lower_summary_pmic_write_executed": _int_value(summary.get("pmic_write_executed"), -1),
        "lower_summary_esoc_ioctl_executed": _int_value(summary.get("esoc_ioctl_executed"), -1),
    })
    return result


def _sample_rows_with_summary(manifest: dict[str, Any]) -> list[list[Any]]:
    rows = _ORIGINAL_SAMPLE_ROWS(manifest)
    sampler = manifest.get("response_sampler") or {}
    rows.extend([
        ["helper_stdout_truncated", sampler.get("helper_stdout_truncated")],
        ["lower_summary_emitted", sampler.get("lower_summary_emitted")],
        ["lower_summary_end", sampler.get("lower_summary_end")],
        ["lower_summary_mode", sampler.get("lower_summary_mode")],
        ["lower_summary_sample_count", sampler.get("lower_summary_sample_count")],
        ["lower_summary_powerup_seen", sampler.get("lower_summary_powerup_seen")],
        ["lower_summary_max_powerup_thread_count", sampler.get("lower_summary_max_powerup_thread_count")],
        ["lower_summary_max_mdm_status_count_total", sampler.get("lower_summary_max_mdm_status_count_total")],
        ["lower_summary_max_pci_dev_count", sampler.get("lower_summary_max_pci_dev_count")],
        ["lower_summary_max_mhi_bus_count", sampler.get("lower_summary_max_mhi_bus_count")],
        ["lower_summary_mhi_pipe_seen", sampler.get("lower_summary_mhi_pipe_seen")],
        ["lower_summary_max_mhi_pipe_fd_count", sampler.get("lower_summary_max_mhi_pipe_fd_count")],
        ["lower_summary_max_mhi_pipe_cmdline_count", sampler.get("lower_summary_max_mhi_pipe_cmdline_count")],
        ["lower_summary_max_ks_process_count", sampler.get("lower_summary_max_ks_process_count")],
        ["lower_summary_wlan0_seen", sampler.get("lower_summary_wlan0_seen")],
        ["lower_summary_pcie1_gdsc_zero_seen", sampler.get("lower_summary_pcie1_gdsc_zero_seen")],
        ["lower_summary_pcie1_gdsc_nonzero_seen", sampler.get("lower_summary_pcie1_gdsc_nonzero_seen")],
        ["lower_summary_pcie1_gdsc_line", sampler.get("lower_summary_pcie1_gdsc_line")],
        ["lower_summary_pcie0_gdsc_zero_seen", sampler.get("lower_summary_pcie0_gdsc_zero_seen")],
        ["lower_summary_pcie0_gdsc_nonzero_seen", sampler.get("lower_summary_pcie0_gdsc_nonzero_seen")],
        ["lower_summary_pcie0_gdsc_line", sampler.get("lower_summary_pcie0_gdsc_line")],
        ["lower_summary_pmic_soft_reset_line", sampler.get("lower_summary_pmic_soft_reset_line")],
        ["lower_summary_tlmm_gpio135_line", sampler.get("lower_summary_tlmm_gpio135_line")],
        ["lower_summary_tlmm_gpio142_line", sampler.get("lower_summary_tlmm_gpio142_line")],
        ["lower_summary_gpiochip_line_request_executed", sampler.get("lower_summary_gpiochip_line_request_executed")],
        ["lower_summary_pmic_write_executed", sampler.get("lower_summary_pmic_write_executed")],
        ["lower_summary_esoc_ioctl_executed", sampler.get("lower_summary_esoc_ioctl_executed")],
    ])
    return rows


def _decision(suffix: str) -> str:
    return f"{base.CYCLE_LABEL}-{suffix}"


def decide_v1313(manifest: dict[str, Any]) -> tuple[str, bool, str, str]:
    if manifest.get("command") == "plan":
        return (
            _decision("lower-sequence-summary-plan-ready"),
            True,
            "plan-only; no device mutation or live actor executed",
            "run V1313 bounded lower-sequence summary sampler live",
        )

    sampler = manifest.get("response_sampler") or {}
    mode = str(sampler.get("lower_summary_mode") or "")
    sample_count = int(sampler.get("lower_summary_sample_count") or 0)

    if sampler.get("helper_stdout_truncated"):
        return (
            _decision("lower-sequence-summary-stdout-truncated"),
            False,
            "helper stdout still hit the capture cap",
            "reduce summary output further before live rerun",
        )
    if not sampler.get("lower_summary_emitted") or not sampler.get("lower_summary_end"):
        return (
            _decision("lower-sequence-summary-missing"),
            False,
            "lower sequence summary did not emit a complete begin/end block",
            "verify helper v275 deploy and summary flag injection",
        )
    if mode != "late-per-proxy-lower-sequence-summary":
        return (
            _decision("lower-sequence-summary-mode-mismatch"),
            False,
            f"unexpected summary mode={mode!r}",
            "verify helper v275 deploy and command flags",
        )
    if sample_count < EXPECTED_MIN_SUMMARY_SAMPLE_COUNT:
        return (
            _decision("lower-sequence-summary-short-window"),
            False,
            f"summary sample_count={sample_count}; expected at least {EXPECTED_MIN_SUMMARY_SAMPLE_COUNT}",
            "inspect helper summary sampler window before rerunning live",
        )
    if (
        sampler.get("lower_summary_gpiochip_line_request_executed") != 0 or
        sampler.get("lower_summary_pmic_write_executed") != 0 or
        sampler.get("lower_summary_esoc_ioctl_executed") != 0
    ):
        return (
            _decision("lower-sequence-summary-safety-violation"),
            False,
            "summary reports a forbidden lower mutation",
            "stop and inspect helper safety markers",
        )

    progress = (
        int(sampler.get("lower_summary_max_mdm_status_count_total") or 0) > 0 or
        int(sampler.get("lower_summary_max_pci_dev_count") or 0) > 0 or
        int(sampler.get("lower_summary_max_mhi_bus_count") or 0) > 0 or
        bool(sampler.get("lower_summary_mhi_pipe_seen")) or
        int(sampler.get("lower_summary_max_mhi_pipe_fd_count") or 0) > 0 or
        int(sampler.get("lower_summary_max_ks_process_count") or 0) > 0 or
        bool(sampler.get("lower_summary_wlan0_seen")) or
        bool(sampler.get("lower_summary_pcie1_gdsc_nonzero_seen")) or
        bool(sampler.get("lower_summary_pcie0_gdsc_nonzero_seen"))
    )
    if progress:
        return (
            _decision("lower-sequence-summary-progress"),
            True,
            "full lower-sequence summary window observed lower-surface progress",
            "preserve evidence and classify the first progressed surface before Wi-Fi HAL/connect",
        )
    if sampler.get("lower_summary_powerup_seen"):
        return (
            _decision("lower-sequence-full-window-no-transition"),
            True,
            "full lower-sequence summary window saw mdm_subsys_powerup but no PCIe/GDSC/MHI/ks/wlan0 transition",
            "classify exact safe dynamic GDSC/eSoC prerequisite before any PMIC/GPIO/eSoC mutation",
        )
    return _ORIGINAL_DECIDE(manifest)


base._force_response_sampler_child_command = _force_lower_sequence_summary_child_command
base._collect_response_samples = _collect_response_samples_with_summary
base._sample_rows = _sample_rows_with_summary
base.decide_v1242 = decide_v1313


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "plan":
        base.DEFAULT_OUT_DIR = PLAN_OUT_DIR
        base.LATEST_POINTER = PLAN_LATEST_POINTER
    raise SystemExit(base.main())

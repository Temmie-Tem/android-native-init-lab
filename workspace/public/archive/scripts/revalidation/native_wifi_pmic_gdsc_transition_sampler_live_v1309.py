#!/usr/bin/env python3
"""V1309 bounded no-write PMIC/GDSC transition sampler with helper v274."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import native_wifi_compact_powerup_marker_live_v1303 as v1303


base = v1303.base

PMIC_GDSC_TRANSITION_FLAG = "--pm-observer-late-per-proxy-pmic-gdsc-transition-sampler"
EXPECTED_MIN_FOCUSED_SAMPLE_COUNT = 82
SUFFICIENT_PARTIAL_FOCUSED_SAMPLE_COUNT = 70

base.DEFAULT_OUT_DIR = Path("tmp/wifi/v1309-pmic-gdsc-transition-sampler-live")
base.LATEST_POINTER = Path("tmp/wifi/latest-v1309-pmic-gdsc-transition-sampler-live.txt")
base.HELPER_MARKER = "a90_android_execns_probe v274"
base.HELPER_SHA256 = "eb96072631ca38c3296f5da1756a93765e198e8fdd4dc010d087bc4b3b5fc180"
base.CYCLE_LABEL = "v1309"
base.CYCLE_NAME = "V1309"
base.SUMMARY_HEADING = "V1309 PMIC/GDSC Transition Sampler"
base.EVIDENCE_FILE_PREFIX = "v1309"

_ORIGINAL_FORCE = base._force_response_sampler_child_command
_ORIGINAL_COLLECT = base._collect_response_samples
_ORIGINAL_DECIDE = base.decide_v1242
_ORIGINAL_SAMPLE_ROWS = base._sample_rows


def _int_value(value: Any, fallback: int = 0) -> int:
    return base._int_value(value, fallback)


def _force_focused_pmic_gdsc_child_command(original):
    wrapped = _ORIGINAL_FORCE(original)

    def command(args: Any) -> list[str]:
        result = wrapped(args)
        if PMIC_GDSC_TRANSITION_FLAG not in result:
            result.append(PMIC_GDSC_TRANSITION_FLAG)
        return result

    return command


def _collect_response_samples_with_focus(text: str) -> dict[str, Any]:
    result = _ORIGINAL_COLLECT(text)
    keys = base._parse_keys(text)
    focused_samples: dict[str, dict[str, str]] = {}
    for key, value in keys.items():
        if not key.startswith(base.SAMPLE_PREFIX):
            continue
        rest = key[len(base.SAMPLE_PREFIX):]
        if "." not in rest:
            continue
        phase, field = rest.split(".", 1)
        focused_samples.setdefault(phase, {})[field] = value

    focused_phases = sorted(
        phase
        for phase, sample in focused_samples.items()
        if _int_value(sample.get("pmic_gdsc_focus"), 0) == 1
    )
    rows = [focused_samples[phase] for phase in focused_phases]

    result.update({
        "pmic_gdsc_focus_emitted": bool(focused_phases),
        "pmic_gdsc_focus_sample_count": len(focused_phases),
        "pmic_gdsc_focus_phases": focused_phases,
        "pmic_gdsc_focus_completed": all(_int_value(row.get("end"), 0) == 1 for row in rows),
        "pmic_gdsc_focus_max_mhi_pipe_fd_count": max(
            (_int_value(row.get("mhi_pipe_fd_count"), -1) for row in rows),
            default=-1,
        ),
        "pmic_gdsc_focus_max_mhi_pipe_cmdline_count": max(
            (_int_value(row.get("mhi_pipe_cmdline_count"), -1) for row in rows),
            default=-1,
        ),
        "pmic_gdsc_focus_max_ks_process_count": max(
            (_int_value(row.get("ks_process_count"), -1) for row in rows),
            default=-1,
        ),
        "pmic_gdsc_focus_pmic_soft_reset_lines": sorted({
            row.get("pmic_soft_reset_line", "")
            for row in rows
            if row.get("pmic_soft_reset_line")
        }),
        "pmic_gdsc_focus_pcie1_gdsc_lines": sorted({
            row.get("pcie1_gdsc_line", "")
            for row in rows
            if row.get("pcie1_gdsc_line")
        }),
        "pmic_gdsc_focus_pcie0_gdsc_lines": sorted({
            row.get("pcie0_gdsc_line", "")
            for row in rows
            if row.get("pcie0_gdsc_line")
        }),
    })
    return result


def _sample_rows_with_focus(manifest: dict[str, Any]) -> list[list[Any]]:
    rows = _ORIGINAL_SAMPLE_ROWS(manifest)
    sampler = manifest.get("response_sampler") or {}
    rows.extend([
        ["pmic_gdsc_focus_emitted", sampler.get("pmic_gdsc_focus_emitted")],
        ["pmic_gdsc_focus_sample_count", sampler.get("pmic_gdsc_focus_sample_count")],
        ["pmic_gdsc_focus_completed", sampler.get("pmic_gdsc_focus_completed")],
        ["pmic_gdsc_focus_max_mhi_pipe_fd_count", sampler.get("pmic_gdsc_focus_max_mhi_pipe_fd_count")],
        ["pmic_gdsc_focus_max_mhi_pipe_cmdline_count", sampler.get("pmic_gdsc_focus_max_mhi_pipe_cmdline_count")],
        ["pmic_gdsc_focus_max_ks_process_count", sampler.get("pmic_gdsc_focus_max_ks_process_count")],
        ["pmic_gdsc_focus_pmic_soft_reset_lines", " ; ".join(sampler.get("pmic_gdsc_focus_pmic_soft_reset_lines") or [])],
        ["pmic_gdsc_focus_pcie1_gdsc_lines", " ; ".join(sampler.get("pmic_gdsc_focus_pcie1_gdsc_lines") or [])],
        ["pmic_gdsc_focus_pcie0_gdsc_lines", " ; ".join(sampler.get("pmic_gdsc_focus_pcie0_gdsc_lines") or [])],
    ])
    return rows


def _decision(suffix: str) -> str:
    return f"{base.CYCLE_LABEL}-{suffix}"


def decide_v1309(manifest: dict[str, Any]) -> tuple[str, bool, str, str]:
    if manifest.get("command") == "plan":
        return (
            _decision("pmic-gdsc-transition-sampler-plan-ready"),
            True,
            "plan-only; no device mutation or live actor executed",
            "run V1309 bounded no-write PMIC/GDSC transition sampler live",
        )

    sampler = manifest.get("response_sampler") or {}
    mode = str(sampler.get("mode") or "")
    focused_count = int(sampler.get("pmic_gdsc_focus_sample_count") or 0)

    if "focused-pmic-gdsc" not in mode:
        return (
            _decision("focused-pmic-gdsc-mode-missing"),
            False,
            f"helper output mode did not prove focused PMIC/GDSC sampler: mode={mode!r}",
            "verify V1308 helper v274 deploy and flag injection",
        )
    if not sampler.get("pmic_gdsc_focus_emitted"):
        return (
            _decision("focused-pmic-gdsc-samples-missing"),
            False,
            "helper v274 did not emit pmic_gdsc_focus samples",
            "inspect transcript for helper mode mismatch or output truncation",
        )
    complete_window = (
        bool(sampler.get("ended")) and
        bool(sampler.get("pmic_gdsc_focus_completed")) and
        focused_count >= EXPECTED_MIN_FOCUSED_SAMPLE_COUNT
    )
    if focused_count < SUFFICIENT_PARTIAL_FOCUSED_SAMPLE_COUNT:
        return (
            _decision("focused-pmic-gdsc-short-window"),
            False,
            f"focused sampler emitted {focused_count} samples; expected at least {SUFFICIENT_PARTIAL_FOCUSED_SAMPLE_COUNT} for partial-window classification",
            "inspect helper poll window or transcript truncation before rerunning live",
        )

    progress = (
        int(sampler.get("max_mdm_status_count_total") or 0) > 0 or
        int(sampler.get("max_mhi_bus_count") or 0) > 0 or
        bool(sampler.get("mhi_pipe_seen")) or
        bool(sampler.get("wlan0_seen")) or
        int(sampler.get("pmic_gdsc_focus_max_mhi_pipe_fd_count") or 0) > 0 or
        int(sampler.get("pmic_gdsc_focus_max_ks_process_count") or 0) > 0
    )
    if progress:
        return (
            _decision("focused-pmic-gdsc-response-progress"),
            True,
            "focused PMIC/GDSC sampler observed lower-surface progress",
            "preserve evidence and classify the first progressed surface before Wi-Fi HAL/connect",
        )

    pm = manifest.get("pm_service_trigger_observer") or {}
    trigger_seen = bool(pm.get("pm_service_actor_esoc0_attempt")) or bool(
        sampler.get("powerup_subsys_esoc0_inferred_seen")
    )
    window_label = "full" if complete_window else "partial"
    if trigger_seen:
        return (
            _decision(f"focused-pmic-gdsc-{window_label}-window-no-transition"),
            True,
            f"focused {window_label} PMIC/GDSC sampler covered {focused_count} samples during pm-service /dev/subsys_esoc0 powerup, but no PMIC/GDSC/MHI/ks/wlan0 transition was observed",
            "classify exact safe lower prerequisite or reduce helper stdout before any PMIC/GPIO/eSoC mutation",
        )

    decision, passed, reason, next_step = _ORIGINAL_DECIDE(manifest)
    if not passed:
        return decision, passed, reason, next_step
    return (
        _decision("focused-pmic-gdsc-" + decision.removeprefix(base.CYCLE_LABEL + "-")),
        True,
        f"focused PMIC/GDSC sampler completed {focused_count} samples; {reason}",
        next_step,
    )


base._force_response_sampler_child_command = _force_focused_pmic_gdsc_child_command
base._collect_response_samples = _collect_response_samples_with_focus
base._sample_rows = _sample_rows_with_focus
base.decide_v1242 = decide_v1309


if __name__ == "__main__":
    raise SystemExit(base.main())

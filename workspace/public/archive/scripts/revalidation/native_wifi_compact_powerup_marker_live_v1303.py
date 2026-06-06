#!/usr/bin/env python3
"""V1303 bounded compact dense response sampler with v273 powerup markers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import native_wifi_compact_dense_response_sampler_live_v1299 as v1299


base = v1299.base

EXPECTED_MIN_SAMPLE_COUNT = v1299.EXPECTED_MIN_SAMPLE_COUNT
POWERUP_PREFIX = "powerup_marker."

base.DEFAULT_OUT_DIR = Path("tmp/wifi/v1303-compact-powerup-marker-live")
base.LATEST_POINTER = Path("tmp/wifi/latest-v1303-compact-powerup-marker-live.txt")
base.HELPER_MARKER = "a90_android_execns_probe v273"
base.HELPER_SHA256 = "dd1d15a5ef01189526720814c50b007f6dc9a0f25e9239caf0e9da34c65b6b46"
base.CYCLE_LABEL = "v1303"
base.CYCLE_NAME = "V1303"
base.SUMMARY_HEADING = "V1303 Compact Powerup Marker Live"
base.EVIDENCE_FILE_PREFIX = "v1303"

_ORIGINAL_COLLECT = base._collect_response_samples
_ORIGINAL_DECIDE = base.decide_v1242
_ORIGINAL_SAMPLE_ROWS = base._sample_rows


def _int_value(value: Any, fallback: int = 0) -> int:
    return base._int_value(value, fallback)


def _collect_response_samples_with_powerup(text: str) -> dict[str, Any]:
    result = _ORIGINAL_COLLECT(text)
    keys = base._parse_keys(text)
    markers: dict[str, dict[str, str]] = {}
    for key, value in keys.items():
        if not key.startswith(base.SAMPLE_PREFIX):
            continue
        rest = key[len(base.SAMPLE_PREFIX):]
        if "." not in rest:
            continue
        phase, field = rest.split(".", 1)
        if not field.startswith(POWERUP_PREFIX):
            continue
        markers.setdefault(phase, {})[field[len(POWERUP_PREFIX):]] = value

    phases = sorted(markers)
    powerup_counts = [_int_value(markers[phase].get("powerup_thread_count"), -1) for phase in phases]
    inferred = [_int_value(markers[phase].get("subsys_esoc0_open_inferred"), -1) for phase in phases]
    first_paths = sorted({
        markers[phase].get("first_syscall.path.value", "")
        for phase in phases
        if markers[phase].get("first_syscall.path.value")
    })
    result.update({
        "powerup_marker_emitted": bool(phases),
        "powerup_marker_phase_count": len(phases),
        "powerup_marker_phases": phases,
        "max_powerup_thread_count": max(powerup_counts, default=-1),
        "powerup_subsys_esoc0_inferred_seen": any(value > 0 for value in inferred),
        "powerup_first_path_values": first_paths,
        "powerup_first_wchans": sorted({
            markers[phase].get("first_wchan", "")
            for phase in phases
            if markers[phase].get("first_wchan")
        }),
        "powerup_first_syscall_names": sorted({
            markers[phase].get("first_syscall_name", "")
            for phase in phases
            if markers[phase].get("first_syscall_name")
        }),
        "powerup_samples": [
            {
                "phase": phase,
                "process_count": _int_value(markers[phase].get("per_mgr_process_count"), -1),
                "thread_count": _int_value(markers[phase].get("per_mgr_thread_count"), -1),
                "powerup_thread_count": _int_value(markers[phase].get("powerup_thread_count"), -1),
                "subsys_esoc0_open_inferred": _int_value(markers[phase].get("subsys_esoc0_open_inferred"), -1),
                "first_pid": _int_value(markers[phase].get("first_pid"), -1),
                "first_tid": _int_value(markers[phase].get("first_tid"), -1),
                "first_state": markers[phase].get("first_state", ""),
                "first_wchan": markers[phase].get("first_wchan", ""),
                "first_syscall_name": markers[phase].get("first_syscall_name", ""),
                "first_syscall_path": markers[phase].get("first_syscall.path.value", ""),
            }
            for phase in phases
        ],
    })
    return result


def _sample_rows_with_powerup(manifest: dict[str, Any]) -> list[list[Any]]:
    rows = _ORIGINAL_SAMPLE_ROWS(manifest)
    sampler = manifest.get("response_sampler") or {}
    rows.extend([
        ["powerup_marker_emitted", sampler.get("powerup_marker_emitted")],
        ["powerup_marker_phase_count", sampler.get("powerup_marker_phase_count")],
        ["max_powerup_thread_count", sampler.get("max_powerup_thread_count")],
        ["powerup_subsys_esoc0_inferred_seen", sampler.get("powerup_subsys_esoc0_inferred_seen")],
        ["powerup_first_path_values", " ; ".join(sampler.get("powerup_first_path_values") or [])],
        ["powerup_first_wchans", " ; ".join(sampler.get("powerup_first_wchans") or [])],
        ["powerup_first_syscall_names", " ; ".join(sampler.get("powerup_first_syscall_names") or [])],
    ])
    return rows


def _decision(suffix: str) -> str:
    return f"{base.CYCLE_LABEL}-{suffix}"


def decide_v1303(manifest: dict[str, Any]) -> tuple[str, bool, str, str]:
    if manifest.get("command") == "plan":
        return (
            _decision("compact-powerup-marker-plan-ready"),
            True,
            "plan-only; no device mutation or live actor executed",
            "run V1303 bounded compact dense sampler with powerup marker gate",
        )

    sampler = manifest.get("response_sampler") or {}
    sample_count = int(sampler.get("sample_count") or 0)
    marker_count = int(sampler.get("powerup_marker_phase_count") or 0)

    if not sampler.get("powerup_marker_emitted"):
        return (
            _decision("powerup-marker-missing"),
            False,
            "helper v273 did not emit compact powerup_marker keys",
            "verify V1302 deploy and helper marker before rerunning live",
        )
    if marker_count < min(sample_count, EXPECTED_MIN_SAMPLE_COUNT):
        return (
            _decision("powerup-marker-short-window"),
            False,
            f"powerup_marker emitted {marker_count} phases for {sample_count} response samples",
            "inspect transcript for parser drift or output truncation",
        )

    progress = (
        int(sampler.get("max_mdm_status_count_total") or 0) > 0 or
        int(sampler.get("max_mhi_bus_count") or 0) > 0 or
        bool(sampler.get("mhi_pipe_seen")) or
        bool(sampler.get("wlan0_seen"))
    )
    if sampler.get("powerup_subsys_esoc0_inferred_seen") and not progress:
        pm = manifest.get("pm_service_trigger_observer") or {}
        all_postflight_safe = int(pm.get("all_postflight_safe") or 0)
        if all_postflight_safe <= 0:
            return (
                _decision("powerup-marker-pm-esoc0-trigger-sampled-mdm2ap-silent-reboot-required"),
                True,
                "powerup_marker proves pm-service reached /dev/subsys_esoc0/openat/mdm_subsys_powerup, but GPIO142/MHI/wlan0 stayed absent and cleanup was not proven safe",
                "reboot/health-check if needed, then classify SDX50M AP2MDM/MDM2AP response prerequisites before another trigger",
            )
        return (
            _decision("powerup-marker-pm-esoc0-trigger-sampled-mdm2ap-silent"),
            True,
            "powerup_marker proves pm-service reached /dev/subsys_esoc0/openat/mdm_subsys_powerup, but GPIO142/MHI/wlan0 stayed absent",
            "classify SDX50M AP2MDM/MDM2AP response prerequisites before another trigger",
        )

    decision, passed, reason, next_step = _ORIGINAL_DECIDE(manifest)
    if not passed:
        return decision, passed, reason, next_step
    return (
        _decision("compact-powerup-marker-" + decision.removeprefix(base.CYCLE_LABEL + "-")),
        True,
        f"powerup_marker covered {marker_count} phases; {reason}",
        next_step,
    )


base._collect_response_samples = _collect_response_samples_with_powerup
base._sample_rows = _sample_rows_with_powerup
base.decide_v1242 = decide_v1303


if __name__ == "__main__":
    raise SystemExit(base.main())

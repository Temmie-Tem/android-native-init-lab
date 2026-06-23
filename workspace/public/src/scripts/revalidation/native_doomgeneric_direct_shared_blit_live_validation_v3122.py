#!/usr/bin/env python3
"""V3122 rollback-gated live validation for V3120 DOOM direct shared blit."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import native_doomgeneric_no_full_clear_live_validation_v3119 as v3119

base = v3119.base
ROOT = v3119.ROOT

RUN_ID = "V3122"
BUILD_TAG = "v3122-doomgeneric-direct-shared-blit-live"
DECISION_PREFIX = "v3122-doomgeneric-direct-shared-blit"
REPORT_PATH = ROOT / "docs/reports/NATIVE_INIT_V3122_DOOMGENERIC_DIRECT_SHARED_BLIT_LIVE_2026-06-23.md"

CANDIDATE_IMAGE = ROOT / "workspace/private/inputs/boot_images/boot_linux_v3120_doomgeneric_direct_shared_blit.img"
CANDIDATE_VERSION = "0.10.115"
CANDIDATE_TAG = "v3120-doomgeneric-direct-shared-blit"
CANDIDATE_SHA256 = "fb7d561731a0b426f03fc70050a80d57ad33897f3befffd9d22d187d22fbb9e3"

ROLLBACK_IMAGE = v3119.ROLLBACK_IMAGE
ROLLBACK_VERSION = v3119.ROLLBACK_VERSION
ROLLBACK_SHA256 = v3119.ROLLBACK_SHA256
FALLBACK_V2237 = v3119.FALLBACK_V2237
FALLBACK_V2237_SHA256 = v3119.FALLBACK_V2237_SHA256
FALLBACK_V48 = v3119.FALLBACK_V48
EXPECTED_WAD_SHA256 = v3119.EXPECTED_WAD_SHA256
DEFAULT_FRAMES = v3119.DEFAULT_FRAMES

EXPECTED_READER = "shared-mmap-direct-blit"
V3119_READ_AVG_US = 477
V3119_DRAW_AVG_US = 4816
READ_IMPROVED_THRESHOLD_US = 250

LOOP_MARKERS = v3119.LOOP_MARKERS + (
    "video.demo.doom.loop.presenter.reader=shared-mmap-direct-blit",
)

v3119._apply_v3119_globals()
_base_preflight_state = v3119.preflight_state
_base_parse_loop_output = v3119.parse_loop_output
_base_loop_classification = v3119.loop_classification
_base_live_pass = v3119.live_pass
_base_preflight_ok = v3119.preflight_ok


def _apply_v3122_globals() -> None:
    v3119.RUN_ID = RUN_ID
    v3119.BUILD_TAG = BUILD_TAG
    v3119.DECISION_PREFIX = DECISION_PREFIX
    v3119.REPORT_PATH = REPORT_PATH
    v3119.CANDIDATE_IMAGE = CANDIDATE_IMAGE
    v3119.CANDIDATE_VERSION = CANDIDATE_VERSION
    v3119.CANDIDATE_TAG = CANDIDATE_TAG
    v3119.CANDIDATE_SHA256 = CANDIDATE_SHA256
    v3119.LOOP_MARKERS = LOOP_MARKERS
    v3119.preflight_state = preflight_state
    v3119.parse_loop_output = parse_loop_output
    v3119.loop_classification = loop_classification
    v3119.live_pass = live_pass
    v3119.render_report = render_report
    v3119.dry_run_payload = dry_run_payload


def now_slug() -> str:
    return v3119.now_slug()


def rel(path: Path | str | None) -> str | None:
    return v3119.rel(path)


def parse_key_values(text: str) -> dict[str, list[str]]:
    return v3119.parse_key_values(text)


def _last_int(values: dict[str, list[str]], key: str) -> int | None:
    return v3119._last_int(values, key)


def _last_value(values: dict[str, list[str]], key: str) -> str | None:
    return v3119._last_value(values, key)


def preflight_state(args: argparse.Namespace) -> dict[str, Any]:
    _apply_v3122_globals()
    try:
        state = _base_preflight_state(args)
    finally:
        v3119._apply_v3119_globals()
    state.update({
        "run_id": RUN_ID,
        "candidate_version": CANDIDATE_VERSION,
        "candidate_tag": CANDIDATE_TAG,
        "expected_reader": EXPECTED_READER,
        "expected_reader_marker": "video.demo.doom.loop.presenter.reader=shared-mmap-direct-blit",
        "v3119_read_avg_us": V3119_READ_AVG_US,
        "v3119_draw_avg_us": V3119_DRAW_AVG_US,
        "read_improved_threshold_us": READ_IMPROVED_THRESHOLD_US,
    })
    return state


def preflight_ok(state: dict[str, Any]) -> bool:
    return _base_preflight_ok(state)


def parse_loop_output(text: str) -> dict[str, Any]:
    _apply_v3122_globals()
    try:
        parsed = _base_parse_loop_output(text)
    finally:
        v3119._apply_v3119_globals()
    values = parse_key_values(text)
    presenter_reader = _last_value(values, "video.demo.doom.loop.presenter.reader")
    read_avg_us = parsed.get("timing_read_avg_us")
    draw_avg_us = parsed.get("timing_draw_avg_us")
    read_improved = (
        isinstance(read_avg_us, int)
        and read_avg_us < READ_IMPROVED_THRESHOLD_US
    )
    read_delta = read_avg_us - V3119_READ_AVG_US if isinstance(read_avg_us, int) else None
    draw_delta = draw_avg_us - V3119_DRAW_AVG_US if isinstance(draw_avg_us, int) else None
    parsed.update({
        "presenter_reader": presenter_reader,
        "direct_shared_blit_markers_ok": presenter_reader == EXPECTED_READER,
        "v3119_read_avg_us": V3119_READ_AVG_US,
        "v3119_draw_avg_us": V3119_DRAW_AVG_US,
        "read_improved_threshold_us": READ_IMPROVED_THRESHOLD_US,
        "read_improved_vs_v3119": read_improved,
        "read_delta_vs_v3119_us": read_delta,
        "draw_delta_vs_v3119_us": draw_delta,
    })
    return parsed


def loop_classification(loop: dict[str, Any], requested_frames: int) -> str:
    base_classification = _base_loop_classification(loop, requested_frames)
    if base_classification in {
        "loop-not-clean",
        "prescaled-marker-missing",
        "no-full-clear-marker-missing",
    }:
        return base_classification
    if not loop.get("direct_shared_blit_markers_ok"):
        return "direct-shared-blit-marker-missing"
    return base_classification


def live_pass(result: dict[str, Any]) -> bool:
    loop = result.get("doom_loop", {}) if isinstance(result.get("doom_loop"), dict) else {}
    return bool(_base_live_pass(result) and loop.get("direct_shared_blit_markers_ok"))


def _marker_lines(summary: dict[str, Any]) -> list[str]:
    if not summary:
        return ["- none captured in this run"]
    return [f"- `{marker}`: `{int(bool(ok))}`" for marker, ok in sorted(summary.items())]


def render_report(result: dict[str, Any]) -> str:
    live_executed = bool(result.get("live_executed"))
    preflight = result.get("preflight", {}) if isinstance(result.get("preflight"), dict) else {}
    loop = result.get("doom_loop", {}) if isinstance(result.get("doom_loop"), dict) else {}
    preflight_status = result.get("preflight_ok")
    if preflight_status is None and all(
        key in preflight for key in ("candidate", "rollback", "fallback_v2237", "fallback_v48", "flash_helper")
    ):
        preflight_status = preflight_ok(preflight)

    def live_bool(value: Any) -> str:
        return str(int(bool(value))) if live_executed else "not-run"

    def live_value(value: Any) -> str:
        return str(value) if live_executed else "not-run"

    return "\n".join([
        "# Native Init V3122 DOOMGENERIC Direct Shared Blit Live Validation",
        "",
        "## Summary",
        "",
        f"- Decision: `{result.get('decision')}`",
        f"- Result before rollback: `{int(bool(result.get('pass')))}`",
        f"- Loop classification: `{result.get('loop_classification', 'not-run')}`",
        "- Track: DOOM frame IPC/copy reduction.",
        f"- Candidate: `A90 Linux init {CANDIDATE_VERSION} ({CANDIDATE_TAG})`",
        f"- Candidate image: `{rel(CANDIDATE_IMAGE)}`",
        f"- Candidate SHA256: `{CANDIDATE_SHA256}`",
        f"- Private run dir: `{result.get('out_dir')}`",
        f"- Live execution: `{int(live_executed)}`",
        "",
        "## Preflight",
        "",
        f"- Preflight ok: `{int(bool(preflight_status))}`",
        f"- Candidate SHA256 ok: `{int(bool((preflight.get('candidate') or {}).get('sha256_ok')))}`",
        f"- Rollback v2321 SHA256 ok: `{int(bool((preflight.get('rollback') or {}).get('sha256_ok')))}`",
        f"- Fallback v2237 SHA256 ok: `{int(bool((preflight.get('fallback_v2237') or {}).get('sha256_ok')))}`",
        f"- Fallback v48 exists: `{int(bool((preflight.get('fallback_v48') or {}).get('exists')))}`",
        f"- Flash helper exists: `{int(bool((preflight.get('flash_helper') or {}).get('exists')))}`",
        f"- Recovery gate: `{preflight.get('recovery_gate', '-')}`",
        f"- Expected reader: `{EXPECTED_READER}`",
        f"- V3119 read/draw avg baseline us: `{V3119_READ_AVG_US}` / `{V3119_DRAW_AVG_US}`",
        "",
        "## Live Evidence",
        "",
        f"- Pre-flash current version: `{live_value(result.get('preflash_version'))}`",
        f"- Pre-flash selftest fail=0: `{live_bool(result.get('preflash_selftest_fail0'))}`",
        f"- Candidate version ok: `{live_bool(result.get('candidate_version_ok'))}`",
        f"- Candidate selftest fail=0: `{live_bool(result.get('candidate_selftest_fail0'))}`",
        f"- Candidate hide-before-loop ok: `{live_bool(result.get('candidate_hide_before_loop_ok'))}`",
        f"- DOOM loop rc: `{live_value(result.get('doom_loop_rc'))}` transport_rc=`{live_value(result.get('doom_loop_transport_rc'))}` protocol_end=`{live_bool(result.get('doom_loop_protocol_end_present'))}`",
        f"- Frames requested/presented: `{preflight.get('frames', 'not-run')}` / `{live_value(loop.get('frames_presented'))}`",
        f"- Direct reader marker: `{live_value(loop.get('presenter_reader'))}` ok=`{live_bool(loop.get('direct_shared_blit_markers_ok'))}`",
        f"- Pre-scaled marker count: `{live_value(loop.get('pre_scaled_count'))}` markers_ok=`{live_bool(loop.get('producer_markers_ok'))}`",
        f"- No-full-clear markers: full_clear=`{live_value(loop.get('full_clear'))}` clear_path=`{live_value(loop.get('clear_path'))}` ok=`{live_bool(loop.get('no_full_clear_markers_ok'))}`",
        f"- Frame mode/scale/path: `{live_value(loop.get('frame_mode'))}` / `{live_value(loop.get('frame_scale'))}` / `{live_value(loop.get('scale_path'))}`",
        f"- Timing alloc/read/begin avg us: `{live_value(loop.get('timing_alloc_avg_us'))}` / `{live_value(loop.get('timing_read_avg_us'))}` / `{live_value(loop.get('timing_begin_avg_us'))}`",
        f"- Read avg vs V3119: improved=`{live_bool(loop.get('read_improved_vs_v3119'))}` delta_us=`{live_value(loop.get('read_delta_vs_v3119_us'))}` threshold_us=`{READ_IMPROVED_THRESHOLD_US}` baseline_us=`{V3119_READ_AVG_US}`",
        f"- Timing draw avg/max us: `{live_value(loop.get('timing_draw_avg_us'))}` / `{live_value(loop.get('timing_draw_max_us'))}` delta_vs_v3119_us=`{live_value(loop.get('draw_delta_vs_v3119_us'))}`",
        f"- Timing present avg us: `{live_value(loop.get('timing_present_avg_us'))}`",
        f"- Timing total avg/max us: `{live_value(loop.get('timing_total_avg_us'))}` / `{live_value(loop.get('timing_total_max_us'))}`",
        f"- Flip events: `{live_value(loop.get('flip_events'))}` delta avg/max us: `{live_value(loop.get('flip_delta_avg_us'))}` / `{live_value(loop.get('flip_delta_max_us'))}` 60hz_stable=`{live_bool(loop.get('pageflip_60hz_stable'))}` 30hz_stable=`{live_bool(loop.get('pageflip_30hz_stable'))}`",
        f"- Shared seq missed/max-gap: `{live_value(loop.get('seq_shared_missed_frames'))}` / `{live_value(loop.get('seq_shared_max_sequence_gap_frames'))}` clean=`{live_bool(loop.get('shared_seq_clean'))}`",
        f"- Duplicate frame polls: `{live_value(loop.get('seq_duplicate_frame_polls'))}`",
        f"- Candidate post-loop selftest fail=0: `{live_bool(result.get('candidate_selftest_after_loop_fail0'))}`",
        "",
        "## Loop Markers",
        "",
        *_marker_lines(loop.get("markers", {}) if isinstance(loop.get("markers"), dict) else {}),
        "",
        "## Rollback Evidence",
        "",
        f"- Rollback attempted: `{int(bool(result.get('rollback_attempted')))}`",
        f"- Rollback step ok: `{int(bool(result.get('rollback_step_ok')))}`",
        f"- Rollback health: version_ok=`{int(bool(result.get('rollback_version_ok')))}` selftest_fail0=`{int(bool(result.get('rollback_selftest_fail0')))}`",
        "",
        "## Interpretation",
        "",
        "- `direct-shared-blit-marker-missing` means the image did not exercise the intended direct mmap source path.",
        "- If the direct marker is present and read avg drops, the shared-frame heap staging copy was measurable overhead.",
        "- If the direct marker is present but read avg stays near V3119, the remaining visible cost is draw/present cadence, producer pixel work, or DOOM's 35 Hz game-tic cadence rather than the presenter staging copy.",
        "- If pageflip is stable and shared sequence is clean, residual motion stepping is still the known original-speed DOOM 35 Hz cadence on a 60 Hz panel.",
        "- This candidate still uses bounded tone co-run, not real DOOM music/SFX.",
        "",
        "## Safety",
        "",
        "- Live mode flashes only the boot partition through `native_init_flash.py`; rollback target remains `v2321`.",
        "- The validation path hides the auto menu and then runs one bounded foreground `video demo doom loop` over the serial command bridge.",
        "- No Wi-Fi connect/dhcp/ping, PMIC, backlight, GPIO, regulator, GDSC, panel re-init, GPU/GL stack, or forbidden partition path is touched.",
        "- Raw command output stays private under `workspace/private/runs/`; this report includes metadata only.",
        "",
        "## Host Validation",
        "",
        "- `py_compile`: V3122 live runner and focused tests.",
        "- `unittest`: V3122 live parser/report/preflight contract.",
        "- dry-run preflight/report: PASS when preflight assets are present.",
        "- `git diff --check`: PASS",
    ]) + "\n"


def dry_run_payload(args: argparse.Namespace, state: dict[str, Any]) -> dict[str, Any]:
    return {
        "decision": f"{DECISION_PREFIX}-dry-run" if preflight_ok(state) else f"{DECISION_PREFIX}-preflight-failed",
        "ok": preflight_ok(state),
        "preflight": state,
        "commands": [
            "verify current resident version/status/selftest over serial",
            f"flash exact V3120 image {CANDIDATE_IMAGE}",
            "version/status/selftest",
            "hide auto menu before foreground DOOM loop",
            f"video demo doom loop {args.frames} --wad runtime-private --sha256 {EXPECTED_WAD_SHA256}",
            "parse direct-shared-blit marker, no-full-clear/pre-scaled markers, timing, seq, and pageflip markers",
            "selftest verbose after bounded loop",
            "rollback v2321 and verify selftest fail=0",
        ],
    }


def run_live(args: argparse.Namespace, out_dir: Path, state: dict[str, Any]) -> dict[str, Any]:
    _apply_v3122_globals()
    return v3119.run_live(args, out_dir, state)


def main() -> int:
    _apply_v3122_globals()
    return v3119.main()


if __name__ == "__main__":
    raise SystemExit(main())

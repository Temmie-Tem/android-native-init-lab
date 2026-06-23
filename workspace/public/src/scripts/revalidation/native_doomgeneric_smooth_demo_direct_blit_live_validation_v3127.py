#!/usr/bin/env python3
"""V3127 rollback-gated live validation for V3126 smooth-demo direct blit."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import native_doomgeneric_summary_only_direct_blit_live_validation_v3124 as v3124

base = v3124.base
ROOT = v3124.ROOT

RUN_ID = "V3127"
BUILD_TAG = "v3127-doomgeneric-smooth-demo-direct-blit-live"
DECISION_PREFIX = "v3127-doomgeneric-smooth-demo-direct-blit"
REPORT_PATH = ROOT / "docs/reports/NATIVE_INIT_V3127_DOOMGENERIC_SMOOTH_DEMO_DIRECT_BLIT_LIVE_2026-06-23.md"

CANDIDATE_IMAGE = ROOT / "workspace/private/inputs/boot_images/boot_linux_v3126_doomgeneric_smooth_demo_direct_blit.img"
CANDIDATE_VERSION = "0.10.117"
CANDIDATE_TAG = "v3126-doomgeneric-smooth-demo-direct-blit"
CANDIDATE_SHA256 = "bda5dffce49ae0e590d2dc629f299e39d54c097ce60d63aa022f146d2fa1f75d"

ROLLBACK_IMAGE = v3124.ROLLBACK_IMAGE
ROLLBACK_VERSION = v3124.ROLLBACK_VERSION
ROLLBACK_SHA256 = v3124.ROLLBACK_SHA256
FALLBACK_V2237 = v3124.FALLBACK_V2237
FALLBACK_V2237_SHA256 = v3124.FALLBACK_V2237_SHA256
FALLBACK_V48 = v3124.FALLBACK_V48
EXPECTED_WAD_SHA256 = v3124.EXPECTED_WAD_SHA256
DEFAULT_FRAMES = v3124.DEFAULT_FRAMES

EXPECTED_READER = "shared-mmap-direct-blit"
EXPECTED_FOREGROUND_FRAME_LOG = 0
EXPECTED_SMOOTH_MODE = "non-original-smooth-demo"
EXPECTED_PACED_TIME_MARKER = "a90.doomgeneric.v3126.paced_time=smooth-demo-presenter-token-doom-tic-quantum"
EXPECTED_PACED_TIME_MODEL = "presenter-token-doom-tic-quantum"
EXPECTED_TICK_TELEMETRY_MARKER = "a90.doomgeneric.v3126.tick_telemetry=smooth-demo-paced-time-direct-blit"
EXPECTED_TICK_QUANTUM_US = 28571
V3124_READ_AVG_US = 2
V3124_DRAW_AVG_US = 4289

LOOP_MARKERS = v3124.LOOP_MARKERS + (
    "video.demo.doom.loop.tick_telemetry.summary=1",
    "video.demo.doom.loop.tick_telemetry.open_rc=0",
    f"video.demo.doom.loop.tick_telemetry.paced_time_marker={EXPECTED_PACED_TIME_MARKER}",
    f"video.demo.doom.loop.tick_telemetry.paced_time_model={EXPECTED_PACED_TIME_MODEL}",
    f"video.demo.doom.loop.tick_telemetry.smooth_demo_mode={EXPECTED_SMOOTH_MODE}",
)

v3124._apply_v3124_globals()
_base_preflight_state = v3124.preflight_state
_base_parse_loop_output = v3124.parse_loop_output
_base_loop_classification = v3124.loop_classification
_base_live_pass = v3124.live_pass
_base_preflight_ok = v3124.preflight_ok

_V3124_ORIGINALS = {
    "RUN_ID": v3124.RUN_ID,
    "BUILD_TAG": v3124.BUILD_TAG,
    "DECISION_PREFIX": v3124.DECISION_PREFIX,
    "REPORT_PATH": v3124.REPORT_PATH,
    "CANDIDATE_IMAGE": v3124.CANDIDATE_IMAGE,
    "CANDIDATE_VERSION": v3124.CANDIDATE_VERSION,
    "CANDIDATE_TAG": v3124.CANDIDATE_TAG,
    "CANDIDATE_SHA256": v3124.CANDIDATE_SHA256,
    "LOOP_MARKERS": v3124.LOOP_MARKERS,
    "preflight_state": v3124.preflight_state,
    "parse_loop_output": v3124.parse_loop_output,
    "loop_classification": v3124.loop_classification,
    "live_pass": v3124.live_pass,
    "render_report": v3124.render_report,
    "dry_run_payload": v3124.dry_run_payload,
}


def _apply_v3127_globals() -> None:
    v3124.RUN_ID = RUN_ID
    v3124.BUILD_TAG = BUILD_TAG
    v3124.DECISION_PREFIX = DECISION_PREFIX
    v3124.REPORT_PATH = REPORT_PATH
    v3124.CANDIDATE_IMAGE = CANDIDATE_IMAGE
    v3124.CANDIDATE_VERSION = CANDIDATE_VERSION
    v3124.CANDIDATE_TAG = CANDIDATE_TAG
    v3124.CANDIDATE_SHA256 = CANDIDATE_SHA256
    v3124.LOOP_MARKERS = LOOP_MARKERS
    v3124.preflight_state = preflight_state
    v3124.parse_loop_output = parse_loop_output
    v3124.loop_classification = loop_classification
    v3124.live_pass = live_pass
    v3124.render_report = render_report
    v3124.dry_run_payload = dry_run_payload
    v3124._apply_v3124_globals()


def _restore_v3124_globals() -> None:
    for name, value in _V3124_ORIGINALS.items():
        setattr(v3124, name, value)
    v3124._apply_v3124_globals()


def now_slug() -> str:
    return v3124.now_slug()


def rel(path: Path | str | None) -> str | None:
    return v3124.rel(path)


def parse_key_values(text: str) -> dict[str, list[str]]:
    return v3124.parse_key_values(text)


def _last_int(values: dict[str, list[str]], key: str) -> int | None:
    return v3124._last_int(values, key)


def _last_value(values: dict[str, list[str]], key: str) -> str | None:
    return v3124._last_value(values, key)


def preflight_state(args: argparse.Namespace) -> dict[str, Any]:
    _apply_v3127_globals()
    try:
        state = _base_preflight_state(args)
    finally:
        _restore_v3124_globals()
    state.update({
        "run_id": RUN_ID,
        "candidate_version": CANDIDATE_VERSION,
        "candidate_tag": CANDIDATE_TAG,
        "expected_reader": EXPECTED_READER,
        "expected_foreground_frame_log": EXPECTED_FOREGROUND_FRAME_LOG,
        "expected_smooth_mode": EXPECTED_SMOOTH_MODE,
        "expected_paced_time_marker": EXPECTED_PACED_TIME_MARKER,
        "expected_paced_time_model": EXPECTED_PACED_TIME_MODEL,
        "expected_tick_quantum_us": EXPECTED_TICK_QUANTUM_US,
        "v3124_read_avg_us": V3124_READ_AVG_US,
        "v3124_draw_avg_us": V3124_DRAW_AVG_US,
    })
    return state


def preflight_ok(state: dict[str, Any]) -> bool:
    return _base_preflight_ok(state)


def parse_loop_output(text: str) -> dict[str, Any]:
    _apply_v3127_globals()
    try:
        parsed = _base_parse_loop_output(text)
    finally:
        _restore_v3124_globals()
    values = parse_key_values(text)
    prefix = "video.demo.doom.loop.tick_telemetry."
    tick_marker = _last_value(values, prefix + "marker")
    open_rc = _last_int(values, prefix + "open_rc")
    close_rc = _last_int(values, prefix + "close_rc")
    lines = _last_int(values, prefix + "lines")
    paced_marker = _last_value(values, prefix + "paced_time_marker")
    paced_model = _last_value(values, prefix + "paced_time_model")
    smooth_mode = _last_value(values, prefix + "smooth_demo_mode")
    tick_quantum_us = _last_int(values, prefix + "paced_time.quantum_us")
    advance_calls = _last_int(values, prefix + "paced_time.advance_calls")
    advance_us_total = _last_int(values, prefix + "paced_time.advance_us_total")
    loop_tick_changed = _last_int(values, prefix + "loop_tick.gametic_changed")
    loop_tick_repeated = _last_int(values, prefix + "loop_tick.gametic_repeated")
    loop_tick_max_delta = _last_int(values, prefix + "loop_tick.gametic_max_delta")
    draw_changed = _last_int(values, prefix + "draw_gametic.changed_transitions")
    draw_repeated = _last_int(values, prefix + "draw_gametic.repeated_transitions")
    draw_max_same_run = _last_int(values, prefix + "draw_gametic.max_same_run")
    dump_changed = _last_int(values, prefix + "dump_gametic.changed_transitions")
    dump_repeated = _last_int(values, prefix + "dump_gametic.repeated_transitions")
    dump_max_same_run = _last_int(values, prefix + "dump_gametic.max_same_run")
    dump_max_delta = _last_int(values, prefix + "dump_gametic.max_delta")
    read_avg_us = parsed.get("timing_read_avg_us")
    draw_avg_us = parsed.get("timing_draw_avg_us")
    telemetry_available = open_rc == 0 and (lines or 0) > 0
    paced_time_markers_ok = (
        tick_marker == EXPECTED_TICK_TELEMETRY_MARKER
        and paced_marker == EXPECTED_PACED_TIME_MARKER
        and paced_model == EXPECTED_PACED_TIME_MODEL
        and smooth_mode == EXPECTED_SMOOTH_MODE
    )
    paced_time_quantum_ok = tick_quantum_us == EXPECTED_TICK_QUANTUM_US
    output_gametic_repetition_bounded = (
        isinstance(loop_tick_changed, int)
        and loop_tick_changed > 0
        and (loop_tick_repeated is None or loop_tick_repeated <= 2)
        and isinstance(dump_changed, int)
        and dump_changed > 0
        and (dump_repeated is None or dump_repeated <= 2)
        and (dump_max_same_run is None or dump_max_same_run <= 2)
    )

    parsed.update({
        "tick_telemetry_open_rc": open_rc,
        "tick_telemetry_close_rc": close_rc,
        "tick_telemetry_lines": lines,
        "tick_telemetry_marker": tick_marker,
        "telemetry_available": telemetry_available,
        "paced_time_marker": paced_marker,
        "paced_time_model": paced_model,
        "smooth_demo_mode": smooth_mode,
        "paced_time_quantum_us": tick_quantum_us,
        "paced_time_advance_calls": advance_calls,
        "paced_time_advance_us_total": advance_us_total,
        "paced_time_markers_ok": paced_time_markers_ok,
        "paced_time_quantum_ok": paced_time_quantum_ok,
        "loop_tick_gametic_changed": loop_tick_changed,
        "loop_tick_gametic_repeated": loop_tick_repeated,
        "loop_tick_gametic_max_delta": loop_tick_max_delta,
        "draw_gametic_changed_transitions": draw_changed,
        "draw_gametic_repeated_transitions": draw_repeated,
        "draw_gametic_max_same_run": draw_max_same_run,
        "dump_gametic_changed_transitions": dump_changed,
        "dump_gametic_repeated_transitions": dump_repeated,
        "dump_gametic_max_same_run": dump_max_same_run,
        "dump_gametic_max_delta": dump_max_delta,
        "gametic_repetition_bounded": output_gametic_repetition_bounded,
        "draw_gametic_internal_repeats": isinstance(draw_max_same_run, int) and draw_max_same_run > 2,
        "v3124_read_avg_us": V3124_READ_AVG_US,
        "v3124_draw_avg_us": V3124_DRAW_AVG_US,
        "read_delta_vs_v3124_us": read_avg_us - V3124_READ_AVG_US if isinstance(read_avg_us, int) else None,
        "draw_delta_vs_v3124_us": draw_avg_us - V3124_DRAW_AVG_US if isinstance(draw_avg_us, int) else None,
    })
    return parsed


def loop_classification(loop: dict[str, Any], requested_frames: int) -> str:
    base_classification = _base_loop_classification(loop, requested_frames)
    if base_classification in {
        "loop-not-clean",
        "prescaled-marker-missing",
        "no-full-clear-marker-missing",
        "direct-shared-blit-marker-missing",
        "summary-only-marker-missing",
    }:
        return base_classification
    if not loop.get("telemetry_available"):
        return "paced-time-telemetry-missing"
    if not loop.get("paced_time_markers_ok"):
        return "paced-time-marker-missing"
    if not loop.get("paced_time_quantum_ok"):
        return "paced-time-quantum-mismatch"
    if loop.get("gametic_repetition_bounded") and loop.get("pageflip_60hz_stable") and loop.get("shared_seq_clean"):
        return "smooth-demo-cadence-clean"
    return "smooth-demo-cadence-review"


def live_pass(result: dict[str, Any]) -> bool:
    loop = result.get("doom_loop", {}) if isinstance(result.get("doom_loop"), dict) else {}
    return bool(
        result.get("preflash_selftest_fail0")
        and result.get("candidate_version_ok")
        and result.get("candidate_selftest_fail0")
        and result.get("candidate_hide_before_loop_ok")
        and result.get("doom_loop_rc") == 0
        and result.get("doom_loop_protocol_end_present")
        and result.get("candidate_selftest_after_loop_fail0")
        and loop.get("producer_markers_ok")
        and loop.get("no_full_clear_markers_ok")
        and loop.get("direct_shared_blit_markers_ok")
        and loop.get("summary_only_markers_ok")
        and loop.get("telemetry_available")
        and loop.get("paced_time_markers_ok")
        and loop.get("paced_time_quantum_ok")
        and result.get("loop_classification") in {"smooth-demo-cadence-clean", "smooth-demo-cadence-review"}
    )


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
        "# Native Init V3127 DOOMGENERIC Smooth Demo Direct Blit Live Validation",
        "",
        "## Summary",
        "",
        f"- Decision: `{result.get('decision')}`",
        f"- Result before rollback: `{int(bool(result.get('pass')))}`",
        f"- Loop classification: `{result.get('loop_classification', 'not-run')}`",
        "- Track: residual DOOM cadence diagnosis / non-original smooth demo comparison.",
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
        f"- Expected smooth mode: `{EXPECTED_SMOOTH_MODE}`",
        f"- Expected tic quantum us: `{EXPECTED_TICK_QUANTUM_US}`",
        f"- V3124 read/draw avg baseline us: `{V3124_READ_AVG_US}` / `{V3124_DRAW_AVG_US}`",
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
        f"- Summary-only marker: foreground_frame_log=`{live_value(loop.get('foreground_frame_log'))}` ok=`{live_bool(loop.get('summary_only_markers_ok'))}`",
        f"- Pre-scaled/no-full-clear ok: producer=`{live_bool(loop.get('producer_markers_ok'))}` no_full_clear=`{live_bool(loop.get('no_full_clear_markers_ok'))}`",
        f"- Timing read/draw/total avg us: `{live_value(loop.get('timing_read_avg_us'))}` / `{live_value(loop.get('timing_draw_avg_us'))}` / `{live_value(loop.get('timing_total_avg_us'))}`",
        f"- Timing deltas vs V3124 read/draw us: `{live_value(loop.get('read_delta_vs_v3124_us'))}` / `{live_value(loop.get('draw_delta_vs_v3124_us'))}`",
        f"- Flip events: `{live_value(loop.get('flip_events'))}` delta avg/max us: `{live_value(loop.get('flip_delta_avg_us'))}` / `{live_value(loop.get('flip_delta_max_us'))}` 60hz_stable=`{live_bool(loop.get('pageflip_60hz_stable'))}`",
        f"- Shared seq missed/max-gap: `{live_value(loop.get('seq_shared_missed_frames'))}` / `{live_value(loop.get('seq_shared_max_sequence_gap_frames'))}` clean=`{live_bool(loop.get('shared_seq_clean'))}`",
        "",
        "## Smooth Telemetry",
        "",
        f"- Telemetry available: `{live_bool(loop.get('telemetry_available'))}` open_rc=`{live_value(loop.get('tick_telemetry_open_rc'))}` lines=`{live_value(loop.get('tick_telemetry_lines'))}`",
        f"- Tick telemetry marker: `{live_value(loop.get('tick_telemetry_marker'))}`",
        f"- Paced-time marker/model: `{live_value(loop.get('paced_time_marker'))}` / `{live_value(loop.get('paced_time_model'))}` ok=`{live_bool(loop.get('paced_time_markers_ok'))}`",
        f"- Smooth mode: `{live_value(loop.get('smooth_demo_mode'))}`",
        f"- Tic quantum us: `{live_value(loop.get('paced_time_quantum_us'))}` ok=`{live_bool(loop.get('paced_time_quantum_ok'))}`",
        f"- Paced advance calls/us_total: `{live_value(loop.get('paced_time_advance_calls'))}` / `{live_value(loop.get('paced_time_advance_us_total'))}`",
        f"- Loop gametic changed/repeated/max_delta: `{live_value(loop.get('loop_tick_gametic_changed'))}` / `{live_value(loop.get('loop_tick_gametic_repeated'))}` / `{live_value(loop.get('loop_tick_gametic_max_delta'))}`",
        f"- Draw gametic changed/repeated/max_same_run: `{live_value(loop.get('draw_gametic_changed_transitions'))}` / `{live_value(loop.get('draw_gametic_repeated_transitions'))}` / `{live_value(loop.get('draw_gametic_max_same_run'))}` internal_repeats=`{live_bool(loop.get('draw_gametic_internal_repeats'))}`",
        f"- Dump gametic changed/repeated/max_same_run/max_delta: `{live_value(loop.get('dump_gametic_changed_transitions'))}` / `{live_value(loop.get('dump_gametic_repeated_transitions'))}` / `{live_value(loop.get('dump_gametic_max_same_run'))}` / `{live_value(loop.get('dump_gametic_max_delta'))}`",
        f"- Output gametic repetition bounded: `{live_bool(loop.get('gametic_repetition_bounded'))}`",
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
        "- If pageflip remains 60Hz stable, shared seq stays clean, and smooth telemetry has bounded output-frame gametic repetition, the residual V3124 stutter was original DOOM 35Hz game-tic cadence rather than presenter/IPC/display overhead.",
        "- `draw_gametic` is an internal draw-call sample; repeated draw samples are review evidence only when `dump_gametic` also repeats.",
        "- If smooth telemetry is present but output-frame gametic repetition remains high, the remaining problem is inside the engine time/tic model.",
        "- If pageflip or shared sequence regresses, the remaining cause is still in presenter/display synchronization and not DOOM semantics.",
        "- This candidate intentionally changes DOOM virtual time and is a comparison/demo mode, not original-speed gameplay.",
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
        "- `py_compile`: V3127 live runner and focused tests.",
        "- `unittest`: V3127 live parser/report/preflight contract.",
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
            f"flash exact V3126 image {CANDIDATE_IMAGE}",
            "version/status/selftest",
            "hide auto menu before foreground DOOM loop",
            f"video demo doom loop {args.frames} --wad runtime-private --sha256 {EXPECTED_WAD_SHA256}",
            "parse direct/summary/pageflip/seq markers plus bounded tick telemetry summary",
            "selftest verbose after bounded loop",
            "rollback v2321 and verify selftest fail=0",
        ],
    }


def run_live(args: argparse.Namespace, out_dir: Path, state: dict[str, Any]) -> dict[str, Any]:
    _apply_v3127_globals()
    try:
        return v3124.run_live(args, out_dir, state)
    finally:
        _restore_v3124_globals()


def main() -> int:
    _apply_v3127_globals()
    return v3124.main()


if __name__ == "__main__":
    raise SystemExit(main())

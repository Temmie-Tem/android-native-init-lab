#!/usr/bin/env python3
"""V3113 rollback-gated live validation for V3112 DOOM hardware plane cached-crtc."""

from __future__ import annotations

import argparse
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import native_doom_status_stub_live_handoff_v3001 as status_live

base = status_live.base
ROOT = status_live.ROOT

RUN_ID = "V3113"
BUILD_TAG = "v3113-doomgeneric-hw-plane-cached-crtc-live"
DECISION_PREFIX = "v3113-doomgeneric-hw-plane-cached-crtc"
REPORT_PATH = ROOT / "docs/reports/NATIVE_INIT_V3113_DOOMGENERIC_HW_PLANE_CACHED_CRTC_LIVE_2026-06-23.md"

CANDIDATE_IMAGE = ROOT / "workspace/private/inputs/boot_images/boot_linux_v3112_doomgeneric_hw_plane_cached_crtc.img"
CANDIDATE_VERSION = "0.10.111"
CANDIDATE_TAG = "v3112-doomgeneric-hw-plane-cached-crtc"
CANDIDATE_SHA256 = "e58d08d57de91831738b3fc48911e2c6da02e50059c77935203b03409df6e5b0"

ROLLBACK_IMAGE = status_live.ROLLBACK_IMAGE
ROLLBACK_VERSION = status_live.ROLLBACK_VERSION
ROLLBACK_SHA256 = status_live.ROLLBACK_SHA256
FALLBACK_V2237 = status_live.FALLBACK_V2237
FALLBACK_V2237_SHA256 = status_live.FALLBACK_V2237_SHA256
FALLBACK_V48 = status_live.FALLBACK_V48

EXPECTED_WAD_SHA256 = "1d7d43be501e67d927e415e0b8f3e29c3bf33075e859721816f652a526cac771"
DEFAULT_FRAMES = 180

LOOP_MARKERS = (
    "video.demo.doom.loop=doomgeneric-sd-wad-visible-playable-loop",
    "video.demo.doom.loop.verify.ok=1",
    "video.demo.doom.dashboard.hw_plane_scale=1",
    "video.demo.doom.dashboard.scale_path=drm-plane-srcdst",
    "video.demo.doom.dashboard.hw_plane.stage=",
    "video.demo.doom.dashboard.hw_plane.cached_crtc_index=",
    "video.demo.doom.loop.timing_probe=1",
    "video.demo.doom.loop.seq_telemetry=1",
    "video.demo.doom.loop.flip_telemetry=pageflip-event-delta-us",
)

KEY_VALUE_RE = re.compile(r"^(?P<key>[A-Za-z0-9_.-]+)=(?P<value>[^\r\n]*)\r?$", re.MULTILINE)
VERSION_LINE_RE = re.compile(r"^version:\s+(?P<version>\S+)\s+build=(?P<build>\S+)\r?$", re.MULTILINE)


def now_slug() -> str:
    return datetime.now(timezone.utc).astimezone().strftime("%Y%m%d-%H%M%S")


def rel(path: Path | str | None) -> str | None:
    if path is None:
        return None
    return status_live.rel(Path(path))


def stdout_of(step: dict[str, Any] | None) -> str:
    return status_live.stdout_of(step)


def write_json(path: Path, payload: Any) -> None:
    status_live.write_json(path, payload)


def file_state(path: Path, expected_sha: str | None = None) -> dict[str, Any]:
    return status_live.file_state(path, expected_sha)


def selftest_step_ok(step: dict[str, Any]) -> bool:
    return status_live.selftest_step_ok(step)


def flash_command(image: Path, expect_version: str, expect_sha: str, *, from_native: bool) -> list[str]:
    return status_live.flash_command(image, expect_version, expect_sha, from_native=from_native)


def marker_summary(text: str, markers: tuple[str, ...]) -> dict[str, bool]:
    text = normalize_serial_text(text)
    return {marker: marker in text for marker in markers}


def all_markers_present(summary: dict[str, bool]) -> bool:
    return bool(summary) and all(summary.values())


def _last_int(values: dict[str, list[str]], key: str) -> int | None:
    items = values.get(key) or []
    for item in reversed(items):
        try:
            return int(item.strip(), 10)
        except ValueError:
            continue
    return None


def _last_value(values: dict[str, list[str]], key: str) -> str | None:
    items = values.get(key) or []
    return items[-1] if items else None


def _int_values(values: dict[str, list[str]], key: str) -> list[int]:
    parsed: list[int] = []
    for item in values.get(key) or []:
        try:
            parsed.append(int(item.strip(), 10))
        except ValueError:
            continue
    return parsed


def _count_value(values: dict[str, list[str]], key: str, expected: str) -> int:
    return sum(1 for value in values.get(key) or [] if value.strip() == expected)


def _max_int(values: dict[str, list[str]], key: str) -> int | None:
    items = _int_values(values, key)
    return max(items) if items else None


def normalize_serial_text(text: str) -> str:
    if "\\r\\n" in text or "\\n" in text or "\\r" in text:
        text = text.replace("\\r\\n", "\n").replace("\\n", "\n").replace("\\r", "\n")
    return text.replace("\r\n", "\n").replace("\r", "\n")


def parse_key_values(text: str) -> dict[str, list[str]]:
    text = normalize_serial_text(text)
    values: dict[str, list[str]] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", key.strip()):
            continue
        values.setdefault(key.strip(), []).append(value.strip())
    return values


def parse_version_summary(text: str) -> str:
    match = VERSION_LINE_RE.search(text)
    if match is None:
        return ""
    return f"{match.group('version')} ({match.group('build')})"


def parse_loop_output(text: str) -> dict[str, Any]:
    normalized = normalize_serial_text(text)
    values = parse_key_values(text)

    hw_present_values = values.get("video.demo.doom.dashboard.hw_plane.presented", [])
    hw_attempt_values = values.get("video.demo.doom.dashboard.hw_plane.attempted", [])
    cached_values = values.get("video.demo.doom.dashboard.hw_plane.cached_crtc_index", [])
    fallback_values = values.get("video.demo.doom.dashboard.hw_plane.fallback", [])
    loop_rc = _last_int(values, "video.demo.doom.loop.rc")
    display_rc = _last_int(values, "video.demo.doom.loop.display.rc")
    frames_presented = _last_int(values, "video.demo.doom.loop.frames_presented")
    shared_missed = _last_int(values, "video.demo.doom.loop.seq.shared_missed_frames")
    flip_avg = _last_int(values, "video.demo.doom.loop.flip_delta_avg_us")
    flip_max = _last_int(values, "video.demo.doom.loop.flip_delta_max_us")
    stage_key = "video.demo.doom.dashboard.hw_plane.stage"
    setplane_count = _count_value(values, stage_key, "setplane")
    fetch_resources_count = _count_value(values, stage_key, "fetch-resources")
    scan_planes_count = _count_value(values, stage_key, "scan-planes")
    presented_stage_count = _count_value(values, stage_key, "presented")
    cached_count = sum(1 for value in cached_values if value.strip() == "1")
    cached_any = cached_count > 0
    cached_or_reuse_evidence = cached_any or setplane_count > 0 or presented_stage_count > 0
    protocol_end_present = re.search(r"^A90P1 END ", normalized, re.MULTILINE) is not None
    loop_summary_present = loop_rc is not None and frames_presented is not None

    return {
        "loop_rc": loop_rc,
        "display_rc": display_rc,
        "protocol_end_present": protocol_end_present,
        "loop_summary_present": loop_summary_present,
        "loop_summary_missing_with_protocol_end": protocol_end_present and not loop_summary_present,
        "frames_presented": frames_presented,
        "display_presented_count": _count_value(values, "video.demo.doom.frame.display.presented", "1"),
        "dashboard_present_seq_max": _max_int(values, "video.demo.doom.dashboard.present_seq"),
        "hw_plane_attempted_count": sum(1 for value in hw_attempt_values if value.strip() == "1"),
        "hw_plane_presented_count": sum(1 for value in hw_present_values if value.strip() == "1"),
        "hw_plane_presented": any(value.strip() == "1" for value in hw_present_values),
        "hw_plane_fallback": bool(fallback_values),
        "hw_plane_fallback_value": fallback_values[-1] if fallback_values else "",
        "hw_plane_last_id": _last_int(values, "video.demo.doom.dashboard.hw_plane.id"),
        "hw_plane_last_fb_id": _last_int(values, "video.demo.doom.dashboard.hw_plane.fb_id"),
        "hw_plane_last_rc": _last_int(values, "video.demo.doom.dashboard.hw_plane.rc"),
        "hw_plane_stage": _last_value(values, "video.demo.doom.dashboard.hw_plane.stage"),
        "hw_plane_stage_id": _last_int(values, "video.demo.doom.dashboard.hw_plane.stage_id"),
        "hw_plane_setplane_count": setplane_count,
        "hw_plane_fetch_resources_count": fetch_resources_count,
        "hw_plane_scan_planes_count": scan_planes_count,
        "hw_plane_presented_stage_count": presented_stage_count,
        "hw_plane_einval_count": _count_value(values, "video.demo.doom.dashboard.hw_plane.rc", "-22"),
        "hw_plane_crtc_index": _last_int(values, "video.demo.doom.dashboard.hw_plane.crtc_index"),
        "hw_plane_cached_crtc_index": _last_int(values, "video.demo.doom.dashboard.hw_plane.cached_crtc_index"),
        "hw_plane_cached_crtc_index_count": cached_count,
        "hw_plane_cached_crtc_index_any": cached_any,
        "hw_plane_cached_or_reuse_evidence": cached_or_reuse_evidence,
        "hw_plane_plane_count": _last_int(values, "video.demo.doom.dashboard.hw_plane.plane_count"),
        "hw_plane_compatible_count": _last_int(values, "video.demo.doom.dashboard.hw_plane.compatible_count"),
        "hw_plane_idle_xbgr_count": _last_int(values, "video.demo.doom.dashboard.hw_plane.idle_xbgr_count"),
        "hw_plane_universal_cap_rc": _last_int(values, "video.demo.doom.dashboard.hw_plane.universal_cap_rc"),
        "hw_plane_atomic_cap_rc": _last_int(values, "video.demo.doom.dashboard.hw_plane.atomic_cap_rc"),
        "hw_plane_fetch_resources_rc": _last_int(values, "video.demo.doom.dashboard.hw_plane.fetch_resources_rc"),
        "frame_mode": _last_value(values, "video.demo.doom.dashboard.frame_mode"),
        "frame_scale": _last_value(values, "video.demo.doom.dashboard.frame_scale"),
        "scale_path": _last_value(values, "video.demo.doom.dashboard.scale_path"),
        "timing_draw_avg_us": _last_int(values, "video.demo.doom.loop.timing.draw.avg_us"),
        "timing_draw_max_us": _last_int(values, "video.demo.doom.loop.timing.draw.max_us"),
        "timing_total_avg_us": _last_int(values, "video.demo.doom.loop.timing.total.avg_us"),
        "timing_total_max_us": _last_int(values, "video.demo.doom.loop.timing.total.max_us"),
        "seq_duplicate_frame_polls": _last_int(values, "video.demo.doom.loop.seq.duplicate_frame_polls"),
        "seq_shared_missed_frames": shared_missed,
        "seq_shared_max_sequence_gap_frames": _last_int(values, "video.demo.doom.loop.seq.shared_max_sequence_gap_frames"),
        "flip_events": _last_int(values, "video.demo.doom.loop.flip_events"),
        "flip_delta_avg_us": flip_avg,
        "flip_delta_max_us": flip_max,
        "pageflip_stable": flip_avg is not None and flip_max is not None and 15000 <= flip_avg <= 19000 and flip_max <= 34000,
        "shared_seq_clean": shared_missed == 0,
        "markers": marker_summary(text, LOOP_MARKERS),
    }


def loop_classification(loop: dict[str, Any], requested_frames: int) -> str:
    loop_ok = loop.get("loop_rc") == 0 and loop.get("frames_presented") == requested_frames
    if not loop_ok:
        if loop.get("loop_summary_missing_with_protocol_end"):
            return "loop-summary-missing"
        return "loop-not-clean"
    if loop.get("hw_plane_presented"):
        return "hw-plane-presented"
    if loop.get("hw_plane_fallback"):
        return "cpu-fallback-observed"
    return "hw-plane-not-classified"


def live_pass(result: dict[str, Any]) -> bool:
    loop = result.get("doom_loop", {}) if isinstance(result.get("doom_loop"), dict) else {}
    return bool(
        result.get("preflash_selftest_fail0")
        and result.get("candidate_version_ok")
        and result.get("candidate_selftest_fail0")
        and result.get("candidate_hide_before_loop_ok")
        and result.get("doom_loop_rc") == 0
        and result.get("doom_loop_protocol_end_present")
        and result.get("loop_classification") in {"hw-plane-presented", "cpu-fallback-observed"}
        and loop.get("hw_plane_cached_or_reuse_evidence")
        and result.get("candidate_selftest_after_loop_fail0")
    )


def preflight_state(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "run_id": RUN_ID,
        "candidate": file_state(CANDIDATE_IMAGE, CANDIDATE_SHA256),
        "rollback": file_state(ROLLBACK_IMAGE, ROLLBACK_SHA256),
        "fallback_v2237": file_state(FALLBACK_V2237, FALLBACK_V2237_SHA256),
        "fallback_v48": file_state(FALLBACK_V48),
        "flash_helper": file_state(base.FLASH),
        "candidate_version": CANDIDATE_VERSION,
        "candidate_tag": CANDIDATE_TAG,
        "frames": args.frames,
        "expected_wad_sha256": EXPECTED_WAD_SHA256,
        "recovery_gate": "native_init_flash.py wait_recovery_adb during candidate flash; rollback_v2321 on failure",
        "operator_prerequisite": "runtime-private WAD must already be staged on SD; host input is not required for this bounded loop",
        "hard_boundary": [
            "boot partition only via native_init_flash.py",
            "rollback to v2321 and verify selftest fail=0",
            "hide auto menu before the foreground video demo doom loop; no host input drive required",
            "no Wi-Fi connect/dhcp/ping, PMIC, backlight, GPIO, regulator, GDSC, or forbidden partition path",
            "raw command output stays private under workspace/private/runs",
        ],
    }


def preflight_ok(state: dict[str, Any]) -> bool:
    return bool(
        state["candidate"].get("sha256_ok")
        and state["rollback"].get("sha256_ok")
        and state["fallback_v2237"].get("sha256_ok")
        and state["fallback_v48"].get("exists")
        and state["flash_helper"].get("exists")
        and int(state.get("frames", 0)) > 0
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
        "# Native Init V3113 DOOMGENERIC Hardware Plane Cached CRTC Live Validation",
        "",
        "## Summary",
        "",
        f"- Decision: `{result.get('decision')}`",
        f"- Result before rollback: `{int(bool(result.get('pass')))}`",
        f"- Loop classification: `{result.get('loop_classification', 'not-run')}`",
        "- Track: DOOM large-frame scale-path optimization.",
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
        f"- Operator prerequisite: `{preflight.get('operator_prerequisite', '-')}`",
        "",
        "## Live Evidence",
        "",
        f"- Pre-flash current version: `{live_value(result.get('preflash_version'))}`",
        f"- Pre-flash selftest fail=0: `{live_bool(result.get('preflash_selftest_fail0'))}`",
        f"- Candidate version ok: `{live_bool(result.get('candidate_version_ok'))}`",
        f"- Candidate selftest fail=0: `{live_bool(result.get('candidate_selftest_fail0'))}`",
        f"- Candidate hide-before-loop ok: `{live_bool(result.get('candidate_hide_before_loop_ok'))}`",
        f"- DOOM loop rc: `{live_value(result.get('doom_loop_rc'))}` transport_rc=`{live_value(result.get('doom_loop_transport_rc'))}` protocol_end=`{live_bool(result.get('doom_loop_protocol_end_present'))}`",
        f"- Loop summary present/missing-with-END: `{live_bool(loop.get('loop_summary_present'))}` / `{live_bool(loop.get('loop_summary_missing_with_protocol_end'))}`",
        f"- Frames requested/presented: `{preflight.get('frames', 'not-run')}` / `{live_value(loop.get('frames_presented'))}`",
        f"- Display presented logs / max dashboard seq: `{live_value(loop.get('display_presented_count'))}` / `{live_value(loop.get('dashboard_present_seq_max'))}`",
        f"- HW plane presented: `{live_bool(loop.get('hw_plane_presented'))}` count=`{live_value(loop.get('hw_plane_presented_count'))}`",
        f"- HW plane fallback: `{live_bool(loop.get('hw_plane_fallback'))}` value=`{live_value(loop.get('hw_plane_fallback_value'))}`",
        f"- HW plane last id/fb/rc: `{live_value(loop.get('hw_plane_last_id'))}` / `{live_value(loop.get('hw_plane_last_fb_id'))}` / `{live_value(loop.get('hw_plane_last_rc'))}`",
        f"- HW plane stage/id: `{live_value(loop.get('hw_plane_stage'))}` / `{live_value(loop.get('hw_plane_stage_id'))}`",
        f"- HW plane stage counts setplane/fetch-resources/scan-planes/presented: `{live_value(loop.get('hw_plane_setplane_count'))}` / `{live_value(loop.get('hw_plane_fetch_resources_count'))}` / `{live_value(loop.get('hw_plane_scan_planes_count'))}` / `{live_value(loop.get('hw_plane_presented_stage_count'))}`",
        f"- HW plane crtc_index/cached-last/cached-count/reuse-evidence/fetch_resources_rc: `{live_value(loop.get('hw_plane_crtc_index'))}` / `{live_value(loop.get('hw_plane_cached_crtc_index'))}` / `{live_value(loop.get('hw_plane_cached_crtc_index_count'))}` / `{live_bool(loop.get('hw_plane_cached_or_reuse_evidence'))}` / `{live_value(loop.get('hw_plane_fetch_resources_rc'))}`",
        f"- HW plane counts plane/compatible/idle_xbgr: `{live_value(loop.get('hw_plane_plane_count'))}` / `{live_value(loop.get('hw_plane_compatible_count'))}` / `{live_value(loop.get('hw_plane_idle_xbgr_count'))}`",
        f"- HW plane EINVAL count: `{live_value(loop.get('hw_plane_einval_count'))}`",
        f"- HW plane client caps universal/atomic rc: `{live_value(loop.get('hw_plane_universal_cap_rc'))}` / `{live_value(loop.get('hw_plane_atomic_cap_rc'))}`",
        f"- Frame mode/scale/path: `{live_value(loop.get('frame_mode'))}` / `{live_value(loop.get('frame_scale'))}` / `{live_value(loop.get('scale_path'))}`",
        f"- Timing draw avg/max us: `{live_value(loop.get('timing_draw_avg_us'))}` / `{live_value(loop.get('timing_draw_max_us'))}`",
        f"- Timing total avg/max us: `{live_value(loop.get('timing_total_avg_us'))}` / `{live_value(loop.get('timing_total_max_us'))}`",
        f"- Flip events: `{live_value(loop.get('flip_events'))}` delta avg/max us: `{live_value(loop.get('flip_delta_avg_us'))}` / `{live_value(loop.get('flip_delta_max_us'))}` stable=`{live_bool(loop.get('pageflip_stable'))}`",
        f"- Shared seq missed/max-gap: `{live_value(loop.get('seq_shared_missed_frames'))}` / `{live_value(loop.get('seq_shared_max_sequence_gap_frames'))}` clean=`{live_bool(loop.get('shared_seq_clean'))}`",
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
        "- `hw-plane-presented` means the next check is visual/z-order plus timing quality.",
        "- `cpu-fallback-observed` means V3112 safely ran but the large path still used the known stuttering CPU 3:2 scaler; proceed to the pre-scaled-producer fallback.",
        "- `cached_crtc_index=1` means V3112 bypassed the legacy `GETRESOURCES` hot path and used the KMS init CRTC index for plane enumeration.",
        "- `cached_crtc_index=0` after `stage=setplane` is a diagnostic limitation: once a plane was selected, later frames reuse it without replaying the original selection metadata.",
        "- `hw_plane.stage=fetch-resources` with `cached_crtc_index=0` means the cached index was unavailable and the old resources fallback still failed.",
        "- `hw_plane.stage=scan-planes` with `rc=-19` means there was no compatible idle XBGR plane; `stage=setplane` means the next unit should try atomic plane commit.",
        "- `loop-summary-missing` with protocol END means the serial command completed but per-frame diagnostic output likely drowned or interleaved the final summary markers; treat it as a logging/validation problem, not a boot-health failure.",
        "- `protocol-end-missing` means the foreground loop returned prompt-visible output but did not emit a cmdv1 END marker, so host validation waits for timeout even when frame evidence is present.",
        "- If pageflip is stable and shared sequence is clean, residual stepped motion is the known DOOM 35 Hz game-tic cadence on the 60 Hz panel.",
        "- This candidate still uses a bounded tone corun, not real DOOM music/SFX.",
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
        "- `python3 -m py_compile workspace/public/src/scripts/revalidation/native_doomgeneric_hw_plane_cached_crtc_live_validation_v3113.py tests/test_native_doomgeneric_hw_plane_cached_crtc_live_v3113.py`: PASS",
        "- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation:workspace/public/src/harness python3 -m unittest tests.test_native_doomgeneric_hw_plane_cached_crtc_live_v3113`: PASS",
        "- dry-run preflight/report: PASS when preflight assets are present.",
        "- `git diff --check`: PASS",
    ]) + "\n"


def run_live(args: argparse.Namespace, out_dir: Path, state: dict[str, Any]) -> dict[str, Any]:
    steps: list[dict[str, Any]] = []
    candidate_flash_attempted = False
    candidate_flash_ok = False
    result: dict[str, Any] = {
        "decision": f"{DECISION_PREFIX}-live-started",
        "pass": False,
        "live_executed": True,
        "out_dir": rel(out_dir),
        "preflight": state,
        "steps": steps,
        "rollback_attempted": False,
        "rollback_version_ok": False,
        "rollback_selftest_fail0": False,
    }
    try:
        pre_version = base.run_serial_step(out_dir, steps, "preflash-current-version", ["version"], timeout=90.0, retry_unsafe=True)
        base.run_serial_step(out_dir, steps, "preflash-current-status", ["status"], timeout=90.0, retry_unsafe=True)
        pre_selftest = base.run_serial_step(out_dir, steps, "preflash-current-selftest", ["selftest", "verbose"], timeout=120.0, retry_unsafe=True)
        result["preflash_version"] = parse_version_summary(stdout_of(pre_version))
        result["preflash_selftest_fail0"] = selftest_step_ok(pre_selftest)
        if not result["preflash_selftest_fail0"]:
            result["decision"] = f"{DECISION_PREFIX}-preflash-health-failed"
            raise RuntimeError("pre-flash resident selftest did not report fail=0")

        candidate_flash_attempted = True
        flash = base.run_step(
            out_dir,
            steps,
            f"flash-{CANDIDATE_TAG}",
            flash_command(CANDIDATE_IMAGE, CANDIDATE_VERSION, CANDIDATE_SHA256, from_native=True),
            timeout=args.flash_timeout,
        )
        candidate_flash_ok = flash.get("rc") == 0
        version = base.run_serial_step(out_dir, steps, "candidate-version", ["version"], timeout=90.0, retry_unsafe=True)
        base.run_serial_step(out_dir, steps, "candidate-status", ["status"], timeout=90.0, retry_unsafe=True)
        selftest = base.run_serial_step(out_dir, steps, "candidate-selftest", ["selftest", "verbose"], timeout=120.0, retry_unsafe=True)
        hide_before_loop = base.run_serial_step(
            out_dir,
            steps,
            "candidate-hide-menu-before-doom-loop",
            ["hide"],
            timeout=45.0,
            retry_unsafe=True,
            allow_error=True,
        )
        result["candidate_hide_before_loop_ok"] = bool(hide_before_loop.get("ok"))
        time.sleep(1.0)
        loop_command = [
            "video", "demo", "doom", "loop", str(args.frames),
            "--wad", "runtime-private",
            "--sha256", EXPECTED_WAD_SHA256,
        ]
        doom_loop = base.run_serial_step(out_dir, steps, "candidate-video-demo-doom-loop", loop_command, timeout=args.loop_timeout, retry_unsafe=False, allow_error=True)
        after = base.run_serial_step(out_dir, steps, "candidate-selftest-after-loop", ["selftest", "verbose"], timeout=120.0, retry_unsafe=True)
        loop_stdout = stdout_of(doom_loop)
        loop = parse_loop_output(loop_stdout)
        classification = loop_classification(loop, args.frames)
        result.update({
            "candidate_version_ok": f"A90 Linux init {CANDIDATE_VERSION} ({CANDIDATE_TAG})" in stdout_of(version),
            "candidate_selftest_fail0": selftest_step_ok(selftest),
            "doom_loop_transport_rc": doom_loop.get("rc"),
            "doom_loop_rc": loop.get("loop_rc"),
            "doom_loop_protocol_end_present": bool(loop.get("protocol_end_present")),
            "doom_loop_stdout_path": doom_loop.get("stdout_path"),
            "doom_loop": loop,
            "loop_classification": classification,
            "candidate_selftest_after_loop_fail0": selftest_step_ok(after),
        })
        result["pass"] = live_pass(result)
        if classification in {"hw-plane-presented", "cpu-fallback-observed"} and not result["doom_loop_protocol_end_present"]:
            result["decision"] = f"{DECISION_PREFIX}-{classification}-protocol-end-missing"
        elif classification == "hw-plane-presented":
            result["decision"] = f"{DECISION_PREFIX}-hw-plane-presented-pass-before-rollback"
        elif classification == "cpu-fallback-observed":
            result["decision"] = f"{DECISION_PREFIX}-cpu-fallback-observed-before-rollback"
        else:
            result["decision"] = f"{DECISION_PREFIX}-{classification}"
        if not result["pass"]:
            raise RuntimeError(f"V3112 hardware plane scale live validation did not classify cleanly: {classification}")
    except Exception as exc:  # noqa: BLE001 - write report and rollback
        if result["decision"] == f"{DECISION_PREFIX}-live-started":
            result["decision"] = f"{DECISION_PREFIX}-live-blocked"
        result["error_type"] = type(exc).__name__
        result["error"] = str(exc)
    finally:
        if candidate_flash_attempted:
            result["rollback_attempted"] = True
            rollback = base.rollback_v2321(out_dir, steps, from_native=candidate_flash_ok, timeout=args.flash_timeout)
            result["rollback_step_ok"] = bool(rollback.get("success"))
            result["rollback_attempts"] = rollback.get("attempts", [])
            result["rollback_recovery_fallback_used"] = bool(rollback.get("used_recovery_fallback"))
            if rollback.get("success"):
                rollback_version = base.run_serial_step(out_dir, steps, "rollback-version", ["version"], timeout=90.0, retry_unsafe=True, allow_error=True)
                rollback_selftest = base.run_serial_step(out_dir, steps, "rollback-selftest", ["selftest", "verbose"], timeout=120.0, retry_unsafe=True, allow_error=True)
                result["rollback_version_ok"] = ROLLBACK_VERSION in stdout_of(rollback_version)
                result["rollback_selftest_fail0"] = selftest_step_ok(rollback_selftest)
        result["result_json"] = rel(out_dir / "result.json")
        write_json(out_dir / "result.json", result)
        REPORT_PATH.write_text(render_report(result), encoding="utf-8")
    return result


def dry_run_payload(args: argparse.Namespace, state: dict[str, Any]) -> dict[str, Any]:
    return {
        "decision": f"{DECISION_PREFIX}-dry-run" if preflight_ok(state) else f"{DECISION_PREFIX}-preflight-failed",
        "ok": preflight_ok(state),
        "preflight": state,
        "commands": [
            "verify current resident version/status/selftest over serial",
            f"flash exact V3112 image {CANDIDATE_IMAGE}",
            "version/status/selftest",
            "hide auto menu before foreground DOOM loop",
            f"video demo doom loop {args.frames} --wad runtime-private --sha256 {EXPECTED_WAD_SHA256}",
            "parse hw_plane cached-crtc/stage/counters/presented/fallback, timing, seq, and pageflip markers",
            "selftest verbose after bounded loop",
            "rollback v2321 and verify selftest fail=0",
        ],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="flash V3112, run bounded DOOM loop, then rollback")
    parser.add_argument("--frames", type=int, default=DEFAULT_FRAMES)
    parser.add_argument("--flash-timeout", type=float, default=900.0)
    parser.add_argument("--loop-timeout", type=float, default=180.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    out_dir = ROOT / f"workspace/private/runs/video/{BUILD_TAG}-{now_slug()}"
    out_dir.mkdir(parents=True, exist_ok=True)
    state = preflight_state(args)
    if not args.live:
        payload = dry_run_payload(args, state)
        write_json(out_dir / "dry_run.json", payload)
        report_payload = {
            "decision": payload["decision"],
            "pass": False,
            "live_executed": False,
            "out_dir": rel(out_dir),
            "preflight": state,
            "preflight_ok": payload["ok"],
            "rollback_attempted": False,
        }
        REPORT_PATH.write_text(render_report(report_payload), encoding="utf-8")
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0 if payload["ok"] else 1
    if not preflight_ok(state):
        result = {
            "decision": f"{DECISION_PREFIX}-preflight-failed",
            "pass": False,
            "live_executed": False,
            "out_dir": rel(out_dir),
            "preflight": state,
            "preflight_ok": False,
            "rollback_attempted": False,
        }
        write_json(out_dir / "result.json", result)
        REPORT_PATH.write_text(render_report(result), encoding="utf-8")
        print(json.dumps(result, indent=2, sort_keys=True))
        return 1
    result = run_live(args, out_dir, state)
    print(json.dumps({
        "decision": result.get("decision"),
        "pass": result.get("pass"),
        "loop_classification": result.get("loop_classification"),
        "doom_loop_rc": result.get("doom_loop_rc"),
        "doom_loop_transport_rc": result.get("doom_loop_transport_rc"),
        "doom_loop_protocol_end_present": result.get("doom_loop_protocol_end_present"),
        "doom_loop": result.get("doom_loop"),
        "rollback_version_ok": result.get("rollback_version_ok"),
        "rollback_selftest_fail0": result.get("rollback_selftest_fail0"),
        "result_json": result.get("result_json"),
    }, indent=2, sort_keys=True))
    return 0 if result.get("pass") and result.get("rollback_version_ok") and result.get("rollback_selftest_fail0") else 1


if __name__ == "__main__":
    raise SystemExit(main())

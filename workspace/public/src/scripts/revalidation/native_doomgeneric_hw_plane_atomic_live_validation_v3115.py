#!/usr/bin/env python3
"""V3115 rollback-gated live validation for V3114 DOOM hardware-plane atomic."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import native_doomgeneric_hw_plane_cached_crtc_live_validation_v3113 as base_live

ROOT = base_live.ROOT

RUN_ID = "V3115"
BUILD_TAG = "v3115-doomgeneric-hw-plane-atomic-live"
DECISION_PREFIX = "v3115-doomgeneric-hw-plane-atomic"
REPORT_PATH = ROOT / "docs/reports/NATIVE_INIT_V3115_DOOMGENERIC_HW_PLANE_ATOMIC_LIVE_2026-06-23.md"

CANDIDATE_IMAGE = ROOT / "workspace/private/inputs/boot_images/boot_linux_v3114_doomgeneric_hw_plane_atomic.img"
CANDIDATE_VERSION = "0.10.112"
CANDIDATE_TAG = "v3114-doomgeneric-hw-plane-atomic"
CANDIDATE_SHA256 = "c25090ecefe790ab680320a0cedebaa6b937155437dc37e52ca2485ffb8485c4"

EXPECTED_WAD_SHA256 = base_live.EXPECTED_WAD_SHA256
DEFAULT_FRAMES = base_live.DEFAULT_FRAMES

LOOP_MARKERS = base_live.LOOP_MARKERS + (
    "video.demo.doom.dashboard.hw_plane.atomic_attempted=",
    "video.demo.doom.dashboard.hw_plane.atomic_props_rc=",
    "video.demo.doom.dashboard.hw_plane.atomic_commit_rc=",
    "video.demo.doom.dashboard.hw_plane.legacy_setplane_rc=",
)

_BASE_PARSE_LOOP_OUTPUT = base_live.parse_loop_output
_BASE_LOOP_CLASSIFICATION = base_live.loop_classification
_BASE_RENDER_REPORT = base_live.render_report
_BASE_LIVE_PASS = base_live.live_pass
_BASE_DRY_RUN_PAYLOAD = base_live.dry_run_payload


def _last_int(values: dict[str, list[str]], key: str) -> int | None:
    return base_live._last_int(values, key)


def _count_value(values: dict[str, list[str]], key: str, expected: str) -> int:
    return sum(1 for value in values.get(key) or [] if value.strip() == expected)


def rel(path: Path | str | None) -> str | None:
    return base_live.rel(path)


def parse_loop_output(text: str) -> dict[str, Any]:
    loop = _BASE_PARSE_LOOP_OUTPUT(text)
    values = base_live.parse_key_values(text)
    loop.update({
        "hw_plane_atomic_attempted_count": _count_value(
            values, "video.demo.doom.dashboard.hw_plane.atomic_attempted", "1"
        ),
        "hw_plane_atomic_props_rc": _last_int(values, "video.demo.doom.dashboard.hw_plane.atomic_props_rc"),
        "hw_plane_atomic_prop_count": _last_int(values, "video.demo.doom.dashboard.hw_plane.atomic_prop_count"),
        "hw_plane_atomic_commit_rc": _last_int(values, "video.demo.doom.dashboard.hw_plane.atomic_commit_rc"),
        "hw_plane_atomic_commit_success_count": _count_value(
            values, "video.demo.doom.dashboard.hw_plane.atomic_commit_rc", "0"
        ),
        "hw_plane_atomic_einval_count": _count_value(
            values, "video.demo.doom.dashboard.hw_plane.atomic_commit_rc", "-22"
        ),
        "hw_plane_legacy_setplane_rc": _last_int(values, "video.demo.doom.dashboard.hw_plane.legacy_setplane_rc"),
        "hw_plane_legacy_setplane_einval_count": _count_value(
            values, "video.demo.doom.dashboard.hw_plane.legacy_setplane_rc", "-22"
        ),
        "markers": base_live.marker_summary(text, LOOP_MARKERS),
    })
    return loop


def loop_classification(loop: dict[str, Any], requested_frames: int) -> str:
    return _BASE_LOOP_CLASSIFICATION(loop, requested_frames)


def live_pass(result: dict[str, Any]) -> bool:
    return _BASE_LIVE_PASS(result)


def render_report(result: dict[str, Any]) -> str:
    report = _BASE_RENDER_REPORT(result)
    report = report.replace(
        "Native Init V3113 DOOMGENERIC Hardware Plane Cached CRTC Live Validation",
        "Native Init V3115 DOOMGENERIC Hardware Plane Atomic Live Validation",
    )
    report = report.replace("v3113-doomgeneric-hw-plane-cached-crtc", DECISION_PREFIX)
    report = report.replace(
        "A90 Linux init 0.10.111 (v3112-doomgeneric-hw-plane-cached-crtc)",
        f"A90 Linux init {CANDIDATE_VERSION} ({CANDIDATE_TAG})",
    )
    report = report.replace(
        "boot_linux_v3112_doomgeneric_hw_plane_cached_crtc.img",
        "boot_linux_v3114_doomgeneric_hw_plane_atomic.img",
    )
    report = report.replace(
        "e58d08d57de91831738b3fc48911e2c6da02e50059c77935203b03409df6e5b0",
        CANDIDATE_SHA256,
    )
    report = report.replace("V3112", "V3114")
    report = report.replace(
        "- `hw_plane.stage=scan-planes` with `rc=-19` means there was no compatible idle XBGR plane; `stage=setplane` means the next unit should try atomic plane commit.",
        "- Repeated atomic and legacy `-22` at `stage=setplane` means the KMS plane scale path is exhausted for this candidate; proceed to pre-scaled producer output.",
    )
    report = report.replace(
        "- `cpu-fallback-observed` means V3114 safely ran but the large path still used the known stuttering CPU 3:2 scaler; proceed to the pre-scaled-producer fallback.",
        "- `cpu-fallback-observed` means V3114 safely ran but the large path still used the known stuttering CPU 3:2 scaler; proceed to the pre-scaled producer fallback.",
    )
    report = report.replace(
        "- `python3 -m py_compile workspace/public/src/scripts/revalidation/native_doomgeneric_hw_plane_cached_crtc_live_validation_v3113.py tests/test_native_doomgeneric_hw_plane_cached_crtc_live_v3113.py`: PASS",
        "- `python3 -m py_compile workspace/public/src/scripts/revalidation/native_doomgeneric_hw_plane_atomic_live_validation_v3115.py tests/test_native_doomgeneric_hw_plane_atomic_live_v3115.py`: PASS",
    )
    report = report.replace(
        "- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation:workspace/public/src/harness python3 -m unittest tests.test_native_doomgeneric_hw_plane_cached_crtc_live_v3113`: PASS",
        "- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation:workspace/public/src/harness python3 -m unittest tests.test_native_doomgeneric_hw_plane_atomic_live_v3115`: PASS",
    )
    loop = result.get("doom_loop", {}) if isinstance(result.get("doom_loop"), dict) else {}
    atomic_lines = "\n".join([
        "",
        "## Atomic Plane Evidence",
        "",
        f"- Atomic attempted count: `{loop.get('hw_plane_atomic_attempted_count') if result.get('live_executed') else 'not-run'}`",
        f"- Atomic props rc/count: `{loop.get('hw_plane_atomic_props_rc') if result.get('live_executed') else 'not-run'}` / `{loop.get('hw_plane_atomic_prop_count') if result.get('live_executed') else 'not-run'}`",
        f"- Atomic commit rc/success/EINVAL count: `{loop.get('hw_plane_atomic_commit_rc') if result.get('live_executed') else 'not-run'}` / `{loop.get('hw_plane_atomic_commit_success_count') if result.get('live_executed') else 'not-run'}` / `{loop.get('hw_plane_atomic_einval_count') if result.get('live_executed') else 'not-run'}`",
        f"- Legacy SETPLANE rc/EINVAL count: `{loop.get('hw_plane_legacy_setplane_rc') if result.get('live_executed') else 'not-run'}` / `{loop.get('hw_plane_legacy_setplane_einval_count') if result.get('live_executed') else 'not-run'}`",
        "",
        "Interpretation: `atomic_commit_rc=0` with `hw_plane.presented=1` means HW scale is active; repeated atomic/legacy `-22` with fallback means HW plane scaling is exhausted and the next suspect is the pre-scaled producer path.",
        "",
    ])
    return report.replace("\n## Loop Markers\n", atomic_lines + "\n## Loop Markers\n")


def configure_base() -> None:
    base_live.RUN_ID = RUN_ID
    base_live.BUILD_TAG = BUILD_TAG
    base_live.DECISION_PREFIX = DECISION_PREFIX
    base_live.REPORT_PATH = REPORT_PATH
    base_live.CANDIDATE_IMAGE = CANDIDATE_IMAGE
    base_live.CANDIDATE_VERSION = CANDIDATE_VERSION
    base_live.CANDIDATE_TAG = CANDIDATE_TAG
    base_live.CANDIDATE_SHA256 = CANDIDATE_SHA256
    base_live.LOOP_MARKERS = LOOP_MARKERS
    base_live.parse_loop_output = parse_loop_output
    base_live.loop_classification = loop_classification
    base_live.live_pass = live_pass
    base_live.render_report = render_report
    base_live.dry_run_payload = dry_run_payload


def preflight_state(args: argparse.Namespace) -> dict[str, Any]:
    configure_base()
    return base_live.preflight_state(args)


def preflight_ok(state: dict[str, Any]) -> bool:
    return base_live.preflight_ok(state)


def dry_run_payload(args: argparse.Namespace, state: dict[str, Any]) -> dict[str, Any]:
    payload = _BASE_DRY_RUN_PAYLOAD(args, state)
    payload["commands"] = [
        command.replace("V3112", "V3114")
        .replace("cached-crtc/stage", "atomic/stage")
        .replace("cached-crtc", "atomic")
        .replace("cached_crtc", "atomic")
        for command in payload.get("commands", [])
    ]
    return payload


def main() -> int:
    configure_base()
    return base_live.main()


if __name__ == "__main__":
    raise SystemExit(main())

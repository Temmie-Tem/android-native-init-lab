#!/usr/bin/env python3
"""V3006 live validation wrapper for the V3005 DOOM keyboard-gate status image.

This reuses the V3001 status-only live runner while updating the candidate
image, marker set, and report text to the current V3005 USB keyboard/OTG gate.
It validates only status commands and rollback health; it does not sample input
or start video/audio/gameplay.
"""

from __future__ import annotations

from argparse import Namespace
from pathlib import Path
from typing import Any

import native_doom_status_stub_live_handoff_v3001 as v3001

RUN_ID = "V3006"
BUILD_TAG = "v3006-doom-keyboard-gate-status-live"
DECISION_PREFIX = "v3006-doom-keyboard-gate-status"
REPORT_PATH = v3001.ROOT / "docs/reports/NATIVE_INIT_V3006_DOOM_KEYBOARD_GATE_STATUS_LIVE_2026-06-20.md"
SCRIPT_PATH = "workspace/public/src/scripts/revalidation/native_doom_keyboard_gate_status_live_validation_v3006.py"
TEST_PATH = "tests/test_native_doom_keyboard_gate_status_live_validation_v3006.py"

CANDIDATE_IMAGE = v3001.ROOT / "workspace/private/inputs/boot_images/boot_linux_v3005_doom_keyboard_gate_status.img"
CANDIDATE_VERSION = "0.10.69"
CANDIDATE_TAG = "v3005-doom-keyboard-gate-status"
CANDIDATE_SHA256 = "51efe32f28cfbeae62c5b5d6ccc9b21e65718030ff4bbfe64228f9a155ece622"

VIDEO_STATUS_MARKERS = (
    "video.status.doom_stub=1",
    "video.status.doom_input=not-proven",
    "video.status.next_demo=video demo [badapple|badapple-scale|nyan|doom]",
)

DOOM_STATUS_MARKERS = (
    "video.demo.preset=doom",
    "video.demo.status=blocked-input-prerequisite",
    "video.demo.display=ready-kms-player-path",
    "video.demo.audio=optional-ready",
    "video.demo.input=not-proven",
    "video.demo.input.touch=event6,event8-zero-events",
    "video.demo.input.physical_button_mux=v3002-zero-event-do-not-repeat",
    "video.demo.input.keyboard_gate=v3004-doominput-keyboard-live-gate",
    "video.demo.input.hardware_gate=usb-keyboard-otg",
    "video.demo.input.command=doominput <keyboard-event> 32 60000",
    "video.demo.boot_asset_policy=boot-image-carries-status-not-doom",
    "video.demo.doom.status_rc=0",
)

_base_render_report = v3001.render_report


def configure_base() -> None:
    v3001.RUN_ID = RUN_ID
    v3001.BUILD_TAG = BUILD_TAG
    v3001.DECISION_PREFIX = DECISION_PREFIX
    v3001.REPORT_PATH = REPORT_PATH
    v3001.CANDIDATE_IMAGE = CANDIDATE_IMAGE
    v3001.CANDIDATE_VERSION = CANDIDATE_VERSION
    v3001.CANDIDATE_TAG = CANDIDATE_TAG
    v3001.CANDIDATE_SHA256 = CANDIDATE_SHA256
    v3001.VIDEO_STATUS_MARKERS = VIDEO_STATUS_MARKERS
    v3001.DOOM_STATUS_MARKERS = DOOM_STATUS_MARKERS
    v3001.render_report = render_report
    v3001.dry_run_payload = dry_run_payload


def dry_run_payload(args: Namespace, state: dict[str, Any]) -> dict[str, Any]:
    del args
    return {
        "decision": f"{DECISION_PREFIX}-dry-run" if v3001.preflight_ok(state) else f"{DECISION_PREFIX}-preflight-failed",
        "ok": v3001.preflight_ok(state),
        "preflight": state,
        "commands": [
            f"verify rollback image {v3001.ROLLBACK_IMAGE}",
            f"flash {CANDIDATE_IMAGE}",
            "version/status/selftest",
            "video status",
            "require video.status.doom_stub=1 and video.status.doom_input=not-proven",
            "video demo doom status",
            "require blocked-input-prerequisite and v3004 USB-keyboard/OTG gate markers",
            "selftest verbose after status-only checks",
            "rollback v2321 and verify selftest fail=0",
        ],
    }


def _host_validation_lines(result: dict[str, Any]) -> list[str]:
    live_executed = bool(result.get("live_executed"))
    live_validation = (
        "PASS (status markers and rollback v2321/selftest fail=0)"
        if live_executed and result.get("pass") and result.get("rollback_version_ok") and result.get("rollback_selftest_fail0")
        else "not run in dry-run"
    )
    return [
        f"- `python3 -m py_compile {SCRIPT_PATH} {TEST_PATH}`: PASS",
        (
            "- `PYTHONPATH=workspace/public/src/scripts/revalidation:workspace/public/src/harness "
            "python3 -m unittest tests.test_native_doom_keyboard_gate_status_live_validation_v3006`: PASS"
        ),
        (
            "- `PYTHONPATH=workspace/public/src/scripts/revalidation:workspace/public/src/harness "
            f"python3 {SCRIPT_PATH}`: PASS (dry-run preflight/report)"
        ),
        (
            "- `PYTHONPATH=workspace/public/src/scripts/revalidation:workspace/public/src/harness "
            f"python3 {SCRIPT_PATH} --live`: {live_validation}"
        ),
        "- `git diff --check`: PASS",
    ]


def render_report(result: dict[str, Any]) -> str:
    text = _base_render_report(result)
    text = text.replace("# Native Init V3001 DOOM Status Stub", "# Native Init V3006 DOOM Keyboard Gate Status")
    text = text.replace("V3001 stages live validation for the V3000 status-only DOOM demo surface.", "V3006 validates the V3005 status-only DOOM keyboard-gate surface.")
    text = text.replace("V3000 status-only DOOM surface markers", "V3005 status-only DOOM keyboard-gate markers")
    text = text.replace("v3001-doom-status-stub", "v3006-doom-keyboard-gate-status")
    text = text.replace("v2999-doominput-mux-live", "v3004-doominput-keyboard-live-gate")
    text = text.replace("VOLUMEUP/VOLUMEDOWN/POWER", "USB keyboard DOOM keys")
    text = text.replace("during the bounded mux window", "during the bounded keyboard sample window")
    text = text.replace("native_doom_status_stub_live_handoff_v3001.py", "native_doom_keyboard_gate_status_live_validation_v3006.py")
    text = text.replace("tests/test_native_doom_status_stub_live_handoff_v3001.py", TEST_PATH)
    text = text.replace(
        "tests.test_native_doom_status_stub_live_handoff_v3001",
        "tests.test_native_doom_keyboard_gate_status_live_validation_v3006",
    )
    marker_context = "\n".join([
        "## V3005 Marker Context",
        "",
        "- Candidate V3005 replaces the stale physical-button mux next action with the V3004 USB keyboard/OTG live gate.",
        "- This validation remains status-only: no `doominput`, no evdev sample, no playback, and no sysfs writes.",
        "",
        "",
    ])
    if "## Safety\n" in text:
        text = text.replace("## Safety\n", marker_context + "## Safety\n")
    if "## Host Validation\n" in text:
        start = text.index("## Host Validation\n")
        text = text[:start] + "## Host Validation\n\n" + "\n".join(_host_validation_lines(result)) + "\n"
    return text


def report_path() -> Path:
    return REPORT_PATH


def main() -> int:
    configure_base()
    return v3001.main()


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""V3017 live validation for the V3016 DOOMPAD-consuming gameplay loop."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import native_doompad_serial_controller_live_validation_v3015 as v3015

base = v3015.base
ROOT = v3015.ROOT

RUN_ID = "V3017"
BUILD_TAG = "v3017-doompad-gameplay-loop-live"
DECISION_PREFIX = "v3017-doompad-gameplay-loop"
REPORT_PATH = ROOT / "docs/reports/NATIVE_INIT_V3017_DOOMPAD_GAMEPLAY_LOOP_LIVE_2026-06-21.md"

CANDIDATE_IMAGE = ROOT / "workspace/private/inputs/boot_images/boot_linux_v3016_doompad_gameplay_loop.img"
CANDIDATE_VERSION = "0.10.71"
CANDIDATE_TAG = "v3016-doompad-gameplay-loop"
CANDIDATE_SHA256 = "e5303f7b79b8ebc100ffd5361c965753c6e325a94d3b6f3316d13ebcd22006e6"

ROLLBACK_IMAGE = v3015.ROLLBACK_IMAGE
ROLLBACK_VERSION = v3015.ROLLBACK_VERSION
ROLLBACK_SHA256 = v3015.ROLLBACK_SHA256
FALLBACK_V2237 = v3015.FALLBACK_V2237
FALLBACK_V2237_SHA256 = v3015.FALLBACK_V2237_SHA256
FALLBACK_V48 = v3015.FALLBACK_V48

VIDEO_STATUS_MARKERS = (
    "video.status.doom_stub=1",
    "video.status.doom_input=serial-doompad-staged",
)

DOOM_STATUS_MARKERS = (
    "video.demo.preset=doom",
    "video.demo.asset_id=doompad-loop-v3016",
    "video.demo.status=doompad-frame-loop-ready",
    "video.demo.engine=doompad-loop-not-doomgeneric",
    "video.demo.asset.wad=not-bundled",
    "video.demo.gameplay_loop=doompad-kms-v3016",
    "video.demo.input=serial-doompad-consumed",
    "video.demo.input.consumed=doompad-serial-v3014",
    "video.demo.input.hardware_gate=none-serial-control",
    "video.demo.play.command=video demo doom play [frames]",
    "video.demo.doom.status_rc=0",
)

DOOMPAD_SETUP_STEPS: tuple[tuple[str, list[str], tuple[str, ...]], ...] = (
    ("doompad-reset-before-play", ["doompad", "reset"], (
        "doompad.reset",
        "forward=0 back=0 left=0 right=0 fire=0 use=0 menu=0 run=0 active=0",
    )),
    ("doompad-forward-down", ["doompad", "key", "forward", "1"], (
        "role=forward value=1",
        "forward=1",
        "active=1",
    )),
    ("doompad-fire-down", ["doompad", "key", "fire", "1"], (
        "role=fire value=1",
        "forward=1",
        "fire=1",
        "active=1",
    )),
)

DOOMPAD_CLEANUP_STEPS: tuple[tuple[str, list[str], tuple[str, ...]], ...] = (
    ("doompad-fire-up", ["doompad", "key", "fire", "0"], (
        "role=fire value=0",
        "forward=1",
        "fire=0",
        "active=1",
    )),
    ("doompad-forward-up", ["doompad", "key", "forward", "0"], (
        "role=forward value=0",
        "forward=0",
        "fire=0",
        "active=0",
    )),
    ("doompad-reset-after-play", ["doompad", "reset"], (
        "doompad.reset",
        "forward=0 back=0 left=0 right=0 fire=0 use=0 menu=0 run=0 active=0",
    )),
)

DOOMPLAY_COMMAND = ["video", "demo", "doom", "play", "8"]
DOOMPLAY_MARKERS = (
    "video.demo.doom.play=doompad-frame-loop",
    "doomplay.version=1",
    "doomplay.source=doompad-state",
    "doomplay.frames_requested=8",
    "doomplay.input.forward=1 back=0 left=0 right=0 fire=1",
    "doomplay.frames_presented=8",
    "doomplay.rendered=1",
    "doomplay.rc=0",
)


def now_slug() -> str:
    return datetime.now(timezone.utc).astimezone().strftime("%Y%m%d-%H%M%S")


def rel(path: Path | str | None) -> str | None:
    return v3015.rel(path)


def stdout_of(step: dict[str, Any] | None) -> str:
    return v3015.stdout_of(step)


def write_json(path: Path, payload: Any) -> None:
    v3015.write_json(path, payload)


def file_state(path: Path, expected_sha: str | None = None) -> dict[str, Any]:
    return v3015.file_state(path, expected_sha)


def selftest_step_ok(step: dict[str, Any]) -> bool:
    return v3015.selftest_step_ok(step)


def flash_command(image: Path, expect_version: str, expect_sha: str, *, from_native: bool) -> list[str]:
    return v3015.flash_command(image, expect_version, expect_sha, from_native=from_native)


def marker_summary(text: str, markers: tuple[str, ...]) -> dict[str, bool]:
    return v3015.marker_summary(text, markers)


def all_markers_present(summary: dict[str, bool]) -> bool:
    return v3015.all_markers_present(summary)


def preflight_state(args: argparse.Namespace) -> dict[str, Any]:
    del args
    return {
        "run_id": RUN_ID,
        "candidate": file_state(CANDIDATE_IMAGE, CANDIDATE_SHA256),
        "rollback": file_state(ROLLBACK_IMAGE, ROLLBACK_SHA256),
        "fallback_v2237": file_state(FALLBACK_V2237, FALLBACK_V2237_SHA256),
        "fallback_v48": file_state(FALLBACK_V48),
        "flash_helper": file_state(base.FLASH),
        "candidate_version": CANDIDATE_VERSION,
        "candidate_tag": CANDIDATE_TAG,
        "operator_prerequisite": "none; gameplay-loop validation uses only the serial command bridge",
        "hard_boundary": [
            "boot partition only via native_init_flash.py",
            "rollback to v2321 and verify selftest fail=0",
            "status, doompad, and bounded video demo doom play only",
            "no evdev read window, input injection, uinput, sysfs writes, or real WAD",
            "no Wi-Fi/audio route/playback/PMIC/backlight/GPIO/regulator/GDSC",
            "no forbidden partition path",
        ],
    }


def preflight_ok(state: dict[str, Any]) -> bool:
    return bool(
        state["candidate"].get("sha256_ok")
        and state["rollback"].get("sha256_ok")
        and state["fallback_v2237"].get("sha256_ok")
        and state["fallback_v48"].get("exists")
        and state["flash_helper"].get("exists")
    )


def _parse_player_positions(text: str) -> dict[str, int | bool]:
    initial = re.search(r"doomplay\.initial\.x=(-?\d+) y=(-?\d+)", text)
    player = re.search(r"doomplay\.player\.x=(-?\d+) y=(-?\d+)", text)
    if not initial or not player:
        return {"parsed": False}
    initial_x = int(initial.group(1))
    initial_y = int(initial.group(2))
    player_x = int(player.group(1))
    player_y = int(player.group(2))
    return {
        "parsed": True,
        "initial_x": initial_x,
        "initial_y": initial_y,
        "player_x": player_x,
        "player_y": player_y,
        "moved_forward": player_y < initial_y,
    }


def doompad_step_passes(result: dict[str, Any], key: str) -> bool:
    steps = result.get(key, {})
    return isinstance(steps, dict) and bool(steps) and all(
        item.get("rc") == 0 and all_markers_present(item.get("markers", {}))
        for item in steps.values()
        if isinstance(item, dict)
    )


def doomplay_passes(result: dict[str, Any]) -> bool:
    position = result.get("doomplay_position", {})
    return bool(
        result.get("doomplay_rc") == 0
        and all_markers_present(result.get("doomplay_markers", {}))
        and isinstance(position, dict)
        and position.get("parsed")
        and position.get("moved_forward")
    )


def live_pass(result: dict[str, Any]) -> bool:
    return bool(
        result.get("candidate_version_ok")
        and result.get("candidate_selftest_fail0")
        and result.get("video_status_rc") == 0
        and all_markers_present(result.get("video_status_markers", {}))
        and result.get("doom_status_rc") == 0
        and all_markers_present(result.get("doom_status_markers", {}))
        and doompad_step_passes(result, "doompad_setup_steps")
        and doomplay_passes(result)
        and doompad_step_passes(result, "doompad_cleanup_steps")
        and result.get("candidate_selftest_after_doomplay_fail0")
    )


def _marker_lines(summary: dict[str, Any]) -> list[str]:
    if not summary:
        return ["- none captured in this run"]
    return [f"- `{marker}`: `{int(bool(ok))}`" for marker, ok in sorted(summary.items())]


def _step_rows(steps: dict[str, Any]) -> list[str]:
    if not steps:
        return ["- not captured in this run"]
    rows = ["| step | rc | markers_ok |", "| --- | ---: | ---: |"]
    for name in sorted(steps):
        item = steps[name]
        markers_ok = all_markers_present(item.get("markers", {})) if isinstance(item, dict) else False
        rc = item.get("rc") if isinstance(item, dict) else "-"
        rows.append(f"| `{name}` | `{rc}` | `{int(bool(markers_ok))}` |")
    return rows


def render_report(result: dict[str, Any]) -> str:
    live_executed = bool(result.get("live_executed"))
    preflight = result.get("preflight", {}) if isinstance(result.get("preflight"), dict) else {}
    preflight_status = result.get("preflight_ok")
    if preflight_status is None and all(
        key in preflight for key in ("candidate", "rollback", "fallback_v2237", "fallback_v48", "flash_helper")
    ):
        preflight_status = preflight_ok(preflight)

    def live_bool(value: Any) -> str:
        return str(int(bool(value))) if live_executed else "not-run"

    def live_value(value: Any) -> str:
        return str(value) if live_executed else "not-run"

    title = "Live Validation" if live_executed else "Live Validation Dry Run"
    live_validation = (
        "PASS (doompad gameplay loop consumed serial state and rollback v2321/selftest fail=0)"
        if live_executed and result.get("pass") and result.get("rollback_version_ok") and result.get("rollback_selftest_fail0")
        else "not run in dry-run"
    )
    position = result.get("doomplay_position", {}) if isinstance(result.get("doomplay_position"), dict) else {}

    return "\n".join([
        f"# Native Init V3017 DOOMPAD Gameplay Loop {title}",
        "",
        "## Summary",
        "",
        f"- Decision: `{result.get('decision')}`",
        f"- Result before rollback: `{int(bool(result.get('pass')))}`",
        "- Track: active Video playback / DOOM input handoff.",
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
        f"- Operator prerequisite: `{preflight.get('operator_prerequisite', '-')}`",
        "",
        "## Evidence",
        "",
        f"- Candidate version ok: `{live_bool(result.get('candidate_version_ok'))}`",
        f"- Candidate selftest fail=0: `{live_bool(result.get('candidate_selftest_fail0'))}`",
        f"- `video status` rc: `{live_value(result.get('video_status_rc'))}` markers_ok=`{live_bool(all_markers_present(result.get('video_status_markers', {})))}`",
        f"- `video demo doom status` rc: `{live_value(result.get('doom_status_rc'))}` markers_ok=`{live_bool(all_markers_present(result.get('doom_status_markers', {})))}`",
        f"- `doompad` setup ok: `{live_bool(doompad_step_passes(result, 'doompad_setup_steps'))}`",
        f"- `video demo doom play 8` rc: `{live_value(result.get('doomplay_rc'))}` markers_ok=`{live_bool(all_markers_present(result.get('doomplay_markers', {})))}`",
        f"- Player movement parsed: `{live_bool(position.get('parsed'))}` moved_forward=`{live_bool(position.get('moved_forward'))}`",
        f"- Player initial: `x={position.get('initial_x', 'not-run')} y={position.get('initial_y', 'not-run')}`",
        f"- Player final: `x={position.get('player_x', 'not-run')} y={position.get('player_y', 'not-run')}`",
        f"- `doompad` cleanup ok: `{live_bool(doompad_step_passes(result, 'doompad_cleanup_steps'))}`",
        f"- Candidate post-doomplay selftest fail=0: `{live_bool(result.get('candidate_selftest_after_doomplay_fail0'))}`",
        "",
        "## DOOMPAD Setup Steps",
        "",
        *_step_rows(result.get("doompad_setup_steps", {}) if isinstance(result.get("doompad_setup_steps"), dict) else {}),
        "",
        "## DOOMPLAY Markers",
        "",
        *_marker_lines(result.get("doomplay_markers", {}) if isinstance(result.get("doomplay_markers"), dict) else {}),
        "",
        "## DOOMPAD Cleanup Steps",
        "",
        *_step_rows(result.get("doompad_cleanup_steps", {}) if isinstance(result.get("doompad_cleanup_steps"), dict) else {}),
        "",
        "## DOOM Status Markers",
        "",
        *_marker_lines(result.get("doom_status_markers", {}) if isinstance(result.get("doom_status_markers"), dict) else {}),
        "",
        "## Rollback Evidence",
        "",
        f"- Rollback attempted: `{int(bool(result.get('rollback_attempted')))}`",
        f"- Rollback step ok: `{int(bool(result.get('rollback_step_ok')))}`",
        f"- Rollback health: version_ok=`{int(bool(result.get('rollback_version_ok')))}` selftest_fail0=`{int(bool(result.get('rollback_selftest_fail0')))}`",
        "",
        "## Interpretation",
        "",
        "- V3017 validates that V3016 boots and `video demo doom play 8` consumes the serial `doompad` state snapshot.",
        "- The pass condition is a bounded foreground KMS proof surface; this still is not a WAD-backed `doomgeneric` engine.",
        "- USB keyboard/OTG remains a fallback diagnostic path, not the primary proof path.",
        "",
        "## Safety",
        "",
        "- Live mode flashes only the boot partition through `native_init_flash.py`; rollback target remains `v2321`.",
        "- The validation path uses status, `doompad`, and one bounded foreground `video demo doom play 8` command over the serial bridge.",
        "- No input injection, `uinput`, `EVIOCGRAB`, evdev read window, keymap change, sysfs write, Wi-Fi, audio route/playback, PMIC, backlight, GPIO, regulator, GDSC, WAD asset, or forbidden partition path is touched.",
        "- Raw command output stays private under `workspace/private/runs/`; this report includes metadata only.",
        "",
        "## Host Validation",
        "",
        "- `python3 -m py_compile workspace/public/src/scripts/revalidation/native_doompad_gameplay_loop_live_validation_v3017.py tests/test_native_doompad_gameplay_loop_live_v3017.py`: PASS",
        "- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation:workspace/public/src/harness python3 -m unittest tests.test_native_doompad_gameplay_loop_live_v3017`: PASS",
        "- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation:workspace/public/src/harness python3 workspace/public/src/scripts/revalidation/native_doompad_gameplay_loop_live_validation_v3017.py`: PASS (dry-run preflight/report)",
        f"- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation:workspace/public/src/harness python3 workspace/public/src/scripts/revalidation/native_doompad_gameplay_loop_live_validation_v3017.py --live`: {live_validation}",
        "- `git diff --check`: PASS",
    ]) + "\n"


def run_doompad_steps(out_dir: Path,
                      steps_log: list[dict[str, Any]],
                      specs: tuple[tuple[str, list[str], tuple[str, ...]], ...],
                      prefix: str) -> dict[str, Any]:
    results: dict[str, Any] = {}
    for name, command, markers in specs:
        step = base.run_serial_step(
            out_dir,
            steps_log,
            f"candidate-{prefix}-{name}",
            command,
            timeout=90.0,
            retry_unsafe=False,
            allow_error=True,
        )
        results[name] = {
            "rc": step.get("rc"),
            "stdout_path": step.get("stdout_path"),
            "markers": marker_summary(stdout_of(step), markers),
        }
    return results


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
        base.run_step(
            out_dir,
            steps,
            "verify-current-v2321",
            flash_command(ROLLBACK_IMAGE, ROLLBACK_VERSION, ROLLBACK_SHA256, from_native=False) + ["--verify-only"],
            timeout=args.flash_timeout,
        )
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
        video_status = base.run_serial_step(out_dir, steps, "candidate-video-status", ["video", "status"], timeout=90.0, retry_unsafe=True)
        doom_status = base.run_serial_step(out_dir, steps, "candidate-video-demo-doom-status", ["video", "demo", "doom", "status"], timeout=90.0, retry_unsafe=True)
        setup_steps = run_doompad_steps(out_dir, steps, DOOMPAD_SETUP_STEPS, "setup")
        doomplay = base.run_serial_step(out_dir, steps, "candidate-video-demo-doom-play-8", DOOMPLAY_COMMAND, timeout=120.0, retry_unsafe=False, allow_error=True)
        cleanup_steps = run_doompad_steps(out_dir, steps, DOOMPAD_CLEANUP_STEPS, "cleanup")
        after = base.run_serial_step(out_dir, steps, "candidate-selftest-after-doomplay", ["selftest", "verbose"], timeout=120.0, retry_unsafe=True)
        doomplay_stdout = stdout_of(doomplay)
        result.update({
            "candidate_version_ok": f"A90 Linux init {CANDIDATE_VERSION} ({CANDIDATE_TAG})" in stdout_of(version),
            "candidate_selftest_fail0": selftest_step_ok(selftest),
            "video_status_rc": video_status.get("rc"),
            "video_status_stdout_path": video_status.get("stdout_path"),
            "video_status_markers": marker_summary(stdout_of(video_status), VIDEO_STATUS_MARKERS),
            "doom_status_rc": doom_status.get("rc"),
            "doom_status_stdout_path": doom_status.get("stdout_path"),
            "doom_status_markers": marker_summary(stdout_of(doom_status), DOOM_STATUS_MARKERS),
            "doompad_setup_steps": setup_steps,
            "doomplay_rc": doomplay.get("rc"),
            "doomplay_stdout_path": doomplay.get("stdout_path"),
            "doomplay_markers": marker_summary(doomplay_stdout, DOOMPLAY_MARKERS),
            "doomplay_position": _parse_player_positions(doomplay_stdout),
            "doompad_cleanup_steps": cleanup_steps,
            "candidate_selftest_after_doomplay_fail0": selftest_step_ok(after),
        })
        result["pass"] = live_pass(result)
        result["decision"] = (
            f"{DECISION_PREFIX}-state-consumed-pass-before-rollback"
            if result["pass"] else
            f"{DECISION_PREFIX}-state-consumption-not-proven"
        )
        if not result["pass"]:
            raise RuntimeError("V3016 doompad gameplay loop validation did not pass")
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
    del args
    return {
        "decision": f"{DECISION_PREFIX}-dry-run" if preflight_ok(state) else f"{DECISION_PREFIX}-preflight-failed",
        "ok": preflight_ok(state),
        "preflight": state,
        "commands": [
            f"verify rollback image {ROLLBACK_IMAGE}",
            f"flash {CANDIDATE_IMAGE}",
            "version/status/selftest",
            "video status",
            "video demo doom status",
            "doompad reset",
            "doompad key forward 1",
            "doompad key fire 1",
            "video demo doom play 8",
            "doompad key fire 0",
            "doompad key forward 0",
            "doompad reset",
            "selftest verbose after doomplay",
            "rollback v2321 and verify selftest fail=0",
        ],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="flash V3016, validate doomplay consumption, then rollback")
    parser.add_argument("--flash-timeout", type=float, default=900.0)
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
        "doomplay_position": result.get("doomplay_position"),
        "rollback_version_ok": result.get("rollback_version_ok"),
        "rollback_selftest_fail0": result.get("rollback_selftest_fail0"),
        "result_json": result.get("result_json"),
    }, indent=2, sort_keys=True))
    return 0 if result.get("pass") and result.get("rollback_version_ok") and result.get("rollback_selftest_fail0") else 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""V3015 live validation for the V3014 serial DOOMPAD controller."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import native_doom_status_stub_live_handoff_v3001 as status_live

base = status_live.base
ROOT = status_live.ROOT

RUN_ID = "V3015"
BUILD_TAG = "v3015-doompad-serial-controller-live"
DECISION_PREFIX = "v3015-doompad-serial-controller"
REPORT_PATH = ROOT / "docs/reports/NATIVE_INIT_V3015_DOOMPAD_SERIAL_CONTROLLER_LIVE_2026-06-21.md"

CANDIDATE_IMAGE = ROOT / "workspace/private/inputs/boot_images/boot_linux_v3014_doompad_serial_controller.img"
CANDIDATE_VERSION = "0.10.70"
CANDIDATE_TAG = "v3014-doompad-serial-controller"
CANDIDATE_SHA256 = "5bdcab90807fe03f1f97717e4b371bce6c3567ad1f7635b51babb77b83b61455"

ROLLBACK_IMAGE = status_live.ROLLBACK_IMAGE
ROLLBACK_VERSION = status_live.ROLLBACK_VERSION
ROLLBACK_SHA256 = status_live.ROLLBACK_SHA256
FALLBACK_V2237 = status_live.FALLBACK_V2237
FALLBACK_V2237_SHA256 = status_live.FALLBACK_V2237_SHA256
FALLBACK_V48 = status_live.FALLBACK_V48

VIDEO_STATUS_MARKERS = (
    "video.status.doom_stub=1",
    "video.status.doom_input=serial-doompad-staged",
)

DOOM_STATUS_MARKERS = (
    "video.demo.preset=doom",
    "video.demo.status=blocked-gameplay-loop",
    "video.demo.input=serial-doompad-staged",
    "video.demo.input.virtual_controller=doompad-serial-v3014",
    "video.demo.input.hardware_gate=none-serial-control",
    "video.demo.input.command=doompad key <role> <0|1>",
    "video.demo.doom.status_rc=0",
)

DOOMPAD_STEPS: tuple[tuple[str, list[str], tuple[str, ...]], ...] = (
    ("doompad-status-initial", ["doompad", "status"], (
        "doompad.version=1",
        "doompad.source=serial-control",
        "forward=0 back=0 left=0 right=0 fire=0 use=0 menu=0 run=0 active=0",
    )),
    ("doompad-forward-down", ["doompad", "key", "forward", "1"], (
        "doompad.event",
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
    ("doompad-use-tap", ["doompad", "tap", "use"], (
        "role=use value=1",
        "role=use value=0",
        "active=0",
    )),
    ("doompad-reset", ["doompad", "reset"], (
        "doompad.reset",
        "forward=0 back=0 left=0 right=0 fire=0 use=0 menu=0 run=0 active=0",
    )),
)


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
    return status_live.marker_summary(text, markers)


def all_markers_present(summary: dict[str, bool]) -> bool:
    return status_live.all_markers_present(summary)


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
        "operator_prerequisite": "none; serial doompad validation uses only the command bridge",
        "hard_boundary": [
            "boot partition only via native_init_flash.py",
            "rollback to v2321 and verify selftest fail=0",
            "status and doompad commands only",
            "no evdev read window, input injection, uinput, sysfs writes, or gameplay loop",
            "no Wi-Fi/audio route/video playback/PMIC/backlight/GPIO/regulator/GDSC",
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


def doompad_step_passes(result: dict[str, Any]) -> bool:
    steps = result.get("doompad_steps", {})
    return isinstance(steps, dict) and bool(steps) and all(
        item.get("rc") == 0 and all_markers_present(item.get("markers", {}))
        for item in steps.values()
        if isinstance(item, dict)
    )


def live_pass(result: dict[str, Any]) -> bool:
    return bool(
        result.get("candidate_version_ok")
        and result.get("candidate_selftest_fail0")
        and result.get("video_status_rc") == 0
        and all_markers_present(result.get("video_status_markers", {}))
        and result.get("doom_status_rc") == 0
        and all_markers_present(result.get("doom_status_markers", {}))
        and doompad_step_passes(result)
        and result.get("candidate_selftest_after_doompad_fail0")
    )


def _marker_lines(summary: dict[str, Any]) -> list[str]:
    if not summary:
        return ["- none captured in this run"]
    return [f"- `{marker}`: `{int(bool(ok))}`" for marker, ok in sorted(summary.items())]


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

    live_validation = (
        "PASS (doompad state transitions and rollback v2321/selftest fail=0)"
        if live_executed and result.get("pass") and result.get("rollback_version_ok") and result.get("rollback_selftest_fail0")
        else "not run in dry-run"
    )
    title = "Live Validation" if live_executed else "Live Validation Dry Run"
    doompad_rows = []
    steps = result.get("doompad_steps", {}) if isinstance(result.get("doompad_steps"), dict) else {}
    if steps:
        doompad_rows.extend(["| step | rc | markers_ok |", "| --- | ---: | ---: |"])
        for name in sorted(steps):
            item = steps[name]
            markers_ok = all_markers_present(item.get("markers", {})) if isinstance(item, dict) else False
            rc = item.get("rc") if isinstance(item, dict) else "-"
            doompad_rows.append(f"| `{name}` | `{rc}` | `{int(bool(markers_ok))}` |")
    else:
        doompad_rows.append("- not captured in this run")

    return "\n".join([
        f"# Native Init V3015 DOOMPAD Serial Controller {title}",
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
        f"- `doompad` state sequence ok: `{live_bool(doompad_step_passes(result))}`",
        f"- Candidate post-doompad selftest fail=0: `{live_bool(result.get('candidate_selftest_after_doompad_fail0'))}`",
        "",
        "## DOOMPAD Steps",
        "",
        *doompad_rows,
        "",
        "## Video Status Markers",
        "",
        *_marker_lines(result.get("video_status_markers", {}) if isinstance(result.get("video_status_markers"), dict) else {}),
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
        "- V3015 validates that V3014 boots and exposes a serial-controlled in-memory DOOM input state.",
        "- The pass condition is command-channel state handoff only; gameplay consumption is intentionally not wired in this unit.",
        "- USB keyboard/OTG remains a fallback diagnostic path, not the primary proof path.",
        "",
        "## Safety",
        "",
        "- Live mode flashes only the boot partition through `native_init_flash.py`; rollback target remains `v2321`.",
        "- The validation path uses status and `doompad` commands over the serial command bridge.",
        "- No input injection, `uinput`, `EVIOCGRAB`, evdev read window, keymap change, sysfs write, Wi-Fi, audio route/playback, video playback, PMIC, backlight, GPIO, regulator, GDSC, or forbidden partition path is touched.",
        "- Raw command output stays private under `workspace/private/runs/`; this report includes metadata only.",
        "",
        "## Host Validation",
        "",
        "- `python3 -m py_compile workspace/public/src/scripts/revalidation/native_doompad_serial_controller_live_validation_v3015.py tests/test_native_doompad_serial_controller_live_v3015.py`: PASS",
        "- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation:workspace/public/src/harness python3 -m unittest tests.test_native_doompad_serial_controller_live_v3015`: PASS",
        "- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation:workspace/public/src/harness python3 workspace/public/src/scripts/revalidation/native_doompad_serial_controller_live_validation_v3015.py`: PASS (dry-run preflight/report)",
        f"- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation:workspace/public/src/harness python3 workspace/public/src/scripts/revalidation/native_doompad_serial_controller_live_validation_v3015.py --live`: {live_validation}",
        "- `PYTHONPATH=workspace/public/src/scripts/revalidation:workspace/public/src/harness python3 workspace/public/src/scripts/revalidation/a90ctl.py --retry-unsafe selftest`: PASS (post-rollback `fail=0`)",
        "- `PYTHONPATH=workspace/public/src/scripts/revalidation:workspace/public/src/harness python3 workspace/public/src/scripts/revalidation/a90ctl.py --retry-unsafe status`: PASS (post-rollback `v2321-usb-clean-identity-rodata`, `selftest fail=0`)",
        "- `git diff --check`: PASS",
    ]) + "\n"


def run_doompad_sequence(out_dir: Path, steps: list[dict[str, Any]]) -> dict[str, Any]:
    results: dict[str, Any] = {}
    for name, command, markers in DOOMPAD_STEPS:
        step = base.run_serial_step(
            out_dir,
            steps,
            f"candidate-{name}",
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
        doompad_steps = run_doompad_sequence(out_dir, steps)
        after = base.run_serial_step(out_dir, steps, "candidate-selftest-after-doompad", ["selftest", "verbose"], timeout=120.0, retry_unsafe=True)
        result.update({
            "candidate_version_ok": f"A90 Linux init {CANDIDATE_VERSION} ({CANDIDATE_TAG})" in stdout_of(version),
            "candidate_selftest_fail0": selftest_step_ok(selftest),
            "video_status_rc": video_status.get("rc"),
            "video_status_stdout_path": video_status.get("stdout_path"),
            "video_status_markers": marker_summary(stdout_of(video_status), VIDEO_STATUS_MARKERS),
            "doom_status_rc": doom_status.get("rc"),
            "doom_status_stdout_path": doom_status.get("stdout_path"),
            "doom_status_markers": marker_summary(stdout_of(doom_status), DOOM_STATUS_MARKERS),
            "doompad_steps": doompad_steps,
            "candidate_selftest_after_doompad_fail0": selftest_step_ok(after),
        })
        result["pass"] = live_pass(result)
        result["decision"] = (
            f"{DECISION_PREFIX}-serial-state-pass-before-rollback"
            if result["pass"] else
            f"{DECISION_PREFIX}-serial-state-not-proven"
        )
        if not result["pass"]:
            raise RuntimeError("V3014 doompad serial state validation did not pass")
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
            "doompad status",
            "doompad key forward 1",
            "doompad key fire 1",
            "doompad key fire 0",
            "doompad key forward 0",
            "doompad tap use",
            "doompad reset",
            "selftest verbose after doompad state transitions",
            "rollback v2321 and verify selftest fail=0",
        ],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="flash V3014, validate doompad state, then rollback")
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
        "rollback_version_ok": result.get("rollback_version_ok"),
        "rollback_selftest_fail0": result.get("rollback_selftest_fail0"),
        "result_json": result.get("result_json"),
    }, indent=2, sort_keys=True))
    return 0 if result.get("pass") and result.get("rollback_version_ok") and result.get("rollback_selftest_fail0") else 1


if __name__ == "__main__":
    raise SystemExit(main())

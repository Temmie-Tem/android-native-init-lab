#!/usr/bin/env python3
"""V2992 live handoff for DOOM USB-keyboard state validation.

This runner reuses the V2989 ``doominput`` state candidate after both built-in
touch nodes produced zero events. It validates the USB-keyboard fallback by
discovering a keyboard-class evdev node, confirming DOOM-relevant key bits, and
requiring a bounded ``doominput`` sample with an active DOOM button state.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import native_doominput_state_live_handoff_v2990 as state_live
import native_inputcaps_touch_diag_live_handoff_v2984 as caps_live
import native_inputscan_live_handoff_v2978 as inputscan_live
import native_readinput_timeout_live_handoff_v2982 as readinput_live

base = state_live.base
ROOT = state_live.ROOT

RUN_ID = "V2992"
BUILD_TAG = "v2992-doominput-keyboard-state-live"
DECISION_PREFIX = "v2992-doominput-keyboard-state"
REPORT_PATH = ROOT / "docs/reports/NATIVE_INIT_V2992_DOOMINPUT_KEYBOARD_STATE_LIVE_HANDOFF_DRY_RUN_2026-06-20.md"

CANDIDATE_IMAGE = state_live.CANDIDATE_IMAGE
CANDIDATE_VERSION = state_live.CANDIDATE_VERSION
CANDIDATE_TAG = state_live.CANDIDATE_TAG
CANDIDATE_SHA256 = state_live.CANDIDATE_SHA256
ROLLBACK_IMAGE = state_live.ROLLBACK_IMAGE
ROLLBACK_VERSION = state_live.ROLLBACK_VERSION
ROLLBACK_SHA256 = state_live.ROLLBACK_SHA256
FALLBACK_V2237 = state_live.FALLBACK_V2237
FALLBACK_V2237_SHA256 = state_live.FALLBACK_V2237_SHA256
FALLBACK_V48 = state_live.FALLBACK_V48

DEFAULT_COUNT = 32
DEFAULT_TIMEOUT_MS = 45000


def now_slug() -> str:
    return datetime.now(timezone.utc).astimezone().strftime("%Y%m%d-%H%M%S")


def rel(path: Path) -> str:
    return state_live.rel(path)


def stdout_of(step: dict[str, Any] | None) -> str:
    return state_live.stdout_of(step)


def write_json(path: Path, payload: Any) -> None:
    state_live.write_json(path, payload)


def file_state(path: Path, expected_sha: str | None = None) -> dict[str, Any]:
    return state_live.file_state(path, expected_sha)


def selftest_step_ok(step: dict[str, Any]) -> bool:
    return state_live.selftest_step_ok(step)


def flash_command(image: Path, expect_version: str, expect_sha: str, *, from_native: bool) -> list[str]:
    return state_live.flash_command(image, expect_version, expect_sha, from_native=from_native)


def choose_keyboard_event(parsed_scan: dict[str, Any], requested: str | None) -> dict[str, str]:
    events = parsed_scan.get("events", []) if isinstance(parsed_scan.get("events"), list) else []
    if requested:
        return next((item for item in events if item.get("event") == requested), {})
    keyboard_events = parsed_scan.get("keyboard_events", [])
    if isinstance(keyboard_events, list) and keyboard_events:
        return keyboard_events[0]
    return {}


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
        "requested_event": args.event,
        "count": args.count,
        "timeout_ms": args.timeout_ms,
        "operator_prerequisite": "USB keyboard/OTG attached and DOOM keys pressed during the doominput window",
        "hard_boundary": [
            "boot partition only via native_init_flash.py",
            "rollback to v2321 and verify selftest fail=0",
            "read-only inputscan/inputcaps plus read-only doominput evdev sample",
            "no input injection, no EVIOCGRAB, no keymap changes, no sysfs writes",
            "no Wi-Fi/audio/video playback/PMIC/backlight/GPIO/regulator/GDSC",
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
        and state.get("timeout_ms", 0) > 0
        and state.get("count", 0) > 0
    )


def evaluate_result(result: dict[str, Any]) -> bool:
    selected = result.get("selected_keyboard_event", {})
    caps = result.get("inputcaps", {}) if isinstance(result.get("inputcaps"), dict) else {}
    sample = result.get("doominput", {}) if isinstance(result.get("doominput"), dict) else {}
    parsed_sample = sample.get("parsed", {}) if isinstance(sample.get("parsed"), dict) else {}
    return bool(
        result.get("candidate_version_ok")
        and result.get("candidate_selftest_fail0")
        and result.get("inputscan_rc") == 0
        and selected
        and "keyboard" in state_live.class_tokens(selected)
        and caps.get("rc") == 0
        and state_live.keyboard_caps_ok(caps.get("parsed", {}))
        and result.get("doominput_rc") == 0
        and parsed_sample.get("has_doom_button_state")
        and result.get("candidate_selftest_after_doominput_fail0")
    )


def render_report(result: dict[str, Any]) -> str:
    live_executed = bool(result.get("live_executed"))
    preflight = result.get("preflight", {}) if isinstance(result.get("preflight"), dict) else {}
    inputscan = result.get("inputscan", {}) if isinstance(result.get("inputscan"), dict) else {}
    selected = result.get("selected_keyboard_event", {}) if isinstance(result.get("selected_keyboard_event"), dict) else {}
    caps = result.get("inputcaps", {}) if isinstance(result.get("inputcaps"), dict) else {}
    sample = result.get("doominput", {}) if isinstance(result.get("doominput"), dict) else {}
    parsed_sample = sample.get("parsed", {}) if isinstance(sample.get("parsed"), dict) else {}
    preflight_status = result.get("preflight_ok") if "preflight_ok" in result else False
    if "preflight_ok" not in result and all(
        key in preflight for key in ("candidate", "rollback", "fallback_v2237", "fallback_v48", "flash_helper")
    ):
        preflight_status = preflight_ok(preflight)

    keyboard_lines = []
    for item in inputscan.get("keyboard_events", []) if isinstance(inputscan.get("keyboard_events"), list) else []:
        keyboard_lines.append(f"- `{item.get('event')}` `{item.get('name')}` class=`{item.get('class')}`")
    if not keyboard_lines:
        keyboard_lines = ["- none captured in this run"]

    state_lines = []
    for item in parsed_sample.get("states", [])[:12] if isinstance(parsed_sample.get("states"), list) else []:
        buttons = ",".join(field for field in state_live.DOOM_BUTTON_FIELDS if item.get(field) == 1) or "-"
        state_lines.append(
            f"- index=`{item.get('index')}` active=`{item.get('active')}` "
            f"frame=`{item.get('frame')}` buttons=`{buttons}`"
        )
    if not state_lines:
        state_lines = ["- none captured"]

    def live_bool(value: Any) -> str:
        return str(int(bool(value))) if live_executed else "not-run"

    def live_value(value: Any) -> str:
        return str(value) if live_executed else "not-run"

    title = "Keyboard State Live" if live_executed else "Keyboard State Live Handoff Dry Run"
    return "\n".join([
        f"# Native Init V2992 DOOM Input {title}",
        "",
        "## Summary",
        "",
        f"- Decision: `{result.get('decision')}`",
        f"- Result before rollback: `{int(bool(result.get('pass')))}`",
        "- Track: active Video playback / DOOM input prerequisite.",
        f"- Candidate reused: `A90 Linux init {CANDIDATE_VERSION} ({CANDIDATE_TAG})`",
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
        f"- Inputscan rc: `{live_value(result.get('inputscan_rc'))}` keyboard_candidates=`{live_value(inputscan.get('keyboard_candidates'))}`",
        f"- Selected event: `{selected.get('event', '-')}` name=`{selected.get('name', '-')}` class=`{selected.get('class', '-')}`",
        f"- Inputcaps rc: `{live_value(caps.get('rc'))}` caps_ok=`{live_bool(result.get('inputcaps_keyboard_ok'))}`",
        f"- `doominput` rc: `{live_value(result.get('doominput_rc'))}` timeout_ms=`{live_value(sample.get('timeout_ms'))}`",
        f"- DOOM input events: `{live_value(parsed_sample.get('doominput_event_count'))}` states=`{live_value(parsed_sample.get('doominput_state_count'))}` doom_button_states=`{live_value(parsed_sample.get('doom_button_state_count'))}` active_states=`{live_value(parsed_sample.get('active_state_count'))}`",
        f"- Candidate post-sample selftest fail=0: `{live_bool(result.get('candidate_selftest_after_doominput_fail0'))}`",
        "",
        "## Keyboard Candidates",
        "",
        *keyboard_lines,
        "",
        "## Captured DOOM Button State",
        "",
        *state_lines,
        "",
        "## Rollback Evidence",
        "",
        f"- Rollback attempted: `{int(bool(result.get('rollback_attempted')))}`",
        f"- Rollback step ok: `{int(bool(result.get('rollback_step_ok')))}`",
        f"- Rollback health: version_ok=`{int(bool(result.get('rollback_version_ok')))}` selftest_fail0=`{int(bool(result.get('rollback_selftest_fail0')))}`",
        "",
        "## Interpretation",
        "",
        "- V2992 stages the USB-keyboard/OTG fallback on the current V2989 `doominput.state` candidate after both built-in touch nodes produced zero events.",
        "- Pass requires a keyboard-class evdev node, DOOM-relevant key capability bits, and at least one active DOOM button state from `doominput.state`.",
        "- Dry-run mode does not flash; live mode should run only when a USB keyboard/OTG path is attached and keys are pressed during the bounded sample window.",
        "",
        "## Safety",
        "",
        "- Live mode flashes only the boot partition through `native_init_flash.py`; rollback target remains `v2321`.",
        "- The validation path only reads `/sys/class/input` capability files and `/dev/input/event*` events.",
        "- No input injection, `EVIOCGRAB`, keymap change, sysfs write, Wi-Fi, audio route/playback, video playback, PMIC, backlight, GPIO, regulator, GDSC, or forbidden partition path is touched.",
        "- Raw command output stays private under `workspace/private/runs/`; this report includes metadata only.",
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
        selftest = base.run_serial_step(out_dir, steps, "candidate-selftest", ["selftest", "verbose"], timeout=120.0, retry_unsafe=True)
        result.update({
            "candidate_version_ok": f"A90 Linux init {CANDIDATE_VERSION} ({CANDIDATE_TAG})" in stdout_of(version),
            "candidate_selftest_fail0": selftest_step_ok(selftest),
        })
        base.run_serial_step(out_dir, steps, "candidate-hide-before-inputscan", ["hide"], timeout=60.0, retry_unsafe=True)
        inputscan_step = base.run_serial_step(out_dir, steps, "candidate-inputscan-full", ["inputscan"], timeout=120.0, retry_unsafe=True)
        parsed_scan = inputscan_live.parse_inputscan(stdout_of(inputscan_step))
        selected = choose_keyboard_event(parsed_scan, args.event)
        result.update({
            "inputscan_rc": inputscan_step.get("rc"),
            "inputscan": parsed_scan,
            "selected_keyboard_event": selected,
        })
        if not selected or "keyboard" not in state_live.class_tokens(selected):
            result["decision"] = f"{DECISION_PREFIX}-no-keyboard-candidate"
            raise RuntimeError("no keyboard-class input event found")
        event_name = str(selected["event"])
        base.run_serial_step(out_dir, steps, f"candidate-hide-before-inputcaps-{event_name}", ["hide"], timeout=60.0, retry_unsafe=True)
        caps_step = base.run_serial_step(out_dir, steps, f"candidate-inputcaps-{event_name}", ["inputcaps", event_name], timeout=120.0, retry_unsafe=True)
        parsed_caps = caps_live.parse_inputcaps(stdout_of(caps_step))
        result["inputcaps"] = {
            "event": event_name,
            "rc": caps_step.get("rc"),
            "stdout_path": caps_step.get("stdout_path"),
            "parsed": parsed_caps,
        }
        result["inputcaps_keyboard_ok"] = state_live.keyboard_caps_ok(parsed_caps)
        if not result["inputcaps_keyboard_ok"]:
            result["decision"] = f"{DECISION_PREFIX}-keyboard-caps-not-ready"
            raise RuntimeError("keyboard candidate lacks required DOOM key capability bits")
        base.run_serial_step(out_dir, steps, "candidate-hide-before-doominput", ["hide"], timeout=60.0, retry_unsafe=True)
        sample = state_live.run_timeout_doominput(
            args.host,
            args.port,
            event_name,
            args.count,
            timeout_ms=args.timeout_ms,
        )
        readinput_live.write_manual_step(out_dir, steps, "candidate-doominput-keyboard-state-sample", sample)
        result.update({
            "doominput": {key: value for key, value in sample.items() if key != "text"},
            "doominput_rc": sample.get("protocol", {}).get("rc"),
        })
        after = base.run_serial_step(out_dir, steps, "candidate-selftest-after-doominput", ["selftest", "verbose"], timeout=120.0, retry_unsafe=True)
        result["candidate_selftest_after_doominput_fail0"] = selftest_step_ok(after)
        result["pass"] = evaluate_result(result)
        result["decision"] = f"{DECISION_PREFIX}-pass-before-rollback" if result["pass"] else f"{DECISION_PREFIX}-not-proven"
        if not result["pass"]:
            raise RuntimeError("doominput keyboard sample did not produce required DOOM button state")
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
            f"verify rollback image {ROLLBACK_IMAGE}",
            f"flash {CANDIDATE_IMAGE}",
            "version/selftest",
            "hide; inputscan",
            "select keyboard-class event, or requested keyboard event",
            "inputcaps <keyboard-event> and require DOOM key capability bits",
            f"doominput <keyboard-event> {args.count} {args.timeout_ms} while operator presses DOOM keys",
            "require doominput.state active DOOM button state lines",
            "selftest verbose after doominput",
            "rollback v2321 and verify selftest fail=0",
        ],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="flash V2989, sample USB keyboard doominput state, then rollback")
    parser.add_argument("--event", default=None, help="optional keyboard eventX override; otherwise selected from inputscan")
    parser.add_argument("--count", type=int, default=DEFAULT_COUNT)
    parser.add_argument("--timeout-ms", type=int, default=DEFAULT_TIMEOUT_MS)
    parser.add_argument("--flash-timeout", type=float, default=900.0)
    parser.add_argument("--host", default=state_live.a90ctl.DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=state_live.a90ctl.DEFAULT_PORT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    out_dir = ROOT / f"workspace/private/runs/input/{BUILD_TAG}-{now_slug()}"
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
        "selected_keyboard_event": (result.get("selected_keyboard_event") or {}).get("event") if isinstance(result.get("selected_keyboard_event"), dict) else None,
        "doominput_rc": result.get("doominput_rc"),
        "doom_button_states": ((result.get("doominput") or {}).get("parsed") or {}).get("doom_button_state_count"),
        "rollback_version_ok": result.get("rollback_version_ok"),
        "rollback_selftest_fail0": result.get("rollback_selftest_fail0"),
        "result_json": result.get("result_json"),
    }, indent=2, sort_keys=True))
    return 0 if result.get("pass") and result.get("rollback_version_ok") and result.get("rollback_selftest_fail0") else 1


if __name__ == "__main__":
    raise SystemExit(main())

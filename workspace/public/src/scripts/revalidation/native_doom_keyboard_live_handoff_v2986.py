#!/usr/bin/env python3
"""V2986 live handoff for DOOM USB-keyboard input validation.

This runner flashes the V2985 DOOM keyboard-capability candidate, discovers a
keyboard-class evdev node via ``inputscan``, confirms DOOM-relevant key bits via
``inputcaps``, captures one native-bounded ``readinput`` sample, then rolls back
to the v2321 clean USB identity checkpoint. It only reads input state/events;
it does not inject input, grab devices, alter keymaps, or write sysfs state.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import native_inputcaps_touch_diag_live_handoff_v2984 as caps_live
import native_inputscan_live_handoff_v2978 as inputscan_live
import native_readinput_timeout_live_handoff_v2982 as readinput_live

base = inputscan_live.base
ROOT = inputscan_live.ROOT

RUN_ID = "V2986"
BUILD_TAG = "v2986-doom-keyboard-live"
DECISION_PREFIX = "v2986-doom-keyboard"
REPORT_PATH = ROOT / "docs/reports/NATIVE_INIT_V2986_DOOM_KEYBOARD_LIVE_HANDOFF_DRY_RUN_2026-06-20.md"

CANDIDATE_IMAGE = ROOT / "workspace/private/inputs/boot_images/boot_linux_v2985_doom_keyboard_caps.img"
CANDIDATE_VERSION = "0.10.63"
CANDIDATE_TAG = "v2985-doom-keyboard-caps"
CANDIDATE_SHA256 = "4ffdb9b6078e99b3c5f40db42c0c9ef9d01f7936006be33943a65d9965343e54"

ROLLBACK_IMAGE = inputscan_live.ROLLBACK_IMAGE
ROLLBACK_VERSION = inputscan_live.ROLLBACK_VERSION
ROLLBACK_SHA256 = inputscan_live.ROLLBACK_SHA256
FALLBACK_V2237 = inputscan_live.FALLBACK_V2237
FALLBACK_V2237_SHA256 = inputscan_live.FALLBACK_V2237_SHA256
FALLBACK_V48 = inputscan_live.FALLBACK_V48
SELFTEST_FAIL0_RE = inputscan_live.SELFTEST_FAIL0_RE

DEFAULT_COUNT = 24
DEFAULT_TIMEOUT_MS = 30000

EV_KEY = 0x0001
DOOM_KEY_CODES = {
    0x0001: "KEY_ESC",
    0x0011: "KEY_W",
    0x001e: "KEY_A",
    0x001f: "KEY_S",
    0x0020: "KEY_D",
    0x001c: "KEY_ENTER",
    0x0039: "KEY_SPACE",
    0x001d: "KEY_LEFTCTRL",
    0x0061: "KEY_RIGHTCTRL",
    0x002a: "KEY_LEFTSHIFT",
    0x0036: "KEY_RIGHTSHIFT",
    0x0067: "KEY_UP",
    0x006c: "KEY_DOWN",
    0x0069: "KEY_LEFT",
    0x006a: "KEY_RIGHT",
}
WASD_CAP_KEYS = ("key_w", "key_a", "key_s", "key_d")
ARROW_CAP_KEYS = ("key_up", "key_down", "key_left", "key_right")
ACTION_CAP_KEYS = ("key_enter", "key_space", "key_esc")


def now_slug() -> str:
    return datetime.now(timezone.utc).astimezone().strftime("%Y%m%d-%H%M%S")


def rel(path: Path) -> str:
    return inputscan_live.rel(path)


def stdout_of(step: dict[str, Any] | None) -> str:
    return inputscan_live.stdout_of(step)


def write_json(path: Path, payload: Any) -> None:
    inputscan_live.av_live.write_json(path, payload)


def file_state(path: Path, expected_sha: str | None = None) -> dict[str, Any]:
    return inputscan_live.file_state(path, expected_sha)


def selftest_step_ok(step: dict[str, Any]) -> bool:
    return bool(SELFTEST_FAIL0_RE.search(stdout_of(step))) or base.protocol_selftest_ok(step)


def flash_command(image: Path, expect_version: str, expect_sha: str, *, from_native: bool) -> list[str]:
    return inputscan_live.flash_command(image, expect_version, expect_sha, from_native=from_native)


def class_tokens(item: dict[str, str]) -> set[str]:
    return {part.strip() for part in str(item.get("class", "")).split(",") if part.strip()}


def has_all(parsed_caps: dict[str, Any], keys: tuple[str, ...]) -> bool:
    decoded = parsed_caps.get("decode", {}) if isinstance(parsed_caps.get("decode"), dict) else {}
    return all(decoded.get(key) == "1" for key in keys)


def keyboard_caps_ok(parsed_caps: dict[str, Any]) -> bool:
    return bool(
        parsed_caps.get("has_event_header")
        and parsed_caps.get("decode", {}).get("ev_key") == "1"
        and (has_all(parsed_caps, WASD_CAP_KEYS) or has_all(parsed_caps, ARROW_CAP_KEYS))
        and has_all(parsed_caps, ACTION_CAP_KEYS)
    )


def parse_keyboard_readinput(text: str) -> dict[str, Any]:
    base_parsed = readinput_live.parse_readinput(text)
    events = base_parsed.get("events", []) if isinstance(base_parsed.get("events"), list) else []
    key_events = [
        {
            **item,
            "name": DOOM_KEY_CODES.get(item.get("code"), f"KEY_0x{item.get('code', 0):04x}"),
        }
        for item in events
        if item.get("type") == EV_KEY
    ]
    doom_events = [item for item in key_events if item.get("code") in DOOM_KEY_CODES]
    pressed_events = [item for item in doom_events if item.get("value") != 0]
    parsed = dict(base_parsed)
    parsed.update({
        "keyboard_key_event_count": len(key_events),
        "doom_key_event_count": len(doom_events),
        "doom_key_press_count": len(pressed_events),
        "doom_key_events": doom_events,
        "has_doom_key_event": bool(doom_events),
    })
    return parsed


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
        "operator_prerequisite": "USB keyboard/OTG attached and keys pressed during readinput window",
        "hard_boundary": [
            "boot partition only via native_init_flash.py",
            "rollback to v2321 and verify selftest fail=0",
            "read-only inputscan/inputcaps plus read-only evdev sample",
            "no input injection, no EVIOCGRAB, no keymap changes, no sysfs writes",
            "no Wi-Fi/audio/video playback/PMIC/backlight/GPIO/regulator/GDSC",
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


def choose_keyboard_event(parsed_scan: dict[str, Any], requested: str | None) -> dict[str, str]:
    events = parsed_scan.get("events", []) if isinstance(parsed_scan.get("events"), list) else []
    if requested:
        return next((item for item in events if item.get("event") == requested), {})
    keyboard_events = parsed_scan.get("keyboard_events", [])
    if isinstance(keyboard_events, list) and keyboard_events:
        return keyboard_events[0]
    return {}


def evaluate_result(result: dict[str, Any]) -> bool:
    selected = result.get("selected_keyboard_event", {})
    caps = result.get("inputcaps", {}) if isinstance(result.get("inputcaps"), dict) else {}
    sample = result.get("readinput", {}) if isinstance(result.get("readinput"), dict) else {}
    parsed_sample = sample.get("parsed", {}) if isinstance(sample.get("parsed"), dict) else {}
    return bool(
        result.get("candidate_version_ok")
        and result.get("candidate_selftest_fail0")
        and result.get("inputscan_rc") == 0
        and selected
        and "keyboard" in class_tokens(selected)
        and caps.get("rc") == 0
        and keyboard_caps_ok(caps.get("parsed", {}))
        and result.get("readinput_rc") == 0
        and parsed_sample.get("has_doom_key_event")
        and result.get("candidate_selftest_after_readinput_fail0")
    )


def render_report(result: dict[str, Any]) -> str:
    live_executed = bool(result.get("live_executed"))
    preflight = result.get("preflight", {}) if isinstance(result.get("preflight"), dict) else {}
    inputscan = result.get("inputscan", {}) if isinstance(result.get("inputscan"), dict) else {}
    selected = result.get("selected_keyboard_event", {}) if isinstance(result.get("selected_keyboard_event"), dict) else {}
    caps = result.get("inputcaps", {}) if isinstance(result.get("inputcaps"), dict) else {}
    parsed_caps = caps.get("parsed", {}) if isinstance(caps.get("parsed"), dict) else {}
    sample = result.get("readinput", {}) if isinstance(result.get("readinput"), dict) else {}
    parsed_sample = sample.get("parsed", {}) if isinstance(sample.get("parsed"), dict) else {}
    keyboard_lines = []
    for item in inputscan.get("keyboard_events", []) if isinstance(inputscan.get("keyboard_events"), list) else []:
        keyboard_lines.append(f"- `{item.get('event')}` `{item.get('name')}` class=`{item.get('class')}`")
    if not keyboard_lines:
        keyboard_lines = ["- none captured in this run"]
    event_lines = []
    for item in parsed_sample.get("doom_key_events", [])[:12] if isinstance(parsed_sample.get("doom_key_events"), list) else []:
        event_lines.append(
            f"- index=`{item.get('index')}` key=`{item.get('name')}` "
            f"code=`0x{item.get('code', 0):04x}` value=`{item.get('value')}`"
        )
    if not event_lines:
        event_lines = ["- none captured"]

    def live_bool(value: Any) -> str:
        return str(int(bool(value))) if live_executed else "not-run"

    def live_value(value: Any) -> str:
        return str(value) if live_executed else "not-run"

    return "\n".join([
        "# Native Init V2986 DOOM Keyboard Live Handoff Dry Run",
        "",
        "## Summary",
        "",
        f"- Decision: `{result.get('decision')}`",
        f"- Result before rollback: `{int(bool(result.get('pass')))}`",
        "- Track: active Video playback / DOOM input prerequisite.",
        f"- Candidate: `A90 Linux init {CANDIDATE_VERSION} ({CANDIDATE_TAG})`",
        f"- Candidate image: `{rel(CANDIDATE_IMAGE)}`",
        f"- Candidate SHA256: `{CANDIDATE_SHA256}`",
        f"- Private run dir: `{result.get('out_dir')}`",
        f"- Live execution: `{int(bool(result.get('live_executed')))}`",
        "",
        "## Dry-Run Preflight",
        "",
        f"- Preflight ok: `{int(bool(result.get('preflight_ok') if 'preflight_ok' in result else (preflight_ok(preflight) if preflight else False)))}`",
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
        f"- Inputscan rc: `{live_value(result.get('inputscan_rc'))}` keyboard_candidates=`{live_value(inputscan.get('keyboard_candidates', 0))}`",
        f"- Selected event: `{selected.get('event', '-')}` name=`{selected.get('name', '-')}` class=`{selected.get('class', '-')}`",
        f"- Inputcaps rc: `{live_value(caps.get('rc'))}` doom_caps_ok=`{live_bool(keyboard_caps_ok(parsed_caps))}`",
        f"- `readinput` rc: `{live_value(result.get('readinput_rc'))}` timeout_ms=`{live_value(sample.get('timeout_ms'))}`",
        f"- Captured events: `{live_value(parsed_sample.get('event_count', 0))}` key_events=`{live_value(parsed_sample.get('keyboard_key_event_count', 0))}` doom_key_events=`{live_value(parsed_sample.get('doom_key_event_count', 0))}`",
        f"- Candidate post-sample selftest fail=0: `{live_bool(result.get('candidate_selftest_after_readinput_fail0'))}`",
        "",
        "## Keyboard Candidates",
        "",
        *keyboard_lines,
        "",
        "## Captured DOOM Key Events",
        "",
        *event_lines,
        "",
        "## Rollback Evidence",
        "",
        f"- Rollback attempted: `{int(bool(result.get('rollback_attempted')))}`",
        f"- Rollback step ok: `{int(bool(result.get('rollback_step_ok')))}`",
        f"- Rollback health: version_ok=`{int(bool(result.get('rollback_version_ok')))}` selftest_fail0=`{int(bool(result.get('rollback_selftest_fail0')))}`",
        "",
        "## Interpretation",
        "",
        "- V2986 stages the exact live handoff for the DOOM USB-keyboard fallback after V2984 showed touch capability/runtime-PM did not explain zero touch samples.",
        "- Pass requires a keyboard-class evdev node, DOOM-relevant key capability bits, a bounded native `readinput` sample containing a DOOM key event, and clean rollback health.",
        "- This dry run intentionally does not flash until a USB keyboard/OTG path is attached; current v2321 precheck observed only built-in input nodes (`event0` through `event8`).",
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
        if not selected or "keyboard" not in class_tokens(selected):
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
        if not keyboard_caps_ok(parsed_caps):
            result["decision"] = f"{DECISION_PREFIX}-caps-not-doom-ready"
            raise RuntimeError("keyboard candidate lacks required DOOM key capability bits")
        base.run_serial_step(out_dir, steps, "candidate-hide-before-readinput", ["hide"], timeout=60.0, retry_unsafe=True)
        sample = readinput_live.run_timeout_readinput(
            args.host,
            args.port,
            event_name,
            args.count,
            timeout_ms=args.timeout_ms,
        )
        sample["parsed"] = parse_keyboard_readinput(sample.get("text", ""))
        readinput_live.write_manual_step(out_dir, steps, "candidate-readinput-keyboard-sample", sample)
        result.update({
            "readinput": {key: value for key, value in sample.items() if key != "text"},
            "readinput_rc": sample.get("protocol", {}).get("rc"),
        })
        after = base.run_serial_step(out_dir, steps, "candidate-selftest-after-readinput", ["selftest", "verbose"], timeout=120.0, retry_unsafe=True)
        result["candidate_selftest_after_readinput_fail0"] = selftest_step_ok(after)
        result["pass"] = evaluate_result(result)
        result["decision"] = f"{DECISION_PREFIX}-key-sample-pass-before-rollback" if result["pass"] else f"{DECISION_PREFIX}-key-sample-not-proven"
        if not result["pass"]:
            raise RuntimeError("readinput keyboard sample did not produce DOOM-key evidence")
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
            "select first keyboard-class input event unless --event is supplied",
            "inputcaps <keyboard-event> and require DOOM key capability bits",
            f"readinput <keyboard-event> {args.count} {args.timeout_ms} with native timeout while operator presses keys",
            "selftest verbose after readinput",
            "rollback v2321 and verify selftest fail=0",
        ],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="flash V2985, sample USB keyboard input, then rollback to V2321")
    parser.add_argument("--event", default=None, help="optional keyboard eventX override; otherwise first keyboard candidate is used")
    parser.add_argument("--count", type=int, default=DEFAULT_COUNT)
    parser.add_argument("--timeout-ms", type=int, default=DEFAULT_TIMEOUT_MS)
    parser.add_argument("--flash-timeout", type=float, default=900.0)
    parser.add_argument("--host", default=readinput_live.a90ctl.DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=readinput_live.a90ctl.DEFAULT_PORT)
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
        payload = {
            "decision": f"{DECISION_PREFIX}-preflight-failed",
            "pass": False,
            "live_executed": False,
            "preflight": state,
            "out_dir": rel(out_dir),
        }
        write_json(out_dir / "result.json", payload)
        REPORT_PATH.write_text(render_report(payload), encoding="utf-8")
        print(json.dumps({"decision": payload["decision"], "pass": False, "out_dir": rel(out_dir)}, indent=2, sort_keys=True))
        return 1
    result = run_live(args, out_dir, state)
    print(json.dumps({
        "decision": result.get("decision"),
        "pass": bool(result.get("pass")),
        "out_dir": rel(out_dir),
        "selected_event": (result.get("selected_keyboard_event") or {}).get("event"),
        "inputscan_rc": result.get("inputscan_rc"),
        "inputcaps_rc": (result.get("inputcaps") or {}).get("rc"),
        "readinput_rc": result.get("readinput_rc"),
        "doom_key_events": (result.get("readinput") or {}).get("parsed", {}).get("doom_key_event_count"),
        "rollback_version_ok": result.get("rollback_version_ok"),
        "rollback_selftest_fail0": result.get("rollback_selftest_fail0"),
    }, indent=2, sort_keys=True))
    return 0 if (result.get("pass") and result.get("rollback_version_ok") and result.get("rollback_selftest_fail0")) else 1


if __name__ == "__main__":
    raise SystemExit(main())

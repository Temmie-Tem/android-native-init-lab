#!/usr/bin/env python3
"""V2988 live handoff for decoded DOOM/touch readinput validation.

This runner targets the V2987 readinput decode candidate. It can validate either
the built-in touch nodes or a USB-keyboard fallback, but only reads input
inventory/capabilities and bounded evdev samples. It does not inject events,
grab evdev nodes, alter keymaps, or write touch/sysfs configuration.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import native_doom_keyboard_live_handoff_v2986 as keyboard_live
import native_inputcaps_touch_diag_live_handoff_v2984 as caps_live
import native_inputscan_live_handoff_v2978 as inputscan_live
import native_readinput_timeout_live_handoff_v2982 as readinput_live

base = inputscan_live.base
ROOT = inputscan_live.ROOT

RUN_ID = "V2988"
BUILD_TAG = "v2988-readinput-doom-decode-live"
DECISION_PREFIX = "v2988-readinput-doom-decode"
REPORT_PATH = ROOT / "docs/reports/NATIVE_INIT_V2988_READINPUT_DOOM_DECODE_LIVE_HANDOFF_DRY_RUN_2026-06-20.md"

CANDIDATE_IMAGE = ROOT / "workspace/private/inputs/boot_images/boot_linux_v2987_readinput_doom_decode.img"
CANDIDATE_VERSION = "0.10.64"
CANDIDATE_TAG = "v2987-readinput-doom-decode"
CANDIDATE_SHA256 = "fc5d680be0b6575ea4650a4e84a2ee7f0620cc02693e77b5f4453f44f9ffad21"

ROLLBACK_IMAGE = inputscan_live.ROLLBACK_IMAGE
ROLLBACK_VERSION = inputscan_live.ROLLBACK_VERSION
ROLLBACK_SHA256 = inputscan_live.ROLLBACK_SHA256
FALLBACK_V2237 = inputscan_live.FALLBACK_V2237
FALLBACK_V2237_SHA256 = inputscan_live.FALLBACK_V2237_SHA256
FALLBACK_V48 = inputscan_live.FALLBACK_V48
SELFTEST_FAIL0_RE = inputscan_live.SELFTEST_FAIL0_RE

DEFAULT_COUNT = 32
DEFAULT_TIMEOUT_MS = 45000
VALID_MODES = ("auto", "touch", "keyboard")
TOUCH_PREFERRED_EVENTS = ("event6", "event8")
TOUCH_DECODE_ROLES = {"touch_x", "touch_y", "touch_tracking", "touch_contact", "touch_slot", "touch_pressure", "touch_major"}
DOOM_DECODE_PREFIX = "doom_"

DECODE_RE = re.compile(
    r"event\.decode\s+(?P<index>\d+):\s+type=(?P<type>\S+)\s+code=(?P<code>\S+)\s+role=(?P<role>\S+)\s+value=(?P<value>-?\d+)"
)


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


def touch_caps_ok(parsed_caps: dict[str, Any]) -> bool:
    decoded = parsed_caps.get("decode", {}) if isinstance(parsed_caps.get("decode"), dict) else {}
    return bool(
        parsed_caps.get("has_event_header")
        and decoded.get("ev_abs") == "1"
        and decoded.get("btn_touch") == "1"
        and decoded.get("mt_x") == "1"
        and decoded.get("mt_y") == "1"
        and decoded.get("mt_tracking_id") == "1"
    )


def keyboard_caps_ok(parsed_caps: dict[str, Any]) -> bool:
    return keyboard_live.keyboard_caps_ok(parsed_caps)


def parse_decoded_readinput(text: str) -> dict[str, Any]:
    parsed = readinput_live.parse_readinput(text)
    decoded_events: list[dict[str, Any]] = []
    for match in DECODE_RE.finditer(text):
        decoded_events.append({
            "index": int(match.group("index")),
            "type": match.group("type"),
            "code": match.group("code"),
            "role": match.group("role"),
            "value": int(match.group("value")),
        })
    touch_events = [item for item in decoded_events if item.get("role") in TOUCH_DECODE_ROLES]
    doom_events = [item for item in decoded_events if str(item.get("role", "")).startswith(DOOM_DECODE_PREFIX)]
    doom_pressed = [item for item in doom_events if item.get("value") != 0]
    parsed.update({
        "decoded_events": decoded_events,
        "decoded_event_count": len(decoded_events),
        "touch_decoded_event_count": len(touch_events),
        "doom_decoded_event_count": len(doom_events),
        "doom_decoded_press_count": len(doom_pressed),
        "touch_roles": sorted({str(item.get("role")) for item in touch_events}),
        "doom_roles": sorted({str(item.get("role")) for item in doom_events}),
        "has_touch_decoded_event": bool(touch_events),
        "has_doom_decoded_event": bool(doom_events),
        "has_doom_decoded_press": bool(doom_pressed),
    })
    return parsed


def choose_event(parsed_scan: dict[str, Any], requested: str | None, mode: str) -> tuple[str, dict[str, str]]:
    events = parsed_scan.get("events", []) if isinstance(parsed_scan.get("events"), list) else []
    if requested:
        item = next((entry for entry in events if entry.get("event") == requested), {})
        if not item:
            return mode, {}
        tokens = class_tokens(item)
        if mode == "auto":
            if "keyboard" in tokens:
                return "keyboard", item
            if "touch" in tokens:
                return "touch", item
        return mode, item

    if mode in ("auto", "keyboard"):
        keyboard_events = parsed_scan.get("keyboard_events", [])
        if isinstance(keyboard_events, list) and keyboard_events:
            return "keyboard", keyboard_events[0]
        if mode == "keyboard":
            return "keyboard", {}

    if mode in ("auto", "touch"):
        touch_events = parsed_scan.get("touch_events", [])
        touch_list = touch_events if isinstance(touch_events, list) else []
        for preferred in TOUCH_PREFERRED_EVENTS:
            item = next((entry for entry in touch_list if entry.get("event") == preferred), {})
            if item:
                return "touch", item
        if touch_list:
            return "touch", touch_list[0]
        return "touch", {}

    return mode, {}


def evaluate_result(result: dict[str, Any]) -> bool:
    mode = result.get("selected_mode")
    selected = result.get("selected_event", {})
    caps = result.get("inputcaps", {}) if isinstance(result.get("inputcaps"), dict) else {}
    sample = result.get("readinput", {}) if isinstance(result.get("readinput"), dict) else {}
    parsed_sample = sample.get("parsed", {}) if isinstance(sample.get("parsed"), dict) else {}
    common_ok = bool(
        result.get("candidate_version_ok")
        and result.get("candidate_selftest_fail0")
        and result.get("inputscan_rc") == 0
        and selected
        and caps.get("rc") == 0
        and result.get("readinput_rc") == 0
        and result.get("candidate_selftest_after_readinput_fail0")
    )
    if not common_ok:
        return False
    if mode == "keyboard":
        return bool(
            "keyboard" in class_tokens(selected)
            and keyboard_caps_ok(caps.get("parsed", {}))
            and parsed_sample.get("has_doom_decoded_press")
        )
    if mode == "touch":
        return bool(
            "touch" in class_tokens(selected)
            and touch_caps_ok(caps.get("parsed", {}))
            and parsed_sample.get("has_touch_decoded_event")
        )
    return False


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
        "requested_mode": args.mode,
        "requested_event": args.event,
        "count": args.count,
        "timeout_ms": args.timeout_ms,
        "operator_prerequisite": (
            "touch mode requires finger movement during the readinput window; "
            "keyboard mode requires USB keyboard/OTG attached and keys pressed"
        ),
        "hard_boundary": [
            "boot partition only via native_init_flash.py",
            "rollback to v2321 and verify selftest fail=0",
            "read-only inputscan/inputcaps plus read-only evdev sample",
            "no input injection, no EVIOCGRAB, no keymap changes, no sysfs writes",
            "no PMIC/backlight/GPIO/regulator/GDSC and no forbidden partition path",
        ],
    }


def preflight_ok(state: dict[str, Any]) -> bool:
    return bool(
        state["candidate"].get("sha256_ok")
        and state["rollback"].get("sha256_ok")
        and state["fallback_v2237"].get("sha256_ok")
        and state["fallback_v48"].get("exists")
        and state["flash_helper"].get("exists")
        and state.get("requested_mode") in VALID_MODES
        and state.get("timeout_ms", 0) > 0
        and state.get("count", 0) > 0
    )


def mode_caps_ok(mode: str, parsed_caps: dict[str, Any]) -> bool:
    return touch_caps_ok(parsed_caps) if mode == "touch" else keyboard_caps_ok(parsed_caps)


def render_report(result: dict[str, Any]) -> str:
    live_executed = bool(result.get("live_executed"))
    preflight = result.get("preflight", {}) if isinstance(result.get("preflight"), dict) else {}
    inputscan = result.get("inputscan", {}) if isinstance(result.get("inputscan"), dict) else {}
    selected = result.get("selected_event", {}) if isinstance(result.get("selected_event"), dict) else {}
    caps = result.get("inputcaps", {}) if isinstance(result.get("inputcaps"), dict) else {}
    parsed_caps = caps.get("parsed", {}) if isinstance(caps.get("parsed"), dict) else {}
    sample = result.get("readinput", {}) if isinstance(result.get("readinput"), dict) else {}
    parsed_sample = sample.get("parsed", {}) if isinstance(sample.get("parsed"), dict) else {}

    candidate_lines = []
    for item in inputscan.get("keyboard_events", []) if isinstance(inputscan.get("keyboard_events"), list) else []:
        candidate_lines.append(f"- keyboard `{item.get('event')}` `{item.get('name')}` class=`{item.get('class')}`")
    for item in inputscan.get("touch_events", []) if isinstance(inputscan.get("touch_events"), list) else []:
        candidate_lines.append(f"- touch `{item.get('event')}` `{item.get('name')}` class=`{item.get('class')}`")
    if not candidate_lines:
        candidate_lines = ["- none captured in this run"]

    decoded_lines = []
    for item in parsed_sample.get("decoded_events", [])[:12] if isinstance(parsed_sample.get("decoded_events"), list) else []:
        decoded_lines.append(
            f"- index=`{item.get('index')}` type=`{item.get('type')}` code=`{item.get('code')}` "
            f"role=`{item.get('role')}` value=`{item.get('value')}`"
        )
    if not decoded_lines:
        decoded_lines = ["- none captured"]

    def live_bool(value: Any) -> str:
        return str(int(bool(value))) if live_executed else "not-run"

    def live_value(value: Any) -> str:
        return str(value) if live_executed else "not-run"

    return "\n".join([
        "# Native Init V2988 Readinput DOOM Decode Live Handoff Dry Run",
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
        f"- Live execution: `{int(live_executed)}`",
        f"- Requested mode: `{preflight.get('requested_mode', '-')}` selected_mode=`{result.get('selected_mode', '-')}`",
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
        f"- Inputscan rc: `{live_value(result.get('inputscan_rc'))}` keyboard_candidates=`{live_value(inputscan.get('keyboard_candidates'))}` touch_candidates=`{live_value(inputscan.get('touch_candidates'))}`",
        f"- Selected event: `{selected.get('event', '-')}` name=`{selected.get('name', '-')}` class=`{selected.get('class', '-')}`",
        f"- Inputcaps rc: `{live_value(caps.get('rc'))}` caps_ok=`{live_bool(result.get('inputcaps_mode_ok'))}`",
        f"- `readinput` rc: `{live_value(result.get('readinput_rc'))}` timeout_ms=`{live_value(sample.get('timeout_ms'))}`",
        f"- Decoded events: `{live_value(parsed_sample.get('decoded_event_count'))}` touch_decoded=`{live_value(parsed_sample.get('touch_decoded_event_count'))}` doom_decoded=`{live_value(parsed_sample.get('doom_decoded_event_count'))}` doom_presses=`{live_value(parsed_sample.get('doom_decoded_press_count'))}`",
        f"- Candidate post-sample selftest fail=0: `{live_bool(result.get('candidate_selftest_after_readinput_fail0'))}`",
        "",
        "## Input Candidates",
        "",
        *candidate_lines,
        "",
        "## Captured Decoded Events",
        "",
        *decoded_lines,
        "",
        "## Rollback Evidence",
        "",
        f"- Rollback attempted: `{int(bool(result.get('rollback_attempted')))}`",
        f"- Rollback step ok: `{int(bool(result.get('rollback_step_ok')))}`",
        f"- Rollback health: version_ok=`{int(bool(result.get('rollback_version_ok')))}` selftest_fail0=`{int(bool(result.get('rollback_selftest_fail0')))}`",
        "",
        "## Interpretation",
        "",
        "- V2988 stages the live handoff for the V2987 decoded readinput candidate, covering both proven MT-capable touch nodes and the USB-keyboard fallback.",
        "- Pass requires the decoded `event.decode` line to carry either touch roles (`touch_x`/`touch_y`/`touch_tracking`/`touch_contact`) or a pressed DOOM keyboard role (`doom_*`), plus clean rollback health.",
        "- This dry run intentionally does not flash because meaningful validation still needs operator finger motion or an attached USB keyboard during the bounded read window.",
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
        selected_mode, selected = choose_event(parsed_scan, args.event, args.mode)
        result.update({
            "selected_mode": selected_mode,
            "inputscan_rc": inputscan_step.get("rc"),
            "inputscan": parsed_scan,
            "selected_event": selected,
        })
        if not selected or selected_mode not in ("touch", "keyboard") or selected_mode not in class_tokens(selected):
            result["decision"] = f"{DECISION_PREFIX}-no-{selected_mode}-candidate"
            raise RuntimeError(f"no {selected_mode}-class input event found")
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
        result["inputcaps_mode_ok"] = mode_caps_ok(selected_mode, parsed_caps)
        if not result["inputcaps_mode_ok"]:
            result["decision"] = f"{DECISION_PREFIX}-{selected_mode}-caps-not-ready"
            raise RuntimeError(f"{selected_mode} candidate lacks required capability bits")
        base.run_serial_step(out_dir, steps, "candidate-hide-before-readinput", ["hide"], timeout=60.0, retry_unsafe=True)
        sample = readinput_live.run_timeout_readinput(
            args.host,
            args.port,
            event_name,
            args.count,
            timeout_ms=args.timeout_ms,
        )
        sample["parsed"] = parse_decoded_readinput(sample.get("text", ""))
        readinput_live.write_manual_step(out_dir, steps, f"candidate-readinput-{selected_mode}-decode-sample", sample)
        result.update({
            "readinput": {key: value for key, value in sample.items() if key != "text"},
            "readinput_rc": sample.get("protocol", {}).get("rc"),
        })
        after = base.run_serial_step(out_dir, steps, "candidate-selftest-after-readinput", ["selftest", "verbose"], timeout=120.0, retry_unsafe=True)
        result["candidate_selftest_after_readinput_fail0"] = selftest_step_ok(after)
        result["pass"] = evaluate_result(result)
        result["decision"] = f"{DECISION_PREFIX}-{selected_mode}-decode-pass-before-rollback" if result["pass"] else f"{DECISION_PREFIX}-{selected_mode}-decode-not-proven"
        if not result["pass"]:
            raise RuntimeError(f"readinput {selected_mode} sample did not produce decoded role evidence")
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
            "mode auto: select first keyboard candidate, otherwise prefer touch event6/event8",
            "inputcaps <event> and require mode-specific capability bits",
            f"readinput <event> {args.count} {args.timeout_ms} with native timeout while operator provides real input",
            "require decoded event roles from event.decode lines",
            "selftest verbose after readinput",
            "rollback v2321 and verify selftest fail=0",
        ],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="flash V2987, sample decoded input, then rollback to V2321")
    parser.add_argument("--mode", choices=VALID_MODES, default="auto")
    parser.add_argument("--event", default=None, help="optional eventX override; otherwise selected from inputscan for the chosen mode")
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
        "selected_mode": result.get("selected_mode"),
        "selected_event": (result.get("selected_event") or {}).get("event") if isinstance(result.get("selected_event"), dict) else None,
        "rollback_version_ok": result.get("rollback_version_ok"),
        "rollback_selftest_fail0": result.get("rollback_selftest_fail0"),
        "result_json": result.get("result_json"),
    }, indent=2, sort_keys=True))
    return 0 if result.get("pass") and result.get("rollback_version_ok") and result.get("rollback_selftest_fail0") else 1


if __name__ == "__main__":
    raise SystemExit(main())

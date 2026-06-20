#!/usr/bin/env python3
"""V2979 bounded live handoff for a human touch sample via readinput.

This runner reuses the V2977 inputscan candidate image. It flashes the candidate,
revalidates the selected event with ``inputscan <eventX>``, runs one bounded
``readinput <eventX> <count>`` window, sends ``q`` to cancel if no event arrives,
and always rolls back to the v2321 clean USB identity checkpoint. The command
only reads evdev events; it does not inject input or alter keymaps.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import socket
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import a90ctl
from a90_serial_lock import SerialBridgeLock
import native_inputscan_live_handoff_v2978 as inputscan_live

base = inputscan_live.base
ROOT = inputscan_live.ROOT

RUN_ID = "V2979"
BUILD_TAG = "v2979-readinput-touch-sample"
DECISION_PREFIX = "v2979-readinput"
REPORT_PATH = ROOT / "docs/reports/NATIVE_INIT_V2979_READINPUT_TOUCH_SAMPLE_2026-06-20.md"

CANDIDATE_IMAGE = inputscan_live.CANDIDATE_IMAGE
CANDIDATE_VERSION = inputscan_live.CANDIDATE_VERSION
CANDIDATE_TAG = inputscan_live.CANDIDATE_TAG
CANDIDATE_SHA256 = inputscan_live.CANDIDATE_SHA256
ROLLBACK_IMAGE = inputscan_live.ROLLBACK_IMAGE
ROLLBACK_VERSION = inputscan_live.ROLLBACK_VERSION
ROLLBACK_SHA256 = inputscan_live.ROLLBACK_SHA256
FALLBACK_V2237 = inputscan_live.FALLBACK_V2237
FALLBACK_V2237_SHA256 = inputscan_live.FALLBACK_V2237_SHA256
FALLBACK_V48 = inputscan_live.FALLBACK_V48

DEFAULT_EVENT = "event6"
DEFAULT_COUNT = 16
SELFTEST_FAIL0_RE = inputscan_live.SELFTEST_FAIL0_RE
READ_EVENT_RE = re.compile(
    r"^event (?P<index>\d+): type=0x(?P<type>[0-9a-fA-F]{4}) "
    r"code=0x(?P<code>[0-9a-fA-F]{4}) value=(?P<value>-?\d+)$",
    re.MULTILINE,
)

EV_SYN = 0x0000
EV_KEY = 0x0001
EV_ABS = 0x0003
BTN_TOUCH = 0x014A
ABS_X = 0x0000
ABS_Y = 0x0001
ABS_MT_POSITION_X = 0x0035
ABS_MT_POSITION_Y = 0x0036
ABS_MT_TRACKING_ID = 0x0039
TOUCH_ABS_CODES = {ABS_X, ABS_Y, ABS_MT_POSITION_X, ABS_MT_POSITION_Y, ABS_MT_TRACKING_ID}


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
        "event": args.event,
        "count": args.count,
        "sample_timeout_sec": args.sample_timeout,
        "hard_boundary": [
            "boot partition only via native_init_flash.py",
            "rollback to v2321 and verify selftest fail=0",
            "readinput evdev read-only sample only",
            "send q cancel if the sample window times out",
            "no input injection, no keymap changes, no touchscreen configuration writes",
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
    )


def parse_readinput(text: str) -> dict[str, Any]:
    events: list[dict[str, int]] = []
    for match in READ_EVENT_RE.finditer(text):
        events.append({
            "index": int(match.group("index"), 10),
            "type": int(match.group("type"), 16),
            "code": int(match.group("code"), 16),
            "value": int(match.group("value"), 10),
        })
    abs_events = [item for item in events if item["type"] == EV_ABS]
    key_events = [item for item in events if item["type"] == EV_KEY]
    syn_events = [item for item in events if item["type"] == EV_SYN]
    touch_abs_events = [item for item in abs_events if item["code"] in TOUCH_ABS_CODES]
    btn_touch_events = [item for item in key_events if item["code"] == BTN_TOUCH]
    return {
        "events": events,
        "event_count": len(events),
        "abs_event_count": len(abs_events),
        "key_event_count": len(key_events),
        "syn_event_count": len(syn_events),
        "touch_abs_event_count": len(touch_abs_events),
        "btn_touch_event_count": len(btn_touch_events),
        "has_touch_signal": bool(touch_abs_events or btn_touch_events),
    }


def has_prompt_after_last_end(data: bytearray) -> bool:
    end_index = data.rfind(b"A90P1 END ")
    if end_index < 0:
        return False
    tail = data[end_index:]
    return b"\na90:/#" in tail or b"\ra90:/#" in tail


def run_cancellable_readinput(host: str,
                              port: int,
                              event: str,
                              count: int,
                              *,
                              sample_timeout: float,
                              cancel_timeout: float,
                              connect_timeout: float = 3.0) -> dict[str, Any]:
    command = ["readinput", event, str(count)]
    line = a90ctl.encode_cmdv1_line(command)
    data = bytearray()
    cancel_sent = False
    started = time.monotonic()
    cancel_deadline: float | None = None
    with SerialBridgeLock(timeout_sec=sample_timeout + cancel_timeout + connect_timeout, purpose="v2979-readinput"):
        with socket.create_connection((host, port), timeout=connect_timeout) as sock:
            sock.settimeout(0.25)
            sock.sendall(("\n" + line + "\n").encode("utf-8"))
            while True:
                now = time.monotonic()
                if b"A90P1 END " in data and has_prompt_after_last_end(data):
                    break
                if not cancel_sent and now - started >= sample_timeout:
                    sock.sendall(b"q\n")
                    cancel_sent = True
                    cancel_deadline = now + cancel_timeout
                if cancel_sent and cancel_deadline is not None and now >= cancel_deadline:
                    break
                try:
                    chunk = sock.recv(8192)
                except socket.timeout:
                    continue
                if not chunk:
                    break
                data.extend(chunk)
    text = data.decode("utf-8", errors="replace")
    protocol: dict[str, Any] = {"begin": {}, "end": {}, "rc": None, "status": "missing"}
    protocol_error = None
    try:
        parsed = a90ctl.parse_protocol_output(text)
        protocol = {"begin": parsed.begin, "end": parsed.end, "rc": parsed.rc, "status": parsed.status}
    except Exception as exc:  # noqa: BLE001 - record partial output for report
        protocol_error = f"{type(exc).__name__}: {exc}"
    return {
        "command": command,
        "text": text,
        "cancel_sent": cancel_sent,
        "duration_sec": round(time.monotonic() - started, 3),
        "protocol": protocol,
        "protocol_error": protocol_error,
        "parsed": parse_readinput(text),
    }


def write_manual_step(out_dir: Path, steps: list[dict[str, Any]], name: str, payload: dict[str, Any]) -> dict[str, Any]:
    index = len(steps)
    prefix = f"{index:02d}_{name}"
    stdout_path = out_dir / f"{prefix}.txt"
    json_path = out_dir / f"{prefix}.json"
    stdout_path.write_text(str(payload.get("text", "")), encoding="utf-8")
    record = {key: value for key, value in payload.items() if key != "text"}
    record.update({
        "name": name,
        "stdout_path": rel(stdout_path),
        "json_path": rel(json_path),
        "rc": payload.get("protocol", {}).get("rc"),
        "ok": payload.get("protocol", {}).get("rc") == 0,
    })
    write_json(json_path, record)
    steps.append(record)
    return record


def evaluate_result(result: dict[str, Any]) -> bool:
    sample = result.get("readinput", {}) if isinstance(result.get("readinput"), dict) else {}
    parsed = sample.get("parsed", {}) if isinstance(sample.get("parsed"), dict) else {}
    inputscan = result.get("inputscan", {}) if isinstance(result.get("inputscan"), dict) else {}
    return bool(
        result.get("candidate_version_ok")
        and result.get("candidate_selftest_fail0")
        and result.get("inputscan_event_is_touch")
        and result.get("readinput_rc") == 0
        and parsed.get("event_count", 0) > 0
        and parsed.get("has_touch_signal")
        and result.get("candidate_selftest_after_readinput_fail0")
        and inputscan.get("summary_found")
    )


def render_report(result: dict[str, Any]) -> str:
    sample = result.get("readinput", {}) if isinstance(result.get("readinput"), dict) else {}
    parsed = sample.get("parsed", {}) if isinstance(sample.get("parsed"), dict) else {}
    inputscan = result.get("inputscan", {}) if isinstance(result.get("inputscan"), dict) else {}
    event_lines = []
    for item in parsed.get("events", [])[:12] if isinstance(parsed.get("events"), list) else []:
        event_lines.append(
            f"- index=`{item.get('index')}` type=`0x{item.get('type', 0):04x}` "
            f"code=`0x{item.get('code', 0):04x}` value=`{item.get('value')}`"
        )
    if not event_lines:
        event_lines = ["- none captured"]
    return "\n".join([
        "# Native Init V2979 Readinput Touch Sample Handoff",
        "",
        "## Summary",
        "",
        f"- Decision: `{result.get('decision')}`",
        f"- Result before rollback: `{int(bool(result.get('pass')))}`",
        "- Track: Video playback / DOOM input prerequisite.",
        f"- Candidate reused: `A90 Linux init {CANDIDATE_VERSION} ({CANDIDATE_TAG})`",
        f"- Candidate SHA256: `{CANDIDATE_SHA256}`",
        f"- Event under test: `{result.get('event')}` count=`{result.get('count')}`",
        f"- Private run dir: `{result.get('out_dir')}`",
        "",
        "## Evidence",
        "",
        f"- Candidate version ok: `{int(bool(result.get('candidate_version_ok')))}`",
        f"- Candidate selftest fail=0: `{int(bool(result.get('candidate_selftest_fail0')))}`",
        f"- `inputscan <event>` rc: `{result.get('inputscan_rc')}` touch_class=`{int(bool(result.get('inputscan_event_is_touch')))}`",
        f"- `readinput` rc: `{result.get('readinput_rc')}` cancel_sent=`{int(bool(sample.get('cancel_sent')))}`",
        f"- Read events: `{parsed.get('event_count', 0)}` abs=`{parsed.get('abs_event_count', 0)}` key=`{parsed.get('key_event_count', 0)}` syn=`{parsed.get('syn_event_count', 0)}`",
        f"- Touch signal: `{int(bool(parsed.get('has_touch_signal')))}` touch_abs=`{parsed.get('touch_abs_event_count', 0)}` btn_touch=`{parsed.get('btn_touch_event_count', 0)}`",
        f"- Candidate post-sample selftest fail=0: `{int(bool(result.get('candidate_selftest_after_readinput_fail0')))}`",
        "",
        "## Captured Event Sample",
        "",
        *event_lines,
        "",
        "## Inputscan Recheck",
        "",
        f"- Summary found: `{int(bool(inputscan.get('summary_found')))}` events=`{inputscan.get('event_count', 0)}` touch_candidates=`{inputscan.get('touch_candidates', 0)}`",
        "",
        "## Rollback Evidence",
        "",
        f"- Rollback attempted: `{int(bool(result.get('rollback_attempted')))}`",
        f"- Rollback step ok: `{int(bool(result.get('rollback_step_ok')))}`",
        f"- Rollback health: version_ok=`{int(bool(result.get('rollback_version_ok')))}` selftest_fail0=`{int(bool(result.get('rollback_selftest_fail0')))}`",
        "",
        "## Interpretation",
        "",
        "- This unit is the first bounded bridge between static input inventory and an actual evdev sample for the DOOM prerequisite.",
        "- A pass proves the selected touch event emits EV_ABS/BTN_TOUCH-class data through native init without input injection or configuration writes.",
        "- If the sample window times out, the runner sends `q` and records a cancelled run rather than leaving a blocking command active.",
        "",
        "## Safety",
        "",
        "- Only the boot partition is flashed, through `native_init_flash.py`; rollback target is `v2321`.",
        "- The live path only opens and reads the selected `/dev/input/event*` node through `readinput`; no input injection, keymap writes, Wi-Fi, audio/video playback, PMIC, backlight, GPIO, regulator, GDSC, or forbidden partition path is touched.",
        "- Raw command output stays private under `workspace/private/runs/`; this report includes only event metadata.",
    ]) + "\n"


def run_live(args: argparse.Namespace, out_dir: Path, state: dict[str, Any]) -> dict[str, Any]:
    steps: list[dict[str, Any]] = []
    candidate_flash_attempted = False
    candidate_flash_ok = False
    result: dict[str, Any] = {
        "decision": f"{DECISION_PREFIX}-live-started",
        "pass": False,
        "out_dir": rel(out_dir),
        "preflight": state,
        "steps": steps,
        "event": args.event,
        "count": args.count,
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
        inputscan_step = base.run_serial_step(out_dir, steps, "candidate-inputscan-selected-event", ["inputscan", args.event], timeout=120.0, retry_unsafe=True)
        inputscan = inputscan_live.parse_inputscan(stdout_of(inputscan_step))
        selected = inputscan["events"][0] if inputscan.get("events") else {}
        result.update({
            "candidate_version_ok": f"A90 Linux init {CANDIDATE_VERSION} ({CANDIDATE_TAG})" in stdout_of(version),
            "candidate_selftest_fail0": selftest_step_ok(selftest),
            "inputscan_rc": inputscan_step.get("rc"),
            "inputscan": inputscan,
            "inputscan_event_is_touch": selected.get("class") == "touch",
        })
        sample = run_cancellable_readinput(
            args.host,
            args.port,
            args.event,
            args.count,
            sample_timeout=args.sample_timeout,
            cancel_timeout=args.cancel_timeout,
        )
        write_manual_step(out_dir, steps, "candidate-readinput-touch-sample", sample)
        result.update({
            "readinput": {key: value for key, value in sample.items() if key != "text"},
            "readinput_rc": sample.get("protocol", {}).get("rc"),
        })
        after = base.run_serial_step(out_dir, steps, "candidate-selftest-after-readinput", ["selftest", "verbose"], timeout=120.0, retry_unsafe=True)
        result["candidate_selftest_after_readinput_fail0"] = selftest_step_ok(after)
        result["pass"] = evaluate_result(result)
        result["decision"] = f"{DECISION_PREFIX}-touch-sample-pass-before-rollback" if result["pass"] else f"{DECISION_PREFIX}-touch-sample-not-proven"
        if not result["pass"]:
            raise RuntimeError("readinput touch sample did not produce touch-class evidence")
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
            "version/selftest/inputscan <event>",
            f"readinput {args.event} {args.count} with q-cancel after {args.sample_timeout}s",
            "selftest verbose after readinput",
            "rollback v2321 and verify selftest fail=0",
        ],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="flash V2977, sample readinput, then rollback to V2321")
    parser.add_argument("--event", default=DEFAULT_EVENT)
    parser.add_argument("--count", type=int, default=DEFAULT_COUNT)
    parser.add_argument("--sample-timeout", type=float, default=30.0)
    parser.add_argument("--cancel-timeout", type=float, default=8.0)
    parser.add_argument("--flash-timeout", type=float, default=900.0)
    parser.add_argument("--host", default=a90ctl.DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=a90ctl.DEFAULT_PORT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    out_dir = ROOT / f"workspace/private/runs/input/{BUILD_TAG}-{now_slug()}"
    out_dir.mkdir(parents=True, exist_ok=True)
    state = preflight_state(args)
    if not args.live:
        payload = dry_run_payload(args, state)
        write_json(out_dir / "dry_run.json", payload)
        REPORT_PATH.write_text(render_report({
            "decision": payload["decision"],
            "pass": False,
            "out_dir": rel(out_dir),
            "event": args.event,
            "count": args.count,
            "rollback_attempted": False,
        }), encoding="utf-8")
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0 if payload["ok"] else 1
    if not preflight_ok(state):
        payload = {"decision": f"{DECISION_PREFIX}-preflight-failed", "pass": False, "preflight": state, "out_dir": rel(out_dir)}
        write_json(out_dir / "result.json", payload)
        REPORT_PATH.write_text(render_report(payload), encoding="utf-8")
        print(json.dumps({"decision": payload["decision"], "pass": False, "out_dir": rel(out_dir)}, indent=2, sort_keys=True))
        return 1
    result = run_live(args, out_dir, state)
    print(json.dumps({
        "decision": result.get("decision"),
        "pass": bool(result.get("pass")),
        "out_dir": rel(out_dir),
        "event": result.get("event"),
        "readinput_rc": result.get("readinput_rc"),
        "read_events": (result.get("readinput") or {}).get("parsed", {}).get("event_count"),
        "touch_signal": (result.get("readinput") or {}).get("parsed", {}).get("has_touch_signal"),
        "rollback_version_ok": result.get("rollback_version_ok"),
        "rollback_selftest_fail0": result.get("rollback_selftest_fail0"),
    }, indent=2, sort_keys=True))
    return 0 if (result.get("pass") and result.get("rollback_version_ok") and result.get("rollback_selftest_fail0")) else 1


if __name__ == "__main__":
    raise SystemExit(main())

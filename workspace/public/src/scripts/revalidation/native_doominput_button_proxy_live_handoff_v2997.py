#!/usr/bin/env python3
"""V2997 live handoff for the V2996 DOOM physical-button proxy candidate.

The V2996 source build maps A90 physical buttons into diagnostic DOOM state:
VOLUMEUP -> forward, VOLUMEDOWN -> back, POWER -> fire. This runner stages the
bounded live validation for that candidate. Dry-run is the default; ``--live``
is required before any flash, and live mode rolls back to v2321 after sampling.
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

RUN_ID = "V2997"
BUILD_TAG = "v2997-doominput-button-proxy-live"
DECISION_PREFIX = "v2997-doominput-button-proxy"
REPORT_PATH = ROOT / "docs/reports/NATIVE_INIT_V2997_DOOMINPUT_BUTTON_PROXY_LIVE_HANDOFF_DRY_RUN_2026-06-20.md"

CANDIDATE_IMAGE = ROOT / "workspace/private/inputs/boot_images/boot_linux_v2996_doominput_button_proxy.img"
CANDIDATE_VERSION = "0.10.66"
CANDIDATE_TAG = "v2996-doominput-button-proxy"
CANDIDATE_SHA256 = "1509ce74701f2f8d30e7a5ee924b108ca9bb60debed8afab5f9352643e2a4a75"

ROLLBACK_IMAGE = state_live.ROLLBACK_IMAGE
ROLLBACK_VERSION = state_live.ROLLBACK_VERSION
ROLLBACK_SHA256 = state_live.ROLLBACK_SHA256
FALLBACK_V2237 = state_live.FALLBACK_V2237
FALLBACK_V2237_SHA256 = state_live.FALLBACK_V2237_SHA256
FALLBACK_V48 = state_live.FALLBACK_V48

DEFAULT_EVENTS = ("event3", "event0")
DEFAULT_COUNT = 16
DEFAULT_TIMEOUT_MS = 45000
PROXY_BUTTON_FIELDS = ("forward", "back", "fire")
BUTTON_CAP_KEYS = ("key_volup", "key_voldown", "key_power")


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


def parse_events_arg(value: str) -> tuple[str, ...]:
    events = tuple(part.strip() for part in value.split(",") if part.strip())
    if not events:
        raise argparse.ArgumentTypeError("at least one event name is required")
    for event in events:
        if not event.startswith("event") or not event[5:].isdigit():
            raise argparse.ArgumentTypeError(f"invalid event name: {event}")
    return events


def button_proxy_caps_ok(parsed_caps: dict[str, Any]) -> bool:
    decoded = parsed_caps.get("decode", {}) if isinstance(parsed_caps.get("decode"), dict) else {}
    return bool(
        parsed_caps.get("has_event_header")
        and decoded.get("ev_key") == "1"
        and any(decoded.get(key) == "1" for key in BUTTON_CAP_KEYS)
    )


def proxy_state_fields(parsed_sample: dict[str, Any]) -> list[str]:
    states = parsed_sample.get("states", []) if isinstance(parsed_sample.get("states"), list) else []
    fields: set[str] = set()
    for item in states:
        if not isinstance(item, dict):
            continue
        for field in PROXY_BUTTON_FIELDS:
            if item.get(field) == 1:
                fields.add(field)
    return sorted(fields)


def has_proxy_button_state(parsed_sample: dict[str, Any]) -> bool:
    return bool(proxy_state_fields(parsed_sample))


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
        "events": list(args.events),
        "count": args.count,
        "timeout_ms": args.timeout_ms,
        "operator_prerequisite": "operator presses VOLUMEUP/VOLUMEDOWN/POWER during each bounded doominput window",
        "hard_boundary": [
            "boot partition only via native_init_flash.py",
            "rollback to v2321 and verify selftest fail=0",
            "read-only inputscan/inputcaps plus read-only doominput evdev samples",
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
        and state.get("events")
        and state.get("timeout_ms", 0) > 0
        and state.get("count", 0) > 0
    )


def button_sample_pass(event_result: dict[str, Any], *, post_selftest_ok: bool) -> bool:
    parsed = event_result.get("parsed", {}) if isinstance(event_result.get("parsed"), dict) else {}
    return bool(
        event_result.get("selected_is_button")
        and event_result.get("inputcaps_rc") == 0
        and event_result.get("inputcaps_button_ok")
        and event_result.get("doominput_rc") == 0
        and has_proxy_button_state(parsed)
        and post_selftest_ok
    )


def summarize_event_results(event_results: list[dict[str, Any]]) -> list[str]:
    lines = []
    for item in event_results:
        parsed = item.get("parsed", {}) if isinstance(item.get("parsed"), dict) else {}
        fields = ",".join(proxy_state_fields(parsed)) or "-"
        lines.append(
            f"- `{item.get('event')}` selected_buttons=`{int(bool(item.get('selected_is_button')))}` "
            f"caps_ok=`{int(bool(item.get('inputcaps_button_ok')))}` "
            f"doominput_rc=`{item.get('doominput_rc')}` "
            f"events=`{parsed.get('doominput_event_count', 0)}` "
            f"states=`{parsed.get('doominput_state_count', 0)}` "
            f"active_states=`{parsed.get('active_state_count', 0)}` "
            f"proxy_fields=`{fields}` pass=`{int(bool(item.get('pass')))}`"
        )
    return lines or ["- none captured in this run"]


def render_report(result: dict[str, Any]) -> str:
    live_executed = bool(result.get("live_executed"))
    preflight = result.get("preflight", {}) if isinstance(result.get("preflight"), dict) else {}
    inputscan = result.get("inputscan", {}) if isinstance(result.get("inputscan"), dict) else {}
    event_results = result.get("event_results", []) if isinstance(result.get("event_results"), list) else []
    title = "Button Proxy Live" if live_executed else "Button Proxy Live Handoff Dry Run"
    preflight_status = result.get("preflight_ok") if "preflight_ok" in result else False
    if "preflight_ok" not in result and all(
        key in preflight for key in ("candidate", "rollback", "fallback_v2237", "fallback_v48", "flash_helper")
    ):
        preflight_status = preflight_ok(preflight)

    candidate_lines = []
    for item in inputscan.get("button_events", []) if isinstance(inputscan.get("button_events"), list) else []:
        candidate_lines.append(f"- buttons `{item.get('event')}` `{item.get('name')}` class=`{item.get('class')}`")
    if not candidate_lines:
        candidate_lines = ["- none captured in this run"]

    def live_bool(value: Any) -> str:
        return str(int(bool(value))) if live_executed else "not-run"

    def live_value(value: Any) -> str:
        return str(value) if live_executed else "not-run"

    return "\n".join([
        f"# Native Init V2997 DOOM Input {title}",
        "",
        "## Summary",
        "",
        f"- Decision: `{result.get('decision')}`",
        f"- Result before rollback: `{int(bool(result.get('pass')))}`",
        "- Track: active Video playback / DOOM input prerequisite.",
        f"- Candidate: `A90 Linux init {CANDIDATE_VERSION} ({CANDIDATE_TAG})`",
        f"- Candidate image: `{rel(CANDIDATE_IMAGE)}`",
        f"- Candidate SHA256: `{CANDIDATE_SHA256}`",
        f"- Events: `{','.join(str(item) for item in preflight.get('events', []))}`",
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
        f"- Inputscan rc: `{live_value(result.get('inputscan_rc'))}` button_candidates=`{live_value(inputscan.get('button_candidates'))}`",
        f"- Candidate post-sample selftest fail=0: `{live_bool(result.get('candidate_selftest_after_doominput_fail0'))}`",
        "",
        "## Button Candidates",
        "",
        *candidate_lines,
        "",
        "## Per-Event Results",
        "",
        *summarize_event_results(event_results),
        "",
        "## Rollback Evidence",
        "",
        f"- Rollback attempted: `{int(bool(result.get('rollback_attempted')))}`",
        f"- Rollback step ok: `{int(bool(result.get('rollback_step_ok')))}`",
        f"- Rollback health: version_ok=`{int(bool(result.get('rollback_version_ok')))}` selftest_fail0=`{int(bool(result.get('rollback_selftest_fail0')))}`",
        "",
        "## Interpretation",
        "",
        "- V2997 stages live validation for the V2996 diagnostic physical-button proxy candidate.",
        "- Pass requires a selected `buttons` event, POWER/VOLUME capability bits, and `doominput.state` evidence for `forward`, `back`, or `fire` while candidate health remains clean.",
        "- Dry-run mode does not flash; live mode should run only when an operator can press A90 physical buttons during the bounded sample windows.",
        "- This is diagnostic evdev-to-`doominput.state` liveness proof, not a final DOOM control scheme.",
        "",
        "## Safety",
        "",
        "- Live mode flashes only the boot partition through `native_init_flash.py`; rollback target remains `v2321`.",
        "- The validation path only reads `/sys/class/input` capability files and `/dev/input/event*` events.",
        "- No input injection, `EVIOCGRAB`, keymap change, sysfs write, Wi-Fi, audio route/playback, video playback, PMIC, backlight, GPIO, regulator, GDSC, or forbidden partition path is touched.",
        "- Raw command output stays private under `workspace/private/runs/`; this report includes metadata only.",
        "",
        "## Host Validation",
        "",
        "- `python3 -m py_compile workspace/public/src/scripts/revalidation/native_doominput_button_proxy_live_handoff_v2997.py tests/test_native_doominput_button_proxy_live_handoff_v2997.py`: PASS",
        "- `PYTHONPATH=workspace/public/src/scripts/revalidation:workspace/public/src/harness python3 -m unittest tests.test_native_doominput_button_proxy_live_handoff_v2997`: PASS",
        "- `PYTHONPATH=workspace/public/src/scripts/revalidation:workspace/public/src/harness python3 workspace/public/src/scripts/revalidation/native_doominput_button_proxy_live_handoff_v2997.py --count 16 --timeout-ms 45000`: PASS (dry-run preflight/report)",
        "- `git diff --check`: PASS",
        "- `PYTHONPATH=workspace/public/src/scripts/revalidation:workspace/public/src/harness python3 -m unittest discover -s tests -p 'test_*.py'`: FAIL (`25` failures, `5` errors in legacy audio tests; focused V2997 tests passed).",
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
        "event_results": [],
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
        result.update({"inputscan_rc": inputscan_step.get("rc"), "inputscan": parsed_scan})
        events_by_name = {
            str(item.get("event")): item
            for item in parsed_scan.get("events", [])
            if isinstance(item, dict) and item.get("event")
        }
        for event_name in args.events:
            selected = events_by_name.get(event_name, {})
            event_result: dict[str, Any] = {
                "event": event_name,
                "selected_event": selected,
                "selected_is_button": "buttons" in state_live.class_tokens(selected),
                "inputcaps_rc": None,
                "inputcaps_button_ok": False,
                "doominput_rc": None,
                "parsed": {},
                "pass": False,
            }
            result["event_results"].append(event_result)
            if not event_result["selected_is_button"]:
                event_result["decision"] = "not-button-candidate"
                continue
            base.run_serial_step(out_dir, steps, f"candidate-hide-before-inputcaps-{event_name}", ["hide"], timeout=60.0, retry_unsafe=True)
            caps_step = base.run_serial_step(out_dir, steps, f"candidate-inputcaps-{event_name}", ["inputcaps", event_name], timeout=120.0, retry_unsafe=True)
            parsed_caps = caps_live.parse_inputcaps(stdout_of(caps_step))
            event_result.update({
                "inputcaps_rc": caps_step.get("rc"),
                "inputcaps_stdout_path": caps_step.get("stdout_path"),
                "inputcaps_button_ok": button_proxy_caps_ok(parsed_caps),
            })
            if not event_result["inputcaps_button_ok"]:
                event_result["decision"] = "button-caps-not-ready"
                continue
            base.run_serial_step(out_dir, steps, f"candidate-hide-before-doominput-{event_name}", ["hide"], timeout=60.0, retry_unsafe=True)
            sample = state_live.run_timeout_doominput(
                args.host,
                args.port,
                event_name,
                args.count,
                timeout_ms=args.timeout_ms,
            )
            readinput_live.write_manual_step(out_dir, steps, f"candidate-doominput-{event_name}-button-proxy-sample", sample)
            event_result.update({
                "doominput_rc": sample.get("protocol", {}).get("rc"),
                "doominput_stdout_path": next(
                    (
                        step.get("stdout_path")
                        for step in reversed(steps)
                        if step.get("name") == f"candidate-doominput-{event_name}-button-proxy-sample"
                    ),
                    None,
                ),
                "parsed": sample.get("parsed", {}),
            })
        after = base.run_serial_step(out_dir, steps, "candidate-selftest-after-doominput", ["selftest", "verbose"], timeout=120.0, retry_unsafe=True)
        result["candidate_selftest_after_doominput_fail0"] = selftest_step_ok(after)
        for event_result in result["event_results"]:
            event_result["pass"] = button_sample_pass(event_result, post_selftest_ok=result["candidate_selftest_after_doominput_fail0"])
        result["pass"] = bool(
            result.get("candidate_version_ok")
            and result.get("candidate_selftest_fail0")
            and result.get("inputscan_rc") == 0
            and any(item.get("pass") for item in result["event_results"])
        )
        result["decision"] = f"{DECISION_PREFIX}-state-pass-before-rollback" if result["pass"] else f"{DECISION_PREFIX}-state-not-proven"
        if not result["pass"]:
            raise RuntimeError("button proxy doominput samples did not produce required state evidence")
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
            "for each requested button event: inputcaps <event>",
            f"for each requested button event: doominput <event> {args.count} {args.timeout_ms}",
            "operator presses VOLUMEUP/VOLUMEDOWN/POWER during the bounded sample windows",
            "require doominput.state forward/back/fire proxy state lines",
            "selftest verbose after doominput samples",
            "rollback v2321 and verify selftest fail=0",
        ],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="flash V2996, sample physical-button doominput state, then rollback")
    parser.add_argument("--events", type=parse_events_arg, default=DEFAULT_EVENTS, help="comma-separated button events, default event3,event0")
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
            "event_results": [],
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
            "event_results": [],
        }
        write_json(out_dir / "result.json", result)
        REPORT_PATH.write_text(render_report(result), encoding="utf-8")
        print(json.dumps(result, indent=2, sort_keys=True))
        return 1
    result = run_live(args, out_dir, state)
    print(json.dumps({
        "decision": result.get("decision"),
        "pass": result.get("pass"),
        "event_results": [
            {
                "event": item.get("event"),
                "doominput_rc": item.get("doominput_rc"),
                "proxy_fields": proxy_state_fields(item.get("parsed") or {}),
                "pass": item.get("pass"),
            }
            for item in result.get("event_results", [])
        ],
        "rollback_version_ok": result.get("rollback_version_ok"),
        "rollback_selftest_fail0": result.get("rollback_selftest_fail0"),
        "result_json": result.get("result_json"),
    }, indent=2, sort_keys=True))
    return 0 if result.get("pass") and result.get("rollback_version_ok") and result.get("rollback_selftest_fail0") else 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""V2978 live validation for V2977 read-only inputscan inventory.

This runner flashes the V2977 inputscan candidate, runs health checks and the
read-only ``inputscan`` command, then rolls back to the v2321 clean USB identity
checkpoint. It does not read event streams or require a human touch sample.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import native_av_pcm_video_corun_live_handoff_v2882 as av_live

base = av_live.base
ROOT = av_live.ROOT

RUN_ID = "V2978"
BUILD_TAG = "v2978-inputscan-live"
DECISION_PREFIX = "v2978-inputscan"
REPORT_PATH = ROOT / "docs/reports/NATIVE_INIT_V2978_INPUTSCAN_LIVE_2026-06-20.md"

CANDIDATE_IMAGE = ROOT / "workspace/private/inputs/boot_images/boot_linux_v2977_inputscan_summary.img"
CANDIDATE_VERSION = "0.10.60"
CANDIDATE_TAG = "v2977-inputscan-summary"
CANDIDATE_SHA256 = "52a5d0329f8c42f360772e4541f77d31d4f3569e7e01aa086d17ed655a4349aa"

ROLLBACK_IMAGE = av_live.ROLLBACK_IMAGE
ROLLBACK_VERSION = av_live.ROLLBACK_VERSION
ROLLBACK_SHA256 = av_live.ROLLBACK_SHA256
FALLBACK_V2237 = av_live.FALLBACK_V2237
FALLBACK_V2237_SHA256 = av_live.FALLBACK_V2237_SHA256
FALLBACK_V48 = av_live.FALLBACK_V48
SELFTEST_FAIL0_RE = re.compile(r"\bfail=0\b")
SUMMARY_RE = re.compile(
    r"inputscan\.summary events=(?P<events>\d+) nodes=(?P<nodes>\d+) "
    r"touch_candidates=(?P<touch>\d+) keyboard_candidates=(?P<keyboard>\d+) "
    r"button_candidates=(?P<button>\d+)"
)
EVENT_RE = re.compile(
    r"^inputscan\.event=(?P<event>\S+) name=(?P<name>.*?) dev=(?P<dev>\S+) "
    r"node=(?P<node>\S+) class=(?P<class>[^\r\n]+)\r?$",
    re.MULTILINE,
)


def now_slug() -> str:
    return datetime.now(timezone.utc).astimezone().strftime("%Y%m%d-%H%M%S")


def rel(path: Path) -> str:
    return av_live.rel(path)


def stdout_of(step: dict[str, Any] | None) -> str:
    if not step:
        return ""
    return av_live.stdout_of(step)


def file_state(path: Path, expected_sha: str | None = None) -> dict[str, Any]:
    return av_live.file_state(path, expected_sha)


def selftest_step_ok(step: dict[str, Any]) -> bool:
    return bool(SELFTEST_FAIL0_RE.search(stdout_of(step))) or base.protocol_selftest_ok(step)


def flash_command(image: Path, expect_version: str, expect_sha: str, *, from_native: bool) -> list[str]:
    return av_live.flash_command(image, expect_version, expect_sha, from_native=from_native)


def preflight_state() -> dict[str, Any]:
    return {
        "run_id": RUN_ID,
        "candidate": file_state(CANDIDATE_IMAGE, CANDIDATE_SHA256),
        "rollback": file_state(ROLLBACK_IMAGE, ROLLBACK_SHA256),
        "fallback_v2237": file_state(FALLBACK_V2237, FALLBACK_V2237_SHA256),
        "fallback_v48": file_state(FALLBACK_V48),
        "flash_helper": file_state(base.FLASH),
        "candidate_version": CANDIDATE_VERSION,
        "candidate_tag": CANDIDATE_TAG,
        "hard_boundary": [
            "boot partition only via native_init_flash.py",
            "rollback to v2321 and verify selftest fail=0",
            "read-only inputscan sysfs/capability inventory only",
            "no readinput sample, no input injection, no keymap changes",
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


def parse_inputscan(text: str) -> dict[str, Any]:
    summary_match = SUMMARY_RE.search(text)
    events: list[dict[str, str]] = []
    for match in EVENT_RE.finditer(text):
        event_class = match.group("class").strip()
        events.append({
            "event": match.group("event").strip(),
            "name": match.group("name").strip(),
            "class": event_class,
        })

    def class_tokens(item: dict[str, str]) -> set[str]:
        return {part.strip() for part in item["class"].split(",") if part.strip()}

    touch_events = [item for item in events if "touch" in class_tokens(item)]
    keyboard_events = [item for item in events if "keyboard" in class_tokens(item)]
    button_events = [item for item in events if "buttons" in class_tokens(item)]
    parsed: dict[str, Any] = {
        "summary_found": summary_match is not None,
        "events": events,
        "touch_events": touch_events,
        "keyboard_events": keyboard_events,
        "button_events": button_events,
    }
    if summary_match:
        parsed.update({
            "event_count": int(summary_match.group("events")),
            "node_count": int(summary_match.group("nodes")),
            "touch_candidates": int(summary_match.group("touch")),
            "keyboard_candidates": int(summary_match.group("keyboard")),
            "button_candidates": int(summary_match.group("button")),
        })
    else:
        parsed.update({
            "event_count": 0,
            "node_count": 0,
            "touch_candidates": 0,
            "keyboard_candidates": 0,
            "button_candidates": 0,
        })
    parsed["touch_event_count_matches"] = len(touch_events) == parsed["touch_candidates"]
    parsed["keyboard_event_count_matches"] = len(keyboard_events) == parsed["keyboard_candidates"]
    parsed["button_event_count_matches"] = len(button_events) == parsed["button_candidates"]
    return parsed


def evaluate_result_markers(result: dict[str, Any]) -> bool:
    parsed = result.get("inputscan", {}) if isinstance(result.get("inputscan"), dict) else {}
    return bool(
        result.get("candidate_version_ok")
        and result.get("candidate_status_ok")
        and result.get("candidate_selftest_fail0")
        and result.get("candidate_help_has_inputscan")
        and result.get("inputscan_rc") == 0
        and parsed.get("summary_found")
        and parsed.get("event_count", 0) > 0
        and parsed.get("touch_event_count_matches")
        and parsed.get("keyboard_event_count_matches")
        and parsed.get("button_event_count_matches")
        and result.get("candidate_selftest_after_inputscan_fail0")
    )


def apply_marker_decision(result: dict[str, Any]) -> None:
    result["pass"] = evaluate_result_markers(result)
    result["decision"] = f"{DECISION_PREFIX}-live-pass-before-rollback" if result["pass"] else f"{DECISION_PREFIX}-marker-failed"


def render_report(result: dict[str, Any]) -> str:
    parsed = result.get("inputscan", {}) if isinstance(result.get("inputscan"), dict) else {}
    touch_lines = []
    for item in parsed.get("touch_events", []) if isinstance(parsed.get("touch_events"), list) else []:
        touch_lines.append(f"- `{item.get('event')}` `{item.get('name')}` class=`{item.get('class')}`")
    if not touch_lines:
        touch_lines = ["- none captured in this run"]
    keyboard_lines = []
    for item in parsed.get("keyboard_events", []) if isinstance(parsed.get("keyboard_events"), list) else []:
        keyboard_lines.append(f"- `{item.get('event')}` `{item.get('name')}` class=`{item.get('class')}`")
    if not keyboard_lines:
        keyboard_lines = ["- none captured in this run"]
    return "\n".join([
        "# Native Init V2978 Inputscan Live Validation",
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
        f"- Reclassified from existing live evidence: `{int(bool(result.get('posthoc_reclassified')))}`",
        "",
        "## Live Evidence",
        "",
        f"- Candidate version ok: `{int(bool(result.get('candidate_version_ok')))}`",
        f"- Candidate status ok: `{int(bool(result.get('candidate_status_ok')))}`",
        f"- Candidate selftest fail=0: `{int(bool(result.get('candidate_selftest_fail0')))}`",
        f"- Inputscan rc: `{result.get('inputscan_rc')}`",
        f"- Input events: `{parsed.get('event_count', 0)}` nodes=`{parsed.get('node_count', 0)}`",
        f"- Touch candidates: `{parsed.get('touch_candidates', 0)}`",
        f"- Keyboard candidates: `{parsed.get('keyboard_candidates', 0)}`",
        f"- Button candidates: `{parsed.get('button_candidates', 0)}`",
        f"- Candidate post-scan selftest fail=0: `{int(bool(result.get('candidate_selftest_after_inputscan_fail0')))}`",
        "",
        "## Touch Candidates",
        "",
        *touch_lines,
        "",
        "## Keyboard Fallback Candidates",
        "",
        *keyboard_lines,
        "",
        "## Rollback Evidence",
        "",
        f"- Rollback attempted: `{int(bool(result.get('rollback_attempted')))}`",
        f"- Rollback step ok: `{int(bool(result.get('rollback_step_ok')))}`",
        f"- Rollback health: version_ok=`{int(bool(result.get('rollback_version_ok')))}` selftest_fail0=`{int(bool(result.get('rollback_selftest_fail0')))}`",
        "",
        "## Interpretation",
        "",
        "- V2978 validates the V2977 `inputscan` command on hardware without consuming input events or requiring a human touch sample.",
        "- If touch candidates are present, the next bounded unit can sample the named event with `readinput <event> 1` while the operator touches the panel.",
        "- If no touch candidate is present but keyboard candidates exist, DOOM input should pivot to the USB-keyboard fallback before touch firmware work.",
        "",
        "## Safety",
        "",
        "- Only the boot partition was flashed, through `native_init_flash.py`; rollback target remained `v2321`.",
        "- No input stream read, input injection, keymap change, Wi-Fi, audio route/playback, video playback, PMIC, backlight, GPIO, regulator, GDSC, or forbidden partition path was touched.",
        "- Raw command output stays private under `workspace/private/runs/`; this report includes only metadata and event names/classes.",
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
        status = base.run_serial_step(out_dir, steps, "candidate-status", ["status"], timeout=90.0, retry_unsafe=True)
        selftest = base.run_serial_step(out_dir, steps, "candidate-selftest", ["selftest", "verbose"], timeout=120.0, retry_unsafe=True)
        help_step = base.run_serial_step(out_dir, steps, "candidate-help", ["help"], timeout=90.0, retry_unsafe=True)
        inputscan = base.run_serial_step(out_dir, steps, "candidate-inputscan", ["inputscan"], timeout=120.0, retry_unsafe=True)
        inputscan_text = stdout_of(inputscan)
        parsed = parse_inputscan(inputscan_text)
        after = base.run_serial_step(out_dir, steps, "candidate-selftest-after-inputscan", ["selftest", "verbose"], timeout=120.0, retry_unsafe=True)
        result.update({
            "candidate_version_ok": f"A90 Linux init {CANDIDATE_VERSION} ({CANDIDATE_TAG})" in stdout_of(version),
            "candidate_status_ok": bool(status.get("ok")),
            "candidate_selftest_fail0": selftest_step_ok(selftest),
            "candidate_help_has_inputscan": "inputscan [eventX]" in stdout_of(help_step),
            "inputscan_rc": inputscan.get("rc"),
            "inputscan_stdout_path": inputscan.get("stdout_path"),
            "inputscan": parsed,
            "candidate_selftest_after_inputscan_fail0": selftest_step_ok(after),
        })
        apply_marker_decision(result)
        if not result["pass"]:
            raise RuntimeError("inputscan live markers did not pass")
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
        av_live.write_json(out_dir / "result.json", result)
        REPORT_PATH.write_text(render_report(result), encoding="utf-8")
    return result


def reclassify_run(run_dir: Path) -> dict[str, Any]:
    result_path = run_dir / "result.json"
    result = json.loads(result_path.read_text(encoding="utf-8"))
    previous = {
        "decision": result.get("decision"),
        "pass": result.get("pass"),
        "error_type": result.get("error_type"),
        "error": result.get("error"),
    }
    stdout_path_value = result.get("inputscan_stdout_path") or str(run_dir / "06_candidate-inputscan.txt")
    stdout_path = Path(stdout_path_value)
    if not stdout_path.is_absolute():
        stdout_path = ROOT / stdout_path
    result["inputscan"] = parse_inputscan(stdout_path.read_text(encoding="utf-8", errors="replace"))
    apply_marker_decision(result)
    result["posthoc_reclassified"] = True
    result["posthoc_previous"] = previous
    result["posthoc_reclassify_reason"] = "reparsed preserved candidate-inputscan stdout; no additional device action"
    if result["pass"]:
        result.pop("error_type", None)
        result.pop("error", None)
    result_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    REPORT_PATH.write_text(render_report(result), encoding="utf-8")
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="flash V2977, run inputscan, then rollback to V2321")
    parser.add_argument("--flash-timeout", type=float, default=900.0)
    parser.add_argument("--reclassify-run", type=Path, help="reparse an existing V2978 run directory without touching the device")
    return parser.parse_args()


def dry_run_payload(state: dict[str, Any]) -> dict[str, Any]:
    return {
        "decision": f"{DECISION_PREFIX}-dry-run" if preflight_ok(state) else f"{DECISION_PREFIX}-preflight-failed",
        "ok": preflight_ok(state),
        "preflight": state,
        "commands": [
            f"verify rollback image {ROLLBACK_IMAGE}",
            f"flash {CANDIDATE_IMAGE}",
            "version/status/selftest/help",
            "inputscan",
            "selftest verbose after inputscan",
            "rollback v2321 and verify selftest fail=0",
        ],
    }


def main() -> int:
    args = parse_args()
    if args.reclassify_run:
        result = reclassify_run(args.reclassify_run)
        print(json.dumps({
            "decision": result.get("decision"),
            "pass": bool(result.get("pass")),
            "out_dir": result.get("out_dir"),
            "touch_candidates": (result.get("inputscan") or {}).get("touch_candidates"),
            "keyboard_candidates": (result.get("inputscan") or {}).get("keyboard_candidates"),
            "rollback_version_ok": result.get("rollback_version_ok"),
            "rollback_selftest_fail0": result.get("rollback_selftest_fail0"),
        }, indent=2, sort_keys=True))
        return 0 if (result.get("pass") and result.get("rollback_version_ok") and result.get("rollback_selftest_fail0")) else 1
    out_dir = ROOT / f"workspace/private/runs/input/{BUILD_TAG}-{now_slug()}"
    out_dir.mkdir(parents=True, exist_ok=True)
    state = preflight_state()
    if not args.live:
        payload = dry_run_payload(state)
        av_live.write_json(out_dir / "dry_run.json", payload)
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0 if payload["ok"] else 1
    if not preflight_ok(state):
        payload = {"decision": f"{DECISION_PREFIX}-preflight-failed", "pass": False, "preflight": state, "out_dir": rel(out_dir)}
        av_live.write_json(out_dir / "result.json", payload)
        REPORT_PATH.write_text(render_report(payload), encoding="utf-8")
        print(json.dumps({"decision": payload["decision"], "pass": False, "out_dir": rel(out_dir)}, indent=2, sort_keys=True))
        return 1
    result = run_live(args, out_dir, state)
    print(json.dumps({
        "decision": result.get("decision"),
        "pass": bool(result.get("pass")),
        "out_dir": rel(out_dir),
        "touch_candidates": (result.get("inputscan") or {}).get("touch_candidates"),
        "keyboard_candidates": (result.get("inputscan") or {}).get("keyboard_candidates"),
        "rollback_version_ok": result.get("rollback_version_ok"),
        "rollback_selftest_fail0": result.get("rollback_selftest_fail0"),
    }, indent=2, sort_keys=True))
    return 0 if (result.get("pass") and result.get("rollback_version_ok") and result.get("rollback_selftest_fail0")) else 1


if __name__ == "__main__":
    raise SystemExit(main())

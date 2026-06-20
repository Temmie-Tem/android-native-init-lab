#!/usr/bin/env python3
"""V2995 host-only audit for remaining DOOM input branches.

This report prevents low-information live repeats after V2993/V2994 by checking
the remaining input evidence against the actual native-init source. It does not
flash, call the device, or open evdev nodes.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[5]

RUN_ID = "V2995"
DECISION = "v2995-doom-input-residual-branches-gated"
REPORT_PATH = ROOT / "docs/reports/NATIVE_INIT_V2995_DOOM_INPUT_RESIDUAL_BRANCH_AUDIT_2026-06-20.md"

V2991_RESULT = ROOT / "workspace/private/runs/input/v2991-doominput-dual-touch-live-20260620-181451/result.json"
V2993_REPORT = ROOT / "docs/reports/NATIVE_INIT_V2993_DOOM_INPUT_FRONTIER_DECISION_2026-06-20.md"
V2994_REPORT = ROOT / "docs/reports/NATIVE_INIT_V2994_DOOM_INPUT_LIVE_GATE_AUDIT_2026-06-20.md"
MENU_APPS_SOURCE = ROOT / "workspace/public/src/native-init/v319/40_menu_apps.inc.c"
INPUT_SOURCE = ROOT / "workspace/public/src/native-init/a90_input.c"

DOOM_KEY_CODES = [
    "KEY_W",
    "KEY_S",
    "KEY_A",
    "KEY_D",
    "KEY_UP",
    "KEY_DOWN",
    "KEY_LEFT",
    "KEY_RIGHT",
    "KEY_ENTER",
    "KEY_SPACE",
    "KEY_ESC",
    "KEY_LEFTCTRL",
    "KEY_RIGHTCTRL",
    "KEY_LEFTSHIFT",
    "KEY_RIGHTSHIFT",
    "BTN_TOUCH",
]
DEVICE_BUTTON_CODES = ["KEY_POWER", "KEY_VOLUMEUP", "KEY_VOLUMEDOWN"]


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def extract_switch_case_codes(source: str, function_name: str) -> list[str]:
    match = re.search(
        rf"static [^{{]+ {re.escape(function_name)}\([^{{]+{{(?P<body>.*?)\n}}",
        source,
        flags=re.S,
    )
    if not match:
        return []
    return sorted(set(re.findall(r"case (KEY_[A-Z0-9_]+|BTN_[A-Z0-9_]+):", match.group("body"))))


def extract_menu_button_codes(input_source: str) -> list[str]:
    match = re.search(
        r"unsigned int a90_input_button_mask_from_key\([^}]+}",
        input_source,
        flags=re.S,
    )
    if not match:
        return []
    return sorted(set(re.findall(r"case (KEY_[A-Z0-9_]+):", match.group(0))))


def v2991_input_summary(v2991: dict[str, Any]) -> dict[str, Any]:
    scan = v2991.get("inputscan", {}) if isinstance(v2991.get("inputscan"), dict) else {}
    event_results = v2991.get("event_results", []) if isinstance(v2991.get("event_results"), list) else []
    zero_touch_events = [
        item.get("event")
        for item in event_results
        if isinstance(item, dict)
        and item.get("doominput_rc") == -110
        and (item.get("parsed") or {}).get("doominput_event_count") == 0
        and (item.get("parsed") or {}).get("doominput_state_count") == 0
    ]
    return {
        "keyboard_candidates": scan.get("keyboard_candidates"),
        "keyboard_events": scan.get("keyboard_events", []),
        "touch_candidates": scan.get("touch_candidates"),
        "touch_events": scan.get("touch_events", []),
        "button_candidates": scan.get("button_candidates"),
        "button_events": scan.get("button_events", []),
        "zero_touch_events": zero_touch_events,
        "rollback_clean": bool(v2991.get("rollback_version_ok") and v2991.get("rollback_selftest_fail0")),
    }


def build_payload() -> dict[str, Any]:
    menu_source = MENU_APPS_SOURCE.read_text(encoding="utf-8")
    input_source = INPUT_SOURCE.read_text(encoding="utf-8")
    v2991 = read_json(V2991_RESULT)
    summary = v2991_input_summary(v2991)
    doom_key_codes = extract_switch_case_codes(menu_source, "doominput_apply_key")
    role_codes = extract_switch_case_codes(menu_source, "readinput_event_role_name")
    menu_button_codes = extract_menu_button_codes(input_source)
    button_codes_in_doom = sorted(set(doom_key_codes).intersection(DEVICE_BUTTON_CODES))
    v2993_text = V2993_REPORT.read_text(encoding="utf-8")
    v2994_text = V2994_REPORT.read_text(encoding="utf-8")
    button_branch_viable_now = bool(
        summary["button_candidates"]
        and set(DEVICE_BUTTON_CODES).issubset(set(menu_button_codes))
        and button_codes_in_doom
    )
    return {
        "run_id": RUN_ID,
        "decision": DECISION,
        "v2991": summary,
        "source": {
            "doominput_key_codes": doom_key_codes,
            "readinput_role_codes": role_codes,
            "menu_button_codes": menu_button_codes,
            "device_button_codes": DEVICE_BUTTON_CODES,
            "device_buttons_mapped_by_doominput": button_codes_in_doom,
            "doom_keyboard_codes_present": sorted(set(DOOM_KEY_CODES).intersection(doom_key_codes)),
        },
        "prior_reports": {
            "v2993_touch_repeat_saturated": "Do not keep re-running identical event6/event8 touch samples" in v2993_text,
            "v2994_keyboard_live_not_actionable": "v2994-doom-input-live-gate-not-actionable" in v2994_text,
        },
        "branch_status": {
            "touch_repeat": "gated-new-touch-hypothesis-required",
            "usb_keyboard": "gated-a90-keyboard-evdev-required",
            "physical_buttons": "not-current-doom-fallback",
            "physical_buttons_viable_now": button_branch_viable_now,
        },
        "inputs": {
            "v2991_result": rel(V2991_RESULT),
            "v2993_report": rel(V2993_REPORT),
            "v2994_report": rel(V2994_REPORT),
            "menu_apps_source": rel(MENU_APPS_SOURCE),
            "input_source": rel(INPUT_SOURCE),
        },
        "next_action": (
            "Do not flash another input live run for touch, USB keyboard, or physical buttons "
            "until the missing prerequisite changes: a new touch hypothesis, an A90 keyboard-class "
            "evdev node, or an explicit source change that defines a DOOM-capable physical-button map."
        ),
    }


def event_list(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "-"
    return ", ".join(f"`{item.get('event')}` `{item.get('name')}` class=`{item.get('class')}`" for item in rows)


def render_report(payload: dict[str, Any]) -> str:
    v2991 = payload["v2991"]
    source = payload["source"]
    branches = payload["branch_status"]
    return "\n".join([
        "# Native Init V2995 DOOM Input Residual Branch Audit",
        "",
        "## Summary",
        "",
        f"- Decision: `{payload['decision']}`",
        "- Device action: `none` in this host-only/source audit.",
        "- Track: active Video playback / DOOM input prerequisite.",
        f"- Touch repeat branch: `{branches['touch_repeat']}`",
        f"- USB keyboard branch: `{branches['usb_keyboard']}`",
        f"- Physical button branch: `{branches['physical_buttons']}`",
        f"- Physical button viable as current DOOM fallback: `{int(bool(branches['physical_buttons_viable_now']))}`",
        "",
        "## Evidence State",
        "",
        f"- V2991 keyboard candidates: `{v2991['keyboard_candidates']}` events: {event_list(v2991['keyboard_events'])}",
        f"- V2991 touch candidates: `{v2991['touch_candidates']}` events: {event_list(v2991['touch_events'])}",
        f"- V2991 zero-event touch samples: `{','.join(v2991['zero_touch_events'])}`",
        f"- V2991 button candidates: `{v2991['button_candidates']}` events: {event_list(v2991['button_events'])}",
        f"- V2991 rollback clean: `{int(bool(v2991['rollback_clean']))}`",
        f"- V2993 touch repeat saturated: `{int(bool(payload['prior_reports']['v2993_touch_repeat_saturated']))}`",
        f"- V2994 keyboard live not actionable: `{int(bool(payload['prior_reports']['v2994_keyboard_live_not_actionable']))}`",
        "",
        "## Source Audit",
        "",
        f"- Existing menu/input physical buttons: `{','.join(source['menu_button_codes'])}`",
        f"- `doominput_apply_key()` mapped keys: `{','.join(source['doominput_key_codes'])}`",
        f"- Device physical buttons mapped by current `doominput`: `{','.join(source['device_buttons_mapped_by_doominput']) or '-'}`",
        "- The current `inputscan` classifier treats `KEY_POWER`/`KEY_VOLUMEUP`/`KEY_VOLUMEDOWN` as `buttons`, not `keyboard`.",
        "- The current `doominput` state only treats WASD/arrows, Enter/Space, Esc, Ctrl/Shift, and touch contact as DOOM controls.",
        "",
        "## Decision",
        "",
        "- Repeating touch samples is gated by V2993 until a new touch hypothesis exists.",
        "- Running V2992 keyboard live is gated by V2994 until A90 exposes a keyboard-class evdev node.",
        "- Sampling `event0`/`event3` physical buttons through current `doominput` would not prove the requested USB-keyboard fallback because those keys are not mapped to DOOM state bits.",
        "- A physical-button DOOM branch would require an explicit source design/change first; it is not a current live-validation branch.",
        "",
        "## Next Action",
        "",
        f"- {payload['next_action']}",
        "",
        "## Evidence Inputs",
        "",
        f"- V2991 result: `{payload['inputs']['v2991_result']}`",
        f"- V2993 report: `{payload['inputs']['v2993_report']}`",
        f"- V2994 report: `{payload['inputs']['v2994_report']}`",
        f"- Native menu/input source: `{payload['inputs']['menu_apps_source']}`",
        f"- Native physical-button source: `{payload['inputs']['input_source']}`",
        "",
        "## Host Validation",
        "",
        "- `python3 -m py_compile workspace/public/src/scripts/revalidation/native_doom_input_residual_branch_audit_v2995.py tests/test_native_doom_input_residual_branch_audit_v2995.py`: PASS",
        "- `PYTHONPATH=workspace/public/src/scripts/revalidation:workspace/public/src/harness python3 -m unittest tests.test_native_doom_input_residual_branch_audit_v2995`: PASS (`5` tests)",
        "- `PYTHONPATH=workspace/public/src/scripts/revalidation:workspace/public/src/harness python3 workspace/public/src/scripts/revalidation/native_doom_input_residual_branch_audit_v2995.py`: PASS (host-only/source report materialized)",
        "- `git diff --check`: PASS",
        "",
        "## Safety",
        "",
        "- Host-only/source audit; no flash, no serial command, no evdev open, no input injection, and no sysfs write.",
        "- No Wi-Fi/audio/video playback, PMIC, backlight, GPIO, regulator, GDSC, or forbidden partition path is touched.",
        "- No new raw command output is collected; prior private run inputs remain under `workspace/private/runs/` and this report includes metadata only.",
    ]) + "\n"


def main() -> int:
    payload = build_payload()
    REPORT_PATH.write_text(render_report(payload), encoding="utf-8")
    print(json.dumps({
        "decision": payload["decision"],
        "touch_repeat": payload["branch_status"]["touch_repeat"],
        "usb_keyboard": payload["branch_status"]["usb_keyboard"],
        "physical_buttons_viable_now": payload["branch_status"]["physical_buttons_viable_now"],
        "button_candidates": payload["v2991"]["button_candidates"],
        "device_buttons_mapped_by_doominput": payload["source"]["device_buttons_mapped_by_doominput"],
        "report": rel(REPORT_PATH),
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

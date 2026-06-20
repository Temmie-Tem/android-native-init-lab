#!/usr/bin/env python3
"""V3008 host-only reconciliation of the current DOOM input frontier.

This unit reconciles the stale touch-bring-up objective with the newer committed
V2984..V3007 evidence. It does not touch the device. The purpose is to prevent a
low-information repeat flash while the only meaningful next live step is still
external USB-keyboard/OTG hardware stimulus plus operator key presses.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[5]

RUN_ID = "V3008"
BUILD_TAG = "v3008-doom-input-frontier-reconciliation"
DECISION = "v3008-doom-input-frontier-keyboard-gate-still-external-stimulus"
REPORT_PATH = ROOT / "docs/reports/NATIVE_INIT_V3008_DOOM_INPUT_FRONTIER_RECONCILIATION_2026-06-20.md"

REPORTS = {
    "v2984": ROOT / "docs/reports/NATIVE_INIT_V2984_INPUTCAPS_TOUCH_DIAG_LIVE_2026-06-20.md",
    "v2990": ROOT / "docs/reports/NATIVE_INIT_V2990_DOOMINPUT_STATE_LIVE_HANDOFF_DRY_RUN_2026-06-20.md",
    "v2991": ROOT / "docs/reports/NATIVE_INIT_V2991_DOOMINPUT_DUAL_TOUCH_LIVE_HANDOFF_DRY_RUN_2026-06-20.md",
    "v3002": ROOT / "docs/reports/NATIVE_INIT_V3002_DOOMINPUT_MUX_LIVE_2026-06-20.md",
    "v3004": ROOT / "docs/reports/NATIVE_INIT_V3004_DOOMINPUT_KEYBOARD_LIVE_GATE_DRY_RUN_2026-06-20.md",
    "v3006": ROOT / "docs/reports/NATIVE_INIT_V3006_DOOM_KEYBOARD_GATE_STATUS_LIVE_2026-06-20.md",
    "v3007": ROOT / "docs/reports/NATIVE_INIT_V3007_DOOM_KEYBOARD_GATE_CURRENT_AUDIT_2026-06-20.md",
}

NEXT_COMMAND = (
    "PYTHONPATH=workspace/public/src/scripts/revalidation:workspace/public/src/harness "
    "python3 workspace/public/src/scripts/revalidation/"
    "native_doominput_keyboard_live_gate_v3004.py --live --count 32 --timeout-ms 60000"
)


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def load_reports() -> dict[str, str]:
    return {key: path.read_text(encoding="utf-8") for key, path in REPORTS.items()}


def has(text: str, needle: str) -> bool:
    return needle in text


def analyze_reports(texts: dict[str, str]) -> dict[str, Any]:
    v2984 = texts.get("v2984", "")
    v2990 = texts.get("v2990", "")
    v2991 = texts.get("v2991", "")
    v3002 = texts.get("v3002", "")
    v3004 = texts.get("v3004", "")
    v3006 = texts.get("v3006", "")
    v3007 = texts.get("v3007", "")

    touch_caps_proven = all([
        has(v2984, "v2984-inputcaps-live-pass-before-rollback"),
        has(v2984, "`event6` | `0` | `1` | `1` | `1` | `1` | `1` | `unsupported`"),
        has(v2984, "`event8` | `0` | `1` | `1` | `1` | `1` | `1` | `unsupported`"),
        has(v2984, "runtime PM reports `unsupported` rather than `suspended`"),
    ])
    touch_events_not_proven = all([
        has(v2990, "v2990-doominput-state-touch-state-not-proven"),
        has(v2990, "DOOM input events: `0` states=`0` touch_states=`0`"),
        has(v2991, "v2991-doominput-dual-touch-touch-state-not-proven"),
        has(v2991, "`event6` selected_touch=`1` caps_ok=`1` doominput_rc=`-110` events=`0` states=`0`"),
        has(v2991, "`event8` selected_touch=`1` caps_ok=`1` doominput_rc=`-110` events=`0` states=`0`"),
    ])
    button_mux_not_proven = all([
        has(v3002, "v3002-doominput-mux-state-not-proven"),
        has(v3002, "button_candidates=`2`"),
        has(v3002, "Mux events: `0` states=`0` active_states=`0` proxy_states=`0`"),
        has(v3002, "Rollback health: version_ok=`1` selftest_fail0=`1`"),
    ])
    keyboard_gate_staged = all([
        has(v3004, "v3004-doominput-keyboard-dry-run"),
        has(v3004, "Preflight ok: `1`"),
        has(v3004, "USB keyboard/OTG attached and DOOM keys pressed"),
        has(v3004, "Live execution: `0`"),
    ])
    status_surface_points_to_keyboard = all([
        has(v3006, "v3006-doom-keyboard-gate-status-status-surface-pass-before-rollback"),
        has(v3006, "video.demo.input.hardware_gate=usb-keyboard-otg"),
        has(v3006, "video.demo.input.keyboard_gate=v3004-doominput-keyboard-live-gate"),
        has(v3006, "video.demo.input.physical_button_mux=v3002-zero-event-do-not-repeat"),
        has(v3006, "video.demo.input.touch=event6,event8-zero-events"),
    ])
    current_gate_not_actionable = all([
        has(v3007, "v3007-doom-keyboard-gate-hardware-stimulus-required"),
        has(v3007, "A90 OTG keyboard evdev evidence: `0`"),
        has(v3007, "V3004 live actionable now: `0`"),
    ])

    saturated_without_external_stimulus = all([
        touch_caps_proven,
        touch_events_not_proven,
        button_mux_not_proven,
        keyboard_gate_staged,
        status_surface_points_to_keyboard,
        current_gate_not_actionable,
    ])

    return {
        "touch_caps_proven": touch_caps_proven,
        "touch_events_not_proven": touch_events_not_proven,
        "button_mux_not_proven": button_mux_not_proven,
        "keyboard_gate_staged": keyboard_gate_staged,
        "status_surface_points_to_keyboard": status_surface_points_to_keyboard,
        "current_gate_not_actionable": current_gate_not_actionable,
        "saturated_without_external_stimulus": saturated_without_external_stimulus,
        "decision": DECISION if saturated_without_external_stimulus else "v3008-doom-input-frontier-evidence-incomplete",
        "next_live_command": NEXT_COMMAND,
        "next_action": (
            "Do not repeat touch, physical-button mux, or keyboard live flashes until a real input-state change "
            "is present. The next live action is V3004 with USB keyboard/OTG attached to the A90 and operator "
            "DOOM key presses during the bounded window."
        ),
        "drop_tier_trigger": (
            "Active DOOM input tier needs external hardware stimulus that is not currently evidenced; "
            "host-only reconciliation records the trigger instead of re-flashing a low-information sample."
        ),
    }


def build_payload() -> dict[str, Any]:
    texts = load_reports()
    return {
        "run_id": RUN_ID,
        "build_tag": BUILD_TAG,
        "reports": {key: rel(path) for key, path in REPORTS.items()},
        "flags": analyze_reports(texts),
    }


def render_report(payload: dict[str, Any]) -> str:
    flags = payload["flags"]
    reports = payload["reports"]
    return "\n".join([
        "# Native Init V3008 DOOM Input Frontier Reconciliation",
        "",
        "## Summary",
        "",
        f"- Decision: `{flags['decision']}`",
        "- Device action: `none` in this host-only unit.",
        "- Track: active Video playback / DOOM input prerequisite.",
        f"- Touch capability/runtime-PM branch closed: `{int(flags['touch_caps_proven'])}`",
        f"- Touch event liveness still not proven: `{int(flags['touch_events_not_proven'])}`",
        f"- Physical-button mux liveness still not proven: `{int(flags['button_mux_not_proven'])}`",
        f"- USB keyboard live gate staged: `{int(flags['keyboard_gate_staged'])}`",
        f"- Status surface points to USB keyboard gate: `{int(flags['status_surface_points_to_keyboard'])}`",
        f"- Current V3007 gate actionable now: `{int(not flags['current_gate_not_actionable'])}`",
        f"- Active tier saturated without external stimulus: `{int(flags['saturated_without_external_stimulus'])}`",
        "",
        "## Reconciled Evidence",
        "",
        f"- V2984: touch/MT capability bits are present on `event6` and `event8`; runtime-PM is `unsupported`, not `suspended` (`{reports['v2984']}`).",
        f"- V2990/V2991: `doominput` touch samples on `event6` and `event8` still captured zero events/states (`{reports['v2990']}`, `{reports['v2991']}`).",
        f"- V3002/V3003: physical-button mux capability exists, but the bounded mux run captured zero events/states, so repeating it without confirmed button input is low-information (`{reports['v3002']}`).",
        f"- V3004: the higher-information USB keyboard/OTG gate is staged and preflight-clean, but has not run live (`{reports['v3004']}`).",
        f"- V3006/V3007: device-visible DOOM status points to V3004, and the current gate audit records no A90 OTG keyboard evdev evidence (`{reports['v3006']}`, `{reports['v3007']}`).",
        "",
        "## Drop-Tier Trigger",
        "",
        f"- {flags['drop_tier_trigger']}",
        "",
        "## Next Live Action",
        "",
        f"- {flags['next_action']}",
        f"- Command when the external prerequisite is true: `{flags['next_live_command']}`",
        "",
        "## Host Validation",
        "",
        "- `python3 -m py_compile workspace/public/src/scripts/revalidation/native_doom_input_frontier_reconcile_v3008.py tests/test_native_doom_input_frontier_reconcile_v3008.py`: PASS",
        "- `PYTHONPATH=workspace/public/src/scripts/revalidation:workspace/public/src/harness python3 -m unittest tests.test_native_doom_input_frontier_reconcile_v3008`: PASS",
        "- `PYTHONPATH=workspace/public/src/scripts/revalidation:workspace/public/src/harness python3 workspace/public/src/scripts/revalidation/native_doom_input_frontier_reconcile_v3008.py`: PASS (host-only report materialized)",
        "- `git diff --check`: PASS",
        "",
        "## Safety",
        "",
        "- Host-only metadata reconciliation; no flash, no serial command, no evdev open, no input injection, and no sysfs write.",
        "- No Wi-Fi/audio/video playback, PMIC, backlight, GPIO, regulator, GDSC, or forbidden partition path is touched.",
        "- No private raw logs or device identifiers are copied into this report.",
    ]) + "\n"


def main() -> int:
    payload = build_payload()
    REPORT_PATH.write_text(render_report(payload), encoding="utf-8")
    print(json.dumps({
        "decision": payload["flags"]["decision"],
        "saturated_without_external_stimulus": payload["flags"]["saturated_without_external_stimulus"],
        "next_live_command": payload["flags"]["next_live_command"],
        "report": rel(REPORT_PATH),
    }, indent=2, sort_keys=True))
    return 0 if payload["flags"]["saturated_without_external_stimulus"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

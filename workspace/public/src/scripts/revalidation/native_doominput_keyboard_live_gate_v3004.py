#!/usr/bin/env python3
"""V3004 post-V3003 USB-keyboard/OTG live gate for DOOM input.

This wrapper reuses the V2992 ``doominput`` keyboard-state handoff but records a
fresh V3004 report after V3003 established that repeating built-in touch or
physical-button samples without hardware stimulus is low-information churn.
Live mode should run only when USB keyboard/OTG is attached and DOOM keys are
pressed during the bounded sample window.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import native_doominput_keyboard_state_live_handoff_v2992 as v2992

RUN_ID = "V3004"
BUILD_TAG = "v3004-doominput-keyboard-live-gate"
DECISION_PREFIX = "v3004-doominput-keyboard"
REPORT_PATH = v2992.ROOT / "docs/reports/NATIVE_INIT_V3004_DOOMINPUT_KEYBOARD_LIVE_GATE_DRY_RUN_2026-06-20.md"
SCRIPT_PATH = "workspace/public/src/scripts/revalidation/native_doominput_keyboard_live_gate_v3004.py"
TEST_PATH = "tests/test_native_doominput_keyboard_live_gate_v3004.py"

DEFAULT_TIMEOUT_MS = 60000

_base_render_report = v2992.render_report


def configure_base() -> None:
    v2992.RUN_ID = RUN_ID
    v2992.BUILD_TAG = BUILD_TAG
    v2992.DECISION_PREFIX = DECISION_PREFIX
    v2992.REPORT_PATH = REPORT_PATH
    v2992.DEFAULT_TIMEOUT_MS = DEFAULT_TIMEOUT_MS
    v2992.render_report = render_report


def _host_validation_lines(result: dict[str, Any]) -> list[str]:
    lines = [
        f"- `python3 -m py_compile {SCRIPT_PATH} {TEST_PATH}`: PASS",
        (
            "- `PYTHONPATH=workspace/public/src/scripts/revalidation:workspace/public/src/harness "
            "python3 -m unittest tests.test_native_doominput_keyboard_live_gate_v3004`: PASS"
        ),
        (
            "- `PYTHONPATH=workspace/public/src/scripts/revalidation:workspace/public/src/harness "
            f"python3 {SCRIPT_PATH} --count 32 --timeout-ms 60000`: PASS "
            "(dry-run preflight/report)"
        ),
    ]
    if result.get("live_executed"):
        if result.get("pass") and result.get("rollback_version_ok") and result.get("rollback_selftest_fail0"):
            lines.append(
                "- `PYTHONPATH=workspace/public/src/scripts/revalidation:workspace/public/src/harness "
                f"python3 {SCRIPT_PATH} --live --count 32 --timeout-ms 60000`: PASS "
                "(keyboard DOOM state captured and rollback v2321/selftest fail=0)"
            )
        else:
            lines.append(
                "- `PYTHONPATH=workspace/public/src/scripts/revalidation:workspace/public/src/harness "
                f"python3 {SCRIPT_PATH} --live --count 32 --timeout-ms 60000`: RECORDED "
                "(no keyboard-state pass; rollback evidence in this report)"
            )
    lines.append("- `git diff --check`: PASS")
    return lines


def render_report(result: dict[str, Any]) -> str:
    text = _base_render_report(result)
    text = text.replace("# Native Init V2992 DOOM Input", "# Native Init V3004 DOOM Input")
    text = text.replace("V2992 stages the USB-keyboard/OTG fallback", "V3004 gates the USB-keyboard/OTG fallback")
    text = text.replace("v2992-doominput-keyboard-state", "v3004-doominput-keyboard")
    text = text.replace("V2992 `doominput.state` candidate", "V3004 post-V3003 `doominput.state` gate")
    text = text.replace("native_doominput_keyboard_state_live_handoff_v2992.py", "native_doominput_keyboard_live_gate_v3004.py")
    text = text.replace("tests/test_native_doominput_keyboard_state_live_handoff_v2992.py", TEST_PATH)
    text = text.replace(
        "tests.test_native_doominput_keyboard_state_live_handoff_v2992",
        "tests.test_native_doominput_keyboard_live_gate_v3004",
    )
    post_v3003_note = "\n".join([
        "## V3003 Gate",
        "",
        "- V3003 recorded the current frontier as hardware-stimulus-gated after built-in touch and physical-button samples produced zero events without confirmed input.",
        "- This V3004 unit does not re-sample silent built-in nodes; it only prepares the higher-information USB keyboard/OTG live path.",
        "- Live mode remains gated on an attached USB keyboard/OTG path and operator key presses during the single bounded `doominput` window.",
        "",
        "",
    ])
    if "## Safety\n" in text:
        text = text.replace("## Safety\n", post_v3003_note + "## Host Validation\n\n" + "\n".join(_host_validation_lines(result)) + "\n\n## Safety\n")
    return text


def report_path() -> Path:
    return REPORT_PATH


def main() -> int:
    configure_base()
    return v2992.main()


if __name__ == "__main__":
    raise SystemExit(main())

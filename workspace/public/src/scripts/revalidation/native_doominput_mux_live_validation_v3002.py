#!/usr/bin/env python3
"""V3002 live validation wrapper for the V2998 DOOM input mux candidate.

This reuses the V2999 mux runner but records a fresh V3002 report so the
original dry-run handoff report remains stable. Live mode still needs the
operator to press VOLUMEUP/VOLUMEDOWN/POWER during the bounded mux window.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import native_doominput_mux_live_handoff_v2999 as v2999

RUN_ID = "V3002"
BUILD_TAG = "v3002-doominput-mux-live"
DECISION_PREFIX = "v3002-doominput-mux"
REPORT_PATH = v2999.ROOT / "docs/reports/NATIVE_INIT_V3002_DOOMINPUT_MUX_LIVE_2026-06-20.md"
SCRIPT_PATH = "workspace/public/src/scripts/revalidation/native_doominput_mux_live_validation_v3002.py"
TEST_PATH = "tests/test_native_doominput_mux_live_validation_v3002.py"

_base_render_report = v2999.render_report


def configure_base() -> None:
    v2999.RUN_ID = RUN_ID
    v2999.BUILD_TAG = BUILD_TAG
    v2999.DECISION_PREFIX = DECISION_PREFIX
    v2999.REPORT_PATH = REPORT_PATH
    v2999.render_report = render_report


def render_report(result: dict[str, Any]) -> str:
    text = _base_render_report(result)
    text = text.replace("# Native Init V2999 DOOM Input", "# Native Init V3002 DOOM Input")
    text = text.replace("V2999 stages live validation", "V3002 runs live validation")
    text = text.replace("v2999-doominput-mux", "v3002-doominput-mux")
    text = text.replace("native_doominput_mux_live_handoff_v2999.py", "native_doominput_mux_live_validation_v3002.py")
    text = text.replace("tests/test_native_doominput_mux_live_handoff_v2999.py", TEST_PATH)
    text = text.replace("tests.test_native_doominput_mux_live_handoff_v2999", "tests.test_native_doominput_mux_live_validation_v3002")
    text = text.replace(
        f"`PYTHONPATH=workspace/public/src/scripts/revalidation:workspace/public/src/harness python3 {SCRIPT_PATH} --count 24 --timeout-ms 45000`: PASS (dry-run preflight/report)",
        f"`PYTHONPATH=workspace/public/src/scripts/revalidation:workspace/public/src/harness python3 {SCRIPT_PATH} --events event3,event0 --count 24 --timeout-ms 60000`: PASS (dry-run preflight/report)",
    )
    live_line = None
    if result.get("live_executed"):
        if result.get("pass") and result.get("rollback_version_ok") and result.get("rollback_selftest_fail0"):
            live_line = (
                f"- `PYTHONPATH=workspace/public/src/scripts/revalidation:workspace/public/src/harness python3 {SCRIPT_PATH} "
                "--live --events event3,event0 --count 24 --timeout-ms 60000`: PASS "
                "(proxy state captured and rollback v2321/selftest fail=0)"
            )
        else:
            live_line = (
                f"- `PYTHONPATH=workspace/public/src/scripts/revalidation:workspace/public/src/harness python3 {SCRIPT_PATH} "
                "--live --events event3,event0 --count 24 --timeout-ms 60000`: RECORDED "
                "(no proxy-state pass; rollback evidence in this report)"
            )
    if live_line is not None:
        text = text.replace("- `git diff --check`: PASS", live_line + "\n- `git diff --check`: PASS")
    return text


def report_path() -> Path:
    return REPORT_PATH


def main() -> int:
    configure_base()
    return v2999.main()


if __name__ == "__main__":
    raise SystemExit(main())

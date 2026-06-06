#!/usr/bin/env python3
"""V902 bounded mdm_helper/ks blocker-capture proof.

This reuses the V900 live contract runner with helper v146. The live action is
the same ordered `mdm_helper` before `/dev/subsys_esoc0` contract, but helper
v146 captures `/proc/<trigger_pid>` wchan/status/stat/sched/stack evidence
before cleanup when the subsystem-open child blocks.
"""

from __future__ import annotations

from pathlib import Path

import native_wifi_mdm_helper_ks_contract_live_v900 as base


base.DEFAULT_OUT_DIR = Path("tmp/wifi/v902-mdm-helper-ks-blocker-capture-live")
base.LATEST_POINTER = Path("tmp/wifi/latest-v902-mdm-helper-ks-blocker-capture-live.txt")
base.DEFAULT_LOCAL_HELPER = Path("tmp/wifi/v902-execns-helper-v146-build/a90_android_execns_probe")
base.DEFAULT_HELPER_SHA256 = "8c095b2a151eb80000bb1b6bf71d23dbab805db5166ba5b453a87fbc80cce256"
base.DEFAULT_HELPER_MARKER = "a90_android_execns_probe v146"

_base_decide = base.decide
_base_render_summary = base.render_summary


def decide(args, local, steps, analysis):  # type: ignore[no-untyped-def]
    decision, pass_ok, reason, next_step = _base_decide(args, local, steps, analysis)
    decision = decision.replace("v900", "v902")
    if next_step == "inspect pre-reboot evidence and plan safer reduced live contract":
        next_step = "classify captured wchan/stack and select the next lower trigger"
    elif "V900" in next_step:
        next_step = next_step.replace("V900", "V902")
    return decision, pass_ok, reason, next_step


def render_summary(manifest):  # type: ignore[no-untyped-def]
    return _base_render_summary(manifest).replace(
        "# V900 mdm_helper/ks Contract Live Proof",
        "# V902 mdm_helper/ks Blocker Capture Proof",
    ).replace("V900", "V902").replace("v900", "v902")


base.decide = decide
base.render_summary = render_summary


if __name__ == "__main__":
    raise SystemExit(base.main())

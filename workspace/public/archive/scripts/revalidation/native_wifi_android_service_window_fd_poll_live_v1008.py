#!/usr/bin/env python3
"""V1008 bounded live proof for helper v171 service-window fd-poll mode."""

from __future__ import annotations

from pathlib import Path

import native_wifi_android_service_window_subsys_trigger_live_v1004 as v1004


base = v1004.base
ORIGINAL_DECIDE = v1004.decide
ORIGINAL_RENDER_SUMMARY = v1004.render_summary

base.DEFAULT_OUT_DIR = Path("tmp/wifi/v1008-android-service-window-fd-poll-live")
base.LATEST_POINTER = Path("tmp/wifi/latest-v1008-android-service-window-fd-poll-live.txt")
base.DEFAULT_LOCAL_HELPER = Path("tmp/wifi/v1006-execns-helper-v171-build/a90_android_execns_probe")
base.DEFAULT_HELPER_SHA256 = "347f38ab24d67bf300bd6dccd033a081328ec5afdd711b49f3d0d2f9328cf3a1"
base.DEFAULT_HELPER_MARKER = "a90_android_execns_probe v171"


def decide(args, local, steps, analysis):
    decision, pass_ok, reason, next_step = ORIGINAL_DECIDE(args, local, steps, analysis)
    return (
        decision.replace("v1004", "v1008").replace("v170", "v171"),
        pass_ok,
        reason.replace("v1004", "v1008").replace("V1004", "V1008").replace("v170", "v171"),
        next_step.replace("v1004", "v1008").replace("V1004", "V1008").replace("v170", "v171"),
    )


def render_summary(manifest):
    return (
        ORIGINAL_RENDER_SUMMARY(manifest)
        .replace("V1004 Android Service-Window Subsys Trigger Live", "V1008 Android Service-Window fd Poll Live")
        .replace("V1004", "V1008")
        .replace("v1004", "v1008")
        .replace("helper v170", "helper v171")
        .replace("a90_android_execns_probe v170", "a90_android_execns_probe v171")
    )


v1004.decide = decide
v1004.render_summary = render_summary
base.decide = decide
base.render_summary = render_summary
v1004.v923.decide = decide
v1004.v923.render_summary = render_summary


if __name__ == "__main__":
    raise SystemExit(base.main())

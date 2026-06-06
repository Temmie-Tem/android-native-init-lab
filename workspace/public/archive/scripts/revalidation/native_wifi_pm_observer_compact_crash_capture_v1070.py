#!/usr/bin/env python3
"""V1070 PM observer compact service-manager crash capture.

This reuses the V1066 PM observer harness with helper v188 and appends
`--capture-mode ptrace-lite`. The helper traces only the service-manager trio
inside the PM observer and uses compact crash/observable output so the bounded
NCM transcript reaches the final summary.
"""

from __future__ import annotations

from pathlib import Path

import native_wifi_pm_service_trigger_observer_live_v1066 as base


base.DEFAULT_LOCAL_HELPER = Path("tmp/wifi/v1070-execns-helper-v188-build/a90_android_execns_probe")
base.DEFAULT_HELPER_MARKER = "a90_android_execns_probe v188"
base.DEFAULT_HELPER_SHA256 = ""
base.DEFAULT_OUT_DIR = Path("tmp/wifi/v1070-pm-observer-compact-crash-capture-live")

_orig_helper_command = base.helper_command


def helper_command(args: base.argparse.Namespace) -> list[str]:
    command = _orig_helper_command(args)
    if len(command) >= 3 and command[0] == args.toybox and command[1] == "timeout":
        command = command[3:]
    try:
        mode_index = command.index("--mode")
    except ValueError:
        mode_index = len(command)
    command[mode_index:mode_index] = ["--capture-mode", "ptrace-lite"]
    return command


base.helper_command = helper_command


if __name__ == "__main__":
    raise SystemExit(base.main())

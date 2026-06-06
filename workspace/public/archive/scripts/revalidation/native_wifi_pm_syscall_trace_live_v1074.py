#!/usr/bin/env python3
"""V1074 bounded PM-service syscall trace live gate."""

from __future__ import annotations

from pathlib import Path

import native_wifi_pm_service_trigger_observer_live_v1066 as base


base.DEFAULT_OUT_DIR = Path("tmp/wifi/v1074-pm-service-syscall-trace-live")
base.LATEST_POINTER = Path("tmp/wifi/latest-v1074-pm-service-syscall-trace-live.txt")
base.DEFAULT_LOCAL_HELPER = Path("tmp/wifi/v1074-execns-helper-v196-build/a90_android_execns_probe")
base.DEFAULT_HELPER_SHA256 = "61b8ac54460f05e1d3a6fc6b68d8873c04537c171054921b4266be1ef6a0fb59"
base.DEFAULT_HELPER_MARKER = "a90_android_execns_probe v196"

_base_decide = base.decide
_base_render_summary = base.render_summary
_base_helper_command = base.helper_command


def _contract_int(contract: dict[str, str], key: str, default: int = 0) -> int:
    try:
        return int(contract.get(key, str(default)), 10)
    except ValueError:
        return default


def decide(args, local, steps, analysis):  # type: ignore[no-untyped-def]
    base_decision, base_pass, base_reason, base_next = _base_decide(args, local, steps, analysis)
    if args.command == "plan":
        if base_pass:
            return (
                "v1074-pm-service-syscall-trace-plan-ready",
                True,
                "plan-only; helper v196 and observer mode are locally present",
                "deploy helper v196 and run bounded V1074 syscall trace",
            )
        return base_decision.replace("v1066", "v1074"), base_pass, base_reason, base_next

    helper = analysis.get("helper") or {}
    contract = helper.get("contract") or {}
    per_mgr_trace_syscalls = (
        contract.get("child.per_mgr.trace_syscalls") == "1"
        or contract.get("child.per_mgr.syscall_trace_started") == "1"
    )
    per_mgr_records = _contract_int(contract, "child.per_mgr.syscall_record_count")
    per_mgr_stops = _contract_int(contract, "child.per_mgr.syscall_stop_count")
    per_mgr_exit = contract.get("child.per_mgr.exit_code")
    if not base_pass:
        return base_decision.replace("v1066", "v1074"), base_pass, base_reason, base_next
    if not per_mgr_trace_syscalls:
        return (
            "v1074-pm-service-syscall-trace-missing",
            False,
            "per_mgr syscall trace was not started",
            "audit helper v196 trace selection before retry",
        )
    if per_mgr_records <= 0:
        return (
            "v1074-pm-service-syscall-records-missing",
            False,
            f"syscall_stop_count={per_mgr_stops} syscall_record_count={per_mgr_records}",
            "inspect ptrace stop handling before another live gate",
        )
    return (
        "v1074-pm-service-syscall-boundary-captured",
        True,
        f"per_mgr_exit={per_mgr_exit} syscall_stop_count={per_mgr_stops} syscall_record_count={per_mgr_records}",
        "classify captured open/socket/bind/connect/ioctl/exit records for the next PM input repair",
    )


def render_summary(manifest):  # type: ignore[no-untyped-def]
    text = _base_render_summary(manifest)
    return text.replace("# V1066 PM-Service Trigger Observer Live", "# V1074 PM-Service Syscall Trace Live")


def helper_command(args):  # type: ignore[no-untyped-def]
    command = _base_helper_command(args)
    if len(command) >= 3 and command[0] == args.toybox and command[1] == "timeout":
        command = command[3:]
    try:
        mode_index = command.index("--mode")
    except ValueError:
        mode_index = len(command)
    command[mode_index:mode_index] = ["--capture-mode", "ptrace-lite"]
    return command


base.decide = decide
base.render_summary = render_summary
base.helper_command = helper_command


if __name__ == "__main__":
    raise SystemExit(base.main())

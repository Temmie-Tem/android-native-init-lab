#!/usr/bin/env python3
"""V484 Samsung Wi-Fi HAL abort capture with private property-service shim.

This runner keeps the V483 bounded registration scope, but switches the helper
mode to trace only the Samsung Wi-Fi HAL child. It captures a compact ptrace
crash snapshot when the HAL aborts. It does not scan, connect, link up, read
credentials, run DHCP, change routes, or send external pings.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import native_samsung_wifi_registration_v483 as v483


base = v483.base

base.__doc__ = __doc__
base.DEFAULT_OUT_DIR = Path("tmp/wifi/v484-samsung-wifi-hal-abort-capture")
base.DEFAULT_HELPER_SHA256 = "1b061faf5031225066d5d58fdef32512b488b72520a2d828a148c5466972ba49"
base.HELPER_LABEL = "v43"
base.APPROVAL_PHRASE = (
    "approve v484 Samsung Wi-Fi HAL ptrace abort capture only; "
    "no scan/connect/link-up and no Wi-Fi bring-up"
)

CAPTURE_KEY_RE = re.compile(r"^capture\.([A-Za-z0-9_.]+)=(.*)$")

_BASE_BUILD_HELPER_ARGV = base.build_helper_argv
_BASE_BUILD_PLAN = base.build_plan
_BASE_DECIDE = base.decide
_BASE_REFUSAL_MANIFEST = base.refusal_manifest
_BASE_RENDER_SUMMARY = base.render_summary
_BASE_RUN_LIVE = v483.v479.v473.v469.v467.run_live


def build_helper_argv(args: base.argparse.Namespace, *, include_data_wifi: bool = False) -> list[str]:
    argv = _BASE_BUILD_HELPER_ARGV(args, include_data_wifi=include_data_wifi)
    for index, value in enumerate(argv):
        if value == "wifi-surface-composite-lshal-wait-samsung":
            argv[index] = "wifi-surface-composite-lshal-wait-samsung-ptrace"
            break
    return argv


def parse_capture_keys(text: str) -> dict[str, str]:
    keys: dict[str, str] = {}
    for raw_line in text.splitlines():
        match = CAPTURE_KEY_RE.match(raw_line.strip())
        if match:
            keys[match.group(1)] = match.group(2).strip()
    return keys


def run_live(args: base.argparse.Namespace, store: base.EvidenceStore) -> dict[str, Any]:
    live = _BASE_RUN_LIVE(args, store)
    file_name = live.get("file")
    text = ""
    if isinstance(file_name, str):
        path = store.path(file_name)
        if path.exists():
            text = path.read_text(encoding="utf-8", errors="replace")
    live["capture_keys"] = parse_capture_keys(text)
    live["wifi_hal_trace"] = {
        key.removeprefix("child.wifi_hal."): value
        for key, value in (live.get("keys") or {}).items()
        if key.startswith("child.wifi_hal.") and (
            "trace" in key or "capture" in key or key.endswith(".signal")
        )
    }
    live["crash_captured"] = (
        (live.get("keys") or {}).get("child.wifi_hal.capture_crash") == "1"
        or live["capture_keys"].get("crash.siginfo.signo") == "6"
    )
    return live


def build_plan(args: base.argparse.Namespace) -> dict[str, Any]:
    plan = _BASE_BUILD_PLAN(args)
    plan["helper_version"] = base.HELPER_LABEL
    plan["helper_mode"] = "wifi-surface-composite-lshal-wait-samsung-ptrace"
    plan["ptrace_abort_capture"] = {
        "traced_child": "vendor.samsung.hardware.wifi@2.0-service only",
        "captures": [
            "SIGABRT siginfo",
            "selected AArch64 registers",
            "stack ASCII scan",
            "PC/LR map rows",
            "bounded frame chain",
            "maps and mountinfo excerpts",
        ],
        "still_blocked": [
            "Wi-Fi scan/connect/link-up",
            "credential reads",
            "DHCP/routing/external ping",
        ],
    }
    return plan


def _v484_label(decision: str) -> str:
    return (
        decision
        .replace("v483-samsung-registration-property-shim", "v484-samsung-wifi-hal-abort-capture")
        .replace("v479-samsung-wifi-registration-selinux-context", "v484-samsung-wifi-hal-abort-capture")
        .replace("v473-samsung-wifi-registration-v471-property", "v484-samsung-wifi-hal-abort-capture")
        .replace("v469-samsung-wifi-registration", "v484-samsung-wifi-hal-abort-capture")
    )


def decide(args: base.argparse.Namespace, checks: list[base.Check], live_result: dict[str, Any] | None,
           post: dict[str, Any] | None) -> tuple[str, bool, str, str, bool]:
    decision, pass_ok, reason, next_step, daemon_started = _BASE_DECIDE(args, checks, live_result, post)
    if args.command == "run" and live_result and post and post.get("clean"):
        keys = live_result.get("keys") or {}
        capture_keys = live_result.get("capture_keys") or {}
        if live_result.get("crash_captured") and keys.get("child.wifi_hal.signal") == "6":
            pc_map = capture_keys.get("crash.maprow.pc.path", "")
            lr_map = capture_keys.get("crash.maprow.lr.path", "")
            return (
                "v484-samsung-wifi-hal-abort-capture-pass",
                True,
                f"captured Samsung Wi-Fi HAL SIGABRT with pc={pc_map or 'unknown'} lr={lr_map or 'unknown'}",
                "classify abort frame against Android boot-complete runtime before scan/connect",
                daemon_started,
            )
    return (
        _v484_label(decision),
        pass_ok,
        reason.replace("V483", "V484").replace("v42", "v43"),
        next_step.replace("V483", "V484").replace("v42", "v43"),
        daemon_started,
    )


def refusal_manifest(args: base.argparse.Namespace, android_manifest: dict[str, Any]) -> dict[str, Any]:
    manifest = _BASE_REFUSAL_MANIFEST(args, android_manifest)
    manifest["decision"] = _v484_label(str(manifest["decision"]))
    manifest["next_step"] = "rerun with exact V484 approval after helper v43 deploy"
    manifest["required_approval_phrase"] = base.APPROVAL_PHRASE
    return manifest


def render_summary(manifest: dict[str, Any]) -> str:
    return _BASE_RENDER_SUMMARY(manifest).replace(
        "# V483 Samsung ISehWifi/default Registration With Private Property-Service Shim",
        "# V484 Samsung Wi-Fi HAL Abort Capture",
        1,
    )


base.build_helper_argv = build_helper_argv
base.build_plan = build_plan
base.decide = decide
base.refusal_manifest = refusal_manifest
base.render_summary = render_summary
v483.v479.v473.v469.build_helper_argv = build_helper_argv
v483.v479.v473.v469.build_plan = build_plan
v483.v479.v473.v469.decide = decide
v483.v479.v473.v469.refusal_manifest = refusal_manifest
v483.v479.v473.v469.render_summary = render_summary
v483.v479.v473.v469.v467.run_live = run_live


if __name__ == "__main__":
    raise SystemExit(base.main())

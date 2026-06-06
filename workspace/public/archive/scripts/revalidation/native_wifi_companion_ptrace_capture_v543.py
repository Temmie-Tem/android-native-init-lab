#!/usr/bin/env python3
"""V543 bounded companion cnss-daemon ptrace capture.

This is a V534 successor that keeps the same bounded companion start-only
contract, but passes `--capture-mode ptrace-lite` so the helper traces only the
`cnss-daemon` child and records the abort stop. It does not start
service-manager, Wi-Fi HAL, scan/connect/link-up, DHCP, routing, or external
ping.
"""

from __future__ import annotations

import re
from dataclasses import asdict
from typing import Any

import native_wifi_companion_start_only_v534 as v534


base = v534.base
base.__doc__ = __doc__
base.DEFAULT_OUT_DIR = base.Path("tmp/wifi/v543-companion-cnss-ptrace-capture")
base.DEFAULT_HELPER_SHA256 = "30c15d7dc33f537753ab0aecd45280a598e6d480340c6fb6f53f26573a96d2cd"
base.DEFAULT_HELPER_MARKER = "a90_android_execns_probe v72"
base.PROOF_VERSION = "V543"
base.PROOF_SLUG = "v543-companion-cnss-ptrace-capture"
base.LIVE_HELPER_STEP_NAME = "v543-helper-run"
base.APPROVAL_PHRASE = (
    "approve v543 companion cnss-daemon ptrace capture only; "
    "no service-manager, no Wi-Fi HAL start, no scan/connect/link-up and no external ping"
)
base.KEY_RE = re.compile(
    r"^(wifi_companion_start|wifi_hal_composite_start|wifi_hal_composite_child|capture)\.([A-Za-z0-9_.-]+)=(.*)$"
)

_orig_helper_command = base.helper_command
_orig_run_live = base.run_live
_orig_render_summary = base.render_summary
_orig_build_manifest = base.build_manifest
_orig_classify = base.classify


def helper_command(args: base.argparse.Namespace) -> list[str]:
    command = _orig_helper_command(args)
    command.extend(["--capture-mode", "ptrace-lite"])
    return command


def _trace_rows(keys: dict[str, str]) -> list[list[str]]:
    rows: list[list[str]] = []
    for key in sorted(keys):
        if key.startswith("capture.") or ".trace." in key or key.endswith(".traced"):
            rows.append([key, keys[key]])
    return rows


def run_live(args: base.argparse.Namespace, store: base.EvidenceStore) -> dict[str, Any]:
    result = _orig_run_live(args, store)
    result["trace_keys"] = _trace_rows(result.get("keys") or {})
    return result


def classify(args: base.argparse.Namespace,
             checks: list[base.Check],
             live_result: dict[str, Any] | None,
             dmesg: dict[str, Any]) -> tuple[str, bool, str, str, bool]:
    decision, pass_ok, reason, next_step, live_executed = _orig_classify(args, checks, live_result, dmesg)
    keys = (live_result or {}).get("keys") or {}
    if (
        args.command == "run"
        and pass_ok
        and keys.get("wifi_hal_composite_start.child.cnss_daemon.trace.crash_stop") == "1"
    ):
        return (
            "v543-companion-cnss-ptrace-captured",
            True,
            "cnss-daemon SIGABRT was captured by ptrace-lite during bounded companion replay",
            "classify crash PC/LR/maps and patch the next missing runtime surface",
            live_executed,
        )
    return decision, pass_ok, reason, next_step, live_executed


def render_summary(manifest: dict[str, Any]) -> str:
    text = _orig_render_summary(manifest)
    live = manifest.get("live_result") or {}
    trace_rows = live.get("trace_keys") or []
    extra = "\n".join([
        "## Cnss Ptrace Keys",
        "",
        base.markdown_table(["key", "value"], trace_rows[:160]) if trace_rows else "- none",
        "",
    ])
    return text.replace("## Evidence\n\n", extra + "## Evidence\n\n")


def build_manifest(args: base.argparse.Namespace, store: base.EvidenceStore) -> dict[str, Any]:
    manifest = _orig_build_manifest(args, store)
    manifest["ptrace_capture"] = {
        "target_child": "cnss-daemon",
        "capture_mode": "ptrace-lite",
        "scope": "bounded companion start-only; no service-manager, no Wi-Fi HAL, no scan/connect/link-up",
    }
    manifest["checks"] = [asdict(check) if hasattr(check, "name") else check for check in manifest["checks"]]
    return manifest


base.helper_command = helper_command
base.run_live = run_live
base.classify = classify
base.render_summary = render_summary
base.build_manifest = build_manifest


if __name__ == "__main__":
    raise SystemExit(base.main())

#!/usr/bin/env python3
"""Build a read-only A90 tracefs/pstore debug observability plan."""

from __future__ import annotations

import argparse
import datetime as dt
from pathlib import Path
from typing import Any

from a90_kernel_tools import (
    DEFAULT_EXPECT_VERSION,
    REPO_ROOT,
    capture_to_manifest,
    collect_host_metadata,
    config_enabled,
    config_state,
    fetch_kernel_config,
    markdown_table,
    repo_path,
    run_capture,
    strip_cmdv1_text,
    write_private_json,
    write_private_text,
)


CONFIG_OPTIONS = [
    "CONFIG_TRACEFS_FS",
    "CONFIG_TRACING",
    "CONFIG_FTRACE",
    "CONFIG_FUNCTION_TRACER",
    "CONFIG_FUNCTION_GRAPH_TRACER",
    "CONFIG_DYNAMIC_FTRACE",
    "CONFIG_EVENT_TRACING",
    "CONFIG_TRACEPOINTS",
    "CONFIG_KPROBES",
    "CONFIG_KPROBE_EVENTS",
    "CONFIG_DEBUG_FS",
    "CONFIG_USB_MON",
    "CONFIG_PSTORE",
    "CONFIG_PSTORE_CONSOLE",
    "CONFIG_PSTORE_PMSG",
    "CONFIG_PSTORE_RAM",
    "CONFIG_PSTORE_FTRACE",
    "CONFIG_RAMOOPS",
]


def default_out() -> Path:
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return REPO_ROOT / "tmp" / "debug-observability" / f"a90-debug-observability-{stamp}.md"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=54321)
    parser.add_argument("--timeout", type=float, default=45.0)
    parser.add_argument("--expect-version", default=DEFAULT_EXPECT_VERSION)
    parser.add_argument("--out", type=Path, default=default_out())
    parser.add_argument("--json-out", type=Path)
    return parser.parse_args()


def has_text(capture_text: str, needle: str) -> bool:
    return needle in strip_cmdv1_text(capture_text)


def build_report(args: argparse.Namespace,
                 captures: list[Any],
                 config: dict[str, str]) -> tuple[str, dict[str, Any], bool]:
    by_name = {capture.name: capture for capture in captures}
    version_matches = args.expect_version in by_name["version"].text
    tracefs_text = strip_cmdv1_text(by_name["tracefs-full"].text)
    pstore_text = strip_cmdv1_text(by_name["pstore-full"].text)
    tracefs_supported = has_text(tracefs_text, "fs_tracefs=yes") and config_enabled(config, "CONFIG_TRACING")
    tracefs_mounted = has_text(tracefs_text, "mount_tracefs=yes")
    pstore_supported = has_text(pstore_text, "fs_pstore=yes") and config_enabled(config, "CONFIG_PSTORE")
    pstore_mounted = has_text(pstore_text, "mounted=yes")
    usbmon_supported = config_enabled(config, "CONFIG_USB_MON")
    debugfs_supported = config_enabled(config, "CONFIG_DEBUG_FS")
    pass_ok = version_matches and bool(config) and by_name["tracefs-full"].ok and by_name["pstore-full"].ok

    config_rows = [[option, config_state(config, option)] for option in CONFIG_OPTIONS]
    state_rows = [
        ["tracefs support", "yes" if tracefs_supported else "no"],
        ["tracefs mounted", "yes" if tracefs_mounted else "no"],
        ["pstore support", "yes" if pstore_supported else "no"],
        ["pstore mounted", "yes" if pstore_mounted else "no"],
        ["debugfs support", "yes" if debugfs_supported else "no"],
        ["usbmon support", "yes" if usbmon_supported else "no"],
    ]
    plan_rows = [
        [
            "tracefs mount probe",
            "opt-in-safe-candidate" if tracefs_supported and not tracefs_mounted else "already-mounted" if tracefs_mounted else "blocked",
            "Mount state changes kernel debugfs namespace; do only under explicit debug session.",
        ],
        [
            "ftrace current_tracer/tracing_on",
            "blocked-by-default",
            "Writes are active tracing state changes; require short bounded diagnostic plan.",
        ],
        [
            "pstore mount/read entries",
            "opt-in-safe-candidate" if pstore_supported and not pstore_mounted else "already-mounted" if pstore_mounted else "blocked",
            "Mount/read only; no entry deletion; useful after crashes/reboots.",
        ],
        [
            "pstore reboot persistence test",
            "maintenance-window-only",
            "Requires reboot cycle and comparison before/after; not part of normal validation.",
        ],
        [
            "debugfs broad mount",
            "blocked-by-default" if debugfs_supported else "unsupported",
            "debugfs exposes many mutable controls; prefer tracefs-specific plan first.",
        ],
        [
            "usbmon",
            "candidate-if-needed" if usbmon_supported else "kernel-missing",
            "Useful for USB drops only if kernel support and safe capture policy exist.",
        ],
    ]
    guardrail_rows = [
        ["default", "read-only `tracefs full`, `pstore full`, config decode only"],
        ["forbid", "watchdog open, crash trigger, fault injection, current_tracer write, tracing_on write"],
        ["require", "explicit opt-in plan, duration limit, rollback, native log + host bundle evidence"],
        ["fallback", "ACM bridge remains rescue path; do not run during flash/recovery work"],
    ]
    manifest = {
        "created": dt.datetime.now(dt.timezone.utc).isoformat(),
        "expect_version": args.expect_version,
        "version_matches": version_matches,
        "pass": pass_ok,
        "state": {
            "tracefs_supported": tracefs_supported,
            "tracefs_mounted": tracefs_mounted,
            "pstore_supported": pstore_supported,
            "pstore_mounted": pstore_mounted,
            "debugfs_supported": debugfs_supported,
            "usbmon_supported": usbmon_supported,
        },
        "kernel": {option: config_state(config, option) for option in CONFIG_OPTIONS},
        "host": collect_host_metadata(),
        "captures": [capture_to_manifest(capture) for capture in captures],
    }
    lines = [
        "# A90 Tracefs / Pstore Debug Observability Plan",
        "",
        "## Summary",
        "",
        f"- result: {'PASS' if pass_ok else 'FAIL'}",
        f"- expected version: `{args.expect_version}`",
        f"- version matches: `{version_matches}`",
        "- policy: read-only plan generation; no mount, no tracing enable, no pstore delete, no reboot",
        "",
        "## Current State",
        "",
        markdown_table(["item", "state"], state_rows),
        "",
        "## Opt-in Plan Matrix",
        "",
        markdown_table(["feature", "classification", "reason"], plan_rows),
        "",
        "## Guardrails",
        "",
        markdown_table(["type", "rule"], guardrail_rows),
        "",
        "## Kernel Config",
        "",
        markdown_table(["CONFIG", "state"], config_rows),
        "",
        "## Device Evidence",
        "",
        "### tracefs full",
        "",
        "```text",
        tracefs_text.strip(),
        "```",
        "",
        "### pstore full",
        "",
        "```text",
        pstore_text.strip(),
        "```",
        "",
    ]
    return "\n".join(lines), manifest, pass_ok


def main() -> int:
    args = parse_args()
    captures = [run_capture(args, "version", ["version"], timeout=15.0)]
    config_capture, _config_text, config = fetch_kernel_config(args)
    captures.append(config_capture)
    captures.append(run_capture(args, "tracefs-full", ["tracefs", "full"], timeout=15.0))
    captures.append(run_capture(args, "pstore-full", ["pstore", "full"], timeout=15.0))

    report, manifest, pass_ok = build_report(args, captures, config)
    output = repo_path(args.out)
    json_output = repo_path(args.json_out) if args.json_out else output.with_suffix(".json")
    write_private_text(output, report.rstrip() + "\n")
    write_private_json(json_output, manifest)
    print(f"{'PASS' if pass_ok else 'FAIL'} out={output} json={json_output}")
    return 0 if pass_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Collect read-only A90 cgroup and PSI resource-control inventory."""

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
    "CONFIG_CGROUPS",
    "CONFIG_CGROUP_FREEZER",
    "CONFIG_CGROUP_PIDS",
    "CONFIG_CGROUP_CPUACCT",
    "CONFIG_CGROUP_DEVICE",
    "CONFIG_CPUSETS",
    "CONFIG_MEMCG",
    "CONFIG_BLK_CGROUP",
    "CONFIG_CGROUP_SCHED",
    "CONFIG_FAIR_GROUP_SCHED",
    "CONFIG_RT_GROUP_SCHED",
    "CONFIG_CGROUP_BPF",
    "CONFIG_PSI",
    "CONFIG_NAMESPACES",
    "CONFIG_PID_NS",
    "CONFIG_NET_NS",
]

PROC_COMMANDS: tuple[tuple[str, list[str]], ...] = (
    ("proc-cgroups", ["run", "/cache/bin/toybox", "cat", "/proc/cgroups"]),
    ("self-cgroup", ["run", "/cache/bin/toybox", "cat", "/proc/self/cgroup"]),
    ("psi-cpu", ["run", "/cache/bin/toybox", "cat", "/proc/pressure/cpu"]),
    ("psi-memory", ["run", "/cache/bin/toybox", "cat", "/proc/pressure/memory"]),
    ("psi-io", ["run", "/cache/bin/toybox", "cat", "/proc/pressure/io"]),
    ("sysfs-cgroup-ls", ["run", "/cache/bin/toybox", "ls", "-ld", "/sys/fs/cgroup", "/dev/cpuset", "/dev/memcg", "/acct"]),
)


def default_out() -> Path:
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return REPO_ROOT / "tmp" / "cgroup-psi" / f"a90-cgroup-psi-{stamp}.md"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=54321)
    parser.add_argument("--timeout", type=float, default=45.0)
    parser.add_argument("--expect-version", default=DEFAULT_EXPECT_VERSION)
    parser.add_argument("--out", type=Path, default=default_out())
    parser.add_argument("--json-out", type=Path)
    return parser.parse_args()


def clean_lines(text: str) -> list[str]:
    return [line.strip() for line in strip_cmdv1_text(text).splitlines() if line.strip()]


def parse_proc_cgroups(text: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for line in clean_lines(text):
        if line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) == 4:
            rows.append({
                "subsys": parts[0],
                "hierarchy": parts[1],
                "num_cgroups": parts[2],
                "enabled": parts[3],
            })
    return rows


def parse_psi(text: str) -> list[str]:
    return clean_lines(text)


def mounted_cgroup_lines(mounts_text: str) -> list[str]:
    lines = []
    for line in strip_cmdv1_text(mounts_text).splitlines():
        parts = line.split()
        if len(parts) >= 3 and parts[2] in {"cgroup", "cgroup2"}:
            lines.append(line)
    return lines


def build_report(args: argparse.Namespace,
                 captures: list[Any],
                 config: dict[str, str]) -> tuple[str, dict[str, Any], bool]:
    by_name = {capture.name: capture for capture in captures}
    version_matches = args.expect_version in by_name["version"].text
    config_ok = bool(config)
    cgroups = parse_proc_cgroups(by_name["proc-cgroups"].text)
    enabled_controllers = [row["subsys"] for row in cgroups if row["enabled"] == "1"]
    psi = {
        "cpu": parse_psi(by_name["psi-cpu"].text),
        "memory": parse_psi(by_name["psi-memory"].text),
        "io": parse_psi(by_name["psi-io"].text),
    }
    cgroup_mounts = mounted_cgroup_lines(by_name["mounts"].text)
    cgroup_supported = config_enabled(config, "CONFIG_CGROUPS") and bool(cgroups)
    psi_supported = config_enabled(config, "CONFIG_PSI") and all(psi.values())
    decision = (
        "supported-unmounted-psi-present"
        if cgroup_supported and psi_supported and not cgroup_mounts
        else "supported-mounted-psi-present"
        if cgroup_supported and psi_supported and cgroup_mounts
        else "partial"
    )
    pass_ok = version_matches and config_ok and cgroup_supported and psi_supported

    config_rows = [[option, config_state(config, option)] for option in CONFIG_OPTIONS]
    controller_rows = [[row["subsys"], row["enabled"], row["hierarchy"], row["num_cgroups"]] for row in cgroups]
    psi_rows = [[name, "<br>".join(lines)] for name, lines in psi.items()]
    mount_rows = [[line] for line in cgroup_mounts] or [["(no cgroup/cgroup2 mounts)"]]
    isolation_rows = [
        ["tcpctl/rshell helper limit", "possible-after-explicit-cgroup-mount-plan" if cgroup_supported else "blocked"],
        ["CPU pressure observation", "available" if psi["cpu"] else "missing"],
        ["Memory pressure observation", "available" if psi["memory"] else "missing"],
        ["I/O pressure observation", "available" if psi["io"] else "missing"],
        ["PID/process count controller", "kernel-missing" if config_state(config, "CONFIG_CGROUP_PIDS") in {"n", "unset"} else "available"],
        ["device controller", "kernel-missing" if config_state(config, "CONFIG_CGROUP_DEVICE") in {"n", "unset"} else "available"],
    ]

    manifest = {
        "created": dt.datetime.now(dt.timezone.utc).isoformat(),
        "expect_version": args.expect_version,
        "version_matches": version_matches,
        "pass": pass_ok,
        "decision": decision,
        "controllers": cgroups,
        "enabled_controllers": enabled_controllers,
        "psi": psi,
        "cgroup_mounts": cgroup_mounts,
        "kernel": {option: config_state(config, option) for option in CONFIG_OPTIONS},
        "host": collect_host_metadata(),
        "captures": [capture_to_manifest(capture) for capture in captures],
    }
    lines = [
        "# A90 Cgroup / PSI Resource Control Inventory",
        "",
        "## Summary",
        "",
        f"- result: {'PASS' if pass_ok else 'FAIL'}",
        f"- decision: `{decision}`",
        f"- expected version: `{args.expect_version}`",
        f"- version matches: `{version_matches}`",
        f"- enabled controllers: `{', '.join(enabled_controllers)}`",
        "- policy: read-only; no cgroup mount, no cgroup writes, no process migration",
        "",
        "## Runtime Controllers",
        "",
        markdown_table(["controller", "enabled", "hierarchy", "num_cgroups"], controller_rows),
        "",
        "## PSI",
        "",
        markdown_table(["resource", "pressure"], psi_rows),
        "",
        "## Mount State",
        "",
        markdown_table(["mount"], mount_rows),
        "",
        "## Kernel Config",
        "",
        markdown_table(["CONFIG", "state"], config_rows),
        "",
        "## Service Isolation Implications",
        "",
        markdown_table(["item", "state"], isolation_rows),
        "",
    ]
    return "\n".join(lines), manifest, pass_ok


def main() -> int:
    args = parse_args()
    captures = [run_capture(args, "version", ["version"], timeout=15.0)]
    config_capture, _config_text, config = fetch_kernel_config(args)
    captures.append(config_capture)
    captures.append(run_capture(args, "mounts", ["mounts"], timeout=15.0))
    for name, command in PROC_COMMANDS:
        captures.append(run_capture(args, name, command, timeout=args.timeout))

    report, manifest, pass_ok = build_report(args, captures, config)
    output = repo_path(args.out)
    json_output = repo_path(args.json_out) if args.json_out else output.with_suffix(".json")
    write_private_text(output, report.rstrip() + "\n")
    write_private_json(json_output, manifest)
    print(f"{'PASS' if pass_ok else 'FAIL'} out={output} json={json_output} decision={manifest['decision']}")
    return 0 if pass_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

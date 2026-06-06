#!/usr/bin/env python3
"""Collect read-only A90 netfilter/iptables/nftables exposure inventory."""

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
    "CONFIG_NETFILTER",
    "CONFIG_NETFILTER_ADVANCED",
    "CONFIG_NF_CONNTRACK",
    "CONFIG_NF_CONNTRACK_IPV4",
    "CONFIG_NF_CONNTRACK_IPV6",
    "CONFIG_NF_NAT",
    "CONFIG_NF_TABLES",
    "CONFIG_NFT_CT",
    "CONFIG_NFT_NAT",
    "CONFIG_IP_NF_IPTABLES",
    "CONFIG_IP_NF_FILTER",
    "CONFIG_IP_NF_NAT",
    "CONFIG_IP_NF_MANGLE",
    "CONFIG_IP_NF_RAW",
    "CONFIG_IP6_NF_IPTABLES",
    "CONFIG_IP6_NF_FILTER",
    "CONFIG_IP6_NF_MANGLE",
    "CONFIG_IP6_NF_RAW",
    "CONFIG_BRIDGE_NETFILTER",
]

PROC_COMMANDS: tuple[tuple[str, list[str]], ...] = (
    ("ip4-tables", ["run", "/cache/bin/toybox", "cat", "/proc/net/ip_tables_names"]),
    ("ip6-tables", ["run", "/cache/bin/toybox", "cat", "/proc/net/ip6_tables_names"]),
    ("ip4-targets", ["run", "/cache/bin/toybox", "cat", "/proc/net/ip_tables_targets"]),
    ("ip4-matches", ["run", "/cache/bin/toybox", "cat", "/proc/net/ip_tables_matches"]),
    ("ip6-targets", ["run", "/cache/bin/toybox", "cat", "/proc/net/ip6_tables_targets"]),
    ("ip6-matches", ["run", "/cache/bin/toybox", "cat", "/proc/net/ip6_tables_matches"]),
    ("conntrack-count", ["run", "/cache/bin/toybox", "cat", "/proc/sys/net/netfilter/nf_conntrack_count"]),
    ("conntrack-max", ["run", "/cache/bin/toybox", "cat", "/proc/sys/net/netfilter/nf_conntrack_max"]),
    ("conntrack-lines", ["run", "/cache/bin/toybox", "wc", "-l", "/proc/net/nf_conntrack"]),
    ("nf-runtime-ls", ["run", "/cache/bin/toybox", "ls", "-l", "/proc/net/netfilter", "/proc/sys/net/netfilter"]),
    (
        "userland-tools-ls",
        [
            "run",
            "/cache/bin/toybox",
            "ls",
            "-l",
            "/cache/bin/iptables",
            "/cache/bin/ip6tables",
            "/cache/bin/nft",
            "/cache/bin/conntrack",
            "/system/bin/iptables",
            "/system/bin/ip6tables",
            "/system/bin/nft",
            "/system/bin/conntrack",
        ],
    ),
)


def default_out() -> Path:
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return REPO_ROOT / "tmp" / "netfilter" / f"a90-netfilter-{stamp}.md"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=54321)
    parser.add_argument("--timeout", type=float, default=45.0)
    parser.add_argument("--expect-version", default=DEFAULT_EXPECT_VERSION)
    parser.add_argument("--out", type=Path, default=default_out())
    parser.add_argument("--json-out", type=Path)
    return parser.parse_args()


def nonempty_lines(text: str) -> list[str]:
    return [line.strip() for line in strip_cmdv1_text(text).splitlines() if line.strip() and not line.startswith("toybox:")]


def has_tool(text: str, path: str) -> bool:
    return any(path in line and "No such file" not in line for line in strip_cmdv1_text(text).splitlines())


def build_report(args: argparse.Namespace,
                 captures: list[Any],
                 config: dict[str, str]) -> tuple[str, dict[str, Any], bool]:
    by_name = {capture.name: capture for capture in captures}
    version_matches = args.expect_version in by_name["version"].text
    config_ok = bool(config)
    proc_required_ok = all(by_name[name].ok for name in ("ip4-tables", "ip6-tables", "conntrack-count", "conntrack-max"))

    ip4_tables = nonempty_lines(by_name["ip4-tables"].text)
    ip6_tables = nonempty_lines(by_name["ip6-tables"].text)
    conntrack_count = " ".join(nonempty_lines(by_name["conntrack-count"].text)) or "unknown"
    conntrack_max = " ".join(nonempty_lines(by_name["conntrack-max"].text)) or "unknown"
    tool_text = by_name["userland-tools-ls"].text

    kernel_rows = [[option, config_state(config, option)] for option in CONFIG_OPTIONS]
    runtime_rows = [
        ["ip4 tables", ", ".join(ip4_tables) if ip4_tables else "(empty)"],
        ["ip6 tables", ", ".join(ip6_tables) if ip6_tables else "(empty)"],
        ["conntrack count", conntrack_count],
        ["conntrack max", conntrack_max],
        ["proc netfilter", "present" if by_name["nf-runtime-ls"].ok else "missing"],
    ]
    tool_rows = []
    for path in (
        "/cache/bin/iptables",
        "/cache/bin/ip6tables",
        "/cache/bin/nft",
        "/cache/bin/conntrack",
        "/system/bin/iptables",
        "/system/bin/ip6tables",
        "/system/bin/nft",
        "/system/bin/conntrack",
    ):
        tool_rows.append([path, "present" if has_tool(tool_text, path) else "missing"])

    nft_kernel = config_enabled(config, "CONFIG_NF_TABLES")
    legacy_kernel = config_enabled(config, "CONFIG_IP_NF_IPTABLES") or config_enabled(config, "CONFIG_IP6_NF_IPTABLES")
    conntrack_kernel = config_enabled(config, "CONFIG_NF_CONNTRACK")
    decision = (
        "legacy-iptables-runtime-present"
        if legacy_kernel and (ip4_tables or ip6_tables) and conntrack_kernel
        else "kernel-only-or-incomplete"
    )
    notes = [
        "nftables kernel core is enabled" if nft_kernel else "nftables kernel core is not enabled; use legacy iptables path first",
        "conntrack runtime knobs are present" if by_name["conntrack-count"].ok else "conntrack runtime knobs missing",
        "userland firewall tools are not required for this read-only inventory",
    ]

    manifest = {
        "created": dt.datetime.now(dt.timezone.utc).isoformat(),
        "expect_version": args.expect_version,
        "version_matches": version_matches,
        "pass": bool(version_matches and config_ok and proc_required_ok),
        "decision": decision,
        "kernel": {option: config_state(config, option) for option in CONFIG_OPTIONS},
        "runtime": {
            "ip4_tables": ip4_tables,
            "ip6_tables": ip6_tables,
            "conntrack_count": conntrack_count,
            "conntrack_max": conntrack_max,
        },
        "host": collect_host_metadata(),
        "captures": [capture_to_manifest(capture) for capture in captures],
    }
    lines = [
        "# A90 Netfilter / Nftables Exposure Inventory",
        "",
        "## Summary",
        "",
        f"- result: {'PASS' if manifest['pass'] else 'FAIL'}",
        f"- decision: `{decision}`",
        f"- expected version: `{args.expect_version}`",
        f"- version matches: `{version_matches}`",
        "- policy: read-only; no firewall rule writes, no sysctl writes, no module load, no Wi-Fi enablement",
        "",
        "## Runtime Snapshot",
        "",
        markdown_table(["item", "value"], runtime_rows),
        "",
        "## Kernel Config",
        "",
        markdown_table(["CONFIG", "state"], kernel_rows),
        "",
        "## Userland Tool Paths",
        "",
        markdown_table(["path", "state"], tool_rows),
        "",
        "## Notes",
        "",
    ]
    lines.extend(f"- {note}" for note in notes)
    lines.append("")
    return "\n".join(lines), manifest, bool(manifest["pass"])


def main() -> int:
    args = parse_args()
    captures = [run_capture(args, "version", ["version"], timeout=15.0)]
    config_capture, _config_text, config = fetch_kernel_config(args)
    captures.append(config_capture)
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

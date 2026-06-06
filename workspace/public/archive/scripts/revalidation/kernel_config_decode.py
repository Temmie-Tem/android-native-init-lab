#!/usr/bin/env python3
"""Decode A90 /proc/config.gz into a kernel capability matrix."""

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
    parse_kernel_config,
    repo_path,
    run_capture,
    summarize_options,
    write_private_json,
    write_private_text,
)


CATEGORIES: tuple[dict[str, Any], ...] = (
    {
        "name": "netfilter_nftables",
        "reason": "Firewall, ACL, conntrack, NAT, and future non-USB exposure control.",
        "options": [
            "CONFIG_NETFILTER",
            "CONFIG_NETFILTER_ADVANCED",
            "CONFIG_NF_CONNTRACK",
            "CONFIG_NF_TABLES",
            "CONFIG_NF_TABLES_INET",
            "CONFIG_NFT_CT",
            "CONFIG_NFT_COUNTER",
            "CONFIG_NFT_LOG",
            "CONFIG_NFT_LIMIT",
            "CONFIG_NFT_REJECT",
            "CONFIG_NFT_MASQ",
            "CONFIG_NFT_NAT",
            "CONFIG_IP_NF_IPTABLES",
            "CONFIG_IP_NF_FILTER",
            "CONFIG_IP_NF_NAT",
            "CONFIG_IP6_NF_IPTABLES",
            "CONFIG_IP6_NF_FILTER",
            "CONFIG_BRIDGE_NETFILTER",
        ],
    },
    {
        "name": "cgroup_psi_resource_control",
        "reason": "Process/service isolation and long-running server workload visibility.",
        "options": [
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
        ],
    },
    {
        "name": "bpf_observability",
        "reason": "Packet filtering, tracing hooks, and future diagnostics feasibility.",
        "options": [
            "CONFIG_BPF",
            "CONFIG_BPF_SYSCALL",
            "CONFIG_BPF_JIT",
            "CONFIG_HAVE_EBPF_JIT",
            "CONFIG_CGROUP_BPF",
            "CONFIG_NET_CLS_BPF",
            "CONFIG_NET_ACT_BPF",
            "CONFIG_BPF_EVENTS",
        ],
    },
    {
        "name": "pstore_ramoops",
        "reason": "Crash/oops persistence and reboot-failure debugging.",
        "options": [
            "CONFIG_PSTORE",
            "CONFIG_PSTORE_CONSOLE",
            "CONFIG_PSTORE_PMSG",
            "CONFIG_PSTORE_RAM",
            "CONFIG_PSTORE_FTRACE",
            "CONFIG_RAMOOPS",
        ],
    },
    {
        "name": "tracefs_ftrace_debug",
        "reason": "Kernel observability for USB, scheduler, IRQ, and latency debugging.",
        "options": [
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
            "CONFIG_UPROBE_EVENTS",
            "CONFIG_DEBUG_FS",
            "CONFIG_USB_MON",
        ],
    },
    {
        "name": "wifi_wireless_stack",
        "reason": "Native Wi-Fi bring-up prerequisites before touching rfkill or firmware.",
        "options": [
            "CONFIG_WIRELESS",
            "CONFIG_CFG80211",
            "CONFIG_MAC80211",
            "CONFIG_RFKILL",
            "CONFIG_WLAN",
            "CONFIG_QCOM_WCNSS_PIL",
            "CONFIG_CNSS",
            "CONFIG_QCA_CLD_WLAN",
            "CONFIG_PRIMA_WLAN",
            "CONFIG_WCNSS_MEM_PRE_ALLOC",
        ],
    },
    {
        "name": "network_namespaces_tun",
        "reason": "Future service/container boundaries and VPN/tunnel feasibility.",
        "options": [
            "CONFIG_NAMESPACES",
            "CONFIG_UTS_NS",
            "CONFIG_IPC_NS",
            "CONFIG_PID_NS",
            "CONFIG_NET_NS",
            "CONFIG_USER_NS",
            "CONFIG_TUN",
            "CONFIG_VETH",
            "CONFIG_DUMMY",
        ],
    },
)


def default_out() -> Path:
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return REPO_ROOT / "tmp" / "kernel-config" / f"a90-kernel-config-{stamp}.md"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=54321)
    parser.add_argument("--timeout", type=float, default=45.0)
    parser.add_argument("--expect-version", default=DEFAULT_EXPECT_VERSION)
    parser.add_argument("--config-file", type=Path, help="parse a local decompressed kernel config instead of device /proc/config.gz")
    parser.add_argument("--out", type=Path, default=default_out())
    parser.add_argument("--json-out", type=Path)
    return parser.parse_args()


def category_status(config: dict[str, str], category: dict[str, Any]) -> str:
    options = category["options"]
    enabled = [option for option in options if config_enabled(config, option)]
    if category["name"] == "netfilter_nftables":
        if config_enabled(config, "CONFIG_NETFILTER") and (
            config_enabled(config, "CONFIG_NF_TABLES") or config_enabled(config, "CONFIG_IP_NF_IPTABLES")
        ):
            return "present"
        return "missing-core"
    if category["name"] == "cgroup_psi_resource_control":
        if config_enabled(config, "CONFIG_CGROUPS") and config_enabled(config, "CONFIG_PSI"):
            return "present"
        if config_enabled(config, "CONFIG_CGROUPS"):
            return "partial-no-psi"
        return "missing-core"
    if category["name"] == "wifi_wireless_stack":
        if config_enabled(config, "CONFIG_CFG80211") and config_enabled(config, "CONFIG_RFKILL"):
            return "kernel-stack-present"
        return "no-native-gate"
    return "present" if enabled else "missing"


def build_report(args: argparse.Namespace,
                 captures: list[Any],
                 config_text: str,
                 config: dict[str, str]) -> tuple[str, dict[str, Any], bool]:
    version_capture = next((capture for capture in captures if capture.name == "version"), None)
    version_matches = bool(version_capture and args.expect_version in version_capture.text)
    config_ok = bool(config)
    category_rows: list[list[str]] = []
    detail_tables: list[str] = []
    category_data: list[dict[str, Any]] = []

    for category in CATEGORIES:
        options = category["options"]
        summary = summarize_options(config, options)
        status = category_status(config, category)
        category_rows.append([
            category["name"],
            status,
            f"y={summary['y']} m={summary['m']} n={summary['n']} unset={summary['unset']} value={summary['value']}",
            category["reason"],
        ])
        rows = [[option, config_state(config, option)] for option in options]
        detail_tables.append(f"### {category['name']}\n\n" + markdown_table(["CONFIG", "state"], rows))
        category_data.append({
            "name": category["name"],
            "status": status,
            "summary": summary,
            "options": {option: config_state(config, option) for option in options},
        })

    pass_ok = config_ok and (version_matches if not args.config_file else True)
    manifest = {
        "created": dt.datetime.now(dt.timezone.utc).isoformat(),
        "expect_version": args.expect_version,
        "version_matches": version_matches,
        "pass": pass_ok,
        "config_option_count": len(config),
        "config_ok": config_ok,
        "source": "local-file" if args.config_file else "device-proc-config-gz",
        "host": collect_host_metadata(),
        "categories": category_data,
        "captures": [capture_to_manifest(capture) for capture in captures],
    }

    lines = [
        "# A90 Kernel Config Capability Matrix",
        "",
        "## Summary",
        "",
        f"- result: {'PASS' if pass_ok else 'FAIL'}",
        f"- source: {'local file `' + str(args.config_file) + '`' if args.config_file else '`/proc/config.gz` via toybox zcat'}",
        f"- expected version: `{args.expect_version}`",
        f"- version matches: `{version_matches}`",
        f"- parsed CONFIG entries: `{len(config)}`",
        "- policy: read-only; no mount, no module load, no tracing enable, no Wi-Fi enablement",
        "",
        "## Capability Matrix",
        "",
        markdown_table(["area", "status", "option summary", "why it matters"], category_rows),
        "",
        "## Option Details",
        "",
        "\n\n".join(detail_tables),
        "",
    ]
    if config_text:
        lines.extend([
            "## Config Header",
            "",
            "```text",
            "\n".join(config_text.splitlines()[:8]),
            "```",
            "",
        ])
    return "\n".join(lines), manifest, pass_ok


def main() -> int:
    args = parse_args()
    captures = []
    if args.config_file:
        config_text = repo_path(args.config_file).read_text(encoding="utf-8", errors="replace")
        config = parse_kernel_config(config_text)
    else:
        version_capture = run_capture(args, "version", ["version"], timeout=15.0)
        config_capture, config_text, config = fetch_kernel_config(args)
        captures.extend([version_capture, config_capture])

    report, manifest, pass_ok = build_report(args, captures, config_text, config)
    output = repo_path(args.out)
    json_output = repo_path(args.json_out) if args.json_out else output.with_suffix(".json")
    write_private_text(output, report.rstrip() + "\n")
    write_private_json(json_output, manifest)
    print(f"{'PASS' if pass_ok else 'FAIL'} out={output} json={json_output} configs={len(config)}")
    return 0 if pass_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

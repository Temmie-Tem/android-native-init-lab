#!/usr/bin/env python3
"""Build one A90 kernel capability summary from v197-v200 evidence."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from a90_kernel_tools import (
    DEFAULT_EXPECT_VERSION,
    REPO_ROOT,
    collect_host_metadata,
    markdown_table,
    repo_path,
    run_capture,
    write_private_json,
    write_private_text,
)


DEFAULT_INPUTS = {
    "config": "tmp/kernel-config/v201-kernel-config.json",
    "netfilter": "tmp/netfilter/v201-netfilter.json",
    "cgroup": "tmp/cgroup-psi/v201-cgroup-psi.json",
    "debug": "tmp/debug-observability/v201-debug-observability.json",
}


def default_out() -> Path:
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return REPO_ROOT / "tmp" / "kernel-capability" / f"a90-kernel-capability-{stamp}.md"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=54321)
    parser.add_argument("--timeout", type=float, default=45.0)
    parser.add_argument("--expect-version", default=DEFAULT_EXPECT_VERSION)
    parser.add_argument("--config-json", type=Path, default=Path(DEFAULT_INPUTS["config"]))
    parser.add_argument("--netfilter-json", type=Path, default=Path(DEFAULT_INPUTS["netfilter"]))
    parser.add_argument("--cgroup-json", type=Path, default=Path(DEFAULT_INPUTS["cgroup"]))
    parser.add_argument("--debug-json", type=Path, default=Path(DEFAULT_INPUTS["debug"]))
    parser.add_argument("--refresh", action="store_true", help="rerun v197-v200 collectors before summarizing")
    parser.add_argument("--out", type=Path, default=default_out())
    parser.add_argument("--json-out", type=Path)
    return parser.parse_args()


def run_refresh(args: argparse.Namespace) -> None:
    commands = [
        [
            sys.executable,
            "scripts/revalidation/kernel_config_decode.py",
            "--host",
            args.host,
            "--port",
            str(args.port),
            "--timeout",
            str(args.timeout),
            "--expect-version",
            args.expect_version,
            "--out",
            "tmp/kernel-config/v202-kernel-config.md",
            "--json-out",
            str(args.config_json),
        ],
        [
            sys.executable,
            "scripts/revalidation/netfilter_inventory.py",
            "--host",
            args.host,
            "--port",
            str(args.port),
            "--timeout",
            str(args.timeout),
            "--expect-version",
            args.expect_version,
            "--out",
            "tmp/netfilter/v202-netfilter.md",
            "--json-out",
            str(args.netfilter_json),
        ],
        [
            sys.executable,
            "scripts/revalidation/cgroup_psi_inventory.py",
            "--host",
            args.host,
            "--port",
            str(args.port),
            "--timeout",
            str(args.timeout),
            "--expect-version",
            args.expect_version,
            "--out",
            "tmp/cgroup-psi/v202-cgroup-psi.md",
            "--json-out",
            str(args.cgroup_json),
        ],
        [
            sys.executable,
            "scripts/revalidation/debug_observability_plan.py",
            "--host",
            args.host,
            "--port",
            str(args.port),
            "--timeout",
            str(args.timeout),
            "--expect-version",
            args.expect_version,
            "--out",
            "tmp/debug-observability/v202-debug-observability.md",
            "--json-out",
            str(args.debug_json),
        ],
    ]
    for command in commands:
        result = subprocess.run(command, cwd=REPO_ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
        if result.returncode != 0:
            raise RuntimeError(f"refresh failed rc={result.returncode}: {' '.join(command)}\n{result.stdout}")


def load_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    return json.loads(resolved.read_text(encoding="utf-8"))


def get_category(data: dict[str, Any], name: str) -> dict[str, Any]:
    for item in data.get("categories", []):
        if item.get("name") == name:
            return item
    return {}


VALID_WIFI_DECISIONS = {"baseline-required", "no-go", "go"}


def wifi_gate(args: argparse.Namespace) -> tuple[str, str, bool, str]:
    capture = run_capture(args, "wififeas-gate", ["wififeas", "gate"], timeout=20.0)
    text = capture.text
    if not text and capture.error:
        text = f"[capture-error] {capture.error}\n"
    decision = "unknown"
    for line in text.splitlines():
        if line.startswith("wififeas: decision="):
            decision = line.split("=", 1)[1].strip()
            break
    gate_ok = capture.ok and decision in VALID_WIFI_DECISIONS
    return decision, text, gate_ok, capture.status


def build_summary(args: argparse.Namespace,
                  config_data: dict[str, Any],
                  netfilter_data: dict[str, Any],
                  cgroup_data: dict[str, Any],
                  debug_data: dict[str, Any],
                  wifi_decision: str,
                  wifi_text: str,
                  wifi_gate_ok: bool,
                  wifi_status: str) -> tuple[str, dict[str, Any], bool]:
    config_pass = bool(config_data.get("pass"))
    netfilter_pass = bool(netfilter_data.get("pass"))
    cgroup_pass = bool(cgroup_data.get("pass"))
    debug_pass = bool(debug_data.get("pass"))
    version_matches = all(bool(data.get("version_matches")) for data in (config_data, netfilter_data, cgroup_data, debug_data))
    pass_ok = (
        config_pass and
        netfilter_pass and
        cgroup_pass and
        debug_pass and
        version_matches and
        wifi_gate_ok
    )

    matrix_rows = [
        [
            "Kernel config",
            "pass" if config_pass else "fail",
            f"CONFIG entries={config_data.get('config_option_count')}",
            "Base evidence for every later kernel-facing feature.",
        ],
        [
            "Netfilter exposure",
            netfilter_data.get("decision", "unknown"),
            "legacy iptables path" if netfilter_data.get("decision") == "legacy-iptables-runtime-present" else "review required",
            "Use before widening NCM/Wi-Fi exposure.",
        ],
        [
            "Cgroup / PSI",
            cgroup_data.get("decision", "unknown"),
            "PSI present, cgroup unmounted" if cgroup_data.get("decision") == "supported-unmounted-psi-present" else "review required",
            "Useful for service isolation and load observation.",
        ],
        [
            "Tracefs / pstore",
            "tracefs=yes pstore=yes" if debug_data.get("state", {}).get("tracefs_supported") and debug_data.get("state", {}).get("pstore_supported") else "partial",
            f"mounted tracefs={debug_data.get('state', {}).get('tracefs_mounted')} pstore={debug_data.get('state', {}).get('pstore_mounted')}",
            "Use only through explicit opt-in debug sessions.",
        ],
        [
            "Wi-Fi gate",
            wifi_decision,
            (
                "active bring-up blocked" if wifi_gate_ok and wifi_decision != "go"
                else "review required" if wifi_gate_ok
                else f"gate failed status={wifi_status}"
            ),
            "Do not enable Wi-Fi until native WLAN/rfkill/module gates change.",
        ],
    ]
    config_rows = [
        ["netfilter", get_category(config_data, "netfilter_nftables").get("status", "unknown")],
        ["cgroup/PSI", get_category(config_data, "cgroup_psi_resource_control").get("status", "unknown")],
        ["BPF", get_category(config_data, "bpf_observability").get("status", "unknown")],
        ["pstore/ramoops", get_category(config_data, "pstore_ramoops").get("status", "unknown")],
        ["tracefs/ftrace", get_category(config_data, "tracefs_ftrace_debug").get("status", "unknown")],
        ["Wi-Fi stack", get_category(config_data, "wifi_wireless_stack").get("status", "unknown")],
    ]
    next_rows = [
        ["Wi-Fi baseline refresh", "allowed-read-only", "Collect updated native/mounted-system evidence; no bring-up."],
        ["iptables userland packaging", "candidate", "Kernel path exists, but tools are missing."],
        ["cgroup mount probe", "opt-in-plan-required", "Supported but unmounted; no process migration by default."],
        ["tracefs mount probe", "opt-in-plan-required", "Useful for USB/serial diagnosis; no tracing writes by default."],
        ["pstore read/mount probe", "opt-in-plan-required", "Read-only only; reboot persistence remains maintenance-window-only."],
    ]
    manifest = {
        "created": dt.datetime.now(dt.timezone.utc).isoformat(),
        "expect_version": args.expect_version,
        "pass": pass_ok,
        "version_matches": version_matches,
        "wifi_gate_ok": wifi_gate_ok,
        "wifi_gate_status": wifi_status,
        "wifi_decision": wifi_decision,
        "source_files": {
            "config": str(repo_path(args.config_json)),
            "netfilter": str(repo_path(args.netfilter_json)),
            "cgroup": str(repo_path(args.cgroup_json)),
            "debug": str(repo_path(args.debug_json)),
        },
        "matrix": matrix_rows,
        "host": collect_host_metadata(),
        "wifi_text": wifi_text,
    }
    lines = [
        "# A90 Kernel Capability Summary",
        "",
        "## Summary",
        "",
        f"- result: {'PASS' if pass_ok else 'FAIL'}",
        f"- expected version: `{args.expect_version}`",
        f"- all source versions match: `{version_matches}`",
        f"- live Wi-Fi gate captured: `{wifi_gate_ok}` status=`{wifi_status}`",
        f"- Wi-Fi decision: `{wifi_decision}`",
        "- policy: summary only; no mount, no firewall writes, no cgroup writes, no Wi-Fi enablement",
        "",
        "## Capability Matrix",
        "",
        markdown_table(["area", "state", "detail", "operator meaning"], matrix_rows),
        "",
        "## Config Category Snapshot",
        "",
        markdown_table(["category", "status"], config_rows),
        "",
        "## Recommended Next Actions",
        "",
        markdown_table(["candidate", "classification", "reason"], next_rows),
        "",
        "## Wi-Fi Gate Evidence",
        "",
        "```text",
        wifi_text.strip(),
        "```",
        "",
    ]
    return "\n".join(lines), manifest, pass_ok


def main() -> int:
    args = parse_args()
    if args.refresh:
        run_refresh(args)
    config_data = load_json(args.config_json)
    netfilter_data = load_json(args.netfilter_json)
    cgroup_data = load_json(args.cgroup_json)
    debug_data = load_json(args.debug_json)
    wifi_decision, wifi_text, wifi_gate_ok, wifi_status = wifi_gate(args)
    report, manifest, pass_ok = build_summary(
        args,
        config_data,
        netfilter_data,
        cgroup_data,
        debug_data,
        wifi_decision,
        wifi_text,
        wifi_gate_ok,
        wifi_status,
    )
    output = repo_path(args.out)
    json_output = repo_path(args.json_out) if args.json_out else output.with_suffix(".json")
    write_private_text(output, report.rstrip() + "\n")
    write_private_json(json_output, manifest)
    print(f"{'PASS' if pass_ok else 'FAIL'} out={output} json={json_output} wifi={wifi_decision} gate_ok={wifi_gate_ok}")
    return 0 if pass_ok else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(f"FAIL {exc}", file=sys.stderr)
        raise SystemExit(1)

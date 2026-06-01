#!/usr/bin/env python3
"""V1545 host-only design classifier for the next low-overhead RC1 observer."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1545-low-overhead-endpoint-observer-design")
DEFAULT_REPORT_PATH = Path(
    "docs/reports/NATIVE_INIT_V1545_LOW_OVERHEAD_ENDPOINT_OBSERVER_DESIGN_2026-06-02.md"
)
LATEST_POINTER = Path("tmp/wifi/latest-v1545-low-overhead-endpoint-observer-design.txt")

V1544_MANIFEST = Path("tmp/wifi/v1544-endpoint-electrical-result-classifier/manifest.json")
V1541_BUILD = Path("scripts/revalidation/build_native_init_wifi_test_boot_v1541.py")
V1515_BUILD = Path("scripts/revalidation/build_native_init_wifi_test_boot_v1515.py")
V1536_BUILD = Path("scripts/revalidation/build_native_init_wifi_test_boot_v1536.py")
BASE_BUILD = Path("scripts/revalidation/build_native_init_wifi_test_boot_v1393.py")
PID1_SOURCE = Path("stage3/linux_init/v724/90_main.inc.c")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def rel(path: Path) -> str:
    resolved = repo_path(path)
    try:
        return str(resolved.relative_to(repo_path(".")))
    except ValueError:
        return str(resolved)


def read_text(path: Path) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    return resolved.read_text(encoding="utf-8", errors="replace")


def read_json(path: Path) -> dict[str, Any]:
    text = read_text(path)
    if not text:
        return {}
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def has_flag(text: str, flag: str) -> bool:
    return flag in text


def line_number(text: str, needle: str) -> int | None:
    for index, line in enumerate(text.splitlines(), start=1):
        if needle in line:
            return index
    return None


def block_between(text: str, start: str, end: str) -> str:
    start_index = text.find(start)
    if start_index < 0:
        return ""
    end_index = text.find(end, start_index + len(start))
    if end_index < 0:
        return text[start_index:]
    return text[start_index:end_index]


def analyze() -> dict[str, Any]:
    v1544 = read_json(V1544_MANIFEST)
    v1541_build = read_text(V1541_BUILD)
    v1515_build = read_text(V1515_BUILD)
    v1536_build = read_text(V1536_BUILD)
    base_build = read_text(BASE_BUILD)
    pid1_source = read_text(PID1_SOURCE)
    micro_fn = block_between(
        pid1_source,
        "static void v1393_rc1_micro_endpoint_sample",
        "#if A90_WIFI_TEST_BOOT_PROVIDER_TRIGGER_AP2MDM_HOLD",
    )
    critical_block = block_between(
        micro_fn,
        "#if A90_WIFI_TEST_BOOT_RC1_MICRO_CRITICAL_FAST_ENDPOINT_SAMPLER",
        "#if A90_WIFI_TEST_BOOT_RC1_MICRO_FOCUSED_ENDPOINT_SAMPLER",
    )
    focused_block = block_between(
        micro_fn,
        "#if A90_WIFI_TEST_BOOT_RC1_MICRO_FOCUSED_ENDPOINT_SAMPLER",
        "#if A90_WIFI_TEST_BOOT_RC1_MICRO_BATCHED_FOCUSED_ENDPOINT_SAMPLER",
    )
    v1544_evidence = v1544.get("evidence") if isinstance(v1544.get("evidence"), dict) else {}
    v1544_window = v1544_evidence.get("window") if isinstance(v1544_evidence.get("window"), dict) else {}
    return {
        "paths": {
            "v1544_manifest": rel(V1544_MANIFEST),
            "v1541_build": rel(V1541_BUILD),
            "v1515_build": rel(V1515_BUILD),
            "v1536_build": rel(V1536_BUILD),
            "base_build": rel(BASE_BUILD),
            "pid1_source": rel(PID1_SOURCE),
        },
        "v1544": {
            "pass": bool(v1544.get("pass")),
            "decision": v1544.get("decision"),
            "next_gate": (v1544.get("next_gate") or {}).get("cycle")
            if isinstance(v1544.get("next_gate"), dict)
            else None,
            "first_clk_begin_micro_elapsed_ms": v1544_window.get("first_clk_begin_micro_elapsed_ms"),
            "max_clk_source_duration_ms": v1544_window.get("max_clk_source_duration_ms"),
        },
        "build_flags": {
            "v1541_has_sysfs_client_enumerate": has_flag(v1541_build, "--wifi-test-rc1-sysfs-client-enumerate"),
            "v1541_has_micro_critical_fast": has_flag(v1541_build, "--wifi-test-rc1-micro-critical-fast-endpoint-sampler"),
            "v1541_has_micro_focused": has_flag(v1541_build, "--wifi-test-rc1-micro-focused-endpoint-sampler"),
            "v1515_has_micro_critical_fast": has_flag(v1515_build, "--wifi-test-rc1-micro-critical-fast-endpoint-sampler"),
            "v1515_has_micro_focused": has_flag(v1515_build, "--wifi-test-rc1-micro-focused-endpoint-sampler"),
            "v1536_has_sysfs_client_enumerate": has_flag(v1536_build, "--wifi-test-rc1-sysfs-client-enumerate"),
            "base_exposes_micro_critical_flag": has_flag(base_build, "wifi_test_rc1_micro_critical_fast_endpoint_sampler"),
            "base_exposes_micro_focused_flag": has_flag(base_build, "wifi_test_rc1_micro_focused_endpoint_sampler"),
        },
        "pid1_contract": {
            "micro_function_present": bool(micro_fn),
            "critical_block_has_clk_skip_marker": "micro_critical_clk_summary_skipped=1" in critical_block,
            "critical_block_reads_full_clk_summary": "/sys/kernel/debug/clk/clk_summary" in critical_block,
            "critical_block_reads_interrupts": "/proc/interrupts" in critical_block,
            "critical_block_reads_debug_gpio": "/sys/kernel/debug/gpio" in critical_block,
            "critical_block_reads_regulator_summary": "/sys/kernel/debug/regulator/regulator_summary" in critical_block,
            "critical_block_reads_pinmux": "/sys/kernel/debug/pinctrl/3000000.pinctrl/pinmux-pins" in critical_block,
            "focused_block_reads_full_clk_summary": "/sys/kernel/debug/clk/clk_summary" in focused_block,
            "critical_skip_line": line_number(pid1_source, "micro_critical_clk_summary_skipped=1"),
            "focused_clk_line": line_number(pid1_source, "\"micro_focused_clk\""),
        },
    }


def classify() -> dict[str, Any]:
    evidence = analyze()
    flags = evidence["build_flags"]
    contract = evidence["pid1_contract"]
    v1544 = evidence["v1544"]
    checks = {
        "v1544-fixed-no-l0-classifier-pass": v1544["pass"]
        and v1544["decision"] == "v1544-endpoint-electrical-confirms-no-l0-gpio-gdsc-zero-clk-postfail",
        "v1541-explains-slow-clock-source": flags["v1541_has_micro_focused"]
        and v1544["first_clk_begin_micro_elapsed_ms"] is not None
        and int(v1544["first_clk_begin_micro_elapsed_ms"]) >= 100,
        "critical-fast-contract-exists": flags["base_exposes_micro_critical_flag"]
        and contract["critical_block_has_clk_skip_marker"],
        "critical-fast-avoids-full-clk-summary": not contract["critical_block_reads_full_clk_summary"],
        "critical-fast-covers-endpoint-sources": contract["critical_block_reads_interrupts"]
        and contract["critical_block_reads_debug_gpio"]
        and contract["critical_block_reads_regulator_summary"]
        and contract["critical_block_reads_pinmux"],
        "existing-build-proves-critical-without-micro-focused": flags["v1515_has_micro_critical_fast"]
        and not flags["v1515_has_micro_focused"],
        "sysfs-client-enumerate-flag-available": flags["v1536_has_sysfs_client_enumerate"]
        and flags["v1541_has_sysfs_client_enumerate"],
    }
    pass_ok = all(checks.values())
    recommended_flags = [
        "--wifi-test-mount-debugfs",
        "--wifi-test-auto-readiness-supervisor",
        "--wifi-test-pid1-rc1-watcher",
        "--wifi-test-rc1-window-sampler",
        "--wifi-test-rc1-endpoint-sampler",
        "--wifi-test-rc1-micro-endpoint-sampler",
        "--wifi-test-rc1-micro-source-timestamped-sampler",
        "--wifi-test-rc1-micro-critical-fast-endpoint-sampler",
        "--wifi-test-rc1-case-aligned-micro-endpoint-sampler",
        "--wifi-test-rc1-sysfs-client-enumerate",
    ]
    forbidden_next_flags = [
        "--wifi-test-rc1-micro-focused-endpoint-sampler",
        "--wifi-test-rc1-micro-batched-focused-endpoint-sampler",
        "--wifi-test-rc1-immediate-endpoint-sampler",
    ]
    return {
        "cycle": "V1545",
        "generated_at": now_iso(),
        "decision": (
            "v1545-low-overhead-observer-design-ready"
            if pass_ok
            else "v1545-low-overhead-observer-design-needs-review"
        ),
        "pass": pass_ok,
        "reason": (
            "existing PID1 critical-fast sampler can build the next observer without full clk_summary in the RC1 micro window"
            if pass_ok
            else "one or more source contracts for the low-overhead observer did not match"
        ),
        "inputs": evidence["paths"],
        "host": collect_host_metadata(),
        "checks": checks,
        "evidence": evidence,
        "classification": {
            "active_blocker": "SDX50M endpoint still does not reach RC1 L0 after sysfs/client enumerate",
            "design": "reuse the V1541 sysfs/client enumerate route but drop micro-focused clock/pinconf reads from the critical micro loop",
            "recommended_next_cycle": "V1546",
            "recommended_next_artifact": "rollbackable source/build-only test boot with critical-fast-only micro endpoint observer",
            "recommended_flags": recommended_flags,
            "forbidden_next_flags": forbidden_next_flags,
            "expected_output_markers": [
                "micro_critical_fast_endpoint_sampler=1",
                "micro_critical_clk_summary_skipped=1",
                "micro_interrupts",
                "micro_debug_gpio",
                "micro_pcie1_current_link_state",
                "micro_pcie1_link_state",
                "micro_critical_regulator",
                "micro_critical_pinmux",
            ],
            "expected_absent_markers": [
                "micro_focused_clk",
                "micro_batched_clk",
                "immediate_clk",
            ],
        },
        "next_gate": {
            "cycle": "V1546",
            "summary": "source/build-only V1541-derived test boot that removes micro-focused clk_summary from the case-aligned micro loop",
            "guardrails": [
                "no live flash until V1546 artifact sanity passes",
                "no full clk_summary read in the sub-120ms micro loop",
                "no PMIC/GPIO/GDSC direct write",
                "no global PCI rescan or platform bind/unbind",
                "no Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping",
                "no firmware/MHI/WLFW branch until native L0 and PCI enumeration exist",
            ],
        },
        "safety": {
            "host_only_classifier": True,
            "device_commands_executed": False,
            "boot_or_partition_write_executed": False,
            "wifi_hal_start_executed": False,
            "scan_connect_executed": False,
            "credential_use_executed": False,
            "dhcp_route_executed": False,
            "external_ping_executed": False,
            "pmic_gpio_gdsc_write_executed": False,
            "global_pci_rescan_executed": False,
            "platform_bind_unbind_executed": False,
        },
    }


def render_report(result: dict[str, Any]) -> str:
    evidence = result["evidence"]
    flags = evidence["build_flags"]
    contract = evidence["pid1_contract"]
    return "\n".join([
        "# Native Init V1545 Low-Overhead Endpoint Observer Design",
        "",
        "## Summary",
        "",
        "- Cycle: `V1545`",
        "- Type: host-only source/design classifier",
        f"- Decision: `{result['decision']}`",
        f"- Result: {'PASS' if result['pass'] else 'REVIEW'}",
        f"- Reason: {result['reason']}",
        "",
        "## Inputs",
        "",
        markdown_table(["input", "path"], [[name, path] for name, path in result["inputs"].items()]),
        "",
        "## Checks",
        "",
        markdown_table(["check", "value"], [[name, value] for name, value in result["checks"].items()]),
        "",
        "## Source Contract",
        "",
        markdown_table(
            ["field", "value"],
            [
                ["V1541 has micro-focused sampler", flags["v1541_has_micro_focused"]],
                ["V1515 has critical-fast without micro-focused", flags["v1515_has_micro_critical_fast"] and not flags["v1515_has_micro_focused"]],
                ["V1536/V1541 have sysfs-client enumerate", flags["v1536_has_sysfs_client_enumerate"] and flags["v1541_has_sysfs_client_enumerate"]],
                ["critical block skips clk_summary", contract["critical_block_has_clk_skip_marker"]],
                ["critical block reads full clk_summary", contract["critical_block_reads_full_clk_summary"]],
                ["focused block reads full clk_summary", contract["focused_block_reads_full_clk_summary"]],
                ["critical skip line", contract["critical_skip_line"]],
                ["focused clk line", contract["focused_clk_line"]],
            ],
        ),
        "",
        "## Interpretation",
        "",
        "V1544 proves that `clk_summary` is too slow to serve as a precise sub-120ms pre-fail clock trace in the current endpoint-electrical handoff. The PID1 source already has a narrower critical-fast micro sampler that records interrupts, debug GPIO, link-state files, focused regulator lines, and focused pinmux lines while explicitly writing `micro_critical_clk_summary_skipped=1` instead of reading full `/sys/kernel/debug/clk/clk_summary` in the micro loop.",
        "",
        "Therefore the next useful live attempt should not repeat V1543 unchanged. It should build a V1541-derived test image that keeps sysfs/client enumerate and case-aligned micro sampling, keeps `micro_critical_fast_endpoint_sampler`, and removes `micro_focused_endpoint_sampler` from the critical micro path.",
        "",
        "## V1546 Recommended Contract",
        "",
        markdown_table(["include flag"], [[flag] for flag in result["classification"]["recommended_flags"]]),
        "",
        markdown_table(["exclude flag"], [[flag] for flag in result["classification"]["forbidden_next_flags"]]),
        "",
        "## Expected Markers",
        "",
        markdown_table(["present"], [[item] for item in result["classification"]["expected_output_markers"]]),
        "",
        markdown_table(["absent"], [[item] for item in result["classification"]["expected_absent_markers"]]),
        "",
        "## Next Gate",
        "",
        f"- Cycle: `{result['next_gate']['cycle']}`",
        f"- Summary: {result['next_gate']['summary']}",
        *(f"- Guardrail: {item}" for item in result["next_gate"]["guardrails"]),
        "",
        "## Safety Scope",
        "",
        "This classifier is host-only. It performs no device command, flash, reboot, partition write, Wi-Fi HAL start, scan/connect, credential handling, DHCP/routes, external ping, PMIC/GPIO/GDSC write, global PCI rescan, or platform bind/unbind.",
        "",
    ])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--write-report", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = classify()
    report = render_report(result)
    store = EvidenceStore(repo_path(args.out_dir))
    result["out_dir"] = str(store.run_dir)
    store.write_json("manifest.json", result)
    store.write_text("summary.md", report)
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    if args.write_report:
        write_private_text(repo_path(args.report_path), report)
    print(
        json.dumps(
            {
                "decision": result["decision"],
                "next_gate": result["next_gate"]["cycle"],
                "out_dir": rel(args.out_dir),
                "pass": result["pass"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

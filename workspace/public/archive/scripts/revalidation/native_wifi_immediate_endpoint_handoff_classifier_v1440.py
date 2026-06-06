#!/usr/bin/env python3
"""V1440 host-only classifier for V1439 immediate endpoint handoff evidence."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from a90harness.evidence import EvidenceStore, write_private_text


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
DEFAULT_INPUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1439-wifi-test-boot-immediate-endpoint-handoff"
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1440-immediate-endpoint-handoff-classifier"
DEFAULT_REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1440_IMMEDIATE_ENDPOINT_HANDOFF_CLASSIFIER_2026-06-01.md"
)
SAMPLE_HEADER_RE = re.compile(
    r"rc1_immediate_sample label=([^ ]+) elapsed_ms=(-?\d+) "
    r"detect_elapsed_ms=(-?\d+) immediate_elapsed_ms=(-?\d+)"
)


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def first_int_after_name(line: str, name: str) -> int | None:
    if name not in line:
        return None
    tail = line.rsplit(name, 1)[1].strip()
    if not tail:
        return None
    try:
        return int(tail.split()[0])
    except ValueError:
        return None


def collect_immediate_headers(text: str) -> list[dict[str, Any]]:
    headers = []
    for line in text.splitlines():
        match = SAMPLE_HEADER_RE.search(line)
        if not match:
            continue
        headers.append(
            {
                "label": match.group(1),
                "elapsed_ms": int(match.group(2)),
                "detect_elapsed_ms": int(match.group(3)),
                "immediate_elapsed_ms": int(match.group(4)),
            }
        )
    return headers


def line_for(text: str, label: str, source: str, needle: str) -> str:
    prefix = f"sample={label} source={source} needle={needle}"
    for line in text.splitlines():
        if line.startswith(prefix):
            return line
    return ""


def any_immediate_clock_enabled(text: str, label: str) -> bool:
    clocks = (
        "gcc_pcie_1_slv_q2a_axi_clk",
        "gcc_pcie_1_slv_axi_clk",
        "gcc_pcie_1_pipe_clk",
        "gcc_pcie_1_mstr_axi_clk",
        "gcc_pcie_1_clkref_clk",
        "gcc_pcie_1_cfg_ahb_clk",
        "gcc_pcie1_phy_refgen_clk",
        "gcc_pcie_phy_refgen_clk_src",
    )
    return any(
        (first_int_after_name(line_for(text, label, "immediate_clk", clock), clock) or 0) > 0
        for clock in clocks
    )


def classify(args: argparse.Namespace) -> dict[str, Any]:
    manifest_path = args.input_dir / "manifest.json"
    window_path = args.input_dir / "test-rc1-window-result.stdout.txt"
    dmesg_path = args.input_dir / "test-v1393-dmesg.stdout.txt"
    watcher_path = args.input_dir / "test-v1393-rc1-watcher-result.stdout.txt"
    manifest = load_json(manifest_path)
    window = read_text(window_path)
    dmesg = read_text(dmesg_path)
    watcher = read_text(watcher_path)
    progress = manifest.get("wifi_progress", {})
    headers = collect_immediate_headers(window)
    labels = [item["label"] for item in headers]
    elapsed_by_label = {item["label"]: item["immediate_elapsed_ms"] for item in headers}
    final_label = headers[-1]["label"] if headers else ""
    final_elapsed = headers[-1]["immediate_elapsed_ms"] if headers else None
    after_case_0_gdsc = first_int_after_name(
        line_for(window, "after_case_0ms", "immediate_regulator", "pcie_1_gdsc"),
        "pcie_1_gdsc",
    )
    all_immediate_clocks_off = bool(headers) and all(
        not any_immediate_clock_enabled(window, item["label"]) for item in headers
    )
    all_immediate_gdsc_off = bool(headers) and all(
        first_int_after_name(
            line_for(window, item["label"], "immediate_regulator", "pcie_1_gdsc"),
            "pcie_1_gdsc",
        ) == 0
        for item in headers
    )
    gpio103_high = "source=immediate_debug_gpio needle=gpio103 match= gpio103 : in 1" in window
    gpio142_low = "source=immediate_debug_gpio needle=gpio142 match= gpio142 : in 0" in window
    link_failed = "PCIe RC1 link initialization failed" in dmesg
    l0_seen = "LTSSM_STATE: LTSSM_L0" in dmesg
    downstream_absent = (
        progress.get("rc1_l0") is False
        and progress.get("mhi_progress") is False
        and progress.get("wlfw_progress") is False
        and progress.get("bdf_progress") is False
        and progress.get("fw_ready_progress") is False
        and progress.get("wlan0_present") is False
    )
    write_triggered = "state=triggered" in watcher and "write_rc=0" in watcher
    samples_too_slow = final_elapsed is not None and final_elapsed > 1000
    passed = (
        manifest.get("pass") is True
        and manifest.get("handoff_pass") is True
        and write_triggered
        and labels == ["after_case_0ms", "after_case_1ms", "after_case_5ms", "after_case_20ms"]
        and link_failed
        and not l0_seen
        and downstream_absent
        and all_immediate_gdsc_off
        and all_immediate_clocks_off
        and gpio103_high
        and gpio142_low
        and samples_too_slow
    )
    decision = (
        "v1440-immediate-sampler-too-slow-no-l0"
        if passed
        else "v1440-immediate-endpoint-needs-more-evidence"
    )
    reason = (
        "V1439 confirmed no L0/MHI/WLFW/wlan0, but debugfs exact immediate samples take seconds and cannot resolve the sub-100ms RC1 active window"
        if passed
        else "V1439 immediate endpoint evidence did not satisfy the classifier contract"
    )
    return {
        "cycle": "V1440",
        "decision": decision,
        "pass": passed,
        "reason": reason,
        "inputs": {
            "manifest": rel(manifest_path),
            "window": rel(window_path),
            "dmesg": rel(dmesg_path),
            "watcher": rel(watcher_path),
        },
        "observations": {
            "handoff_pass": manifest.get("handoff_pass"),
            "rollback": manifest.get("rollback"),
            "write_triggered": write_triggered,
            "labels": labels,
            "immediate_elapsed_ms": elapsed_by_label,
            "final_immediate_label": final_label,
            "final_immediate_elapsed_ms": final_elapsed,
            "samples_too_slow_for_rc1_window": samples_too_slow,
            "after_case_0_pcie_1_gdsc_enable": after_case_0_gdsc,
            "all_immediate_pcie_1_gdsc_off": all_immediate_gdsc_off,
            "all_immediate_pcie1_clocks_off": all_immediate_clocks_off,
            "gpio103_clkreq_high": gpio103_high,
            "gpio142_mdm2ap_low": gpio142_low,
            "link_failed": link_failed,
            "l0_seen": l0_seen,
            "downstream_absent": downstream_absent,
        },
        "next_gate": "V1441 source/build-only micro-sampler: concurrent writer plus minimal fast reader, avoiding full debugfs summary scans in the active RC1 window",
        "guardrails": {
            "host_only": True,
            "device_command_executed": False,
            "flash_executed": False,
            "wifi_hal_scan_connect_executed": False,
            "credential_use_executed": False,
            "dhcp_route_external_ping_executed": False,
            "pmic_gpio_gdsc_write_executed": False,
            "esoc_notify_boot_done_executed": False,
            "global_pci_rescan_executed": False,
            "platform_bind_unbind_executed": False,
        },
    }


def render_report(result: dict[str, Any]) -> str:
    obs = result["observations"]
    return "\n".join(
        [
            "# Native Init V1440 Immediate Endpoint Handoff Classifier",
            "",
            "## Summary",
            "",
            "- Cycle: `V1440`",
            "- Type: host-only classifier over V1439 immediate endpoint evidence",
            f"- Decision: `{result['decision']}`",
            f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
            f"- Reason: {result['reason']}",
            "",
            "## Inputs",
            "",
            f"- Manifest: `{result['inputs']['manifest']}`",
            f"- Window: `{result['inputs']['window']}`",
            f"- Dmesg: `{result['inputs']['dmesg']}`",
            f"- Watcher: `{result['inputs']['watcher']}`",
            "",
            "## Observations",
            "",
            "| Signal | Value |",
            "| --- | --- |",
            f"| handoff pass | `{obs['handoff_pass']}` |",
            f"| rollback | `{obs['rollback']}` |",
            f"| corrected RC1 write triggered | `{obs['write_triggered']}` |",
            f"| immediate labels | `{obs['labels']}` |",
            f"| immediate elapsed ms | `{obs['immediate_elapsed_ms']}` |",
            f"| samples too slow for RC1 window | `{obs['samples_too_slow_for_rc1_window']}` |",
            f"| after-case-0 `pcie_1_gdsc` enable | `{obs['after_case_0_pcie_1_gdsc_enable']}` |",
            f"| all immediate pcie1 GDSC off | `{obs['all_immediate_pcie_1_gdsc_off']}` |",
            f"| all immediate pcie1 clocks off | `{obs['all_immediate_pcie1_clocks_off']}` |",
            f"| GPIO103/CLKREQ high | `{obs['gpio103_clkreq_high']}` |",
            f"| GPIO142/MDM2AP low | `{obs['gpio142_mdm2ap_low']}` |",
            f"| link failed | `{obs['link_failed']}` |",
            f"| L0 seen | `{obs['l0_seen']}` |",
            f"| downstream absent | `{obs['downstream_absent']}` |",
            "",
            "## Classification",
            "",
            "V1439 still fails before `LTSSM L0`; no MHI, WLFW, BDF, FW-ready, or",
            "`wlan0` appears. The immediate exact sampler does not solve the timing",
            "problem because scanning debugfs regulator/clock summaries is slower",
            "than the RC1 active window. The `after_case_1ms` label appears at",
            "`2402ms` immediate elapsed, and `after_case_20ms` appears at `8634ms`.",
            "",
            "The useful next change is not Wi-Fi HAL/scan/connect. It is a source-only",
            "test-boot instrumentation change: use a concurrent writer plus a minimal",
            "fast reader, or remove slow summary scans from the active RC1 window.",
            "",
            "## Safety Scope",
            "",
            "This cycle was host-only. It did not run device commands, flash, reboot,",
            "write partitions, handle credentials, scan/connect Wi-Fi, run DHCP/routes,",
            "ping externally, write PMIC/GPIO/GDSC controls, spoof eSoC notify/",
            "`BOOT_DONE`, run global PCI rescan, or bind/unbind platform devices.",
            "",
        ]
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_DIR)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--write-report", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = classify(args)
    report = render_report(result)
    store = EvidenceStore(args.out_dir)
    store.write_json("manifest.json", result)
    store.write_text("summary.md", report)
    if args.write_report:
        write_private_text(args.report_path, report)
    print(
        json.dumps(
            {
                "decision": result["decision"],
                "pass": result["pass"],
                "out_dir": rel(args.out_dir),
                "next_gate": result["next_gate"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

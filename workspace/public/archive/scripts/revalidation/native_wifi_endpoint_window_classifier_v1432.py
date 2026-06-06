#!/usr/bin/env python3
"""V1432 host-only classifier for V1431 endpoint window evidence."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from a90harness.evidence import EvidenceStore, write_private_text


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
DEFAULT_INPUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1431-wifi-test-boot-endpoint-prereq-handoff"
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1432-endpoint-window-classifier"
DEFAULT_REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1432_ENDPOINT_WINDOW_CLASSIFIER_2026-06-01.md"
)
SAMPLE_RE = re.compile(r"sample=([^ ]+)")


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def first_int_after_name(line: str, name: str) -> int | None:
    if name not in line:
        return None
    tail = line.split(name, 1)[1].strip()
    if not tail:
        return None
    first_token = tail.split()[0]
    try:
        return int(first_token)
    except ValueError:
        return None


def collect_sample_lines(window_text: str) -> dict[str, list[str]]:
    samples: dict[str, list[str]] = {}
    for line in window_text.splitlines():
        match = SAMPLE_RE.search(line)
        if not match:
            continue
        samples.setdefault(match.group(1), []).append(line)
    return samples


def lines_with(lines: list[str], needle: str) -> list[str]:
    return [line for line in lines if needle in line]


def first_line_with(lines: list[str], needle: str) -> str:
    matches = lines_with(lines, needle)
    return matches[0] if matches else ""


def pcie_clock_lines(lines: list[str]) -> list[str]:
    names = (
        "gcc_pcie_1_slv_q2a_axi_clk",
        "gcc_pcie_1_slv_axi_clk",
        "gcc_pcie_1_pipe_clk",
        "gcc_pcie_1_mstr_axi_clk",
        "gcc_pcie_1_clkref_clk",
        "gcc_pcie_1_cfg_ahb_clk",
        "gcc_pcie1_phy_refgen_clk",
        "gcc_pcie_phy_refgen_clk_src",
    )
    return [line for line in lines if any(name in line for name in names)]


def any_clock_enabled(lines: list[str]) -> bool:
    for line in pcie_clock_lines(lines):
        for name in (
            "gcc_pcie_1_slv_q2a_axi_clk",
            "gcc_pcie_1_slv_axi_clk",
            "gcc_pcie_1_mstr_axi_clk",
            "gcc_pcie_1_clkref_clk",
            "gcc_pcie_1_cfg_ahb_clk",
            "gcc_pcie1_phy_refgen_clk",
            "gcc_pcie_phy_refgen_clk_src",
        ):
            value = first_int_after_name(line, name)
            if value and value > 0:
                return True
    return False


def classify(args: argparse.Namespace) -> dict[str, Any]:
    manifest_path = args.input_dir / "manifest.json"
    window_path = args.input_dir / "test-rc1-window-result.stdout.txt"
    dmesg_path = args.input_dir / "test-v1393-dmesg.stdout.txt"
    manifest = json.loads(read_text(manifest_path))
    window_text = read_text(window_path)
    dmesg_text = read_text(dmesg_path)
    progress = manifest.get("wifi_progress", {})
    samples = collect_sample_lines(window_text)

    pre_delay = samples.get("pre_delay", [])
    pre_rc1 = samples.get("pre_rc1", [])
    post_50 = samples.get("post_rc1_50ms", [])
    post_150 = samples.get("post_rc1_150ms", [])
    post_500 = samples.get("post_rc1_500ms", [])

    pre_delay_gdsc = first_int_after_name(first_line_with(pre_delay, "pcie_1_gdsc"), "pcie_1_gdsc")
    pre_rc1_gdsc = first_int_after_name(first_line_with(pre_rc1, "pcie_1_gdsc"), "pcie_1_gdsc")
    post_50_gdsc = first_int_after_name(first_line_with(post_50, "pcie_1_gdsc"), "pcie_1_gdsc")
    post_500_gdsc = first_int_after_name(first_line_with(post_500, "pcie_1_gdsc"), "pcie_1_gdsc")
    clkreq_high = any("gpio103" in line and " in 1 " in line for line in pre_rc1 + post_50 + post_150 + post_500)
    endpoint_sampler_seen = "endpoint_sampler=1" in window_text
    sampler_name_seen = "read-only-v1429-endpoint-prereq" in window_text
    pre_rc1_clock_enabled = any_clock_enabled(pre_rc1)
    post_50_clock_enabled = any_clock_enabled(post_50)
    post_500_clock_enabled = any_clock_enabled(post_500)
    link_failed = "PCIe RC1 link initialization failed" in dmesg_text
    l0_seen = "LTSSM_STATE: LTSSM_L0" in dmesg_text
    downstream_absent = (
        progress.get("rc1_l0") is False
        and progress.get("mhi_progress") is False
        and progress.get("wlfw_progress") is False
        and progress.get("wlan0_present") is False
    )
    ap_side_window_seen = (
        endpoint_sampler_seen
        and sampler_name_seen
        and pre_delay_gdsc == 0
        and pre_rc1_gdsc == 1
        and pre_rc1_clock_enabled
        and post_50_gdsc == 0
        and not post_50_clock_enabled
        and post_500_gdsc == 0
        and not post_500_clock_enabled
        and clkreq_high
    )
    passed = (
        manifest.get("pass") is True
        and manifest.get("handoff_pass") is True
        and ap_side_window_seen
        and link_failed
        and not l0_seen
        and downstream_absent
    )
    decision = (
        "v1432-ap-rc1-prereqs-toggle-but-endpoint-no-l0"
        if passed
        else "v1432-endpoint-window-needs-more-evidence"
    )
    reason = (
        "V1431 shows AP-side pcie1 GDSC/clocks toggle in the corrected-RC1 window, but the endpoint still never reaches L0"
        if passed
        else "V1431 endpoint window evidence did not cleanly classify the AP-side prerequisite state"
    )
    return {
        "cycle": "V1432",
        "decision": decision,
        "pass": passed,
        "reason": reason,
        "inputs": {
            "manifest": rel(manifest_path),
            "window": rel(window_path),
            "dmesg": rel(dmesg_path),
        },
        "handoff": {
            "pass": manifest.get("pass"),
            "handoff_pass": manifest.get("handoff_pass"),
            "rollback": manifest.get("rollback"),
        },
        "observations": {
            "endpoint_sampler_seen": endpoint_sampler_seen,
            "sampler_name_seen": sampler_name_seen,
            "sample_count": progress.get("pid1_rc1_window_sample_count"),
            "pre_delay_pcie_1_gdsc_enable": pre_delay_gdsc,
            "pre_rc1_pcie_1_gdsc_enable": pre_rc1_gdsc,
            "post_50_pcie_1_gdsc_enable": post_50_gdsc,
            "post_500_pcie_1_gdsc_enable": post_500_gdsc,
            "pre_rc1_clock_enabled": pre_rc1_clock_enabled,
            "post_50_clock_enabled": post_50_clock_enabled,
            "post_500_clock_enabled": post_500_clock_enabled,
            "clkreq_gpio103_high": clkreq_high,
            "link_failed": link_failed,
            "l0_seen": l0_seen,
            "downstream_absent": downstream_absent,
            "pre_rc1_pcie_clock_lines": pcie_clock_lines(pre_rc1),
            "post_50_pcie_clock_lines": pcie_clock_lines(post_50),
            "post_500_pcie_clock_lines": pcie_clock_lines(post_500),
        },
        "next_gate": "V1433 host/source plan for focused endpoint parity: reduce clock-summary truncation or capture Android pcie1 reference",
        "guardrails": {
            "host_only": True,
            "device_command_executed": False,
            "flash_executed": False,
            "wifi_hal_scan_connect_executed": False,
            "credential_use_executed": False,
            "dhcp_route_external_ping_executed": False,
            "pmic_gpio_gdsc_write_executed": False,
            "esoc_notify_boot_done_executed": False,
        },
    }


def render_report(result: dict[str, Any]) -> str:
    observations = result["observations"]
    return "\n".join(
        [
            "# Native Init V1432 Endpoint Window Classifier",
            "",
            "## Summary",
            "",
            "- Cycle: `V1432`",
            "- Type: host-only classifier over V1431 endpoint-sampler evidence",
            f"- Decision: `{result['decision']}`",
            f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
            f"- Reason: {result['reason']}",
            "",
            "## Inputs",
            "",
            f"- Manifest: `{result['inputs']['manifest']}`",
            f"- Window: `{result['inputs']['window']}`",
            f"- Dmesg: `{result['inputs']['dmesg']}`",
            "",
            "## Observations",
            "",
            "| Signal | Value |",
            "| --- | --- |",
            f"| endpoint sampler seen | `{observations['endpoint_sampler_seen']}` |",
            f"| sample count | `{observations['sample_count']}` |",
            f"| pre-delay `pcie_1_gdsc` enable | `{observations['pre_delay_pcie_1_gdsc_enable']}` |",
            f"| pre-RC1 `pcie_1_gdsc` enable | `{observations['pre_rc1_pcie_1_gdsc_enable']}` |",
            f"| post-50ms `pcie_1_gdsc` enable | `{observations['post_50_pcie_1_gdsc_enable']}` |",
            f"| post-500ms `pcie_1_gdsc` enable | `{observations['post_500_pcie_1_gdsc_enable']}` |",
            f"| pre-RC1 pcie1 clocks enabled | `{observations['pre_rc1_clock_enabled']}` |",
            f"| post-50ms pcie1 clocks enabled | `{observations['post_50_clock_enabled']}` |",
            f"| post-500ms pcie1 clocks enabled | `{observations['post_500_clock_enabled']}` |",
            f"| GPIO103/CLKREQ high | `{observations['clkreq_gpio103_high']}` |",
            f"| link failed | `{observations['link_failed']}` |",
            f"| L0 seen | `{observations['l0_seen']}` |",
            f"| downstream absent | `{observations['downstream_absent']}` |",
            "",
            "## Classification",
            "",
            "V1431 no longer supports the broad claim that pcie1 never powers in the",
            "test window. The corrected-RC1 path briefly enables the AP-side pcie1",
            "GDSC/clock set, then disables it again after the endpoint fails before",
            "L0. GPIO103/CLKREQ is high/pull-up in the same window. The remaining",
            "gap is therefore narrower: endpoint response/parity at PERST release,",
            "not another blind RC1 retry or direct GDSC/PMIC/GPIO write.",
            "",
            "## Next",
            "",
            "V1433 should stay host/source-only first. Two useful options are:",
            "",
            "1. refine the native endpoint sampler to avoid clock-summary truncation",
            "   and emit exact pcie1 clock/GDSC/PERST/CLKREQ fields; or",
            "2. capture an Android-side pcie1 clock/GDSC/CLKREQ reference for the",
            "   known-good L0 path, then compare against V1431.",
            "",
            "Do not proceed to scan/connect, credentials, DHCP/routes, or external",
            "ping until at least L0/MHI/WLFW/`wlan0` progress exists.",
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

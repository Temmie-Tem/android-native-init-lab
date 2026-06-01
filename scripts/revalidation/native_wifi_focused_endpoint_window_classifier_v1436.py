#!/usr/bin/env python3
"""V1436 host-only classifier for V1435 focused endpoint-window evidence."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from a90harness.evidence import EvidenceStore, write_private_text


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1435-wifi-test-boot-focused-endpoint-handoff"
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1436-focused-endpoint-window-classifier"
DEFAULT_REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1436_FOCUSED_ENDPOINT_WINDOW_CLASSIFIER_2026-06-01.md"
)
SAMPLE_RE = re.compile(r"sample=([^ ]+)")


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def collect_sample_lines(window_text: str) -> dict[str, list[str]]:
    samples: dict[str, list[str]] = {}
    for line in window_text.splitlines():
        match = SAMPLE_RE.search(line)
        if match:
            samples.setdefault(match.group(1), []).append(line)
    return samples


def lines_with(lines: list[str], *needles: str) -> list[str]:
    return [line for line in lines if all(needle in line for needle in needles)]


def first_line_with(lines: list[str], *needles: str) -> str:
    matches = lines_with(lines, *needles)
    return matches[0] if matches else ""


def first_int_after_name(line: str, name: str) -> int | None:
    if name not in line:
        return None
    tail = line.rsplit(name, 1)[1].strip()
    if not tail:
        return None
    token = tail.split()[0]
    try:
        return int(token)
    except ValueError:
        return None


PCIE1_CLOCKS = (
    "gcc_pcie_1_slv_q2a_axi_clk",
    "gcc_pcie_1_slv_axi_clk",
    "gcc_pcie_1_pipe_clk",
    "gcc_pcie_1_mstr_axi_clk",
    "gcc_pcie_1_clkref_clk",
    "gcc_pcie_1_cfg_ahb_clk",
    "gcc_pcie1_phy_refgen_clk",
    "gcc_pcie_phy_refgen_clk_src",
)


def clock_lines(lines: list[str], source: str) -> list[str]:
    return [
        line
        for line in lines
        if f"source={source}" in line and any(clock in line for clock in PCIE1_CLOCKS)
    ]


def any_clock_enabled(lines: list[str]) -> bool:
    for line in lines:
        for clock in PCIE1_CLOCKS:
            value = first_int_after_name(line, clock)
            if value and value > 0:
                return True
    return False


def gdsc_value(lines: list[str], source: str) -> int | None:
    line = first_line_with(lines, f"source={source}", "pcie_1_gdsc")
    return first_int_after_name(line, "pcie_1_gdsc")


def gpio_high(lines: list[str], gpio: str) -> bool:
    return any(f"needle={gpio}" in line and " in 1 " in line for line in lines)


def gpio_low(lines: list[str], gpio: str) -> bool:
    return any(f"needle={gpio}" in line and " in 0 " in line for line in lines)


def pinmux_claimed(lines: list[str], gpio: str, owner: str) -> bool:
    return any(f"needle={gpio}" in line and owner in line for line in lines)


def classify(args: argparse.Namespace) -> dict[str, Any]:
    manifest_path = args.input_dir / "manifest.json"
    window_path = args.input_dir / "test-rc1-window-result.stdout.txt"
    dmesg_path = args.input_dir / "test-v1393-dmesg.stdout.txt"
    manifest = load_json(manifest_path)
    window_text = read_text(window_path)
    dmesg_text = read_text(dmesg_path)
    progress = manifest.get("wifi_progress", {})
    samples = collect_sample_lines(window_text)

    sample_names = ["pre_delay", "pre_rc1", "post_rc1_50ms", "post_rc1_150ms", "post_rc1_500ms"]
    sample_counts = {sample: len(samples.get(sample, [])) for sample in sample_names}
    pre_rc1 = samples.get("pre_rc1", [])
    post_50 = samples.get("post_rc1_50ms", [])
    post_500 = samples.get("post_rc1_500ms", [])

    broad_pre_gdsc = gdsc_value(pre_rc1, "regulator_summary")
    focused_pre_gdsc = gdsc_value(pre_rc1, "focused_regulator")
    post_50_gdsc = gdsc_value(post_50, "focused_regulator")
    post_500_gdsc = gdsc_value(post_500, "focused_regulator")
    broad_pre_clocks = clock_lines(pre_rc1, "clk_summary")
    focused_pre_clocks = clock_lines(pre_rc1, "focused_clk")
    focused_post_50_clocks = clock_lines(post_50, "focused_clk")
    focused_post_500_clocks = clock_lines(post_500, "focused_clk")
    broad_pre_clocks_enabled = any_clock_enabled(broad_pre_clocks)
    focused_pre_clocks_enabled = any_clock_enabled(focused_pre_clocks)
    focused_post_50_clocks_enabled = any_clock_enabled(focused_post_50_clocks)
    focused_post_500_clocks_enabled = any_clock_enabled(focused_post_500_clocks)
    same_window_timing_race = (
        broad_pre_gdsc == 1
        and focused_pre_gdsc == 0
        and broad_pre_clocks_enabled
        and not focused_pre_clocks_enabled
    )
    focused_sampler_seen = "read-only-v1433-focused-endpoint-prereq" in window_text
    all_samples_present = all(count > 0 for count in sample_counts.values())
    clkreq_high = all(gpio_high(samples.get(sample, []), "gpio103") for sample in sample_names)
    mdm2ap_low = all(gpio_low(samples.get(sample, []), "gpio142") for sample in sample_names)
    perst_owned_by_rc1 = pinmux_claimed(pre_rc1, "gpio102", "1c08000.qcom,pcie")
    clkreq_function = any(
        "needle=gpio103" in line and "function pci_e1" in line
        for sample in sample_names
        for line in samples.get(sample, [])
    )
    link_failed = "PCIe RC1 link initialization failed" in dmesg_text
    l0_seen = "LTSSM_STATE: LTSSM_L0" in dmesg_text
    downstream_absent = (
        progress.get("rc1_l0") is False
        and progress.get("mhi_progress") is False
        and progress.get("wlfw_progress") is False
        and progress.get("bdf_progress") is False
        and progress.get("fw_ready_progress") is False
        and progress.get("wlan0_present") is False
    )
    post_failure_off = (
        post_50_gdsc == 0
        and post_500_gdsc == 0
        and not focused_post_50_clocks_enabled
        and not focused_post_500_clocks_enabled
    )
    passed = (
        manifest.get("pass") is True
        and manifest.get("handoff_pass") is True
        and focused_sampler_seen
        and all_samples_present
        and progress.get("rc1_progress") is True
        and link_failed
        and not l0_seen
        and downstream_absent
        and same_window_timing_race
        and post_failure_off
        and clkreq_high
        and mdm2ap_low
    )
    decision = (
        "v1436-focused-window-race-endpoint-no-l0"
        if passed
        else "v1436-focused-endpoint-window-needs-more-evidence"
    )
    reason = (
        "V1435 proves corrected RC1 still fails before L0; focused exact lines confirm endpoint no-response, but pre-RC1 GDSC/clock reads are too timing-sensitive for a stable single-sample conclusion"
        if passed
        else "V1435 focused endpoint evidence did not satisfy the classifier contract"
    )
    return {
        "cycle": "V1436",
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
            "focused_sampler_seen": focused_sampler_seen,
            "sample_counts": sample_counts,
            "broad_pre_rc1_pcie_1_gdsc_enable": broad_pre_gdsc,
            "focused_pre_rc1_pcie_1_gdsc_enable": focused_pre_gdsc,
            "focused_post_50_pcie_1_gdsc_enable": post_50_gdsc,
            "focused_post_500_pcie_1_gdsc_enable": post_500_gdsc,
            "broad_pre_rc1_clock_enabled": broad_pre_clocks_enabled,
            "focused_pre_rc1_clock_enabled": focused_pre_clocks_enabled,
            "focused_post_50_clock_enabled": focused_post_50_clocks_enabled,
            "focused_post_500_clock_enabled": focused_post_500_clocks_enabled,
            "same_window_timing_race": same_window_timing_race,
            "gpio103_clkreq_high_all_samples": clkreq_high,
            "gpio142_mdm2ap_low_all_samples": mdm2ap_low,
            "gpio102_perst_owned_by_rc1": perst_owned_by_rc1,
            "gpio103_clkreq_pci_e1_function_seen": clkreq_function,
            "link_failed": link_failed,
            "l0_seen": l0_seen,
            "downstream_absent": downstream_absent,
            "post_failure_pcie1_off": post_failure_off,
            "broad_pre_rc1_clock_lines": broad_pre_clocks,
            "focused_pre_rc1_clock_lines": focused_pre_clocks,
        },
        "next_gate": "V1437 source/build-only tighter in-PID1 immediate around-write endpoint sampler, or Android reference capture before new mutation",
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
    observations = result["observations"]
    counts = observations["sample_counts"]
    return "\n".join(
        [
            "# Native Init V1436 Focused Endpoint Window Classifier",
            "",
            "## Summary",
            "",
            "- Cycle: `V1436`",
            "- Type: host-only classifier over V1435 focused endpoint evidence",
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
            f"| focused sampler seen | `{observations['focused_sampler_seen']}` |",
            f"| pre-delay sample lines | `{counts['pre_delay']}` |",
            f"| pre-RC1 sample lines | `{counts['pre_rc1']}` |",
            f"| post-50ms sample lines | `{counts['post_rc1_50ms']}` |",
            f"| post-150ms sample lines | `{counts['post_rc1_150ms']}` |",
            f"| post-500ms sample lines | `{counts['post_rc1_500ms']}` |",
            f"| broad pre-RC1 `pcie_1_gdsc` enable | `{observations['broad_pre_rc1_pcie_1_gdsc_enable']}` |",
            f"| focused pre-RC1 `pcie_1_gdsc` enable | `{observations['focused_pre_rc1_pcie_1_gdsc_enable']}` |",
            f"| focused post-50ms `pcie_1_gdsc` enable | `{observations['focused_post_50_pcie_1_gdsc_enable']}` |",
            f"| focused post-500ms `pcie_1_gdsc` enable | `{observations['focused_post_500_pcie_1_gdsc_enable']}` |",
            f"| broad pre-RC1 pcie1 clocks enabled | `{observations['broad_pre_rc1_clock_enabled']}` |",
            f"| focused pre-RC1 pcie1 clocks enabled | `{observations['focused_pre_rc1_clock_enabled']}` |",
            f"| focused post-50ms pcie1 clocks enabled | `{observations['focused_post_50_clock_enabled']}` |",
            f"| focused post-500ms pcie1 clocks enabled | `{observations['focused_post_500_clock_enabled']}` |",
            f"| same-window timing race | `{observations['same_window_timing_race']}` |",
            f"| GPIO103/CLKREQ high in all samples | `{observations['gpio103_clkreq_high_all_samples']}` |",
            f"| GPIO142/MDM2AP low in all samples | `{observations['gpio142_mdm2ap_low_all_samples']}` |",
            f"| GPIO102/PERST owned by RC1 | `{observations['gpio102_perst_owned_by_rc1']}` |",
            f"| GPIO103 pci_e1 function seen | `{observations['gpio103_clkreq_pci_e1_function_seen']}` |",
            f"| link failed | `{observations['link_failed']}` |",
            f"| L0 seen | `{observations['l0_seen']}` |",
            f"| downstream absent | `{observations['downstream_absent']}` |",
            f"| post-failure pcie1 off | `{observations['post_failure_pcie1_off']}` |",
            "",
            "## Classification",
            "",
            "V1435 confirms the current native path reaches the corrected RC1/LTSSM",
            "window but still fails before `LTSSM L0`. No MHI, WLFW, BDF, FW-ready,",
            "or `wlan0` evidence appears, so Wi-Fi scan/connect remains out of",
            "scope.",
            "",
            "The focused sampler improves the signal quality by emitting exact pcie1",
            "regulator, clock, GPIO, pinmux, and pinconf lines. It also shows that",
            "the `pre_rc1` window is still too wide for a stable one-read conclusion:",
            "the broad pass saw pcie1 GDSC/clocks enabled, while later focused exact",
            "reads in the same logical sample saw them already disabled. The next",
            "instrumentation should sample the exact fields immediately around the",
            "`case=11` write inside the PID1 test-boot process, or compare against an",
            "Android positive reference, before changing lower hardware controls.",
            "",
            "## Next",
            "",
            "- Preferred V1437: source/build-only tighter in-PID1 around-write sampler",
            "  for pcie1 GDSC/clocks, PERST/CLKREQ/WAKE/MDM2AP, and LTSSM.",
            "- Alternative: Android-side positive reference capture for the same exact",
            "  fields around the known-good L0 path.",
            "- Do not proceed to Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or",
            "  external ping until at least L0/MHI/WLFW/`wlan0` progress exists.",
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

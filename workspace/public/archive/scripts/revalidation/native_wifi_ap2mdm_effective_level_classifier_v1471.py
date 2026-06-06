#!/usr/bin/env python3
"""V1471 host-only AP2MDM effective-level and pinctrl ownership classifier."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from a90harness.evidence import EvidenceStore


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
DEFAULT_V1470_MANIFEST = REPO_ROOT / "tmp" / "wifi" / "v1470-provider-pil-gpio-classifier" / "manifest.json"
DEFAULT_V1469_DIR = REPO_ROOT / "tmp" / "wifi" / "v1469-wifi-test-boot-exact-provider-pil-gpio-tracepoint-handoff"
DEFAULT_SDX5XM_DTS = (
    REPO_ROOT
    / "kernel_build"
    / "SM-A908N_KOR_12_Opensource"
    / "Kernel"
    / "arch"
    / "arm64"
    / "boot"
    / "dts"
    / "qcom"
    / "sdx5xm-external-soc.dtsi"
)
DEFAULT_SM8150_PINCTRL_DTS = (
    REPO_ROOT
    / "kernel_build"
    / "SM-A908N_KOR_12_Opensource"
    / "Kernel"
    / "arch"
    / "arm64"
    / "boot"
    / "dts"
    / "qcom"
    / "sm8150-pinctrl.dtsi"
)
DEFAULT_GPIO_TRACE_HEADER = (
    REPO_ROOT
    / "kernel_build"
    / "SM-A908N_KOR_12_Opensource"
    / "Kernel"
    / "include"
    / "trace"
    / "events"
    / "gpio.h"
)
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1471-ap2mdm-effective-level-classifier"
DEFAULT_REPORT_PATH = REPO_ROOT / "docs" / "reports" / "NATIVE_INIT_V1471_AP2MDM_EFFECTIVE_LEVEL_CLASSIFIER_2026-06-01.md"


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def read_json(path: Path) -> dict[str, Any]:
    text = read_text(path)
    if not text:
        return {}
    return json.loads(text)


def first_match(pattern: str, text: str) -> str:
    match = re.search(pattern, text, re.MULTILINE | re.DOTALL)
    if not match:
        return ""
    return match.group(0)


def extract_gpio_debug_lines(window_text: str, gpio: int) -> list[str]:
    needle = f"needle=gpio{gpio} match="
    lines: list[str] = []
    for line in window_text.splitlines():
        if needle in line:
            lines.append(line.split("match=", 1)[1].strip())
    return sorted(set(lines))


def classify(args: argparse.Namespace) -> dict[str, Any]:
    v1470 = read_json(args.v1470_manifest)
    window_text = read_text(args.v1469_dir / "test-rc1-window-result.stdout.txt")
    sdx5xm_dts = read_text(args.sdx5xm_dts)
    sm8150_pinctrl = read_text(args.sm8150_pinctrl_dts)
    gpio_trace_header = read_text(args.gpio_trace_header)

    trace = v1470.get("trace", {})
    samples = v1470.get("samples", {})
    progress = v1470.get("progress", {})
    gpio135_lines = extract_gpio_debug_lines(window_text, 135)
    gpio142_lines = extract_gpio_debug_lines(window_text, 142)

    active_block = first_match(
        r"ap2mdm_active: ap2mdm_active \{.*?drive-strength = <16>;\s*bias-disable;",
        sm8150_pinctrl,
    )
    sleep_block = first_match(
        r"ap2mdm_sleep: ap2mdm_sleep \{.*?drive-strength = <8>;\s*bias-disable;",
        sm8150_pinctrl,
    )
    mdm2ap_block = first_match(
        r"mdm2ap_active: mdm2ap_active \{.*?pins = \"gpio142\", \"gpio53\";.*?bias-disable;",
        sm8150_pinctrl,
    )

    checks = {
        "v1470_pass": bool(v1470.get("pass"))
        and v1470.get("decision") == "v1470-ap2mdm-set-called-but-not-effective-no-mdm2ap-no-rc1",
        "gpio_direction_trace_err_semantics": "TP_PROTO(unsigned gpio, int in, int err)" in gpio_trace_header
        and 'TP_printk("%u %3s (%d)"' in gpio_trace_header,
        "gpio_value_trace_set_semantics": "TP_PROTO(unsigned gpio, int get, int value)" in gpio_trace_header
        and 'TP_printk("%u %3s %d"' in gpio_trace_header,
        "sdx5xm_maps_gpio135_ap2mdm": 'qcom,ap2mdm-status-gpio   = <&tlmm 135 0x00>;' in sdx5xm_dts,
        "sdx5xm_uses_active_pinctrl": "pinctrl-1 = <&ap2mdm_active &mdm2ap_active>;" in sdx5xm_dts,
        "ap2mdm_active_gpio_function": 'pins = "gpio135", "gpio141";' in active_block and 'function = "gpio";' in active_block,
        "ap2mdm_active_drive_16_bias_disable": "drive-strength = <16>;" in active_block and "bias-disable;" in active_block,
        "ap2mdm_sleep_drive_8_bias_disable": "drive-strength = <8>;" in sleep_block and "bias-disable;" in sleep_block,
        "mdm2ap_active_gpio142_present": 'pins = "gpio142", "gpio53";' in mdm2ap_block,
        "v1469_gpio135_debug_matches_active_config": any("gpio135 : out 0 16mA no pull" in line for line in gpio135_lines),
        "v1469_gpio142_debug_matches_active_config": any("gpio142 : in 0 8mA no pull" in line for line in gpio142_lines),
        "v1470_ap2mdm_set_called": int(trace.get("gpio135_set1_count") or 0) > 0,
        "v1470_no_gpio135_high_samples": int(samples.get("gpio135_high_sample_count") or 0) == 0,
        "v1470_no_gpio142_high_samples": int(samples.get("gpio142_high_sample_count") or 0) == 0,
        "v1470_no_irq_or_downstream": int(samples.get("mdm_status_irq_nonzero_count") or 0) == 0
        and int(samples.get("pcie_wake_irq_nonzero_count") or 0) == 0
        and bool(progress.get("downstream_absent")),
    }

    pass_condition = all(checks.values())
    if pass_condition:
        decision = "v1471-ap2mdm-active-pinctrl-present-effective-output-low"
        reason = (
            "Source and live evidence show the AP2MDM pinctrl path is present and active-configured, "
            "and the provider calls GPIO135 set-high, but readback remains low with no GPIO142/PCIe/Wi-Fi downstream response."
        )
        next_gate = "V1472 source/build-only extended AP2MDM effective-level sampler"
    else:
        decision = "v1471-ap2mdm-effective-level-needs-review"
        reason = "AP2MDM effective-level/source ownership evidence did not satisfy the classifier contract."
        next_gate = "review V1470/V1469 evidence and DTS inputs before another live mutation"

    return {
        "cycle": "V1471",
        "decision": decision,
        "pass": pass_condition,
        "reason": reason,
        "inputs": {
            "v1470_manifest": rel(args.v1470_manifest),
            "v1469_dir": rel(args.v1469_dir),
            "sdx5xm_dts": rel(args.sdx5xm_dts),
            "sm8150_pinctrl_dts": rel(args.sm8150_pinctrl_dts),
            "gpio_trace_header": rel(args.gpio_trace_header),
        },
        "checks": checks,
        "evidence": {
            "gpio135_debug_lines": gpio135_lines,
            "gpio142_debug_lines": gpio142_lines,
            "gpio135_set1_delta_ms": trace.get("gpio135_set1_delta_ms"),
            "gpio1270_set1_delta_ms": trace.get("gpio1270_set1_delta_ms"),
            "wchan_values": samples.get("wchan_values"),
            "downstream_absent": progress.get("downstream_absent"),
        },
        "interpretation": {
            "gpio_direction_out_zero_is_error_code": checks["gpio_direction_trace_err_semantics"],
            "gpio_value_set_one_is_set_high_call": checks["gpio_value_trace_set_semantics"],
            "pinctrl_active_state_observed": checks["v1469_gpio135_debug_matches_active_config"],
            "ownership_gap_closed": checks["sdx5xm_maps_gpio135_ap2mdm"] and checks["ap2mdm_active_gpio_function"],
            "effective_level_gap_open": checks["v1470_ap2mdm_set_called"] and checks["v1470_no_gpio135_high_samples"],
        },
        "guardrails": {
            "host_only": True,
            "device_command_executed": False,
            "flash_executed": False,
            "wifi_hal_scan_connect_executed": False,
            "credential_use_executed": False,
            "dhcp_route_external_ping_executed": False,
            "pmic_gpio_gdsc_write_executed": False,
        },
        "next_gate": next_gate,
    }


def render_report(result: dict[str, Any]) -> str:
    checks = result["checks"]
    evidence = result["evidence"]
    interpretation = result["interpretation"]
    check_lines = [f"- `{key}`: `{value}`" for key, value in sorted(checks.items())]
    return "\n".join([
        "# Native Init V1471 AP2MDM Effective-Level Classifier",
        "",
        "## Summary",
        "",
        "- Cycle: `V1471`",
        "- Type: host-only classifier over V1470/V1469 plus OSRC DTS/tracepoint source",
        f"- Decision: `{result['decision']}`",
        f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
        f"- Reason: {result['reason']}",
        "",
        "## Inputs",
        "",
        f"- V1470 manifest: `{result['inputs']['v1470_manifest']}`",
        f"- V1469 evidence: `{result['inputs']['v1469_dir']}`",
        f"- SDX5XM DTS: `{result['inputs']['sdx5xm_dts']}`",
        f"- SM8150 pinctrl DTS: `{result['inputs']['sm8150_pinctrl_dts']}`",
        f"- GPIO trace header: `{result['inputs']['gpio_trace_header']}`",
        "",
        "## Checks",
        "",
        *check_lines,
        "",
        "## Evidence",
        "",
        f"- GPIO135 debug readback lines: `{evidence['gpio135_debug_lines']}`",
        f"- GPIO142 debug readback lines: `{evidence['gpio142_debug_lines']}`",
        f"- GPIO1270/PON set-high delta ms: `{evidence['gpio1270_set1_delta_ms']}`",
        f"- GPIO135/AP2MDM set-high delta ms: `{evidence['gpio135_set1_delta_ms']}`",
        f"- provider thread wchan values: `{evidence['wchan_values']}`",
        f"- downstream absent: `{evidence['downstream_absent']}`",
        "",
        "## Interpretation",
        "",
        f"- `gpio_direction: ... out (0)` means direction-output succeeded with error code 0: `{interpretation['gpio_direction_out_zero_is_error_code']}`",
        f"- `gpio_value: 135 set 1` is the AP2MDM set-high call: `{interpretation['gpio_value_set_one_is_set_high_call']}`",
        f"- AP2MDM source ownership is present in DTS/pinctrl: `{interpretation['ownership_gap_closed']}`",
        f"- Active pinctrl configuration is visible in live readback: `{interpretation['pinctrl_active_state_observed']}`",
        f"- Effective output level remains the open gap: `{interpretation['effective_level_gap_open']}`",
        "",
        "This rules out a simple missing AP2MDM source mapping or missing active",
        "pinctrl state. The lower provider reaches the AP2MDM set-high call, but",
        "the sampled effective line stays low and MDM2AP/PCIe/Wi-Fi downstream",
        "progress remains absent. The next test boot should extend observation of",
        "effective GPIO135 state and pinctrl/debugfs surfaces after the set-high",
        "call without adding writes.",
        "",
        "## Safety Scope",
        "",
        "This classifier was host-only. It did not issue device commands, flash,",
        "reboot, start Wi-Fi HAL, scan/connect, use credentials, configure",
        "DHCP/routes, perform external ping, or write PMIC/GPIO/GDSC/eSoC controls.",
        "",
        "## Next",
        "",
        result["next_gate"],
        "",
    ])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--v1470-manifest", type=Path, default=DEFAULT_V1470_MANIFEST)
    parser.add_argument("--v1469-dir", type=Path, default=DEFAULT_V1469_DIR)
    parser.add_argument("--sdx5xm-dts", type=Path, default=DEFAULT_SDX5XM_DTS)
    parser.add_argument("--sm8150-pinctrl-dts", type=Path, default=DEFAULT_SM8150_PINCTRL_DTS)
    parser.add_argument("--gpio-trace-header", type=Path, default=DEFAULT_GPIO_TRACE_HEADER)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--write-report", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = classify(args)
    store = EvidenceStore(args.out_dir)
    store.write_json("manifest.json", result)
    store.write_text("summary.md", render_report(result))
    if args.write_report:
        args.report_path.parent.mkdir(parents=True, exist_ok=True)
        args.report_path.write_text(render_report(result), encoding="utf-8")
    print(json.dumps({"decision": result["decision"], "pass": result["pass"], "next": result["next_gate"]}, indent=2))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

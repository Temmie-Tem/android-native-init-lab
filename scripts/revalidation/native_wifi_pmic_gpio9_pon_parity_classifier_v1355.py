#!/usr/bin/env python3
"""V1355 host-only PM8150L GPIO9/PON parity classifier."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import markdown_table, repo_path
from a90harness.evidence import write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1355-pmic-gpio9-pon-parity-classifier")
REPORT_PATH = Path("docs/reports/NATIVE_INIT_V1355_PMIC_GPIO9_PON_PARITY_CLASSIFIER_2026-06-01.md")

V1276_REPORT = Path("docs/reports/NATIVE_INIT_V1276_PMIC_GPIO9_POLARITY_CLASSIFIER_2026-05-31.md")
V1318_REPORT = Path("docs/reports/NATIVE_INIT_V1318_CRITICAL_LOWER_TRACE_COLLECTOR_2026-05-31.md")
V1354_REPORT = Path("docs/reports/NATIVE_INIT_V1354_PCIE1_RC_POWER_OBSERVER_LIVE_2026-06-01.md")
SDX50M_DTS = Path("kernel_build/SM-A908N_KOR_12_Opensource/Kernel/arch/arm64/boot/dts/qcom/sdx5xm-external-soc.dtsi")
R3Q_OVERLAY = Path(
    "kernel_build/SM-A908N_KOR_12_Opensource/Kernel/arch/arm64/boot/dts/samsung/renovation/"
    "sm8150-sec-r3q-kor-overlay-r03.dts"
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def read_text(path: Path) -> str:
    return repo_path(path).read_text(encoding="utf-8", errors="replace")


def bool_text(value: bool) -> str:
    return "true" if value else "false"


def extract_gpio_event_time(text: str, gpio: int, action: str) -> float | None:
    pattern = re.compile(
        rf"(?P<time>\d+\.\d+):\s+gpio_value:\s+{gpio}\s+{re.escape(action)}\b"
    )
    match = pattern.search(text)
    return float(match.group("time")) if match else None


def classify() -> dict[str, Any]:
    v1276 = read_text(V1276_REPORT)
    v1318 = read_text(V1318_REPORT)
    v1354 = read_text(V1354_REPORT)
    sdx50m_dts = read_text(SDX50M_DTS)
    r3q_overlay = read_text(R3Q_OVERLAY)

    gpio1270_set0 = extract_gpio_event_time(v1318, 1270, "set 0")
    gpio1270_set1 = extract_gpio_event_time(v1318, 1270, "set 1")
    gpio135_set1 = extract_gpio_event_time(v1318, 135, "set 1")

    pon_low_pulse_ms = None
    ap2mdm_after_pon_high_ms = None
    ap2mdm_after_pon_low_ms = None
    if gpio1270_set0 is not None and gpio1270_set1 is not None:
        pon_low_pulse_ms = round((gpio1270_set1 - gpio1270_set0) * 1000, 3)
    if gpio1270_set1 is not None and gpio135_set1 is not None:
        ap2mdm_after_pon_high_ms = round((gpio135_set1 - gpio1270_set1) * 1000, 3)
    if gpio1270_set0 is not None and gpio135_set1 is not None:
        ap2mdm_after_pon_low_ms = round((gpio135_set1 - gpio1270_set0) * 1000, 3)

    checks = {
        "dts_ext_sdx50m": 'compatible = "qcom,ext-sdx50m"' in r3q_overlay,
        "dts_soft_reset_gpio": "qcom,ap2mdm-soft-reset-gpio" in sdx50m_dts
        and "<&pm8150l_gpios 9 0>" in sdx50m_dts,
        "dts_pon_control_label": "MDM PON" in sdx50m_dts,
        "dts_no_mdm3_regulator_supply": "regulator-supply" not in sdx50m_dts
        and "vdd-supply" not in sdx50m_dts,
        "v1276_gpio9_state_match": "PMIC GPIO9 state match | `true`" in v1276,
        "v1276_native_out_high": "native PMIC GPIO9 | `out/high`" in v1276,
        "v1276_android_out_high": "Android/reference PMIC GPIO9 | `out/high`" in v1276,
        "v1318_pon_toggle_observed": gpio1270_set0 is not None and gpio1270_set1 is not None,
        "v1318_ap2mdm_after_pon": gpio135_set1 is not None
        and gpio1270_set1 is not None
        and gpio135_set1 > gpio1270_set1,
        "v1318_gpio142_absent": "GPIO1270 / GPIO135 / GPIO142 lines | 5 / 2 / 0" in v1318,
        "v1354_pcie1_rc_stayed_off": "v1354-current-route-pcie1-rc-stayed-off" in v1354,
        "v1354_gdsc_0mv": "pcie_1_gdsc" in v1354 and "0mV" in v1354,
        "v1354_perst_low": "gpio102 : out 0" in v1354,
    }

    exact_reset_time_ms_available = "reset-time-ms" in sdx50m_dts or "reset-time-ms" in r3q_overlay
    pass_condition = all(checks.values()) and not exact_reset_time_ms_available
    decision = (
        "v1355-pon-parity-closed-pcie1-rc-next"
        if pass_condition
        else "v1355-pon-parity-needs-more-evidence"
    )
    reason = (
        "PM8150L GPIO9/PON is mapped to the expected ext-sdx50m soft-reset line, "
        "native and Android steady-state polarity both show out/high, and V1318 "
        "captured the proprietary native PON low/high pulse before AP2MDM. V1354 "
        "then showed pcie1 RC stayed off, so PON is not the shortest remaining blocker."
        if pass_condition
        else "one or more PON parity inputs were missing or contradictory"
    )
    next_step = (
        "design a bounded reboot-safe pcie1 RC enable experiment with explicit GDSC/refclk/PERST guards"
        if pass_condition
        else "collect the missing PON parity evidence before any pcie1 RC mutation"
    )

    return {
        "cycle": "v1355",
        "generated_at": now_iso(),
        "decision": decision,
        "pass": pass_condition,
        "reason": reason,
        "next_step": next_step,
        "inputs": {
            "v1276_report": str(V1276_REPORT),
            "v1318_report": str(V1318_REPORT),
            "v1354_report": str(V1354_REPORT),
            "sdx50m_dts": str(SDX50M_DTS),
            "r3q_overlay": str(R3Q_OVERLAY),
        },
        "checks": checks,
        "timing": {
            "gpio1270_set0_sec": gpio1270_set0,
            "gpio1270_set1_sec": gpio1270_set1,
            "gpio135_set1_sec": gpio135_set1,
            "pon_low_pulse_ms": pon_low_pulse_ms,
            "ap2mdm_after_pon_high_ms": ap2mdm_after_pon_high_ms,
            "ap2mdm_after_pon_low_ms": ap2mdm_after_pon_low_ms,
            "exact_reset_time_ms_available_in_public_dts": exact_reset_time_ms_available,
        },
        "guardrails": {
            "device_command_executed": False,
            "sysfs_debugfs_write_executed": False,
            "pmic_gpio_gdsc_write_executed": False,
            "esoc_notify_boot_done_executed": False,
            "wifi_hal_scan_connect_executed": False,
            "credential_use_executed": False,
            "dhcp_route_external_ping_executed": False,
            "flash_boot_partition_write_executed": False,
        },
    }


def check_rows(manifest: dict[str, Any]) -> list[list[str]]:
    return [[key, bool_text(bool(value))] for key, value in sorted(manifest["checks"].items())]


def timing_rows(manifest: dict[str, Any]) -> list[list[Any]]:
    timing = manifest["timing"]
    return [
        ["GPIO1270 set 0", timing["gpio1270_set0_sec"]],
        ["GPIO1270 set 1", timing["gpio1270_set1_sec"]],
        ["GPIO135 set 1", timing["gpio135_set1_sec"]],
        ["PON low pulse ms", timing["pon_low_pulse_ms"]],
        ["AP2MDM after PON high ms", timing["ap2mdm_after_pon_high_ms"]],
        ["AP2MDM after PON low ms", timing["ap2mdm_after_pon_low_ms"]],
        ["public DTS reset-time-ms available", timing["exact_reset_time_ms_available_in_public_dts"]],
    ]


def render_summary(manifest: dict[str, Any]) -> str:
    return "\n".join([
        "# V1355 PMIC GPIO9/PON Parity Classifier",
        "",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        "",
        markdown_table(["check", "pass"], check_rows(manifest)),
        "",
        markdown_table(["field", "value"], timing_rows(manifest)),
        "",
    ])


def render_report(manifest: dict[str, Any]) -> str:
    return "\n".join([
        "# Native Init V1355 PMIC GPIO9/PON Parity Classifier",
        "",
        "## Summary",
        "",
        "- Cycle: `V1355`",
        "- Type: host-only classifier",
        f"- Decision: `{manifest['decision']}`",
        f"- Result: {'PASS' if manifest['pass'] else 'FAIL'}",
        "- Script: `scripts/revalidation/native_wifi_pmic_gpio9_pon_parity_classifier_v1355.py`",
        "- Evidence:",
        "  - `tmp/wifi/v1355-pmic-gpio9-pon-parity-classifier/manifest.json`",
        "  - `tmp/wifi/v1355-pmic-gpio9-pon-parity-classifier/summary.md`",
        "",
        "## Inputs",
        "",
        markdown_table(["input", "path"], [[key, value] for key, value in manifest["inputs"].items()]),
        "",
        "## Checks",
        "",
        markdown_table(["check", "pass"], check_rows(manifest)),
        "",
        "## Timing Extracted From V1318",
        "",
        markdown_table(["field", "value"], timing_rows(manifest)),
        "",
        "## Interpretation",
        "",
        manifest["reason"],
        "",
        "The exact proprietary `reset-time-ms` value is not present in the public",
        "DTS/OSRC surface, but the live V1318 trace proves the native provider did",
        "toggle the PM8150L GPIO9/PON-equivalent line low then high before AP2MDM.",
        "Combined with V1276's native-vs-Android out/high parity, PON is closed",
        "enough to stop treating blind PMIC GPIO9 write/hold as the next step.",
        "",
        "## Next",
        "",
        manifest["next_step"],
        "",
        "## Safety",
        "",
        "- Host-only; no device command or live runtime access.",
        "- No sysfs/debugfs write, PMIC/GPIO/GDSC write, eSoC notify/`BOOT_DONE`,",
        "  Wi-Fi HAL, scan/connect, credential handling, DHCP/routes, external ping,",
        "  flash, boot image write, or partition write.",
        "",
    ])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("command", choices=("run",), nargs="?", default="run")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest = classify()
    out_dir = repo_path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    write_private_text(out_dir / "manifest.json", json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    write_private_text(out_dir / "summary.md", render_summary(manifest))
    write_private_text(repo_path(REPORT_PATH), render_report(manifest))
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"evidence: {out_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""V1475 host-only classifier for the V1474 effective-level live handoff evidence."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from a90harness.evidence import EvidenceStore


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_V1474_DIR = REPO_ROOT / "tmp" / "wifi" / "v1474-wifi-test-boot-effective-level-handoff"
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1475-effective-level-live-classifier"
DEFAULT_REPORT_PATH = REPO_ROOT / "docs" / "reports" / "NATIVE_INIT_V1475_EFFECTIVE_LEVEL_LIVE_CLASSIFIER_2026-06-01.md"


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


def unique_matching_lines(text: str, needle: str) -> list[str]:
    return sorted({line.strip() for line in text.splitlines() if needle in line})


def parse_window(text: str) -> dict[str, Any]:
    full_sample_labels: list[str] = []
    full_child_elapsed: list[int] = []
    for line in text.splitlines():
        match = re.match(r"rc1_window_sample label=(?P<label>\S+).* child_elapsed_ms=(?P<elapsed>-?\d+)", line)
        if match:
            full_sample_labels.append(match.group("label"))
            full_child_elapsed.append(int(match.group("elapsed")))
    return {
        "effective_marker_seen": "read-only-v1472-exact-provider-effective-level" in text,
        "full_sample_labels": full_sample_labels,
        "full_sample_count": len(full_sample_labels),
        "full_child_elapsed_ms": full_child_elapsed,
        "max_full_child_elapsed_ms": max(full_child_elapsed or [0]),
        "gpio135_low_lines": unique_matching_lines(text, "gpio135 : out 0"),
        "gpio135_high_lines": unique_matching_lines(text, "gpio135 : out 1"),
        "gpio142_low_lines": unique_matching_lines(text, "gpio142 : in 0"),
        "gpio142_high_lines": unique_matching_lines(text, "gpio142 : in 1"),
        "gpio135_pinmux_owner_lines": unique_matching_lines(text, "pin 135 (GPIO_135): soc:qcom,mdm3"),
        "gpio142_pinmux_owner_lines": unique_matching_lines(text, "pin 142 (GPIO_142): soc:qcom,mdm3"),
        "pcie1_gdsc_0mv_lines": unique_matching_lines(text, "pcie_1_gdsc 0 2 0 0mV"),
        "pcie1_pipe_clk_zero_lines": unique_matching_lines(text, "gcc_pcie_1_pipe_clk 0 0 0 0 0"),
        "pcie1_runtime_unsupported_lines": unique_matching_lines(text, "pcie1_runtime_status"),
        "esoc_pil_count": text.count("fw=esoc0"),
        "gpio135_set1_count": text.count("gpio_value: 135 set 1"),
        "ltssm_count": text.count("LTSSM"),
        "wlan0_count": text.count("wlan0"),
    }


def classify(args: argparse.Namespace) -> dict[str, Any]:
    manifest = read_json(args.v1474_dir / "manifest.json")
    window_text = read_text(args.v1474_dir / "test-rc1-window-result.stdout.txt")
    summary_text = read_text(args.v1474_dir / "test-v1393-summary.stdout.txt")
    parsed = parse_window(window_text)
    progress = manifest.get("wifi_progress", {})

    handoff_pass = (
        manifest.get("decision") == "v1474-test-boot-provider-trigger-no-downstream-rollback-pass"
        and bool(manifest.get("pass"))
        and bool(manifest.get("rollback", {}).get("ok"))
        and progress.get("provider_trigger") is True
    )
    downstream_absent = not any(
        bool(progress.get(key))
        for key in ("rc1_progress", "mhi_progress", "wlfw_progress", "bdf_progress", "fw_ready_progress", "wlan0_present")
    )
    pass_condition = (
        handoff_pass
        and parsed["effective_marker_seen"]
        and parsed["full_sample_count"] >= 6
        and parsed["max_full_child_elapsed_ms"] >= 30000
        and bool(parsed["gpio135_low_lines"])
        and not parsed["gpio135_high_lines"]
        and bool(parsed["gpio142_low_lines"])
        and not parsed["gpio142_high_lines"]
        and bool(parsed["gpio135_pinmux_owner_lines"])
        and bool(parsed["gpio142_pinmux_owner_lines"])
        and bool(parsed["pcie1_gdsc_0mv_lines"])
        and bool(parsed["pcie1_pipe_clk_zero_lines"])
        and parsed["esoc_pil_count"] > 0
        and parsed["gpio135_set1_count"] > 0
        and downstream_absent
    )
    if pass_condition:
        decision = "v1475-effective-level-low-pcie1-off-through-extended-window"
        reason = (
            "V1474 proves the effective-level sampler ran for an extended provider window: "
            "GPIO135 remains low despite the AP2MDM set-high trace, GPIO142 remains low, "
            "pinctrl ownership is soc:qcom,mdm3, pcie1 GDSC/pipe clock stay off, and no downstream Wi-Fi markers appear."
        )
        next_gate = "V1476 host-only lower-intervention design review before any write-based experiment"
    else:
        decision = "v1475-effective-level-live-needs-review"
        reason = "V1474 evidence did not satisfy the extended effective-level classifier contract."
        next_gate = "review V1474 evidence before any new live mutation"

    return {
        "cycle": "V1475",
        "decision": decision,
        "pass": pass_condition,
        "reason": reason,
        "inputs": {
            "v1474_dir": rel(args.v1474_dir),
            "v1474_manifest": rel(args.v1474_dir / "manifest.json"),
        },
        "handoff": {
            "pass": handoff_pass,
            "decision": manifest.get("decision"),
            "rollback": manifest.get("rollback", {}),
            "summary_has_final_timeout": "helper_timed_out=1" in summary_text,
        },
        "window": parsed,
        "progress": {
            "provider_trigger": progress.get("provider_trigger"),
            "modem_trigger": progress.get("modem_trigger"),
            "rc1_progress": progress.get("rc1_progress"),
            "mhi_progress": progress.get("mhi_progress"),
            "wlfw_progress": progress.get("wlfw_progress"),
            "bdf_progress": progress.get("bdf_progress"),
            "fw_ready_progress": progress.get("fw_ready_progress"),
            "wlan0_present": progress.get("wlan0_present"),
            "downstream_absent": downstream_absent,
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
    window = result["window"]
    progress = result["progress"]
    return "\n".join([
        "# Native Init V1475 Effective-Level Live Classifier",
        "",
        "## Summary",
        "",
        "- Cycle: `V1475`",
        "- Type: host-only classifier over V1474 rollbackable live handoff evidence",
        f"- Decision: `{result['decision']}`",
        f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
        f"- Reason: {result['reason']}",
        "",
        "## Inputs",
        "",
        f"- V1474 evidence: `{result['inputs']['v1474_dir']}`",
        f"- V1474 manifest: `{result['inputs']['v1474_manifest']}`",
        "",
        "## Handoff",
        "",
        f"- handoff pass: `{result['handoff']['pass']}`",
        f"- V1474 decision: `{result['handoff']['decision']}`",
        f"- rollback: `{result['handoff']['rollback']}`",
        f"- final timeout summary captured: `{result['handoff']['summary_has_final_timeout']}`",
        "",
        "## Extended Window",
        "",
        f"- effective marker seen: `{window['effective_marker_seen']}`",
        f"- full sample count: `{window['full_sample_count']}`",
        f"- full sample labels: `{window['full_sample_labels']}`",
        f"- full sample child elapsed ms: `{window['full_child_elapsed_ms']}`",
        f"- max full sample child elapsed ms: `{window['max_full_child_elapsed_ms']}`",
        f"- GPIO135 high lines: `{window['gpio135_high_lines']}`",
        f"- GPIO135 low lines: `{window['gpio135_low_lines']}`",
        f"- GPIO142 high lines: `{window['gpio142_high_lines']}`",
        f"- GPIO142 low lines: `{window['gpio142_low_lines']}`",
        f"- GPIO135 pinmux owner lines: `{window['gpio135_pinmux_owner_lines']}`",
        f"- GPIO142 pinmux owner lines: `{window['gpio142_pinmux_owner_lines']}`",
        f"- pcie1 GDSC 0mV lines: `{window['pcie1_gdsc_0mv_lines']}`",
        f"- pcie1 pipe clock zero lines: `{window['pcie1_pipe_clk_zero_lines']}`",
        f"- esoc0 PIL trace count: `{window['esoc_pil_count']}`",
        f"- GPIO135 set-high trace count: `{window['gpio135_set1_count']}`",
        "",
        "## Wi-Fi Progress",
        "",
        f"- provider trigger: `{progress['provider_trigger']}`",
        f"- modem trigger: `{progress['modem_trigger']}`",
        f"- RC1 progress: `{progress['rc1_progress']}`",
        f"- MHI progress: `{progress['mhi_progress']}`",
        f"- WLFW progress: `{progress['wlfw_progress']}`",
        f"- BDF progress: `{progress['bdf_progress']}`",
        f"- FW-ready progress: `{progress['fw_ready_progress']}`",
        f"- wlan0 present: `{progress['wlan0_present']}`",
        f"- downstream absent: `{progress['downstream_absent']}`",
        "",
        "## Interpretation",
        "",
        "The extended sampler closes the short-window explanation. The provider",
        "hits the AP2MDM set-high tracepoint, but GPIO135 remains sampled low",
        "with mdm3 pinmux ownership present. GPIO142/MDM2AP, PCIe wake, pcie1",
        "GDSC/pipe clock, RC1, MHI, WLFW, BDF, FW-ready, and `wlan0` remain absent.",
        "",
        "Do not proceed to Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or",
        "external ping from this state. Any next live mutation needs a separate",
        "lower-intervention design review with rollback boundaries.",
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
    parser.add_argument("--v1474-dir", type=Path, default=DEFAULT_V1474_DIR)
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
        args.report_path.write_text(render_report(result), encoding="utf-8")
    print(json.dumps({"decision": result["decision"], "pass": result["pass"], "next": result["next_gate"]}, indent=2))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

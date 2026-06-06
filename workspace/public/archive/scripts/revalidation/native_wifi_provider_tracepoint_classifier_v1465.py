#!/usr/bin/env python3
"""V1465 host-only classifier for V1464 provider GPIO tracepoint evidence."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from a90harness.evidence import EvidenceStore, write_private_text


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
DEFAULT_INPUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1464-wifi-test-boot-exact-provider-tracepoint-handoff"
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1465-provider-tracepoint-classifier"
DEFAULT_REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1465_PROVIDER_TRACEPOINT_CLASSIFIER_2026-06-01.md"
)

TRACE_RE = re.compile(r"gpio_(?P<kind>value|direction): (?P<num>\d+) (?P<op>.*)$")
WCHAN_RE = re.compile(
    r"^sample=(?P<label>\S+) source=provider_thread_wchan "
    r"path=(?P<path>\S+) value=(?P<value>.*)$"
)
TRACE_SAMPLE_RE = re.compile(
    r"^provider_tracepoint_sample label=(?P<label>\S+) "
    r"elapsed_ms=(?P<elapsed>-?\d+) "
    r"detect_elapsed_ms=(?P<detect>-?\d+) "
    r"trace_elapsed_ms=(?P<trace>-?\d+)"
)
GPIO_RE = re.compile(
    r"^sample=(?P<label>\S+) source=(?:micro_)?debug_gpio needle=(?P<needle>gpio\d+) "
    r"match=\s*(?P<match>.*)$"
)
CONTEXT_GPIO_RE = re.compile(
    r"^sample=(?P<label>\S+) source=debug_gpio match_\d+=\s*(?P<match>gpio(?P<num>\d+)\s*:.*)$"
)
INTERRUPT_RE = re.compile(
    r"^sample=(?P<label>\S+) source=(?:micro_)?interrupts match_\d+=(?P<line>.*)$"
)
REGULATOR_RE = re.compile(
    r"^sample=(?P<label>\S+) source=regulator_summary match_\d+=(?P<line>.*)$"
)
CLK_RE = re.compile(r"^sample=(?P<label>\S+) source=clk_summary match_\d+=(?P<line>.*)$")

EXPECTED_LABELS = [
    "provider_micro_after_trigger_0ms",
    "provider_micro_after_trigger_1ms",
    "provider_micro_after_trigger_2ms",
    "provider_micro_after_trigger_5ms",
    "provider_micro_after_trigger_10ms",
    "provider_micro_after_trigger_20ms",
    "provider_micro_after_trigger_50ms",
    "provider_micro_after_trigger_100ms",
    "provider_micro_after_trigger_150ms",
    "provider_micro_after_trigger_250ms",
    "provider_micro_after_trigger_300ms",
    "provider_micro_after_trigger_500ms",
    "provider_micro_after_trigger_1000ms",
]


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def parse_window(text: str) -> dict[str, Any]:
    trace_samples: dict[str, dict[str, Any]] = {}
    trace_events: dict[str, list[dict[str, str]]] = {}
    wchan_by_label: dict[str, str] = {}
    gpio: dict[str, dict[str, str]] = {}
    interrupts: dict[str, list[str]] = {}
    regulators: dict[str, list[str]] = {}
    clocks: dict[str, list[str]] = {}

    for raw_line in text.splitlines():
        line = raw_line.strip()
        sample_match = TRACE_SAMPLE_RE.match(line)
        if sample_match:
            trace_samples[sample_match.group("label")] = {
                "label": sample_match.group("label"),
                "elapsed_ms": int(sample_match.group("elapsed")),
                "detect_elapsed_ms": int(sample_match.group("detect")),
                "trace_elapsed_ms": int(sample_match.group("trace")),
            }
            continue
        if "source=provider_gpio_trace" in line and "match_" in line:
            label_match = re.match(r"^sample=(?P<label>\S+)", line)
            trace_match = TRACE_RE.search(line)
            if label_match and trace_match:
                label = label_match.group("label")
                trace_events.setdefault(label, []).append({
                    "kind": trace_match.group("kind"),
                    "num": trace_match.group("num"),
                    "op": trace_match.group("op"),
                    "line": line,
                })
            continue
        wchan_match = WCHAN_RE.match(line)
        if wchan_match:
            wchan_by_label[wchan_match.group("label")] = wchan_match.group("value")
            continue
        gpio_match = GPIO_RE.match(line)
        if gpio_match:
            gpio.setdefault(gpio_match.group("label"), {})[gpio_match.group("needle")] = gpio_match.group("match")
            continue
        context_gpio_match = CONTEXT_GPIO_RE.match(line)
        if context_gpio_match:
            gpio.setdefault(context_gpio_match.group("label"), {})[
                f"gpio{context_gpio_match.group('num')}"
            ] = context_gpio_match.group("match")
            continue
        interrupt_match = INTERRUPT_RE.match(line)
        if interrupt_match:
            interrupts.setdefault(interrupt_match.group("label"), []).append(interrupt_match.group("line"))
            continue
        regulator_match = REGULATOR_RE.match(line)
        if regulator_match:
            regulators.setdefault(regulator_match.group("label"), []).append(regulator_match.group("line"))
            continue
        clk_match = CLK_RE.match(line)
        if clk_match:
            clocks.setdefault(clk_match.group("label"), []).append(clk_match.group("line"))

    all_events = [event for events in trace_events.values() for event in events]
    events_by_num: dict[str, list[dict[str, str]]] = {}
    for event in all_events:
        events_by_num.setdefault(event["num"], []).append(event)

    labels_with_events = sorted(trace_events)
    all_labels = sorted(set(list(gpio) + EXPECTED_LABELS + ["post_provider_micro_1200ms"]))
    gpio135_values = [gpio.get(label, {}).get("gpio135", "") for label in all_labels if label in gpio]
    gpio142_values = [gpio.get(label, {}).get("gpio142", "") for label in all_labels if label in gpio]
    mdm_status_lines = [
        line for values in interrupts.values() for line in values
        if "msmgpio-dc 142" in line and "mdm status" in line
    ]
    pcie_wake_lines = [
        line for values in interrupts.values() for line in values
        if "msmgpio-dc 104" in line and "msm_pcie_wake" in line
    ]
    pcie1_regulator_lines = [
        line for values in regulators.values() for line in values if "pcie_1_gdsc" in line
    ]
    pcie1_clock_lines = [
        line for values in clocks.values() for line in values if "gcc_pcie_1" in line
    ]

    gpio1270_ops = [event["op"] for event in events_by_num.get("1270", []) if event["kind"] == "value"]
    gpio135_ops = [event["op"] for event in events_by_num.get("135", [])]
    gpio142_ops = [event["op"] for event in events_by_num.get("142", [])]
    gpio141_ops = [event["op"] for event in events_by_num.get("141", [])]

    return {
        "trace_sample_count": len(trace_samples),
        "trace_labels": sorted(trace_samples),
        "expected_trace_labels_present": all(label in trace_samples for label in EXPECTED_LABELS),
        "labels_with_events": labels_with_events,
        "event_counts_by_gpio": {num: len(events) for num, events in sorted(events_by_num.items())},
        "gpio1270_ops": gpio1270_ops,
        "gpio135_ops": gpio135_ops,
        "gpio142_ops": gpio142_ops,
        "gpio141_ops": gpio141_ops,
        "gpio1270_pon_low_high_seen": any(op == "set 0" for op in gpio1270_ops)
        and any(op == "set 1" for op in gpio1270_ops),
        "gpio135_trace_absent": len(gpio135_ops) == 0,
        "gpio142_trace_absent": len(gpio142_ops) == 0,
        "gpio141_errfatal_low_seen": any(op == "set 0" for op in gpio141_ops),
        "wchan_by_label": {label: wchan_by_label.get(label, "") for label in EXPECTED_LABELS},
        "wchan_soft_reset_seen": any(value == "sdx50m_toggle_soft_reset" for value in wchan_by_label.values()),
        "wchan_msleep_seen": any(value == "msleep" for value in wchan_by_label.values()),
        "wchan_powerup_seen": any(value == "mdm_subsys_powerup" for value in wchan_by_label.values()),
        "gpio135_all_low": bool(gpio135_values) and all("out 0" in value for value in gpio135_values),
        "gpio142_all_low": bool(gpio142_values) and all("in 0" in value for value in gpio142_values),
        "mdm_status_irq_all_zero": bool(mdm_status_lines) and all(": 0 0 0 0 0 0 0 0" in line for line in mdm_status_lines),
        "pcie_wake_irq_all_zero": bool(pcie_wake_lines) and all(": 0 0 0 0 0 0 0 0" in line for line in pcie_wake_lines),
        "pcie1_gdsc_all_0mv": bool(pcie1_regulator_lines) and all(" 0mV " in line for line in pcie1_regulator_lines),
        "pcie1_clocks_all_zero_enable": bool(pcie1_clock_lines) and all(" 0 0 0 " in line for line in pcie1_clock_lines),
    }


def classify(input_dir: Path) -> dict[str, Any]:
    handoff = json.loads(read_text(input_dir / "manifest.json") or "{}")
    window_text = read_text(input_dir / "test-rc1-window-result.stdout.txt")
    log_text = read_text(input_dir / "test-v1393-log.stdout.txt")
    dmesg = read_text(input_dir / "test-v1393-dmesg.stdout.txt")
    wlan0 = read_text(input_dir / "test-wlan0.stdout.txt")
    version = read_text(input_dir / "test-version.stdout.txt")
    rollback = read_text(input_dir / "rollback-from-native.stdout.txt")
    parsed = parse_window(window_text)

    tracepoint_header = "tracepoint_sampler=1" in window_text
    tracepoint_arm_ok = "provider tracepoint arm trace_off_rc=0 clear_rc=0 gpio_value_rc=0 gpio_direction_rc=0 trace_on_rc=0" in log_text
    tracepoint_disarm_seen = "provider tracepoint disarm" in log_text
    rc1_progress = any(marker in dmesg for marker in ("PCIe RC1 PHY is ready", "LTSSM_STATE", "PCIe RC1 Current", "PCIe RC1 link"))
    mhi_progress = any(marker in dmesg for marker in ("mhi_arch", "mhi_pci", "mhi_0305", "MHI control"))
    wlfw_progress = any(marker in dmesg for marker in ("wlfw", "WLFW", "icnss_qmi"))
    bdf_progress = any(marker in dmesg for marker in ("BDF", "bdwlan", "regdb"))
    fw_ready_progress = any(marker in dmesg for marker in ("FW ready", "fw_ready", "FW_READY"))
    wlan0_present = "wlan0=present" in wlan0
    downstream_progress = any((rc1_progress, mhi_progress, wlfw_progress, bdf_progress, fw_ready_progress, wlan0_present))
    rollback_ok = bool(handoff.get("rollback", {}).get("ok")) and "A90 Linux init 0.9.68 (v724)" in rollback
    test_version_ok = "A90 Linux init 0.9.86 (v1462-wifitest)" in version

    passed = (
        bool(handoff.get("pass"))
        and rollback_ok
        and test_version_ok
        and tracepoint_header
        and tracepoint_arm_ok
        and parsed["expected_trace_labels_present"]
        and parsed["gpio1270_pon_low_high_seen"]
        and parsed["gpio141_errfatal_low_seen"]
        and parsed["gpio135_trace_absent"]
        and parsed["gpio142_trace_absent"]
        and parsed["wchan_soft_reset_seen"]
        and parsed["wchan_msleep_seen"]
        and parsed["wchan_powerup_seen"]
        and parsed["gpio135_all_low"]
        and parsed["gpio142_all_low"]
        and parsed["mdm_status_irq_all_zero"]
        and parsed["pcie_wake_irq_all_zero"]
        and parsed["pcie1_gdsc_all_0mv"]
        and parsed["pcie1_clocks_all_zero_enable"]
        and not downstream_progress
    )
    if passed:
        decision = "v1465-pon-toggles-ap2mdm-absent-no-downstream"
        reason = (
            "V1464 tracepoints prove the provider toggles GPIO1270 PON low/high and GPIO141 low, "
            "but never emits GPIO135/AP2MDM or GPIO142/MDM2AP trace events; endpoint state and pcie1 remain inactive"
        )
        next_gate = "V1466 host-only provider AP2MDM branch/source classifier before any new live mutation"
    else:
        decision = "v1465-provider-tracepoint-needs-review"
        reason = "V1464 tracepoint evidence did not satisfy the classifier contract"
        next_gate = "review V1464 evidence before another test boot"

    return {
        "cycle": "V1465",
        "decision": decision,
        "pass": passed,
        "reason": reason,
        "input_dir": rel(input_dir),
        "handoff_decision": handoff.get("decision", ""),
        "handoff_pass": bool(handoff.get("pass")),
        "rollback_ok": rollback_ok,
        "test_version_ok": test_version_ok,
        "tracepoint_header": tracepoint_header,
        "tracepoint_arm_ok": tracepoint_arm_ok,
        "tracepoint_disarm_seen": tracepoint_disarm_seen,
        "window": parsed,
        "progress": {
            "rc1_progress": rc1_progress,
            "mhi_progress": mhi_progress,
            "wlfw_progress": wlfw_progress,
            "bdf_progress": bdf_progress,
            "fw_ready_progress": fw_ready_progress,
            "wlan0_present": wlan0_present,
            "connect_ready": wlan0_present,
            "downstream_progress": downstream_progress,
        },
        "guardrails": {
            "host_only": True,
            "device_command_executed": False,
            "flash_executed": False,
            "wifi_hal_scan_connect_executed": False,
            "credential_use_executed": False,
            "dhcp_route_external_ping_executed": False,
        },
        "next_gate": next_gate,
    }


def render_report(result: dict[str, Any]) -> str:
    window = result["window"]
    progress = result["progress"]
    return "\n".join([
        "# Native Init V1465 Provider Tracepoint Classifier",
        "",
        "## Summary",
        "",
        "- Cycle: `V1465`",
        "- Type: host-only classifier over V1464 exact-provider GPIO tracepoint evidence",
        f"- Decision: `{result['decision']}`",
        f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
        f"- Reason: {result['reason']}",
        f"- Evidence: `{result['input_dir']}`",
        f"- Handoff decision: `{result['handoff_decision']}`",
        f"- Rollback v724 verified: `{result['rollback_ok']}`",
        "",
        "## Tracepoint Contract",
        "",
        f"- tracepoint header: `{result['tracepoint_header']}`",
        f"- tracepoint arm all rc=0: `{result['tracepoint_arm_ok']}`",
        f"- tracepoint disarm observed: `{result['tracepoint_disarm_seen']}`",
        f"- trace samples: `{window['trace_sample_count']}`",
        f"- expected trace labels present: `{window['expected_trace_labels_present']}`",
        f"- event counts by GPIO: `{window['event_counts_by_gpio']}`",
        "",
        "## GPIO Events",
        "",
        f"- GPIO1270/PON low-high seen: `{window['gpio1270_pon_low_high_seen']}`",
        f"- GPIO1270 ops: `{window['gpio1270_ops']}`",
        f"- GPIO141 errfatal low seen: `{window['gpio141_errfatal_low_seen']}`",
        f"- GPIO135/AP2MDM trace absent: `{window['gpio135_trace_absent']}`",
        f"- GPIO142/MDM2AP trace absent: `{window['gpio142_trace_absent']}`",
        f"- endpoint GPIO135 all low: `{window['gpio135_all_low']}`",
        f"- endpoint GPIO142 all low: `{window['gpio142_all_low']}`",
        "",
        "## Provider Thread",
        "",
        "| sample | wchan |",
        "| --- | --- |",
        *[f"| `{label}` | `{window['wchan_by_label'].get(label, '')}` |" for label in EXPECTED_LABELS],
        "",
        "## Endpoint State",
        "",
        f"- MDM status IRQ all zero: `{window['mdm_status_irq_all_zero']}`",
        f"- PCIe wake IRQ all zero: `{window['pcie_wake_irq_all_zero']}`",
        f"- pcie1 GDSC all 0mV: `{window['pcie1_gdsc_all_0mv']}`",
        f"- pcie1 clocks all zero-enable: `{window['pcie1_clocks_all_zero_enable']}`",
        "",
        "## Progress Classification",
        "",
        f"- `rc1_progress`: `{progress['rc1_progress']}`",
        f"- `mhi_progress`: `{progress['mhi_progress']}`",
        f"- `wlfw_progress`: `{progress['wlfw_progress']}`",
        f"- `bdf_progress`: `{progress['bdf_progress']}`",
        f"- `fw_ready_progress`: `{progress['fw_ready_progress']}`",
        f"- `wlan0_present`: `{progress['wlan0_present']}`",
        f"- `connect_ready`: `{progress['connect_ready']}`",
        "",
        "## Interpretation",
        "",
        "V1464 closes the PON-observability gap for the current exact-provider boot.",
        "The provider reaches the PMIC/PON side and toggles GPIO1270 low then high,",
        "but no GPIO135/AP2MDM assertion is observed by tracepoint or endpoint",
        "snapshot, and GPIO142/MDM2AP never responds. pcie1 remains off and no",
        "RC1/MHI/WLFW/BDF/FW-ready/`wlan0` progress appears.",
        "",
        "This shifts the next question to the provider branch between PON completion",
        "and AP2MDM assertion, not Wi-Fi HAL/connect readiness.",
        "",
        "## Safety Scope",
        "",
        "This classifier was host-only. It did not issue device commands, flash,",
        "reboot, start Wi-Fi HAL, scan/connect, use credentials, configure",
        "DHCP/routes, or perform external ping.",
        "",
        "## Next",
        "",
        result["next_gate"],
        "",
    ])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_DIR)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--write-report", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    store = EvidenceStore(args.out_dir)
    result = classify(args.input_dir)
    report = render_report(result)
    store.write_json("manifest.json", result)
    store.write_text("summary.md", report)
    if args.write_report:
        write_private_text(args.report_path, report)
    print(json.dumps({
        "decision": result["decision"],
        "pass": result["pass"],
        "out_dir": rel(args.out_dir),
        "next_gate": result["next_gate"],
    }, indent=2, sort_keys=True))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

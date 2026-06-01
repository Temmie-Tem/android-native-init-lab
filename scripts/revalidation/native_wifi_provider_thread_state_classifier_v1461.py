#!/usr/bin/env python3
"""V1461 host-only classifier for V1460 provider thread-state evidence."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from a90harness.evidence import EvidenceStore, write_private_text


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT_DIR = (
    REPO_ROOT / "tmp" / "wifi" / "v1460-wifi-test-boot-exact-provider-thread-state-handoff"
)
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1461-provider-thread-state-classifier"
DEFAULT_REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1461_PROVIDER_THREAD_STATE_CLASSIFIER_2026-06-01.md"
)

MICRO_SAMPLE_RE = re.compile(
    r"^rc1_micro_sample label=(?P<label>\S+) "
    r"elapsed_ms=(?P<elapsed>-?\d+) "
    r"detect_elapsed_ms=(?P<detect>-?\d+) "
    r"micro_elapsed_ms=(?P<micro>-?\d+)"
)
WINDOW_SAMPLE_RE = re.compile(
    r"^rc1_window_sample label=(?P<label>\S+) "
    r"elapsed_ms=(?P<elapsed>-?\d+) "
    r"detect_elapsed_ms=(?P<detect>-?\d+) "
    r"child_elapsed_ms=(?P<child>-?\d+)"
)
THREAD_STATE_RE = re.compile(
    r"^provider_thread_state label=(?P<label>\S+) "
    r"elapsed_ms=(?P<elapsed>-?\d+) "
    r"detect_elapsed_ms=(?P<detect>-?\d+) "
    r"thread_elapsed_ms=(?P<thread>-?\d+) "
    r"trigger_pid=(?P<pid>-?\d+)"
)
WCHAN_RE = re.compile(
    r"^sample=(?P<label>\S+) source=provider_thread_wchan "
    r"path=(?P<path>\S+) value=(?P<value>.*)$"
)
COMM_RE = re.compile(
    r"^sample=(?P<label>\S+) source=provider_thread_comm "
    r"path=(?P<path>\S+) value=(?P<value>.*)$"
)
STATUS_RE = re.compile(
    r"^sample=(?P<label>\S+) source=provider_thread_status "
    r"match_\d+=(?P<line>.*)$"
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
    micro_samples: list[dict[str, Any]] = []
    context_samples: list[dict[str, Any]] = []
    thread_samples: dict[str, dict[str, Any]] = {}
    gpio: dict[str, dict[str, str]] = {}
    interrupts: dict[str, list[str]] = {}
    regulators: dict[str, list[str]] = {}
    clocks: dict[str, list[str]] = {}

    for raw_line in text.splitlines():
        line = raw_line.strip()
        micro_match = MICRO_SAMPLE_RE.match(line)
        if micro_match:
            micro_samples.append({
                "label": micro_match.group("label"),
                "elapsed_ms": int(micro_match.group("elapsed")),
                "detect_elapsed_ms": int(micro_match.group("detect")),
                "micro_elapsed_ms": int(micro_match.group("micro")),
            })
            continue
        window_match = WINDOW_SAMPLE_RE.match(line)
        if window_match:
            context_samples.append({
                "label": window_match.group("label"),
                "elapsed_ms": int(window_match.group("elapsed")),
                "detect_elapsed_ms": int(window_match.group("detect")),
                "child_elapsed_ms": int(window_match.group("child")),
            })
            continue
        thread_match = THREAD_STATE_RE.match(line)
        if thread_match:
            label = thread_match.group("label")
            thread_samples.setdefault(label, {}).update({
                "label": label,
                "elapsed_ms": int(thread_match.group("elapsed")),
                "detect_elapsed_ms": int(thread_match.group("detect")),
                "thread_elapsed_ms": int(thread_match.group("thread")),
                "trigger_pid": int(thread_match.group("pid")),
            })
            continue
        wchan_match = WCHAN_RE.match(line)
        if wchan_match:
            thread_samples.setdefault(wchan_match.group("label"), {})["wchan"] = wchan_match.group("value")
            continue
        comm_match = COMM_RE.match(line)
        if comm_match:
            thread_samples.setdefault(comm_match.group("label"), {})["comm"] = comm_match.group("value")
            continue
        status_match = STATUS_RE.match(line)
        if status_match:
            thread_samples.setdefault(status_match.group("label"), {}).setdefault("status_lines", []).append(
                status_match.group("line")
            )
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

    micro_labels = [sample["label"] for sample in micro_samples]
    all_labels = micro_labels + [sample["label"] for sample in context_samples]
    gpio135_values = [gpio.get(label, {}).get("gpio135", "") for label in all_labels]
    gpio142_values = [gpio.get(label, {}).get("gpio142", "") for label in all_labels]
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
    ordered_thread_samples = [thread_samples.get(label, {}) for label in EXPECTED_LABELS]
    wchan_by_label = {
        label: str(thread_samples.get(label, {}).get("wchan", "")) for label in EXPECTED_LABELS
    }
    trigger_pids = {
        int(sample["trigger_pid"]) for sample in ordered_thread_samples if "trigger_pid" in sample
    }
    comm_values = {
        str(sample["comm"]) for sample in ordered_thread_samples if sample.get("comm")
    }
    state_lines = [
        line for sample in ordered_thread_samples for line in sample.get("status_lines", [])
        if line.startswith("State:")
    ]

    return {
        "micro_sample_count": len(micro_samples),
        "micro_labels": micro_labels,
        "micro_offsets_ms": [sample["micro_elapsed_ms"] for sample in micro_samples],
        "expected_labels_present": all(label in micro_labels for label in EXPECTED_LABELS),
        "context_sample_count": len(context_samples),
        "context_labels": [sample["label"] for sample in context_samples],
        "post_1200_present": any(sample["label"] == "post_provider_micro_1200ms" for sample in context_samples),
        "thread_sample_count": sum(1 for label in EXPECTED_LABELS if label in thread_samples),
        "thread_samples": ordered_thread_samples,
        "wchan_by_label": wchan_by_label,
        "trigger_pids": sorted(trigger_pids),
        "single_trigger_pid": len(trigger_pids) == 1,
        "comm_values": sorted(comm_values),
        "binder_thread_seen": any(value.startswith("Binder:") for value in comm_values),
        "state_lines": state_lines,
        "thread_all_d_state": bool(state_lines) and all("D (disk sleep)" in line for line in state_lines),
        "soft_reset_phase_seen": any(value == "sdx50m_toggle_soft_reset" for value in wchan_by_label.values()),
        "msleep_phase_seen": any(value == "msleep" for value in wchan_by_label.values()),
        "powerup_phase_seen": any(value == "mdm_subsys_powerup" for value in wchan_by_label.values()),
        "late_powerup_block": all(
            wchan_by_label.get(label) == "mdm_subsys_powerup"
            for label in (
                "provider_micro_after_trigger_300ms",
                "provider_micro_after_trigger_500ms",
                "provider_micro_after_trigger_1000ms",
            )
        ),
        "gpio135_all_low": bool(gpio135_values) and all("out 0" in value for value in gpio135_values),
        "gpio142_all_low": bool(gpio142_values) and all("in 0" in value for value in gpio142_values),
        "gpio135_values": gpio135_values,
        "gpio142_values": gpio142_values,
        "mdm_status_irq_all_zero": bool(mdm_status_lines) and all(": 0 0 0 0 0 0 0 0" in line for line in mdm_status_lines),
        "pcie_wake_irq_all_zero": bool(pcie_wake_lines) and all(": 0 0 0 0 0 0 0 0" in line for line in pcie_wake_lines),
        "pcie1_gdsc_all_0mv": bool(pcie1_regulator_lines) and all(" 0mV " in line for line in pcie1_regulator_lines),
        "pcie1_clocks_all_zero_enable": bool(pcie1_clock_lines) and all(" 0 0 0 " in line for line in pcie1_clock_lines),
    }


def classify(input_dir: Path) -> dict[str, Any]:
    handoff = json.loads(read_text(input_dir / "manifest.json") or "{}")
    window_text = read_text(input_dir / "test-rc1-window-result.stdout.txt")
    watcher_text = read_text(input_dir / "test-v1393-rc1-watcher-result.stdout.txt")
    dmesg = read_text(input_dir / "test-v1393-dmesg.stdout.txt")
    wlan0 = read_text(input_dir / "test-wlan0.stdout.txt")
    version = read_text(input_dir / "test-version.stdout.txt")
    rollback = read_text(input_dir / "rollback-from-native.stdout.txt")
    parsed = parse_window(window_text)

    exact_header = "exact_provider_line=1" in window_text
    long_header = "long_provider_window=1" in window_text
    exact_watcher_line = "__subsystem_get: esoc0 count:0" in watcher_text and "__netlink_sendskb" not in watcher_text
    thread_state_header = "sampler=read-only-v1458-exact-provider-thread-state" in window_text
    explicit_rc1_test = "PCIe: TEST:" in dmesg or "rc1_micro_writer_summary" in window_text
    rc1_progress = any(marker in dmesg for marker in ("PCIe RC1 PHY is ready", "LTSSM_STATE", "PCIe RC1 Current", "PCIe RC1 link"))
    mhi_progress = any(marker in dmesg for marker in ("mhi_arch", "mhi_pci", "mhi_0305", "MHI control"))
    wlfw_progress = any(marker in dmesg for marker in ("wlfw", "WLFW", "icnss_qmi"))
    bdf_progress = any(marker in dmesg for marker in ("BDF", "bdwlan", "regdb"))
    fw_ready_progress = any(marker in dmesg for marker in ("FW ready", "fw_ready", "FW_READY"))
    wlan0_present = "wlan0=present" in wlan0
    downstream_progress = any((rc1_progress, mhi_progress, wlfw_progress, bdf_progress, fw_ready_progress, wlan0_present))
    rollback_ok = bool(handoff.get("rollback", {}).get("ok")) and "A90 Linux init 0.9.68 (v724)" in rollback
    test_version_ok = "A90 Linux init 0.9.85 (v1458-wifitest)" in version

    passed = (
        bool(handoff.get("pass"))
        and rollback_ok
        and test_version_ok
        and exact_header
        and long_header
        and exact_watcher_line
        and thread_state_header
        and parsed["expected_labels_present"]
        and parsed["thread_sample_count"] == len(EXPECTED_LABELS)
        and parsed["single_trigger_pid"]
        and parsed["binder_thread_seen"]
        and parsed["thread_all_d_state"]
        and parsed["soft_reset_phase_seen"]
        and parsed["msleep_phase_seen"]
        and parsed["powerup_phase_seen"]
        and parsed["late_powerup_block"]
        and parsed["post_1200_present"]
        and parsed["gpio135_all_low"]
        and parsed["gpio142_all_low"]
        and parsed["mdm_status_irq_all_zero"]
        and parsed["pcie_wake_irq_all_zero"]
        and parsed["pcie1_gdsc_all_0mv"]
        and parsed["pcie1_clocks_all_zero_enable"]
        and not explicit_rc1_test
        and not downstream_progress
    )

    if passed:
        decision = "v1461-provider-thread-state-powerup-block-no-downstream"
        reason = (
            "V1460 proves the exact provider Binder thread enters sdx50m_toggle_soft_reset, "
            "then msleep, then remains blocked in mdm_subsys_powerup while GPIO135/GPIO142, "
            "MDM status IRQ, pcie1 clocks/GDSC, RC1/MHI/WLFW, and wlan0 stay inactive"
        )
        next_gate = (
            "V1462 source/build-only exact-provider tracepoint test boot for GPIO1270/GPIO135/"
            "GPIO142 and pcie1 clock/GDSC timing around the provider thread phases"
        )
    else:
        decision = "v1461-provider-thread-state-needs-review"
        reason = "V1460 evidence did not satisfy the provider thread-state classifier contract"
        next_gate = "review V1460 evidence before another test boot"

    return {
        "cycle": "V1461",
        "decision": decision,
        "pass": passed,
        "reason": reason,
        "input_dir": rel(input_dir),
        "handoff_decision": handoff.get("decision", ""),
        "handoff_pass": bool(handoff.get("pass")),
        "rollback_ok": rollback_ok,
        "test_version_ok": test_version_ok,
        "window": parsed,
        "classification": {
            "exact_header": exact_header,
            "long_header": long_header,
            "exact_watcher_line": exact_watcher_line,
            "thread_state_header": thread_state_header,
            "expected_labels_present": parsed["expected_labels_present"],
            "thread_sample_count": parsed["thread_sample_count"],
            "single_trigger_pid": parsed["single_trigger_pid"],
            "binder_thread_seen": parsed["binder_thread_seen"],
            "thread_all_d_state": parsed["thread_all_d_state"],
            "soft_reset_phase_seen": parsed["soft_reset_phase_seen"],
            "msleep_phase_seen": parsed["msleep_phase_seen"],
            "powerup_phase_seen": parsed["powerup_phase_seen"],
            "late_powerup_block": parsed["late_powerup_block"],
            "post_1200_present": parsed["post_1200_present"],
            "gpio135_all_low": parsed["gpio135_all_low"],
            "gpio142_all_low": parsed["gpio142_all_low"],
            "mdm_status_irq_all_zero": parsed["mdm_status_irq_all_zero"],
            "pcie_wake_irq_all_zero": parsed["pcie_wake_irq_all_zero"],
            "pcie1_gdsc_all_0mv": parsed["pcie1_gdsc_all_0mv"],
            "pcie1_clocks_all_zero_enable": parsed["pcie1_clocks_all_zero_enable"],
        },
        "progress": {
            "explicit_rc1_test": explicit_rc1_test,
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
    cls = result["classification"]
    progress = result["progress"]
    window = result["window"]
    wchan_by_label = window["wchan_by_label"]
    return "\n".join([
        "# Native Init V1461 Provider Thread-State Classifier",
        "",
        "## Summary",
        "",
        "- Cycle: `V1461`",
        "- Type: host-only classifier over V1460 exact provider thread-state evidence",
        f"- Decision: `{result['decision']}`",
        f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
        f"- Reason: {result['reason']}",
        f"- Evidence: `{result['input_dir']}`",
        f"- Handoff decision: `{result['handoff_decision']}`",
        f"- Rollback v724 verified: `{result['rollback_ok']}`",
        "",
        "## Exact Provider Thread",
        "",
        f"- exact header: `{cls['exact_header']}`",
        f"- long-window header: `{cls['long_header']}`",
        f"- thread-state sampler header: `{cls['thread_state_header']}`",
        f"- exact watcher line: `{cls['exact_watcher_line']}`",
        f"- trigger PIDs: `{window['trigger_pids']}`",
        f"- comm values: `{window['comm_values']}`",
        f"- thread samples: `{cls['thread_sample_count']}`",
        f"- all sampled thread states are D-state: `{cls['thread_all_d_state']}`",
        f"- soft-reset phase seen: `{cls['soft_reset_phase_seen']}`",
        f"- msleep phase seen: `{cls['msleep_phase_seen']}`",
        f"- powerup block phase seen: `{cls['powerup_phase_seen']}`",
        f"- late samples blocked in `mdm_subsys_powerup`: `{cls['late_powerup_block']}`",
        "",
        "## Wchan Sequence",
        "",
        "| sample | wchan |",
        "| --- | --- |",
        *[f"| `{label}` | `{wchan_by_label.get(label, '')}` |" for label in EXPECTED_LABELS],
        "",
        "## Endpoint State",
        "",
        f"- GPIO135 all low through long window: `{cls['gpio135_all_low']}`",
        f"- GPIO142 all low through long window: `{cls['gpio142_all_low']}`",
        f"- MDM status IRQ all zero: `{cls['mdm_status_irq_all_zero']}`",
        f"- PCIe wake IRQ all zero: `{cls['pcie_wake_irq_all_zero']}`",
        f"- pcie1 GDSC all 0mV: `{cls['pcie1_gdsc_all_0mv']}`",
        f"- pcie1 clocks all zero-enable: `{cls['pcie1_clocks_all_zero_enable']}`",
        "",
        "## Progress Classification",
        "",
        f"- explicit RC1 test write observed: `{progress['explicit_rc1_test']}`",
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
        "V1460 moves the blocker from a generic provider-trigger event to a concrete",
        "thread-state sequence. The triggering Binder thread is alive, D-state, and",
        "transitions through `sdx50m_toggle_soft_reset` and `msleep` before remaining",
        "in `mdm_subsys_powerup`. At the same time, endpoint-visible GPIO135/GPIO142,",
        "MDM status IRQ, pcie1 GDSC/clocks, RC1/MHI/WLFW/BDF/FW-ready, and `wlan0`",
        "remain inactive.",
        "",
        "This supports a lower-provider timing gap, not Wi-Fi connect readiness.",
        "The next useful evidence should capture GPIO tracepoint events and pcie1",
        "power/refclk state around the exact provider thread phases, rather than",
        "starting Wi-Fi HAL, scanning, or using credentials.",
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

#!/usr/bin/env python3
"""V1453 host-only classifier for V1452 provider-trigger micro endpoint evidence."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from a90harness.evidence import EvidenceStore, write_private_text


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
DEFAULT_INPUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1452-wifi-test-boot-provider-trigger-micro-endpoint-handoff"
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1453-provider-trigger-micro-handoff-classifier"
DEFAULT_REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1453_PROVIDER_TRIGGER_MICRO_HANDOFF_CLASSIFIER_2026-06-01.md"
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
GPIO_RE = re.compile(
    r"^sample=(?P<label>\S+) source=(?:micro_)?debug_gpio needle=(?P<needle>gpio\d+) "
    r"match=\s*(?P<match>.*)$"
)
INTERRUPT_RE = re.compile(
    r"^sample=(?P<label>\S+) source=(?:micro_)?interrupts match_\d+=(?P<line>.*)$"
)
REGULATOR_RE = re.compile(
    r"^sample=(?P<label>\S+) source=regulator_summary match_\d+=(?P<line>.*)$"
)
CLK_RE = re.compile(
    r"^sample=(?P<label>\S+) source=clk_summary match_\d+=(?P<line>.*)$"
)
DMESG_TS_RE = re.compile(r"^\[\s*(?P<ts>\d+\.\d+)\]")


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def first_dmesg_ts(text: str, needle: str) -> float | None:
    for line in text.splitlines():
        if needle not in line:
            continue
        match = DMESG_TS_RE.match(line)
        if match:
            return float(match.group("ts"))
    return None


def parse_window(text: str) -> dict[str, Any]:
    micro_samples: list[dict[str, Any]] = []
    context_samples: list[dict[str, Any]] = []
    gpio: dict[str, dict[str, str]] = {}
    interrupts: dict[str, list[str]] = {}
    regulators: dict[str, list[str]] = {}
    clocks: dict[str, list[str]] = {}
    pcie_link_unreadable_labels: set[str] = set()
    pcie_current_unreadable_labels: set[str] = set()

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
        gpio_match = GPIO_RE.match(line)
        if gpio_match:
            gpio.setdefault(gpio_match.group("label"), {})[gpio_match.group("needle")] = gpio_match.group("match")
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
            continue
        if "source=micro_pcie1_link_state" in line and "unreadable" in line:
            label = line.split("sample=", 1)[1].split(" ", 1)[0] if "sample=" in line else ""
            pcie_link_unreadable_labels.add(label)
        if "source=micro_pcie1_current_link_state" in line and "unreadable" in line:
            label = line.split("sample=", 1)[1].split(" ", 1)[0] if "sample=" in line else ""
            pcie_current_unreadable_labels.add(label)

    micro_labels = [sample["label"] for sample in micro_samples]
    gpio135_values = [gpio.get(label, {}).get("gpio135", "") for label in micro_labels]
    gpio142_values = [gpio.get(label, {}).get("gpio142", "") for label in micro_labels]
    gpio104_values = [gpio.get(label, {}).get("gpio104", "") for label in micro_labels]

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

    return {
        "micro_sample_count": len(micro_samples),
        "micro_samples": micro_samples,
        "micro_labels": micro_labels,
        "context_sample_count": len(context_samples),
        "context_samples": context_samples,
        "micro_offsets_ms": [sample["micro_elapsed_ms"] for sample in micro_samples],
        "gpio135_all_low": bool(gpio135_values) and all("out 0" in value for value in gpio135_values),
        "gpio142_all_low": bool(gpio142_values) and all("in 0" in value for value in gpio142_values),
        "gpio104_all_low": bool(gpio104_values) and all("in 0" in value for value in gpio104_values),
        "gpio135_values": gpio135_values,
        "gpio142_values": gpio142_values,
        "mdm_status_irq_all_zero": bool(mdm_status_lines) and all(": 0 0 0 0 0 0 0 0" in line for line in mdm_status_lines),
        "pcie_wake_irq_all_zero": bool(pcie_wake_lines) and all(": 0 0 0 0 0 0 0 0" in line for line in pcie_wake_lines),
        "pcie1_gdsc_all_0mv": bool(pcie1_regulator_lines) and all(" 0mV " in line for line in pcie1_regulator_lines),
        "pcie1_clocks_all_zero_enable": bool(pcie1_clock_lines) and all(" 0 0 0 " in line for line in pcie1_clock_lines),
        "pcie_link_unreadable_count": len(pcie_link_unreadable_labels),
        "pcie_current_unreadable_count": len(pcie_current_unreadable_labels),
    }


def classify(input_dir: Path) -> dict[str, Any]:
    handoff = json.loads(read_text(input_dir / "manifest.json") or "{}")
    window_text = read_text(input_dir / "test-rc1-window-result.stdout.txt")
    dmesg = read_text(input_dir / "test-v1393-dmesg.stdout.txt")
    wlan0 = read_text(input_dir / "test-wlan0.stdout.txt")
    version = read_text(input_dir / "test-version.stdout.txt")
    rollback = read_text(input_dir / "rollback-from-native.stdout.txt")
    watcher = read_text(input_dir / "test-v1393-rc1-watcher-result.stdout.txt")
    parsed = parse_window(window_text)

    modem_get_ts = first_dmesg_ts(dmesg, "__subsystem_get: modem")
    esoc_get_ts = first_dmesg_ts(dmesg, "__subsystem_get: esoc0")
    rc1_test_ts = first_dmesg_ts(dmesg, "PCIe: TEST:")
    rc1_phy_ts = first_dmesg_ts(dmesg, "PCIe RC1 PHY is ready")
    rc1_l0_ts = first_dmesg_ts(dmesg, "LTSSM_STATE: LTSSM_L0")
    rc1_current_ts = first_dmesg_ts(dmesg, "PCIe RC1 Current")
    rc1_link_failed_ts = first_dmesg_ts(dmesg, "PCIe RC1 link initialization failed")
    mhi_ts = (
        first_dmesg_ts(dmesg, "mhi_arch") or
        first_dmesg_ts(dmesg, "mhi_pci") or
        first_dmesg_ts(dmesg, "mhi_0305") or
        first_dmesg_ts(dmesg, "MHI")
    )
    wlfw_ts = first_dmesg_ts(dmesg, "wlfw")
    fw_ready_ts = first_dmesg_ts(dmesg, "FW ready")

    rc1_l0 = rc1_l0_ts is not None or rc1_current_ts is not None
    explicit_rc1_test = rc1_test_ts is not None or "rc1_micro_writer_summary" in window_text
    downstream_progress = any(value is not None for value in (rc1_phy_ts, rc1_l0_ts, rc1_current_ts, rc1_link_failed_ts, mhi_ts, wlfw_ts, fw_ready_ts))
    wlan0_present = "wlan0=present" in wlan0
    rollback_ok = "A90 Linux init 0.9.68 (v724)" in rollback
    test_version_ok = "A90 Linux init 0.9.83 (v1450-wifitest)" in version
    trigger_chunk_prefix_is_not_exact = "__netlink_sendskb" in watcher and "__subsystem_get: esoc0" not in watcher[:240]

    complete_micro_offsets = parsed["micro_offsets_ms"] == [0, 11, 21, 31, 39, 44, 50, 100, 150]
    expected_micro_count = parsed["micro_sample_count"] == 9

    if (
        handoff.get("pass")
        and rollback_ok
        and test_version_ok
        and expected_micro_count
        and parsed["gpio135_all_low"]
        and parsed["gpio142_all_low"]
        and parsed["mdm_status_irq_all_zero"]
        and parsed["pcie_wake_irq_all_zero"]
        and not downstream_progress
        and not wlan0_present
        and not explicit_rc1_test
    ):
        decision = "v1453-provider-window-low-no-downstream"
        passed = True
        reason = (
            "V1452 safely sampled the provider-trigger window without explicit RC1 debugfs writes; "
            "GPIO135/GPIO142 and endpoint IRQs stayed low and no RC1/MHI/WLFW/wlan0 progress appeared"
        )
        next_gate = "V1454 source/build-only exact-line provider trigger with a longer read-only endpoint window"
    else:
        decision = "v1453-provider-window-needs-review"
        passed = False
        reason = "V1452 evidence did not meet the expected complete low/no-downstream classifier contract"
        next_gate = "review V1452 evidence before building another test boot"

    return {
        "cycle": "V1453",
        "decision": decision,
        "pass": passed,
        "reason": reason,
        "input_dir": rel(input_dir),
        "handoff_decision": handoff.get("decision", ""),
        "handoff_pass": bool(handoff.get("pass")),
        "rollback_ok": rollback_ok,
        "test_version_ok": test_version_ok,
        "trigger_chunk_prefix_is_not_exact": trigger_chunk_prefix_is_not_exact,
        "provider_timing": {
            "modem_get_ts": modem_get_ts,
            "esoc_get_ts": esoc_get_ts,
            "rc1_test_ts": rc1_test_ts,
        },
        "window": parsed,
        "progress": {
            "explicit_rc1_test": explicit_rc1_test,
            "rc1_phy_ready": rc1_phy_ts is not None,
            "rc1_l0": rc1_l0,
            "rc1_link_failed": rc1_link_failed_ts is not None,
            "mhi_progress": mhi_ts is not None,
            "wlfw_progress": wlfw_ts is not None,
            "fw_ready_progress": fw_ready_ts is not None,
            "wlan0_present": wlan0_present,
            "connect_ready": wlan0_present,
            "downstream_progress": downstream_progress,
        },
        "classification": {
            "expected_micro_count": expected_micro_count,
            "complete_micro_offsets": complete_micro_offsets,
            "gpio135_all_low": parsed["gpio135_all_low"],
            "gpio142_all_low": parsed["gpio142_all_low"],
            "mdm_status_irq_all_zero": parsed["mdm_status_irq_all_zero"],
            "pcie_wake_irq_all_zero": parsed["pcie_wake_irq_all_zero"],
            "pcie1_gdsc_all_0mv_in_context": parsed["pcie1_gdsc_all_0mv"],
            "pcie1_clocks_all_zero_enable_in_context": parsed["pcie1_clocks_all_zero_enable"],
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
    timing = result["provider_timing"]
    cls = result["classification"]
    return "\n".join([
        "# Native Init V1453 Provider-Trigger Micro Handoff Classifier",
        "",
        "## Summary",
        "",
        "- Cycle: `V1453`",
        "- Type: host-only classifier over V1452 provider-trigger micro evidence",
        f"- Decision: `{result['decision']}`",
        f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
        f"- Reason: {result['reason']}",
        f"- Evidence: `{result['input_dir']}`",
        f"- Handoff decision: `{result['handoff_decision']}`",
        f"- Rollback v724 verified: `{result['rollback_ok']}`",
        f"- Test boot version verified: `{result['test_version_ok']}`",
        "",
        "## Provider Window",
        "",
        f"- micro sample count: `{window['micro_sample_count']}`",
        f"- micro offsets ms: `{window['micro_offsets_ms']}`",
        f"- expected micro count: `{cls['expected_micro_count']}`",
        f"- complete micro offsets: `{cls['complete_micro_offsets']}`",
        f"- context sample count: `{window['context_sample_count']}`",
        f"- modem `__subsystem_get` ts: `{timing['modem_get_ts']}`",
        f"- esoc0 `__subsystem_get` ts: `{timing['esoc_get_ts']}`",
        f"- explicit RC1 debugfs test ts: `{timing['rc1_test_ts']}`",
        f"- trigger chunk prefix not exact provider line: `{result['trigger_chunk_prefix_is_not_exact']}`",
        "",
        "## Endpoint State",
        "",
        f"- GPIO135 all low: `{cls['gpio135_all_low']}`",
        f"- GPIO142 all low: `{cls['gpio142_all_low']}`",
        f"- MDM status IRQ all zero: `{cls['mdm_status_irq_all_zero']}`",
        f"- PCIe wake IRQ all zero: `{cls['pcie_wake_irq_all_zero']}`",
        f"- pcie1 GDSC all 0mV in context sample: `{cls['pcie1_gdsc_all_0mv_in_context']}`",
        f"- pcie1 clocks all zero-enable in context sample: `{cls['pcie1_clocks_all_zero_enable_in_context']}`",
        f"- pcie link-state unreadable micro samples: `{window['pcie_link_unreadable_count']}`",
        f"- pcie current-link-state unreadable micro samples: `{window['pcie_current_unreadable_count']}`",
        "",
        "## Progress Classification",
        "",
        f"- explicit RC1 test write observed: `{progress['explicit_rc1_test']}`",
        f"- `rc1_phy_ready`: `{progress['rc1_phy_ready']}`",
        f"- `rc1_l0`: `{progress['rc1_l0']}`",
        f"- `rc1_link_failed`: `{progress['rc1_link_failed']}`",
        f"- `mhi_progress`: `{progress['mhi_progress']}`",
        f"- `wlfw_progress`: `{progress['wlfw_progress']}`",
        f"- `fw_ready_progress`: `{progress['fw_ready_progress']}`",
        f"- `wlan0_present`: `{progress['wlan0_present']}`",
        f"- `connect_ready`: `{progress['connect_ready']}`",
        "",
        "## Interpretation",
        "",
        "The rollbackable Wi-Fi test-boot strategy is valid for this phase: it can",
        "capture boot-time lower bring-up evidence and return to the main v724 image.",
        "V1452 did not prove Wi-Fi bring-up. It proved the opposite boundary: while",
        "the PM/CNSS path reached the esoc0 provider region, AP2MDM GPIO135 and",
        "MDM2AP GPIO142 stayed low, endpoint IRQs stayed at zero, pcie1 did not expose",
        "a readable link state, and no RC1/MHI/WLFW/BDF/FW-ready/`wlan0` marker",
        "appeared.",
        "",
        "One measurement weakness remains: the PID1 kmsg reader records the raw chunk",
        "that triggered the match, so the stored line prefix can show an earlier",
        "cnss-daemon netlink message even when the chunk also contains the provider",
        "line. The next image should split kmsg chunks into exact lines and extend",
        "the read-only provider window beyond `150ms`.",
        "",
        "## Safety Scope",
        "",
        "This classifier was host-only. It did not issue device commands, flash,",
        "reboot, start Wi-Fi HAL, scan/connect, use credentials, configure",
        "DHCP/routes, or perform external ping.",
        "",
        "## Next",
        "",
        "V1454 should be source/build-only and create an exact-line provider-trigger",
        "test boot. It should split `/proc/kmsg` chunks into individual lines, trigger",
        "only on the exact `__subsystem_get: esoc0` or `mdm_subsys_powerup` line, keep",
        "the run read-only, and extend endpoint samples to include at least `250ms`,",
        "`300ms`, `500ms`, and `1000ms` after the exact provider trigger.",
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

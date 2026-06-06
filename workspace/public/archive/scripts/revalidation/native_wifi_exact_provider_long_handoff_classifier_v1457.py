#!/usr/bin/env python3
"""V1457 host-only classifier for V1456 exact provider long-window evidence."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from a90harness.evidence import EvidenceStore, write_private_text


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
DEFAULT_INPUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1456-wifi-test-boot-exact-provider-long-endpoint-handoff"
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1457-exact-provider-long-handoff-classifier"
DEFAULT_REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1457_EXACT_PROVIDER_LONG_HANDOFF_CLASSIFIER_2026-06-01.md"
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

    return {
        "micro_sample_count": len(micro_samples),
        "micro_samples": micro_samples,
        "micro_offsets_ms": [sample["micro_elapsed_ms"] for sample in micro_samples],
        "context_sample_count": len(context_samples),
        "context_samples": context_samples,
        "labels": all_labels,
        "gpio135_all_low": bool(gpio135_values) and all("out 0" in value for value in gpio135_values),
        "gpio142_all_low": bool(gpio142_values) and all("in 0" in value for value in gpio142_values),
        "gpio135_values": gpio135_values,
        "gpio142_values": gpio142_values,
        "mdm_status_irq_all_zero": bool(mdm_status_lines) and all(": 0 0 0 0 0 0 0 0" in line for line in mdm_status_lines),
        "pcie_wake_irq_all_zero": bool(pcie_wake_lines) and all(": 0 0 0 0 0 0 0 0" in line for line in pcie_wake_lines),
        "pcie1_gdsc_all_0mv": bool(pcie1_regulator_lines) and all(" 0mV " in line for line in pcie1_regulator_lines),
        "pcie1_clocks_all_zero_enable": bool(pcie1_clock_lines) and all(" 0 0 0 " in line for line in pcie1_clock_lines),
        "post_1200_present": any(sample["label"] == "post_provider_micro_1200ms" for sample in context_samples),
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
    expected_offsets = [0, 11, 21, 31, 38, 43, 50, 100, 150, 250, 300, 500, 1001]
    expected_samples = parsed["micro_sample_count"] == 13
    offsets_ok = parsed["micro_offsets_ms"] == expected_offsets

    explicit_rc1_test = "PCIe: TEST:" in dmesg or "rc1_micro_writer_summary" in window_text
    rc1_progress = any(marker in dmesg for marker in ("PCIe RC1 PHY is ready", "LTSSM_STATE", "PCIe RC1 Current", "PCIe RC1 link"))
    mhi_progress = any(marker in dmesg for marker in ("mhi_arch", "mhi_pci", "mhi_0305", "MHI control"))
    wlfw_progress = any(marker in dmesg for marker in ("wlfw", "WLFW", "icnss_qmi"))
    bdf_progress = any(marker in dmesg for marker in ("BDF", "bdwlan", "regdb"))
    fw_ready_progress = any(marker in dmesg for marker in ("FW ready", "fw_ready", "FW_READY"))
    wlan0_present = "wlan0=present" in wlan0
    downstream_progress = any((rc1_progress, mhi_progress, wlfw_progress, bdf_progress, fw_ready_progress, wlan0_present))
    rollback_ok = "A90 Linux init 0.9.68 (v724)" in rollback
    test_version_ok = "A90 Linux init 0.9.84 (v1454-wifitest)" in version

    if (
        handoff.get("pass")
        and rollback_ok
        and test_version_ok
        and exact_header
        and long_header
        and exact_watcher_line
        and expected_samples
        and offsets_ok
        and parsed["post_1200_present"]
        and parsed["gpio135_all_low"]
        and parsed["gpio142_all_low"]
        and parsed["mdm_status_irq_all_zero"]
        and parsed["pcie_wake_irq_all_zero"]
        and parsed["pcie1_gdsc_all_0mv"]
        and parsed["pcie1_clocks_all_zero_enable"]
        and not explicit_rc1_test
        and not downstream_progress
    ):
        decision = "v1457-exact-provider-long-window-low-no-downstream"
        passed = True
        reason = (
            "V1456 exact-line provider trigger and long read-only window confirmed: "
            "GPIO135/GPIO142, endpoint IRQs, pcie1 GDSC/clocks, and downstream Wi-Fi markers stayed inactive"
        )
        next_gate = "V1458 source/build-only provider-trigger thread-state sampler"
    else:
        decision = "v1457-exact-provider-long-window-needs-review"
        passed = False
        reason = "V1456 evidence did not satisfy the exact-line long-window classifier contract"
        next_gate = "review V1456 evidence before another test boot"

    return {
        "cycle": "V1457",
        "decision": decision,
        "pass": passed,
        "reason": reason,
        "input_dir": rel(input_dir),
        "handoff_decision": handoff.get("decision", ""),
        "handoff_pass": bool(handoff.get("pass")),
        "rollback_ok": rollback_ok,
        "test_version_ok": test_version_ok,
        "provider_timing": {
            "modem_get_ts": first_dmesg_ts(dmesg, "__subsystem_get: modem"),
            "esoc_get_ts": first_dmesg_ts(dmesg, "__subsystem_get: esoc0"),
        },
        "window": parsed,
        "classification": {
            "exact_header": exact_header,
            "long_header": long_header,
            "exact_watcher_line": exact_watcher_line,
            "expected_samples": expected_samples,
            "offsets_ok": offsets_ok,
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
    timing = result["provider_timing"]
    return "\n".join([
        "# Native Init V1457 Exact Provider Long Handoff Classifier",
        "",
        "## Summary",
        "",
        "- Cycle: `V1457`",
        "- Type: host-only classifier over V1456 exact provider long-window evidence",
        f"- Decision: `{result['decision']}`",
        f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
        f"- Reason: {result['reason']}",
        f"- Evidence: `{result['input_dir']}`",
        f"- Handoff decision: `{result['handoff_decision']}`",
        f"- Rollback v724 verified: `{result['rollback_ok']}`",
        "",
        "## Exact Provider Window",
        "",
        f"- exact header: `{cls['exact_header']}`",
        f"- long-window header: `{cls['long_header']}`",
        f"- exact watcher line: `{cls['exact_watcher_line']}`",
        f"- modem `__subsystem_get` ts: `{timing['modem_get_ts']}`",
        f"- esoc0 `__subsystem_get` ts: `{timing['esoc_get_ts']}`",
        f"- micro sample count: `{window['micro_sample_count']}`",
        f"- micro offsets ms: `{window['micro_offsets_ms']}`",
        f"- offsets ok: `{cls['offsets_ok']}`",
        f"- post `1200ms` context present: `{cls['post_1200_present']}`",
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
        "V1456 closes the prior measurement weakness. The trigger line is the exact",
        "`__subsystem_get: esoc0` provider line, not a chunk prefix. Even with the",
        "read-only window extended to `1000ms` plus a `1200ms` context sample, AP2MDM",
        "GPIO135 stayed low, MDM2AP GPIO142 stayed low, endpoint IRQs stayed zero,",
        "pcie1 GDSC/clocks stayed off, and no RC1/MHI/WLFW/BDF/FW-ready/`wlan0`",
        "marker appeared.",
        "",
        "The next useful question is no longer trigger timing. It is where the",
        "provider-trigger thread blocks before the expected GPIO/pcie1 side effects.",
        "",
        "## Safety Scope",
        "",
        "This classifier was host-only. It did not issue device commands, flash,",
        "reboot, start Wi-Fi HAL, scan/connect, use credentials, configure",
        "DHCP/routes, or perform external ping.",
        "",
        "## Next",
        "",
        "V1458 should be source/build-only and add a provider-trigger thread-state",
        "sampler: capture the triggering Binder thread PID/TID, `/proc/<pid>/task/*/wchan`,",
        "state, and compact stack-adjacent process metadata around exact provider",
        "trigger time, still without PMIC/GPIO/GDSC writes, RC1 debugfs writes, Wi-Fi",
        "HAL, scan/connect, DHCP/routes, or external ping.",
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

#!/usr/bin/env python3
"""V1510 host-only classifier for V1509 batched pre-L0 parity evidence."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from a90harness.evidence import EvidenceStore, write_private_text


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_V1509_DIR = REPO_ROOT / "tmp" / "wifi" / "v1509-wifi-batched-pre-l0-parity-handoff"
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1510-wifi-batched-pre-l0-parity-classifier"
DEFAULT_REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1510_WIFI_BATCHED_PRE_L0_PARITY_CLASSIFIER_2026-06-01.md"
)
EXPECTED_LABELS = (
    "case_aligned_micro_after_case_0ms",
    "case_aligned_micro_after_case_1ms",
    "case_aligned_micro_after_case_2ms",
    "case_aligned_micro_after_case_5ms",
    "case_aligned_micro_after_case_10ms",
    "case_aligned_micro_after_case_20ms",
    "case_aligned_micro_after_case_50ms",
    "case_aligned_micro_after_case_100ms",
    "case_aligned_micro_after_case_150ms",
)
GPIO_EXPECTED = {
    "gpio102": ("out", "0"),
    "gpio103": ("in", "1"),
    "gpio104": ("in", "0"),
    "gpio135": ("out", "0"),
    "gpio142": ("in", "0"),
}
PCIE1_CLOCKS = (
    "gcc_pcie_1_slv_q2a_axi_clk",
    "gcc_pcie_1_slv_axi_clk",
    "gcc_pcie_1_pipe_clk",
    "gcc_pcie_1_mstr_axi_clk",
    "gcc_pcie_1_clkref_clk",
    "gcc_pcie_1_cfg_ahb_clk",
)
REFGEN_CLOCKS = (
    "gcc_pcie1_phy_refgen_clk",
    "gcc_pcie_phy_refgen_clk_src",
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


def read_json(path: Path) -> dict[str, Any]:
    text = read_text(path)
    return json.loads(text) if text else {}


def first_ts(text: str, needle: str) -> float | None:
    for line in text.splitlines():
        if needle not in line:
            continue
        match = DMESG_TS_RE.match(line)
        if match is not None:
            return float(match.group("ts"))
    return None


def sample_lines(text: str, label: str) -> list[str]:
    prefix = f"sample={label} "
    return [line.strip() for line in text.splitlines() if prefix in line]


def find_source_line(lines: list[str], source: str, needle: str | None = None) -> str:
    for line in lines:
        if f"source={source}" not in line:
            continue
        if needle is not None and needle not in line:
            continue
        return line
    return ""


def parse_micro_headers(text: str) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    pattern = re.compile(
        r"^rc1_micro_sample label=(?P<label>\S+) "
        r"elapsed_ms=(?P<elapsed>-?\d+) "
        r"detect_elapsed_ms=(?P<detect>-?\d+) "
        r"micro_elapsed_ms=(?P<micro>-?\d+)"
    )
    for line in text.splitlines():
        match = pattern.match(line.strip())
        if match is None:
            continue
        out[match.group("label")] = {
            "elapsed_ms": int(match.group("elapsed")),
            "detect_elapsed_ms": int(match.group("detect")),
            "micro_elapsed_ms": int(match.group("micro")),
            "line": line.strip(),
        }
    return out


def parse_gpio(line: str) -> dict[str, str]:
    match = re.search(r"(?:match(?:_\d+)?=)\s*(gpio\d+)\s*:\s*(\S+)\s+(\S+)(?:\s+(.*))?$", line)
    if match is None:
        return {}
    return {
        "name": match.group(1),
        "direction": match.group(2),
        "level": match.group(3),
        "tail": (match.group(4) or "").strip(),
    }


def irq_count(line: str) -> int | None:
    if ":" not in line:
        return None
    after_colon = line.split(":", 1)[1]
    before_name = after_colon.split("msmgpio-dc", 1)[0]
    counts = [int(token) for token in before_name.split() if token.isdigit()]
    if not counts:
        return None
    return sum(counts)


def clock_off(line: str) -> bool:
    return " 0 0 0 0 0 " in line


def parse_label(text: str, label: str) -> dict[str, Any]:
    lines = sample_lines(text, label)
    joined = "\n".join(lines)
    regulator = {
        "pcie_1_gdsc": find_source_line(lines, "micro_batched_regulator", "pcie_1_gdsc"),
        "pcie_0_gdsc": find_source_line(lines, "micro_batched_regulator", "pcie_0_gdsc"),
        "pm8150l_l3": find_source_line(lines, "micro_batched_regulator", "pm8150l_l3"),
        "pm8150_l5": find_source_line(lines, "micro_batched_regulator", "pm8150_l5"),
    }
    clocks = {clock: find_source_line(lines, "micro_batched_clk", clock) for clock in (*PCIE1_CLOCKS, *REFGEN_CLOCKS)}
    gpio = {
        name: parse_gpio(find_source_line(lines, "micro_batched_debug_gpio", name))
        for name in GPIO_EXPECTED
    }
    pinmux = {
        name: find_source_line(lines, "micro_batched_pinmux", name.replace("gpio", "GPIO_"))
        for name in GPIO_EXPECTED
    }
    pinconf = {
        name: find_source_line(lines, "micro_batched_pinconf", name.replace("gpio", "GPIO_"))
        for name in GPIO_EXPECTED
    }
    wake_line = ""
    status_line = ""
    for line in lines:
        if "source=micro_interrupts" not in line:
            continue
        if "msmgpio-dc 104" in line:
            wake_line = line
        if "msmgpio-dc 142" in line:
            status_line = line
    return {
        "batched_present": "micro_batched_focused_endpoint_sampler=1" in joined,
        "pcie1_gdsc_off": "pcie_1_gdsc" in regulator["pcie_1_gdsc"] and "0mV" in regulator["pcie_1_gdsc"],
        "pcie1_clocks_off": all(clock_off(clocks[clock]) for clock in PCIE1_CLOCKS),
        "refgen_available": all("19200000" in clocks[clock] for clock in REFGEN_CLOCKS),
        "gpio_expected": all(
            gpio[name].get("direction") == expected[0] and gpio[name].get("level") == expected[1]
            for name, expected in GPIO_EXPECTED.items()
        ),
        "gpio104_wake_count": irq_count(wake_line),
        "gpio142_mdm_status_count": irq_count(status_line),
        "pinmux_expected": all(pinmux[name] for name in GPIO_EXPECTED),
        "pinconf_present": all(pinconf[name] for name in GPIO_EXPECTED),
        "regulator": regulator,
        "clocks": clocks,
        "gpio": gpio,
        "pinmux": pinmux,
        "pinconf": pinconf,
    }


def parse_dmesg(text: str) -> dict[str, Any]:
    timestamps = {
        "esoc0": first_ts(text, "__subsystem_get: esoc0"),
        "case11": first_ts(text, "PCIe: TEST: 11"),
        "assert_reset": first_ts(text, "Assert the reset of endpoint of RC1"),
        "phy_ready": first_ts(text, "PCIe RC1 PHY is ready"),
        "release_reset": first_ts(text, "Release the reset of endpoint of RC1"),
        "detect_quiet": first_ts(text, "LTSSM_DETECT_QUIET"),
        "poll_active": first_ts(text, "LTSSM_POLL_ACTIVE"),
        "poll_compliance": first_ts(text, "LTSSM_POLL_COMPLIANCE"),
        "link_failed": first_ts(text, "PCIe RC1 link initialization failed"),
        "l0": first_ts(text, "LTSSM_L0"),
        "mhi": first_ts(text, "MHI"),
        "wlfw": first_ts(text, "WLFW"),
        "wlan0": first_ts(text, "wlan0"),
    }
    derived: dict[str, float] = {}
    if timestamps["case11"] is not None and timestamps["esoc0"] is not None:
        derived["case_after_esoc0_ms"] = round((timestamps["case11"] - timestamps["esoc0"]) * 1000.0, 3)
    if timestamps["phy_ready"] is not None and timestamps["case11"] is not None:
        derived["phy_ready_after_case_ms"] = round((timestamps["phy_ready"] - timestamps["case11"]) * 1000.0, 3)
    if timestamps["link_failed"] is not None and timestamps["case11"] is not None:
        derived["link_failed_after_case_ms"] = round((timestamps["link_failed"] - timestamps["case11"]) * 1000.0, 3)
    states = sorted(set(re.findall(r"LTSSM_STATE:\s+(LTSSM_[A-Z_]+)", text)))
    return {
        "timestamps": timestamps,
        "derived": derived,
        "ltssm_states": states,
        "link_failed": "PCIe RC1 link initialization failed" in text,
        "l0": "LTSSM_L0" in text or "Current GEN" in text,
        "mhi": "MHI" in text,
        "wlfw": "WLFW" in text,
        "bdf": "BDF" in text,
        "fw_ready": "FW ready" in text or "fw_ready" in text,
        "wlan0": "wlan0" in text,
    }


def classify(v1509_dir: Path) -> dict[str, Any]:
    manifest = read_json(v1509_dir / "manifest.json")
    progress = manifest.get("wifi_progress", {})
    rc1_text = read_text(v1509_dir / "test-rc1-window-result.stdout.txt")
    dmesg_text = read_text(v1509_dir / "test-v1393-dmesg.stdout.txt")
    headers = parse_micro_headers(rc1_text)
    missing_labels = [label for label in EXPECTED_LABELS if label not in headers]
    labels = {label: parse_label(rc1_text, label) for label in EXPECTED_LABELS if label in headers}
    micro_elapsed = {label: headers[label]["micro_elapsed_ms"] for label in EXPECTED_LABELS if label in headers}
    first_label = EXPECTED_LABELS[0]
    second_label = EXPECTED_LABELS[1]
    first_sample = labels.get(first_label, {})
    all_batched_present = bool(labels) and all(item["batched_present"] for item in labels.values())
    all_gdsc_off = bool(labels) and all(item["pcie1_gdsc_off"] for item in labels.values())
    all_clocks_off = bool(labels) and all(item["pcie1_clocks_off"] for item in labels.values())
    all_refgen_available = bool(labels) and all(item["refgen_available"] for item in labels.values())
    all_gpio_expected = bool(labels) and all(item["gpio_expected"] for item in labels.values())
    all_status_irq_zero = bool(labels) and all(item["gpio142_mdm_status_count"] == 0 for item in labels.values())
    all_pinmux_expected = bool(labels) and all(item["pinmux_expected"] for item in labels.values())
    all_pinconf_present = bool(labels) and all(item["pinconf_present"] for item in labels.values())
    dmesg = parse_dmesg(dmesg_text)
    link_failed_after_case_ms = dmesg["derived"].get("link_failed_after_case_ms")
    first_micro = micro_elapsed.get(first_label)
    second_micro = micro_elapsed.get(second_label)
    first_sample_before_link_fail = (
        isinstance(first_micro, int)
        and isinstance(link_failed_after_case_ms, float)
        and first_micro < link_failed_after_case_ms
    )
    second_sample_after_link_fail = (
        isinstance(second_micro, int)
        and isinstance(link_failed_after_case_ms, float)
        and second_micro > link_failed_after_case_ms
    )
    source_timestamps_missing = "source_begin_elapsed_ms=" not in rc1_text and "source_end_elapsed_ms=" not in rc1_text
    batched_still_overruns_micro_window = bool(second_micro is not None and second_micro > 100)
    improved_vs_v1505_exact = bool(second_micro is not None and second_micro < 500)

    checks = {
        "handoff": {
            "decision": manifest.get("decision"),
            "pass": manifest.get("pass") is True,
            "handoff_pass": manifest.get("handoff_pass") is True,
            "rollback_ok": manifest.get("rollback", {}).get("ok") is True,
        },
        "progress": {
            "final_decision": progress.get("final_decision"),
            "provider_trigger": progress.get("provider_trigger") is True,
            "rc1_progress": progress.get("rc1_progress") is True,
            "rc1_l0": progress.get("rc1_l0") is True,
            "rc1_link_failed": progress.get("rc1_link_failed") is True,
            "mhi_progress": progress.get("mhi_progress") is True,
            "wlfw_progress": progress.get("wlfw_progress") is True,
            "bdf_progress": progress.get("bdf_progress") is True,
            "fw_ready_progress": progress.get("fw_ready_progress") is True,
            "wlan0_present": progress.get("wlan0_present") is True,
        },
        "labels": {
            "missing": missing_labels,
            "count": len(headers),
            "micro_elapsed_ms": micro_elapsed,
        },
        "batched": {
            "all_batched_present": all_batched_present,
            "all_gdsc_off": all_gdsc_off,
            "all_pcie1_clocks_off": all_clocks_off,
            "all_refgen_available": all_refgen_available,
            "all_gpio_expected": all_gpio_expected,
            "all_gpio142_irq_zero": all_status_irq_zero,
            "all_pinmux_expected": all_pinmux_expected,
            "all_pinconf_present": all_pinconf_present,
            "first_sample": first_sample,
        },
        "timing": {
            "first_label_micro_elapsed_ms": first_micro,
            "second_label_micro_elapsed_ms": second_micro,
            "max_micro_elapsed_ms": max(micro_elapsed.values()) if micro_elapsed else None,
            "link_failed_after_case_ms": link_failed_after_case_ms,
            "first_sample_before_link_fail": first_sample_before_link_fail,
            "second_sample_after_link_fail": second_sample_after_link_fail,
            "batched_still_overruns_micro_window": batched_still_overruns_micro_window,
            "improved_vs_v1505_exact": improved_vs_v1505_exact,
            "source_timestamps_missing": source_timestamps_missing,
        },
        "dmesg": dmesg,
    }
    required = [
        checks["handoff"]["pass"],
        checks["handoff"]["handoff_pass"],
        checks["handoff"]["rollback_ok"],
        checks["progress"]["final_decision"] == "rc1-ltssm-link-failed-no-l0",
        checks["progress"]["provider_trigger"],
        checks["progress"]["rc1_progress"],
        checks["progress"]["rc1_link_failed"],
        not checks["progress"]["rc1_l0"],
        not checks["progress"]["mhi_progress"],
        not checks["progress"]["wlfw_progress"],
        not checks["progress"]["bdf_progress"],
        not checks["progress"]["fw_ready_progress"],
        not checks["progress"]["wlan0_present"],
        not missing_labels,
        all_batched_present,
        all_gdsc_off,
        all_clocks_off,
        all_refgen_available,
        all_gpio_expected,
        all_status_irq_zero,
        all_pinmux_expected,
        all_pinconf_present,
        first_sample_before_link_fail,
        second_sample_after_link_fail,
        batched_still_overruns_micro_window,
        improved_vs_v1505_exact,
        source_timestamps_missing,
        dmesg["link_failed"],
        not dmesg["l0"],
        not dmesg["mhi"],
        not dmesg["wlfw"],
        not dmesg["wlan0"],
    ]
    pass_ok = all(bool(item) for item in required)
    if pass_ok:
        decision = "v1510-batched-pre-l0-improves-sampling-but-source-timestamps-needed"
        reason = "V1509 batched evidence preserves the RC1 no-L0 failure classification and captures first-sample pre-link-fail state, but per-source timestamps are still missing"
    else:
        decision = "v1510-batched-pre-l0-classifier-blocked"
        reason = "V1509 batched evidence did not satisfy the strict classifier"
    return {
        "cycle": "V1510",
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "v1509_dir": rel(v1509_dir),
        "checks": checks,
        "next_gate": {
            "primary": "V1511 source/build-only source-timestamped batched sampler",
            "rationale": "V1509 reads batched data faster than V1505, but the first sample still contains several file reads with no source begin/end timing; add per-source timestamps or narrow to critical files only.",
        },
    }


def render_report(result: dict[str, Any]) -> str:
    checks = result["checks"]
    timing = checks["timing"]
    batched = checks["batched"]
    dmesg = checks["dmesg"]
    lines = [
        "# Native Init V1510 Wi-Fi Batched Pre-L0 Parity Classifier",
        "",
        "## Summary",
        "",
        "- Cycle: `V1510`",
        "- Type: host-only classifier over V1509 live handoff evidence",
        f"- Decision: `{result['decision']}`",
        f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
        f"- Reason: {result['reason']}",
        f"- Evidence: `{result['v1509_dir']}`",
        "",
        "## Handoff Result",
        "",
        f"- V1509 decision: `{checks['handoff']['decision']}`",
        f"- handoff pass: `{checks['handoff']['handoff_pass']}`",
        f"- rollback ok: `{checks['handoff']['rollback_ok']}`",
        f"- progress decision: `{checks['progress']['final_decision']}`",
        f"- RC1 progress/link failed/L0: `{checks['progress']['rc1_progress']}/{checks['progress']['rc1_link_failed']}/{checks['progress']['rc1_l0']}`",
        f"- MHI/WLFW/BDF/FW-ready/wlan0: `{checks['progress']['mhi_progress']}/{checks['progress']['wlfw_progress']}/{checks['progress']['bdf_progress']}/{checks['progress']['fw_ready_progress']}/{checks['progress']['wlan0_present']}`",
        "",
        "## Batched Focused Reads",
        "",
        f"- labels present: `{checks['labels']['count']}` / `{len(EXPECTED_LABELS)}`",
        f"- batched marker present for every label: `{batched['all_batched_present']}`",
        f"- `pcie_1_gdsc` off for every label: `{batched['all_gdsc_off']}`",
        f"- PCIe1 batched clocks off for every label: `{batched['all_pcie1_clocks_off']}`",
        f"- refgen clocks available for every label: `{batched['all_refgen_available']}`",
        f"- GPIO102/103/104/135/142 expected for every label: `{batched['all_gpio_expected']}`",
        f"- GPIO142 mdm-status IRQ stays zero: `{batched['all_gpio142_irq_zero']}`",
        f"- pinmux lines present for every label: `{batched['all_pinmux_expected']}`",
        f"- pinconf lines present for every label: `{batched['all_pinconf_present']}`",
        "",
        "## Timing Caveat",
        "",
        f"- link failed after TEST:11 case: `{timing['link_failed_after_case_ms']}` ms",
        f"- first sample actual micro elapsed: `{timing['first_label_micro_elapsed_ms']}` ms",
        f"- second sample actual micro elapsed: `{timing['second_label_micro_elapsed_ms']}` ms",
        f"- max sample actual micro elapsed: `{timing['max_micro_elapsed_ms']}` ms",
        f"- first sample starts before link fail: `{timing['first_sample_before_link_fail']}`",
        f"- second sample starts after link fail: `{timing['second_sample_after_link_fail']}`",
        f"- improved versus V1505 exact scanner: `{timing['improved_vs_v1505_exact']}`",
        f"- still overruns nominal micro window: `{timing['batched_still_overruns_micro_window']}`",
        f"- per-source timestamps missing: `{timing['source_timestamps_missing']}`",
        "",
        "V1509 is materially faster than V1505 because each debugfs source is read once per sample. It is still not a source-exact first-150ms proof: the first sample starts at case+0ms, but it reads several sources without per-source begin/end timestamps, while the second sample starts after the RC1 link-fail marker.",
        "",
        "## Dmesg Classification",
        "",
        f"- LTSSM states: `{', '.join(dmesg['ltssm_states'])}`",
        f"- case after esoc0: `{dmesg['derived'].get('case_after_esoc0_ms')}` ms",
        f"- PHY ready after case: `{dmesg['derived'].get('phy_ready_after_case_ms')}` ms",
        f"- link failed after case: `{dmesg['derived'].get('link_failed_after_case_ms')}` ms",
        f"- link failed marker: `{dmesg['link_failed']}`",
        f"- L0/MHI/WLFW/BDF/FW-ready/wlan0: `{dmesg['l0']}/{dmesg['mhi']}/{dmesg['wlfw']}/{dmesg['bdf']}/{dmesg['fw_ready']}/{dmesg['wlan0']}`",
        "",
        "## Interpretation",
        "",
        "V1509 keeps the current blocker fixed at `rc1-ltssm-link-failed-no-l0`. The batched sample shows the same pre-L0 endpoint-response symptoms: `pcie_1_gdsc` and PCIe1 clocks stay off, refgen remains available, GPIO135/GPIO142 stay inactive, and GPIO142 IRQ does not fire. Firmware, MHI, WLFW, BDF, FW-ready, wlan0, scan/connect, and network tests remain downstream and should stay parked until RC1 reaches L0 and PCI enumeration exists.",
        "",
        "## Safety Scope",
        "",
        "This classifier is host-only. It performs no device command, flash, reboot, partition write, Wi-Fi HAL start, scan/connect, credential handling, DHCP/routes, external ping, PMIC/GPIO/GDSC write, eSoC notify/`BOOT_DONE` spoof, global PCI rescan, or platform bind/unbind.",
        "",
        "## Next",
        "",
        "- V1511 should add source begin/end timestamps to the batched sampler or narrow the capture to the minimum critical sources.",
        "- Keep firmware/MHI/WLFW/scan/connect work parked until RC1 L0 and PCI enumeration exist.",
        "",
    ]
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--v1509-dir", type=Path, default=DEFAULT_V1509_DIR)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--write-report", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.v1509_dir.exists():
        raise SystemExit(f"missing V1509 evidence dir: {args.v1509_dir}")
    store = EvidenceStore(args.out_dir)
    result = classify(args.v1509_dir)
    report = render_report(result)
    store.write_json("manifest.json", result)
    store.write_text("summary.md", report)
    if args.write_report:
        write_private_text(args.report_path, report)
    print(json.dumps({"decision": result["decision"], "pass": result["pass"], "out_dir": rel(args.out_dir)}, indent=2))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

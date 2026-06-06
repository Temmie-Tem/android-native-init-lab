#!/usr/bin/env python3
"""V1506 host-only classifier for V1505 dense pre-L0 parity evidence."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from a90harness.evidence import EvidenceStore, write_private_text


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
DEFAULT_V1505_DIR = REPO_ROOT / "tmp" / "wifi" / "v1505-wifi-dense-pre-l0-parity-handoff"
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1506-wifi-dense-pre-l0-parity-classifier"
DEFAULT_REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1506_WIFI_DENSE_PRE_L0_PARITY_CLASSIFIER_2026-06-01.md"
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


def first_line(lines: list[str], source: str, needle: str | None = None) -> str:
    for line in lines:
        if f"source={source}" not in line:
            continue
        if needle is not None and f"needle={needle}" not in line:
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
    match = re.search(r"needle=(gpio\d+)\s+match=\s*(gpio\d+)\s*:\s*(\S+)\s+(\S+)(?:\s+(.*))?$", line)
    if match is None:
        return {}
    return {
        "needle": match.group(1),
        "direction": match.group(3),
        "level": match.group(4),
        "tail": (match.group(5) or "").strip(),
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
    focused_present = "micro_focused_endpoint_sampler=1" in "\n".join(lines)
    regulator = {
        "pcie_1_gdsc": first_line(lines, "micro_focused_regulator", "pcie_1_gdsc"),
        "pcie_0_gdsc": first_line(lines, "micro_focused_regulator", "pcie_0_gdsc"),
        "pm8150l_l3": first_line(lines, "micro_focused_regulator", "pm8150l_l3"),
        "pm8150_l5": first_line(lines, "micro_focused_regulator", "pm8150_l5"),
    }
    clocks = {clock: first_line(lines, "micro_focused_clk", clock) for clock in (*PCIE1_CLOCKS, *REFGEN_CLOCKS)}
    gpio = {
        name: parse_gpio(first_line(lines, "micro_focused_debug_gpio", name))
        for name in GPIO_EXPECTED
    }
    pinmux = {
        name: first_line(lines, "micro_focused_pinmux", name)
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
        "focused_present": focused_present,
        "pcie1_gdsc_off": "pcie_1_gdsc" in regulator["pcie_1_gdsc"] and "0mV" in regulator["pcie_1_gdsc"],
        "pcie1_clocks_off": all(clock_off(clocks[clock]) for clock in PCIE1_CLOCKS),
        "refgen_available": all("19200000" in clocks[clock] for clock in REFGEN_CLOCKS),
        "gpio_expected": all(
            gpio[name].get("direction") == expected[0] and gpio[name].get("level") == expected[1]
            for name, expected in GPIO_EXPECTED.items()
        ),
        "gpio104_wake_count": irq_count(wake_line),
        "gpio142_mdm_status_count": irq_count(status_line),
        "regulator": regulator,
        "clocks": clocks,
        "gpio": gpio,
        "pinmux": pinmux,
    }


def parse_dmesg(text: str) -> dict[str, Any]:
    timestamps = {
        "esoc0": first_ts(text, "__subsystem_get: esoc0"),
        "case11": first_ts(text, "PCIe: TEST: 11"),
        "phy_ready": first_ts(text, "PCIe RC1 PHY is ready"),
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


def classify(v1505_dir: Path) -> dict[str, Any]:
    manifest = read_json(v1505_dir / "manifest.json")
    progress = manifest.get("wifi_progress", {})
    rc1_text = read_text(v1505_dir / "test-rc1-window-result.stdout.txt")
    dmesg_text = read_text(v1505_dir / "test-v1393-dmesg.stdout.txt")
    headers = parse_micro_headers(rc1_text)
    missing_labels = [label for label in EXPECTED_LABELS if label not in headers]
    labels = {label: parse_label(rc1_text, label) for label in EXPECTED_LABELS if label in headers}
    micro_elapsed = {label: headers[label]["micro_elapsed_ms"] for label in EXPECTED_LABELS if label in headers}
    dense_overrun = any(value > 250 for label, value in micro_elapsed.items() if label != EXPECTED_LABELS[0])
    first_sample = labels.get(EXPECTED_LABELS[0], {})
    all_focused_present = bool(labels) and all(item["focused_present"] for item in labels.values())
    all_gdsc_off = bool(labels) and all(item["pcie1_gdsc_off"] for item in labels.values())
    all_clocks_off = bool(labels) and all(item["pcie1_clocks_off"] for item in labels.values())
    all_refgen_available = bool(labels) and all(item["refgen_available"] for item in labels.values())
    all_gpio_expected = bool(labels) and all(item["gpio_expected"] for item in labels.values())
    all_status_irq_zero = bool(labels) and all(item["gpio142_mdm_status_count"] == 0 for item in labels.values())
    dmesg = parse_dmesg(dmesg_text)

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
        "focused": {
            "all_focused_present": all_focused_present,
            "all_gdsc_off": all_gdsc_off,
            "all_pcie1_clocks_off": all_clocks_off,
            "all_refgen_available": all_refgen_available,
            "all_gpio_expected": all_gpio_expected,
            "all_gpio142_irq_zero": all_status_irq_zero,
            "first_sample": first_sample,
        },
        "timing": {
            "dense_overrun": dense_overrun,
            "first_label_micro_elapsed_ms": micro_elapsed.get(EXPECTED_LABELS[0]),
            "second_label_micro_elapsed_ms": micro_elapsed.get(EXPECTED_LABELS[1]),
            "max_micro_elapsed_ms": max(micro_elapsed.values()) if micro_elapsed else None,
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
        all_focused_present,
        all_gdsc_off,
        all_clocks_off,
        all_refgen_available,
        all_gpio_expected,
        all_status_irq_zero,
        dense_overrun,
        dmesg["link_failed"],
        not dmesg["l0"],
        not dmesg["mhi"],
        not dmesg["wlfw"],
        not dmesg["wlan0"],
    ]
    pass_ok = all(bool(item) for item in required)
    if pass_ok:
        decision = "v1506-dense-pre-l0-captures-off-state-but-overruns-micro-window"
        reason = "V1505 captured focused regulator/clock/GPIO state and still failed before L0, but exact-match dense reads overrun the intended micro window"
    else:
        decision = "v1506-dense-pre-l0-classifier-blocked"
        reason = "V1505 dense evidence did not satisfy the strict classifier"
    return {
        "cycle": "V1506",
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "v1505_dir": rel(v1505_dir),
        "checks": checks,
        "next_gate": {
            "primary": "V1507 source/build-only batched dense sampler",
            "rationale": "V1505 proves the fields are readable but exact-match scanning reopens large debugfs files many times per sample; batch each file once per sample before another live handoff.",
        },
    }


def render_report(result: dict[str, Any]) -> str:
    checks = result["checks"]
    timing = checks["timing"]
    focused = checks["focused"]
    dmesg = checks["dmesg"]
    lines = [
        "# Native Init V1506 Wi-Fi Dense Pre-L0 Parity Classifier",
        "",
        "## Summary",
        "",
        "- Cycle: `V1506`",
        "- Type: host-only classifier over V1505 live handoff evidence",
        f"- Decision: `{result['decision']}`",
        f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
        f"- Reason: {result['reason']}",
        f"- Evidence: `{result['v1505_dir']}`",
        "",
        "## Handoff Result",
        "",
        f"- V1505 decision: `{checks['handoff']['decision']}`",
        f"- handoff pass: `{checks['handoff']['handoff_pass']}`",
        f"- rollback ok: `{checks['handoff']['rollback_ok']}`",
        f"- progress decision: `{checks['progress']['final_decision']}`",
        f"- RC1 progress/link failed/L0: `{checks['progress']['rc1_progress']}/{checks['progress']['rc1_link_failed']}/{checks['progress']['rc1_l0']}`",
        f"- MHI/WLFW/BDF/FW-ready/wlan0: `{checks['progress']['mhi_progress']}/{checks['progress']['wlfw_progress']}/{checks['progress']['bdf_progress']}/{checks['progress']['fw_ready_progress']}/{checks['progress']['wlan0_present']}`",
        "",
        "## Dense Focused Reads",
        "",
        f"- labels present: `{checks['labels']['count']}` / `{len(EXPECTED_LABELS)}`",
        f"- focused marker present for every label: `{focused['all_focused_present']}`",
        f"- `pcie_1_gdsc` off for every label: `{focused['all_gdsc_off']}`",
        f"- PCIe1 focused clocks off for every label: `{focused['all_pcie1_clocks_off']}`",
        f"- refgen clocks available for every label: `{focused['all_refgen_available']}`",
        f"- GPIO102/103/104/135/142 expected for every label: `{focused['all_gpio_expected']}`",
        f"- GPIO142 mdm-status IRQ stays zero: `{focused['all_gpio142_irq_zero']}`",
        "",
        "## Timing Caveat",
        "",
        f"- first sample actual micro elapsed: `{timing['first_label_micro_elapsed_ms']}` ms",
        f"- second sample actual micro elapsed: `{timing['second_label_micro_elapsed_ms']}` ms",
        f"- max sample actual micro elapsed: `{timing['max_micro_elapsed_ms']}` ms",
        f"- dense sampler overran intended micro window: `{timing['dense_overrun']}`",
        "",
        "The dense exact-match implementation is diagnostically useful but too slow for 0/1/2/5/10/20/50/100/150ms timing. Each sample scans several debugfs files repeatedly, so labels after 0ms do not represent their nominal offsets.",
        "",
        "## Dmesg Classification",
        "",
        f"- LTSSM states: `{', '.join(dmesg['ltssm_states'])}`",
        f"- case after esoc0: `{dmesg['derived'].get('case_after_esoc0_ms')}` ms",
        f"- link failed after case: `{dmesg['derived'].get('link_failed_after_case_ms')}` ms",
        f"- link failed marker: `{dmesg['link_failed']}`",
        f"- L0/MHI/WLFW/BDF/FW-ready/wlan0: `{dmesg['l0']}/{dmesg['mhi']}/{dmesg['wlfw']}/{dmesg['bdf']}/{dmesg['fw_ready']}/{dmesg['wlan0']}`",
        "",
        "## Interpretation",
        "",
        "V1505 reinforces the pre-L0 endpoint-response blocker: RC1 reaches PHY/LTSSM and fails before L0, while focused state reads show `pcie_1_gdsc` and PCIe1 clocks off with refgen available and GPIO142 inactive. However, because the dense exact-match reads overrun the micro schedule, this cannot be treated as precise first-150ms timing evidence.",
        "",
        "## Safety Scope",
        "",
        "This classifier is host-only. It performs no device command, flash, reboot, partition write, Wi-Fi HAL start, scan/connect, credential handling, DHCP/routes, external ping, PMIC/GPIO/GDSC write, eSoC notify/`BOOT_DONE` spoof, global PCI rescan, or platform bind/unbind.",
        "",
        "## Next",
        "",
        "- V1507 should replace per-needle exact-match scanning with a batched per-file micro sampler so each debugfs file is read at most once per sample.",
        "- Do not move to firmware/MHI/WLFW/scan/connect work until RC1 L0 and PCI enumeration exist.",
        "",
    ]
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--v1505-dir", type=Path, default=DEFAULT_V1505_DIR)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--write-report", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.v1505_dir.exists():
        raise SystemExit(f"missing V1505 evidence dir: {args.v1505_dir}")
    store = EvidenceStore(args.out_dir)
    result = classify(args.v1505_dir)
    report = render_report(result)
    store.write_json("manifest.json", result)
    store.write_text("summary.md", report)
    if args.write_report:
        write_private_text(args.report_path, report)
    print(json.dumps({"decision": result["decision"], "pass": result["pass"], "out_dir": rel(args.out_dir)}, indent=2))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

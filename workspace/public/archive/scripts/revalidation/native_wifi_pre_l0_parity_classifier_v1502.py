#!/usr/bin/env python3
"""V1502 host-only classifier for V1501 pre-L0 endpoint parity evidence."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from a90harness.evidence import EvidenceStore, write_private_text


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
DEFAULT_V1501_DIR = REPO_ROOT / "tmp" / "wifi" / "v1501-wifi-pre-l0-parity-handoff"
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1502-wifi-pre-l0-parity-classifier"
DEFAULT_REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1502_WIFI_PRE_L0_PARITY_CLASSIFIER_2026-06-01.md"
)
EXPECTED_MICRO_LABELS = (
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
POST_LABEL = "post_case_aligned_micro_200ms"
EXPECTED_GPIO_STATES = {
    "gpio102": ("out", "0"),
    "gpio103": ("in", "1"),
    "gpio104": ("in", "0"),
    "gpio135": ("out", "0"),
    "gpio142": ("in", "0"),
}
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
        if match is None:
            continue
        return float(match.group("ts"))
    return None


def matching_lines(text: str, needles: tuple[str, ...], limit: int = 80) -> list[str]:
    lines: list[str] = []
    for line in text.splitlines():
        if any(needle in line for needle in needles):
            lines.append(line.strip())
        if len(lines) >= limit:
            break
    return lines


def sample_lines(text: str, label: str) -> list[str]:
    prefix = f"sample={label} "
    return [line.strip() for line in text.splitlines() if prefix in line]


def find_line(lines: list[str], source: str, needle: str | None = None) -> str:
    for line in lines:
        if f"source={source}" not in line:
            continue
        if needle is not None and f"needle={needle}" not in line:
            continue
        return line
    return ""


def parse_micro_labels(text: str) -> dict[str, Any]:
    label_re = re.compile(r"^rc1_micro_sample label=(?P<label>\S+).*?micro_elapsed_ms=(?P<elapsed>\d+)")
    observed: dict[str, dict[str, Any]] = {}
    for line in text.splitlines():
        match = label_re.match(line.strip())
        if match is None:
            continue
        observed[match.group("label")] = {
            "micro_elapsed_ms": int(match.group("elapsed")),
            "line": line.strip(),
        }
    missing = [label for label in EXPECTED_MICRO_LABELS if label not in observed]
    unexpected = [label for label in observed if label not in EXPECTED_MICRO_LABELS]
    return {
        "expected": list(EXPECTED_MICRO_LABELS),
        "observed": observed,
        "missing": missing,
        "unexpected": unexpected,
        "count": len(observed),
        "expected_present": not missing,
    }


def parse_gpio_state(line: str) -> dict[str, str]:
    match = re.search(r"needle=(gpio\d+)\s+match=\s*(gpio\d+)\s*:\s*(\S+)\s+(\S+)(?:\s+(.*))?$", line)
    if match is None:
        return {}
    return {
        "needle": match.group(1),
        "match_gpio": match.group(2),
        "direction": match.group(3),
        "level": match.group(4),
        "tail": (match.group(5) or "").strip(),
    }


def parse_micro_gpio(text: str) -> dict[str, Any]:
    by_label: dict[str, dict[str, Any]] = {}
    failing: list[dict[str, str]] = []
    for label in EXPECTED_MICRO_LABELS:
        lines = sample_lines(text, label)
        observed: dict[str, Any] = {}
        for gpio, expected in EXPECTED_GPIO_STATES.items():
            parsed = parse_gpio_state(find_line(lines, "micro_debug_gpio", gpio))
            observed[gpio] = parsed
            if parsed.get("direction") != expected[0] or parsed.get("level") != expected[1]:
                failing.append({
                    "label": label,
                    "gpio": gpio,
                    "expected": f"{expected[0]} {expected[1]}",
                    "observed": f"{parsed.get('direction', 'missing')} {parsed.get('level', 'missing')}",
                })
        by_label[label] = observed
    return {"by_label": by_label, "failures": failing, "all_expected": not failing}


def parse_interrupt_count(line: str) -> int | None:
    if ":" not in line:
        return None
    after_colon = line.split(":", 1)[1]
    before_name = after_colon.split("msmgpio-dc", 1)[0]
    counts = [int(token) for token in before_name.split() if token.isdigit()]
    if not counts:
        return None
    return sum(counts)


def parse_micro_interrupts(text: str) -> dict[str, Any]:
    by_label: dict[str, Any] = {}
    nonzero: list[dict[str, Any]] = []
    for label in EXPECTED_MICRO_LABELS:
        lines = sample_lines(text, label)
        wake_line = ""
        status_line = ""
        for line in lines:
            if "source=micro_interrupts" not in line:
                continue
            if "msmgpio-dc 104" in line:
                wake_line = line
            if "msmgpio-dc 142" in line:
                status_line = line
        wake_count = parse_interrupt_count(wake_line)
        status_count = parse_interrupt_count(status_line)
        by_label[label] = {
            "gpio104_wake_count": wake_count,
            "gpio142_mdm_status_count": status_count,
            "wake_line": wake_line,
            "status_line": status_line,
        }
        if wake_count not in (0, None):
            nonzero.append({"label": label, "irq": "gpio104_wake", "count": wake_count})
        if status_count not in (0, None):
            nonzero.append({"label": label, "irq": "gpio142_mdm_status", "count": status_count})
    missing = [
        {"label": label, "irq": irq}
        for label, item in by_label.items()
        for irq in ("gpio104_wake_count", "gpio142_mdm_status_count")
        if item[irq] is None
    ]
    return {
        "by_label": by_label,
        "missing": missing,
        "nonzero": nonzero,
        "all_present_zero": not missing and not nonzero,
    }


def parse_micro_link_state(text: str) -> dict[str, Any]:
    unreadable_by_label: dict[str, bool] = {}
    for label in EXPECTED_MICRO_LABELS:
        lines = sample_lines(text, label)
        current_line = find_line(lines, "micro_pcie1_current_link_state")
        link_line = find_line(lines, "micro_pcie1_link_state")
        unreadable_by_label[label] = "unreadable_rc=-1" in current_line and "unreadable_rc=-1" in link_line
    return {
        "unreadable_by_label": unreadable_by_label,
        "all_unreadable": all(unreadable_by_label.values()),
    }


def parse_post_sample(text: str) -> dict[str, Any]:
    lines = sample_lines(text, POST_LABEL)
    post_present = bool(re.search(rf"^rc1_window_sample label={re.escape(POST_LABEL)}\b", text, re.MULTILINE))
    focused_regulators = {
        "pcie_1_gdsc": find_line(lines, "focused_regulator", "pcie_1_gdsc"),
        "pcie_0_gdsc": find_line(lines, "focused_regulator", "pcie_0_gdsc"),
        "pm8150l_l3": find_line(lines, "focused_regulator", "pm8150l_l3"),
        "pm8150_l5": find_line(lines, "focused_regulator", "pm8150_l5"),
    }
    focused_clocks = {
        "gcc_pcie_1_pipe_clk": find_line(lines, "focused_clk", "gcc_pcie_1_pipe_clk"),
        "gcc_pcie_1_clkref_clk": find_line(lines, "focused_clk", "gcc_pcie_1_clkref_clk"),
        "gcc_pcie_1_slv_q2a_axi_clk": find_line(lines, "focused_clk", "gcc_pcie_1_slv_q2a_axi_clk"),
        "gcc_pcie_1_slv_axi_clk": find_line(lines, "focused_clk", "gcc_pcie_1_slv_axi_clk"),
        "gcc_pcie_1_mstr_axi_clk": find_line(lines, "focused_clk", "gcc_pcie_1_mstr_axi_clk"),
        "gcc_pcie_1_cfg_ahb_clk": find_line(lines, "focused_clk", "gcc_pcie_1_cfg_ahb_clk"),
        "gcc_pcie1_phy_refgen_clk": find_line(lines, "focused_clk", "gcc_pcie1_phy_refgen_clk"),
        "gcc_pcie_phy_refgen_clk_src": find_line(lines, "focused_clk", "gcc_pcie_phy_refgen_clk_src"),
    }
    focused_gpio = {
        gpio: parse_gpio_state(find_line(lines, "focused_debug_gpio", gpio))
        for gpio in ("gpio102", "gpio103", "gpio104", "gpio142")
    }
    pinmux = {
        gpio: find_line(lines, "focused_pinmux", gpio)
        for gpio in ("gpio102", "gpio103", "gpio104", "gpio142")
    }
    status_line = ""
    wake_line = ""
    errfatal_line = ""
    for line in lines:
        if "source=interrupts" not in line:
            continue
        if "msmgpio-dc 142" in line:
            status_line = line
        if "msmgpio-dc 104" in line:
            wake_line = line
        if "msmgpio-dc 53" in line:
            errfatal_line = line
    pcie1_gdsc_off = "pcie_1_gdsc" in focused_regulators["pcie_1_gdsc"] and "0mV" in focused_regulators["pcie_1_gdsc"]
    pcie1_clocks_off = all(
        " 0 0 0 0 0 " in line
        for key, line in focused_clocks.items()
        if key.startswith("gcc_pcie_1_")
    )
    refgen_present = "19200000" in focused_clocks["gcc_pcie1_phy_refgen_clk"]
    expected_gpio = all(
        focused_gpio[gpio].get("direction") == EXPECTED_GPIO_STATES[gpio][0]
        and focused_gpio[gpio].get("level") == EXPECTED_GPIO_STATES[gpio][1]
        for gpio in ("gpio102", "gpio103", "gpio104", "gpio142")
    )
    return {
        "present": post_present,
        "focused_regulators": focused_regulators,
        "focused_clocks": focused_clocks,
        "focused_gpio": focused_gpio,
        "pinmux": pinmux,
        "gpio104_wake_count": parse_interrupt_count(wake_line),
        "gpio142_mdm_status_count": parse_interrupt_count(status_line),
        "gpio53_mdm_errfatal_count": parse_interrupt_count(errfatal_line),
        "pcie1_gdsc_off_at_200ms": pcie1_gdsc_off,
        "pcie1_clocks_off_at_200ms": pcie1_clocks_off,
        "pcie1_refgen_available_at_200ms": refgen_present,
        "expected_gpio_at_200ms": expected_gpio,
    }


def parse_writer(text: str) -> dict[str, Any]:
    line = ""
    for candidate in text.splitlines():
        if "rc1_micro_writer_summary" in candidate:
            line = candidate.strip()
            break
    def int_field(name: str) -> int | None:
        match = re.search(rf"\b{re.escape(name)}=(-?\d+)", line)
        return int(match.group(1)) if match else None
    return {
        "line": line,
        "writer_wait_rc": int_field("writer_wait_rc"),
        "micro_writer_rc": int_field("rc"),
        "errno": int_field("errno"),
        "rc_sel_elapsed_ms": int_field("rc_sel_elapsed_ms"),
        "case_elapsed_ms": int_field("case_elapsed_ms"),
        "ok": "writer_wait_rc=0" in line and "micro_writer rc=0" in line and "errno=0" in line,
    }


def parse_dmesg(text: str) -> dict[str, Any]:
    timestamps = {
        "modem_subsystem_get": first_ts(text, "__subsystem_get: modem"),
        "esoc0_subsystem_get": first_ts(text, "__subsystem_get: esoc0"),
        "rc_sel": first_ts(text, "PCIe: rc_sel is now: 0x2"),
        "case11": first_ts(text, "PCIe: TEST: 11"),
        "assert_reset": first_ts(text, "Assert the reset of endpoint of RC1"),
        "phy_ready": first_ts(text, "PCIe RC1 PHY is ready"),
        "release_reset": first_ts(text, "Release the reset of endpoint of RC1"),
        "ltssm_detect_quiet": first_ts(text, "LTSSM_DETECT_QUIET"),
        "ltssm_poll_active": first_ts(text, "LTSSM_POLL_ACTIVE"),
        "ltssm_poll_compliance": first_ts(text, "LTSSM_POLL_COMPLIANCE"),
        "link_failed": first_ts(text, "PCIe RC1 link initialization failed"),
        "enumeration_failed": first_ts(text, "RC1 enumeration failed"),
        "ltssm_l0": first_ts(text, "LTSSM_L0"),
        "mhi": first_ts(text, "MHI"),
        "wlfw": first_ts(text, "WLFW"),
        "bdf": first_ts(text, "BDF"),
        "fw_ready": first_ts(text, "FW ready"),
        "wlan0": first_ts(text, "wlan0"),
    }
    derived: dict[str, float] = {}
    if timestamps["case11"] is not None and timestamps["esoc0_subsystem_get"] is not None:
        derived["case_after_esoc0_ms"] = round((timestamps["case11"] - timestamps["esoc0_subsystem_get"]) * 1000.0, 3)
    if timestamps["phy_ready"] is not None and timestamps["case11"] is not None:
        derived["phy_ready_after_case_ms"] = round((timestamps["phy_ready"] - timestamps["case11"]) * 1000.0, 3)
    if timestamps["link_failed"] is not None and timestamps["case11"] is not None:
        derived["link_failed_after_case_ms"] = round((timestamps["link_failed"] - timestamps["case11"]) * 1000.0, 3)
    ltssm_states = sorted(set(re.findall(r"LTSSM_STATE:\s+(LTSSM_[A-Z_]+)", text)))
    return {
        "timestamps": timestamps,
        "derived": derived,
        "ltssm_states": ltssm_states,
        "has_l0": "LTSSM_L0" in text or "Current GEN" in text,
        "has_link_failed": "PCIe RC1 link initialization failed" in text,
        "has_mhi": "MHI" in text,
        "has_wlfw": "WLFW" in text,
        "has_bdf": "BDF" in text,
        "has_fw_ready": "FW ready" in text or "fw_ready" in text,
        "has_wlan0": "wlan0" in text,
        "key_lines": matching_lines(
            text,
            (
                "__subsystem_get: modem",
                "__subsystem_get: esoc0",
                "PCIe: rc_sel is now: 0x2",
                "PCIe: TEST: 11",
                "Assert the reset of endpoint of RC1",
                "PCIe RC1 PHY is ready",
                "Release the reset of endpoint of RC1",
                "LTSSM_",
                "link initialization failed",
                "RC1 enumeration failed",
            ),
        ),
    }


def classify(v1501_dir: Path) -> dict[str, Any]:
    manifest = read_json(v1501_dir / "manifest.json")
    progress = manifest.get("wifi_progress", {})
    rc1_result = read_text(v1501_dir / "test-rc1-window-result.stdout.txt")
    dmesg = read_text(v1501_dir / "test-v1393-dmesg.stdout.txt")
    wlan0 = read_text(v1501_dir / "test-wlan0.stdout.txt")

    micro_labels = parse_micro_labels(rc1_result)
    writer = parse_writer(rc1_result)
    micro_gpio = parse_micro_gpio(rc1_result)
    micro_interrupts = parse_micro_interrupts(rc1_result)
    micro_link_state = parse_micro_link_state(rc1_result)
    post_sample = parse_post_sample(rc1_result)
    dmesg_result = parse_dmesg(dmesg)

    checks = {
        "handoff": {
            "manifest_decision": manifest.get("decision"),
            "pass": manifest.get("pass") is True,
            "handoff_pass": manifest.get("handoff_pass") is True,
            "rollback_ok": manifest.get("rollback", {}).get("ok") is True,
        },
        "progress": {
            "final_decision": progress.get("final_decision"),
            "provider_trigger": progress.get("provider_trigger") is True,
            "modem_trigger": progress.get("modem_trigger") is True,
            "rc1_progress": progress.get("rc1_progress") is True,
            "rc1_l0": progress.get("rc1_l0") is True,
            "rc1_link_failed": progress.get("rc1_link_failed") is True,
            "mhi_progress": progress.get("mhi_progress") is True,
            "wlfw_progress": progress.get("wlfw_progress") is True,
            "bdf_progress": progress.get("bdf_progress") is True,
            "fw_ready_progress": progress.get("fw_ready_progress") is True,
            "wlan0_present": progress.get("wlan0_present") is True,
            "connect_ready": progress.get("connect_ready") is True,
        },
        "writer": writer,
        "micro_labels": micro_labels,
        "micro_gpio": micro_gpio,
        "micro_interrupts": micro_interrupts,
        "micro_link_state": micro_link_state,
        "post_sample": post_sample,
        "dmesg": dmesg_result,
        "wlan0_stdout": {
            "contains_absent": "wlan0=absent" in wlan0,
            "raw_excerpt": wlan0.strip().splitlines()[-4:],
        },
    }

    required = [
        checks["handoff"]["pass"],
        checks["handoff"]["handoff_pass"],
        checks["handoff"]["rollback_ok"],
        checks["progress"]["final_decision"] == "rc1-ltssm-link-failed-no-l0",
        checks["progress"]["provider_trigger"],
        checks["progress"]["modem_trigger"],
        checks["progress"]["rc1_progress"],
        not checks["progress"]["rc1_l0"],
        checks["progress"]["rc1_link_failed"],
        not checks["progress"]["mhi_progress"],
        not checks["progress"]["wlfw_progress"],
        not checks["progress"]["bdf_progress"],
        not checks["progress"]["fw_ready_progress"],
        not checks["progress"]["wlan0_present"],
        not checks["progress"]["connect_ready"],
        checks["writer"]["ok"],
        checks["micro_labels"]["expected_present"],
        checks["micro_labels"]["count"] == len(EXPECTED_MICRO_LABELS),
        checks["micro_gpio"]["all_expected"],
        checks["micro_interrupts"]["all_present_zero"],
        checks["micro_link_state"]["all_unreadable"],
        checks["post_sample"]["present"],
        checks["post_sample"]["pcie1_gdsc_off_at_200ms"],
        checks["post_sample"]["pcie1_clocks_off_at_200ms"],
        checks["post_sample"]["pcie1_refgen_available_at_200ms"],
        checks["post_sample"]["expected_gpio_at_200ms"],
        checks["post_sample"]["gpio142_mdm_status_count"] == 0,
        checks["dmesg"]["has_link_failed"],
        not checks["dmesg"]["has_l0"],
        not checks["dmesg"]["has_mhi"],
        not checks["dmesg"]["has_wlfw"],
        not checks["dmesg"]["has_bdf"],
        not checks["dmesg"]["has_fw_ready"],
        not checks["dmesg"]["has_wlan0"],
        checks["wlan0_stdout"]["contains_absent"],
    ]
    pass_ok = all(bool(item) for item in required)
    if pass_ok:
        decision = "v1502-pre-l0-parity-confirms-rc1-link-fail-with-endpoint-lines-low"
        reason = "V1501 evidence confirms corrected RC1 enumerate reaches PHY/LTSSM but endpoint-side lines remain non-responsive and no L0/MHI/WLFW/wlan0 appears"
    else:
        decision = "v1502-pre-l0-parity-classifier-blocked"
        reason = "V1501 evidence did not satisfy the strict pre-L0 parity classifier"

    return {
        "cycle": "V1502",
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "v1501_dir": rel(v1501_dir),
        "checks": checks,
        "next_gate": {
            "primary": "V1503 dense pre-L0 full parity sampler or Android-good RC1 parity capture",
            "rationale": (
                "V1501 micro samples prove GPIO102/103/104/135/142 and IRQ state through 150ms, "
                "but focused GDSC/clock/regulator sampling is only captured at the 200ms post sample, "
                "which may be after link-failure cleanup."
            ),
            "keep_blocked": [
                "Wi-Fi HAL start",
                "scan/connect",
                "credential use",
                "DHCP/routes",
                "external ping",
                "PMIC/GPIO/GDSC direct write",
                "blind eSoC notify or BOOT_DONE spoof",
                "global PCI rescan",
                "platform bind/unbind",
            ],
        },
    }


def render_report(result: dict[str, Any]) -> str:
    checks = result["checks"]
    dmesg = checks["dmesg"]
    post = checks["post_sample"]
    micro_gpio = checks["micro_gpio"]
    micro_labels = checks["micro_labels"]
    lines = [
        "# Native Init V1502 Wi-Fi Pre-L0 Parity Classifier",
        "",
        "## Summary",
        "",
        "- Cycle: `V1502`",
        "- Type: host-only classifier over V1501 live handoff evidence",
        f"- Decision: `{result['decision']}`",
        f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
        f"- Reason: {result['reason']}",
        f"- Evidence: `{result['v1501_dir']}`",
        "",
        "## V1501 Handoff Result",
        "",
        f"- V1501 manifest decision: `{checks['handoff']['manifest_decision']}`",
        f"- handoff pass: `{checks['handoff']['handoff_pass']}`",
        f"- rollback ok: `{checks['handoff']['rollback_ok']}`",
        f"- progress decision: `{checks['progress']['final_decision']}`",
        f"- provider trigger: `{checks['progress']['provider_trigger']}`",
        f"- modem trigger: `{checks['progress']['modem_trigger']}`",
        f"- RC1 progress: `{checks['progress']['rc1_progress']}`",
        f"- RC1 L0: `{checks['progress']['rc1_l0']}`",
        f"- RC1 link failed: `{checks['progress']['rc1_link_failed']}`",
        f"- MHI/WLFW/BDF/FW-ready/wlan0: `{checks['progress']['mhi_progress']}/{checks['progress']['wlfw_progress']}/{checks['progress']['bdf_progress']}/{checks['progress']['fw_ready_progress']}/{checks['progress']['wlan0_present']}`",
        "",
        "## Corrected RC1 Enumerate",
        "",
        f"- writer summary ok: `{checks['writer']['ok']}`",
        f"- writer line: `{checks['writer']['line']}`",
        f"- LTSSM states: `{', '.join(dmesg['ltssm_states'])}`",
        f"- case after esoc0: `{dmesg['derived'].get('case_after_esoc0_ms')}` ms",
        f"- PHY ready after case: `{dmesg['derived'].get('phy_ready_after_case_ms')}` ms",
        f"- link failed after case: `{dmesg['derived'].get('link_failed_after_case_ms')}` ms",
        "",
        "## Micro Endpoint Samples",
        "",
        f"- expected labels present: `{micro_labels['expected_present']}`",
        f"- micro sample count: `{micro_labels['count']}`",
        f"- GPIO expected through micro window: `{micro_gpio['all_expected']}`",
        f"- GPIO104 wake / GPIO142 mdm-status IRQ counts stay zero: `{checks['micro_interrupts']['all_present_zero']}`",
        f"- PCIe1 link-state sysfs unreadable in every micro sample: `{checks['micro_link_state']['all_unreadable']}`",
        "",
        "| line | state through 0/1/2/5/10/20/50/100/150ms |",
        "|---|---|",
    ]
    for gpio, expected in EXPECTED_GPIO_STATES.items():
        stable = all(
            micro_gpio["by_label"][label][gpio].get("direction") == expected[0]
            and micro_gpio["by_label"][label][gpio].get("level") == expected[1]
            for label in EXPECTED_MICRO_LABELS
        )
        lines.append(f"| `{gpio}` | `{expected[0]} {expected[1]}` stable = `{stable}` |")
    lines.extend([
        "",
        "## Post Micro Full Sample",
        "",
        f"- post sample present: `{post['present']}`",
        f"- GPIO142 mdm-status IRQ count: `{post['gpio142_mdm_status_count']}`",
        f"- pcie_1_gdsc off at 200ms: `{post['pcie1_gdsc_off_at_200ms']}`",
        f"- PCIe1 focused clocks off at 200ms: `{post['pcie1_clocks_off_at_200ms']}`",
        f"- PCIe1 refgen available at 200ms: `{post['pcie1_refgen_available_at_200ms']}`",
        f"- focused GPIO expected at 200ms: `{post['expected_gpio_at_200ms']}`",
        "",
        "## Dmesg Classification",
        "",
        f"- link failed marker: `{dmesg['has_link_failed']}`",
        f"- L0 marker: `{dmesg['has_l0']}`",
        f"- MHI marker: `{dmesg['has_mhi']}`",
        f"- WLFW marker: `{dmesg['has_wlfw']}`",
        f"- BDF marker: `{dmesg['has_bdf']}`",
        f"- FW-ready marker: `{dmesg['has_fw_ready']}`",
        f"- wlan0 marker: `{dmesg['has_wlan0']}`",
        "",
        "## Key Lines",
        "",
    ])
    lines.extend(f"- `{line}`" for line in dmesg["key_lines"])
    lines.extend([
        "",
        "## Interpretation",
        "",
        "V1501 confirms the intended corrected RC1 enumerate path is no longer the blocker: the write succeeds, the RC1 PHY becomes ready, and LTSSM advances to `POLL_COMPLIANCE`. The failure remains pre-L0: no endpoint response reaches L0, GPIO142/MDM2AP interrupt count stays zero, and no MHI/WLFW/BDF/FW-ready/`wlan0` evidence appears.",
        "",
        "The GPIO micro samples cover 0/1/2/5/10/20/50/100/150ms after `case=11`. The focused regulator/clock evidence is currently captured in the 200ms post sample, likely after link failure cleanup, so it should not be over-read as proof of the exact clock/GDSC state during the first 150ms.",
        "",
        "## Safety Scope",
        "",
        "This classifier is host-only. It performs no device command, flash, reboot, partition write, Wi-Fi HAL start, scan/connect, credential handling, DHCP/routes, external ping, PMIC/GPIO/GDSC write, eSoC notify/`BOOT_DONE` spoof, global PCI rescan, or platform bind/unbind.",
        "",
        "## Next",
        "",
        "- V1503 should either add dense focused regulator/clock/GDSC sampling into each 0/1/2/5/10/20/50/100/150ms micro sample or capture an Android-good RC1 parity reference with the same fields.",
        "- Keep firmware/MHI/WLFW/scan/connect work parked until RC1 L0 and PCI enumeration exist.",
        "",
    ])
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--v1501-dir", type=Path, default=DEFAULT_V1501_DIR)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--write-report", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.v1501_dir.exists():
        raise SystemExit(f"missing V1501 evidence dir: {args.v1501_dir}")
    store = EvidenceStore(args.out_dir)
    result = classify(args.v1501_dir)
    report = render_report(result)
    store.write_json("manifest.json", result)
    store.write_text("summary.md", report)
    if args.write_report:
        write_private_text(args.report_path, report)
    print(json.dumps({"decision": result["decision"], "pass": result["pass"], "out_dir": rel(args.out_dir)}, indent=2))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

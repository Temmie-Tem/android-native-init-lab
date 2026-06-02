#!/usr/bin/env python3
"""V1662 host-only Android-good vs native power/clock/sequence diff classifier."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from a90harness.evidence import EvidenceStore, write_private_text


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ANDROID_MANIFEST = REPO_ROOT / "tmp/wifi/v1660-android-good-power-diff-reference/manifest.json"
DEFAULT_NATIVE_MANIFEST = REPO_ROOT / "tmp/wifi/v1661-native-natural-power-diff-handoff/manifest.json"
DEFAULT_OUT_DIR = REPO_ROOT / "tmp/wifi/v1662-android-native-power-diff-classifier"
DEFAULT_REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1662_ANDROID_NATIVE_POWER_DIFF_CLASSIFIER_2026-06-02.md"
)
ANDROID_EXPECTED_DECISION = "v1660-android-good-power-diff-reference-trace-opaque-pass"
NATIVE_EXPECTED_DECISION = "v1661-native-natural-power-diff-capture-pass"
LABELS = ("power-vote-gap", "sequence-gap", "full-power-parity-hardware-wall")
TARGET_CLOCKS = (
    "gcc_pcie_1_aux_clk_src",
    "gcc_pcie_1_aux_clk",
    "gcc_pcie_1_cfg_ahb_clk",
    "gcc_pcie_1_mstr_axi_clk",
    "gcc_pcie_1_slv_axi_clk",
    "gcc_pcie_1_clkref_clk",
    "gcc_pcie_1_slv_q2a_axi_clk",
    "gcc_pcie_phy_refgen_clk_src",
    "gcc_pcie1_phy_refgen_clk",
    "gcc_pcie_1_pipe_clk",
    "pcie_1_pipe_clk",
)
TARGET_REGULATOR_PATTERNS = (
    "pcie",
    "refgen",
    "mdm",
    "modem",
    "sdx",
    "wlan",
)


@dataclass
class ClockState:
    name: str
    max_enable: int = 0
    max_prepare: int = 0
    max_rate: int = 0
    samples: int = 0
    first_on: str = ""
    missing_samples: int = 0


@dataclass
class RegulatorState:
    name: str
    max_use: int = 0
    max_open: int = 0
    max_voltage_mv: int = 0
    samples: int = 0
    first_on: str = ""


@dataclass
class SubsysState:
    name: str
    samples: int = 0
    states: dict[str, int] = field(default_factory=dict)
    first_online: str = ""


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def android_evidence_dir(android_manifest: Path) -> Path:
    base = android_manifest.parent / "android-postfs-evidence" / "a90-v1660-android-power-diff-ref"
    return base


def native_window_path(native_manifest: Path) -> Path:
    return native_manifest.parent / "test-rc1-window-result.stdout.txt"


def context_from_begin(line: str, prefix: str) -> str:
    index = re.search(r"index=([0-9]+)", line)
    uptime = re.search(r"uptime=([0-9.]+)", line)
    elapsed = re.search(r"elapsed_ms=([0-9]+)", line)
    micro = re.search(r"micro_elapsed_ms=([0-9]+)", line)
    parts = [prefix]
    if index:
        parts.append(f"index={index.group(1)}")
    if uptime:
        parts.append(f"uptime={uptime.group(1)}")
    if elapsed:
        parts.append(f"elapsed_ms={elapsed.group(1)}")
    if micro:
        parts.append(f"micro_elapsed_ms={micro.group(1)}")
    return " ".join(parts)


def parse_clocks(text: str, begin_token: str, context_prefix: str) -> dict[str, ClockState]:
    states: dict[str, ClockState] = {}
    context = context_prefix
    begin_pattern = re.compile(rf"^{re.escape(begin_token)}_CLOCKS_BEGIN\b")
    clock_pattern = re.compile(
        r"^CLOCK\s+(\S+)\s+clk_enable_count=(\d+)\s+clk_prepare_count=(\d+)\s+clk_rate=(\d+)"
    )
    missing_pattern = re.compile(r"^CLOCK\s+(\S+)\s+missing$")
    for line in text.splitlines():
        stripped = line.strip()
        if begin_pattern.search(stripped):
            context = context_from_begin(stripped, context_prefix)
            continue
        match = clock_pattern.match(stripped)
        if match:
            name = match.group(1)
            enable = int(match.group(2))
            prepare = int(match.group(3))
            rate = int(match.group(4))
            state = states.setdefault(name, ClockState(name=name))
            state.samples += 1
            state.max_enable = max(state.max_enable, enable)
            state.max_prepare = max(state.max_prepare, prepare)
            state.max_rate = max(state.max_rate, rate)
            if not state.first_on and (enable > 0 or prepare > 0):
                state.first_on = context
            continue
        missing = missing_pattern.match(stripped)
        if missing:
            name = missing.group(1)
            state = states.setdefault(name, ClockState(name=name))
            state.missing_samples += 1
    return states


def normalize_regulator_line(line: str) -> str:
    match = re.search(r"match_[0-9]+=([^$]+)$", line)
    if match:
        return match.group(1).strip()
    return line.strip()


def parse_regulators(text: str, begin_token: str, context_prefix: str) -> dict[str, RegulatorState]:
    states: dict[str, RegulatorState] = {}
    context = context_prefix
    begin_pattern = re.compile(rf"^{re.escape(begin_token)}_REGULATOR_BEGIN\b")
    regulator_pattern = re.compile(
        r"^([A-Za-z0-9_.:-]+)\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)mV\b"
    )
    for line in text.splitlines():
        stripped = line.strip()
        if begin_pattern.search(stripped):
            context = context_from_begin(stripped, context_prefix)
            continue
        normalized = normalize_regulator_line(stripped)
        match = regulator_pattern.match(normalized)
        if not match:
            continue
        name = match.group(1)
        use = int(match.group(2))
        open_count = int(match.group(3))
        voltage = int(match.group(5))
        state = states.setdefault(name, RegulatorState(name=name))
        state.samples += 1
        state.max_use = max(state.max_use, use)
        state.max_open = max(state.max_open, open_count)
        state.max_voltage_mv = max(state.max_voltage_mv, voltage)
        if not state.first_on and use > 0:
            state.first_on = context
    return states


def parse_subsystems(text: str, begin_token: str, context_prefix: str) -> dict[str, SubsysState]:
    states: dict[str, SubsysState] = {}
    context = context_prefix
    begin_pattern = re.compile(rf"^{re.escape(begin_token)}_SUBSYS_BEGIN\b")
    subsys_pattern = re.compile(r"^SUBSYS\s+path=(\S+)\s+name=(\S+)\s+state=(\S+)")
    for line in text.splitlines():
        stripped = line.strip()
        if begin_pattern.search(stripped):
            context = context_from_begin(stripped, context_prefix)
            continue
        match = subsys_pattern.match(stripped)
        if not match:
            continue
        name = match.group(2)
        value = match.group(3)
        state = states.setdefault(name, SubsysState(name=name))
        state.samples += 1
        state.states[value] = state.states.get(value, 0) + 1
        if not state.first_online and value == "ONLINE":
            state.first_online = context
    return states


def target_regulator(name: str) -> bool:
    lower = name.lower()
    return any(pattern in lower for pattern in TARGET_REGULATOR_PATTERNS)


def clock_gaps(android: dict[str, ClockState], native: dict[str, ClockState]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    names = sorted(set(TARGET_CLOCKS) | set(android) | set(native))
    for name in names:
        if name not in TARGET_CLOCKS and "pcie" not in name and "refgen" not in name:
            continue
        a = android.get(name, ClockState(name=name))
        n = native.get(name, ClockState(name=name))
        if a.max_enable > n.max_enable or a.max_prepare > n.max_prepare or a.max_rate > n.max_rate:
            rows.append({
                "name": name,
                "android_max_enable": a.max_enable,
                "native_max_enable": n.max_enable,
                "android_max_prepare": a.max_prepare,
                "native_max_prepare": n.max_prepare,
                "android_max_rate": a.max_rate,
                "native_max_rate": n.max_rate,
                "android_first_on": a.first_on,
                "native_first_on": n.first_on,
                "kind": "clock",
            })
    return rows


def regulator_gaps(android: dict[str, RegulatorState], native: dict[str, RegulatorState]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    names = sorted(set(android) | set(native))
    for name in names:
        if not target_regulator(name):
            continue
        a = android.get(name, RegulatorState(name=name))
        n = native.get(name, RegulatorState(name=name))
        if a.max_use > n.max_use:
            rows.append({
                "name": name,
                "android_max_use": a.max_use,
                "native_max_use": n.max_use,
                "android_max_voltage_mv": a.max_voltage_mv,
                "native_max_voltage_mv": n.max_voltage_mv,
                "android_first_on": a.first_on,
                "native_first_on": n.first_on,
                "kind": "regulator",
            })
    return rows


def sequence_gaps(android: dict[str, SubsysState], native: dict[str, SubsysState]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for name in ("modem", "mss", "esoc0"):
        a = android.get(name, SubsysState(name=name))
        n = native.get(name, SubsysState(name=name))
        if a.first_online and not n.first_online:
            rows.append({
                "name": name,
                "android_first_online": a.first_online,
                "native_first_online": n.first_online,
                "android_states": a.states,
                "native_states": n.states,
            })
    return rows


def load_android_inputs(path: Path) -> dict[str, Any]:
    manifest = read_json(path)
    evidence = android_evidence_dir(path)
    return {
        "manifest": manifest,
        "evidence_dir": evidence,
        "regulator_text": read_text(evidence / "regulator-full.log"),
        "clock_text": read_text(evidence / "clock-targets.log"),
        "subsys_text": read_text(evidence / "subsys-sequence.log"),
        "dmesg_text": read_text(evidence / "dmesg-filtered.txt"),
    }


def load_native_inputs(path: Path) -> dict[str, Any]:
    manifest = read_json(path)
    window = native_window_path(path)
    text = read_text(window)
    return {
        "manifest": manifest,
        "window_path": window,
        "regulator_text": text,
        "clock_text": text,
        "subsys_text": text,
    }


def classify(args: argparse.Namespace) -> dict[str, Any]:
    android = load_android_inputs(args.android_manifest)
    native = load_native_inputs(args.native_manifest)
    android_clocks = parse_clocks(android["clock_text"], "A90_V1660", "android")
    native_clocks = parse_clocks(native["clock_text"], "A90_V1661", "native")
    android_regulators = parse_regulators(android["regulator_text"], "A90_V1660", "android")
    native_regulators = parse_regulators(native["regulator_text"], "A90_V1661", "native")
    android_subsys = parse_subsystems(android["subsys_text"], "A90_V1660", "android")
    native_subsys = parse_subsystems(native["subsys_text"], "A90_V1661", "native")

    c_gaps = clock_gaps(android_clocks, native_clocks)
    r_gaps = regulator_gaps(android_regulators, native_regulators)
    s_gaps = sequence_gaps(android_subsys, native_subsys)
    power_gaps = r_gaps + c_gaps
    if power_gaps:
        label = "power-vote-gap"
        reason = "Android-good enables AP-side pcie/refgen power or clock resources that native never enables in the natural powerup window."
    elif s_gaps:
        label = "sequence-gap"
        reason = "Power and clock snapshots are at parity, but Android brings a subsystem ONLINE that native does not."
    else:
        label = "full-power-parity-hardware-wall"
        reason = "No AP-side power, clock, or subsystem sequence gap remains visible in the captured windows."

    checks = {
        "android_manifest_present": bool(android["manifest"]),
        "native_manifest_present": bool(native["manifest"]),
        "android_v1660_pass": android["manifest"].get("decision") == ANDROID_EXPECTED_DECISION
        and android["manifest"].get("pass") is True,
        "native_v1661_pass": native["manifest"].get("decision") == NATIVE_EXPECTED_DECISION
        and native["manifest"].get("pass") is True,
        "android_lower_success": all(token in android["dmesg_text"] for token in ("FW ready", "wlan0")),
        "native_natural_path_silent": native["manifest"].get("natural_path_observation", {}).get("label")
        == "mdm2ap-silent-natural-path",
        "android_regulator_snapshots": bool(android_regulators),
        "native_regulator_snapshots": bool(native_regulators),
        "android_clock_snapshots": bool(android_clocks),
        "native_clock_snapshots": bool(native_clocks),
        "android_subsys_snapshots": bool(android_subsys),
        "native_subsys_snapshots": bool(native_subsys),
        "native_safety_zero": native["manifest"].get("power_diff_capture", {}).get("safety_zero") is True,
        "host_only_no_device_command": True,
        "no_autonomous_write_gate": True,
        "fixed_label": label in LABELS,
    }
    pass_ok = all(checks.values())
    decision = f"v1662-android-native-power-diff-{label}-pass" if pass_ok else "v1662-android-native-power-diff-review"
    result = {
        "cycle": "V1662",
        "type": "host-only Android-good vs native power/clock/sequence diff classifier",
        "decision": decision,
        "pass": pass_ok,
        "label": label,
        "reason": reason,
        "inputs": {
            "android_manifest": rel(args.android_manifest),
            "native_manifest": rel(args.native_manifest),
            "android_evidence_dir": rel(android["evidence_dir"]),
            "native_window": rel(native["window_path"]),
        },
        "checks": checks,
        "counts": {
            "android_clock_names": len(android_clocks),
            "native_clock_names": len(native_clocks),
            "android_regulator_names": len(android_regulators),
            "native_regulator_names": len(native_regulators),
            "android_subsys_names": len(android_subsys),
            "native_subsys_names": len(native_subsys),
            "power_gap_count": len(power_gaps),
            "clock_gap_count": len(c_gaps),
            "regulator_gap_count": len(r_gaps),
            "sequence_gap_count": len(s_gaps),
        },
        "power_gaps": power_gaps[:40],
        "clock_gaps": c_gaps[:30],
        "regulator_gaps": r_gaps[:30],
        "sequence_gaps": s_gaps,
        "next": {
            "stop": True,
            "no_autonomous_write": True,
            "if_power_vote_gap": "hand back for separately authorized bounded targeted AP-side power/clock gate",
            "if_sequence_gap": "plan a non-write route fix from Android ordering evidence",
            "if_full_power_parity_hardware_wall": "declare AP-side read-only parity wall; Wi-Fi remains Android-handoff-only on this route",
        },
    }
    return result


def render_gap_rows(rows: list[dict[str, Any]], keys: tuple[str, ...], *, limit: int = 12) -> list[str]:
    lines: list[str] = []
    for row in rows[:limit]:
        cells = [str(row.get(key, "")) for key in keys]
        lines.append("| " + " | ".join(cells) + " |")
    if not lines:
        lines.append("| none | | | | | | |")
    return lines


def render_report(result: dict[str, Any]) -> str:
    if result["label"] == "power-vote-gap":
        interpretation = [
            "The fixed contract labels this run as `power-vote-gap` because Android-good",
            "shows AP-side pcie1/refgen clock and pcie1 GDSC use windows while the native",
            "natural path keeps those resources at zero. This is a concrete AP-side",
            "resource differential. Per contract, this classifier stops here and does",
            "not enter a write gate.",
        ]
    elif result["label"] == "sequence-gap":
        interpretation = [
            "The fixed contract labels this run as `sequence-gap` because no AP-side",
            "power/clock vote gap is visible, but Android brings a subsystem ONLINE",
            "that native does not. This is a route/order candidate, not a write gate.",
        ]
    else:
        interpretation = [
            "The fixed contract labels this run as `full-power-parity-hardware-wall`",
            "because no AP-side power, clock, or subsystem sequence gap remains visible.",
            "The remaining blocker is below the observed AP-side surfaces.",
        ]
    lines = [
        "# Native Init V1662 Android-native Power Diff Classifier",
        "",
        "## Summary",
        "",
        "- Cycle: `V1662`",
        "- Type: host-only Android-good vs native power/clock/sequence diff",
        f"- Decision: `{result['decision']}`",
        f"- Result: {'PASS' if result['pass'] else 'REVIEW'}",
        f"- Label: `{result['label']}`",
        f"- Reason: {result['reason']}",
        "- Stop: `True`",
        "- Autonomous write gate: `False`",
        "",
        "## Inputs",
        "",
    ]
    for key, value in result["inputs"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend([
        "",
        "## Checks",
        "",
    ])
    for key, value in result["checks"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend([
        "",
        "## Counts",
        "",
    ])
    for key, value in result["counts"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend([
        "",
        "## Power Gap Evidence",
        "",
        "### Regulator Gaps",
        "",
        "| name | android_max_use | native_max_use | android_first_on | native_first_on | android_max_voltage_mv | native_max_voltage_mv |",
        "|---|---:|---:|---|---|---:|---:|",
    ])
    lines.extend(render_gap_rows(
        result["regulator_gaps"],
        ("name", "android_max_use", "native_max_use", "android_first_on", "native_first_on", "android_max_voltage_mv", "native_max_voltage_mv"),
    ))
    lines.extend([
        "",
        "### Clock Gaps",
        "",
        "| name | android_max_enable | native_max_enable | android_max_prepare | native_max_prepare | android_max_rate | native_max_rate |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ])
    lines.extend(render_gap_rows(
        result["clock_gaps"],
        ("name", "android_max_enable", "native_max_enable", "android_max_prepare", "native_max_prepare", "android_max_rate", "native_max_rate"),
    ))
    lines.extend([
        "",
        "## Sequence Gap Evidence",
        "",
        "| name | android_first_online | native_first_online | android_states | native_states |",
        "|---|---|---|---|---|",
    ])
    if result["sequence_gaps"]:
        for row in result["sequence_gaps"]:
            lines.append(
                f"| {row['name']} | {row['android_first_online']} | {row['native_first_online']} | "
                f"{json.dumps(row['android_states'], sort_keys=True)} | {json.dumps(row['native_states'], sort_keys=True)} |"
            )
    else:
        lines.append("| none | | | | |")
    lines.extend([
        "",
        "## Interpretation",
        "",
        *interpretation,
        "",
        "## Safety Scope",
        "",
        "V1662 is host-only. It performs no device command, reboot, flash, partition",
        "write, PMIC/GPIO/GDSC/regulator write, forced RC1/case write, fake ONLINE",
        "or system-info spoof, eSoC notify/`BOOT_DONE`, PCI rescan, platform",
        "bind/unbind, Wi-Fi HAL start, scan/connect, credentials, DHCP/routes, or",
        "external ping.",
        "",
        "## Next",
        "",
        "- Stop this read-only diff loop.",
        "- If proceeding, request explicit approval for a separate bounded targeted",
        "  AP-side pcie1 power/clock vote gate based on the resources above.",
        "",
    ])
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--android-manifest", type=Path, default=DEFAULT_ANDROID_MANIFEST)
    parser.add_argument("--native-manifest", type=Path, default=DEFAULT_NATIVE_MANIFEST)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT_PATH)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    store = EvidenceStore(args.out_dir)
    result = classify(args)
    store.write_json("manifest.json", result)
    report = render_report(result)
    write_private_text(args.out_dir / "summary.md", report)
    write_private_text(args.report_path, report)
    print(json.dumps({
        "decision": result["decision"],
        "pass": result["pass"],
        "label": result["label"],
        "power_gap_count": result["counts"]["power_gap_count"],
        "sequence_gap_count": result["counts"]["sequence_gap_count"],
        "out_dir": rel(args.out_dir),
        "report": rel(args.report_path),
    }, indent=2))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

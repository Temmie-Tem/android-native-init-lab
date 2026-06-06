#!/usr/bin/env python3
"""V1559 host-only Android/native pre-endpoint ordering classifier.

V1558 selected the next gate: compare Android-good pre-endpoint/pre-IRQ
ordering against native provider-driven endpoint silence.  V1559 consumes
existing V1552/V1555/V1557 evidence only and extracts the earliest comparable
event times.  It does not run the device.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1559-android-pre-endpoint-order-classifier")
DEFAULT_REPORT_PATH = Path(
    "docs/reports/NATIVE_INIT_V1559_ANDROID_PRE_ENDPOINT_ORDER_CLASSIFIER_2026-06-02.md"
)
LATEST_POINTER = Path("tmp/wifi/latest-v1559-android-pre-endpoint-order-classifier.txt")

V1552_MANIFEST = Path("tmp/wifi/v1552-rc1-endpoint-response-tracefs-live/manifest.json")
V1555_MANIFEST = Path("tmp/wifi/v1555-android-good-minimal-trace-reference/manifest.json")
V1557_MANIFEST = Path("tmp/wifi/v1557-native-endpoint-long-hold-handoff/manifest.json")
V1555_BASE = Path(
    "tmp/wifi/v1555-android-good-minimal-trace-reference"
    "/android-postfs-evidence/a90-v1555-android-min-trace-ref"
)
V1552_NATIVE = Path("tmp/wifi/v1552-rc1-endpoint-response-tracefs-live/native")


DMESG_TIME_RE = re.compile(r"\[\s*(?P<time>\d+\.\d+)\]")
TRACE_TIME_RE = re.compile(r"\s(?P<time>\d+\.\d+):\s")
SAMPLE_BEGIN_RE = re.compile(r"A90_V1555_SAMPLE_BEGIN index=(?P<index>\d+) uptime=(?P<uptime>\d+\.\d+)")
IRQ_LINE_RE = re.compile(r"^\s*(?P<irq>\d+):(?P<count_text>.*?)(?P<label>msm_pcie_wake|mdm status|mdm errfatal)\s*$")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def rel(path: Path) -> str:
    resolved = repo_path(path)
    try:
        return str(resolved.relative_to(repo_path(".")))
    except ValueError:
        return str(resolved)


def read_text(path: Path) -> str:
    resolved = repo_path(path)
    return resolved.read_text(encoding="utf-8", errors="replace") if resolved.exists() else ""


def read_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {}
    try:
        data = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def first_dmesg_time(text: str, *needles: str) -> float | None:
    for line in text.splitlines():
        if all(needle in line for needle in needles):
            match = DMESG_TIME_RE.search(line)
            if match:
                return float(match.group("time"))
    return None


def first_trace_time(text: str, *needles: str) -> float | None:
    for line in text.splitlines():
        if all(needle in line for needle in needles):
            match = TRACE_TIME_RE.search(line)
            if match:
                return float(match.group("time"))
    return None


def first_sample_irq_uptime(text: str, label: str) -> float | None:
    current_uptime: float | None = None
    for line in text.splitlines():
        sample_match = SAMPLE_BEGIN_RE.search(line)
        if sample_match:
            current_uptime = float(sample_match.group("uptime"))
            continue
        irq_match = IRQ_LINE_RE.match(line)
        if not irq_match or label not in irq_match.group("label"):
            continue
        counts = [int(value) for value in re.findall(r"\b\d+\b", irq_match.group("count_text"))[:8]]
        if sum(counts) > 0:
            return current_uptime
    return None


def get_nested(data: dict[str, Any], *keys: str) -> Any:
    value: Any = data
    for key in keys:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value


def build_android_events(v1555: dict[str, Any]) -> dict[str, Any]:
    dmesg = read_text(V1555_BASE / "dmesg-filtered.txt")
    trace = read_text(V1555_BASE / "tracefs-targets.txt")
    samples = read_text(V1555_BASE / "samples.log")
    analysis = get_nested(v1555, "context", "analysis") or {}
    dmesg_analysis = analysis.get("dmesg") or {}
    trace_analysis = analysis.get("tracefs_analysis") or {}
    first_times = trace_analysis.get("first_times") or {}
    return {
        "esoc0_get_dmesg": dmesg_analysis.get("esoc0_time") or first_dmesg_time(dmesg, "__subsystem_get: esoc0"),
        "wlfw_start_dmesg": dmesg_analysis.get("wlfw_time") or first_dmesg_time(dmesg, "wlfw_start"),
        "bdf_dmesg": dmesg_analysis.get("bdf_time") or first_dmesg_time(dmesg, "BDF file"),
        "fw_ready_dmesg": dmesg_analysis.get("fw_ready_time") or first_dmesg_time(dmesg, "FW"),
        "wlan0_dmesg": dmesg_analysis.get("wlan0_time") or first_dmesg_time(dmesg, "wlan0"),
        "pcie_l0_dmesg": dmesg_analysis.get("pcie_l0_time") or first_dmesg_time(dmesg, "LTSSM_L0"),
        "gpio135_trace": first_times.get("gpio135") or first_trace_time(trace, "gpio_value: 135", "set 1"),
        "gpio102_set0_trace": first_trace_time(trace, "gpio_value: 102", "set 0"),
        "gpio102_set1_trace": first_trace_time(trace, "gpio_value: 102", "set 1"),
        "irq252_trace": first_trace_time(trace, "irq_handler_entry: irq=252"),
        "irq290_trace": first_trace_time(trace, "irq_handler_entry: irq=290"),
        "gpio142_get1_trace": first_trace_time(trace, "gpio_value: 142", "get 1"),
        "irq252_sample_uptime": first_sample_irq_uptime(samples, "msm_pcie_wake"),
        "irq290_sample_uptime": first_sample_irq_uptime(samples, "mdm status"),
        "sample_count": analysis.get("sample_count"),
    }


def build_native_events(v1552: dict[str, Any], v1557: dict[str, Any]) -> dict[str, Any]:
    trace = read_text(V1552_NATIVE / "tracefs-dump-targets.txt")
    dmesg = read_text(V1552_NATIVE / "dmesg-tail.txt")
    analysis = v1552.get("analysis") or {}
    target_counts = analysis.get("target_counts") or {}
    irq_delta = analysis.get("interrupt_delta") or {}
    progress = v1557.get("progress") or {}
    return {
        "gpio102_set0_trace": first_trace_time(trace, "gpio_value: 102", "set 0"),
        "gpio102_set1_trace": first_trace_time(trace, "gpio_value: 102", "set 1"),
        "pcie1_gdsc_enable_trace": first_trace_time(trace, "regulator_enable: name=pcie_1_gdsc"),
        "pcie1_clkref_enable_trace": first_trace_time(trace, "clk_enable: gcc_pcie_1_clkref_clk"),
        "pcie1_pipe_enable_trace": first_trace_time(trace, "clk_enable: gcc_pcie_1_pipe_clk"),
        "link_fail_dmesg": first_dmesg_time(dmesg, "PCIe RC1 link initialization failed"),
        "l0_seen": bool(analysis.get("l0_seen")),
        "mhi_seen": bool(analysis.get("mhi_seen")),
        "target_counts": target_counts,
        "interrupt_delta": irq_delta,
        "v1557_provider_trigger": bool(progress.get("provider_trigger")),
        "v1557_modem_trigger": bool(progress.get("modem_trigger")),
        "v1557_rc1_progress": bool(progress.get("rc1_progress")),
        "v1557_rc1_l0": bool(progress.get("rc1_l0")),
        "v1557_endpoint_positive": bool(progress.get("endpoint_positive")),
    }


def fmt_time(value: Any) -> str:
    return "missing" if value is None else f"{float(value):.6f}"


def delta(after: Any, before: Any) -> str:
    if after is None or before is None:
        return "n/a"
    return f"{float(after) - float(before):+.6f}s"


def classify() -> dict[str, Any]:
    v1552 = read_json(V1552_MANIFEST)
    v1555 = read_json(V1555_MANIFEST)
    v1557 = read_json(V1557_MANIFEST)
    android = build_android_events(v1555)
    native = build_native_events(v1552, v1557)
    android_ap2mdm_before_bdf = (
        android["gpio135_trace"] is not None
        and android["bdf_dmesg"] is not None
        and android["gpio135_trace"] < android["bdf_dmesg"]
    )
    android_endpoint_late_vs_wlan0 = (
        android["irq252_trace"] is not None
        and android["wlan0_dmesg"] is not None
        and android["irq252_trace"] > android["wlan0_dmesg"]
    )
    native_ap_side_ready = all(
        native[key] is not None
        for key in ("pcie1_gdsc_enable_trace", "pcie1_clkref_enable_trace", "pcie1_pipe_enable_trace", "gpio102_set1_trace")
    )
    native_endpoint_silent = (
        not native["v1557_endpoint_positive"]
        and not native["v1557_rc1_l0"]
        and (native["target_counts"].get("gpio104", 0) == 0)
        and (native["target_counts"].get("gpio142", 0) == 0)
        and (native["target_counts"].get("gpio135", 0) == 0)
        and (native["interrupt_delta"].get("pcie_wake", 0) == 0)
        and (native["interrupt_delta"].get("mdm_status", 0) == 0)
    )
    prerequisites_ok = (
        v1552.get("pass") is True
        and v1555.get("pass") is True
        and v1557.get("pass") is True
        and android_ap2mdm_before_bdf
        and native_ap_side_ready
        and native_endpoint_silent
    )
    decision = (
        "v1559-ap2mdm-before-bdf-gap-endpoint-order-caveat"
        if prerequisites_ok
        else "v1559-pre-endpoint-order-inputs-incomplete-review"
    )
    reason = (
        "Android-good shows GPIO135/AP2MDM before BDF while native has AP-side RC1 power/refclk/PERST but no AP2MDM/endpoint response; retained Android IRQ/L0 evidence is late and must not be treated as first-L0 ordering"
        if prerequisites_ok
        else "existing evidence does not fully prove Android AP2MDM-before-BDF plus native AP-side-ready endpoint silence"
    )
    comparison_rows = [
        ["esoc0/provider trigger", fmt_time(android["esoc0_get_dmesg"]), f"provider={native['v1557_provider_trigger']} modem={native['v1557_modem_trigger']}", "both routes reach a lower trigger"],
        ["GPIO135/AP2MDM", fmt_time(android["gpio135_trace"]), native["target_counts"].get("gpio135", 0), f"Android GPIO135 occurs {delta(android['gpio135_trace'], android['esoc0_get_dmesg'])} from esoc0 and {delta(android['gpio135_trace'], android['bdf_dmesg'])} before BDF; native count stays zero"],
        ["GPIO102/PERST", f"{fmt_time(android['gpio102_set0_trace'])}/{fmt_time(android['gpio102_set1_trace'])}", f"{fmt_time(native['gpio102_set0_trace'])}/{fmt_time(native['gpio102_set1_trace'])}", "both can toggle PERST-like GPIO102"],
        ["pcie1 AP-side power/refclk/pipe", "not in V1555 minimal trace", f"{fmt_time(native['pcie1_gdsc_enable_trace'])}/{fmt_time(native['pcie1_clkref_enable_trace'])}/{fmt_time(native['pcie1_pipe_enable_trace'])}", "native AP-side pcie1 prerequisites are present"],
        ["GPIO104/IRQ252", f"trace={fmt_time(android['irq252_trace'])} sample={fmt_time(android['irq252_sample_uptime'])}", f"delta={native['interrupt_delta'].get('pcie_wake', 0)} count={native['target_counts'].get('gpio104', 0)}", f"Android retained IRQ252 is {delta(android['irq252_trace'], android['wlan0_dmesg'])} after wlan0; native stays zero"],
        ["GPIO142/IRQ290", f"trace={fmt_time(android['irq290_trace'])} sample={fmt_time(android['irq290_sample_uptime'])}", f"delta={native['interrupt_delta'].get('mdm_status', 0)} count={native['target_counts'].get('gpio142', 0)}", f"Android retained IRQ290 is {delta(android['irq290_trace'], android['wlan0_dmesg'])} after wlan0; native stays zero"],
        ["lower Wi-Fi", f"WLFW={fmt_time(android['wlfw_start_dmesg'])} BDF={fmt_time(android['bdf_dmesg'])} FW={fmt_time(android['fw_ready_dmesg'])} wlan0={fmt_time(android['wlan0_dmesg'])}", f"RC1={native['v1557_rc1_progress']} L0={native['v1557_rc1_l0']} MHI={native['mhi_seen']}", "firmware/MHI/WLFW remains downstream for native until endpoint response exists"],
    ]
    next_gate = {
        "recommended_cycle": "V1560",
        "type": "host-only/source-build or bounded read-only reference, no connect-side actions",
        "focus": "AP2MDM assertion/effective-level gap before BDF rather than late retained IRQ252/IRQ290 ordering",
        "requirements": [
            "treat Android GPIO135/AP2MDM before BDF as the earliest currently proven discriminating signal",
            "do not use V1555 late IRQ252/IRQ290/L0 excerpts as first-L0 proof",
            "explain why native provider/RC1 path does not produce GPIO135/AP2MDM or endpoint wake/status despite AP-side pcie1 power/refclk/PERST",
            "keep Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, PMIC/GPIO/GDSC direct writes, eSoC notify/BOOT_DONE spoof, global PCI rescan, and platform bind/unbind blocked",
        ],
    }
    return {
        "decision": decision,
        "pass": prerequisites_ok,
        "reason": reason,
        "android": android,
        "native": native,
        "derived": {
            "android_ap2mdm_before_bdf": android_ap2mdm_before_bdf,
            "android_endpoint_late_vs_wlan0": android_endpoint_late_vs_wlan0,
            "native_ap_side_ready": native_ap_side_ready,
            "native_endpoint_silent": native_endpoint_silent,
        },
        "comparison_rows": comparison_rows,
        "next_gate": next_gate,
    }


def render_report(manifest: dict[str, Any]) -> str:
    analysis = manifest["analysis"]
    return "\n".join(
        [
            "# Native Init V1559 Android Pre-Endpoint Order Classifier",
            "",
            "## Summary",
            "",
            "- Cycle: `V1559`",
            "- Type: host-only existing-evidence ordering classifier",
            f"- Decision: `{manifest['decision']}`",
            f"- Result: `{'PASS' if manifest['pass'] else 'FAIL'}`",
            f"- Reason: {manifest['reason']}",
            f"- Evidence: `{manifest['out_dir']}`",
            "",
            "## Inputs",
            "",
            markdown_table(
                ["input", "path"],
                [
                    ["native_v1552", rel(V1552_MANIFEST)],
                    ["android_v1555", rel(V1555_MANIFEST)],
                    ["native_v1557", rel(V1557_MANIFEST)],
                ],
            ),
            "",
            "## Comparison",
            "",
            markdown_table(["signal", "android_v1555", "native", "interpretation"], analysis["comparison_rows"]),
            "",
            "## Derived Checks",
            "",
            markdown_table(
                ["check", "value"],
                [[key, value] for key, value in analysis["derived"].items()],
            ),
            "",
            "## Interpretation",
            "",
            "Existing evidence can order one important Android-good signal: GPIO135/AP2MDM is asserted after the esoc0 trigger and before BDF download. Native evidence already proves AP-side pcie1 power/refclk/pipe/PERST activity, but GPIO135/AP2MDM, GPIO104/WAKE, GPIO142/MDM2AP, IRQ252, IRQ290, L0, MHI, WLFW, BDF, FW-ready, and `wlan0` remain absent.",
            "",
            "Existing V1555 evidence cannot prove that retained IRQ252/IRQ290/L0 are the first lower-Wi-Fi-enabling events, because those excerpts occur after the first retained `wlan0` lines. They are still useful positive endpoint proof, but not first-L0 ordering proof.",
            "",
            "## Next Gate",
            "",
            f"- Recommended cycle: `{analysis['next_gate']['recommended_cycle']}`",
            f"- Type: {analysis['next_gate']['type']}",
            f"- Focus: {analysis['next_gate']['focus']}",
            "",
            "### Requirements",
            "",
            *[f"- {item}" for item in analysis["next_gate"]["requirements"]],
            "",
            "## Safety Scope",
            "",
            "This classifier is host-only. It performs no device command, flash, reboot, partition write, Wi-Fi HAL start, scan/connect, credential handling, DHCP/routes, external ping, PMIC/GPIO/GDSC write, eSoC notify/BOOT_DONE spoof, pci-msm debugfs write, global PCI rescan, or platform bind/unbind.",
            "",
        ]
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--write-report", action="store_true", default=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    analysis = classify()
    manifest = {
        "cycle": "V1559",
        "generated_at": now_iso(),
        "decision": analysis["decision"],
        "pass": analysis["pass"],
        "reason": analysis["reason"],
        "host": collect_host_metadata(),
        "input_paths": {
            "native_v1552": rel(V1552_MANIFEST),
            "android_v1555": rel(V1555_MANIFEST),
            "native_v1557": rel(V1557_MANIFEST),
        },
        "analysis": analysis,
        "out_dir": rel(store.run_dir),
        "device_commands_executed": False,
        "device_mutations": False,
    }
    store.write_json("manifest.json", manifest)
    report = render_report(manifest)
    store.write_text("summary.md", report)
    if args.write_report:
        write_private_text(repo_path(args.report_path), report)
    write_private_text(repo_path(LATEST_POINTER), rel(store.run_dir) + "\n")
    print(json.dumps({"decision": manifest["decision"], "pass": manifest["pass"]}, indent=2))
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""V1466 host-only classifier for the provider PON-to-AP2MDM branch."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from a90harness.evidence import EvidenceStore, write_private_text


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_V1465_MANIFEST = REPO_ROOT / "tmp" / "wifi" / "v1465-provider-tracepoint-classifier" / "manifest.json"
DEFAULT_V1464_DIR = REPO_ROOT / "tmp" / "wifi" / "v1464-wifi-test-boot-exact-provider-tracepoint-handoff"
DEFAULT_V1318_REPORT = REPO_ROOT / "docs" / "reports" / "NATIVE_INIT_V1318_CRITICAL_LOWER_TRACE_COLLECTOR_2026-05-31.md"
DEFAULT_STATIC_REPORT = REPO_ROOT / "docs" / "reports" / "ESOC_PROVIDER_STATIC_ANALYSIS_2026-06-01.md"
DEFAULT_PROVIDER_RESEARCH = REPO_ROOT / "docs" / "overview" / "MDM3_ESOC_SDX50M_BRINGUP_RESEARCH_2026-05-25.md"
DEFAULT_PID1_SOURCE = REPO_ROOT / "stage3" / "linux_init" / "v724" / "90_main.inc.c"
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1466-provider-ap2mdm-branch-classifier"
DEFAULT_REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1466_PROVIDER_AP2MDM_BRANCH_CLASSIFIER_2026-06-01.md"
)


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


def extract_int(pattern: str, text: str) -> int:
    match = re.search(pattern, text)
    if not match:
        return 0
    return int(match.group(1))


def parse_trace_times(window_text: str) -> dict[str, Any]:
    times: dict[str, list[float]] = {"1270_set0": [], "1270_set1": [], "135": [], "142": [], "141_set0": []}
    for line in window_text.splitlines():
        time_match = re.search(r"\s(?P<time>\d+\.\d+): gpio_(?:value|direction): (?P<gpio>\d+) (?P<op>.*)$", line)
        if not time_match:
            continue
        ts = float(time_match.group("time"))
        gpio = time_match.group("gpio")
        op = time_match.group("op")
        if gpio == "1270" and "set 0" in op:
            times["1270_set0"].append(ts)
        elif gpio == "1270" and "set 1" in op:
            times["1270_set1"].append(ts)
        elif gpio == "135":
            times["135"].append(ts)
        elif gpio == "142":
            times["142"].append(ts)
        elif gpio == "141" and "set 0" in op:
            times["141_set0"].append(ts)
    pon_low = min(times["1270_set0"]) if times["1270_set0"] else None
    pon_high = min(times["1270_set1"]) if times["1270_set1"] else None
    return {
        "times": times,
        "pon_low_first": pon_low,
        "pon_high_first": pon_high,
        "pon_low_to_high_ms": round((pon_high - pon_low) * 1000.0, 3) if pon_low is not None and pon_high is not None else None,
        "gpio135_event_count": len(times["135"]),
        "gpio142_event_count": len(times["142"]),
    }


def classify(args: argparse.Namespace) -> dict[str, Any]:
    v1465 = read_json(args.v1465_manifest)
    window_text = read_text(args.v1464_dir / "test-rc1-window-result.stdout.txt")
    log_text = read_text(args.v1464_dir / "test-v1393-log.stdout.txt")
    summary_text = read_text(args.v1464_dir / "test-v1393-summary.stdout.txt")
    v1318_report = read_text(args.v1318_report)
    static_report = read_text(args.static_report)
    provider_research = read_text(args.provider_research)
    pid1_source = read_text(args.pid1_source)

    trace_times = parse_trace_times(window_text)
    v1318_gpio135_high_count = extract_int(r"\| GPIO135 high count \| (\d+) \|", v1318_report)
    v1318_gpio142_lines = extract_int(r"\| GPIO1270 / GPIO135 / GPIO142 lines \| \d+ / \d+ / (\d+) \|", v1318_report)
    v1318_has_esoc_pil_notif = "pil_notif" in v1318_report and "fw=esoc0" in v1318_report
    v1318_has_pon_trace = "gpio_value: 1270 set 0" in v1318_report and "gpio_value: 1270 set 1" in v1318_report

    source_model_expects_ap2mdm = (
        "gpio_direction_output(MDM_GPIO(mdm, AP2MDM_STATUS), 1)" in provider_research
        and "msleep(150)" in provider_research
        and "msleep(200)" in provider_research
    )
    static_provider_is_gpio_only = (
        "GPIO/ioctl handshake" in static_report
        and "Zero" in static_report
        and "PCIe/MHI/GDSC/regulator" in static_report
    )
    pid1_tracepoint_lacks_pil = "msm_pil_event" not in pid1_source and "pil_notif" not in pid1_source
    v1464_tracepoint_armed = (
        "provider tracepoint arm trace_off_rc=0 clear_rc=0 gpio_value_rc=0 gpio_direction_rc=0 trace_on_rc=0"
        in log_text
    )
    v1464_summary_still_armed = "state=armed" in summary_text

    v1464_pon_seen = bool(trace_times["times"]["1270_set0"] and trace_times["times"]["1270_set1"])
    v1464_ap2mdm_absent = trace_times["gpio135_event_count"] == 0 and bool(v1465.get("window", {}).get("gpio135_trace_absent"))
    v1464_mdm2ap_absent = trace_times["gpio142_event_count"] == 0 and bool(v1465.get("window", {}).get("gpio142_trace_absent"))
    v1464_no_downstream = not bool(v1465.get("progress", {}).get("downstream_progress"))
    v1464_wchan_power_path = bool(v1465.get("window", {}).get("wchan_soft_reset_seen")) and bool(
        v1465.get("window", {}).get("wchan_powerup_seen")
    )

    pass_condition = (
        v1465.get("decision") == "v1465-pon-toggles-ap2mdm-absent-no-downstream"
        and bool(v1465.get("pass"))
        and v1464_tracepoint_armed
        and v1464_pon_seen
        and v1464_ap2mdm_absent
        and v1464_mdm2ap_absent
        and v1464_no_downstream
        and v1464_wchan_power_path
        and v1318_gpio135_high_count > 0
        and v1318_gpio142_lines == 0
        and v1318_has_esoc_pil_notif
        and v1318_has_pon_trace
        and source_model_expects_ap2mdm
        and static_provider_is_gpio_only
        and pid1_tracepoint_lacks_pil
    )

    if pass_condition:
        decision = "v1466-ap2mdm-branch-divergence-needs-pil-parity-test-boot"
        reason = (
            "V1464 proves the test boot reaches the PON side but does not observe AP2MDM, while "
            "V1318 proves an earlier native PM path emitted esoc0 PIL notifications and AP2MDM high; "
            "the current test boot lacks PIL tracepoint parity, so the next safe gate is source/build-only."
        )
        next_gate = "V1467 source/build-only exact-provider PIL+GPIO tracepoint test boot"
    else:
        decision = "v1466-provider-ap2mdm-branch-needs-review"
        reason = "The V1464/V1318/static source evidence did not satisfy the AP2MDM branch divergence contract."
        next_gate = "review V1464/V1318 evidence before any new test boot"

    return {
        "cycle": "V1466",
        "decision": decision,
        "pass": pass_condition,
        "reason": reason,
        "inputs": {
            "v1465_manifest": rel(args.v1465_manifest),
            "v1464_dir": rel(args.v1464_dir),
            "v1318_report": rel(args.v1318_report),
            "static_report": rel(args.static_report),
            "provider_research": rel(args.provider_research),
            "pid1_source": rel(args.pid1_source),
        },
        "v1464": {
            "tracepoint_armed": v1464_tracepoint_armed,
            "summary_still_armed_when_collected": v1464_summary_still_armed,
            "pon_seen": v1464_pon_seen,
            "pon_low_to_high_ms": trace_times["pon_low_to_high_ms"],
            "gpio135_event_count": trace_times["gpio135_event_count"],
            "gpio142_event_count": trace_times["gpio142_event_count"],
            "ap2mdm_absent": v1464_ap2mdm_absent,
            "mdm2ap_absent": v1464_mdm2ap_absent,
            "no_downstream": v1464_no_downstream,
            "wchan_power_path": v1464_wchan_power_path,
        },
        "v1318": {
            "gpio135_high_count": v1318_gpio135_high_count,
            "gpio142_lines": v1318_gpio142_lines,
            "esoc_pil_notif_seen": v1318_has_esoc_pil_notif,
            "pon_trace_seen": v1318_has_pon_trace,
        },
        "source": {
            "source_model_expects_ap2mdm_after_pon": source_model_expects_ap2mdm,
            "static_provider_is_gpio_only": static_provider_is_gpio_only,
            "pid1_tracepoint_lacks_pil_notif": pid1_tracepoint_lacks_pil,
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
    v1464 = result["v1464"]
    v1318 = result["v1318"]
    source = result["source"]
    return "\n".join([
        "# Native Init V1466 Provider AP2MDM Branch Classifier",
        "",
        "## Summary",
        "",
        "- Cycle: `V1466`",
        "- Type: host-only classifier over V1464/V1465, V1318, and source/static provider evidence",
        f"- Decision: `{result['decision']}`",
        f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
        f"- Reason: {result['reason']}",
        "",
        "## Evidence Inputs",
        "",
        f"- V1465 manifest: `{result['inputs']['v1465_manifest']}`",
        f"- V1464 evidence: `{result['inputs']['v1464_dir']}`",
        f"- V1318 report: `{result['inputs']['v1318_report']}`",
        f"- Static provider analysis: `{result['inputs']['static_report']}`",
        f"- Provider research note: `{result['inputs']['provider_research']}`",
        f"- PID1 source: `{result['inputs']['pid1_source']}`",
        "",
        "## V1464 Exact-Provider Test Boot",
        "",
        f"- tracepoint armed: `{v1464['tracepoint_armed']}`",
        f"- summary still armed when collected: `{v1464['summary_still_armed_when_collected']}`",
        f"- PON low-high seen: `{v1464['pon_seen']}`",
        f"- PON low-to-high interval ms: `{v1464['pon_low_to_high_ms']}`",
        f"- GPIO135/AP2MDM event count: `{v1464['gpio135_event_count']}`",
        f"- GPIO142/MDM2AP event count: `{v1464['gpio142_event_count']}`",
        f"- AP2MDM absent: `{v1464['ap2mdm_absent']}`",
        f"- MDM2AP absent: `{v1464['mdm2ap_absent']}`",
        f"- downstream progress absent: `{v1464['no_downstream']}`",
        f"- provider wchan path seen: `{v1464['wchan_power_path']}`",
        "",
        "## V1318 Reference Evidence",
        "",
        f"- GPIO135 high count: `{v1318['gpio135_high_count']}`",
        f"- GPIO142 line count: `{v1318['gpio142_lines']}`",
        f"- esoc0 PIL notification seen: `{v1318['esoc_pil_notif_seen']}`",
        f"- PON trace seen: `{v1318['pon_trace_seen']}`",
        "",
        "## Source/Static Contract",
        "",
        f"- source expects AP2MDM after PON: `{source['source_model_expects_ap2mdm_after_pon']}`",
        f"- provider is GPIO/ioctl only: `{source['static_provider_is_gpio_only']}`",
        f"- current PID1 tracepoint sampler lacks PIL notification parity: `{source['pid1_tracepoint_lacks_pil_notif']}`",
        "",
        "## Interpretation",
        "",
        "V1464 is not yet a safe basis to jump to Wi-Fi HAL, scan/connect, or network",
        "testing. It proves the test boot enters the provider/PON side but does not",
        "prove the same lower tracepoint contract as V1318, because the V1462 PID1",
        "sampler only arms GPIO tracepoints. V1318 saw `fw=esoc0` PIL notifications",
        "and then GPIO135/AP2MDM high, while V1464 saw PON/errfatal activity but no",
        "GPIO135 event through the current exact-provider window.",
        "",
        "The next aligned step is not a lower write or another blind live retry. It is",
        "a source/build-only test boot update that adds `msm_pil_event:pil_notif`",
        "parity to the exact-provider GPIO tracepoint sampler and records whether the",
        "PIL notification branch appears before expecting AP2MDM.",
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
    parser.add_argument("--v1465-manifest", type=Path, default=DEFAULT_V1465_MANIFEST)
    parser.add_argument("--v1464-dir", type=Path, default=DEFAULT_V1464_DIR)
    parser.add_argument("--v1318-report", type=Path, default=DEFAULT_V1318_REPORT)
    parser.add_argument("--static-report", type=Path, default=DEFAULT_STATIC_REPORT)
    parser.add_argument("--provider-research", type=Path, default=DEFAULT_PROVIDER_RESEARCH)
    parser.add_argument("--pid1-source", type=Path, default=DEFAULT_PID1_SOURCE)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--write-report", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    store = EvidenceStore(args.out_dir)
    result = classify(args)
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

#!/usr/bin/env python3
"""V1518 host-only classifier for V1517 critical-source pre-L0 evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from a90harness.evidence import EvidenceStore, write_private_text

import native_wifi_source_timing_classifier_v1514 as base


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_V1517_DIR = REPO_ROOT / "tmp" / "wifi" / "v1517-wifi-critical-source-pre-l0-handoff"
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1518-wifi-critical-source-timing-classifier"
DEFAULT_REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1518_WIFI_CRITICAL_SOURCE_TIMING_CLASSIFIER_2026-06-01.md"
)
FIRST_LABEL = "case_aligned_micro_after_case_0ms"
EXPECTED_SOURCES = (
    "micro_interrupts",
    "micro_debug_gpio",
    "micro_pcie1_current_link_state",
    "micro_pcie1_link_state",
    "micro_critical_regulator",
    "micro_critical_pinmux",
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
    return json.loads(text) if text else {}


def classify(v1517_dir: Path) -> dict[str, Any]:
    manifest = read_json(v1517_dir / "manifest.json")
    progress = manifest.get("wifi_progress", {})
    rc1_text = read_text(v1517_dir / "test-rc1-window-result.stdout.txt")
    dmesg_text = read_text(v1517_dir / "test-v1393-dmesg.stdout.txt")
    headers = base.parse_headers(rc1_text)
    source_timings = base.parse_source_timing(rc1_text)
    first_sources = source_timings.get(FIRST_LABEL, {})
    dmesg = base.parse_dmesg(dmesg_text)
    link_failed_after_case_ms = dmesg["derived"].get("link_failed_after_case_ms")
    missing_sources = [source for source in EXPECTED_SOURCES if source not in first_sources]
    first_header = headers.get(FIRST_LABEL, {})
    first_sample = {source: base.source_window(first_sources[source]) for source in first_sources}
    expected_end_values = [
        first_sources.get(source, {}).get("end_micro_elapsed_ms")
        for source in EXPECTED_SOURCES
    ]
    max_expected_end_ms = max([value for value in expected_end_values if value is not None], default=None)
    all_expected_before_link_fail = (
        isinstance(max_expected_end_ms, int)
        and isinstance(link_failed_after_case_ms, float)
        and max_expected_end_ms < link_failed_after_case_ms
    )
    critical_skip_present = "micro_critical_clk_summary_skipped=1" in rc1_text
    no_full_clk_summary_source = "source=micro_batched_clk" not in rc1_text and "source=micro_focused_clk" not in rc1_text
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
        "timing": {
            "headers_count": len(headers),
            "first_header": first_header,
            "missing_sources": missing_sources,
            "source_timing_marker_present": "micro_source_timestamped_sampler=1" in rc1_text,
            "critical_marker_present": "micro_critical_fast_endpoint_sampler=1" in rc1_text,
            "critical_skip_present": critical_skip_present,
            "no_full_clk_summary_source": no_full_clk_summary_source,
            "link_failed_after_case_ms": link_failed_after_case_ms,
            "max_expected_source_end_ms": max_expected_end_ms,
            "all_expected_before_link_fail": all_expected_before_link_fail,
            "first_sample": first_sample,
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
        checks["timing"]["source_timing_marker_present"],
        checks["timing"]["critical_marker_present"],
        critical_skip_present,
        no_full_clk_summary_source,
        not missing_sources,
        first_header.get("micro_elapsed_ms") == 0,
        all_expected_before_link_fail,
        dmesg["link_failed"],
        not dmesg["l0"],
        not dmesg["mhi"],
        not dmesg["wlfw"],
        not dmesg["wlan0"],
    ]
    pass_ok = all(bool(item) for item in required)
    if pass_ok:
        decision = "v1518-critical-source-first-window-pre-fail-confirmed"
        reason = "V1517 proves all selected critical first-window sources finish before the RC1 link-fail marker while L0/MHI/WLFW/wlan0 remain absent"
    else:
        decision = "v1518-critical-source-timing-classifier-blocked"
        reason = "V1517 critical-source evidence did not satisfy the strict classifier"
    return {
        "cycle": "V1518",
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "v1517_dir": rel(v1517_dir),
        "checks": checks,
        "next_gate": {
            "primary": "V1519 Android-good vs native-fail critical source comparison",
            "rationale": "The native pre-fail window is now source-exact; compare against Android-good GPIO/GDSC/PERST/refclk/RC1 ordering before any new mutation.",
        },
    }


def render_report(result: dict[str, Any]) -> str:
    checks = result["checks"]
    timing = checks["timing"]
    dmesg = checks["dmesg"]
    lines = [
        "# Native Init V1518 Wi-Fi Critical Source Timing Classifier",
        "",
        "## Summary",
        "",
        "- Cycle: `V1518`",
        "- Type: host-only classifier over V1517 live handoff evidence",
        f"- Decision: `{result['decision']}`",
        f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
        f"- Reason: {result['reason']}",
        f"- Evidence: `{result['v1517_dir']}`",
        "",
        "## Handoff Result",
        "",
        f"- V1517 decision: `{checks['handoff']['decision']}`",
        f"- handoff pass: `{checks['handoff']['handoff_pass']}`",
        f"- rollback ok: `{checks['handoff']['rollback_ok']}`",
        f"- progress decision: `{checks['progress']['final_decision']}`",
        f"- RC1 progress/link failed/L0: `{checks['progress']['rc1_progress']}/{checks['progress']['rc1_link_failed']}/{checks['progress']['rc1_l0']}`",
        f"- MHI/WLFW/BDF/FW-ready/wlan0: `{checks['progress']['mhi_progress']}/{checks['progress']['wlfw_progress']}/{checks['progress']['bdf_progress']}/{checks['progress']['fw_ready_progress']}/{checks['progress']['wlan0_present']}`",
        "",
        "## Critical First-Window Timing",
        "",
        f"- link failed after TEST:11 case: `{timing['link_failed_after_case_ms']}` ms",
        f"- first sample micro elapsed: `{timing['first_header'].get('micro_elapsed_ms')}` ms",
        f"- max selected source end: `{timing['max_expected_source_end_ms']}` ms",
        f"- all selected sources finish before link fail: `{timing['all_expected_before_link_fail']}`",
        f"- full `clk_summary` skipped: `{timing['critical_skip_present']}`",
        f"- no full clock summary source emitted: `{timing['no_full_clk_summary_source']}`",
        "",
        "| Source | Begin ms | End ms | Duration ms |",
        "|---|---:|---:|---:|",
    ]
    for source in EXPECTED_SOURCES:
        item = timing["first_sample"].get(source, {})
        lines.append(
            f"| `{source}` | `{item.get('begin_micro_elapsed_ms')}` | `{item.get('end_micro_elapsed_ms')}` | `{item.get('duration_ms')}` |"
        )
    lines.extend([
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
        "V1517 closes the V1514 sampler-overrun gap. The selected fast sources complete by about 30ms after `case=11`, before the ~115ms RC1 link-fail marker. In that pre-fail window GPIO135 remains low, GPIO142 remains low, `pcie_1_gdsc` remains 0mV, and the pcie1 pinmux ownership is as expected. RC1 still fails before L0, so firmware/MHI/WLFW/scan/connect remain downstream.",
        "",
        "## Safety Scope",
        "",
        "This classifier is host-only. It performs no device command, flash, reboot, partition write, Wi-Fi HAL start, scan/connect, credential handling, DHCP/routes, external ping, PMIC/GPIO/GDSC write, eSoC notify/`BOOT_DONE` spoof, global PCI rescan, or platform bind/unbind.",
        "",
        "## Next",
        "",
        "- V1519 should compare Android-good and native-fail critical source timing/order before any new live mutation.",
        "- Keep firmware/MHI/WLFW/scan/connect work parked until RC1 L0 and PCI enumeration exist.",
        "",
    ])
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--v1517-dir", type=Path, default=DEFAULT_V1517_DIR)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--write-report", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.v1517_dir.exists():
        raise SystemExit(f"missing V1517 evidence dir: {args.v1517_dir}")
    store = EvidenceStore(args.out_dir)
    result = classify(args.v1517_dir)
    report = render_report(result)
    store.write_json("manifest.json", result)
    store.write_text("summary.md", report)
    if args.write_report:
        write_private_text(args.report_path, report)
    print(json.dumps({"decision": result["decision"], "pass": result["pass"], "out_dir": rel(args.out_dir)}, indent=2))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

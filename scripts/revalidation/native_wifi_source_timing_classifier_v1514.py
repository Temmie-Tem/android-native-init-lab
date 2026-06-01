#!/usr/bin/env python3
"""V1514 host-only classifier for V1513 source-timestamped pre-L0 evidence."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from a90harness.evidence import EvidenceStore, write_private_text


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_V1513_DIR = REPO_ROOT / "tmp" / "wifi" / "v1513-wifi-source-timestamped-pre-l0-handoff"
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1514-wifi-source-timing-classifier"
DEFAULT_REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1514_WIFI_SOURCE_TIMING_CLASSIFIER_2026-06-01.md"
)
FIRST_LABEL = "case_aligned_micro_after_case_0ms"
EXPECTED_SOURCES = (
    "micro_interrupts",
    "micro_debug_gpio",
    "micro_pcie1_current_link_state",
    "micro_pcie1_link_state",
    "micro_batched_regulator",
    "micro_batched_clk",
    "micro_batched_debug_gpio",
    "micro_batched_pinmux",
    "micro_batched_pinconf",
)
DMESG_TS_RE = re.compile(r"^\[\s*(?P<ts>\d+\.\d+)\]")
HEADER_RE = re.compile(
    r"^rc1_micro_sample label=(?P<label>\S+) "
    r"elapsed_ms=(?P<elapsed>-?\d+) "
    r"detect_elapsed_ms=(?P<detect>-?\d+) "
    r"micro_elapsed_ms=(?P<micro>-?\d+)"
)
TIMING_RE = re.compile(
    r"^sample=(?P<label>\S+) source=(?P<source>\S+) "
    r"source_timing=(?P<phase>begin|end) "
    r"elapsed_ms=(?P<elapsed>-?\d+) "
    r"micro_elapsed_ms=(?P<micro>-?\d+) "
    r"source_duration_ms=(?P<duration>-?\d+) "
    r"path=(?P<path>.*)$"
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


def first_ts(text: str, needle: str) -> float | None:
    for line in text.splitlines():
        if needle not in line:
            continue
        match = DMESG_TS_RE.match(line)
        if match is not None:
            return float(match.group("ts"))
    return None


def parse_headers(text: str) -> dict[str, dict[str, int]]:
    headers: dict[str, dict[str, int]] = {}
    for line in text.splitlines():
        match = HEADER_RE.match(line.strip())
        if match is None:
            continue
        headers[match.group("label")] = {
            "elapsed_ms": int(match.group("elapsed")),
            "detect_elapsed_ms": int(match.group("detect")),
            "micro_elapsed_ms": int(match.group("micro")),
        }
    return headers


def parse_source_timing(text: str) -> dict[str, dict[str, dict[str, Any]]]:
    out: dict[str, dict[str, dict[str, Any]]] = {}
    for line in text.splitlines():
        match = TIMING_RE.match(line.strip())
        if match is None:
            continue
        label = match.group("label")
        source = match.group("source")
        phase = match.group("phase")
        item = out.setdefault(label, {}).setdefault(source, {"path": match.group("path")})
        item[phase] = {
            "elapsed_ms": int(match.group("elapsed")),
            "micro_elapsed_ms": int(match.group("micro")),
            "source_duration_ms": int(match.group("duration")),
            "path": match.group("path"),
        }
    for sources in out.values():
        for item in sources.values():
            begin = item.get("begin", {})
            end = item.get("end", {})
            if begin and end:
                item["duration_ms"] = end["micro_elapsed_ms"] - begin["micro_elapsed_ms"]
                item["begin_micro_elapsed_ms"] = begin["micro_elapsed_ms"]
                item["end_micro_elapsed_ms"] = end["micro_elapsed_ms"]
            elif end:
                item["duration_ms"] = end.get("source_duration_ms")
                item["end_micro_elapsed_ms"] = end["micro_elapsed_ms"]
            elif begin:
                item["begin_micro_elapsed_ms"] = begin["micro_elapsed_ms"]
    return out


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


def source_window(source: dict[str, Any]) -> dict[str, Any]:
    return {
        "begin_micro_elapsed_ms": source.get("begin_micro_elapsed_ms"),
        "end_micro_elapsed_ms": source.get("end_micro_elapsed_ms"),
        "duration_ms": source.get("duration_ms"),
        "path": source.get("path"),
    }


def classify(v1513_dir: Path) -> dict[str, Any]:
    manifest = read_json(v1513_dir / "manifest.json")
    progress = manifest.get("wifi_progress", {})
    rc1_text = read_text(v1513_dir / "test-rc1-window-result.stdout.txt")
    dmesg_text = read_text(v1513_dir / "test-v1393-dmesg.stdout.txt")
    headers = parse_headers(rc1_text)
    source_timings = parse_source_timing(rc1_text)
    first_sources = source_timings.get(FIRST_LABEL, {})
    dmesg = parse_dmesg(dmesg_text)
    link_failed_after_case_ms = dmesg["derived"].get("link_failed_after_case_ms")
    missing_sources = [source for source in EXPECTED_SOURCES if source not in first_sources]
    first_header = headers.get(FIRST_LABEL, {})
    clk = first_sources.get("micro_batched_clk", {})
    regulator = first_sources.get("micro_batched_regulator", {})
    post_clk_sources = {
        source: source_window(first_sources[source])
        for source in ("micro_batched_debug_gpio", "micro_batched_pinmux", "micro_batched_pinconf")
        if source in first_sources
    }
    clk_crosses_link_fail = (
        isinstance(link_failed_after_case_ms, float)
        and clk.get("begin_micro_elapsed_ms") is not None
        and clk.get("end_micro_elapsed_ms") is not None
        and clk["begin_micro_elapsed_ms"] < link_failed_after_case_ms < clk["end_micro_elapsed_ms"]
    )
    first_sample_source_exact_before_clk = (
        first_sources.get("micro_interrupts", {}).get("end_micro_elapsed_ms", 9999) <= 5
        and first_sources.get("micro_debug_gpio", {}).get("end_micro_elapsed_ms", 9999) <= 15
        and first_sources.get("micro_pcie1_link_state", {}).get("end_micro_elapsed_ms", 9999) <= 15
        and regulator.get("end_micro_elapsed_ms", 9999) < link_failed_after_case_ms
        if isinstance(link_failed_after_case_ms, float)
        else False
    )
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
            "first_sample_source_count": len(first_sources),
            "missing_sources": missing_sources,
            "source_timing_marker_present": "micro_source_timestamped_sampler=1" in rc1_text,
            "link_failed_after_case_ms": link_failed_after_case_ms,
            "clk_crosses_link_fail": clk_crosses_link_fail,
            "first_sample_source_exact_before_clk": first_sample_source_exact_before_clk,
            "first_sample": {source: source_window(first_sources[source]) for source in first_sources},
            "post_clk_sources": post_clk_sources,
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
        not missing_sources,
        first_header.get("micro_elapsed_ms") == 0,
        first_sample_source_exact_before_clk,
        clk_crosses_link_fail,
        dmesg["link_failed"],
        not dmesg["l0"],
        not dmesg["mhi"],
        not dmesg["wlfw"],
        not dmesg["wlan0"],
    ]
    pass_ok = all(bool(item) for item in required)
    if pass_ok:
        decision = "v1514-source-timing-identifies-clk-summary-overrun"
        reason = "V1513 proves the first sample starts at case+0ms, but clk_summary read crosses the RC1 link-fail marker and makes later source reads post-failure"
    else:
        decision = "v1514-source-timing-classifier-blocked"
        reason = "V1513 source-timestamped evidence did not satisfy the strict classifier"
    return {
        "cycle": "V1514",
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "v1513_dir": rel(v1513_dir),
        "checks": checks,
        "next_gate": {
            "primary": "V1515 source/build-only critical-source pre-L0 sampler",
            "rationale": "The broad source-timestamped sampler proves clk_summary is too slow for the first 115ms link-fail window; keep only fast critical GPIO/interrupt/link/regulator reads before any optional slow clock/pinmux reads.",
        },
    }


def render_report(result: dict[str, Any]) -> str:
    checks = result["checks"]
    timing = checks["timing"]
    dmesg = checks["dmesg"]
    first_sample = timing["first_sample"]
    lines = [
        "# Native Init V1514 Wi-Fi Source Timing Classifier",
        "",
        "## Summary",
        "",
        "- Cycle: `V1514`",
        "- Type: host-only classifier over V1513 live handoff evidence",
        f"- Decision: `{result['decision']}`",
        f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
        f"- Reason: {result['reason']}",
        f"- Evidence: `{result['v1513_dir']}`",
        "",
        "## Handoff Result",
        "",
        f"- V1513 decision: `{checks['handoff']['decision']}`",
        f"- handoff pass: `{checks['handoff']['handoff_pass']}`",
        f"- rollback ok: `{checks['handoff']['rollback_ok']}`",
        f"- progress decision: `{checks['progress']['final_decision']}`",
        f"- RC1 progress/link failed/L0: `{checks['progress']['rc1_progress']}/{checks['progress']['rc1_link_failed']}/{checks['progress']['rc1_l0']}`",
        f"- MHI/WLFW/BDF/FW-ready/wlan0: `{checks['progress']['mhi_progress']}/{checks['progress']['wlfw_progress']}/{checks['progress']['bdf_progress']}/{checks['progress']['fw_ready_progress']}/{checks['progress']['wlan0_present']}`",
        "",
        "## First Sample Source Timing",
        "",
        f"- link failed after TEST:11 case: `{timing['link_failed_after_case_ms']}` ms",
        f"- first sample micro elapsed: `{timing['first_header'].get('micro_elapsed_ms')}` ms",
        f"- source timing marker present: `{timing['source_timing_marker_present']}`",
        f"- expected sources present: `{not timing['missing_sources']}`",
        f"- fast sources finish before `clk_summary`: `{timing['first_sample_source_exact_before_clk']}`",
        f"- `clk_summary` crosses link fail: `{timing['clk_crosses_link_fail']}`",
        "",
        "| Source | Begin ms | End ms | Duration ms |",
        "|---|---:|---:|---:|",
    ]
    for source in EXPECTED_SOURCES:
        item = first_sample.get(source, {})
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
        "V1513 removes the ambiguity from V1510. The first sample begins at case+0ms and captures fast sources before the link-fail window, but the broad `/sys/kernel/debug/clk/clk_summary` read lasts about 114ms and crosses the RC1 link-fail marker. Reads after that point are not pre-fail evidence. The next useful sampler should split fast critical sources from slow diagnostic sources instead of repeating full `clk_summary` inside the first 115ms window.",
        "",
        "## Safety Scope",
        "",
        "This classifier is host-only. It performs no device command, flash, reboot, partition write, Wi-Fi HAL start, scan/connect, credential handling, DHCP/routes, external ping, PMIC/GPIO/GDSC write, eSoC notify/`BOOT_DONE` spoof, global PCI rescan, or platform bind/unbind.",
        "",
        "## Next",
        "",
        "- V1515 should be source/build-only and add a critical-source pre-L0 sampler that avoids full `clk_summary` during the first link-fail window.",
        "- Keep firmware/MHI/WLFW/scan/connect work parked until RC1 L0 and PCI enumeration exist.",
        "",
    ])
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--v1513-dir", type=Path, default=DEFAULT_V1513_DIR)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--write-report", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.v1513_dir.exists():
        raise SystemExit(f"missing V1513 evidence dir: {args.v1513_dir}")
    store = EvidenceStore(args.out_dir)
    result = classify(args.v1513_dir)
    report = render_report(result)
    store.write_json("manifest.json", result)
    store.write_text("summary.md", report)
    if args.write_report:
        write_private_text(args.report_path, report)
    print(json.dumps({"decision": result["decision"], "pass": result["pass"], "out_dir": rel(args.out_dir)}, indent=2))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

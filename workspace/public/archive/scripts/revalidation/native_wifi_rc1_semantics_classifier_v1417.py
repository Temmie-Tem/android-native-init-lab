#!/usr/bin/env python3
"""V1417 host-only RC1 semantics classifier for delayed Wi-Fi test-boot evidence."""

from __future__ import annotations

import argparse
import json
import re
import socket
from pathlib import Path
from typing import Any

from a90harness.evidence import EvidenceStore, write_private_text


REPO = Path(__file__).resolve().parents[2]
RUN_DIR = REPO / "tmp" / "wifi" / "v1417-rc1-semantics-classifier"
REPORT_PATH = REPO / "docs" / "reports" / "NATIVE_INIT_V1417_RC1_SEMANTICS_CLASSIFIER_2026-06-01.md"
ANDROID_MANIFEST = REPO / "tmp" / "wifi" / "v1371-rc1-ltssm-failure-classifier" / "manifest.json"
V1413_DMESG = REPO / "tmp" / "wifi" / "v1413-wifi-test-boot-kmsg-fallback-handoff" / "test-v1393-dmesg.stdout.txt"
V1416_MANIFEST = REPO / "tmp" / "wifi" / "v1416-wifi-test-boot-delayed-rc1-handoff" / "manifest.json"
V1416_DMESG = REPO / "tmp" / "wifi" / "v1416-wifi-test-boot-delayed-rc1-handoff" / "test-v1393-dmesg.stdout.txt"

DMESG_RE = re.compile(r"^\[\s*(?P<time>\d+\.\d+)\]\s*(?P<text>.*)$")

EVENT_PATTERNS = {
    "esoc0_get": "__subsystem_get: esoc0 count",
    "test11": "PCIe: TEST: 11",
    "assert_reset": "Assert the reset of endpoint of RC1",
    "phy_ready": "PCIe RC1 PHY is ready",
    "release_reset": "Release the reset of endpoint of RC1",
    "detect_quiet_first": "LTSSM_STATE: LTSSM_DETECT_QUIET",
    "poll_active_first": "LTSSM_STATE: LTSSM_POLL_ACTIVE",
    "poll_compliance_first": "LTSSM_STATE: LTSSM_POLL_COMPLIANCE",
    "l0_first": "LTSSM_STATE: LTSSM_L0",
    "current_gen": "PCIe RC1 Current GEN",
    "link_initialized": "PCIe RC1 link initialized",
    "link_failed": "PCIe RC1 link initialization failed",
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_dmesg_events(path: Path) -> dict[str, dict[str, Any]]:
    events: dict[str, dict[str, Any]] = {}
    for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = DMESG_RE.match(raw_line)
        if not match:
            continue
        text = match.group("text")
        for event, pattern in EVENT_PATTERNS.items():
            if event in events:
                continue
            if pattern in text:
                events[event] = {
                    "time": float(match.group("time")),
                    "text": text,
                    "raw": raw_line,
                }
    return events


def event_time(events: dict[str, dict[str, Any]], name: str) -> float | None:
    event = events.get(name)
    if not event:
        return None
    value = event.get("time")
    return float(value) if value is not None else None


def delta(events: dict[str, dict[str, Any]], start: str, end: str) -> float | None:
    start_time = event_time(events, start)
    end_time = event_time(events, end)
    if start_time is None or end_time is None:
        return None
    return round(end_time - start_time, 6)


def compact_event(events: dict[str, dict[str, Any]], name: str) -> dict[str, Any] | None:
    event = events.get(name)
    if not event:
        return None
    return {
        "time": event.get("time"),
        "text": event.get("text"),
    }


def fmt_seconds(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:.6f}s"


def build_manifest() -> dict[str, Any]:
    android = load_json(ANDROID_MANIFEST)
    v1416 = load_json(V1416_MANIFEST)
    v1413_events = parse_dmesg_events(V1413_DMESG)
    v1416_events = parse_dmesg_events(V1416_DMESG)

    android_deltas = android["deltas"]
    android_esoc0_to_assert = float(android_deltas["android_esoc0_to_assert_sec"])
    android_assert_to_release = float(android_deltas["android_assert_to_release_sec"])
    android_release_to_l0 = float(android_deltas["android_release_to_l0_sec"])

    v1413_esoc0_to_test11 = delta(v1413_events, "esoc0_get", "test11")
    v1416_esoc0_to_test11 = delta(v1416_events, "esoc0_get", "test11")
    v1416_test11_to_phy = delta(v1416_events, "test11", "phy_ready")
    v1416_test11_to_fail = delta(v1416_events, "test11", "link_failed")
    v1416_trigger_error = (
        round(v1416_esoc0_to_test11 - android_esoc0_to_assert, 6)
        if v1416_esoc0_to_test11 is not None
        else None
    )
    timing_aligned = (
        v1416_trigger_error is not None
        and abs(v1416_trigger_error) <= 0.050
    )
    dmesg_filter = ""
    for step in v1416.get("steps", []):
        command = step.get("command", [])
        joined = " ".join(str(item) for item in command)
        if "dmesg" in joined and "grep" in joined:
            dmesg_filter = joined
            break
    filter_includes_reset_markers = (
        "Assert the reset" in dmesg_filter
        or "Release the reset" in dmesg_filter
        or "endpoint of RC1" in dmesg_filter
    )
    reset_markers_absent_in_filtered_evidence = (
        "assert_reset" not in v1416_events
        and "release_reset" not in v1416_events
    )
    reset_marker_absence_proven = (
        filter_includes_reset_markers
        and reset_markers_absent_in_filtered_evidence
    )
    link_failed_no_l0 = (
        "link_failed" in v1416_events
        and "l0_first" not in v1416_events
        and not bool(v1416.get("wifi_progress", {}).get("wlan0_present"))
    )

    if timing_aligned and link_failed_no_l0 and not filter_includes_reset_markers:
        decision = "v1417-delayed-rc1-timing-aligned-filtered-dmesg-recapture-needed"
        reason = (
            "V1416 aligns corrected RC1 timing with Android within 50ms and still "
            "fails before L0, but the V1416 dmesg grep pattern omitted endpoint "
            "reset/release markers; their absence is therefore not proven."
        )
        next_step = (
            "V1418 should rerun the same V1414 test image with an expanded dmesg "
            "pattern that includes endpoint reset/release and PCIE20_PARF_INT "
            "markers before changing timing or trigger design."
        )
    elif timing_aligned and reset_marker_absence_proven and link_failed_no_l0:
        decision = "v1417-delayed-rc1-timing-aligned-test11-semantics-gap"
        reason = (
            "V1416 aligns corrected RC1 timing with Android within 50ms, but the "
            "test-boot debugfs TEST:11 path still lacks Android reset/release "
            "markers and fails before L0."
        )
        next_step = (
            "V1418 should be source/host-only: inspect the stock msm_pcie debugfs "
            "TEST:11 path against Android's normal RC1 bring-up path and decide "
            "whether the next test boot needs a different RC1 trigger, not another "
            "blind delay retry."
        )
    elif link_failed_no_l0:
        decision = "v1417-delayed-rc1-link-failed-needs-delay-or-endpoint-classifier"
        reason = (
            "V1416 still fails before L0, but the current evidence is insufficient "
            "to separate delay tuning from trigger semantics."
        )
        next_step = "Classify a delay sweep or trigger-semantics check before another live handoff."
    else:
        decision = "v1417-rc1-semantics-classifier-inconclusive"
        reason = "Existing evidence did not match the expected V1416 RC1 failure shape."
        next_step = "Collect stronger RC1 evidence before progressing toward connect."

    return {
        "cycle": "V1417",
        "type": "host-only RC1 semantics classifier",
        "decision": decision,
        "pass": True,
        "reason": reason,
        "host": socket.gethostname(),
        "inputs": {
            "android_manifest": str(ANDROID_MANIFEST.relative_to(REPO)),
            "v1413_dmesg": str(V1413_DMESG.relative_to(REPO)),
            "v1416_manifest": str(V1416_MANIFEST.relative_to(REPO)),
            "v1416_dmesg": str(V1416_DMESG.relative_to(REPO)),
        },
        "android_reference": {
            "esoc0_to_assert_sec": android_esoc0_to_assert,
            "assert_to_release_sec": android_assert_to_release,
            "release_to_l0_sec": android_release_to_l0,
            "assert_reset": android["android_events"].get("assert_reset"),
            "release_reset": android["android_events"].get("release_reset"),
            "l0_first": android["android_events"].get("l0_first"),
            "current_gen": android["android_events"].get("current_gen"),
        },
        "v1413": {
            "esoc0_get": compact_event(v1413_events, "esoc0_get"),
            "test11": compact_event(v1413_events, "test11"),
            "link_failed": compact_event(v1413_events, "link_failed"),
            "esoc0_to_test11_sec": v1413_esoc0_to_test11,
            "l0_seen": "l0_first" in v1413_events,
        },
        "v1416": {
            "wifi_progress": v1416.get("wifi_progress", {}),
            "events": {
                name: compact_event(v1416_events, name)
                for name in (
                    "esoc0_get",
                    "test11",
                    "assert_reset",
                    "phy_ready",
                    "release_reset",
                    "detect_quiet_first",
                    "poll_active_first",
                    "poll_compliance_first",
                    "l0_first",
                    "current_gen",
                    "link_initialized",
                    "link_failed",
                )
            },
            "esoc0_to_test11_sec": v1416_esoc0_to_test11,
            "test11_to_phy_ready_sec": v1416_test11_to_phy,
            "test11_to_link_failed_sec": v1416_test11_to_fail,
            "trigger_error_vs_android_sec": v1416_trigger_error,
            "timing_aligned_with_android_50ms": timing_aligned,
            "dmesg_filter": dmesg_filter,
            "dmesg_filter_includes_reset_markers": filter_includes_reset_markers,
            "reset_markers_absent_in_filtered_evidence": reset_markers_absent_in_filtered_evidence,
            "reset_marker_absence_proven": reset_marker_absence_proven,
            "link_failed_no_l0": link_failed_no_l0,
        },
        "safety": {
            "host_only": True,
            "device_command_executed": False,
            "flash_executed": False,
            "wifi_scan_connect_executed": False,
            "credential_use_executed": False,
            "dhcp_route_executed": False,
            "external_ping_executed": False,
            "pmic_gpio_gdsc_write_executed": False,
            "blind_esoc_notify_executed": False,
        },
        "next_step": next_step,
    }


def render_report(manifest: dict[str, Any]) -> str:
    android = manifest["android_reference"]
    v1413 = manifest["v1413"]
    v1416 = manifest["v1416"]
    return "\n".join([
        "# Native Init V1417 RC1 Semantics Classifier",
        "",
        "## Summary",
        "",
        "- Cycle: `V1417`",
        "- Type: host-only RC1 semantics classifier",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS for classification; still BLOCKED for Wi-Fi connect readiness",
        f"- Reason: {manifest['reason']}",
        f"- Evidence: `{RUN_DIR.relative_to(REPO)}`",
        "",
        "## Timing Comparison",
        "",
        "| Path | esoc0→trigger | reset/release markers | L0 | link fail |",
        "|---|---:|---|---|---|",
        (
            f"| Android reference | {fmt_seconds(android['esoc0_to_assert_sec'])} | "
            "assert+release present | yes | no |"
        ),
        (
            f"| V1413 immediate kmsg watcher | {fmt_seconds(v1413['esoc0_to_test11_sec'])} | "
            "not required for this classifier | no | yes |"
        ),
        (
            f"| V1416 delayed kmsg watcher | {fmt_seconds(v1416['esoc0_to_test11_sec'])} | "
            f"{'unproven-filtered' if not v1416['dmesg_filter_includes_reset_markers'] else ('absent' if v1416['reset_markers_absent_in_filtered_evidence'] else 'present')} | "
            f"{'no' if v1416['link_failed_no_l0'] else 'unknown'} | "
            f"{'yes' if v1416['link_failed_no_l0'] else 'unknown'} |"
        ),
        "",
        "## Classification",
        "",
        f"- `v1416_trigger_error_vs_android_sec`: `{v1416['trigger_error_vs_android_sec']}`",
        f"- `v1416_timing_aligned_with_android_50ms`: `{v1416['timing_aligned_with_android_50ms']}`",
        f"- `v1416_dmesg_filter_includes_reset_markers`: `{v1416['dmesg_filter_includes_reset_markers']}`",
        f"- `v1416_reset_markers_absent_in_filtered_evidence`: `{v1416['reset_markers_absent_in_filtered_evidence']}`",
        f"- `v1416_reset_marker_absence_proven`: `{v1416['reset_marker_absence_proven']}`",
        f"- `v1416_link_failed_no_l0`: `{v1416['link_failed_no_l0']}`",
        f"- `v1416_test11_to_phy_ready_sec`: `{v1416['test11_to_phy_ready_sec']}`",
        f"- `v1416_test11_to_link_failed_sec`: `{v1416['test11_to_link_failed_sec']}`",
        "",
        "V1416 removes the major timing objection from V1413: the corrected RC1",
        "action now lands close to the Android reference window. The remaining",
        "difference that remains proven is link behavior: V1416 reaches",
        "PHY/LTSSM but stalls in poll-compliance. Reset/release marker absence",
        "is not proven because the V1416 dmesg capture was filtered without those",
        "patterns.",
        "",
        "## Safety Scope",
        "",
        "This cycle is host-only. It executes no device command, flash, Wi-Fi",
        "scan/connect, credential handling, DHCP/routes, external ping,",
        "PMIC/GPIO/GDSC write, or blind eSoC notify/`BOOT_DONE` spoof.",
        "",
        "## Next",
        "",
        manifest["next_step"],
    ]) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-report", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    store = EvidenceStore(RUN_DIR)
    manifest = build_manifest()
    report = render_report(manifest)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", report)
    if args.write_report:
        write_private_text(REPORT_PATH, report)
    print(json.dumps({
        "decision": manifest["decision"],
        "pass": manifest["pass"],
        "out_dir": str(RUN_DIR.relative_to(REPO)),
        "report": str(REPORT_PATH.relative_to(REPO)) if args.write_report else None,
    }, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

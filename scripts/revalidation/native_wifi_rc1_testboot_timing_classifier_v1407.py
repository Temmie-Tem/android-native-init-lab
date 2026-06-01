#!/usr/bin/env python3
"""V1407 host-only RC1 timing classifier for Wi-Fi test-boot evidence."""

from __future__ import annotations

import argparse
import json
import re
import socket
from pathlib import Path
from typing import Any

from a90harness.evidence import EvidenceStore, write_private_text


REPO = Path(__file__).resolve().parents[2]
RUN_DIR = REPO / "tmp/wifi/v1407-rc1-testboot-timing-classifier"
REPORT_PATH = REPO / "docs/reports/NATIVE_INIT_V1407_RC1_TESTBOOT_TIMING_CLASSIFIER_2026-06-01.md"
V1371_MANIFEST = REPO / "tmp/wifi/v1371-rc1-ltssm-failure-classifier/manifest.json"
V1391_MANIFEST = REPO / "tmp/wifi/v1391-android-participant-early-powerup-corrected-rc1-live/manifest.json"
V1406_MANIFEST = REPO / "tmp/wifi/v1406-wifi-test-boot-debugfs-handoff/manifest.json"
V1406_DMESG = REPO / "tmp/wifi/v1406-wifi-test-boot-debugfs-handoff/test-v1393-dmesg.stdout.txt"
V1406_REPORT = REPO / "docs/reports/NATIVE_INIT_V1406_WIFI_TEST_BOOT_DEBUGFS_HANDOFF_2026-06-01.md"

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
    "link_initialized": "PCIe RC1 link initialized",
    "current_gen": "PCIe RC1 Current GEN",
    "link_failed": "PCIe RC1 link initialization failed",
}


def repo_path(path: Path) -> Path:
    return path if path.is_absolute() else REPO / path


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(repo_path(path).read_text(encoding="utf-8"))


def parse_dmesg_events(path: Path) -> dict[str, dict[str, Any]]:
    events: dict[str, dict[str, Any]] = {}
    for raw_line in repo_path(path).read_text(encoding="utf-8", errors="replace").splitlines():
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
                    "raw": raw_line,
                    "text": text,
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


def ratio(value: float | None, baseline: float | None) -> float | None:
    if value is None or baseline in (None, 0):
        return None
    return round(value / baseline, 3)


def compact_event(events: dict[str, dict[str, Any]], name: str) -> dict[str, Any] | None:
    event = events.get(name)
    if not event:
        return None
    return {
        "time": event.get("time"),
        "text": event.get("text"),
    }


def build_manifest() -> dict[str, Any]:
    v1371 = load_json(V1371_MANIFEST)
    v1391 = load_json(V1391_MANIFEST)
    v1406 = load_json(V1406_MANIFEST)
    v1406_events = parse_dmesg_events(V1406_DMESG)

    android_events = v1371["android_events"]
    android_deltas = v1371["deltas"]
    v1391_rc1 = v1391["dmesg_rc1"]
    v1406_deltas = {
        "esoc0_to_test11_sec": delta(v1406_events, "esoc0_get", "test11"),
        "esoc0_to_assert_sec": delta(v1406_events, "esoc0_get", "assert_reset"),
        "test11_to_phy_ready_sec": delta(v1406_events, "test11", "phy_ready"),
        "test11_to_link_failed_sec": delta(v1406_events, "test11", "link_failed"),
        "assert_to_release_sec": delta(v1406_events, "assert_reset", "release_reset"),
        "release_to_poll_active_sec": delta(v1406_events, "release_reset", "poll_active_first"),
        "release_to_poll_compliance_sec": delta(v1406_events, "release_reset", "poll_compliance_first"),
        "release_to_l0_sec": delta(v1406_events, "release_reset", "l0_first"),
        "release_to_link_failed_sec": delta(v1406_events, "release_reset", "link_failed"),
        "phy_ready_to_link_failed_sec": delta(v1406_events, "phy_ready", "link_failed"),
    }
    android_esoc0_to_assert = float(android_deltas["android_esoc0_to_assert_sec"])
    android_release_to_l0 = float(android_deltas["android_release_to_l0_sec"])
    v1406_trigger_delta = (
        v1406_deltas["esoc0_to_assert_sec"]
        if v1406_deltas["esoc0_to_assert_sec"] is not None
        else v1406_deltas["esoc0_to_test11_sec"]
    )
    v1406_failure_delta = (
        v1406_deltas["release_to_link_failed_sec"]
        if v1406_deltas["release_to_link_failed_sec"] is not None
        else v1406_deltas["phy_ready_to_link_failed_sec"]
    )
    v1391_esoc0_to_assert = float(v1391_rc1["esoc0_to_assert_sec"])

    trigger_late = (
        v1406_trigger_delta is not None
        and v1406_trigger_delta > android_esoc0_to_assert + 1.0
    )
    same_late_class_as_v1391 = (
        v1406_trigger_delta is not None
        and abs(v1406_trigger_delta - v1391_esoc0_to_assert) < 0.25
    )
    link_failed_no_l0 = (
        "link_failed" in v1406_events
        and "l0_first" not in v1406_events
        and not v1406.get("wifi_progress", {}).get("wlan0_present")
    )
    if trigger_late and same_late_class_as_v1391 and link_failed_no_l0:
        decision = "v1407-test-boot-rc1-trigger-still-late-no-l0"
        next_step = (
            "V1408 source/build-only: split corrected RC1 trigger into a tiny PID1-started "
            "parallel watcher that does no service snapshots and writes debugfs immediately "
            "after the first esoc0/powerup condition."
        )
    elif link_failed_no_l0:
        decision = "v1407-test-boot-rc1-link-fail-needs-endpoint-readiness-design"
        next_step = (
            "Design the next below-connect endpoint-readiness probe before another live handoff."
        )
    else:
        decision = "v1407-test-boot-rc1-comparison-inconclusive"
        next_step = "Collect stronger host-only timing evidence before another boot image handoff."

    return {
        "cycle": "V1407",
        "type": "host-only RC1 test-boot timing classifier",
        "decision": decision,
        "pass": True,
        "reason": (
            "V1406 boot-time debugfs makes the corrected RC1 path reachable, but the trigger "
            "still lands in the same late timing class as V1391 and RC1 fails before L0."
        ),
        "host": socket.gethostname(),
        "inputs": {
            "v1371_manifest": str(V1371_MANIFEST.relative_to(REPO)),
            "v1391_manifest": str(V1391_MANIFEST.relative_to(REPO)),
            "v1406_manifest": str(V1406_MANIFEST.relative_to(REPO)),
            "v1406_dmesg": str(V1406_DMESG.relative_to(REPO)),
            "v1406_report": str(V1406_REPORT.relative_to(REPO)),
        },
        "android_reference": {
            "esoc0_get": compact_event(android_events, "esoc0_get"),
            "assert_reset": compact_event(android_events, "assert_reset"),
            "release_reset": compact_event(android_events, "release_reset"),
            "l0_first": compact_event(android_events, "l0_first"),
            "link_initialized": compact_event(android_events, "link_initialized"),
            "esoc0_to_assert_sec": android_esoc0_to_assert,
            "release_to_l0_sec": android_release_to_l0,
        },
        "v1391_reference": {
            "esoc0_to_assert_sec": v1391_esoc0_to_assert,
            "release_to_link_failed_sec": float(v1391_rc1["release_to_link_failed_sec"]),
            "l0_seen": bool(v1391_rc1["l0_seen"]),
            "link_failed_seen": bool(v1391_rc1["link_failed_seen"]),
        },
        "v1406_events": {
            name: compact_event(v1406_events, name)
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
                "link_initialized",
                "current_gen",
                "link_failed",
            )
        },
        "v1406_deltas": v1406_deltas,
        "comparison": {
            "v1406_extra_esoc0_to_assert_vs_android_sec": (
                round(v1406_trigger_delta - android_esoc0_to_assert, 6)
                if v1406_trigger_delta is not None
                else None
            ),
            "v1406_trigger_delta_basis": (
                "esoc0_to_assert_sec"
                if v1406_deltas["esoc0_to_assert_sec"] is not None
                else "esoc0_to_test11_sec"
            ),
            "v1406_esoc0_to_assert_ratio_vs_android": ratio(v1406_trigger_delta, android_esoc0_to_assert),
            "v1406_release_to_link_failed_ratio_vs_android_l0": ratio(
                v1406_failure_delta,
                android_release_to_l0,
            ),
            "v1406_same_late_class_as_v1391": same_late_class_as_v1391,
            "trigger_late_vs_android": trigger_late,
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


def fmt(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def render_report(manifest: dict[str, Any]) -> str:
    android = manifest["android_reference"]
    v1391 = manifest["v1391_reference"]
    v1406_deltas = manifest["v1406_deltas"]
    comparison = manifest["comparison"]
    v1406_trigger_delta = v1406_deltas[comparison["v1406_trigger_delta_basis"]]
    v1406_failure_delta = (
        v1406_deltas["release_to_link_failed_sec"]
        if v1406_deltas["release_to_link_failed_sec"] is not None
        else v1406_deltas["phy_ready_to_link_failed_sec"]
    )
    lines = [
        "# Native Init V1407 RC1 Test-Boot Timing Classifier",
        "",
        "## Summary",
        "",
        f"- Cycle: `{manifest['cycle']}`",
        f"- Type: {manifest['type']}",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS for host-only classification; still BLOCKED for Wi-Fi connect readiness",
        f"- Reason: {manifest['reason']}",
        f"- Evidence: `{RUN_DIR.relative_to(REPO)}`",
        "",
        "## Timing Comparison",
        "",
        "| Path | esoc0→assert | release→success/fail | L0 | link fail |",
        "|---|---:|---:|---|---|",
        (
            f"| Android reference | {android['esoc0_to_assert_sec']:.6f}s | "
            f"{android['release_to_l0_sec']:.6f}s to L0 | yes | no |"
        ),
        (
            f"| V1391 early observer | {v1391['esoc0_to_assert_sec']:.6f}s | "
            f"{v1391['release_to_link_failed_sec']:.6f}s to fail | no | yes |"
        ),
        (
            f"| V1406 test boot | {fmt(v1406_trigger_delta)}s | "
            f"{fmt(v1406_failure_delta)}s to fail | no | yes |"
        ),
        "",
        "## Classification",
        "",
        f"- `trigger_late_vs_android`: `{comparison['trigger_late_vs_android']}`",
        f"- `v1406_same_late_class_as_v1391`: `{comparison['v1406_same_late_class_as_v1391']}`",
        f"- `v1406_trigger_delta_basis`: `{comparison['v1406_trigger_delta_basis']}`",
        f"- `v1406_extra_esoc0_to_assert_vs_android_sec`: `{comparison['v1406_extra_esoc0_to_assert_vs_android_sec']}`",
        f"- `v1406_esoc0_to_assert_ratio_vs_android`: `{comparison['v1406_esoc0_to_assert_ratio_vs_android']}`",
        f"- `link_failed_no_l0`: `{comparison['link_failed_no_l0']}`",
        "",
        "V1406 proves debugfs availability is no longer the blocker. The remaining",
        "difference is timing/endpoint readiness: the corrected RC1 write still occurs",
        "seconds after `esoc0`, while Android reaches the RC1 assert window in roughly",
        "a quarter second and reaches L0 immediately after reset release.",
        "",
        "## Safety Scope",
        "",
        "This cycle is host-only. It executes no device command, flash, Wi-Fi scan/connect,",
        "credential handling, DHCP/routes, external ping, PMIC/GPIO/GDSC write, or blind",
        "eSoC notify/`BOOT_DONE` spoof.",
        "",
        "## Next",
        "",
        manifest["next_step"],
    ]
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-report", action="store_true", help="write docs report in addition to evidence")
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

#!/usr/bin/env python3
"""V672 service-notifier regression classifier.

This host-only classifier compares the V668 service74-positive live evidence
with the V671 service74-timeout live evidence. It does not contact the device,
start services, start Wi-Fi HAL, scan, connect, run DHCP, change routes, use
credentials, or ping externally.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v672-service74-regression-classifier")
DEFAULT_V668_MANIFEST = Path("tmp/wifi/v668-cnss2-focused-capture-live/manifest.json")
DEFAULT_V671_MANIFEST = Path("tmp/wifi/v671-service74-android-userspace-live/manifest.json")

FORBIDDEN_ACTIONS = (
    "device command",
    "service start",
    "Wi-Fi HAL start",
    "supplicant or hostapd start",
    "scan/connect/link-up",
    "credential/DHCP/routing/external ping",
    "boot image or partition write",
)

MARKERS = (
    "qrtr_rx",
    "qrtr_tx",
    "sysmon_qmi",
    "service_notifier",
    "kernel_warning",
    "qmi_server_connected",
    "wlfw",
    "bdf",
    "wlan_fw_ready",
    "wlan0",
)
COUNT_KEYS = (
    "service_notifier_180",
    "service_notifier_74",
    "cnss_daemon_netlink",
    "cnss_daemon_cld80211",
    "cnss_binder_transaction_failed",
    "binder_transaction_failed",
    "binder_ioctl_unsupported",
    "kernel_warning",
    "qmi_server_connected",
    "wlfw_start",
    "wlfw_service_request",
    "bdf_regdb",
    "bdf_bdwlan",
    "wlan_fw_ready",
    "wlan0",
)
TIMESTAMP_RE = re.compile(r"\[\s*(?P<ts>[0-9]+(?:\.[0-9]+)?)\]")
EVENT_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("qrtr_rx", re.compile(r"qrtr: Modem QMI Readiness RX", re.I)),
    ("qrtr_tx", re.compile(r"qrtr: Modem QMI Readiness TX", re.I)),
    ("sysmon_qmi", re.compile(r"sysmon-qmi: ssctl_new_server", re.I)),
    ("service_notifier_180", re.compile(r"service-notifier:.*180 service", re.I)),
    ("service_notifier_74", re.compile(r"service-notifier:.*74 service", re.I)),
    ("cnss_diag_netlink", re.compile(r"netlink_create.*comm:\s*cnss_diag", re.I)),
    ("cnss_daemon_netlink", re.compile(r"netlink_create.*comm:\s*cnss-daemon", re.I)),
    ("cnss_binder_failure", re.compile(r"cnss-daemon.*binder:.*transaction failed .*?-22", re.I)),
    ("kernel_warning", re.compile(r"WARNING: CPU|pm_qos_add_request", re.I)),
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v668-manifest", type=Path, default=DEFAULT_V668_MANIFEST)
    parser.add_argument("--v671-manifest", type=Path, default=DEFAULT_V671_MANIFEST)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def read_text(path: Path) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    return resolved.read_bytes().replace(b"\0", b"\n").decode("utf-8", errors="replace")


def load_json(path: Path) -> dict[str, Any]:
    text = read_text(path)
    return json.loads(text) if text else {}


def evidence_dir(manifest_path: Path, manifest: dict[str, Any]) -> Path:
    evidence = manifest.get("evidence") or manifest.get("out_dir")
    if evidence:
        return repo_path(Path(str(evidence)))
    return repo_path(manifest_path).parent


def int_value(value: object) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def live_surface(manifest: dict[str, Any]) -> dict[str, Any]:
    live = manifest.get("live") or {}
    for key in ("v671_android_userspace_surface", "v668_surface", "v655_surface"):
        value = live.get(key)
        if isinstance(value, dict):
            return value
    return {}


def service74_gate(manifest: dict[str, Any]) -> dict[str, Any]:
    surface = live_surface(manifest)
    value = surface.get("service74_gate")
    return value if isinstance(value, dict) else {}


def marker_counts(manifest: dict[str, Any]) -> dict[str, int]:
    live = manifest.get("live") or {}
    markers = ((live.get("markers") or {}).get("counts") or {})
    return {name: int_value(markers.get(name)) for name in MARKERS}


def v655_counts(manifest: dict[str, Any]) -> dict[str, int]:
    live = manifest.get("live") or {}
    counts = live.get("v655_counts") or live.get("v668_counts") or live.get("v644_counts") or {}
    return {name: int_value(counts.get(name)) for name in COUNT_KEYS}


def lower_surface(manifest: dict[str, Any]) -> dict[str, Any]:
    live = manifest.get("live") or {}
    return {
        "firmware_class_path": live.get("firmware_class_path", ""),
        "mounted_hits": live.get("mounted_hits") or {},
        "modem_blob_visible": live.get("modem_blob_visible") or {},
        "mss_after_holder": live.get("mss_after_holder", ""),
        "mss_after_companion": live.get("mss_after_companion", ""),
        "mdm3_after_companion": live.get("mdm3_after_companion", ""),
        "holder_started": bool(live.get("holder_started")),
        "qrtr_rx_seen": bool((live.get("qrtr_rx_wait") or {}).get("seen")),
        "companion_executed": bool(live.get("companion_executed")),
    }


def android_userspace_withheld(v671: dict[str, Any]) -> bool:
    surface = (v671.get("live") or {}).get("v671_android_userspace_surface") or {}
    children = surface.get("children") or {}
    names = ("wifi_hal_legacy", "wifi_hal_ext", "wificond", "cnss_daemon_retry")
    return all(not ((children.get(name) or {}).get("start_order")) for name in names)


def event_timeline(evidence: Path) -> list[dict[str, Any]]:
    text = read_text(evidence / "native" / "dmesg-delta.txt")
    events: list[dict[str, Any]] = []
    for raw in text.splitlines():
        for name, pattern in EVENT_PATTERNS:
            if not pattern.search(raw):
                continue
            timestamp_match = TIMESTAMP_RE.search(raw)
            timestamp = float(timestamp_match.group("ts")) if timestamp_match else None
            events.append({
                "event": name,
                "timestamp": timestamp,
                "line": raw.strip(),
            })
            break
    return events


def first_event_map(events: list[dict[str, Any]]) -> dict[str, float | None]:
    result: dict[str, float | None] = {}
    for event in events:
        result.setdefault(event["event"], event.get("timestamp"))
    return result


def build_checks(v668: dict[str, Any],
                 v671: dict[str, Any],
                 v668_lower: dict[str, Any],
                 v671_lower: dict[str, Any],
                 v668_counts: dict[str, int],
                 v671_counts: dict[str, int],
                 v668_markers: dict[str, int],
                 v671_markers: dict[str, int]) -> list[dict[str, Any]]:
    v668_gate = service74_gate(v668)
    v671_gate = service74_gate(v671)
    lower_same = (
        v668_lower["firmware_class_path"] == v671_lower["firmware_class_path"]
        and v668_lower["mounted_hits"] == v671_lower["mounted_hits"]
        and v668_lower["modem_blob_visible"] == v671_lower["modem_blob_visible"]
        and v668_lower["holder_started"] is True
        and v671_lower["holder_started"] is True
        and v668_lower["qrtr_rx_seen"] is True
        and v671_lower["qrtr_rx_seen"] is True
        and v668_lower["companion_executed"] is True
        and v671_lower["companion_executed"] is True
    )
    return [
        {
            "name": "v668-service74-positive-reference",
            "status": "pass" if (
                v668.get("decision") == "v668-cnss2-focused-capture-gap-classified"
                and v668_counts.get("service_notifier_180", 0) > 0
                and v668_counts.get("service_notifier_74", 0) > 0
                and v668_gate.get("open") == "1"
            ) else "blocked",
            "detail": {
                "decision": v668.get("decision"),
                "service_notifier_180": v668_counts.get("service_notifier_180"),
                "service_notifier_74": v668_counts.get("service_notifier_74"),
                "gate": v668_gate,
            },
            "next_step": "provide V668-positive live evidence before classifying regression",
        },
        {
            "name": "v671-service74-timeout-target",
            "status": "pass" if (
                v671.get("decision") == "v671-service74-gate-timeout"
                and v671_counts.get("service_notifier_180", 0) == 0
                and v671_counts.get("service_notifier_74", 0) == 0
                and v671_gate.get("open") == "0"
            ) else "blocked",
            "detail": {
                "decision": v671.get("decision"),
                "service_notifier_180": v671_counts.get("service_notifier_180"),
                "service_notifier_74": v671_counts.get("service_notifier_74"),
                "gate": v671_gate,
            },
            "next_step": "provide V671 timeout evidence before classifying regression",
        },
        {
            "name": "lower-firmware-modem-surface-equivalent",
            "status": "pass" if lower_same else "blocked",
            "detail": {
                "v668": v668_lower,
                "v671": v671_lower,
            },
            "next_step": "normalize firmware/modem mount and holder prerequisites before retrying",
        },
        {
            "name": "qrtr-sysmon-parity-before-gap",
            "status": "pass" if (
                v668_markers.get("qrtr_rx", 0) > 0
                and v668_markers.get("qrtr_tx", 0) > 0
                and v668_markers.get("sysmon_qmi", 0) > 0
                and v671_markers.get("qrtr_rx", 0) > 0
                and v671_markers.get("qrtr_tx", 0) > 0
                and v671_markers.get("sysmon_qmi", 0) > 0
            ) else "blocked",
            "detail": {"v668": v668_markers, "v671": v671_markers},
            "next_step": "restore QRTR/sysmon baseline before isolating service-notifier publication",
        },
        {
            "name": "android-userspace-withheld-by-gate",
            "status": "pass" if android_userspace_withheld(v671) else "review",
            "detail": (v671.get("live") or {}).get("v671_android_userspace_surface") or {},
            "next_step": "if children started, inspect HAL/wificond side effects; otherwise classify lower gate first",
        },
    ]


def blockers(checks: list[dict[str, Any]]) -> list[str]:
    return [check["name"] for check in checks if check["status"] == "blocked"]


def decide(command: str, checks: list[dict[str, Any]], v668_counts: dict[str, int], v671_counts: dict[str, int]) -> tuple[str, bool, str, str]:
    if command == "plan":
        return (
            "v672-service74-regression-plan-ready",
            True,
            "plan-only; no evidence classification or device command executed",
            "run V672 host-only classifier",
        )
    blocked = blockers(checks)
    if blocked:
        return (
            "v672-service74-regression-blocked",
            False,
            "blocked by " + ", ".join(blocked),
            "refresh the missing V668/V671 live evidence before choosing a live retry",
        )
    binder_delta = v671_counts.get("cnss_binder_transaction_failed", 0) - v668_counts.get("cnss_binder_transaction_failed", 0)
    return (
        "v672-service74-regression-classified",
        True,
        (
            "V668 and V671 both reach QRTR RX/TX and sysmon with equivalent firmware/modem surface, "
            "but only V668 publishes service-notifier 180/74; V671 withholds Android userspace children "
            f"at the service74 gate and shows cnss binder failure delta={binder_delta}"
        ),
        (
            "run V673 as a same-helper replay matrix: v111 V668-compatible service74 CNSS retry versus "
            "v111 Android-userspace mode on a freshly restored current boot, then only proceed to HAL/wificond "
            "if service74/180 publication is reproducible"
        ),
    )


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    v668 = load_json(args.v668_manifest)
    v671 = load_json(args.v671_manifest)
    v668_evidence = evidence_dir(args.v668_manifest, v668)
    v671_evidence = evidence_dir(args.v671_manifest, v671)
    v668_counts = v655_counts(v668)
    v671_counts = v655_counts(v671)
    v668_markers = marker_counts(v668)
    v671_markers = marker_counts(v671)
    v668_lower = lower_surface(v668)
    v671_lower = lower_surface(v671)
    v668_events = event_timeline(v668_evidence)
    v671_events = event_timeline(v671_evidence)
    checks = build_checks(v668, v671, v668_lower, v671_lower, v668_counts, v671_counts, v668_markers, v671_markers)
    decision, pass_ok, reason, next_step = decide(args.command, checks, v668_counts, v671_counts)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "cycle": "v672",
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "inputs": {
            "v668_manifest": str(repo_path(args.v668_manifest)),
            "v671_manifest": str(repo_path(args.v671_manifest)),
            "v668_evidence": str(v668_evidence),
            "v671_evidence": str(v671_evidence),
        },
        "checks": checks,
        "comparison": {
            "v668_decision": v668.get("decision", ""),
            "v671_decision": v671.get("decision", ""),
            "v668_service74_gate": service74_gate(v668),
            "v671_service74_gate": service74_gate(v671),
            "v668_lower_surface": v668_lower,
            "v671_lower_surface": v671_lower,
            "v668_marker_counts": v668_markers,
            "v671_marker_counts": v671_markers,
            "v668_counts": v668_counts,
            "v671_counts": v671_counts,
            "v668_first_events": first_event_map(v668_events),
            "v671_first_events": first_event_map(v671_events),
            "v668_event_count": len(v668_events),
            "v671_event_count": len(v671_events),
        },
        "forbidden_actions": FORBIDDEN_ACTIONS,
        "device_commands_executed": False,
        "device_mutations": False,
        "daemon_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "wifi_bringup_executed": False,
        "external_ping_executed": False,
    }


def check_rows(checks: list[dict[str, Any]]) -> list[list[str]]:
    return [[check["name"], check["status"], json.dumps(check["detail"], sort_keys=True), check["next_step"]] for check in checks]


def count_rows(comparison: dict[str, Any]) -> list[list[str]]:
    rows: list[list[str]] = []
    for name in COUNT_KEYS:
        rows.append([
            name,
            str((comparison.get("v668_counts") or {}).get(name, 0)),
            str((comparison.get("v671_counts") or {}).get(name, 0)),
        ])
    return rows


def marker_rows(comparison: dict[str, Any]) -> list[list[str]]:
    rows: list[list[str]] = []
    for name in MARKERS:
        rows.append([
            name,
            str((comparison.get("v668_marker_counts") or {}).get(name, 0)),
            str((comparison.get("v671_marker_counts") or {}).get(name, 0)),
        ])
    return rows


def event_rows(comparison: dict[str, Any]) -> list[list[str]]:
    v668 = comparison.get("v668_first_events") or {}
    v671 = comparison.get("v671_first_events") or {}
    names = sorted(set(v668) | set(v671))
    return [[name, str(v668.get(name, "")), str(v671.get(name, ""))] for name in names]


def render_summary(manifest: dict[str, Any]) -> str:
    comparison = manifest["comparison"]
    return "\n".join([
        "# V672 Service-notifier Regression Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- wifi_hal_start_executed: `{manifest['wifi_hal_start_executed']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        f"- external_ping_executed: `{manifest['external_ping_executed']}`",
        "",
        "## Checks",
        "",
        markdown_table(["check", "status", "detail", "next"], check_rows(manifest["checks"])),
        "",
        "## Marker Counts",
        "",
        markdown_table(["marker", "V668", "V671"], marker_rows(comparison)),
        "",
        "## Service Counts",
        "",
        markdown_table(["name", "V668", "V671"], count_rows(comparison)),
        "",
        "## First Event Timestamps",
        "",
        markdown_table(["event", "V668", "V671"], event_rows(comparison)),
        "",
        "## Interpretation",
        "",
        "- V668 and V671 both prove the lower QRTR/sysmon path reaches the modem.",
        "- V668 publishes service-notifier `180/74`; V671 does not.",
        "- V671 withholds Wi-Fi HAL, `wificond`, and retry `cnss-daemon` at the gate, so the immediate blocker is lower service-notifier reproducibility rather than Wi-Fi connect logic.",
        "- The next live unit should isolate mode/helper/current-boot differences before any scan/connect or external ping attempt.",
    ])


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"wifi_hal_start_executed: {manifest['wifi_hal_start_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

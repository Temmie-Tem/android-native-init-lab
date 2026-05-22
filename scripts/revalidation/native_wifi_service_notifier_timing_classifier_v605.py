#!/usr/bin/env python3
"""V605 host-only service-notifier timing classifier."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v605-service-notifier-timing-classifier")
ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
TS_RE = re.compile(r"^\[\s*([0-9]+(?:\.[0-9]+)?)\]")


@dataclass(frozen=True)
class CaseInput:
    name: str
    dmesg: Path
    manifest: Path


@dataclass(frozen=True)
class Event:
    name: str
    timestamp: float
    line: str


DEFAULT_CASES = (
    CaseInput(
        "v598-baseline-no-service-manager",
        Path("tmp/wifi/v598-modem-holder-wlfw-readback/native/dmesg-delta.txt"),
        Path("tmp/wifi/v598-modem-holder-wlfw-readback/manifest.json"),
    ),
    CaseInput(
        "v603-qrtr-first-service-manager",
        Path("tmp/wifi/v603-qrtr-first-service-manager-live/native/dmesg-delta.txt"),
        Path("tmp/wifi/v603-qrtr-first-service-manager-live/manifest.json"),
    ),
    CaseInput(
        "v604b-cnss-first-delayed-service-manager",
        Path("tmp/wifi/v604b-cnss-first-service-manager-live/native/dmesg-delta.txt"),
        Path("tmp/wifi/v604b-cnss-first-service-manager-live/manifest.json"),
    ),
)

EVENT_PATTERNS = (
    ("qrtr_rx", re.compile(r"qrtr: Modem QMI Readiness RX", re.IGNORECASE)),
    ("qrtr_tx", re.compile(r"qrtr: Modem QMI Readiness TX", re.IGNORECASE)),
    ("sysmon_qmi", re.compile(r"sysmon-qmi", re.IGNORECASE)),
    ("service_notifier_180", re.compile(r"service-notifier.*\b180\b", re.IGNORECASE)),
    ("service_notifier_74", re.compile(r"service-notifier.*\b74\b", re.IGNORECASE)),
    ("cnss_diag_netlink", re.compile(r"cnss_diag.*netlink_create", re.IGNORECASE)),
    ("cnss_daemon_netlink", re.compile(r"cnss-daemon.*netlink_create", re.IGNORECASE)),
    ("binder_transaction_failed", re.compile(r"binder: .*transaction failed|binder transaction failed", re.IGNORECASE)),
    ("service_manager_binder_ioctl", re.compile(r"servicemanager.*binder:|binder: .*servicemanager|servicemanager.*ioctl", re.IGNORECASE)),
    ("hwservice_manager_binder_ioctl", re.compile(r"hwservicemanage.*binder:|hwservicemanage.*ioctl", re.IGNORECASE)),
    ("wlan_pd", re.compile(r"wlan[_-]pd|msm/modem/wlan_pd", re.IGNORECASE)),
    ("wlfw", re.compile(r"\bWLFW\b|wlfw", re.IGNORECASE)),
    ("bdf", re.compile(r"BDF file|bdwlan\.bin|regdb\.bin", re.IGNORECASE)),
    ("wlan0", re.compile(r"\bwlan0\b", re.IGNORECASE)),
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("command", choices=("run",), nargs="?", default="run")
    return parser.parse_args()


def read_text(path: Path) -> str:
    return repo_path(path).read_text(encoding="utf-8", errors="replace")


def load_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {"exists": False, "path": str(resolved)}
    data = json.loads(resolved.read_text(encoding="utf-8"))
    data["exists"] = True
    data["path"] = str(resolved)
    return data


def timestamp(line: str) -> float | None:
    cleaned = ANSI_RE.sub("", line).strip()
    match = TS_RE.match(cleaned)
    return float(match.group(1)) if match else None


def events_from_dmesg(text: str) -> list[Event]:
    events: list[Event] = []
    for raw_line in text.splitlines():
        ts = timestamp(raw_line)
        if ts is None:
            continue
        cleaned = ANSI_RE.sub("", raw_line).strip()
        for name, pattern in EVENT_PATTERNS:
            if pattern.search(cleaned):
                events.append(Event(name, ts, cleaned))
    return events


def first_time(events: list[Event], name: str) -> float | None:
    values = [event.timestamp for event in events if event.name == name]
    return min(values) if values else None


def count_events(events: list[Event], name: str) -> int:
    return sum(1 for event in events if event.name == name)


def delta(base_time: float | None, event_time: float | None) -> float | None:
    if base_time is None or event_time is None:
        return None
    return round((event_time - base_time) * 1000.0, 3)


def manifest_order(manifest: dict[str, Any]) -> str:
    live = manifest.get("live") or {}
    service_manager = live.get("service_manager") or {}
    return str(service_manager.get("order") or "")


def classify_case(case: CaseInput) -> dict[str, Any]:
    dmesg_path = repo_path(case.dmesg)
    manifest = load_json(case.manifest)
    if not dmesg_path.exists():
        return {
            "name": case.name,
            "exists": False,
            "dmesg": str(dmesg_path),
            "manifest": manifest,
        }
    text = read_text(case.dmesg)
    events = events_from_dmesg(text)
    first = {name: first_time(events, name) for name, _ in EVENT_PATTERNS}
    sysmon = first["sysmon_qmi"]
    cnss_diag = first["cnss_diag_netlink"]
    cnss_daemon = first["cnss_daemon_netlink"]
    service_notifier = first["service_notifier_180"]
    binder_failed = first["binder_transaction_failed"]
    counts = {name: count_events(events, name) for name, _ in EVENT_PATTERNS}
    return {
        "name": case.name,
        "exists": True,
        "dmesg": str(dmesg_path),
        "manifest_path": str(repo_path(case.manifest)),
        "decision": manifest.get("decision"),
        "pass": manifest.get("pass"),
        "order": manifest_order(manifest),
        "first": first,
        "counts": counts,
        "delta_ms": {
            "sysmon_to_service_notifier_180": delta(sysmon, service_notifier),
            "sysmon_to_cnss_diag": delta(sysmon, cnss_diag),
            "sysmon_to_cnss_daemon": delta(sysmon, cnss_daemon),
            "cnss_daemon_to_binder_failed": delta(cnss_daemon, binder_failed),
            "service_notifier_180_to_cnss_diag": delta(service_notifier, cnss_diag),
            "service_notifier_180_to_cnss_daemon": delta(service_notifier, cnss_daemon),
        },
        "focus_tail": [asdict(event) for event in events[-80:]],
    }


def classify(cases: list[dict[str, Any]]) -> tuple[str, bool, str, str]:
    by_name = {case["name"]: case for case in cases}
    v598 = by_name.get("v598-baseline-no-service-manager", {})
    v604 = by_name.get("v604b-cnss-first-delayed-service-manager", {})
    v603 = by_name.get("v603-qrtr-first-service-manager", {})
    v598_service_before_cnss = (
        (v598.get("delta_ms") or {}).get("service_notifier_180_to_cnss_diag") is not None
        and float((v598.get("delta_ms") or {}).get("service_notifier_180_to_cnss_diag")) > 0
    )
    v604_cnss_window_ms = (v604.get("delta_ms") or {}).get("sysmon_to_cnss_diag")
    v598_service_ms = (v598.get("delta_ms") or {}).get("sysmon_to_service_notifier_180")
    v604_had_long_enough_pre_cnss_window = (
        v604_cnss_window_ms is not None
        and v598_service_ms is not None
        and float(v604_cnss_window_ms) > float(v598_service_ms)
    )
    v604_service_missing = (v604.get("counts") or {}).get("service_notifier_180", 0) == 0
    v604_binder_failed = (v604.get("counts") or {}).get("binder_transaction_failed", 0) > 0
    v603_service_missing = (v603.get("counts") or {}).get("service_notifier_180", 0) == 0
    if v598_service_before_cnss and v604_had_long_enough_pre_cnss_window and v604_service_missing:
        return (
            "v605-service-notifier-pre-cnss-regression-classified",
            True,
            "V598 service-notifier 180 appeared before CNSS, while V604b had a longer pre-CNSS window but no service-notifier; short service-manager/CNSS ordering alone is not sufficient",
            "run a v102 no-service-manager baseline replay or inspect helper/runtime deltas before another service-manager timing tweak",
        )
    if v604_service_missing and v604_binder_failed and v603_service_missing:
        return (
            "v605-service-notifier-ordering-gap-persists",
            True,
            "V603 and V604b both miss service-notifier 180; V604b also keeps binder failures",
            "compare helper/runtime deltas against V598 before another live proof",
        )
    return (
        "v605-service-notifier-timing-review",
        True,
        "timing evidence did not match the expected classifier route",
        "inspect manifest and dmesg deltas manually",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    rows = []
    for case in manifest["cases"]:
        delta_ms = case.get("delta_ms") or {}
        counts = case.get("counts") or {}
        rows.append([
            case["name"],
            str(case.get("decision", "")),
            str(counts.get("service_notifier_180", 0)),
            str(counts.get("binder_transaction_failed", 0)),
            str(delta_ms.get("sysmon_to_service_notifier_180")),
            str(delta_ms.get("sysmon_to_cnss_diag")),
            str(delta_ms.get("service_notifier_180_to_cnss_diag")),
        ])
    return "\n".join([
        "# V605 Service-Notifier Timing Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        "",
        markdown_table([
            "case",
            "decision",
            "svc180",
            "binder_failed",
            "sysmon_to_svc180_ms",
            "sysmon_to_cnss_diag_ms",
            "svc180_to_cnss_diag_ms",
        ], rows),
        "",
    ])


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    cases = [classify_case(case) for case in DEFAULT_CASES]
    decision, pass_ok, reason, next_step = classify(cases)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "cases": cases,
        "device_commands_executed": False,
        "device_mutations": False,
        "daemon_start_executed": False,
        "wifi_bringup_executed": False,
        "external_ping_executed": False,
    }


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
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

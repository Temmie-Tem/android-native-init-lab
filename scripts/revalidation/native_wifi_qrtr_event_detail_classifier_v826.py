#!/usr/bin/env python3
"""V826 host-only QRTR event detail classifier.

V825 proved that encoded QRTR nameservice lookups produce service events below
HAL/connect.  The helper already captured event payload fields; V826 parses that
existing evidence without issuing any device command.
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


DEFAULT_OUT_DIR = Path("tmp/wifi/v826-qrtr-event-detail-classifier")
LATEST_POINTER = Path("tmp/wifi/latest-v826-qrtr-event-detail-classifier.txt")
DEFAULT_V825_MANIFEST = Path("tmp/wifi/v825-qrtr-encoded-matrix/manifest.json")

EVENT_KEY_RE = re.compile(
    r"^wifi_companion_qrtr_readback\.case_(?P<case>\d+)\.readback\.event\."
    r"(?P<event>\d+)\.(?P<field>[A-Za-z0-9_]+)$"
)

FORBIDDEN_ACTIONS = (
    "host-only; no bridge command",
    "no device command, reboot, bootloader handoff, boot image write, or partition write",
    "no QRTR socket open or QRTR/QMI packet transmission",
    "no service-manager, Wi-Fi HAL, scan/connect, credential use, DHCP, route, or external ping",
    "custom OSRC kernel flashing remains paused",
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v825-manifest", type=Path, default=DEFAULT_V825_MANIFEST)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    resolved = path if path.is_absolute() else repo_path(path)
    if not resolved.exists():
        return {"file": {"path": str(resolved), "exists": False}, "data": {}}
    try:
        data = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {"file": {"path": str(resolved), "exists": True}, "data": {}, "error": str(exc)}
    return {
        "file": {"path": str(resolved), "exists": True, "size": resolved.stat().st_size},
        "data": data if isinstance(data, dict) else {},
    }


def int_value(value: Any, default: int = 0) -> int:
    if value is None:
        return default
    try:
        return int(str(value), 0)
    except ValueError:
        return default


def v825_input(args: argparse.Namespace) -> dict[str, Any]:
    loaded = load_json(args.v825_manifest)
    data = loaded["data"]
    return {
        "file": loaded["file"],
        "decision": data.get("decision", ""),
        "pass": bool(data.get("pass")),
        "reason": data.get("reason", ""),
        "next_step": data.get("next_step", ""),
        "live_manifest": ((data.get("live") or {}).get("manifest")),
        "matrix": ((data.get("live") or {}).get("matrix") or {}),
        "guardrails": {
            "device_commands_executed": data.get("device_commands_executed"),
            "qmi_payload_executed": data.get("qmi_payload_executed"),
            "wifi_hal_start_executed": data.get("wifi_hal_start_executed"),
            "scan_connect_executed": data.get("scan_connect_executed"),
            "external_ping_executed": data.get("external_ping_executed"),
            "custom_kernel_flash_executed": data.get("custom_kernel_flash_executed"),
            "boot_image_write_executed": data.get("boot_image_write_executed"),
            "partition_write_executed": data.get("partition_write_executed"),
        },
    }


def annotated_manifest_path(v825: dict[str, Any]) -> Path | None:
    value = v825.get("live_manifest")
    if not value:
        return None
    return repo_path(Path(str(value)))


def case_rows(v825: dict[str, Any]) -> dict[int, dict[str, Any]]:
    rows = ((v825.get("matrix") or {}).get("rows") or [])
    result: dict[int, dict[str, Any]] = {}
    for row in rows:
        case = int_value(row.get("case"), -1)
        if case >= 0:
            result[case] = row
    return result


def extract_key_map(annotated: dict[str, Any]) -> dict[str, Any]:
    helper = ((annotated.get("live") or {}).get("helper_result") or {})
    keys = helper.get("keys") or {}
    return keys if isinstance(keys, dict) else {}


def extract_events(keys: dict[str, Any], rows: dict[int, dict[str, Any]]) -> list[dict[str, Any]]:
    event_map: dict[tuple[int, int], dict[str, Any]] = {}
    for key, value in keys.items():
        match = EVENT_KEY_RE.match(str(key))
        if not match:
            continue
        case = int(match.group("case"))
        event = int(match.group("event"))
        field = match.group("field")
        item = event_map.setdefault((case, event), {"case": case, "event": event})
        item[field] = value
    events: list[dict[str, Any]] = []
    for (case, event), item in sorted(event_map.items()):
        row = rows.get(case, {})
        normalized = {
            "case": case,
            "event": event,
            "label": row.get("label", ""),
            "lookup_service": int_value(row.get("service")),
            "lookup_instance": int_value(row.get("instance")),
            "cmd": int_value(item.get("cmd")),
            "type": item.get("type", ""),
            "service": int_value(item.get("service")),
            "instance": int_value(item.get("instance")),
            "node": int_value(item.get("node")),
            "port": int_value(item.get("port")),
            "from_family": int_value(item.get("from.family")),
            "from_node": int_value(item.get("from.node")),
            "from_port": int_value(item.get("from.port")),
            "empty": int_value(item.get("empty")),
            "bytes": int_value(item.get("bytes")),
        }
        normalized["service_event"] = (
            normalized["type"] == "new-server"
            and normalized["empty"] == 0
            and normalized["service"] != 0
        )
        normalized["matches_lookup"] = (
            normalized["service"] == normalized["lookup_service"]
            and normalized["instance"] == normalized["lookup_instance"]
        )
        events.append(normalized)
    return events


def build_checks(args: argparse.Namespace,
                 v825: dict[str, Any],
                 annotated: dict[str, Any],
                 events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    service_events = [event for event in events if event["service_event"]]
    visible_pairs = sorted({(event["service"], event["instance"], event["node"], event["port"]) for event in service_events})
    guardrails = v825["guardrails"]
    guardrails_ok = (
        guardrails.get("qmi_payload_executed") is False
        and guardrails.get("wifi_hal_start_executed") is False
        and guardrails.get("scan_connect_executed") is False
        and guardrails.get("external_ping_executed") is False
        and guardrails.get("custom_kernel_flash_executed") is False
        and guardrails.get("boot_image_write_executed") is False
        and guardrails.get("partition_write_executed") is False
    )
    return [
        {
            "name": "host-only-boundary",
            "status": "pass",
            "detail": "V826 reads only V825 evidence",
            "next_step": "keep V826 host-only",
        },
        {
            "name": "v825-input-ready",
            "status": "pass" if v825["pass"] and v825["decision"] == "v825-encoded-publication-visible" else "blocked",
            "detail": {"decision": v825["decision"], "pass": v825["pass"], "file": v825["file"]},
            "next_step": "complete V825 before V826",
        },
        {
            "name": "annotated-manifest-ready",
            "status": "pass" if bool(annotated) else "blocked",
            "detail": {"live_manifest": v825.get("live_manifest"), "has_data": bool(annotated)},
            "next_step": "restore V825 annotated manifest evidence",
        },
        {
            "name": "guardrails-preserved",
            "status": "pass" if guardrails_ok else "blocked",
            "detail": guardrails,
            "next_step": "discard V826 interpretation if V825 exceeded guardrails",
        },
        {
            "name": "event-details-present",
            "status": "pass" if events and service_events else "blocked",
            "detail": {"event_count": len(events), "service_event_count": len(service_events), "visible_pairs": visible_pairs},
            "next_step": "capture event details before selecting any continuation",
        },
        {
            "name": "visible-publication-classified",
            "status": "finding",
            "detail": {"service_events": service_events},
            "next_step": "use service/node/port details to select the next no-QMI continuation gate",
        },
    ]


def decide(checks: list[dict[str, Any]], events: list[dict[str, Any]]) -> tuple[str, bool, str, str]:
    blockers = [check["name"] for check in checks if check["status"] == "blocked"]
    if blockers:
        return (
            "v826-qrtr-event-detail-classifier-blocked",
            False,
            "blocked by " + ", ".join(blockers),
            "resolve host-only evidence blockers before live work",
        )
    service_events = [event for event in events if event["service_event"]]
    visible = ", ".join(
        f"{event['label']} {event['service']}/{event['instance']} node={event['node']} port={event['port']}"
        for event in service_events
    )
    return (
        "v826-qrtr-event-details-classified",
        True,
        f"visible QRTR services: {visible}",
        "plan V827 as a no-QMI continuation classifier for service-notifier 180 visibility versus WLFW absence",
    )


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    v825 = v825_input(args)
    annotated_path = annotated_manifest_path(v825)
    annotated_loaded = load_json(annotated_path) if annotated_path is not None else {"file": {}, "data": {}}
    annotated = annotated_loaded["data"]
    rows = case_rows(v825)
    keys = extract_key_map(annotated)
    events = extract_events(keys, rows)
    checks = build_checks(args, v825, annotated, events)
    decision, pass_ok, reason, next_step = decide(checks, events)
    if args.command == "plan":
        decision = "v826-qrtr-event-detail-classifier-plan-ready"
        reason = "plan-only; V825 evidence parser defined"
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "cycle": "v826",
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "v825": v825,
        "annotated_manifest": annotated_loaded["file"],
        "events": events,
        "service_events": [event for event in events if event["service_event"]],
        "empty_events": [event for event in events if event["empty"] == 1],
        "checks": checks,
        "device_commands_executed": False,
        "device_mutations": False,
        "custom_kernel_flash_executed": False,
        "boot_image_write_executed": False,
        "partition_write_executed": False,
        "qmi_payload_executed": False,
        "service_manager_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "forbidden_actions": FORBIDDEN_ACTIONS,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    check_rows = [
        [check["name"], check["status"], json.dumps(check["detail"], ensure_ascii=False, sort_keys=True), check["next_step"]]
        for check in manifest["checks"]
    ]
    event_rows = [
        [
            str(event["case"]),
            str(event["event"]),
            str(event["label"]),
            str(event["lookup_service"]),
            str(event["lookup_instance"]),
            str(event["type"]),
            str(event["service"]),
            str(event["instance"]),
            str(event["node"]),
            str(event["port"]),
            str(event["empty"]),
            str(event["service_event"]),
        ]
        for event in manifest["events"]
    ]
    return "\n".join([
        "# V826 QRTR Event Detail Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- qmi_payload_executed: `{manifest['qmi_payload_executed']}`",
        f"- wifi_hal_start_executed: `{manifest['wifi_hal_start_executed']}`",
        f"- scan_connect_executed: `{manifest['scan_connect_executed']}`",
        f"- external_ping_executed: `{manifest['external_ping_executed']}`",
        "",
        "## Checks",
        "",
        markdown_table(["check", "status", "detail", "next"], check_rows),
        "",
        "## Event Details",
        "",
        markdown_table(
            ["case", "event", "label", "lookup_service", "lookup_instance", "type", "service", "instance", "node", "port", "empty", "service_event"],
            event_rows,
        ) if event_rows else "- none",
        "",
        "## Guardrails",
        "",
        "\n".join(f"- {item}" for item in manifest["forbidden_actions"]),
        "",
    ])


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir.relative_to(repo_path("."))) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"service_events: {len(manifest['service_events'])}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"qmi_payload_executed: {manifest['qmi_payload_executed']}")
    print(f"wifi_hal_start_executed: {manifest['wifi_hal_start_executed']}")
    print(f"scan_connect_executed: {manifest['scan_connect_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""V1168 bounded PM-service callback-dispatch live gate.

This V1167 derivative keeps the same late pm-proxy action-branch gate and adds
uprobes below the state helper at 0x92dc.  It captures the client callback
record, resolved branch target, and pm-service maps so the target can be mapped
to a loaded binary region.  It does not start Wi-Fi HAL, scan/connect/link-up,
use credentials, run DHCP/routes, external ping, write boot/partitions, or
flash.
"""

from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

import native_wifi_pm_action_branch_live_v1167 as v1167
from a90_kernel_tools import markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1168-pm-callback-dispatch-live")
LATEST_POINTER = Path("tmp/wifi/latest-v1168-pm-callback-dispatch-live.txt")
DEFAULT_WORK_DIR = "/cache/a90-runtime/v1168"
DEFAULT_CHILD_SCRIPT = "/cache/a90-runtime/v1168/pm-callback-dispatch-child.sh"
DEFAULT_COLLECTOR_SCRIPT = "/cache/a90-runtime/v1168/pm-callback-dispatch-collector.sh"
DEFAULT_CHILD_OUTPUT = "/cache/a90-runtime/v1168/pm-callback-dispatch-output.txt"
PROOF_PREFIX = "/tmp/a90-v1168-"
DEFAULT_V1167_MANIFEST = Path("tmp/wifi/v1167-pm-action-branch-live-after-v490/manifest.json")

CALLBACK_EVENT_SPECS = (
    ("pm_state_helper_client_node", "service", "93bc", "entry=%x19 node=%x21 head=%x23 state=%x20"),
    ("pm_state_helper_client_callback_call", "service", "93c4", "entry=%x19 node=%x21 client_record=%x0 state=%x1"),
    ("pm_client_callback_entry", "service", "8630", "client_record=%x0 state=%x1"),
    ("pm_client_callback_target_ready", "service", "8640", "target=%x0 vtable=%x9 state=%x1"),
    ("pm_client_callback_branch", "service", "8644", "target=%x0 vtable=%x9 callback=%x2 state=%x1"),
)
CALLBACK_LABELS = {label for label, _binary_key, _offset, _fetch in CALLBACK_EVENT_SPECS}
VALUE_RE = re.compile(
    r"\b(?P<key>entry|node|head|state|client_record|target|vtable|callback)="
    r"(?P<value>0x[0-9A-Fa-f]+|-?[0-9]+)"
)
MAP_RE = re.compile(
    r"^(?P<start>[0-9A-Fa-f]+)-(?P<end>[0-9A-Fa-f]+)\s+"
    r"(?P<perms>\S+)\s+(?P<offset>[0-9A-Fa-f]+)\s+\S+\s+\S+\s*(?P<path>.*)$"
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def intish(value: Any, default: int = 0) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    try:
        return int(str(value).strip(), 0)
    except (TypeError, ValueError):
        return default


def _install_callback_event_specs() -> None:
    v1106 = v1167.v1165.v1143.v1139.v1113.v1106
    existing = {label for label, _binary_key, _offset, _fetch in v1106.EVENT_SPECS}
    additions = tuple(spec for spec in CALLBACK_EVENT_SPECS if spec[0] not in existing)
    if additions:
        v1106.EVENT_SPECS = tuple(v1106.EVENT_SPECS) + additions
    v1106.SERVER_EVENT_LABELS = {
        label
        for label, binary_key, _offset, _fetch in v1106.EVENT_SPECS
        if binary_key == "service"
    }
    v1106.RETURN_EVENT_LABELS = {
        label
        for label, _binary_key, _offset, _fetch in v1106.EVENT_SPECS
        if label.endswith("_ret")
    }


_base_tracefs_collector_script_v1165 = v1167.v1165.tracefs_collector_script_v1165
_base_parse_tracefs_output_v1167 = v1167.parse_tracefs_output_v1167


def tracefs_collector_script_v1168(args: Any) -> str:
    script = _base_tracefs_collector_script_v1165(args)
    old = "sample_pm_service_threads final\n$BB sleep 1\necho trace_lines_begin"
    new = """sample_pm_service_threads final
pm_pid=$(find_pm_service_pid || true)
echo pm_service_maps_begin
if $BB test -n "$pm_pid" && $BB test -r "/proc/$pm_pid/maps"; then
  $BB cat "/proc/$pm_pid/maps" 2>/dev/null || true
fi
echo pm_service_maps_end
$BB sleep 1
echo trace_lines_begin"""
    if old not in script:
        raise RuntimeError("V1106 collector maps insertion point changed")
    return script.replace(old, new, 1)


def _trace_match(line: str) -> tuple[str, str] | None:
    match = v1167.v1165.v1143.v1139.v1113.v1106.TRACE_LINE_RE.match(line)
    if not match:
        return None
    return match.group("comm").strip(), match.group("label")


def _value_map(line: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for match in VALUE_RE.finditer(line):
        values[match.group("key")] = match.group("value")
    return values


def collect_section(text: str, begin: str, end: str) -> list[str]:
    lines: list[str] = []
    in_section = False
    for line in text.splitlines():
        if line.strip() == begin:
            in_section = True
            continue
        if line.strip() == end:
            in_section = False
            continue
        if in_section:
            lines.append(line.rstrip())
    return lines


def parse_maps(text: str) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for line in collect_section(text, "pm_service_maps_begin", "pm_service_maps_end"):
        match = MAP_RE.match(line)
        if not match:
            continue
        entries.append({
            "start": int(match.group("start"), 16),
            "end": int(match.group("end"), 16),
            "perms": match.group("perms"),
            "offset": int(match.group("offset"), 16),
            "path": match.group("path").strip(),
            "line": line,
        })
    return entries


def map_pointer(pointer: int, maps: list[dict[str, Any]]) -> dict[str, Any]:
    for entry in maps:
        if entry["start"] <= pointer < entry["end"]:
            return {
                "pointer": hex(pointer),
                "path": entry["path"],
                "perms": entry["perms"],
                "map_start": hex(entry["start"]),
                "map_end": hex(entry["end"]),
                "map_offset": hex(entry["offset"]),
                "file_offset": hex(entry["offset"] + pointer - entry["start"]),
            }
    return {"pointer": hex(pointer), "path": "", "perms": "", "file_offset": ""}


def parse_callback_dispatch(text: str) -> dict[str, Any]:
    trace_lines = v1167.v1165.v1143.v1139.v1113.v1106.collect_trace_lines(text)
    maps = parse_maps(text)
    events: list[dict[str, Any]] = []
    by_label: dict[str, int] = {label: 0 for label in sorted(CALLBACK_LABELS)}
    by_comm: dict[str, dict[str, int]] = {}
    for line in trace_lines:
        matched = _trace_match(line)
        if not matched:
            continue
        comm, label = matched
        if label not in CALLBACK_LABELS:
            continue
        values = _value_map(line)
        events.append({"comm": comm, "label": label, "values": values, "line": line.strip()})
        by_label[label] = by_label.get(label, 0) + 1
        by_comm.setdefault(comm, {})
        by_comm[comm][label] = by_comm[comm].get(label, 0) + 1

    callback_values = [
        intish(event["values"].get("callback"))
        for event in events
        if event["label"] == "pm_client_callback_branch"
        and "callback" in event["values"]
    ]
    mapped_callbacks = [map_pointer(value, maps) for value in callback_values]
    state_values = [
        intish(event["values"].get("state"))
        for event in events
        if "state" in event["values"]
    ]
    client_records = sorted({
        event["values"].get("client_record", "")
        for event in events
        if event["values"].get("client_record")
    })
    return {
        "event_specs": [
            {"label": label, "binary_key": binary_key, "offset": offset, "fetch": fetch}
            for label, binary_key, offset, fetch in CALLBACK_EVENT_SPECS
        ],
        "events": events[:100],
        "event_count": len(events),
        "by_label": by_label,
        "by_comm": by_comm,
        "maps_count": len(maps),
        "maps_sample": [entry["line"] for entry in maps[:24]],
        "callback_values": [hex(value) for value in callback_values],
        "mapped_callbacks": mapped_callbacks,
        "state_values": state_values,
        "state2_seen": 2 in state_values,
        "client_records": client_records,
        "callback_branch_seen": bool(callback_values),
    }


def parse_tracefs_output_v1168(text: str) -> dict[str, Any]:
    parsed = _base_parse_tracefs_output_v1167(text)
    parsed["pm_callback_dispatch"] = parse_callback_dispatch(text)
    return parsed


def patch_defaults() -> None:
    v1167.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    v1167.LATEST_POINTER = LATEST_POINTER
    v1167.DEFAULT_WORK_DIR = DEFAULT_WORK_DIR
    v1167.DEFAULT_CHILD_SCRIPT = DEFAULT_CHILD_SCRIPT
    v1167.DEFAULT_COLLECTOR_SCRIPT = DEFAULT_COLLECTOR_SCRIPT
    v1167.DEFAULT_CHILD_OUTPUT = DEFAULT_CHILD_OUTPUT
    v1167.PROOF_PREFIX = PROOF_PREFIX
    _install_callback_event_specs()
    v1167.v1165.tracefs_collector_script_v1165 = tracefs_collector_script_v1168
    v1167.parse_tracefs_output_v1167 = parse_tracefs_output_v1168
    v1167.patch_defaults()


def tracefs(manifest: dict[str, Any]) -> dict[str, Any]:
    return v1167.tracefs(manifest)


def callback_dispatch(manifest: dict[str, Any]) -> dict[str, Any]:
    value = tracefs(manifest).get("pm_callback_dispatch") or {}
    return value if isinstance(value, dict) else {}


def late_polls(manifest: dict[str, Any]) -> dict[str, str]:
    return v1167.late_polls(manifest)


def _poll_values(polls: dict[str, str], suffix: str) -> list[int]:
    values: list[int] = []
    for key, value in sorted(polls.items()):
        if key.endswith(suffix):
            values.append(intish(value))
    return values


def decide_v1168(args: Any, manifest: dict[str, Any]) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return (
            "v1168-pm-callback-dispatch-plan-ready",
            True,
            "plan-only; no device mutation, PM actor, mdm_helper, CNSS daemon, reboot, or Wi-Fi action executed",
            "run bounded callback-dispatch live with helper v217 and explicit allow flags",
        )

    base_decision, base_pass, base_reason, base_next = v1167.decide_v1167(args, manifest)
    dispatch = callback_dispatch(manifest)
    polls = late_polls(manifest)
    esoc_seen = any(value > 0 for value in _poll_values(polls, "per_mgr_subsys_esoc0_count"))
    if not base_pass:
        return (
            base_decision.replace("v1167", "v1168", 1),
            False,
            base_reason,
            base_next,
        )
    if not dispatch.get("event_count"):
        return (
            "v1168-callback-dispatch-events-missing",
            False,
            f"dispatch={dispatch}",
            "verify V1168 uprobe event registration and callback offsets before retry",
        )
    if esoc_seen:
        return (
            "v1168-callback-dispatch-esoc0-advanced",
            True,
            f"dispatch={dispatch}",
            "preserve evidence before any Wi-Fi HAL or scan/connect gate",
        )
    if dispatch.get("callback_branch_seen"):
        return (
            "v1168-callback-branch-dispatched-but-no-esoc0",
            True,
            f"dispatch={dispatch}",
            "classify the mapped callback target and trace inside that target if it is vendor code",
        )
    if dispatch.get("by_label", {}).get("pm_state_helper_client_callback_call", 0):
        return (
            "v1168-callback-call-prepared-but-no-branch",
            True,
            f"dispatch={dispatch}",
            "trace the callback wrapper between 0x8630 and 0x8644",
        )
    return (
        "v1168-state-helper-client-list-empty-or-skipped",
        True,
        f"dispatch={dispatch}",
        "classify PM-service client registration list content before state=2",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    base = v1167.render_summary(manifest).replace(
        "# V1167 PM-Service Action Branch Live",
        "# V1168 PM-Service Callback Dispatch Live",
        1,
    )
    dispatch = callback_dispatch(manifest)
    rows = [
        ["event_count", dispatch.get("event_count", "")],
        ["by_label", json.dumps(dispatch.get("by_label", {}), sort_keys=True)],
        ["by_comm", json.dumps(dispatch.get("by_comm", {}), sort_keys=True)],
        ["maps_count", dispatch.get("maps_count", "")],
        ["callback_values", json.dumps(dispatch.get("callback_values", []))],
        ["mapped_callbacks", json.dumps(dispatch.get("mapped_callbacks", []), sort_keys=True)],
        ["state_values", json.dumps(dispatch.get("state_values", []))],
        ["state2_seen", dispatch.get("state2_seen", "")],
        ["client_records", json.dumps(dispatch.get("client_records", []))],
        ["callback_branch_seen", dispatch.get("callback_branch_seen", "")],
    ]
    specs = [
        [item.get("label", ""), item.get("offset", ""), item.get("fetch", "")]
        for item in dispatch.get("event_specs", [])
    ]
    return base + "\n".join([
        "",
        "## V1168 PM-Service Callback Dispatch",
        "",
        markdown_table(["key", "value"], rows),
        "",
        "## V1168 Event Specs",
        "",
        markdown_table(["label", "offset", "fetch"], specs),
        "",
    ])


def main() -> int:
    patch_defaults()
    args = v1167.v1165.v1143.v1139.v1113.v1106.parse_args()
    v1167.v1165.v1143.v1139.v1113.set_global_defaults(args)
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = v1167.v1165.v1143.v1139.v1113.v1106.build_manifest(args, store)
    manifest["base_v1167_decision"] = manifest.get("decision", "")
    manifest["cycle"] = "v1168"
    manifest["generated_at"] = now_iso()
    manifest["v1167_manifest"] = str(DEFAULT_V1167_MANIFEST)
    decision, passed, reason, next_step = decide_v1168(args, manifest)
    manifest.update({"decision": decision, "pass": passed, "reason": reason, "next_step": next_step})

    fw = v1167.v1165.v1143.v1139.global_firmware(manifest)
    values = v1167.v1165.v1143.v1139.contract(manifest)
    post = v1167.v1165.v1143.v1139.post_pm(manifest)
    lower = v1167.v1165.v1143.lower_trace(manifest)
    late = v1167.v1165.late_per_proxy(manifest)
    manifest["firmware_mounts_executed"] = bool(fw.get("mount_results"))
    manifest["global_modem_holder_opened"] = bool(fw.get("holder_opened"))
    manifest["reboot_executed"] = bool(fw.get("reboot_cleanup"))
    manifest["post_pm_mdm_helper_executed"] = post.get("exec_attempted") == "1"
    manifest["post_pm_mdm_helper_lower_trace_emitted"] = lower.get("begin") == "1"
    manifest["late_per_proxy_started"] = late.get("started") == "1"
    manifest["cnss_daemon_start_executed"] = values.get("cnss_daemon_start_executed") == "1"
    manifest["wifi_hal_start_executed"] = (
        values.get("wifi_hal_start_executed") == "1"
        or post.get("wifi_hal_start_executed") == "1"
        or lower.get("wifi_hal_start_executed") == "1"
    )
    manifest["scan_connect_executed"] = (
        values.get("scan_connect_linkup") == "1"
        or post.get("scan_connect_linkup") == "1"
        or lower.get("scan_connect_linkup") == "1"
    )
    manifest["credential_use_executed"] = lower.get("credentials") == "1"
    manifest["dhcp_route_executed"] = lower.get("dhcp_routing") == "1"
    manifest["external_ping_executed"] = (
        values.get("external_ping") == "1"
        or post.get("external_ping") == "1"
        or lower.get("external_ping") == "1"
    )
    manifest["wifi_bringup_executed"] = False

    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"firmware_mounts_executed: {manifest['firmware_mounts_executed']}")
    print(f"global_modem_holder_opened: {manifest['global_modem_holder_opened']}")
    print(f"post_pm_mdm_helper_executed: {manifest['post_pm_mdm_helper_executed']}")
    print(f"post_pm_mdm_helper_lower_trace_emitted: {manifest['post_pm_mdm_helper_lower_trace_emitted']}")
    print(f"late_per_proxy_started: {manifest['late_per_proxy_started']}")
    print(f"tracefs_write_executed: {manifest['tracefs_write_executed']}")
    print(f"cnss_daemon_start_executed: {manifest['cnss_daemon_start_executed']}")
    print(f"wifi_hal_start_executed: {manifest['wifi_hal_start_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    print(f"manifest: {store.run_dir / 'manifest.json'}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""V1177 bounded PM dependency-flag live gate.

This V1175 derivative traces the PM-service state-0 dependency path around the
state-2 dependency flag.  It verifies whether native arms the dependency flag
only after the first state-2 ack has already skipped the dependency/eSoC branch.
It does not start Wi-Fi HAL, scan/connect/link-up, use credentials, run
DHCP/routes, external ping, write boot/partitions, or flash.
"""

from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

import native_wifi_pm_ack_fd_target_live_v1175 as v1175
from a90_kernel_tools import markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1177-pm-dependency-flag-live")
LATEST_POINTER = Path("tmp/wifi/latest-v1177-pm-dependency-flag-live.txt")
DEFAULT_WORK_DIR = "/cache/a90-runtime/v1177"
DEFAULT_CHILD_SCRIPT = "/cache/a90-runtime/v1177/pm-dependency-flag-child.sh"
DEFAULT_COLLECTOR_SCRIPT = "/cache/a90-runtime/v1177/pm-dependency-flag-collector.sh"
DEFAULT_CHILD_OUTPUT = "/cache/a90-runtime/v1177/pm-dependency-flag-output.txt"
PROOF_PREFIX = "/tmp/a90-v1177-"
DEFAULT_V1176_MANIFEST = Path("tmp/wifi/v1176-pm-state3-dependency-classifier/manifest.json")
DEP_EVENT_SPECS = (
    ("pm_dep_state0_entry", "service", "8a10", "peripheral=%x20 current_state=%x8"),
    ("pm_dep_state0_dependency_present", "service", "8a74", "peripheral=%x20 dependency=%x22"),
    ("pm_dep_state0_dependency_state_first", "service", "8a94", "dependency_state=%x22"),
    ("pm_dep_state0_dependency_state_second", "service", "8ab8", "dependency_state=%x22"),
    ("pm_dep_state0_dependency_state0_call", "service", "8b04", "dependency=%x0 state=%x1"),
    ("pm_dep_state0_wait_call", "service", "8b30", "dependency_wait=%x0 wait_arg=%x1"),
    ("pm_dep_state0_wait_return", "service", "8b34", "peripheral=%x20"),
    ("pm_dep_state0_post_wait_state", "service", "8b78", "dependency_state=%x25"),
    ("pm_dep_state0_flag_set", "service", "8b94", "peripheral=%x20 flag_value=%x24"),
    ("pm_dep_state2_dependency_state2_call", "service", "8980", "dependency=%x0 state=%x1"),
)
DEP_LABELS = {label for label, _binary_key, _offset, _fetch in DEP_EVENT_SPECS}
VALUE_RE = re.compile(
    r"\b(?P<key>peripheral|current_state|dependency|dependency_state|state|"
    r"dependency_wait|wait_arg|flag_value)="
    r"(?P<value>0x[0-9A-Fa-f]+|-?[0-9]+)"
)
TIME_RE = re.compile(r"\s(?P<time>\d+\.\d+):\s+(?P<label>[A-Za-z0-9_]+):")
_base_tracefs_collector_script_v1175 = v1175.tracefs_collector_script_v1175
_base_parse_tracefs_output_v1175 = v1175.parse_tracefs_output_v1175


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


def _tracebase() -> Any:
    return v1175.v1174._tracebase()


def _install_dep_event_specs() -> None:
    tracebase = _tracebase()
    existing = {label for label, _binary_key, _offset, _fetch in tracebase.EVENT_SPECS}
    additions = tuple(spec for spec in DEP_EVENT_SPECS if spec[0] not in existing)
    if additions:
        tracebase.EVENT_SPECS = tuple(tracebase.EVENT_SPECS) + additions
    tracebase.SERVER_EVENT_LABELS = {
        label
        for label, binary_key, _offset, _fetch in tracebase.EVENT_SPECS
        if binary_key == "service"
    }
    tracebase.RETURN_EVENT_LABELS = {
        label
        for label, _binary_key, _offset, _fetch in tracebase.EVENT_SPECS
        if label.endswith("_ret")
    }


def tracefs_collector_script_v1177(args: Any) -> str:
    return _base_tracefs_collector_script_v1175(args)


def _trace_match(line: str) -> tuple[str, str] | None:
    match = _tracebase().TRACE_LINE_RE.match(line)
    if not match:
        return None
    return match.group("comm").strip(), match.group("label")


def _value_map(line: str) -> dict[str, str]:
    return {match.group("key"): match.group("value") for match in VALUE_RE.finditer(line)}


def _line_time(line: str) -> float | None:
    match = TIME_RE.search(line)
    return float(match.group("time")) if match else None


def parse_dependency_trace(text: str) -> dict[str, Any]:
    trace_lines = _tracebase().collect_trace_lines(text)
    events: list[dict[str, Any]] = []
    by_label: dict[str, int] = {label: 0 for label in sorted(DEP_LABELS)}
    by_comm: dict[str, dict[str, int]] = {}
    for line in trace_lines:
        matched = _trace_match(line)
        if not matched:
            continue
        comm, label = matched
        if label not in DEP_LABELS:
            continue
        values = _value_map(line)
        events.append({
            "comm": comm,
            "label": label,
            "values": values,
            "time": _line_time(line),
            "line": line.strip(),
        })
        by_label[label] = by_label.get(label, 0) + 1
        by_comm.setdefault(comm, {})
        by_comm[comm][label] = by_comm[comm].get(label, 0) + 1

    flag_values = [
        intish(event["values"].get("flag_value"), -1)
        for event in events
        if event["label"] == "pm_dep_state0_flag_set"
    ]
    state2_dependency_calls = [
        event
        for event in events
        if event["label"] == "pm_dep_state2_dependency_state2_call"
    ]
    state0_dependency_calls = [
        event
        for event in events
        if event["label"] == "pm_dep_state0_dependency_state0_call"
    ]
    first_flag_time = next(
        (event.get("time") for event in events if event["label"] == "pm_dep_state0_flag_set" and event.get("time") is not None),
        None,
    )
    return {
        "event_specs": [
            {"label": label, "binary_key": binary_key, "offset": offset, "fetch": fetch}
            for label, binary_key, offset, fetch in DEP_EVENT_SPECS
        ],
        "events": events[:160],
        "event_count": len(events),
        "by_label": by_label,
        "by_comm": by_comm,
        "flag_values": flag_values,
        "state0_dependency_call_count": len(state0_dependency_calls),
        "state2_dependency_call_count": len(state2_dependency_calls),
        "state0_flag_set_seen": bool(flag_values),
        "state0_flag_value_one_seen": 1 in flag_values,
        "state2_dependency_call_seen": bool(state2_dependency_calls),
        "first_flag_set_time": first_flag_time,
    }


def parse_tracefs_output_v1177(text: str) -> dict[str, Any]:
    parsed = _base_parse_tracefs_output_v1175(text)
    parsed["pm_dependency_flag"] = parse_dependency_trace(text)
    return parsed


def patch_defaults() -> None:
    v1175.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    v1175.LATEST_POINTER = LATEST_POINTER
    v1175.DEFAULT_WORK_DIR = DEFAULT_WORK_DIR
    v1175.DEFAULT_CHILD_SCRIPT = DEFAULT_CHILD_SCRIPT
    v1175.DEFAULT_COLLECTOR_SCRIPT = DEFAULT_COLLECTOR_SCRIPT
    v1175.DEFAULT_CHILD_OUTPUT = DEFAULT_CHILD_OUTPUT
    v1175.PROOF_PREFIX = PROOF_PREFIX
    v1175.patch_defaults()
    _install_dep_event_specs()
    v1175.tracefs_collector_script_v1175 = tracefs_collector_script_v1177
    v1175.parse_tracefs_output_v1175 = parse_tracefs_output_v1177
    v1175.v1174.v1173.v1172.v1171.v1170.v1169.tracefs_collector_script_v1169 = tracefs_collector_script_v1177
    v1175.v1174.v1173.v1172.v1171.v1170.parse_tracefs_output_v1170 = parse_tracefs_output_v1177
    v1175.v1174.v1173.v1172.v1171.v1170.v1169.v1168.tracefs_collector_script_v1168 = tracefs_collector_script_v1177
    v1175.v1174.v1173.v1172.v1171.v1170.v1169.parse_tracefs_output_v1169 = parse_tracefs_output_v1177
    v1175.v1174.v1173.v1172.v1171.v1170.v1169.v1168.v1167.v1165.tracefs_collector_script_v1165 = (
        tracefs_collector_script_v1177
    )
    v1175.v1174.v1173.v1172.v1171.v1170.v1169.v1168.parse_tracefs_output_v1168 = parse_tracefs_output_v1177
    v1175.v1174.v1173.v1172.v1171.v1170.v1169.v1168.v1167.parse_tracefs_output_v1167 = parse_tracefs_output_v1177
    v1175.v1174.v1173.v1172.v1171.v1170.v1169.v1168.v1167.v1165.v1143.v1139.v1113.v1106.tracefs_collector_script = (
        tracefs_collector_script_v1177
    )
    v1175.v1174.v1173.v1172.v1171.v1170.v1169.v1168.v1167.v1165.v1143.v1139.v1113.v1106.parse_tracefs_output = (
        parse_tracefs_output_v1177
    )


def tracefs(manifest: dict[str, Any]) -> dict[str, Any]:
    return v1175.tracefs(manifest)


def dependency_flag(manifest: dict[str, Any]) -> dict[str, Any]:
    value = tracefs(manifest).get("pm_dependency_flag") or {}
    return value if isinstance(value, dict) else {}


def pm_ack_body(manifest: dict[str, Any]) -> dict[str, Any]:
    return v1175.pm_ack_body(manifest)


def decide_v1177(args: Any, manifest: dict[str, Any]) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return (
            "v1177-pm-dependency-flag-plan-ready",
            True,
            "plan-only; no device mutation, PM actor, mdm_helper, CNSS daemon, reboot, or Wi-Fi action executed",
            "run bounded PM dependency-flag live with helper v217 and explicit allow flags",
        )

    base_decision, base_pass, base_reason, base_next = v1175.decide_v1175(args, manifest)
    dep = dependency_flag(manifest)
    body = pm_ack_body(manifest)
    if not base_pass:
        return (
            base_decision.replace("v1175", "v1177", 1),
            False,
            base_reason,
            base_next,
        )
    if not dep.get("event_count"):
        return (
            "v1177-dependency-trace-missing",
            True,
            f"dep={dep}",
            "verify dependency branch offsets or extend trace window before changing PM order",
        )
    if dep.get("state2_dependency_call_seen"):
        return (
            "v1177-state2-dependency-call-observed",
            True,
            f"dep={dep}",
            "move to bounded eSoC/MHI/WLFW publication gate",
        )
    if dep.get("state0_flag_value_one_seen") and 0 in body.get("dependency_flag_values", []):
        return (
            "v1177-state0-arms-dependency-after-state2-gap",
            True,
            f"body={body} dep={dep}",
            "repair PM event ordering so dependency flag is armed before the state-2 ack path",
        )
    if dep.get("state0_flag_set_seen"):
        return (
            "v1177-state0-flag-set-unclassified",
            True,
            f"body={body} dep={dep}",
            "inspect flag value and invocation order before changing PM event ordering",
        )
    return (
        "v1177-dependency-flag-not-armed",
        True,
        f"body={body} dep={dep}",
        "trace earlier PM state-0/reset path or compare Android state order",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    base = v1175.render_summary(manifest).replace(
        "# V1175 PM Ack FD Target Live",
        "# V1177 PM Dependency Flag Live",
        1,
    )
    dep = dependency_flag(manifest)
    body = pm_ack_body(manifest)
    rows = [
        ["event_count", dep.get("event_count", "")],
        ["by_label", json.dumps(dep.get("by_label", {}), sort_keys=True)],
        ["body_dependency_flag_values", json.dumps(body.get("dependency_flag_values", []))],
        ["body_core_states", json.dumps(body.get("core_states", []))],
        ["state0_dependency_call_count", dep.get("state0_dependency_call_count", "")],
        ["state2_dependency_call_count", dep.get("state2_dependency_call_count", "")],
        ["flag_values", json.dumps(dep.get("flag_values", []))],
        ["state0_flag_set_seen", dep.get("state0_flag_set_seen", "")],
        ["state0_flag_value_one_seen", dep.get("state0_flag_value_one_seen", "")],
        ["state2_dependency_call_seen", dep.get("state2_dependency_call_seen", "")],
        ["first_flag_set_time", dep.get("first_flag_set_time", "")],
    ]
    specs = [
        [item.get("label", ""), item.get("offset", ""), item.get("fetch", "")]
        for item in dep.get("event_specs", [])
    ]
    return base + "\n".join([
        "",
        "## V1177 PM Dependency Flag",
        "",
        markdown_table(["key", "value"], rows),
        "",
        "## V1177 Event Specs",
        "",
        markdown_table(["label", "offset", "fetch"], specs),
        "",
    ])


def main() -> int:
    patch_defaults()
    args = v1175.v1174.v1173.v1172.v1171.v1170.v1169.v1168.v1167.v1165.v1143.v1139.v1113.v1106.parse_args()
    v1175.v1174.v1173.v1172.v1171.v1170.v1169.v1168.v1167.v1165.v1143.v1139.v1113.set_global_defaults(args)
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = v1175.v1174.v1173.v1172.v1171.v1170.v1169.v1168.v1167.v1165.v1143.v1139.v1113.v1106.build_manifest(args, store)
    manifest["base_v1175_decision"] = manifest.get("decision", "")
    manifest["cycle"] = "v1177"
    manifest["generated_at"] = now_iso()
    manifest["v1176_manifest"] = str(DEFAULT_V1176_MANIFEST)
    decision, passed, reason, next_step = decide_v1177(args, manifest)
    manifest.update({"decision": decision, "pass": passed, "reason": reason, "next_step": next_step})

    fw = v1175.v1174.v1173.v1172.v1171.v1170.v1169.v1168.v1167.v1165.v1143.v1139.global_firmware(manifest)
    values = v1175.v1174.v1173.v1172.v1171.v1170.v1169.v1168.v1167.v1165.v1143.v1139.contract(manifest)
    post = v1175.v1174.v1173.v1172.v1171.v1170.v1169.v1168.v1167.v1165.v1143.v1139.post_pm(manifest)
    lower = v1175.v1174.v1173.v1172.v1171.v1170.v1169.v1168.v1167.v1165.v1143.lower_trace(manifest)
    late = v1175.v1174.v1173.v1172.v1171.v1170.v1169.v1168.v1167.v1165.late_per_proxy(manifest)
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
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())

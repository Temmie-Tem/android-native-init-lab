#!/usr/bin/env python3
"""V1167 bounded PM-service action-branch live gate.

This V1165 derivative adds narrow pm-service uprobes for the successful-connect
branch classified in V1166.  It keeps the same bounded late pm-proxy gate and
does not start Wi-Fi HAL, scan/connect/link-up, use credentials, run
DHCP/routes, external ping, write boot/partitions, or flash.
"""

from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

import native_wifi_late_per_proxy_actionability_live_v1165 as v1165
from a90_kernel_tools import markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1167-pm-action-branch-live")
LATEST_POINTER = Path("tmp/wifi/latest-v1167-pm-action-branch-live.txt")
DEFAULT_WORK_DIR = "/cache/a90-runtime/v1167"
DEFAULT_CHILD_SCRIPT = "/cache/a90-runtime/v1167/pm-action-branch-child.sh"
DEFAULT_COLLECTOR_SCRIPT = "/cache/a90-runtime/v1167/pm-action-branch-collector.sh"
DEFAULT_CHILD_OUTPUT = "/cache/a90-runtime/v1167/pm-action-branch-output.txt"
PROOF_PREFIX = "/tmp/a90-v1167-"
DEFAULT_V1166_MANIFEST = Path("tmp/wifi/v1166-pm-action-branch-classifier/manifest.json")

ACTION_BRANCH_EVENT_SPECS = (
    ("pm_server_connect_vote_count_before", "service", "9738", "voters_before=%x8"),
    ("pm_server_connect_vote_count_after_store", "service", "9740", "voters_before=%x8 voters_after=%x9"),
    ("pm_server_connect_reconnect_flag_check", "service", "9748", "reconnect_flag=%x8"),
    ("pm_server_connect_powerup_state_call", "service", "97dc", "entry=%x0 state=%x1"),
    ("pm_server_state_transition_entry", "service", "92dc", "entry=%x0 state=%x1"),
)
ACTION_LABELS = {label for label, _binary_key, _offset, _fetch in ACTION_BRANCH_EVENT_SPECS}
VALUE_RE = re.compile(
    r"\b(?P<key>voters_before|voters_after|reconnect_flag|entry|state)="
    r"(?P<value>0x[0-9A-Fa-f]+|-?[0-9]+)"
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


def _install_action_branch_event_specs() -> None:
    v1106 = v1165.v1143.v1139.v1113.v1106
    existing = {label for label, _binary_key, _offset, _fetch in v1106.EVENT_SPECS}
    additions = tuple(spec for spec in ACTION_BRANCH_EVENT_SPECS if spec[0] not in existing)
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


_base_parse_tracefs_output_v1165 = v1165.parse_tracefs_output_v1165


def _trace_match(line: str) -> tuple[str, str] | None:
    match = v1165.v1143.v1139.v1113.v1106.TRACE_LINE_RE.match(line)
    if not match:
        return None
    return match.group("comm").strip(), match.group("label")


def _value_map(line: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for match in VALUE_RE.finditer(line):
        values[match.group("key")] = match.group("value")
    return values


def parse_action_branch(text: str) -> dict[str, Any]:
    trace_lines = v1165.v1143.v1139.v1113.v1106.collect_trace_lines(text)
    events: list[dict[str, Any]] = []
    by_comm: dict[str, dict[str, int]] = {}
    by_label: dict[str, int] = {label: 0 for label in sorted(ACTION_LABELS)}
    for line in trace_lines:
        matched = _trace_match(line)
        if not matched:
            continue
        comm, label = matched
        if label not in ACTION_LABELS:
            continue
        values = _value_map(line)
        event = {
            "comm": comm,
            "label": label,
            "values": values,
            "line": line.strip(),
        }
        events.append(event)
        by_label[label] = by_label.get(label, 0) + 1
        by_comm.setdefault(comm, {})
        by_comm[comm][label] = by_comm[comm].get(label, 0) + 1

    vote_before = [
        intish(event["values"].get("voters_before"))
        for event in events
        if event["label"] in {"pm_server_connect_vote_count_before", "pm_server_connect_vote_count_after_store"}
        and "voters_before" in event["values"]
    ]
    vote_after = [
        intish(event["values"].get("voters_after"))
        for event in events
        if event["label"] == "pm_server_connect_vote_count_after_store"
        and "voters_after" in event["values"]
    ]
    reconnect_flags = [
        intish(event["values"].get("reconnect_flag"))
        for event in events
        if event["label"] == "pm_server_connect_reconnect_flag_check"
        and "reconnect_flag" in event["values"]
    ]
    state_calls = [
        {
            "comm": event["comm"],
            "state": intish(event["values"].get("state")),
            "entry": event["values"].get("entry", ""),
            "label": event["label"],
        }
        for event in events
        if event["label"] in {"pm_server_connect_powerup_state_call", "pm_server_state_transition_entry"}
        and "state" in event["values"]
    ]
    state2_calls = [event for event in state_calls if event["state"] == 2]
    return {
        "event_specs": [
            {"label": label, "binary_key": binary_key, "offset": offset, "fetch": fetch}
            for label, binary_key, offset, fetch in ACTION_BRANCH_EVENT_SPECS
        ],
        "events": events[:80],
        "event_count": len(events),
        "by_label": by_label,
        "by_comm": by_comm,
        "vote_before_values": vote_before,
        "vote_after_values": vote_after,
        "reconnect_flag_values": reconnect_flags,
        "state_calls": state_calls,
        "state2_calls": state2_calls,
        "old_voter_nonzero_seen": any(value != 0 for value in vote_before),
        "old_voter_zero_seen": any(value == 0 for value in vote_before),
        "reconnect_flag_nonzero_seen": any(value != 0 for value in reconnect_flags),
        "reconnect_flag_zero_seen": any(value == 0 for value in reconnect_flags),
        "state2_call_seen": bool(state2_calls),
    }


def parse_tracefs_output_v1167(text: str) -> dict[str, Any]:
    parsed = _base_parse_tracefs_output_v1165(text)
    parsed["pm_action_branch"] = parse_action_branch(text)
    return parsed


def patch_defaults() -> None:
    v1165.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    v1165.LATEST_POINTER = LATEST_POINTER
    v1165.DEFAULT_WORK_DIR = DEFAULT_WORK_DIR
    v1165.DEFAULT_CHILD_SCRIPT = DEFAULT_CHILD_SCRIPT
    v1165.DEFAULT_COLLECTOR_SCRIPT = DEFAULT_COLLECTOR_SCRIPT
    v1165.DEFAULT_CHILD_OUTPUT = DEFAULT_CHILD_OUTPUT
    v1165.PROOF_PREFIX = PROOF_PREFIX
    _install_action_branch_event_specs()
    v1165.parse_tracefs_output_v1165 = parse_tracefs_output_v1167
    v1165.patch_defaults()


def tracefs(manifest: dict[str, Any]) -> dict[str, Any]:
    return v1165.tracefs(manifest)


def action_branch(manifest: dict[str, Any]) -> dict[str, Any]:
    value = tracefs(manifest).get("pm_action_branch") or {}
    return value if isinstance(value, dict) else {}


def late_polls(manifest: dict[str, Any]) -> dict[str, str]:
    return v1165.late_polls(manifest)


def _poll_values(polls: dict[str, str], suffix: str) -> list[int]:
    values: list[int] = []
    for key, value in sorted(polls.items()):
        if key.endswith(suffix):
            values.append(intish(value))
    return values


def decide_v1167(args: Any, manifest: dict[str, Any]) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return (
            "v1167-pm-action-branch-plan-ready",
            True,
            "plan-only; no device mutation, PM actor, mdm_helper, CNSS daemon, reboot, or Wi-Fi action executed",
            "run bounded action-branch live with helper v217 and explicit allow flags",
        )

    base_decision, base_pass, base_reason, base_next = v1165.decide_v1165(args, manifest)
    branch = action_branch(manifest)
    polls = late_polls(manifest)
    esoc_counts = _poll_values(polls, "per_mgr_subsys_esoc0_count")
    esoc_seen = any(value > 0 for value in esoc_counts)
    if not base_pass:
        return (
            base_decision.replace("v1165", "v1167", 1),
            False,
            base_reason,
            base_next,
        )
    if not branch.get("event_count"):
        return (
            "v1167-action-branch-events-missing",
            False,
            f"branch={branch}",
            "verify V1167 uprobe event registration and pm-service offsets before retry",
        )
    if esoc_seen:
        return (
            "v1167-action-branch-esoc0-advanced",
            True,
            f"esoc_counts={esoc_counts} branch={branch}",
            "preserve evidence before any Wi-Fi HAL or scan/connect gate",
        )
    if branch.get("state2_call_seen"):
        return (
            "v1167-state-transition-called-but-no-esoc0",
            True,
            f"branch={branch}",
            "trace the state helper client-callback/open path below 0x92dc",
        )
    if branch.get("old_voter_nonzero_seen"):
        return (
            "v1167-old-voter-count-skips-state-transition",
            True,
            f"votes={branch.get('vote_before_values')} branch={branch}",
            "test PM actor ordering so late pm-proxy is the first modem voter, or classify stale voter reset semantics",
        )
    if branch.get("reconnect_flag_nonzero_seen"):
        return (
            "v1167-reconnect-flag-skips-state-transition",
            True,
            f"reconnect={branch.get('reconnect_flag_values')} branch={branch}",
            "classify PM reconnect/timer state initialization before replaying the trigger",
        )
    return (
        "v1167-action-branch-no-state-call-unclassified",
        True,
        f"branch={branch}",
        "inspect action-branch trace lines and add the next lower pm-service branch probe",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    base = v1165.render_summary(manifest).replace(
        "# V1165 Late pm-proxy Actionability Live",
        "# V1167 PM-Service Action Branch Live",
        1,
    )
    branch = action_branch(manifest)
    rows = [
        ["event_count", branch.get("event_count", "")],
        ["by_label", json.dumps(branch.get("by_label", {}), sort_keys=True)],
        ["by_comm", json.dumps(branch.get("by_comm", {}), sort_keys=True)],
        ["vote_before_values", json.dumps(branch.get("vote_before_values", []))],
        ["vote_after_values", json.dumps(branch.get("vote_after_values", []))],
        ["reconnect_flag_values", json.dumps(branch.get("reconnect_flag_values", []))],
        ["state_calls", json.dumps(branch.get("state_calls", []), sort_keys=True)],
        ["state2_call_seen", branch.get("state2_call_seen", "")],
        ["old_voter_nonzero_seen", branch.get("old_voter_nonzero_seen", "")],
        ["reconnect_flag_nonzero_seen", branch.get("reconnect_flag_nonzero_seen", "")],
    ]
    specs = [
        [item.get("label", ""), item.get("offset", ""), item.get("fetch", "")]
        for item in branch.get("event_specs", [])
    ]
    return base + "\n".join([
        "",
        "## V1167 PM-Service Action Branch",
        "",
        markdown_table(["key", "value"], rows),
        "",
        "## V1167 Event Specs",
        "",
        markdown_table(["label", "offset", "fetch"], specs),
        "",
    ])


def main() -> int:
    patch_defaults()
    args = v1165.v1143.v1139.v1113.v1106.parse_args()
    v1165.v1143.v1139.v1113.set_global_defaults(args)
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = v1165.v1143.v1139.v1113.v1106.build_manifest(args, store)
    manifest["base_v1165_decision"] = manifest.get("decision", "")
    manifest["cycle"] = "v1167"
    manifest["generated_at"] = now_iso()
    manifest["v1166_manifest"] = str(DEFAULT_V1166_MANIFEST)
    decision, passed, reason, next_step = decide_v1167(args, manifest)
    manifest.update({"decision": decision, "pass": passed, "reason": reason, "next_step": next_step})

    fw = v1165.v1143.v1139.global_firmware(manifest)
    values = v1165.v1143.v1139.contract(manifest)
    post = v1165.v1143.v1139.post_pm(manifest)
    lower = v1165.v1143.lower_trace(manifest)
    late = v1165.late_per_proxy(manifest)
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

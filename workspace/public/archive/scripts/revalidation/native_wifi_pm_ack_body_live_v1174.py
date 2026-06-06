#!/usr/bin/env python3
"""V1174 bounded PM-service ack implementation body live gate.

This V1173 derivative traces the mapped PM-service ack implementation target at
`pm-service+0x63f4` and its state-transition body at `pm-service+0x8788`.
It does not start Wi-Fi HAL, scan/connect/link-up, use credentials, run
DHCP/routes, external ping, write boot/partitions, or flash.
"""

from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

import native_wifi_pm_ack_path_live_v1173 as v1173
from a90_kernel_tools import markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1174-pm-ack-body-live")
LATEST_POINTER = Path("tmp/wifi/latest-v1174-pm-ack-body-live.txt")
DEFAULT_WORK_DIR = "/cache/a90-runtime/v1174"
DEFAULT_CHILD_SCRIPT = "/cache/a90-runtime/v1174/pm-ack-body-child.sh"
DEFAULT_COLLECTOR_SCRIPT = "/cache/a90-runtime/v1174/pm-ack-body-collector.sh"
DEFAULT_CHILD_OUTPUT = "/cache/a90-runtime/v1174/pm-ack-body-output.txt"
PROOF_PREFIX = "/tmp/a90-v1174-"
DEFAULT_V1173_MANIFEST = Path("tmp/wifi/v1173-rerun-pm-ack-path-live-after-v490/manifest.json")

BODY_EVENT_SPECS = (
    ("pm_ack_impl_entry", "service", "63f4", "manager=%x0 handle=%x1 state=%x2"),
    ("pm_ack_impl_client_match", "service", "6474", "client=%x21 handle=%x19 state=%x20"),
    ("pm_ack_state_core_entry", "service", "8788", "peripheral=%x0 handle=%x1 state=%x2"),
    ("pm_ack_state_client_clear", "service", "882c", "client=%x22 state=%x21"),
    ("pm_ack_state_pending_scan_done", "service", "8894", "peripheral=%x20 all_acked=%x21"),
    ("pm_ack_state_current", "service", "88d0", "peripheral=%x20 current_state=%x8 all_acked=%x21"),
    ("pm_ack_state2_dependency_ptr", "service", "88e4", "peripheral=%x20 dependency=%x22"),
    ("pm_ack_state2_dependency_flag", "service", "88ec", "dependency=%x22 dependency_flag=%x8"),
    ("pm_ack_state2_fd_eval", "service", "898c", "peripheral=%x20 fd=%x8"),
    ("pm_ack_state2_open_call", "service", "8cd0", "device_path=%x0 flags=%x1"),
    ("pm_ack_state2_open_result", "service", "8cd4", "fd=%x0"),
    ("pm_ack_state_set_call", "service", "8d14", "peripheral=%x20 state=%x1"),
    ("pm_ack_state_core_ret", "service", "8788", "ret=$retval"),
)
BODY_LABELS = {label for label, _binary_key, _offset, _fetch in BODY_EVENT_SPECS}
VALUE_RE = re.compile(
    r"\b(?P<key>manager|handle|state|client|peripheral|all_acked|current_state|"
    r"dependency|dependency_flag|fd|device_path|flags|ret)="
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


def signed32(value: int) -> int:
    return value - 0x100000000 if value & 0x80000000 else value


def _tracebase() -> Any:
    return v1173._tracebase()


def _install_body_event_specs() -> None:
    tracebase = _tracebase()
    existing = {label for label, _binary_key, _offset, _fetch in tracebase.EVENT_SPECS}
    additions = tuple(spec for spec in BODY_EVENT_SPECS if spec[0] not in existing)
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


def tracefs_collector_script_v1174(args: Any) -> str:
    return v1173.tracefs_collector_script_v1173(args)


def _trace_match(line: str) -> tuple[str, str] | None:
    match = _tracebase().TRACE_LINE_RE.match(line)
    if not match:
        return None
    return match.group("comm").strip(), match.group("label")


def _value_map(line: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for match in VALUE_RE.finditer(line):
        values[match.group("key")] = match.group("value")
    return values


def parse_body_trace(text: str) -> dict[str, Any]:
    trace_lines = _tracebase().collect_trace_lines(text)
    events: list[dict[str, Any]] = []
    by_label: dict[str, int] = {label: 0 for label in sorted(BODY_LABELS)}
    by_comm: dict[str, dict[str, int]] = {}
    for line in trace_lines:
        matched = _trace_match(line)
        if not matched:
            continue
        comm, label = matched
        if label not in BODY_LABELS:
            continue
        values = _value_map(line)
        events.append({"comm": comm, "label": label, "values": values, "line": line.strip()})
        by_label[label] = by_label.get(label, 0) + 1
        by_comm.setdefault(comm, {})
        by_comm[comm][label] = by_comm[comm].get(label, 0) + 1

    impl_states = [
        intish(event["values"].get("state"), -1)
        for event in events
        if event["label"] in {"pm_ack_impl_entry", "pm_ack_impl_client_match", "pm_ack_state_core_entry"}
        and "state" in event["values"]
    ]
    core_states = [
        intish(event["values"].get("state"), -1)
        for event in events
        if event["label"] == "pm_ack_state_core_entry"
        and "state" in event["values"]
    ]
    current_states = [
        intish(event["values"].get("current_state"), -1)
        for event in events
        if event["label"] == "pm_ack_state_current"
        and "current_state" in event["values"]
    ]
    set_states = [
        intish(event["values"].get("state"), -1)
        for event in events
        if event["label"] == "pm_ack_state_set_call"
        and "state" in event["values"]
    ]
    all_acked_values = [
        intish(event["values"].get("all_acked"), -1)
        for event in events
        if event["label"] in {"pm_ack_state_pending_scan_done", "pm_ack_state_current"}
        and "all_acked" in event["values"]
    ]
    dependency_values = [
        intish(event["values"].get("dependency"), -1)
        for event in events
        if event["label"] == "pm_ack_state2_dependency_ptr"
        and "dependency" in event["values"]
    ]
    dependency_flag_values = [
        intish(event["values"].get("dependency_flag"), -1)
        for event in events
        if event["label"] == "pm_ack_state2_dependency_flag"
        and "dependency_flag" in event["values"]
    ]
    fd_eval_values = [
        intish(event["values"].get("fd"), -1)
        for event in events
        if event["label"] == "pm_ack_state2_fd_eval"
        and "fd" in event["values"]
    ]
    fd_eval_signed = [signed32(value) for value in fd_eval_values]
    open_ret_values = [
        intish(event["values"].get("fd"), -1)
        for event in events
        if event["label"] == "pm_ack_state2_open_result"
        and "fd" in event["values"]
    ]
    open_ret_signed = [signed32(value) for value in open_ret_values]
    returns = []
    for event in events:
        if event["label"] != "pm_ack_state_core_ret" or "ret" not in event["values"]:
            continue
        ret = intish(event["values"].get("ret"))
        returns.append(
            {
                "comm": event["comm"],
                "ret": ret,
                "ret_signed32": signed32(ret),
                "ret_hex": event["values"].get("ret", ""),
                "line": event["line"],
            }
        )

    return {
        "event_specs": [
            {"label": label, "binary_key": binary_key, "offset": offset, "fetch": fetch}
            for label, binary_key, offset, fetch in BODY_EVENT_SPECS
        ],
        "events": events[:160],
        "event_count": len(events),
        "by_label": by_label,
        "by_comm": by_comm,
        "impl_states": impl_states,
        "core_states": core_states,
        "current_states": current_states,
        "set_states": set_states,
        "all_acked_values": all_acked_values,
        "dependency_values": [hex(value) for value in dependency_values],
        "dependency_flag_values": dependency_flag_values,
        "fd_eval_values": fd_eval_values,
        "fd_eval_signed": fd_eval_signed,
        "open_ret_values": open_ret_values,
        "open_ret_signed": open_ret_signed,
        "returns": returns,
        "state2_impl_entry_seen": 2 in impl_states,
        "state2_core_entry_seen": 2 in core_states,
        "state2_current_seen": 2 in current_states,
        "state2_all_acked_seen": 1 in all_acked_values,
        "state2_dependency_seen": bool(dependency_values),
        "state2_dependency_enabled_seen": any(value != 0 for value in dependency_flag_values),
        "state2_fd_eval_seen": bool(fd_eval_values),
        "state2_fd_zero_seen": 0 in fd_eval_signed,
        "state2_fd_negative_seen": any(value < 0 for value in fd_eval_signed),
        "state2_open_call_seen": by_label.get("pm_ack_state2_open_call", 0) > 0,
        "state2_open_success_seen": any(value >= 0 for value in open_ret_signed),
        "state3_set_seen": 3 in set_states,
        "ack_body_return_success_seen": any(item.get("ret") == 0 for item in returns),
    }


def parse_tracefs_output_v1174(text: str) -> dict[str, Any]:
    parsed = v1173.parse_tracefs_output_v1173(text)
    parsed["pm_ack_impl_body"] = parse_body_trace(text)
    return parsed


def patch_defaults() -> None:
    v1173.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    v1173.LATEST_POINTER = LATEST_POINTER
    v1173.DEFAULT_WORK_DIR = DEFAULT_WORK_DIR
    v1173.DEFAULT_CHILD_SCRIPT = DEFAULT_CHILD_SCRIPT
    v1173.DEFAULT_COLLECTOR_SCRIPT = DEFAULT_COLLECTOR_SCRIPT
    v1173.DEFAULT_CHILD_OUTPUT = DEFAULT_CHILD_OUTPUT
    v1173.PROOF_PREFIX = PROOF_PREFIX
    v1173.patch_defaults()
    _install_body_event_specs()
    v1173.v1172.v1171.v1170.v1169.tracefs_collector_script_v1169 = tracefs_collector_script_v1174
    v1173.v1172.v1171.v1170.parse_tracefs_output_v1170 = parse_tracefs_output_v1174
    v1173.v1172.v1171.v1170.v1169.v1168.tracefs_collector_script_v1168 = tracefs_collector_script_v1174
    v1173.v1172.v1171.v1170.v1169.parse_tracefs_output_v1169 = parse_tracefs_output_v1174
    v1173.v1172.v1171.v1170.v1169.v1168.v1167.v1165.tracefs_collector_script_v1165 = (
        tracefs_collector_script_v1174
    )
    v1173.v1172.v1171.v1170.v1169.v1168.parse_tracefs_output_v1168 = parse_tracefs_output_v1174
    v1173.v1172.v1171.v1170.v1169.v1168.v1167.parse_tracefs_output_v1167 = parse_tracefs_output_v1174
    v1173.v1172.v1171.v1170.v1169.v1168.v1167.v1165.v1143.v1139.v1113.v1106.tracefs_collector_script = (
        tracefs_collector_script_v1174
    )
    v1173.v1172.v1171.v1170.v1169.v1168.v1167.v1165.v1143.v1139.v1113.v1106.parse_tracefs_output = (
        parse_tracefs_output_v1174
    )


def tracefs(manifest: dict[str, Any]) -> dict[str, Any]:
    return v1173.tracefs(manifest)


def pm_ack_body(manifest: dict[str, Any]) -> dict[str, Any]:
    value = tracefs(manifest).get("pm_ack_impl_body") or {}
    return value if isinstance(value, dict) else {}


def decide_v1174(args: Any, manifest: dict[str, Any]) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return (
            "v1174-pm-ack-body-plan-ready",
            True,
            "plan-only; no device mutation, PM actor, mdm_helper, CNSS daemon, reboot, or Wi-Fi action executed",
            "run bounded PM ack body live with helper v217 and explicit allow flags",
        )

    base_decision, base_pass, base_reason, base_next = v1173.decide_v1173(args, manifest)
    body = pm_ack_body(manifest)
    no_esoc0 = not v1173.v1172.v1171.esoc0_open_seen(manifest)
    if not base_pass:
        return (
            base_decision.replace("v1173", "v1174", 1),
            False,
            base_reason,
            base_next,
        )
    if not body.get("event_count"):
        return (
            "v1174-pm-ack-body-missing",
            True,
            f"body={body}",
            "verify pm-service body offsets and service binary uprobe registration",
        )
    if not no_esoc0:
        return (
            "v1174-pm-ack-body-opened-esoc0",
            True,
            f"body={body}",
            "move to bounded MHI/WLFW/BDF publication gate",
        )
    if body.get("state2_open_call_seen"):
        if body.get("state2_open_success_seen") and body.get("state3_set_seen"):
            return (
                "v1174-state2-open-success-state3-no-esoc0",
                True,
                f"body={body}",
                "decode opened device path and compare why state=3 does not publish mdm3/WLFW",
            )
        return (
            "v1174-state2-open-call-no-esoc0",
            True,
            f"body={body}",
            "classify opened path/fd result and why eSoC publication did not follow",
        )
    if body.get("state2_fd_zero_seen"):
        return (
            "v1174-state2-fd-zero-skip-open-no-esoc0",
            True,
            f"body={body}",
            "compare Android pm-service object fd initialization and native device-fd field before ack",
        )
    if body.get("state2_fd_eval_seen"):
        return (
            "v1174-state2-fd-eval-no-open-no-esoc0",
            True,
            f"body={body}",
            "classify fd value and PM-service state fields before another eSoC gate",
        )
    if body.get("state2_current_seen"):
        return (
            "v1174-state2-current-no-fd-eval-no-esoc0",
            True,
            f"body={body}",
            "trace state-2 dependency branch and fd-eval fallthrough",
        )
    if body.get("state2_core_entry_seen"):
        return (
            "v1174-state2-body-exits-before-current-state",
            True,
            f"body={body}",
            "classify all-acked/timer-stop/current-state branch before fd evaluation",
        )
    return (
        "v1174-pm-ack-body-unclassified",
        True,
        f"body={body} esoc0_open_seen={not no_esoc0}",
        "inspect PM ack body trace values before choosing the next gate",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    base = v1173.render_summary(manifest).replace(
        "# V1173 PM Ack Path Live",
        "# V1174 PM Ack Body Live",
        1,
    )
    body = pm_ack_body(manifest)
    rows = [
        ["event_count", body.get("event_count", "")],
        ["by_label", json.dumps(body.get("by_label", {}), sort_keys=True)],
        ["by_comm", json.dumps(body.get("by_comm", {}), sort_keys=True)],
        ["impl_states", json.dumps(body.get("impl_states", []))],
        ["core_states", json.dumps(body.get("core_states", []))],
        ["current_states", json.dumps(body.get("current_states", []))],
        ["set_states", json.dumps(body.get("set_states", []))],
        ["all_acked_values", json.dumps(body.get("all_acked_values", []))],
        ["dependency_values", json.dumps(body.get("dependency_values", []))],
        ["dependency_flag_values", json.dumps(body.get("dependency_flag_values", []))],
        ["fd_eval_signed", json.dumps(body.get("fd_eval_signed", []))],
        ["open_ret_signed", json.dumps(body.get("open_ret_signed", []))],
        ["state2_core_entry_seen", body.get("state2_core_entry_seen", "")],
        ["state2_current_seen", body.get("state2_current_seen", "")],
        ["state2_fd_eval_seen", body.get("state2_fd_eval_seen", "")],
        ["state2_fd_zero_seen", body.get("state2_fd_zero_seen", "")],
        ["state2_open_call_seen", body.get("state2_open_call_seen", "")],
        ["state3_set_seen", body.get("state3_set_seen", "")],
        ["esoc0_open_seen", v1173.v1172.v1171.esoc0_open_seen(manifest)],
    ]
    specs = [
        [item.get("label", ""), item.get("offset", ""), item.get("fetch", "")]
        for item in body.get("event_specs", [])
    ]
    return base + "\n".join([
        "",
        "## V1174 PM Ack Body",
        "",
        markdown_table(["key", "value"], rows),
        "",
        "## V1174 Event Specs",
        "",
        markdown_table(["label", "offset", "fetch"], specs),
        "",
    ])


def main() -> int:
    patch_defaults()
    args = v1173.v1172.v1171.v1170.v1169.v1168.v1167.v1165.v1143.v1139.v1113.v1106.parse_args()
    v1173.v1172.v1171.v1170.v1169.v1168.v1167.v1165.v1143.v1139.v1113.set_global_defaults(args)
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = v1173.v1172.v1171.v1170.v1169.v1168.v1167.v1165.v1143.v1139.v1113.v1106.build_manifest(args, store)
    manifest["base_v1173_decision"] = manifest.get("decision", "")
    manifest["cycle"] = "v1174"
    manifest["generated_at"] = now_iso()
    manifest["v1173_manifest"] = str(DEFAULT_V1173_MANIFEST)
    decision, passed, reason, next_step = decide_v1174(args, manifest)
    manifest.update({"decision": decision, "pass": passed, "reason": reason, "next_step": next_step})

    fw = v1173.v1172.v1171.v1170.v1169.v1168.v1167.v1165.v1143.v1139.global_firmware(manifest)
    values = v1173.v1172.v1171.v1170.v1169.v1168.v1167.v1165.v1143.v1139.contract(manifest)
    post = v1173.v1172.v1171.v1170.v1169.v1168.v1167.v1165.v1143.v1139.post_pm(manifest)
    lower = v1173.v1172.v1171.v1170.v1169.v1168.v1167.v1165.v1143.lower_trace(manifest)
    late = v1173.v1172.v1171.v1170.v1169.v1168.v1167.v1165.late_per_proxy(manifest)
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

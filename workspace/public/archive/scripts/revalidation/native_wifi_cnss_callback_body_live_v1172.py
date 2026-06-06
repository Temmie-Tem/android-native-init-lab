#!/usr/bin/env python3
"""V1172 bounded cnss-daemon PM callback body live gate.

This V1171 derivative traces the mapped `cnss-daemon+0xc340` receiver callback
body.  It verifies whether the state=2 callback takes an eSoC/action branch or
only tail-calls `pm_client_event_acknowledge`.  It does not start Wi-Fi HAL,
scan/connect/link-up, use credentials, run DHCP/routes, external ping, write
boot/partitions, or flash.
"""

from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

import native_wifi_pm_receiver_callback_live_v1171 as v1171
from a90_kernel_tools import markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1172-cnss-callback-body-live")
LATEST_POINTER = Path("tmp/wifi/latest-v1172-cnss-callback-body-live.txt")
DEFAULT_WORK_DIR = "/cache/a90-runtime/v1172"
DEFAULT_CHILD_SCRIPT = "/cache/a90-runtime/v1172/cnss-callback-body-child.sh"
DEFAULT_COLLECTOR_SCRIPT = "/cache/a90-runtime/v1172/cnss-callback-body-collector.sh"
DEFAULT_CHILD_OUTPUT = "/cache/a90-runtime/v1172/cnss-callback-body-output.txt"
PROOF_PREFIX = "/tmp/a90-v1172-"
CNSS_DAEMON_BIN = "/mnt/vendor/bin/cnss-daemon"
DEFAULT_V1171_MANIFEST = Path("tmp/wifi/v1171-retry-pm-receiver-callback-live-after-v490/manifest.json")

CNSS_EVENT_SPECS = (
    ("cnss_pm_callback_entry", "cnss", "c340", "object=%x0 state=%x1"),
    ("cnss_pm_callback_meta_loaded", "cnss", "c354", "object=%x0 state_arg=%x1 object_id=%x4"),
    ("cnss_pm_callback_handle_loaded", "cnss", "c37c", "object=%x20 pm_handle=%x0 state_saved=%x19"),
    ("cnss_pm_callback_ack_call", "cnss", "c38c", "pm_handle=%x0 state_arg=%x1"),
    ("cnss_pm_callback_ret", "cnss", "c340", "ret=$retval"),
)
CNSS_LABELS = {label for label, _binary_key, _offset, _fetch in CNSS_EVENT_SPECS}
VALUE_RE = re.compile(
    r"\b(?P<key>object|state|state_arg|object_id|pm_handle|state_saved|ret)="
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
    return v1171._tracebase()


def _install_cnss_event_specs() -> None:
    tracebase = _tracebase()
    existing = {label for label, _binary_key, _offset, _fetch in tracebase.EVENT_SPECS}
    additions = tuple(spec for spec in CNSS_EVENT_SPECS if spec[0] not in existing)
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


def _replace_once(text: str, old: str, new: str, message: str) -> str:
    if old not in text:
        raise RuntimeError(message)
    return text.replace(old, new, 1)


def tracefs_collector_script_v1172(args: Any) -> str:
    script = v1171.tracefs_collector_script_v1171(args)
    service_line = f"SERVICE_BIN={args.pm_service!r}\n".replace("'", "")
    if service_line not in script:
        service_line = f"SERVICE_BIN={args.pm_service}\n"
    script = _replace_once(
        script,
        service_line,
        service_line + f"CNSS_BIN={CNSS_DAEMON_BIN}\n",
        "V1171 collector service binary line changed",
    )
    script = _replace_once(
        script,
        'echo service_binary="$SERVICE_BIN"\n',
        'echo service_binary="$SERVICE_BIN"\necho cnss_binary="$CNSS_BIN"\n',
        "V1171 collector service echo insertion point changed",
    )
    script = _replace_once(
        script,
        'if ! $BB test -x "$CHILD"; then\n',
        'if ! $BB test -r "$CNSS_BIN"; then\n'
        '  echo result=tracefs-uprobe-cnss-binary-missing\n'
        '  exit 1\n'
        'fi\n'
        'if ! $BB test -x "$CHILD"; then\n',
        "V1171 collector child check insertion point changed",
    )
    script = _replace_once(
        script,
        '    service) bin="$SERVICE_BIN" ;;\n',
        '    service) bin="$SERVICE_BIN" ;;\n'
        '    cnss) bin="$CNSS_BIN" ;;\n',
        "V1171 collector register_event binary case changed",
    )
    return script


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


def parse_cnss_callback_trace(text: str) -> dict[str, Any]:
    trace_lines = _tracebase().collect_trace_lines(text)
    events: list[dict[str, Any]] = []
    by_label: dict[str, int] = {label: 0 for label in sorted(CNSS_LABELS)}
    by_comm: dict[str, dict[str, int]] = {}
    for line in trace_lines:
        matched = _trace_match(line)
        if not matched:
            continue
        comm, label = matched
        if label not in CNSS_LABELS:
            continue
        values = _value_map(line)
        events.append({"comm": comm, "label": label, "values": values, "line": line.strip()})
        by_label[label] = by_label.get(label, 0) + 1
        by_comm.setdefault(comm, {})
        by_comm[comm][label] = by_comm[comm].get(label, 0) + 1

    state_values = [
        intish(event["values"].get("state", event["values"].get("state_arg", event["values"].get("state_saved"))), -1)
        for event in events
        if "state" in event["values"] or "state_arg" in event["values"] or "state_saved" in event["values"]
    ]
    callback_returns = []
    for event in events:
        if event["label"] != "cnss_pm_callback_ret" or "ret" not in event["values"]:
            continue
        ret = intish(event["values"].get("ret"))
        callback_returns.append({
            "comm": event["comm"],
            "ret": ret,
            "ret_signed32": signed32(ret),
            "ret_hex": event["values"].get("ret", ""),
            "line": event["line"],
        })
    ack_states = [
        intish(event["values"].get("state_arg"), -1)
        for event in events
        if event["label"] == "cnss_pm_callback_ack_call"
    ]
    state2_entry_seen = any(
        event["label"] == "cnss_pm_callback_entry"
        and intish(event["values"].get("state"), -1) == 2
        for event in events
    )
    state2_ack_call_seen = any(
        event["label"] == "cnss_pm_callback_ack_call"
        and intish(event["values"].get("state_arg"), -1) == 2
        for event in events
    )
    return {
        "event_specs": [
            {"label": label, "binary_key": binary_key, "offset": offset, "fetch": fetch}
            for label, binary_key, offset, fetch in CNSS_EVENT_SPECS
        ],
        "events": events[:120],
        "event_count": len(events),
        "by_label": by_label,
        "by_comm": by_comm,
        "state_values": state_values,
        "ack_states": ack_states,
        "callback_returns": callback_returns,
        "state2_entry_seen": state2_entry_seen,
        "state2_ack_call_seen": state2_ack_call_seen,
    }


def parse_tracefs_output_v1172(text: str) -> dict[str, Any]:
    parsed = v1171.parse_tracefs_output_v1171(text)
    parsed["cnss_callback_body"] = parse_cnss_callback_trace(text)
    return parsed


def patch_defaults() -> None:
    v1171.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    v1171.LATEST_POINTER = LATEST_POINTER
    v1171.DEFAULT_WORK_DIR = DEFAULT_WORK_DIR
    v1171.DEFAULT_CHILD_SCRIPT = DEFAULT_CHILD_SCRIPT
    v1171.DEFAULT_COLLECTOR_SCRIPT = DEFAULT_COLLECTOR_SCRIPT
    v1171.DEFAULT_CHILD_OUTPUT = DEFAULT_CHILD_OUTPUT
    v1171.PROOF_PREFIX = PROOF_PREFIX
    v1171.patch_defaults()
    _install_cnss_event_specs()
    v1171.v1170.v1169.tracefs_collector_script_v1169 = tracefs_collector_script_v1172
    v1171.v1170.parse_tracefs_output_v1170 = parse_tracefs_output_v1172
    v1171.v1170.v1169.v1168.tracefs_collector_script_v1168 = tracefs_collector_script_v1172
    v1171.v1170.v1169.parse_tracefs_output_v1169 = parse_tracefs_output_v1172
    v1171.v1170.v1169.v1168.v1167.v1165.tracefs_collector_script_v1165 = tracefs_collector_script_v1172
    v1171.v1170.v1169.v1168.parse_tracefs_output_v1168 = parse_tracefs_output_v1172
    v1171.v1170.v1169.v1168.v1167.parse_tracefs_output_v1167 = parse_tracefs_output_v1172
    v1171.v1170.v1169.v1168.v1167.v1165.v1143.v1139.v1113.v1106.tracefs_collector_script = (
        tracefs_collector_script_v1172
    )
    v1171.v1170.v1169.v1168.v1167.v1165.v1143.v1139.v1113.v1106.parse_tracefs_output = (
        parse_tracefs_output_v1172
    )


def tracefs(manifest: dict[str, Any]) -> dict[str, Any]:
    return v1171.tracefs(manifest)


def cnss_callback_body(manifest: dict[str, Any]) -> dict[str, Any]:
    value = tracefs(manifest).get("cnss_callback_body") or {}
    return value if isinstance(value, dict) else {}


def decide_v1172(args: Any, manifest: dict[str, Any]) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return (
            "v1172-cnss-callback-body-plan-ready",
            True,
            "plan-only; no device mutation, PM actor, mdm_helper, CNSS daemon, reboot, or Wi-Fi action executed",
            "run bounded cnss-daemon callback-body live with helper v217 and explicit allow flags",
        )

    base_decision, base_pass, base_reason, base_next = v1171.decide_v1171(args, manifest)
    cnss = cnss_callback_body(manifest)
    no_esoc0 = not v1171.esoc0_open_seen(manifest)
    if not base_pass:
        return (
            base_decision.replace("v1171", "v1172", 1),
            False,
            base_reason,
            base_next,
        )
    if v1171.receiver_callback(manifest).get("callback_to_cnss_daemon_seen") is not True:
        return (
            "v1172-cnss-callback-precondition-missing",
            False,
            f"receiver={v1171.receiver_callback(manifest)}",
            "restore V1171 cnss-daemon receiver mapping before callback-body tracing",
        )
    if not cnss.get("event_count"):
        return (
            "v1172-cnss-callback-body-not-observed",
            True,
            f"cnss={cnss}",
            "verify cnss-daemon binary path/offset and rerun before changing PM ordering",
        )
    if not no_esoc0:
        return (
            "v1172-cnss-callback-opened-esoc0",
            True,
            f"cnss={cnss}",
            "move to bounded MHI/WLFW/BDF publication gate",
        )
    if cnss.get("state2_entry_seen") and cnss.get("state2_ack_call_seen"):
        return (
            "v1172-cnss-state2-ack-only-no-esoc0",
            True,
            f"cnss={cnss}",
            "classify pm_client_event_acknowledge handling or the next Android actor that advances eSoC",
        )
    if cnss.get("state2_entry_seen"):
        return (
            "v1172-cnss-state2-callback-no-ack",
            True,
            f"cnss={cnss}",
            "trace callback null/guard path and object lifetime before changing PM ordering",
        )
    return (
        "v1172-cnss-callback-body-unclassified",
        True,
        f"cnss={cnss} esoc0_open_seen={not no_esoc0}",
        "inspect cnss callback trace values before choosing the next gate",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    base = v1171.render_summary(manifest).replace(
        "# V1171 PM Receiver Callback Live",
        "# V1172 CNSS Callback Body Live",
        1,
    )
    cnss = cnss_callback_body(manifest)
    rows = [
        ["event_count", cnss.get("event_count", "")],
        ["by_label", json.dumps(cnss.get("by_label", {}), sort_keys=True)],
        ["by_comm", json.dumps(cnss.get("by_comm", {}), sort_keys=True)],
        ["state_values", json.dumps(cnss.get("state_values", []))],
        ["ack_states", json.dumps(cnss.get("ack_states", []))],
        ["callback_returns", json.dumps(cnss.get("callback_returns", []), sort_keys=True)],
        ["state2_entry_seen", cnss.get("state2_entry_seen", "")],
        ["state2_ack_call_seen", cnss.get("state2_ack_call_seen", "")],
        ["esoc0_open_seen", v1171.esoc0_open_seen(manifest)],
    ]
    specs = [
        [item.get("label", ""), item.get("offset", ""), item.get("fetch", "")]
        for item in cnss.get("event_specs", [])
    ]
    return base + "\n".join([
        "",
        "## V1172 CNSS Callback Body",
        "",
        markdown_table(["key", "value"], rows),
        "",
        "## V1172 Event Specs",
        "",
        markdown_table(["label", "offset", "fetch"], specs),
        "",
    ])


def main() -> int:
    patch_defaults()
    args = v1171.v1170.v1169.v1168.v1167.v1165.v1143.v1139.v1113.v1106.parse_args()
    v1171.v1170.v1169.v1168.v1167.v1165.v1143.v1139.v1113.set_global_defaults(args)
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = v1171.v1170.v1169.v1168.v1167.v1165.v1143.v1139.v1113.v1106.build_manifest(args, store)
    manifest["base_v1171_decision"] = manifest.get("decision", "")
    manifest["cycle"] = "v1172"
    manifest["generated_at"] = now_iso()
    manifest["v1171_manifest"] = str(DEFAULT_V1171_MANIFEST)
    decision, passed, reason, next_step = decide_v1172(args, manifest)
    manifest.update({"decision": decision, "pass": passed, "reason": reason, "next_step": next_step})

    fw = v1171.v1170.v1169.v1168.v1167.v1165.v1143.v1139.global_firmware(manifest)
    values = v1171.v1170.v1169.v1168.v1167.v1165.v1143.v1139.contract(manifest)
    post = v1171.v1170.v1169.v1168.v1167.v1165.v1143.v1139.post_pm(manifest)
    lower = v1171.v1170.v1169.v1168.v1167.v1165.v1143.lower_trace(manifest)
    late = v1171.v1170.v1169.v1168.v1167.v1165.late_per_proxy(manifest)
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

#!/usr/bin/env python3
"""V1173 bounded PM acknowledge path live gate.

This V1172 derivative traces `pm_client_event_acknowledge` in
libperipheral_client.so and the PM-service `BnPeripheralManager::onTransact`
code-5 ack branch.  It does not start Wi-Fi HAL, scan/connect/link-up, use
credentials, run DHCP/routes, external ping, write boot/partitions, or flash.
"""

from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

import native_wifi_cnss_callback_body_live_v1172 as v1172
from a90_kernel_tools import markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1173-pm-ack-path-live")
LATEST_POINTER = Path("tmp/wifi/latest-v1173-pm-ack-path-live.txt")
DEFAULT_WORK_DIR = "/cache/a90-runtime/v1173"
DEFAULT_CHILD_SCRIPT = "/cache/a90-runtime/v1173/pm-ack-path-child.sh"
DEFAULT_COLLECTOR_SCRIPT = "/cache/a90-runtime/v1173/pm-ack-path-collector.sh"
DEFAULT_CHILD_OUTPUT = "/cache/a90-runtime/v1173/pm-ack-path-output.txt"
PROOF_PREFIX = "/tmp/a90-v1173-"
DEFAULT_V1172_MANIFEST = Path("tmp/wifi/v1172-rerun2-cnss-callback-body-live-after-v490/manifest.json")

ACK_EVENT_SPECS = (
    ("pm_client_ack_entry", "client", "76f0", "pm_handle=%x0 state=%x1"),
    ("pm_client_ack_match", "client", "7754", "pm_handle=%x20 state_saved=%x19"),
    ("pm_client_ack_virtual_call", "client", "7780", "manager=%x0 pm_handle_arg=%x1 state_arg=%x2 target=%x8"),
    ("pm_client_ack_virtual_ret", "client", "7784", "ret=%x0 state_saved=%x19"),
    ("pm_client_ack_ret", "client", "76f0", "ret=$retval"),
    ("pm_server_ontransact_entry", "client", "85bc", "this=%x0 code=%x1 data=%x2 reply=%x3 flags=%x4"),
    ("pm_server_ack_read_handle", "client", "8744", "this=%x20 handle=%x22"),
    ("pm_server_ack_read_state", "client", "8750", "this=%x20 handle=%x22 state=%x0"),
    ("pm_server_ack_impl_call", "client", "8760", "this=%x0 handle=%x1 state=%x2 target=%x8"),
    ("pm_server_ack_write_ret", "client", "8814", "ret=%x0"),
    ("pm_server_ontransact_ret", "client", "85bc", "ret=$retval"),
)
ACK_LABELS = {label for label, _binary_key, _offset, _fetch in ACK_EVENT_SPECS}
VALUE_RE = re.compile(
    r"\b(?P<key>pm_handle|state|state_saved|manager|pm_handle_arg|state_arg|target|ret|"
    r"this|code|data|reply|flags|handle)="
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
    return v1172._tracebase()


def _install_ack_event_specs() -> None:
    tracebase = _tracebase()
    existing = {label for label, _binary_key, _offset, _fetch in tracebase.EVENT_SPECS}
    additions = tuple(spec for spec in ACK_EVENT_SPECS if spec[0] not in existing)
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


def tracefs_collector_script_v1173(args: Any) -> str:
    return v1172.tracefs_collector_script_v1172(args)


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


def _map_pointer(value: int, entries: list[dict[str, Any]], receiver: str) -> dict[str, Any]:
    mapped = v1172.v1171.v1170.v1169.v1168.map_pointer(value, entries)
    mapped["receiver"] = receiver if mapped.get("path") else ""
    return mapped


def parse_ack_trace(text: str) -> dict[str, Any]:
    trace_lines = _tracebase().collect_trace_lines(text)
    pm_service_maps = v1172.v1171.parse_named_sample_maps(text, "pm_service")
    cnss_maps = v1172.v1171.parse_named_sample_maps(text, "cnss_daemon")
    events: list[dict[str, Any]] = []
    by_label: dict[str, int] = {label: 0 for label in sorted(ACK_LABELS)}
    by_comm: dict[str, dict[str, int]] = {}
    for line in trace_lines:
        matched = _trace_match(line)
        if not matched:
            continue
        comm, label = matched
        if label not in ACK_LABELS:
            continue
        values = _value_map(line)
        events.append({"comm": comm, "label": label, "values": values, "line": line.strip()})
        by_label[label] = by_label.get(label, 0) + 1
        by_comm.setdefault(comm, {})
        by_comm[comm][label] = by_comm[comm].get(label, 0) + 1

    client_ack_states = [
        intish(event["values"].get("state", event["values"].get("state_arg", event["values"].get("state_saved"))), -1)
        for event in events
        if event["label"].startswith("pm_client_ack_")
        and ("state" in event["values"] or "state_arg" in event["values"] or "state_saved" in event["values"])
    ]
    server_codes = [
        intish(event["values"].get("code"), -1)
        for event in events
        if event["label"] == "pm_server_ontransact_entry"
    ]
    server_ack_states = [
        intish(event["values"].get("state"), -1)
        for event in events
        if event["label"] in {"pm_server_ack_read_state", "pm_server_ack_impl_call"}
        and "state" in event["values"]
    ]
    client_virtual_returns = []
    callback_returns = []
    server_ontransact_returns = []
    server_write_returns = []
    for event in events:
        if "ret" not in event["values"]:
            continue
        ret = intish(event["values"].get("ret"))
        item = {
            "comm": event["comm"],
            "ret": ret,
            "ret_signed32": signed32(ret),
            "ret_hex": event["values"].get("ret", ""),
            "line": event["line"],
        }
        if event["label"] == "pm_client_ack_virtual_ret":
            item["state"] = intish(event["values"].get("state_saved"), -1)
            client_virtual_returns.append(item)
        elif event["label"] == "pm_client_ack_ret":
            callback_returns.append(item)
        elif event["label"] == "pm_server_ontransact_ret":
            server_ontransact_returns.append(item)
        elif event["label"] == "pm_server_ack_write_ret":
            server_write_returns.append(item)

    client_targets = [
        intish(event["values"].get("target"), -1)
        for event in events
        if event["label"] == "pm_client_ack_virtual_call"
        and "target" in event["values"]
    ]
    server_targets = [
        intish(event["values"].get("target"), -1)
        for event in events
        if event["label"] == "pm_server_ack_impl_call"
        and "target" in event["values"]
    ]
    mapped_client_targets = [
        _map_pointer(value, cnss_maps["entries"], "cnss-daemon")
        for value in client_targets
    ]
    mapped_server_targets = [
        _map_pointer(value, pm_service_maps["entries"], "pm-service")
        for value in server_targets
    ]
    return {
        "event_specs": [
            {"label": label, "binary_key": binary_key, "offset": offset, "fetch": fetch}
            for label, binary_key, offset, fetch in ACK_EVENT_SPECS
        ],
        "events": events[:160],
        "event_count": len(events),
        "by_label": by_label,
        "by_comm": by_comm,
        "client_ack_states": client_ack_states,
        "server_codes": server_codes,
        "server_ack_states": server_ack_states,
        "client_virtual_returns": client_virtual_returns,
        "client_ack_returns": callback_returns,
        "server_write_returns": server_write_returns,
        "server_ontransact_returns": server_ontransact_returns,
        "client_targets": [hex(value) for value in client_targets],
        "server_targets": [hex(value) for value in server_targets],
        "mapped_client_targets": mapped_client_targets,
        "mapped_server_targets": mapped_server_targets,
        "state2_client_ack_seen": 2 in client_ack_states,
        "state2_client_ack_return_success_seen": any(
            item.get("ret") == 0
            for item in callback_returns
        ),
        "state2_client_virtual_success_seen": any(
            item.get("state") == 2 and item.get("ret") == 0
            for item in client_virtual_returns
        ),
        "server_code5_seen": 5 in server_codes,
        "state2_server_ack_seen": 2 in server_ack_states,
        "state2_server_ack_return_success_seen": any(
            item.get("ret") == 0
            for item in server_write_returns
        ),
        "server_ontransact_return_success_seen": any(
            item.get("ret") == 0
            for item in server_ontransact_returns
        ),
    }


def parse_tracefs_output_v1173(text: str) -> dict[str, Any]:
    parsed = v1172.parse_tracefs_output_v1172(text)
    parsed["pm_ack_path"] = parse_ack_trace(text)
    return parsed


def patch_defaults() -> None:
    v1172.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    v1172.LATEST_POINTER = LATEST_POINTER
    v1172.DEFAULT_WORK_DIR = DEFAULT_WORK_DIR
    v1172.DEFAULT_CHILD_SCRIPT = DEFAULT_CHILD_SCRIPT
    v1172.DEFAULT_COLLECTOR_SCRIPT = DEFAULT_COLLECTOR_SCRIPT
    v1172.DEFAULT_CHILD_OUTPUT = DEFAULT_CHILD_OUTPUT
    v1172.PROOF_PREFIX = PROOF_PREFIX
    v1172.patch_defaults()
    _install_ack_event_specs()
    v1172.v1171.v1170.v1169.tracefs_collector_script_v1169 = tracefs_collector_script_v1173
    v1172.v1171.v1170.parse_tracefs_output_v1170 = parse_tracefs_output_v1173
    v1172.v1171.v1170.v1169.v1168.tracefs_collector_script_v1168 = tracefs_collector_script_v1173
    v1172.v1171.v1170.v1169.parse_tracefs_output_v1169 = parse_tracefs_output_v1173
    v1172.v1171.v1170.v1169.v1168.v1167.v1165.tracefs_collector_script_v1165 = (
        tracefs_collector_script_v1173
    )
    v1172.v1171.v1170.v1169.v1168.parse_tracefs_output_v1168 = parse_tracefs_output_v1173
    v1172.v1171.v1170.v1169.v1168.v1167.parse_tracefs_output_v1167 = parse_tracefs_output_v1173
    v1172.v1171.v1170.v1169.v1168.v1167.v1165.v1143.v1139.v1113.v1106.tracefs_collector_script = (
        tracefs_collector_script_v1173
    )
    v1172.v1171.v1170.v1169.v1168.v1167.v1165.v1143.v1139.v1113.v1106.parse_tracefs_output = (
        parse_tracefs_output_v1173
    )


def tracefs(manifest: dict[str, Any]) -> dict[str, Any]:
    return v1172.tracefs(manifest)


def pm_ack_path(manifest: dict[str, Any]) -> dict[str, Any]:
    value = tracefs(manifest).get("pm_ack_path") or {}
    return value if isinstance(value, dict) else {}


def decide_v1173(args: Any, manifest: dict[str, Any]) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return (
            "v1173-pm-ack-path-plan-ready",
            True,
            "plan-only; no device mutation, PM actor, mdm_helper, CNSS daemon, reboot, or Wi-Fi action executed",
            "run bounded PM ack path live with helper v217 and explicit allow flags",
        )

    base_decision, base_pass, base_reason, base_next = v1172.decide_v1172(args, manifest)
    ack = pm_ack_path(manifest)
    no_esoc0 = not v1172.v1171.esoc0_open_seen(manifest)
    if not base_pass:
        return (
            base_decision.replace("v1172", "v1173", 1),
            False,
            base_reason,
            base_next,
        )
    if not ack.get("event_count"):
        return (
            "v1173-state2-ack-client-missing",
            True,
            f"ack={ack}",
            "verify ack offsets and tracefs registration before changing PM ordering",
        )
    if not no_esoc0:
        return (
            "v1173-ack-path-opened-esoc0",
            True,
            f"ack={ack}",
            "move to bounded MHI/WLFW/BDF publication gate",
        )
    if ack.get("state2_client_ack_seen") and not ack.get("state2_server_ack_seen"):
        return (
            "v1173-state2-ack-client-no-server",
            True,
            f"ack={ack}",
            "classify Binder transaction target/timing for PM acknowledge",
        )
    if (
        ack.get("state2_client_ack_seen")
        and ack.get("state2_client_ack_return_success_seen")
        and ack.get("server_code5_seen")
        and ack.get("state2_server_ack_seen")
        and (
            ack.get("state2_server_ack_return_success_seen")
            or ack.get("server_ontransact_return_success_seen")
        )
        and no_esoc0
    ):
        return (
            "v1173-state2-ack-client-server-success-no-esoc0",
            True,
            f"ack={ack}",
            "trace the mapped PM-service ack implementation body or compare Android post-ack actor timing",
        )
    return (
        "v1173-pm-ack-path-unclassified",
        True,
        f"ack={ack} esoc0_open_seen={not no_esoc0}",
        "inspect ack trace values before choosing the next gate",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    base = v1172.render_summary(manifest).replace(
        "# V1172 CNSS Callback Body Live",
        "# V1173 PM Ack Path Live",
        1,
    )
    ack = pm_ack_path(manifest)
    rows = [
        ["event_count", ack.get("event_count", "")],
        ["by_label", json.dumps(ack.get("by_label", {}), sort_keys=True)],
        ["by_comm", json.dumps(ack.get("by_comm", {}), sort_keys=True)],
        ["client_ack_states", json.dumps(ack.get("client_ack_states", []))],
        ["client_ack_returns", json.dumps(ack.get("client_ack_returns", []), sort_keys=True)],
        ["server_codes", json.dumps(ack.get("server_codes", []))],
        ["server_ack_states", json.dumps(ack.get("server_ack_states", []))],
        ["client_virtual_returns", json.dumps(ack.get("client_virtual_returns", []), sort_keys=True)],
        ["server_write_returns", json.dumps(ack.get("server_write_returns", []), sort_keys=True)],
        ["server_ontransact_returns", json.dumps(ack.get("server_ontransact_returns", []), sort_keys=True)],
        ["mapped_client_targets", json.dumps(ack.get("mapped_client_targets", []), sort_keys=True)],
        ["mapped_server_targets", json.dumps(ack.get("mapped_server_targets", []), sort_keys=True)],
        ["state2_client_ack_seen", ack.get("state2_client_ack_seen", "")],
        ["state2_client_ack_return_success_seen", ack.get("state2_client_ack_return_success_seen", "")],
        ["state2_client_virtual_success_seen", ack.get("state2_client_virtual_success_seen", "")],
        ["server_code5_seen", ack.get("server_code5_seen", "")],
        ["state2_server_ack_seen", ack.get("state2_server_ack_seen", "")],
        ["state2_server_ack_return_success_seen", ack.get("state2_server_ack_return_success_seen", "")],
        ["server_ontransact_return_success_seen", ack.get("server_ontransact_return_success_seen", "")],
        ["esoc0_open_seen", v1172.v1171.esoc0_open_seen(manifest)],
    ]
    specs = [
        [item.get("label", ""), item.get("offset", ""), item.get("fetch", "")]
        for item in ack.get("event_specs", [])
    ]
    return base + "\n".join([
        "",
        "## V1173 PM Ack Path",
        "",
        markdown_table(["key", "value"], rows),
        "",
        "## V1173 Event Specs",
        "",
        markdown_table(["label", "offset", "fetch"], specs),
        "",
    ])


def main() -> int:
    patch_defaults()
    args = v1172.v1171.v1170.v1169.v1168.v1167.v1165.v1143.v1139.v1113.v1106.parse_args()
    v1172.v1171.v1170.v1169.v1168.v1167.v1165.v1143.v1139.v1113.set_global_defaults(args)
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = v1172.v1171.v1170.v1169.v1168.v1167.v1165.v1143.v1139.v1113.v1106.build_manifest(args, store)
    manifest["base_v1172_decision"] = manifest.get("decision", "")
    manifest["cycle"] = "v1173"
    manifest["generated_at"] = now_iso()
    manifest["v1172_manifest"] = str(DEFAULT_V1172_MANIFEST)
    decision, passed, reason, next_step = decide_v1173(args, manifest)
    manifest.update({"decision": decision, "pass": passed, "reason": reason, "next_step": next_step})

    fw = v1172.v1171.v1170.v1169.v1168.v1167.v1165.v1143.v1139.global_firmware(manifest)
    values = v1172.v1171.v1170.v1169.v1168.v1167.v1165.v1143.v1139.contract(manifest)
    post = v1172.v1171.v1170.v1169.v1168.v1167.v1165.v1143.v1139.post_pm(manifest)
    lower = v1172.v1171.v1170.v1169.v1168.v1167.v1165.v1143.lower_trace(manifest)
    late = v1172.v1171.v1170.v1169.v1168.v1167.v1165.late_per_proxy(manifest)
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

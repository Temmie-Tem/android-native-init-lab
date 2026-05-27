#!/usr/bin/env python3
"""V1170 bounded libperipheral callback transact live gate.

This V1169 derivative traces the mapped `libperipheral_client.so+0x8a5c`
callback stub.  It captures state write, remote binder pointer, transact call
arguments, transact return, and function return.  It does not start Wi-Fi HAL,
scan/connect/link-up, use credentials, run DHCP/routes, external ping, write
boot/partitions, or flash.
"""

from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

import native_wifi_pm_callback_maps_live_v1169 as v1169
from a90_kernel_tools import markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1170-pm-callback-transact-live")
LATEST_POINTER = Path("tmp/wifi/latest-v1170-pm-callback-transact-live.txt")
DEFAULT_WORK_DIR = "/cache/a90-runtime/v1170"
DEFAULT_CHILD_SCRIPT = "/cache/a90-runtime/v1170/pm-callback-transact-child.sh"
DEFAULT_COLLECTOR_SCRIPT = "/cache/a90-runtime/v1170/pm-callback-transact-collector.sh"
DEFAULT_CHILD_OUTPUT = "/cache/a90-runtime/v1170/pm-callback-transact-output.txt"
PROOF_PREFIX = "/tmp/a90-v1170-"
DEFAULT_V1169_MANIFEST = Path("tmp/wifi/v1169-pm-callback-maps-live-after-v490/manifest.json")

TRANSACT_EVENT_SPECS = (
    ("pm_client_callback_stub_entry", "client", "8a5c", "object=%x0 state=%x1"),
    ("pm_client_callback_write_state", "client", "8adc", "parcel=%x0 state=%x1"),
    ("pm_client_callback_remote_binder", "client", "8ae4", "object=%x20 remote_binder=%x0 state_saved=%x19"),
    ("pm_client_callback_transact_call", "client", "8afc", "remote_binder=%x0 code=%x1 data=%x2 reply=%x3 flags=%x4 transact_target=%x8 state_saved=%x19"),
    ("pm_client_callback_transact_return", "client", "8b00", "transact_ret=%x0 state_saved=%x19"),
    ("pm_client_callback_function_ret", "client", "8a5c", "ret=$retval"),
)
TRANSACT_LABELS = {label for label, _binary_key, _offset, _fetch in TRANSACT_EVENT_SPECS}
VALUE_RE = re.compile(
    r"\b(?P<key>object|state|parcel|remote_binder|state_saved|code|data|reply|flags|"
    r"transact_target|transact_ret|ret)=(?P<value>0x[0-9A-Fa-f]+|-?[0-9]+)"
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


def _install_transact_event_specs() -> None:
    tracebase = v1169.v1168.v1167.v1165.v1143.v1139.v1113.v1106
    existing = {label for label, _binary_key, _offset, _fetch in tracebase.EVENT_SPECS}
    additions = tuple(spec for spec in TRANSACT_EVENT_SPECS if spec[0] not in existing)
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


_base_parse_tracefs_output_v1169 = v1169.parse_tracefs_output_v1169


def _trace_match(line: str) -> tuple[str, str] | None:
    match = v1169.v1168.v1167.v1165.v1143.v1139.v1113.v1106.TRACE_LINE_RE.match(line)
    if not match:
        return None
    return match.group("comm").strip(), match.group("label")


def _value_map(line: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for match in VALUE_RE.finditer(line):
        values[match.group("key")] = match.group("value")
    return values


def parse_transact_trace(text: str) -> dict[str, Any]:
    trace_lines = v1169.v1168.v1167.v1165.v1143.v1139.v1113.v1106.collect_trace_lines(text)
    events: list[dict[str, Any]] = []
    by_label: dict[str, int] = {label: 0 for label in sorted(TRANSACT_LABELS)}
    by_comm: dict[str, dict[str, int]] = {}
    for line in trace_lines:
        matched = _trace_match(line)
        if not matched:
            continue
        comm, label = matched
        if label not in TRANSACT_LABELS:
            continue
        values = _value_map(line)
        events.append({"comm": comm, "label": label, "values": values, "line": line.strip()})
        by_label[label] = by_label.get(label, 0) + 1
        by_comm.setdefault(comm, {})
        by_comm[comm][label] = by_comm[comm].get(label, 0) + 1

    transact_results: list[dict[str, Any]] = []
    for event in events:
        if event["label"] != "pm_client_callback_transact_return":
            continue
        if "transact_ret" not in event["values"]:
            continue
        ret = intish(event["values"].get("transact_ret"))
        state = intish(event["values"].get("state_saved"), -1)
        transact_results.append({
            "comm": event["comm"],
            "state": state,
            "ret": ret,
            "ret_signed32": signed32(ret),
            "ret_hex": event["values"].get("transact_ret", ""),
            "line": event["line"],
        })
    transact_returns = [item["ret"] for item in transact_results]
    state2_transact_results = [item for item in transact_results if item["state"] == 2]
    nonzero_transact_results = [item for item in transact_results if item["ret"] != 0]
    transact_codes = [
        intish(event["values"].get("code"))
        for event in events
        if event["label"] == "pm_client_callback_transact_call"
        and "code" in event["values"]
    ]
    state_values = [
        intish(event["values"].get("state", event["values"].get("state_saved")))
        for event in events
        if "state" in event["values"] or "state_saved" in event["values"]
    ]
    remote_binders = sorted({
        event["values"].get("remote_binder", "")
        for event in events
        if event["values"].get("remote_binder")
    })
    transact_targets = sorted({
        event["values"].get("transact_target", "")
        for event in events
        if event["values"].get("transact_target")
    })
    return {
        "event_specs": [
            {"label": label, "binary_key": binary_key, "offset": offset, "fetch": fetch}
            for label, binary_key, offset, fetch in TRANSACT_EVENT_SPECS
        ],
        "events": events[:120],
        "event_count": len(events),
        "by_label": by_label,
        "by_comm": by_comm,
        "state_values": state_values,
        "state2_seen": 2 in state_values,
        "transact_codes": transact_codes,
        "transact_returns": transact_returns,
        "transact_results": transact_results,
        "transact_success_seen": any(value == 0 for value in transact_returns),
        "transact_failure_seen": any(value != 0 for value in transact_returns),
        "nonzero_transact_results": nonzero_transact_results,
        "state2_transact_results": state2_transact_results,
        "state2_transact_returns": [item["ret"] for item in state2_transact_results],
        "state2_transact_success_seen": any(item["ret"] == 0 for item in state2_transact_results),
        "state2_transact_failure_seen": any(item["ret"] != 0 for item in state2_transact_results),
        "remote_binders": remote_binders,
        "transact_targets": transact_targets,
        "transact_call_seen": bool(by_label.get("pm_client_callback_transact_call")),
        "transact_return_seen": bool(transact_returns),
    }


def parse_tracefs_output_v1170(text: str) -> dict[str, Any]:
    parsed = _base_parse_tracefs_output_v1169(text)
    parsed["pm_callback_transact"] = parse_transact_trace(text)
    return parsed


def patch_defaults() -> None:
    v1169.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    v1169.LATEST_POINTER = LATEST_POINTER
    v1169.DEFAULT_WORK_DIR = DEFAULT_WORK_DIR
    v1169.DEFAULT_CHILD_SCRIPT = DEFAULT_CHILD_SCRIPT
    v1169.DEFAULT_COLLECTOR_SCRIPT = DEFAULT_COLLECTOR_SCRIPT
    v1169.DEFAULT_CHILD_OUTPUT = DEFAULT_CHILD_OUTPUT
    v1169.PROOF_PREFIX = PROOF_PREFIX
    _install_transact_event_specs()
    v1169.parse_tracefs_output_v1169 = parse_tracefs_output_v1170
    v1169.patch_defaults()


def tracefs(manifest: dict[str, Any]) -> dict[str, Any]:
    return v1169.tracefs(manifest)


def callback_dispatch(manifest: dict[str, Any]) -> dict[str, Any]:
    return v1169.callback_dispatch(manifest)


def callback_transact(manifest: dict[str, Any]) -> dict[str, Any]:
    value = tracefs(manifest).get("pm_callback_transact") or {}
    return value if isinstance(value, dict) else {}


def decide_v1170(args: Any, manifest: dict[str, Any]) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return (
            "v1170-pm-callback-transact-plan-ready",
            True,
            "plan-only; no device mutation, PM actor, mdm_helper, CNSS daemon, reboot, or Wi-Fi action executed",
            "run bounded callback-transact live with helper v217 and explicit allow flags",
        )

    base_decision, base_pass, base_reason, base_next = v1169.decide_v1169(args, manifest)
    transact = callback_transact(manifest)
    if not base_pass:
        return (
            base_decision.replace("v1169", "v1170", 1),
            False,
            base_reason,
            base_next,
        )
    if not transact.get("event_count"):
        return (
            "v1170-callback-transact-events-missing",
            False,
            f"transact={transact}",
            "verify libperipheral_client.so offset mapping and uprobe registration",
        )
    if not transact.get("transact_call_seen"):
        return (
            "v1170-callback-transact-call-missing",
            True,
            f"transact={transact}",
            "trace the callback stub between 0x8a5c and 0x8afc",
        )
    if not transact.get("transact_return_seen"):
        return (
            "v1170-callback-transact-return-missing",
            True,
            f"transact={transact}",
            "extend post-call probes or classify Binder transact blocking",
        )
    if transact.get("state2_transact_failure_seen") and not transact.get("state2_transact_success_seen"):
        return (
            "v1170-state2-callback-transact-failed",
            True,
            f"transact={transact}",
            "classify primary state=2 Binder status failure before any Wi-Fi HAL or scan/connect gate",
        )
    if transact.get("state2_transact_success_seen"):
        return (
            "v1170-state2-transact-success-no-esoc0",
            True,
            f"transact={transact}",
            "trace the receiving client-side Binder callback handler that should act on state=2",
        )
    if transact.get("transact_failure_seen"):
        return (
            "v1170-callback-transact-failed-nonprimary",
            True,
            f"transact={transact}",
            "classify non-primary Binder status failure while tracing the state=2 receiver path",
        )
    if transact.get("transact_success_seen"):
        return (
            "v1170-callback-transact-success-no-esoc0",
            True,
            f"transact={transact}",
            "trace the receiving client-side Binder callback handler that should act on state=2",
        )
    return (
        "v1170-callback-transact-unclassified",
        True,
        f"transact={transact}",
        "inspect callback transact trace values before choosing the next gate",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    base = v1169.render_summary(manifest).replace(
        "# V1169 PM-Service Callback Maps Live",
        "# V1170 PM-Service Callback Transact Live",
        1,
    )
    transact = callback_transact(manifest)
    rows = [
        ["event_count", transact.get("event_count", "")],
        ["by_label", json.dumps(transact.get("by_label", {}), sort_keys=True)],
        ["state_values", json.dumps(transact.get("state_values", []))],
        ["transact_codes", json.dumps(transact.get("transact_codes", []))],
        ["transact_returns", json.dumps(transact.get("transact_returns", []))],
        ["transact_results", json.dumps(transact.get("transact_results", []), sort_keys=True)],
        ["transact_success_seen", transact.get("transact_success_seen", "")],
        ["transact_failure_seen", transact.get("transact_failure_seen", "")],
        ["state2_transact_returns", json.dumps(transact.get("state2_transact_returns", []))],
        ["state2_transact_success_seen", transact.get("state2_transact_success_seen", "")],
        ["state2_transact_failure_seen", transact.get("state2_transact_failure_seen", "")],
        ["nonzero_transact_results", json.dumps(transact.get("nonzero_transact_results", []), sort_keys=True)],
        ["remote_binders", json.dumps(transact.get("remote_binders", []))],
        ["transact_targets", json.dumps(transact.get("transact_targets", []))],
    ]
    specs = [
        [item.get("label", ""), item.get("offset", ""), item.get("fetch", "")]
        for item in transact.get("event_specs", [])
    ]
    return base + "\n".join([
        "",
        "## V1170 PM-Service Callback Transact",
        "",
        markdown_table(["key", "value"], rows),
        "",
        "## V1170 Event Specs",
        "",
        markdown_table(["label", "offset", "fetch"], specs),
        "",
    ])


def main() -> int:
    patch_defaults()
    args = v1169.v1168.v1167.v1165.v1143.v1139.v1113.v1106.parse_args()
    v1169.v1168.v1167.v1165.v1143.v1139.v1113.set_global_defaults(args)
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = v1169.v1168.v1167.v1165.v1143.v1139.v1113.v1106.build_manifest(args, store)
    manifest["base_v1169_decision"] = manifest.get("decision", "")
    manifest["cycle"] = "v1170"
    manifest["generated_at"] = now_iso()
    manifest["v1169_manifest"] = str(DEFAULT_V1169_MANIFEST)
    decision, passed, reason, next_step = decide_v1170(args, manifest)
    manifest.update({"decision": decision, "pass": passed, "reason": reason, "next_step": next_step})

    fw = v1169.v1168.v1167.v1165.v1143.v1139.global_firmware(manifest)
    values = v1169.v1168.v1167.v1165.v1143.v1139.contract(manifest)
    post = v1169.v1168.v1167.v1165.v1143.v1139.post_pm(manifest)
    lower = v1169.v1168.v1167.v1165.v1143.lower_trace(manifest)
    late = v1169.v1168.v1167.v1165.late_per_proxy(manifest)
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

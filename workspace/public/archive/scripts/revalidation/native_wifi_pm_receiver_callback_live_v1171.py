#!/usr/bin/env python3
"""V1171 bounded PM receiver callback live gate.

This V1170 derivative traces the receiver side of the successful `state=2`
Binder callback: `BnPeriperalManagerCb::onTransact`, `EventNotifier`, and the
local callback branch.  It also samples `cnss-daemon` and `pm-proxy` maps so
branch targets can be mapped.  It does not start Wi-Fi HAL, scan/connect/link-up,
use credentials, run DHCP/routes, external ping, write boot/partitions, or
flash.
"""

from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

import native_wifi_pm_callback_transact_live_v1170 as v1170
from a90_kernel_tools import markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1171-pm-receiver-callback-live")
LATEST_POINTER = Path("tmp/wifi/latest-v1171-pm-receiver-callback-live.txt")
DEFAULT_WORK_DIR = "/cache/a90-runtime/v1171"
DEFAULT_CHILD_SCRIPT = "/cache/a90-runtime/v1171/pm-receiver-callback-child.sh"
DEFAULT_COLLECTOR_SCRIPT = "/cache/a90-runtime/v1171/pm-receiver-callback-collector.sh"
DEFAULT_CHILD_OUTPUT = "/cache/a90-runtime/v1171/pm-receiver-callback-output.txt"
PROOF_PREFIX = "/tmp/a90-v1171-"
DEFAULT_V1170_MANIFEST = Path("tmp/wifi/v1170-pm-callback-transact-live-after-v490/manifest.json")

RECEIVER_EVENT_SPECS = (
    ("pm_receiver_cb_ontransact_entry", "client", "824c", "this=%x0 code=%x1 data=%x2 reply=%x3 flags=%x4"),
    ("pm_receiver_cb_read_state_return", "client", "8284", "this=%x20 data=%x19 state=%x0"),
    ("pm_receiver_cb_notify_call", "client", "8294", "this=%x20 state=%x1 notify_target=%x8"),
    ("pm_receiver_cb_ontransact_ret", "client", "824c", "ret=$retval"),
    ("pm_receiver_cb_ontransact_thunk_entry", "client", "82cc", "this=%x0 code=%x1 data=%x2 reply=%x3 flags=%x4"),
    ("pm_receiver_cb_thunk_read_state_return", "client", "8304", "this=%x20 data=%x19 state=%x0"),
    ("pm_receiver_cb_thunk_notify_call", "client", "8314", "this=%x20 state=%x1 notify_target=%x8"),
    ("pm_receiver_cb_ontransact_thunk_ret", "client", "82cc", "ret=$retval"),
    ("pm_event_notifier_entry", "client", "6d84", "object=%x0 state=%x1"),
    ("pm_event_notifier_callback_ready", "client", "6d8c", "object=%x0 state=%x1 callback=%x2"),
    ("pm_event_notifier_callback_branch", "client", "6d90", "callback_arg=%x0 state=%x1 callback=%x2"),
)
RECEIVER_LABELS = {label for label, _binary_key, _offset, _fetch in RECEIVER_EVENT_SPECS}
VALUE_RE = re.compile(
    r"\b(?P<key>this|code|data|reply|flags|state|notify_target|ret|object|callback_arg|callback)="
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
    return v1170.v1169.v1168.v1167.v1165.v1143.v1139.v1113.v1106


def _install_receiver_event_specs() -> None:
    tracebase = _tracebase()
    existing = {label for label, _binary_key, _offset, _fetch in tracebase.EVENT_SPECS}
    additions = tuple(spec for spec in RECEIVER_EVENT_SPECS if spec[0] not in existing)
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


_base_tracefs_collector_script_v1169 = v1170.v1169.tracefs_collector_script_v1169
_base_parse_tracefs_output_v1170 = v1170.parse_tracefs_output_v1170


def tracefs_collector_script_v1171(args: Any) -> str:
    script = _base_tracefs_collector_script_v1169(args)
    function_anchor = 'echo "pm_service_maps_sample_end index=$idx"\n}\n\n'
    proxy_functions = '''echo "pm_service_maps_sample_end index=$idx"
}

find_pm_proxy_pid() {
  for proc in /proc/[0-9]*; do
    pid="${proc##*/}"
    comm=$($BB cat "$proc/comm" 2>/dev/null || true)
    cmdline=$($BB tr '\\000' ' ' < "$proc/cmdline" 2>/dev/null || true)
    first_arg="${cmdline%% *}"
    case "$comm:$first_arg" in
      pm-proxy:*|*:*/pm-proxy|*:pm-proxy)
        echo "$pid"
        return 0
        ;;
    esac
  done
  return 1
}

sample_pm_proxy_maps() {
  idx="$1"
  echo "pm_proxy_maps_sample_begin index=$idx"
  proxy_pid=$(find_pm_proxy_pid || true)
  echo "pm_proxy_maps_sample_pid index=$idx pid=$proxy_pid"
  if $BB test -n "$proxy_pid" && $BB test -r "/proc/$proxy_pid/maps"; then
    $BB cat "/proc/$proxy_pid/maps" 2>/dev/null || true
    echo "pm_proxy_maps_sample_cat_rc index=$idx rc=$?"
  else
    echo "pm_proxy_maps_sample_unavailable index=$idx"
  fi
  echo "pm_proxy_maps_sample_end index=$idx"
}

find_cnss_daemon_pid() {
  for proc in /proc/[0-9]*; do
    pid="${proc##*/}"
    comm=$($BB cat "$proc/comm" 2>/dev/null || true)
    cmdline=$($BB tr '\\000' ' ' < "$proc/cmdline" 2>/dev/null || true)
    first_arg="${cmdline%% *}"
    case "$comm:$first_arg" in
      cnss-daemon:*|*:*/cnss-daemon|*:cnss-daemon)
        echo "$pid"
        return 0
        ;;
    esac
  done
  return 1
}

sample_cnss_daemon_maps() {
  idx="$1"
  echo "cnss_daemon_maps_sample_begin index=$idx"
  cnss_pid=$(find_cnss_daemon_pid || true)
  echo "cnss_daemon_maps_sample_pid index=$idx pid=$cnss_pid"
  if $BB test -n "$cnss_pid" && $BB test -r "/proc/$cnss_pid/maps"; then
    $BB cat "/proc/$cnss_pid/maps" 2>/dev/null || true
    echo "cnss_daemon_maps_sample_cat_rc index=$idx rc=$?"
  else
    echo "cnss_daemon_maps_sample_unavailable index=$idx"
  fi
  echo "cnss_daemon_maps_sample_end index=$idx"
}

'''
    if function_anchor not in script:
        raise RuntimeError("V1169 collector pm-service maps insertion point changed")
    script = script.replace(function_anchor, proxy_functions, 1)
    loop_anchor = '  sample_pm_service_maps "$sample_index"\n'
    loop_replacement = (
        '  sample_pm_service_maps "$sample_index"\n'
        '  sample_pm_proxy_maps "$sample_index"\n'
        '  sample_cnss_daemon_maps "$sample_index"\n'
    )
    if loop_anchor not in script:
        raise RuntimeError("V1169 collector sample loop insertion point changed")
    return script.replace(loop_anchor, loop_replacement, 1)


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


def parse_named_sample_maps(text: str, prefix: str) -> dict[str, Any]:
    samples: list[dict[str, Any]] = []
    current_index = ""
    current_lines: list[str] = []
    in_sample = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith(f"{prefix}_maps_sample_begin "):
            in_sample = True
            current_index = stripped.split("index=", 1)[-1]
            current_lines = []
            continue
        if stripped.startswith(f"{prefix}_maps_sample_end "):
            entries = []
            for raw in current_lines:
                match = v1170.v1169.v1168.MAP_RE.match(raw)
                if not match:
                    continue
                entries.append({
                    "start": int(match.group("start"), 16),
                    "end": int(match.group("end"), 16),
                    "perms": match.group("perms"),
                    "offset": int(match.group("offset"), 16),
                    "path": match.group("path").strip(),
                    "line": raw,
                })
            samples.append({"index": current_index, "entry_count": len(entries), "entries": entries})
            in_sample = False
            current_index = ""
            current_lines = []
            continue
        if in_sample and not stripped.startswith(f"{prefix}_maps_sample_"):
            current_lines.append(line.rstrip())
    all_entries = [entry for sample in samples for entry in sample["entries"]]
    return {
        "sample_count": len(samples),
        "samples_with_entries": sum(1 for sample in samples if sample["entry_count"] > 0),
        "entry_count": len(all_entries),
        "samples": [
            {
                "index": sample["index"],
                "entry_count": sample["entry_count"],
                "entries": [
                    {
                        "start": hex(entry["start"]),
                        "end": hex(entry["end"]),
                        "perms": entry["perms"],
                        "offset": hex(entry["offset"]),
                        "path": entry["path"],
                        "line": entry["line"],
                    }
                    for entry in sample["entries"][:16]
                ],
            }
            for sample in samples[:16]
        ],
        "entries": all_entries,
    }


def parse_receiver_trace(text: str) -> dict[str, Any]:
    trace_lines = _tracebase().collect_trace_lines(text)
    proxy_maps = parse_named_sample_maps(text, "pm_proxy")
    cnss_maps = parse_named_sample_maps(text, "cnss_daemon")
    events: list[dict[str, Any]] = []
    by_label: dict[str, int] = {label: 0 for label in sorted(RECEIVER_LABELS)}
    by_comm: dict[str, dict[str, int]] = {}
    for line in trace_lines:
        matched = _trace_match(line)
        if not matched:
            continue
        comm, label = matched
        if label not in RECEIVER_LABELS:
            continue
        values = _value_map(line)
        events.append({"comm": comm, "label": label, "values": values, "line": line.strip()})
        by_label[label] = by_label.get(label, 0) + 1
        by_comm.setdefault(comm, {})
        by_comm[comm][label] = by_comm[comm].get(label, 0) + 1

    state_values = [
        intish(event["values"].get("state"))
        for event in events
        if "state" in event["values"]
    ]
    ontransact_codes = [
        intish(event["values"].get("code"))
        for event in events
        if event["label"] in {"pm_receiver_cb_ontransact_entry", "pm_receiver_cb_ontransact_thunk_entry"}
        and "code" in event["values"]
    ]
    ontransact_returns = []
    for event in events:
        if event["label"] not in {"pm_receiver_cb_ontransact_ret", "pm_receiver_cb_ontransact_thunk_ret"} or "ret" not in event["values"]:
            continue
        ret = intish(event["values"].get("ret"))
        ontransact_returns.append({"comm": event["comm"], "ret": ret, "ret_signed32": signed32(ret), "ret_hex": event["values"].get("ret", "")})
    callback_values = [
        intish(event["values"].get("callback"))
        for event in events
        if event["label"] == "pm_event_notifier_callback_branch"
        and "callback" in event["values"]
    ]
    mapped_callbacks = []
    for value in callback_values:
        mapped = v1170.v1169.v1168.map_pointer(value, cnss_maps["entries"])
        mapped["receiver"] = "cnss-daemon" if mapped.get("path") else ""
        if not mapped.get("path"):
            mapped = v1170.v1169.v1168.map_pointer(value, proxy_maps["entries"])
            mapped["receiver"] = "pm-proxy" if mapped.get("path") else ""
        mapped_callbacks.append(mapped)
    unique_mapped_callbacks = []
    seen: set[tuple[str, str]] = set()
    for item in mapped_callbacks:
        key = (str(item.get("pointer", "")), str(item.get("path", "")))
        if key in seen:
            continue
        seen.add(key)
        unique_mapped_callbacks.append(item)
    callback_to_pm_proxy_seen = any(
        item.get("receiver") == "pm-proxy"
        for item in mapped_callbacks
    )
    callback_to_cnss_daemon_seen = any(
        item.get("receiver") == "cnss-daemon"
        for item in mapped_callbacks
    )
    return {
        "event_specs": [
            {"label": label, "binary_key": binary_key, "offset": offset, "fetch": fetch}
            for label, binary_key, offset, fetch in RECEIVER_EVENT_SPECS
        ],
        "events": events[:120],
        "event_count": len(events),
        "by_label": by_label,
        "by_comm": by_comm,
        "state_values": state_values,
        "state2_seen": 2 in state_values,
        "state2_read_seen": any(
            event["label"] in {"pm_receiver_cb_read_state_return", "pm_receiver_cb_thunk_read_state_return"}
            and intish(event["values"].get("state")) == 2
            for event in events
        ),
        "state2_notify_call_seen": any(
            event["label"] in {"pm_receiver_cb_notify_call", "pm_receiver_cb_thunk_notify_call"}
            and intish(event["values"].get("state")) == 2
            for event in events
        ),
        "state2_branch_seen": any(
            event["label"] == "pm_event_notifier_callback_branch"
            and intish(event["values"].get("state")) == 2
            for event in events
        ),
        "ontransact_codes": ontransact_codes,
        "ontransact_returns": ontransact_returns,
        "callback_values": [hex(value) for value in callback_values],
        "mapped_callbacks": mapped_callbacks,
        "unique_mapped_callbacks": unique_mapped_callbacks,
        "callback_to_cnss_daemon_seen": callback_to_cnss_daemon_seen,
        "callback_to_pm_proxy_seen": callback_to_pm_proxy_seen,
        "cnss_daemon_maps": {
            key: value
            for key, value in cnss_maps.items()
            if key != "entries"
        },
        "pm_proxy_maps": {
            key: value
            for key, value in proxy_maps.items()
            if key != "entries"
        },
    }


def parse_tracefs_output_v1171(text: str) -> dict[str, Any]:
    parsed = _base_parse_tracefs_output_v1170(text)
    parsed["pm_receiver_callback"] = parse_receiver_trace(text)
    return parsed


def patch_defaults() -> None:
    v1170.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    v1170.LATEST_POINTER = LATEST_POINTER
    v1170.DEFAULT_WORK_DIR = DEFAULT_WORK_DIR
    v1170.DEFAULT_CHILD_SCRIPT = DEFAULT_CHILD_SCRIPT
    v1170.DEFAULT_COLLECTOR_SCRIPT = DEFAULT_COLLECTOR_SCRIPT
    v1170.DEFAULT_CHILD_OUTPUT = DEFAULT_CHILD_OUTPUT
    v1170.PROOF_PREFIX = PROOF_PREFIX
    _install_receiver_event_specs()
    v1170.v1169.tracefs_collector_script_v1169 = tracefs_collector_script_v1171
    v1170.parse_tracefs_output_v1170 = parse_tracefs_output_v1171
    v1170.patch_defaults()


def tracefs(manifest: dict[str, Any]) -> dict[str, Any]:
    return v1170.tracefs(manifest)


def callback_transact(manifest: dict[str, Any]) -> dict[str, Any]:
    return v1170.callback_transact(manifest)


def receiver_callback(manifest: dict[str, Any]) -> dict[str, Any]:
    value = tracefs(manifest).get("pm_receiver_callback") or {}
    return value if isinstance(value, dict) else {}


def esoc0_open_seen(manifest: dict[str, Any]) -> bool:
    tfs = tracefs(manifest)
    for section_name in ("late_per_proxy_polls", "mdm_helper_queue_timing"):
        section = tfs.get(section_name) or {}
        if not isinstance(section, dict):
            continue
        for key, value in section.items():
            key_text = str(key)
            if not key_text.endswith(("per_mgr_subsys_esoc0_count", "per_mgr_esoc0_count")):
                continue
            if intish(value) > 0:
                return True
    return False


def decide_v1171(args: Any, manifest: dict[str, Any]) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return (
            "v1171-pm-receiver-callback-plan-ready",
            True,
            "plan-only; no device mutation, PM actor, mdm_helper, CNSS daemon, reboot, or Wi-Fi action executed",
            "run bounded receiver-callback live with helper v217 and explicit allow flags",
        )

    base_decision, base_pass, base_reason, base_next = v1170.decide_v1170(args, manifest)
    receiver = receiver_callback(manifest)
    no_esoc0 = not esoc0_open_seen(manifest)
    if not base_pass:
        return (
            base_decision.replace("v1170", "v1171", 1),
            False,
            base_reason,
            base_next,
        )
    if not callback_transact(manifest).get("state2_transact_success_seen"):
        return (
            "v1171-state2-transact-precondition-missing",
            False,
            f"transact={callback_transact(manifest)}",
            "restore V1170 state=2 transact success before receiver tracing",
        )
    if not receiver.get("event_count"):
        return (
            "v1171-receiver-callback-not-observed-after-state2-transact",
            True,
            f"receiver={receiver}",
            "classify Binder one-way delivery timing or receiver lifetime before changing PM ordering",
        )
    if receiver.get("state2_branch_seen") and receiver.get("callback_to_cnss_daemon_seen") and no_esoc0:
        return (
            "v1171-state2-cnss-callback-dispatched-no-esoc0",
            True,
            f"receiver={receiver}",
            "trace the mapped cnss-daemon callback function body and its PM/eSoC action branch",
        )
    if receiver.get("callback_to_pm_proxy_seen") and no_esoc0:
        return (
            "v1171-state2-receiver-callback-dispatched-no-esoc0",
            True,
            f"receiver={receiver}",
            "trace the mapped pm-proxy callback function body and its PM/eSoC action branch",
        )
    if receiver.get("state2_branch_seen") and no_esoc0:
        return (
            "v1171-state2-receiver-callback-dispatched-unmapped",
            True,
            f"receiver={receiver}",
            "improve receiver maps sampling, then trace the receiver callback function body",
        )
    if not receiver.get("state2_read_seen"):
        return (
            "v1171-receiver-ontransact-without-state2",
            True,
            f"receiver={receiver}",
            "trace Parcel check/read path or extend receiver offsets",
        )
    if not receiver.get("state2_branch_seen"):
        return (
            "v1171-state2-receiver-ontransact-no-notifier-branch",
            True,
            f"receiver={receiver}",
            "trace EventNotifier dispatch guard and object lifetime before changing PM ordering",
        )
    return (
        "v1171-state2-receiver-callback-unclassified",
        True,
        f"receiver={receiver} esoc0_open_seen={not no_esoc0}",
        "inspect receiver callback trace values before choosing the next gate",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    base = v1170.render_summary(manifest).replace(
        "# V1170 PM-Service Callback Transact Live",
        "# V1171 PM Receiver Callback Live",
        1,
    )
    receiver = receiver_callback(manifest)
    rows = [
        ["event_count", receiver.get("event_count", "")],
        ["by_label", json.dumps(receiver.get("by_label", {}), sort_keys=True)],
        ["by_comm", json.dumps(receiver.get("by_comm", {}), sort_keys=True)],
        ["state_values", json.dumps(receiver.get("state_values", []))],
        ["state2_read_seen", receiver.get("state2_read_seen", "")],
        ["state2_notify_call_seen", receiver.get("state2_notify_call_seen", "")],
        ["state2_branch_seen", receiver.get("state2_branch_seen", "")],
        ["ontransact_codes", json.dumps(receiver.get("ontransact_codes", []))],
        ["ontransact_returns", json.dumps(receiver.get("ontransact_returns", []), sort_keys=True)],
        ["callback_values", json.dumps(receiver.get("callback_values", []))],
        ["unique_mapped_callbacks", json.dumps(receiver.get("unique_mapped_callbacks", []), sort_keys=True)],
        ["callback_to_cnss_daemon_seen", receiver.get("callback_to_cnss_daemon_seen", "")],
        ["callback_to_pm_proxy_seen", receiver.get("callback_to_pm_proxy_seen", "")],
        ["cnss_daemon_maps", json.dumps(receiver.get("cnss_daemon_maps", {}), sort_keys=True)],
        ["pm_proxy_maps", json.dumps(receiver.get("pm_proxy_maps", {}), sort_keys=True)],
        ["esoc0_open_seen", esoc0_open_seen(manifest)],
    ]
    specs = [
        [item.get("label", ""), item.get("offset", ""), item.get("fetch", "")]
        for item in receiver.get("event_specs", [])
    ]
    return base + "\n".join([
        "",
        "## V1171 PM Receiver Callback",
        "",
        markdown_table(["key", "value"], rows),
        "",
        "## V1171 Event Specs",
        "",
        markdown_table(["label", "offset", "fetch"], specs),
        "",
    ])


def main() -> int:
    patch_defaults()
    args = v1170.v1169.v1168.v1167.v1165.v1143.v1139.v1113.v1106.parse_args()
    v1170.v1169.v1168.v1167.v1165.v1143.v1139.v1113.set_global_defaults(args)
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = v1170.v1169.v1168.v1167.v1165.v1143.v1139.v1113.v1106.build_manifest(args, store)
    manifest["base_v1170_decision"] = manifest.get("decision", "")
    manifest["cycle"] = "v1171"
    manifest["generated_at"] = now_iso()
    manifest["v1170_manifest"] = str(DEFAULT_V1170_MANIFEST)
    decision, passed, reason, next_step = decide_v1171(args, manifest)
    manifest.update({"decision": decision, "pass": passed, "reason": reason, "next_step": next_step})

    fw = v1170.v1169.v1168.v1167.v1165.v1143.v1139.global_firmware(manifest)
    values = v1170.v1169.v1168.v1167.v1165.v1143.v1139.contract(manifest)
    post = v1170.v1169.v1168.v1167.v1165.v1143.v1139.post_pm(manifest)
    lower = v1170.v1169.v1168.v1167.v1165.v1143.lower_trace(manifest)
    late = v1170.v1169.v1168.v1167.v1165.late_per_proxy(manifest)
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

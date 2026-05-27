#!/usr/bin/env python3
"""V1169 bounded PM-service callback maps live gate.

This V1168 derivative moves pm-service maps capture into the live sampling loop
so the callback pointer observed at 0x8644 can be mapped while pm-service is
still alive.  It does not start Wi-Fi HAL, scan/connect/link-up, use
credentials, run DHCP/routes, external ping, write boot/partitions, or flash.
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Any

import native_wifi_pm_callback_dispatch_live_v1168 as v1168
from a90_kernel_tools import markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1169-pm-callback-maps-live")
LATEST_POINTER = Path("tmp/wifi/latest-v1169-pm-callback-maps-live.txt")
DEFAULT_WORK_DIR = "/cache/a90-runtime/v1169"
DEFAULT_CHILD_SCRIPT = "/cache/a90-runtime/v1169/pm-callback-maps-child.sh"
DEFAULT_COLLECTOR_SCRIPT = "/cache/a90-runtime/v1169/pm-callback-maps-collector.sh"
DEFAULT_CHILD_OUTPUT = "/cache/a90-runtime/v1169/pm-callback-maps-output.txt"
PROOF_PREFIX = "/tmp/a90-v1169-"
DEFAULT_V1168_MANIFEST = Path("tmp/wifi/v1168-pm-callback-dispatch-live-after-v490/manifest.json")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


_base_tracefs_collector_script_v1168 = v1168.tracefs_collector_script_v1168
_base_parse_tracefs_output_v1168 = v1168.parse_tracefs_output_v1168


def tracefs_collector_script_v1169(args: Any) -> str:
    script = _base_tracefs_collector_script_v1168(args)
    function_anchor = 'echo "thread_sample_end index=$idx"\n}\n\n'
    maps_function = '''echo "thread_sample_end index=$idx"
}

sample_pm_service_maps() {
  idx="$1"
  echo "pm_service_maps_sample_begin index=$idx"
  pm_pid=$(find_pm_service_pid || true)
  echo "pm_service_maps_sample_pid index=$idx pid=$pm_pid"
  if $BB test -n "$pm_pid" && $BB test -r "/proc/$pm_pid/maps"; then
    $BB cat "/proc/$pm_pid/maps" 2>/dev/null || true
    echo "pm_service_maps_sample_cat_rc index=$idx rc=$?"
  else
    echo "pm_service_maps_sample_unavailable index=$idx"
  fi
  echo "pm_service_maps_sample_end index=$idx"
}

'''
    if function_anchor not in script:
        raise RuntimeError("V1106 collector sample function insertion point changed")
    script = script.replace(function_anchor, maps_function, 1)
    loop_anchor = '  sample_pm_service_threads "$sample_index"\n'
    loop_replacement = '  sample_pm_service_threads "$sample_index"\n  sample_pm_service_maps "$sample_index"\n'
    if loop_anchor not in script:
        raise RuntimeError("V1106 collector sample loop insertion point changed")
    return script.replace(loop_anchor, loop_replacement, 1)


def parse_sample_maps(text: str) -> dict[str, Any]:
    samples: list[dict[str, Any]] = []
    current_index = ""
    current_lines: list[str] = []
    in_sample = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("pm_service_maps_sample_begin "):
            in_sample = True
            current_index = stripped.split("index=", 1)[-1]
            current_lines = []
            continue
        if stripped.startswith("pm_service_maps_sample_end "):
            entries = []
            for raw in current_lines:
                match = v1168.MAP_RE.match(raw)
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
            samples.append({
                "index": current_index,
                "entry_count": len(entries),
                "entries": entries,
            })
            in_sample = False
            current_index = ""
            current_lines = []
            continue
        if in_sample and not stripped.startswith("pm_service_maps_sample_"):
            current_lines.append(line.rstrip())
    all_entries = [
        entry
        for sample in samples
        for entry in sample["entries"]
    ]
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


def parse_tracefs_output_v1169(text: str) -> dict[str, Any]:
    parsed = _base_parse_tracefs_output_v1168(text)
    dispatch = parsed.get("pm_callback_dispatch") or {}
    sample_maps = parse_sample_maps(text)
    callback_values = [
        int(str(value), 16)
        for value in dispatch.get("callback_values", [])
        if str(value).startswith("0x")
    ]
    mapped_callbacks = [
        v1168.map_pointer(value, sample_maps["entries"])
        for value in callback_values
    ]
    unique_mapped = []
    seen: set[tuple[str, str]] = set()
    for item in mapped_callbacks:
        key = (str(item.get("pointer", "")), str(item.get("path", "")))
        if key in seen:
            continue
        seen.add(key)
        unique_mapped.append(item)
    dispatch["sample_maps"] = {
        key: value
        for key, value in sample_maps.items()
        if key != "entries"
    }
    dispatch["maps_count"] = sample_maps["entry_count"]
    dispatch["maps_sample_count"] = sample_maps["sample_count"]
    dispatch["maps_samples_with_entries"] = sample_maps["samples_with_entries"]
    dispatch["mapped_callbacks"] = mapped_callbacks
    dispatch["unique_mapped_callbacks"] = unique_mapped
    dispatch["callback_mapping_resolved"] = any(item.get("path") for item in mapped_callbacks)
    parsed["pm_callback_dispatch"] = dispatch
    return parsed


def patch_defaults() -> None:
    v1168.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    v1168.LATEST_POINTER = LATEST_POINTER
    v1168.DEFAULT_WORK_DIR = DEFAULT_WORK_DIR
    v1168.DEFAULT_CHILD_SCRIPT = DEFAULT_CHILD_SCRIPT
    v1168.DEFAULT_COLLECTOR_SCRIPT = DEFAULT_COLLECTOR_SCRIPT
    v1168.DEFAULT_CHILD_OUTPUT = DEFAULT_CHILD_OUTPUT
    v1168.PROOF_PREFIX = PROOF_PREFIX
    v1168.tracefs_collector_script_v1168 = tracefs_collector_script_v1169
    v1168.parse_tracefs_output_v1168 = parse_tracefs_output_v1169
    v1168.patch_defaults()


def tracefs(manifest: dict[str, Any]) -> dict[str, Any]:
    return v1168.tracefs(manifest)


def callback_dispatch(manifest: dict[str, Any]) -> dict[str, Any]:
    return v1168.callback_dispatch(manifest)


def decide_v1169(args: Any, manifest: dict[str, Any]) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return (
            "v1169-pm-callback-maps-plan-ready",
            True,
            "plan-only; no device mutation, PM actor, mdm_helper, CNSS daemon, reboot, or Wi-Fi action executed",
            "run bounded callback-maps live with helper v217 and explicit allow flags",
        )

    base_decision, base_pass, base_reason, base_next = v1168.decide_v1168(args, manifest)
    dispatch = callback_dispatch(manifest)
    if not base_pass:
        return (
            base_decision.replace("v1168", "v1169", 1),
            False,
            base_reason,
            base_next,
        )
    if not dispatch.get("callback_branch_seen"):
        return (
            "v1169-callback-branch-missing",
            False,
            f"dispatch={dispatch}",
            "restore V1168 callback branch before maps mapping",
        )
    if not dispatch.get("maps_samples_with_entries"):
        return (
            "v1169-sample-loop-maps-empty",
            False,
            f"dispatch={dispatch}",
            "capture pm-service maps earlier or preserve pid from trace events",
        )
    if dispatch.get("callback_mapping_resolved"):
        return (
            "v1169-callback-target-mapped-no-esoc0",
            True,
            f"mapped={dispatch.get('unique_mapped_callbacks')}",
            "trace inside the mapped callback target before any Wi-Fi HAL or scan/connect gate",
        )
    return (
        "v1169-callback-target-unmapped",
        True,
        f"dispatch={dispatch}",
        "inspect sample maps and callback pointer address class before choosing the next uprobe",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    base = v1168.render_summary(manifest).replace(
        "# V1168 PM-Service Callback Dispatch Live",
        "# V1169 PM-Service Callback Maps Live",
        1,
    )
    dispatch = callback_dispatch(manifest)
    rows = [
        ["maps_sample_count", dispatch.get("maps_sample_count", "")],
        ["maps_samples_with_entries", dispatch.get("maps_samples_with_entries", "")],
        ["maps_count", dispatch.get("maps_count", "")],
        ["callback_values", json.dumps(dispatch.get("callback_values", []))],
        ["unique_mapped_callbacks", json.dumps(dispatch.get("unique_mapped_callbacks", []), sort_keys=True)],
        ["callback_mapping_resolved", dispatch.get("callback_mapping_resolved", "")],
    ]
    return base + "\n".join([
        "",
        "## V1169 PM-Service Maps Mapping",
        "",
        markdown_table(["key", "value"], rows),
        "",
    ])


def main() -> int:
    patch_defaults()
    args = v1168.v1167.v1165.v1143.v1139.v1113.v1106.parse_args()
    v1168.v1167.v1165.v1143.v1139.v1113.set_global_defaults(args)
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = v1168.v1167.v1165.v1143.v1139.v1113.v1106.build_manifest(args, store)
    manifest["base_v1168_decision"] = manifest.get("decision", "")
    manifest["cycle"] = "v1169"
    manifest["generated_at"] = now_iso()
    manifest["v1168_manifest"] = str(DEFAULT_V1168_MANIFEST)
    decision, passed, reason, next_step = decide_v1169(args, manifest)
    manifest.update({"decision": decision, "pass": passed, "reason": reason, "next_step": next_step})

    fw = v1168.v1167.v1165.v1143.v1139.global_firmware(manifest)
    values = v1168.v1167.v1165.v1143.v1139.contract(manifest)
    post = v1168.v1167.v1165.v1143.v1139.post_pm(manifest)
    lower = v1168.v1167.v1165.v1143.lower_trace(manifest)
    late = v1168.v1167.v1165.late_per_proxy(manifest)
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

#!/usr/bin/env python3
"""V663 host-only classifier for V662 registry snapshot zero-count results.

This classifier consumes existing V662/V661/V658/V525 evidence only. It does
not contact the device, write sysfs, start daemons, start service-manager,
start Wi-Fi HAL, scan, connect, use credentials, run DHCP, change routes, or
ping externally.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v663-v662-snapshot-zero-classifier")
DEFAULT_V662_MANIFEST = Path("tmp/wifi/v662-registry-context-snapshot-live-rerun/manifest.json")
DEFAULT_V662_HELPER = Path("tmp/wifi/v662-registry-context-snapshot-live-rerun/native/companion-start-only-with-holder.txt")
DEFAULT_V661_MANIFEST = Path("tmp/wifi/v661-binder-registration-context-classifier/manifest.json")
DEFAULT_V658_MANIFEST = Path("tmp/wifi/v658-vndbinder-surface-classifier/manifest.json")
DEFAULT_V525_MANIFEST = Path(
    "tmp/wifi/v526-android-companion-identity-handoff-run/"
    "v525-android-companion-identity-run/manifest.json"
)

KEY_RE = re.compile(r"^([A-Za-z0-9_.-]+)=(.*)$")
PATH_BEGIN_RE = re.compile(r"^A90_EXECNS_PATH_(?P<label>[^ ]+)_BEGIN path=(?P<path>[^ ]+) limit=(?P<limit>[0-9]+)")
PATH_END_RE = re.compile(r"^A90_EXECNS_PATH_(?P<label>[^ ]+)_END bytes=(?P<bytes>[0-9]+) truncated=(?P<truncated>[0-9]+)")
DIR_BEGIN_RE = re.compile(
    r"^A90_EXECNS_DIR_(?P<label>[^ ]+)_BEGIN path=(?P<path>[^ ]+) filter=(?P<filter>[0-9]+) "
    r"max_entries=(?P<max_entries>[0-9]+)"
)
DIR_END_RE = re.compile(
    r"^A90_EXECNS_DIR_(?P<label>[^ ]+)_END count=(?P<count>[0-9]+) shown=(?P<shown>[0-9]+) "
    r"truncated=(?P<truncated>[0-9]+)"
)

FORBIDDEN_ACTIONS = (
    "device command",
    "sysfs write",
    "DSP boot-node write",
    "partition/boot-image write",
    "daemon start",
    "service-manager start",
    "Wi-Fi HAL start",
    "scan/connect/link-up",
    "credential/DHCP/routing/external ping",
)

REGISTRY_PHASES = ("before_initial_cnss_cleanup", "after_initial_cnss_cleanup")
RUNTIME_DIR_LABELS = (
    "binder_debug_dir",
    "binder_proc_dir",
    "dev_properties_dir",
    "dev_socket_dir",
)
DEVNODES = ("binder", "hwbinder", "vndbinder")
CHILDREN = (
    "qrtr_ns",
    "rmt_storage",
    "tftp_server",
    "pd_mapper",
    "cnss_diag",
    "cnss_daemon",
    "servicemanager",
    "hwservicemanager",
    "vndservicemanager",
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v662-manifest", type=Path, default=DEFAULT_V662_MANIFEST)
    parser.add_argument("--v662-helper", type=Path, default=DEFAULT_V662_HELPER)
    parser.add_argument("--v661-manifest", type=Path, default=DEFAULT_V661_MANIFEST)
    parser.add_argument("--v658-manifest", type=Path, default=DEFAULT_V658_MANIFEST)
    parser.add_argument("--v525-manifest", type=Path, default=DEFAULT_V525_MANIFEST)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def read_text(path: Path) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    return resolved.read_bytes().replace(b"\0", b"\n").decode("utf-8", errors="replace")


def load_json(path: Path) -> dict[str, Any]:
    text = read_text(path)
    return json.loads(text) if text else {}


def nested(mapping: dict[str, Any], path: tuple[str, ...], default: Any = None) -> Any:
    current: Any = mapping
    for key in path:
        if not isinstance(current, dict):
            return default
        current = current.get(key, default)
    return current


def boolish(value: Any) -> bool:
    return value in (True, 1, "1", "true", "True", "yes", "pass", "ok")


def intish(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def parse_key_values(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in text.splitlines():
        match = KEY_RE.match(raw_line.strip())
        if match:
            values[match.group(1)] = match.group(2).strip()
    return values


def parse_path_blocks(text: str) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    active: dict[str, Any] | None = None
    for raw_line in text.splitlines():
        line = raw_line.strip()
        begin = PATH_BEGIN_RE.match(line)
        if begin:
            active = {
                "label": begin.group("label"),
                "path": begin.group("path"),
                "limit": intish(begin.group("limit")),
                "open_error": "",
                "bytes": 0,
                "truncated": 0,
            }
            continue
        if active is not None and line.startswith("open-error="):
            active["open_error"] = line.split("=", 1)[1]
            continue
        end = PATH_END_RE.match(line)
        if end and active is not None and end.group("label") == active["label"]:
            active["bytes"] = intish(end.group("bytes"))
            active["truncated"] = intish(end.group("truncated"))
            blocks.append(active)
            active = None
    return blocks


def parse_dir_blocks(text: str) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    active_by_label: dict[str, dict[str, Any]] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        begin = DIR_BEGIN_RE.match(line)
        if begin:
            active_by_label[begin.group("label")] = {
                "label": begin.group("label"),
                "path": begin.group("path"),
                "filter": intish(begin.group("filter")),
                "max_entries": intish(begin.group("max_entries")),
                "open_error": "",
                "count": 0,
                "shown": 0,
                "truncated": 0,
            }
            continue
        if line.startswith("open-error="):
            for block in reversed(active_by_label.values()):
                if not block["open_error"]:
                    block["open_error"] = line.split("=", 1)[1]
                    break
            continue
        end = DIR_END_RE.match(line)
        if end and end.group("label") in active_by_label:
            block = active_by_label.pop(end.group("label"))
            block["count"] = intish(end.group("count"))
            block["shown"] = intish(end.group("shown"))
            block["truncated"] = intish(end.group("truncated"))
            blocks.append(block)
    return blocks


def registry_summary(keys: dict[str, str]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for phase in REGISTRY_PHASES:
        prefix = f"wifi_registry_snapshot.{phase}"
        child_rows: list[list[str]] = []
        for child in CHILDREN:
            child_rows.append([
                child,
                keys.get(f"{prefix}.child.{child}.pid", ""),
                keys.get(f"{prefix}.child.{child}.observable", ""),
            ])
        summary[phase] = {
            "begin": keys.get(f"{prefix}.begin", ""),
            "end": keys.get(f"{prefix}.end", ""),
            "child_count": keys.get(f"{prefix}.child_count", ""),
            "files_captured": keys.get(f"{prefix}.files_captured", ""),
            "dirs_captured": keys.get(f"{prefix}.dirs_captured", ""),
            "child_proc_captured": keys.get(f"{prefix}.child_proc_captured", ""),
            "child_rows": child_rows,
        }
    return summary


def surface_from_v662(v662_manifest: dict[str, Any], keys: dict[str, str]) -> dict[str, Any]:
    live = v662_manifest.get("live") or {}
    surface = live.get("v662_surface") or {}
    counts = live.get("v662_counts") or {}
    service74_gate = surface.get("service74_gate") or {}
    vnd_ready = surface.get("vndservicemanager_readiness") or {}
    registry = surface.get("registry_snapshot") or {}
    initial_cnss = surface.get("initial_cnss_daemon") or {}
    return {
        "decision": v662_manifest.get("decision"),
        "pass": v662_manifest.get("pass"),
        "helper_result": live.get("helper_result"),
        "all_observable": live.get("all_observable"),
        "all_postflight_safe": live.get("all_postflight_safe"),
        "order": surface.get("order") or keys.get("wifi_companion_start.order", ""),
        "service74_open": boolish(service74_gate.get("open")) or service74_gate.get("status") == "open",
        "service74_seen": boolish(service74_gate.get("seen")),
        "service74_wait_ms": service74_gate.get("wait_ms"),
        "service_manager_started": boolish(surface.get("service_manager_started")),
        "with_service_manager": boolish(surface.get("with_service_manager")),
        "with_vnd_service_manager": boolish(surface.get("with_vnd_service_manager")),
        "vndservicemanager_ready": boolish(vnd_ready.get("ready")),
        "vndservicemanager_observable": boolish(vnd_ready.get("observable")),
        "vndservicemanager_fd_summary": boolish(vnd_ready.get("fd_summary_captured")),
        "cnss_retry_enabled": boolish((surface.get("cnss_retry") or {}).get("enabled")),
        "initial_cnss_cleanup_safe": boolish(initial_cnss.get("cleanup_safe")),
        "registry": registry,
        "counts": {
            "service_notifier_180": intish(counts.get("service_notifier_180")),
            "service_notifier_74": intish(counts.get("service_notifier_74")),
            "cnss_daemon_netlink": intish(counts.get("cnss_daemon_netlink")),
            "cnss_binder_transaction_failed": intish(counts.get("cnss_binder_transaction_failed")),
            "binder_transaction_failed": intish(counts.get("binder_transaction_failed")),
            "binder_ioctl_unsupported": intish(counts.get("binder_ioctl_unsupported")),
            "wlfw_start": intish(counts.get("wlfw_start")),
            "wlan_pd": intish(counts.get("wlan_pd")),
            "qmi_server_connected": intish(counts.get("qmi_server_connected")),
            "bdf_regdb": intish(counts.get("bdf_regdb")),
            "bdf_bdwlan": intish(counts.get("bdf_bdwlan")),
            "wlan_fw_ready": intish(counts.get("wlan_fw_ready")),
            "wlan0": intish(counts.get("wlan0")),
            "kernel_warning": intish(counts.get("kernel_warning")),
        },
    }


def runtime_rows(dir_blocks: list[dict[str, Any]]) -> list[list[str]]:
    rows: list[list[str]] = []
    for phase in REGISTRY_PHASES:
        for runtime_label in RUNTIME_DIR_LABELS:
            full_label = f"wifi_registry_{phase}_{runtime_label}"
            block = next((candidate for candidate in dir_blocks if candidate["label"] == full_label), None)
            rows.append([
                phase,
                runtime_label,
                block.get("path", "") if block else "",
                str(block.get("count", "")) if block else "missing",
                block.get("open_error", "") if block else "missing",
            ])
    return rows


def devnode_rows(keys: dict[str, str]) -> list[list[str]]:
    rows: list[list[str]] = []
    for node in DEVNODES:
        rows.append([
            f"/dev/{node}",
            keys.get(f"context.dev_{node}.exists", ""),
            keys.get(f"context.dev_{node}.access_r", ""),
            keys.get(f"context.dev_{node}.mode", ""),
            keys.get(f"context.dev_{node}.rdev", ""),
        ])
    rows.append([
        "/dev/__properties__",
        keys.get("context.dev_properties.exists", ""),
        keys.get("context.dev_properties.access_r", ""),
        keys.get("context.dev_properties.mode", ""),
        keys.get("context.dev_properties.errno", ""),
    ])
    return rows


def path_summary(path_blocks: list[dict[str, Any]]) -> dict[str, Any]:
    binder_debug = [block for block in path_blocks if block["path"].startswith("/sys/kernel/debug/binder/")]
    binder_proc = [block for block in binder_debug if "/proc/" in block["path"]]
    top_level = [block for block in binder_debug if "/proc/" not in block["path"]]
    return {
        "path_blocks": len(path_blocks),
        "binder_debug_path_blocks": len(binder_debug),
        "binder_debug_top_level_blocks": len(top_level),
        "binder_proc_blocks": len(binder_proc),
        "binder_debug_open_errors": sum(1 for block in binder_debug if block["open_error"]),
        "binder_debug_bytes": sum(intish(block["bytes"]) for block in binder_debug),
        "binder_proc_open_errors": sum(1 for block in binder_proc if block["open_error"]),
        "binder_proc_bytes": sum(intish(block["bytes"]) for block in binder_proc),
    }


def build_checks(manifest: dict[str, Any]) -> dict[str, bool]:
    v662 = manifest["v662_surface"]
    registry = manifest["registry_summary"]
    path_stats = manifest["path_summary"]
    prior = manifest["prior_context"]
    runtime = manifest["runtime_surface"]
    devnodes_present = all(row[1] == "1" and row[2] == "1" for row in manifest["devnode_rows"][:3])
    snapshot_complete = all(
        boolish(registry[phase]["begin"]) and boolish(registry[phase]["end"])
        for phase in REGISTRY_PHASES
    )
    snapshot_zero = all(
        intish(registry[phase]["files_captured"]) == 0
        and intish(registry[phase]["dirs_captured"]) == 0
        and intish(registry[phase]["child_proc_captured"]) == 0
        for phase in REGISTRY_PHASES
    )
    return {
        "v662_live_passed": v662["decision"] == "v662-registry-context-snapshot-pass" and boolish(v662["pass"]),
        "service74_gate_open": v662["service74_seen"] and v662["service74_open"],
        "vndservicemanager_ready": v662["vndservicemanager_ready"] and v662["vndservicemanager_fd_summary"],
        "registry_snapshot_complete": snapshot_complete,
        "registry_snapshot_zero_counts": snapshot_zero,
        "binder_devnodes_present": devnodes_present,
        "binder_debugfs_absent_in_namespace": (
            path_stats["binder_debug_path_blocks"] > 0
            and path_stats["binder_debug_open_errors"] == path_stats["binder_debug_path_blocks"]
            and runtime["binder_debug_zero"]
        ),
        "property_runtime_absent_in_namespace": runtime["dev_properties_zero"],
        "socket_runtime_absent_in_namespace": runtime["dev_socket_zero"],
        "v661_already_ruled_out_devnodes": prior["v661_binder_devnodes_present"],
        "v661_property_gap_confirmed": prior["v661_property_namespace_not_mounted"],
        "android_reference_has_companion_identity": prior["v525_android_identities"],
        "wlfw_still_blocked": (
            v662["counts"]["wlfw_start"] == 0
            and v662["counts"]["wlan_pd"] == 0
            and v662["counts"]["qmi_server_connected"] == 0
            and v662["counts"]["wlan0"] == 0
        ),
    }


def runtime_surface(dir_rows: list[list[str]]) -> dict[str, bool]:
    def rows_for(label: str) -> list[list[str]]:
        return [row for row in dir_rows if row[1] == label]

    def all_zero(label: str) -> bool:
        selected = rows_for(label)
        return bool(selected) and all(row[3] == "0" and row[4] for row in selected)

    return {
        "binder_debug_zero": all_zero("binder_debug_dir") and all_zero("binder_proc_dir"),
        "dev_properties_zero": all_zero("dev_properties_dir"),
        "dev_socket_zero": all_zero("dev_socket_dir"),
    }


def prior_context(v661_manifest: dict[str, Any], v658_manifest: dict[str, Any], v525_manifest: dict[str, Any]) -> dict[str, Any]:
    v661_checks = v661_manifest.get("checks") or {}
    v525_android = v525_manifest.get("android_summary") or {}
    v525_required = v525_android.get("all_required_process_identities")
    if v525_required is None:
        v525_required = v525_manifest.get("all_required_process_identities")
    return {
        "v661_decision": v661_manifest.get("decision"),
        "v661_pass": boolish(v661_manifest.get("pass")),
        "v661_binder_devnodes_present": boolish(v661_checks.get("binder_devnodes_present")),
        "v661_context_files_present": boolish(v661_checks.get("selinux_context_files_present")),
        "v661_property_namespace_not_mounted": boolish(v661_checks.get("property_namespace_not_mounted")),
        "v661_property_service_shim_disabled": boolish(v661_checks.get("property_service_shim_disabled")),
        "v661_cnss_retry_reaches_vndbinder": boolish(v661_checks.get("cnss_retry_reaches_vndbinder")),
        "v661_vndservicemanager_reaches_vndbinder": boolish(v661_checks.get("vndservicemanager_reaches_vndbinder")),
        "v658_decision": v658_manifest.get("decision"),
        "v658_pass": boolish(v658_manifest.get("pass")),
        "v525_decision": v525_manifest.get("decision"),
        "v525_pass": boolish(v525_manifest.get("pass")),
        "v525_android_identities": boolish(v525_required),
    }


def evidence_rows(manifest: dict[str, Any]) -> list[list[str]]:
    checks = manifest["checks"]
    path_stats = manifest["path_summary"]
    runtime = manifest["runtime_surface"]
    v662 = manifest["v662_surface"]
    return [
        [
            "V662 execution",
            "valid snapshot, not helper failure",
            f"pass={checks['v662_live_passed']} complete={checks['registry_snapshot_complete']} zero={checks['registry_snapshot_zero_counts']}",
            "consume V662 as evidence; do not rerun unchanged snapshot",
        ],
        [
            "Binder devnodes",
            "present but insufficient",
            f"devnodes={checks['binder_devnodes_present']} v661_devnodes={checks['v661_already_ruled_out_devnodes']}",
            "do not remount binder devnodes as the next repair",
        ],
        [
            "Binder debugfs",
            "observability gap",
            (
                f"blocks={path_stats['binder_debug_path_blocks']} "
                f"open_errors={path_stats['binder_debug_open_errors']} bytes={path_stats['binder_debug_bytes']}"
            ),
            "useful for diagnostics, but not enough alone to explain WLFW block",
        ],
        [
            "Property runtime",
            "strong repair candidate",
            f"v662_zero={runtime['dev_properties_zero']} v661_gap={checks['v661_property_gap_confirmed']}",
            "next live proof should materialize private property runtime before CNSS retry",
        ],
        [
            "Socket runtime",
            "candidate repair surface",
            f"v662_zero={runtime['dev_socket_zero']}",
            "materialize required private /dev/socket entries only if property-first proof is insufficient",
        ],
        [
            "WLFW path",
            "still blocked before Wi-Fi HAL",
            (
                f"wlfw={v662['counts']['wlfw_start']} wlan_pd={v662['counts']['wlan_pd']} "
                f"qmi={v662['counts']['qmi_server_connected']} wlan0={v662['counts']['wlan0']}"
            ),
            "keep Wi-Fi HAL, scan/connect, credentials, DHCP, routes, and external ping blocked",
        ],
    ]


def classify(manifest: dict[str, Any]) -> tuple[str, bool, str, str]:
    checks = manifest["checks"]
    required = (
        "v662_live_passed",
        "service74_gate_open",
        "vndservicemanager_ready",
        "registry_snapshot_complete",
        "registry_snapshot_zero_counts",
        "binder_devnodes_present",
        "binder_debugfs_absent_in_namespace",
        "property_runtime_absent_in_namespace",
        "socket_runtime_absent_in_namespace",
        "v661_property_gap_confirmed",
        "android_reference_has_companion_identity",
        "wlfw_still_blocked",
    )
    if all(checks[name] for name in required):
        return (
            "v663-private-runtime-surface-gap-classified",
            True,
            (
                "V662 snapshot zero counts are explained by absent private binder-debugfs, "
                "property, and socket runtime surfaces rather than a failed snapshot; "
                "binder devnodes already exist, so property/runtime materialization is "
                "the next narrower repair candidate before another CNSS retry."
            ),
            (
                "plan V664 bounded private property/runtime materialization proof before "
                "fresh CNSS retry; keep Wi-Fi HAL, scan/connect, credentials, DHCP, routes, "
                "and external ping blocked"
            ),
        )

    if not checks["v662_live_passed"] or not checks["registry_snapshot_complete"]:
        return (
            "v663-v662-snapshot-evidence-incomplete",
            False,
            "V662 did not provide a complete usable registry snapshot",
            "inspect V662 helper transcript before changing runtime surfaces",
        )

    return (
        "v663-runtime-surface-classification-incomplete",
        False,
        "Existing evidence does not yet distinguish property/socket/runtime absence from another blocker",
        "add a host-only parser or a read-only snapshot before any live mutation",
    )


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    v662_manifest = load_json(args.v662_manifest)
    v661_manifest = load_json(args.v661_manifest)
    v658_manifest = load_json(args.v658_manifest)
    v525_manifest = load_json(args.v525_manifest)
    helper_text = read_text(args.v662_helper)
    helper_keys = parse_key_values(helper_text)
    path_blocks = parse_path_blocks(helper_text)
    dir_blocks = parse_dir_blocks(helper_text)
    dir_rows = runtime_rows(dir_blocks)
    manifest: dict[str, Any] = {
        "generated_at": now_iso(),
        "command": args.command,
        "host": collect_host_metadata(),
        "inputs": {
            "v662_manifest": str(repo_path(args.v662_manifest)),
            "v662_helper": str(repo_path(args.v662_helper)),
            "v661_manifest": str(repo_path(args.v661_manifest)),
            "v658_manifest": str(repo_path(args.v658_manifest)),
            "v525_manifest": str(repo_path(args.v525_manifest)),
        },
        "v662_surface": surface_from_v662(v662_manifest, helper_keys),
        "registry_summary": registry_summary(helper_keys),
        "path_summary": path_summary(path_blocks),
        "runtime_rows": dir_rows,
        "runtime_surface": runtime_surface(dir_rows),
        "devnode_rows": devnode_rows(helper_keys),
        "prior_context": prior_context(v661_manifest, v658_manifest, v525_manifest),
        "forbidden_actions": FORBIDDEN_ACTIONS,
        "device_commands_executed": False,
        "device_mutations": False,
        "sysfs_writes_executed": False,
        "daemon_start_executed": False,
        "service_manager_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "wifi_bringup_executed": False,
        "external_ping_executed": False,
    }
    manifest["checks"] = build_checks(manifest)
    manifest["evidence_rows"] = evidence_rows(manifest)
    if args.command == "plan":
        decision, pass_ok, reason, next_step = (
            "v663-v662-snapshot-zero-classifier-plan-ready",
            True,
            "plan-only; no device contact, no daemon start, no Wi-Fi bring-up",
            "run V663 host-only classifier",
        )
    else:
        decision, pass_ok, reason, next_step = classify(manifest)
    manifest.update({
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
    })
    return manifest


def registry_rows(manifest: dict[str, Any]) -> list[list[str]]:
    rows: list[list[str]] = []
    for phase in REGISTRY_PHASES:
        item = manifest["registry_summary"][phase]
        rows.append([
            phase,
            item["begin"],
            item["end"],
            item["child_count"],
            item["files_captured"],
            item["dirs_captured"],
            item["child_proc_captured"],
        ])
    return rows


def prior_rows(manifest: dict[str, Any]) -> list[list[str]]:
    return [[key, str(value)] for key, value in manifest["prior_context"].items()]


def marker_rows(manifest: dict[str, Any]) -> list[list[str]]:
    return [[key, str(value)] for key, value in manifest["v662_surface"]["counts"].items()]


def render_summary(manifest: dict[str, Any]) -> str:
    return "\n".join([
        "# V663 V662 Snapshot Zero-count Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- daemon_start_executed: `{manifest['daemon_start_executed']}`",
        f"- service_manager_start_executed: `{manifest['service_manager_start_executed']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        "",
        "## Checks",
        "",
        markdown_table(["check", "value"], [[key, str(value)] for key, value in manifest["checks"].items()]),
        "",
        "## Evidence Matrix",
        "",
        markdown_table(["subject", "classification", "evidence", "next"], manifest["evidence_rows"]),
        "",
        "## Registry Snapshot",
        "",
        markdown_table(
            ["phase", "begin", "end", "child_count", "files", "dirs", "child_proc"],
            registry_rows(manifest),
        ),
        "",
        "## Runtime Directories",
        "",
        markdown_table(["phase", "surface", "path", "count", "open_error"], manifest["runtime_rows"]),
        "",
        "## Device Nodes",
        "",
        markdown_table(["node", "exists", "access_r", "mode", "rdev_or_errno"], manifest["devnode_rows"]),
        "",
        "## V662 Marker Counts",
        "",
        markdown_table(["marker", "count"], marker_rows(manifest)),
        "",
        "## Prior Context",
        "",
        markdown_table(["key", "value"], prior_rows(manifest)),
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
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"daemon_start_executed: {manifest['daemon_start_executed']}")
    print(f"service_manager_start_executed: {manifest['service_manager_start_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

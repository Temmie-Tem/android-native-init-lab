#!/usr/bin/env python3
"""V678 host-only Binder failure target classifier.

This classifier consumes V677 evidence after the private property runtime
repair. It does not contact the device, start services, scan/connect, use
credentials, run DHCP, change routes, write sysfs, or ping externally.
"""

from __future__ import annotations

import argparse
import collections
import datetime as dt
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v678-binder-failure-target-classifier")
DEFAULT_V677_MANIFEST = Path("tmp/wifi/v677-v676-residual-property-replay-live/manifest.json")

ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
KEY_RE = re.compile(r"^([A-Za-z0-9_.-]+)=(.*)$")
BINDER_RE = re.compile(
    r"\[[^\]]*:\s*(?P<comm>[^:\]]+):\s*(?P<pid>\d+)\]\s+"
    r"binder:\s+(?P<pair>\d+:\d+)\s+(?P<detail>.*?(?P<errno>-\d+))",
    re.I,
)
IOCTL_RE = re.compile(r"ioctl\s+(?P<code>[0-9a-fA-Fx]+)\s+.*?returned\s+(?P<errno>-\d+)", re.I)
TX_RE = re.compile(r"transaction failed\s+(?P<code>\d+)/(?P<errno>-\d+)", re.I)
TS_RE = re.compile(r"^\[\s*(?P<ts>[0-9]+(?:\.[0-9]+)?)\]")

FORBIDDEN_ACTIONS = (
    "device command",
    "sysfs write",
    "DSP boot-node write",
    "esoc0 open",
    "daemon start",
    "service-manager start",
    "Wi-Fi HAL start",
    "supplicant or hostapd start",
    "scan/connect/link-up",
    "credential/DHCP/routing/external ping",
    "boot image or partition write",
)

SERVICE_MANAGER_CHILDREN = ("servicemanager", "hwservicemanager", "vndservicemanager")
POST_HAL_CHILDREN = ("wifi_hal_legacy", "wifi_hal_ext", "wificond")
CNSS_CHILDREN = ("cnss_daemon", "cnss_daemon_retry")
SURFACE_CHILDREN = SERVICE_MANAGER_CHILDREN + POST_HAL_CHILDREN + CNSS_CHILDREN
LOWER_ZERO_MARKERS = (
    "wlfw_start",
    "wlfw_service_request",
    "wlan_pd",
    "qmi_server_connected",
    "bdf_regdb",
    "bdf_bdwlan",
    "wlan_fw_ready",
    "wlan0",
)


@dataclass(frozen=True)
class BinderFailure:
    actor: str
    pid: int
    tid_pair: str
    kind: str
    code: str
    errno: str
    timestamp: float | None
    line: str


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v677-manifest", type=Path, default=DEFAULT_V677_MANIFEST)
    parser.add_argument("--arm-manifest", type=Path, default=None)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def clean_line(raw_line: str) -> str:
    return ANSI_RE.sub("", raw_line).strip()


def read_text(path: Path) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    return resolved.read_bytes().replace(b"\0", b"\n").decode("utf-8", errors="replace")


def load_json(path: Path) -> dict[str, Any]:
    text = read_text(path)
    return json.loads(text) if text else {}


def boolish(value: Any) -> bool:
    return value in (True, 1, "1", "true", "True", "yes", "pass", "ok")


def intish(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def line_time(line: str) -> float | None:
    match = TS_RE.match(clean_line(line))
    if not match:
        return None
    try:
        return float(match.group("ts"))
    except ValueError:
        return None


def nested(mapping: dict[str, Any], path: tuple[str, ...], default: Any = None) -> Any:
    current: Any = mapping
    for key in path:
        if not isinstance(current, dict):
            return default
        current = current.get(key, default)
    return current


def resolve_arm_manifest(args: argparse.Namespace, v677: dict[str, Any]) -> Path:
    if args.arm_manifest is not None:
        return repo_path(args.arm_manifest)
    manifest = nested(v677, ("arm_v676", "manifest"))
    if manifest:
        return repo_path(Path(str(manifest)))
    return repo_path(args.v677_manifest).parent / "arm-v676-v535" / "live" / "manifest.json"


def evidence_root(arm_path: Path, arm: dict[str, Any]) -> Path:
    out_dir = arm.get("out_dir")
    if out_dir:
        return repo_path(Path(str(out_dir)))
    return repo_path(arm_path).parent


def load_dmesg(arm_path: Path, arm: dict[str, Any]) -> str:
    file_text = read_text(evidence_root(arm_path, arm) / "native" / "dmesg-delta.txt")
    if file_text:
        return file_text
    return str(nested(arm, ("live", "dmesg_delta"), ""))


def load_helper(arm_path: Path, arm: dict[str, Any]) -> str:
    file_text = read_text(evidence_root(arm_path, arm) / "native" / "companion-start-only-with-holder.txt")
    if file_text:
        return file_text
    return str(nested(arm, ("live", "helper_stdout_stderr"), ""))


def parse_keys(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in text.splitlines():
        match = KEY_RE.match(clean_line(raw_line))
        if match:
            values[match.group(1)] = match.group(2).strip()
    return values


def normalize_actor(comm: str) -> str:
    actor = comm.strip()
    if actor.startswith("hwservicemanage"):
        return "hwservicemanager"
    return actor


def parse_binder_failures(text: str) -> list[BinderFailure]:
    failures: list[BinderFailure] = []
    for raw_line in text.splitlines():
        line = clean_line(raw_line)
        match = BINDER_RE.search(line)
        if not match:
            continue
        detail = match.group("detail")
        ioctl = IOCTL_RE.search(detail)
        tx = TX_RE.search(detail)
        if ioctl:
            kind = "ioctl"
            code = ioctl.group("code")
            errno = ioctl.group("errno")
        elif tx:
            kind = "transaction"
            code = tx.group("code")
            errno = tx.group("errno")
        else:
            kind = "unknown"
            code = ""
            errno = match.group("errno")
        failures.append(BinderFailure(
            actor=normalize_actor(match.group("comm")),
            pid=int(match.group("pid")),
            tid_pair=match.group("pair"),
            kind=kind,
            code=code,
            errno=errno,
            timestamp=line_time(line),
            line=line,
        ))
    return failures


def binder_summary(failures: list[BinderFailure]) -> dict[str, Any]:
    by_actor = collections.Counter(failure.actor for failure in failures)
    by_kind = collections.Counter(failure.kind for failure in failures)
    by_code = collections.Counter(f"{failure.kind}:{failure.code}:{failure.errno}" for failure in failures)
    return {
        "total": len(failures),
        "by_actor": dict(sorted(by_actor.items())),
        "by_kind": dict(sorted(by_kind.items())),
        "by_code": dict(sorted(by_code.items())),
        "failures": [asdict(failure) for failure in failures],
    }


def marker_counts(live: dict[str, Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for source in (
        live.get("v655_counts") or {},
        (live.get("markers") or {}).get("counts") or {},
        live.get("v644_counts") or {},
    ):
        if not isinstance(source, dict):
            continue
        for key, value in source.items():
            parsed = intish(value)
            if parsed is not None:
                counts.setdefault(key, parsed)
    return counts


def fd_targets(keys: dict[str, str], child: str) -> list[str]:
    prefix = f"capture.wifi_hal_composite_{child}.fd_links.entry_"
    return [
        value
        for key, value in sorted(keys.items())
        if key.startswith(prefix) and key.endswith(".target")
    ]


def has_fd(targets: list[str], name: str) -> bool:
    return any(target.endswith(f"/dev/{name}") or f"/dev/{name}" in target for target in targets)


def child_surface(keys: dict[str, str], child: str) -> dict[str, Any]:
    targets = fd_targets(keys, child)
    return {
        "child": child,
        "start_order": intish(keys.get(f"wifi_companion_start.child.{child}.start_order")),
        "exec_attempted": boolish(keys.get(f"wifi_hal_composite_start.child.{child}.exec_attempted")),
        "child_started": boolish(keys.get(f"wifi_hal_composite_start.child.{child}.child_started")),
        "observable": boolish(keys.get(f"wifi_companion_start.child.{child}.observable")),
        "postflight_safe": boolish(keys.get(f"wifi_companion_start.child.{child}.postflight_safe")),
        "exit_code": intish(keys.get(f"wifi_companion_start.child.{child}.exit_code")),
        "signal": intish(keys.get(f"wifi_companion_start.child.{child}.signal")),
        "pid": intish(keys.get(f"wifi_hal_composite_start.child.{child}.pid")),
        "pgid": intish(keys.get(f"wifi_hal_composite_start.child.{child}.pgid")),
        "target": keys.get(f"wifi_hal_composite_start.child.{child}.target", ""),
        "preexec_status": keys.get(f"wifi_hal_composite_child.{child}.preexec_status", ""),
        "selinux_exec": keys.get(f"wifi_hal_composite_child.{child}.selinux.exec", ""),
        "selinux_exec_ok": boolish(keys.get(f"wifi_hal_composite_child.{child}.selinux_exec.ok")),
        "expected_uid": keys.get(f"wifi_hal_composite_child.{child}.expected.uid", ""),
        "expected_gid": keys.get(f"wifi_hal_composite_child.{child}.expected.gid", ""),
        "expected_cap": keys.get(f"wifi_hal_composite_child.{child}.expected.cap", ""),
        "fd_count": len(targets),
        "binder_fd": has_fd(targets, "binder"),
        "hwbinder_fd": has_fd(targets, "hwbinder"),
        "vndbinder_fd": has_fd(targets, "vndbinder"),
        "socket_fd_count": sum(target.startswith("socket:[") for target in targets),
    }


def binder_device_rows(keys: dict[str, str]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for device in ("binder", "hwbinder", "vndbinder"):
        rows.append({
            "device": f"/dev/{device}",
            "exists": keys.get(f"context.dev_{device}.exists", ""),
            "access_r": keys.get(f"context.dev_{device}.access_r", ""),
            "mode": keys.get(f"context.dev_{device}.mode", ""),
            "rdev": keys.get(f"context.dev_{device}.rdev", ""),
        })
    return rows


def registry_surface(keys: dict[str, str]) -> dict[str, Any]:
    key_names = tuple(keys)
    return {
        "registry_snapshot_enabled": boolish(keys.get("wifi_companion_start.registry_snapshot.enabled")),
        "registry_snapshot_before_initial_cnss_cleanup": boolish(
            keys.get("wifi_companion_start.registry_snapshot.before_initial_cnss_cleanup")
        ),
        "service_list_snapshot_seen": any("servicemanager_list" in key or "service_list" in key for key in key_names),
        "vndservice_list_snapshot_seen": any(
            "vndservicemanager_list" in key or "vndservice_list" in key for key in key_names
        ),
        "binder_debug_snapshot_seen": any(
            token in key.lower()
            for key in key_names
            for token in ("binder_state", "binder_stats", "transaction_log", "failed_transaction_log")
        ),
        "context_manager_probe_seen": any("context_manager" in key.lower() for key in key_names),
    }


def surface_checks(children: dict[str, dict[str, Any]]) -> dict[str, bool]:
    return {
        "service_manager_children_ready": all(
            children[name]["child_started"]
            and children[name]["observable"]
            and children[name]["postflight_safe"]
            for name in SERVICE_MANAGER_CHILDREN
        ),
        "service_manager_binder_fds_ready": (
            children["servicemanager"]["binder_fd"]
            and children["hwservicemanager"]["hwbinder_fd"]
            and children["vndservicemanager"]["vndbinder_fd"]
        ),
        "post_hal_children_ready": all(
            children[name]["child_started"]
            and children[name]["observable"]
            and children[name]["postflight_safe"]
            for name in POST_HAL_CHILDREN
        ),
        "post_hal_binder_fds_ready": (
            children["wifi_hal_legacy"]["hwbinder_fd"]
            and children["wifi_hal_ext"]["hwbinder_fd"]
            and children["wificond"]["binder_fd"]
            and children["wificond"]["hwbinder_fd"]
        ),
        "cnss_retry_reaches_vndbinder": children["cnss_daemon_retry"]["vndbinder_fd"],
        "cnss_retry_observable_safe": (
            children["cnss_daemon_retry"]["child_started"]
            and children["cnss_daemon_retry"]["observable"]
            and children["cnss_daemon_retry"]["postflight_safe"]
        ),
    }


def build_checks(v677: dict[str, Any],
                 arm: dict[str, Any],
                 live: dict[str, Any],
                 counts: dict[str, int],
                 binders: dict[str, Any],
                 children: dict[str, dict[str, Any]],
                 devices: list[dict[str, str]],
                 registry: dict[str, Any]) -> list[dict[str, Any]]:
    property_surface = live.get("v676_property_runtime_surface") or {}
    property_denial_total = intish(property_surface.get("property_denial_total")) or 0
    property_denial_unique = intish(property_surface.get("property_denial_unique")) or 0
    child_checks = surface_checks(children)
    lower_zero = {name: counts.get(name, 0) for name in LOWER_ZERO_MARKERS}
    cnss_tx = binders["by_actor"].get("cnss-daemon", 0)
    return [
        {
            "name": "v677-input-ready",
            "status": "pass" if v677.get("pass") and arm.get("pass") else "blocked",
            "detail": {"v677_decision": v677.get("decision"), "arm_decision": arm.get("decision")},
            "next_step": "rerun V677 replay before V678 classification",
        },
        {
            "name": "property-denials-cleared",
            "status": "pass" if property_denial_total == 0 and property_denial_unique == 0 else "blocked",
            "detail": {"total": property_denial_total, "unique": property_denial_unique},
            "next_step": "do not classify Binder as primary until property denials are zero",
        },
        {
            "name": "binder-devnodes-ready",
            "status": "pass" if all(row["exists"] == "1" and row["access_r"] == "1" for row in devices) else "blocked",
            "detail": devices,
            "next_step": "fix private binder devnode materialization before another Binder retry",
        },
        {
            "name": "service-manager-surface-ready",
            "status": "pass" if child_checks["service_manager_children_ready"] and child_checks["service_manager_binder_fds_ready"] else "blocked",
            "detail": {
                "children_ready": child_checks["service_manager_children_ready"],
                "binder_fds_ready": child_checks["service_manager_binder_fds_ready"],
            },
            "next_step": "fix service-manager child identity or Binder FD surface before retry",
        },
        {
            "name": "post-hal-surface-ready",
            "status": "pass" if child_checks["post_hal_children_ready"] and child_checks["post_hal_binder_fds_ready"] else "blocked",
            "detail": {
                "children_ready": child_checks["post_hal_children_ready"],
                "binder_fds_ready": child_checks["post_hal_binder_fds_ready"],
            },
            "next_step": "fix HAL/wificond child identity or Binder FD surface before retry",
        },
        {
            "name": "cnss-retry-surface-ready",
            "status": "pass" if child_checks["cnss_retry_observable_safe"] and child_checks["cnss_retry_reaches_vndbinder"] else "blocked",
            "detail": {
                "observable_safe": child_checks["cnss_retry_observable_safe"],
                "vndbinder_fd": child_checks["cnss_retry_reaches_vndbinder"],
            },
            "next_step": "fix CNSS retry setup before attributing transaction failure",
        },
        {
            "name": "wifi-lower-markers-still-absent",
            "status": "pass" if all(value == 0 for value in lower_zero.values()) else "review",
            "detail": lower_zero,
            "next_step": "if any lower marker advanced, route to scan/connect readiness instead of Binder repair",
        },
        {
            "name": "binder-failures-persist",
            "status": "finding" if binders["total"] > 0 else "review",
            "detail": {"total": binders["total"], "by_actor": binders["by_actor"], "by_kind": binders["by_kind"]},
            "next_step": "capture Binder registration and failed transaction target state",
        },
        {
            "name": "cnss-transaction-gap-present",
            "status": "finding" if cnss_tx > 0 and all(value == 0 for value in lower_zero.values()) else "review",
            "detail": {"cnss_daemon_failures": cnss_tx, "lower_zero": lower_zero},
            "next_step": "focus next live gate on CNSS vndbinder transaction context",
        },
        {
            "name": "registry-debug-snapshot-missing",
            "status": "finding" if not registry["registry_snapshot_enabled"] and not registry["binder_debug_snapshot_seen"] else "pass",
            "detail": registry,
            "next_step": "enable bounded registry/binder debug snapshot around the failing window",
        },
    ]


def decide(command: str, checks: list[dict[str, Any]]) -> tuple[str, bool, str, str]:
    if command == "plan":
        return (
            "v678-binder-failure-target-plan-ready",
            True,
            "plan-only; no device command or live mutation executed",
            "run V678 host-only classifier",
        )
    blocked = [check["name"] for check in checks if check["status"] == "blocked"]
    if blocked:
        return (
            "v678-binder-failure-target-blocked",
            False,
            "blocked by " + ", ".join(blocked),
            "refresh V677 evidence before Binder target classification",
        )
    findings = {check["name"] for check in checks if check["status"] == "finding"}
    if {"binder-failures-persist", "cnss-transaction-gap-present", "registry-debug-snapshot-missing"} <= findings:
        return (
            "v678-property-clean-binder-transaction-targets-classified",
            True,
            (
                "V677 removed property denials while service-manager, HAL/wificond, and CNSS retry surfaces "
                "all started with expected Binder FDs; the remaining native blocker is Binder transaction/"
                "registration state, especially the cnss-daemon vndbinder transaction failure before WLFW."
            ),
            (
                "plan V679 as a bounded Binder registry/debug snapshot and CNSS transaction-context capture "
                "in the same private namespace; keep supplicant, scan/connect, credentials, DHCP, routes, "
                "and external ping blocked"
            ),
        )
    return (
        "v678-binder-failure-target-review",
        False,
        "V677 evidence did not match the expected property-clean Binder-failure target pattern",
        "inspect V677 dmesg/helper evidence before selecting another live gate",
    )


def row_value(value: Any) -> str:
    if isinstance(value, (dict, list)):
        return json.dumps(value, sort_keys=True)
    return "" if value is None else str(value)


def child_rows(children: dict[str, dict[str, Any]]) -> list[list[str]]:
    rows: list[list[str]] = []
    for name in SURFACE_CHILDREN:
        child = children[name]
        rows.append([
            name,
            row_value(child["start_order"]),
            row_value(child["child_started"]),
            row_value(child["observable"]),
            row_value(child["postflight_safe"]),
            child["selinux_exec"],
            row_value(child["binder_fd"]),
            row_value(child["hwbinder_fd"]),
            row_value(child["vndbinder_fd"]),
        ])
    return rows


def binder_rows(summary: dict[str, Any]) -> list[list[str]]:
    return [
        [
            row["actor"],
            row["kind"],
            row["code"],
            row["errno"],
            "" if row["timestamp"] is None else f"{row['timestamp']:.6f}",
        ]
        for row in summary["failures"]
    ]


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    v677 = load_json(args.v677_manifest)
    arm_path = resolve_arm_manifest(args, v677)
    arm = load_json(arm_path)
    live = arm.get("live") or {}
    helper = load_helper(arm_path, arm)
    keys = parse_keys(helper)
    dmesg = load_dmesg(arm_path, arm)
    failures = parse_binder_failures(dmesg)
    binders = binder_summary(failures)
    counts = marker_counts(live)
    children = {name: child_surface(keys, name) for name in SURFACE_CHILDREN}
    devices = binder_device_rows(keys)
    registry = registry_surface(keys)
    checks = build_checks(v677, arm, live, counts, binders, children, devices, registry)
    decision, pass_ok, reason, next_step = decide(args.command, checks)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "cycle": "v678",
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "inputs": {
            "v677_manifest": str(repo_path(args.v677_manifest)),
            "arm_manifest": str(arm_path),
        },
        "prior": {
            "v677": {"decision": v677.get("decision"), "pass": v677.get("pass")},
            "arm": {"decision": arm.get("decision"), "pass": arm.get("pass")},
        },
        "property_surface": live.get("v676_property_runtime_surface") or {},
        "property_target_coverage": live.get("v676_property_target_coverage") or {},
        "counts": counts,
        "binder_summary": binders,
        "children": children,
        "binder_devices": devices,
        "registry_surface": registry,
        "checks": checks,
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


def render_summary(manifest: dict[str, Any]) -> str:
    property_surface = manifest["property_surface"]
    marker_rows = [[name, str(manifest["counts"].get(name, 0))] for name in LOWER_ZERO_MARKERS]
    device_rows = [
        [row["device"], row["exists"], row["access_r"], row["mode"], row["rdev"]]
        for row in manifest["binder_devices"]
    ]
    check_rows = [
        [check["name"], check["status"], json.dumps(check["detail"], sort_keys=True), check["next_step"]]
        for check in manifest["checks"]
    ]
    return "\n".join([
        "# V678 Binder Failure Target Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- service_manager_start_executed: `{manifest['service_manager_start_executed']}`",
        f"- wifi_hal_start_executed: `{manifest['wifi_hal_start_executed']}`",
        f"- scan_connect_executed: `{manifest['scan_connect_executed']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        f"- external_ping_executed: `{manifest['external_ping_executed']}`",
        "",
        "## Checks",
        "",
        markdown_table(["check", "status", "detail", "next"], check_rows),
        "",
        "## Property Surface",
        "",
        f"- property_denial_total: `{property_surface.get('property_denial_total', 0)}`",
        f"- property_denial_unique: `{property_surface.get('property_denial_unique', 0)}`",
        f"- binder_failure_count: `{property_surface.get('binder_failure_count', manifest['binder_summary']['total'])}`",
        "",
        "## Binder Failures",
        "",
        f"- total: `{manifest['binder_summary']['total']}`",
        f"- by_actor: `{json.dumps(manifest['binder_summary']['by_actor'], sort_keys=True)}`",
        f"- by_kind: `{json.dumps(manifest['binder_summary']['by_kind'], sort_keys=True)}`",
        f"- by_code: `{json.dumps(manifest['binder_summary']['by_code'], sort_keys=True)}`",
        "",
        markdown_table(["actor", "kind", "code", "errno", "first_time"], binder_rows(manifest["binder_summary"])),
        "",
        "## Child Binder Surface",
        "",
        markdown_table(
            ["child", "order", "started", "observable", "safe", "selinux", "binder", "hwbinder", "vndbinder"],
            child_rows(manifest["children"]),
        ),
        "",
        "## Binder Devices",
        "",
        markdown_table(["device", "exists", "access_r", "mode", "rdev"], device_rows),
        "",
        "## Lower Wi-Fi Markers",
        "",
        markdown_table(["marker", "count"], marker_rows),
        "",
        "## Registry/Debug Snapshot Surface",
        "",
        markdown_table(
            ["field", "value"],
            [[key, row_value(value)] for key, value in sorted(manifest["registry_surface"].items())],
        ),
        "",
        "## Interpretation",
        "",
        "- V677 made the private property runtime clean: no property denial remains in the replay evidence.",
        "- Service managers, Wi-Fi HAL processes, `wificond`, and fresh `cnss-daemon` retry all started and exposed the expected Binder FD class.",
        "- Generic service-manager or `wificond` Binder ioctl `-22` remains a separate noise class; the target blocker is the CNSS vndbinder transaction failure while WLFW/BDF/`wlan0` stay absent.",
        "- The next live unit should capture Binder registry/debug/failed-transaction state around the same failing window, not start supplicant or attempt scan/connect.",
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
    print(f"service_manager_start_executed: {manifest['service_manager_start_executed']}")
    print(f"wifi_hal_start_executed: {manifest['wifi_hal_start_executed']}")
    print(f"scan_connect_executed: {manifest['scan_connect_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

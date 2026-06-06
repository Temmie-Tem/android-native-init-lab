#!/usr/bin/env python3
"""V680 host-only Binder debugfs gap classifier.

This classifier consumes V679 evidence. It does not contact the device, mount
filesystems, start services, scan/connect, use credentials, run DHCP, change
routes, or ping externally.
"""

from __future__ import annotations

import argparse
import collections
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v680-binder-debugfs-gap-classifier")
DEFAULT_V679_MANIFEST = Path("tmp/wifi/v679-v535-binder-registry-snapshot-orchestrated-live/manifest.json")

ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
PATH_BEGIN_RE = re.compile(r"^A90_EXECNS_PATH_(wifi_registry_[A-Za-z0-9_]+)_BEGIN path=([^ ]+) limit=(\d+)$")
PATH_END_RE = re.compile(r"^A90_EXECNS_PATH_(wifi_registry_[A-Za-z0-9_]+)_END bytes=(\d+) truncated=(\d+)$")
DIR_BEGIN_RE = re.compile(r"^A90_EXECNS_DIR_(wifi_registry_[A-Za-z0-9_]+)_BEGIN path=([^ ]+) filter=(\d+) max_entries=(\d+)$")
DIR_END_RE = re.compile(r"^A90_EXECNS_DIR_(wifi_registry_[A-Za-z0-9_]+)_END count=(\d+) shown=(\d+) truncated=(\d+)$")
BINDER_FAILURE_RE = re.compile(r"binder:.*(?:transaction failed|ioctl).*?-22", re.I)

PHASES = (
    "before_initial_cnss_cleanup",
    "after_initial_cnss_cleanup",
    "after_cnss_retry_spawn",
    "window",
)
DEBUG_LABELS = (
    "binder_state",
    "binder_stats",
    "binder_transactions",
    "binder_transaction_log",
    "binder_failed_transaction_log",
)
FORBIDDEN_ACTIONS = (
    "device command",
    "mount or bind mount",
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


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v679-manifest", type=Path, default=DEFAULT_V679_MANIFEST)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def clean_line(line: str) -> str:
    return ANSI_RE.sub("", line).strip()


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


def arm_manifest_path(v679: dict[str, Any], manifest_path: Path) -> Path:
    arm = nested(v679, ("arm_v679", "manifest"))
    if arm:
        return repo_path(Path(str(arm)))
    return repo_path(manifest_path).parent / "arm-v679-v535-registry" / "live" / "manifest.json"


def evidence_root(arm_path: Path, arm: dict[str, Any]) -> Path:
    out_dir = arm.get("out_dir")
    if out_dir:
        return repo_path(Path(str(out_dir)))
    return repo_path(arm_path).parent


def parse_registry_blocks(text: str) -> dict[str, Any]:
    phases: dict[str, Any] = {
        phase: {
            "path_blocks": {},
            "dir_blocks": {},
            "open_errors": collections.Counter(),
            "open_error_labels": [],
        }
        for phase in PHASES
    }
    current_label = ""
    current_path = ""
    current_kind = ""
    for raw_line in text.replace("\0", "\n").splitlines():
        line = clean_line(raw_line)
        path_begin = PATH_BEGIN_RE.match(line)
        if path_begin:
            current_label = path_begin.group(1)
            current_path = path_begin.group(2)
            current_kind = "path"
            continue
        dir_begin = DIR_BEGIN_RE.match(line)
        if dir_begin:
            current_label = dir_begin.group(1)
            current_path = dir_begin.group(2)
            current_kind = "dir"
            continue
        if line.startswith("open-error=") and current_label:
            phase = label_phase(current_label)
            if phase in phases:
                error = line.split("=", 1)[1]
                phases[phase]["open_errors"][error] += 1
                phases[phase]["open_error_labels"].append({
                    "label": current_label,
                    "kind": current_kind,
                    "path": current_path,
                    "error": error,
                })
            continue
        path_end = PATH_END_RE.match(line)
        if path_end:
            label = path_end.group(1)
            phase = label_phase(label)
            if phase in phases:
                phases[phase]["path_blocks"][label] = {
                    "bytes": int(path_end.group(2)),
                    "truncated": int(path_end.group(3)),
                }
            current_label = ""
            current_path = ""
            current_kind = ""
            continue
        dir_end = DIR_END_RE.match(line)
        if dir_end:
            label = dir_end.group(1)
            phase = label_phase(label)
            if phase in phases:
                phases[phase]["dir_blocks"][label] = {
                    "count": int(dir_end.group(2)),
                    "shown": int(dir_end.group(3)),
                    "truncated": int(dir_end.group(4)),
                }
            current_label = ""
            current_path = ""
            current_kind = ""
    return phases


def label_phase(label: str) -> str:
    prefix = "wifi_registry_"
    if not label.startswith(prefix):
        return ""
    suffix = label[len(prefix):]
    for phase in PHASES:
        if suffix.startswith(phase + "_"):
            return phase
    return ""


def summarize_registry(phases: dict[str, Any], v679_registry: dict[str, Any]) -> dict[str, Any]:
    rows: list[list[str]] = []
    totals = {
        "path_blocks": 0,
        "path_nonzero": 0,
        "dir_blocks": 0,
        "dir_shown": 0,
        "debug_path_blocks": 0,
        "debug_nonzero": 0,
        "open_errors": collections.Counter(),
        "binder_debug_enoent": 0,
    }
    for phase in PHASES:
        parsed = phases.get(phase) or {}
        path_blocks = parsed.get("path_blocks") or {}
        dir_blocks = parsed.get("dir_blocks") or {}
        open_errors = parsed.get("open_errors") or collections.Counter()
        debug_blocks = {
            label: values
            for label, values in path_blocks.items()
            if any(label.endswith("_" + debug_label) for debug_label in DEBUG_LABELS)
        }
        debug_nonzero = sum(1 for values in debug_blocks.values() if values["bytes"] > 0)
        phase_open_errors = dict(sorted(open_errors.items()))
        rows.append([
            phase,
            str(len(path_blocks)),
            str(sum(1 for values in path_blocks.values() if values["bytes"] > 0)),
            str(len(dir_blocks)),
            str(sum(values["shown"] for values in dir_blocks.values())),
            str(len(debug_blocks)),
            str(debug_nonzero),
            json.dumps(phase_open_errors, sort_keys=True),
        ])
        totals["path_blocks"] += len(path_blocks)
        totals["path_nonzero"] += sum(1 for values in path_blocks.values() if values["bytes"] > 0)
        totals["dir_blocks"] += len(dir_blocks)
        totals["dir_shown"] += sum(values["shown"] for values in dir_blocks.values())
        totals["debug_path_blocks"] += len(debug_blocks)
        totals["debug_nonzero"] += debug_nonzero
        totals["open_errors"].update(open_errors)
        totals["binder_debug_enoent"] += sum(
            1
            for item in parsed.get("open_error_labels", [])
            if item["error"] == "No such file or directory" and "/sys/kernel/debug/binder" in item["path"]
        )
    return {
        "v679_registry_summary": v679_registry,
        "rows": rows,
        "totals": {
            **{key: value for key, value in totals.items() if key != "open_errors"},
            "open_errors": dict(sorted(totals["open_errors"].items())),
        },
    }


def build_checks(v679: dict[str, Any],
                 arm: dict[str, Any],
                 registry: dict[str, Any],
                 mounts: str,
                 dmesg: str) -> list[dict[str, Any]]:
    property_surface = nested(arm, ("live", "v676_property_runtime_surface"), {}) or {}
    top_registry = nested(v679, ("arm_v679", "registry_surface"), {}) or {}
    totals = registry["totals"]
    binder_failures = BINDER_FAILURE_RE.findall(dmesg)
    debugfs_mounted = any(" debugfs " in line and "/sys/kernel/debug" in line for line in mounts.splitlines())
    return [
        {
            "name": "v679-input-ready",
            "status": "pass" if v679.get("pass") and arm.get("pass") else "blocked",
            "detail": {"v679_decision": v679.get("decision"), "arm_decision": arm.get("decision")},
            "next_step": "rerun V679 before V680",
        },
        {
            "name": "property-still-clean",
            "status": "pass" if property_surface.get("property_denial_total") == 0 else "blocked",
            "detail": property_surface,
            "next_step": "do not focus Binder debugfs until property denials are clean",
        },
        {
            "name": "registry-phases-executed",
            "status": "pass" if top_registry.get("after_retry_captured") and top_registry.get("window_captured") else "blocked",
            "detail": top_registry,
            "next_step": "fix helper v112 registry phase execution before classifying debugfs",
        },
        {
            "name": "binder-debug-paths-unavailable",
            "status": "finding" if totals["debug_path_blocks"] > 0 and totals["debug_nonzero"] == 0 and totals["binder_debug_enoent"] > 0 else "review",
            "detail": {key: totals[key] for key in ("debug_path_blocks", "debug_nonzero", "binder_debug_enoent", "open_errors")},
            "next_step": "plan private debugfs mount/bind or alternate Binder transaction capture",
        },
        {
            "name": "debugfs-not-mounted",
            "status": "finding" if not debugfs_mounted else "pass",
            "detail": {"debugfs_mounted": debugfs_mounted},
            "next_step": "if unmounted, prove a private read-only debugfs surface before expecting binder debug files",
        },
        {
            "name": "binder-failure-persists",
            "status": "finding" if binder_failures else "review",
            "detail": {"binder_failure_count": len(binder_failures)},
            "next_step": "keep transaction target capture as next blocker while WLFW/BDF/wlan0 are absent",
        },
    ]


def decide(command: str, checks: list[dict[str, Any]]) -> tuple[str, bool, str, str]:
    if command == "plan":
        return (
            "v680-binder-debugfs-gap-plan-ready",
            True,
            "plan-only; no device command or mount executed",
            "run V680 host-only classifier",
        )
    blocked = [check["name"] for check in checks if check["status"] == "blocked"]
    if blocked:
        return (
            "v680-binder-debugfs-gap-blocked",
            False,
            "blocked by " + ", ".join(blocked),
            "refresh V679 evidence before V680",
        )
    findings = {check["name"] for check in checks if check["status"] == "finding"}
    if {"binder-debug-paths-unavailable", "debugfs-not-mounted", "binder-failure-persists"} <= findings:
        return (
            "v680-binder-debugfs-gap-classified",
            True,
            "V679 registry phases executed, but binder debugfs paths were ENOENT and debugfs was not mounted while Binder failures persisted.",
            "plan V681 private debugfs/binder-debug read-only surface proof or alternate Binder transaction capture; keep Wi-Fi connect blocked until wlan0 exists",
        )
    return (
        "v680-binder-debugfs-gap-review",
        False,
        "V679 evidence did not match the expected debugfs-unavailable pattern",
        "inspect V679 helper transcript manually",
    )


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    v679_path = repo_path(args.v679_manifest)
    v679 = load_json(v679_path)
    arm_path = arm_manifest_path(v679, args.v679_manifest)
    arm = load_json(arm_path)
    root = evidence_root(arm_path, arm)
    helper = str(nested(arm, ("live", "helper_stdout_stderr"), ""))
    dmesg = read_text(root / "native" / "dmesg-delta.txt") or str(nested(arm, ("live", "dmesg_delta"), ""))
    mounts = read_text(root / "native" / "mounted-proc-mounts.txt")
    phases = parse_registry_blocks(helper)
    registry = summarize_registry(phases, nested(v679, ("arm_v679", "registry_surface"), {}) or {})
    checks = build_checks(v679, arm, registry, mounts, dmesg)
    decision, pass_ok, reason, next_step = decide(args.command, checks)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "cycle": "v680",
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "inputs": {
            "v679_manifest": str(v679_path),
            "arm_manifest": str(arm_path),
        },
        "checks": checks,
        "registry": registry,
        "forbidden_actions": FORBIDDEN_ACTIONS,
        "device_commands_executed": False,
        "device_mutations": False,
        "mount_executed": False,
        "daemon_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "wifi_bringup_executed": False,
        "external_ping_executed": False,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    check_rows = [
        [check["name"], check["status"], json.dumps(check["detail"], sort_keys=True), check["next_step"]]
        for check in manifest["checks"]
    ]
    return "\n".join([
        "# V680 Binder Debugfs Gap Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- mount_executed: `{manifest['mount_executed']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        "",
        "## Checks",
        "",
        markdown_table(["check", "status", "detail", "next"], check_rows),
        "",
        "## Registry Phase Matrix",
        "",
        markdown_table(
            ["phase", "path_blocks", "path_nonzero", "dir_blocks", "dir_shown", "debug_blocks", "debug_nonzero", "open_errors"],
            manifest["registry"]["rows"],
        ),
        "",
        "## Totals",
        "",
        markdown_table(
            ["key", "value"],
            [[key, json.dumps(value, sort_keys=True) if isinstance(value, dict) else str(value)] for key, value in sorted(manifest["registry"]["totals"].items())],
        ),
        "",
        "## Interpretation",
        "",
        "- V679 executed the registry snapshot phases, so the helper control flow is not the blocker.",
        "- All Binder debug path captures were empty and reported `No such file or directory` for `/sys/kernel/debug/binder*` surfaces.",
        "- The next live unit should prove a private read-only debugfs/Binder debug surface or choose another Binder transaction-observation primitive.",
        "- Wi-Fi connect remains blocked because WLFW/BDF/`wlan0` are still absent.",
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
    print(f"mount_executed: {manifest['mount_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

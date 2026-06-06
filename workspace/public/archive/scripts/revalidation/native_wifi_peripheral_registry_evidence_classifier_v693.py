#!/usr/bin/env python3
"""V693 host-only classifier for V692 PeripheralManager registry evidence."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v693-peripheral-registry-evidence-classifier")
DEFAULT_V692_MANIFEST = Path("tmp/wifi/v692-peripheral-manager-registry-snapshot-orchestrated-live/manifest.json")
REGISTRY_PHASES = (
    "before_initial_cnss_cleanup",
    "after_initial_cnss_cleanup",
    "after_per_mgr_probe",
    "after_per_proxy_probe",
    "window",
)
FORBIDDEN_ACTIONS = (
    "device command",
    "helper deploy",
    "daemon or service start",
    "Wi-Fi HAL, wificond, supplicant, or hostapd start",
    "scan/connect/link-up",
    "credential, DHCP, route change, or external ping",
    "sysfs subsystem state write",
    "esoc0 open or hold",
    "boot image or partition write",
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v692-manifest", type=Path, default=DEFAULT_V692_MANIFEST)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def read_text(path: Path) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    return resolved.read_bytes().replace(b"\0", b"\n").decode("utf-8", errors="replace")


def load_json(path: Path) -> dict[str, Any]:
    text = read_text(path)
    if not text:
        return {"present": False, "path": str(repo_path(path))}
    data = json.loads(text)
    data["present"] = True
    data["path"] = str(repo_path(path))
    return data


def parse_keys(text: str) -> dict[str, str]:
    keys: dict[str, str] = {}
    for line in text.splitlines():
        match = re.match(r"^([A-Za-z0-9_.-]+)=(.*)$", line.strip())
        if match:
            keys[match.group(1)] = match.group(2).strip()
    return keys


def evidence_dir(manifest: dict[str, Any], fallback_manifest: Path) -> Path:
    evidence = manifest.get("evidence") or manifest.get("out_dir")
    if evidence:
        return repo_path(Path(str(evidence)))
    return repo_path(fallback_manifest).parent


def arm_manifest_from_v692(v692_path: Path, v692: dict[str, Any]) -> dict[str, Any]:
    arm_path = ((v692.get("arm_v692") or {}).get("manifest") or "")
    if not arm_path:
        arm_path = str(repo_path(v692_path).parent / "arm-v692-v116-peripheral-manager" / "live" / "manifest.json")
    return load_json(Path(str(arm_path)))


def companion_path(v692_path: Path, v692: dict[str, Any], arm: dict[str, Any]) -> Path:
    arm_path = Path(str((v692.get("arm_v692") or {}).get("manifest") or v692_path))
    return evidence_dir(arm, arm_path) / "native" / "companion-start-only-with-holder.txt"


def child_surface(keys: dict[str, str], name: str) -> dict[str, Any]:
    child_prefix = f"wifi_companion_start.child.{name}."
    start_prefix = f"wifi_hal_composite_start.child.{name}."
    context_prefix = f"wifi_hal_composite_child.{name}."
    fd_prefix = f"capture.wifi_hal_composite_{name}.fd_links."
    fd_targets = [
        value
        for key, value in keys.items()
        if key.startswith(fd_prefix) and key.endswith(".target")
    ]
    return {
        "pid": keys.get(start_prefix + "pid", ""),
        "target": keys.get(start_prefix + "target", ""),
        "start_order": keys.get(child_prefix + "start_order", ""),
        "observable": keys.get(child_prefix + "observable", ""),
        "exited": keys.get(child_prefix + "exited", ""),
        "exit_code": keys.get(child_prefix + "exit_code", ""),
        "signal": keys.get(child_prefix + "signal", ""),
        "postflight_safe": keys.get(child_prefix + "postflight_safe", ""),
        "fd_count": keys.get(fd_prefix + "count", ""),
        "socket_count": keys.get(fd_prefix + "socket_count", ""),
        "has_vndbinder_fd": any(target.endswith("/dev/vndbinder") for target in fd_targets),
        "has_binder_fd": any(target.endswith("/dev/binder") for target in fd_targets),
        "has_hwbinder_fd": any(target.endswith("/dev/hwbinder") for target in fd_targets),
        "selinux_context_mode": keys.get(context_prefix + "selinux_context_mode", ""),
        "selinux_exec_target_context": keys.get(context_prefix + "selinux_exec.target_context", ""),
        "selinux_exec_skipped": keys.get(context_prefix + "selinux_exec.skipped", ""),
        "selinux_exec_reason": keys.get(context_prefix + "selinux_exec.reason", ""),
        "attr_current": child_attr_current(keys, name),
    }


def child_attr_current(keys: dict[str, str], name: str) -> str:
    marker = f"capture.wifi_hal_composite_{name}.attr_current"
    for key, value in keys.items():
        if key.startswith(marker) and value.startswith("u:r:"):
            return value
    return ""


def dir_entries(text: str, label: str) -> list[str]:
    entries: list[str] = []
    in_block = False
    begin = f"A90_EXECNS_DIR_{label}_BEGIN"
    end = f"A90_EXECNS_DIR_{label}_END"
    for line in text.splitlines():
        if line.startswith(begin):
            in_block = True
            continue
        if line.startswith(end):
            in_block = False
            continue
        if not in_block:
            continue
        match = re.match(r"entry\.\d+=(.*)$", line.strip())
        if match:
            entries.append(match.group(1))
    return entries


def registry_surface(keys: dict[str, str], text: str, arm: dict[str, Any]) -> dict[str, Any]:
    arm_surface = (arm.get("arm_v692") or {}).get("registry_snapshot") or arm.get("registry_snapshot_surface") or {}
    phases: dict[str, Any] = {}
    for phase in REGISTRY_PHASES:
        dev_socket_entries = dir_entries(text, f"wifi_registry_{phase}_dev_socket_dir")
        phases[phase] = {
            "begin": keys.get(f"wifi_registry_snapshot.{phase}.begin", ""),
            "end": keys.get(f"wifi_registry_snapshot.{phase}.end", ""),
            "child_count": keys.get(f"wifi_registry_snapshot.{phase}.child_count", ""),
            "files_captured": keys.get(f"wifi_registry_snapshot.{phase}.files_captured", ""),
            "dirs_captured": keys.get(f"wifi_registry_snapshot.{phase}.dirs_captured", ""),
            "child_proc_captured": keys.get(f"wifi_registry_snapshot.{phase}.child_proc_captured", ""),
            "dev_socket_entries": dev_socket_entries,
            "dev_socket_non_property_entries": [
                entry for entry in dev_socket_entries
                if entry != "property_service"
            ],
        }
    return {
        "manifest_surface": arm_surface,
        "phases": phases,
        "complete": all(
            phase["begin"] == "1" and phase["end"] == "1"
            for phase in phases.values()
        ),
        "binder_debug_available": any(
            str(phase.get("files_captured")) not in {"", "0"} or
            str(phase.get("child_proc_captured")) not in {"", "0"}
            for phase in phases.values()
        ),
        "dev_socket_only_property_service": all(
            phase["dev_socket_entries"] == ["property_service"]
            for phase in phases.values()
        ),
    }


def provider_stdout_stderr_surface(text: str) -> dict[str, Any]:
    stderr = ""
    match = re.search(r"A90_EXECNS_STDERR_BEGIN\n(.*?)\nA90_EXECNS_STDERR_END", text, re.S)
    if match:
        stderr = match.group(1)
    interesting = [
        line for line in stderr.splitlines()
        if any(token in line.lower() for token in ("pm-service", "pm-proxy", "peripheral", "binder", "vnd"))
    ]
    return {
        "stderr_present": bool(stderr.strip()),
        "stderr_lines": stderr.splitlines()[:20],
        "provider_related_stderr": interesting[:20],
        "provider_error_lines_in_stdout": [
            line for line in text.splitlines()
            if any(token in line.lower() for token in ("pm-service", "pm-proxy", "peripheral"))
            and any(token in line.lower() for token in ("error", "failed", "denied", "cannot", "unable"))
        ][:40],
    }


def marker_counts(v692: dict[str, Any]) -> dict[str, Any]:
    return ((v692.get("arm_v692") or {}).get("counts") or {})


def decide(command: str,
           v692: dict[str, Any],
           arm: dict[str, Any],
           children: dict[str, Any],
           registry: dict[str, Any]) -> tuple[str, bool, str, str]:
    if command == "plan":
        return (
            "v693-peripheral-registry-evidence-classifier-plan-ready",
            True,
            "plan-only; no evidence parsed",
            "run host-only classifier against V692 evidence",
        )
    if not v692.get("present") or not arm.get("present"):
        return "v693-missing-v692-evidence", False, "V692 top-level or arm manifest missing", "restore V692 evidence before V693"
    if v692.get("decision") != "v692-provider-registration-snapshot-captured":
        return "v693-v692-state-mismatch", False, f"v692_decision={v692.get('decision')}", "refresh V692 evidence before V693"
    if not registry.get("complete"):
        return "v693-registry-snapshot-incomplete", False, f"registry={registry}", "fix V692 snapshot completeness first"

    per_mgr = children.get("per_mgr") or {}
    per_proxy = children.get("per_proxy") or {}
    if (
        per_mgr.get("has_vndbinder_fd")
        and per_mgr.get("exited") == "1"
        and per_mgr.get("exit_code") == "0"
        and per_proxy.get("fd_count") in {"", "0"}
        and per_proxy.get("exit_code") == "1"
        and not registry.get("binder_debug_available")
    ):
        return (
            "v693-provider-registration-observability-gap-classified",
            True,
            "pm-service opens vndbinder then exits 0; pm-proxy exits 1 before opening fds; binder debugfs is unavailable, so V692 cannot prove vndservice registration",
            "add a bounded vndservicemanager service-query or provider self-query proof before Wi-Fi HAL start",
        )
    if registry.get("binder_debug_available"):
        return (
            "v693-provider-binder-registry-ready-for-query",
            True,
            "binder debugfs content exists in V692; parse service entries before changing runtime behavior",
            "parse binder registry service names and provider nodes",
        )
    return (
        "v693-provider-registration-manual-review",
        True,
        f"children={children} registry={registry}",
        "inspect V692 provider evidence manually before further live changes",
    )


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    v692 = load_json(args.v692_manifest)
    arm = {} if args.command == "plan" else arm_manifest_from_v692(args.v692_manifest, v692)
    path = companion_path(args.v692_manifest, v692, arm)
    text = "" if args.command == "plan" else read_text(path)
    keys = parse_keys(text)
    children = {
        name: child_surface(keys, name)
        for name in ("per_mgr", "per_proxy", "cnss_daemon_retry", "vndservicemanager")
    }
    registry = registry_surface(keys, text, v692.get("arm_v692") or {})
    output = provider_stdout_stderr_surface(text)
    decision, pass_ok, reason, next_step = decide(args.command, v692, arm, children, registry)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "cycle": "v693",
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "inputs": {
            "v692": {
                "path": v692.get("path"),
                "present": bool(v692.get("present")),
                "decision": v692.get("decision"),
                "pass": v692.get("pass"),
            },
            "v692_arm": {
                "path": arm.get("path"),
                "present": bool(arm.get("present")),
                "decision": arm.get("decision"),
                "pass": arm.get("pass"),
            },
            "companion_output": {
                "path": str(path),
                "present": bool(text),
                "bytes": len(text.encode("utf-8")),
            },
        },
        "provider_children": children,
        "registry_surface": registry,
        "provider_output_surface": output,
        "marker_counts": marker_counts(v692),
        "forbidden_actions": FORBIDDEN_ACTIONS,
        "device_commands_executed": False,
        "device_mutations": False,
        "daemon_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "wifi_bringup_executed": False,
        "external_ping_executed": False,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    child_rows = []
    for name, surface in (manifest.get("provider_children") or {}).items():
        child_rows.append([
            name,
            surface.get("start_order", ""),
            surface.get("observable", ""),
            surface.get("exited", ""),
            surface.get("exit_code", ""),
            surface.get("fd_count", ""),
            str(surface.get("has_vndbinder_fd", "")),
            surface.get("selinux_exec_reason", ""),
        ])
    registry_rows = []
    for phase, surface in ((manifest.get("registry_surface") or {}).get("phases") or {}).items():
        registry_rows.append([
            phase,
            surface.get("begin", ""),
            surface.get("end", ""),
            surface.get("files_captured", ""),
            surface.get("child_proc_captured", ""),
            ",".join(surface.get("dev_socket_entries") or []),
        ])
    return "\n".join([
        "# V693 Peripheral Registry Evidence Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- wifi_hal_start_executed: `{manifest['wifi_hal_start_executed']}`",
        f"- scan_connect_executed: `{manifest['scan_connect_executed']}`",
        f"- external_ping_executed: `{manifest['external_ping_executed']}`",
        "",
        "## Provider Children",
        "",
        markdown_table(
            ["child", "order", "observable", "exited", "exit", "fd_count", "vndbinder", "selinux_reason"],
            child_rows,
        ) if child_rows else "- no child surface",
        "",
        "## Registry Phases",
        "",
        markdown_table(
            ["phase", "begin", "end", "files", "child_proc", "dev_socket"],
            registry_rows,
        ) if registry_rows else "- no registry surface",
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
    print(f"wifi_hal_start_executed: {manifest['wifi_hal_start_executed']}")
    print(f"scan_connect_executed: {manifest['scan_connect_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""V1343 bounded provider-ready SDX50M route live gate.

Runs the V1342-selected next gate:

1. refresh current-boot V490 SELinux policy-load proof with helper v279;
2. run the V1221-proven private cnss-daemon SDX50M route with helper v279;
3. classify whether SDX50M client registration reaches eSoC, WLFW/BDF, or wlan0.

No Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping are
executed by this wrapper.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import time
from pathlib import Path
from typing import Any

import native_wifi_android_pre_cnss_provider_policy_ready_live_v1341 as v1341
import native_wifi_android_pre_cnss_provider_observer_live_v1339 as base
from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1343-provider-ready-sdx50m-route-live")
LATEST_POINTER = Path("tmp/wifi/latest-v1343-provider-ready-sdx50m-route-live.txt")
REPORT_PATH = Path("docs/reports/NATIVE_INIT_V1343_PROVIDER_READY_SDX50M_ROUTE_LIVE_2026-06-01.md")
DEFAULT_V490_OUT_DIR = Path("tmp/wifi/v1343-v490-policy-load")
DEFAULT_V1221_OUT_DIR = Path("tmp/wifi/v1343-v1221-sdx50m-route")
DEFAULT_HELPER = "/cache/bin/a90_android_execns_probe"
DEFAULT_LOCAL_HELPER = Path("stage3/linux_init/helpers/a90_android_execns_probe_v279")
DEFAULT_HELPER_SHA256 = "2ec7c9584e0adb09755e1066ee01a986e3b7fd719c11b8a96aaf5c500d9dd15a"
DEFAULT_HELPER_MARKER = "a90_android_execns_probe v279"
DEFAULT_PRIVATE_CNSS = "/cache/bin/cnss-daemon.sdx50m"
DEFAULT_PRIVATE_CNSS_SHA256 = "784fd7bd9b602d8e1f94c9ceef977845909f452611025c40fda589d0e57de5fd"
V490_APPROVAL = v1341.V490_APPROVAL


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).astimezone().isoformat(timespec="seconds")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v490-out-dir", type=Path, default=DEFAULT_V490_OUT_DIR)
    parser.add_argument("--v1221-out-dir", type=Path, default=DEFAULT_V1221_OUT_DIR)
    parser.add_argument(
        "--reuse-v1221-manifest",
        type=Path,
        default=None,
        help="reuse an existing V1221 live manifest instead of starting PM/CNSS actors",
    )
    parser.add_argument("--host", "--bridge-host", dest="host", default=base.v857.DEFAULT_HOST)
    parser.add_argument("--port", "--bridge-port", dest="port", type=int, default=base.v857.DEFAULT_PORT)
    parser.add_argument("--device-ip", default=base.v857.DEFAULT_DEVICE_IP)
    parser.add_argument("--tcp-timeout", type=float, default=90.0)
    parser.add_argument("--timeout", type=float, default=base.v857.DEFAULT_TIMEOUT)
    parser.add_argument("--busybox", default=base.v857.DEFAULT_BUSYBOX)
    parser.add_argument("--toybox", default=base.v857.DEFAULT_TOYBOX)
    parser.add_argument("--helper", default=DEFAULT_HELPER)
    parser.add_argument("--local-helper", type=Path, default=DEFAULT_LOCAL_HELPER)
    parser.add_argument("--helper-sha256", default=DEFAULT_HELPER_SHA256)
    parser.add_argument("--helper-marker", default=DEFAULT_HELPER_MARKER)
    parser.add_argument("--private-cnss-daemon", default=DEFAULT_PRIVATE_CNSS)
    parser.add_argument("--private-cnss-sha256", default=DEFAULT_PRIVATE_CNSS_SHA256)
    parser.add_argument("--tracefs-duration-sec", type=int, default=24)
    parser.add_argument("--thread-sample-count", type=int, default=160)
    parser.add_argument("--thread-sample-interval-sec", default="0.25")
    parser.add_argument("--allow-mountsystem-ro", action="store_true")
    parser.add_argument("--allow-selinuxfs-mount", action="store_true")
    parser.add_argument("--allow-policy-load", action="store_true")
    parser.add_argument("--allow-provider-ready-sdx50m-route", action="store_true")
    parser.add_argument("--allow-cleanup-reboot", action="store_true")
    parser.add_argument("--assume-yes", action="store_true")
    parser.add_argument("command", choices=("plan", "run", "recover"), nargs="?", default="run")
    return parser.parse_args()


def required_flags(args: argparse.Namespace) -> list[str]:
    missing = []
    for flag, enabled in (
        ("--allow-mountsystem-ro", args.allow_mountsystem_ro),
        ("--allow-selinuxfs-mount", args.allow_selinuxfs_mount),
        ("--allow-policy-load", args.allow_policy_load),
        ("--allow-provider-ready-sdx50m-route", args.allow_provider_ready_sdx50m_route),
        ("--allow-cleanup-reboot", args.allow_cleanup_reboot),
        ("--assume-yes", args.assume_yes),
    ):
        if not enabled:
            missing.append(flag)
    return missing


def read_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {}
    try:
        value = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def write_output(store: EvidenceStore, rel_path: str, text: str) -> None:
    store.write_text(rel_path, base.v857.redact(text).rstrip() + "\n")


def run_subprocess(command: list[str], *, timeout: float) -> tuple[int, str, float]:
    started = time.monotonic()
    result = subprocess.run(
        command,
        cwd=repo_path("."),
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
    )
    return result.returncode, result.stdout, time.monotonic() - started


def local_helper_info(args: argparse.Namespace) -> dict[str, Any]:
    return v1341.local_helper_info(args)


def run_v490(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    command = [
        "python3",
        "scripts/revalidation/native_selinux_policy_load_proof_v490.py",
        "--out-dir",
        str(args.v490_out_dir),
        "--host",
        args.host,
        "--port",
        str(args.port),
        "--timeout",
        str(args.timeout),
        "--expect-version",
        "A90 Linux init 0.9.68 (v724)",
        "--helper",
        args.helper,
        "--helper-sha256",
        args.helper_sha256,
        "--toybox",
        args.toybox,
        "--approval-phrase",
        V490_APPROVAL,
        "--apply",
        "--assume-yes",
        "run",
    ]
    rc, output, duration = run_subprocess(command, timeout=220.0)
    write_output(store, "host/v490-policy-load.txt", output)
    manifest = read_json(args.v490_out_dir / "manifest.json")
    return {
        "name": "v490-policy-load",
        "rc": rc,
        "ok": rc == 0 and manifest.get("decision") == "v490-selinux-policy-load-proof-pass",
        "duration_sec": round(duration, 3),
        "file": "host/v490-policy-load.txt",
        "manifest": str(args.v490_out_dir / "manifest.json"),
        "decision": manifest.get("decision", ""),
        "pass": manifest.get("pass"),
        "policy_load_executed": manifest.get("policy_load_executed"),
        "wifi_bringup_executed": manifest.get("wifi_bringup_executed"),
    }


def run_v1221_route(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    command = [
        "python3",
        "scripts/revalidation/native_wifi_private_cnss_daemon_sdx50m_live_v1221.py",
        "--out-dir",
        str(args.v1221_out_dir),
        "--host",
        args.host,
        "--port",
        str(args.port),
        "--device-ip",
        args.device_ip,
        "--tcp-timeout",
        str(args.tcp_timeout),
        "--busybox",
        args.busybox,
        "--toybox",
        args.toybox,
        "--helper",
        args.helper,
        "--helper-sha256",
        args.helper_sha256,
        "--helper-marker",
        args.helper_marker,
        "--tracefs-duration-sec",
        str(args.tracefs_duration_sec),
        "--thread-sample-count",
        str(args.thread_sample_count),
        "--thread-sample-interval-sec",
        args.thread_sample_interval_sec,
        "--allow-tracefs-mount",
        "--allow-tracefs-write",
        "--allow-vendor-mount",
        "--allow-selinuxfs-mount",
        "--allow-pm-service-trigger-observer",
        "--allow-cnss-daemon-start",
        "--assume-yes",
        "run",
    ]
    rc, output, duration = run_subprocess(command, timeout=max(240.0, args.tcp_timeout + 180.0))
    write_output(store, "host/v1221-sdx50m-route.txt", output)
    manifest_path = args.v1221_out_dir / "manifest.json"
    if not repo_path(manifest_path).exists():
        match = re.search(r"^evidence:\s+(.+)$", output, re.MULTILINE)
        if match:
            candidate = Path(match.group(1).strip()) / "manifest.json"
            try:
                manifest_path = candidate.relative_to(repo_path("."))
            except ValueError:
                manifest_path = candidate
    manifest = read_json(manifest_path)
    return {
        "name": "v1221-sdx50m-route",
        "rc": rc,
        "ok": rc == 0 and bool(manifest.get("pass")),
        "duration_sec": round(duration, 3),
        "file": "host/v1221-sdx50m-route.txt",
        "manifest": str(manifest_path),
        "decision": manifest.get("decision", ""),
        "pass": manifest.get("pass"),
        "reason": manifest.get("reason", ""),
        "next_step": manifest.get("next_step", ""),
    }


def latest_v1221_manifest() -> Path:
    pointer = repo_path(Path("tmp/wifi/latest-v1221-private-cnss-daemon-sdx50m-live.txt"))
    if pointer.exists():
        target = pointer.read_text(encoding="utf-8", errors="replace").strip()
        if target:
            try:
                return (Path(target) / "manifest.json").relative_to(repo_path("."))
            except ValueError:
                return Path(target) / "manifest.json"
    return Path("tmp/wifi/v1221-private-cnss-daemon-sdx50m-live/manifest.json")


def recover_v1221_route(args: argparse.Namespace) -> dict[str, Any]:
    manifest_path = args.reuse_v1221_manifest or latest_v1221_manifest()
    manifest = read_json(manifest_path)
    return {
        "name": "v1221-sdx50m-route-recovered",
        "rc": 0 if manifest else 1,
        "ok": bool(manifest.get("pass")),
        "duration_sec": 0.0,
        "file": "",
        "manifest": str(manifest_path),
        "decision": manifest.get("decision", ""),
        "pass": manifest.get("pass"),
        "reason": manifest.get("reason", ""),
        "next_step": manifest.get("next_step", ""),
    }


def extract_v1221(v1221_manifest: dict[str, Any]) -> dict[str, Any]:
    tracefs = ((v1221_manifest.get("analysis") or {}).get("tracefs_uprobe") or {})
    clients = ((tracefs.get("client_register_args_by_comm") or {}).get("cnss-daemon") or [])
    peripherals = [
        str(item.get("peripheral"))
        for item in clients
        if isinstance(item, dict) and item.get("peripheral")
    ]
    private_cnss = v1221_manifest.get("private_cnss_daemon") or {}
    post = ((v1221_manifest.get("analysis") or {}).get("post_surface") or {})
    dmesg_hits = post.get("wlfw_or_wlan_dmesg_hits") or []
    wlfw_or_wlan = any(
        any(token in str(line).lower() for token in ("wlfw", "bdf", "fw ready", "wlan0"))
        for line in dmesg_hits
    )
    thread_analysis = v1221_manifest.get("thread_analysis") or {}
    return {
        "decision": v1221_manifest.get("decision", ""),
        "pass": bool(v1221_manifest.get("pass")),
        "reason": v1221_manifest.get("reason", ""),
        "private_cnss_bind_rc": str(private_cnss.get("bind_rc", "")),
        "private_cnss_expected_c_string": str(private_cnss.get("expected_c_string", "")),
        "cnss_client_peripherals": peripherals,
        "thread_cnss_registered_peripherals": thread_analysis.get("cnss_registered_peripherals") or [],
        "sdx50m_registered": "SDX50M" in peripherals or "SDX50M" in (thread_analysis.get("cnss_registered_peripherals") or []),
        "per_mgr_esoc0_any": bool(v1221_manifest.get("per_mgr_esoc0_any")),
        "wlan0_up": bool(v1221_manifest.get("wlan0_up")),
        "wlfw_or_wlan_dmesg_seen": wlfw_or_wlan,
        "wifi_hal_start_executed": bool(v1221_manifest.get("wifi_hal_start_executed")),
        "scan_connect_executed": bool(v1221_manifest.get("scan_connect_executed")),
        "credential_use_executed": bool(v1221_manifest.get("credential_use_executed")),
        "dhcp_route_executed": bool(v1221_manifest.get("dhcp_route_executed")),
        "external_ping_executed": bool(v1221_manifest.get("external_ping_executed")),
        "wifi_bringup_executed": bool(v1221_manifest.get("wifi_bringup_executed")),
        "flash_executed": bool(v1221_manifest.get("flash_executed")),
        "partition_write_executed": bool(v1221_manifest.get("partition_write_executed")),
        "reboot_executed": bool(v1221_manifest.get("reboot_executed")),
    }


def route_brief(route: dict[str, Any]) -> str:
    return (
        f"sdx50m_registered={route.get('sdx50m_registered')} "
        f"per_mgr_esoc0_any={route.get('per_mgr_esoc0_any')} "
        f"wlfw_or_wlan_dmesg_seen={route.get('wlfw_or_wlan_dmesg_seen')} "
        f"wlan0_up={route.get('wlan0_up')}"
    )


def decide(args: argparse.Namespace,
           local: dict[str, Any],
           steps: list[dict[str, Any]],
           analysis: dict[str, Any]) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        if not (local["exists"] and local["sha256"] == args.helper_sha256 and local["marker"]):
            return "v1343-plan-helper-v279-missing", False, f"local={local}", "build/deploy helper v279 before V1343"
        return "v1343-provider-ready-sdx50m-route-plan-ready", True, "plan-only; no device command executed", "run bounded V1343 provider-ready SDX50M route"
    if args.command == "run":
        missing = required_flags(args)
        if missing:
            return "v1343-approval-required", False, f"missing flags: {', '.join(missing)}", "rerun with explicit V1343 flags"
    v490 = analysis.get("v490_policy_load") or {}
    if not v490.get("ok"):
        return "v1343-precondition-failed", False, f"v490={v490}", "repair current-boot V490 policy load before retry"
    route_step = analysis.get("v1221_route_step") or {}
    route = analysis.get("v1221_route") or {}
    if not route_step.get("ok"):
        return "v1343-precondition-failed", False, f"route_step={route_step}", "inspect V1221 route output before retry"
    forbidden = [
        key for key in (
            "wifi_hal_start_executed",
            "scan_connect_executed",
            "credential_use_executed",
            "dhcp_route_executed",
            "external_ping_executed",
            "wifi_bringup_executed",
            "flash_executed",
            "partition_write_executed",
        )
        if route.get(key)
    ]
    if forbidden:
        return "v1343-forbidden-action-detected", False, f"forbidden={forbidden}", "stop and audit route gate"
    if route.get("wlan0_up") or route.get("wlfw_or_wlan_dmesg_seen"):
        return (
            "v1343-sdx50m-route-wlfw-or-wlan0",
            True,
            route_brief(route),
            "classify WLFW/BDF/wlan0 readiness before Wi-Fi HAL, scan/connect, DHCP, or external ping",
        )
    if route.get("per_mgr_esoc0_any"):
        return (
            "v1343-sdx50m-route-esoc-powerup-observed",
            True,
            route_brief(route),
            "compare lower failure against V1222/V1324 response gap before Wi-Fi HAL or scan/connect",
        )
    if route.get("sdx50m_registered"):
        return (
            "v1343-sdx50m-client-registered-no-esoc",
            True,
            route_brief(route),
            "classify PM request/actionability despite SDX50M registration",
        )
    return (
        "v1343-provider-positive-no-sdx50m",
        True,
        route_brief(route),
        "inspect private bind/artifact/context before lower retry",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    step_rows = [[step["name"], step["ok"], step["rc"], step["duration_sec"], step["file"], step.get("decision", "")] for step in manifest.get("steps", [])]
    route = (manifest.get("analysis") or {}).get("v1221_route") or {}
    safety_rows = [[key, manifest.get(key)] for key in (
        "current_command_device_commands_executed",
        "recovered_from_live_evidence",
        "device_commands_executed",
        "device_mutations",
        "policy_load_executed",
        "pm_actor_executed",
        "cnss_daemon_start_executed",
        "tracefs_write_executed",
        "wifi_hal_start_executed",
        "scan_connect_executed",
        "credential_use_executed",
        "dhcp_route_executed",
        "external_ping_executed",
        "wifi_bringup_executed",
        "flash_executed",
        "partition_write_executed",
    )]
    return "\n".join([
        "# V1343 Provider-ready SDX50M Route Live",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        "",
        "## Route",
        "",
        markdown_table(["field", "value"], [[key, value] for key, value in route.items()]),
        "",
        "## Steps",
        "",
        markdown_table(["name", "ok", "rc", "duration_sec", "file", "decision"], step_rows),
        "",
        "## Safety",
        "",
        markdown_table(["field", "value"], safety_rows),
        "",
    ])


def render_report(manifest: dict[str, Any]) -> str:
    route_step = (manifest.get("analysis") or {}).get("v1221_route_step") or {}
    route = (manifest.get("analysis") or {}).get("v1221_route") or {}
    route_manifest = route_step.get("manifest", "tmp/wifi/v1343-v1221-sdx50m-route/manifest.json")
    route_rows = [[key, route.get(key)] for key in (
        "decision",
        "sdx50m_registered",
        "per_mgr_esoc0_any",
        "wlfw_or_wlan_dmesg_seen",
        "wlan0_up",
        "wifi_hal_start_executed",
        "scan_connect_executed",
        "credential_use_executed",
        "dhcp_route_executed",
        "external_ping_executed",
    )]
    return "\n".join([
        "# Native Init V1343 Provider-ready SDX50M Route Live",
        "",
        "## Summary",
        "",
        "- Cycle: `V1343`",
        "- Type: bounded provider-ready SDX50M route live gate",
        f"- Decision: `{manifest['decision']}`",
        f"- Result: {'PASS' if manifest['pass'] else 'FAIL'}",
        "- Evidence:",
        "  - `tmp/wifi/v1343-provider-ready-sdx50m-route-live/manifest.json`",
        "  - `tmp/wifi/v1343-provider-ready-sdx50m-route-live/summary.md`",
        f"  - `{route_manifest}`",
        "- Script: `scripts/revalidation/native_wifi_provider_ready_sdx50m_route_live_v1343.py`",
        "",
        "## Execution Scope",
        "",
        f"- Current command executed device actions: `{manifest['current_command_device_commands_executed']}`",
        f"- Recovered from live evidence: `{manifest['recovered_from_live_evidence']}`",
        f"- Live evidence includes PM actor execution: `{manifest['pm_actor_executed']}`",
        f"- Live evidence includes private CNSS start: `{manifest['cnss_daemon_start_executed']}`",
        "",
        "## Key Observations",
        "",
        markdown_table(["field", "value"], route_rows),
        "",
        "## Decision",
        "",
        manifest["reason"],
        "",
        "V1343 intentionally stops before Wi-Fi HAL, scan/connect, credentials,",
        "DHCP/routes, or external ping. If the lower route reaches eSoC without",
        "`wlan0`, the next unit remains lower-path classification, not active Wi-Fi",
        "connection.",
        "",
        "## Next",
        "",
        manifest["next_step"],
        "",
    ])


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    local = local_helper_info(args)
    steps: list[dict[str, Any]] = []
    analysis: dict[str, Any] = {}
    if args.command == "run" and not required_flags(args):
        v490 = run_v490(args, store)
        steps.append(v490)
        analysis["v490_policy_load"] = v490
        route_step = run_v1221_route(args, store)
        steps.append(route_step)
        analysis["v1221_route_step"] = route_step
        route_manifest = read_json(args.v1221_out_dir / "manifest.json")
        if not route_manifest and route_step.get("manifest"):
            route_manifest = read_json(Path(str(route_step["manifest"])))
        analysis["v1221_route_manifest"] = route_manifest
        analysis["v1221_route"] = extract_v1221(route_manifest)
    elif args.command == "recover":
        v490_manifest = read_json(args.v490_out_dir / "manifest.json")
        v490 = {
            "name": "v490-policy-load-recovered",
            "rc": 0 if v490_manifest else 1,
            "ok": v490_manifest.get("decision") == "v490-selinux-policy-load-proof-pass",
            "duration_sec": 0.0,
            "file": "",
            "manifest": str(args.v490_out_dir / "manifest.json"),
            "decision": v490_manifest.get("decision", ""),
            "pass": v490_manifest.get("pass"),
            "policy_load_executed": v490_manifest.get("policy_load_executed"),
            "wifi_bringup_executed": v490_manifest.get("wifi_bringup_executed"),
        }
        steps.append(v490)
        analysis["v490_policy_load"] = v490
        route_step = recover_v1221_route(args)
        steps.append(route_step)
        analysis["v1221_route_step"] = route_step
        route_manifest = read_json(Path(str(route_step["manifest"])))
        analysis["v1221_route_manifest"] = route_manifest
        analysis["v1221_route"] = extract_v1221(route_manifest)
    decision, passed, reason, next_step = decide(args, local, steps, analysis)
    route = analysis.get("v1221_route") or {}
    live_executed = args.command == "run" and not required_flags(args)
    recovered_live_evidence = args.command == "recover" and bool(route)
    evidence_device_actions = live_executed or recovered_live_evidence
    evidence_route_actions = bool(route) and (live_executed or recovered_live_evidence)
    return {
        "cycle": "v1343",
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": passed,
        "reason": reason,
        "next_step": next_step,
        "out_dir": str(store.run_dir),
        "host": collect_host_metadata(),
        "helper_marker": args.helper_marker,
        "helper_sha256": args.helper_sha256,
        "local_helper": local,
        "private_cnss_daemon": args.private_cnss_daemon,
        "private_cnss_sha256": args.private_cnss_sha256,
        "steps": steps,
        "analysis": analysis,
        "recovered_from_live_evidence": args.command == "recover",
        "current_command_device_commands_executed": live_executed,
        "current_command_device_mutations": live_executed,
        "device_commands_executed": evidence_device_actions,
        "device_mutations": evidence_device_actions,
        "policy_load_executed": bool((analysis.get("v490_policy_load") or {}).get("policy_load_executed")),
        "pm_actor_executed": evidence_route_actions,
        "cnss_daemon_start_executed": evidence_route_actions,
        "tracefs_write_executed": evidence_route_actions,
        "live_esoc_ioctl_executed": False,
        "live_esoc_notify_executed": False,
        "manual_esoc_open_executed": False,
        "pmic_write_executed": False,
        "gpio_line_request_executed": False,
        "direct_esoc_ioctl_executed": False,
        "gdsc_write_executed": False,
        "wifi_hal_start_executed": bool(route.get("wifi_hal_start_executed")),
        "scan_connect_executed": bool(route.get("scan_connect_executed")),
        "credential_use_executed": bool(route.get("credential_use_executed")),
        "dhcp_route_executed": bool(route.get("dhcp_route_executed")),
        "external_ping_executed": bool(route.get("external_ping_executed")),
        "wifi_bringup_executed": bool(route.get("wifi_bringup_executed")),
        "flash_executed": False,
        "partition_write_executed": False,
    }


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args, store)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    if args.command in ("run", "recover"):
        write_private_text(repo_path(REPORT_PATH), render_report(manifest))
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"policy_load_executed: {manifest['policy_load_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"manifest: {store.run_dir / 'manifest.json'}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

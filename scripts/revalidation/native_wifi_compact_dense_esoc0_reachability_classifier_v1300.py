#!/usr/bin/env python3
"""V1300 host-only classifier for V1295/V1299 eSoC reachability evidence."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1300-compact-dense-esoc0-reachability-classifier")
DEFAULT_V1295 = Path("tmp/wifi/v1295-dense-response-sampler-live")
DEFAULT_V1299 = Path("tmp/wifi/v1299-compact-dense-response-sampler-live")
LATEST_POINTER = Path("tmp/wifi/latest-v1300-compact-dense-esoc0-reachability-classifier.txt")

KEY_RE = re.compile(r"^([A-Za-z0-9_.-]+)=(.*)$")
POLL_RE = re.compile(r"response_sample\.(late_per_proxy_poll_\d+)\.begin=1")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v1295-dir", type=Path, default=DEFAULT_V1295)
    parser.add_argument("--v1299-dir", type=Path, default=DEFAULT_V1299)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def load_manifest(run_dir: Path) -> dict[str, Any]:
    path = repo_path(run_dir) / "manifest.json"
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def load_transcript(run_dir: Path) -> str:
    path = repo_path(run_dir) / "host" / "pm-server-wchan-tracefs-observer.txt"
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def parse_key_values(text: str) -> dict[str, str]:
    keys: dict[str, str] = {}
    for raw_line in text.replace("\0", "\n").splitlines():
        match = KEY_RE.match(raw_line.strip())
        if match:
            keys[match.group(1)] = match.group(2).strip()
    return keys


def int_value(value: Any, fallback: int = 0) -> int:
    try:
        return int(str(value), 0)
    except (TypeError, ValueError):
        return fallback


def analyze_run(label: str, run_dir: Path) -> dict[str, Any]:
    manifest = load_manifest(run_dir)
    text = load_transcript(run_dir)
    keys = parse_key_values(text)
    phases = sorted(set(POLL_RE.findall(text)))
    fd_esoc_counts = [
        int_value(value, -1)
        for key, value in keys.items()
        if key.endswith(".per_mgr_subsys_esoc0_count")
    ]
    return {
        "label": label,
        "dir": str(repo_path(run_dir)),
        "manifest_exists": bool(manifest),
        "transcript_exists": bool(text),
        "decision": manifest.get("decision", ""),
        "pass": bool(manifest.get("pass")),
        "manifest_pm_esoc0_attempt": bool((manifest.get("pm_service_trigger_observer") or {}).get("pm_service_actor_esoc0_attempt")),
        "manifest_sample_count": int_value((manifest.get("response_sampler") or {}).get("sample_count"), 0),
        "manifest_sampler_ended": bool((manifest.get("response_sampler") or {}).get("ended")),
        "manifest_sampler_mode": (manifest.get("response_sampler") or {}).get("mode", ""),
        "sample_phase_count": len(phases),
        "stdout_truncated": "A90_EXECNS_STDOUT_END truncated=1" in text,
        "stdout_not_truncated": "A90_EXECNS_STDOUT_END truncated=0" in text,
        "stdout_bytes": max([int_value(item, -1) for item in re.findall(r"A90_EXECNS_STDOUT_END truncated=[01] bytes=(\d+)", text)] or [-1]),
        "execns_end_rc0": "A90_EXECNS_END rc=0" in text,
        "syscall_probe_late_count": len(re.findall(r"syscall_probe\.late_per_proxy_poll_\d+\.begin=1", text)),
        "syscall_path_esoc0_count": text.count("path.value=/dev/subsys_esoc0"),
        "syscall_wchan_powerup_count": text.count("wchan=mdm_subsys_powerup"),
        "thread_sample_powerup_count": len(re.findall(r"thread_sample .*wchan=mdm_subsys_powerup", text)),
        "kmsg_esoc0_count": text.count("__subsystem_get(): __subsystem_get: esoc0"),
        "kmsg_changing_esoc0_count": text.count("Changing subsys fw_name to esoc0"),
        "compact_fd_snapshot_count": text.count("compact_fd_snapshot.begin=1"),
        "verbose_fd_snapshot_count": text.count(".fd_snapshot.begin=1"),
        "per_mgr_subsys_esoc0_count_max": max(fd_esoc_counts or [-1]),
        "per_mgr_subsys_esoc0_count_positive": any(count > 0 for count in fd_esoc_counts),
        "has_powerup_or_esoc0_path": (
            "path.value=/dev/subsys_esoc0" in text or
            "wchan=mdm_subsys_powerup" in text or
            "__subsystem_get(): __subsystem_get: esoc0" in text
        ),
    }


def decide(command: str, v1295: dict[str, Any], v1299: dict[str, Any]) -> tuple[str, bool, str, str]:
    if command == "plan":
        return (
            "v1300-compact-dense-esoc0-reachability-plan-ready",
            True,
            "plan-only; no device command executed",
            "run V1300 host-only classifier",
        )
    if not v1295["manifest_exists"] or not v1299["manifest_exists"]:
        return (
            "v1300-input-missing",
            False,
            "required V1295 or V1299 manifest is missing",
            "rerun or restore the missing evidence before classification",
        )
    if not v1299["manifest_sampler_ended"] or v1299["manifest_sample_count"] < 42:
        return (
            "v1300-v1299-compact-window-not-proven",
            False,
            "V1299 did not prove full compact dense window",
            "fix V1299 before comparing eSoC reachability",
        )
    if v1299["has_powerup_or_esoc0_path"] and not v1299["manifest_pm_esoc0_attempt"]:
        return (
            "v1300-v1299-esoc0-reached-manifest-false-negative",
            True,
            "V1299 reached /dev/subsys_esoc0/mdm_subsys_powerup, but manifest classification missed it because compact dense loop removed repeated syscall/kmsg probes and blocked opens do not create fds",
            "V1301 should add a compact powerup-thread/path marker to the live sampler before another response run",
        )
    if v1299["has_powerup_or_esoc0_path"]:
        return (
            "v1300-v1299-esoc0-reached",
            True,
            "V1299 reached /dev/subsys_esoc0/mdm_subsys_powerup; continue SDX50M no-response classification",
            "V1301 should classify GPIO142/PCIe/MHI absence with compact powerup markers",
        )
    return (
        "v1300-v1299-esoc0-not-reached",
        True,
        "V1299 full compact window did not contain /dev/subsys_esoc0/mdm_subsys_powerup evidence",
        "classify late per_proxy to PM-service request delivery before rerunning live",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    rows = []
    for run in (manifest["analysis"]["v1295"], manifest["analysis"]["v1299"]):
        rows.append([
            run["label"],
            run["decision"],
            run["manifest_sample_count"],
            run["manifest_sampler_ended"],
            run["stdout_truncated"],
            run["stdout_bytes"],
            run["manifest_pm_esoc0_attempt"],
            run["syscall_path_esoc0_count"],
            run["syscall_wchan_powerup_count"],
            run["kmsg_esoc0_count"],
            run["per_mgr_subsys_esoc0_count_max"],
        ])
    return "\n".join([
        "# V1300 Compact Dense eSoC Reachability Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        "",
        "## Comparison",
        "",
        markdown_table(
            [
                "run",
                "decision",
                "samples",
                "ended",
                "truncated",
                "stdout_bytes",
                "manifest_esoc0",
                "path_esoc0",
                "wchan_powerup",
                "kmsg_esoc0",
                "fd_esoc0_max",
            ],
            rows,
        ),
        "",
        "## Safety",
        "",
        "- host-only classifier; no bridge/device command",
        "- no PM/CNSS actor start, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, PMIC write, GPIO request/hold, direct eSoC ioctl, flash, boot image write, or partition write",
        "",
    ])


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    v1295 = analyze_run("v1295", args.v1295_dir)
    v1299 = analyze_run("v1299", args.v1299_dir)
    decision, passed, reason, next_step = decide(args.command, v1295, v1299)
    manifest = {
        "cycle": "v1300",
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": passed,
        "reason": reason,
        "next_step": next_step,
        "out_dir": str(store.run_dir),
        "host": collect_host_metadata(),
        "inputs": {
            "v1295_dir": str(repo_path(args.v1295_dir)),
            "v1299_dir": str(repo_path(args.v1299_dir)),
        },
        "analysis": {
            "v1295": v1295,
            "v1299": v1299,
        },
        "device_commands_executed": False,
        "live_actor_started": False,
        "pmic_write_executed": False,
        "gpio_line_request_executed": False,
        "direct_esoc_ioctl_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "wifi_bringup_executed": False,
        "flash_or_partition_write_executed": False,
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"manifest: {store.run_dir / 'manifest.json'}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

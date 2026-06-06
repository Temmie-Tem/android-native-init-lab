#!/usr/bin/env python3
"""V1164 host-only PM proxy/Binder delta classifier.

This classifier consumes already captured Android V1159 and native V1163
evidence. It does not contact the device, start daemons, start Wi-Fi HAL,
scan/connect, use credentials, run DHCP/routes, ping externally, write
partitions, flash, or reboot.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1164-pm-proxy-binder-delta-classifier")
LATEST_POINTER = Path("tmp/wifi/latest-v1164-pm-proxy-binder-delta-classifier.txt")
DEFAULT_V1159_ROOT = Path("tmp/wifi/v1159-pm-thread-sampler-live-20260527-191019")
DEFAULT_V1163_MANIFEST = Path("tmp/wifi/v1163-late-per-proxy-esoc-live-after-v490/manifest.json")
DEFAULT_V1163_SUMMARY = Path("tmp/wifi/v1163-late-per-proxy-esoc-live-after-v490/summary.md")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v1159-root", type=Path, default=DEFAULT_V1159_ROOT)
    parser.add_argument("--v1163-manifest", type=Path, default=DEFAULT_V1163_MANIFEST)
    parser.add_argument("--v1163-summary", type=Path, default=DEFAULT_V1163_SUMMARY)
    return parser.parse_args()


def read_text(path: Path, limit: int = 12_000_000) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    return resolved.read_bytes()[:limit].replace(b"\0", b"\\0").decode("utf-8", errors="replace")


def load_json(path: Path) -> dict[str, Any]:
    text = read_text(path)
    if not text:
        return {}
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def boolish(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    return str(value).strip().lower() in {"1", "true", "yes", "ok", "pass"}


def intish(value: Any, default: int = 0) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    try:
        return int(str(value).strip(), 0)
    except (TypeError, ValueError):
        return default


def count_lines(text: str, *needles: str) -> int:
    return sum(1 for line in text.splitlines() if all(needle in line for needle in needles))


def first_line(text: str, *needles: str) -> str:
    for line in text.splitlines():
        if all(needle in line for needle in needles):
            return line.strip()
    return ""


def dmesg_time(text: str, pattern: str) -> float | None:
    regex = re.compile(r"\[\s*(?P<time>\d+\.\d+)\].*" + pattern)
    for line in text.splitlines():
        match = regex.search(line)
        if match:
            return float(match.group("time"))
    return None


def read_snapshot_bundle(root: Path, filename: str) -> str:
    chunks: list[str] = []
    snapshot_root = repo_path(root)
    for path in sorted(snapshot_root.glob(f"pm_thread_snapshots/pm-service_*_*/{filename}")):
        chunks.append(f"--- {path.parent.name}/{filename} ---\n{read_text(path)}")
    return "\n".join(chunks)


def summarize_android(v1159_root: Path) -> dict[str, Any]:
    root = repo_path(v1159_root)
    manifest = load_json(root / "manifest.json")
    extracted = root / "android-trace" / "extracted" / "a90-wifi"
    dmesg = read_text(extracted / "boot_dmesg.txt")
    interesting = read_text(extracted / "pm_thread_interesting.txt")
    stack = read_snapshot_bundle(extracted, "stack.txt")
    fd = read_snapshot_bundle(extracted, "fd.txt")
    status = read_snapshot_bundle(extracted, "status.txt")

    trace = (manifest.get("context") or {}).get("trace_classification") or {}
    if not isinstance(trace, dict):
        trace = {}

    times = {
        "per_proxy_helper_start": dmesg_time(dmesg, r"starting service 'vendor\.per_proxy_helper'"),
        "per_proxy_start": dmesg_time(dmesg, r"starting service 'vendor\.per_proxy'"),
        "pm_service_modem_get": dmesg_time(dmesg, r"Binder:\d+_2:.*__subsystem_get: modem count:1"),
        "mdm_helper_start": dmesg_time(dmesg, r"starting service 'vendor\.mdm_helper'"),
        "cnss_daemon_start": dmesg_time(dmesg, r"starting service 'cnss-daemon'"),
        "pm_service_esoc0_get": dmesg_time(dmesg, r"Binder:\d+_2:.*__subsystem_get: esoc0 count:0"),
        "icnss_qmi_connected": dmesg_time(dmesg, r"icnss_qmi: QMI Server Connected"),
        "bdf_regdb": dmesg_time(dmesg, r"BDF file : regdb\.bin"),
        "bdf_bdwlan": dmesg_time(dmesg, r"BDF file : bdwlan\.bin"),
        "fw_ready": dmesg_time(dmesg, r"FW ready event received"),
        "wlan0": dmesg_time(dmesg, r"dev : wlan0 : event : 16"),
    }

    return {
        "decision": manifest.get("decision", ""),
        "pass": boolish(manifest.get("pass")),
        "trace_present": boolish(trace.get("present")),
        "dmesg_fw_ready": boolish(trace.get("dmesg_fw_ready")),
        "dmesg_wlan0_created": boolish(trace.get("dmesg_wlan0_created")),
        "pm_thread_sample_count": intish(trace.get("pm_thread_sample_count")),
        "pm_service_powerup_samples": count_lines(interesting, "label=pm-service", "wchan=mdm_subsys_powerup"),
        "pm_service_binder_openat_samples": count_lines(interesting, "label=pm-service", "comm=Binder:", "syscall=56"),
        "pm_service_powerup_first_line": first_line(interesting, "label=pm-service", "wchan=mdm_subsys_powerup"),
        "pm_service_stack_has_mdm_subsys_powerup": "mdm_subsys_powerup" in stack,
        "pm_service_stack_has_subsystem_get": "__subsystem_get" in stack,
        "pm_service_status_d_state": "State:\tD" in status,
        "pm_service_fd_has_subsys_modem": "/dev/subsys_modem" in fd,
        "pm_service_fd_has_subsys_esoc0": "/dev/subsys_esoc0" in fd,
        "dmesg_per_proxy_start": times["per_proxy_start"] is not None,
        "dmesg_pm_service_modem_get": times["pm_service_modem_get"] is not None,
        "dmesg_pm_service_esoc0_get": times["pm_service_esoc0_get"] is not None,
        "dmesg_icnss_qmi_connected": times["icnss_qmi_connected"] is not None,
        "dmesg_bdf_downloads": times["bdf_regdb"] is not None and times["bdf_bdwlan"] is not None,
        "times": times,
    }


def tracefs(manifest: dict[str, Any]) -> dict[str, Any]:
    value = (manifest.get("analysis") or {}).get("tracefs_uprobe") or {}
    return value if isinstance(value, dict) else {}


def summarize_native(v1163_manifest: Path, v1163_summary: Path) -> dict[str, Any]:
    manifest = load_json(v1163_manifest)
    summary = read_text(v1163_summary)
    tfs = tracefs(manifest)
    late = tfs.get("late_per_proxy") or {}
    polls = tfs.get("late_per_proxy_polls") or {}
    pm_hits = tfs.get("pm_server_hits_by_comm") or {}
    returns = tfs.get("return_values_by_comm") or {}
    client_args = tfs.get("client_register_args_by_comm") or {}
    markers = re.search(r"marker_counts \| (?P<value>.+?) \|", summary)

    poll_indices = sorted({
        match.group(1)
        for key in polls
        for match in [re.search(r"late_per_proxy_poll_(\d+)", str(key))]
        if match
    }) if isinstance(polls, dict) else []

    per_mgr_esoc_counts = [
        intish(polls.get(f"late_per_proxy_poll_{index}.per_mgr_subsys_esoc0_count"))
        for index in poll_indices
    ] if isinstance(polls, dict) else []
    per_mgr_modem_counts = [
        intish(polls.get(f"late_per_proxy_poll_{index}.per_mgr_subsys_modem_count"))
        for index in poll_indices
    ] if isinstance(polls, dict) else []
    per_mgr_vndbinder_counts = [
        intish(polls.get(f"late_per_proxy_poll_{index}.per_mgr_vndbinder_count"))
        for index in poll_indices
    ] if isinstance(polls, dict) else []
    pm_proxy_helper_modem_counts = [
        intish(polls.get(f"late_per_proxy_poll_{index}.pm_proxy_helper_subsys_modem_count"))
        for index in poll_indices
    ] if isinstance(polls, dict) else []

    pm_proxy_returns = returns.get("pm-proxy") if isinstance(returns, dict) else {}
    cnss_returns = returns.get("cnss-daemon") if isinstance(returns, dict) else {}
    binder_hits = pm_hits.get("Binder:2510_2") if isinstance(pm_hits, dict) else {}

    return {
        "decision": manifest.get("decision", ""),
        "pass": boolish(manifest.get("pass")),
        "late_per_proxy_started": boolish(manifest.get("late_per_proxy_started")),
        "firmware_mounts_executed": boolish(manifest.get("firmware_mounts_executed")),
        "global_modem_holder_opened": boolish(manifest.get("global_modem_holder_opened")),
        "post_pm_mdm_helper_executed": boolish(manifest.get("post_pm_mdm_helper_executed")),
        "post_pm_mdm_helper_lower_trace_emitted": boolish(manifest.get("post_pm_mdm_helper_lower_trace_emitted")),
        "wifi_hal_start_executed": boolish(manifest.get("wifi_hal_start_executed")),
        "scan_connect_executed": boolish(manifest.get("scan_connect_executed")),
        "credential_use_executed": boolish(manifest.get("credential_use_executed")),
        "dhcp_route_executed": boolish(manifest.get("dhcp_route_executed")),
        "external_ping_executed": boolish(manifest.get("external_ping_executed")),
        "late_gate_positive": boolish(late.get("gate_positive") if isinstance(late, dict) else False),
        "late_gate_mdm_helper_esoc0_fd_count": intish(
            late.get("gate_mdm_helper_esoc0_fd_count") if isinstance(late, dict) else 0
        ),
        "late_poll_count": len(poll_indices),
        "per_mgr_subsys_modem_counts": per_mgr_modem_counts,
        "per_mgr_subsys_esoc0_counts": per_mgr_esoc_counts,
        "per_mgr_vndbinder_counts": per_mgr_vndbinder_counts,
        "pm_proxy_helper_subsys_modem_counts": pm_proxy_helper_modem_counts,
        "pm_proxy_client_register_ret": pm_proxy_returns.get("pm_client_register_ret", []) if isinstance(pm_proxy_returns, dict) else [],
        "pm_proxy_client_connect_ret": pm_proxy_returns.get("pm_client_connect_ret", []) if isinstance(pm_proxy_returns, dict) else [],
        "cnss_client_register_ret": cnss_returns.get("pm_client_register_ret", []) if isinstance(cnss_returns, dict) else [],
        "cnss_client_connect_ret": cnss_returns.get("pm_client_connect_ret", []) if isinstance(cnss_returns, dict) else [],
        "pm_proxy_client_args": client_args.get("pm-proxy", []) if isinstance(client_args, dict) else [],
        "cnss_client_args": client_args.get("cnss-daemon", []) if isinstance(client_args, dict) else [],
        "binder_server_connect_entry": intish(binder_hits.get("pm_server_connect_entry") if isinstance(binder_hits, dict) else 0),
        "binder_server_connect_start_vote": intish(
            binder_hits.get("pm_server_connect_impl_start_vote") if isinstance(binder_hits, dict) else 0
        ),
        "binder_server_connect_ret": intish(binder_hits.get("pm_server_connect_ret") if isinstance(binder_hits, dict) else 0),
        "marker_counts_text": markers.group("value") if markers else "",
        "summary_has_binder_idle": "binder_ioctl_write_read" in summary,
        "summary_has_no_subsys_esoc0": "per_mgr_subsys_esoc0_count` | `0` in every late poll" in summary
        or "per_mgr_subsys_esoc0_count': '0'" in summary,
    }


def decide(android: dict[str, Any], native: dict[str, Any]) -> tuple[str, bool, str, str]:
    forbidden = any(
        native.get(key)
        for key in (
            "wifi_hal_start_executed",
            "scan_connect_executed",
            "credential_use_executed",
            "dhcp_route_executed",
            "external_ping_executed",
        )
    )
    android_good = (
        android["dmesg_per_proxy_start"]
        and android["dmesg_pm_service_esoc0_get"]
        and android["pm_service_powerup_samples"] > 0
        and android["dmesg_fw_ready"]
        and android["dmesg_wlan0_created"]
    )
    native_gate = (
        native["late_per_proxy_started"]
        and native["late_gate_positive"]
        and native["late_poll_count"] >= 6
        and all(value > 0 for value in native["per_mgr_subsys_modem_counts"])
        and all(value == 0 for value in native["per_mgr_subsys_esoc0_counts"])
        and native["binder_server_connect_start_vote"] > 0
        and "0x0" in native["pm_proxy_client_connect_ret"]
    )
    if forbidden:
        return (
            "v1164-forbidden-action-detected",
            False,
            "native V1163 evidence shows a forbidden HAL/credential/network action",
            "discard this evidence and rerun bounded host-only classifier on clean inputs",
        )
    if not android_good:
        return (
            "v1164-android-reference-insufficient",
            False,
            f"android={android}",
            "refresh Android PM sampler evidence before native delta classification",
        )
    if not native_gate:
        return (
            "v1164-native-reference-insufficient",
            False,
            f"native={native}",
            "rerun V1163 after current-boot V401/V490 prerequisites",
        )
    return (
        "v1164-pm-proxy-binder-actionability-gap",
        True,
        "Android pm-service Binder thread enters mdm_subsys_powerup/esoc0 after per_proxy, while native late pm-proxy reaches PM client/server connect and start_vote but leaves pm-service Binder threads idle and never opens /dev/subsys_esoc0",
        "V1165 should instrument late pm-proxy stdout/stderr/exit plus PM server connect state/action arguments over a longer bounded post-connect window",
    )


def summary_markdown(manifest: dict[str, Any]) -> str:
    android = manifest["android_v1159"]
    native = manifest["native_v1163"]
    return "\n".join([
        "# V1164 PM proxy Binder Delta Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        "",
        "## Android V1159 Reference",
        "",
        markdown_table(["key", "value"], [
            ["per_proxy_start", android["times"]["per_proxy_start"]],
            ["pm_service_modem_get", android["times"]["pm_service_modem_get"]],
            ["pm_service_esoc0_get", android["times"]["pm_service_esoc0_get"]],
            ["icnss_qmi_connected", android["times"]["icnss_qmi_connected"]],
            ["fw_ready", android["times"]["fw_ready"]],
            ["wlan0", android["times"]["wlan0"]],
            ["pm_service_powerup_samples", android["pm_service_powerup_samples"]],
            ["pm_service_binder_openat_samples", android["pm_service_binder_openat_samples"]],
        ]),
        "",
        "## Native V1163 after V490",
        "",
        markdown_table(["key", "value"], [
            ["late_per_proxy_started", native["late_per_proxy_started"]],
            ["late_gate_positive", native["late_gate_positive"]],
            ["late_poll_count", native["late_poll_count"]],
            ["per_mgr_subsys_modem_counts", native["per_mgr_subsys_modem_counts"]],
            ["per_mgr_subsys_esoc0_counts", native["per_mgr_subsys_esoc0_counts"]],
            ["pm_proxy_client_args", native["pm_proxy_client_args"]],
            ["pm_proxy_client_register_ret", native["pm_proxy_client_register_ret"]],
            ["pm_proxy_client_connect_ret", native["pm_proxy_client_connect_ret"]],
            ["binder_server_connect_start_vote", native["binder_server_connect_start_vote"]],
            ["summary_has_binder_idle", native["summary_has_binder_idle"]],
        ]),
        "",
        "## Safety",
        "",
        "- Host-only classifier; no device command was executed.",
        "- Wi-Fi HAL, scan/connect, credential use, DHCP, route, external ping, partition write, boot image write, flash, and reboot are out of scope.",
        "",
    ]) + "\n"


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    android = summarize_android(args.v1159_root)
    native = summarize_native(args.v1163_manifest, args.v1163_summary)
    decision, passed, reason, next_step = decide(android, native)
    manifest = {
        "generated_at": now_iso(),
        "cycle": "v1164",
        "decision": decision,
        "pass": passed,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "inputs": {
            "v1159_root": str(args.v1159_root),
            "v1163_manifest": str(args.v1163_manifest),
            "v1163_summary": str(args.v1163_summary),
        },
        "android_v1159": android,
        "native_v1163": native,
        "device_command_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "partition_write_executed": False,
        "boot_image_write_executed": False,
        "flash_executed": False,
        "reboot_executed": False,
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", summary_markdown(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir.relative_to(repo_path("."))) + "\n")
    print(f"decision: {decision}")
    print(f"pass: {passed}")
    print(f"reason: {reason}")
    print(f"next_step: {next_step}")
    print(f"evidence: {store.run_dir / 'manifest.json'}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())

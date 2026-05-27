#!/usr/bin/env python3
"""V1160 host-only classifier for the PM-service eSoC trigger gap.

This script consumes already-captured Android/native evidence.  It does not
contact the device and does not execute PM actors, mdm_helper, Wi-Fi HAL,
scan/connect, DHCP, routes, credentials, external ping, or any flash action.
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


DEFAULT_OUT_DIR = Path("tmp/wifi/v1160-pm-esoc-trigger-reconcile")
LATEST_POINTER = Path("tmp/wifi/latest-v1160-pm-esoc-trigger-reconcile.txt")
DEFAULT_V1159_ROOT = Path("tmp/wifi/v1159-pm-thread-sampler-live-20260527-191019")
DEFAULT_V1139 = Path("tmp/wifi/v1139-post-pm-mdm-helper-esoc-live-r2/manifest.json")
DEFAULT_V1099 = Path("tmp/wifi/v1099-pm-server-transaction-code-tracefs-live/manifest.json")
DEFAULT_V1107_REPORT = Path("docs/reports/NATIVE_INIT_V1107_PM_SERVER_MUTEX_OWNER_CLASSIFIER_2026-05-27.md")
DEFAULT_V1108_REPORT = Path("docs/reports/NATIVE_INIT_V1108_PM_ORDERING_NO_PRE_CNSS_PER_PROXY_2026-05-27.md")
DEFAULT_V1159_REPORT = Path("docs/reports/NATIVE_INIT_V1159_ANDROID_PM_THREAD_SAMPLER_CAPTURE_2026-05-27.md")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v1159-root", type=Path, default=DEFAULT_V1159_ROOT)
    parser.add_argument("--v1139", type=Path, default=DEFAULT_V1139)
    parser.add_argument("--v1099", type=Path, default=DEFAULT_V1099)
    parser.add_argument("--v1107-report", type=Path, default=DEFAULT_V1107_REPORT)
    parser.add_argument("--v1108-report", type=Path, default=DEFAULT_V1108_REPORT)
    parser.add_argument("--v1159-report", type=Path, default=DEFAULT_V1159_REPORT)
    return parser.parse_args()


def read_text(path: Path, limit: int = 8_000_000) -> str:
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


def nested_get(data: dict[str, Any], path: tuple[str, ...], default: Any = None) -> Any:
    current: Any = data
    for item in path:
        if not isinstance(current, dict):
            return default
        current = current.get(item)
    return default if current is None else current


def boolish(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    return str(value).strip().lower() in {"1", "true", "yes", "ok", "pass", "running"}


def intish(value: Any, default: int = 0) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    try:
        return int(str(value).strip(), 0)
    except (TypeError, ValueError):
        return default


def dmesg_time(text: str, pattern: str) -> float | None:
    regex = re.compile(r"\[\s*(?P<time>\d+\.\d+)\].*" + pattern)
    for line in text.splitlines():
        match = regex.search(line)
        if match:
            return float(match.group("time"))
    return None


def count_lines(text: str, *needles: str) -> int:
    return sum(1 for line in text.splitlines() if all(needle in line for needle in needles))


def parse_getprop(text: str, key: str) -> str:
    pattern = re.compile(rf"^\[{re.escape(key)}\]: \[(.*)\]$", re.MULTILINE)
    match = pattern.search(text)
    return match.group(1) if match else ""


def read_snapshot_files(root: Path, glob_pattern: str, filename: str) -> str:
    resolved = repo_path(root)
    chunks = []
    for directory in sorted(resolved.glob(glob_pattern)):
        candidate = directory / filename
        if candidate.exists():
            chunks.append(f"--- {directory.name}/{filename} ---\n{read_text(candidate)}")
    return "\n".join(chunks)


def summarize_android(v1159_root: Path) -> dict[str, Any]:
    root = repo_path(v1159_root)
    manifest = load_json(root / "manifest.json")
    extracted = root / "android-trace" / "extracted" / "a90-wifi"
    dmesg = read_text(extracted / "boot_dmesg.txt")
    getprop = read_text(extracted / "getprop.txt")
    ps = read_text(extracted / "ps_azef.txt")
    interesting = read_text(extracted / "pm_thread_interesting.txt")
    samples = read_text(extracted / "pm_thread_samples.txt")
    stack = read_snapshot_files(extracted, "pm_thread_snapshots/pm-service_*_*", "stack.txt")
    status = read_snapshot_files(extracted, "pm_thread_snapshots/pm-service_*_*", "status.txt")
    fd = read_snapshot_files(extracted, "pm_thread_snapshots/pm-service_*_*", "fd.txt")
    trace_classification = nested_get(manifest, ("context", "trace_classification"), {})

    times = {
        "pm_proxy_helper_start": dmesg_time(dmesg, r"starting service 'vendor\.per_proxy_helper'"),
        "pm_proxy_helper_modem_get": dmesg_time(dmesg, r"pm_proxy_helper:.*__subsystem_get: modem count:0"),
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
        "pass": bool(manifest.get("pass")),
        "trace_present": boolish(trace_classification.get("present") if isinstance(trace_classification, dict) else False),
        "dmesg_fw_ready": boolish(trace_classification.get("dmesg_fw_ready") if isinstance(trace_classification, dict) else False),
        "dmesg_wlan0_created": boolish(
            trace_classification.get("dmesg_wlan0_created") if isinstance(trace_classification, dict) else False
        ),
        "pm_thread_sample_count": intish(
            trace_classification.get("pm_thread_sample_count") if isinstance(trace_classification, dict) else 0
        ),
        "pm_thread_interesting_count": intish(
            trace_classification.get("pm_thread_interesting_count") if isinstance(trace_classification, dict) else 0
        ),
        "pm_service_mdm_subsys_powerup_samples": count_lines(interesting, "label=pm-service", "wchan=mdm_subsys_powerup"),
        "pm_service_binder_openat_samples": count_lines(interesting, "label=pm-service", "comm=Binder:", "syscall=56"),
        "pm_proxy_helper_samples": count_lines(samples, "label=pm_proxy_helper"),
        "pm_proxy_process_present": "/vendor/bin/pm-proxy" in ps,
        "pm_proxy_service_state": parse_getprop(getprop, "init.svc.vendor.per_proxy"),
        "pm_proxy_helper_service_state": parse_getprop(getprop, "init.svc.vendor.per_proxy_helper"),
        "pm_service_process_present": "/vendor/bin/pm-service" in ps,
        "pm_service_stack_has_mdm_subsys_powerup": "mdm_subsys_powerup" in stack,
        "pm_service_stack_has_subsystem_get": "__subsystem_get" in stack,
        "pm_service_stack_has_openat": "SyS_openat" in stack or "do_sys_open" in stack,
        "pm_service_status_d_state": "State:\tD" in status,
        "pm_service_fd_has_subsys_modem": "/dev/subsys_modem" in fd,
        "pm_service_fd_has_subsys_esoc0": "/dev/subsys_esoc0" in fd,
        "dmesg_pm_proxy_helper_modem_get": times["pm_proxy_helper_modem_get"] is not None,
        "dmesg_per_proxy_start": times["per_proxy_start"] is not None,
        "dmesg_pm_service_esoc0_get": times["pm_service_esoc0_get"] is not None,
        "dmesg_icnss_qmi_connected": times["icnss_qmi_connected"] is not None,
        "dmesg_bdf_downloads": times["bdf_regdb"] is not None and times["bdf_bdwlan"] is not None,
        "times": times,
    }


def summarize_v1139(data: dict[str, Any]) -> dict[str, Any]:
    trace = nested_get(data, ("analysis", "tracefs_uprobe"), {})
    pm_contract = trace.get("pm_contract", {}) if isinstance(trace, dict) else {}
    post_pm = trace.get("post_pm_mdm_helper", {}) if isinstance(trace, dict) else {}
    queue = trace.get("mdm_helper_queue_timing", {}) if isinstance(trace, dict) else {}
    fw = nested_get(data, ("analysis", "global_firmware"), {})
    markers = nested_get(fw, ("markers", "counts"), {}) if isinstance(fw, dict) else {}
    services = fw.get("qrtr_services_after_observer", {}) if isinstance(fw, dict) else {}
    return {
        "decision": data.get("decision", ""),
        "pass": bool(data.get("pass")),
        "per_proxy_start_executed": pm_contract.get("per_proxy_start_executed", ""),
        "per_proxy_start_skipped": pm_contract.get("child.per_proxy.start_skipped", ""),
        "start_cnss_before_per_proxy": pm_contract.get("start_cnss_before_per_proxy", ""),
        "pm_proxy_helper_start_executed": pm_contract.get("pm_proxy_helper_start_executed", ""),
        "per_mgr_subsys_modem_seen": intish(pm_contract.get("per_mgr_subsys_modem_seen")),
        "pm_proxy_helper_subsys_modem_seen": intish(pm_contract.get("pm_proxy_helper_subsys_modem_seen")),
        "pm_proxy_count_window": intish(queue.get("post_pm_window.pm_proxy_count") if isinstance(queue, dict) else 0),
        "pm_proxy_helper_count_window": intish(queue.get("post_pm_window.pm_proxy_helper_count") if isinstance(queue, dict) else 0),
        "pm_service_count_window": intish(queue.get("post_pm_window.pm_service_count") if isinstance(queue, dict) else 0),
        "per_mgr_subsys_esoc0_count": intish(queue.get("post_pm_window.per_mgr_subsys_esoc0_count") if isinstance(queue, dict) else 0),
        "mdm_helper_esoc0_count": intish(post_pm.get("fd_esoc0_count.window") if isinstance(post_pm, dict) else 0),
        "mdm_helper_subsys_esoc0_count": intish(
            post_pm.get("fd_subsys_esoc0_count.window") if isinstance(post_pm, dict) else 0
        ),
        "mhi_pipe_count": intish(post_pm.get("fd_mhi_pipe_count.window") if isinstance(post_pm, dict) else 0),
        "ks_count": intish(post_pm.get("ks_count.window") if isinstance(post_pm, dict) else 0),
        "mdm3_after_observer": fw.get("mdm3_after_observer", "") if isinstance(fw, dict) else "",
        "qrtr_service69": intish(services.get("69") if isinstance(services, dict) else 0),
        "wlfw_count": intish(markers.get("wlfw") if isinstance(markers, dict) else 0),
        "wlan0_count": intish(markers.get("wlan0") if isinstance(markers, dict) else 0),
        "wifi_hal_start_executed": boolish(data.get("wifi_hal_start_executed")),
        "scan_connect_executed": boolish(data.get("scan_connect_executed")),
        "credential_use_executed": boolish(data.get("credential_use_executed")),
        "dhcp_route_executed": boolish(data.get("dhcp_route_executed")),
        "external_ping_executed": boolish(data.get("external_ping_executed")),
        "flash_executed": boolish(data.get("flash_executed")),
    }


def summarize_v1099(data: dict[str, Any]) -> dict[str, Any]:
    trace = nested_get(data, ("analysis", "tracefs_uprobe"), {})
    by_comm = trace.get("by_comm", {}) if isinstance(trace, dict) else {}
    transaction_counts = trace.get("transaction_code_counts", {}) if isinstance(trace, dict) else {}
    pm_proxy = by_comm.get("pm-proxy", {}) if isinstance(by_comm, dict) else {}
    return {
        "decision": data.get("decision", ""),
        "pass": bool(data.get("pass")),
        "pm_proxy_register": intish(pm_proxy.get("pm_client_register") if isinstance(pm_proxy, dict) else 0),
        "pm_proxy_connect": intish(pm_proxy.get("pm_client_connect") if isinstance(pm_proxy, dict) else 0),
        "pm_proxy_ack": intish(nested_get(by_comm, ("Binder:1487_1", "pm_client_ack"), 0) if isinstance(by_comm, dict) else 0),
        "cnss_register": intish(nested_get(by_comm, ("cnss-daemon", "pm_client_register"), 0) if isinstance(by_comm, dict) else 0),
        "transaction_0x1": intish(transaction_counts.get("0x1") if isinstance(transaction_counts, dict) else 0),
        "transaction_0x3": intish(transaction_counts.get("0x3") if isinstance(transaction_counts, dict) else 0),
        "transaction_0x5": intish(transaction_counts.get("0x5") if isinstance(transaction_counts, dict) else 0),
    }


def classify(analysis: dict[str, Any]) -> dict[str, Any]:
    android = analysis["android_v1159"]
    v1139 = analysis["native_v1139"]
    v1099 = analysis["native_v1099"]
    refs = analysis["references"]
    times = android["times"]
    per_proxy_before_esoc0 = (
        times["per_proxy_start"] is not None
        and times["pm_service_esoc0_get"] is not None
        and times["per_proxy_start"] < times["pm_service_esoc0_get"]
    )
    guardrails_clean = not any(
        bool(v1139[key])
        for key in (
            "wifi_hal_start_executed",
            "scan_connect_executed",
            "credential_use_executed",
            "dhcp_route_executed",
            "external_ping_executed",
            "flash_executed",
        )
    )
    flags = {
        "android_good_wifi_lower_chain": (
            android["pass"]
            and android["dmesg_fw_ready"]
            and android["dmesg_wlan0_created"]
            and android["dmesg_icnss_qmi_connected"]
            and android["dmesg_bdf_downloads"]
        ),
        "android_pm_service_esoc0_owner_captured": (
            android["dmesg_pm_service_esoc0_get"]
            and android["pm_service_mdm_subsys_powerup_samples"] > 0
            and android["pm_service_stack_has_mdm_subsys_powerup"]
            and android["pm_service_stack_has_subsystem_get"]
            and android["pm_service_stack_has_openat"]
        ),
        "android_per_proxy_action_precedes_esoc0": (
            android["pm_proxy_process_present"]
            and android["pm_proxy_service_state"] == "running"
            and android["dmesg_per_proxy_start"]
            and per_proxy_before_esoc0
        ),
        "native_pm_proxy_actionable_codes_known": (
            v1099["pass"]
            and v1099["pm_proxy_register"] > 0
            and v1099["pm_proxy_connect"] > 0
            and v1099["pm_proxy_ack"] > 0
            and v1099["transaction_0x3"] > 0
            and v1099["transaction_0x5"] > 0
        ),
        "pre_cnss_per_proxy_known_mutex_blocker": refs["v1107_pre_cnss_per_proxy_mutex_blocker"],
        "native_v1139_skipped_per_proxy_after_repair": (
            v1139["pass"]
            and v1139["per_proxy_start_executed"] == "0"
            and v1139["per_proxy_start_skipped"] == "1"
            and v1139["start_cnss_before_per_proxy"] == "1"
            and v1139["pm_proxy_count_window"] == 0
        ),
        "native_v1139_upper_pm_mdm_helper_positive": (
            v1139["per_mgr_subsys_modem_seen"] > 0
            and v1139["pm_proxy_helper_subsys_modem_seen"] > 0
            and v1139["pm_proxy_helper_count_window"] > 0
            and v1139["pm_service_count_window"] > 0
            and v1139["mdm_helper_esoc0_count"] > 0
        ),
        "native_v1139_missing_lower_esoc_publication": (
            v1139["per_mgr_subsys_esoc0_count"] == 0
            and v1139["mdm_helper_subsys_esoc0_count"] == 0
            and v1139["mhi_pipe_count"] == 0
            and v1139["ks_count"] == 0
            and v1139["qrtr_service69"] == 0
            and v1139["wlfw_count"] == 0
            and v1139["wlan0_count"] == 0
            and v1139["mdm3_after_observer"] == "OFFLINING"
        ),
        "guardrails_clean": guardrails_clean,
    }
    missing = [name for name, ok in flags.items() if not ok]
    if not missing:
        return {
            "decision": "v1160-late-per-proxy-esoc-trigger-route-classified",
            "pass": True,
            "reason": (
                "Android shows vendor.per_proxy starts before the pm-service Binder thread enters "
                "__subsystem_get(esoc0)/mdm_subsys_powerup, while native V1139 intentionally skips "
                "per_proxy and therefore misses the actionable eSoC trigger after upper PM/CNSS/mdm_helper readiness"
            ),
            "next_step": (
                "V1161 should add a bounded late-per_proxy gate: start provider + cnss-daemon + mdm_helper "
                "until /dev/esoc-0 is held, then start pm-proxy as the eSoC trigger and capture pm-service "
                "Binder wchan/syscall/stack, /dev/subsys_esoc0, MHI/ks, service69, and mdm3 state; keep "
                "Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, and boot-image writes disabled"
            ),
            "flags": flags,
            "missing": [],
        }
    return {
        "decision": "v1160-pm-esoc-trigger-input-incomplete",
        "pass": False,
        "reason": "missing=" + ",".join(missing),
        "next_step": "refresh the missing V1159/V1139/V1099/V1107 evidence before selecting the next live gate",
        "flags": flags,
        "missing": missing,
    }


def summarize_references(v1107_report: str, v1108_report: str, v1159_report: str) -> dict[str, Any]:
    return {
        "v1107_present": bool(v1107_report),
        "v1107_pre_cnss_per_proxy_mutex_blocker": (
            "pre-CNSS `per_proxy` connect" in v1107_report
            and ("holds the modem record mutex" in v1107_report or "hold the modem record mutex" in v1107_report)
            and "__subsystem_get" in v1107_report
        ),
        "v1108_present": bool(v1108_report),
        "v1108_no_pre_cnss_per_proxy_repair": (
            "per_proxy_start_executed=0" in v1108_report
            and "CNSS now reaches both PM register and PM connect" in v1108_report
        ),
        "v1159_present": bool(v1159_report),
        "v1159_pm_service_owner_reported": (
            "Android `pm-service`, not `mdm_helper`, owns the lower `esoc0` power-up wait" in v1159_report
        ),
    }


def render_summary(manifest: dict[str, Any]) -> str:
    android = manifest["analysis"]["android_v1159"]
    v1139 = manifest["analysis"]["native_v1139"]
    v1099 = manifest["analysis"]["native_v1099"]
    cls = manifest["analysis"]["classification"]
    rows = [
        ["Android lower chain", str(cls["flags"]["android_good_wifi_lower_chain"]), "FW-ready + wlan0"],
        [
            "Android PM-service owner",
            str(cls["flags"]["android_pm_service_esoc0_owner_captured"]),
            f"samples={android['pm_service_mdm_subsys_powerup_samples']}",
        ],
        [
            "Android per_proxy before eSoC",
            str(cls["flags"]["android_per_proxy_action_precedes_esoc0"]),
            f"per_proxy={android['times']['per_proxy_start']} esoc0={android['times']['pm_service_esoc0_get']}",
        ],
        [
            "PM proxy actionable codes",
            str(cls["flags"]["native_pm_proxy_actionable_codes_known"]),
            f"connect={v1099['pm_proxy_connect']} ack={v1099['pm_proxy_ack']} 0x3={v1099['transaction_0x3']} 0x5={v1099['transaction_0x5']}",
        ],
        [
            "pre-CNSS per_proxy blocker",
            str(cls["flags"]["pre_cnss_per_proxy_known_mutex_blocker"]),
            "V1107 mutex owner in subsystem_get",
        ],
        [
            "V1139 per_proxy skipped",
            str(cls["flags"]["native_v1139_skipped_per_proxy_after_repair"]),
            f"start={v1139['per_proxy_start_executed']} skipped={v1139['per_proxy_start_skipped']}",
        ],
        [
            "V1139 upper path positive",
            str(cls["flags"]["native_v1139_upper_pm_mdm_helper_positive"]),
            f"pm_helper={v1139['pm_proxy_helper_count_window']} pm_service={v1139['pm_service_count_window']} mdm_helper_esoc0={v1139['mdm_helper_esoc0_count']}",
        ],
        [
            "V1139 lower missing",
            str(cls["flags"]["native_v1139_missing_lower_esoc_publication"]),
            f"subsys_esoc0={v1139['mdm_helper_subsys_esoc0_count']} mhi={v1139['mhi_pipe_count']} ks={v1139['ks_count']} svc69={v1139['qrtr_service69']}",
        ],
        ["guardrails", str(cls["flags"]["guardrails_clean"]), "no HAL/scan/credential/DHCP/ping/flash"],
    ]
    times = [[key, str(value)] for key, value in android["times"].items()]
    return "\n".join(
        [
            "# V1160 PM eSoC Trigger Reconcile",
            "",
            f"- generated: `{manifest['generated_at']}`",
            f"- decision: `{manifest['decision']}`",
            f"- pass: `{manifest['pass']}`",
            f"- reason: {manifest['reason']}",
            f"- next_step: {manifest['next_step']}",
            "",
            "## Classification",
            "",
            markdown_table(["evidence", "ok", "detail"], rows),
            "",
            "## Android Timeline",
            "",
            markdown_table(["event", "dmesg_sec"], times),
            "",
            "## Safety",
            "",
            "- device commands executed: `false`",
            "- PM actors, mdm_helper, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping: `false`",
            "- boot image/partition writes/flash: `false`",
            "",
            "## Missing",
            "",
            json.dumps(cls["missing"], indent=2, sort_keys=True),
            "",
        ]
    )


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    analysis = {
        "android_v1159": summarize_android(args.v1159_root),
        "native_v1139": summarize_v1139(load_json(args.v1139)),
        "native_v1099": summarize_v1099(load_json(args.v1099)),
        "references": summarize_references(
            read_text(args.v1107_report),
            read_text(args.v1108_report),
            read_text(args.v1159_report),
        ),
    }
    classification = classify(analysis)
    analysis["classification"] = classification
    manifest = {
        "cycle": "v1160",
        "generated_at": now_iso(),
        "host": collect_host_metadata(),
        "inputs": {
            "v1159_root": str(repo_path(args.v1159_root)),
            "v1139": str(repo_path(args.v1139)),
            "v1099": str(repo_path(args.v1099)),
            "v1107_report": str(repo_path(args.v1107_report)),
            "v1108_report": str(repo_path(args.v1108_report)),
            "v1159_report": str(repo_path(args.v1159_report)),
        },
        "analysis": analysis,
        "decision": classification["decision"],
        "pass": classification["pass"],
        "reason": classification["reason"],
        "next_step": classification["next_step"],
        "device_commands_executed": False,
        "device_mutations": False,
        "pm_actor_executed": False,
        "mdm_helper_executed": False,
        "tracefs_write_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "wifi_bringup_executed": False,
        "partition_write_executed": False,
        "flash_executed": False,
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"manifest: {store.run_dir / 'manifest.json'}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""V1225 host-only classifier for the mdm_helper wait/request gap.

V1224 proved the native path now starts ``mdm_helper`` with ``/dev/esoc-0``
and makes ``pm-service`` attempt ``/dev/subsys_esoc0``, but still reaches a
crash boundary before ``ks``, MHI, WLFW service 69, BDF, or ``wlan0``.  This
classifier does not contact the device.  It joins V1224 with earlier
WAIT_FOR_REQ and Android-success evidence to select the next minimal live gate:
focused ``mdm_helper`` worker syscall/wchan/ioctl and MHI/ks surface
instrumentation in the same PM/CNSS path.
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


DEFAULT_OUT_DIR = Path("tmp/wifi/v1225-mdm-helper-wait-req-gap-classifier")
LATEST_POINTER = Path("tmp/wifi/latest-v1225-mdm-helper-wait-req-gap-classifier.txt")
DEFAULT_V1224_MANIFEST = Path("tmp/wifi/v1224-mdm-helper-ks-mhi-parity-live/manifest.json")
DEFAULT_V1224_OBSERVER = Path("tmp/wifi/v1224-mdm-helper-ks-mhi-parity-live/host/pm-server-wchan-tracefs-observer.txt")
DEFAULT_V1160_MANIFEST = Path("tmp/wifi/v1160-pm-esoc-trigger-reconcile/manifest.json")

REFERENCE_REPORTS = {
    "v911": Path("docs/reports/NATIVE_INIT_V911_MDM_HELPER_ESOC_FD_STALL_CLASSIFIER_2026-05-26.md"),
    "v1144": Path("docs/reports/NATIVE_INIT_V1144_ESOC_WAIT_IOCTL_CONTRACT_2026-05-27.md"),
    "v1158": Path("docs/reports/NATIVE_INIT_V1158_ANDROID_MDM_HELPER_EXTENDED_STRACE_CAPTURE_2026-05-27.md"),
    "v1193_v1194": Path("docs/plans/NATIVE_INIT_V1193_V1194_ESOC_POWER_PLAN_2026-05-29.md"),
}


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v1224-manifest", type=Path, default=DEFAULT_V1224_MANIFEST)
    parser.add_argument("--v1224-observer", type=Path, default=DEFAULT_V1224_OBSERVER)
    parser.add_argument("--v1160-manifest", type=Path, default=DEFAULT_V1160_MANIFEST)
    return parser.parse_args()


def read_text(path: Path, limit: int = 4_000_000) -> str:
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
    return str(value).strip().lower() in {"1", "true", "yes", "ok", "pass"}


def intish(value: Any) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    text = str(value).strip()
    if not text:
        return 0
    try:
        return int(text, 0)
    except ValueError:
        return 0


def text_has_all(text: str, needles: list[str]) -> bool:
    return bool(text) and all(needle in text for needle in needles)


def lower_trace_field_present(lower: dict[str, Any], suffixes: tuple[str, ...]) -> bool:
    return any(str(key).endswith(suffixes) for key in lower)


def lower_trace_syscall_visibility(lower: dict[str, Any]) -> dict[str, Any]:
    keys = [str(key) for key in lower]
    thread_probe_keys = [key for key in keys if "thread_probe" in key]
    syscall_keys = [key for key in keys if ".syscall" in key or key.endswith(".syscall.raw")]
    wchan_keys = [key for key in keys if key.endswith(".wchan")]
    wchans = sorted({str(lower[key]) for key in wchan_keys if str(lower[key]).strip()})
    syscall_names = sorted({str(lower[key]) for key in keys if key.endswith(".name") and str(lower[key]).strip()})
    ioctl_values = [
        str(value)
        for key, value in lower.items()
        if "0x8004cc02" in str(value) or "ESOC_WAIT_FOR_REQ" in str(value)
    ]
    return {
        "thread_probe_key_count": len(thread_probe_keys),
        "syscall_key_count": len(syscall_keys),
        "wchan_key_count": len(wchan_keys),
        "has_thread_probe": bool(thread_probe_keys),
        "has_syscall": bool(syscall_keys),
        "has_wchan": bool(wchan_keys),
        "has_wait_for_req_value": bool(ioctl_values),
        "wchans": wchans,
        "syscall_names": syscall_names,
        "all_wchans_nanosleep": bool(wchans) and set(wchans) == {"SyS_nanosleep"},
    }


def summarize_v1224(manifest: dict[str, Any], observer_text: str) -> dict[str, Any]:
    parity = manifest.get("mdm_helper_ks_mhi_parity") or {}
    boundary = manifest.get("post_esoc_boundary") or {}
    tracefs = nested_get(manifest, ("analysis", "tracefs_uprobe"), {})
    pm_contract = tracefs.get("pm_contract", {}) if isinstance(tracefs, dict) else {}
    lower = parity.get("lower_trace", {}) if isinstance(parity, dict) else {}
    lower_visibility = lower_trace_syscall_visibility(lower if isinstance(lower, dict) else {})
    states = boundary.get("mdm3_state_transitions") or []
    if not isinstance(states, list):
        states = []
    safety_keys = [
        "wifi_hal_start_executed",
        "scan_connect_executed",
        "credential_use_executed",
        "dhcp_route_executed",
        "external_ping_executed",
        "wifi_bringup_executed",
        "flash_executed",
        "partition_write_executed",
    ]
    syscall_paths = parity.get("syscall_paths") or []
    if not isinstance(syscall_paths, list):
        syscall_paths = []
    observer_has_lower_trace = "post_pm_mdm_helper_lower_trace." in observer_text
    observer_has_wait_req = "0x8004cc02" in observer_text or "ESOC_WAIT_FOR_REQ" in observer_text
    observer_has_mdm_subsys_powerup = "mdm_subsys_powerup" in observer_text
    return {
        "decision": manifest.get("decision", ""),
        "pass": bool(manifest.get("pass")),
        "reason": manifest.get("reason", ""),
        "next_step": manifest.get("next_step", ""),
        "pm_service_subsys_esoc0_attempt": boolish(parity.get("pm_service_subsys_esoc0_attempt")),
        "pm_service_subsys_esoc0_fd_count": intish(parity.get("pm_service_subsys_esoc0_fd_count")),
        "pm_service_subsys_modem_fd_count": intish(parity.get("pm_service_subsys_modem_fd_count")),
        "mdm_helper_esoc_present": boolish(parity.get("mdm_helper_esoc_present")),
        "mdm_helper_esoc0_count_window": intish(parity.get("mdm_helper_esoc0_count_window")),
        "mdm_helper_mhi_pipe_count_window": intish(parity.get("mdm_helper_mhi_pipe_count_window")),
        "ks_or_mhi_present": boolish(parity.get("ks_or_mhi_present")),
        "ks_count_window": intish(parity.get("ks_count_window")),
        "mhi_cmdline_count_window": intish(parity.get("mhi_cmdline_count_window")),
        "lower_trace_sample_count": intish(parity.get("lower_trace_sample_count")),
        "lower_trace_samples": parity.get("lower_trace_samples") or [],
        "lower_trace_visibility": lower_visibility,
        "pm_service_syscall_paths": syscall_paths,
        "pm_service_openat_subsys_esoc0_wchan": "mdm_subsys_powerup" if observer_has_mdm_subsys_powerup else "",
        "observer_has_lower_trace": observer_has_lower_trace,
        "observer_has_wait_req": observer_has_wait_req,
        "mdm3_state_transitions": states,
        "max_dmesg_modem_down_count": intish(boundary.get("max_dmesg_modem_down_count")),
        "max_dmesg_wlfw_count": intish(boundary.get("max_dmesg_wlfw_count")),
        "service69_seen": boolish(boundary.get("service69_seen")),
        "wlan0_seen": boolish(boundary.get("wlan0_seen")),
        "child_mdm_helper_trace_syscalls": intish(pm_contract.get("child.mdm_helper.trace_syscalls")),
        "child_mdm_helper_syscall_trace_started": intish(pm_contract.get("child.mdm_helper.syscall_trace_started")),
        "safety": {key: boolish(manifest.get(key)) for key in safety_keys},
    }


def summarize_v1160(manifest: dict[str, Any]) -> dict[str, Any]:
    android = nested_get(manifest, ("analysis", "android_v1159"), {})
    classification = nested_get(manifest, ("analysis", "classification"), {})
    times = android.get("times", {}) if isinstance(android, dict) else {}
    return {
        "decision": manifest.get("decision", ""),
        "pass": bool(manifest.get("pass")),
        "classification_decision": classification.get("decision", "") if isinstance(classification, dict) else "",
        "dmesg_fw_ready": boolish(android.get("dmesg_fw_ready") if isinstance(android, dict) else False),
        "dmesg_wlan0_created": boolish(android.get("dmesg_wlan0_created") if isinstance(android, dict) else False),
        "dmesg_pm_service_esoc0_get": boolish(android.get("dmesg_pm_service_esoc0_get") if isinstance(android, dict) else False),
        "pm_service_stack_has_mdm_subsys_powerup": boolish(
            android.get("pm_service_stack_has_mdm_subsys_powerup") if isinstance(android, dict) else False
        ),
        "times": times if isinstance(times, dict) else {},
    }


def summarize_references() -> dict[str, Any]:
    refs: dict[str, Any] = {}
    for name, path in REFERENCE_REPORTS.items():
        text = read_text(path)
        if name == "v911":
            checks = {
                "wait_for_req_observed": text_has_all(text, ["ESOC_WAIT_FOR_REQ", "worker thread wchan", "esoc_dev_ioctl"]),
                "esoc_fd_no_mhi_ks": text_has_all(text, ["`fd_esoc0_count.window`", "`fd_mhi_pipe_count.final`", "`ks_count.final`"]),
            }
        elif name == "v1144":
            checks = {
                "wait_ioctl_decoded": text_has_all(text, ["_IOR(0xcc, 2", "ESOC_WAIT_FOR_REQ"]),
                "request_engine_fifo": "request-engine FIFO" in text,
                "no_wlfw_wlan0": text_has_all(text, ["WLFW/service69/BDF/wlan0", "not observed"]),
            }
        elif name == "v1158":
            checks = {
                "android_fw_ready_wlan0": text_has_all(text, ["FW ready event received", "wlan0"]),
                "mdm_helper_not_image_transfer": (
                    "mdm_helper` does not expose a post-wakelock image transfer path" in text
                    or "mdm_helper does not expose a post-wakelock image transfer path" in text
                ),
                "pm_service_trigger_candidate": "`pm-service` remains the stronger trigger candidate" in text,
            }
        else:
            checks = {
                "long_wait_req_gap": text_has_all(text, ["ESOC_WAIT_FOR_REQ", "53 minutes"]),
                "subsys_esoc0_power_route": text_has_all(text, ["subsys_esoc0 open", "mdm_subsys_powerup"]),
            }
        refs[name] = {
            "path": str(path),
            "present": bool(text),
            "checks": checks,
            "all_checks": all(checks.values()) if checks else bool(text),
        }
    return refs


def classify(analysis: dict[str, Any]) -> dict[str, Any]:
    v1224 = analysis["v1224"]
    v1160 = analysis["v1160"]
    refs = analysis["references"]
    safety_clean = not any(v1224["safety"].values())
    lower_visibility = v1224["lower_trace_visibility"]
    worker_visible_sleeping_without_wait_req = (
        v1224["lower_trace_sample_count"] > 0
        and lower_visibility["has_thread_probe"]
        and lower_visibility["has_syscall"]
        and lower_visibility["has_wchan"]
        and lower_visibility["all_wchans_nanosleep"]
        and not lower_visibility["has_wait_for_req_value"]
        and v1224["child_mdm_helper_trace_syscalls"] == 0
        and v1224["child_mdm_helper_syscall_trace_started"] == 0
    )
    flags = {
        "v1224_live_passed": v1224["pass"] and v1224["decision"] == "v1224-mdm-helper-esoc-present-ks-mhi-absent-crash",
        "pm_service_esoc_power_trigger_seen": (
            v1224["pm_service_subsys_esoc0_attempt"]
            and "/dev/subsys_esoc0" in v1224["pm_service_syscall_paths"]
            and v1224["pm_service_openat_subsys_esoc0_wchan"] == "mdm_subsys_powerup"
        ),
        "mdm_helper_esoc_fd_present": v1224["mdm_helper_esoc_present"] and v1224["mdm_helper_esoc0_count_window"] > 0,
        "ks_mhi_absent": (
            not v1224["ks_or_mhi_present"]
            and v1224["ks_count_window"] == 0
            and v1224["mdm_helper_mhi_pipe_count_window"] == 0
            and v1224["mhi_cmdline_count_window"] <= 0
        ),
        "wlfw_bdf_wlan0_absent": (
            not v1224["service69_seen"]
            and not v1224["wlan0_seen"]
            and v1224["max_dmesg_wlfw_count"] == 0
        ),
        "mdm3_crash_or_offlining_seen": (
            "OFFLINING" in v1224["mdm3_state_transitions"]
            and v1224["max_dmesg_modem_down_count"] > 0
        ),
        "v1224_worker_visible_sleeping_without_wait_req": worker_visible_sleeping_without_wait_req,
        "historical_wait_req_boundary_known": refs["v911"]["all_checks"] and refs["v1144"]["all_checks"],
        "android_success_trigger_reference_available": (
            refs["v1158"]["present"]
            and refs["v1158"]["checks"]["android_fw_ready_wlan0"]
            and refs["v1158"]["checks"]["pm_service_trigger_candidate"]
            and v1160["pass"]
            and v1160["dmesg_fw_ready"]
            and v1160["dmesg_wlan0_created"]
            and v1160["dmesg_pm_service_esoc0_get"]
            and v1160["pm_service_stack_has_mdm_subsys_powerup"]
        ),
        "older_long_wait_gap_recorded": refs["v1193_v1194"]["all_checks"],
        "safety_clean": safety_clean,
    }
    required = [
        "v1224_live_passed",
        "pm_service_esoc_power_trigger_seen",
        "mdm_helper_esoc_fd_present",
        "ks_mhi_absent",
        "wlfw_bdf_wlan0_absent",
        "mdm3_crash_or_offlining_seen",
        "v1224_worker_visible_sleeping_without_wait_req",
        "historical_wait_req_boundary_known",
        "android_success_trigger_reference_available",
        "safety_clean",
    ]
    missing = [name for name in required if not flags.get(name)]
    if not missing:
        return {
            "decision": "v1225-mdm-helper-post-wait-sleep-gap-classified",
            "pass": True,
            "reason": (
                "V1224 reaches the Android-like mdm_helper-esoc plus pm-service subsys_esoc0 trigger, "
                "but mdm_helper threads are only observed in SyS_nanosleep with no ks/MHI/WLFW; "
                "historical evidence identifies ESOC_WAIT_FOR_REQ as the earlier boundary, so the next "
                "gap is the post-wait sleep/no-MHI branch."
            ),
            "next_step": (
                "V1226 should add a bounded lower-trace v2 live gate in the V1224 PM/CNSS path: "
                "enable mdm_helper syscall/return tracing from process start, capture ESOC_WAIT_FOR_REQ "
                "return value and every subsequent open/exec/ioctl error, and poll "
                "/dev/mhi_0305_01.01.00_pipe_10, /sys/bus/mhi/devices, PCIe link state, and /vendor/bin/ks "
                "before and after pm-service opens /dev/subsys_esoc0; keep Wi-Fi HAL, scan/connect, "
                "credentials, DHCP/routes, external ping, flash, and partition writes blocked."
            ),
            "missing": [],
            "flags": flags,
        }
    return {
        "decision": "v1225-mdm-helper-wait-req-gap-input-incomplete",
        "pass": False,
        "reason": "missing=" + ",".join(missing),
        "next_step": "refresh V1224/V911/V1144/V1158/V1160 evidence before designing a new live gate",
        "missing": missing,
        "flags": flags,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    v1224 = manifest["analysis"]["v1224"]
    v1160 = manifest["analysis"]["v1160"]
    classification = manifest["analysis"]["classification"]
    rows = [
        ["V1224 decision", str(v1224["pass"]), v1224["decision"]],
        ["pm-service /dev/subsys_esoc0", str(classification["flags"]["pm_service_esoc_power_trigger_seen"]), v1224["pm_service_openat_subsys_esoc0_wchan"]],
        ["mdm_helper /dev/esoc-0", str(classification["flags"]["mdm_helper_esoc_fd_present"]), str(v1224["mdm_helper_esoc0_count_window"])],
        ["ks/MHI absent", str(classification["flags"]["ks_mhi_absent"]), f"ks={v1224['ks_count_window']} mhi={v1224['mdm_helper_mhi_pipe_count_window']}"],
        ["WLFW/wlan0 absent", str(classification["flags"]["wlfw_bdf_wlan0_absent"]), f"wlfw={v1224['max_dmesg_wlfw_count']} wlan0={v1224['wlan0_seen']}"],
        ["mdm3 crash/offlining", str(classification["flags"]["mdm3_crash_or_offlining_seen"]), f"states={v1224['mdm3_state_transitions']} modem_down={v1224['max_dmesg_modem_down_count']}"],
        ["worker sleep/no wait value", str(classification["flags"]["v1224_worker_visible_sleeping_without_wait_req"]), json.dumps(v1224["lower_trace_visibility"], sort_keys=True)],
        ["historical wait boundary", str(classification["flags"]["historical_wait_req_boundary_known"]), "V911/V1144"],
        ["Android trigger reference", str(classification["flags"]["android_success_trigger_reference_available"]), v1160["classification_decision"]],
        ["safety clean", str(classification["flags"]["safety_clean"]), "no HAL/scan/credential/DHCP/ping/flash"],
    ]
    samples = [
        [
            sample.get("index"),
            sample.get("alive"),
            sample.get("state"),
            sample.get("fd_esoc0_count"),
            sample.get("fd_subsys_esoc0_count"),
            sample.get("fd_mhi_pipe_count"),
            sample.get("ks_count"),
        ]
        for sample in v1224["lower_trace_samples"][:10]
    ]
    reference_rows = [
        [name, str(ref["present"]), str(ref["all_checks"]), json.dumps(ref["checks"], sort_keys=True)]
        for name, ref in manifest["analysis"]["references"].items()
    ]
    return "\n".join(
        [
            "# V1225 mdm_helper WAIT_FOR_REQ Gap Classifier",
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
            "## V1224 Lower Samples",
            "",
            markdown_table(["idx", "alive", "state", "esoc0 fd", "subsys fd", "mhi fd", "ks"], samples),
            "",
            "## Reference Checks",
            "",
            markdown_table(["ref", "present", "all checks", "checks"], reference_rows),
            "",
            "## Safety",
            "",
            "- device commands executed: `false`",
            "- live eSoC/subsys/ioctl retry: `false`",
            "- Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping: `false`",
            "- flash, partition writes, and boot image writes: `false`",
            "",
        ]
    )


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    analysis = {
        "v1224": summarize_v1224(load_json(args.v1224_manifest), read_text(args.v1224_observer)),
        "v1160": summarize_v1160(load_json(args.v1160_manifest)),
        "references": summarize_references(),
    }
    classification = classify(analysis)
    analysis["classification"] = classification
    manifest = {
        "cycle": "v1225",
        "generated_at": now_iso(),
        "host": collect_host_metadata(),
        "inputs": {
            "v1224_manifest": str(repo_path(args.v1224_manifest)),
            "v1224_observer": str(repo_path(args.v1224_observer)),
            "v1160_manifest": str(repo_path(args.v1160_manifest)),
            "reference_reports": {key: str(repo_path(path)) for key, path in REFERENCE_REPORTS.items()},
        },
        "analysis": analysis,
        "decision": classification["decision"],
        "pass": classification["pass"],
        "reason": classification["reason"],
        "next_step": classification["next_step"],
        "device_commands_executed": False,
        "device_mutations": False,
        "live_esoc_ioctl_executed": False,
        "tracefs_write_executed": False,
        "pm_actor_executed": False,
        "cnss_daemon_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "wifi_bringup_executed": False,
        "boot_image_write_executed": False,
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

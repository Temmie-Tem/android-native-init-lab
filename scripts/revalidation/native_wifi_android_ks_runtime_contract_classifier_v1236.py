#!/usr/bin/env python3
"""V1236 host-only classifier for Android ks/MHI runtime contract vs native V1235."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1236-android-ks-runtime-contract-classifier")
LATEST_POINTER = Path("tmp/wifi/latest-v1236-android-ks-runtime-contract-classifier.txt")
V896_MANIFEST = Path("tmp/wifi/v896-android-mdm-helper-image-contract/manifest.json")
V1159_MANIFEST = Path("tmp/wifi/v1159-pm-thread-sampler-live-20260527-191019/manifest.json")
V1160_MANIFEST = Path("tmp/wifi/v1160-pm-esoc-trigger-reconcile/manifest.json")
V1228_MANIFEST = Path("tmp/wifi/v1228-mdm-helper-early-compact-trace-live/manifest.json")
V1232_MANIFEST = Path("tmp/wifi/v1232-mdm-helper-post-wait-req-ks-observer-live/manifest.json")
V1235_MANIFEST = Path("tmp/wifi/v1235-mdm-helper-post-wait-req-branch-snapshot-live/manifest.json")
V1235_OBSERVER = Path("tmp/wifi/v1235-mdm-helper-post-wait-req-branch-snapshot-live/host/pm-server-wchan-tracefs-observer.txt")


FORBIDDEN_OUTPUT_ENV_KEYS = ("A90_WIFI_SSID", "A90_WIFI_PSK")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def load_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {}
    try:
        value = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def read_text_limited(path: Path, limit: int = 4 * 1024 * 1024) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    data = resolved.read_bytes()[:limit]
    return data.decode("utf-8", errors="replace")


def bool_path(mapping: dict[str, Any], *keys: str) -> bool:
    current: Any = mapping
    for key in keys:
        if not isinstance(current, dict):
            return False
        current = current.get(key)
    return bool(current)


def int_path(mapping: dict[str, Any], *keys: str, default: int = 0) -> int:
    current: Any = mapping
    for key in keys:
        if not isinstance(current, dict):
            return default
        current = current.get(key)
    try:
        return int(str(current), 0)
    except (TypeError, ValueError):
        return default


def parse_status_series(text: str, field: str) -> list[str]:
    pattern = re.compile(rf"^pm_observer_mdm_power_on\.status\.{re.escape(field)}=(.*)$", re.MULTILINE)
    return [match.group(1).strip() for match in pattern.finditer(text)]


def analyze_v1235_observer(text: str) -> dict[str, Any]:
    gpio142 = [int(value) for value in parse_status_series(text, "gpio142_count") if value.isdigit()]
    mdm3 = parse_status_series(text, "mdm3_state")
    child_wchan = parse_status_series(text, "child_wchan")
    mhi_dev = [int(value) for value in parse_status_series(text, "mhi_dev_count") if value.isdigit()]
    ks_count = [int(value) for value in parse_status_series(text, "ks_count") if value.isdigit()]
    pcie = parse_status_series(text, "pcie_link_state")
    mdm_helper_fds = parse_status_series(text, "mdm_helper_fds")
    return {
        "present": bool(text),
        "post_wait_branch_flag_seen": "post_pm_mdm_helper_esoc_observer.post_wait_req_branch_snapshot=1" in text,
        "direct_subsys_path": "/dev/subsys_esoc0" in text,
        "child_wchan_has_mdm_subsys_powerup": any("mdm_subsys_powerup" in value for value in child_wchan),
        "mdm_helper_holds_esoc0": any("/dev/esoc-0" in value for value in mdm_helper_fds),
        "max_gpio142_count": max(gpio142, default=0),
        "max_mhi_dev_count": max(mhi_dev, default=0),
        "max_ks_count": max(ks_count, default=0),
        "mdm3_states": sorted(set(mdm3)),
        "pcie_states": sorted(set(pcie)),
        "status_sample_count": len(child_wchan),
    }


def analyze() -> dict[str, Any]:
    v896 = load_json(V896_MANIFEST)
    v1159 = load_json(V1159_MANIFEST)
    v1160 = load_json(V1160_MANIFEST)
    v1228 = load_json(V1228_MANIFEST)
    v1232 = load_json(V1232_MANIFEST)
    v1235 = load_json(V1235_MANIFEST)
    observer_text = read_text_limited(V1235_OBSERVER)
    v1235_observer = analyze_v1235_observer(observer_text)

    v896_flags = v896.get("v853_actor_flags") or {}
    v852 = v896.get("v852") or {}
    v1159_trace = ((v1159.get("context") or {}).get("trace_classification") or {})
    v1160_analysis = v1160.get("analysis") or {}
    v1160_android = v1160_analysis.get("android_v1159") or {}
    v1160_native = v1160_analysis.get("native_v1139") or {}
    v1160_flags = ((v1160_analysis.get("classification") or {}).get("flags") or {})
    v1235_post = v1235.get("mdm_helper_post_wait_req") or {}
    v1235_branch = v1235.get("mdm_helper_post_wait_branch") or {}
    v1228_early = v1228.get("mdm_helper_early_compact_trace") or {}
    v1232_post = v1232.get("mdm_helper_post_wait_req") or {}

    android_contract = {
        "v896_pass": bool(v896.get("pass")),
        "mdm3_online": (v852.get("mdm3_state") == "ONLINE"),
        "wlan0_present": bool_path(v852, "timeline", "wlan0", "present"),
        "bdf_present": bool_path(v852, "dmesg_hints", "has_bdf"),
        "wlfw_present": bool_path(v852, "dmesg_hints", "has_wlfw"),
        "gpio142_irq_count": int_path(v852, "irq_mdm_status", "count_total"),
        "actor_mdm_helper_esoc_fd": bool(v896_flags.get("has_mdm_helper_esoc_fd")),
        "actor_ks_esoc_fd": bool(v896_flags.get("has_ks_esoc_fd")),
        "actor_ks_mhi_pipe": bool(v896_flags.get("has_ks_mhi_pipe")),
        "actor_per_mgr_subsys_esoc0_fd": bool(v896_flags.get("has_per_mgr_subsys_esoc0_fd")),
        "actor_per_mgr_subsys_modem_fd": bool(v896_flags.get("has_per_mgr_subsys_modem_fd")),
        "mdm_helper_strace_wait_for_req": bool(v1159_trace.get("strace_has_wait_for_req")),
        "mdm_helper_strace_cmd_engine_register": bool(v1159_trace.get("strace_has_cmd_engine_register")),
        "mdm_helper_strace_wakelock": bool(v1159_trace.get("strace_has_wakelock")),
        "pm_service_binder_mdm_subsys_powerup": bool(v1160_android.get("pm_service_stack_has_mdm_subsys_powerup")),
        "pm_service_status_d_state": bool(v1160_android.get("pm_service_status_d_state")),
        "per_proxy_before_esoc0": bool(v1160_flags.get("android_per_proxy_action_precedes_esoc0")),
        "pm_service_esoc0_time": (v1160_android.get("times") or {}).get("pm_service_esoc0_get"),
        "per_proxy_start_time": (v1160_android.get("times") or {}).get("per_proxy_start"),
        "fw_ready_time": (v1160_android.get("times") or {}).get("fw_ready"),
        "wlan0_time": (v1160_android.get("times") or {}).get("wlan0"),
    }
    native_contract = {
        "v1228_wait_for_req_seen": int_path(v1228_early, "wait_for_req_thread_count") > 0,
        "v1228_mdm_helper_esoc0": int_path(v1228_early, "max_fd_esoc0_count") > 0,
        "v1232_wait_returned": int_path(v1232_post, "summary", "transition_detected") > 0,
        "v1232_transition_sample": int_path(v1232_post, "summary", "transition_sample", default=-1),
        "v1235_wait_returned": int_path(v1235_post, "summary", "transition_detected") > 0,
        "v1235_transition_sample": int_path(v1235_post, "summary", "transition_sample", default=-1),
        "v1235_execve_count": int_path(v1235_branch, "execve_count"),
        "v1235_ioctl_count": int_path(v1235_branch, "ioctl_count"),
        "v1235_nanosleep_count": int_path(v1235_branch, "nanosleep_count"),
        "v1235_ks_count": int_path(v1235_post, "summary", "ks_process_count"),
        "v1235_mhi_pipe_exists": int_path(v1235_post, "summary", "mhi_pipe_exists"),
        "v1235_mhi_pipe_fd_count": int_path(v1235_post, "summary", "mhi_pipe_fd_count"),
        "v1235_branch_forbidden": v1235_branch.get("forbidden") or {},
        "v1235_post_forbidden": v1235_post.get("forbidden") or {},
        "v1235_observer": v1235_observer,
        "v1160_native_per_proxy_skipped": str(v1160_native.get("per_proxy_start_skipped")) == "1",
        "v1160_native_pm_proxy_helper_seen": bool(v1160_native.get("pm_proxy_helper_subsys_modem_seen")),
        "v1160_native_mdm_helper_esoc0": int(v1160_native.get("mdm_helper_esoc0_count") or 0) > 0,
        "v1160_native_ks_count": int(v1160_native.get("ks_count") or 0),
        "v1160_native_mhi_pipe_count": int(v1160_native.get("mhi_pipe_count") or 0),
        "v1160_native_service69": int(v1160_native.get("qrtr_service69") or 0),
        "v1160_native_wlan0": int(v1160_native.get("wlan0_count") or 0),
    }
    checks = [
        {
            "name": "android-positive-lower-chain",
            "status": "pass" if all([
                android_contract["v896_pass"],
                android_contract["mdm3_online"],
                android_contract["wlan0_present"],
                android_contract["bdf_present"],
                android_contract["wlfw_present"],
                android_contract["gpio142_irq_count"] > 0,
            ]) else "blocked",
            "detail": "Android has mdm3 ONLINE, WLFW/BDF/wlan0, and GPIO142 IRQ",
        },
        {
            "name": "android-actor-contract",
            "status": "pass" if all([
                android_contract["actor_mdm_helper_esoc_fd"],
                android_contract["actor_ks_esoc_fd"],
                android_contract["actor_ks_mhi_pipe"],
                android_contract["actor_per_mgr_subsys_esoc0_fd"],
            ]) else "blocked",
            "detail": "Android actor handoff includes mdm_helper, ks, MHI, and per_mgr subsystem fds",
        },
        {
            "name": "android-pm-proxy-precedes-esoc0",
            "status": "pass" if android_contract["per_proxy_before_esoc0"] else "blocked",
            "detail": f"per_proxy={android_contract['per_proxy_start_time']} esoc0={android_contract['pm_service_esoc0_time']}",
        },
        {
            "name": "native-mdm-helper-wait-returned",
            "status": "pass" if native_contract["v1235_wait_returned"] else "blocked",
            "detail": f"transition_sample={native_contract['v1235_transition_sample']}",
        },
        {
            "name": "native-no-mdm-helper-exec",
            "status": "pass" if native_contract["v1235_execve_count"] == 0 else "blocked",
            "detail": f"execve_count={native_contract['v1235_execve_count']}",
        },
        {
            "name": "native-no-ks-mhi-wlfw",
            "status": "pass" if all([
                native_contract["v1235_ks_count"] == 0,
                native_contract["v1235_mhi_pipe_exists"] == 0,
                native_contract["v1235_mhi_pipe_fd_count"] == 0,
                native_contract["v1235_observer"]["max_gpio142_count"] == 0,
                native_contract["v1235_observer"]["max_mhi_dev_count"] == 0,
                native_contract["v1235_observer"]["max_ks_count"] == 0,
            ]) else "blocked",
            "detail": "latest native window has no ks/MHI/GPIO142 progress",
        },
        {
            "name": "native-direct-subsys-blocks",
            "status": "pass" if native_contract["v1235_observer"]["child_wchan_has_mdm_subsys_powerup"] else "blocked",
            "detail": "direct subsystem trigger child is in mdm_subsys_powerup",
        },
        {
            "name": "guardrails-clean",
            "status": "pass" if not native_contract["v1235_branch_forbidden"] and not native_contract["v1235_post_forbidden"] else "blocked",
            "detail": "no Wi-Fi HAL/scan/credential/DHCP/ping guardrail violation in V1235 parser",
        },
    ]
    blockers = [check["name"] for check in checks if check["status"] != "pass"]
    if blockers:
        decision = "v1236-android-ks-contract-classifier-blocked"
        passed = False
        reason = "blocked by " + ", ".join(blockers)
        next_step = "repair missing input evidence before planning a live gate"
    else:
        decision = "v1236-ks-contract-is-pm-proxy-pm-service-trigger-not-mdm-helper-exec"
        passed = True
        reason = (
            "Android ks/MHI path correlates with per_proxy -> pm-service Binder -> subsys_esoc0/mdm_subsys_powerup, "
            "while native V1235 proves mdm_helper WAIT_FOR_REQ return does not exec ks or create MHI by itself"
        )
        next_step = (
            "V1237 should run a bounded live gate that keeps V1235 branch snapshot but enables late per_proxy only after "
            "mdm_helper holds /dev/esoc-0; capture pm-service Binder wchan/fds plus ks/MHI/GPIO142, still no Wi-Fi HAL or connect"
        )
    return {
        "cycle": "v1236",
        "decision": decision,
        "pass": passed,
        "reason": reason,
        "next_step": next_step,
        "inputs": {
            "v896": str(repo_path(V896_MANIFEST)),
            "v1159": str(repo_path(V1159_MANIFEST)),
            "v1160": str(repo_path(V1160_MANIFEST)),
            "v1228": str(repo_path(V1228_MANIFEST)),
            "v1232": str(repo_path(V1232_MANIFEST)),
            "v1235": str(repo_path(V1235_MANIFEST)),
            "v1235_observer": str(repo_path(V1235_OBSERVER)),
        },
        "android_contract": android_contract,
        "native_contract": native_contract,
        "checks": checks,
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
        "flash_executed": False,
        "partition_write_executed": False,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    android = manifest["android_contract"]
    native = manifest["native_contract"]
    observer = native["v1235_observer"]
    checks = [[row["name"], row["status"], row["detail"]] for row in manifest["checks"]]
    android_rows = [
        ["mdm3_online", android["mdm3_online"]],
        ["wlan0_present", android["wlan0_present"]],
        ["bdf_present", android["bdf_present"]],
        ["wlfw_present", android["wlfw_present"]],
        ["gpio142_irq_count", android["gpio142_irq_count"]],
        ["mdm_helper_esoc_fd", android["actor_mdm_helper_esoc_fd"]],
        ["ks_esoc_fd", android["actor_ks_esoc_fd"]],
        ["ks_mhi_pipe", android["actor_ks_mhi_pipe"]],
        ["per_mgr_subsys_esoc0_fd", android["actor_per_mgr_subsys_esoc0_fd"]],
        ["per_proxy_start_time", android["per_proxy_start_time"]],
        ["pm_service_esoc0_time", android["pm_service_esoc0_time"]],
        ["pm_service_binder_mdm_subsys_powerup", android["pm_service_binder_mdm_subsys_powerup"]],
        ["fw_ready_time", android["fw_ready_time"]],
        ["wlan0_time", android["wlan0_time"]],
    ]
    native_rows = [
        ["v1228_wait_for_req_seen", native["v1228_wait_for_req_seen"]],
        ["v1235_wait_returned", native["v1235_wait_returned"]],
        ["v1235_transition_sample", native["v1235_transition_sample"]],
        ["v1235_execve_count", native["v1235_execve_count"]],
        ["v1235_ioctl_count", native["v1235_ioctl_count"]],
        ["v1235_nanosleep_count", native["v1235_nanosleep_count"]],
        ["v1235_ks_count", native["v1235_ks_count"]],
        ["v1235_mhi_pipe_exists", native["v1235_mhi_pipe_exists"]],
        ["v1235_mhi_pipe_fd_count", native["v1235_mhi_pipe_fd_count"]],
        ["observer_child_mdm_subsys_powerup", observer["child_wchan_has_mdm_subsys_powerup"]],
        ["observer_mdm_helper_holds_esoc0", observer["mdm_helper_holds_esoc0"]],
        ["observer_max_gpio142_count", observer["max_gpio142_count"]],
        ["observer_max_mhi_dev_count", observer["max_mhi_dev_count"]],
        ["observer_max_ks_count", observer["max_ks_count"]],
        ["observer_mdm3_states", ",".join(observer["mdm3_states"])],
        ["observer_pcie_states", ",".join(observer["pcie_states"])],
    ]
    safety_rows = [[key, manifest[key]] for key in (
        "device_commands_executed",
        "device_mutations",
        "pm_actor_executed",
        "mdm_helper_executed",
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
        "# V1236 Android ks/MHI Runtime Contract Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        "",
        "## Checks",
        "",
        markdown_table(["check", "status", "detail"], checks),
        "",
        "## Android Contract Evidence",
        "",
        markdown_table(["field", "value"], android_rows),
        "",
        "## Native Negative Evidence",
        "",
        markdown_table(["field", "value"], native_rows),
        "",
        "## Safety",
        "",
        markdown_table(["field", "value"], safety_rows),
        "",
    ])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = analyze()
    manifest["generated_at"] = now_iso()
    manifest["command"] = args.command
    manifest["host"] = collect_host_metadata()
    if args.command == "plan":
        manifest["decision"] = "v1236-android-ks-runtime-contract-plan-ready"
        manifest["pass"] = True
        manifest["reason"] = "plan-only; host-only classifier would read existing manifests and observer transcript"
        manifest["next_step"] = "run V1236 host-only classifier"
    text = render_summary(manifest)
    for env_key in FORBIDDEN_OUTPUT_ENV_KEYS:
        needle = os.environ.get(env_key, "")
        if needle and needle in text:
            raise RuntimeError(f"forbidden output string leaked from {env_key}")
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", text)
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

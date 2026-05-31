#!/usr/bin/env python3
"""V1336 host-only classifier for Android-only pre-CNSS provider inputs."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1336-android-pre-cnss-provider-classifier")
LATEST_POINTER = Path("tmp/wifi/latest-v1336-android-pre-cnss-provider-classifier.txt")
DEFAULT_V1331 = Path("tmp/wifi/v1331-android-sdx50m-timing-handoff/v1331-android-sdx50m-timing-recapture-run/manifest.json")
DEFAULT_V1328 = Path("tmp/wifi/v1328-mdm2ap-timing-sampler-live/manifest.json")
DEFAULT_V1335 = Path("tmp/wifi/v1335-early-cnss-wlfw-parity-observer-live/manifest.json")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v1331-manifest", type=Path, default=DEFAULT_V1331)
    parser.add_argument("--v1328-manifest", type=Path, default=DEFAULT_V1328)
    parser.add_argument("--v1335-manifest", type=Path, default=DEFAULT_V1335)
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {}
    try:
        payload = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def prop_ns_to_seconds(props: dict[str, str], key: str) -> float | None:
    raw = props.get(key)
    if raw is None or not str(raw).isdigit():
        return None
    return int(str(raw)) / 1_000_000_000.0


def before(left: float | None, right: float | None) -> bool:
    return left is not None and right is not None and left < right


def extract_android(v1331: dict[str, Any]) -> dict[str, Any]:
    summary = v1331.get("android_summary") or {}
    props = {str(key): str(value) for key, value in (summary.get("props") or {}).items()}
    first_times = summary.get("first_times") or {}
    boottime_keys = (
        "ro.boottime.vendor.per_proxy_helper",
        "ro.boottime.vendor.qrtr-ns",
        "ro.boottime.vendor.pd_mapper",
        "ro.boottime.vendor.per_mgr",
        "ro.boottime.vendor.rmt_storage",
        "ro.boottime.vendor.tftp_server",
        "ro.boottime.vendor.per_proxy",
        "ro.boottime.cnss_diag",
        "ro.boottime.vendor.mdm_helper",
        "ro.boottime.cnss-daemon",
    )
    boottime_s = {key: prop_ns_to_seconds(props, key) for key in boottime_keys}
    boot_order = [
        {"key": key, "time_s": value}
        for key, value in sorted(boottime_s.items(), key=lambda item: (item[1] is None, item[1] or 0.0))
    ]
    cnss_daemon_s = boottime_s.get("ro.boottime.cnss-daemon")
    companion_keys = (
        "ro.boottime.vendor.qrtr-ns",
        "ro.boottime.vendor.rmt_storage",
        "ro.boottime.vendor.tftp_server",
        "ro.boottime.vendor.pd_mapper",
    )
    companion_before_cnss = {
        key: before(boottime_s.get(key), cnss_daemon_s)
        for key in companion_keys
    }
    return {
        "decision": v1331.get("decision", ""),
        "pass": bool(v1331.get("pass")),
        "first_times": first_times,
        "counts": summary.get("counts") or {},
        "process_flags": summary.get("process_flags") or {},
        "props": props,
        "boottime_s": boottime_s,
        "boot_order": boot_order,
        "wlfw_before_esoc": before(first_times.get("wlfw"), first_times.get("subsys_get_esoc0")),
        "bdf_after_wlfw": before(first_times.get("wlfw"), first_times.get("bdf")),
        "wlan0_after_bdf": before(first_times.get("bdf"), first_times.get("wlan0")),
        "pm_proxy_helper_before_per_mgr": before(
            boottime_s.get("ro.boottime.vendor.per_proxy_helper"),
            boottime_s.get("ro.boottime.vendor.per_mgr"),
        ),
        "per_proxy_before_cnss_daemon": before(
            boottime_s.get("ro.boottime.vendor.per_proxy"),
            cnss_daemon_s,
        ),
        "cnss_diag_before_cnss_daemon": before(
            boottime_s.get("ro.boottime.cnss_diag"),
            cnss_daemon_s,
        ),
        "mdm_helper_before_cnss_daemon": before(
            boottime_s.get("ro.boottime.vendor.mdm_helper"),
            cnss_daemon_s,
        ),
        "companion_before_cnss_daemon": companion_before_cnss,
        "all_companions_before_cnss_daemon": all(companion_before_cnss.values()),
    }


def extract_v1335(v1335: dict[str, Any]) -> dict[str, Any]:
    contract = (((v1335.get("analysis") or {}).get("helper") or {}).get("contract") or {})
    return {
        "decision": v1335.get("decision", ""),
        "pass": bool(v1335.get("pass")),
        "observe_only_gate": contract.get("observe_only_gate") == "1",
        "cnss_diag_started": contract.get("cnss_diag_started") == "1",
        "cnss_daemon_started": contract.get("cnss_daemon_started") == "1",
        "mdm_helper_started": contract.get("mdm_helper_start_attempted") == "1",
        "mdm_helper_esoc0_fd_seen": contract.get("mdm_helper_esoc0_fd_seen") == "1",
        "wlfw_precondition_observed": contract.get("wlfw_precondition_observed") == "1",
        "subsys_esoc0_open_attempted": contract.get("subsys_esoc0_open_attempted") == "1",
        "pm_proxy_helper_started": contract.get("pm_proxy_helper_start_executed") == "1",
        "per_proxy_started": contract.get("pm_proxy_started") == "1" or contract.get("pm_proxy_start_attempted") == "1",
        "service_manager_started": contract.get("service_manager_start_executed") == "1",
        "wifi_hal_started": contract.get("wifi_hal_start_executed") == "1",
        "scan_connect": contract.get("scan_connect_linkup") == "1",
        "external_ping": contract.get("external_ping") == "1",
        "result": contract.get("result", ""),
        "reason": contract.get("reason", ""),
        "surface_poll_count": contract.get("surface_poll_count", ""),
        "all_postflight_safe": contract.get("all_postflight_safe") == "1",
        "contract": contract,
    }


def extract_v1328(v1328: dict[str, Any]) -> dict[str, Any]:
    analysis = v1328.get("analysis") or {}
    trace = analysis.get("tracefs_uprobe") or {}
    pm_contract = trace.get("pm_contract") or {}
    response = analysis.get("response_sampler") or {}
    return {
        "decision": v1328.get("decision", ""),
        "pass": bool(v1328.get("pass")),
        "order": pm_contract.get("order", ""),
        "per_proxy_initial_start_executed": str(pm_contract.get("per_proxy_initial_start_executed", "0")) == "1",
        "late_per_proxy_started": str(pm_contract.get("late_per_proxy_started", "0")) == "1",
        "late_per_proxy_gate_positive": str(pm_contract.get("late_per_proxy_gate_positive", "0")) == "1",
        "cnss_daemon_start_executed": bool(v1328.get("cnss_daemon_start_executed")) or str(pm_contract.get("cnss_daemon_start_executed", "0")) == "1",
        "timing_wlfw_kmsg_max": int(str(response.get("timing_wlfw_kmsg_max", "0")) or "0"),
        "timing_ks_process_max": int(str(response.get("timing_ks_process_max", "0")) or "0"),
        "timing_mhi_bus_max": int(str(response.get("timing_mhi_bus_max", "0")) or "0"),
        "timing_wlan0_seen": bool(response.get("timing_wlan0_seen")),
        "timing_pm_service_powerup_seen": bool(response.get("timing_pm_service_powerup_seen")),
    }


def decide(android: dict[str, Any], native_v1335: dict[str, Any], native_v1328: dict[str, Any]) -> tuple[str, bool, str, str, dict[str, Any]]:
    android_pre_cnss_provider_chain = (
        android["pass"]
        and android["wlfw_before_esoc"]
        and android["pm_proxy_helper_before_per_mgr"]
        and android["per_proxy_before_cnss_daemon"]
        and android["all_companions_before_cnss_daemon"]
        and android["cnss_diag_before_cnss_daemon"]
    )
    native_observe_only_no_wlfw = (
        native_v1335["pass"]
        and native_v1335["observe_only_gate"]
        and native_v1335["cnss_daemon_started"]
        and native_v1335["mdm_helper_esoc0_fd_seen"]
        and not native_v1335["wlfw_precondition_observed"]
        and not native_v1335["subsys_esoc0_open_attempted"]
    )
    native_missing_pre_cnss_provider_chain = (
        not native_v1335["pm_proxy_helper_started"]
        and not native_v1335["per_proxy_started"]
        and not native_v1335["service_manager_started"]
    )
    late_per_proxy_not_sufficient = (
        native_v1328["pass"]
        and native_v1328["late_per_proxy_started"]
        and not native_v1328["per_proxy_initial_start_executed"]
        and native_v1328["timing_wlfw_kmsg_max"] == 0
        and native_v1328["timing_ks_process_max"] == 0
        and native_v1328["timing_mhi_bus_max"] == 0
        and not native_v1328["timing_wlan0_seen"]
    )
    derived = {
        "android_pre_cnss_provider_chain": android_pre_cnss_provider_chain,
        "native_observe_only_no_wlfw": native_observe_only_no_wlfw,
        "native_missing_pre_cnss_provider_chain": native_missing_pre_cnss_provider_chain,
        "late_per_proxy_not_sufficient": late_per_proxy_not_sufficient,
        "ranked_missing_input": "pre-CNSS PM/provider chain" if android_pre_cnss_provider_chain else "unranked",
    }
    if (
        android_pre_cnss_provider_chain
        and native_observe_only_no_wlfw
        and native_missing_pre_cnss_provider_chain
        and late_per_proxy_not_sufficient
    ):
        return (
            "v1336-pre-cnss-provider-order-gap",
            True,
            "Android starts pm_proxy_helper/per_mgr/per_proxy, QRTR/RFS/pd-mapper companions, and cnss_diag before cnss-daemon and WLFW; V1335 observe-only omitted the pre-CNSS provider chain, while V1328 showed late per_proxy after CNSS is not sufficient",
            "V1337 should add a bounded Android-order pre-CNSS provider observe-only gate: start service-manager/provider surface, pm_proxy_helper, per_mgr, per_proxy, companion services, then mdm_helper/cnss_diag/cnss-daemon, while keeping /dev/subsys_esoc0 closed and forbidding Wi-Fi HAL/scan/connect",
            derived,
        )
    if android_pre_cnss_provider_chain and native_observe_only_no_wlfw:
        return (
            "v1336-pre-cnss-provider-candidate-unproven",
            True,
            f"partial derived={derived}",
            "inspect V1328/V1335 provider order evidence before implementing the next live gate",
            derived,
        )
    return (
        "v1336-input-incomplete",
        False,
        f"derived={derived}",
        "repair V1331/V1328/V1335 inputs before selecting the next Wi-Fi gate",
        derived,
    )


def render_summary(manifest: dict[str, Any]) -> str:
    android = manifest["android"]
    native_v1335 = manifest["native_v1335"]
    native_v1328 = manifest["native_v1328"]
    boot_rows = [
        [item["key"], "" if item["time_s"] is None else f"{item['time_s']:.6f}"]
        for item in android["boot_order"]
    ]
    derived_rows = [[key, value] for key, value in manifest["derived"].items()]
    native_rows = [
        ["v1335_decision", native_v1335["decision"]],
        ["v1335_observe_only_gate", native_v1335["observe_only_gate"]],
        ["v1335_cnss_daemon_started", native_v1335["cnss_daemon_started"]],
        ["v1335_mdm_helper_esoc0_fd_seen", native_v1335["mdm_helper_esoc0_fd_seen"]],
        ["v1335_wlfw_precondition_observed", native_v1335["wlfw_precondition_observed"]],
        ["v1335_subsys_esoc0_open_attempted", native_v1335["subsys_esoc0_open_attempted"]],
        ["v1335_pm_proxy_helper_started", native_v1335["pm_proxy_helper_started"]],
        ["v1335_per_proxy_started", native_v1335["per_proxy_started"]],
        ["v1328_decision", native_v1328["decision"]],
        ["v1328_per_proxy_initial_start_executed", native_v1328["per_proxy_initial_start_executed"]],
        ["v1328_late_per_proxy_started", native_v1328["late_per_proxy_started"]],
        ["v1328_timing_wlfw_kmsg_max", native_v1328["timing_wlfw_kmsg_max"]],
        ["v1328_timing_ks_process_max", native_v1328["timing_ks_process_max"]],
        ["v1328_timing_mhi_bus_max", native_v1328["timing_mhi_bus_max"]],
    ]
    android_rows = [
        ["v1331_decision", android["decision"]],
        ["wlfw_before_esoc", android["wlfw_before_esoc"]],
        ["pm_proxy_helper_before_per_mgr", android["pm_proxy_helper_before_per_mgr"]],
        ["per_proxy_before_cnss_daemon", android["per_proxy_before_cnss_daemon"]],
        ["all_companions_before_cnss_daemon", android["all_companions_before_cnss_daemon"]],
        ["cnss_diag_before_cnss_daemon", android["cnss_diag_before_cnss_daemon"]],
        ["mdm_helper_before_cnss_daemon", android["mdm_helper_before_cnss_daemon"]],
    ]
    return "\n".join([
        "# V1336 Android Pre-CNSS Provider Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        "",
        "## Derived",
        "",
        markdown_table(["field", "value"], derived_rows),
        "",
        "## Android V1331",
        "",
        markdown_table(["field", "value"], android_rows),
        "",
        "## Android Boottime Order",
        "",
        markdown_table(["property", "seconds"], boot_rows),
        "",
        "## Native Comparison",
        "",
        markdown_table(["field", "value"], native_rows),
        "",
        "## Safety",
        "",
        "- host-only classifier; no device command, deploy, actor start, tracefs write, eSoC open/ioctl, PMIC/GPIO write, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, flash, boot image write, or partition write",
        "",
    ])


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    v1331 = load_json(args.v1331_manifest)
    v1328 = load_json(args.v1328_manifest)
    v1335 = load_json(args.v1335_manifest)
    android = extract_android(v1331)
    native_v1328 = extract_v1328(v1328)
    native_v1335 = extract_v1335(v1335)
    decision, pass_ok, reason, next_step, derived = decide(android, native_v1335, native_v1328)
    manifest = {
        "cycle": "v1336",
        "generated_at": now_iso(),
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "inputs": {
            "v1331_manifest": str(args.v1331_manifest),
            "v1328_manifest": str(args.v1328_manifest),
            "v1335_manifest": str(args.v1335_manifest),
        },
        "android": android,
        "native_v1328": native_v1328,
        "native_v1335": native_v1335,
        "derived": derived,
        "device_commands_executed": False,
        "deploy_executed": False,
        "pm_actor_executed": False,
        "cnss_daemon_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "wifi_bringup_executed": False,
        "flash_executed": False,
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
    return 0 if pass_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

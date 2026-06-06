#!/usr/bin/env python3
"""V1332 host-only classifier for Android WLFW-before-eSoC ordering.

V1331 captured Android `wlfw_start` before the first captured
`__subsystem_get(esoc0)` marker, followed by BDF and wlan0. V1328 captured the
native path reaching `mdm_subsys_powerup` with cnss-daemon started but no WLFW,
BDF, MHI, ks, or wlan0 transition. This classifier reconciles those evidence
sets and selects the next non-mutating native gate.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1332-wlfw-before-esoc-classifier")
LATEST_POINTER = Path("tmp/wifi/latest-v1332-wlfw-before-esoc-classifier.txt")
REPORT_PATH = Path("docs/reports/NATIVE_INIT_V1332_WLFW_BEFORE_ESOC_CLASSIFIER_2026-05-31.md")
DEFAULT_V1331 = Path("tmp/wifi/v1331-android-sdx50m-timing-handoff/v1331-android-sdx50m-timing-recapture-run/manifest.json")
DEFAULT_V1331_HANDOFF = Path("tmp/wifi/v1331-android-sdx50m-timing-handoff/manifest.json")
DEFAULT_V1328 = Path("tmp/wifi/v1328-mdm2ap-timing-sampler-live/manifest.json")
DEFAULT_V1329 = Path("tmp/wifi/v1329-android-only-sdx50m-prereq-classifier/manifest.json")

FORBIDDEN_FLAGS = (
    "device_commands_executed",
    "device_mutations",
    "daemon_start_executed",
    "service_manager_start_executed",
    "wifi_hal_start_executed",
    "wlan_driver_state_write_executed",
    "scan_connect_executed",
    "credential_use_executed",
    "dhcp_route_executed",
    "wifi_bringup_executed",
    "external_ping_executed",
    "pmic_write_executed",
    "gpio_line_request_executed",
    "direct_esoc_ioctl_executed",
    "live_esoc_notify_executed",
    "flash_executed",
    "partition_write_executed",
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def load_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {}
    try:
        payload = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def bool_value(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on", "pass"}
    return False


def int_value(value: Any, fallback: int = 0) -> int:
    try:
        return int(str(value), 0)
    except (TypeError, ValueError):
        return fallback


def float_or_none(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(str(value))
    except (TypeError, ValueError):
        return None


def nested(mapping: dict[str, Any], *keys: str) -> Any:
    value: Any = mapping
    for key in keys:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value


def host_only_clear(manifest: dict[str, Any]) -> bool:
    return all(not bool_value(manifest.get(flag)) for flag in FORBIDDEN_FLAGS)


def summarize_v1331(manifest: dict[str, Any], handoff: dict[str, Any]) -> dict[str, Any]:
    summary = manifest.get("android_summary") or {}
    first_times = summary.get("first_times") or {}
    counts = summary.get("counts") or {}
    process_flags = summary.get("process_flags") or {}
    return {
        "decision": manifest.get("decision", ""),
        "handoff_decision": handoff.get("decision", ""),
        "pass": bool_value(manifest.get("pass")) and bool_value(handoff.get("pass")),
        "boot_completed": bool_value(summary.get("boot_completed")),
        "response_present": bool_value(summary.get("response_present")),
        "all_commands_ok": bool_value(summary.get("all_commands_ok")),
        "wlfw_time": float_or_none(first_times.get("wlfw")),
        "esoc_time": float_or_none(first_times.get("subsys_get_esoc0")),
        "bdf_time": float_or_none(first_times.get("bdf")),
        "wlan0_time": float_or_none(first_times.get("wlan0")),
        "icnss_qmi_time": float_or_none(first_times.get("icnss_qmi")),
        "wlfw_count": int_value(counts.get("wlfw")),
        "bdf_count": int_value(counts.get("bdf")),
        "wlan0_count": int_value(counts.get("wlan0")),
        "subsys_esoc0_count": int_value(counts.get("subsys_get_esoc0")),
        "pcie_count": int_value(counts.get("pcie_rc1")) + int_value(counts.get("pcie_l0")),
        "mhi_count": int_value(counts.get("mhi")) + int_value(counts.get("mhi_pipe")),
        "fd_esoc0_seen": bool_value(process_flags.get("fd_esoc0_seen")),
        "fd_subsys_modem_seen": bool_value(process_flags.get("fd_subsys_modem_seen")),
        "handoff_wifi": bool_value(handoff.get("wifi_bringup_executed")),
        "handoff_external_ping": bool_value(handoff.get("external_ping_executed")),
    }


def summarize_v1328(manifest: dict[str, Any]) -> dict[str, Any]:
    sampler = manifest.get("response_sampler") or {}
    pm_observer = manifest.get("pm_service_trigger_observer") or {}
    parity = manifest.get("mdm_helper_ks_mhi_parity") or {}
    thread = manifest.get("thread_analysis") or {}
    order = str(pm_observer.get("order", ""))
    return {
        "decision": manifest.get("decision", ""),
        "pass": bool_value(manifest.get("pass")),
        "powerup_seen": bool_value(sampler.get("timing_pm_service_powerup_seen")),
        "sample_count": int_value(sampler.get("timing_sample_count")),
        "wlfw_kmsg_max": int_value(sampler.get("timing_wlfw_kmsg_max"), -1),
        "wlan0_seen": bool_value(sampler.get("timing_wlan0_seen")),
        "bdf_or_wlfw_seen": bool_value(parity.get("wlfw_or_wlan0_present")),
        "mhi_bus_max": int_value(sampler.get("timing_mhi_bus_max"), -1),
        "ks_process_max": int_value(sampler.get("timing_ks_process_max"), -1),
        "mhi_pipe_seen": bool_value(sampler.get("timing_mhi_pipe_seen")),
        "gpio142_delta": int_value(sampler.get("timing_gpio142_irq_delta"), -1),
        "errfatal_delta": int_value(sampler.get("timing_errfatal_irq_delta"), -1),
        "late_per_proxy_started": bool_value(pm_observer.get("late_per_proxy_started")),
        "vndservice_provider_seen": bool_value(pm_observer.get("vndservice_provider_seen")),
        "order": order,
        "cnss_before_mdm_helper": "cnss_daemon,mdm_helper" in order,
        "cnss_before_late_per_proxy": "cnss_daemon,mdm_helper,late_per_proxy" in order,
        "cnss_registered_sdx50m": bool_value(thread.get("cnss_registered_sdx50m")),
        "cnss_registered_modem": bool_value(thread.get("cnss_registered_modem")),
        "cnss_daemon_start_executed": str(nested(manifest, "lower_trace", "cnss_daemon_start_executed") or "") == "1",
    }


def summarize_v1329(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "decision": manifest.get("decision", ""),
        "pass": bool_value(manifest.get("pass")),
        "reason": str(manifest.get("reason", "")),
    }


def check(name: str, passed: bool, detail: str, next_step: str = "") -> dict[str, str]:
    return {
        "name": name,
        "status": "pass" if passed else "blocked",
        "detail": detail,
        "next_step": next_step,
    }


def ordered(*values: float | None) -> bool:
    if any(value is None for value in values):
        return False
    numbers = [float(value) for value in values if value is not None]
    return all(left < right for left, right in zip(numbers, numbers[1:]))


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    v1331 = summarize_v1331(load_json(args.v1331_manifest), load_json(args.v1331_handoff_manifest))
    v1328 = summarize_v1328(load_json(args.v1328_manifest))
    v1329 = summarize_v1329(load_json(args.v1329_manifest))

    android_ordering = (
        v1331["pass"]
        and v1331["decision"] == "v1331-android-wlfw-before-subsys-esoc0"
        and v1331["boot_completed"]
        and v1331["response_present"]
        and ordered(v1331["wlfw_time"], v1331["esoc_time"], v1331["bdf_time"], v1331["wlan0_time"])
    )
    android_response_chain = (
        v1331["wlfw_count"] > 0
        and v1331["bdf_count"] > 0
        and v1331["wlan0_count"] > 0
        and v1331["subsys_esoc0_count"] > 0
    )
    native_negative_window = (
        v1328["pass"]
        and v1328["decision"] == "v1328-mdm2ap-timing-full-window-no-transition"
        and v1328["powerup_seen"]
        and v1328["sample_count"] >= 120
        and v1328["wlfw_kmsg_max"] == 0
        and not v1328["bdf_or_wlfw_seen"]
        and not v1328["wlan0_seen"]
        and v1328["mhi_bus_max"] == 0
        and v1328["ks_process_max"] == 0
        and not v1328["mhi_pipe_seen"]
        and v1328["gpio142_delta"] == 0
        and v1328["errfatal_delta"] == 0
    )
    native_started_cnss_before_esoc_gate = (
        v1328["cnss_before_mdm_helper"]
        and v1328["cnss_before_late_per_proxy"]
        and v1328["late_per_proxy_started"]
        and v1328["vndservice_provider_seen"]
        and v1328["cnss_registered_sdx50m"]
    )
    prior_closed = (
        v1329["pass"]
        and v1329["decision"] == "v1329-android-prereq-is-earlier-sdx50m-response-sequence"
    )
    safety_clear = host_only_clear({
        "device_commands_executed": False,
        "device_mutations": False,
        "daemon_start_executed": False,
        "service_manager_start_executed": False,
        "wifi_hal_start_executed": False,
        "wlan_driver_state_write_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "wifi_bringup_executed": False,
        "external_ping_executed": False,
        "pmic_write_executed": False,
        "gpio_line_request_executed": False,
        "direct_esoc_ioctl_executed": False,
        "live_esoc_notify_executed": False,
        "flash_executed": False,
        "partition_write_executed": False,
    })

    checks = [
        check("android-wlfw-before-esoc-ordering", android_ordering, f"wlfw={v1331['wlfw_time']} esoc0={v1331['esoc_time']} bdf={v1331['bdf_time']} wlan0={v1331['wlan0_time']}"),
        check("android-response-chain-present", android_response_chain, f"wlfw={v1331['wlfw_count']} bdf={v1331['bdf_count']} wlan0={v1331['wlan0_count']} esoc0={v1331['subsys_esoc0_count']}"),
        check("native-v1328-no-response-window", native_negative_window, f"powerup={v1328['powerup_seen']} samples={v1328['sample_count']} wlfw={v1328['wlfw_kmsg_max']} mhi={v1328['mhi_bus_max']} ks={v1328['ks_process_max']} wlan0={v1328['wlan0_seen']}"),
        check("native-cnss-before-esoc-gate", native_started_cnss_before_esoc_gate, f"order={v1328['order']} registered_sdx50m={v1328['cnss_registered_sdx50m']}"),
        check("prior-android-prereq-branch-closed", prior_closed, f"v1329={v1329['decision']}"),
        check("guardrails-clear", safety_clear, "host-only classifier; no device command, mutation, Wi-Fi action, credential, DHCP, external ping, or flash"),
    ]
    passed = all(row["status"] == "pass" for row in checks)
    if passed:
        decision = "v1332-native-missing-early-wlfw-provider-state"
        reason = (
            "Android reaches WLFW userspace before captured esoc0 and then BDF/wlan0, "
            "while native starts cnss-daemon before the eSoC gate yet records no WLFW/BDF/MHI/ks/wlan0 during the full mdm_subsys_powerup window"
        )
        next_step = (
            "V1333 should run a bounded native early-CNSS WLFW parity observer before per_proxy/eSoC trigger, "
            "capturing cnss-daemon stdout/stderr, properties, fds, and kmsg WLFW markers without Wi-Fi HAL/scan/connect"
        )
    elif android_ordering and native_negative_window:
        decision = "v1332-cnss-provider-detail-needed"
        reason = "Android ordering and native no-response are proven, but native cnss/provider parity is incomplete"
        next_step = "classify native cnss-daemon/provider details before live mutation"
    else:
        decision = "v1332-evidence-incomplete"
        reason = "required V1331 or V1328 evidence is missing or inconsistent"
        next_step = "refresh the missing host-only evidence before native live gates"

    return {
        "cycle": "v1332",
        "command": args.command,
        "generated_at": now_iso(),
        "host": collect_host_metadata(),
        "inputs": {
            "v1331_manifest": str(repo_path(args.v1331_manifest)),
            "v1331_handoff_manifest": str(repo_path(args.v1331_handoff_manifest)),
            "v1328_manifest": str(repo_path(args.v1328_manifest)),
            "v1329_manifest": str(repo_path(args.v1329_manifest)),
        },
        "v1331": v1331,
        "v1328": v1328,
        "v1329": v1329,
        "checks": checks,
        "decision": decision,
        "pass": passed,
        "reason": reason,
        "next_step": next_step,
        **{flag: False for flag in FORBIDDEN_FLAGS},
    }


def render_summary(manifest: dict[str, Any]) -> str:
    rows = [[row["name"], row["status"], row["detail"], row["next_step"]] for row in manifest["checks"]]
    v1331 = manifest["v1331"]
    v1328 = manifest["v1328"]
    return "\n".join([
        "# V1332 WLFW-before-eSoC Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        "",
        "## Checks",
        "",
        markdown_table(["name", "status", "detail", "next"], rows),
        "",
        "## Ordering",
        "",
        markdown_table(["surface", "Android V1331", "Native V1328"], [
            ["WLFW", f"first={v1331['wlfw_time']} count={v1331['wlfw_count']}", f"kmsg_max={v1328['wlfw_kmsg_max']}"],
            ["eSoC trigger", f"subsys_get_esoc0={v1331['esoc_time']}", f"powerup={v1328['powerup_seen']}"],
            ["BDF/wlan0", f"bdf={v1331['bdf_time']} wlan0={v1331['wlan0_time']}", f"wlan0={v1328['wlan0_seen']}"],
            ["native order", "-", v1328["order"]],
        ]),
        "",
        "## Safety",
        "",
        "- host-only classifier",
        "- no device command, helper deploy, actor start, tracefs write, live eSoC ioctl/notify, PMIC/GPIO write, Wi-Fi HAL, scan/connect, credential use, DHCP/routes, external ping, flash, boot image write, or partition write",
        "",
    ])


def render_report(manifest: dict[str, Any]) -> str:
    v1331 = manifest["v1331"]
    v1328 = manifest["v1328"]
    return "\n".join([
        "# Native Init V1332 WLFW-before-eSoC Classifier",
        "",
        "## Summary",
        "",
        "- Cycle: `V1332`",
        "- Type: host-only classifier",
        f"- Decision: `{manifest['decision']}`",
        f"- Result: {'PASS' if manifest['pass'] else 'FAIL'}",
        "- Evidence:",
        "  - `tmp/wifi/v1332-wlfw-before-esoc-classifier/manifest.json`",
        "  - `tmp/wifi/v1332-wlfw-before-esoc-classifier/summary.md`",
        "- Script: `scripts/revalidation/native_wifi_wlfw_before_esoc_classifier_v1332.py`",
        "",
        "V1332 compares the Android-positive V1331 timeline with the native V1328",
        "full-window no-response evidence. Android recorded `wlfw_start` before the",
        "first captured `__subsystem_get(esoc0)`, then BDF download and `wlan0`.",
        "Native started `cnss_daemon` before `mdm_helper`/late `per_proxy` and reached",
        "`mdm_subsys_powerup`, but still recorded no WLFW/BDF/MHI/ks/`wlan0`.",
        "",
        "## Key Evidence",
        "",
        markdown_table(["item", "value"], [
            ["android_wlfw_time", str(v1331["wlfw_time"])],
            ["android_esoc_time", str(v1331["esoc_time"])],
            ["android_bdf_time", str(v1331["bdf_time"])],
            ["android_wlan0_time", str(v1331["wlan0_time"])],
            ["native_order", v1328["order"]],
            ["native_wlfw_kmsg_max", str(v1328["wlfw_kmsg_max"])],
            ["native_mhi_bus_max", str(v1328["mhi_bus_max"])],
            ["native_ks_process_max", str(v1328["ks_process_max"])],
        ]),
        "",
        "## Decision",
        "",
        "The next native gate should not be a longer wait after `mdm_subsys_powerup`.",
        "It should prove whether native `cnss-daemon` can reach the same early WLFW",
        "userspace state that Android reaches before the captured eSoC trigger.",
        "",
        "## Safety",
        "",
        "Host-only classifier. No device command, helper deploy, actor start, tracefs",
        "write, live eSoC ioctl/notify, PMIC/GPIO write, Wi-Fi HAL start, scan/connect,",
        "credential use, DHCP/routes, external ping, flash, boot image write, or",
        "partition write occurred.",
        "",
    ])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v1331-manifest", type=Path, default=DEFAULT_V1331)
    parser.add_argument("--v1331-handoff-manifest", type=Path, default=DEFAULT_V1331_HANDOFF)
    parser.add_argument("--v1328-manifest", type=Path, default=DEFAULT_V1328)
    parser.add_argument("--v1329-manifest", type=Path, default=DEFAULT_V1329)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args)
    if args.command == "plan":
        manifest["decision"] = "v1332-wlfw-before-esoc-classifier-plan-ready"
        manifest["pass"] = True
        manifest["reason"] = "plan-only; no device command or live action"
        manifest["next_step"] = "run V1332 host-only classifier"
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    if args.command == "run":
        repo_path(REPORT_PATH).write_text(render_report(manifest), encoding="utf-8")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

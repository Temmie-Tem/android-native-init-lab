#!/usr/bin/env python3
"""V1348 host-only Android WLFW request path classifier.

Reconciles V1345's native lower-route no-response result with V1347's Android
earliest-response recapture. This script is host-only: it reads existing
manifests, writes evidence/report files, and executes no device command.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1348-android-wlfw-request-path-classifier")
LATEST_POINTER = Path("tmp/wifi/latest-v1348-android-wlfw-request-path-classifier.txt")
REPORT_PATH = Path("docs/reports/NATIVE_INIT_V1348_ANDROID_WLFW_REQUEST_PATH_CLASSIFIER_2026-06-01.md")

DEFAULT_V1345 = Path("tmp/wifi/v1345-current-route-mdm2ap-timing-sampler-live/manifest.json")
DEFAULT_V1346 = Path("tmp/wifi/v1346-android-only-response-prereq-reclassifier/manifest.json")
DEFAULT_V1347_HANDOFF = Path("tmp/wifi/v1347-android-earliest-response-handoff/manifest.json")
DEFAULT_V1347_RECAPTURE = Path(
    "tmp/wifi/v1347-android-earliest-response-handoff/"
    "v1347-android-earliest-response-recapture-run/manifest.json"
)

FORBIDDEN_ACTIVE_FLAGS = (
    "wifi_hal_start_executed",
    "wificond_start_executed",
    "scan_connect_executed",
    "credential_use_executed",
    "dhcp_route_executed",
    "external_ping_executed",
    "wifi_bringup_executed",
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).astimezone().isoformat(timespec="seconds")


def read_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {"_exists": False, "_path": str(path)}
    try:
        value = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {"_exists": True, "_path": str(path), "_json_error": str(exc)}
    if not isinstance(value, dict):
        return {"_exists": True, "_path": str(path), "_json_error": "top-level JSON is not an object"}
    value["_exists"] = True
    value["_path"] = str(path)
    return value


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


def float_value(value: Any, fallback: float | None = None) -> float | None:
    if value is None:
        return fallback
    try:
        return float(str(value))
    except (TypeError, ValueError):
        return fallback


def check(name: str, passed: bool, detail: str) -> dict[str, Any]:
    return {"name": name, "pass": bool(passed), "detail": detail}


def nested(data: dict[str, Any], *keys: str) -> Any:
    value: Any = data
    for key in keys:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value


def summarize_v1345(manifest: dict[str, Any]) -> dict[str, Any]:
    sampler = manifest.get("response_sampler") or {}
    current_route = manifest.get("current_route") or {}
    thread = manifest.get("thread_analysis") or {}
    return {
        "exists": bool_value(manifest.get("_exists")),
        "decision": str(manifest.get("decision", "")),
        "pass": bool_value(manifest.get("pass")),
        "reason": str(manifest.get("reason", "")),
        "private_route": bool_value(current_route.get("private_flag_in_child_script")),
        "private_cnss_expected": str((manifest.get("private_cnss_daemon") or {}).get("expected_c_string", "")),
        "cnss_registered_sdx50m": bool_value(thread.get("cnss_registered_sdx50m")),
        "powerup_seen": bool_value(sampler.get("timing_pm_service_powerup_seen")),
        "sample_count": int_value(sampler.get("timing_sample_count")),
        "gpio142_delta": int_value(sampler.get("timing_gpio142_irq_delta")),
        "errfatal_delta": int_value(sampler.get("timing_errfatal_irq_delta")),
        "pcie_transition": bool_value(sampler.get("timing_pcie_rc1_transition_seen")),
        "pci_dev_max": int_value(sampler.get("timing_pci_dev_max")),
        "mhi_bus_max": int_value(sampler.get("timing_mhi_bus_max")),
        "mhi_pipe_seen": bool_value(sampler.get("timing_mhi_pipe_seen")),
        "ks_process_max": int_value(sampler.get("timing_ks_process_max")),
        "wlfw_kmsg_max": int_value(sampler.get("timing_wlfw_kmsg_max")),
        "wlan0_seen": bool_value(sampler.get("timing_wlan0_seen")),
        "safety_clear": bool_value(current_route.get("timing_safety_clear")),
    }


def summarize_v1346(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "exists": bool_value(manifest.get("_exists")),
        "decision": str(manifest.get("decision", "")),
        "pass": bool_value(manifest.get("pass")),
        "reason": str(manifest.get("reason", "")),
        "next_step": str(manifest.get("next_step", "")),
    }


def capture_status(manifest: dict[str, Any], name: str) -> dict[str, Any]:
    for capture in manifest.get("captures") or []:
        if capture.get("name") == name:
            return {
                "ok": bool_value(capture.get("ok")),
                "rc": capture.get("rc"),
                "duration_sec": float_value(capture.get("duration_sec"), 0.0),
            }
    return {"ok": False, "rc": None, "duration_sec": 0.0}


def summarize_v1347(handoff: dict[str, Any], recapture: dict[str, Any]) -> dict[str, Any]:
    summary = recapture.get("android_summary") or {}
    counts = summary.get("counts") or {}
    first_times = summary.get("first_times") or {}
    surface = summary.get("surface_flags") or {}
    process = summary.get("process_flags") or {}
    process_capture = capture_status(recapture, "v1347-process-fds")
    return {
        "handoff_exists": bool_value(handoff.get("_exists")),
        "recapture_exists": bool_value(recapture.get("_exists")),
        "handoff_decision": str(handoff.get("decision", "")),
        "handoff_pass": bool_value(handoff.get("pass")),
        "handoff_reason": str(handoff.get("reason", "")),
        "recapture_decision": str(recapture.get("decision", "")),
        "recapture_pass": bool_value(recapture.get("pass")),
        "recapture_reason": str(recapture.get("reason", "")),
        "boot_completed": bool_value(summary.get("boot_completed")),
        "response_present": bool_value(summary.get("response_present")),
        "all_commands_ok": bool_value(summary.get("all_commands_ok")),
        "wlfw_count": int_value(counts.get("wlfw")),
        "icnss_qmi_count": int_value(counts.get("icnss_qmi")),
        "bdf_count": int_value(counts.get("bdf")),
        "wlan_fw_ready_count": int_value(counts.get("wlan_fw_ready")),
        "wlan0_count": int_value(counts.get("wlan0")),
        "subsys_get_esoc0_count": int_value(counts.get("subsys_get_esoc0")),
        "pcie_rc1_count": int_value(counts.get("pcie_rc1")),
        "pcie_l0_count": int_value(counts.get("pcie_l0")),
        "mhi_count": int_value(counts.get("mhi")),
        "mhi_pipe_count": int_value(counts.get("mhi_pipe")),
        "ks_count": int_value(counts.get("ks")),
        "wlfw_time": float_value(first_times.get("wlfw")),
        "subsys_get_esoc0_time": float_value(first_times.get("subsys_get_esoc0")),
        "icnss_qmi_time": float_value(nested(summary, "first", "icnss_qmi", "timestamp")),
        "bdf_time": float_value(first_times.get("bdf")),
        "wlan_fw_ready_time": float_value(nested(summary, "first", "wlan_fw_ready", "timestamp")),
        "wlan0_time": float_value(first_times.get("wlan0")),
        "pci_devices_seen": bool_value(surface.get("pci_devices_seen")),
        "mhi_devices_seen": bool_value(surface.get("mhi_devices_seen")),
        "mhi_devnode_seen": bool_value(surface.get("mhi_devnode_seen")),
        "wlan0_sysfs_seen": bool_value(surface.get("wlan0_sysfs_seen")),
        "ks_seen": bool_value(process.get("ks_seen")),
        "fd_subsys_esoc0_seen": bool_value(process.get("fd_subsys_esoc0_seen")),
        "fd_mhi_pipe_seen": bool_value(process.get("fd_mhi_pipe_seen")),
        "process_fds_ok": bool_value(process_capture.get("ok")),
        "process_fds_duration_sec": float_value(process_capture.get("duration_sec"), 0.0),
    }


def forbidden_hits(manifests: dict[str, dict[str, Any]]) -> list[str]:
    hits: list[str] = []
    for name, manifest in manifests.items():
        for flag in FORBIDDEN_ACTIVE_FLAGS:
            if bool_value(manifest.get(flag)):
                hits.append(f"{name}.{flag}")
    return hits


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    raw = {
        "v1345": read_json(args.v1345_manifest),
        "v1346": read_json(args.v1346_manifest),
        "v1347_handoff": read_json(args.v1347_handoff_manifest),
        "v1347_recapture": read_json(args.v1347_recapture_manifest),
    }
    v1345 = summarize_v1345(raw["v1345"])
    v1346 = summarize_v1346(raw["v1346"])
    v1347 = summarize_v1347(raw["v1347_handoff"], raw["v1347_recapture"])
    forbidden = forbidden_hits(raw)

    native_lower_no_transition = (
        v1345["exists"]
        and v1345["pass"]
        and v1345["decision"] == "v1345-current-route-mdm2ap-full-window-no-transition"
        and v1345["private_route"]
        and v1345["private_cnss_expected"] == "SDX50M"
        and v1345["cnss_registered_sdx50m"]
        and v1345["powerup_seen"]
        and v1345["sample_count"] >= 120
        and v1345["gpio142_delta"] == 0
        and v1345["errfatal_delta"] == 0
        and not v1345["pcie_transition"]
        and v1345["pci_dev_max"] == 0
        and v1345["mhi_bus_max"] == 0
        and not v1345["mhi_pipe_seen"]
        and v1345["ks_process_max"] == 0
        and v1345["wlfw_kmsg_max"] == 0
        and not v1345["wlan0_seen"]
        and v1345["safety_clear"]
    )
    recapture_branch_expected = (
        v1346["exists"]
        and v1346["pass"]
        and v1346["decision"] == "v1346-need-android-earliest-response-recapture"
    )
    android_positive_chain = (
        v1347["handoff_exists"]
        and v1347["recapture_exists"]
        and v1347["handoff_pass"]
        and v1347["recapture_pass"]
        and v1347["boot_completed"]
        and v1347["response_present"]
        and v1347["wlfw_count"] > 0
        and v1347["icnss_qmi_count"] > 0
        and v1347["bdf_count"] > 0
        and v1347["wlan_fw_ready_count"] > 0
        and v1347["wlan0_count"] > 0
    )
    wlfw_before_captured_esoc0 = (
        isinstance(v1347["wlfw_time"], float)
        and isinstance(v1347["subsys_get_esoc0_time"], float)
        and v1347["wlfw_time"] < v1347["subsys_get_esoc0_time"]
    )
    public_lower_markers_incomplete = (
        v1347["pcie_rc1_count"] == 0
        and v1347["pcie_l0_count"] == 0
        and v1347["mhi_count"] == 0
        and v1347["mhi_pipe_count"] == 0
        and v1347["ks_count"] == 0
        and not v1347["pci_devices_seen"]
        and not v1347["mhi_devices_seen"]
        and not v1347["mhi_devnode_seen"]
        and v1347["wlan0_sysfs_seen"]
    )
    process_fd_limited = not v1347["process_fds_ok"]

    checks = [
        check(
            "v1345-native-lower-no-transition",
            native_lower_no_transition,
            f"powerup={v1345['powerup_seen']} samples={v1345['sample_count']} gpio142={v1345['gpio142_delta']} pcie={v1345['pcie_transition']} mhi={v1345['mhi_bus_max']} ks={v1345['ks_process_max']} wlfw={v1345['wlfw_kmsg_max']} wlan0={v1345['wlan0_seen']}",
        ),
        check(
            "v1346-recapture-branch-confirmed",
            recapture_branch_expected,
            f"decision={v1346['decision']}",
        ),
        check(
            "v1347-android-positive-chain",
            android_positive_chain,
            f"wlfw={v1347['wlfw_time']} qmi={v1347['icnss_qmi_time']} bdf={v1347['bdf_time']} fw_ready={v1347['wlan_fw_ready_time']} wlan0={v1347['wlan0_time']}",
        ),
        check(
            "v1347-wlfw-before-captured-esoc0",
            wlfw_before_captured_esoc0,
            f"wlfw={v1347['wlfw_time']} esoc0={v1347['subsys_get_esoc0_time']}",
        ),
        check(
            "v1347-public-lower-markers-incomplete",
            public_lower_markers_incomplete,
            f"pcie={v1347['pcie_rc1_count']}/{v1347['pcie_l0_count']} mhi={v1347['mhi_count']} pipe={v1347['mhi_pipe_count']} ks={v1347['ks_count']} wlan0_sysfs={v1347['wlan0_sysfs_seen']}",
        ),
        check(
            "guardrails-clear",
            not forbidden,
            "no active Wi-Fi HAL, scan/connect, credential, DHCP/route, external ping, or Wi-Fi bring-up flag in classifier inputs",
        ),
    ]

    if forbidden:
        decision = "v1348-forbidden-action-detected"
        passed = False
        reason = "forbidden active Wi-Fi/network actions were present in reconciled evidence: " + ", ".join(forbidden)
        next_step = "stop and audit evidence before more Wi-Fi path work"
    elif not all(item["pass"] for item in checks[:3] + checks[5:]):
        decision = "v1348-evidence-incomplete"
        passed = False
        reason = "required V1345/V1346/V1347 evidence is missing or inconsistent"
        next_step = "refresh the failed host-only evidence source before live work"
    elif wlfw_before_captured_esoc0:
        decision = "v1348-cnss-wlfw-request-path-before-lower-mutation"
        passed = True
        reason = (
            "Android reaches cnss-daemon wlfw_start before the captured subsys_get(esoc0) marker and then reaches "
            "ICNSS QMI, BDF, firmware-ready, and wlan0; native already reaches mdm_subsys_powerup with no lower response"
        )
        next_step = (
            "V1349 should classify Android-vs-native cnss-daemon/WLFW runtime prerequisites before any PMIC/GPIO/GDSC/eSoC mutation"
        )
    elif public_lower_markers_incomplete:
        decision = "v1348-cnss-wlfw-request-path-likely-but-order-incomplete"
        passed = True
        reason = (
            "Android response chain is positive but public lower PCIe/MHI/ks markers remain incomplete, so the safest next branch remains CNSS/WLFW prerequisite analysis"
        )
        next_step = "V1349 should inspect CNSS/WLFW runtime prerequisites and only recapture lower markers if a concrete missing surface is identified"
    else:
        decision = "v1348-android-lower-order-captured-needs-native-parity"
        passed = True
        reason = "Android lower ordering is concrete enough to design a native parity observer"
        next_step = "plan a narrow host-only or observe-only native parity gate for the captured Android lower marker"

    if args.command == "plan":
        decision = "v1348-android-wlfw-request-path-plan-ready"
        passed = True
        reason = "plan-only; no device command or live action executed"
        next_step = "run the V1348 host-only classifier against V1345/V1346/V1347 evidence"

    return {
        "cycle": "v1348",
        "command": args.command,
        "generated_at": now_iso(),
        "host": collect_host_metadata(),
        "inputs": {
            "v1345": str(repo_path(args.v1345_manifest)),
            "v1346": str(repo_path(args.v1346_manifest)),
            "v1347_handoff": str(repo_path(args.v1347_handoff_manifest)),
            "v1347_recapture": str(repo_path(args.v1347_recapture_manifest)),
        },
        "v1345": v1345,
        "v1346": v1346,
        "v1347": v1347,
        "checks": checks,
        "forbidden_hits": forbidden,
        "process_fd_limited": process_fd_limited,
        "public_lower_markers_incomplete": public_lower_markers_incomplete,
        "decision": decision,
        "pass": passed,
        "reason": reason,
        "next_step": next_step,
        "device_commands_executed": False,
        "device_mutations": False,
        "helper_deploy_executed": False,
        "daemon_start_executed": False,
        "pm_actor_executed": False,
        "tracefs_write_executed": False,
        "sysfs_write_executed": False,
        "debugfs_write_executed": False,
        "direct_esoc_ioctl_executed": False,
        "live_esoc_ioctl_executed": False,
        "live_esoc_notify_executed": False,
        "pmic_write_executed": False,
        "gpio_line_request_executed": False,
        "gdsc_write_executed": False,
        "wifi_hal_start_executed": False,
        "wificond_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "wifi_bringup_executed": False,
        "flash_executed": False,
        "boot_image_write_executed": False,
        "partition_write_executed": False,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    check_rows = [[item["name"], item["pass"], item["detail"]] for item in manifest["checks"]]
    v1345 = manifest["v1345"]
    v1347 = manifest["v1347"]
    basis_rows = [
        [
            "native V1345",
            f"powerup={v1345['powerup_seen']} samples={v1345['sample_count']} GPIO142={v1345['gpio142_delta']} PCIe={v1345['pcie_transition']} MHI={v1345['mhi_bus_max']} WLFW={v1345['wlfw_kmsg_max']} wlan0={v1345['wlan0_seen']}",
        ],
        [
            "Android V1347",
            f"WLFW={v1347['wlfw_time']}s eSoC={v1347['subsys_get_esoc0_time']}s QMI={v1347['icnss_qmi_time']}s BDF={v1347['bdf_time']}s FW-ready={v1347['wlan_fw_ready_time']}s wlan0={v1347['wlan0_time']}s",
        ],
        [
            "public lower surfaces",
            f"PCIe={v1347['pcie_rc1_count']}/{v1347['pcie_l0_count']} MHI={v1347['mhi_count']} pipe={v1347['mhi_pipe_count']} ks={v1347['ks_count']} process_fd_ok={v1347['process_fds_ok']}",
        ],
        ["next safe branch", manifest["next_step"]],
    ]
    return "\n".join([
        "# V1348 Android WLFW Request Path Classifier",
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
        markdown_table(["check", "pass", "detail"], check_rows),
        "",
        "## Decision Basis",
        "",
        markdown_table(["surface", "value"], basis_rows),
        "",
        "## Limitation",
        "",
        f"- process_fd_limited: `{manifest['process_fd_limited']}`",
        f"- public_lower_markers_incomplete: `{manifest['public_lower_markers_incomplete']}`",
        "",
        "## Safety",
        "",
        "Host-only classifier. No device command, helper deploy, daemon start, PM actor, tracefs/sysfs/debugfs write, eSoC ioctl/notify, PMIC/GPIO/GDSC write, Wi-Fi HAL, scan/connect, credential, DHCP/route, external ping, flash, boot image write, or partition write was executed.",
        "",
    ])


def render_report(manifest: dict[str, Any]) -> str:
    v1345 = manifest["v1345"]
    v1347 = manifest["v1347"]
    return "\n".join([
        "# Native Init V1348 Android WLFW Request Path Classifier",
        "",
        "## Summary",
        "",
        "- Cycle: `V1348`",
        "- Type: host-only evidence classifier",
        f"- Decision: `{manifest['decision']}`",
        f"- Result: {'PASS' if manifest['pass'] else 'FAIL'}",
        "- Evidence:",
        "  - `tmp/wifi/v1348-android-wlfw-request-path-classifier/manifest.json`",
        "  - `tmp/wifi/v1348-android-wlfw-request-path-classifier/summary.md`",
        "- Script: `scripts/revalidation/native_wifi_android_wlfw_request_path_classifier_v1348.py`",
        "",
        "## Key Facts",
        "",
        markdown_table(["fact", "value"], [
            ["native V1345 lower window", f"powerup={v1345['powerup_seen']} samples={v1345['sample_count']} GPIO142={v1345['gpio142_delta']} errfatal={v1345['errfatal_delta']} PCIe={v1345['pcie_transition']} MHI={v1345['mhi_bus_max']} ks={v1345['ks_process_max']} WLFW={v1345['wlfw_kmsg_max']} wlan0={v1345['wlan0_seen']}"],
            ["Android V1347 response chain", f"WLFW={v1347['wlfw_time']}s eSoC={v1347['subsys_get_esoc0_time']}s QMI={v1347['icnss_qmi_time']}s BDF={v1347['bdf_time']}s FW-ready={v1347['wlan_fw_ready_time']}s wlan0={v1347['wlan0_time']}s"],
            ["Android public lower surfaces", f"PCIe={v1347['pcie_rc1_count']}/{v1347['pcie_l0_count']} MHI={v1347['mhi_count']} pipe={v1347['mhi_pipe_count']} ks={v1347['ks_count']} pci_sysfs={v1347['pci_devices_seen']} mhi_sysfs={v1347['mhi_devices_seen']}"],
            ["V1347 process/fd limitation", f"process_fds_ok={v1347['process_fds_ok']} duration={v1347['process_fds_duration_sec']}s"],
        ]),
        "",
        "## Decision",
        "",
        manifest["reason"],
        "",
        "Do not add PMIC/GPIO/GDSC/eSoC mutation based on V1345 alone. V1347's positive Android anchors are the `cnss-daemon` WLFW request path, ICNSS QMI connection, BDF transfer, firmware-ready event, and `wlan0` creation. The next unit should classify what Android has in the CNSS/WLFW runtime path that native still lacks.",
        "",
        "## Next",
        "",
        manifest["next_step"],
        "",
        "## Safety",
        "",
        "Host-only classifier. No device command, helper deploy, daemon start, PM actor, tracefs/sysfs/debugfs write, eSoC ioctl/notify, PMIC/GPIO/GDSC write, Wi-Fi HAL start, scan/connect, credential use, DHCP/routes, external ping, flash, boot image write, or partition write occurred.",
        "",
    ])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v1345-manifest", type=Path, default=DEFAULT_V1345)
    parser.add_argument("--v1346-manifest", type=Path, default=DEFAULT_V1346)
    parser.add_argument("--v1347-handoff-manifest", type=Path, default=DEFAULT_V1347_HANDOFF)
    parser.add_argument("--v1347-recapture-manifest", type=Path, default=DEFAULT_V1347_RECAPTURE)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def print_result(manifest: dict[str, Any]) -> None:
    print(f"decision: {manifest['decision']}")
    print(f"pass:     {manifest['pass']}")
    print(f"reason:   {manifest['reason']}")
    print(f"next:     {manifest['next_step']}")
    print(f"evidence: {manifest.get('_run_dir')}")


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args)
    manifest["_run_dir"] = str(store.run_dir)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    if args.command == "run":
        write_private_text(repo_path(REPORT_PATH), render_report(manifest))
    print_result(manifest)
    return 0 if manifest.get("pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())

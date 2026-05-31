#!/usr/bin/env python3
"""V1321 host-only image-link reconciliation classifier.

V1320 selected a fail-closed mdm_helper/ks/MHI image-link gate from the latest
post-GPIO135 evidence.  Earlier authoritative evidence already exercised that
branch through V1236-V1239.  This classifier reconciles both evidence sets and
selects the next blocker without running device commands or broadening into
Wi-Fi HAL/connect.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1321-image-link-reconciliation-classifier")
LATEST_POINTER = Path("tmp/wifi/latest-v1321-image-link-reconciliation-classifier.txt")
REPORT_PATH = Path("docs/reports/NATIVE_INIT_V1321_IMAGE_LINK_RECONCILIATION_CLASSIFIER_2026-05-31.md")
DEFAULT_V1320_MANIFEST = Path("tmp/wifi/v1320-mdm-helper-ks-mhi-contract-classifier/manifest.json")
DEFAULT_V1236_MANIFEST = Path("tmp/wifi/v1236-android-ks-runtime-contract-classifier/manifest.json")
DEFAULT_V1238_MANIFEST = Path("tmp/wifi/v1238-late-per-proxy-only-live/manifest.json")
DEFAULT_V1239_MANIFEST = Path("tmp/wifi/v1239-post-esoc0-powerup-gap-classifier/manifest.json")
DEFAULT_V1319_MANIFEST = Path("tmp/wifi/v1319-gpio135-response-gap-classifier/manifest.json")


FORBIDDEN_FLAGS = (
    "wifi_hal_start_executed",
    "scan_connect_executed",
    "credential_use_executed",
    "dhcp_route_executed",
    "external_ping_executed",
    "wifi_bringup_executed",
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
        value = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def bool_value(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on"}
    return False


def int_value(value: Any, fallback: int = 0) -> int:
    try:
        return int(str(value), 0)
    except (TypeError, ValueError):
        return fallback


def all_forbidden_clear(manifest: dict[str, Any]) -> bool:
    return all(not bool_value(manifest.get(flag)) for flag in FORBIDDEN_FLAGS)


def summarize_v1320(manifest: dict[str, Any]) -> dict[str, Any]:
    v1319 = manifest.get("v1319") or {}
    v1318 = manifest.get("v1318") or {}
    return {
        "decision": manifest.get("decision", ""),
        "pass": bool_value(manifest.get("pass")),
        "forbidden_clear": all_forbidden_clear(manifest),
        "native_gpio135_high_count": int_value(v1319.get("gpio135_high_count")),
        "native_gpio142_line_count": int_value(v1319.get("gpio142_line_count")),
        "native_ks_count": int_value(v1318.get("ks_count_window")),
        "native_mhi_pipe_seen": bool_value(v1318.get("mhi_pipe_seen")),
        "android_ks_mhi_pipe": bool_value(v1319.get("android_ks_mhi_pipe")),
        "android_gpio142_irq_count": int_value(v1319.get("android_gpio142_irq_count")),
        "next_step": manifest.get("next_step", ""),
    }


def summarize_v1236(manifest: dict[str, Any]) -> dict[str, Any]:
    android = manifest.get("android_contract") or {}
    native = manifest.get("native_contract") or {}
    return {
        "decision": manifest.get("decision", ""),
        "pass": bool_value(manifest.get("pass")),
        "forbidden_clear": all_forbidden_clear(manifest),
        "per_proxy_before_esoc0": bool_value(android.get("per_proxy_before_esoc0")),
        "pm_service_binder_mdm_subsys_powerup": bool_value(android.get("pm_service_binder_mdm_subsys_powerup")),
        "actor_ks_mhi_pipe": bool_value(android.get("actor_ks_mhi_pipe")),
        "android_gpio142_irq_count": int_value(android.get("gpio142_irq_count")),
        "native_wait_returned": bool_value(native.get("v1232_wait_returned")),
        "native_execve_count": int_value(native.get("v1235_execve_count")),
        "native_ks_count": int_value(native.get("v1235_ks_count")),
        "next_step": manifest.get("next_step", ""),
    }


def summarize_v1238(manifest: dict[str, Any]) -> dict[str, Any]:
    late = manifest.get("late_per_proxy") or {}
    pm_observer = manifest.get("pm_service_trigger_observer") or {}
    parity = manifest.get("mdm_helper_ks_mhi_parity") or {}
    boundary = manifest.get("post_esoc_boundary") or {}
    thread = manifest.get("thread_analysis") or {}
    return {
        "decision": manifest.get("decision", ""),
        "pass": bool_value(manifest.get("pass")),
        "forbidden_clear": all_forbidden_clear(manifest),
        "late_per_proxy_started": bool_value(late.get("started")) or bool_value(pm_observer.get("late_per_proxy_started")),
        "late_per_proxy_gate_positive": bool_value(late.get("gate_positive")) or bool_value(pm_observer.get("late_per_proxy_gate_positive")),
        "pm_service_actor_esoc0_attempt": bool_value(pm_observer.get("pm_service_actor_esoc0_attempt")) or bool_value(parity.get("pm_service_subsys_esoc0_attempt")),
        "mdm_subsys_powerup": bool_value(thread.get("mdm_subsys_powerup_any")),
        "ks_count": int_value(parity.get("ks_count_window")),
        "mhi_pipe_fd_count": int_value(parity.get("mdm_helper_mhi_pipe_count_window")),
        "wlfw_count": int_value(boundary.get("max_dmesg_wlfw_count")),
        "wlan0_seen": bool_value(boundary.get("wlan0_seen")),
        "mdm3_states": boundary.get("mdm3_state_transitions") or [],
        "all_postflight_safe": bool_value(pm_observer.get("all_postflight_safe")),
        "reboot_executed": bool_value(manifest.get("reboot_executed")),
        "next_step": manifest.get("next_step", ""),
    }


def summarize_v1239(manifest: dict[str, Any]) -> dict[str, Any]:
    android = manifest.get("android") or {}
    native = manifest.get("native") or {}
    return {
        "decision": manifest.get("decision", ""),
        "pass": bool_value(manifest.get("pass")),
        "forbidden_clear": all_forbidden_clear(manifest),
        "android_gpio142_irq_count": int_value(android.get("gpio142_irq_count")),
        "android_pcie_rc1_lines": int_value(android.get("pcie_rc1_lines")),
        "android_ks_mhi_pipe": bool_value(android.get("ks_mhi_pipe")),
        "android_wlan0_present": bool_value(android.get("wlan0_present")),
        "native_late_per_proxy_started": bool_value(native.get("late_per_proxy_started")),
        "native_pm_service_esoc0_attempt": bool_value(native.get("pm_service_actor_esoc0_attempt")),
        "native_mdm_subsys_powerup_lines": int_value(native.get("pm_service_binder_mdm_subsys_powerup_lines")),
        "native_wlfw_count": int_value(native.get("wlfw_count")),
        "native_wlan0_seen": bool_value(native.get("wlan0_seen")),
        "native_mdm3_states": native.get("mdm3_states") or [],
        "next_step": manifest.get("next_step", ""),
    }


def summarize_v1319(manifest: dict[str, Any]) -> dict[str, Any]:
    native = manifest.get("native_v1318") or {}
    android = manifest.get("android_reference") or {}
    return {
        "decision": manifest.get("decision", ""),
        "pass": bool_value(manifest.get("pass")),
        "forbidden_clear": all_forbidden_clear(manifest),
        "gpio135_high_count": int_value(native.get("gpio135_high_count")),
        "gpio142_line_count": int_value(native.get("gpio142_line_count")),
        "post_gpio135_sample_span_sec": float(native.get("post_gpio135_sample_span_sec") or 0.0),
        "native_mhi_pipe_seen": bool_value(native.get("mhi_pipe_seen")),
        "native_wlan0_seen": bool_value(native.get("wlan0_seen")),
        "android_gpio142_irq_count": int_value(android.get("v1239_gpio142_irq_count")),
        "android_pcie_rc1_lines": int_value(android.get("v1239_pcie_rc1_lines")),
        "android_wlan0_present": bool_value(android.get("v1239_wlan0_present")),
    }


def check(name: str, passed: bool, detail: str) -> dict[str, Any]:
    return {"name": name, "pass": bool(passed), "detail": detail}


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    v1320 = summarize_v1320(load_json(args.v1320_manifest))
    v1236 = summarize_v1236(load_json(args.v1236_manifest))
    v1238 = summarize_v1238(load_json(args.v1238_manifest))
    v1239 = summarize_v1239(load_json(args.v1239_manifest))
    v1319 = summarize_v1319(load_json(args.v1319_manifest))

    v1320_image_link_selected = (
        v1320["pass"]
        and v1320["decision"] == "v1320-mdm-helper-ks-mhi-contract-selected"
        and v1320["native_gpio135_high_count"] >= 1
        and v1320["native_gpio142_line_count"] == 0
        and v1320["android_ks_mhi_pipe"]
    )
    v1236_pm_contract_classified = (
        v1236["pass"]
        and v1236["decision"] == "v1236-ks-contract-is-pm-proxy-pm-service-trigger-not-mdm-helper-exec"
        and v1236["per_proxy_before_esoc0"]
        and v1236["pm_service_binder_mdm_subsys_powerup"]
        and v1236["actor_ks_mhi_pipe"]
        and v1236["native_wait_returned"]
        and v1236["native_execve_count"] == 0
    )
    v1238_native_pm_reached = (
        v1238["pass"]
        and v1238["decision"] == "v1238-late-per-proxy-reached-pm-service-esoc0-reboot-required"
        and v1238["late_per_proxy_started"]
        and v1238["pm_service_actor_esoc0_attempt"]
        and v1238["mdm_subsys_powerup"]
        and v1238["ks_count"] == 0
        and not v1238["wlan0_seen"]
    )
    v1239_lower_gap_classified = (
        v1239["pass"]
        and v1239["decision"] == "v1239-gap-is-after-pm-service-esoc0-before-gpio142-pcie-wlfw"
        and v1239["native_late_per_proxy_started"]
        and v1239["native_pm_service_esoc0_attempt"]
        and v1239["native_mdm_subsys_powerup_lines"] > 0
        and v1239["android_gpio142_irq_count"] > 0
        and v1239["android_pcie_rc1_lines"] > 0
        and not v1239["native_wlan0_seen"]
    )
    v1319_gpio135_response_absent = (
        v1319["pass"]
        and v1319["decision"] == "v1319-gpio135-asserted-mdm2ap-pcie-response-absent"
        and v1319["gpio135_high_count"] >= 1
        and v1319["gpio142_line_count"] == 0
        and v1319["post_gpio135_sample_span_sec"] >= 10.0
        and v1319["android_gpio142_irq_count"] > 0
    )
    guardrails_clear = all(
        item["forbidden_clear"]
        for item in (v1320, v1236, v1238, v1239, v1319)
    )

    checks = [
        check(
            "v1320-image-link-selected",
            v1320_image_link_selected,
            f"decision={v1320['decision']} native_gpio135={v1320['native_gpio135_high_count']} native_gpio142={v1320['native_gpio142_line_count']} android_ks_mhi={v1320['android_ks_mhi_pipe']}",
        ),
        check(
            "v1236-pm-contract-classified",
            v1236_pm_contract_classified,
            f"per_proxy_before_esoc0={v1236['per_proxy_before_esoc0']} pm_powerup={v1236['pm_service_binder_mdm_subsys_powerup']} native_execve={v1236['native_execve_count']}",
        ),
        check(
            "v1238-native-pm-reached",
            v1238_native_pm_reached,
            f"late_per_proxy={v1238['late_per_proxy_started']} esoc0_attempt={v1238['pm_service_actor_esoc0_attempt']} mdm_subsys_powerup={v1238['mdm_subsys_powerup']} ks={v1238['ks_count']}",
        ),
        check(
            "v1239-lower-gap-classified",
            v1239_lower_gap_classified,
            f"native_powerup_lines={v1239['native_mdm_subsys_powerup_lines']} android_gpio142={v1239['android_gpio142_irq_count']} android_pcie={v1239['android_pcie_rc1_lines']} native_wlan0={v1239['native_wlan0_seen']}",
        ),
        check(
            "v1319-gpio135-response-absent",
            v1319_gpio135_response_absent,
            f"gpio135={v1319['gpio135_high_count']} gpio142={v1319['gpio142_line_count']} span={v1319['post_gpio135_sample_span_sec']}",
        ),
        check(
            "guardrails-clear",
            guardrails_clear,
            "no Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, flash, or partition write in reconciled evidence",
        ),
    ]

    passed = all(item["pass"] for item in checks)
    if passed:
        decision = "v1321-image-link-gate-covered-next-sdx50m-response-inputs"
        reason = (
            "V1320's image-link gate is already covered by V1236-V1239: late per_proxy reaches "
            "pm-service /dev/subsys_esoc0 mdm_subsys_powerup, so the remaining gap is lower "
            "SDX50M response after GPIO135 before GPIO142/PCIe/MHI/WLFW"
        )
        next_step = (
            "V1322 should target SDX50M response inputs around mdm_subsys_powerup/GPIO135: "
            "read-only PCIe RC1, GPIO142 IRQ/state, regulator/pinctrl/GDSC, and cleanup-safe "
            "reboot boundary classification; do not repeat image-link gate or start Wi-Fi HAL/connect"
        )
    else:
        decision = "v1321-reconciliation-evidence-incomplete"
        reason = "required V1320, V1236, V1238, V1239, or V1319 evidence is missing or inconsistent"
        next_step = "refresh the failed evidence source before another live gate"

    return {
        "cycle": "v1321",
        "command": args.command,
        "generated_at": now_iso(),
        "host": collect_host_metadata(),
        "inputs": {
            "v1320_manifest": str(repo_path(args.v1320_manifest)),
            "v1236_manifest": str(repo_path(args.v1236_manifest)),
            "v1238_manifest": str(repo_path(args.v1238_manifest)),
            "v1239_manifest": str(repo_path(args.v1239_manifest)),
            "v1319_manifest": str(repo_path(args.v1319_manifest)),
        },
        "v1320": v1320,
        "v1236": v1236,
        "v1238": v1238,
        "v1239": v1239,
        "v1319": v1319,
        "checks": checks,
        "decision": decision,
        "pass": passed,
        "reason": reason,
        "next_step": next_step,
        "device_commands_executed": False,
        "device_mutations": False,
        "pm_actor_executed": False,
        "mdm_helper_executed": False,
        "tracefs_write_executed": False,
        "live_esoc_ioctl_executed": False,
        "live_esoc_notify_executed": False,
        "pmic_write_executed": False,
        "gpio_line_request_executed": False,
        "direct_esoc_ioctl_executed": False,
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
    rows = [[item["name"], item["pass"], item["detail"]] for item in manifest["checks"]]
    v1238 = manifest["v1238"]
    v1239 = manifest["v1239"]
    v1319 = manifest["v1319"]
    safety_rows = [[key, manifest.get(key)] for key in (
        "device_commands_executed",
        "device_mutations",
        "pm_actor_executed",
        "mdm_helper_executed",
        "tracefs_write_executed",
        "live_esoc_ioctl_executed",
        "live_esoc_notify_executed",
        "pmic_write_executed",
        "gpio_line_request_executed",
        "direct_esoc_ioctl_executed",
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
        "# V1321 Image-link Reconciliation Classifier",
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
        markdown_table(["check", "pass", "detail"], rows),
        "",
        "## Reconciled Blocker",
        "",
        markdown_table(["surface", "native", "Android / prior proof"], [
            ["image-link actor path", f"late_per_proxy={v1238['late_per_proxy_started']} pm_esoc0={v1238['pm_service_actor_esoc0_attempt']} mdm_subsys_powerup={v1238['mdm_subsys_powerup']}", "V1236 maps Android ks/MHI to per_proxy -> pm-service Binder -> esoc0"],
            ["post-powerup response", f"GPIO142={v1319['gpio142_line_count']} MHI=False wlan0={v1239['native_wlan0_seen']}", f"GPIO142={v1239['android_gpio142_irq_count']} PCIe_RC1={v1239['android_pcie_rc1_lines']} wlan0={v1239['android_wlan0_present']}"],
            ["cleanup boundary", f"v1238_all_postflight_safe={v1238['all_postflight_safe']} reboot={v1238['reboot_executed']}", "future live gate must be cleanup-safe or explicitly reboot-bounded"],
        ]),
        "",
        "## Safety",
        "",
        markdown_table(["field", "value"], safety_rows),
        "",
    ])


def render_report(manifest: dict[str, Any]) -> str:
    return "\n".join([
        "# Native Init V1321 Image-link Reconciliation Classifier",
        "",
        "## Summary",
        "",
        "- Cycle: `V1321`",
        "- Type: host-only reconciliation classifier",
        f"- Decision: `{manifest['decision']}`",
        f"- Result: {'PASS' if manifest['pass'] else 'FAIL'}",
        "- Evidence:",
        "  - `tmp/wifi/v1321-image-link-reconciliation-classifier/manifest.json`",
        "  - `tmp/wifi/v1321-image-link-reconciliation-classifier/summary.md`",
        "- Script: `scripts/revalidation/native_wifi_image_link_reconciliation_classifier_v1321.py`",
        "",
        "V1321 reconciles V1320 with the already-existing V1236-V1239 evidence.",
        "V1320 correctly identified the Android `mdm_helper`/`ks`/MHI image-link",
        "contract as relevant, but V1236-V1239 already prove the native late",
        "`per_proxy` path reaches `pm-service` and `/dev/subsys_esoc0` /",
        "`mdm_subsys_powerup`. The remaining blocker is therefore below the PM",
        "userspace actor path: SDX50M does not produce GPIO142, PCIe RC1/MHI, WLFW,",
        "BDF, or `wlan0` after native reaches GPIO135 / eSoC powerup.",
        "",
        "## Decision",
        "",
        "Do not repeat the image-link gate as the next primary branch. The next unit",
        "should target SDX50M response inputs around `mdm_subsys_powerup` and GPIO135:",
        "read-only GPIO142 IRQ/state, PCIe RC1, regulator/pinctrl/GDSC, MHI surface,",
        "and reboot-bounded cleanup behavior. Wi-Fi HAL, scan/connect, credentials,",
        "DHCP/routes, external ping, flash, boot image write, and partition write",
        "remain blocked.",
        "",
        "## Safety",
        "",
        "Host-only classifier. No device command, PM actor start, `mdm_helper` start,",
        "tracefs write, live eSoC ioctl/notify, PMIC write, userspace GPIO request,",
        "Wi-Fi HAL start, scan/connect, credential use, DHCP/routes, external ping,",
        "flash, boot image write, or partition write occurred.",
        "",
    ])


def print_result(manifest: dict[str, Any]) -> None:
    print(f"decision: {manifest.get('decision')}")
    print(f"pass:     {manifest.get('pass')}")
    print(f"reason:   {manifest.get('reason')}")
    print(f"next:     {manifest.get('next_step')}")
    print(f"v1238_pm_esoc0: {manifest['v1238']['pm_service_actor_esoc0_attempt']}")
    print(f"v1239_native_powerup_lines: {manifest['v1239']['native_mdm_subsys_powerup_lines']}")
    print(f"evidence: {manifest.get('_run_dir')}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v1320-manifest", type=Path, default=DEFAULT_V1320_MANIFEST)
    parser.add_argument("--v1236-manifest", type=Path, default=DEFAULT_V1236_MANIFEST)
    parser.add_argument("--v1238-manifest", type=Path, default=DEFAULT_V1238_MANIFEST)
    parser.add_argument("--v1239-manifest", type=Path, default=DEFAULT_V1239_MANIFEST)
    parser.add_argument("--v1319-manifest", type=Path, default=DEFAULT_V1319_MANIFEST)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args)
    manifest["_run_dir"] = str(store.run_dir)
    if args.command == "plan":
        manifest["decision"] = "v1321-image-link-reconciliation-plan-ready"
        manifest["pass"] = True
        manifest["reason"] = "plan-only; no device command or live action executed"
        manifest["next_step"] = "run V1321 host-only reconciliation against existing image-link and lower-response evidence"
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    if args.command == "run":
        write_private_text(repo_path(REPORT_PATH), render_report(manifest))
    print_result(manifest)
    return 0 if manifest.get("pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())

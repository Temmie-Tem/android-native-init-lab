#!/usr/bin/env python3
"""V1751 one-run WLAN-PD tracefs mount-restore handoff."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import native_wifi_wlan_pd_pure_nonlog_parity_handoff_v1744 as base


REPO_ROOT = Path(__file__).resolve().parents[2]
CYCLE = "V1751"
V1749_OUT = REPO_ROOT / "tmp" / "wifi" / "v1749-wlan-pd-tracefs-mount-restore-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v1749/dev/__properties__"
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1751-wlan-pd-tracefs-mount-restore-handoff"
DEFAULT_REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1751_WLAN_PD_TRACEFS_MOUNT_RESTORE_HANDOFF_2026-06-03.md"
)
TEST_EXPECT_VERSION = "A90 Linux init 0.9.143 (v1749-wlan-pd-tracefs-mount-restore)"
TEST_LOG_PATH = "/cache/native-init-wifi-test-boot-v1749.log"
TEST_SUMMARY_PATH = "/cache/native-init-wifi-test-boot-v1749.summary"
TEST_HELPER_RESULT_PATH = "/cache/native-init-wifi-test-boot-v1749-helper.result"
DMESG_PATTERN = (
    "A90v1749|wlan_pd_cnss_output_visibility|property_lookup|"
    "wlan_pd_cnss_nonlog_control_flow|wlan_pd_firmware_serve_gate|"
    "tracefs|uprobe|wlan_pd|wlanmdsp|tftp|rmt_storage|pd-mapper|qrtr|service 69|"
    "wlfw|wlfw_start|wlfw_service_request|icnss|FW ready|BDF|wlan0|"
    "cnss-daemon|4080000.qcom,mss|Brought out of reset|modem: loading"
)

ORIGINAL_CONFIGURE_BASE = base.configure_base
ORIGINAL_CLASSIFY_GATE = base.classify_gate


def intish(value: object) -> int:
    try:
        return int(str(value), 0)
    except (TypeError, ValueError):
        return 0


def is_true(value: object) -> bool:
    return str(value) == "1"


def configure_base() -> None:
    base.CYCLE = CYCLE
    base.V1743_OUT = V1749_OUT
    base.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    base.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    base.DEFAULT_REPORT_PATH = DEFAULT_REPORT_PATH
    base.TEST_EXPECT_VERSION = TEST_EXPECT_VERSION
    base.TEST_LOG_PATH = TEST_LOG_PATH
    base.TEST_SUMMARY_PATH = TEST_SUMMARY_PATH
    base.TEST_HELPER_RESULT_PATH = TEST_HELPER_RESULT_PATH
    base.DMESG_PATTERN = DMESG_PATTERN
    ORIGINAL_CONFIGURE_BASE()
    base.prev.base.base.DEFAULT_SOURCE_MANIFEST = V1749_OUT / "manifest.json"
    base.prev.base.base.DEFAULT_TEST_IMAGE = V1749_OUT / "boot_linux_v1749_wlan_pd_tracefs_mount_restore.img"


def choose_label(details: dict[str, Any]) -> tuple[str, str]:
    output_label = str(details.get("v1744_output_label") or "")
    first_failure_slug = str(details.get("first_failure_slug") or "none")
    tracefs_available = is_true(details.get("v1744_tracefs_available"))
    uprobe_attempted = is_true(details.get("v1744_uprobe_attempted"))
    uprobe_register_attempted = is_true(details.get("v1744_uprobe_register_attempted"))
    uprobe_hits = intish(details.get("v1744_uprobe_hit_count"))
    reached_by_nonlog = bool(details.get("v1744_reached_wlfw")) or uprobe_hits > 0

    if not tracefs_available or not uprobe_attempted or not uprobe_register_attempted:
        return (
            "tracefs-surface-unavailable",
            "V1749 restored debugfs mount in the artifact, but live helper still could not arm the private tracefs/uProbe surface",
        )
    if output_label == "wlfw-start-reached-downstream-block" or reached_by_nonlog:
        return (
            "wlfw-start-reached-downstream-block",
            "cnss-daemon reached wlfw_start by output or private tracefs/uProbe evidence",
        )
    if output_label.startswith("cnss-init-step-failed-"):
        return (
            output_label,
            "cnss-daemon emitted a named pre-WLFW init failure",
        )
    if first_failure_slug not in ("", "none", "None"):
        return (
            f"cnss-init-step-failed-{first_failure_slug}",
            "cnss-daemon first-failure slug was captured without a fixed output label",
        )
    return (
        "cnss-output-still-invisible",
        "tracefs/uProbe surface was available, but no cnss-daemon wlfw_start or named pre-WLFW init failure was visible",
    )


def classify_gate(args: argparse.Namespace,
                  test_flash: dict[str, Any],
                  rollback_result: dict[str, Any],
                  evidence_dir: Path) -> tuple[str, bool, str, dict[str, Any]]:
    decision, pass_ok, reason, details = ORIGINAL_CLASSIFY_GATE(
        args,
        test_flash,
        rollback_result,
        evidence_dir,
    )
    if not pass_ok:
        return decision, pass_ok, reason, details

    label, basis = choose_label(details)
    details.update({
        "v1751_label": label,
        "v1751_basis": basis,
        "v1751_tracefs_mount_restore_branch": True,
    })
    return (
        f"{args.cycle.lower()}-{label}-rollback-pass",
        True,
        "one tracefs mount-restore live handoff produced a fixed label and rollback verified",
        details,
    )


def render_report(result: dict[str, Any]) -> str:
    gate = result.get("gate", {})
    property_deploy = result.get("property_deploy", {})
    lines = [
        "# Native Init V1751 WLAN-PD Tracefs Mount Restore Handoff",
        "",
        "## Summary",
        "",
        "- Cycle: `V1751`",
        "- Type: one-run rollbackable tracefs mount-restore live gate",
        f"- Decision: `{result['decision']}`",
        f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
        f"- Reason: {result['reason']}",
        f"- Evidence: `{result['out_dir']}`",
        f"- Rollback attempt: `{result.get('rollback', {}).get('attempt')}`",
        "",
        "## Fixed Label",
        "",
        f"- V1751 label: `{gate.get('v1751_label')}`",
        f"- V1751 basis: {gate.get('v1751_basis')}",
        f"- output label: `{gate.get('v1744_output_label')}`",
        f"- `wlfw_start` source: `{gate.get('wlfw_start_source')}`",
        f"- `wlfw_start` stdout/stderr/kmsg counts: `{gate.get('wlfw_start_stdout_count')}` / `{gate.get('wlfw_start_stderr_count')}` / `{gate.get('wlfw_start_kmsg_count')}`",
        f"- first init failure slug: `{gate.get('first_failure_slug')}`",
        f"- non-log label: `{gate.get('v1744_nonlog_label')}`",
        f"- non-log contract seen: `{gate.get('v1744_nonlog_contract_seen')}`",
        f"- tracefs available/path/errno: `{gate.get('v1744_tracefs_available')}` / `{gate.get('v1744_tracefs_path')}` / `{gate.get('v1744_tracefs_errno')}`",
        f"- uprobe attempted/register rc/enabled/hits: `{gate.get('v1744_uprobe_attempted')}` / `{gate.get('v1744_uprobe_register_rc')}` / `{gate.get('v1744_uprobe_enabled')}` / `{gate.get('v1744_uprobe_hit_count')}`",
        f"- reached wlfw by non-log evidence: `{gate.get('v1744_reached_wlfw')}`",
        f"- route safety ok: `{gate.get('v1744_route_safety_ok')}`",
        "",
        "## Property Runtime",
        "",
        f"- Remote root: `{property_deploy.get('remote_property_root')}`",
        f"- Uploaded files: `{property_deploy.get('file_count')}`",
        f"- Uploaded bytes: `{property_deploy.get('bytes')}`",
        f"- property_info SHA verified: `{property_deploy.get('property_info_sha_ok')}`",
        f"- vendor_default_prop SHA verified: `{property_deploy.get('vendor_default_sha_ok')}`",
        "",
        "## Safety Scope",
        "",
        "- `/dev/subsys_esoc0`, forced RC1, fake-ONLINE, PMIC/GPIO/GDSC writes, eSoC notify, BOOT_DONE spoof, PCI rescan, and platform bind/unbind were not used.",
        "- service-manager, PM trio, `boot_wlan`, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping were not used.",
        "- Mutation scope was private property runtime staging on `/mnt/sdext`, test boot flash, and rollback to `stage3/boot_linux_v724.img`.",
        "",
        "## Interpretation",
        "",
        "- This gate preserves the corrected premise: `boot_wlan` is not a WLFW trigger and missing native dmesg output can be a measurement artifact.",
        "- It reuses only the V1680-style internal-modem firmware-serve route and adds no PM/service-window actors.",
        "- One live run sets one label. Stop after this label; do not spin timing/window variants.",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    base.configure_base = configure_base
    base.classify_gate = classify_gate
    base.render_report = render_report
    return base.main(argv)


if __name__ == "__main__":
    raise SystemExit(main())

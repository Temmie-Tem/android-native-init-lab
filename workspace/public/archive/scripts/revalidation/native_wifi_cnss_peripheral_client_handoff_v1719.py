#!/usr/bin/env python3
"""V1719 one-run CNSS libperipheral_client.so uprobe handoff."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import native_wifi_cnss_pm_init_handoff_v1716 as prev


base = prev.base
REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
CYCLE = "V1719"
V1718_OUT = REPO_ROOT / "tmp" / "wifi" / "v1718-cnss-peripheral-client-uprobe-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v1718/dev/__properties__"
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1719-cnss-peripheral-client-uprobe-handoff"
DEFAULT_REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1719_CNSS_PERIPHERAL_CLIENT_UPROBE_HANDOFF_2026-06-02.md"
)
TEST_EXPECT_VERSION = "A90 Linux init 0.9.134 (v1718-cnss-peripheral-client-uprobe)"
TEST_LOG_PATH = "/cache/native-init-wifi-test-boot-v1718.log"
TEST_SUMMARY_PATH = "/cache/native-init-wifi-test-boot-v1718.summary"
TEST_HELPER_RESULT_PATH = "/cache/native-init-wifi-test-boot-v1718-helper.result"
PERIPHERAL_KEYS = (
    "periph_pm_client_register_entry",
    "periph_pm_register_connect_entry",
    "periph_vndbinder_init_call",
    "periph_default_service_manager_call",
    "periph_manager_name_string16_call",
    "periph_service_manager_get_call",
    "periph_binder_object_present_check",
    "periph_as_interface_call",
    "periph_manager_register_tx_call",
    "periph_manager_register_tx_retcheck",
    "periph_success_path",
    "periph_pm_register_connect_return",
    "periph_pm_client_register_common_return",
)
PERIPHERAL_LABELS = {
    "peripheral-register-returned",
    "peripheral-success-path-no-return",
    "peripheral-manager-register-transaction-returned",
    "peripheral-manager-register-transaction-call-no-return",
    "peripheral-as-interface-no-register-transaction",
    "peripheral-service-lookup-returned-no-interface",
    "peripheral-service-manager-get-call-no-return",
    "peripheral-service-name-built-no-get",
    "peripheral-default-service-manager-call-no-return",
    "peripheral-vndbinder-init-call-no-return",
    "peripheral-register-connect-entry-no-vndbinder-init",
    "peripheral-client-register-entry-no-connect-entry",
}


def configure_base() -> None:
    prev.configure_base()
    base.CYCLE = CYCLE
    base.V1699_OUT = V1718_OUT
    base.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    base.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    base.DEFAULT_REPORT_PATH = DEFAULT_REPORT_PATH
    base.TEST_EXPECT_VERSION = TEST_EXPECT_VERSION
    base.TEST_LOG_PATH = TEST_LOG_PATH
    base.TEST_SUMMARY_PATH = TEST_SUMMARY_PATH
    base.TEST_HELPER_RESULT_PATH = TEST_HELPER_RESULT_PATH
    base.DMESG_PATTERN = prev.DMESG_PATTERN.replace("A90v1715", "A90v1718") + "|" + "|".join(PERIPHERAL_KEYS)
    base.VALID_NONLOG_LABELS = set(prev.VALID_PM_INIT_LABELS) | PERIPHERAL_LABELS
    base.base.CYCLE = CYCLE
    base.base.V1690_OUT = V1718_OUT
    base.base.base.V1687_OUT = V1718_OUT
    base.base.base.DEFAULT_SOURCE_MANIFEST = V1718_OUT / "manifest.json"
    base.base.base.DEFAULT_TEST_IMAGE = V1718_OUT / "boot_linux_v1718_cnss_peripheral_client_uprobe.img"
    base.base.base.LOCAL_PROPERTY_ROOT = V1718_OUT / "property-runtime" / "layout" / "dev" / "__properties__"
    base.base.base.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    base.base.base.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    base.base.base.DEFAULT_REPORT_PATH = DEFAULT_REPORT_PATH
    base.base.base.CYCLE = CYCLE
    base.base.base.TEST_EXPECT_VERSION = TEST_EXPECT_VERSION
    base.base.base.TEST_LOG_PATH = TEST_LOG_PATH
    base.base.base.TEST_SUMMARY_PATH = TEST_SUMMARY_PATH
    base.base.base.TEST_HELPER_RESULT_PATH = TEST_HELPER_RESULT_PATH
    base.base.base.DMESG_PATTERN = base.DMESG_PATTERN


def classify_gate(args: argparse.Namespace,
                  test_flash: dict[str, Any],
                  rollback_result: dict[str, Any],
                  evidence_dir: Path) -> tuple[str, bool, str, dict[str, Any]]:
    decision, pass_ok, reason, details = prev.classify_gate(
        args,
        test_flash,
        rollback_result,
        evidence_dir,
    )
    helper_fields = base.base.base.fwbase.parse_helper_fields(evidence_dir)
    details["peripheral_uprobe_attempted"] = helper_fields.get(
        "wlan_pd_cnss_nonlog_control_flow.peripheral_uprobe_attempted"
    )
    details["peripheral_uprobe_target"] = helper_fields.get(
        "wlan_pd_cnss_nonlog_control_flow.peripheral_uprobe.target.selected_path"
    )
    details["peripheral_uprobe_hit_count"] = helper_fields.get(
        "wlan_pd_cnss_nonlog_control_flow.peripheral_uprobe.hit_count"
    )
    details["peripheral_uprobe_first_hit_line"] = helper_fields.get(
        "wlan_pd_cnss_nonlog_control_flow.peripheral_uprobe.first_hit_line"
    )
    for key in PERIPHERAL_KEYS:
        prefix = f"wlan_pd_cnss_nonlog_control_flow.peripheral_uprobe.{key}"
        details[f"peripheral_{key}_offset"] = helper_fields.get(f"{prefix}.offset")
        details[f"peripheral_{key}_registered"] = helper_fields.get(f"{prefix}.registered")
        details[f"peripheral_{key}_enabled"] = helper_fields.get(f"{prefix}.enabled")
        details[f"peripheral_{key}_hit_count"] = helper_fields.get(f"{prefix}.hit_count")
        details[f"peripheral_{key}_first_hit_line"] = helper_fields.get(f"{prefix}.first_hit_line")
    return decision, pass_ok, reason, details


def render_report(result: dict[str, Any]) -> str:
    gate = result.get("gate", {})
    rollback = result.get("rollback", {})
    lines = [
        "# Native Init V1719 CNSS Peripheral Client Uprobe Handoff",
        "",
        "## Summary",
        "",
        "- Cycle: `V1719`",
        "- Type: one-run rollbackable CNSS `libperipheral_client.so` tracefs uprobe classifier",
        f"- Decision: `{result.get('decision')}`",
        f"- Result: `{'PASS' if result.get('pass') else 'FAIL'}`",
        f"- Evidence: `{result.get('out_dir')}`",
        f"- Rollback attempt: `{rollback.get('attempt')}`",
        f"- Rollback ok: `{rollback.get('ok')}`",
        "",
        "## Gate Label",
        "",
        f"- output label: `{gate.get('label')}`",
        f"- non-log label: `{gate.get('nonlog_label')}`",
        f"- legacy firmware-serve label: `{gate.get('old_firmware_serve_label')}`",
        f"- peripheral target: `{gate.get('peripheral_uprobe_target')}`",
        f"- peripheral hit count: `{gate.get('peripheral_uprobe_hit_count')}`",
        f"- peripheral first hit: `{gate.get('peripheral_uprobe_first_hit_line')}`",
        f"- cnss-daemon running: `{gate.get('cnss_daemon_running')}`",
        "",
        "## Peripheral Trace Targets",
        "",
    ]
    for key in PERIPHERAL_KEYS:
        lines.extend([
            f"- `{key}` offset `{gate.get(f'peripheral_{key}_offset')}` hit_count `{gate.get(f'peripheral_{key}_hit_count')}` registered/enabled `{gate.get(f'peripheral_{key}_registered')}` / `{gate.get(f'peripheral_{key}_enabled')}`",
            f"  first_hit: `{gate.get(f'peripheral_{key}_first_hit_line')}`",
        ])
    lines.extend([
        "",
        "## Safety Scope",
        "",
        "- `/dev/subsys_esoc0`, forced RC1, fake-ONLINE, PMIC/GPIO/GDSC writes, eSoC notify, BOOT_DONE spoof, PCI rescan, and platform bind/unbind were not used.",
        "- service-manager, PM trio, `boot_wlan`, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping were not used.",
        "- Mutation scope was private property runtime staging on `/mnt/sdext`, test boot flash, and rollback to `stage3/boot_linux_v724.img`.",
        "",
        "## Interpretation",
        "",
        "- This classifier distinguishes `/dev/vndbinder` initialization, default service-manager lookup, `vendor.qcom.PeripheralManager` service lookup, and the manager register transaction.",
        "- It still does not add service-manager or PM actors.",
        "",
    ])
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    configure_base()
    base.base.base.classify_gate = classify_gate
    base.base.base.render_report = render_report
    return base.base.base.main(argv)


if __name__ == "__main__":
    raise SystemExit(main())

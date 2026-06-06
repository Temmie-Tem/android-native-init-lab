#!/usr/bin/env python3
"""V1686 one-run WLAN-PD PM-trio service-window handoff."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import native_wifi_wlan_pd_firmware_serve_handoff_v1675 as base


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
CYCLE = "V1686"
VALID_LABELS = {
    "wlfw-start-reached",
    "pm-trio-still-no-wlfw",
    "pm-trio-child-failed",
    "service-window-child-failed",
    "modem-holder-regression",
}


def _configure_base() -> None:
    base.__doc__ = __doc__
    base.CYCLE = CYCLE
    base.DEFAULT_SOURCE_MANIFEST = (
        REPO_ROOT
        / "tmp"
        / "wifi"
        / "v1685-wlan-pd-pm-trio-source-build"
        / "manifest.json"
    )
    base.DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1686-wlan-pd-pm-trio-handoff"
    base.DEFAULT_REPORT_PATH = (
        REPO_ROOT
        / "docs"
        / "reports"
        / "NATIVE_INIT_V1686_WLAN_PD_PM_TRIO_HANDOFF_2026-06-02.md"
    )
    base.DEFAULT_TEST_IMAGE = (
        REPO_ROOT
        / "tmp"
        / "wifi"
        / "v1685-wlan-pd-pm-trio-source-build"
        / "boot_linux_v1393_wifi_test.img"
    )
    base.TEST_EXPECT_VERSION = "A90 Linux init 0.9.69 (v1393-wifitest)"
    base.TEST_LOG_PATH = "/cache/native-init-wifi-test-boot-v1685.log"
    base.TEST_SUMMARY_PATH = "/cache/native-init-wifi-test-boot-v1685.summary"
    base.TEST_HELPER_RESULT_PATH = "/cache/native-init-wifi-test-boot-v1685-helper.result"
    base.DMESG_PATTERN = (
        "A90v1685|wlan_pd_pm_service_window_trigger|wlan_pd_firmware_serve_gate|"
        "wlan_pd|wlanmdsp|tftp|rmt_storage|pd-mapper|qrtr|service 69|"
        "wlfw|wlfw_start|wlfw_service_request|icnss|FW ready|BDF|wlan0|"
        "pm_proxy_helper|pm-service|pm-proxy|per_mgr|per_proxy|peripheral|"
        "4080000.qcom,mss|Brought out of reset|modem: loading"
    )
    base.VALID_LABELS = VALID_LABELS
    base.classify_gate = classify_gate
    base.render_report = render_report


def classify_gate(args: Any,
                  test_flash: dict[str, Any],
                  rollback_result: dict[str, Any],
                  evidence_dir: Path) -> tuple[str, bool, str, dict[str, Any]]:
    test_version = base.read_text(evidence_dir, "test-version.stdout.txt")
    helper_fields = base.parse_helper_fields(evidence_dir)
    label = helper_fields.get("wlan_pd_pm_service_window_trigger.label", "")
    helper_contract_seen = helper_fields.get("wlan_pd_pm_service_window_trigger.begin") == "1"
    version_ok = args.expect_test_version in test_version
    rollback_ok = bool(rollback_result.get("ok"))
    label_ok = label in VALID_LABELS

    details = {
        "version_ok": version_ok,
        "rollback_ok": rollback_ok,
        "helper_contract_seen": helper_contract_seen,
        "label": label,
        "label_ok": label_ok,
        "old_firmware_serve_label": helper_fields.get("wlan_pd_firmware_serve_gate.label"),
        "subsys_modem_holder_opened": helper_fields.get("wlan_pd_pm_service_window_trigger.subsys_modem_holder_opened"),
        "pm_proxy_helper_present": helper_fields.get("wlan_pd_pm_service_window_trigger.pm_proxy_helper_present"),
        "pm_proxy_helper_observable": helper_fields.get("wlan_pd_pm_service_window_trigger.pm_proxy_helper_observable"),
        "pm_proxy_helper_running": helper_fields.get("wlan_pd_pm_service_window_trigger.pm_proxy_helper_running"),
        "per_mgr_present": helper_fields.get("wlan_pd_pm_service_window_trigger.per_mgr_present"),
        "per_mgr_observable": helper_fields.get("wlan_pd_pm_service_window_trigger.per_mgr_observable"),
        "per_mgr_running": helper_fields.get("wlan_pd_pm_service_window_trigger.per_mgr_running"),
        "per_proxy_present": helper_fields.get("wlan_pd_pm_service_window_trigger.per_proxy_present"),
        "per_proxy_observable": helper_fields.get("wlan_pd_pm_service_window_trigger.per_proxy_observable"),
        "per_proxy_running": helper_fields.get("wlan_pd_pm_service_window_trigger.per_proxy_running"),
        "tftp_running": helper_fields.get("wlan_pd_pm_service_window_trigger.tftp_running"),
        "cnss_daemon_started": helper_fields.get("wlan_pd_pm_service_window_trigger.cnss_daemon_started"),
        "wlfw_start_seen": helper_fields.get("wlan_pd_pm_service_window_trigger.wlfw_start_seen"),
        "wlfw_service_request_seen": helper_fields.get("wlan_pd_pm_service_window_trigger.wlfw_service_request_seen"),
        "wlfw_service69_seen": helper_fields.get("wlan_pd_pm_service_window_trigger.wlfw_service69_seen"),
        "requested_wlanmdsp": helper_fields.get("wlan_pd_pm_service_window_trigger.requested_wlanmdsp"),
        "kmsg_wlfw_start_count": helper_fields.get("wlan_pd_pm_service_window_trigger.kmsg_wlfw_start_count"),
        "kmsg_wlfw_service_request_count": helper_fields.get("wlan_pd_pm_service_window_trigger.kmsg_wlfw_service_request_count"),
        "no_esoc0": helper_fields.get("wlan_pd_pm_service_window_trigger.no_esoc0"),
        "no_forced_rc1": helper_fields.get("wlan_pd_pm_service_window_trigger.no_forced_rc1"),
        "no_mdm_helper": helper_fields.get("wlan_pd_pm_service_window_trigger.no_mdm_helper"),
        "no_wifi_hal": helper_fields.get("wlan_pd_pm_service_window_trigger.no_wifi_hal"),
        "no_wificond": helper_fields.get("wlan_pd_pm_service_window_trigger.no_wificond"),
        "no_scan_connect": helper_fields.get("wlan_pd_pm_service_window_trigger.no_scan_connect"),
        "no_credentials": helper_fields.get("wlan_pd_pm_service_window_trigger.no_credentials"),
        "no_dhcp_routes": helper_fields.get("wlan_pd_pm_service_window_trigger.no_dhcp_routes"),
        "no_external_ping": helper_fields.get("wlan_pd_pm_service_window_trigger.no_external_ping"),
        "companion_result": helper_fields.get("wifi_companion_start.result"),
        "companion_reason": helper_fields.get("wifi_companion_start.reason"),
        "companion_order": helper_fields.get("wifi_companion_start.order"),
    }

    if not test_flash.get("ok"):
        return (
            f"{args.cycle.lower()}-test-boot-flash-or-verify-failed",
            False,
            "test boot flash/verify failed; rollback evidence must be inspected before retry",
            details,
        )
    if not version_ok:
        return (
            f"{args.cycle.lower()}-test-boot-version-missing",
            False,
            f"expected {args.cycle} test boot version marker was not collected",
            details,
        )
    if not rollback_ok:
        return (
            f"{args.cycle.lower()}-rollback-failed",
            False,
            "PM-trio service-window evidence may exist, but rollback to v724 did not verify",
            details,
        )
    if not helper_contract_seen:
        return (
            f"{args.cycle.lower()}-pm-service-window-contract-missing",
            False,
            "helper result did not include the WLAN-PD PM-trio service-window trigger contract",
            details,
        )
    if not label_ok:
        return (
            f"{args.cycle.lower()}-pm-service-window-label-missing",
            False,
            "helper result did not produce one of the fixed PM-trio service-window labels",
            details,
        )
    return (
        f"{args.cycle.lower()}-{label}-rollback-pass",
        True,
        "one WLAN-PD PM-trio service-window gate run produced a fixed label and rollback verified",
        details,
    )


def render_report(result: dict[str, Any]) -> str:
    gate = result.get("gate", {})
    cycle = str(result.get("cycle", CYCLE))
    lines = [
        f"# Native Init {cycle} WLAN-PD PM-trio Service-window Handoff",
        "",
        "## Summary",
        "",
        f"- Cycle: `{cycle}`",
        "- Type: one-run rollbackable WLAN-PD PM-trio service-window gate",
        f"- Decision: `{result['decision']}`",
        f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
        f"- Reason: {result['reason']}",
        f"- Evidence: `{result['out_dir']}`",
        f"- Rollback attempt: `{result.get('rollback', {}).get('attempt')}`",
        "",
        "## Gate Label",
        "",
        f"- Label: `{gate.get('label')}`",
        f"- legacy firmware-serve label: `{gate.get('old_firmware_serve_label')}`",
        f"- subsys_modem holder opened: `{gate.get('subsys_modem_holder_opened')}`",
        f"- pm_proxy_helper running: `{gate.get('pm_proxy_helper_running')}`",
        f"- per_mgr running: `{gate.get('per_mgr_running')}`",
        f"- per_proxy running: `{gate.get('per_proxy_running')}`",
        f"- tftp running: `{gate.get('tftp_running')}`",
        f"- cnss-daemon started: `{gate.get('cnss_daemon_started')}`",
        f"- wlfw_start seen: `{gate.get('wlfw_start_seen')}`",
        f"- wlfw_service_request seen: `{gate.get('wlfw_service_request_seen')}`",
        f"- WLFW service 69 seen: `{gate.get('wlfw_service69_seen')}`",
        f"- requested wlanmdsp: `{gate.get('requested_wlanmdsp')}`",
        f"- companion order: `{gate.get('companion_order')}`",
        "",
        "## Safety Scope",
        "",
        "- `/dev/subsys_esoc0`, raw eSoC ioctl, forced RC1, fake-ONLINE, PMIC/GPIO/GDSC writes, eSoC notify, and BOOT_DONE spoof were not used.",
        "- `mdm_helper`, Wi-Fi HAL, `wificond`, scan/connect, credentials, DHCP/routes, and external ping were not used.",
        "- Mutation scope was test boot flash followed by rollback to `stage3/boot_linux_v724.img`.",
        "",
        "## Next",
        "",
        "- Stop after this one label.",
        "- If label is `wlfw-start-reached`, the next gate may inspect WLFW service 69 / WLAN-PD / firmware serving.",
        "- If label is `pm-trio-still-no-wlfw`, PM trio alone is not the missing WLAN-PD trigger; analyze Android-good PM/CNSS inputs before adding any lower-layer work.",
        "- If label is `pm-trio-child-failed`, fix the specific child startup before retrying the gate.",
        "- Do not proceed to MSA/BDF, Wi-Fi HAL, scan/connect, DHCP/routes, credentials, or external ping until WLFW service 69 or `wlfw-start-reached` appears.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    _configure_base()
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())

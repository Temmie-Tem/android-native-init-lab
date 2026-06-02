#!/usr/bin/env python3
"""V1683 one-run WLAN-PD service-window trigger handoff."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import native_wifi_wlan_pd_firmware_serve_handoff_v1675 as base


REPO_ROOT = Path(__file__).resolve().parents[2]
CYCLE = "V1683"
VALID_LABELS = {
    "wlfw-start-reached",
    "service-window-still-no-wlfw",
    "modem-holder-regression",
    "service-window-child-failed",
}


def _configure_base() -> None:
    base.CYCLE = CYCLE
    base.DEFAULT_SOURCE_MANIFEST = (
        REPO_ROOT
        / "tmp"
        / "wifi"
        / "v1682-wlan-pd-service-window-merge-source-build"
        / "manifest.json"
    )
    base.DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1683-wlan-pd-service-window-handoff"
    base.DEFAULT_REPORT_PATH = (
        REPO_ROOT
        / "docs"
        / "reports"
        / "NATIVE_INIT_V1683_WLAN_PD_SERVICE_WINDOW_HANDOFF_2026-06-02.md"
    )
    base.DEFAULT_TEST_IMAGE = (
        REPO_ROOT
        / "tmp"
        / "wifi"
        / "v1682-wlan-pd-service-window-merge-source-build"
        / "boot_linux_v1393_wifi_test.img"
    )
    base.TEST_EXPECT_VERSION = "A90 Linux init 0.9.69 (v1393-wifitest)"
    base.TEST_LOG_PATH = "/cache/native-init-wifi-test-boot-v1682.log"
    base.TEST_SUMMARY_PATH = "/cache/native-init-wifi-test-boot-v1682.summary"
    base.TEST_HELPER_RESULT_PATH = "/cache/native-init-wifi-test-boot-v1682-helper.result"
    base.DMESG_PATTERN = (
        "A90v1682|wlan_pd_service_window_trigger|wlan_pd_firmware_serve_gate|"
        "wlan_pd|wlanmdsp|tftp|rmt_storage|pd-mapper|qrtr|service 69|"
        "wlfw|wlfw_start|wlfw_service_request|icnss|FW ready|BDF|wlan0|"
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
    label = helper_fields.get("wlan_pd_service_window_trigger.label", "")
    helper_contract_seen = helper_fields.get("wlan_pd_service_window_trigger.begin") == "1"
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
        "tftp_running": helper_fields.get("wlan_pd_service_window_trigger.tftp_running"),
        "subsys_modem_holder_opened": helper_fields.get("wlan_pd_service_window_trigger.subsys_modem_holder_opened"),
        "cnss_daemon_started": helper_fields.get("wlan_pd_service_window_trigger.cnss_daemon_started"),
        "wlfw_start_seen": helper_fields.get("wlan_pd_service_window_trigger.wlfw_start_seen"),
        "wlfw_service_request_seen": helper_fields.get("wlan_pd_service_window_trigger.wlfw_service_request_seen"),
        "wlfw_service69_seen": helper_fields.get("wlan_pd_service_window_trigger.wlfw_service69_seen"),
        "requested_wlanmdsp": helper_fields.get("wlan_pd_service_window_trigger.requested_wlanmdsp"),
        "kmsg_wlfw_start_count": helper_fields.get("wlan_pd_service_window_trigger.kmsg_wlfw_start_count"),
        "kmsg_wlfw_service_request_count": helper_fields.get("wlan_pd_service_window_trigger.kmsg_wlfw_service_request_count"),
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
            "service-window evidence may exist, but rollback to v724 did not verify",
            details,
        )
    if not helper_contract_seen:
        return (
            f"{args.cycle.lower()}-service-window-contract-missing",
            False,
            "helper result did not include the WLAN-PD service-window trigger contract",
            details,
        )
    if not label_ok:
        return (
            f"{args.cycle.lower()}-service-window-label-missing",
            False,
            "helper result did not produce one of the fixed service-window labels",
            details,
        )
    return (
        f"{args.cycle.lower()}-{label}-rollback-pass",
        True,
        "one WLAN-PD service-window trigger gate run produced a fixed label and rollback verified",
        details,
    )


def render_report(result: dict[str, Any]) -> str:
    gate = result.get("gate", {})
    cycle = str(result.get("cycle", CYCLE))
    lines = [
        f"# Native Init {cycle} WLAN-PD Service-window Trigger Handoff",
        "",
        "## Summary",
        "",
        f"- Cycle: `{cycle}`",
        "- Type: one-run rollbackable WLAN-PD service-window trigger gate",
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
        f"- tftp running: `{gate.get('tftp_running')}`",
        f"- subsys_modem holder opened: `{gate.get('subsys_modem_holder_opened')}`",
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
        "- Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping were not used.",
        "- Mutation scope was test boot flash followed by rollback to `stage3/boot_linux_v724.img`.",
        "",
        "## Next",
        "",
        "- Stop after this one label.",
        "- If label is `wlfw-start-reached`, the next gate may inspect WLFW service 69 / WLAN-PD / firmware serving.",
        "- If label is `service-window-still-no-wlfw`, inspect missing Android property/binder/service inputs before adding lower-layer work.",
        "- Do not proceed to MSA/BDF, Wi-Fi HAL, scan/connect, DHCP/routes, credentials, or external ping until WLFW service 69 or `wlfw-start-reached` appears.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    _configure_base()
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())

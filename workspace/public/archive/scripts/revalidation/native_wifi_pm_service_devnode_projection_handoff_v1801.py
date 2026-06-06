#!/usr/bin/env python3
"""V1801 one-run WLAN-PD PM-service devnode projection handoff."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import native_wifi_pm_service_devnode_access_handoff_v1799 as prev1799
import native_wifi_wlan_pd_pm_service_count_sample_handoff_v1796 as prev1796


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
CYCLE = "V1801"
V1800_OUT = REPO_ROOT / "tmp" / "wifi" / "v1800-pm-service-devnode-projection-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v1800/dev/__properties__"
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1801-pm-service-devnode-projection-handoff"
DEFAULT_REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1801_PM_SERVICE_DEVNODE_PROJECTION_HANDOFF_2026-06-03.md"
)
TEST_EXPECT_VERSION = "A90 Linux init 0.9.150 (v1800-pm-service-devnode-projection)"
TEST_LOG_PATH = "/cache/native-init-wifi-test-boot-v1800.log"
TEST_SUMMARY_PATH = "/cache/native-init-wifi-test-boot-v1800.summary"
TEST_HELPER_RESULT_PATH = "/cache/native-init-wifi-test-boot-v1800-helper.result"
DMESG_PATTERN = (
    "A90v1800|wlan_pd_service_object_visible_trigger|private_node.subsys|"
    "devnode_access|devnode.sdx50m|devnode.modem|access_f_ok|lstat_ok|"
    "char_device|wlan_pd_cnss_nonlog_control_flow|pm_server_uprobe|"
    "pm_server_register|pm-service-init|pm_service_init|pm_service_add_peripheral|"
    "first_count=|second_count=|record=|devnode=|pm-server-register|pm-service|"
    "PeripheralManager|peripheral|vndservicemanager|vndbinder|service-manager|"
    "servicemanager|hwservicemanager|pm_proxy_helper|wlan_pd|wlanmdsp|tftp|"
    "rmt_storage|pd-mapper|qrtr|service 69|wlfw|wlfw_start|"
    "wlfw_service_request|icnss|FW ready|BDF|wlan0|cnss-daemon|"
    "4080000.qcom,mss|Brought out of reset|modem: loading"
)


def configure_runner() -> None:
    prev1796.CYCLE = CYCLE
    prev1796.V1795_OUT = V1800_OUT
    prev1796.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev1796.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    prev1796.DEFAULT_REPORT_PATH = DEFAULT_REPORT_PATH
    prev1796.TEST_EXPECT_VERSION = TEST_EXPECT_VERSION
    prev1796.TEST_LOG_PATH = TEST_LOG_PATH
    prev1796.TEST_SUMMARY_PATH = TEST_SUMMARY_PATH
    prev1796.TEST_HELPER_RESULT_PATH = TEST_HELPER_RESULT_PATH
    prev1796.DMESG_PATTERN = DMESG_PATTERN
    prev1796.configure_runner()
    prev1796.runner.DEFAULT_SOURCE_MANIFEST = V1800_OUT / "manifest.json"
    prev1796.runner.DEFAULT_TEST_IMAGE = (
        V1800_OUT / "boot_linux_v1800_pm_service_devnode_projection.img"
    )
    prev1796.runner.LOCAL_PROPERTY_ROOT = (
        V1800_OUT / "property-runtime" / "layout" / "dev" / "__properties__"
    )


def private_node_prefix(label: str) -> str:
    return f"wifi_companion_start.private_node.{label}."


def collect_private_node(fields: dict[str, str], label: str) -> dict[str, str]:
    prefix = private_node_prefix(label)
    return {
        "exists": fields.get(prefix + "exists", ""),
        "char_device": fields.get(prefix + "char_device", ""),
        "major": fields.get(prefix + "major", ""),
        "minor": fields.get(prefix + "minor", ""),
        "mode": fields.get(prefix + "mode", ""),
        "uid": fields.get(prefix + "uid", ""),
        "gid": fields.get(prefix + "gid", ""),
        "path": fields.get(prefix + "path", ""),
        "error": fields.get(prefix + "error", ""),
    }


def private_node_visible(node: dict[str, str]) -> bool:
    return node.get("exists") == "1" and node.get("char_device") == "1"


def private_node_expected(node: dict[str, str]) -> bool:
    return (
        private_node_visible(node) and
        node.get("mode") == "0640" and
        node.get("uid") == "1000" and
        node.get("gid") == "1000"
    )


def collect_gate_fields(fields: dict[str, str]) -> dict[str, Any]:
    details = prev1799.collect_gate_fields(fields)
    private_modem = collect_private_node(fields, "subsys_modem")
    private_sdx50m = collect_private_node(fields, "subsys_esoc0")
    details.update(
        {
            "private_node_modem": private_modem,
            "private_node_sdx50m": private_sdx50m,
            "private_node_modem_visible": private_node_visible(private_modem),
            "private_node_sdx50m_visible": private_node_visible(private_sdx50m),
            "private_node_modem_expected": private_node_expected(private_modem),
            "private_node_sdx50m_expected": private_node_expected(private_sdx50m),
        }
    )
    return details


def classify_gate(args: Any,
                  test_flash: dict[str, Any],
                  rollback_result: dict[str, Any],
                  evidence_dir: Path) -> tuple[str, bool, str, dict[str, Any]]:
    test_version = prev1796.runner.fwbase.read_text(evidence_dir, "test-version.stdout.txt")
    helper_fields = prev1796.runner.fwbase.parse_helper_fields(evidence_dir)
    details = collect_gate_fields(helper_fields)
    version_ok = args.expect_test_version in test_version
    rollback_ok = bool(rollback_result.get("ok"))
    helper_contract_seen = prev1796.field_bool(
        helper_fields,
        "wlan_pd_service_object_visible_trigger.begin",
    )
    nonlog_contract_seen = prev1796.field_bool(
        helper_fields,
        "wlan_pd_cnss_nonlog_control_flow.begin",
    )
    late_listener_contract_seen = prev1796.field_bool(
        helper_fields,
        "wifi_companion_service_notifier_late_listener.begin",
    )
    safety_ok = prev1796.safety_ok(helper_fields) and bool(details.get("devnode_safety_ok"))
    details.update(
        {
            "version_ok": version_ok,
            "rollback_ok": rollback_ok,
            "helper_contract_seen": helper_contract_seen,
            "nonlog_contract_seen": nonlog_contract_seen,
            "late_listener_contract_seen": late_listener_contract_seen,
            "safety_ok": safety_ok,
        }
    )

    if not test_flash.get("ok"):
        return f"{args.cycle.lower()}-test-boot-flash-or-verify-failed", False, "test boot flash/verify failed", details
    if not version_ok:
        return f"{args.cycle.lower()}-test-boot-version-missing", False, "expected V1800 test boot version was not collected", details
    if not rollback_ok:
        return f"{args.cycle.lower()}-rollback-failed", False, "rollback to v724 did not verify", details
    if not helper_contract_seen or not nonlog_contract_seen or not late_listener_contract_seen:
        return f"{args.cycle.lower()}-service-object-contract-missing", False, "helper result missed service-object, nonlog, or late listener fields", details
    if not safety_ok:
        details["pm_service_devnode_projection_label"] = "safety-regression"
        return f"{args.cycle.lower()}-safety-regression", False, "one or more hard-stop safety fields regressed", details

    list_commit_hits = prev1796.intish(details.get("pm_service_add_peripheral_list_commit_hits"))
    init_fail_hits = prev1796.intish(details.get("pm_service_add_peripheral_init_fail_hits"))
    private_ready = bool(details["private_node_sdx50m_expected"]) and bool(details["private_node_modem_expected"])

    if not private_ready:
        label = "projection-setup-failed"
        reason = "early private-node status did not show both projected candidate char nodes with expected mode/owner"
    elif list_commit_hits > 0:
        label = "list-commit-progress"
        reason = "PM-service reached supported-list commit after private-dev projection"
    elif init_fail_hits > 0:
        label = "projection-visible-still-fails"
        reason = "both projected candidate nodes were visible before children, but PM-service still failed before list commit"
    else:
        label = "projection-visible-still-fails"
        reason = "projection was visible but PM-service did not reach a supported-list commit in this bounded route"

    details["pm_service_devnode_projection_label"] = label
    return f"{args.cycle.lower()}-{label}-rollback-pass", True, reason, details


def render_private_node(label: str, node: dict[str, str]) -> list[str]:
    return [
        f"- {label} exists/char: `{node.get('exists')}` / `{node.get('char_device')}`",
        f"- {label} major:minor mode uid:gid: `{node.get('major')}:{node.get('minor')}` `{node.get('mode')}` `{node.get('uid')}:{node.get('gid')}`",
        f"- {label} path/error: `{node.get('path')}` / `{node.get('error')}`",
    ]


def render_report(result: dict[str, Any]) -> str:
    gate = result.get("gate", {})
    property_deploy = result.get("property_deploy", {})
    cycle = str(result.get("cycle", CYCLE))
    lines = [
        f"# Native Init {cycle} PM-service Devnode Projection Handoff",
        "",
        "## Summary",
        "",
        f"- Cycle: `{cycle}`",
        "- Type: one-run rollbackable WLAN-PD PM-service private-dev projection discriminator",
        f"- Decision: `{result['decision']}`",
        f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
        f"- Reason: {result['reason']}",
        f"- Evidence: `{result['out_dir']}`",
        f"- Rollback attempt: `{result.get('rollback', {}).get('attempt')}`",
        f"- Rollback ok: `{result.get('rollback', {}).get('ok')}`",
        "",
        "## Gate Label",
        "",
        f"- PM-service projection label: `{gate.get('pm_service_devnode_projection_label')}`",
        f"- helper label: `{gate.get('helper_label')}`",
        f"- PM server label: `{gate.get('pm_server_label')}`",
        f"- safety ok: `{gate.get('safety_ok')}`",
        "",
        "## Early Private Nodes",
        "",
        *render_private_node("sdx50m", gate.get("private_node_sdx50m", {})),
        *render_private_node("modem", gate.get("private_node_modem", {})),
        f"- expected flags: sdx50m `{gate.get('private_node_sdx50m_expected')}`, modem `{gate.get('private_node_modem_expected')}`",
        "",
        "## Final No-open Devnode Status",
        "",
        *prev1799.render_node("sdx50m", gate.get("devnode_sdx50m", {})),
        *prev1799.render_node("modem", gate.get("devnode_modem", {})),
        "",
        "## PM-service Correlation",
        "",
        f"- first/second count: `{gate.get('pm_service_first_count')}` / `{gate.get('pm_service_second_count')}`",
        f"- first add names/devnodes: `{gate.get('pm_service_first_add_names')}` / `{gate.get('pm_service_first_add_devnodes')}`",
        f"- entry/init-fail/list-commit hits: `{gate.get('pm_service_add_peripheral_entry_hits')}` / `{gate.get('pm_service_add_peripheral_init_fail_hits')}` / `{gate.get('pm_service_add_peripheral_list_commit_hits')}`",
        f"- init-fail names/devnodes: `{gate.get('pm_service_init_fail_names')}` / `{gate.get('pm_service_init_fail_devnodes')}`",
        f"- register no-peripheral requested: `{gate.get('pm_server_register_no_peripheral_name')}`",
        f"- loop/match/success/no-peripheral hits: `{gate.get('pm_server_loop_node_hits')}` / `{gate.get('pm_server_match_hits')}` / `{gate.get('pm_server_success_return_hits')}` / `{gate.get('pm_server_no_peripheral_hits')}`",
        "",
        "## Route Health",
        "",
        f"- provider seen: `{gate.get('provider_seen')}`",
        f"- requested `wlanmdsp`: `{gate.get('requested_wlanmdsp')}`",
        f"- WLFW service 69 seen: `{gate.get('wlfw_service69_seen')}`",
        f"- wlan0 present: `{gate.get('wlan0_present')}`",
        f"- `pm_proxy_helper` ready: `{gate.get('pm_proxy_helper_ready')}`",
        f"- `pm-service` ready: `{gate.get('per_mgr_ready')}`",
        f"- `tftp_server` running: `{gate.get('tftp_running')}`",
        f"- `cnss-daemon` running: `{gate.get('cnss_daemon_running')}`",
        "",
        "## Property Runtime",
        "",
        f"- Remote root: `{property_deploy.get('remote_property_root')}`",
        f"- Transport: `{property_deploy.get('transport')}`",
        f"- Uploaded files/bytes: `{property_deploy.get('file_count')}` / `{property_deploy.get('bytes')}`",
        f"- property_info SHA verified: `{property_deploy.get('property_info_sha_ok')}`",
        f"- vendor_default_prop SHA verified: `{property_deploy.get('vendor_default_sha_ok')}`",
        "",
        "## Safety Scope",
        "",
        "- The route projected private char nodes but did not open `/dev/subsys_esoc0` and did not start Wi-Fi HAL, scan/connect, use credentials, configure DHCP/routes, or external ping.",
        "- Forced RC1, fake-ONLINE, PMIC/GPIO/GDSC writes, eSoC notify, BOOT_DONE spoof, PCI rescan, platform bind/unbind, restart-PD request, full `pm-proxy`, and `boot_wlan` were not used.",
        "- Mutation scope is private property runtime staging on `/mnt/sdext`, one test boot flash, and rollback to `stage3/boot_linux_v724.img`.",
        "",
        "## Next",
        "",
        "- Stop after this one label; choose the next source/build-only step from the projection result.",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    configure_runner()
    prev1796.runner.deploy_property_root = prev1796.deploy_property_root_serial
    prev1796.runner.classify_gate = classify_gate
    prev1796.runner.render_report = render_report
    rc = prev1796.runner.main(argv)
    prev1796.sanitize_evidence_dir(DEFAULT_OUT_DIR)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())

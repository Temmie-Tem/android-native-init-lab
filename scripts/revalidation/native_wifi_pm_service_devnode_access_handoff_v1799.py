#!/usr/bin/env python3
"""V1799 one-run WLAN-PD PM-service devnode access observer handoff."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import native_wifi_wlan_pd_pm_service_count_sample_handoff_v1796 as prev1796


REPO_ROOT = Path(__file__).resolve().parents[2]
CYCLE = "V1799"
V1798_OUT = REPO_ROOT / "tmp" / "wifi" / "v1798-pm-service-devnode-access-observer-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v1798/dev/__properties__"
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1799-pm-service-devnode-access-handoff"
DEFAULT_REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1799_PM_SERVICE_DEVNODE_ACCESS_HANDOFF_2026-06-03.md"
)
TEST_EXPECT_VERSION = "A90 Linux init 0.9.149 (v1798-pm-service-devnode-access-observer)"
TEST_LOG_PATH = "/cache/native-init-wifi-test-boot-v1798.log"
TEST_SUMMARY_PATH = "/cache/native-init-wifi-test-boot-v1798.summary"
TEST_HELPER_RESULT_PATH = "/cache/native-init-wifi-test-boot-v1798-helper.result"
DMESG_PATTERN = (
    "A90v1798|wlan_pd_service_object_visible_trigger|devnode_access|"
    "devnode.sdx50m|devnode.modem|access_f_ok|lstat_ok|char_device|"
    "wlan_pd_cnss_nonlog_control_flow|pm_server_uprobe|pm_server_register|"
    "pm-service-init|pm_service_init|pm_service_add_peripheral|"
    "first_count=|second_count=|record=|devnode=|pm-server-register|pm-service|"
    "PeripheralManager|peripheral|vndservicemanager|vndbinder|service-manager|"
    "servicemanager|hwservicemanager|pm_proxy_helper|wlan_pd|wlanmdsp|tftp|"
    "rmt_storage|pd-mapper|qrtr|service 69|wlfw|wlfw_start|"
    "wlfw_service_request|icnss|FW ready|BDF|wlan0|cnss-daemon|"
    "4080000.qcom,mss|Brought out of reset|modem: loading"
)


def configure_runner() -> None:
    prev1796.CYCLE = CYCLE
    prev1796.V1795_OUT = V1798_OUT
    prev1796.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev1796.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    prev1796.DEFAULT_REPORT_PATH = DEFAULT_REPORT_PATH
    prev1796.TEST_EXPECT_VERSION = TEST_EXPECT_VERSION
    prev1796.TEST_LOG_PATH = TEST_LOG_PATH
    prev1796.TEST_SUMMARY_PATH = TEST_SUMMARY_PATH
    prev1796.TEST_HELPER_RESULT_PATH = TEST_HELPER_RESULT_PATH
    prev1796.DMESG_PATTERN = DMESG_PATTERN
    prev1796.configure_runner()
    prev1796.runner.DEFAULT_SOURCE_MANIFEST = V1798_OUT / "manifest.json"
    prev1796.runner.DEFAULT_TEST_IMAGE = (
        V1798_OUT / "boot_linux_v1798_pm_service_devnode_access_observer.img"
    )
    prev1796.runner.LOCAL_PROPERTY_ROOT = (
        V1798_OUT / "property-runtime" / "layout" / "dev" / "__properties__"
    )


def devnode_prefix(label: str) -> str:
    return f"wlan_pd_service_object_visible_trigger.devnode.{label}."


def collect_devnode(fields: dict[str, str], label: str) -> dict[str, str]:
    prefix = devnode_prefix(label)
    return {
        "name": fields.get(prefix + "name", ""),
        "path": fields.get(prefix + "path", ""),
        "open_attempted": fields.get(prefix + "open_attempted", ""),
        "mknod_attempted": fields.get(prefix + "mknod_attempted", ""),
        "access_f_ok": fields.get(prefix + "access_f_ok", ""),
        "access_errno": fields.get(prefix + "access_errno", ""),
        "lstat_ok": fields.get(prefix + "lstat_ok", ""),
        "lstat_errno": fields.get(prefix + "lstat_errno", ""),
        "char_device": fields.get(prefix + "char_device", ""),
        "major": fields.get(prefix + "major", ""),
        "minor": fields.get(prefix + "minor", ""),
        "mode": fields.get(prefix + "mode", ""),
        "uid": fields.get(prefix + "uid", ""),
        "gid": fields.get(prefix + "gid", ""),
    }


def parse_mode(mode: str) -> int:
    try:
        return int(str(mode or "0"), 8)
    except ValueError:
        return -1


def node_present(node: dict[str, str]) -> bool:
    return (
        node.get("lstat_ok") == "1" and
        node.get("access_f_ok") == "1" and
        node.get("char_device") == "1"
    )


def node_absent(node: dict[str, str]) -> bool:
    return node.get("lstat_ok") != "1" and node.get("access_f_ok") != "1"


def node_mismatch(node: dict[str, str]) -> bool:
    if node.get("lstat_ok") != "1":
        return False
    if node.get("char_device") != "1" or node.get("access_f_ok") != "1":
        return True
    mode = parse_mode(node.get("mode", ""))
    uid = prev1796.intish(node.get("uid"))
    gid = prev1796.intish(node.get("gid"))
    mode_ok = mode in {0o600, 0o640, 0o660}
    owner_ok = (uid, gid) in {(0, 0), (1000, 1000)}
    return not mode_ok or not owner_ok


def devnode_safety_ok(fields: dict[str, str]) -> bool:
    if fields.get("wlan_pd_service_object_visible_trigger.devnode_access.open_attempted") != "0":
        return False
    if fields.get("wlan_pd_service_object_visible_trigger.devnode_access.mknod_attempted") != "0":
        return False
    for label in ("sdx50m", "modem"):
        prefix = devnode_prefix(label)
        if fields.get(prefix + "open_attempted") != "0":
            return False
        if fields.get(prefix + "mknod_attempted") != "0":
            return False
    return True


def collect_gate_fields(fields: dict[str, str]) -> dict[str, Any]:
    details = prev1796.collect_pm_fields(fields)
    sdx50m = collect_devnode(fields, "sdx50m")
    modem = collect_devnode(fields, "modem")
    details.update(
        {
            "devnode_access_begin": fields.get(
                "wlan_pd_service_object_visible_trigger.devnode_access.begin",
                "",
            ),
            "devnode_access_source": fields.get(
                "wlan_pd_service_object_visible_trigger.devnode_access.source",
                "",
            ),
            "devnode_access_open_attempted": fields.get(
                "wlan_pd_service_object_visible_trigger.devnode_access.open_attempted",
                "",
            ),
            "devnode_access_mknod_attempted": fields.get(
                "wlan_pd_service_object_visible_trigger.devnode_access.mknod_attempted",
                "",
            ),
            "devnode_access_end": fields.get(
                "wlan_pd_service_object_visible_trigger.devnode_access.end",
                "",
            ),
            "devnode_sdx50m": sdx50m,
            "devnode_modem": modem,
            "devnode_sdx50m_present": node_present(sdx50m),
            "devnode_modem_present": node_present(modem),
            "devnode_sdx50m_absent": node_absent(sdx50m),
            "devnode_modem_absent": node_absent(modem),
            "devnode_sdx50m_mismatch": node_mismatch(sdx50m),
            "devnode_modem_mismatch": node_mismatch(modem),
            "devnode_safety_ok": devnode_safety_ok(fields),
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
    devnode_contract_seen = (
        details["devnode_access_begin"] == "1" and
        details["devnode_access_end"] == "1" and
        details["devnode_sdx50m"].get("name") == "subsys_esoc0" and
        details["devnode_modem"].get("name") == "subsys_modem"
    )
    nonlog_contract_seen = prev1796.field_bool(
        helper_fields,
        "wlan_pd_cnss_nonlog_control_flow.begin",
    )
    late_listener_contract_seen = prev1796.field_bool(
        helper_fields,
        "wifi_companion_service_notifier_late_listener.begin",
    )
    details.update(
        {
            "version_ok": version_ok,
            "rollback_ok": rollback_ok,
            "helper_contract_seen": helper_contract_seen,
            "devnode_contract_seen": devnode_contract_seen,
            "nonlog_contract_seen": nonlog_contract_seen,
            "late_listener_contract_seen": late_listener_contract_seen,
            "safety_ok": prev1796.safety_ok(helper_fields) and details["devnode_safety_ok"],
        }
    )

    if not test_flash.get("ok"):
        return f"{args.cycle.lower()}-test-boot-flash-or-verify-failed", False, "test boot flash/verify failed", details
    if not version_ok:
        return f"{args.cycle.lower()}-test-boot-version-missing", False, "expected V1798 test boot version was not collected", details
    if not rollback_ok:
        return f"{args.cycle.lower()}-rollback-failed", False, "rollback to v724 did not verify", details
    if not helper_contract_seen or not nonlog_contract_seen or not late_listener_contract_seen:
        return f"{args.cycle.lower()}-service-object-contract-missing", False, "helper result missed service-object, nonlog, or late listener fields", details
    if not devnode_contract_seen:
        return f"{args.cycle.lower()}-devnode-access-contract-missing", False, "helper result missed V1798 devnode access observer fields", details
    if not details["safety_ok"]:
        return f"{args.cycle.lower()}-safety-contract-regression", False, "one or more hard-stop safety fields regressed", details

    sdx50m_present = bool(details["devnode_sdx50m_present"])
    modem_present = bool(details["devnode_modem_present"])
    sdx50m_absent = bool(details["devnode_sdx50m_absent"])
    modem_absent = bool(details["devnode_modem_absent"])
    sdx50m_mismatch = bool(details["devnode_sdx50m_mismatch"])
    modem_mismatch = bool(details["devnode_modem_mismatch"])
    list_commit_hits = prev1796.intish(details.get("pm_service_add_peripheral_list_commit_hits"))
    init_fail_hits = prev1796.intish(details.get("pm_service_add_peripheral_init_fail_hits"))

    if list_commit_hits > 0:
        label = "list-commit-progress"
        reason = "PM-service reached supported-list commit; stop before any PM repair, restart-PD request, or WLAN-PD cascade"
    elif sdx50m_mismatch or modem_mismatch:
        label = "nonchar-or-mode-mismatch"
        reason = "a candidate path exists but the no-open status shows non-character, inaccessible, or unexpected mode/owner state"
    elif sdx50m_absent and modem_absent:
        label = "both-devnodes-absent"
        reason = "both PM-service candidate devnodes are absent from the private Android dev tree"
    elif sdx50m_absent and modem_present:
        label = "modem-present-sdx50m-absent"
        reason = "private dev tree has the modem holder node but lacks the SDX50M/esoc candidate node"
    elif sdx50m_present and modem_present and init_fail_hits > 0:
        label = "candidate-visible-but-pm-fails"
        reason = "both candidate devnodes are visible to the helper, but PM-service still fails before list commit"
    elif sdx50m_present or modem_present:
        label = "candidate-visible-but-pm-fails"
        reason = "at least one candidate devnode is visible while PM-service still does not reach list commit"
    else:
        label = "nonchar-or-mode-mismatch"
        reason = "devnode observer produced rollback-verified evidence outside the expected absent/visible patterns"

    details["pm_service_devnode_access_label"] = label
    return f"{args.cycle.lower()}-{label}-rollback-pass", True, reason, details


def render_node(label: str, node: dict[str, str]) -> list[str]:
    return [
        f"- {label} name/path: `{node.get('name')}` / `{node.get('path')}`",
        f"- {label} access/lstat: `{node.get('access_f_ok')}` errno `{node.get('access_errno')}` / `{node.get('lstat_ok')}` errno `{node.get('lstat_errno')}`",
        f"- {label} char major:minor mode uid:gid: `{node.get('char_device')}` `{node.get('major')}:{node.get('minor')}` `{node.get('mode')}` `{node.get('uid')}:{node.get('gid')}`",
    ]


def render_report(result: dict[str, Any]) -> str:
    gate = result.get("gate", {})
    property_deploy = result.get("property_deploy", {})
    cycle = str(result.get("cycle", CYCLE))
    lines = [
        f"# Native Init {cycle} PM-service Devnode Access Handoff",
        "",
        "## Summary",
        "",
        f"- Cycle: `{cycle}`",
        "- Type: one-run rollbackable WLAN-PD PM-service devnode access discriminator",
        f"- Decision: `{result['decision']}`",
        f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
        f"- Reason: {result['reason']}",
        f"- Evidence: `{result['out_dir']}`",
        f"- Rollback attempt: `{result.get('rollback', {}).get('attempt')}`",
        f"- Rollback ok: `{result.get('rollback', {}).get('ok')}`",
        "",
        "## Gate Label",
        "",
        f"- PM-service devnode access label: `{gate.get('pm_service_devnode_access_label')}`",
        f"- helper label: `{gate.get('helper_label')}`",
        f"- PM server label: `{gate.get('pm_server_label')}`",
        f"- devnode observer source: `{gate.get('devnode_access_source')}`",
        f"- observer open/mknod attempted: `{gate.get('devnode_access_open_attempted')}` / `{gate.get('devnode_access_mknod_attempted')}`",
        f"- safety ok: `{gate.get('safety_ok')}`",
        "",
        "## Devnode Status",
        "",
        *render_node("sdx50m", gate.get("devnode_sdx50m", {})),
        *render_node("modem", gate.get("devnode_modem", {})),
        f"- present flags: sdx50m `{gate.get('devnode_sdx50m_present')}`, modem `{gate.get('devnode_modem_present')}`",
        f"- absent flags: sdx50m `{gate.get('devnode_sdx50m_absent')}`, modem `{gate.get('devnode_modem_absent')}`",
        f"- mismatch flags: sdx50m `{gate.get('devnode_sdx50m_mismatch')}`, modem `{gate.get('devnode_modem_mismatch')}`",
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
        "- `/dev/subsys_esoc0` was not opened, no PM-service devnode repair was attempted, and no private devnode was created by the V1798 observer.",
        "- Forced RC1, fake-ONLINE, PMIC/GPIO/GDSC writes, eSoC notify, BOOT_DONE spoof, PCI rescan, platform bind/unbind, restart-PD request, full `pm-proxy`, `boot_wlan`, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping were not used.",
        "- Mutation scope is private property runtime staging on `/mnt/sdext`, one test boot flash, and rollback to `stage3/boot_linux_v724.img`.",
        "",
        "## Next",
        "",
        "- Stop after this one label; use the devnode access label to choose the next source/build-only repair or parity observer.",
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

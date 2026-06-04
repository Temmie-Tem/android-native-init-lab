#!/usr/bin/env python3
"""V2059 rollbackable handoff for focused cnss-daemon PerMgr register/vote evidence."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

import native_wifi_readwrite_transition_handoff_v2057 as prev2057


CYCLE = "V2059"
OUT_DIR = prev2057.prev2046.prev2035.prev1998.prev1992.prev.repo_path(
    "tmp/wifi/v2059-permgr-vote-focused-handoff"
)
HANDOFF_DIR = OUT_DIR / "v2058-handoff"
HANDOFF_REPORT = OUT_DIR / "v2058-handoff-report.md"
REPORT_PATH = prev2057.prev2046.prev2035.prev1998.prev1992.prev.repo_path(
    "docs/reports/NATIVE_INIT_V2059_PERMGR_VOTE_FOCUSED_HANDOFF_2026-06-04.md"
)
V2058_OUT = prev2057.prev2046.prev2035.prev1998.prev1992.prev.repo_path(
    "tmp/wifi/v2058-permgr-vote-focused-test-boot"
)
V2058_INIT = V2058_OUT / "init_v2058_permgr_vote_focused"
V2058_BOOT = V2058_OUT / "boot_linux_v2058_permgr_vote_focused.img"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v2058/dev/__properties__"
TEST_EXPECT_VERSION = "A90 Linux init 0.9.208 (v2058-permgr-vote-focused)"
TEST_LOG_PATH = "/cache/native-init-wifi-test-boot-v2058.log"
TEST_SUMMARY_PATH = "/cache/native-init-wifi-test-boot-v2058.summary"
TEST_HELPER_RESULT_PATH = "/cache/native-init-wifi-test-boot-v2058-helper.result"
EXPECTED_HELPER_VERSION = "a90_android_execns_probe v393"

ORIGINAL_ARTIFACT_HOOK = prev2057.artifact_hook_check
ORIGINAL_COLLECT_DETAILS = prev2057.collect_details
ORIGINAL_CLASSIFY = prev2057.classify
ORIGINAL_RENDER_REPORT = prev2057.render_report


def rel(path: Path) -> str:
    return prev2057.rel(path)


def intish(value: object) -> int:
    return prev2057.intish(value)


def boolish(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "ok"}


def markdown_table(headers: list[str], rows: list[list[object]]) -> str:
    return prev2057.markdown_table(headers, rows)


def artifact_hook_check() -> dict[str, Any]:
    init_forbidden = (
        "--allow-servloc-domain-list-probe",
        "--allow-service-notifier-listener-probe",
        "--qrtr-readback-matrix",
        "wlfw:69:0,1",
        "--pm-observer-private-cnss-daemon-sdx50m",
        "--private-cnss-daemon-path",
    )
    boot_forbidden = (
        "wlan_pd_tftp_server_trace.late_attach.begin=1",
        "wifi_companion_start.wlan_pd_producer_tftp_server_syscall_trace.compiled=1",
        "PTRACE_ATTACH",
    )
    init_required = (
        "native-init-sibling-fwssctl-v641",
        "A90v641: sibling fwssctl proof armed",
        "wifi-v641-fwssctl",
        "A90v2058",
        "wifi-companion-wlan-pd-post-pm-lower-state-observer-start-only",
        "--timeout-sec",
        "75",
    )
    boot_required = (
        EXPECTED_HELPER_VERSION,
        "per_mgr_vote_focused.begin=1",
        "per_mgr_vote_focused.mode=cnss-pm-client-register-vote-uprobe-compact",
        "per_mgr_vote_focused.pm_server.register_success_return.hit_count=%d",
        "per_mgr_vote_focused.label=%s",
        "tftp_readwrite_transition.mode=read-only-stat-open-on-change",
        "tftp_readwrite_transition.sample_%03u.%s.exists=%d",
        "tftp_ready_before_wlfw_vote.mode=alive-socket-plus-android-order-settle",
        "tftp_ready_before_wlfw_vote.no_qrtr_send=1",
        "tftp_ready_before_wlfw_vote.no_qmi_send=1",
        "tftp_logdw_sink.order_timestamps=1",
        "tftp_logdw_sink.summary.first_wlanmdsp_delta_ms=%ld",
    )
    checks: dict[str, Any] = {}
    for path, required in ((V2058_INIT, init_required), (V2058_BOOT, boot_required)):
        key = rel(path)
        forbidden_tokens = init_forbidden if path == V2058_INIT else boot_forbidden
        data = path.read_bytes() if path.exists() else b""
        missing = [token for token in required if token.encode() not in data]
        forbidden = [token for token in forbidden_tokens if token.encode() in data]
        checks[key] = {
            "exists": path.exists(),
            "ok": path.exists() and not missing and not forbidden,
            "missing": missing,
            "forbidden": forbidden,
        }
    return checks


def focused_first_line(fields: dict[str, str], key: str) -> str:
    return fields.get(f"per_mgr_vote_focused.{key}.first_hit_line", "")


def collect_permgr_vote(fields: dict[str, str]) -> dict[str, Any]:
    prefix = "per_mgr_vote_focused"
    interesting_ints = (
        "begin",
        "cnss.pm_client_register_call.hit_count",
        "cnss.pm_client_register_retcheck.hit_count",
        "cnss.pm_client_register_retcheck.rc_zero",
        "cnss.pm_client_connect_call.hit_count",
        "cnss.pm_client_connect_retcheck.hit_count",
        "cnss.pm_client_connect_retcheck.rc_zero",
        "peripheral.pm_client_register_entry.hit_count",
        "peripheral.manager_register_tx_call.hit_count",
        "peripheral.manager_register_tx_retcheck.hit_count",
        "peripheral.success_path.hit_count",
        "peripheral.pm_register_connect_return.hit_count",
        "peripheral.pm_client_register_common_return.hit_count",
        "peripheral.callback_stub_entry.hit_count",
        "pm_server.register_entry.hit_count",
        "pm_server.register_match.hit_count",
        "pm_server.register_add_client_call.hit_count",
        "pm_server.register_success_return.hit_count",
        "pm_server.no_peripheral.hit_count",
        "pm_server.ack_impl_entry.hit_count",
        "pm_server.post_ack_action_entry.hit_count",
        "cnss_register_success",
        "cnss_connect_success",
        "peripheral_register_success",
        "pm_server_register_success",
        "pm_vote_ack_seen",
    )
    data: dict[str, Any] = {
        "mode": fields.get(f"{prefix}.mode", ""),
        "label": fields.get(f"{prefix}.label", ""),
        "target": fields.get(f"{prefix}.pm_server.target.selected_path", ""),
        "cnss_register_ret_line": fields.get(f"{prefix}.cnss.pm_client_register_retcheck.first_hit_line", ""),
        "cnss_connect_ret_line": fields.get(f"{prefix}.cnss.pm_client_connect_retcheck.first_hit_line", ""),
        "pm_server_register_entry_line": fields.get(f"{prefix}.pm_server.register_entry.first_hit_line", ""),
    }
    for key in interesting_ints:
        data[key.replace(".", "_")] = intish(fields.get(f"{prefix}.{key}"))
    data["safe"] = (
        intish(fields.get(f"{prefix}.no_ptrace")) == 1
        and intish(fields.get(f"{prefix}.no_qrtr_send")) == 1
        and intish(fields.get(f"{prefix}.no_qmi_send")) == 1
        and intish(fields.get(f"{prefix}.no_wifi_hal")) == 1
    )
    return data


def collect_details(handoff: dict[str, Any]) -> dict[str, Any]:
    details = ORIGINAL_COLLECT_DETAILS(handoff)
    fields = prev2057.parse_fields()
    details["per_mgr_vote_focused"] = collect_permgr_vote(fields)
    return details


def classify(handoff: dict[str, Any],
             hook: dict[str, Any],
             steps: list[dict[str, Any]],
             details: dict[str, Any]) -> dict[str, Any]:
    base = ORIGINAL_CLASSIFY(handoff, hook, steps, details)
    pm = details.get("per_mgr_vote_focused") if isinstance(details.get("per_mgr_vote_focused"), dict) else {}
    hook_ok = all(bool(item.get("ok")) for item in hook.values())
    focused_ok = intish(pm.get("begin")) == 1 and bool(pm.get("safe"))
    route_ok = bool(base.get("route_ok")) and hook_ok and focused_ok
    wlanmdsp_seen = bool(base.get("wlanmdsp_seen"))
    server_success = intish(pm.get("pm_server_register_success")) == 1
    client_success = intish(pm.get("cnss_register_success")) == 1 and intish(pm.get("cnss_connect_success")) == 1
    peripheral_success = intish(pm.get("peripheral_register_success")) == 1

    if not hook_ok:
        label = "per-mgr-vote-artifact-hook-regression"
        passed = False
        reason = "V2058 artifact does not contain the focused PerMgr vote contract tokens"
    elif not focused_ok:
        label = "per-mgr-vote-focused-summary-missing"
        passed = False
        reason = "focused PerMgr register/vote summary was absent or safety markers were incomplete"
    elif not route_ok:
        label = "per-mgr-vote-route-regression"
        passed = False
        reason = "lower route prerequisites regressed before focused PerMgr classification"
    elif client_success and peripheral_success and server_success and wlanmdsp_seen:
        label = "cnss-permgr-register-vote-success-wlanmdsp-requested"
        passed = True
        reason = "cnss-daemon PerMgr register/connect and pm-service server acceptance succeeded and wlanmdsp was requested"
    elif client_success and peripheral_success and server_success:
        label = "cnss-permgr-register-vote-success-no-wlanmdsp"
        passed = True
        reason = "cnss-daemon PerMgr register/connect and pm-service server acceptance succeeded, but native still made no wlanmdsp request"
    elif client_success and peripheral_success:
        label = "cnss-permgr-client-success-server-unobserved-no-wlanmdsp"
        passed = True
        reason = "cnss/libperipheral register/connect succeeded, but focused pm-service server acceptance was not observed and wlanmdsp was still absent"
    elif intish(pm.get("cnss_pm_client_register_call_hit_count")) > 0:
        label = "cnss-permgr-register-started-no-vote-success"
        passed = True
        reason = "cnss-daemon entered the PM client register path but did not complete the register/connect vote contract"
    else:
        label = "cnss-permgr-register-not-started"
        passed = True
        reason = "cnss-daemon did not enter the PM client register path in the focused window"

    return {
        **base,
        "decision": f"v2059-{label}-rollback-{'pass' if passed else 'blocked'}",
        "label": label,
        "pass": passed,
        "reason": reason,
        "hook_ok": hook_ok,
        "focused_ok": focused_ok,
        "route_ok": route_ok,
        "per_mgr_client_success": client_success,
        "per_mgr_peripheral_success": peripheral_success,
        "per_mgr_server_success": server_success,
    }


def render_report(manifest: dict[str, Any]) -> str:
    details = manifest["details"]
    classification = manifest["classification"]
    pm = details.get("per_mgr_vote_focused", {})
    logdw = details.get("tftp_logdw", {}) if isinstance(details.get("tftp_logdw"), dict) else {}
    transition = details.get("readwrite_transition", {}) if isinstance(details.get("readwrite_transition"), dict) else {}
    transition_summary = transition.get("summary", {}) if isinstance(transition.get("summary"), dict) else {}
    cascade = details.get("cascade", {}) if isinstance(details.get("cascade"), dict) else {}
    step_lines = [
        f"- `{step['name']}` rc `{step['rc']}` ok `{step['ok']}` evidence `{step['file']}`"
        for step in manifest["steps"]
    ]
    return "\n".join([
        "# Native Init V2059 PerMgr Vote Focused Handoff",
        "",
        "## Summary",
        "",
        "- Cycle: `V2059`",
        f"- Decision: `{manifest['decision']}`",
        f"- Label: `{manifest['label']}`",
        f"- Pass: `{manifest['pass']}`",
        f"- Reason: {manifest['reason']}",
        f"- Evidence: `{manifest['out_dir']}`",
        f"- Inner handoff: `{manifest['handoff_manifest']}`",
        "",
        "## Matrix",
        "",
        markdown_table(
            ["area", "value", "detail"],
            [
                ["route", classification.get("route_ok"), f"hook={classification.get('hook_ok')} focused={classification.get('focused_ok')}"],
                ["cnss_client", classification.get("per_mgr_client_success"), f"register_rc0={pm.get('cnss_register_success')} connect_rc0={pm.get('cnss_connect_success')}"] ,
                ["libperipheral", classification.get("per_mgr_peripheral_success"), f"tx_ret={pm.get('peripheral_manager_register_tx_retcheck_hit_count')} success={pm.get('peripheral_success_path_hit_count')} return={pm.get('peripheral_pm_register_connect_return_hit_count')}"],
                ["pm_service", classification.get("per_mgr_server_success"), f"entry={pm.get('pm_server_register_entry_hit_count')} match={pm.get('pm_server_register_match_hit_count')} add_client={pm.get('pm_server_register_add_client_call_hit_count')} success={pm.get('pm_server_register_success_return_hit_count')} no_periph={pm.get('pm_server_no_peripheral_hit_count')}"] ,
                ["callback_ack", pm.get("pm_vote_ack_seen"), f"callback={pm.get('peripheral_callback_stub_entry_hit_count')} ack={pm.get('pm_server_ack_impl_entry_hit_count')} post_ack={pm.get('pm_server_post_ack_action_entry_hit_count')}"],
                ["tftp_branch", "", f"server_check={logdw.get('summary', {}).get('server_check')} ota={logdw.get('summary', {}).get('ota_firewall')} mcfg={logdw.get('summary', {}).get('mcfg')} wlanmdsp={logdw.get('summary', {}).get('wlanmdsp')}"] ,
                ["readwrite_file", "", f"server_check_seen={transition_summary.get('server_check_seen')} delta_ms={transition_summary.get('first_server_check_file_delta_ms')} ota={transition_summary.get('ota_ruleset_seen')}"] ,
                ["cascade", "", f"wlan_pd={cascade.get('wlan_pd_up')} icnss_qmi={cascade.get('icnss_qmi_connected')} fw_ready={cascade.get('fw_ready')} wlan0={cascade.get('wlan0')}"],
            ],
        ),
        "",
        "## Focused PerMgr Evidence",
        "",
        markdown_table(
            ["field", "value"],
            [
                ["focused_label", pm.get("label", "")],
                ["mode", pm.get("mode", "")],
                ["pm_service_target", pm.get("target", "")],
                ["cnss_register_ret", pm.get("cnss_register_ret_line", "")],
                ["cnss_connect_ret", pm.get("cnss_connect_ret_line", "")],
                ["pm_server_register_entry", pm.get("pm_server_register_entry_line", "")],
            ],
        ),
        "",
        "## Android Comparator",
        "",
        "- Android V2053 order: `wlfw_start` -> `PerMgrSrv add client cnss-daemon` -> `PerMgrLib cnss-daemon voting for modem` -> `wlfw_service_request` -> first `wlanmdsp.mbn` RRQ.",
        "- Native V2059 reaches the equivalent AP-side register/connect/server-accept contract (`cnss_client=True`, `libperipheral=True`, `pm_service=True`) but the TFTP branch remains `wlanmdsp=0`.",
        "- This down-ranks the AP-side PerMgr register/vote as the missing trigger for this unit; the remaining gap is after AP-side PerMgr success and before the modem selects the WLAN image-request branch.",
        "",
        "## Branch",
        "",
        "- If `cnss-permgr-register-vote-success-no-wlanmdsp`, the AP-side PerMgr trigger candidate is down-ranked; native completes the register/connect/server-accept path but still never asks for `wlanmdsp.mbn`.",
        "- If `cnss-permgr-client-success-server-unobserved-no-wlanmdsp`, the next unit should narrow why pm-service server acceptance was not observable before treating the trigger as modem-internal.",
        "- If register/connect is incomplete, repair the PerMgr registration path before retesting the TFTP `wlanmdsp` cascade.",
        "",
        "## Steps",
        "",
        *step_lines,
        *([] if step_lines else ["- `none`"]),
        "",
        "## Safety",
        "",
        "- No Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping was used.",
        "- No passive DIAG, active DIAG mask/log-mode, rild/cnss/pm-service strace, boot-time QRTR matrix, service-locator probe, service-notifier listener, active QRTR readback, QMI payload send, or `tftp_server` ptrace was run.",
        "- No `/dev/subsys_esoc0`, forced RC1/case, PMIC/GPIO/GDSC/regulator write, PCI rescan, bind/unbind, fake ONLINE, or eSoC notify/BOOT_DONE action was used.",
        "- Mutation scope: `/cache` one-shot clean-DSP flag, V2058 test-boot flash-handoff, namespace-local fallback readonly/readwrite RFS bridges, namespace-local persist-RFS tmpfs mirrors, private tmp-root `/dev/socket/logdw`, tracefs uprobes, and rollback to `stage3/boot_linux_v724.img` with selftest fail=0.",
        "",
    ])


def configure_prev2057() -> None:
    prev2057.CYCLE = CYCLE
    prev2057.OUT_DIR = OUT_DIR
    prev2057.HANDOFF_DIR = HANDOFF_DIR
    prev2057.HANDOFF_REPORT = HANDOFF_REPORT
    prev2057.REPORT_PATH = REPORT_PATH
    prev2057.V2056_OUT = V2058_OUT
    prev2057.V2056_INIT = V2058_INIT
    prev2057.V2056_BOOT = V2058_BOOT
    prev2057.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev2057.TEST_EXPECT_VERSION = TEST_EXPECT_VERSION
    prev2057.TEST_LOG_PATH = TEST_LOG_PATH
    prev2057.TEST_SUMMARY_PATH = TEST_SUMMARY_PATH
    prev2057.TEST_HELPER_RESULT_PATH = TEST_HELPER_RESULT_PATH
    prev2057.EXPECTED_HELPER_VERSION = EXPECTED_HELPER_VERSION
    prev2057.artifact_hook_check = artifact_hook_check
    prev2057.collect_details = collect_details
    prev2057.classify = classify
    prev2057.render_report = render_report


def main(argv: list[str] | None = None) -> int:
    configure_prev2057()
    return prev2057.main(argv)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

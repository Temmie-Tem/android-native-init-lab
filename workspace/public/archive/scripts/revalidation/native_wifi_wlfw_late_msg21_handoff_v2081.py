#!/usr/bin/env python3
"""V2081 rollbackable native handoff for the WLFW late msg21 edge."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

import native_wifi_permgr_vote_focused_handoff_v2059 as prev2059


CYCLE = "V2081"
OUT_DIR = prev2059.prev2057.prev2046.prev2035.prev1998.prev1992.prev.repo_path(
    "tmp/wifi/v2081-wlfw-late-msg21-native-handoff"
)
HANDOFF_DIR = OUT_DIR / "v2080-handoff"
HANDOFF_REPORT = OUT_DIR / "v2080-handoff-report.md"
REPORT_PATH = prev2059.prev2057.prev2046.prev2035.prev1998.prev1992.prev.repo_path(
    "docs/reports/NATIVE_INIT_V2081_WLFW_LATE_MSG21_NATIVE_HANDOFF_2026-06-05.md"
)
V2080_OUT = prev2059.prev2057.prev2046.prev2035.prev1998.prev1992.prev.repo_path(
    "tmp/wifi/v2080-wlfw-late-msg21-native-test-boot"
)
V2080_INIT = V2080_OUT / "init_v2080_wlfw_late_msg21_native"
V2080_BOOT = V2080_OUT / "boot_linux_v2080_wlfw_late_msg21_native.img"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v2080/dev/__properties__"
TEST_EXPECT_VERSION = "A90 Linux init 0.9.218 (v2080-wlfw-late-msg21-native)"
TEST_LOG_PATH = "/cache/native-init-wifi-test-boot-v2080.log"
TEST_SUMMARY_PATH = "/cache/native-init-wifi-test-boot-v2080.summary"
TEST_HELPER_RESULT_PATH = "/cache/native-init-wifi-test-boot-v2080-helper.result"
EXPECTED_HELPER_VERSION = "a90_android_execns_probe v403"

BASE_CLASSIFY = prev2059.classify
BASE_RENDER_REPORT = prev2059.render_report


def rel(path: Path) -> str:
    return prev2059.rel(path)


def intish(value: object) -> int:
    return prev2059.intish(value)


def markdown_table(headers: list[str], rows: list[list[object]]) -> str:
    return prev2059.markdown_table(headers, rows)


def msg_id(line: str) -> str:
    match = re.search(r"msg_id=(0x[0-9a-fA-F]+)", line or "")
    return match.group(1).lower() if match else ""


def collect_late_msg21(fields: dict[str, str]) -> dict[str, Any]:
    prefix = "wlfw_late_msg21_focused"
    sample_lines = [fields.get(f"{prefix}.qmi_cb.sample_{index}", "") for index in range(4)]
    data: dict[str, Any] = {
        "begin": intish(fields.get(f"{prefix}.begin")),
        "mode": fields.get(f"{prefix}.mode", ""),
        "no_diag": intish(fields.get(f"{prefix}.no_diag")),
        "no_strace": intish(fields.get(f"{prefix}.no_strace")),
        "no_qrtr_matrix": intish(fields.get(f"{prefix}.no_qrtr_matrix")),
        "no_wifi_hal": intish(fields.get(f"{prefix}.no_wifi_hal")),
        "scan_connect": intish(fields.get(f"{prefix}.scan_connect")),
        "credentials": intish(fields.get(f"{prefix}.credentials")),
        "external_ping": intish(fields.get(f"{prefix}.external_ping")),
        "qmi_hit_count": intish(fields.get(f"{prefix}.qmi_cb.hit_count")),
        "qmi_sample_count": intish(fields.get(f"{prefix}.qmi_cb.sample_count")),
        "saw_msg21": intish(fields.get(f"{prefix}.qmi_cb.saw_msg21")),
        "saw_msg2b": intish(fields.get(f"{prefix}.qmi_cb.saw_msg2b")),
        "first_line": fields.get(f"{prefix}.qmi_cb.first", ""),
        "sample_lines": sample_lines,
        "sample_msg_ids": [msg_id(line) for line in sample_lines if msg_id(line)],
        "queue_link": intish(fields.get(f"{prefix}.queue_link.hit_count")),
        "cond_signal": intish(fields.get(f"{prefix}.cond_signal.hit_count")),
        "fw_mem_flag": intish(fields.get(f"{prefix}.fw_mem_flag.hit_count")),
        "msa_flag": intish(fields.get(f"{prefix}.msa_flag.hit_count")),
        "handle_ind": intish(fields.get(f"{prefix}.handle_ind.hit_count")),
        "wlan_status": intish(fields.get(f"{prefix}.wlan_status.hit_count")),
        "wlan_version": intish(fields.get(f"{prefix}.wlan_version.hit_count")),
        "cal_return": intish(fields.get(f"{prefix}.cal_return.hit_count")),
    }
    data["first_msg_id"] = msg_id(data["first_line"])
    data["safe"] = (
        data["begin"] == 1
        and data["no_diag"] == 1
        and data["no_strace"] == 1
        and data["no_qrtr_matrix"] == 1
        and data["no_wifi_hal"] == 1
        and data["scan_connect"] == 0
        and data["credentials"] == 0
        and data["external_ping"] == 0
    )
    return data


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
        "diag_remote_dev_poll_probe.begin=1",
        "diag_wlan_pd_memory_device_probe.begin=1",
        "diag_wlan_pd_memory_regular_mask_probe.begin=1",
        "diag_dci_register_read_probe.begin=1",
        "wlan_pd_tftp_server_trace.late_attach.begin=1",
        "wifi_companion_start.wlan_pd_producer_tftp_server_syscall_trace.compiled=1",
        "PTRACE_ATTACH",
    )
    init_required = (
        "native-init-sibling-fwssctl-v641",
        "A90v641: sibling fwssctl proof armed",
        "wifi-v641-fwssctl",
        "A90v2080",
        "wifi-companion-wlan-pd-post-pm-lower-state-observer-start-only",
        "--timeout-sec",
        "75",
    )
    boot_required = (
        EXPECTED_HELPER_VERSION,
        "wlfw_late_msg21_focused.begin=1",
        "wlfw_late_msg21_focused.mode=compact-post-cal-wlfw-ready-edge",
        "wlfw_late_msg21_focused.no_diag=1",
        "wlfw_late_msg21_focused.no_strace=1",
        "wlfw_late_msg21_focused.no_qrtr_matrix=1",
        "wlfw_late_msg21_focused.qmi_cb.saw_msg21=%d",
        "wlfw_late_msg21_focused.qmi_cb.sample_0=%s",
        "per_mgr_vote_focused.begin=1",
    )
    checks: dict[str, Any] = {}
    for path, required in ((V2080_INIT, init_required), (V2080_BOOT, boot_required)):
        key = rel(path)
        forbidden_tokens = init_forbidden if path == V2080_INIT else boot_forbidden
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


def collect_details(handoff: dict[str, Any]) -> dict[str, Any]:
    details = prev2059.ORIGINAL_COLLECT_DETAILS(handoff)
    fields = prev2059.prev2057.parse_fields()
    details["per_mgr_vote_focused"] = prev2059.collect_permgr_vote(fields)
    details["wlfw_late_msg21"] = collect_late_msg21(fields)
    return details


def classify(handoff: dict[str, Any],
             hook: dict[str, Any],
             steps: list[dict[str, Any]],
             details: dict[str, Any]) -> dict[str, Any]:
    base = BASE_CLASSIFY(handoff, hook, steps, details)
    late = details.get("wlfw_late_msg21") if isinstance(details.get("wlfw_late_msg21"), dict) else {}
    cascade = details.get("cascade", {}) if isinstance(details.get("cascade"), dict) else {}
    hook_ok = all(bool(item.get("ok")) for item in hook.values())
    late_safe = bool(late.get("safe"))
    qmi_hit = intish(late.get("qmi_hit_count"))
    saw_msg21 = intish(late.get("saw_msg21")) == 1
    saw_msg2b = intish(late.get("saw_msg2b")) == 1
    cal_ok = intish(late.get("cal_return")) > 0
    fw_ready = intish(cascade.get("fw_ready")) > 0
    wlan0 = intish(cascade.get("wlan0")) > 0
    per_mgr_register_vote = (
        bool(base.get("per_mgr_server_success"))
        and bool(base.get("per_mgr_client_success"))
        and bool(base.get("per_mgr_peripheral_success"))
    )

    if not hook_ok:
        label = "wlfw-late-msg21-artifact-hook-regression"
        passed = False
        reason = "V2080 artifact does not contain the compact late-msg21 observer contract"
    elif not late_safe:
        label = "wlfw-late-msg21-safety-regression"
        passed = False
        reason = "compact late-msg21 safety markers were absent or unsafe"
    elif wlan0:
        label = "wlfw-late-msg21-native-wlan0-progress"
        passed = True
        reason = "native reached wlan0; stop before scan/connect and run a dedicated connectivity gate"
    elif saw_msg21 and fw_ready:
        label = "wlfw-late-msg21-native-fw-ready-progress"
        passed = True
        reason = "native captured late WLFW msg_id 0x21 and FW-ready; chase wlan0 next"
    elif saw_msg21:
        label = "wlfw-late-msg21-native-msg21-no-fw-ready"
        passed = True
        reason = "native captured the Android-good late WLFW msg_id 0x21 edge, but FW-ready/wlan0 did not follow"
    elif saw_msg2b and cal_ok:
        label = "wlfw-late-msg21-native-post-cal-msg2b-only-no-msg21"
        passed = True
        reason = "native completed cap/BDF/cal and saw only WLFW msg_id 0x2b, never Android-good late msg_id 0x21"
    elif qmi_hit > 0:
        label = "wlfw-late-msg21-native-qmi-callback-non-msg21"
        passed = True
        reason = "native WLFW QMI callback fired, but no Android-good msg_id 0x21 edge was observed"
    else:
        label = "wlfw-late-msg21-native-no-qmi-callback"
        passed = True
        reason = "native did not reach the WLFW QMI callback edge in the compact observer window"

    return {
        **base,
        "decision": f"v2081-{label}-rollback-{'pass' if passed else 'blocked'}",
        "label": label,
        "pass": passed,
        "reason": reason,
        "hook_ok": hook_ok,
        "late_safe": late_safe,
        "per_mgr_register_vote": per_mgr_register_vote,
        "saw_msg21": saw_msg21,
        "saw_msg2b": saw_msg2b,
        "cal_return_seen": cal_ok,
    }


def render_report(manifest: dict[str, Any]) -> str:
    details = manifest["details"]
    classification = manifest["classification"]
    late = details.get("wlfw_late_msg21", {}) if isinstance(details.get("wlfw_late_msg21"), dict) else {}
    pm = details.get("per_mgr_vote_focused", {}) if isinstance(details.get("per_mgr_vote_focused"), dict) else {}
    cascade = details.get("cascade", {}) if isinstance(details.get("cascade"), dict) else {}
    logdw = details.get("tftp_logdw", {}) if isinstance(details.get("tftp_logdw"), dict) else {}
    summary = logdw.get("summary", {}) if isinstance(logdw.get("summary"), dict) else {}
    step_lines = [
        f"- `{step['name']}` rc `{step['rc']}` ok `{step['ok']}` evidence `{step['file']}`"
        for step in manifest["steps"]
    ]
    return "\n".join([
        "# Native Init V2081 WLFW Late Msg21 Native Handoff",
        "",
        "## Summary",
        "",
        "- Cycle: `V2081`",
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
                ["route", classification.get("route_ok"), f"hook={classification.get('hook_ok')} late_safe={classification.get('late_safe')}"],
                ["per_mgr", classification.get("per_mgr_server_success"), f"cnss={classification.get('per_mgr_client_success')} peripheral={classification.get('per_mgr_peripheral_success')}"],
                ["late_msg21", classification.get("saw_msg21"), f"qmi_hit={late.get('qmi_hit_count')} sample_ids={late.get('sample_msg_ids')} first={late.get('first_msg_id')}"],
                ["msg2b_seen", classification.get("saw_msg2b"), f"cal_return={late.get('cal_return')} queue={late.get('queue_link')} cond={late.get('cond_signal')}"],
                ["tftp_branch", "", f"server_check={summary.get('server_check')} ota={summary.get('ota_firewall')} mcfg={summary.get('mcfg')} wlanmdsp={summary.get('wlanmdsp')}"],
                ["cascade", "", f"wlan_pd={cascade.get('wlan_pd_up')} icnss_qmi={cascade.get('icnss_qmi_connected')} fw_ready={cascade.get('fw_ready')} wlan0={cascade.get('wlan0')}"],
            ],
        ),
        "",
        "## PerMgr Vote Edge",
        "",
        markdown_table(
            ["field", "value"],
            [
                ["label", pm.get("label", "")],
                ["cnss_register_success", pm.get("cnss_register_success", "")],
                ["cnss_connect_success", pm.get("cnss_connect_success", "")],
                ["pm_server_register_success", pm.get("pm_server_register_success", "")],
                ["peripheral_register_success", pm.get("peripheral_register_success", "")],
                ["pm_vote_ack_seen", pm.get("pm_vote_ack_seen", "")],
                ["cnss_register_ret", pm.get("cnss_register_ret_line", "")],
                ["cnss_connect_ret", pm.get("cnss_connect_ret_line", "")],
            ],
        ),
        "",
        "## Late WLFW Edge",
        "",
        markdown_table(
            ["field", "value"],
            [
                ["mode", late.get("mode", "")],
                ["qmi_hit_count", late.get("qmi_hit_count", "")],
                ["qmi_sample_count", late.get("qmi_sample_count", "")],
                ["saw_msg21", late.get("saw_msg21", "")],
                ["saw_msg2b", late.get("saw_msg2b", "")],
                ["first_line", late.get("first_line", "")],
                ["sample_0", (late.get("sample_lines") or [""])[0] if late.get("sample_lines") else ""],
                ["sample_1", (late.get("sample_lines") or ["", ""])[1] if len(late.get("sample_lines") or []) > 1 else ""],
                ["sample_2", (late.get("sample_lines") or ["", "", ""])[2] if len(late.get("sample_lines") or []) > 2 else ""],
                ["sample_3", (late.get("sample_lines") or ["", "", "", ""])[3] if len(late.get("sample_lines") or []) > 3 else ""],
                ["status_version", f"status={late.get('wlan_status')} version={late.get('wlan_version')} handle={late.get('handle_ind')}"],
            ],
        ),
        "",
        "## Comparator",
        "",
        "- Android V2079 reached `wlanmdsp`/BDF/FW-ready/`wlan0` and captured late `wlfw_qmi_ind_cb_entry msg_id=0x21 payload_len=0x0`.",
        "- Native V2081 confirms cnss-daemon PerMgr register/connect returned `rc=0`, pm-service accepted the cnss client, and the PM vote ACK path was seen.",
        "- Native V2081 uses the same internal-modem route without DIAG/strace/QRTR matrix and emits compact samples before stdout truncation.",
        "- If native remains `0x2b`-only after cap/BDF/cal, the missing edge is the modem/WLFW ready-publication condition, not AP PerMgr registration.",
        "",
        "## Branch",
        "",
        "- `wlfw-late-msg21-native-post-cal-msg2b-only-no-msg21`: target why the WLAN PD/modem never publishes the Android-good late `0x21` ready indication.",
        "- `wlfw-late-msg21-native-msg21-no-fw-ready`: chase the immediate kernel FW-ready publication after `0x21`.",
        "- `wlfw-late-msg21-native-wlan0-progress`: stop before scan/connect and run the dedicated connectivity gate.",
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
        "- Mutation scope: `/cache` one-shot clean-DSP flag, V2080 test-boot flash-handoff, namespace-local fallback readonly/readwrite RFS bridges, namespace-local persist-RFS tmpfs mirrors, private tmp-root `/dev/socket/logdw`, tracefs uprobes, compact WLFW late-edge summary, and rollback to `stage3/boot_linux_v724.img` with selftest fail=0.",
        "",
    ])


def configure_prev2059() -> None:
    prev2059.CYCLE = CYCLE
    prev2059.OUT_DIR = OUT_DIR
    prev2059.HANDOFF_DIR = HANDOFF_DIR
    prev2059.HANDOFF_REPORT = HANDOFF_REPORT
    prev2059.REPORT_PATH = REPORT_PATH
    prev2059.V2058_OUT = V2080_OUT
    prev2059.V2058_INIT = V2080_INIT
    prev2059.V2058_BOOT = V2080_BOOT
    prev2059.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev2059.TEST_EXPECT_VERSION = TEST_EXPECT_VERSION
    prev2059.TEST_LOG_PATH = TEST_LOG_PATH
    prev2059.TEST_SUMMARY_PATH = TEST_SUMMARY_PATH
    prev2059.TEST_HELPER_RESULT_PATH = TEST_HELPER_RESULT_PATH
    prev2059.EXPECTED_HELPER_VERSION = EXPECTED_HELPER_VERSION
    prev2059.artifact_hook_check = artifact_hook_check
    prev2059.collect_details = collect_details
    prev2059.classify = classify
    prev2059.render_report = render_report


def main(argv: list[str] | None = None) -> int:
    configure_prev2059()
    return prev2059.main(argv)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

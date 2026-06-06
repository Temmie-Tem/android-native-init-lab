#!/usr/bin/env python3
"""V2121 rollbackable handoff for the dual-RFS shared server_info bridge."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

import native_wifi_dual_rfs_leaf_precreate_handoff_v2113 as prev2113


CYCLE = "V2121"
REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v2121-dual-rfs-shared-server-info-handoff"
HANDOFF_DIR = OUT_DIR / "v2120-handoff"
HANDOFF_REPORT = OUT_DIR / "v2120-handoff-report.md"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V2121_DUAL_RFS_SHARED_SERVER_INFO_HANDOFF_2026-06-05.md"
)
V2120_OUT = REPO_ROOT / "tmp" / "wifi" / "v2120-dual-rfs-shared-server-info-test-boot"
V2120_INIT = V2120_OUT / "init_v2120_dual_rfs_shared_server_info"
V2120_BOOT = V2120_OUT / "boot_linux_v2120_dual_rfs_shared_server_info.img"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v2120/dev/__properties__"
TEST_EXPECT_VERSION = "A90 Linux init 0.9.235 (v2120-dual-rfs-shared-server-info)"
TEST_LOG_PATH = "/cache/native-init-wifi-test-boot-v2120.log"
TEST_SUMMARY_PATH = "/cache/native-init-wifi-test-boot-v2120.summary"
TEST_HELPER_RESULT_PATH = "/cache/native-init-wifi-test-boot-v2120-helper.result"
EXPECTED_HELPER_VERSION = "a90_android_execns_probe v419"
FIELD_PREFIX = "wlan_pd_firmware_serve_gate.rfs_bridge.shared_server_info."

ORIGINAL_COLLECT_DETAILS = prev2113.collect_details
ORIGINAL_CLASSIFY = prev2113.classify


def rel(path: Path) -> str:
    return prev2113.rel(path)


def intish(value: object) -> int:
    return prev2113.intish(value)


def markdown_table(headers: list[str], rows: list[list[object]]) -> str:
    return prev2113.markdown_table(headers, rows)


def artifact_hook_check() -> dict[str, Any]:
    init_required = (
        "native-init-sibling-fwssctl-v641",
        "A90v641: sibling fwssctl proof armed",
        "wifi-v641-fwssctl",
        "A90v2120",
        "wifi-companion-wlan-pd-post-pm-lower-state-observer-start-only",
        "--timeout-sec",
        "75",
    )
    init_forbidden = (
        "--allow-servloc-domain-list-probe",
        "--allow-service-notifier-listener-probe",
        "--qrtr-readback-matrix",
        "wlfw:69:0,1",
        "--pm-observer-private-cnss-daemon-sdx50m",
        "--private-cnss-daemon-path",
    )
    boot_required = (
        EXPECTED_HELPER_VERSION,
        "android_parity=firmware_mnt_probe_present_firmware_fallback_present",
        "probe.absolute=/vendor/rfs/msm/mpss/readonly/vendor/firmware_mnt/image/wlanmdsp.mbn",
        "fallback.absolute=/vendor/rfs/msm/mpss/readonly/vendor/firmware/wlanmdsp.mbn",
        "shared_server_info.tmpfs_requested=1",
        "shared_server_info.absolute=/vendor/rfs/msm/mpss/shared/server_info.txt",
        "shared_server_info.rootfs_namespace_only=1",
        "shared_server_info.sda29_write=0",
        "wifi_companion_start.tftp_shared_server_info_tmpfs.enabled=%d",
        "wifi_companion_start.tftp_shared_server_info_tmpfs.path=/vendor/rfs/msm/mpss/shared/server_info.txt",
        "vendor_rfs_shared_server_info",
        "wifi_companion_start.tftp_persist_rfs_leaf_precreate.enabled=%d",
        "wifi_companion_start.tftp_process_namespace_audit.compiled=%d",
        "persist_rfs_mdm_mpss",
        "persist_rfs_apq_gnss",
        "tftp_ready_before_wlfw_vote.mode=alive-socket-plus-android-order-settle",
        "tftp_logdw_sink.order_timestamps=1",
        "per_mgr_vote_focused.begin=1",
        "wlfw_late_msg21_focused.begin=1",
        "icnss_qcacld_post_bdf_focused",
    )
    boot_forbidden = (
        "diag_remote_dev_poll_probe.begin=1",
        "diag_wlan_pd_memory_device_probe.begin=1",
        "diag_wlan_pd_memory_regular_mask_probe.begin=1",
        "diag_dci_register_read_probe.begin=1",
        "wlan_pd_tftp_server_trace.late_attach.begin=1",
        "wifi_companion_start.wlan_pd_producer_tftp_server_syscall_trace.compiled=1",
        "wifi_companion_start.macloader_syscall_trace.compiled=1",
        "PTRACE_ATTACH",
        "post_bdf_boot_wlan_consumer_gate.begin=1",
        "ota_firewall/ruleset:",
        "tftp_server-android-runtime",
    )
    checks: dict[str, Any] = {}
    for path, required in ((V2120_INIT, init_required), (V2120_BOOT, boot_required)):
        key = rel(path)
        forbidden_tokens = init_forbidden if path == V2120_INIT else boot_forbidden
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


def parse_shared_server_info_fields() -> dict[str, str]:
    result_path = HANDOFF_DIR / "test-v1393-helper-result.stdout.txt"
    if not result_path.exists():
        return {"_present": "0", "_path": rel(result_path)}
    text = result_path.read_text(encoding="utf-8", errors="replace")
    fields: dict[str, str] = {"_present": "1", "_path": rel(result_path)}
    pattern = re.compile(re.escape(FIELD_PREFIX) + r"([A-Za-z0-9_.-]+)=([^\r\n]*)")
    for match in pattern.finditer(text):
        fields[match.group(1)] = match.group(2).strip()
    return fields


def collect_details(handoff: dict[str, Any]) -> dict[str, Any]:
    details = ORIGINAL_COLLECT_DETAILS(handoff)
    shared = parse_shared_server_info_fields()
    records = details.get("tftp_logdw", {}).get("records", []) if isinstance(details.get("tftp_logdw"), dict) else []
    server_info_errors = [
        item for item in records
        if isinstance(item, dict)
        and (
            "server_info.txt" in str(item.get("payload", ""))
            or "Info file creation failed" in str(item.get("payload", ""))
        )
    ]
    details["shared_server_info_bridge"] = {
        "tmpfs_requested": intish(shared.get("tmpfs_requested")),
        "dir_exists": intish(shared.get("dir_exists")),
        "dir_is_dir": intish(shared.get("dir_is_dir")),
        "dir_mode": shared.get("dir_mode", ""),
        "dir_uid": shared.get("dir_uid", ""),
        "dir_gid": shared.get("dir_gid", ""),
        "exists": intish(shared.get("exists")),
        "is_reg": intish(shared.get("is_reg")),
        "size": shared.get("size", ""),
        "mode": shared.get("mode", ""),
        "uid": shared.get("uid", ""),
        "gid": shared.get("gid", ""),
        "stat_errno": intish(shared.get("stat_errno")),
        "stat_error": shared.get("stat_error", ""),
        "rootfs_namespace_only": intish(shared.get("rootfs_namespace_only")),
        "sda29_write": intish(shared.get("sda29_write")),
        "source": shared.get("_path", ""),
    }
    details["server_info_startup_error_count"] = len(server_info_errors)
    details["server_info_startup_error_payloads"] = [
        str(item.get("payload", "")) for item in server_info_errors[:4]
    ]
    return details


def shared_server_info_ok(details: dict[str, Any]) -> bool:
    shared = details.get("shared_server_info_bridge") if isinstance(details.get("shared_server_info_bridge"), dict) else {}
    return (
        intish(shared.get("tmpfs_requested")) == 1
        and intish(shared.get("dir_exists")) == 1
        and intish(shared.get("dir_is_dir")) == 1
        and intish(shared.get("exists")) == 1
        and intish(shared.get("is_reg")) == 1
        and intish(shared.get("stat_errno")) == 0
        and intish(shared.get("rootfs_namespace_only")) == 1
        and intish(shared.get("sda29_write")) == 0
    )


def post_cal_value(details: dict[str, Any], key: str) -> str:
    post_cal = details.get("post_cal_indication") if isinstance(details.get("post_cal_indication"), dict) else {}
    return str(post_cal.get(key, ""))


def post_cal_hit(details: dict[str, Any], group: str, event: str) -> int:
    post_cal = details.get("post_cal_indication") if isinstance(details.get("post_cal_indication"), dict) else {}
    events = post_cal.get(group) if isinstance(post_cal.get(group), dict) else {}
    item = events.get(event) if isinstance(events.get(event), dict) else {}
    return intish(item.get("hit_count"))


def classify(handoff: dict[str, Any],
             hook: dict[str, Any],
             steps: list[dict[str, Any]],
             details: dict[str, Any]) -> dict[str, Any]:
    base = ORIGINAL_CLASSIFY(handoff, hook, steps, details)
    cascade = details.get("cascade") if isinstance(details.get("cascade"), dict) else {}
    branch = details.get("tftp_tombstone_branch") if isinstance(details.get("tftp_tombstone_branch"), dict) else {}
    fw_ready = intish(cascade.get("fw_ready")) > 0
    wlan0 = intish(cascade.get("wlan0")) > 0
    wlanmdsp_seen = bool(base.get("wlanmdsp_seen"))
    ota_seen = bool(base.get("ota_seen"))
    server_payload = str(branch.get("server_check", {}).get("payload", ""))
    shared_ok = shared_server_info_ok(details)
    server_info_error_count = intish(details.get("server_info_startup_error_count"))
    cap_success = post_cal_value(details, "cap_return_rc") == "0x0"
    bdf_success = (
        post_cal_value(details, "bdf_return_rc") == "0x0"
        and post_cal_value(details, "bdf_qmi_result") == "0x0"
        and post_cal_hit(details, "bdf_events", "wlfw_bdf_send_ret") > 0
    )
    cal_success = post_cal_value(details, "cal_return_rc") == "0x0"
    fw_mem_ind = post_cal_hit(details, "ind_events", "wlfw_qmi_ind_fw_mem_flag") > 0
    worker_done = post_cal_hit(details, "ind_events", "wlfw_worker_done_signal") > 0

    if not base.get("hook_ok"):
        label = "shared-server-info-artifact-hook-regression"
        passed = False
        reason = "V2120 artifact does not contain the bounded shared server_info bridge contract"
    elif not shared_ok:
        label = "shared-server-info-bridge-missing"
        passed = False
        reason = "namespace-local `/vendor/rfs/msm/mpss/shared/server_info.txt` was not present/readable in the helper snapshot"
    elif server_info_error_count > 0:
        label = "shared-server-info-startup-error-persists"
        passed = False
        reason = "tftp_server still logged server_info startup failure despite the shared tmpfs bridge"
    elif wlan0:
        label = "shared-server-info-wlan0-progress"
        passed = True
        reason = "native reached wlan0; stop before scan/connect and run the dedicated connectivity gate"
    elif fw_ready:
        label = "shared-server-info-fw-ready-progress"
        passed = True
        reason = "native reached FW_READY; chase wlan0 next"
    elif wlanmdsp_seen:
        label = "shared-server-info-wlanmdsp-progress"
        passed = True
        reason = "shared server_info bridge produced a visible wlanmdsp TFTP request"
    elif bdf_success and not fw_ready:
        label = "shared-server-info-post-bdf-no-fw-ready"
        passed = True
        reason = "server_info startup errors cleared and WLFW cap/BDF/cal succeeded, but FW_READY/wlan0 still never appeared"
    elif ota_seen:
        label = "shared-server-info-ota-progress-no-wlanmdsp"
        passed = True
        reason = "shared server_info bridge reached ota_firewall but not wlanmdsp"
    elif server_payload == "hello":
        label = "shared-server-info-cleared-post-up-server-check-no-wlanmdsp"
        passed = True
        reason = "server_info startup errors cleared, but native still only shows late post-UP server_check and no ota/wlanmdsp"
    else:
        label = "shared-server-info-cleared-no-android-order-branch"
        passed = True
        reason = "server_info startup errors cleared, but Android-order TFTP bootstrap still did not appear"

    return {
        **base,
        "decision": f"v2121-{label}-rollback-{'pass' if passed else 'blocked'}",
        "label": label,
        "pass": passed,
        "reason": reason,
        "shared_server_info_bridge_ok": shared_ok,
        "server_info_startup_error_count": server_info_error_count,
        "cap_success": cap_success,
        "bdf_success": bdf_success,
        "cal_success": cal_success,
        "fw_mem_ind": fw_mem_ind,
        "wlfw_worker_done": worker_done,
    }


def render_report(manifest: dict[str, Any]) -> str:
    details = manifest["details"]
    classification = manifest["classification"]
    ns = details.get("tftp_process_namespace_audit", {}) if isinstance(details.get("tftp_process_namespace_audit"), dict) else {}
    paths = ns.get("paths", {}) if isinstance(ns.get("paths"), dict) else {}
    cascade = details.get("cascade", {}) if isinstance(details.get("cascade"), dict) else {}
    branch = details.get("tftp_tombstone_branch", {}) if isinstance(details.get("tftp_tombstone_branch"), dict) else {}
    bridge = details.get("dual_rfs_bridge", {}) if isinstance(details.get("dual_rfs_bridge"), dict) else {}
    shared = details.get("shared_server_info_bridge", {}) if isinstance(details.get("shared_server_info_bridge"), dict) else {}
    post_cal = details.get("post_cal_indication", {}) if isinstance(details.get("post_cal_indication"), dict) else {}
    step_lines = [
        f"- `{step['name']}` rc `{step['rc']}` ok `{step['ok']}` evidence `{step['file']}`"
        for step in manifest["steps"]
    ]
    selected_paths = [
        "vendor_rfs_readwrite",
        "persist_rfs_shared",
        "persist_rfs_msm_mpss",
        "persist_rfs_mdm_mpss",
        "persist_rfs_apq_gnss",
    ]
    return "\n".join([
        "# Native Init V2121 Dual-RFS Shared Server Info Handoff",
        "",
        "## Summary",
        "",
        "- Cycle: `V2121`",
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
                ["artifact", classification.get("hook_ok"), f"helper={EXPECTED_HELPER_VERSION}"],
                ["dual_rfs", classification.get("dual_rfs_bridge_ok"), f"bridge={bridge}"],
                ["shared_server_info", classification.get("shared_server_info_bridge_ok"), f"shared={shared}"],
                ["startup_error", classification.get("server_info_startup_error_count"), f"payloads={details.get('server_info_startup_error_payloads')}"],
                ["tftp_branch", "", f"server_check={branch.get('server_check')} ota={classification.get('ota_seen')} wlanmdsp={classification.get('wlanmdsp_seen')}"],
                ["post_bdf", classification.get("bdf_success"), f"cap={classification.get('cap_success')} bdf_rc={post_cal.get('bdf_return_rc')} bdf_qmi={post_cal.get('bdf_qmi_result')} cal={classification.get('cal_success')} fw_mem_ind={classification.get('fw_mem_ind')} worker_done={classification.get('wlfw_worker_done')} dms_addr_qmi={post_cal.get('dms_addr_qmi_result')}"],
                ["cascade", "", f"wlan_pd={cascade.get('wlan_pd_up')} icnss_qmi={cascade.get('icnss_qmi_connected')} wlfw69={cascade.get('wlfw69')} fw_ready={cascade.get('fw_ready')} wlan0={cascade.get('wlan0')}"],
            ],
        ),
        "",
        "## Shared Snapshot",
        "",
        markdown_table(
            ["field", "value"],
            [
                ["tmpfs_requested", shared.get("tmpfs_requested")],
                ["dir_exists", shared.get("dir_exists")],
                ["dir_mode", shared.get("dir_mode")],
                ["dir_uid_gid", f"{shared.get('dir_uid')}:{shared.get('dir_gid')}"],
                ["file_exists", shared.get("exists")],
                ["file_mode", shared.get("mode")],
                ["file_uid_gid", f"{shared.get('uid')}:{shared.get('gid')}"],
                ["stat_errno", shared.get("stat_errno")],
                ["rootfs_namespace_only", shared.get("rootfs_namespace_only")],
                ["sda29_write", shared.get("sda29_write")],
                ["source", shared.get("source")],
            ],
        ),
        "",
        "## Process-Root Paths",
        "",
        markdown_table(
            ["path", "exists", "dir", "mode", "uid", "gid", "errno"],
            [
                [name, item.get("exists"), item.get("is_dir"), item.get("mode"), item.get("uid"), item.get("gid"), item.get("errno")]
                for name in selected_paths
                for item in [paths.get(name, {})]
                if isinstance(item, dict)
            ],
        ),
        "",
        "## Interpretation",
        "",
        "- V2121 tests only whether the missing `/vendor/rfs/msm/mpss/shared/server_info.txt` startup path was blocking stock `tftp_server` from the Android-order TFTP branch.",
        "- A `wlanmdsp`/FW-ready/`wlan0` label is progress toward the final native Wi-Fi goal; a cleared-but-post-UP-only label falsifies this startup file as the producer trigger.",
        "- This run remains light/passive: no `tftp_server` ptrace, no boot-time QRTR matrix, no AP QMI send, and no Wi-Fi HAL/scan/connect.",
        "",
        "## Remaining Blocker",
        "",
        "- `server_info.txt` is no longer a startup error, and native now reaches WLFW client init, FW-mem indication, cap success, BDF send/return success, and cal-only success.",
        "- The remaining blocker moved downstream: after post-BDF/cal success, native still has no FW_READY and no `wlan0`; the next useful gate is the missing post-BDF FW-ready/status transition, not another mcfg/server_info/AP-side strace loop.",
        "",
        "## Steps",
        "",
        *step_lines,
        *([] if step_lines else ["- `none`"]),
        "",
        "## Safety",
        "",
        "- No Wi-Fi HAL, wificond, supplicant, hostapd, scan/connect, credentials, DHCP/routes, or external ping was used.",
        "- No macloader retry, DIAG, rild/cnss/pm-service strace, boot-time QRTR matrix, service-locator probe, service-notifier listener, active QRTR readback, QMI payload send, or `tftp_server` ptrace was run.",
        "- No `/dev/subsys_esoc0`, forced RC1/case, PMIC/GPIO/GDSC/regulator write, PCI rescan, bind/unbind, fake ONLINE, or eSoC notify/BOOT_DONE action was used.",
        "- Mutation scope: `/cache` one-shot clean-DSP flag, V2120 test-boot flash-handoff, namespace-local RFS bridges/tmpfs mirrors, namespace-local shared `server_info.txt` tmpfs, namespace-local persist-RFS leaf precreate in the private rootfs, read-only tftp process-root audit, and rollback to `stage3/boot_linux_v724.img` with selftest fail=0.",
        "",
    ])


def configure_prev2113() -> None:
    prev2113.CYCLE = CYCLE
    prev2113.OUT_DIR = OUT_DIR
    prev2113.HANDOFF_DIR = HANDOFF_DIR
    prev2113.HANDOFF_REPORT = HANDOFF_REPORT
    prev2113.REPORT_PATH = REPORT_PATH
    prev2113.V2112_OUT = V2120_OUT
    prev2113.V2112_INIT = V2120_INIT
    prev2113.V2112_BOOT = V2120_BOOT
    prev2113.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev2113.TEST_EXPECT_VERSION = TEST_EXPECT_VERSION
    prev2113.TEST_LOG_PATH = TEST_LOG_PATH
    prev2113.TEST_SUMMARY_PATH = TEST_SUMMARY_PATH
    prev2113.TEST_HELPER_RESULT_PATH = TEST_HELPER_RESULT_PATH
    prev2113.EXPECTED_HELPER_VERSION = EXPECTED_HELPER_VERSION
    prev2113.BRIDGE_CAPTURE = OUT_DIR / "host" / "v2121-autostart-bridge.log"
    prev2113.BRIDGE_STDOUT = OUT_DIR / "host" / "v2121-autostart-bridge.stdout.txt"
    prev2113.BRIDGE_STDERR = OUT_DIR / "host" / "v2121-autostart-bridge.stderr.txt"
    prev2113.BRIDGE_PID = OUT_DIR / "host" / "v2121-autostart-bridge.pid"
    prev2113.artifact_hook_check = artifact_hook_check
    prev2113.collect_details = collect_details
    prev2113.classify = classify
    prev2113.render_report = render_report


def main(argv: list[str] | None = None) -> int:
    configure_prev2113()
    return prev2113.main(argv)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

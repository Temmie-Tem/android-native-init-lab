#!/usr/bin/env python3
"""V2101 rollbackable handoff for TFTP persist-RFS auto-dir parity."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import native_wifi_tftp_tombstone_vendor_perms_handoff_v2098 as prev2098


CYCLE = "V2101"
REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v2101-tftp-persist-rfs-autodir-handoff"
HANDOFF_DIR = OUT_DIR / "v2100-handoff"
HANDOFF_REPORT = OUT_DIR / "v2100-handoff-report.md"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V2101_TFTP_PERSIST_RFS_AUTODIR_HANDOFF_2026-06-05.md"
)
V2100_OUT = REPO_ROOT / "tmp" / "wifi" / "v2100-tftp-persist-rfs-autodir-parity-test-boot"
V2100_INIT = V2100_OUT / "init_v2100_tftp_persist_rfs_autodir_parity"
V2100_BOOT = V2100_OUT / "boot_linux_v2100_tftp_persist_rfs_autodir_parity.img"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v2100/dev/__properties__"
TEST_EXPECT_VERSION = "A90 Linux init 0.9.227 (v2100-tftp-persist-rfs-autodir-parity)"
TEST_LOG_PATH = "/cache/native-init-wifi-test-boot-v2100.log"
TEST_SUMMARY_PATH = "/cache/native-init-wifi-test-boot-v2100.summary"
TEST_HELPER_RESULT_PATH = "/cache/native-init-wifi-test-boot-v2100-helper.result"
EXPECTED_HELPER_VERSION = "a90_android_execns_probe v411"


def rel(path: Path) -> str:
    return prev2098.rel(path)


def intish(value: object) -> int:
    return prev2098.intish(value)


def markdown_table(headers: list[str], rows: list[list[object]]) -> str:
    return prev2098.markdown_table(headers, rows)


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
        "wifi_companion_start.macloader_syscall_trace.compiled=1",
        "PTRACE_ATTACH",
    )
    init_required = (
        "native-init-sibling-fwssctl-v641",
        "A90v641: sibling fwssctl proof armed",
        "wifi-v641-fwssctl",
        "A90v2100",
        "wifi-companion-wlan-pd-post-pm-lower-state-observer-start-only",
        "--timeout-sec",
        "75",
    )
    boot_required = (
        EXPECTED_HELPER_VERSION,
        "wifi_companion_start.tftp_tombstone_rfs_tmpfs.enabled=%d",
        "wifi_companion_start.tftp_tombstone_rfs_tmpfs.vendor_rfs_perms=%d",
        "wifi_companion_start.tftp_tombstone_rfs_tmpfs.rootfs_namespace_only=1",
        "%s.persist_rfs.autodir_parity=%d",
        "persist-rfs-shared",
        "persist-rfs-msm-mpss",
        "persist-rfs-msm-adsp",
        "tftp_readwrite_transition.mode=read-only-stat-open-on-change",
        "tftp_ready_before_wlfw_vote.mode=alive-socket-plus-android-order-settle",
        "tftp_logdw_sink.order_timestamps=1",
        "per_mgr_vote_focused.begin=1",
        "wlfw_late_msg21_focused.begin=1",
        "icnss_qcacld_post_bdf_focused",
    )
    checks: dict[str, Any] = {}
    for path, required in ((V2100_INIT, init_required), (V2100_BOOT, boot_required)):
        key = rel(path)
        forbidden_tokens = init_forbidden if path == V2100_INIT else boot_forbidden
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
    return prev2098.collect_details(handoff)


def classify(handoff: dict[str, Any],
             hook: dict[str, Any],
             steps: list[dict[str, Any]],
             details: dict[str, Any]) -> dict[str, Any]:
    base = prev2098.classify(handoff, hook, steps, details)
    tombstone = details.get("tftp_tombstone_rfs_tmpfs") if isinstance(details.get("tftp_tombstone_rfs_tmpfs"), dict) else {}
    branch = details.get("tftp_tombstone_branch") if isinstance(details.get("tftp_tombstone_branch"), dict) else {}
    cascade = details.get("cascade") if isinstance(details.get("cascade"), dict) else {}
    hook_ok = all(bool(item.get("ok")) for item in hook.values())
    tombstone_auto_dir = intish(tombstone.get("auto_dir_error_count"))
    tombstone_mkdir = intish(tombstone.get("mkdir_failed_count"))
    persist_auto_dir = intish(tombstone.get("persist_auto_dir_error_count"))
    persist_mkdir = intish(tombstone.get("persist_mkdir_failed_count"))
    wlanmdsp_seen = bool(base.get("wlanmdsp_seen"))
    ota_seen = bool(base.get("ota_seen"))
    server_payload = str(branch.get("server_check", {}).get("payload", ""))
    post_up_server = branch.get("server_after_wlan_pd_ms")
    fw_ready = intish(cascade.get("fw_ready")) > 0
    wlan0 = intish(cascade.get("wlan0")) > 0

    if not hook_ok:
        label = "persist-rfs-autodir-artifact-hook-regression"
        passed = False
        reason = "V2100 artifact does not contain the bounded persist-RFS auto-dir parity contract"
    elif wlan0:
        label = "persist-rfs-autodir-wlan0-progress"
        passed = True
        reason = "native reached wlan0; stop before scan/connect and run the dedicated connectivity gate"
    elif fw_ready:
        label = "persist-rfs-autodir-fw-ready-progress"
        passed = True
        reason = "native reached FW_READY; chase wlan0 next"
    elif wlanmdsp_seen:
        label = "persist-rfs-autodir-wlanmdsp-progress"
        passed = True
        reason = "clearing persist-RFS auto-dir failures allowed a wlanmdsp tftp request"
    elif ota_seen:
        label = "persist-rfs-autodir-early-branch-progress-no-wlanmdsp"
        passed = True
        reason = "clearing persist-RFS auto-dir failures reached ota_firewall, but not wlanmdsp"
    elif persist_auto_dir > 0 or persist_mkdir > 0:
        label = "persist-rfs-autodir-still-fails"
        passed = True
        reason = "persist-RFS auto-dir EACCES remains; the namespace precreate did not clear tftp_server startup setup"
    elif tombstone_auto_dir == 0 and tombstone_mkdir == 0 and server_payload == "hello" and isinstance(post_up_server, int) and post_up_server > 0:
        label = "persist-rfs-autodir-no-effect-post-up-server-check"
        passed = True
        reason = "tftp_server startup auto-dir failures cleared, but native still only shows late post-UP server_check and no ota/wlanmdsp"
    else:
        label = "persist-rfs-autodir-no-early-tftp-branch"
        passed = True
        reason = "persist-RFS auto-dir parity did not produce Android's early tftp branch"

    return {
        **base,
        "decision": f"v2101-{label}-rollback-{'pass' if passed else 'blocked'}",
        "label": label,
        "pass": passed,
        "reason": reason,
        "hook_ok": hook_ok,
        "persist_auto_dir_error_count": persist_auto_dir,
        "persist_mkdir_failed_count": persist_mkdir,
        "tombstone_auto_dir_error_count": tombstone_auto_dir,
        "tombstone_mkdir_failed_count": tombstone_mkdir,
        "server_check_payload": server_payload,
        "server_after_wlan_pd_ms": post_up_server,
    }


def render_report(manifest: dict[str, Any]) -> str:
    details = manifest["details"]
    classification = manifest["classification"]
    tombstone = details.get("tftp_tombstone_rfs_tmpfs", {}) if isinstance(details.get("tftp_tombstone_rfs_tmpfs"), dict) else {}
    branch = details.get("tftp_tombstone_branch", {}) if isinstance(details.get("tftp_tombstone_branch"), dict) else {}
    cascade = details.get("cascade", {}) if isinstance(details.get("cascade"), dict) else {}
    summary = prev2098.prev2096.prev2083.logdw_summary(details)
    step_lines = [
        f"- `{step['name']}` rc `{step['rc']}` ok `{step['ok']}` evidence `{step['file']}`"
        for step in manifest["steps"]
    ]
    return "\n".join([
        "# Native Init V2101 TFTP Persist-RFS Auto-Dir Handoff",
        "",
        "## Summary",
        "",
        "- Cycle: `V2101`",
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
                ["persist_auto_dir", classification.get("persist_auto_dir_error_count"), f"mkdir_failed={classification.get('persist_mkdir_failed_count')} total_auto_dir={tombstone.get('total_auto_dir_error_count')}"],
                ["tombstone_auto_dir", classification.get("tombstone_auto_dir_error_count"), f"mkdir_failed={classification.get('tombstone_mkdir_failed_count')} tokens={tombstone.get('tombstone_token_count')}"],
                ["server_check", classification.get("server_check_payload"), f"after_wlan_pd_ms={classification.get('server_after_wlan_pd_ms')} logdw={branch.get('logdw_server_check')}"],
                ["ota_firewall", classification.get("ota_seen"), f"logdw={branch.get('logdw_ota_firewall')} file={branch.get('ota', {}).get('index')}"],
                ["wlanmdsp", classification.get("wlanmdsp_seen"), f"logdw={branch.get('logdw_wlanmdsp')} summary={summary.get('wlanmdsp')}/{summary.get('fallback_wlanmdsp')}"],
                ["cascade", "", f"wlan_pd={cascade.get('wlan_pd_up')} icnss_qmi={cascade.get('icnss_qmi_connected')} fw_ready={cascade.get('fw_ready')} wlan0={cascade.get('wlan0')}"],
            ],
        ),
        "",
        "## Interpretation",
        "",
        "- This is the bounded follow-up to V2099: only the remaining persist-RFS auto-dir startup failures are pre-created in the namespace.",
        "- If this clears persist auto-dir but stays `no-effect-post-up-server-check`, tftp_server startup directory parity is not the producer trigger.",
        "- The remaining primary question then returns to modem-internal state before Android's pre-spawn `server_check -> ota_firewall -> wlanmdsp` branch.",
        "",
        "## Steps",
        "",
        *step_lines,
        *([] if step_lines else ["- `none`"]),
        "",
        "## Safety",
        "",
        "- No Wi-Fi HAL, wificond, supplicant, hostapd, scan/connect, credentials, DHCP/routes, or external ping was used.",
        "- No macloader retry, passive DIAG, active DIAG mask/log-mode, rild/cnss/pm-service strace, boot-time QRTR matrix, service-locator probe, service-notifier listener, active QRTR readback, QMI payload send, or `tftp_server` ptrace was run.",
        "- No `/dev/subsys_esoc0`, forced RC1/case, PMIC/GPIO/GDSC/regulator write, PCI rescan, bind/unbind, fake ONLINE, or eSoC notify/BOOT_DONE action was used.",
        "- Mutation scope: `/cache` one-shot clean-DSP flag, V2100 test-boot flash-handoff, namespace-local RFS bridges/tmpfs mirrors including persist-RFS auto-dir targets, private tmp-root `/dev/socket/logdw`, tracefs uprobes, and rollback to `stage3/boot_linux_v724.img` with selftest fail=0.",
        "",
    ])


def configure_prev2081() -> None:
    prev2098.prev2096.prev2083.prev2081.CYCLE = CYCLE
    prev2098.prev2096.prev2083.prev2081.OUT_DIR = OUT_DIR
    prev2098.prev2096.prev2083.prev2081.HANDOFF_DIR = HANDOFF_DIR
    prev2098.prev2096.prev2083.prev2081.HANDOFF_REPORT = HANDOFF_REPORT
    prev2098.prev2096.prev2083.prev2081.REPORT_PATH = REPORT_PATH
    prev2098.prev2096.prev2083.prev2081.V2080_OUT = V2100_OUT
    prev2098.prev2096.prev2083.prev2081.V2080_INIT = V2100_INIT
    prev2098.prev2096.prev2083.prev2081.V2080_BOOT = V2100_BOOT
    prev2098.prev2096.prev2083.prev2081.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev2098.prev2096.prev2083.prev2081.TEST_EXPECT_VERSION = TEST_EXPECT_VERSION
    prev2098.prev2096.prev2083.prev2081.TEST_LOG_PATH = TEST_LOG_PATH
    prev2098.prev2096.prev2083.prev2081.TEST_SUMMARY_PATH = TEST_SUMMARY_PATH
    prev2098.prev2096.prev2083.prev2081.TEST_HELPER_RESULT_PATH = TEST_HELPER_RESULT_PATH
    prev2098.prev2096.prev2083.prev2081.EXPECTED_HELPER_VERSION = EXPECTED_HELPER_VERSION
    prev2098.prev2096.prev2083.prev2081.artifact_hook_check = artifact_hook_check
    prev2098.prev2096.prev2083.prev2081.collect_details = collect_details
    prev2098.prev2096.prev2083.prev2081.classify = classify
    prev2098.prev2096.prev2083.prev2081.render_report = render_report
    prev2098.prev2096.prev2083.prev2081.configure_prev2059()


def main(argv: list[str] | None = None) -> int:
    configure_prev2081()
    return prev2098.prev2096.prev2083.prev2081.prev2059.main(argv)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

#!/usr/bin/env python3
"""V2113 rollbackable handoff for dual-RFS plus persist-RFS leaf precreate."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import native_wifi_tftp_persist_rfs_leaf_precreate_handoff_v2109 as prev2109


CYCLE = "V2113"
REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v2113-dual-rfs-leaf-precreate-handoff"
HANDOFF_DIR = OUT_DIR / "v2112-handoff"
HANDOFF_REPORT = OUT_DIR / "v2112-handoff-report.md"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V2113_DUAL_RFS_LEAF_PRECREATE_HANDOFF_2026-06-05.md"
)
V2112_OUT = REPO_ROOT / "tmp" / "wifi" / "v2112-dual-rfs-leaf-precreate-test-boot"
V2112_INIT = V2112_OUT / "init_v2112_dual_rfs_leaf_precreate"
V2112_BOOT = V2112_OUT / "boot_linux_v2112_dual_rfs_leaf_precreate.img"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v2112/dev/__properties__"
TEST_EXPECT_VERSION = "A90 Linux init 0.9.231 (v2112-dual-rfs-leaf-precreate)"
TEST_LOG_PATH = "/cache/native-init-wifi-test-boot-v2112.log"
TEST_SUMMARY_PATH = "/cache/native-init-wifi-test-boot-v2112.summary"
TEST_HELPER_RESULT_PATH = "/cache/native-init-wifi-test-boot-v2112-helper.result"
EXPECTED_HELPER_VERSION = "a90_android_execns_probe v415"

ORIGINAL_COLLECT_DETAILS = prev2109.collect_details
ORIGINAL_CLASSIFY = prev2109.classify


def rel(path: Path) -> str:
    return prev2109.rel(path)


def intish(value: object) -> int:
    return prev2109.intish(value)


def markdown_table(headers: list[str], rows: list[list[object]]) -> str:
    return prev2109.markdown_table(headers, rows)


def artifact_hook_check() -> dict[str, Any]:
    init_required = (
        "native-init-sibling-fwssctl-v641",
        "A90v641: sibling fwssctl proof armed",
        "wifi-v641-fwssctl",
        "A90v2112",
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
        "wifi_companion_start.tftp_persist_rfs_leaf_precreate.enabled=%d",
        "wifi_companion_start.tftp_persist_rfs_leaf_precreate.paths=/mnt/vendor/persist/rfs/mdm/mpss,/mnt/vendor/persist/rfs/apq/gnss",
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
    )
    checks: dict[str, Any] = {}
    for path, required in ((V2112_INIT, init_required), (V2112_BOOT, boot_required)):
        key = rel(path)
        forbidden_tokens = init_forbidden if path == V2112_INIT else boot_forbidden
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
    details = ORIGINAL_COLLECT_DETAILS(handoff)
    trace = details.get("wlanmdsp_trace") if isinstance(details.get("wlanmdsp_trace"), dict) else {}
    bridge = trace.get("rfs_bridge") if isinstance(trace.get("rfs_bridge"), dict) else {}
    details["dual_rfs_bridge"] = {
        "android_parity": bridge.get("android_parity", ""),
        "probe_exists": intish(bridge.get("probe_exists")),
        "probe_nonzero": intish(bridge.get("probe_nonzero")),
        "probe_open_rc": str(bridge.get("probe_open_rc", "")),
        "fallback_exists": intish(bridge.get("fallback_exists")),
        "fallback_nonzero": intish(bridge.get("fallback_nonzero")),
        "fallback_open_rc": str(bridge.get("fallback_open_rc", "")),
        "rootfs_namespace_only": intish(bridge.get("rootfs_namespace_only")),
        "sda29_write": intish(bridge.get("sda29_write")),
    }
    return details


def dual_rfs_ok(details: dict[str, Any]) -> bool:
    bridge = details.get("dual_rfs_bridge") if isinstance(details.get("dual_rfs_bridge"), dict) else {}
    return (
        bridge.get("android_parity") == "firmware_mnt_probe_present_firmware_fallback_present"
        and intish(bridge.get("probe_exists")) == 1
        and intish(bridge.get("probe_nonzero")) == 1
        and str(bridge.get("probe_open_rc")) == "0"
        and intish(bridge.get("fallback_exists")) == 1
        and intish(bridge.get("fallback_nonzero")) == 1
        and str(bridge.get("fallback_open_rc")) == "0"
        and intish(bridge.get("rootfs_namespace_only")) == 1
        and intish(bridge.get("sda29_write")) == 0
    )


def classify(handoff: dict[str, Any],
             hook: dict[str, Any],
             steps: list[dict[str, Any]],
             details: dict[str, Any]) -> dict[str, Any]:
    base = ORIGINAL_CLASSIFY(handoff, hook, steps, details)
    bridge_ok = dual_rfs_ok(details)
    cascade = details.get("cascade") if isinstance(details.get("cascade"), dict) else {}
    branch = details.get("tftp_tombstone_branch") if isinstance(details.get("tftp_tombstone_branch"), dict) else {}
    fw_ready = intish(cascade.get("fw_ready")) > 0
    wlan0 = intish(cascade.get("wlan0")) > 0
    wlanmdsp_seen = bool(base.get("wlanmdsp_seen"))
    ota_seen = bool(base.get("ota_seen"))
    server_payload = str(branch.get("server_check", {}).get("payload", ""))

    if not base.get("hook_ok"):
        label = "dual-rfs-leaf-precreate-artifact-hook-regression"
        passed = False
        reason = "V2112 artifact does not contain the bounded dual-RFS plus leaf-precreate contract"
    elif not bridge_ok:
        label = "dual-rfs-leaf-precreate-bridge-missing"
        passed = False
        reason = "exact Android firmware_mnt WLAN image path or fallback path did not resolve in the private RFS bridge"
    elif wlan0:
        label = "dual-rfs-leaf-precreate-wlan0-progress"
        passed = True
        reason = "native reached wlan0; stop before scan/connect and run the dedicated connectivity gate"
    elif fw_ready:
        label = "dual-rfs-leaf-precreate-fw-ready-progress"
        passed = True
        reason = "native reached FW_READY; chase wlan0 next"
    elif wlanmdsp_seen:
        label = "dual-rfs-leaf-precreate-wlanmdsp-progress"
        passed = True
        reason = "dual-RFS plus persist-RFS leaf precreate produced a visible wlanmdsp TFTP request"
    elif ota_seen:
        label = "dual-rfs-leaf-precreate-ota-progress-no-wlanmdsp"
        passed = True
        reason = "dual-RFS plus persist-RFS leaf precreate reached ota_firewall but not wlanmdsp"
    elif server_payload == "hello":
        label = "dual-rfs-leaf-precreate-post-up-server-check-no-wlanmdsp"
        passed = True
        reason = "both WLAN image RFS paths resolve and persist-RFS mkdir failures are clear, but native still only shows late post-UP server_check and no ota/wlanmdsp"
    else:
        label = "dual-rfs-leaf-precreate-no-android-order-branch"
        passed = True
        reason = "both WLAN image RFS paths resolve, but Android-order tftp bootstrap still did not appear"

    return {
        **base,
        "decision": f"v2113-{label}-rollback-{'pass' if passed else 'blocked'}",
        "label": label,
        "pass": passed,
        "reason": reason,
        "dual_rfs_bridge_ok": bridge_ok,
    }


def render_report(manifest: dict[str, Any]) -> str:
    details = manifest["details"]
    classification = manifest["classification"]
    ns = details.get("tftp_process_namespace_audit", {}) if isinstance(details.get("tftp_process_namespace_audit"), dict) else {}
    paths = ns.get("paths", {}) if isinstance(ns.get("paths"), dict) else {}
    cascade = details.get("cascade", {}) if isinstance(details.get("cascade"), dict) else {}
    marker = details.get("leaf_precreate_marker", {}) if isinstance(details.get("leaf_precreate_marker"), dict) else {}
    bridge = details.get("dual_rfs_bridge", {}) if isinstance(details.get("dual_rfs_bridge"), dict) else {}
    step_lines = [
        f"- `{step['name']}` rc `{step['rc']}` ok `{step['ok']}` evidence `{step['file']}`"
        for step in manifest["steps"]
    ]
    return "\n".join([
        "# Native Init V2113 Dual-RFS Leaf Precreate Handoff",
        "",
        "## Summary",
        "",
        "- Cycle: `V2113`",
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
                ["leaf_precreate", classification.get("persist_rfs_leaves_visible_for_tftp"), f"marker={marker}"],
                ["namespace_audit", classification.get("namespace_audit_ok"), f"pid={classification.get('tftp_pid')} root={ns.get('root_target')}"],
                ["persist_targets_visible", classification.get("all_persist_targets_visible"), f"mountinfo_matches={classification.get('mountinfo_match_count')}"],
                ["persist_auto_dir", classification.get("persist_auto_dir_error_count"), f"mkdir_failed={classification.get('persist_mkdir_failed_count')}"],
                ["server_check", classification.get("server_check_payload"), f"after_wlan_pd_ms={classification.get('server_after_wlan_pd_ms')}"],
                ["cascade", "", f"wlan_pd={cascade.get('wlan_pd_up')} icnss_qmi={cascade.get('icnss_qmi_connected')} fw_ready={cascade.get('fw_ready')} wlan0={cascade.get('wlan0')}"],
            ],
        ),
        "",
        "## Process-Root Paths",
        "",
        markdown_table(
            ["path", "exists", "dir", "mode", "uid", "gid", "errno"],
            [
                [name, item.get("exists"), item.get("is_dir"), item.get("mode"), item.get("uid"), item.get("gid"), item.get("errno")]
                for name, item in paths.items()
                if isinstance(item, dict)
            ],
        ),
        "",
        "## Interpretation",
        "",
        "- V2113 integrates the V2109 persist-RFS leaf fix with the exact Android dual-RFS WLAN image path that earlier passive V2109 did not expose.",
        "- A `wlanmdsp`/FW-ready/`wlan0` label is progress toward the final native Wi-Fi goal; a post-UP-only `server_check` label keeps the blocker before Android-order WLAN-PD firmware fetch selection.",
        "- This run remains light/passive: no `tftp_server` ptrace, no boot-time QRTR matrix, no AP QMI send, and no Wi-Fi HAL/scan/connect.",
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
        "- Mutation scope: `/cache` one-shot clean-DSP flag, V2112 test-boot flash-handoff, namespace-local RFS bridges/tmpfs mirrors, namespace-local persist-RFS leaf precreate in the private rootfs, read-only tftp process-root audit, and rollback to `stage3/boot_linux_v724.img` with selftest fail=0.",
        "",
    ])


def configure_prev2109() -> None:
    prev2109.CYCLE = CYCLE
    prev2109.OUT_DIR = OUT_DIR
    prev2109.HANDOFF_DIR = HANDOFF_DIR
    prev2109.HANDOFF_REPORT = HANDOFF_REPORT
    prev2109.REPORT_PATH = REPORT_PATH
    prev2109.V2108_OUT = V2112_OUT
    prev2109.V2108_INIT = V2112_INIT
    prev2109.V2108_BOOT = V2112_BOOT
    prev2109.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev2109.TEST_EXPECT_VERSION = TEST_EXPECT_VERSION
    prev2109.TEST_LOG_PATH = TEST_LOG_PATH
    prev2109.TEST_SUMMARY_PATH = TEST_SUMMARY_PATH
    prev2109.TEST_HELPER_RESULT_PATH = TEST_HELPER_RESULT_PATH
    prev2109.EXPECTED_HELPER_VERSION = EXPECTED_HELPER_VERSION
    prev2109.BRIDGE_CAPTURE = OUT_DIR / "host" / "v2113-autostart-bridge.log"
    prev2109.BRIDGE_STDOUT = OUT_DIR / "host" / "v2113-autostart-bridge.stdout.txt"
    prev2109.BRIDGE_STDERR = OUT_DIR / "host" / "v2113-autostart-bridge.stderr.txt"
    prev2109.BRIDGE_PID = OUT_DIR / "host" / "v2113-autostart-bridge.pid"
    prev2109.artifact_hook_check = artifact_hook_check
    prev2109.collect_details = collect_details
    prev2109.classify = classify
    prev2109.render_report = render_report


def main(argv: list[str] | None = None) -> int:
    configure_prev2109()
    return prev2109.main(argv)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

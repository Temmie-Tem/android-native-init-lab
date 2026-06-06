#!/usr/bin/env python3
"""V2098 rollbackable handoff for TFTP tombstone-RFS vendor_rfs permission parity."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import native_wifi_tftp_tombstone_parity_handoff_v2096 as prev2096


CYCLE = "V2098"
REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v2098-tftp-tombstone-rfs-vendor-perms-handoff"
HANDOFF_DIR = OUT_DIR / "v2097-handoff"
HANDOFF_REPORT = OUT_DIR / "v2097-handoff-report.md"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V2098_TFTP_TOMBSTONE_RFS_VENDOR_PERMS_HANDOFF_2026-06-05.md"
)
V2097_OUT = REPO_ROOT / "tmp" / "wifi" / "v2097-tftp-tombstone-rfs-vendor-perms-test-boot"
V2097_INIT = V2097_OUT / "init_v2097_tftp_tombstone_rfs_vendor_perms"
V2097_BOOT = V2097_OUT / "boot_linux_v2097_tftp_tombstone_rfs_vendor_perms.img"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v2097/dev/__properties__"
TEST_EXPECT_VERSION = "A90 Linux init 0.9.226 (v2097-tftp-tombstone-rfs-vendor-perms)"
TEST_LOG_PATH = "/cache/native-init-wifi-test-boot-v2097.log"
TEST_SUMMARY_PATH = "/cache/native-init-wifi-test-boot-v2097.summary"
TEST_HELPER_RESULT_PATH = "/cache/native-init-wifi-test-boot-v2097-helper.result"
EXPECTED_HELPER_VERSION = "a90_android_execns_probe v410"
VENDOR_RFS = 2903

BASE_COLLECT_DETAILS = prev2096.BASE_COLLECT_DETAILS
BASE_CLASSIFY = prev2096.BASE_CLASSIFY


def rel(path: Path) -> str:
    return prev2096.rel(path)


def intish(value: object) -> int:
    return prev2096.intish(value)


def markdown_table(headers: list[str], rows: list[list[object]]) -> str:
    return prev2096.markdown_table(headers, rows)


def count_lines(text: str, needle: str, path_fragment: str) -> int:
    return prev2096.count_lines(text, needle, path_fragment)


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
        "A90v2097",
        "wifi-companion-wlan-pd-post-pm-lower-state-observer-start-only",
        "--timeout-sec",
        "75",
    )
    boot_required = (
        EXPECTED_HELPER_VERSION,
        "wifi_companion_start.tftp_tombstone_rfs_tmpfs.enabled=%d",
        "wifi_companion_start.tftp_tombstone_rfs_tmpfs.vendor_rfs_perms=%d",
        "wifi_companion_start.tftp_tombstone_rfs_tmpfs.rootfs_namespace_only=1",
        "wifi_companion_start.tftp_tombstone_rfs_tmpfs.ota_ruleset_created=0",
        "/data/vendor/tombstones/rfs/modem",
        "/data/vendor/tombstones/rfs/lpass",
        "/data/vendor/tombstones/rfs/tn",
        "tftp_readwrite_transition.mode=read-only-stat-open-on-change",
        "tftp_ready_before_wlfw_vote.mode=alive-socket-plus-android-order-settle",
        "tftp_logdw_sink.order_timestamps=1",
        "per_mgr_vote_focused.begin=1",
        "wlfw_late_msg21_focused.begin=1",
        "icnss_qcacld_post_bdf_focused",
    )
    checks: dict[str, Any] = {}
    for path, required in ((V2097_INIT, init_required), (V2097_BOOT, boot_required)):
        key = rel(path)
        forbidden_tokens = init_forbidden if path == V2097_INIT else boot_forbidden
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


def collect_tombstone(fields: dict[str, str], text: str) -> dict[str, Any]:
    paths = {name: prev2096.get_path_snapshot(fields, name) for name in ("tombstones", "rfs", "modem", "lpass", "tn")}
    vendor_perms = intish(fields.get("wifi_companion_start.tftp_tombstone_rfs_tmpfs.pre.vendor_rfs_perms")) == 1
    tombstone_auto_dir = count_lines(text, "Failed to auto_dir", "/data/vendor/tombstones")
    tombstone_mkdir = count_lines(text, "mkdir failed", "/data/vendor/tombstones")
    persist_auto_dir = count_lines(text, "Failed to auto_dir", "/mnt/vendor/persist/rfs")
    persist_mkdir = count_lines(text, "mkdir failed", "/mnt/vendor/persist/rfs")
    safe = (
        intish(fields.get("wifi_companion_start.tftp_tombstone_rfs_tmpfs.enabled")) == 1
        and intish(fields.get("wifi_companion_start.tftp_tombstone_rfs_tmpfs.vendor_rfs_perms")) == 1
        and intish(fields.get("wifi_companion_start.tftp_tombstone_rfs_tmpfs.pre.enabled")) == 1
        and vendor_perms
        and intish(fields.get("wifi_companion_start.tftp_tombstone_rfs_tmpfs.pre.rootfs_namespace_only")) == 1
        and intish(fields.get("wifi_companion_start.tftp_tombstone_rfs_tmpfs.pre.sda29_write")) == 0
        and intish(fields.get("wifi_companion_start.tftp_tombstone_rfs_tmpfs.pre.ota_ruleset_created")) == 0
        and all(path["exists"] == 1 and path["is_dir"] == 1 for path in paths.values())
        and all(path["uid"] == VENDOR_RFS and path["gid"] == VENDOR_RFS for path in paths.values())
    )
    return {
        "enabled": intish(fields.get("wifi_companion_start.tftp_tombstone_rfs_tmpfs.enabled")),
        "pre_enabled": intish(fields.get("wifi_companion_start.tftp_tombstone_rfs_tmpfs.pre.enabled")),
        "vendor_rfs_perms": 1 if vendor_perms else 0,
        "rootfs_namespace_only": intish(fields.get("wifi_companion_start.tftp_tombstone_rfs_tmpfs.pre.rootfs_namespace_only")),
        "sda29_write": intish(fields.get("wifi_companion_start.tftp_tombstone_rfs_tmpfs.pre.sda29_write")),
        "ota_ruleset_created": intish(fields.get("wifi_companion_start.tftp_tombstone_rfs_tmpfs.pre.ota_ruleset_created")),
        "paths": paths,
        "safe": safe,
        "auto_dir_error_count": tombstone_auto_dir,
        "mkdir_failed_count": tombstone_mkdir,
        "total_auto_dir_error_count": text.count("Failed to auto_dir"),
        "total_mkdir_failed_count": text.count("mkdir failed"),
        "persist_auto_dir_error_count": persist_auto_dir,
        "persist_mkdir_failed_count": persist_mkdir,
        "tombstone_token_count": text.count("/data/vendor/tombstones"),
    }


def collect_details(handoff: dict[str, Any]) -> dict[str, Any]:
    details = BASE_COLLECT_DETAILS(handoff)
    fields = prev2096.prev2083.prev2081.prev2059.prev2057.parse_fields()
    text = prev2096.prev2083.prev2081.prev2059.prev2057.helper_text()
    details["tftp_tombstone_rfs_tmpfs"] = collect_tombstone(fields, text)
    details["tftp_tombstone_branch"] = prev2096.collect_tftp_branch(fields, details)
    return details


def classify(handoff: dict[str, Any],
             hook: dict[str, Any],
             steps: list[dict[str, Any]],
             details: dict[str, Any]) -> dict[str, Any]:
    base = prev2096.classify(handoff, hook, steps, details)
    label = str(base.get("label", "tombstone-parity-review"))
    passed = bool(base.get("pass"))
    return {
        **base,
        "decision": f"v2098-{label}-rollback-{'pass' if passed else 'blocked'}",
        "vendor_rfs_perms": intish(details.get("tftp_tombstone_rfs_tmpfs", {}).get("vendor_rfs_perms")),
    }


def render_report(manifest: dict[str, Any]) -> str:
    details = manifest["details"]
    classification = manifest["classification"]
    tombstone = details.get("tftp_tombstone_rfs_tmpfs", {}) if isinstance(details.get("tftp_tombstone_rfs_tmpfs"), dict) else {}
    branch = details.get("tftp_tombstone_branch", {}) if isinstance(details.get("tftp_tombstone_branch"), dict) else {}
    cascade = details.get("cascade", {}) if isinstance(details.get("cascade"), dict) else {}
    summary = prev2096.prev2083.logdw_summary(details)
    paths = tombstone.get("paths", {}) if isinstance(tombstone.get("paths"), dict) else {}
    step_lines = [
        f"- `{step['name']}` rc `{step['rc']}` ok `{step['ok']}` evidence `{step['file']}`"
        for step in manifest["steps"]
    ]
    return "\n".join([
        "# Native Init V2098 TFTP Tombstone-RFS Vendor-Perms Handoff",
        "",
        "## Summary",
        "",
        "- Cycle: `V2098`",
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
                ["tombstone_bridge", classification.get("tombstone_safe"), f"vendor_rfs_perms={classification.get('vendor_rfs_perms')} auto_dir_cleared={classification.get('auto_dir_cleared')} tombstone_tokens={tombstone.get('tombstone_token_count')}"],
                ["tombstone_auto_dir", tombstone.get("auto_dir_error_count"), f"mkdir_failed={tombstone.get('mkdir_failed_count')} total_auto_dir={tombstone.get('total_auto_dir_error_count')}"],
                ["persist_auto_dir", tombstone.get("persist_auto_dir_error_count"), f"mkdir_failed={tombstone.get('persist_mkdir_failed_count')}"],
                ["server_check", classification.get("server_check_payload"), f"after_wlan_pd_ms={classification.get('server_after_wlan_pd_ms')} logdw={branch.get('logdw_server_check')}"],
                ["ota_firewall", classification.get("ota_seen"), f"logdw={branch.get('logdw_ota_firewall')} file={branch.get('ota', {}).get('index')}"],
                ["wlanmdsp", classification.get("wlanmdsp_seen"), f"logdw={branch.get('logdw_wlanmdsp')} summary={summary.get('wlanmdsp')}/{summary.get('fallback_wlanmdsp')}"],
                ["cascade", "", f"wlan_pd={cascade.get('wlan_pd_up')} icnss_qmi={cascade.get('icnss_qmi_connected')} fw_ready={cascade.get('fw_ready')} wlan0={cascade.get('wlan0')}"],
            ],
        ),
        "",
        "## Tombstone Paths",
        "",
        markdown_table(
            ["path", "exists", "dir", "mode", "uid", "gid", "fs"],
            [
                [name, item.get("exists"), item.get("is_dir"), item.get("mode"), item.get("uid"), item.get("gid"), item.get("fs_type")]
                for name, item in paths.items()
                if isinstance(item, dict)
            ],
        ),
        "",
        "## Interpretation",
        "",
        "- This reruns V2096 after correcting the setup miss: `tftp_server` runs as `vendor_rfs` and the helper now creates `modem`, `lpass`, and `tn` tombstone dirs with `vendor_rfs:vendor_rfs` ownership.",
        "- If tombstone auto-dir clears but the label stays `no-effect-post-up-server-check`, this AP-infra tombstone path is not the WLAN-PD firmware-fetch trigger.",
        "- The remaining primary gate then stays modem-internal: why Android enters pre-spawn `server_check -> ota_firewall -> wlanmdsp`, while native only reaches a late post-UP `server_check` branch.",
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
        "- Mutation scope: `/cache` one-shot clean-DSP flag, V2097 test-boot flash-handoff, namespace-local RFS bridges/tmpfs mirrors including vendor-owned `/data/vendor/tombstones/rfs/{modem,lpass,tn}`, private tmp-root `/dev/socket/logdw`, tracefs uprobes, and rollback to `stage3/boot_linux_v724.img` with selftest fail=0.",
        "",
    ])


def configure_prev2081() -> None:
    prev2096.prev2083.prev2081.CYCLE = CYCLE
    prev2096.prev2083.prev2081.OUT_DIR = OUT_DIR
    prev2096.prev2083.prev2081.HANDOFF_DIR = HANDOFF_DIR
    prev2096.prev2083.prev2081.HANDOFF_REPORT = HANDOFF_REPORT
    prev2096.prev2083.prev2081.REPORT_PATH = REPORT_PATH
    prev2096.prev2083.prev2081.V2080_OUT = V2097_OUT
    prev2096.prev2083.prev2081.V2080_INIT = V2097_INIT
    prev2096.prev2083.prev2081.V2080_BOOT = V2097_BOOT
    prev2096.prev2083.prev2081.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev2096.prev2083.prev2081.TEST_EXPECT_VERSION = TEST_EXPECT_VERSION
    prev2096.prev2083.prev2081.TEST_LOG_PATH = TEST_LOG_PATH
    prev2096.prev2083.prev2081.TEST_SUMMARY_PATH = TEST_SUMMARY_PATH
    prev2096.prev2083.prev2081.TEST_HELPER_RESULT_PATH = TEST_HELPER_RESULT_PATH
    prev2096.prev2083.prev2081.EXPECTED_HELPER_VERSION = EXPECTED_HELPER_VERSION
    prev2096.prev2083.prev2081.artifact_hook_check = artifact_hook_check
    prev2096.prev2083.prev2081.collect_details = collect_details
    prev2096.prev2083.prev2081.classify = classify
    prev2096.prev2083.prev2081.render_report = render_report
    prev2096.prev2083.prev2081.configure_prev2059()


def main(argv: list[str] | None = None) -> int:
    configure_prev2081()
    return prev2096.prev2083.prev2081.prev2059.main(argv)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

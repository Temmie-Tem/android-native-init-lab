#!/usr/bin/env python3
"""Build V1843 PM-service post-ack branch observer test boot."""

from __future__ import annotations

from pathlib import Path

import build_native_init_wifi_test_boot_v1792 as prev1792


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1843-pm-service-post-ack-branch-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v1843/dev/__properties__"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1843_PM_SERVICE_POST_ACK_BRANCH_SOURCE_BUILD_2026-06-03.md"
)

POST_ACK_LABELS = [
    "pm_service_ack_impl_entry",
    "pm_service_ack_impl_match_dispatch",
    "pm_service_post_ack_action_entry",
    "pm_service_post_ack_client_state_store",
    "pm_service_post_ack_vote_scan_done",
    "pm_service_post_ack_action_branch",
    "pm_service_post_ack_timer_settime_call",
    "pm_service_post_ack_power_state_load",
    "pm_service_post_ack_qmi_restart_ind_call",
    "pm_service_post_ack_power_on_open_call",
    "pm_service_post_ack_power_on_open_ret",
    "pm_service_post_ack_unlock_return",
]


def configure_base() -> None:
    prev1792.configure_base()
    prev1792.OUT_DIR = OUT_DIR
    prev1792.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev1792.REPORT_PATH = REPORT_PATH
    prev1792.prev1790.OUT_DIR = OUT_DIR
    prev1792.prev1790.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev1792.prev1790.REPORT_PATH = REPORT_PATH
    prev1792.prev1790.prev1783.V1783_OUT = OUT_DIR
    prev1792.prev1790.prev1783.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev1792.prev1790.prev1783.DEFAULT_REPORT_PATH = REPORT_PATH
    prev = prev1792.prev1790.prev1783.prev
    prev.OUT_DIR = OUT_DIR
    prev.PROPERTY_RUNTIME_DIR = OUT_DIR / "property-runtime"
    prev.PROPERTY_ROOT = prev.PROPERTY_RUNTIME_DIR / "layout" / "dev" / "__properties__"
    prev.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev.REPORT_PATH = REPORT_PATH
    prev.DEFAULT_ARGS = [
        "--cycle",
        "V1843",
        "--decision",
        "v1843-pm-service-post-ack-branch-source-build-pass",
        "--cycle-label",
        "v1843",
        "--init-version",
        "0.9.164",
        "--init-build",
        "v1843-pm-service-post-ack-branch",
        "--out-dir",
        str(OUT_DIR),
        "--init-binary",
        str(OUT_DIR / "init_v1843_pm_service_post_ack_branch"),
        "--helper-binary",
        str(OUT_DIR / "a90_android_execns_probe_v355"),
        "--ramdisk-cpio",
        str(OUT_DIR / "ramdisk_v1843_pm_service_post_ack_branch.cpio"),
        "--boot-image",
        str(OUT_DIR / "boot_linux_v1843_pm_service_post_ack_branch.img"),
        "--wifi-test-klog-prefix",
        "A90v1843",
        "--wifi-test-disable",
        "/cache/native-init-wifi-test-boot-v1843.disable",
        "--wifi-test-log",
        "/cache/native-init-wifi-test-boot-v1843.log",
        "--wifi-test-summary",
        "/cache/native-init-wifi-test-boot-v1843.summary",
        "--wifi-test-helper-result",
        "/cache/native-init-wifi-test-boot-v1843-helper.result",
        "--wifi-test-pid",
        "/cache/native-init-wifi-test-boot-v1843.pid",
        "--wifi-test-watcher-pid",
        "/cache/native-init-wifi-test-boot-v1843-supervisor.pid",
        "--wifi-test-watch-sec",
        "90",
        "--wifi-test-supervise-helper",
        "--wifi-test-supervisor-timeout-sec",
        "120",
        "--wifi-test-firmware-mounts",
        "--wifi-test-mount-debugfs",
        "--wifi-test-property-root",
        REMOTE_PROPERTY_ROOT,
        "--wifi-test-helper-mode",
        "wlan-pd-post-pm-lower-state-observer",
    ]


def render_report(manifest: dict[str, object]) -> str:
    wifi = manifest["wifi_test"]
    property_runtime = manifest["cnss_nonlog_property_runtime"]
    check_lines = [
        f"- `{item['name']}`: `{item['actual']}` in `{item['context']}`"
        for item in property_runtime["checks"]
    ]
    labels = ", ".join(f"`{label}`" for label in POST_ACK_LABELS)
    return "\n".join([
        "# Native Init V1843 PM-Service Post-Ack Branch Source Build",
        "",
        "## Summary",
        "",
        "- Cycle: `V1843`",
        "- Type: source/build-only rollbackable PM-service post-ack branch observer test boot artifact",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: helper v355 keeps the V1841 current-route callback/ack observer and adds read-only `pm-service` uprobe hit counts for the `0x63f4` ack implementation body and its post-ack action path toward the devnode open branch.",
        "- Manifest: `tmp/wifi/v1843-pm-service-post-ack-branch-test-boot/manifest.json`",
        f"- Boot image: `{manifest['boot_image']}`",
        f"- Boot SHA256: `{manifest['boot_sha256']}`",
        f"- Init: `A90 Linux init {manifest['init_version']} ({manifest['init_build']})`",
        f"- Helper marker: `{manifest['helper_marker']}`",
        f"- Helper SHA256: `{manifest['helper_sha256']}`",
        "",
        "## Route",
        "",
        f"- Helper runtime mode: `{wifi['helper_runtime_mode']}`",
        f"- Property root: `{REMOTE_PROPERTY_ROOT}`",
        "- Base route remains the bounded WLAN-PD post-PM lower observer from V1841, including callback/ack hit counters, PMIC/GDSC focus samples, and inherited bounded QRTR/QMI probes.",
        f"- Added PM-service post-ack labels: {labels}.",
        "- Offsets are read-only tracefs uprobes on the already selected `/vendor/bin/pm-service` target: ack implementation entry/match dispatch, post-ack action entry, client state store, vote scan, action branch, timer/state checks, QMI restart indication branch, devnode open call/return, and unlock/return.",
        "- Explicit limitation: V1843 is a build artifact only; a later rollbackable handoff must confirm which labels actually fire in the current route.",
        "- Still excluded: direct `/dev/subsys_esoc0` open, fake-ONLINE, eSoC notify/BOOT_DONE, PCI rescan/bind, platform unbind, PMIC/GPIO/GDSC writes, `boot_wlan`, restart-PD request, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping.",
        "",
        "## Expected Live Discriminator",
        "",
        "- `post-ack-open-branch-reached`: `pm_service_post_ack_power_on_open_call` or `_ret` fires; stop and inspect lower state before any Wi-Fi action.",
        "- `post-ack-action-no-open`: ack implementation and post-ack action labels fire, but the devnode open branch stays zero and lower state remains static.",
        "- `post-ack-impl-no-action`: ack implementation entry/match fires, but `pm_service_post_ack_action_entry` stays zero.",
        "- `post-ack-contract-missing`: expected PM-service post-ack labels fail to register or enable.",
        "- `powerup-or-wlfw-progress`: powerup thread, inferred eSoC open, mdm-status IRQ, MHI, WLFW service 69, service74/WLAN-PD UP, or `wlan0` appears; stop before Wi-Fi HAL/scan/connect.",
        "- `safety-regression`: any forbidden side effect appears; stop and roll back.",
        "",
        "## Property Runtime",
        "",
        *check_lines,
        "",
        "## Safety Scope",
        "",
        "This build script performed host-side source/build work only. It did not issue live device commands, flash, reboot, scan/connect, use credentials, configure DHCP/routes, perform external ping, open `/dev/subsys_esoc0`, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE` spoof, run PCI rescan/platform bind-unbind, or write firmware/boot/device partitions.",
        "",
    ])


def main() -> int:
    configure_base()
    base = prev1792.prev1790.prev1783.prev
    base.render_report = render_report
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())

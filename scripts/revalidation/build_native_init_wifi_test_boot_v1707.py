#!/usr/bin/env python3
"""Build V1707 WLAN-PD cnss-daemon wlfw_start branch uprobe test boot."""

from __future__ import annotations

from pathlib import Path

import build_native_init_wifi_test_boot_v1699 as base


REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1707-cnss-wlfw-start-branch-uprobe-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v1707/dev/__properties__"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1707_CNSS_WLFW_START_BRANCH_UPROBE_SOURCE_BUILD_2026-06-02.md"
)

ORIGINAL_BUILD_CNSS_PROPERTY_RUNTIME = base.build_cnss_property_runtime


def configure_base() -> None:
    base.configure_base()
    base.base.OUT_DIR = OUT_DIR
    base.base.PROPERTY_RUNTIME_DIR = OUT_DIR / "property-runtime"
    base.base.PROPERTY_ROOT = base.base.PROPERTY_RUNTIME_DIR / "layout" / "dev" / "__properties__"
    base.base.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    base.base.REPORT_PATH = REPORT_PATH
    base.OUT_DIR = OUT_DIR
    base.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    base.REPORT_PATH = REPORT_PATH
    base.base.DEFAULT_ARGS = [
        "--cycle",
        "V1707",
        "--decision",
        "v1707-cnss-wlfw-start-branch-uprobe-source-build-pass",
        "--cycle-label",
        "v1707",
        "--init-version",
        "0.9.130",
        "--init-build",
        "v1707-cnss-wlfw-start-branch-uprobe",
        "--out-dir",
        str(OUT_DIR),
        "--init-binary",
        str(OUT_DIR / "init_v1707_cnss_wlfw_start_branch_uprobe"),
        "--helper-binary",
        str(OUT_DIR / "a90_android_execns_probe_v316"),
        "--ramdisk-cpio",
        str(OUT_DIR / "ramdisk_v1707_cnss_wlfw_start_branch_uprobe.cpio"),
        "--boot-image",
        str(OUT_DIR / "boot_linux_v1707_cnss_wlfw_start_branch_uprobe.img"),
        "--wifi-test-klog-prefix",
        "A90v1707",
        "--wifi-test-disable",
        "/cache/native-init-wifi-test-boot-v1707.disable",
        "--wifi-test-log",
        "/cache/native-init-wifi-test-boot-v1707.log",
        "--wifi-test-summary",
        "/cache/native-init-wifi-test-boot-v1707.summary",
        "--wifi-test-helper-result",
        "/cache/native-init-wifi-test-boot-v1707-helper.result",
        "--wifi-test-pid",
        "/cache/native-init-wifi-test-boot-v1707.pid",
        "--wifi-test-watcher-pid",
        "/cache/native-init-wifi-test-boot-v1707-supervisor.pid",
        "--wifi-test-watch-sec",
        "55",
        "--wifi-test-supervise-helper",
        "--wifi-test-supervisor-timeout-sec",
        "80",
        "--wifi-test-firmware-mounts",
        "--wifi-test-mount-debugfs",
        "--wifi-test-property-root",
        REMOTE_PROPERTY_ROOT,
        "--wifi-test-helper-mode",
        "wlan-pd-cnss-output-visibility",
    ]


def render_report(manifest: dict[str, object]) -> str:
    return "\n".join([
        "# Native Init V1707 CNSS WLFW Start Branch Uprobe Source Build",
        "",
        "## Summary",
        "",
        "- Cycle: `V1707`",
        "- Type: source/build-only rollbackable CNSS WLFW start-branch uprobe test boot artifact",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: extends the V1705 non-log proof from `wlfw_start` to bounded in-function branch tracepoints around DMS init and pthread_create",
        "- Manifest: `tmp/wifi/v1707-cnss-wlfw-start-branch-uprobe-test-boot/manifest.json`",
        f"- Boot image: `{manifest['boot_image']}`",
        f"- Boot SHA256: `{manifest['boot_sha256']}`",
        f"- Init: `A90 Linux init {manifest['init_version']} ({manifest['init_build']})`",
        f"- Helper marker: `{manifest['helper_marker']}`",
        f"- Helper SHA256: `{manifest['helper_sha256']}`",
        "",
        "## Route",
        "",
        "- Helper runtime mode: `wifi-companion-wlan-pd-cnss-output-visibility-start-only`",
        f"- Property root: `{REMOTE_PROPERTY_ROOT}`",
        "- Actors: `qrtr-ns`, `pd-mapper`, `rmt_storage`, `tftp_server`, `/dev/subsys_modem` holder, `cnss_diag`, stock `cnss-daemon`.",
        "- No service-manager, PM trio, `boot_wlan`, `/dev/subsys_esoc0`, forced RC1, fake-ONLINE, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping.",
        "",
        "## Trace Targets",
        "",
        "- `cnss-daemon+0xec00`: `wlfw_start` continuity target from V1705.",
        "- `cnss-daemon+0xecd4`: DMS initialization call.",
        "- `cnss-daemon+0xecd8`: DMS initialization return-code branch.",
        "- `cnss-daemon+0xecf0`: WLFW worker `pthread_create` call.",
        "- `cnss-daemon+0xecf8`: WLFW worker `pthread_create` failure path.",
        "- `cnss-daemon+0xeda0`: WLFW worker `pthread_create` success path.",
        "",
        "## Live Labels",
        "",
        "- `wlfw-start-dms-init-blocked-before-worker`",
        "- `wlfw-start-dms-init-failed-before-worker`",
        "- `wlfw-start-pthread-create-not-reached`",
        "- `wlfw-start-pthread-create-failed`",
        "- `wlfw-start-pthread-create-call-no-return`",
        "- `wlfw-start-pthread-create-success-worker-missing`",
        "- `wlfw-start-worker-entry-reached`",
        "- `wlfw-worker-thread-started-waiting-for-qmi-service`",
        "- `wlfw-worker-thread-started-qmi-ind-register-sent`",
        "- `wlfw-worker-thread-started-qmi-cap-sent`",
        "- `cnss-target-unavailable`",
        "",
        "## Safety Scope",
        "",
        "This build script performed host-side source/build work only. It did not issue live device commands, flash, reboot, scan/connect, use credentials, configure DHCP/routes, perform external ping, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE` spoof, run PCI rescan/platform bind-unbind, or write firmware/boot/device partitions.",
        "",
    ])


def build_cnss_property_runtime() -> dict[str, object]:
    manifest = ORIGINAL_BUILD_CNSS_PROPERTY_RUNTIME()
    pass_ok = bool(manifest.get("pass"))
    manifest["decision"] = (
        "v1707-cnss-wlfw-start-branch-property-runtime-ready"
        if pass_ok
        else "v1707-cnss-wlfw-start-branch-property-runtime-blocked"
    )
    return manifest


def main() -> int:
    configure_base()
    base.build_cnss_property_runtime = build_cnss_property_runtime
    base.render_report = render_report
    base.base.build_cnss_property_runtime = build_cnss_property_runtime
    base.base.render_report = render_report
    return base.base.main()


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Build V1709 WLAN-PD cnss-daemon pre-DMS microtrace test boot."""

from __future__ import annotations

from pathlib import Path

import build_native_init_wifi_test_boot_v1707 as prev


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1709-cnss-wlfw-pre-dms-microtrace-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v1709/dev/__properties__"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1709_CNSS_WLFW_PRE_DMS_MICROTRACE_SOURCE_BUILD_2026-06-02.md"
)


def configure_base() -> None:
    prev.configure_base()
    prev.base.base.OUT_DIR = OUT_DIR
    prev.base.base.PROPERTY_RUNTIME_DIR = OUT_DIR / "property-runtime"
    prev.base.base.PROPERTY_ROOT = prev.base.base.PROPERTY_RUNTIME_DIR / "layout" / "dev" / "__properties__"
    prev.base.base.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev.base.base.REPORT_PATH = REPORT_PATH
    prev.base.OUT_DIR = OUT_DIR
    prev.base.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev.base.REPORT_PATH = REPORT_PATH
    prev.OUT_DIR = OUT_DIR
    prev.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev.REPORT_PATH = REPORT_PATH
    prev.base.base.DEFAULT_ARGS = [
        "--cycle",
        "V1709",
        "--decision",
        "v1709-cnss-wlfw-pre-dms-microtrace-source-build-pass",
        "--cycle-label",
        "v1709",
        "--init-version",
        "0.9.131",
        "--init-build",
        "v1709-cnss-wlfw-pre-dms-microtrace",
        "--out-dir",
        str(OUT_DIR),
        "--init-binary",
        str(OUT_DIR / "init_v1709_cnss_wlfw_pre_dms_microtrace"),
        "--helper-binary",
        str(OUT_DIR / "a90_android_execns_probe_v317"),
        "--ramdisk-cpio",
        str(OUT_DIR / "ramdisk_v1709_cnss_wlfw_pre_dms_microtrace.cpio"),
        "--boot-image",
        str(OUT_DIR / "boot_linux_v1709_cnss_wlfw_pre_dms_microtrace.img"),
        "--wifi-test-klog-prefix",
        "A90v1709",
        "--wifi-test-disable",
        "/cache/native-init-wifi-test-boot-v1709.disable",
        "--wifi-test-log",
        "/cache/native-init-wifi-test-boot-v1709.log",
        "--wifi-test-summary",
        "/cache/native-init-wifi-test-boot-v1709.summary",
        "--wifi-test-helper-result",
        "/cache/native-init-wifi-test-boot-v1709-helper.result",
        "--wifi-test-pid",
        "/cache/native-init-wifi-test-boot-v1709.pid",
        "--wifi-test-watcher-pid",
        "/cache/native-init-wifi-test-boot-v1709-supervisor.pid",
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
        "# Native Init V1709 CNSS WLFW Pre-DMS Microtrace Source Build",
        "",
        "## Summary",
        "",
        "- Cycle: `V1709`",
        "- Type: source/build-only rollbackable CNSS `wlfw_start` pre-DMS microtrace test boot artifact",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: extends V1708 from entry-only `wlfw_start` proof to call/retcheck tracepoints for the four pre-DMS pthread init calls",
        "- Manifest: `tmp/wifi/v1709-cnss-wlfw-pre-dms-microtrace-test-boot/manifest.json`",
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
        "## New Trace Targets",
        "",
        "- `cnss-daemon+0xec58` / `0xec5c`: first `pthread_mutex_init` call and return check.",
        "- `cnss-daemon+0xec78` / `0xec7c`: second `pthread_mutex_init` call and return check.",
        "- `cnss-daemon+0xec9c` / `0xeca0`: first `pthread_cond_init` call and return check.",
        "- `cnss-daemon+0xecbc` / `0xecc0`: second `pthread_cond_init` call and return check.",
        "- Existing V1708 targets remain armed: `wlfw_start`, failure branches, DMS init, pthread_create, worker/QMI targets.",
        "",
        "## Live Labels",
        "",
        "- `wlfw-start-cal-mutex-call-no-return`",
        "- `wlfw-start-cal-mutex-retcheck-no-mutex`",
        "- `wlfw-start-mutex-call-no-return`",
        "- `wlfw-start-mutex-retcheck-no-cond`",
        "- `wlfw-start-cond-call-no-return`",
        "- `wlfw-start-cond-retcheck-no-cond-rsp`",
        "- `wlfw-start-cond-rsp-call-no-return`",
        "- `wlfw-start-cond-rsp-retcheck-no-dms`",
        "- Existing downstream labels from V1708 remain valid.",
        "",
        "## Safety Scope",
        "",
        "This build script performed host-side source/build work only. It did not issue live device commands, flash, reboot, scan/connect, use credentials, configure DHCP/routes, perform external ping, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE` spoof, run PCI rescan/platform bind-unbind, or write firmware/boot/device partitions.",
        "",
    ])


def build_cnss_property_runtime() -> dict[str, object]:
    manifest = prev.ORIGINAL_BUILD_CNSS_PROPERTY_RUNTIME()
    pass_ok = bool(manifest.get("pass"))
    manifest["decision"] = (
        "v1709-cnss-wlfw-pre-dms-property-runtime-ready"
        if pass_ok
        else "v1709-cnss-wlfw-pre-dms-property-runtime-blocked"
    )
    return manifest


def main() -> int:
    configure_base()
    prev.base.build_cnss_property_runtime = build_cnss_property_runtime
    prev.base.render_report = render_report
    prev.base.base.build_cnss_property_runtime = build_cnss_property_runtime
    prev.base.base.render_report = render_report
    return prev.base.base.main()


if __name__ == "__main__":
    raise SystemExit(main())

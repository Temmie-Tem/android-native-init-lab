#!/usr/bin/env python3
"""Build V1846 PM-service post-ack open-context observer test boot."""

from __future__ import annotations

from pathlib import Path

import build_native_init_wifi_test_boot_v1792 as prev1792


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1846-pm-service-open-context-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v1846/dev/__properties__"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1846_PM_SERVICE_OPEN_CONTEXT_SOURCE_BUILD_2026-06-03.md"
)

OPEN_CONTEXT_LABELS = [
    "pm_service_post_ack_power_state_loaded",
    "pm_service_post_ack_open_context",
    "pm_service_post_ack_open_path_loaded",
    "pm_service_post_ack_open_fd_store",
    "pm_service_post_ack_open_fd_compare",
    "pm_service_post_ack_open_success_counter",
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
        "V1846",
        "--decision",
        "v1846-pm-service-open-context-source-build-pass",
        "--cycle-label",
        "v1846",
        "--init-version",
        "0.9.165",
        "--init-build",
        "v1846-pm-service-open-context",
        "--out-dir",
        str(OUT_DIR),
        "--init-binary",
        str(OUT_DIR / "init_v1846_pm_service_open_context"),
        "--helper-binary",
        str(OUT_DIR / "a90_android_execns_probe_v356"),
        "--ramdisk-cpio",
        str(OUT_DIR / "ramdisk_v1846_pm_service_open_context.cpio"),
        "--boot-image",
        str(OUT_DIR / "boot_linux_v1846_pm_service_open_context.img"),
        "--wifi-test-klog-prefix",
        "A90v1846",
        "--wifi-test-disable",
        "/cache/native-init-wifi-test-boot-v1846.disable",
        "--wifi-test-log",
        "/cache/native-init-wifi-test-boot-v1846.log",
        "--wifi-test-summary",
        "/cache/native-init-wifi-test-boot-v1846.summary",
        "--wifi-test-helper-result",
        "/cache/native-init-wifi-test-boot-v1846-helper.result",
        "--wifi-test-pid",
        "/cache/native-init-wifi-test-boot-v1846.pid",
        "--wifi-test-watcher-pid",
        "/cache/native-init-wifi-test-boot-v1846-supervisor.pid",
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
    labels = ", ".join(f"`{label}`" for label in OPEN_CONTEXT_LABELS)
    return "\n".join([
        "# Native Init V1846 PM-Service Open-Context Source Build",
        "",
        "## Summary",
        "",
        "- Cycle: `V1846`",
        "- Type: source/build-only rollbackable PM-service post-ack open-context observer test boot artifact",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: helper v356 keeps the V1844 post-ack branch observer and adds read-only PM-service context uprobes for corrected power-state load, open-object fields, path load, fd store/compare, and open-success counter.",
        "- Manifest: `tmp/wifi/v1846-pm-service-open-context-test-boot/manifest.json`",
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
        "- Base route remains the bounded WLAN-PD post-PM lower observer from V1844, including callback/ack hit counters, PM-service post-ack branch hit counters, PMIC/GDSC focus samples, and inherited bounded QRTR/QMI probes.",
        f"- Added PM-service open-context labels: {labels}.",
        "- The new context labels are read-only tracefs uprobes around `pm-service` offsets `0x88cc`, `0x8cc8`, `0x8ccc`, `0x8cd8`, `0x8ce0`, and `0x8ce8`.",
        "- Explicit limitation: V1846 is a build artifact only; a later rollbackable handoff must confirm which context labels register and what field values are captured.",
        "- Still excluded: direct `/dev/subsys_esoc0` open, fake-ONLINE, eSoC notify/BOOT_DONE, PCI rescan/bind, platform unbind, PMIC/GPIO/GDSC writes, `boot_wlan`, restart-PD request, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping.",
        "",
        "## Expected Live Discriminator",
        "",
        "- `open-context-modem-success-static`: context labels confirm `/dev/subsys_modem` open success while lower state stays static.",
        "- `open-context-esoc0-or-powerup-progress`: context labels show `/dev/subsys_esoc0`, powerup thread, inferred eSoC open, MHI, WLFW service 69, or `wlan0`; stop before Wi-Fi HAL/scan/connect.",
        "- `open-context-contract-missing`: expected context labels fail to register or enable.",
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

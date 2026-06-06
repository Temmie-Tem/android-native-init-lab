#!/usr/bin/env python3
"""Build V1821 QRTR/servloc registry snapshot observer test boot."""

from __future__ import annotations

from pathlib import Path

import build_native_init_wifi_test_boot_v1792 as prev1792


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1821-qrtr-servloc-registry-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v1821/dev/__properties__"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1821_QRTR_SERVLOC_REGISTRY_SOURCE_BUILD_2026-06-03.md"
)


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
        "V1821",
        "--decision",
        "v1821-qrtr-servloc-registry-source-build-pass",
        "--cycle-label",
        "v1821",
        "--init-version",
        "0.9.157",
        "--init-build",
        "v1821-qrtr-servloc-registry",
        "--out-dir",
        str(OUT_DIR),
        "--init-binary",
        str(OUT_DIR / "init_v1821_qrtr_servloc_registry"),
        "--helper-binary",
        str(OUT_DIR / "a90_android_execns_probe_v348"),
        "--ramdisk-cpio",
        str(OUT_DIR / "ramdisk_v1821_qrtr_servloc_registry.cpio"),
        "--boot-image",
        str(OUT_DIR / "boot_linux_v1821_qrtr_servloc_registry.img"),
        "--wifi-test-klog-prefix",
        "A90v1821",
        "--wifi-test-disable",
        "/cache/native-init-wifi-test-boot-v1821.disable",
        "--wifi-test-log",
        "/cache/native-init-wifi-test-boot-v1821.log",
        "--wifi-test-summary",
        "/cache/native-init-wifi-test-boot-v1821.summary",
        "--wifi-test-helper-result",
        "/cache/native-init-wifi-test-boot-v1821-helper.result",
        "--wifi-test-pid",
        "/cache/native-init-wifi-test-boot-v1821.pid",
        "--wifi-test-watcher-pid",
        "/cache/native-init-wifi-test-boot-v1821-supervisor.pid",
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
    return "\n".join([
        "# Native Init V1821 QRTR/Servloc Registry Source Build",
        "",
        "## Summary",
        "",
        "- Cycle: `V1821`",
        "- Type: source/build-only rollbackable QRTR/service-locator registry snapshot observer test boot artifact",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: helper v348 keeps the bounded lower publication route and adds read-only `/proc/net/qrtr` plus debugfs QRTR/service-locator registry summary fields for wlan/fw and wlan_pd surfaces.",
        "- Manifest: `tmp/wifi/v1821-qrtr-servloc-registry-test-boot/manifest.json`",
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
        "- Base route remains the bounded lower handoff observer: PM-client return fetchargs, lower-state samples, service-notifier listener state, raw service-notifier 180/74 samples, lower precondition klog samples, and publication text samples.",
        "- Added registry summary prefix: `wlan_pd_qrtr_registry.<phase>.*` for `after_holder_start`, `after_early_listener`, and `after_post_listener_window`.",
        "- Added read-only sources: `/proc/net/qrtr`, `/sys/kernel/debug/qrtr/nodes`, `/sys/kernel/debug/qrtr/services`, and `/sys/kernel/debug/msm_ipc_router/dump` when present.",
        "- Added summary fields: open/error/bytes/lines/interesting lines plus text flags for `wlan`, service-locator, `wlan/fw`, `wlan_pd`, service 74, service 180, and qmi.",
        "- Explicit non-actions: `no_qrtr_lookup_send=1`, `no_service_start=1`, `no_esoc0_open=1`, `no_fake_online=1`, and `no_pmic_gpio_gdsc_write=1`.",
        "- Still excluded: direct `/dev/subsys_esoc0` open, fake-ONLINE, eSoC notify/BOOT_DONE, PCI rescan/bind, platform unbind, PMIC/GPIO/GDSC writes, `boot_wlan`, restart-PD request, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping.",
        "",
        "## Expected Live Discriminator",
        "",
        "- V1822 should run one rollbackable live gate with this artifact and classify whether read-only QRTR/servloc registry state exposes wlan/fw or wlan_pd while service74/wlan_pd remain absent.",
        "- `qrtr-registry-wlan-absent`: QRTR registry is readable but no wlan/fw or wlan_pd registry text appears.",
        "- `qrtr-registry-wlan-visible-still-no-service74`: registry text appears for wlan surfaces but service74/wlan_pd still do not publish.",
        "- `lower-publication-progress`: service 74, wlan_pd, WLFW service 69, MHI, or `wlan0` appears; stop before Wi-Fi HAL/scan/connect.",
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

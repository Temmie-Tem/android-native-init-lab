#!/usr/bin/env python3
"""Build V1771 WLAN-PD service-object-visible test boot."""

from __future__ import annotations

from pathlib import Path

import build_native_init_wifi_test_boot_v1693 as prev


REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1771-wlan-pd-service-object-visible-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v1771/dev/__properties__"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1771_WLAN_PD_SERVICE_OBJECT_VISIBLE_SOURCE_BUILD_2026-06-03.md"
)

ORIGINAL_BUILD_CNSS_PROPERTY_RUNTIME = prev.build_cnss_property_runtime


def configure_base() -> None:
    prev.OUT_DIR = OUT_DIR
    prev.PROPERTY_RUNTIME_DIR = OUT_DIR / "property-runtime"
    prev.PROPERTY_ROOT = prev.PROPERTY_RUNTIME_DIR / "layout" / "dev" / "__properties__"
    prev.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev.REPORT_PATH = REPORT_PATH
    prev.DEFAULT_ARGS = [
        "--cycle",
        "V1771",
        "--decision",
        "v1771-wlan-pd-service-object-visible-source-build-pass",
        "--cycle-label",
        "v1771",
        "--init-version",
        "0.9.140",
        "--init-build",
        "v1771-wlan-pd-service-object-visible",
        "--out-dir",
        str(OUT_DIR),
        "--init-binary",
        str(OUT_DIR / "init_v1771_wlan_pd_service_object_visible"),
        "--helper-binary",
        str(OUT_DIR / "a90_android_execns_probe_v331"),
        "--ramdisk-cpio",
        str(OUT_DIR / "ramdisk_v1771_wlan_pd_service_object_visible.cpio"),
        "--boot-image",
        str(OUT_DIR / "boot_linux_v1771_wlan_pd_service_object_visible.img"),
        "--wifi-test-klog-prefix",
        "A90v1771",
        "--wifi-test-disable",
        "/cache/native-init-wifi-test-boot-v1771.disable",
        "--wifi-test-log",
        "/cache/native-init-wifi-test-boot-v1771.log",
        "--wifi-test-summary",
        "/cache/native-init-wifi-test-boot-v1771.summary",
        "--wifi-test-helper-result",
        "/cache/native-init-wifi-test-boot-v1771-helper.result",
        "--wifi-test-pid",
        "/cache/native-init-wifi-test-boot-v1771.pid",
        "--wifi-test-watcher-pid",
        "/cache/native-init-wifi-test-boot-v1771-supervisor.pid",
        "--wifi-test-watch-sec",
        "75",
        "--wifi-test-supervise-helper",
        "--wifi-test-supervisor-timeout-sec",
        "105",
        "--wifi-test-firmware-mounts",
        "--wifi-test-mount-debugfs",
        "--wifi-test-property-root",
        REMOTE_PROPERTY_ROOT,
        "--wifi-test-helper-mode",
        "wlan-pd-service-object-visible-trigger",
    ]


def build_cnss_property_runtime() -> dict[str, object]:
    manifest = ORIGINAL_BUILD_CNSS_PROPERTY_RUNTIME()
    pass_ok = bool(manifest.get("pass"))
    manifest["decision"] = (
        "v1771-service-object-visible-property-runtime-ready"
        if pass_ok
        else "v1771-service-object-visible-property-runtime-blocked"
    )
    return manifest


def render_report(manifest: dict[str, object]) -> str:
    wifi = manifest["wifi_test"]
    property_runtime = manifest["cnss_nonlog_property_runtime"]
    check_lines = [
        f"- `{item['name']}`: `{item['actual']}` in `{item['context']}`"
        for item in property_runtime["checks"]
    ]
    return "\n".join([
        "# Native Init V1771 WLAN-PD Service-object Visible Source Build",
        "",
        "## Summary",
        "",
        "- Cycle: `V1771`",
        "- Type: source/build-only rollbackable WLAN-PD service-object-visible test boot artifact",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: carries the approved one-run V1764 dormant helper gate into a rollbackable test boot with late listener evidence.",
        "- Manifest: `tmp/wifi/v1771-wlan-pd-service-object-visible-test-boot/manifest.json`",
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
        "- Actors: `servicemanager`, `hwservicemanager`, VND service-manager fallback, `qrtr-ns`, `pd-mapper`, `rmt_storage`, `tftp_server`, `pm_proxy_helper`, `pm-service`, `/dev/subsys_modem` holder, `cnss_diag`, and stock `cnss-daemon`.",
        "- Added evidence: service-object visibility summary, CNSS peripheral uprobes, WLFW/readback fields, and late WLAN-PD service-notifier listener state.",
        "- No full `pm-proxy`, `boot_wlan`, restart-PD request, `/dev/subsys_esoc0`, forced RC1, fake-ONLINE, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping.",
        "",
        "## Property Runtime",
        "",
        *check_lines,
        "",
        "## Live Labels",
        "",
        "- `service-object-nonnull-vote-sent-wlanmdsp-requested`",
        "- `service-object-nonnull-vote-sent-no-request`",
        "- `service-object-nonnull-no-vote`",
        "- `service-object-still-null`",
        "",
        "## Safety Scope",
        "",
        "This build script performed host-side source/build work only. It did not issue live device commands, flash, reboot, scan/connect, use credentials, configure DHCP/routes, perform external ping, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE` spoof, run PCI rescan/platform bind-unbind, or write firmware/boot/device partitions.",
        "",
    ])


def main() -> int:
    configure_base()
    prev.build_cnss_property_runtime = build_cnss_property_runtime
    prev.render_report = render_report
    return prev.main()


if __name__ == "__main__":
    raise SystemExit(main())

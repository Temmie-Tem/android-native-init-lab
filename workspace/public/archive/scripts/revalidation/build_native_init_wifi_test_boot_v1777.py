#!/usr/bin/env python3
"""Build V1777 WLAN-PD service-object policy-load test boot."""

from __future__ import annotations

from pathlib import Path

import build_native_init_wifi_test_boot_v1693 as prev


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1777-service-object-policy-load-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v1777/dev/__properties__"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1777_SERVICE_OBJECT_POLICY_LOAD_SOURCE_BUILD_2026-06-03.md"
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
        "V1777",
        "--decision",
        "v1777-service-object-policy-load-source-build-pass",
        "--cycle-label",
        "v1777",
        "--init-version",
        "0.9.142",
        "--init-build",
        "v1777-service-object-policy-load",
        "--out-dir",
        str(OUT_DIR),
        "--init-binary",
        str(OUT_DIR / "init_v1777_service_object_policy_load"),
        "--helper-binary",
        str(OUT_DIR / "a90_android_execns_probe_v333"),
        "--ramdisk-cpio",
        str(OUT_DIR / "ramdisk_v1777_service_object_policy_load.cpio"),
        "--boot-image",
        str(OUT_DIR / "boot_linux_v1777_service_object_policy_load.img"),
        "--wifi-test-klog-prefix",
        "A90v1777",
        "--wifi-test-disable",
        "/cache/native-init-wifi-test-boot-v1777.disable",
        "--wifi-test-log",
        "/cache/native-init-wifi-test-boot-v1777.log",
        "--wifi-test-summary",
        "/cache/native-init-wifi-test-boot-v1777.summary",
        "--wifi-test-helper-result",
        "/cache/native-init-wifi-test-boot-v1777-helper.result",
        "--wifi-test-pid",
        "/cache/native-init-wifi-test-boot-v1777.pid",
        "--wifi-test-watcher-pid",
        "/cache/native-init-wifi-test-boot-v1777-supervisor.pid",
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
        "v1777-service-object-property-runtime-ready"
        if pass_ok
        else "v1777-service-object-property-runtime-blocked"
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
        "# Native Init V1777 Service-object Policy-load Source Build",
        "",
        "## Summary",
        "",
        "- Cycle: `V1777`",
        "- Type: source/build-only rollbackable WLAN-PD service-object policy-load test boot artifact",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: carries V1774 repair target into a rollbackable test boot: service-object route now loads precompiled SELinux policy before PM actors and rejects zombie per_mgr as ready.",
        "- Manifest: `tmp/wifi/v1777-service-object-policy-load-test-boot/manifest.json`",
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
        "- Actors remain bounded: `servicemanager`, `hwservicemanager`, VND service-manager fallback, `qrtr-ns`, `pd-mapper`, `rmt_storage`, `tftp_server`, `pm_proxy_helper`, `pm-service`, `/dev/subsys_modem` holder, `cnss_diag`, and stock `cnss-daemon`.",
        "- Repair target: service-object route now applies the V1092 SELinux policy-load precondition before PM actors and does not treat zombie `pm-service` as ready.",
        "- Still excluded: full `pm-proxy`, `boot_wlan`, restart-PD request, `/dev/subsys_esoc0`, forced RC1, fake-ONLINE, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping.",
        "",
        "## Property Runtime",
        "",
        *check_lines,
        "",
        "## Expected Live Discriminator",
        "",
        "- `service-object-route-provider-visible` if `vendor.qcom.PeripheralManager` appears after `per_mgr`.",
        "- `service-object-route-provider-still-hidden` if the SELinux policy-load precondition is present but provider remains absent.",
        "- Subsequent CNSS labels remain separate: `asInterface`, register-TX, `wlanmdsp` request, WLFW service 69, and `wlan0` are not chased by this build unit.",
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

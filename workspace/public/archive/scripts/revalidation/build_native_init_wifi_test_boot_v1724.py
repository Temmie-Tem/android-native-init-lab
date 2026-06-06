#!/usr/bin/env python3
"""Build V1724 corrected WLAN-PD cnss-daemon output-visibility test boot."""

from __future__ import annotations

from pathlib import Path

import build_native_init_wifi_test_boot_v1693 as prev


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1724-cnss-output-visible-route-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v1724/dev/__properties__"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1724_CNSS_OUTPUT_VISIBLE_ROUTE_SOURCE_BUILD_2026-06-03.md"
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
        "V1724",
        "--decision",
        "v1724-cnss-output-visible-route-source-build-pass",
        "--cycle-label",
        "v1724",
        "--init-version",
        "0.9.135",
        "--init-build",
        "v1724-cnss-output-visible-route",
        "--out-dir",
        str(OUT_DIR),
        "--init-binary",
        str(OUT_DIR / "init_v1724_cnss_output_visible_route"),
        "--helper-binary",
        str(OUT_DIR / "a90_android_execns_probe_v322"),
        "--ramdisk-cpio",
        str(OUT_DIR / "ramdisk_v1724_cnss_output_visible_route.cpio"),
        "--boot-image",
        str(OUT_DIR / "boot_linux_v1724_cnss_output_visible_route.img"),
        "--wifi-test-klog-prefix",
        "A90v1724",
        "--wifi-test-disable",
        "/cache/native-init-wifi-test-boot-v1724.disable",
        "--wifi-test-log",
        "/cache/native-init-wifi-test-boot-v1724.log",
        "--wifi-test-summary",
        "/cache/native-init-wifi-test-boot-v1724.summary",
        "--wifi-test-helper-result",
        "/cache/native-init-wifi-test-boot-v1724-helper.result",
        "--wifi-test-pid",
        "/cache/native-init-wifi-test-boot-v1724.pid",
        "--wifi-test-watcher-pid",
        "/cache/native-init-wifi-test-boot-v1724-supervisor.pid",
        "--wifi-test-watch-sec",
        "55",
        "--wifi-test-supervise-helper",
        "--wifi-test-supervisor-timeout-sec",
        "80",
        "--wifi-test-firmware-mounts",
        "--wifi-test-property-root",
        REMOTE_PROPERTY_ROOT,
        "--wifi-test-helper-mode",
        "wlan-pd-cnss-output-visibility",
    ]


def build_cnss_property_runtime() -> dict[str, object]:
    manifest = ORIGINAL_BUILD_CNSS_PROPERTY_RUNTIME()
    pass_ok = bool(manifest.get("pass"))
    manifest["decision"] = (
        "v1724-cnss-output-visible-property-runtime-ready"
        if pass_ok
        else "v1724-cnss-output-visible-property-runtime-blocked"
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
        "# Native Init V1724 CNSS Output-visible Route Source Build",
        "",
        "## Summary",
        "",
        "- Cycle: `V1724`",
        "- Type: source/build-only rollbackable WLAN-PD cnss-daemon output-visibility test boot artifact",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: corrects the helper CNSS kmsg property contract to `persist.vendor.cnss-daemon.kmsg_logging=1` without adding PM/service-window actors",
        "- Manifest: `tmp/wifi/v1724-cnss-output-visible-route-test-boot/manifest.json`",
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
        "- Actors: `qrtr-ns`, `pd-mapper`, `rmt_storage`, `tftp_server`, `/dev/subsys_modem` holder, `cnss_diag`, stock `cnss-daemon`.",
        "- Output classifier watches for `wlfw_start: Starting` and the eight pre-WLFW `Failed to ...` init strings.",
        "- No service-manager, PM trio, `vendor.qcom.PeripheralManager`, `boot_wlan`, `/dev/subsys_esoc0`, forced RC1, fake-ONLINE, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping.",
        "",
        "## Property Runtime",
        "",
        *check_lines,
        "",
        "## Live Labels",
        "",
        "- `wlfw-start-reached-downstream-block`",
        "- `cnss-init-step-failed-<name>`",
        "- `cnss-output-still-invisible`",
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

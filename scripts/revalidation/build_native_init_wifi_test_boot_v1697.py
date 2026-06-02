#!/usr/bin/env python3
"""Build V1697 WLAN-PD cnss-daemon kmsg4 output-visibility test boot."""

from __future__ import annotations

from pathlib import Path

import build_native_init_wifi_test_boot_v1693 as base


REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1697-wlan-pd-cnss-kmsg4-output-visibility-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v1697/dev/__properties__"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1697_WLAN_PD_CNSS_KMSG4_SOURCE_BUILD_2026-06-02.md"
)


ORIGINAL_RENDER_REPORT = base.render_report
ORIGINAL_BUILD_CNSS_PROPERTY_RUNTIME = base.build_cnss_property_runtime


def configure_base() -> None:
    base.OUT_DIR = OUT_DIR
    base.PROPERTY_RUNTIME_DIR = OUT_DIR / "property-runtime"
    base.PROPERTY_ROOT = base.PROPERTY_RUNTIME_DIR / "layout" / "dev" / "__properties__"
    base.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    base.REPORT_PATH = REPORT_PATH
    base.CNSS_PROPERTY_OVERRIDES = {
        "persist.vendor.cnss-daemon.kmsg_logging": "4",
        "persist.vendor.cnss-daemon.debug_level": "4",
    }
    base.DEFAULT_ARGS = [
        "--cycle",
        "V1697",
        "--decision",
        "v1697-wlan-pd-cnss-kmsg4-source-build-pass",
        "--cycle-label",
        "v1697",
        "--init-version",
        "0.9.126",
        "--init-build",
        "v1697-wlan-pd-cnss-kmsg4-output-visibility",
        "--out-dir",
        str(OUT_DIR),
        "--init-binary",
        str(OUT_DIR / "init_v1697_wlan_pd_cnss_kmsg4_output_visibility"),
        "--helper-binary",
        str(OUT_DIR / "a90_android_execns_probe_v312"),
        "--ramdisk-cpio",
        str(OUT_DIR / "ramdisk_v1697_wlan_pd_cnss_kmsg4_output_visibility.cpio"),
        "--boot-image",
        str(OUT_DIR / "boot_linux_v1697_wlan_pd_cnss_kmsg4_output_visibility.img"),
        "--wifi-test-klog-prefix",
        "A90v1697",
        "--wifi-test-disable",
        "/cache/native-init-wifi-test-boot-v1697.disable",
        "--wifi-test-log",
        "/cache/native-init-wifi-test-boot-v1697.log",
        "--wifi-test-summary",
        "/cache/native-init-wifi-test-boot-v1697.summary",
        "--wifi-test-helper-result",
        "/cache/native-init-wifi-test-boot-v1697-helper.result",
        "--wifi-test-pid",
        "/cache/native-init-wifi-test-boot-v1697.pid",
        "--wifi-test-watcher-pid",
        "/cache/native-init-wifi-test-boot-v1697-supervisor.pid",
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


def render_report(manifest: dict[str, object]) -> str:
    text = ORIGINAL_RENDER_REPORT(manifest)
    text = text.replace("V1693", "V1697")
    text = text.replace("v1693", "v1697")
    text = text.replace("non-log control-flow", "kmsg4 output-visibility")
    text = text.replace("Non-log Control-flow", "Kmsg4 Output-visibility")
    text += "\n".join([
        "",
        "## V1697 Delta",
        "",
        "- Raises `persist.vendor.cnss-daemon.kmsg_logging` from `1` to `4` so `wlfw_start` severity-2 messages are kmsg-visible.",
        "- Keeps `persist.vendor.cnss-daemon.debug_level=4`.",
        "- Keeps the V1680 internal modem firmware-serve route and does not add PM/service-window actors or `boot_wlan`.",
        "",
    ])
    return text


def build_cnss_property_runtime() -> dict[str, object]:
    manifest = ORIGINAL_BUILD_CNSS_PROPERTY_RUNTIME()
    pass_ok = bool(manifest.get("pass"))
    manifest["decision"] = (
        "v1697-cnss-kmsg4-property-runtime-ready"
        if pass_ok
        else "v1697-cnss-kmsg4-property-runtime-blocked"
    )
    return manifest


def main() -> int:
    configure_base()
    base.build_cnss_property_runtime = build_cnss_property_runtime
    base.render_report = render_report
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())

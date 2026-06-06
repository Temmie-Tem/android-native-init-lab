#!/usr/bin/env python3
"""Build V1699 WLAN-PD cnss-daemon tracefs-uprobe visibility test boot."""

from __future__ import annotations

from pathlib import Path

import build_native_init_wifi_test_boot_v1693 as base


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1699-wlan-pd-cnss-tracefs-uprobe-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v1699/dev/__properties__"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1699_WLAN_PD_CNSS_TRACEFS_UPROBE_SOURCE_BUILD_2026-06-02.md"
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
        "V1699",
        "--decision",
        "v1699-wlan-pd-cnss-tracefs-uprobe-source-build-pass",
        "--cycle-label",
        "v1699",
        "--init-version",
        "0.9.127",
        "--init-build",
        "v1699-wlan-pd-cnss-tracefs-uprobe",
        "--out-dir",
        str(OUT_DIR),
        "--init-binary",
        str(OUT_DIR / "init_v1699_wlan_pd_cnss_tracefs_uprobe"),
        "--helper-binary",
        str(OUT_DIR / "a90_android_execns_probe_v313"),
        "--ramdisk-cpio",
        str(OUT_DIR / "ramdisk_v1699_wlan_pd_cnss_tracefs_uprobe.cpio"),
        "--boot-image",
        str(OUT_DIR / "boot_linux_v1699_wlan_pd_cnss_tracefs_uprobe.img"),
        "--wifi-test-klog-prefix",
        "A90v1699",
        "--wifi-test-disable",
        "/cache/native-init-wifi-test-boot-v1699.disable",
        "--wifi-test-log",
        "/cache/native-init-wifi-test-boot-v1699.log",
        "--wifi-test-summary",
        "/cache/native-init-wifi-test-boot-v1699.summary",
        "--wifi-test-helper-result",
        "/cache/native-init-wifi-test-boot-v1699-helper.result",
        "--wifi-test-pid",
        "/cache/native-init-wifi-test-boot-v1699.pid",
        "--wifi-test-watcher-pid",
        "/cache/native-init-wifi-test-boot-v1699-supervisor.pid",
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
    text = ORIGINAL_RENDER_REPORT(manifest)
    text = text.replace("V1693", "V1699")
    text = text.replace("v1693", "v1699")
    text = text.replace("non-log control-flow", "tracefs uprobe visibility")
    text = text.replace("Non-log Control-flow", "Tracefs Uprobe Visibility")
    text = text.replace(
        "The new fallback does not write tracefs and does not arm uprobes; it records PID, maps load-bias, computed `wlfw_start` runtime PC, fd/socket counts, task state, and MHI/ks absence.",
        "The helper first attempts a bounded tracefs uprobe for `cnss-daemon+0xec00` and falls back to `/proc` PID/maps/fd/task-state evidence when uprobe registration is unavailable.",
    )
    text = text.replace(
        "- `cnss-uprobe-unavailable-fallback-needed`\n- Existing output labels remain captured through `wlan_pd_cnss_output_visibility.label`.",
        "- `cnss-wlfw-entry-hit-downstream-wait`\n- `cnss-wlfw-entry-not-hit-init-stall`\n- `cnss-uprobe-unavailable-fallback-needed`\n- Existing output labels remain captured through `wlan_pd_cnss_output_visibility.label`.",
    )
    text += "\n".join([
        "",
        "## V1699 Delta",
        "",
        "- Uses helper `a90_android_execns_probe v313`.",
        "- Arms a bounded tracefs uprobe for stock `/vendor/bin/cnss-daemon:0xec00` (`wlfw_start`) before starting `cnss-daemon`.",
        "- Mounts debugfs in the test boot so `/sys/kernel/debug/tracing/uprobe_events` can be used when supported.",
        "- Keeps `persist.vendor.cnss-daemon.kmsg_logging=4` and `debug_level=4`.",
        "- Keeps the V1680 internal-modem firmware-serve route and does not add PM/service-window actors or `boot_wlan`.",
        "",
    ])
    return text


def build_cnss_property_runtime() -> dict[str, object]:
    manifest = ORIGINAL_BUILD_CNSS_PROPERTY_RUNTIME()
    pass_ok = bool(manifest.get("pass"))
    manifest["decision"] = (
        "v1699-cnss-tracefs-uprobe-property-runtime-ready"
        if pass_ok
        else "v1699-cnss-tracefs-uprobe-property-runtime-blocked"
    )
    return manifest


def main() -> int:
    configure_base()
    base.build_cnss_property_runtime = build_cnss_property_runtime
    base.render_report = render_report
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())

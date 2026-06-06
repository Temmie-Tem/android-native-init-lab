#!/usr/bin/env python3
"""Build V1743 WLAN-PD pure-route non-log parity test boot."""

from __future__ import annotations

from pathlib import Path

import build_native_init_wifi_test_boot_v1739 as prev


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1743-wlan-pd-pure-nonlog-parity-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v1743/dev/__properties__"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1743_WLAN_PD_PURE_NONLOG_PARITY_SOURCE_BUILD_2026-06-03.md"
)


def build_cnss_property_runtime() -> dict[str, object]:
    manifest = prev.ORIGINAL_BUILD_CNSS_PROPERTY_RUNTIME()
    pass_ok = bool(manifest.get("pass"))
    manifest["decision"] = (
        "v1743-cnss-output-source-property-runtime-ready"
        if pass_ok
        else "v1743-cnss-output-source-property-runtime-blocked"
    )
    return manifest


def configure_base() -> None:
    prev.configure_base()
    prev.prev.OUT_DIR = OUT_DIR
    prev.prev.PROPERTY_RUNTIME_DIR = OUT_DIR / "property-runtime"
    prev.prev.PROPERTY_ROOT = prev.prev.PROPERTY_RUNTIME_DIR / "layout" / "dev" / "__properties__"
    prev.prev.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev.prev.REPORT_PATH = REPORT_PATH
    prev.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev.REPORT_PATH = REPORT_PATH
    prev.prev.DEFAULT_ARGS = [
        "--cycle",
        "V1743",
        "--decision",
        "v1743-wlan-pd-pure-nonlog-parity-source-build-pass",
        "--cycle-label",
        "v1743",
        "--init-version",
        "0.9.141",
        "--init-build",
        "v1743-wlan-pd-pure-nonlog-parity",
        "--out-dir",
        str(OUT_DIR),
        "--init-binary",
        str(OUT_DIR / "init_v1743_wlan_pd_pure_nonlog_parity"),
        "--helper-binary",
        str(OUT_DIR / "a90_android_execns_probe_v328"),
        "--ramdisk-cpio",
        str(OUT_DIR / "ramdisk_v1743_wlan_pd_pure_nonlog_parity.cpio"),
        "--boot-image",
        str(OUT_DIR / "boot_linux_v1743_wlan_pd_pure_nonlog_parity.img"),
        "--wifi-test-klog-prefix",
        "A90v1743",
        "--wifi-test-disable",
        "/cache/native-init-wifi-test-boot-v1743.disable",
        "--wifi-test-log",
        "/cache/native-init-wifi-test-boot-v1743.log",
        "--wifi-test-summary",
        "/cache/native-init-wifi-test-boot-v1743.summary",
        "--wifi-test-helper-result",
        "/cache/native-init-wifi-test-boot-v1743-helper.result",
        "--wifi-test-pid",
        "/cache/native-init-wifi-test-boot-v1743.pid",
        "--wifi-test-watcher-pid",
        "/cache/native-init-wifi-test-boot-v1743-supervisor.pid",
        "--wifi-test-watch-sec",
        "70",
        "--wifi-test-supervise-helper",
        "--wifi-test-supervisor-timeout-sec",
        "95",
        "--wifi-test-firmware-mounts",
        "--wifi-test-property-root",
        REMOTE_PROPERTY_ROOT,
        "--wifi-test-helper-mode",
        "wlan-pd-cnss-output-visibility",
    ]


def render_report(manifest: dict[str, object]) -> str:
    wifi = manifest["wifi_test"]
    property_runtime = manifest["cnss_nonlog_property_runtime"]
    check_lines = [
        f"- `{item['name']}`: `{item['actual']}` in `{item['context']}`"
        for item in property_runtime["checks"]
    ]
    return "\n".join([
        "# Native Init V1743 WLAN-PD Pure-route Non-log Parity Source Build",
        "",
        "## Summary",
        "",
        "- Cycle: `V1743`",
        "- Type: source/build-only rollbackable pure-route non-log parity test boot artifact",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: keeps the V1740 pure internal-modem route but adds private tracefs materialization so the same CNSS non-log uprobe observer can run without service-manager actors.",
        "- Manifest: `tmp/wifi/v1743-wlan-pd-pure-nonlog-parity-test-boot/manifest.json`",
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
        "- New source change: materialize private tracefs for output-visibility mode before CNSS uprobe arming.",
        "- No service-manager, PM trio, `boot_wlan`, `/dev/subsys_esoc0`, forced RC1, fake-ONLINE, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping.",
        "",
        "## Property Runtime",
        "",
        *check_lines,
        "",
        "## Expected Live Discriminator",
        "",
        "- If tracefs becomes available and `wlfw_start` remains absent, V1740's pure-route no-entry result is confirmed without the old non-log measurement gap.",
        "- If tracefs becomes available and `wlfw_start` appears, V1740 was only a tracefs visibility gap and the blocker returns to downstream WLAN-PD/WLFW publication.",
        "- If tracefs is still unavailable, classify the live result as a tracefs-surface failure before adding any actors.",
        "",
        "## Safety Scope",
        "",
        "This build script performed host-side source/build work only. It did not issue live device commands, flash, reboot, scan/connect, use credentials, configure DHCP/routes, perform external ping, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE` spoof, run PCI rescan/platform bind-unbind, or write firmware/boot/device partitions.",
        "",
    ])


def main() -> int:
    configure_base()
    prev.prev.build_cnss_property_runtime = build_cnss_property_runtime
    prev.prev.render_report = render_report
    return prev.prev.main()


if __name__ == "__main__":
    raise SystemExit(main())

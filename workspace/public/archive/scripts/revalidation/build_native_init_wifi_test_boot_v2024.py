#!/usr/bin/env python3
"""Build V2024 native Android-parity RFS fallback test boot."""

from __future__ import annotations

from pathlib import Path

import build_native_init_wifi_test_boot_v2006 as prev2006


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v2024-rfs-android-fallback-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v2024/dev/__properties__"
EXPECTED_HELPER_MARKER = "a90_android_execns_probe v381"
EXPECTED_HELPER_SHA256 = "dd127b3263ee8ae2a5da3f060da44d6d68b33f8dab02edf05dbbc6d0b231f9a7"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V2024_RFS_ANDROID_FALLBACK_SOURCE_BUILD_2026-06-04.md"
)


ORIGINAL_CONFIGURE_BASE = prev2006.configure_base


def configure_base() -> None:
    prev2006.OUT_DIR = OUT_DIR
    prev2006.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev2006.EXPECTED_HELPER_MARKER = EXPECTED_HELPER_MARKER
    prev2006.EXPECTED_HELPER_SHA256 = EXPECTED_HELPER_SHA256
    prev2006.REPORT_PATH = REPORT_PATH
    ORIGINAL_CONFIGURE_BASE()

    base = prev2006.build_base_module()
    args = list(base.DEFAULT_ARGS)
    replacements = {
        "--cycle": "V2024",
        "--decision": "v2024-rfs-android-fallback-source-build-pass",
        "--cycle-label": "v2024",
        "--init-version": "0.9.194",
        "--init-build": "v2024-rfs-android-fallback",
        "--out-dir": str(OUT_DIR),
        "--init-binary": str(OUT_DIR / "init_v2024_rfs_android_fallback"),
        "--helper-binary": str(OUT_DIR / "a90_android_execns_probe_v381"),
        "--ramdisk-cpio": str(OUT_DIR / "ramdisk_v2024_rfs_android_fallback.cpio"),
        "--boot-image": str(OUT_DIR / "boot_linux_v2024_rfs_android_fallback.img"),
        "--wifi-test-klog-prefix": "A90v2024",
        "--wifi-test-disable": "/cache/native-init-wifi-test-boot-v2024.disable",
        "--wifi-test-log": "/cache/native-init-wifi-test-boot-v2024.log",
        "--wifi-test-summary": "/cache/native-init-wifi-test-boot-v2024.summary",
        "--wifi-test-helper-result": "/cache/native-init-wifi-test-boot-v2024-helper.result",
        "--wifi-test-pid": "/cache/native-init-wifi-test-boot-v2024.pid",
        "--wifi-test-watcher-pid": "/cache/native-init-wifi-test-boot-v2024-supervisor.pid",
        "--wifi-test-property-root": REMOTE_PROPERTY_ROOT,
    }
    for key, value in replacements.items():
        prev2006.set_arg(args, key, value)
    base.DEFAULT_ARGS = args


def render_report(manifest: dict[str, object]) -> str:
    wifi = manifest["wifi_test"]
    property_runtime = manifest["cnss_nonlog_property_runtime"]
    check_lines = [
        f"- `{item['name']}`: `{item['actual']}` in `{item['context']}`"
        for item in property_runtime["checks"]
    ]
    return "\n".join([
        "# Native Init V2024 RFS Android Fallback Source Build",
        "",
        "## Summary",
        "",
        "- Cycle: `V2024`",
        "- Type: source/build-only rollbackable internal-modem Android-parity RFS fallback artifact",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: helper v381 changes only the namespace-local RFS bridge: `readonly/vendor/firmware_mnt/image/wlanmdsp.mbn` is left absent like Android, while `readonly/vendor/firmware/wlanmdsp.mbn` resolves to the existing `/vendor/firmware/wlanmdsp.mbn` fallback.",
        "- Manifest: `tmp/wifi/v2024-rfs-android-fallback-test-boot/manifest.json`",
        f"- Boot image: `{manifest['boot_image']}`",
        f"- Boot SHA256: `{manifest['boot_sha256']}`",
        f"- Init: `A90 Linux init {manifest['init_version']} ({manifest['init_build']})`",
        f"- Helper marker: `{manifest['helper_marker']}`",
        f"- Helper SHA256: `{manifest['helper_sha256']}`",
        "",
        "## Route",
        "",
        f"- Helper runtime mode: `{wifi['helper_runtime_mode']}`",
        f"- Helper timeout: `{wifi['helper_timeout_sec']}`",
        f"- Property root: `{REMOTE_PROPERTY_ROOT}`",
        f"- Light firmware trace: `{wifi['light_firmware_trace']}`",
        "- Kept: clean-DSP companion, service managers, `pm-service`, `/dev/subsys_modem` holder, `cnss_diag`, stock `cnss-daemon`, `rmt_storage`, `tftp_server`, `pd-mapper`, firmware mounts, readwrite tmpfs bridge, post-BDF tail probes, and light klog/ICNSS summaries.",
        "- Changed: readonly RFS bridge now mirrors Android fallback semantics instead of satisfying the first `firmware_mnt/image` probe path.",
        "- Excluded: tftp_server ptrace, boot-time QRTR matrix, rild/cnss/pm-service multi-strace, private SDX50M route, `/dev/subsys_esoc0` open, eSoC notify/BOOT_DONE, PCI rescan/bind, platform unbind, PMIC/GPIO/GDSC/regulator writes, forced RC1/case, restart-PD request, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping.",
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
    prev2006.configure_base = configure_base
    prev2006.render_report = render_report
    return prev2006.main()


if __name__ == "__main__":
    raise SystemExit(main())

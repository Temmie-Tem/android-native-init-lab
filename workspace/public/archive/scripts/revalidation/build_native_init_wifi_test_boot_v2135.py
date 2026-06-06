#!/usr/bin/env python3
"""Build V2135 native firmware_class fallback-request sampler test boot."""

from __future__ import annotations

from pathlib import Path

import build_native_init_wifi_test_boot_v2133 as prev2133


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v2135-firmware-class-fallback-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v2135/dev/__properties__"
EXPECTED_HELPER_MARKER = "a90_android_execns_probe v425"
EXPECTED_HELPER_SHA256 = "6ca1a61f71fd68df2d3ce1d015e61830490cb1f63a4e0ae059389f74eb1f3d8d"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V2135_FIRMWARE_CLASS_FALLBACK_SOURCE_BUILD_2026-06-05.md"
)
HELPER_FLAGS = (
    *prev2133.prev2131.HELPER_FLAGS,
    "-DA90_WIFI_TEST_BOOT_FIRMWARE_CLASS_FALLBACK_SAMPLER=1",
)
EXTRA_INIT_FLAGS = prev2133.EXTRA_INIT_FLAGS


def base_module():
    return prev2133.base_module()


def configure_base() -> None:
    prev2133.OUT_DIR = OUT_DIR
    prev2133.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev2133.REPORT_PATH = REPORT_PATH
    prev2133.EXPECTED_HELPER_MARKER = EXPECTED_HELPER_MARKER
    prev2133.EXPECTED_HELPER_SHA256 = EXPECTED_HELPER_SHA256
    prev2133.EXTRA_INIT_FLAGS = EXTRA_INIT_FLAGS
    prev2133.prev2131.HELPER_FLAGS = HELPER_FLAGS
    prev2133.configure_base()

    base = base_module()
    args = list(base.DEFAULT_ARGS)
    replacements = {
        "--cycle": "V2135",
        "--decision": "v2135-firmware-class-fallback-source-build-pass",
        "--cycle-label": "v2135",
        "--init-version": "0.9.242",
        "--init-build": "v2135-firmware-class-fallback",
        "--out-dir": str(OUT_DIR),
        "--init-binary": str(OUT_DIR / "init_v2135_firmware_class_fallback"),
        "--helper-binary": str(OUT_DIR / "a90_android_execns_probe_v425_firmware_class_fallback"),
        "--ramdisk-cpio": str(OUT_DIR / "ramdisk_v2135_firmware_class_fallback.cpio"),
        "--boot-image": str(OUT_DIR / "boot_linux_v2135_firmware_class_fallback.img"),
        "--wifi-test-klog-prefix": "A90v2135",
        "--wifi-test-disable": "/cache/native-init-wifi-test-boot-v2135.disable",
        "--wifi-test-log": "/cache/native-init-wifi-test-boot-v2135.log",
        "--wifi-test-summary": "/cache/native-init-wifi-test-boot-v2135.summary",
        "--wifi-test-helper-result": "/cache/native-init-wifi-test-boot-v2135-helper.result",
        "--wifi-test-pid": "/cache/native-init-wifi-test-boot-v2135.pid",
        "--wifi-test-watcher-pid": "/cache/native-init-wifi-test-boot-v2135-supervisor.pid",
        "--wifi-test-property-root": REMOTE_PROPERTY_ROOT,
    }
    for key, value in replacements.items():
        prev2133.prev2131.prev2129.prev2127.prev2120.prev2112.prev2108.prev2106.prev2102.prev2100.prev2097.prev2095.prev2082.prev2080.prev2058.prev2038.prev2008.prev2006.set_arg(args, key, value)
    base.DEFAULT_ARGS = args
    base.base.EXTRA_INIT_FLAGS = EXTRA_INIT_FLAGS


def render_report(manifest: dict[str, object]) -> str:
    wifi = manifest["wifi_test"]
    property_runtime = manifest["cnss_nonlog_property_runtime"]
    check_lines = [
        f"- `{item['name']}`: `{item['actual']}` in `{item['context']}`"
        for item in property_runtime["checks"]
    ]
    return "\n".join([
        "# Native Init V2135 Firmware Class Fallback Source Build",
        "",
        "## Summary",
        "",
        "- Cycle: `V2135`",
        "- Type: source/build-only discriminator for the exact kernel firmware-class fallback request edge.",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: helper v425 keeps the V2133 global firmware_class vendor-path bridge and V2131 stack sampler, then adds a bounded read-only `/sys/class/firmware` and `/sys/devices/virtual/firmware` snapshot at the stuck `request_firmware -> qdf_ini_parse` window.",
        "- Manifest: `tmp/wifi/v2135-firmware-class-fallback-test-boot/manifest.json`",
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
        "- Kept: V2133 rollbackable `firmware_class.path=/mnt/vendor/firmware` apply/restore, read-only `sda29` mount, dual-RFS bridges, readwrite tmpfs bridge, post-FW_READY `boot_wlan` gate, stack sampler, focused PerMgr/WLFW summaries, post-BDF summary, and long lower-window hold.",
        "- Added: `firmware_class_fallback_sampler` at `after_boot_wlan_trigger` and `after_boot_wlan_long_window`, with hard-capped read-only sysfs enumeration and no reads from firmware `data` nodes.",
        "- Excluded: firmware fallback writes, tracefs writes, sysrq, DIAG, boot-time QRTR matrix, rild/cnss/pm-service strace, `tftp_server` ptrace, AP QMI send, module load/unload, driver bind/unbind, `/dev/subsys_esoc0`, eSoC notify/BOOT_DONE, PCI rescan/bind, platform unbind, PMIC/GPIO/GDSC/regulator writes, forced RC1/case, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, and firmware/partition writes.",
        "",
        "## Branch",
        "",
        "- If the sampler captures a `WCNSS`/`qca`/`qdf`/`cfg` fallback entry while the stack remains in `qdf_ini_parse`, the exact request name/error is the next bounded fix target.",
        "- If no firmware-class fallback entry exists while the stack remains in `qdf_ini_parse`, the next unit should capture the `qdf_file_read()` argument rather than retrying the AP-side producer path.",
        "- If `wlan0` appears, stop before credentials and run the dedicated connectivity gate.",
        "",
        "## Property Runtime",
        "",
        *check_lines,
        "",
        "## Safety Scope",
        "",
        "This build script performed host-side source/build work only. The eventual live handoff is rollbackable and permits only the existing temporary `firmware_class.path` sysfs write with restore plus read-only firmware-class sysfs snapshots. It does not write firmware fallback `loading`/`data` nodes, `sda29`, firmware files, EFS, boot partitions, Wi-Fi credentials, network routes, or external pings.",
        "",
    ])


def main() -> int:
    configure_base()
    base = base_module()
    base.base.EXPECTED_HELPER_MARKER = EXPECTED_HELPER_MARKER
    base.base.EXPECTED_HELPER_SHA256 = EXPECTED_HELPER_SHA256
    prev2133.prev2131.prev2129.prev2127.prev2120.prev2112.prev2108.prev2106.prev2102.prev2100.prev2097.prev2095.prev2082.prev2080.prev2058.prev2038.patch_helper_builder(base)
    base.render_report = render_report
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())

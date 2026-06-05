#!/usr/bin/env python3
"""Build V2133 native firmware_class vendor-path bridge test boot."""

from __future__ import annotations

from pathlib import Path

import build_native_init_wifi_test_boot_v2131 as prev2131


REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v2133-fwclass-vendor-path-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v2133/dev/__properties__"
EXPECTED_HELPER_MARKER = "a90_android_execns_probe v424"
EXPECTED_HELPER_SHA256 = "ebfcddfdb5e54064fa561ea24d355a7c2ec31196c94285da09a189b4fac1a93d"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V2133_FWCLASS_VENDOR_PATH_SOURCE_BUILD_2026-06-05.md"
)
EXTRA_INIT_FLAGS = ("-DA90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH=1",)


def base_module():
    return prev2131.prev2129.prev2127.prev2120.prev2112.prev2108.prev2106.prev2102.prev2100.prev2097.prev2095.prev2082.prev2080.prev2058.prev2038.prev2008.prev2006.build_base_module()


def configure_base() -> None:
    prev2131.OUT_DIR = OUT_DIR
    prev2131.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev2131.REPORT_PATH = REPORT_PATH
    prev2131.EXPECTED_HELPER_MARKER = EXPECTED_HELPER_MARKER
    prev2131.EXPECTED_HELPER_SHA256 = EXPECTED_HELPER_SHA256
    prev2131.configure_base()

    base = base_module()
    args = list(base.DEFAULT_ARGS)
    replacements = {
        "--cycle": "V2133",
        "--decision": "v2133-fwclass-vendor-path-source-build-pass",
        "--cycle-label": "v2133",
        "--init-version": "0.9.241",
        "--init-build": "v2133-fwclass-vendor-path",
        "--out-dir": str(OUT_DIR),
        "--init-binary": str(OUT_DIR / "init_v2133_fwclass_vendor_path"),
        "--helper-binary": str(OUT_DIR / "a90_android_execns_probe_v424_fwclass_vendor_path"),
        "--ramdisk-cpio": str(OUT_DIR / "ramdisk_v2133_fwclass_vendor_path.cpio"),
        "--boot-image": str(OUT_DIR / "boot_linux_v2133_fwclass_vendor_path.img"),
        "--wifi-test-klog-prefix": "A90v2133",
        "--wifi-test-disable": "/cache/native-init-wifi-test-boot-v2133.disable",
        "--wifi-test-log": "/cache/native-init-wifi-test-boot-v2133.log",
        "--wifi-test-summary": "/cache/native-init-wifi-test-boot-v2133.summary",
        "--wifi-test-helper-result": "/cache/native-init-wifi-test-boot-v2133-helper.result",
        "--wifi-test-pid": "/cache/native-init-wifi-test-boot-v2133.pid",
        "--wifi-test-watcher-pid": "/cache/native-init-wifi-test-boot-v2133-supervisor.pid",
        "--wifi-test-property-root": REMOTE_PROPERTY_ROOT,
    }
    for key, value in replacements.items():
        prev2131.prev2129.prev2127.prev2120.prev2112.prev2108.prev2106.prev2102.prev2100.prev2097.prev2095.prev2082.prev2080.prev2058.prev2038.prev2008.prev2006.set_arg(args, key, value)
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
        "# Native Init V2133 Firmware Class Vendor Path Source Build",
        "",
        "## Summary",
        "",
        "- Cycle: `V2133`",
        "- Type: source/build-only discriminator for the kernel QCACLD firmware request root.",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: PID1 now compile-gates a rollbackable global `/mnt/vendor` read-only `sda29` mount and temporary `firmware_class.path=/mnt/vendor/firmware` switch around the supervised V2131/V2132 route, so kernel-worker `request_firmware()` can resolve `wlan/qca_cld/WCNSS_qcom_cfg.ini` from the real vendor firmware tree.",
        "- Manifest: `tmp/wifi/v2133-fwclass-vendor-path-test-boot/manifest.json`",
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
        "- Kept: V2131 stack sampler, V2129 post-FW_READY `boot_wlan` gate, V2127 ICNSS stats, dual-RFS bridges, shared `server_info.txt`, root lower companions, PerMgr/WLFW focused summaries, post-BDF summary, and long lower-window hold.",
        "- Added: PID1 global `/mnt/vendor` `sda29` mount with `ro,noload`, required stats for `WCNSS_qcom_cfg.ini`, `bdwlan.bin`, and `regdb.bin`, temporary `/sys/module/firmware_class/parameters/path` switch to `/mnt/vendor/firmware`, readback verification, and supervised restore/unmount cleanup.",
        "- Excluded: ICNSS bind/unbind, module load/unload, tracefs writes, sysrq, DIAG, boot-time QRTR matrix, rild/cnss/pm-service strace, `tftp_server` ptrace, AP QMI send, `/dev/subsys_esoc0`, eSoC notify/BOOT_DONE, PCI rescan/bind, platform unbind, PMIC/GPIO/GDSC/regulator writes, forced RC1/case, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, and firmware/partition writes.",
        "",
        "## Branch",
        "",
        "- If `REGISTER_DRIVER` reaches `DRIVER PROBED` and `wlan0` appears, stop before credentials and run the dedicated connectivity gate.",
        "- If the stack still shows `request_firmware -> qdf_ini_parse`, the global vendor firmware path did not satisfy the kernel request and the live log/readback identifies why.",
        "- If the INI stack disappears but `wlan0` still does not appear, classify the next QCACLD probe/startup blocker from the existing long-window ICNSS and stack sampler evidence.",
        "",
        "## Property Runtime",
        "",
        *check_lines,
        "",
        "## Safety Scope",
        "",
        "This build script performed host-side source/build work only. The eventual live handoff is rollbackable and permits one temporary global `firmware_class.path` sysfs write with verified restore plus a read-only `sda29` mount. It does not write `sda29`, firmware files, EFS, boot partitions, Wi-Fi credentials, network routes, or external pings.",
        "",
    ])


def main() -> int:
    configure_base()
    base = base_module()
    base.base.EXPECTED_HELPER_MARKER = EXPECTED_HELPER_MARKER
    base.base.EXPECTED_HELPER_SHA256 = EXPECTED_HELPER_SHA256
    prev2131.prev2129.prev2127.prev2120.prev2112.prev2108.prev2106.prev2102.prev2100.prev2097.prev2095.prev2082.prev2080.prev2058.prev2038.patch_helper_builder(base)
    base.render_report = render_report
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())

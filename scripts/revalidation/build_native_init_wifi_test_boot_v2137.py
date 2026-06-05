#!/usr/bin/env python3
"""Build V2137 native QCACLD firmware_class fallback feeder test boot."""

from __future__ import annotations

from pathlib import Path

import build_native_init_wifi_test_boot_v2135 as prev2135


REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v2137-qcacld-fwclass-feeder-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v2137/dev/__properties__"
EXPECTED_HELPER_MARKER = "a90_android_execns_probe v426"
EXPECTED_HELPER_SHA256 = "a766fd277752bd5a31637daaca9fbf6458abde5c5566a9a756ea8cd163422288"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V2137_QCACLD_FWCLASS_FEEDER_SOURCE_BUILD_2026-06-05.md"
)
HELPER_FLAGS = (
    *prev2135.HELPER_FLAGS,
    "-DA90_WIFI_TEST_BOOT_QCACLD_FIRMWARE_CLASS_FALLBACK_FEEDER=1",
)
EXTRA_INIT_FLAGS = prev2135.EXTRA_INIT_FLAGS


def base_module():
    return prev2135.base_module()


def configure_base() -> None:
    prev2135.OUT_DIR = OUT_DIR
    prev2135.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev2135.REPORT_PATH = REPORT_PATH
    prev2135.EXPECTED_HELPER_MARKER = EXPECTED_HELPER_MARKER
    prev2135.EXPECTED_HELPER_SHA256 = EXPECTED_HELPER_SHA256
    prev2135.HELPER_FLAGS = HELPER_FLAGS
    prev2135.EXTRA_INIT_FLAGS = EXTRA_INIT_FLAGS
    prev2135.prev2133.prev2131.HELPER_FLAGS = HELPER_FLAGS
    prev2135.configure_base()

    base = base_module()
    args = list(base.DEFAULT_ARGS)
    replacements = {
        "--cycle": "V2137",
        "--decision": "v2137-qcacld-fwclass-feeder-source-build-pass",
        "--cycle-label": "v2137",
        "--init-version": "0.9.243",
        "--init-build": "v2137-qcacld-fwclass-feeder",
        "--out-dir": str(OUT_DIR),
        "--init-binary": str(OUT_DIR / "init_v2137_qcacld_fwclass_feeder"),
        "--helper-binary": str(OUT_DIR / "a90_android_execns_probe_v426_qcacld_fwclass_feeder"),
        "--ramdisk-cpio": str(OUT_DIR / "ramdisk_v2137_qcacld_fwclass_feeder.cpio"),
        "--boot-image": str(OUT_DIR / "boot_linux_v2137_qcacld_fwclass_feeder.img"),
        "--wifi-test-klog-prefix": "A90v2137",
        "--wifi-test-disable": "/cache/native-init-wifi-test-boot-v2137.disable",
        "--wifi-test-log": "/cache/native-init-wifi-test-boot-v2137.log",
        "--wifi-test-summary": "/cache/native-init-wifi-test-boot-v2137.summary",
        "--wifi-test-helper-result": "/cache/native-init-wifi-test-boot-v2137-helper.result",
        "--wifi-test-pid": "/cache/native-init-wifi-test-boot-v2137.pid",
        "--wifi-test-watcher-pid": "/cache/native-init-wifi-test-boot-v2137-supervisor.pid",
        "--wifi-test-property-root": REMOTE_PROPERTY_ROOT,
    }
    for key, value in replacements.items():
        prev2135.prev2133.prev2131.prev2129.prev2127.prev2120.prev2112.prev2108.prev2106.prev2102.prev2100.prev2097.prev2095.prev2082.prev2080.prev2058.prev2038.prev2008.prev2006.set_arg(args, key, value)
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
        "# Native Init V2137 QCACLD Firmware Class Feeder Source Build",
        "",
        "## Summary",
        "",
        "- Cycle: `V2137`",
        "- Type: source/build-only functional bridge for the V2136 firmware_class fallback request edge.",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: helper v426 keeps the V2135 read-only sampler and adds a bounded userspace-fallback feeder for only `WCNSS_qcom_cfg.ini`, `bdwlan.bin`, and `regdb.bin`, sourced from the read-only vendor firmware tree.",
        "- Manifest: `tmp/wifi/v2137-qcacld-fwclass-feeder-test-boot/manifest.json`",
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
        "- Kept: V2133 rollbackable `firmware_class.path=/mnt/vendor/firmware` apply/restore, read-only `sda29` mount, RFS bridges, post-FW_READY `boot_wlan` gate, stack sampler, firmware_class fallback sampler, focused PerMgr/WLFW summaries, and long lower-window hold.",
        "- Added: `qcacld_firmware_class_fallback_feeder` after the read-only sampler captures the fallback request, writing only the matching sysfs `loading`/`data` fallback nodes for the three known QCACLD files.",
        "- Excluded: firmware/partition file writes, EFS writes, tracefs writes, sysrq, DIAG, boot-time QRTR matrix, rild/cnss/pm-service strace, `tftp_server` ptrace, AP QMI send, module load/unload, driver bind/unbind, `/dev/subsys_esoc0`, eSoC notify/BOOT_DONE, PCI rescan/bind, platform unbind, PMIC/GPIO/GDSC/regulator writes, forced RC1/case, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping.",
        "",
        "## Branch",
        "",
        "- If feeder writes all requested QCACLD files and `wlan0` appears, stop before credentials and run the dedicated native connectivity gate.",
        "- If feeder writes INI but the next request is BDF/regdb and stalls, extend only the observed requested file set.",
        "- If feeder succeeds for all three files but `REGISTER_DRIVER` still returns without `wlan0`, classify the next QCACLD startup blocker from ICNSS stats/stack evidence.",
        "",
        "## Property Runtime",
        "",
        *check_lines,
        "",
        "## Safety Scope",
        "",
        "This build script performed host-side source/build work only. The eventual live handoff is rollbackable and allows bounded firmware_class userspace-fallback sysfs writes only for the observed QCACLD request nodes. It does not write `sda29`, firmware files, EFS, boot partitions, Wi-Fi credentials, network routes, or external pings.",
        "",
    ])


def main() -> int:
    configure_base()
    base = base_module()
    base.base.EXPECTED_HELPER_MARKER = EXPECTED_HELPER_MARKER
    base.base.EXPECTED_HELPER_SHA256 = EXPECTED_HELPER_SHA256
    prev2135.prev2133.prev2131.prev2129.prev2127.prev2120.prev2112.prev2108.prev2106.prev2102.prev2100.prev2097.prev2095.prev2082.prev2080.prev2058.prev2038.patch_helper_builder(base)
    base.render_report = render_report
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())

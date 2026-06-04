#!/usr/bin/env python3
"""Build V2100 native TFTP persist-RFS auto-dir parity test boot."""

from __future__ import annotations

from pathlib import Path

import build_native_init_wifi_test_boot_v2097 as prev2097


REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v2100-tftp-persist-rfs-autodir-parity-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v2100/dev/__properties__"
EXPECTED_HELPER_MARKER = "a90_android_execns_probe v411"
EXPECTED_HELPER_SHA256 = "b3b68a3560f8c16f495e7028922ca5157222c36f56780737e27833a3e02d0f1d"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V2100_TFTP_PERSIST_RFS_AUTODIR_PARITY_SOURCE_BUILD_2026-06-05.md"
)
HELPER_FLAGS = (
    *prev2097.HELPER_FLAGS,
    "-DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_AUTODIR_PARITY=1",
)


def configure_base() -> None:
    prev2097.OUT_DIR = OUT_DIR
    prev2097.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev2097.REPORT_PATH = REPORT_PATH
    prev2097.EXPECTED_HELPER_MARKER = EXPECTED_HELPER_MARKER
    prev2097.EXPECTED_HELPER_SHA256 = EXPECTED_HELPER_SHA256
    prev2097.HELPER_FLAGS = HELPER_FLAGS
    prev2097.configure_base()

    base = prev2097.prev2095.prev2082.prev2080.prev2058.prev2038.prev2008.prev2006.build_base_module()
    args = list(base.DEFAULT_ARGS)
    replacements = {
        "--cycle": "V2100",
        "--decision": "v2100-tftp-persist-rfs-autodir-parity-source-build-pass",
        "--cycle-label": "v2100",
        "--init-version": "0.9.227",
        "--init-build": "v2100-tftp-persist-rfs-autodir-parity",
        "--out-dir": str(OUT_DIR),
        "--init-binary": str(OUT_DIR / "init_v2100_tftp_persist_rfs_autodir_parity"),
        "--helper-binary": str(OUT_DIR / "a90_android_execns_probe_v411_tftp_persist_rfs_autodir_parity"),
        "--ramdisk-cpio": str(OUT_DIR / "ramdisk_v2100_tftp_persist_rfs_autodir_parity.cpio"),
        "--boot-image": str(OUT_DIR / "boot_linux_v2100_tftp_persist_rfs_autodir_parity.img"),
        "--wifi-test-klog-prefix": "A90v2100",
        "--wifi-test-disable": "/cache/native-init-wifi-test-boot-v2100.disable",
        "--wifi-test-log": "/cache/native-init-wifi-test-boot-v2100.log",
        "--wifi-test-summary": "/cache/native-init-wifi-test-boot-v2100.summary",
        "--wifi-test-helper-result": "/cache/native-init-wifi-test-boot-v2100-helper.result",
        "--wifi-test-pid": "/cache/native-init-wifi-test-boot-v2100.pid",
        "--wifi-test-watcher-pid": "/cache/native-init-wifi-test-boot-v2100-supervisor.pid",
        "--wifi-test-property-root": REMOTE_PROPERTY_ROOT,
    }
    for key, value in replacements.items():
        prev2097.prev2095.prev2082.prev2080.prev2058.prev2038.prev2008.prev2006.set_arg(args, key, value)
    base.DEFAULT_ARGS = args


def render_report(manifest: dict[str, object]) -> str:
    wifi = manifest["wifi_test"]
    property_runtime = manifest["cnss_nonlog_property_runtime"]
    check_lines = [
        f"- `{item['name']}`: `{item['actual']}` in `{item['context']}`"
        for item in property_runtime["checks"]
    ]
    return "\n".join([
        "# Native Init V2100 TFTP Persist-RFS Auto-Dir Parity Source Build",
        "",
        "## Summary",
        "",
        "- Cycle: `V2100`",
        "- Type: source/build-only follow-up to V2099, fixing the remaining `tftp_server` auto-dir EACCES target after tombstone parity cleared.",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: helper v411 keeps the V2097 light internal-modem route and adds only namespace-local persist-RFS auto-dir targets `/mnt/vendor/persist/rfs/{shared,msm/mpss,msm/adsp}` before stock `tftp_server` starts. This does not fabricate `ota_firewall/ruleset`, ptrace `tftp_server`, retry macloader, send QMI, use DIAG, use Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, or touch SDX50M/eSoC/PCIe/GDSC/PMIC/GPIO.",
        "- Manifest: `tmp/wifi/v2100-tftp-persist-rfs-autodir-parity-test-boot/manifest.json`",
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
        "- Kept: V2097 route, readonly/readwrite RFS bridges, vendor-owned tombstone dirs, `tftp_server` logdw sink, focused PerMgr/WLFW summaries, post-BDF surface summary, and long lower-window hold.",
        "- Added: namespace-local persist-RFS auto-dir targets only; `sda29` remains read-only.",
        "- Excluded: `ota_firewall/ruleset` fabrication, macloader retry, `boot_wlan`/`qcwlanstate` write, module load/unload, driver bind/unbind, DIAG, boot-time QRTR matrix, rild/cnss/pm-service strace, `tftp_server` ptrace, AP QMI send, `/dev/subsys_esoc0`, eSoC notify/BOOT_DONE, PCI rescan/bind, platform unbind, PMIC/GPIO/GDSC/regulator writes, forced RC1/case, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, and firmware/partition writes.",
        "",
        "## Property Runtime",
        "",
        *check_lines,
        "",
        "## Safety Scope",
        "",
        "This build script performed host-side source/build work only. The live handoff should decide whether clearing the remaining persist-RFS startup auto-dir failures changes the native `server_check -> ota_firewall -> wlanmdsp` producer branch.",
        "",
    ])


def main() -> int:
    configure_base()
    base = prev2097.prev2095.prev2082.prev2080.prev2058.prev2038.prev2008.prev2006.build_base_module()
    base.base.EXPECTED_HELPER_MARKER = EXPECTED_HELPER_MARKER
    base.base.EXPECTED_HELPER_SHA256 = EXPECTED_HELPER_SHA256
    prev2097.prev2095.prev2082.prev2080.prev2058.prev2038.patch_helper_builder(base)
    base.render_report = render_report
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())

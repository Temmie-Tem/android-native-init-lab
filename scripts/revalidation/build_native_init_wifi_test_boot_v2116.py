#!/usr/bin/env python3
"""Build V2116 native dual-RFS leaf-precreate plus Android lower-companion identities."""

from __future__ import annotations

from pathlib import Path

import build_native_init_wifi_test_boot_v2112 as prev2112


REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v2116-dual-rfs-leaf-android-identity-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v2116/dev/__properties__"
EXPECTED_HELPER_MARKER = "a90_android_execns_probe v417"
EXPECTED_HELPER_SHA256 = "bf5f06779064be53321b27dc97773c0f479cf8ebd0a00bb1b5ea96d7934c59ce"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V2116_DUAL_RFS_LEAF_ANDROID_IDENTITY_SOURCE_BUILD_2026-06-05.md"
)
HELPER_FLAGS = (
    *prev2112.HELPER_FLAGS,
    "-DA90_WIFI_TEST_BOOT_ANDROID_RMT_TFTP_IDENTITY=1",
)


def configure_base() -> None:
    prev2112.OUT_DIR = OUT_DIR
    prev2112.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev2112.REPORT_PATH = REPORT_PATH
    prev2112.EXPECTED_HELPER_MARKER = EXPECTED_HELPER_MARKER
    prev2112.EXPECTED_HELPER_SHA256 = EXPECTED_HELPER_SHA256
    prev2112.HELPER_FLAGS = HELPER_FLAGS
    prev2112.configure_base()

    base = prev2112.prev2108.prev2106.prev2102.prev2100.prev2097.prev2095.prev2082.prev2080.prev2058.prev2038.prev2008.prev2006.build_base_module()
    args = list(base.DEFAULT_ARGS)
    replacements = {
        "--cycle": "V2116",
        "--decision": "v2116-dual-rfs-leaf-android-identity-source-build-pass",
        "--cycle-label": "v2116",
        "--init-version": "0.9.233",
        "--init-build": "v2116-dual-rfs-leaf-android-identity",
        "--out-dir": str(OUT_DIR),
        "--init-binary": str(OUT_DIR / "init_v2116_dual_rfs_leaf_android_identity"),
        "--helper-binary": str(OUT_DIR / "a90_android_execns_probe_v417_dual_rfs_leaf_android_identity"),
        "--ramdisk-cpio": str(OUT_DIR / "ramdisk_v2116_dual_rfs_leaf_android_identity.cpio"),
        "--boot-image": str(OUT_DIR / "boot_linux_v2116_dual_rfs_leaf_android_identity.img"),
        "--wifi-test-klog-prefix": "A90v2116",
        "--wifi-test-disable": "/cache/native-init-wifi-test-boot-v2116.disable",
        "--wifi-test-log": "/cache/native-init-wifi-test-boot-v2116.log",
        "--wifi-test-summary": "/cache/native-init-wifi-test-boot-v2116.summary",
        "--wifi-test-helper-result": "/cache/native-init-wifi-test-boot-v2116-helper.result",
        "--wifi-test-pid": "/cache/native-init-wifi-test-boot-v2116.pid",
        "--wifi-test-watcher-pid": "/cache/native-init-wifi-test-boot-v2116-supervisor.pid",
        "--wifi-test-property-root": REMOTE_PROPERTY_ROOT,
    }
    for key, value in replacements.items():
        prev2112.prev2108.prev2106.prev2102.prev2100.prev2097.prev2095.prev2082.prev2080.prev2058.prev2038.prev2008.prev2006.set_arg(args, key, value)
    base.DEFAULT_ARGS = args


def render_report(manifest: dict[str, object]) -> str:
    wifi = manifest["wifi_test"]
    property_runtime = manifest["cnss_nonlog_property_runtime"]
    check_lines = [
        f"- `{item['name']}`: `{item['actual']}` in `{item['context']}`"
        for item in property_runtime["checks"]
    ]
    return "\n".join([
        "# Native Init V2116 Dual-RFS Leaf Android Identity Source Build",
        "",
        "## Summary",
        "",
        "- Cycle: `V2116`",
        "- Type: source/build-only integration of V2113 dual-RFS leaf route with Android-observed `rmt_storage` and `tftp_server` runtime identities.",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: helper v417 keeps the light V2113 bridge route and changes only the lower-companion identity contracts behind `A90_WIFI_TEST_BOOT_ANDROID_RMT_TFTP_IDENTITY=1`: `rmt_storage` becomes uid `9999` gid `1000` groups `1000,3010`, and `tftp_server` becomes uid/gid `2903` groups `1000,2903,2904,3010`; both retain only `CAP_NET_BIND_SERVICE` and `CAP_BLOCK_SUSPEND` as ambient caps.",
        "- Manifest: `tmp/wifi/v2116-dual-rfs-leaf-android-identity-test-boot/manifest.json`",
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
        "- Kept: V2113 exact Android dual-RFS WLAN image path, readwrite tmpfs, persist-RFS leaf precreate, process namespace audit, PerMgr/WLFW focused summaries, and long lower-window hold.",
        "- Added: Android-runtime lower-companion identities for only `rmt_storage` and `tftp_server`, matching the V570/V1753 observed uid/gid/group/capability contract.",
        "- Excluded: DIAG, boot-time QRTR matrix, rild/cnss/pm-service strace, `tftp_server` ptrace, AP QMI send, OTA ruleset fabrication, macloader retry, `boot_wlan`/`qcwlanstate` writes, `/dev/subsys_esoc0`, eSoC notify/BOOT_DONE, PCI rescan/bind, platform unbind, PMIC/GPIO/GDSC/regulator writes, forced RC1/case, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, and firmware/partition writes.",
        "",
        "## Branch",
        "",
        "- If Android-runtime identities move native into the Android-order TFTP branch (`server_check`/`ota_firewall`/`wlanmdsp`) or FW-ready/`wlan0`, chase the documented cascade next.",
        "- If identities apply but the route regresses before `wlan_pd UP`, or still shows only post-UP `server_check` or mcfg, the lower-companion identity mismatch is falsified in the current bridge route.",
        "- If artifact validation fails, do not run the live handoff.",
        "",
        "## Property Runtime",
        "",
        *check_lines,
        "",
        "## Safety Scope",
        "",
        "This build script performed host-side source/build work only. It did not issue live device commands, flash, reboot, run Wi-Fi HAL, scan/connect, use credentials, configure DHCP/routes, perform external ping, write `/dev/wlan`, write `qcwlanstate`, open `/dev/subsys_esoc0`, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE` spoof, run PCI rescan/platform bind-unbind, use DIAG, ptrace `tftp_server`, send AP QMI payloads, or write firmware/boot/device partitions.",
        "",
    ])


def main() -> int:
    configure_base()
    base = prev2112.prev2108.prev2106.prev2102.prev2100.prev2097.prev2095.prev2082.prev2080.prev2058.prev2038.prev2008.prev2006.build_base_module()
    base.base.EXPECTED_HELPER_MARKER = EXPECTED_HELPER_MARKER
    base.base.EXPECTED_HELPER_SHA256 = EXPECTED_HELPER_SHA256
    prev2112.prev2108.prev2106.prev2102.prev2100.prev2097.prev2095.prev2082.prev2080.prev2058.prev2038.patch_helper_builder(base)
    base.render_report = render_report
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())

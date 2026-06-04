#!/usr/bin/env python3
"""Build V2095 native TFTP tombstone-RFS parity discriminator test boot."""

from __future__ import annotations

from pathlib import Path

import build_native_init_wifi_test_boot_v2082 as prev2082


REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v2095-tftp-tombstone-rfs-parity-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v2095/dev/__properties__"
EXPECTED_HELPER_MARKER = "a90_android_execns_probe v409"
EXPECTED_HELPER_SHA256 = "4740f435dabb54a046af205aad8dfef2b3e0d125a5b70c8787019fbf464b42d5"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V2095_TFTP_TOMBSTONE_RFS_PARITY_SOURCE_BUILD_2026-06-05.md"
)
HELPER_FLAGS = (
    *prev2082.HELPER_FLAGS,
    "-DA90_WIFI_TEST_BOOT_TFTP_TOMBSTONE_RFS_TMPFS=1",
)


def configure_base() -> None:
    prev2082.OUT_DIR = OUT_DIR
    prev2082.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev2082.REPORT_PATH = REPORT_PATH
    prev2082.EXPECTED_HELPER_MARKER = EXPECTED_HELPER_MARKER
    prev2082.EXPECTED_HELPER_SHA256 = EXPECTED_HELPER_SHA256
    prev2082.HELPER_FLAGS = HELPER_FLAGS
    prev2082.configure_base()

    base = prev2082.prev2080.prev2058.prev2038.prev2008.prev2006.build_base_module()
    args = list(base.DEFAULT_ARGS)
    replacements = {
        "--cycle": "V2095",
        "--decision": "v2095-tftp-tombstone-rfs-parity-source-build-pass",
        "--cycle-label": "v2095",
        "--init-version": "0.9.225",
        "--init-build": "v2095-tftp-tombstone-rfs-parity",
        "--out-dir": str(OUT_DIR),
        "--init-binary": str(OUT_DIR / "init_v2095_tftp_tombstone_rfs_parity"),
        "--helper-binary": str(OUT_DIR / "a90_android_execns_probe_v409_tftp_tombstone_rfs_parity"),
        "--ramdisk-cpio": str(OUT_DIR / "ramdisk_v2095_tftp_tombstone_rfs_parity.cpio"),
        "--boot-image": str(OUT_DIR / "boot_linux_v2095_tftp_tombstone_rfs_parity.img"),
        "--wifi-test-klog-prefix": "A90v2095",
        "--wifi-test-disable": "/cache/native-init-wifi-test-boot-v2095.disable",
        "--wifi-test-log": "/cache/native-init-wifi-test-boot-v2095.log",
        "--wifi-test-summary": "/cache/native-init-wifi-test-boot-v2095.summary",
        "--wifi-test-helper-result": "/cache/native-init-wifi-test-boot-v2095-helper.result",
        "--wifi-test-pid": "/cache/native-init-wifi-test-boot-v2095.pid",
        "--wifi-test-watcher-pid": "/cache/native-init-wifi-test-boot-v2095-supervisor.pid",
        "--wifi-test-property-root": REMOTE_PROPERTY_ROOT,
    }
    for key, value in replacements.items():
        prev2082.prev2080.prev2058.prev2038.prev2008.prev2006.set_arg(args, key, value)
    base.DEFAULT_ARGS = args


def render_report(manifest: dict[str, object]) -> str:
    wifi = manifest["wifi_test"]
    property_runtime = manifest["cnss_nonlog_property_runtime"]
    check_lines = [
        f"- `{item['name']}`: `{item['actual']}` in `{item['context']}`"
        for item in property_runtime["checks"]
    ]
    return "\n".join([
        "# Native Init V2095 TFTP Tombstone-RFS Parity Source Build",
        "",
        "## Summary",
        "",
        "- Cycle: `V2095`",
        "- Type: source/build-only light internal-modem route with one namespace-local TFTP tombstone-RFS parity bridge.",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: helper v409 keeps the V2082 light route and adds only private-root `/data/vendor/tombstones/rfs/{modem,lpass}` directories so `tftp_server` no longer fails its Android tombstone auto-dir setup before the lower-window vote. It does not create `ota_firewall/ruleset`, does not ptrace `tftp_server`, and does not add macloader, AP QMI captures, DIAG, QRTR matrix, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, or off-path SDX50M/eSoC/PCIe/GDSC/PMIC/GPIO actions.",
        "- Manifest: `tmp/wifi/v2095-tftp-tombstone-rfs-parity-test-boot/manifest.json`",
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
        "- Kept: clean-DSP companion, service managers, `pm-service`, `/dev/subsys_modem` holder, `cnss_diag`, stock `cnss-daemon`, `rmt_storage`, `tftp_server`, `pd-mapper`, Android-parity RFS readonly/readwrite bridges, cap/BDF/cal probes, PerMgr compact summary, late `msg_id=0x21` compact summary, read-only ICNSS/QCACLD post-BDF summary, and long lower-window hold.",
        "- Added: namespace-local private-root `/data/vendor/tombstones/rfs/modem` and `/data/vendor/tombstones/rfs/lpass` directories only; `sda29` remains read-only and the helper reports `ota_ruleset_created=0`.",
        "- Excluded: macloader retry, `boot_wlan`/`qcwlanstate` write, module load/unload, driver bind/unbind, DIAG, boot-time QRTR matrix, rild/cnss/pm-service strace, `tftp_server` ptrace, AP QMI send, private SDX50M route, `/dev/subsys_esoc0`, eSoC notify/BOOT_DONE, PCI rescan/bind, platform unbind, PMIC/GPIO/GDSC/regulator writes, forced RC1/case, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, and firmware/partition writes.",
        "",
        "## Property Runtime",
        "",
        *check_lines,
        "",
        "## Safety Scope",
        "",
        "This build script performed host-side source/build work only. The eventual live handoff remains rollbackable and should classify only whether removing the `tftp_server` tombstone auto-dir failure changes the early `server_check -> ota_firewall -> wlanmdsp` branch.",
        "",
    ])


def main() -> int:
    configure_base()
    base = prev2082.prev2080.prev2058.prev2038.prev2008.prev2006.build_base_module()
    base.base.EXPECTED_HELPER_MARKER = EXPECTED_HELPER_MARKER
    base.base.EXPECTED_HELPER_SHA256 = EXPECTED_HELPER_SHA256
    prev2082.prev2080.prev2058.prev2038.patch_helper_builder(base)
    base.render_report = render_report
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())

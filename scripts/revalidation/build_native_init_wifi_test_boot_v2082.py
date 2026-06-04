#!/usr/bin/env python3
"""Build V2082 native ICNSS/QCACLD post-BDF focused test boot."""

from __future__ import annotations

from pathlib import Path

import build_native_init_wifi_test_boot_v2080 as prev2080


REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v2082-icnss-qcacld-post-bdf-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v2082/dev/__properties__"
EXPECTED_HELPER_MARKER = "a90_android_execns_probe v404"
EXPECTED_HELPER_SHA256 = "99263051954aeaa96cb2c8f5eb40cb68b78ec254e8913210a61cd721d3a35d06"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V2082_ICNSS_QCACLD_POST_BDF_SOURCE_BUILD_2026-06-05.md"
)
HELPER_FLAGS = (
    *prev2080.HELPER_FLAGS,
    "-DA90_WIFI_TEST_BOOT_ICNSS_QCACLD_POST_BDF_FOCUSED_SUMMARY=1",
)


def configure_base() -> None:
    prev2080.OUT_DIR = OUT_DIR
    prev2080.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev2080.REPORT_PATH = REPORT_PATH
    prev2080.EXPECTED_HELPER_MARKER = EXPECTED_HELPER_MARKER
    prev2080.EXPECTED_HELPER_SHA256 = EXPECTED_HELPER_SHA256
    prev2080.HELPER_FLAGS = HELPER_FLAGS
    prev2080.configure_base()

    base = prev2080.prev2058.prev2038.prev2008.prev2006.build_base_module()
    args = list(base.DEFAULT_ARGS)
    replacements = {
        "--cycle": "V2082",
        "--decision": "v2082-icnss-qcacld-post-bdf-source-build-pass",
        "--cycle-label": "v2082",
        "--init-version": "0.9.219",
        "--init-build": "v2082-icnss-qcacld-post-bdf",
        "--out-dir": str(OUT_DIR),
        "--init-binary": str(OUT_DIR / "init_v2082_icnss_qcacld_post_bdf"),
        "--helper-binary": str(OUT_DIR / "a90_android_execns_probe_v404_icnss_qcacld_post_bdf"),
        "--ramdisk-cpio": str(OUT_DIR / "ramdisk_v2082_icnss_qcacld_post_bdf.cpio"),
        "--boot-image": str(OUT_DIR / "boot_linux_v2082_icnss_qcacld_post_bdf.img"),
        "--wifi-test-klog-prefix": "A90v2082",
        "--wifi-test-disable": "/cache/native-init-wifi-test-boot-v2082.disable",
        "--wifi-test-log": "/cache/native-init-wifi-test-boot-v2082.log",
        "--wifi-test-summary": "/cache/native-init-wifi-test-boot-v2082.summary",
        "--wifi-test-helper-result": "/cache/native-init-wifi-test-boot-v2082-helper.result",
        "--wifi-test-pid": "/cache/native-init-wifi-test-boot-v2082.pid",
        "--wifi-test-watcher-pid": "/cache/native-init-wifi-test-boot-v2082-supervisor.pid",
        "--wifi-test-property-root": REMOTE_PROPERTY_ROOT,
    }
    for key, value in replacements.items():
        prev2080.prev2058.prev2038.prev2008.prev2006.set_arg(args, key, value)
    base.DEFAULT_ARGS = args


def render_report(manifest: dict[str, object]) -> str:
    wifi = manifest["wifi_test"]
    property_runtime = manifest["cnss_nonlog_property_runtime"]
    check_lines = [
        f"- `{item['name']}`: `{item['actual']}` in `{item['context']}`"
        for item in property_runtime["checks"]
    ]
    return "\n".join([
        "# Native Init V2082 ICNSS QCACLD Post-BDF Source Build",
        "",
        "## Summary",
        "",
        "- Cycle: `V2082`",
        "- Type: source/build-only no-DIAG native route with compact post-BDF ICNSS/QCACLD surface summary emitted before verbose output truncation",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: helper v404 keeps the V2080 light internal-modem route and adds only read-only sysfs/devnode/process surface state for the post-BDF kernel consumer edge; no `boot_wlan`/`qcwlanstate` write, module load/unload, bind/unbind, DIAG, strace, QRTR matrix, QMI send, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping.",
        "- Manifest: `tmp/wifi/v2082-icnss-qcacld-post-bdf-test-boot/manifest.json`",
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
        "- Kept: clean-DSP companion, service managers, `pm-service`, `/dev/subsys_modem` holder, `cnss_diag`, stock `cnss-daemon`, `rmt_storage`, `tftp_server`, `pd-mapper`, Android-parity RFS bridges, cap/BDF/cal probes, post-cal WLFW indication probes, PerMgr compact summary, late `msg_id=0x21` compact summary, read-only ICNSS/QCACLD post-BDF summary, and long lower-window hold.",
        "- Excluded: `boot_wlan` write, `qcwlanstate` write, module load/unload, driver bind/unbind, DIAG ioctl/write/log-mask, passive DIAG, active DIAG, boot-time QRTR matrix, rild/cnss/pm-service strace, `tftp_server` ptrace, private SDX50M route, `/dev/subsys_esoc0` open, eSoC notify/BOOT_DONE, PCI rescan/bind, platform unbind, PMIC/GPIO/GDSC/regulator writes, forced RC1/case, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, and firmware partition writes.",
        "",
        "## Property Runtime",
        "",
        *check_lines,
        "",
        "## Safety Scope",
        "",
        "This build script performed host-side source/build work only. It did not issue live device commands, flash, reboot, scan/connect, use credentials, configure DHCP/routes, perform external ping, open `/dev/subsys_esoc0`, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE` spoof, run PCI rescan/platform bind-unbind, write `boot_wlan`/`qcwlanstate`, load/unload modules, or write firmware/boot/device partitions.",
        "",
    ])


def main() -> int:
    configure_base()
    base = prev2080.prev2058.prev2038.prev2008.prev2006.build_base_module()
    base.base.EXPECTED_HELPER_MARKER = EXPECTED_HELPER_MARKER
    base.base.EXPECTED_HELPER_SHA256 = EXPECTED_HELPER_SHA256
    prev2080.prev2058.prev2038.patch_helper_builder(base)
    base.render_report = render_report
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())

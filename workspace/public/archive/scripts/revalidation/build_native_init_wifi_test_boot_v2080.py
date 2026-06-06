#!/usr/bin/env python3
"""Build V2080 native WLFW late-msg21 focused test boot."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import build_native_init_wifi_test_boot_v2058 as prev2058


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v2080-wlfw-late-msg21-native-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v2080/dev/__properties__"
EXPECTED_HELPER_MARKER = "a90_android_execns_probe v403"
EXPECTED_HELPER_SHA256 = "2f6a3fab0842282a7f1f5a76ef55be25d1413ee89daf0adc0cf79bf4204cd034"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V2080_WLFW_LATE_MSG21_NATIVE_SOURCE_BUILD_2026-06-05.md"
)
HELPER_FLAGS = (
    *prev2058.HELPER_FLAGS,
    "-DA90_WIFI_TEST_BOOT_WLFW_LATE_MSG21_FOCUSED_SUMMARY=1",
)


def configure_base() -> None:
    prev2058.OUT_DIR = OUT_DIR
    prev2058.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev2058.REPORT_PATH = REPORT_PATH
    prev2058.EXPECTED_HELPER_MARKER = EXPECTED_HELPER_MARKER
    prev2058.EXPECTED_HELPER_SHA256 = EXPECTED_HELPER_SHA256
    prev2058.HELPER_FLAGS = HELPER_FLAGS
    prev2058.configure_base()

    base = prev2058.prev2038.prev2008.prev2006.build_base_module()
    args = list(base.DEFAULT_ARGS)
    replacements = {
        "--cycle": "V2080",
        "--decision": "v2080-wlfw-late-msg21-native-source-build-pass",
        "--cycle-label": "v2080",
        "--init-version": "0.9.218",
        "--init-build": "v2080-wlfw-late-msg21-native",
        "--out-dir": str(OUT_DIR),
        "--init-binary": str(OUT_DIR / "init_v2080_wlfw_late_msg21_native"),
        "--helper-binary": str(OUT_DIR / "a90_android_execns_probe_v403_wlfw_late_msg21_native"),
        "--ramdisk-cpio": str(OUT_DIR / "ramdisk_v2080_wlfw_late_msg21_native.cpio"),
        "--boot-image": str(OUT_DIR / "boot_linux_v2080_wlfw_late_msg21_native.img"),
        "--wifi-test-klog-prefix": "A90v2080",
        "--wifi-test-disable": "/cache/native-init-wifi-test-boot-v2080.disable",
        "--wifi-test-log": "/cache/native-init-wifi-test-boot-v2080.log",
        "--wifi-test-summary": "/cache/native-init-wifi-test-boot-v2080.summary",
        "--wifi-test-helper-result": "/cache/native-init-wifi-test-boot-v2080-helper.result",
        "--wifi-test-pid": "/cache/native-init-wifi-test-boot-v2080.pid",
        "--wifi-test-watcher-pid": "/cache/native-init-wifi-test-boot-v2080-supervisor.pid",
        "--wifi-test-property-root": REMOTE_PROPERTY_ROOT,
    }
    for key, value in replacements.items():
        prev2058.prev2038.prev2008.prev2006.set_arg(args, key, value)
    base.DEFAULT_ARGS = args


def render_report(manifest: dict[str, object]) -> str:
    wifi = manifest["wifi_test"]
    property_runtime = manifest["cnss_nonlog_property_runtime"]
    check_lines = [
        f"- `{item['name']}`: `{item['actual']}` in `{item['context']}`"
        for item in property_runtime["checks"]
    ]
    return "\n".join([
        "# Native Init V2080 WLFW Late Msg21 Native Source Build",
        "",
        "## Summary",
        "",
        "- Cycle: `V2080`",
        "- Type: source/build-only no-DIAG native route with compact WLFW late `msg_id=0x21` summary emitted before verbose trace output truncation",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: helper v403 keeps the V2058 light internal-modem route and adds only a compact `wlfw_late_msg21_focused` summary over existing cnss-daemon tracefs uprobes; no DIAG, strace, QRTR matrix, QMI send, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping.",
        "- Manifest: `tmp/wifi/v2080-wlfw-late-msg21-native-test-boot/manifest.json`",
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
        "- Kept: clean-DSP companion, service managers, `pm-service`, `/dev/subsys_modem` holder, `cnss_diag`, stock `cnss-daemon`, `rmt_storage`, `tftp_server`, `pd-mapper`, Android-parity RFS bridges, cap/BDF/cal probes, post-cal WLFW indication probes, PerMgr compact summary, and long lower-window hold.",
        "- Excluded: DIAG ioctl/write/log-mask, passive DIAG, active DIAG, boot-time QRTR matrix, rild/cnss/pm-service strace, `tftp_server` ptrace, private SDX50M route, `/dev/subsys_esoc0` open, eSoC notify/BOOT_DONE, PCI rescan/bind, platform unbind, PMIC/GPIO/GDSC/regulator writes, forced RC1/case, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, and firmware partition writes.",
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
    configure_base()
    base = prev2058.prev2038.prev2008.prev2006.build_base_module()
    base.base.EXPECTED_HELPER_MARKER = EXPECTED_HELPER_MARKER
    base.base.EXPECTED_HELPER_SHA256 = EXPECTED_HELPER_SHA256
    prev2058.prev2038.patch_helper_builder(base)
    base.render_report = render_report
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())

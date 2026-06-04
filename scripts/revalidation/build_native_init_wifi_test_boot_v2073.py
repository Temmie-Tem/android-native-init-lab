#!/usr/bin/env python3
"""Build V2073 native WLAN-PD memory-device DIAG session-mask test boot."""

from __future__ import annotations

from pathlib import Path

import build_native_init_wifi_test_boot_v2071 as prev2071


REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v2073-diag-wlan-pd-memory-session-mask-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v2073/dev/__properties__"
EXPECTED_HELPER_MARKER = "a90_android_execns_probe v400"
EXPECTED_HELPER_SHA256 = "4cb7f6f60bc1408edd09b30cdb500c39ee20502447ac7ea20c39d56ca1a2d682"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V2073_DIAG_WLAN_PD_MEMORY_SESSION_MASK_SOURCE_BUILD_2026-06-04.md"
)
HELPER_FLAGS = (
    *prev2071.HELPER_FLAGS,
    "-DA90_WIFI_TEST_BOOT_DIAG_WLAN_PD_MEMORY_SESSION_MASK_PROBE=1",
)


def configure_base() -> None:
    prev2071.OUT_DIR = OUT_DIR
    prev2071.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev2071.REPORT_PATH = REPORT_PATH
    prev2071.EXPECTED_HELPER_MARKER = EXPECTED_HELPER_MARKER
    prev2071.EXPECTED_HELPER_SHA256 = EXPECTED_HELPER_SHA256
    prev2071.HELPER_FLAGS = HELPER_FLAGS
    prev2071.configure_base()

    base = prev2071.prev2068.prev2038.prev2008.prev2006.build_base_module()
    args = list(base.DEFAULT_ARGS)
    replacements = {
        "--cycle": "V2073",
        "--decision": "v2073-diag-wlan-pd-memory-session-mask-source-build-pass",
        "--cycle-label": "v2073",
        "--init-version": "0.9.215",
        "--init-build": "v2073-diag-wlan-pd-memory-session-mask",
        "--out-dir": str(OUT_DIR),
        "--init-binary": str(OUT_DIR / "init_v2073_diag_wlan_pd_memory_session_mask"),
        "--helper-binary": str(OUT_DIR / "a90_android_execns_probe_v400_diag_wlan_pd_memory_session_mask"),
        "--ramdisk-cpio": str(OUT_DIR / "ramdisk_v2073_diag_wlan_pd_memory_session_mask.cpio"),
        "--boot-image": str(OUT_DIR / "boot_linux_v2073_diag_wlan_pd_memory_session_mask.img"),
        "--wifi-test-klog-prefix": "A90v2073",
        "--wifi-test-disable": "/cache/native-init-wifi-test-boot-v2073.disable",
        "--wifi-test-log": "/cache/native-init-wifi-test-boot-v2073.log",
        "--wifi-test-summary": "/cache/native-init-wifi-test-boot-v2073.summary",
        "--wifi-test-helper-result": "/cache/native-init-wifi-test-boot-v2073-helper.result",
        "--wifi-test-pid": "/cache/native-init-wifi-test-boot-v2073.pid",
        "--wifi-test-watcher-pid": "/cache/native-init-wifi-test-boot-v2073-supervisor.pid",
        "--wifi-test-property-root": REMOTE_PROPERTY_ROOT,
    }
    for key, value in replacements.items():
        prev2071.prev2068.prev2038.prev2008.prev2006.set_arg(args, key, value)
    base.DEFAULT_ARGS = args


def render_report(manifest: dict[str, object]) -> str:
    wifi = manifest["wifi_test"]
    property_runtime = manifest["cnss_nonlog_property_runtime"]
    check_lines = [
        f"- `{item['name']}`: `{item['actual']}` in `{item['context']}`"
        for item in property_runtime["checks"]
    ]
    return "\n".join([
        "# Native Init V2073 DIAG WLAN-PD Memory Session-Mask Source Build",
        "",
        "## Summary",
        "",
        "- Cycle: `V2073`",
        "- Type: source/build-only rollbackable internal-modem route with V2071 WLAN-PD memory-device mode plus session-scoped regular DIAG masks",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: helper v400 keeps the V2071 route and, after `DIAG_IOCTL_SWITCH_LOGGING` succeeds for `DIAG_CON_UPD_WLAN` in `MEMORY_DEVICE_MODE`, disables HDLC only for that helper-owned memory session, writes `USER_SPACE_DATA_TYPE` normal app masks for exactly three WLAN log codes and three WLAN event IDs, holds them through the lower window, clears them, re-enables HDLC, and closes the fd.",
        "- Manifest: `tmp/wifi/v2073-diag-wlan-pd-memory-session-mask-test-boot/manifest.json`",
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
        "- Observer: passive private `/dev/socket/logdw`; compact PerMgr register/vote uprobes; private `/dev/diag` DCI support/register/read/deinit plus bounded WLAN target masks; borrowed-fd WLAN-PD memory-device session; session-scoped regular WLAN log/event masks.",
        "- Regular mask scope: `USER_SPACE_DATA_TYPE`, session-local HDLC disabled, `LOG_WLAN_PKT_LOG_INFO_C` (`0x18e0`), `LOG_WLAN_COLD_BOOT_CAL_DATA_C` (`0x1a18`), `LOG_WLAN_DP_PROTO_PKT_INFO_C` (`0x1a1e`), `EVENT_WLAN_BRINGUP_STATUS` (`0x0680`), `EVENT_WLAN_LOG_COMPLETE` (`0x0aa7`), and `EVENT_WLAN_STATUS_V2` (`0x0ab3`).",
        "- Excluded: USB/PCIE/global DIAG restore, broad DIAG masks, DCI stream config, passive DIAG replay, boot-time QRTR matrix, rild/cnss/pm-service multi-strace, `tftp_server` ptrace, private SDX50M route, `/dev/subsys_esoc0` open, eSoC notify/BOOT_DONE, PCI rescan/bind, platform unbind, PMIC/GPIO/GDSC/regulator writes, forced RC1/case, restart-PD request, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, and firmware partition writes.",
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
    base = prev2071.prev2068.prev2038.prev2008.prev2006.build_base_module()
    base.base.EXPECTED_HELPER_MARKER = EXPECTED_HELPER_MARKER
    base.base.EXPECTED_HELPER_SHA256 = EXPECTED_HELPER_SHA256
    prev2071.prev2068.prev2038.patch_helper_builder(base)
    base.render_report = render_report
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())

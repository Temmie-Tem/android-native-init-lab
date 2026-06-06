#!/usr/bin/env python3
"""Build V2068 native bounded DIAG DCI WLAN target-mask test boot."""

from __future__ import annotations

from pathlib import Path

import build_native_init_wifi_test_boot_v2038 as prev2038


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v2068-dci-wlan-target-mask-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v2068/dev/__properties__"
EXPECTED_HELPER_MARKER = "a90_android_execns_probe v398"
EXPECTED_HELPER_SHA256 = "cb62d077c41c9e0fdd63f83609f3cd549fa234cc74d136bcf57608b3509fee96"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V2068_DCI_WLAN_TARGET_MASK_SOURCE_BUILD_2026-06-04.md"
)
HELPER_FLAGS = (
    "-DA90_WIFI_TEST_BOOT_TFTP_LOGDW_SINK=1",
    "-DA90_WIFI_TEST_BOOT_TFTP_MCFG_READBACK=1",
    "-DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_TMPFS=1",
    "-DA90_WIFI_TEST_BOOT_TFTP_LOGDW_ORDER_TIMESTAMPS=1",
    "-DA90_WIFI_TEST_BOOT_TFTP_READY_BEFORE_WLFW_VOTE=1",
    "-DA90_WIFI_TEST_BOOT_TFTP_READWRITE_TRANSITION_SAMPLER=1",
    "-DA90_WIFI_TEST_BOOT_PERMGR_VOTE_FOCUSED_SUMMARY=1",
    "-DA90_WIFI_TEST_BOOT_DIAG_DCI_REGISTER_READ_PROBE=1",
    "-DA90_WIFI_TEST_BOOT_DIAG_DCI_WLAN_TARGET_MASK_PROBE=1",
)


def configure_base() -> None:
    prev2038.OUT_DIR = OUT_DIR
    prev2038.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev2038.REPORT_PATH = REPORT_PATH
    prev2038.EXPECTED_HELPER_MARKER = EXPECTED_HELPER_MARKER
    prev2038.EXPECTED_HELPER_SHA256 = EXPECTED_HELPER_SHA256
    prev2038.HELPER_FLAGS = HELPER_FLAGS
    prev2038.configure_base()

    base = prev2038.prev2008.prev2006.build_base_module()
    args = list(base.DEFAULT_ARGS)
    replacements = {
        "--cycle": "V2068",
        "--decision": "v2068-dci-wlan-target-mask-source-build-pass",
        "--cycle-label": "v2068",
        "--init-version": "0.9.213",
        "--init-build": "v2068-dci-wlan-target-mask",
        "--out-dir": str(OUT_DIR),
        "--init-binary": str(OUT_DIR / "init_v2068_dci_wlan_target_mask"),
        "--helper-binary": str(OUT_DIR / "a90_android_execns_probe_v398_dci_wlan_target_mask"),
        "--ramdisk-cpio": str(OUT_DIR / "ramdisk_v2068_dci_wlan_target_mask.cpio"),
        "--boot-image": str(OUT_DIR / "boot_linux_v2068_dci_wlan_target_mask.img"),
        "--wifi-test-klog-prefix": "A90v2068",
        "--wifi-test-disable": "/cache/native-init-wifi-test-boot-v2068.disable",
        "--wifi-test-log": "/cache/native-init-wifi-test-boot-v2068.log",
        "--wifi-test-summary": "/cache/native-init-wifi-test-boot-v2068.summary",
        "--wifi-test-helper-result": "/cache/native-init-wifi-test-boot-v2068-helper.result",
        "--wifi-test-pid": "/cache/native-init-wifi-test-boot-v2068.pid",
        "--wifi-test-watcher-pid": "/cache/native-init-wifi-test-boot-v2068-supervisor.pid",
        "--wifi-test-property-root": REMOTE_PROPERTY_ROOT,
    }
    for key, value in replacements.items():
        prev2038.prev2008.prev2006.set_arg(args, key, value)
    base.DEFAULT_ARGS = args


def render_report(manifest: dict[str, object]) -> str:
    wifi = manifest["wifi_test"]
    property_runtime = manifest["cnss_nonlog_property_runtime"]
    check_lines = [
        f"- `{item['name']}`: `{item['actual']}` in `{item['context']}`"
        for item in property_runtime["checks"]
    ]
    return "\n".join([
        "# Native Init V2068 DIAG DCI WLAN Target-Mask Source Build",
        "",
        "## Summary",
        "",
        "- Cycle: `V2068`",
        "- Type: source/build-only rollbackable internal-modem route with V2059 PerMgr success retained and bounded `/dev/diag` DCI WLAN log/event target masks",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: helper v398 keeps the V2058 readonly/readwrite RFS bridges, TFTP order sink, pre-vote readiness gate, compact PerMgr summary, and private-node DCI support/register/read/deinit probe, then arms exactly three WLAN log codes and three WLAN event IDs through the lower window and clears them during cleanup. It does not call `DIAG_IOCTL_SWITCH_LOGGING`, configure DCI streams, set broad masks, send QMI, ptrace, or run AP-side strace/QRTR matrices.",
        "- Manifest: `tmp/wifi/v2068-dci-wlan-target-mask-test-boot/manifest.json`",
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
        "- Observer: passive private `/dev/socket/logdw`; compact PerMgr register/vote uprobes; private `/dev/diag` DCI support/register/read/deinit plus bounded WLAN target log/event masks held until cleanup.",
        "- Target logs: `LOG_WLAN_PKT_LOG_INFO_C` (`0x18e0`), `LOG_WLAN_COLD_BOOT_CAL_DATA_C` (`0x1a18`), `LOG_WLAN_DP_PROTO_PKT_INFO_C` (`0x1a1e`).",
        "- Target events: `EVENT_WLAN_BRINGUP_STATUS` (`0x0680`), `EVENT_WLAN_LOG_COMPLETE` (`0x0aa7`), `EVENT_WLAN_STATUS_V2` (`0x0ab3`).",
        "- Kept: clean-DSP companion, service managers, `pm-service`, `/dev/subsys_modem` holder, `cnss_diag`, stock `cnss-daemon`, `rmt_storage`, `tftp_server`, `pd-mapper`, firmware mounts, Android-parity fallback readonly RFS bridge, readwrite tmpfs bridge, persist-RFS tmpfs mirrors, cap/BDF/cal probes, post-cal indication probes, and long lower-window hold.",
        "- Excluded: DIAG logging-mode switch, broad DIAG log/event masks, DCI stream config, passive DIAG replay, boot-time QRTR matrix, rild/cnss/pm-service multi-strace, `tftp_server` ptrace, private SDX50M route, `/dev/subsys_esoc0` open, eSoC notify/BOOT_DONE, PCI rescan/bind, platform unbind, PMIC/GPIO/GDSC/regulator writes, forced RC1/case, restart-PD request, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, and firmware partition writes.",
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
    base = prev2038.prev2008.prev2006.build_base_module()
    base.base.EXPECTED_HELPER_MARKER = EXPECTED_HELPER_MARKER
    base.base.EXPECTED_HELPER_SHA256 = EXPECTED_HELPER_SHA256
    prev2038.patch_helper_builder(base)
    base.render_report = render_report
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())

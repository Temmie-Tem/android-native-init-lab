#!/usr/bin/env python3
"""Build V2054 native TFTP-ready pre-vote pre-wlanmdsp trigger test boot."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import build_native_init_wifi_test_boot_v2038 as prev2038


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v2054-tftp-ready-pre-vote-pre-wlanmdsp-trigger-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v2054/dev/__properties__"
EXPECTED_HELPER_MARKER = "a90_android_execns_probe v391"
EXPECTED_HELPER_SHA256 = "9b986f1030941577dbf07659899888727820fce7515047f6b830ed45cca15629"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V2054_TFTP_READY_PRE_VOTE_PRE_WLANMDSP_TRIGGER_SOURCE_BUILD_2026-06-04.md"
)
HELPER_FLAGS = (
    "-DA90_WIFI_TEST_BOOT_TFTP_LOGDW_SINK=1",
    "-DA90_WIFI_TEST_BOOT_TFTP_MCFG_READBACK=1",
    "-DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_TMPFS=1",
    "-DA90_WIFI_TEST_BOOT_TFTP_LOGDW_ORDER_TIMESTAMPS=1",
    "-DA90_WIFI_TEST_BOOT_TFTP_READY_BEFORE_WLFW_VOTE=1",
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
        "--cycle": "V2054",
        "--decision": "v2054-tftp-ready-pre-vote-pre-wlanmdsp-trigger-source-build-pass",
        "--cycle-label": "v2054",
        "--init-version": "0.9.206",
        "--init-build": "v2054-tftp-ready-pre-vote-pre-wlanmdsp-trigger",
        "--out-dir": str(OUT_DIR),
        "--init-binary": str(OUT_DIR / "init_v2054_tftp_ready_pre_vote_pre_wlanmdsp_trigger"),
        "--helper-binary": str(OUT_DIR / "a90_android_execns_probe_v391_tftp_ready_pre_vote_pre_wlanmdsp_trigger"),
        "--ramdisk-cpio": str(OUT_DIR / "ramdisk_v2054_tftp_ready_pre_vote_pre_wlanmdsp_trigger.cpio"),
        "--boot-image": str(OUT_DIR / "boot_linux_v2054_tftp_ready_pre_vote_pre_wlanmdsp_trigger.img"),
        "--wifi-test-klog-prefix": "A90v2054",
        "--wifi-test-disable": "/cache/native-init-wifi-test-boot-v2054.disable",
        "--wifi-test-log": "/cache/native-init-wifi-test-boot-v2054.log",
        "--wifi-test-summary": "/cache/native-init-wifi-test-boot-v2054.summary",
        "--wifi-test-helper-result": "/cache/native-init-wifi-test-boot-v2054-helper.result",
        "--wifi-test-pid": "/cache/native-init-wifi-test-boot-v2054.pid",
        "--wifi-test-watcher-pid": "/cache/native-init-wifi-test-boot-v2054-supervisor.pid",
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
        "# Native Init V2054 TFTP-Ready Pre-Vote Pre-WLANMDSP Trigger Source Build",
        "",
        "## Summary",
        "",
        "- Cycle: `V2054`",
        "- Type: source/build-only rollbackable internal-modem route with passive pre-`wlanmdsp` ordering timestamps plus a pre-vote `tftp_server` readiness/settle gate",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: helper v391 keeps the V2045 fallback readonly bridge, readwrite tmpfs, persist-RFS tmpfs mirrors, passive logdw, and read-only mcfg observer, and adds only a bounded pre-vote `tftp_server` readiness/settle gate with passive logdw drains; no ioctl/write/log-mask, ptrace, AP-side strace, QRTR matrix, or QMI send.",
        "- Manifest: `tmp/wifi/v2054-tftp-ready-pre-vote-pre-wlanmdsp-trigger-test-boot/manifest.json`",
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
        "- Observer: passive private `/dev/socket/logdw` with monotonic record timestamps plus a bounded TFTP pre-vote readiness/settle wait; no DIAG ioctl/write/log-mask, ptrace, AP-side strace, QRTR matrix, or QMI send.",
        "- Kept: clean-DSP companion, service managers, `pm-service`, `/dev/subsys_modem` holder, `cnss_diag`, stock `cnss-daemon`, `rmt_storage`, `tftp_server`, `pd-mapper`, firmware mounts, Android-parity fallback readonly RFS bridge, readwrite tmpfs bridge, persist-RFS tmpfs mirrors, cap/BDF/cal probes, post-cal indication probes, and long lower-window hold.",
        "- Excluded: boot-time QRTR matrix, rild/cnss/pm-service multi-strace, `tftp_server` ptrace, private SDX50M route, `/dev/subsys_esoc0` open, eSoC notify/BOOT_DONE, PCI rescan/bind, platform unbind, PMIC/GPIO/GDSC/regulator writes, forced RC1/case, restart-PD request, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, and firmware partition writes.",
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

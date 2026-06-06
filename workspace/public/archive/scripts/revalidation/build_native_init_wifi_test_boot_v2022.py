#!/usr/bin/env python3
"""Build V2022 native early all-task TFTP trace test boot."""

from __future__ import annotations

from pathlib import Path

import build_native_init_wifi_test_boot_v2020 as prev2020


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v2022-tftp-early-alltask-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v2022/dev/__properties__"
EXPECTED_HELPER_MARKER = "a90_android_execns_probe v380"
EXPECTED_HELPER_SHA256 = "c903a2453ed04a4400511b44aa2dfa388b4f69c1b87611c5910c39810d2f0727"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V2022_TFTP_EARLY_ALLTASK_SOURCE_BUILD_2026-06-04.md"
)
TFTP_HELPER_FLAGS = (
    "-DA90_WIFI_TEST_BOOT_WLAN_PD_PRODUCER_TFTP_SERVER_TRACE=1",
    "-DA90_WIFI_TEST_BOOT_WLAN_PD_PRODUCER_TFTP_SERVER_TRACE_COMPACT=1",
    "-DA90_WIFI_TEST_BOOT_WLAN_PD_PRODUCER_TFTP_SERVER_TRACE_ALL_TASKS=1",
    "-DA90_WIFI_TEST_BOOT_WLAN_PD_PRODUCER_TFTP_SERVER_TRACE_EARLY=1",
    "-DTFTP_SERVER_SYSCALL_RECORD_LIMIT=4096U",
    "-DTFTP_SERVER_SYSCALL_STOP_LIMIT=50000U",
    "-DTFTP_SERVER_SYSCALL_TRACE_MAX_TASKS=32U",
    "-DTFTP_SERVER_SYSCALL_TRACE_TIMEOUT_MS=45000U",
)


ORIGINAL_CONFIGURE_BASE = prev2020.configure_base


def configure_base() -> None:
    prev2020.OUT_DIR = OUT_DIR
    prev2020.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev2020.EXPECTED_HELPER_MARKER = EXPECTED_HELPER_MARKER
    prev2020.EXPECTED_HELPER_SHA256 = EXPECTED_HELPER_SHA256
    prev2020.REPORT_PATH = REPORT_PATH
    prev2020.TFTP_HELPER_FLAGS = TFTP_HELPER_FLAGS
    ORIGINAL_CONFIGURE_BASE()

    base = prev2020.prev2012.prev2010.prev2008.prev2006.build_base_module()
    args = list(base.DEFAULT_ARGS)
    replacements = {
        "--cycle": "V2022",
        "--decision": "v2022-tftp-early-alltask-source-build-pass",
        "--cycle-label": "v2022",
        "--init-version": "0.9.193",
        "--init-build": "v2022-tftp-early-alltask",
        "--out-dir": str(OUT_DIR),
        "--init-binary": str(OUT_DIR / "init_v2022_tftp_early_alltask"),
        "--helper-binary": str(OUT_DIR / "a90_android_execns_probe_v380"),
        "--ramdisk-cpio": str(OUT_DIR / "ramdisk_v2022_tftp_early_alltask.cpio"),
        "--boot-image": str(OUT_DIR / "boot_linux_v2022_tftp_early_alltask.img"),
        "--wifi-test-klog-prefix": "A90v2022",
        "--wifi-test-disable": "/cache/native-init-wifi-test-boot-v2022.disable",
        "--wifi-test-log": "/cache/native-init-wifi-test-boot-v2022.log",
        "--wifi-test-summary": "/cache/native-init-wifi-test-boot-v2022.summary",
        "--wifi-test-helper-result": "/cache/native-init-wifi-test-boot-v2022-helper.result",
        "--wifi-test-pid": "/cache/native-init-wifi-test-boot-v2022.pid",
        "--wifi-test-watcher-pid": "/cache/native-init-wifi-test-boot-v2022-supervisor.pid",
        "--wifi-test-property-root": REMOTE_PROPERTY_ROOT,
    }
    for key, value in replacements.items():
        prev2020.prev2012.prev2010.prev2008.prev2006.set_arg(args, key, value)
    if "--wifi-test-tftp-server-syscall-trace" not in args:
        args.append("--wifi-test-tftp-server-syscall-trace")
    base.DEFAULT_ARGS = args


def render_report(manifest: dict[str, object]) -> str:
    wifi = manifest["wifi_test"]
    property_runtime = manifest["cnss_nonlog_property_runtime"]
    check_lines = [
        f"- `{item['name']}`: `{item['actual']}` in `{item['context']}`"
        for item in property_runtime["checks"]
    ]
    return "\n".join([
        "# Native Init V2022 TFTP Early All-Task Source Build",
        "",
        "## Summary",
        "",
        "- Cycle: `V2022`",
        "- Type: source/build-only rollbackable internal-modem early TFTP discriminator",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: helper v380 keeps the full consumer chain and moves the bounded all-task `tftp_server` trace to the immediate post-`/dev/subsys_modem` holder edge, before the observer snapshots that missed the initial `server_check` / `ota_firewall` / `wlanmdsp` branch in V2021.",
        "- Manifest: `tmp/wifi/v2022-tftp-early-alltask-test-boot/manifest.json`",
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
        f"- TFTP-server syscall trace: `{wifi['tftp_server_syscall_trace']}`",
        "- TFTP trace contract: all current and newly discovered `tftp_server` tasks, compact RRQ/WRQ/DATA/ACK/ERROR packet records plus focused filesystem results, immediate post-holder attach, timeout `45000ms`, record limit `4096`, stop limit `50000`, max tasks `32`, no QRTR send, no QMI payload send.",
        "- Kept: clean-DSP companion, service managers, `pm-service`, `/dev/subsys_modem` holder, `cnss_diag`, stock `cnss-daemon`, `rmt_storage`, `tftp_server`, `pd-mapper`, firmware mounts, readonly RFS bridge, readwrite tmpfs bridge, cap/BDF/cal probes, indication probes, and light klog/ICNSS summaries.",
        "- Excluded: boot-time QRTR matrix, rild/cnss/pm-service multi-strace, private SDX50M route, `/dev/subsys_esoc0` open, eSoC notify/BOOT_DONE, PCI rescan/bind, platform unbind, PMIC/GPIO/GDSC/regulator writes, forced RC1/case, restart-PD request, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping.",
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
    prev2020.configure_base = configure_base
    prev2020.render_report = render_report
    return prev2020.main()


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Build V2020 native tftp all-task result test boot."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import build_native_init_wifi_test_boot_v2012 as prev2012


REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v2020-tftp-alltask-result-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v2020/dev/__properties__"
EXPECTED_HELPER_MARKER = "a90_android_execns_probe v379"
EXPECTED_HELPER_SHA256 = "da1358ab5b19dc0722b66c9c1d62796ebec6753e744ba7983d827eda92588c7a"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V2020_TFTP_ALLTASK_RESULT_SOURCE_BUILD_2026-06-04.md"
)
TFTP_HELPER_FLAGS = (
    "-DA90_WIFI_TEST_BOOT_WLAN_PD_PRODUCER_TFTP_SERVER_TRACE=1",
    "-DA90_WIFI_TEST_BOOT_WLAN_PD_PRODUCER_TFTP_SERVER_TRACE_COMPACT=1",
    "-DA90_WIFI_TEST_BOOT_WLAN_PD_PRODUCER_TFTP_SERVER_TRACE_ALL_TASKS=1",
    "-DTFTP_SERVER_SYSCALL_RECORD_LIMIT=2048U",
    "-DTFTP_SERVER_SYSCALL_STOP_LIMIT=30000U",
    "-DTFTP_SERVER_SYSCALL_TRACE_MAX_TASKS=24U",
    "-DTFTP_SERVER_SYSCALL_TRACE_TIMEOUT_MS=45000U",
)


def configure_base() -> None:
    prev2012.OUT_DIR = OUT_DIR
    prev2012.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev2012.REPORT_PATH = REPORT_PATH
    prev2012.EXPECTED_HELPER_MARKER = EXPECTED_HELPER_MARKER
    prev2012.EXPECTED_HELPER_SHA256 = EXPECTED_HELPER_SHA256
    prev2012.configure_base()

    base = prev2012.prev2010.prev2008.prev2006.build_base_module()
    args = list(base.DEFAULT_ARGS)
    replacements = {
        "--cycle": "V2020",
        "--decision": "v2020-tftp-alltask-result-source-build-pass",
        "--cycle-label": "v2020",
        "--init-version": "0.9.192",
        "--init-build": "v2020-tftp-alltask-result",
        "--out-dir": str(OUT_DIR),
        "--init-binary": str(OUT_DIR / "init_v2020_tftp_alltask_result"),
        "--helper-binary": str(OUT_DIR / "a90_android_execns_probe_v379"),
        "--ramdisk-cpio": str(OUT_DIR / "ramdisk_v2020_tftp_alltask_result.cpio"),
        "--boot-image": str(OUT_DIR / "boot_linux_v2020_tftp_alltask_result.img"),
        "--wifi-test-klog-prefix": "A90v2020",
        "--wifi-test-disable": "/cache/native-init-wifi-test-boot-v2020.disable",
        "--wifi-test-log": "/cache/native-init-wifi-test-boot-v2020.log",
        "--wifi-test-summary": "/cache/native-init-wifi-test-boot-v2020.summary",
        "--wifi-test-helper-result": "/cache/native-init-wifi-test-boot-v2020-helper.result",
        "--wifi-test-pid": "/cache/native-init-wifi-test-boot-v2020.pid",
        "--wifi-test-watcher-pid": "/cache/native-init-wifi-test-boot-v2020-supervisor.pid",
        "--wifi-test-property-root": REMOTE_PROPERTY_ROOT,
    }
    for key, value in replacements.items():
        prev2012.prev2010.prev2008.prev2006.set_arg(args, key, value)
    if "--wifi-test-tftp-server-syscall-trace" not in args:
        args.append("--wifi-test-tftp-server-syscall-trace")
    base.DEFAULT_ARGS = args


def patch_helper_builder(base_wrapper: Any) -> None:
    build_base = base_wrapper.base

    def build_helper(args: Any) -> None:
        args.out_dir.mkdir(parents=True, exist_ok=True)
        command: list[object] = [
            "env",
            "A90_EXECNS_PROBE_CFLAGS=" + " ".join(TFTP_HELPER_FLAGS),
            "bash",
            build_base.HELPER_BUILD_SCRIPT,
            args.helper_binary,
        ]
        build_base.run(command)
        args.helper_binary.chmod(0o600)
        helper_sha = build_base.sha256(args.helper_binary)
        if helper_sha != EXPECTED_HELPER_SHA256:
            raise RuntimeError(
                f"helper sha mismatch: got {helper_sha}, expected {EXPECTED_HELPER_SHA256}"
            )
        strings = build_base.run(["strings", args.helper_binary], capture=True).stdout
        if EXPECTED_HELPER_MARKER not in strings:
            raise RuntimeError(f"missing helper marker: {EXPECTED_HELPER_MARKER}")

    build_base.build_helper = build_helper


def render_report(manifest: dict[str, object]) -> str:
    wifi = manifest["wifi_test"]
    property_runtime = manifest["cnss_nonlog_property_runtime"]
    check_lines = [
        f"- `{item['name']}`: `{item['actual']}` in `{item['context']}`"
        for item in property_runtime["checks"]
    ]
    return "\n".join([
        "# Native Init V2020 TFTP All-Task Result Source Build",
        "",
        "## Summary",
        "",
        "- Cycle: `V2020`",
        "- Type: source/build-only rollbackable internal-modem tftp all-task result discriminator",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: helper v379 keeps the full consumer chain and adds all-task `tftp_server` late attach with compact `sendmsg`/`recvmsg` TFTP result decoding plus focused filesystem path results for the `mcfg.tmp` retry gate.",
        "- Manifest: `tmp/wifi/v2020-tftp-alltask-result-test-boot/manifest.json`",
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
        "- TFTP trace contract: all current and newly discovered `tftp_server` tasks, with compact RRQ/WRQ/DATA/ACK/ERROR packet records from recvfrom/sendto/recvmsg/sendmsg plus focused path syscall records, timeout `45000ms`, record limit `2048`, stop limit `30000`, no QRTR send, no QMI payload send.",
        "- Kept: clean-DSP companion, service managers, `pm-service`, `/dev/subsys_modem` holder, `cnss_diag`, stock `cnss-daemon`, `rmt_storage`, `tftp_server`, `pd-mapper`, firmware mounts, readonly RFS bridge, readwrite tmpfs bridge, cap/BDF/cal probes, indication probes, and light klog/ICNSS summaries.",
        "- Excluded by construction: boot-time QRTR matrix, rild/cnss/pm-service multi-strace, private SDX50M mount, `/dev/subsys_esoc0` open, eSoC notify/BOOT_DONE, PCI rescan/bind, platform unbind, PMIC/GPIO/GDSC/regulator writes, forced RC1/case, restart-PD request, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping.",
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
    base = prev2012.prev2010.prev2008.prev2006.build_base_module()
    base.base.EXPECTED_HELPER_MARKER = EXPECTED_HELPER_MARKER
    base.base.EXPECTED_HELPER_SHA256 = EXPECTED_HELPER_SHA256
    patch_helper_builder(base)
    base.render_report = render_report
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())

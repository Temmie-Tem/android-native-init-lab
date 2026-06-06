#!/usr/bin/env python3
"""Build V1995 pd-mapper syscall-trace native observer test boot."""

from __future__ import annotations

from pathlib import Path

import build_native_init_wifi_test_boot_v1991 as prev1991


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1995-pd-mapper-syscall-trace-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v1995/dev/__properties__"
EXPECTED_HELPER_MARKER = "a90_android_execns_probe v367"
EXPECTED_HELPER_SHA256 = "2295b070e422a1b917d1588dcbfe2d6217d9df994d1e99799c1b875a616d4901"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1995_PD_MAPPER_SYSCALL_TRACE_SOURCE_BUILD_2026-06-04.md"
)


def configure_base() -> None:
    prev1991.configure_base()
    prev1991.OUT_DIR = OUT_DIR
    prev1991.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev1991.REPORT_PATH = REPORT_PATH
    prev1991.prev1989.OUT_DIR = OUT_DIR
    prev1991.prev1989.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev1991.prev1989.REPORT_PATH = REPORT_PATH
    prev1991.prev1989.prev1936.OUT_DIR = OUT_DIR
    prev1991.prev1989.prev1936.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev1991.prev1989.prev1936.REPORT_PATH = REPORT_PATH
    prev1991.prev1989.prev1936.prev1929.OUT_DIR = OUT_DIR
    prev1991.prev1989.prev1936.prev1929.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev1991.prev1989.prev1936.prev1929.REPORT_PATH = REPORT_PATH
    prev1991.prev1989.prev1936.prev1929.prev1792.OUT_DIR = OUT_DIR
    prev1991.prev1989.prev1936.prev1929.prev1792.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev1991.prev1989.prev1936.prev1929.prev1792.REPORT_PATH = REPORT_PATH
    prev1991.prev1989.prev1936.prev1929.prev1792.prev1790.OUT_DIR = OUT_DIR
    prev1991.prev1989.prev1936.prev1929.prev1792.prev1790.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev1991.prev1989.prev1936.prev1929.prev1792.prev1790.REPORT_PATH = REPORT_PATH
    prev1991.prev1989.prev1936.prev1929.prev1792.prev1790.prev1783.V1783_OUT = OUT_DIR
    prev1991.prev1989.prev1936.prev1929.prev1792.prev1790.prev1783.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev1991.prev1989.prev1936.prev1929.prev1792.prev1790.prev1783.DEFAULT_REPORT_PATH = REPORT_PATH
    prev = prev1991.prev1989.prev1936.prev1929.prev1792.prev1790.prev1783.prev
    prev.OUT_DIR = OUT_DIR
    prev.PROPERTY_RUNTIME_DIR = OUT_DIR / "property-runtime"
    prev.PROPERTY_ROOT = prev.PROPERTY_RUNTIME_DIR / "layout" / "dev" / "__properties__"
    prev.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev.REPORT_PATH = REPORT_PATH
    prev.DEFAULT_ARGS = [
        "--cycle",
        "V1995",
        "--decision",
        "v1995-pd-mapper-syscall-trace-source-build-pass",
        "--cycle-label",
        "v1995",
        "--init-version",
        "0.9.180",
        "--init-build",
        "v1995-pd-mapper-syscall-trace",
        "--out-dir",
        str(OUT_DIR),
        "--init-binary",
        str(OUT_DIR / "init_v1995_pd_mapper_syscall_trace"),
        "--helper-binary",
        str(OUT_DIR / "a90_android_execns_probe_v367"),
        "--ramdisk-cpio",
        str(OUT_DIR / "ramdisk_v1995_pd_mapper_syscall_trace.cpio"),
        "--boot-image",
        str(OUT_DIR / "boot_linux_v1995_pd_mapper_syscall_trace.img"),
        "--wifi-test-klog-prefix",
        "A90v1995",
        "--wifi-test-disable",
        "/cache/native-init-wifi-test-boot-v1995.disable",
        "--wifi-test-log",
        "/cache/native-init-wifi-test-boot-v1995.log",
        "--wifi-test-summary",
        "/cache/native-init-wifi-test-boot-v1995.summary",
        "--wifi-test-helper-result",
        "/cache/native-init-wifi-test-boot-v1995-helper.result",
        "--wifi-test-pid",
        "/cache/native-init-wifi-test-boot-v1995.pid",
        "--wifi-test-watcher-pid",
        "/cache/native-init-wifi-test-boot-v1995-supervisor.pid",
        "--wifi-test-watch-sec",
        "120",
        "--wifi-test-supervise-helper",
        "--wifi-test-supervisor-timeout-sec",
        "150",
        "--wifi-test-firmware-mounts",
        "--wifi-test-mount-debugfs",
        "--wifi-test-light-firmware-trace",
        "--wifi-test-pd-mapper-syscall-trace",
        "--wifi-test-property-root",
        REMOTE_PROPERTY_ROOT,
        "--wifi-test-helper-mode",
        "wlan-pd-post-pm-lower-state-observer",
    ]


def render_report(manifest: dict[str, object]) -> str:
    wifi = manifest["wifi_test"]
    property_runtime = manifest["cnss_nonlog_property_runtime"]
    check_lines = [
        f"- `{item['name']}`: `{item['actual']}` in `{item['context']}`"
        for item in property_runtime["checks"]
    ]
    return "\n".join([
        "# Native Init V1995 PD-Mapper Syscall Trace Source Build",
        "",
        "## Summary",
        "",
        "- Cycle: `V1995`",
        "- Type: source/build-only rollbackable internal-modem pd-mapper producer observer",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: helper v367 keeps the V1991/V1993 RFS-bridge light route and adds an opt-in late-attach single-child ptrace payload trace for stock `pd-mapper` only.",
        "- Manifest: `tmp/wifi/v1995-pd-mapper-syscall-trace-test-boot/manifest.json`",
        f"- Boot image: `{manifest['boot_image']}`",
        f"- Boot SHA256: `{manifest['boot_sha256']}`",
        f"- Init: `A90 Linux init {manifest['init_version']} ({manifest['init_build']})`",
        f"- Helper marker: `{manifest['helper_marker']}`",
        f"- Helper SHA256: `{manifest['helper_sha256']}`",
        "",
        "## Route",
        "",
        f"- Helper runtime mode: `{wifi['helper_runtime_mode']}`",
        f"- Property root: `{REMOTE_PROPERTY_ROOT}`",
        f"- Light firmware trace: `{wifi['light_firmware_trace']}`",
        f"- PD-mapper syscall trace: `{wifi['pd_mapper_syscall_trace']}`",
        "- Kept: clean-DSP companion, service managers, `pm-service`, `/dev/subsys_modem` holder, `cnss_diag`, stock `cnss-daemon`, `rmt_storage`, `tftp_server`, `pd-mapper`, firmware mounts, RFS bridge, and klog lower-window summaries.",
        "- Added: late-attach single-child ptrace of already-running `pd-mapper` `sendmsg`/`recvmsg`/`sendto`/`recvfrom` payloads, bounded to answer whether the modem queries PD mapping before the missing `wlanmdsp.mbn` request.",
        "- Still excluded from init argv: rild/cnss/pm-service strace, boot-time QRTR matrix, service-locator probe, service-notifier listener, active QRTR send/readback, and QMI payload send.",
        "- Live discriminator: no pd-mapper QRTR payload before no-request, pd-mapper query seen but no tftp request, or query plus wlanmdsp request/load progress.",
        "- Excluded by construction: private SDX50M mount, `/dev/subsys_esoc0` open, eSoC notify/BOOT_DONE, PCI rescan/bind, platform unbind, PMIC/GPIO/GDSC/regulator writes, forced RC1/case, restart-PD request, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping.",
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
    base = prev1991.prev1989.prev1936.prev1929.prev1792.prev1790.prev1783.prev
    base.base.EXPECTED_HELPER_MARKER = EXPECTED_HELPER_MARKER
    base.base.EXPECTED_HELPER_SHA256 = EXPECTED_HELPER_SHA256
    base.render_report = render_report
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())

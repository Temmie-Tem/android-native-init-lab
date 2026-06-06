#!/usr/bin/env python3
"""Build V2010 native post-cal tftp sockaddr test boot."""

from __future__ import annotations

from pathlib import Path

import build_native_init_wifi_test_boot_v2008 as prev2008


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v2010-post-cal-tftp-sockaddr-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v2010/dev/__properties__"
EXPECTED_HELPER_MARKER = "a90_android_execns_probe v374"
EXPECTED_HELPER_SHA256 = "a32bdb65c208b7eece93916dbcbd5a03b91ce79add6b4eda11fd49f6309852bb"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V2010_POST_CAL_TFTP_SOCKADDR_SOURCE_BUILD_2026-06-04.md"
)


def configure_base() -> None:
    prev2008.OUT_DIR = OUT_DIR
    prev2008.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev2008.REPORT_PATH = REPORT_PATH
    prev2008.EXPECTED_HELPER_MARKER = EXPECTED_HELPER_MARKER
    prev2008.EXPECTED_HELPER_SHA256 = EXPECTED_HELPER_SHA256
    prev2008.configure_base()

    base = prev2008.prev2006.build_base_module()
    args = list(base.DEFAULT_ARGS)
    replacements = {
        "--cycle": "V2010",
        "--decision": "v2010-post-cal-tftp-sockaddr-source-build-pass",
        "--cycle-label": "v2010",
        "--init-version": "0.9.187",
        "--init-build": "v2010-post-cal-tftp-sockaddr",
        "--out-dir": str(OUT_DIR),
        "--init-binary": str(OUT_DIR / "init_v2010_post_cal_tftp_sockaddr"),
        "--helper-binary": str(OUT_DIR / "a90_android_execns_probe_v374"),
        "--ramdisk-cpio": str(OUT_DIR / "ramdisk_v2010_post_cal_tftp_sockaddr.cpio"),
        "--boot-image": str(OUT_DIR / "boot_linux_v2010_post_cal_tftp_sockaddr.img"),
        "--wifi-test-klog-prefix": "A90v2010",
        "--wifi-test-disable": "/cache/native-init-wifi-test-boot-v2010.disable",
        "--wifi-test-log": "/cache/native-init-wifi-test-boot-v2010.log",
        "--wifi-test-summary": "/cache/native-init-wifi-test-boot-v2010.summary",
        "--wifi-test-helper-result": "/cache/native-init-wifi-test-boot-v2010-helper.result",
        "--wifi-test-pid": "/cache/native-init-wifi-test-boot-v2010.pid",
        "--wifi-test-watcher-pid": "/cache/native-init-wifi-test-boot-v2010-supervisor.pid",
        "--wifi-test-property-root": REMOTE_PROPERTY_ROOT,
    }
    for key, value in replacements.items():
        prev2008.prev2006.set_arg(args, key, value)
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
        "# Native Init V2010 Post-Cal TFTP Sockaddr Source Build",
        "",
        "## Summary",
        "",
        "- Cycle: `V2010`",
        "- Type: source/build-only rollbackable internal-modem post-cal tftp sockaddr discriminator",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: helper v374 keeps the V2008 downstream consumer route and adds only recvfrom source-sockaddr capture to the bounded single-child `tftp_server` trace.",
        "- Manifest: `tmp/wifi/v2010-post-cal-tftp-sockaddr-test-boot/manifest.json`",
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
        "- Kept: clean-DSP companion, service managers, `pm-service`, `/dev/subsys_modem` holder, `cnss_diag`, stock `cnss-daemon`, `rmt_storage`, `tftp_server`, `pd-mapper`, firmware mounts, readonly RFS bridge, readwrite tmpfs bridge, cap/BDF/cal probes, and light klog/ICNSS summaries.",
        "- Added: `recvfrom` source `sockaddr`/`sockaddr_len` capture for the stock `tftp_server` trace, to distinguish modem QRTR traffic from local control packets.",
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
    base = prev2008.prev2006.build_base_module()
    base.base.EXPECTED_HELPER_MARKER = EXPECTED_HELPER_MARKER
    base.base.EXPECTED_HELPER_SHA256 = EXPECTED_HELPER_SHA256
    base.render_report = render_report
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())

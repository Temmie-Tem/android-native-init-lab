#!/usr/bin/env python3
"""Build V2038 native dual-RFS + mcfg readback test boot."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import build_native_init_wifi_test_boot_v2008 as prev2008


REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v2038-dual-rfs-mcfg-readback-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v2038/dev/__properties__"
EXPECTED_HELPER_MARKER = "a90_android_execns_probe v385"
EXPECTED_HELPER_SHA256 = "9db3a1da725be9c4e0fe6537f46fb399a4de36a617fe6918378f06222725157f"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V2038_DUAL_RFS_MCFG_READBACK_SOURCE_BUILD_2026-06-04.md"
)
HELPER_FLAGS = (
    "-DA90_WIFI_TEST_BOOT_TFTP_LOGDW_SINK=1",
    "-DA90_RFS_BRIDGE_SERVE_FIRMWARE_MNT_PROBE=1",
    "-DA90_WIFI_TEST_BOOT_TFTP_MCFG_READBACK=1",
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
        "--cycle": "V2038",
        "--decision": "v2038-dual-rfs-mcfg-readback-source-build-pass",
        "--cycle-label": "v2038",
        "--init-version": "0.9.200",
        "--init-build": "v2038-dual-rfs-mcfg-readback",
        "--out-dir": str(OUT_DIR),
        "--init-binary": str(OUT_DIR / "init_v2038_dual_rfs_mcfg_readback"),
        "--helper-binary": str(OUT_DIR / "a90_android_execns_probe_v385_mcfg_readback"),
        "--ramdisk-cpio": str(OUT_DIR / "ramdisk_v2038_dual_rfs_mcfg_readback.cpio"),
        "--boot-image": str(OUT_DIR / "boot_linux_v2038_dual_rfs_mcfg_readback.img"),
        "--wifi-test-klog-prefix": "A90v2038",
        "--wifi-test-disable": "/cache/native-init-wifi-test-boot-v2038.disable",
        "--wifi-test-log": "/cache/native-init-wifi-test-boot-v2038.log",
        "--wifi-test-summary": "/cache/native-init-wifi-test-boot-v2038.summary",
        "--wifi-test-helper-result": "/cache/native-init-wifi-test-boot-v2038-helper.result",
        "--wifi-test-pid": "/cache/native-init-wifi-test-boot-v2038.pid",
        "--wifi-test-watcher-pid": "/cache/native-init-wifi-test-boot-v2038-supervisor.pid",
        "--wifi-test-property-root": REMOTE_PROPERTY_ROOT,
    }
    for key, value in replacements.items():
        prev2008.prev2006.set_arg(args, key, value)
    base.DEFAULT_ARGS = args


def patch_helper_builder(base_wrapper: Any) -> None:
    build_base = base_wrapper.base

    def build_helper(args: Any) -> None:
        args.out_dir.mkdir(parents=True, exist_ok=True)
        command: list[object] = [
            "env",
            "A90_EXECNS_PROBE_CFLAGS=" + " ".join(HELPER_FLAGS),
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
        "# Native Init V2038 Dual RFS MCFG Readback Source Build",
        "",
        "## Summary",
        "",
        "- Cycle: `V2038`",
        "- Type: source/build-only rollbackable internal-modem dual-RFS route with passive `mcfg.tmp` post-WRQ readback",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: helper v385 keeps the V2037 dual-RFS + logdw route and adds only read-only stat/open/read samples of `/vendor/rfs/msm/mpss/readwrite/mcfg.tmp` after stock `tftp_server` reports the WRQ edge.",
        "- Manifest: `tmp/wifi/v2038-dual-rfs-mcfg-readback-test-boot/manifest.json`",
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
        "- Readback observer: passive private `/dev/socket/logdw` trigger plus read-only `mcfg.tmp` stat/open/read samples; no file writes beyond modem-originated tmpfs WRQ.",
        "- Kept: clean-DSP companion, service managers, `pm-service`, `/dev/subsys_modem` holder, `cnss_diag`, stock `cnss-daemon`, `rmt_storage`, `tftp_server`, `pd-mapper`, firmware mounts, dual-RFS WLAN image bridge, readwrite tmpfs bridge, cap/BDF/cal probes, post-cal indication probes, and light klog/ICNSS summaries.",
        "- Excluded: boot-time QRTR matrix, rild/cnss/pm-service multi-strace, `tftp_server` ptrace, private SDX50M route, `/dev/subsys_esoc0` open, eSoC notify/BOOT_DONE, PCI rescan/bind, platform unbind, PMIC/GPIO/GDSC/regulator writes, forced RC1/case, restart-PD request, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping.",
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
    patch_helper_builder(base)
    base.render_report = render_report
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())

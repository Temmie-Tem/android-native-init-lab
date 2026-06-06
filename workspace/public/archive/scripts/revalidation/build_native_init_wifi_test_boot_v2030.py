#!/usr/bin/env python3
"""Build V2030 native dual RFS post-cal indication test boot."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import build_native_init_wifi_test_boot_v2008 as prev2008


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v2030-dual-rfs-post-cal-indication-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v2030/dev/__properties__"
EXPECTED_HELPER_MARKER = "a90_android_execns_probe v382"
EXPECTED_HELPER_SHA256 = "e3ac90ed04e81e8364c8149dee5a991ee9beccd38e8d7c566718137f2387912d"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V2030_DUAL_RFS_POST_CAL_INDICATION_SOURCE_BUILD_2026-06-04.md"
)
HELPER_FLAGS = ("-DA90_RFS_BRIDGE_SERVE_FIRMWARE_MNT_PROBE=1",)


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
        "--cycle": "V2030",
        "--decision": "v2030-dual-rfs-post-cal-indication-source-build-pass",
        "--cycle-label": "v2030",
        "--init-version": "0.9.197",
        "--init-build": "v2030-dual-rfs-post-cal-indication",
        "--out-dir": str(OUT_DIR),
        "--init-binary": str(OUT_DIR / "init_v2030_dual_rfs_post_cal_indication"),
        "--helper-binary": str(OUT_DIR / "a90_android_execns_probe_v382_dual_rfs_indication"),
        "--ramdisk-cpio": str(OUT_DIR / "ramdisk_v2030_dual_rfs_post_cal_indication.cpio"),
        "--boot-image": str(OUT_DIR / "boot_linux_v2030_dual_rfs_post_cal_indication.img"),
        "--wifi-test-klog-prefix": "A90v2030",
        "--wifi-test-disable": "/cache/native-init-wifi-test-boot-v2030.disable",
        "--wifi-test-log": "/cache/native-init-wifi-test-boot-v2030.log",
        "--wifi-test-summary": "/cache/native-init-wifi-test-boot-v2030.summary",
        "--wifi-test-helper-result": "/cache/native-init-wifi-test-boot-v2030-helper.result",
        "--wifi-test-pid": "/cache/native-init-wifi-test-boot-v2030.pid",
        "--wifi-test-watcher-pid": "/cache/native-init-wifi-test-boot-v2030-supervisor.pid",
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
        "# Native Init V2030 Dual RFS Post-Cal Indication Source Build",
        "",
        "## Summary",
        "",
        "- Cycle: `V2030`",
        "- Type: source/build-only rollbackable internal-modem dual RFS post-cal indication probe artifact",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: helper v382 keeps the exact native `wlanmdsp.mbn` RFS serve path from V2029 and removes the TFTP ptrace observer, while preserving the post-cal WLFW indication queue/handler probes from V2009.",
        "- Manifest: `tmp/wifi/v2030-dual-rfs-post-cal-indication-test-boot/manifest.json`",
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
        "- Kept: clean-DSP companion, service managers, `pm-service`, `/dev/subsys_modem` holder, `cnss_diag`, stock `cnss-daemon`, `rmt_storage`, `tftp_server`, `pd-mapper`, firmware mounts, dual RFS wlanmdsp bridge, readwrite tmpfs bridge, cap/BDF/cal probes, indication probes, and light klog/ICNSS summaries.",
        "- Excluded: tftp_server ptrace, boot-time QRTR matrix, rild/cnss/pm-service multi-strace, private SDX50M route, `/dev/subsys_esoc0` open, eSoC notify/BOOT_DONE, PCI rescan/bind, platform unbind, PMIC/GPIO/GDSC/regulator writes, forced RC1/case, restart-PD request, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping.",
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

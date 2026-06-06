#!/usr/bin/env python3
"""Build V2002 native post-WLFW-cap branch-probe test boot."""

from __future__ import annotations

from pathlib import Path

import build_native_init_wifi_test_boot_v1999 as prev1999


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v2002-post-wlfw-cap-branch-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v2002/dev/__properties__"
EXPECTED_HELPER_MARKER = "a90_android_execns_probe v370"
EXPECTED_HELPER_SHA256 = "d3c13d00d4a9317720ad875fda9547ef80c04ccceb84a39a7eddaa4f41f26362"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V2002_POST_WLFW_CAP_BRANCH_SOURCE_BUILD_2026-06-04.md"
)


def configure_base() -> None:
    prev1999.OUT_DIR = OUT_DIR
    prev1999.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev1999.REPORT_PATH = REPORT_PATH
    prev1999.configure_base()
    base = prev1999.prev1997.prev1991.prev1989.prev1936.prev1929.prev1792.prev1790.prev1783.prev
    base.DEFAULT_ARGS = [
        "--cycle",
        "V2002",
        "--decision",
        "v2002-post-wlfw-cap-branch-source-build-pass",
        "--cycle-label",
        "v2002",
        "--init-version",
        "0.9.183",
        "--init-build",
        "v2002-post-wlfw-cap-branch",
        "--out-dir",
        str(OUT_DIR),
        "--init-binary",
        str(OUT_DIR / "init_v2002_post_wlfw_cap_branch"),
        "--helper-binary",
        str(OUT_DIR / "a90_android_execns_probe_v370"),
        "--ramdisk-cpio",
        str(OUT_DIR / "ramdisk_v2002_post_wlfw_cap_branch.cpio"),
        "--boot-image",
        str(OUT_DIR / "boot_linux_v2002_post_wlfw_cap_branch.img"),
        "--wifi-test-klog-prefix",
        "A90v2002",
        "--wifi-test-disable",
        "/cache/native-init-wifi-test-boot-v2002.disable",
        "--wifi-test-log",
        "/cache/native-init-wifi-test-boot-v2002.log",
        "--wifi-test-summary",
        "/cache/native-init-wifi-test-boot-v2002.summary",
        "--wifi-test-helper-result",
        "/cache/native-init-wifi-test-boot-v2002-helper.result",
        "--wifi-test-pid",
        "/cache/native-init-wifi-test-boot-v2002.pid",
        "--wifi-test-watcher-pid",
        "/cache/native-init-wifi-test-boot-v2002-supervisor.pid",
        "--wifi-test-watch-sec",
        "150",
        "--wifi-test-supervise-helper",
        "--wifi-test-supervisor-timeout-sec",
        "180",
        "--wifi-test-helper-timeout-sec",
        "75",
        "--wifi-test-firmware-mounts",
        "--wifi-test-mount-debugfs",
        "--wifi-test-light-firmware-trace",
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
        "# Native Init V2002 Post-WLFW-Cap Branch Source Build",
        "",
        "## Summary",
        "",
        "- Cycle: `V2002`",
        "- Type: source/build-only rollbackable internal-modem post-WLFW-cap branch-probe artifact",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: helper v370 keeps the V1999/V2000 route and adds only branch-level WLFW capability-send probes from V2001.",
        "- Manifest: `tmp/wifi/v2002-post-wlfw-cap-branch-test-boot/manifest.json`",
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
        "- Kept: clean-DSP companion, service managers, `pm-service`, `/dev/subsys_modem` holder, `cnss_diag`, stock `cnss-daemon`, `rmt_storage`, `tftp_server`, `pd-mapper`, firmware mounts, readonly RFS bridge, readwrite tmpfs bridge, and klog/ICNSS summaries.",
        "- Added: `wlfw_fw_mem_wait_return`, `wlfw_cap_send_ret`, `wlfw_cap_send_or_result_error_branch`, `wlfw_cap_invalid_0x77_branch`, `wlfw_cap_success_branch`, `wlfw_cap_rsp_result_error_branch`, and `wlfw_cap_return` uprobes.",
        "- Excluded by construction: tftp_server ptrace, boot-time QRTR matrix, rild/cnss/pm-service multi-strace, private SDX50M mount, `/dev/subsys_esoc0` open, eSoC notify/BOOT_DONE, PCI rescan/bind, platform unbind, PMIC/GPIO/GDSC/regulator writes, forced RC1/case, restart-PD request, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping.",
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
    base = prev1999.prev1997.prev1991.prev1989.prev1936.prev1929.prev1792.prev1790.prev1783.prev
    base.base.EXPECTED_HELPER_MARKER = EXPECTED_HELPER_MARKER
    base.base.EXPECTED_HELPER_SHA256 = EXPECTED_HELPER_SHA256
    base.render_report = render_report
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())

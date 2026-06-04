#!/usr/bin/env python3
"""Build V2004 native post-cap BDF branch-probe test boot."""

from __future__ import annotations

from pathlib import Path

import build_native_init_wifi_test_boot_v1999 as prev1999


REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v2004-post-cap-bdf-branch-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v2004/dev/__properties__"
EXPECTED_HELPER_MARKER = "a90_android_execns_probe v371"
EXPECTED_HELPER_SHA256 = "8ddc1b06fde58db8592c254f4bd2ac43ac071ed2a392b85feae99f19f02a8a31"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V2004_POST_CAP_BDF_BRANCH_SOURCE_BUILD_2026-06-04.md"
)


def configure_base() -> None:
    prev1999.OUT_DIR = OUT_DIR
    prev1999.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev1999.REPORT_PATH = REPORT_PATH
    prev1999.configure_base()
    base = prev1999.prev1997.prev1991.prev1989.prev1936.prev1929.prev1792.prev1790.prev1783.prev
    base.DEFAULT_ARGS = [
        "--cycle",
        "V2004",
        "--decision",
        "v2004-post-cap-bdf-branch-source-build-pass",
        "--cycle-label",
        "v2004",
        "--init-version",
        "0.9.184",
        "--init-build",
        "v2004-post-cap-bdf-branch",
        "--out-dir",
        str(OUT_DIR),
        "--init-binary",
        str(OUT_DIR / "init_v2004_post_cap_bdf_branch"),
        "--helper-binary",
        str(OUT_DIR / "a90_android_execns_probe_v371"),
        "--ramdisk-cpio",
        str(OUT_DIR / "ramdisk_v2004_post_cap_bdf_branch.cpio"),
        "--boot-image",
        str(OUT_DIR / "boot_linux_v2004_post_cap_bdf_branch.img"),
        "--wifi-test-klog-prefix",
        "A90v2004",
        "--wifi-test-disable",
        "/cache/native-init-wifi-test-boot-v2004.disable",
        "--wifi-test-log",
        "/cache/native-init-wifi-test-boot-v2004.log",
        "--wifi-test-summary",
        "/cache/native-init-wifi-test-boot-v2004.summary",
        "--wifi-test-helper-result",
        "/cache/native-init-wifi-test-boot-v2004-helper.result",
        "--wifi-test-pid",
        "/cache/native-init-wifi-test-boot-v2004.pid",
        "--wifi-test-watcher-pid",
        "/cache/native-init-wifi-test-boot-v2004-supervisor.pid",
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
        "# Native Init V2004 Post-Cap BDF Branch Source Build",
        "",
        "## Summary",
        "",
        "- Cycle: `V2004`",
        "- Type: source/build-only rollbackable internal-modem post-cap BDF branch-probe artifact",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: helper v371 keeps the V1999/V2002 route and adds only branch-level `wlfw_send_bdf_download_req` probes after V2003 proved WLFW capability QMI success.",
        "- Manifest: `tmp/wifi/v2004-post-cap-bdf-branch-test-boot/manifest.json`",
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
        "- Added: `wlfw_bdf_entry`, `wlfw_bdf_named_path_ready`, `wlfw_bdf_open_success`, `wlfw_bdf_not_found`, `wlfw_bdf_read_complete`, `wlfw_bdf_send_call`, `wlfw_bdf_send_ret`, `wlfw_bdf_send_error_branch`, `wlfw_bdf_result_log`, and `wlfw_bdf_return` uprobes.",
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

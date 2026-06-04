#!/usr/bin/env python3
"""Build V1999 native downstream cascade test boot."""

from __future__ import annotations

from pathlib import Path

import build_native_init_wifi_test_boot_v1997 as prev1997


REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1999-downstream-cascade-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v1999/dev/__properties__"
EXPECTED_HELPER_MARKER = "a90_android_execns_probe v369"
EXPECTED_HELPER_SHA256 = "65f239ab69887ae964f7c49c8fc4bea4aad76e200a89f9bb83b93bb38c40ebda"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1999_DOWNSTREAM_CASCADE_SOURCE_BUILD_2026-06-04.md"
)


def configure_base() -> None:
    prev1997.configure_base()
    prev1997.OUT_DIR = OUT_DIR
    prev1997.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev1997.REPORT_PATH = REPORT_PATH
    prev1997.prev1991.OUT_DIR = OUT_DIR
    prev1997.prev1991.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev1997.prev1991.REPORT_PATH = REPORT_PATH
    prev1997.prev1991.prev1989.OUT_DIR = OUT_DIR
    prev1997.prev1991.prev1989.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev1997.prev1991.prev1989.REPORT_PATH = REPORT_PATH
    prev1997.prev1991.prev1989.prev1936.OUT_DIR = OUT_DIR
    prev1997.prev1991.prev1989.prev1936.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev1997.prev1991.prev1989.prev1936.REPORT_PATH = REPORT_PATH
    prev1997.prev1991.prev1989.prev1936.prev1929.OUT_DIR = OUT_DIR
    prev1997.prev1991.prev1989.prev1936.prev1929.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev1997.prev1991.prev1989.prev1936.prev1929.REPORT_PATH = REPORT_PATH
    prev1997.prev1991.prev1989.prev1936.prev1929.prev1792.OUT_DIR = OUT_DIR
    prev1997.prev1991.prev1989.prev1936.prev1929.prev1792.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev1997.prev1991.prev1989.prev1936.prev1929.prev1792.REPORT_PATH = REPORT_PATH
    prev1997.prev1991.prev1989.prev1936.prev1929.prev1792.prev1790.OUT_DIR = OUT_DIR
    prev1997.prev1991.prev1989.prev1936.prev1929.prev1792.prev1790.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev1997.prev1991.prev1989.prev1936.prev1929.prev1792.prev1790.REPORT_PATH = REPORT_PATH
    prev1997.prev1991.prev1989.prev1936.prev1929.prev1792.prev1790.prev1783.V1783_OUT = OUT_DIR
    prev1997.prev1991.prev1989.prev1936.prev1929.prev1792.prev1790.prev1783.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev1997.prev1991.prev1989.prev1936.prev1929.prev1792.prev1790.prev1783.DEFAULT_REPORT_PATH = REPORT_PATH
    prev = prev1997.prev1991.prev1989.prev1936.prev1929.prev1792.prev1790.prev1783.prev
    prev.OUT_DIR = OUT_DIR
    prev.PROPERTY_RUNTIME_DIR = OUT_DIR / "property-runtime"
    prev.PROPERTY_ROOT = prev.PROPERTY_RUNTIME_DIR / "layout" / "dev" / "__properties__"
    prev.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev.REPORT_PATH = REPORT_PATH
    prev.DEFAULT_ARGS = [
        "--cycle",
        "V1999",
        "--decision",
        "v1999-downstream-cascade-source-build-pass",
        "--cycle-label",
        "v1999",
        "--init-version",
        "0.9.182",
        "--init-build",
        "v1999-downstream-cascade",
        "--out-dir",
        str(OUT_DIR),
        "--init-binary",
        str(OUT_DIR / "init_v1999_downstream_cascade"),
        "--helper-binary",
        str(OUT_DIR / "a90_android_execns_probe_v369"),
        "--ramdisk-cpio",
        str(OUT_DIR / "ramdisk_v1999_downstream_cascade.cpio"),
        "--boot-image",
        str(OUT_DIR / "boot_linux_v1999_downstream_cascade.img"),
        "--wifi-test-klog-prefix",
        "A90v1999",
        "--wifi-test-disable",
        "/cache/native-init-wifi-test-boot-v1999.disable",
        "--wifi-test-log",
        "/cache/native-init-wifi-test-boot-v1999.log",
        "--wifi-test-summary",
        "/cache/native-init-wifi-test-boot-v1999.summary",
        "--wifi-test-helper-result",
        "/cache/native-init-wifi-test-boot-v1999-helper.result",
        "--wifi-test-pid",
        "/cache/native-init-wifi-test-boot-v1999.pid",
        "--wifi-test-watcher-pid",
        "/cache/native-init-wifi-test-boot-v1999-supervisor.pid",
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
        "# Native Init V1999 Downstream Cascade Source Build",
        "",
        "## Summary",
        "",
        "- Cycle: `V1999`",
        "- Type: source/build-only rollbackable internal-modem downstream cascade artifact",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: helper v369 keeps the readonly wlanmdsp bridge and readwrite tmpfs bridge, removes the V1997 tftp ptrace, and raises the helper window to 75s so the stock CNSS/WLFW consumer chain can run after WLAN-PD UP.",
        "- Manifest: `tmp/wifi/v1999-downstream-cascade-test-boot/manifest.json`",
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
        "- Kept: clean-DSP companion, service managers, `pm-service`, `/dev/subsys_modem` holder, `cnss_diag`, stock `cnss-daemon`, `rmt_storage`, `tftp_server`, `pd-mapper`, firmware mounts, readonly RFS bridge, readwrite tmpfs bridge, and klog/ICNSS lower-window summaries.",
        "- Removed: the V1997/V1998 late tftp_server ptrace, so the downstream consumer path is not stopped while WLAN-PD tries to publish WLFW.",
        "- Live discriminator: WLAN-PD UP followed by WLFW service69/cap/BDF/FW-ready/wlan0, or WLAN-PD UP plus confirmed bridges but no WLFW publication after a long post-UP hold.",
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
    base = prev1997.prev1991.prev1989.prev1936.prev1929.prev1792.prev1790.prev1783.prev
    base.base.EXPECTED_HELPER_MARKER = EXPECTED_HELPER_MARKER
    base.base.EXPECTED_HELPER_SHA256 = EXPECTED_HELPER_SHA256
    base.render_report = render_report
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())

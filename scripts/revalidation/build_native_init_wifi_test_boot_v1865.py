#!/usr/bin/env python3
"""Build V1865 route-fixed private SDX50M cnss-daemon mount test boot."""

from __future__ import annotations

from pathlib import Path

import build_native_init_wifi_test_boot_v1846 as prev1846


REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1865-sdx50m-private-mount-routefix-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v1865/dev/__properties__"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1865_SDX50M_PRIVATE_MOUNT_ROUTEFIX_SOURCE_BUILD_2026-06-03.md"
)
PRIVATE_CNSS_PATH = "/cache/bin/cnss-daemon.sdx50m"


def configure_base() -> None:
    prev1846.configure_base()
    prev1846.OUT_DIR = OUT_DIR
    prev1846.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev1846.REPORT_PATH = REPORT_PATH
    prev1846.prev1792.OUT_DIR = OUT_DIR
    prev1846.prev1792.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev1846.prev1792.REPORT_PATH = REPORT_PATH
    prev1846.prev1792.prev1790.OUT_DIR = OUT_DIR
    prev1846.prev1792.prev1790.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev1846.prev1792.prev1790.REPORT_PATH = REPORT_PATH
    prev1846.prev1792.prev1790.prev1783.V1783_OUT = OUT_DIR
    prev1846.prev1792.prev1790.prev1783.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev1846.prev1792.prev1790.prev1783.DEFAULT_REPORT_PATH = REPORT_PATH
    base = prev1846.prev1792.prev1790.prev1783.prev
    base.OUT_DIR = OUT_DIR
    base.PROPERTY_RUNTIME_DIR = OUT_DIR / "property-runtime"
    base.PROPERTY_ROOT = base.PROPERTY_RUNTIME_DIR / "layout" / "dev" / "__properties__"
    base.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    base.REPORT_PATH = REPORT_PATH
    base.DEFAULT_ARGS = [
        "--cycle",
        "V1865",
        "--decision",
        "v1865-sdx50m-private-mount-routefix-source-build-pass",
        "--cycle-label",
        "v1865",
        "--init-version",
        "0.9.167",
        "--init-build",
        "v1865-sdx50m-private-mount-routefix",
        "--out-dir",
        str(OUT_DIR),
        "--init-binary",
        str(OUT_DIR / "init_v1865_sdx50m_private_mount_routefix"),
        "--helper-binary",
        str(OUT_DIR / "a90_android_execns_probe_v356"),
        "--ramdisk-cpio",
        str(OUT_DIR / "ramdisk_v1865_sdx50m_private_mount_routefix.cpio"),
        "--boot-image",
        str(OUT_DIR / "boot_linux_v1865_sdx50m_private_mount_routefix.img"),
        "--wifi-test-klog-prefix",
        "A90v1865",
        "--wifi-test-disable",
        "/cache/native-init-wifi-test-boot-v1865.disable",
        "--wifi-test-log",
        "/cache/native-init-wifi-test-boot-v1865.log",
        "--wifi-test-summary",
        "/cache/native-init-wifi-test-boot-v1865.summary",
        "--wifi-test-helper-result",
        "/cache/native-init-wifi-test-boot-v1865-helper.result",
        "--wifi-test-pid",
        "/cache/native-init-wifi-test-boot-v1865.pid",
        "--wifi-test-watcher-pid",
        "/cache/native-init-wifi-test-boot-v1865-supervisor.pid",
        "--wifi-test-watch-sec",
        "90",
        "--wifi-test-supervise-helper",
        "--wifi-test-supervisor-timeout-sec",
        "120",
        "--wifi-test-firmware-mounts",
        "--wifi-test-mount-debugfs",
        "--wifi-test-property-root",
        REMOTE_PROPERTY_ROOT,
        "--wifi-test-helper-mode",
        "wlan-pd-post-pm-lower-state-observer",
        "--wifi-test-private-cnss-daemon-sdx50m",
        "--wifi-test-private-cnss-daemon-path",
        PRIVATE_CNSS_PATH,
    ]


def render_report(manifest: dict[str, object]) -> str:
    wifi = manifest["wifi_test"]
    property_runtime = manifest["cnss_nonlog_property_runtime"]
    check_lines = [
        f"- `{item['name']}`: `{item['actual']}` in `{item['context']}`"
        for item in property_runtime["checks"]
    ]
    labels = ", ".join(f"`{label}`" for label in prev1846.OPEN_CONTEXT_LABELS)
    return "\n".join([
        "# Native Init V1865 SDX50M Private Mount Routefix Source Build",
        "",
        "## Summary",
        "",
        "- Cycle: `V1865`",
        "- Type: source/build-only rollbackable v356 lower-state observer with private SDX50M cnss-daemon bind mount on the active firmware-serve route",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: V1864 proved the V1863 live handoff reached the firmware-serve/lower-observer route without emitting `private_cnss_daemon.*`; V1865 adds the private mount flags to that active PID1 branch.",
        "- Manifest: `tmp/wifi/v1865-sdx50m-private-mount-routefix-test-boot/manifest.json`",
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
        f"- Private CNSS mount: `{wifi['private_cnss_daemon_sdx50m']}` path `{wifi['private_cnss_daemon_path']}`",
        "- Active PID1 firmware-serve branch now carries `--pm-observer-private-cnss-daemon-sdx50m` and `--private-cnss-daemon-path`.",
        "- The private mount remains namespace-local; it does not write `/vendor` and depends on the remote cache artifact already verified by V1862.",
        f"- PM-service open-context labels retained: {labels}.",
        "- Lower-state observer guardrails remain: no direct `/dev/subsys_esoc0` open, no fake ONLINE, no eSoC notify/BOOT_DONE, no forced RC1, no PCI rescan/bind, no PMIC/GPIO/GDSC writes, no Wi-Fi HAL, no scan/connect, no credentials, no DHCP/routes, and no external ping.",
        "",
        "## Expected Live Discriminator",
        "",
        "- `private-mount-bind-failed`: active branch still failed to materialize the namespace-local bind mount; stop before live bridge interpretation.",
        "- `private-mount-sdx50m-selected`: SDX50M private daemon path executed and changed PM selection; inspect lower publication before connect.",
        "- `private-mount-lower-publication-progress`: WLFW service 69, BDF, MHI, or `wlan0` appears; stop before Wi-Fi HAL/scan/connect.",
        "- `private-mount-pre-wifi-gap`: private mount works but WLFW service 69 and `wlan0` still remain absent.",
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
    base = prev1846.prev1792.prev1790.prev1783.prev
    base.render_report = render_report
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())

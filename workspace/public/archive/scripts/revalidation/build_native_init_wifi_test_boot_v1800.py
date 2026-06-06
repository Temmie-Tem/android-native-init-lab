#!/usr/bin/env python3
"""Build V1800 WLAN-PD PM-service devnode projection test boot."""

from __future__ import annotations

from pathlib import Path

import build_native_init_wifi_test_boot_v1792 as prev1792


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1800-pm-service-devnode-projection-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v1800/dev/__properties__"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1800_PM_SERVICE_DEVNODE_PROJECTION_SOURCE_BUILD_2026-06-03.md"
)


def configure_base() -> None:
    prev1792.configure_base()
    prev1792.OUT_DIR = OUT_DIR
    prev1792.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev1792.REPORT_PATH = REPORT_PATH
    prev1792.prev1790.OUT_DIR = OUT_DIR
    prev1792.prev1790.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev1792.prev1790.REPORT_PATH = REPORT_PATH
    prev1792.prev1790.prev1783.V1783_OUT = OUT_DIR
    prev1792.prev1790.prev1783.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev1792.prev1790.prev1783.DEFAULT_REPORT_PATH = REPORT_PATH
    prev = prev1792.prev1790.prev1783.prev
    prev.OUT_DIR = OUT_DIR
    prev.PROPERTY_RUNTIME_DIR = OUT_DIR / "property-runtime"
    prev.PROPERTY_ROOT = prev.PROPERTY_RUNTIME_DIR / "layout" / "dev" / "__properties__"
    prev.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev.REPORT_PATH = REPORT_PATH
    prev.DEFAULT_ARGS = [
        "--cycle",
        "V1800",
        "--decision",
        "v1800-pm-service-devnode-projection-source-build-pass",
        "--cycle-label",
        "v1800",
        "--init-version",
        "0.9.150",
        "--init-build",
        "v1800-pm-service-devnode-projection",
        "--out-dir",
        str(OUT_DIR),
        "--init-binary",
        str(OUT_DIR / "init_v1800_pm_service_devnode_projection"),
        "--helper-binary",
        str(OUT_DIR / "a90_android_execns_probe_v341"),
        "--ramdisk-cpio",
        str(OUT_DIR / "ramdisk_v1800_pm_service_devnode_projection.cpio"),
        "--boot-image",
        str(OUT_DIR / "boot_linux_v1800_pm_service_devnode_projection.img"),
        "--wifi-test-klog-prefix",
        "A90v1800",
        "--wifi-test-disable",
        "/cache/native-init-wifi-test-boot-v1800.disable",
        "--wifi-test-log",
        "/cache/native-init-wifi-test-boot-v1800.log",
        "--wifi-test-summary",
        "/cache/native-init-wifi-test-boot-v1800.summary",
        "--wifi-test-helper-result",
        "/cache/native-init-wifi-test-boot-v1800-helper.result",
        "--wifi-test-pid",
        "/cache/native-init-wifi-test-boot-v1800.pid",
        "--wifi-test-watcher-pid",
        "/cache/native-init-wifi-test-boot-v1800-supervisor.pid",
        "--wifi-test-watch-sec",
        "75",
        "--wifi-test-supervise-helper",
        "--wifi-test-supervisor-timeout-sec",
        "105",
        "--wifi-test-firmware-mounts",
        "--wifi-test-mount-debugfs",
        "--wifi-test-property-root",
        REMOTE_PROPERTY_ROOT,
        "--wifi-test-helper-mode",
        "wlan-pd-service-object-devnode-projection-trigger",
    ]


def render_report(manifest: dict[str, object]) -> str:
    wifi = manifest["wifi_test"]
    property_runtime = manifest["cnss_nonlog_property_runtime"]
    check_lines = [
        f"- `{item['name']}`: `{item['actual']}` in `{item['context']}`"
        for item in property_runtime["checks"]
    ]
    return "\n".join([
        "# Native Init V1800 PM-service Devnode Projection Source Build",
        "",
        "## Summary",
        "",
        "- Cycle: `V1800`",
        "- Type: source/build-only rollbackable WLAN-PD PM-service private-dev projection test boot artifact",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: helper v341 adds a scoped service-object route variant that projects only the two V1799-proven absent PM-service candidate char nodes (`subsys_esoc0` and `subsys_modem`) into the private Android `/dev` tree before `pm-service` starts.",
        "- Manifest: `tmp/wifi/v1800-pm-service-devnode-projection-test-boot/manifest.json`",
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
        "- Base route remains the bounded service-object route: service managers, firmware-serve stack, `pm_proxy_helper`, `pm-service`, `/dev/subsys_modem` holder, `cnss_diag`, and stock `cnss-daemon`.",
        "- Added projection only: setup reads `/sys/class/subsys/subsys_esoc0/dev` and `/sys/class/subsys/subsys_modem/dev`, then creates private char nodes `subsys_esoc0` and `subsys_modem` with mode `0640` and owner/group `system`.",
        "- Added early observer: `wifi_companion_start.private_node.subsys_esoc0.*` and `wifi_companion_start.private_node.subsys_modem.*` record private-dev status before child startup.",
        "- Retained observer: the V1798 final no-open `wlan_pd_service_object_visible_trigger.devnode_access.*` block remains present.",
        "- Still excluded: `esoc-0` projection, `/dev/subsys_esoc0` open, forced RC1, fake-ONLINE, full `pm-proxy`, `boot_wlan`, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping.",
        "",
        "## Expected Live Discriminator",
        "",
        "- V1801 should run one rollbackable live gate with this artifact and classify whether PM-service reaches supported-list commit, still fails despite visible private nodes, or loses route safety.",
        "- `list-commit-progress`: PM-service list commit becomes nonzero; stop before restart-PD request, WLAN-PD cascade, Wi-Fi HAL, or scan/connect.",
        "- `projection-visible-still-fails`: early private-node fields show both char nodes but PM-service still hits init-fail/list-commit `0`; inspect process-domain or ioctl/open behavior without opening `/dev/subsys_esoc0` in the runner.",
        "- `projection-setup-failed`: early private-node fields are missing or non-char; return to sysfs/dev projection setup.",
        "- `safety-regression`: any hard-stop field regresses; roll back and stop.",
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
    base = prev1792.prev1790.prev1783.prev
    base.render_report = render_report
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())

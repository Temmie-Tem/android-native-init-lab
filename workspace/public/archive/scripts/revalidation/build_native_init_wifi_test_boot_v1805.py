#!/usr/bin/env python3
"""Build V1805 WLAN-PD post-PM lower-state observer test boot."""

from __future__ import annotations

from pathlib import Path

import build_native_init_wifi_test_boot_v1792 as prev1792


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1805-post-pm-lower-state-observer-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v1805/dev/__properties__"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1805_POST_PM_LOWER_STATE_OBSERVER_SOURCE_BUILD_2026-06-03.md"
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
        "V1805",
        "--decision",
        "v1805-post-pm-lower-state-observer-source-build-pass",
        "--cycle-label",
        "v1805",
        "--init-version",
        "0.9.151",
        "--init-build",
        "v1805-post-pm-lower-state-observer",
        "--out-dir",
        str(OUT_DIR),
        "--init-binary",
        str(OUT_DIR / "init_v1805_post_pm_lower_state_observer"),
        "--helper-binary",
        str(OUT_DIR / "a90_android_execns_probe_v342"),
        "--ramdisk-cpio",
        str(OUT_DIR / "ramdisk_v1805_post_pm_lower_state_observer.cpio"),
        "--boot-image",
        str(OUT_DIR / "boot_linux_v1805_post_pm_lower_state_observer.img"),
        "--wifi-test-klog-prefix",
        "A90v1805",
        "--wifi-test-disable",
        "/cache/native-init-wifi-test-boot-v1805.disable",
        "--wifi-test-log",
        "/cache/native-init-wifi-test-boot-v1805.log",
        "--wifi-test-summary",
        "/cache/native-init-wifi-test-boot-v1805.summary",
        "--wifi-test-helper-result",
        "/cache/native-init-wifi-test-boot-v1805-helper.result",
        "--wifi-test-pid",
        "/cache/native-init-wifi-test-boot-v1805.pid",
        "--wifi-test-watcher-pid",
        "/cache/native-init-wifi-test-boot-v1805-supervisor.pid",
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
    ]


def render_report(manifest: dict[str, object]) -> str:
    wifi = manifest["wifi_test"]
    property_runtime = manifest["cnss_nonlog_property_runtime"]
    check_lines = [
        f"- `{item['name']}`: `{item['actual']}` in `{item['context']}`"
        for item in property_runtime["checks"]
    ]
    return "\n".join([
        "# Native Init V1805 Post-PM Lower-state Observer Source Build",
        "",
        "## Summary",
        "",
        "- Cycle: `V1805`",
        "- Type: source/build-only rollbackable WLAN-PD post-PM lower-state observer test boot artifact",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: helper v342 keeps the V1800 private-dev PM-service projection route and adds a compact no-write lower-state sampler after the PM vote boundary.",
        "- Manifest: `tmp/wifi/v1805-post-pm-lower-state-observer-test-boot/manifest.json`",
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
        "- Base route remains the V1800 bounded service-object route: service managers, firmware-serve stack, `pm_proxy_helper`, `pm-service`, `/dev/subsys_modem` holder, `cnss_diag`, and stock `cnss-daemon`.",
        "- Retained projection: private Android `/dev` receives only `subsys_esoc0` and `subsys_modem` char nodes from sysfs major/minor metadata before `pm-service` starts; the runner still does not open `/dev/subsys_esoc0`.",
        "- Added observer: `wlan_pd_post_pm_lower_state_observer.after_holder_start.*` captures an immediate compact read-only lower-state sample.",
        "- Added observer window: `wlan_pd_post_pm_lower_state_observer.post_listener_window.*` captures 12 samples at 500 ms spacing after the bounded service-notifier listener path.",
        "- Captured fields are read-only: mss/mdm3 states and crash counts, mdm status/errfatal IRQ totals, PCI/MHI/rpmsg/msm_subsys counts, MHI pipe presence, and `wlan0` presence.",
        "- Still excluded: `esoc-0` projection, `/dev/subsys_esoc0` open, forced RC1, fake-ONLINE, full `pm-proxy`, `boot_wlan`, restart-PD request, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, and PMIC/GPIO/GDSC writes.",
        "",
        "## Expected Live Discriminator",
        "",
        "- V1806 should run one rollbackable live gate with this artifact and classify whether post-PM lower-state sampling shows mdm3 or IRQ/MHI progress after PM client connect, or confirms a stable `mdm3=OFFLINING` stall.",
        "- `lower-progress`: mdm3 leaves `OFFLINING`, mdm status IRQ increases, MHI appears, WLFW service 69 appears, or `wlan0` appears; stop before Wi-Fi HAL/scan/connect.",
        "- `stable-mdm3-offlining`: PM register/connect still succeeds but all compact samples keep mdm3 `OFFLINING`, MHI absent, WLFW service 69 absent, and `wlan0` absent; route next to host/source classification of the PM-service-owned lower continuation.",
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

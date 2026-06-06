#!/usr/bin/env python3
"""Build V1903 internal-modem service-notifier passive-edge observer test boot."""

from __future__ import annotations

from pathlib import Path

import build_native_init_wifi_test_boot_v1792 as prev1792


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1903-servnotif-passive-edge-observer-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v1903/dev/__properties__"
EXPECTED_HELPER_MARKER = "a90_android_execns_probe v359"
EXPECTED_HELPER_SHA256 = "6d69287158a12b47b8e8d795e9ee3cc3401380a9c905adf5cd5f3e2b75f7711c"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1903_SERVNOTIF_PASSIVE_EDGE_OBSERVER_SOURCE_BUILD_2026-06-03.md"
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
        "V1903",
        "--decision",
        "v1903-servnotif-passive-edge-observer-source-build-pass",
        "--cycle-label",
        "v1903",
        "--init-version",
        "0.9.172",
        "--init-build",
        "v1903-servnotif-passive-edge-observer",
        "--out-dir",
        str(OUT_DIR),
        "--init-binary",
        str(OUT_DIR / "init_v1903_servnotif_passive_edge_observer"),
        "--helper-binary",
        str(OUT_DIR / "a90_android_execns_probe_v359"),
        "--ramdisk-cpio",
        str(OUT_DIR / "ramdisk_v1903_servnotif_passive_edge_observer.cpio"),
        "--boot-image",
        str(OUT_DIR / "boot_linux_v1903_servnotif_passive_edge_observer.img"),
        "--wifi-test-klog-prefix",
        "A90v1903",
        "--wifi-test-disable",
        "/cache/native-init-wifi-test-boot-v1903.disable",
        "--wifi-test-log",
        "/cache/native-init-wifi-test-boot-v1903.log",
        "--wifi-test-summary",
        "/cache/native-init-wifi-test-boot-v1903.summary",
        "--wifi-test-helper-result",
        "/cache/native-init-wifi-test-boot-v1903-helper.result",
        "--wifi-test-pid",
        "/cache/native-init-wifi-test-boot-v1903.pid",
        "--wifi-test-watcher-pid",
        "/cache/native-init-wifi-test-boot-v1903-supervisor.pid",
        "--wifi-test-watch-sec",
        "120",
        "--wifi-test-supervise-helper",
        "--wifi-test-supervisor-timeout-sec",
        "150",
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
        "# Native Init V1903 Service-notifier Passive-edge Observer Source Build",
        "",
        "## Summary",
        "",
        "- Cycle: `V1903`",
        "- Type: source/build-only rollbackable internal-modem service-notifier passive-edge observer test boot artifact",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: V1902 selected the internal modem service-notifier root-service state-up edge as the remaining boundary; this artifact keeps the proven post-PM lower observer and updates it to helper v359 without SDX50M, PCIe, eSoC, delayed degraded-boot sampler, or GDSC paths.",
        "- Manifest: `tmp/wifi/v1903-servnotif-passive-edge-observer-test-boot/manifest.json`",
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
        "- Internal modem route only: `/dev/subsys_modem` post-vote observer, service-locator domain-list, service-notifier listener, WLFW QRTR readback, and bounded AF_QIPCRTR passive poll/recv surfaces.",
        "- Klog discriminator fields retained: `wlan_pd_post_pm_lower_handoff_klog.*.raw_count_service_notifier_new_server`, `raw_count_180_service_text`, `raw_count_74_service_text`, `raw_count_wlan_pd_text`, and last-line snapshots.",
        "- Helper v359 disables the V1880 delayed `post_powerup_delayed` sampler by default; this keeps V1903 anchored to the normal internal-modem boot window instead of the degraded 257s SDX50M/PCIe/MHI path.",
        "- Stop condition: service 74, `wlan_pd`, WLFW service 69, requested `wlanmdsp`, or `wlan0` appears; do not proceed to HAL/scan/connect in this unit.",
        "- Excluded by construction: private SDX50M mount, `/dev/subsys_esoc0` open, eSoC notify/BOOT_DONE, PCI rescan/bind, platform unbind, PMIC/GPIO/GDSC writes, forced RC1/case, restart-PD request, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping.",
        "",
        "## Expected Live Discriminator",
        "",
        "- `servnotif-passive-edge-progress-readonly-stop`: service74, `wlan_pd`, WLFW service 69, requested `wlanmdsp`, or `wlan0` appears; stop before connect.",
        "- `servnotif-new-server-180-only-stateup-edge-absent`: service-notifier new-server/service180 is visible, but service74/`wlan_pd`/WLFW69/`wlan0` stay absent and listener state remains `uninit`.",
        "- `servnotif-passive-edge-incomplete`: bounded fields were collected but do not match a fixed absence/progress discriminator.",
        "- `safety-regression`: any hard-stop side effect appears; stop and roll back.",
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
    base.base.EXPECTED_HELPER_MARKER = EXPECTED_HELPER_MARKER
    base.base.EXPECTED_HELPER_SHA256 = EXPECTED_HELPER_SHA256
    base.render_report = render_report
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())

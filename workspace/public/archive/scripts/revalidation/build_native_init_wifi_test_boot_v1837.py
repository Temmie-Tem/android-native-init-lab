#!/usr/bin/env python3
"""Build V1837 WLAN-PD lower-continuation sampler test boot."""

from __future__ import annotations

from pathlib import Path

import build_native_init_wifi_test_boot_v1792 as prev1792


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1837-wlan-pd-lower-continuation-sampler-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v1837/dev/__properties__"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1837_WLAN_PD_LOWER_CONTINUATION_SAMPLER_SOURCE_BUILD_2026-06-03.md"
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
        "V1837",
        "--decision",
        "v1837-wlan-pd-lower-continuation-sampler-source-build-pass",
        "--cycle-label",
        "v1837",
        "--init-version",
        "0.9.162",
        "--init-build",
        "v1837-wlan-pd-lower-continuation-sampler",
        "--out-dir",
        str(OUT_DIR),
        "--init-binary",
        str(OUT_DIR / "init_v1837_wlan_pd_lower_continuation_sampler"),
        "--helper-binary",
        str(OUT_DIR / "a90_android_execns_probe_v353"),
        "--ramdisk-cpio",
        str(OUT_DIR / "ramdisk_v1837_wlan_pd_lower_continuation_sampler.cpio"),
        "--boot-image",
        str(OUT_DIR / "boot_linux_v1837_wlan_pd_lower_continuation_sampler.img"),
        "--wifi-test-klog-prefix",
        "A90v1837",
        "--wifi-test-disable",
        "/cache/native-init-wifi-test-boot-v1837.disable",
        "--wifi-test-log",
        "/cache/native-init-wifi-test-boot-v1837.log",
        "--wifi-test-summary",
        "/cache/native-init-wifi-test-boot-v1837.summary",
        "--wifi-test-helper-result",
        "/cache/native-init-wifi-test-boot-v1837-helper.result",
        "--wifi-test-pid",
        "/cache/native-init-wifi-test-boot-v1837.pid",
        "--wifi-test-watcher-pid",
        "/cache/native-init-wifi-test-boot-v1837-supervisor.pid",
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
        "# Native Init V1837 WLAN-PD Lower-Continuation Sampler Source Build",
        "",
        "## Summary",
        "",
        "- Cycle: `V1837`",
        "- Type: source/build-only rollbackable WLAN-PD lower-continuation sampler test boot artifact",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: helper v353 keeps the V1834/V1835 bounded lower route and adds read-only PMIC/GDSC focus samples inside the same WLAN-PD post-PM lower observer path.",
        "- Manifest: `tmp/wifi/v1837-wlan-pd-lower-continuation-sampler-test-boot/manifest.json`",
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
        "- Base route remains the bounded lower handoff observer and retains the unbound, node-zero bind, observed-local-node bind, and bound passive poll/recv QRTR snapshots.",
        "- Added read-only PMIC/GDSC focus sample prefixes: `pm_service_trigger_observer.response_sample.wlan_pd_after_holder_start.*` and `pm_service_trigger_observer.response_sample.wlan_pd_after_post_listener_window.*`.",
        "- These samples reuse the existing PMIC/GDSC transition observer surface only as a no-write lower-state sampler for mdm3/ext-SDX50M prerequisites, GPIO 135/142 target-line state, PMIC soft-reset line state, PCIe/GDSC state, MHI presence, and `wlan0` presence.",
        "- Explicit non-actions in the reused sample: `gpiochip_line_request_executed=0`, `pmic_write_executed=0`, and `esoc_ioctl_executed=0`.",
        "- Still excluded: direct `/dev/subsys_esoc0` open, fake-ONLINE, eSoC notify/BOOT_DONE, PCI rescan/bind, platform unbind, PMIC/GPIO/GDSC writes, `boot_wlan`, restart-PD request, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping.",
        "",
        "## Expected Live Discriminator",
        "",
        "- V1838 should run one rollbackable live gate with this artifact only if the read-only lower-continuation sampler is accepted as the next bounded surface.",
        "- `lower-continuation-static-gap`: mdm3/ext-SDX50M, PMIC/GDSC, MHI, WLFW/service 69, and `wlan0` remain unchanged from V1834/V1836; stop and classify the remaining prerequisite gap.",
        "- `pmic-gdsc-or-mdm-status-progress`: one of the PMIC/GDSC, mdm3, IRQ, or PCIe prerequisite surfaces changes during the guarded holder/listener windows; stop and classify the transition.",
        "- `mhi-wlfw-wlan0-progress`: MHI, WLFW service 69, `wlan0`, WLAN-PD UP, or service 74 appears; stop before Wi-Fi HAL/scan/connect.",
        "- `safety-regression`: any forbidden side effect appears; stop and roll back.",
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

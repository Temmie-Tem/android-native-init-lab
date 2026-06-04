#!/usr/bin/env python3
"""Build V2071 native WLAN-PD memory-device DIAG test boot."""

from __future__ import annotations

from pathlib import Path

import build_native_init_wifi_test_boot_v2068 as prev2068


REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v2071-diag-wlan-pd-memory-device-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v2071/dev/__properties__"
EXPECTED_HELPER_MARKER = "a90_android_execns_probe v399"
EXPECTED_HELPER_SHA256 = "e68173735dce517322d58ae6b78f31b8aa7e26ab07223794213825b9016b6bc8"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V2071_DIAG_WLAN_PD_MEMORY_DEVICE_SOURCE_BUILD_2026-06-04.md"
)
HELPER_FLAGS = (
    *prev2068.HELPER_FLAGS,
    "-DA90_WIFI_TEST_BOOT_DIAG_WLAN_PD_MEMORY_DEVICE_PROBE=1",
)


def configure_base() -> None:
    prev2068.OUT_DIR = OUT_DIR
    prev2068.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev2068.REPORT_PATH = REPORT_PATH
    prev2068.EXPECTED_HELPER_MARKER = EXPECTED_HELPER_MARKER
    prev2068.EXPECTED_HELPER_SHA256 = EXPECTED_HELPER_SHA256
    prev2068.HELPER_FLAGS = HELPER_FLAGS
    prev2068.configure_base()

    base = prev2068.prev2038.prev2008.prev2006.build_base_module()
    args = list(base.DEFAULT_ARGS)
    replacements = {
        "--cycle": "V2071",
        "--decision": "v2071-diag-wlan-pd-memory-device-source-build-pass",
        "--cycle-label": "v2071",
        "--init-version": "0.9.214",
        "--init-build": "v2071-diag-wlan-pd-memory-device",
        "--out-dir": str(OUT_DIR),
        "--init-binary": str(OUT_DIR / "init_v2071_diag_wlan_pd_memory_device"),
        "--helper-binary": str(OUT_DIR / "a90_android_execns_probe_v399_diag_wlan_pd_memory_device"),
        "--ramdisk-cpio": str(OUT_DIR / "ramdisk_v2071_diag_wlan_pd_memory_device.cpio"),
        "--boot-image": str(OUT_DIR / "boot_linux_v2071_diag_wlan_pd_memory_device.img"),
        "--wifi-test-klog-prefix": "A90v2071",
        "--wifi-test-disable": "/cache/native-init-wifi-test-boot-v2071.disable",
        "--wifi-test-log": "/cache/native-init-wifi-test-boot-v2071.log",
        "--wifi-test-summary": "/cache/native-init-wifi-test-boot-v2071.summary",
        "--wifi-test-helper-result": "/cache/native-init-wifi-test-boot-v2071-helper.result",
        "--wifi-test-pid": "/cache/native-init-wifi-test-boot-v2071.pid",
        "--wifi-test-watcher-pid": "/cache/native-init-wifi-test-boot-v2071-supervisor.pid",
        "--wifi-test-property-root": REMOTE_PROPERTY_ROOT,
    }
    for key, value in replacements.items():
        prev2068.prev2038.prev2008.prev2006.set_arg(args, key, value)
    base.DEFAULT_ARGS = args


def render_report(manifest: dict[str, object]) -> str:
    wifi = manifest["wifi_test"]
    property_runtime = manifest["cnss_nonlog_property_runtime"]
    check_lines = [
        f"- `{item['name']}`: `{item['actual']}` in `{item['context']}`"
        for item in property_runtime["checks"]
    ]
    return "\n".join([
        "# Native Init V2071 DIAG WLAN-PD Memory-Device Source Build",
        "",
        "## Summary",
        "",
        "- Cycle: `V2071`",
        "- Type: source/build-only rollbackable internal-modem route with V2069 DCI WLAN masks plus a query-gated WLAN-PD memory-device DIAG session",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: helper v399 keeps the V2068 route and adds a `DIAG_IOCTL_QUERY_PD_LOGGING`-gated `DIAG_IOCTL_SWITCH_LOGGING` request for `DIAG_CON_UPD_WLAN` into `MEMORY_DEVICE_MODE`. The memory-device probe borrows the existing DCI `/dev/diag` fd, avoiding the duplicate-open failure mode, and never issues USB/PCIE restore, broad masks, DCI stream config, QMI sends, ptrace, AP-side strace, or QRTR matrices.",
        "- Manifest: `tmp/wifi/v2071-diag-wlan-pd-memory-device-test-boot/manifest.json`",
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
        "- Observer: passive private `/dev/socket/logdw`; compact PerMgr register/vote uprobes; private `/dev/diag` DCI support/register/read/deinit plus bounded WLAN target masks; borrowed-fd WLAN-PD memory-device session after PD query success.",
        "- Switch scope: `req_mode=MEMORY_DEVICE_MODE`, `peripheral_mask=DIAG_CON_UPD_WLAN`, `pd_mask=DIAG_CON_UPD_WLAN`, `device_mask=DIAG_MSM_MASK`.",
        "- Kept: clean-DSP companion, service managers, `pm-service`, `/dev/subsys_modem` holder, `cnss_diag`, stock `cnss-daemon`, `rmt_storage`, `tftp_server`, `pd-mapper`, firmware mounts, fallback readonly RFS bridge, readwrite tmpfs bridge, persist-RFS tmpfs mirrors, cap/BDF/cal probes, post-cal indication probes, and long lower-window hold.",
        "- Excluded: USB/PCIE/global DIAG restore, broad DIAG masks, DCI stream config, passive DIAG replay, boot-time QRTR matrix, rild/cnss/pm-service multi-strace, `tftp_server` ptrace, private SDX50M route, `/dev/subsys_esoc0` open, eSoC notify/BOOT_DONE, PCI rescan/bind, platform unbind, PMIC/GPIO/GDSC/regulator writes, forced RC1/case, restart-PD request, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, and firmware partition writes.",
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
    base = prev2068.prev2038.prev2008.prev2006.build_base_module()
    base.base.EXPECTED_HELPER_MARKER = EXPECTED_HELPER_MARKER
    base.base.EXPECTED_HELPER_SHA256 = EXPECTED_HELPER_SHA256
    prev2068.prev2038.patch_helper_builder(base)
    base.render_report = render_report
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())

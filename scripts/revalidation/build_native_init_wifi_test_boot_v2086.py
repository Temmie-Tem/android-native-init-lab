#!/usr/bin/env python3
"""Build V2086 native macloader MAC-source WLAN-PD trigger test boot."""

from __future__ import annotations

from pathlib import Path

import build_native_init_wifi_test_boot_v2082 as prev2082


REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v2086-mac-source-bridge-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v2086/dev/__properties__"
EXPECTED_HELPER_MARKER = "a90_android_execns_probe v406"
EXPECTED_HELPER_SHA256 = "e57b01e33ddcf317a6e81edc8f4e97cafcfce55edcc72bc2daa6713aa78b4106"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V2086_MAC_SOURCE_BRIDGE_SOURCE_BUILD_2026-06-05.md"
)
HELPER_FLAGS = (
    *prev2082.HELPER_FLAGS,
    "-DA90_WIFI_TEST_BOOT_MACLOADER_PRE_CNSS=1",
    "-DA90_WIFI_TEST_BOOT_MACLOADER_MAC_SOURCE_BRIDGE=1",
)


def configure_base() -> None:
    prev2082.OUT_DIR = OUT_DIR
    prev2082.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev2082.REPORT_PATH = REPORT_PATH
    prev2082.EXPECTED_HELPER_MARKER = EXPECTED_HELPER_MARKER
    prev2082.EXPECTED_HELPER_SHA256 = EXPECTED_HELPER_SHA256
    prev2082.HELPER_FLAGS = HELPER_FLAGS
    prev2082.configure_base()

    base = prev2082.prev2080.prev2058.prev2038.prev2008.prev2006.build_base_module()
    args = list(base.DEFAULT_ARGS)
    replacements = {
        "--cycle": "V2086",
        "--decision": "v2086-mac-source-bridge-source-build-pass",
        "--cycle-label": "v2086",
        "--init-version": "0.9.222",
        "--init-build": "v2086-mac-source-bridge",
        "--out-dir": str(OUT_DIR),
        "--init-binary": str(OUT_DIR / "init_v2086_mac_source_bridge"),
        "--helper-binary": str(OUT_DIR / "a90_android_execns_probe_v406_mac_source_bridge"),
        "--ramdisk-cpio": str(OUT_DIR / "ramdisk_v2086_mac_source_bridge.cpio"),
        "--boot-image": str(OUT_DIR / "boot_linux_v2086_mac_source_bridge.img"),
        "--wifi-test-klog-prefix": "A90v2086",
        "--wifi-test-disable": "/cache/native-init-wifi-test-boot-v2086.disable",
        "--wifi-test-log": "/cache/native-init-wifi-test-boot-v2086.log",
        "--wifi-test-summary": "/cache/native-init-wifi-test-boot-v2086.summary",
        "--wifi-test-helper-result": "/cache/native-init-wifi-test-boot-v2086-helper.result",
        "--wifi-test-pid": "/cache/native-init-wifi-test-boot-v2086.pid",
        "--wifi-test-watcher-pid": "/cache/native-init-wifi-test-boot-v2086-supervisor.pid",
        "--wifi-test-property-root": REMOTE_PROPERTY_ROOT,
    }
    for key, value in replacements.items():
        prev2082.prev2080.prev2058.prev2038.prev2008.prev2006.set_arg(args, key, value)
    base.DEFAULT_ARGS = args


def render_report(manifest: dict[str, object]) -> str:
    wifi = manifest["wifi_test"]
    property_runtime = manifest["cnss_nonlog_property_runtime"]
    check_lines = [
        f"- `{item['name']}`: `{item['actual']}` in `{item['context']}`"
        for item in property_runtime["checks"]
    ]
    return "\n".join([
        "# Native Init V2086 Macloader MAC-Source Bridge Source Build",
        "",
        "## Summary",
        "",
        "- Cycle: `V2086`",
        "- Type: source/build-only native route that adds one Android-parity `macloader` active driver-start child before `cnss-daemon` and exposes read-only EFS/persist plus ICNSS sysfs to `macloader`.",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: helper v406 keeps the V2082 light internal-modem route and adds `/vendor/bin/hw/macloader` with Android init parity before `cnss-daemon`, wiring `/mnt/vendor/efs/wifi/.mac.info`, `/sys/wifi`, `/sys/kernel/boot_wlan`, and `/persist/WCNSS_qcom_wlan_nv.bin` into the private namespace (`user wifi`, `group wifi inet net_raw net_admin`, `NET_ADMIN NET_RAW SYS_MODULE`, `u:r:macloader:s0`). This is an explicit active driver-start gate with read-only EFS/persist exposure, not a read-only observer; it still excludes Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, DIAG, strace, QRTR matrix, QMI send, eSoC/PCIe/GDSC/PMIC/GPIO paths, and firmware/partition writes.",
        "- Manifest: `tmp/wifi/v2086-mac-source-bridge-test-boot/manifest.json`",
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
        "- Order: `qrtr_ns,pd_mapper,rmt_storage,tftp_server,subsys_modem_holder,cnss_diag,macloader,cnss_daemon`.",
        "- Kept: clean-DSP companion, `pm-service`, read-only MAC-source bridge, `/dev/subsys_modem` holder, stock `cnss_diag`, stock `cnss-daemon`, `rmt_storage`, `tftp_server`, `pd-mapper`, Android-parity RFS bridges, cap/BDF/cal probes, PerMgr/WLFW compact summaries, post-BDF surface summary, and long lower-window hold.",
        "- Excluded: Wi-Fi HAL, wificond, supplicant, hostapd, scan/connect, credentials, DHCP/routes, external ping, DIAG mask/log-mode, passive DIAG, boot-time QRTR matrix, rild/cnss/pm-service strace, `tftp_server` ptrace, private SDX50M route, `/dev/subsys_esoc0`, eSoC notify/BOOT_DONE, PCI rescan/bind, platform unbind, PMIC/GPIO/GDSC/regulator writes, forced RC1/case, and firmware/partition writes.",
        "",
        "## Property Runtime",
        "",
        *check_lines,
        "",
        "## Safety Scope",
        "",
        "This build script performed host-side source/build work only. The eventual V2087 live handoff is rollbackable and intentionally permits the Android `macloader` driver-start action while still forbidding Wi-Fi HAL/scan/connect/credentials/DHCP/routes/external ping and off-path modem/PCIe/GDSC/PMIC/GPIO actions.",
        "",
    ])


def main() -> int:
    configure_base()
    base = prev2082.prev2080.prev2058.prev2038.prev2008.prev2006.build_base_module()
    base.base.EXPECTED_HELPER_MARKER = EXPECTED_HELPER_MARKER
    base.base.EXPECTED_HELPER_SHA256 = EXPECTED_HELPER_SHA256
    prev2082.prev2080.prev2058.prev2038.patch_helper_builder(base)
    base.render_report = render_report
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())

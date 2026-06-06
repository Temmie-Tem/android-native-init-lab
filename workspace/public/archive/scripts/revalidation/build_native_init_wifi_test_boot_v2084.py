#!/usr/bin/env python3
"""Build V2084 native macloader-pre-CNSS WLAN-PD trigger test boot."""

from __future__ import annotations

from pathlib import Path

import build_native_init_wifi_test_boot_v2082 as prev2082


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v2084-macloader-pre-cnss-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v2084/dev/__properties__"
EXPECTED_HELPER_MARKER = "a90_android_execns_probe v405"
EXPECTED_HELPER_SHA256 = "7fb0e09b064d854809f1e0e1b3bd602f65f9d9bd59d3183778ce7cd6971ed2fb"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V2084_MACLOADER_PRE_CNSS_SOURCE_BUILD_2026-06-05.md"
)
HELPER_FLAGS = (
    *prev2082.HELPER_FLAGS,
    "-DA90_WIFI_TEST_BOOT_MACLOADER_PRE_CNSS=1",
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
        "--cycle": "V2084",
        "--decision": "v2084-macloader-pre-cnss-source-build-pass",
        "--cycle-label": "v2084",
        "--init-version": "0.9.220",
        "--init-build": "v2084-macloader-pre-cnss",
        "--out-dir": str(OUT_DIR),
        "--init-binary": str(OUT_DIR / "init_v2084_macloader_pre_cnss"),
        "--helper-binary": str(OUT_DIR / "a90_android_execns_probe_v405_macloader_pre_cnss"),
        "--ramdisk-cpio": str(OUT_DIR / "ramdisk_v2084_macloader_pre_cnss.cpio"),
        "--boot-image": str(OUT_DIR / "boot_linux_v2084_macloader_pre_cnss.img"),
        "--wifi-test-klog-prefix": "A90v2084",
        "--wifi-test-disable": "/cache/native-init-wifi-test-boot-v2084.disable",
        "--wifi-test-log": "/cache/native-init-wifi-test-boot-v2084.log",
        "--wifi-test-summary": "/cache/native-init-wifi-test-boot-v2084.summary",
        "--wifi-test-helper-result": "/cache/native-init-wifi-test-boot-v2084-helper.result",
        "--wifi-test-pid": "/cache/native-init-wifi-test-boot-v2084.pid",
        "--wifi-test-watcher-pid": "/cache/native-init-wifi-test-boot-v2084-supervisor.pid",
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
        "# Native Init V2084 Macloader Pre-CNSS Source Build",
        "",
        "## Summary",
        "",
        "- Cycle: `V2084`",
        "- Type: source/build-only native route that adds one Android-parity `macloader` active driver-start child before `cnss-daemon`.",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: helper v405 keeps the V2082 light internal-modem route and adds only `/vendor/bin/hw/macloader` with Android init parity (`user wifi`, `group wifi inet net_raw net_admin`, `NET_ADMIN NET_RAW SYS_MODULE`, `u:r:macloader:s0`) before `cnss-daemon`. This is an explicit active driver-start gate, not a read-only observer; it still excludes Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, DIAG, strace, QRTR matrix, QMI send, eSoC/PCIe/GDSC/PMIC/GPIO paths, and firmware/partition writes.",
        "- Manifest: `tmp/wifi/v2084-macloader-pre-cnss-test-boot/manifest.json`",
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
        "- Kept: clean-DSP companion, `pm-service`, `/dev/subsys_modem` holder, stock `cnss_diag`, stock `cnss-daemon`, `rmt_storage`, `tftp_server`, `pd-mapper`, Android-parity RFS bridges, cap/BDF/cal probes, PerMgr/WLFW compact summaries, post-BDF surface summary, and long lower-window hold.",
        "- Excluded: Wi-Fi HAL, wificond, supplicant, hostapd, scan/connect, credentials, DHCP/routes, external ping, DIAG mask/log-mode, passive DIAG, boot-time QRTR matrix, rild/cnss/pm-service strace, `tftp_server` ptrace, private SDX50M route, `/dev/subsys_esoc0`, eSoC notify/BOOT_DONE, PCI rescan/bind, platform unbind, PMIC/GPIO/GDSC/regulator writes, forced RC1/case, and firmware/partition writes.",
        "",
        "## Property Runtime",
        "",
        *check_lines,
        "",
        "## Safety Scope",
        "",
        "This build script performed host-side source/build work only. The eventual V2085 live handoff is rollbackable and intentionally permits the Android `macloader` driver-start action while still forbidding Wi-Fi HAL/scan/connect/credentials/DHCP/routes/external ping and off-path modem/PCIe/GDSC/PMIC/GPIO actions.",
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

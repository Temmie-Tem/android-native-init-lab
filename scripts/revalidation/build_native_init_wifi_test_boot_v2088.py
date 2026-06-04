#!/usr/bin/env python3
"""Build V2088 native macloader syscall-trace discriminator test boot."""

from __future__ import annotations

from pathlib import Path

import build_native_init_wifi_test_boot_v2086 as prev2086


REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v2088-macloader-syscall-trace-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v2088/dev/__properties__"
EXPECTED_HELPER_MARKER = "a90_android_execns_probe v407"
EXPECTED_HELPER_SHA256 = "313315ff66d23c1f19993f1ed487763bc3f5d9e1c2768014b96d74eeb1868b92"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V2088_MACLOADER_SYSCALL_TRACE_SOURCE_BUILD_2026-06-05.md"
)
HELPER_FLAGS = (
    *prev2086.HELPER_FLAGS,
    "-DA90_WIFI_TEST_BOOT_MACLOADER_SYSCALL_TRACE=1",
)


def configure_base() -> None:
    prev2086.OUT_DIR = OUT_DIR
    prev2086.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev2086.REPORT_PATH = REPORT_PATH
    prev2086.EXPECTED_HELPER_MARKER = EXPECTED_HELPER_MARKER
    prev2086.EXPECTED_HELPER_SHA256 = EXPECTED_HELPER_SHA256
    prev2086.HELPER_FLAGS = HELPER_FLAGS
    prev2086.configure_base()

    base = prev2086.prev2082.prev2080.prev2058.prev2038.prev2008.prev2006.build_base_module()
    args = list(base.DEFAULT_ARGS)
    replacements = {
        "--cycle": "V2088",
        "--decision": "v2088-macloader-syscall-trace-source-build-pass",
        "--cycle-label": "v2088",
        "--init-version": "0.9.223",
        "--init-build": "v2088-macloader-syscall-trace",
        "--out-dir": str(OUT_DIR),
        "--init-binary": str(OUT_DIR / "init_v2088_macloader_syscall_trace"),
        "--helper-binary": str(OUT_DIR / "a90_android_execns_probe_v407_macloader_syscall_trace"),
        "--ramdisk-cpio": str(OUT_DIR / "ramdisk_v2088_macloader_syscall_trace.cpio"),
        "--boot-image": str(OUT_DIR / "boot_linux_v2088_macloader_syscall_trace.img"),
        "--wifi-test-klog-prefix": "A90v2088",
        "--wifi-test-disable": "/cache/native-init-wifi-test-boot-v2088.disable",
        "--wifi-test-log": "/cache/native-init-wifi-test-boot-v2088.log",
        "--wifi-test-summary": "/cache/native-init-wifi-test-boot-v2088.summary",
        "--wifi-test-helper-result": "/cache/native-init-wifi-test-boot-v2088-helper.result",
        "--wifi-test-pid": "/cache/native-init-wifi-test-boot-v2088.pid",
        "--wifi-test-watcher-pid": "/cache/native-init-wifi-test-boot-v2088-supervisor.pid",
        "--wifi-test-property-root": REMOTE_PROPERTY_ROOT,
    }
    for key, value in replacements.items():
        prev2086.prev2082.prev2080.prev2058.prev2038.prev2008.prev2006.set_arg(args, key, value)
    base.DEFAULT_ARGS = args


def render_report(manifest: dict[str, object]) -> str:
    wifi = manifest["wifi_test"]
    property_runtime = manifest["cnss_nonlog_property_runtime"]
    check_lines = [
        f"- `{item['name']}`: `{item['actual']}` in `{item['context']}`"
        for item in property_runtime["checks"]
    ]
    return "\n".join([
        "# Native Init V2088 Macloader Syscall Trace Source Build",
        "",
        "## Summary",
        "",
        "- Cycle: `V2088`",
        "- Type: source/build-only bounded `macloader` syscall discriminator over the V2086 MAC-source bridge route.",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: helper v407 keeps the light internal-modem route and adds single-child `macloader` ptrace only, proving whether `macloader` opens/reads `.mac.info` and writes the real `/sys/wifi/mac_addr` node. It hashes short read/write payload samples and records colon/hex shape only; it does not emit raw MAC bytes.",
        "- Manifest: `tmp/wifi/v2088-macloader-syscall-trace-test-boot/manifest.json`",
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
        "- Added: real-node `statfs` snapshots for `/sys/wifi/mac_addr`, `/sys/kernel/boot_wlan/boot_wlan` existence/writability, `/data/vendor/conn` namespace availability, and focused `macloader` syscall records.",
        "- Kept: clean-DSP companion, `pm-service`, read-only MAC-source bridge, `/dev/subsys_modem` holder, stock `cnss_diag`, stock `cnss-daemon`, `rmt_storage`, `tftp_server`, `pd-mapper`, Android-parity RFS bridges, cap/BDF/cal probes, PerMgr/WLFW compact summaries, post-BDF surface summary, and long lower-window hold.",
        "- Excluded: Wi-Fi HAL, wificond, supplicant, hostapd, scan/connect, credentials, DHCP/routes, external ping, DIAG mask/log-mode, passive DIAG, boot-time QRTR matrix, rild/cnss/pm-service strace, `tftp_server` ptrace, `cnss-daemon` ptrace, private SDX50M route, `/dev/subsys_esoc0`, eSoC notify/BOOT_DONE, PCI rescan/bind, platform unbind, PMIC/GPIO/GDSC/regulator writes, forced RC1/case, raw MAC payload logging, and firmware/partition writes.",
        "",
        "## Property Runtime",
        "",
        *check_lines,
        "",
        "## Safety Scope",
        "",
        "This build script performed host-side source/build work only. The eventual V2089 live handoff is rollbackable and intentionally permits only the Android `macloader` driver-start action plus single-child `macloader` ptrace. EFS/persist exposure remains read-only, RFS bridges are namespace-local, and MAC assignment is treated as a bounded downstream/cosmetic falsifier rather than the primary modem producer gate.",
        "",
    ])


def main() -> int:
    configure_base()
    base = prev2086.prev2082.prev2080.prev2058.prev2038.prev2008.prev2006.build_base_module()
    base.base.EXPECTED_HELPER_MARKER = EXPECTED_HELPER_MARKER
    base.base.EXPECTED_HELPER_SHA256 = EXPECTED_HELPER_SHA256
    prev2086.prev2082.prev2080.prev2058.prev2038.patch_helper_builder(base)
    base.render_report = render_report
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())

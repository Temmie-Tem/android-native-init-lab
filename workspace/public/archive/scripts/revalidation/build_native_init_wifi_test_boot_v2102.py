#!/usr/bin/env python3
"""Build V2102 native TFTP process namespace audit test boot."""

from __future__ import annotations

from pathlib import Path

import build_native_init_wifi_test_boot_v2100 as prev2100


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v2102-tftp-process-namespace-audit-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v2102/dev/__properties__"
EXPECTED_HELPER_MARKER = "a90_android_execns_probe v412"
EXPECTED_HELPER_SHA256 = "3e59a0b0de541afb2b604d3d3f23f1e0b7b18a51c659804674d20d88234d8473"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V2102_TFTP_PROCESS_NAMESPACE_AUDIT_SOURCE_BUILD_2026-06-05.md"
)
HELPER_FLAGS = (
    *prev2100.HELPER_FLAGS,
    "-DA90_WIFI_TEST_BOOT_TFTP_PROCESS_NAMESPACE_AUDIT=1",
)


def configure_base() -> None:
    prev2100.OUT_DIR = OUT_DIR
    prev2100.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev2100.REPORT_PATH = REPORT_PATH
    prev2100.EXPECTED_HELPER_MARKER = EXPECTED_HELPER_MARKER
    prev2100.EXPECTED_HELPER_SHA256 = EXPECTED_HELPER_SHA256
    prev2100.HELPER_FLAGS = HELPER_FLAGS
    prev2100.configure_base()

    base = prev2100.prev2097.prev2095.prev2082.prev2080.prev2058.prev2038.prev2008.prev2006.build_base_module()
    args = list(base.DEFAULT_ARGS)
    replacements = {
        "--cycle": "V2102",
        "--decision": "v2102-tftp-process-namespace-audit-source-build-pass",
        "--cycle-label": "v2102",
        "--init-version": "0.9.228",
        "--init-build": "v2102-tftp-process-namespace-audit",
        "--out-dir": str(OUT_DIR),
        "--init-binary": str(OUT_DIR / "init_v2102_tftp_process_namespace_audit"),
        "--helper-binary": str(OUT_DIR / "a90_android_execns_probe_v412_tftp_process_namespace_audit"),
        "--ramdisk-cpio": str(OUT_DIR / "ramdisk_v2102_tftp_process_namespace_audit.cpio"),
        "--boot-image": str(OUT_DIR / "boot_linux_v2102_tftp_process_namespace_audit.img"),
        "--wifi-test-klog-prefix": "A90v2102",
        "--wifi-test-disable": "/cache/native-init-wifi-test-boot-v2102.disable",
        "--wifi-test-log": "/cache/native-init-wifi-test-boot-v2102.log",
        "--wifi-test-summary": "/cache/native-init-wifi-test-boot-v2102.summary",
        "--wifi-test-helper-result": "/cache/native-init-wifi-test-boot-v2102-helper.result",
        "--wifi-test-pid": "/cache/native-init-wifi-test-boot-v2102.pid",
        "--wifi-test-watcher-pid": "/cache/native-init-wifi-test-boot-v2102-supervisor.pid",
        "--wifi-test-property-root": REMOTE_PROPERTY_ROOT,
    }
    for key, value in replacements.items():
        prev2100.prev2097.prev2095.prev2082.prev2080.prev2058.prev2038.prev2008.prev2006.set_arg(args, key, value)
    base.DEFAULT_ARGS = args


def render_report(manifest: dict[str, object]) -> str:
    wifi = manifest["wifi_test"]
    property_runtime = manifest["cnss_nonlog_property_runtime"]
    check_lines = [
        f"- `{item['name']}`: `{item['actual']}` in `{item['context']}`"
        for item in property_runtime["checks"]
    ]
    return "\n".join([
        "# Native Init V2102 TFTP Process Namespace Audit Source Build",
        "",
        "## Summary",
        "",
        "- Cycle: `V2102`",
        "- Type: source/build-only follow-up to V2101, adding a read-only `/proc/<tftp_server>/root` and `mountinfo` audit for the stock `tftp_server` process.",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: helper v412 keeps the V2100 light internal-modem route and adds no ptrace, no QMI send, and no extra service actors. It only records whether the running stock `tftp_server` process actually sees the namespace-local `/mnt/vendor/persist/rfs` auto-dir targets.",
        "- Manifest: `tmp/wifi/v2102-tftp-process-namespace-audit-test-boot/manifest.json`",
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
        "- Kept: V2100 route, readonly/readwrite RFS bridges, vendor-owned tombstone dirs, persist-RFS auto-dir targets, `tftp_server` logdw sink, focused PerMgr/WLFW summaries, post-BDF surface summary, and long lower-window hold.",
        "- Added: read-only process-root/mountinfo audit for the already-running stock `tftp_server` process.",
        "- Excluded: `tftp_server` ptrace, AP QMI send, DIAG, QRTR matrix, RIL/cnss/pm-service strace, macloader retry, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, and off-path SDX50M/eSoC/PCIe/GDSC/PMIC/GPIO actions.",
        "",
        "## Property Runtime",
        "",
        *check_lines,
        "",
        "## Safety Scope",
        "",
        "This build script performed host-side source/build work only. The live handoff should decide whether `tftp_server` is in the same filesystem view as the helper-created persist-RFS auto-dir targets.",
        "",
    ])


def main() -> int:
    configure_base()
    base = prev2100.prev2097.prev2095.prev2082.prev2080.prev2058.prev2038.prev2008.prev2006.build_base_module()
    base.base.EXPECTED_HELPER_MARKER = EXPECTED_HELPER_MARKER
    base.base.EXPECTED_HELPER_SHA256 = EXPECTED_HELPER_SHA256
    prev2100.prev2097.prev2095.prev2082.prev2080.prev2058.prev2038.patch_helper_builder(base)
    base.render_report = render_report
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())

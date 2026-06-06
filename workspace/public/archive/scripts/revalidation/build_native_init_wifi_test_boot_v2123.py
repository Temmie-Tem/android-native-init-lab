#!/usr/bin/env python3
"""Build V2123 native shared-server-info route with corrected WLFW indication labels."""

from __future__ import annotations

from pathlib import Path

import build_native_init_wifi_test_boot_v2120 as prev2120


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v2123-wlfw-indication-label-fix-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v2123/dev/__properties__"
EXPECTED_HELPER_MARKER = "a90_android_execns_probe v420"
EXPECTED_HELPER_SHA256 = "e5f6a31724a429fd34cc10df3cc9633325a07637b3ac225d2b90db860ae6a3ae"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V2123_WLFW_INDICATION_LABEL_FIX_SOURCE_BUILD_2026-06-05.md"
)
HELPER_FLAGS = (
    *prev2120.HELPER_FLAGS,
    "-DA90_WIFI_TEST_BOOT_WLFW_INDICATION_LABEL_FIX=1",
)


def configure_base() -> None:
    prev2120.OUT_DIR = OUT_DIR
    prev2120.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev2120.REPORT_PATH = REPORT_PATH
    prev2120.EXPECTED_HELPER_MARKER = EXPECTED_HELPER_MARKER
    prev2120.EXPECTED_HELPER_SHA256 = EXPECTED_HELPER_SHA256
    prev2120.HELPER_FLAGS = HELPER_FLAGS
    prev2120.configure_base()

    base = prev2120.prev2112.prev2108.prev2106.prev2102.prev2100.prev2097.prev2095.prev2082.prev2080.prev2058.prev2038.prev2008.prev2006.build_base_module()
    args = list(base.DEFAULT_ARGS)
    replacements = {
        "--cycle": "V2123",
        "--decision": "v2123-wlfw-indication-label-fix-source-build-pass",
        "--cycle-label": "v2123",
        "--init-version": "0.9.236",
        "--init-build": "v2123-wlfw-indication-label-fix",
        "--out-dir": str(OUT_DIR),
        "--init-binary": str(OUT_DIR / "init_v2123_wlfw_indication_label_fix"),
        "--helper-binary": str(OUT_DIR / "a90_android_execns_probe_v420_wlfw_indication_label_fix"),
        "--ramdisk-cpio": str(OUT_DIR / "ramdisk_v2123_wlfw_indication_label_fix.cpio"),
        "--boot-image": str(OUT_DIR / "boot_linux_v2123_wlfw_indication_label_fix.img"),
        "--wifi-test-klog-prefix": "A90v2123",
        "--wifi-test-disable": "/cache/native-init-wifi-test-boot-v2123.disable",
        "--wifi-test-log": "/cache/native-init-wifi-test-boot-v2123.log",
        "--wifi-test-summary": "/cache/native-init-wifi-test-boot-v2123.summary",
        "--wifi-test-helper-result": "/cache/native-init-wifi-test-boot-v2123-helper.result",
        "--wifi-test-pid": "/cache/native-init-wifi-test-boot-v2123.pid",
        "--wifi-test-watcher-pid": "/cache/native-init-wifi-test-boot-v2123-supervisor.pid",
        "--wifi-test-property-root": REMOTE_PROPERTY_ROOT,
    }
    for key, value in replacements.items():
        prev2120.prev2112.prev2108.prev2106.prev2102.prev2100.prev2097.prev2095.prev2082.prev2080.prev2058.prev2038.prev2008.prev2006.set_arg(args, key, value)
    base.DEFAULT_ARGS = args


def render_report(manifest: dict[str, object]) -> str:
    wifi = manifest["wifi_test"]
    property_runtime = manifest["cnss_nonlog_property_runtime"]
    check_lines = [
        f"- `{item['name']}`: `{item['actual']}` in `{item['context']}`"
        for item in property_runtime["checks"]
    ]
    return "\n".join([
        "# Native Init V2123 WLFW Indication Label Fix Source Build",
        "",
        "## Summary",
        "",
        "- Cycle: `V2123`",
        "- Type: source/build-only observability correction for the post-cal WLFW indication edge.",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: helper v420 keeps the V2120 shared-server-info route unchanged and only corrects the Samsung `cnss-daemon` uprobe labels: `0xe2f0` is MSA-ready (`msg 0x2b`) and `0xe328` is FW-memory-ready (`msg 0x37`).",
        "- Manifest: `tmp/wifi/v2123-wlfw-indication-label-fix-test-boot/manifest.json`",
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
        "- Kept: V2120 dual-RFS read-only/read-write/shared bridges, root lower companions, PerMgr/WLFW focused summaries, post-BDF summary, and long lower-window hold.",
        "- Added: corrected focused fields `saw_msg37`, `msa_ready_flag.hit_count`, and `fw_mem_ready_flag.hit_count`.",
        "- Excluded: route behavior changes, tftp identity changes, OTA ruleset fabrication, mcfg optimization, macloader retry, DIAG, boot-time QRTR matrix, rild/cnss/pm-service strace, `tftp_server` ptrace, AP QMI send, `/dev/subsys_esoc0`, eSoC notify/BOOT_DONE, PCI rescan/bind, platform unbind, PMIC/GPIO/GDSC/regulator writes, forced RC1/case, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, and firmware/partition writes.",
        "",
        "## Branch",
        "",
        "- If `msg 0x21` appears but kernel FW_READY/`wlan0` does not, classify the gap as userspace FW_READY indication seen but not converted into kernel FW_READY.",
        "- If MSA-ready appears without FW-memory-ready, classify the gap at the MSA-to-FW-memory-ready indication edge.",
        "- If artifact validation fails, do not run the live handoff.",
        "",
        "## Property Runtime",
        "",
        *check_lines,
        "",
        "## Safety Scope",
        "",
        "This build script performed host-side source/build work only. It did not issue live device commands, flash, reboot, run Wi-Fi HAL, scan/connect, use credentials, configure DHCP/routes, perform external ping, write `/dev/wlan`, write `qcwlanstate`, open `/dev/subsys_esoc0`, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE` spoof, run PCI rescan/platform bind-unbind, use DIAG, ptrace `tftp_server`, send AP QMI payloads, or write firmware/boot/device partitions.",
        "",
    ])


def main() -> int:
    configure_base()
    base = prev2120.prev2112.prev2108.prev2106.prev2102.prev2100.prev2097.prev2095.prev2082.prev2080.prev2058.prev2038.prev2008.prev2006.build_base_module()
    base.base.EXPECTED_HELPER_MARKER = EXPECTED_HELPER_MARKER
    base.base.EXPECTED_HELPER_SHA256 = EXPECTED_HELPER_SHA256
    prev2120.prev2112.prev2108.prev2106.prev2102.prev2100.prev2097.prev2095.prev2082.prev2080.prev2058.prev2038.patch_helper_builder(base)
    base.render_report = render_report
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())

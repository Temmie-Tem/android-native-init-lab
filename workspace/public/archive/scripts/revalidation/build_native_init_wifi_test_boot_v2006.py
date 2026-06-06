#!/usr/bin/env python3
"""Build V2006 native post-BDF tail-probe test boot."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import build_native_init_wifi_test_boot_v2004 as prev2004


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v2006-post-bdf-tail-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v2006/dev/__properties__"
EXPECTED_HELPER_MARKER = "a90_android_execns_probe v372"
EXPECTED_HELPER_SHA256 = "954a9130fbc30cc4e4c1d342269d2f23dd77f3cc78e256199dd813c9d2952b00"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V2006_POST_BDF_TAIL_SOURCE_BUILD_2026-06-04.md"
)


def build_base_module() -> Any:
    return prev2004.prev1999.prev1997.prev1991.prev1989.prev1936.prev1929.prev1792.prev1790.prev1783.prev


def set_arg(args: list[str], key: str, value: str) -> None:
    index = args.index(key)
    args[index + 1] = value


def configure_base() -> None:
    prev2004.OUT_DIR = OUT_DIR
    prev2004.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev2004.REPORT_PATH = REPORT_PATH
    prev2004.EXPECTED_HELPER_MARKER = EXPECTED_HELPER_MARKER
    prev2004.EXPECTED_HELPER_SHA256 = EXPECTED_HELPER_SHA256
    prev2004.configure_base()

    base = build_base_module()
    args = list(base.DEFAULT_ARGS)
    replacements = {
        "--cycle": "V2006",
        "--decision": "v2006-post-bdf-tail-source-build-pass",
        "--cycle-label": "v2006",
        "--init-version": "0.9.185",
        "--init-build": "v2006-post-bdf-tail",
        "--out-dir": str(OUT_DIR),
        "--init-binary": str(OUT_DIR / "init_v2006_post_bdf_tail"),
        "--helper-binary": str(OUT_DIR / "a90_android_execns_probe_v372"),
        "--ramdisk-cpio": str(OUT_DIR / "ramdisk_v2006_post_bdf_tail.cpio"),
        "--boot-image": str(OUT_DIR / "boot_linux_v2006_post_bdf_tail.img"),
        "--wifi-test-klog-prefix": "A90v2006",
        "--wifi-test-disable": "/cache/native-init-wifi-test-boot-v2006.disable",
        "--wifi-test-log": "/cache/native-init-wifi-test-boot-v2006.log",
        "--wifi-test-summary": "/cache/native-init-wifi-test-boot-v2006.summary",
        "--wifi-test-helper-result": "/cache/native-init-wifi-test-boot-v2006-helper.result",
        "--wifi-test-pid": "/cache/native-init-wifi-test-boot-v2006.pid",
        "--wifi-test-watcher-pid": "/cache/native-init-wifi-test-boot-v2006-supervisor.pid",
        "--wifi-test-property-root": REMOTE_PROPERTY_ROOT,
    }
    for key, value in replacements.items():
        set_arg(args, key, value)
    base.DEFAULT_ARGS = args


def render_report(manifest: dict[str, object]) -> str:
    wifi = manifest["wifi_test"]
    property_runtime = manifest["cnss_nonlog_property_runtime"]
    check_lines = [
        f"- `{item['name']}`: `{item['actual']}` in `{item['context']}`"
        for item in property_runtime["checks"]
    ]
    return "\n".join([
        "# Native Init V2006 Post-BDF Tail Source Build",
        "",
        "## Summary",
        "",
        "- Cycle: `V2006`",
        "- Type: source/build-only rollbackable internal-modem post-BDF tail-probe artifact",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: helper v372 keeps the V2004 route and adds only post-BDF WLFW cal-report, DMS, status, and version send/return uprobes after V2005 proved BDF QMI success.",
        "- Manifest: `tmp/wifi/v2006-post-bdf-tail-test-boot/manifest.json`",
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
        "- Kept: clean-DSP companion, service managers, `pm-service`, `/dev/subsys_modem` holder, `cnss_diag`, stock `cnss-daemon`, `rmt_storage`, `tftp_server`, `pd-mapper`, firmware mounts, readonly RFS bridge, readwrite tmpfs bridge, and light klog/ICNSS summaries.",
        "- Added: `wlfw_cal_report_*`, `dms_get_wlan_address_*`, `dms_service_request_*`, `wlan_send_status_*`, and `wlan_send_version_*` uprobes.",
        "- Excluded by construction: tftp_server ptrace, boot-time QRTR matrix, rild/cnss/pm-service multi-strace, private SDX50M mount, `/dev/subsys_esoc0` open, eSoC notify/BOOT_DONE, PCI rescan/bind, platform unbind, PMIC/GPIO/GDSC/regulator writes, forced RC1/case, restart-PD request, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping.",
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
    base = build_base_module()
    base.base.EXPECTED_HELPER_MARKER = EXPECTED_HELPER_MARKER
    base.base.EXPECTED_HELPER_SHA256 = EXPECTED_HELPER_SHA256
    base.render_report = render_report
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())

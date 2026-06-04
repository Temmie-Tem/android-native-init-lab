#!/usr/bin/env python3
"""Build V2008 native post-cal indication-probe test boot."""

from __future__ import annotations

from pathlib import Path

import build_native_init_wifi_test_boot_v2006 as prev2006


REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v2008-post-cal-indication-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v2008/dev/__properties__"
EXPECTED_HELPER_MARKER = "a90_android_execns_probe v373"
EXPECTED_HELPER_SHA256 = "474cd69041c3b4ab021bfd9208038ad44cc85efbdabc64efa598bc08c30025ee"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V2008_POST_CAL_INDICATION_SOURCE_BUILD_2026-06-04.md"
)


def configure_base() -> None:
    prev2006.OUT_DIR = OUT_DIR
    prev2006.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev2006.REPORT_PATH = REPORT_PATH
    prev2006.EXPECTED_HELPER_MARKER = EXPECTED_HELPER_MARKER
    prev2006.EXPECTED_HELPER_SHA256 = EXPECTED_HELPER_SHA256
    prev2006.configure_base()

    base = prev2006.build_base_module()
    args = list(base.DEFAULT_ARGS)
    replacements = {
        "--cycle": "V2008",
        "--decision": "v2008-post-cal-indication-source-build-pass",
        "--cycle-label": "v2008",
        "--init-version": "0.9.186",
        "--init-build": "v2008-post-cal-indication",
        "--out-dir": str(OUT_DIR),
        "--init-binary": str(OUT_DIR / "init_v2008_post_cal_indication"),
        "--helper-binary": str(OUT_DIR / "a90_android_execns_probe_v373"),
        "--ramdisk-cpio": str(OUT_DIR / "ramdisk_v2008_post_cal_indication.cpio"),
        "--boot-image": str(OUT_DIR / "boot_linux_v2008_post_cal_indication.img"),
        "--wifi-test-klog-prefix": "A90v2008",
        "--wifi-test-disable": "/cache/native-init-wifi-test-boot-v2008.disable",
        "--wifi-test-log": "/cache/native-init-wifi-test-boot-v2008.log",
        "--wifi-test-summary": "/cache/native-init-wifi-test-boot-v2008.summary",
        "--wifi-test-helper-result": "/cache/native-init-wifi-test-boot-v2008-helper.result",
        "--wifi-test-pid": "/cache/native-init-wifi-test-boot-v2008.pid",
        "--wifi-test-watcher-pid": "/cache/native-init-wifi-test-boot-v2008-supervisor.pid",
        "--wifi-test-property-root": REMOTE_PROPERTY_ROOT,
    }
    for key, value in replacements.items():
        prev2006.set_arg(args, key, value)
    base.DEFAULT_ARGS = args


def render_report(manifest: dict[str, object]) -> str:
    wifi = manifest["wifi_test"]
    property_runtime = manifest["cnss_nonlog_property_runtime"]
    check_lines = [
        f"- `{item['name']}`: `{item['actual']}` in `{item['context']}`"
        for item in property_runtime["checks"]
    ]
    return "\n".join([
        "# Native Init V2008 Post-Cal Indication Source Build",
        "",
        "## Summary",
        "",
        "- Cycle: `V2008`",
        "- Type: source/build-only rollbackable internal-modem post-cal indication-probe artifact",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: helper v373 keeps the V2006 route and adds only `wlfw_service_request` post-cal branch and WLFW QMI indication queue/handler probes after V2007 proved cap/BDF/cal-report success.",
        "- Manifest: `tmp/wifi/v2008-post-cal-indication-test-boot/manifest.json`",
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
        "- Added: `wlfw_worker_*`, `wlfw_qmi_ind_*`, and `wlfw_handle_ind_*` uprobes.",
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
    base = prev2006.build_base_module()
    base.base.EXPECTED_HELPER_MARKER = EXPECTED_HELPER_MARKER
    base.base.EXPECTED_HELPER_SHA256 = EXPECTED_HELPER_SHA256
    base.render_report = render_report
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())

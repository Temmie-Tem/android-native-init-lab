#!/usr/bin/env python3
"""Build V2077 native remote-MDM DIAG bridge poll test boot."""

from __future__ import annotations

from pathlib import Path

import build_native_init_wifi_test_boot_v2073 as prev2073


REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v2077-remote-mdm-diag-bridge-poll-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v2077/dev/__properties__"
EXPECTED_HELPER_MARKER = "a90_android_execns_probe v402"
EXPECTED_HELPER_SHA256 = "68cb51de7685425e5e43346aae21aa9491e8da90291d1dc1ec3caa241433c5a6"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V2077_REMOTE_MDM_DIAG_BRIDGE_POLL_SOURCE_BUILD_2026-06-05.md"
)
HELPER_FLAGS = (
    *prev2073.HELPER_FLAGS,
    "-DA90_WIFI_TEST_BOOT_DIAG_REMOTE_DEV_POLL_PROBE=1",
)


def configure_base() -> None:
    prev2073.OUT_DIR = OUT_DIR
    prev2073.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev2073.REPORT_PATH = REPORT_PATH
    prev2073.EXPECTED_HELPER_MARKER = EXPECTED_HELPER_MARKER
    prev2073.EXPECTED_HELPER_SHA256 = EXPECTED_HELPER_SHA256
    prev2073.HELPER_FLAGS = HELPER_FLAGS
    prev2073.configure_base()

    base = prev2073.prev2071.prev2068.prev2038.prev2008.prev2006.build_base_module()
    args = list(base.DEFAULT_ARGS)
    replacements = {
        "--cycle": "V2077",
        "--decision": "v2077-remote-mdm-diag-bridge-poll-source-build-pass",
        "--cycle-label": "v2077",
        "--init-version": "0.9.217",
        "--init-build": "v2077-remote-mdm-diag-bridge-poll",
        "--out-dir": str(OUT_DIR),
        "--init-binary": str(OUT_DIR / "init_v2077_remote_mdm_diag_bridge_poll"),
        "--helper-binary": str(OUT_DIR / "a90_android_execns_probe_v402_remote_mdm_diag_bridge_poll"),
        "--ramdisk-cpio": str(OUT_DIR / "ramdisk_v2077_remote_mdm_diag_bridge_poll.cpio"),
        "--boot-image": str(OUT_DIR / "boot_linux_v2077_remote_mdm_diag_bridge_poll.img"),
        "--wifi-test-klog-prefix": "A90v2077",
        "--wifi-test-disable": "/cache/native-init-wifi-test-boot-v2077.disable",
        "--wifi-test-log": "/cache/native-init-wifi-test-boot-v2077.log",
        "--wifi-test-summary": "/cache/native-init-wifi-test-boot-v2077.summary",
        "--wifi-test-helper-result": "/cache/native-init-wifi-test-boot-v2077-helper.result",
        "--wifi-test-pid": "/cache/native-init-wifi-test-boot-v2077.pid",
        "--wifi-test-watcher-pid": "/cache/native-init-wifi-test-boot-v2077-supervisor.pid",
        "--wifi-test-property-root": REMOTE_PROPERTY_ROOT,
    }
    for key, value in replacements.items():
        prev2073.prev2071.prev2068.prev2038.prev2008.prev2006.set_arg(args, key, value)
    base.DEFAULT_ARGS = args


def render_report(manifest: dict[str, object]) -> str:
    wifi = manifest["wifi_test"]
    property_runtime = manifest["cnss_nonlog_property_runtime"]
    check_lines = [
        f"- `{item['name']}`: `{item['actual']}` in `{item['context']}`"
        for item in property_runtime["checks"]
    ]
    return "\n".join([
        "# Native Init V2077 Remote-MDM DIAG Bridge Poll Source Build",
        "",
        "## Summary",
        "",
        "- Cycle: `V2077`",
        "- Type: source/build-only rollbackable internal-modem route with V2073 WLAN-PD memory session masks plus a query-only remote-MDM DIAG bridge poll",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: helper v402 keeps the V2073 light observer route and polls borrowed-fd `DIAG_IOCTL_REMOTE_DEV` across the lower window. It records whether the MDM data bridge ever becomes active before any future remote-MDM mask attempt, and does not send remote masks, QMI, USB/PCIE restore, DCI stream config, ptrace, AP-side strace, or QRTR matrices.",
        "- Manifest: `tmp/wifi/v2077-remote-mdm-diag-bridge-poll-test-boot/manifest.json`",
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
        "- Observer: passive private `/dev/socket/logdw`; compact PerMgr register/vote summary retained only as a closed baseline; private `/dev/diag` DCI support/register/read/deinit; bounded WLAN target masks; WLAN-PD memory-device session; session-scoped regular WLAN log/event masks; query-only `DIAG_IOCTL_REMOTE_DEV` remote bridge polling.",
        "- Remote discriminator: `DIAG_IOCTL_REMOTE_DEV` number `32`, `DIAGFWD_MDM` slot `0`, success if any returned remote-device mask has bit `0` set during the lower window.",
        "- Branch: if MDM data bridge is never active, do not send remote masks and close this transport. If it becomes active, a later unit can target that time window with one bounded `USER_SPACE_DATA_TYPE + -MDM` WLAN mask write under a separate report.",
        "- Excluded: remote DIAG mask writes, USB/PCIE/global DIAG restore, broad DIAG masks, DCI stream config, passive DIAG replay, boot-time QRTR matrix, rild/cnss/pm-service multi-strace, `tftp_server` ptrace, private SDX50M route, `/dev/subsys_esoc0` open, eSoC notify/BOOT_DONE, PCI rescan/bind, platform unbind, PMIC/GPIO/GDSC/regulator writes, forced RC1/case, restart-PD request, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, and firmware partition writes.",
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
    base = prev2073.prev2071.prev2068.prev2038.prev2008.prev2006.build_base_module()
    base.base.EXPECTED_HELPER_MARKER = EXPECTED_HELPER_MARKER
    base.base.EXPECTED_HELPER_SHA256 = EXPECTED_HELPER_SHA256
    prev2073.prev2071.prev2068.prev2038.patch_helper_builder(base)
    base.render_report = render_report
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())

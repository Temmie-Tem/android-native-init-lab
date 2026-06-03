#!/usr/bin/env python3
"""Build V1833 QIPCRTR bound poll/recv observer test boot."""

from __future__ import annotations

from pathlib import Path

import build_native_init_wifi_test_boot_v1792 as prev1792


REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1833-qipcrtr-bound-recv-poll-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v1833/dev/__properties__"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1833_QIPCRTR_BOUND_RECV_POLL_SOURCE_BUILD_2026-06-03.md"
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
        "V1833",
        "--decision",
        "v1833-qipcrtr-bound-recv-poll-source-build-pass",
        "--cycle-label",
        "v1833",
        "--init-version",
        "0.9.161",
        "--init-build",
        "v1833-qipcrtr-bound-recv-poll",
        "--out-dir",
        str(OUT_DIR),
        "--init-binary",
        str(OUT_DIR / "init_v1833_qipcrtr_bound_recv_poll"),
        "--helper-binary",
        str(OUT_DIR / "a90_android_execns_probe_v352"),
        "--ramdisk-cpio",
        str(OUT_DIR / "ramdisk_v1833_qipcrtr_bound_recv_poll.cpio"),
        "--boot-image",
        str(OUT_DIR / "boot_linux_v1833_qipcrtr_bound_recv_poll.img"),
        "--wifi-test-klog-prefix",
        "A90v1833",
        "--wifi-test-disable",
        "/cache/native-init-wifi-test-boot-v1833.disable",
        "--wifi-test-log",
        "/cache/native-init-wifi-test-boot-v1833.log",
        "--wifi-test-summary",
        "/cache/native-init-wifi-test-boot-v1833.summary",
        "--wifi-test-helper-result",
        "/cache/native-init-wifi-test-boot-v1833-helper.result",
        "--wifi-test-pid",
        "/cache/native-init-wifi-test-boot-v1833.pid",
        "--wifi-test-watcher-pid",
        "/cache/native-init-wifi-test-boot-v1833-supervisor.pid",
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
        "# Native Init V1833 QIPCRTR Bound Poll/Recv Source Build",
        "",
        "## Summary",
        "",
        "- Cycle: `V1833`",
        "- Type: source/build-only rollbackable QIPCRTR bound socket poll/recv observer test boot artifact",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: helper v352 keeps the bounded lower publication route and adds one observed-local-node AF_QIPCRTR bound socket poll/recv snapshot at `net_window`.",
        "- Manifest: `tmp/wifi/v1833-qipcrtr-bound-recv-poll-test-boot/manifest.json`",
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
        "- Base route remains the bounded lower handoff observer and retains the unbound, node-zero bind, and observed-local-node bind snapshots.",
        "- Added bound poll/recv prefix: `wlan_pd_qipcrtr_bound_recv_poll_state.net_window.*`.",
        "- Added passive operations: protocol summary before open, AF_QIPCRTR/SOCK_DGRAM open, pre-bind `getsockname`, bind using observed local node and port `0`, post-bind `getsockname`, protocol summary before poll, `O_NONBLOCK`, 250 ms `poll(POLLIN)`, `recvfrom` only if `POLLIN`, protocol summary after poll, close, and protocol summary after close.",
        "- Explicit non-actions: `no_connect=1`, `no_send=1`, `no_qrtr_lookup_send=1`, `no_qrtr_control_payload=1`, and `no_service_start=1`.",
        "- Still excluded: direct `/dev/subsys_esoc0` open, fake-ONLINE, eSoC notify/BOOT_DONE, PCI rescan/bind, platform unbind, PMIC/GPIO/GDSC writes, `boot_wlan`, restart-PD request, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping.",
        "",
        "## Expected Live Discriminator",
        "",
        "- V1834 should run one rollbackable live gate with this artifact only if the bound poll/recv snapshot is accepted as the next bounded surface.",
        "- `qipcrtr-bound-recv-poll-timeout-passive`: bind succeeds, no inbound QRTR datagram arrives during the 250 ms window, and service74/wlan_pd still remain absent.",
        "- `qipcrtr-bound-recv-poll-packet-passive`: bind succeeds and one inbound datagram is observed without connect/send/lookup/control traffic; stop for classification.",
        "- `qipcrtr-bound-recv-poll-error`: bind succeeds but `poll` or `recvfrom` errors; capture errno and stop.",
        "- `lower-publication-progress`: service 74, wlan_pd, WLFW service 69, MHI, or `wlan0` appears; stop before Wi-Fi HAL/scan/connect.",
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

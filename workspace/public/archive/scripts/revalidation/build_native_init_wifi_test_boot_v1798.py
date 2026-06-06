#!/usr/bin/env python3
"""Build V1798 WLAN-PD PM-service devnode access observer test boot."""

from __future__ import annotations

from pathlib import Path

import build_native_init_wifi_test_boot_v1792 as prev1792


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1798-pm-service-devnode-access-observer-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v1798/dev/__properties__"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1798_PM_SERVICE_DEVNODE_ACCESS_OBSERVER_SOURCE_BUILD_2026-06-03.md"
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
        "V1798",
        "--decision",
        "v1798-pm-service-devnode-access-observer-source-build-pass",
        "--cycle-label",
        "v1798",
        "--init-version",
        "0.9.149",
        "--init-build",
        "v1798-pm-service-devnode-access-observer",
        "--out-dir",
        str(OUT_DIR),
        "--init-binary",
        str(OUT_DIR / "init_v1798_pm_service_devnode_access_observer"),
        "--helper-binary",
        str(OUT_DIR / "a90_android_execns_probe_v340"),
        "--ramdisk-cpio",
        str(OUT_DIR / "ramdisk_v1798_pm_service_devnode_access_observer.cpio"),
        "--boot-image",
        str(OUT_DIR / "boot_linux_v1798_pm_service_devnode_access_observer.img"),
        "--wifi-test-klog-prefix",
        "A90v1798",
        "--wifi-test-disable",
        "/cache/native-init-wifi-test-boot-v1798.disable",
        "--wifi-test-log",
        "/cache/native-init-wifi-test-boot-v1798.log",
        "--wifi-test-summary",
        "/cache/native-init-wifi-test-boot-v1798.summary",
        "--wifi-test-helper-result",
        "/cache/native-init-wifi-test-boot-v1798-helper.result",
        "--wifi-test-pid",
        "/cache/native-init-wifi-test-boot-v1798.pid",
        "--wifi-test-watcher-pid",
        "/cache/native-init-wifi-test-boot-v1798-supervisor.pid",
        "--wifi-test-watch-sec",
        "75",
        "--wifi-test-supervise-helper",
        "--wifi-test-supervisor-timeout-sec",
        "105",
        "--wifi-test-firmware-mounts",
        "--wifi-test-mount-debugfs",
        "--wifi-test-property-root",
        REMOTE_PROPERTY_ROOT,
        "--wifi-test-helper-mode",
        "wlan-pd-service-object-visible-trigger",
    ]


def render_report(manifest: dict[str, object]) -> str:
    wifi = manifest["wifi_test"]
    property_runtime = manifest["cnss_nonlog_property_runtime"]
    check_lines = [
        f"- `{item['name']}`: `{item['actual']}` in `{item['context']}`"
        for item in property_runtime["checks"]
    ]
    return "\n".join([
        "# Native Init V1798 PM-service Devnode Access Observer Source Build",
        "",
        "## Summary",
        "",
        "- Cycle: `V1798`",
        "- Type: source/build-only rollbackable WLAN-PD PM-service devnode access observer test boot artifact",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: helper v340 keeps the V1795 PM-service count/sample trace observers and adds a no-open, no-mknod private-root `lstat`/`access(F_OK)` status block for both PM-service candidate devnodes (`subsys_esoc0` and `subsys_modem`) in the service-object route.",
        "- Manifest: `tmp/wifi/v1798-pm-service-devnode-access-observer-test-boot/manifest.json`",
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
        "- Base route remains the bounded V1792/V1795 service-object route: service managers, firmware-serve stack, `pm_proxy_helper`, `pm-service`, `/dev/subsys_modem` holder, `cnss_diag`, and stock `cnss-daemon`.",
        "- Added observer only: the route summary now emits `wlan_pd_service_object_visible_trigger.devnode_access.*` plus per-candidate `devnode.sdx50m.*` and `devnode.modem.*` fields.",
        "- The new status uses `lstat` and `access(F_OK)` only; it does not open `/dev/subsys_esoc0`, create nodes, change modes, or attempt repair.",
        "- Still excluded: full `pm-proxy`, `boot_wlan`, restart-PD request, `/dev/subsys_esoc0` open, forced RC1, fake-ONLINE, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping.",
        "",
        "## New Output Fields",
        "",
        "- `wlan_pd_service_object_visible_trigger.devnode_access.open_attempted=0`",
        "- `wlan_pd_service_object_visible_trigger.devnode_access.mknod_attempted=0`",
        "- `wlan_pd_service_object_visible_trigger.devnode.sdx50m.name=subsys_esoc0`",
        "- `wlan_pd_service_object_visible_trigger.devnode.modem.name=subsys_modem`",
        "- Per candidate: `path`, `access_f_ok`, `access_errno`, `lstat_ok`, `lstat_errno`, `char_device`, `major`, `minor`, `mode`, `uid`, and `gid`.",
        "",
        "## Retained Observers",
        "",
        "- `pm_service_init_first_count_load`: `first_count=%x8`",
        "- `pm_service_init_second_count_load`: `second_count=%x8`",
        "- `pm_service_init_first_add_peripheral_call`: `record=%x1 name=+4(%x1):string devnode=+68(%x1):string off_timeout=%x2 ack_timeout=%x3 flags=%x4`",
        "- `pm_service_init_second_add_peripheral_call`: `record=%x1 name=+4(%x1):string devnode=+68(%x1):string off_timeout=%x2 ack_timeout=%x3 flags=%x4`",
        "- PM-service event output still includes `sample_count` and `sample_line_0..3` for each `pm_server_uprobe` event.",
        "- Retained: `pm_server_register_no_peripheral`: `peripheral=+0(%x26):string`",
        "- Retained: `pm_service_add_peripheral_entry`: `record=%x1 name=+4(%x1):string devnode=+68(%x1):string`",
        "- Retained: `pm_service_add_peripheral_known_name`: `record=%x25 name=+0(%x21):string devnode=+68(%x25):string`",
        "- Retained: `pm_service_add_peripheral_init_fail`: `name=+0(%x21):string devnode=+0(%x25):string`",
        "",
        "## Property Runtime",
        "",
        *check_lines,
        "",
        "## Expected Live Discriminator",
        "",
        "- V1799 should run one rollbackable live gate with this artifact and classify whether the PM-service candidates are absent, non-character, mode/owner mismatched, or already visible in the private Android `/dev` tree before any repair.",
        "- `both-devnodes-absent`: `sdx50m` and `modem` both report `lstat_ok=0` / `access_f_ok=0`; return to private-dev materialization source, not PM-service list logic.",
        "- `modem-present-sdx50m-absent`: only `subsys_modem` is present; keep repair scoped to candidate parity and do not open `/dev/subsys_esoc0`.",
        "- `nonchar-or-mode-mismatch`: a path exists but is not a char device or has unexpected mode/owner; classify source of private-dev projection before repair.",
        "- `candidate-visible-but-pm-fails`: helper sees both candidates but PM-service still fails; investigate process-domain/namespace parity without Wi-Fi HAL escalation.",
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

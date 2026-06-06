#!/usr/bin/env python3
"""Build V1679 corrected WLAN-PD firmware-serve test boot with modem holder."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from a90harness.evidence import write_private_text

import build_native_init_wifi_test_boot_v1393 as base


OUT_DIR = base.REPO_ROOT / "tmp" / "wifi" / "v1679-wlan-pd-firmware-serve-modem-holder-test-boot"
REPORT_PATH = (
    base.REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1679_WLAN_PD_FIRMWARE_SERVE_MODEM_HOLDER_SOURCE_BUILD_2026-06-02.md"
)

DEFAULT_ARGS = [
    "--cycle",
    "V1679",
    "--decision",
    "v1679-wlan-pd-firmware-serve-modem-holder-source-build-pass",
    "--cycle-label",
    "v1679",
    "--init-version",
    "0.9.122",
    "--init-build",
    "v1679-wlan-pd-firmware-serve-modem-holder",
    "--out-dir",
    str(OUT_DIR),
    "--init-binary",
    str(OUT_DIR / "init_v1679_wlan_pd_firmware_serve_modem_holder"),
    "--ramdisk-cpio",
    str(OUT_DIR / "ramdisk_v1679_wlan_pd_firmware_serve_modem_holder.cpio"),
    "--boot-image",
    str(OUT_DIR / "boot_linux_v1679_wlan_pd_firmware_serve_modem_holder.img"),
    "--wifi-test-klog-prefix",
    "A90v1679",
    "--wifi-test-disable",
    "/cache/native-init-wifi-test-boot-v1679.disable",
    "--wifi-test-log",
    "/cache/native-init-wifi-test-boot-v1679.log",
    "--wifi-test-summary",
    "/cache/native-init-wifi-test-boot-v1679.summary",
    "--wifi-test-helper-result",
    "/cache/native-init-wifi-test-boot-v1679-helper.result",
    "--wifi-test-pid",
    "/cache/native-init-wifi-test-boot-v1679.pid",
    "--wifi-test-watcher-pid",
    "/cache/native-init-wifi-test-boot-v1679-supervisor.pid",
    "--wifi-test-watch-sec",
    "55",
    "--wifi-test-supervise-helper",
    "--wifi-test-supervisor-timeout-sec",
    "80",
    "--wifi-test-firmware-mounts",
    "--wifi-test-helper-mode",
    "wlan-pd-firmware-serve-gate",
]


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(base.REPO_ROOT))
    except ValueError:
        return str(path)


def render_report(manifest: dict[str, Any]) -> str:
    wifi = manifest["wifi_test"]
    return "\n".join([
        "# Native Init V1679 WLAN-PD Firmware-serve Modem-holder Source Build",
        "",
        "## Summary",
        "",
        "- Cycle: `V1679`",
        "- Type: source/build-only rollbackable WLAN-PD firmware-serve test boot artifact",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: corrected V1676/V1677 gate by adding a modem-only `/dev/subsys_modem` holder to the firmware-serve window",
        f"- Manifest: `{rel(OUT_DIR / 'manifest.json')}`",
        f"- Boot image: `{manifest['boot_image']}`",
        f"- Boot SHA256: `{manifest['boot_sha256']}`",
        f"- Init: `A90 Linux init {manifest['init_version']} ({manifest['init_build']})`",
        f"- Init SHA256: `{manifest['init_sha256']}`",
        f"- Helper marker: `{manifest['helper_marker']}`",
        f"- Helper SHA256: `{manifest['helper_sha256']}`",
        "",
        "## Correction From V1677",
        "",
        "- V1678 host-only audit showed V1677 did not open `/dev/subsys_modem`, so mss/PIL never triggered.",
        "- V1679 keeps the same read-only WLAN-PD firmware-serve contract but inserts a modem-only holder after the companion stack is spawned.",
        "- eSoC/subsys_esoc0, forced RC1, fake-ONLINE, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping remain disabled.",
        "",
        "## Artifact Paths",
        "",
        f"- Log path: `{wifi['log']}`",
        f"- Summary path: `{wifi['summary']}`",
        f"- Helper result path: `{wifi['helper_result']}`",
        "",
    ])


def main() -> int:
    rc = base.main([*DEFAULT_ARGS, *sys.argv[1:]])
    if rc != 0:
        return rc
    manifest_path = OUT_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["pass"] = True
    manifest["source_build_only"] = True
    manifest["device_command"] = False
    manifest["corrects_v1677_trigger_gap"] = True
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_private_text(REPORT_PATH, render_report(manifest))
    print(f"report={rel(REPORT_PATH)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

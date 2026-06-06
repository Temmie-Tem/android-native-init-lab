#!/usr/bin/env python3
"""Build the V1676 corrected WLAN-PD firmware-serve gate test boot artifact."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from a90harness.evidence import write_private_text

import build_native_init_wifi_test_boot_v1393 as base


OUT_DIR = base.REPO_ROOT / "tmp" / "wifi" / "v1676-wlan-pd-firmware-serve-gate-corrected-test-boot"
REPORT_PATH = (
    base.REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1676_WLAN_PD_FIRMWARE_SERVE_GATE_CORRECTED_SOURCE_BUILD_2026-06-02.md"
)

DEFAULT_ARGS = [
    "--cycle",
    "V1676",
    "--decision",
    "v1676-wlan-pd-firmware-serve-gate-corrected-source-build-pass",
    "--cycle-label",
    "v1676",
    "--init-version",
    "0.9.121",
    "--init-build",
    "v1676-wlan-pd-firmware-serve-gate-corrected",
    "--out-dir",
    str(OUT_DIR),
    "--init-binary",
    str(OUT_DIR / "init_v1676_wlan_pd_firmware_serve_gate_corrected"),
    "--ramdisk-cpio",
    str(OUT_DIR / "ramdisk_v1676_wlan_pd_firmware_serve_gate_corrected.cpio"),
    "--boot-image",
    str(OUT_DIR / "boot_linux_v1676_wlan_pd_firmware_serve_gate_corrected.img"),
    "--wifi-test-klog-prefix",
    "A90v1676",
    "--wifi-test-disable",
    "/cache/native-init-wifi-test-boot-v1676.disable",
    "--wifi-test-log",
    "/cache/native-init-wifi-test-boot-v1676.log",
    "--wifi-test-summary",
    "/cache/native-init-wifi-test-boot-v1676.summary",
    "--wifi-test-helper-result",
    "/cache/native-init-wifi-test-boot-v1676-helper.result",
    "--wifi-test-pid",
    "/cache/native-init-wifi-test-boot-v1676.pid",
    "--wifi-test-watcher-pid",
    "/cache/native-init-wifi-test-boot-v1676-supervisor.pid",
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
        "# Native Init V1676 Corrected WLAN-PD Firmware-serve Gate Source Build",
        "",
        "## Summary",
        "",
        "- Cycle: `V1676`",
        "- Type: source/build-only rollbackable WLAN-PD firmware-serve read-only test boot artifact",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: rebuilt the V1674 gate with helper v305 so tftp running state is sampled after observable-child capture",
        f"- Manifest: `{rel(OUT_DIR / 'manifest.json')}`",
        f"- Boot image: `{manifest['boot_image']}`",
        f"- Boot SHA256: `{manifest['boot_sha256']}`",
        f"- Init: `A90 Linux init {manifest['init_version']} ({manifest['init_build']})`",
        f"- Init SHA256: `{manifest['init_sha256']}`",
        f"- Helper marker: `{manifest['helper_marker']}`",
        f"- Helper SHA256: `{manifest['helper_sha256']}`",
        "",
        "## Correction From V1675",
        "",
        "- V1675 label `tqftpserv-not-running` is invalid because summary ran before `composite_capture_observable_children`.",
        "- V1676 moves observable-child capture before `wlan_pd_firmware_serve_gate.*` summary and treats a non-reaped tftp child as running.",
        "- The live gate must be repeated once as V1677; do not use V1675 for technical conclusions.",
        "",
        "## Gate Contract",
        "",
        "- Active path is internal modem WLAN-PD only.",
        "- Companion order: `qrtr_ns,pd_mapper,rmt_storage,tftp_server,cnss_diag,cnss_daemon`.",
        "- No eSoC/subsys_esoc0, forced RC1, fake-ONLINE, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping.",
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
    manifest["supersedes_v1675_label"] = True
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_private_text(REPORT_PATH, render_report(manifest))
    print(f"report={rel(REPORT_PATH)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

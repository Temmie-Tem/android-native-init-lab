#!/usr/bin/env python3
"""Build the V1612 non-stopping per_mgr context-trace Wi-Fi test boot artifact."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from a90harness.evidence import write_private_text

import build_native_init_wifi_test_boot_v1393 as base


OUT_DIR = base.REPO_ROOT / "tmp" / "wifi" / "v1612-per-mgr-nonstop-context-test-boot"
REPORT_PATH = (
    base.REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1612_PER_MGR_NONSTOP_CONTEXT_SOURCE_BUILD_2026-06-02.md"
)

DEFAULT_ARGS = [
    "--cycle",
    "V1612",
    "--decision",
    "v1612-per-mgr-nonstop-context-test-boot-source-build-pass",
    "--cycle-label",
    "v1612",
    "--init-version",
    "0.9.108",
    "--init-build",
    "v1612-per-mgr-nonstop-context",
    "--out-dir",
    str(OUT_DIR),
    "--init-binary",
    str(OUT_DIR / "init_v1612_wifi_test"),
    "--helper-binary",
    str(OUT_DIR / "a90_android_execns_probe_v300"),
    "--ramdisk-cpio",
    str(OUT_DIR / "ramdisk_v1612_wifi_test.cpio"),
    "--boot-image",
    str(OUT_DIR / "boot_linux_v1612_wifi_test.img"),
    "--wifi-test-klog-prefix",
    "A90v1612",
    "--wifi-test-disable",
    "/cache/native-init-wifi-test-boot-v1612.disable",
    "--wifi-test-log",
    "/cache/native-init-wifi-test-boot-v1612.log",
    "--wifi-test-summary",
    "/cache/native-init-wifi-test-boot-v1612.summary",
    "--wifi-test-helper-result",
    "/cache/native-init-wifi-test-boot-v1612-helper.result",
    "--wifi-test-pid",
    "/cache/native-init-wifi-test-boot-v1612.pid",
    "--wifi-test-watcher-pid",
    "/cache/native-init-wifi-test-boot-v1612-supervisor.pid",
    "--wifi-test-watch-sec",
    "120",
    "--wifi-test-supervise-helper",
    "--wifi-test-supervisor-timeout-sec",
    "130",
    "--wifi-test-firmware-mounts",
    "--wifi-test-helper-mode",
    "android-service-window-pm-proxy-contract-pm-first-late-per-proxy-pph-gate-per-mgr-nonstop-context-trace-lower-marker",
]


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(base.REPO_ROOT))
    except ValueError:
        return str(path)


def render_report(manifest: dict[str, Any]) -> str:
    wifi = manifest["wifi_test"]
    return "\n".join([
        "# Native Init V1612 per_mgr Non-stopping Context Source Build",
        "",
        "## Summary",
        "",
        "- Cycle: `V1612`",
        "- Type: source/build-only rollbackable Wi-Fi test boot artifact",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: built the V1604 route with helper v300 and non-stopping `per_mgr` context snapshots",
        f"- Manifest: `{rel(OUT_DIR / 'manifest.json')}`",
        f"- Boot image: `{manifest['boot_image']}`",
        f"- Boot SHA256: `{manifest['boot_sha256']}`",
        f"- Init: `A90 Linux init {manifest['init_version']} ({manifest['init_build']})`",
        f"- Init SHA256: `{manifest['init_sha256']}`",
        f"- Helper marker: `{manifest['helper_marker']}`",
        f"- Helper SHA256: `{manifest['helper_sha256']}`",
        "",
        "## Delta From V1608/V1610",
        "",
        "- Bumps `a90_android_execns_probe` to v300.",
        "- Preserves the PM-first late-per-proxy PPH-gated lower-marker route.",
        "- Retires `--capture-mode ptrace-lite` for `/vendor/bin/pm-service`.",
        "- Keeps the V1604 startup sampler and adds `--allow-android-wifi-service-window-per-mgr-nonstop-context-trace`.",
        "- Captures registry/property/socket/runtime snapshots before and after the `per_mgr` startup sampler without stopping the process.",
        "",
        "## Test-Boot Contract",
        "",
        f"- Log path: `{wifi['log']}`",
        f"- Summary path: `{wifi['summary']}`",
        f"- Helper result path: `{wifi['helper_result']}`",
        f"- Supervisor timeout sec: `{wifi['supervisor_timeout_sec']}`",
        f"- Helper runtime mode: `{wifi['helper_runtime_mode']}`",
        f"- Firmware mounts: `{wifi['firmware_mounts']}`",
        f"- Android service window: `{wifi['android_service_window']}`",
        "",
        "## Safety Scope",
        "",
        "This build script was source/build-only. It did not issue device commands, flash, reboot, scan/connect, use credentials, configure DHCP/routes, perform external ping, write PMIC/GPIO/GDSC controls, perform blind eSoC notify/`BOOT_DONE` spoof, global PCI rescan/platform bind-unbind, or write device partitions.",
        "",
        "## Next",
        "",
        "V1613 should run local artifact sanity over this exact manifest. If it passes, a later rollbackable live handoff can collect the non-stopping `per_mgr` context snapshots and roll back to `stage3/boot_linux_v724.img`.",
        "",
    ])


def main() -> int:
    rc = base.main([*DEFAULT_ARGS, *sys.argv[1:]])
    if rc != 0:
        return rc
    manifest_path = OUT_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    write_private_text(REPORT_PATH, render_report(manifest))
    print(f"report={rel(REPORT_PATH)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

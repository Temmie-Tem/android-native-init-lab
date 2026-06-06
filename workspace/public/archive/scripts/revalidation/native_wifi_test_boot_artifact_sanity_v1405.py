#!/usr/bin/env python3
"""V1405 local-only sanity verifier for the V1404 Wi-Fi test boot artifact."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import native_wifi_test_boot_artifact_sanity_v1401 as base
from a90harness.evidence import EvidenceStore


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
DEFAULT_MANIFEST = REPO_ROOT / "tmp" / "wifi" / "v1404-wifi-test-boot-debugfs" / "manifest.json"
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1405-wifi-test-boot-debugfs-artifact-sanity"
DEFAULT_REPORT_PATH = REPO_ROOT / "docs" / "reports" / "NATIVE_INIT_V1405_WIFI_TEST_BOOT_DEBUGFS_ARTIFACT_SANITY_2026-06-01.md"
EXPECTED_DECISION = "v1404-wifi-test-boot-debugfs-source-build-pass"
EXPECTED_HELPER = "a90_android_execns_probe_v286"
EXPECTED_BOOT_MARKERS = (
    "A90 Linux init 0.9.72 (v1404-wifitest)",
    "a90_android_execns_probe v286",
    "A90v1404",
    "wifi test boot armed",
    "/cache/native-init-wifi-test-boot-v1404.log",
    "/cache/native-init-wifi-test-boot-v1404.summary",
    "/cache/native-init-wifi-test-boot-v1404.pid",
    "/cache/native-init-wifi-test-boot-v1404-supervisor.pid",
    "debugfs_mount_requested",
    "debugfs prepare rc=",
    "/sys/kernel/debug/pci-msm/case",
)


def decide(checks: dict[str, Any]) -> tuple[str, bool, str]:
    required = [
        checks["manifest"]["decision_ok"],
        checks["base_boot"]["exists"],
        checks["files"]["init_binary"]["sha256_ok"],
        checks["files"]["helper"]["sha256_ok"],
        checks["files"]["ramdisk"]["sha256_ok"],
        checks["files"]["boot"]["sha256_ok"],
        checks["static"]["init_binary"]["no_dynamic_section"],
        checks["static"]["init_binary"]["no_interp"],
        checks["static"]["helper"]["no_dynamic_section"],
        checks["static"]["helper"]["no_interp"],
        checks["ramdisk"]["entries_ok"],
        checks["boot_markers"]["markers_ok"],
        checks["header_parity"]["header_args_ok"],
        checks["header_parity"]["kernel_sha256_ok"],
        checks["forbidden_bytes"]["ok"],
        checks["private_modes"]["ok"],
        checks["wifi_test_contract"]["ok"],
    ]
    if all(bool(item) for item in required):
        return (
            "v1405-wifi-test-boot-debugfs-artifact-sanity-pass",
            True,
            "V1404 debugfs-prepared test boot artifact passed local sanity; a bounded live handoff may be planned separately",
        )
    return (
        "v1405-wifi-test-boot-debugfs-artifact-sanity-blocked",
        False,
        "V1404 debugfs-prepared artifact sanity failed; fix local artifact before any flash handoff",
    )


def render_report(manifest: dict[str, Any], result: dict[str, Any]) -> str:
    checks = result["checks"]
    return "\n".join([
        "# Native Init V1405 Wi-Fi Test Boot Debugfs Artifact Sanity",
        "",
        "## Summary",
        "",
        "- Cycle: `V1405`",
        "- Type: local-only artifact sanity verifier",
        f"- Decision: `{result['decision']}`",
        f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
        f"- V1404 manifest: `{manifest['_path']}`",
        f"- V1404 boot image: `{manifest['boot_image']}`",
        "",
        "## Checks",
        "",
        f"- manifest decision: `{checks['manifest']['decision_ok']}`",
        f"- base boot exists: `{checks['base_boot']['exists']}`",
        f"- init static: `{checks['static']['init_binary']['no_dynamic_section'] and checks['static']['init_binary']['no_interp']}`",
        f"- helper static: `{checks['static']['helper']['no_dynamic_section'] and checks['static']['helper']['no_interp']}`",
        f"- ramdisk entries: `{checks['ramdisk']['entries_ok']}`",
        f"- boot markers: `{checks['boot_markers']['markers_ok']}`",
        f"- Wi-Fi test debugfs contract: `{checks['wifi_test_contract']['ok']}`",
        f"- header parity: `{checks['header_parity']['header_args_ok']}`",
        f"- kernel parity: `{checks['header_parity']['kernel_sha256_ok']}`",
        f"- forbidden credential-like bytes absent: `{checks['forbidden_bytes']['ok']}`",
        f"- private modes: `{checks['private_modes']['ok']}`",
        "",
        "## Artifact",
        "",
        f"- boot image: `{manifest['boot_image']}`",
        f"- boot sha256: `{manifest['boot_sha256']}`",
        f"- ramdisk sha256: `{manifest['ramdisk_sha256']}`",
        f"- helper sha256: `{manifest['helper_sha256']}`",
        "",
        "## Safety Scope",
        "",
        "No device command, flash, reboot, boot partition write, partition write,",
        "Wi-Fi HAL, scan/connect, credential handling, DHCP/routes, external ping,",
        "PMIC/GPIO/GDSC direct write, or blind eSoC notify/`BOOT_DONE` spoof was",
        "performed.",
        "",
        "## Next",
        "",
        "A later live handoff may flash only the V1404 test image, expect",
        "`A90 Linux init 0.9.72 (v1404-wifitest)`, collect the V1404 log, summary,",
        "and dmesg markers, then roll back to `stage3/boot_linux_v724.img`.",
        "",
    ])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--write-report", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    store = EvidenceStore(args.out_dir)
    manifest = base.load_manifest(args.manifest)
    manifest["_path"] = base.rel(args.manifest)

    base.EXPECTED_BOOT_MARKERS = EXPECTED_BOOT_MARKERS
    base.EXPECTED_DECISION = EXPECTED_DECISION

    base_boot = base.repo_path(str(manifest["base_boot"]))
    init_binary = base.repo_path(str(manifest["init_binary"]))
    helper = args.manifest.parent / EXPECTED_HELPER
    ramdisk = base.repo_path(str(manifest["ramdisk_cpio"]))
    boot = base.repo_path(str(manifest["boot_image"]))
    wifi_test = manifest.get("wifi_test", {})

    checks: dict[str, Any] = {
        "manifest": {
            "decision": manifest.get("decision", ""),
            "decision_ok": manifest.get("decision") == EXPECTED_DECISION,
        },
        "base_boot": {
            "path": base.rel(base_boot),
            "exists": base_boot.exists(),
            "sha256": base.sha256(base_boot) if base_boot.exists() else "",
        },
        "files": {
            "init_binary": base.file_sha_check(manifest, "init_binary", "init_sha256"),
            "helper": {
                "path": base.rel(helper),
                "exists": helper.exists(),
                "expected_sha256": manifest["helper_sha256"],
                "actual_sha256": base.sha256(helper) if helper.exists() else "",
                "sha256_ok": helper.exists() and base.sha256(helper) == manifest["helper_sha256"],
                "mode": base.mode_octal(helper) if helper.exists() else "",
            },
            "ramdisk": base.file_sha_check(manifest, "ramdisk_cpio", "ramdisk_sha256"),
            "boot": base.file_sha_check(manifest, "boot_image", "boot_sha256"),
        },
        "static": {
            "init_binary": base.static_check(init_binary),
            "helper": base.static_check(helper),
        },
        "ramdisk": base.ramdisk_check(ramdisk),
        "boot_markers": base.boot_marker_check(boot),
        "header_parity": base.header_parity_check(base_boot, boot),
        "forbidden_bytes": base.no_forbidden_check([init_binary, helper, ramdisk, boot]),
        "private_modes": {
            "ramdisk_mode": base.mode_octal(ramdisk),
            "boot_mode": base.mode_octal(boot),
            "manifest_mode": base.mode_octal(args.manifest),
            "ok": base.mode_octal(ramdisk) == "0o600" and base.mode_octal(boot) == "0o600",
        },
        "wifi_test_contract": {
            "label": wifi_test.get("label"),
            "fresh_log": wifi_test.get("fresh_log"),
            "summary_watcher": wifi_test.get("summary_watcher"),
            "supervise_helper": wifi_test.get("supervise_helper"),
            "supervisor_timeout_sec": wifi_test.get("supervisor_timeout_sec"),
            "watch_sec": wifi_test.get("watch_sec"),
            "mount_debugfs": wifi_test.get("mount_debugfs"),
            "ok": (
                wifi_test.get("label") == "v1404"
                and wifi_test.get("fresh_log") is True
                and wifi_test.get("summary_watcher") is True
                and wifi_test.get("supervise_helper") is True
                and wifi_test.get("supervisor_timeout_sec") == 40
                and wifi_test.get("watch_sec") == 35
                and wifi_test.get("mount_debugfs") is True
            ),
        },
    }
    label, pass_ok, reason = decide(checks)
    result = {
        "cycle": "V1405",
        "decision": label,
        "pass": pass_ok,
        "reason": reason,
        "checks": checks,
    }
    store.write_json("manifest.json", result)
    store.write_text("summary.md", render_report(manifest, result))
    if args.write_report:
        args.report_path.write_text(render_report(manifest, result), encoding="utf-8")
    print(json.dumps({"decision": label, "pass": pass_ok, "out_dir": str(args.out_dir)}, indent=2))
    return 0 if pass_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

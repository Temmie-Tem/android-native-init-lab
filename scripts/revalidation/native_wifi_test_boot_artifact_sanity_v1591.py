#!/usr/bin/env python3
"""V1591 local-only sanity verifier for the late-per_proxy lower-marker test boot."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import native_wifi_test_boot_artifact_sanity_v1401 as base
from a90harness.evidence import EvidenceStore, write_private_text


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST = (
    REPO_ROOT
    / "tmp"
    / "wifi"
    / "v1591-late-per-proxy-lower-marker-test-boot"
    / "manifest.json"
)
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1591-late-per-proxy-lower-marker-artifact-sanity"
DEFAULT_REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1591_LATE_PER_PROXY_LOWER_MARKER_ARTIFACT_SANITY_2026-06-02.md"
)
EXPECTED_DECISION = "v1591-late-per-proxy-lower-marker-test-boot-source-build-pass"
EXPECTED_HELPER = "a90_android_execns_probe_v294"
EXPECTED_BOOT_MARKERS = (
    "A90 Linux init 0.9.102 (v1591-late-per-proxy-lower-marker)",
    "a90_android_execns_probe v294",
    "A90v1591",
    "wifi test boot armed",
    "/cache/native-init-wifi-test-boot-v1591-helper.result",
    "firmware_mounts_requested",
    "firmware mounts prepare rc=",
    "A90v641: firmware mounts ready",
    "wifi-companion-android-wifi-service-window-subsys-trigger-capture",
    "--allow-android-wifi-service-window",
    "--allow-android-wifi-service-window-subsys-trigger-capture",
    "--allow-android-wifi-service-window-pm-proxy-contract",
    "--allow-android-wifi-service-window-late-per-proxy-only",
    "guarded-pm-proxy-contract-late-per-proxy-lower-marker",
    "android_wifi_service_window.lower_marker.begin=1",
    "android_wifi_service_window.lower_marker.mode=service-window-pm-proxy-contract-lower-marker",
    "android_wifi_service_window.lower_marker_sampled=%d",
    "android_wifi_service_window.credentials=0",
    "android_wifi_service_window.dhcp_routing=0",
    "android_wifi_service_window.external_ping=0",
)
EXPECTED_HELPER_MARKERS = (
    "a90_android_execns_probe v294",
    "android_wifi_service_window.lower_marker.begin=1",
    "android_wifi_service_window.lower_marker.mode=service-window-pm-proxy-contract-lower-marker",
    "android_wifi_service_window.lower_marker.mhi_bus_max=%d",
    "android_wifi_service_window.lower_marker.wlfw_start_kmsg_max=%d",
    "android_wifi_service_window.lower_marker.bdf_kmsg_max=%d",
    "android_wifi_service_window.lower_marker.fw_ready_kmsg_max=%d",
    "android_wifi_service_window.lower_marker.wlan0_seen=%d",
    "android_wifi_service_window.lower_marker.scan_connect=0",
    "android_wifi_service_window.lower_marker.credentials=0",
    "android_wifi_service_window.lower_marker.external_ping=0",
)
EXPECTED_INIT_MARKERS = (
    "wifi-companion-android-wifi-service-window-subsys-trigger-capture",
    "--result-output-path",
    "--allow-android-wifi-service-window",
    "--allow-android-wifi-service-window-subsys-trigger-capture",
    "--allow-android-wifi-service-window-pm-proxy-contract",
    "--allow-android-wifi-service-window-late-per-proxy-only",
)
FORBIDDEN_INIT_MARKERS = (
    "--allow-connect-dhcp-ping",
    "--allow-scan-only",
    "--connect-config",
    "--ping-target",
    "--wifi-test-mount-debugfs",
    "--wifi-test-pid1-rc1-watcher",
)


def strings_check(path: Path, markers: tuple[str, ...]) -> dict[str, Any]:
    strings = base.run(["strings", path]).stdout
    missing = [marker for marker in markers if marker not in strings]
    return {"path": base.rel(path), "missing": missing, "ok": not missing}


def init_route_check(path: Path) -> dict[str, Any]:
    strings = base.run(["strings", path]).stdout
    missing = [marker for marker in EXPECTED_INIT_MARKERS if marker not in strings]
    forbidden_present = [marker for marker in FORBIDDEN_INIT_MARKERS if marker in strings]
    return {
        "path": base.rel(path),
        "missing": missing,
        "forbidden_present": forbidden_present,
        "ok": not missing and not forbidden_present,
    }


def contract_check(wifi_test: dict[str, Any], safety: dict[str, Any]) -> dict[str, Any]:
    expected = {
        "label": "v1591",
        "fresh_log": True,
        "summary_watcher": True,
        "supervise_helper": True,
        "supervisor_timeout_sec": 130,
        "watch_sec": 120,
        "helper_mode": "android-service-window-pm-proxy-contract-late-per-proxy-lower-marker",
        "helper_runtime_mode": "wifi-companion-android-wifi-service-window-subsys-trigger-capture",
        "helper_result": "/cache/native-init-wifi-test-boot-v1591-helper.result",
        "android_service_window": True,
        "scan_connect_credentials": False,
        "mount_debugfs": False,
        "firmware_mounts": True,
        "pid1_rc1_watcher": False,
        "rc1_window_sampler": False,
        "auto_readiness_supervisor": False,
        "rc1_retry_count": 0,
    }
    expected_safety = {
        "device_command": False,
        "flash": False,
        "partition_write": False,
        "wifi_scan_connect": False,
        "credentials": False,
        "dhcp_routes_external_ping": False,
    }
    observed = {key: wifi_test.get(key) for key in expected}
    safety_observed = {key: safety.get(key) for key in expected_safety}
    mismatches = {
        key: {"expected": expected[key], "observed": observed[key]}
        for key in expected
        if observed[key] != expected[key]
    }
    safety_mismatches = {
        key: {"expected": expected_safety[key], "observed": safety_observed[key]}
        for key in expected_safety
        if safety_observed[key] != expected_safety[key]
    }
    return {
        **observed,
        "safety": safety_observed,
        "mismatches": mismatches,
        "safety_mismatches": safety_mismatches,
        "ok": not mismatches and not safety_mismatches,
    }


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
        checks["boot_markers"]["ok"],
        checks["helper_markers"]["ok"],
        checks["init_route"]["ok"],
        checks["header_parity"]["header_args_ok"],
        checks["header_parity"]["kernel_sha256_ok"],
        checks["forbidden_bytes"]["ok"],
        checks["private_modes"]["ok"],
        checks["wifi_test_contract"]["ok"],
    ]
    if all(bool(item) for item in required):
        return (
            "v1591-late-per-proxy-lower-marker-artifact-sanity-pass",
            True,
            "V1591 late-per_proxy lower-marker test boot artifact passed local sanity",
        )
    return (
        "v1591-late-per-proxy-lower-marker-artifact-sanity-blocked",
        False,
        "V1591 artifact sanity failed; fix local artifact before any live handoff",
    )


def render_report(manifest: dict[str, Any], result: dict[str, Any]) -> str:
    checks = result["checks"]
    return "\n".join([
        "# Native Init V1591 Late-per_proxy Lower-marker Artifact Sanity",
        "",
        "## Summary",
        "",
        "- Cycle: `V1591`",
        "- Type: local-only artifact sanity verifier",
        f"- Decision: `{result['decision']}`",
        f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
        f"- V1591 manifest: `{manifest['_path']}`",
        f"- V1591 boot image: `{manifest['boot_image']}`",
        "",
        "## Checks",
        "",
        f"- manifest decision: `{checks['manifest']['decision_ok']}`",
        f"- base boot exists: `{checks['base_boot']['exists']}`",
        f"- init static: `{checks['static']['init_binary']['no_dynamic_section'] and checks['static']['init_binary']['no_interp']}`",
        f"- helper static: `{checks['static']['helper']['no_dynamic_section'] and checks['static']['helper']['no_interp']}`",
        f"- ramdisk entries: `{checks['ramdisk']['entries_ok']}`",
        f"- boot lower-marker markers: `{checks['boot_markers']['ok']}`",
        f"- helper lower-marker markers: `{checks['helper_markers']['ok']}`",
        f"- init route: `{checks['init_route']['ok']}`",
        f"- route contract: `{checks['wifi_test_contract']['ok']}`",
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
        f"- init sha256: `{manifest['init_sha256']}`",
        f"- helper sha256: `{manifest['helper_sha256']}`",
        f"- helper marker: `{manifest['helper_marker']}`",
        "",
        "## Safety Scope",
        "",
        "No device command, flash, reboot, boot partition write, partition write,",
        "scan/connect, credential handling, DHCP/routes, external ping,",
        "PMIC/GPIO/GDSC direct write, blind eSoC notify/`BOOT_DONE` spoof, global",
        "PCI rescan, or platform bind/unbind was performed by this verifier.",
        "",
        "## Next",
        "",
        "V1592 may run a rollbackable live handoff of only this V1591 image, collect",
        "the helper result with `android_wifi_service_window.lower_marker`, then",
        "roll back to `stage3/boot_linux_v724.img` and verify selftest `fail=0`.",
        "",
    ])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--write-report", action="store_true", default=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    store = EvidenceStore(args.out_dir)
    manifest = base.load_manifest(args.manifest)
    manifest["_path"] = base.rel(args.manifest)

    base_boot = base.repo_path(str(manifest["base_boot"]))
    init_binary = base.repo_path(str(manifest["init_binary"]))
    helper = args.manifest.parent / EXPECTED_HELPER
    ramdisk = base.repo_path(str(manifest["ramdisk_cpio"]))
    boot = base.repo_path(str(manifest["boot_image"]))
    wifi_test = manifest.get("wifi_test", {})
    safety = manifest.get("safety", {})

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
        "boot_markers": strings_check(boot, EXPECTED_BOOT_MARKERS),
        "helper_markers": strings_check(helper, EXPECTED_HELPER_MARKERS),
        "init_route": init_route_check(init_binary),
        "header_parity": base.header_parity_check(base_boot, boot),
        "forbidden_bytes": base.no_forbidden_check([init_binary, helper, ramdisk, boot]),
        "private_modes": {
            "ramdisk_mode": base.mode_octal(ramdisk),
            "boot_mode": base.mode_octal(boot),
            "manifest_mode": base.mode_octal(args.manifest),
            "ok": base.mode_octal(ramdisk) == "0o600" and base.mode_octal(boot) == "0o600",
        },
        "wifi_test_contract": contract_check(wifi_test, safety),
    }
    label, pass_ok, reason = decide(checks)
    result = {
        "cycle": "V1591",
        "decision": label,
        "pass": pass_ok,
        "reason": reason,
        "checks": checks,
    }
    store.write_json("manifest.json", result)
    report = render_report(manifest, result)
    store.write_text("summary.md", report)
    if args.write_report:
        write_private_text(args.report_path, report)
    print(json.dumps({"decision": label, "pass": pass_ok, "out_dir": str(args.out_dir)}, indent=2))
    return 0 if pass_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

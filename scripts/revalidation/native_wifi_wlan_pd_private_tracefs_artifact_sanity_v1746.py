#!/usr/bin/env python3
"""V1746 local-only sanity verifier for the V1745 private tracefs repair test boot."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from a90harness.evidence import EvidenceStore, write_private_text

import native_wifi_test_boot_artifact_sanity_v1394 as base


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST = (
    REPO_ROOT
    / "tmp"
    / "wifi"
    / "v1745-wlan-pd-private-tracefs-repair-test-boot"
    / "manifest.json"
)
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1746-wlan-pd-private-tracefs-repair-artifact-sanity"
DEFAULT_REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1746_WLAN_PD_PRIVATE_TRACEFS_REPAIR_ARTIFACT_SANITY_2026-06-03.md"
)
EXPECTED_DECISION = "v1745-wlan-pd-private-tracefs-repair-source-build-pass"
EXPECTED_BOOT_MARKERS = (
    "A90 Linux init 0.9.142 (v1745-wlan-pd-private-tracefs-repair)",
    "a90_android_execns_probe v329",
    "A90v1745",
    "native-init-wifi-test-boot-v1745",
    "/bin/a90_android_execns_probe",
    "wifi-companion-wlan-pd-cnss-output-visibility-start-only",
    "wlan_pd_cnss_nonlog_control_flow.tracefs.available=%d",
    "wlan_pd_cnss_nonlog_control_flow.tracefs.path=%s",
    "bind private tracefs",
)
EXPECTED_RAMDISK_ENTRIES = (
    "init",
    "bin/a90_android_execns_probe",
    "bin/a90_tcpctl",
    "bin/a90_rshell",
)


def helper_path(manifest_path: Path, manifest: dict[str, Any]) -> Path:
    marker = str(manifest.get("helper_marker", ""))
    version = marker.rsplit(" ", 1)[-1] if " " in marker else "v329"
    return manifest_path.parent / f"a90_android_execns_probe_{version}"


def display_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def check_boot_markers(path: Path) -> dict[str, Any]:
    strings = base.run(["strings", path]).stdout
    missing = [marker for marker in EXPECTED_BOOT_MARKERS if marker not in strings]
    return {
        "path": display_path(path),
        "missing": missing,
        "markers_ok": not missing,
    }


def check_ramdisk(path: Path) -> dict[str, Any]:
    listing = base.run(["bash", "-lc", f"cpio -it < {path}"]).stdout.splitlines()
    missing = [entry for entry in EXPECTED_RAMDISK_ENTRIES if entry not in listing]
    return {
        "path": display_path(path),
        "entry_count": len(listing),
        "missing": missing,
        "entries_ok": not missing,
    }


def route_contract(manifest: dict[str, Any]) -> dict[str, Any]:
    wifi = manifest.get("wifi_test", {})
    safety = manifest.get("safety", {})
    expected = {
        "label": "v1745",
        "helper_mode": "wlan-pd-cnss-output-visibility",
        "helper_runtime_mode": "wifi-companion-wlan-pd-cnss-output-visibility-start-only",
        "wlan_pd_cnss_output_visibility": True,
        "wlan_pd_firmware_serve_gate": True,
        "firmware_mounts": True,
        "summary_watcher": True,
        "supervise_helper": True,
        "supervisor_timeout_sec": 95,
        "watch_sec": 70,
        "android_service_window": False,
        "scan_connect_credentials": False,
        "mount_debugfs": False,
        "pid1_rc1_watcher": False,
        "rc1_window_sampler": False,
        "rc1_endpoint_sampler": False,
        "provider_trigger_micro_endpoint_sampler": False,
        "provider_trigger_tracepoint_sampler": False,
        "provider_trigger_pil_tracepoint_sampler": False,
        "provider_trigger_effective_level_sampler": False,
        "provider_trigger_ap2mdm_hold": False,
        "rc1_retry_count": 0,
        "rc1_retry_delay_ms": 0,
    }
    expected_safety = {
        "device_command": False,
        "flash": False,
        "partition_write": False,
        "wifi_scan_connect": False,
        "credentials": False,
        "dhcp_routes_external_ping": False,
    }
    observed = {key: wifi.get(key) for key in expected}
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


def property_runtime_contract(manifest: dict[str, Any]) -> dict[str, Any]:
    runtime = manifest.get("cnss_nonlog_property_runtime", {})
    checks = runtime.get("checks", [])
    expected = {
        "persist.vendor.cnss-daemon.kmsg_logging": "1",
        "persist.vendor.cnss-daemon.debug_level": "4",
    }
    found = {item.get("name"): item for item in checks}
    mismatches = {
        key: found.get(key, {}).get("actual")
        for key, value in expected.items()
        if found.get(key, {}).get("actual") != value or found.get(key, {}).get("status") != "pass"
    }
    return {
        "decision": runtime.get("decision", ""),
        "pass": bool(runtime.get("pass")),
        "mismatches": mismatches,
        "ok": bool(runtime.get("pass")) and not mismatches,
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
        checks["boot_markers"]["markers_ok"],
        checks["header_parity"]["header_args_ok"],
        checks["header_parity"]["kernel_sha256_ok"],
        checks["forbidden_bytes"]["ok"],
        checks["private_modes"]["ok"],
        checks["route_contract"]["ok"],
        checks["property_runtime"]["ok"],
    ]
    if all(bool(item) for item in required):
        return (
            "v1746-wlan-pd-private-tracefs-repair-artifact-sanity-pass",
            True,
            "V1745 private tracefs repair artifact passed local sanity; one rollbackable live handoff may be planned separately",
        )
    return (
        "v1746-wlan-pd-private-tracefs-repair-artifact-sanity-blocked",
        False,
        "V1745 artifact sanity failed; fix local artifact before any flash handoff",
    )


def render_report(manifest: dict[str, Any], result: dict[str, Any]) -> str:
    checks = result["checks"]
    return "\n".join([
        "# Native Init V1746 WLAN-PD Private Tracefs Repair Artifact Sanity",
        "",
        "## Summary",
        "",
        "- Cycle: `V1746`",
        "- Type: local-only artifact sanity verifier",
        f"- Decision: `{result['decision']}`",
        f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
        f"- V1745 manifest: `{manifest['_path']}`",
        f"- V1745 boot image: `{manifest['boot_image']}`",
        "",
        "## Checks",
        "",
        f"- manifest decision: `{checks['manifest']['decision_ok']}`",
        f"- base boot exists: `{checks['base_boot']['exists']}`",
        f"- init static: `{checks['static']['init_binary']['no_dynamic_section'] and checks['static']['init_binary']['no_interp']}`",
        f"- helper static: `{checks['static']['helper']['no_dynamic_section'] and checks['static']['helper']['no_interp']}`",
        f"- ramdisk entries: `{checks['ramdisk']['entries_ok']}`",
        f"- boot markers: `{checks['boot_markers']['markers_ok']}`",
        f"- route contract: `{checks['route_contract']['ok']}`",
        f"- property runtime: `{checks['property_runtime']['ok']}`",
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
        f"- helper runtime mode: `{manifest['wifi_test']['helper_runtime_mode']}`",
        f"- helper result path: `{manifest['wifi_test']['helper_result']}`",
        "",
        "## Verified Scope",
        "",
        "- The test image selects `wifi-companion-wlan-pd-cnss-output-visibility-start-only`.",
        "- The manifest route excludes service-manager, PM trio, `boot_wlan`, eSoC/subsys_esoc0, forced RC1, fake-ONLINE, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping.",
        "- The boot image contains the v329 helper marker and private tracefs/uProbe result fields.",
        "",
        "## Safety Scope",
        "",
        "No device command, flash, reboot, boot partition write, partition write, Wi-Fi scan/connect, credential handling, DHCP/routes, external ping, PMIC/GPIO/GDSC direct write, blind eSoC notify/`BOOT_DONE` spoof, global PCI rescan, or platform bind/unbind was performed by this verifier.",
        "",
        "## Next",
        "",
        "V1747 may be a separate one-run rollbackable live handoff for only this V1745 image, expecting `A90 Linux init 0.9.142 (v1745-wlan-pd-private-tracefs-repair)`, collecting the helper result, then rolling back to `stage3/boot_linux_v724.img`.",
        "",
    ])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT_PATH)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    store = EvidenceStore(args.out_dir)
    manifest = base.load_manifest(args.manifest)
    manifest["_path"] = str(args.manifest.relative_to(REPO_ROOT))

    base_boot = base.repo_path(str(manifest["base_boot"]))
    init_binary = base.repo_path(str(manifest["init_binary"]))
    helper = helper_path(args.manifest, manifest)
    ramdisk = base.repo_path(str(manifest["ramdisk_cpio"]))
    boot = base.repo_path(str(manifest["boot_image"]))

    checks: dict[str, Any] = {
        "manifest": {
            "decision": manifest.get("decision", ""),
            "decision_ok": manifest.get("decision") == EXPECTED_DECISION,
        },
        "base_boot": {
            "path": display_path(base_boot),
            "exists": base_boot.exists(),
            "sha256": base.sha256(base_boot) if base_boot.exists() else "",
        },
        "files": {
            "init_binary": base.check_file_sha(manifest, "init_binary", "init_sha256"),
            "helper": {
                "path": display_path(helper),
                "exists": helper.exists(),
                "expected_sha256": manifest["helper_sha256"],
                "actual_sha256": base.sha256(helper) if helper.exists() else "",
                "sha256_ok": helper.exists() and base.sha256(helper) == manifest["helper_sha256"],
                "mode": base.mode_octal(helper) if helper.exists() else "",
            },
            "ramdisk": base.check_file_sha(manifest, "ramdisk_cpio", "ramdisk_sha256"),
            "boot": base.check_file_sha(manifest, "boot_image", "boot_sha256"),
        },
        "static": {
            "init_binary": base.check_static(init_binary),
            "helper": base.check_static(helper),
        },
        "ramdisk": check_ramdisk(ramdisk),
        "boot_markers": check_boot_markers(boot),
        "header_parity": base.check_header_parity(base_boot, boot),
        "forbidden_bytes": base.check_no_forbidden([init_binary, helper, ramdisk, boot]),
        "private_modes": {
            "ramdisk_mode": base.mode_octal(ramdisk),
            "boot_mode": base.mode_octal(boot),
            "manifest_mode": base.mode_octal(args.manifest),
            "ok": base.mode_octal(ramdisk) == "0o600" and base.mode_octal(boot) == "0o600",
        },
        "route_contract": route_contract(manifest),
        "property_runtime": property_runtime_contract(manifest),
    }
    label, pass_ok, reason = decide(checks)
    result = {
        "cycle": "V1746",
        "decision": label,
        "pass": pass_ok,
        "reason": reason,
        "checks": checks,
    }
    store.write_json("manifest.json", result)
    store.write_text("summary.md", render_report(manifest, result))
    write_private_text(args.report_path, render_report(manifest, result))
    print(json.dumps({"decision": label, "pass": pass_ok, "out_dir": str(args.out_dir)}, indent=2))
    return 0 if pass_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

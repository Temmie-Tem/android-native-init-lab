#!/usr/bin/env python3
"""V1566 local-only sanity verifier for the service-window subsys-trigger test boot."""

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
    / "v1566-android-wifi-service-window-subsys-trigger-test-boot"
    / "manifest.json"
)
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1566-service-window-subsys-trigger-artifact-sanity"
DEFAULT_REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1566_SERVICE_WINDOW_SUBSYS_TRIGGER_ARTIFACT_SANITY_2026-06-02.md"
)
EXPECTED_DECISION = "v1566-android-wifi-service-window-subsys-trigger-test-boot-source-build-pass"
EXPECTED_BOOT_MARKERS = (
    "A90 Linux init 0.9.69 (v1566-service-window-subsys-trigger)",
    "a90_android_execns_probe v287",
    "v1566",
    "wifi test boot armed",
    "/cache/native-init-wifi-test-boot-v1393.log",
    "/cache/native-init-wifi-test-boot-v1393.summary",
    "/cache/native-init-wifi-test-boot-v1393.pid",
    "/cache/native-init-wifi-test-boot-v1393-watcher.pid",
    "wifi-companion-android-wifi-service-window-subsys-trigger-capture",
    "--allow-android-wifi-service-window",
    "--allow-android-wifi-service-window-subsys-trigger-capture",
    "cnss_before_esoc.subsys_trigger.started",
    "cnss_before_esoc.subsys_esoc0_open_attempted",
    "cnss_before_esoc.scan_connect_linkup=0",
    "cnss_before_esoc.credentials=0",
    "cnss_before_esoc.dhcp_routing=0",
    "cnss_before_esoc.external_ping=0",
)
EXPECTED_INIT_MARKERS = (
    "wifi-companion-android-wifi-service-window-subsys-trigger-capture",
    "--allow-android-wifi-service-window",
    "--allow-android-wifi-service-window-subsys-trigger-capture",
)
FORBIDDEN_INIT_MARKERS = (
    "wifi-companion-android-wifi-service-window-start-only",
    "--allow-pm-service-trigger-observer",
    "--allow-post-pm-mdm-helper-esoc-observer",
    "--allow-post-pm-mdm-helper-lower-trace",
    "--pm-observer-continue-after-provider",
    "--pm-observer-start-cnss-after-provider",
    "--pm-observer-start-mdm-helper-after-cnss",
    "--pm-observer-start-mdm-helper-before-cnss",
    "--pm-observer-early-powerup-corrected-rc1-enumerate",
    "--pm-observer-private-cnss-daemon-sdx50m",
    "--private-cnss-daemon-path",
    "--allow-connect-dhcp-ping",
    "--allow-scan-only",
    "--connect-config",
    "--ping-target",
)


def boot_marker_check(path: Path) -> dict[str, Any]:
    strings = base.run(["strings", path]).stdout
    missing = [marker for marker in EXPECTED_BOOT_MARKERS if marker not in strings]
    return {"path": base.rel(path), "missing": missing, "markers_ok": not missing}


def init_route_check(path: Path) -> dict[str, Any]:
    strings = base.run(["strings", path]).stdout
    missing = [marker for marker in EXPECTED_INIT_MARKERS if marker not in strings]
    present = [marker for marker in FORBIDDEN_INIT_MARKERS if marker in strings]
    return {
        "path": base.rel(path),
        "missing": missing,
        "forbidden_present": present,
        "ok": not missing and not present,
    }


def contract_check(wifi_test: dict[str, Any], safety: dict[str, Any]) -> dict[str, Any]:
    expected = {
        "label": "v1566",
        "fresh_log": True,
        "summary_watcher": True,
        "supervise_helper": True,
        "supervisor_timeout_sec": 75,
        "watch_sec": 75,
        "helper_mode": "android-service-window-subsys-trigger-capture",
        "helper_runtime_mode": "wifi-companion-android-wifi-service-window-subsys-trigger-capture",
        "android_service_window": True,
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
        "auto_readiness_supervisor": False,
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
        checks["boot_markers"]["markers_ok"],
        checks["init_route"]["ok"],
        checks["header_parity"]["header_args_ok"],
        checks["header_parity"]["kernel_sha256_ok"],
        checks["forbidden_bytes"]["ok"],
        checks["private_modes"]["ok"],
        checks["wifi_test_contract"]["ok"],
    ]
    if all(bool(item) for item in required):
        return (
            "v1566-service-window-subsys-trigger-artifact-sanity-pass",
            True,
            "V1566 service-window subsys-trigger test boot artifact passed local sanity; rollbackable live handoff may be planned separately",
        )
    return (
        "v1566-service-window-subsys-trigger-artifact-sanity-blocked",
        False,
        "V1566 artifact sanity failed; fix local artifact before any flash handoff",
    )


def render_report(manifest: dict[str, Any], result: dict[str, Any]) -> str:
    checks = result["checks"]
    return "\n".join([
        "# Native Init V1566 Service-Window Subsys Trigger Artifact Sanity",
        "",
        "## Summary",
        "",
        "- Cycle: `V1566`",
        "- Type: local-only artifact sanity verifier",
        f"- Decision: `{result['decision']}`",
        f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
        f"- V1566 manifest: `{manifest['_path']}`",
        f"- V1566 boot image: `{manifest['boot_image']}`",
        "",
        "## Checks",
        "",
        f"- manifest decision: `{checks['manifest']['decision_ok']}`",
        f"- base boot exists: `{checks['base_boot']['exists']}`",
        f"- init static: `{checks['static']['init_binary']['no_dynamic_section'] and checks['static']['init_binary']['no_interp']}`",
        f"- helper static: `{checks['static']['helper']['no_dynamic_section'] and checks['static']['helper']['no_interp']}`",
        f"- ramdisk entries: `{checks['ramdisk']['entries_ok']}`",
        f"- boot markers: `{checks['boot_markers']['markers_ok']}`",
        f"- init trigger route: `{checks['init_route']['ok']}`",
        f"- trigger contract: `{checks['wifi_test_contract']['ok']}`",
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
        f"- supervisor timeout: `{manifest['wifi_test']['supervisor_timeout_sec']}` seconds",
        "",
        "## Verified Test Scope",
        "",
        "- The test image selects `wifi-companion-android-wifi-service-window-subsys-trigger-capture`.",
        "- The PID1 argv contains both Android service-window allow flags.",
        "- The PID1 argv excludes the start-only route, post-PM observer route, forced RC1 enumerate, private patched CNSS daemon path, direct scan/connect flags, and external ping flags.",
        "- The generated manifest records no credential, scan/connect, DHCP/route, external ping, flash, or partition write action for the source/build step.",
        "- The boot image contains `cnss_before_esoc`/subsys-trigger evidence markers for the next live classifier.",
        "",
        "## Safety Scope",
        "",
        "No device command, flash, reboot, boot partition write, partition write,",
        "Wi-Fi scan/connect, credential handling, DHCP/routes, external ping,",
        "PMIC/GPIO/GDSC direct write, blind eSoC notify/`BOOT_DONE` spoof, global",
        "PCI rescan, or platform bind/unbind was performed by this verifier.",
        "",
        "## Next",
        "",
        "A later V1567 rollbackable live handoff may flash only this V1566 test",
        "image, expect `A90 Linux init 0.9.69 (v1566-service-window-subsys-trigger)`,",
        "collect the service-window log, summary, focused dmesg, and `wlan0` state,",
        "then roll back to `stage3/boot_linux_v724.img`. The live target remains",
        "WLFW/BDF/FW-ready/`wlan0` progress and trigger-window classification;",
        "no credentials, scan/connect, DHCP/routes, or external ping.",
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
    helper = args.manifest.parent / "a90_android_execns_probe_v287"
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
        "boot_markers": boot_marker_check(boot),
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
        "cycle": "V1566",
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

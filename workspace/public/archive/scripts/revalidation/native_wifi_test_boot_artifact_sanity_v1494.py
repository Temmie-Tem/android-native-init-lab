#!/usr/bin/env python3
"""V1494 local-only sanity verifier for the V1493 RC1-window auto-readiness Wi-Fi test boot."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import native_wifi_test_boot_artifact_sanity_v1401 as base
from a90harness.evidence import EvidenceStore


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
DEFAULT_MANIFEST = REPO_ROOT / "tmp" / "wifi" / "v1493-wifi-auto-readiness-rc1-window-test-boot" / "manifest.json"
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1494-wifi-auto-readiness-rc1-window-artifact-sanity"
DEFAULT_REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1494_WIFI_AUTO_READINESS_RC1_WINDOW_ARTIFACT_SANITY_2026-06-01.md"
)
EXPECTED_DECISION = "v1493-wifi-auto-readiness-rc1-window-test-boot-source-build-pass"
EXPECTED_BOOT_MARKERS = (
    "A90 Linux init 0.9.92 (v1493-wifitest)",
    "a90_android_execns_probe v287",
    "A90v1493",
    "wifi test boot armed",
    "/cache/native-init-wifi-test-boot-v1493.log",
    "/cache/native-init-wifi-test-boot-v1493.summary",
    "/cache/native-init-wifi-test-boot-v1493.pid",
    "/cache/native-init-wifi-test-boot-v1493-supervisor.pid",
    "auto-v1485-wifi-readiness-test",
    "auto_readiness_supervisor_requested",
    "pid1_rc1_watcher_requested",
    "rc1_window_sampler_requested",
    "/cache/native-init-wifi-test-boot-v1493-rc1-watcher.result",
    "/cache/native-init-wifi-test-boot-v1493-rc1-window.result",
    "auto_readiness_pid1.begin=1",
    "auto_readiness_pid1.primary_checkpoint=%s",
    "auto_readiness_pid1.provider_trigger_seen=%d",
    "auto_readiness_pid1.wlan0_seen=%d",
    "auto_readiness_pid1.safety_credentials=0",
    "--pm-observer-auto-readiness-summary",
    "auto_readiness.begin=1",
    "auto_readiness.primary_checkpoint=%s",
    "auto_readiness.wlfw_start_seen=%d",
    "auto_readiness.icnss_qmi_seen=%d",
    "auto_readiness.bdf_seen=%d",
    "auto_readiness.fw_ready_seen=%d",
    "auto_readiness.wlan0_seen=%d",
    "auto_readiness.safety_credentials=0",
    "auto_readiness.safety_scan_connect=0",
    "auto_readiness.safety_external_ping=0",
)
EXPECTED_ABSENT_MARKERS = (
    "bounded-v1477-ap2mdm-hold-test",
    "ap2mdm_hold gate_sample=%s",
    "ap2mdm_hold attempt export_rc=%d",
    "ap2mdm_hold cleanup release_rc=%d",
)


def boot_marker_check(path: Path) -> dict[str, Any]:
    strings = base.run(["strings", path]).stdout
    missing = [marker for marker in EXPECTED_BOOT_MARKERS if marker not in strings]
    return {"path": base.rel(path), "missing": missing, "markers_ok": not missing}


def boot_absent_marker_check(path: Path) -> dict[str, Any]:
    strings = base.run(["strings", path]).stdout
    present = [marker for marker in EXPECTED_ABSENT_MARKERS if marker in strings]
    return {"path": base.rel(path), "present": present, "absent_ok": not present}


def contract_check(wifi_test: dict[str, Any]) -> dict[str, Any]:
    expected = {
        "label": "v1493",
        "fresh_log": True,
        "summary_watcher": True,
        "supervise_helper": True,
        "supervisor_timeout_sec": 70,
        "watch_sec": 45,
        "mount_debugfs": True,
        "pid1_rc1_watcher": True,
        "rc1_window_sampler": True,
        "rc1_endpoint_sampler": False,
        "rc1_micro_endpoint_sampler": False,
        "provider_trigger_micro_endpoint_sampler": False,
        "provider_trigger_tracepoint_sampler": False,
        "provider_trigger_pil_tracepoint_sampler": False,
        "provider_trigger_effective_level_sampler": False,
        "provider_trigger_ap2mdm_hold": False,
        "auto_readiness_supervisor": True,
        "rc1_retry_count": 0,
        "rc1_retry_delay_ms": 0,
        "rc1_watcher_timeout_sec": 70,
        "rc1_watcher_delay_ms": 0,
        "rc1_watcher_result": "/cache/native-init-wifi-test-boot-v1493-rc1-watcher.result",
        "rc1_window_result": "/cache/native-init-wifi-test-boot-v1493-rc1-window.result",
    }
    observed = {key: wifi_test.get(key) for key in expected}
    mismatches = {
        key: {"expected": expected[key], "observed": observed[key]}
        for key in expected
        if observed[key] != expected[key]
    }
    return {**observed, "mismatches": mismatches, "ok": not mismatches}


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
        checks["boot_absent_markers"]["absent_ok"],
        checks["header_parity"]["header_args_ok"],
        checks["header_parity"]["kernel_sha256_ok"],
        checks["forbidden_bytes"]["ok"],
        checks["private_modes"]["ok"],
        checks["wifi_test_contract"]["ok"],
    ]
    if all(bool(item) for item in required):
        return (
            "v1494-wifi-auto-readiness-rc1-window-artifact-sanity-pass",
            True,
            "V1493 RC1-window auto-readiness test boot artifact passed local sanity; a rollbackable live handoff may be planned separately",
        )
    return (
        "v1494-wifi-auto-readiness-rc1-window-artifact-sanity-blocked",
        False,
        "V1493 artifact sanity failed; fix local artifact before any flash handoff",
    )


def render_report(manifest: dict[str, Any], result: dict[str, Any]) -> str:
    checks = result["checks"]
    return "\n".join([
        "# Native Init V1494 Wi-Fi Auto-readiness RC1 Window Artifact Sanity",
        "",
        "## Summary",
        "",
        "- Cycle: `V1494`",
        "- Type: local-only artifact sanity verifier",
        f"- Decision: `{result['decision']}`",
        f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
        f"- V1493 manifest: `{manifest['_path']}`",
        f"- V1493 boot image: `{manifest['boot_image']}`",
        "",
        "## Checks",
        "",
        f"- manifest decision: `{checks['manifest']['decision_ok']}`",
        f"- base boot exists: `{checks['base_boot']['exists']}`",
        f"- init static: `{checks['static']['init_binary']['no_dynamic_section'] and checks['static']['init_binary']['no_interp']}`",
        f"- helper static: `{checks['static']['helper']['no_dynamic_section'] and checks['static']['helper']['no_interp']}`",
        f"- ramdisk entries: `{checks['ramdisk']['entries_ok']}`",
        f"- boot markers: `{checks['boot_markers']['markers_ok']}`",
        f"- AP2MDM hold marker absence: `{checks['boot_absent_markers']['absent_ok']}`",
        f"- RC1 auto-readiness contract: `{checks['wifi_test_contract']['ok']}`",
        "- RC1 watcher contract includes bounded pci-msm debugfs writes:",
        "  `/sys/kernel/debug/pci-msm/rc_sel=2` then",
        "  `/sys/kernel/debug/pci-msm/case=11`.",
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
        f"- marker: `auto-v1485-wifi-readiness-test`",
        f"- helper marker: `{manifest['helper_marker']}`",
        "",
        "## Safety Scope",
        "",
        "No device command, flash, reboot, boot partition write, partition write,",
        "Wi-Fi HAL, scan/connect, credential handling, DHCP/routes, external ping,",
        "PMIC/GPIO/GDSC direct write, blind eSoC notify/`BOOT_DONE` spoof, global",
        "PCI rescan, or platform bind/unbind was performed by this verifier. The",
        "verified test image itself is not observation-only: if booted, its PID1 watcher",
        "may issue the bounded corrected RC1 enumerate debugfs writes listed above.",
        "",
        "## Next",
        "",
        "V1495 may perform a rollbackable live handoff for only the V1493 test",
        "image, expect `A90 Linux init 0.9.92 (v1493-wifitest)`, collect the",
        "V1493 log, summary, RC1 watcher/window, focused dmesg, and `wlan0` state, then roll back to",
        "`stage3/boot_linux_v724.img` and verify selftest `fail=0`.",
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

    base_boot = base.repo_path(str(manifest["base_boot"]))
    init_binary = base.repo_path(str(manifest["init_binary"]))
    helper = args.manifest.parent / "a90_android_execns_probe_v287"
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
        "boot_markers": boot_marker_check(boot),
        "boot_absent_markers": boot_absent_marker_check(boot),
        "header_parity": base.header_parity_check(base_boot, boot),
        "forbidden_bytes": base.no_forbidden_check([init_binary, helper, ramdisk, boot]),
        "private_modes": {
            "ramdisk_mode": base.mode_octal(ramdisk),
            "boot_mode": base.mode_octal(boot),
            "manifest_mode": base.mode_octal(args.manifest),
            "ok": base.mode_octal(ramdisk) == "0o600" and base.mode_octal(boot) == "0o600",
        },
        "wifi_test_contract": contract_check(wifi_test),
    }
    label, pass_ok, reason = decide(checks)
    result = {
        "cycle": "V1494",
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

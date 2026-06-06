#!/usr/bin/env python3
"""V1637 local-only sanity verifier for the V1636 natural-path MDM2AP IRQ artifact."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import native_wifi_test_boot_artifact_sanity_v1401 as base
from a90harness.evidence import EvidenceStore, write_private_text


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
DEFAULT_MANIFEST = (
    REPO_ROOT
    / "tmp"
    / "wifi"
    / "v1636-natural-path-mdm2ap-irq-summary-test-boot"
    / "manifest.json"
)
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1637-natural-path-mdm2ap-irq-summary-artifact-sanity"
DEFAULT_REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1637_NATURAL_PATH_MDM2AP_IRQ_SUMMARY_ARTIFACT_SANITY_2026-06-02.md"
)
EXPECTED_DECISION = "v1636-natural-path-mdm2ap-irq-summary-source-build-pass"
EXPECTED_INIT_MARKERS = (
    "A90 Linux init 0.9.114 (v1636-natural-mdm2ap-irq-summary)",
    "A90v1636",
    "wifi test boot armed",
    "/cache/native-init-wifi-test-boot-v1636.log",
    "/cache/native-init-wifi-test-boot-v1636.summary",
    "/cache/native-init-wifi-test-boot-v1636.pid",
    "/cache/native-init-wifi-test-boot-v1636-supervisor.pid",
    "/cache/native-init-wifi-test-boot-v1636-natural-watcher.result",
    "/cache/native-init-wifi-test-boot-v1636-natural-window.result",
    "read-only-v1467-exact-provider-pil-gpio-tracepoint",
    "provider_trigger_micro_endpoint_sampler_requested",
    "provider_trigger_tracepoint_sampler_requested",
    "provider_trigger_pil_tracepoint_sampler_requested",
    "natural_mdm2ap_irq_summary_requested=%d",
    "provider_pil_gpio_trace",
    "fw=esoc0",
    "mdm2ap_timing.mode=pid1-natural-provider-mdm2ap-irq-summary",
    "mdm2ap_timing.gpio142_irq_delta=%lu",
    "mdm2ap_timing.errfatal_irq_delta=%lu",
    "mdm2ap_timing.safety_wifi_hal_start=0",
    "mdm2ap_timing.safety_pmic_write=0",
    "mdm2ap_timing.safety_direct_esoc_ioctl=0",
    "--pm-observer-late-per-proxy-response-sampler",
    "--pm-observer-late-per-proxy-mdm2ap-errfatal-pcie-timing-sampler",
)
EXPECTED_BOOT_MARKERS = (
    *EXPECTED_INIT_MARKERS,
    "a90_android_execns_probe v303",
)
DANGEROUS_INIT_ARG_MARKERS = (
    "--pm-observer-early-powerup-corrected-rc1-enumerate",
    "--pm-observer-late-per-proxy-corrected-rc1-enumerate",
    "--pm-observer-late-per-proxy-immediate-corrected-rc1-enumerate",
    "--pm-observer-late-per-proxy-prepoll-corrected-rc1-enumerate",
    "--pm-observer-trigger-pcie-enumerate",
    "--allow-android-wifi-service-window-fake-mdm3-online-system-info",
)
DANGEROUS_BOOT_MARKERS = (
    "rc1_micro_writer_summary",
    "micro_writer rc=%d",
    "writer_wait_rc=%d",
    "case_aligned_micro_after_case_%dms",
    "post_case_aligned_micro_200ms",
    "ap2mdm_hold attempt export_rc=%d",
)


def rel(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT))


def strings_text(path: Path) -> str:
    return base.run(["strings", path]).stdout


def marker_check(path: Path, markers: tuple[str, ...]) -> dict[str, Any]:
    text = strings_text(path)
    missing = [marker for marker in markers if marker not in text]
    return {"path": rel(path), "missing": missing, "ok": not missing}


def absent_marker_check(path: Path, markers: tuple[str, ...]) -> dict[str, Any]:
    text = strings_text(path)
    present = [marker for marker in markers if marker in text]
    return {"path": rel(path), "present": present, "ok": not present}


def contract_check(wifi_test: dict[str, Any]) -> dict[str, Any]:
    expected = {
        "label": "v1636",
        "fresh_log": True,
        "summary_watcher": True,
        "supervise_helper": True,
        "supervisor_timeout_sec": 80,
        "watch_sec": 55,
        "mount_debugfs": True,
        "pid1_rc1_watcher": True,
        "rc1_watcher_timeout_sec": 70,
        "rc1_watcher_delay_ms": 0,
        "rc1_watcher_result": "/cache/native-init-wifi-test-boot-v1636-natural-watcher.result",
        "rc1_window_sampler": True,
        "rc1_window_result": "/cache/native-init-wifi-test-boot-v1636-natural-window.result",
        "rc1_endpoint_sampler": True,
        "rc1_micro_endpoint_sampler": True,
        "rc1_immediate_endpoint_sampler": False,
        "rc1_case_aligned_micro_endpoint_sampler": False,
        "rc1_sysfs_client_enumerate": False,
        "rc1_retry_count": 0,
        "rc1_retry_delay_ms": 0,
        "auto_readiness_supervisor": False,
        "android_service_window": False,
        "natural_mdm2ap_irq_summary": True,
        "provider_trigger_micro_endpoint_sampler": True,
        "provider_trigger_exact_line": True,
        "provider_trigger_long_window": True,
        "provider_trigger_thread_state": True,
        "provider_trigger_tracepoint_sampler": True,
        "provider_trigger_pil_tracepoint_sampler": True,
        "provider_trigger_effective_level_sampler": False,
        "provider_trigger_ap2mdm_hold": False,
        "scan_connect_credentials": False,
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
        checks["init_markers"]["ok"],
        checks["boot_markers"]["ok"],
        checks["dangerous_init_args_absent"]["ok"],
        checks["dangerous_boot_markers_absent"]["ok"],
        checks["header_parity"]["header_args_ok"],
        checks["header_parity"]["kernel_sha256_ok"],
        checks["forbidden_bytes"]["ok"],
        checks["private_modes"]["ok"],
        checks["wifi_test_contract"]["ok"],
    ]
    if all(bool(item) for item in required):
        return (
            "v1637-natural-path-mdm2ap-irq-summary-artifact-sanity-pass",
            True,
            "V1636 natural-path IRQ summary artifact passed local sanity; one rollbackable live handoff may proceed",
        )
    return (
        "v1637-natural-path-mdm2ap-irq-summary-artifact-sanity-blocked",
        False,
        "artifact sanity failed; fix local artifact before any flash handoff",
    )


def render_report(manifest: dict[str, Any], result: dict[str, Any]) -> str:
    checks = result["checks"]
    contract = checks["wifi_test_contract"]
    return "\n".join([
        "# Native Init V1637 Natural-path MDM2AP IRQ Summary Artifact Sanity",
        "",
        "## Summary",
        "",
        "- Cycle: `V1637`",
        "- Type: local-only artifact sanity verifier",
        f"- Decision: `{result['decision']}`",
        f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
        f"- V1636 manifest: `{manifest['_path']}`",
        f"- V1636 boot image: `{manifest['boot_image']}`",
        "",
        "## Checks",
        "",
        f"- manifest decision: `{checks['manifest']['decision_ok']}`",
        f"- init static: `{checks['static']['init_binary']['no_dynamic_section'] and checks['static']['init_binary']['no_interp']}`",
        f"- helper static: `{checks['static']['helper']['no_dynamic_section'] and checks['static']['helper']['no_interp']}`",
        f"- ramdisk entries: `{checks['ramdisk']['entries_ok']}`",
        f"- init markers: `{checks['init_markers']['ok']}`",
        f"- boot markers: `{checks['boot_markers']['ok']}`",
        f"- dangerous init argv markers absent: `{checks['dangerous_init_args_absent']['ok']}`",
        f"- dangerous writer/hold markers absent: `{checks['dangerous_boot_markers_absent']['ok']}`",
        f"- exact provider PIL+GPIO contract: `{contract['ok']}`",
        f"- natural IRQ summary: `{contract['natural_mdm2ap_irq_summary']}`",
        f"- pid1 watcher delay ms: `{contract['rc1_watcher_delay_ms']}`",
        f"- rc1 retry count: `{contract['rc1_retry_count']}`",
        f"- provider sampler: `{contract['provider_trigger_micro_endpoint_sampler']}`",
        f"- provider PIL tracepoint sampler: `{contract['provider_trigger_pil_tracepoint_sampler']}`",
        f"- PID1 mdm2ap timing markers: `{checks['boot_markers']['ok']}`",
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
        f"- helper result path: `{manifest['wifi_test']['helper_result']}`",
        f"- watcher result path: `{manifest['wifi_test']['rc1_watcher_result']}`",
        f"- window result path: `{manifest['wifi_test']['rc1_window_result']}`",
        "",
        "## Safety Scope",
        "",
        "No device command, flash, reboot, boot partition write, partition write, Wi-Fi HAL, scan/connect, credential handling, DHCP/routes, external ping, PMIC/GPIO/GDSC direct write, eSoC notify/`BOOT_DONE` spoof, global PCI rescan, platform bind/unbind, fake ONLINE/system-info bind, or forced RC1 enumerate was performed.",
        "",
        "## Next",
        "",
        "V1638 may perform one rollbackable live handoff using only the V1636 image, then roll back to `stage3/boot_linux_v724.img` and verify selftest `fail=0`.",
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
    manifest["_path"] = rel(args.manifest)

    base_boot = base.repo_path(str(manifest["base_boot"]))
    init_binary = base.repo_path(str(manifest["init_binary"]))
    helper = args.manifest.parent / "a90_android_execns_probe_v293"
    ramdisk = base.repo_path(str(manifest["ramdisk_cpio"]))
    boot = base.repo_path(str(manifest["boot_image"]))
    wifi_test = manifest.get("wifi_test", {})

    checks: dict[str, Any] = {
        "manifest": {
            "decision": manifest.get("decision", ""),
            "decision_ok": manifest.get("decision") == EXPECTED_DECISION,
        },
        "base_boot": {
            "path": rel(base_boot),
            "exists": base_boot.exists(),
            "sha256": base.sha256(base_boot) if base_boot.exists() else "",
        },
        "files": {
            "init_binary": base.file_sha_check(manifest, "init_binary", "init_sha256"),
            "helper": {
                "path": rel(helper),
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
        "init_markers": marker_check(init_binary, EXPECTED_INIT_MARKERS),
        "boot_markers": marker_check(boot, EXPECTED_BOOT_MARKERS),
        "dangerous_init_args_absent": absent_marker_check(init_binary, DANGEROUS_INIT_ARG_MARKERS),
        "dangerous_boot_markers_absent": absent_marker_check(boot, DANGEROUS_BOOT_MARKERS),
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
        "cycle": "V1637",
        "decision": label,
        "pass": pass_ok,
        "reason": reason,
        "checks": checks,
    }
    report = render_report(manifest, result)
    store.write_json("manifest.json", result)
    store.write_text("summary.md", report)
    if args.write_report:
        write_private_text(args.report_path, report)
    print(json.dumps({
        "decision": label,
        "pass": pass_ok,
        "out_dir": rel(args.out_dir),
    }, indent=2, sort_keys=True))
    return 0 if pass_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

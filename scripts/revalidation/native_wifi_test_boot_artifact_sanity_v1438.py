#!/usr/bin/env python3
"""V1438 local-only sanity verifier for the V1437 Wi-Fi test boot artifact."""

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
    / "v1437-wifi-test-boot-immediate-endpoint-sampler"
    / "manifest.json"
)
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1438-wifi-test-boot-immediate-endpoint-artifact-sanity"
DEFAULT_REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1438_WIFI_TEST_BOOT_IMMEDIATE_ENDPOINT_ARTIFACT_SANITY_2026-06-01.md"
)
EXPECTED_DECISION = "v1437-wifi-test-boot-immediate-endpoint-source-build-pass"
EXPECTED_HELPER = "a90_android_execns_probe_v286"
EXPECTED_BOOT_MARKERS = (
    "A90 Linux init 0.9.80 (v1437-wifitest)",
    "a90_android_execns_probe v286",
    "A90v1437",
    "wifi test boot armed",
    "/cache/native-init-wifi-test-boot-v1437.log",
    "/cache/native-init-wifi-test-boot-v1437.summary",
    "/cache/native-init-wifi-test-boot-v1437.pid",
    "/cache/native-init-wifi-test-boot-v1437-supervisor.pid",
    "/cache/native-init-wifi-test-boot-v1437-rc1-watcher.result",
    "/cache/native-init-wifi-test-boot-v1437-rc1-window.result",
    "debugfs_mount_requested",
    "debugfs prepare rc=",
    "pid1_rc1_watcher_requested",
    "pid1 rc1 watcher",
    "delay_ms=%d",
    "rc1_window_sampler_requested",
    "rc1_window_sample label=%s",
    "read-only-v1437-immediate-endpoint",
    "sample=%s endpoint_sampler=1",
    "rc1_immediate_endpoint_sampler_requested",
    "rc1_immediate_sample label=%s",
    "sample=%s immediate_endpoint_sampler=1",
    "immediate_regulator",
    "immediate_clk",
    "immediate_debug_gpio",
    "immediate_pinmux",
    "immediate_pinconf",
    "immediate_pcie1_current_link_state",
    "immediate_pcie1_link_state",
    "after_case_0ms",
    "after_case_1ms",
    "after_case_5ms",
    "after_case_20ms",
    "/dev/kmsg",
    "/proc/kmsg",
    "state=drain-kmsg-failed",
    "/proc/interrupts",
    "/sys/kernel/debug/gpio",
    "/sys/kernel/debug/pinctrl/3000000.pinctrl/pins",
    "/sys/kernel/debug/pinctrl/3000000.pinctrl/pinmux-pins",
    "/sys/kernel/debug/pinctrl/3000000.pinctrl/pinconf-pins",
    "/sys/kernel/debug/regulator/regulator_summary",
    "/sys/kernel/debug/clk/clk_summary",
    "/sys/devices/platform/soc/1c08000.qcom,pcie/current_link_state",
    "/sys/kernel/debug/pci-msm/case",
    "/sys/kernel/debug/pci-msm/rc_sel",
)
EXPECTED_ABSENT_MARKERS = (
    "pid1 rc1 watcher retry index=%d",
)


def boot_absent_marker_check(path: Path) -> dict[str, Any]:
    strings = base.run(["strings", path]).stdout
    present = [marker for marker in EXPECTED_ABSENT_MARKERS if marker in strings]
    return {
        "path": base.rel(path),
        "present": present,
        "absent_ok": not present,
    }


def contract_check(wifi_test: dict[str, Any]) -> dict[str, Any]:
    expected = {
        "label": "v1437",
        "fresh_log": True,
        "summary_watcher": True,
        "supervise_helper": True,
        "supervisor_timeout_sec": 40,
        "watch_sec": 35,
        "mount_debugfs": True,
        "pid1_rc1_watcher": True,
        "rc1_watcher_timeout_sec": 45,
        "rc1_watcher_delay_ms": 250,
        "rc1_watcher_result": "/cache/native-init-wifi-test-boot-v1437-rc1-watcher.result",
        "rc1_window_sampler": True,
        "rc1_window_result": "/cache/native-init-wifi-test-boot-v1437-rc1-window.result",
        "rc1_endpoint_sampler": True,
        "rc1_focused_endpoint_sampler": True,
        "rc1_immediate_endpoint_sampler": True,
        "rc1_retry_count": 0,
        "rc1_retry_delay_ms": 0,
    }
    observed = {key: wifi_test.get(key) for key in expected}
    mismatches = {
        key: {"expected": expected[key], "observed": observed[key]}
        for key in expected
        if observed[key] != expected[key]
    }
    return {
        **observed,
        "mismatches": mismatches,
        "ok": not mismatches,
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
        checks["boot_absent_markers"]["absent_ok"],
        checks["header_parity"]["header_args_ok"],
        checks["header_parity"]["kernel_sha256_ok"],
        checks["forbidden_bytes"]["ok"],
        checks["private_modes"]["ok"],
        checks["wifi_test_contract"]["ok"],
    ]
    if all(bool(item) for item in required):
        return (
            "v1438-wifi-test-boot-immediate-endpoint-artifact-sanity-pass",
            True,
            "V1437 immediate endpoint test boot artifact passed local sanity; a bounded live handoff may be planned separately",
        )
    return (
        "v1438-wifi-test-boot-immediate-endpoint-artifact-sanity-blocked",
        False,
        "V1437 artifact sanity failed; fix local artifact before any flash handoff",
    )


def render_report(manifest: dict[str, Any], result: dict[str, Any]) -> str:
    checks = result["checks"]
    return "\n".join(
        [
            "# Native Init V1438 Wi-Fi Test Boot Immediate Endpoint Artifact Sanity",
            "",
            "## Summary",
            "",
            "- Cycle: `V1438`",
            "- Type: local-only artifact sanity verifier",
            f"- Decision: `{result['decision']}`",
            f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
            f"- V1437 manifest: `{manifest['_path']}`",
            f"- V1437 boot image: `{manifest['boot_image']}`",
            "",
            "## Checks",
            "",
            f"- manifest decision: `{checks['manifest']['decision_ok']}`",
            f"- base boot exists: `{checks['base_boot']['exists']}`",
            f"- init static: `{checks['static']['init_binary']['no_dynamic_section'] and checks['static']['init_binary']['no_interp']}`",
            f"- helper static: `{checks['static']['helper']['no_dynamic_section'] and checks['static']['helper']['no_interp']}`",
            f"- ramdisk entries: `{checks['ramdisk']['entries_ok']}`",
            f"- boot markers: `{checks['boot_markers']['markers_ok']}`",
            f"- retry markers absent: `{checks['boot_absent_markers']['absent_ok']}`",
            f"- immediate endpoint sampler contract: `{checks['wifi_test_contract']['ok']}`",
            f"- RC1 watcher delay ms: `{checks['wifi_test_contract']['rc1_watcher_delay_ms']}`",
            f"- RC1 retry count: `{checks['wifi_test_contract']['rc1_retry_count']}`",
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
            f"- RC1 watcher result path: `{manifest['wifi_test']['rc1_watcher_result']}`",
            f"- RC1 window result path: `{manifest['wifi_test']['rc1_window_result']}`",
            "",
            "## Safety Scope",
            "",
            "No device command, flash, reboot, boot partition write, partition write,",
            "Wi-Fi HAL, scan/connect, credential handling, DHCP/routes, external ping,",
            "PMIC/GPIO/GDSC direct write, blind eSoC notify/`BOOT_DONE` spoof, global",
            "PCI rescan, or platform bind/unbind was performed.",
            "",
            "## Next",
            "",
            "V1439 may perform a rollbackable live handoff for only the V1437 test",
            "image, expect `A90 Linux init 0.9.80 (v1437-wifitest)`, collect the",
            "V1437 log, summary, RC1 watcher result, immediate endpoint window",
            "result, expanded dmesg markers, and `wlan0` state, then roll back to",
            "`stage3/boot_linux_v724.img` and verify selftest fail=0.",
            "",
        ]
    )


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
    decision, passed, reason = decide(checks)
    result = {
        "cycle": "V1438",
        "decision": decision,
        "pass": passed,
        "reason": reason,
        "checks": checks,
        "guardrails": {
            "local_only": True,
            "device_command_executed": False,
            "flash_executed": False,
            "wifi_hal_scan_connect_executed": False,
            "credential_use_executed": False,
            "dhcp_route_external_ping_executed": False,
            "pmic_gpio_gdsc_write_executed": False,
            "esoc_notify_boot_done_executed": False,
            "global_pci_rescan_executed": False,
            "platform_bind_unbind_executed": False,
        },
        "next_gate": "V1439 rollbackable live handoff for only the V1437 image",
    }
    store.write_json("manifest.json", result)
    store.write_text("summary.md", render_report(manifest, result))
    if args.write_report:
        write_private_text(args.report_path, render_report(manifest, result))
    print(
        json.dumps(
            {
                "decision": result["decision"],
                "pass": result["pass"],
                "out_dir": base.rel(args.out_dir),
                "next_gate": result["next_gate"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

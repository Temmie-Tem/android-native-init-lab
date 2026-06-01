#!/usr/bin/env python3
"""V1463 local-only sanity verifier for the V1462 Wi-Fi test boot artifact."""

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
    / "v1462-wifi-test-boot-exact-provider-tracepoint-sampler"
    / "manifest.json"
)
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1463-wifi-test-boot-exact-provider-tracepoint-artifact-sanity"
DEFAULT_REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1463_WIFI_TEST_BOOT_EXACT_PROVIDER_TRACEPOINT_ARTIFACT_SANITY_2026-06-01.md"
)
EXPECTED_DECISION = "v1462-wifi-test-boot-exact-provider-tracepoint-source-build-pass"
EXPECTED_BOOT_MARKERS = (
    "A90 Linux init 0.9.86 (v1462-wifitest)",
    "a90_android_execns_probe v286",
    "A90v1462",
    "wifi test boot armed",
    "/cache/native-init-wifi-test-boot-v1462.log",
    "/cache/native-init-wifi-test-boot-v1462.summary",
    "/cache/native-init-wifi-test-boot-v1462.pid",
    "/cache/native-init-wifi-test-boot-v1462-supervisor.pid",
    "/cache/native-init-wifi-test-boot-v1462-rc1-watcher.result",
    "/cache/native-init-wifi-test-boot-v1462-rc1-window.result",
    "debugfs_mount_requested",
    "debugfs prepare rc=",
    "pid1_rc1_watcher_requested",
    "pid1 rc1 watcher",
    "delay_ms=%d",
    "rc1_window_sampler_requested",
    "rc1_window_sample label=%s",
    "read-only-v1462-exact-provider-tracepoint",
    "state=armed sampler=%s detect_elapsed_ms=%ld delay_ms=%d exact_provider_line=%d long_provider_window=%d tracepoint_sampler=%d line=%.*s",
    "provider_trigger_tracepoint_sampler_requested",
    "provider tracepoint arm",
    "provider tracepoint disarm",
    "provider_tracepoint_sample label=%s",
    "provider_gpio_trace",
    "/sys/kernel/debug/tracing/events/gpio/gpio_value/enable",
    "/sys/kernel/debug/tracing/events/gpio/gpio_direction/enable",
    "/sys/kernel/debug/tracing/tracing_on",
    "/sys/kernel/debug/tracing/trace",
    "gpio_value: 1270",
    "gpio_direction: 1270",
    "gpio_value: 135",
    "gpio_direction: 135",
    "gpio_value: 142",
    "gpio_direction: 142",
    "sample=%s endpoint_sampler=1",
    "rc1_micro_endpoint_sampler_requested",
    "rc1_micro_sample label=%s",
    "sample=%s micro_endpoint_sampler=1",
    "micro_interrupts",
    "micro_debug_gpio",
    "micro_pcie1_current_link_state",
    "micro_pcie1_link_state",
    "provider_micro_after_trigger_%dms",
    "post_provider_micro_1200ms",
    "provider_thread_state label=%s",
    "sample=%s provider_thread_state=1",
    "provider_thread_comm",
    "provider_thread_wchan",
    "provider_thread_status",
    "/proc/%d/wchan",
    "/dev/kmsg",
    "/proc/kmsg",
    "/proc/interrupts",
    "/sys/kernel/debug/gpio",
    "/sys/kernel/debug/pinctrl/3000000.pinctrl/pins",
    "/sys/kernel/debug/pinctrl/3000000.pinctrl/pinmux-pins",
    "/sys/kernel/debug/pinctrl/3000000.pinctrl/pinconf-pins",
    "/sys/kernel/debug/regulator/regulator_summary",
    "/sys/kernel/debug/clk/clk_summary",
    "/sys/devices/platform/soc/1c08000.qcom,pcie/current_link_state",
)
EXPECTED_ABSENT_MARKERS = (
    "pid1 rc1 watcher retry index=%d",
    "read-only-v1450-provider-trigger-micro-endpoint",
    "read-only-v1454-exact-provider-long-endpoint",
    "read-only-v1458-exact-provider-thread-state",
    "read-only-v1437-immediate-endpoint",
    "read-only-v1441-micro-endpoint",
    "read-only-v1445-case-aligned-micro-endpoint",
    "rc1_immediate_sample label=%s",
    "sample=%s immediate_endpoint_sampler=1",
    "rc1_micro_writer_summary",
    "micro_writer rc=%d",
    "writer_wait_rc=%d",
    "case_aligned_micro_after_case_%dms",
    "post_provider_micro_200ms",
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
        "label": "v1462",
        "fresh_log": True,
        "summary_watcher": True,
        "supervise_helper": True,
        "supervisor_timeout_sec": 40,
        "watch_sec": 35,
        "mount_debugfs": True,
        "pid1_rc1_watcher": True,
        "rc1_watcher_timeout_sec": 45,
        "rc1_watcher_delay_ms": 0,
        "rc1_watcher_result": "/cache/native-init-wifi-test-boot-v1462-rc1-watcher.result",
        "rc1_window_sampler": True,
        "rc1_window_result": "/cache/native-init-wifi-test-boot-v1462-rc1-window.result",
        "rc1_endpoint_sampler": True,
        "rc1_focused_endpoint_sampler": False,
        "rc1_immediate_endpoint_sampler": False,
        "rc1_micro_endpoint_sampler": True,
        "rc1_case_aligned_micro_endpoint_sampler": False,
        "provider_trigger_micro_endpoint_sampler": True,
        "provider_trigger_exact_line": True,
        "provider_trigger_long_window": True,
        "provider_trigger_thread_state": True,
        "provider_trigger_tracepoint_sampler": True,
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
            "v1463-wifi-test-boot-exact-provider-tracepoint-artifact-sanity-pass",
            True,
            "V1462 exact provider tracepoint test boot artifact passed local sanity; a bounded live handoff may be planned separately",
        )
    return (
        "v1463-wifi-test-boot-exact-provider-tracepoint-artifact-sanity-blocked",
        False,
        "V1462 artifact sanity failed; fix local artifact before any flash handoff",
    )


def render_report(manifest: dict[str, Any], result: dict[str, Any]) -> str:
    checks = result["checks"]
    return "\n".join(
        [
            "# Native Init V1463 Wi-Fi Test Boot Exact Provider Tracepoint Artifact Sanity",
            "",
            "## Summary",
            "",
            "- Cycle: `V1463`",
            "- Type: local-only artifact sanity verifier",
            f"- Decision: `{result['decision']}`",
            f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
            f"- V1462 manifest: `{manifest['_path']}`",
            f"- V1462 boot image: `{manifest['boot_image']}`",
            "",
            "## Checks",
            "",
            f"- manifest decision: `{checks['manifest']['decision_ok']}`",
            f"- base boot exists: `{checks['base_boot']['exists']}`",
            f"- init static: `{checks['static']['init_binary']['no_dynamic_section'] and checks['static']['init_binary']['no_interp']}`",
            f"- helper static: `{checks['static']['helper']['no_dynamic_section'] and checks['static']['helper']['no_interp']}`",
            f"- ramdisk entries: `{checks['ramdisk']['entries_ok']}`",
            f"- boot markers: `{checks['boot_markers']['markers_ok']}`",
            f"- retry/legacy/case-writer markers absent: `{checks['boot_absent_markers']['absent_ok']}`",
            f"- exact provider tracepoint contract: `{checks['wifi_test_contract']['ok']}`",
            f"- provider tracepoint sampler: `{checks['wifi_test_contract']['provider_trigger_tracepoint_sampler']}`",
            f"- provider thread-state: `{checks['wifi_test_contract']['provider_trigger_thread_state']}`",
            f"- exact provider line: `{checks['wifi_test_contract']['provider_trigger_exact_line']}`",
            f"- provider long window: `{checks['wifi_test_contract']['provider_trigger_long_window']}`",
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
            "V1464 may perform a rollbackable live handoff for only the V1462 test",
            "image, expect `A90 Linux init 0.9.86 (v1462-wifitest)`, collect the",
            "V1462 log, summary, RC1 watcher result, exact-provider tracepoint window",
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
    helper = args.manifest.parent / "a90_android_execns_probe_v286"
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
    label, pass_ok, reason = decide(checks)
    result = {
        "cycle": "V1463",
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
        "out_dir": base.rel(args.out_dir),
    }, indent=2, sort_keys=True))
    return 0 if pass_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

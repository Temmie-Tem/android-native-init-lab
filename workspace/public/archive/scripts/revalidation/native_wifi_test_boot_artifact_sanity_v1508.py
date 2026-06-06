#!/usr/bin/env python3
"""V1508 local-only sanity verifier for the V1507 batched pre-L0 Wi-Fi test boot."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import native_wifi_test_boot_artifact_sanity_v1500 as base


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
DEFAULT_MANIFEST = (
    REPO_ROOT
    / "tmp"
    / "wifi"
    / "v1507-wifi-batched-pre-l0-parity-test-boot"
    / "manifest.json"
)
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1508-wifi-batched-pre-l0-parity-artifact-sanity"
DEFAULT_REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1508_WIFI_BATCHED_PRE_L0_PARITY_ARTIFACT_SANITY_2026-06-01.md"
)
EXPECTED_DECISION = "v1507-wifi-batched-pre-l0-parity-test-boot-source-build-pass"
EXPECTED_BOOT_MARKERS = (
    "A90 Linux init 0.9.95 (v1507-wifitest)",
    "a90_android_execns_probe v287",
    "A90v1507",
    "wifi test boot armed",
    "/cache/native-init-wifi-test-boot-v1507.log",
    "/cache/native-init-wifi-test-boot-v1507.summary",
    "/cache/native-init-wifi-test-boot-v1507.pid",
    "/cache/native-init-wifi-test-boot-v1507-supervisor.pid",
    "/cache/native-init-wifi-test-boot-v1507-rc1-watcher.result",
    "/cache/native-init-wifi-test-boot-v1507-batched-pre-l0-parity.result",
    "auto-v1485-wifi-readiness-test",
    "auto_readiness_supervisor_requested",
    "auto_readiness_pid1.begin=1",
    "auto_readiness_pid1.primary_checkpoint=%s",
    "auto_readiness_pid1.safety_credentials=0",
    "--pm-observer-auto-readiness-summary",
    "pid1_rc1_watcher_requested",
    "rc1_window_sampler_requested",
    "rc1_micro_endpoint_sampler_requested",
    "rc1_micro_batched_focused_endpoint_sampler_requested",
    "rc1_case_aligned_micro_endpoint_sampler_requested",
    "endpoint_sampler=1",
    "focused_regulator",
    "focused_clk",
    "micro_endpoint_sampler=1",
    "micro_batched_focused_endpoint_sampler=1",
    "micro_interrupts",
    "micro_debug_gpio",
    "micro_batched_regulator",
    "micro_batched_clk",
    "micro_batched_debug_gpio",
    "micro_batched_pinmux",
    "micro_batched_pinconf",
    "micro_pcie1_current_link_state",
    "case_aligned_micro_after_case_%dms",
    "post_case_aligned_micro_200ms",
    "pcie_1_gdsc",
    "gcc_pcie_1_pipe_clk",
    "gcc_pcie_1_clkref_clk",
    "gpio102",
    "gpio103",
    "gpio104",
    "gpio135",
    "gpio142",
    "/sys/kernel/debug/pci-msm/rc_sel",
    "/sys/kernel/debug/pci-msm/case",
    "/sys/kernel/debug/regulator/regulator_summary",
    "/sys/kernel/debug/clk/clk_summary",
    "/sys/kernel/debug/gpio",
    "/sys/devices/platform/soc/1c08000.qcom,pcie/current_link_state",
)


def contract_check(wifi_test: dict[str, Any]) -> dict[str, Any]:
    expected = {
        "label": "v1507",
        "fresh_log": True,
        "summary_watcher": True,
        "supervise_helper": True,
        "supervisor_timeout_sec": 70,
        "watch_sec": 45,
        "mount_debugfs": True,
        "pid1_rc1_watcher": True,
        "rc1_watcher_timeout_sec": 70,
        "rc1_watcher_delay_ms": 0,
        "rc1_watcher_result": "/cache/native-init-wifi-test-boot-v1507-rc1-watcher.result",
        "rc1_window_sampler": True,
        "rc1_window_result": "/cache/native-init-wifi-test-boot-v1507-batched-pre-l0-parity.result",
        "rc1_endpoint_sampler": True,
        "rc1_focused_endpoint_sampler": True,
        "rc1_immediate_endpoint_sampler": False,
        "rc1_micro_endpoint_sampler": True,
        "rc1_micro_focused_endpoint_sampler": False,
        "rc1_micro_batched_focused_endpoint_sampler": True,
        "rc1_case_aligned_micro_endpoint_sampler": True,
        "provider_trigger_micro_endpoint_sampler": False,
        "provider_trigger_exact_line": False,
        "provider_trigger_long_window": False,
        "provider_trigger_thread_state": False,
        "provider_trigger_tracepoint_sampler": False,
        "provider_trigger_pil_tracepoint_sampler": False,
        "provider_trigger_effective_level_sampler": False,
        "provider_trigger_ap2mdm_hold": False,
        "auto_readiness_supervisor": True,
        "rc1_retry_count": 0,
        "rc1_retry_delay_ms": 0,
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
            "v1508-wifi-batched-pre-l0-parity-artifact-sanity-pass",
            True,
            "V1507 batched pre-L0 parity test boot artifact passed local sanity; a rollbackable live handoff may be planned separately",
        )
    return (
        "v1508-wifi-batched-pre-l0-parity-artifact-sanity-blocked",
        False,
        "V1507 artifact sanity failed; fix local artifact before any flash handoff",
    )


def render_report(manifest: dict[str, Any], result: dict[str, Any]) -> str:
    checks = result["checks"]
    return "\n".join([
        "# Native Init V1508 Wi-Fi Batched Pre-L0 Parity Artifact Sanity",
        "",
        "## Summary",
        "",
        "- Cycle: `V1508`",
        "- Type: local-only artifact sanity verifier",
        f"- Decision: `{result['decision']}`",
        f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
        f"- V1507 manifest: `{manifest['_path']}`",
        f"- V1507 boot image: `{manifest['boot_image']}`",
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
        f"- batched pre-L0 parity contract: `{checks['wifi_test_contract']['ok']}`",
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
        f"- marker: `auto-v1485-wifi-readiness-test`",
        f"- helper marker: `{manifest['helper_marker']}`",
        "",
        "## Verified Test Scope",
        "",
        "- The test image keeps PID1-triggered corrected RC1 enumerate after provider trigger.",
        "- The test image records case-aligned micro samples at 0/1/2/5/10/20/50/100/150ms after `case=11`.",
        "- The test image scans each focused debugfs file at most once per micro sample.",
        "- The test image emits `micro_batched_regulator`, `micro_batched_clk`, `micro_batched_debug_gpio`, `micro_batched_pinmux`, and `micro_batched_pinconf`.",
        "- The test image blocks Wi-Fi HAL start, scan/connect, credential use, DHCP/routes, and external ping.",
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
        "V1509 may perform a rollbackable live handoff for only the V1507 test image,",
        "expect `A90 Linux init 0.9.95 (v1507-wifitest)`, collect the V1507 log,",
        "summary, RC1 watcher result, batched pre-L0 parity result, focused dmesg, and",
        "`wlan0` state, then roll back to `stage3/boot_linux_v724.img` and verify",
        "selftest `fail=0`.",
        "",
    ])


def main() -> int:
    base.DEFAULT_MANIFEST = DEFAULT_MANIFEST
    base.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    base.DEFAULT_REPORT_PATH = DEFAULT_REPORT_PATH
    base.EXPECTED_DECISION = EXPECTED_DECISION
    base.EXPECTED_BOOT_MARKERS = EXPECTED_BOOT_MARKERS
    base.contract_check = contract_check
    base.decide = decide
    base.render_report = render_report
    rc = base.main()
    if rc == 0:
        manifest_path = DEFAULT_OUT_DIR / "manifest.json"
        if manifest_path.exists():
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
            payload["cycle"] = "V1508"
            base.write_private_text(
                manifest_path,
                json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            )
    return rc


if __name__ == "__main__":
    raise SystemExit(main())

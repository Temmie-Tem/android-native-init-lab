#!/usr/bin/env python3
"""V1519 host-only Android-good vs native-fail critical-source comparison."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1519-android-good-native-fail-critical-comparison")
DEFAULT_REPORT_PATH = Path(
    "docs/reports/NATIVE_INIT_V1519_ANDROID_GOOD_NATIVE_FAIL_CRITICAL_SOURCE_COMPARISON_2026-06-01.md"
)
LATEST_POINTER = Path("tmp/wifi/latest-v1519-android-good-native-fail-critical-comparison.txt")
V1518_MANIFEST = Path("tmp/wifi/v1518-wifi-critical-source-timing-classifier/manifest.json")
V1517_RC1 = Path("tmp/wifi/v1517-wifi-critical-source-pre-l0-handoff/test-rc1-window-result.stdout.txt")
V1239_MANIFEST = Path("tmp/wifi/v1239-post-esoc0-powerup-gap-classifier/manifest.json")
V896_MANIFEST = Path("tmp/wifi/v896-android-mdm-helper-image-contract/manifest.json")
V852_MANIFEST = Path("tmp/wifi/v852-android-ext-mdm-provider-surface-handoff/manifest.json")
V1331_MANIFEST = Path("tmp/wifi/v1331-android-sdx50m-timing-handoff/manifest.json")
FORBIDDEN_OUTPUT_ENV_KEYS = ("A90_WIFI_SSID", "A90_WIFI_PSK")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def rel(path: Path) -> str:
    resolved = repo_path(path)
    try:
        return str(resolved.relative_to(repo_path(".")))
    except ValueError:
        return str(resolved)


def load_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {}
    try:
        data = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def read_text(path: Path, limit: int = 4 * 1024 * 1024) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    return resolved.read_bytes()[:limit].decode("utf-8", errors="replace")


def first_match(lines: list[str], pattern: str) -> str:
    regex = re.compile(pattern, re.IGNORECASE)
    for line in lines:
        if regex.search(line):
            return line.strip()
    return ""


def as_bool(value: Any) -> bool:
    return value is True


def nested(mapping: dict[str, Any], *keys: str, default: Any = None) -> Any:
    current: Any = mapping
    for key in keys:
        if not isinstance(current, dict):
            return default
        current = current.get(key)
    return default if current is None else current


def extract_native_first_window(rc1_text: str) -> dict[str, Any]:
    prefix = "sample=case_aligned_micro_after_case_0ms"
    lines = [line for line in rc1_text.splitlines() if line.startswith(prefix)]
    return {
        "gpio135_line": first_match(lines, r"gpio135\s*:"),
        "gpio142_line": first_match(lines, r"gpio142\s*:"),
        "gpio142_irq_line": first_match(lines, r"msmgpio-dc\s+142\s+Edge\s+mdm status"),
        "pcie1_gdsc_line": first_match(lines, r"pcie_1_gdsc"),
        "pcie_gpio102_pinmux": first_match(lines, r"pin 102 .*qcom,pcie"),
        "pcie_gpio103_pinmux": first_match(lines, r"pin 103 .*qcom,pcie"),
        "pcie_gpio104_pinmux": first_match(lines, r"pin 104 .*qcom,pcie"),
        "mdm_gpio135_pinmux": first_match(lines, r"pin 135 .*qcom,mdm3"),
        "mdm_gpio142_pinmux": first_match(lines, r"pin 142 .*qcom,mdm3"),
        "source_count": len(lines),
        "has_first_window": bool(lines),
    }


def classify() -> dict[str, Any]:
    v1518 = load_json(V1518_MANIFEST)
    v1239 = load_json(V1239_MANIFEST)
    v896 = load_json(V896_MANIFEST)
    v852 = load_json(V852_MANIFEST)
    v1331 = load_json(V1331_MANIFEST)
    rc1_text = read_text(V1517_RC1)
    native_window = extract_native_first_window(rc1_text)

    native_progress = nested(v1518, "checks", "progress", default={}) or {}
    native_timing = nested(v1518, "checks", "timing", default={}) or {}
    native_dmesg = nested(v1518, "checks", "dmesg", default={}) or {}

    v852_from_v896 = v896.get("v852") or {}
    v852_context_state = nested(v852, "context", "comparison", "state", default={}) or {}
    android_gpio_lines = [
        str(line)
        for line in (
            v852_from_v896.get("gpio_focus_lines")
            or nested(v852, "context", "comparison", "state", "gpio_focus_lines", default=[])
            or []
        )
    ]
    android = {
        "v1239_pass": as_bool(v1239.get("pass")),
        "v852_pass": as_bool(v852.get("pass")) or as_bool(v852_from_v896.get("pass")),
        "v896_pass": as_bool(v896.get("pass")),
        "v1331_pass": as_bool(v1331.get("pass")),
        "mdm3_online": nested(v1239, "android", "mdm3_online", default=False) is True
        or v852_from_v896.get("mdm3_state") == "ONLINE"
        or v852_context_state.get("mdm3_state") == "ONLINE",
        "gpio142_irq_count": nested(v1239, "android", "gpio142_irq_count", default=0),
        "pcie_l0_time": nested(v1239, "android", "pcie_l0_time"),
        "pcie_l0_lines": nested(v1239, "android", "pcie_l0_lines", default=0),
        "pcie_reset_time": nested(v1239, "android", "pcie_reset_time"),
        "wlfw_present": nested(v1239, "android", "wlfw_present", default=False) is True,
        "bdf_present": nested(v1239, "android", "bdf_present", default=False) is True,
        "wlan0_present": nested(v1239, "android", "wlan0_present", default=False) is True,
        "v1331_wlfw_start": nested(v1331, "context", "comparison", "state", "first_wlfw_start"),
        "v1331_subsys_get_esoc0": nested(v1331, "context", "comparison", "state", "first_subsys_get_esoc0"),
        "gpio135_static_line": first_match(android_gpio_lines, r"^\s*gpio135\s*:"),
        "gpio142_static_line": first_match(android_gpio_lines, r"^\s*gpio142\s*:"),
        "mdm_gpio135_pinmux": first_match(android_gpio_lines, r"pin 135 .*qcom,mdm3"),
        "mdm_gpio142_pinmux": first_match(android_gpio_lines, r"pin 142 .*qcom,mdm3"),
    }
    native = {
        "v1518_pass": as_bool(v1518.get("pass")),
        "v1518_decision": v1518.get("decision"),
        "final_decision": native_progress.get("final_decision"),
        "provider_trigger": native_progress.get("provider_trigger") is True,
        "rc1_progress": native_progress.get("rc1_progress") is True,
        "rc1_l0": native_progress.get("rc1_l0") is True,
        "rc1_link_failed": native_progress.get("rc1_link_failed") is True,
        "mhi_progress": native_progress.get("mhi_progress") is True,
        "wlfw_progress": native_progress.get("wlfw_progress") is True,
        "bdf_progress": native_progress.get("bdf_progress") is True,
        "fw_ready_progress": native_progress.get("fw_ready_progress") is True,
        "wlan0_present": native_progress.get("wlan0_present") is True,
        "link_failed_after_case_ms": native_timing.get("link_failed_after_case_ms"),
        "max_expected_source_end_ms": native_timing.get("max_expected_source_end_ms"),
        "all_expected_before_link_fail": native_timing.get("all_expected_before_link_fail") is True,
        "ltssm_states": native_dmesg.get("ltssm_states") or [],
        "first_window": native_window,
    }

    native_first_window_solid = all(
        [
            native["v1518_pass"],
            native["final_decision"] == "rc1-ltssm-link-failed-no-l0",
            native["provider_trigger"],
            native["rc1_progress"],
            native["rc1_link_failed"],
            not native["rc1_l0"],
            not native["mhi_progress"],
            not native["wlfw_progress"],
            not native["bdf_progress"],
            not native["fw_ready_progress"],
            not native["wlan0_present"],
            native["all_expected_before_link_fail"],
            native_window["has_first_window"],
        ]
    )
    android_positive = all(
        [
            android["v1239_pass"],
            android["v852_pass"],
            android["v896_pass"],
            android["mdm3_online"],
            int(android["gpio142_irq_count"] or 0) > 0,
            int(android["pcie_l0_lines"] or 0) > 0,
            android["wlfw_present"],
            android["bdf_present"],
            android["wlan0_present"],
        ]
    )
    static_gpio_low_parity = all(
        [
            "gpio135" in native_window["gpio135_line"],
            "out 0" in native_window["gpio135_line"],
            "gpio142" in native_window["gpio142_line"],
            "in 0" in native_window["gpio142_line"],
            "gpio135" in android["gpio135_static_line"],
            "out 0" in android["gpio135_static_line"],
            "gpio142" in android["gpio142_static_line"],
            "in  0" in android["gpio142_static_line"] or "in 0" in android["gpio142_static_line"],
        ]
    )
    matched_android_critical_missing = not all(
        [
            android.get("pcie_reset_time") is not None,
            android.get("pcie_l0_time") is not None,
            android.get("gpio135_static_line"),
            android.get("gpio142_static_line"),
        ]
    ) or not any("pcie_1_gdsc" in line for line in android_gpio_lines)

    checks = [
        {
            "name": "native-source-exact-fail-window",
            "status": "pass" if native_first_window_solid else "blocked",
            "detail": "V1518 preserves rc1-ltssm-link-failed-no-l0 with selected sources before link fail",
        },
        {
            "name": "android-positive-lower-chain",
            "status": "pass" if android_positive else "blocked",
            "detail": "Android reference reaches mdm3 ONLINE, GPIO142 IRQ, PCIe L0, WLFW/BDF, and wlan0",
        },
        {
            "name": "static-gpio-low-is-not-discriminating",
            "status": "pass" if static_gpio_low_parity else "blocked",
            "detail": "Native and Android snapshots both include GPIO135/GPIO142 low readback, so low snapshot alone cannot explain failure",
        },
        {
            "name": "matched-android-critical-source-gap",
            "status": "pass" if matched_android_critical_missing else "blocked",
            "detail": "Existing Android-good evidence lacks the same pre-L0 critical source snapshot set, especially pcie_1_gdsc/refclk/PERST timing",
        },
    ]
    pass_ok = all(check["status"] == "pass" for check in checks)
    if pass_ok:
        decision = "v1519-android-good-native-fail-compared-matched-rc1-source-capture-needed"
        reason = "native source-exact failure and Android-good lower chain are consistent, but existing Android evidence is not matched enough to assign the no-L0 root cause"
        next_step = "V1520 should capture or classify an Android-good matched critical-source RC1 timeline before another native mutation"
    else:
        decision = "v1519-comparison-inputs-incomplete"
        reason = "one or more Android/native evidence inputs are missing or contradictory"
        next_step = "refresh the missing host evidence before planning another live gate"

    return {
        "cycle": "V1519",
        "generated_at": now_iso(),
        "inputs": {
            "v1518": rel(V1518_MANIFEST),
            "v1517_rc1_result": rel(V1517_RC1),
            "v1239": rel(V1239_MANIFEST),
            "v896": rel(V896_MANIFEST),
            "v852": rel(V852_MANIFEST),
            "v1331": rel(V1331_MANIFEST),
        },
        "host": collect_host_metadata(),
        "native": native,
        "android": android,
        "checks": checks,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "device_commands_executed": False,
        "device_mutations": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "wifi_bringup_executed": False,
        "pmic_gpio_gdsc_write_executed": False,
        "blind_esoc_notify_executed": False,
        "boot_done_spoof_executed": False,
        "global_pci_rescan_executed": False,
        "platform_bind_unbind_executed": False,
        "flash_executed": False,
        "boot_image_write_executed": False,
        "partition_write_executed": False,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    native = manifest["native"]
    android = manifest["android"]
    first = native["first_window"]
    return "\n".join(
        [
            "# Native Init V1519 Android-Good vs Native-Fail Critical Source Comparison",
            "",
            "## Summary",
            "",
            "- Cycle: `V1519`",
            "- Type: host-only classifier over existing Android-good and native-fail evidence",
            f"- Decision: `{manifest['decision']}`",
            f"- Result: {'PASS' if manifest['pass'] else 'BLOCKED'}",
            f"- Reason: {manifest['reason']}",
            f"- Evidence: `{DEFAULT_OUT_DIR}`",
            "",
            "## Checks",
            "",
            markdown_table(
                ["check", "status", "detail"],
                [[check["name"], check["status"], check["detail"]] for check in manifest["checks"]],
            ),
            "",
            "## Native-Fail Reference",
            "",
            markdown_table(
                ["field", "value"],
                [
                    ["decision", native["final_decision"]],
                    ["provider_trigger", native["provider_trigger"]],
                    ["RC1 progress/link failed/L0", f"{native['rc1_progress']}/{native['rc1_link_failed']}/{native['rc1_l0']}"],
                    ["MHI/WLFW/BDF/FW-ready/wlan0", f"{native['mhi_progress']}/{native['wlfw_progress']}/{native['bdf_progress']}/{native['fw_ready_progress']}/{native['wlan0_present']}"],
                    ["link failed after case", f"{native['link_failed_after_case_ms']} ms"],
                    ["selected sources end by", f"{native['max_expected_source_end_ms']} ms"],
                    ["LTSSM states", ", ".join(native["ltssm_states"])],
                ],
            ),
            "",
            "## Native First-Window Critical Lines",
            "",
            markdown_table(
                ["source", "line"],
                [
                    ["GPIO135", first["gpio135_line"]],
                    ["GPIO142", first["gpio142_line"]],
                    ["GPIO142 IRQ", first["gpio142_irq_line"]],
                    ["pcie_1_gdsc", first["pcie1_gdsc_line"]],
                    ["PCIe pinmux GPIO102", first["pcie_gpio102_pinmux"]],
                    ["PCIe pinmux GPIO103", first["pcie_gpio103_pinmux"]],
                    ["PCIe pinmux GPIO104", first["pcie_gpio104_pinmux"]],
                    ["MDM pinmux GPIO135", first["mdm_gpio135_pinmux"]],
                    ["MDM pinmux GPIO142", first["mdm_gpio142_pinmux"]],
                ],
            ),
            "",
            "## Android-Good Reference",
            "",
            markdown_table(
                ["field", "value"],
                [
                    ["mdm3_online", android["mdm3_online"]],
                    ["GPIO142 IRQ count", android["gpio142_irq_count"]],
                    ["PCIe reset time", android["pcie_reset_time"]],
                    ["PCIe L0 time/lines", f"{android['pcie_l0_time']} / {android['pcie_l0_lines']}"],
                    ["WLFW/BDF/wlan0", f"{android['wlfw_present']}/{android['bdf_present']}/{android['wlan0_present']}"],
                    ["static GPIO135", android["gpio135_static_line"]],
                    ["static GPIO142", android["gpio142_static_line"]],
                    ["MDM pinmux GPIO135", android["mdm_gpio135_pinmux"]],
                    ["MDM pinmux GPIO142", android["mdm_gpio142_pinmux"]],
                ],
            ),
            "",
            "## Interpretation",
            "",
            "V1519 does not move the blocker downstream. Native still fails at `RC1 LTSSM_POLL_COMPLIANCE -> link failed -> no L0`, while Android-good evidence proves the same stock kernel/hardware can reach GPIO142 IRQ, PCIe L0, WLFW/BDF, and `wlan0`.",
            "",
            "The important correction is that GPIO135/GPIO142 low readback is not, by itself, a discriminating root cause: existing Android-good static snapshots also show GPIO135/GPIO142 low while Android reaches the lower Wi-Fi chain. The remaining gap is a matched Android-good critical-source timeline for pcie1 GDSC/clock/refclk/PERST/reset and the exact RC1 normal path.",
            "",
            "## Safety Scope",
            "",
            "This classifier is host-only. It performs no device command, flash, reboot, partition write, Wi-Fi HAL start, scan/connect, credential handling, DHCP/routes, external ping, PMIC/GPIO/GDSC write, eSoC notify/`BOOT_DONE` spoof, global PCI rescan, or platform bind/unbind.",
            "",
            "## Next",
            "",
            f"- {manifest['next_step']}",
            "- Keep firmware/MHI/WLFW/scan/connect work parked until RC1 L0 and PCI enumeration exist.",
            "",
        ]
    )


def check_forbidden_output(manifest: dict[str, Any], summary: str) -> list[str]:
    text = json.dumps(manifest, ensure_ascii=False, sort_keys=True) + "\n" + summary
    leaks: list[str] = []
    for key in FORBIDDEN_OUTPUT_ENV_KEYS:
        value = os.environ.get(key, "")
        if value and value in text:
            leaks.append(key)
    return leaks


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--write-report", action="store_true")
    args = parser.parse_args()

    store = EvidenceStore(repo_path(args.out_dir))
    manifest = classify()
    manifest["command"] = args.command
    if args.command == "plan":
        manifest["decision"] = "v1519-comparison-plan-ready"
        manifest["pass"] = True
        manifest["reason"] = "plan-only host classifier; no device command or mutation"
        manifest["next_step"] = "run V1519 host-only classifier"
    summary = render_summary(manifest)
    leaks = check_forbidden_output(manifest, summary)
    manifest["forbidden_output_env_hits"] = leaks
    if leaks:
        manifest["decision"] = "v1519-forbidden-output-hit"
        manifest["pass"] = False
        manifest["reason"] = "forbidden environment-backed output string detected"
        manifest["next_step"] = "remove sensitive output before continuing"
        summary = render_summary(manifest)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", summary)
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    if args.write_report:
        write_private_text(repo_path(args.report_path), summary)
    print(f"decision: {manifest['decision']}")
    print(f"pass:     {manifest['pass']}")
    print(f"reason:   {manifest['reason']}")
    print(f"next:     {manifest['next_step']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest.get("pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())

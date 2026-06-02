#!/usr/bin/env python3
"""V1661 rollbackable native natural-path power diff handoff."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import native_wifi_natural_path_mdm2ap_handoff_v1632 as v1632
import native_wifi_test_boot_handoff_v1395 as base
from a90harness.evidence import write_private_json, write_private_text


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1661-native-natural-power-diff-handoff"
DEFAULT_REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1661_NATIVE_NATURAL_POWER_DIFF_HANDOFF_2026-06-02.md"
)
DEFAULT_V1661_MANIFEST = (
    REPO_ROOT
    / "tmp"
    / "wifi"
    / "v1661-native-natural-power-diff-test-boot"
    / "manifest.json"
)
DEFAULT_TEST_IMAGE = (
    REPO_ROOT
    / "tmp"
    / "wifi"
    / "v1661-native-natural-power-diff-test-boot"
    / "boot_linux_v1661_native_power_diff.img"
)
TEST_EXPECT_VERSION = "A90 Linux init 0.9.115 (v1661-native-power-diff)"
DEFAULT_TEST_LOG_PATH = "/cache/native-init-wifi-test-boot-v1661.log"
DEFAULT_TEST_SUMMARY_PATH = "/cache/native-init-wifi-test-boot-v1661.summary"
DEFAULT_TEST_HELPER_RESULT_PATH = "/cache/native-init-wifi-test-boot-v1661-helper.result"
DEFAULT_TEST_WATCHER_PATH = "/cache/native-init-wifi-test-boot-v1661-natural-watcher.result"
DEFAULT_TEST_WINDOW_PATH = "/cache/native-init-wifi-test-boot-v1661-natural-window.result"
DEFAULT_DMESG_PATTERN = (
    "A90v1661|subsystem_get|mdm_subsys_powerup|sdx50m_toggle_soft_reset|"
    "pil_notif|fw=esoc0|gpio_value|gpio_direction|GPIO142|mdm status|"
    "mdm errfatal|PCIe RC1|LTSSM|mhi|MHI|wlfw|WLFW|BDF|FW ready|wlan0|ks"
)


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def parse_key_values(text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("[") or line.startswith("A90P1 "):
            continue
        match = re.match(r"^([A-Za-z0-9_.:-]+)=(.*)$", line)
        if match:
            fields[match.group(1)] = match.group(2).strip()
    return fields


def int_field(fields: dict[str, str], key: str, default: int = 0) -> int:
    try:
        return int(str(fields.get(key, default)).strip())
    except (TypeError, ValueError):
        return default


def count_lines(text: str, pattern: str) -> int:
    matcher = re.compile(pattern)
    return sum(1 for line in text.splitlines() if matcher.search(line))


def matching_lines(text: str, pattern: str, limit: int) -> list[str]:
    matcher = re.compile(pattern)
    rows: list[str] = []
    for line in text.splitlines():
        if matcher.search(line):
            rows.append(line[:240])
            if len(rows) >= limit:
                break
    return rows


def parse_power_diff(out_dir: Path) -> dict[str, Any]:
    window = read_text(out_dir / "test-rc1-window-result.stdout.txt")
    fields = parse_key_values(window)
    regulator_snapshot_count = count_lines(window, r"^A90_V1661_REGULATOR_BEGIN")
    clock_snapshot_count = count_lines(window, r"^A90_V1661_CLOCKS_BEGIN")
    subsys_snapshot_count = count_lines(window, r"^A90_V1661_SUBSYS_BEGIN")
    summary_snapshot_count = int_field(fields, "natural_power_diff.snapshot_count", -1)
    safety_keys = {
        key: int_field(fields, key, 0)
        for key in (
            "natural_power_diff.safety_wifi_hal_start",
            "natural_power_diff.safety_scan_connect",
            "natural_power_diff.safety_credentials",
            "natural_power_diff.safety_dhcp_route",
            "natural_power_diff.safety_external_ping",
            "natural_power_diff.safety_pmic_write",
            "natural_power_diff.safety_gpio_write",
            "natural_power_diff.safety_gdsc_write",
            "natural_power_diff.safety_regulator_write",
            "natural_power_diff.safety_forced_rc1",
            "natural_power_diff.safety_pci_rescan",
            "natural_power_diff.safety_platform_bind",
        )
        if key in fields
    }
    return {
        "begin": fields.get("natural_power_diff.begin") == "1",
        "end": fields.get("natural_power_diff.end") == "1",
        "mode": fields.get("natural_power_diff.mode", ""),
        "snapshot_count": summary_snapshot_count,
        "regulator_snapshot_count": regulator_snapshot_count,
        "clock_snapshot_count": clock_snapshot_count,
        "subsys_snapshot_count": subsys_snapshot_count,
        "full_clk_summary_read": int_field(fields, "natural_power_diff.full_clk_summary_read", -1),
        "targeted_named_clocks": int_field(fields, "natural_power_diff.targeted_named_clocks", 0),
        "regulator_summary_full": int_field(fields, "natural_power_diff.regulator_summary_full", 0),
        "subsystem_sequence": int_field(fields, "natural_power_diff.subsystem_sequence", 0),
        "pcie1_gdsc_lines": count_lines(window, r"pcie_1_gdsc"),
        "target_clock_present_lines": count_lines(window, r"^CLOCK .* clk_enable_count="),
        "target_clock_missing_lines": count_lines(window, r"^CLOCK .* missing$"),
        "subsys_mss_lines": count_lines(window, r"name=(mss|modem)"),
        "subsys_esoc0_lines": count_lines(window, r"name=esoc0"),
        "safety_values": safety_keys,
        "safety_zero": all(value == 0 for value in safety_keys.values()),
        "regulator_excerpt": matching_lines(window, r"pcie_1_gdsc|refgen|PM8150|PMXPRAIRIE|VDD", 24),
        "clock_excerpt": matching_lines(window, r"^CLOCK .*?(gcc_pcie|pcie_1|refgen)", 24),
        "subsys_excerpt": matching_lines(window, r"^SUBSYS ", 24),
    }


def power_capture_ok(power: dict[str, Any]) -> bool:
    return bool(
        power["begin"]
        and power["end"]
        and power["snapshot_count"] >= 1
        and power["regulator_snapshot_count"] >= 1
        and power["clock_snapshot_count"] >= 1
        and power["subsys_snapshot_count"] >= 1
        and power["subsys_mss_lines"] >= 1
        and power["subsys_esoc0_lines"] >= 1
        and power["full_clk_summary_read"] == 0
        and power["targeted_named_clocks"] == 1
        and power["regulator_summary_full"] == 1
        and power["subsystem_sequence"] == 1
        and power["safety_zero"]
    )


def render_report(result: dict[str, Any]) -> str:
    observation = result["natural_path_observation"]
    power = result["power_diff_capture"]
    lines = [
        "# Native Init V1661 Native Natural-path Power Diff Handoff",
        "",
        "## Summary",
        "",
        "- Cycle: `V1661`",
        "- Type: one-run rollbackable native natural-path power/clock/sequence capture",
        f"- Decision: `{result['decision']}`",
        f"- Result: {'PASS' if result['pass'] else 'REVIEW'}",
        f"- Natural-path label: `{observation['label']}`",
        f"- Reason: {result['reason']}",
        f"- Evidence: `{result['out_dir']}`",
        f"- Test boot image: `{result['preflight']['test_image']}`",
        f"- Rollback image: `{result['preflight']['rollback_image']}`",
        f"- Rollback ok: `{observation['rollback_ok']}`",
        "",
        "## Natural-path Checks",
        "",
        f"- `provider_trigger_seen`: `{observation['provider_trigger_seen']}`",
        f"- `pil_esoc_seen`: `{observation['pil_esoc_seen']}`",
        f"- `pon_low_seen`: `{observation['pon_low_seen']}`",
        f"- `pon_high_seen`: `{observation['pon_high_seen']}`",
        f"- `ap2mdm_seen`: `{observation['ap2mdm_seen']}`",
        f"- `gpio142_irq_delta`: `{observation['gpio142_irq_delta']}`",
        f"- `errfatal_irq_delta`: `{observation['errfatal_irq_delta']}`",
        f"- `timing_complete`: `{observation['timing_complete']}`",
        f"- `sample_count`: `{observation['sample_count']}`",
        f"- `safety_zero`: `{observation['safety_zero']}`",
        f"- `forbidden_markers_seen`: `{observation['forbidden_markers_seen']}`",
        "",
        "## Power Diff Capture",
        "",
        f"- `mode`: `{power['mode']}`",
        f"- `snapshot_count`: `{power['snapshot_count']}`",
        f"- `regulator_snapshot_count`: `{power['regulator_snapshot_count']}`",
        f"- `clock_snapshot_count`: `{power['clock_snapshot_count']}`",
        f"- `subsys_snapshot_count`: `{power['subsys_snapshot_count']}`",
        f"- `full_clk_summary_read`: `{power['full_clk_summary_read']}`",
        f"- `pcie1_gdsc_lines`: `{power['pcie1_gdsc_lines']}`",
        f"- `target_clock_present_lines`: `{power['target_clock_present_lines']}`",
        f"- `target_clock_missing_lines`: `{power['target_clock_missing_lines']}`",
        f"- `subsys_mss_lines`: `{power['subsys_mss_lines']}`",
        f"- `subsys_esoc0_lines`: `{power['subsys_esoc0_lines']}`",
        f"- `safety_zero`: `{power['safety_zero']}`",
        "",
        "## Excerpts",
        "",
        "### Regulator",
        "",
        *[f"- `{line}`" for line in power["regulator_excerpt"]],
        "",
        "### Clocks",
        "",
        *[f"- `{line}`" for line in power["clock_excerpt"]],
        "",
        "### Subsystems",
        "",
        *[f"- `{line}`" for line in power["subsys_excerpt"]],
        "",
        "## Safety Scope",
        "",
        "This run observes the natural `__subsystem_get(esoc0)` provider path only.",
        "It does not force RC1 enumerate, write pci-msm debugfs case values, spoof",
        "ONLINE/system-info, write PMIC/GPIO/GDSC/regulator state, issue eSoC",
        "notify/`BOOT_DONE`, rescan PCI, bind/unbind platforms, start Wi-Fi HAL,",
        "scan/connect, use credentials, run DHCP/routes, or external ping.",
        "",
        "## Next",
        "",
        "- Run V1662 host-only diff against V1660 Android-good reference.",
        "- Do not enter any write gate from this runner.",
        "",
    ]
    return "\n".join(lines)


def build_base_argv(args: argparse.Namespace) -> list[str]:
    return [
        "--cycle",
        "V1661",
        "--out-dir",
        str(args.out_dir),
        "--report-path",
        str(args.report_path),
        "--v1394-manifest",
        str(args.v1661_manifest),
        "--test-image",
        str(args.test_image),
        "--expect-test-version",
        TEST_EXPECT_VERSION,
        "--test-log-path",
        DEFAULT_TEST_LOG_PATH,
        "--test-summary-path",
        DEFAULT_TEST_SUMMARY_PATH,
        "--test-helper-result-path",
        DEFAULT_TEST_HELPER_RESULT_PATH,
        "--test-rc1-watcher-result-path",
        DEFAULT_TEST_WATCHER_PATH,
        "--test-rc1-window-result-path",
        DEFAULT_TEST_WINDOW_PATH,
        "--dmesg-grep-pattern",
        DEFAULT_DMESG_PATTERN,
        "--post-boot-hold-sec",
        str(args.post_boot_hold_sec),
        "--collect-timeout-sec",
        str(args.collect_timeout_sec),
        "--native-direct-rollback-fallback",
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--v1661-manifest", type=Path, default=DEFAULT_V1661_MANIFEST)
    parser.add_argument("--test-image", type=Path, default=DEFAULT_TEST_IMAGE)
    parser.add_argument("--post-boot-hold-sec", type=float, default=100.0)
    parser.add_argument("--collect-timeout-sec", type=float, default=180.0)
    parser.add_argument("--classify-only", action="store_true")
    parser.add_argument("--assume-yes", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    base_rc = 0
    if not args.classify_only:
        base_rc = base.main(build_base_argv(args))
    manifest_path = args.out_dir / "manifest.json"
    handoff = read_json(manifest_path)
    if not handoff:
        print(json.dumps({
            "decision": "v1661-native-power-diff-handoff-manifest-missing",
            "pass": False,
            "base_rc": base_rc,
        }, indent=2))
        return 1

    observation = v1632.classify_natural_path(args.out_dir, handoff)
    power = parse_power_diff(args.out_dir)
    power_ok = power_capture_ok(power)
    pass_ok = bool(observation["pass"] and power_ok)
    decision = (
        "v1661-native-natural-power-diff-capture-pass"
        if pass_ok
        else "v1661-native-natural-power-diff-capture-review"
    )
    reason = (
        "native natural path and read-only power/clock/subsystem snapshots captured; rollback verified"
        if pass_ok
        else "native natural path or power/clock/subsystem snapshot evidence incomplete; inspect before V1662"
    )
    result = dict(handoff)
    result.update({
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "natural_path_observation": observation,
        "power_diff_capture": power,
        "base_handoff_decision": handoff.get("base_handoff_decision", handoff.get("decision", "")),
        "base_handoff_pass": handoff.get("base_handoff_pass", handoff.get("pass", False)),
        "contract": {
            "source": "docs/reports/ESOC_ANDROID_NATIVE_POWER_DIFF_CONTRACT_2026-06-02.md",
            "native_side": True,
            "natural_path_only": True,
            "same_observables_as_v1660": True,
            "no_autonomous_write_gate": True,
        },
    })
    write_private_json(manifest_path, result)
    report = render_report(result)
    write_private_text(args.out_dir / "summary.md", report)
    write_private_text(args.report_path, report)
    print(json.dumps({
        "decision": result["decision"],
        "pass": result["pass"],
        "label": observation["label"],
        "power_ok": power_ok,
        "base_rc": base_rc,
        "rollback_ok": observation["rollback_ok"],
        "out_dir": rel(args.out_dir),
        "report": rel(args.report_path),
    }, indent=2))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

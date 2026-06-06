#!/usr/bin/env python3
"""V1659 plan for Android-good vs native power/clock/sequence diff."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from a90harness.evidence import EvidenceStore, write_private_text


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1659-android-native-power-diff-plan"
DEFAULT_REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1659_ANDROID_NATIVE_POWER_DIFF_PLAN_2026-06-02.md"
)
REPORTS = {
    "contract": REPO_ROOT / "docs/reports/ESOC_ANDROID_NATIVE_POWER_DIFF_CONTRACT_2026-06-02.md",
    "v1514": REPO_ROOT / "docs/reports/NATIVE_INIT_V1514_WIFI_SOURCE_TIMING_CLASSIFIER_2026-06-01.md",
    "v1555": REPO_ROOT / "docs/reports/NATIVE_INIT_V1555_ANDROID_GOOD_MINIMAL_TRACE_REFERENCE_2026-06-02.md",
    "v1657": REPO_ROOT / "docs/reports/NATIVE_INIT_V1657_NATURAL_PATH_MDM2AP_OBSERVATION_HANDOFF_2026-06-02.md",
    "v1641": REPO_ROOT / "docs/reports/NATIVE_INIT_V1641_RAIL_CONTROL_INVENTORY_2026-06-02.md",
    "v1656": REPO_ROOT / "docs/reports/NATIVE_INIT_V1656_XBL_REFERENCE_RECONCILIATION_2026-06-02.md",
    "pon": REPO_ROOT / "docs/reports/ESOC_PON_SOURCE_ANALYSIS_2026-06-02.md",
    "dtb": REPO_ROOT / "docs/reports/ESOC_DTB_PARITY_2026-06-02.md",
}


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


def classify() -> dict[str, Any]:
    texts = {key: read_text(path) for key, path in REPORTS.items()}
    checks = {
        "contract_present": "Android-good vs native power/clock/sequence diff" in texts["contract"],
        "contract_labels_fixed": all(
            label in texts["contract"]
            for label in ("power-vote-gap", "sequence-gap", "full-power-parity-hardware-wall")
        ),
        "contract_both_sides": "SAME observables on BOTH sides" in texts["contract"],
        "v1657_clean_silent": "v1657-mdm2ap-silent-natural-path" in texts["v1657"],
        "v1555_android_good": "v1555-android-good-minimal-trace-reference-pass" in texts["v1555"],
        "v1641_no_write_target": "v1641-no-safe-live-write-target-host-inventory-pass" in texts["v1641"],
        "v1656_xbl_dead_end": "not a direct native-vs-Android differential or write target" in texts["v1656"],
        "pon_provider_no_regulator": "Provider has ZERO power/regulator code" in texts["pon"],
        "dtb_parity": "DTB parity = PASS" in texts["dtb"],
        "v1514_clk_summary_caution_or_contract": (
            "V1514 proved it overruns timing" in texts["contract"]
            and "clk_summary read crosses the RC1 link-fail marker" in texts["v1514"]
        ),
    }
    observables = [
        {
            "name": "regulator_summary_full",
            "android": "read full `/sys/kernel/debug/regulator/regulator_summary` snapshots",
            "native": "read the same summary snapshots in the natural-provider window",
            "diff": "rails enabled/used in Android but off/zero/absent in native",
        },
        {
            "name": "targeted_named_clocks",
            "android": "read only pcie1/refclk/modem-related named clock lines",
            "native": "read only the same targeted clock lines",
            "diff": "clock prepared/enabled in Android but not native",
        },
        {
            "name": "subsystem_sequence",
            "android": "sample subsys0(mss), subsys9(esoc0), service/process timing around esoc0",
            "native": "sample the same subsystem state/order in the V1657 natural PM-first route",
            "diff": "Android-only pre-esoc0 subsystem bring-up or glink/SMP2P step",
        },
        {
            "name": "gpio_irq",
            "android": "GPIO135/142, msm_pcie_wake, mdm status, errfatal IRQ deltas",
            "native": "same GPIO/IRQ deltas with no forced RC1 and no spoof",
            "diff": "positive Android response vs native silence",
        },
    ]
    labels = [
        {
            "label": "power-vote-gap",
            "meaning": "Android enables a rail/clock that native does not.",
            "action": "STOP and hand back for separately authorized targeted write gate; do not write here.",
        },
        {
            "label": "sequence-gap",
            "meaning": "Power/clock parity, but Android brings up a subsystem/route before esoc0 that native omits.",
            "action": "STOP and design route fix; no PMIC/GPIO/GDSC write.",
        },
        {
            "label": "full-power-parity-hardware-wall",
            "meaning": "AP-side rails, clocks, and sequence match; remaining cause is below AP control.",
            "action": "Terminal PASS classification; STOP. Do not enter write gate autonomously.",
        },
    ]
    execution_plan = [
        {
            "cycle": "V1660",
            "side": "Android-good",
            "type": "source/build-only then rollbackable handoff",
            "implementation": "reuse V1521/V1555 Magisk post-fs-data engine; add full regulator snapshot and targeted clock snapshot reads",
        },
        {
            "cycle": "V1661",
            "side": "native",
            "type": "source/build-only then rollbackable natural-path handoff",
            "implementation": "reuse V1657 natural PM-first route; add the same regulator/clock/subsys/GPIO/IRQ read-only sampler",
        },
        {
            "cycle": "V1662",
            "side": "host",
            "type": "host-only diff classifier",
            "implementation": "diff V1660 vs V1661 and emit exactly one fixed label",
        },
    ]
    hard_stops = [
        "no regulator/PMIC/GPIO/GDSC writes",
        "no forced RC1/case writes",
        "no fake ONLINE/system-info spoof",
        "no eSoC notify/BOOT_DONE",
        "no PCI rescan",
        "no platform bind/unbind",
        "no Wi-Fi HAL/scan/connect",
        "no credentials",
        "no DHCP/routes",
        "no external ping",
        "one Android run plus one native run plus one diff only; no timing/window variants",
    ]
    pass_ok = all(checks.values())
    return {
        "cycle": "V1659",
        "type": "source/build-only Android-good vs native power/clock/sequence diff plan",
        "decision": "v1659-android-native-power-diff-plan-ready" if pass_ok else "v1659-android-native-power-diff-plan-review",
        "pass": pass_ok,
        "checks": checks,
        "observables": observables,
        "labels": labels,
        "execution_plan": execution_plan,
        "hard_stops": hard_stops,
        "reports": {key: rel(path) for key, path in REPORTS.items()},
    }


def render_report(result: dict[str, Any]) -> str:
    lines = [
        "# Native Init V1659 Android-good vs Native Power Diff Plan",
        "",
        "## Summary",
        "",
        "- Cycle: `V1659`",
        "- Type: source/build-only Android-good vs native power/clock/sequence diff plan",
        f"- Decision: `{result['decision']}`",
        f"- Result: {'PASS' if result['pass'] else 'REVIEW'}",
        "- Contract: `docs/reports/ESOC_ANDROID_NATIVE_POWER_DIFF_CONTRACT_2026-06-02.md`",
        "- Reason: V1657 fixed clean natural-path MDM2AP silence; a write gate still has no concrete target, so the next gate is the final AP-side read-only Android-vs-native diff.",
        "",
        "## Evidence Checks",
        "",
        "| check | value |",
        "|---|---:|",
    ]
    for key, value in result["checks"].items():
        lines.append(f"| `{key}` | `{value}` |")
    lines.extend([
        "",
        "## Observables",
        "",
        "| observable | Android-good | native | diff target |",
        "|---|---|---|---|",
    ])
    for item in result["observables"]:
        lines.append(f"| `{item['name']}` | {item['android']} | {item['native']} | {item['diff']} |")
    lines.extend([
        "",
        "## Fixed Labels",
        "",
        "| label | meaning | action |",
        "|---|---|---|",
    ])
    for item in result["labels"]:
        lines.append(f"| `{item['label']}` | {item['meaning']} | {item['action']} |")
    lines.extend([
        "",
        "## Execution Plan",
        "",
        "| cycle | side | type | implementation |",
        "|---|---|---|---|",
    ])
    for item in result["execution_plan"]:
        lines.append(f"| `{item['cycle']}` | {item['side']} | {item['type']} | {item['implementation']} |")
    lines.extend([
        "",
        "## Hard Stops",
        "",
    ])
    for item in result["hard_stops"]:
        lines.append(f"- {item}")
    lines.extend([
        "",
        "## Honest Scope Limit",
        "",
        "The SDX50M's own modem-side rail is not represented in the AP regulator tree. If that is the true blocker, this gate should produce `full-power-parity-hardware-wall`, not a write target. That is still a useful terminal classification for the native route.",
        "",
        "## Safety Scope",
        "",
        "V1659 is source/build-only planning. It performs no device command, flash, reboot, partition write, Wi-Fi HAL start, scan/connect, credential handling, DHCP/routes, external ping, PMIC/GPIO/GDSC write, eSoC notify/`BOOT_DONE` spoof, pci-msm debugfs write, global PCI rescan, platform bind/unbind, Android handoff, or native test boot.",
        "",
    ])
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT_PATH)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    store = EvidenceStore(args.out_dir)
    result = classify()
    store.write_json("manifest.json", result)
    report = render_report(result)
    store.write_text("summary.md", report)
    write_private_text(args.report_path, report)
    print(json.dumps({
        "decision": result["decision"],
        "pass": result["pass"],
        "out_dir": rel(args.out_dir),
        "report": rel(args.report_path),
    }, indent=2))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""V1658 host-only next-gate selector after natural-path MDM2AP silence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from a90harness.evidence import EvidenceStore, write_private_text


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1658-post-mdm2ap-silence-next-gate"
DEFAULT_REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1658_POST_MDM2AP_SILENCE_NEXT_GATE_2026-06-02.md"
)
REPORTS = {
    "v1555": REPO_ROOT / "docs/reports/NATIVE_INIT_V1555_ANDROID_GOOD_MINIMAL_TRACE_REFERENCE_2026-06-02.md",
    "v1641": REPO_ROOT / "docs/reports/NATIVE_INIT_V1641_RAIL_CONTROL_INVENTORY_2026-06-02.md",
    "v1642": REPO_ROOT / "docs/reports/NATIVE_INIT_V1642_SDX_POWER_OWNER_CLASSIFIER_2026-06-02.md",
    "v1656": REPO_ROOT / "docs/reports/NATIVE_INIT_V1656_XBL_REFERENCE_RECONCILIATION_2026-06-02.md",
    "v1657": REPO_ROOT / "docs/reports/NATIVE_INIT_V1657_NATURAL_PATH_MDM2AP_OBSERVATION_HANDOFF_2026-06-02.md",
    "contract": REPO_ROOT / "docs/reports/ESOC_NATURAL_PATH_MDM2AP_OBSERVATION_CONTRACT_2026-06-02.md",
    "dtb": REPO_ROOT / "docs/reports/ESOC_DTB_PARITY_2026-06-02.md",
    "pon": REPO_ROOT / "docs/reports/ESOC_PON_SOURCE_ANALYSIS_2026-06-02.md",
}
SOURCE_DIR = REPO_ROOT / "tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/esoc"
PUBLIC_SOURCES = [
    {
        "label": "Qualcomm MDM devicetree binding",
        "url": "https://android.googlesource.com/kernel/msm/+/ed2365b00f56c064b561b008659e2a5e5afd79a8/Documentation/devicetree/bindings/arm/msm/mdm-modem.txt",
        "used_for": "external modem GPIO model and optional AP2MDM PMIC power-enable property",
    },
    {
        "label": "Qualcomm eSoC MDM driver",
        "url": "https://android.googlesource.com/kernel/msm/+/android-wear-6.0.1_r0.114/drivers/esoc/esoc-mdm-4x.c",
        "used_for": "AP2MDM/MDM2AP GPIO map and status IRQ readiness model",
    },
]


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


def source_has_regulator_code() -> bool:
    if not SOURCE_DIR.exists():
        return False
    haystack = ""
    for path in SOURCE_DIR.glob("*.c"):
        haystack += read_text(path).lower()
    for path in SOURCE_DIR.glob("*.h"):
        haystack += read_text(path).lower()
    return any(token in haystack for token in ("regulator", "vreg", "supply"))


def classify() -> dict[str, Any]:
    texts = {key: read_text(path) for key, path in REPORTS.items()}
    checks = {
        "v1657_clean_natural_silent": "v1657-mdm2ap-silent-natural-path" in texts["v1657"],
        "v1657_gpio142_zero": "`gpio142_irq_delta`: `0`" in texts["v1657"],
        "v1657_errfatal_zero": "`errfatal_irq_delta`: `0`" in texts["v1657"],
        "v1657_rollback_ok": "Rollback ok: `True`" in texts["v1657"],
        "contract_stop_after_silent": "Once `mdm2ap-silent-natural-path` is\nrecorded, STOP" in texts["contract"],
        "v1641_no_safe_write_target": "v1641-no-safe-live-write-target-host-inventory-pass" in texts["v1641"],
        "v1642_owner_outside_ap_source": "v1642-sdx-main-rail-owner-outside-ap-source-pass" in texts["v1642"],
        "v1656_xbl_no_mutation_target": "not a direct native-vs-Android differential or write target" in texts["v1656"],
        "v1555_android_good_reference": "v1555-android-good-minimal-trace-reference-pass" in texts["v1555"],
        "pon_provider_no_regulator": "Provider has ZERO power/regulator code" in texts["pon"],
        "dtb_non_differential": "DTB parity = PASS" in texts["dtb"],
        "local_esoc_no_regulator_code": not source_has_regulator_code(),
    }
    gates = [
        {
            "gate": "repeat natural-path timing/window variant",
            "class": "reject",
            "reason": "V1657 already produced the fixed contract label; repeating this recreates the V1370-V1559 drift mode.",
            "next": "none",
        },
        {
            "gate": "forced RC1 enumerate / pci-msm case write",
            "class": "reject",
            "reason": "downstream and contaminating; it cannot prove natural MDM2AP response.",
            "next": "none",
        },
        {
            "gate": "fake ONLINE / system-info spoof",
            "class": "reject",
            "reason": "inverts causality below the provider; does not power SDX50M.",
            "next": "none",
        },
        {
            "gate": "direct PMIC/GPIO/GDSC write",
            "class": "reject-for-now",
            "reason": "no named owner, voltage/sequence constraints, or rollbackable AP-native write surface exists.",
            "next": "requires separate bounded hypothesis after a concrete target is identified",
        },
        {
            "gate": "Android-good rail/reference capture",
            "class": "selected-next",
            "reason": "non-mutating reference capture can identify which regulator/PMIC/clock/IRQ surfaces differ when Android-good reaches GPIO142, WLFW, and wlan0.",
            "next": "V1659 plan/source-build for a minimal Android-good rail snapshot handoff",
        },
        {
            "gate": "additional bootloader/XBL context expansion",
            "class": "secondary",
            "reason": "useful only if Android-good rail reference still cannot name a target; current XBL context is informative but not causal.",
            "next": "bounded private artifact context only, not a live write",
        },
    ]
    selected = next(gate for gate in gates if gate["class"] == "selected-next")
    pass_ok = all(checks.values())
    decision = "v1658-select-android-good-rail-reference-next" if pass_ok else "v1658-next-gate-selection-review"
    return {
        "cycle": "V1658",
        "type": "host-only post-MDM2AP-silence next-gate selector",
        "decision": decision,
        "pass": pass_ok,
        "checks": checks,
        "gates": gates,
        "selected_gate": selected,
        "reports": {key: rel(path) for key, path in REPORTS.items()},
        "public_sources": PUBLIC_SOURCES,
        "next_cycle": {
            "cycle": "V1659",
            "type": "source/build-only Android-good SDX50M rail/reference capture plan",
            "success_criteria": [
                "preserve Android-good lower path through BDF/FW-ready/wlan0",
                "capture read-only regulator/PMIC/GPIO/IRQ summaries before and after esoc0/provider trigger",
                "rollback to stage3/boot_linux_v724.img and verify native selftest fail=0",
                "avoid PMIC/GPIO/GDSC writes, PCI rescan, platform bind/unbind, Wi-Fi credentials, DHCP/routes, and external ping",
            ],
        },
    }


def render_report(result: dict[str, Any]) -> str:
    lines = [
        "# Native Init V1658 Post-MDM2AP Silence Next-Gate Selector",
        "",
        "## Summary",
        "",
        "- Cycle: `V1658`",
        "- Type: host-only post-MDM2AP-silence next-gate selector",
        f"- Decision: `{result['decision']}`",
        f"- Result: {'PASS' if result['pass'] else 'REVIEW'}",
        "- Selected next gate: `Android-good rail/reference capture`",
        "- Reason: V1657 fixed the lower blocker at clean natural-path MDM2AP silence, but prior rail/owner classifiers still do not identify a safe AP-native write target.",
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
        "## Gate Matrix",
        "",
        "| gate | class | reason | next |",
        "|---|---|---|---|",
    ])
    for gate in result["gates"]:
        lines.append(f"| {gate['gate']} | `{gate['class']}` | {gate['reason']} | {gate['next']} |")
    lines.extend([
        "",
        "## Interpretation",
        "",
        "V1657 removes the forced-RC1 caveat: the natural provider/PON/AP2MDM path ran and MDM2AP/GPIO142 plus errfatal IRQ deltas stayed zero. The next step toward actual Wi-Fi connectivity is not credentials, HAL, firmware transfer, or another timing retry. It is to name the missing lower power prerequisite.",
        "",
        "A direct PMIC/GPIO/GDSC write remains unjustified because V1641/V1642/V1656 still lack a concrete AP-native target with owner, voltage/sequence constraints, and rollbackable control surface. The shortest useful non-mutating step is an Android-good reference capture that preserves the known-good lower path while recording read-only regulator/PMIC/GPIO/IRQ summaries around esoc0/provider trigger and `wlan0` creation.",
        "",
        "## V1659 Contract Sketch",
        "",
        "- Type: source/build-only plan first, then separate rollbackable Android-good handoff.",
        "- Capture: filtered dmesg, GPIO135/142/141/104/102 IRQ and level summaries, `/sys/class/regulator` names/states/voltages, pcie1 GDSC/refclk/pipe summaries, and module status.",
        "- Timing: pre-esoc0 baseline, esoc0/AP2MDM window, first GPIO142/MDM status response, BDF/FW-ready/`wlan0`, and final post-good snapshot.",
        "- Rollback: restore `stage3/boot_linux_v724.img`; verify `A90 Linux init 0.9.68 (v724)` and selftest `fail=0`.",
        "- Hard stops: no PMIC/GPIO/GDSC writes, no PCI rescan, no platform bind/unbind, no eSoC notify/`BOOT_DONE`, no native Wi-Fi HAL/scan/connect, no credentials, no DHCP/routes, and no external ping in this reference gate.",
        "",
        "## Public Source Notes",
        "",
        "Public Qualcomm kernel sources match the local source model: external MDM devices are GPIO-controlled, `ap2mdm-pmic-pwr-en-gpio` is optional, and MDM readiness is represented by MDM2AP status/interrupt handling. A90's local DTS/source evidence still lacks an AP-side PMIC power-enable or mdm3 regulator property, so these sources support observation and target discovery, not blind mutation.",
        "",
        "| source | used for |",
        "|---|---|",
    ])
    for source in result["public_sources"]:
        lines.append(f"| {source['url']} | {source['used_for']} |")
    lines.extend([
        "",
        "## Safety Scope",
        "",
        "V1658 is host-only. It performs no device command, flash, reboot, partition write, Wi-Fi HAL start, scan/connect, credential handling, DHCP/routes, external ping, PMIC/GPIO/GDSC write, eSoC notify/`BOOT_DONE` spoof, pci-msm debugfs write, global PCI rescan, or platform bind/unbind.",
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
        "selected_gate": result["selected_gate"]["gate"],
        "out_dir": rel(args.out_dir),
        "report": rel(args.report_path),
    }, indent=2))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

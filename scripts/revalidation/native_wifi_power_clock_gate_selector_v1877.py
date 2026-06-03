#!/usr/bin/env python3
"""V1877 host-only pcie1 power/clock gate selector."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from a90harness.evidence import EvidenceStore, write_private_text


REPO_ROOT = Path(__file__).resolve().parents[2]
REPORTS = REPO_ROOT / "docs" / "reports"
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1877-power-clock-gate-selector"
DEFAULT_REPORT_PATH = (
    REPORTS / "NATIVE_INIT_V1877_POWER_CLOCK_GATE_SELECTOR_2026-06-03.md"
)
DEFAULT_V1876_REPORT = (
    REPORTS / "NATIVE_INIT_V1876_LOWER_RESPONSE_READONLY_SAMPLER_HANDOFF_2026-06-03.md"
)
DEFAULT_V1673_REPORT = (
    REPORTS / "NATIVE_INIT_V1673_PCIE1_CLOCK_VOTE_DIRECT_RETRY_HANDOFF_2026-06-02.md"
)
DEFAULT_V1663_REPORT = REPORTS / "NATIVE_INIT_V1663_PCIE1_VOTE_GATE_PLAN_2026-06-02.md"
DEFAULT_V1662_REPORT = (
    REPORTS / "NATIVE_INIT_V1662_ANDROID_NATIVE_POWER_DIFF_CLASSIFIER_2026-06-02.md"
)
DEFAULT_V1549_REPORT = (
    REPORTS / "NATIVE_INIT_V1549_LOW_OVERHEAD_RESULT_CLASSIFIER_2026-06-02.md"
)
DEFAULT_V1354_REPORT = (
    REPORTS / "NATIVE_INIT_V1354_PCIE1_RC_POWER_OBSERVER_LIVE_2026-06-01.md"
)
DEFAULT_V1252_REPORT = (
    REPORTS / "NATIVE_INIT_V1252_PMIC_POWER_WRITE_GATE_PLAN_2026-05-31.md"
)


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def read_text_artifact(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False, "path": rel(path), "text": ""}
    return {
        "exists": True,
        "path": rel(path),
        "text": path.read_text(encoding="utf-8", errors="replace"),
    }


def contains_all(artifact: dict[str, Any], markers: list[str]) -> bool:
    text = str(artifact.get("text") or "")
    return bool(artifact.get("exists")) and all(marker in text for marker in markers)


def first_matching_line(artifact: dict[str, Any], needle: str) -> str:
    for line in str(artifact.get("text") or "").splitlines():
        if needle in line:
            stripped = line.strip()
            if stripped.startswith("- "):
                return stripped[2:].strip()
            return stripped
    return ""


def summarize(artifact: dict[str, Any], needles: list[str]) -> dict[str, Any]:
    return {
        "exists": bool(artifact.get("exists")),
        "path": artifact.get("path", ""),
        "lines": {needle: first_matching_line(artifact, needle) for needle in needles},
    }


def build_result(args: argparse.Namespace) -> dict[str, Any]:
    artifacts = {
        "v1876": read_text_artifact(args.v1876_report),
        "v1673": read_text_artifact(args.v1673_report),
        "v1663": read_text_artifact(args.v1663_report),
        "v1662": read_text_artifact(args.v1662_report),
        "v1549": read_text_artifact(args.v1549_report),
        "v1354": read_text_artifact(args.v1354_report),
        "v1252": read_text_artifact(args.v1252_report),
    }

    checks = {
        "v1876_current_route_confirms_power_clock_gap": contains_all(
            artifacts["v1876"],
            [
                "v1876-lower-input-power-clock-snapshot-gap-rollback-pass",
                "contract label: `lower-input-power-clock-snapshot-gap`",
                "guard read-only/no-esoc0/no-rc/no-pci/no-hal: `True` / `True` / `True` / `True` / `True`",
                "max mdm-status/pci/mhi/ks: `0` / `0` / `0` / `0`",
                "mdm3/MHI/WLFW69/wlan0: `OFFLINING` / `False` / `False` / `False`",
                "Do not proceed to Wi-Fi HAL/scan/connect unless WLFW service 69 and `wlan0` are present",
            ],
        ),
        "v1662_establishes_android_native_power_vote_gap": contains_all(
            artifacts["v1662"],
            [
                "v1662-android-native-power-diff-power-vote-gap-pass",
                "Label: `power-vote-gap`",
                "Autonomous write gate: `False`",
                "| pcie_1_gdsc | 1 | 0 |",
                "| gcc_pcie1_phy_refgen_clk | 1 | 0 |",
                "no_autonomous_write_gate",
            ],
        ),
        "v1663_authorized_only_narrow_clock_debug_first": contains_all(
            artifacts["v1663"],
            [
                "v1663-pcie1-clock-vote-gate-plan-ready",
                "Allowed writes: targeted `/sys/kernel/debug/clk/<target>/rate` and `/sys/kernel/debug/clk/<target>/enable` only.",
                "No regulator/GDSC direct write in this gate",
                "No PMIC/GPIO/PERST write",
                "No `/sys/kernel/debug/pci-msm/case` write",
            ],
        ),
        "v1673_closes_clock_debug_surface": contains_all(
            artifacts["v1673"],
            [
                "v1673-clock-vote-surface-failed",
                "success_count=0, failure_count=10",
                "`success_count`: `0`",
                "`failure_count`: `10`",
                "`safety_zero`: `True`",
                "`forbidden_seen`: `False`",
                "This closes the debugfs clock-vote surface as a practical pcie1 power-vote",
                "Do not keep repeating timing/readiness variants.",
            ],
        ),
        "v1549_and_v1354_carry_forward_no_l0_gdsc_zero": contains_all(
            artifacts["v1549"],
            [
                "v1549-low-overhead-confirms-pre-fail-gpio-gdsc-no-l0",
                "pre-fail-pcie1-gdsc-zero-observed",
                "Guardrail: no PMIC/GPIO/GDSC direct write",
            ],
        )
        and contains_all(
            artifacts["v1354"],
            [
                "v1354-current-route-pcie1-rc-stayed-off",
                "timing_pcie1_gdsc_nonzero_seen | False",
                "timing_pci_dev_max | 0",
                "timing_mhi_bus_max | 0",
                "timing_wlan0_seen | False",
            ],
        ),
        "v1252_rejects_broad_power_writes_without_separate_gate": contains_all(
            artifacts["v1252"],
            [
                "V1252 is host-only",
                "helper `--allow-pmic-soft-reset-write` remains reserved fail-closed",
                "no debugfs regulator write",
                "no direct PCIe GDSC enable",
                "no blind `/dev/subsys_esoc0` retry",
                "no Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping",
            ],
        ),
        "host_only_no_live_mutation": True,
    }

    pass_ok = all(checks.values())
    decision = (
        "v1877-clock-debug-surface-closed-pcie-resource-gate-needed-host-pass"
        if pass_ok
        else "v1877-power-clock-gate-selector-review"
    )
    label = (
        "clock-debug-closed-resource-gdsc-or-driver-pm-next"
        if pass_ok
        else "review"
    )

    return {
        "cycle": "V1877",
        "type": "host-only pcie1 power/clock gate selector",
        "decision": decision,
        "label": label,
        "pass": pass_ok,
        "reason": (
            "V1876 confirms the current private SDX50M route still stops at a pcie1 "
            "power/clock snapshot gap, while V1663-V1673 already closed the bounded "
            "clock-debug vote path. The next safe unit must be source/build-only and "
            "select a legitimate pcie1 driver PM resource path, or stop for explicit "
            "approval before any narrowly targeted resource/GDSC write."
        ),
        "checks": checks,
        "inputs": {name: artifact["path"] for name, artifact in artifacts.items()},
        "summaries": {
            "v1876": summarize(
                artifacts["v1876"],
                [
                    "Decision:",
                    "contract label:",
                    "guard read-only/no-esoc0/no-rc/no-pci/no-hal",
                    "max mdm-status/pci/mhi/ks",
                    "mdm3/MHI/WLFW69/wlan0",
                    "pcie1-gdsc-line",
                ],
            ),
            "v1662": summarize(
                artifacts["v1662"],
                [
                    "Decision:",
                    "Label:",
                    "Autonomous write gate:",
                    "| pcie_1_gdsc |",
                    "| gcc_pcie1_phy_refgen_clk |",
                ],
            ),
            "v1663": summarize(
                artifacts["v1663"],
                [
                    "Decision:",
                    "Allowed writes:",
                    "No regulator/GDSC direct write",
                    "No `/sys/kernel/debug/pci-msm/case` write",
                ],
            ),
            "v1673": summarize(
                artifacts["v1673"],
                [
                    "Decision:",
                    "Reason:",
                    "`success_count`:",
                    "`failure_count`:",
                    "`safety_zero`:",
                    "`forbidden_seen`:",
                    "This closes the debugfs clock-vote surface",
                ],
            ),
            "v1549": summarize(
                artifacts["v1549"],
                [
                    "Decision:",
                    "pre-fail-pcie1-gdsc-zero-observed",
                    "Guardrail: no PMIC/GPIO/GDSC direct write",
                ],
            ),
            "v1354": summarize(
                artifacts["v1354"],
                [
                    "Decision",
                    "timing_pcie1_gdsc_nonzero_seen",
                    "timing_pci_dev_max",
                    "timing_mhi_bus_max",
                    "timing_wlan0_seen",
                ],
            ),
            "v1252": summarize(
                artifacts["v1252"],
                [
                    "helper `--allow-pmic-soft-reset-write` remains reserved fail-closed",
                    "no debugfs regulator write",
                    "no direct PCIe GDSC enable",
                    "no blind `/dev/subsys_esoc0` retry",
                ],
            ),
        },
        "selected_next_gate": {
            "cycle": "V1878",
            "label": "pcie1-driver-pm-resource-path-source-selector",
            "type": "source/build-only first; no live mutation",
            "preferred_path": (
                "find a legitimate pcie1 driver PM/resource path that can be invoked "
                "without global PCI rescan, platform bind/unbind, forced RC1, fake "
                "ONLINE state, direct `/dev/subsys_esoc0`, PMIC/GPIO writes, or direct "
                "GDSC/regulator writes"
            ),
            "fallback_path": (
                "if static source cannot identify a safe driver PM path, stop for "
                "explicit approval before building any narrowly targeted pcie1 "
                "resource/GDSC write gate"
            ),
            "required_fail_closed_checks": [
                "source selector must prove the candidate call path and all write surfaces before any boot image change",
                "artifact sanity must reject Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping strings",
                "live handoff remains forbidden until WLFW service 69 and `wlan0` prerequisites are present or a separate lower-resource gate is approved",
                "direct PMIC/GPIO/GDSC writes remain forbidden unless explicitly approved for a narrow, named gate",
            ],
        },
    }


def render_report(result: dict[str, Any]) -> str:
    checks = result["checks"]
    summaries = result["summaries"]
    next_gate = result["selected_next_gate"]
    return "\n".join([
        "# Native Init V1877 Power Clock Gate Selector",
        "",
        "## Summary",
        "",
        "- Cycle: `V1877`",
        "- Type: host-only pcie1 power/clock gate selector",
        f"- Decision: `{result['decision']}`",
        f"- Label: `{result['label']}`",
        f"- Result: {'PASS' if result['pass'] else 'REVIEW'}",
        f"- Reason: {result['reason']}",
        "- Evidence: `tmp/wifi/v1877-power-clock-gate-selector`",
        "",
        "## Checks",
        "",
        "| check | value |",
        "|---|---:|",
        *(f"| `{key}` | `{value}` |" for key, value in checks.items()),
        "",
        "## Evidence Chain",
        "",
        f"- V1876 latest route: {summaries['v1876']['lines']['Decision:']}",
        f"- V1876 lower contract: {summaries['v1876']['lines']['contract label:']}",
        f"- V1876 safety guards: {summaries['v1876']['lines']['guard read-only/no-esoc0/no-rc/no-pci/no-hal']}",
        f"- V1876 lower counts: {summaries['v1876']['lines']['max mdm-status/pci/mhi/ks']}",
        f"- V1876 Wi-Fi prereqs: {summaries['v1876']['lines']['mdm3/MHI/WLFW69/wlan0']}",
        f"- V1662 power diff: {summaries['v1662']['lines']['Decision:']} / {summaries['v1662']['lines']['Label:']}",
        f"- V1662 pcie1 GDSC gap: {summaries['v1662']['lines']['| pcie_1_gdsc |']}",
        f"- V1662 refgen gap: {summaries['v1662']['lines']['| gcc_pcie1_phy_refgen_clk |']}",
        f"- V1663 first gate: {summaries['v1663']['lines']['Decision:']}",
        f"- V1663 allowed surface: {summaries['v1663']['lines']['Allowed writes:']}",
        f"- V1673 clock-debug result: {summaries['v1673']['lines']['Decision:']} / {summaries['v1673']['lines']['Reason:']}",
        f"- V1673 counts: {summaries['v1673']['lines']['`success_count`:']} / {summaries['v1673']['lines']['`failure_count`:']}",
        f"- V1673 safety: {summaries['v1673']['lines']['`safety_zero`:']} / {summaries['v1673']['lines']['`forbidden_seen`:']}",
        f"- V1549 historical no-L0: {summaries['v1549']['lines']['Decision:']}",
        f"- V1354 private-route power observer: {summaries['v1354']['lines']['Decision']}",
        f"- V1252 write-gate boundary: {summaries['v1252']['lines']['no direct PCIe GDSC enable']}",
        "",
        "## Interpretation",
        "",
        "V1876 updates the current-route evidence after the private SDX50M mount: PM-service registration and return-path still work, but the lower publication remains absent. The read-only sampler observed the pcie1 GDSC line while mdm-status, PCI, MHI, `ks`, WLFW service 69, and `wlan0` all stayed at zero/absent. That keeps Wi-Fi HAL, scan/connect, DHCP/routes, and ping below the safe gate.",
        "",
        "V1662 identified the Android-good versus native pcie1 resource gap, but it explicitly did not authorize a write gate. V1663 then limited the first authorized live proof to targeted clock-debug leaf writes only. V1673 ran that bounded proof, all enable writes failed, safety stayed clean, and the report closed clock-debug as a practical pcie1 power-vote mechanism. Repeating clock-debug timing, readiness, or direct-write variants would not add a new source.",
        "",
        "The remaining actionable gap is therefore not a connectivity problem yet. It is a pcie1 lower-resource path problem before MHI/WLFW publication. The next unit must select and build from source first, then either use a legitimate pcie1 driver PM/resource path or stop for explicit approval before any narrowly targeted resource/GDSC write.",
        "",
        "## Selected Next Gate",
        "",
        f"- Cycle: `{next_gate['cycle']}`",
        f"- Label: `{next_gate['label']}`",
        f"- Type: `{next_gate['type']}`",
        f"- Preferred path: {next_gate['preferred_path']}",
        f"- Fallback path: {next_gate['fallback_path']}",
        *(f"- Fail-closed check: {item}" for item in next_gate["required_fail_closed_checks"]),
        "- Do not attempt Wi-Fi connect or ping until WLFW service 69 and `wlan0` are both present.",
        "",
        "## Safety Scope",
        "",
        "V1877 is host-only. It does not contact the device, flash, reboot, start services, open `/dev/subsys_esoc0`, force RC1, fake ONLINE state, start Wi-Fi HAL, scan/connect, use credentials, configure DHCP/routes, perform external ping, write PMIC/GPIO/GDSC/regulator controls, perform eSoC notify/`BOOT_DONE`, run PCI rescan/platform bind-unbind, or write firmware/boot/device partitions.",
        "",
    ])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--v1876-report", type=Path, default=DEFAULT_V1876_REPORT)
    parser.add_argument("--v1673-report", type=Path, default=DEFAULT_V1673_REPORT)
    parser.add_argument("--v1663-report", type=Path, default=DEFAULT_V1663_REPORT)
    parser.add_argument("--v1662-report", type=Path, default=DEFAULT_V1662_REPORT)
    parser.add_argument("--v1549-report", type=Path, default=DEFAULT_V1549_REPORT)
    parser.add_argument("--v1354-report", type=Path, default=DEFAULT_V1354_REPORT)
    parser.add_argument("--v1252-report", type=Path, default=DEFAULT_V1252_REPORT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = build_result(args)
    store = EvidenceStore(args.out_dir)
    store.write_json("manifest.json", result)
    report = render_report(result)
    store.write_text("summary.md", report)
    write_private_text(args.report_path, report)
    print(json.dumps({
        "decision": result["decision"],
        "pass": result["pass"],
        "label": result["label"],
        "out_dir": rel(args.out_dir),
        "report": rel(args.report_path),
    }, indent=2))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

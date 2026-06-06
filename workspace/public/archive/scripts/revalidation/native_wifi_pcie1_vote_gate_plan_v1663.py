#!/usr/bin/env python3
"""V1663 host-only plan for the bounded pcie1 clock/power vote gate."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from a90harness.evidence import EvidenceStore, write_private_text


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1663-pcie1-vote-gate-plan"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1663_PCIE1_VOTE_GATE_PLAN_2026-06-02.md"
)
V1662_REPORT = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1662_ANDROID_NATIVE_POWER_DIFF_CLASSIFIER_2026-06-02.md"
)
POWER_DIFF_CONTRACT = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "ESOC_ANDROID_NATIVE_POWER_DIFF_CONTRACT_2026-06-02.md"
)
CLOCK_DEBUG = (
    REPO_ROOT
    / "tmp"
    / "wifi"
    / "v766-icnss-qcacld-patch-apply-build"
    / "source"
    / "drivers"
    / "clk"
    / "msm"
    / "clock-debug.c"
)
PCI_MSM = (
    REPO_ROOT
    / "tmp"
    / "wifi"
    / "v766-icnss-qcacld-patch-apply-build"
    / "source"
    / "drivers"
    / "pci"
    / "host"
    / "pci-msm.c"
)
SM8150_PCIE_DTSI = (
    REPO_ROOT
    / "kernel_build"
    / "SM-A908N_KOR_12_Opensource"
    / "Kernel"
    / "arch"
    / "arm64"
    / "boot"
    / "dts"
    / "qcom"
    / "sm8150-pcie.dtsi"
)
TARGET_CLOCKS = (
    "gcc_pcie_1_aux_clk_src",
    "gcc_pcie_1_aux_clk",
    "gcc_pcie_1_cfg_ahb_clk",
    "gcc_pcie_1_mstr_axi_clk",
    "gcc_pcie_1_slv_axi_clk",
    "gcc_pcie_1_clkref_clk",
    "gcc_pcie_1_slv_q2a_axi_clk",
    "gcc_pcie_phy_refgen_clk_src",
    "gcc_pcie1_phy_refgen_clk",
    "gcc_pcie_1_pipe_clk",
)


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


def contains(path: Path, *needles: str) -> bool:
    text = read_text(path)
    return all(needle in text for needle in needles)


def grep_lines(path: Path, patterns: tuple[str, ...], *, limit: int = 16) -> list[str]:
    text = read_text(path)
    rows: list[str] = []
    for number, line in enumerate(text.splitlines(), start=1):
        if any(pattern in line for pattern in patterns):
            rows.append(f"{rel(path)}:{number}: {line.strip()}")
            if len(rows) >= limit:
                break
    return rows


def extract_v1662_power_gaps() -> dict[str, list[str]]:
    text = read_text(V1662_REPORT)
    regulators: list[str] = []
    clocks: list[str] = []
    section = ""
    for line in text.splitlines():
        if line.startswith("### Regulator Gaps"):
            section = "regulator"
            continue
        if line.startswith("### Clock Gaps"):
            section = "clock"
            continue
        if line.startswith("## ") and not line.startswith("### "):
            section = ""
        if not line.startswith("| "):
            continue
        if line.startswith("| name ") or line.startswith("|---"):
            continue
        name = line.split("|", 3)[1].strip()
        if section == "regulator" and name:
            regulators.append(name)
        if section == "clock" and name:
            clocks.append(name)
    return {"regulators": regulators, "clocks": clocks}


def classify() -> dict[str, Any]:
    power_gaps = extract_v1662_power_gaps()
    checks = {
        "v1662_power_vote_gap": "`power-vote-gap`" in read_text(V1662_REPORT),
        "contract_requires_separate_write_gate": "SEPARATELY user-authorized bounded targeted write gate"
        in read_text(POWER_DIFF_CONTRACT),
        "clock_debug_enable_write_surface": contains(CLOCK_DEBUG, "clock_debug_enable_set", "clk_prepare_enable"),
        "clock_debug_rate_write_surface": contains(CLOCK_DEBUG, "clock_debug_rate_set", "clk_set_rate"),
        "pcie_dtsi_maps_gdsc": contains(SM8150_PCIE_DTSI, "qcom,pcie@1c08000", "gdsc-vdd-supply = <&pcie_1_gdsc>;"),
        "pcie_dtsi_lists_target_clocks": all(clock in read_text(SM8150_PCIE_DTSI) for clock in (
            "pcie_1_pipe_clk",
            "pcie_1_ref_clk_src",
            "pcie_1_aux_clk",
            "pcie_1_cfg_ahb_clk",
            "pcie_1_mstr_axi_clk",
            "pcie_1_slv_axi_clk",
            "pcie_1_slv_q2a_axi_clk",
            "pcie_phy_refgen_clk",
        )),
        "pci_msm_normal_path_is_broad": contains(PCI_MSM, "msm_pcie_enable", "msm_pcie_vreg_init", "msm_pcie_clk_init"),
        "pci_msm_debug_case_broad": contains(PCI_MSM, "MSM_PCIE_ENUMERATION", "MSM_PCIE_ENABLE_LINK"),
        "gdsc_direct_write_surface_unproven": True,
        "no_live_command": True,
    }
    pass_ok = all(checks.values())
    return {
        "cycle": "V1663",
        "type": "host-only bounded pcie1 vote gate plan",
        "decision": "v1663-pcie1-clock-vote-gate-plan-ready" if pass_ok else "v1663-pcie1-clock-vote-gate-plan-review",
        "pass": pass_ok,
        "checks": checks,
        "inputs": {
            "v1662_report": rel(V1662_REPORT),
            "power_diff_contract": rel(POWER_DIFF_CONTRACT),
            "clock_debug": rel(CLOCK_DEBUG),
            "pci_msm": rel(PCI_MSM),
            "sm8150_pcie_dtsi": rel(SM8150_PCIE_DTSI),
        },
        "v1662_power_gaps": power_gaps,
        "first_live_gate": {
            "cycle": "V1665",
            "name": "bounded clock-debug vote surface proof",
            "trigger": "test boot PID1 mounts debugfs and writes only targeted clock debugfs leaf files",
            "allowed_writes": [
                "/sys/kernel/debug/clk/<target>/rate for refgen/source clocks",
                "/sys/kernel/debug/clk/<target>/enable for targeted pcie1/refgen clocks",
            ],
            "explicitly_not_allowed": [
                "regulator/GDSC direct write",
                "pci-msm case write",
                "forced RC1 enumerate",
                "PERST/GPIO/PMIC write",
                "eSoC notify or BOOT_DONE",
                "Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping",
            ],
            "cleanup": "disable only clocks successfully enabled by the test boot before rollback",
            "decision_labels": [
                "clock-vote-surface-pass-no-gdsc",
                "clock-vote-surface-pass-gdsc-moved",
                "clock-vote-surface-failed",
            ],
        },
        "next": "Implement V1664 source/build-only test boot, then run one V1665 rollbackable live gate.",
    }


def render_markdown(result: dict[str, Any]) -> str:
    source_rows = [
        *grep_lines(CLOCK_DEBUG, ("clock_debug_enable_set", "clk_prepare_enable", "clock_debug_rate_set", "clk_set_rate"), limit=8),
        *grep_lines(SM8150_PCIE_DTSI, ("gdsc-vdd-supply", "clock-names", "pcie_1_pipe_clk", "pcie_phy_refgen_clk"), limit=10),
        *grep_lines(PCI_MSM, ("MSM_PCIE_ENUMERATION", "MSM_PCIE_ENABLE_LINK", "MSM_PCIE_KEEP_RESOURCES_ON", "msm_pcie_enable"), limit=10),
    ]
    lines = [
        "# Native Init V1663 pcie1 Vote Gate Plan",
        "",
        "## Summary",
        "",
        "- Cycle: `V1663`",
        "- Type: host-only plan for the separately authorized AP-side pcie1 power/clock vote gate",
        f"- Decision: `{result['decision']}`",
        f"- Result: {'PASS' if result['pass'] else 'REVIEW'}",
        "- Reason: V1662 fixed a `power-vote-gap`; the first live mutation should prove only the narrow clock-debug vote surface before any broader regulator/GDSC or PCI path write.",
        "- Device command: `False`",
        "",
        "## Inputs",
        "",
    ]
    for key, value in result["inputs"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend([
        "",
        "## Checks",
        "",
    ])
    for key, value in result["checks"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend([
        "",
        "## V1662 Gap Carried Forward",
        "",
        f"- Regulator gaps: `{', '.join(result['v1662_power_gaps']['regulators'])}`",
        f"- Clock gaps: `{', '.join(result['v1662_power_gaps']['clocks'])}`",
        "",
        "## Static Source Notes",
        "",
    ])
    lines.extend(f"- `{row}`" for row in source_rows)
    lines.extend([
        "",
        "## First Live Gate",
        "",
        "- Cycle: `V1665`",
        "- Name: `bounded clock-debug vote surface proof`",
        "- Trigger: test boot PID1 mounts debugfs, writes only targeted clock debugfs leaf files, samples the existing pcie1/GPIO/subsystem observables, then disables only clocks it enabled.",
        "- Allowed writes: targeted `/sys/kernel/debug/clk/<target>/rate` and `/sys/kernel/debug/clk/<target>/enable` only.",
        "- Initial target clocks: `" + "`, `".join(TARGET_CLOCKS) + "`.",
        "- Rates: set refgen/source clocks that Android shows at `100000000`; leave fixed-gate clocks at existing rates.",
        "- Hold: bounded short hold only; no timing/window variants after one result.",
        "- Cleanup: disable only clocks successfully enabled by the test boot, then rollback to `stage3/boot_linux_v724.img` and verify selftest.",
        "",
        "## Explicit Non-goals",
        "",
        "- No regulator/GDSC direct write in this gate; no safe per-GDSC write surface is proven yet.",
        "- No `/sys/kernel/debug/pci-msm/case` write; `MSM_PCIE_ENABLE_LINK`/`MSM_PCIE_ENUMERATION` are broader normal/debug paths and previously contaminate MDM2AP observation.",
        "- No PMIC/GPIO/PERST write, eSoC notify/`BOOT_DONE`, PCI rescan, platform bind/unbind, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping.",
        "",
        "## Result Labels",
        "",
        "- `clock-vote-surface-pass-no-gdsc`: clock writes succeed and clean up, but pcie1 GDSC/RC1/MDM2AP do not move.",
        "- `clock-vote-surface-pass-gdsc-moved`: clock writes succeed and pcie1 power/link observables change; next gate can consider a fuller pcie1 normal resource vote.",
        "- `clock-vote-surface-failed`: clock leaf write/readback or cleanup fails; stop and repair the harness.",
        "",
        "## Next",
        "",
        "Implement V1664 source/build-only test boot support and run one rollbackable V1665 live handoff under this gate.",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    result = classify()
    store = EvidenceStore(OUT_DIR)
    store.write_json("manifest.json", result)
    write_private_text(REPORT_PATH, render_markdown(result))
    print(json.dumps({
        "decision": result["decision"],
        "pass": result["pass"],
        "report": rel(REPORT_PATH),
        "manifest": rel(OUT_DIR / "manifest.json"),
    }, indent=2, sort_keys=True))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

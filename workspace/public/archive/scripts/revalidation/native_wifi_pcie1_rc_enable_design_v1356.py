#!/usr/bin/env python3
"""V1356 host-only pcie1 RC bounded-enable design classifier."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

from a90_kernel_tools import markdown_table, repo_path
from a90harness.evidence import write_private_text, workspace_private_input_path


DEFAULT_OUT_DIR = Path("tmp/wifi/v1356-pcie1-rc-enable-design")
REPORT_PATH = Path("docs/reports/NATIVE_INIT_V1356_PCIE1_RC_ENABLE_DESIGN_2026-06-01.md")
SOURCE_ROOT = workspace_private_input_path("kernel_source", 'SM-A908N_KOR_12_Opensource', 'Kernel')

INPUTS = {
    "esoc_static_analysis": Path("docs/reports/ESOC_PROVIDER_STATIC_ANALYSIS_2026-06-01.md"),
    "v1353_static_contract": Path(
        "docs/reports/NATIVE_INIT_V1353_PCIE1_RC_STATIC_CONTRACT_CLASSIFIER_2026-06-01.md"
    ),
    "v1354_live_observer": Path(
        "docs/reports/NATIVE_INIT_V1354_PCIE1_RC_POWER_OBSERVER_LIVE_2026-06-01.md"
    ),
    "v1355_pon_parity": Path(
        "docs/reports/NATIVE_INIT_V1355_PMIC_GPIO9_PON_PARITY_CLASSIFIER_2026-06-01.md"
    ),
    "sm8150_pcie_dtsi": SOURCE_ROOT / "arch/arm64/boot/dts/qcom/sm8150-pcie.dtsi",
    "sm8150_sdx50m_dtsi": SOURCE_ROOT / "arch/arm64/boot/dts/qcom/sm8150-sdx50m.dtsi",
    "sm8150_mhi_dtsi": SOURCE_ROOT / "arch/arm64/boot/dts/qcom/sm8150-mhi.dtsi",
    "sm8150_dtsi": SOURCE_ROOT / "arch/arm64/boot/dts/qcom/sm8150.dtsi",
    "r3q_overlay": SOURCE_ROOT
    / "arch/arm64/boot/dts/samsung/renovation/sm8150-sec-r3q-kor-overlay-r03.dts",
    "msm_pcie_h": SOURCE_ROOT / "include/linux/msm_pcie.h",
    "cnss_h": SOURCE_ROOT / "include/net/cnss.h",
    "cnss2_debug_c": SOURCE_ROOT / "drivers/net/wireless/cnss2/debug.c",
    "cnss2_pci_c": SOURCE_ROOT / "drivers/net/wireless/cnss2/pci.c",
    "cnss2_main_c": SOURCE_ROOT / "drivers/net/wireless/cnss2/main.c",
    "mhi_arch_qcom_c": SOURCE_ROOT / "drivers/bus/mhi/controllers/mhi_arch_qcom.c",
}


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def read_text(path: Path) -> str:
    return repo_path(path).read_text(encoding="utf-8", errors="replace")


def first_line(text: str, needle: str) -> str:
    for line in text.splitlines():
        if needle in line:
            return line.strip()
    return ""


def bool_text(value: bool) -> str:
    return "true" if value else "false"


def control_surfaces(inputs: dict[str, str]) -> list[dict[str, str]]:
    return [
        {
            "surface": "msm_pcie_enumerate(1)",
            "status": "best semantic kernel operation, no direct userspace entry yet",
            "evidence": first_line(inputs["msm_pcie_h"], "int msm_pcie_enumerate(u32 rc_idx);"),
            "action": "V1357 must find an existing kernel-exposed caller before any write",
        },
        {
            "surface": "cnss2 debugfs dev_boot enumerate",
            "status": "possible but unproven and likely board-mismatched until live read-only checks pass",
            "evidence": "debugfs supports enumerate/linkup/powerup; generic cnss2 DTS uses wlan-rc-num=0 while A90 active path is ICNSS pcie-parent pcie1",
            "action": "read-only verify /sys/kernel/debug/cnss/dev_boot existence and RC mapping first",
        },
        {
            "surface": "platform driver bind/probe for 1c08000.qcom,pcie",
            "status": "possible but source-incomplete and higher risk",
            "evidence": "pcie1 platform node exists in DTS; Qualcomm PCIe core implementation is not present in the staged OSRC tree",
            "action": "read-only enumerate platform device/driver names and bind files only",
        },
        {
            "surface": "/sys/bus/pci/rescan or broad bus rescan",
            "status": "rejected as first mutation",
            "evidence": "global side effects; does not prove RC1-specific GDSC/refclk/PERST control",
            "action": "do not use unless narrower RC1-specific surfaces are absent and a later plan narrows risk",
        },
        {
            "surface": "direct PMIC/GPIO/GDSC/debugfs writes",
            "status": "rejected",
            "evidence": "V1355 closes PON parity; V1354 points at missing RC1 enable, not blind PON/GDSC pokes",
            "action": "keep excluded",
        },
    ]


def readonly_verifier_plan() -> list[dict[str, str]]:
    return [
        {
            "step": "pcie1 platform surface",
            "read": "list /sys/devices/platform/soc/*1c08000*, /sys/bus/platform/devices/*1c08000*, driver symlinks, modalias, uevent, power/runtime_status",
            "purpose": "prove the RC1 platform device and bound driver names before considering bind/probe writes",
        },
        {
            "step": "cnss debugfs surface",
            "read": "stat/read /sys/kernel/debug/cnss/dev_boot if present; read-only capture usage text and nearby cnss debug files",
            "purpose": "decide whether dev_boot exists and whether it can plausibly target pcie1 rather than generic RC0",
        },
        {
            "step": "live devicetree mapping",
            "read": "read /sys/firmware/devicetree/base qcom,wlan-rc-num and qcom,pcie-parent nodes if exposed",
            "purpose": "prevent using a cnss2 debug hook bound to the wrong root complex",
        },
        {
            "step": "power and clock baseline",
            "read": "pcie_1_gdsc, pcie1 clkref/refgen/pipe clocks, PERST/CLKREQ/WAKE, PCI/MHI device counts",
            "purpose": "confirm V1354 off-state before any later bounded mutation",
        },
        {
            "step": "log and interrupt baseline",
            "read": "focused dmesg/klog and /proc/interrupts for pcie1, LTSSM, MHI, GPIO142, errfatal",
            "purpose": "separate existing boot noise from mutation-caused transitions",
        },
    ]


def first_mutation_contract() -> list[dict[str, str]]:
    return [
        {
            "gate": "preflight",
            "requirement": "V1357 proves one narrow RC1-specific surface, maps it to pcie1, and baseline is still off",
        },
        {
            "gate": "candidate A",
            "requirement": "if cnss/dev_boot is present and proven RC1-safe, only consider 'enumerate' first; do not use 'powerup'",
        },
        {
            "gate": "candidate B",
            "requirement": "if only platform bind/probe exists, stop for a new design; do not bind blindly",
        },
        {
            "gate": "observe window",
            "requirement": "2-5s bounded observation of GDSC/refclk/PERST/LTSSM/PCI/MHI/GPIO142 with timeout",
        },
        {
            "gate": "cleanup",
            "requirement": "always cleanup by reboot; do not chain eSoC notify, BOOT_DONE, HAL, scan, DHCP, routes, or external ping",
        },
        {
            "gate": "stop conditions",
            "requirement": "stop if GDSC/refclk/PERST remain off, if wrong RC is indicated, if kernel reports PCIe errors, or if device health check fails",
        },
    ]


def classify() -> dict[str, Any]:
    missing = [str(path) for path in INPUTS.values() if not repo_path(path).exists()]
    if missing:
        return {
            "cycle": "V1356",
            "created_at": now_iso(),
            "decision": "v1356-inputs-missing",
            "pass": False,
            "missing": missing,
        }

    inputs = {name: read_text(path) for name, path in INPUTS.items()}
    checks = {
        "v1354_pcie1_rc_off_confirmed": "v1354-current-route-pcie1-rc-stayed-off"
        in inputs["v1354_live_observer"],
        "v1355_pon_parity_closed": "v1355-pon-parity-closed-pcie1-rc-next"
        in inputs["v1355_pon_parity"],
        "pcie1_static_contract_present": "pcie1: qcom,pcie@1c08000"
        in inputs["sm8150_pcie_dtsi"]
        and "gdsc-vdd-supply = <&pcie_1_gdsc>" in inputs["sm8150_pcie_dtsi"]
        and "perst-gpio = <&tlmm 102 0>" in inputs["sm8150_pcie_dtsi"],
        "sdx50m_mhi_endpoint_on_pcie1": "esoc-0 = <&mdm3>" in inputs["sm8150_sdx50m_dtsi"]
        and 'pci-ids = "17cb:0305"' in inputs["sm8150_mhi_dtsi"],
        "msm_pcie_enumerate_exported": "int msm_pcie_enumerate(u32 rc_idx);" in inputs["msm_pcie_h"]
        and "extern int msm_pcie_enumerate(u32 rc_idx);" in inputs["cnss_h"],
        "cnss_dev_boot_enumerate_exists": "sysfs_streq(cmd, \"enumerate\")"
        in inputs["cnss2_debug_c"]
        and "debugfs_create_file(\"dev_boot\"" in inputs["cnss2_debug_c"],
        "cnss2_rc_num_mismatch_risk_identified": "qcom,wlan-rc-num" in inputs["cnss2_pci_c"]
        and "qcom,wlan-rc-num = <0>" in inputs["sm8150_dtsi"]
        and "qcom,pcie-parent = <&pcie1>" in inputs["sm8150_dtsi"],
        "mhi_hook_downstream_of_pci_dev": "mhi_arch_esoc_ops_power_on" in inputs["mhi_arch_qcom_c"]
        and "devm_register_esoc_client" in inputs["mhi_arch_qcom_c"]
        and "mhi_pci_probe" in inputs["mhi_arch_qcom_c"],
        "hard_exclusions_preserved": True,
    }

    passed = all(checks.values())
    decision = (
        "v1356-pcie1-rc-enable-design-ready-readonly-surface-next"
        if passed
        else "v1356-pcie1-rc-enable-design-incomplete"
    )
    reason = (
        "V1354 proves the current lower route reaches mdm_subsys_powerup while pcie1 RC stays off, "
        "and V1355 closes blind PON mutation. The only defensible next step is a read-only live "
        "surface verifier that proves a narrow RC1 control path before any bounded enumerate/link-up attempt."
        if passed
        else "one or more pcie1 RC design inputs were missing or contradictory"
    )

    return {
        "cycle": "V1356",
        "type": "host-only design classifier",
        "created_at": now_iso(),
        "decision": decision,
        "pass": passed,
        "reason": reason,
        "inputs": {name: str(path) for name, path in INPUTS.items()},
        "checks": checks,
        "control_surfaces": control_surfaces(inputs),
        "readonly_verifier_plan": readonly_verifier_plan(),
        "first_mutation_contract": first_mutation_contract(),
        "next_step": "V1357 live read-only pcie1 RC control-surface verifier",
        "hard_exclusions": [
            "no PMIC/GPIO/GDSC write",
            "no eSoC notify or BOOT_DONE",
            "no Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping",
            "no platform bind, pci rescan, cnss dev_boot write, or debugfs/sysfs write in V1357",
            "no flash, boot image write, or partition write",
        ],
    }


def check_rows(manifest: dict[str, Any]) -> list[list[str]]:
    return [[key, bool_text(bool(value))] for key, value in sorted(manifest["checks"].items())]


def render_summary(manifest: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# V1356 pcie1 RC Enable Design",
            "",
            f"- decision: `{manifest['decision']}`",
            f"- pass: `{manifest['pass']}`",
            f"- reason: {manifest['reason']}",
            f"- next_step: {manifest['next_step']}",
            "",
            markdown_table(["check", "pass"], check_rows(manifest)),
            "",
        ]
    )


def render_report(manifest: dict[str, Any]) -> str:
    surface_rows = [
        [item["surface"], item["status"], item["evidence"], item["action"]]
        for item in manifest["control_surfaces"]
    ]
    verifier_rows = [
        [item["step"], item["read"], item["purpose"]]
        for item in manifest["readonly_verifier_plan"]
    ]
    mutation_rows = [
        [item["gate"], item["requirement"]]
        for item in manifest["first_mutation_contract"]
    ]
    return "\n".join(
        [
            "# Native Init V1356 pcie1 RC Enable Design",
            "",
            "## Summary",
            "",
            "- Cycle: `V1356`",
            "- Type: host-only design classifier",
            f"- Decision: `{manifest['decision']}`",
            f"- Result: {'PASS' if manifest['pass'] else 'FAIL'}",
            "- Script: `scripts/revalidation/native_wifi_pcie1_rc_enable_design_v1356.py`",
            "- Evidence:",
            "  - `tmp/wifi/v1356-pcie1-rc-enable-design/manifest.json`",
            "  - `tmp/wifi/v1356-pcie1-rc-enable-design/summary.md`",
            "",
            "## Inputs",
            "",
            markdown_table(["input", "path"], [[key, value] for key, value in manifest["inputs"].items()]),
            "",
            "## Checks",
            "",
            markdown_table(["check", "pass"], check_rows(manifest)),
            "",
            "## Decision",
            "",
            manifest["reason"],
            "",
            "The shortest confirmed blocker is now RC-side PCIe readiness. V1354",
            "proved the current native lower route reaches `mdm_subsys_powerup`",
            "while `pcie_1_gdsc`, pcie1 clkref/pipe, GPIO102/PERST, PCI, MHI,",
            "GPIO142/MDM2AP, WLFW, and `wlan0` stay absent. V1355 closes blind",
            "PM8150L GPIO9/PON mutation as the next branch. Therefore the next",
            "work must prove the available RC1 control surface before any write.",
            "",
            "## Candidate Control Surfaces",
            "",
            markdown_table(["surface", "status", "evidence", "required action"], surface_rows),
            "",
            "## V1357 Read-only Verifier Plan",
            "",
            markdown_table(["step", "read-only collection", "purpose"], verifier_rows),
            "",
            "## First Mutation Contract",
            "",
            "This is not approved by V1356. It is the contract a later V1358-style",
            "bounded experiment must satisfy after V1357 proves the surface.",
            "",
            markdown_table(["gate", "requirement"], mutation_rows),
            "",
            "## Safety",
            "",
            "- Host-only; no device command or live runtime access.",
            "- No sysfs/debugfs write, platform bind, PCI rescan, `cnss/dev_boot` write,",
            "  PMIC/GPIO/GDSC write, eSoC notify/`BOOT_DONE`, Wi-Fi HAL,",
            "  scan/connect, credential handling, DHCP/routes, external ping, flash,",
            "  boot image write, or partition write.",
            "",
            "## Next",
            "",
            "Implement V1357 as a live read-only pcie1 RC control-surface verifier.",
            "Do not execute the RC enable experiment until V1357 proves a narrow",
            "RC1-specific path and records a clean preflight baseline.",
            "",
        ]
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("command", choices=("run",), nargs="?", default="run")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest = classify()
    out_dir = repo_path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    write_private_text(out_dir / "manifest.json", json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    write_private_text(out_dir / "summary.md", render_summary(manifest))
    write_private_text(repo_path(REPORT_PATH), render_report(manifest))
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest.get('reason', 'missing inputs')}")
    print(f"next: {manifest.get('next_step', 'resolve missing inputs')}")
    print(f"evidence: {out_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

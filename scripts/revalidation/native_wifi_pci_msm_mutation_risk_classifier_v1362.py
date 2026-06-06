#!/usr/bin/env python3
"""V1362 host-only pci-msm/pcie1 mutation risk classifier."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

from a90_kernel_tools import markdown_table, repo_path
from a90harness.evidence import workspace_private_input_path, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1362-pci-msm-mutation-risk-classifier")
REPORT_PATH = Path("docs/reports/NATIVE_INIT_V1362_PCI_MSM_MUTATION_RISK_CLASSIFIER_2026-06-01.md")
SOURCE_ROOT = workspace_private_input_path("kernel_source", "SM-A908N_KOR_12_Opensource", "Kernel")

INPUTS = {
    "v1359_report": Path("docs/reports/NATIVE_INIT_V1359_ICNSS_PCI_ENTRY_CLASSIFIER_2026-06-01.md"),
    "v1360_report": Path("docs/reports/NATIVE_INIT_V1360_MHI_PLATFORM_SURFACE_VERIFIER_LIVE_2026-06-01.md"),
    "v1361_report": Path("docs/reports/NATIVE_INIT_V1361_MHI_SURFACE_OWNERSHIP_CLASSIFIER_2026-06-01.md"),
    "v1360_manifest": Path("tmp/wifi/v1360-mhi-platform-surface-verifier-live/manifest.json"),
    "msm_pcie_h": SOURCE_ROOT / "include/linux/msm_pcie.h",
    "cnss_h": SOURCE_ROOT / "include/net/cnss.h",
    "cnss2_pci_c": SOURCE_ROOT / "drivers/net/wireless/cnss2/pci.c",
    "sm8150_pcie_dtsi": SOURCE_ROOT / "arch/arm64/boot/dts/qcom/sm8150-pcie.dtsi",
    "mhi_arch_qcom_c": SOURCE_ROOT / "drivers/bus/mhi/controllers/mhi_arch_qcom.c",
}

RISK_ROWS = [
    {
        "option": "platform unbind/bind pci-msm:1c08000",
        "rc1_specific": "partial",
        "risk": "high",
        "reason": "targets pcie1 device name but invokes proprietary pci-msm remove/probe lifecycle without source-level cleanup or timeout proof",
        "decision": "reject for live until a bounded rollback model exists",
    },
    {
        "option": "platform drivers_probe for pci-msm",
        "rc1_specific": "no",
        "risk": "high",
        "reason": "generic bus reprobe; not tied to msm_pcie_enumerate(1) and cannot prove only pcie1 will be affected",
        "decision": "reject",
    },
    {
        "option": "global PCI rescan",
        "rc1_specific": "no",
        "risk": "high",
        "reason": "global PCI mutation with no RC1 scoping and no proof it powers pcie1 GDSC/refclk/PERST first",
        "decision": "reject",
    },
    {
        "option": "MHI client bind/unbind",
        "rc1_specific": "no",
        "risk": "closed",
        "reason": "V1361 proved MHI client drivers require existing mhi_device instances and are downstream of PCI enumeration",
        "decision": "closed",
    },
    {
        "option": "kernel-side msm_pcie_enumerate(1) shim",
        "rc1_specific": "yes",
        "risk": "unknown",
        "reason": "matches the semantic operation but requires module/export/signing or kernel patch feasibility proof before live use",
        "decision": "next host-only feasibility track",
    },
]


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def read_text(path: Path) -> str:
    return repo_path(path).read_text(encoding="utf-8", errors="replace")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(repo_path(path).read_text(encoding="utf-8"))


def first_line(text: str, needle: str) -> str:
    for line in text.splitlines():
        if needle in line:
            return line.strip()
    return ""


def count(text: str, needle: str) -> int:
    return text.count(needle)


def checks(inputs: dict[str, str], v1360_manifest: dict[str, Any]) -> dict[str, bool]:
    analysis = v1360_manifest.get("analysis") or {}
    return {
        "v1359_closed_icnss_dev_boot": "v1359-no-safe-userspace-msm-pcie-enumerate-entry" in inputs["v1359_report"],
        "v1360_live_has_pcie1_bound_no_pci_device": "pcie1_bound_pci_msm | True" in inputs["v1360_report"]
        and analysis.get("pci_device_count") == 0,
        "v1361_closed_mhi_client_surfaces": "v1361-mhi-surfaces-downstream-no-safe-mutation" in inputs["v1361_report"],
        "msm_pcie_enumerate_declared_only": "int msm_pcie_enumerate(u32 rc_idx);" in inputs["msm_pcie_h"]
        and "msm_pcie_enumerate(u32 rc_idx)" in inputs["cnss_h"],
        "msm_pcie_enumerate_source_absent_from_osrc": "int msm_pcie_enumerate(u32 rc_idx)" not in inputs["cnss2_pci_c"]
        and "msm_pcie_enumerate" in inputs["cnss2_pci_c"],
        "cnss2_calls_enumerate_but_wrong_branch": "ret = msm_pcie_enumerate(rc_num);" in inputs["cnss2_pci_c"]
        and "qcom,wlan-rc-num = <0>" in inputs["v1359_report"],
        "pcie0_and_pcie1_share_pci_msm_driver": count(inputs["sm8150_pcie_dtsi"], 'compatible = "qcom,pci-msm";') >= 2
        and "pcie0: qcom,pcie@1c00000" in inputs["sm8150_pcie_dtsi"]
        and "pcie1: qcom,pcie@1c08000" in inputs["sm8150_pcie_dtsi"],
        "mhi_arch_needs_existing_pci_dev": "struct pci_dev *pci_dev = mhi_dev->pci_dev" in inputs["mhi_arch_qcom_c"]
        and "msm_pcie_pm_control(MSM_PCIE_RESUME" in inputs["mhi_arch_qcom_c"],
        "risk_table_has_no_live_mutation_selected": all(row["decision"] != "approve live" for row in RISK_ROWS),
    }


def classify() -> dict[str, Any]:
    missing = [str(path) for path in INPUTS.values() if not repo_path(path).exists()]
    if missing:
        return {
            "cycle": "V1362",
            "generated_at": now_iso(),
            "decision": "v1362-inputs-missing",
            "pass": False,
            "missing": missing,
        }

    inputs = {name: read_text(path) for name, path in INPUTS.items() if name != "v1360_manifest"}
    v1360_manifest = read_json(INPUTS["v1360_manifest"])
    result_checks = checks(inputs, v1360_manifest)
    passed = all(result_checks.values())
    decision = (
        "v1362-no-safe-userspace-pci-msm-mutation"
        if passed
        else "v1362-pci-msm-risk-incomplete"
    )
    reason = (
        "All remaining userspace mutations are either generic bus operations or proprietary "
        "pci-msm remove/probe lifecycles without source-level timeout/rollback proof. "
        "No RC1-specific, bounded, observable, rollback-safe userspace mutation is proven."
        if passed
        else "one or more pci-msm mutation-risk assumptions are not proven"
    )
    next_step = (
        "V1363 host-only kernel-side msm_pcie_enumerate(1) shim feasibility classifier"
        if passed
        else "repair missing evidence before selecting any pci-msm mutation"
    )
    return {
        "cycle": "V1362",
        "type": "host-only risk classifier",
        "generated_at": now_iso(),
        "decision": decision,
        "pass": passed,
        "reason": reason,
        "next_step": next_step,
        "inputs": {name: str(path) for name, path in INPUTS.items()},
        "checks": result_checks,
        "risk_table": RISK_ROWS,
        "source_facts": {
            "msm_pcie_enumerate_decl": first_line(inputs["msm_pcie_h"], "int msm_pcie_enumerate"),
            "cnss2_enumerate_call": first_line(inputs["cnss2_pci_c"], "ret = msm_pcie_enumerate(rc_num);"),
            "pcie0_compatible": first_line(inputs["sm8150_pcie_dtsi"], "pcie0: qcom,pcie@1c00000"),
            "pcie1_compatible": first_line(inputs["sm8150_pcie_dtsi"], "pcie1: qcom,pcie@1c08000"),
            "mhi_pcie_resume": first_line(inputs["mhi_arch_qcom_c"], "msm_pcie_pm_control(MSM_PCIE_RESUME"),
        },
        "hard_exclusions": [
            "host-only; no device command",
            "no platform bind/unbind",
            "no PCI rescan",
            "no MHI bind/unbind",
            "no PMIC/GPIO/GDSC write",
            "no eSoC notify or BOOT_DONE",
            "no Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping",
            "no flash, boot image write, or partition write",
        ],
    }


def bool_text(value: bool) -> str:
    return "true" if value else "false"


def check_rows(manifest: dict[str, Any]) -> list[list[str]]:
    return [[key, bool_text(bool(value))] for key, value in sorted((manifest.get("checks") or {}).items())]


def risk_rows(manifest: dict[str, Any]) -> list[list[str]]:
    return [[row["option"], row["rc1_specific"], row["risk"], row["decision"], row["reason"]] for row in manifest.get("risk_table", [])]


def fact_rows(manifest: dict[str, Any]) -> list[list[Any]]:
    return [[key, value] for key, value in (manifest.get("source_facts") or {}).items()]


def render_summary(manifest: dict[str, Any]) -> str:
    return "\n".join([
        "# V1362 pci-msm Mutation Risk Classifier",
        "",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        "",
        markdown_table(["option", "rc1_specific", "risk", "decision", "reason"], risk_rows(manifest)) if manifest.get("risk_table") else "",
        "",
    ])


def render_report(manifest: dict[str, Any]) -> str:
    return "\n".join([
        "# Native Init V1362 pci-msm Mutation Risk Classifier",
        "",
        "## Summary",
        "",
        "- Cycle: `V1362`",
        "- Type: host-only risk classifier",
        f"- Decision: `{manifest['decision']}`",
        f"- Result: {'PASS' if manifest['pass'] else 'FAIL'}",
        "- Script: `scripts/revalidation/native_wifi_pci_msm_mutation_risk_classifier_v1362.py`",
        "- Evidence:",
        "  - `tmp/wifi/v1362-pci-msm-mutation-risk-classifier/manifest.json`",
        "  - `tmp/wifi/v1362-pci-msm-mutation-risk-classifier/summary.md`",
        "",
        "## Decision",
        "",
        manifest["reason"],
        "",
        "## Risk Table",
        "",
        markdown_table(["option", "rc1_specific", "risk", "decision", "reason"], risk_rows(manifest)) if manifest.get("risk_table") else "inputs missing",
        "",
        "## Checks",
        "",
        markdown_table(["check", "pass"], check_rows(manifest)) if manifest.get("checks") else "inputs missing",
        "",
        "## Source Facts",
        "",
        markdown_table(["fact", "value"], fact_rows(manifest)) if manifest.get("source_facts") else "inputs missing",
        "",
        "## Safety",
        "",
        "- Host-only; no device command or live runtime access.",
        "- No platform bind/unbind, PCI rescan, MHI bind/unbind, PMIC/GPIO/GDSC write,",
        "  eSoC notify/`BOOT_DONE`, Wi-Fi HAL, scan/connect, credential handling,",
        "  DHCP/routes, external ping, flash, boot image write, or partition write.",
        "",
        "## Next",
        "",
        manifest["next_step"],
        "",
    ])


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
    print(json.dumps({"decision": manifest["decision"], "pass": manifest["pass"], "out_dir": str(out_dir)}, indent=2))
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

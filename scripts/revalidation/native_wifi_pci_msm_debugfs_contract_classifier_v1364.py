#!/usr/bin/env python3
"""V1364 host-only pci-msm debugfs RC1 contract classifier."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

from a90_kernel_tools import markdown_table, repo_path
from a90harness.evidence import write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1364-pci-msm-debugfs-contract-classifier")
REPORT_PATH = Path("docs/reports/NATIVE_INIT_V1364_PCI_MSM_DEBUGFS_CONTRACT_CLASSIFIER_2026-06-01.md")
SOURCE_ROOT = Path("kernel_build/SM-A908N_KOR_12_Opensource/Kernel")

INPUTS = {
    "v1363_manifest": Path("tmp/wifi/v1363-pci-msm-debugfs-surface-verifier-live/manifest.json"),
    "v1363_report": Path("docs/reports/NATIVE_INIT_V1363_PCI_MSM_DEBUGFS_SURFACE_VERIFIER_LIVE_2026-06-01.md"),
    "v1363_heads": Path("tmp/wifi/v1363-pci-msm-debugfs-surface-verifier-live/native/pci-msm-file-heads.txt"),
    "v851_kallsyms": Path("tmp/wifi/v851-ext-mdm-provider-surface-snapshot/native/kallsyms-focus.txt"),
    "v1362_report": Path("docs/reports/NATIVE_INIT_V1362_PCI_MSM_MUTATION_RISK_CLASSIFIER_2026-06-01.md"),
    "sm8150_pcie_dtsi": SOURCE_ROOT / "arch/arm64/boot/dts/qcom/sm8150-pcie.dtsi",
}


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


def bool_text(value: bool) -> str:
    return "true" if value else "false"


def checks(inputs: dict[str, str], v1363_manifest: dict[str, Any]) -> dict[str, bool]:
    analysis = v1363_manifest.get("analysis") or {}
    kallsyms = inputs["v851_kallsyms"]
    heads = inputs["v1363_heads"]
    return {
        "v1363_found_debugfs_candidate": "v1363-pci-msm-debugfs-rc-control-candidate" in inputs["v1363_report"]
        and bool(analysis.get("pci_msm_present")),
        "case_lists_enumerate_11": "11:\t ENUMERATE" in heads or "11:	 ENUMERATE" in heads,
        "case_lists_status_26": "26:\t OUTPUT PERST AND WAKE GPIO STATUS" in heads
        or "26:	 OUTPUT PERST AND WAKE GPIO STATUS" in heads,
        "case_lists_perst_mutations": "27:\t ASSERT PERST" in heads
        or "27:	 ASSERT PERST" in heads,
        "rc_sel_file_exists": "/sys/kernel/debug/pci-msm/rc_sel" in inputs["v1363_report"]
        or "/sys/kernel/debug/pci-msm/rc_sel" in heads,
        "kallsyms_has_debugfs_selectors": "msm_pcie_debugfs_rc_select" in kallsyms
        and "msm_pcie_debugfs_case_select" in kallsyms
        and "msm_pcie_sel_debug_testcase" in kallsyms,
        "kallsyms_has_enumerate_path": "msm_pcie_enumerate" in kallsyms
        and "msm_pcie_enumerate_store" in kallsyms,
        "pcie1_is_rc1_by_dts_order": "pcie0: qcom,pcie@1c00000" in inputs["sm8150_pcie_dtsi"]
        and "pcie1: qcom,pcie@1c08000" in inputs["sm8150_pcie_dtsi"],
        "previous_userspace_paths_closed": "v1362-no-safe-userspace-pci-msm-mutation" in inputs["v1362_report"],
    }


def classify() -> dict[str, Any]:
    missing = [str(path) for path in INPUTS.values() if not repo_path(path).exists()]
    if missing:
        return {
            "cycle": "V1364",
            "generated_at": now_iso(),
            "decision": "v1364-inputs-missing",
            "pass": False,
            "missing": missing,
        }

    inputs = {name: read_text(path) for name, path in INPUTS.items() if name != "v1363_manifest"}
    v1363_manifest = read_json(INPUTS["v1363_manifest"])
    result_checks = checks(inputs, v1363_manifest)
    passed = all(result_checks.values())
    decision = (
        "v1364-pci-msm-debugfs-contract-candidate-not-approved"
        if passed
        else "v1364-pci-msm-debugfs-contract-incomplete"
    )
    reason = (
        "V1363 exposes a pci-msm debugfs selector surface and kallsyms contains matching "
        "selector/enumerate functions. The likely contract is rc_sel=<RC> then case=<testcase>; "
        "case 11 is ENUMERATE and case 26 is status-only PERST/WAKE output. Because proprietary "
        "source/disassembly has not yet proven the exact call path, enumerate is not approved. "
        "The only defensible first write candidate is a bounded status-only case 26 probe."
        if passed
        else "one or more pci-msm debugfs contract assumptions are not proven"
    )
    next_step = (
        "V1365 bounded live pci-msm debugfs status-only proof: rc_sel=1 then case=26; no enumerate"
        if passed
        else "repair missing evidence before any pci-msm debugfs write"
    )
    return {
        "cycle": "V1364",
        "type": "host-only classifier",
        "generated_at": now_iso(),
        "decision": decision,
        "pass": passed,
        "reason": reason,
        "next_step": next_step,
        "inputs": {name: str(path) for name, path in INPUTS.items()},
        "checks": result_checks,
        "candidate_contracts": [
            {
                "name": "status-only pcie1 PERST/WAKE readout",
                "writes": ["echo 1 > /sys/kernel/debug/pci-msm/rc_sel", "echo 26 > /sys/kernel/debug/pci-msm/case"],
                "expected_effect": "dmesg/debug output only; no enumerate, no PERST toggle",
                "approval_state": "candidate for V1365 bounded live proof",
            },
            {
                "name": "pcie1 enumerate",
                "writes": ["echo 1 > /sys/kernel/debug/pci-msm/rc_sel", "echo 11 > /sys/kernel/debug/pci-msm/case"],
                "expected_effect": "likely msm_pcie_enumerate(1), but exact call path still unproven",
                "approval_state": "not approved before V1365/V1366 evidence",
            },
        ],
        "source_facts": {
            "case_11": first_line(inputs["v1363_heads"], "11:"),
            "case_26": first_line(inputs["v1363_heads"], "26:"),
            "case_27": first_line(inputs["v1363_heads"], "27:"),
            "kallsyms_rc_select": first_line(inputs["v851_kallsyms"], "msm_pcie_debugfs_rc_select"),
            "kallsyms_case_select": first_line(inputs["v851_kallsyms"], "msm_pcie_debugfs_case_select"),
            "kallsyms_testcase": first_line(inputs["v851_kallsyms"], "msm_pcie_sel_debug_testcase"),
            "kallsyms_enumerate": first_line(inputs["v851_kallsyms"], "msm_pcie_enumerate"),
        },
        "hard_exclusions": [
            "host-only; no device command",
            "no debugfs/sysfs writes",
            "no case=11 enumerate",
            "no platform bind/unbind",
            "no PCI rescan",
            "no PMIC/GPIO/GDSC write",
            "no eSoC notify or BOOT_DONE",
            "no Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping",
            "no flash, boot image write, or partition write",
        ],
    }


def check_rows(manifest: dict[str, Any]) -> list[list[str]]:
    return [[key, bool_text(bool(value))] for key, value in sorted((manifest.get("checks") or {}).items())]


def contract_rows(manifest: dict[str, Any]) -> list[list[Any]]:
    return [[row["name"], "<br>".join(row["writes"]), row["expected_effect"], row["approval_state"]] for row in manifest.get("candidate_contracts", [])]


def fact_rows(manifest: dict[str, Any]) -> list[list[Any]]:
    return [[key, value] for key, value in (manifest.get("source_facts") or {}).items()]


def render_summary(manifest: dict[str, Any]) -> str:
    return "\n".join([
        "# V1364 pci-msm Debugfs Contract Classifier",
        "",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        "",
        markdown_table(["check", "pass"], check_rows(manifest)) if manifest.get("checks") else "",
        "",
    ])


def render_report(manifest: dict[str, Any]) -> str:
    return "\n".join([
        "# Native Init V1364 pci-msm Debugfs Contract Classifier",
        "",
        "## Summary",
        "",
        "- Cycle: `V1364`",
        "- Type: host-only classifier",
        f"- Decision: `{manifest['decision']}`",
        f"- Result: {'PASS' if manifest['pass'] else 'FAIL'}",
        "- Script: `scripts/revalidation/native_wifi_pci_msm_debugfs_contract_classifier_v1364.py`",
        "- Evidence:",
        "  - `tmp/wifi/v1364-pci-msm-debugfs-contract-classifier/manifest.json`",
        "  - `tmp/wifi/v1364-pci-msm-debugfs-contract-classifier/summary.md`",
        "",
        "## Decision",
        "",
        manifest["reason"],
        "",
        "## Candidate Contracts",
        "",
        markdown_table(["name", "writes", "expected_effect", "approval_state"], contract_rows(manifest)) if manifest.get("candidate_contracts") else "inputs missing",
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
        "- No debugfs/sysfs write, `case=11` enumerate, platform bind/unbind, PCI rescan,",
        "  PMIC/GPIO/GDSC write, eSoC notify/`BOOT_DONE`, Wi-Fi HAL, scan/connect,",
        "  credential handling, DHCP/routes, external ping, flash, boot image write,",
        "  or partition write.",
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

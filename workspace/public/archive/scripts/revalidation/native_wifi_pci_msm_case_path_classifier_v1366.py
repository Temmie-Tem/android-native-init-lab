#!/usr/bin/env python3
"""V1366 host-only pci-msm debugfs case-path classifier."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import markdown_table, repo_path
from a90harness.evidence import write_private_text, workspace_private_input_path


DEFAULT_OUT_DIR = Path("tmp/wifi/v1366-pci-msm-case-path-classifier")
REPORT_PATH = Path("docs/reports/NATIVE_INIT_V1366_PCI_MSM_CASE_PATH_CLASSIFIER_2026-06-01.md")
SOURCE_ROOT = Path("tmp/wifi/v766-icnss-qcacld-patch-apply-build/source")
KERNEL_DTS_ROOT = workspace_private_input_path("kernel_source", 'SM-A908N_KOR_12_Opensource', 'Kernel', 'arch', 'arm64', 'boot', 'dts', 'qcom')

INPUTS = {
    "pci_msm_source": SOURCE_ROOT / "drivers/pci/host/pci-msm.c",
    "sm8150_pcie_dtsi": KERNEL_DTS_ROOT / "sm8150-pcie.dtsi",
    "v1363_heads": Path("tmp/wifi/v1363-pci-msm-debugfs-surface-verifier-live/native/pci-msm-file-heads.txt"),
    "v1364_manifest": Path("tmp/wifi/v1364-pci-msm-debugfs-contract-classifier/manifest.json"),
    "v1365_manifest": Path("tmp/wifi/v1365-pci-msm-status-case-live/manifest.json"),
    "v1365_report": Path("docs/reports/NATIVE_INIT_V1365_PCI_MSM_STATUS_CASE_LIVE_2026-06-01.md"),
}


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def read_text(path: Path) -> str:
    return repo_path(path).read_text(encoding="utf-8", errors="replace")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(read_text(path))


def bool_text(value: bool) -> str:
    return "true" if value else "false"


def line_no(text: str, needle: str) -> int | None:
    for index, line in enumerate(text.splitlines(), start=1):
        if needle in line:
            return index
    return None


def first_line(text: str, needle: str) -> str:
    for line in text.splitlines():
        if needle in line:
            return line.strip()
    return ""


def block_between(text: str, start: str, end: str) -> str:
    start_index = text.find(start)
    if start_index < 0:
        return ""
    end_index = text.find(end, start_index + len(start))
    if end_index < 0:
        return text[start_index:]
    return text[start_index:end_index]


def pcie1_cell_index(dtsi: str) -> int | None:
    match = re.search(r"pcie1:\s+qcom,pcie@1c08000\s*\{(?P<body>.*?)\n\t\};", dtsi, flags=re.S)
    if not match:
        return None
    cell = re.search(r"cell-index\s*=\s*<(?P<idx>\d+)>;", match.group("body"))
    return int(cell.group("idx")) if cell else None


def build_checks(source: str, dtsi: str, v1365: dict[str, Any]) -> dict[str, bool]:
    case26_block = block_between(source, "case MSM_PCIE_GPIO_STATUS:", "case MSM_PCIE_ASSERT_PERST:")
    case11_block = block_between(source, "case MSM_PCIE_ENUMERATION:", "case MSM_PCIE_READ_PCIE_REGISTER:")
    return {
        "source_snapshot_has_pci_msm": "static void msm_pcie_sel_debug_testcase" in source,
        "debugfs_case_select_loops_bitmask": "if (rc_sel & BIT(i))" in source
        and "msm_pcie_sel_debug_testcase(&msm_pcie_dev[i], testcase)" in source,
        "rc_sel_default_is_bit0": "static u32 rc_sel = BIT(0);" in source,
        "rc_sel_max_is_bitmask": "rc_sel_max = (0x1 << MAX_RC_NUM) - 1;" in source,
        "pcie1_cell_index_is_1": pcie1_cell_index(dtsi) == 1,
        "case11_calls_msm_pcie_enumerate": "msm_pcie_enumerate(dev->rc_idx)" in case11_block,
        "case26_reads_perst_wake_gpio": case26_block.count("gpio_get_value") >= 2
        and "MSM_PCIE_GPIO_PERST" in case26_block
        and "MSM_PCIE_GPIO_WAKE" in case26_block,
        "case26_has_no_direct_mutating_call": all(
            token not in case26_block
            for token in (
                "gpio_set_value",
                "msm_pcie_enumerate",
                "msm_pcie_pm_control",
                "msm_pcie_enable",
                "msm_pcie_disable",
                "writel_relaxed",
            )
        ),
        "v1365_saw_transport_loss": v1365.get("decision") == "v1365-case26-transport-reset-reboot-risk",
    }


def classify() -> dict[str, Any]:
    missing = [str(path) for path in INPUTS.values() if not repo_path(path).exists()]
    if missing:
        return {
            "cycle": "V1366",
            "type": "host-only classifier",
            "generated_at": now_iso(),
            "decision": "v1366-inputs-missing",
            "pass": False,
            "reason": "required pci-msm source or prior evidence is missing",
            "next_step": "restore required inputs before any pci-msm debugfs write",
            "missing": missing,
        }

    source = read_text(INPUTS["pci_msm_source"])
    dtsi = read_text(INPUTS["sm8150_pcie_dtsi"])
    heads = read_text(INPUTS["v1363_heads"])
    v1364 = read_json(INPUTS["v1364_manifest"])
    v1365 = read_json(INPUTS["v1365_manifest"])
    checks = build_checks(source, dtsi, v1365)
    pcie1_index = pcie1_cell_index(dtsi)
    pcie1_rc_sel = 1 << pcie1_index if pcie1_index is not None else None
    v1365_rc_sel = 1
    v1365_target = "RC0" if v1365_rc_sel == 1 else "unknown"
    all_core = all(checks.values())

    decision = (
        "v1366-pci-msm-case-path-corrected-rc-selector-no-live-write"
        if all_core
        else "v1366-pci-msm-case-path-incomplete"
    )
    pass_condition = all_core
    reason = (
        "Reference pci-msm source proves rc_sel is a bitmask, not an ordinal RC index: "
        "V1365 used rc_sel=1 and therefore selected RC0, while pcie1/RC1 would require "
        "rc_sel=2. Source also shows case 26 is intended as PERST/WAKE gpio_get_value "
        "readout and case 11 calls msm_pcie_enumerate(dev->rc_idx). Because the live "
        "V1365 write still caused transport loss, no further pci-msm case write is "
        "approved without a new reboot-safe design and source/live parity check."
        if all_core
        else "one or more pci-msm source/evidence assumptions are not proven"
    )
    next_step = (
        "V1367 host-only corrected-RC1 design: decide whether rc_sel=2 case=26 can be made reboot-safe, or prefer a kernel-side msm_pcie_enumerate(1) shim path"
        if all_core
        else "repair classifier inputs before selecting any live pci-msm debugfs action"
    )

    return {
        "cycle": "V1366",
        "type": "host-only classifier",
        "generated_at": now_iso(),
        "decision": decision,
        "pass": pass_condition,
        "reason": reason,
        "next_step": next_step,
        "inputs": {name: str(path) for name, path in INPUTS.items()},
        "checks": checks,
        "facts": {
            "rc_sel_semantics": "bitmask: loop executes i when rc_sel & BIT(i)",
            "v1365_rc_sel_written": v1365_rc_sel,
            "v1365_actual_target": v1365_target,
            "pcie1_cell_index": pcie1_index,
            "pcie1_correct_rc_sel_bitmask": pcie1_rc_sel,
            "case_11_label": first_line(heads, "11:"),
            "case_26_label": first_line(heads, "26:"),
            "v1364_prior_decision": v1364.get("decision"),
            "v1365_decision": v1365.get("decision"),
            "source_line_rc_sel_default": line_no(source, "static u32 rc_sel = BIT(0);"),
            "source_line_case_select": line_no(source, "static ssize_t msm_pcie_debugfs_case_select"),
            "source_line_case11": line_no(source, "case MSM_PCIE_ENUMERATION:"),
            "source_line_case26": line_no(source, "case MSM_PCIE_GPIO_STATUS:"),
            "source_line_enumerate": line_no(source, "int msm_pcie_enumerate(u32 rc_idx)"),
        },
        "classification": [
            {
                "item": "V1365 rc_sel target",
                "result": "wrong-RC for pcie1",
                "detail": "rc_sel=1 selects BIT(0)/RC0; pcie1 has cell-index 1 and needs rc_sel=2",
            },
            {
                "item": "case 26 source behavior",
                "result": "intended read-only GPIO readout",
                "detail": "branch reads PERST/WAKE with gpio_get_value and contains no direct enumerate/pm/gpio_set/MMIO write call",
            },
            {
                "item": "case 11 source behavior",
                "result": "mutation/enumerate",
                "detail": "branch calls msm_pcie_enumerate(dev->rc_idx)",
            },
            {
                "item": "live approval",
                "result": "not approved",
                "detail": "V1365 transport loss means the source-intended readout is not enough to justify another case write without a new design",
            },
        ],
        "hard_exclusions": [
            "host-only; no device command",
            "no debugfs/sysfs writes",
            "no rc_sel=2 live retry",
            "no case=11 enumerate",
            "no PERST assert/deassert",
            "no PCI rescan or platform bind/unbind",
            "no PMIC/GPIO/GDSC write",
            "no eSoC notify or BOOT_DONE",
            "no Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping",
            "no flash, boot image write, or partition write",
        ],
    }


def check_rows(manifest: dict[str, Any]) -> list[list[str]]:
    return [[key, bool_text(bool(value))] for key, value in sorted((manifest.get("checks") or {}).items())]


def fact_rows(manifest: dict[str, Any]) -> list[list[Any]]:
    return [[key, value] for key, value in (manifest.get("facts") or {}).items()]


def classification_rows(manifest: dict[str, Any]) -> list[list[Any]]:
    return [[row["item"], row["result"], row["detail"]] for row in manifest.get("classification") or []]


def render_summary(manifest: dict[str, Any]) -> str:
    return "\n".join([
        "# V1366 pci-msm Case-path Classifier",
        "",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        "",
        markdown_table(["item", "result", "detail"], classification_rows(manifest)) if manifest.get("classification") else "",
        "",
    ])


def render_report(manifest: dict[str, Any]) -> str:
    return "\n".join([
        "# Native Init V1366 pci-msm Case-path Classifier",
        "",
        "## Summary",
        "",
        "- Cycle: `V1366`",
        "- Type: host-only classifier",
        f"- Decision: `{manifest['decision']}`",
        f"- Result: {'PASS' if manifest['pass'] else 'FAIL'}",
        "- Script: `scripts/revalidation/native_wifi_pci_msm_case_path_classifier_v1366.py`",
        "- Evidence:",
        "  - `tmp/wifi/v1366-pci-msm-case-path-classifier/manifest.json`",
        "  - `tmp/wifi/v1366-pci-msm-case-path-classifier/summary.md`",
        "",
        "## Decision",
        "",
        manifest["reason"],
        "",
        "## Classification",
        "",
        markdown_table(["item", "result", "detail"], classification_rows(manifest)) if manifest.get("classification") else "inputs missing",
        "",
        "## Checks",
        "",
        markdown_table(["check", "pass"], check_rows(manifest)) if manifest.get("checks") else "inputs missing",
        "",
        "## Facts",
        "",
        markdown_table(["fact", "value"], fact_rows(manifest)) if manifest.get("facts") else "inputs missing",
        "",
        "## Safety",
        "",
        "- Host-only; no device command or live runtime access.",
        "- No debugfs/sysfs write, corrected `rc_sel=2` live retry, `case=11`",
        "  enumerate, PERST assert/deassert, PCI rescan, platform bind/unbind,",
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

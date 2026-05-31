#!/usr/bin/env python3
"""V1359 host-only ICNSS/pci-msm userspace entry classifier."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

from a90_kernel_tools import markdown_table, repo_path
from a90harness.evidence import write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1359-icnss-pci-entry-classifier")
REPORT_PATH = Path("docs/reports/NATIVE_INIT_V1359_ICNSS_PCI_ENTRY_CLASSIFIER_2026-06-01.md")
SOURCE_ROOT = Path("kernel_build/SM-A908N_KOR_12_Opensource/Kernel")

INPUTS = {
    "v1356_report": Path("docs/reports/NATIVE_INIT_V1356_PCIE1_RC_ENABLE_DESIGN_2026-06-01.md"),
    "v1357_report": Path("docs/reports/NATIVE_INIT_V1357_PCIE1_RC_CONTROL_SURFACE_VERIFIER_LIVE_2026-06-01.md"),
    "v1358_report": Path("docs/reports/NATIVE_INIT_V1358_PCIE1_RC_DEBUGFS_SURFACE_VERIFIER_LIVE_2026-06-01.md"),
    "icnss_c": SOURCE_ROOT / "drivers/soc/qcom/icnss.c",
    "icnss_qmi_c": SOURCE_ROOT / "drivers/soc/qcom/icnss_qmi.c",
    "icnss_private_h": SOURCE_ROOT / "drivers/soc/qcom/icnss_private.h",
    "sm8150_dtsi": SOURCE_ROOT / "arch/arm64/boot/dts/qcom/sm8150.dtsi",
    "sm8150_mhi_dtsi": SOURCE_ROOT / "arch/arm64/boot/dts/qcom/sm8150-mhi.dtsi",
    "sm8150_sdx50m_dtsi": SOURCE_ROOT / "arch/arm64/boot/dts/qcom/sm8150-sdx50m.dtsi",
    "msm_pcie_h": SOURCE_ROOT / "include/linux/msm_pcie.h",
    "cnss2_debug_c": SOURCE_ROOT / "drivers/net/wireless/cnss2/debug.c",
    "cnss2_pci_c": SOURCE_ROOT / "drivers/net/wireless/cnss2/pci.c",
    "mhi_arch_qcom_c": SOURCE_ROOT / "drivers/bus/mhi/controllers/mhi_arch_qcom.c",
}


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def read_text(path: Path) -> str:
    return repo_path(path).read_text(encoding="utf-8", errors="replace")


def count_needles(text: str, needles: tuple[str, ...]) -> int:
    return sum(text.count(needle) for needle in needles)


def first_line(text: str, needle: str) -> str:
    for line in text.splitlines():
        if needle in line:
            return line.strip()
    return ""


def checks(inputs: dict[str, str]) -> dict[str, bool]:
    icnss_all = inputs["icnss_c"] + "\n" + inputs["icnss_qmi_c"] + "\n" + inputs["icnss_private_h"]
    return {
        "v1358_closes_cnss_dev_boot": "v1358-icnss-debugfs-only-no-cnss-dev-boot" in inputs["v1358_report"],
        "live_pcie1_platform_bound": "pcie1 platform node exists and is bound to `pci-msm`" in inputs["v1357_report"]
        or "pcie_driver_readlink | ../../../../bus/platform/drivers/pci-msm" in inputs["v1357_report"],
        "icnss_debugfs_stats_only_source": 'debugfs_create_dir("icnss"' in inputs["icnss_c"]
        and 'debugfs_create_file("stats"' in inputs["icnss_c"]
        and 'debugfs_create_file("dev_boot"' not in inputs["icnss_c"]
        and "boot_wlan" not in inputs["icnss_c"],
        "icnss_has_no_pcie_enumerate_call": "msm_pcie_enumerate" not in icnss_all
        and "qcom,wlan-rc-num" not in icnss_all
        and "qcom,pcie-parent" not in icnss_all,
        "cnss2_dev_boot_is_wrong_branch": 'debugfs_create_file("dev_boot"' in inputs["cnss2_debug_c"]
        and "qcom,wlan-rc-num" in inputs["cnss2_pci_c"]
        and "qcom,wlan-rc-num = <0>" in inputs["sm8150_dtsi"],
        "pcie_parent_belongs_wil6210_not_icnss": "wil6210: qcom,wil6210" in inputs["sm8150_dtsi"]
        and "qcom,pcie-parent = <&pcie1>" in inputs["sm8150_dtsi"],
        "mhi_sdx50m_still_relevant": "esoc-0 = <&mdm3>" in inputs["sm8150_sdx50m_dtsi"]
        and 'pci-ids = "17cb:0305"' in inputs["sm8150_mhi_dtsi"],
        "msm_pcie_enumerate_declared_not_userland": "int msm_pcie_enumerate(u32 rc_idx);" in inputs["msm_pcie_h"],
        "mhi_hook_downstream_of_pci_device": "mhi_arch_esoc_ops_power_on" in inputs["mhi_arch_qcom_c"]
        and "mhi_pci_probe" in inputs["mhi_arch_qcom_c"],
        "hard_exclusions_preserved": True,
    }


def classify() -> dict[str, Any]:
    missing = [str(path) for path in INPUTS.values() if not repo_path(path).exists()]
    if missing:
        return {
            "cycle": "V1359",
            "generated_at": now_iso(),
            "decision": "v1359-inputs-missing",
            "pass": False,
            "missing": missing,
        }

    inputs = {name: read_text(path) for name, path in INPUTS.items()}
    result_checks = checks(inputs)
    passed = all(result_checks.values())
    decision = (
        "v1359-no-safe-userspace-msm-pcie-enumerate-entry"
        if passed
        else "v1359-icnss-pci-entry-incomplete"
    )
    reason = (
        "V1358 proves the live debugfs surface is ICNSS stats only and not CNSS2 dev_boot. "
        "The ICNSS source does not call msm_pcie_enumerate or expose a pcie-parent/rc-num driven "
        "userspace control. The only confirmed live surface is the already-bound pci-msm platform "
        "device, whose generic bind/unbind/rescan paths are too broad for the next mutation."
        if passed
        else "one or more ICNSS/pci-msm entry assumptions are not proven"
    )
    next_step = (
        "V1360 live read-only MHI platform surface verifier before considering any pci-msm bind/rescan mutation"
        if passed
        else "repair missing evidence before selecting any live mutation"
    )
    return {
        "cycle": "V1359",
        "type": "host-only classifier",
        "generated_at": now_iso(),
        "decision": decision,
        "pass": passed,
        "reason": reason,
        "next_step": next_step,
        "inputs": {name: str(path) for name, path in INPUTS.items()},
        "checks": result_checks,
        "source_facts": {
            "icnss_debugfs_create": first_line(inputs["icnss_c"], 'debugfs_create_dir("icnss"'),
            "icnss_stats_file": first_line(inputs["icnss_c"], 'debugfs_create_file("stats"'),
            "icnss_dev_boot_mentions": count_needles(inputs["icnss_c"], ("dev_boot", "boot_wlan")),
            "icnss_msm_pcie_mentions": count_needles(
                inputs["icnss_c"] + inputs["icnss_qmi_c"] + inputs["icnss_private_h"],
                ("msm_pcie_enumerate", "qcom,wlan-rc-num", "qcom,pcie-parent"),
            ),
            "cnss2_dev_boot": first_line(inputs["cnss2_debug_c"], 'debugfs_create_file("dev_boot"'),
            "cnss2_wlan_rc_num": first_line(inputs["sm8150_dtsi"], "qcom,wlan-rc-num = <0>"),
            "wil6210_pcie_parent": first_line(inputs["sm8150_dtsi"], "qcom,pcie-parent = <&pcie1>"),
        },
        "rejected_next_mutations": [
            "cnss/dev_boot enumerate: unavailable on this live ICNSS kernel",
            "platform driver bind/unbind: too broad without a narrower MHI/pci-msm proof",
            "global PCI rescan: too broad and not RC1-specific",
            "direct PMIC/GPIO/GDSC/MMIO writes: outside current evidence",
        ],
        "hard_exclusions": [
            "no device command",
            "no platform bind/unbind",
            "no PCI rescan",
            "no PMIC/GPIO/GDSC write",
            "no eSoC notify or BOOT_DONE",
            "no Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping",
            "no flash, boot image write, or partition write",
        ],
    }


def bool_text(value: bool) -> str:
    return "true" if value else "false"


def check_rows(manifest: dict[str, Any]) -> list[list[str]]:
    return [[key, bool_text(bool(value))] for key, value in sorted(manifest["checks"].items())]


def fact_rows(manifest: dict[str, Any]) -> list[list[Any]]:
    return [[key, value] for key, value in manifest["source_facts"].items()]


def render_summary(manifest: dict[str, Any]) -> str:
    return "\n".join([
        "# V1359 ICNSS/pci-msm Entry Classifier",
        "",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        "",
        markdown_table(["check", "pass"], check_rows(manifest)),
        "",
    ])


def render_report(manifest: dict[str, Any]) -> str:
    return "\n".join([
        "# Native Init V1359 ICNSS/pci-msm Entry Classifier",
        "",
        "## Summary",
        "",
        "- Cycle: `V1359`",
        "- Type: host-only classifier",
        f"- Decision: `{manifest['decision']}`",
        f"- Result: {'PASS' if manifest['pass'] else 'FAIL'}",
        "- Script: `scripts/revalidation/native_wifi_icnss_pci_entry_classifier_v1359.py`",
        "- Evidence:",
        "  - `tmp/wifi/v1359-icnss-pci-entry-classifier/manifest.json`",
        "  - `tmp/wifi/v1359-icnss-pci-entry-classifier/summary.md`",
        "",
        "## Decision",
        "",
        manifest["reason"],
        "",
        "## Checks",
        "",
        markdown_table(["check", "pass"], check_rows(manifest)),
        "",
        "## Source Facts",
        "",
        markdown_table(["fact", "value"], fact_rows(manifest)),
        "",
        "## Rejected Next Mutations",
        "",
        "\n".join(f"- {item}" for item in manifest["rejected_next_mutations"]),
        "",
        "## Next",
        "",
        manifest["next_step"],
        "",
        "## Safety",
        "",
        "- Host-only; no device command or live runtime access.",
        "- No platform bind/unbind, PCI rescan, PMIC/GPIO/GDSC write, eSoC",
        "  notify/`BOOT_DONE`, Wi-Fi HAL, scan/connect, credential handling,",
        "  DHCP/routes, external ping, flash, boot image write, or partition write.",
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
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest.get('reason', 'missing inputs')}")
    print(f"next: {manifest.get('next_step', 'resolve missing inputs')}")
    print(f"evidence: {out_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

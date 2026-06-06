#!/usr/bin/env python3
"""V1642 host-only classifier for SDX50M main-rail / PMIC owner evidence."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from a90harness.evidence import EvidenceStore, write_private_text

REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
SOURCE_ROOT = REPO_ROOT / "tmp/wifi/v766-icnss-qcacld-patch-apply-build/source"
DEFAULT_OUT_DIR = REPO_ROOT / "tmp/wifi/v1642-sdx-power-owner-classifier"
DEFAULT_REPORT_PATH = REPO_ROOT / "docs/reports/NATIVE_INIT_V1642_SDX_POWER_OWNER_CLASSIFIER_2026-06-02.md"
FILES = {
    "external_soc": SOURCE_ROOT / "arch/arm64/boot/dts/qcom/sdx5xm-external-soc.dtsi",
    "ap_sdxprairie_link": SOURCE_ROOT / "arch/arm64/boot/dts/qcom/sm8150-sdxprairie.dtsi",
    "ap_pcie": SOURCE_ROOT / "arch/arm64/boot/dts/qcom/sm8150-pcie.dtsi",
    "sdx_regulator": SOURCE_ROOT / "arch/arm64/boot/dts/qcom/sdxprairie-regulator.dtsi",
    "sdx_soc": SOURCE_ROOT / "arch/arm64/boot/dts/qcom/sdxprairie.dtsi",
    "r3q_overlay": SOURCE_ROOT / "arch/arm64/boot/dts/samsung/renovation/sm8150-sec-r3q-kor-overlay-r00.dts",
}


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


def extract_block(text: str, start_pattern: str, max_lines: int = 120) -> str:
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if re.search(start_pattern, line):
            return "\n".join(lines[index:index + max_lines])
    return ""


def find_bootloader_binaries() -> list[str]:
    hits: list[str] = []
    roots = [REPO_ROOT / "stage3", REPO_ROOT / "tmp/wifi"]
    tokens = ("xbl", "abl", "non-hlos", "non_hlos", "pmic", "modem")
    suffixes = (".img", ".bin", ".mbn", ".elf", ".tar", ".lz4", ".md5")
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            try:
                relative = path.relative_to(REPO_ROOT)
            except ValueError:
                continue
            if "source" in relative.parts or "ramdisk" in relative.parts:
                continue
            name = path.name.lower()
            if name.endswith(suffixes) and any(token in name for token in tokens):
                hits.append(str(relative))
                if len(hits) >= 80:
                    return sorted(hits)
    return sorted(hits)


def classify() -> dict[str, Any]:
    texts = {key: read_text(path) for key, path in FILES.items()}
    mdm3_block = extract_block(texts["external_soc"], r"mdm3:\s*qcom,mdm3")
    r3q_mdm3_block = extract_block(texts["r3q_overlay"], r"qcom,mdm3")
    pcie1_block = extract_block(texts["ap_pcie"], r"pcie1:\s*qcom,pcie@1c08000", 280)
    sdx_pcie_ep_block = extract_block(texts["sdx_soc"], r"pcie_ep:\s*qcom,pcie@", 120)
    sdx_reg_block = extract_block(texts["sdx_regulator"], r"PMXPRAIRIE S1 \+ S6 = VDD_MODEM", 170)
    boot_hits = find_bootloader_binaries()

    checks = {
        "all_sources_present": all(bool(texts[key]) for key in FILES),
        "mdm3_ext_sdx50m": "qcom,ext-sdx50m" in mdm3_block or "qcom,ext-sdx50m" in r3q_mdm3_block,
        "mdm3_has_soft_reset_gpio": "qcom,ap2mdm-soft-reset-gpio" in mdm3_block or "qcom,ap2mdm-soft-reset-gpio" in r3q_mdm3_block,
        "mdm3_has_no_supply_property": not re.search(r"supply\s*=|regulator", mdm3_block + "\n" + r3q_mdm3_block),
        "ap_sdx_link_deletes_vdd_mss": "/delete-property/ vdd_mss-supply" in texts["ap_sdxprairie_link"],
        "ap_mhi_links_esoc0_to_mdm3": "esoc-0 = <&mdm3>;" in texts["ap_sdxprairie_link"],
        "ap_pcie1_supplies_are_rc_side": all(token in pcie1_block for token in ("pcie_1_gdsc", "pm8150l_l3", "pm8150_l5", "VDD_CX_LEVEL")),
        "sdx_has_internal_vdd_modem": "VDD_MODEM_LEVEL" in sdx_reg_block and "vdd_mss-supply = <&VDD_MODEM_LEVEL>" in texts["sdx_soc"],
        "sdx_has_wlan_internal_supply": "vdd-wlan-aon-supply = <&pmxprairie_s3>" in texts["sdx_soc"],
        "bootloader_pmic_binaries_absent": not boot_hits,
    }
    owner_rows = [
        {
            "surface": "AP qcom,mdm3 external-soc node",
            "owner": "AP kernel eSoC provider",
            "finding": "GPIO handshake only; no regulator/supply property in mdm3 block.",
            "class": "closed-no-main-rail-control",
        },
        {
            "surface": "AP pcie1 RC supplies",
            "owner": "AP msm_pcie driver",
            "finding": "pcie_1_gdsc, pm8150l_l3, pm8150_l5, VDD_CX_LEVEL are RC-side prerequisites; not proven SDX main rail controls.",
            "class": "diagnostic-not-main-rail",
        },
        {
            "surface": "SDXprairie regulators",
            "owner": "SDX-side PMIC/RPMH domain",
            "finding": "VDD_MODEM_LEVEL, pmxprairie rails, and wlan supplies are defined in SDX-side DTS, not as AP mdm3 controls.",
            "class": "candidate-owner-outside-ap-native",
        },
        {
            "surface": "bootloader / PMIC config artifacts",
            "owner": "bootloader or PMIC firmware if present",
            "finding": "No binary-like xbl/abl/NON-HLOS/pmic/modem artifacts found in bounded repo scope.",
            "class": "missing-artifact",
        },
    ]
    pass_ok = all(checks.values())
    decision = "v1642-sdx-main-rail-owner-outside-ap-source-pass" if pass_ok else "v1642-sdx-power-owner-review"
    return {
        "cycle": "V1642",
        "type": "host-only SDX50M power owner classifier",
        "decision": decision,
        "pass": pass_ok,
        "checks": checks,
        "owner_rows": owner_rows,
        "files": {key: rel(path) for key, path in FILES.items()},
        "bootloader_pmic_binary_hits": boot_hits,
        "excerpts": {
            "mdm3_block": mdm3_block[:2500],
            "r3q_mdm3_block": r3q_mdm3_block[:2500],
            "pcie1_block": pcie1_block[:2500],
            "sdx_regulator_block": sdx_reg_block[:2500],
            "sdx_pcie_ep_block": sdx_pcie_ep_block[:2500],
        },
        "next": {
            "recommended_cycle": "V1643",
            "type": "read-only partition/source acquisition plan or host-only bootloader gap handoff",
            "reason": "the remaining suspected owner is outside AP kernel source and absent from bounded repo artifacts",
            "no_live_write": True,
        },
    }


def render_report(result: dict[str, Any]) -> str:
    lines = [
        "# Native Init V1642 SDX50M Power Owner Classifier",
        "",
        "## Summary",
        "",
        "- Cycle: `V1642`",
        "- Type: host-only SDX50M power owner classifier",
        f"- Decision: `{result['decision']}`",
        f"- Result: {'PASS' if result['pass'] else 'REVIEW'}",
        "- Reason: AP mdm3/eSoC source exposes GPIO handshake only; AP pcie1 supplies are RC-side; SDX VDD_MODEM/WLAN rails live in SDX-side source or bootloader/PMIC domain, not as an AP-native safe write target.",
        "",
        "## Checks",
        "",
    ]
    for key, value in result["checks"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend([
        "",
        "## Owner Table",
        "",
        "| surface | owner | class | finding |",
        "|---|---|---|---|",
    ])
    for row in result["owner_rows"]:
        lines.append(f"| {row['surface']} | {row['owner']} | {row['class']} | {row['finding']} |")
    lines.extend([
        "",
        "## Interpretation",
        "",
        "The unknown SDX50M main-rail prerequisite is not represented as a controllable AP `qcom,mdm3` regulator or AP eSoC provider operation. The AP side links `mhi_0` to `mdm3` and gives pcie1 RC supply names, but those are not sufficient to justify a PMIC/GDSC write gate. SDX-side source names VDD_MODEM and WLAN rails, but those belong to the SDX/PMXPRAIRIE domain and are not currently reachable as a narrow AP-native write surface.",
        "",
        f"Bounded bootloader/PMIC binary artifact hits: `{len(result['bootloader_pmic_binary_hits'])}`",
        "",
        "## Next",
        "",
        "V1643 should stay non-mutating: either prepare a read-only partition/artifact acquisition plan for bootloader/PMIC ownership evidence, or hand off that external artifact gap explicitly. Do not design a live PMIC/GPIO/GDSC write until a named owner, voltage/sequence constraints, and rollbackable control surface are identified.",
        "",
        "## Safety Scope",
        "",
        "V1642 is host-only. It performs no device command, flash, reboot, partition write, Wi-Fi HAL start, scan/connect, credential handling, DHCP/routes, external ping, PMIC/GPIO/GDSC write, eSoC notify/`BOOT_DONE` spoof, pci-msm debugfs write, global PCI rescan, or platform bind/unbind.",
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
    write_private_text(args.out_dir / "summary.md", report)
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

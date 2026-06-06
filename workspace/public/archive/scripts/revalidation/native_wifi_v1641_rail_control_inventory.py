#!/usr/bin/env python3
"""V1641 host-only SDX50M rail/control inventory classifier."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from a90harness.evidence import EvidenceStore, write_private_text


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1641-rail-control-inventory"
DEFAULT_REPORT_PATH = REPO_ROOT / "docs" / "reports" / "NATIVE_INIT_V1641_RAIL_CONTROL_INVENTORY_2026-06-02.md"
REPORTS = {
    "v1244": REPO_ROOT / "docs/reports/NATIVE_INIT_V1244_ANDROID_POWER_SURFACE_CLASSIFIER_2026-05-31.md",
    "v1252": REPO_ROOT / "docs/reports/NATIVE_INIT_V1252_PMIC_POWER_WRITE_GATE_PLAN_2026-05-31.md",
    "v1268": REPO_ROOT / "docs/reports/NATIVE_INIT_V1268_AP2MDM_VALUE_OBSERVER_CLASSIFIER_2026-05-31.md",
    "v1276": REPO_ROOT / "docs/reports/NATIVE_INIT_V1276_PMIC_GPIO9_POLARITY_CLASSIFIER_2026-05-31.md",
    "v1287": REPO_ROOT / "docs/reports/NATIVE_INIT_V1287_SDX50M_POWER_GAP_CLASSIFIER_2026-05-31.md",
    "v1306": REPO_ROOT / "docs/reports/NATIVE_INIT_V1306_EXT_MDM_PMIC_GDSC_BRANCH_CLASSIFIER_2026-05-31.md",
    "v1355": REPO_ROOT / "docs/reports/NATIVE_INIT_V1355_PMIC_GPIO9_PON_PARITY_CLASSIFIER_2026-06-01.md",
    "v1559": REPO_ROOT / "docs/reports/NATIVE_INIT_V1559_ANDROID_PRE_ENDPOINT_ORDER_CLASSIFIER_2026-06-02.md",
    "v1639": REPO_ROOT / "docs/reports/NATIVE_INIT_V1639_PON_HIGH_EVIDENCE_RECONCILIATION_2026-06-02.md",
    "v1640": REPO_ROOT / "docs/reports/NATIVE_INIT_V1640_MODEM_RAIL_PMIC_GATE_PLAN_2026-06-02.md",
    "pon": REPO_ROOT / "docs/reports/ESOC_PON_SOURCE_ANALYSIS_2026-06-02.md",
    "dtb": REPO_ROOT / "docs/reports/ESOC_DTB_PARITY_2026-06-02.md",
}
PON_SOURCE = REPO_ROOT / "tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/esoc/esoc-mdm-pon.c"
FOURX_SOURCE = REPO_ROOT / "tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/esoc/esoc-mdm-4x.c"


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


def has(report: str, needle: str) -> bool:
    return needle in report


def find_limited_artifacts() -> list[str]:
    hits: list[str] = []
    search_roots = [REPO_ROOT / "stage3", REPO_ROOT / "tmp" / "wifi"]
    name_tokens = ("xbl", "abl", "non-hlos", "non_hlos", "modem", "pmic")
    binary_suffixes = (".img", ".bin", ".mbn", ".elf", ".tar", ".lz4", ".md5")
    for root in search_roots:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            try:
                relative = path.relative_to(REPO_ROOT)
            except ValueError:
                continue
            parts = set(relative.parts)
            if "source" in parts or "ramdisk" in parts:
                continue
            name = path.name.lower()
            if not name.endswith(binary_suffixes):
                continue
            if any(token in name for token in name_tokens):
                hits.append(str(relative))
                if len(hits) >= 80:
                    return sorted(hits)
    return sorted(hits)


def classify() -> dict[str, Any]:
    texts = {key: read_text(path) for key, path in REPORTS.items()}
    pon_source = read_text(PON_SOURCE)
    fourx_source = read_text(FOURX_SOURCE)
    provider_has_regulator_code = any(token in (pon_source + fourx_source).lower() for token in ("regulator", "vreg", "supply"))
    artifacts = find_limited_artifacts()

    inventory = [
        {
            "candidate": "PM8150L GPIO9/PON",
            "class": "closed-reject-direct-write",
            "evidence": "V1276/V1355/V1639 show parity-correct kernel-owned PON path; provider source drives it naturally.",
            "write_surface": "userspace GPIO line request/hold rejected",
            "rollback_risk": "high if misused; can hold modem reset line incorrectly",
            "allowed_next_action": "read-only/source only",
            "checks": {
                "v1276_out_high_parity": has(texts["v1276"], "out/high"),
                "v1355_pulse_parity": has(texts["v1355"], "PON low pulse ms"),
                "v1639_source_order": has(texts["v1639"], "PON high inferred from source order: `True`"),
            },
        },
        {
            "candidate": "GPIO135/AP2MDM",
            "class": "closed-reject-direct-write",
            "evidence": "Natural provider path reaches AP2MDM; direct write would bypass eSoC semantics.",
            "write_surface": "reject direct TLMM GPIO write",
            "rollback_risk": "high; can invert provider ordering",
            "allowed_next_action": "observe only",
            "checks": {
                "v1639_ap2mdm_seen": has(texts["v1639"], "GPIO135/AP2MDM high time: `9.480079`"),
                "source_ap2mdm_after_sleep": "gpio_direction_output(MDM_GPIO(mdm, AP2MDM_STATUS), 1);" in pon_source,
            },
        },
        {
            "candidate": "GPIO142/MDM2AP",
            "class": "observe-only-response-input",
            "evidence": "V1638/V1639 collect IRQ delta 0; this is the discriminator, not a control.",
            "write_surface": "none",
            "rollback_risk": "n/a",
            "allowed_next_action": "observe IRQ/level only",
            "checks": {
                "v1639_gpio142_zero": has(texts["v1639"], "GPIO142/MDM2AP IRQ delta: `0`"),
                "v1244_android_positive_contrast": has(texts["v1244"], "Android reaches WLAN-PD"),
            },
        },
        {
            "candidate": "GPIO141/errfatal",
            "class": "observe-only-response-input",
            "evidence": "V1638/V1639 collect errfatal IRQ delta 0; it can identify modem crash/fatal response only.",
            "write_surface": "none",
            "rollback_risk": "n/a",
            "allowed_next_action": "observe IRQ only",
            "checks": {
                "v1639_errfatal_zero": has(texts["v1639"], "mdm errfatal IRQ delta: `0`"),
            },
        },
        {
            "candidate": "pcie1 GDSC / clocks / refclk / PERST",
            "class": "diagnostic-not-primary-write-target",
            "evidence": "Prior forced-RC1 work proves AP-side PCIe can move, but natural-path MDM2AP remains the current discriminator; blind GDSC/RC1 writes contaminate the contract.",
            "write_surface": "reject blind debugfs/sysfs enable or pci-msm case write",
            "rollback_risk": "medium/high; can reset transport or train dead endpoint",
            "allowed_next_action": "source/static ownership analysis or read-only snapshot only",
            "checks": {
                "v1306_gdsc_gap": has(texts["v1306"], "PCIe1 GDSC native value"),
                "v1640_reject_blind_gdsc": has(texts["v1640"], "pcie_1_gdsc 0mV"),
                "dtb_pcie1_present": has(texts["dtb"], "pcie_1_gdsc"),
            },
        },
        {
            "candidate": "unknown SDX50M main rail / bootloader PMIC default",
            "class": "candidate-unowned-not-writeable-yet",
            "evidence": "eSoC provider has no regulator code, DTB has no mdm3 regulator supply, and no repo bootloader/PMIC config artifact currently names the rail.",
            "write_surface": "unknown; no safe live write target identified",
            "rollback_risk": "high until owner and voltage constraints are known",
            "allowed_next_action": "host-only artifact/source owner search before any live preflight",
            "checks": {
                "provider_regulator_code_absent": not provider_has_regulator_code,
                "pon_report_no_regulator": has(texts["pon"], "Provider has ZERO power/regulator code"),
                "dtb_no_differential": has(texts["dtb"], "DTB parity = PASS"),
                "bootloader_pmic_binary_hits": artifacts[:20],
            },
        },
    ]
    all_required = all(all(bool(value) for value in item["checks"].values() if not isinstance(value, list)) for item in inventory)
    safe_write_targets = [item["candidate"] for item in inventory if "candidate-unowned" not in item["class"] and "write" not in item["class"] and item["write_surface"] not in ("none", "unknown; no safe live write target identified")]
    decision = "v1641-no-safe-live-write-target-host-inventory-pass" if all_required and not safe_write_targets else "v1641-rail-control-inventory-review"
    return {
        "cycle": "V1641",
        "type": "host-only rail/control inventory classifier",
        "decision": decision,
        "pass": decision.endswith("pass"),
        "inventory": inventory,
        "safe_write_targets": safe_write_targets,
        "source": {
            "pon_source": rel(PON_SOURCE),
            "fourx_source": rel(FOURX_SOURCE),
            "provider_has_regulator_code": provider_has_regulator_code,
        },
        "artifact_scan": {
            "scope": "limited stage3/tmp-wifi binary-like bootloader or PMIC artifacts, excluding source and ramdisk subtrees",
            "hits": artifacts,
        },
        "next": {
            "recommended_cycle": "V1642",
            "type": "host-only bootloader/PMIC-owner artifact classifier",
            "reason": "the only remaining candidate is an unnamed SDX50M main-rail or bootloader/PMIC default; identify owner and constraints before any live write",
            "no_live_write": True,
        },
    }


def render_report(result: dict[str, Any]) -> str:
    lines = [
        "# Native Init V1641 Rail / Control Inventory",
        "",
        "## Summary",
        "",
        "- Cycle: `V1641`",
        "- Type: host-only rail/control inventory classifier",
        f"- Decision: `{result['decision']}`",
        f"- Result: {'PASS' if result['pass'] else 'REVIEW'}",
        "- Reason: no named safe live write target is currently justified; the only remaining candidate is an unowned SDX50M main-rail / bootloader-PMIC prerequisite.",
        "",
        "## Inventory",
        "",
        "| candidate | class | write surface | allowed next action |",
        "|---|---|---|---|",
    ]
    for item in result["inventory"]:
        lines.append(
            f"| {item['candidate']} | {item['class']} | {item['write_surface']} | {item['allowed_next_action']} |"
        )
    lines.extend([
        "",
        "## Key Evidence",
        "",
    ])
    for item in result["inventory"]:
        lines.append(f"### {item['candidate']}")
        lines.append("")
        lines.append(f"- class: `{item['class']}`")
        lines.append(f"- evidence: {item['evidence']}")
        lines.append(f"- rollback risk: {item['rollback_risk']}")
        lines.append(f"- checks: `{json.dumps(item['checks'], sort_keys=True)}`")
        lines.append("")
    lines.extend([
        "## Source / Artifact Notes",
        "",
        f"- eSoC provider has regulator code: `{result['source']['provider_has_regulator_code']}`",
        f"- limited bootloader/PMIC binary artifact hits: `{len(result['artifact_scan']['hits'])}`",
        "- Artifact scan is intentionally bounded and excludes source subtrees to avoid broad/OOM-prone searches.",
        "",
        "## Decision",
        "",
        "No safe live PMIC/GPIO/GDSC write target is identified by current evidence. PMIC GPIO9/PON and GPIO135/AP2MDM are closed as direct userspace write targets; GPIO142 and errfatal are observe-only; pcie1 GDSC/clocks/refclk are diagnostic and must not be blind-enabled from this state. The remaining candidate is an unnamed SDX50M main rail or bootloader/PMIC default outside the eSoC provider source and current DTB contract.",
        "",
        "## Next",
        "",
        "V1642 should be host-only: classify bootloader/PMIC-owner artifacts and source references for the unknown SDX50M main-rail prerequisite. It should not perform live write, flash, reboot, PMIC/GPIO/GDSC mutation, Wi-Fi HAL start, scan/connect, credentials, DHCP/routes, external ping, eSoC notify/BOOT_DONE, PCI rescan, or platform bind/unbind.",
        "",
        "## Safety Scope",
        "",
        "V1641 is host-only. It performs no device command, flash, reboot, partition write, Wi-Fi HAL start, scan/connect, credential handling, DHCP/routes, external ping, PMIC/GPIO/GDSC write, eSoC notify/`BOOT_DONE` spoof, pci-msm debugfs write, global PCI rescan, or platform bind/unbind.",
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

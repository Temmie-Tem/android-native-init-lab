#!/usr/bin/env python3
"""V1656 host-only reconciliation of XBL context with Android-good references."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from a90harness.evidence import EvidenceStore, write_private_text

REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
DEFAULT_INPUT = REPO_ROOT / "tmp/wifi/v1655-xbl-context-interpretation/manifest.json"
DEFAULT_OUT_DIR = REPO_ROOT / "tmp/wifi/v1656-xbl-reference-reconciliation"
DEFAULT_REPORT_PATH = REPO_ROOT / "docs/reports/NATIVE_INIT_V1656_XBL_REFERENCE_RECONCILIATION_2026-06-02.md"
EXPECTED_INPUT_DECISION = "v1655-xbl-context-interpretation-pass"


@dataclass(frozen=True)
class Reference:
    key: str
    path: Path
    role: str
    required: tuple[str, ...]


REFERENCES = (
    Reference(
        "android-v852-provider-positive",
        REPO_ROOT / "docs/reports/NATIVE_INIT_V852_ANDROID_EXT_MDM_PROVIDER_SURFACE_HANDOFF_2026-05-25.md",
        "Android-good lower Wi-Fi/provider positive control",
        ("mdm3 state", "ONLINE", "GPIO 142", "BDF", "wlan0"),
    ),
    Reference(
        "native-v1461-provider-block",
        REPO_ROOT / "docs/reports/NATIVE_INIT_V1461_PROVIDER_THREAD_STATE_CLASSIFIER_2026-06-01.md",
        "native provider reaches sdx50m path but no endpoint response",
        ("sdx50m_toggle_soft_reset", "mdm_subsys_powerup", "GPIO135", "GPIO142", "wlan0"),
    ),
    Reference(
        "android-v1559-pre-endpoint-order",
        REPO_ROOT / "docs/reports/NATIVE_INIT_V1559_ANDROID_PRE_ENDPOINT_ORDER_CLASSIFIER_2026-06-02.md",
        "Android-good AP2MDM ordering before BDF",
        ("GPIO135/AP2MDM", "before BDF", "native_endpoint_silent", "scan/connect"),
    ),
    Reference(
        "v1524-pcie-path-attribution",
        REPO_ROOT / "docs/reports/NATIVE_INIT_V1524_ENDPOINT_TRIGGER_ATTRIBUTION_CLASSIFIER_2026-06-02.md",
        "PCIe/MHI resume path vs debugfs TEST path",
        ("Android V852", "RC1 L0", "MSM_PCIE_RESUME", "TEST:11", "scan/connect"),
    ),
    Reference(
        "esoc-pon-source-analysis",
        REPO_ROOT / "docs/reports/ESOC_PON_SOURCE_ANALYSIS_2026-06-02.md",
        "exact provider PON source and polarity closure",
        ("GPIO9 PON", "GPIO135", "GPIO142", "ZERO power/regulator", "not on disk"),
    ),
    Reference(
        "esoc-dtb-parity",
        REPO_ROOT / "docs/reports/ESOC_DTB_PARITY_2026-06-02.md",
        "native/Android DTB and bootloader/config parity closure",
        ("DTB parity", "bootloader", "NO", "only remaining unknown", "GPIO142"),
    ),
    Reference(
        "natural-path-contract",
        REPO_ROOT / "docs/reports/ESOC_NATURAL_PATH_MDM2AP_OBSERVATION_CONTRACT_2026-06-02.md",
        "next live natural-path observation contract",
        ("natural", "GPIO142", "errfatal", "forced RC1", "fake-ONLINE"),
    ),
)


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def matching_lines(path: Path, needles: tuple[str, ...], *, limit: int = 18) -> list[dict[str, str]]:
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    lower_needles = [needle.lower() for needle in needles]
    out: list[dict[str, str]] = []
    for lineno, line in enumerate(lines, start=1):
        lower = line.lower()
        if any(needle in lower for needle in lower_needles):
            out.append({"line": str(lineno), "text": line.strip()})
            if len(out) >= limit:
                break
    return out


def reference_matrix() -> list[dict[str, Any]]:
    matrix: list[dict[str, Any]] = []
    for reference in REFERENCES:
        text = reference.path.read_text(encoding="utf-8", errors="replace") if reference.path.exists() else ""
        required_hits = {needle: needle.lower() in text.lower() for needle in reference.required}
        matrix.append({
            "key": reference.key,
            "path": rel(reference.path),
            "exists": reference.path.exists(),
            "role": reference.role,
            "required_hits": required_hits,
            "all_required_present": reference.path.exists() and all(required_hits.values()),
            "anchors": matching_lines(reference.path, reference.required),
        })
    return matrix


def summarize_xbl(input_manifest: dict[str, Any]) -> dict[str, Any]:
    artifacts = input_manifest.get("artifact_summaries", [])
    token_totals: dict[str, int] = {}
    class_totals: dict[str, int] = {}
    for artifact in artifacts:
        for token, count in artifact.get("token_counts", {}).items():
            token_totals[token] = token_totals.get(token, 0) + int(count)
        for class_name, count in artifact.get("class_counts", {}).items():
            class_totals[class_name] = class_totals.get(class_name, 0) + int(count)
    return {
        "total_records": input_manifest.get("total_records", 0),
        "cross_slot_duplicate_groups": input_manifest.get("cross_slot_duplicate_groups", 0),
        "token_totals": dict(sorted(token_totals.items())),
        "class_totals": dict(sorted(class_totals.items())),
        "has_sdx_pon_pmic": all(token_totals.get(token, 0) > 0 for token in ("sdx", "pon", "pmic")),
        "has_pcie_context": class_totals.get("pcie-context", 0) > 0,
        "has_gpio_token": token_totals.get("gpio", 0) > 0,
    }


def build_reconciliation(xbl: dict[str, Any], matrix: list[dict[str, Any]]) -> list[dict[str, str]]:
    by_key = {entry["key"]: entry for entry in matrix}
    dtb_parity = by_key.get("esoc-dtb-parity", {}).get("all_required_present", False)
    pon_closed = by_key.get("esoc-pon-source-analysis", {}).get("all_required_present", False)
    android_positive = by_key.get("android-v852-provider-positive", {}).get("all_required_present", False)
    native_block = by_key.get("native-v1461-provider-block", {}).get("all_required_present", False)
    natural_contract = by_key.get("natural-path-contract", {}).get("all_required_present", False)
    return [
        {
            "topic": "xbl-as-information-source",
            "status": "supported",
            "finding": "XBL contains SDX/PON/PMIC/RPMh/AOP/PCIe context and is useful for owner attribution.",
            "basis": f"records={xbl['total_records']} cross_slot_dupes={xbl['cross_slot_duplicate_groups']} has_sdx_pon_pmic={xbl['has_sdx_pon_pmic']}",
            "limit": "The records are redacted metadata; they do not expose a direct write target.",
        },
        {
            "topic": "xbl-as-native-vs-android-differential",
            "status": "not-supported",
            "finding": "XBL context does not currently explain a native-vs-Android differential.",
            "basis": f"dtb_and_bootloader_parity_reference_present={dtb_parity}; only boot partition changes between native and Android rollback flow.",
            "limit": "XBL can identify historical ownership, but identical bootloader artifacts are not a mutation target without a concrete differential.",
        },
        {
            "topic": "provider-pon-path",
            "status": "closed-host-side",
            "finding": "The AP/provider PON sequence remains host-verified rather than the active defect.",
            "basis": f"pon_source_closure_present={pon_closed}; native provider block present={native_block}",
            "limit": "Host evidence cannot prove whether the SDX50M main rail electrically responds to the correct PON pulse.",
        },
        {
            "topic": "lower-wifi-path",
            "status": "blocked-before-connect",
            "finding": "Wi-Fi HAL, scan/connect, DHCP, and external ping remain downstream.",
            "basis": f"android_positive_reference={android_positive}; native provider block={native_block}",
            "limit": "Native still lacks GPIO142/MDM2AP response, RC1 L0, MHI, WLFW, BDF, FW-ready, and wlan0.",
        },
        {
            "topic": "next-live-gate",
            "status": "natural-path-read-only",
            "finding": "The next aligned live gate is the one-run natural-path MDM2AP observation contract, not another forced RC1 or XBL mutation.",
            "basis": f"natural_contract_present={natural_contract}; xbl_has_gpio_token={xbl['has_gpio_token']} xbl_has_pcie_context={xbl['has_pcie_context']}",
            "limit": "If mdm2ap-silent-natural-path repeats, bounded rail/PMIC write remains a separate explicit gate.",
        },
    ]


def classify(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    input_manifest = load_json(args.input)
    xbl = summarize_xbl(input_manifest)
    matrix = reference_matrix()
    reconciliation = build_reconciliation(xbl, matrix)
    checks = {
        "input_exists": args.input.exists(),
        "input_v1655_pass": input_manifest.get("decision") == EXPECTED_INPUT_DECISION and input_manifest.get("pass") is True,
        "reference_files_exist": all(entry["exists"] for entry in matrix),
        "reference_anchors_present": all(entry["all_required_present"] for entry in matrix),
        "xbl_has_sdx_pon_pmic_context": xbl["has_sdx_pon_pmic"],
        "xbl_has_pcie_context": xbl["has_pcie_context"],
        "host_only_no_device_command": True,
        "no_raw_string_output": True,
        "no_wifi_or_power_mutation": True,
    }
    decision = "v1656-xbl-reference-reconciliation-pass" if all(checks.values()) else "v1656-xbl-reference-reconciliation-review"
    result = {
        "cycle": "V1656",
        "type": "host-only XBL/reference reconciliation",
        "decision": decision,
        "pass": all(checks.values()),
        "input": rel(args.input),
        "source_decision": input_manifest.get("decision"),
        "checks": checks,
        "xbl_summary": xbl,
        "reference_matrix": matrix,
        "reconciliation": reconciliation,
        "next": {
            "recommended_cycle": "V1657",
            "type": "bounded live natural-path MDM2AP observation",
            "shape": "reuse existing natural __subsystem_get(esoc0)->mdm_subsys_powerup observer; measure GPIO142 IRQ delta and errfatal IRQ delta; no forced RC1, fake-ONLINE, PMIC/GPIO/GDSC writes, HAL, scan/connect, DHCP/routes, or external ping",
            "mutation": False,
        },
    }
    store.write_json("manifest.json", result)
    return result


def format_counts(counts: dict[str, int]) -> str:
    return ", ".join(f"{key}={value}" for key, value in sorted(counts.items())) or "none"


def render_report(result: dict[str, Any]) -> str:
    lines = [
        "# Native Init V1656 XBL Reference Reconciliation",
        "",
        "## Summary",
        "",
        "- Cycle: `V1656`",
        "- Type: host-only XBL/reference reconciliation",
        f"- Decision: `{result['decision']}`",
        f"- Result: {'PASS' if result['pass'] else 'REVIEW'}",
        f"- Input: `{result['input']}`",
        f"- Source decision: `{result['source_decision']}`",
        "- Device commands: `0`",
        "- Raw string output: `0`",
        "- Power / PCI / Wi-Fi mutation: `0`",
        "",
        "## Checks",
        "",
    ]
    for key, value in result["checks"].items():
        lines.append(f"- `{key}`: `{value}`")

    xbl = result["xbl_summary"]
    lines.extend([
        "",
        "## XBL Signal Summary",
        "",
        f"- Total records: `{xbl['total_records']}`",
        f"- Cross-slot duplicate groups: `{xbl['cross_slot_duplicate_groups']}`",
        f"- Token totals: {format_counts(xbl['token_totals'])}",
        f"- Class totals: {format_counts(xbl['class_totals'])}",
        f"- Has SDX/PON/PMIC context: `{xbl['has_sdx_pon_pmic']}`",
        f"- Has PCIe context: `{xbl['has_pcie_context']}`",
        f"- Has GPIO token: `{xbl['has_gpio_token']}`",
        "",
        "## Reference Matrix",
        "",
        "| key | role | file | anchors |",
        "|---|---|---|---|",
    ])
    for entry in result["reference_matrix"]:
        anchors = ", ".join(f"{key}={value}" for key, value in entry["required_hits"].items())
        lines.append(f"| `{entry['key']}` | {entry['role']} | `{entry['path']}` | {anchors} |")

    lines.extend([
        "",
        "## Reconciliation",
        "",
        "| topic | status | finding | basis | limit |",
        "|---|---|---|---|---|",
    ])
    for item in result["reconciliation"]:
        lines.append(
            f"| `{item['topic']}` | `{item['status']}` | {item['finding']} | {item['basis']} | {item['limit']} |"
        )

    lines.extend([
        "",
        "## Selected Reference Anchors",
        "",
    ])
    for entry in result["reference_matrix"]:
        lines.append(f"### `{entry['key']}`")
        for anchor in entry["anchors"][:8]:
            lines.append(f"- `{entry['path']}:{anchor['line']}` {anchor['text']}")
        if not entry["anchors"]:
            lines.append("- none")

    lines.extend([
        "",
        "## Decision",
        "",
        "V1656 narrows the role of XBL evidence: it is useful owner/context evidence, but not a direct native-vs-Android differential or write target. Existing references still place the active blocker below provider entry and before connect-side Wi-Fi: native lacks the SDX50M MDM2AP/GPIO142 response and downstream RC1 L0/MHI/WLFW/wlan0.",
        "",
        "## Next",
        "",
        "V1657 should return to the bounded natural-path MDM2AP observation contract: one read-only live run using natural `__subsystem_get(esoc0)`/`mdm_subsys_powerup`, with GPIO142 IRQ delta and errfatal IRQ delta as discriminators. Do not use forced RC1 enumerate, fake-ONLINE/system-info spoofing, PMIC/GPIO/GDSC writes, eSoC notify/`BOOT_DONE`, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping.",
        "",
    ])
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT_PATH)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    store = EvidenceStore(args.out_dir)
    result = classify(args, store)
    report = render_report(result)
    write_private_text(args.out_dir / "summary.md", report)
    write_private_text(args.report_path, report)
    print(json.dumps({
        "decision": result["decision"],
        "pass": result["pass"],
        "report": rel(args.report_path),
        "next": result["next"]["recommended_cycle"],
    }, indent=2))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

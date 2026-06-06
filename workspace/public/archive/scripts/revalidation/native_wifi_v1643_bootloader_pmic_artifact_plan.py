#!/usr/bin/env python3
"""V1643 host-only plan for bootloader / PMIC ownership artifact acquisition."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from a90harness.evidence import EvidenceStore, write_private_text

REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
DEFAULT_OUT_DIR = REPO_ROOT / "tmp/wifi/v1643-bootloader-pmic-artifact-plan"
DEFAULT_REPORT_PATH = REPO_ROOT / "docs/reports/NATIVE_INIT_V1643_BOOTLOADER_PMIC_ARTIFACT_ACQUISITION_PLAN_2026-06-02.md"

REQUIRED_REPORTS = [
    REPO_ROOT / "docs/reports/ESOC_NATURAL_PATH_MDM2AP_OBSERVATION_CONTRACT_2026-06-02.md",
    REPO_ROOT / "docs/reports/ESOC_PON_SOURCE_ANALYSIS_2026-06-02.md",
    REPO_ROOT / "docs/reports/ESOC_DTB_PARITY_2026-06-02.md",
    REPO_ROOT / "docs/reports/NATIVE_INIT_V1638_NATURAL_PATH_MDM2AP_IRQ_SUMMARY_HANDOFF_2026-06-02.md",
    REPO_ROOT / "docs/reports/NATIVE_INIT_V1642_SDX_POWER_OWNER_CLASSIFIER_2026-06-02.md",
]

PRIMARY_PARTITIONS = [
    "xbl",
    "xblbak",
    "abl",
    "ablbak",
    "aop",
    "aopbak",
    "devcfg",
    "devcfgbak",
    "tz",
    "tzbak",
    "hyp",
    "hypbak",
    "keymaster",
    "keymasterbak",
    "cmnlib",
    "cmnlibbak",
    "cmnlib64",
    "cmnlib64bak",
    "qupfw",
    "qupfwbak",
]

CONTEXT_PARTITIONS = [
    "modem",
    "NON-HLOS",
    "bluetooth",
    "dsp",
]

SENSITIVE_EXCLUSIONS = [
    "userdata",
    "metadata",
    "persist",
    "efs",
    "modemst1",
    "modemst2",
    "fsg",
    "fsc",
    "keystore",
    "sec_efs",
]

SEARCH_TOKENS = [
    "sdx",
    "sdx50",
    "sdxprairie",
    "pmic",
    "pm8150",
    "pm8150l",
    "pmxprairie",
    "pon",
    "ps_hold",
    "mdm",
    "mhi",
    "pcie",
    "gpio",
    "ap2mdm",
    "mdm2ap",
    "vdd_modem",
]


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def bounded_local_artifact_scan() -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    roots = [REPO_ROOT / "stage3", REPO_ROOT / "tmp/wifi"]
    names = {name.lower() for name in PRIMARY_PARTITIONS + CONTEXT_PARTITIONS}
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
            lower_name = path.name.lower()
            stem_hit = path.stem.lower() in names
            token_hit = any(token in lower_name for token in names)
            suffix_hit = lower_name.endswith(suffixes)
            if not suffix_hit or not (stem_hit or token_hit):
                continue
            hits.append({
                "path": str(relative),
                "size": path.stat().st_size,
                "sha256": sha256(path),
            })
            if len(hits) >= 80:
                return hits
    return sorted(hits, key=lambda item: item["path"])


def classify() -> dict[str, Any]:
    required = {rel(path): path.exists() for path in REQUIRED_REPORTS}
    local_hits = bounded_local_artifact_scan()
    checks = {
        "required_reports_present": all(required.values()),
        "v1638_one_run_handoff_present": REQUIRED_REPORTS[3].exists(),
        "v1642_external_owner_gap_present": REQUIRED_REPORTS[4].exists(),
        "candidate_partition_policy_defined": bool(PRIMARY_PARTITIONS and CONTEXT_PARTITIONS),
        "sensitive_exclusions_defined": bool(SENSITIVE_EXCLUSIONS),
        "metadata_only_report_mode": True,
        "no_binary_commit_policy": True,
        "no_live_write_gate": True,
    }
    decision = (
        "v1643-read-only-bootloader-pmic-artifact-plan-ready"
        if all(checks.values())
        else "v1643-artifact-plan-review"
    )
    return {
        "cycle": "V1643",
        "type": "host-only bootloader / PMIC artifact acquisition plan",
        "decision": decision,
        "pass": all(checks.values()),
        "checks": checks,
        "required_reports": required,
        "primary_partitions": PRIMARY_PARTITIONS,
        "context_partitions": CONTEXT_PARTITIONS,
        "sensitive_exclusions": SENSITIVE_EXCLUSIONS,
        "search_tokens": SEARCH_TOKENS,
        "local_artifact_hits": local_hits,
        "commands": {
            "partition_map": "toybox ls -l /dev/block/by-name 2>&1",
            "metadata_loop": "for p in xbl xblbak abl ablbak aop aopbak devcfg devcfgbak tz tzbak hyp hypbak keymaster keymasterbak cmnlib cmnlibbak cmnlib64 cmnlib64bak qupfw qupfwbak modem NON-HLOS bluetooth dsp; do if [ -e /dev/block/by-name/$p ]; then printf 'PART %s\\n' \"$p\"; toybox ls -l /dev/block/by-name/$p; toybox blockdev --getsize64 /dev/block/by-name/$p 2>&1; toybox sha256sum /dev/block/by-name/$p 2>&1; fi; done",
            "bounded_strings_policy": "strings are optional, token-filtered, capped, and evidence-only; do not commit raw binary dumps",
        },
        "next": {
            "recommended_cycle": "V1644",
            "type": "read-only live partition metadata/hash capture, if selected",
            "mutation": False,
            "requires_binary_commit": False,
        },
    }


def render_report(result: dict[str, Any]) -> str:
    primary = ", ".join(f"`{name}`" for name in result["primary_partitions"])
    context = ", ".join(f"`{name}`" for name in result["context_partitions"])
    exclusions = ", ".join(f"`{name}`" for name in result["sensitive_exclusions"])
    tokens = ", ".join(f"`{name}`" for name in result["search_tokens"])
    lines = [
        "# Native Init V1643 Bootloader / PMIC Artifact Acquisition Plan",
        "",
        "## Summary",
        "",
        "- Cycle: `V1643`",
        "- Type: host-only bootloader / PMIC artifact acquisition plan",
        f"- Decision: `{result['decision']}`",
        f"- Result: {'PASS' if result['pass'] else 'REVIEW'}",
        "- Reason: V1642 leaves the suspected SDX50M main-rail owner outside AP kernel source; the next safe step is read-only artifact metadata, not a live PMIC/GPIO/GDSC write.",
        "",
        "## Inputs",
        "",
    ]
    for path, exists in result["required_reports"].items():
        lines.append(f"- `{path}`: `{exists}`")
    lines.extend([
        "",
        "## Checks",
        "",
    ])
    for key, value in result["checks"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend([
        "",
        "## Acquisition Policy",
        "",
        f"- Primary bootloader / PMIC-control candidates: {primary}.",
        f"- Context-only firmware candidates: {context}. These may explain SDX firmware expectations, but do not justify Wi-Fi HAL or connect work.",
        f"- Sensitive / identity-bearing exclusions: {exclusions}. These are not needed for the SDX50M power-owner question.",
        "- Repository policy: do not commit raw proprietary bootloader, firmware, partition dumps, `.img`, `.bin`, `.mbn`, `.elf`, `.tar`, `.lz4`, or `.md5` artifacts.",
        "- Evidence policy: collect partition name, resolved block path, byte size, SHA256, and bounded token-filtered strings only; store any raw dump outside git under private `tmp/` storage if a later gate explicitly needs it.",
        f"- Token filter for bounded strings: {tokens}.",
        "",
        "## Proposed V1644 Read-only Live Gate",
        "",
        "If selected, V1644 should only read metadata and hashes from existing block devices:",
        "",
        "```sh",
        "toybox ls -l /dev/block/by-name 2>&1",
        "",
        "for p in xbl xblbak abl ablbak aop aopbak devcfg devcfgbak tz tzbak hyp hypbak keymaster keymasterbak cmnlib cmnlibbak cmnlib64 cmnlib64bak qupfw qupfwbak modem NON-HLOS bluetooth dsp; do",
        "  if [ -e /dev/block/by-name/$p ]; then",
        "    printf 'PART %s\\n' \"$p\"",
        "    toybox ls -l /dev/block/by-name/$p",
        "    toybox blockdev --getsize64 /dev/block/by-name/$p 2>&1",
        "    toybox sha256sum /dev/block/by-name/$p 2>&1",
        "  fi",
        "done",
        "```",
        "",
        "The live gate must not dump full partition contents by default. If a later explicit gate needs a private dump, it must write under a private, ignored `tmp/` path with `umask 077`, record SHA256/size in the report, and keep the binary out of git.",
        "",
        "## Current Local Artifact Scan",
        "",
        f"- Bounded local bootloader / PMIC artifact hits: `{len(result['local_artifact_hits'])}`",
    ])
    if result["local_artifact_hits"]:
        lines.extend(["", "| path | size | sha256 |", "|---|---:|---|"])
        for item in result["local_artifact_hits"]:
            lines.append(f"| `{item['path']}` | {item['size']} | `{item['sha256']}` |")
    lines.extend([
        "",
        "## Interpretation",
        "",
        "V1638 already performed the one natural-path observation run and later V1642 found no AP-native safe write target. Re-running natural-path timing variants or jumping to PMIC/GPIO/GDSC mutation would violate the current stop condition. The only defensible next move is to close the missing artifact gap with read-only partition metadata and, if necessary, private non-git dumps for offline analysis.",
        "",
        "## Hard Stops",
        "",
        "No forced RC1 enumerate, pci-msm case write, fake ONLINE/system-info spoof, PMIC/GPIO/GDSC/regulator write, eSoC notify/`BOOT_DONE`, PCI rescan, platform bind/unbind, Wi-Fi HAL start, scan/connect, credentials, DHCP/routes, external ping, boot image write, or partition write is part of V1643.",
        "",
        "## Next",
        "",
        "V1644 may be a read-only live partition metadata/hash capture if the device is available. It should produce a private evidence bundle and a report that either identifies a concrete bootloader/PMIC owner artifact for offline analysis or explicitly hands off the remaining evidence gap.",
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

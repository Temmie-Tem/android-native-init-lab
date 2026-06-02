#!/usr/bin/env python3
"""V1652 host-only contract for bounded private XBL context extraction."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from a90harness.evidence import EvidenceStore, write_private_text

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT_REPORT = REPO_ROOT / "docs/reports/NATIVE_INIT_V1651_XBL_TOKEN_CLUSTER_CONTEXT_2026-06-02.md"
DEFAULT_OUT_DIR = REPO_ROOT / "tmp/wifi/v1652-xbl-private-context-contract"
DEFAULT_REPORT_PATH = REPO_ROOT / "docs/reports/NATIVE_INIT_V1652_XBL_PRIVATE_CONTEXT_CONTRACT_2026-06-02.md"

TARGET_CLUSTERS = [
    {
        "artifact": "xbl_a",
        "range": "3340797..3377867",
        "label": "rpmh-aop-pmic-context",
        "reason": "strongest RPMh/AOP/PMIC/PON/VDD cluster",
    },
    {
        "artifact": "xbl_b",
        "range": "3355345..3400091",
        "label": "rpmh-aop-pmic-context",
        "reason": "matching high-value cluster in alternate XBL slot",
    },
    {
        "artifact": "xbl_a",
        "range": "20034..29600",
        "label": "pon-pshold-pmic-context",
        "reason": "early PON/PS_HOLD/PMIC/VDD/SDX cluster",
    },
    {
        "artifact": "xbl_b",
        "range": "20027..30662",
        "label": "pon-pshold-pmic-context",
        "reason": "early PON/PS_HOLD/PMIC/VDD/SDX cluster in alternate slot",
    },
]

OUTPUT_ALLOWLIST = [
    "artifact label",
    "range start/end",
    "string offset",
    "string length",
    "sha256 of full private string",
    "matched token list",
    "redacted token-neighborhood class",
]

OUTPUT_FORBIDDEN = [
    "raw string text in tracked report",
    "raw binary bytes",
    "full strings output",
    "partition dump",
    "SSID or passphrase",
    "PMIC/GPIO/GDSC writes",
    "eSoC notify/BOOT_DONE",
    "PCI rescan",
    "Wi-Fi HAL or scan/connect",
]


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def classify(input_report: Path) -> dict[str, Any]:
    text = input_report.read_text(encoding="utf-8", errors="replace")
    checks = {
        "v1651_report_present": input_report.exists(),
        "v1651_pass_recorded": "Decision: `v1651-xbl-cluster-context-ready`" in text,
        "target_clusters_defined": len(TARGET_CLUSTERS) == 4,
        "output_allowlist_defined": bool(OUTPUT_ALLOWLIST),
        "output_forbidden_defined": bool(OUTPUT_FORBIDDEN),
        "no_device_command": True,
        "no_live_write_gate": True,
    }
    decision = "v1652-xbl-private-context-contract-ready" if all(checks.values()) else "v1652-xbl-private-context-contract-review"
    return {
        "cycle": "V1652",
        "type": "host-only private XBL context extraction contract",
        "decision": decision,
        "pass": all(checks.values()),
        "input_report": rel(input_report),
        "checks": checks,
        "target_clusters": TARGET_CLUSTERS,
        "output_allowlist": OUTPUT_ALLOWLIST,
        "output_forbidden": OUTPUT_FORBIDDEN,
        "helper_contract": {
            "recommended_cycle": "V1653",
            "name": "a90_xbl_context_probe",
            "type": "source/build-only static helper",
            "inputs": "temporary private block devnode path, artifact label, bounded ranges, token regex",
            "behavior": "read only the specified byte ranges; identify printable strings intersecting ranges; write raw string text only to ignored private evidence if explicitly requested; tracked report receives hashes/redacted classes only",
            "tracked_output": "offset, length, sha256, tokens, redacted class, source range",
            "live_mutation": "none for V1653; later live gate may create temporary devnodes exactly like V1647 and remove them",
        },
    }


def render_report(result: dict[str, Any]) -> str:
    lines = [
        "# Native Init V1652 XBL Private Context Contract",
        "",
        "## Summary",
        "",
        "- Cycle: `V1652`",
        "- Type: host-only private XBL context extraction contract",
        f"- Decision: `{result['decision']}`",
        f"- Result: {'PASS' if result['pass'] else 'REVIEW'}",
        f"- Input: `{result['input_report']}`",
        "- Reason: define a safe bounded extraction contract before reading any XBL string context.",
        "",
        "## Checks",
        "",
    ]
    for key, value in result["checks"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend([
        "",
        "## Target Clusters",
        "",
        "| artifact | range | label | reason |",
        "|---|---|---|---|",
    ])
    for cluster in result["target_clusters"]:
        lines.append(f"| `{cluster['artifact']}` | `{cluster['range']}` | `{cluster['label']}` | {cluster['reason']} |")
    lines.extend([
        "",
        "## Output Contract",
        "",
        "Tracked reports may include only:",
    ])
    for item in result["output_allowlist"]:
        lines.append(f"- {item}")
    lines.extend(["", "Tracked reports and git must not include:"])
    for item in result["output_forbidden"]:
        lines.append(f"- {item}")
    lines.extend([
        "",
        "## Helper Contract",
        "",
        "- Next cycle: `V1653` source/build-only static helper.",
        "- Helper name: `a90_xbl_context_probe`.",
        "- Input: temporary private block devnode path, artifact label, bounded ranges, and token regex.",
        "- Behavior: read only specified byte ranges and identify printable strings intersecting those ranges.",
        "- Tracked output: offset, length, SHA256 of the private string, matched token list, redacted class, and source range.",
        "- Private output: raw string text may exist only under ignored private evidence if a later gate explicitly needs it.",
        "",
        "## Hard Stops",
        "",
        "No raw strings in tracked files, no raw binary dump, no partition write, no PMIC/GPIO/GDSC write, no eSoC notify/`BOOT_DONE`, no PCI rescan, no Wi-Fi HAL, no scan/connect, no credentials, no DHCP/routes, and no external ping.",
        "",
    ])
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-report", type=Path, default=DEFAULT_INPUT_REPORT)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT_PATH)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    store = EvidenceStore(args.out_dir)
    result = classify(args.input_report)
    store.write_json("manifest.json", result)
    report = render_report(result)
    write_private_text(args.out_dir / "summary.md", report)
    write_private_text(args.report_path, report)
    print(json.dumps({
        "decision": result["decision"],
        "pass": result["pass"],
        "report": rel(args.report_path),
    }, indent=2))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""V1648 host-only interpretation of V1647 hashes and bounded token-scan plan."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from a90harness.evidence import EvidenceStore, write_private_text

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT_REPORT = REPO_ROOT / "docs/reports/NATIVE_INIT_V1647_PRIVATE_DEVNODE_HASH_GATE_2026-06-02.md"
DEFAULT_OUT_DIR = REPO_ROOT / "tmp/wifi/v1648-hash-interpretation-token-scan-plan"
DEFAULT_REPORT_PATH = REPO_ROOT / "docs/reports/NATIVE_INIT_V1648_HASH_INTERPRETATION_TOKEN_SCAN_PLAN_2026-06-02.md"

TOKENS = [
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
    "mdm2ap",
    "ap2mdm",
    "vdd",
    "rpmh",
    "aop",
    "gpio",
    "pcie",
    "mhi",
]


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def parse_hash_rows(text: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for line in text.splitlines():
        if not line.startswith("| `"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != 7:
            continue
        label = cells[0].strip("`")
        if label == "label":
            continue
        rows.append({
            "label": label,
            "name": cells[1].strip("`"),
            "devname": cells[2].strip("`"),
            "major_minor": cells[3].strip("`"),
            "size": cells[4],
            "sha256": cells[5].strip("`"),
            "cleanup": cells[6].strip("`"),
        })
    return rows


def classify(report_path: Path) -> dict[str, Any]:
    text = report_path.read_text(encoding="utf-8", errors="replace")
    rows = parse_hash_rows(text)
    sha_to_labels: dict[str, list[str]] = {}
    for row in rows:
        sha_to_labels.setdefault(row["sha256"], []).append(row["label"])
    duplicate_groups = {sha: labels for sha, labels in sha_to_labels.items() if sha and len(labels) > 1}
    xbl_hashes = {row["sha256"] for row in rows if row["name"] == "xbl"}
    checks = {
        "v1647_report_present": report_path.exists(),
        "v1647_pass_recorded": "Decision: `v1647-private-devnode-sha256-captured`" in text,
        "hash_row_count_five": len(rows) == 5,
        "all_hashes_present": all(re.fullmatch(r"[0-9a-f]{64}", row["sha256"]) for row in rows),
        "xbl_copies_are_distinct": len(xbl_hashes) == 2,
        "no_device_command": True,
        "no_live_write_gate": True,
    }
    decision = "v1648-bounded-token-scan-plan-ready" if all(checks.values()) else "v1648-hash-interpretation-review"
    return {
        "cycle": "V1648",
        "type": "host-only hash interpretation and bounded token-scan plan",
        "decision": decision,
        "pass": all(checks.values()),
        "checks": checks,
        "input_report": rel(report_path),
        "rows": rows,
        "duplicate_groups": duplicate_groups,
        "token_regex": "|".join(TOKENS),
        "tokens": TOKENS,
        "next": {
            "recommended_cycle": "V1649",
            "type": "bounded token-only grep gate",
            "shape": "temporary private devnodes, grep -a -i -b -o -m 200 -E token_regex, cleanup, report only offset:token matches",
            "no_raw_strings": True,
            "no_raw_binary": True,
        },
    }


def render_report(result: dict[str, Any]) -> str:
    lines = [
        "# Native Init V1648 Hash Interpretation / Token Scan Plan",
        "",
        "## Summary",
        "",
        "- Cycle: `V1648`",
        "- Type: host-only hash interpretation and bounded token-scan plan",
        f"- Decision: `{result['decision']}`",
        f"- Result: {'PASS' if result['pass'] else 'REVIEW'}",
        f"- Input: `{result['input_report']}`",
        "- Reason: interpret V1647 hashes and define the next live content-read gate without dumping raw proprietary strings or binaries.",
        "",
        "## Checks",
        "",
    ]
    for key, value in result["checks"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend([
        "",
        "## Hash Interpretation",
        "",
        "| label | name | devname | size | sha256 |",
        "|---|---|---|---:|---|",
    ])
    for row in result["rows"]:
        lines.append(f"| `{row['label']}` | `{row['name']}` | `{row['devname']}` | {row['size']} | `{row['sha256']}` |")
    lines.extend([
        "",
        "Duplicate hash groups: " + ("none" if not result["duplicate_groups"] else json.dumps(result["duplicate_groups"], sort_keys=True)),
        "",
        "The two `xbl` slots are distinct. Treat them as separate copies or versions until an external artifact comparison proves which slot is active for this boot chain.",
        "",
        "## Proposed V1649 Token-only Gate",
        "",
        "Use temporary private devnodes exactly as in V1647, but run bounded match-only grep instead of dumping strings:",
        "",
        "```sh",
        "toybox grep -a -i -b -o -m 200 -E 'sdx|sdx50|sdxprairie|pmic|pm8150|pm8150l|pmxprairie|pon|ps_hold|mdm|mdm2ap|ap2mdm|vdd|rpmh|aop|gpio|pcie|mhi' <temporary-node>",
        "```",
        "",
        "This emits only `offset:matched-token`, not full strings or raw binary lines. The goal is to identify which artifact contains SDX/PMIC/PON vocabulary before deciding whether any private offline string extraction is justified.",
        "",
        "## Hard Stops",
        "",
        "No raw partition dump, no full `strings` output, no proprietary binary commit, no partition write, no PMIC/GPIO/GDSC write, no eSoC notify/`BOOT_DONE`, no PCI rescan, no Wi-Fi HAL, no scan/connect, no credentials, no DHCP/routes, and no external ping.",
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

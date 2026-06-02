#!/usr/bin/env python3
"""V1650 host-only interpretation of V1649 token scan evidence."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from a90harness.evidence import EvidenceStore, write_private_text

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT_REPORT = REPO_ROOT / "docs/reports/NATIVE_INIT_V1649_BOUNDED_TOKEN_SCAN_GATE_2026-06-02.md"
DEFAULT_OUT_DIR = REPO_ROOT / "tmp/wifi/v1650-token-owner-hypothesis"
DEFAULT_REPORT_PATH = REPO_ROOT / "docs/reports/NATIVE_INIT_V1650_TOKEN_OWNER_HYPOTHESIS_2026-06-02.md"

POWER_TOKENS = {"pmic", "vdd", "pon", "ps_hold", "rpmh", "aop", "gpio"}
SDX_TOKENS = {"sdx", "sdx50", "sdxprairie", "mdm", "mdm2ap", "ap2mdm", "mhi", "pcie"}


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def parse_summary_rows(text: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    in_table = False
    for line in text.splitlines():
        if line.startswith("| label | name | match count | token counts |"):
            in_table = True
            continue
        if not in_table:
            continue
        if line.startswith("|---"):
            continue
        if not line.startswith("| `"):
            break
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != 4:
            continue
        label = cells[0].strip("`")
        name = cells[1].strip("`")
        match_count = int(cells[2])
        token_counts: dict[str, int] = {}
        if cells[3] != "none":
            for item in cells[3].split(","):
                if "=" not in item:
                    continue
                token, count = item.strip().split("=", 1)
                token_counts[token] = int(count)
        rows.append({
            "label": label,
            "name": name,
            "match_count": match_count,
            "token_counts": token_counts,
        })
    return rows


def score(row: dict[str, Any]) -> dict[str, Any]:
    counts = row["token_counts"]
    power_score = sum(counts.get(token, 0) for token in POWER_TOKENS)
    sdx_score = sum(counts.get(token, 0) for token in SDX_TOKENS)
    specific_score = (
        counts.get("pon", 0) * 4
        + counts.get("ps_hold", 0) * 8
        + counts.get("pmic", 0) * 2
        + counts.get("vdd", 0) * 2
        + counts.get("rpmh", 0) * 2
        + counts.get("sdx", 0) * 5
        + counts.get("mdm", 0) * 2
        + counts.get("pcie", 0)
    )
    return {
        **row,
        "power_score": power_score,
        "sdx_score": sdx_score,
        "specific_score": specific_score,
    }


def classify(report_path: Path) -> dict[str, Any]:
    text = report_path.read_text(encoding="utf-8", errors="replace")
    rows = [score(row) for row in parse_summary_rows(text)]
    ranked = sorted(rows, key=lambda item: (item["specific_score"], item["power_score"], item["sdx_score"]), reverse=True)
    xbl_rows = [row for row in ranked if row["name"] == "xbl"]
    secondary_rows = [row for row in ranked if row["name"] in {"aop", "devcfg"}]
    checks = {
        "v1649_report_present": report_path.exists(),
        "v1649_pass_recorded": "Decision: `v1649-bounded-token-scan-captured`" in text,
        "summary_rows_present": len(rows) == 5,
        "xbl_rows_dominate": len(xbl_rows) == 2 and all(row["specific_score"] > 100 for row in xbl_rows),
        "secondary_context_present": len(secondary_rows) == 2,
        "no_device_command": True,
        "no_live_write_gate": True,
    }
    decision = "v1650-xbl-first-private-analysis-hypothesis" if all(checks.values()) else "v1650-token-owner-hypothesis-review"
    return {
        "cycle": "V1650",
        "type": "host-only token owner hypothesis",
        "decision": decision,
        "pass": all(checks.values()),
        "input_report": rel(report_path),
        "checks": checks,
        "ranked": ranked,
        "hypothesis": {
            "primary": "xbl_a/xbl_b",
            "secondary": "aop/devcfg",
            "defer": "abl",
            "reason": "XBL artifacts contain dense PMIC/VDD/PON/PS_HOLD/RPMh/SDX/PCIe vocabulary; AOP/devcfg contain weaker but relevant context; ABL is too sparse for this blocker.",
        },
        "next": {
            "recommended_cycle": "V1651",
            "type": "private offline XBL string-context extraction plan",
            "shape": "do not dump to git; extract only bounded context around already observed offsets under ignored private evidence, then commit only summary",
            "mutation": False,
        },
    }


def render_report(result: dict[str, Any]) -> str:
    lines = [
        "# Native Init V1650 Token Owner Hypothesis",
        "",
        "## Summary",
        "",
        "- Cycle: `V1650`",
        "- Type: host-only token owner hypothesis",
        f"- Decision: `{result['decision']}`",
        f"- Result: {'PASS' if result['pass'] else 'REVIEW'}",
        f"- Input: `{result['input_report']}`",
        "- Reason: convert V1649 token-only evidence into an artifact-analysis priority without running another live gate.",
        "",
        "## Checks",
        "",
    ]
    for key, value in result["checks"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend([
        "",
        "## Ranked Artifacts",
        "",
        "| rank | label | name | matches | power score | sdx score | specific score |",
        "|---:|---|---|---:|---:|---:|---:|",
    ])
    for index, row in enumerate(result["ranked"], start=1):
        lines.append(
            f"| {index} | `{row['label']}` | `{row['name']}` | {row['match_count']} | "
            f"{row['power_score']} | {row['sdx_score']} | {row['specific_score']} |"
        )
    lines.extend([
        "",
        "## Hypothesis",
        "",
        "- Primary target: `xbl_a` / `xbl_b`.",
        "- Secondary context: `aop` / `devcfg`.",
        "- Defer: `abl` for this blocker.",
        "",
        result["hypothesis"]["reason"],
        "",
        "This does not prove a concrete PMIC write target. It only narrows the next private offline analysis target to the XBL artifacts. PMIC/GPIO/GDSC mutation remains unjustified.",
        "",
        "## Next",
        "",
        "V1651 should be a host-only/private-evidence plan for bounded XBL string-context extraction around offsets already observed in V1649. Raw proprietary content must remain under ignored private storage; tracked output should summarize only non-sensitive token contexts and hypotheses. No Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, partition write, PMIC/GPIO/GDSC write, eSoC notify/`BOOT_DONE`, or PCI rescan.",
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

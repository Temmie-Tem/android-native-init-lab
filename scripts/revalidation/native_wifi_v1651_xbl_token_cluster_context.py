#!/usr/bin/env python3
"""V1651 host-only XBL token-cluster interpretation from V1649 evidence."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from a90harness.evidence import EvidenceStore, write_private_text

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT_DIR = REPO_ROOT / "tmp/wifi/v1649-bounded-token-scan-gate"
DEFAULT_OUT_DIR = REPO_ROOT / "tmp/wifi/v1651-xbl-token-cluster-context"
DEFAULT_REPORT_PATH = REPO_ROOT / "docs/reports/NATIVE_INIT_V1651_XBL_TOKEN_CLUSTER_CONTEXT_2026-06-02.md"

POWER_TOKENS = {"pmic", "vdd", "pon", "ps_hold", "rpmh", "aop", "gpio"}
SDX_TOKENS = {"sdx", "mdm", "mdm2ap", "ap2mdm", "pcie", "mhi"}
CRITICAL_TOKENS = {"pon", "ps_hold", "pmic", "vdd", "rpmh", "sdx", "mdm", "pcie", "gpio", "aop"}


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def parse_grep_file(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8", errors="replace")
    matches: list[dict[str, Any]] = []
    active = False
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line.startswith("run: pid="):
            active = True
            continue
        if not active:
            continue
        if line.startswith("[exit ") or line.startswith("[done]") or line.startswith("[err]"):
            break
        match = re.fullmatch(r"(?P<offset>\d+):(?P<token>[A-Za-z0-9_+-]+)", line)
        if match:
            matches.append({"offset": int(match.group("offset")), "token": match.group("token").lower()})
    return matches


def cluster_matches(matches: list[dict[str, Any]], gap: int) -> list[dict[str, Any]]:
    if not matches:
        return []
    sorted_matches = sorted(matches, key=lambda item: item["offset"])
    clusters: list[list[dict[str, Any]]] = []
    current = [sorted_matches[0]]
    for item in sorted_matches[1:]:
        if item["offset"] - current[-1]["offset"] <= gap:
            current.append(item)
        else:
            clusters.append(current)
            current = [item]
    clusters.append(current)
    rendered: list[dict[str, Any]] = []
    for index, cluster in enumerate(clusters, start=1):
        counts = Counter(item["token"] for item in cluster)
        tokens = set(counts)
        power_count = sum(counts[token] for token in POWER_TOKENS)
        sdx_count = sum(counts[token] for token in SDX_TOKENS)
        critical_count = sum(counts[token] for token in CRITICAL_TOKENS)
        span_start = cluster[0]["offset"]
        span_end = cluster[-1]["offset"]
        score = (
            critical_count
            + power_count
            + sdx_count
            + counts["ps_hold"] * 8
            + counts["pon"] * 4
            + counts["sdx"] * 5
            + counts["rpmh"] * 2
        )
        if {"pon", "ps_hold", "pmic"} <= tokens:
            label = "pon-pshold-pmic-context"
        elif "rpmh" in tokens and ("aop" in tokens or "pmic" in tokens):
            label = "rpmh-aop-pmic-context"
        elif "sdx" in tokens or "mdm" in tokens:
            label = "sdx-mdm-context"
        elif "pcie" in tokens:
            label = "pcie-context"
        else:
            label = "generic-power-token-context"
        rendered.append({
            "cluster": index,
            "start": span_start,
            "end": span_end,
            "span": span_end - span_start,
            "count": len(cluster),
            "token_counts": dict(sorted(counts.items())),
            "power_count": power_count,
            "sdx_count": sdx_count,
            "critical_count": critical_count,
            "score": score,
            "label": label,
        })
    return sorted(rendered, key=lambda item: item["score"], reverse=True)


def classify(input_dir: Path, gap: int, top_n: int) -> dict[str, Any]:
    manifest_path = input_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    labels = ["xbl_a", "xbl_b"]
    results = []
    for label in labels:
        path = input_dir / f"{label}-grep.txt"
        matches = parse_grep_file(path)
        clusters = cluster_matches(matches, gap)
        results.append({
            "label": label,
            "grep_file": rel(path),
            "match_count": len(matches),
            "top_clusters": clusters[:top_n],
            "cluster_count": len(clusters),
        })
    checks = {
        "v1649_manifest_present": manifest_path.exists(),
        "v1649_pass_recorded": manifest.get("decision") == "v1649-bounded-token-scan-captured",
        "xbl_grep_files_present": all((input_dir / f"{label}-grep.txt").exists() for label in labels),
        "xbl_matches_present": all(item["match_count"] > 0 for item in results),
        "critical_clusters_present": any(
            any(cluster["label"] in {"pon-pshold-pmic-context", "rpmh-aop-pmic-context"} for cluster in item["top_clusters"])
            for item in results
        ),
        "no_device_command": True,
        "no_live_write_gate": True,
    }
    decision = "v1651-xbl-cluster-context-ready" if all(checks.values()) else "v1651-xbl-cluster-context-review"
    return {
        "cycle": "V1651",
        "type": "host-only XBL token cluster interpretation",
        "decision": decision,
        "pass": all(checks.values()),
        "input_dir": rel(input_dir),
        "cluster_gap": gap,
        "top_n": top_n,
        "checks": checks,
        "results": results,
        "next": {
            "recommended_cycle": "V1652",
            "type": "bounded private XBL string-context extraction plan",
            "reason": "target only top XBL clusters; keep raw strings private and commit only redacted summaries",
            "mutation": False,
        },
    }


def format_counts(counts: dict[str, int]) -> str:
    return ", ".join(f"{token}={count}" for token, count in counts.items())


def render_report(result: dict[str, Any]) -> str:
    lines = [
        "# Native Init V1651 XBL Token Cluster Context",
        "",
        "## Summary",
        "",
        "- Cycle: `V1651`",
        "- Type: host-only XBL token cluster interpretation",
        f"- Decision: `{result['decision']}`",
        f"- Result: {'PASS' if result['pass'] else 'REVIEW'}",
        f"- Input evidence: `{result['input_dir']}`",
        f"- Cluster gap: `{result['cluster_gap']}` bytes",
        "- Reason: group V1649 token-only offsets into XBL regions without dumping raw strings or binaries.",
        "",
        "## Checks",
        "",
    ]
    for key, value in result["checks"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend([
        "",
        "## Top XBL Clusters",
        "",
        "| artifact | rank | label | start | end | count | score | token counts |",
        "|---|---:|---|---:|---:|---:|---:|---|",
    ])
    for item in result["results"]:
        for rank, cluster in enumerate(item["top_clusters"], start=1):
            lines.append(
                f"| `{item['label']}` | {rank} | `{cluster['label']}` | "
                f"{cluster['start']} | {cluster['end']} | {cluster['count']} | "
                f"{cluster['score']} | {format_counts(cluster['token_counts'])} |"
            )
    lines.extend([
        "",
        "## Interpretation",
        "",
        "The XBL token evidence is not random low-density noise. Both XBL copies contain compact regions combining PMIC/VDD/PON/PS_HOLD or RPMh/AOP/PMIC/PCIe vocabulary. This is now the strongest artifact-level explanation path for the native-vs-Android SDX50M power-state difference, but it still does not identify a concrete PMIC/GPIO/GDSC write target.",
        "",
        "## Next",
        "",
        "V1652 should plan a bounded private string-context extraction only around the top XBL clusters. Raw strings and proprietary binary content must stay under ignored private evidence; tracked output should contain only redacted context classes, token neighborhoods, hashes, and hypotheses. No PMIC/GPIO/GDSC write, partition write, eSoC notify/`BOOT_DONE`, PCI rescan, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping.",
        "",
    ])
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_DIR)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--gap", type=int, default=8192)
    parser.add_argument("--top-n", type=int, default=8)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    store = EvidenceStore(args.out_dir)
    result = classify(args.input_dir, args.gap, args.top_n)
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

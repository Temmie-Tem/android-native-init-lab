#!/usr/bin/env python3
"""Summarize Codex Cloud security scan CSV against local finding docs."""

from __future__ import annotations

import argparse
import csv
import json
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90harness.evidence import EvidenceStore


DEFAULT_CSV = Path("docs/security/scans/codex-security-findings-2026-05-11T07-54-55.648Z.csv")
DEFAULT_INDEX = Path("docs/security/findings/README.md")


@dataclass
class CsvFinding:
    title: str
    severity: str
    status: str
    url: str
    commit_hash: str
    relevant_paths: str


@dataclass
class IndexedFinding:
    finding_id: str
    severity: str
    status: str
    title: str
    file: str
    relevant_paths: str


def timestamp() -> str:
    return time.strftime("%Y%m%d-%H%M%S")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create a security scan follow-up summary.")
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--index", type=Path, default=DEFAULT_INDEX)
    parser.add_argument("--run-dir", type=Path,
                        default=Path("tmp") / f"security-followup-v196-{timestamp()}")
    parser.add_argument("--require-indexed", action="store_true",
                        help="fail if any CSV title is not present in the local findings index")
    return parser


def strip_ticks(value: str) -> str:
    value = value.strip()
    if value.startswith("`") and value.endswith("`"):
        return value[1:-1]
    return value


def load_csv(path: Path) -> list[CsvFinding]:
    with path.open("r", encoding="utf-8", newline="") as file_obj:
        reader = csv.DictReader(file_obj)
        findings: list[CsvFinding] = []
        for row in reader:
            findings.append(
                CsvFinding(
                    title=row.get("title", "").strip(),
                    severity=row.get("severity", "").strip(),
                    status=row.get("status", "").strip(),
                    url=row.get("finding_url", "").strip(),
                    commit_hash=row.get("commit_hash", "").strip(),
                    relevant_paths=row.get("relevant_paths", "").strip(),
                )
            )
    return findings


def load_index(path: Path) -> dict[str, IndexedFinding]:
    table_re = re.compile(
        r"^\| (?P<id>F\d{3}) \| `(?P<severity>[^`]+)` \| `(?P<status>[^`]+)` "
        r"\| (?P<title>.*?) \| (?P<file>.*?) \| (?P<paths>.*?) \|$"
    )
    findings: dict[str, IndexedFinding] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        match = table_re.match(line)
        if not match:
            continue
        title = match.group("title").strip()
        findings[title] = IndexedFinding(
            finding_id=match.group("id"),
            severity=match.group("severity"),
            status=match.group("status"),
            title=title,
            file=match.group("file").strip(),
            relevant_paths=match.group("paths").strip(),
        )
    return findings


def severity_rank(severity: str) -> int:
    return {
        "critical": 0,
        "high": 1,
        "medium": 2,
        "low": 3,
        "informational": 4,
    }.get(severity.lower(), 9)


def build_summary(csv_findings: list[CsvFinding],
                  indexed: dict[str, IndexedFinding]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for finding in sorted(csv_findings, key=lambda item: (severity_rank(item.severity), item.title)):
        index_entry = indexed.get(finding.title)
        rows.append(
            {
                "title": finding.title,
                "csv_severity": finding.severity,
                "csv_status": finding.status,
                "indexed": index_entry is not None,
                "finding_id": index_entry.finding_id if index_entry else None,
                "local_status": index_entry.status if index_entry else None,
                "local_file": index_entry.file if index_entry else None,
                "url": finding.url,
                "commit_hash": finding.commit_hash,
                "relevant_paths": finding.relevant_paths,
            }
        )
    status_counts: dict[str, int] = {}
    for row in rows:
        status = str(row["local_status"] or "unindexed")
        status_counts[status] = status_counts.get(status, 0) + 1
    return {
        "csv_count": len(csv_findings),
        "indexed_count": sum(1 for row in rows if row["indexed"]),
        "unindexed_count": sum(1 for row in rows if not row["indexed"]),
        "local_status_counts": dict(sorted(status_counts.items())),
        "rows": rows,
    }


def render_markdown(summary: dict[str, Any], csv_path: Path, index_path: Path) -> str:
    pass_ok = summary["unindexed_count"] == 0
    lines = [
        "# Security Scan Follow-up Summary\n\n",
        f"- result: `{'PASS' if pass_ok else 'FAIL'}`\n",
        f"- csv: `{csv_path}`\n",
        f"- index: `{index_path}`\n",
        f"- csv_count: `{summary['csv_count']}`\n",
        f"- indexed_count: `{summary['indexed_count']}`\n",
        f"- unindexed_count: `{summary['unindexed_count']}`\n\n",
        "## Local Status Counts\n\n",
    ]
    for status, count in summary["local_status_counts"].items():
        lines.append(f"- `{status}`: `{count}`\n")
    lines.append("\n## Findings\n\n")
    lines.append("| severity | csv status | local id | local status | title |\n")
    lines.append("|---|---|---|---|---|\n")
    for row in summary["rows"]:
        lines.append(
            f"| `{row['csv_severity']}` | `{row['csv_status']}` | "
            f"`{row['finding_id'] or '-'}` | `{row['local_status'] or 'unindexed'}` | "
            f"{row['title']} |\n"
        )
    return "".join(lines)


def main() -> int:
    args = build_parser().parse_args()
    store = EvidenceStore(args.run_dir)
    csv_findings = load_csv(args.csv)
    indexed = load_index(args.index)
    summary = build_summary(csv_findings, indexed)
    store.write_json("security-scan-followup-summary.json", summary)
    store.write_text("security-scan-followup-report.md", render_markdown(summary, args.csv, args.index))
    pass_ok = summary["unindexed_count"] == 0
    print(
        f"{'PASS' if pass_ok else 'FAIL'} run_dir={args.run_dir} "
        f"csv={summary['csv_count']} indexed={summary['indexed_count']} "
        f"unindexed={summary['unindexed_count']}"
    )
    if args.require_indexed and not pass_ok:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

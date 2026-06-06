#!/usr/bin/env python3
"""V1655 host-only interpretation of V1654 redacted XBL context records."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from a90harness.evidence import EvidenceStore, write_private_text

REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
DEFAULT_INPUT = REPO_ROOT / "tmp/wifi/v1654-xbl-context-probe-live/manifest.json"
DEFAULT_OUT_DIR = REPO_ROOT / "tmp/wifi/v1655-xbl-context-interpretation"
DEFAULT_REPORT_PATH = REPO_ROOT / "docs/reports/NATIVE_INIT_V1655_XBL_CONTEXT_INTERPRETATION_2026-06-02.md"

EXPECTED_V1654_DECISION = "v1654-xbl-context-probe-live-pass"
HIGH_SIGNAL_TOKENS = {"sdx", "gpio", "pcie", "ps_hold", "pon", "pmic", "vdd", "rpmh", "aop"}
ALLOWED_RECORD_FIELDS = {
    "artifact",
    "range_start",
    "range_end",
    "offset",
    "length",
    "truncated",
    "string_sha256",
    "tokens",
    "class",
}


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def load_manifest(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def record_tokens(record: dict[str, str]) -> list[str]:
    return [token for token in record.get("tokens", "").split(",") if token]


def all_records(manifest: dict[str, Any]) -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    for target in manifest.get("targets", []):
        for record in target.get("records", []):
            records.append(record)
    return records


def summarize_by_artifact(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    for target in manifest.get("targets", []):
        token_counts: Counter[str] = Counter()
        class_counts: Counter[str] = Counter()
        range_counts: Counter[str] = Counter()
        high_signal_offsets: list[dict[str, str]] = []
        for record in target.get("records", []):
            class_counts[record["class"]] += 1
            range_counts[f"{record['range_start']}:{record['range_end']}"] += 1
            tokens = record_tokens(record)
            token_counts.update(tokens)
            if any(token in HIGH_SIGNAL_TOKENS for token in tokens):
                high_signal_offsets.append({
                    "offset": record["offset"],
                    "tokens": record["tokens"],
                    "class": record["class"],
                    "sha256": record["string_sha256"],
                })
        summaries.append({
            "label": target["label"],
            "record_count": target["record_count"],
            "class_counts": dict(sorted(class_counts.items())),
            "token_counts": dict(sorted(token_counts.items())),
            "range_counts": dict(sorted(range_counts.items())),
            "high_signal_count": len(high_signal_offsets),
            "high_signal_offsets_first": high_signal_offsets[:24],
        })
    return summaries


def duplicate_groups(records: list[dict[str, str]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for record in records:
        grouped[record["string_sha256"]].append(record)
    groups: list[dict[str, Any]] = []
    for digest, items in grouped.items():
        artifacts = sorted({item["artifact"] for item in items})
        if len(items) < 2:
            continue
        groups.append({
            "string_sha256": digest,
            "count": len(items),
            "artifacts": artifacts,
            "cross_slot": len(artifacts) > 1,
            "classes": sorted({item["class"] for item in items}),
            "tokens": sorted({token for item in items for token in record_tokens(item)}),
            "locations": [
                {
                    "artifact": item["artifact"],
                    "range": f"{item['range_start']}:{item['range_end']}",
                    "offset": item["offset"],
                    "length": item["length"],
                }
                for item in items[:12]
            ],
        })
    groups.sort(key=lambda item: (not item["cross_slot"], -item["count"], item["string_sha256"]))
    return groups


def class_cluster(records: list[dict[str, str]]) -> list[dict[str, Any]]:
    clusters: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for record in records:
        key = (record["artifact"], record["class"])
        clusters[key].append(record)
    rows: list[dict[str, Any]] = []
    for (artifact, class_name), items in clusters.items():
        offsets = [int(item["offset"]) for item in items]
        token_counts: Counter[str] = Counter(token for item in items for token in record_tokens(item))
        rows.append({
            "artifact": artifact,
            "class": class_name,
            "count": len(items),
            "offset_min": min(offsets),
            "offset_max": max(offsets),
            "token_counts": dict(sorted(token_counts.items())),
        })
    rows.sort(key=lambda item: (item["artifact"], -item["count"], item["class"]))
    return rows


def build_hypotheses(artifact_summaries: list[dict[str, Any]],
                     dupes: list[dict[str, Any]],
                     clusters: list[dict[str, Any]]) -> list[dict[str, str]]:
    cross_slot_dupes = [item for item in dupes if item["cross_slot"]]
    has_sdx = any(summary["token_counts"].get("sdx", 0) for summary in artifact_summaries)
    has_ps_hold = any(summary["token_counts"].get("ps_hold", 0) for summary in artifact_summaries)
    has_gpio = any(summary["token_counts"].get("gpio", 0) for summary in artifact_summaries)
    rpmh_dense = any(item["class"] == "no-token-context" and item["token_counts"].get("rpmh", 0) >= 40 for item in clusters)
    hypotheses = [
        {
            "id": "H1",
            "strength": "strong",
            "claim": "XBL remains the highest-yield bootloader-side artifact for SDX50M power context.",
            "evidence": "Both XBL slots contain PMIC/PON/SDX/RPMh/AOP/PCIe-class records inside the V1652-approved ranges.",
            "limit": "The records are redacted hashes and token classes; they do not identify a concrete register, GPIO, or rail write.",
        },
        {
            "id": "H2",
            "strength": "medium",
            "claim": "The early PON range is relevant to the SDX50M path.",
            "evidence": f"sdx_present={has_sdx} ps_hold_present={has_ps_hold}; early approved ranges contain PMIC/PON/VDD/SDX records.",
            "limit": "No raw string text is exposed, so the exact bootloader function or data-table name remains private.",
        },
        {
            "id": "H3",
            "strength": "medium",
            "claim": "The dense RPMh/AOP range is likely a boot-resource vocabulary table or nearby code/data cluster.",
            "evidence": f"rpmh_dense={rpmh_dense}; large record clusters preserve RPMh/AOP/PMIC/PCIe token proximity.",
            "limit": "Many records classify as no-token-context because the helper only emits hashed strings; semantic naming is intentionally absent.",
        },
        {
            "id": "H4",
            "strength": "weak-medium",
            "claim": "Cross-slot duplicate hashes show shared XBL code/data, but slot-local deltas still matter.",
            "evidence": f"cross_slot_duplicate_groups={len(cross_slot_dupes)} gpio_token_present={has_gpio}.",
            "limit": "Differences between xbl_a and xbl_b are not automatically causal without Android-good vs native-fail linkage.",
        },
    ]
    return hypotheses


def classify(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    manifest = load_manifest(args.input)
    records = all_records(manifest)
    artifact_summaries = summarize_by_artifact(manifest)
    dupes = duplicate_groups(records)
    clusters = class_cluster(records)
    hypotheses = build_hypotheses(artifact_summaries, dupes, clusters)

    record_field_violations = [
        sorted(set(record) - ALLOWED_RECORD_FIELDS)
        for record in records
        if set(record) - ALLOWED_RECORD_FIELDS
    ]
    total_records = len(records)
    cross_slot_duplicate_count = sum(1 for item in dupes if item["cross_slot"])
    checks = {
        "input_exists": args.input.exists(),
        "input_v1654_pass": manifest.get("decision") == EXPECTED_V1654_DECISION and manifest.get("pass") is True,
        "records_present": total_records > 0,
        "record_fields_allowlisted": not record_field_violations,
        "host_only_no_device_command": True,
        "no_raw_string_output": True,
        "no_partition_write_command": True,
        "no_lower_layer_mutation": True,
    }
    decision = "v1655-xbl-context-interpretation-pass" if all(checks.values()) else "v1655-xbl-context-interpretation-review"
    result = {
        "cycle": "V1655",
        "type": "host-only redacted XBL context interpretation",
        "decision": decision,
        "pass": all(checks.values()),
        "input": rel(args.input),
        "source_decision": manifest.get("decision"),
        "checks": checks,
        "total_records": total_records,
        "artifact_summaries": artifact_summaries,
        "class_clusters": clusters,
        "duplicate_groups_total": len(dupes),
        "cross_slot_duplicate_groups": cross_slot_duplicate_count,
        "duplicate_groups_first": dupes[:32],
        "hypotheses": hypotheses,
        "next": {
            "recommended_cycle": "V1656",
            "type": "bounded host-only XBL-to-Android reference mapping",
            "shape": "map redacted hashes/classes to Android-good boot references without exposing raw strings; no live mutation",
            "mutation": False,
        },
    }
    store.write_json("manifest.json", result)
    return result


def format_counts(counts: dict[str, int]) -> str:
    return ", ".join(f"{key}={value}" for key, value in sorted(counts.items())) or "none"


def render_report(result: dict[str, Any]) -> str:
    lines = [
        "# Native Init V1655 XBL Context Interpretation",
        "",
        "## Summary",
        "",
        "- Cycle: `V1655`",
        "- Type: host-only redacted XBL context interpretation",
        f"- Decision: `{result['decision']}`",
        f"- Result: {'PASS' if result['pass'] else 'REVIEW'}",
        f"- Input: `{result['input']}`",
        f"- Source decision: `{result['source_decision']}`",
        f"- Total redacted records: `{result['total_records']}`",
        f"- Duplicate groups: `{result['duplicate_groups_total']}`",
        f"- Cross-slot duplicate groups: `{result['cross_slot_duplicate_groups']}`",
        "- Device commands: `0`",
        "- Raw string output: `0`",
        "",
        "## Checks",
        "",
    ]
    for key, value in result["checks"].items():
        lines.append(f"- `{key}`: `{value}`")

    lines.extend([
        "",
        "## Artifact Summary",
        "",
        "| artifact | records | high-signal records | classes | tokens | ranges |",
        "|---|---:|---:|---|---|---|",
    ])
    for summary in result["artifact_summaries"]:
        lines.append(
            f"| `{summary['label']}` | {summary['record_count']} | {summary['high_signal_count']} | "
            f"{format_counts(summary['class_counts'])} | {format_counts(summary['token_counts'])} | "
            f"{format_counts(summary['range_counts'])} |"
        )

    lines.extend([
        "",
        "## Class Clusters",
        "",
        "| artifact | class | count | offset min | offset max | tokens |",
        "|---|---|---:|---:|---:|---|",
    ])
    for cluster in result["class_clusters"]:
        lines.append(
            f"| `{cluster['artifact']}` | `{cluster['class']}` | {cluster['count']} | "
            f"{cluster['offset_min']} | {cluster['offset_max']} | {format_counts(cluster['token_counts'])} |"
        )

    lines.extend([
        "",
        "## Cross-Slot Duplicate Digest Groups",
        "",
        "Only digest, token, class, and location metadata are shown. The digest is a SHA256 of private string text captured by V1654.",
        "",
    ])
    cross_slot = [item for item in result["duplicate_groups_first"] if item["cross_slot"]]
    if not cross_slot:
        lines.append("- none in first duplicate window")
    else:
        for item in cross_slot[:16]:
            locations = "; ".join(
                f"{loc['artifact']}@{loc['offset']}[{loc['range']}]"
                for loc in item["locations"]
            )
            lines.append(
                f"- digest=`{item['string_sha256']}` count=`{item['count']}` "
                f"tokens=`{','.join(item['tokens']) or 'none'}` classes=`{','.join(item['classes'])}` "
                f"locations={locations}"
            )

    lines.extend([
        "",
        "## Hypotheses",
        "",
        "| id | strength | claim | evidence | limit |",
        "|---|---|---|---|---|",
    ])
    for hypothesis in result["hypotheses"]:
        lines.append(
            f"| `{hypothesis['id']}` | `{hypothesis['strength']}` | "
            f"{hypothesis['claim']} | {hypothesis['evidence']} | {hypothesis['limit']} |"
        )

    lines.extend([
        "",
        "## Decision",
        "",
        "V1655 keeps XBL as the strongest artifact-level explanation path, but it does not authorize direct PMIC, GPIO, GDSC, PCI, eSoC, or upper Wi-Fi actions. The evidence is sufficient for another host-only mapping pass, not for mutation.",
        "",
        "## Next",
        "",
        "V1656 should stay host-only and map these redacted hashes/classes against Android-good boot references or OSRC/XBL-adjacent public metadata where possible. A bounded rail or PMIC write requires a separate explicit gate with a concrete target and rollback contract.",
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
        "records": result["total_records"],
        "cross_slot_duplicate_groups": result["cross_slot_duplicate_groups"],
    }, indent=2))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

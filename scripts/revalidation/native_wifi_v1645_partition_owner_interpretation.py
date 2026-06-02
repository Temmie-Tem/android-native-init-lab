#!/usr/bin/env python3
"""V1645 host-only interpretation of V1644 partition metadata."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from a90harness.evidence import EvidenceStore, write_private_text

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT_REPORT = REPO_ROOT / "docs/reports/NATIVE_INIT_V1644_PARTITION_METADATA_CAPTURE_2026-06-02.md"
DEFAULT_OUT_DIR = REPO_ROOT / "tmp/wifi/v1645-partition-owner-interpretation"
DEFAULT_REPORT_PATH = REPO_ROOT / "docs/reports/NATIVE_INIT_V1645_PARTITION_OWNER_INTERPRETATION_2026-06-02.md"

PRIORITY = {
    "xbl": {
        "priority": "high",
        "class": "bootloader-pmic-owner-candidate",
        "reason": "earliest bootloader stage; most plausible place for board/PMIC/rail policy before Linux starts",
    },
    "aop": {
        "priority": "high",
        "class": "always-on-power-firmware-candidate",
        "reason": "AOP/RPMh-side firmware is a plausible owner for always-on power sequencing and PMIC coordination",
    },
    "devcfg": {
        "priority": "medium-high",
        "class": "hardware-config-candidate",
        "reason": "device configuration can carry board resource policy consumed by early firmware or boot stages",
    },
    "abl": {
        "priority": "medium",
        "class": "late-bootloader-context",
        "reason": "ABL can affect Linux handoff state but is less likely than XBL/AOP to be the cold SDX rail owner",
    },
    "tz": {
        "priority": "medium",
        "class": "secure-firmware-context",
        "reason": "secure firmware may constrain access but is not a direct AP-native modem rail control surface",
    },
    "hyp": {
        "priority": "low-medium",
        "class": "secure-firmware-context",
        "reason": "hypervisor context may constrain devices but is unlikely to be the primary PMIC owner",
    },
    "qupfw": {
        "priority": "low-medium",
        "class": "bus-firmware-context",
        "reason": "QUP firmware is peripheral-bus context, not a likely SDX50M main-rail owner",
    },
    "cmnlib": {
        "priority": "low",
        "class": "security-library-context",
        "reason": "common security library, unlikely to own board power sequencing",
    },
    "cmnlib64": {
        "priority": "low",
        "class": "security-library-context",
        "reason": "64-bit common security library, unlikely to own board power sequencing",
    },
    "keymaster": {
        "priority": "low",
        "class": "security-service-context",
        "reason": "key service firmware, not a likely PMIC or SDX rail owner",
    },
    "modem": {
        "priority": "context-only",
        "class": "downstream-firmware-context",
        "reason": "modem firmware can explain downstream protocol expectations but not the pre-MDM2AP AP-side power owner",
    },
    "dsp": {
        "priority": "context-only",
        "class": "downstream-firmware-context",
        "reason": "DSP firmware is downstream context, not a bootloader/PMIC ownership candidate",
    },
    "bluetooth": {
        "priority": "context-only",
        "class": "downstream-firmware-context",
        "reason": "Bluetooth firmware is not expected to own SDX50M power sequencing",
    },
}


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def parse_v1644_table(report: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for line in report.splitlines():
        if not line.startswith("| `"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != 6:
            continue
        name = cells[0].strip("`")
        devname = cells[1].strip("`")
        partn = cells[2]
        size = cells[3]
        devnode = cells[4].strip("`")
        sha256 = cells[5].strip("`")
        if not name or name == "name":
            continue
        rows.append({
            "name": name,
            "devname": devname,
            "partn": partn,
            "size": size,
            "devnode": devnode,
            "sha256": sha256,
        })
    return rows


def classify(report_path: Path) -> dict[str, Any]:
    report = report_path.read_text(encoding="utf-8", errors="replace")
    rows = parse_v1644_table(report)
    classifications = []
    for row in rows:
        info = PRIORITY.get(row["name"], {
            "priority": "review",
            "class": "unclassified",
            "reason": "not in V1645 partition priority table",
        })
        classifications.append({
            **row,
            **info,
            "raw_content_available": bool(row.get("sha256")),
            "devnode_available": bool(row.get("devnode")),
        })
    high = [item for item in classifications if item["priority"] == "high"]
    actionable = [item for item in classifications if item["priority"] in {"high", "medium-high", "medium"}]
    checks = {
        "v1644_report_present": report_path.exists(),
        "v1644_pass_recorded": "Decision: `v1644-read-only-partition-metadata-captured`" in report,
        "candidate_count_positive": len(classifications) > 0,
        "high_priority_candidates_present": len(high) > 0,
        "raw_binaries_not_required_for_this_cycle": True,
        "no_device_command": True,
        "no_live_write_gate": True,
    }
    decision = (
        "v1645-partition-owner-priority-classified"
        if all(checks.values())
        else "v1645-partition-owner-interpretation-review"
    )
    return {
        "cycle": "V1645",
        "type": "host-only partition owner interpretation",
        "decision": decision,
        "pass": all(checks.values()),
        "input_report": rel(report_path),
        "checks": checks,
        "classifications": classifications,
        "high_priority": high,
        "actionable_candidates": actionable,
        "next": {
            "recommended_cycle": "V1646",
            "type": "private read-only artifact access preflight",
            "reason": "XBL/AOP/devcfg/ABL are the only plausible next artifacts, but raw content is not yet available because native exposes sysfs GPT metadata without candidate /dev/block nodes",
            "allowed_shape": "host-only plan first; if live is selected later, create temporary private devnodes or use TWRP/Android read-only pull, hash selected small candidates, and keep binary content out of git",
            "mutation": "no partition writes; no PMIC/GPIO/GDSC writes; temporary filesystem-only devnode creation requires a separate explicit gate",
        },
    }


def render_report(result: dict[str, Any]) -> str:
    lines = [
        "# Native Init V1645 Partition Owner Interpretation",
        "",
        "## Summary",
        "",
        "- Cycle: `V1645`",
        "- Type: host-only partition owner interpretation",
        f"- Decision: `{result['decision']}`",
        f"- Result: {'PASS' if result['pass'] else 'REVIEW'}",
        f"- Input: `{result['input_report']}`",
        "- Reason: classify V1644 sysfs GPT partition metadata into plausible SDX50M / PMIC / PON owner artifacts before any raw extraction or write gate.",
        "",
        "## Checks",
        "",
    ]
    for key, value in result["checks"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend([
        "",
        "## Candidate Priority",
        "",
        "| name | devname | size | priority | class | reason |",
        "|---|---|---:|---|---|---|",
    ])
    for item in result["classifications"]:
        lines.append(
            f"| `{item['name']}` | `{item['devname']}` | {item['size']} | "
            f"`{item['priority']}` | `{item['class']}` | {item['reason']} |"
        )
    lines.extend([
        "",
        "## Interpretation",
        "",
        "The highest-value artifacts are `xbl` and `aop`, followed by `devcfg` and `abl`. These are the only currently plausible places for bootloader / always-on / board-resource policy that could explain why Android starts with a usable SDX50M power state while native reaches the correct eSoC provider path but still sees no MDM2AP response. `modem`, `dsp`, and `bluetooth` remain downstream context and should not pull the loop back into MHI/WLFW analysis before MDM2AP responds.",
        "",
        "V1644 did not expose candidate `/dev/block/<devname>` nodes, so raw content and SHA256 are intentionally absent. That absence is a runtime surface finding, not permission to write partitions or to force PMIC/GPIO/GDSC state.",
        "",
        "## Next",
        "",
        "V1646 should be a separate private read-only artifact access preflight. It should choose one safe path: temporary private devnodes derived from sysfs major/minor with cleanup, or TWRP/Android read-only pull. It must hash only selected small high-priority candidates first (`xbl`, `aop`, `devcfg`, `abl`), keep binary content out of git, and avoid PMIC/GPIO/GDSC writes, eSoC notify/`BOOT_DONE`, PCI rescan, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping.",
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
        "high_priority": [item["name"] for item in result["high_priority"]],
        "report": rel(args.report_path),
    }, indent=2))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

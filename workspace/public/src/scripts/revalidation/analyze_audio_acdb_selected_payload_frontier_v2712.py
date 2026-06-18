#!/usr/bin/env python3
"""V2712 host-only ACDB selected-payload frontier audit.

V2711 closed SET-argument geometry as the explanation for the V2708
`send_asm_custom_topology` DSP rejection.  This audit consolidates the remaining
payload/selector evidence:

* the core topology DB contains the selected ADM/ASM/AFE records;
* the captured lower/V2704 cal10 and cal14 payloads do not contain the selected
  route topology IDs;
* the synthetic selected/defined-module candidates were already replayed and
  failed; and
* cal24 is not the current frontier because its selected AFE record is present
  in the exact lower payload family.

It reads private binary payloads only to compute metadata and selected-ID
presence.  It never emits raw ACDB bytes, runs a device, or issues an ioctl.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import analyze_audio_acdb_db_selected_topology_v2696 as v2696
except ModuleNotFoundError:  # pragma: no cover - package import path in unittest.
    from workspace.public.src.scripts.revalidation import analyze_audio_acdb_db_selected_topology_v2696 as v2696

ROOT = Path(__file__).resolve().parents[5]
RUN_ID = "V2712"
DEFAULT_REPORT = ROOT / "docs/reports/NATIVE_INIT_V2712_AUDIO_ACDB_SELECTED_PAYLOAD_FRONTIER_2026-06-18.md"

DEFAULT_PAYLOADS = {
    10: {
        "role": "ADM_CUST_TOPOLOGY",
        "selected_topology": 0x10004000,
        "observed_payload": ROOT / "workspace/private/inputs/audio/acdb_replay/payloads/adm_custom_topology_cal10_v2704.bin",
    },
    14: {
        "role": "ASM_CUST_TOPOLOGY",
        "selected_topology": 0x10005000,
        "observed_payload": ROOT / "workspace/private/inputs/audio/acdb_replay/payloads/asm_custom_topology_cal14_v2704.bin",
    },
    24: {
        "role": "AFE_CUST_TOPOLOGY",
        "selected_topology": 0x1001025D,
        "observed_payload": ROOT / "workspace/private/inputs/audio/acdb_replay/payloads/afe_custom_topology_cal24_v2704.bin",
    },
}

CORE_PAYLOAD = ROOT / "workspace/private/inputs/audio/acdb_replay/payloads/core_custom_topologies_v2547.bin"
V2688_PLAN = ROOT / "workspace/private/builds/audio/v2688-acdb-defined-module-topology-replay-deploy-plan/deploy-plan.json"
V2689_REPORT = ROOT / "docs/reports/NATIVE_INIT_V2689_AUDIO_ACDB_DEFINED_MODULE_TOPOLOGY_LIVE_REPLAY_2026-06-18.md"
V2711_REPORT = ROOT / "docs/reports/NATIVE_INIT_V2711_AUDIO_ACDB_SETARG_GEOMETRY_FRONTIER_2026-06-18.md"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def rel(path: Path | str | None) -> str | None:
    if path is None:
        return None
    target = Path(path)
    try:
        return str(target.resolve().relative_to(ROOT.resolve()))
    except ValueError:
        return str(path)


def hex32(value: int) -> str:
    return f"0x{value & 0xFFFFFFFF:08x}"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def selected_present(scan: dict[str, Any], topology_id: int) -> bool:
    target = hex32(topology_id)
    if scan.get("target_word_hits", {}).get(target):
        return True
    for key in ("whole_core_topologies", "whole_fixed_topologies"):
        for item in scan.get(key) or []:
            if int(item.get("topology_id", -1)) == topology_id:
                return True
    return False


def parser_name(scan: dict[str, Any]) -> str:
    if scan.get("whole_core_ok"):
        return "core"
    if scan.get("whole_fixed_ok"):
        return "fixed"
    return "unparsed"


def scan_private_payload(path: Path, topology_id: int) -> dict[str, Any]:
    if not path.exists():
        return {
            "path": rel(path),
            "exists": False,
            "selected_present": False,
            "parser": "missing",
        }
    scan = v2696.scan_file(path)
    return {
        "path": scan["path"],
        "exists": True,
        "size": scan["size"],
        "sha256": scan["sha256"],
        "parser": parser_name(scan),
        "selected_topology": hex32(topology_id),
        "selected_present": selected_present(scan, topology_id),
        "topology_ids": [
            item["topology_hex"]
            for item in (scan.get("whole_core_topologies") or scan.get("whole_fixed_topologies") or [])
        ],
        "target_word_hits": scan.get("target_word_hits", {}),
    }


def plan_remote_to_local(plan: dict[str, Any]) -> dict[str, Path]:
    output: dict[str, Path] = {}
    for item in plan.get("files", []):
        remote = item.get("remote_path")
        local = (item.get("local") or {}).get("local_path_private")
        if remote and local:
            output[str(remote)] = ROOT / local if not Path(local).is_absolute() else Path(local)
    return output


def defined_candidate_paths(plan_path: Path) -> dict[int, Path]:
    if not plan_path.exists():
        return {}
    plan = read_json(plan_path)
    path_map = plan_remote_to_local(plan)
    paths: dict[int, Path] = {}
    for entry in plan.get("basic_payloads", []):
        try:
            cal_type = int(entry.get("cal_type"))
        except (TypeError, ValueError):
            continue
        if cal_type not in (10, 14):
            continue
        remote = entry.get("payload_remote")
        if remote in path_map:
            paths[cal_type] = path_map[remote]
    return paths


def report_contains(path: Path, *needles: str) -> bool:
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8", errors="replace")
    return all(needle in text for needle in needles)


def build_rows(args: argparse.Namespace) -> list[dict[str, Any]]:
    core_scan = scan_private_payload(args.core_payload, 0)
    candidate_paths = defined_candidate_paths(args.v2688_plan)
    rows: list[dict[str, Any]] = []
    for cal_type, meta in DEFAULT_PAYLOADS.items():
        selected_topology = int(meta["selected_topology"])
        observed = scan_private_payload(Path(meta["observed_payload"]), selected_topology)
        candidate = scan_private_payload(candidate_paths[cal_type], selected_topology) if cal_type in candidate_paths else {
            "exists": False,
            "selected_present": False,
            "path": None,
            "parser": "missing",
        }
        core_selected = selected_present(v2696.scan_file(args.core_payload), selected_topology) if args.core_payload.exists() else False
        rows.append(
            {
                "cal_type": cal_type,
                "role": str(meta["role"]),
                "selected_topology": hex32(selected_topology),
                "core_selected_present": core_selected,
                "observed_payload": observed,
                "defined_candidate_payload": candidate,
                "frontier": classify_cal_frontier(cal_type, observed, candidate, core_selected),
            }
        )
    _ = core_scan
    return rows


def classify_cal_frontier(cal_type: int, observed: dict[str, Any], candidate: dict[str, Any], core_selected: bool) -> str:
    if cal_type == 24 and observed.get("selected_present"):
        return "not-current-frontier-selected-lower-payload-present"
    if cal_type == 14:
        if not observed.get("selected_present") and candidate.get("selected_present"):
            return "selected-candidate-already-failed-existing-lower-payload-stale"
    if cal_type == 10:
        if not observed.get("selected_present") and candidate.get("selected_present"):
            return "selected-candidate-already-failed-no-exact-lower-set"
        if core_selected and not observed.get("selected_present"):
            return "core-selected-only-no-exact-lower-set"
    return "unresolved"


def classify(summary_rows: list[dict[str, Any]], args: argparse.Namespace) -> dict[str, Any]:
    by_cal = {row["cal_type"]: row for row in summary_rows}
    v2689_failed = report_contains(args.v2689_report, "v2689-defined-module-topology-replay-still-adsp-ebadparam", "send_asm_custom_topology")
    v2711_geometry_closed = report_contains(args.v2711_report, "v2711-setarg-geometry-exhausted-selector-payload-frontier")
    cal14_lower_stale = bool(not by_cal[14]["observed_payload"].get("selected_present"))
    cal10_lower_unselected = bool(not by_cal[10]["observed_payload"].get("selected_present"))
    cal24_ok = bool(by_cal[24]["observed_payload"].get("selected_present"))
    existing_candidates_exhausted = bool(v2689_failed and v2711_geometry_closed and cal14_lower_stale and cal10_lower_unselected and cal24_ok)
    return {
        "decision": "v2712-existing-payload-corpus-exhausted-need-new-selector-model" if existing_candidates_exhausted else "v2712-selected-payload-frontier-open",
        "v2689_defined_candidate_replay_failed": v2689_failed,
        "v2711_setarg_geometry_closed": v2711_geometry_closed,
        "cal14_observed_payload_selected_present": not cal14_lower_stale,
        "cal10_observed_payload_selected_present": not cal10_lower_unselected,
        "cal24_observed_payload_selected_present": cal24_ok,
        "existing_candidates_exhausted": existing_candidates_exhausted,
        "native_replay_should_remain_parked": existing_candidates_exhausted,
        "recommended_next": "loader-selector-state-re-or-route-specific-real-hal-set-capture",
    }


def build_summary(args: argparse.Namespace) -> dict[str, Any]:
    rows = build_rows(args)
    return {
        "run_id": RUN_ID,
        "created_at": now_iso(),
        "host_only": True,
        "device_action": False,
        "raw_payload_read_for_metadata_only": True,
        "inputs": {
            "core_payload": rel(args.core_payload),
            "v2688_plan": rel(args.v2688_plan),
            "v2689_report": rel(args.v2689_report),
            "v2711_report": rel(args.v2711_report),
        },
        "rows": rows,
        "classification": classify(rows, args),
        "next_requirements": [
            "Do not replay the unchanged V2707/V2708 manifest again.",
            "Do not replay the V2688 defined-module cal10/cal14 candidates again; V2689 already falsified that branch.",
            "Treat cal24 as closed for this frontier because its selected AFE topology is present in the exact lower payload family.",
            "Recover byte-exact selected cal10/cal14 SET payloads or change the loader selector model before any new native replay.",
        ],
    }


def write_report(summary: dict[str, Any], path: Path) -> None:
    c = summary["classification"]
    lines = [
        "# NATIVE_INIT V2712 — ACDB selected-payload frontier audit",
        "",
        "Date: 2026-06-18",
        "",
        "## Scope",
        "",
        "Host-only audit of the existing private ACDB custom-topology payload corpus and public prior reports.",
        "This unit reads private binary payloads only for SHA-256, parser metadata, and selected topology-ID presence.",
        "It emits no raw ACDB bytes, runs no device step, and issues no `/dev/msm_audio_cal` ioctl.",
        "",
        "## Result",
        "",
        f"- Decision: `{c['decision']}`",
        f"- V2689 defined-candidate replay failed: `{c['v2689_defined_candidate_replay_failed']}`",
        f"- V2711 SET-arg geometry closed: `{c['v2711_setarg_geometry_closed']}`",
        f"- cal_type 10 observed payload contains selected topology: `{c['cal10_observed_payload_selected_present']}`",
        f"- cal_type 14 observed payload contains selected topology: `{c['cal14_observed_payload_selected_present']}`",
        f"- cal_type 24 observed payload contains selected topology: `{c['cal24_observed_payload_selected_present']}`",
        f"- Existing candidates exhausted: `{c['existing_candidates_exhausted']}`",
        f"- Recommended next: `{c['recommended_next']}`",
        "",
        "## Payload frontier table",
        "",
        "| cal_type | role | selected topology | core selected | observed payload selected | observed size | observed SHA-256 | defined candidate selected | defined candidate size | frontier |",
        "| ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | --- |",
    ]
    for row in summary["rows"]:
        observed = row["observed_payload"]
        candidate = row["defined_candidate_payload"]
        lines.append(
            "| `{cal}` | `{role}` | `{top}` | `{core}` | `{obs_sel}` | `{obs_size}` | `{obs_sha}` | `{cand_sel}` | `{cand_size}` | `{frontier}` |".format(
                cal=row["cal_type"],
                role=row["role"],
                top=row["selected_topology"],
                core=row["core_selected_present"],
                obs_sel=observed.get("selected_present"),
                obs_size=observed.get("size", "missing"),
                obs_sha=observed.get("sha256", "missing"),
                cand_sel=candidate.get("selected_present"),
                cand_size=candidate.get("size", "missing"),
                frontier=row["frontier"],
            )
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- The core topology blob still contains parseable selected ADM `0x10004000`, ASM `0x10005000`, and AFE `0x1001025d` records.",
            "- The observed/lower cal_type `10` and `14` payloads do not contain the selected ADM/ASM route topology IDs.",
            "- The defined-module selected cal_type `10`/`14` candidates do contain those selected IDs, but V2689 already replayed that branch and still failed at `send_asm_custom_topology` with `ADSP_EBADPARAM`.",
            "- V2711 closed SET-arg geometry for cal_type `14`: V2708 effectively replayed the same exact lower cal14 SET arg/payload family, not an arbitrary header shape.",
            "- cal_type `24` is not the current blocker: the selected AFE topology is already present in the exact lower/V2704 payload family.",
            "",
            "Therefore the next replay cannot be another unchanged V2707/V2708 run, another V2688 defined-module replay, or another SET-arg-only capture. The frontier is the selected cal_type `10`/`14` selector/payload contract itself.",
            "",
            "## Next Requirements",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in summary["next_requirements"])
    lines.extend(
        [
            "",
            "## Validation",
            "",
            "- `python3 -m py_compile workspace/public/src/scripts/revalidation/analyze_audio_acdb_selected_payload_frontier_v2712.py tests/test_analyze_audio_acdb_selected_payload_frontier_v2712.py`",
            "- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_analyze_audio_acdb_selected_payload_frontier_v2712 -v`",
            "- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/analyze_audio_acdb_selected_payload_frontier_v2712.py --write-report --json`",
            "- `git diff --check`",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--core-payload", type=Path, default=CORE_PAYLOAD)
    parser.add_argument("--v2688-plan", type=Path, default=V2688_PLAN)
    parser.add_argument("--v2689-report", type=Path, default=V2689_REPORT)
    parser.add_argument("--v2711-report", type=Path, default=V2711_REPORT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    summary = build_summary(args)
    if args.write_report:
        write_report(summary, args.report)
    if args.json:
        print(json.dumps(summary, indent=2, sort_keys=True))
    elif not args.write_report:
        print(summary["classification"]["decision"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

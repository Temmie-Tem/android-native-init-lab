#!/usr/bin/env python3
"""Select the next native-init frontier action from current public state."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

from _workspace_bootstrap import repo_root


REPO_ROOT = repo_root()
GOAL_PATH = REPO_ROOT / "GOAL.md"
TODO_PATH = REPO_ROOT / "docs" / "plans" / "NATIVE_INIT_CURRENT_TODO_2026-06-08.md"
INVENTORY_JSON = REPO_ROOT / "docs" / "reports" / "REVALIDATION_SCRIPT_INVENTORY_2026-06-10.json"
FRONTIER_CANDIDATES_JSON = REPO_ROOT / "docs" / "artifacts" / "native-init-frontier-candidates.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    return parser.parse_args()


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def marker_present(text: str, marker: str) -> bool:
    return marker in text


def all_markers_present(text: str, markers: tuple[str, ...]) -> bool:
    return all(marker in text for marker in markers)


def ready_t1_candidates(frontier_candidates: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        candidate
        for candidate in frontier_candidates.get("candidates", [])
        if candidate.get("track") == "T1"
        and candidate.get("safe_actionable_now") is True
        and candidate.get("status") == "ready_for_next_v_iteration"
    ]


def track_evaluations(
    goal_text: str,
    todo_text: str,
    inventory: dict[str, Any],
    frontier_candidates: dict[str, Any],
) -> list[dict[str, Any]]:
    signals = inventory["consolidation_signals"]
    t1_candidates = ready_t1_candidates(frontier_candidates)
    t1_closed_boundary = all_markers_present(
        goal_text,
        (
            "Do not spend more T1 work on generic CPU-clock tuning",
            "this firmware_class boundary unless a new independent oracle is identified",
        ),
    )
    t2_complete_baseline = marker_present(
        todo_text,
        "Status: complete for the current `v2254-wifi-detail-surface` baseline.",
    )
    t2_hold_reconnect_complete = marker_present(
        todo_text,
        "V2282 rollbackably validated V2254 through current-baseline connect, DHCP,",
    )
    t2_soak_deferred = marker_present(
        todo_text,
        "V2282 already covers the current 180 second hold/reconnect criterion.",
    )
    t3_no_direct_migration = signals.get("direct_a90ctl_actionable_now_count") == 0
    t3_no_delete_review = signals.get("source_delete_review_count") == 0
    t3_no_phase_residual_backlog = bool(signals.get("active_live_phase_residual_backlog_closed"))
    t1_status = "new-independent-oracle-ready" if t1_candidates else "defer-until-new-independent-oracle"
    t1_trigger = (
        "V2253 closed the documented firmware_class boundary and generic CPU-clock sampler loop; "
        "V2279 built a higher-coverage workqueue execute_start oracle after V2278 exposed a printed-window overflow limitation; "
        "the V2280 live-validation candidate remains."
        if t1_candidates
        else "V2253 closed the documented firmware_class boundary and generic CPU-clock sampler loop; "
        "V2280 closed the widened workqueue execute_start scalar function-pointer window with total=stored and overflow=0; "
        "current public state names no new independent kernel-observation oracle."
    )

    return [
        {
            "track": "T1",
            "name": "kernel-observation",
            "safe_actionable_now": bool(t1_candidates),
            "status": t1_status,
            "drop_trigger": t1_trigger,
            "evidence": {
                "closed_boundary_marker_present": t1_closed_boundary,
                "ready_candidate_count": len(t1_candidates),
                "ready_candidate_ids": [candidate["id"] for candidate in t1_candidates],
            },
        },
        {
            "track": "T2",
            "name": "wlan-native-init",
            "safe_actionable_now": False,
            "status": "defer-until-new-promotion-or-live-validation-criterion",
            "drop_trigger": (
                "V2254/V2256 are the current promoted WLAN surface baseline, and V2282 "
                "already covered the current 180 second connect/DHCP/ping/hold/reconnect criterion; "
                "longer data-path soak remains deferred until new promotion criteria require it."
            ),
            "evidence": {
                "current_baseline_complete_marker_present": t2_complete_baseline,
                "hold_reconnect_complete_marker_present": t2_hold_reconnect_complete,
                "soak_deferred_marker_present": t2_soak_deferred,
            },
        },
        {
            "track": "T3",
            "name": "self-directed-cleanup",
            "safe_actionable_now": not (t3_no_direct_migration and t3_no_delete_review and t3_no_phase_residual_backlog),
            "status": "no-cleanup-backlog" if t3_no_direct_migration and t3_no_delete_review and t3_no_phase_residual_backlog else "inspect-cleanup-backlog",
            "drop_trigger": (
                "Inventory has no actionable direct command-client migration group, no delete-review rows, "
                "and no active live phase/residual metadata backlog."
            ),
            "evidence": {
                "direct_actionable_now_count": signals.get("direct_a90ctl_actionable_now_count"),
                "direct_review_only_count": signals.get("direct_a90ctl_review_only_count"),
                "direct_next_actionable_group": signals.get("direct_a90ctl_next_actionable_group"),
                "source_delete_review_count": signals.get("source_delete_review_count"),
                "active_live_phase_residual_backlog_closed": signals.get("active_live_phase_residual_backlog_closed"),
            },
        },
    ]


def select_frontier() -> dict[str, Any]:
    goal_text = read_text(GOAL_PATH)
    todo_text = read_text(TODO_PATH)
    inventory = read_json(INVENTORY_JSON)
    frontier_candidates = read_json(FRONTIER_CANDIDATES_JSON) if FRONTIER_CANDIDATES_JSON.exists() else {"candidates": []}
    evaluations = track_evaluations(goal_text, todo_text, inventory, frontier_candidates)
    actionable = [evaluation for evaluation in evaluations if evaluation["safe_actionable_now"]]
    return {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "decision": "frontier-selector-no-automatic-safe-unit" if not actionable else "frontier-selector-actionable-unit-present",
        "selected_track": actionable[0]["track"] if actionable else None,
        "selected_reason": actionable[0]["status"] if actionable else None,
        "track_evaluations": evaluations,
        "next_operator_decision": (
            "Define a new T1 oracle, set a concrete V2254 live-validation criterion beyond V2282, "
            "or revive a historical runner before selecting the next bounded unit."
        ) if not actionable else "Run the first actionable track through the normal GOAL.md cycle.",
        "source_paths": {
            "goal": str(GOAL_PATH.relative_to(REPO_ROOT)),
            "todo": str(TODO_PATH.relative_to(REPO_ROOT)),
            "inventory": str(INVENTORY_JSON.relative_to(REPO_ROOT)),
            "frontier_candidates": str(FRONTIER_CANDIDATES_JSON.relative_to(REPO_ROOT)),
        },
    }


def render_text(data: dict[str, Any]) -> str:
    lines = [
        f"decision={data['decision']}",
        f"selected_track={data['selected_track']}",
    ]
    for evaluation in data["track_evaluations"]:
        lines.append(
            f"{evaluation['track']} {evaluation['status']} "
            f"safe_actionable_now={evaluation['safe_actionable_now']}"
        )
    lines.append(f"next_operator_decision={data['next_operator_decision']}")
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    data = select_frontier()
    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(render_text(data))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

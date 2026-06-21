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
CURRENT_DOOM_FRONTIER_REPORT = (
    REPO_ROOT / "docs" / "reports" / "NATIVE_INIT_V3008_DOOM_INPUT_FRONTIER_RECONCILIATION_2026-06-20.md"
)
CURRENT_DOOM_FLASH_GATE_REPORT = (
    REPO_ROOT / "docs" / "reports" / "NATIVE_INIT_V3010_DOOM_INPUT_FLASH_GATE_ASSETS_2026-06-20.md"
)
CURRENT_DOOM_LIVE_PRECONDITION_REPORT = (
    REPO_ROOT / "docs" / "reports" / "NATIVE_INIT_V3012_DOOM_INPUT_LIVE_PRECONDITION_CURRENT_2026-06-20.md"
)
CURRENT_DOOM_GAMEPLAY_LOOP_REPORT = (
    REPO_ROOT / "docs" / "reports" / "NATIVE_INIT_V3017_DOOMPAD_GAMEPLAY_LOOP_LIVE_2026-06-21.md"
)
CURRENT_DEMO_CHECKPOINT_SOURCE_REPORT = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V3021_DEMO_CHECKPOINT_BADAPPLE_NYAN_SOURCE_BUILD_2026-06-21.md"
)
CURRENT_DEMO_CHECKPOINT_LIVE_REPORT = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V3022_DEMO_CHECKPOINT_BADAPPLE_NYAN_LIVE_2026-06-21.md"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    return parser.parse_args()


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_optional_text(path: Path) -> str | None:
    return read_text(path) if path.exists() else None


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


def current_doom_flash_gate_evidence(report_text: str | None) -> dict[str, Any]:
    if not report_text:
        return {
            "v3010_flash_gate_report_present": False,
            "v3010_flash_gate_assets_ready": False,
            "v3010_flash_gate_reports_ok": False,
            "v3010_external_hardware_wait_retained": False,
            "v3010_v3004_live_actionable_now": None,
            "v3010_flash_gate_decision": None,
        }
    decision_ready = "v3010-doom-input-flash-gate-assets-ready-hardware-wait" in report_text
    assets_ready = marker_present(report_text, "Required assets present: `1`") and marker_present(
        report_text, "Expected SHA256 checks pass: `1`"
    )
    reports_ok = marker_present(report_text, "Current gate reports pass: `1`")
    external_wait = marker_present(report_text, "External hardware wait retained: `1`")
    live_actionable = marker_present(report_text, "V3004 live actionable now: `1`")
    return {
        "v3010_flash_gate_report_present": True,
        "v3010_flash_gate_assets_ready": bool(decision_ready and assets_ready),
        "v3010_flash_gate_reports_ok": bool(reports_ok),
        "v3010_external_hardware_wait_retained": bool(external_wait),
        "v3010_v3004_live_actionable_now": bool(live_actionable),
        "v3010_flash_gate_decision": (
            "v3010-doom-input-flash-gate-assets-ready-hardware-wait"
            if decision_ready
            else "v3010-doom-input-flash-gate-assets-not-ready"
        ),
    }


def current_doom_live_precondition_evidence(report_text: str | None) -> dict[str, Any]:
    if not report_text:
        return {
            "v3012_live_precondition_report_present": False,
            "v3012_resident_health_ok": False,
            "v3012_gate_assets_ready": False,
            "v3012_external_gate_retained": False,
            "v3012_a90_otg_keyboard_evidence": False,
            "v3012_v3004_live_actionable_now": None,
            "v3012_host_only_gate_audit_stop": False,
            "v3012_live_precondition_decision": None,
        }
    decision_wait = "v3012-doom-input-live-precondition-current-hardware-wait" in report_text
    decision_ready = "v3012-doom-input-live-precondition-live-ready" in report_text
    resident_health_ok = marker_present(report_text, "Bridge/control path ready: `1`") and marker_present(
        report_text, "Resident selftest fail=0: `1`"
    )
    gate_assets_ready = marker_present(report_text, "V3010 flash-gate assets ready: `1`")
    external_gate_retained = marker_present(report_text, "V3011 selector external gate retained: `1`")
    a90_otg_keyboard_evidence = marker_present(report_text, "A90 OTG keyboard evdev evidence: `1`")
    live_actionable = marker_present(report_text, "V3004 live actionable now: `1`")
    return {
        "v3012_live_precondition_report_present": True,
        "v3012_resident_health_ok": bool(resident_health_ok),
        "v3012_gate_assets_ready": bool(gate_assets_ready),
        "v3012_external_gate_retained": bool(external_gate_retained),
        "v3012_a90_otg_keyboard_evidence": bool(a90_otg_keyboard_evidence),
        "v3012_v3004_live_actionable_now": bool(live_actionable),
        "v3012_host_only_gate_audit_stop": bool(
            decision_wait
            and resident_health_ok
            and gate_assets_ready
            and external_gate_retained
            and not a90_otg_keyboard_evidence
            and not live_actionable
        ),
        "v3012_live_precondition_decision": (
            "v3012-doom-input-live-precondition-live-ready"
            if decision_ready
            else (
                "v3012-doom-input-live-precondition-current-hardware-wait"
                if decision_wait
                else "v3012-doom-input-live-precondition-current-blocked"
            )
        ),
    }


def current_doom_gameplay_loop_evidence(report_text: str | None) -> dict[str, Any]:
    if not report_text:
        return {
            "v3017_gameplay_loop_report_present": False,
            "v3017_state_consumed": False,
            "v3017_doomplay_rc_ok": False,
            "v3017_doomplay_markers_ok": False,
            "v3017_player_moved_forward": False,
            "v3017_rollback_health_ok": False,
            "v3017_not_wad_backed": False,
            "v3017_gameplay_loop_decision": None,
        }
    decision_pass = "v3017-doompad-gameplay-loop-state-consumed-pass-before-rollback" in report_text
    doomplay_rc_ok = marker_present(report_text, "`video demo doom play 8` rc: `0`")
    doomplay_markers_ok = marker_present(report_text, "`video demo doom play 8` rc: `0` markers_ok=`1`")
    moved_forward = marker_present(report_text, "Player movement parsed: `1` moved_forward=`1`")
    rollback_health_ok = marker_present(report_text, "Rollback health: version_ok=`1` selftest_fail0=`1`")
    not_wad_backed = marker_present(report_text, "not a WAD-backed `doomgeneric` engine")
    return {
        "v3017_gameplay_loop_report_present": True,
        "v3017_state_consumed": bool(decision_pass and doomplay_rc_ok and doomplay_markers_ok and moved_forward),
        "v3017_doomplay_rc_ok": bool(doomplay_rc_ok),
        "v3017_doomplay_markers_ok": bool(doomplay_markers_ok),
        "v3017_player_moved_forward": bool(moved_forward),
        "v3017_rollback_health_ok": bool(rollback_health_ok),
        "v3017_not_wad_backed": bool(not_wad_backed),
        "v3017_gameplay_loop_decision": (
            "v3017-doompad-gameplay-loop-state-consumed-pass-before-rollback"
            if decision_pass
            else "v3017-doompad-gameplay-loop-not-proven"
        ),
    }


def current_demo_checkpoint_source_evidence(report_text: str | None) -> dict[str, Any]:
    if not report_text:
        return {
            "v3021_source_report_present": False,
            "v3021_source_build_pass": False,
            "v3021_boot_sha_present": False,
            "v3021_badapple_contract_present": False,
            "v3021_nyan_contract_present": False,
            "v3021_adoption_pending_live": False,
        }
    source_build_pass = "v3021-demo-checkpoint-badapple-nyan-source-build-pass" in report_text
    boot_sha_present = marker_present(report_text, "Boot SHA256: `c860d604e3c906abf61fdd2c9bd9cd12d1aef2c88c05be57677b472ad36ef0f7`")
    badapple_contract = all_markers_present(
        report_text,
        (
            "Bad Apple asset ID: `badapple-480x360-full-v2903`",
            "menu.demo.badapple.action=play-av-fullsong",
            "menu.demo.badapple.frames=6962",
        ),
    )
    nyan_contract = all_markers_present(
        report_text,
        (
            "Nyan asset ID: `nyancat-v2973-pal8-rle-preview`",
            "menu.demo.nyan.action=play-av-preview",
            "pal8-rle",
        ),
    )
    adoption_pending = "pending-badapple-nyan-same-image-live-validation" in report_text
    return {
        "v3021_source_report_present": True,
        "v3021_source_build_pass": bool(source_build_pass),
        "v3021_boot_sha_present": bool(boot_sha_present),
        "v3021_badapple_contract_present": bool(badapple_contract),
        "v3021_nyan_contract_present": bool(nyan_contract),
        "v3021_adoption_pending_live": bool(adoption_pending),
    }


def current_demo_checkpoint_live_evidence(report_text: str | None) -> dict[str, Any]:
    if not report_text:
        return {
            "v3022_live_report_present": False,
            "v3022_same_image_live_pass": False,
            "v3022_badapple_pass": False,
            "v3022_nyan_pass": False,
            "v3022_rollback_health_ok": False,
        }
    same_image_pass = "v3022-demo-checkpoint-badapple-nyan-same-image-live-pass-before-rollback" in report_text
    badapple_pass = "Same-image validation: Bad Apple pass=`1` Nyan pass=`1`" in report_text
    nyan_pass = badapple_pass
    rollback_ok = "Rollback health: version_ok=`1` selftest_fail0=`1`" in report_text
    return {
        "v3022_live_report_present": True,
        "v3022_same_image_live_pass": bool(same_image_pass),
        "v3022_badapple_pass": bool(badapple_pass),
        "v3022_nyan_pass": bool(nyan_pass),
        "v3022_rollback_health_ok": bool(rollback_ok),
    }


def current_demo_checkpoint_evaluation(
    goal_text: str,
    source_report_text: str | None = None,
    live_report_text: str | None = None,
) -> dict[str, Any] | None:
    checkpoint_chartered = all_markers_present(
        goal_text,
        (
            'PATCH-level kept "demo checkpoint"',
            "**Bad Apple + Nyan** demos",
            "**0.11.0 (MINOR) is RESERVED",
        ),
    )
    if not checkpoint_chartered:
        return None
    source = current_demo_checkpoint_source_evidence(source_report_text)
    live = current_demo_checkpoint_live_evidence(live_report_text)
    source_ready = bool(
        source["v3021_source_build_pass"]
        and source["v3021_boot_sha_present"]
        and source["v3021_badapple_contract_present"]
        and source["v3021_nyan_contract_present"]
        and source["v3021_adoption_pending_live"]
    )
    live_validated = bool(
        live["v3022_same_image_live_pass"]
        and live["v3022_badapple_pass"]
        and live["v3022_nyan_pass"]
        and live["v3022_rollback_health_ok"]
    )
    return {
        "track": "VIDEO",
        "name": "demo-checkpoint",
        "safe_actionable_now": not live_validated,
        "status": (
            "demo-checkpoint-live-validated"
            if live_validated
            else "demo-checkpoint-live-validation-ready"
            if source_ready
            else "demo-checkpoint-source-build-ready"
        ),
        "drop_trigger": (
            "V3022 validated the exact V3021 patch-level checkpoint in one resident image: "
            "Bad Apple full-song and Nyan both passed, then rollback to V2321 passed. Resume "
            "WAD-backed DOOM integration as the next frontier."
            if live_validated
            else
            "GOAL.md now requires a patch-level kept Bad Apple + Nyan checkpoint before further "
            "WAD-backed DOOM integration. V3021 has produced the exact source-built image, so the "
            "next bounded unit is same-image live validation and rollback."
            if source_ready
            else "GOAL.md now requires a patch-level kept Bad Apple + Nyan checkpoint before further "
            "WAD-backed DOOM integration; build the checkpoint image first."
        ),
        "evidence": {
            "goal_checkpoint_chartered": True,
            **source,
            **live,
            "next_source_command": (
                "PYTHONPATH=workspace/public/src/scripts/revalidation:workspace/public/src/harness "
                "python3 workspace/public/src/scripts/revalidation/"
                "build_native_init_boot_v3021_demo_checkpoint_badapple_nyan.py"
            ),
            "next_live_scope": (
                "Flash boot_linux_v3021_demo_checkpoint_badapple_nyan.img, validate Bad Apple and "
                "Nyan in the same resident image, health-check, then rollback to V2321."
            ),
        },
    }


def current_doom_input_evaluation(
    report_text: str | None,
    flash_gate_report_text: str | None = None,
    live_precondition_report_text: str | None = None,
    gameplay_loop_report_text: str | None = None,
) -> dict[str, Any] | None:
    gameplay_loop = current_doom_gameplay_loop_evidence(gameplay_loop_report_text)
    if gameplay_loop["v3017_state_consumed"] and gameplay_loop["v3017_rollback_health_ok"]:
        return {
            "track": "VIDEO",
            "name": "doom-capstone",
            "safe_actionable_now": True,
            "status": "doomgeneric-wad-feasibility-host-ready",
            "drop_trigger": (
                "V3017 supersedes the V3012 OTG-keyboard hardware wait: the serial doompad state "
                "is consumed by a bounded foreground KMS gameplay loop and rollback health is clean. "
                "The remaining DOOM gap is WAD-backed doomgeneric/source-asset integration, which "
                "has a safe host-only feasibility/design unit before any flash."
            ),
            "evidence": {
                **gameplay_loop,
                "next_host_only_unit": "doomgeneric/WAD feasibility and asset-policy source audit",
                "next_live_command": None,
            },
        }
    if not report_text:
        return None
    if "v3008-doom-input-frontier-keyboard-gate-still-external-stimulus" not in report_text:
        return None
    saturated = marker_present(report_text, "Active tier saturated without external stimulus: `1`")
    keyboard_gate = marker_present(report_text, "USB keyboard live gate staged: `1`")
    current_actionable = marker_present(report_text, "Current V3007 gate actionable now: `1`")
    flash_gate = current_doom_flash_gate_evidence(flash_gate_report_text)
    live_precondition = current_doom_live_precondition_evidence(live_precondition_report_text)
    safe_actionable_now = bool(current_actionable or live_precondition["v3012_v3004_live_actionable_now"])
    drop_trigger = (
        "V3008 reconciles V2984..V3007: touch capability is proven but touch/button liveness "
        "is not, V3004 USB keyboard/OTG is staged, and current evidence lacks an A90 OTG "
        "keyboard evdev node plus operator DOOM key presses."
    )
    if flash_gate["v3010_flash_gate_assets_ready"]:
        drop_trigger += " V3010 confirms the live-gate flash assets are present and checksum-clean."
    if live_precondition["v3012_host_only_gate_audit_stop"]:
        drop_trigger += (
            " V3012 confirms the resident bridge/health and assets are clean, but A90-side "
            "OTG keyboard evidence is still absent; further host-only gate audits are churn."
        )
    elif live_precondition["v3012_v3004_live_actionable_now"]:
        drop_trigger += " V3012 reports the V3004 live gate is actionable now."
    return {
        "track": "VIDEO",
        "name": "doom-input",
        "safe_actionable_now": safe_actionable_now,
        "status": "keyboard-otg-live-ready" if safe_actionable_now else "external-hardware-stimulus-required",
        "drop_trigger": drop_trigger,
        "evidence": {
            "v3008_reconciliation_present": True,
            "active_tier_saturated_without_external_stimulus": saturated,
            "keyboard_gate_staged": keyboard_gate,
            "current_v3007_gate_actionable": current_actionable,
            **flash_gate,
            **live_precondition,
            **gameplay_loop,
            "next_live_command": (
                "PYTHONPATH=workspace/public/src/scripts/revalidation:workspace/public/src/harness "
                "python3 workspace/public/src/scripts/revalidation/"
                "native_doominput_keyboard_live_gate_v3004.py --live --count 32 --timeout-ms 60000"
            ),
        },
    }


def track_evaluations(
    goal_text: str,
    todo_text: str,
    inventory: dict[str, Any],
    frontier_candidates: dict[str, Any],
    current_doom_report_text: str | None = None,
    current_doom_flash_gate_report_text: str | None = None,
    current_doom_live_precondition_report_text: str | None = None,
    current_doom_gameplay_loop_report_text: str | None = None,
    current_demo_checkpoint_source_report_text: str | None = None,
    current_demo_checkpoint_live_report_text: str | None = None,
) -> list[dict[str, Any]]:
    signals = inventory["consolidation_signals"]
    t1_candidates = ready_t1_candidates(frontier_candidates)
    current_video = current_doom_input_evaluation(
        current_doom_report_text,
        current_doom_flash_gate_report_text,
        current_doom_live_precondition_report_text,
        current_doom_gameplay_loop_report_text,
    )
    current_demo_checkpoint = current_demo_checkpoint_evaluation(
        goal_text,
        current_demo_checkpoint_source_report_text,
        current_demo_checkpoint_live_report_text,
    )
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

    evaluations = [
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
    if current_demo_checkpoint is not None:
        if current_video is not None:
            return [current_demo_checkpoint, current_video, *evaluations]
        return [current_demo_checkpoint, *evaluations]
    if current_video is not None:
        return [current_video, *evaluations]
    return evaluations


def select_frontier() -> dict[str, Any]:
    goal_text = read_text(GOAL_PATH)
    todo_text = read_text(TODO_PATH)
    inventory = read_json(INVENTORY_JSON)
    frontier_candidates = read_json(FRONTIER_CANDIDATES_JSON) if FRONTIER_CANDIDATES_JSON.exists() else {"candidates": []}
    current_doom_report_text = read_optional_text(CURRENT_DOOM_FRONTIER_REPORT)
    current_doom_flash_gate_report_text = read_optional_text(CURRENT_DOOM_FLASH_GATE_REPORT)
    current_doom_live_precondition_report_text = read_optional_text(CURRENT_DOOM_LIVE_PRECONDITION_REPORT)
    current_doom_gameplay_loop_report_text = read_optional_text(CURRENT_DOOM_GAMEPLAY_LOOP_REPORT)
    current_demo_checkpoint_source_report_text = read_optional_text(CURRENT_DEMO_CHECKPOINT_SOURCE_REPORT)
    current_demo_checkpoint_live_report_text = read_optional_text(CURRENT_DEMO_CHECKPOINT_LIVE_REPORT)
    evaluations = track_evaluations(
        goal_text,
        todo_text,
        inventory,
        frontier_candidates,
        current_doom_report_text,
        current_doom_flash_gate_report_text,
        current_doom_live_precondition_report_text,
        current_doom_gameplay_loop_report_text,
        current_demo_checkpoint_source_report_text,
        current_demo_checkpoint_live_report_text,
    )
    actionable = [evaluation for evaluation in evaluations if evaluation["safe_actionable_now"]]
    current_video = current_doom_input_evaluation(
        current_doom_report_text,
        current_doom_flash_gate_report_text,
        current_doom_live_precondition_report_text,
        current_doom_gameplay_loop_report_text,
    )
    current_demo_checkpoint = current_demo_checkpoint_evaluation(
        goal_text,
        current_demo_checkpoint_source_report_text,
        current_demo_checkpoint_live_report_text,
    )
    if current_demo_checkpoint and current_demo_checkpoint["status"] == "demo-checkpoint-live-validation-ready":
        next_operator_decision = (
            "Run the V3022 same-image live checkpoint: flash the exact V3021 image, validate "
            "Bad Apple and Nyan, health-check, then rollback to V2321 before resuming WAD-backed DOOM."
        )
    elif current_demo_checkpoint and current_demo_checkpoint["status"] == "demo-checkpoint-source-build-ready":
        next_operator_decision = (
            "Build the V3021 patch-level Bad Apple + Nyan checkpoint image before further "
            "WAD-backed DOOM integration."
        )
    elif current_video and current_video["status"] == "doomgeneric-wad-feasibility-host-ready":
        next_operator_decision = (
            "Run a host-only doomgeneric/WAD feasibility and asset-policy unit next. Do not flash "
            "a WAD-backed engine until source provenance, boot-size impact, bounded runtime controls, "
            "and rollback validation are pinned."
        )
    elif current_video and not current_video["safe_actionable_now"]:
        evidence = current_video["evidence"]
        if evidence.get("v3012_host_only_gate_audit_stop"):
            next_operator_decision = (
                "V3012 confirms bridge/resident health and live-gate assets are clean, but A90-side "
                "USB keyboard/OTG evidence is still absent; stop DOOM input host-only gate audits "
                "until hardware plus operator key presses are available, then run the V3004 keyboard live gate."
            )
        else:
            attach_clause = (
                "Flash-gate assets are ready; attach"
                if evidence.get("v3010_flash_gate_assets_ready")
                else "Attach"
            )
            next_operator_decision = (
                f"{attach_clause} USB keyboard/OTG to the A90 and provide operator DOOM key presses, "
                "then run the V3004 keyboard live gate; otherwise use T3 host-only tooling only, "
                "not repeat touch/button live flashes."
            )
    elif not actionable:
        next_operator_decision = (
            "Define a new T1 oracle, set a concrete V2254 live-validation criterion beyond V2282, "
            "or revive a historical runner before selecting the next bounded unit."
        )
    else:
        next_operator_decision = "Run the first actionable track through the normal GOAL.md cycle."
    return {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "decision": "frontier-selector-no-automatic-safe-unit" if not actionable else "frontier-selector-actionable-unit-present",
        "selected_track": actionable[0]["track"] if actionable else None,
        "selected_reason": actionable[0]["status"] if actionable else None,
        "track_evaluations": evaluations,
        "next_operator_decision": next_operator_decision,
        "source_paths": {
            "goal": str(GOAL_PATH.relative_to(REPO_ROOT)),
            "todo": str(TODO_PATH.relative_to(REPO_ROOT)),
            "inventory": str(INVENTORY_JSON.relative_to(REPO_ROOT)),
            "frontier_candidates": str(FRONTIER_CANDIDATES_JSON.relative_to(REPO_ROOT)),
            "current_doom_frontier_report": str(CURRENT_DOOM_FRONTIER_REPORT.relative_to(REPO_ROOT)),
            "current_doom_flash_gate_report": str(CURRENT_DOOM_FLASH_GATE_REPORT.relative_to(REPO_ROOT)),
            "current_doom_live_precondition_report": str(CURRENT_DOOM_LIVE_PRECONDITION_REPORT.relative_to(REPO_ROOT)),
            "current_doom_gameplay_loop_report": str(CURRENT_DOOM_GAMEPLAY_LOOP_REPORT.relative_to(REPO_ROOT)),
            "current_demo_checkpoint_source_report": str(CURRENT_DEMO_CHECKPOINT_SOURCE_REPORT.relative_to(REPO_ROOT)),
            "current_demo_checkpoint_live_report": str(CURRENT_DEMO_CHECKPOINT_LIVE_REPORT.relative_to(REPO_ROOT)),
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

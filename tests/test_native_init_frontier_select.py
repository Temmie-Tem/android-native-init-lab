from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from _loader import load_script


frontier = load_script("workspace/public/src/scripts/revalidation/native_init_frontier_select.py")


class NativeInitFrontierSelectTests(unittest.TestCase):
    def test_read_text_and_read_json_load_utf8_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            text_path = root / "goal.md"
            json_path = root / "inventory.json"
            text_path.write_text("native-init ✓", encoding="utf-8")
            json_path.write_text(json.dumps({"k": [1, "two"]}), encoding="utf-8")

            self.assertEqual(frontier.read_text(text_path), "native-init ✓")
            self.assertEqual(frontier.read_json(json_path), {"k": [1, "two"]})
            self.assertIsNone(frontier.read_optional_text(root / "missing.md"))
            self.assertEqual(frontier.read_optional_text(text_path), "native-init ✓")

    def test_marker_helpers_require_literal_markers(self) -> None:
        text = "alpha\nDo not spend more T1 work on generic CPU-clock tuning\nomega"

        self.assertTrue(frontier.marker_present(text, "generic CPU-clock tuning"))
        self.assertFalse(frontier.marker_present(text, "generic gpu tuning"))
        self.assertTrue(frontier.all_markers_present(text, ("alpha", "omega")))
        self.assertFalse(frontier.all_markers_present(text, ("alpha", "missing")))
        self.assertTrue(frontier.all_markers_present(text, ()))

    def test_ready_t1_candidates_filters_exact_ready_safe_t1_rows(self) -> None:
        candidates = {
            "candidates": [
                {"id": "keep", "track": "T1", "safe_actionable_now": True, "status": "ready_for_next_v_iteration"},
                {"id": "wrong-track", "track": "T2", "safe_actionable_now": True, "status": "ready_for_next_v_iteration"},
                {"id": "unsafe", "track": "T1", "safe_actionable_now": False, "status": "ready_for_next_v_iteration"},
                {"id": "review", "track": "T1", "safe_actionable_now": True, "status": "needs_review"},
            ]
        }

        self.assertEqual([row["id"] for row in frontier.ready_t1_candidates(candidates)], ["keep"])
        self.assertEqual(frontier.ready_t1_candidates({}), [])

    def test_track_evaluations_reports_ready_t1_and_closed_cleanup(self) -> None:
        goal_text = (
            "Do not spend more T1 work on generic CPU-clock tuning\n"
            "this firmware_class boundary unless a new independent oracle is identified\n"
        )
        todo_text = (
            "Status: complete for the current `v2254-wifi-detail-surface` baseline.\n"
            "V2282 rollbackably validated V2254 through current-baseline connect, DHCP,\n"
            "V2282 already covers the current 180 second hold/reconnect criterion.\n"
        )
        inventory = {
            "consolidation_signals": {
                "direct_a90ctl_actionable_now_count": 0,
                "direct_a90ctl_review_only_count": 3,
                "direct_a90ctl_next_actionable_group": None,
                "source_delete_review_count": 0,
                "active_live_phase_residual_backlog_closed": True,
            }
        }
        frontier_candidates = {
            "candidates": [
                {"id": "v2280-live", "track": "T1", "safe_actionable_now": True, "status": "ready_for_next_v_iteration"}
            ]
        }

        t1, t2, t3 = frontier.track_evaluations(goal_text, todo_text, inventory, frontier_candidates)

        self.assertEqual(t1["track"], "T1")
        self.assertTrue(t1["safe_actionable_now"])
        self.assertEqual(t1["status"], "new-independent-oracle-ready")
        self.assertEqual(t1["evidence"]["ready_candidate_ids"], ["v2280-live"])
        self.assertTrue(t1["evidence"]["closed_boundary_marker_present"])
        self.assertFalse(t2["safe_actionable_now"])
        self.assertTrue(t2["evidence"]["current_baseline_complete_marker_present"])
        self.assertEqual(t3["status"], "no-cleanup-backlog")
        self.assertFalse(t3["safe_actionable_now"])

    def test_track_evaluations_flags_cleanup_backlog_when_inventory_counts_are_open(self) -> None:
        inventory = {
            "consolidation_signals": {
                "direct_a90ctl_actionable_now_count": 2,
                "direct_a90ctl_review_only_count": 1,
                "direct_a90ctl_next_actionable_group": "legacy-runner",
                "source_delete_review_count": 1,
                "active_live_phase_residual_backlog_closed": False,
            }
        }

        t1, _t2, t3 = frontier.track_evaluations("", "", inventory, {"candidates": []})

        self.assertFalse(t1["safe_actionable_now"])
        self.assertEqual(t1["status"], "defer-until-new-independent-oracle")
        self.assertTrue(t3["safe_actionable_now"])
        self.assertEqual(t3["status"], "inspect-cleanup-backlog")
        self.assertEqual(t3["evidence"]["direct_next_actionable_group"], "legacy-runner")

    def test_current_doom_input_evaluation_reads_v3008_gate(self) -> None:
        report = "\n".join([
            "v3008-doom-input-frontier-keyboard-gate-still-external-stimulus",
            "Active tier saturated without external stimulus: `1`",
            "USB keyboard live gate staged: `1`",
            "Current V3007 gate actionable now: `0`",
        ])

        evaluation = frontier.current_doom_input_evaluation(report)

        self.assertIsNotNone(evaluation)
        assert evaluation is not None
        self.assertEqual(evaluation["track"], "VIDEO")
        self.assertEqual(evaluation["name"], "doom-input")
        self.assertFalse(evaluation["safe_actionable_now"])
        self.assertEqual(evaluation["status"], "external-hardware-stimulus-required")
        self.assertTrue(evaluation["evidence"]["active_tier_saturated_without_external_stimulus"])
        self.assertFalse(evaluation["evidence"]["v3010_flash_gate_report_present"])
        self.assertFalse(evaluation["evidence"]["v3012_live_precondition_report_present"])
        self.assertIn("native_doominput_keyboard_live_gate_v3004.py --live", evaluation["evidence"]["next_live_command"])

    def test_current_doom_input_evaluation_includes_v3010_flash_gate_readiness(self) -> None:
        report = "\n".join([
            "v3008-doom-input-frontier-keyboard-gate-still-external-stimulus",
            "Active tier saturated without external stimulus: `1`",
            "USB keyboard live gate staged: `1`",
            "Current V3007 gate actionable now: `0`",
        ])
        flash_gate_report = "\n".join([
            "v3010-doom-input-flash-gate-assets-ready-hardware-wait",
            "Required assets present: `1`",
            "Expected SHA256 checks pass: `1`",
            "Current gate reports pass: `1`",
            "External hardware wait retained: `1`",
            "V3004 live actionable now: `0`",
        ])

        evaluation = frontier.current_doom_input_evaluation(report, flash_gate_report)

        self.assertIsNotNone(evaluation)
        assert evaluation is not None
        evidence = evaluation["evidence"]
        self.assertFalse(evaluation["safe_actionable_now"])
        self.assertTrue(evidence["v3010_flash_gate_report_present"])
        self.assertTrue(evidence["v3010_flash_gate_assets_ready"])
        self.assertTrue(evidence["v3010_flash_gate_reports_ok"])
        self.assertTrue(evidence["v3010_external_hardware_wait_retained"])
        self.assertFalse(evidence["v3010_v3004_live_actionable_now"])
        self.assertIn("V3010 confirms", evaluation["drop_trigger"])

    def test_current_doom_input_evaluation_includes_v3012_current_precondition_stop(self) -> None:
        report = "\n".join([
            "v3008-doom-input-frontier-keyboard-gate-still-external-stimulus",
            "Active tier saturated without external stimulus: `1`",
            "USB keyboard live gate staged: `1`",
            "Current V3007 gate actionable now: `0`",
        ])
        live_precondition_report = "\n".join([
            "v3012-doom-input-live-precondition-current-hardware-wait",
            "Bridge/control path ready: `1`",
            "Resident selftest fail=0: `1`",
            "V3010 flash-gate assets ready: `1`",
            "V3011 selector external gate retained: `1`",
            "A90 OTG keyboard evdev evidence: `0`",
            "V3004 live actionable now: `0`",
        ])

        evaluation = frontier.current_doom_input_evaluation(report, None, live_precondition_report)

        self.assertIsNotNone(evaluation)
        assert evaluation is not None
        evidence = evaluation["evidence"]
        self.assertFalse(evaluation["safe_actionable_now"])
        self.assertTrue(evidence["v3012_live_precondition_report_present"])
        self.assertTrue(evidence["v3012_resident_health_ok"])
        self.assertTrue(evidence["v3012_gate_assets_ready"])
        self.assertTrue(evidence["v3012_external_gate_retained"])
        self.assertFalse(evidence["v3012_a90_otg_keyboard_evidence"])
        self.assertFalse(evidence["v3012_v3004_live_actionable_now"])
        self.assertTrue(evidence["v3012_host_only_gate_audit_stop"])
        self.assertIn("further host-only gate audits are churn", evaluation["drop_trigger"])

    def test_current_doom_flash_gate_evidence_rejects_incomplete_report(self) -> None:
        evidence = frontier.current_doom_flash_gate_evidence("Required assets present: `1`")

        self.assertTrue(evidence["v3010_flash_gate_report_present"])
        self.assertFalse(evidence["v3010_flash_gate_assets_ready"])
        self.assertFalse(evidence["v3010_flash_gate_reports_ok"])
        self.assertEqual(evidence["v3010_flash_gate_decision"], "v3010-doom-input-flash-gate-assets-not-ready")

    def test_current_doom_live_precondition_evidence_rejects_incomplete_report(self) -> None:
        evidence = frontier.current_doom_live_precondition_evidence("Bridge/control path ready: `1`")

        self.assertTrue(evidence["v3012_live_precondition_report_present"])
        self.assertFalse(evidence["v3012_resident_health_ok"])
        self.assertFalse(evidence["v3012_gate_assets_ready"])
        self.assertFalse(evidence["v3012_host_only_gate_audit_stop"])
        self.assertEqual(
            evidence["v3012_live_precondition_decision"],
            "v3012-doom-input-live-precondition-current-blocked",
        )

    def test_current_doom_gameplay_loop_evidence_reads_v3017_pass(self) -> None:
        report = "\n".join([
            "v3017-doompad-gameplay-loop-state-consumed-pass-before-rollback",
            "`video demo doom play 8` rc: `0` markers_ok=`1`",
            "Player movement parsed: `1` moved_forward=`1`",
            "Rollback health: version_ok=`1` selftest_fail0=`1`",
            "not a WAD-backed `doomgeneric` engine",
        ])

        evidence = frontier.current_doom_gameplay_loop_evidence(report)

        self.assertTrue(evidence["v3017_gameplay_loop_report_present"])
        self.assertTrue(evidence["v3017_state_consumed"])
        self.assertTrue(evidence["v3017_doomplay_rc_ok"])
        self.assertTrue(evidence["v3017_doomplay_markers_ok"])
        self.assertTrue(evidence["v3017_player_moved_forward"])
        self.assertTrue(evidence["v3017_rollback_health_ok"])
        self.assertTrue(evidence["v3017_not_wad_backed"])

    def test_current_doom_input_evaluation_prefers_v3017_gameplay_loop_frontier(self) -> None:
        stale_report = "\n".join([
            "v3008-doom-input-frontier-keyboard-gate-still-external-stimulus",
            "Active tier saturated without external stimulus: `1`",
            "USB keyboard live gate staged: `1`",
            "Current V3007 gate actionable now: `0`",
        ])
        gameplay_report = "\n".join([
            "v3017-doompad-gameplay-loop-state-consumed-pass-before-rollback",
            "`video demo doom play 8` rc: `0` markers_ok=`1`",
            "Player movement parsed: `1` moved_forward=`1`",
            "Rollback health: version_ok=`1` selftest_fail0=`1`",
            "not a WAD-backed `doomgeneric` engine",
        ])

        evaluation = frontier.current_doom_input_evaluation(stale_report, gameplay_loop_report_text=gameplay_report)

        self.assertIsNotNone(evaluation)
        assert evaluation is not None
        self.assertEqual(evaluation["track"], "VIDEO")
        self.assertEqual(evaluation["name"], "doom-capstone")
        self.assertTrue(evaluation["safe_actionable_now"])
        self.assertEqual(evaluation["status"], "doomgeneric-wad-feasibility-host-ready")
        self.assertTrue(evaluation["evidence"]["v3017_state_consumed"])
        self.assertIn("V3017 supersedes", evaluation["drop_trigger"])

    def test_current_doomgeneric_policy_evidence_reads_v3023_pass(self) -> None:
        report = "\n".join([
            "v3023-doomgeneric-private-integration-policy-ready",
            "Private doomgeneric source pinned: `1`",
            "Private source clean: `1`",
            "V3020 port probe pass: `1`",
            "V3022 checkpoint live pass retained: `1`",
            "Public WAD files committed/present: `0`",
            "Runtime WAD currently staged: `0`",
            "Safe next host-only unit: `1`",
            "Run ID: `V3024`",
        ])

        evidence = frontier.current_doomgeneric_policy_evidence(report)

        self.assertTrue(evidence["v3023_policy_report_present"])
        self.assertTrue(evidence["v3023_policy_ready"])
        self.assertTrue(evidence["v3023_source_pinned"])
        self.assertTrue(evidence["v3023_source_clean"])
        self.assertTrue(evidence["v3023_no_public_wad"])
        self.assertFalse(evidence["v3023_runtime_wad_staged"])
        self.assertEqual(evidence["v3023_next_run_id"], "V3024")

    def test_current_doom_input_evaluation_uses_v3023_policy_next_unit(self) -> None:
        gameplay_report = "\n".join([
            "v3017-doompad-gameplay-loop-state-consumed-pass-before-rollback",
            "`video demo doom play 8` rc: `0` markers_ok=`1`",
            "Player movement parsed: `1` moved_forward=`1`",
            "Rollback health: version_ok=`1` selftest_fail0=`1`",
            "not a WAD-backed `doomgeneric` engine",
        ])
        policy_report = "\n".join([
            "v3023-doomgeneric-private-integration-policy-ready",
            "Private doomgeneric source pinned: `1`",
            "Private source clean: `1`",
            "V3020 port probe pass: `1`",
            "V3022 checkpoint live pass retained: `1`",
            "Public WAD files committed/present: `0`",
            "Safe next host-only unit: `1`",
            "Run ID: `V3024`",
        ])

        evaluation = frontier.current_doom_input_evaluation(
            None,
            gameplay_loop_report_text=gameplay_report,
            doomgeneric_policy_report_text=policy_report,
        )

        self.assertIsNotNone(evaluation)
        assert evaluation is not None
        self.assertEqual(evaluation["track"], "VIDEO")
        self.assertEqual(evaluation["name"], "doom-capstone")
        self.assertTrue(evaluation["safe_actionable_now"])
        self.assertEqual(evaluation["status"], "doomgeneric-private-source-integration-build-ready")
        self.assertTrue(evaluation["evidence"]["v3023_policy_ready"])
        self.assertIn("V3024 private-source", evaluation["evidence"]["next_host_only_unit"])

    def test_current_doomgeneric_private_build_evidence_reads_v3024_pass(self) -> None:
        report = "\n".join([
            "v3024-doomgeneric-private-full-engine-link-pass",
            "Private engine source files compiled: `80`",
            "AArch64 static engine linked: `1`",
            "Marker check pass: `1`",
            "Public WAD files committed/present: `0`",
            "Engine-only object total within V3023 2 MiB cap: `1`",
            "Boot-image delta: `not-produced`",
            "Run ID: `V3025`",
        ])

        evidence = frontier.current_doomgeneric_private_build_evidence(report)

        self.assertTrue(evidence["v3024_private_build_report_present"])
        self.assertTrue(evidence["v3024_private_build_ready"])
        self.assertTrue(evidence["v3024_private_source_compiled"])
        self.assertTrue(evidence["v3024_aarch64_static_engine_linked"])
        self.assertTrue(evidence["v3024_marker_check_pass"])
        self.assertTrue(evidence["v3024_no_public_wad"])
        self.assertTrue(evidence["v3024_boot_image_not_produced"])
        self.assertTrue(evidence["v3024_size_cap_pass"])
        self.assertEqual(evidence["v3024_next_run_id"], "V3025")

    def test_current_demo_checkpoint_evaluation_reads_v3021_source_ready(self) -> None:
        goal = "\n".join([
            'PATCH-level kept "demo checkpoint"',
            "**Bad Apple + Nyan** demos",
            "**0.11.0 (MINOR) is RESERVED",
        ])
        source_report = "\n".join([
            "v3021-demo-checkpoint-badapple-nyan-source-build-pass",
            "Boot SHA256: `c860d604e3c906abf61fdd2c9bd9cd12d1aef2c88c05be57677b472ad36ef0f7`",
            "Bad Apple asset ID: `badapple-480x360-full-v2903`",
            "menu.demo.badapple.action=play-av-fullsong",
            "menu.demo.badapple.frames=6962",
            "Nyan asset ID: `nyancat-v2973-pal8-rle-preview`",
            "menu.demo.nyan.action=play-av-preview",
            "pal8-rle",
            "pending-badapple-nyan-same-image-live-validation",
        ])

        evaluation = frontier.current_demo_checkpoint_evaluation(goal, source_report)

        self.assertIsNotNone(evaluation)
        assert evaluation is not None
        self.assertEqual(evaluation["track"], "VIDEO")
        self.assertEqual(evaluation["name"], "demo-checkpoint")
        self.assertTrue(evaluation["safe_actionable_now"])
        self.assertEqual(evaluation["status"], "demo-checkpoint-live-validation-ready")
        self.assertTrue(evaluation["evidence"]["v3021_source_build_pass"])
        self.assertIn("same resident image", evaluation["evidence"]["next_live_scope"])

    def test_track_evaluations_prioritizes_current_video_doom_gate(self) -> None:
        inventory = {
            "consolidation_signals": {
                "direct_a90ctl_actionable_now_count": 0,
                "direct_a90ctl_review_only_count": 0,
                "direct_a90ctl_next_actionable_group": None,
                "source_delete_review_count": 0,
                "active_live_phase_residual_backlog_closed": True,
            }
        }
        report = "\n".join([
            "v3008-doom-input-frontier-keyboard-gate-still-external-stimulus",
            "Active tier saturated without external stimulus: `1`",
            "USB keyboard live gate staged: `1`",
            "Current V3007 gate actionable now: `0`",
        ])

        evaluations = frontier.track_evaluations("", "", inventory, {"candidates": []}, report)

        self.assertEqual(evaluations[0]["track"], "VIDEO")
        self.assertEqual(evaluations[0]["status"], "external-hardware-stimulus-required")
        self.assertEqual(evaluations[1]["track"], "T1")

    def test_select_frontier_uses_missing_frontier_file_as_empty_candidates(self) -> None:
        with self._fake_repo(
            inventory_signals={
                "direct_a90ctl_actionable_now_count": 0,
                "direct_a90ctl_review_only_count": 0,
                "direct_a90ctl_next_actionable_group": None,
                "source_delete_review_count": 0,
                "active_live_phase_residual_backlog_closed": True,
            },
            frontier_candidates=None,
        ) as paths:
            with self._patch_paths(paths):
                result = frontier.select_frontier()

        self.assertEqual(result["decision"], "frontier-selector-no-automatic-safe-unit")
        self.assertIsNone(result["selected_track"])
        self.assertEqual(result["source_paths"]["goal"], "GOAL.md")
        self.assertEqual(result["source_paths"]["frontier_candidates"], "docs/artifacts/native-init-frontier-candidates.json")
        self.assertEqual(result["source_paths"]["current_doom_frontier_report"], "docs/reports/NATIVE_INIT_V3008_DOOM_INPUT_FRONTIER_RECONCILIATION_2026-06-20.md")
        self.assertEqual(result["source_paths"]["current_doom_flash_gate_report"], "docs/reports/NATIVE_INIT_V3010_DOOM_INPUT_FLASH_GATE_ASSETS_2026-06-20.md")
        self.assertEqual(result["source_paths"]["current_doom_live_precondition_report"], "docs/reports/NATIVE_INIT_V3012_DOOM_INPUT_LIVE_PRECONDITION_CURRENT_2026-06-20.md")
        self.assertEqual(result["source_paths"]["current_doom_gameplay_loop_report"], "docs/reports/NATIVE_INIT_V3017_DOOMPAD_GAMEPLAY_LOOP_LIVE_2026-06-21.md")
        self.assertEqual(result["source_paths"]["current_demo_checkpoint_source_report"], "docs/reports/NATIVE_INIT_V3021_DEMO_CHECKPOINT_BADAPPLE_NYAN_SOURCE_BUILD_2026-06-21.md")
        self.assertEqual(result["source_paths"]["current_demo_checkpoint_live_report"], "docs/reports/NATIVE_INIT_V3022_DEMO_CHECKPOINT_BADAPPLE_NYAN_LIVE_2026-06-21.md")
        self.assertEqual(result["source_paths"]["current_doomgeneric_policy_report"], "docs/reports/NATIVE_INIT_V3023_DOOMGENERIC_INTEGRATION_POLICY_2026-06-21.md")
        self.assertEqual(result["source_paths"]["current_doomgeneric_private_build_report"], "docs/reports/NATIVE_INIT_V3024_DOOMGENERIC_PRIVATE_INTEGRATION_BUILD_2026-06-21.md")
        self.assertEqual(result["source_paths"]["current_doomgeneric_command_bridge_report"], "docs/reports/NATIVE_INIT_V3025_DOOMGENERIC_COMMAND_BRIDGE_SOURCE_BUILD_2026-06-21.md")
        self.assertEqual(result["source_paths"]["current_doomgeneric_visible_frame_report"], "docs/reports/NATIVE_INIT_V3031_DOOMGENERIC_VISIBLE_FRAME_SOURCE_BUILD_2026-06-22.md")

    def test_select_frontier_selects_first_actionable_track(self) -> None:
        with self._fake_repo(
            inventory_signals={
                "direct_a90ctl_actionable_now_count": 5,
                "direct_a90ctl_review_only_count": 0,
                "direct_a90ctl_next_actionable_group": "cleanup",
                "source_delete_review_count": 1,
                "active_live_phase_residual_backlog_closed": False,
            },
            frontier_candidates={
                "candidates": [
                    {"id": "t1-ready", "track": "T1", "safe_actionable_now": True, "status": "ready_for_next_v_iteration"}
                ]
            },
        ) as paths:
            with self._patch_paths(paths):
                result = frontier.select_frontier()

        self.assertEqual(result["decision"], "frontier-selector-actionable-unit-present")
        self.assertEqual(result["selected_track"], "T1")
        self.assertEqual(result["selected_reason"], "new-independent-oracle-ready")
        self.assertEqual(result["track_evaluations"][0]["evidence"]["ready_candidate_ids"], ["t1-ready"])

    def test_select_frontier_reports_current_doom_gate_when_v3008_exists(self) -> None:
        with self._fake_repo(
            inventory_signals={
                "direct_a90ctl_actionable_now_count": 0,
                "direct_a90ctl_review_only_count": 0,
                "direct_a90ctl_next_actionable_group": None,
                "source_delete_review_count": 0,
                "active_live_phase_residual_backlog_closed": True,
            },
            frontier_candidates=None,
            current_doom_report="\n".join([
                "v3008-doom-input-frontier-keyboard-gate-still-external-stimulus",
                "Active tier saturated without external stimulus: `1`",
                "USB keyboard live gate staged: `1`",
                "Current V3007 gate actionable now: `0`",
            ]),
        ) as paths:
            with self._patch_paths(paths):
                result = frontier.select_frontier()

        self.assertEqual(result["decision"], "frontier-selector-no-automatic-safe-unit")
        self.assertEqual(result["track_evaluations"][0]["track"], "VIDEO")
        self.assertEqual(result["track_evaluations"][0]["status"], "external-hardware-stimulus-required")
        self.assertIn("Attach USB keyboard/OTG", result["next_operator_decision"])

    def test_select_frontier_reports_v3010_flash_gate_assets_ready(self) -> None:
        with self._fake_repo(
            inventory_signals={
                "direct_a90ctl_actionable_now_count": 0,
                "direct_a90ctl_review_only_count": 0,
                "direct_a90ctl_next_actionable_group": None,
                "source_delete_review_count": 0,
                "active_live_phase_residual_backlog_closed": True,
            },
            frontier_candidates=None,
            current_doom_report="\n".join([
                "v3008-doom-input-frontier-keyboard-gate-still-external-stimulus",
                "Active tier saturated without external stimulus: `1`",
                "USB keyboard live gate staged: `1`",
                "Current V3007 gate actionable now: `0`",
            ]),
            current_doom_flash_gate_report="\n".join([
                "v3010-doom-input-flash-gate-assets-ready-hardware-wait",
                "Required assets present: `1`",
                "Expected SHA256 checks pass: `1`",
                "Current gate reports pass: `1`",
                "External hardware wait retained: `1`",
                "V3004 live actionable now: `0`",
            ]),
        ) as paths:
            with self._patch_paths(paths):
                result = frontier.select_frontier()

        self.assertEqual(result["decision"], "frontier-selector-no-automatic-safe-unit")
        evidence = result["track_evaluations"][0]["evidence"]
        self.assertTrue(evidence["v3010_flash_gate_assets_ready"])
        self.assertIn("Flash-gate assets are ready", result["next_operator_decision"])

    def test_select_frontier_reports_v3012_current_precondition_anti_churn_stop(self) -> None:
        with self._fake_repo(
            inventory_signals={
                "direct_a90ctl_actionable_now_count": 0,
                "direct_a90ctl_review_only_count": 0,
                "direct_a90ctl_next_actionable_group": None,
                "source_delete_review_count": 0,
                "active_live_phase_residual_backlog_closed": True,
            },
            frontier_candidates=None,
            current_doom_report="\n".join([
                "v3008-doom-input-frontier-keyboard-gate-still-external-stimulus",
                "Active tier saturated without external stimulus: `1`",
                "USB keyboard live gate staged: `1`",
                "Current V3007 gate actionable now: `0`",
            ]),
            current_doom_flash_gate_report="\n".join([
                "v3010-doom-input-flash-gate-assets-ready-hardware-wait",
                "Required assets present: `1`",
                "Expected SHA256 checks pass: `1`",
                "Current gate reports pass: `1`",
                "External hardware wait retained: `1`",
                "V3004 live actionable now: `0`",
            ]),
            current_doom_live_precondition_report="\n".join([
                "v3012-doom-input-live-precondition-current-hardware-wait",
                "Bridge/control path ready: `1`",
                "Resident selftest fail=0: `1`",
                "V3010 flash-gate assets ready: `1`",
                "V3011 selector external gate retained: `1`",
                "A90 OTG keyboard evdev evidence: `0`",
                "V3004 live actionable now: `0`",
            ]),
        ) as paths:
            with self._patch_paths(paths):
                result = frontier.select_frontier()

        self.assertEqual(result["decision"], "frontier-selector-no-automatic-safe-unit")
        evidence = result["track_evaluations"][0]["evidence"]
        self.assertTrue(evidence["v3012_host_only_gate_audit_stop"])
        self.assertIn("stop DOOM input host-only gate audits", result["next_operator_decision"])

    def test_select_frontier_selects_v3017_gameplay_loop_next_host_unit(self) -> None:
        with self._fake_repo(
            inventory_signals={
                "direct_a90ctl_actionable_now_count": 0,
                "direct_a90ctl_review_only_count": 0,
                "direct_a90ctl_next_actionable_group": None,
                "source_delete_review_count": 0,
                "active_live_phase_residual_backlog_closed": True,
            },
            frontier_candidates=None,
            current_doom_report="\n".join([
                "v3008-doom-input-frontier-keyboard-gate-still-external-stimulus",
                "Active tier saturated without external stimulus: `1`",
                "USB keyboard live gate staged: `1`",
                "Current V3007 gate actionable now: `0`",
            ]),
            current_doom_live_precondition_report="\n".join([
                "v3012-doom-input-live-precondition-current-hardware-wait",
                "Bridge/control path ready: `1`",
                "Resident selftest fail=0: `1`",
                "V3010 flash-gate assets ready: `1`",
                "V3011 selector external gate retained: `1`",
                "A90 OTG keyboard evdev evidence: `0`",
                "V3004 live actionable now: `0`",
            ]),
            current_doom_gameplay_loop_report="\n".join([
                "v3017-doompad-gameplay-loop-state-consumed-pass-before-rollback",
                "`video demo doom play 8` rc: `0` markers_ok=`1`",
                "Player movement parsed: `1` moved_forward=`1`",
                "Rollback health: version_ok=`1` selftest_fail0=`1`",
                "not a WAD-backed `doomgeneric` engine",
            ]),
        ) as paths:
            with self._patch_paths(paths):
                result = frontier.select_frontier()

        self.assertEqual(result["decision"], "frontier-selector-actionable-unit-present")
        self.assertEqual(result["selected_track"], "VIDEO")
        self.assertEqual(result["selected_reason"], "doomgeneric-wad-feasibility-host-ready")
        self.assertEqual(result["track_evaluations"][0]["name"], "doom-capstone")
        self.assertIn("doomgeneric/WAD feasibility", result["next_operator_decision"])

    def test_select_frontier_prioritizes_v3021_demo_checkpoint_live_gate(self) -> None:
        with self._fake_repo(
            goal_text="\n".join([
                'PATCH-level kept "demo checkpoint"',
                "**Bad Apple + Nyan** demos",
                "**0.11.0 (MINOR) is RESERVED",
            ]),
            inventory_signals={
                "direct_a90ctl_actionable_now_count": 0,
                "direct_a90ctl_review_only_count": 0,
                "direct_a90ctl_next_actionable_group": None,
                "source_delete_review_count": 0,
                "active_live_phase_residual_backlog_closed": True,
            },
            frontier_candidates=None,
            current_doom_gameplay_loop_report="\n".join([
                "v3017-doompad-gameplay-loop-state-consumed-pass-before-rollback",
                "`video demo doom play 8` rc: `0` markers_ok=`1`",
                "Player movement parsed: `1` moved_forward=`1`",
                "Rollback health: version_ok=`1` selftest_fail0=`1`",
                "not a WAD-backed `doomgeneric` engine",
            ]),
            current_demo_checkpoint_source_report="\n".join([
                "v3021-demo-checkpoint-badapple-nyan-source-build-pass",
                "Boot SHA256: `c860d604e3c906abf61fdd2c9bd9cd12d1aef2c88c05be57677b472ad36ef0f7`",
                "Bad Apple asset ID: `badapple-480x360-full-v2903`",
                "menu.demo.badapple.action=play-av-fullsong",
                "menu.demo.badapple.frames=6962",
                "Nyan asset ID: `nyancat-v2973-pal8-rle-preview`",
                "menu.demo.nyan.action=play-av-preview",
                "pal8-rle",
                "pending-badapple-nyan-same-image-live-validation",
            ]),
        ) as paths:
            with self._patch_paths(paths):
                result = frontier.select_frontier()

        self.assertEqual(result["decision"], "frontier-selector-actionable-unit-present")
        self.assertEqual(result["selected_track"], "VIDEO")
        self.assertEqual(result["selected_reason"], "demo-checkpoint-live-validation-ready")
        self.assertEqual(result["track_evaluations"][0]["name"], "demo-checkpoint")
        self.assertEqual(result["track_evaluations"][1]["name"], "doom-capstone")
        self.assertIn("V3022 same-image live checkpoint", result["next_operator_decision"])

    def test_select_frontier_resumes_doom_after_v3022_demo_checkpoint_validated(self) -> None:
        with self._fake_repo(
            goal_text="\n".join([
                'PATCH-level kept "demo checkpoint"',
                "**Bad Apple + Nyan** demos",
                "**0.11.0 (MINOR) is RESERVED",
            ]),
            inventory_signals={
                "direct_a90ctl_actionable_now_count": 0,
                "direct_a90ctl_review_only_count": 0,
                "direct_a90ctl_next_actionable_group": None,
                "source_delete_review_count": 0,
                "active_live_phase_residual_backlog_closed": True,
            },
            frontier_candidates=None,
            current_doom_gameplay_loop_report="\n".join([
                "v3017-doompad-gameplay-loop-state-consumed-pass-before-rollback",
                "`video demo doom play 8` rc: `0` markers_ok=`1`",
                "Player movement parsed: `1` moved_forward=`1`",
                "Rollback health: version_ok=`1` selftest_fail0=`1`",
                "not a WAD-backed `doomgeneric` engine",
            ]),
            current_demo_checkpoint_source_report="\n".join([
                "v3021-demo-checkpoint-badapple-nyan-source-build-pass",
                "Boot SHA256: `c860d604e3c906abf61fdd2c9bd9cd12d1aef2c88c05be57677b472ad36ef0f7`",
                "Bad Apple asset ID: `badapple-480x360-full-v2903`",
                "menu.demo.badapple.action=play-av-fullsong",
                "menu.demo.badapple.frames=6962",
                "Nyan asset ID: `nyancat-v2973-pal8-rle-preview`",
                "menu.demo.nyan.action=play-av-preview",
                "pal8-rle",
                "pending-badapple-nyan-same-image-live-validation",
            ]),
            current_demo_checkpoint_live_report="\n".join([
                "v3022-demo-checkpoint-badapple-nyan-same-image-live-pass-before-rollback",
                "Same-image validation: Bad Apple pass=`1` Nyan pass=`1`",
                "Rollback health: version_ok=`1` selftest_fail0=`1`",
            ]),
        ) as paths:
            with self._patch_paths(paths):
                result = frontier.select_frontier()

        self.assertEqual(result["decision"], "frontier-selector-actionable-unit-present")
        self.assertEqual(result["selected_track"], "VIDEO")
        self.assertEqual(result["selected_reason"], "doomgeneric-wad-feasibility-host-ready")
        self.assertEqual(result["track_evaluations"][0]["name"], "demo-checkpoint")
        self.assertEqual(result["track_evaluations"][0]["status"], "demo-checkpoint-live-validated")
        self.assertFalse(result["track_evaluations"][0]["safe_actionable_now"])
        self.assertEqual(result["track_evaluations"][1]["name"], "doom-capstone")
        self.assertIn("doomgeneric/WAD feasibility", result["next_operator_decision"])

    def test_select_frontier_uses_v3023_policy_for_v3024_private_source_build(self) -> None:
        with self._fake_repo(
            goal_text="\n".join([
                'PATCH-level kept "demo checkpoint"',
                "**Bad Apple + Nyan** demos",
                "**0.11.0 (MINOR) is RESERVED",
            ]),
            inventory_signals={
                "direct_a90ctl_actionable_now_count": 0,
                "direct_a90ctl_review_only_count": 0,
                "direct_a90ctl_next_actionable_group": None,
                "source_delete_review_count": 0,
                "active_live_phase_residual_backlog_closed": True,
            },
            frontier_candidates=None,
            current_doom_gameplay_loop_report="\n".join([
                "v3017-doompad-gameplay-loop-state-consumed-pass-before-rollback",
                "`video demo doom play 8` rc: `0` markers_ok=`1`",
                "Player movement parsed: `1` moved_forward=`1`",
                "Rollback health: version_ok=`1` selftest_fail0=`1`",
                "not a WAD-backed `doomgeneric` engine",
            ]),
            current_demo_checkpoint_source_report="\n".join([
                "v3021-demo-checkpoint-badapple-nyan-source-build-pass",
                "Boot SHA256: `c860d604e3c906abf61fdd2c9bd9cd12d1aef2c88c05be57677b472ad36ef0f7`",
                "Bad Apple asset ID: `badapple-480x360-full-v2903`",
                "menu.demo.badapple.action=play-av-fullsong",
                "menu.demo.badapple.frames=6962",
                "Nyan asset ID: `nyancat-v2973-pal8-rle-preview`",
                "menu.demo.nyan.action=play-av-preview",
                "pal8-rle",
                "pending-badapple-nyan-same-image-live-validation",
            ]),
            current_demo_checkpoint_live_report="\n".join([
                "v3022-demo-checkpoint-badapple-nyan-same-image-live-pass-before-rollback",
                "Same-image validation: Bad Apple pass=`1` Nyan pass=`1`",
                "Rollback health: version_ok=`1` selftest_fail0=`1`",
            ]),
            current_doomgeneric_policy_report="\n".join([
                "v3023-doomgeneric-private-integration-policy-ready",
                "Private doomgeneric source pinned: `1`",
                "Private source clean: `1`",
                "V3020 port probe pass: `1`",
                "V3022 checkpoint live pass retained: `1`",
                "Public WAD files committed/present: `0`",
                "Runtime WAD currently staged: `0`",
                "Safe next host-only unit: `1`",
                "Run ID: `V3024`",
            ]),
        ) as paths:
            with self._patch_paths(paths):
                result = frontier.select_frontier()

        self.assertEqual(result["decision"], "frontier-selector-actionable-unit-present")
        self.assertEqual(result["selected_track"], "VIDEO")
        self.assertEqual(result["selected_reason"], "doomgeneric-private-source-integration-build-ready")
        self.assertEqual(result["track_evaluations"][1]["name"], "doom-capstone")
        self.assertTrue(result["track_evaluations"][1]["evidence"]["v3023_policy_ready"])
        self.assertIn("V3024 host-only private-source", result["next_operator_decision"])

    def test_select_frontier_uses_v3024_private_build_for_v3025_boot_candidate(self) -> None:
        with self._fake_repo(
            goal_text="\n".join([
                'PATCH-level kept "demo checkpoint"',
                "**Bad Apple + Nyan** demos",
                "**0.11.0 (MINOR) is RESERVED",
            ]),
            inventory_signals={
                "direct_a90ctl_actionable_now_count": 0,
                "direct_a90ctl_review_only_count": 0,
                "direct_a90ctl_next_actionable_group": None,
                "source_delete_review_count": 0,
                "active_live_phase_residual_backlog_closed": True,
            },
            frontier_candidates=None,
            current_doom_gameplay_loop_report="\n".join([
                "v3017-doompad-gameplay-loop-state-consumed-pass-before-rollback",
                "`video demo doom play 8` rc: `0` markers_ok=`1`",
                "Player movement parsed: `1` moved_forward=`1`",
                "Rollback health: version_ok=`1` selftest_fail0=`1`",
                "not a WAD-backed `doomgeneric` engine",
            ]),
            current_demo_checkpoint_source_report="\n".join([
                "v3021-demo-checkpoint-badapple-nyan-source-build-pass",
                "Boot SHA256: `c860d604e3c906abf61fdd2c9bd9cd12d1aef2c88c05be57677b472ad36ef0f7`",
                "Bad Apple asset ID: `badapple-480x360-full-v2903`",
                "menu.demo.badapple.action=play-av-fullsong",
                "menu.demo.badapple.frames=6962",
                "Nyan asset ID: `nyancat-v2973-pal8-rle-preview`",
                "menu.demo.nyan.action=play-av-preview",
                "pal8-rle",
                "pending-badapple-nyan-same-image-live-validation",
            ]),
            current_demo_checkpoint_live_report="\n".join([
                "v3022-demo-checkpoint-badapple-nyan-same-image-live-pass-before-rollback",
                "Same-image validation: Bad Apple pass=`1` Nyan pass=`1`",
                "Rollback health: version_ok=`1` selftest_fail0=`1`",
            ]),
            current_doomgeneric_policy_report="\n".join([
                "v3023-doomgeneric-private-integration-policy-ready",
                "Private doomgeneric source pinned: `1`",
                "Private source clean: `1`",
                "V3020 port probe pass: `1`",
                "V3022 checkpoint live pass retained: `1`",
                "Public WAD files committed/present: `0`",
                "Safe next host-only unit: `1`",
                "Run ID: `V3024`",
            ]),
            current_doomgeneric_private_build_report="\n".join([
                "v3024-doomgeneric-private-full-engine-link-pass",
                "Private engine source files compiled: `80`",
                "AArch64 static engine linked: `1`",
                "Marker check pass: `1`",
                "Public WAD files committed/present: `0`",
                "Engine-only object total within V3023 2 MiB cap: `1`",
                "Boot-image delta: `not-produced`",
                "Run ID: `V3025`",
            ]),
        ) as paths:
            with self._patch_paths(paths):
                result = frontier.select_frontier()

        self.assertEqual(result["decision"], "frontier-selector-actionable-unit-present")
        self.assertEqual(result["selected_track"], "VIDEO")
        self.assertEqual(result["selected_reason"], "doomgeneric-native-command-boot-integration-ready")
        self.assertEqual(result["track_evaluations"][1]["name"], "doom-capstone")
        self.assertTrue(result["track_evaluations"][1]["evidence"]["v3024_private_build_ready"])
        self.assertIn("V3025 host-only native-init", result["next_operator_decision"])

    def test_current_doomgeneric_command_bridge_evidence_reads_v3025_pass(self) -> None:
        report = "\n".join([
            "v3025-doomgeneric-command-bridge-source-build-pass",
            "Boot SHA256: `boot-sha`",
            "V3024 engine SHA256: `8b6630498b7ff217e6ad9b27593f89644ba73eb7cbbf11361838972f15581735`",
            "Helper bundled in ramdisk: `1`",
            "WAD files in ramdisk: `0`",
            "video demo doom engine-probe",
            "serial-doompad-to-DG_GetKey",
            "video.demo.input.otg_required=0",
            "Run ID: `V3026`",
        ])

        evidence = frontier.current_doomgeneric_command_bridge_evidence(report)

        self.assertTrue(evidence["v3025_command_bridge_report_present"])
        self.assertTrue(evidence["v3025_command_bridge_ready"])
        self.assertTrue(evidence["v3025_helper_bundled"])
        self.assertTrue(evidence["v3025_ramdisk_wad_zero"])
        self.assertTrue(evidence["v3025_engine_probe_command"])
        self.assertTrue(evidence["v3025_no_otg_required"])
        self.assertEqual(evidence["v3025_next_run_id"], "V3026")

    def test_select_frontier_uses_v3025_command_bridge_for_v3026_live_validation(self) -> None:
        with self._fake_repo(
            goal_text="\n".join([
                'PATCH-level kept "demo checkpoint"',
                "**Bad Apple + Nyan** demos",
                "**0.11.0 (MINOR) is RESERVED",
            ]),
            inventory_signals={
                "direct_a90ctl_actionable_now_count": 0,
                "direct_a90ctl_review_only_count": 0,
                "direct_a90ctl_next_actionable_group": None,
                "source_delete_review_count": 0,
                "active_live_phase_residual_backlog_closed": True,
            },
            frontier_candidates=None,
            current_doom_gameplay_loop_report="\n".join([
                "v3017-doompad-gameplay-loop-state-consumed-pass-before-rollback",
                "`video demo doom play 8` rc: `0` markers_ok=`1`",
                "Player movement parsed: `1` moved_forward=`1`",
                "Rollback health: version_ok=`1` selftest_fail0=`1`",
                "not a WAD-backed `doomgeneric` engine",
            ]),
            current_demo_checkpoint_source_report="\n".join([
                "v3021-demo-checkpoint-badapple-nyan-source-build-pass",
                "Boot SHA256: `c860d604e3c906abf61fdd2c9bd9cd12d1aef2c88c05be57677b472ad36ef0f7`",
                "Bad Apple asset ID: `badapple-480x360-full-v2903`",
                "menu.demo.badapple.action=play-av-fullsong",
                "menu.demo.badapple.frames=6962",
                "Nyan asset ID: `nyancat-v2973-pal8-rle-preview`",
                "menu.demo.nyan.action=play-av-preview",
                "pal8-rle",
                "pending-badapple-nyan-same-image-live-validation",
            ]),
            current_demo_checkpoint_live_report="\n".join([
                "v3022-demo-checkpoint-badapple-nyan-same-image-live-pass-before-rollback",
                "Same-image validation: Bad Apple pass=`1` Nyan pass=`1`",
                "Rollback health: version_ok=`1` selftest_fail0=`1`",
            ]),
            current_doomgeneric_policy_report="\n".join([
                "v3023-doomgeneric-private-integration-policy-ready",
                "Private doomgeneric source pinned: `1`",
                "Private source clean: `1`",
                "V3020 port probe pass: `1`",
                "V3022 checkpoint live pass retained: `1`",
                "Public WAD files committed/present: `0`",
                "Safe next host-only unit: `1`",
                "Run ID: `V3024`",
            ]),
            current_doomgeneric_private_build_report="\n".join([
                "v3024-doomgeneric-private-full-engine-link-pass",
                "Private engine source files compiled: `80`",
                "AArch64 static engine linked: `1`",
                "Marker check pass: `1`",
                "Public WAD files committed/present: `0`",
                "Engine-only object total within V3023 2 MiB cap: `1`",
                "Boot-image delta: `not-produced`",
                "Run ID: `V3025`",
            ]),
            current_doomgeneric_command_bridge_report="\n".join([
                "v3025-doomgeneric-command-bridge-source-build-pass",
                "Boot SHA256: `boot-sha`",
                "V3024 engine SHA256: `8b6630498b7ff217e6ad9b27593f89644ba73eb7cbbf11361838972f15581735`",
                "Helper bundled in ramdisk: `1`",
                "WAD files in ramdisk: `0`",
                "video demo doom engine-probe",
                "serial-doompad-to-DG_GetKey",
                "video.demo.input.otg_required=0",
                "Run ID: `V3026`",
            ]),
        ) as paths:
            with self._patch_paths(paths):
                result = frontier.select_frontier()

        self.assertEqual(result["decision"], "frontier-selector-actionable-unit-present")
        self.assertEqual(result["selected_track"], "VIDEO")
        self.assertEqual(result["selected_reason"], "doomgeneric-command-bridge-live-validation-ready")
        self.assertEqual(result["track_evaluations"][1]["name"], "doom-capstone")
        self.assertTrue(result["track_evaluations"][1]["evidence"]["v3025_command_bridge_ready"])
        self.assertIn("V3026 rollback-gated live validation", result["next_operator_decision"])

    def test_current_doomgeneric_command_bridge_live_evidence_reads_v3026_pass(self) -> None:
        report = "\n".join([
            "v3026-doomgeneric-command-bridge-live-pass-before-rollback",
            "Candidate post-flash version rc/status: `0` / `ok`",
            "Candidate post-flash status rc/status: `0` / `ok`",
            "Candidate post-flash selftest fail=0: `1`",
            "`video demo doom status` rc/status: `0` / `ok`",
            "video.demo.engine.bridge=v3025-doomgeneric-command-bridge",
            "video.demo.engine.helper.present=1",
            "video.demo.engine.helper.executable=1",
            "`video demo doom engine-probe` rc/status: `0` / `ok`",
            "video.demo.doom.engine_probe.rc=0",
            "video.demo.doom.engine_probe.timed_out=0",
            "Rollback health: version_ok=`1` selftest_fail0=`1`",
            "video.demo.input.otg_required=0",
            "video.demo.asset.wad.embedded_in_boot=0",
            "No WAD/IWAD bytes were staged",
            "Run ID: `V3027`",
        ])

        evidence = frontier.current_doomgeneric_command_bridge_live_evidence(report)

        self.assertTrue(evidence["v3026_command_bridge_live_report_present"])
        self.assertTrue(evidence["v3026_command_bridge_live_pass"])
        self.assertTrue(evidence["v3026_candidate_health_ok"])
        self.assertTrue(evidence["v3026_status_command_ok"])
        self.assertTrue(evidence["v3026_engine_probe_ok"])
        self.assertTrue(evidence["v3026_rollback_health_ok"])
        self.assertTrue(evidence["v3026_no_otg_required"])
        self.assertTrue(evidence["v3026_wad_not_embedded"])
        self.assertEqual(evidence["v3026_next_run_id"], "V3027")

    def test_select_frontier_uses_v3026_live_pass_for_v3027_wad_preflight(self) -> None:
        with self._fake_repo(
            goal_text="\n".join([
                'PATCH-level kept "demo checkpoint"',
                "**Bad Apple + Nyan** demos",
                "**0.11.0 (MINOR) is RESERVED",
            ]),
            inventory_signals={
                "direct_a90ctl_actionable_now_count": 0,
                "direct_a90ctl_review_only_count": 0,
                "direct_a90ctl_next_actionable_group": None,
                "source_delete_review_count": 0,
                "active_live_phase_residual_backlog_closed": True,
            },
            frontier_candidates=None,
            current_doom_gameplay_loop_report="\n".join([
                "v3017-doompad-gameplay-loop-state-consumed-pass-before-rollback",
                "`video demo doom play 8` rc: `0` markers_ok=`1`",
                "Player movement parsed: `1` moved_forward=`1`",
                "Rollback health: version_ok=`1` selftest_fail0=`1`",
                "not a WAD-backed `doomgeneric` engine",
            ]),
            current_demo_checkpoint_source_report="\n".join([
                "v3021-demo-checkpoint-badapple-nyan-source-build-pass",
                "Boot SHA256: `c860d604e3c906abf61fdd2c9bd9cd12d1aef2c88c05be57677b472ad36ef0f7`",
                "Bad Apple asset ID: `badapple-480x360-full-v2903`",
                "menu.demo.badapple.action=play-av-fullsong",
                "menu.demo.badapple.frames=6962",
                "Nyan asset ID: `nyancat-v2973-pal8-rle-preview`",
                "menu.demo.nyan.action=play-av-preview",
                "pal8-rle",
                "pending-badapple-nyan-same-image-live-validation",
            ]),
            current_demo_checkpoint_live_report="\n".join([
                "v3022-demo-checkpoint-badapple-nyan-same-image-live-pass-before-rollback",
                "Same-image validation: Bad Apple pass=`1` Nyan pass=`1`",
                "Rollback health: version_ok=`1` selftest_fail0=`1`",
            ]),
            current_doomgeneric_policy_report="\n".join([
                "v3023-doomgeneric-private-integration-policy-ready",
                "Private doomgeneric source pinned: `1`",
                "Private source clean: `1`",
                "V3020 port probe pass: `1`",
                "V3022 checkpoint live pass retained: `1`",
                "Public WAD files committed/present: `0`",
                "Safe next host-only unit: `1`",
                "Run ID: `V3024`",
            ]),
            current_doomgeneric_private_build_report="\n".join([
                "v3024-doomgeneric-private-full-engine-link-pass",
                "Private engine source files compiled: `80`",
                "AArch64 static engine linked: `1`",
                "Marker check pass: `1`",
                "Public WAD files committed/present: `0`",
                "Engine-only object total within V3023 2 MiB cap: `1`",
                "Boot-image delta: `not-produced`",
                "Run ID: `V3025`",
            ]),
            current_doomgeneric_command_bridge_report="\n".join([
                "v3025-doomgeneric-command-bridge-source-build-pass",
                "Boot SHA256: `boot-sha`",
                "V3024 engine SHA256: `8b6630498b7ff217e6ad9b27593f89644ba73eb7cbbf11361838972f15581735`",
                "Helper bundled in ramdisk: `1`",
                "WAD files in ramdisk: `0`",
                "video demo doom engine-probe",
                "serial-doompad-to-DG_GetKey",
                "video.demo.input.otg_required=0",
                "Run ID: `V3026`",
            ]),
            current_doomgeneric_command_bridge_live_report="\n".join([
                "v3026-doomgeneric-command-bridge-live-pass-before-rollback",
                "Candidate post-flash version rc/status: `0` / `ok`",
                "Candidate post-flash status rc/status: `0` / `ok`",
                "Candidate post-flash selftest fail=0: `1`",
                "`video demo doom status` rc/status: `0` / `ok`",
                "video.demo.engine.bridge=v3025-doomgeneric-command-bridge",
                "video.demo.engine.helper.present=1",
                "video.demo.engine.helper.executable=1",
                "`video demo doom engine-probe` rc/status: `0` / `ok`",
                "video.demo.doom.engine_probe.rc=0",
                "video.demo.doom.engine_probe.timed_out=0",
                "Rollback health: version_ok=`1` selftest_fail0=`1`",
                "video.demo.input.otg_required=0",
                "video.demo.asset.wad.embedded_in_boot=0",
                "No WAD/IWAD bytes were staged",
                "Run ID: `V3027`",
            ]),
        ) as paths:
            with self._patch_paths(paths):
                result = frontier.select_frontier()

        self.assertEqual(result["decision"], "frontier-selector-actionable-unit-present")
        self.assertEqual(result["selected_track"], "VIDEO")
        self.assertEqual(result["selected_reason"], "doomgeneric-runtime-wad-staging-preflight-ready")
        self.assertEqual(result["track_evaluations"][1]["name"], "doom-capstone")
        self.assertTrue(result["track_evaluations"][1]["evidence"]["v3026_command_bridge_live_pass"])
        self.assertIn("V3027 host-only runtime-private WAD staging preflight", result["next_operator_decision"])

    def test_current_doomgeneric_runtime_wad_preflight_evidence_reads_asset_needed(self) -> None:
        report = "\n".join([
            "v3027-doomgeneric-runtime-wad-staging-preflight-asset-needed",
            "Preflight OK: `1`",
            "Live asset ready: `0`",
            "Public WAD files committed/present: `0`",
            "Private WAD/IWAD candidate count: `0`",
            "Next requires command implementation: `1`",
            "Public output records no WAD bytes and no private WAD filename.",
        ])

        evidence = frontier.current_doomgeneric_runtime_wad_preflight_evidence(report)

        self.assertTrue(evidence["v3027_runtime_wad_preflight_report_present"])
        self.assertFalse(evidence["v3027_runtime_wad_contract_ready"])
        self.assertTrue(evidence["v3027_runtime_wad_asset_needed"])
        self.assertTrue(evidence["v3027_preflight_ok"])
        self.assertFalse(evidence["v3027_live_asset_ready"])
        self.assertTrue(evidence["v3027_public_wad_zero"])
        self.assertTrue(evidence["v3027_private_candidate_count_zero"])
        self.assertTrue(evidence["v3027_no_private_filename_public"])
        self.assertTrue(evidence["v3027_next_requires_command_implementation"])

    def test_current_doomgeneric_sd_wad_stage_evidence_reads_pass(self) -> None:
        report = "\n".join([
            "v3028-doomgeneric-sd-wad-stage-live-pass",
            "Remote SD WAD path: `/mnt/sdext/a90/runtime/doom/v3028/DOOM1.WAD`",
            "Device WAD SHA256 match: `1`",
            "Device WAD mode: `0600`",
            "Public WAD files committed/present: `0`",
            "Boot image written: `0`",
            "Ramdisk WAD bytes written: `0`",
            "Post-stage selftest fail=0: `1`",
            "Run ID: `V3029`",
        ])

        evidence = frontier.current_doomgeneric_sd_wad_stage_evidence(report)

        self.assertTrue(evidence["v3028_sd_wad_stage_report_present"])
        self.assertTrue(evidence["v3028_sd_wad_stage_pass"])
        self.assertTrue(evidence["v3028_sd_wad_sha_match"])
        self.assertTrue(evidence["v3028_sd_wad_mode_0600"])
        self.assertEqual(evidence["v3028_next_run_id"], "V3029")

    def test_current_doomgeneric_sd_wad_command_evidence_reads_pass(self) -> None:
        report = "\n".join([
            "v3029-doomgeneric-sd-wad-command-source-build-pass",
            "Boot SHA256: `9b45abb847ac64c9032f0e873038a3abf577e27f2dabc2ceccad8cd8e95cf804`",
            "Runtime WAD path: `/mnt/sdext/a90/runtime/doom/v3028/DOOM1.WAD`",
            "Expected WAD SHA256: `1d7d43be501e67d927e415e0b8f3e29c3bf33075e859721816f652a526cac771`",
            "WAD files in ramdisk: `0`",
            "Public WAD files committed/present: `0`",
            "WAD bytes embedded in boot image: `0`",
            "Helper bundled in ramdisk: `1`",
            "Device action: `none` in this build unit.",
            "video demo doom verify --wad runtime-private --sha256",
            "video demo doom play [frames] --wad runtime-private --sha256",
            "Run ID: `V3030`",
        ])

        evidence = frontier.current_doomgeneric_sd_wad_command_evidence(report)

        self.assertTrue(evidence["v3029_sd_wad_command_report_present"])
        self.assertTrue(evidence["v3029_sd_wad_command_ready"])
        self.assertTrue(evidence["v3029_boot_sha_present"])
        self.assertTrue(evidence["v3029_runtime_wad_path_pinned"])
        self.assertTrue(evidence["v3029_expected_wad_sha_pinned"])
        self.assertTrue(evidence["v3029_verify_command_present"])
        self.assertTrue(evidence["v3029_play_command_present"])
        self.assertTrue(evidence["v3029_ramdisk_wad_zero"])
        self.assertTrue(evidence["v3029_wad_not_embedded"])
        self.assertEqual(evidence["v3029_next_run_id"], "V3030")

    def test_current_doomgeneric_sd_wad_command_live_evidence_reads_pass(self) -> None:
        report = "\n".join([
            "v3030-doomgeneric-sd-wad-command-live-pass-before-rollback",
            "Candidate flashed through checked helper: `1`",
            "Candidate remote SHA256 matched local: `1`",
            "Candidate boot readback SHA256 matched expected: `1`",
            "Candidate post-flash version rc/status: `0` / `ok`",
            "Candidate post-flash status rc/status: `0` / `ok`",
            "Candidate post-flash selftest fail=0: `1`",
            "`video demo doom status` rc/status: `0` / `ok`",
            "`video demo doom verify --wad runtime-private --sha256 EXPECTED` rc/status: `0` / `ok`",
            "video.demo.doom.verify.sha256_match=1",
            "video.demo.doom.verify.magic=IWAD",
            "video.demo.doom.verify.ok=1",
            "`video demo doom play 4 --wad runtime-private --sha256 EXPECTED` rc/status: `0` / `ok`",
            "video.demo.doom.play.rc=0",
            "video.demo.doom.play.timed_out=0",
            "Rollback health: version_ok=`1` selftest_fail0=`1`",
            "Rollback boot readback SHA256 matched expected: `1`",
            "Final rollback selftest fail=0 re-check: `1`",
            "Run ID: `V3031`",
        ])

        evidence = frontier.current_doomgeneric_sd_wad_command_live_evidence(report)

        self.assertTrue(evidence["v3030_sd_wad_command_live_report_present"])
        self.assertTrue(evidence["v3030_sd_wad_command_live_pass"])
        self.assertTrue(evidence["v3030_candidate_flash_ok"])
        self.assertTrue(evidence["v3030_candidate_health_ok"])
        self.assertTrue(evidence["v3030_status_command_ok"])
        self.assertTrue(evidence["v3030_verify_command_ok"])
        self.assertTrue(evidence["v3030_verify_sha_match"])
        self.assertTrue(evidence["v3030_play_smoke_ok"])
        self.assertTrue(evidence["v3030_play_not_timed_out"])
        self.assertTrue(evidence["v3030_rollback_health_ok"])
        self.assertEqual(evidence["v3030_next_run_id"], "V3031")

    def test_current_doomgeneric_visible_frame_evidence_reads_pass(self) -> None:
        report = "\n".join([
            "v3031-doomgeneric-visible-frame-source-build-pass",
            "Boot SHA256: `1fefa60b9530cf4cfeb21f2419b77e7d9ca4258078899e3826a0c99918912fb4`",
            "--wad-frame-dump",
            "--output",
            "video demo doom frame [frames] --wad runtime-private --sha256",
            "DEMO > DOOM menu item now launches",
            "Frame format: `xbgr8888-raw`",
            "Frame geometry: `640x400` stride `2560` bytes `1024000`",
            "KMS path: `existing-kms-dumb-buffer-blit-present`",
            "WAD files in ramdisk: `0`",
            "Public WAD files committed/present: `0`",
            "WAD bytes embedded in boot image: `0`",
            "Device action: `none` in this build unit.",
            "Run ID: `V3032`",
        ])

        evidence = frontier.current_doomgeneric_visible_frame_evidence(report)

        self.assertTrue(evidence["v3031_visible_frame_report_present"])
        self.assertTrue(evidence["v3031_visible_frame_ready"])
        self.assertTrue(evidence["v3031_helper_frame_dump_present"])
        self.assertTrue(evidence["v3031_native_frame_command_present"])
        self.assertTrue(evidence["v3031_menu_frame_preview_present"])
        self.assertTrue(evidence["v3031_frame_contract_pinned"])
        self.assertTrue(evidence["v3031_ramdisk_wad_zero"])
        self.assertTrue(evidence["v3031_public_wad_zero"])
        self.assertTrue(evidence["v3031_wad_not_embedded"])
        self.assertTrue(evidence["v3031_no_device_action"])
        self.assertEqual(evidence["v3031_next_run_id"], "V3032")

    def test_v3027_ready_selects_sd_wad_stage_before_command_implementation(self) -> None:
        evaluation = frontier.current_doom_input_evaluation(
            None,
            gameplay_loop_report_text="\n".join([
                "v3017-doompad-gameplay-loop-state-consumed-pass-before-rollback",
                "`video demo doom play 8` rc: `0` markers_ok=`1`",
                "Player movement parsed: `1` moved_forward=`1`",
                "Rollback health: version_ok=`1` selftest_fail0=`1`",
                "not a WAD-backed `doomgeneric` engine",
            ]),
            doomgeneric_policy_report_text="\n".join([
                "v3023-doomgeneric-private-integration-policy-ready",
                "Private doomgeneric source pinned: `1`",
                "Private source clean: `1`",
                "V3020 port probe pass: `1`",
                "V3022 checkpoint live pass retained: `1`",
                "Public WAD files committed/present: `0`",
                "Safe next host-only unit: `1`",
                "Run ID: `V3024`",
            ]),
            doomgeneric_private_build_report_text="\n".join([
                "v3024-doomgeneric-private-full-engine-link-pass",
                "Private engine source files compiled: `80`",
                "AArch64 static engine linked: `1`",
                "Marker check pass: `1`",
                "Public WAD files committed/present: `0`",
                "Engine-only object total within V3023 2 MiB cap: `1`",
                "Boot-image delta: `not-produced`",
                "Run ID: `V3025`",
            ]),
            doomgeneric_command_bridge_report_text="\n".join([
                "v3025-doomgeneric-command-bridge-source-build-pass",
                "Boot SHA256: `boot-sha`",
                "V3024 engine SHA256: `8b6630498b7ff217e6ad9b27593f89644ba73eb7cbbf11361838972f15581735`",
                "Helper bundled in ramdisk: `1`",
                "WAD files in ramdisk: `0`",
                "video demo doom engine-probe",
                "serial-doompad-to-DG_GetKey",
                "video.demo.input.otg_required=0",
                "Run ID: `V3026`",
            ]),
            doomgeneric_command_bridge_live_report_text="\n".join([
                "v3026-doomgeneric-command-bridge-live-pass-before-rollback",
                "Candidate post-flash version rc/status: `0` / `ok`",
                "Candidate post-flash status rc/status: `0` / `ok`",
                "Candidate post-flash selftest fail=0: `1`",
                "`video demo doom status` rc/status: `0` / `ok`",
                "video.demo.engine.bridge=v3025-doomgeneric-command-bridge",
                "video.demo.engine.helper.present=1",
                "video.demo.engine.helper.executable=1",
                "`video demo doom engine-probe` rc/status: `0` / `ok`",
                "video.demo.doom.engine_probe.rc=0",
                "video.demo.doom.engine_probe.timed_out=0",
                "Rollback health: version_ok=`1` selftest_fail0=`1`",
                "video.demo.input.otg_required=0",
                "video.demo.asset.wad.embedded_in_boot=0",
                "No WAD/IWAD bytes were staged",
                "Run ID: `V3027`",
            ]),
            doomgeneric_runtime_wad_preflight_report_text="\n".join([
                "v3027-doomgeneric-runtime-wad-staging-contract-ready",
                "Preflight OK: `1`",
                "Live asset ready: `1`",
                "Public WAD files committed/present: `0`",
                "Next requires command implementation: `1`",
                "Public output records no WAD bytes and no private WAD filename.",
                "Run ID: `V3028`",
            ]),
        )

        self.assertEqual(evaluation["status"], "doomgeneric-sd-wad-stage-ready")
        self.assertTrue(evaluation["safe_actionable_now"])
        self.assertIn("V3028 SD runtime WAD stage", evaluation["evidence"]["next_host_only_unit"])

    def test_v3028_sd_wad_stage_selects_v3029_command_implementation(self) -> None:
        evaluation = frontier.current_doom_input_evaluation(
            None,
            gameplay_loop_report_text="\n".join([
                "v3017-doompad-gameplay-loop-state-consumed-pass-before-rollback",
                "`video demo doom play 8` rc: `0` markers_ok=`1`",
                "Player movement parsed: `1` moved_forward=`1`",
                "Rollback health: version_ok=`1` selftest_fail0=`1`",
                "not a WAD-backed `doomgeneric` engine",
            ]),
            doomgeneric_policy_report_text="\n".join([
                "v3023-doomgeneric-private-integration-policy-ready",
                "Private doomgeneric source pinned: `1`",
                "Private source clean: `1`",
                "V3020 port probe pass: `1`",
                "V3022 checkpoint live pass retained: `1`",
                "Public WAD files committed/present: `0`",
                "Safe next host-only unit: `1`",
                "Run ID: `V3024`",
            ]),
            doomgeneric_private_build_report_text="\n".join([
                "v3024-doomgeneric-private-full-engine-link-pass",
                "Private engine source files compiled: `80`",
                "AArch64 static engine linked: `1`",
                "Marker check pass: `1`",
                "Public WAD files committed/present: `0`",
                "Engine-only object total within V3023 2 MiB cap: `1`",
                "Boot-image delta: `not-produced`",
                "Run ID: `V3025`",
            ]),
            doomgeneric_command_bridge_report_text="\n".join([
                "v3025-doomgeneric-command-bridge-source-build-pass",
                "Boot SHA256: `boot-sha`",
                "V3024 engine SHA256: `8b6630498b7ff217e6ad9b27593f89644ba73eb7cbbf11361838972f15581735`",
                "Helper bundled in ramdisk: `1`",
                "WAD files in ramdisk: `0`",
                "video demo doom engine-probe",
                "serial-doompad-to-DG_GetKey",
                "video.demo.input.otg_required=0",
                "Run ID: `V3026`",
            ]),
            doomgeneric_command_bridge_live_report_text="\n".join([
                "v3026-doomgeneric-command-bridge-live-pass-before-rollback",
                "Candidate post-flash version rc/status: `0` / `ok`",
                "Candidate post-flash status rc/status: `0` / `ok`",
                "Candidate post-flash selftest fail=0: `1`",
                "`video demo doom status` rc/status: `0` / `ok`",
                "video.demo.engine.bridge=v3025-doomgeneric-command-bridge",
                "video.demo.engine.helper.present=1",
                "video.demo.engine.helper.executable=1",
                "`video demo doom engine-probe` rc/status: `0` / `ok`",
                "video.demo.doom.engine_probe.rc=0",
                "video.demo.doom.engine_probe.timed_out=0",
                "Rollback health: version_ok=`1` selftest_fail0=`1`",
                "video.demo.input.otg_required=0",
                "video.demo.asset.wad.embedded_in_boot=0",
                "No WAD/IWAD bytes were staged",
                "Run ID: `V3027`",
            ]),
            doomgeneric_runtime_wad_preflight_report_text="\n".join([
                "v3027-doomgeneric-runtime-wad-staging-contract-ready",
                "Preflight OK: `1`",
                "Live asset ready: `1`",
                "Public WAD files committed/present: `0`",
                "Next requires command implementation: `1`",
                "Public output records no WAD bytes and no private WAD filename.",
                "Run ID: `V3028`",
            ]),
            doomgeneric_sd_wad_stage_report_text="\n".join([
                "v3028-doomgeneric-sd-wad-stage-live-pass",
                "Remote SD WAD path: `/mnt/sdext/a90/runtime/doom/v3028/DOOM1.WAD`",
                "Device WAD SHA256 match: `1`",
                "Device WAD mode: `0600`",
                "Public WAD files committed/present: `0`",
                "Boot image written: `0`",
                "Ramdisk WAD bytes written: `0`",
                "Post-stage selftest fail=0: `1`",
                "Run ID: `V3029`",
            ]),
        )

        self.assertEqual(evaluation["status"], "doomgeneric-wad-backed-command-implementation-ready")
        self.assertTrue(evaluation["safe_actionable_now"])
        self.assertTrue(evaluation["evidence"]["v3028_sd_wad_stage_pass"])
        self.assertIn("V3029 WAD-backed doomgeneric command implementation", evaluation["evidence"]["next_host_only_unit"])

    def test_v3029_sd_wad_command_build_selects_v3030_live_validation(self) -> None:
        evaluation = frontier.current_doom_input_evaluation(
            None,
            gameplay_loop_report_text="\n".join([
                "v3017-doompad-gameplay-loop-state-consumed-pass-before-rollback",
                "`video demo doom play 8` rc: `0` markers_ok=`1`",
                "Player movement parsed: `1` moved_forward=`1`",
                "Rollback health: version_ok=`1` selftest_fail0=`1`",
                "not a WAD-backed `doomgeneric` engine",
            ]),
            doomgeneric_policy_report_text="\n".join([
                "v3023-doomgeneric-private-integration-policy-ready",
                "Private doomgeneric source pinned: `1`",
                "Private source clean: `1`",
                "V3020 port probe pass: `1`",
                "V3022 checkpoint live pass retained: `1`",
                "Public WAD files committed/present: `0`",
                "Safe next host-only unit: `1`",
                "Run ID: `V3024`",
            ]),
            doomgeneric_private_build_report_text="\n".join([
                "v3024-doomgeneric-private-full-engine-link-pass",
                "Private engine source files compiled: `80`",
                "AArch64 static engine linked: `1`",
                "Marker check pass: `1`",
                "Public WAD files committed/present: `0`",
                "Engine-only object total within V3023 2 MiB cap: `1`",
                "Boot-image delta: `not-produced`",
                "Run ID: `V3025`",
            ]),
            doomgeneric_command_bridge_report_text="\n".join([
                "v3025-doomgeneric-command-bridge-source-build-pass",
                "Boot SHA256: `boot-sha`",
                "V3024 engine SHA256: `8b6630498b7ff217e6ad9b27593f89644ba73eb7cbbf11361838972f15581735`",
                "Helper bundled in ramdisk: `1`",
                "WAD files in ramdisk: `0`",
                "video demo doom engine-probe",
                "serial-doompad-to-DG_GetKey",
                "video.demo.input.otg_required=0",
                "Run ID: `V3026`",
            ]),
            doomgeneric_command_bridge_live_report_text="\n".join([
                "v3026-doomgeneric-command-bridge-live-pass-before-rollback",
                "Candidate post-flash version rc/status: `0` / `ok`",
                "Candidate post-flash status rc/status: `0` / `ok`",
                "Candidate post-flash selftest fail=0: `1`",
                "`video demo doom status` rc/status: `0` / `ok`",
                "video.demo.engine.bridge=v3025-doomgeneric-command-bridge",
                "video.demo.engine.helper.present=1",
                "video.demo.engine.helper.executable=1",
                "`video demo doom engine-probe` rc/status: `0` / `ok`",
                "video.demo.doom.engine_probe.rc=0",
                "video.demo.doom.engine_probe.timed_out=0",
                "Rollback health: version_ok=`1` selftest_fail0=`1`",
                "video.demo.input.otg_required=0",
                "video.demo.asset.wad.embedded_in_boot=0",
                "No WAD/IWAD bytes were staged",
                "Run ID: `V3027`",
            ]),
            doomgeneric_runtime_wad_preflight_report_text="\n".join([
                "v3027-doomgeneric-runtime-wad-staging-contract-ready",
                "Preflight OK: `1`",
                "Live asset ready: `1`",
                "Public WAD files committed/present: `0`",
                "Next requires command implementation: `1`",
                "Public output records no WAD bytes and no private WAD filename.",
                "Run ID: `V3028`",
            ]),
            doomgeneric_sd_wad_stage_report_text="\n".join([
                "v3028-doomgeneric-sd-wad-stage-live-pass",
                "Remote SD WAD path: `/mnt/sdext/a90/runtime/doom/v3028/DOOM1.WAD`",
                "Device WAD SHA256 match: `1`",
                "Device WAD mode: `0600`",
                "Public WAD files committed/present: `0`",
                "Boot image written: `0`",
                "Ramdisk WAD bytes written: `0`",
                "Post-stage selftest fail=0: `1`",
                "Run ID: `V3029`",
            ]),
            doomgeneric_sd_wad_command_report_text="\n".join([
                "v3029-doomgeneric-sd-wad-command-source-build-pass",
                "Boot SHA256: `9b45abb847ac64c9032f0e873038a3abf577e27f2dabc2ceccad8cd8e95cf804`",
                "Runtime WAD path: `/mnt/sdext/a90/runtime/doom/v3028/DOOM1.WAD`",
                "Expected WAD SHA256: `1d7d43be501e67d927e415e0b8f3e29c3bf33075e859721816f652a526cac771`",
                "WAD files in ramdisk: `0`",
                "Public WAD files committed/present: `0`",
                "WAD bytes embedded in boot image: `0`",
                "Helper bundled in ramdisk: `1`",
                "Device action: `none` in this build unit.",
                "video demo doom verify --wad runtime-private --sha256",
                "video demo doom play [frames] --wad runtime-private --sha256",
                "Run ID: `V3030`",
            ]),
        )

        self.assertEqual(evaluation["status"], "doomgeneric-sd-wad-command-live-validation-ready")
        self.assertTrue(evaluation["safe_actionable_now"])
        self.assertTrue(evaluation["evidence"]["v3029_sd_wad_command_ready"])
        self.assertIn("V3030 rollback-gated live validation", evaluation["evidence"]["next_live_unit"])

    def test_select_frontier_uses_v3030_live_pass_for_v3031_visible_frame_unit(self) -> None:
        with self._fake_repo(
            inventory_signals={
                "direct_a90ctl_actionable_now_count": 0,
                "direct_a90ctl_review_only_count": 0,
                "direct_a90ctl_next_actionable_group": None,
                "source_delete_review_count": 0,
                "active_live_phase_residual_backlog_closed": True,
            },
            frontier_candidates=None,
            current_doom_gameplay_loop_report="\n".join([
                "v3017-doompad-gameplay-loop-state-consumed-pass-before-rollback",
                "`video demo doom play 8` rc: `0` markers_ok=`1`",
                "Player movement parsed: `1` moved_forward=`1`",
                "Rollback health: version_ok=`1` selftest_fail0=`1`",
                "not a WAD-backed `doomgeneric` engine",
            ]),
            current_doomgeneric_sd_wad_command_live_report="\n".join([
                "v3030-doomgeneric-sd-wad-command-live-pass-before-rollback",
                "Candidate flashed through checked helper: `1`",
                "Candidate remote SHA256 matched local: `1`",
                "Candidate boot readback SHA256 matched expected: `1`",
                "Candidate post-flash version rc/status: `0` / `ok`",
                "Candidate post-flash status rc/status: `0` / `ok`",
                "Candidate post-flash selftest fail=0: `1`",
                "`video demo doom status` rc/status: `0` / `ok`",
                "`video demo doom verify --wad runtime-private --sha256 EXPECTED` rc/status: `0` / `ok`",
                "video.demo.doom.verify.sha256_match=1",
                "video.demo.doom.verify.magic=IWAD",
                "video.demo.doom.verify.ok=1",
                "`video demo doom play 4 --wad runtime-private --sha256 EXPECTED` rc/status: `0` / `ok`",
                "video.demo.doom.play.rc=0",
                "video.demo.doom.play.timed_out=0",
                "Rollback health: version_ok=`1` selftest_fail0=`1`",
                "Rollback boot readback SHA256 matched expected: `1`",
                "Final rollback selftest fail=0 re-check: `1`",
                "Run ID: `V3031`",
            ]),
        ) as paths:
            with self._patch_paths(paths):
                result = frontier.select_frontier()

        self.assertEqual(result["decision"], "frontier-selector-actionable-unit-present")
        self.assertEqual(result["selected_track"], "VIDEO")
        self.assertEqual(result["selected_reason"], "doomgeneric-visible-frame-integration-ready")
        self.assertEqual(result["track_evaluations"][0]["name"], "doom-capstone")
        self.assertTrue(result["track_evaluations"][0]["evidence"]["v3030_sd_wad_command_live_pass"])
        self.assertIn("V3031 host-only WAD-backed visible DOOM", result["next_operator_decision"])

    def test_select_frontier_uses_v3031_visible_frame_for_v3032_live_validation(self) -> None:
        with self._fake_repo(
            inventory_signals={
                "direct_a90ctl_actionable_now_count": 0,
                "direct_a90ctl_review_only_count": 0,
                "direct_a90ctl_next_actionable_group": None,
                "source_delete_review_count": 0,
                "active_live_phase_residual_backlog_closed": True,
            },
            frontier_candidates=None,
            current_doom_gameplay_loop_report="\n".join([
                "v3017-doompad-gameplay-loop-state-consumed-pass-before-rollback",
                "`video demo doom play 8` rc: `0` markers_ok=`1`",
                "Player movement parsed: `1` moved_forward=`1`",
                "Rollback health: version_ok=`1` selftest_fail0=`1`",
                "not a WAD-backed `doomgeneric` engine",
            ]),
            current_doomgeneric_sd_wad_command_live_report="\n".join([
                "v3030-doomgeneric-sd-wad-command-live-pass-before-rollback",
                "Candidate flashed through checked helper: `1`",
                "Candidate remote SHA256 matched local: `1`",
                "Candidate boot readback SHA256 matched expected: `1`",
                "Candidate post-flash version rc/status: `0` / `ok`",
                "Candidate post-flash status rc/status: `0` / `ok`",
                "Candidate post-flash selftest fail=0: `1`",
                "`video demo doom status` rc/status: `0` / `ok`",
                "`video demo doom verify --wad runtime-private --sha256 EXPECTED` rc/status: `0` / `ok`",
                "video.demo.doom.verify.sha256_match=1",
                "video.demo.doom.verify.magic=IWAD",
                "video.demo.doom.verify.ok=1",
                "`video demo doom play 4 --wad runtime-private --sha256 EXPECTED` rc/status: `0` / `ok`",
                "video.demo.doom.play.rc=0",
                "video.demo.doom.play.timed_out=0",
                "Rollback health: version_ok=`1` selftest_fail0=`1`",
                "Rollback boot readback SHA256 matched expected: `1`",
                "Final rollback selftest fail=0 re-check: `1`",
                "Run ID: `V3031`",
            ]),
            current_doomgeneric_visible_frame_report="\n".join([
                "v3031-doomgeneric-visible-frame-source-build-pass",
                "Boot SHA256: `1fefa60b9530cf4cfeb21f2419b77e7d9ca4258078899e3826a0c99918912fb4`",
                "--wad-frame-dump",
                "--output",
                "video demo doom frame [frames] --wad runtime-private --sha256",
                "DEMO > DOOM menu item now launches",
                "Frame format: `xbgr8888-raw`",
                "Frame geometry: `640x400` stride `2560` bytes `1024000`",
                "KMS path: `existing-kms-dumb-buffer-blit-present`",
                "WAD files in ramdisk: `0`",
                "Public WAD files committed/present: `0`",
                "WAD bytes embedded in boot image: `0`",
                "Device action: `none` in this build unit.",
                "Run ID: `V3032`",
            ]),
        ) as paths:
            with self._patch_paths(paths):
                result = frontier.select_frontier()

        self.assertEqual(result["decision"], "frontier-selector-actionable-unit-present")
        self.assertEqual(result["selected_track"], "VIDEO")
        self.assertEqual(result["selected_reason"], "doomgeneric-visible-frame-live-validation-ready")
        self.assertEqual(result["track_evaluations"][0]["name"], "doom-capstone")
        self.assertTrue(result["track_evaluations"][0]["evidence"]["v3031_visible_frame_ready"])
        self.assertIn("V3032 rollback-gated live validation", result["next_operator_decision"])

    def test_select_frontier_stops_on_v3027_asset_needed(self) -> None:
        with self._fake_repo(
            goal_text="\n".join([
                'PATCH-level kept "demo checkpoint"',
                "**Bad Apple + Nyan** demos",
                "**0.11.0 (MINOR) is RESERVED",
            ]),
            inventory_signals={
                "direct_a90ctl_actionable_now_count": 0,
                "direct_a90ctl_review_only_count": 0,
                "direct_a90ctl_next_actionable_group": None,
                "source_delete_review_count": 0,
                "active_live_phase_residual_backlog_closed": True,
            },
            frontier_candidates=None,
            current_doom_gameplay_loop_report="\n".join([
                "v3017-doompad-gameplay-loop-state-consumed-pass-before-rollback",
                "`video demo doom play 8` rc: `0` markers_ok=`1`",
                "Player movement parsed: `1` moved_forward=`1`",
                "Rollback health: version_ok=`1` selftest_fail0=`1`",
                "not a WAD-backed `doomgeneric` engine",
            ]),
            current_demo_checkpoint_source_report="\n".join([
                "v3021-demo-checkpoint-badapple-nyan-source-build-pass",
                "Boot SHA256: `c860d604e3c906abf61fdd2c9bd9cd12d1aef2c88c05be57677b472ad36ef0f7`",
                "Bad Apple asset ID: `badapple-480x360-full-v2903`",
                "menu.demo.badapple.action=play-av-fullsong",
                "menu.demo.badapple.frames=6962",
                "Nyan asset ID: `nyancat-v2973-pal8-rle-preview`",
                "menu.demo.nyan.action=play-av-preview",
                "pal8-rle",
                "pending-badapple-nyan-same-image-live-validation",
            ]),
            current_demo_checkpoint_live_report="\n".join([
                "v3022-demo-checkpoint-badapple-nyan-same-image-live-pass-before-rollback",
                "Same-image validation: Bad Apple pass=`1` Nyan pass=`1`",
                "Rollback health: version_ok=`1` selftest_fail0=`1`",
            ]),
            current_doomgeneric_policy_report="\n".join([
                "v3023-doomgeneric-private-integration-policy-ready",
                "Private doomgeneric source pinned: `1`",
                "Private source clean: `1`",
                "V3020 port probe pass: `1`",
                "V3022 checkpoint live pass retained: `1`",
                "Public WAD files committed/present: `0`",
                "Safe next host-only unit: `1`",
                "Run ID: `V3024`",
            ]),
            current_doomgeneric_private_build_report="\n".join([
                "v3024-doomgeneric-private-full-engine-link-pass",
                "Private engine source files compiled: `80`",
                "AArch64 static engine linked: `1`",
                "Marker check pass: `1`",
                "Public WAD files committed/present: `0`",
                "Engine-only object total within V3023 2 MiB cap: `1`",
                "Boot-image delta: `not-produced`",
                "Run ID: `V3025`",
            ]),
            current_doomgeneric_command_bridge_report="\n".join([
                "v3025-doomgeneric-command-bridge-source-build-pass",
                "Boot SHA256: `boot-sha`",
                "V3024 engine SHA256: `8b6630498b7ff217e6ad9b27593f89644ba73eb7cbbf11361838972f15581735`",
                "Helper bundled in ramdisk: `1`",
                "WAD files in ramdisk: `0`",
                "video demo doom engine-probe",
                "serial-doompad-to-DG_GetKey",
                "video.demo.input.otg_required=0",
                "Run ID: `V3026`",
            ]),
            current_doomgeneric_command_bridge_live_report="\n".join([
                "v3026-doomgeneric-command-bridge-live-pass-before-rollback",
                "Candidate post-flash version rc/status: `0` / `ok`",
                "Candidate post-flash status rc/status: `0` / `ok`",
                "Candidate post-flash selftest fail=0: `1`",
                "`video demo doom status` rc/status: `0` / `ok`",
                "video.demo.engine.bridge=v3025-doomgeneric-command-bridge",
                "video.demo.engine.helper.present=1",
                "video.demo.engine.helper.executable=1",
                "`video demo doom engine-probe` rc/status: `0` / `ok`",
                "video.demo.doom.engine_probe.rc=0",
                "video.demo.doom.engine_probe.timed_out=0",
                "Rollback health: version_ok=`1` selftest_fail0=`1`",
                "video.demo.input.otg_required=0",
                "video.demo.asset.wad.embedded_in_boot=0",
                "No WAD/IWAD bytes were staged",
                "Run ID: `V3027`",
            ]),
            current_doomgeneric_runtime_wad_preflight_report="\n".join([
                "v3027-doomgeneric-runtime-wad-staging-preflight-asset-needed",
                "Preflight OK: `1`",
                "Live asset ready: `0`",
                "Public WAD files committed/present: `0`",
                "Private WAD/IWAD candidate count: `0`",
                "Next requires command implementation: `1`",
                "Public output records no WAD bytes and no private WAD filename.",
            ]),
        ) as paths:
            with self._patch_paths(paths):
                result = frontier.select_frontier()

        self.assertEqual(result["decision"], "frontier-selector-no-automatic-safe-unit")
        self.assertIsNone(result["selected_track"])
        self.assertIsNone(result["selected_reason"])
        self.assertEqual(result["track_evaluations"][1]["status"], "doomgeneric-runtime-wad-private-asset-needed")
        self.assertFalse(result["track_evaluations"][1]["safe_actionable_now"])
        self.assertIn("Stage exactly one private IWAD/WAD", result["next_operator_decision"])

    @staticmethod
    def _fake_repo(
        *,
        inventory_signals: dict[str, object],
        frontier_candidates: dict[str, object] | None,
        current_doom_report: str | None = None,
        current_doom_flash_gate_report: str | None = None,
        current_doom_live_precondition_report: str | None = None,
        current_doom_gameplay_loop_report: str | None = None,
        current_demo_checkpoint_source_report: str | None = None,
        current_demo_checkpoint_live_report: str | None = None,
        current_doomgeneric_policy_report: str | None = None,
        current_doomgeneric_private_build_report: str | None = None,
        current_doomgeneric_command_bridge_report: str | None = None,
        current_doomgeneric_command_bridge_live_report: str | None = None,
        current_doomgeneric_runtime_wad_preflight_report: str | None = None,
        current_doomgeneric_sd_wad_stage_report: str | None = None,
        current_doomgeneric_sd_wad_command_report: str | None = None,
        current_doomgeneric_sd_wad_command_live_report: str | None = None,
        current_doomgeneric_visible_frame_report: str | None = None,
        goal_text: str = "goal text\n",
    ):
        class RepoContext:
            def __enter__(self):
                self.tmp = tempfile.TemporaryDirectory()
                root = Path(self.tmp.name)
                (root / "docs" / "plans").mkdir(parents=True)
                (root / "docs" / "reports").mkdir(parents=True)
                (root / "docs" / "artifacts").mkdir(parents=True)
                (root / "GOAL.md").write_text(goal_text, encoding="utf-8")
                (root / "docs" / "plans" / "NATIVE_INIT_CURRENT_TODO_2026-06-08.md").write_text(
                    "todo text\n", encoding="utf-8"
                )
                (root / "docs" / "reports" / "REVALIDATION_SCRIPT_INVENTORY_2026-06-10.json").write_text(
                    json.dumps({"consolidation_signals": inventory_signals}), encoding="utf-8"
                )
                if frontier_candidates is not None:
                    (root / "docs" / "artifacts" / "native-init-frontier-candidates.json").write_text(
                        json.dumps(frontier_candidates), encoding="utf-8"
                    )
                if current_doom_report is not None:
                    (root / "docs" / "reports" / "NATIVE_INIT_V3008_DOOM_INPUT_FRONTIER_RECONCILIATION_2026-06-20.md").write_text(
                        current_doom_report, encoding="utf-8"
                    )
                if current_doom_flash_gate_report is not None:
                    (root / "docs" / "reports" / "NATIVE_INIT_V3010_DOOM_INPUT_FLASH_GATE_ASSETS_2026-06-20.md").write_text(
                        current_doom_flash_gate_report, encoding="utf-8"
                    )
                if current_doom_live_precondition_report is not None:
                    (
                        root
                        / "docs"
                        / "reports"
                        / "NATIVE_INIT_V3012_DOOM_INPUT_LIVE_PRECONDITION_CURRENT_2026-06-20.md"
                    ).write_text(current_doom_live_precondition_report, encoding="utf-8")
                if current_doom_gameplay_loop_report is not None:
                    (
                        root
                        / "docs"
                        / "reports"
                        / "NATIVE_INIT_V3017_DOOMPAD_GAMEPLAY_LOOP_LIVE_2026-06-21.md"
                    ).write_text(current_doom_gameplay_loop_report, encoding="utf-8")
                if current_demo_checkpoint_source_report is not None:
                    (
                        root
                        / "docs"
                        / "reports"
                        / "NATIVE_INIT_V3021_DEMO_CHECKPOINT_BADAPPLE_NYAN_SOURCE_BUILD_2026-06-21.md"
                    ).write_text(current_demo_checkpoint_source_report, encoding="utf-8")
                if current_demo_checkpoint_live_report is not None:
                    (
                        root
                        / "docs"
                        / "reports"
                        / "NATIVE_INIT_V3022_DEMO_CHECKPOINT_BADAPPLE_NYAN_LIVE_2026-06-21.md"
                    ).write_text(current_demo_checkpoint_live_report, encoding="utf-8")
                if current_doomgeneric_policy_report is not None:
                    (
                        root
                        / "docs"
                        / "reports"
                        / "NATIVE_INIT_V3023_DOOMGENERIC_INTEGRATION_POLICY_2026-06-21.md"
                    ).write_text(current_doomgeneric_policy_report, encoding="utf-8")
                if current_doomgeneric_private_build_report is not None:
                    (
                        root
                        / "docs"
                        / "reports"
                        / "NATIVE_INIT_V3024_DOOMGENERIC_PRIVATE_INTEGRATION_BUILD_2026-06-21.md"
                    ).write_text(current_doomgeneric_private_build_report, encoding="utf-8")
                if current_doomgeneric_command_bridge_report is not None:
                    (
                        root
                        / "docs"
                        / "reports"
                        / "NATIVE_INIT_V3025_DOOMGENERIC_COMMAND_BRIDGE_SOURCE_BUILD_2026-06-21.md"
                    ).write_text(current_doomgeneric_command_bridge_report, encoding="utf-8")
                if current_doomgeneric_command_bridge_live_report is not None:
                    (
                        root
                        / "docs"
                        / "reports"
                        / "NATIVE_INIT_V3026_DOOMGENERIC_COMMAND_BRIDGE_LIVE_2026-06-21.md"
                    ).write_text(current_doomgeneric_command_bridge_live_report, encoding="utf-8")
                if current_doomgeneric_runtime_wad_preflight_report is not None:
                    (
                        root
                        / "docs"
                        / "reports"
                        / "NATIVE_INIT_V3027_DOOMGENERIC_RUNTIME_WAD_PREFLIGHT_2026-06-21.md"
                    ).write_text(current_doomgeneric_runtime_wad_preflight_report, encoding="utf-8")
                if current_doomgeneric_sd_wad_stage_report is not None:
                    (
                        root
                        / "docs"
                        / "reports"
                        / "NATIVE_INIT_V3028_DOOMGENERIC_SD_WAD_STAGE_LIVE_2026-06-22.md"
                    ).write_text(current_doomgeneric_sd_wad_stage_report, encoding="utf-8")
                if current_doomgeneric_sd_wad_command_report is not None:
                    (
                        root
                        / "docs"
                        / "reports"
                        / "NATIVE_INIT_V3029_DOOMGENERIC_SD_WAD_COMMAND_SOURCE_BUILD_2026-06-22.md"
                    ).write_text(current_doomgeneric_sd_wad_command_report, encoding="utf-8")
                if current_doomgeneric_sd_wad_command_live_report is not None:
                    (
                        root
                        / "docs"
                        / "reports"
                        / "NATIVE_INIT_V3030_DOOMGENERIC_SD_WAD_COMMAND_LIVE_2026-06-22.md"
                    ).write_text(current_doomgeneric_sd_wad_command_live_report, encoding="utf-8")
                if current_doomgeneric_visible_frame_report is not None:
                    (
                        root
                        / "docs"
                        / "reports"
                        / "NATIVE_INIT_V3031_DOOMGENERIC_VISIBLE_FRAME_SOURCE_BUILD_2026-06-22.md"
                    ).write_text(current_doomgeneric_visible_frame_report, encoding="utf-8")
                self.root = root
                return {
                    "root": root,
                    "goal": root / "GOAL.md",
                    "todo": root / "docs" / "plans" / "NATIVE_INIT_CURRENT_TODO_2026-06-08.md",
                    "inventory": root / "docs" / "reports" / "REVALIDATION_SCRIPT_INVENTORY_2026-06-10.json",
                    "frontier": root / "docs" / "artifacts" / "native-init-frontier-candidates.json",
                    "current_doom": root / "docs" / "reports" / "NATIVE_INIT_V3008_DOOM_INPUT_FRONTIER_RECONCILIATION_2026-06-20.md",
                    "current_doom_flash_gate": root / "docs" / "reports" / "NATIVE_INIT_V3010_DOOM_INPUT_FLASH_GATE_ASSETS_2026-06-20.md",
                    "current_doom_live_precondition": (
                        root
                        / "docs"
                        / "reports"
                        / "NATIVE_INIT_V3012_DOOM_INPUT_LIVE_PRECONDITION_CURRENT_2026-06-20.md"
                    ),
                    "current_doom_gameplay_loop": (
                        root
                        / "docs"
                        / "reports"
                        / "NATIVE_INIT_V3017_DOOMPAD_GAMEPLAY_LOOP_LIVE_2026-06-21.md"
                    ),
                    "current_demo_checkpoint_source": (
                        root
                        / "docs"
                        / "reports"
                        / "NATIVE_INIT_V3021_DEMO_CHECKPOINT_BADAPPLE_NYAN_SOURCE_BUILD_2026-06-21.md"
                    ),
                    "current_demo_checkpoint_live": (
                        root
                        / "docs"
                        / "reports"
                        / "NATIVE_INIT_V3022_DEMO_CHECKPOINT_BADAPPLE_NYAN_LIVE_2026-06-21.md"
                    ),
                    "current_doomgeneric_policy": (
                        root
                        / "docs"
                        / "reports"
                        / "NATIVE_INIT_V3023_DOOMGENERIC_INTEGRATION_POLICY_2026-06-21.md"
                    ),
                    "current_doomgeneric_private_build": (
                        root
                        / "docs"
                        / "reports"
                        / "NATIVE_INIT_V3024_DOOMGENERIC_PRIVATE_INTEGRATION_BUILD_2026-06-21.md"
                    ),
                    "current_doomgeneric_command_bridge": (
                        root
                        / "docs"
                        / "reports"
                        / "NATIVE_INIT_V3025_DOOMGENERIC_COMMAND_BRIDGE_SOURCE_BUILD_2026-06-21.md"
                    ),
                    "current_doomgeneric_command_bridge_live": (
                        root
                        / "docs"
                        / "reports"
                        / "NATIVE_INIT_V3026_DOOMGENERIC_COMMAND_BRIDGE_LIVE_2026-06-21.md"
                    ),
                    "current_doomgeneric_runtime_wad_preflight": (
                        root
                        / "docs"
                        / "reports"
                        / "NATIVE_INIT_V3027_DOOMGENERIC_RUNTIME_WAD_PREFLIGHT_2026-06-21.md"
                    ),
                    "current_doomgeneric_sd_wad_stage": (
                        root
                        / "docs"
                        / "reports"
                        / "NATIVE_INIT_V3028_DOOMGENERIC_SD_WAD_STAGE_LIVE_2026-06-22.md"
                    ),
                    "current_doomgeneric_sd_wad_command": (
                        root
                        / "docs"
                        / "reports"
                        / "NATIVE_INIT_V3029_DOOMGENERIC_SD_WAD_COMMAND_SOURCE_BUILD_2026-06-22.md"
                    ),
                    "current_doomgeneric_sd_wad_command_live": (
                        root
                        / "docs"
                        / "reports"
                        / "NATIVE_INIT_V3030_DOOMGENERIC_SD_WAD_COMMAND_LIVE_2026-06-22.md"
                    ),
                    "current_doomgeneric_visible_frame": (
                        root
                        / "docs"
                        / "reports"
                        / "NATIVE_INIT_V3031_DOOMGENERIC_VISIBLE_FRAME_SOURCE_BUILD_2026-06-22.md"
                    ),
                }

            def __exit__(self, exc_type, exc, tb):
                self.tmp.cleanup()
                return False

        return RepoContext()

    @staticmethod
    def _patch_paths(paths: dict[str, Path]):
        return mock.patch.multiple(
            frontier,
            REPO_ROOT=paths["root"],
            GOAL_PATH=paths["goal"],
            TODO_PATH=paths["todo"],
            INVENTORY_JSON=paths["inventory"],
            FRONTIER_CANDIDATES_JSON=paths["frontier"],
            CURRENT_DOOM_FRONTIER_REPORT=paths["current_doom"],
            CURRENT_DOOM_FLASH_GATE_REPORT=paths["current_doom_flash_gate"],
            CURRENT_DOOM_LIVE_PRECONDITION_REPORT=paths["current_doom_live_precondition"],
            CURRENT_DOOM_GAMEPLAY_LOOP_REPORT=paths["current_doom_gameplay_loop"],
            CURRENT_DEMO_CHECKPOINT_SOURCE_REPORT=paths["current_demo_checkpoint_source"],
            CURRENT_DEMO_CHECKPOINT_LIVE_REPORT=paths["current_demo_checkpoint_live"],
            CURRENT_DOOMGENERIC_POLICY_REPORT=paths["current_doomgeneric_policy"],
            CURRENT_DOOMGENERIC_PRIVATE_BUILD_REPORT=paths["current_doomgeneric_private_build"],
            CURRENT_DOOMGENERIC_COMMAND_BRIDGE_REPORT=paths["current_doomgeneric_command_bridge"],
            CURRENT_DOOMGENERIC_COMMAND_BRIDGE_LIVE_REPORT=paths["current_doomgeneric_command_bridge_live"],
            CURRENT_DOOMGENERIC_RUNTIME_WAD_PREFLIGHT_REPORT=paths["current_doomgeneric_runtime_wad_preflight"],
            CURRENT_DOOMGENERIC_SD_WAD_STAGE_REPORT=paths["current_doomgeneric_sd_wad_stage"],
            CURRENT_DOOMGENERIC_SD_WAD_COMMAND_REPORT=paths["current_doomgeneric_sd_wad_command"],
            CURRENT_DOOMGENERIC_SD_WAD_COMMAND_LIVE_REPORT=paths["current_doomgeneric_sd_wad_command_live"],
            CURRENT_DOOMGENERIC_VISIBLE_FRAME_REPORT=paths["current_doomgeneric_visible_frame"],
        )


if __name__ == "__main__":
    unittest.main()

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

    @staticmethod
    def _fake_repo(
        *,
        inventory_signals: dict[str, object],
        frontier_candidates: dict[str, object] | None,
        current_doom_report: str | None = None,
        current_doom_flash_gate_report: str | None = None,
        current_doom_live_precondition_report: str | None = None,
        current_doom_gameplay_loop_report: str | None = None,
    ):
        class RepoContext:
            def __enter__(self):
                self.tmp = tempfile.TemporaryDirectory()
                root = Path(self.tmp.name)
                (root / "docs" / "plans").mkdir(parents=True)
                (root / "docs" / "reports").mkdir(parents=True)
                (root / "docs" / "artifacts").mkdir(parents=True)
                (root / "GOAL.md").write_text("goal text\n", encoding="utf-8")
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
        )


if __name__ == "__main__":
    unittest.main()

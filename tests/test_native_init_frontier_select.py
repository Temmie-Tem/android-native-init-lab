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
        self.assertIn("native_doominput_keyboard_live_gate_v3004.py --live", evaluation["evidence"]["next_live_command"])

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

    @staticmethod
    def _fake_repo(
        *,
        inventory_signals: dict[str, object],
        frontier_candidates: dict[str, object] | None,
        current_doom_report: str | None = None,
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
                self.root = root
                return {
                    "root": root,
                    "goal": root / "GOAL.md",
                    "todo": root / "docs" / "plans" / "NATIVE_INIT_CURRENT_TODO_2026-06-08.md",
                    "inventory": root / "docs" / "reports" / "REVALIDATION_SCRIPT_INVENTORY_2026-06-10.json",
                    "frontier": root / "docs" / "artifacts" / "native-init-frontier-candidates.json",
                    "current_doom": root / "docs" / "reports" / "NATIVE_INIT_V3008_DOOM_INPUT_FRONTIER_RECONCILIATION_2026-06-20.md",
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
        )


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "workspace/public/src/scripts/revalidation"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import s22plus_fyg8_p284_stock_outer_d1_spec as spec  # noqa: E402


class P284StockOuterD1SpecTests(unittest.TestCase):
    def test_boundary_offsets_are_exact_aligned_and_in_body(self):
        spec.validate_static_spec()
        self.assertEqual(
            tuple(spec.PARENT_SUSPEND_BOUNDARY_OFFSETS.items()),
            (
                ("parent_mutex_acquired", 0x044),
                ("parent_perf_cancel_done", 0x064),
                ("parent_prepare_done", 0x13C),
                ("parent_irq_disabled", 0x144),
                ("parent_hsphy_done", 0x180),
                ("parent_ssphy_done", 0x2E0),
                ("parent_clocks_done", 0x358),
                ("parent_gdsc_done", 0x3E4),
                ("parent_bus_vote_done", 0x3F0),
                ("parent_wake_irq_done", 0x610),
                ("parent_mutex_released", 0x680),
            ),
        )

    def test_boundary_ranking_is_complete_and_perf_cancel_is_demoted(self):
        self.assertEqual(
            tuple(item[0] for item in spec.PARENT_SUSPEND_BOUNDARY_RANKING),
            tuple(range(1, 9)),
        )
        self.assertEqual(
            spec.PARENT_SUSPEND_BOUNDARY_RANKING[0][1],
            "suspend_resume_mutex",
        )
        self.assertEqual(
            spec.PARENT_SUSPEND_BOUNDARY_RANKING[6][1],
            "cancel_delayed_work_sync(perf_vote_work)",
        )

    def test_each_live_stage_precedes_the_recovery_watchdog(self):
        self.assertTrue(
            all(
                deadline < spec.RECOVERY_WATCHDOG_DEADLINE_SEC
                for deadline in (
                    spec.ROLE_WRITE_RETURN_DEADLINE_SEC,
                    spec.CHILD_SUSPENDED_DEADLINE_SEC,
                    spec.CONTROL_OUTER_RETURN_DEADLINE_SEC,
                )
            )
        )

    def test_challenge_stops_when_outer_precedes_suspended_observation(self):
        result = spec.challenge_eligibility(
            none_dispatch_ns=1_000_000,
            child_suspended_observed_ns=4_000_000,
            outer_return_ns=3_000_000,
            measured_reaction_ns=100_000,
        )
        self.assertFalse(result["eligible"])
        self.assertEqual(
            result["reason"],
            "CONTROL_OUTER_RETURNED_BEFORE_REACTOR_READY",
        )

    def test_challenge_stops_below_quantitative_margin(self):
        result = spec.challenge_eligibility(
            none_dispatch_ns=1_000_000,
            child_suspended_observed_ns=4_000_000,
            outer_return_ns=12_000_000,
            measured_reaction_ns=1_000_000,
        )
        self.assertFalse(result["eligible"])
        self.assertEqual(result["reason"], "CONTROL_WINDOW_TOO_SHORT")
        self.assertEqual(result["required_margin_ns"], 10_000_000)

    def test_challenge_is_eligible_only_above_measured_margin(self):
        result = spec.challenge_eligibility(
            none_dispatch_ns=1_000_000,
            child_suspended_observed_ns=4_000_000,
            outer_return_ns=25_000_000,
            measured_reaction_ns=3_000_000,
        )
        self.assertTrue(result["eligible"])
        self.assertEqual(
            result["reason"],
            "CONTROL_WINDOW_INTERVENTION_CAPABLE",
        )
        self.assertEqual(result["required_margin_ns"], 12_000_000)
        self.assertEqual(result["overlap_window_ns"], 21_000_000)

    def test_external_mode_store_writer_is_a_stop_condition(self):
        clean = spec.classify_mode_store_callers(
            (
                spec.ModeStoreCaller(410, "p284-lane"),
                spec.ModeStoreCaller(410, "p284-lane"),
            ),
            expected_writer_pid=410,
            expected_writer_comm=spec.LANE_WRITER_COMM,
        )
        self.assertFalse(clean["external_writer_observed"])
        contaminated = spec.classify_mode_store_callers(
            (
                spec.ModeStoreCaller(410, "p284-lane"),
                spec.ModeStoreCaller(921, "UsbDeviceManager"),
                spec.ModeStoreCaller(410, "p284-lane"),
            ),
            expected_writer_pid=410,
            expected_writer_comm=spec.LANE_WRITER_COMM,
        )
        self.assertTrue(contaminated["external_writer_observed"])
        self.assertEqual(contaminated["external_call_count"], 1)
        self.assertEqual(
            contaminated["external_callers"],
            ({"pid": 921, "comm": "UsbDeviceManager"},),
        )

    def test_invalid_timing_and_pid_inputs_fail_closed(self):
        with self.assertRaises(ValueError):
            spec.challenge_eligibility(
                none_dispatch_ns=2,
                child_suspended_observed_ns=1,
                outer_return_ns=3,
                measured_reaction_ns=1,
            )
        with self.assertRaises(ValueError):
            spec.classify_mode_store_callers(
                (spec.ModeStoreCaller(0, "invalid"),),
                expected_writer_pid=1,
                expected_writer_comm=spec.LANE_WRITER_COMM,
            )
        with self.assertRaisesRegex(ValueError, "frozen lane identity"):
            spec.classify_mode_store_callers(
                (spec.ModeStoreCaller(1, spec.LANE_WRITER_COMM),),
                expected_writer_pid=1,
                expected_writer_comm="shell",
            )


if __name__ == "__main__":
    unittest.main()

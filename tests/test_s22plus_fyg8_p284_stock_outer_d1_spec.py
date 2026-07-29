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
        self.assertEqual(spec.NORMAL_REBOOT_BOOT_START_DEADLINE_SEC, 45)
        self.assertEqual(spec.HARD_RESTART_BOOT_START_DEADLINE_SEC, 45)
        self.assertEqual(spec.HARD_RESTART_MAX_ATTEMPTS, 1)
        self.assertEqual(spec.HARD_RESTART_HOLD_LIMIT_SEC, 15)
        self.assertEqual(
            spec.BOOT_START_SIGNAL,
            "OPERATOR_OBSERVED_SAMSUNG_BOOT_SPLASH",
        )

    def test_two_stage_recovery_waits_then_requests_one_hard_restart(self):
        self.assertEqual(
            spec.classify_recovery_stage(
                normal_reboot_issued=True,
                boot_start_observed=False,
                elapsed_since_last_recovery_action_sec=44,
                hard_restart_attempts=0,
            ),
            "WAIT_NORMAL_REBOOT_BOOT_START",
        )
        self.assertEqual(
            spec.classify_recovery_stage(
                normal_reboot_issued=True,
                boot_start_observed=False,
                elapsed_since_last_recovery_action_sec=45,
                hard_restart_attempts=0,
            ),
            "OPERATOR_HARD_RESTART_ONCE_REQUIRED",
        )
        self.assertEqual(
            spec.classify_recovery_stage(
                normal_reboot_issued=True,
                boot_start_observed=False,
                elapsed_since_last_recovery_action_sec=44,
                hard_restart_attempts=1,
            ),
            "WAIT_HARD_RESTART_BOOT_START",
        )
        self.assertEqual(
            spec.classify_recovery_stage(
                normal_reboot_issued=True,
                boot_start_observed=False,
                elapsed_since_last_recovery_action_sec=45,
                hard_restart_attempts=1,
            ),
            "HARD_RESTART_FAILED_STOP",
        )

    def test_recovery_accepts_only_declared_boot_start_and_one_attempt(self):
        self.assertEqual(
            spec.classify_recovery_stage(
                normal_reboot_issued=False,
                boot_start_observed=True,
                elapsed_since_last_recovery_action_sec=0,
                hard_restart_attempts=0,
            ),
            "SPONTANEOUS_REBOOT_STOP",
        )
        self.assertEqual(
            spec.classify_recovery_stage(
                normal_reboot_issued=True,
                boot_start_observed=True,
                elapsed_since_last_recovery_action_sec=1,
                hard_restart_attempts=0,
            ),
            "BOOT_START_OBSERVED_WAIT_FINAL_HEALTH",
        )
        with self.assertRaisesRegex(ValueError, "one-shot bound"):
            spec.classify_recovery_stage(
                normal_reboot_issued=True,
                boot_start_observed=False,
                elapsed_since_last_recovery_action_sec=0,
                hard_restart_attempts=2,
            )

    def test_tcp_adb_prelude_is_volatile_one_shot_and_reboot_cleared(self):
        spec.validate_static_spec()
        self.assertEqual(
            spec.TCP_ADB_VOLATILE_PROPERTY,
            "service.adb.tcp.port",
        )
        self.assertEqual(spec.TCP_ADB_PORT, 5555)
        self.assertEqual(spec.TCP_ADB_RESTART_CONTROL_PROPERTY, "ctl.restart")
        self.assertEqual(spec.TCP_ADB_RESTART_SERVICE, "adbd")
        self.assertEqual(spec.TCP_ADB_PROPERTY_SET_MAX, 1)
        self.assertEqual(spec.TCP_ADB_RESTART_MAX, 1)
        self.assertEqual(spec.TCP_ADB_PERSIST_PROPERTY, "persist.adb.tcp.port")
        self.assertTrue(spec.TCP_ADB_PERSIST_PROPERTY_FORBIDDEN)
        self.assertEqual(
            spec.TCP_ADB_CLEANUP,
            "ONE_NORMAL_REBOOT_CLEARS_VOLATILE_PROPERTY",
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

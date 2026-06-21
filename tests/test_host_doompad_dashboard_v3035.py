from __future__ import annotations

import unittest
from unittest import mock

from _loader import load_script


dashboard = load_script("workspace/public/src/scripts/revalidation/host_doompad_dashboard_v3035.py")
keyboard = load_script("workspace/public/src/scripts/revalidation/host_doompad_keyboard_v3033.py")


class HostDoompadDashboardV3035Tests(unittest.TestCase):
    def test_dashboard_contract_reuses_v3033_serial_doompad_path(self) -> None:
        self.assertEqual(dashboard.EXPECTED_WAD_SHA256, keyboard.EXPECTED_WAD_SHA256)
        self.assertEqual(dashboard.DEFAULT_LOOP_FRAMES, keyboard.DEFAULT_LOOP_FRAMES)
        self.assertEqual(dashboard.DEFAULT_LOOP_FRAMES, 0)
        self.assertEqual(dashboard.DEFAULT_LOOP_FRAME_MS, 33)
        self.assertEqual(dashboard.DEFAULT_HOLD_MS, 250)
        self.assertEqual(dashboard.DEFAULT_SYSTEM_STATUS_INTERVAL_SEC, 10.0)
        self.assertEqual(dashboard.DEFAULT_SYSTEM_STATUS_IDLE_SEC, 2.0)
        self.assertEqual(
            dashboard.token_for_curses_key(ord("w")),
            "w",
        )
        self.assertEqual(dashboard.token_for_curses_key(dashboard.curses.KEY_UP), "\x1b[A")

    def test_parse_key_value_lines_extracts_native_status_markers(self) -> None:
        text = "\n".join(
            [
                "video.demo.doom.loop_status.active=1",
                "video.demo.doom.loop_status.pid=123",
                "doompad.state seq=7 forward=1 back=0 active=1",
                "thermal: cpu=44.7C 0% gpu=42.8C 0%",
            ]
        )

        values = dashboard.parse_key_value_lines(text)

        self.assertEqual(values["video.demo.doom.loop_status.active"], "1")
        self.assertEqual(values["video.demo.doom.loop_status.pid"], "123")
        self.assertEqual(values["doompad.state seq"], "7 forward=1 back=0 active=1")
        self.assertNotIn("thermal: cpu", values)

    def test_interesting_lines_keeps_dashboard_status_subset(self) -> None:
        text = "\n".join(
            [
                "init: A90 Linux init 0.10.76",
                "thermal: cpu=44.7C 0% gpu=42.8C 0%",
                "video.demo.asset.wad.present=1",
                "A90P1 END seq=1 cmd=status rc=0 status=ok",
            ]
        )

        lines = dashboard.interesting_lines(
            text,
            ("init:", "thermal:", "video.demo.asset.wad."),
        )

        self.assertEqual(
            lines,
            [
                "init: A90 Linux init 0.10.76",
                "thermal: cpu=44.7C 0% gpu=42.8C 0%",
                "video.demo.asset.wad.present=1",
            ],
        )

    def test_loop_frame_estimate_wraps_at_loop_frame_budget(self) -> None:
        state = dashboard.DashboardState(loop_frames=300, loop_frame_ms=50)
        state.loop_started_at = 100.0

        self.assertEqual(dashboard.estimated_loop_frame(state, now=101.0), 20)
        self.assertEqual(dashboard.estimated_loop_frame(state, now=115.0), 0)
        self.assertAlmostEqual(dashboard.target_fps(50), 20.0)

    def test_dashboard_sender_print_only_records_commands_without_device(self) -> None:
        state = dashboard.DashboardState()
        sender = dashboard.DashboardCommandSender(
            state,
            "127.0.0.1",
            54321,
            0.1,
            print_only=True,
        )

        rc = sender.send(["doompad", "key", "fire", "1"])

        self.assertEqual(rc, 0)
        self.assertEqual(sender.sent, [["doompad", "key", "fire", "1"]])
        self.assertEqual(state.command_count, 1)
        self.assertIn("doompad key fire 1", state.logs[-1].message)

    def test_dashboard_fast_read_command_predicate_covers_status_refreshes(self) -> None:
        self.assertTrue(dashboard.is_dashboard_fast_read_command(["status"]))
        self.assertTrue(dashboard.is_dashboard_fast_read_command(["video", "demo", "doom", "status"]))
        self.assertTrue(dashboard.is_dashboard_fast_read_command(["video", "demo", "doom", "loop-status"]))
        self.assertTrue(dashboard.is_dashboard_fast_read_command(["doompad", "status"]))
        self.assertFalse(dashboard.is_dashboard_fast_read_command(["video", "demo", "doom", "loop-start"]))

    def test_light_refresh_omits_heavy_system_status(self) -> None:
        class FakeSender:
            def __init__(self) -> None:
                self.sent: list[list[str]] = []

            def send_result(self, command: list[str]):
                self.sent.append(list(command))
                text_by_command = {
                    ("video", "demo", "doom", "status"): "video.demo.doom.loop.frame_ms=33\n",
                    ("video", "demo", "doom", "loop-status"): "video.demo.doom.loop_status.active=1\n",
                    ("doompad", "status"): "doompad.state seq=9 forward=0 active=0\n",
                }
                return dashboard.a90ctl.ProtocolResult(
                    {},
                    {"rc": "0", "status": "ok", "cmd": command[-1]},
                    text_by_command.get(tuple(command), ""),
                )

        state = dashboard.DashboardState()
        sender = FakeSender()

        dashboard.refresh_light_device_state(sender, state)

        self.assertEqual(
            sender.sent,
            [
                ["video", "demo", "doom", "status"],
                ["video", "demo", "doom", "loop-status"],
                ["doompad", "status"],
            ],
        )
        self.assertEqual(state.loop_frame_ms, 33)
        self.assertTrue(state.loop_active)
        self.assertEqual(state.doompad_kv["doompad.state seq"], "9 forward=0 active=0")

    def test_auto_restart_loop_throttles_active_status_rechecks(self) -> None:
        class FakeSender:
            def __init__(self) -> None:
                self.sent: list[list[str]] = []

            def send_result(self, command: list[str]):
                self.sent.append(list(command))
                return dashboard.a90ctl.ProtocolResult(
                    {},
                    {"rc": "0", "status": "ok", "cmd": command[-1]},
                    "video.demo.doom.loop_status.active=1\n",
                )

        state = dashboard.DashboardState(loop_frames=10, loop_frame_ms=10)
        state.loop_started_at = 1.0
        state.loop_next_check_at = 1.6
        sender = FakeSender()

        with mock.patch.object(dashboard.time, "monotonic", return_value=1.7):
            dashboard.maybe_auto_restart_loop(sender, state, "a" * 64)

        self.assertEqual(sender.sent, [["video", "demo", "doom", "loop-status"]])
        self.assertAlmostEqual(state.loop_next_check_at, 2.2)

    def test_start_loop_zero_frames_marks_continuous_check_window(self) -> None:
        class FakeSender:
            def __init__(self) -> None:
                self.sent: list[list[str]] = []

            def send_result(self, command: list[str]):
                self.sent.append(list(command))
                return dashboard.a90ctl.ProtocolResult(
                    {},
                    {"rc": "0", "status": "ok", "cmd": command[-1]},
                    "",
                )

        state = dashboard.DashboardState(loop_frames=0, loop_frame_ms=33)
        sender = FakeSender()

        with mock.patch.object(dashboard.time, "monotonic", return_value=10.0):
            rc = dashboard.start_loop(sender, state, "a" * 64)

        self.assertEqual(rc, 0)
        self.assertEqual(sender.sent, [keyboard.loop_start_command(0, "a" * 64)])
        self.assertTrue(state.loop_active)
        self.assertEqual(state.loop_started_at, 10.0)
        self.assertEqual(state.loop_next_check_at, 15.0)

    def test_continuous_loop_status_refresh_sets_zero_frame_mode(self) -> None:
        class FakeSender:
            def send_result(self, command: list[str]):
                return dashboard.a90ctl.ProtocolResult(
                    {},
                    {"rc": "0", "status": "ok", "cmd": command[-1]},
                    "\n".join(
                        [
                            "video.demo.doom.loop_status.active=1",
                            "video.demo.doom.loop_status.continuous=1",
                            "video.demo.doom.loop_status.frames=0",
                        ]
                    ),
                )

        state = dashboard.DashboardState(loop_frames=300, loop_frame_ms=33)

        dashboard.refresh_loop_state(FakeSender(), state)

        self.assertTrue(state.loop_active)
        self.assertEqual(state.loop_frames, 0)


if __name__ == "__main__":
    unittest.main()

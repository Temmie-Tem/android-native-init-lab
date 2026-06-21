from __future__ import annotations

import unittest

from _loader import load_script


dashboard = load_script("workspace/public/src/scripts/revalidation/host_doompad_dashboard_v3035.py")
keyboard = load_script("workspace/public/src/scripts/revalidation/host_doompad_keyboard_v3033.py")


class HostDoompadDashboardV3035Tests(unittest.TestCase):
    def test_dashboard_contract_reuses_v3033_serial_doompad_path(self) -> None:
        self.assertEqual(dashboard.EXPECTED_WAD_SHA256, keyboard.EXPECTED_WAD_SHA256)
        self.assertEqual(dashboard.DEFAULT_LOOP_FRAMES, keyboard.DEFAULT_LOOP_FRAMES)
        self.assertEqual(dashboard.DEFAULT_LOOP_FRAME_MS, 50)
        self.assertEqual(dashboard.DEFAULT_HOLD_MS, 250)
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


if __name__ == "__main__":
    unittest.main()

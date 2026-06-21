from __future__ import annotations

import unittest
from unittest import mock

from _loader import load_script


keyboard = load_script("workspace/public/src/scripts/revalidation/host_doompad_keyboard_v3033.py")
dashboard = load_script("workspace/public/src/scripts/revalidation/host_doompad_dashboard_v3035.py")


class HostDoompadFastPathV3042Tests(unittest.TestCase):
    def test_keyboard_sender_uses_fast_path_only_for_doompad_key(self) -> None:
        calls: list[tuple[list[str], bool, float]] = []

        def fake_run(host, port, timeout, command, *, retry_unsafe, require_prompt_after_end, post_marker_drain_sec):
            calls.append((list(command), require_prompt_after_end, post_marker_drain_sec))
            return keyboard.a90ctl.ProtocolResult({}, {"rc": "0", "status": "ok", "cmd": command[0]}, "")

        sender = keyboard.CommandSender("127.0.0.1", 54321, 0.1)
        with mock.patch.object(keyboard.a90ctl, "run_cmdv1_command", side_effect=fake_run):
            self.assertEqual(sender.send(["doompad", "key", "fire", "1"]), 0)
            self.assertEqual(sender.send(["doompad", "status"]), 0)

        self.assertEqual(
            calls,
            [
                (["doompad", "key", "fire", "1"], False, 0.0),
                (["doompad", "status"], True, 0.15),
            ],
        )

    def test_dashboard_sender_uses_keyboard_fast_path_predicate(self) -> None:
        state = dashboard.DashboardState()
        calls: list[tuple[list[str], bool, float]] = []

        def fake_run(host, port, timeout, command, *, retry_unsafe, require_prompt_after_end, post_marker_drain_sec):
            calls.append((list(command), require_prompt_after_end, post_marker_drain_sec))
            return dashboard.a90ctl.ProtocolResult({}, {"rc": "0", "status": "ok", "cmd": command[0]}, "")

        sender = dashboard.DashboardCommandSender(state, "127.0.0.1", 54321, 0.1)
        with mock.patch.object(dashboard.a90ctl, "run_cmdv1_command", side_effect=fake_run):
            self.assertEqual(sender.send(["doompad", "key", "left", "1"]), 0)
            self.assertEqual(sender.send(["video", "demo", "doom", "status"]), 0)

        self.assertEqual(
            calls,
            [
                (["doompad", "key", "left", "1"], False, 0.0),
                (["video", "demo", "doom", "status"], True, 0.15),
            ],
        )


if __name__ == "__main__":
    unittest.main()

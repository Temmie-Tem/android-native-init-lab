from __future__ import annotations

import unittest

from _loader import load_script


keyboard = load_script("workspace/public/src/scripts/revalidation/host_doompad_keyboard_v3033.py")


class HostDoompadEvdevV3055Tests(unittest.TestCase):
    def test_proc_bus_input_parser_finds_keyboard_event_devices(self) -> None:
        sample = """
I: Bus=0011 Vendor=0001 Product=0001 Version=ab41
N: Name="AT Translated Set 2 keyboard"
H: Handlers=sysrq kbd event3 leds
B: EV=120013

I: Bus=0003 Vendor=1234 Product=5678 Version=0111
N: Name="Generic Mouse"
H: Handlers=mouse0 event7
B: EV=17
"""

        devices = keyboard.parse_proc_bus_input_devices(sample)

        self.assertEqual(len(devices), 2)
        self.assertEqual(devices[0].path, "/dev/input/event3")
        self.assertEqual(devices[0].name, "AT Translated Set 2 keyboard")
        self.assertTrue(devices[0].is_keyboard)
        self.assertEqual(devices[1].path, "/dev/input/event7")
        self.assertFalse(devices[1].is_keyboard)

    def test_evdev_role_mapping_uses_real_down_up_and_ignores_repeats(self) -> None:
        self.assertEqual(
            keyboard.role_for_evdev_event(keyboard.EV_KEY, 17, keyboard.EVDEV_KEY_DOWN),
            ("forward", True),
        )
        self.assertEqual(
            keyboard.role_for_evdev_event(keyboard.EV_KEY, 17, keyboard.EVDEV_KEY_UP),
            ("forward", False),
        )
        self.assertIsNone(
            keyboard.role_for_evdev_event(keyboard.EV_KEY, 17, keyboard.EVDEV_KEY_REPEAT)
        )
        self.assertIsNone(keyboard.role_for_evdev_event(0, 17, keyboard.EVDEV_KEY_DOWN))

    def test_session_explicit_role_state_sends_only_on_edges(self) -> None:
        class FakeSender:
            def __init__(self) -> None:
                self.sent: list[list[str]] = []

            def send(self, command: list[str]) -> int:
                self.sent.append(list(command))
                return 0

        sender = FakeSender()
        session = keyboard.DoompadKeyboardSession(sender, hold_ms=110)

        self.assertTrue(session.set_role("forward", True))
        self.assertFalse(session.set_role("forward", True))
        self.assertTrue(session.set_role("fire", True))
        self.assertTrue(session.set_role("forward", False))
        self.assertTrue(session.set_role("fire", False))

        self.assertEqual(
            sender.sent,
            [
                ["doompad", "state", "1", "0x01"],
                ["doompad", "state", "2", "0x11"],
                ["doompad", "state", "3", "0x10"],
                ["doompad", "state", "4", "0x00"],
            ],
        )


if __name__ == "__main__":
    unittest.main()

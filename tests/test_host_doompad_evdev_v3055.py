from __future__ import annotations

import contextlib
import io
import struct
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

    def test_udp_input_packet_is_fixed_little_endian_state_mask(self) -> None:
        self.assertEqual(
            keyboard.doompad_input_packet(12, 0x91),
            struct.pack("<IIIII", 0x41394450, 1, 12, 0x91, 1),
        )
        self.assertEqual(
            keyboard.doompad_input_packet(13, 0x00),
            struct.pack("<IIIII", 0x41394450, 1, 13, 0x00, 0),
        )

    def test_udp_sender_accepts_only_batched_state_commands(self) -> None:
        sender = keyboard.UdpInputSender("192.168.7.2", 30570, print_only=True)
        stdout = io.StringIO()

        with contextlib.redirect_stdout(stdout):
            rc = sender.send(["doompad", "state", "7", "0x11"])

        self.assertEqual(rc, 0)
        self.assertEqual(sender.sent, [["doompad", "state", "7", "0x11"]])
        self.assertIn("udp 192.168.7.2:30570 seq=7 mask=0x11 bytes=20", stdout.getvalue())
        with self.assertRaises(ValueError):
            sender.send(["doompad", "key", "forward", "1"])

    def test_loop_keeper_treats_active_loop_start_busy_as_success(self) -> None:
        class FakeSender:
            def __init__(self) -> None:
                self.sent: list[tuple[list[str], bool]] = []

            def send_result(self, command: list[str], *, fast: bool = False):
                self.sent.append((list(command), fast))
                return keyboard.a90ctl.ProtocolResult(
                    {},
                    {"rc": "-16", "status": "error", "cmd": "video"},
                    "\n".join(
                        [
                            "video.demo.doom.loop_start.active=1",
                            "video.demo.doom.loop_start.pid=3599",
                            "video.demo.doom.loop_start.rc=-16",
                        ]
                    ),
                )

        sender = FakeSender()
        keeper = keyboard.DoomLoopKeeper(
            sender,
            loop_frames=0,
            frame_ms=33,
            sha256="a" * 64,
            restart_grace_ms=500,
        )

        rc = keeper.start(now=10.0)

        self.assertEqual(rc, 0)
        self.assertEqual(sender.sent, [(keyboard.loop_start_command(0, "a" * 64), True)])
        self.assertEqual(keeper.loop_started_at, 10.0)


if __name__ == "__main__":
    unittest.main()

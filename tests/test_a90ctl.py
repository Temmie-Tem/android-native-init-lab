from __future__ import annotations

import json
import os
import unittest
from unittest import mock

from _loader import load_script


a90ctl = load_script("workspace/public/src/scripts/revalidation/a90ctl.py")


class A90CtlProtocolHelperTests(unittest.TestCase):
    def test_parse_fields_and_protocol_properties(self) -> None:
        fields = a90ctl.parse_fields("seq=2 ignored cmd=status rc=0x10 status=ok value=a=b")
        self.assertEqual(
            fields,
            {"seq": "2", "cmd": "status", "rc": "0x10", "status": "ok", "value": "a=b"},
        )
        result = a90ctl.ProtocolResult(begin={}, end=fields, text="payload")
        self.assertEqual(result.rc, 16)
        self.assertEqual(result.status, "ok")

    def test_shell_command_to_argv_accepts_quotes_and_rejects_invalid_or_empty(self) -> None:
        self.assertEqual(
            a90ctl.shell_command_to_argv("wifi scan --ssid 'temmie 2g'"),
            ["wifi", "scan", "--ssid", "temmie 2g"],
        )
        self.assertIsNone(a90ctl.shell_command_to_argv(""))
        self.assertIsNone(a90ctl.shell_command_to_argv("wifi 'unterminated"))

    def test_legacy_arg_policy(self) -> None:
        self.assertTrue(a90ctl.can_use_legacy_cmdv1_arg("status"))
        self.assertTrue(a90ctl.can_use_legacy_cmdv1_arg("wifi-scan_1"))
        self.assertFalse(a90ctl.can_use_legacy_cmdv1_arg(""))
        self.assertFalse(a90ctl.can_use_legacy_cmdv1_arg("#comment"))
        self.assertFalse(a90ctl.can_use_legacy_cmdv1_arg("two words"))
        self.assertFalse(a90ctl.can_use_legacy_cmdv1_arg("line\nbreak"))

    def test_cmdv1_line_uses_legacy_or_cmdv1x_as_needed(self) -> None:
        self.assertEqual(a90ctl.encode_cmdv1_line(["status", "verbose"]), "cmdv1 status verbose")
        self.assertEqual(
            a90ctl.encode_cmdv1_line(["wifi", "scan", "ssid name"]),
            "cmdv1x 4:77696669 4:7363616e 9:73736964206e616d65",
        )
        self.assertEqual(a90ctl.encode_cmdv1x_arg("한"), "3:ed959c")

    def test_cmdv1_line_rejects_missing_bad_name_or_nul(self) -> None:
        for command in ([], ["bad/name"], [""], ["status", "bad\x00arg"]):
            with self.subTest(command=command):
                with self.assertRaises(RuntimeError):
                    a90ctl.encode_cmdv1_line(command)
        with self.assertRaises(RuntimeError):
            a90ctl.encode_cmdv1x_arg("bad\x00arg")

    def test_wire_line_modes(self) -> None:
        self.assertEqual(a90ctl.double_input_line("ab\n"), "aabb\n\n")
        self.assertEqual(a90ctl.encode_wire_line("status", input_mode="normal"), "status")
        self.assertEqual(a90ctl.encode_wire_line("status", input_mode="slow"), "status")
        self.assertEqual(a90ctl.encode_wire_line("status", input_mode="double"), "ssttaattuuss")
        with mock.patch.dict(os.environ, {a90ctl.INPUT_MODE_ENV: "double"}):
            self.assertEqual(a90ctl.encode_wire_line("ok"), "ookk")
        with self.assertRaises(RuntimeError):
            a90ctl.encode_wire_line("status", input_mode="invalid")

    def test_prompt_detection_after_last_end(self) -> None:
        self.assertFalse(a90ctl.has_prompt_after_last_end(bytearray(b"A90P1 END seq=1 cmd=status rc=0")))
        self.assertTrue(
            a90ctl.has_prompt_after_last_end(
                bytearray(b"old\nA90P1 END seq=1 cmd=status rc=0 status=ok\na90:/# ")
            )
        )
        self.assertTrue(
            a90ctl.has_prompt_after_last_end(
                bytearray(b"A90P1 END seq=1 cmd=status rc=0 status=ok\ra90:/# ")
            )
        )

    def test_parse_protocol_output_matches_last_end_to_corresponding_begin(self) -> None:
        text = (
            "noise\n"
            "A90P1 BEGIN seq=1 cmd=status\n"
            "status body\n"
            "A90P1 BEGIN seq=2 cmd=wifi\n"
            "wifi body\n"
            "A90P1 END seq=1 cmd=status rc=0 status=ok\n"
            "A90P1 END seq=2 cmd=wifi rc=5 status=busy\n"
        )
        result = a90ctl.parse_protocol_output(text)
        self.assertEqual(result.begin, {"seq": "2", "cmd": "wifi"})
        self.assertEqual(result.end["cmd"], "wifi")
        self.assertEqual(result.rc, 5)
        self.assertEqual(result.status, "busy")

    def test_parse_protocol_output_allows_missing_begin_but_requires_end(self) -> None:
        result = a90ctl.parse_protocol_output("body\nA90P1 END seq=7 cmd=status rc=0 status=ok\n")
        self.assertEqual(result.begin, {})
        self.assertEqual(result.end["seq"], "7")
        with self.assertRaisesRegex(RuntimeError, "A90P1 END marker not found"):
            a90ctl.parse_protocol_output("A90P1 BEGIN seq=1 cmd=status\nbody\n")

    def test_validate_protocol_command_rejects_mismatched_command(self) -> None:
        result = a90ctl.ProtocolResult(
            begin={"cmd": "status"},
            end={"cmd": "wifi", "rc": "0", "status": "ok"},
            text="raw output",
        )
        with self.assertRaisesRegex(RuntimeError, "command mismatch"):
            a90ctl.validate_protocol_command(result, ["status"])
        a90ctl.validate_protocol_command(result, [])

    def test_retry_policy_marks_observation_commands_only(self) -> None:
        self.assertTrue(a90ctl.command_allows_retry(["status"]))
        self.assertTrue(a90ctl.command_allows_retry(["wifi", "scan"]))
        self.assertFalse(a90ctl.command_allows_retry(["setprop"]))
        self.assertFalse(a90ctl.command_allows_retry([]))
        self.assertTrue(a90ctl.should_retry_cmdv1_exchange(""))
        self.assertTrue(a90ctl.should_retry_cmdv1_exchange(f"x {a90ctl.BRIDGE_BUSY_TEXT} y"))
        self.assertFalse(a90ctl.should_retry_cmdv1_exchange("A90P1 END seq=1 cmd=status rc=0"))
        with mock.patch.dict(os.environ, {a90ctl.INPUT_MODE_ENV: "double"}):
            self.assertTrue(a90ctl.should_retry_cmdv1_exchange("[err] unknown command: ssttaattuuss"))

    def test_result_to_json_includes_derived_rc_and_status(self) -> None:
        result = a90ctl.ProtocolResult(
            begin={"seq": "1", "cmd": "status"},
            end={"seq": "1", "cmd": "status", "rc": "0", "status": "ok"},
            text="A90P1 END seq=1 cmd=status rc=0 status=ok\n",
        )
        payload = json.loads(a90ctl.result_to_json(result))
        self.assertEqual(payload["begin"], {"seq": "1", "cmd": "status"})
        self.assertEqual(payload["end"]["cmd"], "status")
        self.assertEqual(payload["rc"], 0)
        self.assertEqual(payload["status"], "ok")
        self.assertIn("A90P1 END", payload["text"])

    def test_run_cmdv1_command_retries_safe_empty_exchange_then_succeeds(self) -> None:
        responses = ["", "A90P1 BEGIN seq=1 cmd=status\nbody\nA90P1 END seq=1 cmd=status rc=0 status=ok\n"]
        calls: list[str] = []

        def fake_bridge(host, port, line, timeout, *, markers, require_prompt_after_end, post_marker_drain_sec):
            calls.append(line)
            return responses.pop(0)

        with mock.patch.object(a90ctl, "bridge_exchange", side_effect=fake_bridge), \
                mock.patch.object(a90ctl, "sleep_before_retry", return_value=None):
            result = a90ctl.run_cmdv1_command("127.0.0.1", 54321, 2.0, ["status"])

        self.assertEqual(result.status, "ok")
        self.assertEqual(calls, ["cmdv1 status", "cmdv1 status"])

    def test_run_cmdv1_command_can_skip_prompt_and_drain_for_fast_input(self) -> None:
        calls: list[tuple[bool, float]] = []

        def fake_bridge(host, port, line, timeout, *, markers, require_prompt_after_end, post_marker_drain_sec):
            calls.append((require_prompt_after_end, post_marker_drain_sec))
            return "A90P1 BEGIN seq=1 cmd=doompad\nA90P1 END seq=1 cmd=doompad rc=0 status=ok\n"

        with mock.patch.object(a90ctl, "bridge_exchange", side_effect=fake_bridge):
            result = a90ctl.run_cmdv1_command(
                "127.0.0.1",
                54321,
                2.0,
                ["doompad", "key", "fire", "1"],
                retry_unsafe=True,
                require_prompt_after_end=False,
                post_marker_drain_sec=0.0,
            )

        self.assertEqual(result.status, "ok")
        self.assertEqual(calls, [(False, 0.0)])

    def test_run_cmdv1_command_does_not_retry_unsafe_busy_response(self) -> None:
        with mock.patch.object(a90ctl, "bridge_exchange", return_value=a90ctl.BRIDGE_BUSY_TEXT) as bridge:
            with self.assertRaisesRegex(RuntimeError, "unsafe command"):
                a90ctl.run_cmdv1_command("127.0.0.1", 54321, 1.0, ["setprop", "x", "y"])
        bridge.assert_called_once()


if __name__ == "__main__":
    unittest.main()

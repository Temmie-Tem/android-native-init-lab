from __future__ import annotations

from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
REVALIDATION = ROOT / "workspace/public/src/scripts/revalidation"
if str(REVALIDATION) not in sys.path:
    sys.path.insert(0, str(REVALIDATION))

import s22plus_fyg8_p327_framed_exec_runtime as p327  # noqa: E402
import s22plus_fyg8_p330_auth_exec_runtime as p330  # noqa: E402
import s22plus_fyg8_p332_logical_resident_exec_runtime as runtime  # noqa: E402


TEST_KEY = bytes(range(32))


class P332LogicalResidentExecRuntimeTests(unittest.TestCase):
    @staticmethod
    def p330_source() -> bytes:
        raw = (
            p327.P327_HELPER
            + p327.PUBLISHER
            + p327.P327_ENTRY
            + b"s22plus_max77705_p319_stock_encode"
        )
        return p330.transform_runtime_include(raw, TEST_KEY)

    def test_transform_changes_only_p330_publisher_entry(self) -> None:
        before = self.p330_source()
        after = runtime.transform_runtime_include(before, TEST_KEY)
        self.assertEqual(
            after, before.replace(runtime.P330_ENTRY, runtime.P332_ENTRY, 1)
        )
        result = runtime.validate_transform(
            before, after, auth_key_sha256=runtime.auth_key_sha256(TEST_KEY)
        )
        self.assertEqual(result["changed_anchors"], ["p330_publisher_entry"])
        self.assertEqual(result["run_id_hex"], runtime.P332_RUN_ID_HEX)
        self.assertEqual(result["predecessor"]["run_id_hex"], p330.P330_RUN_ID_HEX)

    def test_two_unrolled_same_fd_sessions_and_failure_gate(self) -> None:
        entry = runtime.P332_ENTRY
        banner = b"s22plus_p318_banner_attempt(tty_fd);"
        console = b"p328_framed_console(tty_fd)"
        self.assertEqual(entry.count(banner), 2)
        self.assertEqual(entry.count(console), 2)
        self.assertIn(b"long p332_first_session_rc = -EIO;", entry)
        first_banner_gate = entry.index(
            b"if (p332_banner_1.outcome == S22PLUS_P318_BANNER_WRITTEN)"
        )
        first_console = entry.index(
            b"p332_first_session_rc = p328_framed_console(tty_fd);"
        )
        second_gate = entry.index(b"if (p332_first_session_rc == 0) {")
        second_banner = entry.index(banner, second_gate)
        self.assertLess(first_banner_gate, first_console)
        self.assertLess(first_console, second_gate)
        self.assertLess(second_gate, second_banner)
        self.assertEqual(entry.count(b"if (p332_first_session_rc == 0) {"), 1)
        for forbidden in (b"for (", b"while (", b"close(", b"open(", b"TCSETS"):
            self.assertNotIn(forbidden, entry)

        result = runtime.validate_p332_runtime(
            self.p330_source().replace(runtime.P330_ENTRY, runtime.P332_ENTRY, 1),
            auth_key_sha256=runtime.auth_key_sha256(TEST_KEY),
        )
        self.assertEqual(result["session_count"], 2)
        self.assertEqual(result["session_transitions"], 1)
        self.assertEqual(result["reconnect_count"], 0)
        self.assertEqual(result["physical_reopen_count"], 0)
        self.assertTrue(result["same_tty_fd"])
        self.assertTrue(result["unrolled_sessions"])
        self.assertFalse(result["session_loop"])
        self.assertFalse(result["close_open"])
        self.assertFalse(result["tty_reconfiguration"])

    def test_p330_helper_hmac_diagnostics_and_commands_are_unchanged(self) -> None:
        self.assertEqual(runtime.P332_HELPER_TEMPLATE, p330.P330_HELPER_TEMPLATE)
        self.assertEqual(runtime.P330_HELPER_TEMPLATE, p330.P330_HELPER_TEMPLATE)
        self.assertEqual(runtime.DEFAULT_COMMANDS[:2], p330.DEFAULT_COMMANDS[:2])
        self.assertEqual(len(runtime.DEFAULT_COMMANDS), 3)
        self.assertIn(runtime.P332_RUN_ID_HEX.encode(), runtime.DEFAULT_COMMANDS[2])
        self.assertNotIn(p330.P330_RUN_ID_HEX.encode(), runtime.DEFAULT_COMMANDS[2])
        self.assertEqual(runtime.P330_DEFAULT_COMMANDS, p330.DEFAULT_COMMANDS)
        self.assertNotIn(b"P331", b" ".join(runtime.DEFAULT_COMMANDS))
        self.assertNotIn(b"c331f1e0a90b5e6d7c8a9b0c1d2e3f9b", b" ".join(runtime.DEFAULT_COMMANDS))
        self.assertEqual(runtime.materialize_helper(TEST_KEY), p330.materialize_helper(TEST_KEY))
        for name in (
            "AUTH_DOMAIN_OPEN",
            "AUTH_DOMAIN_READY",
            "AUTH_DOMAIN_EXEC",
            "AUTH_DOMAIN_CLOSE",
            "FRAME_MAGIC",
            "FRAME_VERSION",
            "FRAME_OPEN",
            "FRAME_EXEC",
            "FRAME_CLOSE",
            "FRAME_AUTH",
            "FRAME_READY",
            "FRAME_DATA",
            "FRAME_EXIT",
            "FRAME_DONE",
            "FRAME_CHALLENGE",
            "FRAME_HEADER_SIZE",
            "MAX_FRAME_PAYLOAD",
            "MAX_COMMAND_SIZE",
            "MAX_COMMANDS",
            "COMMAND_TIMEOUT_SEC",
            "MAX_OUTPUT_BYTES",
            "DIAGNOSTIC_FRAME_TYPE",
            "DIAGNOSTIC_STAGE_OPEN_PARSED",
            "DIAGNOSTIC_STAGE_RNG",
            "RNG_EAGAIN_RETRY_LIMIT",
        ):
            self.assertEqual(getattr(runtime, name), getattr(p330, name), name)

    def test_fresh_identity_and_metadata_are_p332(self) -> None:
        self.assertEqual(
            runtime.P332_RUN_ID_HEX,
            "c332f1e0a90b5e6d7c8a9b0c1d2e3f8b",
        )
        self.assertNotEqual(runtime.P332_RUN_ID_HEX, p330.P330_RUN_ID_HEX)
        self.assertIn(runtime.P332_RUN_ID_HEX.encode(), runtime.DEVICE_BANNER)
        self.assertNotIn(p330.P330_RUN_ID_HEX.encode(), runtime.DEVICE_BANNER)
        self.assertEqual(runtime.SESSION_COUNT, 2)
        self.assertEqual(runtime.SESSION_TRANSITIONS, 1)
        self.assertEqual(runtime.RECONNECT_COUNT, 0)
        self.assertEqual(runtime.MAX_RECONNECTS, 0)
        self.assertEqual(runtime.PHYSICAL_REOPEN_COUNT, 0)
        self.assertEqual(runtime.MAX_PHYSICAL_REOPENS, 0)
        self.assertNotIn(p330.P330_RUN_ID_HEX.encode(), b" ".join(runtime.DEFAULT_COMMANDS))
        self.assertNotIn(b"P331", b" ".join(runtime.DEFAULT_COMMANDS))
        source = Path(runtime.__file__).read_bytes()
        self.assertNotIn(TEST_KEY.hex().encode(), source)
        self.assertIn(runtime.AUTH_KEY_PLACEHOLDER.encode(), runtime.P332_HELPER_TEMPLATE)

    def test_first_session_failure_and_extra_delta_are_rejected(self) -> None:
        before = self.p330_source()
        after = runtime.transform_runtime_include(before, TEST_KEY)
        mutated = after.replace(
            b"if (p332_first_session_rc == 0) {",
            b"if (p332_first_session_rc != 0) {",
            1,
        )
        with self.assertRaises(runtime.P332RuntimeError):
            runtime.validate_transform(before, mutated)
        with self.assertRaises(runtime.P332RuntimeError):
            runtime.transform_runtime_include(before, bytes([0]) * 32)

    def test_transform_artifacts_changes_only_runtime_key(self) -> None:
        before = self.p330_source()
        source = {runtime.RUNTIME_KEY: before, "unchanged": b"fixture"}
        result = runtime.transform_artifacts(source, TEST_KEY)
        self.assertEqual(set(result), set(source))
        self.assertEqual(result["unchanged"], source["unchanged"])
        self.assertEqual(
            result[runtime.RUNTIME_KEY],
            before.replace(runtime.P330_ENTRY, runtime.P332_ENTRY, 1),
        )


if __name__ == "__main__":
    unittest.main()

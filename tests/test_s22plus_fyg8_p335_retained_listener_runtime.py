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
import s22plus_fyg8_p332_logical_resident_exec_runtime as p332  # noqa: E402
import s22plus_fyg8_p333_open_entry_diag_runtime as p333  # noqa: E402
import s22plus_fyg8_p334_first_read_rc_runtime as p334  # noqa: E402
import s22plus_fyg8_p335_retained_listener_runtime as runtime  # noqa: E402


TEST_KEY = bytes(range(32))


def p334_source() -> bytes:
    base = (
        p327.P327_HELPER
        + p327.PUBLISHER
        + p327.P327_ENTRY
        + p334.P333_DETAIL_ANCHOR
    )
    p330_source = p330.transform_runtime_include(base, TEST_KEY)
    p332_source = p332.transform_runtime_include(p330_source, TEST_KEY)
    p333_source = p333.transform_runtime_include(p332_source, TEST_KEY)
    return p334.transform_runtime_include(p333_source, TEST_KEY)


class P335RetainedListenerRuntimeTests(unittest.TestCase):
    def test_exact_p334_transform_adds_authenticated_listener_delta(self) -> None:
        before = p334_source()
        after = runtime.transform_runtime_include(before, TEST_KEY)
        expected = before.replace(
            p334.materialize_helper(TEST_KEY),
            runtime.materialize_helper(TEST_KEY),
            1,
        ).replace(p334.P334_ENTRY, runtime.P335_ENTRY, 1).replace(
            p334.P334_DETAIL_ANCHOR, runtime.P335_DETAIL_ANCHOR, 1
        )
        self.assertEqual(after, expected)
        result = runtime.validate_transform(
            before,
            after,
            auth_key_sha256=runtime.auth_key_sha256(TEST_KEY),
        )
        self.assertEqual(
            result["changed_anchors"],
            [
                "p334_authenticated_helper",
                "p334_publisher_entry",
                "p334_stock_terminal_detail",
            ],
        )
        self.assertEqual(
            result["run_id_hex"], "c335f1e0a90b5e6d7c8a9b0c1d2e3f5b"
        )
        self.assertTrue(result["per_boot_identity"])
        self.assertFalse(result["listener_replays_commands"])

    def test_helper_binds_boot_frame_and_exact_three_command_sequences(self) -> None:
        helper = runtime.P335_HELPER_TEMPLATE
        for anchor in (
            b"#define P335_FRAME_BOOT_ID 0x87U",
            b"#define P335_BOOT_ID_SEQUENCE 2U",
            b"#define P335_BOOT_ID_SIZE 32U",
            b"#define P335_COMMANDS_PER_SESSION 3U",
            b"#define P335_DETAIL_BOOT_ID 0xc350U",
            b"#define P335_DETAIL_LISTENER_PROTOCOL 0xc353U",
            b"p335_auth_domain_boot_id",
            b"p335_getrandom_boot_id",
            b"p335_command_valid(sequence, input, input_length)",
            b"expected_sequence = 3U",
            b"p335_framed_console(",
        ):
            self.assertIn(anchor, helper)
        self.assertEqual(runtime.P335_ENTRY.count(b"for (;;) {"), 1)
        self.assertEqual(
            runtime.P335_ENTRY.count(b"p335_framed_console("), 3
        )
        self.assertEqual(
            runtime.P335_ENTRY.count(b"s22plus_p318_banner_attempt(tty_fd);"), 3
        )
        self.assertNotIn(b"close(", runtime.P335_ENTRY)
        self.assertNotIn(b"open(", runtime.P335_ENTRY)
        self.assertNotIn(b"-EPIPE", helper)
        self.assertNotIn(b"p334_first_console_called", runtime.P335_DETAIL_ANCHOR)
        self.assertNotIn(b"p334_first_session_rc", runtime.P335_DETAIL_ANCHOR)

    def test_mutated_helper_or_entry_is_rejected_without_broad_fallback(self) -> None:
        before = p334_source()
        after = runtime.transform_runtime_include(before, TEST_KEY)
        mutations = (
            (b"P335_FRAME_BOOT_ID 0x87U", b"P335_FRAME_BOOT_ID 0x88U"),
            (b"expected_sequence = 3U", b"expected_sequence = 4U"),
            (b"p335_command_valid(sequence, input, input_length)", b"p335_command_valid(input, input_length)"),
        )
        for old, new in mutations:
            with self.subTest(old=old):
                self.assertEqual(after.count(old), 1)
                with self.assertRaises(runtime.P335RuntimeError):
                    runtime.validate_transform(
                        before,
                        after.replace(old, new, 1),
                        auth_key_sha256=runtime.auth_key_sha256(TEST_KEY),
                    )
        mutated_entry = runtime.P335_ENTRY.replace(b"        for (;;) {\n", b"        while (1) {\n", 1)
        with self.assertRaises(runtime.P335RuntimeError):
            runtime.validate_transform(
                before,
                after.replace(runtime.P335_ENTRY, mutated_entry, 1),
                auth_key_sha256=runtime.auth_key_sha256(TEST_KEY),
            )

    def test_predecessor_and_key_identity_are_strict(self) -> None:
        source = p334_source()
        with self.assertRaises(runtime.P335RuntimeError):
            runtime.transform_runtime_include(source[:-1], TEST_KEY)
        with self.assertRaises(runtime.P335RuntimeError):
            runtime.transform_runtime_include(source, b"x" * 31)
        with self.assertRaises(runtime.P335RuntimeError):
            runtime.validate_p335_runtime(
                runtime.transform_runtime_include(source, TEST_KEY).replace(
                    runtime.P335_ENTRY, p334.P334_ENTRY, 1
                )
            )


if __name__ == "__main__":
    unittest.main()

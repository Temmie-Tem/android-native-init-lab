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
import s22plus_fyg8_p333_open_entry_diag_runtime as runtime  # noqa: E402


TEST_KEY = bytes(range(32))


def p332_source() -> bytes:
    base = (
        p327.P327_HELPER
        + p327.PUBLISHER
        + p327.P327_ENTRY
        + b"s22plus_max77705_p319_stock_encode"
    )
    p330_source = p330.transform_runtime_include(base, TEST_KEY)
    return p332.transform_runtime_include(p330_source, TEST_KEY)


class P333OpenEntryDiagnosticRuntimeTests(unittest.TestCase):
    def test_exact_one_anchor_transform_and_restore(self) -> None:
        before = p332_source()
        after = runtime.transform_runtime_include(before, TEST_KEY)
        self.assertEqual(
            after, before.replace(runtime.P332_ENTRY, runtime.P333_ENTRY, 1)
        )
        result = runtime.validate_transform(
            before,
            after,
            auth_key_sha256=runtime.auth_key_sha256(TEST_KEY),
        )
        self.assertEqual(result["changed_anchors"], ["p332_publisher_entry"])
        self.assertEqual(result["entry_diagnostic_stage"], 0)
        self.assertEqual(result["entry_diagnostic_count"], 2)

    def test_entry_diagnostic_precedes_each_out_of_line_call(self) -> None:
        entry = runtime.P333_ENTRY
        diagnostic = b"p330_write_diagnostic(tty_fd, 0U, 0) == 0"
        console = b"p328_framed_console(tty_fd)"
        self.assertEqual(entry.count(diagnostic), 2)
        self.assertEqual(entry.count(console), 2)
        first_diag = entry.index(diagnostic)
        first_console = entry.index(console)
        second_diag = entry.index(diagnostic, first_diag + 1)
        second_console = entry.index(console, first_console + 1)
        self.assertLess(first_diag, first_console)
        self.assertLess(first_console, second_diag)
        self.assertLess(second_diag, second_console)
        for forbidden in (b"for (", b"while (", b"close(", b"open(", b"TCSETS"):
            self.assertNotIn(forbidden, entry)

    def test_p332_protocol_and_same_fd_bounds_are_unchanged(self) -> None:
        self.assertEqual(runtime.P333_HELPER_TEMPLATE, p332.P332_HELPER_TEMPLATE)
        self.assertEqual(runtime.DEFAULT_COMMANDS[:2], p332.DEFAULT_COMMANDS[:2])
        self.assertEqual(runtime.MAX_SESSIONS, 2)
        self.assertEqual(runtime.MAX_RECONNECTS, 0)
        self.assertEqual(runtime.PHYSICAL_REOPEN_COUNT, 0)
        for name in (
            "FRAME_MAGIC",
            "FRAME_VERSION",
            "FRAME_OPEN",
            "FRAME_CHALLENGE",
            "DIAGNOSTIC_FRAME_TYPE",
            "DIAGNOSTIC_STAGE_OPEN_PARSED",
            "DIAGNOSTIC_STAGE_RNG",
            "RNG_EAGAIN_RETRY_LIMIT",
            "AUTH_DOMAIN_OPEN",
            "AUTH_DOMAIN_READY",
            "AUTH_DOMAIN_EXEC",
            "AUTH_DOMAIN_CLOSE",
            "MAX_COMMANDS",
            "COMMAND_TIMEOUT_SEC",
            "MAX_OUTPUT_BYTES",
        ):
            self.assertEqual(getattr(runtime, name), getattr(p332, name), name)

    def test_fresh_identity_and_no_secret_in_source(self) -> None:
        self.assertEqual(
            runtime.P333_RUN_ID_HEX,
            "c333f1e0a90b5e6d7c8a9b0c1d2e3f7b",
        )
        self.assertNotEqual(runtime.P333_RUN_ID_HEX, p332.P332_RUN_ID_HEX)
        self.assertIn(runtime.P333_RUN_ID_HEX.encode(), runtime.DEVICE_BANNER)
        self.assertIn(runtime.P333_RUN_ID_HEX.encode(), runtime.DEFAULT_COMMANDS[2])
        source = Path(runtime.__file__).read_bytes()
        self.assertNotIn(TEST_KEY.hex().encode(), source)

    def test_mutation_and_non_runtime_delta_are_rejected(self) -> None:
        before = p332_source()
        after = runtime.transform_runtime_include(before, TEST_KEY)
        changed = after.replace(
            b"p330_write_diagnostic(tty_fd, 0U, 0) == 0",
            b"p330_write_diagnostic(tty_fd, 1U, 0) == 0",
            1,
        )
        with self.assertRaises(runtime.P333RuntimeError):
            runtime.validate_transform(before, changed)
        result = runtime.transform_artifacts(
            {runtime.RUNTIME_KEY: before, "unchanged": b"fixture"}, TEST_KEY
        )
        self.assertEqual(result["unchanged"], b"fixture")
        self.assertEqual(
            result[runtime.RUNTIME_KEY],
            before.replace(runtime.P332_ENTRY, runtime.P333_ENTRY, 1),
        )


if __name__ == "__main__":
    unittest.main()

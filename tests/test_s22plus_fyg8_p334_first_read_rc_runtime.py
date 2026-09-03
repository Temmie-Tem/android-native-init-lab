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
import s22plus_fyg8_p334_first_read_rc_runtime as runtime  # noqa: E402


TEST_KEY = bytes(range(32))


def p333_source() -> bytes:
    base = (
        p327.P327_HELPER
        + p327.PUBLISHER
        + p327.P327_ENTRY
        + runtime.P333_DETAIL_ANCHOR
    )
    p330_source = p330.transform_runtime_include(base, TEST_KEY)
    p332_source = p332.transform_runtime_include(p330_source, TEST_KEY)
    return p333.transform_runtime_include(p332_source, TEST_KEY)


class P334FirstReadReturnCodeRuntimeTests(unittest.TestCase):
    def test_exact_two_outer_anchor_transform_and_restore(self) -> None:
        before = p333_source()
        after = runtime.transform_runtime_include(before, TEST_KEY)
        expected = before.replace(runtime.P333_ENTRY, runtime.P334_ENTRY, 1).replace(
            runtime.P333_DETAIL_ANCHOR, runtime.P334_DETAIL_ANCHOR, 1
        )
        self.assertEqual(after, expected)
        result = runtime.validate_transform(
            before,
            after,
            auth_key_sha256=runtime.auth_key_sha256(TEST_KEY),
        )
        self.assertEqual(
            result["changed_anchors"],
            ["p333_publisher_entry", "stock_terminal_detail"],
        )
        self.assertFalse(result["console_body_changed"])
        self.assertTrue(
            result["first_read_interpretation_requires_stage0_without_stage1"]
        )

    def test_return_code_encoding_is_small_exact_and_reversible(self) -> None:
        cases = {
            0: 0xB000,
            -5: 0xB005,
            -71: 0xB047,
            -110: 0xB06E,
            -4094: 0xBFFE,
        }
        for return_code, detail in cases.items():
            self.assertEqual(
                runtime.encode_first_read_detail(
                    console_called=True, return_code=return_code
                ),
                detail,
            )
            self.assertEqual(
                runtime.decode_first_read_detail(detail),
                {
                    "valid": True,
                    "console_called": True,
                    "return_code": return_code,
                },
            )
        for called, return_code in ((False, -5), (True, 1), (True, -4095)):
            self.assertEqual(
                runtime.encode_first_read_detail(
                    console_called=called, return_code=return_code
                ),
                runtime.P334_DETAIL_SENTINEL,
            )
        self.assertEqual(
            runtime.decode_first_read_detail(runtime.P334_DETAIL_SENTINEL),
            {"valid": False, "console_called": None, "return_code": None},
        )

    def test_console_and_protocol_are_not_modified(self) -> None:
        self.assertEqual(runtime.P334_HELPER_TEMPLATE, p333.P333_HELPER_TEMPLATE)
        self.assertEqual(runtime.DEFAULT_COMMANDS[:2], p333.DEFAULT_COMMANDS[:2])
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
            self.assertEqual(getattr(runtime, name), getattr(p333, name), name)
        for forbidden in (
            b"p328_read_frame",
            b"for (",
            b"while (",
            b"close(",
            b"open(",
            b"TCSETS",
        ):
            self.assertNotIn(forbidden, runtime.P334_ENTRY)

    def test_fresh_identity_and_hostile_mutations_rejected(self) -> None:
        self.assertEqual(runtime.SOURCE, Path(p333.__file__).resolve())
        self.assertEqual(
            runtime.SOURCE_IDENTITY,
            {
                "size": 10_991,
                "sha256": "fb61a41719df431fc465d763eebb63e412f68c95adaa21300f20e8a603ba7397",
            },
        )
        self.assertEqual(
            runtime.P334_RUN_ID_HEX,
            "c334f1e0a90b5e6d7c8a9b0c1d2e3f6b",
        )
        self.assertNotEqual(runtime.P334_RUN_ID_HEX, p333.P333_RUN_ID_HEX)
        before = p333_source()
        after = runtime.transform_runtime_include(before, TEST_KEY)
        for old, new in (
            (b"0xb000U", b"0xc000U"),
            (b"p334_first_session_rc < -4094L", b"p334_first_session_rc < -4095L"),
            (b"p334_first_console_called = 1", b"p334_first_console_called = 0"),
        ):
            with self.assertRaises(runtime.P334RuntimeError):
                runtime.validate_transform(before, after.replace(old, new, 1))
        result = runtime.transform_artifacts(
            {runtime.RUNTIME_KEY: before, "unchanged": b"fixture"}, TEST_KEY
        )
        self.assertEqual(result["unchanged"], b"fixture")


if __name__ == "__main__":
    unittest.main()

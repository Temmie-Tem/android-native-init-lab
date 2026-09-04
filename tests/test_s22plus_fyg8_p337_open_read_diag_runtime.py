from __future__ import annotations

from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "workspace/public/src/scripts/revalidation"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import s22plus_fyg8_p327_framed_exec_runtime as p327  # noqa: E402
import s22plus_fyg8_p330_auth_exec_runtime as p330  # noqa: E402
import s22plus_fyg8_p332_logical_resident_exec_runtime as p332  # noqa: E402
import s22plus_fyg8_p333_open_entry_diag_runtime as p333  # noqa: E402
import s22plus_fyg8_p334_first_read_rc_runtime as p334  # noqa: E402
import s22plus_fyg8_p335_retained_listener_runtime as p335  # noqa: E402
import s22plus_fyg8_p336_long_idle_runtime as p336  # noqa: E402
import s22plus_fyg8_p337_open_read_diag_runtime as p337  # noqa: E402


TEST_KEY = bytes(range(p337.AUTH_KEY_SIZE))


def p335_source() -> bytes:
    base = (
        p327.P327_HELPER
        + p327.PUBLISHER
        + p327.P327_ENTRY
        + p334.P333_DETAIL_ANCHOR
    )
    value = p330.transform_runtime_include(base, TEST_KEY)
    value = p332.transform_runtime_include(value, TEST_KEY)
    value = p333.transform_runtime_include(value, TEST_KEY)
    value = p334.transform_runtime_include(value, TEST_KEY)
    return p335.transform_runtime_include(value, TEST_KEY)


def p336_source() -> bytes:
    return p336.transform_runtime_include(p335_source(), TEST_KEY)


class P337OpenReadDiagnosticRuntimeTests(unittest.TestCase):
    def test_binding_is_fresh_host_only_and_adds_no_retry(self) -> None:
        value = p337.audit_binding()
        self.assertEqual(value["run_id_hex"], p337.P337_RUN_ID_HEX)
        self.assertEqual(
            value["predecessor_run_id"], p337.P336_PREDECESSOR_RUN_ID_HEX
        )
        self.assertNotEqual(
            p337.P337_RUN_ID_HEX, p337.P336_PREDECESSOR_RUN_ID_HEX
        )
        self.assertEqual(
            value["open_read_diagnostic_stage"],
            p337.DIAGNOSTIC_STAGE_OPEN_READ_RESULT,
        )
        self.assertTrue(value["successful_wire_exchange_unchanged"])
        self.assertFalse(value["retry_added"])
        self.assertFalse(value["timeout_changed"])
        self.assertFalse(value["device_contact"])
        self.assertFalse(value["live_authorized"])

    def test_transform_is_one_helper_replacement_and_restores_p336(self) -> None:
        before = p336_source()
        after = p337.transform_runtime_include(before, TEST_KEY)
        receipt = p337.validate_transform(
            before,
            after,
            auth_key_sha256=p337.auth_key_sha256(TEST_KEY),
        )
        self.assertNotEqual(before, after)
        self.assertEqual(receipt["run_id_hex"], p337.P337_RUN_ID_HEX)
        self.assertEqual(
            receipt["changed_anchors"],
            [
                "p336_fixed_command_identity",
                "p335_framed_console_open_read_failure_diagnostic",
            ],
        )
        self.assertEqual(
            receipt["predecessor"]["run_id_hex"],
            p337.P336_PREDECESSOR_RUN_ID_HEX,
        )
        self.assertTrue(receipt["successful_wire_exchange_unchanged"])
        self.assertFalse(receipt["retry_added"])
        self.assertFalse(receipt["timeout_changed"])

        artifacts = {p337.RUNTIME_KEY: before, "unchanged": b"same"}
        transformed = p337.transform_artifacts(artifacts, TEST_KEY)
        self.assertEqual(transformed[p337.RUNTIME_KEY], after)
        self.assertEqual(transformed["unchanged"], artifacts["unchanged"])

    def test_failure_only_diagnostic_has_two_bounded_branches(self) -> None:
        after = p337.transform_runtime_include(p336_source(), TEST_KEY)
        start = after.index(b"static long p335_framed_console(")
        end = after.index(b"    uint32_t rng_retries", start)
        opening = after[start:end]
        self.assertEqual(
            after.count(b"#define P337_DIAG_OPEN_READ_RESULT 3U"), 1
        )
        self.assertEqual(
            after.count(b"#define P337_OPEN_READ_VALIDATION_REJECTED 1"), 1
        )
        self.assertEqual(
            opening.count(b"P337_DIAG_OPEN_READ_RESULT"), 2
        )
        self.assertEqual(opening.count(b"p337_read_code"), 2)
        self.assertEqual(
            opening.count(b"P337_OPEN_READ_VALIDATION_REJECTED"), 1
        )
        self.assertEqual(opening.count(b"P330_DIAG_OPEN_PARSED"), 1)
        self.assertNotIn(b"for (", opening)
        self.assertNotIn(b"while (", opening)
        self.assertNotIn(b"retry", opening.lower())

    def test_success_and_failure_codes_are_disjoint(self) -> None:
        self.assertEqual(
            p337.classify_open_read_diagnostic(
                p337.DIAGNOSTIC_STAGE_OPEN_PARSED, 0
            ),
            "open-accepted",
        )
        self.assertEqual(
            p337.classify_open_read_diagnostic(
                p337.DIAGNOSTIC_STAGE_OPEN_READ_RESULT,
                p337.OPEN_READ_VALIDATION_REJECTED,
            ),
            "open-validation-rejected",
        )
        for code in (-1, -5, -71, -110, -4095):
            with self.subTest(code=code):
                self.assertEqual(
                    p337.classify_open_read_diagnostic(
                        p337.DIAGNOSTIC_STAGE_OPEN_READ_RESULT, code
                    ),
                    "open-read-error",
                )

    def test_invalid_diagnostic_values_fail_closed(self) -> None:
        for stage, code in (
            (True, 0),
            (p337.DIAGNOSTIC_STAGE_OPEN_PARSED, 1),
            (p337.DIAGNOSTIC_STAGE_OPEN_READ_RESULT, 0),
            (p337.DIAGNOSTIC_STAGE_OPEN_READ_RESULT, 2),
            (p337.DIAGNOSTIC_STAGE_OPEN_READ_RESULT, -4096),
            (4, 1),
        ):
            with self.subTest(stage=stage, code=code):
                with self.assertRaises(p337.P337RuntimeError):
                    p337.classify_open_read_diagnostic(stage, code)

    def test_predecessor_and_wrong_key_are_rejected(self) -> None:
        before = p336_source()
        after = p337.transform_runtime_include(before, TEST_KEY)
        with self.assertRaises(p337.P337RuntimeError):
            p337.validate_p337_runtime(before)
        with self.assertRaises(p337.P337RuntimeError):
            p337.validate_p337_runtime(after, auth_key_sha256="0" * 64)
        with self.assertRaises(p337.P337RuntimeError):
            p337.transform_runtime_include(after, TEST_KEY)


if __name__ == "__main__":
    unittest.main()

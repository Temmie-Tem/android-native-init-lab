from __future__ import annotations

from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
REVALIDATION = ROOT / "workspace/public/src/scripts/revalidation"
if str(REVALIDATION) not in sys.path:
    sys.path.insert(0, str(REVALIDATION))

import s22plus_fyg8_p341_open_read_branch_acm_observer as observer  # noqa: E402
import s22plus_fyg8_p341_open_read_branch_runtime as runtime  # noqa: E402
import s22plus_fyg8_p335_retained_listener_acm_observer as encoder  # noqa: E402


class P341ObserverTests(unittest.TestCase):
    def test_no_banner_diagnostic_is_rejected_for_raw_no_proof(self) -> None:
        diagnostic = encoder.encode_frame(
            runtime.DIAGNOSTIC_FRAME_TYPE,
            0,
            runtime.P341_RUN_ID,
        )
        with self.assertRaises(observer.P341ObserverBindingError):
            observer.parse_retained_open_read_branch(diagnostic)

    def test_actual_banner_precedes_stage_zero_and_open_parsed(self) -> None:
        stage_zero = encoder.encode_frame(
            runtime.DIAGNOSTIC_FRAME_TYPE,
            0,
            runtime.P341_RUN_ID,
        )
        stage_zero_payload = observer.HEADER.pack(
            runtime.FRAME_MAGIC,
            runtime.FRAME_VERSION,
            runtime.DIAGNOSTIC_FRAME_TYPE,
            8,
            0,
            0,
        )
        # Use the real encoder so CRC and diagnostic payload are exact.
        stage_zero = encoder.encode_frame(
            runtime.DIAGNOSTIC_FRAME_TYPE,
            0,
            runtime.P341_RUN_ID,
        )
        reason = encoder.encode_frame(
            runtime.DIAGNOSTIC_FRAME_TYPE,
            0,
            runtime.P341_RUN_ID,
        )
        # The encoder's payload is a boot/run frame, not a diagnostic frame;
        # construct diagnostic frames with the inherited codec directly.
        import struct

        def diagnostic(stage: int, code: int) -> bytes:
            payload = struct.pack("<Ii", stage, code)
            return encoder.encode_frame(
                runtime.DIAGNOSTIC_FRAME_TYPE, 0, payload
            )

        raw = runtime.DEVICE_BANNER + diagnostic(0, 0) + diagnostic(3, 1)
        value = observer.parse_retained_open_read_branch(raw)
        self.assertTrue(value["banner_seen"])
        self.assertEqual(value["reason_frame_index"], 1)
        self.assertTrue(value["no_banner_is_raw_no_proof"] is False)
        self.assertFalse(value["candidate_success"])
        self.assertFalse(value["causal_result_allowed"])

    def test_audit_binds_shared_host_first_helper(self) -> None:
        value = observer.audit_binding()
        self.assertEqual(value["run_id_hex"], runtime.P341_RUN_ID_HEX)
        self.assertEqual(value["host_first_source"], runtime.HOST_FIRST_SOURCE_IDENTITY)
        self.assertTrue(value["host_open_before_banner"])
        self.assertTrue(value["no_banner_is_raw_no_proof"])
        self.assertFalse(value["successful_wire_exchange_unchanged"])


if __name__ == "__main__":
    unittest.main()

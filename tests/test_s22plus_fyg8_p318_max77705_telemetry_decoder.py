import sys
import unittest
from dataclasses import replace
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "workspace/public/src/scripts/revalidation"
sys.path.insert(0, str(SCRIPT_DIR))

import s22plus_fyg8_p318_max77705_envelope_qualification as qualified
import s22plus_fyg8_p318_max77705_telemetry as telemetry
import s22plus_fyg8_p318_max77705_telemetry_decoder as decoder


RUN_ID = b"p318decoderfix01"


def classified(event_kind: int, *, pre_gate_events: int = 0):
    result = qualified._result((b"\x80", b"\x80", b"\x80", b"\x80"))  # noqa: SLF001
    envelope = telemetry.encode_envelope(
        binding=qualified._binding(),  # noqa: SLF001
        exec_witness=qualified._exec(),  # noqa: SLF001
        banner=qualified._banner("written", "none", 49),  # noqa: SLF001
        mux_class="pre-nonusb-post-stable-usb",
        result=result,
        latch=replace(  # noqa: SLF001
            qualified._latch(event_kind), pre_gate_events=pre_gate_events
        ),
    )
    record = telemetry.encode_carrier_record(envelope, run_id=RUN_ID)
    return decoder.classify_observation(
        record, expected_profile=decoder.PROFILE, expected_run_id=RUN_ID
    )


class P318Max77705TelemetryDecoderTests(unittest.TestCase):
    def test_latch_snapshot_requires_explicit_pre_gate_count(self):
        with self.assertRaises(TypeError):
            telemetry.LatchSnapshot(
                install_valid=1,
                gate_valid=1,
                event_valid=0,
                event_kind=0,
                install_ns=1,
                gate_ns=2,
                event_ns=0,
                event_raw=0,
            )

    def test_record_alone_remains_pending(self):
        value = classified(1)
        self.assertFalse(value["accepted"])
        self.assertEqual(
            value["classification"],
            "NO_PROOF_OBSERVER_HOST_RECEIPT_REQUIRED",
        )
        self.assertEqual(value["p318_host_receipt_pending_count"], 1)

    def test_complete_same_endpoint_and_host_event_accepts_terminal(self):
        value = decoder.correlate_candidate_receipt(
            classified(1),
            relationship="same",
            authority_state="candidate_approved_exact",
            observation_complete=True,
        )
        self.assertTrue(value["accepted"])
        self.assertEqual(value["classification"], "RETAIN_EXPERIMENT_TERMINAL")
        decoded = value["records"][0]["max77705"]
        self.assertEqual(
            decoded["host_timing_classification"],
            "host_event_observed_consistent_with_endpoint",
        )

    def test_complete_absence_distinguishes_no_event_and_device_event(self):
        silent = decoder.correlate_candidate_receipt(
            classified(0),
            relationship="absent",
            authority_state="candidate_approved_exact",
            observation_complete=True,
        )
        event = decoder.correlate_candidate_receipt(
            classified(1),
            relationship="absent",
            authority_state="candidate_approved_exact",
            observation_complete=True,
        )
        self.assertTrue(silent["accepted"])
        self.assertEqual(silent["classification"], "DEVICE_RESULT_HOST_SILENT")
        self.assertTrue(event["accepted"])
        self.assertEqual(
            event["classification"],
            "DEVICE_RESULT_DWC3_HOST_EVENT_NO_ENDPOINT",
        )

    def test_present_without_latched_event_is_observer_failure(self):
        value = decoder.correlate_candidate_receipt(
            classified(0),
            relationship="same",
            authority_state="candidate_approved_exact",
            observation_complete=True,
        )
        self.assertFalse(value["accepted"])
        self.assertEqual(value["classification"], "NO_PROOF_OBSERVER")

    def test_pre_gate_event_cannot_become_favorable_host_silence(self):
        value = decoder.correlate_candidate_receipt(
            classified(0, pre_gate_events=1),
            relationship="absent",
            authority_state="candidate_approved_exact",
            observation_complete=True,
        )
        self.assertFalse(value["accepted"])
        self.assertEqual(value["classification"], "NO_PROOF_OBSERVER")

    def test_drift_and_incomplete_receipts_do_not_accept(self):
        drift = decoder.correlate_candidate_receipt(
            classified(1),
            relationship="drift",
            authority_state="candidate_approved_exact",
            observation_complete=True,
        )
        incomplete = decoder.correlate_candidate_receipt(
            classified(0),
            relationship="absent",
            authority_state="candidate_approved_exact",
            observation_complete=False,
        )
        self.assertFalse(drift["accepted"])
        self.assertEqual(
            drift["classification"], "NO_PROOF_EXPERIMENT_PRECONDITION"
        )
        self.assertFalse(incomplete["accepted"])
        self.assertEqual(incomplete["classification"], "NO_PROOF_OBSERVER")


if __name__ == "__main__":
    unittest.main()

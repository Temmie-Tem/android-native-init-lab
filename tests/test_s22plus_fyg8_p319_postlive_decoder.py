from __future__ import annotations

import importlib.util
import struct
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REVALIDATION = ROOT / "workspace/public/src/scripts/revalidation"
if str(REVALIDATION) not in sys.path:
    sys.path.insert(0, str(REVALIDATION))

SCRIPT = REVALIDATION / "s22plus_fyg8_p319_postlive_decoder.py"
SPEC = importlib.util.spec_from_file_location("p319_postlive_decoder", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
decoder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(decoder)
carrier = decoder.carrier

RUN_ID = bytes.fromhex("1234567890abcdef1234567890abcdef")


def _slot(
    header: bytes,
    slot_id: int,
    *,
    generation: int,
    stage: int,
    outcome: int,
    item: int,
    detail: int,
) -> bytes:
    body = carrier.SLOT_BODY_STRUCT.pack(
        generation,
        stage,
        outcome,
        item,
        carrier.PAYLOAD_NONE,
        0,
        0,
        detail,
        bytes(carrier.SLOT_PAYLOAD_SIZE),
    )
    return body + struct.pack("<I", carrier._slot_crc(header, slot_id, body))  # noqa: SLF001


def incident_record(*, detail: int = decoder.FAILURE_DETAIL) -> bytes:
    header = carrier._header("E2", RUN_ID)  # noqa: SLF001
    return b"".join(
        (
            header,
            _slot(
                header,
                0,
                generation=decoder.FIRST_GENERATION,
                stage=decoder.FIRST_STAGE,
                outcome=carrier.OUTCOME_PROGRESS,
                item=decoder.FIRST_ITEM,
                detail=0,
            ),
            _slot(
                header,
                1,
                generation=decoder.FAILURE_GENERATION,
                stage=decoder.FAILURE_STAGE,
                outcome=carrier.OUTCOME_FAILURE,
                item=decoder.FAILURE_ITEM,
                detail=detail,
            ),
        )
    )


class P319PostliveDecoderTests(unittest.TestCase):
    def test_structural_validity_is_separate_from_legacy_semantics(self) -> None:
        value = decoder.decode_carrier(incident_record(), expected_run_id=RUN_ID)
        self.assertTrue(value["header_crc_valid"])
        self.assertTrue(value["exact_p319_early_incident"])
        self.assertEqual(
            [slot["structural_status"] for slot in value["slots"]],
            ["valid", "valid"],
        )
        self.assertEqual(value["slots"][0]["legacy_semantic_status"], "valid")
        self.assertEqual(
            value["slots"][1]["legacy_semantic_status"],
            "semantic-out-of-domain",
        )
        self.assertFalse(value["formal_acceptance"])

    def test_nonincident_detail_remains_structural_but_is_not_promoted(self) -> None:
        value = decoder.decode_carrier(
            incident_record(detail=0x6021), expected_run_id=RUN_ID
        )
        self.assertFalse(value["exact_p319_early_incident"])
        self.assertEqual(value["slots"][1]["structural_status"], "valid")
        self.assertEqual(
            value["slots"][1]["legacy_semantic_status"],
            "semantic-out-of-domain",
        )

    def test_crc_mutation_fails_closed(self) -> None:
        record = bytearray(incident_record())
        record[-1] ^= 0x01
        with self.assertRaisesRegex(decoder.DecodeError, "slot CRC"):
            decoder.decode_carrier(bytes(record), expected_run_id=RUN_ID)

    def test_actual_evidence_keeps_formal_result_immutable(self) -> None:
        if not decoder.LIVE_RESULT.exists():
            self.skipTest("private current-run evidence is unavailable")
        value = decoder.build_actual_result()
        self.assertEqual(value["formal_result"]["verdict"], decoder.FORMAL_VERDICT)
        self.assertEqual(
            value["formal_result"]["observer_proof_class"],
            decoder.FORMAL_OBSERVER_PROOF,
        )
        self.assertTrue(value["formal_result"]["unchanged_by_this_decoder"])
        self.assertEqual(
            value["additive_h0_interpretation"]["evidence_class"], "SUPPORTED"
        )
        self.assertEqual(
            value["additive_h0_interpretation"]["smem_attempted_or_loaded"],
            "UNKNOWN",
        )
        self.assertFalse(
            value["additive_h0_interpretation"][
                "usb_stack_execution_claim_allowed"
            ]
        )


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3

from __future__ import annotations

import sys
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "workspace/public/src/scripts/revalidation"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import s22plus_fyg8_p232_e1_latest_stage_design as v1  # noqa: E402
import s22plus_fyg8_p308_telemetry_spec as spec  # noqa: E402
import s22plus_fyg8_p310_carrier_model as model  # noqa: E402


def _run_id() -> bytes:
    return model.model_run_id()


def _first_request(run_id: bytes, **kwargs) -> bytes:
    position = spec.POSITIONS[0]
    return model.encode_request(
        spec.PROFILE,
        position.stage,
        run_id=run_id,
        item_index=position.item_index,
        **kwargs,
    )


class CarrierV2Tests(unittest.TestCase):
    def test_carrier_v2_contract_and_boundary_matrix(self) -> None:
        result = model.validate()
        self.assertTrue(result["verified"])
        self.assertEqual(result["record_size"], 192)
        self.assertEqual(result["header_size"], 32)
        self.assertEqual(result["slot_size"], 80)
        self.assertEqual(result["raw_excerpt_max"], 64)

    def test_v2_request_compatibility_and_v3_payload(self) -> None:
        run_id = _run_id()
        record = model.initialize_record(spec.PROFILE, run_id)
        request_v2 = _first_request(run_id)
        self.assertEqual(len(request_v2), 32)
        self.assertEqual(model.decode_request(request_v2).version, 2)
        request_v3 = _first_request(
            run_id,
            payload_kind=model.PAYLOAD_RAW_EXCERPT,
            payload=b"bounded raw line",
            version=3,
        )
        self.assertEqual(len(request_v3), 100)
        advanced = model.apply_request(record, request_v3)
        self.assertEqual(model.decode_record(advanced)["active"]["payload"], b"bounded raw line")

    def test_embedded_evidence_families_do_not_self_increment_foreign_count(self) -> None:
        run_id = _run_id()
        excerpt = b"|".join(model.ALL_FAMILIES)
        self.assertLessEqual(len(excerpt), model.REQUEST_PAYLOAD_SIZE)
        record = model.apply_request(
            model.initialize_record(spec.PROFILE, run_id),
            _first_request(
                run_id,
                payload_kind=model.PAYLOAD_RAW_EXCERPT,
                payload=excerpt,
                version=3,
            ),
        )
        result = model.classify_observation(
            b"prefix" + record + b"suffix",
            expected_profile=spec.PROFILE,
            expected_run_id=run_id,
        )
        self.assertGreaterEqual(result["embedded_family_count"], len(model.ALL_FAMILIES))
        self.assertEqual(result["foreign_count"], 0)
        self.assertFalse(result["integrity_issue"])

    def test_invalid_outer_record_does_not_shield_nested_family(self) -> None:
        run_id = _run_id()
        record = bytearray(model.initialize_record(spec.PROFILE, run_id))
        record[28] ^= 0x80
        record[48 : 48 + len(model.LEGACY_FAMILIES[0])] = model.LEGACY_FAMILIES[0]
        result = model.classify_observation(
            bytes(record),
            expected_profile=spec.PROFILE,
            expected_run_id=run_id,
        )
        self.assertTrue(result["integrity_issue"])
        self.assertIn("foreign-or-malformed-v2-long-record", result["integrity_issues"])
        self.assertIn("legacy-or-foreign-evidence-family", result["integrity_issues"])

    def test_partial_family_at_snapshot_edges_fails_closed(self) -> None:
        run_id = _run_id()
        for payload in (
            model.LONG_FAMILY[-4:] + b"body",
            b"body" + model.UNSAT_FAMILY[:4],
        ):
            with self.assertRaisesRegex(model.DesignError, "partial evidence family"):
                model.classify_clean_baseline(
                    payload,
                    expected_profile=spec.PROFILE,
                    expected_run_id=run_id,
                )
            result = model.classify_observation(
                payload,
                expected_profile=spec.PROFILE,
                expected_run_id=run_id,
            )
            self.assertTrue(result["integrity_issue"])
            self.assertIn("partial-family-at-snapshot-edge", result["integrity_issues"])

    def test_torn_second_update_falls_back_to_first_committed_generation(self) -> None:
        run_id = _run_id()
        record = model.apply_request(
            model.initialize_record(spec.PROFILE, run_id),
            _first_request(run_id),
        )
        second = spec.POSITIONS[1]
        request = model.encode_request(
            spec.PROFILE,
            second.stage,
            run_id=run_id,
            item_index=second.item_index,
        )
        for phase in ("invalidate", "body"):
            decoded = model.decode_record(model.apply_request(record, request, stop_after=phase))
            self.assertEqual(decoded["active"]["generation"], 1)
            self.assertTrue(decoded["fallback_used"])

    def test_header_crc_is_independent_from_slot_crc(self) -> None:
        run_id = _run_id()
        record = bytearray(model.initialize_record(spec.PROFILE, run_id))
        record[12] ^= 1
        with self.assertRaisesRegex(model.DesignError, "header CRC"):
            model.decode_record(bytes(record))

    def test_historical_v1_decoder_remains_usable_but_v2_rejects_v1(self) -> None:
        run_id = v1.model_run_id("E2")
        old = v1.initialize_record("E2", run_id)
        self.assertEqual(v1.decode_record(old, expected_profile="E2")["active"]["generation"], 0)
        with self.assertRaises(model.DesignError):
            model.decode_record(old)

    def test_only_bounded_precursor_region_changes(self) -> None:
        run_id = _run_id()
        for idx, expected in ((24, model.UNSAT_SIZE), (191, model.UNSAT_SIZE), (192, model.LONG_RECORD_SIZE), (513, model.LONG_RECORD_SIZE)):
            row = model.simulate_initial_visibility(spec.PROFILE, run_id, idx=idx)
            self.assertEqual(row["changed_bytes"], expected)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import sys
import unittest
from functools import lru_cache
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "workspace/public/src/scripts/revalidation"
sys.path.insert(0, str(SCRIPTS))

import s22plus_fyg8_p305_generator as parent  # noqa: E402
import s22plus_fyg8_p305_overlay_contract as parent_contract  # noqa: E402
import s22plus_fyg8_p306_generator as generator  # noqa: E402
import s22plus_fyg8_p306_ipc_spec as spec  # noqa: E402
import s22plus_fyg8_p306_runtime_transform as transform  # noqa: E402
import s22plus_fyg8_p306_telemetry_decoder as decoder  # noqa: E402


@lru_cache(maxsize=1)
def _baseline() -> dict[str, bytes]:
    exact = parent_contract.verify_parent(ROOT)
    return parent.generate_bytes(
        ROOT,
        run_id=bytes.fromhex(exact["run_id"]),
        unsat_tag=bytes.fromhex(exact["unsat_tag_hex"]),
        profile=exact["profile"],
    )


class P306IpcTelemetryTests(unittest.TestCase):
    def test_encoding_fits_fixed_image(self) -> None:
        value = spec.validate()
        self.assertTrue(value["verified"])
        self.assertEqual(spec.CHAIN_DETAIL_MAX, 0xD80)
        self.assertEqual(spec.SUMMARY_DETAIL_MAX, 0x4800)
        self.assertNotEqual(spec.encode_chain(0), 0xD00)

    def test_encoding_round_trip(self) -> None:
        mask = (
            spec.MARKER_MODE_DEVICE
            | spec.MARKER_BSV_SET
            | spec.MARKER_START_GADGET
            | spec.MARKER_PERIPHERAL
        )
        self.assertEqual(spec.decode_chain(spec.encode_chain(mask))["marker_mask"], mask)
        detail = spec.encode_summary(
            condition_mask=spec.CONDITION_BSV_CLEAR,
            bsv_set_count=1,
            start_gadget_count=2,
            peripheral_count=4,
            ordered_chain_complete=True,
        )
        decoded = spec.decode_summary(detail)
        self.assertEqual(decoded["bsv_set_count_bucket"], 1)
        self.assertEqual(decoded["start_gadget_count_bucket"], 2)
        self.assertEqual(decoded["peripheral_count_bucket"], 3)
        self.assertTrue(decoded["ordered_chain_complete"])

    def test_transform_arms_after_dwc3_before_notifier_tail(self) -> None:
        result = transform.transform_artifacts(_baseline())
        wrapper = result["runtime_wrapper"]
        begin = wrapper.index(b"p306_ipc_begin()")
        tail = wrapper.index(b"index = P305_FOLDED_MODULE_INDEX", begin)
        self.assertLess(begin, tail)
        self.assertIn(b"p306_ipc_tail_rc", wrapper[tail:])
        runtime = result["p290_e3_runtime_include"]
        self.assertIn(b"a600000_ssusb/log", runtime)
        self.assertIn(b"XCVR: BSV set", runtime)
        self.assertIn(b"FF StrtGdgt gsync", runtime)
        self.assertIn(b"FF peripheral", runtime)
        self.assertIn(b"p294_publish_final_pair(p306_chain, p306_summary)", runtime)

    def test_transform_preserves_kernel_and_module_plan(self) -> None:
        exact = parent_contract.verify_parent(ROOT)
        result = generator.generate_bytes(
            ROOT,
            run_id=bytes.fromhex(exact["run_id"]),
            unsat_tag=bytes.fromhex(exact["unsat_tag_hex"]),
            profile=exact["profile"],
        )
        baseline = _baseline()
        self.assertEqual(
            {key for key in result if result[key] != baseline[key]},
            generator.DELTA_KEYS,
        )
        self.assertEqual(result["candidate_patch"], baseline["candidate_patch"])
        self.assertEqual(result["plan_header"], baseline["plan_header"])

    def test_transform_fails_closed_on_shape_drift(self) -> None:
        transformed = transform.transform_artifacts(_baseline())
        with self.assertRaises(transform.TransformError):
            transform.transform_artifacts(transformed)

    def test_decoder_requires_the_adjacent_p306_pair(self) -> None:
        run_id = bytes.fromhex("00112233445566778899aabbccddeeff")
        record = decoder.model.initialize_record(spec.PROFILE, run_id)
        chain_detail = spec.encode_chain(
            spec.MARKER_BSV_SET
            | spec.MARKER_START_GADGET
            | spec.MARKER_PERIPHERAL
        )
        summary_detail = spec.encode_summary(
            condition_mask=0,
            bsv_set_count=1,
            start_gadget_count=1,
            peripheral_count=1,
            ordered_chain_complete=True,
        )
        for generation, position in enumerate(decoder.inherited.spec.POSITIONS, 1):
            if generation == spec.CHAIN_ORDINAL + 1:
                outcome = spec.OUTCOME_PROGRESS
                detail = chain_detail
            elif generation == spec.SUMMARY_ORDINAL + 1:
                outcome = spec.OUTCOME_FAILURE
                detail = summary_detail
            else:
                outcome = decoder.model.OUTCOME_PROGRESS
                detail = 0
            request = decoder.model.encode_request(
                spec.PROFILE,
                position.stage,
                run_id=run_id,
                outcome=outcome,
                item_index=position.item_index,
                detail=detail,
            )
            record = decoder.model.apply_request(record, request)
            if generation == spec.SUMMARY_ORDINAL + 1:
                break
        decoded = decoder.decode_record(
            record,
            expected_profile=spec.PROFILE,
            expected_run_id=run_id,
        )
        self.assertIn("p306_pair", decoded)
        self.assertTrue(
            decoded["p306_pair"]["b"]["telemetry"]["ordered_chain_complete"]
        )


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "workspace/public/src/scripts/revalidation"
sys.path.insert(0, str(SCRIPTS))

import s22plus_fyg8_p305_generator as parent  # noqa: E402
import s22plus_fyg8_p305_overlay_contract as parent_contract  # noqa: E402
import device_action_f1_evidence_v2 as evidence  # noqa: E402
import s22plus_fyg8_p307_generator as generator  # noqa: E402
import s22plus_fyg8_p307_qscratch_audit as qscratch_audit  # noqa: E402
import s22plus_fyg8_p307_runtime_transform as transform  # noqa: E402
import s22plus_fyg8_p307_telemetry_decoder as decoder  # noqa: E402
import s22plus_fyg8_p307_telemetry_spec as spec  # noqa: E402


@lru_cache(maxsize=1)
def _baseline() -> dict[str, bytes]:
    exact = parent_contract.verify_parent(ROOT)
    return parent.generate_bytes(
        ROOT,
        run_id=bytes.fromhex(exact["run_id"]),
        unsat_tag=bytes.fromhex(exact["unsat_tag_hex"]),
        profile=exact["profile"],
    )


class P307TelemetryTests(unittest.TestCase):
    def test_encoding_fits_fixed_image(self) -> None:
        value = spec.validate()
        self.assertTrue(value["verified"])
        self.assertEqual(spec.ATTR_VALUE_COUNT, 150)
        self.assertEqual(spec.ATTR_DETAIL_MAX, 0xD95)
        self.assertEqual(spec.QSCRATCH_STATE_COUNT, 25)
        self.assertEqual(spec.SUMMARY_VALUE_COUNT, 4075)
        self.assertEqual(spec.SUMMARY_DETAIL_MAX, 0x4FEB)

    def test_attribution_round_trip_and_causal_limit(self) -> None:
        for cache in range(2):
            for init in range(3):
                for dpdm in range(5):
                    for preclock in range(5):
                        detail = spec.encode_attribution(
                            cache_value=cache,
                            init_state=init,
                            dpdm_state=dpdm,
                            preclock_state=preclock,
                        )
                        decoded = spec.decode_attribution(detail)
                        self.assertEqual(decoded["cache_value"], cache)
                        self.assertEqual(decoded["init_state"], init)
                        self.assertEqual(decoded["dpdm_state"], dpdm)
                        self.assertEqual(decoded["preclock_state"], preclock)
        agreed = spec.decode_attribution(spec.encode_attribution(
            cache_value=1,
            init_state=spec.INIT_REACHED_CSR,
            dpdm_state=0,
            preclock_state=0,
        ))
        self.assertEqual(
            agreed["eud_pair_conclusion"],
            "eud-seen-by-secure-cache-and-phy-init",
        )
        mismatch = spec.decode_attribution(spec.encode_attribution(
            cache_value=1,
            init_state=spec.INIT_REACHED_NO_CSR,
            dpdm_state=0,
            preclock_state=0,
        ))
        self.assertIn("no-causal-conclusion", mismatch["eud_pair_conclusion"])

    def test_qscratch_and_combined_summary_round_trip(self) -> None:
        samples = [
            [],
            [0],
            [1 << 20],
            [(1 << 20) | (1 << 28)],
            [0, 1 << 20],
            [1 << 20] * 8,
        ]
        for values in samples:
            state = spec.encode_qscratch(values)
            decoded = spec.decode_qscratch(state)
            self.assertEqual(decoded["hit_count_bucket"] == 0, not values)
            detail = spec.encode_summary(clock_detail=0xD00, qscratch_state=state)
            summary = spec.decode_summary(detail)
            self.assertEqual(summary["clock_detail"], 0xD00)
            self.assertEqual(summary["qscratch_state"], state)

    def test_transform_is_narrow_and_path_is_singleton(self) -> None:
        result = transform.transform_artifacts(_baseline())
        self.assertEqual(
            {key for key in result if result[key] != _baseline()[key]},
            generator.DELTA_KEYS,
        )
        self.assertEqual(result["candidate_patch"], _baseline()["candidate_patch"])
        self.assertEqual(result["plan_header"], _baseline()["plan_header"])
        self.assertEqual(
            result["p290_e3_runtime_include"].count(
                spec.EUD_CACHE_PATH.encode("ascii")
            ),
            1,
        )
        self.assertEqual(
            result["trace_descriptor_header"].count(b"p307_qscratch"), 2
        )
        self.assertEqual(result["runtime_wrapper"].count(b"p307_read_eud_cache"), 1)

    def test_qscratch_callsite_audit(self) -> None:
        result = qscratch_audit.audit(
            ROOT,
            Path(spec.DWC3_MODULE_PATH),
            "aarch64-linux-gnu-objdump",
            "readelf",
        )
        self.assertTrue(result["verified"])
        self.assertEqual(result["probe"]["offset"], 0x4CC)
        self.assertTrue(result["probe"]["w21_unmodified_from_readback_to_probe"])

    def test_decoder_requires_adjacent_pair(self) -> None:
        run_id = bytes.fromhex("00112233445566778899aabbccddeeff")
        record = decoder.model.initialize_record(spec.PROFILE, run_id)
        attr = spec.encode_attribution(
            cache_value=0,
            init_state=spec.INIT_REACHED_NO_CSR,
            dpdm_state=spec.DPDM_NOT_SEEN,
            preclock_state=spec.PRECLOCK_1_1,
        )
        summary = spec.encode_summary(
            clock_detail=0xD00,
            qscratch_state=spec.encode_qscratch([1 << 20]),
        )
        for generation, position in enumerate(decoder.inherited.inherited.spec.POSITIONS, 1):
            if generation == spec.ATTR_ORDINAL + 1:
                outcome, detail = spec.OUTCOME_PROGRESS, attr
            elif generation == spec.SUMMARY_ORDINAL + 1:
                outcome, detail = spec.OUTCOME_FAILURE, summary
            else:
                outcome, detail = decoder.model.OUTCOME_PROGRESS, 0
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
        self.assertIn("p307_pair", decoded)
        self.assertTrue(decoded["p307_pair"]["observer_complete"])

    def test_process_v2_resolves_inherited_terminal_position(self) -> None:
        self.assertEqual(
            evidence._latest_stage_terminal(decoder, spec.PROFILE),  # noqa: SLF001
            decoder.inherited.inherited.TERMINAL_POSITION[0],
        )


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "workspace/public/src/scripts/revalidation"
sys.path.insert(0, str(SCRIPTS))

import s22plus_fyg8_p307_generator as parent  # noqa: E402
import s22plus_fyg8_p307_overlay_contract as parent_contract  # noqa: E402
import s22plus_fyg8_p308_cross_gate_audit as cross_gate  # noqa: E402
import s22plus_fyg8_p308_generator as generator  # noqa: E402
import s22plus_fyg8_p308_telemetry_decoder as decoder  # noqa: E402
import s22plus_fyg8_p308_telemetry_model as model  # noqa: E402
import s22plus_fyg8_p308_telemetry_spec as spec  # noqa: E402


@lru_cache(maxsize=1)
def _parent_contract() -> dict:
    return parent_contract.verify_intent(ROOT, ROOT / parent_contract.DEFAULT_INTENT)


@lru_cache(maxsize=1)
def _baseline() -> dict[str, bytes]:
    exact = _parent_contract()
    return parent.generate_bytes(
        ROOT,
        run_id=bytes.fromhex(exact["run_id"]),
        unsat_tag=bytes.fromhex(exact["unsat_tag_hex"]),
        profile=exact["profile"],
    )


@lru_cache(maxsize=1)
def _generated() -> dict[str, bytes]:
    exact = _parent_contract()
    return generator.generate_bytes(
        ROOT,
        run_id=bytes.fromhex(exact["run_id"]),
        unsat_tag=bytes.fromhex(exact["unsat_tag_hex"]),
        profile=exact["profile"],
    )


class P308TelemetryTests(unittest.TestCase):
    def test_actual_encoder_output_cardinality(self) -> None:
        result = spec.validate()
        self.assertEqual(result["enumerated_family_value_count"], 5988)
        self.assertEqual(len(spec.attribution_outputs()), 150)
        self.assertEqual(len(spec.clock_outputs()), 163)
        self.assertEqual(len(spec.summary_outputs()), 4075)
        self.assertEqual(len(spec.degraded_outputs()), 1600)

    def test_degraded_round_trip_includes_zero_mask(self) -> None:
        for site in range(spec.FAILURE_SITE_COUNT):
            for mask in (0, spec.PREFIX_MASK_MAX):
                for qscratch in (0, spec.QSCRATCH_STATE_COUNT - 1):
                    detail = spec.encode_degraded(
                        failure_site=site,
                        prefix_mask=mask,
                        qscratch_state=qscratch,
                    )
                    decoded = spec.decode_degraded(detail)
                    self.assertEqual(decoded["failure_site"], site)
                    self.assertEqual(decoded["prefix_mask"], mask)
                    self.assertEqual(decoded["qscratch_state"], qscratch)

    def test_transform_changes_only_runtime_include(self) -> None:
        self.assertEqual(
            {key for key in _generated() if _generated()[key] != _baseline()[key]},
            generator.DELTA_KEYS,
        )
        for key in ("candidate_patch", "plan_header", "trace_descriptor_header"):
            self.assertEqual(_generated()[key], _baseline()[key])
        runtime = _generated()["p290_e3_runtime_include"]
        self.assertIn(b'body_end = p282_find_bytes(', runtime)
        self.assertIn(b'P308_DEGRADED_DETAIL_BASE 0x6100U', runtime)
        self.assertNotIn(b'rc = p307_kmsg_observe(message, message_length);', runtime)

    def test_actual_c_gates_and_parser_execute(self) -> None:
        result = cross_gate.audit(ROOT)
        self.assertTrue(result["verified"])
        self.assertEqual(
            result["telemetry"]["enumerated_family_value_count"], 5988
        )
        self.assertIn("local-degraded-continues=1", result["executed_actual_gates"]["parser"])

    def test_pair_context_disambiguates_d00_and_4fc1(self) -> None:
        normal = cross_gate._apply_pair(0xD00, 0x4FC1)  # noqa: SLF001
        degraded = cross_gate._apply_pair(0xD00, 0x6100)  # noqa: SLF001
        self.assertEqual(normal["p308_pair"]["kind"], "normal")
        self.assertEqual(
            normal["p308_pair"]["a"]["detail_kind"],
            "p308-eud-kmsg-attribution",
        )
        self.assertEqual(
            normal["p308_pair"]["b"]["detail_kind"],
            "p308-clock-qscratch-summary",
        )
        self.assertEqual(degraded["p308_pair"]["kind"], "degraded")
        self.assertEqual(
            degraded["p308_pair"]["a"]["detail_kind"],
            "p308-degraded-clock-witness",
        )

    def test_carrier_v2_raw_excerpt_family_collision_is_explicit(self) -> None:
        run_id = bytes.fromhex("00112233445566778899aabbccddeeff")
        record = model.initialize_record(spec.PROFILE, run_id)
        self.assertEqual(record.count(model.LONG_FAMILY), 1)
        payload_with_unescaped_excerpt = record + model.LONG_FAMILY
        family_count = payload_with_unescaped_excerpt.count(model.LONG_FAMILY)
        exact_record_count = 1
        self.assertEqual(family_count, 2)
        self.assertEqual(max(0, family_count - exact_record_count), 1)


if __name__ == "__main__":
    unittest.main()

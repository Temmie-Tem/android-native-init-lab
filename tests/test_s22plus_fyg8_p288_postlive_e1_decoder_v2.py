from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "workspace/public/src/scripts/revalidation"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import s22plus_fyg8_p288_contract_spec as spec  # noqa: E402
import s22plus_fyg8_p288_e1_decoder as bound_decoder  # noqa: E402
import s22plus_fyg8_p288_latest_stage_model as model  # noqa: E402
import s22plus_fyg8_p288_postlive_e1_decoder_v2 as postlive  # noqa: E402
import s22plus_fyg8_p288_source_contract as source_contract  # noqa: E402


RUN_ID = bytes.fromhex("00112233445566778899aabbccddeeff")


def advance_to(generation: int) -> bytes:
    record = model.initialize_record(spec.PROFILE, RUN_ID)
    for current, position in enumerate(spec.POSITIONS[:generation], 1):
        terminal = current == spec.TERMINAL_GENERATION
        request = model.encode_request(
            spec.PROFILE,
            position.stage,
            run_id=RUN_ID,
            outcome=(
                model.OUTCOME_SUCCESS
                if terminal
                else model.OUTCOME_PROGRESS
            ),
            item_index=position.item_index,
            detail=0,
        )
        record = model.apply_request(record, request)
    return record


class P288PostliveDecoderV2Tests(unittest.TestCase):
    def test_generation_87_zero_progress_is_not_rendered_invalid(self):
        record = advance_to(87)
        bound = bound_decoder.decode_record(
            record,
            expected_profile=spec.PROFILE,
            expected_run_id=RUN_ID,
        )
        self.assertEqual(
            bound["active_semantics"]["detail_kind"], "invalid"
        )

        corrected = postlive.decode_record(
            record,
            expected_profile=spec.PROFILE,
            expected_run_id=RUN_ID,
        )
        self.assertEqual(
            corrected["active_semantics"]["position_name"],
            "inherited_generation_087",
        )
        self.assertEqual(
            corrected["active_semantics"]["detail_kind"], "progress"
        )
        self.assertEqual(
            corrected["active_semantics"]["detail_name"],
            "progress-no-diagnostic-detail",
        )
        self.assertEqual(
            corrected["semantic_renderer"]["base_decoder_id"],
            bound_decoder.DECODER_ID,
        )

    def test_nonzero_progress_detail_semantics_are_unchanged(self):
        record = advance_to(87)
        position = spec.POSITIONS[87]
        request = model.encode_request(
            spec.PROFILE,
            position.stage,
            run_id=RUN_ID,
            outcome=model.OUTCOME_PROGRESS,
            item_index=position.item_index,
            detail=0xC18,
        )
        record = model.apply_request(record, request)
        bound = bound_decoder.decode_record(
            record,
            expected_profile=spec.PROFILE,
            expected_run_id=RUN_ID,
        )
        corrected = postlive.decode_record(
            record,
            expected_profile=spec.PROFILE,
            expected_run_id=RUN_ID,
        )
        self.assertEqual(
            corrected["active_semantics"]["detail_kind"],
            bound["active_semantics"]["detail_kind"],
        )
        self.assertEqual(
            corrected["active_semantics"]["detail_name"],
            bound["active_semantics"]["detail_name"],
        )

    def test_terminal_zero_has_success_semantics(self):
        corrected = postlive.decode_record(
            advance_to(spec.TERMINAL_GENERATION),
            expected_profile=spec.PROFILE,
            expected_run_id=RUN_ID,
        )
        self.assertEqual(
            corrected["active_semantics"]["detail_kind"], "success"
        )
        self.assertEqual(
            corrected["active_semantics"]["detail_name"],
            "terminal-success",
        )

    def test_first_successor_wrapper_has_hidden_prepublication_revalidation(
        self,
    ):
        source = source_contract.source_bytes(ROOT)
        include = source["p288_e3_runtime_include"]
        progress = source_contract._c_function_body(
            include, "p288_progress_position"
        )
        self.assertLess(
            progress.index(b"p260_revalidate_or_fail("),
            progress.index(b"s22_p288_checkpoint_progress_position("),
        )
        restart = source_contract._c_function_body(
            include, "p282_cycle_restart"
        )
        self.assertLess(
            restart.index(b"p282_deadline_after("),
            restart.index(
                b"S22_P288_POSITION_RESTART_HELPER_DISPATCH"
            ),
        )
        self.assertEqual(spec.GATE_COUNT, 12)

    def test_abstract_model_rejects_request_for_already_advanced_record(
        self,
    ):
        # This checks the decoded-record transition model only.  It does not
        # model the exact writer's pre-state-update post-commit -ESTALE path,
        # where kernel and userspace generations have not advanced yet.
        kernel_record = advance_to(88)
        stale_position = spec.POSITIONS[87]
        stale_fallback = model.encode_request(
            spec.PROFILE,
            stale_position.stage,
            run_id=RUN_ID,
            outcome=model.OUTCOME_FAILURE,
            item_index=stale_position.item_index,
            detail=spec.UNCLASSIFIED_DETAIL,
        )
        with self.assertRaisesRegex(
            model.DesignError, "exact next position"
        ):
            model.apply_request(kernel_record, stale_fallback)


if __name__ == "__main__":
    unittest.main()

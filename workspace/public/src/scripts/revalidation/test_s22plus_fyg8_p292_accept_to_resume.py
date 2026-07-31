#!/usr/bin/env python3
"""Focused tests for P2.92 accept-to-resume and errno closure."""

from __future__ import annotations

import unittest

import s22plus_fyg8_p292_accept_to_resume as closure
import s22plus_fyg8_p292_repair_decoder as decoder
import s22plus_fyg8_p292_repair_model as model
import s22plus_fyg8_p292_repair_spec as repair


class AcceptToResumeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = closure.zero.repo_root()

    def test_real_closure_passes(self) -> None:
        result = closure.run_closure(self.root)
        self.assertEqual(result["verdict"], closure.VERDICT)
        self.assertEqual(
            result["accept_to_resume_closure"]["closure_case_count"], 171
        )
        self.assertEqual(
            result["accept_to_resume_sequence_walk"]["snapshot_count"], 214
        )
        self.assertTrue(
            result["checkpoint_errno_observability"]["verified"]
        )
        self.assertTrue(
            result["legacy_seed_and_prefix"][
                "exact_old_generation_88_resumed_to_89"
            ]
        )

    def test_publication_error_model_decoder_round_trip(self) -> None:
        run_id = bytes.fromhex("2ec2bbaeed33025c92a0831c5e82dd3b")
        detail = repair.encode_publication_error(
            repair.OPERATION_WRITE, -116
        )
        record = model.initialize_record(model.PROFILE, run_id)
        request = model.encode_request(
            model.PROFILE,
            0x10,
            run_id=run_id,
            outcome=model.OUTCOME_FAILURE,
            item_index=0,
            detail=detail,
        )
        decoded = decoder.decode_record(
            model.apply_request(record, request),
            expected_run_id=run_id,
        )
        self.assertEqual(
            decoded["active_semantics"]["publication_error"],
            {
                "operation": repair.OPERATION_WRITE,
                "operation_name": "write",
                "errno": -116,
            },
        )

    def test_missing_exact_slot_update_fails(self) -> None:
        def mutate(values):  # noqa: ANN001, ANN202
            patch = values["candidate_patch"]
            token = b"memcpy(&s22_fyg8_e1_state.active, &next,"
            self.assertEqual(patch.count(token), 1)
            values["candidate_patch"] = patch.replace(
                token,
                b"memcpy(&s22_fyg8_e1_state.active, &record->slots[0],",
            )
            return values

        with self.assertRaises(closure.ClosureError):
            closure.run_closure(self.root, mutate=mutate)

    def test_errno_loss_fails(self) -> None:
        def mutate(values):  # noqa: ANN001, ANN202
            client = values["checkpoint_client"]
            token = b"client->publication_error_errno = error;"
            self.assertEqual(client.count(token), 1)
            values["checkpoint_client"] = client.replace(
                token, b"client->publication_error_errno = -1;"
            )
            return values

        with self.assertRaises(closure.ClosureError):
            closure.run_closure(self.root, mutate=mutate)

    def test_missing_volatile_sink_fails(self) -> None:
        def mutate(values):  # noqa: ANN001, ANN202
            wrapper = values["runtime_wrapper"]
            token = b"g_p292_checkpoint_errno_evidence.valid = 1U;"
            self.assertEqual(wrapper.count(token), 1)
            values["runtime_wrapper"] = wrapper.replace(
                token, b"g_p292_checkpoint_errno_evidence.valid = 0U;"
            )
            return values

        with self.assertRaises(closure.ClosureError):
            closure.run_closure(self.root, mutate=mutate)

    def test_runtime_producer_route_loss_fails(self) -> None:
        def mutate(values):  # noqa: ANN001, ANN202
            runtime = values["p290_e3_runtime_include"]
            token = b"p282_cycle_warning_detail(cycle, P282_STAGE_STOP)"
            self.assertEqual(runtime.count(token), 1)
            values["p290_e3_runtime_include"] = runtime.replace(
                token, b"0U"
            )
            return values

        with self.assertRaises(closure.ClosureError):
            closure.run_closure(self.root, mutate=mutate)


if __name__ == "__main__":
    unittest.main()

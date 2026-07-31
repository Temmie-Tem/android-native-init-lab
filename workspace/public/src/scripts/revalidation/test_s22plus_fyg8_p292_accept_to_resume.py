#!/usr/bin/env python3
"""Focused tests for P2.92 accept-to-resume and errno closure."""

from __future__ import annotations

import unittest

import s22plus_fyg8_p292_accept_to_resume as closure
import s22plus_fyg8_p292_repair_decoder as decoder
import s22plus_fyg8_p292_repair_model as model
import s22plus_fyg8_p292_repair_spec as repair


PAIR_HELPER = "p294_publish_final_pair"
PAIR_FIRST = (
    b"s22_p294_checkpoint_progress_position("
    b"&g_checkpoint, S22_P294_POSITION_USBLNKST, first_detail)"
)
PAIR_TERMINAL = (
    b"s22_p294_checkpoint_terminal_position("
    b"&g_checkpoint, S22_P294_POSITION_FINAL_STATE, terminal_detail)"
)
PAIR_RUNTIME = (
    b"static long p294_publish_final_pair(\n"
    b"    uint16_t first_detail, uint16_t terminal_detail) {\n"
    b"    long first_rc = "
    + PAIR_FIRST
    + b";\n"
    b"    if (first_rc != 0) {\n"
    b"        return first_rc;\n"
    b"    }\n"
    b"    return "
    + PAIR_TERMINAL
    + b";\n"
    b"}\n"
    b"\n"
    b"static long p294_publish_captured_values(\n"
    b"    uint16_t link_state, uint16_t final_state) {\n"
    b"    return p294_publish_final_pair(link_state, final_state);\n"
    b"}\n"
)


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
        self.assertEqual(
            result["repository_module_attribute_closure"]["file_count"], 2
        )
        self.assertEqual(
            result["successor_mandatory_gates"],
            list(closure.SUCCESSOR_MANDATORY_GATES),
        )

    def test_repository_module_attribute_gate(self) -> None:
        source = b"""\
import s22plus_fyg8_p282_contract_spec as spec
import s22plus_fyg8_p292_identity_tiers as identity
DETAIL = spec.detail_name(0xc40)
TIERS = identity.path_tiers()
"""
        result = closure.audit_repository_module_attributes(
            source,
            filename="positive-fixture.py",
            repository_root=self.root,
        )
        self.assertEqual(result["verdict"], closure.PYTHON_ATTR_VERDICT)
        self.assertEqual(result["repository_module_count"], 2)

    def test_repository_module_attribute_mistakes_fail_at_ast_gate(
        self,
    ) -> None:
        fixtures = {
            "detail_spec": b"""\
import s22plus_fyg8_p282_contract_spec as spec
VALUE = spec.detail_spec(0xc40)
""",
            "repo_root": b"""\
import s22plus_fyg8_p292_identity_tiers as identity
ROOT = identity.repo_root()
""",
            "shadowed_alias": b"""\
import s22plus_fyg8_p282_contract_spec as spec
def invalid(spec):
    return spec.detail_name(0xc40)
""",
        }
        for name, source in fixtures.items():
            with self.subTest(name=name), self.assertRaises(
                closure.ClosureError
            ):
                closure.audit_repository_module_attributes(
                    source,
                    filename=f"{name}.py",
                    repository_root=self.root,
                )

    def test_pair_publication_adjacency_gate(self) -> None:
        result = closure.audit_pair_publication_adjacency(
            PAIR_RUNTIME,
            helper_name=PAIR_HELPER,
            first_publish_expression=PAIR_FIRST,
            terminal_publish_expression=PAIR_TERMINAL,
        )
        self.assertEqual(result["verdict"], closure.PAIR_ADJACENCY_VERDICT)
        self.assertEqual(
            result["calls_between_first_return_and_terminal_invocation"], 0
        )
        self.assertTrue(
            result["first_failure_returns_without_terminal_attempt"]
        )

    def test_pair_publication_adjacency_mutations_fail_closed(self) -> None:
        mutations = {
            "abort_between": PAIR_RUNTIME.replace(
                b"    return " + PAIR_TERMINAL + b";",
                b"    p290_fail_next(0xcffU);\n"
                b"    return "
                + PAIR_TERMINAL
                + b";",
                1,
            ),
            "failure_path_publishes": PAIR_RUNTIME.replace(
                b"        return first_rc;",
                b"        p290_fail_next(first_rc);",
                1,
            ),
            "reordered": PAIR_RUNTIME.replace(
                PAIR_FIRST, b"PAIR_PLACEHOLDER", 1
            )
            .replace(PAIR_TERMINAL, PAIR_FIRST, 1)
            .replace(b"PAIR_PLACEHOLDER", PAIR_TERMINAL, 1),
            "duplicate_first": PAIR_RUNTIME
            + b"long p294_duplicate(uint16_t first_detail) { return "
            + PAIR_FIRST
            + b"; }\n",
            "caller_missing": PAIR_RUNTIME.split(
                b"static long p294_publish_captured_values", 1
            )[0],
        }
        for name, runtime in mutations.items():
            with self.subTest(name=name), self.assertRaises(
                closure.ClosureError
            ):
                closure.audit_pair_publication_adjacency(
                    runtime,
                    helper_name=PAIR_HELPER,
                    first_publish_expression=PAIR_FIRST,
                    terminal_publish_expression=PAIR_TERMINAL,
                )

    def test_pair_publication_expression_cannot_hide_an_extra_call(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            closure.ClosureError,
            "publication expressions are not canonical",
        ):
            closure.audit_pair_publication_adjacency(
                PAIR_RUNTIME,
                helper_name=PAIR_HELPER,
                first_publish_expression=(
                    b"p294_hidden_publish(), " + PAIR_FIRST
                ),
                terminal_publish_expression=PAIR_TERMINAL,
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

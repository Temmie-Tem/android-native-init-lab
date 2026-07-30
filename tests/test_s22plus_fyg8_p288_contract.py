from __future__ import annotations

import hashlib
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "workspace/public/src/scripts/revalidation"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import device_action_f1_evidence_v2 as typed_evidence  # noqa: E402
import device_action_f1_v2 as process_v2  # noqa: E402
import s22plus_fyg8_p288_change_freeze as change_freeze  # noqa: E402
import s22plus_fyg8_p288_build_repro_check as repro_check  # noqa: E402
import s22plus_fyg8_p286_source_contract as p286_contract  # noqa: E402
import s22plus_fyg8_p288_candidate_intent as candidate_intent  # noqa: E402
import s22plus_fyg8_p288_contract_spec as spec  # noqa: E402
import s22plus_fyg8_p288_e1_decoder as decoder  # noqa: E402
import s22plus_fyg8_p288_e2_stock_closure as stock_closure  # noqa: E402
import s22plus_fyg8_p288_latest_stage_model as model  # noqa: E402
import s22plus_fyg8_p288_linked_audit as linked_audit  # noqa: E402
import s22plus_fyg8_p288_pre_lto_qualification as qualification  # noqa: E402
import s22plus_fyg8_p288_source_contract as source_contract  # noqa: E402


RUN_ID = bytes.fromhex("00112233445566778899aabbccddeeff")


def p288_acceptance() -> dict:
    artifact = {
        "path": "workspace/private/p288-evidence.json",
        "size": 1,
        "sha256": "1" * 64,
    }
    return {
        "kind": typed_evidence.E1_LATEST_STAGE_KIND,
        "source": typed_evidence.CHECKPOINT_SOURCE,
        "decoder": decoder.DECODER_ID,
        "policy_id": decoder.POLICY_ID,
        "profile": spec.PROFILE,
        "run_id": RUN_ID.hex(),
        "long_family_hex": model.LONG_FAMILY.hex(),
        "unsat_family_hex": model.UNSAT_FAMILY.hex(),
        "terminal_stage": spec.TERMINAL_STAGE,
        "minimum_success_count": 1,
        "clean_baseline_required": True,
        "source_contract_id": source_contract.CONTRACT_ID,
        "contract": {
            "candidate_static": artifact,
            "run_manifest": artifact,
            "static_check": artifact,
        },
    }


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


class P288PairContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = source_contract.source_bytes(ROOT)

    def test_generation_is_exact_pair_sequence_index(self):
        self.assertEqual(len(spec.POSITIONS), 103)
        self.assertEqual(spec.TERMINAL_GENERATION, 103)
        self.assertEqual(spec.TERMINAL_ORDINAL, 102)
        self.assertEqual(
            len(set(spec.POSITION_SEQUENCE)),
            len(spec.POSITION_SEQUENCE),
        )
        self.assertEqual(
            tuple(
                (position.stage, position.item_index)
                for position in spec.SUCCESSOR_POSITIONS
            ),
            (
                (0x90, 0),
                (0x90, 1),
                (0x90, 2),
                (0x90, 3),
                (0x90, 4),
                (0x90, 5),
                (0x90, 6),
                (0x90, 7),
                (0x91, 0),
                (0x91, 1),
                (0x91, 2),
                (0x91, 3),
                (0x92, 0),
                (0x92, 1),
                (0x93, 0),
            ),
        )
        for generation, pair in enumerate(spec.POSITION_SEQUENCE, 1):
            self.assertEqual(
                spec.generation_for_position(*pair), generation
            )

    def test_same_stage_subpositions_advance_and_skips_fail_closed(self):
        record = advance_to(88)
        dispatch = spec.SUCCESSOR_POSITIONS[0]
        returned = spec.SUCCESSOR_POSITIONS[1]
        skipped = model.encode_request(
            spec.PROFILE,
            returned.stage,
            run_id=RUN_ID,
            item_index=returned.item_index,
        )
        with self.assertRaisesRegex(
            model.DesignError, "exact next position"
        ):
            model.apply_request(record, skipped)
        first = model.encode_request(
            spec.PROFILE,
            dispatch.stage,
            run_id=RUN_ID,
            item_index=dispatch.item_index,
        )
        record = model.apply_request(record, first)
        with self.assertRaisesRegex(
            model.DesignError, "exact next position"
        ):
            model.apply_request(record, first)
        second = model.encode_request(
            spec.PROFILE,
            returned.stage,
            run_id=RUN_ID,
            item_index=returned.item_index,
        )
        active = model.decode_record(
            model.apply_request(record, second),
            expected_profile=spec.PROFILE,
            expected_run_id=RUN_ID,
        )["active"]
        self.assertEqual(
            (active["generation"], active["stage"], active["item_index"]),
            (90, 0x90, 1),
        )

    def test_order_failure_can_publish_unclassified_at_actual_next_pair(self):
        record = advance_to(88)
        wrong = spec.SUCCESSOR_POSITIONS[1]
        with self.assertRaisesRegex(
            model.DesignError, "exact next position"
        ):
            model.apply_request(
                record,
                model.encode_request(
                    spec.PROFILE,
                    wrong.stage,
                    run_id=RUN_ID,
                    item_index=wrong.item_index,
                ),
            )
        actual = spec.SUCCESSOR_POSITIONS[0]
        fallback = model.encode_request(
            spec.PROFILE,
            actual.stage,
            run_id=RUN_ID,
            outcome=model.OUTCOME_FAILURE,
            item_index=actual.item_index,
            detail=spec.UNCLASSIFIED_DETAIL,
        )
        decoded = decoder.decode_record(
            model.apply_request(record, fallback),
            expected_profile=spec.PROFILE,
            expected_run_id=RUN_ID,
        )
        self.assertEqual(
            (
                decoded["active"]["generation"],
                decoded["active"]["stage"],
                decoded["active"]["item_index"],
                decoded["active"]["outcome"],
                decoded["active"]["detail"],
            ),
            (
                89,
                actual.stage,
                actual.item_index,
                model.OUTCOME_FAILURE,
                spec.UNCLASSIFIED_DETAIL,
            ),
        )

    def test_terminal_generation_and_post_terminal_write_are_closed(self):
        record = advance_to(103)
        decoded = decoder.decode_record(
            record,
            expected_profile=spec.PROFILE,
            expected_run_id=RUN_ID,
        )
        self.assertTrue(decoded["terminal"])
        self.assertTrue(decoded["terminal_success"])
        self.assertEqual(decoded["active"]["generation"], 103)
        request = model.encode_request(
            spec.PROFILE,
            spec.SUCCESSOR_POSITIONS[0].stage,
            run_id=RUN_ID,
            item_index=spec.SUCCESSOR_POSITIONS[0].item_index,
        )
        with self.assertRaisesRegex(
            model.DesignError, "already terminal"
        ):
            model.apply_request(record, request)

    def test_inherited_generation_87_zero_detail_0x8e_is_valid(self):
        record = advance_to(87)
        decoded = decoder.decode_record(
            record,
            expected_profile=spec.PROFILE,
            expected_run_id=RUN_ID,
        )
        self.assertEqual(
            (
                decoded["active"]["generation"],
                decoded["active"]["stage"],
                decoded["active"]["item_index"],
                decoded["active"]["detail"],
            ),
            (87, 0x8E, 0, 0),
        )

    def test_two_adjacent_slots_still_mean_one_candidate_boot(self):
        one_record = advance_to(90)
        one = decoder.classify_observation(
            one_record,
            expected_profile=spec.PROFILE,
            expected_run_id=RUN_ID,
        )
        two = decoder.classify_observation(
            one_record + one_record,
            expected_profile=spec.PROFILE,
            expected_run_id=RUN_ID,
        )
        self.assertEqual(one["long_record_count"], 1)
        self.assertEqual(one["minimum_candidate_boots"], 1)
        self.assertEqual(two["long_record_count"], 2)
        self.assertEqual(two["minimum_candidate_boots"], 2)
        selected = typed_evidence._latest_stage_decoder(
            source_contract.CONTRACT_ID, spec.PROFILE
        )
        self.assertIs(selected, decoder)
        self.assertEqual(
            selected.classify_observation(
                one_record,
                expected_profile=spec.PROFILE,
                expected_run_id=RUN_ID,
            )["minimum_candidate_boots"],
            1,
        )
        typed = typed_evidence.classify_e1_latest_stage(
            one_record, p288_acceptance()
        )
        self.assertEqual(typed["minimum_candidate_boots"], 1)
        self.assertEqual(typed["long_record_count"], 1)
        self.assertEqual(
            typed["records"][0]["active_semantics"]["position_name"],
            "restart_helper_returned",
        )

    def test_process_v2_binds_pair_model_and_nonidentity_support(self):
        receipts = process_v2.execution_critical_source_receipts(
            p288_acceptance()
        )
        model_data = (
            ROOT
            / "workspace/public/src/scripts/revalidation/"
            "s22plus_fyg8_p288_latest_stage_model.py"
        ).read_bytes()
        self.assertEqual(
            receipts["e1_latest_stage_design_model"]["sha256"],
            hashlib.sha256(model_data).hexdigest(),
        )
        self.assertEqual(
            len(
                tuple(
                    name
                    for name in receipts
                    if name.startswith("candidate_source_")
                )
            ),
            83,
        )
        support_names = {
            name
            for name in receipts
            if name.startswith("p288_support_")
        }
        self.assertEqual(
            support_names,
            {
                f"p288_support_{name}"
                for name in change_freeze.NON_IDENTITY_SUPPORT_PATHS
            },
        )
        self.assertFalse(
            any(name.startswith("p286_support_") for name in receipts)
        )
        self.assertTrue(
            set(change_freeze.NON_IDENTITY_SUPPORT_PATHS).isdisjoint(
                source_contract.SOURCE_KEYS
            )
        )

    def test_qualification_adapter_supplies_only_inherited_module_paths(self):
        self.assertFalse(
            hasattr(source_contract, "DEFAULT_DWC3_MSM_MODULE")
        )
        self.assertFalse(hasattr(source_contract, "DEFAULT_HSPHY_MODULE"))
        adapter = qualification.QUALIFICATION_SOURCE_CONTRACT
        self.assertEqual(
            adapter.DEFAULT_DWC3_MSM_MODULE,
            p286_contract.DEFAULT_DWC3_MSM_MODULE,
        )
        self.assertEqual(
            adapter.DEFAULT_HSPHY_MODULE,
            p286_contract.DEFAULT_HSPHY_MODULE,
        )
        self.assertEqual(adapter.CONTRACT_ID, source_contract.CONTRACT_ID)

    def test_stock_closure_applies_p286_authority_context_exactly_once(self):
        result = stock_closure.build_result(ROOT)
        self.assertEqual(result["schema"], stock_closure.SCHEMA)
        self.assertEqual(result["verdict"], stock_closure.VERDICT)
        self.assertEqual(
            result["contract_id"], source_contract.CONTRACT_ID
        )
        self.assertTrue(result["verified"])

    def test_pre_intent_freeze_is_git_derived_and_exact(self):
        result = change_freeze.validate_freeze(ROOT)
        self.assertTrue(result["pre_intent_ready"])
        self.assertEqual(result["inherited_receipts"]["changed_keys"], [])
        self.assertEqual(result["source_key_counts"]["planned_total"], 83)
        self.assertEqual(result["source_key_counts"]["planned_direct"], 74)
        self.assertEqual(result["source_key_counts"]["generated_total"], 9)
        derived = change_freeze.git_derived_changed_paths(
            ROOT, change_freeze.CHANGE_WINDOW_BASE_COMMIT
        )
        exact = change_freeze.validate_declared_change_set(
            derived_paths=derived,
            declared_paths=change_freeze.DECLARED_CHANGED_PATHS,
        )
        self.assertEqual(
            exact["git_derived_paths"], exact["declared_paths"]
        )
        with self.assertRaisesRegex(
            change_freeze.FreezeError,
            "missing_declarations",
        ):
            change_freeze.validate_declared_change_set(
                derived_paths=(*derived, "undeclared-file"),
                declared_paths=change_freeze.DECLARED_CHANGED_PATHS,
            )

    def test_p288_candidate_path_retires_p286_without_mutating_it(self):
        historical_superseded = dict(
            candidate_intent.base.SUPERSEDED_FOR_NEW_CANDIDATES
        )
        historical_ids = candidate_intent.base.candidate_contract_ids()
        accepted = candidate_intent.parse_args(
            [
                "--profile",
                spec.PROFILE,
                "--source-contract-id",
                source_contract.CONTRACT_ID,
            ]
        )
        self.assertEqual(
            accepted.source_contract_id, source_contract.CONTRACT_ID
        )
        self.assertNotIn(
            p286_contract.CONTRACT_ID,
            candidate_intent.candidate_contract_ids(),
        )
        with self.assertRaisesRegex(
            candidate_intent.IntentError, "superseded"
        ):
            candidate_intent.selected_source_contract_for_candidate(
                p286_contract.CONTRACT_ID,
                spec.PROFILE,
            )
        self.assertEqual(
            candidate_intent.base.SUPERSEDED_FOR_NEW_CANDIDATES,
            historical_superseded,
        )
        self.assertEqual(
            candidate_intent.base.candidate_contract_ids(),
            historical_ids,
        )

    def test_full_lto_a_path_gate_runs_before_b(self):
        private_root = ROOT / "workspace/private"
        private_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(
            prefix="p288-a-gate-", dir=private_root
        ) as directory:
            build_a = Path(directory)
            relative = build_a.relative_to(ROOT)
            stable = b"/private-repo/clang/lib/clang/17/include"
            (build_a / "vmlinux").write_bytes(
                b"\x7fELF\x00" + stable + b"\x00"
            )
            (build_a / "Image").write_bytes(b"IMAGE")
            result = repro_check.audit_a_path_leaks(relative)
            self.assertTrue(result["b_build_permitted"])
            self.assertEqual(
                result["absolute_host_clang_resource_path_count"], 0
            )
            self.assertGreater(
                result["mapped_clang_resource_path_count"], 0
            )

            (build_a / "vmlinux").write_bytes(
                b"\x7fELF\x00"
                + repro_check.RANDOM_PRIVATE_PATH_PREFIX
                + b"deadbeef\x00"
                + stable
                + b"\x00"
            )
            with self.assertRaisesRegex(
                repro_check.CheckError, "random private namespace"
            ):
                repro_check.audit_a_path_leaks(relative)

            (build_a / "vmlinux").write_bytes(
                b"\x7fELF\x00"
                + stable
                + b"\x00/opt/clang/lib/clang/17/include\x00"
            )
            with self.assertRaisesRegex(
                repro_check.CheckError,
                "absolute clang resource path",
            ):
                repro_check.audit_a_path_leaks(relative)

    def test_runtime_call_order_and_all_four_mutations_are_rejected(self):
        include = self.source["p288_e3_runtime_include"]
        order = source_contract._audit_runtime_position_order(include)
        mutations = source_contract._audit_runtime_position_mutations(
            include
        )
        self.assertEqual(order["declared_nonterminal_suffix"], 14)
        self.assertTrue(order["exact_program_order"])
        self.assertEqual(
            mutations,
            {
                "remove_rejected": True,
                "reorder_rejected": True,
                "duplicate_rejected": True,
                "rename_rejected": True,
                "verified": True,
            },
        )

    def test_helper_return_marker_precedes_every_restart_readback(self):
        include = self.source["p288_e3_runtime_include"]
        restart = include.index(
            b"static unsigned int p282_cycle_restart("
        )
        end = include.index(
            b"static unsigned int p282_phase_bind(", restart
        )
        corridor = include[restart:end]
        returned = corridor.index(
            b"S22_P288_POSITION_RESTART_HELPER_RETURNED"
        )
        child = corridor.index(b"P282_CHILD_RUNTIME_STATUS_PATH")
        parent = corridor.index(b"P282_PARENT_MODE_PATH")
        udc = corridor.index(b"p282_wait_exact_udc(", parent)
        self.assertLess(returned, child)
        self.assertLess(returned, parent)
        self.assertLess(returned, udc)

    def test_retired_details_are_unreachable_and_unclassified_is_total(self):
        rules = set(spec.exact_detail_rules())
        self.assertFalse(
            any(
                detail in spec.RETIRED_DETAIL_VALUES
                for _ordinal, _outcome, detail in rules
            )
        )
        for ordinal in range(len(spec.POSITIONS)):
            self.assertIn(
                (
                    ordinal,
                    model.OUTCOME_FAILURE,
                    spec.UNCLASSIFIED_DETAIL,
                ),
                rules,
            )

    def test_active_producer_routes_match_declared_exact_tuples(self):
        result = source_contract._audit_active_producer_routes(self.source)
        self.assertEqual(
            result["active_route_count"],
            result["declared_route_count"],
        )
        self.assertEqual(result["missing_active_routes"], [])
        self.assertEqual(result["undeclared_active_routes"], [])
        self.assertTrue(result["bidirectional_exact_tuple_coverage"])

    def test_every_park_is_routed_or_preinit_unreachable(self):
        result = source_contract._audit_park_routes(self.source)
        self.assertTrue(result["raw_sinks_publication_dominated"])
        self.assertTrue(result["unclassified_before_generic_park"])
        self.assertTrue(
            result["preinit_non_pid1_guard_unreachable_for_init"]
        )
        wrapper = self.source["runtime_wrapper"]
        with self.assertRaisesRegex(
            source_contract.SourceContractError,
            "raw park sink escaped",
        ):
            source_contract._audit_park_routes(
                {
                    **self.source,
                    "runtime_wrapper": wrapper.replace(
                        b"(void)s22_p288_checkpoint_unclassified_next("
                        b"&g_checkpoint);",
                        b"(void)0;",
                        1,
                    ),
                }
            )

    def test_publication_bound_is_sequence_length_not_u8_budget(self):
        result = source_contract._audit_publication_bound()
        self.assertEqual(result["position_count"], 103)
        self.assertEqual(result["terminal_generation"], 103)
        self.assertTrue(result["generation_limit_is_sequence_length"])
        self.assertTrue(result["generation_u8_wrap_unreachable"])

    def test_linked_adapter_requires_exact_call_edges(self):
        calls = {
            "s22_fyg8_e1_write": [
                "s22_fyg8_e1_request_allowed"
            ]
        }
        linked_audit._require_call(
            calls,
            "s22_fyg8_e1_write",
            "s22_fyg8_e1_request_allowed",
        )
        calls["s22_fyg8_e1_write"].append(
            "s22_fyg8_e1_request_allowed"
        )
        with self.assertRaisesRegex(
            linked_audit.AuditError, "not exact"
        ):
            linked_audit._require_call(
                calls,
                "s22_fyg8_e1_write",
                "s22_fyg8_e1_request_allowed",
            )

    def test_terminal_publish_survives_infinite_trace_finish(self):
        runtime = self.source["p288_e3_runtime_include"].decode("ascii")
        start = runtime.index(
            "static __attribute__((noreturn)) void p282_cycle_abort("
        )
        end = runtime.index(
            "static __attribute__((noreturn)) void "
            "p282_cycle_abort_condition(",
            start,
        )
        production = runtime[start:end]
        harness = r'''
#include <stdint.h>
#include <unistd.h>

struct p282_trace_control { unsigned int marker; };
struct p282_cycle_context {
    struct p282_trace_control trace;
    unsigned int armed;
};
static int g_checkpoint;
static __attribute__((noreturn)) void quiet_park(void) { _exit(0); }
static long s22_p288_checkpoint_failure_next(void *client, long detail)
{
    if (client != &g_checkpoint || detail != 0xc5dL)
        _exit(90);
    if (write(STDOUT_FILENO, "P", 1) != 1)
        _exit(91);
    return 0;
}
static __attribute__((noreturn)) long p282_trace_finish(
    struct p282_trace_control *trace, long *quality)
{
    (void)trace;
    (void)quality;
    if (write(STDOUT_FILENO, "C", 1) != 1)
        _exit(92);
    for (;;)
        __asm__ volatile("" ::: "memory");
}
'''
        harness += production
        harness += r'''
int main(void)
{
    struct p282_cycle_context cycle = {0};
    cycle.armed = 1U;
    p282_cycle_abort(&cycle, 0x90U, 0xc5dL);
}
'''
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory)
            source = work / "abort-fault.c"
            binary = work / "abort-fault"
            source.write_text(harness, encoding="ascii")
            compiled = subprocess.run(
                (
                    "aarch64-linux-gnu-gcc",
                    "-static",
                    "-Os",
                    "-Wall",
                    "-Wextra",
                    "-Werror",
                    str(source),
                    "-o",
                    str(binary),
                ),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
            )
            self.assertEqual(
                compiled.returncode,
                0,
                compiled.stdout.decode("utf-8", "replace"),
            )
            identity = subprocess.run(
                ("file", str(binary)),
                check=True,
                text=True,
                stdout=subprocess.PIPE,
            ).stdout
            self.assertIn("ARM aarch64", identity)
            process = subprocess.Popen(
                ("qemu-aarch64", str(binary)),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
            try:
                with self.assertRaises(
                    subprocess.TimeoutExpired
                ) as blocked:
                    process.communicate(timeout=3)
                self.assertEqual(blocked.exception.output, b"PC")
                self.assertIsNone(process.poll())
            finally:
                process.kill()
                process.communicate()


if __name__ == "__main__":
    unittest.main()

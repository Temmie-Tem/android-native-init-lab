from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "workspace/public/src/scripts/revalidation"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import s22plus_fyg8_p288_contract_spec as p288_spec  # noqa: E402
import device_action_f1_evidence_v2 as typed_evidence  # noqa: E402
import device_action_f1_v2 as process_v2  # noqa: E402
import s22plus_fyg8_p290_candidate_static_checker as static_checker  # noqa: E402
import s22plus_fyg8_p290_change_freeze as change_freeze  # noqa: E402
import s22plus_fyg8_p290_contract_spec as spec  # noqa: E402
import s22plus_fyg8_p290_e1_decoder as decoder  # noqa: E402
import s22plus_fyg8_p290_latest_stage_model as model  # noqa: E402
import s22plus_fyg8_p290_postbuild_linked_audit as postbuild  # noqa: E402
import s22plus_fyg8_p290_source_contract as source_contract  # noqa: E402


RUN_ID = bytes.fromhex("00112233445566778899aabbccddeeff")


def advance_to(generation: int) -> bytes:
    record = model.initialize_record(spec.PROFILE, RUN_ID)
    for current, position in enumerate(spec.POSITIONS[:generation], 1):
        request = model.encode_request(
            spec.PROFILE,
            position.stage,
            run_id=RUN_ID,
            outcome=(
                model.OUTCOME_SUCCESS
                if current == spec.TERMINAL_GENERATION
                else model.OUTCOME_PROGRESS
            ),
            item_index=position.item_index,
            detail=0,
        )
        record = model.apply_request(record, request)
    return record


class P290ParkRepairContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = source_contract.source_bytes(ROOT)
        cls.generated = source_contract.generate(ROOT)

    def test_exact_position_sequence_and_live_prefix(self):
        self.assertEqual(len(spec.POSITIONS), 107)
        self.assertEqual(spec.TERMINAL_GENERATION, 107)
        self.assertEqual(spec.TERMINAL_ORDINAL, 106)
        self.assertEqual(
            len(set(spec.POSITION_SEQUENCE)),
            len(spec.POSITION_SEQUENCE),
        )
        self.assertEqual(
            spec.POSITION_SEQUENCE[:88],
            p288_spec.POSITION_SEQUENCE[:88],
        )
        self.assertEqual(
            tuple(position.pair for position in spec.CORRIDOR_POSITIONS),
            ((0x8F, 1), (0x8F, 2), (0x8F, 3), (0x8F, 4)),
        )
        self.assertEqual(spec.POSITION_SEQUENCE[92], (0x90, 0))

    def test_model_advances_all_positions_and_rejects_skip(self):
        record = advance_to(88)
        second = spec.CORRIDOR_POSITIONS[1]
        with self.assertRaisesRegex(model.DesignError, "exact next position"):
            model.apply_request(
                record,
                model.encode_request(
                    spec.PROFILE,
                    second.stage,
                    run_id=RUN_ID,
                    item_index=second.item_index,
                ),
            )
        terminal = decoder.decode_record(
            advance_to(107),
            expected_profile=spec.PROFILE,
            expected_run_id=RUN_ID,
        )
        self.assertTrue(terminal["terminal_success"])
        self.assertEqual(terminal["active"]["generation"], 107)
        self.assertEqual(
            terminal["active_semantics"]["position_name"], "terminal"
        )

    def test_runtime_constructs_helper_dispatch_as_0x90_item_zero(self):
        result = source_contract._audit_runtime_request_encoding(self.source)
        self.assertEqual(result["position_ordinal"], 92)
        self.assertEqual(result["generation"], 93)
        self.assertEqual(result["declared_pair"], [0x90, 0])
        self.assertEqual(result["linked_step_pair"], [0x90, 0])
        self.assertTrue(result["publisher_checks_supplied_ordinal"])

    def test_generated_userspace_uses_only_p290_position_names(self):
        self.assertNotIn(
            b"s22plus_fyg8_p288_positions.h",
            self.source["p290_e3_runtime_include"],
        )
        self.assertNotIn(
            b"S22_P288_POSITION_",
            self.source["checkpoint_client"],
        )
        result = source_contract.implementation_result(ROOT)
        self.assertTrue(result["linked_userspace"]["static_aarch64"])
        self.assertTrue(
            result["linked_userspace"]["two_link_reproducible"]
        )

    def test_all_historical_park_sites_are_accounted(self):
        result = source_contract._audit_park_routes(ROOT, self.source)
        self.assertEqual(result["inherited_site_count"], 16)
        self.assertEqual(result["inherited_routes_checked"], 16)
        self.assertEqual(result["inherited_source_removed_routes"], 2)
        self.assertEqual(result["active_include_checked_fallback_routes"], 14)
        self.assertEqual(result["active_include_confirmed_routes"], 3)
        self.assertEqual(result["raw_sink_count"], 2)
        self.assertEqual(result["persistent_channel_failure_sink_count"], 1)
        self.assertFalse(
            result["single_channel_total_failure_self_reporting_possible"]
        )
        self.assertTrue(result["fallback_return_checked"])

    def test_first_marker_is_immediately_after_generation_88_return(self):
        result = source_contract._audit_first_position_adjacency(
            self.source["p290_e3_runtime_include"]
        )
        self.assertEqual(result["last_live_generation"], 88)
        self.assertEqual(result["first_successor_generation"], 89)
        self.assertEqual(result["first_successor_pair"], [0x8F, 1])
        self.assertFalse(result["unrelated_syscall_between_publishers"])
        self.assertFalse(result["gate_revalidation_between_publishers"])

    def test_runtime_order_is_mechanically_equal_to_declaration(self):
        result = source_contract._audit_runtime_position_order(
            self.source["p290_e3_runtime_include"]
        )
        self.assertEqual(result["declared_nonterminal_suffix"], 18)
        self.assertEqual(result["runtime_nonterminal_suffix"], 18)
        self.assertTrue(result["exact_program_order"])

    def test_runtime_mutations_fail_closed(self):
        include = self.source["p290_e3_runtime_include"]
        missing = include.replace(
            b"    p290_progress_position(\n"
            b"        S22_P290_POSITION_SUSPEND_FUNCTION_RETURNED, 0U);\n",
            b"",
            1,
        )
        with self.assertRaisesRegex(
            source_contract.SourceContractError,
            "caller marker",
        ):
            source_contract._audit_runtime_position_order(missing)

        displaced = include.replace(
            b"    p290_progress_position(\n"
            b"        S22_P290_POSITION_SUSPENDED_PUBLISH_RETURNED, 0U);\n",
            b"    (void)sys_getpid();\n"
            b"    p290_progress_position(\n"
            b"        S22_P290_POSITION_SUSPENDED_PUBLISH_RETURNED, 0U);\n",
            1,
        )
        with self.assertRaisesRegex(
            source_contract.SourceContractError, "adjacency differs"
        ):
            source_contract._audit_first_position_adjacency(displaced)

    def test_unchecked_park_mutations_fail_closed(self):
        source = dict(self.source)
        source["runtime_wrapper"] = source["runtime_wrapper"].replace(
            b"if (fallback_rc == 0)",
            b"if (fallback_rc != 0)",
            1,
        )
        with self.assertRaisesRegex(
            source_contract.SourceContractError,
            "park topology differs",
        ):
            source_contract._audit_park_routes(ROOT, source)

        source = dict(self.source)
        source["p290_e3_runtime_include"] += b"\np288_raw_quiet_park();\n"
        with self.assertRaisesRegex(
            source_contract.SourceContractError,
            "park topology differs",
        ):
            source_contract._audit_park_routes(ROOT, source)

    def test_publication_fault_matrix_uses_checked_fallback(self):
        binary = self._compile_park_harness()
        cases = (
            (("quiet", "0", "0", "88"), b"UR"),
            (("quiet", "-5", "-6", "88"), b"UR"),
            (("fail", "0", "0", "88"), b"NR"),
            (("fail", "-5", "0", "88"), b"NUR"),
            (("fail", "-5", "-6", "88"), b"NUR"),
            (("fail", "0", "0", "87"), b"LR"),
        )
        for arguments, expected in cases:
            with self.subTest(arguments=arguments):
                completed = subprocess.run(
                    (str(binary), *arguments),
                    check=False,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=5,
                )
                self.assertEqual(completed.returncode, 0)
                self.assertEqual(completed.stdout, expected)
                self.assertEqual(completed.stderr, b"")

    def test_publication_nonreturn_is_the_explicit_residual_sink_class(self):
        binary = self._compile_park_harness()
        process = subprocess.Popen(
            (str(binary), "fail", "99", "0", "88"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        try:
            with self.assertRaises(subprocess.TimeoutExpired) as blocked:
                process.communicate(timeout=0.2)
            self.assertEqual(blocked.exception.output, b"N")
        finally:
            process.kill()
            process.communicate()

    def test_host_native_validator_is_exhaustive(self):
        result = postbuild.run_host_validator_tu(
            postbuild.host_validator_tu(self.generated["patch"])
        )
        self.assertEqual(result["checked_pairs"], 7_077_888)
        self.assertEqual(result["accepted_pairs"], 107)
        self.assertTrue(result["register_allocation_independent"])

    def test_host_validator_rejects_pair_guard_mutation(self):
        tu = postbuild.host_validator_tu(self.generated["patch"])
        changed = tu.replace(
            b"request->item_index != expected_item",
            b"request->item_index == expected_item",
        )
        self.assertNotEqual(changed, tu)
        with self.assertRaisesRegex(
            postbuild.AuditError, "exhaustive evaluation failed"
        ):
            postbuild.run_host_validator_tu(changed)

    def test_direct_elf_tables_match_exact_position_bytes(self):
        expected = source_contract.linked_table_bytes()
        result = postbuild.verify_linked_table_data(
            self._tiny_tables_elf(expected), expected
        )
        self.assertEqual(result["position_count"], 107)
        self.assertTrue(result["objdump_text_not_used"])
        self.assertTrue(result["stage_and_item_bytes_equal_position_sequence"])

    def test_identity_contains_only_byte_affecting_p290_adapters(self):
        self.assertEqual(len(source_contract.SOURCE_KEYS), 94)
        expected = {
            "p290_contract_spec",
            "p290_source_contract",
            "p290_runtime_transform",
            "p290_candidate_intent",
            "p290_userspace_build",
            "p290_build",
            "p290_candidate_builder",
            "p290_boot_only_packager",
            "p290_e3_runtime_include",
            "p290_position_header",
            "p290_checkpoint_header",
        }
        self.assertEqual(
            {
                key
                for key in source_contract.SOURCE_KEYS
                if key.startswith("p290")
            },
            expected,
        )
        self.assertNotIn("p290_postbuild_linked_audit", source_contract.SOURCE_KEYS)
        self.assertNotIn("p290_candidate_contract", source_contract.SOURCE_KEYS)

    def test_freeze_is_git_derived_and_inherited_receipts_are_exact(self):
        result = change_freeze.validate_freeze(ROOT)
        self.assertTrue(result["pre_intent_ready"])
        self.assertEqual(result["inherited_receipts"]["changed_keys"], [])
        self.assertEqual(result["source_key_counts"]["planned_total"], 94)
        derived = change_freeze.git_derived_changed_paths(ROOT)
        exact = change_freeze.validate_declared_change_set(
            derived_paths=derived,
            declared_paths=change_freeze.DECLARED_CHANGED_PATHS,
        )
        self.assertEqual(
            exact["git_derived_paths"], exact["declared_paths"]
        )

    def test_typed_evidence_and_process_v2_bind_p290_support(self):
        selected = typed_evidence._latest_stage_decoder(
            source_contract.CONTRACT_ID, spec.PROFILE
        )
        self.assertIs(selected, decoder)
        closure = typed_evidence._select_e2_closure(
            source_contract.CONTRACT_ID
        )
        self.assertEqual(
            closure.source_contract.CONTRACT_ID,
            source_contract.CONTRACT_ID,
        )
        receipts = process_v2.execution_critical_source_receipts(
            {
                "kind": typed_evidence.E1_LATEST_STAGE_KIND,
                "profile": spec.PROFILE,
                "source_contract_id": source_contract.CONTRACT_ID,
            }
        )
        self.assertEqual(
            len(
                tuple(
                    name
                    for name in receipts
                    if name.startswith("candidate_source_")
                )
            ),
            94,
        )
        self.assertEqual(
            {
                name
                for name in receipts
                if name.startswith("p290_support_")
            },
            {
                f"p290_support_{name}"
                for name in change_freeze.NON_IDENTITY_SUPPORT_PATHS
            },
        )

    def test_static_checker_dispatches_fresh_p290_postbuild_replay(self):
        static_checker._configure()
        self.assertIs(
            static_checker.base.verify_repro,
            static_checker.verify_repro,
        )
        self.assertEqual(
            postbuild.ADAPTER_ID,
            "s22plus-fyg8-p290-linked-audit-v1",
        )

    def test_p288_and_p290_contexts_do_not_contaminate_each_other(self):
        before = tuple(p288_spec.POSITION_SEQUENCE)
        self.assertEqual(
            spec.position_failure_details(0x90, 0),
            spec.position_failure_details(0x90, 0),
        )
        self.assertEqual(p288_spec.POSITION_SEQUENCE, before)
        self.assertEqual(len(p288_spec.POSITIONS), 103)
        self.assertEqual(len(spec.POSITIONS), 107)

    @classmethod
    def _compile_park_harness(cls) -> Path:
        if hasattr(cls, "_park_binary"):
            return cls._park_binary
        wrapper = cls.source["runtime_wrapper"]
        start = wrapper.index(
            b"static __attribute__((noreturn))\n"
            b"void p290_park_after_confirmed_publication"
        )
        end = wrapper.index(
            b'\n\n#include "s22plus_fyg8_p286_e3_plan.h"', start
        )
        production = wrapper[start:end].decode("ascii")
        harness = r'''
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

struct checkpoint_client {
    int initialized;
    uint8_t generation;
};
static struct checkpoint_client g_checkpoint;
static long g_primary;
static long g_fallback;

static void emit(char value)
{
    if (write(STDOUT_FILENO, &value, 1) != 1)
        _exit(90);
}

static __attribute__((noreturn)) void p288_raw_quiet_park(void)
{
    emit('R');
    _exit(0);
}

static long s22_p290_checkpoint_unclassified_next(void *client)
{
    if (client != &g_checkpoint)
        _exit(91);
    emit('U');
    return g_fallback;
}

static long s22_p290_checkpoint_failure_next(void *client, long detail)
{
    if (client != &g_checkpoint || detail != 0x123L)
        _exit(92);
    emit('N');
    if (g_primary == 99)
        for (;;)
            __asm__ volatile("" ::: "memory");
    return g_primary;
}

static long s22_r4w1e_checkpoint_failure(
    void *client, uint8_t stage, uint8_t item, long detail)
{
    if (client != &g_checkpoint || stage != 0x90U ||
        item != 0U || detail != 0x123L)
        _exit(93);
    emit('L');
    return g_primary;
}
'''
        harness += production
        harness += r'''
int main(int argc, char **argv)
{
    if (argc != 5)
        return 94;
    g_primary = strtol(argv[2], 0, 10);
    g_fallback = strtol(argv[3], 0, 10);
    g_checkpoint.initialized = 1;
    g_checkpoint.generation = (uint8_t)strtoul(argv[4], 0, 10);
    if (strcmp(argv[1], "quiet") == 0)
        quiet_park();
    if (strcmp(argv[1], "fail") == 0)
        fail_at(0x90U, 0U, 0x123L);
    return 95;
}
'''
        cls._park_directory = tempfile.TemporaryDirectory(
            prefix="s22-p290-park-"
        )
        work = Path(cls._park_directory.name)
        source = work / "park.c"
        binary = work / "park"
        source.write_text(harness, encoding="ascii")
        compiled = subprocess.run(
            (
                "cc",
                "-std=c11",
                "-O0",
                "-Wall",
                "-Wextra",
                "-Werror",
                str(source),
                "-o",
                str(binary),
            ),
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        if compiled.returncode != 0:
            raise AssertionError(
                compiled.stdout.decode("utf-8", errors="replace")
            )
        cls._park_binary = binary
        return binary

    @staticmethod
    def _tiny_tables_elf(tables: dict[str, bytes]) -> bytes:
        declarations = []
        for symbol_name in postbuild.LINKED_DATA_SYMBOLS:
            body = ", ".join(str(value) for value in tables[symbol_name])
            declarations.append(
                "__attribute__((used)) "
                f"const uint8_t {symbol_name}[] = {{{body}}};"
            )
        source = "\n".join(
            (
                "#include <stdint.h>",
                *declarations,
                "int main(void) { return 0; }",
            )
        )
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory)
            source_path = work / "tables.c"
            binary = work / "tables"
            source_path.write_text(source, encoding="ascii")
            subprocess.run(
                (
                    "cc",
                    "-std=c11",
                    "-O2",
                    str(source_path),
                    "-o",
                    str(binary),
                ),
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
            return binary.read_bytes()


if __name__ == "__main__":
    unittest.main()

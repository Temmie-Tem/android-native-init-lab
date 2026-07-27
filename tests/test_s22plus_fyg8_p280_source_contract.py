from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "workspace/public/src/scripts/revalidation"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import s22plus_fyg8_p260_source_contract as p260  # noqa: E402
import s22plus_fyg8_p280_contract_spec as spec  # noqa: E402
import s22plus_fyg8_p280_e1_decoder as decoder  # noqa: E402
import s22plus_fyg8_p280_source_contract as p280  # noqa: E402


class S22PlusFyg8P280SourceContractTest(unittest.TestCase):
    RUN_ID = bytes.fromhex("80" * 16)

    @classmethod
    def setUpClass(cls) -> None:
        cls.generated = p280.generate(ROOT)
        cls.historical = p260.generate(ROOT)
        cls.source = p280.source_bytes(ROOT)
        cls.implementation = p280.implementation_result(ROOT)

    def _header(self) -> bytes:
        model = decoder.model
        return (
            model.LONG_FAMILY
            + bytes(
                [
                    (model.FORMAT_VERSION << 4)
                    | model.PROFILE_NUMBERS[spec.PROFILE]
                ]
            )
            + self.RUN_ID
        )

    def _record(self, older: bytes, newer: bytes) -> bytes:
        slots = [bytes(decoder.model.SLOT_SIZE), bytes(decoder.model.SLOT_SIZE)]
        older_generation = int.from_bytes(older[0:4], "little")
        newer_generation = int.from_bytes(newer[0:4], "little")
        slots[older_generation & 1] = older
        slots[newer_generation & 1] = newer
        return self._header() + b"".join(slots)

    def _slot(
        self,
        stage: int,
        outcome: int,
        detail: int,
    ) -> bytes:
        generation = spec.ordinal_for_stage(stage) + 1
        return decoder.encode_slot(
            self._header(),
            generation=generation,
            stage=stage,
            outcome=outcome,
            item_index=spec.expected_item(stage),
            detail=detail,
        )

    def test_p260_geometry_and_plan_are_unchanged(self) -> None:
        self.assertEqual(spec.STEPS, spec.p260.STEPS)
        self.assertEqual(spec.TERMINAL_STAGE, 0x90)
        self.assertEqual(spec.TERMINAL_ORDINAL, 88)
        self.assertEqual(self.generated["plan"], self.historical["plan"])
        self.assertEqual(
            self.generated["runtime"].count(
                b'#include "s22plus_fyg8_p280_e3_runtime.inc.c"'
            ),
            1,
        )
        self.assertEqual(self.generated["runtime"].count(b"p280_e3_run();"), 1)
        self.assertNotIn(b"    p260_e3_run();\n", self.generated["runtime"])

    def test_exact_diagnostic_table_is_generated_for_both_validators(
        self,
    ) -> None:
        checkpoint = self.generated["checkpoint"]
        patch = self.generated["patch"]
        for detail in spec.DIAGNOSTIC_DETAILS:
            token = f"0x{detail.value:03x}".encode("ascii")
            self.assertEqual(checkpoint.count(token), 1)
            self.assertEqual(patch.count(token), 1)
        self.assertIn(b"if (detail >= 0xb00U)", checkpoint)
        self.assertIn(b"if (detail >= 0xb00)", patch)

    def test_runtime_authority_source_rejects_each_operation_mutation(
        self,
    ) -> None:
        runtime = self.source["e3_runtime_include"]
        p280._validate_runtime_authority_source(runtime)
        for name, token, count in spec.RUNTIME_OPERATION_TOKENS:
            self.assertEqual(runtime.count(token.encode("ascii")), count)
            mutated = runtime.replace(
                token.encode("ascii"),
                f"P280_MUTATED_{name}".encode("ascii"),
                1,
            )
            with self.assertRaisesRegex(
                p280.SourceContractError,
                f"operation {name}",
            ):
                p280._validate_runtime_authority_source(mutated)

    def test_runtime_authority_rejects_constant_path_and_global_broadening(
        self,
    ) -> None:
        runtime = self.source["e3_runtime_include"]
        for name, _value in spec.RUNTIME_EXTERNAL_CONSTANTS:
            marker = f"#define {name} ".encode("ascii")
            self.assertEqual(runtime.count(marker), 1)
            start = runtime.index(marker)
            end = runtime.index(b"\n", start)
            mutated = (
                runtime[:start]
                + marker
                + b"999999U"
                + runtime[end:]
            )
            with self.assertRaisesRegex(
                p280.SourceContractError,
                f"constant {name}",
            ):
                p280._validate_runtime_authority_source(mutated)

        path = b'"/sys/kernel/tracing/instances/p280/trace"'
        mutated = runtime.replace(
            path,
            b'"/sys/kernel/tracing/trace"',
            1,
        )
        with self.assertRaisesRegex(
            p280.SourceContractError,
            "absolute path set",
        ):
            p280._validate_runtime_authority_source(mutated)

        for forbidden in (
            b'\nstatic const char bad[] = "/sys/kernel/tracing/current_tracer";\n',
            b'\nstatic const char bad[] = "function_graph";\n',
        ):
            with self.assertRaisesRegex(
                p280.SourceContractError,
                "broadened",
            ):
                p280._validate_runtime_authority_source(runtime + forbidden)

    def test_role_helper_is_one_shot_bounded_and_malformed_fail_closed(
        self,
    ) -> None:
        runtime = self.source["e3_runtime_include"]
        self.assertEqual(
            runtime.count(
                b"record.result = p280_role_write_once(&byte_count);"
            ),
            1,
        )
        self.assertEqual(runtime.count(b"sys_clone();"), 1)
        self.assertEqual(runtime.count(b"sys_kill(pid, SIGKILL);"), 1)
        self.assertEqual(
            runtime.count(b"deadline.tv_sec += P280_ROLE_DEADLINE_SEC;"),
            1,
        )
        self.assertIn(b"record_malformed\n", runtime)
        self.assertIn(b"|| child_status != 0", runtime)
        self.assertIn(b"extra_amount != 0", runtime)
        self.assertEqual(
            runtime.count(b"p280_role_write_once(&byte_count)"),
            1,
        )

    def test_same_warning_in_both_slots_is_not_ambiguous(self) -> None:
        older = self._slot(
            spec.ROLE_UDC_STAGE,
            spec.OUTCOME_PROGRESS,
            0xB01,
        )
        newer = self._slot(
            spec.UDC_BIND_STAGE,
            spec.OUTCOME_PROGRESS,
            0xB01,
        )
        result = decoder.decode_record(
            self._record(older, newer),
            expected_profile=spec.PROFILE,
            expected_run_id=self.RUN_ID,
        )
        self.assertEqual(result["progress_warning"]["detail"], 0xB01)
        self.assertEqual(
            result["progress_warning"]["stage"],
            spec.ROLE_UDC_STAGE,
        )

    def test_distinct_retained_warnings_are_ambiguous(self) -> None:
        older = self._slot(
            spec.ROLE_UDC_STAGE,
            spec.OUTCOME_PROGRESS,
            0xB01,
        )
        newer = self._slot(
            spec.UDC_BIND_STAGE,
            spec.OUTCOME_PROGRESS,
            0xB02,
        )
        with self.assertRaisesRegex(decoder.DecodeError, "distinct"):
            decoder.decode_record(
                self._record(older, newer),
                expected_profile=spec.PROFILE,
                expected_run_id=self.RUN_ID,
            )

    def test_warning_survives_zero_detail_terminal_success(self) -> None:
        older = self._slot(
            spec.CONFIGURED_STAGE,
            spec.OUTCOME_PROGRESS,
            0xB03,
        )
        newer = self._slot(
            spec.TERMINAL_STAGE,
            spec.OUTCOME_SUCCESS,
            0,
        )
        result = decoder.decode_record(
            self._record(older, newer),
            expected_profile=spec.PROFILE,
            expected_run_id=self.RUN_ID,
        )
        self.assertTrue(result["terminal_success"])
        self.assertEqual(result["progress_warning"]["detail"], 0xB03)

    def test_reachable_records_and_static_aarch64_two_link_pass(self) -> None:
        reachable = p280.validate_reachable_records(self.RUN_ID)
        self.assertTrue(reachable["verified"])
        self.assertEqual(
            reachable["exact_diagnostic_detail_count"],
            len(spec.DIAGNOSTIC_DETAILS),
        )
        self.assertTrue(
            self.implementation["linked_userspace"]["static_aarch64"]
        )
        self.assertTrue(
            self.implementation["linked_userspace"][
                "two_link_reproducible"
            ]
        )
        self.assertTrue(self.implementation["patch"]["clean_apply"])


if __name__ == "__main__":
    unittest.main()

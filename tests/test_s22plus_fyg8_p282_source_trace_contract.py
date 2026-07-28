from __future__ import annotations

import hashlib
import shutil
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "workspace/public/src/scripts/revalidation"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import s22plus_fyg8_p282_contract_spec as spec  # noqa: E402
import s22plus_fyg8_p282_e1_decoder as decoder  # noqa: E402
import s22plus_fyg8_p282_source_contract as source  # noqa: E402
import s22plus_fyg8_p282_trace_contract as trace  # noqa: E402


def trace_line(
    pid: int,
    counter: int,
    event: str,
    fields: str = "",
) -> str:
    suffix = f" {fields}" if fields else ""
    return (
        f" <...>-{pid} [000] d..2 {counter}: "
        f"{event}: (ffffffff){suffix}\n"
    )


def valid_cycle_trace(*, pid: int = 17) -> str:
    rows = (
        ("worker_in", "on=0"),
        ("child_suspend_in", ""),
        ("phy_suspend_in", "suspend=1"),
        ("phy_power_in", "on=0"),
        ("phy_power_out", "rc=0"),
        ("phy_suspend_out", "rc=0"),
        ("child_suspend_out", "rc=0"),
        ("worker_out", "rc=0"),
        ("worker_in", "on=1"),
        ("child_resume_in", ""),
        ("phy_init_in", ""),
        ("phy_power_in", "on=1"),
        ("phy_power_out", "rc=0"),
        ("phy_init_out", "rc=0"),
        ("child_resume_out", "rc=0"),
        ("notify_connect_in", ""),
        ("notify_connect_out", "rc=0"),
        ("worker_out", "rc=0"),
    )
    return "".join(
        trace_line(pid, counter, event, fields)
        for counter, (event, fields) in enumerate(rows, 1)
    )


class P282SourceContractSidecarTest(unittest.TestCase):
    def test_generate_is_deterministic_and_byte_materialized(self) -> None:
        first = source.generate(ROOT)
        second = source.generate(ROOT)
        self.assertEqual(first, second)
        self.assertEqual(
            set(first),
            {"plan", "runtime", "checkpoint", "patch"},
        )
        self.assertTrue(all(type(value) is bytes for value in first.values()))
        self.assertTrue(all(value for value in first.values()))

        with tempfile.TemporaryDirectory(prefix="p282-generate-a-") as a_raw:
            with tempfile.TemporaryDirectory(
                prefix="p282-generate-b-"
            ) as b_raw:
                directories = (Path(a_raw), Path(b_raw))
                output_filenames = {
                    output_key: source.MATERIALIZED_FILENAMES.get(
                        source_key,
                        f"{source_key}.bin",
                    )
                    for source_key, output_key
                    in source.GENERATED_OUTPUT_NAMES.items()
                }
                snapshots = []
                for directory, generated in zip(
                    directories, (first, second), strict=True
                ):
                    for key, payload in generated.items():
                        filename = output_filenames[key]
                        (directory / filename).write_bytes(payload)
                    snapshots.append(
                        {
                            path.name: path.read_bytes()
                            for path in sorted(directory.iterdir())
                        }
                    )
                self.assertEqual(snapshots[0], snapshots[1])

    def test_source_inventory_materialization_is_deterministic(self) -> None:
        first = source.source_bytes(ROOT)
        second = source.source_bytes(ROOT)
        self.assertEqual(first, second)
        self.assertEqual(set(first), source.SOURCE_KEYS)
        self.assertEqual(
            source.source_receipts(ROOT)[1],
            {
                name: source.receipt(payload)
                for name, payload in sorted(first.items())
            },
        )

        names = tuple(source.MATERIALIZED_FILENAMES.values())
        self.assertEqual(len(names), len(set(names)))
        with tempfile.TemporaryDirectory(prefix="p282-materialize-a-") as a_raw:
            with tempfile.TemporaryDirectory(
                prefix="p282-materialize-b-"
            ) as b_raw:
                snapshots = []
                for directory in (Path(a_raw), Path(b_raw)):
                    for key, filename in source.MATERIALIZED_FILENAMES.items():
                        (directory / filename).write_bytes(first[key])
                    snapshots.append(
                        {
                            path.name: hashlib.sha256(
                                path.read_bytes()
                            ).hexdigest()
                            for path in sorted(directory.iterdir())
                        }
                    )
                self.assertEqual(snapshots[0], snapshots[1])

    def test_cycle_helper_and_restart_stage_miswiring_fails_closed(
        self,
    ) -> None:
        runtime = (
            ROOT
            / "workspace/public/src/native-init/"
            "s22plus_fyg8_p282_e3_runtime.inc.c"
        ).read_bytes()
        mutations = (
            (
                b"P282_HELPER_OPERATION_NONE_WRITE,\n"
                b"        unrelated_fd,",
                b"P282_STAGE_STOP,\n        unrelated_fd,",
            ),
            (
                b"P282_HELPER_OPERATION_PERIPHERAL_WRITE,\n"
                b"        unrelated_fd,",
                b"P282_STAGE_RESTART,\n        unrelated_fd,",
            ),
            (
                b"&classification,\n        P282_STAGE_RESTART,\n"
                b"        P282_OUTCOME_FAILURE,",
                b"&classification,\n"
                b"        P282_HELPER_OPERATION_PERIPHERAL_WRITE,\n"
                b"        P282_OUTCOME_FAILURE,",
            ),
        )
        for original, replacement in mutations:
            with self.subTest(original=original):
                self.assertEqual(runtime.count(original), 1)
                mutated = runtime.replace(original, replacement, 1)
                with self.assertRaisesRegex(
                    source.SourceContractError,
                    "cardinality drifted",
                ):
                    source._validate_runtime_authority_source(mutated)


class P282TraceDerivationSidecarTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.dwc3 = ROOT / source.DEFAULT_DWC3_MSM_MODULE
        cls.hsphy = ROOT / source.DEFAULT_HSPHY_MODULE

    def test_exact_modules_and_all_phase_definitions_derive(self) -> None:
        if not self.dwc3.is_file() or not self.hsphy.is_file():
            self.skipTest("private exact FYG8 modules are absent")
        if not shutil.which("aarch64-linux-gnu-nm") or not shutil.which(
            "aarch64-linux-gnu-objdump"
        ):
            self.skipTest("pinned GNU AArch64 inspection tools are absent")

        derived = trace.derive_module_contract(
            dwc3_msm_module=self.dwc3,
            hsphy_module=self.hsphy,
        )
        modules = {
            module["module"]: module for module in derived["modules"]
        }
        self.assertEqual(
            modules[spec.DWC3_MSM_MODULE_RUNTIME_NAME]["sha256"],
            spec.EXACT_DWC3_MSM_SHA256,
        )
        self.assertEqual(
            modules[spec.HSPHY_MODULE_RUNTIME_NAME]["sha256"],
            spec.EXACT_HSPHY_SHA256,
        )
        self.assertEqual(
            set(derived["event_definitions"]),
            {spec.PHASE_ROLE, spec.PHASE_CYCLE, spec.PHASE_BIND},
        )
        self.assertEqual(
            {
                phase: len(definitions)
                for phase, definitions in derived[
                    "event_definitions"
                ].items()
            },
            {
                spec.PHASE_ROLE: 4,
                spec.PHASE_CYCLE: 14,
                spec.PHASE_BIND: 6,
            },
        )
        for phase in (spec.PHASE_ROLE, spec.PHASE_CYCLE, spec.PHASE_BIND):
            self.assertEqual(
                tuple(derived["event_definitions"][phase]),
                tuple(
                    event.definition(
                        tuple(
                            modules[
                                spec.DWC3_MSM_MODULE_RUNTIME_NAME
                            ]["parent_pm_post_call_offsets"]
                        )
                    )
                    for event in spec.events_for_phase(phase)
                ),
            )

    def test_module_hash_mutation_fails_closed(self) -> None:
        if not self.dwc3.is_file() or not self.hsphy.is_file():
            self.skipTest("private exact FYG8 modules are absent")
        with tempfile.TemporaryDirectory(prefix="p282-module-mutation-") as raw:
            mutated = Path(raw) / "dwc3-msm.ko"
            payload = bytearray(self.dwc3.read_bytes())
            payload[-1] ^= 0x01
            mutated.write_bytes(payload)
            with self.assertRaisesRegex(
                trace.TraceContractError,
                "hash mismatch",
            ):
                trace.derive_module_contract(
                    dwc3_msm_module=mutated,
                    hsphy_module=self.hsphy,
                )

    def test_rendered_header_has_exact_event_counts_and_stage_masks(
        self,
    ) -> None:
        derived = {
            "schema": "s22plus_fyg8_p282_module_trace_contract_v1",
            "modules": [
                {
                    "module": spec.DWC3_MSM_MODULE_RUNTIME_NAME,
                    "sha256": spec.EXACT_DWC3_MSM_SHA256,
                    "parent_pm_post_call_offsets": [0x34, 0x450],
                },
                {
                    "module": spec.HSPHY_MODULE_RUNTIME_NAME,
                    "sha256": spec.EXACT_HSPHY_SHA256,
                },
            ],
            "event_definitions": {
                phase: [
                    event.definition((0x34, 0x450))
                    for event in spec.events_for_phase(phase)
                ]
                for phase in (
                    spec.PHASE_ROLE,
                    spec.PHASE_CYCLE,
                    spec.PHASE_BIND,
                )
            },
        }
        header = trace.render_c_header(derived).decode("ascii")
        self.assertIn("#define P282_ROLE_EVENT_COUNT 4U", header)
        self.assertIn("#define P282_CYCLE_EVENT_COUNT 14U", header)
        self.assertIn("#define P282_BIND_EVENT_COUNT 6U", header)
        self.assertIn("#define P282_DETAIL_COUNT 46U", header)
        self.assertNotIn("_STAGE_MIN", header)
        self.assertNotIn("_STAGE_MAX", header)
        for detail in spec.DIAGNOSTIC_DETAILS:
            row = (
                f"{{0x{detail.value:03x}U, {detail.outcomes[0]}U, "
                f"0x{spec.stage_mask(detail.stages):02x}U}},"
            )
            self.assertEqual(header.count(row), 1, detail.name)
        self.assertIn("{0xc06U, 2U, 0x0aU},", header)


class P282TraceParserSidecarTest(unittest.TestCase):
    def test_direct_and_resume_nested_bind_are_distinct(self) -> None:
        direct = "".join(
            (
                trace_line(1, 1, "pull_in", "on=1"),
                trace_line(1, 2, "run_in", "on=1"),
                trace_line(1, 3, "run_out", "rc=0"),
                trace_line(1, 4, "pull_out", "rc=0"),
            )
        )
        nested = "".join(
            (
                trace_line(1, 1, "pull_in", "on=1"),
                trace_line(1, 2, "resume_in"),
                trace_line(1, 3, "run_in", "on=1"),
                trace_line(1, 4, "run_out", "rc=0"),
                trace_line(1, 5, "resume_out", "rc=0"),
                trace_line(1, 6, "pull_out", "rc=0"),
            )
        )
        direct_result = trace.parse_bind_trace(direct)
        nested_result = trace.parse_bind_trace(nested)
        self.assertEqual(
            direct_result["classification"], "direct-run-stop-zero"
        )
        self.assertEqual(
            nested_result["classification"], "resume-run-stop-zero"
        )
        self.assertNotEqual(
            direct_result["classification"],
            nested_result["classification"],
        )

    def test_complete_cycle_parses_ordered_stop_and_restart(self) -> None:
        result = trace.parse_cycle_trace(valid_cycle_trace())
        self.assertEqual(result["classification"], "authoritative")
        self.assertTrue(result["clean"])
        self.assertEqual(result["stop"]["parent_rc"], 0)
        self.assertEqual(result["stop"]["child_suspend"]["rc"], 0)
        self.assertEqual(result["stop"]["power_off"]["rc"], 0)
        self.assertEqual(result["restart"]["parent_rc"], 0)
        self.assertEqual(result["restart"]["child_resume"]["rc"], 0)
        self.assertEqual(result["restart"]["phy_init"]["rc"], 0)
        self.assertEqual(result["restart"]["power_on"]["rc"], 0)
        self.assertEqual(result["restart"]["notify"]["rc"], 0)

    def test_malformed_owned_trace_fails_closed(self) -> None:
        with self.assertRaisesRegex(trace.TraceContractError, "truncated"):
            trace.parse_trace(
                trace_line(1, 1, "pull_in", "on=1").rstrip("\n")
            )
        with self.assertRaisesRegex(trace.TraceContractError, "malformed"):
            trace.parse_trace(trace_line(1, 1, "pull_in", "on=1junk"))
        with self.assertRaisesRegex(trace.TraceContractError, "unknown"):
            trace.parse_trace(trace_line(1, 1, "foreign_event"))
        non_monotonic = "".join(
            (
                trace_line(1, 2, "pull_in", "on=1"),
                trace_line(1, 1, "pull_out", "rc=0"),
            )
        )
        with self.assertRaisesRegex(trace.TraceContractError, "increasing"):
            trace.parse_trace(non_monotonic)

    def test_contradictory_bind_trace_fails_closed(self) -> None:
        direct_negative = "".join(
            (
                trace_line(1, 1, "pull_in", "on=1"),
                trace_line(1, 2, "run_in", "on=1"),
                trace_line(1, 3, "run_out", "rc=-110"),
                trace_line(1, 4, "pull_out", "rc=0"),
            )
        )
        with self.assertRaisesRegex(trace.TraceContractError, "contradicts"):
            trace.parse_bind_trace(direct_negative)

        invalid_nesting = "".join(
            (
                trace_line(1, 1, "pull_in", "on=1"),
                trace_line(1, 2, "run_in", "on=1"),
                trace_line(1, 3, "resume_in"),
                trace_line(1, 4, "run_out", "rc=0"),
                trace_line(1, 5, "resume_out", "rc=0"),
                trace_line(1, 6, "pull_out", "rc=0"),
            )
        )
        with self.assertRaisesRegex(trace.TraceContractError, "nested"):
            trace.parse_bind_trace(invalid_nesting)

    def test_source_incompatible_cycle_nesting_fails_closed(self) -> None:
        valid = valid_cycle_trace()
        contradictory = valid.replace(
            trace_line(17, 14, "phy_init_out", "rc=0")
            + trace_line(17, 15, "child_resume_out", "rc=0"),
            trace_line(17, 14, "child_resume_out", "rc=0")
            + trace_line(17, 15, "phy_init_out", "rc=0"),
        )
        with self.assertRaisesRegex(
            trace.TraceContractError,
            "nest|source|order|outside",
        ):
            trace.parse_cycle_trace(contradictory)


class P282PublicRoundTripSidecarTest(unittest.TestCase):
    def test_all_46_details_round_trip_through_public_interfaces(self) -> None:
        spec.validate()
        self.assertEqual(len(spec.DIAGNOSTIC_DETAILS), 46)
        self.assertEqual(len(spec.DETAIL_VALUES), 46)
        self.assertEqual(len(set(spec.DETAIL_VALUES)), 46)
        self.assertEqual(
            {fixture.detail for fixture in spec.CLASSIFIER_FIXTURES},
            set(spec.DETAIL_VALUES),
        )
        classifier_header = spec.render_classifier_contract_c()
        linked = source.linked_table_bytes()[
            "s22_fyg8_p282_details"
        ]
        self.assertEqual(len(linked), 46 * 4)

        for index, detail in enumerate(spec.DIAGNOSTIC_DETAILS):
            decoded = decoder.decode_detail(detail.value)
            self.assertEqual(decoded["detail"], detail.value)
            self.assertEqual(decoded["detail_name"], detail.name)
            self.assertEqual(decoded["detail_kind"], detail.category)
            self.assertIsNone(decoded["final_tuple"])
            self.assertTrue(
                spec.detail_allowed(
                    detail.stages[0],
                    detail.outcomes[0],
                    detail.value,
                )
            )
            self.assertIn(
                f"#define {detail.macro} 0x{detail.value:03x}U",
                classifier_header,
            )
            row = linked[index * 4 : (index + 1) * 4]
            self.assertEqual(
                int.from_bytes(row[:2], "little"),
                detail.value,
            )
            self.assertEqual(row[2], detail.outcomes[0])
            self.assertEqual(row[3], spec.stage_mask(detail.stages))

    def test_all_567_tuples_round_trip_through_public_interfaces(self) -> None:
        values = spec.tuple_values()
        self.assertEqual(len(values), 567)
        self.assertEqual((values[0], values[-1]), (0xD00, 0xF36))
        self.assertEqual(len(set(values)), 567)
        progress = 0
        for value in values:
            decoded = spec.decode_tuple(value)
            self.assertEqual(
                spec.encode_tuple(
                    decoded.repair,
                    decoded.bind,
                    decoded.state_index,
                    decoded.speed_index,
                ),
                value,
            )
            public = decoder.decode_detail(value)
            self.assertEqual(public["detail"], value)
            self.assertEqual(
                public["final_tuple"]["repair_index"],
                int(decoded.repair),
            )
            self.assertEqual(
                public["final_tuple"]["bind_index"],
                int(decoded.bind),
            )
            self.assertEqual(
                public["final_tuple"]["state"],
                decoded.state,
            )
            self.assertEqual(
                public["final_tuple"]["speed"],
                decoded.speed,
            )
            self.assertEqual(
                public["final_tuple"]["outcome"],
                decoded.outcome,
            )
            self.assertTrue(
                spec.detail_allowed(
                    spec.FINAL_STAGE,
                    decoded.outcome,
                    value,
                )
            )
            progress += decoded.outcome == spec.OUTCOME_PROGRESS
        self.assertEqual(progress, 9)


if __name__ == "__main__":
    unittest.main()

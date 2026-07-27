from __future__ import annotations

import importlib
import sys
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SCRIPT_DIR = REPO / "workspace/public/src/scripts/revalidation"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

spec = importlib.import_module("s22plus_fyg8_p280_contract_spec")
trace = importlib.import_module("s22plus_fyg8_p280_trace_contract")

MODULE = (
    REPO
    / "workspace/private/inputs/s22plus_firmware/"
    "S906NKSS7FYG8_SKC/extracted-images/ramdisk-list/vendor/extract/"
    "lib/modules/dwc3-msm.ko"
)
VMLINUX = (
    REPO
    / "workspace/private/outputs/s22plus_fyg8_p260_v6/"
    "bundle-a/vmlinux"
)


def line(pid: int, counter: int, event: str, fields: str = "") -> str:
    suffix = f" {fields}" if fields else ""
    return (
        f" <...>-{pid} [000] d..2 {counter}: "
        f"p280_{event}: (ffffffff){suffix}"
    )


class P280ContractSpecTest(unittest.TestCase):
    def test_detail_domain_is_exact(self) -> None:
        self.assertEqual(len(spec.DETAIL_VALUES), 21)
        self.assertEqual(spec.DETAIL_VALUES[0], 0xB01)
        self.assertEqual(spec.DETAIL_VALUES[-1], 0xB27)
        for value in range(0xB00, 0xC00):
            allowed = any(
                spec.detail_allowed(stage, outcome, value)
                for stage in (
                    spec.ROLE_UDC_STAGE,
                    spec.UDC_BIND_STAGE,
                    spec.CONFIGURED_STAGE,
                )
                for outcome in (
                    spec.OUTCOME_PROGRESS,
                    spec.OUTCOME_FAILURE,
                )
            )
            self.assertEqual(allowed, value in spec.DETAIL_BY_VALUE)

    def test_progress_warning_and_failure_stage_scopes(self) -> None:
        spec.validate_slot(
            generation=spec.p260.ordinal_for_stage(spec.ROLE_UDC_STAGE) + 1,
            stage=spec.ROLE_UDC_STAGE,
            outcome=spec.OUTCOME_PROGRESS,
            item_index=0,
            detail=0xB01,
        )
        with self.assertRaises(spec.SpecError):
            spec.validate_slot(
                generation=spec.p260.ordinal_for_stage(spec.ROLE_UDC_STAGE) + 1,
                stage=spec.ROLE_UDC_STAGE,
                outcome=spec.OUTCOME_FAILURE,
                item_index=0,
                detail=0xB01,
            )
        with self.assertRaises(spec.SpecError):
            spec.validate_slot(
                generation=spec.p260.ordinal_for_stage(spec.UDC_BIND_STAGE) + 1,
                stage=spec.UDC_BIND_STAGE,
                outcome=spec.OUTCOME_FAILURE,
                item_index=0,
                detail=0xB20,
            )

    def test_event_definitions_derive_offsets(self) -> None:
        definitions = tuple(
            event.definition((0x34, 0x450))
            for event in spec.events_for_phase(spec.PHASE_ROLE)
        )
        self.assertIn(
            "dwc3_msm:dwc3_otg_start_peripheral+0x34 rc=%x0:s32",
            definitions[1],
        )
        self.assertIn(
            "dwc3_msm:dwc3_otg_start_peripheral+0x450 rc=%x0:s32",
            definitions[2],
        )

    def test_runtime_authority_mutation_fails(self) -> None:
        original = spec.RUNTIME_AUTHORITY
        try:
            for selected in tuple(original):
                spec.RUNTIME_AUTHORITY = {
                    key: value
                    for key, value in original.items()
                    if key != selected
                }
                with self.assertRaisesRegex(spec.SpecError, "authority"):
                    spec.validate()
                spec.RUNTIME_AUTHORITY = dict(original)
                spec.RUNTIME_AUTHORITY[selected] = "mutated"
                with self.assertRaisesRegex(spec.SpecError, "authority"):
                    spec.validate()
            spec.RUNTIME_AUTHORITY = dict(original)
            spec.RUNTIME_AUTHORITY["global_tracer"] = True
            with self.assertRaisesRegex(spec.SpecError, "authority"):
                spec.validate()
        finally:
            spec.RUNTIME_AUTHORITY = original


class P280TraceContractTest(unittest.TestCase):
    def test_exact_private_artifacts_derive_expected_contract(self) -> None:
        if not MODULE.is_file() or not VMLINUX.is_file():
            self.skipTest("private exact P2.80 extraction inputs are absent")
        result = trace.derive_contract(module=MODULE, vmlinux=VMLINUX)
        self.assertEqual(
            result["parent_pm_post_call_offsets"], [0x34, 0x450]
        )
        self.assertEqual(
            len(result["event_definitions"][spec.PHASE_ROLE]), 4
        )
        self.assertEqual(
            len(result["event_definitions"][spec.PHASE_BIND]), 6
        )

    def test_offset_extractor_rejects_missing_second_call(self) -> None:
        if not MODULE.is_file():
            self.skipTest("private exact module is absent")
        nm = trace._run(["aarch64-linux-gnu-nm", "-an", str(MODULE)])
        disassembly = trace._run(
            [
                "aarch64-linux-gnu-objdump",
                "-dr",
                f"--disassemble={spec.PARENT_SYMBOL}",
                str(MODULE),
            ]
        )
        mutated = disassembly.replace(
            "R_AARCH64_CALL26\t__pm_runtime_resume",
            "R_AARCH64_CALL26\tfixture",
            1,
        )
        with self.assertRaisesRegex(trace.TraceContractError, "exactly two"):
            trace.derive_parent_post_call_offsets(
                nm_text=nm, disassembly=mutated
            )

    def test_role_trace_complete_and_negative_pm(self) -> None:
        complete = "\n".join(
            (
                line(7, 10, "start_in", "on=1"),
                line(7, 11, "parent_pm_out", "rc=0"),
                line(7, 12, "child_pm_out", "rc=0"),
                line(7, 13, "start_out", "rc=0"),
            )
        )
        self.assertEqual(
            trace.parse_role_trace(complete)["classification"], "complete"
        )
        negative = complete.replace("parent_pm_out: (ffffffff) rc=0", "parent_pm_out: (ffffffff) rc=-19")
        self.assertEqual(
            trace.parse_role_trace(negative)["classification"],
            "parent-pm-negative",
        )

    def test_role_trace_ignores_older_stop_side_worker(self) -> None:
        value = "\n".join(
            (
                line(4, 1, "start_in", "on=0"),
                line(4, 2, "start_out", "rc=0"),
                line(9, 3, "start_in", "on=1"),
                line(9, 4, "parent_pm_out", "rc=0"),
                line(9, 5, "child_pm_out", "rc=0"),
                line(9, 6, "start_out", "rc=0"),
            )
        )
        result = trace.parse_role_trace(value)
        self.assertEqual(result["classification"], "complete")
        self.assertEqual(result["pid"], 9)

    def test_bind_trace_source_valid_variants(self) -> None:
        no_run = "\n".join(
            (
                line(1, 1, "pull_in", "on=1"),
                line(1, 2, "pull_out", "rc=0"),
            )
        )
        self.assertEqual(
            trace.parse_bind_trace(no_run)["classification"],
            "pullup-without-run-stop",
        )
        nested_failure = "\n".join(
            (
                line(1, 1, "pull_in", "on=1"),
                line(1, 2, "resume_in"),
                line(1, 3, "run_in", "on=1"),
                line(1, 4, "run_out", "rc=-110"),
                line(1, 5, "resume_out", "rc=0"),
                line(1, 6, "pull_out", "rc=0"),
            )
        )
        self.assertEqual(
            trace.parse_bind_trace(nested_failure)["classification"],
            "nested-run-stop-failure",
        )

    def test_bind_trace_rejects_non_pid1_and_missing_return(self) -> None:
        value = "\n".join(
            (
                line(2, 1, "pull_in", "on=1"),
                line(2, 2, "pull_out", "rc=0"),
            )
        )
        with self.assertRaisesRegex(trace.TraceContractError, "non-PID1"):
            trace.parse_bind_trace(value)
        missing = line(1, 1, "pull_in", "on=1")
        with self.assertRaisesRegex(trace.TraceContractError, "pull-up pair"):
            trace.parse_bind_trace(missing)

    def test_timeout_detail_priority(self) -> None:
        self.assertEqual(
            trace.detail_for_timeout(state="powered", bind_trace=None), 0xB23
        )
        self.assertEqual(
            trace.detail_for_timeout(state="not attached", bind_trace=None),
            0xB27,
        )
        self.assertEqual(
            trace.detail_for_timeout(
                state="not attached",
                bind_trace={
                    "clean": True,
                    "classification": "nested-run-stop-failure",
                },
            ),
            0xB21,
        )
        with self.assertRaisesRegex(trace.TraceContractError, "unknown"):
            trace.detail_for_timeout(state="configured-ish", bind_trace=None)

    def test_generated_c_header_uses_descriptor_only(self) -> None:
        if not MODULE.is_file() or not VMLINUX.is_file():
            self.skipTest("private exact P2.80 extraction inputs are absent")
        derived = trace.derive_contract(module=MODULE, vmlinux=VMLINUX)
        header = trace.render_c_header(derived)
        self.assertIn(
            b"dwc3_msm:dwc3_otg_start_peripheral+0x34 rc=%x0:s32",
            header,
        )
        self.assertIn(b"#define P280_DETAIL_COUNT 21U", header)
        self.assertIn(
            b"#define P280_DETAIL_RUN_STOP_ZERO_NO_BUS_STATE 0xb22U",
            header,
        )

    def test_generated_c_header_rejects_offset_shape_mutation(self) -> None:
        with self.assertRaisesRegex(trace.TraceContractError, "two post-call"):
            trace.render_c_header({"parent_pm_post_call_offsets": [0x34]})


if __name__ == "__main__":
    unittest.main()

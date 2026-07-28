from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "workspace/public/src/scripts/revalidation"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import s22plus_fyg8_p282_contract_spec as spec  # noqa: E402


class S22PlusFyg8P282ContractSpecTest(unittest.TestCase):
    def test_stage_geometry_and_public_interface(self) -> None:
        self.assertEqual(spec.STEPS[:86], spec.P280_PREFIX_STEPS)
        self.assertEqual(
            spec.STAGE_SEQUENCE[-7:],
            (0x8D, 0x8E, 0x8F, 0x90, 0x91, 0x92, 0x93),
        )
        self.assertEqual(spec.TERMINAL_STAGE, 0x93)
        self.assertEqual(spec.TERMINAL_ORDINAL, 91)
        self.assertEqual(
            spec.ordinal_for_stage(spec.TERMINAL_STAGE) + 1,
            92,
        )
        for name in (
            "PHASE_CYCLE",
            "PHASE_BIND",
            "TRACE_EVENTS",
            "DIAGNOSTIC_DETAILS",
            "DETAIL_BY_VALUE",
            "DETAIL_VALUES",
            "RUNTIME_AUTHORITY_ITEMS",
            "RUNTIME_AUTHORITY",
            "RUNTIME_EXTERNAL_CONSTANTS",
            "RUNTIME_STRING_CONSTANTS",
            "TRACEFS_ABSOLUTE_PATHS",
            "RUNTIME_OPERATION_TOKENS",
            "EXACT_DWC3_MSM_SHA256",
            "EXACT_HSPHY_SHA256",
            "DWC3_MSM_MODULE_RUNTIME_NAME",
            "HSPHY_MODULE_RUNTIME_NAME",
            "PARENT_SYMBOL",
            "UDC_STATES",
            "USB_SPEEDS",
            "STATE_CONFIGURED",
            "SPEED_HIGH",
            "TUPLE_FIRST",
            "TUPLE_LAST",
            "DEFAULT_STAGE_EXACT_MASKS",
        ):
            self.assertTrue(hasattr(spec, name), name)
        self.assertEqual(spec.TUPLE_FIRST, spec.TUPLE_BASE)
        self.assertEqual(spec.TUPLE_LAST, spec.TUPLE_MAX)
        self.assertEqual(
            spec.UDC_STATES[spec.STATE_CONFIGURED],
            "configured",
        )
        self.assertEqual(spec.USB_SPEEDS[spec.SPEED_HIGH], "high-speed")
        self.assertEqual(
            spec.CHILD_RUNTIME_STATUS_PATH,
            "/sys/devices/platform/soc/a600000.ssusb/"
            "a600000.dwc3/power/runtime_status",
        )
        self.assertNotIn(
            ("P282_ROLE_HOST_WRITE", "host\n"),
            spec.RUNTIME_STRING_CONSTANTS,
        )
        self.assertEqual(
            len(spec.RUNTIME_AUTHORITY),
            len(spec.RUNTIME_AUTHORITY_ITEMS),
        )
        self.assertTrue(
            all(
                "p280" not in value
                for value in spec.RUNTIME_AUTHORITY.values()
                if isinstance(value, str)
            )
        )

    def test_exact_46_detail_domain_and_masks(self) -> None:
        expected = (
            *range(0xC01, 0xC07),
            *range(0xC10, 0xC1B),
            *range(0xC20, 0xC31),
            *range(0xC40, 0xC4C),
        )
        self.assertEqual(spec.DETAIL_VALUES, expected)
        self.assertEqual(len(spec.DETAIL_BY_VALUE), 46)
        self.assertEqual(len(spec.CLASSIFIER_FIXTURES), 46)
        self.assertEqual(
            {fixture.detail for fixture in spec.CLASSIFIER_FIXTURES},
            set(expected),
        )
        c06 = spec.DETAIL_BY_VALUE[0xC06]
        self.assertEqual(c06.stages, (spec.STOP_STAGE, spec.RESTART_STAGE))
        self.assertEqual(
            c06.stage_mask,
            spec.stage_mask((spec.STOP_STAGE, spec.RESTART_STAGE)),
        )
        self.assertFalse(
            spec.detail_allowed(
                spec.SUSPENDED_STAGE,
                spec.OUTCOME_FAILURE,
                0xC06,
            )
        )
        for detail in spec.DIAGNOSTIC_DETAILS:
            for stage in (
                spec.STOP_STAGE,
                spec.SUSPENDED_STAGE,
                spec.RESTART_STAGE,
                spec.BIND_STAGE,
                spec.FINAL_STAGE,
            ):
                self.assertEqual(
                    spec.detail_allowed(
                        stage,
                        detail.outcomes[0],
                        detail.value,
                    ),
                    stage in detail.stages,
                )

    def test_trace_descriptor_is_4_plus_14_plus_6_and_typed(self) -> None:
        role = spec.events_for_phase(spec.PHASE_ROLE)
        cycle = spec.events_for_phase(spec.PHASE_CYCLE)
        bind = spec.events_for_phase(spec.PHASE_BIND)
        self.assertEqual(len(role), 4)
        self.assertEqual(len(cycle), 14)
        self.assertEqual(len(bind), 6)
        self.assertEqual(
            tuple(event.name for event in role),
            ("start_in", "parent_pm_out", "child_pm_out", "start_out"),
        )
        self.assertEqual(
            tuple(event.post_call_ordinal for event in role),
            (None, 0, 1, None),
        )
        self.assertIn("+0x44", role[1].definition((0x44, 0x88)))
        self.assertIn("+0x88", role[2].definition((0x44, 0x88)))
        with self.assertRaisesRegex(spec.SpecError, "offsets"):
            role[1].definition()
        self.assertEqual(
            tuple(event.name for event in cycle),
            (
                "worker_in",
                "worker_out",
                "child_suspend_in",
                "child_suspend_out",
                "child_resume_in",
                "child_resume_out",
                "phy_suspend_in",
                "phy_suspend_out",
                "phy_power_in",
                "phy_power_out",
                "phy_init_in",
                "phy_init_out",
                "notify_connect_in",
                "notify_connect_out",
            ),
        )
        for event in spec.TRACE_EVENTS:
            self.assertIsInstance(event.fetch, str)
            self.assertEqual(event.filter_expression, "common_pid > 0")
            offsets = (
                (0x44, 0x88)
                if event.post_call_ordinal is not None
                else None
            )
            self.assertTrue(event.definition(offsets).endswith("\n"))
        with self.assertRaisesRegex(spec.SpecError, "unknown"):
            spec.events_for_phase("foreign")

    def test_all_567_tuples_round_trip_and_outcomes(self) -> None:
        values = spec.tuple_values()
        self.assertEqual(len(values), 567)
        self.assertEqual((values[0], values[-1]), (0xD00, 0xF36))
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
            self.assertTrue(
                spec.detail_allowed(
                    spec.FINAL_STAGE,
                    decoded.outcome,
                    value,
                )
            )
            progress += decoded.outcome == spec.OUTCOME_PROGRESS
        self.assertEqual(progress, 9)
        self.assertEqual(
            spec.encode_tuple(0, 0, "configured", "high-speed"),
            0xD26,
        )
        self.assertEqual(
            spec.encode_tuple(1, 0, "configured", "high-speed"),
            0xDE3,
        )
        self.assertEqual(
            spec.encode_tuple(2, 2, "configured", "high-speed"),
            0xF1E,
        )
        with self.assertRaises(spec.SpecError):
            spec.encode_tuple(3, 0, 0, 0)
        with self.assertRaises(spec.SpecError):
            spec.decode_tuple(0xCFF)

    def test_generated_c_contract_uses_exact_masks(self) -> None:
        generated = spec.render_classifier_contract_c()
        self.assertIn("#define P282_STAGE_TERMINAL 0x93U", generated)
        self.assertIn("#define P282_TUPLE_MAX 0xf36U", generated)
        self.assertIn(
            "#define "
            "P282_DETAIL_CYCLE_HELPER_SOURCE_CONTRADICTION_STAGE_MASK "
            "0x0aU",
            generated,
        )
        self.assertNotIn(
            "P282_DETAIL_CYCLE_HELPER_SOURCE_CONTRADICTION_STAGE_MIN",
            generated,
        )

    def test_stable_pair_detail_is_failure_at_final_only(self) -> None:
        detail = spec.DETAIL_BY_VALUE[0xC4B]
        self.assertEqual(detail.name, "final-state-speed-unstable")
        self.assertEqual(detail.stages, (spec.FINAL_STAGE,))
        self.assertEqual(detail.outcomes, (spec.OUTCOME_FAILURE,))
        spec.validate_slot(
            generation=spec.ordinal_for_stage(spec.FINAL_STAGE) + 1,
            stage=spec.FINAL_STAGE,
            outcome=spec.OUTCOME_FAILURE,
            item_index=0,
            detail=0xC4B,
        )
        with self.assertRaises(spec.SpecError):
            spec.validate_slot(
                generation=spec.ordinal_for_stage(spec.BIND_STAGE) + 1,
                stage=spec.BIND_STAGE,
                outcome=spec.OUTCOME_FAILURE,
                item_index=0,
                detail=0xC4B,
            )

    def test_p280_initial_role_details_remain_inherited(self) -> None:
        self.assertEqual(
            spec.INHERITED_DIAGNOSTIC_DETAILS,
            spec.p280.DIAGNOSTIC_DETAILS,
        )
        self.assertEqual(
            len(spec.all_details()),
            len(spec.p280.DIAGNOSTIC_DETAILS) + 46,
        )
        for detail in spec.INHERITED_DIAGNOSTIC_DETAILS:
            if spec.ROLE_UDC_STAGE not in detail.stages:
                continue
            for outcome in detail.outcomes:
                self.assertEqual(
                    spec.detail_allowed(
                        spec.ROLE_UDC_STAGE,
                        outcome,
                        detail.value,
                    ),
                    spec.p280.detail_allowed(
                        spec.ROLE_UDC_STAGE,
                        outcome,
                        detail.value,
                    ),
                )
            self.assertEqual(
                spec.detail_name(detail.value),
                spec.p280.detail_name(detail.value),
            )
            self.assertEqual(
                spec.detail_kind(detail.value),
                spec.p280.detail_kind(detail.value),
            )


if __name__ == "__main__":
    unittest.main()

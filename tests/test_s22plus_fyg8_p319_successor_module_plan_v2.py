from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / (
    "workspace/public/src/scripts/analysis/"
    "s22plus_fyg8_p319_successor_module_plan_v2.py"
)


def load_module(name: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPT)
    if spec is None or spec.loader is None:
        raise AssertionError("unable to load successor module-plan auditor")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def replace_once(payload: bytes, old: bytes, new: bytes) -> bytes:
    count = payload.count(old)
    if count != 1:
        raise AssertionError(f"mutation source count is {count}, expected one")
    return payload.replace(old, new, 1)


class P319SuccessorModulePlanV2Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module("p319_successor_module_plan_v2")
        cls.source = SCRIPT.read_bytes()
        cls.module._BOUND_AUDITOR_SOURCE = cls.source
        cls.inputs = {
            key: cls.module.stable_bytes(
                spec.source,
                label=key,
                maximum=spec.maximum,
                expected_size=spec.size,
                expected_sha256=spec.sha256,
            )
            for key, spec in cls.module.SPECS.items()
        }
        cls.result = cls.module.build_result(cls.inputs)

    def test_exact_successor_delta_is_three_rows_not_fourteen(self):
        plan = self.result["successor_plan"]
        self.assertEqual(plan["base_plan_count"], 70)
        self.assertEqual(plan["closure_count"], 14)
        self.assertEqual(plan["base_overlap_count"], 11)
        self.assertEqual(plan["incremental_count"], 3)
        self.assertEqual(plan["successor_plan_count"], 73)
        self.assertEqual(
            [row["filename"] for row in plan["incremental_entries"]],
            ["spu_verify.ko", "mfd_max77705.ko", "pdic_max77705.ko"],
        )

    def test_dependency_depth_and_successor_order_are_rederived(self):
        plan = self.result["successor_plan"]
        self.assertEqual(
            plan["dependency_depths"]["5"], ["pdic_max77705.ko"]
        )
        self.assertEqual(
            plan["dependency_depths"]["4"], ["dwc3-msm.ko"]
        )
        self.assertEqual(plan["dependency_order_violations"], [])

    def test_latch_and_stock_dwc3_already_coexist(self):
        plan = self.result["successor_plan"]
        self.assertEqual(plan["custom_latch_index"], 0)
        self.assertEqual(plan["stock_dwc3_msm_index"], 59)
        self.assertFalse(plan["custom_latch_replaces_stock_dwc3_msm"])
        self.assertFalse(plan["new_dwc3_plan_row_required"])
        self.assertFalse(plan["dwc3_symbol_provider_identity_qualified_for_successor"])

    def test_seventy_three_rows_fit_the_existing_folded_stage(self):
        stage = self.result["successor_plan"]["stage_capacity"]
        self.assertEqual(stage["module_stage_capacity"], 60)
        self.assertEqual(stage["direct_module_count"], 59)
        self.assertEqual(stage["folded_tail_count"], 14)
        self.assertEqual(stage["last_module_index"], 72)
        self.assertEqual(stage["last_folded_failure_detail"], 0x748)
        self.assertEqual(stage["last_direct_stage"], 0x7A)
        self.assertEqual(stage["folded_stage"], 0x7B)
        self.assertEqual(stage["gate_stage_base"], 0x7C)
        self.assertEqual(stage["retained_detail_max"], 0x7FF)

    def test_folded_representation_closes_at_exact_256_boundary(self):
        wrapper = self.inputs["p318_wrapper"]
        maximum = self.module.stage_model(256, wrapper)
        self.assertEqual(maximum["last_module_item_index"], 0xFF)
        self.assertEqual(maximum["last_folded_failure_detail"], 0x7FF)
        with self.assertRaisesRegex(
            self.module.AuditError, "outside the folded stage representation"
        ):
            self.module.stage_model(257, wrapper)

    def test_eud_index_is_derived_from_the_exact_tuple(self):
        eud = self.result["successor_plan"]["eud_trigger"]
        self.assertEqual(eud["derived_index"], 38)
        self.assertEqual(eud["inherited_literal_index"], 37)
        self.assertFalse(eud["inherited_literal_matches_effective_plan"])
        self.assertTrue(eud["successor_requires_same-plan-derived_index"])
        self.assertTrue(
            eud["successor_requires_post-load_trigger_in_direct_and_folded_loops"]
        )
        self.assertFalse(eud["independent_runtime_index_literal_allowed"])

    def test_eud_derivation_tracks_an_insertion_before_it(self):
        rows = self.module.parse_plan(self.inputs["p318_plan"])
        original = self.module.derive_eud_index(rows)
        shifted = rows[:original] + [("fixture.ko", "fixture", "")] + rows[original:]
        self.assertEqual(original, 38)
        self.assertEqual(self.module.derive_eud_index(shifted), 39)

    def test_duplicate_or_nonexact_eud_identity_is_rejected(self):
        rows = self.module.parse_plan(self.inputs["p318_plan"])
        with self.assertRaisesRegex(self.module.AuditError, "one exact EUD identity"):
            self.module.derive_eud_index(rows + [self.module.EUD_IDENTITY])
        changed = list(rows)
        changed[38] = ("eud.ko", "eud_other", "")
        with self.assertRaisesRegex(self.module.AuditError, "one exact EUD identity"):
            self.module.derive_eud_index(changed)

    def test_dependency_or_folded_consumer_drift_is_rejected(self):
        dep = replace_once(
            self.inputs["modules_dep"],
            b"/vendor/lib/modules/mfd_max77705.ko: /vendor/lib/modules/usb_notify_layer.ko",
            b"/vendor/lib/modules/mfd_max77705.ko:",
        )
        with self.assertRaisesRegex(self.module.AuditError, "closure or depth"):
            self.module.audit_successor_plan(
                self.inputs["p318_plan"],
                dep,
                self.inputs["p318_wrapper"],
                self.inputs["p318_runtime"],
            )
        wrapper = replace_once(
            self.inputs["p318_wrapper"],
            b"P305_FOLDED_FAILURE_BASE + index",
            b"P305_FOLDED_FAILURE_BASE + P305_FOLDED_MODULE_INDEX",
        )
        with self.assertRaisesRegex(self.module.AuditError, "folded module stage"):
            self.module.audit_successor_plan(
                self.inputs["p318_plan"],
                self.inputs["modules_dep"],
                wrapper,
                self.inputs["p318_runtime"],
            )
        detail_max = replace_once(
            self.inputs["p318_wrapper"],
            b"#define S22_P248_DETAIL_ERRNO_MAX 0x7ffL",
            b"#define S22_P248_DETAIL_ERRNO_MAX 0x7feL",
        )
        with self.assertRaisesRegex(
            self.module.AuditError, "exceeds retained|maxima do not coincide"
        ):
            self.module.audit_successor_plan(
                self.inputs["p318_plan"],
                self.inputs["modules_dep"],
                detail_max,
                self.inputs["p318_runtime"],
            )

    def test_eud_consumer_must_remain_inside_the_direct_post_load_seam(self):
        wrapper = self.inputs["p318_wrapper"]
        block = (
            b"        if (index == P307_EUD_MODULE_INDEX) {\n"
            b"            long p307_eud_cache_rc = p307_read_eud_cache();\n"
            b"            if (p307_eud_cache_rc != 0) p290_fail_next(p307_eud_cache_rc);\n"
            b"        }\n"
        )
        anchor = b"    long p305_checkpoint_rc = s22_r4w1e_checkpoint_progress(\n"
        moved = replace_once(wrapper, block, b"")
        moved = replace_once(moved, anchor, block + anchor)
        with self.assertRaisesRegex(self.module.AuditError, "direct post-load seam"):
            self.module.audit_successor_plan(
                self.inputs["p318_plan"],
                self.inputs["modules_dep"],
                moved,
                self.inputs["p318_runtime"],
            )

    def test_p318_absence_auditor_is_retained_not_weakened(self):
        boundary = self.result["p318_negative_boundary"]
        self.assertTrue(boundary["p318_absence_assertion_retained"])
        self.assertTrue(boundary["successor_plan_uses_separate_derivation"])
        self.assertTrue(boundary["p318_auditor_is_not_weakened"])
        mutated = replace_once(
            self.inputs["p318_transport_auditor"],
            b"P3.18 unexpectedly carries stock MAX77705 modules",
            b"P3.18 accepts stock MAX77705 modules unexpectedly",
        )
        with self.assertRaisesRegex(self.module.AuditError, "negative auditor"):
            self.module.audit_p318_negative_auditor(mutated)

    def test_result_refuses_to_claim_materialization_or_build_readiness(self):
        conclusion = self.result["conclusion"]
        self.assertFalse(conclusion["successor_plan_header_materialized"])
        self.assertFalse(conclusion["successor_runtime_implemented"])
        self.assertFalse(conclusion["module_binary_identities_frozen_for_successor"])
        self.assertFalse(
            conclusion["dwc3_symbol_provider_identity_qualified_for_successor"]
        )
        self.assertFalse(conclusion["candidate_build_qualified"])
        self.assertFalse(conclusion["symbol_stub_authorized"])
        self.assertFalse(self.result["scope"]["device_contact"])
        self.assertFalse(self.result["scope"]["live_authority_created"])

    def test_unbound_import_cannot_build_an_authoritative_result(self):
        unbound = load_module("p319_successor_module_plan_v2_unbound")
        with self.assertRaisesRegex(unbound.AuditError, "unbound auditor"):
            unbound.build_result(self.inputs)

    def test_writer_normalizes_hostile_umask(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "receipt.json"
            old = os.umask(0o777)
            try:
                self.module._write_exclusive(path, b"{}\n")
            finally:
                os.umask(old)
            state = path.stat()
            self.assertEqual(state.st_mode & 0o777, 0o400)
            self.assertEqual(state.st_nlink, 1)
            self.assertEqual(path.read_bytes(), b"{}\n")

    def test_private_receipt_and_inputs_are_exact(self):
        _, expected = self.module.run(materialize=False)
        self.assertEqual(self.module.OUTPUT.read_bytes(), expected)
        output_state = self.module.OUTPUT.stat()
        self.assertEqual(output_state.st_mode & 0o777, 0o400)
        self.assertEqual(output_state.st_nlink, 1)
        for spec in self.module.SPECS.values():
            state = (self.module.INPUT_ROOT / spec.snapshot).stat()
            self.assertEqual(state.st_mode & 0o777, 0o400)
            self.assertEqual(state.st_nlink, 1)


if __name__ == "__main__":
    unittest.main()

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
    "s22plus_fyg8_p319_successor_module_materialization.py"
)
REPORT = ROOT / (
    "docs/reports/"
    "S22PLUS_FYG8_P319_SUCCESSOR_MODULE_MATERIALIZATION_H0_2026-08-20.md"
)
LEDGER = ROOT / "docs/operations/CAMPAIGN_LEDGER_S22PLUS.md"
GOAL = ROOT / "GOAL.md"


def load_module(name: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPT)
    if spec is None or spec.loader is None:
        raise AssertionError("unable to load P3.19 module materializer")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def replace_once(payload: bytes, old: bytes, new: bytes) -> bytes:
    if payload.count(old) != 1:
        raise AssertionError("mutation anchor is not unique")
    return payload.replace(old, new, 1)


class P319SuccessorModuleMaterializationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module("p319_successor_module_materialization")
        cls.source = SCRIPT.read_bytes()
        cls.module._BOUND_AUDITOR_SOURCE = cls.source
        cls.bundle = cls.module.load_bundle(cls.module.DEFAULT_OUTPUT_ROOT)
        cls.result = cls.module.build_result(cls.bundle)
        cls.payload = cls.module.encode(cls.result)

    def test_materializes_exact_seventy_three_row_plan(self):
        value = self.result["materialization"]
        self.assertEqual(value["base_plan_count"], 70)
        self.assertEqual(value["successor_plan_count"], 73)
        self.assertEqual(value["changed_source_count"], 3)
        self.assertEqual(value["unchanged_source_count"], 9)
        self.assertEqual(
            [row["filename"] for row in value["added_entries"]],
            ["spu_verify.ko", "mfd_max77705.ko", "pdic_max77705.ko"],
        )

    def test_only_plan_wrapper_and_runtime_include_change(self):
        self.assertEqual(
            set(self.result["materialization"]["changed_sources"]),
            self.module.CHANGED_SOURCES,
        )
        for name, base in self.bundle["base"].items():
            if name not in self.module.CHANGED_SOURCES:
                self.assertEqual(base, self.bundle["generated"][name])

    def test_eud_index_is_rendered_by_the_plan_not_the_runtime(self):
        value = self.result["materialization"]["eud_identity"]
        self.assertEqual(value["derived_index"], 38)
        self.assertFalse(value["independent_runtime_literal_present"])
        plan = self.bundle["generated"][self.module.PLAN_NAME]
        wrapper = self.bundle["generated"][self.module.WRAPPER_NAME]
        runtime = self.bundle["generated"][self.module.RUNTIME_NAME]
        self.assertEqual(plan.count(b"S22PLUS_O2_EUD_MODULE_INDEX 38U"), 1)
        self.assertNotIn(b"P307_EUD_MODULE_INDEX", wrapper + runtime)

    def test_one_helper_is_consumed_after_both_successful_loads(self):
        value = self.result["materialization"]
        self.assertEqual(value["shared_post_load_helper_count"], 1)
        self.assertEqual(value["direct_loop_consumer_count"], 1)
        self.assertEqual(value["folded_loop_consumer_count"], 1)
        self.assertTrue(value["both_consumers_follow_successful_load"])

    def test_module_bytes_are_exact_across_both_firmware_trees(self):
        modules = self.result["module_bytes"]
        self.assertTrue(modules["candidate_and_stock_copies_byte_identical"])
        expected = {
            "spu_verify.ko": (18_608, "d670a944"),
            "mfd_max77705.ko": (125_840, "26f23873"),
            "pdic_max77705.ko": (423_456, "27e98878"),
            "dwc3-msm.ko": (308_624, "8913b050"),
        }
        for name, (size, prefix) in expected.items():
            row = modules["modules"][name]
            self.assertEqual(row["size"], size)
            self.assertTrue(row["sha256"].startswith(prefix))
            self.assertEqual(self.bundle["modules"][name], self.bundle["stock"][name])
            self.assertTrue(row["dependencies_precede_module"])

    def test_existing_dwc3_row_is_bound_to_the_p318_provider_bytes(self):
        value = self.result["p318_dwc3_provider_binding"]
        self.assertEqual(value["p318_stock_closure_index"], 58)
        self.assertEqual(value["p318_effective_plan_index_after_latch"], 59)
        self.assertTrue(value["same_exact_dwc3_msm_bytes"])
        self.assertEqual(value["sha256"], self.module.MODULE_SPECS["dwc3-msm.ko"].sha256)

    def test_exact_dwc3_export_and_pdic_relocation_are_rechecked(self):
        edge = self.result["pdic_dwc3_symbol_edge"]
        self.assertTrue(edge["provider_export_present"])
        self.assertEqual(edge["consumer_import_count"], 1)
        self.assertEqual(edge["consumer_relocation_count"], 1)
        self.assertEqual(edge["relocation_offset"], "0x12318")
        self.assertEqual(edge["enclosing_function"], "max77705_vdm_dp_select_pin")

    def test_plan_index_or_hook_drift_is_rejected(self):
        generated = dict(self.bundle["generated"])
        generated[self.module.PLAN_NAME] = replace_once(
            generated[self.module.PLAN_NAME],
            b"S22PLUS_O2_EUD_MODULE_INDEX 38U",
            b"S22PLUS_O2_EUD_MODULE_INDEX 39U",
        )
        with self.assertRaisesRegex(self.module.AuditError, "materialization differs"):
            self.module.audit_materialized(self.bundle["base"], generated)

        for marker in (
            (
                b"        long p319_post_load_rc = p319_after_module_load(index);\n"
                b"        if (p319_post_load_rc != 0) p290_fail_next(p319_post_load_rc);\n"
                b"    }\n    for (size_t index = P305_FOLDED_MODULE_INDEX;",
                b"    }\n    for (size_t index = P305_FOLDED_MODULE_INDEX;",
            ),
            (
                b"static long p319_after_module_load(size_t index) {\n",
                b"static long p319_after_module_load_removed(size_t index) {\n",
            ),
        ):
            changed = dict(self.bundle["generated"])
            changed[self.module.WRAPPER_NAME] = replace_once(
                changed[self.module.WRAPPER_NAME], marker[0], marker[1]
            )
            with self.assertRaisesRegex(self.module.AuditError, "materialization differs"):
                self.module.audit_materialized(self.bundle["base"], changed)

    def test_eud_tuple_or_added_row_drift_is_rejected_at_generation(self):
        base = dict(self.bundle["base"])
        base[self.module.PLAN_NAME] = replace_once(
            base[self.module.PLAN_NAME],
            b'{"eud.ko", "eud", ""}',
            b'{"eud.ko", "eud_changed", ""}',
        )
        with self.assertRaisesRegex(self.module.AuditError, "one exact EUD identity"):
            self.module.materialized_bytes(base)

    def test_provider_symbol_or_module_identity_mutation_is_rejected(self):
        modules = dict(self.bundle["modules"])
        self.assertGreater(
            modules["dwc3-msm.ko"].count(b"dwc3_restart_usb_host_mode\0"), 0
        )
        modules["dwc3-msm.ko"] = modules["dwc3-msm.ko"].replace(
            b"dwc3_restart_usb_host_mode\0", b"dwc3_restart_usb_host_noge\0"
        )
        with self.assertRaisesRegex(self.module.AuditError, "provider export"):
            self.module.audit_provider_elf(modules)
        spec = self.module.MODULE_SPECS["spu_verify.ko"]
        with tempfile.TemporaryDirectory() as name:
            path = Path(name) / "spu_verify.ko"
            path.write_bytes(self.bundle["modules"]["spu_verify.ko"] + b"x")
            with self.assertRaisesRegex(self.module.AuditError, "identity differs"):
                self.module.stable_bytes(
                    path,
                    label="mutated module",
                    maximum=spec.maximum,
                    expected_size=spec.size,
                    expected_sha256=spec.sha256,
                )

    def test_strict_v2_and_p318_receipt_binding_rejects_mutation(self):
        v2 = self.module.strict_json(self.bundle["v2"], "V2")
        v2["successor_plan"]["successor_plan_count"] = 74
        with self.assertRaisesRegex(self.module.AuditError, "V2 derivation"):
            self.module.audit_v2(v2)
        static = self.module.strict_json(self.bundle["p318_static"], "P3.18")
        rows = static["candidate"]["module_closure"]["modules"]
        next(row for row in rows if row["file"] == "dwc3-msm.ko")["sha256"] = "0" * 64
        with self.assertRaisesRegex(self.module.AuditError, "provider identity"):
            self.module.audit_p318_static(
                static, self.bundle["modules"]["dwc3-msm.ko"]
            )

    def test_unbound_import_cannot_build_authoritative_receipt(self):
        unbound = load_module("p319_successor_module_materialization_unbound")
        with self.assertRaisesRegex(unbound.AuditError, "unbound materializer"):
            unbound.build_result(self.bundle)

    def test_private_bundle_is_exact_mode0400_single_link(self):
        paths = self.module._paths(self.module.DEFAULT_OUTPUT_ROOT)
        self.assertEqual(paths["result"].read_bytes(), self.payload)
        for directory in (paths["inputs"], paths["sources"], paths["modules"], paths["stock"]):
            for path in directory.iterdir():
                state = path.stat()
                self.assertTrue(path.is_file())
                self.assertEqual(state.st_mode & 0o777, 0o400)
                self.assertEqual(state.st_nlink, 1)
        result_state = paths["result"].stat()
        self.assertEqual(result_state.st_mode & 0o777, 0o400)
        self.assertEqual(result_state.st_nlink, 1)

    def test_writer_normalizes_hostile_umask_and_refuses_clobber(self):
        with tempfile.TemporaryDirectory() as name:
            path = Path(name) / "receipt.json"
            old = os.umask(0o777)
            try:
                self.module._write_exclusive(path, b"{}\n")
            finally:
                os.umask(old)
            self.assertEqual(path.stat().st_mode & 0o777, 0o400)
            with self.assertRaises(FileExistsError):
                self.module._write_exclusive(path, b"changed\n")

    def test_independent_tmp_regeneration_is_byte_identical(self):
        with tempfile.TemporaryDirectory() as name:
            output = Path(name) / "materialization"
            result, payload = self.module.run(output, materialize=True)
            self.module.publish_result(output, payload)
            self.assertEqual(payload, self.payload)
            self.assertEqual(result, self.result)
            self.assertEqual((output / "result.json").read_bytes(), self.payload)

    def test_receipt_refuses_to_claim_candidate_or_live_authority(self):
        conclusion = self.result["conclusion"]
        self.assertTrue(conclusion["successor_plan_header_materialized"])
        self.assertTrue(conclusion["successor_runtime_hook_materialized"])
        self.assertFalse(conclusion["candidate_userspace_built"])
        self.assertFalse(conclusion["candidate_boot_built"])
        self.assertFalse(conclusion["candidate_packaged"])
        self.assertFalse(conclusion["parser_qualified"])
        self.assertFalse(conclusion["candidate_build_qualified"])
        self.assertFalse(conclusion["symbol_stub_authorized"])
        self.assertFalse(self.result["scope"]["device_contact"])
        self.assertFalse(self.result["scope"]["live_authority_created"])

    def test_report_records_exact_materialization_and_authority_boundary(self):
        report = REPORT.read_text(encoding="utf-8")
        for token in (
            "IMPLEMENTED_REVIEW_PENDING; H0 ONLY; NO LIVE AUTHORITY",
            "14,833-byte V2 receipt",
            "only three missing",
            "ramdisk `lib/modules` and stock `vendor_dlkm/lib/modules`",
            "S22PLUS_O2_EUD_MODULE_INDEX 38U",
            "Both module loops call that same helper only after their load has succeeded.",
            "`R_AARCH64_CALL26` relocation at `.text+0x12318`",
            "10,658 bytes",
            "8b8c1f5afd8c02693901d3552c221bcc73bafa2543c77dfff4954bdba188f6b5",
            "creates no second pending topic",
            "No candidate or device action may be inferred",
        ):
            with self.subTest(token=token):
                self.assertIn(token, report)

    def test_ledger_records_materialization_under_existing_obligation(self):
        rows = [
            line
            for line in LEDGER.read_text(encoding="utf-8").splitlines()
            if "h0-module-closure-materialization-v1-9" in line
        ]
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertIn("UNDER_EXISTING_MODULE_CLOSURE_REVIEW_OBLIGATION", row)
        self.assertIn("10658-byte 8b8c1f5a", row)
        self.assertIn("16/16", row)
        self.assertIn("creates no second pending topic", row)
        self.assertIn("no device", row)

    def test_goal_keeps_build_and_live_authority_closed(self):
        goal = GOAL.read_text(encoding="utf-8")
        self.assertIn("73-row plan", goal)
        self.assertIn("S22PLUS_FYG8_P319_SUCCESSOR_MODULE_MATERIALIZATION_H0_2026-08-20.md", goal)
        self.assertIn("stock-witness runtime/build closure is independently reviewed `PASS_GO`, H0-only", goal)
        self.assertLessEqual(len(goal.splitlines()), 900)


if __name__ == "__main__":
    unittest.main()

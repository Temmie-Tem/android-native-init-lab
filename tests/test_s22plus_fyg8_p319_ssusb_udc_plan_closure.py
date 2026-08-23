from __future__ import annotations

import copy
import importlib.util
import stat
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / (
    "workspace/public/src/scripts/analysis/"
    "s22plus_fyg8_p319_ssusb_udc_plan_closure.py"
)
REPORT = ROOT / (
    "docs/reports/"
    "S22PLUS_FYG8_P319_SSUSB_UDC_PLAN_CLOSURE_H0_2026-08-24.md"
)
LEDGER = ROOT / "docs/operations/CAMPAIGN_LEDGER_S22PLUS.md"


def load_module():
    spec = importlib.util.spec_from_file_location(
        "p319_ssusb_udc_plan_closure_tested", SCRIPT
    )
    if spec is None or spec.loader is None:
        raise AssertionError("unable to load P319 SSUSB/UDC closure")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.load_bound_auditor()


class P319SsusbUdcPlanClosureTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()
        cls.result, cls.payload = cls.module.run()
        cls.phase = cls.module.json_object(
            cls.module.PHASE_RESULT.read_bytes(), "phase fixture"
        )
        cls.plan_source = cls.module.PLAN_SOURCE.read_bytes()
        cls.wrapper = cls.module.WRAPPER_SOURCE.read_bytes()
        cls.runtime = cls.module.RUNTIME_SOURCE.read_bytes()
        cls.role = cls.module.ROLE_SOURCE.read_bytes()
        cls.module_payloads = {
            row["file"]: (cls.module.MODULE_DIR / row["file"]).read_bytes()
            for row in cls.phase["module_crc_closure"]["modules"]
        }

    def test_exact_plan_closes_declared_and_crc_dependencies(self):
        plan = self.result["plan_closure"]
        self.assertEqual(plan["module_count"], 73)
        self.assertEqual(plan["declared_dependency_edges"], 110)
        self.assertEqual(plan["missing_declared_dependencies"], [])
        self.assertEqual(plan["dependency_order_violations"], [])
        self.assertTrue(plan["crc_provider_closure"]["ordered_crc_closed"])
        self.assertEqual(
            plan["crc_provider_closure"]["provider_resolution"],
            {
                "fixed_image_imports": 3238,
                "earlier_module_imports": 328,
                "total_resolved_imports": 3566,
            },
        )

    def test_recovery_control_is_a_byte_exact_superset(self):
        recovery = self.result["recovery_control_comparison"]
        self.assertEqual(recovery["modules_load_recovery"]["line_count"], 446)
        self.assertEqual(recovery["modules_load_recovery"]["unique_count"], 441)
        self.assertEqual(recovery["candidate_stock_row_count"], 72)
        self.assertEqual(
            recovery["candidate_stock_module_bytes_identical_to_vendor_ramdisk"],
            72,
        )
        self.assertEqual(recovery["recovery_unique_members_outside_candidate"], 369)
        self.assertEqual(
            recovery["only_non_recovery_candidate_row"],
            "s22plus_dwc3_event_latch.ko",
        )

    def test_image_and_exact_elf_bind_the_mode_and_udc_producers(self):
        image = self.result["fixed_image"]
        self.assertTrue(image["dwc3_core_built_in"])
        self.assertTrue(image["gadget_core_built_in"])
        self.assertTrue(image["ucsi_core_built_in"])
        mode = self.result["mode_producer"]
        self.assertEqual(
            mode["direct_mode_path"],
            ["mode_store", "dwc3_msm_set_role", "dwc3_ext_event_notify"],
        )
        self.assertIn(
            "dwc3_otg_start_peripheral->usb_gadget_connect",
            mode["required_call_edges"],
        )

    def test_runtime_waits_for_ssusb_dwc3_and_udc_before_role_phase(self):
        runtime = self.result["runtime"]
        self.assertTrue(runtime["module_loops_precede_bind_gates"])
        self.assertTrue(runtime["all_bind_gates_precede_experiment_runtime"])
        self.assertTrue(runtime["ssusb_dwc3_udc_gates_precede_role_write"])
        self.assertEqual(runtime["direct_role_value"], "peripheral")
        self.assertEqual(
            runtime["exact_role_path"],
            "/sys/devices/platform/soc/a600000.ssusb/mode",
        )

    def test_dependency_order_mutation_is_rejected(self):
        first = (
            b'    {"usb_notify_layer.ko", "usb_notify_layer", ""},\n'
        )
        second = (
            b'    {"usb_notifier_qcom.ko", "usb_notifier_qcom", ""},\n'
        )
        self.assertEqual(self.plan_source.count(first), 1)
        self.assertEqual(self.plan_source.count(second), 1)
        mutated_source = self.plan_source.replace(first, b"__SWAP__\n", 1)
        mutated_source = mutated_source.replace(second, first, 1)
        mutated_source = mutated_source.replace(b"__SWAP__\n", second, 1)
        mutated_phase = copy.deepcopy(self.phase)
        rows = mutated_phase["plan"]["rows"]
        left = next(i for i, row in enumerate(rows) if row["file"] == "usb_notify_layer.ko")
        right = next(
            i for i, row in enumerate(rows)
            if row["file"] == "usb_notifier_qcom.ko"
        )
        rows[left], rows[right] = rows[right], rows[left]
        with self.assertRaisesRegex(
            self.module.AuditError, "dependency closure"
        ):
            self.module.audit_plan(
                mutated_phase, mutated_source, self.module_payloads
            )

    def test_plan_count_declaration_drift_is_rejected(self):
        mutated = copy.deepcopy(self.phase)
        mutated["plan"]["module_count"] = 72
        with self.assertRaisesRegex(
            self.module.AuditError, "phase result and plan source"
        ):
            self.module.audit_plan(
                mutated, self.plan_source, self.module_payloads
            )

    def test_dtb_compatible_mutation_is_rejected(self):
        dtb = self.module.VENDOR_DTB.read_bytes()
        old = b"qcom,dwc-usb3-msm\x00"
        new = b"qcom,dwc-usb3-bad\x00"
        self.assertEqual(len(old), len(new))
        self.assertGreater(dtb.count(old), 0)
        with self.assertRaisesRegex(
            self.module.p251.AuditError, "SSUSB compatible"
        ):
            self.module.p251.audit_vendor_dtb(dtb.replace(old, new))

    def test_direct_role_value_mutation_is_rejected(self):
        mutated = self.role.replace(
            b'rc = p260_write_value(p260_role_path, "peripheral");',
            b'rc = p260_write_value(p260_role_path, "host");',
            1,
        )
        self.assertNotEqual(mutated, self.role)
        with self.assertRaisesRegex(
            self.module.AuditError, "direct-role source token"
        ):
            self.module.audit_runtime(
                self.wrapper, self.runtime, mutated
            )

    def test_private_receipt_is_exact_deterministic_regeneration(self):
        self.assertEqual(self.module.OUTPUT.read_bytes(), self.payload)
        state = self.module.OUTPUT.stat()
        self.assertEqual(stat.S_IMODE(state.st_mode), 0o400)
        self.assertEqual(state.st_nlink, 1)

    def test_conclusion_does_not_upgrade_static_closure_to_runtime_proof(self):
        conclusion = self.result["conclusion"]
        self.assertTrue(conclusion["known_ssusb_module_membership_closed"])
        self.assertFalse(conclusion["dynamic_supplier_bind_proved"])
        self.assertFalse(conclusion["dwc3_msm_probe_success_proved"])
        self.assertFalse(conclusion["candidate_udc_creation_proved"])
        self.assertFalse(conclusion["natural_ucsi_stock_path_closed"])
        self.assertFalse(self.result["scope"]["device_contact"])
        self.assertFalse(self.result["scope"]["live_authority_created"])

    def test_report_and_ledger_preserve_the_review_boundary(self):
        report = REPORT.read_text(encoding="utf-8")
        for token in (
            "PASS_P319_SSUSB_UDC_PLAN_CLOSURE_H0",
            "PASS_GO_P319_SSUSB_UDC_PLAN_CLOSURE_H0_CAPABILITY_V1",
            "yes for static membership, order, and ABI closure",
            "unproved for runtime bind and probe success",
            "does not silently repin",
            "topic 37",
        ):
            self.assertIn(token, report)
        implementation_rows = [
            line
            for line in LEDGER.read_text(encoding="utf-8").splitlines()
            if " h0-ssusb-udc-plan-closure-37 " in line
        ]
        review_rows = [
            line
            for line in LEDGER.read_text(encoding="utf-8").splitlines()
            if " h0-ssusb-udc-plan-closure-review-37 " in line
        ]
        self.assertEqual(len(implementation_rows), 1)
        self.assertEqual(len(review_rows), 1)
        self.assertIn(
            "P319_SSUSB_UDC_PLAN_CLOSURE_IMPLEMENTED_REVIEW_PENDING",
            implementation_rows[0],
        )
        self.assertIn(
            "PASS_GO_P319_SSUSB_UDC_PLAN_CLOSURE_H0_CAPABILITY_V1",
            review_rows[0],
        )

    def test_auditor_has_no_device_or_transfer_primitive(self):
        source = SCRIPT.read_text(encoding="utf-8")
        for forbidden in (
            "import subprocess",
            "adb_command(",
            "adb reboot",
            "odin4 ",
            "fastboot ",
            "finit_module(",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()

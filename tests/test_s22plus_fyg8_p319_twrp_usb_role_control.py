from __future__ import annotations

from dataclasses import replace
import importlib.util
import stat
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / (
    "workspace/public/src/scripts/analysis/"
    "s22plus_fyg8_p319_twrp_usb_role_control.py"
)
REPORT = ROOT / (
    "docs/reports/"
    "S22PLUS_FYG8_P319_TWRP_USB_ROLE_CONTROL_H0_2026-08-24.md"
)
LEDGER = ROOT / "docs/operations/CAMPAIGN_LEDGER_S22PLUS.md"


def load_module():
    spec = importlib.util.spec_from_file_location(
        "p319_twrp_usb_role_control_tested", SCRIPT
    )
    if spec is None or spec.loader is None:
        raise AssertionError("unable to load P319 TWRP role-control auditor")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.load_bound_auditor()


class P319TwrpUsbRoleControlTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()
        cls.result, cls.payload = cls.module.run()
        recovery, cls.tar_member = cls.module.extract_recovery_image(
            cls.module.TWRP_TAR.read_bytes()
        )
        cls.header, parts = cls.module.parse_boot_image(recovery)
        _cpio, cls.entries = cls.module.cpio_map(parts["ramdisk_gzip"])
        cls.modules = {
            name: cls.entries[f"lib/modules/{name}"].data
            for name in cls.module.RELEVANT_MODULES
        }

    def test_exact_single_member_archive_and_boot_image_are_bound(self):
        self.assertEqual(self.tar_member["name"], "recovery.img")
        self.assertEqual(self.tar_member["size"], 55_435_280)
        self.assertEqual(self.header["header_version"], 2)
        self.assertEqual(self.header["page_size"], 4096)
        self.assertEqual(self.header["product"], "SRPUI14B002")
        self.assertEqual(self.header["samsung_footer"], "SEANDROIDENFORCE")
        self.assertTrue(self.header["all_inter_part_padding_zero"])

    def test_twrp_kernel_is_dual_role_and_not_candidate_exact(self):
        kernel = self.result["kernel"]
        self.assertEqual(kernel["image"]["size"], 41_488_896)
        self.assertTrue(kernel["different_from_stock_fyg8_and_current_candidate"])
        self.assertEqual(kernel["required_config"]["CONFIG_USB_DWC3_DUAL_ROLE"], "y")
        self.assertEqual(kernel["required_config"]["CONFIG_USB_ROLE_SWITCH"], "y")
        self.assertIn("5.10.81-afaneh92", kernel["required_config"]["kernel_banner"])

    def test_userspace_binds_configfs_without_an_ssusb_role_write(self):
        userspace = self.result["ramdisk"]["userspace"]
        self.assertEqual(userspace["controller_property"], "a600000.dwc3")
        self.assertEqual(userspace["configfs_udc_bind_count"], 4)
        self.assertEqual(userspace["configfs_udc_unbind_count"], 1)
        self.assertFalse(userspace["explicit_ssusb_mode_write"])
        self.assertFalse(userspace["explicit_udc_wait"])
        self.assertEqual(userspace["hidden_role_write_scan"], {
            "a600000.ssusb": [],
            "ssusb/mode": [],
        })

    def test_all_base_and_overlay_trees_retain_automatic_role_topology(self):
        tree = self.result["device_tree"]
        self.assertEqual(tree["base_dtb_count"], 4)
        self.assertEqual(tree["recovery_dtbo_entry_count"], 5)
        for row in tree["base_dtbs"]:
            self.assertEqual(row["child_dr_mode"], "otg")
            self.assertTrue(row["child_role_switch"])
            self.assertEqual(row["ucsi_compatible"], "qcom,ucsi-glink")
        for row in tree["recovery_dtbo_entries"]:
            self.assertTrue(all(row["checks"].values()))

    def test_recovery_module_population_and_dwc3_closure_are_exact(self):
        modules = self.result["modules"]
        self.assertEqual(modules["modules_load_recovery"]["line_count"], 440)
        self.assertEqual(modules["modules_load_recovery"]["unique_count"], 438)
        self.assertEqual(modules["dwc3_transitive_dependency_count"], 28)
        for name in (
            "pmic_glink.ko",
            "ucsi_glink.ko",
            "usb_typec_manager.ko",
            "ssusb-redriver-nb7vpq904m.ko",
        ):
            self.assertIn(name, modules["dwc3_transitive_dependencies"])

    def test_pre_role_dwc3_materialization_is_instruction_bound(self):
        automatic = self.result["automatic_role_paths"]
        self.assertTrue(all(automatic["udc_bootstrap_instruction_checks"].values()))
        self.assertEqual(
            automatic["dwc3_symbol_layout"]["dwc3_msm_core_init"],
            {"address": "0xaf9c", "size": 1404},
        )
        self.assertIn(
            "dwc3_otg_sm_work->dwc3_msm_core_init",
            automatic["dwc3_bootstrap_edges"],
        )
        self.assertIn(
            "dwc3_msm_core_init->of_platform_populate",
            automatic["dwc3_bootstrap_edges"],
        )

    def test_two_automatic_role_paths_are_present_but_no_winner_is_claimed(self):
        automatic = self.result["automatic_role_paths"]
        self.assertTrue(automatic["set_peripheral_callback"]["bound"])
        self.assertIn(
            "qcom_set_peripheral->dwc_msm_vbus_event",
            automatic["samsung_notifier_edges"],
        )
        self.assertIn(
            "ucsi_probe->pmic_glink_register_client",
            automatic["ucsi_transport_edges"],
        )
        self.assertFalse(automatic["ucsi_path_execution_proved"])
        self.assertFalse(automatic["unique_winning_role_producer_proved"])

    def test_historical_control_does_not_invent_a_role_transition_trace(self):
        historical = self.result["historical_control"]
        self.assertTrue(historical["exact_recovery_prefix_match_recorded"])
        self.assertTrue(historical["recovery_adb_success_recorded"])
        self.assertFalse(historical["runtime_role_producer_retained"])

    def test_candidate_comparison_rejects_twrp_byte_transfer(self):
        comparison = self.result["candidate_comparison"]
        plan = comparison["current_p319_plan"]
        self.assertEqual(plan["module_count"], 73)
        self.assertEqual(plan["eud_index"], 38)
        self.assertEqual(plan["comparison_module_count"], 8)
        self.assertEqual(plan["byte_identical_to_twrp"], [])
        self.assertEqual(plan["byte_different_from_twrp_count"], 8)
        self.assertFalse(comparison["twrp_selected_module_bytes_transferable"])
        self.assertFalse(comparison["twrp_kernel_or_dt_transferable"])

    def test_hidden_userspace_role_write_mutation_is_rejected(self):
        mutated = dict(self.entries)
        entry = mutated["init.recovery.usb.rc"]
        mutated[entry.name] = replace(entry, data=entry.data + b"\n# a600000.ssusb\n")
        with self.assertRaisesRegex(
            self.module.AuditError, "unregistered SSUSB role write"
        ):
            self.module.audit_userspace(mutated)

    def test_dwc3_symbol_identity_mutation_is_rejected(self):
        old = b"dwc3_msm_core_init"
        new = b"dwc3_msm_core_badx"
        self.assertEqual(len(old), len(new))
        self.assertGreater(self.modules["dwc3-msm.ko"].count(old), 0)
        mutated = dict(self.modules)
        mutated["dwc3-msm.ko"] = mutated["dwc3-msm.ko"].replace(old, new)
        with self.assertRaisesRegex(
            self.module.AuditError, "automatic role ELF edges differ"
        ):
            self.module.audit_elf_modules(mutated, enforce_identities=False)

    def test_private_receipt_is_exact_deterministic_regeneration(self):
        self.assertEqual(self.module.OUTPUT.read_bytes(), self.payload)
        state = self.module.OUTPUT.stat()
        self.assertEqual(stat.S_IMODE(state.st_mode), 0o400)
        self.assertEqual(state.st_nlink, 1)

    def test_conclusion_preserves_runtime_and_authority_boundaries(self):
        conclusion = self.result["conclusion"]
        self.assertTrue(conclusion["twrp_has_pre_role_udc_materialization_path"])
        self.assertFalse(conclusion["twrp_runtime_udc_creation_proved"])
        self.assertFalse(conclusion["historical_twrp_adb_selects_unique_candidate"])
        self.assertFalse(conclusion["current_p319_direct_mode_path_should_be_removed"])
        self.assertFalse(conclusion["current_p319_module_growth_justified"])
        self.assertFalse(self.result["scope"]["device_contact"])
        self.assertFalse(self.result["scope"]["live_authority_created"])

    def test_report_and_ledger_preserve_the_review_boundary(self):
        report = REPORT.read_text(encoding="utf-8")
        for token in (
            "PASS_P319_TWRP_USB_ROLE_CONTROL_H0",
            "PASS_GO_P319_TWRP_USB_ROLE_CONTROL_H0_CAPABILITY_V1",
            "6b08c15b18abcf027253087801412e2b447359c42ef45dbbc339e9223e6f8393",
            "identify which automatic producer won",
            "byte-identical between TWRP and P3.19",
            "does not clear",
            "topic 38",
        ):
            self.assertIn(token, report)
        implementation_rows = [
            line
            for line in LEDGER.read_text(encoding="utf-8").splitlines()
            if " h0-twrp-usb-role-control-38 " in line
        ]
        review_rows = [
            line
            for line in LEDGER.read_text(encoding="utf-8").splitlines()
            if " h0-twrp-usb-role-control-review-38 " in line
        ]
        self.assertEqual(len(implementation_rows), 1)
        self.assertEqual(len(review_rows), 1)
        self.assertIn(
            "P319_TWRP_USB_ROLE_CONTROL_IMPLEMENTED_REVIEW_PENDING",
            implementation_rows[0],
        )
        self.assertIn(
            "PASS_GO_P319_TWRP_USB_ROLE_CONTROL_H0_CAPABILITY_V1",
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

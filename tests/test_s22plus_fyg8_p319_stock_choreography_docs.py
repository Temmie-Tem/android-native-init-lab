import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / (
    "docs/reports/"
    "S22PLUS_FYG8_P319_STOCK_USERSPACE_CHOREOGRAPHY_H0_2026-08-19.md"
)
LEDGER = ROOT / "docs/operations/CAMPAIGN_LEDGER_S22PLUS.md"


class P319StockChoreographyDocsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = REPORT.read_text(encoding="utf-8")

    def test_report_states_the_h0_only_authority_boundary(self):
        for token in (
            "IMPLEMENTED_REVIEW_PENDING",
            "NO DEVICE OR LIVE AUTHORITY",
            "creates no D0, D1, F1, recovery, replay, device,\nor live authority",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)

    def test_report_pins_the_three_properties_that_select_the_path(self):
        # The chain is only reproducible if the branch conditions are pinned
        # to this unit's values rather than assumed from the generic vendor rc.
        for token in (
            "vendor.usb.use_gadget_hal=0",
            "vendor/build.prop:326",
            "vendor.usb.controller=a600000.dwc3",
            "init.target.rc:130",
            "androidboot.usbcontroller=a600000.dwc3",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)

    def test_report_states_the_udc_bind_ordering_gate(self):
        self.assertIn(
            "the UDC bind\nis gated on a userspace daemon having already opened "
            "the function's endpoints.",
            self.report,
        )
        self.assertIn("sys.usb.ffs.ready", self.report)

    def test_report_records_the_inert_aosp_usb_rc(self):
        for token in (
            "entirely gated on `sys.usb.configfs=0`",
            "is therefore inert here",
            "on property:init.svc.adbd=stopped",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)

    def refutation_section(self):
        section = re.search(
            r"^## (\w+) candidate causes this unit refutes$(.*?)(?=^## )",
            self.report,
            re.MULTILINE | re.DOTALL,
        )
        self.assertIsNotNone(section, "refutation section missing")
        return section.group(1), re.findall(
            r"^\*\*\d\. ", section.group(2), re.MULTILINE
        )

    def test_refutation_count_matches_its_own_numbered_items(self):
        word, items = self.refutation_section()
        self.assertEqual(word, "Four")
        self.assertEqual(len(items), 4)

    def test_each_refutation_carries_a_binary_level_anchor(self):
        # A refutation from the source alone would not survive a config change;
        # each of these is anchored in a shipped .ko or an initialiser.
        for token in (
            "has no `pmic_info`, `charging_mode`, or\n`ccic_info` symbol",
            "carries no bare `lpcharge` or\n`factory_mode` symbol",
            "`set_gpio_usb_sel` is never assigned anywhere in the tree",
            "`usb_notify_sysfs.c:1260` sets\n`udev->usb_data_enabled = 1`",
            "`is_blocked` returns false on a NULL `otg_notify`",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)

    def test_report_records_the_module_parameter_mechanism_and_why_it_is_benign(self):
        for token in (
            "muic_param_pmic_info=3",
            "There\nis no `modules.options` anywhere",
            "`insmod` does\nnot do this",
            "-1 & 0xfff = 0xfff",
            "the same result as the stock value\nof 3",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)

    def test_report_corrects_the_three_nonexistent_hal_paths(self):
        for token in (
            "**None of the three exists in this kernel.**",
            "`b_sess`\ndoes not appear anywhere under `drivers/`",
            "The HAL is named for `coral`, a Pixel",
            "`orientation`, `mode`, `speed`, `bus_vote`",
            "The review's `a600000.ssusb/mode`\nis real",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)

    def test_report_does_not_present_usb_sel_as_a_switch(self):
        self.assertIn("**It issues no I²C.**", self.report)
        self.assertIn("it does not move the mux", self.report)

    def test_report_names_the_next_measurement_as_a_read(self):
        self.assertIn(
            "cat /sys/bus/platform/devices/a600000.ssusb/mode", self.report
        )
        self.assertIn("has no side effect", self.report)
        self.assertIn(
            "strictly weaker action than the Stage B\nregister read", self.report
        )
        # The body first described mode as the controller's actual current role.
        self.assertIn(
            "It returns the role the driver has been told to take, not the\n"
            "controller's negotiated state",
            self.report,
        )
        self.assertNotIn("returns the controller's actual current role.", self.report)

    def test_report_keeps_the_ss_mon_question_open_rather_than_answering_it(self):
        self.assertIn(
            "Whether it is required for the pull-up is not\nestablished here",
            self.report,
        )

    def test_report_records_the_measured_control_tuple(self):
        for token in (
            "| `a600000.ssusb/mode` | `peripheral` |",
            "| `udc/state` | `configured` |",
            "| `udc/current_speed` | `super-speed` |",
            "| `configfs g1/UDC` | `a600000.dwc3` |",
            "`a600000.dwc3`, `dummy_udc.0`",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)

    def test_report_withdraws_its_own_novelty_claims(self):
        # Both claims were checked against the campaign's own record after the
        # measurement, and both were too strong.
        for token in (
            "**First correction: this is not a new control.**",
            "S22PLUS_FYG8_P278_..._2026-07-26",
            "**Second correction: the runner is not a new instrument for the candidate.**",
            "p260_wait_role_and_udc",
            "p260_wait_configured",
            "a reproducible stock\ncontrol tuple",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)

    def test_report_bounds_the_high_speed_predicate_without_calling_it_a_defect(self):
        for token in (
            "It is not a defect and not a discovery",
            "S22PLUS_FYG8_P274_..._2026-07-26",
            "finds no run\nin which stage `0x8f` produced `EPROTO`",
            "bounds it rather than clearing it",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)

    def test_report_records_the_dummy_udc_trap_as_already_closed(self):
        for token in (
            "there is no\n`dummy_hcd.ko`",
            "built into the kernel",
            "That trap is already\nclosed",
            '`p260_udc_name` is the literal `"a600000.dwc3"`',
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)

    def test_report_closes_the_module_identity_question_with_a_digest(self):
        for token in (
            "27e988788242888dc0c3acaf835a66585c024b034b07741e619b674ee77db3db  ramdisk",
            "27e988788242888dc0c3acaf835a66585c024b034b07741e619b674ee77db3db  vendor_dlkm",
            "here they\nare the same file",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)

    def test_report_states_the_whole_tree_comparison_not_just_the_one_module(self):
        for token in (
            "441 `.ko` files",
            "`vendor_dlkm` holds 356",
            "**all 306 are byte\nidentical, with zero differences**",
            "every one of the 135 is in the ramdisk's\n  own 140-entry first-stage",
            "Not one of them matches `usb`, `typec`, `muic`, `pdic`, `dwc`, `phy`, or\n  `redriver`",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)

    def test_report_states_the_consequence_for_a_candidate(self):
        for token in (
            "no difference between the two copies can explain any candidate\nfailure",
            "no candidate needs to mount a logical partition to reach the USB\npath",
            "strictly stronger statement than the matching\nvermagic",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)

    def test_report_no_longer_lists_the_identity_question_as_open(self):
        self.assertNotIn(
            "- The ramdisk versus `vendor_dlkm` `pdic_max77705.ko` identity, "
            "still unresolved.",
            self.report,
        )

    def test_report_reproduces_the_review_counts_rather_than_repeating_them(self):
        for token in (
            "They were checked rather than repeated.",
            "**42\noverlapping and 27 genuinely late**, exactly the review's figures",
            "69 entries with 69 unique names, which is the\nself-check",
            "`EXPECTED_MODULE_PLAN_COUNT = 69`",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)

    def test_report_verifies_the_candidate_passes_no_module_parameters(self):
        for token in (
            "**The candidate passes no module parameters at all.**",
            "it is the empty string for all 59 base entries",
            "verified in the plan rather\nthan inferred",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)

    def test_report_reads_the_omission_as_a_substitution(self):
        for token in (
            "**The plan omits the stock mux driver, and the omission is a substitution.**",
            "`mfd_max77705.ko`, `spu_verify.ko` and `pdic_max77705.ko`",
            'CUSTOM_LATE_COMPAT = "maxim,max77705"',
            "Two drivers\ncannot bind one device",
            "not an oversight but a\nprecondition",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)

    def test_report_scopes_the_consequence_to_p317_only(self):
        # The campaign has already corrected one generalisation from stock or
        # from one candidate to candidates at large; this must not repeat it.
        for token in (
            "The consequence is specific to P3.17 and must not be generalised.",
            "This says nothing about\nother candidates.",
            "S7A2, M7, M11, M12 and M18 did load `pdic_max77705` and failed\nanyway",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)

    def test_report_does_not_read_the_96_omissions_as_a_defect(self):
        self.assertIn("omits 96 of the 140 stock first-stage modules", self.report)
        self.assertIn(
            "recorded as a fact about scope, not as a defect", self.report
        )

    def test_report_no_longer_lists_the_plan_diff_as_open(self):
        self.assertNotIn(
            "- The 69-entry P3.17 plan against the 140-entry first-stage list.\n",
            self.report,
        )

    def test_ledger_records_one_row_for_this_topic(self):
        rows = [
            line
            for line in LEDGER.read_text(encoding="utf-8").splitlines()
            if "h0-stock-choreography-1 " in line
        ]
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertIn("s22plus-fyg8-p319", row)
        self.assertIn(
            "P319_STOCK_USERSPACE_CHOREOGRAPHY_IMPLEMENTED_REVIEW_PENDING", row
        )
        self.assertIn("| 0/0 |", row)


if __name__ == "__main__":
    unittest.main()

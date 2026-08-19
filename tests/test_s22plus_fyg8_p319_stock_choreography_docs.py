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

    def test_report_keeps_the_ss_mon_question_open_rather_than_answering_it(self):
        self.assertIn(
            "Whether it is required for the pull-up is not\nestablished here",
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

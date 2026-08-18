import hashlib
import importlib.util
import re
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "docs/reports/S22PLUS_FYG8_P319_STAGE_A_PROBE_RESULT_2026-08-18.md"
REVALIDATION = ROOT / "workspace/public/src/scripts/revalidation"
PROBE = REVALIDATION / "s22plus_fyg8_p319_stage_a_truncation_probe.py"
STAGE_A = REVALIDATION / "s22plus_fyg8_p319_max77705_attribute_stage_a.py"
LEDGER = ROOT / "docs/operations/CAMPAIGN_LEDGER_S22PLUS.md"


def load(path: Path, name: str):
    if str(REVALIDATION) not in sys.path:
        sys.path.insert(0, str(REVALIDATION))
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class P319StageAProbeDocsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = REPORT.read_text(encoding="utf-8")
        cls.probe = load(PROBE, "p319_stage_a_probe_doc")
        cls.stage_a = load(STAGE_A, "p319_stage_a_doc")

    def test_probe_safety_contract_is_listing_only_and_pinned(self):
        safety = self.probe.probe_safety_contract()
        self.assertEqual(safety["result"], "pass")
        self.assertTrue(safety["listing_and_inode_test_only"])
        for name in (
            "sysfs_write_count",
            "attribute_body_read_count",
            "debugfs_access_count",
            "i2c_device_access_count",
            "module_action_count",
            "reboot_count",
        ):
            with self.subTest(name=name):
                self.assertEqual(safety[name], 0)
        self.assertIn(safety["script_sha256"], self.report)

    def test_stage_a_pinned_contract_is_untouched(self):
        # The result was obtained without editing Stage A; that is the claim.
        digest = self.stage_a.stage_a_safety_contract()["script_sha256"]
        self.assertEqual(
            digest,
            "e60e71042381ff258d870b6520e18ad3b05c251524e275fe210a2886a34eabbe",
        )
        self.assertIn("e60e7104", self.report)

    def test_report_states_the_regmap_answer_with_both_proofs(self):
        for token in (
            "There is **no `regmap` entry** under the Max77705 `57-0066` I2C client.",
            "regmap_in_listing  : False",
            'regmap_present     : no       [ -e "$client/regmap" ]',
            "uevent_in_listing  : True",
            "reached_end        : True",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)

    def test_report_names_the_stage_a_defect_and_the_offending_entry(self):
        for token in (
            "supplier:platform:c42d000.qcom,spmi:qcom,pm8350c@2:pinctrl@8800",
            "Commas and `@` are not permitted",
            "exited 23 on a legitimate sysfs name",
            "deliberately **not repaired here**",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)

    def test_report_records_why_the_failure_looked_like_success(self):
        for token in (
            "adb reported\n`returncode 0` with empty stderr",
            "Three hypotheses were tested and refuted",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)

    def test_report_blocks_stage_b_until_the_target_is_rederived(self):
        for token in (
            "`CONTROL1_R`/`CONTROL1_W` as opcodes",
            "The first was wrong and the second was also wrong.",
            # The path exists, and it was in this report's own table.
            "`57-0066` was the correct directory.",
            "only userspace `CONTROL1` entry point",
            "is **false**",
            "grants no authority for anything beyond it",
            "Full regmap dumps remain forbidden.",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)

    def test_report_records_the_fw_update_write_hazard(self):
        for token in (
            "**New hazard, recorded not exercised.**",
            "runs *before*\nthe `start_fw_update` switch",
            "must not be written\nwithout F1-class authority",
            "Nothing in this campaign has written it.",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)

    def test_report_admits_the_safety_contract_is_a_lint(self):
        for token in (
            "**That contract is a lint, not a proof.**",
            "ten dangerous scripts through it and nine passed",
            "*filename* net did the work",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)

    def test_probe_script_never_reads_an_attribute_body(self):
        script = self.probe.PROBE_SCRIPT
        for token in ("cat ", " od ", "dd ", "/dev/i2c", "/sys/kernel/debug"):
            with self.subTest(token=token):
                self.assertNotIn(token, script)
        self.assertIn("ls -a", script)
        # No `set -e`: the end sentinel must be reachable through a failure.
        self.assertNotIn("set -e", script)
        self.assertIn("probe\\tend", script)

    def test_ledger_records_the_probe_row(self):
        rows = [
            line
            for line in LEDGER.read_text(encoding="utf-8").splitlines()
            if "| stage-a-probe-1 |" in line
        ]
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertIn("s22plus-fyg8-p319", row)
        self.assertIn("| D0 |", row)
        self.assertIn("regmap", row)


    def test_report_records_the_mxim_surfaces_as_present_on_the_unit(self):
        for token in (
            "| `/dev/mxim_dev` | present |",
            "| `/sys/class/mxim/debug0` | present |",
            "| `debug0` entries | `opcode`, `power`, `reg`, `subsystem`, `uevent` |",
            "reachable on this unit",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)

    def reg_read_registers(self):
        """Return the stated call count and the register names it enumerates."""
        window = re.search(
            r"A read therefore performs\s+(\d+) single-byte(.*?)This matters because",
            self.report,
            re.DOTALL,
        )
        self.assertIsNotNone(window, "reg-read paragraph missing")
        names = [
            name
            for name in re.findall(r"`([^`]+)`", window.group(2))
            if re.fullmatch(r"[A-Z][A-Z0-9_]+", name)
        ]
        return int(window.group(1)), names

    def test_report_bounds_the_reg_read_by_enumerating_every_register(self):
        # A cost claim that is only a number can drift; make it derive from the
        # list, and make the list match the driver table minus the ignored rows.
        stated, names = self.reg_read_registers()
        self.assertEqual(stated, len(names))
        self.assertEqual(
            names,
            [
                "UIC_HW_REV",
                "UIC_FW_REV",
                "RSVD1",
                "USBC_STATUS1",
                "USBC_STATUS2",
                "BC_STATUS",
                "RSVD2",
                "CC_STATUS1",
                "CC_STATUS2",
                "PD_STATUS1",
                "PD_STATUS2",
                "USBC_IRQM",
                "CC_IRQM",
                "PD_IRQM",
            ],
        )
        # 17-entry table, three read-to-clear rows skipped by the driver.
        self.assertIn("fixed 17-entry table", self.report)
        for skipped in ("`USBC_IRQ` `0x02`", "`CC_IRQ`\n`0x03`", "`PD_IRQ` `0x04`"):
            with self.subTest(skipped=skipped):
                self.assertIn(skipped, self.report)
        self.assertEqual(stated + 3, 17)

    def test_report_keeps_the_full_dump_prohibition_while_clearing_this_path(self):
        for token in (
            "**Neither register is in this table.**",
            "prohibition on full regmap dumps still stands; this is not one.",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)

    def test_report_refuses_to_call_the_reg_read_a_control1_read(self):
        # Two Stage B claims in this report were already wrong; this one states
        # its own limit in the same breath as its result.
        for token in (
            "Stage B revives, but not as a CONTROL1 read",
            "`CONTROL1` is not in the table and is not at any\naddress it covers",
            "mux fields remain unreachable by\nreading",
            "A read opcode delivered by a mailbox write is still a command to the PD\ncontroller, and it is not a D0.",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)

    def test_report_records_the_mxim_write_and_concurrency_hazards(self):
        for token in (
            "Both `debug0` attributes are mode\n`0664`",
            "arbitrary single-register I2C write with no address validation",
            "issues an arbitrary opcode command",
            "`MXIM_DEBUG_REG_WRITE` and `MXIM_DEBUG_OPCODE_WRITE`",
            "These join `fw_update` as\nsurfaces that must not be written without F1-class authority",
            "Nothing in this\ncampaign has written any of them.",
            "neither sysfs `show` nor sysfs `store` takes\nany lock",
            "treat even the `opcode` *read* as deferred",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)

    def test_report_admits_its_own_width_dependent_parser_defect(self):
        for token in (
            "A defect in this probe, found in its own output",
            "column-collapsed",
            "The difference is entry-name width, not anything about the directories.",
            "same class of defect as\nthe Stage A truncation",
            "use `ls -a1` and must not derive a count",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)

    def test_probe_never_names_a_write_or_body_read_target(self):
        # The listing shows fw_update, reg and opcode; the probe must not touch
        # them.  Checked against the script bytes, not against the prose.
        script = self.probe.PROBE_SCRIPT
        for forbidden in ("fw_update", "cat ", "debug0/reg", "debug0/opcode", ">"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, script)
        self.assertIn("/sys/class/mxim/debug0", script)

    def test_ledger_records_the_mxim_probe_row(self):
        rows = [
            line
            for line in LEDGER.read_text(encoding="utf-8").splitlines()
            if " stage-a-probe-2 " in line
        ]
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertIn("s22plus-fyg8-p319", row)
        self.assertIn("| D0 |", row)
        self.assertIn("P319_MXIM_DEBUG_SURFACE_PRESENT_READ_ONLY", row)
        # A D0 row may not carry an H0 review label.
        self.assertNotIn("REVIEW_PENDING", row)
        for token in (
            "956854d8",
            "/dev/mxim_dev",
            "fourteen single-byte",
            "not as a CONTROL1 read",
            "must not be written without F1-class authority",
            "device_writes false",
        ):
            with self.subTest(token=token):
                self.assertIn(token, row)


if __name__ == "__main__":
    unittest.main()

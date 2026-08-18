import importlib.util
import io
import sys
import unittest
from contextlib import redirect_stderr
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REVALIDATION = ROOT / "workspace/public/src/scripts/revalidation"
RUNNER = REVALIDATION / "s22plus_fyg8_p319_max77705_reg_stage_b_d0.py"
AUDIT = REVALIDATION / "s22plus_fyg8_raw_first_observer_audit.py"
REPORT = ROOT / "docs/reports/S22PLUS_FYG8_P319_STAGE_A_PROBE_RESULT_2026-08-18.md"
LEDGER = ROOT / "docs/operations/CAMPAIGN_LEDGER_S22PLUS.md"


def load(path: Path, name: str):
    if str(REVALIDATION) not in sys.path:
        sys.path.insert(0, str(REVALIDATION))
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class P319StageBRegTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runner = load(RUNNER, "p319_stage_b_reg_runner")
        cls.report = REPORT.read_text(encoding="utf-8")

    # --- safety contract -------------------------------------------------

    def test_contract_proves_one_body_read_of_the_pinned_target(self):
        contract = self.runner.stage_b_safety_contract()
        self.assertEqual(contract["result"], "pass")
        self.assertTrue(contract["single_body_read_of_pinned_target"])
        self.assertEqual(contract["body_read_count"], 1)
        self.assertEqual(contract["body_read_line"], 'cat "$target"')
        self.assertEqual(
            contract["target_assignment"], "target=/sys/class/mxim/debug0/reg"
        )
        self.assertEqual(contract["redirect_count"], 0)
        self.assertEqual(contract["forbidden_path_hits"], [])

    def test_contract_rejects_every_way_of_widening_the_read(self):
        # The probe's token contract passed nine of ten dangerous scripts.  This
        # one is structural, so prove it actually rejects the shapes that matter.
        base = self.runner.STAGE_B_SCRIPT
        mutations = {
            "second body read": base + 'cat "$target"\n',
            "opcode read": base.replace(
                'cat "$target"',
                'cat "$target"\ncat /sys/class/mxim/debug0/opcode',
            ),
            "retargeted": base.replace(
                "target=/sys/class/mxim/debug0/reg",
                "target=/sys/class/mxim/debug0/opcode",
            ),
            "sysfs write": base + 'echo 0x06 0x09 > "$target"\n',
            "fw_update touched": base + "cat /sys/.../fw_update\n",
            "head instead of cat": base.replace('cat "$target"', 'head "$target"'),
        }
        for label, script in mutations.items():
            with self.subTest(mutation=label):
                contract = self.runner.stage_b_safety_contract(script)
                self.assertEqual(contract["result"], "fail")
                self.assertFalse(contract["single_body_read_of_pinned_target"])

    def test_script_never_names_a_write_primitive(self):
        script = self.runner.STAGE_B_SCRIPT
        for forbidden in ("opcode", "fw_update", "/dev/", "insmod", "reboot", "i2c"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, script)

    # --- the newly found read side effect --------------------------------

    def test_collect_refuses_until_the_vdm_int_clear_is_acknowledged(self):
        # Executed, not asserted in prose: the gate must return before any
        # device contact and before a run directory exists.
        run_root = ROOT / self.runner.DEFAULT_RUN_ROOT
        before = sorted(run_root.glob("d0-*")) if run_root.exists() else []
        stream = io.StringIO()
        with redirect_stderr(stream):
            code = self.runner.main(["--collect"])
        self.assertEqual(code, 3)
        self.assertIn("REG_VDM_INT", stream.getvalue())
        self.assertEqual(sorted(run_root.glob("d0-*")), before)

    def test_read_to_clear_address_is_the_mislabelled_vdm_int(self):
        self.assertEqual(self.runner.READ_TO_CLEAR_ADDRESSES, (0x05,))
        self.assertEqual(self.runner.REGISTERS[0x05][0], "REG_VDM_INT")
        decoded = self.runner.decode(0x05, 0x10)
        self.assertTrue(decoded["read_to_clear"])
        self.assertFalse(self.runner.decode(0x06, 0x00)["read_to_clear"])

    # --- register map ----------------------------------------------------

    def test_expected_addresses_are_the_fourteen_unignored_table_entries(self):
        self.assertEqual(
            self.runner.EXPECTED_ADDRESSES,
            (0x00, 0x01, 0x05, 0x06, 0x07, 0x08, 0x09,
             0x0A, 0x0B, 0x0C, 0x0D, 0x0E, 0x0F, 0x10),
        )
        self.assertEqual(len(self.runner.EXPECTED_ADDRESSES), 14)
        # The three skipped entries plus these fourteen are the whole table.
        self.assertEqual(len(self.runner.EXPECTED_ADDRESSES) + 3, 17)

    def test_names_follow_the_real_header_not_the_debug_headers_mislabels(self):
        # max77705_debug.h calls 0x09 RSVD2 and 0x0A/0x0C CC_STATUS1/PD_STATUS1;
        # max77705.h and the driver's own reads disagree, and the driver wins.
        for address, name in (
            (0x05, "REG_VDM_INT"),
            (0x09, "REG_UIC_FW_MINOR"),
            (0x0A, "REG_CC_STATUS0"),
            (0x0B, "REG_CC_STATUS1"),
            (0x0C, "REG_PD_STATUS0"),
            (0x0D, "REG_PD_STATUS1"),
        ):
            with self.subTest(address=address):
                self.assertEqual(self.runner.REGISTERS[address][0], name)

    def test_decode_matches_the_driver_bitfields(self):
        cc0 = self.runner.decode(0x0A, 0x41)["fields"]
        self.assertEqual(cc0["CCPinStat"], {"value": 1, "name": "CC1_ACTIVE"})
        self.assertEqual(cc0["CCIStat"], {"value": 0, "name": "NOT_IN_UFP_MODE"})
        self.assertEqual(cc0["CCVcnStat"], 0)
        self.assertEqual(cc0["CCStat"], {"value": 1, "name": "cc_SINK"})
        status1 = self.runner.decode(0x06, 0x25)["fields"]
        self.assertEqual(status1["VBADC"], {"value": 2, "name": "4.5-5.5V"})
        self.assertEqual(status1["UIDADC"], {"value": 5, "name": "UIADC_523K"})
        bc = self.runner.decode(0x08, 0x83)["fields"]
        self.assertEqual(bc["VBUSDet"], 1)
        self.assertEqual(bc["PrChgTyp"], {"value": 0, "name": "PRCHGTYP_UNKNOWN"})
        self.assertEqual(bc["DCDTmo"], 0)
        self.assertEqual(
            bc["ChgTyp"], {"value": 3, "name": "CHGTYP_DEDICATED_CHARGER"}
        )

    # --- parser refusals -------------------------------------------------

    def body(self, rows):
        lines = ["stage_b\tbegin", "target_present\tyes", "body\tbegin", "reg   val"]
        lines += rows
        lines += ["body\tend", "body_rc\t0", "stage_b\tend"]
        return "\n".join(lines) + "\n"

    def full_rows(self, value=0x11):
        return [
            f"0x{address:02x}  0x{value:02x}"
            for address in self.runner.EXPECTED_ADDRESSES
        ]

    def test_parser_accepts_a_complete_dump(self):
        observation = self.runner.parse_stage_b(self.body(self.full_rows()))
        self.assertTrue(observation["reached_end"])
        self.assertTrue(observation["header_seen"])
        self.assertTrue(observation["addresses_match_expected"])
        self.assertEqual(observation["row_count"], 14)
        self.assertFalse(observation["all_zero"])
        self.assertTrue(observation["identity_nonzero"])
        self.assertEqual(observation["body_rc"], "0")

    def test_parser_refuses_an_all_zero_dump(self):
        # A failed i2c read is truncated into the value byte, so an all-zero
        # dump is indistinguishable from fourteen failures and must not pass.
        observation = self.runner.parse_stage_b(self.body(self.full_rows(0x00)))
        self.assertTrue(observation["all_zero"])
        self.assertFalse(observation["identity_nonzero"])

    def test_parser_refuses_a_truncated_dump(self):
        observation = self.runner.parse_stage_b(self.body(self.full_rows()[:9]))
        self.assertEqual(observation["row_count"], 9)
        self.assertFalse(observation["addresses_match_expected"])

    def test_parser_records_unparsed_rows_rather_than_dropping_them(self):
        rows = self.full_rows()
        rows[3] = "0x06  garbage"
        observation = self.runner.parse_stage_b(self.body(rows))
        self.assertEqual(observation["unparsed_rows"], ["0x06  garbage"])
        self.assertFalse(observation["addresses_match_expected"])

    def test_missing_end_sentinel_is_not_a_complete_read(self):
        text = self.body(self.full_rows()).replace("stage_b\tend\n", "")
        self.assertFalse(self.runner.parse_stage_b(text)["reached_end"])

    # --- boundary registration -------------------------------------------

    def test_runner_is_declared_to_the_raw_first_boundary(self):
        audit = load(AUDIT, "p319_stage_b_audit_doc")
        # The filename must be one the boundary actually catches.
        self.assertIsNotNone(audit.OBSERVER_FILE_RE.fullmatch(RUNNER.name))

    # --- documentation ---------------------------------------------------

    def test_report_corrects_the_read_to_clear_claim(self):
        for token in (
            "A fourth interrupt register is read, and the report above said "
            "otherwise",
            "`MXIM_REG_RSVD1`",
            "clear all interrpts",
            "gated behind an explicit flag",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)

    def test_ledger_records_the_stage_b_runner_row(self):
        rows = [
            line
            for line in LEDGER.read_text(encoding="utf-8").splitlines()
            if " h0-stage-b-reg-runner-1 " in line
        ]
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertIn("| H0 |", row)
        self.assertIn("REVIEW_PENDING", row)
        for token in ("REG_VDM_INT", "no device", "123"):
            with self.subTest(token=token):
                self.assertIn(token, row)


    def test_enum_tables_decode_the_observed_dump(self):
        # Pins the one real measurement against decoder drift.  Values are the
        # d0-20260818T194353Z run; names come from max77705.h and
        # max77705-muic.h, not from the mislabelled debug header.
        observed = {
            0x06: ("VBADC", "4.5-5.5V"),
            0x07: ("SYSMsg", "SYSMSG_BOOT_POR"),
            0x08: ("ChgTyp", "CHGTYP_CDP"),
            0x0A: ("CCPinStat", "CC2_ACTIVE"),
            0x0C: ("PDMsg", "HARDRESET_SENT"),
        }
        values = {0x06: 0x27, 0x07: 0x05, 0x08: 0x82, 0x0A: 0xA1, 0x0C: 0x19}
        for address, (field, name) in observed.items():
            with self.subTest(address=address):
                fields = self.runner.decode(address, values[address])["fields"]
                self.assertEqual(fields[field]["name"], name)
        status1 = self.runner.decode(0x06, 0x27)["fields"]
        self.assertEqual(status1["UIDADC"]["name"], "UIADC_OPEN")
        cc0 = self.runner.decode(0x0A, 0xA1)["fields"]
        self.assertEqual(cc0["CCIStat"]["name"], "CCI_1_5A")
        self.assertEqual(cc0["CCStat"]["name"], "cc_SINK")
        pd1 = self.runner.decode(0x0D, 0x47)["fields"]
        self.assertEqual((pd1["PD_PSRDY"], pd1["PD_DataRole"]), (0, 0))

    def test_unknown_enum_values_are_named_reserved_not_dropped(self):
        # 0x01 and 0x02 have no vendor UIDADC name; the field must still report.
        self.assertEqual(
            self.runner.decode(0x06, 0x01)["fields"]["UIDADC"],
            {"value": 1, "name": "reserved"},
        )

    def test_report_states_the_stage_b_result_and_its_limits(self):
        for token in (
            "PASS_S22PLUS_FYG8_P319_MAX77705_REG_STAGE_B_D0",
            "The side effect cost nothing this time.",
            "That is inference, not measurement",
            "It does not answer the mux question.",
            "constrains\nthe \"D+/D- never got connected at all\" reading without resolving where the\nswitch sits.",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)


if __name__ == "__main__":
    unittest.main()

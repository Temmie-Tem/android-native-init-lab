"""Host-side regression fixtures for the optional UFS study."""
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "workspace/public/src/scripts/analysis"))
import s22plus_mainline_ufs_h0 as study


class UfsStudyTests(unittest.TestCase):
    def test_calls_in_comments_strings_prototypes_or_other_functions_do_not_count(self):
        source = '''int init(void);
int previous(void) { set_flag(); }
int init(void)
{
 /* set_flag(); */
 log("set_flag()");
 schedule_scan();
}
int another(void) { set_flag(); }
'''
        with self.assertRaisesRegex(ValueError, "missing ordered witness"):
            study.ordered(source, "init", ("set_flag(", "schedule_scan("))
        physical_path = source.replace(" schedule_scan();", " set_flag();\n schedule_scan();")
        lines = study.ordered(physical_path, "init", ("set_flag(", "schedule_scan("))
        self.assertEqual([x["line"] for x in lines], [7,8])
        with self.assertRaises(ValueError):
            study.ordered(physical_path, "init", ("schedule_scan(", "set_flag("))

    def test_historical_ml028_output_is_rejected_before_a_write(self):
        with self.assertRaisesRegex(ValueError, "new ML029 study output required"):
            study.run(study.ML028 / "would-be-study-output")

    def test_missing_clock_pair_or_duplicate_name_has_no_mapping(self):
        for names, values in ((b"a\0b\0", (0,1)), (b"a\0a\0", (0,1,2,3))):
            with self.subTest(names=names), self.assertRaises(ValueError):
                study.clock_ranges({"clock-names":names, "freq-table-hz":struct.pack(f">{len(values)}I",*values)})

    def test_real_dtc_rehearsal_retains_reservation_disabled_nodes_and_existing_usb_supply(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "fixture.dts"
            source.write_text('''/dts-v1/;
/memreserve/ 0x13000000 0x4000;
/ {
 soc@0 {
  tlmm: pinctrl@f100000 { gpio-controller; #gpio-cells = <2>; status = "disabled"; };
  rsc@17a00000 { regulators-0 { vreg_l5b_0p88: ldo5 { regulator-max-microvolt = <888000>; }; }; };
  ufs_mem_hc: ufshc@1d84000 { status = "disabled"; clock-names = "ref_clk", "core_clk"; freq-table-hz = <75 300 1 9>; };
  ufs_mem_phy: phy@1d87000 { status = "disabled"; };
  usb-phy { vdda-pll-supply = <&vreg_l5b_0p88>; };
 };
};
''')
            def run(_, argv):
                subprocess.run(argv, check=True, capture_output=True)
            baseline = root / "base.dtb"
            run("fixture",["dtc","-@","-I","dts","-O","dtb","-o",baseline,source])
            original = baseline.read_bytes()
            main = study.nodes(baseline)
            stock = {study.STOCK["host"]:{"clock-names":b"core_clk\0core_clk_ice\0ref_clk\0",
                     "freq-table-hz":struct.pack(">6I",1,9,75,300,0,0)}}
            study.rehearsal(stock, main, baseline, root, run)
            self.assertEqual(baseline.read_bytes(), original)
            out = study.nodes(root/"study.dtb")
            self.assertEqual(study.clock_ranges(out[study.MAIN["host"]]), {"ref_clk":(0,0),"core_clk":(1,9)})
            self.assertEqual(out["/soc@0/usb-phy"], main["/soc@0/usb-phy"])
            self.assertEqual(out[study.MAIN["phy"]]["status"], b"disabled\0")
            self.assertEqual((root/"restored.canonical").read_bytes(),(root/"baseline.canonical").read_bytes())


if __name__ == "__main__":
    unittest.main()

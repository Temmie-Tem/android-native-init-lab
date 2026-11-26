import json
from pathlib import Path
import shlex
import subprocess
import sys
import unittest
from unittest.mock import Mock, patch
from contextlib import ExitStack

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "workspace/public/src/scripts/revalidation"))
import s20plus_g986n_fdt_input_d0 as owner
from test_s20plus_g986n_fdt_layout_d0 import BOOT, DTS, tree

BASE = (DTS.replace("MEMRESERVE", "").replace("test,board", "qcom,kona")
        .replace("0x8000>", "0xaff25000>").replace("0x8100>", "0xafffe64c>")
        .replace("0 0 0 0x10000", "0 0xaf000000 0 0x1000000"))
RESULT = b"input_v1=500,match,match,match,match,1,1,1,1,1,0,0\n"


def compare(blob, app=("awk",)):
    tail = owner.query().rsplit(' | "$bb" awk ', 1)[1]
    hex_dump = subprocess.check_output(["od", "-An", "-v", "-tx1"], input=blob)
    run = subprocess.run([*app, *shlex.split(tail)], input=hex_dump, capture_output=True, timeout=45)
    if run.returncode or run.stderr:
        raise ValueError("reducer rejected input")
    return owner.parse(run.stdout)


class InputFdtTest(unittest.TestCase):
    def test_expected_tree_and_equivalent_four_byte_endpoints(self):
        for text in (BASE, BASE.replace("<0 0xaff", "<0xaff")):
            facts = compare(tree(text))
            self.assertEqual([facts[k] for k in ("initrd_start", "initrd_end", "initrd_size", "root_compatible")],
                             ["match"] * 4)
            self.assertTrue(all(facts[k] for k in owner.FLAGS[:5]))
            self.assertFalse(any(facts[k] for k in owner.FLAGS[5:]))

    def test_relocated_short_or_missing(self):
        for text, states in [
            (BASE.replace("0xaff25000","0xaff26000").replace("0xafffe64c","0xaffff64c"),
             ("higher","higher","match")),
            (BASE.replace("0xaff25000","0xaff24000"), ("lower","match","higher")),
            (BASE.replace("0xafffe64c","0xafffe64b"), ("match","lower","lower")),
            (BASE.replace("linux,initrd-start = <0 0xaff25000>;", ""), ("missing","match","missing")),
            (BASE.replace("linux,initrd-end = <0 0xafffe64c>;", ""), ("match","missing","missing")),
            (BASE.replace("linux,initrd-start = <0 0xaff25000>; linux,initrd-end = <0 0xafffe64c>;", ""),
             ("missing","missing","missing")),
        ]:
            with self.subTest(states=states):
                facts = compare(tree(text))
                self.assertEqual(tuple(facts[k] for k in ("initrd_start","initrd_end","initrd_size")), states)

    def test_structure_and_reservations(self):
        changed = BASE.replace('"qcom,kona"', '"qcom,kona","qcom,other"').replace("chosen {", 'chosen { status = "disabled";')
        changed = changed.replace("reg = <0 0x9000 0 0x100>;", "reg = <0 0xaff25000 0 1 0 0x7000 0 0>;")
        changed = changed.replace("/dts-v1/;", "/dts-v1/;\n/memreserve/ 0xafd24000 1;")
        facts = compare(tree(changed))
        self.assertEqual(facts["root_compatible"], "different")
        self.assertFalse(facts["chosen_status_ok"] or facts["reserved_reg_sizes_nonzero"])
        self.assertTrue(facts["assumed_input_tree_fixed_overlap"] and facts["expected_initrd_fixed_overlap"])

    def test_reject_cut_or_inconsistent_reply(self):
        self.assertEqual(owner.parse(b"layout_unavailable=missing\n"), {"observation":"missing"})
        with self.assertRaises(ValueError):
            compare(tree(BASE)[:-4])
        for bad in (RESULT[:-1], RESULT.replace(b",match,match,match,", b",higher,match,match,"),
                    RESULT.replace(b",match,match,match,", b",match,higher,lower,"), RESULT+b"raw"):
            with self.assertRaises(ValueError):
                owner.parse(bad)

    def test_live_brackets_and_no_raw_evidence(self):
        identity = owner.subject()
        expected = dict(owner.vendor.source_health(), boot_id_sha256=owner.io.sha(BOOT.encode()))
        before = ("fixture", "usb:fixture", {"boot_id": BOOT})
        for mode in ("ok", "changed", "truncated"):
            with self.subTest(mode=mode), ExitStack() as stack:
                def stub(obj, name, **args):
                    return stack.enter_context(patch.object(obj, name, **args))
                stub(owner, "admit")
                stub(owner.vendor, "source_health", return_value=expected)
                stub(owner.health.base,"tool_receipt")
                stub(owner.health,"_validate_adb_receipt",return_value={"path":"adb"})
                stub(owner.support,"bracket",side_effect=[before, before if mode!="changed" else ("other",)])
                capture=stub(owner.io,"root_capture",return_value=("overflow" if mode=="truncated" else "completed",0,RESULT,b""))
                evidence=Mock()
                if mode=="ok":
                    self.assertEqual(owner.collect(identity, evidence)["facts"]["initrd_start"], "match")
                else:
                    with self.assertRaises(ValueError):
                        owner.collect(identity,evidence)
                argv, deadline, limit = capture.call_args.args
                self.assertEqual(argv[:-1], ["adb","-s","fixture","shell","su","-c"])
                self.assertEqual((deadline,limit),(45,2048))
                self.assertIn(BOOT, argv[-1])
                evidence.publish_json.assert_called_once()
                self.assertNotIn("input_v1=", json.dumps(evidence.publish_json.call_args.args))


if __name__ == "__main__":
    unittest.main()

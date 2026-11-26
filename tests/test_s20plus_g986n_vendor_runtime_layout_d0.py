import re
import subprocess
import sys
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "workspace/public/src/scripts/revalidation"))
import s20plus_g986n_vendor_runtime_layout_d0 as owner
from test_s20plus_g986n_fdt_layout_d0 import BOOT, DTS, LAYOUT, tree


class RuntimeGeometryTest(unittest.TestCase):
    def test_fixed_interval_and_unchanged_filter(self):
        start, size, script = owner.fixed_query()
        self.assertEqual((start, start + size, size), (0xa4880000, 0xa8bbf000, 70512640))
        mask = lambda s: re.sub(r"awk -v dst=\d+ -v de=\d+ ", "awk D ", s, count=1)
        self.assertEqual(mask(script), mask(owner.io.root_template()))

    def test_exact_end_split_bank_and_one_byte_reservation(self):
        start, size, script = owner.fixed_query()
        args = re.search(r'awk (-v dst=\d+ -v de=\d+ -v src=\d+ -v se=\d+) ', script)[1].split()
        for banks, reserved, contained, overlap in [
            (f"0 {start:#x} 0 {size:#x}", "", True, False),
            (f"0 {start:#x} 0 {size-1:#x}", "", False, False),
            (f"0 {start:#x} 0 0x100000 0 {start+0x100000:#x} 0 {size-0x100000:#x}", "", False, False),
            (f"0 {start:#x} 0 {size:#x}", f"/memreserve/ {start+size-1:#x} 1;", True, True),
        ]:
            with self.subTest(banks=banks, reserved=reserved):
                dtb = tree(DTS.replace("MEMRESERVE", reserved).replace("0 0 0 0x10000", banks))
                data = subprocess.check_output(["od", "-An", "-v", "-tx1"], input=dtb)
                out = subprocess.check_output(["awk", *args, "-f", owner.io.AWK], input=data)
                facts = owner.io.parse_layout(out)
                self.assertEqual((facts["destination_one_bank"], facts["destination_fixed_overlap"]),
                                 (contained, overlap))

    def test_whole_connected_read_and_changed_post_boot(self):
        subject = owner.subject()
        expected = dict(owner.source_health(), boot_id_sha256=owner.io.sha(BOOT.encode()))
        before = ("sample", "usb:sample", {"boot_id": BOOT})
        for scenario in ("ok", "changed", "overflow"):
            with self.subTest(scenario=scenario), ExitStack() as mocks:
                def mocked(obj, name, **kw):
                    return mocks.enter_context(patch.object(obj, name, **kw))
                mocked(owner, "admit")
                mocked(owner, "source_health", return_value=expected)
                mocked(owner.health.base, "tool_receipt")
                mocked(owner.health, "_validate_adb_receipt", return_value={"path": "adb"})
                bracket = mocked(owner.support, "bracket", side_effect=[
                    before, before if scenario != "changed" else ("sample", "usb:other", before[2])])
                evidence = Mock()
                capture = mocked(owner.io, "root_capture", return_value=(
                    "overflow" if scenario == "overflow" else "completed", 0, LAYOUT, b""))
                if scenario == "ok":
                    facts = owner.collect(subject, evidence)["facts"]
                    self.assertTrue(facts["destination_one_bank"])
                    self.assertEqual(bracket.call_count, 2)
                else:
                    with self.assertRaises(ValueError):
                        owner.collect(subject, evidence)
                evidence.publish_json.assert_called_once()
                argv, timeout, limit = capture.call_args.args
                self.assertEqual(argv[:-1], ["adb", "-s", "sample", "shell", "su", "-c"])
                self.assertIn(BOOT, argv[-1])
                self.assertEqual((timeout, limit), (45, 2048))


if __name__ == "__main__":
    unittest.main()

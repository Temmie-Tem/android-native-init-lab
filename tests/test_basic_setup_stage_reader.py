"""The three S20+ milestones have individual counts and linear adjacency."""
from pathlib import Path
import subprocess
import sys
import unittest

SOURCE = Path(__file__).resolve().parents[1] / "workspace/public/src/mainline/s20plus_y2q_h0"
sys.path.insert(0, str(SOURCE))
import basic_setup_stage_reader as reader


class SetupScan(unittest.TestCase):
    def test_exact_counts(self):
        a, b, c = reader.frames("1" * 32).values()
        keys = ("dt_ready_count", "basic_enter_count", "basic_return_count",
                "dt_enter_pair_count", "enter_return_pair_count", "triple_count")
        examples = [(a+b+c, (1,1,1,1,1,1)), ((a+b+c)*4, (4,4,4,4,4,4)),
                    (a+b+b+c, (1,2,1,1,1,0)), (c+b+a, (1,1,1,0,0,0)),
                    (c+a+b, (1,1,1,1,0,0)), (b+c, (0,1,1,0,1,0)),
                    (c, (0,0,1,0,0,0)), (a+b"X"*256+b+c, (1,1,1,0,1,0)),
                    (b"X"*17+a+b+c[:-1], (1,1,0,1,0,0)),
                    (b"".join(reader.frames("2"*32).values()), (0,0,0,0,0,0))]
        for payload, expected in examples:
            with self.subTest(expected=expected):
                words = subprocess.check_output(["od", "-An", "-v", "-tx1"], input=payload)
                res = subprocess.run(["awk", "-v", f"expected={len(payload)}", "-v", "first="+a.hex(),
                                      "-v", "second="+b.hex(), "-v", "third="+c.hex(), "-f", reader.FILTER],
                                     input=words, capture_output=True, check=True)
                facts = reader.parse(res.returncode, res.stdout, res.stderr)
                self.assertEqual(tuple(facts[k] for k in keys), expected)
                self.assertEqual(facts["size"], len(payload))

    def test_bracket_and_invalid_counts(self):
        script = reader.shell("3"*32, "0"*64)
        for frame in reader.frames("3"*32).values():
            self.assertEqual(len(frame), 80)
            self.assertEqual(script.count(frame.hex()), 1)
        self.assertEqual(script.count("same_boot || exit 4"), 2)
        self.assertNotIn("y2q_pid1_v1=", script)
        for response in [b"239,1,1,1,1,1,1", b"400,1,1,1,1,1,0",
                         b"400,2,2,0,2,1,0", b"2097137,0,0,0,0,0,0",
                         b"400,1,1,1,1,0,1", b"000,0,0,0,0,0,0"]:
            with self.assertRaises(ValueError):
                reader.parse(0, b"y2q_basic_v1="+response+b"\n", b"")
        self.assertEqual(reader.parse(0,b"y2q_log_missing\n",b""), {"state":"missing"})
        with self.assertRaises(ValueError):
            reader.parse(1,b"y2q_log_missing\n",b"")

"""The two retained PID1 stages are byte-specific and ordered independently of USB."""
from pathlib import Path
import subprocess
import sys
import unittest

SOURCE = Path(__file__).resolve().parents[1]/"workspace/public/src/mainline/s20plus_y2q_h0"
sys.path.insert(0, str(SOURCE))
import pid1_stage_reader as reader


class ReturnScan(unittest.TestCase):
    def test_reducer_and_parser(self):
        a, b = reader.frames("a"*32).values()
        other = b"".join(reader.frames("f"*32).values())
        for payload, counts in [(a+b, (1,1,1)), ((a+b)*4,(4,4,4)),
                                (a*4+b"gap"+b*4,(4,4,0)), (b+a,(1,1,0)),
                                (b"!"*17+a+b,(1,1,1)), (other,(0,0,0))]:
            with self.subTest(counts=counts):
                words = b"\n".join(payload[i:i+16].hex(" ").encode() for i in range(0,len(payload),16))+b"\n"
                run = subprocess.run(["awk","-v",f"expected={len(payload)}","-v","first="+a.hex(),
                                      "-v","second="+b.hex(),"-f",reader.FILTER],input=words,capture_output=True,check=True)
                result = reader.parse(run.returncode,run.stdout,run.stderr)
                self.assertEqual(tuple(result[k] for k in ("exec_attempt_count","el0_getpid_count",
                                                           "adjacent_pair_count")),counts)
                self.assertEqual(result['state'],'complete' if any(counts) else 'no_record')

    def test_exact_bracket_and_failure_taxonomy(self):
        frames = reader.frames("a"*32)
        self.assertEqual(tuple(frames), reader.STAGES)
        script = reader.shell("a"*32, "b"*64)
        for value in frames.values():
            self.assertEqual(len(value),128)
            self.assertEqual(script.count(value.hex()),1)
        self.assertNotIn("y2q_log_v1=",script)
        self.assertIn("same_boot || exit 4\n", script)
        for rc,out,err in [(0,b"y2q_pid1_v1=255,1,1,1\n",b""),
                           (0,b"y2q_pid1_v1=2097137,0,0,0\n",b""),
                           (0,b"y2q_pid1_v1=1000,1,1,2\n",b""),
                           (0,b"y2q_log_v1=1024,1,1,1\n",b""),
                           (1,b"y2q_pid1_v1=256,1,1,1\n",b"")]:
            with self.assertRaises(ValueError):
                reader.parse(rc,out,err)
        self.assertEqual(reader.parse(0,b"y2q_log_missing\n",b""), {'state':'missing'})

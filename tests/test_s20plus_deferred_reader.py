"""CPU-only fixture checks for the y2q R4 shell and its public verdict fields."""
import base64
import hashlib
from pathlib import Path
import struct
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "workspace/public/src/mainline/s20plus_y2q_h0"))
import deferred_reader as reader


def sample(seq, current, returned, phase, rc=-517):
    raw = struct.pack("<5I", seq, current, returned, (phase << 21) | (7 << 16) | (rc & 65535), 42)
    return base64.urlsafe_b64encode(raw).rstrip(b"=")


def parse(epoch, run, flags, pid=b"-", worker=b"-"):
    line = f"R4,240,{epoch},{run},{flags},".encode() + pid + b"," + worker + b"\n"
    return reader.parse(0, line, b"")


class DeferredEvidence(unittest.TestCase):
    def test_worker_before_and_after_are_separate_from_pid_flush_and_probe_success(self):
        pid = sample(328, 159, 159, (1 << 3) | (1 << 9))
        worker = sample(127, 9, 3, 1)
        result = reader.describe(parse(1, 0, 0, pid, worker), True)
        self.assertEqual(result["worker_sample"]["operation"], "enter")
        self.assertEqual(result["worker_sample"]["command_db_rc"], -517)
        self.assertTrue(result["first_flush_return_observed"] and result["el0_getpid_entry_observed"])
        self.assertEqual(result["cohort"], "shared_epoch")
        self.assertEqual(result["last_candidate_attempt"], "unknown")
        fallback = reader.describe(parse(0, 1, 4, pid, sample(128, 9, 9, 2)), True)
        self.assertEqual(fallback["cohort"], "individual_run_samples")
        self.assertEqual(fallback["worker_sample"]["operation"], "return")
        self.assertIsNone(reader.describe(parse(1, 0, 0, pid, worker), False)["worker_sample"])

    def test_bad_inputs_cannot_produce_progress(self):
        for line in (b"R4,240,0,0,128,-,-\n", b"C1,0,0,0,-\n", b"R4,180,2,0,0,-,-\n",
                     b"R4,240,1,0,8,-,-\n", b"R4,240,1,0,68,-,-\n", b"R4,40,0,0,32,-,-\n"):
            result = reader.describe(reader.parse(0, line, b""), True)
            self.assertIsNone(result["worker_sample"])
            self.assertIsNone(result["pid_sample"])
        malformed = [(1, 0, 0, sample(329, 1, 1, 1), b"-"),
                     (1, 0, 0, b"-", sample(129, 1, 1, 2)),
                     (1, 0, 0, b"-", sample(2, 1, 3, 2)),
                     (2, 0, 0, sample(1, 1, 0, 0), b"-"),
                     (1, 0, 8, b"-", sample(1, 1, 0, 1)),
                     (1, 0, 68, sample(1, 1, 0, 8), b"-")]
        for v in malformed:
            with self.subTest(args=v), self.assertRaises(ValueError):
                parse(*v)
        for rc, err in ((4, b""), (0, b"late failure")):
            with self.assertRaises(ValueError):
                reader.parse(rc, b"R4,240,0,0,0,-,-\n", err)

    def test_actual_filter_suppresses_sample_in_a_foreign_cohort(self):
        binary = ROOT / "workspace/private/analysis/s20plus-y2q-fdt-d0-20261123/busybox-host"
        if not binary.is_file():
            self.skipTest("requires the retained BusyBox")
        nonce = "73" * 16
        key = bytes.fromhex(nonce)
        anchor = reader.frames(nonce)["run_anchor"]
        instance = hashlib.blake2s(anchor[24:40], key=key, digest_size=16).digest()
        record = b"HLP2" + struct.pack("<5I", 1, 1, 0, 8 << 21, 12)
        slot = record + hashlib.blake2s(record, key=instance, digest_size=16).digest()
        window = anchor + slot + bytes(120)
        other = reader.frames("4a" * 16)["run_anchor"] + bytes(160)
        for stream, state in [(window, "run_window"), (other + window, "mixed_format"),
                              (window + other, "mixed_format")]:
            raw = subprocess.check_output(["od", "-An", "-v", "-tx1"], input=stream)
            result = subprocess.run([binary, "awk", "-v", "key=" + nonce, "-v",
                                     "legacy=" + reader.legacy.frames(nonce)["basic_enter"].hex(),
                                     "-v", f"expected={len(stream)}", "-f", reader.FILTER],
                                    input=raw, capture_output=True)
            parsed = reader.parse(result.returncode, result.stdout, result.stderr)
            self.assertEqual(parsed["state"], state)
            self.assertEqual(bool(parsed["pid_sample"]), state == "run_window")

    def test_real_shell_binds_boot_and_frame(self):
        nonce = "13" * 16
        frame = reader.frames(nonce)["run_anchor"]
        self.assertEqual(len(frame), 80)
        self.assertEqual(frame[64:], hashlib.blake2s(frame[:64], key=bytes.fromhex(nonce), digest_size=16).digest())
        shell = reader.shell(nonce, "b" * 64)
        self.assertEqual(shell.count("same_boot || exit 4"), 2)
        self.assertIn("set -o pipefail", shell)
        self.assertIn("-v key=" + nonce, shell)


if __name__ == "__main__":
    unittest.main()

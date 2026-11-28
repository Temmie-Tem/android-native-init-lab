"""Exercise the exact ARM64 GPIO filter and the attended owner's normal bindings."""
import json
from pathlib import Path
import struct
import subprocess
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "workspace/public/src/mainline/s20plus_y2q_h0"
SCRIPTS = ROOT / "workspace/public/src/scripts/revalidation"
sys.path[:0] = [str(SRC), str(SCRIPTS)]
import gpio_return_reader as reader

KEY = bytes(range(16))
ANCHOR = reader.frames(KEY.hex())["fixed_anchor"]
INSTANCE = reader.offline.digest(ANCHOR[24:40], KEY)
BUSYBOX = ROOT / "workspace/private/analysis/s20plus-y2q-fdt-d0-20261123/busybox"


def sample(fields):
    slots = []
    for i, (flags, first, worker) in enumerate(fields):
        mask = 1 << reader.offline.RETURN
        slot = (b"TLP2" if i < 2 else b"TLW2") + struct.pack(
            "<IIIIhh", 1 + i % 2, mask if first is not None else 0, mask if worker is not None else 0,
            flags, first or 0, worker or 0)
        slots.append(slot + reader.offline.digest(slot, INSTANCE))
    return ANCHOR + b"".join(slots).ljust(160, bytes(1))


def scan(data):
    od = subprocess.check_output(["od", "-An", "-v", "-tx1"], input=data)
    cmd = ["qemu-aarch64", BUSYBOX, "awk", "-v", "key=" + KEY.hex(), "-v", f"expected={len(data)}",
           reader.program()]
    result = subprocess.run(cmd, input=od, capture_output=True, timeout=120)
    return reader.parse(result.returncode, result.stdout, result.stderr)


class GPIOTrial(unittest.TestCase):
    def test_slot_local_paths(self):
        record = scan(sample([(27, None, None), (160, None, 0), (4, -22, -517), (67, None, None)]))
        self.assertEqual(record["initial_callback_rc"], [-22])
        self.assertEqual(record["worker_callback_rc"], [-517, 0])
        self.assertFalse(any(record[k] for k in ("wait_completed", "flush_returned_true", "flush_returned_false")))
        both = scan(sample([(187, None, -517), (71, None, 0)]))
        self.assertTrue(all(both[k] for k in ("wait_completed", "flush_returned_true", "flush_returned_false")))
        self.assertEqual(scan(sample([(75, None, None)]))["state"], "invalid_snapshot")

    def test_bounded_distinct_results(self):
        chunks = [sample([(0, -4*i-j, 4*i+j) for j in range(4)]) for i in range(256)]
        result = scan(b"".join(chunks))
        self.assertEqual(result["initial_callback_rc"], list(range(-1023, 1)))
        self.assertEqual(result["worker_callback_rc"], list(range(1024)))
        self.assertEqual(scan(sample([]) * 257)["state"], "invalid_snapshot")

    def test_invalid_and_torn(self):
        data = sample([(187, None, 0)])
        torn = bytearray(data)
        torn[104] ^= 1
        self.assertEqual(scan(torn)["ignored"], 1)
        for invalid in (data + b"TLP2", data[:-1], data + reader.frames("ff"*16)["fixed_anchor"] + bytes(160)):
            self.assertEqual(scan(invalid)["state"], "invalid_snapshot")
        for line in (b"GP2,240,1,1,0,0,8192,0,0,0,0,,\n", b"GP2,240,1,0,0,0,0,187,1,1,0,,\n",
                     b"GP2,240,1,1,0,0,0,255,1,1,1,,\n", b"GP2,240,1,1,0,0,0,59,0,0,0,,\n"):
            with self.assertRaises(ValueError):
                reader.parse(0, line, b"")

    def test_owner(self):
        program = """
import s20plus_g986n_tlmm_gpio_f1 as m
m.bind()
assert m.stage._configure_runtime.__code__.co_filename == str(m.SCRIPT)
assert m.owner.ACTIVATION == m.RUN_ROOT/'activation.json'
assert m.stage.reader.FILTER == m.FILTER and m.stage.derive is m.derive
assert m.stage.capture_options('mainline-return-scan')['stdout_maximum'] == m.stage.reader.MAX_STDOUT
assert m.base.execute is m.prior.prior.cstage.execute and m.base.restore is m.prior.prior.cstage.restore
assert m.owner.terminal_verdict is m.verdict and m.base.review is m.review
assert m.pair()['candidate']['ap']['sha256'] == m.CANDIDATE
m.parent.observer().witness()
"""
        subprocess.run([sys.executable, "-B", "-c", program], cwd=SCRIPTS, check=True)

    def test_terminal_gap(self):
        import s20plus_g986n_tlmm_gpio_f1 as m
        with m.stage.bound_run(Path("/fixture")), patch.object(m, "proof") as proof:
            m.bind()
            gap = dict(initial=[], worker=[], flush=[], usb_pid1="not_seen", initial_callback_rc=[],
                       worker_callback_rc=[], wait_completed=False, flush_returned_true=False, flush_returned_false=False)
            for fields, label in ((dict(usb_pid1="pid1_exact"), "ACM_PID1"),
                                  (dict(flush=["opened"], flush_returned_false=True), "FLUSH_FALSE"),
                                  (dict(flush=["opened"]), "KERNEL_PROGRESS"),
                                  (dict(worker=["gpio_add"]), "GPIO_REGISTRATION"),
                                  (dict(worker=["callback_return"], worker_callback_rc=[0]), "TLMM_CALLBACK_RETURN")):
                proof.return_value = dict(gap, **fields)
                self.assertEqual(m.verdict("odin_transfer_completed", "NO_PROOF", True),
                                 (f"OBSERVED_{label}_ORIGINAL_RETURNED", True))
            proof.return_value = gap
            self.assertFalse(m.verdict("odin_transfer_completed", "NO_PROOF", True)[1])
            with self.assertRaises(m.owner.Stop):
                m.verdict("odin_transfer_completed", "NO_PROOF", False)


if __name__ == "__main__":
    unittest.main()

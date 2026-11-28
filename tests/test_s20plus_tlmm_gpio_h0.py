"""The GPIO return reader must keep independent slots and code paths separate."""
import struct
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] /
                       "workspace/public/src/mainline/s20plus_y2q_h0"))
import tlmm_gpio_h0 as reader

NONCE = bytes(range(16)).hex()
ANCHOR = reader.frames(NONCE)["fixed_anchor"]
INSTANCE = reader.digest(ANCHOR[24:40], bytes.fromhex(NONCE))


def slot(events, *, worker=False, rc=None):
    flags = sum(1 << reader.FLUSH.index(name) for name in events)
    callback = (1 << reader.RETURN) if rc is not None else 0
    data = (b"TLW2" if worker else b"TLP2") + struct.pack("<IIIIhh", 1, 0, callback,
                                                           flags, 0, rc or 0)
    return data + reader.digest(data, INSTANCE)


class GPIOReader(unittest.TestCase):
    def test_scattered_stages_do_not_complete_wait(self):
        path = ["opened", "call", "barrier", "before_wait"]
        left = slot(path)
        right = slot(["after_wait", "returned_true"], worker=True, rc=-517)
        rows = reader.decode(ANCHOR + left + bytes(40) + right + bytes(40), NONCE)
        self.assertEqual(reader.outcomes(rows), dict(worker_callback_rc=[-517], wait_completed=False,
                                                     flush_returned_true=False))
        complete = slot(path + ["after_wait", "returned_true"])
        result = reader.outcomes(reader.decode(ANCHOR + complete + bytes(120), NONCE))
        self.assertEqual(result, dict(worker_callback_rc=[], wait_completed=True, flush_returned_true=True))

    def test_incompatible_branches(self):
        for flags in (("barrier", "no_barrier"), ("returned_true", "returned_false"),
                      ("after_wait", "returned_false")):
            with self.subTest(flags=flags), self.assertRaises(ValueError):
                reader.decode(ANCHOR + slot(flags) + bytes(120), NONCE)

    def test_stale_torn_and_foreign_slots(self):
        frame = slot(["opened"])
        window = ANCHOR + frame + bytes(120)
        epoch = b"TLEPOCH2" + bytes.fromhex(NONCE) + b"x" * 16 + bytes(24)
        epoch += reader.digest(epoch, bytes.fromhex(NONCE))
        self.assertEqual(reader.decode(epoch + window[80:], NONCE), [])
        torn = bytearray(window)
        torn[104] ^= 1
        self.assertEqual(reader.decode(torn, NONCE), [])
        with self.assertRaises(ValueError):
            reader.decode(window, "ff" * 16)


if __name__ == "__main__":
    unittest.main()

import hashlib
import itertools
from pathlib import Path
import struct
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "workspace/public/src/mainline/s20plus_y2q_h0"))
import deferred_presence_h0 as h

NONCE = "31" * 16
KEY = bytes.fromhex(NONCE)


def frame(body, key):
    return body + hashlib.blake2s(body, key=key, digest_size=16).digest()


def window(slots=(), epoch=None):
    tag = epoch if epoch is not None else b"RUN-LEVEL-ONLY!!"
    magic = b"H0EPOCH3" if epoch is not None else b"H0UNATR3"
    head = frame(magic + KEY + tag + bytes(24), KEY)
    result = bytearray(head + bytes(160))
    instance = hashlib.blake2s(tag, key=KEY, digest_size=16).digest()
    for slot, seq, cur, ret, phase in slots:
        body = (b"HLP2" if slot < 2 else b"HLW2") + struct.pack("<5I",seq,cur,ret,phase << 21,1)
        offset = 80 + 40 * slot
        result[offset:offset+40] = frame(body, instance)
    return bytes(result)


class Presence(unittest.TestCase):
    def test_reordered_and_repeated_independent_facts(self):
        # A higher sequence in the other worker slot must not hide the entry.
        worker = window([(2,1,17,0,1),(3,2,17,17,2)])
        pid = window([(1,2,159,159,8)], epoch=b"a"*16)
        empty = window()
        for parts in itertools.permutations((worker,pid,empty)):
            result = h.presence(b"".join(parts * 3), NONCE)
            self.assertEqual(result, dict(valid_windows=9,unauthenticated_slots=0,
                before_bus_probe_device="observed",before_call_device_ids=["00000011"],return_device_ids=["00000011"],
                first_flush_return="observed"))

    def test_independent_and_unproved(self):
        for slots,entry,flush in [([],False,False), ([(2,1,5,0,1)],True,False),
                                  ([(0,1,1,0,8)],False,True), ([(2,1,5,5,2)],False,False)]:
            r=h.presence(window(slots)*9,NONCE)
            self.assertEqual((r["before_bus_probe_device"]=="observed",r["first_flush_return"]=="observed"),(entry,flush))

    def test_stale_slots_wrong_lane_and_invalid_inputs(self):
        epoch=window(epoch=b"x"*16)
        valid=window([(2,1,7,0,1)])
        stale=h.presence(epoch[:160]+valid[160:],NONCE)
        self.assertEqual((stale["before_bus_probe_device"],stale["unauthenticated_slots"]),("unproved",1))
        swapped=h.presence(valid[:80]+valid[160:200]+bytes(120),NONCE)
        self.assertEqual(swapped["before_call_device_ids"],[])
        for bad in [valid+epoch[:-1],valid+b"Y2QANCH1",valid+bytes(3)+h.r4.frames("51"*16)["run_anchor"]+bytes(160),
                    window([(2,2,3,0,1)]),window([(2,129,3,0,1)]),valid[:80]+valid,window()*257]:
            with self.assertRaises(ValueError):
                h.presence(bad,NONCE)

if __name__=="__main__":
    unittest.main()

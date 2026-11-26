"""Exercise the actual BusyBox reducer for signed progress, torn writes and independent boots."""
import base64
import hashlib
from pathlib import Path
import subprocess
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"workspace/public/src/mainline/s20plus_y2q_h0"))
import consolidated_reader as reader

BUSYBOX=ROOT/"workspace/private/analysis/s20plus-y2q-fdt-d0-20261123/busybox-host"
NONCE="19"*16


def record(bits, nonce=NONCE):
    head=reader.DOMAIN+bytes.fromhex(nonce)+bits.to_bytes(40,"little")
    return head+hashlib.blake2s(head,digest_size=16).digest()


class ProgressReader(unittest.TestCase):
    def scan(self,payload):
        args=[str(BUSYBOX),"awk","-v",f"expected={len(payload)}","-v",
              "anchor="+reader.frames(NONCE)["basic_enter"].hex(),"-v","tag="+reader.DOMAIN.hex()+NONCE,
              "-f",reader.FILTER]
        raw=subprocess.check_output(["od","-An","-v","-tx1"],input=payload)
        result=subprocess.run(args,input=raw,capture_output=True)
        return reader.parse(result.returncode,result.stdout,result.stderr)

    def test_full_and_disjoint_records(self):
        anchor=reader.frames(NONCE)["basic_enter"]
        full=(1<<316)-1
        facts=self.scan(b"!"*17+anchor+record(full)+record(1<<310)+anchor)
        self.assertEqual((facts["anchor_count"],facts["record_count"]),(2,2))
        desc=reader.describe(facts["bitmap"])
        self.assertEqual((desc["entry_count"],desc["return_count"],desc["highest_return"]),(153,153,152))
        self.assertIn("el0_getpid",desc["milestones"])
        # Equal weight: choose one real record; their union was never observed.
        mixed=self.scan(record(1)+record(2))
        self.assertEqual(mixed["bitmap"],(2).to_bytes(40,"little").hex())

    def test_no_prefix_wrap_or_torn_acceptance(self):
        good=record(3); damaged=bytearray(good);damaged[28]^=1
        payload=good[20:]+bytes(damaged)+record(3,"f0"*16)+good[:20]
        self.assertEqual(self.scan(payload)["state"],"no_record")
        self.assertEqual(self.scan(reader.frames(NONCE)["basic_enter"])["record_count"],0)
        # Digest-size=16 is a distinct BLAKE2s parameter.
        self.assertEqual(self.scan(good[:64]+hashlib.blake2s(good[:64]).digest()[:16])["state"],"no_record")

    def test_fixed_limits_and_bracket(self):
        self.assertEqual(reader.shell(NONCE,"a"*64).count("same_boot || exit 4"),2)
        for out in (b"C1,0,1,0,-\n",b"C1,80,0,1,-\n",b"C1,2097137,0,0,-\n",
                    b"C1,80,0,1,"+base64.urlsafe_b64encode(bytes(40)).rstrip(b"=")+b"\n"):
            with self.assertRaises(ValueError):
                reader.parse(0,out,b"")
        with self.assertRaises(ValueError):
            self.scan(record(1<<317))

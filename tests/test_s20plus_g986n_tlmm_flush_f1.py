"""Host-only TLMM recovery reducer and owner controls."""
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT/"workspace/public/src/mainline/s20plus_y2q_h0"
sys.path.insert(0,str(SRC))
sys.path.insert(0,str(ROOT/"workspace/public/src/scripts/revalidation"))
import tlmm_return_reader as reader

EXP = ROOT/"workspace/private/analysis/s20plus-y2q-tlmm-flush-h0-20261128"


class Recovery(unittest.TestCase):
    def scan(self,data):
        import json
        nonce=json.loads((EXP/"candidate/stage.json").read_bytes())["nonce"]
        binary=EXP.parent/"s20plus-y2q-fdt-d0-20261123/busybox"
        args=["qemu-aarch64",binary,"awk","-v","key="+nonce,"-v",f"expected={len(data)}","-f",reader.FILTER]
        proc=subprocess.run(args,input=subprocess.check_output(["od","-An","-v","-tx1"],input=data),capture_output=True)
        return reader.parse(proc.returncode,proc.stdout,proc.stderr)

    @unittest.skipUnless((EXP/"verified-ready/after.bin").exists(),"requires historical QEMU fixtures")
    def test_ram_windows(self):
        get=lambda d,n:(EXP/d/(n+".bin")).read_bytes()
        ready=get("verified-ready","after")
        absent=get("verified-missing","after")
        idle=get("final-idle","after")
        cut=get("verified-ready","before-wait")
        for d,initial,completed,rc in [(ready,"supplier_pdc",True,"zero"),(absent,"wake_missing",True,"defer"),
                                       (idle,"supplier_pdc",False,None),(cut,"supplier_pdc",False,None)]:
            facts=self.scan(d)
            self.assertIn(initial,facts["initial"])
            self.assertEqual(facts["completed_barrier_wait"],completed)
            if rc:
                self.assertIn(rc,facts["worker_rc_classes"])
        self.assertIn("returned_false",self.scan(idle)["flush"])
        self.assertNotIn("after_wait",self.scan(cut)["flush"])
        joined=self.scan(bytes(4089)+ready+absent+idle)
        self.assertEqual(joined["windows"],3)
        self.assertEqual(set(joined["worker_rc_classes"]),{"defer","zero"})
        self.assertTrue(joined["completed_barrier_wait"])
        for bad in (ready+idle[:120],ready[:80]+ready,b"TLP1"+bytes(1024)):
            self.assertEqual(self.scan(bad)["state"],"invalid_snapshot")
        self.assertEqual(self.scan(bytes(2048))["state"],"no_record")
        invalid=bytearray(ready)
        for i in range(4):
            invalid[80+40*i+24]^=1
        self.assertEqual(self.scan(invalid)["slots"],0)

    def test_union_never_completes_a_wait(self):
        import json
        import struct
        nonce = json.loads((EXP/"candidate/stage.json").read_bytes())["nonce"]
        key = bytes.fromhex(nonce)
        anchor = reader.frames(nonce)["fixed_anchor"]
        instance = reader.offline.digest(anchor[24:40], key)
        def sample(flags):
            body = b"TLP1" + struct.pack("<5I", 1, 0, 0, flags, 0)
            return anchor + body + reader.offline.digest(body, instance) + bytes(120)
        split = self.scan(sample(27) + sample(160))
        self.assertIn("after_wait",split["flush"])
        self.assertIn("returned_true",split["flush"])
        self.assertFalse(split["completed_barrier_wait"])
        self.assertTrue(self.scan(sample(187))["completed_barrier_wait"])
        for contradictory in (12,192):
            self.assertEqual(self.scan(sample(contradictory))["state"],"invalid_snapshot")

    def test_normal_owner_bindings(self):
        program = """
import s20plus_g986n_tlmm_flush_f1 as m
m.bind()
assert m.stage._configure_runtime.__code__.co_filename == str(m.SCRIPT)
assert m.owner.terminal_verdict is m.verdict and m.owner.checked_terminal is m.stage.publish
assert m.base.execute is m.prior.cstage.execute and m.base.restore is m.prior.cstage.restore
assert m.base.prepare is m.prior.cstage.prepare and m.base.review is m.review
assert m.owner.ACTIVATION == m.RUN_ROOT/'activation.json'
assert m.stage.reader.FILTER == m.FILTER and m.stage.reader.STAGES == m.STAGES
assert m.pair()['candidate']['ap']['sha256'] == m.CANDIDATE
m.parent.observer().witness()
"""
        subprocess.run([sys.executable,"-B","-c",program],cwd=ROOT/"workspace/public/src/scripts/revalidation",check=True)

    def test_parser(self):
        for raw in (b"TL1,240,1,0,0,1,0,0,0,0,0\n",b"TL1,240,1,4,0,0,0,0,0,0,1\n",
                    b"TL1,240,1,2,0,8192,0,0,0,0,0\n"):
            with self.assertRaises(ValueError):
                reader.parse(0,raw,b"")

    def test_owner_terminal(self):
        import s20plus_g986n_tlmm_flush_f1 as m
        with m.stage.bound_run(Path("/fixture")),patch.object(m,"proof") as proof:
            proof.return_value=dict(initial=["supplier_pdc"], worker=[], flush=["barrier","before_wait"],
                                    completed_barrier_wait=False,usb_pid1="not_seen")
            verdict,ok=m.verdict("odin_transfer_completed","NO_PROOF",True)
            self.assertTrue(ok)
            self.assertIn("INITIAL_PDC_DEFER",verdict)
            self.assertNotIn("WAIT_RETURNED",verdict)
            with self.assertRaises(m.owner.Stop):
                m.verdict("odin_transfer_completed","NO_PROOF",False)


if __name__=="__main__":
    unittest.main()

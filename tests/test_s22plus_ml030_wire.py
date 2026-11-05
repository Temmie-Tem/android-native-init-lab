"""Check the result-bound return, partial hardware outcomes and late witness."""
import errno
import hashlib
import subprocess
import tempfile
from pathlib import Path
import struct
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"workspace/public/src/mainline/s22plus_ufs_link_h0"))
import link_wire as w

KEY, ID, FIRST, SECOND, BOOT = (bytes([i])*n for i,n in ((1,32),(2,32),(3,32),(4,32),(5,16)))
T0,T1=2000,303100
WIT = w.frame(b"G030WIT1",17,KEY,ID,FIRST,SECOND,BOOT,T0,T1)
GOOD = [0,6,0x40000000,1,6,1,8,0x400,0,9,1,3,7,7,7,0,0,1,1]


def record(values=None, *, load=0, read=0, raw_bytes=b""):
    line=raw_bytes if values is None else (" ".join(map(str,values))+"\n").encode()
    raw=b"G030RES1"+WIT[8:w.HEADER.size]+struct.pack("<III",load,read,len(line))+line.ljust(256,b"\0")
    return raw+w.tag(KEY,ID,20,raw)


class LinkWireTest(unittest.TestCase):
    def test_same_boot_and_gap(self):
        self.assertEqual(w.witness(WIT,KEY,ID,FIRST,SECOND,BOOT,T0),T1)
        for boot, second, t0 in ((b"x"*16,SECOND,T0),(BOOT,FIRST,T0),(BOOT,SECOND,T0+2000)):
            with self.subTest(t0=t0),self.assertRaises(ValueError):
                w.witness(WIT,KEY,ID,FIRST,second,boot,t0)
        with self.assertRaises(ValueError):
            w.frame(b"G030WIT1",17,KEY,ID,FIRST,SECOND,BOOT,T0,T0+w.GAP_MS-1)

    def test_link_and_return_identity(self):
        raw=record(GOOD)
        result=w.result(raw,WIT,KEY,ID)
        self.assertEqual(result["control_nonce"],hashlib.sha256(raw).digest())
        self.assertTrue(result["normal_return"])
        for index,value in ((3,0),(4,5),(5,0),(6,9),(7,0x40),(8,2),(9,8),(10,0),
                            (11,0),(12,1),(13,3),(14,3),(15,1),(16,-5),(17,0),(18,0)):
            changed=list(GOOD);changed[index]=value
            with self.subTest(index=index),self.assertRaises(ValueError):
                w.result(record(changed),WIT,KEY,ID)
        for bad in (raw[:-1],raw[:145]+bytes([raw[145]^1])+raw[146:]):
            with self.assertRaises(ValueError):
                w.result(bad,WIT,KEY,ID)

    def test_partial_report_preserves_errno_and_length(self):
        for data, error in ((b"0 6",errno.EIO),(b"x"*256,errno.EOVERFLOW)):
            proof=w.result(record(read=error,raw_bytes=data),WIT,KEY,ID)
            self.assertEqual(proof["report_bytes"],len(data))
            self.assertEqual(proof["read_errno"],error)
            self.assertFalse(proof["normal_return"])

    def test_actual_c_reader_preserves_partial_bytes(self):
        source=Path(w.__file__).with_name("link-runtime.h").read_text()
        start=source.index("static int ml030_read_result(")
        end=source.index("\n}\n",start)+3
        with tempfile.TemporaryDirectory() as directory:
            dest=Path(directory)
            (dest/"reader.inc").write_text(source[start:end])
            exe=dest/"reader"
            subprocess.run(["cc","-Wall","-Wextra","-Werror","-I",dest,
                            Path(__file__).with_name("s22plus_ml030_report_fixture.c"),"-o",exe],check=True)
            subprocess.run([exe],check=True,timeout=2)

    def test_no_normal_return_on_failure(self):
        uncertain=[-110,2,0x40000000,0,0,0,0,0,0,0,0,2,3,3,1,0,-110,1,1]
        for raw in (record(uncertain),record(load=19),record(read=5)):
            result=w.result(raw,WIT,KEY,ID)
            self.assertFalse(result["normal_return"])
            self.assertNotIn("control_nonce",result)


if __name__=="__main__":
    unittest.main()

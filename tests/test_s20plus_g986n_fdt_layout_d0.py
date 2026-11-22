"""Run the fixed layout filter on synthetic inputs and the D0 owner on fake ADB."""
import contextlib
import importlib.util
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "workspace/public/src/scripts/revalidation"
SPEC = importlib.util.spec_from_file_location("s20_layout", SCRIPTS / "s20plus_g986n_fdt_layout_d0.py")
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)
BOOT = "12345678-1234-1234-1234-123456789abc"
LAYOUT = b"layout_v1=4096,1,1,0,1,1,1,0,0,0,0,1,1\n"
ROW = b"S20TEST device usb:3-1 product:y2qksx model:SM_G986N device:y2q transport_id:1\n"
OTHER = b"S22TEST device usb:3-2 product:g0qksx model:SM_S906N device:g0q transport_id:2\n"
LIST = b"List of devices attached\n" + ROW + OTHER
DTS = """/dts-v1/;
MEMRESERVE
/ {
 #address-cells = <2>; #size-cells = <2>;
 compatible = "test,board";
 chosen { linux,initrd-start = <0 0x8000>; linux,initrd-end = <0 0x8100>; };
 memory@0 { device_type = "memory"; reg = <0 0 0 0x10000>; };
 reserved-memory {
  #address-cells = <2>; #size-cells = <2>; ranges;
  fixed@9000 { reg = <0 0x9000 0 0x100>; };
  pool { size = <0 0x100>; };
 };
};"""


def public(boot=BOOT):
    return ("model=SM-G986N\ndevice=y2q\nproduct_name=y2qksx\nincremental=G986NKSS8IYC2\n"
            "boot_completed=1\nbootanim=stopped\nselinux=Enforcing\nboot_id=" + boot + "\n").encode()


def tree(text):
    return subprocess.run(["dtc","-q","-I","dts","-O","dtb"],input=text.encode(),check=True,stdout=subprocess.PIPE).stdout


def reduce_blob(blob):
    hexdump = subprocess.run(["od","-An","-v","-tx1"],input=blob,check=True,stdout=subprocess.PIPE).stdout
    return subprocess.run(["awk","-v","src=8192","-v","se=12288","-v","dst=16384","-v","de=20480",
                           "-f",M.AWK],input=hexdump,capture_output=True,timeout=15)


@unittest.skipUnless(shutil.which("dtc") and shutil.which("awk") and shutil.which("od"), "host DT tools required")
class FilterTest(unittest.TestCase):
    def test_positive_and_private_fields(self):
        data=DTS.replace("MEMRESERVE","").replace('chosen {','chosen { bootargs = "secret-fixture-text";')
        result=reduce_blob(tree(data))
        self.assertEqual((result.returncode,result.stderr),(0,b""))
        facts=M.parse_layout(result.stdout)
        self.assertTrue(facts["destination_one_bank"] and facts["source_one_bank"])
        self.assertTrue(facts["initrd_one_bank"])
        self.assertEqual((facts["fixed_ranges"],facts["dynamic_pools"]),(1,1))
        self.assertNotIn(b"secret",result.stdout)

    def test_boundaries(self):
        cases=[
            ("header",DTS.replace("MEMRESERVE","/memreserve/ 0x4fff 1;"),"destination_fixed_overlap",True),
            ("adjacent",DTS.replace("MEMRESERVE","/memreserve/ 0x5000 1;"),"destination_fixed_overlap",False),
            ("disabled",DTS.replace("MEMRESERVE","").replace('reg = <0 0x9000','status="disabled"; reg = <0 0x4000'),"destination_fixed_overlap",True),
            ("split",DTS.replace("MEMRESERVE","").replace("reg = <0 0 0 0x10000>","reg = <0 0 0 0x4800>, <0 0x4800 0 0xb800>"),"destination_one_bank",False),
            ("initrd",DTS.replace("MEMRESERVE","").replace("0x8000","0x4fff"),"destination_initrd_overlap",True),
            ("absent-bank",DTS.replace("MEMRESERVE","").replace('device_type = "memory";','status="disabled"; device_type="memory";'),"initrd_one_bank",False),
        ]
        for label,source,key,value in cases:
            with self.subTest(label=label):
                self.assertEqual(M.parse_layout(reduce_blob(tree(source)).stdout)[key],value)

    def test_malformed_or_unsupported(self):
        src=DTS.replace("MEMRESERVE",""); blob=tree(src)
        cases=[blob[:-1],blob+b"x",blob[:16]+bytes(4)+blob[20:],
               tree(src.replace('chosen {','chosen { linux,usable-memory-range = <0 0 0 0x100>;')),
               tree(src.replace('device_type = "memory";','linux,usable-memory=<0 0 0 0x100>; device_type = "memory";'))]
        for b in cases:
            with self.subTest(size=len(b)):
                r=reduce_blob(b)
                self.assertNotEqual(r.returncode,0)
                self.assertEqual(r.stdout,b"")


class OwnerTest(unittest.TestCase):
    def test_capture_bound_and_stderr(self):
        reason,rc,out,err=M.root_capture([sys.executable,"-c","import sys;sys.stderr.write('x'*9)"],1,8)
        self.assertEqual((reason,out,err),("overflow",b"",b"x"*8))
        reason,rc,out,err=M.root_capture([sys.executable,"-c","import time;print('a',flush=True);time.sleep(2)"],.25,8)
        self.assertEqual((reason,out),("timeout",b"a\n"))

    def exercise(self, inv=LIST, last=LIST, before=None, after=None, root=LAYOUT, error=False):
        responses=[inv,b"usb:3-1\n",public() if before is None else before,public() if after is None else after,last]
        started=[];counts=[]
        def read(argv,timeout,maximum):
            started.append(argv)
            return 0,responses.pop(0),b""
        def root_read(argv,timeout,maximum):
            started.append(argv)
            self.assertEqual(argv[1:6],["-s","S20TEST","shell","su","-c"])
            self.assertEqual(shlex.split(argv[-1]),["check "+BOOT])
            return "completed",0,root,b""
        tool=dict(path=M.health.EXPECTED_ADB_PATH, device=1, inode=2, mtime_ns=3,
                  size=M.health.EXPECTED_ADB_SIZE, sha256=M.health.EXPECTED_ADB_SHA256)
        with tempfile.TemporaryDirectory() as tmp, contextlib.ExitStack() as st:
            path=Path(tmp);os.chmod(path,0o700)
            st.enter_context(mock.patch.object(M,"EVIDENCE",path))
            st.enter_context(mock.patch.object(M,"admission"))
            st.enter_context(mock.patch.object(M,"root_template",return_value="check "+M.ZERO_BOOT))
            st.enter_context(mock.patch.object(M.health.base,"tool_receipt",return_value=tool))
            st.enter_context(mock.patch.object(M.health.base,"bounded_command",side_effect=read))
            st.enter_context(mock.patch.object(M,"root_capture",side_effect=root_read))
            with M.allocate() as owner:
                try:
                    result=M.collect({},owner,counts)
                except ValueError:
                    if not error: raise
                    owner.publish_json("failure.json",{"counts":M.command_counts(counts)})
                except (M.health.RootHealthD0Error, M.health.base.InventoryError):
                    if not error: raise
                    owner.publish_json("failure.json",{"counts":M.command_counts(counts)})
                else:
                    self.assertFalse(error)
                    owner.publish_json("result.json",result)
                    self.assertEqual(result["selected_s20plus_commands"],4)
                    self.assertNotIn("S20TEST",json.dumps(result))
                if "root" in counts:
                    receipt=json.loads((owner.path/"root-receipt.json").read_text())
                    self.assertEqual(receipt["stdout_sha256"],M.sha(root))
            self.assertTrue(all("S22TEST" not in argv for argv in started))
        return counts

    def test_six_commands(self):
        self.assertEqual(self.exercise(),["inventory","devpath","snapshot","root","snapshot","inventory"])
        self.exercise(root=b"layout_unavailable=missing\n")

    def test_failures(self):
        self.assertEqual(self.exercise(inv=LIST+ROW,error=True),["inventory"])
        self.assertNotIn("root",self.exercise(before=public().replace(b"IYC2",b"BAD!"),error=True))
        self.assertIn("root",self.exercise(last=LIST.replace(b"usb:3-1",b"usb:3-4"),error=True))
        self.assertIn("root",self.exercise(after=public(BOOT[::-1]),error=True))
        self.assertIn("root",self.exercise(root=b"forbidden raw field\n",error=True))

    def test_inconsistent_receipts(self):
        for b in (LAYOUT+b"extra\n",LAYOUT.replace(b"4096,1",b"4096,0",1),LAYOUT.replace(b"4096",b"9999999"),
                  b"layout_unavailable=unexpected_name\n"):
            with self.assertRaises(ValueError): M.parse_layout(b)

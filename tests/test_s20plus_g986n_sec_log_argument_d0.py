"""Fixed argument classification and target/boot continuity with fake ADB."""
import contextlib
import importlib.util
import json
from pathlib import Path
import subprocess
import unittest
from unittest import mock

from test_s20plus_g986n_fdt_layout_d0 import BOOT, LIST, ROW, SCRIPTS, public

spec = importlib.util.spec_from_file_location("s20_sec_log", SCRIPTS / "s20plus_g986n_sec_log_argument_d0.py")
M = importlib.util.module_from_spec(spec)
spec.loader.exec_module(M)
TOKEN = b"sec_log=0x200000@0x9f200000"


def reduce_data(data, end):
    hexes = subprocess.check_output(["od", "-An", "-v", "-tx1"], input=data)
    return subprocess.check_output(["awk", "-v", f"terminator={end}", "-f", M.FILTER], input=hexes).decode().strip()


class SecLogD0(unittest.TestCase):
    def test_argument_sources(self):
        cases = [
            (TOKEN + b"\n", 10, "match"), (TOKEN + b"\0", 0, "match"),
            (TOKEN.replace(b"9f", b"9F") + b"\n", 10, "match"),
            (b"sec_log=2M@9f200000\n", 10, "match"),
            (b"sec_log=010000000@0x9F200000\n", 10, "match"),
            (b"sec_log=2097152@0X9F200000\n", 10, "match"),
            (b'"--" ' + TOKEN + b'\n', 10, "absent"),
            (b"sec_log=garbage\n", 10, "unsupported"),
            (b"sec_log=3M@9f200000\n", 10, "unsupported"),
            (TOKEN + b" " + TOKEN + b"\n", 10, "ambiguous"),
            (b"prefix." + TOKEN + b" -- " + TOKEN + b"\0", 0, "absent"),
            (b'v="prefix ' + TOKEN + b'"\0', 0, "absent"),
            (b'sec_log="value"\n', 10, "unsupported"),
            (b'sec-log=wrong ' + TOKEN + b'\n', 10, "unsupported"),
            (TOKEN[:-1] + b"1\n", 10, "different"),
            (TOKEN + b"\0", 10, "unsupported"), (TOKEN, 0, "unsupported"),
            (TOKEN + b"\0tail", 0, "unsupported"),
            (b" "*8192 + b"\n", 10, "unsupported"), (b" "*8191 + b"\n", 10, "absent"),
        ]
        for data, end, want in cases:
            with self.subTest(expected=want, length=len(data)):
                self.assertEqual(reduce_data(data,end),want)

    def test_collect(self):
        for label in ("success","before_target","ambiguous","changed_boot","root_exit","unexpected_output","lost_port"):
            counts=[]
            rows=iter((LIST+ROW if label=="ambiguous" else LIST,
                       LIST.replace(b"usb:3-1",b"usb:3-4") if label=="lost_port" else LIST))
            snapshots=iter((public().replace(b"IYC2",b"BAD!") if label=="before_target" else public(),
                            public(BOOT[::-1]) if label=="changed_boot" else public()))
            tool=M.health.base.tool_receipt(M.health.base.DEFAULT_ADB)
            def command(args,timeout,limit):
                self.assertNotIn("S22TEST",args)
                if args[1]=="devices":return 0,next(rows),b""
                self.assertEqual(args[1:3],["-s","S20TEST"])
                if args[3]=="get-devpath":return 0,b"usb:3-1\n",b""
                self.assertEqual(args[3:6],["exec-out","sh","-c"])
                return 0,next(snapshots),b""
            def root(args,timeout,limit):
                self.assertEqual(args[1:6],["-s","S20TEST","shell","su","-c"])
                self.assertIn(BOOT,args[-1])
                self.assertEqual((timeout,limit),(25,2048))
                return ("completed",1 if label=="root_exit" else 0,
                        b"arbitrary\n" if label=="unexpected_output" else b"match\nabsent\n",b"")
            with self.subTest(label=label), contextlib.ExitStack() as s:
                s.enter_context(mock.patch.object(M,"admit"))
                s.enter_context(mock.patch.object(M.health.base,"bounded_command",side_effect=command))
                s.enter_context(mock.patch.object(M.health.base,"tool_receipt",return_value=tool))
                s.enter_context(mock.patch.object(M.lib,"root_capture",side_effect=root))
                owner=mock.Mock()
                if label=="success":
                    result=M.collect({},owner,counts)
                    self.assertEqual(result["facts"],{"effective":"match","chosen":"absent"})
                    self.assertEqual(counts,["inventory","devpath","snapshot","root","snapshot","inventory"])
                    self.assertNotIn("S20TEST",json.dumps(result))
                else:
                    with self.assertRaises((ValueError,M.health.RootHealthD0Error,M.health.base.InventoryError)):
                        M.collect({},owner,counts)
                if label in ("before_target","ambiguous"):self.assertNotIn("root",counts)
                if "root" in counts:
                    self.assertEqual(owner.publish_json.call_args.args[0],"root-receipt.json")

    def test_disabled_or_foreign_owner(self):
        import os
        import tempfile
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(M,"PARENT",Path(tmp)):
            identity=M.subject()
            receipt=Path(tmp)/"activation.json"
            with self.assertRaises(FileNotFoundError): M.admit(identity)
            receipt.write_bytes(M.health._json_bytes(dict(identity=identity,review=dict(verdict="PASS_GO",high=0,medium=0,low=0))))
            receipt.chmod(0o400)
            with mock.patch.object(os.path,"lexists",return_value=True), self.assertRaises(ValueError):
                M.admit(identity)
            with self.assertRaises(ValueError): M.admit({})

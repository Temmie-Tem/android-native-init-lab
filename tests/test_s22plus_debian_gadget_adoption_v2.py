"""Run the fixed shell producer on explicit regular-file configfs substitutes.

This checks the producer's selected paths, ownership and failure ordering.
Stock-kernel dispatcher reproduction is separate; neither is electrical USB.
"""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'workspace/public/src/debian/s22plus_v1/device/lab-usb-adopt-g1'


class GadgetTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup);self.root=Path(t.name)
        r=self.root;self.g=r/'config/usb_gadget/g1';self.bin=r/'bin';self.bin.mkdir()
        for path in ('strings/0x409','configs/b.1/strings/0x409','functions/acm.usb0'):
            (self.g/path).mkdir(parents=True,exist_ok=True)
        (self.g/'configs/b.1/acm.usb0').symlink_to('../../functions/acm.usb0')
        for name,data in {'UDC':'','idVendor':'0x04e8','idProduct':'0x6861'}.items():
            (self.g/name).write_text(data)
        (r/'run-config').symlink_to(r/'config',target_is_directory=True)
        (r/'run').mkdir();(r/'run/usb-release').touch()
        (r/'run/hook').write_text('#!/bin/sh\nprintf "%s\\n" "$1" > "'+str(r/'park')+'"\nexit 99\n')
        (r/'run/hook').chmod(0o700)
        (r/'defaults').write_text('serial=fixture\nhost_mac=02:00:00:00:00:01\ndevice_mac=02:00:00:00:00:02\ndevice_address=192.0.2.2/30\n')
        for name,body in {
            'uname':'printf "5.10.226-android12-9-30958166-abS906NKSS7FYG8\\n"',
            'findmnt':'printf "configfs\\n"',
            'ip':'printf "%s\\n" "$*" >> "'+str(r/'ip-calls')+'"',
        }.items():
            (self.bin/name).write_text('#!/bin/sh\n'+body+'\n');(self.bin/name).chmod(0o700)
        text=SOURCE.read_text()
        for original,new in [('/sys/kernel/config',r/'config'),('/run/config',r/'run-config'),
            ('/run/s22-debian',r/'run'),('/etc/default/lab-usb',r/'defaults'),
            ('/sys/devices/platform/soc/a600000.ssusb/mode',r/'mode')]:
            self.assertIn(original,text);text=text.replace(original,str(new))
        self.script=r/'producer';self.script.write_text(text)
        self.identity=self.g.stat().st_ino

    def run_script(self):
        return subprocess.run(['/bin/sh',str(self.script),'start'],env=dict(os.environ,
            PATH=str(self.bin)+':/usr/bin:/bin'),capture_output=True,timeout=5)

    def test_same_first_object_and_configuration_rebound_once(self):
        result=self.run_script();self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(self.g.stat().st_ino,self.identity)
        self.assertTrue((self.g/'functions/acm.usb0').is_dir())
        self.assertFalse((self.g/'configs/b.1/acm.usb0').exists())
        self.assertEqual((self.g/'configs/b.1/ncm.usb0').resolve(),self.g/'functions/ncm.usb0')
        self.assertEqual((self.g/'UDC').read_text(),'a600000.dwc3')
        self.assertEqual((self.g/'idVendor').read_text(),'0x1d6b')
        self.assertEqual([p.name for p in self.g.parent.iterdir()],['g1'])
        self.assertEqual(len((self.root/'ip-calls').read_text().splitlines()),3)

    def test_bound_gadget_rejects_before_any_mutation(self):
        (self.g/'UDC').write_text('a600000.dwc3')
        self.assertEqual(self.run_script().returncode,99)
        self.assertTrue((self.g/'configs/b.1/acm.usb0').is_symlink())
        self.assertEqual((self.g/'idVendor').read_text(),'0x04e8')
        self.assertFalse((self.g/'functions/ncm.usb0').exists())

    def test_mid_transition_failure_parks_without_rebinding_or_recreation(self):
        (self.bin/'mkdir').write_text('#!/bin/sh\nexit 1\n');(self.bin/'mkdir').chmod(0o700)
        self.assertEqual(self.run_script().returncode,99)
        self.assertEqual(self.g.stat().st_ino,self.identity)
        self.assertEqual((self.g/'UDC').read_text(),'')
        self.assertFalse((self.root/'ip-calls').exists())
        self.assertEqual((self.root/'park').read_text(),'park\n')

    def test_repeated_start_is_rejected_without_second_network_action(self):
        self.assertEqual(self.run_script().returncode,0)
        original=(self.root/'ip-calls').read_bytes()
        self.assertEqual(self.run_script().returncode,99)
        self.assertEqual((self.root/'ip-calls').read_bytes(),original)


if __name__=='__main__':unittest.main()

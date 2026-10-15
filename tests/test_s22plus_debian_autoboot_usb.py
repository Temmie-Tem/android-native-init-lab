"""Execute the physical script in private namespaces with effect stubs."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
SCRIPT=ROOT/'workspace/public/src/debian/s22plus_v1/device/lab-usb-autoboot'


def tree(path):
    return {str(p.relative_to(path)):('link',os.readlink(p)) if p.is_symlink() else
        ('file',hashlib.sha256(p.read_bytes()).hexdigest()) if p.is_file() else ('dir',)
        for p in sorted(path.rglob('*'))}


def inside(folder,case):
    subprocess.run(['mount','--make-rprivate','/'],check=True)
    for name in ('sys','run','etc'):
        subprocess.run(['mount','--bind',str(folder/name),'/'+name],check=True)
    env=dict(os.environ,PATH=str(folder/'bin')+':/usr/bin:/bin',CASE=case,STUB_LOG=str(folder/'effects'))
    first=subprocess.run(['/bin/sh',str(SCRIPT),'start'],env=env,capture_output=True,timeout=10)
    before=tree(folder/'run');effects=(folder/'effects').read_bytes() if (folder/'effects').exists() else b''
    second=subprocess.run(['/bin/sh',str(SCRIPT),'start'],env=env,capture_output=True,timeout=10)
    after=tree(folder/'run');later=(folder/'effects').read_bytes() if (folder/'effects').exists() else b''
    print(json.dumps(dict(first=first.returncode,second=second.returncode,unchanged=before==after,
        no_repeated_effect=effects==later,claim=(folder/'run/s22-debian/usb-attempt').exists(),
        gadget=(folder/'run/config/usb_gadget/g1').exists(),stderr=first.stderr.decode(),effects=effects.decode())))


class PhysicalScriptTests(unittest.TestCase):
    def run_case(self,case):
        with tempfile.TemporaryDirectory(prefix='s22-autoboot-usb-') as temporary:
            folder=Path(temporary)
            for name in ('etc/default','run/config/usb_gadget','run/s22-debian','sys/class/udc/a600000.dwc3',
                    'sys/devices/platform/soc/a600000.ssusb','bin'):(folder/name).mkdir(parents=True)
            (folder/'etc/default/lab-usb').write_text('serial=fixture\nhost_mac=host-fixture\ndevice_mac=device-fixture\ndevice_address=address-fixture\n')
            (folder/'sys/devices/platform/soc/a600000.ssusb/mode').write_text('')
            stubs={
                'uname':"printf '%s\\n' 5.10.226-android12-9-30958166-abS906NKSS7FYG8\n",
                'findmnt':"printf '%s\\n' configfs\n",
                'find':'test "$CASE" != find-error || exit 17\nexec /usr/bin/find "$@"\n',
                'mkdir':'''printf 'mkdir %s\\n' "$*" >> "$STUB_LOG"
test "$CASE" != partial || test "$1" != /run/config/usb_gadget/g1/configs/c.1 || exit 19
/usr/bin/mkdir "$@" || exit $?
if test "$1" = /run/config/usb_gadget/g1; then
 /usr/bin/mkdir "$1/strings" "$1/configs" "$1/functions"
fi
''',
                'ip':'''printf 'ip %s\\n' "$*" >> "$STUB_LOG"
test "$CASE" != network-error
'''}
            for name,text in stubs.items():
                path=folder/'bin'/name;path.write_text('#!/bin/sh\nset -eu\n'+text);path.chmod(0o700)
            completed=subprocess.run(['unshare','--user','--map-root-user','--mount','--pid','--fork','--mount-proc',
                sys.executable,str(Path(__file__).resolve()),'inside',str(folder),case],capture_output=True,text=True,timeout=30)
            self.assertEqual(completed.returncode,0,completed.stderr)
            return json.loads(completed.stdout)

    def test_first_gadget_and_no_replay(self):
        row=self.run_case('normal')
        self.assertEqual(row['first'],0,row)
        self.assertNotEqual(row['second'],0,row)
        self.assertTrue(row['claim'] and row['gadget'] and row['unchanged'] and row['no_repeated_effect'],row)
        self.assertEqual(row['effects'].count('mkdir /run/config/usb_gadget/g1\n'),1)
        self.assertEqual(row['effects'].count('ip '),3)

    def test_partial_setup_is_consumed(self):
        for case in ('partial','network-error'):
            with self.subTest(case=case):
                row=self.run_case(case)
                self.assertNotEqual(row['first'],0,row);self.assertNotEqual(row['second'],0,row)
                self.assertTrue(row['claim'] and row['gadget'] and row['unchanged'] and row['no_repeated_effect'],row)

    def test_failed_inventory_is_not_empty(self):
        row=self.run_case('find-error')
        self.assertNotEqual(row['first'],0,row)
        self.assertFalse(row['claim'] or row['gadget'],row)
        self.assertEqual(row['effects'],'')


if __name__=='__main__':
    if len(sys.argv)==4 and sys.argv[1]=='inside':inside(Path(sys.argv[2]),sys.argv[3])
    else:unittest.main()

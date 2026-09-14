"""Host-only privilege boundary and actual fuser/PTY behavior; no USB access."""
from contextlib import ExitStack
import json
import os
from pathlib import Path
import pty
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

SCRIPTS = Path(__file__).resolve().parents[1]/'workspace/public/src/scripts/revalidation'
if str(SCRIPTS) not in sys.path: sys.path.insert(0,str(SCRIPTS))
import s22plus_native_host_census_v1 as census

CONFIG = dict(schema=census.SCHEMA, uid=1000, account='fixture', topology='3-7.9',
              vendor='04e8', product='6861', interface='00', driver='cdc_acm', serial_prefix='S22E3')


class CensusTests(unittest.TestCase):
    def temporary(self):
        value = tempfile.TemporaryDirectory(); self.addCleanup(value.cleanup)
        return Path(value.name)

    def fixture(self):
        root = self.temporary(); usb = root/'devices'/CONFIG['topology']
        interface = usb/(CONFIG['topology']+':1.0'); tty = interface/'tty'/'ttyACM0'
        tty.mkdir(parents=True)
        driver = root/'drivers'/'cdc_acm'; driver.mkdir(parents=True)
        (interface/'driver').symlink_to(driver)
        for name,value in [('idVendor','04e8'),('idProduct','6861'),('serial','S22E3'+'a'*32)]:
            (usb/name).write_text(value+'\n')
        (interface/'bInterfaceNumber').write_text('00\n')
        (tty/'dev').write_text('166:0\n'); (tty/'device').symlink_to(interface)
        classes = root/'class'; classes.mkdir(); (classes/'ttyACM0').symlink_to(tty)
        nodes = root/'dev'; nodes.mkdir(); (nodes/'ttyACM0').touch()
        node_stat = os.stat_result((stat.S_IFCHR|0o600,1,0,1,os.getuid(),os.getgid(),0,0,0,0))
        original = Path.lstat
        def lstat(path):
            if path == nodes/'ttyACM0':
                info = original(path)
                return type('CharacterNode',(),dict(st_mode=node_stat.st_mode,st_rdev=os.makedev(166,0),
                    st_dev=info.st_dev,st_ino=info.st_ino))()
            return original(path)
        stack = ExitStack(); self.addCleanup(stack.close)
        stack.enter_context(mock.patch.object(Path,'lstat',lstat))
        return root,classes,nodes,usb,interface

    def test_fixed_configuration_and_no_argument_interface(self):
        self.assertEqual(census.config_value(json.dumps(CONFIG)),CONFIG)
        for change in [dict(uid=True),dict(account='fixture;id'),dict(topology='../../dev'),
                       dict(serial_prefix='*'),dict(vendor='1234'),dict(interface='01')]:
            with self.subTest(change=change),self.assertRaises(census.CensusError):
                census.config_value(json.dumps({**CONFIG,**change}))
        with self.assertRaises(census.CensusError):
            census.config_value(json.dumps(CONFIG)[:-1]+',"uid":1001}')
        with mock.patch.object(census,'collect') as collect:
            with self.assertRaises(census.CensusError): census.main(['helper','/dev/ttyACM0'])
            collect.assert_not_called()

    def test_root_and_exact_invoking_account_required(self):
        with mock.patch.object(os,'geteuid',return_value=1000),self.assertRaises(census.CensusError):
            census.main(['helper'])
        with mock.patch.object(os,'geteuid',return_value=0),mock.patch.object(census,'trusted_file',return_value=json.dumps(CONFIG)),\
                mock.patch.dict(os.environ,PKEXEC_UID='1001'),mock.patch.object(census,'collect') as collect:
            with self.assertRaises(census.CensusError): census.main(['helper'])
            collect.assert_not_called()

    def test_user_owned_or_indirect_installed_file_rejected(self):
        root = self.temporary(); path = root/'policy.json'; path.write_text(json.dumps(CONFIG))
        with self.assertRaises(census.CensusError): census.trusted_file(path)
        link = root/'linked'; link.symlink_to(path)
        with self.assertRaises(census.CensusError): census.trusted_file(link)

    def test_exact_endpoint_absence_and_identity_drift(self):
        _,classes,nodes,usb,interface = self.fixture()
        value = census.endpoint(CONFIG,class_tty=classes,dev_root=nodes)
        self.assertEqual((value['tty_name'],value['major'],value['minor']),('ttyACM0',166,0))
        (usb/'serial').write_text('foreign\n')
        with self.assertRaises(census.CensusError): census.endpoint(CONFIG,class_tty=classes,dev_root=nodes)
        (usb/'serial').write_text('S22E3'+'a'*32+'\n')
        (interface/'bInterfaceNumber').write_text('01\n')
        with self.assertRaises(census.CensusError): census.endpoint(CONFIG,class_tty=classes,dev_root=nodes)
        (classes/'ttyACM0').unlink()
        self.assertIsNone(census.endpoint(CONFIG,class_tty=classes,dev_root=nodes))

    def test_incomplete_inventory_is_not_absence(self):
        _,classes,nodes,_,interface = self.fixture()
        (interface/'driver').unlink()
        with self.assertRaises(OSError): census.endpoint(CONFIG,class_tty=classes,dev_root=nodes)
        for path in (classes/'missing', nodes/'ttyACM0'):
            with self.assertRaises(OSError): census.endpoint(CONFIG,class_tty=path,dev_root=nodes)
        with mock.patch.object(os,'scandir',side_effect=PermissionError),self.assertRaises(OSError):
            census.endpoint(CONFIG,class_tty=classes,dev_root=nodes)

    def test_same_name_replacement_during_census_is_rejected(self):
        _,classes,nodes,_,_ = self.fixture()
        original_endpoint = census.endpoint
        node = nodes/'ttyACM0'
        def replacement(_):
            node.rename(nodes/'old-held-node'); node.touch()
            return [os.getpid()]
        with mock.patch.object(census,'endpoint',side_effect=lambda config: original_endpoint(config,class_tty=classes,dev_root=nodes)),\
                mock.patch.object(census,'bounded_fuser',side_effect=replacement),self.assertRaises(census.CensusError):
            census.collect(CONFIG)

    def test_actual_fuser_reports_current_holder_without_opening_tty(self):
        master,slave = pty.openpty()
        try:
            node = os.ttyname(slave)
            self.assertIn(os.getpid(),census.bounded_fuser(node))
            child = subprocess.Popen([sys.executable,'-c','import sys; sys.stdin.buffer.read(1)'],
                pass_fds=(slave,),stdin=subprocess.PIPE)
            try: self.assertEqual(set(census.bounded_fuser(node)),{os.getpid(),child.pid})
            finally: child.communicate(b'x',timeout=3)
        finally:
            os.close(slave); os.close(master)

    def fake_fuser(self, body):
        path = self.temporary()/'fuser'
        path.write_text('#!/usr/bin/python3\n'+body+'\n'); path.chmod(0o700)
        patch = mock.patch.object(census,'FUSER',str(path)); patch.start(); self.addCleanup(patch.stop)

    def test_census_negative_diagnostics_overflow_and_timeout(self):
        bodies = ["import sys; sys.stderr.write('denied\\n'); sys.exit(1)",
                  "import sys; sys.stdout.write('9'*9000)",
                  "import time; time.sleep(30)"]
        for body in bodies:
            with self.subTest(body=body):
                self.fake_fuser(body)
                with self.assertRaises(census.CensusError): census.bounded_fuser('/dev/ttyACM0',timeout=.15)

    def test_no_holders_complete_and_endpoint_change_rejected(self):
        self.fake_fuser('raise SystemExit(1)')
        self.assertEqual(census.bounded_fuser('/dev/ttyACM0'),[])
        original = dict(tty_name='ttyACM0',major=166,minor=0,identity_sha256='a'*64)
        with mock.patch.object(census,'endpoint',side_effect=[original,None]),\
                mock.patch.object(census,'bounded_fuser',return_value=[os.getpid()]):
            with self.assertRaises(census.CensusError): census.collect(CONFIG)


if __name__ == '__main__': unittest.main()

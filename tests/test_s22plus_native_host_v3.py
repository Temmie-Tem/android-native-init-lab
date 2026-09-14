"""Fixed installation rendering and real tty descriptor/exclusive-close checks."""
import json
import os
from pathlib import Path
import pty
import pwd
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from unittest import mock

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'workspace/public/src/scripts/revalidation'))
import s22plus_native_host_v3 as host
from s22plus_native_records_v3 import read


class HostTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory(); self.addCleanup(temporary.cleanup)
        self.root=Path(temporary.name)
        self.account=pwd.getpwuid(os.getuid()).pw_name
        receipt=host.prepare_installation(self.root/'installation',uid=os.getuid(),account=self.account,topology='3-7.9')
        self.installation=read(Path(receipt['path']))

    def test_generated_rules_have_one_program_account_and_native_port(self):
        files=host.installation_files(uid=os.getuid(),account=self.account,topology='3-7.9')
        self.assertEqual(set(files),{host.census.HELPER,host.census.CONFIG,host.POLKIT,host.UDEV,host.ACTION})
        policy=files[host.POLKIT][0].decode()
        self.assertIn('action.id === "'+host.census.ACTION_ID+'"',policy)
        self.assertIn('subject.user === "'+self.account+'"',policy)
        self.assertNotIn('command_line',policy)
        action=ET.fromstring(files[host.ACTION][0]).find('action')
        self.assertEqual(action.attrib,{'id':host.census.ACTION_ID})
        self.assertEqual([(item.attrib,item.text) for item in action.findall('annotate')],
            [({'key':'org.freedesktop.policykit.exec.path'},str(host.census.HELPER))])
        self.assertEqual([item.text for item in action.find('defaults')],['no','no','no'])
        udev=files[host.UDEV][0].decode()
        self.assertIn('KERNELS=="3-7.9"',udev); self.assertIn('ID_USB_INTERFACE_NUM}=="00"',udev)

    def test_ready_is_noninteractive_and_reports_original_process_identity(self):
        client=host.NativeHost(self.installation,self.root/'ready')
        with mock.patch.object(client,'installed'),mock.patch.object(client,'command',return_value=('',{'fixture':True})) as command:
            client.ready()
        argv=command.call_args.args[0]
        self.assertNotIn('--allow-user-interaction',argv)
        self.assertNotIn('--detail',argv)
        self.assertEqual(argv[argv.index('--action-id')+1],host.census.ACTION_ID)
        process=argv[argv.index('--process')+1].split(',')
        self.assertEqual((int(process[0]),int(process[2])),(os.getpid(),os.getuid()))

    def test_real_pty_exclusion_released_and_close_receipt_is_actual(self):
        master,slave=pty.openpty(); name=os.ttyname(slave); info=os.fstat(slave)
        self.addCleanup(os.close,master); os.close(slave)
        endpoint=dict(tty_name='ttyACM0',generation=dict(node=[info.st_dev,info.st_ino,info.st_rdev]))
        client=host.NativeHost(self.installation,self.root/'tty')
        original=os.open
        def redirected(path,*args,**kwargs):
            return original(name if str(path)=='/dev/ttyACM0' else path,*args,**kwargs)
        def holders(**kwargs):
            if kwargs.get('descriptor') is not None:
                actual=os.fstat(kwargs['descriptor'])
                self.assertEqual(endpoint['generation']['node'],[actual.st_dev,actual.st_ino,actual.st_rdev])
            return {'endpoint':endpoint},{'fixture':True}
        with mock.patch.object(client,'holders',side_effect=holders),mock.patch.object(client,'properties',return_value={'fixture':True}),\
                mock.patch.object(host.census,'endpoint',return_value=endpoint),mock.patch.object(os,'open',side_effect=redirected):
            for _ in range(2):
                with client.open_native('a'*32,before_open=lambda:None) as (fd,receipt):
                    with self.assertRaises(OSError): original(name,os.O_RDWR|os.O_NOCTTY|os.O_NONBLOCK)
                self.assertTrue(receipt['close']['descriptor_closed'])
                self.assertIsNone(receipt['close']['exclusive_release_errno'])
                with self.assertRaises(OSError): os.fstat(fd)


if __name__=='__main__': unittest.main()

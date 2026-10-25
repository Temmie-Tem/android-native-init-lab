"""Run the production final helper under ARM64 syscall fixtures."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import types

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'workspace/public/src/scripts/revalidation'))
import s22plus_debian_download_v1 as download
import s22plus_debian_reboot_access_v1 as access
import s22plus_debian_autoboot_session_v1 as session
from s22plus_native_records_v3 import Journal,publish,read


class DownloadReturnTests(unittest.TestCase):
    def test_actual_arm64_helper(self):
        with tempfile.TemporaryDirectory() as work:
            folder=Path(work)
            (folder/'s22plus_debian_download_seal_v1.h').write_bytes(download.return_header())
            binary=folder/'download-fixtures'
            subprocess.run(['aarch64-linux-gnu-gcc','-static','-O2','-Wall','-Wextra','-Werror',
                '-Wno-misleading-indentation','-I',str(folder),'-I',str(ROOT/'workspace/public/src/native-init'),
                str(ROOT/'tests/s22plus_debian_download_return_harness.c'),'-o',str(binary)],check=True)
            identity=subprocess.check_output(['file',str(binary)],text=True)
            self.assertIn('ARM aarch64',identity)
            result=subprocess.run(['qemu-aarch64',str(binary)],capture_output=True,text=True,timeout=20)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            self.assertIn('PASS ARM64 production Download helper',result.stdout)

    def test_original_final_intent_deadline_cannot_be_renewed(self):
        with tempfile.TemporaryDirectory() as work:
            root=Path(work);folder=root/'io-debian-shutdown';folder.mkdir()
            adapter=types.SimpleNamespace(directory=root,folder=lambda name:root/('io-'+name))
            request=dict(operation='debian-autoboot',N=dict(namespace=download.NAMESPACE))
            control=dict(action='debian-shutdown',command='download')
            detail=dict(command='download',dispatch_ns=100,deadline_ns=190)
            publish(root/'operation.json',request);publish(folder/'intent.json',detail)
            publish(root/'debian-shutdown.json',control)
            Journal(root/'journal').append('effect-intent',step='debian-shutdown',action='debian-shutdown',role='N',detail=detail)
            with mock.patch.object(access,'Access') as owner:
                owner.return_value.rederive_control.return_value=control
                first=access.return_request(adapter,request,create=True)
                self.assertEqual((first['requested_ns'],first['deadline_ns']),(100,190))
                self.assertEqual(access.return_request(adapter,request,create=True),first)
                changed=dict(first,deadline_ns=200)
                (root/'debian-return-ready.json').unlink();publish(root/'debian-return-ready.json',changed)
                with self.assertRaisesRegex(ValueError,'deadline or original intent'):
                    access.return_request(adapter,request,create=True)

    def test_final_verb_is_selected_before_reading_or_dispatching(self):
        owner=access.Access.__new__(access.Access);owner.reboot_phase=2
        owner.request=dict(operation='debian-autoboot',N=dict(namespace=download.NAMESPACE))
        self.assertEqual(owner.final_command(),'download')
        with self.assertRaisesRegex(ValueError,'control phase'):owner.control_evidence('shutdown')
        owner.request['N']['namespace']='p460'
        self.assertEqual(owner.final_command(),'shutdown')
        with self.assertRaisesRegex(ValueError,'control phase'):owner.control_evidence('download')

    def test_health_only_close_preserves_original_automatic_transfer_proof(self):
        request=dict(operation='debian-autoboot',N=dict(namespace=download.NAMESPACE))
        adapter=types.SimpleNamespace(directory=Path('/fixture'))
        returned=dict(launch={'path':'/launch'},completed=True)
        adapter.recover_transfer_result=mock.Mock(return_value=returned)
        ready=dict(requested_ns=100,deadline_ns=190)
        launch=dict(arrival_deadline_ns=190,boottime_ns=150,ticket={'observed':True},revalidation={'valid':True})
        owners=[]
        for phase in (1,2):
            current=mock.Mock();current.evidence.return_value=dict(proof={})
            current.rederive_health.return_value=dict(health=dict(boot_count=phase));owners.append(current)
        with mock.patch.object(access,'Access',side_effect=owners),\
             mock.patch.object(access,'return_request',return_value=ready),\
             mock.patch.object(session,'verify',return_value=Path('/launch')),\
             mock.patch.object(session,'read',return_value=launch),mock.patch.object(session,'pin',return_value={}):
            value=session.reboot_terminal(adapter,request,recovered=True)
        self.assertTrue(value['automatic_download_return_proved'])
        self.assertFalse(value['normal_return'])
        self.assertEqual(adapter.recover_transfer_result.call_args.args[0].name,'install-android')
        adapter.recover_transfer_result.side_effect=ValueError('no original install-android transfer')
        with mock.patch.object(access,'Access',side_effect=owners),\
             mock.patch.object(access,'return_request',return_value=ready):
            self.assertFalse(session.reboot_terminal(adapter,request,recovered=True)['automatic_download_return_proved'])


if __name__=='__main__':unittest.main()

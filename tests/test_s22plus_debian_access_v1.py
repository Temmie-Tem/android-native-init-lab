"""Same-boot SSH evidence and narrowly owned host-network cleanup."""
import hashlib
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock
import s22plus_debian_access_v1 as access
import s22plus_debian_handoff_session_v1 as session
import s22plus_native_observation_v3 as observation
import s22plus_native_root_inspect_profile_v1 as root_profile
from s22plus_native_records_v3 import publish,pin


class AccessTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup);self.folder=Path(temporary.name)
        self.ordinal=0
    def capture(self,stdout,stderr=b'',returncode=0):
        self.ordinal+=1
        writer=access.raw.RawCaptureWriter(self.folder,'capture-'+str(self.ordinal),stdout_maximum=65536,
            stderr_maximum=16384,argv0_name='fixture')
        writer.write_stdout(stdout);writer.write_stderr(stderr);return writer.finalize(returncode=returncode)

    def test_ssh_health_joins_both_candidate_and_original_native_boot(self):
        boot='01234567-1234-4234-8234-0123456789ab';run='a'*32
        plan=dict(root_run_id='b'*32,candidate=dict(namespace='p999',version='v1.0.0',run_id=run))
        body=(f'S22PLUS_FYG8_DEBIAN_V1 {plan["root_run_id"]}\nBOOTSTRAP_CANDIDATE p999 v1.0.0 {run}\n'
            'BOOTSTRAP_HANDOFF pid=1 children=0 backend=s22plus-fyg8\npid1_exe=/usr/sbin/init\npid1_root=/\n'
            f'boot_id={boot}\nboot_count=1\nDEBIAN_HEALTH_PASS\n').encode()
        digest=hashlib.sha256(boot.encode()).hexdigest()
        self.assertEqual(access.health_projection(self.capture(body),plan,boot_sha256=digest)['boot_count'],1)
        for changed in (body.replace(run.encode(),b'c'*32),body.replace(b'pid1_root=/\n',b''),
                body+b'extra\n',body.replace(b'boot_count=1',b'boot_count=100001')):
            with self.assertRaises(ValueError):access.health_projection(self.capture(changed),plan,boot_sha256=digest)
        with self.assertRaises(ValueError):access.health_projection(self.capture(body),plan,boot_sha256='0'*64)
        with self.assertRaises(access.raw.RawCaptureError):access.health_projection(self.capture(body,b'warning'),plan,boot_sha256=digest)

    def test_new_task_pins_current_nmcli_and_later_tool_drift_rejects(self):
        retained={}
        for name in ('client_key','known_hosts','ssh','nmcli'):
            path=self.folder/name;path.write_text(name+' retained\n');retained[name]=pin(path)
        retained['link']={};current=self.folder/'current-nmcli';current.write_text('current pinned tool\n')
        with mock.patch.object(root_profile,'prior_inputs',return_value=(dict(run_id='b'*32),{},retained)),\
                mock.patch.object(access,'Path',side_effect=lambda name:current if name=='/usr/bin/nmcli' else Path(name)):
            initial=access.inputs('a'*32);self.assertEqual(initial['nmcli'],pin(current));self.assertNotEqual(initial['nmcli'],retained['nmcli'])
            task=dict(N=dict(run_id_hex='a'*32),seconds=3600,debian_access=initial)
            session.validate_task(task,recovery=False)
            current.write_text('host tool changed later\n')
            with self.assertRaises(ValueError):session.validate_task(task,recovery=False)
            session.validate_task(task,recovery=True)

    def test_shutdown_ack_does_not_claim_clean_filesystem_or_accept_early_zero(self):
        result=access.shutdown_projection(self.capture(b'DEBIAN_SHUTDOWN_REQUEST_ACCEPTED\n'),'192.0.2.1')
        self.assertTrue(result['request_accepted']);self.assertFalse(result['clean_shutdown_proved'])
        for output in (b'',b'DEBIAN_REBOOT_REQUEST_ACCEPTED\n'):
            with self.assertRaises(ValueError):access.shutdown_projection(self.capture(output),'192.0.2.1')

    def test_cleanup_deletes_only_recorded_uuid_name_mac_interface(self):
        for mismatch in (False,True):
            with self.subTest(mismatch=mismatch):
                folder=self.folder/str(mismatch);folder.mkdir();tool=folder/'nmcli';tool.write_text('fixture')
                found=dict(interface='fixture0');publish(folder/'endpoint.json',found)
                connection='01234567-1234-4234-8234-0123456789ab'
                publish(folder/'network-intent.json',dict(uuid=connection,endpoint=found))
                plan=dict(network_uuid=connection,nmcli=pin(tool),candidate=dict(run_id='a'*32),link=dict(host_mac='02:00:00:00:00:01'))
                obj=access.Access.__new__(access.Access);obj.plan=plan;obj.adapter=SimpleNamespace(folder=lambda name:folder)
                deleted=[]
                def acquire(args,output,name,**kw):
                    writer=access.raw.RawCaptureWriter(output,name,stdout_maximum=16384,stderr_maximum=16384,argv0_name='nmcli')
                    if args[1:4]==['connection','delete','uuid']:
                        deleted.append(args[4]);return writer.finalize(returncode=0)
                    if deleted:return writer.finalize(returncode=10)
                    mac='02:00:00:00:00:ff' if mismatch else plan['link']['host_mac']
                    writer.write_stdout(('s22-debian-'+'a'*32+'\n'+connection+'\n'+mac+'\nfixture0\n').encode())
                    return writer.finalize(returncode=0)
                with mock.patch.object(access.raw,'acquire_command',acquire):result=obj.cleanup()
                self.assertEqual(deleted,[] if mismatch else [connection])
                self.assertEqual(result['status'],'HOST_CLEANUP_UNPROVED' if mismatch else 'REMOVED')

    def test_missing_or_malformed_science_raw_does_not_block_recovered_android_terminal(self):
        original=dict(nonce_sha256='a'*64,kernel_boot_identity_sha256='b'*64)
        publish(self.folder/'transition-intent.json',original)
        adapter=SimpleNamespace(directory=self.folder,folder=lambda name:self.folder)
        with mock.patch.object(session,'intents',return_value=[dict(detail=original)]),\
                mock.patch.object(observation,'switch_prefix',side_effect=access.raw.RawCaptureError('partial receipt')):
            value=session.terminal(adapter,dict(N={}),recovered=True)
        self.assertFalse(value['debian_boot_proved']);self.assertFalse(value['ssh_access_proved'])
        self.assertEqual(value['evidence_error']['type'],'RawCaptureError')


if __name__=='__main__':unittest.main()

"""Compound-start ordering, raw preservation, original recovery and scope."""
from contextlib import contextmanager
import copy
from pathlib import Path
import socket
import struct
import tempfile
import unittest
from unittest import mock

import test_s22plus_debian_handoff_v1 as previous
import test_s22plus_debian_integrated_v1 as fixture
import s22plus_debian_integrated_profile_v1 as profile
import s22plus_debian_integrated_observation_v1 as observation
import s22plus_debian_integrated_protocol_v1 as wire
import s22plus_native_records_v3 as records


class Device(previous.Device):
    def integrated_observe(self,step,request,*,guard,before_start):
        guard();self.assert_mode('N');before_start(dict(mode=profile.OPERATION,nonce_sha256='1'*64))
        self.actions.append('rw-init-once')
        if self.fail_after=='rw-init':raise OSError('compound start delivered; response lost')
        self.actions.append('acm-release-once');self.mode='Debian'
        if self.fail_after=='acm-release':raise OSError('release ACK lost')
        return self.proof(step)


class OwnerTests(previous.OwnerTests):
    def operation(self,device=None):
        device=device or Device()
        directory=previous.owner.prepare_operation(self.root,self.grant,operation=profile.OPERATION,adapter=device)
        patch=mock.patch.object(previous.access,'Access',previous.FixtureAccess);patch.start();self.addCleanup(patch.stop)
        return previous.owner.Session(self.root,directory,device),device

    def test_normal_path_pauses_for_physical_return_then_one_a(self):
        session,device=self.operation();pending=session.execute(attended=True)
        self.assertEqual(pending['state'],'AWAITING_PHYSICAL_DOWNLOAD');self.assertEqual(device.installed,['N'])
        device.mode='Download';result=session.resume(attended=True)
        self.assertFalse(result['recovered']);self.assertEqual(device.installed,['N','A']);self.assertIsNone(self.f1)
        self.assertEqual(device.actions.count('rw-init-once'),1);self.assertEqual(device.actions.count('shutdown-once'),1)
        self.assertEqual([row['data']['step'] for row in session.rows() if row['event']=='effect-intent'],
            ['android-download','install-native-first','debian-integrated','debian-shutdown','install-android'])
        with self.assertRaises(ValueError):session.execute(attended=True)

    def test_uncertainty_stops_for_original_recovery_without_native_or_ssh_replay(self):
        for fault in ('rw-init','acm-release','ssh-health','shutdown'):
            with self.subTest(fault=fault):
                self.setUp();device=Device();device.fail_after=fault;session,device=self.operation(device)
                self.assertEqual(session.execute(attended=True)['state'],'AWAITING_ATTENDED_RECOVERY')
                before=list(device.actions);session.recover(attended=True)
                self.assertEqual(device.installed,['N','A'])
                for action in ('rw-init-once','shutdown-once'):
                    self.assertEqual(device.actions.count(action),before.count(action))

    def test_completed_a_then_failed_health_never_retransfers(self):
        session,device=self.operation();session.execute(attended=True);device.mode='Download';device.health_failure=True
        self.assertEqual(session.resume(attended=True)['state'],'AWAITING_ATTENDED_RECOVERY')
        device.health_failure=False;session.recover(attended=True)
        self.assertEqual(device.installed,['N','A']);self.assertEqual(device.actions.count('rw-init-once'),1)


class ScopeTests(unittest.TestCase):
    def test_integrated_scope_requires_one_attended_3600s_operation(self):
        task=previous.root.ScopeTests().task();task.update(N=dict(profile=profile.PROFILE,run_id_hex='1'*32),
            seconds=3600,operations=[profile.OPERATION],debian_access=dict.fromkeys(
                ('link','client_key','known_hosts','nmcli','ssh','root_run_id','network_uuid')))
        with mock.patch.object(profile,'image_binding'),mock.patch.object(previous.scope,'android_basis_for_image'),\
                mock.patch.object(previous.access,'inputs',return_value=task['debian_access']):
            previous.scope.validate_task(task)
            for name,value in (('seconds',1800),('seconds',3601),('recovery_mode','deferred'),('operation_budget',2),
                    ('E',{}),('admission',{}),('reentry',True),('operations',['debian-handoff']),('hud',True)):
                changed=copy.deepcopy(task);changed[name]=value
                with self.assertRaises(ValueError):previous.scope.validate_task(changed)
        with mock.patch.object(previous.scope,'android_basis_for_image'),\
                mock.patch.object(profile,'image_binding',side_effect=FileNotFoundError),\
                mock.patch.object(previous.access,'inputs',side_effect=FileNotFoundError):
            previous.scope.validate_task(task,recovery=True)


def full_transcript():
    key,run,nonce=fixture.KEY,fixture.RUN,fixture.NONCE
    enc=lambda kind,seq,body:wire.handoff.encode(key,run,nonce,kind,seq,body)
    rows=fixture.prefix()+fixture.root_rows()
    rows.extend((enc(wire.handoff.CONTINUE_ACK,6,struct.pack('<I',1)),
        enc(wire.handoff.INIT_PROOF,7,struct.pack('<3I',1,8,41)+fixture.BOOT+bytes.fromhex('55'*32+'66'*32)+bytes(8)),
        enc(wire.handoff.START_ACK,8,struct.pack('<I',1))))
    for ordinal in range(15):
        sample=max(0,ordinal-2)
        rows.append(enc(wire.handoff.PROGRESS,2000+ordinal,
            struct.pack('<4IQ',ordinal+1 if ordinal<3 else 4,sample,1,0 if ordinal<2 else 3,sample*10000)+fixture.BOOT))
    rows.append(enc(wire.handoff.RELEASE_ACK,9,struct.pack('<I',1)))
    return b''.join(rows)


class CaptureTests(unittest.TestCase):
    @contextmanager
    def prepared(self,rx):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp);key=folder/'key';key.write_bytes(fixture.KEY)
            handoff=records.publish(folder/'handoff.json',fixture.SELECTION)
            image=dict(key=records.pin(key),run_id_hex=fixture.RUN.hex(),profile=profile.PROFILE)
            bound=dict(expected=fixture.EXPECTED,module_names=fixture.NAMES,handoff=handoff)
            left,right=socket.socketpair()
            try:
                if rx:right.sendall(rx)
                class Host:
                    config=dict(topology='fixture')
                    @contextmanager
                    def open_native(self,*args,**kwargs):
                        acquisition=dict(local_carrier=True,endpoint=dict(fixture='exact-open-generation'))
                        try:yield left.fileno(),acquisition
                        finally:acquisition['close']=dict(descriptor_closed=True,exclusive_release_errno=None)
                with mock.patch.object(profile,'image_binding',return_value=bound),\
                        mock.patch.object(observation.secrets,'token_bytes',return_value=fixture.NONCE),\
                        mock.patch.object(observation.target,'usb_snapshot',return_value=dict(fixture=True)),\
                        mock.patch.object(observation.target,'wait_departure',side_effect=lambda before,directory,deadline_ns,guard:
                            dict(departed=True,before=before,deadline_ns=deadline_ns,observed_ns=records.clock())):
                    yield folder,image,Host(),right
            finally:left.close();right.close()

    def run_observer(self,folder,image,host,before):
        return observation.observe(folder/'capture',image,host,guard=lambda:None,before_start=before,
            deadline_ns=records.clock()+2_000_000_000)

    def test_actual_host_consumer_journals_before_first_write_and_rederives(self):
        with self.prepared(full_transcript()) as (folder,image,host,peer):
            seen=[]
            def intent(value):
                peer.setblocking(False)
                with self.assertRaises(BlockingIOError):peer.recv(4096)
                self.assertEqual(value,records.read(folder/'capture/start-intent.json'));seen.append(value)
            value=self.run_observer(folder,image,host,intent)
            self.assertEqual(len(seen),1);self.assertEqual(value['proof']['status'],'PASS_DEBIAN_INTEGRATED_RUNTIME')
            self.assertFalse(value['proof']['ssh_access_proved'])
            self.assertEqual(value,observation.rederive(folder/'capture',image))
            sent=peer.recv(4096);self.assertEqual(len(sent),224)
            self.assertEqual(sent[:80],wire.request(fixture.KEY,fixture.RUN,fixture.NONCE))
            with self.assertRaises(FileExistsError):self.run_observer(folder,image,host,intent)

    def test_failed_original_intent_sends_nothing_and_preserves_capture(self):
        with self.prepared(b'') as (folder,image,host,peer):
            def fail(value):raise OSError('intent unavailable')
            with self.assertRaisesRegex(OSError,'intent unavailable'):self.run_observer(folder,image,host,fail)
            handle=observation.raw.load_handle(folder/'capture/session.capture.json')
            self.assertEqual(observation.raw.read_stderr(handle,maximum=224),b'')
            peer.setblocking(False)
            with self.assertRaises(BlockingIOError):peer.recv(4096)

    def test_failed_continuation_receipt_preserves_root_proof_without_sending(self):
        with self.prepared(b''.join(fixture.prefix()+fixture.root_rows())) as (folder,image,host,peer):
            real=observation.publish
            def publish(path,value):
                if path.name=='continue.json':raise OSError('continuation disk full')
                return real(path,value)
            with mock.patch.object(observation,'publish',publish),self.assertRaisesRegex(OSError,'disk full'):
                self.run_observer(folder,image,host,lambda value:None)
            value=observation.rederive(folder/'capture',image,complete=False)['proof']
            self.assertIsNotNone(value['debian_handoff']['root_transition']['proof'])
            self.assertIsNone(value['debian_handoff']['init_proof'])
            self.assertEqual(len(peer.recv(4096)),80)

    def test_close_publication_failure_cannot_discard_raw_or_repeat(self):
        with self.prepared(full_transcript()) as (folder,image,host,peer):
            real=observation.publish
            def publish(path,value):
                if path.name=='close.json':raise OSError('close publication failed')
                return real(path,value)
            with mock.patch.object(observation,'publish',publish),self.assertRaisesRegex(OSError,'publication'):
                self.run_observer(folder,image,host,lambda value:None)
            handle=observation.raw.load_handle(folder/'capture/session.capture.json')
            self.assertEqual(handle.producer_error_type,'OSError')
            self.assertEqual(observation.raw.read_stdout(handle,maximum=wire.MAXIMUM),full_transcript())
            self.assertTrue(observation.rederive(folder/'capture',image,complete=False)['proof']['debian_handoff']['runtime_proof'])


if __name__=='__main__':unittest.main()

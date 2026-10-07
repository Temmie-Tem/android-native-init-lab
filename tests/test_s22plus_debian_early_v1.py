"""Authenticated early evidence and one-transfer owner failure boundaries."""
from contextlib import contextmanager
import copy
import hashlib
from pathlib import Path
import socket
import struct
import tempfile
import unittest
from unittest import mock

import test_s22plus_native_session_v3 as harness
import test_s22plus_native_root_inspect_v1 as root
import s22plus_debian_early_protocol_v1 as wire
import s22plus_debian_early_profile_v1 as profile
import s22plus_debian_early_observation_v1 as observation
import s22plus_native_root_inspect_session_v1 as scope
import s22plus_native_records_v3 as records
import s22plus_native_session_v3 as owner

KEY=bytes(range(32));RUN=bytes(range(16));NONCE=bytes(range(1,33))
BOOT=b'12345678-1234-1234-1234-123456789abc'
EXPECTED=dict(shell_sha256='11'*32,init_sha256='22'*32,helper_sha256='33'*32)
MODULES=['first','second','third']


def log(state='clean'):
    events=[f'BEGIN run={RUN.hex()} boot={BOOT.decode()} parent=1','TARGET_GUARD_OK']
    for index,name in enumerate(MODULES,1):
        events += [f'MODULE_BEGIN ordinal={index} name={name}',f'MODULE_DONE ordinal={index} name={name}']
    events += ['MODULE_SET_READY count=3','STORAGE_BOUND','RO_BEGIN','RO_DONE',
        f'METADATA state={state} complete_root_admission=0','STORAGE_CLOSED protected=1 cleanup_error=0',
        f'TERMINAL result=METADATA_{state.upper()} error=0']
    return ''.join(f'FYG8_H0 seq={i} {event}\n' for i,event in enumerate(events,1)).encode()


def encode(kind,seq,body,nonce=NONCE,run=RUN):
    return wire.frames.encode_frame(kind,seq,body+wire.tag(KEY,run,nonce,kind,seq,body))


def transcript(*,state='clean',pid=1,status=None,raw=None):
    raw=log(state) if raw is None else raw;hashed=hashlib.sha256(raw).digest()
    body=struct.pack('<4I',pid,7,(0 if state=='clean' else 2) if status is None else status,len(raw))
    body+=hashlib.sha256(BOOT).digest()+bytes.fromhex(EXPECTED['shell_sha256']+EXPECTED['init_sha256'])
    body+=hashed+bytes.fromhex(EXPECTED['helper_sha256'])
    rows=[encode(wire.PROOF,2,body)]
    rows.extend(encode(wire.LOG,i+3,raw[p:p+768]) for i,p in enumerate(range(0,len(raw),768)))
    rows.append(encode(wire.END,len(rows)+2,hashed))
    return rows


def replay(rows,**changes):
    return wire.replay(b''.join(rows),wire.request(KEY,RUN,NONCE),key=KEY,run=RUN,
        expected=changes.get('expected',EXPECTED),module_names=MODULES)


class ProtocolTests(unittest.TestCase):
    def test_clean_and_dirty_prove_only_early_pid1_and_protected_metadata(self):
        for state in ('clean','dirty'):
            value=replay(transcript(state=state))
            self.assertEqual(value['metadata_state'],state);self.assertTrue(value['debian_early_pid1'])
            self.assertTrue(value['partition_readonly']);self.assertFalse(value['root_admitted'])
            self.assertFalse(value['installed_debian_pid1']);self.assertFalse(value['persistent_writes'])

    def test_valid_crc_with_bad_hmac_rejects(self):
        rows=transcript();frame=wire.frames.decode_frame(rows[0])
        rows[0]=wire.frames.encode_frame(frame.frame_type,frame.sequence,frame.payload[:-1]+bytes([frame.payload[-1]^1]))
        with self.assertRaisesRegex(ValueError,'authentication'):replay(rows)

    def test_wrong_nonce_run_pid_binary_status_and_log_do_not_prove(self):
        variants=[transcript(pid=2),transcript(status=2)]
        for nonce,run in ((b'x'*32,RUN),(NONCE,b'x'*16)):
            rows=transcript();frame=wire.frames.decode_frame(rows[0])
            rows[0]=encode(frame.frame_type,frame.sequence,frame.payload[:-32],nonce,run);variants.append(rows)
        rows=transcript();frame=wire.frames.decode_frame(rows[1]);body=bytearray(frame.payload[:-32]);body[0]^=1
        rows[1]=encode(frame.frame_type,frame.sequence,bytes(body));variants.append(rows)
        for rows in variants:
            with self.assertRaises(ValueError):replay(rows)
        for field in EXPECTED:
            with self.assertRaises(ValueError):replay(transcript(),expected=dict(EXPECTED,**{field:'44'*32}))

    def test_truncation_duplicate_skip_and_after_terminal_reject(self):
        good=transcript()
        for rows in (good[:-1],good[:1]+good,good[:1]+good[2:],good+good[-1:],good[:-1]+[good[-1][:-1]]):
            with self.assertRaises(ValueError):replay(rows)

    def test_signed_semantically_false_module_or_protection_log_rejects(self):
        good=log()
        for old,new in ((b'MODULE_DONE ordinal=2',b'MODULE_DONE ordinal=1'),(b'name=third',b'name=wrong'),
                (b'RO_DONE',b'RO_BEGIN'),(b'protected=1',b'protected=0'),(b'parent=1',b'parent=2')):
            with self.assertRaises(ValueError):replay(transcript(raw=good.replace(old,new)))

    def test_negative_cleanup_is_diagnostic_and_must_not_repeat(self):
        negative=log().replace(b'cleanup_error=0',b'cleanup_error=5').replace(b'METADATA_CLEAN error=0',b'REJECTED error=5')
        proof=replay(transcript(raw=negative,status=1))
        self.assertEqual(proof['metadata_state'],'unproved');self.assertFalse(proof['preparation_complete'])
        lines=negative.splitlines();lines.insert(-1,lines[-2])
        repeated=b''.join(b'FYG8_H0 seq='+str(i).encode()+b' '+line.split(b' ',2)[2]+b'\n' for i,line in enumerate(lines,1))
        with self.assertRaises(ValueError):replay(transcript(raw=repeated,status=1))


class ScopeTests(unittest.TestCase):
    def test_exact_attended_android_origin_and_recovery_without_candidate_reads(self):
        task=root.ScopeTests().task();task.update(N=dict(profile=profile.PROFILE,run_id_hex='1'*32),
            seconds=1800,operations=[profile.OPERATION])
        with mock.patch.object(profile,'image_binding'),mock.patch.object(scope,'android_basis_for_image'):
            scope.validate_task(task)
            for field,value in (('seconds',1801),('operation_budget',2),('recovery_mode','deferred'),('reentry',True),
                    ('operations',['debian-early','bootstrap']),('E',{}),('admission',{})):
                invalid=copy.deepcopy(task);invalid[field]=value
                with self.assertRaises(ValueError):scope.validate_task(invalid)
        with mock.patch.object(profile,'image_binding',side_effect=FileNotFoundError),\
                mock.patch.object(scope,'android_basis_for_image'):
            scope.validate_task(task,recovery=True)


class Device(harness.DeviceFixture):
    def early_observe(self,step,request,*,guard):
        guard();self.assert_mode('N');self.actions.append('early-snapshot-once')
        if self.fail_after=='evidence':raise OSError('snapshot interrupted')
        return self.proof(step)


class OwnerTests(unittest.TestCase):
    setUp=harness.OwnerTests.setUp
    def operation(self,device=None):
        device=device or Device()
        directory=owner.prepare_operation(self.root,self.grant,operation=profile.OPERATION,adapter=device)
        return owner.Session(self.root,directory,device),device

    def test_normal_pause_one_n_one_a_and_no_native_control_or_admission(self):
        session,device=self.operation();result=session.execute(attended=True)
        self.assertEqual(result['state'],'AWAITING_PHYSICAL_DOWNLOAD');self.assertEqual(device.installed,['N'])
        self.assertEqual(device.actions,['android-download','install-native-first','early-snapshot-once'])
        device.mode='Download';self.assertFalse(session.resume(attended=True)['recovered'])
        self.assertEqual(device.installed,['N','A']);self.assertEqual(device.admitted,0);self.assertIsNone(self.f1)
        self.assertEqual([r['data']['step'] for r in session.rows() if r['event']=='effect-intent'],
            ['android-download','install-native-first','install-android'])
        with self.assertRaises(ValueError):session.execute(attended=True)

    def test_uncertain_n_or_evidence_uses_recovery_without_repeating_either(self):
        for fault in ('install-native-first','evidence'):
            with self.subTest(fault=fault):
                self.setUp();device=Device();device.fail_after=fault;session,device=self.operation(device)
                self.assertEqual(session.execute(attended=True)['state'],'AWAITING_ATTENDED_RECOVERY')
                before=list(device.actions);session.recover(attended=True)
                self.assertEqual(device.installed,['N','A'])
                self.assertEqual(device.actions.count('early-snapshot-once'),before.count('early-snapshot-once'))

    def test_completed_a_health_failure_retries_only_health(self):
        session,device=self.operation();session.execute(attended=True);device.mode='Download';device.health_failure=True
        self.assertEqual(session.resume(attended=True)['state'],'AWAITING_ATTENDED_RECOVERY')
        device.health_failure=False;session.recover(attended=True)
        self.assertEqual(device.installed,['N','A']);self.assertEqual(device.actions.count('early-snapshot-once'),1)

    def test_uncertain_a_does_not_gain_second_transfer(self):
        session,device=self.operation()
        with self.assertRaises(ValueError):session.execute(attended=False)
        session.execute(attended=True);device.mode='Download';device.fail_after='install-android'
        self.assertEqual(session.resume(attended=True)['state'],'AWAITING_ATTENDED_RECOVERY')
        with self.assertRaises((ValueError,KeyError)):session.recover(attended=True)
        self.assertEqual(device.installed,['N','A'])


class CaptureTests(unittest.TestCase):
    def test_close_publication_failure_preserves_raw_and_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp);key=folder/'key';key.write_bytes(KEY);key.chmod(0o400)
            left,right=socket.socketpair();self.addCleanup(left.close);self.addCleanup(right.close)
            right.sendall(b''.join(transcript()))
            class Host:
                @contextmanager
                def open_native(self,*args,**kwargs):
                    acquisition=dict(local_carrier=True)
                    try:yield left.fileno(),acquisition
                    finally:acquisition['close']=dict(descriptor_closed=True,exclusive_release_errno=None)
            def publish(path,value):
                if path.name=='close.json':raise OSError('injected publication failure')
                return records.publish(path,value)
            with mock.patch.object(observation.profile,'image_binding',return_value=dict(expected=EXPECTED,module_names=MODULES)),\
                    mock.patch.object(observation.secrets,'token_bytes',return_value=NONCE),mock.patch.object(observation,'publish',publish):
                with self.assertRaisesRegex(OSError,'publication'):
                    observation.observe(folder/'capture',dict(key=records.pin(key),run_id_hex=RUN.hex()),Host(),
                        guard=lambda:None,deadline_ns=records.clock()+1_000_000_000)
            handle=observation.raw.load_handle(folder/'capture/session.capture.json')
            self.assertEqual(observation.raw.read_stdout(handle,maximum=wire.MAXIMUM),b''.join(transcript()))
            self.assertEqual(handle.producer_error_type,'OSError')
            self.assertEqual(right.recv(4096),wire.request(KEY,RUN,NONCE))


if __name__=='__main__':unittest.main()

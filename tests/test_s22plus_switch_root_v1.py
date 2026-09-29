"""Record integrity, exact scope and compound-owner no-replay behavior."""
import struct
from contextlib import nullcontext
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock
import test_s22plus_native_root_inspect_v1 as root
import test_s22plus_native_session_v3 as harness
import s22plus_switch_root_protocol_v1 as wire
import s22plus_switch_root_profile_v1 as profile
import s22plus_native_root_inspect_session_v1 as protected
import s22plus_native_session_v3 as owner
import s22plus_native_adapter_v3 as adapter_module
import s22plus_native_records_v3 as records

KEY=b'k'*32;RUN=b'r'*16;NONCE=b'n'*32;BOOT=b'b'*32;WITNESS='99'*32


def transcript(*,pid=1,boot=BOOT,flags=15,witness=bytes.fromhex(WITNESS)):
    rows=[]
    for stage in range(1,9):
        data=wire.LABELS[stage] if stage<8 else struct.pack('<4I',pid,8,41,7)+boot+witness+b'm'*32+struct.pack('<2I',flags,1)
        rows.append(wire.encode(KEY,RUN,NONCE,wire.RECORD,1023+stage,struct.pack('<2I',stage,0)+data))
    rows.append(wire.encode(KEY,RUN,NONCE,wire.RETURN_ACK,6,struct.pack('<I',1)))
    return rows


class RecordsTests(unittest.TestCase):
    def reader(self):return wire.Records(KEY,RUN,NONCE,BOOT,WITNESS)
    def test_post_exec_witness_is_separate_from_intent_and_return(self):
        reader=self.reader();rows=transcript()
        for row in rows[:7]:reader.accept(wire.frames.decode_frame(row))
        self.assertFalse(reader.projection()['pid1_handoff_proved'])
        reader.accept(wire.frames.decode_frame(rows[7]))
        self.assertTrue(reader.projection()['pid1_handoff_proved']);self.assertFalse(reader.returned)
        self.assertFalse(reader.projection()['debian_boot_proved'])
        reader.accept(wire.frames.decode_frame(rows[8]));self.assertTrue(reader.returned)

    def test_wrong_pid_boot_root_flags_or_executable_never_prove(self):
        for change in (dict(pid=2),dict(boot=b'x'*32),dict(flags=7),dict(witness=b'x'*32)):
            with self.subTest(change=change):
                reader=self.reader()
                with self.assertRaises(ValueError):
                    for row in transcript(**change):reader.accept(wire.frames.decode_frame(row))
                self.assertIsNone(reader.proof)

    def test_stale_nonce_bad_hmac_crc_stage_order_and_duplicates_reject(self):
        rows=transcript()
        for damaged in (rows[0][:-1]+bytes([rows[0][-1]^1]),b'BAD!'+rows[0][4:]):
            with self.assertRaises(ValueError):self.reader().accept(wire.frames.decode_frame(damaged))
        stale=wire.Records(KEY,RUN,b'o'*32,BOOT,WITNESS)
        with self.assertRaises(ValueError):stale.accept(wire.frames.decode_frame(rows[0]))
        reader=self.reader()
        with self.assertRaises(ValueError):reader.accept(wire.frames.decode_frame(rows[1]))
        reader.accept(wire.frames.decode_frame(rows[0]))
        with self.assertRaises(ValueError):reader.accept(wire.frames.decode_frame(rows[0]))

    def test_partial_prefix_stop_and_zero_without_a_witness_are_unproved(self):
        rows=transcript();reader=self.reader()
        for row in rows[:3]:reader.accept(wire.frames.decode_frame(row))
        stop=wire.encode(KEY,RUN,NONCE,wire.RECORD,1027,struct.pack('<3I',11,5,3))
        reader.accept(wire.frames.decode_frame(stop));self.assertIsNone(reader.proof)
        with self.assertRaises(ValueError):reader.accept(wire.frames.decode_frame(rows[3]))
        for length in (0,1,15,len(rows[7])-1):
            with self.assertRaises(ValueError):wire.frames.decode_frame(rows[7][:length])


class ScopeTests(unittest.TestCase):
    def test_only_one_android_origin_readonly_transition(self):
        task=root.ScopeTests().task();task['N']['profile']=profile.PROFILE;task['operations']=[profile.OPERATION]
        with mock.patch.object(profile,'image_binding'),mock.patch.object(protected,'android_basis_for_image'):
            protected.validate_task(task)
            for key,value in [('operations',['staged-preflight']),('E',{}),('admission',{}),('prior_terminal',{}),
                    ('operation_budget',2),('seconds',1801),('reentry',True),('hud',True),('usb_reconnect',True)]:
                bad=dict(task);bad[key]=value
                with self.subTest(key=key),self.assertRaises(ValueError):protected.validate_task(bad)
        steps=owner.steps(profile.OPERATION)
        self.assertEqual([s.name for s in steps],['android-download','install-native-first','switch-root','install-android','android-final'])
        self.assertFalse(any(s.ending=='detach' for s in steps))


class Device(harness.DeviceFixture):
    def observe(self,step,request,*,guard,before_terminal,consume_observation=None,before_extra=None):
        if step.name!=profile.SELECTION:return super().observe(step,request,guard=guard,before_terminal=before_terminal,
            consume_observation=consume_observation)
        guard();self.assert_mode('N');before_extra(dict(mode='fixed-pid1-transition',sequence=5))
        self.actions.append('transition-once')
        if self.fail_after=='transition':raise OSError('replacement occurred; proof lost')
        self.actions.append('post-exec-witness')
        if self.fail_after=='witness':raise OSError('proof reached; return unavailable')
        before_terminal(dict(request=dict(mode='switch-root-return',sequence=6)))
        self.actions.append('witness-return-once');self.mode='Download'
        if self.fail_after=='return':raise OSError('return sent; acknowledgement lost')
        return self.proof(step)


class OwnerTests(unittest.TestCase):
    setUp=harness.OwnerTests.setUp
    def test_normal_compound_intent_consumes_once(self):
        device=Device();directory=owner.prepare_operation(self.root,self.grant,operation=profile.OPERATION,adapter=device)
        session=owner.Session(self.root,directory,device);value=session.execute(attended=True)
        self.assertFalse(value['recovered']);self.assertEqual(device.installed,['N','A'])
        intents=[r['data']['step'] for r in session.rows() if r['event']=='effect-intent']
        self.assertEqual(intents,['android-download','install-native-first','switch-root','install-android'])
        self.assertEqual(device.actions.count('transition-once'),1)
        self.assertEqual(device.actions.count('witness-return-once'),1)
        with self.assertRaises(ValueError):session.execute(attended=True)

    def test_each_uncertain_boundary_recovers_without_transition_or_return_replay(self):
        for failure in ('transition','witness','return'):
            with self.subTest(failure=failure):
                self.setUp();device=Device();device.fail_after=failure
                directory=owner.prepare_operation(self.root,self.grant,operation=profile.OPERATION,adapter=device)
                session=owner.Session(self.root,directory,device);value=session.execute(attended=True)
                self.assertTrue(value['recovered']);self.assertEqual(device.installed,['N','A'])
                self.assertEqual(device.actions.count('transition-once'),1)
                self.assertEqual(device.actions.count('witness-return-once'),int(failure=='return'))
                with self.assertRaises(ValueError):session.execute(attended=True)
                self.assertEqual(device.installed,['N','A'])

    def test_final_health_read_failure_keeps_the_proved_single_a_transfer(self):
        class InterruptedHealth(Device):
            health_calls=0
            def android_health(self,step,request,*,guard):
                self.health_calls+=1
                if self.health_calls==1:raise OSError('ADB readiness read interrupted after A')
                return super().android_health(step,request,guard=guard)
        device=InterruptedHealth();directory=owner.prepare_operation(self.root,self.grant,operation=profile.OPERATION,adapter=device)
        session=owner.Session(self.root,directory,device);result=session.execute(attended=True)
        self.assertTrue(result['recovered']);self.assertEqual(device.installed,['N','A'])
        self.assertEqual(device.health_calls,2);self.assertEqual(device.actions.count('transition-once'),1)
        self.assertEqual(device.actions.count('witness-return-once'),1)


class AdapterDeadlineTests(unittest.TestCase):
    def test_delayed_preparation_uses_original_witness_return_deadline(self):
        self.exercise(None)

    def test_missing_or_changed_return_receipt_stops_before_enumeration(self):
        for fault in ('missing','sequence','transition'):
            with self.subTest(fault=fault):self.exercise(fault)

    def exercise(self,fault):
        with tempfile.TemporaryDirectory() as name:
            root=Path(name);directory=root/'workspace/private/operation';directory.mkdir(parents=True)
            adapter=adapter_module.Adapter(root,directory);folder=adapter.folder('switch-root',create=True)
            request=dict(operation=profile.OPERATION,N=dict(profile=profile.PROFILE),
                A=dict(ap=dict(path=str(directory/'A.tar.md5'),size=1,sha256='a'*64)))
            original=dict(mode='fixed-pid1-transition',sequence=5,run_id_hex='1'*32,
                nonce_sha256='2'*64,kernel_boot_identity_sha256='3'*64)
            transition=records.publish(folder/'transition-intent.json',original)
            with mock.patch.object(records,'clock',return_value=10_000_000_000):
                records.Journal(directory/'journal').append('effect-intent',step='switch-root',action='observe',role='N',
                    ending='download',recovery=False,detail=original)
            continuation=dict(transition=transition,request=dict(original,mode='switch-root-return',sequence=6),
                departure_deadline_ns=230_000_000_000,departure=dict(fixture=True))
            if fault=='sequence':continuation['request']['sequence']=7
            if fault=='transition':continuation['transition']=dict(transition,sha256='0'*64)
            if fault!='missing':records.publish(folder/'witness-return-intent.json',continuation)
            task=dict(odin=dict(path='/unused/odin',size=1,sha256='b'*64))
            reached=mock.Mock(side_effect=RuntimeError('H0 reached bounded enumeration'))
            dispatched=mock.Mock()
            with mock.patch.object(adapter,'configuration',return_value=task),\
                    mock.patch.object(adapter_module.inspection_session,'android_basis'),\
                    mock.patch.object(adapter_module,'clock',return_value=200_000_000_000),\
                    mock.patch.object(adapter_module.transport,'pin_regular_file',return_value=nullcontext(SimpleNamespace(path='/unused/odin'))),\
                    mock.patch.object(adapter,'original_android',return_value=nullcontext(None)),\
                    mock.patch.object(adapter_module.transition,'transaction_session',return_value=nullcontext(None)),\
                    mock.patch.object(adapter_module.transition,'wait_for_single_live_endpoint',reached):
                if fault:
                    with self.assertRaises((ValueError,OSError)):
                        adapter.transfer(owner.Step('install-android','transfer','A'),request,guard=lambda:None,before_launch=dispatched)
                    reached.assert_not_called()
                else:
                    with self.assertRaisesRegex(RuntimeError,'bounded enumeration'):
                        adapter.transfer(owner.Step('install-android','transfer','A'),request,guard=lambda:None,before_launch=dispatched)
                    self.assertEqual(reached.call_args.kwargs['timeout_sec'],90)
            dispatched.assert_not_called()


if __name__=='__main__':unittest.main()

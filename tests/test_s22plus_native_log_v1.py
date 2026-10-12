"""Calibration proof taxonomy, settled command transport and one-shot owner."""
import base64
import copy
import hashlib
from pathlib import Path
import sys
import tempfile
import subprocess
from types import SimpleNamespace
import unittest
from unittest import mock
import uuid

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'workspace/public/src/scripts/revalidation'))
import s22plus_native_log_protocol_v1 as protocol
import s22plus_native_log_profile_v1 as profile
import s22plus_native_log_session_v1 as phased
import s22plus_native_root_inspect_session_v1 as scope
import s22plus_native_observation_v3 as observation
import s22plus_native_session_v3 as owner
import s22plus_native_records_v3 as records
import s22plus_debian_usb_retention_v1 as retention
import s22plus_debian_file_retrieval_v1 as retrieval
import test_s22plus_native_session_v3 as harness
import test_s22plus_native_root_inspect_observation_v1 as transport_test
import test_s22plus_native_resident_v1 as producer

KEY=b'k'*32
RUN=bytes.fromhex(producer.IDENTITY.run_id_hex)
BOOT=bytes(range(16))
HELPER='33'*32


def frame(sequence,**changed):
    args=dict(key=KEY,run=RUN,boot=BOOT,sequence=sequence,pid=73,helper=bytes.fromhex(HELPER))
    args.update(changed);return protocol.encode(**args)


def fixture():
    pre,post=frame(1),frame(2);snapshot=b'abc'+pre+b'gap'+post+b'end'
    rows=[f'LC1_BEGIN version=1 run={RUN.hex()} boot={uuid.UUID(bytes=BOOT)} pid=73 helper={HELPER}']
    for stage in range(1,8):
        rows.append(f'LC1_STEP stage={stage}')
        if stage==3:rows.append('LC1_RETURN errno=0')
    rows.append('LC1_RESULT stage=7 errno=0 attempted=1 returned=1 module_errno=0 bound=1 '
        'pre_written=1 pre_ring=1 post_written=1 post_ring=1 backend_bytes=315 backend_eof=1 '
        'pre_count=1 post_count=1 pre_offset=3 post_offset=159 cleanup_errno=0')
    rows += ['LC1_'+name+' frame='+value.hex() for name,value in
        (('PRE',pre),('POST',post),('BACKEND_PRE',pre),('BACKEND_POST',post))]
    rows.append('LC1_BACKEND sha256='+hashlib.sha256(snapshot).hexdigest())
    return ('\n'.join(rows)+'\n').encode()


def live(stdout=None):
    return protocol.decode(fixture() if stdout is None else stdout,b'',key=KEY,run=RUN,helper=HELPER)


class Records(unittest.TestCase):
    def retained(self,raw,proof=None):
        return protocol.retained(raw,key=KEY,run=RUN,helper=HELPER,live=live() if proof is None else proof)

    def test_live_backend_is_distinct_from_returned_retention(self):
        result=live();self.assertTrue(result['live_pair_proved']);self.assertFalse(result['post_return_retention_proved'])
        result=self.retained(b'prefix'+frame(1)+b'\n'+frame(2)+b'suffix')
        self.assertEqual(result['status'],'PASS_NATIVE_LOG_RETENTION')
        self.assertEqual(result['records'][0]['offset'],6)
        for field in ('debian_early_pid1','installed_debian_pid1','absence_proves_nonexecution','replay_authorized'):
            self.assertFalse(result[field])

    def test_partial_torn_and_absent_records_do_not_gain_completion(self):
        for raw in (b'',frame(1),frame(1)[:-1],frame(1)+frame(2)[:-1]):
            with self.subTest(raw=raw[:8]):self.assertFalse(self.retained(raw)['post_return_retention_proved'])

    def test_foreign_run_and_mixed_boot_do_not_join_live_bytes(self):
        for raw in (frame(1,run=b'F'*16)+frame(2),frame(1)+frame(2,boot=b'B'*16)):
            self.assertFalse(self.retained(raw)['post_return_retention_proved'])

    def test_duplicates_and_reversed_order_reject(self):
        for raw in (frame(1)*2+frame(2),frame(2)+frame(1)):
            with self.assertRaises(ValueError):self.retained(raw)

    def test_bad_authentication_preserves_damage_and_blocks_complete(self):
        damaged=bytearray(base64.b64decode(frame(1)[8:-1]));damaged[-1]^=1
        bad=protocol.PREFIX+base64.b64encode(damaged)+b']'
        result=self.retained(bad+frame(1)+frame(2))
        self.assertEqual(len(result['damaged_candidates']),1);self.assertFalse(result['post_return_retention_proved'])

    def test_negative_live_backend_cannot_be_promoted_by_post_return_pair(self):
        negative=live(fixture().replace(b'errno=0 attempted',b'errno=5 attempted'))
        self.assertFalse(negative['live_pair_proved'])
        self.assertFalse(self.retained(frame(1)+frame(2),negative)['post_return_retention_proved'])

    def test_incomplete_and_contradictory_output_reject(self):
        for raw in (fixture()[:-1],fixture().replace(b'pre_ring=1',b'pre_ring=0'),
                fixture().replace(b'pre_count=1',b'pre_count=0'),fixture().replace(b'post_offset=159',b'post_offset=2'),
                fixture().replace(b'LC1_STEP stage=3\n',b''),fixture().replace(b'LC1_RETURN errno=0',b'LC1_RETURN errno=5')):
            with self.subTest(raw=raw[-60:]),self.assertRaises(ValueError):live(raw)

    def test_profile_requires_real_terminal_accounting_and_settlement(self):
        selected=object.__new__(profile.Profile);selected.key=KEY;selected.run=RUN
        selected.binding=dict(helper=dict(sha256=HELPER))
        stdout=fixture();terminal=(5,0,0,0,len(stdout),0)
        self.assertTrue(selected.project(stdout,b'',terminal,requested=True)['helper_settled'])
        for bad in (None,(5,0,0,1,len(stdout),0),(5,1,0,0,len(stdout),0),(5,0,0,0,len(stdout)-1,0),
                (5,0,0,0,len(stdout),1)):
            self.assertEqual(selected.project(stdout,b'',bad,requested=True)['status'],'NO_PROOF')
        self.assertEqual(selected.project(stdout,b'',terminal,requested=False)['status'],'NO_PROOF')

    def test_bounds_are_finite(self):
        for raw in (b'x'*(protocol.MAXIMUM+1),protocol.PREFIX*513):
            with self.assertRaises(ValueError):self.retained(raw)

    def test_same_native_boot_and_unique_pre_exec_intent_are_required(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory=Path(tmp);journal=records.Journal(directory/'journal')
            image=dict(run_id_hex=RUN.hex());body=b'fixed-command'
            proof=dict(kernel_boot_identity_sha256='11'*32,nonce_sha256='22'*32,
                log_calibration=dict(status='PASS_LOG_CALIBRATION_OBSERVED',kernel_boot_identity_sha256='11'*32))
            detail=dict(mode='fixed-extra',sequence=5,body_sha256=records.digest(body),run_id_hex=RUN.hex(),
                nonce_sha256='22'*32,kernel_boot_identity_sha256='11'*32)
            journal.append('effect-intent',step='install-native-first',action='transfer',role='N',detail={})
            journal.append('effect-intent',step=profile.SELECTION,action='observe',role='N',detail=detail)
            adapter=SimpleNamespace(directory=directory);step=SimpleNamespace(name=profile.SELECTION)
            request=dict(operation=profile.OPERATION,N=image)
            class Fixed:
                RESULT_KEY='log_calibration'
                def __init__(self,image):self.BODY=body
            with mock.patch.object(profile,'Profile',Fixed):
                scope.validate_result(adapter,step,dict(proof=proof),request)
                proof['log_calibration']['kernel_boot_identity_sha256']='ff'*32
                with self.assertRaises(ValueError):scope.validate_result(adapter,step,dict(proof=proof),request)


class Scope(unittest.TestCase):
    def task(self):
        return dict(N=dict(profile=profile.PROFILE),operations=[profile.OPERATION],E=None,
            admission=None,prior_terminal=None,recovery_mode='attended',operation_budget=1,
            seconds=1800,reentry=False,hud=False,usb_reconnect=False,target={},A={})

    def test_only_one_exact_attended_android_origin_operation(self):
        with mock.patch.object(profile,'image_binding'),mock.patch.object(scope,'android_basis_for_image'):
            scope.validate_task(self.task())
            for field,value in (('seconds',1799),('operation_budget',2),('recovery_mode','deferred'),
                    ('E',{}),('admission',{}),('prior_terminal',{}),('reentry',True),('hud',True),
                    ('usb_reconnect',True),('operations',[profile.OPERATION,'bootstrap'])):
                selected=self.task();selected[field]=value
                with self.subTest(field=field),self.assertRaises(ValueError):scope.validate_task(selected)

    def test_recovery_does_not_reread_uncertain_candidate_payload(self):
        with mock.patch.object(profile,'image_binding',side_effect=FileNotFoundError),\
                mock.patch.object(scope,'android_basis_for_image'):
            with self.assertRaises(FileNotFoundError):scope.validate_task(self.task())
            scope.validate_task(self.task(),recovery=True)

    def test_composition_inherits_only_the_proved_drain_carrier(self):
        import s22plus_native_baseline_v2_candidates as catalog
        import s22plus_native_log_source_v1 as source
        declared=catalog.declaration('p9000','99'*16,'v0.1.0','aa'*32,runtime_source=source)
        self.assertEqual(catalog.research_profile(declared),profile.PROFILE)
        for attribute,value in (('ROOT_INSPECT_PROFILE','foreign'),('STORAGE_PROFILE','foreign'),
                ('CONSOLE_PROFILE','foreign'),('DEBIAN_HANDOFF_PROFILE','foreign')):
            changed=copy.copy(declared);setattr(changed,attribute,value)
            with self.subTest(attribute=attribute),self.assertRaises(ValueError):catalog.research_profile(changed)


class Transport(transport_test.RootInspectionObservationTests):
    profile=profile
    fixture=staticmethod(fixture)
    binding=dict(helper=dict(sha256=HELPER))
    command_prefix='exec /s22-log-calibration calibrate '
    result_key='log_calibration'
    expected_status='PASS_LOG_CALIBRATION_OBSERVED'

    def test_truncated_science_stays_unproved_despite_completed_zero_exit_and_detach(self):
        import test_s22plus_native_observation_v3 as base
        with mock.patch.object(profile,'image_binding',return_value=self.binding),self.running() as ctx:
            (ctx.folder/'inspection.bin').write_bytes(fixture().split(b'LC1_BACKEND_POST')[0])
            value=observation.observe(ctx.folder/'negative',self.image,base.HostFixture(ctx),ending='detach',hud=False,
                guard=lambda:None,before_terminal=lambda:None,before_extra=lambda detail:None,first_boot=True,
                profile=profile.SELECTION)
            self.assertTrue(value['proof']['detach_ack_observed'])
            self.assertEqual(value['proof']['log_calibration']['status'],'NO_PROOF')


class Device(harness.DeviceFixture):
    def observe(self,step,request,*,guard,before_terminal,before_extra=None,consume_observation=None):
        guard();self.assert_mode('N');self.actions.append('calibration-health')
        if self.health_failure:raise ValueError('native health missing')
        if self.fail_before==step.name:raise ValueError('before helper dispatch')
        if not callable(before_extra):raise ValueError('missing durable intent')
        before_extra(dict(mode='fixed-extra',sequence=5));self.actions.append('calibration-once')
        if self.fail_after==step.name:raise OSError('helper may have run; output lost')
        before_terminal();return self.proof(step)


class Owner(unittest.TestCase):
    setUp=harness.OwnerTests.setUp

    def operation(self,device=None):
        device=device or Device()
        directory=owner.prepare_operation(self.root,self.grant,operation=profile.OPERATION,adapter=device)
        return owner.Session(self.root,directory,device),device

    def test_exact_graph_one_command_and_physical_a(self):
        self.assertEqual([s.name for s in phased.normal_steps()],
            ['android-download','install-native-first','log-calibration','install-android','android-final'])
        session,device=self.operation();result=session.execute(attended=True)
        self.assertEqual(result['state'],'AWAITING_PHYSICAL_DOWNLOAD');self.assertEqual(device.installed,['N'])
        device.mode='Download';session.resume(attended=True)
        self.assertEqual(device.installed,['N','A']);self.assertEqual(device.actions.count('calibration-once'),1)
        self.assertEqual(device.admitted,0);self.assertIsNone(self.f1)
        with self.assertRaises(ValueError):session.execute(attended=True)

    def test_uncertain_helper_stops_until_original_recovery_without_replay(self):
        session,device=self.operation();device.fail_after=profile.SELECTION
        self.assertEqual(session.execute(attended=True)['state'],'AWAITING_ATTENDED_RECOVERY')
        with self.assertRaises(ValueError):session.resume(attended=True)
        session.recover(attended=True)
        self.assertEqual(device.installed,['N','A']);self.assertEqual(device.actions.count('calibration-once'),1)

    def test_proved_a_health_retry_does_not_repeat_transfer_or_helper(self):
        session,device=self.operation();session.execute(attended=True);device.mode='Download';device.health_failure=True
        self.assertEqual(session.resume(attended=True)['state'],'AWAITING_ATTENDED_RECOVERY')
        device.health_failure=False;session.recover(attended=True)
        self.assertEqual(device.installed,['N','A']);self.assertEqual(device.actions.count('calibration-once'),1)

    def test_uncertain_a_never_replays(self):
        session,device=self.operation()
        with self.assertRaises(ValueError):session.execute(attended=False)
        session.execute(attended=True);device.mode='Download';device.fail_after='install-android'
        self.assertEqual(session.resume(attended=True)['state'],'AWAITING_ATTENDED_RECOVERY')
        with self.assertRaises((ValueError,KeyError)):session.recover(attended=True)
        self.assertEqual(device.installed,['N','A'])


class ReturnedProjection(unittest.TestCase):
    def project(self,*,changed_boot=False,duplicate=False,no_live=False):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);taskdir=root/'task';taskdir.mkdir();directory=root/'capture';directory.mkdir()
            operation=root/'operation';operation.mkdir();key=root/'key';key.write_bytes(KEY)
            task=dict(N=dict(profile=profile.PROFILE,run_id_hex=RUN.hex(),key=records.pin(key)),target={},A={})
            task_receipt=records.publish(taskdir/'task.json',task)
            op=records.publish(operation/'operation.json',{})
            returned=records.publish(root/'returned.json',dict(boot_id_sha256='a'*64))
            final=records.publish(root/'final.json',dict(health=returned))
            outcome=records.publish(operation/'terminal.json',dict(operation_record=op,terminal_result=final,
                log_calibration=dict(status='NO_PROOF') if no_live else live()))
            closed=records.publish(taskdir/'closed.json',dict(current_android_terminal=outcome))
            records.publish(directory/'started.json',dict(schema='s22plus-native-log-retention-d0-v1',
                task=task_receipt,closed=closed,device_effects=0))
            healths={}
            for side in ('before','after'):
                (directory/side).mkdir();boot='b'*64 if side=='after' and changed_boot else 'a'*64
                healths[side]=dict(properties=dict(boot=boot),boot_id_sha256=boot,captures=[side])
                records.publish(directory/side/'health.json',healths[side])
            (directory/'transport').mkdir()
            retention.raw.publish_captured_bytes(directory/'transport','features',stdout=b'shell_v2\n')
            raw=frame(1)+frame(2)+(frame(2) if duplicate else b'')
            handle=retention.raw.publish_captured_bytes(directory,'last-kmsg',stdout=raw)
            before={str(p):p.read_bytes() for p in root.rglob('*') if p.is_file()}
            def denied(*args,**kwargs):raise AssertionError('H0 projection attempted device/process access')
            with mock.patch.object(retention,'private_path',side_effect=lambda base,p,**kw:Path(p)),\
                    mock.patch.object(retrieval,'closed_operation',return_value=dict(task=task,closed=closed)),\
                    mock.patch.object(profile,'image_binding',return_value=dict(helper=dict(sha256=HELPER))),\
                    mock.patch.object(retention.target,'health_projection',side_effect=lambda captures,*args:healths[captures[0]]),\
                    mock.patch.object(retention.raw,'acquire_command',side_effect=denied),\
                    mock.patch.object(subprocess,'run',side_effect=denied),mock.patch.object(subprocess,'Popen',side_effect=denied):
                if changed_boot or duplicate:
                    with self.assertRaises(ValueError):retention.log_projection(directory,taskdir)
                    result=None
                else:result=retention.log_projection(directory,taskdir)
            self.assertEqual(before,{str(p):p.read_bytes() for p in root.rglob('*') if p.is_file()})
            self.assertEqual(retention.raw.read_stdout(handle,maximum=4*1024**2),raw)
            return result

    def test_rederive_same_returned_boot_without_process_or_device_access(self):
        self.assertEqual(self.project()['status'],'PASS_NATIVE_LOG_RETENTION')

    def test_changed_returned_boot_stops(self):self.project(changed_boot=True)

    def test_parser_failure_preserves_raw_and_consumed_records(self):self.project(duplicate=True)

    def test_missing_live_command_never_becomes_retention_proof(self):
        result=self.project(no_live=True)
        self.assertEqual(result['status'],'NO_LIVE_CALIBRATION_EVIDENCE')
        self.assertFalse(result['post_return_retention_proved'])


if __name__=='__main__':unittest.main()

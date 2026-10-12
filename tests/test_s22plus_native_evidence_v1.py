"""Bounded home-block records, strict negatives and one-shot recovery."""
import hashlib
from pathlib import Path
import struct
import sys
import unittest
from unittest import mock
import test_s22plus_native_root_inspect_v1 as root
import test_s22plus_native_session_v3 as harness
import s22plus_native_evidence_profile_v1 as profile
import s22plus_native_root_inspect_session_v1 as protected
import s22plus_native_session_v3 as owner
import s22plus_native_baseline_v2_candidates as candidates
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'workspace/public/src/scripts/analysis'))
import s22plus_native_evidence_build_v1 as builder

BINDING=dict(record_run=None)


def child(*,dirty=False,record_run=None):
    paths=profile.paths(record_run)
    raw=bytearray(b'S22NE01\0'+struct.pack('<4I',len(paths),1,int(dirty),0)+b'\0'*8)
    for ordinal,(_,mode,gid,maximum,capture) in enumerate(paths):
        data=b'2\n' if ordinal==0 else b''
        row=bytearray(96)
        struct.pack_into('<2IQ6IQI',row,0,ordinal,0,0,100+ordinal,mode,0,gid,1,0,len(data),len(data))
        row[64:96]=hashlib.sha256(data).digest()
        raw+=row+data
    raw+=b'S22NEND\0'+struct.pack('<Q4I',65536,16,0,len(raw)+32,0)
    return bytes(raw)


def fixture(*,dirty=False,raw=None):
    raw=child(dirty=dirty) if raw is None else raw
    rows=['RI1_BEGIN version=1','RI1_BIND exact=1','RI1_BLOCK_RO partition=1',
        f'RI1_SUPER clean={int(not dirty)} state=1 recover={int(dirty)} orphan=0',
        'NE1_READ mount=0 replay=0 output_max=24576']
    for name,data in (('stdout',raw),('stderr',b''),('setup',struct.pack('<II',100,0))):
        rows.append(f'UP1_OUTPUT stream={name} bytes={len(data)} hex={data.hex() or "-"}')
    rows+=['UP1_CHILD attempted=1 reaped=1 adopted=0 settled=1 status=0 setup_stage=100 setup_errno=0 error=0 proved=1',
        'RI1_FINAL super_unchanged=1 gpt_unchanged=1 partition_ro=1',
        f'RI1_RESULT complete=1 stage=10 errno=0 cleanup_errno=0 partition_ro=1 clean={int(not dirty)} mounted=0 unmounted=0']
    return ('\n'.join(rows)+'\n').encode()


def absent(raw,error=profile.FILE_NOT_FOUND):
    raw=bytearray(raw);row=bytearray(96);struct.pack_into('<IIQ',row,0,0,1,error)
    raw[32:130]=row
    struct.pack_into('<I',raw,len(raw)-8,len(raw))
    return bytes(raw)


class EvidenceTests(unittest.TestCase):
    def test_clean_and_dirty_capture_never_claim_execution_or_mount(self):
        for dirty in (False,True):
            value=profile.decode(fixture(dirty=dirty),b'',BINDING)
            self.assertEqual(value['files'][0]['raw_hex'],b'2\n'.hex())
            self.assertEqual(value['source_view_clean'],not dirty)
            for key in ('mounted','persistent_writes','debian_boot_proved','latest_state_complete','absence_proves_nonexecution'):
                self.assertFalse(value[key])

    def test_absent_home_block_record_is_observation_only(self):
        value=profile.decode(fixture(dirty=True,raw=absent(child(dirty=True))),b'',BINDING)
        self.assertEqual(value['files'][0]['status'],'ABSENT_IN_HOME_VIEW')
        self.assertFalse(value['absence_proves_nonexecution'])
        with self.assertRaises(ValueError):profile.decode_child(absent(child(),5))

    def test_optional_run_is_fixed_and_bounded(self):
        run='a'*32
        self.assertEqual(len(profile.decode_child(child(record_run=run),run)['files']),13)
        for bad in ('../etc/shadow','A'*32,'0'*31,'0'*33):
            with self.subTest(run=bad),self.assertRaises(ValueError):profile.paths(bad)
        with self.assertRaises(ValueError):profile.decode_child(child(record_run=run))

    def test_truncated_reordered_and_unaccounted_binary_records_reject(self):
        good=child();bad=[]
        for offset,value in ((8,99),(32,1),(32+52,1),(32+48,33),(len(good)-12,1),(len(good)-8,len(good)-1)):
            raw=bytearray(good);struct.pack_into('<I',raw,offset,value);bad.append(bytes(raw))
        bad.extend((good[:-1],good+b'\0',good[:128]+b'3\n'+good[130:]))
        for raw in bad:
            with self.subTest(raw=raw[:40]),self.assertRaises(ValueError):profile.decode_child(raw)

    def test_oversize_requires_valid_regular_file_metadata(self):
        raw=bytearray(absent(child()));struct.pack_into('<I',raw,36,4);struct.pack_into('<Q',raw,40,0)
        struct.pack_into('<6IQ',raw,48,100,0o100644,0,0,1,0,33)
        self.assertEqual(profile.decode_child(raw)['files'][0]['status'],'OVERSIZE')
        for offset,value in ((48,0),(52,0o120777),(56,1),(60,1),(64,2)):
            bad=bytearray(raw);struct.pack_into('<I',bad,offset,value)
            with self.subTest(offset=offset),self.assertRaises(ValueError):profile.decode_child(bad)

    def test_read_and_call_budgets_are_independent(self):
        for offset,value in ((-24,64*1024*1024+1),(-16,16385)):
            raw=bytearray(child());struct.pack_into('<Q' if offset==-24 else '<I',raw,len(raw)+offset,value)
            with self.assertRaises(ValueError):profile.decode_child(raw)

    def test_outer_zero_exit_cannot_replace_settlement_and_protection(self):
        image=dict(run_id_hex='1'*32,root_evidence=BINDING)
        with mock.patch.object(profile,'image_binding',return_value={}):p=profile.Profile(image)
        good=fixture();end=(5,0,0,0,len(good),0,0)
        self.assertEqual(p.project(good,b'',end,requested=True)['status'],'PASS_ROOT_EVIDENCE_OBSERVED')
        bad=[good[:-1],good+b'extra\n',good.replace(b'partition=1',b'partition=0'),
            good.replace(b'settled=1',b'settled=0'),good.replace(b'adopted=0',b'adopted=1'),
            good.replace(b'cleanup_errno=0',b'cleanup_errno=5'),good.replace(b'mounted=0',b'mounted=1'),
            good.replace(b'gpt_unchanged=1',b'gpt_unchanged=0'),good.replace(b'clean=1 state=1 recover=0',b'clean=1 state=1 recover=1')]
        for raw in bad:
            with self.subTest(raw=raw[:50]):
                self.assertEqual(p.project(raw,b'',(5,0,0,0,len(raw),0,0),requested=True)['status'],'NO_PROOF')
        for end in (None,(5,1,0,0,len(good),0,0),(5,0,0,0,len(good)-1,0,0)):
            self.assertEqual(p.project(good,b'',end,requested=True)['status'],'NO_PROOF')


class ScopeTests(unittest.TestCase):
    def test_sealed_record_selection_reaches_helper_and_image(self):
        run='a'*32
        declared=candidates.declaration('p999','b'*32,'v1.0.0','c'*64,
            runtime_source=candidates.evidence_source,evidence_run=run)
        image=builder.Builder(declared)
        self.assertEqual(image.native_selection()['runtime_profile']['root_evidence']['record_run'],run)
        with mock.patch.object(builder.previous.Builder,'runtime_value',return_value={}):
            self.assertEqual(image.runtime_value(Path('/fixture'),{}, {})['profile']['root_evidence']['record_run'],run)
        with mock.patch.object(builder.previous.previous.Builder,'build_native_init'), \
                mock.patch.object(builder.producer,'build') as build, \
                mock.patch.object(builder.producer,'audit') as audit:
            image.build_native_init(Path('/fixture'),False);image.inspection_value(Path('/fixture'))
            self.assertEqual(build.call_args.kwargs['record_run'],run)
            self.assertEqual(audit.call_args.kwargs['record_run'],run)
        for kwargs in (dict(evidence_run='../etc/shadow',runtime_source=candidates.evidence_source),
                dict(evidence_run=run,runtime_source=candidates.journal_source)):
            with self.assertRaises(ValueError):candidates.declaration('p999','b'*32,'v1.0.0','c'*64,**kwargs)

    def test_one_attended_reader_and_original_a_only(self):
        task=root.ScopeTests().task();task['N']['profile']=profile.PROFILE;task['operations']=[profile.OPERATION]
        with mock.patch.object(profile,'image_binding'),mock.patch.object(protected,'android_basis_for_image'):
            protected.validate_task(task)
            for key,value in [('operations',['journal-recovery']),('operations',[profile.OPERATION,'debian-handoff']),
                ('E',{}),('admission',{}),('prior_terminal',{}),('operation_budget',2),('seconds',1801),
                ('recovery_mode','deferred'),('reentry',True),('hud',True),('usb_reconnect',True)]:
                with self.subTest(key=key),self.assertRaises(ValueError):protected.validate_task(dict(task,**{key:value}))
        self.assertEqual([s.name for s in owner.steps(profile.OPERATION)],
            ['android-download','install-native-first','root-evidence','inspector-return','install-android','android-final'])


class Device(harness.DeviceFixture):
    def observe(self,step,request,*,guard,before_terminal,consume_observation=None,before_extra=None):
        if step.name==profile.SELECTION:
            guard();self.assert_mode('N')
            if not callable(before_extra):raise ValueError('partition control has no durable intent')
            before_extra(dict(mode='fixed-extra',sequence=5));self.actions.append('reader-once')
            if self.fail_after==step.name:raise OSError('reader response lost after EXEC')
            before_terminal();return self.proof(step)
        return super().observe(step,request,guard=guard,before_terminal=before_terminal,consume_observation=consume_observation)


class OwnerTests(unittest.TestCase):
    setUp=harness.OwnerTests.setUp
    def test_uncertain_reader_has_one_a_return_and_no_replay(self):
        device=Device();directory=owner.prepare_operation(self.root,self.grant,operation=profile.OPERATION,adapter=device)
        session=owner.Session(self.root,directory,device);device.fail_after=profile.SELECTION
        result=session.execute(attended=True)
        self.assertTrue(result['recovered']);self.assertEqual(device.installed,['N','A'])
        self.assertEqual(device.actions.count('reader-once'),1);self.assertEqual(device.admitted,0)
        self.assertIsNone(self.f1)
        with self.assertRaises(ValueError):session.execute(attended=True)
        self.assertEqual(device.installed,['N','A'])

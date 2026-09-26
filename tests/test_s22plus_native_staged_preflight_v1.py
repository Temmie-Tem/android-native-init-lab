"""Synthetic stage transcripts test ordering, semantic negatives and no replay."""
import struct
import unittest
from unittest import mock
import test_s22plus_native_root_inspect_v1 as root
import test_s22plus_native_session_v3 as harness
import s22plus_native_staged_preflight_profile_v1 as profile
import s22plus_native_root_inspect_session_v1 as protected
import s22plus_native_session_v3 as owner

BINDING=root.BINDING
STEPS=('setup','binding','block-ro','superblock','checker','mount','markers','inventory','comparison',
       'eligibility','loader-inputs','loader-verify','loader-list','parent-protection','unmount','final-binding','cleanup')
LIBS=('linux-vdso.so.1','libselinux.so.1 => /lib/aarch64-linux-gnu/libselinux.so.1',
      'libc.so.6 => /lib/aarch64-linux-gnu/libc.so.6','/lib/ld-linux-aarch64.so.1',
      'libpcre2-8.so.0 => /lib/aarch64-linux-gnu/libpcre2-8.so.0')


def fixture(*,clean=True,eligible=True,negative=None):
    raw=root.fixture(clean=clean).decode().splitlines()
    raw=[s.replace('entries=6 files=3','entries=7 files=4') for s in raw]
    records={s.split()[0]:s for s in raw}
    mapping={'binding':'RI1_BIND','block-ro':'RI1_BLOCK_RO','superblock':'RI1_SUPER','mount':'RI1_MOUNT',
        'markers':'RI1_MARKERS','inventory':'RI1_TREE','comparison':'RI1_COMPARE','unmount':'RI1_UNMOUNT','final-binding':'RI1_FINAL'}
    steps=list(STEPS)
    if not clean:steps=list(STEPS[:4])+list(STEPS[-2:])
    elif negative=='checker':steps=list(STEPS[:5])+list(STEPS[-2:])
    elif not eligible:steps=list(STEPS[:10])+list(STEPS[-3:])
    elif negative=='loader-verify':steps.remove('loader-list')
    rows=[records['RI1_BEGIN']];seq=0;children=passed=0
    for step in steps:
        seq+=1;rows.append(f'SP1_STAGE seq={seq} step={step} phase=begin errno=0')
        if step in mapping:rows.append(records[mapping[step]])
        if step=='eligibility':rows.append(f'SP1_ELIGIBLE exact={int(eligible)}')
        phase='stop' if step==negative or step=='eligibility' and not eligible else 'pass'
        if step in ('checker','loader-verify','loader-list'):
            children+=1;ok=step!=negative;passed+=ok
            out=(b''.join(f'Pass {i}: fixed\n'.encode() for i in range(1,6)) if step=='checker' else
                 b''.join(f'\t{line} (0x1)\n'.encode() for line in LIBS) if step=='loader-list' else b'')
            err=b'e2fsck fixed\n' if step=='checker' else b'';setup=struct.pack('<II',100,0)
            for name,data in [('stdout',out),('stderr',err),('setup',setup)]:
                rows.append(f'UP1_OUTPUT stream={name} bytes={len(data)} hex={data.hex() or "-"}')
            rows.append(f'UP1_CHILD attempted=1 reaped=1 adopted=0 settled=1 status={0 if ok else 1024} '
                f'setup_stage=100 setup_errno=0 error=0 proved={int(ok)}')
        seq+=1;rows.append(f'SP1_STAGE seq={seq} step={step} phase={phase} errno=0')
    final=records['RI1_RESULT']
    if negative=='checker':final=final.replace('mounted=1 unmounted=1','mounted=0 unmounted=0')
    rows += [final,f'SP1_RESULT complete=1 children={children} passed={passed} stopped={int(clean and (not eligible or negative is not None))}']
    return ('\n'.join(rows)+'\n').encode()


class EvidenceTests(unittest.TestCase):
    def test_complete_only_proves_protected_preparation(self):
        result=profile.decode(fixture(),b'',BINDING)
        self.assertTrue(result['preparation_proved']);self.assertEqual(len(result['children']),3)
        self.assertFalse(result['pid1_handoff']);self.assertFalse(result['debian_boot_proved'])

    def test_stops_skip_later_work_but_keep_final_storage_cleanup(self):
        for options,verdict,count in [({'clean':False},'SKIPPED_UNCLEAN_ROOT',0),
                ({'negative':'checker'},'CHECKER_NOT_PROVED',1),({'eligible':False},'SKIPPED_ROOT_NOT_EXACT',1),
                ({'negative':'loader-verify'},'LOADER_NOT_PROVED',2),({'negative':'loader-list'},'LOADER_NOT_PROVED',3)]:
            with self.subTest(options=options):
                result=profile.decode(fixture(**options),b'',BINDING)
                self.assertEqual(result['verdict'],verdict);self.assertFalse(result['preparation_proved'])
                self.assertEqual(len(result['children']),count)

    def test_stage_or_child_injection_and_missing_settlement_reject(self):
        good=fixture();rows=good.splitlines(keepends=True)
        bad=[good.replace(b'partition=1',b'partition=0'),good.replace(b'settled=1',b'settled=0',1),
            good.replace(b'cleanup_errno=0',b'cleanup_errno=5'),good.replace(b'status=0',b'status=1024',1),
            good.replace(b'SP1_RESULT complete=1',b'SP1_RESULT complete=0'),good[:-1],good+b'unknown\n',
            b''.join(r for r in rows if not r.startswith(b'UP1_CHILD')),
            good.replace(b'step=binding phase=begin',b'step=setup phase=begin'),
            good.replace(b'RI1_BIND exact=1\n',b'').replace(b'RI1_BLOCK_RO partition=1',b'RI1_BIND exact=1\nRI1_BLOCK_RO partition=1')]
        self.assertTrue(all(x!=good for x in bad))
        for body in bad:
            with self.subTest(body=body):
                with self.assertRaises((ValueError,KeyError,IndexError)):profile.decode(body,b'',BINDING)

    def test_prefix_keeps_only_valid_markers_without_claiming_completion(self):
        body=fixture();prefix=body[:body.index(b'UP1_OUTPUT')]
        progress=profile.progress(prefix)
        self.assertEqual(progress['open_stage'],'checker');self.assertEqual(progress['last_passed'],'superblock')
        self.assertFalse(progress['session_completion_proved'])
        bad=prefix+b'SP1_STAGE seq=999 step=checker phase=pass errno=0\n'
        value=profile.progress(bad);self.assertEqual(value['stages'],progress['stages']);self.assertIsNotNone(value['diagnostic_error'])
        with self.assertRaises(ValueError):profile.progress(bad,complete=True)

    def test_zero_outer_exit_or_cleanup_marker_does_not_replace_complete_evidence(self):
        with mock.patch.object(profile,'image_binding',return_value=BINDING):fixed=profile.Profile(dict(run_id_hex='1'*32))
        body=fixture()
        self.assertTrue(fixed.project(body,b'',(5,0,0,0,len(body),0,0),requested=True)['preparation_proved'])
        for terminal in (None,(5,1,0,0,len(body),0,0),(5,0,0,0,len(body),1,0),(5,0,0,0,len(body)-1,0,0)):
            result=fixed.project(body,b'',terminal,requested=True)
            self.assertEqual(result['status'],'NO_PROOF');self.assertFalse(result['progress']['session_completion_proved'])


class ScopeTests(unittest.TestCase):
    def test_single_fixed_operation_scope(self):
        task=root.ScopeTests().task();task['N']['profile']=profile.PROFILE;task['operations']=[profile.OPERATION]
        with mock.patch.object(profile,'image_binding'),mock.patch.object(protected,'android_basis_for_image'):
            protected.validate_task(task)
            for key,value in [('operations',['preflight']),('E',{}),('admission',{}),('prior_terminal',{}),
                    ('operation_budget',2),('seconds',1801),('reentry',True),('hud',True),('usb_reconnect',True)]:
                bad=dict(task);bad[key]=value
                with self.subTest(key=key),self.assertRaises(ValueError):protected.validate_task(bad)


class Device(harness.DeviceFixture):
    def observe(self,step,request,*,guard,before_terminal,consume_observation=None,before_extra=None):
        if step.name==profile.SELECTION:
            guard();self.assert_mode('N');self.actions.append('health:'+step.name)
            if not callable(before_extra):raise ValueError('pre-EXEC owner absent')
            before_extra(dict(mode='fixed-extra',sequence=5));self.actions.append('staged-once')
            if self.fail_after==step.name:raise OSError('stage result lost after intended EXEC')
            before_terminal();return self.proof(step)
        return super().observe(step,request,guard=guard,before_terminal=before_terminal,consume_observation=consume_observation)


class OwnerTests(unittest.TestCase):
    setUp=harness.OwnerTests.setUp
    def test_uncertainty_never_repeats_workload_or_transfer(self):
        device=Device();directory=owner.prepare_operation(self.root,self.grant,operation=profile.OPERATION,adapter=device)
        session=owner.Session(self.root,directory,device);device.fail_after=profile.SELECTION
        result=session.execute(attended=True)
        self.assertTrue(result['recovered']);self.assertEqual(device.installed,['N','A'])
        self.assertEqual(device.actions.count('staged-once'),1);self.assertEqual(device.admitted,0)
        with self.assertRaises(ValueError):session.execute(attended=True)
        self.assertEqual(device.installed,['N','A'])

"""Complete filesystem proofs and real resident pre-EXEC intent ordering."""
from pathlib import Path
import sys
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'workspace/public/src/scripts/revalidation'),
                str(ROOT/'workspace/public/src/scripts/analysis')]
import s22plus_native_ext4_profile_v1 as fs
import s22plus_native_observation_v3 as observation
import s22plus_native_output_drain_source_v1 as drain
import s22plus_native_records_v3 as records
import s22plus_native_adapter_v3 as adapter
import s22plus_native_session_v3 as owner
import test_s22plus_native_observation_v3 as base
import test_s22plus_native_resident_v1 as producer


def output(mode):
    rows = []
    steps = [1] if mode == 0 else list(range(1,10)) if mode == 1 else [1,3,4,5,6,8,9]
    for step in steps:
        if step in (2,4):
            tool = 'format' if step == 2 else 'check'; rows.append(f'FS1_TOOL_BEGIN tool={tool}')
            if step == 4:
                rows += ['Pass 1: Checking inodes, blocks, and sizes', 'Pass 2: Checking directory structure',
                         'Pass 3: Checking directory connectivity', 'Pass 4: Checking reference counts',
                         'Pass 5: Checking group summary information',
                         f'S22DEBIAN: {11 if mode==1 else 12}/3139584 files (0.0% non-contiguous), 462287/50189568 blocks']
            rows.append(f'FS1_TOOL_END tool={tool} status=0 reaped=1')
        rows.append(f'FS1_STEP step={step} errno=0')
    rows.append(f'FS1_RESULT mode={mode} status=0 last={1 if mode==0 else 9} failed=0 errno=0 '
                f'formatted={int(mode==1)} mounted={int(mode!=0)} witness={int(mode!=0)} '
                f'synced={int(mode==1)} unmounted={int(mode!=0)} cleanup_attempted=0 cleanup_failed=0 '
                f'cleanup_errno=0 helper_reaped={int(mode!=0)} helper_status=0 blocks=50189568')
    return ('\n'.join(rows)+'\n').encode()


class ProfileTests(unittest.TestCase):
    def test_all_modes_require_their_complete_ordered_proof(self):
        for mode, selection in enumerate(fs.SELECTIONS):
            image=dict(profile=fs.INITIALIZER_PROFILE if mode==1 else fs.READER_PROFILE,run_id_hex='1'*32)
            profile=fs.Profile(image,selection); out=output(mode); err=fs.CHECKER_STDERR if mode else b''
            terminal=(5,0,0,0,len(out)+len(err),0,1)
            good=profile.project(out,err,terminal,requested=True)
            self.assertTrue(good['status'].startswith('PASS_'));self.assertFalse(good['fresh_boot_proved'])
            for bad in (out[:-1],out+b'extra\n',out.replace(b'errno=0',b'errno=5',1),
                        out.replace(b'blocks=50189568',b'blocks=50189567')):
                self.assertEqual(profile.project(bad,err,(5,0,0,0,len(bad)+len(err),0,1),requested=True)['status'],'NO_PROOF')
            self.assertEqual(profile.project(out,err,terminal,requested=False)['status'],'NO_PROOF')
            self.assertEqual(profile.project(out,err,(5,8,0,0,len(out)+len(err),0,1),requested=True)['status'],'NO_PROOF')
        with self.assertRaises(ValueError):fs.Profile(dict(profile=fs.READER_PROFILE,run_id_hex='1'*32),'filesystem-initialize')

    def test_wrong_checker_count_missing_reap_and_extra_output_reject(self):
        value=output(2)
        for bad in (value.replace(b'12/3139584',b'11/3139584'),value.replace(b'reaped=1',b'reaped=0'),
                    value.replace(b'0.0% non',b'...% non'),value.replace(b'FS1_STEP step=8 errno=0\n',b'')):
            with self.assertRaises(ValueError):fs.decode(bad,fs.CHECKER_STDERR,'filesystem-verify')


class ObservationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        base.ObservationTests.setUpClass.__func__(cls)
        cls.image=dict(cls.image,profile=fs.INITIALIZER_PROFILE)
        path=cls.folder/'native.c';text=drain.upgrade_native(path.read_bytes()).decode()
        marker='const char *command=text;';assert text.count(marker)==1
        text=text.replace(marker,marker+'''\n
 if(!strncmp(command,"exec /s22-fs initialize ",sizeof("exec /s22-fs initialize ")-1))
   command="test -f fs-intent && cat fs.stdout && cat fs.stderr >&2";
''')
        path.write_text(text)
        producer.compile_c(path,cls.binary,'-Wno-unused-function','-Wno-unused-const-variable','-Wno-misleading-indentation')

    running=base.ObservationTests.running

    def test_actual_c_execution_follows_durable_intent_and_replays_all_output(self):
        with self.running() as ctx:
            (ctx.folder/'fs.stdout').write_bytes(output(1));(ctx.folder/'fs.stderr').write_bytes(fs.CHECKER_STDERR)
            calls=[]
            def intent(request):
                calls.append(request);records.publish(ctx.folder/'fs-intent',request)
            directory=ctx.folder/'initialize'
            value=observation.observe(directory,self.image,base.HostFixture(ctx),ending='detach',hud=False,
                guard=lambda:None,before_terminal=lambda:None,before_extra=intent,first_boot=True,
                profile='filesystem-initialize')
            self.assertEqual(len(calls),1);self.assertEqual(calls[0]['sequence'],5)
            self.assertEqual(value['proof']['filesystem']['status'],'PASS_INITIALIZED_WRITTEN_CLEAN_UNMOUNT')
            opened=records.read(directory/'open.json')
            self.assertGreater(opened['deadline_ns']-opened['boottime_ns'],290_000_000_000)
            self.assertEqual(value,observation.rederive(directory,self.image,ending='detach',hud=False,
                first_boot=True,profile='filesystem-initialize'))

    def test_failed_intent_prevents_format_exec_and_missing_callback_prevents_open(self):
        with self.running() as ctx:
            callback=mock.Mock(side_effect=OSError('journal unavailable'));directory=ctx.folder/'blocked'
            with self.assertRaises(OSError):
                observation.observe(directory,self.image,base.HostFixture(ctx),ending='detach',hud=False,
                    guard=lambda:None,before_terminal=lambda:None,before_extra=callback,first_boot=True,
                    profile='filesystem-initialize')
            self.assertNotIn(fs.Profile(self.image,'filesystem-initialize').BODY,(directory/'tx.bin').read_bytes())
            self.assertEqual(callback.call_count,1)
            with self.assertRaisesRegex(ValueError,'durable owner callback'):
                observation.observe(ctx.folder/'no-owner',self.image,base.HostFixture(ctx),ending='detach',hud=False,
                    guard=lambda:None,before_terminal=lambda:None,first_boot=True,profile='filesystem-initialize')
            self.assertFalse((ctx.folder/'no-owner').exists())

    def test_complete_negative_inspection_permits_recovery_but_missing_proof_keeps_h0_guard(self):
        with self.running() as ctx:
            image=dict(self.image,profile=fs.READER_PROFILE)
            selected=owner.Step('native-second-2','observe','N','detach')
            backend=adapter.Adapter.__new__(adapter.Adapter);backend.directory=ctx.folder
            directory=backend.folder(selected.name)
            # This fixture has no /s22-fs reader executable: EXEC completes with
            # an observed nonzero status, while fixed health and DETACH succeed.
            value=observation.observe(directory,image,base.HostFixture(ctx),ending='detach',hud=False,
                guard=lambda:None,before_terminal=lambda:None,first_boot=True,profile='filesystem-inspect')
            self.assertEqual(value['proof']['filesystem']['status'],'NO_PROOF')
            request=dict(operation='bootstrap',N=image)
            with mock.patch.object(backend,'recover_step_result',return_value=value):
                self.assertFalse(backend.final_protocol_completed(selected,request))
            with mock.patch.object(backend,'recover_step_result',side_effect=OSError('proof unavailable')):
                self.assertTrue(backend.final_protocol_completed(selected,request))


if __name__=='__main__':unittest.main()

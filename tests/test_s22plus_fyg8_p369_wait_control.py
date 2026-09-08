"""Actual generated PID1/observer with explicit platform and fixed wait fixtures."""
from pathlib import Path
import copy,json,os,subprocess,sys,time,types,unittest
from unittest import mock
import test_s22plus_fyg8_p361_renderer as renderer_fixture
import s22plus_fyg8_p369_display_renderer as renderer

fixture=types.ModuleType('_p369_joined_fixture')
fixture.__file__=str(Path('tests/test_s22plus_fyg8_p367_lifecycle.py').resolve())
sys.modules[fixture.__name__]=fixture
raw=Path(fixture.__file__).read_text().replace('p367','p369').replace('P367','P369')
exec(compile(raw,fixture.__file__+'#p369','exec'),fixture.__dict__)
live=fixture.live
support=fixture.parent.support
observer=support.observer


def source():
    value=support_source()
    value=value.replace('unsigned code=state->swaps;', 'if(fx_case("wait-young"))p241_clock_gettime(&state->wait_started);unsigned code=state->swaps;',1)
    start=value.index('if(!strcmp(p,"/s22-display")){')
    end=value.index('}return neg(execve(p,a,e));',start)+1
    return value[:start]+r'''if(!strcmp(p,"/s22-display")){
 fx_mark("child",0);
 if(fx_case("wait-stall"))for(;;)usleep(10000);
 for(unsigned i=1;i<=3;i++)dprintf(1,"DISPLAY_SWAP_SUBMITTED run=%s swap=%u ioctl_return=0 visible=UNPROVED\n",a[2],i);
 dprintf(1,"DISPLAY_WAIT_ENTERED run=%s after_swaps=3\n",fx_case("wait-wrong")?"00000000000000000000000000000000":a[2]);
 if(fx_case("wait-four"))dprintf(1,"DISPLAY_SWAP_SUBMITTED run=%s swap=4 ioctl_return=0 visible=UNPROVED\n",a[2]);
 if(fx_case("wait-exit"))_Exit(7);
 if(fx_case("wait-signal"))raise(SIGTERM);
 for(;;)usleep(10000);
}'''+value[end:]

support_source=support.console_source

class WaitLifecycle(fixture.P369JoinedLifecycle):
    test_actual_joined_success_and_diagnostic_failure_with_foreign_download=None
    test_native_payload_is_p366_identity_only=None
    test_client_restart_before_eof_resumes_without_transfer_replay=None
    test_after_eof_cut_preserves_fixed_outputs_and_fails_closed=None
    @classmethod
    def setUpClass(cls):
        with mock.patch.object(support,'console_source',side_effect=source):
            super().setUpClass()
    def patches(self):
        stack=super().patches()
        # Native fixture clock scales by30, so .4 host seconds gives12 native.
        stack.enter_context(mock.patch.object(observer.control,'OBSERVATION_INTERVAL_SEC',.4))
        return stack
    def test_wait_witness_and_failure_conditions_preserve_control(self):
        for case in ('wait-good','wait-stall','wait-wrong','wait-four','wait-exit','wait-signal','wait-young'):
            with self.subTest(case=case):
                p=self.prepared();backend=fixture.JoinedBackend(p,self.peer,case,foreign=True)
                with self.patches():
                    result=live.execute_prepared(p,p.approval_token,backend)
                    live.validate_live_result(result,p)
                self.assertEqual(result['current_state'],'CLOSED')
                self.assertFalse(result['recovery_required'])
                self.assertEqual(result['verdict'],'PASS_F1_V2_P369_NATIVE_RETURN_CONTROL_AND_ROLLED_BACK' if case=='wait-good' else 'NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK')
                self.assertIn('download 0',self.peer.last_marks)
                self.assertEqual(self.peer.last_marks.count('download 0'),1)
                self.assertEqual([c for c in backend.calls if c.startswith('transfer-')],['transfer-candidate','transfer-rollback'])
    def test_immediate_control_before_any_wait_marker(self):
        p=self.prepared();backend=fixture.JoinedBackend(p,self.peer,'wait-stall')
        with self.patches(),mock.patch.object(observer.control,'OBSERVATION_INTERVAL_SEC',0):
            result=live.execute_prepared(p,p.approval_token,backend)
        self.assertEqual(result['verdict'],'NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK')
        self.assertEqual(self.peer.last_marks.count('download 0'),1)
        self.assertEqual([c for c in backend.calls if c.startswith('transfer-')],['transfer-candidate','transfer-rollback'])

    def test_bad_control_mac_has_no_reboot_syscall(self):
        original_factory=live._open_header_initial_observer_module
        mutations=[];wires=[]
        def factory(*args,**kwargs):
            codec=original_factory(*args,**kwargs)
            if args[2]=='p369-real-console':
                original=codec._CODEC.encode_frame
                def encode(kind,sequence,payload):
                    if kind==observer.control.FRAME_CONTROL:
                        mutations.append((kind,sequence))
                        payload=payload[:-1]+bytes([payload[-1]^1])
                    wire=original(kind,sequence,payload)
                    if kind==observer.control.FRAME_CONTROL:wires.append(wire)
                    return wire
                codec._CODEC.encode_frame=encode
            return codec
        writer=types.SimpleNamespace(write_stdout=lambda data:None);intents=[]
        with mock.patch.object(observer.control,'OBSERVATION_INTERVAL_SEC',.4),mock.patch.object(live,'_open_header_initial_observer_module',side_effect=factory):
            result,error,audit,projection=self.peer.run('wait-good',writer,intents.append)
        self.assertIsNone(result);self.assertIsNotNone(error)
        # Native exchange plus deterministic retained-TX replay each encode it.
        self.assertEqual(mutations,[(observer.control.FRAME_CONTROL,5)]*2)
        self.assertEqual(len(intents),1)
        self.assertEqual(bytes(audit.tx).count(wires[0]),1)
        self.assertNotIn('download 0',self.peer.last_marks)

    def test_duplicate_control_cannot_repeat_syscall(self):
        factory_base=live._open_header_initial_observer_module;wires=[]
        def factory(*args,**kwargs):
            codec=factory_base(*args,**kwargs)
            if args[2]=='p369-real-console':
                encode_base=codec._CODEC.encode_frame
                def encode(kind,sequence,payload):
                    wire=encode_base(kind,sequence,payload)
                    if kind==observer.control.FRAME_CONTROL:
                        wires.append(wire);return wire+wire
                    return wire
                codec._CODEC.encode_frame=encode
            return codec
        writer=types.SimpleNamespace(write_stdout=lambda data:None)
        with mock.patch.object(observer.control,'OBSERVATION_INTERVAL_SEC',.4),mock.patch.object(live,'_open_header_initial_observer_module',side_effect=factory):
            result,error,audit,projection=self.peer.run('wait-good',writer,lambda request:None)
        self.assertEqual(bytes(audit.tx).count(wires[0]),2)
        self.assertEqual(self.peer.last_marks.count('download 0'),1)

    def test_checkpoint_raw_replay_and_no_delayed_replay(self):
        p=self.prepared();backend=fixture.JoinedBackend(p,self.peer,'wait-good')
        with self.patches():live.execute_prepared(p,p.approval_token,backend)
        proof=backend.fixture.proof;observer.validate_qualification(proof)
        checkpoint=proof['sessions'][0]['native_progress']['wait_checkpoint']
        self.assertEqual(checkpoint,dict(submitted_swaps=3,exact_wait_marker=True,marker_age_at_least_two_seconds=True,child_unreaped_at_control=True))
        for key in checkpoint:
            bad=copy.deepcopy(proof);bad['sessions'][0]['native_progress']['wait_checkpoint'][key]=False
            with self.assertRaises(ValueError):observer.validate_qualification(bad)

class RendererWait(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with mock.patch.object(renderer_fixture,'renderer',renderer):
            renderer_fixture.RendererTests.setUpClass.__func__(cls)
    def test_actual_renderer_remains_alive_after_three_submissions(self):
        path=Path(self.tmp.name)/'wait.stderr'
        with path.open('wb') as log:
            p=subprocess.Popen([self.binary,'success'],stdout=subprocess.DEVNULL,stderr=log)
            try:
                deadline=time.monotonic()+2
                while b'DISPLAY_WAIT_ENTERED' not in path.read_bytes() and time.monotonic()<deadline:
                    time.sleep(.01)
                self.assertIn(b'DISPLAY_WAIT_ENTERED',path.read_bytes())
                time.sleep(.1);self.assertIsNone(p.poll())
                self.assertEqual(path.read_bytes().count(b'DISPLAY_SWAP_SUBMITTED'),3)
                self.assertEqual(path.read_bytes().count(b'H0_ATOMIC_COUNT='),4)
            finally:
                if p.poll() is None:p.kill()
                p.wait(timeout=2)

if __name__=='__main__':unittest.main()

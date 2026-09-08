"""Actual common descriptor owner and paired raw validator, with a PTY/platform fixture."""
from pathlib import Path
import contextlib,errno,fcntl,json,os,pty,signal,subprocess,tempfile,time,tty,termios,types,unittest
from unittest import mock
import test_s22plus_fyg8_p370_handoff as native
from tests.test_s22plus_fyg8_p345_live_receipt import _ReceiptFixture,KEY_SHA256
from s22plus_native_departure_h0_support import Fixture

joined=types.ModuleType('_p370_joined_fixture');joined.__file__=str(Path('tests/test_s22plus_fyg8_p367_lifecycle.py').resolve());__import__('sys').modules[joined.__name__]=joined
raw=Path(joined.__file__).read_text().replace('p367','p370').replace('P367','P370')
exec(compile(raw,joined.__file__+'#p370','exec'),joined.__dict__)
live=joined.live
runtime=native.runtime;observer=native.observer;KEY=native.KEY

class NativePeer:
    def __init__(self,root):
        self.root=Path(root);self.binary=self.root/'unscaled-peer'
        source=native.source().replace('out->tv_sec=t.tv_sec*30+(t.tv_nsec*30)/1000000000;out->tv_nsec=(t.tv_nsec*30)%1000000000;', 'out->tv_sec=t.tv_sec;out->tv_nsec=t.tv_nsec;')
        source=source.replace("long rc=p241_clock_gettime(out);out->tv_sec+=seconds;return rc;", "long rc=p241_clock_gettime(out);if(rc)_Exit(104);out->tv_sec+=seconds;return rc;").replace("struct timespec64 d;p282_deadline_after(seconds,&d);", "struct timespec64 d={0};p282_deadline_after(seconds,&d);")
        source=source.replace('if(fx_case("wait-good")', 'if((fx_case("wait-good")||fx_case("resume-bad-ack"))')
        source=source.replace('return p370_handoff_write(fd,kind,sequence,payload,sizeof(payload),deadline);', 'if(kind==0x8eU && fx_case("resume-bad-ack"))payload[35]^=1U;return p370_handoff_write(fd,kind,sequence,payload,sizeof(payload),deadline);')
        p=subprocess.run(['cc','-x','c','-','-O2','-Wall','-Wextra','-Werror','-Wno-unused-function','-Wno-misleading-indentation','-o',str(self.binary)],input=source,text=True,capture_output=True,timeout=30)
        if p.returncode:raise AssertionError(p.stderr)
    def start(self,case):
        master,slave=pty.openpty();tty.setraw(slave);os.set_blocking(slave,False)
        path=Path(os.ttyname(slave));marks=self.root/('marks-'+str(time.monotonic_ns()))
        p=subprocess.Popen([self.binary,str(master),'1'],env=dict(os.environ,P364_CASE=case,P364_MARK=str(marks)),pass_fds=(master,),stderr=subprocess.PIPE,start_new_session=True)
        os.close(master);return p,slave,path,marks

class Receipt(joined.parent.fixture.Receipt):
    def observe(self,*,timeout_sec,download_departure):
        writer=live.raw_capture.RawCaptureWriter(self.run_dir,'candidate-observer',stdout_maximum=live.P327_MAX_RAW_BYTES,stderr_maximum=1,argv0_name='p370-actual-owner-pty',stdout_name='candidate-observer.raw',stderr_name='candidate-observer.raw.stderr')
        p,bootstrap,path,marks=self.peer.start('resume-bad-ack' if self.case=='resume-bad-ack' else 'wait-good');held=[bootstrap];owner_calls=[]
        platform=Fixture(self.run_dir/'native-platform');endpoint=platform.endpoint;endpoint.tty_name=path.name
        session=live._P370ObserverSession.__new__(live._P370ObserverSession)
        session.namespace='p370';session.run_dir=self.run_dir;session.auth_key=KEY;session.auth_key_sha256=KEY_SHA256
        session.auth_runtime=runtime;session.qualification_observer=observer;session.proof_key=self.variant.proof_key
        session.receipt_schema='s22plus_fyg8_p370_shell_qualification_acm_receipt_v1';session.receipt_label='P370 H0 actual owner'
        session.base=types.SimpleNamespace(dev_root=path.parent,binding=live._candidate_observer_binding(self.prepared),_raw_tty=lambda fd:tty.setraw(fd))
        session._settle_guard_properties=lambda *_:None
        def exact(ep,fd=None):
            owner_calls.append(('exact',fd))
            if fd is not None:
                if os.fstat(fd).st_rdev!=os.stat(path).st_rdev:return False
                if held[0] is not None:os.close(held[0]);held[0]=None
            return True
        session._endpoint_exact=exact
        lane=self._lane()
        opens=[];ioctls=[];real_open=os.open;real_ioctl=fcntl.ioctl
        def opening(name,flags,*args,**kwargs):
            if Path(name)==path:
                opens.append(flags)
                if len(opens)==2 and self.case=='reopen-fail':raise OSError(errno.EIO,'injected reopen failure')
            return real_open(name,flags,*args,**kwargs)
        def ioctl(fd,request,*args):
            ioctls.append(request)
            if request==termios.TIOCEXCL and ioctls.count(request)==2 and self.case=='exclusive-fail':
                raise OSError(errno.EIO,'injected second exclusivity failure')
            return real_ioctl(fd,request,*args)
        try:
            with mock.patch.object(observer.control,'OBSERVATION_INTERVAL_SEC',2.2),mock.patch.object(live._P345ObserverSession,'_lane_supplement',return_value=lane),mock.patch.object(live.native_usb_departure,'_snapshot',return_value=platform.snapshot),mock.patch.object(os,'open',side_effect=opening),mock.patch.object(fcntl,'ioctl',side_effect=ioctl):
                classification=live._P345ObserverSession._read_endpoint(session,endpoint,time.monotonic()+12,writer)
            self.opens=opens;self.ioctls=ioctls;self.session=session
            p.wait(timeout=6)
            if p.returncode:raise AssertionError(p.stderr.read().decode())
            self.peer.last_marks=marks.read_text().splitlines();self.owner_calls=owner_calls
            result=session.qualification;error=session.qualification_error
            audits=[s.session.audit for s in result.sessions] if result else [s.session.audit for s in error.completed_sessions]+[error.failed_audit]
            handle=writer.finalize(returncode=0);self.capture_path=handle.receipt_path
            self.audits=audits;self.rx_streams=[bytes(a.rx) for a in audits];self.tx_streams=[bytes(a.tx) for a in audits];self.payload=b''.join(self.rx_streams)
            self.proof=dict(result.receipt) if result else dict(error.partial_receipt)
            session.proof=self.proof;session.delegate=types.SimpleNamespace()
            base=_ReceiptFixture._receipt_value(self);base.pop('p370_readonly_research_shell_qualification')
            base.update(accepted=classification=='accepted',classification=classification,lane=session.pre_control_lane or lane)
            raw=live.p318_topology.raw_snapshot(phase='candidate_end',capture_complete=True,endpoints=[])
            with mock.patch.object(live._P327ObserverSession,'_observe_value',return_value=(base,session.pre_control_lane or lane)),mock.patch.object(live.p318_topology,'capture_candidate_raw',return_value=raw):
                value=live._P345ObserverSession.observe(session,timeout_sec=timeout_sec,download_departure=download_departure)
            self.value=value;return value
        finally:
            if held[0] is not None:os.close(held[0])
            if p.poll() is None:os.killpg(p.pid,signal.SIGKILL)
            p.communicate(timeout=3)

class Backend(joined.JoinedBackend):
    def __init__(self,p,peer,case,**kwargs):
        super().__init__(p,peer,case,**kwargs);self.fixture=Receipt(p,peer,case)

class JoinedLifecycle(joined.P370JoinedLifecycle):
    test_actual_joined_success_and_diagnostic_failure_with_foreign_download=None
    test_global_ambiguity_still_blocks_before_candidate=None
    test_client_restart_before_eof_resumes_without_transfer_replay=None
    test_after_eof_cut_preserves_fixed_outputs_and_fails_closed=None
    test_native_payload_is_p366_identity_only=None
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.tmp.cleanup);cls.peer=NativePeer(cls.tmp.name)
    def test_real_owner_two_leg_lifecycle(self):
        p=self.prepared();backend=Backend(p,self.peer,'wait-good',foreign=True)
        with self.patches():
            result=live.execute_prepared(p,p.approval_token,backend)
            live.validate_live_result(result,p)
        self.assertEqual(result['verdict'],'PASS_F1_V2_P370_NATIVE_RETURN_CONTROL_AND_ROLLED_BACK')
        self.assertFalse(result['recovery_required']);self.assertEqual(result['current_state'],'CLOSED')
        self.assertEqual(self.peer.last_marks.count('child 0'),1);self.assertEqual(self.peer.last_marks.count('download 0'),1)
        self.assertEqual([x for x in backend.calls if x.startswith('transfer-')],['transfer-candidate','transfer-rollback'])
        self.assertEqual(result['live_state']['physical_reopen_count'],1)
        self.assertFalse(result['live_state']['same_tty_fd'])

    def test_failure_receipts_preserve_reopen_certainty_and_reject_tamper(self):
        for case,count in (('resume-bad-ack',1),('reopen-fail',None),('exclusive-fail',None)):
            with self.subTest(case=case):
                p=self.prepared();backend=Backend(p,self.peer,case)
                with self.patches():
                    result=live.execute_prepared(p,p.approval_token,backend)
                    live.validate_live_result(result,p)
                self.assertEqual(result['verdict'],'NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK')
                self.assertEqual(result['current_state'],'CLOSED');self.assertFalse(result['recovery_required'])
                self.assertIs(result['live_state']['physical_reopen_count'],count)
                self.assertEqual(len(backend.fixture.opens),2)
                self.assertEqual(backend.fixture.ioctls.count(termios.TIOCNXCL),1)
                self.assertIsNone(backend.fixture.session.owned_descriptor)
                self.assertEqual(self.peer.last_marks.count('child 0'),1)
                self.assertNotIn('download 0',self.peer.last_marks)
                self.assertEqual([x for x in backend.calls if x.startswith('transfer-')],['transfer-candidate','transfer-rollback'])
                def validate_receipt():
                    with self.patches():return live._p345_validate_receipt(p,path,backend.fixture.spec)
                path=p.run_dir/'candidate-observer.json';raw=path.read_bytes();value=json.loads(raw)
                validate_receipt()
                for key,bad in (('physical_reopen_count',0),('p370_handoff_intent',None),('p370_handoff_reopen',{'sha256':'0'*64})):
                    changed=dict(value);changed[key]=bad;path.chmod(0o600);path.write_text(json.dumps(changed));path.chmod(0o400)
                    with self.assertRaises(live.F1LiveError):validate_receipt()
                    path.chmod(0o600);path.write_bytes(raw);path.chmod(0o400)
                validate_receipt()
                if case=='reopen-fail':
                    ip=p.run_dir/live.planned_handoff.INTENT_NAME;iraw=ip.read_bytes();iv=json.loads(iraw)
                    iv['request']['nonce_sha256']='0'*64
                    ip.chmod(0o600);ip.write_text(json.dumps(iv));ip.chmod(0o400)
                    _,reference=live.planned_handoff.read_intent(p.run_dir,binding=live._candidate_observer_binding(p))
                    changed=dict(value);changed['p370_handoff_intent']=reference
                    path.chmod(0o600);path.write_text(json.dumps(changed));path.chmod(0o400)
                    with self.assertRaisesRegex(live.F1LiveError,'raw READY identity'):
                        validate_receipt()
                    ip.chmod(0o600);ip.write_bytes(iraw);ip.chmod(0o400)
                    path.chmod(0o600);path.write_bytes(raw);path.chmod(0o400)
                    validate_receipt()

if __name__=='__main__':unittest.main()

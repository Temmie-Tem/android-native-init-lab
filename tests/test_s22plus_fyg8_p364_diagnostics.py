"""Actual generated preparation+console C with fixed host syscall fixtures."""
from pathlib import Path
import copy,hashlib,json,os,signal,socket,subprocess,tempfile,time,unittest
from unittest import mock
from test_s22plus_fyg8_p345_live_receipt import _ReceiptFixture
import test_s22plus_fyg8_p345_c_host_join as base
import s22plus_fyg8_p364_research_shell_runtime as runtime
import s22plus_fyg8_p364_research_shell_observer as observer
import device_action_f1_live_v2 as live
ROOT=Path(__file__).resolve().parents[1]
FIXTURE=ROOT/'tests/fixtures/s22plus_p364_syscalls_h0.inc.c'
KEY=b'k'*32


def source():
    text=base.source(runtime)
    mocks=FIXTURE.read_text()
    # Declarations precede the wrappers; bodies follow them and precede helper C.
    declarations=mocks[:mocks.index('static long fx_openat(')]
    bodies=mocks[mocks.index('static long fx_openat('):]
    prototypes='''static long fx_openat(const char*,int,int),fx_read(int,void*,size_t),fx_close(int),fx_write(int,const void*,size_t),fx_syscall(long,long,long,long,long,long,long);\n'''
    text=text.replace('#include <sys/prctl.h>','#include <sys/prctl.h>\n#include <sys/mman.h>')
    text=text.replace('static long neg(long n)',declarations+prototypes+'\nstatic long neg(long n)',1)
    text=text.replace('return neg(read(fd,p,n));','return fx_read(fd,p,n);',1)
    text=text.replace('return neg(write(fd,p,n));','return fx_write(fd,p,n);',1)
    text=text.replace('return neg(close(fd));','return fx_close(fd);',1)
    text=text.replace('return neg(open(p,flags,mode));','return fx_openat(p,flags,mode);',1)
    text=text.replace('return neg(pipe2(fds,flags));','return fx_prepared&&fx_case("pipe")?-EMFILE:neg(pipe2(fds,flags));',1)
    text=text.replace('return neg(fork());','return fx_prepared&&fx_case("clone")?-EAGAIN:neg(fork());',1)
    a=text.index('static long syscall6(');b=text.index('\nstatic long p241_clock_gettime',a)
    text=text[:a]+'''static long syscall6(long nr,long a,long b,long c,long d,long e,long f){return fx_syscall(nr,a,b,c,d,e,f);}\n'''+bodies+text[b:]
    text=text.replace(' struct timespec t; if(clock_gettime', ' if(fx_clock_error){fx_clock_error=0;return -EIO;}\n struct timespec t; if(clock_gettime',1)
    text=text.replace('out->tv_sec=t.tv_sec;out->tv_nsec=t.tv_nsec;return 0;',
        'out->tv_sec=t.tv_sec*30+(t.tv_nsec*30)/1000000000;out->tv_nsec=(t.tv_nsec*30)%1000000000;return 0;')
    text=text.replace('struct timespec64 n;p241_clock_gettime(&n);','struct timespec64 n={0};if(p241_clock_gettime(&n))_Exit(103);')
    table=runtime.return_spec.render_module_table().decode();rows=[]
    for i,(name,*_) in enumerate(runtime.return_spec.MODULES):
        data=f'P364-fixture-{i}'.encode();assert len(data)==14
        digest=','.join(str(n) for n in hashlib.sha256(data).digest())
        rows.append('{"/s22-display-modules/%s",14ULL,{%s},"%s"}'%(name,digest,'download_mode=0' if i==3 else ''))
    replacement='struct p364_return_module {const char *path;uint64_t size;const uint8_t hash[32];const char*params;};\nstatic const struct p364_return_module p364_return_modules[]={'+','.join(rows)+'};\n'
    assert text.count(table)==1;text=text.replace(table,replacement)
    text=text.replace('return neg(execve(p,a,e));',r'''
if(!strcmp(p,"/s22-display")){
 fx_mark("child",0);
 if(fx_case("child-stall"))for(;;)usleep(10000);
 unsigned count=fx_case("child-exit")?3:10;
 for(unsigned i=1;i<=count;i++)dprintf(1,"DISPLAY_SWAP_SUBMITTED run=%s swap=%u ioctl_return=0 visible=UNPROVED\n",a[2],i);
 if(fx_case("child-exit"))_Exit(7);
 for(;;)usleep(10000);
}return neg(execve(p,a,e));''',1)
    text=text.replace('for (;;) p282_poll_delay();','fx_park();')
    text=text.replace("uint8_t boot[32];memset(boot,'b',32);",'uint8_t boot[32];if(p335_getrandom_boot_id(boot))return 5;')
    text=text.replace('const char *a,const char *b,size_t n','const void *a,const void *b,size_t n')
    return text


class _PartialReceiptFixture(_ReceiptFixture):
    def __init__(self,run_dir,audit,diag):
        self.saved_audit=audit;self.saved_diag=diag
        super().__init__(run_dir,variant='p364')
    def _qualification_proof(self):
        self.audits=[self.saved_audit]
        self.rx_streams=[bytes(self.saved_audit.rx)];self.tx_streams=[bytes(self.saved_audit.tx)]
        return dict(schema=self.observer.SCHEMA,proved=False,sessions=[],
            display_replay_forbidden=True,control_replay_forbidden=True,
            control_effect_occurrence='UNKNOWN',native_progress=self.saved_diag)
    def _receipt_value(self):
        v=super()._receipt_value()
        v.pop(self.variant.prefix+'_readonly_research_shell_qualification')
        v[self.variant.proof_key]=self.proof
        path=self.run_dir/'p364-candidate-end.raw.json'
        raw=live.p318_topology.raw_snapshot(phase='candidate_end',capture_complete=False,endpoints=[])
        receipt=live.p318_topology.publish_raw(path,raw,phase='candidate_end')
        v.update(accepted=False,classification='authenticated-session-error',
            qualification_complete=False,session_count=0,command_count=0,
            pid1_framed_exec_proof=False,busybox_ash_command_proof=False,
            framed_session_closed=False,native_progress=self.saved_diag,
            p364_closure_snapshot=dict(path=str(path),**receipt,capture_complete=False,
                error_type=None,continuity_proved=False,role='post-control-transport-diagnostic'))
        return v


class DiagnosticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.tmp.cleanup)
        cls.root=Path(cls.tmp.name);cls.binary=cls.root/'peer'
        p=subprocess.run(['cc','-x','c','-','-O2','-Wall','-Wextra','-Werror','-Wno-unused-function','-Wno-misleading-indentation','-o',str(cls.binary)],input=source().encode(),capture_output=True,timeout=30)
        if p.returncode:raise AssertionError(p.stderr.decode())
    def run_case(self,case,timeout=4):
        marks=self.root/(case+'-'+str(time.monotonic_ns())+'.marks')
        host,peer=socket.socketpair();host.setblocking(False);peer.setblocking(False)
        p=subprocess.Popen([str(self.binary),str(peer.fileno()),'1'],env=dict(os.environ,P364_CASE=case,P364_MARK=str(marks)),pass_fds=(peer.fileno(),),stderr=subprocess.PIPE,start_new_session=True);peer.close()
        codec=live._open_header_initial_observer_module(runtime,observer,'p364-real-preparation')
        data=bytearray();writer=type('Writer',(),{'write_stdout':lambda self,b:data.extend(b)})();intents=[];value=error=None
        try:
            try:value=observer.qualify(codec,host.fileno(),KEY,None,set(),writer,deadline=time.monotonic()+timeout,before_control=intents.append)
            except observer.QualificationError as exc:error=exc
            audit=value.sessions[0].session.audit if value is not None else error.audit
            self.last_audit=audit
            diag=observer.progress_projection(audit)
            self.assertEqual(observer.replay_progress(codec,bytes(audit.rx),bytes(audit.tx),KEY),diag)
            host.close()
            if case.startswith('hang-'):
                self.assertIsNone(p.poll());os.killpg(p.pid,signal.SIGKILL)
            code=p.wait(timeout=4);stderr=p.stderr.read().decode()
            if not case.startswith('hang-'):self.assertEqual(code,0,stderr)
            lines=marks.read_text().splitlines() if marks.exists() else []
            return value,error,diag,lines,intents
        finally:
            host.close()
            if p.poll() is None:os.killpg(p.pid,signal.SIGKILL)
            p.communicate(timeout=3)
    def test_success_and_delayed_registry(self):
        for case in ('normal','registry-delay'):
            with self.subTest(case=case):
                v,e,d,lines,intents=self.run_case(case)
                self.assertIsNone(e);self.assertIsNotNone(v)
                self.assertTrue(d['preparation_and_clone_returned']);self.assertEqual(len(intents),1)
                self.assertEqual([x for x in lines if x.startswith('finit')],[f'finit {i}' for i in range(5)])
                self.assertIn('download 0',lines);self.assertEqual(lines[-1],'park 0')
    def test_exact_failure_stage_before_child(self):
        cases={'open-2':(16,-2),'mode-2':(16,-71),'hash-2':(16,-71),'read-2':(16,-5),
            'close-2':(18,-5),'provider':(30,-71),'mount':(31,-1),'registry-timeout':(32,-110),
            'writer':(33,-2),'pipe':(40,-24),'clock':(41,-5),'clone':(42,-11)}
        cases.update({f'finit-{i}':(11+3*i,-8) for i in range(5)})
        for case,(stage,code) in cases.items():
            with self.subTest(case=case):
                v,e,d,lines,intents=self.run_case(case)
                self.assertIsNone(v);self.assertIsNotNone(e)
                self.assertEqual(d['reported_failure'],dict(stage=stage,code=code));self.assertEqual(d['terminal_error'],code)
                self.assertEqual(intents,[]);self.assertNotIn('child 0',lines);self.assertNotIn('download 0',lines)
    def test_write_failure_stops_subsequent_operations(self):
        for case in ('enter-zero','enter-partial','enter-eagain','return-zero','pipe-return-zero','clone-return-zero'):
            with self.subTest(case=case):
                v,e,d,lines,intents=self.run_case(case)
                self.assertIsNone(v);self.assertIsNotNone(e);self.assertEqual(intents,[]);self.assertNotIn('download 0',lines)
                loads=[x for x in lines if x.startswith('finit')]
                if case.startswith('enter-'):self.assertEqual(loads,[])
                if case=='return-zero':self.assertEqual(loads,['finit 0'])
    def test_unreturned_call_is_not_an_errno_or_proven_hang(self):
        v,e,d,lines,intents=self.run_case('hang-0',timeout=.5)
        self.assertIsNone(v);self.assertEqual(d['unreturned_stage'],11)
        self.assertIsNone(d['reported_failure']);self.assertIsNone(d['terminal_error']);self.assertEqual(intents,[])
        self.assertEqual(d['unreturned_stage_meaning'],'return-not-observed-not-proved-hang')
    def test_early_child_exit_remains_distinct(self):
        v,e,d,lines,intents=self.run_case('child-exit')
        self.assertIsNone(e);self.assertEqual(d['child_status'],dict(event=2,code=7))
        self.assertEqual(v.receipt['sessions'][0]['semantic']['display_submitted_swaps'],3)
        self.assertEqual(len(intents),1)
    def test_actual_live_receipt_rederives_partial_progress(self):
        _,_,diag,_,_=self.run_case('finit-2')
        f=_PartialReceiptFixture(self.root/('receipt-'+str(time.monotonic_ns())),self.last_audit,diag)
        with mock.patch.object(live,'_p328_read_auth_key',return_value=(KEY,hashlib.sha256(KEY).hexdigest())):
            value=live._p345_validate_receipt(f.prepared,f.run_dir/'candidate-observer.json',f.spec)
            self.assertTrue(value['valid_receipt']);self.assertFalse(value['accepted'])
            changed=copy.deepcopy(f.value);changed['native_progress']['reported_failure']['code']=-5
            f.publish(changed)
            with self.assertRaises(live.F1LiveError):live._p345_validate_receipt(f.prepared,f.run_dir/'candidate-observer.json',f.spec)

    def test_ready_without_progress_never_sends_control(self):
        v,e,d,lines,intents=self.run_case('suppress-diagnostic')
        self.assertIsNone(v);self.assertIsNotNone(e);self.assertEqual(intents,[])
        self.assertFalse(d['preparation_and_clone_returned']);self.assertNotIn('download 0',lines)

    def test_child_stall_preserves_no_terminal_after_diagnostic_expiry(self):
        v,e,d,lines,intents=self.run_case('child-stall')
        self.assertIsNone(v);self.assertIsNotNone(e);self.assertEqual(intents,[])
        self.assertIn('child 0',lines)
        self.assertTrue(d['preparation_and_clone_returned']);self.assertIsNone(d['terminal_error'])

if __name__=='__main__':unittest.main()

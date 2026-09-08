"""Real native C and paired authentication across one actual host PTY close/open."""
from pathlib import Path
import hashlib,json,os,pty,signal,subprocess,tempfile,time,tty,types,unittest
from unittest import mock
import test_s22plus_fyg8_p364_diagnostics as diag_fixture
import test_s22plus_fyg8_p369_wait_control as wait_fixture
import s22plus_fyg8_p370_research_shell_runtime as runtime
import s22plus_fyg8_p370_research_shell_observer as observer
import device_action_f1_live_v2 as live
KEY=b'k'*32


def source():
    with mock.patch.object(diag_fixture,'runtime',runtime):
        value=diag_fixture.source().replace('p364','p370')
    with mock.patch.object(wait_fixture,'support_source',return_value=value):
        return wait_fixture.source()


class HandoffTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.tmp.cleanup);cls.root=Path(cls.tmp.name)
        cls.binary=cls.root/'peer'
        p=subprocess.run(['cc','-x','c','-','-O2','-Wall','-Wextra','-Werror','-Wno-unused-function','-Wno-misleading-indentation','-o',str(cls.binary)],input=source(),text=True,capture_output=True,timeout=30)
        if p.returncode:raise AssertionError(p.stderr)
    def run_case(self,case='wait-good',*,gap=.01,reopen_error=False):
        master,slave=pty.openpty();tty.setraw(slave);os.set_blocking(slave,False)
        path=os.ttyname(slave);marks=self.root/('marks-'+str(time.monotonic_ns()))
        p=subprocess.Popen([self.binary,str(master),'1'],env=dict(os.environ,P364_CASE=case,P364_MARK=str(marks)),pass_fds=(master,),stderr=subprocess.PIPE,start_new_session=True)
        os.close(master);owned=[slave];events=[];captured=bytearray()
        codec=live._open_header_initial_observer_module(runtime,observer,'p370-real-console')
        def reopen(request):
            events.append('close');old=owned[0];owned[0]=None;os.close(old)
            time.sleep(gap)
            if reopen_error:raise OSError('injected open failure')
            fd=os.open(path,os.O_RDWR|os.O_NOCTTY|os.O_NONBLOCK|os.O_CLOEXEC);owned[0]=fd
            tty.setraw(fd);events.append('open');return fd
        writer=types.SimpleNamespace(write_stdout=captured.extend)
        value=error=None
        try:
            with mock.patch.object(observer.control,'OBSERVATION_INTERVAL_SEC',.4):
                try:value=observer.qualify(codec,slave,KEY,None,set(),writer,deadline=time.monotonic()+4,
                    before_handoff=lambda r:events.append('handoff-intent'),reopen=reopen,
                    before_control=lambda r:events.append('control-intent'))
                except observer.QualificationError as exc:error=exc
            if owned[0] is not None:os.close(owned[0]);owned[0]=None
            p.wait(timeout=4)
            if p.returncode:raise AssertionError(p.stderr.read().decode())
            audits=[s.session.audit for s in value.sessions] if value else [s.session.audit for s in error.completed_sessions]+[error.failed_audit]
            rx=b''.join(bytes(a.rx) for a in audits);tx=b''.join(bytes(a.tx) for a in audits)
            self.assertEqual(bytes(captured),rx)
            projected=observer.replay_progress(codec,rx,tx,KEY)
            if value:
                self.assertEqual(observer.replay_pair(codec,rx,tx,KEY),value.receipt)
                self.assertEqual(projected,value.receipt['native_progress'])
            return value,error,events,marks.read_text().splitlines(),audits
        finally:
            if owned[0] is not None:os.close(owned[0])
            if p.poll() is None:os.killpg(p.pid,signal.SIGKILL)
            p.communicate(timeout=3)
    def test_actual_close_open_two_nonces_same_child(self):
        value,error,events,marks,audits=self.run_case()
        self.assertIsNone(error);self.assertIsNotNone(value)
        self.assertEqual(events,['handoff-intent','close','open','control-intent'])
        self.assertEqual(marks.count('child 0'),1);self.assertEqual(marks.count('download 0'),1)
        self.assertEqual(len(audits),2);self.assertNotEqual(audits[0].nonce,audits[1].nonce)
        self.assertEqual(audits[0].boot_id,audits[1].boot_id)
    def test_open_failure_never_retries_or_controls(self):
        value,error,events,marks,audits=self.run_case(reopen_error=True)
        self.assertIsNone(value);self.assertIsNotNone(error)
        self.assertEqual(events,['handoff-intent','close']);self.assertNotIn('download 0',marks)
    def test_late_reopen_does_not_tolerate_tty_eio(self):
        value,error,events,marks,audits=self.run_case(gap=.2)
        self.assertIsNone(value);self.assertIsNotNone(error);self.assertNotIn('download 0',marks)

if __name__=='__main__':unittest.main()

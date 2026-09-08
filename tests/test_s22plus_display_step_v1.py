"""Actual generated renderer/supervisor requests with retained protocol replay."""
import importlib
import os
from pathlib import Path
import pty
import signal
import subprocess
import tempfile
import time
import tty
import types
import unittest
from unittest import mock
from tests import s22plus_display_step_h0_support as support
import device_action_f1_live_v2 as live
KEY=b'k'*32


class DisplayStepTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.temp.cleanup)
        cls.root=Path(cls.temp.name);cls.variants={}
        for prefix in ('p372','p373','p374'):
            folder=cls.root/prefix;folder.mkdir()
            renderer=support.build_renderer(folder,prefix)
            native=support.build_native(folder,prefix)
            runtime=importlib.import_module('s22plus_fyg8_'+prefix+'_research_shell_runtime')
            observer=importlib.import_module('s22plus_fyg8_'+prefix+'_research_shell_observer')
            cls.variants[prefix]=(renderer,native,runtime,observer)

    def run_case(self,prefix,case='success',query=None):
        renderer,native,runtime,observer=self.variants[prefix]
        master,slave=pty.openpty();tty.setraw(slave);os.set_blocking(slave,False)
        path=os.ttyname(slave);marks=self.root/(prefix+'-'+str(time.monotonic_ns()))
        proc=subprocess.Popen([native,str(master),'1'],env=dict(os.environ,P364_CASE=case,P364_MARK=str(marks),DISPLAY_STEP_RENDERER=str(renderer)),pass_fds=(master,),stderr=subprocess.PIPE,start_new_session=True)
        os.close(master);owned=[slave];events=[];captured=bytearray()
        codec=live._open_header_initial_observer_module(runtime,observer,'step-real-console')
        def reopen(request):
            os.close(owned[0]);owned[0]=None
            time.sleep(.01)
            fd=os.open(path,os.O_RDWR|os.O_NOCTTY|os.O_NONBLOCK|os.O_CLOEXEC);owned[0]=fd;tty.setraw(fd);return fd
        value=error=None
        try:
            with mock.patch.object(observer.control,'OBSERVATION_INTERVAL_SEC',.15),mock.patch.object(observer.control,'STATUS_INTERVAL_SEC',.12):
                with mock.patch.object(observer,'_query_statuses',side_effect=query) if query else __import__('contextlib').nullcontext():
                    try:value=observer.qualify(codec,slave,KEY,None,set(),types.SimpleNamespace(write_stdout=captured.extend),deadline=time.monotonic()+4,before_handoff=lambda _:events.append('handoff'),before_control=lambda _:events.append('control'),reopen=reopen)
                    except observer.QualificationError as exc:error=exc
            if owned[0] is not None:os.close(owned[0]);owned[0]=None
            proc.wait(timeout=4)
            if proc.returncode:raise AssertionError(proc.stderr.read().decode())
            audits=[s.session.audit for s in value.sessions] if value else [s.session.audit for s in error.completed_sessions]+[error.failed_audit]
            rx=b''.join(bytes(a.rx) for a in audits);tx=b''.join(bytes(a.tx) for a in audits)
            self.assertEqual(captured,rx)
            if query is None:
                projected=observer.replay_progress(codec,rx,tx,KEY)
                if value:
                    self.assertEqual(observer.replay_pair(codec,rx,tx,KEY),value.receipt)
                    self.assertEqual(projected,value.receipt['native_progress'])
            return value,error,marks.read_text().splitlines(),events
        finally:
            if owned[0] is not None:os.close(owned[0])
            if proc.poll() is None:os.killpg(proc.pid,signal.SIGKILL)
            proc.communicate(timeout=3)

    def test_three_fixed_variants_with_real_child_and_eventfd(self):
        for prefix in self.variants:
            with self.subTest(prefix=prefix):
                value,error,marks,events=self.run_case(prefix)
                self.assertIsNone(error,str(error));self.assertIsNotNone(value)
                samples=value.receipt['status_samples']
                self.assertEqual(samples[-1]['completed_steps'],{'p372':1,'p373':2,'p374':0}[prefix])
                self.assertEqual(samples[-1]['exit_code'],7 if prefix=='p374' else 0)
                self.assertEqual(marks.count('child 0'),1);self.assertEqual(marks.count('download 0'),1)

    def test_stalled_child_does_not_block_control(self):
        value,error,marks,events=self.run_case('p372','step-stall')
        self.assertIsNone(value);self.assertIsNotNone(error)
        self.assertEqual(marks.count('download 0'),1)

    def test_local_ipc_errors_preserve_control_without_retry(self):
        for case in ('step-write-error','step-short-write'):
            with self.subTest(case=case):
                value,error,marks,events=self.run_case('p372',case)
                self.assertIsNone(value);self.assertIsNotNone(error)
                self.assertEqual(marks.count('step-write 0'),1)
                self.assertEqual(marks.count('download 0'),1)

    def test_startup_exit_and_pending_first_step_preserve_control(self):
        for prefix,case in (('p372','step-early-exit'),('p373','step-stall')):
            with self.subTest(prefix=prefix,case=case):
                value,error,marks,events=self.run_case(prefix,case)
                self.assertIsNone(value);self.assertIsNotNone(error)
                self.assertEqual(marks.count('download 0'),1)

    def test_partial_ack_is_not_retried(self):
        value,error,marks,events=self.run_case('p372','step-ack-partial')
        self.assertIsNone(value);self.assertIsNotNone(error)
        self.assertEqual(marks.count('step-ack 0'),1)
        self.assertNotIn('download 0',marks)

    def test_control_before_request_and_while_request_pending(self):
        observer=self.variants['p372'][3]
        def one(io,audit):
            body=observer.control.STEP_BODY;sequence=11
            io.write(observer.control.FRAME_STEP,sequence,body+observer._handoff_tag(io.key,observer.control.STEP_DOMAIN,audit.nonce,sequence,body))
            io.frame(observer.control.FRAME_STEP_ACK,sequence,diagnostics=True)
        for query in (lambda *_:None,one):
            with self.subTest(pending=query is one):
                value,error,marks,events=self.run_case('p372','step-stall',query=query)
                self.assertIsNotNone(error);self.assertEqual(marks.count('download 0'),1)

    def test_duplicate_step_rejected_without_second_dispatch(self):
        observer=self.variants['p372'][3]
        def duplicate(io,audit):
            body=observer.control.STEP_BODY;sequence=11
            for _ in range(2):
                io.write(observer.control.FRAME_STEP,sequence,body+observer._handoff_tag(io.key,observer.control.STEP_DOMAIN,audit.nonce,sequence,body))
                io.frame(observer.control.FRAME_STEP_ACK,sequence,diagnostics=True)
        value,error,marks,events=self.run_case('p372','step-stall',query=duplicate)
        self.assertIsNotNone(error);self.assertNotIn('download 0',marks)


if __name__=='__main__':unittest.main()

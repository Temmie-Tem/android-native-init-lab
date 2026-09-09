"""Full P375 raw receipt reopen with a real generated console peer."""
from pathlib import Path
import base64
import copy
import os
import signal
import socket
import subprocess
import tempfile
import time
import unittest
from types import SimpleNamespace
from unittest import mock

from test_s22plus_fyg8_p345_live_receipt import _ReceiptFixture,KEY,KEY_SHA256
import test_s22plus_fyg8_p375_console_integration as integration
import device_action_f1_live_v2 as live
import s22plus_fyg8_p375_console_owner as owner
import s22plus_fyg8_p375_research_shell_observer as observer
import s22plus_fyg8_p375_research_shell_runtime as runtime
import s22plus_fyg8_p375_return_host as return_host


class Fixture(_ReceiptFixture):
    def __init__(self,run_dir,binary,*,budget_stop=False):
        self.run_dir=run_dir;self.run_dir.mkdir(parents=True)
        self.variant=live.typed_evidence.SHELL_VARIANTS['p375']
        self.runtime=runtime;self.observer=observer
        self.codec=live._open_header_initial_observer_module(runtime,observer,'p375-receipt')
        self.spec=live.typed_evidence._shell_observer_spec('p375')
        self.prepared=self._prepared();self.audits=[];self.rx_streams=[];self.tx_streams=[]
        command=(b'printf skipped' if budget_stop else
            b'i=0; while [ "$i" -lt 600 ]; do /bin/busybox head -c 1000 '
            b'/dev/zero; i=$((i+1)); /bin/busybox sleep 0.005; done')
        self.plan={'schema':owner.SCHEMA,'commands':[{
            'command_base64':base64.b64encode(command).decode(),
            'cwd':'/s22-root-work','timeout_ms':300000}]}
        source=self.run_dir/'plan-source.json';source.write_bytes(owner._canonical(self.plan))
        _,self.plan_receipt=owner.seal(source,self.run_dir)
        host,peer=socket.socketpair();host.setblocking(False);peer.setblocking(False)
        process=subprocess.Popen([str(binary),str(peer.fileno()),'1'],pass_fds=(peer.fileno(),),
            env=dict(os.environ,P364_CASE='normal',P364_MARK=str(self.run_dir/'marks'),
                RC1_WORK=str(self.run_dir)),stderr=subprocess.PIPE,start_new_session=True)
        peer.close();raw=bytearray();writer=type('Writer',(),{
            'write_stdout':lambda _,data:raw.extend(data)})();intents=[]
        try:
            result=observer.qualify(self.codec,host.fileno(),KEY,None,set(),writer,
                deadline=time.monotonic()+(20 if budget_stop else 320),
                before_control=intents.append,
                evidence=self.run_dir/'console-evidence',
                interactive=lambda session,events,deadline:owner.run(
                    session,events,deadline,self.plan))
            if process.wait(timeout=4)!=0:raise AssertionError(process.stderr.read().decode())
        finally:
            host.close()
            if process.poll() is None:os.killpg(process.pid,signal.SIGKILL)
            process.communicate(timeout=3)
        audit=result.sessions[0].session.audit
        self.audits=[audit];self.rx_streams=[bytes(audit.rx)];self.tx_streams=[bytes(audit.tx)]
        self.proof=result.receipt;self.payload=self.rx_streams[0];self.intent=intents[0]
        self._write_supporting_receipts();self._write_raw_capture()
        self.value=self._receipt_value();self.publish(self.value)

    def _lane(self):
        return dict(super()._lane(),observation_phase='before-native-return-control',
            post_control_observation=False)

    def _receipt_value(self):
        value=super()._receipt_value();value.pop('p375_readonly_research_shell_qualification')
        value[self.variant.proof_key]=self.proof
        execution=owner.execution_projection(self.plan,
            self.proof['commands'][len(observer.QUALIFICATION_COMMANDS):])
        value.update(session_count=1,command_count=self.proof['command_count'],
            request_count=self.proof['request_count'],pid1_framed_exec_proof=True,
            busybox_ash_command_proof=True,framed_session_closed=False,same_tty_fd=True,
            root_console=True,root_uid=0,root_gid=0,caller_selected_command=True,
            control_acceptance_observed=True,control_requested_mode='download',
            control_ack_scope='acceptance-only',software_download_arrival='UNPROVED',
            proof_scope=observer.PROOF_SCOPE,descriptor_close_error=None,
            native_progress=self.proof['preparation'],p375_console_plan=self.plan_receipt,
            p375_plan_execution=execution)
        if execution['all_planned_terminal'] is not True:
            value.update(accepted=False,classification='authenticated-session-error',
                protocol_error='root-console-plan-incomplete')
        path=self.run_dir/'p375-candidate-end.raw.json'
        raw=live.p318_topology.raw_snapshot(phase='candidate_end',capture_complete=True,endpoints=[])
        receipt=live.p318_topology.publish_raw(path,raw,phase='candidate_end')
        value['p375_closure_snapshot']=dict(path=str(path),**receipt,capture_complete=True,
            error_type=None,continuity_proved=False,role='post-control-transport-diagnostic')
        value['p375_control_intent']=return_host.write_intent(self.run_dir,
            binding=value['binding'],endpoint_identity_sha256=value['endpoint_identity_sha256'],
            lane=value['lane'],request=self.intent)
        self.intent_value,_=return_host.stable_record(self.run_dir/return_host.INTENT_NAME)
        return value


class P375LiveReceiptTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.temporary.cleanup)
        cls.binary=Path(cls.temporary.name)/'native'
        built=subprocess.run(['cc','-x','c','-','-O2','-Wall','-Wextra','-Werror',
            '-Wno-unused-function','-Wno-unused-const-variable','-Wno-misleading-indentation',
            '-o',str(cls.binary)],input=integration.source(),text=True,capture_output=True,timeout=30)
        if built.returncode:raise AssertionError(built.stderr)

    def validate(self,fixture):
        test_owner=SimpleNamespace(read_intent=lambda *args,**kwargs:
            (fixture.intent_value,fixture.value['p375_control_intent']))
        with mock.patch.object(live,'_p328_read_auth_key',return_value=(KEY,KEY_SHA256)), \
                mock.patch.object(live,'_return_host_for',return_value=test_owner):
            return live._p345_validate_receipt(fixture.prepared,
                fixture.run_dir/'candidate-observer.json',fixture.spec)

    def test_large_raw_progress_and_ordered_plan_reopen(self):
        fixture=Fixture(Path(self.temporary.name)/('run-'+str(time.monotonic_ns())),self.binary)
        self.assertGreater(len(fixture.payload),512*1024)
        value=self.validate(fixture)
        self.assertTrue(value['valid_receipt']);self.assertTrue(value['accepted'])
        self.assertTrue(value['p375_plan_execution']['all_planned_terminal'])
        self.assertEqual(value['p375_plan_execution']['results'][0]['timeout_ms'],300000)

    def test_changed_sealed_plan_cannot_join_raw_exec(self):
        fixture=Fixture(Path(self.temporary.name)/('run-'+str(time.monotonic_ns())),self.binary)
        sealed=fixture.run_dir/owner.SEALED_NAME;sealed.unlink()
        changed=copy.deepcopy(fixture.plan)
        changed['commands'][0]['command_base64']=base64.b64encode(b'printf changed').decode()
        source=fixture.run_dir/'changed-plan.json';source.write_bytes(owner._canonical(changed))
        _,receipt=owner.seal(source,fixture.run_dir)
        candidate=copy.deepcopy(fixture.value);candidate['p375_console_plan']=receipt
        fixture.publish(candidate)
        with self.assertRaises(live.F1LiveError):self.validate(fixture)

    def test_budget_stopped_plan_is_valid_no_proof_with_control(self):
        fixture=Fixture(Path(self.temporary.name)/('run-'+str(time.monotonic_ns())),
            self.binary,budget_stop=True)
        value=self.validate(fixture)
        self.assertTrue(value['valid_receipt']);self.assertFalse(value['accepted'])
        self.assertTrue(value['control_acceptance_observed'])
        self.assertFalse(value['p375_plan_execution']['all_planned_terminal'])
        self.assertEqual(value['p375_plan_execution']['results'][0]['outcome'],'not-executed')
        self.assertFalse(live._p345_proof_ok(value,prefix='p375'))


if __name__=='__main__':unittest.main()

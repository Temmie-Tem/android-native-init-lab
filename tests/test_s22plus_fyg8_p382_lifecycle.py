"""Real P382 wire/receipt/common close; fixture USB, Odin, ADB and native syscalls."""
import base64
import contextlib
import copy
import hashlib
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import time
import types
import unittest
from unittest import mock

import test_device_action_f1_live_v2 as generic
import test_s22plus_fyg8_p367_lifecycle as joined
import test_s22plus_fyg8_p382_hud_integration as integration
from test_s22plus_fyg8_p345_live_receipt import _ReceiptFixture, KEY, KEY_SHA256
from s22plus_native_departure_h0_support import Fixture as DeparturePlatform, departure
import device_action_f1_live_v2 as live
import s22plus_fyg8_p382_research_shell_runtime as runtime
import s22plus_fyg8_p382_research_shell_observer as observer
import s22plus_fyg8_p382_console_owner as owner
import s22plus_fyg8_p382_return_host as return_host


def plan():
    commands = [b"printf 'RC5_RAM_CHECK\\n'", observer.memory_snapshot.EARLY_COMMAND,
                observer.memory_snapshot.LATE_COMMAND]
    return {'schema': owner.SCHEMA, 'commands': [dict(command_base64=base64.b64encode(c).decode(),
        cwd='/s22-root-work', timeout_ms=15000) for c in commands]}


class Receipt(_ReceiptFixture):
    def __init__(self, prepared, binary):
        self.prepared=prepared; self.run_dir=prepared.run_dir; self.binary=binary
        self.variant=live.typed_evidence.SHELL_VARIANTS['p382']
        self.runtime=runtime; self.observer=observer
        self.spec=live.typed_evidence._shell_observer_spec('p382')
        self.codec=live._open_header_initial_observer_module(runtime,observer,'p382-lifecycle')
        self.departure_receipt=None

    def _lane(self):
        lane=dict(super()._lane(),observation_phase='before-native-return-control',post_control_observation=False)
        if self.departure_receipt is not None:lane['native_usb_departure_binding']=self.departure_receipt
        return lane

    def arm(self):
        self._write_supporting_receipts()
        path=self.run_dir/'candidate-observer-guard.json'; path.unlink()
        live.cdc_acm_observer.persist_json(path,dict(schema=live.cdc_acm_observer.GUARD_SCHEMA,
            status='armed',spec_sha256='1'*64,topology_sha256='2'*64,rule_sha256='3'*64,
            instance_sha256='5'*64,output_sha256='6'*64,raw_capture_receipt={},child_alive=True))
        source=self.run_dir/'plan-source.json';source.write_bytes(owner._canonical(plan()))
        self.plan,self.plan_receipt=owner.seal(source,self.run_dir)

    def observe(self, *, timeout_sec, download_departure):
        writer=live.raw_capture.RawCaptureWriter(self.run_dir,'candidate-observer',
            stdout_maximum=observer.RAW_MAXIMUM,stderr_maximum=1,argv0_name='p382-h0-socket',
            stdout_name='candidate-observer.raw',stderr_name='candidate-observer.raw.stderr')
        platform=DeparturePlatform(self.run_dir/'native-platform')
        intents=[]
        def intent(request):
            binding=live._candidate_observer_binding(self.prepared)
            self.departure_receipt=platform.capture(self.run_dir,binding,request)
            intents.append(return_host.write_intent(self.run_dir,binding=binding,
                endpoint_identity_sha256='e'*64,lane=self._lane(),request=request))
        host,peer=socket.socketpair();host.setblocking(False);peer.setblocking(False)
        process=subprocess.Popen([str(self.binary),str(peer.fileno()),'1'],pass_fds=(peer.fileno(),),
            env=dict(os.environ,P364_CASE='normal',P364_MARK=str(self.run_dir/'marks'),
                RC1_WORK=str(self.run_dir)),stderr=subprocess.PIPE,start_new_session=True)
        peer.close()
        try:
            result=observer.qualify(self.codec,host.fileno(),KEY,None,set(),writer,
                deadline=time.monotonic()+timeout_sec,before_control=intent,
                evidence=self.run_dir/'console-evidence',
                interactive=lambda session,events,deadline:owner.run(session,events,deadline,self.plan))
            if process.wait(timeout=4)!=0:raise AssertionError(process.stderr.read().decode())
        finally:
            host.close()
            if process.poll() is None:os.killpg(process.pid,signal.SIGKILL)
            process.communicate(timeout=3)
        handle=writer.finalize(returncode=0); self.capture_path=handle.receipt_path
        audit=result.sessions[0].session.audit
        self.audits=[audit];self.rx_streams=[bytes(audit.rx)];self.tx_streams=[bytes(audit.tx)]
        self.payload=bytes(audit.rx);self.proof=result.receipt
        base=super()._receipt_value();base.pop('p382_readonly_research_shell_qualification')
        base['session_count']=1
        session=live._P363ObserverSession.__new__(live._P363ObserverSession)
        session.delegate=types.SimpleNamespace();session.run_dir=self.run_dir;session.namespace='p382'
        session.qualification=result;session.qualification_error=None;session.proof=self.proof
        session.proof_key=self.variant.proof_key;session.auth_runtime=runtime;session.qualification_observer=observer
        session.auth_key_sha256=KEY_SHA256;session.protocol_error=None
        session.receipt_schema='s22plus_fyg8_p382_shell_qualification_acm_receipt_v1'
        session.receipt_label='P382 H0 receipt';session.control_intent_receipt=intents[0]
        session.root_console_plan_value=self.plan;session.root_console_plan_receipt=self.plan_receipt
        raw=live.p318_topology.raw_snapshot(phase='candidate_end',capture_complete=True,endpoints=[])
        with mock.patch.object(live._P327ObserverSession,'_observe_value',return_value=(base,self._lane())), \
                mock.patch.object(live.p318_topology,'capture_candidate_raw',return_value=raw):
            return live._P345ObserverSession.observe(session,timeout_sec=timeout_sec,download_departure=download_departure)


class Backend(joined.JoinedBackend):
    def __init__(self,p,binary):
        with mock.patch.object(joined.parent.BaseBackend,'__init__',
                lambda self,*args:generic.FakeBackend.__init__(self,live)):
            super().__init__(p,None,'normal')
        self.fixture=Receipt(p,binary)

    @contextlib.contextmanager
    def candidate_observer_session(self,prepared):
        self.fixture.arm()
        try:yield self.fixture
        finally:live.cdc_acm_observer.persist_json(prepared.run_dir/'candidate-observer-guard-release.json',
            dict(schema=live.cdc_acm_observer.GUARD_SCHEMA,status='released',instance_sha256='5'*64,released=True,returncode=0))

    def observe_candidate(self,p,run,lease,session):
        self.calls.append('observe')
        wait=live.odin_core.wait_for_no_live_endpoint
        def absent(*args,**kwargs):
            kwargs.update(self.platform());return wait(*args,**kwargs)
        with mock.patch.object(live.odin_core,'wait_for_no_live_endpoint',side_effect=absent):
            return live.SamsungOdinBackend.observe_candidate(self,p,run,lease,session)


class P382Lifecycle(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        integration.StatusIntegration.setUpClass.__func__(cls)

    def prepared(self):
        factory=generic.DeviceActionF1LiveV2Test();factory.module=live
        temporary,p=factory.prepared();self.addCleanup(temporary.cleanup)
        variant=live.typed_evidence.SHELL_VARIANTS['p382']
        p.bundle.manifest['manifest_id']='p382-full-lifecycle-fixture'
        p.bundle.manifest['observation']=dict(timeout_sec=90,acceptance=variant.adapter.acceptance_fixture(),
            candidate_observer=live.typed_evidence._shell_observer_spec('p382'))
        p.bundle.manifest['observation'][live.typed_evidence.CANDIDATE_ARRIVAL_PROOF_ROLE_KEY]=live.typed_evidence.CANDIDATE_AUTHENTICATED_LOGICAL_RESIDENT_EXEC_ROLE
        p.private_target['topology']=live.p324_typec_lane.SOURCE_TOPOLOGY
        p.prepared.update(p328_auth_key_identity=dict(size=32,sha256=KEY_SHA256),
            approval_binding=dict(p328_auth_key_identity=dict(size=32,sha256=KEY_SHA256)))
        return p

    def test_native_delta_is_only_declared_identity_and_label(self):
        import s22plus_fyg8_p381_research_shell_runtime as previous
        import s22plus_fyg8_p381_display_renderer as old_renderer
        import s22plus_fyg8_p382_display_renderer as new_renderer
        import s22plus_fyg8_p382_namespace as namespace
        old=previous.P381_RUN_ID_HEX.encode();new=runtime.P382_RUN_ID_HEX.encode()
        escaped=lambda raw: ''.join('\\x%02x'%b for b in raw).encode()
        normalized=runtime.P382_HELPER.replace(b'p382',b'p381').replace(b'P382',b'P381')
        normalized=normalized.replace(new,old).replace(escaped(new),escaped(old))
        self.assertEqual(normalized,previous.P381_HELPER)
        self.assertEqual(new_renderer.render().replace(b'rc.5',b'rc.4')
            .replace(b'p382',b'p381').replace(b'P382',b'P381'),old_renderer.render())
        for relative,digest in namespace.P381_SOURCES.values():
            self.assertEqual(hashlib.sha256((namespace.ROOT/relative).read_bytes()).hexdigest(),digest)

    def test_normal_and_interrupted_full_p382_close(self):
        for cut in (None,'before-observed','after-observed','after-rollback'):
            with self.subTest(cut=cut):
                p=self.prepared();backend=Backend(p,self.binary)
                transition=live.core.Journal.transition;retained={}
                def interrupted(journal,state,action,details):
                    if state=='OBSERVED':
                        self.assertNotIn('p382_root_console_qualification',details)
                        for name in ('candidate-observer.json','candidate-observer.raw',return_host.INTENT_NAME):
                            path=p.run_dir/name
                            self.assertTrue(path.is_file())
                            retained[name]=path.read_bytes()
                        self.assertEqual(details['candidate_observer_receipt_sha256'],
                            hashlib.sha256(retained['candidate-observer.json']).hexdigest())
                        if cut=='before-observed':raise KeyboardInterrupt(cut)
                    result=transition(journal,state,action,details)
                    if (state=='OBSERVED' and cut=='after-observed') or (state=='ROLLBACK_FLASHED' and cut=='after-rollback'):
                        raise KeyboardInterrupt(cut)
                    return result
                with contextlib.ExitStack() as stack:
                    stack.enter_context(mock.patch.object(live,'_p300_bundle',return_value=False))
                    stack.enter_context(mock.patch.object(live,'_p328_read_auth_key',return_value=(KEY,KEY_SHA256)))
                    stack.enter_context(mock.patch.object(departure,'_snapshot',side_effect=departure.usbfs.UsbfsEndpointDeparture('/dev/bus/usb/003/077')))
                    stack.enter_context(mock.patch.dict(os.environ,dict(METRICS_COLLECTOR=str(self.collector),
                        SNAPSHOT_BINARY=str(self.snapshot),HUD_RENDERER=str(self.real_renderer))))
                    with mock.patch.object(live.core.Journal,'transition',new=interrupted):
                        if cut is None:result=live.execute_prepared(p,p.approval_token,backend)
                        else:
                            with self.assertRaises(KeyboardInterrupt):live.execute_prepared(p,p.approval_token,backend)
                    if cut is not None:
                        with mock.patch.object(backend,'observe_candidate',side_effect=AssertionError('observer replay')):
                            result=live.recover_prepared(p,backend)
                    live.validate_live_result(json.loads((p.run_dir/'live-result.json').read_text()),p)
                    changed=copy.deepcopy(result)
                    changed['live_state']['p382_root_console_qualification']['proved']=False
                    with self.assertRaises(live.F1LiveError):live.validate_live_result(changed,p)
                self.assertEqual(result['verdict'],'PASS_F1_V2_P382_ROOT_CONSOLE_AND_ROLLED_BACK')
                self.assertEqual(result['current_state'],'CLOSED');self.assertFalse(result['recovery_required'])
                self.assertTrue(result['live_state']['final_verified'])
                self.assertEqual([c for c in backend.calls if c.startswith('transfer-')],['transfer-candidate','transfer-rollback'])
                self.assertEqual(backend.calls.count('observe'),1)
                for name,raw in retained.items():self.assertEqual((p.run_dir/name).read_bytes(),raw)
                for path in (p.run_dir/'transaction/journal').glob('*.json'):
                    self.assertLessEqual(path.stat().st_size,live.core.MAX_RECORD)
                for name in ('live-state.json','live-result.json'):
                    self.assertLessEqual((p.run_dir/name).stat().st_size,live.core.MAX_RESULT_RECORD)
                print('P382 full close',cut,'state',(p.run_dir/'live-state.json').stat().st_size,
                    'result',(p.run_dir/'live-result.json').stat().st_size)

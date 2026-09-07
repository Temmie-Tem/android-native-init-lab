"""Complete return-observer/state/result lifecycle with a fixture platform.

C protocol, raw receipt, namespace and persisted result consumers are real.
ADB/Odin/USB and kernel calls in the C peer are fixtures. The unchanged physical
USB trace sidecar is disabled in this platform simulation; no device is accessed.
"""
from pathlib import Path
import contextlib,copy,hashlib,json,tempfile,types,unittest
from unittest import mock
import test_device_action_f1_live_v2 as generic
from test_s22plus_fyg8_p345_live_receipt import _ReceiptFixture,KEY_SHA256
from s22plus_p365_h0_support import ConsolePeer,KEY,runtime,observer,live

class Receipt(_ReceiptFixture):
    def __init__(self,prepared,peer,case):
        self.prepared=prepared;self.run_dir=prepared.run_dir;self.peer=peer;self.case=case
        self.variant=live.typed_evidence.SHELL_VARIANTS['p365'];self.runtime=runtime;self.observer=observer
        self.spec=live.typed_evidence._shell_observer_spec('p365')
        self.codec=live._open_header_initial_observer_module(runtime,observer,'p365-persistence')
        self.intent_receipt=None
    def arm(self):
        self._write_supporting_receipts()
        path=self.run_dir/'candidate-observer-guard.json';path.unlink()
        live.cdc_acm_observer.persist_json(path,dict(schema=live.cdc_acm_observer.GUARD_SCHEMA,status='armed',spec_sha256='1'*64,topology_sha256='2'*64,rule_sha256='3'*64,instance_sha256='5'*64,output_sha256='6'*64,raw_capture_receipt={},child_alive=True))
    def _lane(self):
        return dict(super()._lane(),observation_phase='before-native-return-control',post_control_observation=False)
    def observe(self,*,timeout_sec,download_departure):
        writer=live.raw_capture.RawCaptureWriter(self.run_dir,'candidate-observer',stdout_maximum=live.P327_MAX_RAW_BYTES,stderr_maximum=1,argv0_name='p365-h0-socket',stdout_name='candidate-observer.raw',stderr_name='candidate-observer.raw.stderr')
        def intent(request):
            self.intent_receipt=live.p365_return_host.write_intent(self.run_dir,binding=live._candidate_observer_binding(self.prepared),endpoint_identity_sha256='e'*64,lane=self._lane(),request=request)
        result,error,audit,diag=self.peer.run(self.case,writer,intent)
        handle=writer.finalize(returncode=0);self.capture_path=handle.receipt_path
        self.audits=[audit];self.rx_streams=[bytes(audit.rx)];self.tx_streams=[bytes(audit.tx)];self.payload=bytes(audit.rx)
        self.proof=dict(result.receipt) if result is not None else dict(error.partial_receipt)
        base=super()._receipt_value();base.pop('p365_readonly_research_shell_qualification')
        base.update(accepted=result is not None,classification='accepted' if result is not None else 'authenticated-session-error')
        session=live._P363ObserverSession.__new__(live._P363ObserverSession)
        session.delegate=types.SimpleNamespace();session.run_dir=self.run_dir;session.namespace='p365';session.qualification=result;session.qualification_error=error
        session.proof=self.proof;session.proof_key=self.variant.proof_key;session.auth_runtime=runtime;session.qualification_observer=observer
        session.auth_key_sha256=KEY_SHA256;session.protocol_error=None if error is None else error.category
        session.receipt_schema='s22plus_fyg8_p365_shell_qualification_acm_receipt_v1';session.receipt_label='P365 H0 receipt'
        session.control_intent_receipt=self.intent_receipt
        raw=live.p318_topology.raw_snapshot(phase='candidate_end',capture_complete=True,endpoints=[])
        with mock.patch.object(live._P327ObserverSession,'_observe_value',return_value=(base,self._lane())),mock.patch.object(live.p318_topology,'capture_candidate_raw',return_value=raw):
            value=live._P345ObserverSession.observe(session,timeout_sec=timeout_sec,download_departure=download_departure)
        self.value=value
        return value

class Backend(generic.FakeBackend):
    def __init__(self,prepared,peer,case):
        super().__init__(live);self.fixture=Receipt(prepared,peer,case)
    def wait_download(self,prepared,run_dir,lease,timeout):
        endpoint=super().wait_download(prepared,run_dir,lease,timeout)
        if self.calls.count('wait-download')>1:
            path=live._p318_phase_paths(prepared,'rollback_download')[1]
            if not path.exists():live._write_exclusive(path,{'fixture_exact_download_phase':True})
        return endpoint
    def revalidate_candidate_lane(self,prepared):
        self.calls.append('revalidate-candidate-lane')
    @contextlib.contextmanager
    def candidate_observer_session(self,prepared):
        self.fixture.arm()
        try:yield self.fixture
        finally:live.cdc_acm_observer.persist_json(prepared.run_dir/'candidate-observer-guard-release.json',dict(schema=live.cdc_acm_observer.GUARD_SCHEMA,status='released',instance_sha256='5'*64,released=True,returncode=0))
    def verify_final(self,prepared,_run_dir,_lease,destination):
        self.calls.append('verify-final');payload=bytes(2097136)
        classification=live.classify_acceptance(payload,prepared.bundle.manifest['observation']['acceptance'])
        reads=[]
        for i in (1,2):
            h=live.raw_capture.publish_captured_bytes(destination,f'900{i}-observer-eof',stdout=payload,stdout_name=f'rollback-observer-{i}.bin',stderr_name=f'rollback-observer-{i}.bin.stderr')
            reads.append(dict(path=str(h.stdout_path),bytes=len(payload),sha256=hashlib.sha256(payload).hexdigest(),raw_capture=live._receipt(h.receipt_path,'fixture raw'),read_to_eof=True,stderr_bytes=0,elapsed_sec=0.01))
        health=dict(android_boot_completed=True,boot_animation_stopped=True,verified_boot_state='orange',root_verified=True,boot_sha256=prepared.bundle.profile['final_health']['boot_sha256'],supporting_partition_sha256=prepared.bundle.profile['final_health']['supporting_partition_sha256'],odin_endpoint_absent=True,kernel_release='fixture-kernel',boot_id_sha256='3'*64)
        obs=dict(reads=reads,byte_identical=True,bytes=len(payload),sha256=hashlib.sha256(payload).hexdigest(),exact_marker_count=classification['exact_count'],marker_family_count=classification['family_count'],classification=classification,accepted=classification['accepted'],p365_stock=live._p320_terminal_projection(classification))
        return dict(health=health,target_evidence_sha256=live.core.json_sha256({'serial':hashlib.sha256(prepared.private_target['serial'].encode()).hexdigest(),'topology':hashlib.sha256(prepared.private_target['topology'].encode()).hexdigest()}),observer=obs,rollback_verified=True)

class NoDevice:
    def __getattr__(self,name):raise AssertionError('closed finalizer requested backend '+name)

class PersistenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.temp.cleanup);cls.peer=ConsolePeer(cls.temp.name)
    def prepared(self):
        base=generic.DeviceActionF1LiveV2Test();base.module=live
        temp,p=base.prepared();self.addCleanup(temp.cleanup)
        v=live.typed_evidence.SHELL_VARIANTS['p365'];m=p.bundle.manifest
        m['manifest_id']='p365-full-lifecycle-fixture';m['observation']=dict(timeout_sec=60,acceptance=v.adapter.acceptance_fixture(),candidate_observer=live.typed_evidence._shell_observer_spec('p365'),candidate_arrival_proof=live.typed_evidence.CANDIDATE_AUTHENTICATED_LOGICAL_RESIDENT_EXEC_ROLE)
        m['observation'][live.typed_evidence.CANDIDATE_ARRIVAL_PROOF_ROLE_KEY]=m['observation'].pop('candidate_arrival_proof')
        p.private_target['topology']=live.p324_typec_lane.SOURCE_TOPOLOGY
        live._write_exclusive(p.run_dir/'fixture-typec-lane.json',{'fixture_typec_lane':True})
        p.prepared['p324_typec_lane_binding']=live._receipt(p.run_dir/'fixture-typec-lane.json','fixture typec')
        p.prepared.update(p328_auth_key_identity={'size':32,'sha256':KEY_SHA256},approval_binding={'p328_auth_key_identity':{'size':32,'sha256':KEY_SHA256}})
        return p
    def patches(self):
        stack=contextlib.ExitStack();stack.enter_context(mock.patch.object(live,'_p300_bundle',return_value=False));stack.enter_context(mock.patch.object(live,'_p328_read_auth_key',return_value=(KEY,KEY_SHA256)))
        return stack
    def test_complete_success_and_late_failure_roundtrip(self):
        for case in ('normal','writer','child-stall','ack-zero'):
            with self.subTest(case=case):
                p=self.prepared();backend=Backend(p,self.peer,case)
                with self.patches():
                    result=live.execute_prepared(p,p.approval_token,backend)
                    live.validate_live_result(json.loads((p.run_dir/'live-result.json').read_text()),p)
                    reopened=live.recover_prepared(p,NoDevice())
                self.assertEqual(reopened,result)
                self.assertEqual(result['current_state'],'CLOSED');self.assertFalse(result['recovery_required'])
                self.assertEqual([x for x in backend.calls if x.startswith('transfer-')],['transfer-candidate','transfer-rollback'])
                self.assertEqual(result['live_state']['candidate_observer_accepted'],case=='normal')
                self.assertEqual(result['verdict'],'PASS_F1_V2_P365_NATIVE_RETURN_CONTROL_AND_ROLLED_BACK' if case=='normal' else 'NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK')
                self.assertEqual(result['outcome_class'],'p365_native_return_control_rollback_verified' if case=='normal' else 'p365_native_return_control_unproved_rollback_verified')
                if case=='normal':
                    self.assertGreater((p.run_dir/'live-state.json').stat().st_size,live.core.MAX_RECORD)
                    self.assertLessEqual((p.run_dir/'live-state.json').stat().st_size,live.core.MAX_RESULT_RECORD)
                self.assertTrue(result['live_state']['final_verified'])
                self.assertEqual('download 0' in self.peer.last_marks,case=='normal')
                self.assertEqual([x['name'] for x in result['timeline']['events']],list(live.core.TIMELINE))
                print('P365',case,'state',(p.run_dir/'live-state.json').stat().st_size,'result',(p.run_dir/'live-result.json').stat().st_size)

    def test_closed_publication_cut_never_replays_backend(self):
        p=self.prepared();backend=Backend(p,self.peer,'normal')
        with self.patches():
            with mock.patch.object(live,'_write_live_result',side_effect=OSError('injected publication cut')):
                with self.assertRaisesRegex(OSError,'publication cut'):
                    live.execute_prepared(p,p.approval_token,backend)
            self.assertFalse((p.run_dir/'live-result.json').exists())
            journal=live.core.Journal(p.run_dir/'transaction',p.binding_sha256)
            self.assertEqual(journal.state(),'CLOSED')
            before={str(x.relative_to(p.run_dir)):x.read_bytes() for x in p.run_dir.rglob('*') if x.is_file()}
            result=live.recover_prepared(p,NoDevice())
            for name,raw in before.items():self.assertEqual((p.run_dir/name).read_bytes(),raw)
            live.validate_live_result(json.loads((p.run_dir/'live-result.json').read_text()),p)
            altered=copy.deepcopy(result);altered['live_state']['native_progress']['records'][-1]['code']=-22
            with self.assertRaises(live.F1LiveError):live.validate_live_result(altered,p)
        self.assertEqual([x for x in backend.calls if x.startswith('transfer-')],['transfer-candidate','transfer-rollback'])

    def test_exact_record_limits_and_unrelated_variants(self):
        p=self.prepared();value={'payload':'x'*live.core.MAX_RECORD}
        live._save_state(p,value)
        self.assertEqual(live._state(p)['payload'],value['payload'])
        prep_path=p.run_dir/'prepared-size.json'
        live._write_prepared_record(p.bundle,prep_path,value)
        self.assertEqual(live._read_json(prep_path,'prepared size'),value)
        for prefix in ('p364','p363','p345'):
            with self.subTest(prefix=prefix):
                other=copy.deepcopy(p.bundle)
                other.manifest['observation']['acceptance']=live.typed_evidence.SHELL_VARIANTS[prefix].adapter.acceptance_fixture()
                other.manifest['observation']['candidate_observer']=live.typed_evidence._shell_observer_spec(prefix)
                q=types.SimpleNamespace(bundle=other,run_dir=p.run_dir)
                with self.assertRaisesRegex(live.F1LiveError,'exceeds its bound'):live._save_state(q,value)
                with self.assertRaisesRegex(live.F1LiveError,'exceeds its bound'):live._write_prepared_record(other,p.run_dir/('old-'+prefix+'.json'),value)
        with self.assertRaises(live.core.F1V2Error):live.core.Journal.create(p.run_dir/'oversize-journal','a'*64,value)
        with self.assertRaises(live.F1LiveError):live._save_state(p,{'payload':'x'*live.core.MAX_RESULT_RECORD})


if __name__=='__main__':unittest.main()

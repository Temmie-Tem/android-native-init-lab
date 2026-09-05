"""P343 live dispatch/proof/close tests, no device authority."""
from pathlib import Path
from types import SimpleNamespace
import tempfile
import sys
import unittest
from unittest import mock

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'workspace/public/src/scripts/revalidation'),str(ROOT/'tests')]
import device_action_f1_live_v2 as live
import test_s22plus_fyg8_idle_reuse_probe as fixture


class P343LiveTests(unittest.TestCase):
    def test_actual_p343_arm_context_and_reopen_contract(self):
        import contextlib
        prepared = self.prepared()
        prepared.private_target = {'topology': 'usb:1-2'}
        prepared.run_dir = Path('/host-fixture')
        base = SimpleNamespace()
        inherited = SimpleNamespace(delegate=SimpleNamespace(delegate=base))
        spec = prepared.bundle.manifest['observation']['candidate_observer']
        backend = SimpleNamespace(usb_root=Path('/no-usb'), typec_root=Path('/no-typec'))
        with mock.patch.object(live, '_p328_read_auth_key', return_value=(b'x'*32, 'ab'*32)), \
             mock.patch.object(live, '_p324_typec_lane_value', return_value=({}, {})), \
             mock.patch.object(live, '_candidate_observer_binding', return_value={}), \
             mock.patch.object(live.p325_guard_adapter, 'observer_session',
                               side_effect=lambda *a, **k: contextlib.nullcontext(inherited)) as guard:
            with live.SamsungOdinBackend.candidate_observer_session(backend, prepared) as session:
                self.assertIsInstance(session, live._P343ObserverSession)
                self.assertIs(session.base, base)
            guard.assert_called_once()
            for field, wrong in [('host_tty_close_reopen', False), ('session_cap', 1),
                                 ('resident_lease_schema', live.P342_LEASE_SCHEMA)]:
                guard.reset_mock()
                with self.assertRaisesRegex(live.F1LiveError, 'contract differs'):
                    with live._p343_candidate_observer_session(prepared, {**spec, field: wrong},
                            lane_value={}, lane_receipt={}, usb_root=Path('/no-usb'),
                            typec_root=Path('/no-typec')):
                        self.fail('invalid arm accepted')
                guard.assert_not_called()

    def test_prepared_record_bound_is_p343_only_and_no_clobber(self):
        import stat
        bundle = self.prepared().bundle
        value = {"closure_fixture": "x" * 33000}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'prepared.json'
            live._write_prepared_record(bundle, path, value)
            self.assertEqual(live._read_json(path, 'prepared fixture'), value)
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o400)
            with self.assertRaises(FileExistsError):
                live._write_prepared_record(bundle, path, value)
            for campaign in ('p342', 'foreign'):
                other = SimpleNamespace(manifest={'acceptance': {
                    'overlay_contract_id': 's22plus-fyg8-'+campaign+'-observer-v4-carrier-v1'}})
                denied = Path(directory) / (campaign+'.json')
                with self.assertRaisesRegex(live.F1LiveError, 'exceeds its bound'):
                    live._write_prepared_record(other, denied, value)
                self.assertFalse(denied.exists())
            oversized = Path(directory) / 'oversized.json'
            with self.assertRaisesRegex(live.F1LiveError, 'exceeds its bound'):
                live._write_prepared_record(bundle, oversized, {'x': 'x' * 65536})
            self.assertFalse(oversized.exists())

    def test_actual_common_classifier_scopes_predecessor_projection(self):
        adapter = live.typed_evidence.p343_stock_adapter
        parser = adapter._raw_parser()
        acceptance = adapter.acceptance_fixture()
        acceptance["auth_key"] = dict(live.typed_evidence.P343_AUTH_EXEC_AUTH_KEY_IDENTITY)
        empty = live.classify_acceptance(bytes(parser.RAW_SIZE), acceptance)
        self.assertNotIn("p319_stock", empty)
        self.assertEqual(empty["proof_class"], "NO_PROOF_OBSERVER")
        payload = parser._observer().encode_stock_payload_v4(
            parser._base_payload(state="COMPLETE"), None
        )
        record = parser._carrier_record_from_envelope(
            parser._envelope_from_payload(payload),
            detail=parser.STOCK_DETAIL_COMPLETE,
            run_id=adapter.P343_RUN_ID,
        )
        value = live.classify_acceptance(
            bytes(parser.RAW_SIZE - len(record)) + record, acceptance
        )
        self.assertNotIn("p319_stock", value)
        self.assertEqual(value["proof_class"], "NONCAUSAL_SUCCESS_PATH")
        self.assertFalse(value["candidate_success"])

    def test_actual_lease_publication_order_guard_failure_and_recovery_stop(self):
        import test_s22plus_fyg8_p343_exploration as exploration_fixture
        resident=live.p343_exploration_session
        for released in (True,False):
            with tempfile.TemporaryDirectory() as directory:
                prepared=self.prepared();prepared.run_dir=Path(directory)
                prepared.bundle.manifest.update(manifest_id='host-fixture',run_id='host-fixture')
                events=[];state={}
                journal=SimpleNamespace(transition=lambda *a:events.append(a[0]),
                    records=lambda:[{'record_sha256':'ab'*32}])
                durable={'accepted':True,'download_endpoint_absent':True}
                def seal(*args):
                    self.assertFalse((prepared.run_dir/resident.DIRECTORY).exists())
                    self.assertEqual(events,['OBSERVED'])
                    events.append('candidate_boot_ready')
                release={'status':'released' if released else 'release_failed','released':released,
                         'warning':None,'receipt_sha256':'cd'*32}
                with mock.patch.object(live,'_reopen_candidate_observation',return_value=durable), \
                     mock.patch.object(live,'_p343_proof_ok',return_value=True), \
                     mock.patch.object(resident,'binding_for',return_value=exploration_fixture.binding()), \
                     mock.patch.object(live,'_seal_p300_before_candidate_boot_ready',side_effect=seal), \
                     mock.patch.object(live,'_state',side_effect=lambda *_:dict(state)), \
                     mock.patch.object(live,'_save_state',side_effect=lambda _,v:state.update(v)), \
                     mock.patch.object(live,'_reopen_candidate_guard_release',return_value=release), \
                     mock.patch.object(live,'_finish_rollback',return_value={'rollback':'requested'}) as rollback:
                    pending=resident.before_guard_release(live,prepared,journal,SimpleNamespace(completed=True),durable,None)
                    self.assertEqual(events,['OBSERVED','candidate_boot_ready'])
                    lease=resident.ResidentLease.open(prepared.run_dir/resident.DIRECTORY)
                    self.assertEqual(lease.snapshot()['state'],'ACTIVE')
                    result=resident.after_guard_release(live,prepared,None,journal,Path('/unused'),None,pending)
                    if released:
                        self.assertEqual(result['verdict'],'P343_EXPLORATION_SESSION_ACTIVE')
                        self.assertFalse(result['f1_closed'])
                        rollback.assert_not_called()
                        resident.mark_rollback_required(live,prepared)
                    else:
                        rollback.assert_called_once()
                    self.assertTrue(resident.ResidentLease.open(prepared.run_dir/resident.DIRECTORY).snapshot()['rollback_required'])
                    self.assertFalse(state['resident_session_active'])

    @staticmethod
    def prepared():
        return SimpleNamespace(bundle=SimpleNamespace(manifest={'observation':{
            'acceptance':live.typed_evidence.p343_stock_adapter.acceptance_fixture(),
            'candidate_observer':live.typed_evidence.p343_authenticated_open_read_branch_observer_spec(),
            live.typed_evidence.CANDIDATE_ARRIVAL_PROOF_ROLE_KEY:
                live.typed_evidence.CANDIDATE_AUTHENTICATED_LOGICAL_RESIDENT_EXEC_ROLE}}))

    @staticmethod
    def codec(clock):
        install=live.idle_reuse_probe.install
        def bound(module,**kwargs):
            return install(module,clock=clock.clock,pause=clock.pause,**kwargs)
        with mock.patch.object(live.idle_reuse_probe,'install',side_effect=bound):
            return live._p343_initial_observer_module(outer_deadline=300)

    def test_actual_initial_four_session_proof_is_distinct(self):
        module,result,proof,receipts=fixture.IdleReuseTests().exercise(codec_factory=self.codec)
        self.assertEqual(proof['run_id_hex'],live.typed_evidence.P343_RUN_ID)
        live.typed_evidence.validate_p343_open_read_branch_proof(proof)
        self.assertEqual(proof['idle_reuse'],receipts[0])
        with self.assertRaises(live._P342_INITIAL_OBSERVER.AuthObserverError):
            live._P342_INITIAL_OBSERVER.validate_proof_value(proof)

    def test_initial_usb_proof_is_not_named_exploration_success(self):
        prepared=self.prepared()
        self.assertTrue(live._p343_bundle(prepared.bundle))
        self.assertFalse(live._p342_bundle(prepared.bundle))
        for initial,named in ((False,False),(True,False),(False,True),(True,True)):
            state={live.typed_evidence.CANDIDATE_ARRIVAL_PROOF_STATE_KEY:{'proof':initial},
                   'p343_exploration_summary':{'proved':named}}
            with mock.patch.object(live,'_state',return_value=state):
                verdict,outcome=live._closed_terminal_classification(prepared)
            self.assertEqual(verdict,live.P343_SUCCESS_VERDICT if initial and named
                             else 'NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK')
        for foreign in ('p341_stock','p342_stock'):
            with self.assertRaisesRegex(live.F1LiveError,'foreign candidate'):
                live._validate_candidate_observer_state(prepared,{foreign:{}})

    def test_postrollback_records_named_summary_without_gating_transfer(self):
        class Recorded(Exception):pass
        prepared=self.prepared();prepared.run_dir=Path('/unused')
        summary={'proved':False,'completed_actions':0}
        projection={'proof_class':'NO_PROOF_OBSERVER'}
        backend=SimpleNamespace(verify_final=lambda *_:{'observer':{'accepted':False,'p343_stock':projection}})
        journal=SimpleNamespace(state=lambda:'ROLLBACK_FLASHED',transition=mock.Mock(side_effect=Recorded))
        with mock.patch.object(live,'_events',return_value={'rollback_flash_done'}), \
             mock.patch.object(live,'_state',return_value={}), \
             mock.patch.object(live.p343_exploration_session,'action_summary',return_value=summary), \
             mock.patch.object(live,'_save_state') as saved,self.assertRaises(Recorded):
            live._finish_rollback(prepared,backend,journal,Path('/unused'),None)
        value=saved.call_args.args[1]
        self.assertIs(value['p343_stock'],projection)
        self.assertIs(value['p343_exploration_summary'],summary)
        self.assertTrue(value['final_verified'])

    def test_state_bound_and_cli_closed_names(self):
        prepared=self.prepared()
        with tempfile.TemporaryDirectory() as directory:
            prepared.run_dir=Path(directory)
            live._save_state(prepared,{'test':'x'*33084})
            self.assertEqual(len(live._state(prepared)['test']),33084)
        parser=live.build_parser()
        self.assertEqual(parser.parse_args(['--resident-action','memory']).resident_action,'memory')
        with self.assertRaises(SystemExit):
            parser.parse_args(['--resident-action','reboot'])


if __name__=='__main__':unittest.main()

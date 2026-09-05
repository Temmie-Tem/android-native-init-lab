"""Actual P342 producer/consumer and recovery dispatch; no device effects."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'workspace/public/src/scripts/revalidation'), str(ROOT / 'tests')]
import device_action_f1_live_v2 as live
import s22plus_fyg8_idle_reuse_probe as probe
import device_action_raw_capture_v1 as raw_capture
import test_s22plus_fyg8_idle_reuse_probe as fixture


class P342LiveTests(unittest.TestCase):
    @staticmethod
    def prepared():
        return SimpleNamespace(bundle=SimpleNamespace(manifest={'observation': {
            'acceptance': live.typed_evidence.p342_stock_adapter.acceptance_fixture(),
            'candidate_observer': live.typed_evidence.p342_authenticated_open_read_branch_observer_spec(),
            live.typed_evidence.CANDIDATE_ARRIVAL_PROOF_ROLE_KEY:
            live.typed_evidence.CANDIDATE_AUTHENTICATED_LOGICAL_RESIDENT_EXEC_ROLE}}))

    @staticmethod
    def codec(clock):
        actual_install = probe.install
        def install(module, **kwargs):
            return actual_install(module, clock=clock.clock, pause=clock.pause, **kwargs)
        with mock.patch.object(probe, 'install', side_effect=install):
            return live._p342_initial_observer_module(outer_deadline=300)

    def test_actual_four_session_producer_parser_and_timing(self):
        module, result, proof, receipts = fixture.IdleReuseTests().exercise(codec_factory=self.codec)
        self.assertEqual(proof['run_id_hex'], live.p342_open_read_runtime.P342_RUN_ID_HEX)
        self.assertEqual(proof['idle_reuse'], receipts[0])
        module.validate_proof_value(proof)
        live.typed_evidence.validate_p342_open_read_branch_proof(proof)
        for corrupt in ('missing', 'short', 'wrong-session'):
            changed = copy.deepcopy(proof)
            if corrupt == 'missing':
                changed.pop('idle_reuse')
            elif corrupt == 'short':
                changed['idle_reuse']['elapsed_seconds'] = 119
            else:
                changed['sessions'][2]['physical_reopen_index'] = 1
            with self.assertRaises(module.AuthObserverError):
                module.validate_proof_value(changed)

    def test_actual_idle_failure_paths(self):
        for kwargs in ({'idle_noise':True}, {'idle_cut':True},
                       {'idle_noise':True,'writer_failure':True}, {'reopen_failure':True}):
            fixture.IdleReuseTests().exercise(codec_factory=self.codec, **kwargs)

    def test_distinct_namespace_and_closed_terminal(self):
        prepared = self.prepared()
        self.assertTrue(live._p342_bundle(prepared.bundle))
        self.assertFalse(live._p341_bundle(prepared.bundle))
        self.assertTrue(live._host_first_bundle(prepared.bundle))
        variant = live._host_first_variant(prepared.bundle)
        self.assertEqual(variant.text('p341_stock'), 'p342_stock')
        self.assertEqual(variant.text('P3.41'), 'P3.42')
        for success in (False, True):
            state = {live.typed_evidence.CANDIDATE_ARRIVAL_PROOF_STATE_KEY: {'proof':success}}
            with mock.patch.object(live, '_state', return_value=state):
                verdict, outcome = live._closed_terminal_classification(prepared)
            self.assertEqual(verdict, live.P342_SUCCESS_VERDICT if success else 'NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK')
            self.assertEqual(outcome, live.P342_SUCCESS_OUTCOME if success else live.P342_NO_PROOF_OUTCOME)
        for old in ('p341_stock', 'p341_authenticated_open_read_branch_resident'):
            with self.assertRaisesRegex(live.F1LiveError, 'foreign candidate'):
                live._validate_candidate_observer_state(prepared, {old:{}})

    def test_final_health_publication_uses_p342(self):
        class Recorded(Exception): pass
        prepared = self.prepared()
        prepared.run_dir = Path('/unused')
        projection = {'proof_class':'NO_PROOF_OBSERVER'}
        backend = SimpleNamespace(verify_final=lambda *_: {'observer':{'accepted':False, 'p342_stock':projection}})
        journal = SimpleNamespace(state=lambda:'ROLLBACK_FLASHED', transition=mock.Mock(side_effect=Recorded))
        with mock.patch.object(live, '_events', return_value={'rollback_flash_done'}), \
             mock.patch.object(live, '_state', return_value={}), \
             mock.patch.object(live, '_save_state') as saved, self.assertRaises(Recorded):
            live._finish_rollback(prepared, backend, journal, Path('/unused'), None)
        state = saved.call_args.args[1]
        self.assertIs(state['p342_stock'], projection)
        self.assertNotIn('p341_stock', state)
        self.assertNotIn('p328_stock', state)
        self.assertTrue(state['final_verified'])

    def test_only_p342_state_uses_existing_terminal_bound(self):
        with tempfile.TemporaryDirectory(prefix='p342-state-bound-h0-') as name:
            prepared = self.prepared()
            prepared.run_dir = Path(name)
            value = {'fixture': 'x' * 33084}
            live._save_state(prepared, value)
            self.assertEqual(live._state(prepared)['fixture'], value['fixture'])
            with self.assertRaises(live.F1LiveError):
                live._save_state(prepared, {'fixture':'x' * 65536})
            old = SimpleNamespace(run_dir=Path(name), bundle=SimpleNamespace(manifest=json.loads(
                (ROOT/'workspace/public/src/device-action/manifests/s22plus_fyg8_p341_process_v2_ready_1.json').read_bytes())))
            with self.assertRaises(live.F1LiveError):
                live._save_state(old, value)

    def test_actual_receipt_publication_and_raw_reopen(self):
        module, result, proof, receipts = fixture.IdleReuseTests().exercise(codec_factory=self.codec)
        with tempfile.TemporaryDirectory(prefix='p342-receipt-h0-') as name:
            directory = Path(name)
            writer = raw_capture.RawCaptureWriter(directory, 'candidate-observer',
                stdout_maximum=16384, stderr_maximum=64, argv0_name='local-pty-fixture',
                stdout_name='candidate-observer.raw', stderr_name='candidate-observer.raw.stderr')
            writer.write_stdout(b''.join(item.raw_rx for item in result.sessions))
            handle = writer.finalize(returncode=0)
            identity = live._receipt(handle.stdout_path, 'local raw')
            identity['capture_receipt'] = live._receipt(handle.receipt_path, 'local capture')
            base = dict(binding={}, spec_sha256='01'*32, baseline_sha256='02'*32,
                download_departure_sha256='03'*32, download_endpoint_absent=True,
                topology_sha256='04'*32, endpoint_identity_sha256='05'*32,
                guard_sha256='06'*32, raw=identity, banner_seen=True, ready_seen=True,
                done_seen=True, lane={}, bounded=True, elapsed_sec=120.1,
                classification='accepted', accepted=True)
            key = bytes(range(32)); key_sha = hashlib.sha256(key).hexdigest()
            session = live._P342ObserverSession(delegate=None, base=None, spec={},
                run_dir=directory, lane_binding={}, lane_binding_receipt={},
                usb_root=Path('/unused/usb'), typec_root=Path('/unused/typec'),
                auth_key=key, auth_key_sha256=key_sha)
            session.auth_observer = module
            session.resident_result = result
            session.proof = proof
            with mock.patch.object(live._P327ObserverSession, '_observe_value', return_value=(base, {})):
                value = session.observe(timeout_sec=300, download_departure={'absent':True})
            path = directory/'candidate-observer.json'
            self.assertEqual(live._read_json(path, 'local published receipt'), value)
            self.assertEqual(value['idle_reuse'], receipts)
            self.assertEqual(value['command_count'], 12)
            lane = {key:True for key in ('both_topologies_inventory_complete',
                'accepted_inventory_exact', 'same_run_typec_partner_continuity', 'accepted_for_p324')}
            with mock.patch.object(live, '_p328_validate_common_receipt', return_value=(lane,'04'*32,'05'*32)), \
                 mock.patch.object(live, '_p328_bound_auth_key_identity', return_value={'size':32,'sha256':key_sha}):
                reopened = live._p342_validate_receipt(SimpleNamespace(run_dir=directory), path, {})
            self.assertTrue(reopened['accepted'])
            self.assertTrue(live._p342_proof_ok(reopened))
            self.assertEqual(reopened['idle_reuse'], receipts)

    def test_outer_deadline_stops_before_post_idle_open(self):
        actual_install = probe.install
        def codec(clock):
            def install(module, **kwargs):
                return actual_install(module, clock=clock.clock, pause=clock.pause, **kwargs)
            with mock.patch.object(probe, 'install', side_effect=install):
                return live._p342_initial_observer_module(outer_deadline=30)
        fixture.IdleReuseTests().exercise(codec_factory=codec, idle_cut=True, deadline_only=True)
        module = live._p342_initial_observer_module(outer_deadline=0)
        import os
        master, slave = os.openpty()
        try:
            with self.assertRaises(module.RetainedListenerObserverError) as caught:
                module.exchange_retained(slave, bytes(range(32)),
                    reopen=lambda: self.fail('deadline cannot reopen'))
            self.assertEqual(caught.exception.result.sessions[-1].raw_tx, b'')
            self.assertEqual(caught.exception.result.sessions[-1].failure_stage, 'observation-deadline')
        finally:
            os.close(master)
            try: os.close(slave)
            except OSError: pass

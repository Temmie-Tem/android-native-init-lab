"""P345 owner acquisition/publication seams; no USB or device contact."""
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import types
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'workspace/public/src/scripts/revalidation'))
import device_action_f1_live_v2 as live
import device_action_raw_capture_v1 as raw


class LiveObserverTests(unittest.TestCase):
    def test_durable_reopen_and_arrival_require_rollback_and_health(self):
        from test_s22plus_fyg8_p345_live_receipt import _ReceiptFixture, KEY, KEY_SHA256
        with tempfile.TemporaryDirectory() as directory:
            fixture=_ReceiptFixture(Path(directory)/'run')
            audits=[live.p345_shell_observer.parse_captured_session(fixture.codec,rx,tx,KEY).session.audit
                for rx,tx in zip(fixture.rx_streams,fixture.tx_streams)]
            value=dict(fixture.value)
            value.update(preauth_diagnostics=[[{'stage':d.stage,'code':d.code} for d in a.diagnostics] for a in audits],
                rng_eagain_retries=[a.rng_eagain_retries for a in audits],
                partial_sessions=[{'current_stage':a.current_stage,'failure_stage':a.failure_stage} for a in audits])
            fixture.publish(value)
            state={'candidate_classification':'odin_transfer_completed','candidate_completed':True,
                'download_endpoint_absent':True,'rollback_classification':'odin_transfer_completed',
                'rollback_completed':True,'final_verified':True}
            with mock.patch.object(live,'_p328_read_auth_key',return_value=(KEY,KEY_SHA256)), \
                 mock.patch.object(live,'_reopen_candidate_guard_release',return_value={'status':'released','released':True}):
                durable=live._reopen_candidate_observation(fixture.prepared)
                self.assertTrue(live._p345_proof_ok(durable))
                proof=live._candidate_arrival_proof_projection(fixture.prepared,state)
                self.assertTrue(proof['proof'])
                self.assertFalse(proof['later_action_lease_active'])
                self.assertNotIn('resident_lease_schema',proof)
                closed=dict(state)
                closed[live.typed_evidence.CANDIDATE_ARRIVAL_PROOF_STATE_KEY]=proof
                with mock.patch.object(live,'_state',return_value=closed):
                    self.assertEqual(live._closed_terminal_classification(fixture.prepared),
                        (live.typed_evidence.P345_AUTH_EXEC_VERDICT,
                         live.typed_evidence.P345_AUTH_EXEC_OUTCOME))
                for field in ('rollback_completed','final_verified','candidate_completed'):
                    bad=dict(state);bad[field]=False
                    self.assertFalse(live._candidate_arrival_proof_projection(fixture.prepared,bad)['proof'])

    def test_partial_p345_observation_skips_legacy_projection_and_is_json_stable(self):
        from test_s22plus_fyg8_p345_live_receipt import _ReceiptFixture
        with tempfile.TemporaryDirectory() as directory:
            fixture = _ReceiptFixture(Path(directory) / 'run')
            fixture.prepared.bundle.manifest['observation']['timeout_sec'] = 300
            durable = dict(fixture.value)
            durable.update(accepted=False, classification='authenticated-session-error',
                receipt_sha256='a' * 64, preauth_diagnostics=[], rng_eagain_retries=[],
                partial_sessions=[{'current_stage': 'exec-read', 'failure_stage': 'exec-read'}],
                p345_readonly_research_shell_qualification={'proved': False, 'session_count': 0},
                qualification_complete=False, session_count=0, command_count=0,
                pid1_framed_exec_proof=False, busybox_ash_command_proof=False,
                framed_session_closed=False, same_tty_fd=False)
            self.assertNotIn('hmac_authenticated', durable)
            backend = object.__new__(live.SamsungOdinBackend)
            backend.odin = Path('/unused')
            absent = types.SimpleNamespace(absent=True, timed_out=False, next_sequence=1)
            with mock.patch.object(live.odin_core, 'list_snapshot_receipts', return_value=[]), \
                 mock.patch.object(live.odin_core, 'wait_for_no_live_endpoint', return_value=absent), \
                 mock.patch.object(live, '_reopen_candidate_observation', return_value=durable):
                value = backend.observe_candidate(fixture.prepared, fixture.run_dir, None, None)
            self.assertFalse(value['candidate_execution_proven'])
            self.assertFalse(value['qualification_complete'])
            self.assertEqual(value['session_count'], 0)
            self.assertEqual(json.loads(json.dumps(value)), value)
            variant = live._host_first_variant(fixture.prepared.bundle)
            metadata = {'branches': variant.OPEN_READ_BRANCH_ORDINALS,
                        'stages': variant.OPEN_HEADER_WORD_STAGES}
            self.assertEqual(json.loads(json.dumps(metadata)), metadata)

    def test_actual_acquisition_retains_semantic_failure_and_closes_fd(self):
        master,slave=os.openpty()
        try:
            path=Path(os.ttyname(slave))
            endpoint=types.SimpleNamespace(tty_name=path.name)
            base=types.SimpleNamespace(dev_root=path.parent,
                _raw_tty=lambda fd: live.cdc_acm_observer.ObserverSession._raw_tty(None,fd))
            with tempfile.TemporaryDirectory() as directory:
                root=Path(directory)
                owner=live._P345ObserverSession(None,base,{},root,{}, {},Path('/unused'),Path('/unused'))
                owner._settle_guard_properties=lambda *args: None
                owner._endpoint_exact=lambda *args: True
                audit=types.SimpleNamespace(tx=b'failed-tx',rx=b'failed-rx',
                    banner_seen=True,ready_seen=True,done_seen=True)
                failure=live.p345_shell_observer.QualificationError('semantic rejection',
                    partial_receipt={'proved':False},audit=audit)
                descriptors=[]
                def fail(codec,fd,key,boot,nonces,writer,*,deadline):
                    descriptors.append(fd)
                    self.assertIsNone(boot);self.assertEqual(nonces,set())
                    writer.write_stdout(audit.rx)
                    raise failure
                writer=raw.RawCaptureWriter(root,'test',stdout_maximum=4096,stderr_maximum=1)
                with mock.patch.object(live.p345_shell_observer,'qualify',side_effect=fail):
                    classification=owner._read_endpoint(endpoint,time.monotonic()+5,writer)
                self.assertEqual(classification,'authenticated-session-error')
                self.assertEqual(owner.exchange.audit.tx,b'failed-tx')
                self.assertEqual(owner.exchange.audit.rx,b'failed-rx')
                self.assertEqual(owner.proof,{'proved':False})
                with self.assertRaises(OSError):os.fstat(descriptors[0])
                receipt=writer.finalize(returncode=0)
                self.assertEqual(raw.read_stdout(receipt,maximum=4096),b'failed-rx')
                self.assertEqual(hashlib.sha256(b'failed-rx').hexdigest(),
                    hashlib.sha256(owner.exchange.audit.rx).hexdigest())
        finally:
            os.close(slave);os.close(master)


if __name__=='__main__':unittest.main()

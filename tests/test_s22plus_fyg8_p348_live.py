"""P348 retained routing, real raw replay and descriptor ownership, H0 only."""
from pathlib import Path
import copy
import contextlib
import io
import hashlib
import os
import tempfile
import time
import types
import unittest
from unittest import mock

from test_s22plus_fyg8_p345_live_receipt import _ReceiptFixture, KEY, KEY_SHA256, BOOT_ID
import device_action_f1_live_v2 as live


class P348ReceiptFixture(_ReceiptFixture):
    def __init__(self, run_dir):
        super().__init__(run_dir, variant='p348')

    def _session(self, ordinal):
        if ordinal == 6:
            with mock.patch.object(self.observer, 'PIPELINE_MARKER', self.observer.REOPEN_WITNESS_MARKER):
                return super()._session(ordinal)
        return super()._session(ordinal)

    def _qualification_proof(self):
        rows = []
        rx_offset = tx_offset = 0
        for ordinal, step in enumerate(self.observer.QUALIFICATION_COMMANDS, 1):
            rx, tx = self._session(ordinal)
            parsed = self.observer.parse_captured_session(self.codec, rx, tx, KEY)
            self.audits.append(parsed.session.audit)
            row = self.observer.validate_session_result(parsed, step)
            row['rx']['offset'] = rx_offset
            row['tx']['offset'] = tx_offset
            rows.append(row)
            self.rx_streams.append(rx)
            self.tx_streams.append(tx)
            rx_offset += len(rx)
            tx_offset += len(tx)
        proof = self.observer._base_receipt(rows,
            expected_boot_sha256=hashlib.sha256(BOOT_ID).hexdigest(), proved=True,
            reopen={'idle_duration_ms':120000, 'physical_reopen_count':1,
                'initial_five_same_tty_fd':True, 'same_tty_fd':False, 'callback_invoked':True})
        self.observer.validate_qualification(proof)
        return proof

    def _receipt_value(self):
        value = super()._receipt_value()
        value.update(same_tty_fd=False, initial_five_same_tty_fd=True,
            session_count=6, command_count=18, physical_reopen_count=1,
            idle_duration_ms=120000)
        return value


class PrecloseTrailingFixture(P348ReceiptFixture):
    def _qualification_proof(self):
        complete = super()._qualification_proof()
        self.rx_streams = self.rx_streams[:5]
        self.tx_streams = self.tx_streams[:5]
        self.audits = self.audits[:5]
        return self.observer._base_receipt(complete['sessions'][:5],
            expected_boot_sha256=complete['expected_boot_sha256'], proved=False,
            failure={'name':'clean-tty-reopen-witness', 'error':'trailing-byte'})

    def _write_raw_capture(self):
        self.payload += b'!'
        super()._write_raw_capture()

    def _receipt_value(self):
        value = super()._receipt_value()
        value.update(accepted=False, classification='authenticated-session-error',
            qualification_complete=False, pid1_framed_exec_proof=False,
            busybox_ash_command_proof=False, framed_session_closed=False,
            session_count=5, command_count=15, physical_reopen_count=0,
            initial_five_same_tty_fd=False, idle_duration_ms=0,
            trailing_bytes_seen=1, trailing_rx=live._p327_identity(b'!'),
            rx=live._p327_identity(self.payload[:-1]))
        return value


class P348LiveTests(unittest.TestCase):
    def test_retained_owner_requires_new_variant_and_later_proof(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture = P348ReceiptFixture(Path(directory)/'run')
            self.assertTrue(live._p348_bundle(fixture.prepared.bundle))
            self.assertIs(live._exploration_owner(fixture.prepared.bundle), live.p348_shell_session)
            with mock.patch.object(live, '_p328_read_auth_key', return_value=(KEY, KEY_SHA256)), \
                 mock.patch.object(live, '_reopen_candidate_guard_release',
                    return_value={'status':'released', 'released':True}):
                durable = live._reopen_candidate_observation(fixture.prepared)
                self.assertTrue(live._p348_proof_ok(durable))
                state = {'candidate_classification':'odin_transfer_completed', 'candidate_completed':True,
                    'download_endpoint_absent':True, 'rollback_classification':'odin_transfer_completed',
                    'rollback_completed':True, 'final_verified':True}
                proof = live._candidate_arrival_proof_projection(fixture.prepared, state)
                self.assertTrue(proof['proof'])
                state[live.typed_evidence.CANDIDATE_ARRIVAL_PROOF_STATE_KEY] = proof
                key = live._exploration_summary_key(fixture.prepared.bundle)
                for completed in (False, True):
                    state[key] = {'proved':completed}
                    with mock.patch.object(live, '_state', return_value=state):
                        verdict, _ = live._closed_terminal_classification(fixture.prepared)
                    self.assertEqual(verdict.startswith('PASS_'), completed)
            for field, invalid in (('idle_duration_ms',119999), ('physical_reopen_count',0),
                                   ('initial_five_same_tty_fd',False), ('same_tty_fd',True)):
                bad = copy.deepcopy(fixture.value)
                bad[field] = invalid
                fixture.publish(bad)
                with mock.patch.object(live, '_p328_read_auth_key', return_value=(KEY, KEY_SHA256)):
                    with self.assertRaises(live.F1LiveError):
                        live._p345_validate_receipt(fixture.prepared, fixture.run_dir/'candidate-observer.json', fixture.spec)

    def test_preclose_trailing_byte_stop_receipt_reopens(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture = PrecloseTrailingFixture(Path(directory)/'run')
            with mock.patch.object(live, '_p328_read_auth_key', return_value=(KEY,KEY_SHA256)):
                value = live._p345_validate_receipt(fixture.prepared,
                    fixture.run_dir/'candidate-observer.json', fixture.spec)
            self.assertFalse(value['accepted'])
            self.assertEqual(value['trailing_bytes_seen'],1)
            self.assertEqual(value['session_count'],5)

    def test_actual_arm_uses_p348_owner_and_rejects_five_session_spec(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture = P348ReceiptFixture(Path(directory)/'run')
            inherited = types.SimpleNamespace(delegate=types.SimpleNamespace(delegate=object()))
            with mock.patch.object(live, '_p328_read_auth_key', return_value=(KEY,KEY_SHA256)), \
                 mock.patch.object(live.p325_guard_adapter, 'observer_session',
                    side_effect=lambda *a,**k:contextlib.nullcontext(inherited)) as guard:
                arguments = dict(lane_value={},lane_receipt={},usb_root=Path('/no-usb'),typec_root=Path('/no-typec'))
                with live._p345_candidate_observer_session(fixture.prepared, fixture.spec, **arguments) as owner:
                    self.assertIsInstance(owner,live._P348ObserverSession)
                    self.assertEqual(owner.namespace,'p348')
                guard.reset_mock()
                with self.assertRaises(live.F1LiveError):
                    with live._p345_candidate_observer_session(fixture.prepared,
                            dict(fixture.spec,total_session_count=5), **arguments):
                        self.fail('old geometry was admitted')
                guard.assert_not_called()

    def test_publication_order_and_nonreleased_warning_cannot_open_lease(self):
        from test_s22plus_fyg8_p348_shell_session import binding
        resident = live.p348_shell_session
        for released in (True,False):
            with self.subTest(released=released), tempfile.TemporaryDirectory() as directory:
                fixture = P348ReceiptFixture(Path(directory)/'run')
                prepared = fixture.prepared
                prepared.bundle.manifest['run_id']='fixture-run'
                events=[]
                state={}
                journal=types.SimpleNamespace(transition=lambda *args:events.append(args[0]),
                    records=lambda:[{'record_sha256':'ab'*32}])
                durable={'accepted':True,'download_endpoint_absent':True}
                def seal(*args):
                    self.assertEqual(events,['OBSERVED'])
                    self.assertFalse((prepared.run_dir/resident.DIRECTORY).exists())
                    events.append('candidate_boot_ready')
                warning = next(iter(live.NON_TAINTING_GUARD_WARNINGS))
                release={'status':'released' if released else warning,'released':released,
                    'warning':None if released else warning,'receipt_sha256':'cd'*32}
                with mock.patch.object(live,'_reopen_candidate_observation',return_value=durable), \
                     mock.patch.object(live,'_p348_proof_ok',return_value=True), \
                     mock.patch.object(resident,'binding_for',return_value=binding()), \
                     mock.patch.object(live,'_seal_p300_before_candidate_boot_ready',side_effect=seal), \
                     mock.patch.object(live,'_state',side_effect=lambda *_:dict(state)), \
                     mock.patch.object(live,'_save_state',side_effect=lambda _,value:state.update(value)), \
                     mock.patch.object(live,'_reopen_candidate_guard_release',return_value=release), \
                     mock.patch.object(live,'_finish_rollback',return_value={'rollback':'requested'}) as rollback:
                    pending=resident.before_guard_release(live,prepared,journal,
                        types.SimpleNamespace(completed=True),durable,None)
                    self.assertEqual(events,['OBSERVED','candidate_boot_ready'])
                    result=resident.after_guard_release(live,prepared,None,journal,Path('/unused'),None,pending)
                    if released:
                        self.assertEqual(result['verdict'],'P348_RETAINED_SHELL_SESSION_ACTIVE')
                        self.assertFalse(result['f1_closed'])
                        rollback.assert_not_called()
                    else:
                        rollback.assert_called_once()
                        self.assertFalse(state['p348_shell_session_active'])
                        self.assertTrue(resident.ShellLease.open(prepared.run_dir/resident.DIRECTORY).snapshot()['rollback_required'])

    def test_status_cli_uses_host_owner_without_backend_or_transport(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture = P348ReceiptFixture(Path(directory)/'run')
            with mock.patch.object(live, 'load_prepared', return_value=fixture.prepared), \
                 mock.patch.object(live.p348_shell_action, 'status', return_value={'state':'ACTIVE'}) as status, \
                 mock.patch.object(live, 'SamsungOdinBackend', side_effect=AssertionError('status contacted backend')), \
                 contextlib.redirect_stdout(io.StringIO()):
                rc = live.main(['--shell-status','--run-dir',str(fixture.run_dir)])
            self.assertEqual(rc,0)
            status.assert_called_once()

    def test_legacy_shell_does_not_acquire_retained_owner(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture = _ReceiptFixture(Path(directory)/'run', variant='p347')
            self.assertFalse(live._named_exploration_bundle(fixture.prepared.bundle))
            with self.assertRaises(live.F1LiveError):
                live._exploration_owner(fixture.prepared.bundle)

    def test_reopen_failure_closes_current_descriptor_and_preserves_partial(self):
        master, slave = os.openpty()
        try:
            path = Path(os.ttyname(slave))
            with tempfile.TemporaryDirectory() as directory:
                base = types.SimpleNamespace(dev_root=path.parent, _raw_tty=lambda fd:None)
                observer = live.typed_evidence.SHELL_VARIANTS['p348'].observer
                runtime = live.typed_evidence.SHELL_VARIANTS['p348'].runtime
                owner = live._P348ObserverSession(None,base,{},Path(directory),{},{},Path('/unused'),Path('/unused'),
                    namespace='p348', qualification_observer=observer, auth_runtime=runtime)
                owner._settle_guard_properties = lambda *args:None
                owner._endpoint_exact = lambda *args:True
                recorded=[]
                def qualify(codec, fd, key, boot, nonces, writer, *, deadline, reopen_after_idle):
                    recorded.append(fd)
                    try:
                        reopen_after_idle()
                    except Exception as exc:
                        raise observer.QualificationError('idle rejected', partial_receipt={'proved':False}) from exc
                    self.fail('short deadline should not reopen')
                writer = live.raw_capture.RawCaptureWriter(Path(directory),'test',stdout_maximum=4096,stderr_maximum=1)
                with mock.patch.object(observer,'qualify',side_effect=qualify), \
                     mock.patch.object(live,'_p327_trailing_probe',return_value=b''):
                    result = owner._read_endpoint(types.SimpleNamespace(tty_name=path.name), time.monotonic()+10,writer)
                self.assertEqual(result,'authenticated-session-error')
                self.assertIsNone(owner.owned_descriptor)
                with self.assertRaises(OSError):
                    os.fstat(recorded[0])
                writer.finalize(returncode=0)
        finally:
            os.close(slave)
            os.close(master)


if __name__ == '__main__':
    unittest.main()

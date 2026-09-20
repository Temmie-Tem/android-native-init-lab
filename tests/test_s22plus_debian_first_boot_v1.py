"""H0 owner cuts/protocol checks. No device/NetworkManager operation is invoked."""
from contextlib import ExitStack, nullcontext
from dataclasses import dataclass
import builtins
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'workspace/public/src/scripts/revalidation'))
import s22plus_debian_first_boot_v1 as lane
import s22plus_native_records_v3 as records


class Cut(Exception):
    pass


@dataclass
class Ticket:
    device: str = 'H0 endpoint fixture'


class OwnerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)

    def capture(self, body=b'', *, stderr=b'', rc=0, timeout=False, overflow=False, fault=None):
        folder = self.path / ('capture-' + str(len(list(self.path.glob('capture-*')))))
        folder.mkdir()
        writer = lane.raw.RawCaptureWriter(folder, 'fixture', stdout_maximum=65536, stderr_maximum=16384)
        writer.write_stdout(body); writer.write_stderr(stderr)
        return writer.finalize(returncode=rc, timed_out=timeout, output_exceeded=overflow, producer_error_type=fault)

    def owner(self):
        owner = object.__new__(lane.Owner)
        owner.directory = self.path
        owner.plan_receipt = dict(path=str(self.path / 'plan.json'), size=10, sha256='a' * 64)
        owner.plan = dict(review={}, candidate=dict(run_id='c' * 32), link=dict(ssh_address='192.0.2.2'))
        owner.journal = lane.Journal(self.path / 'journal')
        owner.grant = dict(deadline_ns=10**30)
        owner.guard = Mock()
        owner.recovery = True
        return owner

    def intent(self, owner, name):
        owner.journal.append('effect-intent', step=name, detail={})

    def result(self, owner, name):
        owner.journal.append('effect-result', step=name, receipt={})

    def observed(self, owner, name):
        owner.journal.append('observation', step=name, receipt={})

    def lifecycle_through_persistence(self, owner):
        for name in ('android-download', 'candidate-install'):
            self.intent(owner, name); self.result(owner, name)
        self.observed(owner, 'first-health')
        self.intent(owner, 'workload'); self.result(owner, 'workload')
        self.observed(owner, 'workload-result')
        self.intent(owner, 'debian-reboot'); self.result(owner, 'debian-reboot')
        self.observed(owner, 'second-health'); self.observed(owner, 'persistence')

    def test_host_restart_keeps_consumed_effect_with_smaller_clock(self):
        journal = lane.Journal(self.path / 'journal')
        with patch.object(lane, 'host_boot', return_value='a' * 64), patch.object(records, 'clock', return_value=9000):
            journal.append('effect-intent', step='android-download', detail={})
        with patch.object(lane, 'host_boot', return_value='b' * 64), patch.object(records, 'clock', return_value=10):
            journal.append('physical-recovery-armed', reason='HOST_RESTART')
        self.assertEqual(len(journal.segments()), 2)
        self.assertIn('android-download', lane.journal_state(journal)[0])
        first_tail = journal.segments()[1][1]['previous']
        self.assertEqual(first_tail, records.pin(self.path / 'journal/epoch-0000/events/0000.json'))

    def test_epoch_cut_before_publication_has_no_hidden_effect(self):
        journal = lane.Journal(self.path / 'journal')
        original = lane.os.rename
        with patch.object(lane.os, 'rename', side_effect=Cut):
            with self.assertRaises(Cut): journal.append('effect-intent', step='android-download', detail={})
        self.assertEqual(journal.rows(), [])
        journal.append('effect-intent', step='android-download', detail={})
        self.assertEqual(len(journal.rows()), 1)
        self.assertTrue(any(p.name.startswith('.epoch-') for p in journal.directory.iterdir()))

    def test_epoch_cut_after_rename_keeps_complete_empty_segment(self):
        journal = lane.Journal(self.path / 'journal')
        with patch.object(lane.BaseJournal, 'append', side_effect=Cut):
            with self.assertRaises(Cut): journal.append('effect-intent', step='android-download', detail={})
        self.assertEqual(len(journal.segments()), 1)
        self.assertEqual(journal.rows(), [])
        journal.append('effect-intent', step='android-download', detail={})
        self.assertEqual(len(journal.rows()), 1)

    def test_unpublished_epoch_with_event_is_rejected(self):
        journal = lane.Journal(self.path / 'journal')
        staging = journal.directory / ('.epoch-' + 'a' * 32 + '.tmp')
        (staging / 'events').mkdir(parents=True)
        (staging / 'events/0000.json').write_text('{}')
        with self.assertRaisesRegex(ValueError, 'unexpectedly contains events'): journal.rows()

    def test_duplicate_device_intent_and_wrong_observation_order_rejected(self):
        owner = self.owner()
        self.intent(owner, 'android-download')
        with self.assertRaisesRegex(ValueError, 'already consumed'): owner.intent('android-download', {})
        self.observed(owner, 'first-health')
        with self.assertRaisesRegex(ValueError, 'precedes'): lane.journal_state(owner.journal)

    def test_expiry_before_shutdown_is_incomplete_research_not_recovery_block(self):
        owner = self.owner(); self.lifecycle_through_persistence(owner)
        self.assertFalse(owner.research_proof())
        self.intent(owner, 'debian-shutdown')
        self.assertFalse(owner.research_proof())

    def test_unacknowledged_control_never_becomes_accepted_from_departure(self):
        for options in ({'body': b''}, {'body': b'DEBIAN_REBOOT_REQUEST_ACCEPTED\n', 'timeout': True},
                        {'body': b'DEBIAN_REBOOT_REQUEST_ACCEPTED\n', 'overflow': True},
                        {'body': b'DEBIAN_REBOOT_REQUEST_ACCEPTED\n', 'fault': 'OSError'},
                        {'body': b'DEBIAN_REBOOT_REQUEST_ACCEPTED\n', 'rc': 255, 'stderr': b'Permission denied\n'}):
            with self.subTest(options=options):
                with self.assertRaises(ValueError): lane.control_projection(self.capture(**options), 'reboot', '192.0.2.2')
        positive = self.capture(b'DEBIAN_REBOOT_REQUEST_ACCEPTED\n')
        self.assertTrue(lane.control_projection(positive, 'reboot', '192.0.2.2')['request_accepted'])

    def test_known_control_ack_then_planned_disconnect_is_bounded(self):
        handle = self.capture(b'DEBIAN_SHUTDOWN_REQUEST_ACCEPTED\n', rc=255,
            stderr=b'Connection to 192.0.2.2 closed by remote host.\r\n')
        self.assertFalse(lane.control_projection(handle, 'shutdown', '192.0.2.2')['transition_proved'])

    def test_wrong_successful_identity_is_not_retried(self):
        owner = self.owner()
        wrong = self.capture(b'S22PLUS_FYG8_DEBIAN_V1 ' + b'd' * 32 + b'\nDEBIAN_HEALTH_PASS\n')
        owner.ssh = Mock(return_value=wrong)
        with self.assertRaisesRegex(ValueError, 'contradictory'): owner.observe_debian('first-health', {})
        self.assertEqual(owner.ssh.call_count, 1)

    def test_ambiguous_successful_boot_is_not_retried(self):
        owner = self.owner()
        body = (b'S22PLUS_FYG8_DEBIAN_V1 ' + b'c' * 32 + b'\n'
            b'boot_id=11111111-2222-4333-8444-555555555555\n'
            b'boot_id=11111111-2222-4333-8444-555555555555\nboot_count=1\nDEBIAN_HEALTH_PASS\n')
        owner.ssh = Mock(return_value=self.capture(body))
        with self.assertRaisesRegex(ValueError, 'ambiguous'): owner.observe_debian('first-health', {})
        self.assertEqual(owner.ssh.call_count, 1)

    def test_hard_cut_without_failure_handler_still_reaches_original_A(self):
        owner = self.owner(); self.intent(owner, 'android-download')
        owner.transfer = Mock(side_effect=Cut)
        with patch.object(lane.registry, 'target_session_lease', return_value=nullcontext()):
            with self.assertRaises(Cut): owner.close(operator_statement='Attended physical Download in this H0 fixture')
        owner.transfer.assert_called_once_with('android-restore')
        self.assertTrue(any(r['event'] == 'physical-recovery-armed' for r in owner.journal.rows()))

    def test_preintent_download_timeout_does_not_consume_A_or_collide_on_resume(self):
        owner = self.owner(); self.intent(owner, 'android-download')
        owner.transfer = Mock(side_effect=[TimeoutError('no endpoint'), Cut()])
        with patch.object(lane.registry, 'target_session_lease', side_effect=lambda *a, **k: nullcontext()):
            with self.assertRaises(TimeoutError): owner.close(operator_statement='Attended, first observation')
            with self.assertRaises(Cut): owner.close(operator_statement='Attended, resumed observation')
        self.assertEqual(owner.transfer.call_count, 2)
        self.assertNotIn('android-restore', lane.journal_state(owner.journal)[0])
        self.assertEqual(len(list(self.path.glob('physical-download-statement-*.json'))), 2)

    def test_original_A_intent_never_transfers_again(self):
        owner = self.owner(); self.intent(owner, 'android-download')
        owner.journal.append('effect-intent', step='android-restore', detail={'capture_directory': str(self.path / 'android-restore-transfer' / ('attempt-' + 'a' * 32))})
        owner.transfer = Mock(side_effect=AssertionError('must not transfer'))
        owner.android_health = Mock(side_effect=Cut)
        with patch.object(lane.registry, 'target_session_lease', return_value=nullcontext()):
            with self.assertRaises(Cut): owner.close(operator_statement='')
        owner.transfer.assert_not_called()
        owner.android_health.assert_called_once()

    def test_transfer_method_rejects_consumed_A_before_tool_or_folder(self):
        owner = self.owner()
        owner.plan['A'] = {'ap': {}}
        owner.journal.append('effect-intent', step='android-restore', detail={})
        with patch.object(lane.transport, 'execute_odin_boot_only') as transfer:
            with self.assertRaisesRegex(ValueError, 'already consumed'): owner.transfer('android-restore')
        transfer.assert_not_called()

    def test_real_transfer_timeout_resume_and_consumed_A_cut(self):
        owner = self.owner(); self.intent(owner, 'android-download')
        artifact = dict(path=str(self.path / 'A.tar.md5'), size=1, sha256='a' * 64)
        owner.plan.update(A=dict(ap=artifact), odin=dict(path=str(self.path / 'odin'), size=1, sha256='b' * 64))
        owner.android_health = Mock(side_effect=Cut)
        found = SimpleNamespace(ticket=Ticket(), timed_out=False, next_sequence=1)
        launches = []
        def produce(*args, **kwargs):
            kwargs['before_launch']()
            # A producer starts only after its durable intent and fresh ticket.
            self.assertIn('android-restore', lane.journal_state(owner.journal)[0])
            launches.append(kwargs['capture_dir'])
            writer = lane.raw.RawCaptureWriter(kwargs['capture_dir'], 'odin', stdout_maximum=65536, stderr_maximum=16384)
            writer.write_stdout(b'Setup Connection\nUpload Binaries\nboot.img.lz4\n100%\nClose Connection\n')
            handle = writer.finalize(returncode=0, timed_out=False, output_exceeded=False, producer_error_type=None)
            return {'H0': True}, handle
        def pinned(path, **kwargs): return nullcontext(SimpleNamespace(path=path))
        with ExitStack() as stack:
            for object_, name, replacement in (
                (lane.registry, 'target_session_lease', lambda *a: nullcontext()),
                (lane.transport, 'pin_regular_file', pinned), (lane.transport, 'pin_boot_only_ap', pinned),
                (lane.transport, 'revalidate_pinned_path', lambda *a: None),
                (lane.transition, 'transaction_session', lambda *a: nullcontext('H0 lease')),
                (lane.transition, 'revalidate_endpoint_ticket', lambda *a, **k: {'H0': True}),
                (lane.target, 'download_identity', lambda *a: {'H0': True}),
                (lane.transport, 'execute_odin_boot_only', produce)):
                stack.enter_context(patch.object(object_, name, side_effect=replacement))
            waiter = stack.enter_context(patch.object(lane.transition, 'wait_for_single_live_endpoint',
                side_effect=[SimpleNamespace(ticket=None, timed_out=True), found]))
            with self.assertRaisesRegex(ValueError, 'did not arrive'):
                owner.close(operator_statement='H0 attendance fixture one')
            self.assertEqual(launches, [])
            self.assertNotIn('android-restore', lane.journal_state(owner.journal)[0])
            with self.assertRaises(Cut): owner.close(operator_statement='H0 attendance fixture two')
            with self.assertRaises(Cut): owner.close(operator_statement='')
            self.assertEqual(waiter.call_count, 2)
        self.assertEqual(len(launches), 1)
        self.assertEqual(len(list((self.path / 'android-restore-transfer').iterdir())), 2)
        self.assertTrue(owner.transfer_proved('android-restore'))
        self.assertEqual(sum(row['event'] == 'effect-intent' and row['data']['step'] == 'android-restore'
                             for row in owner.journal.rows()), 1)

    def test_grant_cannot_extend_budget_or_move_to_a_new_host_epoch(self):
        receipt = dict(path='H0 plan', size=1, sha256='a' * 64)
        grant = dict(schema=lane.SCHEMA + '-grant', plan=receipt, operator_statement='H0 attendance fixture',
            attended=True, host_boot='a' * 64, opened_ns=100, deadline_ns=100 + 7200_000_000_000)
        with patch.object(lane, 'host_boot', return_value='a' * 64), patch.object(lane, 'clock', return_value=101):
            lane.validate_grant(grant, receipt, current=True)
            for changed in (dict(grant, deadline_ns=grant['deadline_ns'] + 1), dict(grant, opened_ns=True),
                            dict(grant, attended=False), dict(grant, extra='field')):
                with self.assertRaises(ValueError): lane.validate_grant(changed, receipt, current=True)
        with patch.object(lane, 'host_boot', return_value='b' * 64):
            with self.assertRaisesRegex(ValueError, 'expired'): lane.validate_grant(grant, receipt, current=True)
            lane.validate_grant(grant, receipt, current=False)

    def test_opened_grant_pin_rejects_shifted_valid_deadline(self):
        owner = self.owner()
        grant = dict(schema=lane.SCHEMA + '-grant', plan=owner.plan_receipt, operator_statement='H0 attendance fixture',
            attended=True, host_boot='a' * 64, opened_ns=100, deadline_ns=100 + 7200_000_000_000)
        receipt = records.publish(self.path / 'grant.json', grant)
        owner.journal.append('owner-opened', plan=owner.plan_receipt, grant=receipt)
        owner.grant = dict(grant, opened_ns=200, deadline_ns=200 + 7200_000_000_000)
        (self.path / 'grant.json').chmod(0o600)
        (self.path / 'grant.json').write_text(json.dumps(owner.grant))
        with patch.object(lane, 'capability'), patch.object(lane.registry, 'require_f1_owner'):
            with self.assertRaisesRegex(ValueError, 'grant changed'): lane.Owner.guard(owner)

    def test_recovery_does_not_import_candidate_only_code_but_admission_requires_it(self):
        review = dict(schema=lane.SCHEMA + '-review', verdict='PASS_GO', findings=[],
            owner_sources=[records.pin(path) for path in lane.source_paths()], capability_sources=[])
        original_import = builtins.__import__
        def missing_candidate(name, *args, **kwargs):
            if name in ('s22plus_debian_profile_v1', 's22plus_debian_artifact_v1'):
                raise ModuleNotFoundError('H0 candidate-only loss fixture')
            return original_import(name, *args, **kwargs)
        with patch.object(lane, 'read', return_value=review), patch.object(lane, 'verify', return_value=self.path / 'frozen.json'), \
             patch.object(builtins, '__import__', side_effect=missing_candidate):
            self.assertEqual(lane.capability(recovery={'H0': True}), review)
            with self.assertRaises(ModuleNotFoundError): lane.capability()
        with patch.object(lane, 'read', return_value=review):
            with self.assertRaisesRegex(ValueError, 'omits, duplicates, or changes'): lane.capability()

    def test_new_local_runtime_dependency_cannot_silently_escape_source_binding(self):
        (self.path / 'fixture.py').write_text('def runtime():\n    import dependency\n')
        (self.path / 'dependency.py').write_text('VALUE = 1\n')
        with patch.object(lane, '__file__', str(self.path / 'fixture.py')):
            with self.assertRaisesRegex(ValueError, 'new local runtime import'): lane.source_paths()

    def closing_fixture(self, owner):
        (self.path / 'prepared').mkdir()
        records.publish(self.path / 'prepared/result.json', dict(boot_id_sha256='a' * 64))
        owner.journal.append('effect-intent', step='android-restore', detail={'capture_directory': str(self.path / 'android-restore-transfer' / ('attempt-' + 'a' * 32))})
        def health(label):
            folder = self.path / label; folder.mkdir()
            value = dict(boot_id_sha256='b' * 64)
            records.publish(folder / 'result.json', value)
            return value
        owner.android_health = Mock(side_effect=health)
        owner.cleanup_network = Mock()
        owner.transfer = Mock(side_effect=AssertionError('consumed A must not repeat'))

    def test_partial_lifecycle_closes_healthy_android_without_promotion(self):
        owner = self.owner(); self.lifecycle_through_persistence(owner); self.closing_fixture(owner)
        with patch.object(lane.registry, 'target_session_lease', return_value=nullcontext()), \
             patch.object(lane.registry, 'retire_f1_owner') as retire:
            receipt = owner.close(operator_statement='')
        value = records.read(Path(receipt['path']))
        self.assertEqual(value['verdict'], 'NO_PROOF_ANDROID_CLOSED_HEALTHY')
        self.assertFalse(value['original_A_transfer_proved'])
        owner.transfer.assert_not_called(); retire.assert_called_once()

    def test_missing_research_receipt_does_not_hide_proved_android_closure(self):
        owner = self.owner(); self.intent(owner, 'android-download'); self.closing_fixture(owner)
        owner.research_proof = Mock(side_effect=FileNotFoundError('retained research file missing'))
        with patch.object(lane.registry, 'target_session_lease', return_value=nullcontext()), \
             patch.object(lane.registry, 'retire_f1_owner') as retire:
            receipt = owner.close(operator_statement='')
        value = records.read(Path(receipt['path']))
        self.assertEqual(value['verdict'], 'NO_PROOF_ANDROID_CLOSED_HEALTHY')
        self.assertEqual(value['research_evidence_error']['type'], 'FileNotFoundError')
        retire.assert_called_once()

    def test_terminal_publication_cut_resumes_without_another_device_read(self):
        owner = self.owner(); self.intent(owner, 'android-download'); self.closing_fixture(owner)
        original = lane.publish
        def publish_then_cut(path, value):
            result = original(path, value)
            if path.name == 'terminal.json': raise Cut()
            return result
        with patch.object(lane.registry, 'target_session_lease', side_effect=lambda *a, **k: nullcontext()), \
             patch.object(lane.registry, 'retire_f1_owner') as retire:
            with patch.object(lane, 'publish', side_effect=publish_then_cut):
                with self.assertRaises(Cut): owner.close(operator_statement='')
            retire.assert_not_called()
            owner.android_health = Mock(side_effect=AssertionError('terminal resumption is H0'))
            with patch.object(lane, 'capability'), patch.object(lane, 'android_projection',
                side_effect=lambda folder, plan: records.read(folder / 'result.json')):
                receipt = owner.close(operator_statement='')
            owner.android_health.assert_not_called(); owner.transfer.assert_not_called(); retire.assert_called_once()
        self.assertEqual(records.read(Path(receipt['path']))['terminal_state'], 'ANDROID_CLOSED_HEALTHY')

    def test_terminal_tampering_never_retires_or_runs_a_device_action(self):
        owner = self.owner(); self.intent(owner, 'android-download'); self.closing_fixture(owner)
        with patch.object(lane.registry, 'target_session_lease', return_value=nullcontext()), \
             patch.object(lane.registry, 'retire_f1_owner'):
            owner.close(operator_statement='')
        terminal = self.path / 'terminal.json'
        value = records.read(terminal); value['closed_boottime_ns'] += 1
        terminal.chmod(0o600)
        terminal.write_text(json.dumps(value))
        owner.android_health = Mock(side_effect=AssertionError('must remain H0'))
        with patch.object(lane.registry, 'target_session_lease', return_value=nullcontext()), \
             patch.object(lane.registry, 'retire_f1_owner') as retire, patch.object(lane, 'capability'):
            with self.assertRaisesRegex(ValueError, 'receipt differs'): owner.close(operator_statement='')
        retire.assert_not_called(); owner.android_health.assert_not_called(); owner.transfer.assert_not_called()

    def test_lost_A_raw_invalidates_previously_published_transfer_claim(self):
        owner = self.owner(); self.intent(owner, 'android-download'); self.closing_fixture(owner)
        owner.transfer_proved = Mock(return_value=True)
        with patch.object(lane.registry, 'target_session_lease', return_value=nullcontext()), \
             patch.object(lane.registry, 'retire_f1_owner'):
            owner.close(operator_statement='')
        owner.transfer_proved = Mock(return_value=False)
        owner.android_health = Mock(side_effect=AssertionError('must remain H0'))
        with patch.object(lane.registry, 'target_session_lease', return_value=nullcontext()), \
             patch.object(lane.registry, 'retire_f1_owner') as retire, patch.object(lane, 'capability'):
            with self.assertRaisesRegex(ValueError, 'claim no longer rederives'): owner.close(operator_statement='')
        retire.assert_not_called(); owner.android_health.assert_not_called(); owner.transfer.assert_not_called()


if __name__ == '__main__':
    unittest.main()

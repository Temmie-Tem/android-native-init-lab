"""Host-only producer/consumer and return-path tests; no device transport."""
import contextlib
import copy
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from tests import test_s20plus_g986n_twrp_boot_identity_d0 as fixtures
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'workspace/public/src/scripts/revalidation'
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
import s20plus_g986n_twrp_f1_engine_v2 as engine
import s20plus_g986n_twrp_f1_runtime_v2 as runtime


class TwrpEngineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixtures.S20PlusTwrpBootIdentityD0Test.setUpClass()
        cls.fixture = fixtures.S20PlusTwrpBootIdentityD0Test()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.run = Path(self.tmp.name)
        self.stack = contextlib.ExitStack()
        self.addCleanup(self.stack.close)
        for name, value in [('require_guard', None), ('require_active', None),
                            ('health_source_closure_receipts', {'fixture': True}),
                            ('validate_health_closure', {'fixture': True}),
                            ('read_twrp_predecessor', self.fixture.predecessor),
                            ('bind_twrp_inventory', None),
                            ('require_all_transfer_processes_quiescent', None)]:
            self.stack.enter_context(mock.patch.object(engine, name, return_value=value))
        self.stack.enter_context(mock.patch.object(engine, 'validate_run_dir', side_effect=lambda path: path))
        self.stack.enter_context(mock.patch.object(engine, 'candidate_claim_present', return_value=False))
        self.release = self.stack.enter_context(mock.patch.object(engine, 'release_guard'))
        self.stack.enter_context(mock.patch.object(engine, 'guard_present', return_value=True))
        self.raw_calls = []
        self.state = 'recovery'
        self.bad_identity = False
        self.raw_faults = {}
        self.boot_id = self.fixture.current_boot_id
        self.stack.enter_context(mock.patch.object(engine.raw_capture, 'acquire_command', side_effect=self.acquire))
        # Any omitted mock must fail before opening a live client.
        self.stack.enter_context(mock.patch.object(subprocess, 'Popen', side_effect=AssertionError('unexpected process')))

    def acquire(self, argv, directory, name, **kwargs):
        self.raw_calls.append(list(argv))
        f = self.fixture
        if argv[1:] == ['devices', '-l']:
            output = f.inventory_output().replace(b' recovery ', (' ' + self.state + ' ').encode())
            if self.state == 'absent':
                output = b'List of devices attached\n\n'
        elif argv[-1] == 'get-devpath':
            output = (f.devpath + '\n').encode()
        elif argv[-1] == engine.twrp_health.identity.t2.h0.RECOVERY_SHELL_ARGUMENT:
            output = f.identity_output(boot_id=self.boot_id)
            if self.bad_identity:
                output = output.replace(b'uid=0\n', b'uid=2000\n')
        elif argv[-1] == engine.twrp_health.identity.BOOT_METADATA_SCRIPT:
            output = f.metadata_output()
        else:
            self.fail('unreviewed command')
        if self.raw_faults:
            writer = engine.raw_capture.RawCaptureWriter(
                directory, name, stdout_maximum=kwargs['stdout_maximum'],
                stderr_maximum=kwargs['stderr_maximum'], argv0_name=engine.ADB.name,
                stdout_name=kwargs['stdout_name'], stderr_name=kwargs['stderr_name'])
            writer.write_stdout(output)
            return writer.finalize(returncode=0, **self.raw_faults)
        return engine.raw_capture.publish_captured_bytes(
            directory, name, stdout=output, stderr=b'', returncode=0,
            argv0_name=engine.ADB.name, stdout_name=kwargs['stdout_name'], stderr_name=kwargs['stderr_name'])

    def write(self, name, value):
        engine.durable_json(self.run / name, value)

    def starting_records(self, *, candidate=True):
        preflight = {key: self.fixture.predecessor[key] for key in
                     ('serial_sha256', 'topology_sha256', 'boot_id_sha256')}
        self.write('preflight.json', {'schema': 'fixture', 'version': engine.VERSION, **preflight})
        prepared = {'binding_sha256': 'b' * 64, 'binding': {'preflight': preflight}}
        if candidate:
            self.write('candidate-intent.json', {'fixture': 'consumed'})
            self.write('rollback-intent.json', {'fixture': 'consumed'})
            self.write('candidate-observation.json', {'claim_verdict': 'NO_PROOF'})
        return prepared

    def test_health_uses_fixed_collector_and_replays_private_capture(self):
        health, serial = engine.resident_health_once(self.run, 'preflight-root')
        self.assertEqual(serial, self.fixture.serial)
        self.assertEqual(len(self.raw_calls), 7)
        self.assertEqual(health['health_kind'], 'retained_t2_recovery')
        self.assertIs(health['android_health_verified'], False)
        self.assertIs(health['boot_content_verified'], False)
        self.assertNotIn('public_health', health)
        self.assertEqual(engine._validate_resident_health_receipt(self.run, health, 'fixture', 'preflight-root'), health)
        self.assertEqual(len(self.raw_calls), 7)

    def test_prepare_binds_twrp_before_one_download_request(self):
        effects = []
        def download(directory, serial, name):
            self.assertEqual(serial, self.fixture.serial)
            self.assertTrue((directory / 'initial-download-intent.json').exists())
            preflight = engine.read_json(directory / 'preflight.json', 'fixture')
            self.assertEqual(preflight['health_kind'], 'retained_t2_recovery')
            effects.append('download')
            return {'outcome': 'dispatched'}
        with mock.patch.object(engine, 'validate_host_closure', return_value={}), \
                mock.patch.object(engine, 'twrp_source_receipts', return_value={}), \
                mock.patch.object(engine.twrp_health.identity, 'validate_t2_predecessor', return_value=self.fixture.predecessor), \
                mock.patch.object(engine, 'allocate_run_dir', return_value=self.run), \
                mock.patch.object(engine, 'acquire_guard'), \
                mock.patch.object(engine, 'download_baseline', return_value={'empty': True}), \
                mock.patch.object(engine, 'adb_reboot_download_capture', side_effect=download), \
                mock.patch.object(engine, 'wait_download', return_value={'endpoint': {'fixture': True}}):
            self.assertEqual(engine.prepare(None), self.run)
        prepared = engine.read_json(self.run / 'prepared.json', 'fixture')
        self.assertEqual(prepared['binding']['preflight']['health_kind'], 'retained_t2_recovery')
        self.assertEqual(effects, ['download'])
        self.assertEqual(len(self.raw_calls), 7)
        self.release.assert_not_called()

    def test_real_prepared_history_and_namespace_survive_abort_and_closed_readback(self):
        baseline = {'schema': 's20plus_g986n_twrp_v2_download_baseline_v1', 'endpoint_count': 0,
                    'listing_sha256': 'd' * 64, 'at': 'fixture'}
        endpoint = {'device': '/dev/bus/usb/001/007', 'endpoint_identity': [1, 2, 3, 4],
                    'endpoint_sha256': hashlib.sha256(b'/dev/bus/usb/001/007').hexdigest(),
                    'topology_sha256': next(iter(engine.EXPECTED_DOWNLOAD_TOPOLOGY_SHA256)),
                    'usb': {**engine.DOWNLOAD_USB, 'serial_absent': True}}
        closure = {'runner': {'normalized_sha256': engine.EXPECTED_REVIEWED_NORMALIZED_SHA256},
                   'candidate': {'ap': {'sha256': engine.CANDIDATE_AP_SHA256}},
                   'rollback': {'ap': {'sha256': engine.ROLLBACK_AP_SHA256}},
                   'manifest': {'sha256': engine.MANIFEST_SHA256},
                   'builder': {'sha256': engine.BUILDER_SHA256}}
        def download(directory, serial, name):
            self.assertTrue((directory / 'initial-download-intent.json').exists())
            writer = engine.raw_capture.RawCaptureWriter(
                directory, name, stdout_maximum=16384, stderr_maximum=16384,
                argv0_name=engine.ADB.name, stdout_name=name + '.stdout', stderr_name=name + '.stderr')
            handle = writer.finalize(returncode=0)
            return {'outcome': 'dispatched', 'returncode': 0,
                    'stdout_sha256': hashlib.sha256(b'').hexdigest(),
                    'stderr_sha256': hashlib.sha256(b'').hexdigest(),
                    'capture_receipt': {'path': str(handle.receipt_path),
                                        'size': handle.receipt_path.stat().st_size,
                                        'sha256': hashlib.sha256(handle.receipt_path.read_bytes()).hexdigest()}}
        with mock.patch.object(engine, 'validate_host_closure', return_value=closure), \
                mock.patch.object(engine, 'twrp_source_receipts', return_value={}), \
                mock.patch.object(engine.twrp_health.identity, 'validate_t2_predecessor', return_value=self.fixture.predecessor), \
                mock.patch.object(engine, 'allocate_run_dir', return_value=self.run), \
                mock.patch.object(engine, 'acquire_guard'), \
                mock.patch.object(engine, 'download_baseline', return_value=baseline), \
                mock.patch.object(engine, 'adb_reboot_download_capture', side_effect=download), \
                mock.patch.object(engine, 'wait_download', return_value={
                    'baseline_sha256': engine.digest(baseline), 'endpoint': endpoint,
                    'arrival_listing_sha256': 'e' * 64}):
            engine.prepare(None)
        prepared = engine.read_prepared(self.run, phase='health')
        engine.validate_prepared_history(self.run, prepared['binding'])
        engine.validate_namespace(self.run)
        self.assertEqual(engine.abort_pre_candidate(self.run)['verdict'], 'ATTENDED_TWRP_ENTRY_PENDING')
        engine.validate_namespace(self.run)
        self.boot_id = '22345678-1234-4123-8123-123456789abc'
        self.assertEqual(engine.abort_pre_candidate(self.run)['verdict'], 'ABORTED_PRE_CANDIDATE_TWRP_HEALTHY')
        # Closed-run validation is read-only and must not require the released guard.
        with mock.patch.object(engine, 'require_guard', side_effect=AssertionError('closed guard required')):
            engine.validate_namespace(self.run)

    def test_actual_odin_producer_and_receipt_validator_agree_for_both_roles(self):
        @contextlib.contextmanager
        def pin(path, *, expected_size, expected_sha256, **_kwargs):
            yield SimpleNamespace(path=path, receipt=lambda: {
                'path': str(path), 'size': expected_size, 'sha256': expected_sha256})
        calls = []
        output = engine.ODIN_CAGE_ENTRY_MARKER + b'Setup Connection Upload Binaries boot.img.lz4 100% Close Connection'
        def capture(argv, directory, name, **kwargs):
            calls.append(argv)
            return engine.raw_capture.publish_captured_bytes(
                directory, name, stdout=output, stderr=b'', returncode=0,
                argv0_name=engine.DASH.name, stdout_name=kwargs['stdout_name'], stderr_name=kwargs['stderr_name'])
        cage = self.run / 'fixture-cage'
        cage.mkdir()
        endpoint = {'device': '/dev/bus/usb/001/007', 'endpoint_identity': [1, 2, 3, 4]}
        with mock.patch.object(engine.transport, 'pin_regular_file', side_effect=pin), \
                mock.patch.object(engine.transport, 'pin_boot_only_ap', side_effect=pin), \
                mock.patch.object(engine.transport, 'revalidate_pinned_path'), \
                mock.patch.object(engine, 'endpoint_stat', return_value=(1, 2, 3, 4)), \
                mock.patch.object(engine, '_cgroup_identity', return_value=[7, 8]), \
                mock.patch.object(engine, '_cgroup_populated', return_value=False), \
                mock.patch.object(engine, 'quiesce_process_cage', return_value={'empty': True}), \
                mock.patch.object(engine.raw_capture, 'acquire_command', side_effect=capture):
            for kind in ('candidate', 'rollback'):
                self.write(kind + '-intent.json', {'endpoint': endpoint, 'process_cage': {
                    'cage': str(cage), 'cage_identity': [7, 8], 'binding_sha256': 'b' * 64}})
                prefix = kind.upper()
                receipt, handle = engine.execute_odin_exact(
                    self.run, kind, getattr(engine, prefix + '_AP'), getattr(engine, prefix + '_AP_SIZE'),
                    getattr(engine, prefix + '_AP_SHA256'), endpoint, 'b' * 64)
                result = {'schema': 's20plus_g986n_twrp_v2_transfer_result_v1', 'version': engine.VERSION,
                          'kind': kind, 'binding_sha256': 'b' * 64, 'classification': 'odin_transfer_completed',
                          'receipt': receipt, 'stdout_sha256': hashlib.sha256(output).hexdigest(),
                          'stderr_sha256': hashlib.sha256(b'').hexdigest(),
                          'host_process_quiescence_proved': True, 'replay_permitted': False, 'at': 'fixture'}
                engine._validate_transfer_outcome(self.run, result, kind, 'b' * 64)
                self.assertEqual('--reboot' in calls[-1], kind == 'candidate')
                bad = copy.deepcopy(result)
                bad['receipt']['command_shape'] = engine.odin_boot_command(
                    'rollback' if kind == 'candidate' else 'candidate', 'odin4', 'AP.tar.md5', 'USBFS')
                with self.assertRaises(engine.B0F1Error):
                    engine._validate_transfer_outcome(self.run, bad, kind, 'b' * 64)
    def test_health_stage_and_derived_claim_tampering_are_rejected(self):
        health, _ = engine.resident_health_once(self.run, 'preflight-root')
        with self.assertRaises(engine.B0F1Error):
            engine._validate_resident_health_receipt(self.run, health, 'fixture', 'final-root')
        bad = copy.deepcopy(health)
        bad['boot_content_verified'] = True
        with self.assertRaises(engine.B0F1Error):
            engine._validate_resident_health_receipt(self.run, bad, 'fixture', 'preflight-root')

    def test_expected_readiness_can_be_observed_again_without_reboot(self):
        self.state = 'absent'
        with self.assertRaises(engine.TwrpNotReady):
            engine.resident_health_once(self.run, 'final-root')
        self.assertFalse((self.run / 'twrp-health-failure.json').exists())
        self.state = 'recovery'
        engine.resident_health_once(self.run, 'final-root')
        self.assertEqual(len(self.raw_calls), 8)
        self.assertFalse(any('reboot' in argv for argv in self.raw_calls))

    def test_unexpected_identity_preserves_raw_and_stops_retry(self):
        self.bad_identity = True
        with self.assertRaises(engine.B0F1Error):
            engine.resident_health_once(self.run, 'final-root')
        self.assertTrue((self.run / 'twrp-health-failure.json').exists())
        self.assertTrue(list(self.run.glob('*.stdout')))
        count = len(self.raw_calls)
        self.bad_identity = False
        with self.assertRaisesRegex(engine.B0F1Error, 'prior TWRP health failure'):
            engine.resident_health_once(self.run, 'final-root')
        self.assertEqual(len(self.raw_calls), count)

    def test_rc_zero_with_raw_acquisition_failure_never_qualifies_health(self):
        for index, faults in enumerate(({'timed_out': True}, {'output_exceeded': True},
                                        {'producer_error_type': 'OSError'})):
            with self.subTest(faults=faults):
                directory = self.run / str(index)
                directory.mkdir()
                self.raw_faults = faults
                with self.assertRaises(engine.B0F1Error):
                    engine.resident_health_once(directory, 'final-root')
                self.assertTrue((directory / 'twrp-health-failure.json').exists())
                self.assertTrue(list(directory.glob('*.stdout')))
                self.assertFalse(list(directory.glob('twrp-final-root-????.json')))

    def test_readback_rejects_fault_flags_even_when_transcript_matches(self):
        health, _ = engine.resident_health_once(self.run, 'preflight-root')
        path = next(self.run.glob('*-step-0.capture.json'))
        record = json.loads(path.read_bytes())
        record['timed_out'] = True
        path.chmod(0o600)
        path.write_bytes(engine.canonical_bytes(record))
        path.chmod(0o400)
        with self.assertRaisesRegex(engine.B0F1Error, 'raw acquisition failed'):
            engine._validate_resident_health_receipt(self.run, health, 'fixture', 'preflight-root')

    def test_rollback_requests_physical_entry_then_closes_only_with_proved_transfer(self):
        prepared = self.starting_records()
        first = engine.final_health_and_terminal(self.run, prepared)
        self.assertEqual(first['verdict'], 'ATTENDED_TWRP_ENTRY_PENDING')
        self.assertEqual(self.raw_calls, [])
        original_intent = (self.run / 'twrp-return-intent.json').read_bytes()
        self.write('rollback-result.json', {'classification': 'odin_transfer_completed'})
        self.write('candidate-result.json', {'classification': 'odin_transfer_completed'})
        with mock.patch.object(engine, '_validate_transfer_outcome'):
            result = engine.final_health_and_terminal(self.run, prepared)
        self.assertFalse(result['experiment_pass'])
        self.assertTrue(result['rollback_transfer_completed'])
        self.assertEqual((self.run / 'twrp-return-intent.json').read_bytes(), original_intent)
        self.release.assert_called_once_with(self.run)

    def test_twrp_health_does_not_close_unknown_boot_rollback(self):
        prepared = self.starting_records()
        engine.final_health_and_terminal(self.run, prepared)
        result = engine.final_health_and_terminal(self.run, prepared)
        self.assertEqual(result['verdict'], 'ROLLBACK_OUTCOME_UNPROVED_TWRP_HEALTHY')
        self.assertFalse((self.run / 'terminal.json').exists())
        self.assertFalse((self.run / 'final-health.json').exists())
        self.assertTrue((self.run / 'twrp-return-arrival.json').exists())
        self.release.assert_not_called()
        calls = len(self.raw_calls)
        engine.final_health_and_terminal(self.run, prepared)
        self.assertEqual(len(self.raw_calls), calls)

    def test_arrival_survives_reporting_cut_without_another_observation(self):
        prepared = self.starting_records()
        engine.final_health_and_terminal(self.run, prepared)
        self.write('rollback-result.json', {'classification': 'odin_transfer_completed'})
        self.write('candidate-result.json', {'classification': 'odin_transfer_completed'})
        original_write = engine.durable_json
        def cut(path, value):
            if path.name == 'final-health.json':
                raise KeyboardInterrupt()
            original_write(path, value)
        with mock.patch.object(engine, '_validate_transfer_outcome'), mock.patch.object(engine, 'durable_json', side_effect=cut):
            with self.assertRaises(KeyboardInterrupt):
                engine.final_health_and_terminal(self.run, prepared)
        count = len(self.raw_calls)
        with mock.patch.object(engine, '_validate_transfer_outcome'):
            result = engine.final_health_and_terminal(self.run, prepared)
        self.assertTrue(result['rollback_transfer_completed'])
        self.assertEqual(len(self.raw_calls), count)

    def test_pre_candidate_abort_returns_to_twrp_without_odin(self):
        self.starting_records(candidate=False)
        first = engine.abort_pre_candidate(self.run)
        self.assertEqual(first['verdict'], 'ATTENDED_TWRP_ENTRY_PENDING')
        result = engine.abort_pre_candidate(self.run)
        self.assertEqual(result['verdict'], 'ABORTED_PRE_CANDIDATE_TWRP_HEALTHY')
        self.assertEqual(result['candidate_attempts'], 0)
        self.assertEqual(result['rollback_attempts'], 0)
        self.assertFalse(any('odin' in argv[0] or 'reboot' in argv for argv in self.raw_calls))
        self.release.assert_called_once_with(self.run)

    def test_return_intent_cannot_switch_from_abort_to_rollback(self):
        prepared = self.starting_records(candidate=False)
        engine.arm_twrp_return(self.run, 'pre-candidate-abort')
        self.write('rollback-intent.json', {'fixture': True})
        with self.assertRaises(engine.B0F1Error):
            engine.arm_twrp_return(self.run, 'rollback', prepared)

    def test_return_rejects_the_starting_boot(self):
        prepared = self.starting_records()
        engine.arm_twrp_return(self.run, 'rollback', prepared)
        health, _ = engine.resident_health_once(self.run, 'final-root')
        # Replace only the fixture starting boot before deriving a fresh intent.
        with mock.patch.object(engine, 'require_twrp_return', return_value={
                'source_identity': {'boot_id_sha256': health['boot_id_sha256']}}):
            with self.assertRaisesRegex(engine.B0F1Error, 'starting boot'):
                engine.record_twrp_arrival(self.run, health, 'rollback', prepared)

    def test_legacy_system_return_is_unreachable(self):
        with self.assertRaises(engine.B0F1Error):
            engine.payload_free_return(self.run, {})
        with self.assertRaises(engine.B0F1Error):
            engine.validate_twrp_records(self.run, {'abort-return-intent.json'})


class TwrpRuntimeTests(unittest.TestCase):
    def test_transport_is_the_isolated_reviewed_s20_copy(self):
        expected = 'f18e2e453e33078a184653722d4579a184c59b1c3ac10f9eb54d4a4ba437ffea'
        self.assertEqual(hashlib.sha256(runtime.TRANSPORT_PATH.read_bytes()).hexdigest(), expected)
        self.assertEqual(runtime.TRANSPORT_PATH.name, 's20plus_g986n_boot_only_f1_transport_v1.py')
        self.assertIs(runtime.engine.transport, runtime._isolated_transport)
        self.assertIs(runtime.engine.transport.raw_capture, runtime.engine.raw_capture)
        self.assertIs(runtime.engine.transport.boot_verify, runtime._isolated_boot_verify)
        receipt = runtime.engine._source_receipts(('transport',))['transport']
        self.assertEqual(receipt['path'], str(runtime.TRANSPORT_PATH))
        self.assertEqual(receipt['sha256'], expected)
        with self.assertRaises(runtime.P0F1Error):
            runtime.engine.transport.execute_odin_boot_only()

    def test_s22_registry_owner_mutators_remain_denied_inside_s20_lease(self):
        def action(run):
            with mock.patch.object(Path, 'mkdir', side_effect=AssertionError('foreign owner mkdir')), \
                    mock.patch.object(Path, 'unlink', side_effect=AssertionError('foreign owner unlink')), \
                    mock.patch.object(runtime.registry, 'target_session_lease', side_effect=AssertionError('S22 research lease')):
                for name in ('begin_f1_owner', 'retire_f1_owner'):
                    with self.assertRaises(runtime.P0F1Error):
                        getattr(runtime.registry, name)(run.parent, run, 'b' * 64)
        self.leased_probe(action)

    def test_new_registry_denials_are_part_of_installation_integrity(self):
        runtime._assert_profile_installed()
        with mock.patch.object(runtime.registry, 'begin_f1_owner', lambda *args: None):
            with self.assertRaisesRegex(runtime.P0F1Error, 'dependency fence'):
                runtime._assert_profile_installed()

    def leased_probe(self, action):
        """Enter the real private lease, stopping at an injected guard observer."""
        with tempfile.TemporaryDirectory() as temporary, contextlib.ExitStack() as stack:
            root = Path(temporary)
            run = root / 'run-fixture'
            run.mkdir()
            lock = root / 'session.lock'
            lock.write_bytes(runtime.registry.SESSION_LOCK_PAYLOAD)
            lock.chmod(0o600)
            for name, value in [('RUN_ROOT', root), ('TWRP_RUNTIME_CONFIGURED', True), ('P0_F1_ACTIVE', True)]:
                stack.enter_context(mock.patch.object(runtime, name, value))
            stack.enter_context(mock.patch.object(runtime.observer, 'OBSERVER_ACTIVE', True))
            for name in ('self_receipt', '_assert_profile_installed', '_validate_live_activation'):
                stack.enter_context(mock.patch.object(runtime, name, return_value={}))
            stack.enter_context(mock.patch.object(runtime, '_session_lock_path', return_value=lock))
            def guard(directory):
                self.assertEqual(directory, run)
                action(run)
                raise runtime.P0F1Error('host-fixture-complete')
            stack.enter_context(mock.patch.object(runtime.engine, 'require_guard', side_effect=guard))
            with self.assertRaisesRegex(runtime.P0F1Error, 'host-fixture-complete'):
                runtime._read_prepared_for_output(run)

    def test_real_lease_raw_inventory_and_selected_reads_share_fixed_environment(self):
        original_popen = subprocess.Popen
        calls = []
        serial = 'SYNTHETIC-TWRP-LEASE'
        inventory = ('List of devices attached\n' + serial +
                     ' recovery usb:1-2 product:twrp_y2q model:SAMSUNG_y2q device:y2q transport_id:1\n').encode()
        def popen(argv, **kwargs):
            calls.append((list(argv), dict(kwargs['env'])))
            output = inventory if argv[1:] == ['devices', '-l'] else b'usb:1-2\n'
            kwargs.pop('executable', None)
            # The validated ADB argv is recorded, but only a host Python producer
            # runs. The real raw-capture pipes, bounds and durable writer execute.
            return original_popen([sys.executable, '-c', 'import os; os.write(1, ' + repr(output) + ')'], **kwargs)
        def action(run):
            name = 'twrp-final-root-0001-step-0'
            handle = runtime.engine.raw_capture.acquire_command(
                [str(runtime.engine.ADB), 'devices', '-l'], run, name,
                timeout=10, stdout_maximum=16384, stderr_maximum=16384,
                stdout_name=name + '.stdout', stderr_name=name + '.stderr')
            rows = runtime.twrp_health.identity.inventory_from_result(
                (handle.returncode, runtime.engine.raw_capture.read_stdout(handle, maximum=16384), b''), 'fixture')
            runtime.engine.bind_twrp_inventory(rows)
            name = 'twrp-final-root-0001-step-1'
            kwargs = dict(timeout=10, stdout_maximum=16384, stderr_maximum=16384,
                          stdout_name=name + '.stdout', stderr_name=name + '.stderr')
            runtime.engine.raw_capture.acquire_command([str(runtime.engine.ADB), '-s', serial, 'get-devpath'], run, name, **kwargs)
            with self.assertRaises(runtime.P0F1Error):
                runtime.engine.raw_capture.acquire_command([str(runtime.engine.ADB), '-s', 'FOREIGN', 'get-devpath'], run, name, **kwargs)
            with mock.patch.object(runtime.engine, 'twrp_read_command_allowed', return_value=True):
                with self.assertRaises(runtime.P0F1Error):
                    runtime.engine.raw_capture.acquire_command([str(runtime.engine.ADB), '-s', serial, 'shell', 'id'], run, name, **kwargs)
        with mock.patch.object(subprocess, 'Popen', side_effect=popen), mock.patch.dict(os.environ, {
                'ADB_SERVER_SOCKET': 'tcp:invalid.invalid:1', 'LD_PRELOAD': '/not-a-library'}), \
                mock.patch.object(runtime.engine, 'read_twrp_predecessor', return_value={
                    'serial_sha256': hashlib.sha256(serial.encode()).hexdigest()}):
            self.leased_probe(action)
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0][1], calls[1][1])
        self.assertEqual(calls[0][1]['ADB_SERVER_SOCKET'], runtime.P0_ADB_SERVER_SOCKET)
        self.assertNotIn('LD_PRELOAD', calls[0][1])

    def test_recovery_lease_binds_retained_serial_and_rejects_switches(self):
        serial = 'SYNTHETIC-TWRP-LEASE'
        serial_sha = hashlib.sha256(serial.encode()).hexdigest()
        recovery = {'serial': serial, 'state': 'recovery',
                    'metadata': {'model:SAMSUNG_y2q', 'product:twrp_y2q', 'device:y2q'}}
        android = {'serial': serial, 'state': 'device',
                   'metadata': set(runtime.engine.EXPECTED_ADB_METADATA)}
        foreign = {**recovery, 'serial': 'SYNTHETIC-OTHER'}
        def action(run):
            with mock.patch.object(runtime.engine, 'read_twrp_predecessor', return_value={'serial_sha256': serial_sha}):
                runtime.engine.bind_twrp_inventory((recovery,))
                for rows in ((foreign,), (recovery, recovery), ({**recovery, 'state': 'offline'},),
                             (android,), (recovery, {**android, 'serial': foreign['serial']})):
                    with self.assertRaises(runtime.P0F1Error):
                        runtime.engine.bind_twrp_inventory(rows)
                runtime.engine.bind_android_inventory((android,))
                with self.assertRaises(runtime.P0F1Error):
                    runtime.engine.bind_android_inventory(({**android, 'serial': foreign['serial']},))
            with mock.patch.object(runtime.engine, 'read_twrp_predecessor', return_value={
                    'serial_sha256': hashlib.sha256(foreign['serial'].encode()).hexdigest()}):
                with self.assertRaisesRegex(runtime.P0F1Error, 'serial changed'):
                    runtime.engine.bind_twrp_inventory((foreign,))
        with mock.patch.object(subprocess, 'Popen', side_effect=AssertionError('device process')):
            self.leased_probe(action)

    def test_real_lease_accepts_no_reboot_rollback_and_rejects_old_shape(self):
        original_popen = subprocess.Popen
        calls = []
        output = runtime.engine.ODIN_CAGE_ENTRY_MARKER + b'Setup Connection Upload Binaries boot.img.lz4 100% Close Connection'
        def popen(argv, **kwargs):
            calls.append(list(argv))
            kwargs.pop('executable', None)
            return original_popen([sys.executable, '-c', 'import os; os.write(1, ' + repr(output) + ')'], **kwargs)
        def action(run):
            cage = str(run / 'fixture-cage')
            endpoint = '/dev/bus/usb/001/007'
            runtime.engine.durable_json(run / 'rollback-intent.json', {
                'process_cage': {'cage': cage}, 'endpoint': {'device': endpoint}})
            argv = [str(runtime.engine.DASH), '-c', runtime.engine.ODIN_CAGE_ENTRY_SCRIPT,
                    's20plus-b0-odin-cage', cage, str(runtime.engine.ODIN),
                    '-a', str(runtime.ROLLBACK_AP), '-d', endpoint]
            kwargs = dict(timeout=300, stdout_maximum=runtime.engine.MAX_RAW_BYTES,
                          stderr_maximum=runtime.engine.MAX_RAW_BYTES, env=runtime.engine.ODIN_FIXED_ENV,
                          stdout_name='rollback.stdout', stderr_name='rollback.stderr', start_new_session=True)
            runtime.engine.raw_capture.acquire_command(argv, run, 'rollback-transfer', **kwargs)
            bad = argv[:6] + ['--reboot'] + argv[6:]
            with self.assertRaises(runtime.P0F1Error):
                runtime.engine.raw_capture.acquire_command(bad, run, 'rollback-transfer', **kwargs)
            with self.assertRaises(runtime.P0F1Error):
                runtime.engine.raw_capture.acquire_command(argv, run, 'abort-return', **kwargs)
        with mock.patch.object(subprocess, 'Popen', side_effect=popen):
            self.leased_probe(action)
        self.assertEqual(len(calls), 1)
        self.assertNotIn('--reboot', calls[0])

    def test_plan_is_unconfigured_and_role_bound(self):
        plan = runtime.render_plan()
        self.assertFalse(plan['live_authority'])
        self.assertFalse(plan['candidate_configured'])
        self.assertIn('--reboot', plan['candidate_odin_shape'])
        self.assertNotIn('--reboot', plan['rollback_odin_shape'])
        with self.assertRaises(engine.B0F1Error):
            engine.odin_boot_command('arbitrary', 'odin4', 'AP.tar.md5', 'USBFS')

    def test_unconfigured_entrypoints_do_not_contact_a_device(self):
        with mock.patch.object(subprocess, 'Popen', side_effect=AssertionError('device command')):
            with contextlib.redirect_stdout(io.StringIO()):
                for option in ('--prepare', '--execute', '--resume', '--finalize-twrp', '--abort-pre-candidate'):
                    self.assertEqual(runtime.main([option]), 3)
            with self.assertRaises(runtime.P0F1Error):
                runtime.engine.prepare(None)

    def test_new_effect_helpers_still_require_a_real_session_lease(self):
        with mock.patch.object(runtime, 'require_active'), mock.patch.object(subprocess, 'Popen', side_effect=AssertionError('device command')):
            for call in (lambda: runtime.engine.arm_twrp_return(Path('/tmp/fixture'), 'pre-candidate-abort'),
                         lambda: runtime.engine.bind_twrp_inventory(()),
                         lambda: runtime.engine.raw_capture.acquire_command([str(runtime.engine.ADB), 'devices', '-l'], Path('/tmp/fixture'), 'twrp-final-root-0001-step-0')):
                with self.assertRaises(runtime.P0F1Error):
                    call()

    def test_fixed_read_surface_rejects_arbitrary_script_and_bounds(self):
        name = 'twrp-final-root-0001-step-0'
        kwargs = dict(timeout=10, stdout_maximum=16384, stderr_maximum=16384,
                      stdout_name=name + '.stdout', stderr_name=name + '.stderr')
        self.assertTrue(runtime.engine.twrp_read_command_allowed([str(runtime.engine.ADB), 'devices', '-l'], name, kwargs))
        self.assertFalse(runtime.engine.twrp_read_command_allowed([str(runtime.engine.ADB), '-s', 'fixture', 'shell', 'su', '-c', 'id'], name, kwargs))
        self.assertFalse(runtime.engine.twrp_read_command_allowed([str(runtime.engine.ADB), 'devices', '-l'], name, {**kwargs, 'timeout': 100}))


if __name__ == '__main__':
    unittest.main()

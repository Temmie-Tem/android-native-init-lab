"""P2 real owner/lease/raw collector tests with host-only hardware fixtures.

Only activation, qualified physical receipts and transport producers are modeled.
Actual shared engine dispatch, flock, command fence, raw capture/replay, evidence
validation and durable records run. Popen is intercepted before any ADB process.
"""
import contextlib
import dataclasses
import hashlib
import json
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from tests import test_s20plus_g986n_p2_ram_snapshot as producer_fixture
from tests.test_s20plus_g986n_p2_ram_snapshot import BOOT, BOOT_SHA, SCRIPTS
import s20plus_g986n_p2_ram_snapshot_f1 as P

R, E, O, C = P._runtime, P.engine, P.observation, P.codec
SERIAL = 'S20_P2_FIXTURE_ONLY'
SERIAL_SHA = C.sha256(SERIAL.encode())
TOPOLOGY = 'usb:1-2'
TOPOLOGY_SHA = C.sha256(TOPOLOGY.encode())
INITIAL_SHA = C.sha256(b'previous synthetic boot')


class P2IntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Once, obtain the real C producer/reader stream via the H0 syscall seam.
        producer_fixture.SnapshotProducerTests.setUpClass()
        try:
            _, cls.stream, result = producer_fixture.SnapshotProducerTests().run_case()
            assert result['structural_verdict'] == 'MATCH'
        finally:
            producer_fixture.SnapshotProducerTests.tearDownClass()
        cls.closure = P.validate_host_closure()

    def test_profile_installs_real_engine_and_remains_dormant(self):
        R._assert_profile_installed()
        for name in ('observe_candidate', 'validate_namespace',
                     'transfer_boot', 'prepare_process_cage', 'revalidate_rollback_source'):
            self.assertIs(getattr(E, name), R._profile_function_replacements()[name])
        self.assertEqual(self.closure['candidate']['ap']['sha256'], P.OUTPUTS['AP.tar.md5']['sha256'])
        self.assertEqual(E.CANDIDATE_AP, P.OUTPUT_ROOT / 'AP.tar.md5')
        with mock.patch('subprocess.Popen', side_effect=AssertionError('live process')), \
                mock.patch.object(P, 'P2_F1_ACTIVE', False):
            for option in ('--prepare', '--execute', '--resume', '--arm-physical-rollback', '--finalize-resident'):
                with self.subTest(option=option), self.assertRaisesRegex(P.P2F1Error, 'NOT_ACTIVE'):
                    P.main([option, '--run-dir', '/fixture/run'])
            with mock.patch.object(P, 'P2_F1_ACTIVE', True), \
                    mock.patch.object(P, 'ACTIVATION', Path('/absent/p2-activation.json')), \
                    self.assertRaisesRegex(R.P0F1Error, 'activation.*absent'):
                P.require_active()

    def test_recovery_validation_omits_candidate_artifacts(self):
        with mock.patch.object(E, 'CANDIDATE_AP', Path('/missing/p2')), \
             mock.patch.object(E, 'BUILDER', Path('/missing/builder')), \
             mock.patch.object(R, '_assert_profile_installed'):
            self.assertIn('rollback', P.validate_rollback_closure())
            self.assertIn('sources', P.validate_health_closure())
        self.assertEqual(O.root_script(E, rollback=True), E.ROOT_READ_SCRIPT)
        self.assertNotIn('reader_', O.root_script(E, rollback=True))

    @contextlib.contextmanager
    def scenario(self, *, fault=None, early_attempt=None, finish=None):
        with tempfile.TemporaryDirectory() as tmp, contextlib.ExitStack() as stack:
            root = Path(tmp); run = root / 'run'; run.mkdir(mode=0o700)
            lock = root / 'target-session.lock'; lock.write_bytes(R.registry.SESSION_LOCK_PAYLOAD); lock.chmod(0o600)
            preflight = {'target': E.TARGET, 'serial_sha256': SERIAL_SHA,
                         'topology_sha256': TOPOLOGY_SHA, 'boot_id_sha256': INITIAL_SHA}
            endpoint = {'fixture': 'download'}
            binding = E.prepared_binding(run, preflight, endpoint, self.closure)
            prepared = {'schema': 's20plus_g986n_twrp_v2_prepared_v1', 'version': P.VERSION,
                        'binding': binding, 'binding_sha256': E.digest(binding),
                        'approval_token': R.APPROVAL_PREFIX + E.digest(binding), 'at': 'fixture'}
            (run / 'prepared.json').write_bytes(E.canonical_bytes(prepared)); (run / 'prepared.json').chmod(0o400)
            calls = []; real_popen = subprocess.Popen; actual_publish = E.durable_json
            public_count = 0

            def output_for(argv):
                nonlocal public_count
                if argv == [str(E.ADB), 'devices', '-l']:
                    if early_attempt == 'absent' and not calls:
                        return b'List of devices attached\n', 0
                    return ('List of devices attached\n' + SERIAL + '\tdevice ' +
                            ' '.join(sorted(E.EXPECTED_ADB_METADATA)) + '\n').encode(), 0
                if argv == [str(E.ADB), '-s', SERIAL, 'get-devpath']:
                    return (TOPOLOGY + '\n').encode(), 0
                if argv[-1] == E.PUBLIC_SNAPSHOT_SCRIPT:
                    public_count += 1
                    values = {'model': E.TARGET['model'], 'device': E.TARGET['device'],
                              'product_name': E.TARGET['product'], 'incremental': E.TARGET['incremental'],
                              'selinux': 'Enforcing', 'boot_id': BOOT,
                              'boot_completed': '0' if public_count == 1 else '1',
                              'bootanim': 'running' if public_count == 1 else 'stopped'}
                    if fault == 'changed-boot' and public_count > 1:
                        values['boot_id'] = '99999999-2222-4333-8444-555555555555'
                    return ''.join(k + '=' + values[k] + '\n' for k in E.PUBLIC_SNAPSHOT_KEYS).encode(), 0
                for rollback in (False, True):
                    if argv[-1] == shlex.quote(O.root_script(E, rollback=rollback)):
                        values = dict(E.EXPECTED_ROOT_OUTPUT, boot_id=BOOT)
                        keys = list(E.ROOT_OUTPUT_KEYS)
                        if not rollback:
                            values.update(reader_location='/debug_ramdisk', reader_state='present',
                                          reader_sha256=P.OUTPUTS[C.READER_NAME]['sha256'], reader_fs='1021994',
                                          reader_size=str(P.OUTPUTS[C.READER_NAME]['size']))
                            keys += ['reader_location', 'reader_state', 'reader_sha256', 'reader_fs', 'reader_size']
                            if early_attempt == 'reader-absent' and public_count == 1:
                                values.update(reader_state='absent', reader_sha256='unavailable',
                                              reader_fs='unavailable', reader_size='unavailable')
                        if fault == 'root':
                            return b'root unavailable\n', 1
                        return ''.join(k + '=' + values[k] + '\n' for k in keys).encode(), 0
                if argv[-1] == shlex.quote('exec /debug_ramdisk/' + C.READER_NAME):
                    return (self.stream[:-1] if fault == 'truncated' else self.stream), (1 if fault == 'reader-rc' else 0)
                self.fail('unreviewed command reached fixture: ' + repr(argv))

            def popen(argv, *args, **kwargs):
                self.assertEqual(R._require_live_transaction()['run_dir'], str(run))
                output, rc = output_for(argv)
                calls.append(('read', argv))
                script = f'import os;os.write(1,{output!r});raise SystemExit({rc})'
                return real_popen([sys.executable, '-c', script], *args, **kwargs)

            def consume(directory, digest):
                self.assertEqual(R._require_live_transaction()['run_dir'], str(directory))
                calls.append(('consume', None))

            def transfer(directory, kind, endpoint, digest):
                self.assertEqual(kind, 'candidate'); calls.append(('transfer', kind))
                actual_publish(directory / 'candidate-intent.json', {'fixture': True})
                actual_publish(directory / 'candidate-result.json', {'classification': 'odin_transfer_completed'})

            def validate_transfer(directory, result, kind, digest):
                self.assertTrue((directory / (kind + '-intent.json')).exists())
                self.assertEqual(digest, prepared['binding_sha256'])

            def rollback_entry(directory, stored, observation, serial):
                self.assertEqual(serial, SERIAL)
                receipt = E.revalidate_rollback_source(directory, stored, observation, serial)
                self.assertEqual(receipt['boot_id_sha256'], BOOT_SHA)
                calls.append(('rollback-entry', None))
                return {'endpoint': endpoint}

            def durable(path, value):
                if fault == 'publish' and path.name == P.EVIDENCE_NAME:
                    raise OSError('fixture publication cut')
                actual_publish(path, value)

            def rollback_and_wait(directory, stored, endpoint):
                actual_publish(directory / 'rollback-intent.json', {'fixture': True})
                actual_publish(directory / 'rollback-result.json', {'classification':
                    'odin_transfer_completed' if finish == 'proved' else 'odin_device_session_failure_or_unknown'})
                return E.final_health_and_terminal(directory, stored)

            patches = [mock.patch.object(P, 'P2_F1_ACTIVE', True),
                mock.patch.object(P, '_require_reviewed_activation'),
                mock.patch.object(R, '_assert_profile_installed'),
                mock.patch.object(R, 'RUN_ROOT', root), mock.patch.object(E, 'RUN_ROOT', root),
                mock.patch.object(R, '_session_lock_path', return_value=lock),
                mock.patch.object(E, 'EXPECTED_ANDROID_TOPOLOGY_SHA256', TOPOLOGY_SHA),
                mock.patch.object(E, 'require_guard'), mock.patch.object(E, 'validate_run_dir', side_effect=lambda p:p),
                mock.patch.object(E, '_validate_resident_health_receipt'), mock.patch.object(E, '_validate_endpoint'),
                mock.patch.object(E, 'validate_prepared_history'),
                mock.patch.object(E, 'validate_host_closure', return_value=self.closure),
                mock.patch.object(E, 'validate_health_closure', return_value={}),
                mock.patch.object(E, 'candidate_claim_present', return_value=False),
                mock.patch.object(E, 'consume_candidate_globally', side_effect=consume),
                mock.patch.object(E, 'require_candidate_claim'),
                mock.patch.object(E, 'identify_download', return_value=endpoint),
                mock.patch.object(E, 'same_download_session', return_value=True),
                mock.patch.object(E, 'transfer_boot', side_effect=transfer),
                mock.patch.object(E, '_validate_transfer_outcome', side_effect=validate_transfer),
                mock.patch.object(E, 'require_transfer_process_quiescence'),
                mock.patch.object(E, 'require_all_transfer_processes_quiescent'),
                mock.patch.object(E, 'source_closure_receipts', return_value={}),
                mock.patch.object(E, 'health_source_closure_receipts', return_value={}),
                mock.patch.object(E.base, 'bounded_command', return_value=(0, b'List of devices attached\n', b'')),
                mock.patch.object(E, 'durable_json', side_effect=durable),
                mock.patch.object(E, 'enter_rollback_download', side_effect=rollback_entry),
                mock.patch.object(E, 'rollback_from_arrival', return_value={'fixture_rollback': True}),
                mock.patch('subprocess.Popen', side_effect=popen), mock.patch.object(O.time, 'sleep'),
                mock.patch.object(R, '_cage_generations', side_effect=lambda d,k: {1:{'prepare','bound','reconciled'}}
                                  if k in ('candidate', 'rollback') and (d/(k+'-intent.json')).exists() else {}),
                mock.patch.object(R, '_validate_cage_prepare', return_value={'cage':'/fixture/cage'}),
                mock.patch.object(R, '_validate_cage_bound', return_value={'process_cage':{}}),
                mock.patch.object(R, '_effect_matches_cage', return_value=True),
                mock.patch.object(R, '_validate_cage_reconciled')]
            for patch in patches: stack.enter_context(patch)
            if finish is not None:
                health = {**preflight, 'boot_id_sha256': C.sha256(b'fresh TWRP fixture boot'),
                          'health_kind': 'retained_t2_recovery'}
                for patch in (
                    mock.patch.object(E, 'rollback_from_arrival', side_effect=rollback_and_wait),
                    mock.patch.object(E, 'arm_twrp_return', side_effect=[True, False]),
                    mock.patch.object(E, 'resident_health_once', return_value=(health, SERIAL)),
                    mock.patch.object(E, 'record_twrp_arrival'),
                    mock.patch.object(E, 'validate_twrp_arrival', return_value=health),
                    mock.patch.object(E, 'release_guard')):
                    stack.enter_context(patch)
            yield run, prepared, calls

    def test_actual_execute_raw_derived_proof_and_fixed_rollback_identity(self):
        with self.scenario() as (run, prepared, calls):
            self.assertEqual(E.execute(run, prepared['approval_token']), {'fixture_rollback': True})
            value = E.read_json(run / 'candidate-observation.json', 'fixture')
            self.assertEqual(value['claim_verdict'], 'PROVED', value)
            self.assertNotIn('resident_health', value)
            P.validate_candidate_observation(run, value, prepared['binding_sha256'], INITIAL_SHA)
            evidence = E.read_json(run / P.EVIDENCE_NAME, 'fixture')
            self.assertEqual(evidence['collection']['before']['public']['boot_completed'], '0')
            self.assertEqual(evidence['collection']['after']['public']['boot_completed'], '1')
            before = len(calls); P._rederive_evidence(run, prepared); self.assertEqual(len(calls), before)
            self.assertTrue((run / P.ROLLBACK_IDENTITY_NAME).exists())
            with self.assertRaisesRegex(E.B0F1Error, 'consumed'):
                E.execute(run, prepared['approval_token'])
            self.assertEqual([c[0] for c in calls].count('transfer'), 1)

    def test_wrong_prepared_approval_stops_before_claim_or_transport(self):
        with self.scenario() as (run, prepared, calls):
            with self.assertRaisesRegex(E.B0F1Error, 'approval does not match'):
                E.execute(run, 'not-the-returned-approval')
            self.assertEqual(calls, [])
            self.assertFalse((run / 'candidate-intent.json').exists())

    def test_diagnostic_snapshot_keeps_recovery_without_proof(self):
        with self.scenario(fault='truncated') as (run, prepared, calls):
            self.assertEqual(E.execute(run, prepared['approval_token']), {'fixture_rollback': True})
            self.assertEqual(E.read_json(run / 'candidate-observation.json','fixture')['claim_verdict'], 'NO_PROOF')
            self.assertTrue((run / 'p2-snapshot.stdout').exists())

    def test_installed_p2_terminal_requires_proved_rollback_and_fresh_twrp(self):
        for finish in ('proved', 'uncertain'):
            with self.subTest(finish=finish), self.scenario(finish=finish) as (run, prepared, calls):
                self.assertEqual(E.execute(run, prepared['approval_token'])['verdict'], 'ATTENDED_TWRP_ENTRY_PENDING')
                before = list(calls)
                terminal = E.resume_run(run)
                self.assertEqual(calls, before)
                if finish == 'proved':
                    self.assertEqual(terminal['verdict'], 'PROVED_NATIVE_PID1_RETURNED_TWRP_HEALTHY')
                    self.assertTrue(terminal['experiment_pass'])
                    self.assertTrue((run / 'terminal.json').exists())
                else:
                    self.assertEqual(terminal['verdict'], 'ROLLBACK_OUTCOME_UNPROVED_TWRP_HEALTHY')
                    self.assertFalse((run / 'terminal.json').exists())

    def test_shared_parser_and_loaded_apis_are_bound(self):
        parser = C.kmsg
        self.assertIn(str(Path(parser.__file__).relative_to(P.ROOT)), P.SOURCE_PINS)
        for module, name in ((C, 'analyze'), (parser, 'parse_capture'), (parser, 'survey'),
                             (O, 'allowed'), (O.Collector, 'capture')):
            with self.subTest(name=name), mock.patch.object(module, name, return_value=True), \
                    self.assertRaisesRegex(P.P2F1Error, 'API was rebound'):
                P.source_receipts()

    def test_recovery_rederives_evidence_without_build_only_development_files(self):
        with self.scenario() as (run, prepared, calls):
            E.execute(run, prepared['approval_token'])
            actual = P._input_bytes
            build_only = {P.BUILDER_PATH, P.SOURCE_PATH}
            def missing(path):
                if path in build_only: raise FileNotFoundError('fixture build-only input removed')
                return actual(path)
            with mock.patch.object(P, '_input_bytes', side_effect=missing):
                P._rederive_evidence(run, prepared)
                P.source_receipts(candidate=False)
                with self.assertRaises(FileNotFoundError): P.source_receipts()
            def missing_header(path):
                if path == C.HEADER: raise FileNotFoundError('runtime header absent')
                return actual(path)
            with mock.patch.object(P, '_input_bytes', side_effect=missing_header), \
                    self.assertRaises(FileNotFoundError):
                P._rederive_evidence(run, prepared)

    def test_failure_and_reporting_cut_resume_without_new_acquisition(self):
        for fault in ('reader-rc', 'changed-boot', 'publish', 'root'):
            with self.subTest(fault=fault), self.scenario(fault=fault) as (run, prepared, calls):
                value = E.execute(run, prepared['approval_token'])
                self.assertEqual(value['verdict'], 'RECOVERY_PENDING_PHYSICAL_DOWNLOAD')
                self.assertTrue((run / P.FAILURE_NAME).exists())
                if fault != 'root': self.assertTrue((run / 'p2-snapshot.stdout').exists())
                before = list(calls)
                E.resume_run(run); self.assertEqual(calls, before)
                # This is a private fixture reporting cut, never a consumed device journal.
                (run / 'candidate-observation.json').unlink()
                E.resume_run(run); self.assertEqual(calls, before)
                obs = E.read_json(run / 'candidate-observation.json', 'fixture')
                P.validate_candidate_observation(run, obs, prepared['binding_sha256'], INITIAL_SHA)
                self.assertEqual(obs['claim_verdict'], 'NO_PROOF')

    def test_reader_absence_can_retry_but_root_failure_cannot(self):
        with self.scenario(early_attempt='reader-absent') as (run, prepared, calls):
            E.execute(run, prepared['approval_token'])
            evidence = E.read_json(run / P.EVIDENCE_NAME, 'fixture')
            self.assertEqual(evidence['collection']['selected_attempt'], 1)
        with self.scenario(fault='root') as (run, prepared, calls):
            E.execute(run, prepared['approval_token'])
            self.assertFalse((run / 'p2-ready-01-inventory.capture.json').exists())

    def test_replay_rejects_stream_substitution_and_raw_fault_flags(self):
        with self.scenario() as (run, prepared, calls):
            E.execute(run, prepared['approval_token'])
            actual = E.raw_capture.load_handle
            def substituted(path):
                handle = actual(path)
                return dataclasses.replace(handle, stdout={**handle.stdout, 'name': 'p2-post-root.stdout'})
            with mock.patch.object(E.raw_capture, 'load_handle', side_effect=substituted), \
                    self.assertRaisesRegex(O.ObservationError, 'stream-binding'):
                P._rederive_evidence(run, prepared)
            for flag, v in (('timed_out', True), ('output_exceeded', True), ('producer_error_type', 'Fixture')):
                def faulty(path): return dataclasses.replace(actual(path), **{flag:v})
                with mock.patch.object(E.raw_capture, 'load_handle', side_effect=faulty), \
                        self.assertRaisesRegex(O.ObservationError, 'raw-acquisition-failed'):
                    P._rederive_evidence(run, prepared)

    def test_fixed_read_requires_lease_and_declared_command(self):
        with self.assertRaises(Exception):
            E.raw_capture.acquire_command(O.command(E, None, 'p2-ready-00-inventory'), Path('/fixture'),
                                          'p2-ready-00-inventory', **O.bounds('p2-ready-00-inventory'))
        fixed = O.command(E, SERIAL, 'p2-post-root')
        self.assertTrue(O.allowed(E, fixed, 'p2-post-root', O.bounds('p2-post-root')))
        self.assertFalse(O.allowed(E, fixed + ['extra'], 'p2-post-root', O.bounds('p2-post-root')))
        self.assertFalse(O.allowed(E, fixed, 'p2-post-root', {**O.bounds('p2-post-root'), 'timeout': 99}))


if __name__ == '__main__': unittest.main()

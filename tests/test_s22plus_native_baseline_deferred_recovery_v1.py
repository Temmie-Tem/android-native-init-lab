"""Actual resident C/PTY and retained readers; hardware effects are fixtures."""
from contextlib import redirect_stdout, redirect_stderr
import copy
import io
import json
from pathlib import Path
import time
import tempfile
import unittest
from unittest import mock

import test_s22plus_native_baseline_owner_v2 as attended

owner, live = attended.owner, attended.live


class ReviewBindingTests(unittest.TestCase):
    def test_distinct_current_review_binds_deferred_policy_and_risk_authority(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for name in (owner.DEFERRED_POLICY, 'docs/operations/DEVICE_ACTION_RISK_TIERS.md'):
                path = root/name; path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes((owner.ROOT/name).read_bytes())
            sources = owner.deferred_review_sources(root)
            review = root/owner.DEFERRED_REVIEW; review.parent.mkdir(parents=True)
            value = dict(verdict='PASS_GO', findings=[], activation=owner.DEFERRED_MODE,
                         limits=owner.DEFERRED_LIMITS, current_sources=sources)
            owner.records.persist_json(review, value)
            self.assertEqual(owner.reviewed(root, policy=owner.V2_POLICY, execution_mode=owner.DEFERRED_MODE), owner.pin(review))
            for name in (owner.DEFERRED_POLICY, 'docs/operations/DEVICE_ACTION_RISK_TIERS.md'):
                path = root/name; original = path.read_bytes(); path.write_bytes(original+b'\nchanged\n')
                with self.assertRaisesRegex(owner.BaselineError, 'sources changed'):
                    owner.reviewed(root, policy=owner.V2_POLICY, execution_mode=owner.DEFERRED_MODE)
                path.write_bytes(original)
            review.unlink(); value['activation'] = owner.V2_POLICY
            owner.records.persist_json(review, value)
            with self.assertRaisesRegex(owner.BaselineError, 'activated independent review'):
                owner.reviewed(root, policy=owner.V2_POLICY, execution_mode=owner.DEFERRED_MODE)


class DeferredRecoveryTests(unittest.TestCase):
    setUpClass = classmethod(attended.OwnerV2Tests.setUpClass.__func__)
    exercise_native = attended.OwnerV2Tests.exercise_native
    running = attended.OwnerV2Tests.running
    grant = attended.OwnerV2Tests.grant
    execute = attended.OwnerV2Tests.execute
    bootstrap = attended.OwnerV2Tests.bootstrap

    def fixture(self):
        fixture = attended.OwnerV2Tests.fixture(self)
        for name in (owner.DEFERRED_POLICY, 'docs/operations/DEVICE_ACTION_RISK_TIERS.md'):
            path = fixture.prepared.root/name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes((owner.ROOT/name).read_bytes())
        return fixture

    def proposal(self, fixture, **changes):
        values = dict(manifest=fixture.manifest, experiment_manifest=fixture.experiment_manifest,
            target_file=fixture.target_file, operations=['experiment'], reservations=1, seconds=600,
            policy=owner.V2_POLICY, execution_mode=owner.DEFERRED_MODE)
        values.update(changes)
        folder = fixture.prepared.root/owner.V2_BASE/str(time.monotonic_ns())
        return owner.prepare_request(live, fixture.prepared.root, folder, **values)

    def deferred_grant(self, fixture):
        proposal = self.proposal(fixture)
        request = Path(proposal['request']['path'])
        owner.open_grant(live, fixture.prepared.root, request, proposal['approval'], attended=False)
        return request.parent/'grant.json'

    def run_deferred(self, fixture, grant, prior):
        return owner.execute(live, fixture.prepared.root, grant, 'experiment', 'native',
            prior_native=prior, attended=False, backend=fixture.backend)

    def test_normal_unattended_N_E_N_and_exact_mode_grant(self):
        fixture = self.fixture(); prior, _ = self.bootstrap(fixture)
        grant = self.deferred_grant(fixture)
        record, _, request, _ = owner.load_grant(live, fixture.prepared.root, grant)
        self.assertIs(record['attended'], False)
        self.assertIs(request['physical_attendance_required'], False)
        self.assertEqual(record['execution_mode'], owner.DEFERRED_MODE)
        result = self.run_deferred(fixture, grant, prior)
        self.assertEqual(result['state'], 'NATIVE_CLOSED', result)
        operation = owner.load_operation(live, fixture.prepared.root, grant.parent/'operation-01')
        self.assertEqual(owner.native_terminal(live, fixture.prepared.root, operation.directory), result)
        self.assertEqual(fixture.backend.calls.count('transfer-'+owner.TRANSFER_NATIVE), 4)
        self.assertNotIn('transfer-'+owner.TRANSFER_ANDROID, fixture.backend.calls)
        owner.registry.require_no_f1_owner(fixture.prepared.root)
        self.assertTrue((grant.parent/'closed.json').exists())

    def test_failures_park_without_recovery_or_new_native_effect_then_later_A(self):
        for fault in ('native-start-guard', 'experiment-health', 'experiment-transfer',
                      'native-final-health', 'native-final-transfer', 'same-boot'):
            with self.subTest(fault=fault):
                fixture = self.fixture(); prior, _ = self.bootstrap(fixture)
                grant = self.deferred_grant(fixture); fixture.backend.fault = fault
                with mock.patch.object(owner, 'recover', side_effect=AssertionError('unattended recovery')):
                    result = self.run_deferred(fixture, grant, prior)
                self.assertEqual(result['state'], 'PARKED', result)
                self.assertEqual(result['device_activity'], 'UNKNOWN')
                self.assertTrue(result['recovery_required'])
                directory = grant.parent/'operation-01'
                operation = owner.load_operation(live, fixture.prepared.root, directory)
                owner.registry.require_f1_owner(fixture.prepared.root, directory, operation.binding)
                self.assertTrue((directory/owner.STOP).exists())
                self.assertTrue((grant.parent/'closed.json').exists())
                self.assertFalse((directory/'android-exit').exists())
                self.assertNotIn('transfer-'+owner.TRANSFER_ANDROID, fixture.backend.calls)
                count = len(fixture.backend.calls)
                with self.assertRaises(owner.BaselineError): self.run_deferred(fixture, grant, prior)
                with self.assertRaises(owner.registry.RegistryError): self.deferred_grant(fixture)
                with owner.registry.target_session_lease(fixture.prepared.root):
                    with self.assertRaisesRegex(owner.BaselineError, 'attendance'):
                        owner.recover(live, operation, fixture.backend, attended=False)
                self.assertEqual(len(fixture.backend.calls), count)
                self.assertEqual(owner.operation_status(live, operation)['state'], 'PARKED')
                native_count = fixture.backend.calls.count('transfer-'+owner.TRANSFER_NATIVE)
                with mock.patch.object(owner.protocol, 'host_now_ns', return_value=operation.grant['deadline_boottime_ns']+1), \
                        owner.registry.target_session_lease(fixture.prepared.root):
                    result = owner.recover(live, operation, fixture.backend, attended=True)
                self.assertEqual(result['state'], 'ANDROID_CLOSED', result)
                self.assertEqual(fixture.backend.calls.count('transfer-'+owner.TRANSFER_NATIVE), native_count)
                self.assertEqual(fixture.backend.calls.count('transfer-'+owner.TRANSFER_ANDROID), 1)
                owner.registry.require_no_f1_owner(fixture.prepared.root)
                fixture.backend.stop_peer()

    def test_hard_cuts_keep_unknown_status_and_never_resume_native_roles(self):
        cuts = [(phase, owner.TRANSFER_NATIVE+'-attempt-01.'+suffix+'.json', when)
            for phase in ('experiment', 'native-final') for suffix in ('start', 'delivery', 'result')
            for when in ('before', 'after')]
        cuts += [('operation-01', 'terminal.json', 'before'), ('operation-01', 'terminal.json', 'after')]
        for phase, name, when in cuts:
            with self.subTest(phase=phase, name=name, when=when):
                fixture = self.fixture(); prior, _ = self.bootstrap(fixture)
                grant = self.deferred_grant(fixture); hit = []
                def intercept(writer):
                    def write(path, value, *args, **kwargs):
                        chosen = Path(path).parent.name == phase and Path(path).name == name and not hit
                        if chosen and when == 'before': hit.append(True); raise KeyboardInterrupt('publication cut')
                        result = writer(path, value, *args, **kwargs)
                        if chosen and when == 'after': hit.append(True); raise KeyboardInterrupt('publication cut')
                        return result
                    return write
                with mock.patch.object(live.core, '_write_exclusive', side_effect=intercept(live.core._write_exclusive)), \
                        mock.patch.object(owner.records, '_write_exclusive', side_effect=intercept(owner.records._write_exclusive)), \
                        self.assertRaises(KeyboardInterrupt):
                    self.run_deferred(fixture, grant, prior)
                self.assertEqual(hit, [True])
                operation = owner.load_operation(live, fixture.prepared.root, grant.parent/'operation-01')
                before = fixture.backend.calls.count('transfer-'+owner.TRANSFER_NATIVE)
                if name != 'terminal.json':
                    status = owner.operation_status(live, operation)
                    self.assertEqual(status['state'], 'UNRESOLVED')
                    self.assertEqual(status['process_activity'], 'UNKNOWN')
                with owner.registry.target_session_lease(fixture.prepared.root), \
                        mock.patch.object(fixture.backend, 'candidate_observer_session', side_effect=AssertionError('native resume')):
                    result = owner.recover(live, operation, fixture.backend, attended=True)
                self.assertEqual(result['state'], 'NATIVE_CLOSED' if name == 'terminal.json' else 'ANDROID_CLOSED', result)
                self.assertEqual(fixture.backend.calls.count('transfer-'+owner.TRANSFER_NATIVE), before)
                self.assertEqual(fixture.backend.calls.count('transfer-'+owner.TRANSFER_ANDROID), 0 if name == 'terminal.json' else 1)
                fixture.backend.stop_peer()

    def test_deferred_policy_drift_blocks_A_and_uncertain_A_never_replays(self):
        fixture = self.fixture(); prior, _ = self.bootstrap(fixture)
        grant = self.deferred_grant(fixture); fixture.backend.fault = 'experiment-health'
        self.run_deferred(fixture, grant, prior)
        operation = owner.load_operation(live, fixture.prepared.root, grant.parent/'operation-01')
        policy = fixture.prepared.root/owner.DEFERRED_POLICY; original = policy.read_bytes()
        policy.write_bytes(original+b'\nchanged authority\n')
        with owner.registry.target_session_lease(fixture.prepared.root), self.assertRaisesRegex(owner.BaselineError, 'recovery source'):
            owner.recover(live, operation, fixture.backend, attended=True)
        self.assertNotIn('transfer-'+owner.TRANSFER_ANDROID, fixture.backend.calls)
        policy.write_bytes(original); fixture.backend.fault = 'android-exit-transfer'
        with owner.registry.target_session_lease(fixture.prepared.root), self.assertRaises(owner.BaselineError):
            owner.recover(live, operation, fixture.backend, attended=True)
        with owner.registry.target_session_lease(fixture.prepared.root), self.assertRaisesRegex(owner.BaselineError, 'consumed'):
            owner.recover(live, operation, fixture.backend, attended=True)
        self.assertEqual(fixture.backend.calls.count('transfer-'+owner.TRANSFER_ANDROID), 1)

    def test_mode_schema_scope_and_legacy_attendance_cannot_be_downgraded(self):
        fixture = self.fixture()
        for changes in (dict(execution_mode='unknown'), dict(execution_mode=False), dict(policy=None),
                        dict(operations=['bootstrap'], experiment_manifest=None), dict(reservations=2),
                        dict(operations=['experiment', 'android-exit']), dict(seconds=601)):
            with self.subTest(changes=changes), self.assertRaises(owner.BaselineError): self.proposal(fixture, **changes)
        legacy = self.grant(fixture)
        with self.assertRaisesRegex(owner.BaselineError, 'attendance'):
            owner.execute(live, fixture.prepared.root, legacy, 'bootstrap', 'android', attended=False, backend=fixture.backend)
        self.assertFalse((legacy.parent/'01-reserved.json').exists())
        grant = self.deferred_grant(fixture)
        original = owner.read(grant)[0]
        for mutation in (lambda v: v.pop('execution_mode'), lambda v: v.update(attended=0),
                         lambda v: v.update(execution_mode='attended')):
            value = copy.deepcopy(original); mutation(value)
            grant.unlink(); owner.publish(grant, value)
            with self.assertRaises(owner.BaselineError): owner.load_grant(live, fixture.prepared.root, grant)
        grant.unlink(); owner.publish(grant, original)
        request = grant.parent/'request.json'; original = owner.read(request)[0]
        for mutation in (lambda v: v.pop('execution_mode'), lambda v: v.update(physical_attendance_required=True),
                         lambda v: v.update(recovery='one-exact-android'), lambda v: v.update(execution_mode=None)):
            value = copy.deepcopy(original); mutation(value)
            request.unlink(); owner.publish(request, value)
            with self.assertRaises(owner.BaselineError): owner.load_request(live, fixture.prepared.root, request)

    def test_real_cli_routes_prepare_grant_execute_status_without_attended_flag(self):
        fixture = self.fixture(); prior, _ = self.bootstrap(fixture)
        root = fixture.prepared.root
        folder = root/owner.V2_BASE/'cli-mode'
        def cli(args):
            output = io.StringIO()
            with redirect_stdout(output), redirect_stderr(io.StringIO()):
                self.assertEqual(owner.main(['--root', str(root), *map(str, args)]), 0)
            return json.loads(output.getvalue().splitlines()[-1])
        proposal = cli(['prepare', '--out', folder, '--manifest', fixture.manifest,
            '--experiment-manifest', fixture.experiment_manifest, '--target-file', fixture.target_file,
            '--operations', 'experiment', '--policy', owner.V2_POLICY, '--execution-mode', owner.DEFERRED_MODE])
        cli(['grant', '--request', folder/'request.json', '--approval', proposal['approval']])
        fixture.backend.fault = 'experiment-health'
        with mock.patch.object(live, 'SamsungOdinBackend', return_value=fixture.backend):
            result = cli(['execute', '--grant', folder/'grant.json', '--operation', 'experiment',
                          '--origin', 'native', '--prior-native', prior])
        self.assertEqual(result['state'], 'PARKED')
        self.assertEqual(cli(['status', '--operation-dir', folder/'operation-01'])['state'], 'PARKED')


if __name__ == '__main__': unittest.main()

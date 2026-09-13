"""Scope/claim/observer consumers with real resident C and synthetic hardware."""
from contextlib import contextmanager, ExitStack
import copy
import hashlib
import json
import os
from pathlib import Path
import pty
import tempfile
import time
from types import SimpleNamespace
import tty
import unittest
from unittest import mock

import test_s22plus_native_baseline_owner_v2 as attended
import s22plus_native_research_scope_v1 as scope
import s22plus_native_reobservation_v1 as observation

owner, live = attended.owner, attended.live


def input_receipt(path):
    return {name: value for name, value in owner.pin(path).items() if name != 'path'}


class ScopeTests(unittest.TestCase):
    setUpClass = classmethod(attended.OwnerV2Tests.setUpClass.__func__)
    exercise_native = attended.OwnerV2Tests.exercise_native
    running = attended.OwnerV2Tests.running
    grant = attended.OwnerV2Tests.grant
    execute = attended.OwnerV2Tests.execute
    bootstrap = attended.OwnerV2Tests.bootstrap

    def fixture(self):
        fixture = attended.OwnerV2Tests.fixture(self)
        root = fixture.prepared.root
        for name in (scope.POLICY, 'docs/operations/DEVICE_ACTION_RISK_TIERS.md'):
            path = root/name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes((owner.ROOT/name).read_bytes())
        for name in scope.MUTABLE_INPUTS:
            path = root/name; path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('/* declared functional source fixture; real protocol C is compiled separately */\n')
        original = owner.current_static
        def selected(bundle=None):
            value = original(bundle); old = value.builder.source_receipts
            value.builder.source_receipts = lambda: dict(old(), **{name: input_receipt(root/name) for name in scope.MUTABLE_INPUTS})
            return value
        stack = ExitStack(); self.addCleanup(stack.close)
        stack.enter_context(mock.patch.object(owner, 'current_static', side_effect=selected))
        reference = {name: input_receipt(root/name) for name in scope.MUTABLE_INPUTS}
        review = root/'scope-review-fixture.json'; owner.publish(review, dict(verdict='PASS_GO', findings=[], functional_reference_inputs=reference))
        stack.enter_context(mock.patch.object(scope, 'reviewed', return_value=owner.pin(review)))
        stack.enter_context(mock.patch.object(scope, 'functional_reference', return_value=reference))
        stack.enter_context(mock.patch.object(scope, '_native_inputs', side_effect=lambda profiles:
            owner.current_static(fixture.bundles['p387']).builder.source_receipts()))
        fixture.scope_review = review
        return fixture

    def task(self, fixture, prior, *, reservations=3, seconds=1800, mutable_paths=None, recovery='deferred'):
        path = fixture.prepared.root/scope.BASE/str(time.monotonic_ns())
        value = scope.prepare(live, fixture.prepared.root, path, baseline_terminal=prior,
            operations=['observe', 'experiment', 'restore', 'android-exit'], profiles=['resident-v1'],
            mutable_paths=sorted(scope.MUTABLE_INPUTS) if mutable_paths is None else mutable_paths,
            seconds=seconds, reservations=reservations, recovery=recovery, purpose='Bounded synthetic-hardware research task')
        scope.open_grant(live, fixture.prepared.root, Path(value['request']['path']), value['approval'], attended=recovery == 'attended')
        return path/'grant.json'

    def select(self, fixture, task, *, repeat=None, assessment=None, operation='experiment'):
        return Path(scope.select(live, fixture.prepared.root, task, operation=operation,
            manifest=fixture.experiment_manifest if repeat is None and operation == 'experiment' else None,
            repeat=repeat, source_assessment=assessment)['grant']['path'])

    def run_child(self, fixture, child, prior, *, operation='experiment', origin='native', attended=False):
        return owner.execute(live, fixture.prepared.root, child, operation, origin,
            prior_native=prior, attended=attended, backend=fixture.backend)

    def assessment(self, fixture):
        native = owner.native_identity(fixture.bundles['p388'])
        path = fixture.prepared.root/'workspace/private'/('assessment-'+str(time.monotonic_ns())+'.json')
        owner.publish(path, dict(schema='s22plus-functional-source-assessment-v1', verdict='PASS_GO', findings=[],
            independent_review=True, reviewer='independent-fixture-review', **scope.source_assessment_binding(native, 'resident-v1')))
        return path

    def test_one_scope_selects_E_then_repeats_with_original_claim_and_no_child_approval(self):
        fixture = self.fixture(); prior, initial = self.bootstrap(fixture); original = prior.read_bytes()
        task = self.task(fixture, prior); parent = scope.load_grant(live, fixture.prepared.root, task)[0]
        child = self.select(fixture, task)
        delegated, _, request, _ = owner.load_grant(live, fixture.prepared.root, child)
        self.assertEqual(delegated['operator_approval'], parent['operator_approval'])
        self.assertEqual(delegated['deadline_boottime_ns'], parent['deadline_boottime_ns'])
        self.assertGreater(request['seconds'], 600)
        first = self.run_child(fixture, child, prior); self.assertEqual(first['state'], 'NATIVE_CLOSED', first)
        op = owner.load_operation(live, fixture.prepared.root, child.parent/'operation-01')
        identity = live._bound_candidate_registry_identity(owner.primary_prepared(live, op))
        claim = owner.registry.active_claim(fixture.prepared.root, identity['candidate_key'])
        admission = scope._repeat_path(fixture.prepared.root, identity)
        second_child = self.select(fixture, task, repeat=admission)
        second = self.run_child(fixture, second_child, op.directory/'terminal.json')
        self.assertEqual(second['state'], 'NATIVE_CLOSED', second)
        self.assertEqual(owner.registry.active_claim(fixture.prepared.root, identity['candidate_key']), claim)
        self.assertTrue((second_child.parent/'operation-01/repeat-intent.json').exists())
        self.assertEqual(prior.read_bytes(), original)
        final_child = self.select(fixture, task, operation='android-exit')
        final = self.run_child(fixture, final_child, second_child.parent/'operation-01/terminal.json', operation='android-exit')
        self.assertEqual(final['state'], 'ANDROID_CLOSED', final)
        self.assertEqual(fixture.backend.calls.count('transfer-'+owner.TRANSFER_NATIVE), 6)
        self.assertEqual(fixture.backend.calls.count('transfer-'+owner.TRANSFER_ANDROID), 1)
        with self.assertRaisesRegex(owner.BaselineError, 'budget'):
            self.select(fixture, task, operation='restore')

    def test_legacy_E_cannot_gain_prospective_repeat_eligibility(self):
        fixture = self.fixture(); prior, _ = self.bootstrap(fixture)
        legacy = self.grant(fixture, operations=['experiment'])
        result = self.execute(fixture, legacy, 'experiment', 'native', prior)
        self.assertEqual(result['state'], 'NATIVE_CLOSED', result)
        latest = legacy.parent/'operation-01/terminal.json'; task = self.task(fixture, latest)
        before = list(fixture.backend.calls)
        with self.assertRaises(owner.registry.DuplicateCandidateClaim): self.select(fixture, task)
        self.assertEqual(fixture.backend.calls, before)
        self.assertFalse((fixture.prepared.root/scope.REPEATS).exists())

    def test_current_fragment_is_not_silently_blessed_by_a_new_scope_and_review_is_reusable(self):
        fixture = self.fixture(); prior, initial = self.bootstrap(fixture)
        name = sorted(scope.MUTABLE_INPUTS)[0]; (fixture.prepared.root/name).write_text('/* changed executable fixture */\n')
        task = self.task(fixture, prior)
        with self.assertRaisesRegex(owner.BaselineError, 'independent source-effect assessment'):
            self.select(fixture, task)
        assessment = self.assessment(fixture)
        child = self.select(fixture, task, assessment=assessment)
        result = self.run_child(fixture, child, prior)
        self.assertEqual(result['state'], 'NATIVE_CLOSED', result)
        self.assertEqual(result['native'], initial['native'])  # N is the admitted byte identity.
        self.assertNotEqual(owner.native_identity(fixture.bundles['p387']), result['native'])
        op = owner.load_operation(live, fixture.prepared.root, child.parent/'operation-01')
        admission = scope._repeat_path(fixture.prepared.root, live._bound_candidate_registry_identity(owner.primary_prepared(live, op)))
        again = self.select(fixture, task, repeat=admission)
        self.assertEqual(owner.load_grant(live, fixture.prepared.root, again)[2]['research_scope']['source_assessment'], owner.pin(assessment))

    def test_out_of_scope_source_and_stale_assessment_reject_before_reservation(self):
        fixture = self.fixture(); prior, _ = self.bootstrap(fixture); task = self.task(fixture, prior)
        name = sorted(scope.MUTABLE_INPUTS)[0]; path = fixture.prepared.root/name
        path.write_text('/* first changed fixture */\n'); assessment = self.assessment(fixture)
        path.write_text('/* different changed fixture */\n')
        with self.assertRaisesRegex(owner.BaselineError, 'exact executable bytes'):
            self.select(fixture, task, assessment=assessment)
        immutable = fixture.prepared.root/'native-source-fixture.c'; immutable.write_text('/* unauthorized input change */\n')
        with self.assertRaisesRegex(owner.BaselineError, 'outside the accepted functional scope'):
            self.select(fixture, task, assessment=assessment)
        self.assertFalse((task.parent/'children').exists())

    def test_expiry_and_parent_tamper_block_child_before_any_native_effect(self):
        fixture = self.fixture(); prior, _ = self.bootstrap(fixture); task = self.task(fixture, prior)
        child = self.select(fixture, task); parent = scope.load_grant(live, fixture.prepared.root, task)[0]
        before = list(fixture.backend.calls)
        with mock.patch.object(owner.protocol, 'host_now_ns', return_value=parent['deadline_boottime_ns']), \
                self.assertRaisesRegex(owner.BaselineError, 'expired'):
            self.run_child(fixture, child, prior)
        value = owner.read(child)[0]; child.unlink(); value['deadline_boottime_ns'] += 10**9; owner.publish(child, value)
        with self.assertRaisesRegex(owner.BaselineError, 'original scope'):
            self.run_child(fixture, child, prior)
        self.assertEqual(fixture.backend.calls, before)
        self.assertFalse((child.parent/'01-reserved.json').exists())

    def test_unexecuted_cancellation_releases_capacity_but_never_reuses_ordinal(self):
        fixture = self.fixture(); prior, _ = self.bootstrap(fixture); task = self.task(fixture, prior, reservations=1)
        child = self.select(fixture, task)
        scope.cancel_child(live, fixture.prepared.root, child.parent, reason='superseded before any operation')
        with self.assertRaises(owner.BaselineError): self.run_child(fixture, child, prior)
        replacement = self.select(fixture, task)
        self.assertEqual(replacement.parent.name, '000002')
        result = self.run_child(fixture, replacement, prior)
        self.assertEqual(result['state'], 'NATIVE_CLOSED', result)
        with self.assertRaisesRegex(owner.BaselineError, 'operation/reservation'):
            scope.cancel_child(live, fixture.prepared.root, replacement.parent, reason='cannot hide an effect')

    def test_interrupted_child_selection_completes_or_cancels_without_new_approval(self):
        for filename in ('request.json', 'selection.json', 'grant.json'):
            with self.subTest(filename=filename):
                fixture = self.fixture(); prior, _ = self.bootstrap(fixture); task = self.task(fixture, prior, reservations=1)
                original = owner.publish; hit = []
                def cut(path, value):
                    if Path(path).name == filename and Path(path).parent.parent.name == 'children' and not hit:
                        hit.append(True); raise KeyboardInterrupt('host selection cut')
                    return original(path, value)
                with mock.patch.object(owner, 'publish', side_effect=cut), self.assertRaises(KeyboardInterrupt): self.select(fixture, task)
                self.assertEqual(hit, [True]); child = task.parent/'children/000001'
                before = list(fixture.backend.calls)
                if filename == 'request.json':
                    scope.cancel_child(live, fixture.prepared.root, child, reason='no complete request was published')
                    selected = self.select(fixture, task)
                else:
                    selected = Path(scope.complete_selection(live, fixture.prepared.root, child)['path'])
                self.assertEqual(fixture.backend.calls, before)
                self.assertEqual(self.run_child(fixture, selected, prior)['state'], 'NATIVE_CLOSED')
                fixture.backend.stop_peer()

    def test_deferred_failure_keeps_original_A_and_scope_cannot_overtake_owner(self):
        fixture = self.fixture(); prior, _ = self.bootstrap(fixture); task = self.task(fixture, prior)
        child = self.select(fixture, task); fixture.backend.fault = 'experiment-transfer'
        result = self.run_child(fixture, child, prior); self.assertEqual(result['state'], 'PARKED', result)
        operation = owner.load_operation(live, fixture.prepared.root, child.parent/'operation-01')
        owner.registry.require_f1_owner(fixture.prepared.root, operation.directory, operation.binding)
        with self.assertRaises(owner.registry.RegistryError):
            observation.observe(live, fixture.prepared.root, prior,
                fixture.prepared.root/observation.BASE/'blocked', purpose='fixed read cannot steal a recovery owner')
        parent = scope.load_grant(live, fixture.prepared.root, task)[0]
        with mock.patch.object(owner.protocol, 'host_now_ns', return_value=parent['deadline_boottime_ns']+1), \
                owner.registry.target_session_lease(fixture.prepared.root):
            recovered = owner.recover(live, operation, fixture.backend, attended=True)
        self.assertEqual(recovered['state'], 'ANDROID_CLOSED', recovered)
        self.assertEqual(fixture.backend.calls.count('transfer-'+owner.TRANSFER_ANDROID), 1)

    def test_recovered_A_after_failed_N_return_cannot_mint_repeat_admission(self):
        fixture = self.fixture(); prior, _ = self.bootstrap(fixture); task = self.task(fixture, prior)
        child = self.select(fixture, task); fixture.backend.fault = 'native-final-transfer'
        result = self.run_child(fixture, child, prior); self.assertEqual(result['state'], 'PARKED', result)
        operation = owner.load_operation(live, fixture.prepared.root, child.parent/'operation-01')
        owner.experiment_outcome(live, operation)  # E health alone is insufficient.
        with owner.registry.target_session_lease(fixture.prepared.root):
            recovered = owner.recover(live, operation, fixture.backend, attended=True)
        self.assertEqual(recovered['state'], 'ANDROID_CLOSED', recovered)
        identity = live._bound_candidate_registry_identity(owner.primary_prepared(live, operation))
        path = scope._repeat_path(fixture.prepared.root, identity)
        self.assertFalse(path.exists())
        path.parent.mkdir(parents=True)
        owner.publish(path, dict(schema=scope.SCHEMA, kind='prospective-repeat-admission',
            operation=operation.receipt, terminal=owner.pin(operation.directory/'terminal.json'),
            claim=owner.registry.active_claim(fixture.prepared.root, identity['candidate_key']),
            native=operation.request['experiment']['native'], target=operation.request['target']))
        with self.assertRaisesRegex(owner.BaselineError, 'original closed health'):
            scope.repeat_admission(live, fixture.prepared.root, path)
        with owner.registry.target_session_lease(fixture.prepared.root):
            self.assertEqual(owner.recover(live, operation, fixture.backend, attended=True), recovered)
        self.assertEqual(fixture.backend.calls.count('transfer-'+owner.TRANSFER_ANDROID), 1)


if __name__ == '__main__': unittest.main()

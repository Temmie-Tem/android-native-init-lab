"""Local fixtures for the read-only ordinary-cue adoption check."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import unittest.mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'workspace/public/src/scripts/analysis'))
import s22plus_ordinary_cue_cutover_h0 as cutover
import s22plus_native_records_v3 as records
import s22plus_mainline_profile_v1 as profile
from s22plus_mainline_task_v1 import IMAGE_V2
from s22plus_mainline_terminal_v1 import ENTRY
from s22plus_native_task_v3 import approval_text


class PrivateWalkTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.closed = self.root / 'build' / 'tree' / 'home' / 'lab'
        self.closed.mkdir(parents=True)
        (self.root / 'task-a').mkdir()
        self.closed.chmod(0)
        self.addCleanup(self.closed.chmod, 0o700)

    def walk(self):
        return [folder for folder, _, _ in cutover.private_walk(self.root)]

    def test_an_unreadable_directory_owned_by_the_lab_uid_holds_cutover(self):
        with self.assertRaises(PermissionError):
            self.walk()

    def test_an_unreadable_directory_owned_by_another_uid_is_skipped(self):
        real = os.getuid()
        with unittest.mock.patch.object(cutover.os, 'getuid', return_value=real + 100000):
            folders = self.walk()
        self.assertIn(self.root / 'task-a', folders)
        self.assertNotIn(self.closed, folders)

    def test_a_foreign_search_only_directory_still_holds_cutover(self):
        self.closed.chmod(0o100)  # search only: exact-path record access works, listing does not
        real = os.getuid()
        with unittest.mock.patch.object(cutover.os, 'getuid', return_value=real + 100000):
            with self.assertRaises(PermissionError):
                self.walk()

    def test_a_foreign_directory_the_lab_uid_can_write_still_holds_cutover(self):
        self.closed.chmod(0o300)  # writable and searchable, not listable
        real = os.getuid()
        with unittest.mock.patch.object(cutover.os, 'getuid', return_value=real + 100000):
            with self.assertRaises(PermissionError):
                self.walk()


class CutoverTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.private = self.root/'workspace/private'
        self.private.mkdir(parents=True)
        (self.root/cutover.BINDINGS).mkdir(parents=True)

    def closed_operation(self):
        path = self.root/cutover.OLD_LOADER
        source = self.root/'source.py'
        source.write_text('# original\n')
        review = records.publish(path, dict(verdict='PASS_GO', findings=[],
            schema='s22plus-loader-android-review-v1', scope='LOADER_ANDROID_F1_CAPABILITY',
            sources=[dict(records.pin(source), path='source.py')]))
        # This direct-CLI operation has no gateway dispatch.
        folder = self.private/'analysis/timing-direct/task'
        return self.comparison_operation(folder, {'review': review}, 'loader-android')

    def comparison_operation(self, folder, task_value, operation_name):
        operation = folder/'operation-0001'
        operation.mkdir(parents=True)
        task_path = folder/'task.json'
        if task_path.exists():
            self.assertEqual(records.read(task_path), task_value)
            task = records.pin(task_path)
        else:
            task = records.publish(task_path, task_value)
        now = records.clock()
        grant = records.publish(folder/'grant.json', dict(task=task, directory=str(folder),
            schema=records.SCHEMA, host_boot=records.host_boot(),
            opened_ns=now, deadline_ns=now+600_000_000_000))
        request = records.publish(operation/'operation.json', dict(
            schema=records.SCHEMA, operation=operation_name, task=task, grant=grant))
        journal = records.Journal(operation/'journal')
        journal.append('effect-intent', step='install-android', action='transfer', role='A')
        terminal = records.publish(operation/'terminal.json', dict(
            schema=records.SCHEMA, operation_sha256=request['sha256'], grant=grant,
            terminal_state='ANDROID_CLOSED_HEALTHY', research_closed=True))
        closure = dict(schema='s22plus-comparison-task-closed-v1', task=task, grant=grant,
            operation=request, source_binding=task_value['review'], current_android_terminal=terminal,
            terminal_state='ANDROID_CLOSED_HEALTHY', journal_rows=1,
            journal_tail=records.pin(journal.directory/'0000.json'),
            original_A_transfers_total=1, device_actions_by_closure=0)
        for key, name in (('source_snapshot', 'source-snapshot.json'), ('raw_captures', 'raw-index.json'),
                          ('canonical_timeline', 'timeline.json')):
            closure[key] = records.publish(folder/name, {'fixture': name})
        return folder/'closed.json', closure

    def mainline_fixture_task(self):
        # Lifecycle metadata only. The fixture has no capability, candidate
        # qualification, or V13 review.
        image = {'profile': profile.PROFILE, 'schema': IMAGE_V2, 'ufs_link': True,
                 'namespace': profile.NAMESPACE, 'version': profile.VERSION}
        return dict(schema=profile.TASK_SCHEMA, N=image, E=None, operations=[profile.OPERATION],
            seconds=profile.SECONDS, operation_budget=1, recovery_mode='attended',
            target={'fixture': 'target'}, A={'fixture': 'rollback'}, review={'fixture': 'record join'})

    def test_open_v13_grant_and_unclosed_operation_hold_until_task_closes(self):
        task = self.mainline_fixture_task()
        folder = self.private/'analysis/ml053-v13-fixture/task'
        path, closure = self.comparison_operation(folder, task, profile.OPERATION)
        unrelated = self.private/'unrelated/task'
        unrelated.mkdir(parents=True)
        records.publish(unrelated/'task.json', {'N': None})
        records.publish(unrelated/'grant.json', {'fixture': True})
        with self.assertRaises(ValueError) as held:
            cutover.require_mainline_quiescence(self.root, {})
        for reason in ('ml053-v13-fixture/task/grant.json: open grant',
                       'ml053-v13-fixture/task/operation-0001: unclosed operation'):
            self.assertIn(reason, str(held.exception))
        records.publish(path, closure)
        cutover.require_mainline_quiescence(self.root, {})

    def test_staged_mainline_approval_holds_until_original_dispatch_closes(self):
        task = self.mainline_fixture_task()
        # This one uses the original RAM profile to cover non-UFS admission.
        task['N'].update(schema='s22plus-mainline-image-v1', ufs_link=False)
        prev, closure = self.comparison_operation(self.private/'previous/task', task, profile.OPERATION)
        preceding_closed = records.publish(prev, closure)
        base = self.private/'outputs/s22plus-ordinary-fixture-h0-20261122-1'
        folder = base/'task-1'
        folder.mkdir(parents=True)
        task_pin = records.publish(folder/'task.json', task)
        proposal = records.publish(folder/'proposal.json',
            dict(task=task_pin, approval=approval_text(task, task_pin), grants_device_authority=False))
        records.publish(base/'connector-preparation.json', dict(
            schema='s22plus-mainline-connector-preparation-v1', status='PREPARED_H0_NOT_RUN_APPROVAL',
            task=task_pin, proposal=proposal, review=task['review'], preceding_closed=preceding_closed))
        entry = self.root/ENTRY
        entry.parent.mkdir(parents=True)
        shutil.copyfile(ROOT/ENTRY, entry)
        approval = records.publish(base/'operator-approval.json', dict(
            task=task_pin, entry=records.pin(entry), preceding_closed=preceding_closed,
            selected_returned_approval=approval_text(task, task_pin),
            actual_user_text='synthetic lifecycle fixture', attended=True))
        with self.assertRaisesRegex(ValueError, 'ordinary-fixture.*staged unconsumed approval'):
            cutover.require_mainline_quiescence(self.root, {})
        dispatch = base/cutover.DISPATCH
        dispatch.mkdir()
        records.publish(dispatch/'intent.json', dict(task=task_pin, approval=approval))
        with self.assertRaisesRegex(ValueError, 'ordinary-fixture.*unclosed dispatch'):
            cutover.require_mainline_quiescence(self.root, {})

        legacy = unittest.mock.patch.object(cutover.Controller, 'bundle',
                                            side_effect=ValueError('earlier approval format'))
        with legacy:  # an unverifiable approval on an unclosed task still holds
            with self.assertRaisesRegex(ValueError, 'ordinary-fixture.*cannot verify approval'):
                cutover.require_mainline_quiescence(self.root, {})

        # Publish an exact closed operation for that same task and dispatch.
        closed, close_value = self.comparison_operation(folder, task, profile.OPERATION)
        records.publish(closed, close_value)
        cutover.require_mainline_quiescence(self.root, {})
        with legacy:  # earlier format: accepted only because the task closed and the owner closed dispatch
            cutover.require_mainline_quiescence(self.root, {})

    def test_historical_closure_schemas_are_accepted_with_their_own_raw_index(self):
        cases = (('s22plus-comparison-task-closed-v2', 'raw-index-v2.json'),
                 ('s22plus-mainline-task-closed-v1', 'raw-capture-index.json'))
        for number, (schema, index) in enumerate(cases):
            folder = self.private/f'outputs/historical-{number}/task-1'
            path, closure = self.comparison_operation(folder, self.mainline_fixture_task(), profile.OPERATION)
            wrong = dict(closure, schema=schema)  # still pins raw-index.json
            records.publish(path, wrong)
            with self.assertRaisesRegex(ValueError, f'historical-{number}/task-1/operation-0001: unclosed operation'):
                cutover.require_mainline_quiescence(self.root, {})
            path.unlink()
            value = dict(closure, schema=schema, raw_captures=records.publish(folder/index, {'fixture': index}))
            if schema == 's22plus-mainline-task-closed-v1':  # predates device_actions_by_closure
                del value['device_actions_by_closure']
                value['f1_owner_absent'] = True
            records.publish(path, value)
        cutover.require_mainline_quiescence(self.root, {})
        folder = self.private/'outputs/early-no-owner-proof/task-1'
        path, closure = self.comparison_operation(folder, self.mainline_fixture_task(), profile.OPERATION)
        value = dict(closure, schema='s22plus-mainline-task-closed-v1',
                     raw_captures=records.publish(folder/'raw-capture-index.json', {'fixture': 1}))
        del value['device_actions_by_closure']  # and no f1_owner_absent: still held
        records.publish(path, value)
        with self.assertRaisesRegex(ValueError, 'early-no-owner-proof.*does not bind its healthy original-A'):
            cutover.require_mainline_quiescence(self.root, {})
        path.unlink()
        outside = records.publish(self.private/'elsewhere-timeline.json', {'fixture': 'outside'})
        records.publish(path, dict(value, f1_owner_absent=True, canonical_timeline=outside))
        with self.assertRaisesRegex(ValueError, 'early-no-owner-proof.*canonical_timeline is outside its run folder'):
            cutover.require_mainline_quiescence(self.root, {})
        path.unlink()
        records.publish(path, dict(value, f1_owner_absent=True))
        cutover.require_mainline_quiescence(self.root, {})
        folder = self.private/'outputs/unknown-schema/task-1'
        path, closure = self.comparison_operation(folder, self.mainline_fixture_task(), profile.OPERATION)
        records.publish(path, dict(closure, schema='s22plus-comparison-task-closed-v9'))
        with self.assertRaisesRegex(ValueError, 'unknown-schema.*does not bind its healthy original-A'):
            cutover.require_mainline_quiescence(self.root, {})

    def orphan(self, folder, grant_path, *, bound=False):
        folder.mkdir(parents=True)
        grant_path.parent.mkdir(parents=True, exist_ok=True)
        grant = records.publish(grant_path, dict(schema=records.SCHEMA, directory=str(grant_path.parent),
                                                 **({'task': {'fixture': 'task'}} if bound else {})))
        records.publish(folder/'operation.json', dict(schema=records.SCHEMA, operation='mainline-ram',
            grant=grant, **({'task': {'fixture': 'task'}} if bound else {})))

    def test_nested_fixture_repositories_are_not_operations_of_this_checkout(self):
        nested = self.private/'analysis/scm-session/trial/bound/tmpabc/workspace/private'
        self.orphan(nested/'task/operation-0001', nested/'task/grant.json')
        cutover.require_mainline_quiescence(self.root, {})
        # same nesting, but the grant points into the operating checkout: still held
        self.orphan(nested/'other/operation-0001', self.private/'outputs/real/task-1/grant.json')
        with self.assertRaisesRegex(ValueError, 'other/operation-0001: mainline operation lacks task.json'):
            cutover.require_mainline_quiescence(self.root, {})
        shutil.rmtree(nested/'other')
        # a production-shaped operation (task-bound) in a nested layout whose task.json is missing: held
        self.orphan(nested/'prod/operation-0001', nested/'prod/grant.json', bound=True)
        with self.assertRaisesRegex(ValueError, 'prod/operation-0001: mainline operation lacks task.json'):
            cutover.require_mainline_quiescence(self.root, {})
        shutil.rmtree(nested/'prod')
        # an orphan outside any nested root: still held
        self.orphan(self.private/'outputs/moved/task-1/operation-0001', self.private/'outputs/moved/task-1/grant.json')
        with self.assertRaisesRegex(ValueError, 'moved/task-1/operation-0001: mainline operation lacks task.json'):
            cutover.require_mainline_quiescence(self.root, {})

    def test_healthy_direct_cli_terminal_still_requires_joined_task_closure(self):
        path, closure = self.closed_operation()
        with self.assertRaisesRegex(ValueError, 'requires closed.json'):
            cutover.require_task_closures(self.root)
        records.publish(path, dict(closure, operation=closure['task']))
        with self.assertRaisesRegex(ValueError, 'closure does not bind'):
            cutover.require_task_closures(self.root)
        path.unlink()
        records.publish(path, closure)
        self.assertEqual(cutover.require_task_closures(self.root), 1)

    def test_prepared_or_proved_unused_operation_has_no_original_a_close(self):
        path, closure = self.closed_operation()
        directory = Path(closure['operation']['path']).parent
        (directory/'terminal.json').unlink()
        (directory/'journal/0000.json').unlink()
        self.assertEqual(cutover.require_task_closures(self.root), 0)
        records.publish(directory/'consumed.json', {'fixture': True})
        with self.assertRaises(FileNotFoundError):
            cutover.require_task_closures(self.root)
        records.publish(directory/'unused.json', dict(
            schema=records.SCHEMA, operation_sha256=closure['operation']['sha256'],
            journal_rows=0, journal_tail=None))
        self.assertEqual(cutover.require_task_closures(self.root), 0)
        self.assertFalse(path.exists())

    def test_old_review_must_still_verify(self):
        self.closed_operation()
        (self.root/'source.py').write_text('# changed\n')
        with self.assertRaisesRegex(ValueError, 'original timing-v3 review source differs'):
            cutover.require_task_closures(self.root)

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.root),
            '-c', 'user.name=Cue fixture', '-c', 'user.email=fixture@example.invalid',
            '-c', 'commit.gpgsign=false', *args]).decode().strip()

    def init_operating_base(self):
        selector = json.loads((ROOT/cutover.SELECTOR).read_bytes())
        selected = Path(selector['review']['path'])
        self.gateway = cutover.BINDINGS/selected.name
        deployment = selected.parents[len(self.gateway.parts)-1]
        self.reviews = {}
        for path in (self.gateway, cutover.NEW_LOADER, cutover.SCM):
            review = json.loads((ROOT/path).read_bytes())
            for row in review['sources'] + review.get('worker_sources', []):
                name = Path(row['path'])
                rel = name.relative_to(deployment) if name.is_absolute() else name
                target = self.root/rel
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT/rel, target)
                if name.is_absolute():
                    row['path'] = str(target)
            self.reviews[path] = review
        self.git('init', '-q')
        self.git('add', '--all')
        self.git('commit', '-qm', 'fixture operating base')
        return self.git('rev-parse', 'HEAD')

    def proposed_tree(self, *, pending=False, missing_schema=False, omit_source=False,
                      loader_pending=False, refuse_recovery=False):
        (self.root/cutover.BINDINGS).mkdir(parents=True, exist_ok=True)
        task_file = self.root/'workspace/public/src/scripts/revalidation/s22plus_mainline_task_v1.py'
        text = task_file.read_text()
        if refuse_recovery:
            signature = 'def capability(root,*,recovery=False,selected=profile,image=None,ordinary_cue=False):\n'
            self.assertIn(signature, text)
            text = text.replace(signature, signature + "    require(not recovery, 'fixture refuses loader recovery')\n")
        task_file.write_text(text+'\n# reviewed fixture change\n')
        for path, original in self.reviews.items():
            verdict = 'PENDING_INDEPENDENT_REVIEW' if pending or (
                loader_pending and path == cutover.NEW_LOADER) else 'PASS_GO'
            review = dict(original, verdict=verdict, reviewer='Synthetic H0 fixture')
            review['sources'] = [dict(records.pin(self.root/row['path']), path=row['path'])
                                 for row in original['sources']]
            if omit_source and path == self.gateway:
                # Keep the stable worker and backend pins the worker checks.
                # An incomplete runtime closure still passed the old check.
                review['sources'] = [row for row in review['sources']
                                     if not row['path'].endswith('/s22plus_debian_handoff_profile_v1.py')]
            (self.root/path).write_bytes(records.canonical(review))
        selector = {'review': records.pin(self.root/self.gateway)}
        if not missing_schema:
            selector['schema'] = 's22plus-approved-terminal-current-review-v1'
        (self.root/cutover.SELECTOR).write_bytes(records.canonical(selector))
        self.git('add', '--', str(cutover.BINDINGS), str(task_file.relative_to(self.root)))
        tree = self.git('write-tree')
        self.git('reset', '--hard', 'HEAD')
        return tree

    def test_only_one_production_accepted_adoption_commit_can_follow_operating_head(self):
        base = self.init_operating_base()
        pending_tree = self.proposed_tree(pending=True)
        pending = self.git('commit-tree', pending_tree, '-p', base, '-m', 'pending')
        approved_tree = self.proposed_tree()
        ordinary_merge = self.git('commit-tree', approved_tree, '-p', base, '-p', pending, '-m', 'merge')
        after_pending = self.git('commit-tree', approved_tree, '-p', pending, '-m', 'approve')
        squash = self.git('commit-tree', approved_tree, '-p', base, '-m', 'squash adoption')
        for candidate in (ordinary_merge, after_pending):
            with self.assertRaisesRegex(ValueError, 'single squash commit'):
                cutover.require_adoption_commit(self.root, candidate)
        with self.assertRaisesRegex(ValueError, 'backend review is not PASS_GO'):
            cutover.require_adoption_commit(self.root, pending)
        self.assertEqual(cutover.require_adoption_commit(self.root, squash), squash)

    def test_production_rejects_review_sets_the_partial_check_accepted(self):
        base = self.init_operating_base()
        for options, expected in (({'missing_schema': True}, 'review selector differs'),
                                  ({'omit_source': True}, 'backend review source closure differs'),
                                  ({'loader_pending': True}, 'mainline independent review is not PASS_GO'),
                                  ({'refuse_recovery': True}, 'fixture refuses loader recovery')):
            with self.subTest(options=options):
                tree = self.proposed_tree(**options)
                squash = self.git('commit-tree', tree, '-p', base, '-m', 'invalid proposed squash')
                with self.assertRaisesRegex(ValueError, expected):
                    cutover.require_adoption_commit(self.root, squash)

    def test_newly_pinned_unchanged_blob_requires_clean_operating_bytes(self):
        base = self.init_operating_base()
        tree = self.proposed_tree()
        squash = self.git('commit-tree', tree, '-p', base, '-m', 'squash adoption')
        rel = Path('workspace/public/src/scripts/revalidation/s22plus_debian_handoff_profile_v1.py')
        self.assertEqual(self.git('diff', '--name-only', base, squash, '--', str(rel)), '')
        path = self.root/rel
        edited = path.read_bytes()+b'\n# uncommitted fixture edit\n'
        path.write_bytes(edited)
        with self.assertRaisesRegex(ValueError, 'operating source differs.*s22plus_debian_handoff_profile'):
            cutover.require_adoption_commit(self.root, squash)
        self.assertEqual(path.read_bytes(), edited)
        self.assertEqual(self.git('rev-parse', 'HEAD'), base)

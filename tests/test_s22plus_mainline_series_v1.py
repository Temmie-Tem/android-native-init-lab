"""One returned approval for a fixed series of attended mainline steps (H0 fixtures only)."""
from pathlib import Path
import hashlib
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'workspace/public/src/scripts/revalidation'))
import s22plus_mainline_series_v1 as series  # noqa: E402
import s22plus_mainline_ufs_android_block_v1 as block  # noqa: E402
from s22plus_native_records_v3 import pin, publish, read, verify  # noqa: E402


class SeriesTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name).resolve()
        self.outputs = self.root / 'workspace/private/outputs'; self.outputs.mkdir(parents=True)
        # A fixture image is "V17 qualified" when it says so; the real check reads its capability.
        patcher = mock.patch.object(series, 'qualified', side_effect=lambda p: (lambda v: v if v.get('v17') else None)(
            read(verify(p))))
        patcher.start(); self.addCleanup(patcher.stop)
        self.image = self.make_image(1)
        self.image2 = self.make_image(2)
        self.first = publish(self.outputs / 'closed-0.json', dict(terminal_state='ANDROID_CLOSED_HEALTHY'))
        steps = [dict(kind='mainline', image=self.image), dict(kind='android-block', of_step=0),
                 dict(kind='mainline', image=self.image2)]
        self.base = self.outputs / 's22plus-ufs-write-series-h0-20261128-1'
        self.series = series.create(self.root, self.base, steps, seconds=1800, first_preceding_closed=self.first)
        self.text = series.approval_text(read(self.base / 'series.json'), self.series)

    def make_image(self, marker, *, v17=True, candidate=None, ap=None):
        return publish(self.outputs / f'image-{marker}.json', dict(profile='mainline-ram-v1', marker=marker, v17=v17,
                       candidate=dict(sha256=candidate or f'c{marker}'), ap=dict(sha256=ap or f'a{marker}')))

    def approve(self, text=None, **extra):
        publish(self.base / 'operator-approval.json', dict(dict(schema=series.APPROVAL_SCHEMA, series=self.series,
                approval=self.text, actual_user_text=text or self.text, attended=True), **extra))

    def task(self, image=None):
        return dict(N=read(Path((image or self.image)['path'])), seconds=1800)

    def closed_path(self, name):
        return self.outputs / name / 'closed.json'

    def closed_mainline(self, name, subject, outcome='WRITTEN', status='PASS_MAINLINE_UFS_LINK', operation=None):
        """A task directory as the close script leaves it: grant, operation, terminal, final health."""
        folder = self.outputs / name; op = folder / 'operation-0001'
        op.mkdir(parents=True, exist_ok=True)
        for leftover in (folder / 'grant.json', op / 'operation.json', op / 'health.json', op / 'android-final.json',
                         op / 'terminal.json', folder / 'closed.json'):
            leftover.unlink(missing_ok=True)
        grant = publish(folder / 'grant.json', dict(task=subject))
        operation_pin = publish(op / 'operation.json', dict(fixture=True))
        health = publish(op / 'health.json', dict(boot_id_sha256='b' * 64))
        final = publish(op / 'android-final.json', dict(action={}, health=health))
        terminal = publish(op / 'terminal.json', dict(grant=grant, terminal_state='ANDROID_CLOSED_HEALTHY',
                           research_closed=True, terminal_result=final, mainline=dict(ufs_evidence=dict(
                           result=dict(storage=dict(write=dict(outcome=outcome)))))))
        return publish(self.closed_path(name), dict(terminal_state='ANDROID_CLOSED_HEALTHY', task=subject,
                       grant=grant, operation=operation or operation_pin, scientific_status=status,
                       current_android_terminal=terminal))

    def block_result(self, status, *, step=1, series_pin=None):
        (self.base / 'block-1').mkdir(exist_ok=True)
        return publish(self.base / 'block-1/terminal.json', dict(terminal_state='ANDROID_CLOSED_HEALTHY',
                       block=dict(status=status), series=series_pin or self.series, step=step))

    def claim_block(self):
        series.claim(self.root, self.series, 1, subject=dict(output=str(self.base / 'block-1')),
                     closed_path=self.base / 'block-1/terminal.json')

    def test_approval_text_names_the_series_digest_steps_and_time(self):
        self.assertEqual(self.text, f"APPROVE S22PLUS MAINLINE SERIES V1 {self.series['sha256']} 3steps 1800s attended")

    def test_no_step_without_the_exact_returned_series_approval(self):
        with self.assertRaises((FileNotFoundError, ValueError)):
            series.bind_step(self.root, self.series, 0, kind='mainline', task=self.task(),
                             task_pin={'p': 0}, preceding_closed=self.first)
        self.approve(text=self.text + ' please')
        with self.assertRaisesRegex(ValueError, 'series approval'):
            series.bind_step(self.root, self.series, 0, kind='mainline', task=self.task(),
                             task_pin={'p': 0}, preceding_closed=self.first)

    def test_first_step_binds_its_image_and_preceding_closure(self):
        self.approve()
        series.bind_step(self.root, self.series, 0, kind='mainline', task=self.task(), task_pin={'p': 0},
                         preceding_closed=self.first)
        for kwargs, message in ((dict(task=self.task(self.image2), preceding_closed=self.first), 'differs from its series step'),
                                (dict(task=self.task(), preceding_closed=self.image), 'preceding closure'),
                                (dict(task=dict(self.task(), seconds=60), preceding_closed=self.first), 'series step')):
            with self.subTest(message=message), self.assertRaisesRegex(ValueError, message):
                series.bind_step(self.root, self.series, 0, kind='mainline', task_pin={'p': 0}, **kwargs)
        with self.assertRaisesRegex(ValueError, 'step selection'):
            series.bind_step(self.root, self.series, 1, kind='mainline', task=self.task(), task_pin={'p': 0},
                             preceding_closed=self.first)

    def test_a_claimed_step_is_never_taken_by_another_subject(self):
        self.approve()
        series.claim(self.root, self.series, 0, subject={'p': 0}, closed_path=self.closed_path('a'))
        # Its own resume or recovery stays bound.
        series.bind_step(self.root, self.series, 0, kind='mainline', task=self.task(), task_pin={'p': 0},
                         preceding_closed=self.first)
        with self.assertRaisesRegex(ValueError, 'another subject'):
            series.bind_step(self.root, self.series, 0, kind='mainline', task=self.task(), task_pin={'p': 1},
                             preceding_closed=self.first)
        with self.assertRaises(OSError):
            series.claim(self.root, self.series, 0, subject={'p': 1}, closed_path=self.outputs / 'x.json')

    def test_recovery_of_a_claimed_step_survives_expiry_and_later_images(self):
        self.approve()
        series.claim(self.root, self.series, 0, subject={'p': 0}, closed_path=self.closed_path('a'))
        later = Path(self.image2['path']); later.rename(later.with_suffix('.away'))
        with mock.patch.object(series, 'clock', return_value=read(self.base / 'series.json')['expires_ns']):
            series.bind_step(self.root, self.series, 0, kind='mainline', task=self.task(), task_pin={'p': 0},
                             preceding_closed=self.first)
            later.with_suffix('.away').rename(later)
            # A new claim needs the live approved series.
            with self.assertRaisesRegex(ValueError, 'expired'):
                series.claim(self.root, self.series, 1, subject={'o': 1}, closed_path=self.outputs / 'x.json')

    def test_later_steps_need_every_earlier_step_closed_with_an_admitted_outcome(self):
        self.approve()
        with self.assertRaisesRegex(ValueError, 'earlier series step was not taken'):
            series.bind_step(self.root, self.series, 1, kind='android-block', task_pin={'o': 1})
        series.claim(self.root, self.series, 0, subject={'p': 0}, closed_path=self.closed_path('a'))
        with self.assertRaisesRegex(ValueError, 'not closed'):
            series.bind_step(self.root, self.series, 1, kind='android-block', task_pin={'o': 1})
        for outcome in ('WRITE_UNCERTAIN', 'READBACK_MISMATCH', 'FOREIGN_CONTENT'):
            with self.subTest(outcome=outcome):
                self.closed_mainline('a', {'p': 0}, outcome=outcome)
                with self.assertRaisesRegex(ValueError, 'admitted write outcome'):
                    series.bind_step(self.root, self.series, 1, kind='android-block', task_pin={'o': 1})

    def test_an_earlier_closure_must_be_its_claimed_task(self):
        self.approve()
        series.claim(self.root, self.series, 0, subject={'p': 0}, closed_path=self.closed_path('a'))
        self.closed_mainline('a', {'p': 'another task'})
        with self.assertRaisesRegex(ValueError, 'not its claimed task'):
            series.bind_step(self.root, self.series, 1, kind='android-block', task_pin={'o': 1})
        # A closure naming the task but carrying another operation's terminal.
        other = self.closed_mainline('elsewhere', {'p': 0})
        closed = read(verify(other))
        self.closed_mainline('a', {'p': 0})
        value = read(self.closed_path('a')); self.closed_path('a').unlink()
        publish(self.closed_path('a'), dict(value, current_android_terminal=closed['current_android_terminal']))
        with self.assertRaisesRegex(ValueError, 'not its claimed'):
            series.bind_step(self.root, self.series, 1, kind='android-block', task_pin={'o': 1})

    def test_a_claim_records_its_approval_and_recovery_needs_no_approval_file(self):
        self.approve()
        receipt = series.claim(self.root, self.series, 0, subject={'p': 0}, closed_path=self.closed_path('a'))
        value = read(verify(receipt))
        self.assertEqual((value['approval'], value['actual_user_text']), (self.text, self.text))
        (self.base / 'operator-approval.json').unlink()
        _, _, returned = series.bind_step(self.root, self.series, 0, kind='mainline', task=self.task(),
                                          task_pin={'p': 0}, preceding_closed=self.first)
        self.assertEqual(returned['actual_user_text'], self.text)

    def test_a_series_grant_needs_its_claim(self):
        self.approve()
        receipt = series.claim(self.root, self.series, 0, subject={'p': 0}, closed_path=self.closed_path('a'))
        series.claimed_for(self.root, receipt, {'p': 0}, self.text, self.task())
        for args, message in (((None, {'p': 0}, self.text, self.task()), 'only through its series claim'),
                              ((receipt, {'p': 1}, self.text, self.task()), 'does not name this task'),
                              ((receipt, {'p': 0}, self.text + ' x', self.task()), 'does not name this task'),
                              ((receipt, {'p': 0}, self.text, self.task(self.image2)), 'does not name this task')):
            with self.subTest(message=message), self.assertRaisesRegex(ValueError, message):
                series.claimed_for(self.root, *args)

    def test_a_claim_reestablishes_the_order(self):
        self.approve()
        # Step 2 cannot be claimed (and so opens no grant) before steps 0 and 1 closed.
        with self.assertRaisesRegex(ValueError, 'earlier series step was not taken'):
            series.claim(self.root, self.series, 2, subject={'p': 2}, closed_path=self.closed_path('c'))
        self.assertFalse(series.claim_path(self.base, 2).exists())

    def test_expiry_is_decided_once_by_the_claim_record(self):
        self.approve()
        record = read(self.base / 'series.json')
        with mock.patch.object(series, 'clock', return_value=record['expires_ns']):
            with self.assertRaisesRegex(ValueError, 'expired'):
                series.claim(self.root, self.series, 0, subject={'p': 0}, closed_path=self.closed_path('a'))
        self.assertFalse(series.claim_path(self.base, 0).exists())
        receipt = series.claim(self.root, self.series, 0, subject={'p': 0}, closed_path=self.closed_path('a'))
        # A claim made before expiry opens its grant even if the grant opens later.
        with mock.patch.object(series, 'clock', return_value=record['expires_ns'] + 1):
            series.claimed_for(self.root, receipt, {'p': 0}, self.text, self.task())
        # A claim record outside the series window never opens one.
        value = read(verify(receipt)); path = Path(receipt['path']); path.unlink()
        forged = publish(path, dict(value, claimed_ns=record['expires_ns']))
        with self.assertRaisesRegex(ValueError, 'not made inside the series'):
            series.claimed_for(self.root, forged, {'p': 0}, self.text, self.task())

    def test_final_health_belongs_to_the_claimed_operation(self):
        self.approve()
        series.claim(self.root, self.series, 0, subject={'p': 0}, closed_path=self.closed_path('a'))
        self.closed_mainline('a', {'p': 0})
        other = read(verify(self.closed_mainline('elsewhere', {'p': 0})))
        foreign = read(verify(read(verify(other['current_android_terminal']))['terminal_result']))['health']
        op = self.outputs / 'a/operation-0001'
        final = read(op / 'android-final.json'); (op / 'android-final.json').unlink()
        publish(op / 'android-final.json', dict(final, health=foreign))
        terminal = read(op / 'terminal.json'); (op / 'terminal.json').unlink()
        terminal_pin = publish(op / 'terminal.json', dict(terminal, terminal_result=pin(op / 'android-final.json')))
        value = read(self.closed_path('a')); self.closed_path('a').unlink()
        publish(self.closed_path('a'), dict(value, current_android_terminal=terminal_pin))
        with self.assertRaisesRegex(ValueError, 'final health is not its claimed operation'):
            series.bind_step(self.root, self.series, 1, kind='android-block', task_pin={'o': 1})

    def test_any_mismatch_or_foreign_closure_stops_the_lane(self):
        self.assertIsNone(series.lane_stopped(self.root))
        self.closed_mainline('run-1/task-1', {'p': 9})
        self.assertIsNone(series.lane_stopped(self.root))
        for number, outcome in enumerate(series.STOP_WRITE, 2):
            with self.subTest(outcome=outcome):
                self.closed_mainline(f'run-{number}/task-1', {'p': number}, outcome=outcome)
                self.assertEqual(series.lane_stopped(self.root), str(self.outputs / 'run-2/task-1/closed.json'))

    def test_a_series_block_read_of_other_content_stops_the_lane(self):
        for status in ('PATTERN', 'ZERO', 'NO_PROOF'):
            (self.base / 'block-1/terminal.json').unlink(missing_ok=True)
            self.block_result(status)
            self.assertIsNone(series.lane_stopped(self.root))
        (self.base / 'block-1/terminal.json').unlink()
        self.block_result('OTHER')
        self.assertEqual(series.lane_stopped(self.root), str(self.base / 'block-1/terminal.json'))
        # A read that stopped after completing still records its class.
        (self.base / 'block-1/terminal.json').unlink()
        self.assertIsNone(series.lane_stopped(self.root))
        publish(self.base / 'block-1/stopped.json', dict(error_type='SessionError', block=dict(status='OTHER')))
        self.assertEqual(series.lane_stopped(self.root), str(self.base / 'block-1/stopped.json'))

    def test_the_whole_chain_in_order(self):
        self.approve()
        series.claim(self.root, self.series, 0, subject={'p': 0}, closed_path=self.closed_path('a'))
        closed_a = self.closed_mainline('a', {'p': 0})
        series.bind_step(self.root, self.series, 1, kind='android-block', task_pin={'o': 1})
        self.claim_block()
        # The final mainline step needs the Android read to have found the pattern.
        self.block_result('ZERO')
        with self.assertRaisesRegex(ValueError, 'did not find the pattern'):
            series.bind_step(self.root, self.series, 2, kind='mainline', task=self.task(self.image2), task_pin={'p': 2},
                             preceding_closed=closed_a)

    def test_an_android_result_must_be_its_claimed_read(self):
        self.approve()
        series.claim(self.root, self.series, 0, subject={'p': 0}, closed_path=self.closed_path('a'))
        closed_a = self.closed_mainline('a', {'p': 0})
        self.claim_block()
        for kwargs in (dict(step=0), dict(series_pin={'path': 'other'})):
            with self.subTest(**kwargs):
                (self.base / 'block-1/terminal.json').unlink(missing_ok=True)
                self.block_result('PATTERN', **kwargs)
                with self.assertRaisesRegex(ValueError, 'not its claimed read'):
                    series.bind_step(self.root, self.series, 2, kind='mainline', task=self.task(self.image2),
                                     task_pin={'p': 2}, preceding_closed=closed_a)

    def test_the_final_step_follows_the_last_mainline_closure(self):
        self.approve()
        series.claim(self.root, self.series, 0, subject={'p': 0}, closed_path=self.closed_path('a'))
        closed_a = self.closed_mainline('a', {'p': 0}, outcome='ALREADY_PRESENT')
        self.claim_block()
        self.block_result('PATTERN')
        series.bind_step(self.root, self.series, 2, kind='mainline', task=self.task(self.image2), task_pin={'p': 2},
                         preceding_closed=closed_a)
        with self.assertRaisesRegex(ValueError, 'preceding closure'):
            series.bind_step(self.root, self.series, 2, kind='mainline', task=self.task(self.image2), task_pin={'p': 2},
                             preceding_closed=self.first)

    def test_expiry_and_another_host_boot_end_the_series(self):
        self.approve()
        record = read(self.base / 'series.json')
        for now in (record['expires_ns'], record['created_ns'] - 1):
            with mock.patch.object(series, 'clock', return_value=now):
                with self.assertRaisesRegex(ValueError, 'expired'):
                    series.approved(self.root, self.series)
        with mock.patch.object(series, 'host_boot', return_value='0' * 64):
            with self.assertRaisesRegex(ValueError, 'expired'):
                series.approved(self.root, self.series)

    def test_series_shape_is_closed(self):
        for number, (steps, message) in enumerate((([dict(kind='android-block', of_step=0)], 'Android block step'),
                               ([dict(kind='mainline', image=self.image), dict(kind='android-block', of_step=5)],
                                'Android block step'),
                               ([dict(kind='mainline', image=self.image)] * 5, 'series record'),
                               ([dict(kind='reboot')], 'unselected series step kind'),
                               ([dict(kind='mainline', image=self.make_image(3, v17=False))], 'not a V17'),
                               ([dict(kind='mainline', image=self.image)] * 2, 'reuse a candidate or AP'),
                               ([dict(kind='mainline', image=self.image),
                                 dict(kind='mainline', image=self.make_image(4, ap='a1'))], 'reuse a candidate or AP'))):
            with self.subTest(message=message), self.assertRaisesRegex(ValueError, message):
                series.create(self.root, self.outputs / f's22plus-x-series-h0-20261128-{number}',
                              steps, seconds=1800, first_preceding_closed=self.first)


class AndroidBlockTests(unittest.TestCase):
    def test_fixed_script(self):
        self.assertIn('skip=62305152 count=1', block.SCRIPT)
        self.assertIn('= 498442240 ]', block.SCRIPT)          # LU0 in 512-byte sectors
        self.assertIn('-le 498441216 ]', block.SCRIPT)        # every partition ends before the block
        self.assertNotIn('of=', block.SCRIPT)
        for forbidden in ('mknod', 'mount', 'insmod', ' > ', 'blockdev --setrw', 'conv='):
            self.assertNotIn(forbidden, block.SCRIPT)
        self.assertEqual(block.PATTERN_SHA256, series_pattern())

    def test_projection_classifies_exactly(self):
        for data, status in ((bytes(4096), 'ZERO'), (pattern(), 'PATTERN'), (b'x' * 4096, 'OTHER')):
            with self.subTest(status=status):
                self.assertEqual(project(b'B0\n' + data + b'END\n')['status'], status)
        for stdout in (b'B0\n' + bytes(4095) + b'END\n', bytes(4096), b'B0\n' + bytes(4096) + b'END\nX'):
            self.assertEqual(project(stdout)['status'], 'NO_PROOF')
        self.assertEqual(project(b'B0\n' + bytes(4096) + b'END\n', returncode=1)['status'], 'NO_PROOF')
        self.assertEqual(project(b'B0\n' + bytes(4096) + b'END\n', stderr=b'x')['status'], 'NO_PROOF')


class GrantPathTests(unittest.TestCase):
    """The direct mainline grant entry: a series text needs its claim; a stopped lane opens no V17 grant."""
    def setUp(self):
        import s22plus_mainline_task_v1 as task
        from contextlib import nullcontext
        self.task = task
        tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name).resolve()
        (self.root / 'workspace/private/outputs/t').mkdir(parents=True)
        self.path = self.root / 'workspace/private/outputs/t/task.json'
        # (deliberately not at outputs/<run>/task-1)
        publish(self.path, dict(N={'fixture': 1}, seconds=1800))
        for target, kwargs in ((task, dict(attribute='validate_task')),
                               (task.tasks, dict(attribute='approval_text', return_value='A')),
                               (task.registry, dict(attribute='target_session_lease', return_value=nullcontext())),
                               (task.registry, dict(attribute='require_no_f1_owner'))):
            patcher = mock.patch.object(target, **kwargs); patcher.start(); self.addCleanup(patcher.stop)

    def test_a_series_text_needs_its_claim(self):
        with self.assertRaisesRegex(ValueError, 'only through its series claim'):
            self.task.open_grant(self.root, self.path, returned_approval='A',
                                 operator_statement='APPROVE S22PLUS MAINLINE SERIES V1 x 3steps 1800s attended')

    def test_a_v17_task_lives_at_run_task_1(self):
        with mock.patch.object(self.task, 'ufs_write', return_value=True), \
                mock.patch.object(series, 'lane_stopped', return_value=None):
            with self.assertRaisesRegex(ValueError, 'outputs/<run>/task-1'):
                self.task.open_grant(self.root, self.path, returned_approval='A', operator_statement='single run')

    def test_a_stopped_lane_opens_no_v17_grant(self):
        with mock.patch.object(self.task, 'ufs_write', return_value=True), \
                mock.patch.object(series, 'lane_stopped', return_value='run-2/task-1/closed.json'):
            (self.root / 'workspace/private/outputs/run/task-1').mkdir(parents=True)
            path = publish(self.root / 'workspace/private/outputs/run/task-1/task.json', dict(N={'fixture': 1}))
            with self.assertRaisesRegex(ValueError, 'no further write run'):
                self.task.open_grant(self.root, Path(path['path']), returned_approval='A', operator_statement='single run')


class AndroidBlockBindingTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        self.out = Path(tmp.name).resolve()

    def test_the_read_runs_only_attended(self):
        with self.assertRaisesRegex(ValueError, 'attended'):
            block.read_block(self.out, {'path': 'x'}, 1, self.out / 'o', attended=False)

    def test_a_read_claimed_after_its_window_never_contacts_android(self):
        from contextlib import nullcontext
        root = self.out; outputs = root / 'workspace/private/outputs'
        base = outputs / 's22plus-x-series-h0-20261128-1'; base.mkdir(parents=True)
        cap = publish(outputs / 'cap.json', dict(fixed=dict(report_version=17)))
        task = publish(outputs / 'task.json', dict(N=dict(capability=cap), review={'r': 1}, adb={}, target={}, A={}))
        closed = publish(outputs / 'closed.json', dict(task=task, closed_boottime_ns=1_000))
        publish(base / 'step-0.json', dict(subject=task, closed=closed))
        current = dict(steps=[dict(kind='mainline'), dict(kind='android-block', of_step=0)], seconds=10)

        def claim(root_, series_pin, index, *, subject, closed_path):
            return publish(base / f'step-{index}.json', dict(claimed_ns=1_000 + 10 * 1_000_000_000))
        with mock.patch.object(block.registry, 'target_session_lease', return_value=nullcontext()), \
                mock.patch.object(block.registry, 'require_no_f1_owner'), \
                mock.patch.object(block.series, 'bind_step', return_value=(current, base, {})), \
                mock.patch.object(block.series, 'claim', side_effect=claim), \
                mock.patch.object(block.mainline, 'ufs_storage', return_value=True), \
                mock.patch.object(block.mainline, 'capability', return_value={'r': 1}), \
                mock.patch.object(block, 'closure_boot', return_value='b' * 64), \
                mock.patch.object(block, 'clock', return_value=2_000), \
                mock.patch.object(block.target_io, 'Android', side_effect=AssertionError('Android contacted')):
            with self.assertRaisesRegex(ValueError, 'consumed, not run'):
                block.read_block(root, {'path': 'x'}, 1, base / 'block-1', attended=True)
        self.assertFalse((base / 'block-1/open.json').exists())

    def test_closure_boot_is_the_v17_final_health(self):
        health = publish(self.out / 'health.json', dict(boot_id_sha256='b' * 64))
        final = publish(self.out / 'android-final.json', dict(action={}, health=health))
        terminal = publish(self.out / 'terminal.json', dict(terminal_result=final))
        self.assertEqual(block.closure_boot(dict(current_android_terminal=terminal)), 'b' * 64)

    def test_rederive_needs_the_closure_boot(self):
        task = publish(self.out / 'task.json', dict(target={}, A={}))
        for boot, ok in (('b' * 64, True), ('c' * 64, False)):
            with self.subTest(ok=ok):
                out = self.out / f'r-{ok}'
                (out / 'before').mkdir(parents=True); (out / 'after').mkdir()
                (out / 'read').mkdir(); publish(out / 'read/block.capture.json', dict(fixture=True))
                publish(out / 'open.json', dict(schema=block.SCHEMA, command_sha256=block.digest(block.SCRIPT.encode()),
                        task=task, series={'s': 1}, step=1, closure_boot_id_sha256=boot, attended=True))
                for side in ('before', 'after'):
                    publish(out / side / 'health.json', dict(captures=[], properties={}, boot_id_sha256='b' * 64))
                with mock.patch.object(block.target_io, 'health_projection', side_effect=lambda c, t, a: dict(
                        captures=[], properties={}, boot_id_sha256='b' * 64)), \
                        mock.patch.object(block, 'projection', return_value=dict(status='PATTERN')):
                    if ok:
                        self.assertEqual(block.rederive(out, read(verify(task)))['block']['status'], 'PATTERN')
                    else:
                        with self.assertRaisesRegex(ValueError, 'closure boot'):
                            block.rederive(out, read(verify(task)))


def pattern():
    return b''.join(b'S22UFS2B' + (62305152).to_bytes(4, 'little') + i.to_bytes(4, 'little') for i in range(256))


def series_pattern():
    return hashlib.sha256(pattern()).hexdigest()


def project(stdout, *, returncode=0, stderr=b''):
    handle = mock.Mock(returncode=returncode, timed_out=False, output_exceeded=False, producer_error_type=None)
    with mock.patch.object(block.raw, 'load_handle', return_value=handle), \
            mock.patch.object(block.raw, 'read_stdout', return_value=stdout), \
            mock.patch.object(block.raw, 'read_stderr', return_value=stderr), \
            mock.patch.object(block, 'verify', side_effect=lambda r: r):
        return block.projection({'path': 'x'})


if __name__ == '__main__':
    unittest.main()

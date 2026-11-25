"""MAX77705 route-timer: staging, binding, outcome, timed return and no-cue regressions."""
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'workspace/public/src/scripts/revalidation'))
sys.path.insert(0, str(ROOT / 'workspace/public/src/mainline/s22plus_canary_h0'))
import s22plus_mainline_access_v1 as access
import s22plus_mainline_auto_recovery_v1 as auto
import s22plus_mainline_profile_v1 as profile
import s22plus_mainline_max77705_route_v1 as mxr
import s22plus_mainline_max77705_route_timer_v1 as mxt
import s22plus_mainline_session_v1 as session
import s22plus_mainline_task_v1 as task
import max77705_route_h0
import max77705_route_timer_h0 as staging
import max77705_route_record as rec
from s22plus_native_records_v3 import pin, publish

SOURCE = ROOT / 'workspace/public/src/mainline/s22plus_canary_h0'
NATIVE = ROOT / 'workspace/public/src/native-init'


def produced(scenario, _cache={}):
    if 'exe' not in _cache:
        _cache['tmp'] = tempfile.TemporaryDirectory()
        _cache['exe'] = Path(_cache['tmp'].name) / 'fake'
        subprocess.run(['gcc', '-std=gnu11', '-Wall', '-Wextra', '-Werror', '-O1', '-I', str(SOURCE),
                        str(SOURCE / 'max77705_route_fake.c'), '-o', str(_cache['exe'])], check=True)
    out = subprocess.run([str(_cache['exe']), scenario], capture_output=True, text=True, check=True).stdout
    return rec.decode(bytes.fromhex(out.splitlines()[1]))


def proof(scenario, **change):
    decoded = produced(scenario)
    return dict(dict(status=profile.MXT_STATUS, runtime_schema=profile.MXT_WIRE_SCHEMA,
                     subject='max77705-route-timer', max77705_verdict=rec.verdict(decoded), max77705=decoded),
                **change)


class StagingTests(unittest.TestCase):
    def stage(self, board):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        out = Path(folder.name) / 'src'
        return out, staging.stage_sources(out, board=board)

    def test_identity_is_distinct_and_complete(self):
        for board, new, old in ((True, staging.BOARD, staging.ROUTE_BOARD), (False, staging.VM, staging.ROUTE_VM)):
            with self.subTest(board=board):
                out, schema = self.stage(board)
                self.assertEqual(schema, new[0])
                text = ''.join((out / name).read_text() for name in ('init.c', 'protocol.h', 'max77705_verify.py'))
                for value in (old[1], old[2] + 'RQ1', old[2] + 'RS1'):
                    self.assertNotIn(value, text)
                verifier = (out / 'max77705_verify.py').read_text()
                self.assertIn(new[0], verifier)
                self.assertIn(new[1], verifier)
                self.assertIn("'subject': 'max77705-route-timer'", verifier)
                self.assertNotIn("'subject': 'max77705-route'}", verifier)

    def test_timer_arms_first_and_closes_its_ipc(self):
        out, _ = self.stage(True)
        source = (out / 'init.c').read_text()
        self.assertEqual(source.count('recovery_begin()'), 1)
        self.assertEqual(source.count('close(recovery_fd); recovery_fd = -1;'), 1)
        self.assertEqual(source.count('#include "download-return.h"'), 1)
        self.assertNotIn('#ifdef CANARY_DOWNLOAD_RAM\n#include "download-return.h"', source)
        arm, begin = source.index('recovery_begin()'), source.index('G0Q_RAM_PID1_BEGIN')
        route, usb = source.index('    mx_begin();'), source.index('    int e=usb();')
        self.assertLess(arm, begin)
        self.assertLess(begin, route)
        self.assertLess(route, usb)
        # The producer itself is the reviewed Stage 2 header, unchanged.
        self.assertEqual((out / 'max77705-usb-route.h').read_bytes(), (SOURCE / 'max77705-usb-route.h').read_bytes())
        self.assertNotIn('recovery_commit', source)

    def test_stage2_staging_is_untouched(self):
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder) / 'src'
            self.assertEqual(max77705_route_h0.stage_sources(out, board=True), staging.ROUTE_BOARD[0])
            self.assertNotIn('recovery_begin', (out / 'init.c').read_text())

    def test_both_profiles_compile_strictly(self):
        compiler = 'aarch64-linux-gnu-gcc'
        if subprocess.run(['which', compiler], capture_output=True).returncode:
            self.skipTest('cross compiler unavailable')
        for board in (False, True):
            with self.subTest(board=board):
                out, _ = self.stage(board)
                (out / 'seal.h').write_text(
                    '#define CANARY_PORT 47649\n' +
                    ''.join('static const unsigned char canary_%s[32]={%s};\n' % (n, ','.join(['1'] * 32))
                            for n in ('key', 'id')) +
                    ''.join('static const char canary_%s[]="%s";\n' % kv for kv in dict(
                        device_ip='10.0.0.2', host_ip='10.0.0.1', netmask='255.255.255.0',
                        device_mac='02:00:00:00:00:01', host_mac='02:00:00:00:00:02', serial='g0q-x',
                        udc='a600000.usb').items()))
                subprocess.run([compiler, '-std=c11', '-static', '-Os', '-Wall', '-Wextra', '-Werror',
                                '-Wno-unused-function', '-Wno-unused-const-variable', '-DCANARY_DEBIAN_RAM',
                                '-DG0Q_AUTOMATIC_RECOVERY', *([] if board else ['-DCANARY_H0_VM']),
                                '-I', str(out), '-I', str(NATIVE), '-I', str(SOURCE),
                                '-I', str(staging.TIMER_INCLUDE_DIR), str(out / 'init.c'), '-o', str(out / 'obs')],
                               check=True, capture_output=True)


class RouteTimerSessionTests(unittest.TestCase):
    def setUp(self):
        self.image = {'schema': profile.MXT_SCHEMA}
        self.request = {'N': self.image, 'operation': 'mainline-ram'}
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.adapter = SimpleNamespace(directory=Path(folder.name), root=ROOT,
                                       configuration=lambda request: {'review': {'path': str(ROOT / profile.MXT_REVIEW)}})

    def terminal(self, value):
        with patch.object(access, 'rederive', return_value={'proof': value}):
            return session.terminal(self.adapter, self.request, recovered=False)

    def test_outcomes_from_producer_records(self):
        cases = {
            'pass': ('ROUTE_CONFIGURED_WITHOUT_REPLUG', 'OBSERVED_MAX77705_USB_ROUTE'),
            'nofix': ('ROUTE_CONFIGURED_AFTER_REPLUG', 'OBSERVED_MAX77705_USB_ROUTE'),
            'early_enum': ('ENUMERATED_BEFORE_WRITE', 'OBSERVED_MAX77705_USB_ROUTE'),
            'write_timeout': ('ROUTE_WRITE_FAILED', 'MAX77705_ROUTE_INCONCLUSIVE'),
            'dcp': ('SKIP_CHGTYP', 'MAX77705_ROUTE_INCONCLUSIVE'),
            'no_identity': ('NO_PROOF_IDENTITY_MISMATCH', 'MAX77705_ROUTE_INCONCLUSIVE'),
        }
        for scenario, (verdict, status) in cases.items():
            with self.subTest(scenario=scenario):
                result = self.terminal(proof(scenario))
                self.assertEqual((result['max77705_route_verdict'], result['status']), (verdict, status))
                self.assertTrue(result['authenticated_usb'] and result['mainline_pid1'])
                self.assertIs(result['physical_return_requested'], False)
                self.assertIs(result['timer_armed_implied_by_response'], True)
                self.assertNotIn('max77705_route_cue_issued', result)
                self.assertNotIn('attach_closure', result)

    def test_timed_return_facts_are_added(self):
        folder = self.adapter.directory / auto.FOLDER
        folder.mkdir()
        publish(folder / 'observation.json', dict(window={'fixture': 'window'}, status='EXACT_DOWNLOAD_OBSERVED'))
        with patch.object(auto, 'deadline', return_value=1):
            result = self.terminal(proof('pass'))
        self.assertTrue(result['automatic_recovery_attempted'])
        self.assertTrue(result['automatic_download_arrival_observed'])
        self.assertIs(result['automatic_recovery_trigger_proved'], False)
        # Missing evidence keeps the arrival fact; the route stays unproved.
        with patch.object(auto, 'deadline', return_value=1), \
                patch.object(access, 'rederive', side_effect=FileNotFoundError):
            result = session.terminal(self.adapter, self.request, recovered=True)
        self.assertEqual(result['status'], 'NO_PROOF')
        self.assertIsNone(result['max77705_route_verdict'])
        self.assertTrue(result['automatic_download_arrival_observed'])

    def automatic_fixture(self, *, bound_offset=0, step='recover-android', status='EXACT_DOWNLOAD_OBSERVED',
                          named=True):
        from s22plus_native_records_v3 import Journal
        d = self.adapter.directory
        (d / 'journal').mkdir(exist_ok=True)
        folder = d / auto.FOLDER
        folder.mkdir(exist_ok=True)
        window = publish(folder / 'window.json', dict(opened_ns=100, deadline_ns=1000, host_boot='fixture'))
        launch = dict(step=step, boottime_ns=500, arrival_deadline_ns=1000 + bound_offset)
        if named:
            launch['recovery_window'] = window
        launch = publish(d / 'launch.json', launch)
        Journal(d / 'journal').append('effect-intent', step=step, action='transfer', role='A',
                                      detail=dict(launch=launch))
        return dict(window=window, status=status)

    def test_automatic_a_is_bound_to_the_automatic_window(self):
        self.assertTrue(session.automatic_a(self.adapter, self.automatic_fixture()))

    def test_attended_fallback_a_is_not_automatic(self):
        # A physical/attended recovery A carries its own 90 s bound.
        self.assertFalse(session.automatic_a(self.adapter, self.automatic_fixture(bound_offset=90_000)))

    def test_same_deadline_without_the_window_receipt_is_not_automatic(self):
        # An attended fallback whose bound happens to equal the window deadline.
        self.assertFalse(session.automatic_a(self.adapter, self.automatic_fixture(named=False)))

    def test_gateway_does_not_pin_guest_build_sources(self):
        sys.path.insert(0, str(ROOT / 'workspace/public/src/scripts/host_tools'))
        import s22plus_approved_terminal_tasks_v1 as backend
        pinned = {str(p.relative_to(ROOT)) for p in backend.review_sources(ROOT)}
        self.assertFalse(set(profile.MXT_GUEST) & pinned)
        self.assertNotIn(profile.MXT_MODULE, pinned)

    def test_no_exact_arrival_is_not_automatic(self):
        self.assertFalse(session.automatic_a(self.adapter, self.automatic_fixture(status='DOWNLOAD_NOT_OBSERVED')))

    def test_terminal_reports_automatic_dispatch_and_uses_the_recorded_epoch(self):
        observed = self.automatic_fixture()
        publish(self.adapter.directory / auto.FOLDER / 'observation.json', observed)
        calls = []
        with patch.object(auto, 'deadline', side_effect=lambda *a, **k: calls.append(k) or 1):
            result = self.terminal(proof('pass'))
        self.assertEqual(calls, [{'historical': True}])
        self.assertIs(result['automatic_original_a_dispatched'], True)

    def test_historical_deadline_checks_the_recorded_epoch(self):
        seen = []
        with tempfile.TemporaryDirectory() as folder:
            receipt = publish(Path(folder) / 'window.json', dict(host_boot='earlier-boot', deadline_ns=7))
            with patch.object(auto, 'window', side_effect=lambda adapter, request, epoch=None:
                              seen.append(epoch) or dict(host_boot='earlier-boot', deadline_ns=7)):
                self.assertEqual(auto.deadline(None, self.request, receipt, historical=True), 7)
                self.assertEqual(auto.deadline(None, self.request, receipt), 7)
        self.assertEqual(seen, ['earlier-boot', None])

    def test_record_identities_do_not_cross(self):
        route = dict(proof('pass'), status=profile.MXR_STATUS, runtime_schema=profile.MXR_WIRE_SCHEMA,
                     subject='max77705-route')
        with self.assertRaises(ValueError):
            mxt.outcome(route)
        with self.assertRaises(ValueError):
            mxr.outcome(proof('pass'), cue_issued=False)
        for change in (dict(subject='max77705-route'), dict(status=profile.MXR_STATUS),
                       dict(runtime_schema=profile.MXR_WIRE_SCHEMA), dict(max77705_verdict='GUESSED')):
            with self.subTest(change=change), self.assertRaises(ValueError):
                mxt.outcome(proof('pass', **change))
        result = self.terminal(route)
        self.assertEqual(result['status'], 'NO_PROOF')
        self.assertIn('evidence_error', result)

    def test_every_decoder_verdict_is_mapped(self):
        import inspect
        named = set(re.findall(r"'((?:ROUTE|SKIP|ENUMERATED|EVENTS|NO_PROOF)_[A-Z_]+)'", inspect.getsource(rec.verdict)))
        self.assertEqual(sorted(named - set(mxt.TESTED + mxt.STATE + mxt.INCONCLUSIVE + mxt.NO_PROOF)), [])
        self.assertEqual((mxt.TESTED, mxt.STATE, mxt.INCONCLUSIVE, mxt.NO_PROOF),
                         (mxr.TESTED, mxr.STATE, mxr.INCONCLUSIVE, mxr.NO_PROOF))

    def test_selection_predicates(self):
        self.assertTrue(profile.max77705_route_timer_board(self.image))
        self.assertTrue(profile.timed_return(self.image))
        self.assertFalse(profile.timed_udc(self.image))
        for other in ({'schema': profile.MXR_SCHEMA}, {'schema': profile.MX_SCHEMA}, {'schema': profile.SCM_SCHEMA}):
            self.assertFalse(profile.timed_return(other))
            self.assertFalse(profile.max77705_route_timer_board(other))
        self.assertTrue(auto.selected(self.request))
        self.assertFalse(auto.selected(dict(self.request, operation='loader-android')))
        self.assertFalse(auto.selected(dict(self.request, N={'schema': profile.MXR_SCHEMA})))

    def test_no_cue_scope_exists(self):
        def adapter(review):
            return SimpleNamespace(root=ROOT, configuration=lambda request: {'review': {'path': str(ROOT / review)}})
        for review in (profile.MXT_REVIEW, profile.MXR_REVIEW, profile.MX_REVIEW, profile.SCM_CUE_REVIEW):
            self.assertFalse(profile.ordinary_cue(adapter(review), self.request))
        with self.assertRaisesRegex(ValueError, 'no cue scope'):
            task.source_paths(ROOT, image=self.image, ordinary_cue=True)
        with self.assertRaisesRegex(ValueError, 'no cue scope'):
            task.capability(ROOT, image=self.image, ordinary_cue=True)
        paths = {str(p.relative_to(ROOT)) for p in task.source_paths(ROOT, image=self.image)}
        self.assertTrue({profile.MXT_POLICY, profile.MXT_MODULE,
                         'workspace/public/src/scripts/revalidation/s22plus_mainline_auto_recovery_v1.py'} <= paths)
        self.assertFalse({profile.MXR_MODULE, profile.MX_MODULE, profile.SCM_MODULE} & paths)
        shared = {'workspace/public/src/scripts/revalidation/' + name + '.py' for name in task.REVIEW_SHARED_IMPORTS}
        self.assertTrue(shared <= paths)

    def test_rederive_checks_review_before_candidate_code(self):
        for failure in (ModuleNotFoundError, SyntaxError):
            with self.subTest(error=failure), patch.object(task, 'capability'), \
                    patch.object(access, 'rederive_base', side_effect=failure):
                with self.assertRaisesRegex(ValueError, 'route-timer code unavailable'):
                    access.rederive(self.adapter, self.request)
        with patch.object(task, 'capability', side_effect=ValueError('review differs')), \
                patch.object(access, 'rederive_base', side_effect=AssertionError('unchecked import')):
            with self.assertRaisesRegex(ValueError, 'review differs'):
                access.rederive(self.adapter, self.request)
        with patch.object(task, 'capability') as checked, \
                patch.object(access, 'rederive_base', return_value={'proof': 'fixture'}):
            self.assertEqual(access.rederive(self.adapter, self.request), {'proof': 'fixture'})
            checked.assert_called_once_with(ROOT, image=self.image, ordinary_cue=False)
            (self.adapter.directory / 'mainline-attach-cue.json').write_text('{}')
            with self.assertRaisesRegex(ValueError, 'attach cue exists'):
                access.rederive(self.adapter, self.request)

    def test_original_a_review_skips_only_candidate_code(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / profile.MXT_MODULE
            source.parent.mkdir(parents=True)
            source.write_text('# synthetic route-timer fixture\n')
            policy = root / profile.MXT_POLICY
            policy.parent.mkdir(parents=True)
            policy.write_text('Fixture policy\n')
            files = [policy, source]
            rows = [dict(pin(f), path=str(f.relative_to(root))) for f in files]
            review = root / profile.MXT_REVIEW
            review.parent.mkdir(parents=True)
            receipt = publish(review, dict(schema=profile.REVIEW_SCHEMA, scope=profile.MXT_SCOPE,
                verdict='PASS_GO', sources=rows, reviewer='H0 test fixture only', findings=[]))
            with patch.object(task, 'source_paths', return_value=files):
                self.assertEqual(task.capability(root, image=self.image), receipt)
                source.unlink()
                with self.assertRaises(OSError):
                    task.capability(root, image=self.image)
                self.assertEqual(task.capability(root, image=self.image, recovery=True), receipt)
                policy.write_text('Altered policy\n')
                with self.assertRaises(ValueError):
                    task.capability(root, image=self.image, recovery=True)

    def test_wire_and_qualification_are_pinned(self):
        with self.assertRaisesRegex(ValueError, 'route-timer decoder selection differs'):
            profile.observation_wire({'debian_ram': {'schema': profile.MXT_WIRE_SCHEMA},
                                      'max77705_decoder': {'sha256': '1' * 64}})
        with self.assertRaisesRegex(ValueError, 'unqualified MAX77705 route-timer board artifact'):
            mxt.qualification({'sha256': '1' * 64})
        with self.assertRaisesRegex(ValueError, 'unreviewed route-timer board decoder'):
            mxt._decoder(b'raise AssertionError("executed unchecked source")')

    def test_normal_return_waits_for_the_timed_download(self):
        owner = session.Coordinator.__new__(session.Coordinator)
        owner.session = SimpleNamespace(request=self.request)
        with patch.object(auto, 'attempt', return_value={'state': 'fixture'}) as attempt:
            self.assertEqual(owner.await_return(), {'state': 'fixture'})
            attempt.assert_called_once_with(owner.session)
        with patch.object(auto, 'attempt', return_value=None):
            with self.assertRaisesRegex(ValueError, 'timed Download not observed'):
                owner.await_return()
        self.assertFalse(owner.prepare_automatic_return())


if __name__ == '__main__':
    unittest.main()

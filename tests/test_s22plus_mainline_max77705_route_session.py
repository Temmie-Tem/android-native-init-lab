"""MAX77705 Stage 2 route: binding, outcome and recovery regressions on the mainline RAM session."""
from pathlib import Path
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
import s22plus_mainline_profile_v1 as profile
import s22plus_mainline_max77705_route_v1 as mxr
import s22plus_mainline_session_v1 as session
import s22plus_mainline_task_v1 as task
import max77705_route_record as rec
from s22plus_native_records_v3 import pin, publish

SOURCE = ROOT / 'workspace/public/src/mainline/s22plus_canary_h0'


def produced(scenario, _cache={}):
    if 'exe' not in _cache:
        _cache['tmp'] = tempfile.TemporaryDirectory()
        _cache['exe'] = Path(_cache['tmp'].name) / 'fake'
        subprocess.run(['gcc', '-std=gnu11', '-Wall', '-Wextra', '-Werror', '-O1', '-I', str(SOURCE),
                        str(SOURCE / 'max77705_route_fake.c'), '-o', str(_cache['exe'])], check=True)
    out = subprocess.run([str(_cache['exe']), scenario], capture_output=True, text=True, check=True).stdout
    return rec.decode(bytes.fromhex(out.splitlines()[1]))


class RouteSessionTests(unittest.TestCase):
    def setUp(self):
        self.image = {'schema': profile.MXR_SCHEMA}
        self.request = {'N': self.image, 'operation': 'mainline-ram'}

    @staticmethod
    def cue_review(request):
        return {'review': {'path': str(ROOT / profile.MXR_REVIEW)}}

    @staticmethod
    def proof(scenario):
        decoded = produced(scenario)
        return dict(status=profile.MXR_STATUS, runtime_schema=profile.MXR_WIRE_SCHEMA, subject='max77705-route',
                    max77705_verdict=rec.verdict(decoded), max77705=decoded)

    def terminal(self, proof, cue):
        closure = {'cue': cue}
        with patch.object(access, 'rederive', return_value={'proof': proof, 'attach': {'fixture': 'closure'}}), \
                patch.object(session, 'verify', lambda receipt: receipt), \
                patch.object(session, 'read', lambda receipt: closure):
            return session.terminal(None, self.request, recovered=False)

    def test_outcomes_from_producer_records(self):
        cases = {
            'pass': (False, 'ROUTE_CONFIGURED_WITHOUT_REPLUG', 'OBSERVED_MAX77705_USB_ROUTE'),
            'nofix': (True, 'ROUTE_CONFIGURED_AFTER_REPLUG', 'OBSERVED_MAX77705_USB_ROUTE'),
            'not_held': (True, 'ROUTE_WRITE_NOT_HELD', 'OBSERVED_MAX77705_USB_ROUTE'),
            'initial_usb': (True, 'SKIP_INITIAL_COM_USB', 'OBSERVED_MAX77705_USB_ROUTE'),
            'early_enum': (False, 'ENUMERATED_BEFORE_WRITE', 'OBSERVED_MAX77705_USB_ROUTE'),
            'gap_replug': (True, 'ROUTE_COVERAGE_GAP', 'MAX77705_ROUTE_INCONCLUSIVE'),
            'write_timeout': (True, 'ROUTE_WRITE_FAILED', 'MAX77705_ROUTE_INCONCLUSIVE'),
            'dcp': (True, 'SKIP_CHGTYP', 'MAX77705_ROUTE_INCONCLUSIVE'),
            'no_identity': (True, 'NO_PROOF_IDENTITY_MISMATCH', 'MAX77705_ROUTE_INCONCLUSIVE'),
        }
        for scenario, (cue, verdict, status) in cases.items():
            with self.subTest(scenario=scenario):
                result = self.terminal(self.proof(scenario), {'fixture': 'cue'} if cue else None)
                self.assertEqual((result['max77705_route_verdict'], result['status']), (verdict, status))
                self.assertEqual(result['max77705_route_cue_issued'], cue)
                self.assertTrue(result['authenticated_usb'] and result['mainline_pid1'])
                self.assertEqual(result['attach_closure'], {'fixture': 'closure'})

    def test_pass_after_an_issued_cue_is_not_cable_untouched(self):
        result = self.terminal(self.proof('pass'), {'fixture': 'cue'})
        self.assertEqual(result['max77705_route_verdict'], 'ROUTE_CONFIGURED_AFTER_CUE')
        self.assertEqual(result['max77705_route_decoder_verdict'], 'ROUTE_CONFIGURED_WITHOUT_REPLUG')
        self.assertEqual(result['status'], 'OBSERVED_MAX77705_USB_ROUTE')

    def test_every_decoder_verdict_is_mapped(self):
        import inspect
        text = inspect.getsource(rec.verdict)
        import re
        named = set(re.findall(r"'((?:ROUTE|SKIP|ENUMERATED|EVENTS|NO_PROOF)_[A-Z_]+)'", text))
        mapped = set(mxr.TESTED + mxr.STATE + mxr.INCONCLUSIVE + mxr.NO_PROOF)
        self.assertEqual(sorted(named - mapped), [])
        skips = {'SKIP_' + g.upper().replace('-', '_') for g in rec.GATE if g not in ('written', 'udc-left')}
        self.assertEqual(sorted(skips - mapped - {'SKIP_NOT_OPEN'}), [])

    def test_result_identity_and_failures_never_block_closure(self):
        good = self.proof('pass')
        for change in (dict(subject='max77705'), dict(status=profile.MX_STATUS),
                       dict(runtime_schema=profile.MX_WIRE_SCHEMA), dict(max77705_verdict='GUESSED')):
            with self.subTest(change=change), self.assertRaises(ValueError):
                mxr.outcome(dict(good, **change), cue_issued=False)
        with self.assertRaises(ValueError):
            mxr.outcome(good, cue_issued=None)
        result = self.terminal(dict(good, subject='max77705'), None)
        self.assertEqual(result['status'], 'NO_PROOF')
        self.assertIn('evidence_error', result)
        with patch.object(access, 'rederive', side_effect=FileNotFoundError):
            result = session.terminal(None, self.request, recovered=True)
        self.assertIsNone(result['max77705_route_verdict'])
        self.assertEqual(result['status'], 'NO_PROOF')
        self.assertTrue(result['original_a_return_proved'])

    def test_validate_result_expects_the_route_status(self):
        self.assertTrue(profile.max77705_route_board(self.image))
        self.assertFalse(profile.max77705_board(self.image))
        self.assertFalse(profile.scm_board(self.image))

    def test_wire_selection_is_by_runtime_schema(self):
        with self.assertRaisesRegex(ValueError, 'MAX77705 route decoder selection differs'):
            profile.observation_wire({'debian_ram': {'schema': profile.MXR_WIRE_SCHEMA},
                                      'max77705_decoder': {'sha256': '0' * 64}})

    def test_unknown_qualification_and_decoder_are_rejected(self):
        with self.assertRaisesRegex(ValueError, 'unqualified MAX77705 route board artifact'):
            mxr.qualification({'sha256': '0' * 64})
        with self.assertRaisesRegex(ValueError, 'unreviewed route board decoder'):
            mxr._decoder(b'raise AssertionError("executed unchecked source")')

    def test_optional_candidate_code_failure_uses_recoverable_error(self):
        adapter = SimpleNamespace(root=ROOT, configuration=self.cue_review)
        for failure in (ModuleNotFoundError, SyntaxError):
            with self.subTest(error=failure), patch.object(task, 'capability'), \
                    patch.object(access, 'rederive_base', side_effect=failure):
                with self.assertRaisesRegex(ValueError, 'MAX77705 observation code unavailable'):
                    access.rederive(adapter, self.request)
        with patch.object(task, 'capability', side_effect=ValueError('review differs')), \
                patch.object(access, 'rederive_base', side_effect=AssertionError('unchecked import')):
            with self.assertRaisesRegex(ValueError, 'review differs'):
                access.rederive(adapter, self.request)
        self.assertRaisesRegex(ValueError, 'requires its cue scope', access.rederive,
            SimpleNamespace(root=ROOT, configuration=lambda request: {'review': {'path': '/other'}}), self.request)

    def test_original_a_review_skips_only_candidate_code(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / profile.MXR_MODULE
            source.parent.mkdir(parents=True)
            source.write_text('# synthetic route fixture\n')
            policy = root / profile.MXR_POLICY
            policy.parent.mkdir(parents=True)
            policy.write_text('Fixture policy\n')
            files = [policy, source]
            rows = [dict(pin(f), path=str(f.relative_to(root))) for f in files]
            review = root / profile.MXR_REVIEW
            review.parent.mkdir(parents=True)
            receipt = publish(review, dict(schema=profile.REVIEW_SCHEMA, scope=profile.MXR_SCOPE,
                verdict='PASS_GO', sources=rows, reviewer='H0 test fixture only', findings=[]))
            with patch.object(task, 'source_paths', return_value=files):
                self.assertEqual(task.capability(root, image=self.image, ordinary_cue=True), receipt)
                source.unlink()
                with self.assertRaises(OSError):
                    task.capability(root, image=self.image, ordinary_cue=True)
                self.assertEqual(task.capability(root, image=self.image, recovery=True, ordinary_cue=True), receipt)
                policy.write_text('Altered policy\n')
                with self.assertRaises(ValueError):
                    task.capability(root, image=self.image, recovery=True, ordinary_cue=True)

    def test_ordinary_cue_selection(self):
        def adapter(review):
            return SimpleNamespace(root=ROOT, configuration=lambda request: {'review': {'path': str(ROOT/review)}})
        self.assertTrue(profile.ordinary_cue(adapter(profile.MXR_REVIEW), self.request))
        for review in (profile.MX_REVIEW, profile.SCM_CUE_REVIEW, profile.SCM_REVIEW, profile.REVIEW):
            self.assertFalse(profile.ordinary_cue(adapter(review), self.request))
        # the Stage 1 image never opens the route review's cue
        self.assertFalse(profile.ordinary_cue(adapter(profile.MXR_REVIEW),
                                              dict(self.request, N={'schema': profile.MX_SCHEMA})))
        for image in ({'schema': profile.MXR_SCHEMA, 'ufs_link': True},
                      {'schema': profile.MXR_SCHEMA, 'udc_observation': {}}):
            self.assertFalse(profile.ordinary_cue(adapter(profile.MXR_REVIEW), dict(self.request, N=image)))

    def test_capability_and_closure_require_the_cue_scope(self):
        with self.assertRaisesRegex(ValueError, 'only with its cue scope'):
            task.source_paths(ROOT, image=self.image)
        with self.assertRaisesRegex(ValueError, 'only with its cue scope'):
            task.capability(ROOT, image=self.image)
        paths = {str(p.relative_to(ROOT)) for p in task.source_paths(ROOT, image=self.image, ordinary_cue=True)}
        self.assertTrue({profile.MXR_POLICY, profile.MXR_MODULE} <= paths)
        self.assertFalse({profile.MX_POLICY, profile.MX_MODULE} & paths)


sys.path.insert(0, str(ROOT / 'tests'))
import test_s22plus_mainline_attach_cue_v1 as cue_tests  # noqa: E402

MXR_IMAGE = {'ap': {'fixture': 'N AP'}, 'member': {'fixture': 'boot-only member'}, 'schema': profile.MXR_SCHEMA}


class RouteCueTests(cue_tests.CueTests):
    """The real cue caller and interlock on a route image's ordinary evidence step."""

    def setUp(self):
        cue = cue_tests.cue
        original_append = cue.Journal.append
        original_publish = cue_tests.publish

        def append(journal, event, **data):
            if event == 'step-start' and data.get('step') == 'mainline-evidence':
                data['action'] = 'mainline-evidence'
            return original_append(journal, event, **data)

        def publish(path, value):
            if Path(path).name == 'operation.json' and value.get('operation') == 'mainline-ram':
                value['N'] = dict(MXR_IMAGE)
            return original_publish(path, value)
        with patch.object(cue.Journal, 'append', append), patch.object(cue_tests, 'publish', publish):
            super().setUp()
        self.stack.enter_context(patch.object(cue.Adapter, 'configuration',
            lambda adapter, request: {'review': {'path': str(adapter.root / profile.MXR_REVIEW)}}))

    def test_fixture_is_the_ordinary_route(self):
        self.assertEqual(self.request['N']['schema'], profile.MXR_SCHEMA)
        self.assertEqual(self.journal.rows()[-1]['data']['action'], 'mainline-evidence')


if __name__ == '__main__':
    unittest.main()

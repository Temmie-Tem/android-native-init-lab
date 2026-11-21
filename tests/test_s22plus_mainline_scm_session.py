"""SCM readout and recovery regressions for the dormant mainline RAM variant."""
from pathlib import Path
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'workspace/public/src/scripts/revalidation'))
import s22plus_mainline_access_v1 as access
import s22plus_mainline_profile_v1 as profile
import s22plus_mainline_scm_v1 as scm
import s22plus_mainline_session_v1 as session
import s22plus_mainline_task_v1 as task
from s22plus_native_records_v3 import pin, publish


class ScmSessionTests(unittest.TestCase):
    def setUp(self):
        self.image = {'schema': profile.SCM_SCHEMA}
        self.request = {'N': self.image, 'operation': 'mainline-ram'}

    def test_authenticated_state_and_missing_response(self):
        for state in ('bound', 'unbound', 'indeterminate'):
            proof = dict(status=profile.SCM_STATUS, runtime_schema=profile.SCM_WIRE_SCHEMA,
                         subject='scm', scm_binding=state)
            with self.subTest(state=state), patch.object(access, 'rederive', return_value={'proof': proof}):
                result = session.terminal(None, self.request, recovered=False)
                self.assertEqual(result['scm_binding'], state)
                self.assertTrue(result['authenticated_usb'])
                expected = 'SCM_OBSERVATION_INDETERMINATE' if state == 'indeterminate' else 'OBSERVED_SCM_BINDING'
                self.assertEqual(result['status'], expected)
        with patch.object(access, 'rederive', side_effect=FileNotFoundError):
            result = session.terminal(None, self.request, recovered=True)
        self.assertIsNone(result['scm_binding'])
        self.assertEqual(result['status'], 'NO_PROOF')
        self.assertFalse(result['authenticated_usb'])

    def test_optional_candidate_code_failure_uses_recoverable_error(self):
        adapter = SimpleNamespace(root=ROOT)
        for failure in (ModuleNotFoundError, SyntaxError):
            with self.subTest(error=failure), patch.object(task, 'capability'), \
                    patch.object(access, 'rederive_base', side_effect=failure):
                with self.assertRaisesRegex(ValueError, 'SCM observation code unavailable'):
                    access.rederive(adapter, self.request)
        with patch.object(task, 'capability', side_effect=ValueError('review differs')), \
                patch.object(access, 'rederive_base', side_effect=AssertionError('unchecked import')):
            with self.assertRaisesRegex(ValueError, 'review differs'):
                access.rederive(adapter, self.request)

    def test_original_a_review_skips_only_candidate_code_in_fixture(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / profile.SCM_MODULE
            source.parent.mkdir(parents=True)
            source.write_text('# synthetic SCM fixture\n')
            policy = root / profile.SCM_POLICY
            policy.parent.mkdir(parents=True)
            policy.write_text('Fixture policy\n')
            files = [policy, source]
            rows = [dict(pin(f), path=str(f.relative_to(root))) for f in files]
            review = root / profile.SCM_REVIEW
            review.parent.mkdir(parents=True)
            receipt = publish(review, dict(schema=profile.REVIEW_SCHEMA, scope=profile.SCM_SCOPE,
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

    def test_unknown_qualification_and_decoder_are_rejected(self):
        with self.assertRaisesRegex(ValueError, 'unqualified SCM board artifact'):
            scm.qualification({'sha256': '0' * 64})
        with self.assertRaisesRegex(ValueError, 'unreviewed board decoder'):
            scm._decoder(b'raise AssertionError("executed unchecked source")')

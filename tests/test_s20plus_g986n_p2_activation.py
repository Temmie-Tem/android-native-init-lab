"""Offline capability-record tests; no device process or development-file flip."""
import contextlib
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'workspace/public/src/scripts/revalidation'))
import s20plus_g986n_p2_ram_snapshot_f1 as P
E = P.engine


class P2ActivationTests(unittest.TestCase):
    @contextlib.contextmanager
    def fixture(self, *, active=True):
        with tempfile.TemporaryDirectory() as temp, contextlib.ExitStack() as stack:
            record = Path(temp) / 'activation-v1.json'
            actual = P._input_bytes
            owner = Path(P.__file__)
            source = actual(owner)
            source = source.replace(b'\nP2_F1_ACTIVE = True\n', b'\nP2_F1_ACTIVE = False\n')
            if active: source = source.replace(b'\nP2_F1_ACTIVE = False\n', b'\nP2_F1_ACTIVE = True\n')
            stack.enter_context(mock.patch.object(P, '_input_bytes', side_effect=lambda path: source if path == owner else actual(path)))
            stack.enter_context(mock.patch.object(P, 'ACTIVATION', record))
            stack.enter_context(mock.patch('subprocess.Popen', side_effect=AssertionError('device process reached')))
            identity = P.activation_identity()
            value = {'schema': P.ACTIVATION_SCHEMA, 'version': P.VERSION, 'target': P.TARGET,
                     'identity': identity, 'identity_sha256': E.digest(identity),
                     'review': {'verdict': 'PASS_GO', 'high': 0, 'medium': 0, 'low': 0}, 'at': 'fixture'}
            def publish(data):
                if record.exists(): record.chmod(0o600)
                record.write_bytes(E.canonical_bytes(data)); record.chmod(0o400)
            publish(value)
            yield record, value, publish

    def test_complete_record_and_exact_source_transition_validate(self):
        with self.fixture() as (record, value, publish):
            self.assertEqual(P._require_reviewed_activation(), value)
            self.assertNotEqual(value['identity']['owner_dormant'], value['identity']['owner_active'])
            self.assertTrue(value['identity']['scope']['fresh_exact_approval_required'])
            self.assertTrue(value['identity']['scope']['attendance_required'])

    def test_record_cannot_activate_dormant_owner_bytes(self):
        with self.fixture(active=False), self.assertRaisesRegex(P.P2F1Error, 'activation identity differs'):
            P._require_reviewed_activation()

    def test_review_scope_source_and_boolean_integer_tampering_rejected(self):
        with self.fixture() as (record, value, publish):
            for mutate in (
                lambda v: v['review'].update(high=1),
                lambda v: v['review'].update(high=False),
                lambda v: v['identity']['scope'].update(candidate_attempt_maximum=True),
                lambda v: v['identity']['scope'].update(attendance_required=False),
                lambda v: v['identity']['critical_sources'].clear(),
                lambda v: v['identity']['owner_active'].update(sha256='0'*64),
                lambda v: v.update(identity_sha256='0'*64),
            ):
                changed = copy.deepcopy(value); mutate(changed); publish(changed)
                with self.assertRaises(P.P2F1Error): P._require_reviewed_activation()

    def test_record_mode_link_and_duplicate_keys_rejected(self):
        with self.fixture() as (record, value, publish):
            record.chmod(0o600)
            with self.assertRaises(P._runtime.P0F1Error): P._require_reviewed_activation()
            publish(value)
            link = record.with_name('hardlink.json'); __import__('os').link(record, link)
            with self.assertRaises(P._runtime.P0F1Error): P._require_reviewed_activation()
            link.unlink(); record.unlink()
            replacement = record.with_name('actual.json'); replacement.write_bytes(E.canonical_bytes(value)); replacement.chmod(0o400)
            record.symlink_to(replacement)
            with self.assertRaises(P._runtime.P0F1Error): P._require_reviewed_activation()
            record.unlink(); publish(value)
            data = record.read_bytes().replace(b'{', b'{"version":"duplicate",', 1)
            record.chmod(0o600); record.write_bytes(data); record.chmod(0o400)
            with self.assertRaises(E.B0F1Error): P._require_reviewed_activation()

    def test_authority_or_runtime_header_change_rejected(self):
        with self.fixture() as (record, value, publish):
            with mock.patch.object(P, '_authority_identity', return_value={'fixture': 'changed'}), \
                    self.assertRaises(P.P2F1Error):
                P._require_reviewed_activation()
            actual = P._input_bytes
            def missing(path):
                if path == P.codec.HEADER: raise FileNotFoundError('header is runtime input')
                return actual(path)
            with mock.patch.object(P, '_input_bytes', side_effect=missing), self.assertRaises(FileNotFoundError):
                P._require_reviewed_activation()

    def test_capability_does_not_supply_a_prepared_approval(self):
        with self.fixture() as (record, value, publish):
            P._require_reviewed_activation()
            with mock.patch.object(P, 'P2_F1_ACTIVE', True):
                # The CLI cannot invent a run directory or approval from this record.
                with self.assertRaisesRegex(P.P2F1Error, '--run-dir is required'):
                    P.main(['--execute'])


if __name__ == '__main__': unittest.main()

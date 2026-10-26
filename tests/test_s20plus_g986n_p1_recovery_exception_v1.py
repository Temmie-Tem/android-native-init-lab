from pathlib import Path
import hashlib
import importlib.util
import json
from types import SimpleNamespace
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'workspace/public/src/scripts/revalidation/s20plus_g986n_p1_recovery_exception_v1.py'


def load():
    spec = importlib.util.spec_from_file_location('incident_fixture', SOURCE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class RecoveryExceptionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.i = load()
        self.i.RUN = Path(self.tmp.name)
        self.i._enabled = True
        self.endpoint = {'device': '/dev/bus/usb/001/002', 'topology_sha256': 'a'*64,
                         'usb': {'product': 'SM8250'}, 'endpoint_identity':[1,2,3,4]}
        self.prepared = {'binding_sha256': self.i.BINDING, 'binding': {'endpoint': self.endpoint}}
        self.events = []
        self.review = {'expires_unix': 9999999999}
        self.review_receipt = {'path': 'fixture-review', 'size': 1, 'sha256': 'b'*64}
        self.i.require_review = lambda: (self.review, self.review_receipt)
        self.i.HISTORY = {}
        def read(path, label):
            return json.loads(Path(path).read_text())
        def publish(path, value):
            with Path(path).open('x') as f:
                json.dump(value, f, sort_keys=True)
        def identify():
            self.events.append('identify')
            return self.endpoint
        def rollback(run, prepared, endpoint):
            self.events.append('rollback')
            self.assertTrue(self.i.transfer_allowed(run, 'rollback', self.i.BINDING))
            publish(run/'rollback-intent.json', {'endpoint': endpoint})
            self.assertTrue(self.i.arrival_permitted(run, {p.name for p in run.iterdir()}))
            return {'verdict': 'fixture-first-rollback'}
        self.e = SimpleNamespace(
            read_json=read, durable_json=publish,
            digest=lambda v: hashlib.sha256(json.dumps(v, sort_keys=True).encode()).hexdigest(),
            utc_now=lambda: 'fixture', ROLLBACK_AP_SHA256='c'*64,
            _validate_endpoint=lambda endpoint, label: None,
            same_download_session=lambda a,b: all(a.get(k)==b.get(k) for k in ('device','topology_sha256','usb')) and a['endpoint_identity'][:3]==b['endpoint_identity'][:3],
            read_prepared=lambda run, phase: self.prepared,
            require_candidate_claim=lambda *args: self.events.append('claim'),
            require_all_transfer_processes_quiescent=lambda *args: self.events.append('quiescent'),
            identify_download=identify, rollback_from_arrival=rollback,
        )
        self.i._engine = self.e
        self.i._runtime = SimpleNamespace(_require_live_transaction=lambda: {
            'entrypoint': 'resume_run', 'run_dir': str(self.i.RUN)})
        self.i._inherited_resume = lambda run: self.events.append('health-only') or {'verdict':'fixture-health'}
        publish(self.i.RUN/'prepared.json', self.prepared)
        publish(self.i.RUN/'physical-observation-miss.json', {'reason': 'original-identity-unproved'})
        self.original_miss = (self.i.RUN/'physical-observation-miss.json').read_bytes()

    def test_first_rollback_preserves_original_miss_and_uses_distinct_arrival(self):
        self.i.resume(self.i.RUN)
        self.assertEqual(self.events, ['claim', 'quiescent', 'identify', 'rollback'])
        self.assertEqual((self.i.RUN/'physical-observation-miss.json').read_bytes(), self.original_miss)
        self.assertTrue((self.i.RUN/self.i.ARRIVAL).exists())
        self.assertFalse((self.i.RUN/'physical-rollback-arrival.json').exists())

    def test_existing_rollback_intent_can_only_resume_health(self):
        self.i.resume(self.i.RUN)
        self.events.clear()
        self.i.resume(self.i.RUN)
        self.assertEqual(self.events, ['claim', 'quiescent', 'health-only'])

    def test_foreign_endpoint_stops_without_transfer_and_cannot_retry(self):
        self.e.identify_download = lambda: {**self.endpoint, 'topology_sha256':'d'*64}
        with self.assertRaisesRegex(RuntimeError, 'differs from prepared'):
            self.i.resume(self.i.RUN)
        self.assertNotIn('rollback', self.events)
        self.assertTrue((self.i.RUN/self.i.MISS).exists())
        self.e.identify_download = lambda: self.fail('identification replay')
        with self.assertRaisesRegex(RuntimeError, 'already stopped'):
            self.i.resume(self.i.RUN)

    def test_product_mismatch_stops_even_on_prepared_topology(self):
        self.e.identify_download = lambda: {**self.endpoint, 'usb': {'product':'SAMSUNG USB'}}
        with self.assertRaises(RuntimeError): self.i.resume(self.i.RUN)
        self.assertNotIn('rollback', self.events)

    def test_identification_cut_consumes_the_new_intent(self):
        self.e.identify_download = mock.Mock(side_effect=KeyboardInterrupt)
        with self.assertRaises(KeyboardInterrupt): self.i.resume(self.i.RUN)
        with self.assertRaisesRegex(RuntimeError, 'cannot repeat'): self.i.resume(self.i.RUN)
        self.assertEqual(self.e.identify_download.call_count, 1)

    def test_failure_after_arrival_before_transfer_closes_exception(self):
        self.e.rollback_from_arrival = mock.Mock(side_effect=RuntimeError('preflight rejected'))
        with self.assertRaisesRegex(RuntimeError, 'preflight'): self.i.resume(self.i.RUN)
        self.assertTrue((self.i.RUN/self.i.ARRIVAL).exists())
        self.assertTrue((self.i.RUN/self.i.MISS).exists())
        with self.assertRaisesRegex(RuntimeError, 'already stopped'): self.i.resume(self.i.RUN)
        self.assertEqual(self.e.rollback_from_arrival.call_count, 1)

    def test_uncertain_transfer_is_not_marked_as_no_effect_or_replayed(self):
        def uncertain(run, prepared, endpoint):
            self.e.durable_json(run/'rollback-intent.json', {'endpoint': endpoint})
            raise RuntimeError('transfer reporting cut')
        self.e.rollback_from_arrival = uncertain
        with self.assertRaisesRegex(RuntimeError, 'reporting cut'): self.i.resume(self.i.RUN)
        self.assertFalse((self.i.RUN/self.i.MISS).exists())
        self.events.clear();self.i.resume(self.i.RUN)
        self.assertEqual(self.events, ['claim', 'quiescent', 'health-only'])

    def test_candidate_other_run_and_other_entrypoints_are_refused(self):
        self.assertTrue(self.i.entrypoint_allowed('resume_run', self.i.RUN))
        for name in ('prepare','execute','confirm_physical_rollback','abort_pre_candidate'):
            self.assertFalse(self.i.entrypoint_allowed(name, self.i.RUN))
        self.assertFalse(self.i.entrypoint_allowed('resume_run', self.i.RUN/'other'))
        self.assertFalse(self.i.transfer_allowed(self.i.RUN,'candidate',self.i.BINDING))

    def test_historical_evidence_change_blocks_before_identification(self):
        self.i.HISTORY = {'physical-observation-miss.json':'0'*64}
        with self.assertRaisesRegex(RuntimeError, 'historical evidence changed'): self.i.resume(self.i.RUN)
        self.assertEqual(self.events, [])

    def test_expiry_prevents_first_transfer_but_not_post_intent_health(self):
        self.review['expires_unix'] = 0
        with self.assertRaisesRegex(RuntimeError, 'expired'): self.i.resume(self.i.RUN)
        self.assertNotIn('identify', self.events)
        self.review['expires_unix'] = 9999999999;self.i.resume(self.i.RUN)
        self.events.clear()
        with mock.patch.object(self.i.time, 'time', return_value=10000000000):
            self.i.resume(self.i.RUN)
        self.assertEqual(self.events, ['claim','quiescent','health-only'])

    def test_rollback_endpoint_cannot_differ_from_new_arrival(self):
        self.i.resume(self.i.RUN)
        path=self.i.RUN/'rollback-intent.json'
        path.write_text(json.dumps({'endpoint': {**self.endpoint,'device':'changed'}}))
        with self.assertRaisesRegex(RuntimeError, 'rollback endpoint differs'):
            self.i.resume(self.i.RUN)

    def test_orphan_arrival_is_not_accepted_as_provenance(self):
        self.e.durable_json(self.i.RUN/self.i.ARRIVAL, {})
        with self.assertRaisesRegex(RuntimeError, 'lacks intent'):
            self.i.arrival_permitted(self.i.RUN, {p.name for p in self.i.RUN.iterdir()})

    def test_ctime_only_change_does_not_block_post_intent_health(self):
        self.i.resume(self.i.RUN)
        path = self.i.RUN/'rollback-intent.json'
        value = json.loads(path.read_text())
        value['endpoint']['endpoint_identity'][-1] += 1
        path.write_text(json.dumps(value))
        self.events.clear();self.i.resume(self.i.RUN)
        self.assertEqual(self.events, ['claim','quiescent','health-only'])

    def test_terminal_readback_uses_inherited_validation(self):
        self.e.durable_json(self.i.RUN/'terminal.json', {'untrusted':'fixture'})
        self.i._inherited_resume = mock.Mock(side_effect=RuntimeError('terminal validation failed'))
        with self.assertRaisesRegex(RuntimeError, 'terminal validation failed'):
            self.i.resume(self.i.RUN)
        self.i._inherited_resume.assert_called_once_with(self.i.RUN)

    def test_host_check_never_identifies_or_transfers(self):
        self.i._host_check = True
        result = self.i.resume(self.i.RUN)
        self.assertEqual(result['verdict'], 'PASS_P1_RECOVERY_HOST_CLOSURE')
        self.assertEqual(self.events, ['claim','quiescent'])
        self.assertFalse(self.i.transfer_allowed(self.i.RUN,'rollback',self.i.BINDING))


if __name__ == '__main__':
    unittest.main()

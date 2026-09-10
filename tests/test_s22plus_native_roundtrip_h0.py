"""Failure/cut matrix for the dormant three-role H0 model and real writer."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import s22plus_native_roundtrip_h0 as model


def plan():
    return dict(schema=model.SCHEMA, host_only=True, target='SM-S906N/g0q/S906NKSS7FYG8',
                native=dict(ap_sha256='1'*64, member_sha256='2'*64, ap_size=4096, member_size=1024),
                android=dict(ap_sha256='3'*64, member_sha256='4'*64, ap_size=4096, member_size=1024))


def intent(role):
    return dict(kind='intent', role=role,
                artifact=plan()['android' if role == 'android-cleanup' else 'native'])


def result(role, outcome='complete'):
    return dict(kind='result', role=role, outcome=outcome, receipt_sha256='5'*64)


def health(arrival):
    return dict(kind='native-health', arrival=arrival, boot_sha256=str(arrival+5)*64,
                nonce_sha256=str(arrival+7)*64, receipt_sha256='5'*64)


def event(kind, **fields):
    return dict(kind=kind, receipt_sha256='5'*64, **fields)


def success():
    return [intent('native-install'), result('native-install'), health(1),
            event('download', source='native-1'), intent('native-restore'),
            result('native-restore'), health(2), event('download', source='native-2'),
            intent('android-cleanup'), result('android-cleanup'), event('android-health')]


class ModelTests(unittest.TestCase):
    def test_success_and_every_publication_cut_reopen(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'run'
            transcript = model.Transcript.create(path, plan())
            for index, item in enumerate(success()):
                self.assertEqual(transcript.result()['outcome'], 'H0_INCOMPLETE')
                transcript.append(item)
                transcript = model.Transcript(path)
                self.assertEqual(transcript.events()[0], success()[:index+1])
            self.assertEqual(transcript.result()['outcome'], 'H0_SIMULATED_PASS')
            self.assertFalse(transcript.result()['live_authorized'])
            with self.assertRaises(ValueError):
                transcript.append(intent('native-install'))

    def test_missing_native_result_never_allows_native_replay_but_can_model_fallback(self):
        for cut in (1, 5):
            events = success()[:cut]
            with self.assertRaises(ValueError):
                model.evaluate(plan(), events+[events[-1]])
            events += [event('failure'), event('download', source='physical'),
                       intent('android-cleanup'), result('android-cleanup'), event('android-health')]
            self.assertEqual(model.evaluate(plan(), events)['outcome'], 'H0_SIMULATED_NO_PROOF_RECOVERED')

    def test_failed_or_uncertain_native_result_cannot_progress_research(self):
        for role, prefix, arrival in (('native-install', [], 1), ('native-restore', success()[:4], 2)):
            for outcome in ('failed', 'uncertain'):
                events = prefix+[intent(role), result(role, outcome)]
                with self.assertRaises(ValueError):
                    model.evaluate(plan(), events+[health(arrival)])
                with self.assertRaises(ValueError):
                    model.evaluate(plan(), events+[intent(role)])
                recovered = events+[event('download', source='physical'), intent('android-cleanup'),
                                     result('android-cleanup'), event('android-health')]
                self.assertEqual(model.evaluate(plan(), recovered)['outcome'], 'H0_SIMULATED_NO_PROOF_RECOVERED')

    def test_failed_or_uncertain_android_transfer_never_replays_or_closes(self):
        for suffix in ([], [result('android-cleanup', 'failed')], [result('android-cleanup', 'uncertain')]):
            prefix = success()[:9]+suffix
            for extra in (intent('android-cleanup'), event('android-health')):
                with self.assertRaises(ValueError):
                    model.evaluate(plan(), prefix+[extra])

    def test_stale_boot_or_nonce_wrong_role_artifact_and_missing_fallback(self):
        for key in ('boot_sha256', 'nonce_sha256'):
            events = success(); events[6][key] = events[2][key]
            with self.assertRaisesRegex(ValueError, 'fresh'):
                model.evaluate(plan(), events)
        for ordinal in (0, 4, 8):
            events = success(); events[ordinal]['artifact']['ap_sha256'] = 'a'*64
            with self.assertRaisesRegex(ValueError, 'artifact'):
                model.evaluate(plan(), events)
        value = plan(); del value['android']
        with self.assertRaises(ValueError):
            model.evaluate(value, [])

    def test_health_failures_and_missing_download_cannot_enable_restoration(self):
        for prefix in (success()[:2], success()[:3], success()[:3]+[event('failure')]):
            with self.assertRaises(ValueError):
                model.evaluate(plan(), prefix+[intent('native-restore')])

    def test_float_artifact_size_does_not_equal_typed_integer_binding(self):
        item = intent('native-install')
        item['artifact']['ap_size'] = 4096.0
        with self.assertRaisesRegex(ValueError, 'artifact'):
            model.evaluate(plan(), [item])

    def test_actual_writer_short_write_and_post_fsync_cut(self):
        for after_write in (False, True):
            with self.subTest(after_write=after_write), tempfile.TemporaryDirectory() as folder:
                transcript = model.Transcript.create(Path(folder)/'run', plan())
                original = os.write
                def write(fd, payload):
                    if after_write:
                        return original(fd, payload)
                    return original(fd, payload[:7])
                def fsync(_fd):
                    raise OSError('injected cut after full publication')
                with mock.patch.object(os, 'write', side_effect=write):
                    with mock.patch.object(os, 'fsync', side_effect=fsync if after_write else os.fsync):
                        with self.assertRaises((OSError, model.core.F1V2Error)):
                            transcript.append(intent('native-install'))
                reopened = model.Transcript(transcript.directory)
                if after_write:
                    self.assertEqual(reopened.result()['transfer_intents'], ['native-install'])
                with self.assertRaises((ValueError, model.core.F1V2Error)):
                    reopened.append(intent('native-install'))

    def test_corrupt_chain_and_unknown_namespace_fail_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            transcript = model.Transcript.create(Path(folder)/'run', plan())
            transcript.append(intent('native-install'))
            (transcript.directory/'unexpected').write_text('x')
            with self.assertRaises(ValueError):
                transcript.result()


if __name__ == '__main__':
    unittest.main()

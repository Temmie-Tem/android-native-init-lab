"""Exercise both timed arms through the fixed raw Android observer."""
from contextlib import contextmanager
from pathlib import Path
import struct
from types import SimpleNamespace
import unittest
from unittest import mock

import test_s22plus_loader_android_v1 as harness
from test_s22plus_loader_logm_control_v1 import report
import s22plus_loader_android_access_v1 as access
import s22plus_loader_android_profile_v1 as profile
import s22plus_native_records_v3 as records
import device_action_raw_capture_v1 as raw
timing = profile.timing_codec()


class TimingTests(harness.ProofTests):
    def setUp(self):
        super().setUp()
        self.config = profile.logm_configuration('d'*64, bytes(range(32)))
        self.task['N']['logm_control'] = {'configuration': self.config, 'key': {'fixture': True}}
        self.task['adb'] = {'path': '/fixture/adb', 'size': 1, 'sha256': 'a'*64}
        self.reads = []
        self.change = None
        self.set_arm(False)

        @contextmanager
        def tool(*args, **kwargs):
            yield SimpleNamespace(path=Path('/fixture/adb'))

        def acquire(argv, directory, name, **kwargs):
            self.assertEqual(argv[:5], ['/fixture/adb', '-s', self.fixture.binding['serial'], 'shell', '-T'])
            self.assertEqual(kwargs['stdout_maximum'], 128)
            kwargs['before_spawn']()
            self.reads.append(name)
            data = self.writer if name == 'report' else self.timer
            result = raw.publish_captured_bytes(directory, name, stdout=data, stderr=b'', returncode=0)
            if name == 'timing' and self.change == 'boot':
                self.changed['boot_id'] = '87654321-1234-1234-1234-123456789abc'
            if name == 'timing' and self.change == 'usb':
                self.generation = 'new-generation'
            return result

        self._stack.enter_context(mock.patch.object(access.transport, 'pin_regular_file', side_effect=tool))
        self._stack.enter_context(mock.patch.object(access.raw, 'acquire_command', side_effect=acquire))

    def set_arm(self, enabled, status='READBACK_MATCH'):
        self.task['N']['timing_control'] = {'logm_enabled': enabled, 'report_property': timing.PROPERTY}
        self.writer = report(self.config, status=status) if enabled else bytes.fromhex(self.config['report_seed_hex'])
        timer = bytearray(timing.seed(self.config['marker']))
        struct.pack_into('>I', timer, 12, 1)
        struct.pack_into('>II5Q', timer, 48, int(enabled), 1_000_000, 10, 20, 30, 60, 70)
        self.timer = bytes(timer)

    def command(self, client, arguments, name, **kwargs):
        if name == 'features':
            kwargs['before_launch']()
            return raw.publish_captured_bytes(client.directory, name, stdout=b'shell_v2\n', stderr=b'', returncode=0)
        return super().command(client, arguments, name, **kwargs)

    def test_timing_both_arms_rederive_same_bracket_and_duration_from_raw(self):
        for enabled in (False, True):
            with self.subTest(enabled=enabled):
                self.setUp()
                self.set_arm(enabled)
                value = self.observe()
                measurement = value['timing_control']
                self.assertEqual(self.reads, ['report', 'timing'])
                self.assertEqual(measurement['status'], 'TIMING_OBSERVED')
                self.assertEqual(measurement['logm_enabled'], enabled)
                self.assertEqual(measurement['counter']['intervals_ns']['logm_branch_and_call'], 30_000)
                first = records.read(records.verify(measurement['before']))
                attempt = records.read(records.verify(first['attempt']))
                launch = records.read(records.verify(self.launch))
                self.assertEqual(measurement['host_transfer_launch_to_android_proof_start_ns'],
                                 attempt['started_ns'] - launch['boottime_ns'])
                with mock.patch.object(access.raw, 'acquire_command', side_effect=AssertionError('new IO')):
                    self.assertEqual(access.rederive(self.adapter, self.request), value)
                    result = access.before_return(self.adapter, self.request,
                                                  self.adapter.folder(profile.RETURN, create=True), lambda: None)
                    access.return_proof(self.adapter, self.request, result)

    def test_starts_a_fresh_inventory_after_the_observed_early_close(self):
        for enabled in (False, True):
            with self.subTest(enabled=enabled):
                self.setUp()
                self.set_arm(enabled)
                events = []

                def capture(client, arguments, name, **kwargs):
                    events.append(name)
                    if name not in ('wait-000-boot', 'wait-001-boot', 'wait-002-inventory'):
                        return self.command(client, arguments, name, **kwargs)
                    client.guard()
                    kwargs['before_launch']()
                    if name == 'wait-000-boot':
                        return raw.publish_captured_bytes(client.directory, name,
                            stdout=b'boot_completed=\nbootanim=running\n', stderr=b'', returncode=0)
                    if name == 'wait-001-boot':
                        self.generation = 'reattached-generation'
                        return raw.publish_captured_bytes(client.directory, name,
                            stdout=b'', stderr=b'error: closed\n', returncode=1)
                    return raw.publish_captured_bytes(client.directory, name,
                        stdout=b'List of devices attached\n', stderr=b'', returncode=0)

                with mock.patch.object(access.CandidateAndroid, 'command', new=capture), \
                        mock.patch.object(access.target.time, 'sleep') as sleep:
                    value = self.observe()
                self.assertEqual(events[:7], ['wait-000-inventory', 'wait-000-boot',
                    'wait-001-inventory', 'wait-001-boot', 'wait-002-inventory',
                    'wait-003-inventory', 'wait-003-boot'])
                self.assertEqual(sleep.call_args_list, [mock.call(1)] * 3)
                self.assertEqual(value['timing_control']['status'], 'TIMING_OBSERVED')
                self.assertEqual(access.rederive(self.adapter, self.request), value)
                proof = self.adapter.folder(profile.SELECTION) / 'proof'
                failed = raw.load_handle(proof / 'wait-001-boot.capture.json')
                self.assertEqual(raw.read_stderr(failed, maximum=128), b'error: closed\n')
                self.assertEqual(records.read(proof / 'attempt.json')['usb_before']['identity'],
                                 {'generation': 'reattached-generation'})

    def test_early_close_exception_requires_timed_arm_and_exact_empty_failure(self):
        for timed, stdout, stderr in (
                (False, b'', b'error: closed\n'),
                (True, b'partial', b'error: closed\n'),
                (True, b'', b'error: offline\n')):
            with self.subTest(timed=timed, stdout=stdout, stderr=stderr):
                self.setUp()
                if not timed:
                    self.task['N'].pop('timing_control')
                def capture(client, arguments, name, **kwargs):
                    if name != 'wait-000-boot':
                        return self.command(client, arguments, name, **kwargs)
                    kwargs['before_launch']()
                    return raw.publish_captured_bytes(client.directory, name,
                        stdout=stdout, stderr=stderr, returncode=1)
                with mock.patch.object(access.CandidateAndroid, 'command', new=capture):
                    with self.assertRaises(raw.RawCaptureError):
                        self.observe()
                folder = self.adapter.folder(profile.SELECTION)
                self.assertTrue((folder / 'proof/wait-000-boot.capture.json').exists())
                self.assertFalse((folder / 'proof/wait-001-inventory.capture.json').exists())
                self.assertFalse((folder / 'proof/complete.json').exists())

    def test_early_close_reobservation_does_not_extend_the_deadline(self):
        client = access.TimedCandidateAndroid(self.task, self.base / 'deadline', guard=lambda: None)
        now = 1_000_000_000

        def capture(client, arguments, name, **kwargs):
            if name != 'wait-000-boot':
                return self.command(client, arguments, name, **kwargs)
            kwargs['before_launch']()
            return raw.publish_captured_bytes(client.directory, name,
                stdout=b'', stderr=b'error: closed\n', returncode=1)

        def sleep(seconds):
            nonlocal now
            now += int(seconds * 1_000_000_000)

        with mock.patch.object(access.CandidateAndroid, 'command', new=capture), \
                mock.patch.object(access.target, 'clock', side_effect=lambda: now), \
                mock.patch.object(access.target.time, 'sleep', side_effect=sleep):
            with self.assertRaisesRegex(TimeoutError, 'readiness did not complete'):
                client.wait_ready(deadline_ns=now + 500_000_000)
        self.assertTrue((client.directory / 'wait-000-boot.capture.json').exists())
        self.assertFalse((client.directory / 'wait-001-inventory.capture.json').exists())

    def test_timing_valid_negative_diagnostics_allow_healthy_return(self):
        for enabled in (False, True):
            with self.subTest(enabled=enabled):
                self.setUp()
                self.set_arm(enabled)
                self.timer = timing.seed(self.config['marker'])
                self.assertEqual(self.observe()['timing_control']['status'], 'TIMING_UNAVAILABLE')
        self.setUp()
        self.set_arm(True, status='SKIP_MAGIC')
        value = self.observe()
        self.assertEqual(value['status'], 'PASS_LOADER_FYG8_ANDROID')
        self.assertEqual(value['timing_control']['status'], 'TIMING_WITHOUT_VALID_LOGM_WRITE')

    def test_timing_rejects_changed_identity_and_mismatched_arm(self):
        for change in ('boot', 'usb', 'wrong-mode', 'off-writer-changed'):
            with self.subTest(change=change):
                self.setUp()
                self.change = change
                if change == 'wrong-mode':
                    self.set_arm(True)
                    self.task['N']['timing_control']['logm_enabled'] = False
                    self.writer = bytes.fromhex(self.config['report_seed_hex'])
                elif change == 'off-writer-changed':
                    self.writer = report(self.config)
                with self.assertRaises(ValueError):
                    self.observe()
                folder = self.adapter.folder(profile.SELECTION)
                self.assertTrue((folder/'timing/timing.capture.json').is_file())
                self.assertFalse((folder/'result.json').exists())


for name in dir(harness.ProofTests):
    if name.startswith('test_') and name not in TimingTests.__dict__:
        setattr(TimingTests, name, None)


if __name__ == '__main__':
    unittest.main()

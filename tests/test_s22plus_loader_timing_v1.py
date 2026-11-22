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
from mainline.s22plus_loader_android_h0 import timing


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
                self.assertEqual(measurement['host_transfer_launch_to_android_ready_ns'],
                                 attempt['started_ns'] - launch['boottime_ns'])
                with mock.patch.object(access.raw, 'acquire_command', side_effect=AssertionError('new IO')):
                    self.assertEqual(access.rederive(self.adapter, self.request), value)
                    result = access.before_return(self.adapter, self.request,
                                                  self.adapter.folder(profile.RETURN, create=True), lambda: None)
                    access.return_proof(self.adapter, self.request, result)

    def test_timing_valid_negative_diagnostics_allow_healthy_return(self):
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

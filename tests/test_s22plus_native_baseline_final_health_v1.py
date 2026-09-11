"""Final-only Android recovery through the real owner and raw ADB consumers."""
import copy
from pathlib import Path
import unittest
from unittest import mock

import test_s22plus_native_baseline_owner_v1 as support
from test_s22plus_native_baseline_owner_v1 import live, owner


class FinalHealthTests(unittest.TestCase):
    running = support.OwnerTests.running
    exercise_native = support.OwnerTests.exercise_native
    fixture = support.OwnerTests.fixture
    grant = support.OwnerTests.grant
    execute = support.OwnerTests.execute
    setUpClass = classmethod(support.OwnerTests.setUpClass.__func__)

    def parked(self):
        fixture = self.fixture(fault='bootstrap-first-health')
        grant = self.grant(fixture)
        with mock.patch.object(owner, 'collect_android_final_health', side_effect=KeyboardInterrupt('health cut')), \
                self.assertRaises(KeyboardInterrupt):
            self.execute(fixture, grant)
        operation = owner.load_operation(live, fixture.prepared.root, grant.parent/'operation-01')
        self.assertTrue((operation.directory/owner.STOP).exists())
        self.assertEqual(fixture.backend.calls.count('transfer-'+owner.TRANSFER_ANDROID), 1)
        return fixture, operation

    def recover(self, fixture, operation):
        with owner.registry.target_session_lease(operation.root), \
                mock.patch.object(fixture.backend, 'transfer', side_effect=AssertionError('A replay')), \
                mock.patch.object(fixture.backend, 'wait_download', side_effect=AssertionError('new Download wait')):
            return owner.recover(live, operation, fixture.backend, attended=True)

    def test_expired_stopped_completed_A_closes_from_raw_without_baseline_read(self):
        fixture, operation = self.parked()
        retained = {p:p.read_bytes() for p in operation.directory.rglob('*') if p.is_file()}
        with mock.patch.object(owner.protocol, 'host_now_ns', return_value=operation.grant['deadline_boottime_ns']+1), \
                mock.patch.object(live.d0.AdbReadOnlyClient, 'capture', side_effect=AssertionError('pre-candidate baseline read')):
            terminal = self.recover(fixture, operation)
        self.assertEqual(terminal['state'], 'ANDROID_CLOSED')
        self.assertTrue(terminal['research_stopped'])
        self.assertFalse(terminal['recovery_required'])
        directory = Path(terminal['final_health']['path']).parent
        value = owner.android_health(live, operation, directory)
        self.assertEqual(value['schema'], owner.FINAL_HEALTH_SCHEMA)
        self.assertEqual(len(value['captures']), 7)
        self.assertGreater(len(list((directory/'raw-adb').glob('*.capture.json'))), 7)
        self.assertEqual(owner.validate_terminal(live, operation), terminal)
        for path, payload in retained.items(): self.assertEqual(path.read_bytes(), payload)
        self.assertEqual(self.recover(fixture, operation), terminal)

        # The starting Android phase still calls the original strict D0 reader.
        (operation.directory/'start-fixture').mkdir()
        with mock.patch.object(live.d0, 'collect_connected', side_effect=RuntimeError('strict start D0')), \
                self.assertRaisesRegex(RuntimeError, 'strict start D0'):
            owner.collect_android(live, operation, fixture.backend,
                mock.Mock(run_dir=operation.directory/'start-fixture'), final=False)

    def test_missing_uncertain_or_mismatched_A_prevents_even_health_acquisition(self):
        fixture, operation = self.parked()
        phase = owner.phase_prepared(live, operation, 'android-exit')
        prefix = owner.TRANSFER_ANDROID+'-attempt-01'
        for suffix in ('.result.json', '.delivery.json', '.start.json'):
            path = phase.run_dir/(prefix+suffix)
            saved = path.with_name(path.name+'.saved'); path.rename(saved)
            try:
                with mock.patch.object(live.d0, 'adb_client_for_bundle', side_effect=AssertionError('unexpected read')) as client, \
                        self.assertRaises(Exception):
                    owner.collect_android(live, operation, fixture.backend, phase, final=True)
                client.assert_not_called()
            finally: saved.rename(path)
        original = live._validate_transfer_result
        with mock.patch.object(live, '_validate_transfer_result', return_value={'classification':'odin_device_session_failure_or_unknown'}), \
                mock.patch.object(live.d0, 'adb_client_for_bundle') as client, self.assertRaises(owner.BaselineError):
            owner.collect_android(live, operation, fixture.backend, phase, final=True)
        client.assert_not_called()
        self.assertIs(live._validate_transfer_result, original)

    def test_final_properties_boot_change_fails_after_preserving_raw(self):
        fixture, operation = self.parked()
        # Change only the third property response: waiter, before, then after.
        source = fixture.backend.adb.read_text()
        counter = fixture.backend.adb.with_name('property-count')
        source = source.replace('import sys\n', 'import sys\nfrom pathlib import Path\n')
        line = next(line for line in source.splitlines() if "elif 'getprop ro.product.model'" in line)
        changed = line.replace(':print(', ':\n count_path=Path('+repr(str(counter))+')\n'
            ' count=int(count_path.read_text())+1 if count_path.exists() else 1\n'
            ' count_path.write_text(str(count))\n print(')
        changed = changed.replace(",end='')", ".replace('12345678-1234-1234-1234-123456789abc',"
            "'22345678-1234-1234-1234-123456789abc' if count==3 else '12345678-1234-1234-1234-123456789abc'),end='')")
        fixture.backend.adb.write_text(source.replace(line, changed))
        with self.assertRaisesRegex(owner.BaselineError, 'boot/properties changed'):
            self.recover(fixture, operation)
        directory = operation.directory/'android-exit'/'health-attempt-002'
        self.assertGreaterEqual(len(list((directory/'raw-adb').glob('*.capture.json'))), 7)
        self.assertFalse((directory/'result.json').exists())
        self.assertFalse((operation.directory/'terminal.json').exists())
        self.assertEqual(fixture.backend.calls.count('transfer-'+owner.TRANSFER_ANDROID), 1)

    def test_reader_rejects_other_phase_USB_target_and_changed_raw(self):
        fixture, operation = self.parked()
        terminal = self.recover(fixture, operation)
        directory = Path(terminal['final_health']['path']).parent
        value = owner.read(directory/'result.json')[0]
        variants = []
        changed = copy.deepcopy(value); changed['operation']['sha256'] = '0'*64; variants.append(changed)
        changed = copy.deepcopy(value); changed['captures'].pop(); variants.append(changed)
        changed = copy.deepcopy(value); changed['captures'][0] = changed['captures'][4]; variants.append(changed)
        changed = copy.deepcopy(value); changed['usb']['final']['download_endpoint_count'] = 1; variants.append(changed)
        changed = copy.deepcopy(value); changed['health']['boot_sha256'] = '0'*64; variants.append(changed)
        for changed in variants:
            with self.subTest(changed=changed.keys()), self.assertRaises(Exception):
                owner.validate_android_final_health(live, operation, directory, changed)
        with self.assertRaises(owner.BaselineError):
            owner.validate_android_final_health(live, operation, operation.directory/'android-start'/'health', value)
        raw = live.d0.raw_capture.load_handle(Path(value['captures'][6]['path'])).stdout_path
        raw.chmod(0o600); raw.write_bytes(raw.read_bytes()+b'corruption'); raw.chmod(0o400)
        with self.assertRaises(Exception): owner.validate_terminal(live, operation)


if __name__ == '__main__': unittest.main()

import contextlib
import copy
import importlib.util
import io
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

M = load('s20_marker_test', ROOT / 'workspace/public/src/scripts/revalidation/s20plus_g986n_pmsg_warm_reboot_d1.py')
R = load('s20_readiness_fixtures', ROOT / 'tests/test_s20plus_g986n_pstore_readiness_d0.py')
OLD = M.digest(R.BOOT.encode())
NEW = M.digest(b'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa')


def observation(boot=OLD):
    return {'readiness': 'METADATA_READY_RETENTION_UNPROVED', 'binding': {'serial_sha256': M.digest(b'S20SERIAL'), 'topology_sha256': M.digest(b'usb:3-2.1'), 'boot_id_sha256': boot}, 'facts': {'pmsg_node': {'major': 1, 'minor': 3}}}


def read_result(state='scanned', matches=1):
    size = 400 if state == 'scanned' else 0
    raw = M.health.EXPECTED_ROOT_STDOUT + f'S20PMSG_READ_V1;state={state};matches={matches};size={size}\n'.encode()
    return M.parse_read((0, raw, b''))


class FakeDevice:
    def __init__(self, boot=OLD, state='scanned', matches=1):
        self.boot, self.state, self.matches = boot, state, matches
        self.calls = []
        self.counts = dict(host_command_count=0, selected_target_command_count=0, inventory_command_count=0, root_command_count=0, s22plus_command_count=0, a90_command_count=0, other_target_command_count=0)

    def preflight(self, binding=None, journal=None):
        self.calls.append('health')
        return observation(self.boot)

    def source_check(self, binding, boot):
        self.calls.append('public')
        if self.boot != boot:
            raise M.MarkerError('boot drift')

    def probe(self, binding):
        self.calls.append('probe')
        raw = M.health.EXPECTED_ROOT_STDOUT + b'S20PMSG_PROBE_V1;returned=1;writable=1\n'
        return M.parse_probe((0, raw, b''))

    def write(self, binding):
        self.calls.append('write')
        raw = M.health.EXPECTED_ROOT_STDOUT + f'S20PMSG_WRITE_V1;returned=1;marker_sha256={M.digest(M.marker_bytes(binding))}\n'.encode()
        return M.parse_write((0, raw, b''), binding)

    def reboot(self):
        self.calls.append('reboot')
        self.boot = NEW
        return {'returned': True, 'stdout_sha256': M.digest(b''), 'stderr_sha256': M.digest(b'')}

    def wait_return(self, binding, journal):
        self.calls.append('wait')
        return observation(self.boot)

    def read_marker(self, binding, boot):
        self.calls.append('read')
        return read_result(self.state, self.matches)


class MarkerTests(unittest.TestCase):
    @contextlib.contextmanager
    def owned(self):
        with tempfile.TemporaryDirectory() as temp, mock.patch.object(M, 'repo_root', return_value=Path(temp)):
            with M.owned_trial(False) as journal:
                yield journal

    def test_happy_one_marker_reboot_read_and_cached_terminal(self):
        with self.owned() as j:
            device = FakeDevice()
            result = M.execute(j, device)
            self.assertEqual(result['verdict'], 'PROVED_PMSG_ORDINARY_REBOOT_RETENTION_HEALTHY')
            self.assertEqual([x for x in device.calls if x in ('write', 'reboot', 'read')], ['write', 'reboot', 'read'])
            later = FakeDevice()
            self.assertEqual(M.resume(j, later), result)
            self.assertEqual(later.calls, [])
            with self.assertRaises(Exception):
                M.execute(j, later)

    def test_absence_multiple_or_changed_are_no_proof(self):
        for state, count in [('unavailable', 0), ('scanned', 0), ('scanned', 2), ('changed', 0)]:
            with self.subTest(state=state, count=count), self.owned() as j:
                result = M.execute(j, FakeDevice(state=state, matches=count))
                self.assertEqual(result['verdict'], 'NO_PROOF_PMSG_TRIAL_HEALTHY')
                self.assertFalse(result['native_pid1_proved'])
                self.assertFalse(result['download_recovery_retention_proved'])

    def test_every_publication_cut_resumes_without_repeating_effect(self):
        events = ['binding', 'marker-intent', 'marker-result', 'reboot-intent', 'reboot-result', 'arrival', 'read-intent', 'read-result', 'terminal']
        for event in events:
            for after in (False, True):
                with self.subTest(event=event, after=after), self.owned() as j:
                    original = j.put
                    def cut(name, data):
                        if name == event and not after:
                            raise OSError('simulated cut')
                        original(name, data)
                        if name == event and after:
                            raise OSError('simulated cut')
                    device = FakeDevice()
                    with mock.patch.object(j, 'put', side_effect=cut), self.assertRaises(OSError):
                        M.execute(j, device)
                    # An intent-only reboot can remain on the original boot.
                    read_consumed = j.has('read-intent')
                    resumed = FakeDevice(boot=device.boot)
                    if j.has('reboot-intent') and device.boot == OLD:
                        with self.assertRaises(M.MarkerError):
                            M.resume(j, resumed)
                    else:
                        M.resume(j, resumed)
                    for effect in ('write', 'reboot'):
                        self.assertNotIn(effect, resumed.calls)
                    if read_consumed:
                        self.assertNotIn('read', resumed.calls)

    def test_reboot_uncertain_can_observe_but_cannot_claim_ordinary_route(self):
        with self.owned() as j:
            device = FakeDevice()
            original = j.put
            def cut(name, value):
                if name == 'reboot-result':
                    raise OSError('lost response')
                original(name, value)
            with mock.patch.object(j, 'put', side_effect=cut), self.assertRaises(OSError):
                M.execute(j, device)
            resumed = FakeDevice(NEW)
            result = M.resume(j, resumed)
            self.assertTrue(result['marker_match'])
            self.assertFalse(result['ordinary_reboot_attributed'])
            self.assertEqual(result['verdict'], 'NO_PROOF_PMSG_TRIAL_HEALTHY')
            self.assertNotIn('reboot', resumed.calls)

    def test_first_observed_return_boot_cannot_change(self):
        with self.owned() as j:
            device = FakeDevice()
            with mock.patch.object(device, 'read_marker', side_effect=OSError('cut')), self.assertRaises(OSError):
                M.execute(j, device)
            other = FakeDevice(M.digest(b'third-boot'))
            with self.assertRaises(M.MarkerError):
                M.resume(j, other)
            self.assertNotIn('read', other.calls)

    def test_wrong_bound_identity_rejected_before_root_read(self):
        binding = M.make_binding(observation())
        for inventory, devpath, expected in [(R.inventory().replace('S20SERIAL', 'DIFFERENT'), b'usb:3-2.1\n', 1), (R.inventory(), b'usb:3-2.2\n', 2)]:
            calls = []
            def capture(argv, timeout, maximum):
                calls.append(argv)
                return (0, inventory.encode(), b'') if argv[-1] == '-l' else (0, devpath, b'')
            with mock.patch.object(M, 'require_active'), mock.patch.object(M.ready, 'require_active'), mock.patch.object(M.ready, 'bounded_capture', side_effect=capture), mock.patch.object(M.health.base, 'tool_receipt', return_value=R.FakeBackend().tool_receipt()):
                device = M.Device()
                with self.assertRaises(M.MarkerError):
                    device.preflight(binding)
                self.assertEqual(len(calls), expected)
                self.assertFalse(any('su' in x for x in calls))

    def test_return_topology_and_ambiguity_stop_before_selected_read(self):
        binding = M.make_binding(observation())
        for inventory in (R.inventory().replace('usb:3-2.1', 'usb:3-2.2'), R.inventory().replace('S20SERIAL device', 'S20SERIAL unauthorized'), R.inventory('SECOND device usb:3-4 product:y2qksx model:SM_G986N device:y2q\n')):
            calls = []
            def capture(argv, timeout, maximum):
                calls.append(argv)
                return 0, inventory.encode(), b''
            with mock.patch.object(M, 'require_active'), mock.patch.object(M.ready, 'bounded_capture', side_effect=capture), mock.patch.object(M.health.base, 'tool_receipt', return_value=R.FakeBackend().tool_receipt()):
                device = M.Device(); device.serial = 'S20SERIAL'
                with self.assertRaises(Exception):
                    device.wait_return(binding, None)
                self.assertEqual(calls, [[M.health.EXPECTED_ADB_PATH, 'devices', '-l']])

    def test_guard_drift_before_effect_denies_dispatch(self):
        with self.owned() as j:
            device = FakeDevice()
            with mock.patch.object(j, 'validate_guard', side_effect=M.MarkerError('foreign')), self.assertRaises(M.MarkerError):
                M.execute(j, device)
            self.assertTrue(j.has('marker-intent'))
            self.assertNotIn('write', device.calls)
            self.assertNotIn('reboot', device.calls)

    def test_timeout_capture_preserved_without_raw_and_resume_health_only(self):
        with tempfile.TemporaryDirectory() as temp, mock.patch.object(M, 'repo_root', return_value=Path(temp)), mock.patch.object(M, 'require_active'), contextlib.redirect_stdout(io.StringIO()) as output:
            device = FakeDevice()
            exc = M.ready.CaptureClosed({'stop_reason': 'timeout', 'stdout_sha256': M.digest(b'private-output')})
            with mock.patch.object(device, 'write', side_effect=exc), mock.patch.object(M, 'Device', return_value=device):
                self.assertEqual(M.main(['--connected']), 1)
            path = Path(temp) / M.PRIVATE_ROOT / 'trial'
            failure = M.Journal(path).get('failure')
            self.assertEqual(failure['capture']['stop_reason'], 'timeout')
            self.assertNotIn('private-output', output.getvalue())
            resumed = FakeDevice()
            with mock.patch.object(M, 'Device', return_value=resumed):
                self.assertEqual(M.main(['--resume']), 0)
            self.assertEqual(resumed.calls, ['health', 'public'])
            self.assertFalse((Path(temp) / M.SHARED_GUARD).exists())

    def test_returned_writer_failure_digest_is_durable_before_parser(self):
        for code, stdout, stderr in [(1, b'partial-private-write', b'private-error'), (0, b'malformed-private-response', b'')]:
            with tempfile.TemporaryDirectory() as temp, mock.patch.object(M, 'repo_root', return_value=Path(temp)), mock.patch.object(M, 'require_active'), contextlib.redirect_stdout(io.StringIO()) as output, mock.patch.object(M.health.base, 'tool_receipt', return_value=R.FakeBackend().tool_receipt()), mock.patch.object(M.ready, 'bounded_capture', return_value=(code, stdout, stderr)):
                device = M.Device(); device.serial = 'S20SERIAL'
                with mock.patch.object(device, 'preflight', return_value=observation()), mock.patch.object(M, 'Device', return_value=device):
                    self.assertEqual(M.main(['--connected']), 1)
                j = M.Journal(Path(temp) / M.PRIVATE_ROOT / 'trial')
                failure = j.get('failure')
                self.assertEqual(failure['capture']['stdout_sha256'], M.digest(stdout))
                self.assertEqual(failure['capture']['stderr_sha256'], M.digest(stderr))
                self.assertNotIn(stdout.decode(), output.getvalue())
                # The write-path probe runs before any action is consumed, so a
                # device that never answers correctly costs no marker intent.
                self.assertFalse(j.has('probe-result'))
                self.assertFalse(j.has('marker-intent'))

    def test_writer_failure_after_a_passed_probe_still_consumes_the_marker_intent(self):
        probe = (0, M.health.EXPECTED_ROOT_STDOUT + b'S20PMSG_PROBE_V1;returned=1;writable=1\n', b'')
        for failure in [(1, b'partial-private-write', b'private-error'), (0, b'malformed-private-response', b'')]:
            with self.subTest(failure=failure[0]), tempfile.TemporaryDirectory() as temp, mock.patch.object(M, 'repo_root', return_value=Path(temp)), mock.patch.object(M, 'require_active'), contextlib.redirect_stdout(io.StringIO()) as output, mock.patch.object(M.health.base, 'tool_receipt', return_value=R.FakeBackend().tool_receipt()), mock.patch.object(M.ready, 'bounded_capture', side_effect=[probe, failure]):
                device = M.Device(); device.serial = 'S20SERIAL'
                with mock.patch.object(device, 'preflight', return_value=observation()), mock.patch.object(M, 'Device', return_value=device):
                    self.assertEqual(M.main(['--connected']), 1)
                j = M.Journal(Path(temp) / M.PRIVATE_ROOT / 'trial')
                self.assertTrue(j.has('probe-result'))
                self.assertTrue(j.has('marker-intent'))
                self.assertFalse(j.has('marker-result'))
                self.assertFalse(j.has('reboot-intent'))
                self.assertEqual(j.get('failure')['capture']['stdout_sha256'], M.digest(failure[1]))
                self.assertNotIn(failure[1].decode(), output.getvalue())
                self.assertFalse(j.has('reboot-intent'))

    def test_public_return_is_durable_before_failing_full_preflight(self):
        with self.owned() as j:
            fake = FakeDevice()
            with mock.patch.object(fake, 'wait_return', side_effect=OSError('pause')), self.assertRaises(OSError):
                M.execute(j, fake)
            binding = j.get('binding')
            results = iter([(0, R.inventory().encode(), b''), (0, R.snapshot(boot_id='aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'), b'')])
            with mock.patch.object(M, 'require_active'), mock.patch.object(M.health.base, 'tool_receipt', return_value=R.FakeBackend().tool_receipt()), mock.patch.object(M.ready, 'bounded_capture', side_effect=lambda *args: next(results)):
                device = M.Device(); device.serial = 'S20SERIAL'
                with mock.patch.object(device, 'preflight', side_effect=OSError('root failure')), self.assertRaises(OSError):
                    device.wait_return(binding, j)
            self.assertEqual(j.get('arrival'), {'boot_id_sha256': NEW})
            later = FakeDevice(M.digest(b'another-boot'))
            with self.assertRaises(M.MarkerError):
                M.resume(j, later)
            self.assertNotIn('read', later.calls)

    def test_resume_pins_public_return_before_root_failure(self):
        with self.owned() as j:
            fake = FakeDevice()
            with mock.patch.object(fake, 'wait_return', side_effect=OSError('pause')), self.assertRaises(OSError):
                M.execute(j, fake)
            results = iter([(0, R.inventory().encode(), b''), (0, b'usb:3-2.1\n', b''), (0, R.snapshot(boot_id='aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'), b''), (1, b'partial-root', b'failed-root')])
            with mock.patch.object(M, 'require_active'), mock.patch.object(M.ready, 'require_active'), mock.patch.object(M.health.base, 'tool_receipt', return_value=R.FakeBackend().tool_receipt()), mock.patch.object(M.ready, 'bounded_capture', side_effect=lambda *args: next(results)):
                device = M.Device()
                with self.assertRaises(Exception):
                    M.resume(j, device)
                self.assertEqual(j.get('arrival'), {'boot_id_sha256': NEW})
                self.assertEqual(device.last_capture['stdout_sha256'], M.digest(b'partial-root'))
                self.assertFalse(j.has('read-intent'))

    def test_lost_arrival_publication_never_promotes_later_boot_to_proof(self):
        with self.owned() as j:
            device = FakeDevice(); original = j.put
            def cut(name, value):
                if name == 'arrival': raise OSError('before arrival publication')
                original(name, value)
            with mock.patch.object(j, 'put', side_effect=cut), self.assertRaises(OSError):
                M.execute(j, device)
            result = M.resume(j, FakeDevice(M.digest(b'third-boot')))
            self.assertTrue(result['marker_match'])
            self.assertTrue(result['ordinary_reboot_attributed'])
            self.assertFalse(result['first_return_continuity'])
            self.assertEqual(result['verdict'], 'NO_PROOF_PMSG_TRIAL_HEALTHY')

    def test_strict_journal_and_claim_validation(self):
        with self.owned() as j:
            M.execute(j, FakeDevice())
            originals = {name: j.get(name) for name in ('marker-result', 'read-result', 'terminal')}
            for name, key, bad in [('marker-result', 'returned', 1), ('read-result', 'matches', True), ('read-result', 'stdout_sha256', '0'*64), ('terminal', 'healthy', 1), ('terminal', 'marker_match', False), ('terminal', 'native_pid1_proved', True), ('terminal', 'return_boot_sha256', 'bad')]:
                altered = copy.deepcopy(originals[name]); altered[key] = bad
                real = j.get
                with mock.patch.object(j, 'get', side_effect=lambda n: altered if n == name else real(n)), self.assertRaises(Exception):
                    M.validate_terminal(j)
            real = j.has
            with mock.patch.object(j, 'has', side_effect=lambda n: False if n == 'marker-intent' else real(n)), self.assertRaises(M.MarkerError):
                M.validate_trial(j)
        for raw in (b'{"a":1,"a":1}\n', b'{ "a":1}\n', b'{"a":NaN}\n'):
            with self.assertRaises(Exception):
                M.strict_json(raw)

    def test_dormant_zero_contact_and_no_caller_parameters(self):
        with mock.patch.object(M, 'ACTIVE', False), mock.patch.object(M, 'owned_trial', side_effect=AssertionError), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(M.main(['--connected']), 2)
            self.assertEqual(M.main(['--resume']), 2)
            with self.assertRaises(M.MarkerError):
                M.Device()
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            M.main(['--connected', '--serial', 'caller'])

    def test_foreign_guard_preserved_and_empty_trial_removed(self):
        with tempfile.TemporaryDirectory() as temp, mock.patch.object(M, 'repo_root', return_value=Path(temp)):
            guard = Path(temp) / M.SHARED_GUARD
            M.ensure_private_dirs(Path(temp), M.SHARED_GUARD.parent)
            M.publish(guard, {'foreign': True})
            with self.assertRaises(FileExistsError), M.owned_trial(False):
                self.fail('must not enter')
            self.assertEqual(M.read_node(guard), {'foreign': True})
            self.assertFalse((Path(temp) / M.PRIVATE_ROOT / 'trial').exists())

    def test_zero_effect_abort_releases_only_owned_guard_and_no_replay(self):
        with tempfile.TemporaryDirectory() as temp, mock.patch.object(M, 'repo_root', return_value=Path(temp)):
            with M.owned_trial(False) as j:
                result = M.abort_unbound(j)
            self.assertFalse((Path(temp) / M.SHARED_GUARD).exists())
            with M.owned_trial(True) as j:
                d = FakeDevice()
                self.assertEqual(M.resume(j, d), result)
                self.assertEqual(d.calls, [])
            with self.assertRaises(FileExistsError), M.owned_trial(False):
                self.fail('consumed namespace')

    def test_atomic_publication_no_clobber_and_symlink_rejection(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'node'
            M.publish(path, {'x': 1})
            with self.assertRaises(FileExistsError):
                M.publish(path, {'x': 2})
            self.assertEqual(M.read_node(path), {'x': 1})
            alias = path.with_name('alias'); alias.symlink_to(path)
            with self.assertRaises(Exception):
                M.read_node(alias)
            self.assertFalse(list(Path(temp).glob('.tmp-*')))

    def shell_fixture(self, root, script, boot=R.BOOT, sink='/dev/null'):
        _, mapping = R.ReadinessTests().shell_fixture(root)
        mapping['/dev/pmsg0'] = sink
        for name in ('sha256sum', 'grep', 'wc', 'printf'):
            mapping['/system/bin/' + name] = shutil.which(name)
        bootpath = root / 'boot-id'; bootpath.write_text(boot + '\n')
        mapping['/proc/sys/kernel/random/boot_id'] = str(bootpath)
        prop = root / 'tools/getprop'
        prop.write_text('#!/bin/sh\ncase "$1" in\nro.product.model) echo SM-G986N;;\nro.product.device) echo y2q;;\nro.product.name) echo y2qksx;;\nro.build.version.incremental) echo G986NKSS8IYC2;;\nsys.boot_completed) echo 1;;\nesac\n')
        prop.chmod(0o755)
        mapping['/system/bin/getprop'] = str(prop)
        pattern = re.compile('|'.join(re.escape(k) for k in sorted(mapping, key=len, reverse=True)))
        return pattern.sub(lambda m: mapping[m.group()], script), mapping

    def test_real_writer_descriptor_open_and_exact_receipt(self):
        with tempfile.TemporaryDirectory() as temp:
            binding = M.make_binding(observation())
            script, _ = self.shell_fixture(Path(temp), M.write_script(binding))
            result = subprocess.run(['/bin/sh', '-c', script], capture_output=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(M.parse_write((result.returncode, result.stdout, result.stderr), binding)['returned'])
            self.assertEqual(len(M.marker_bytes(binding)), 144)
            self.assertNotIn(M.marker_line(binding).encode(), result.stdout)

    def test_real_writer_rejects_regular_symlink_and_wrong_rdev_without_write(self):
        for kind in ('regular', 'symlink', 'wrong-rdev'):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as temp:
                root = Path(temp); sink = root / 'sink'
                if kind == 'symlink': sink.symlink_to('/dev/null')
                else: sink.write_bytes(b'unchanged')
                binding = M.make_binding(observation())
                if kind == 'wrong-rdev': binding['major'] = 2
                script, _ = self.shell_fixture(root, M.write_script(binding), sink='/dev/null' if kind == 'wrong-rdev' else str(sink))
                result = subprocess.run(['/bin/sh', '-c', script], capture_output=True, timeout=10)
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn(b'S20PMSG_WRITE_V1', result.stdout)
                if kind != 'symlink': self.assertEqual(sink.read_bytes(), b'unchanged')

    def test_real_reader_binary_exact_line_only_and_no_body_export(self):
        for kind, expected, count in [('one', 'scanned', 1), ('duplicate', 'scanned', 2), ('substring', 'scanned', 0), ('missing', 'unavailable', 0), ('oversized', 'oversized', 0), ('symlink', 'indirect', 0), ('fifo', 'unreadable', 0)]:
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as temp:
                root = Path(temp); binding = M.make_binding(observation())
                script, mapping = self.shell_fixture(root, M.read_script(binding, NEW), boot='aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa')
                node = Path(mapping['/sys/fs/pstore/pmsg-ramoops-0'])
                node.unlink()
                marker = M.marker_bytes(binding)
                if kind == 'one': node.write_bytes(b'PRIVATE-LOG\x00\xff' + marker + b'other')
                elif kind == 'duplicate': node.write_bytes(marker * 2)
                elif kind == 'substring': node.write_bytes(b'prefix' + marker[1:])
                elif kind == 'oversized': node.write_bytes(b'x' * (M.RECORD_MAXIMUM + 1))
                elif kind == 'symlink': node.symlink_to(root / 'absent')
                elif kind == 'fifo': os.mkfifo(node)
                result = subprocess.run(['/bin/sh', '-c', script], capture_output=True, timeout=10)
                self.assertEqual(result.returncode, 0, result.stderr)
                parsed = M.parse_read((result.returncode, result.stdout, result.stderr))
                self.assertEqual((parsed['state'], parsed['matches']), (expected, count))
                self.assertNotIn(b'PRIVATE-LOG', result.stdout)
                self.assertNotIn(M.marker_line(binding).encode(), result.stdout)


if __name__ == '__main__':
    unittest.main()

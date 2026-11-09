"""Exercise the fixed cue caller with real journal/raw transfer consumers."""
import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'workspace/public/src/scripts/host_tools'))
import s22plus_mainline_attach_cue_v1 as cue
from s22plus_native_records_v3 import publish


class CueTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.fixture_root = Path(self.temp.name)
        self.op = self.fixture_root / 'workspace/private/operation'
        self.op.mkdir(parents=True)
        self.io = self.op / 'io-mainline-evidence'
        self.io.mkdir()
        self.now = 120_000_000_000
        self.stack = contextlib.ExitStack()
        self.addCleanup(self.stack.close)
        for module in (cue, cue.attach):
            self.stack.enter_context(patch.object(module, 'clock', lambda: self.now))
        self.stack.enter_context(patch.object(cue.raw, 'acquire_command', side_effect=AssertionError('device acquisition')))
        self.publish = publish
        grant = publish(self.op / 'grant.json', dict(host_boot=cue.host_boot(), deadline_ns=1_900_000_000_000))
        self.request = dict(operation='mainline-ram', grant=grant,
                            N=dict(ap={'fixture': 'N AP'}, member={'fixture': 'boot-only member'}, ufs_link=True))
        publish(self.op / 'operation.json', self.request)
        self.adapter = cue.Adapter(self.fixture_root, self.op)
        self.journal = cue.Journal(self.op / 'journal')
        transfer = self.op / 'io-install-native-first/attempt-fixture'
        transfer.mkdir(parents=True)
        launch = publish(transfer / 'launch.json', dict(step='install-native-first', role='N',
            ap=self.request['N']['ap'], member=self.request['N']['member'],
            boottime_ns=100_000_000_000, arrival_deadline_ns=110_000_000_000))
        self.capture = cue.raw.publish_captured_bytes(transfer, 'odin',
            stdout=b'Setup Connection\nUpload Binaries\nboot.img.lz4\n100%\nClose Connection\n', stderr=b'')
        self.journal.append('effect-intent', step='install-native-first', action='transfer', role='N', detail=dict(launch=launch))
        result = self.adapter.recover_transfer_result(cue.Step('install-native-first', 'transfer', 'N'), self.request)
        receipt = publish(self.op / 'install-native-first.json', result)
        self.journal.append('step-complete', step='install-native-first', result=receipt)
        self.journal.append('step-start', step='mainline-evidence', action='mainline-download', role='N')
        publish(self.io / 'window.json', cue.access.window_for(self.adapter, self.request))
        self.usb()
        self.guard = lambda: None

    def usb(self, number=1, *, errno=2, fields=None, related=0, topology=None, complete=True):
        data = [dict(kind='begin', topology=topology or cue.access.target.lane.CANDIDATE_TOPOLOGY,
                     boottime_ns=self.now-2_000_000_000),
                dict(kind='usb', errno=errno, fields=fields or {})]
        if complete:
            data.append(dict(kind='end', related=related, boottime_ns=self.now-1_000_000_000))
        return cue.raw.publish_captured_bytes(self.io, f'usb-{number:03d}',
            stdout=b''.join(cue.canonical(row) for row in data), stderr=b'')

    def inspect(self):
        return cue.inspect(self.adapter, self.request, self.guard)

    def issue(self):
        return cue.issue(self.adapter, self.request, self.guard)

    def test_prelaunch_entry_imports_from_another_working_directory(self):
        result = subprocess.run([sys.executable, cue.__file__, '--help'], cwd='/',
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        self.assertIn(b'check,issue,resolve', result.stdout)
        self.assertEqual(result.stderr, b'')

    def test_real_raw_check_issue_resolution_and_existing_interlock(self):
        result = self.inspect()
        self.assertEqual(result['remaining_seconds'], 100)
        self.assertFalse((self.op / 'mainline-attach-cue.json').exists())
        result = self.issue()
        self.assertEqual(result['status'], 'CUE_RECORDED_DISPLAY_NOW')
        self.assertEqual(result['instruction'], cue.INSTRUCTION)
        original = cue.pin(self.op / 'mainline-attach-cue.json')
        with self.assertRaises(ValueError):
            self.issue()
        self.assertEqual(cue.pin(self.op / 'mainline-attach-cue.json'), original)
        window = cue.pin(self.io / 'window.json')
        cue.attach.resolve(self.op, window, cue=original, resolution='completed',
                           operator_statement='Fixture operator reports the one attach completed.')
        cue.attach.close_issuance(self.op, window, guard=self.guard)
        cue.attach.rederive(self.op, window)

    def test_sixty_second_boundary_refuses_before_publication(self):
        self.now = 160_000_000_000
        with self.assertRaisesRegex(ValueError, 'more than 60'):
            self.issue()
        self.assertFalse((self.op / 'mainline-attach-cue.json').exists())

    def test_validation_delay_cannot_extend_window(self):
        calls = []
        def guard():
            calls.append(1)
            if len(calls) == 2:
                self.now = 160_000_000_000
        self.guard = guard
        with self.assertRaisesRegex(ValueError, 'window elapsed'):
            self.issue()
        self.assertFalse((self.op / 'mainline-attach-cue.json').exists())

    def delayed_publication(self, new_now):
        original = cue.attach.publish
        def publish(path, value):
            receipt = original(path, value)
            self.now = new_now
            return receipt
        with patch.object(cue.attach, 'publish', publish):
            result = self.issue()
        self.assertEqual(result['status'], 'CUE_RECORDED_DO_NOT_DISPLAY')
        self.assertIsNone(result['instruction'])
        self.assertTrue((self.op / 'mainline-attach-cue.json').exists())
        self.assertFalse((self.op / 'mainline-attach-resolution.json').exists())
        self.assertEqual(cue.read(cue.verify(result['cue']))['window'], cue.pin(self.io / 'window.json'))
        return result

    def test_published_but_too_late_never_emits_instruction(self):
        self.assertIsNone(self.delayed_publication(161_000_000_000)['publication_error_type'])

    def test_issue_raises_after_publication_retains_original_cue(self):
        self.assertEqual(self.delayed_publication(221_000_000_000)['publication_error_type'], 'SessionError')

    def test_stopped_or_changed_journal_refuses(self):
        self.journal.append('stopped', error_message='fixture stop')
        with self.assertRaisesRegex(ValueError, 'not active'):
            self.issue()

    def test_selection_race_refuses(self):
        calls = []
        def guard():
            calls.append(1)
            if len(calls) == 2:
                self.publish(self.io / 'endpoint.json', {'fixture': 'arrived'})
        self.guard = guard
        with self.assertRaisesRegex(ValueError, 'selection changed'):
            self.issue()
        self.assertFalse((self.op / 'mainline-attach-cue.json').exists())

    def test_selected_endpoint_permit_return_and_terminal_refuse(self):
        for path in (self.io/'endpoint.json', self.io/'attempt.json', self.io/'permit-intent.json',
                     self.op/'mainline-return-ready.json', self.op/'terminal.json'):
            with self.subTest(path=path.name):
                self.publish(path, {'fixture': True})
                with self.assertRaises(ValueError):
                    self.issue()
                path.unlink()

    def test_latest_partial_or_other_endpoint_cannot_reuse_old_absence(self):
        self.usb(2, errno=None, fields={'idVendor': 'fixture'})
        with self.assertRaisesRegex(ValueError, 'exact absent'):
            self.issue()

    def test_truncated_census_refuses(self):
        self.usb(2, complete=False)
        with self.assertRaisesRegex(ValueError, 'exact absent'):
            self.issue()

    def test_wrong_topology_refuses(self):
        self.usb(2, topology='fixture-other-target')
        with self.assertRaisesRegex(ValueError, 'exact absent'):
            self.issue()

    def test_absent_with_children_refuses(self):
        self.usb(2, related=1)
        with self.assertRaisesRegex(ValueError, 'exact absent'):
            self.issue()

    def test_changed_raw_transfer_cannot_supply_completion(self):
        self.capture.stdout_path.chmod(0o600)
        self.capture.stdout_path.write_bytes(b'incomplete transfer')
        with self.assertRaises((ValueError, cue.raw.RawCaptureError)):
            self.issue()

    def test_incomplete_sealed_odin_output_cannot_supply_completion(self):
        folder = self.capture.receipt_path.parent
        for path in folder.glob('odin.*'):
            path.unlink()
        cue.raw.publish_captured_bytes(folder, 'odin', stdout=b'Setup Connection\n', stderr=b'')
        with self.assertRaisesRegex(ValueError, 'does not prove a completed'):
            self.issue()

    def test_censuses_advance_during_final_guard_and_latest_is_bound(self):
        calls = []
        def guard():
            calls.append(1)
            if len(calls) == 2:
                self.usb(2)
                self.usb(3)
        self.guard = guard
        result = self.issue()
        self.assertEqual(result['status'], 'CUE_RECORDED_DISPLAY_NOW')
        evidence = cue.read(cue.verify(result['cue']))['evidence']
        self.assertEqual(evidence['last_sealed_census'], cue.pin(self.io/'usb-003.capture.json'))

    def test_latest_present_arriving_during_guard_has_no_old_absence_fallback(self):
        calls = []
        def guard():
            calls.append(1)
            if len(calls) == 2:
                self.usb(2, errno=None, fields={'idVendor': 'fixture'})
        self.guard = guard
        with self.assertRaisesRegex(ValueError, 'exact absent'):
            self.issue()
        self.assertFalse((self.op/'mainline-attach-cue.json').exists())

    def test_latest_failed_producer_during_guard_refuses(self):
        calls = []
        def guard():
            calls.append(1)
            if len(calls) == 2:
                writer = cue.raw.RawCaptureWriter(self.io, 'usb-002', stdout_maximum=1024, stderr_maximum=0)
                writer.write_stdout(b'{"kind":"begin"}\n')
                writer.finalize(returncode=None, producer_error_type='OSError')
        self.guard = guard
        with self.assertRaises(cue.raw.RawCaptureError):
            self.issue()

    def after_read(self, callback):
        original = cue.raw.read_stdout
        ran = []
        def read(handle, **kwargs):
            value = original(handle, **kwargs)
            if handle.name == 'usb-001' and not ran:
                ran.append(1)
                callback()
            return value
        return patch.object(cue.raw, 'read_stdout', read)

    def test_new_census_after_final_selection_is_still_refused(self):
        diagnostics = {}
        with self.after_read(lambda: self.usb(2)):
            with self.assertRaisesRegex(ValueError, 'new sealed census arrived'):
                cue.issue(self.adapter, self.request, self.guard, diagnostics=diagnostics)
        self.assertEqual(diagnostics['phase'], 'census-tail')
        self.assertEqual(diagnostics['selected_census_path'], str(self.io/'usb-001.capture.json'))
        self.assertEqual(diagnostics['latest_census_path'], str(self.io/'usb-002.capture.json'))
        self.assertFalse((self.op/'mainline-attach-cue.json').exists())

    def test_state_change_after_final_census_is_refused(self):
        with self.after_read(lambda: self.journal.append('stopped', error_message='fixture post-census stop')):
            with self.assertRaisesRegex(ValueError, 'selection changed'):
                self.issue()

    def test_final_raw_tampering_is_not_latest_advancement(self):
        def tamper():
            path=self.io/'usb-001.stdout.bin'
            path.chmod(0o600)
            path.write_bytes(b'changed raw')
        diagnostics = {}
        with self.after_read(tamper):
            with self.assertRaises(cue.raw.RawCaptureError):
                cue.issue(self.adapter, self.request, self.guard, diagnostics=diagnostics)
        self.assertEqual(diagnostics['phase'], 'census-tail')
        self.assertEqual(diagnostics['selected_census_path'], diagnostics['latest_census_path'])

    def test_parse_time_counts_against_sixty_second_boundary(self):
        with self.after_read(lambda: setattr(self, 'now', 160_000_000_000)):
            with self.assertRaisesRegex(ValueError, 'window elapsed'):
                self.issue()
        self.assertFalse((self.op/'mainline-attach-cue.json').exists())

    def test_cli_refusal_retains_phase_and_both_ordinals_on_stderr(self):
        stdout, stderr = io.StringIO(), io.StringIO()
        argv = [cue.__file__, 'issue', str(self.op)]
        with patch.object(sys, 'argv', argv), patch.object(cue, 'context', return_value=(self.adapter,self.request,self.guard)), \
             self.after_read(lambda: self.usb(2)), contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            with self.assertRaises(SystemExit) as stop:
                cue.main()
        self.assertEqual(stop.exception.code, 1)
        self.assertEqual(stdout.getvalue(), '')
        result = json.loads(stderr.getvalue())
        self.assertEqual(result['status'], 'CUE_CALL_REFUSED')
        self.assertEqual(result['diagnostics']['phase'], 'census-tail')
        self.assertEqual(result['diagnostics']['selected_census']['path'], str(self.io/'usb-001.capture.json'))
        self.assertEqual(result['diagnostics']['latest_census_path'], str(self.io/'usb-002.capture.json'))

    def test_cli_display_failure_preserves_published_cue_without_reissue(self):
        stdout, stderr = io.StringIO(), io.StringIO()
        argv = [cue.__file__, 'issue', str(self.op)]
        original_issue = cue.issue
        published = []
        def issue(*args, **kwargs):
            result = original_issue(*args, **kwargs)
            published.append(cue.pin(self.op/'mainline-attach-cue.json'))
            # Only main()'s post-publication display check now loses its clock.
            self.stack.enter_context(patch.object(cue, 'clock', side_effect=OSError('display clock fixture')))
            return result
        with patch.object(sys, 'argv', argv), patch.object(cue, 'context', return_value=(self.adapter,self.request,self.guard)), \
             patch.object(cue, 'issue', wraps=issue) as call, contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            with self.assertRaises(SystemExit) as stop:
                cue.main()
        self.assertEqual(stop.exception.code, 1)
        self.assertEqual(stdout.getvalue(), '')
        result = json.loads(stderr.getvalue())
        self.assertEqual(result['status'], 'CUE_CALL_REFUSED')
        self.assertEqual(result['diagnostics']['phase'], 'display-window')
        self.assertEqual(result['diagnostics']['error_type'], 'OSError')
        self.assertEqual(call.call_count, 1)
        self.assertEqual(published, [cue.pin(self.op/'mainline-attach-cue.json')])
        self.assertFalse((self.op/'mainline-attach-resolution.json').exists())
        self.assertFalse((self.op/'mainline-attach-closed.json').exists())

    def periodic_producer(self, *, present):
        """Actual fixed sysfs reader + RawCaptureWriter on private fake sysfs."""
        usbroot, netroot = self.fixture_root/'usb', self.fixture_root/'net'
        usbroot.mkdir();netroot.mkdir()
        stop = threading.Event();published = threading.Event();captures=[];errors=[]
        started = time.monotonic()
        def clock():return 120_000_000_000 + round((time.monotonic()-started)*1e9)
        def producer():
            try:
                for number in range(2, 200):
                    if stop.is_set():break
                    handle = cue.access.capture_endpoint(self.io, f'usb-{number:03d}', usb_root=usbroot, net_root=netroot)
                    captures.append(handle.receipt_path);published.set()
                    if stop.wait(.05):break
            except BaseException as error:errors.append(error);published.set()
        calls=[]
        def guard():
            calls.append(1)
            if len(calls)!=2:return
            deadline=time.monotonic()+3
            while len(captures)<4:
                self.assertLess(time.monotonic(),deadline)
                published.wait(.05);published.clear()
            if present:
                (usbroot/cue.access.target.lane.CANDIDATE_TOPOLOGY.removeprefix('usb:')).mkdir()
            # At least one normal producer period follows the slow guard.
            # The producer remains alive; no shared lock freezes its output.
            published.clear();self.assertTrue(published.wait(1))
        with patch.object(cue,'clock',clock),patch.object(cue.attach,'clock',clock),patch.object(cue.access,'clock',clock):
            thread=threading.Thread(target=producer);thread.start()
            try:
                if present:
                    with self.assertRaisesRegex(ValueError,'exact absent'):
                        cue.issue(self.adapter,self.request,guard)
                    self.assertFalse((self.op/'mainline-attach-cue.json').exists())
                else:
                    result=cue.issue(self.adapter,self.request,guard)
                    self.assertEqual(result['status'],'CUE_RECORDED_DISPLAY_NOW')
                    selected=cue.read(cue.verify(result['cue']))['evidence']['last_sealed_census']
                    self.assertIn(Path(selected['path']),captures)
                    self.assertGreaterEqual(int(Path(selected['path']).name[4:7]),5)
                self.assertTrue(thread.is_alive())
            finally:
                stop.set();thread.join(3)
                self.assertFalse(thread.is_alive())
        self.assertFalse(errors)

    def test_live_periodic_producer_and_slow_guard_issue_once(self):
        self.periodic_producer(present=False)

    def test_live_periodic_producer_present_without_endpoint_file_refuses(self):
        self.periodic_producer(present=True)


if __name__ == '__main__':
    unittest.main()

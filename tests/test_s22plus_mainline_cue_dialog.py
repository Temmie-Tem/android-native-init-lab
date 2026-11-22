"""Cue dialog helper: sealed-window timing, receipts, explicit clicks (no device, no display)."""
from pathlib import Path
import argparse
import json
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'workspace/public/src/scripts/host_tools'))
import s22plus_mainline_cue_dialog_v1 as cd
from s22plus_native_records_v3 import host_boot, pin, publish

NS = 1_000_000_000
OPENED = 1000 * NS
DEADLINE = OPENED + 120 * NS


class FakeProc:
    def __init__(self, code, out='', err=''):
        self.returncode, self.stdout, self.stderr = code, out, err


class Harness:
    """Fake BOOTTIME clock and fake processes; records are real files."""

    def __init__(self, op, *, start, issue=('ok',), dialogs=((0, ''),), resolve='ok'):
        self.op, self.t, self.calls = op, start, []
        self.issue, self.dialogs, self.resolve = list(issue), list(dialogs), resolve
        self.dialog_timeouts = []

    def clock(self):
        return self.t

    def sleep(self, s):
        self.t += int(s * NS)

    def runner(self, argv, **kw):
        argv = list(map(str, argv))
        self.calls.append(argv)
        if argv[0] == 'paplay':
            return FakeProc(0)
        if argv[0] == 'zenity':
            self.dialog_timeouts.append(int(argv[argv.index('--timeout') + 1]))
            code, out = self.dialogs.pop(0)
            self.t += 5 * NS
            return FakeProc(code, out)
        verb = argv[2]
        window = pin(self.op / 'io-mainline-evidence/window.json')
        if verb == 'issue':
            mode = self.issue.pop(0)
            if mode == 'refused-with-text':
                return FakeProc(1, '', json.dumps({'status': 'CUE_CALL_REFUSED',
                                                   'diagnostics': {'note': 'CUE_RECORDED_DISPLAY_NOW'}}))
            cue = publish(self.op / 'mainline-attach-cue.json', dict(window=window, issued_ns=self.t))
            if mode == 'wrong-receipt':
                cue = dict(cue, sha256='0' * 64)
            return FakeProc(0, json.dumps({'raw_capture': {}, 'result': {
                'status': 'CUE_RECORDED_DISPLAY_NOW', 'instruction': 'replug', 'cue': cue}}))
        if verb == 'resolve':
            self.resolution = (argv[4], argv[5])
            res = publish(self.op / 'mainline-attach-resolution.json', dict(resolution=argv[4]))
            if self.resolve == 'wrong-receipt':
                res = dict(res, sha256='0' * 64)
            return FakeProc(0, json.dumps({'raw_capture': {}, 'result': res}))
        raise AssertionError(argv)


class CueDialogTests(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.op = Path(t.name) / 'operation'
        (self.op / 'io-mainline-evidence').mkdir(parents=True)
        owner = publish(self.op / 'operation.json', {'operation': 'mainline-ram'})
        publish(self.op / 'io-mainline-evidence/window.json',
                dict(operation=owner, host_boot=host_boot(), opened_ns=OPENED, deadline_ns=DEADLINE))
        self.rows = [{'event': 'step-complete', 'data': {'step': 'install-native-first'}},
                     {'event': 'step-start', 'data': {'step': 'mainline-evidence', 'action': 'mainline-evidence'}}]

    def go(self, h):
        args = argparse.Namespace(operation=str(self.op), captures=str(self.op.parent / 'caps'), issue_delay=22.0,
                                  wait_limit=5.0, watch_ports='3-1.3', watch_seconds=1, cable='unknown', no_watch=True)
        return cd.run(args, rows=lambda op: self.rows, runner=h.runner, sleep=h.sleep, clock=h.clock,
                      wait_clock=lambda: h.t / NS)

    def issued_at(self, h):
        return [c for c in h.calls if len(c) > 2 and c[2] == 'issue']

    def test_timing_is_from_the_sealed_window_not_from_discovery(self):
        early = Harness(self.op, start=OPENED + 1 * NS)
        self.assertEqual(self.go(early), 0)
        self.assertEqual(early.dialog_timeouts, [int((DEADLINE - 8 * NS - (OPENED + 22 * NS)) / NS)])
        for f in ('mainline-attach-cue.json', 'mainline-attach-resolution.json'):
            (self.op / f).unlink()
        late = Harness(self.op, start=OPENED + 40 * NS)  # helper noticed the journal late
        self.assertEqual(self.go(late), 0)
        # issued at once, and the dialog still closes 8 s before the real deadline
        self.assertEqual(late.dialog_timeouts, [int((DEADLINE - 8 * NS - (OPENED + 40 * NS)) / NS)])
        self.assertIn('W+45.0 s', late.resolution[1])  # click 5 s after the dialog opened

    def test_explicit_buttons_and_close_or_expiry(self):
        h = Harness(self.op, start=OPENED, dialogs=[(1, '취소\n')])
        self.assertEqual(self.go(h), 0)
        self.assertEqual(h.resolution[0], 'cancelled')
        for f in ('mainline-attach-cue.json', 'mainline-attach-resolution.json'):
            (self.op / f).unlink()
        h = Harness(self.op, start=OPENED, dialogs=[(1, ''), (1, ''), (0, '')])  # closed twice, then clicked
        self.assertEqual(self.go(h), 0)
        self.assertEqual(h.resolution[0], 'completed')
        self.assertEqual(len(h.dialog_timeouts), 3)
        (self.op / 'mainline-attach-cue.json').unlink()
        (self.op / 'mainline-attach-resolution.json').unlink()
        h = Harness(self.op, start=OPENED, dialogs=[(5, '')])  # zenity timeout
        self.assertEqual(self.go(h), 4)
        self.assertFalse((self.op / 'mainline-attach-resolution.json').exists())

    def test_close_never_extends_past_deadline_minus_margin(self):
        h = Harness(self.op, start=OPENED, dialogs=[(1, '')] * 40)
        self.assertEqual(self.go(h), 4)
        self.assertLessEqual(h.t, DEADLINE - 8 * NS + 5 * NS)
        self.assertFalse(any(c[2] == 'resolve' for c in h.calls if len(c) > 2))

    def test_only_the_current_step_opens_the_window(self):
        self.rows.append({'event': 'step-complete', 'data': {'step': 'mainline-evidence'}})
        h = Harness(self.op, start=OPENED)
        self.assertEqual(self.go(h), 3)
        self.assertEqual(h.calls, [])

    def test_failure_text_and_wrong_receipt_never_display(self):
        h = Harness(self.op, start=OPENED, issue=['refused-with-text', 'ok'])
        self.assertEqual(self.go(h), 0)
        self.assertEqual(len(self.issued_at(h)), 2)  # retried: refusal left no cue
        self.assertEqual([c[-1].rsplit('/', 1)[1] for c in self.issued_at(h)], ['cue-issue-raw', 'cue-issue-raw-2'])
        for f in ('mainline-attach-cue.json', 'mainline-attach-resolution.json'):
            (self.op / f).unlink()
        h = Harness(self.op, start=OPENED, issue=['wrong-receipt'])
        self.assertEqual(self.go(h), 2)  # a cue exists but is not this receipt: no dialog, no retry
        self.assertFalse(any(c[0] == 'zenity' for c in h.calls))
        self.assertEqual(len(self.issued_at(h)), 1)

    def test_resolution_requires_its_receipt_and_foreign_window_is_refused(self):
        h = Harness(self.op, start=OPENED, resolve='wrong-receipt')
        self.assertEqual(self.go(h), 5)
        for f in ('mainline-attach-cue.json', 'mainline-attach-resolution.json'):
            (self.op / f).unlink()
        publish(self.op.parent / 'other.json', {'operation': 'other'})
        (self.op / 'io-mainline-evidence/window.json').unlink()
        publish(self.op / 'io-mainline-evidence/window.json', dict(operation=pin(self.op.parent / 'other.json'),
                host_boot=host_boot(), opened_ns=OPENED, deadline_ns=DEADLINE))
        with self.assertRaisesRegex(ValueError, 'another operation'):
            self.go(Harness(self.op, start=OPENED))

    def test_only_reviewed_tool_is_called(self):
        h = Harness(self.op, start=OPENED)
        self.go(h)
        for c in h.calls:
            if c[0] not in ('zenity', 'paplay'):
                self.assertEqual(Path(c[1]).name, 's22plus_mainline_attach_cue_v1.py')
                self.assertIn(c[2], ('issue', 'resolve'))
                self.assertIn('--capture-directory', c)


if __name__ == '__main__':
    unittest.main()

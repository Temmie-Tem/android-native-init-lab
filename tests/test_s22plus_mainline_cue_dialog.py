"""Cue dialog helper: issue/resolve calls, button mapping, timing, refusals (no device, no display)."""
from pathlib import Path
import argparse
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'workspace/public/src/scripts/host_tools'))
import s22plus_mainline_cue_dialog_v1 as cd


class FakeProc:
    def __init__(self, code, out=''):
        self.returncode, self.stdout, self.stderr = code, out, ''


class Harness:
    def __init__(self, issue_outputs, dialog_code):
        self.calls, self.issue_outputs, self.dialog_code = [], list(issue_outputs), dialog_code
        self.t = 0.0

    def runner(self, argv, **kw):
        self.calls.append(list(map(str, argv)))
        if argv[0] == 'zenity':
            self.dialog_timeout = int(argv[argv.index('--timeout') + 1])
            self.t += 7
            return FakeProc(self.dialog_code)
        if argv[0] == 'paplay':
            return FakeProc(0)
        verb = argv[2]
        if verb == 'issue':
            return FakeProc(0, self.issue_outputs.pop(0))
        if verb == 'resolve':
            return FakeProc(0, '{"status":"RESOLVED"}')
        raise AssertionError(argv)

    def sleep(self, s):
        self.t += s


class CueDialogTests(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.base = Path(t.name)

    def go(self, harness, window=True):
        args = argparse.Namespace(operation=str(self.base / 'op'), captures=str(self.base / 'caps'),
                                  issue_delay=22.0, wait_limit=5.0, watch_ports='3-1.3', watch_seconds=1,
                                  cable='unknown', no_watch=True)
        rows = (lambda op: [{'event': 'step-start', 'data': {'step': 'mainline-evidence'}}]) if window \
            else (lambda op: [])
        return cd.run(args, journal_rows=rows, runner=harness.runner, sleep=harness.sleep,
                      clock=lambda: harness.t)

    def resolve_call(self, h):
        return [c for c in h.calls if len(c) > 2 and c[2] == 'resolve']

    def test_click_replugged_resolves_completed(self):
        h = Harness(['{"status":"CUE_RECORDED_DISPLAY_NOW"}'], 0)
        self.assertEqual(self.go(h), 0)
        r = self.resolve_call(h)
        self.assertEqual(len(r), 1)
        self.assertEqual(r[0][4], 'completed')
        self.assertIn('다시 꽂았음', r[0][5])
        self.assertIn('--capture-directory', r[0])
        # issued at window+22 s -> dialog must close >= 8 s before the 120 s window ends
        self.assertEqual(h.dialog_timeout, int(120 - 22 - 8))

    def test_cancel_and_timeout(self):
        h = Harness(['{"status":"CUE_RECORDED_DISPLAY_NOW"}'], 1)
        self.assertEqual(self.go(h), 0)
        self.assertEqual(self.resolve_call(h)[0][4], 'cancelled')
        h = Harness(['{"status":"CUE_RECORDED_DISPLAY_NOW"}'], 5)
        self.assertEqual(self.go(h), 4)
        self.assertEqual(self.resolve_call(h), [])

    def test_refusals_never_resolve(self):
        for text, code in (('cue needs more than 60 seconds', 2), ('CUE_RECORDED_DO_NOT_DISPLAY', 2)):
            h = Harness([text], 0)
            self.assertEqual(self.go(h), code)
            self.assertEqual(self.resolve_call(h), [])
            self.assertFalse(any(c[0] == 'zenity' for c in h.calls))

    def test_retry_then_display(self):
        h = Harness(['CUE_CALL_REFUSED transient', '{"status":"CUE_RECORDED_DISPLAY_NOW"}'], 0)
        self.assertEqual(self.go(h), 0)
        issues = [c for c in h.calls if len(c) > 2 and c[2] == 'issue']
        self.assertEqual([c[-1].rsplit('/', 1)[1] for c in issues], ['cue-issue-raw', 'cue-issue-raw-2'])

    def test_no_window(self):
        h = Harness([], 0)
        self.assertEqual(self.go(h, window=False), 3)
        self.assertEqual(h.calls, [])

    def test_only_reviewed_tool_is_called(self):
        h = Harness(['{"status":"CUE_RECORDED_DISPLAY_NOW"}'], 0)
        self.go(h)
        for c in h.calls:
            if c[0] not in ('zenity', 'paplay'):
                self.assertEqual(Path(c[1]).name, 's22plus_mainline_attach_cue_v1.py')
                self.assertIn(c[2], ('issue', 'resolve'))


if __name__ == '__main__':
    unittest.main()

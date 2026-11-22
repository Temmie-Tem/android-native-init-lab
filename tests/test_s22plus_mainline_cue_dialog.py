"""Cue dialog helper: sealed-window timing, receipts, explicit clicks, modes (no device, no display)."""
from pathlib import Path
import argparse
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'workspace/public/src/scripts/host_tools'))
import s22plus_mainline_cue_dialog_v1 as cd
from s22plus_native_records_v3 import host_boot, pin, publish

NS = 1_000_000_000
OPENED = 1000 * NS
DEADLINE = OPENED + 120 * NS
CUTOFF = DEADLINE - 8 * NS
TICK = int(0.2 * NS)


class FakeProc:
    def __init__(self, code, out='', err=''):
        self.returncode, self.stdout, self.stderr = code, out, err


class FakeDialog:
    """A zenity process on the fake BOOTTIME clock.

    plan: (code, out[, advance_s[, effect, effect_at_s[, hang[, exits_at_kill]]]]).
    It closes itself at --timeout (exit 5) unless `hang`. `exits_at_kill`
    models the button press landing between poll() and kill(): the process
    has already exited with its own answer, so kill() changes nothing."""

    def __init__(self, h, argv, plan):
        self.h, self.start, self.returncode, self.killed, self.fired = h, h.t, None, False, False
        self.timeout = int(argv[argv.index('--timeout') + 1])
        code, out, *rest = plan
        self.code, self.out = code, out
        self.advance = rest[0] if rest else 5  # seconds after launch, or ('abs', boottime_ns)
        self.effect = rest[1] if len(rest) > 1 else None
        self.effect_at = rest[2] if len(rest) > 2 else 0
        self.hang = rest[3] if len(rest) > 3 else False
        self.exits_at_kill = rest[4] if len(rest) > 4 else False
        self.stdout = io.StringIO('')

    def poll(self):
        t = self.h.t - self.start
        if self.effect and not self.fired and t >= self.effect_at * NS:
            self.fired = True
            self.effect(self.h)
        if self.returncode is not None:
            return self.returncode
        target = self.advance[1] - self.start if isinstance(self.advance, tuple) else self.advance * NS
        if t >= target:
            self.returncode, self.stdout = self.code, io.StringIO(self.out)
        elif not self.hang and t >= self.timeout * NS:
            self.returncode = 5
        return self.returncode

    def kill(self):
        self.h.killed.append(self.h.t)
        if self.returncode is not None:
            return
        if self.exits_at_kill:
            self.returncode, self.stdout = self.code, io.StringIO(self.out)
        else:
            self.killed, self.returncode = True, -9

    def wait(self):
        return self.returncode


class Harness:
    """Fake BOOTTIME clock and fake processes; records are real files."""

    def __init__(self, op, *, start, issue=('ok',), dialogs=((0, ''),), resolve='ok', jitter=0, row_cost=0,
                 exec_delay=0):
        self.op, self.t, self.calls, self.killed = op, start, [], []
        self.issue, self.dialogs, self.resolve = list(issue), list(dialogs), resolve
        self.dialog_timeouts, self.dialog_texts, self.dialog_envs = [], [], []
        self.resolution = None
        self.journal_broken = False
        self.jitter, self.row_cost = jitter, row_cost  # wake-up latency; journal validation cost
        self.spawn_kw, self.exec_delay = [], exec_delay  # fork-to-exec pause, checked by the child guard

    def clock(self):
        return self.t

    def sleep(self, s):
        self.t += int(s * NS) + self.jitter

    def spawn(self, argv, **kw):
        argv = list(map(str, argv))
        self.calls.append(argv)
        self.dialog_timeouts.append(int(argv[argv.index('--timeout') + 1]))
        self.dialog_texts.append(argv[argv.index('--text') + 1])
        self.dialog_envs.append(kw.get('env'))
        self.spawn_kw.append(kw)
        guard = kw['preexec_fn']
        self.t += self.exec_delay
        if self.t > guard.exec_by_ns:  # what child_guard does in the forked child
            self.refused_exec = getattr(self, 'refused_exec', 0) + 1
            return FakeDialog(self, argv, (126, '', 0))
        return FakeDialog(self, argv, self.dialogs.pop(0))

    def runner(self, argv, **kw):
        argv = list(map(str, argv))
        self.calls.append(argv)
        if argv[0] == 'paplay':
            return FakeProc(0)
        verb = argv[2]
        window = pin(self.op / 'io-mainline-evidence/window.json')
        if verb == 'issue':
            mode = self.issue.pop(0)
            if mode == 'timeout':
                self.t += 45 * NS
                raise subprocess.TimeoutExpired(argv, 45)
            if mode == 'signalled':
                return FakeProc(-9)
            if mode == 'non-object':
                return FakeProc(0, json.dumps({'raw_capture': {}, 'result': ['CUE_RECORDED_DISPLAY_NOW']}))
            if mode == 'refused-with-text':
                return FakeProc(1, '', json.dumps({'status': 'CUE_CALL_REFUSED',
                                                   'diagnostics': {'note': 'CUE_RECORDED_DISPLAY_NOW'}}))
            if mode == 'slow':
                self.t += 5 * NS
            cue = publish(self.op / 'mainline-attach-cue.json', dict(window=window, issued_ns=self.t))
            if mode == 'wrong-receipt':
                cue = dict(cue, sha256='0' * 64)
            return FakeProc(0, json.dumps({'raw_capture': {}, 'result': {
                'status': 'CUE_RECORDED_DISPLAY_NOW', 'instruction': 'REVIEWED-INSTRUCTION do not repeat',
                'cue': cue}}))
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

    def reset(self):
        for f in ('mainline-attach-cue.json', 'mainline-attach-resolution.json', 'mainline-attach-recovery.json'):
            if (self.op / f).exists():
                (self.op / f).unlink()

    def go(self, h):
        args = argparse.Namespace(operation=str(self.op), captures=str(self.op.parent / 'caps'), issue_delay=22.0,
                                  wait_limit=5.0, watch_ports='3-1.3', watch_seconds=1, cable='unknown', no_watch=True)
        def rows(op):
            h.t += h.row_cost
            if h.journal_broken:
                raise FileNotFoundError('journal staging file renamed during the read')
            return list(self.rows)
        return cd.run(args, rows=rows, runner=h.runner, spawn=h.spawn, sleep=h.sleep,
                      clock=h.clock, wait_clock=lambda: h.t / NS)

    def issued(self, h):
        return [c for c in h.calls if len(c) > 2 and c[2] == 'issue']

    def resolved_calls(self, h):
        return [c for c in h.calls if len(c) > 2 and c[2] == 'resolve']

    def test_timing_is_from_the_sealed_window_not_from_discovery(self):
        early = Harness(self.op, start=OPENED + 1 * NS)
        self.assertEqual(self.go(early), 0)
        self.assertEqual(early.dialog_timeouts, [int((CUTOFF - (OPENED + 22 * NS)) / NS)])
        self.reset()
        late = Harness(self.op, start=OPENED + 40 * NS)  # helper noticed the journal late
        self.assertEqual(self.go(late), 0)
        self.assertEqual(late.dialog_timeouts, [int((CUTOFF - (OPENED + 40 * NS)) / NS)])
        self.assertIn('W+45.0 s', late.resolution[1])  # button observed 5 s after the dialog opened
        self.assertIn('observed the button', late.resolution[1])

    def test_explicit_buttons_and_close_or_expiry(self):
        h = Harness(self.op, start=OPENED, dialogs=[(1, '취소\n')])
        self.assertEqual(self.go(h), 0)
        self.assertEqual(h.resolution[0], 'cancelled')
        self.reset()
        h = Harness(self.op, start=OPENED, dialogs=[(1, ''), (1, ''), (0, '')])  # closed twice, then clicked
        self.assertEqual(self.go(h), 0)
        self.assertEqual(h.resolution[0], 'completed')
        self.assertEqual(len(h.dialog_timeouts), 3)
        self.reset()
        # nobody clicks: instruct is replaced by report at 60 s left, which zenity times out itself
        h = Harness(self.op, start=OPENED, dialogs=[(0, '', 999), (0, '', 999)])
        self.assertEqual(self.go(h), 4)
        self.assertEqual(h.dialog_texts[1], cd.REPORT)
        self.assertFalse((self.op / 'mainline-attach-resolution.json').exists())

    def test_nothing_is_visible_or_accepted_after_the_cutoff(self):
        h = Harness(self.op, start=OPENED + int(0.37 * NS), dialogs=[(1, '')] * 60)  # unaligned with the poll
        self.assertEqual(self.go(h), 4)
        self.assertLessEqual(h.t, CUTOFF)
        self.reset()
        hung = (0, '', 999, None, 0, True)  # zenity ignores its own timer
        h = Harness(self.op, start=OPENED, dialogs=[hung, hung])
        self.assertEqual(self.go(h), 4)
        self.assertEqual(len(h.killed), 2)  # withdrawn at 60 s left, then killed at the cutoff
        self.assertLessEqual(h.killed[0], DEADLINE - 60 * NS + TICK)
        self.assertLessEqual(h.killed[1], CUTOFF)  # polling wakes exactly at the cutoff
        self.assertEqual(self.resolved_calls(h), [])

    def test_zenity_gets_an_allow_listed_environment(self):
        bad = {'ZENITY_CANCEL': '0', 'ZENITY_ESC': '0', 'ZENITY_TIMEOUT': '0', 'ZENITY_EXTRA': '0',
               'DIALOG_CANCEL': '0', 'DIALOG_ESC': '0', 'DIALOG_TIMEOUT': '0', 'DIALOG_EXTRA': '0'}
        self.assertEqual(cd.zenity_env(dict(bad, DISPLAY=':0', LC_ALL='C', PYTHONPATH='/x')),
                         {'DISPLAY': ':0', 'LC_ALL': 'C'})
        with mock.patch.dict(os.environ, bad):
            h = Harness(self.op, start=OPENED)
            self.assertEqual(self.go(h), 0)
        for env in h.dialog_envs:
            self.assertFalse(any(k.startswith(('ZENITY_', 'DIALOG_')) for k in env))

    def test_fence_while_visible_switches_to_report_and_still_records(self):
        fence = lambda h: publish(self.op / 'mainline-attach-recovery.json', {'operation': 'fenced'})
        h = Harness(self.op, start=OPENED, dialogs=[(0, '', 30, fence, 2), (0, '')])
        self.assertEqual(self.go(h), 0)  # the reviewed resolver accepts evidence after a fence
        self.assertEqual(len(h.killed), 1)  # the instructing dialog was withdrawn at once
        self.assertIn('REVIEWED-INSTRUCTION', h.dialog_texts[0])
        self.assertEqual(h.dialog_texts[1], cd.REPORT)
        self.assertIn('report-only', h.resolution[1])

    def test_step_end_while_visible_switches_to_report(self):
        end = lambda h: self.rows.append({'event': 'step-complete', 'data': {'step': 'mainline-evidence'}})
        h = Harness(self.op, start=OPENED, dialogs=[(0, '', 30, end, 2), (1, '취소')])
        self.assertEqual(self.go(h), 0)
        self.assertEqual(h.dialog_texts[1], cd.REPORT)
        self.assertEqual(h.resolution[0], 'cancelled')

    def test_settled_elsewhere_withdraws_without_recording(self):
        other = lambda h: publish(self.op / 'mainline-attach-resolution.json', {'resolution': 'elsewhere'})
        h = Harness(self.op, start=OPENED, dialogs=[(0, '', 30, other, 2)])
        self.assertEqual(self.go(h), 2)
        self.assertEqual(len(h.killed), 1)
        self.assertEqual(self.resolved_calls(h), [])

    def test_sixty_second_display_suppression(self):
        h = Harness(self.op, start=OPENED + 61 * NS)
        self.assertEqual(self.go(h), 2)  # 59 s left at discovery: no issue at all
        self.assertEqual(self.issued(h), [])
        h = Harness(self.op, start=OPENED + 57 * NS, issue=['slow'])
        self.assertEqual(self.go(h), 2)  # receipt arrived with 58 s left: nothing shown, cue kept
        self.assertFalse(any(c[0] == 'zenity' for c in h.calls))
        self.assertTrue((self.op / 'mainline-attach-cue.json').exists())
        self.reset()
        h = Harness(self.op, start=OPENED, dialogs=[(1, '', 50), (0, '')])  # instruct still open at 60 s left
        self.assertEqual(self.go(h), 0)
        self.assertEqual(len(h.killed), 1)
        self.assertEqual(h.dialog_texts[1], cd.REPORT)

    def test_dialog_carries_the_reviewed_instruction_and_warns_on_reopen(self):
        h = Harness(self.op, start=OPENED, dialogs=[(1, ''), (0, '')])
        self.assertEqual(self.go(h), 0)
        first, again = h.dialog_texts
        self.assertIn('REVIEWED-INSTRUCTION do not repeat', first)
        self.assertIn('반복하지 마세요', first)
        self.assertTrue(again.startswith(cd.AGAIN) and not first.startswith(cd.AGAIN))
        self.assertIn('reviewed cue instruction', h.resolution[1])

    def test_issue_is_called_once_and_never_replayed(self):
        for mode in ('refused-with-text', 'non-object', 'timeout', 'signalled'):
            h = Harness(self.op, start=OPENED, issue=[mode, 'ok'])
            self.assertEqual(self.go(h), 2, mode)
            self.assertEqual(len(self.issued(h)), 1, mode)
            self.assertFalse(any(c[0] == 'zenity' for c in h.calls), mode)
            self.reset()

    def test_wrong_receipt_never_displays(self):
        h = Harness(self.op, start=OPENED, issue=['wrong-receipt'])
        self.assertEqual(self.go(h), 2)  # a cue exists but is not this receipt: no dialog, no retry
        self.assertFalse(any(c[0] == 'zenity' for c in h.calls))
        self.assertEqual(len(self.issued(h)), 1)

    def test_journal_read_error_withdraws_and_reaps_the_instruction(self):
        broken = lambda h: setattr(h, 'journal_broken', True)
        h = Harness(self.op, start=OPENED, dialogs=[(0, '', 30, broken, 3), (0, '')])
        self.assertEqual(self.go(h), 0)  # no traceback; the instruction is withdrawn, the report still records
        self.assertEqual(len(h.killed), 1)
        self.assertEqual(h.dialog_texts[1], cd.REPORT)

    def test_an_answer_that_lands_during_withdrawal_is_kept(self):
        fence = lambda h: publish(self.op / 'mainline-attach-recovery.json', {'operation': 'fenced'})
        h = Harness(self.op, start=OPENED, dialogs=[(0, '', 30, fence, 3, False, True)])
        self.assertEqual(self.go(h), 0)
        self.assertEqual(h.resolution[0], 'completed')
        self.assertEqual(len(h.dialog_texts), 1)
        self.assertIn('reviewed cue instruction', h.resolution[1])

    def test_an_instruction_withdrawn_within_two_seconds_counts_as_unseen(self):
        fence = lambda h: publish(self.op / 'mainline-attach-recovery.json', {'operation': 'fenced'})
        h = Harness(self.op, start=OPENED, dialogs=[(0, '', 30, fence, 1)])
        self.assertEqual(self.go(h), 2)  # no report about an instruction the operator may not have seen
        self.assertEqual(len(h.dialog_texts), 1)
        self.assertEqual(self.resolved_calls(h), [])

    def test_an_answer_just_before_the_cutoff_survives_a_late_wakeup(self):
        cancel = (1, '취소', ('abs', CUTOFF - int(0.06 * NS)), None, 0, True)
        hung = (0, '', 999, None, 0, True)  # instruct, replaced by report at 61 s left
        h = Harness(self.op, start=OPENED, dialogs=[hung, cancel], jitter=int(0.02 * NS))
        self.assertEqual(self.go(h), 0)  # found by the poll that woke 20 ms after the cutoff
        self.assertEqual(h.resolution[0], 'cancelled')
        self.reset()
        h = Harness(self.op, start=OPENED, dialogs=[hung, hung], jitter=int(0.02 * NS))
        self.assertEqual(self.go(h), 4)  # alive at the cutoff: killed, nothing recorded
        self.assertEqual(self.resolved_calls(h), [])

    def test_a_button_the_dialog_returned_just_after_the_cutoff_is_kept(self):
        late = (1, '취소', ('abs', CUTOFF + 1), None, 0, True)  # exits right after the cutoff, before the late poll
        hung = (0, '', 999, None, 0, True)
        # 21 ms wake latency keeps polls off the cutoff, so the first post-cutoff wake comes after the exit
        h = Harness(self.op, start=OPENED, dialogs=[hung, late], jitter=int(0.021 * NS))
        self.assertEqual(self.go(h), 0)  # an explicit answer, timestamped honestly; resolver takes late evidence
        self.assertEqual(h.resolution[0], 'cancelled')
        self.assertIn('W+112.0 s', h.resolution[1])

    def test_the_child_refuses_a_late_instruction_launch(self):
        h = Harness(self.op, start=DEADLINE - int(61.05 * NS), exec_delay=int(1.1 * NS))
        self.go(h)  # parent checks pass at 61.05 s; the exec would land at 59.95 s
        self.assertEqual(getattr(h, 'refused_exec', 0), 1)
        self.assertEqual(h.dialog_texts and len(h.dialog_texts), 1)
        self.assertEqual(self.resolved_calls(h), [])

    def test_the_sixty_second_check_is_sampled_after_validation(self):
        h = Harness(self.op, start=DEADLINE - int(61.05 * NS), row_cost=int(0.1 * NS))
        self.assertEqual(self.go(h), 2)  # 61.05 s before validation, 60.95 s after: suppressed
        self.assertEqual(self.issued(h), [])

    def test_zenity_dies_with_the_helper(self):
        h = Harness(self.op, start=OPENED)
        self.assertEqual(self.go(h), 0)
        self.assertTrue(all(kw['preexec_fn'].parent_pid == os.getpid() for kw in h.spawn_kw))
        # the real guard in real forked children (it never runs in this process)
        now = cd.boottime()
        run = lambda guard: subprocess.run([sys.executable, '-c', 'pass'], preexec_fn=guard).returncode
        self.assertEqual(run(cd.child_guard(os.getpid(), now + 30 * NS)), 0)
        self.assertEqual(run(cd.child_guard(os.getpid(), now - NS)), 126)  # launched too late
        self.assertEqual(run(cd.child_guard(os.getpid() + 999999, now + 30 * NS)), 127)  # parent gone
        with self.assertRaises(SystemExit):
            cd._terminate_cleanly(15, None)
        seen = {}
        import signal
        old = {s: signal.getsignal(s) for s in (signal.SIGTERM, signal.SIGHUP, signal.SIGINT)}
        try:
            with mock.patch.object(cd, 'run', lambda a: seen.update(
                    {s: signal.getsignal(s) for s in old}) or 0):
                cd.main(['--operation', 'x', '--captures', 'y'])
        finally:
            for s, f in old.items():
                signal.signal(s, f)
        self.assertTrue(seen and all(f is cd._terminate_cleanly for f in seen.values()))

    def test_resolution_requires_its_receipt_and_foreign_window_is_refused(self):
        h = Harness(self.op, start=OPENED, resolve='wrong-receipt')
        self.assertEqual(self.go(h), 5)
        self.reset()
        publish(self.op.parent / 'other.json', {'operation': 'other'})
        (self.op / 'io-mainline-evidence/window.json').unlink()
        publish(self.op / 'io-mainline-evidence/window.json', dict(operation=pin(self.op.parent / 'other.json'),
                host_boot=host_boot(), opened_ns=OPENED, deadline_ns=DEADLINE))
        h = Harness(self.op, start=OPENED)
        self.assertEqual(self.go(h), 3)  # structured exit, no traceback
        self.assertEqual(h.calls, [])

    def test_only_the_current_step_opens_the_window(self):
        self.rows.append({'event': 'step-complete', 'data': {'step': 'mainline-evidence'}})
        h = Harness(self.op, start=OPENED)
        self.assertEqual(self.go(h), 3)
        self.assertEqual(h.calls, [])

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

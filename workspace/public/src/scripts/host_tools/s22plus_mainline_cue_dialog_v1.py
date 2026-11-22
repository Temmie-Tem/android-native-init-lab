#!/usr/bin/env python3
"""Attended attach-cue helper: one explicit operator click, no assistant turn.

It only *calls* the reviewed cue tool `s22plus_mainline_attach_cue_v1.py`
through its fixed self-capture CLI (`issue` / `resolve ... --capture-directory`).
It never writes operation records, never touches USB/ADB and opens no grant.

Timing is taken from the owner's sealed observation window
(`io-mainline-evidence/window.json`, CLOCK_BOOTTIME), never from when this
helper noticed the journal:
1. wait until the journal's *last* row is `step-start mainline-evidence` and
   the window record belongs to this operation and host boot;
2. start the Stage 0 host port watch (read-only);
3. at window open + 22 s, call `issue`; display only when the call exits 0,
   its stdout object says `CUE_RECORDED_DISPLAY_NOW` with an instruction, and
   its cue receipt equals the operation's `mainline-attach-cue.json`, which in
   turn binds this window. `issue` is called **once**: the reviewed tool says
   a refusal is not proof that no cue was published and grants no retry, so
   any other outcome ends the helper and the typed fallback applies;
4. **instruct** mode shows the reviewed instruction verbatim (one replug, do
   not repeat). It is allowed only while the step is current, no resolution,
   closure or recovery fence exists, and more than 60 s of the window remain
   (the policy's display suppression). Reopening after 닫기 adds a warning not
   to replug again;
5. once an instruction has been shown, if instruct conditions fail, the
   dialog (including one already on screen, which is replaced) switches to
   **report** mode: it asks for no physical action, only whether the earlier
   replug happened. A report remains valid after owner stop or a recovery
   fence because the reviewed resolver accepts evidence then;
6. buttons: **다시 꽂았음** -> `resolve completed`; **취소** -> `resolve
   cancelled`; **닫기**, Esc, window close and timeout record nothing. The
   dialog is killed at deadline - 8 s (polling wakes exactly at the cutoff;
   every exit path, including an exception, kills and reaps it) and a button
   observed later is discarded. A dialog that exits on its own while being
   withdrawn keeps its answer, and a natural exit found by the first poll at
   the cutoff is in time. An instruct dialog withdrawn within 2 s of launch
   counts as never shown. The 60 s check is sampled after the other checks
   with a 1 s launch margin. Zenity dies with the helper (PR_SET_PDEATHSIG),
   and SIGTERM/SIGHUP/SIGINT unwind through the cleanup. Zenity gets an
   allow-listed environment, so no `ZENITY_*` or `DIALOG_*` exit-code
   override reaches it;
7. a click is recorded only while the cue exists with no resolution or
   closure, and counts only when `resolve` exits 0 and returns the receipt of
   `mainline-attach-resolution.json`. The statement gives the time the helper
   *observed* the button and which mode the dialog was in.

The operator accepted an explicit click as their resolution (2026-11-22).
This helper still needs its own review before an attended run uses it.

usage: s22plus_mainline_cue_dialog_v1.py --operation OP_DIR --captures DIR
       [--issue-delay 22] [--watch-ports 3-1.3,2-1.3] [--no-watch]
"""
import argparse
import ctypes
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[5]
CUE_TOOL = ROOT / 'workspace/public/src/scripts/host_tools/s22plus_mainline_attach_cue_v1.py'
WATCH_TOOL = ROOT / 'workspace/public/src/mainline/s22plus_canary_h0/host_port_watch.py'
sys.path.insert(0, str(ROOT / 'workspace/public/src/scripts/revalidation'))
from s22plus_native_records_v3 import Journal, clock as boottime, host_boot, pin, read, verify  # noqa: E402

TITLE = 'S22+ mainline: USB 재연결'
TEXT = ('폰 쪽 USB 케이블을 한 번만 약 3초 뽑았다가 같은 케이블·포트·방향으로 다시 꽂으세요. '
        '폰 버튼은 누르지 마세요. 반복하지 마세요.\n'
        '끝나면 [다시 꽂았음], 하지 않을 거면 [취소]. [닫기]는 아무것도 기록하지 않습니다.')
AGAIN = '이 창이 다시 떴습니다. 이미 다시 꽂았다면 또 하지 말고 버튼만 누르세요.\n'
REPORT = ('지금은 케이블을 새로 뽑거나 꽂지 마세요.\n'
          '앞서 안내에 따라 이미 다시 꽂았다면 [다시 꽂았음], 하지 않았다면 [취소]를 누르세요. '
          '[닫기]는 아무것도 기록하지 않습니다.')
RESOLUTION, CLOSED, FENCE = ('mainline-attach-resolution.json', 'mainline-attach-closed.json',
                             'mainline-attach-recovery.json')
ENV_ALLOW = ('PATH', 'HOME', 'USER', 'LOGNAME', 'LANG', 'LANGUAGE', 'DISPLAY', 'WAYLAND_DISPLAY', 'XAUTHORITY',
             'XDG_RUNTIME_DIR', 'XDG_SESSION_TYPE', 'XDG_CURRENT_DESKTOP', 'DBUS_SESSION_BUS_ADDRESS')
OK_LABEL, CANCEL_LABEL, CLOSE_LABEL = '다시 꽂았음', '취소', '닫기'
SOUND = '/usr/share/sounds/freedesktop/stereo/complete.oga'
MARGIN_NS = 8_000_000_000
MIN_REMAINING_NS = 60_000_000_000
MIN_SEEN_NS = 2_000_000_000
SPAWN_MARGIN_NS = 1_000_000_000  # an instruction needs > 60 s left after this much launch time
POLL_S = 0.2
NS = 1_000_000_000


def log(*a):
    print(time.strftime('%T'), *a, flush=True)


def journal_rows(operation):
    path = Path(operation) / 'journal'
    return Journal(path).rows() if path.exists() else []


def current_window(operation, rows):
    """The sealed window, only while the current journal row opened it."""
    operation = Path(operation)
    if not rows or rows[-1].get('event') != 'step-start' or rows[-1].get('data', {}).get('step') != 'mainline-evidence':
        return None
    path = operation / 'io-mainline-evidence' / 'window.json'
    if not path.is_file():
        return None
    window = read(path)
    if window.get('operation') != pin(operation / 'operation.json') or window.get('host_boot') != host_boot():
        raise ValueError('observation window belongs to another operation or host boot')
    return pin(path), window


def issue_display(operation, window_pin, code, stdout):
    """Display only on a successful captured call whose receipt is this cue."""
    if code != 0:
        return False
    try:
        result = json.loads(stdout)['result']
    except (ValueError, KeyError, TypeError):
        return False
    if not isinstance(result, dict) or not isinstance(result.get('instruction'), str):
        return False
    if result.get('status') != 'CUE_RECORDED_DISPLAY_NOW' or not result.get('instruction'):
        return False
    cue = Path(operation) / 'mainline-attach-cue.json'
    if not cue.is_file() or result.get('cue') != pin(cue):
        return False
    return read(verify(result['cue'])).get('window') == window_pin


def instruct_ok(operation, rows, deadline, clock):
    """A physical instruction may be shown: step current, nothing settled or fenced,
    and more than 60 s (+ launch margin) left, sampled *after* the other checks."""
    try:
        if current_window(operation, rows) is None:
            return False
    except ValueError:
        return False
    op = Path(operation)
    if any((op / n).exists() for n in (RESOLUTION, CLOSED, FENCE)):
        return False
    return deadline - clock() > MIN_REMAINING_NS + SPAWN_MARGIN_NS


def record_ok(operation):
    """An observed answer may still be recorded (the resolver decides the rest)."""
    op = Path(operation)
    return (op / 'mainline-attach-cue.json').is_file() and not (op / RESOLUTION).exists() and not (op / CLOSED).exists()


def resolved(operation, code, stdout):
    if code != 0:
        return False
    try:
        result = json.loads(stdout)['result']
    except (ValueError, KeyError, TypeError):
        return False
    path = Path(operation) / RESOLUTION
    return path.is_file() and result == pin(path)


def call(argv, run):
    """(code, stdout, stderr); code None when the outcome is uncertain (timed out / did not start)."""
    try:
        p = run(argv, capture_output=True, text=True, timeout=45)
    except (OSError, subprocess.TimeoutExpired) as e:
        return None, '', repr(e)
    return p.returncode, p.stdout or '', p.stderr or ''


def zenity_env(environ=None):
    environ = os.environ if environ is None else environ
    # allow-list: zenity also honours DIALOG_* aliases, so a deny-list is not enough
    return {k: v for k, v in environ.items() if k in ENV_ALLOW or k.startswith('LC_')}


def _die_with_parent():
    """Child pre-exec: zenity gets SIGKILL if the helper dies by any means (Linux prctl)."""
    try:
        ctypes.CDLL(None, use_errno=True).prctl(1, signal.SIGKILL, 0, 0, 0)  # PR_SET_PDEATHSIG
    except (OSError, AttributeError):
        pass


def _terminate_cleanly(signum, frame):
    raise SystemExit(128 + signum)  # unwinds through dialog_once's finally, which kills zenity


def dialog_once(text, cutoff_ns, spawn, clock, sleep, keep, zenity='zenity'):
    """(choice, observed_ns, wall, alive_ns).

    choice: completed / cancelled / dismissed / expired / withdrawn. The dialog
    is killed at `cutoff_ns` or as soon as `keep()` turns false or raises
    ('withdrawn'); a button observed after `cutoff_ns` is 'expired'. A dialog
    that exited on its own just before the kill keeps its own answer."""
    def stamp():
        return clock(), time.strftime('%Y-%m-%d %H:%M:%S %z')

    def keeping():
        try:
            return bool(keep())
        except (OSError, ValueError, KeyError, TypeError):
            return False

    remaining = (cutoff_ns - clock()) / NS
    if remaining < 1:
        return ('expired', *stamp(), 0)
    if not keeping():
        return ('withdrawn', *stamp(), 0)
    argv = [zenity, '--question', '--title', TITLE, '--text', text, '--ok-label', OK_LABEL,
            '--cancel-label', CLOSE_LABEL, '--extra-button', CANCEL_LABEL, '--width', '520',
            '--timeout', str(int(remaining))]
    try:
        p = spawn(argv, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, env=zenity_env(),
                  preexec_fn=_die_with_parent)
    except OSError:
        return ('expired', *stamp(), 0)
    started = clock()
    forced, alive_seen = None, started
    try:
        while p.poll() is None:
            now = alive_seen = clock()
            if now >= cutoff_ns:
                forced = 'expired'
            elif not keeping():
                forced = 'withdrawn'
            if forced:
                p.kill()  # no-op if it already exited; its own status is kept
                p.wait()
                break
            sleep(min(POLL_S, (cutoff_ns - now) / NS))
    finally:
        if p.poll() is None:
            p.kill()
            p.wait()
    observed, wall = stamp()
    alive = observed - started
    if forced and p.returncode < 0:
        return forced, observed, wall, alive
    out = (p.stdout.read() if p.stdout else '').strip()
    # A natural exit is found by the poll that wakes at (or just after) the
    # cutoff at the latest; it was still alive at `alive_seen` < cutoff, so the
    # button came before the cutoff (plus scheduler latency). Only a process
    # already seen alive at/after the cutoff is late, and that one was killed.
    if alive_seen >= cutoff_ns:
        return 'expired', observed, wall, alive
    if p.returncode == 0 and not out:
        return 'completed', observed, wall, alive
    if p.returncode == 1 and out == CANCEL_LABEL:
        return 'cancelled', observed, wall, alive
    if p.returncode == 1 and not out:
        return 'dismissed', observed, wall, alive
    return 'expired', observed, wall, alive  # 5 = zenity timeout; anything else is not a choice


def statement(choice, window, observed_ns, wall, mode):
    label = OK_LABEL if choice == 'completed' else CANCEL_LABEL
    shown = ('the reviewed cue instruction (one phone-end disconnect ~3 s, same cable/port/orientation, '
             'no buttons, do not repeat)' if mode == 'instruct' else
             'a report-only prompt asking whether the earlier instructed replug happened, with no new action')
    return (f'Operator clicked "{label}" in the attended cue dialog; the helper observed the button '
            f'at {wall} (W+{(observed_ns - window["opened_ns"]) / NS:.1f} s on the sealed observation window, '
            f'sampled when the dialog returned; the click itself is at or before that). Dialog showed {shown}.')


def run(args, *, rows=journal_rows, runner=subprocess.run, spawn=subprocess.Popen, sleep=time.sleep,
        clock=boottime, wait_clock=time.monotonic, notify=True):
    op, caps = Path(args.operation), Path(args.captures)
    caps.mkdir(mode=0o700, parents=True, exist_ok=True)
    give_up = wait_clock() + args.wait_limit
    found = None
    while found is None:
        try:
            found = current_window(op, rows(op))
        except ValueError as e:
            log('FOREIGN_WINDOW', e)
            return 3
        except OSError:
            found = None  # journal staging rename raced the read; look again
        if found is None:
            if wait_clock() > give_up:
                log('NO_WINDOW')
                return 3
            sleep(0.5)
    window_pin, window = found

    def live_rows():
        """Journal rows, or None if the journal cannot be read (a staging rename races the read)."""
        for _ in range(3):
            try:
                return rows(op)
            except (OSError, ValueError):
                sleep(0.05)
        return None

    opened, deadline = window['opened_ns'], window['deadline_ns']
    log('WINDOW_OPEN', f'now W+{(clock() - opened) / NS:.1f} s')
    if not args.no_watch and runner is subprocess.run:
        argv = [sys.executable, str(WATCH_TOOL), '--output', str(caps / 'host-port-watch'),
                '--duration', str(args.watch_seconds), '--cable', args.cable, '--note', f'attended window {op.name}']
        for port in args.watch_ports.split(','):
            argv += ['--port', port]
        watch = subprocess.Popen(argv, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        log('HOST_PORT_WATCH_PID', watch.pid)
    wait = opened + int(args.issue_delay * NS) - clock()
    if wait > 0:
        sleep(wait / NS)
    if not instruct_ok(op, live_rows(), deadline, clock):
        log('CUE_NOT_ISSUABLE')  # step ended, fenced, settled, or 60 s or less left
        return 2
    cap = caps / 'cue-issue-raw'
    cap.mkdir(mode=0o700, exist_ok=True)
    sent = clock()
    code, out, err = call([sys.executable, str(CUE_TOOL), 'issue', str(op), '--capture-directory', str(cap)], runner)
    log(f'issue sent W+{(sent - opened) / NS:.1f}s returned W+{(clock() - opened) / NS:.1f}s exit {code}',
        (out or err)[:300].replace('\n', ' '))
    if not issue_display(op, window_pin, code, out):
        # one call only: a refusal is not proof that no cue exists, and nothing is replayed
        log('CUE_NOT_DISPLAYED', 'cue file present' if (op / 'mainline-attach-cue.json').exists() else 'no cue file seen')
        return 2
    instruction = json.loads(out)['result']['instruction']
    if notify:
        try:
            runner(['paplay', SOUND], capture_output=True, timeout=2)
        except (OSError, subprocess.TimeoutExpired):
            pass
    cutoff = deadline - MARGIN_NS
    instruct_text = f'{TEXT}\n\n검토된 지시: {instruction}'
    mode, shown = 'instruct', 0
    while True:
        if not record_ok(op):
            log('CUE_SETTLED_ELSEWHERE')  # resolved or closed by the owner: nothing to ask
            return 2
        if mode == 'instruct' and not instruct_ok(op, live_rows(), deadline, clock):
            if not shown:
                log('CUE_DISPLAY_SUPPRESSED')  # nothing was shown; the cue stays for the typed fallback
                return 2
            mode = 'report'
            log('DIALOG_MODE report')
        if mode == 'instruct':
            text = instruct_text if not shown else AGAIN + instruct_text
            keep = lambda: record_ok(op) and instruct_ok(op, live_rows(), deadline, clock)
        else:
            text, keep = REPORT, lambda: record_ok(op)
        choice, observed, wall, alive = dialog_once(text, cutoff, spawn, clock, sleep, keep)
        if choice != 'withdrawn' or alive >= MIN_SEEN_NS:
            shown += 1  # a dialog killed within 2 s of launch is treated as never seen
        log('DIALOG', mode, choice, f'observed W+{(observed - opened) / NS:.1f}s alive {alive / NS:.1f}s')
        if choice in ('completed', 'cancelled'):
            break
        if choice == 'expired':
            log('NO_RESOLUTION_RECORDED')
            return 4
    if not record_ok(op):
        log('CUE_SETTLED_BEFORE_RECORD', choice)
        return 2
    rcap = caps / 'cue-resolution-raw'
    rcap.mkdir(mode=0o700, exist_ok=True)
    code, out, err = call([sys.executable, str(CUE_TOOL), 'resolve', str(op), choice,
                           statement(choice, window, observed, wall, mode), '--capture-directory', str(rcap)], runner)
    log('RESOLVE', code, (out or err)[:300].replace('\n', ' '))
    return 0 if code is not None and resolved(op, code, out) else 5


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--operation', required=True)
    ap.add_argument('--captures', required=True)
    ap.add_argument('--issue-delay', type=float, default=22.0)
    ap.add_argument('--wait-limit', type=float, default=600.0)
    ap.add_argument('--watch-ports', default='3-1.3,2-1.3')
    ap.add_argument('--watch-seconds', type=float, default=200.0)
    ap.add_argument('--cable', choices=('c-to-a', 'c-to-c', 'unknown'), default='unknown')
    ap.add_argument('--no-watch', action='store_true')
    args = ap.parse_args(argv)
    for sig in (signal.SIGTERM, signal.SIGHUP, signal.SIGINT):
        signal.signal(sig, _terminate_cleanly)
    return run(args)


if __name__ == '__main__':
    sys.exit(main())

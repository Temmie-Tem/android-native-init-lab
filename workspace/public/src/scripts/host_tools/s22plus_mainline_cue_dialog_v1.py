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
   turn binds this window. A refusal is retried only while no cue exists and
   more than 60 s of the window remain;
4. show a dialog with three buttons. **다시 꽂았음** -> `resolve completed`;
   **취소** -> `resolve cancelled`; **닫기**, Esc or closing the window record
   nothing and the dialog reappears while time remains. The dialog never stays
   open past deadline - 8 s;
5. a click is recorded only when `resolve` exits 0 and returns the receipt of
   the operation's `mainline-attach-resolution.json`.

The operator accepted an explicit click as their resolution (2026-11-22).
This helper still needs its own review before an attended run uses it.

usage: s22plus_mainline_cue_dialog_v1.py --operation OP_DIR --captures DIR
       [--issue-delay 22] [--watch-ports 3-1.3,2-1.3] [--no-watch]
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[5]
CUE_TOOL = ROOT / 'workspace/public/src/scripts/host_tools/s22plus_mainline_attach_cue_v1.py'
WATCH_TOOL = ROOT / 'workspace/public/src/mainline/s22plus_canary_h0/host_port_watch.py'
sys.path.insert(0, str(ROOT / 'workspace/public/src/scripts/revalidation'))
from s22plus_native_records_v3 import Journal, clock as boottime, host_boot, pin, read, verify  # noqa: E402

TITLE = 'S22+ mainline: USB 재연결'
TEXT = ('지금 폰 쪽 USB 케이블을 약 3초 뽑았다가 같은 케이블·포트·방향으로 다시 꽂으세요. 폰 버튼은 누르지 마세요.\n'
        '끝나면 [다시 꽂았음], 하지 않을 거면 [취소]. [닫기]는 아무것도 기록하지 않습니다.')
OK_LABEL, CANCEL_LABEL, CLOSE_LABEL = '다시 꽂았음', '취소', '닫기'
SOUND = '/usr/share/sounds/freedesktop/stereo/complete.oga'
MARGIN_NS = 8_000_000_000
MIN_REMAINING_NS = 60_000_000_000
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
        value = json.loads(stdout)
        result = value['result']
    except (ValueError, KeyError, TypeError):
        return False
    if result.get('status') != 'CUE_RECORDED_DISPLAY_NOW' or not result.get('instruction'):
        return False
    cue = Path(operation) / 'mainline-attach-cue.json'
    if not cue.is_file() or result.get('cue') != pin(cue):
        return False
    return read(verify(result['cue'])).get('window') == window_pin


def resolved(operation, code, stdout):
    if code != 0:
        return False
    try:
        result = json.loads(stdout)['result']
    except (ValueError, KeyError, TypeError):
        return False
    path = Path(operation) / 'mainline-attach-resolution.json'
    return path.is_file() and result == pin(path)


def call(argv, run):
    p = run(argv, capture_output=True, text=True, timeout=45)
    return p.returncode, p.stdout or '', p.stderr or ''


def dialog_once(timeout_s, run, zenity='zenity'):
    """'completed', 'cancelled', 'dismissed' (close/Esc/닫기) or 'expired'."""
    argv = [zenity, '--question', '--title', TITLE, '--text', TEXT, '--ok-label', OK_LABEL,
            '--cancel-label', CLOSE_LABEL, '--extra-button', CANCEL_LABEL, '--width', '520',
            '--timeout', str(max(1, int(timeout_s)))]
    try:
        p = run(argv, capture_output=True, text=True, timeout=timeout_s + 10)
    except (OSError, subprocess.TimeoutExpired):
        return 'expired'
    out = (p.stdout or '').strip()
    if p.returncode == 0 and not out:
        return 'completed'
    if p.returncode == 1 and out == CANCEL_LABEL:
        return 'cancelled'
    if p.returncode == 1 and not out:
        return 'dismissed'
    return 'expired'  # 5 = zenity timeout; anything else is not a choice


def statement(choice, window, now_ns, wall=time.strftime):
    label = OK_LABEL if choice == 'completed' else CANCEL_LABEL
    return (f'Operator clicked "{label}" in the attended cue dialog at {wall("%Y-%m-%d %H:%M:%S %z")} '
            f'(W+{(now_ns - window["opened_ns"]) / NS:.1f} s on the sealed observation window; '
            'instruction: phone-end disconnect ~3 s, reconnect same cable/port/orientation, no buttons).')


def run(args, *, rows=journal_rows, runner=subprocess.run, sleep=time.sleep, clock=boottime,
        wait_clock=time.monotonic, notify=True):
    op, caps = Path(args.operation), Path(args.captures)
    caps.mkdir(mode=0o700, parents=True, exist_ok=True)
    give_up = wait_clock() + args.wait_limit
    found = None
    while found is None:
        found = current_window(op, rows(op))
        if found is None:
            if wait_clock() > give_up:
                log('NO_WINDOW')
                return 3
            sleep(0.5)
    window_pin, window = found
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
    attempt = 0
    while True:
        if current_window(op, rows(op)) is None:
            log('WINDOW_STEP_ENDED')
            return 2
        if deadline - clock() <= MIN_REMAINING_NS:
            log('CUE_WINDOW_PASSED')
            return 2
        attempt += 1
        cap = caps / ('cue-issue-raw' if attempt == 1 else f'cue-issue-raw-{attempt}')
        cap.mkdir(mode=0o700, exist_ok=True)
        code, out, err = call([sys.executable, str(CUE_TOOL), 'issue', str(op), '--capture-directory', str(cap)], runner)
        log(f'issue attempt {attempt} at W+{(clock() - opened) / NS:.1f}s exit {code}', (out or err)[:300].replace('\n', ' '))
        if issue_display(op, window_pin, code, out):
            break
        if (op / 'mainline-attach-cue.json').exists():
            log('CUE_EXISTS_NOT_DISPLAYED')  # never re-issue or infer a physical action
            return 2
        sleep(3)
    if notify:
        for _ in range(2):
            runner(['paplay', SOUND], capture_output=True)
    while True:
        left = (deadline - MARGIN_NS - clock()) / NS
        if left < 1:
            log('NO_RESOLUTION_RECORDED')
            return 4
        choice = dialog_once(left, runner)
        log('DIALOG', choice, f'W+{(clock() - opened) / NS:.1f}s')
        if choice in ('completed', 'cancelled'):
            break
        if choice == 'expired':
            log('NO_RESOLUTION_RECORDED')
            return 4
    rcap = caps / 'cue-resolution-raw'
    rcap.mkdir(mode=0o700, exist_ok=True)
    code, out, err = call([sys.executable, str(CUE_TOOL), 'resolve', str(op), choice,
                           statement(choice, window, clock()), '--capture-directory', str(rcap)], runner)
    log('RESOLVE', code, (out or err)[:300].replace('\n', ' '))
    return 0 if resolved(op, code, out) else 5


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
    return run(ap.parse_args(argv))


if __name__ == '__main__':
    sys.exit(main())

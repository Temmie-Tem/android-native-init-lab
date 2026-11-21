#!/usr/bin/env python3
"""Attended attach-cue helper: one-click operator resolution, no assistant turn.

Replaces the per-run `cue-watch.py` pattern (ML052). It only *calls* the
reviewed cue tool `s22plus_mainline_attach_cue_v1.py` through its fixed
self-capture CLI (`issue` / `resolve ... --capture-directory`); it never writes
operation records itself, never touches USB/ADB and opens no grant.

Flow:
1. wait for the operation journal's `step-start mainline-evidence`;
2. start the Stage 0 host port watch (read-only) for the window;
3. after `--issue-delay` seconds, call `issue` (retry only while the tool
   refuses with a retryable reason, as before);
4. on `CUE_RECORDED_DISPLAY_NOW`, show a dialog with two buttons and a sound:
   "다시 꽂았음" -> `resolve completed`, "취소" -> `resolve cancelled`;
   the operator statement records the button clicked and the local time;
5. if the dialog times out (it closes 8 s before the 120 s window ends), nothing is resolved
   (the owner's interlock then closes the attempt as before).

The click is the operator's own action; whether it satisfies the contract's
"actual operator resolution" is for the operator and the profile review to
adopt. This helper must be reviewed before an attended run uses it.

usage: s22plus_mainline_cue_dialog_v1.py --operation OP_DIR --captures DIR
       [--issue-delay 22] [--watch-ports 3-1.3,2-1.3] [--no-watch]
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[5]
CUE_TOOL = ROOT / 'workspace/public/src/scripts/host_tools/s22plus_mainline_attach_cue_v1.py'
WATCH_TOOL = ROOT / 'workspace/public/src/mainline/s22plus_canary_h0/host_port_watch.py'
TITLE = 'S22+ mainline: USB 재연결'
TEXT = ('지금 폰 쪽 USB 케이블을 약 3초 뽑았다가 같은 케이블·포트·방향으로 다시 꽂으세요.\n'
        '버튼은 누르지 마세요. 끝나면 [다시 꽂았음], 하지 않을 거면 [취소].')
OK_LABEL, CANCEL_LABEL = '다시 꽂았음', '취소'
SOUND = '/usr/share/sounds/freedesktop/stereo/complete.oga'
WINDOW_S, MARGIN_S = 120.0, 8.0


def log(*a):
    print(time.strftime('%T'), *a, flush=True)


def window_open(operation, journal_rows):
    try:
        rows = journal_rows(operation)
    except Exception:
        return False
    return any(r.get('event') == 'step-start' and r.get('data', {}).get('step') == 'mainline-evidence'
               for r in rows)


def default_rows(operation):
    sys.path.insert(0, str(ROOT / 'workspace/public/src/scripts/revalidation'))
    from s22plus_native_records_v3 import Journal
    p = Path(operation) / 'journal'
    return Journal(p).rows() if p.exists() else []


def call_cue(argv, run=subprocess.run):
    p = run(argv, capture_output=True, text=True, timeout=40)
    return p.returncode, (p.stdout or '') + (p.stderr or '')


def dialog(timeout_s, run=subprocess.run, zenity='zenity'):
    """Return 'completed', 'cancelled' or None (timeout / no display)."""
    argv = [zenity, '--question', '--title', TITLE, '--text', TEXT, '--ok-label', OK_LABEL,
            '--cancel-label', CANCEL_LABEL, '--width', '480', '--timeout', str(max(1, int(timeout_s)))]
    try:
        p = run(argv, capture_output=True, text=True, timeout=timeout_s + 10)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return {0: 'completed', 1: 'cancelled'}.get(p.returncode)  # 5 = zenity timeout


def statement(choice, now=time.strftime):
    label = OK_LABEL if choice == 'completed' else CANCEL_LABEL
    return (f'Operator clicked "{label}" in the attended cue dialog at {now("%Y-%m-%d %H:%M:%S %z")} '
            f'(dialog instruction: phone-end disconnect ~3 s, reconnect same cable/port/orientation, no buttons).')


def run(args, *, journal_rows=default_rows, runner=subprocess.run, sleep=time.sleep, clock=time.monotonic,
        notify=True):
    op, caps = Path(args.operation), Path(args.captures)
    caps.mkdir(mode=0o700, parents=True, exist_ok=True)
    deadline = clock() + args.wait_limit
    while not window_open(op, journal_rows):
        if clock() > deadline:
            log('NO_WINDOW')
            return 3
        sleep(0.5)
    t0 = clock()
    log('WINDOW_OPEN')
    watch = None
    if not args.no_watch:
        out = caps / 'host-port-watch'
        argv = [sys.executable, str(WATCH_TOOL), '--output', str(out), '--duration', str(args.watch_seconds),
                '--cable', args.cable, '--note', f'attended window {op.name}']
        for port in args.watch_ports.split(','):
            argv += ['--port', port]
        watch = subprocess.Popen(argv, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) \
            if runner is subprocess.run else None
    sleep(args.issue_delay)
    attempt = 0
    try:
        while clock() - t0 < 58:
            attempt += 1
            cap = caps / ('cue-issue-raw' if attempt == 1 else f'cue-issue-raw-{attempt}')
            cap.mkdir(mode=0o700, exist_ok=True)
            code, text = call_cue([sys.executable, str(CUE_TOOL), 'issue', str(op), '--capture-directory', str(cap)],
                                  runner)
            log(f'issue attempt {attempt} at window+{clock() - t0:.1f}s', text[:300].replace('\n', ' '))
            if 'CUE_RECORDED_DISPLAY_NOW' in text:
                if notify:
                    for _ in range(2):
                        runner(['paplay', SOUND], capture_output=True)
                left = WINDOW_S - (clock() - t0) - MARGIN_S  # resolve strictly inside the window
                choice = dialog(left, runner)
                log('DIALOG', choice)
                if choice is None:
                    log('NO_RESOLUTION_RECORDED')
                    return 4
                rcap = caps / 'cue-resolution-raw'
                rcap.mkdir(mode=0o700, exist_ok=True)
                code, text = call_cue([sys.executable, str(CUE_TOOL), 'resolve', str(op), choice, statement(choice),
                                       '--capture-directory', str(rcap)], runner)
                log('RESOLVE', code, text[:300].replace('\n', ' '))
                return 0 if code == 0 else 5
            if 'more than 60 seconds' in text or 'CUE_RECORDED_DO_NOT_DISPLAY' in text:
                log('CUE_NOT_POSSIBLE')
                return 2
            sleep(3)
        log('CUE_WINDOW_PASSED')
        return 2
    finally:
        if watch is not None:
            log('HOST_PORT_WATCH_PID', watch.pid)  # ends on its own --duration


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

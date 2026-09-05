"""Bounded idle/reuse schedule on one privately loaded host-first codec.

This module has no CLI, artifact packaging or approval entry point. P342's
ordinary runner binds its fresh wire identity, schedule, immutable timing and
four-session proof; this helper alone grants nothing. Historical P341 wire
identities are used only in synthetic H0 fixtures, never for candidate replay.
"""
from __future__ import annotations

import hashlib
import inspect
import os
import select
import sys
import time
from typing import Any

IDLE_SECONDS = 120
SAME_FD_SESSIONS = 3
TOTAL_SESSIONS = 4
OBSERVATION_SECONDS = 300
# Reserve all four existing 30-second exchange windows, without adding an
# arbitrary tight scheduling-jitter gate around the requested two-minute idle.
MAX_IDLE_SECONDS = OBSERVATION_SECONDS - TOTAL_SESSIONS * 30
IDLE_READ_BOUND = 4096
CONTRACT_ID = 's22plus-fyg8-idle-reuse-h0-v1'


def _replace(source: str, old: str, new: str) -> str:
    if source.count(old) != 1:
        raise ValueError('idle reuse source anchor differs')
    return source.replace(old, new, 1)


def install(module: Any, *, clock=time.monotonic, pause=time.sleep,
            outer_deadline: float | None = None) -> list[dict]:
    """Install once on an unshared codec; injected clock is for H0 tests only.

    Reuse the original exchange loop and raw failure handler. Idle happens
    inside its third-session try, before OPEN; no frame is retried or drained.
    The existing per-exchange deadline starts only after the idle phase.
    """
    if sys.modules.get(module.__name__) is module or hasattr(module, '_idle_reuse_installed'):
        raise ValueError('idle probe requires a fresh private module')
    if (module.MAX_INITIAL_SESSIONS, module.MAX_SESSIONS) != (2, 3):
        raise ValueError('predecessor session bounds differ')
    if MAX_IDLE_SECONDS + TOTAL_SESSIONS * module.SESSION_TIMEOUT_SEC > OBSERVATION_SECONDS:
        raise ValueError('idle schedule exceeds existing observation budget')
    producer = inspect.getsource(module.validate_retained_proof)
    producer = _replace(producer,
        '        value.sessions[0].physical_reopen_index != 0\n'
        '        or value.sessions[1].physical_reopen_index != 0\n'
        '        or value.sessions[2].physical_reopen_index != 1\n'
        '        or value.sessions[0].descriptor != value.sessions[1].descriptor',
        '        any(item.physical_reopen_index != 0 or item.descriptor != value.sessions[0].descriptor\n'
        '            for item in value.sessions[:MAX_INITIAL_SESSIONS])\n'
        '        or value.sessions[MAX_INITIAL_SESSIONS].physical_reopen_index != 1')
    parser = inspect.getsource(module.validate_proof_value)
    parser = _replace(parser, '(0 if index < 2 else 1)',
                      '(0 if index < MAX_INITIAL_SESSIONS else 1)')
    module.MAX_INITIAL_SESSIONS = SAME_FD_SESSIONS
    module.MAX_SESSIONS = TOTAL_SESSIONS
    module.SCHEMA = CONTRACT_ID
    module.CONTRACT_ID = CONTRACT_ID
    exec(compile(producer + '\n' + parser, '<idle-reuse-h0>', 'exec', dont_inherit=True), module.__dict__)

    original = module._exchange_one
    original_retained = module.exchange_retained
    receipts: list[dict] = []
    calls = 0
    first_descriptor = None
    used = False

    def exchange(descriptor, auth_key, writer, seen_nonces, expected_boot_id, timeout_sec):
        nonlocal calls, first_descriptor
        index = calls
        calls += 1
        if index == 0:
            first_descriptor = descriptor
        if index == 2:
            audit = module.ExchangeAudit(auth_key_sha256=hashlib.sha256(auth_key).hexdigest())
            audit.current_stage = 'same-fd-idle'
            started = clock()
            receipt = dict(phase='same-fd-idle', before_session_index=index,
                           requested_seconds=IDLE_SECONDS, elapsed_seconds=0.0,
                           same_descriptor=descriptor == first_descriptor,
                           completed=False, received_bytes=0)
            receipts.append(receipt)
            try:
                if not receipt['same_descriptor']:
                    raise ValueError('idle descriptor changed')
                while True:
                    elapsed = clock() - started
                    receipt['elapsed_seconds'] = elapsed
                    if outer_deadline is not None and clock() >= outer_deadline:
                        raise TimeoutError('observation deadline expired during idle')
                    if elapsed < 0 or elapsed > MAX_IDLE_SECONDS:
                        raise TimeoutError('idle clock/bound exceeded')
                    # Unexpected input/EOF is retained once then stops. No drain,
                    # resynchronization, extra OPEN or other descriptor access.
                    if select.select([descriptor], [], [], 0)[0]:
                        raw = os.read(descriptor, IDLE_READ_BOUND)
                        audit.rx.extend(raw)
                        receipt['received_bytes'] = len(raw)
                        writer.write_stdout(raw)
                        raise OSError('idle endpoint ended or emitted unsolicited bytes')
                    if elapsed >= IDLE_SECONDS:
                        receipt['completed'] = True
                        break
                    remaining = (outer_deadline - clock()) if outer_deadline is not None else 0.25
                    pause(min(0.25, IDLE_SECONDS - elapsed, max(0, remaining)))
            except Exception as exc:
                module._raise_partial(exc, audit, 'same-fd-idle')
        if outer_deadline is not None:
            timeout_sec = min(timeout_sec, outer_deadline - clock())
            if timeout_sec <= 0:
                audit = module.ExchangeAudit(auth_key_sha256=hashlib.sha256(auth_key).hexdigest())
                module._raise_partial(TimeoutError('observation deadline expired'), audit,
                                      'observation-deadline')
        return original(descriptor, auth_key, writer, seen_nonces, expected_boot_id, timeout_sec)

    module._exchange_one = exchange
    def once(*args, **kwargs):
        nonlocal used
        if used:
            raise ValueError('idle qualification module already used')
        used = True
        return original_retained(*args, **kwargs)
    module.exchange_retained = once
    for name in ('exchange_resident', 'exchange_resident_sessions', 'exchange_commands'):
        if hasattr(module, name):
            setattr(module, name, once)
    for name in ('validate_default_proof', 'validate_resident_proof'):
        if hasattr(module, name):
            setattr(module, name, module.validate_retained_proof)
    module._idle_reuse_installed = True
    return receipts


def validate_idle(receipts: list[dict]) -> dict:
    """Timing is separate from session proof; neither alone proves the trial."""
    if type(receipts) is not list or len(receipts) != 1:
        raise ValueError('one idle receipt required')
    value = receipts[0]
    expected = {'phase', 'before_session_index', 'requested_seconds',
                'elapsed_seconds', 'same_descriptor', 'completed', 'received_bytes'}
    if type(value) is not dict or set(value) != expected:
        raise ValueError('idle receipt shape differs')
    if (value['phase'] != 'same-fd-idle' or type(value['before_session_index']) is not int
        or value['before_session_index'] != 2 or type(value['requested_seconds']) is not int
        or value['requested_seconds'] != IDLE_SECONDS or value['same_descriptor'] is not True
        or value['completed'] is not True or type(value['received_bytes']) is not int
        or value['received_bytes'] != 0 or type(value['elapsed_seconds']) not in (float, int)
        or not IDLE_SECONDS <= value['elapsed_seconds'] <= MAX_IDLE_SECONDS):
        raise ValueError('idle interval is not proved')
    return dict(value)

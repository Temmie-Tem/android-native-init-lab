"""Authenticated request dispatch only; no post-display read or visual claim."""
from dataclasses import dataclass
import copy
import hashlib
import hmac
import math
import os
import re
import select
import struct
import time
import types
import s22plus_fyg8_p353_research_shell_runtime as runtime
import s22plus_fyg8_p345_research_shell_observer as shared
import s22plus_fyg8_research_shell_exchange as shell_exchange

SCHEMA = 's22plus-fyg8-p353-static-display-dispatch-v1'
CONTRACT_ID = 's22plus-fyg8-p353-static-display-dispatch-observer-v1'
TARGET = runtime.TARGET
RUN_ID = runtime.P353_RUN_ID
RUN_ID_HEX = runtime.P353_RUN_ID_HEX
INITIAL_OBSERVATION = 'p353_static_display_dispatch'
INITIAL_OBSERVATION_FIELD = 'p353_display_dispatch'
SESSION_COUNT = SAME_FD_SESSION_COUNT = TOTAL_SESSIONS = MAX_SESSIONS = MAX_INITIAL_SESSIONS = 1
TOTAL_COMMANDS = 2
RECONNECT_COUNT = MAX_RECONNECTS = PHYSICAL_REOPEN_COUNT = IDLE_SECONDS = 0
QUALIFICATION_TIMEOUT_SEC = 60.0
QualificationError = shared.QualificationError
QualificationResult = shared.QualificationResult
identity = shared.identity


@dataclass(frozen=True)
class QualificationStep:
    ordinal: int
    name: str
    command: bytes
    expected_outcome: str = 'dispatched'


DISPLAY_STEP = QualificationStep(1, 'static-display-dispatch', runtime.DISPLAY_COMMAND)
QUALIFICATION_COMMANDS = (DISPLAY_STEP,)


def _protocol(observer, key, read_bytes, write_frame, audit):
    """Same exact prefix for live transport and immutable captured replay."""
    codec = observer._CODEC
    key = codec._validate_key(key)
    def expect(kind, seq):
        header = read_bytes(codec.HEADER.size)
        length = codec.HEADER.unpack(header)[3]
        if length > runtime.MAX_FRAME_PAYLOAD:
            raise QualificationError('P353 frame exceeds bound')
        return codec._expect(codec.decode_frame(header + read_bytes(length)), kind, seq)
    audit.current_stage = 'open-write'
    write_frame(runtime.FRAME_OPEN, 0, RUN_ID)
    audit.current_stage = 'banner-read'
    if read_bytes(len(runtime.DEVICE_BANNER)) != runtime.DEVICE_BANNER:
        raise QualificationError('P353 banner differs')
    audit.banner_seen = True
    for stage in (0, runtime.DIAGNOSTIC_STAGE_OPEN_PARSED, runtime.DIAGNOSTIC_STAGE_RNG):
        audit.current_stage = 'diagnostic-read'
        header = read_bytes(codec.HEADER.size)
        length = codec.HEADER.unpack(header)[3]
        if length > runtime.MAX_FRAME_PAYLOAD:
            raise QualificationError('P353 diagnostic exceeds bound')
        frame = codec.decode_frame(header + read_bytes(length))
        audit.diagnostics.append(observer._P333.parse_diagnostic_frame(frame, stage))
    if audit.diagnostics[-1].code < 0:
        raise QualificationError('P353 RNG failed')
    audit.rng_eagain_retries = audit.diagnostics[-1].code
    audit.current_stage = 'challenge-read'
    nonce = expect(runtime.FRAME_CHALLENGE, 0)
    codec._validate_nonce(nonce)
    audit.nonce = nonce
    audit.challenge_seen = True
    write_frame(runtime.FRAME_AUTH, 1, observer.compute_open_tag(key, RUN_ID, nonce))
    audit.current_stage = 'ready-read'
    if not hmac.compare_digest(expect(runtime.FRAME_READY, 1), observer.compute_ready_tag(key, RUN_ID, nonce)):
        raise QualificationError('P353 READY differs')
    audit.ready_seen = audit.authenticated = True
    audit.current_stage = 'boot-id-read'
    header = read_bytes(codec.HEADER.size)
    length = codec.HEADER.unpack(header)[3]
    if length > runtime.MAX_FRAME_PAYLOAD:
        raise QualificationError('P353 BOOT frame exceeds bound')
    audit.boot_id = observer.decode_boot_id_frame(codec.decode_frame(header + read_bytes(length)), key, RUN_ID, nonce)
    parent = runtime.DEFAULT_COMMANDS[0]
    tag = hmac.new(key, runtime.AUTH_DOMAIN_EXEC + RUN_ID + nonce + struct.pack('<I', 3) + parent, hashlib.sha256).digest()
    audit.current_stage = 'identity-exec-write'
    write_frame(runtime.FRAME_EXEC, 3, tag + parent)
    output = bytearray()
    while True:
        audit.current_stage = 'identity-exec-read'
        header = read_bytes(codec.HEADER.size)
        length = codec.HEADER.unpack(header)[3]
        if length > runtime.MAX_FRAME_PAYLOAD:
            raise QualificationError('P353 identity frame exceeds bound')
        frame = codec.decode_frame(header + read_bytes(length))
        if frame.sequence != 3:
            raise QualificationError('P353 identity sequence differs')
        if frame.frame_type == runtime.FRAME_DATA:
            if not frame.payload or len(output) + len(frame.payload) > 4096:
                raise QualificationError('P353 identity output exceeds bound')
            output.extend(frame.payload)
            continue
        if frame.frame_type != runtime.FRAME_EXIT:
            raise QualificationError('P353 identity response type differs')
        flags, code, signal, duration = shell_exchange.parse_exit(codec, frame.payload, len(output))
        if flags or code or signal or not 0 <= duration <= 60000 or not shell_exchange.parent_identity_valid(bytes(output)):
            raise QualificationError('P353 parent identity failed')
        break
    # No read occurs after this write. Full write success proves host dispatch,
    # not receipt by the child, a completed commit, or visible output.
    audit.current_stage = 'display-exec-write'
    tag = hmac.new(key, runtime.AUTH_DOMAIN_EXEC + RUN_ID + nonce + struct.pack('<I', 4) + runtime.DISPLAY_COMMAND, hashlib.sha256).digest()
    write_frame(runtime.FRAME_EXEC, 4, tag + runtime.DISPLAY_COMMAND)
    audit.current_stage = 'dispatch-complete'
    command = observer.CommandResult(3, parent, bytes(output), flags, code, signal, duration)
    return shell_exchange.ShellExchange(observer.SessionResult((command,), audit), 'dispatched', False, None)


def _live(observer, descriptor, key, writer, deadline):
    codec = observer._CODEC
    audit = observer.ExchangeAudit(auth_key_sha256=hashlib.sha256(key).hexdigest())
    def read_bytes(size):
        result = bytearray()
        while len(result) < size:
            left = deadline - time.monotonic()
            if left <= 0:
                raise TimeoutError('P353 dispatch deadline')
            ready, _, _ = select.select([descriptor], [], [], min(.05, left))
            if not ready:
                continue
            try:
                chunk = os.read(descriptor, size - len(result))
            except BlockingIOError:
                continue
            if not chunk:
                raise QualificationError('P353 endpoint EOF before dispatch')
            writer.write_stdout(chunk)
            audit.rx.extend(chunk)
            result.extend(chunk)
        return bytes(result)
    def write_frame(kind, seq, payload):
        codec._send(descriptor, kind, seq, payload, deadline, audit)
    try:
        return _protocol(observer, key, read_bytes, write_frame, audit)
    except BaseException as exc:
        audit.failure_stage = audit.current_stage
        raise QualificationError('P353 stopped before complete dispatch',
            partial_receipt=dict(schema=SCHEMA, proved=False, display_replay_forbidden=True,
                display_effect_occurrence='UNKNOWN', sessions=[]),
            failed_session=DISPLAY_STEP.name, audit=audit, category='dispatch') from exc


def parse_captured_session(observer, rx, tx, key):
    if type(rx) is not bytes or type(tx) is not bytes:
        raise QualificationError('P353 captured bytes required')
    codec = observer._CODEC
    audit = observer.ExchangeAudit(auth_key_sha256=hashlib.sha256(key).hexdigest())
    ro = to = 0
    def read_bytes(size):
        nonlocal ro
        if size < 0 or size > len(rx) - ro:
            raise QualificationError('P353 truncated captured RX')
        value = rx[ro:ro+size]
        ro += size
        audit.rx.extend(value)
        return value
    def write_frame(kind, seq, payload):
        nonlocal to
        value = codec.encode_frame(kind, seq, payload)
        if tx[to:to+len(value)] != value:
            raise QualificationError('P353 captured TX/HMAC differs')
        to += len(value)
        audit.tx.extend(value)
    value = _protocol(observer, key, read_bytes, write_frame, audit)
    if ro != len(rx) or to != len(tx):
        raise QualificationError('P353 trailing or post-dispatch captured data')
    return value


def validate_session_result(shell, step):
    if step != DISPLAY_STEP or shell.outcome != 'dispatched' or shell.cancel_sent is not False or shell.cancel_ack is not None:
        raise QualificationError('P353 dispatch result differs')
    audit = shell.session.audit
    if not (audit.authenticated and audit.banner_seen and audit.ready_seen and audit.challenge_seen) or audit.done_seen or audit.current_stage != 'dispatch-complete':
        raise QualificationError('P353 authenticated prefix incomplete')
    if len(shell.session.commands) != 1:
        raise QualificationError('P353 identity count differs')
    parent = shell.session.commands[0]
    if parent.sequence != 3 or parent.command != runtime.DEFAULT_COMMANDS[0] or any(getattr(parent, k) != 0 for k in ('flags', 'exit_code', 'term_signal')) or not shell_exchange.parent_identity_valid(parent.output):
        raise QualificationError('P353 identity command differs')
    commands = [dict(sequence=3, command=identity(parent.command), output=identity(parent.output),
        flags=0, exit_code=0, term_signal=0, duration_ms=parent.duration_ms),
        dict(sequence=4, command=identity(runtime.DISPLAY_COMMAND), full_request_written=True,
             response_observed=False)]
    return dict(ordinal=1, name=step.name, descriptor_reused=True, command=identity(step.command),
        outcome='dispatched', cancel_sent=False, cancel_ack=None,
        boot_id_sha256=hashlib.sha256(audit.boot_id).hexdigest(),
        nonce_sha256=hashlib.sha256(audit.nonce).hexdigest(),
        rx=dict(offset=0, **identity(bytes(audit.rx))), tx=dict(offset=0, **identity(bytes(audit.tx))),
        commands=commands, semantic=dict(identity_command_complete=True, display_request_dispatched=True,
            display_response_observed=False, display_execution_proved=False,
            visible_panel_output='UNPROVED', framed_session_closed=False))


def _fixed():
    return dict(schema=SCHEMA, contract_id=CONTRACT_ID, target=TARGET, run_id_hex=RUN_ID_HEX,
        initial_observation=INITIAL_OBSERVATION, initial_observation_field=INITIAL_OBSERVATION_FIELD,
        session_count=1, required_session_count=1, total_command_count=2,
        completed_command_count=1, same_fd_session_count=1, same_tty_fd=True,
        reconnect_count=0, physical_reopen_count=0, idle_seconds=0, proved=True,
        proof_scope='authenticated-host-dispatch-only', display_request_dispatched=True,
        display_response_observed=False, display_execution_proved=False, framed_session_closed=False,
        visible_panel_output='UNPROVED', later_action_lease_active=False,
        authority_granted_by_observer=False)


def validate_qualification(value):
    if type(value) is not dict or set(value) != set(_fixed()) | {'sessions', 'expected_boot_sha256'}:
        raise QualificationError('P353 qualification fields differ')
    if any(type(value.get(k)) is not type(v) or value[k] != v for k, v in _fixed().items()):
        raise QualificationError('P353 dispatch constants differ')
    rows = value['sessions']
    if type(rows) is not list or len(rows) != 1:
        raise QualificationError('P353 dispatch row count differs')
    row = rows[0]
    for key in ('boot_id_sha256', 'nonce_sha256'):
        if type(row.get(key)) is not str or not re.fullmatch('[0-9a-f]{64}', row[key]):
            raise QualificationError('P353 digest differs')
    if row['boot_id_sha256'] != value['expected_boot_sha256']:
        raise QualificationError('P353 boot differs')
    expected_sem = dict(identity_command_complete=True, display_request_dispatched=True,
        display_response_observed=False, display_execution_proved=False,
        visible_panel_output='UNPROVED', framed_session_closed=False)
    if row.get('semantic') != expected_sem or row.get('outcome') != 'dispatched' or row.get('ordinal') != 1 or row.get('name') != DISPLAY_STEP.name or row.get('command') != identity(runtime.DISPLAY_COMMAND) or row.get('descriptor_reused') is not True or row.get('cancel_sent') is not False or row.get('cancel_ack') is not None:
        raise QualificationError('P353 dispatch row differs')
    for axis in ('rx', 'tx'):
        part = row.get(axis, {})
        if set(part) != {'offset', 'size', 'sha256'} or part['offset'] != 0 or type(part['size']) is not int or not 0 < part['size'] <= 16384 or type(part['sha256']) is not str or not re.fullmatch('[0-9a-f]{64}', part['sha256']):
            raise QualificationError('P353 raw accounting differs')
    commands = row.get('commands')
    if type(commands) is not list or len(commands) != 2:
        raise QualificationError('P353 command accounting differs')
    parent, dispatch = commands
    if set(parent) != {'sequence','command','output','flags','exit_code','term_signal','duration_ms'} or parent['sequence'] != 3 or parent['command'] != identity(runtime.DEFAULT_COMMANDS[0]) or any(type(parent[k]) is not int or parent[k] != 0 for k in ('flags','exit_code','term_signal')) or type(parent['duration_ms']) is not int or not 0 <= parent['duration_ms'] <= 60000:
        raise QualificationError('P353 identity evidence differs')
    if dispatch != dict(sequence=4,command=identity(runtime.DISPLAY_COMMAND),full_request_written=True,response_observed=False):
        raise QualificationError('P353 display dispatch evidence differs')
    return copy.deepcopy(value)


def qualify(observer, descriptor, auth_key, expected_boot_sha256, seen_nonces, writer, *, deadline):
    now = time.monotonic()
    if type(deadline) not in (int,float) or not math.isfinite(deadline) or not now < deadline <= now + QUALIFICATION_TIMEOUT_SEC or expected_boot_sha256 is not None or type(seen_nonces) is not set or seen_nonces or writer is None:
        raise QualificationError('P353 fresh one-session inputs differ')
    shell = _live(observer, descriptor, auth_key, writer, deadline)
    try:
        row = validate_session_result(shell, DISPLAY_STEP)
        seen_nonces.add(row['nonce_sha256'])
        value = dict(_fixed(), sessions=[row], expected_boot_sha256=row['boot_id_sha256'])
        return QualificationResult(validate_qualification(value), (shell,))
    except BaseException as exc:
        raise QualificationError('P353 dispatched; receipt derivation failed',
            partial_receipt=dict(schema=SCHEMA,proved=False,display_replay_forbidden=True,
                display_request_dispatched=True,display_effect_occurrence='UNKNOWN',sessions=[]),
            failed_session=DISPLAY_STEP.name,audit=shell.session.audit,
            category='post-dispatch-reporting') from exc


def audit_binding():
    return dict(schema=SCHEMA, contract_id=CONTRACT_ID, target=TARGET, run_id_hex=RUN_ID_HEX,
        initial_observation=INITIAL_OBSERVATION, initial_observation_field=INITIAL_OBSERVATION_FIELD,
        session_count=1, same_fd_session_count=1, reconnect_count=0, physical_reopen_count=0,
        idle_seconds=0, total_commands=2, qualification_timeout_sec=60,
        display_child_timeout_sec=60,
        qualification_commands=[dict(ordinal=1,name=DISPLAY_STEP.name,command=identity(DISPLAY_STEP.command),expected_outcome='dispatched')],
        proof_scope='authenticated-host-dispatch-only',visible_panel_output='UNPROVED',
        later_action_lease_active=False,device_contact=False)

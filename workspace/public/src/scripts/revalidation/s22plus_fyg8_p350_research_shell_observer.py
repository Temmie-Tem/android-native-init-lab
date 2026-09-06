#!/usr/bin/env python3
"""Three fixed sessions: USB before, one display command, USB after.

The existing raw protocol parser/exchange are reused. No endpoint selection,
reopen, retry, lease, visual-proof claim or device authority is added here.
"""
from dataclasses import dataclass
from pathlib import Path
import copy
import hashlib
import math
import re
import sys
import time
import types
import s22plus_fyg8_p350_research_shell_runtime as runtime


def _load(name, filename, size, digest, replacements=()):
    path = Path(__file__).with_name(filename)
    source = path.read_bytes()
    if len(source) != size or hashlib.sha256(source).hexdigest() != digest:
        raise ValueError('P350 observer dependency identity differs: ' + filename)
    for before, after in replacements:
        source = source.replace(before, after)
    module = types.ModuleType(name)
    module.__file__ = str(path)
    sys.modules[name] = module
    exec(compile(source, str(path) + '#p350', 'exec'), module.__dict__)
    return module


# Reuse only the existing parser, audit checks, result/error types and exchange.
_base = _load('_p350_protocol', 's22plus_fyg8_p347_research_shell_observer.py',
    3084, 'a3fd9c964f3a9d40892c73c65b162340f9373c755c772957d71b66d0fe1bac0a',
    ((b'P347', b'P350'), (b'p347', b'p350')))
_display_exchange = _load('_p350_display_exchange', 's22plus_fyg8_research_shell_exchange.py',
    10870, 'ac3b47884ed29404b5afc047557486b5c90ece2e85dc799123d100a7238df2c3')
_display_exchange.SESSION_TIMEOUT_SEC = 75.0
SCHEMA = 's22plus-fyg8-p350-display-qualification-v1'
CONTRACT_ID = 's22plus-fyg8-p350-display-qualification-observer-v1'
TARGET = runtime.TARGET
RUN_ID = runtime.P350_RUN_ID
RUN_ID_HEX = runtime.P350_RUN_ID_HEX
INITIAL_OBSERVATION = 'p350_display_qualification'
INITIAL_OBSERVATION_FIELD = 'p350_display'
SESSION_COUNT = SAME_FD_SESSION_COUNT = TOTAL_SESSIONS = MAX_SESSIONS = MAX_INITIAL_SESSIONS = 3
RECONNECT_COUNT = MAX_RECONNECTS = PHYSICAL_REOPEN_COUNT = IDLE_SECONDS = 0
TOTAL_COMMANDS = 9
QUALIFICATION_TIMEOUT_SEC = 150.0
QualificationError = _base.QualificationError
QualificationResult = _base.QualificationResult
parse_captured_session = _base.parse_captured_session
identity = _base.identity


@dataclass(frozen=True)
class QualificationStep:
    ordinal: int
    name: str
    command: bytes
    expected_outcome: str = 'ok'


PRE_MARKER = b'P350-BEFORE-DISPLAY\n65534\n'
POST_MARKER = b'P350-AFTER-DISPLAY\n65534\n'
PRE_STEP = QualificationStep(1, 'usb-before-display', b"printf 'P350-BEFORE-DISPLAY\\n'; /bin/busybox id -u")
DISPLAY_STEP = QualificationStep(2, 'display-once', runtime.DISPLAY_COMMAND)
POST_STEP = QualificationStep(3, 'usb-after-display', b"printf 'P350-AFTER-DISPLAY\\n'; /bin/busybox id -u")
QUALIFICATION_COMMANDS = (PRE_STEP, DISPLAY_STEP, POST_STEP)


def display_output(crtc):
    if type(crtc) is not int or not 1 <= crtc <= 0xffffffff:
        raise QualificationError('P350 CRTC identifier differs')
    rows = []
    for i in range(9):
        rows.extend((f'DISPLAY_LOAD_BEGIN index={i}\n', f'DISPLAY_LOAD_DONE index={i}\n'))
    rows.extend(f'DISPLAY_FLIP run={RUN_ID_HEX} counter={i} crtc={crtc} completed=1\n' for i in range(10))
    rows.append(f'DISPLAY_DONE run={RUN_ID_HEX} completed_frames=10 disabled=1\n')
    return ''.join(rows).encode('ascii')


def validate_session_result(shell, step):
    if step not in QUALIFICATION_COMMANDS:
        raise QualificationError('P350 fixed step differs')
    session = getattr(shell, 'session', None)
    audit = getattr(session, 'audit', None)
    _base._session_audit_checks(audit)
    commands = getattr(session, 'commands', ())
    expected = (runtime.DEFAULT_COMMANDS[0], step.command, runtime.DEFAULT_COMMANDS[2])
    if len(commands) != 3 or shell.outcome != 'ok' or shell.cancel_sent is not False or shell.cancel_ack is not None:
        raise QualificationError('P350 session failed or cancelled')
    rows = []
    for sequence, item, command in zip(range(3, 6), commands, expected):
        if item.sequence != sequence or item.command != command or type(item.output) is not bytes or any(type(getattr(item,k)) is not int or getattr(item,k)!=0 for k in ('flags','exit_code','term_signal')) or type(item.duration_ms) is not int or item.duration_ms < 0:
            raise QualificationError('P350 command binding/status differs')
        rows.append(dict(sequence=sequence, command=identity(command), output=identity(item.output),
            flags=0, exit_code=0, term_signal=0, duration_ms=item.duration_ms))
    if not _display_exchange.parent_identity_valid(commands[0].output) or commands[2].output != b'P328-NONCE ' + RUN_ID_HEX.encode() + b'\n':
        raise QualificationError('P350 parent/run witness differs')
    middle = commands[1]
    if step == DISPLAY_STEP:
        match = re.search(rb' crtc=([0-9]+) completed=1\n', middle.output)
        if match is None or len(match[1]) > 10:
            raise QualificationError('P350 display completion is absent')
        crtc = int(match[1])
        if middle.output != display_output(crtc) or not 10000 <= middle.duration_ms <= 60000:
            raise QualificationError('P350 display output/timing differs')
        semantic = dict(module_insertions=9, completed_frames=10, counters=list(range(10)),
            crtc=crtc, disabled=True, visible_panel_output='UNPROVED')
    else:
        if middle.output != (PRE_MARKER if step == PRE_STEP else POST_MARKER):
            raise QualificationError('P350 USB/read-only witness differs')
        semantic = dict(usb_witness=step.name, normal_child_uid=65534)
    return dict(ordinal=step.ordinal, name=step.name, descriptor_reused=True,
        command=identity(step.command), outcome='ok', cancel_sent=False, cancel_ack=None,
        boot_id_sha256=hashlib.sha256(audit.boot_id).hexdigest(),
        nonce_sha256=hashlib.sha256(audit.nonce).hexdigest(),
        rx=dict(offset=0, **identity(_base._audit_bytes(audit, 'rx'))),
        tx=dict(offset=0, **identity(_base._audit_bytes(audit, 'tx'))),
        commands=rows, semantic=semantic)


def validate_qualification(value):
    if not isinstance(value, dict):
        raise QualificationError('P350 qualification must be an object')
    fixed = dict(schema=SCHEMA, contract_id=CONTRACT_ID, target=TARGET,
        run_id_hex=RUN_ID_HEX, initial_observation=INITIAL_OBSERVATION,
        initial_observation_field=INITIAL_OBSERVATION_FIELD,
        session_count=3, required_session_count=3, total_command_count=9,
        same_fd_session_count=3, same_tty_fd=True, reconnect_count=0,
        physical_reopen_count=0, idle_seconds=0, proved=True, display_consumed=True,
        visible_panel_output='UNPROVED', later_action_lease_active=False,
        authority_granted_by_observer=False)
    if any(type(value.get(k)) is not type(v) or value.get(k) != v for k, v in fixed.items()):
        raise QualificationError('P350 qualification constants differ')
    rows = value.get('sessions')
    if not isinstance(rows, list) or len(rows) != 3:
        raise QualificationError('P350 session count differs')
    boot = value.get('expected_boot_sha256')
    if not isinstance(boot,str) or not re.fullmatch('[0-9a-f]{64}',boot):
        raise QualificationError('P350 boot digest differs')
    nonces = set(); rx_end = tx_end = 0
    for step,row in zip(QUALIFICATION_COMMANDS,rows):
        checks=dict(ordinal=step.ordinal,name=step.name,command=identity(step.command),
            outcome='ok',cancel_sent=False,cancel_ack=None,descriptor_reused=True,boot_id_sha256=boot)
        if any(type(row.get(k)) is not type(v) or row.get(k)!=v for k,v in checks.items()):
            raise QualificationError('P350 row identity/boot differs')
        nonce=row.get('nonce_sha256')
        if not isinstance(nonce,str) or not re.fullmatch('[0-9a-f]{64}',nonce) or nonce in nonces:
            raise QualificationError('P350 nonce duplicate/malformed')
        nonces.add(nonce)
        for axis,offset in [('rx',rx_end),('tx',tx_end)]:
            part=row.get(axis,{})
            if part.get('offset')!=offset or type(part.get('size')) is not int or part['size']<=0 or not isinstance(part.get('sha256'),str) or not re.fullmatch('[0-9a-f]{64}',part['sha256']):
                raise QualificationError('P350 raw stream accounting differs')
        rx_end+=row['rx']['size'];tx_end+=row['tx']['size']
        commands=row.get('commands',[])
        if len(commands)!=3:raise QualificationError('P350 command count differs')
        expected=(runtime.DEFAULT_COMMANDS[0],step.command,runtime.DEFAULT_COMMANDS[2])
        for sequence,command,c in zip(range(3,6),expected,commands):
            if c.get('sequence')!=sequence or c.get('command')!=identity(command) or any(type(c.get(k)) is not int or c[k]!=0 for k in ('flags','exit_code','term_signal')) or type(c.get('duration_ms')) is not int or c['duration_ms']<0:
                raise QualificationError('P350 command row failed')
        if commands[2]['output']!=identity(b'P328-NONCE '+RUN_ID_HEX.encode()+b'\n'):
            raise QualificationError('P350 fixed run output differs')
        if step==DISPLAY_STEP:
            sem=row.get('semantic',{});crtc=sem.get('crtc')
            expected_sem=dict(module_insertions=9,completed_frames=10,counters=list(range(10)),crtc=crtc,disabled=True,visible_panel_output='UNPROVED')
            if sem!=expected_sem or commands[1]['output']!=identity(display_output(crtc)) or not 10000<=commands[1]['duration_ms']<=60000:
                raise QualificationError('P350 completed display evidence differs')
        elif row.get('semantic')!=dict(usb_witness=step.name,normal_child_uid=65534) or commands[1]['output']!=identity(PRE_MARKER if step==PRE_STEP else POST_MARKER):
            raise QualificationError('P350 USB witness differs')
    return copy.deepcopy(value)


def qualify(observer,descriptor,auth_key,expected_boot_sha256,seen_nonces,writer,*,deadline):
    now=time.monotonic()
    if type(deadline) not in (int,float) or not math.isfinite(deadline) or not now<deadline<=now+QUALIFICATION_TIMEOUT_SEC:
        raise QualificationError('P350 observation deadline differs')
    rows=[];parsed=[];boot=expected_boot_sha256
    for step in QUALIFICATION_COMMANDS:
        audit=None;before=_base._writer_sizes(writer)
        try:
            module=_display_exchange if step==DISPLAY_STEP else _base.shell_exchange
            shell=module.exchange(observer,descriptor,auth_key,step.command,boot,seen_nonces,writer,deadline=deadline)
            audit=shell.session.audit
            row=validate_session_result(shell,step)
            if boot is None:boot=row['boot_id_sha256']
            if row['boot_id_sha256']!=boot:raise QualificationError('P350 changed boot')
            row['rx']['offset']=sum(r['rx']['size'] for r in rows)
            row['tx']['offset']=sum(r['tx']['size'] for r in rows)
            span=_base._capture_span(before,_base._writer_sizes(writer))
            if span is not None:row['raw_capture']=span
            rows.append(row);parsed.append(shell)
        except Exception as exc:
            raise QualificationError('P350 stopped at '+step.name,
                partial_receipt=dict(schema=SCHEMA,proved=False,display_replay_forbidden=True,
                    display_effect_occurrence='UNKNOWN',sessions=rows,failed_step=step.name,recovery_required=True),
                failed_session=step.name,audit=getattr(exc,'audit',None) or audit,
                category='display-or-transport',sessions=tuple(parsed)) from exc
    receipt=dict(schema=SCHEMA,contract_id=CONTRACT_ID,target=TARGET,run_id_hex=RUN_ID_HEX,
        initial_observation=INITIAL_OBSERVATION,initial_observation_field=INITIAL_OBSERVATION_FIELD,
        sessions=rows,expected_boot_sha256=boot,session_count=3,required_session_count=3,
        total_command_count=9,same_fd_session_count=3,same_tty_fd=True,reconnect_count=0,
        physical_reopen_count=0,idle_seconds=0,proved=True,display_consumed=True,
        visible_panel_output='UNPROVED',later_action_lease_active=False,authority_granted_by_observer=False)
    return QualificationResult(validate_qualification(receipt),tuple(parsed))


def audit_binding():
    return dict(schema=SCHEMA,contract_id=CONTRACT_ID,target=TARGET,run_id_hex=RUN_ID_HEX,
        initial_observation=INITIAL_OBSERVATION,initial_observation_field=INITIAL_OBSERVATION_FIELD,
        session_count=3,same_fd_session_count=3,reconnect_count=0,physical_reopen_count=0,
        idle_seconds=0,total_commands=9,qualification_timeout_sec=150,
        display_session_timeout_sec=75,display_child_timeout_sec=60,
        qualification_commands=[dict(ordinal=s.ordinal,name=s.name,command=identity(s.command),expected_outcome=s.expected_outcome) for s in QUALIFICATION_COMMANDS],
        visible_panel_output='UNPROVED',later_action_lease_active=False,device_contact=False)

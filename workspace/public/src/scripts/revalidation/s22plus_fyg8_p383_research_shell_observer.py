"""One fixed native health check on each explicitly bound roundtrip arrival.

Endpoint ownership and the second-arrival freshness check belong to the F1
owner. This observer opens no transport and retries no request or session.
"""
from s22plus_fyg8_p383_namespace import load_template
load_template(globals())
import s22plus_native_baseline_health_v1 as health

PROOF_SCOPE = 'fixed-native-health-and-authenticated-return-control'
QUALIFICATION_COMMANDS = (QualificationStep(1, 'native-baseline-health',
    health.COMMAND, health.STDOUT, health.STDERR),)
TOTAL_COMMANDS = 1
_STATUS = struct.pack('<8I', 3, 0, 0, 0, 0,
                      len(health.STDOUT) + len(health.STDERR), 0, 3)


def _qualification(commands, events):
    if len(commands) != 1:
        return False
    row = commands[0]
    terminal = row.get('terminal')
    return (row.get('sequence') == 3 and row.get('timeout_ms') == 15000
        and row.get('command') == identity(health.COMMAND)
        and row.get('cwd') == identity(b'/')
        and row.get('accepted') is True and row.get('rejected') is False
        and row.get('stdout') == identity(health.STDOUT)
        and row.get('stderr') == identity(health.STDERR)
        and type(terminal) is list and len(terminal) == 7
        and all(type(v) is int for v in terminal)
        and terminal[:4] == [3, 0, 0, 0] and terminal[5] == 0
        and [(k, n, p) for k, n, p in events if k == wire.STATUS_REPLY]
            == [(wire.STATUS_REPLY, 4, _STATUS)])


_base_receipt = _receipt


def _receipt(io, session, events):
    value = _base_receipt(io, session, events)
    value['qualification_events'] = [dict(kind=k, sequence=n, payload_hex=p.hex())
        for k, n, p in events if k == wire.STATUS_REPLY]
    return value


def validate_qualification(value):
    if type(value) is not dict:
        raise QualificationError('native health receipt is absent')
    exact = dict(schema=SCHEMA, proved=True, run_id_hex=RUN_ID_HEX,
        session_count=1, command_count=1, request_count=3,
        qualified_command_count=1, control_sequence=5,
        root_ready=[1, 600000, 300000, 1048576, 767, 255, 0, 0],
        control_acceptance_observed=True, control_ack_scope='acceptance-only',
        same_tty_fd=True, physical_reopen_count=0, console_reentry=False,
        all_commands_terminal_or_rejected=True,
        qualification_events=[dict(kind=wire.STATUS_REPLY, sequence=4,
                                   payload_hex=_STATUS.hex())],
        preparation=dict(schema='s22plus-fyg8-p383-preparation-progress-v1',
            records=[dict(stage=stage, event=event, code=0)
                     for stage, event in progress.EXPECTED], failure=None, complete=True))
    # JSON identity keeps booleans and floating values distinct from integers.
    import json
    if any(json.dumps(value.get(k), sort_keys=True) != json.dumps(v, sort_keys=True)
           for k, v in exact.items()):
        raise QualificationError('native health receipt profile differs')
    if not _qualification(value.get('commands', []),
                          [(wire.STATUS_REPLY, 4, _STATUS)]):
        raise QualificationError('native health command evidence differs')
    return copy.deepcopy(value)


def qualify(codec, descriptor, auth_key, expected_boot_sha256, seen_nonces, writer,
            *, deadline, before_control, evidence, interactive=None):
    if (expected_boot_sha256 is not None or seen_nonces
            or not time.monotonic() < deadline <= time.monotonic() + QUALIFICATION_TIMEOUT_SEC):
        raise QualificationError('native health fresh session inputs differ')
    io = IO(codec, auth_key, fd=descriptor, writer=writer, deadline=deadline)
    session = None
    events = []
    try:
        io.handshake()
        seen_nonces.add(health.digest(io.audit.nonce))
        session = wire.Session(descriptor, auth_key, RUN_ID, io.audit.nonce,
            Path(evidence), on_rx=io.capture, on_tx=io.audit.tx.extend)
        health.run_console_checks(session, events,
                                  deadline=min(deadline, time.monotonic() + 29.9))
        # The owner permits only an empty plan for this first qualification.
        if interactive is not None:
            interactive(session, events, deadline)
        health.validate_console(session, events)
        request = dict(run_id_hex=RUN_ID_HEX, mode='download', sequence=5,
            nonce_sha256=health.digest(io.audit.nonce),
            kernel_boot_identity_sha256=health.digest(io.audit.boot_id),
            boot_id_semantic=control.BOOT_ID_SEMANTIC,
            boot_receipt_semantic=control.BOOT_RECEIPT_SEMANTIC)
        before_control(request)
        seq = session.send(wire.CONTROL)
        while not any(k == wire.CONTROL_ACK and n == seq for k, n, p in events):
            if time.monotonic() >= deadline:
                raise TimeoutError('native health CONTROL original deadline')
            events.extend(session.poll())
            time.sleep(.001)
        io.audit.done_seen = True
        io.audit.current_stage = 'control-accepted'
        value = _receipt(io, session, events)
        validate_qualification(value)
        return QualificationResult(value,
            (types.SimpleNamespace(session=types.SimpleNamespace(audit=io.audit)),))
    except BaseException as exc:
        io.audit.failure_stage = io.audit.current_stage
        partial = (_receipt(io, session, events) if session is not None else
                   dict(schema=SCHEMA, proved=False, sessions=[],
                        preparation=io.preparation.projection()))
        partial['proved'] = False
        raise QualificationError('native health stopped; no replay',
            audit=io.audit, partial_receipt=partial) from exc
    finally:
        if session is not None:
            session.close()


def audit_binding():
    return dict(schema=SCHEMA, contract_id=CONTRACT_ID, session_count=1,
        same_fd_session_count=1, reconnect_count=0,
        qualification_timeout_sec=QUALIFICATION_TIMEOUT_SEC,
        root_console=True, qualified_exec_count=1, interactive_commands=False,
        control_ack_scope='acceptance-only', raw_replay_required=True,
        live_authorized=False)

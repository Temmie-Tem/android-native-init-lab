"""P363 sealed successor binding; no device authority."""
from s22plus_fyg8_p363_namespace import load
load(globals())

# The sealed P353 prefix remains OPEN/authentication/kernel-BOOT/identity/EXEC.
# P363 is a bidirectional return protocol, with independent proof semantics.
import s22plus_fyg8_p363_return_spec as control
_dispatch_prefix_protocol = _protocol
_prefix_session_validator = validate_session_result
SCHEMA = 's22plus-fyg8-p363-native-return-control-v1'
CONTRACT_ID = 's22plus-fyg8-p363-native-return-control-observer-v1'
INITIAL_OBSERVATION = 'p363_native_return_control'
INITIAL_OBSERVATION_FIELD = 'p363_native_return_control'
TOTAL_COMMANDS = 3
DISPLAY_STEP = QualificationStep(1, 'native-download-control', runtime.DISPLAY_COMMAND,
    expected_outcome='control-accepted')
QUALIFICATION_COMMANDS = (DISPLAY_STEP,)


def _tag(key, domain, nonce, body):
    return hmac.new(key, domain + RUN_ID + nonce +
        struct.pack('<I', control.CONTROL_SEQUENCE) + body, hashlib.sha256).digest()


def _protocol(observer, key, read_bytes, write_frame, audit, *, before_control=None):
    shell = _dispatch_prefix_protocol(observer, key, read_bytes, write_frame, audit)
    codec = observer._CODEC
    def status(kind, domain, expected_body=None):
        header = read_bytes(codec.HEADER.size)
        length = codec.HEADER.unpack(header)[3]
        if length != 36:
            raise QualificationError('P363 control status length differs')
        payload = codec._expect(codec.decode_frame(header + read_bytes(length)),
            kind, control.CONTROL_SEQUENCE)
        body = payload[:4]
        if (expected_body is not None and body != expected_body) or not hmac.compare_digest(payload[4:],
                _tag(key, domain, audit.nonce, body)):
            raise QualificationError('P363 control status authentication differs')
        return body
    audit.current_stage = 'ten-submissions-and-return-ready-read'
    ready = status(control.FRAME_CONTROL_READY, control.DOMAIN_READY)
    if ready[0] != 1 or ready[2] != 1 or not 0 <= ready[1] <= 10 or ready[3] not in (0,1) or (ready[3] == 0 and ready[1] != 10):
        raise QualificationError('P363 readiness state differs')
    audit.control_ready_body = ready
    audit.current_stage = 'control-intent-before-any-control-byte'
    if before_control is not None:
        before_control(dict(run_id_hex=RUN_ID_HEX, mode='download',
            sequence=control.CONTROL_SEQUENCE,
            nonce_sha256=hashlib.sha256(audit.nonce).hexdigest(),
            kernel_boot_identity_sha256=hashlib.sha256(audit.boot_id).hexdigest(),
            boot_id_semantic=control.BOOT_ID_SEMANTIC,
            boot_receipt_semantic=control.BOOT_RECEIPT_SEMANTIC))
    audit.current_stage = 'control-write'
    write_frame(control.FRAME_CONTROL, control.CONTROL_SEQUENCE,
        control.CONTROL_BODY + _tag(key,control.DOMAIN_CONTROL,audit.nonce,control.CONTROL_BODY))
    audit.current_stage = 'control-ack-read'
    status(control.FRAME_CONTROL_ACK,control.DOMAIN_ACK,bytes((1,0,ready[1],ready[3])))
    audit.current_stage = 'control-accepted'
    return shell_exchange.ShellExchange(shell.session,'control-accepted',False,None)


def _live(observer, descriptor, key, writer, deadline, *, before_control):
    codec = observer._CODEC
    audit = observer.ExchangeAudit(auth_key_sha256=hashlib.sha256(key).hexdigest())
    def read_bytes(size):
        result = bytearray()
        while len(result) < size:
            left = deadline - time.monotonic()
            if left <= 0:
                raise TimeoutError('P363 control deadline')
            ready, _, _ = select.select([descriptor], [], [], min(.05, left))
            if not ready:
                continue
            try:
                chunk = os.read(descriptor, size-len(result))
            except BlockingIOError:
                continue
            if not chunk:
                raise QualificationError('P363 endpoint EOF')
            writer.write_stdout(chunk)
            audit.rx.extend(chunk)
            result.extend(chunk)
        return bytes(result)
    def write_frame(kind, seq, payload):
        codec._send(descriptor,kind,seq,payload,deadline,audit)
    try:
        return _protocol(observer,key,read_bytes,write_frame,audit,before_control=before_control)
    except BaseException as exc:
        audit.failure_stage = audit.current_stage
        raise QualificationError('P363 return exchange stopped; no replay',
            partial_receipt=dict(schema=SCHEMA,proved=False,display_replay_forbidden=True,
                control_replay_forbidden=True,control_effect_occurrence='UNKNOWN',sessions=[]),
            failed_session=DISPLAY_STEP.name,audit=audit,category='return-control') from exc


def _semantic(swaps, child_exited):
    return dict(identity_command_complete=True,display_request_dispatched=True,
        display_response_observed=True,display_submitted_swaps=swaps,
        display_child_exited_before_ready=child_exited,
        visible_panel_output='UNPROVED',return_module_readiness=True,
        control_requested_mode='download',control_acceptance_observed=True,
        control_ack_scope='acceptance-only',software_download_arrival='UNPROVED',
        framed_session_closed=False,kernel_boot_id_semantic=control.BOOT_ID_SEMANTIC,
        boot_receipt_semantic=control.BOOT_RECEIPT_SEMANTIC)


def _request_rows(parent, swaps, child_exited):
    return [dict(sequence=3,command=identity(parent.command),output=identity(parent.output),
        flags=0,exit_code=0,term_signal=0,duration_ms=parent.duration_ms),
        dict(sequence=4,command=identity(runtime.DISPLAY_COMMAND),full_request_written=True,
            response_observed=True,submitted_swaps=swaps,child_exited_before_ready=child_exited),
        dict(sequence=control.CONTROL_SEQUENCE,command=identity(control.CONTROL_BODY),
            full_request_written=True,acceptance_observed=True,mode='download')]


def validate_session_result(shell, step):
    if step != DISPLAY_STEP or shell.outcome != 'control-accepted' or shell.cancel_sent is not False or shell.cancel_ack is not None:
        raise QualificationError('P363 control result differs')
    audit = shell.session.audit
    if not (audit.authenticated and audit.banner_seen and audit.ready_seen and audit.challenge_seen) or audit.done_seen or audit.current_stage != 'control-accepted':
        raise QualificationError('P363 authenticated control incomplete')
    if len(shell.session.commands) != 1:
        raise QualificationError('P363 identity count differs')
    parent = shell.session.commands[0]
    if parent.sequence != 3 or parent.command != runtime.DEFAULT_COMMANDS[0] or any(getattr(parent,k) != 0 for k in ('flags','exit_code','term_signal')) or not shell_exchange.parent_identity_valid(parent.output):
        raise QualificationError('P363 identity command differs')
    ready = getattr(audit,'control_ready_body',b'')
    if type(ready) is not bytes or len(ready) != 4 or ready[0] != 1 or ready[2] != 1 or ready[1] > 10 or ready[3] not in (0,1) or (ready[3] == 0 and ready[1] != 10):
        raise QualificationError('P363 signed readiness missing')
    return dict(ordinal=1,name=step.name,descriptor_reused=True,command=identity(step.command),
        outcome='control-accepted',cancel_sent=False,cancel_ack=None,
        boot_id_sha256=hashlib.sha256(audit.boot_id).hexdigest(),
        nonce_sha256=hashlib.sha256(audit.nonce).hexdigest(),
        rx=dict(offset=0,**identity(bytes(audit.rx))),tx=dict(offset=0,**identity(bytes(audit.tx))),
        commands=_request_rows(parent,ready[1],bool(ready[3])),semantic=_semantic(ready[1],bool(ready[3])))


def _fixed():
    return dict(schema=SCHEMA,contract_id=CONTRACT_ID,target=TARGET,run_id_hex=RUN_ID_HEX,
        initial_observation=INITIAL_OBSERVATION,initial_observation_field=INITIAL_OBSERVATION_FIELD,
        session_count=1,required_session_count=1,total_command_count=3,
        completed_command_count=1,same_fd_session_count=1,same_tty_fd=True,
        reconnect_count=0,physical_reopen_count=0,idle_seconds=0,proved=True,
        proof_scope='submitted-swap-count-and-authenticated-control-acceptance',
        display_request_dispatched=True,display_response_observed=True,
        control_acceptance_observed=True,
        control_requested_mode='download',software_download_arrival='UNPROVED',
        framed_session_closed=False,visible_panel_output='UNPROVED',
        kernel_boot_id_semantic=control.BOOT_ID_SEMANTIC,
        boot_receipt_semantic=control.BOOT_RECEIPT_SEMANTIC,
        later_action_lease_active=False,authority_granted_by_observer=False)


def validate_qualification(value):
    if type(value) is not dict or set(value) != set(_fixed()) | {'sessions','expected_boot_sha256'}:
        raise QualificationError('P363 qualification fields differ')
    if any(type(value.get(k)) is not type(v) or value[k] != v for k,v in _fixed().items()):
        raise QualificationError('P363 proof constants differ')
    rows = value['sessions']
    if type(rows) is not list or len(rows) != 1:
        raise QualificationError('P363 session count differs')
    row = rows[0]
    if type(row) is not dict or set(row) != {'ordinal','name','descriptor_reused','command','outcome','cancel_sent','cancel_ack','boot_id_sha256','nonce_sha256','rx','tx','commands','semantic'}:
        raise QualificationError('P363 row fields differ')
    for key in ('boot_id_sha256','nonce_sha256'):
        if type(row.get(key)) is not str or not re.fullmatch('[0-9a-f]{64}',row[key]):
            raise QualificationError('P363 digest differs')
    if row['boot_id_sha256'] != value['expected_boot_sha256']:
        raise QualificationError('P363 boot digest differs')
    semantic = row['semantic']
    swaps = semantic.get('display_submitted_swaps') if type(semantic) is dict else None
    child_exited = semantic.get('display_child_exited_before_ready') if type(semantic) is dict else None
    if type(swaps) is not int or not 0 <= swaps <= 10 or type(child_exited) is not bool or (not child_exited and swaps != 10):
        raise QualificationError('P363 submitted-swap/child state differs')
    if row['semantic'] != _semantic(swaps,child_exited) or row['outcome'] != 'control-accepted' or type(row['ordinal']) is not int or row['ordinal'] != 1 or row['name'] != DISPLAY_STEP.name or row['command'] != identity(runtime.DISPLAY_COMMAND) or row['descriptor_reused'] is not True or row['cancel_sent'] is not False or row['cancel_ack'] is not None:
        raise QualificationError('P363 control semantic differs')
    for axis in ('rx','tx'):
        part = row[axis]
        if type(part) is not dict or set(part) != {'offset','size','sha256'} or type(part['offset']) is not int or part['offset'] != 0 or type(part['size']) is not int or not 0 < part['size'] <= 16384 or type(part['sha256']) is not str or not re.fullmatch('[0-9a-f]{64}',part['sha256']):
            raise QualificationError('P363 stream accounting differs')
    commands = row['commands']
    if type(commands) is not list or len(commands) != 3:
        raise QualificationError('P363 command count differs')
    parent = commands[0]
    if type(parent) is not dict or set(parent) != {'sequence','command','output','flags','exit_code','term_signal','duration_ms'} or type(parent['sequence']) is not int or parent['sequence'] != 3 or parent['command'] != identity(runtime.DEFAULT_COMMANDS[0]) or any(type(parent[k]) is not int or parent[k] != 0 for k in ('flags','exit_code','term_signal')) or type(parent['duration_ms']) is not int or not 0 <= parent['duration_ms'] <= 60000:
        raise QualificationError('P363 identity accounting differs')
    output = parent['output']
    if type(output) is not dict or set(output) != {'size','sha256'} or type(output['size']) is not int or not 0 < output['size'] <= 4096 or type(output['sha256']) is not str or not re.fullmatch('[0-9a-f]{64}',output['sha256']):
        raise QualificationError('P363 identity output differs')
    if commands[1] != dict(sequence=4,command=identity(runtime.DISPLAY_COMMAND),full_request_written=True,response_observed=True,submitted_swaps=swaps,child_exited_before_ready=child_exited) or commands[2] != dict(sequence=5,command=identity(control.CONTROL_BODY),full_request_written=True,acceptance_observed=True,mode='download'):
        raise QualificationError('P363 request accounting differs')
    return copy.deepcopy(value)


def qualify(observer, descriptor, auth_key, expected_boot_sha256, seen_nonces, writer, *, deadline, before_control):
    now = time.monotonic()
    if type(deadline) not in (int,float) or not math.isfinite(deadline) or not now < deadline <= now + QUALIFICATION_TIMEOUT_SEC or expected_boot_sha256 is not None or type(seen_nonces) is not set or seen_nonces or writer is None or not callable(before_control):
        raise QualificationError('P363 fresh one-session inputs differ')
    shell = _live(observer,descriptor,auth_key,writer,deadline,before_control=before_control)
    try:
        row = validate_session_result(shell,DISPLAY_STEP)
        seen_nonces.add(row['nonce_sha256'])
        result = dict(_fixed(),sessions=[row],expected_boot_sha256=row['boot_id_sha256'])
        return QualificationResult(validate_qualification(result),(shell,))
    except BaseException as exc:
        raise QualificationError('P363 acceptance observed; receipt derivation failed',
            partial_receipt=dict(schema=SCHEMA,proved=False,control_replay_forbidden=True,
                display_replay_forbidden=True,control_effect_occurrence='UNKNOWN',sessions=[]),
            failed_session=DISPLAY_STEP.name,audit=shell.session.audit,
            category='post-control-reporting') from exc


def audit_binding():
    return dict(schema=SCHEMA,contract_id=CONTRACT_ID,target=TARGET,run_id_hex=RUN_ID_HEX,
        initial_observation=INITIAL_OBSERVATION,initial_observation_field=INITIAL_OBSERVATION_FIELD,
        session_count=1,same_fd_session_count=1,reconnect_count=0,physical_reopen_count=0,
        idle_seconds=0,total_commands=3,qualification_timeout_sec=60,display_child_timeout_sec=60,
        qualification_commands=[dict(ordinal=1,name=DISPLAY_STEP.name,command=identity(DISPLAY_STEP.command),expected_outcome='control-accepted')],
        proof_scope='submitted-swap-count-and-authenticated-control-acceptance',
        visible_panel_output='UNPROVED',kernel_boot_id_semantic=control.BOOT_ID_SEMANTIC,
        control_mode='download',control_intent_required_before_write=True,
        later_action_lease_active=False,device_contact=False)

"""P370 one planned pre-CONTROL handoff; H0 only until approved."""
from s22plus_fyg8_p370_namespace import load
load(globals())

import types
SESSION_COUNT=2
TOTAL_COMMANDS=4
SCHEMA='s22plus-fyg8-p370-two-leg-return-v1'
PROOF_SCOPE='two-authenticated-legs-one-display-and-control'
FIRST_STEP=QualificationStep(1,'launch-and-handoff',runtime.DISPLAY_COMMAND,'detach-accepted')
SECOND_STEP=QualificationStep(2,'resume-and-control',control.CONTROL_BODY,'control-accepted')
QUALIFICATION_COMMANDS=(FIRST_STEP,SECOND_STEP)


def _handoff_tag(key,domain,nonce,sequence,body):
    return hmac.new(key,domain+RUN_ID+nonce+struct.pack('<I',sequence)+body,hashlib.sha256).digest()


class _PairIO:
    def __init__(self,codec,key,*,fd=None,writer=None,deadline=None,reopen=None,
                 before_handoff=None,before_control=None,rx=None,tx=None):
        self.codec=codec;self.key=key;self.fd=fd;self.writer=writer;self.deadline=deadline
        self.reopen=reopen;self.before_handoff=before_handoff;self.before_control=before_control
        self.raw_rx=rx;self.raw_tx=tx;self.positions=[0,0];self.audits=[];self.shells=[]
        self.audit=None;self.start_leg()
        self.audits[0].native_progress=progress.Progress()
        self.audits[0].progress_owner=self.audits[0]
    def start_leg(self):
        audit=self.codec.ExchangeAudit(auth_key_sha256=hashlib.sha256(self.key).hexdigest())
        if self.audits:
            audit.native_progress=self.audits[0].native_progress
            audit.progress_owner=self.audits[0]
        self.audits.append(audit);self.audit=audit
        return audit
    def read(self,size):
        if self.raw_rx is not None:
            start=self.positions[0];part=self.raw_rx[start:start+size];self.positions[0]+=len(part)
            self.audit.rx.extend(part)
            if len(part)!=size:raise EOFError('retained RX ended')
            return part
        result=bytearray()
        while len(result)<size:
            left=self.deadline-time.monotonic()
            if left<=0:raise TimeoutError('P370 original observation deadline')
            ready,_,_=select.select([self.fd],[],[],min(.05,left))
            if not ready:continue
            try:part=os.read(self.fd,size-len(result))
            except BlockingIOError:continue
            if not part:raise QualificationError('P370 endpoint EOF')
            self.writer.write_stdout(part);self.audit.rx.extend(part);result.extend(part)
        return bytes(result)
    def write(self,kind,sequence,payload):
        if kind==runtime.FRAME_EXEC and sequence==4:self.audit.parent_identity_verified=True
        if self.raw_tx is not None:
            wire=self.codec._CODEC.encode_frame(kind,sequence,payload)
            start=self.positions[1];part=self.raw_tx[start:start+len(wire)]
            if part!=wire[:len(part)]:raise QualificationError('retained TX differs')
            self.positions[1]+=len(part);self.audit.tx.extend(part)
            if len(part)!=len(wire):raise EOFError('retained TX ended')
        else:self.codec._CODEC._send(self.fd,kind,sequence,payload,self.deadline,self.audit)
        if kind==runtime.FRAME_EXEC and sequence==4:self.audit.display_frame_fully_written=True
    def frame(self,kind,sequence,*,diagnostics=False):
        c=self.codec._CODEC
        while True:
            header=self.read(c.HEADER.size);length=c.HEADER.unpack(header)[3]
            if length>100:raise QualificationError('P370 bounded frame differs')
            frame=c.decode_frame(header+self.read(length))
            if diagnostics and frame.frame_type==control.FRAME_DIAGNOSTIC:
                self.audit.native_progress.accept(frame,self.key,self.audit.nonce);continue
            return c._expect(frame,kind,sequence)
    def status(self,kind,sequence,domain,expected,*,diagnostics=False):
        payload=self.frame(kind,sequence,diagnostics=diagnostics)
        if len(payload)!=36 or payload[:4]!=expected or not hmac.compare_digest(payload[4:],
            _handoff_tag(self.key,domain,self.audit.nonce,sequence,payload[:4])):
            raise QualificationError('P370 authenticated status differs')
        return payload[:4]


def _request(audit,sequence,mode):
    return dict(run_id_hex=RUN_ID_HEX,mode=mode,sequence=sequence,
        nonce_sha256=hashlib.sha256(audit.nonce).hexdigest(),
        kernel_boot_identity_sha256=hashlib.sha256(audit.boot_id).hexdigest(),
        boot_id_semantic=control.BOOT_ID_SEMANTIC,boot_receipt_semantic=control.BOOT_RECEIPT_SEMANTIC)


def _pair(io):
    a=io.audit
    first=_dispatch_prefix_protocol(io.codec,io.key,io.read,io.write,a)
    a.current_stage='control-ready-read'
    a.control_ready_body=io.status(control.FRAME_CONTROL_READY,8,control.DOMAIN_READY,bytes((1,0,1,0)),diagnostics=True)
    if not a.native_progress.ready_for_control():raise QualificationError('P370 preparation incomplete')
    if io.raw_rx is None:
        if io.deadline-time.monotonic()<=control.OBSERVATION_INTERVAL_SEC+2:
            raise TimeoutError('P370 handoff cannot fit original deadline')
        time.sleep(control.OBSERVATION_INTERVAL_SEC)
        io.before_handoff(_request(a,5,'planned-handoff'))
    a.current_stage='detach-write'
    body=control.HANDOFF_BODY
    io.write(control.FRAME_DETACH,5,body+_handoff_tag(io.key,control.DETACH_DOMAIN,a.nonce,5,body))
    a.current_stage='detach-ack-read'
    a.detach_ack_body=io.status(control.FRAME_DETACH_ACK,5,control.DETACH_ACK_DOMAIN,control.CONTINUITY_BODY,diagnostics=True)
    a.current_stage='detach-accepted';a.progress_end=len(a.native_progress.records)
    first=shell_exchange.ShellExchange(first.session,'detach-accepted',False,None);io.shells.append(first)
    b=io.start_leg();b.current_stage='host-close-open'
    if io.raw_rx is None:io.fd=io.reopen(_request(a,5,'planned-handoff'))
    b.current_stage='resume-open-write'
    io.write(control.FRAME_RESUME_OPEN,6,body+_handoff_tag(io.key,control.RESUME_OPEN_DOMAIN,a.nonce,6,body))
    b.current_stage='resume-challenge-read'
    challenge=io.frame(control.FRAME_RESUME_CHALLENGE,6)
    if len(challenge)!=100 or challenge[64:68]!=control.CONTINUITY_BODY or not hmac.compare_digest(challenge[68:],
        _handoff_tag(io.key,control.RESUME_CHALLENGE_DOMAIN,a.nonce,6,challenge[:68])):
        raise QualificationError('P370 handoff challenge continuity differs')
    if challenge[:32]==a.nonce or challenge[32:64]!=a.boot_id:
        raise QualificationError('P370 new nonce or same boot differs')
    b.nonce=challenge[:32];b.boot_id=challenge[32:64];b.challenge_seen=True
    b.resume_challenge_body=challenge[:68];b.previous_nonce_sha256=hashlib.sha256(a.nonce).hexdigest()
    b.current_stage='resume-auth-write'
    io.write(control.FRAME_RESUME_AUTH,7,body+_handoff_tag(io.key,control.RESUME_AUTH_DOMAIN,b.nonce,7,body))
    b.current_stage='resume-ack-read'
    b.resume_ack_body=io.status(control.FRAME_RESUME_ACK,7,control.RESUME_ACK_DOMAIN,control.CONTINUITY_BODY)
    b.authenticated=True;b.ready_seen=True
    b.current_stage='control-intent-before-any-control-byte'
    if io.raw_rx is None:io.before_control(_request(b,8,'download'))
    b.current_stage='control-write'
    io.write(control.FRAME_CONTROL,8,control.CONTROL_BODY+_handoff_tag(io.key,control.DOMAIN_CONTROL,b.nonce,8,control.CONTROL_BODY))
    b.current_stage='control-ack-read'
    b.control_ack_body=io.status(control.FRAME_CONTROL_ACK,8,control.DOMAIN_ACK,bytes((1,0,0,0)),diagnostics=True)
    b.current_stage='control-accepted';b.progress_start=a.progress_end
    second=shell_exchange.ShellExchange(types.SimpleNamespace(audit=b,commands=()),'control-accepted',False,None)
    io.shells.append(second)
    return tuple(io.shells)


def _semantics(ordinal):
    return dict(authenticated_leg=ordinal,same_boot_continuity=True,
        display_request_dispatched=ordinal==1,detach_acceptance_observed=ordinal==1,
        fresh_resume_authentication=ordinal==2,control_acceptance_observed=ordinal==2,
        retained_child_instance=True,display_submitted_swaps=0,
        display_child_exited_before_ready=False,visible_panel_output='UNPROVED')


def validate_session_result(shell,step):
    a=shell.session.audit
    if step not in QUALIFICATION_COMMANDS or shell.outcome!=step.expected_outcome or shell.cancel_sent or shell.cancel_ack is not None:
        raise QualificationError('P370 leg shape differs')
    if not a.authenticated or len(a.nonce)!=32 or len(a.boot_id)!=32 or a.done_seen:
        raise QualificationError('P370 leg authentication incomplete')
    if step.ordinal==1:
        if a.current_stage!='detach-accepted' or a.detach_ack_body!=control.CONTINUITY_BODY or len(shell.session.commands)!=1:
            raise QualificationError('P370 first leg incomplete')
        parent=shell.session.commands[0]
        if parent.sequence!=3 or parent.command!=runtime.DEFAULT_COMMANDS[0] or any(getattr(parent,k)!=0 for k in ('flags','exit_code','term_signal')) or not shell_exchange.parent_identity_valid(parent.output):
            raise QualificationError('P370 parent identity differs')
        commands=_request_rows(parent,0,False)[:2]+[dict(sequence=5,command=identity(control.HANDOFF_BODY),acceptance_observed=True,mode='planned-handoff')]
        extra=dict(previous_nonce_sha256=None,progress_range=[0,a.progress_end])
    else:
        if a.current_stage!='control-accepted' or a.resume_ack_body!=control.CONTINUITY_BODY or a.control_ack_body!=bytes((1,0,0,0)):
            raise QualificationError('P370 second leg incomplete')
        commands=[dict(sequence=8,command=identity(control.CONTROL_BODY),acceptance_observed=True,mode='download')]
        extra=dict(previous_nonce_sha256=a.previous_nonce_sha256,
            progress_range=[a.progress_start,len(a.native_progress.records)])
    return dict(ordinal=step.ordinal,name=step.name,descriptor_reused=True,command=identity(step.command),
        outcome=shell.outcome,cancel_sent=False,cancel_ack=None,
        boot_id_sha256=hashlib.sha256(a.boot_id).hexdigest(),nonce_sha256=hashlib.sha256(a.nonce).hexdigest(),
        rx=dict(offset=0,**identity(bytes(a.rx))),tx=dict(offset=0,**identity(bytes(a.tx))),
        commands=commands,semantic=_semantics(step.ordinal),**extra)


def progress_projection(audit=None):
    return progress.projection(getattr(audit,'progress_owner',audit))


def _fixed():
    return dict(schema=SCHEMA,contract_id=CONTRACT_ID,target=TARGET,run_id_hex=RUN_ID_HEX,
        initial_observation=INITIAL_OBSERVATION,initial_observation_field=INITIAL_OBSERVATION_FIELD,
        session_count=2,required_session_count=2,total_command_count=4,completed_command_count=2,
        same_fd_session_count=1,same_tty_fd=False,reconnect_count=1,physical_reopen_count=1,
        idle_seconds=0,proved=True,proof_scope=PROOF_SCOPE,display_request_dispatched=True,
        display_response_observed=True,control_acceptance_observed=True,control_requested_mode='download',
        software_download_arrival='UNPROVED',framed_session_closed=False,visible_panel_output='UNPROVED',
        kernel_boot_id_semantic=control.BOOT_ID_SEMANTIC,boot_receipt_semantic=control.BOOT_RECEIPT_SEMANTIC,
        later_action_lease_active=False,authority_granted_by_observer=False)


def _receipt(shells):
    rows=[];rx_offset=tx_offset=0
    for step,shell in zip(QUALIFICATION_COMMANDS,shells):
        row=validate_session_result(shell,step);row['rx']['offset']=rx_offset;row['tx']['offset']=tx_offset
        rx_offset+=row['rx']['size'];tx_offset+=row['tx']['size'];rows.append(row)
    return dict(_fixed(),sessions=rows,expected_boot_sha256=rows[0]['boot_id_sha256'],
        native_progress=progress_projection(shells[0].session.audit))


def validate_qualification(value):
    if type(value) is not dict or set(value)!=set(_fixed())|{'sessions','expected_boot_sha256','native_progress'}:
        raise QualificationError('P370 qualification fields differ')
    if any(type(value.get(k)) is not type(v) or value[k]!=v for k,v in _fixed().items()):raise QualificationError('P370 constants differ')
    rows=value['sessions']
    if type(rows) is not list or len(rows)!=2:raise QualificationError('P370 requires two authenticated legs')
    expected_keys={'ordinal','name','descriptor_reused','command','outcome','cancel_sent','cancel_ack','boot_id_sha256','nonce_sha256','rx','tx','commands','semantic','previous_nonce_sha256','progress_range'}
    rxoff=txoff=0
    for ordinal,(row,step) in enumerate(zip(rows,QUALIFICATION_COMMANDS),1):
        if type(row) is not dict or set(row)!=expected_keys:raise QualificationError('P370 leg fields differ')
        fixed=dict(ordinal=ordinal,name=step.name,descriptor_reused=True,command=identity(step.command),outcome=step.expected_outcome,cancel_sent=False,cancel_ack=None,semantic=_semantics(ordinal))
        if any(type(row[k]) is not type(v) or row[k]!=v for k,v in fixed.items()):raise QualificationError('P370 leg constants differ')
        for key in ('boot_id_sha256','nonce_sha256'):
            if type(row[key]) is not str or not re.fullmatch('[0-9a-f]{64}',row[key]):raise QualificationError('P370 digest differs')
        for axis,offset in (('rx',rxoff),('tx',txoff)):
            x=row[axis]
            if type(x) is not dict or set(x)!={'offset','size','sha256'} or type(x['offset']) is not int or x['offset']!=offset or type(x['size']) is not int or not 0<x['size']<=16384 or type(x['sha256']) is not str or not re.fullmatch('[0-9a-f]{64}',x['sha256']):raise QualificationError('P370 leg raw bounds differ')
        rxoff+=row['rx']['size'];txoff+=row['tx']['size']
    if rows[0]['boot_id_sha256']!=rows[1]['boot_id_sha256'] or value['expected_boot_sha256']!=rows[0]['boot_id_sha256'] or rows[0]['nonce_sha256']==rows[1]['nonce_sha256'] or rows[0]['previous_nonce_sha256'] is not None or rows[1]['previous_nonce_sha256']!=rows[0]['nonce_sha256']:
        raise QualificationError('P370 nonce/boot chain differs')
    diag=progress.validate_projection(value['native_progress'])
    expected=dict(submitted_swaps=3,exact_wait_marker=True,marker_age_at_least_two_seconds=True,child_unreaped_at_control=True)
    if diag['wait_checkpoint']!=expected or diag['child_status'] is not None:raise QualificationError('P370 retained wait witness missing')
    if rows[0]['progress_range']!=[0,len(control.SUCCESS_EVENTS)] or rows[1]['progress_range']!=[len(control.SUCCESS_EVENTS),len(diag['records'])]:raise QualificationError('P370 progress boundaries differ')
    first=rows[0]['commands'];second=rows[1]['commands']
    if type(first) is not list or len(first)!=3 or type(second) is not list or len(second)!=1:raise QualificationError('P370 command accounting differs')
    if first[1]!=dict(sequence=4,command=identity(runtime.DISPLAY_COMMAND),full_request_written=True,response_observed=True,submitted_swaps=0,child_exited_before_ready=False) or first[2]!=dict(sequence=5,command=identity(control.HANDOFF_BODY),acceptance_observed=True,mode='planned-handoff') or second[0]!=dict(sequence=8,command=identity(control.CONTROL_BODY),acceptance_observed=True,mode='download'):raise QualificationError('P370 fixed commands differ')
    parent=first[0]
    if type(parent) is not dict or set(parent)!={'sequence','command','output','flags','exit_code','term_signal','duration_ms'} or type(parent['sequence']) is not int or parent['sequence']!=3 or parent['command']!=identity(runtime.DEFAULT_COMMANDS[0]) or any(type(parent[k]) is not int or parent[k]!=0 for k in ('flags','exit_code','term_signal')) or type(parent['duration_ms']) is not int or not 0<=parent['duration_ms']<=60000:
        raise QualificationError('P370 parent command differs')
    output=parent['output']
    if type(output) is not dict or set(output)!={'size','sha256'} or type(output['size']) is not int or not 0<output['size']<=4096 or type(output['sha256']) is not str or not re.fullmatch('[0-9a-f]{64}',output['sha256']):raise QualificationError('P370 parent output differs')
    return copy.deepcopy(value)


def qualify(codec,descriptor,auth_key,expected_boot_sha256,seen_nonces,writer,*,deadline,before_control,before_handoff,reopen):
    now=time.monotonic()
    if expected_boot_sha256 is not None or seen_nonces or not now<deadline<=now+QUALIFICATION_TIMEOUT_SEC or not all(callable(x) for x in (before_control,before_handoff,reopen)):
        raise QualificationError('P370 fresh qualification inputs differ')
    io=_PairIO(codec,auth_key,fd=descriptor,writer=writer,deadline=deadline,reopen=reopen,before_handoff=before_handoff,before_control=before_control)
    try:
        shells=_pair(io);value=validate_qualification(_receipt(shells))
        seen_nonces.update(row['nonce_sha256'] for row in value['sessions'])
        return QualificationResult(value,shells)
    except BaseException as exc:
        io.audit.failure_stage=io.audit.current_stage
        completed=tuple(io.shells[:len(io.audits)-1])
        raise QualificationError('P370 handoff/return stopped; no replay',audit=io.audit,sessions=completed,
            failed_session=io.audit.current_stage,category='planned-handoff',partial_receipt=dict(schema=SCHEMA,proved=False,sessions=[],display_replay_forbidden=True,control_replay_forbidden=True,control_effect_occurrence='UNKNOWN',native_progress=progress_projection(io.audit))) from exc


def replay_pair(codec,rx,tx,key,*,partial=False,handoff_evidence=False):
    io=_PairIO(codec,key,rx=rx,tx=tx)
    try:
        shells=_pair(io)
        result=_receipt(shells)
        if not partial:validate_qualification(result)
    except (ValueError,EOFError):
        if not partial:raise
        result=None
    if io.positions!=[len(rx),len(tx)]:raise QualificationError('unconsumed P370 raw bytes')
    if handoff_evidence:
        a=io.audits[0]
        if not a.authenticated or not a.parent_identity_verified or getattr(a,'control_ready_body',None)!=bytes((1,0,1,0)):
            raise QualificationError('handoff intent lacks authenticated raw READY')
        return dict(request=_request(a,5,'planned-handoff'),
            detach_ack_observed=getattr(a,'detach_ack_body',None)==control.CONTINUITY_BODY)
    return progress.validate_projection(progress_projection(io.audits[0])) if partial else result


def replay_progress(codec,rx,tx,key):return replay_pair(codec,rx,tx,key,partial=True)

def parse_captured_session(*args,**kwargs):
    raise QualificationError('P370 requires paired raw replay; a leg alone is insufficient')

_handoff_observer_audit=audit_binding

def audit_binding():
    value=_handoff_observer_audit()
    value.update(schema=SCHEMA,session_count=2,same_fd_session_count=1,reconnect_count=1,
        total_commands=4,control_sequence=8,proof_scope=PROOF_SCOPE,
        planned_handoff=True,raw_leg_boundaries=True,deadline_renewed=False)
    return value

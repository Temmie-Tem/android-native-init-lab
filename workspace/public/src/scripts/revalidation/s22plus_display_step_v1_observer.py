"""Fixed request/STATUS sequence with raw replay and distinct queue/completion facts."""
TOTAL_COMMANDS=6+_STEP_MAX
SCHEMA='s22plus-fyg8-'+_STEP_PREFIX+'-display-step-return-v1'
PROOF_SCOPE='fixed-requested-display-steps-and-supervised-return'
_step_fixed=_fixed

def _fixed():
    return dict(_step_fixed(),schema=SCHEMA,total_command_count=TOTAL_COMMANDS,
                completed_command_count=TOTAL_COMMANDS,proof_scope=PROOF_SCOPE)

def _delay(io):
    if io.raw_rx is None:
        if io.deadline-time.monotonic()<=control.STATUS_INTERVAL_SEC:raise TimeoutError('step observation exceeds original deadline')
        time.sleep(control.STATUS_INTERVAL_SEC)

def _query_statuses(io,audit):
    audit.status_samples=[]
    for ordinal in (1,2):
        request=None
        if ordinal<=_STEP_MAX and (ordinal==1 or (audit.status_samples[-1]['completed_steps']==ordinal-1 and not audit.status_samples[-1]['pending'] and not audit.status_samples[-1]['failed'] and audit.status_samples[-1]['child_unreaped'])):
            sequence=10+ordinal;body=control.STEP_BODY
            audit.current_stage='step-'+str(ordinal)+'-write'
            io.write(control.FRAME_STEP,sequence,body+_handoff_tag(io.key,control.STEP_DOMAIN,audit.nonce,sequence,body))
            audit.current_stage='step-'+str(ordinal)+'-ack'
            payload=io.frame(control.FRAME_STEP_ACK,sequence,diagnostics=True)
            if len(payload)!=36 or not hmac.compare_digest(payload[4:],_handoff_tag(io.key,control.STEP_ACK_DOMAIN,audit.nonce,sequence,payload[:4])):
                raise QualificationError('step response authentication differs')
            version,index,queued,failed=payload[:4]
            if version!=1 or index!=ordinal or queued not in (0,1) or failed not in (0,1) or bool(queued)==bool(failed):raise QualificationError('step response shape differs')
            request=dict(ordinal=ordinal,queued=bool(queued),dispatch_failed=bool(failed))
        _delay(io)
        sequence=7+ordinal;body=control.STATUS_BODY
        audit.current_stage='status-'+str(ordinal)+'-write'
        io.write(control.FRAME_STATUS,sequence,body+_handoff_tag(io.key,control.STATUS_REQUEST_DOMAIN,audit.nonce,sequence,body))
        audit.current_stage='status-'+str(ordinal)+'-read'
        payload=io.frame(control.FRAME_STATUS_REPLY,sequence,diagnostics=True)
        if len(payload)!=44 or not hmac.compare_digest(payload[12:],_handoff_tag(io.key,control.STATUS_RESPONSE_DOMAIN,audit.nonce,sequence,payload[:12])):
            raise QualificationError('step STATUS authentication differs')
        version,index,requested,started,completed,flags,exit_code,signal,elapsed=struct.unpack('<BBBBBBBBI',payload[:12])
        if version!=2 or index!=ordinal or not 0<=completed<=started<=requested<=_STEP_MAX or flags>15 or bool(flags&4)==bool(flags&8) or signal>64 or (flags&4 and (exit_code or signal)) or (signal and exit_code) or elapsed>60000 or (ordinal==1 and elapsed!=0):
            raise QualificationError('step STATUS shape differs')
        audit.status_samples.append(dict(ordinal=ordinal,request=request,requested_steps=requested,started_steps=started,completed_steps=completed,
            pending=bool(flags&1),failed=bool(flags&2),child_unreaped=bool(flags&4),child_reaped=bool(flags&8),exit_code=exit_code,term_signal=signal,elapsed_since_first_ms=elapsed))

def _status_command_rows(audit):
    rows=[]
    for sample in _samples(audit):
        request=sample['request']
        if request is not None:rows.append(dict(sequence=10+request['ordinal'],command=identity(control.STEP_BODY),response_observed=True,ack=request))
        rows.append(dict(sequence=7+sample['ordinal'],command=identity(control.STATUS_BODY),response_observed=True,sample=sample))
    return rows

def _validate_step_checkpoint(diag):
    expected=dict(completed_steps=0 if _STEP_EXIT else _STEP_MAX,started_steps=_STEP_MAX,
                  pending=_STEP_EXIT,failed=_STEP_EXIT,child_unreaped_at_control=not _STEP_EXIT)
    child=dict(event=control.CHILD_EXIT,code=7) if _STEP_EXIT else None
    if diag['step_checkpoint']!=expected or diag['child_status']!=child:raise QualificationError('step completion/failure checkpoint missing')

def validate_qualification(value):
    value=_status_validate(value) # Sealed general two-leg validation with new checkpoint hook.
    samples=value['status_samples']
    if type(samples) is not list or len(samples)!=2:raise QualificationError('two step STATUS samples required')
    for ordinal,sample in enumerate(samples,1):
        amount=min(ordinal,_STEP_MAX)
        request=dict(ordinal=ordinal,queued=True,dispatch_failed=False) if ordinal<=_STEP_MAX else None
        expected=dict(ordinal=ordinal,request=request,requested_steps=amount,started_steps=amount,
            completed_steps=0 if _STEP_EXIT else amount,pending=_STEP_EXIT,failed=_STEP_EXIT,
            child_unreaped=not _STEP_EXIT,child_reaped=_STEP_EXIT,exit_code=7 if _STEP_EXIT else 0,term_signal=0)
        if type(sample) is not dict or set(sample)!=set(expected)|{'elapsed_since_first_ms'} or any(type(sample[k]) is not type(v) or sample[k]!=v for k,v in expected.items()):raise QualificationError('requested step facts missing')
        if request is not None and (set(sample['request'])!=set(request) or any(type(sample['request'][k]) is not type(v) for k,v in request.items())):raise QualificationError('step ACK types differ')
        elapsed=sample['elapsed_since_first_ms']
        if type(elapsed) is not int or (elapsed!=0 if ordinal==1 else not 2000<=elapsed<=60000):raise QualificationError('step STATUS native interval missing')
    if value['sessions'][1]['commands'][:-1]!=_status_command_rows(types.SimpleNamespace(status_samples=samples)):raise QualificationError('step commands/samples differ')
    return value

_step_observer_audit=audit_binding

def audit_binding():
    value=_step_observer_audit()
    value.update(schema=SCHEMA,total_commands=TOTAL_COMMANDS,control_sequence=14,proof_scope=PROOF_SCOPE,
        status_response_bytes=12,step_maximum=_STEP_MAX,step_exit_before_completion=_STEP_EXIT,
        step_sequences=list(range(11,11+_STEP_MAX)),step_ack_scope='queued-only')
    return value

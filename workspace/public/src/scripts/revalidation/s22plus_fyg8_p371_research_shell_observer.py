"""P371 fixed STATUS observations; H0 only until separately approved."""
from s22plus_fyg8_p371_namespace import load
load(globals())

TOTAL_COMMANDS=6
SCHEMA='s22plus-fyg8-p371-two-leg-status-return-v1'
PROOF_SCOPE='two-fixed-status-observations-after-planned-handoff-and-control'

def _samples(audit):return copy.deepcopy(getattr(audit,'status_samples',[]))

def _query_statuses(io,audit):
    audit.status_samples=[]
    for ordinal in (1,2):
        if ordinal==2 and io.raw_rx is None:
            if io.deadline-time.monotonic()<=control.STATUS_INTERVAL_SEC:
                raise TimeoutError('STATUS interval exceeds original deadline')
            time.sleep(control.STATUS_INTERVAL_SEC)
        sequence=7+ordinal;body=control.STATUS_BODY
        audit.current_stage='status-'+str(ordinal)+'-write'
        io.write(control.FRAME_STATUS,sequence,body+_handoff_tag(io.key,control.STATUS_REQUEST_DOMAIN,audit.nonce,sequence,body))
        audit.current_stage='status-'+str(ordinal)+'-read'
        payload=io.frame(control.FRAME_STATUS_REPLY,sequence,diagnostics=True)
        if len(payload)!=40 or not hmac.compare_digest(payload[8:],_handoff_tag(io.key,control.STATUS_RESPONSE_DOMAIN,audit.nonce,sequence,payload[:8])):
            raise QualificationError('STATUS response authentication differs')
        version,index,swaps,flags,elapsed=struct.unpack('<BBBBI',payload[:8])
        if version!=1 or index!=ordinal or swaps>10 or flags>15 or bool(flags&4)==bool(flags&8) or (flags&2 and not flags&1) or elapsed>60000 or (ordinal==1 and elapsed!=0):
            raise QualificationError('STATUS response shape differs')
        audit.status_samples.append(dict(ordinal=ordinal,submitted_swaps=swaps,
            exact_wait_marker=bool(flags&1),marker_age_at_least_two_seconds=bool(flags&2),
            child_unreaped=bool(flags&4),child_reaped=bool(flags&8),elapsed_since_first_ms=elapsed))

def _status_command_rows(audit):
    return [dict(sequence=7+s['ordinal'],command=identity(control.STATUS_BODY),response_observed=True,sample=s)
        for s in _samples(audit)]

_status_validate=validate_qualification

def validate_qualification(value):
    value=_status_validate(value)
    samples=value['status_samples']
    if type(samples) is not list or len(samples)!=2:raise QualificationError('two STATUS samples required')
    for ordinal,sample in enumerate(samples,1):
        expected=dict(ordinal=ordinal,submitted_swaps=3,exact_wait_marker=True,
            marker_age_at_least_two_seconds=True,child_unreaped=True,child_reaped=False)
        if type(sample) is not dict or set(sample)!=set(expected)|{'elapsed_since_first_ms'} or any(type(sample[k]) is not type(v) or sample[k]!=v for k,v in expected.items()):
            raise QualificationError('STATUS fixed wait facts missing')
        elapsed=sample['elapsed_since_first_ms']
        if type(elapsed) is not int or (elapsed!=0 if ordinal==1 else not 2000<=elapsed<=60000):
            raise QualificationError('STATUS native interval missing')
    if value['sessions'][1]['commands'][:2]!=_status_command_rows(types.SimpleNamespace(status_samples=samples)):
        raise QualificationError('STATUS commands/samples differ')
    return value

def replay_status(codec,rx,tx,key):
    return replay_pair(codec,rx,tx,key,partial=True,status_evidence=True)

_status_observer_audit=audit_binding

def audit_binding():
    value=_status_observer_audit()
    value.update(schema=SCHEMA,total_commands=6,control_sequence=10,proof_scope=PROOF_SCOPE,
        status_sequences=[8,9],status_interval_sec=2,status_response_bytes=8,
        qualification_commands=[dict(ordinal=s.ordinal,name=s.name,command=identity(s.command),expected_outcome=s.expected_outcome) for s in QUALIFICATION_COMMANDS])
    return value

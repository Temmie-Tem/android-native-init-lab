"""Offline independently authenticated worker diagnostics. No device control."""
import hashlib
import hmac
import re
import struct

from s22plus_native_records_v3 import require
from s22plus_debian_early_protocol_v1 import tag

DOMAIN=b'S22PLUS-FYG8-DEBIAN-FAILURE-v1'
FIELDS=('phase','ordinal','call_returned','call_rc','call_errno','close_returned','close_errno',
    'presence_returned','presence','presence_errno','log_stage','log_error','first_failure_phase',
    'first_failure_errno','semantic_done','result','call_returns','first_log_failure_stage',
    'first_log_failure_errno','guard_errno','log_returned','initial_pid1_measured')
PATTERN=re.compile(rb'S22DIAG1 run=([0-9a-f]{32}) boot=([0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}) '
    rb'helper=([12]) seq=([12]) mac=([0-9a-f]{64}) data=([0-9a-f]{216})$')


def decode(raw,*,key,run,expected_boot=None):
    require(type(raw) is bytes and len(raw)<=16*1024**2 and len(key)==32 and len(run)==16,
        'diagnostic input bounds differ')
    records=[];rejected=0;seen=set();boot=None
    for line in raw.replace(b'\r',b'').splitlines():
        at=line.find(b'S22DIAG1 ')
        if at<0:continue
        match=PATTERN.fullmatch(line[at:])
        if not match:rejected+=1;continue
        rid,bid,helper,sequence,signature,data=match.groups()
        helper=int(helper);sequence=int(sequence);data=bytes.fromhex(data.decode())
        nonce=hashlib.sha256(bid).digest()
        if rid.decode()!=run.hex() or (expected_boot is not None and nonce.hex()!=expected_boot) or not hmac.compare_digest(
            bytes.fromhex(signature.decode()),tag(key,run,nonce,250+helper,sequence,data,domain=DOMAIN)):
            rejected+=1;continue
        require(boot in (None,nonce.hex()),'multiple authenticated boots in diagnostic capture')
        boot=nonce.hex();identity=(helper,sequence)
        require(identity not in seen,'duplicate authenticated diagnostic record');seen.add(identity)
        outcome,status,error,stable,deadline,*values=struct.unpack('<27I',data)
        require(stable in (0,1) and 0<deadline<=300000 and outcome<=5 and status<=65535 and error<4096 and
            ((sequence==1 and outcome in (0,5)) or (sequence==2 and outcome in (1,2,3,4,5))),
            'diagnostic envelope semantics differ')
        require(stable or not any(values),'unstable snapshot contains asserted fields')
        fields=dict(zip(FIELDS,values)) if stable else None
        if fields:
            require(fields['phase']<=12 and fields['ordinal']<=82 and fields['call_returns']<=82 and
                all(fields[k] in (0,1) for k in ('call_returned','close_returned','presence_returned','semantic_done','log_returned','initial_pid1_measured')) and
                fields['log_stage']<=9 and fields['first_log_failure_stage']<=9,'diagnostic field bounds differ')
            for name in ('call_rc','presence'):
                if fields[name]>=2**31:fields[name]-=2**32
            require(all(fields[k]<4096 for k in ('call_errno','close_errno','presence_errno','log_error',
                'first_failure_errno','first_log_failure_errno','guard_errno')) and fields['first_failure_phase']<=12,
                'diagnostic error bounds differ')
            require(fields['call_rc'] in (-1,0) and fields['presence'] in (-1,0,1) and
                (fields['call_returned'] or fields['call_rc']==fields['call_errno']==0) and
                (fields['close_returned'] or fields['close_errno']==0) and
                (fields['presence_returned'] or fields['presence']==fields['presence_errno']==0),
                'unreturned operation asserts a result')
        if outcome==1:
            require(status&127==0,'exit record contains non-exit wait status')
            observed='WORKER_EXIT';exit_code=(status>>8)&255;signal=None
        elif outcome==2:
            require(0<(status&127)<127,'signal record contains non-signal wait status')
            observed='WORKER_SIGNAL';exit_code=None;signal=status&127
        else:
            require(status==0,'uncollected worker has a wait status')
            observed={0:'START',3:'WORKER_NOT_COLLECTED_AT_DEADLINE',4:'OBSERVER_ERROR',5:'OBSERVER_START_ERROR'}[outcome]
            exit_code=signal=None
        records.append(dict(helper=helper,sequence=sequence,observation=observed,observer_error=error,
            exit_code=exit_code,signal=signal,stable=bool(stable),deadline_ms=deadline,fields=fields,
            semantic_success=bool(outcome==1 and error==0 and exit_code==0 and fields and fields['semantic_done']==1 and fields['result']==0 and fields['initial_pid1_measured']==1 and
                fields['first_failure_errno']==0 and fields['guard_errno']==0)))
    terminal=[r for r in records if r['sequence']==2]
    return dict(schema='s22plus-debian-failure-evidence-v1',status='AUTHENTICATED_DIAGNOSTICS' if terminal else 'UNKNOWN',
        records=records,rejected_records=rejected,kernel_boot_identity_sha256=boot,
        helper_status={str(helper):next((r['observation'] for r in terminal if r['helper']==helper),'UNKNOWN') for helper in (1,2)},
        worker_collection_proved=len(terminal)==2 and all(r['observation'] in ('WORKER_EXIT','WORKER_SIGNAL') for r in terminal),
        descendant_settlement_proved=False,unmount_proved=False,retention_proved=False,
        nonexecution_proved=False,replay_authorized=False,
        raw=dict(size=len(raw),sha256=hashlib.sha256(raw).hexdigest()))

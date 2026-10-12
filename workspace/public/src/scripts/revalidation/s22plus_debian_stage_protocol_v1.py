"""Exact contiguous short stage frames; no reconstruction or device commands."""
import base64
import hashlib
import hmac
import re
import struct

from s22plus_native_records_v3 import require

DOMAIN=b'S22PLUS-FYG8-DEBIAN-STAGE-v1'
PREFIX=b'S22STG1['
ENCODED=144
WIDTH=108
MAXIMUM=4*1024*1024
EVENTS=('CHILD_ENTERED','PARENT_SHELL','INIT_IMAGE','HELPER_IMAGE',
        'MODULE_CALL_NEXT','MODULE_RETURN','LOGGER_BOUND','COMPLETE')
REJECTED=9


def encode(*,key,run,boot,sequence,event,value=0,detail=bytes(32)):
    require(len(key)==32 and len(run)==len(boot)==16 and len(detail)==32,'stage identity width differs')
    data=run+boot+struct.pack('<III',sequence,event,value)+detail
    tag=hmac.new(key,DOMAIN+run+hashlib.sha256(boot).digest()+struct.pack('<IB',sequence,241)+data,hashlib.sha256).digest()
    return PREFIX+base64.b64encode(data+tag)+b']'


def retained(raw,*,key,run,expected,logger_sha256):
    require(type(raw) is bytes and len(raw)<=MAXIMUM and len(key)==32 and len(run)==16,'stage input bound differs')
    require(set(expected)=={'shell_sha256','init_sha256','helper_sha256'} and
        all(re.fullmatch('[0-9a-f]{64}',s) for s in (*expected.values(),logger_sha256)),
        'stage measurement declaration differs')
    starts=[m.start() for m in re.finditer(re.escape(PREFIX),raw)]
    require(len(starts)<=512,'stage header count exceeds bound')
    records=[];errors=[];foreign=0;boot=None;seen=set()
    for offset in starts:
        span=raw[offset:offset+len(PREFIX)+ENCODED+1]
        reason=None
        if len(span)!=len(PREFIX)+ENCODED+1 or span[-1:]!=b']':reason='TRUNCATED_OR_DAMAGED_ENVELOPE'
        else:
            try:data=base64.b64decode(span[len(PREFIX):-1],validate=True)
            except ValueError:reason='INVALID_BASE64'
            else:
                if len(data)!=WIDTH or base64.b64encode(data)!=span[len(PREFIX):-1]:reason='NONCANONICAL_FRAME'
                elif data[:16]!=run:foreign+=1;continue
                else:
                    seq,kind,value=struct.unpack('<III',data[32:44]);detail=data[44:76]
                    tag=hmac.new(key,DOMAIN+run+hashlib.sha256(data[16:32]).digest()+
                        struct.pack('<IB',seq,241)+data[:76],hashlib.sha256).digest()
                    if not hmac.compare_digest(tag,data[76:]):reason='BAD_AUTHENTICATION'
                    elif not 1<=seq<=9 or not 1<=kind<=9:reason='EVENT_RANGE'
                    elif kind!=REJECTED and seq!=kind:reason='EVENT_SEQUENCE'
                    elif kind==1 and (value<=1 or detail!=bytes(32)):reason='ENTRY_VALUE'
                    elif kind in (2,3,4,5) and (value or detail.hex()!=
                        (expected[('shell_sha256','init_sha256','helper_sha256')[kind-2]] if kind<5 else logger_sha256)):
                        reason='MEASUREMENT_MISMATCH'
                    elif kind in (6,7,8,9) and (detail!=bytes(32) or (kind in (7,8) and value) or
                        (kind==9 and not value) or value>4095):reason='RESULT_VALUE'
                    else:
                        require(boot is None or boot==data[16:32],'mixed authenticated stage boots')
                        require(seq not in seen and (not records or seq>records[-1]['sequence']),
                            'duplicate or reversed authenticated stage sequence')
                        boot=data[16:32];seen.add(seq)
                        records.append(dict(offset=offset,size=len(span),sequence=seq,event=kind,
                            name=EVENTS[kind-1] if kind<9 else 'REJECTED',value=value,detail_sha256=detail.hex(),
                            raw_sha256=hashlib.sha256(span).hexdigest()))
        if reason:errors.append(dict(offset=offset,size=len(span),reason=reason,raw_sha256=hashlib.sha256(span).hexdigest()))
    by={r['event']:r for r in records}
    rejected=9 in by or (6 in by and by[6]['value']!=0)
    complete=not errors and not rejected and [r['event'] for r in records]==list(range(1,9))
    return dict(schema='s22plus-debian-stage-records-v1',
        status='PASS_RETAINED_EARLY_STAGE' if complete else 'RETAINED_STAGE_REJECTED' if rejected else
            'PARTIAL_RETAINED_STAGE' if records else 'NO_AUTHENTICATED_STAGE',
        records=records,damaged_candidates=errors,foreign_frames=foreign,
        run_id_hex=run.hex(),kernel_boot_uuid_hex=boot.hex() if boot else None,
        complete=complete,debian_early_pid1=all(i in by for i in (1,2,3,4)),
        logger_bound=complete,installed_debian_pid1=False,live_usb_proved=False,
        final_ring_readback_proved=False,helper_return_proved=False,park_proved=False,
        last_authenticated_stage=records[-1]['name'] if records else None,
        stopped_at_last_stage=False,absence_proves_nonexecution=False,replay_authorized=False)

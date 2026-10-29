"""Bounded mainline early-stage frames; positive occurrence, never boot success."""
import hashlib
import hmac
import json
from pathlib import Path
import re
import struct

HERE=Path(__file__).resolve().parent
BASE=0x800200000
REGION=0x200000
HEADER=16
PAYLOAD=REGION-HEADER
SPAN=256
SLOT=128
MAGIC=b'S22MRK1!'
DOMAIN=b'S22PLUS-MAINLINE-EARLY-MARKER-V1\0'
STAGES={1:'loader-handoff',2:'kernel-entry'}

def require(condition,message):
    if not condition:raise ValueError(message)

def frame(candidate,key,stage):
    require(re.fullmatch('[0-9a-f]{64}',candidate) is not None and len(key)==32 and stage in STAGES,
            'marker identity/key/stage differs')
    prefix=MAGIC+struct.pack('<II',1,stage)+bytes.fromhex(candidate)+bytes(48)
    return prefix+hmac.digest(key,DOMAIN+prefix,'sha256')

def configuration(candidate,key):
    return dict(schema='s22plus-mainline-retained-marker-v1',candidate_id=candidate,
        base=BASE,region_size=REGION,span=SPAN,slot_size=SLOT,
        frames={str(s):frame(candidate,key,s).hex() for s in STAGES})

def validate(config,candidate,key):
    require(config==configuration(candidate,key),'retained marker configuration differs')
    return config

def render(config,stage):
    require(stage in STAGES and config['base']==BASE and config['region_size']==REGION and
            config['span']==SPAN and config['slot_size']==SLOT,'marker write scope differs')
    data=bytes.fromhex(config['frames'][str(stage)])
    require(len(data)==SLOT,'marker frame size differs')
    name='s22_retained_'+('loader' if stage==1 else 'kernel')
    rows='\n'.join('\t.byte '+','.join(str(x) for x in data[i:i+16]) for i in range(0,SLOT,16))
    return (HERE/'retained-marker.S').read_text().replace('@NAME@',name).replace('@SLOT@',str((stage-1)*SLOT)).replace('@FRAME@',rows)

def decode(data,candidate,key):
    require(type(data) is bytes and len(data)<=4*1024*1024,'retained capture exceeds bound')
    expected={s:frame(candidate,key,s) for s in STAGES}
    records=[];damaged=foreign=0;offset=0
    while True:
        offset=data.find(MAGIC,offset)
        if offset<0:break
        piece=data[offset:offset+SLOT]
        if len(piece)!=SLOT:damaged+=1
        else:
            version,stage=struct.unpack_from('<II',piece,8)
            if piece[16:48]!=bytes.fromhex(candidate):foreign+=1
            elif version!=1 or stage not in STAGES or not hmac.compare_digest(piece,expected[stage]):damaged+=1
            else:records.append(dict(stage=STAGES[stage],offset=offset,sha256=hashlib.sha256(piece).hexdigest()))
        offset+=len(MAGIC)
    stages=sorted({r['stage'] for r in records})
    return dict(schema='s22plus-mainline-retained-marker-result-v1',
        status='RETAINED_STAGE_OBSERVED' if records else 'NO_PROOF',records=records,
        observed_stages=stages,damaged_candidates=damaged,foreign_candidates=foreign,
        occurrence_scope='AT_LEAST_ONCE_IN_CANDIDATE_ATTEMPTS',same_boot_pair_proved=False,
        last_attempt_proved=False,stopped_at_last_record=False,reset_cause_proved=False,
        mainline_pid1=False,authenticated_usb=False,replay_authorized=False)

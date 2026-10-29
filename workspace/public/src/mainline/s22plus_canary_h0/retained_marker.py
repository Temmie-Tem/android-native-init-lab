"""Bounded mainline early-stage frames; positive occurrence, never boot success."""
import hashlib
import hmac
import json
from pathlib import Path
import re
import struct
try:
    from . import retained_trace as trace
except ImportError:
    import retained_trace as trace

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
FORMATS={
    1:dict(schema='s22plus-mainline-retained-marker-v1',magic=MAGIC,domain=DOMAIN,
           stages=STAGES,names={1:'loader',2:'kernel'}),
    2:dict(schema='s22plus-mainline-retained-marker-v2',magic=b'S22MRK2!',
           domain=b'S22PLUS-MAINLINE-MMU-MARKER-V2\0',
           stages={3:'pre-mmu',4:'early-c'},names={3:'pre_mmu',4:'early_c'}),
    3:dict(schema='s22plus-mainline-retained-marker-v3',magic=b'S22MRK3!',
           domain=b'S22PLUS-MAINLINE-ARCH-MARKER-V3\0',
           stages={5:'post-fdt',6:'post-paging'},names={5:'post_fdt',6:'post_paging'}),
    4:dict(schema='s22plus-mainline-retained-marker-v4',magic=b'S22MRK4!',
           domain=b'S22PLUS-MAINLINE-CORE-MARKER-V4\0',
           stages={7:'post-setup-arch',8:'post-time-init'},names={7:'post_setup_arch',8:'post_time_init'}),
    5:dict(schema='s22plus-mainline-retained-marker-v5',magic=b'S22MRK5!',
           domain=b'S22PLUS-MAINLINE-BOOTSTRAP-MARKER-V5\0',
           stages={9:'pre-irq-enable',10:'pre-rest-init'},names={9:'pre_irq_enable',10:'pre_rest_init'}),
    6:dict(schema='s22plus-mainline-retained-marker-v6',magic=b'S22MRK6!',
           domain=b'S22PLUS-MAINLINE-INITTHREAD-MARKER-V6\0',
           stages={11:'post-kthreadd-wait',12:'post-async-sync'},names={11:'post_kthreadd_wait',12:'post_async_sync'}),
    7:dict(schema='s22plus-mainline-retained-marker-v7',magic=b'S22MRK7!',
           domain=b'S22PLUS-MAINLINE-BASICSETUP-MARKER-V7\0',
           stages={13:'pre-basic-setup',14:'post-basic-setup'},names={13:'pre_basic_setup',14:'post_basic_setup'}),
    8:dict(schema=trace.SCHEMA,magic=trace.MAGIC,domain=trace.DOMAIN,
           stages={},names={}),
}

def require(condition,message):
    if not condition:raise ValueError(message)

def version(config):
    matches=[v for v,f in FORMATS.items() if config.get('schema')==f['schema']]
    require(len(matches)==1,'unknown retained marker format')
    return matches[0]

def slot(config,stage):
    stages=list(FORMATS[version(config)]['stages'])
    require(stage in stages,'stage is outside selected marker format')
    return stages.index(stage)*SLOT

def name(config,stage):
    slot(config,stage)
    return 's22_retained_'+FORMATS[version(config)]['names'][stage]

def frame(candidate,key,stage,*,version=1):
    require(version in FORMATS,'unknown retained marker version')
    fmt=FORMATS[version]
    require(re.fullmatch('[0-9a-f]{64}',candidate) is not None and len(key)==32 and stage in fmt['stages'],
            'marker identity/key/stage differs')
    prefix=fmt['magic']+struct.pack('<II',version,stage)+bytes.fromhex(candidate)+bytes(48)
    return prefix+hmac.digest(key,fmt['domain']+prefix,'sha256')

def configuration(candidate,key,*,version=1,initcall_count=None):
    require(version in FORMATS,'unknown retained marker version')
    if version==8:return trace.configuration(candidate,key,initcall_count)
    require(initcall_count is None,'legacy marker has no initcall count')
    return dict(schema=FORMATS[version]['schema'],candidate_id=candidate,
        base=BASE,region_size=REGION,span=SPAN,slot_size=SLOT,
        frames={str(s):frame(candidate,key,s,version=version).hex() for s in FORMATS[version]['stages']})

def validate(config,candidate,key):
    if version(config)==8:return trace.validate(config,candidate,key)
    require(config==configuration(candidate,key,version=version(config)),'retained marker configuration differs')
    return config

def render(config,stage):
    require(stage in FORMATS[version(config)]['stages'] and stage in (1,2,3) and config['base']==BASE and config['region_size']==REGION and
            config['span']==SPAN and config['slot_size']==SLOT,'marker write scope differs')
    data=bytes.fromhex(config['frames'][str(stage)])
    require(len(data)==SLOT,'marker frame size differs')
    routine=name(config,stage)
    rows='\n'.join('\t.byte '+','.join(str(x) for x in data[i:i+16]) for i in range(0,SLOT,16))
    return (HERE/'retained-marker.S').read_text().replace('@NAME@',routine).replace('@SLOT@',str(slot(config,stage))).replace('@FRAME@',rows)

def c_stages(config):
    v=version(config)
    if v==8:return (0,5)
    return (4,) if v==2 else tuple(FORMATS[v]['stages']) if v in (3,4,5,6,7) else ()

def c_source(config):
    require(c_stages(config),'selected format has no C source')
    return 'init/main.c' if version(config) in (4,5,6,7,8) else 'arch/arm64/kernel/setup.c'

def render_c(config,stage=None):
    if version(config)==8:
        require(stage is None,'trace uses one parameterized writer')
        return trace.render(config)
    require(c_stages(config) and config['base']==BASE and config['region_size']==REGION and
            config['span']==SPAN and config['slot_size']==SLOT,'MMU-on marker scope differs')
    if stage is None:return '\n'.join(render_c(config,s) for s in c_stages(config))
    require(stage in c_stages(config),'C stage is outside selected format')
    data=bytes.fromhex(config['frames'][str(stage)]);require(len(data)==SLOT,'early C frame size differs')
    rows='\n'.join('\t'+','.join(str(x) for x in data[i:i+16])+',' for i in range(0,SLOT,16))
    return (HERE/'retained-early-c.h').read_text().replace('@FRAME@',rows).replace('@NAME@',name(config,stage)).replace('@SLOT@',str(slot(config,stage)))

def decode(data,candidate,key,*,version=1,config=None):
    if version==8:return trace.decode(data,candidate,key,config)
    require(type(data) is bytes and len(data)<=4*1024*1024,'retained capture exceeds bound')
    require(version in FORMATS,'unknown retained marker version');fmt=FORMATS[version]
    expected={s:frame(candidate,key,s,version=version) for s in fmt['stages']}
    records=[];damaged=foreign=0;offset=0
    while True:
        offset=data.find(fmt['magic'],offset)
        if offset<0:break
        piece=data[offset:offset+SLOT]
        if len(piece)!=SLOT:damaged+=1
        else:
            wire_version,stage=struct.unpack_from('<II',piece,8)
            if piece[16:48]!=bytes.fromhex(candidate):foreign+=1
            elif wire_version!=version or stage not in fmt['stages'] or not hmac.compare_digest(piece,expected[stage]):damaged+=1
            else:records.append(dict(stage=fmt['stages'][stage],offset=offset,sha256=hashlib.sha256(piece).hexdigest()))
        offset+=len(fmt['magic'])
    stages=sorted({r['stage'] for r in records})
    return dict(schema='s22plus-mainline-retained-marker-result-v'+str(version),
        status='RETAINED_STAGE_OBSERVED' if records else 'NO_PROOF',records=records,
        observed_stages=stages,damaged_candidates=damaged,foreign_candidates=foreign,
        occurrence_scope='AT_LEAST_ONCE_IN_CANDIDATE_ATTEMPTS',same_boot_pair_proved=False,
        last_attempt_proved=False,stopped_at_last_record=False,reset_cause_proved=False,
        mainline_pid1=False,authenticated_usb=False,replay_authorized=False)

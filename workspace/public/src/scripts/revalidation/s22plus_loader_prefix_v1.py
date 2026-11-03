"""Bounded current-boot prefix facts; static V1 readback is not store proof."""
from pathlib import Path
import re
import struct
import sys

from s22plus_native_records_v3 import require
ROOT=Path(__file__).resolve().parents[5]

SCHEMA='s22plus-loader-mainline-prefix-v1'
PROPERTY='codex,uniloader-prefix-v1'
MAGIC=b'S22PFX1!'
SIZE=256
COOKIE=0x50335831
STATES={'SKIP_STATE':1,'SKIP_FDT':2,'RETURNED':3}
MASK=5|4096|(1<<25)
PAYLOAD=0x200000-16


def marker_module():
    # Candidate generation/admission is not an original-A recovery input.
    sys.path.insert(0,str(ROOT/'workspace/public/src'))
    from mainline.s22plus_canary_h0 import retained_marker
    return retained_marker


def configuration(candidate,key):
    require(re.fullmatch('[0-9a-f]{64}',candidate) and type(key) is bytes and len(key)==32,
            'prefix candidate identity/key differs')
    cfg=marker_module().configuration(candidate,key,version=1)
    seed=MAGIC+struct.pack('>II',1,0)+bytes.fromhex(candidate)+bytes(SIZE-48)
    return dict(schema=SCHEMA,marker=candidate,retained_marker=cfg,report_property=PROPERTY,
                report_seed_hex=seed.hex(),return_cookie=COOKIE)


def report(data,config,entry):
    require(type(data) is bytes and len(data)==SIZE and data[:12]==MAGIC+struct.pack('>I',1)
        and data[16:48]==bytes.fromhex(config['marker']) and data[192:]==bytes(64),
        'prefix report shape or candidate differs')
    state=struct.unpack_from('>I',data,12)[0]
    require(state in STATES.values(),'prefix report is unfinalized')
    el,sctlr,pc,returned_el,returned_sctlr,cookie=struct.unpack_from('>QQQQQQ',data,48)
    require(el in (0,4,8,12) and (el in (4,8) or sctlr==0),'prefix CPU sample is impossible')
    rows=[]
    for i in range(2):
        before=struct.unpack_from('>IIII',data,96+i*48)
        after=struct.unpack_from('>IIII',data,112+i*48)
        slot,mismatch,valid,reserved=struct.unpack_from('>IIII',data,128+i*48)
        require(valid in (0,1) and reserved==0,'prefix readback fields differ')
        if state!=3:
            require(not any((*before,*after,slot,mismatch,valid)),'skipped prefix populated diagnostics')
        elif after[1]==0x4d474f4c and after[2]>=256:
            cursor=after[2]%PAYLOAD
            expected=(cursor-256 if cursor>=256 else PAYLOAD-256)+i*128
            require(valid==1 and slot==expected and 0<=mismatch<=128,'prefix postcall readback differs')
        else:require(valid==0 and slot==mismatch==0,'unavailable prefix readback populated')
        rows.append(dict(site=('loader-handoff','kernel-entry')[i],header_before=list(before),
            header_after=list(after),postcall_slot_offset=slot if valid else None,
            postcall_mismatch_count=mismatch if valid else None,current_attempt_store_proved=False))
    if state==1:
        require(el not in (4,8) or sctlr&MASK,'prefix state skip inconsistent')
    else:require(el in (4,8) and not sctlr&MASK,'prefix entry state ineligible')
    if state==3:
        require(pc==entry and returned_el==el and returned_sctlr==sctlr and cookie==COOKIE,
                'prefix returned PC/CPU/cookie differs')
    else:require(pc==returned_el==returned_sctlr==cookie==0,'skipped prefix has return facts')
    return dict(status=next(k for k,v in STATES.items() if v==state),current_el=el,
        sctlr=sctlr,mainline_prefix_return_proved=state==3,observations=rows if state==3 else [],
        current_attempt_store_proved=False,mainline_boot_proved=False,reset_retention_proved=False,
        historical_failure_cause_proved=False)

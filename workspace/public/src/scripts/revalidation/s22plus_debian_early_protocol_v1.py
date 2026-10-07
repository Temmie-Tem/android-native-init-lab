"""One authenticated, read-only snapshot from a child of Debian /init.

The wire shares only the existing bounded frame encoding. It has no native
health, shell, CONTROL, release, shutdown or reentry vocabulary.
"""
import hashlib
import hmac
import re
import struct

import s22plus_native_wire_v3 as frames
from s22plus_native_records_v3 import require

REQUEST,PROOF,LOG,END=48,176,177,178
DOMAIN=b'S22PLUS-FYG8-DEBIAN-EARLY-v1'
MAXIMUM=96*1039
LOG_MAXIMUM=65536


def tag(key,run,nonce,kind,sequence,body=b'',*,domain=DOMAIN):
    require(len(key)==len(nonce)==32 and len(run)==16,'early protocol identity width differs')
    return hmac.digest(key,domain+run+nonce+struct.pack('<IB',sequence,kind)+body,'sha256')


def request(key,run,nonce,*,domain=DOMAIN):
    require(any(nonce),'zero challenge rejected')
    return frames.encode_frame(REQUEST,1,nonce+tag(key,run,nonce,REQUEST,1,domain=domain))


def payload(frame,key,run,nonce,*,domain=DOMAIN):
    require(32<=len(frame.payload)<=800,'early frame size differs')
    body,signature=frame.payload[:-32],frame.payload[-32:]
    require(hmac.compare_digest(signature,tag(key,run,nonce,frame.frame_type,frame.sequence,body,domain=domain)),
        'early frame authentication failed')
    return body


def parse_log(raw,run,module_names,boot):
    require(0<len(raw)<=LOG_MAXIMUM and raw.endswith(b'\n'),'early RAM record truncated')
    lines=raw.splitlines();events=[]
    require(len(lines)<=256,'early RAM event bound exceeded')
    for seq,line in enumerate(lines,1):
        match=re.fullmatch(rb'FYG8_H0 seq=([1-9][0-9]*) ([\x20-\x7e]{1,350})',line)
        require(match and int(match[1])==seq,'early RAM sequence or line grammar differs')
        events.append(match[2])
    first=re.fullmatch(rb'BEGIN run=([0-9a-f]{32}) boot=([0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}) parent=1',events[0])
    require(first and first[1]==run.hex().encode() and hashlib.sha256(first[2]).digest()==boot,
        'RAM record belongs to another candidate or current boot')
    terminal=re.fullmatch(rb'TERMINAL result=(METADATA_CLEAN|METADATA_DIRTY|REJECTED) error=([0-9]{1,4})',events[-1])
    require(terminal and int(terminal[2])<=4095,'early terminal missing or malformed')
    starts=[];dones=[];module_phase=True;stage_events=[]
    require(len(events)>2 and events[1]==b'TARGET_GUARD_OK','target guard not established')
    for event in events[2:-1]:
        match=re.fullmatch(rb'MODULE_(BEGIN|DONE) ordinal=([1-9][0-9]*) name=([A-Za-z0-9_]+)',event)
        if match:
            require(module_phase,'module record follows storage')
            ordinal=int(match[2]);require(1<=ordinal<=len(module_names) and match[3].decode()==module_names[ordinal-1],
                'unexpected module identity')
            if match[1]==b'BEGIN':
                require(len(starts)==len(dones) and ordinal==len(starts)+1,'module insertion repeats or skips')
                starts.append(ordinal)
            else:
                require(len(starts)==len(dones)+1 and ordinal==len(starts),'unjoined module completion')
                dones.append(ordinal)
        else:
            module_phase=False;stage_events.append(event)
    result=terminal[1].decode();error=int(terminal[2])
    positive=result!='REJECTED'
    if positive:
        state='clean' if result=='METADATA_CLEAN' else 'dirty'
        expected=[f'MODULE_SET_READY count={len(module_names)}'.encode(),b'STORAGE_BOUND',b'RO_BEGIN',b'RO_DONE',
            f'METADATA state={state} complete_root_admission=0'.encode(),b'STORAGE_CLOSED protected=1 cleanup_error=0']
        require(not error and starts==dones==list(range(1,len(module_names)+1)) and stage_events==expected,
            'metadata result lacks complete insertion/protection/cleanup')
    else:
        require(error>0,'negative terminal has no error')
        # Negative records are diagnostic, never a module/storage health claim.
        allowed=[f'MODULE_SET_READY count={len(module_names)}'.encode(),b'STORAGE_BOUND',b'RO_BEGIN',b'RO_DONE']
        position=0;closed=False
        for event in stage_events:
            if event.startswith(b'STORAGE_CLOSED '):
                require(not closed and position>=2 and
                    re.fullmatch(rb'STORAGE_CLOSED protected=[01] cleanup_error=[0-9]{1,4}',event),
                    'negative cleanup fields differ')
                closed=True
            elif event.startswith(b'METADATA '):
                require(not closed and position==4 and event in
                    (b'METADATA state=clean complete_root_admission=0',b'METADATA state=dirty complete_root_admission=0'),
                    'negative metadata order differs')
                position=5
            else:
                require(not closed and position<len(allowed) and event==allowed[position],'negative storage sequence differs')
                position+=1
        if stage_events:require(starts==dones==list(range(1,len(module_names)+1)),'storage follows partial modules')
    return dict(preparation_complete=positive,metadata_state='clean' if result=='METADATA_CLEAN' else
        'dirty' if result=='METADATA_DIRTY' else 'unproved',helper_error=error,events=len(events),
        module_attempts=len(starts),module_completions=len(dones),root_admitted=False,
        partition_readonly=positive,filesystem_mounted=False,persistent_writes=False)


class Records:
    def __init__(self,key,run,nonce,expected,module_names,*,domain=DOMAIN,parser=parse_log):
        self.key,self.run,self.nonce=key,run,nonce
        self.expected,self.module_names=expected,module_names
        self.domain,self.parser=domain,parser
        self.next=2;self.proof=None;self.log=bytearray();self.complete=False

    def accept(self,frame):
        require(not self.complete and frame.sequence==self.next,'early frame repeated or out of order')
        body=payload(frame,self.key,self.run,self.nonce,domain=self.domain)
        if self.next==2:
            require(frame.frame_type==PROOF and len(body)==176,'early PID1 proof missing')
            parent,child,status,size=struct.unpack('<4I',body[:16])
            require(parent==1 and child>1 and status in (0,1,2) and 0<size<=LOG_MAXIMUM,
                'early process/status/size fields differ')
            require(body[48:80].hex()==self.expected['shell_sha256'] and body[80:112].hex()==self.expected['init_sha256']
                and body[144:176].hex()==self.expected['helper_sha256'],'early executable binding differs')
            self.proof=dict(parent_pid=parent,observer_pid=child,helper_status=status,size=size,
                boot=body[16:48],log_hash=body[112:144])
        elif frame.frame_type==LOG:
            require(self.proof and 0<len(body)<=768 and len(self.log)+len(body)<=self.proof['size'],
                'early log frame outside declared bound')
            self.log.extend(body)
        else:
            require(frame.frame_type==END and self.proof and len(body)==32 and len(self.log)==self.proof['size'] and
                body==self.proof['log_hash']==hashlib.sha256(self.log).digest(),'early terminal/log digest differs')
            parsed=self.parser(bytes(self.log),self.run,self.module_names,self.proof['boot'])
            expected_status=2 if parsed['metadata_state']=='dirty' else 0 if parsed['preparation_complete'] else 1
            require(self.proof['helper_status']==expected_status,'process exit contradicts structured result')
            self.complete=True;self.result=dict(status='PASS_DEBIAN_EARLY_OBSERVED',debian_early_pid1=True,
                installed_debian_pid1=False,kernel_boot_identity_sha256=self.proof['boot'].hex(),
                nonce_sha256=hashlib.sha256(self.nonce).hexdigest(),log_size=len(self.log),
                log_sha256=self.proof['log_hash'].hex(),**parsed)
        self.next+=1


def replay(rx,tx,*,key,run,expected,module_names,domain=DOMAIN,parser=parse_log):
    require(len(tx)==80 and len(rx)<=MAXIMUM,'early transcript bound differs')
    sent=frames.decode_frame(tx)
    require(sent.frame_type==REQUEST and sent.sequence==1 and len(sent.payload)==64,'unselected early request')
    nonce=sent.payload[:32]
    require(any(nonce) and tx==request(key,run,nonce,domain=domain),'early request is not authenticated')
    records=Records(key,run,nonce,expected,module_names,domain=domain,parser=parser);offset=0
    while offset<len(rx):
        require(offset+16<=len(rx),'partial early frame header')
        size=int.from_bytes(rx[offset+6:offset+8],'little')
        require(size<=800 and offset+16+size<=len(rx),'partial or oversized early frame')
        records.accept(frames.decode_frame(rx[offset:offset+16+size]));offset+=16+size
    require(records.complete,'no complete authenticated early result')
    return records.result

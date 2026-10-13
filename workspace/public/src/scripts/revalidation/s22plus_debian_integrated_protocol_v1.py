"""One same-boot early-parent, root, installed-init and service transcript.

The initial request is a compound integrated-start command, not the old
read-only early observation. Its distinct domain prevents cross-protocol use.
"""
import hashlib
import re

import s22plus_debian_early_protocol_v1 as early
import s22plus_debian_handoff_protocol_v1 as handoff
from s22plus_native_records_v3 import require

DOMAIN=b'S22PLUS-FYG8-DEBIAN-INTEGRATED-v1'
UFS_LOG,UFS_END=179,180
MAXIMUM=early.MAXIMUM+handoff.MAXIMUM+16384
frames=early.frames


def request(key,run,nonce):return early.request(key,run,nonce,domain=DOMAIN)


def events(raw,run,boot,*,start,supervised=False):
    require(type(raw) is bytes and 0<len(raw)<=65536 and raw.endswith(b'\n'),'integrated RAM log truncated')
    rows=[]
    for ordinal,line in enumerate(raw.splitlines(),start):
        parsed=re.fullmatch(rb'FYG8_H0 seq=([1-9][0-9]*) ([\x20-\x7e]{1,350})',line)
        require(parsed and ordinal<=256 and int(parsed[1])==ordinal,'integrated RAM sequence/grammar differs')
        rows.append(parsed[2])
    first=re.fullmatch(rb'BEGIN run=([0-9a-f]{32}) boot=([0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}) parent='+ (b'supervised' if supervised else b'1'),rows[0])
    require(first and first[1]==run.hex().encode() and hashlib.sha256(first[2]).digest()==boot,
        'integrated RAM boot/run differs')
    return rows


def platform(raw,run,names,boot):
    rows=events(raw,run,boot,start=1)
    require(len(names)==74 and names[0]=='sec_log_buf' and len(set(names))==len(names),
        'integrated platform module declaration differs')
    expected=[rows[0],b'TARGET_GUARD_OK']
    for ordinal,name in enumerate(names,1):
        expected.append(f'MODULE_BEGIN ordinal={ordinal} name={name}'.encode())
        if name=='sec_log_buf':expected.append(b'LOGGER_BIND phase=0 error=0')
        expected.append(f'MODULE_DONE ordinal={ordinal} name={name}'.encode())
        if name=='qcom_spmi_pmic':expected.extend((b'PROVIDERS_BEGIN',b'PROVIDERS_READY mask=7'))
    expected.append(b'TERMINAL result=PLATFORM_READY error=0')
    require(rows==expected,'integrated platform/provider preparation incomplete')
    return dict(preparation_complete=True,metadata_state='not_observed',helper_error=0,events=len(rows),
        module_attempts=len(names),module_completions=len(names),root_admitted=False,
        partition_readonly=False,filesystem_mounted=False,persistent_writes=False,
        logger_bound=True,preclient_providers_ready=True)


def ufs(raw,run,names,boot):
    rows=events(raw,run,boot,start=220)
    require(len(names)==8 and len(set(names))==len(names),'integrated UFS module set differs')
    expected=[rows[0],b'TARGET_GUARD_OK']
    for ordinal,name in enumerate(names,75):
        expected.extend(f'MODULE_{phase} ordinal={ordinal} name={name}'.encode() for phase in ('BEGIN','DONE'))
    expected.append(b'TERMINAL result=UFS_MODULES_READY error=0')
    require(rows==expected,'integrated UFS insertion/child completion incomplete')
    return dict(module_completions=8,storage_admitted=False,filesystem_mounted=False,persistent_writes=False,
        log_size=len(raw),log_sha256=hashlib.sha256(raw).hexdigest())


class Records:
    def __init__(self,key,run,nonce,expected,module_names,selection):
        require(len(module_names)==82,'integrated module count differs')
        self.key,self.run,self.nonce=key,run,nonce
        self.names=module_names;self.selection=dict(selection,settlement='early-children-settled')
        self.initial=early.Records(key,run,nonce,expected,module_names[:74],domain=DOMAIN,parser=platform)
        self.ufs_log=bytearray();self.ufs_proof=None;self.handoff=None

    def accept(self,frame):
        if not self.initial.complete:self.initial.accept(frame);return
        if self.handoff is not None:self.handoff.accept(frame);return
        require(frame.sequence==self.initial.next,'integrated UFS frame out of order')
        body=early.payload(frame,self.key,self.run,self.nonce,domain=DOMAIN)
        if frame.frame_type==UFS_LOG:
            require(0<len(body)<=768 and len(self.ufs_log)+len(body)<=8192,'integrated UFS log bound differs')
            self.ufs_log.extend(body)
        else:
            require(frame.frame_type==UFS_END and len(body)==32 and
                body==hashlib.sha256(self.ufs_log).digest(),'integrated UFS terminal differs')
            boot=self.initial.proof['boot']
            self.ufs_proof=ufs(bytes(self.ufs_log),self.run,self.names[74:],boot)
            self.handoff=handoff.reader(self.key,self.run,self.nonce,boot,self.selection)
        self.initial.next+=1

    def projection(self):
        return dict(status='PASS_DEBIAN_INTEGRATED_RUNTIME' if self.handoff and self.handoff.released else
            'PARTIAL_DEBIAN_INTEGRATED' if self.initial.complete else 'NO_PROOF',
            initial_parent=self.initial.result if self.initial.complete else None,
            initial_shell_measurement='SAME_BOOT_BEFORE_TEMPORARY_PID1_EXEC',
            ufs=self.ufs_proof,debian_handoff=self.handoff.projection() if self.handoff else None,
            same_kernel_boot=self.handoff is not None,ssh_access_proved=False,replay_authorized=False)


def replay(rx,tx,*,key,run,expected,module_names,selection,complete=True):
    require(type(rx) is bytes and type(tx) is bytes and len(rx)<=MAXIMUM and 80<=len(tx)<=224,
        'integrated transcript bound differs')
    initial=frames.decode_frame(tx[:80]);nonce=initial.payload[:32]
    require(len(nonce)==32 and tx[:80]==request(key,run,nonce),'integrated start authentication differs')
    records=Records(key,run,nonce,expected,module_names,selection);offset=0;error=None
    try:
        while offset<len(rx):
            require(offset+16<=len(rx),'partial integrated frame header')
            size=int.from_bytes(rx[offset+6:offset+8],'little')
            require(size<=1023 and offset+16+size<=len(rx),'partial or oversized integrated frame')
            records.accept(frames.decode_frame(rx[offset:offset+16+size]));offset+=16+size
        continued=handoff.encode(key,run,nonce,handoff.CONTINUE,6)
        started=handoff.encode(key,run,nonce,handoff.START,handoff.START_SEQUENCE)
        released=handoff.encode(key,run,nonce,handoff.RELEASE,handoff.RELEASE_SEQUENCE)
        rest=tx[80:];state=records.handoff
        require((continued+started+released).startswith(rest),'integrated continuation bytes differ')
        require(not rest or state and state.proof,'continuation precedes root proof')
        require(len(rest)<=48 or state and state.init_proof,'start precedes installed PID1 proof')
        require(len(rest)<=96 or state and state.runtime_proof,'release precedes runtime proof')
        if state:
            require(not state.continued or len(rest)>=48,'continue ACK lacks request')
            require(not state.started or len(rest)>=96,'start ACK lacks request')
            require(not state.released or rest==continued+started+released,'release ACK lacks request')
        if complete:require(state and state.released and state.stop is None,'integrated runtime incomplete')
    except (ValueError,EOFError) as caught:
        if complete:raise
        error=str(caught)
    return dict(records.projection(),protocol_complete=complete,diagnostic_error=error,
        kernel_boot_proof=records.initial.proof['boot'].hex() if records.initial.proof else None,
        nonce_sha256=hashlib.sha256(nonce).hexdigest(),raw_prefix_bytes=offset,
        rx_sha256=hashlib.sha256(rx).hexdigest(),tx_sha256=hashlib.sha256(tx).hexdigest())

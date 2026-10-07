"""USB-first evidence: separate authentication domain and no storage proof."""
import hashlib
import hmac
import re

import s22plus_debian_early_protocol_v1 as common
from s22plus_native_records_v3 import require

DOMAIN=b'S22PLUS-FYG8-DEBIAN-USB-FIRST-v1'
MAXIMUM=common.MAXIMUM
frames=common.frames


def request(key,run,nonce):
    return common.request(key,run,nonce,domain=DOMAIN)


def parse_log(raw,run,module_names,boot):
    require(0<len(raw)<=common.LOG_MAXIMUM and raw.endswith(b'\n'),'USB record truncated')
    events=[]
    for seq,line in enumerate(raw.splitlines(),1):
        match=re.fullmatch(rb'FYG8_H0 seq=([1-9][0-9]*) ([\x20-\x7e]{1,350})',line)
        require(match and seq<=256 and int(match[1])==seq,'USB record grammar/order differs')
        events.append(match[2])
    require(len(events)>=3,'USB record incomplete')
    first=re.fullmatch(rb'BEGIN run=([0-9a-f]{32}) boot=([0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}) parent=1',events[0])
    require(first and first[1]==run.hex().encode() and hashlib.sha256(first[2]).digest()==boot,'USB boot/run differs')
    expected=[events[0],b'TARGET_GUARD_OK']
    for ordinal,name in enumerate(module_names,1):
        expected.extend(f'MODULE_{state} ordinal={ordinal} name={name}'.encode() for state in ('BEGIN','DONE'))
    expected.extend([f'MODULE_SET_READY count={len(module_names)}'.encode(),
        b'LOGGER_BOUND retention_after_reboot=unproved',b'TERMINAL result=PLATFORM_READY error=0'])
    require(events==expected,'USB result lacks exact platform/logger completion or contains storage work')
    return dict(preparation_complete=True,metadata_state='not_observed',helper_error=0,events=len(events),
        module_attempts=len(module_names),module_completions=len(module_names),root_admitted=False,
        partition_readonly=False,filesystem_mounted=False,persistent_writes=False,storage_accessed=False,
        logger_bound=True,retention_after_reboot=False)


def replay(rx,tx,*,key,run,expected,module_names):
    value=common.replay(rx,tx,key=key,run=run,expected=expected,module_names=module_names,domain=DOMAIN,parser=parse_log)
    value['status']='PASS_DEBIAN_USB_FIRST_OBSERVED'
    return value


class Records(common.Records):
    def __init__(self,key,run,nonce,expected,module_names):
        super().__init__(key,run,nonce,expected,module_names,domain=DOMAIN,parser=parse_log)

    def accept(self,frame):
        super().accept(frame)
        if self.complete:self.result['status']='PASS_DEBIAN_USB_FIRST_OBSERVED'


def retained(raw,*,key,run,boot=None):
    """Extract only authenticated current-run stage records from bounded last_kmsg.

    Partial/absent records stay partial/absent; they never negate execution.
    A kernel-ring readback and a post-return snapshot have distinct provenance.
    """
    require(type(raw) is bytes and len(raw)<=4*1024**2,'retained input bound differs')
    result=[];seen=set();observed_boot=None
    pattern=rb'S22USB1 run=([0-9a-f]{32}) boot=([0-9a-f-]{36}) seq=([1-9][0-9]*) mac=([0-9a-f]{64}) ([\x20-\x7e]{1,384})'
    for line in raw.splitlines():
        match=re.search(pattern,line)
        if not match or match[1]!=run.hex().encode():continue
        require(re.fullmatch(rb'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}',match[2]),'retained boot syntax differs')
        seq=int(match[3]);require(1<=seq<=256 and seq not in seen,'retained sequence duplicate/out of range')
        nonce=hashlib.sha256(match[2]).digest()
        require(hmac.compare_digest(bytes.fromhex(match[4].decode()),common.tag(key,run,nonce,240,seq,match[5],domain=DOMAIN)),
            'retained marker authentication failed')
        require((boot is None or nonce.hex()==boot) and (observed_boot is None or observed_boot==match[2]),'mixed retained boots')
        if result:require(seq>result[-1]['sequence'],'retained stage order reversed')
        seen.add(seq);observed_boot=match[2];result.append(dict(sequence=seq,event=match[5].decode()))
    return dict(status='AUTHENTICATED_PARTIAL_RECORDS' if result else 'NO_MATCHING_AUTHENTICATED_RECORDS',
        records=result,kernel_boot_identity_sha256=hashlib.sha256(observed_boot).hexdigest() if observed_boot else None,
        nonexecution_proved=False)

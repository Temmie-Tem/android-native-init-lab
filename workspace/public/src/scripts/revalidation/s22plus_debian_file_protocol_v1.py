"""Offline early-PID1 file evidence. No live USB receipt or clean-return claim."""
import hashlib
import hmac
import struct

import s22plus_debian_early_protocol_v1 as common
import s22plus_debian_usb_protocol_v1 as preparation
from s22plus_native_records_v3 import require

DOMAIN=b'S22PLUS-FYG8-DEBIAN-FILE-PILOT-v1'
HEADER,RECORD,RECORDS,MAXIMUM=256,128,8,16384


def decode(data,*,key,run,expected,module_names,allow_prefix=False,storage_first=False,diagnostic=False,autoboot=False):
    domain=DOMAIN;version=1;magic=b'S22FL01\0';record_magic=b'S22FLR1\0';count=RECORDS;phases=3
    if storage_first:
        import s22plus_debian_file_first_protocol_v1 as first
        domain=first.DOMAIN;version=2;magic=b'S22FL02\0';record_magic=b'S22FLR2\0';phases=len(first.CLIENTS);count=2+2*phases
    require(not diagnostic or storage_first,'diagnostic file requires storage-first')
    if diagnostic:
        domain=b'S22PLUS-FYG8-DEBIAN-FAILURE-v1';version=3;magic=b'S22FL03\0';record_magic=b'S22FLR3\0'
    if autoboot:
        from s22plus_debian_autoboot_profile_v1 import DOMAIN as domain
        require(diagnostic and storage_first,'automatic early record requires supervised storage-first')
    require(type(data) is bytes and HEADER<=len(data)<=MAXIMUM and len(key)==32 and len(run)==16,
        'file evidence size or identity differs')
    header=data[:HEADER];proof=header[32:208];boot=proof[16:48]
    require(header[:8]==magic and struct.unpack_from('<II',header,8)==(version,HEADER) and
        header[16:32]==run and not any(header[216:224]) and
        hmac.compare_digest(header[224:],common.tag(key,run,boot,0,0,header[:224],domain=domain)),
        'file header authentication differs')
    pid1,child,status,length=struct.unpack_from('<4I',proof)
    origin=struct.unpack_from('<Q',header,208)[0]
    require(origin<300000 and pid1==1 and child>1 and status==0 and 0<length<=MAXIMUM-HEADER-count*RECORD and
        proof[48:80].hex()==expected['shell_sha256'] and proof[80:112].hex()==expected['init_sha256'] and
        proof[144:176].hex()==expected['helper_sha256'],'file PID1 or source measurements differ')
    log=data[HEADER:HEADER+length]
    require(len(log)==length and hashlib.sha256(log).digest()==proof[112:144],
        'file preparation bytes are missing or changed')
    parsed=(first.parse_log if storage_first else preparation.parse_log)(log,run,module_names,boot,**(dict(supervised=True) if diagnostic else {}))
    # That shared parser describes the imported module-only phase, not this
    # later file writer. Its storage/persistence fields must not be exported.
    previous=header[224:];position=HEADER+length;rows=[];last_ms=0;failure=None
    wanted=[(1,0),*((kind,phase) for phase in range(1,phases+1) for kind in (2,3)),(4,0)]
    while position<len(data):
        raw=data[position:position+RECORD]
        try:
            require(len(raw)==RECORD and raw[:8]==record_magic,'file record is torn')
            seq,kind,elapsed,phase,error=struct.unpack_from('<IIQII',raw,8)
            require(seq==len(rows)<count and (kind,phase)==wanted[seq] and
                (not error or storage_first and kind==3 and 0<error<4096) and
                last_ms<=elapsed and origin+elapsed<300000 and not any(raw[32:64]) and raw[64:96]==previous and
                hmac.compare_digest(raw[96:],common.tag(key,run,boot,kind,seq,raw[:96],domain=domain)),
                'file record order, result or authentication differs')
        except ValueError as exc:
            if not allow_prefix:raise
            failure=str(exc);break
        rows.append(dict(sequence=seq,kind=kind,phase=phase,elapsed_ms=elapsed,error=error))
        previous=raw[96:];position+=RECORD;last_ms=elapsed
        if error:
            failure='client returned error '+str(error)
            require(position==len(data),'records follow a failed client')
            break
    complete=failure is None and len(rows)==count
    require(allow_prefix or complete,'file pilot completion is missing')
    result=dict(schema='s22plus-debian-file-first-evidence-v1' if storage_first else 's22plus-debian-file-evidence-v1',
        status='AUTHENTICATED_PILOT_PRE_UNMOUNT' if complete else 'AUTHENTICATED_PREFIX_ONLY',
        run_id_hex=run.hex(),kernel_boot_identity_sha256=boot.hex(),debian_early_pid1=True,
        installed_debian_pid1=False,module_completions=parsed['module_completions'],
        origin_ms=origin,records=rows,
        preparation_sha256=hashlib.sha256(log).hexdigest(),valid_prefix_bytes=position,tail_error=failure,
        pre_unmount_complete=complete,unmount_return_proved=False,clean_filesystem_proved=False,
        live_usb_proved=False,nonexecution_proved=False,replay_authorized=False,
        raw=dict(size=len(data),sha256=hashlib.sha256(data).hexdigest()))
    if diagnostic:result.update(schema='s22plus-debian-diagnostic-file-v1',pid1_ancestry='fixed-supervisor-child')
    if autoboot:result.update(schema='s22plus-debian-autoboot-early-file-v1',automatic_start=True)
    if storage_first:
        result.update(preparation_module_completions=parsed['module_completions'],
            client_attempt_records=sum(r['kind']==2 for r in rows),
            client_return_records=sum(r['kind']==3 and not r['error'] for r in rows),
            client_error=next((dict(name=first.CLIENTS[r['phase']-1],error=r['error']) for r in rows if r['error']),None))
    return result

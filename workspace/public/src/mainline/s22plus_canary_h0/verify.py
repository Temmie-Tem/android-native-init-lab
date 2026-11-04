#!/usr/bin/env python3
"""Offline H0 canary transcript verifier. No live socket/device entry point."""
import hashlib
import hmac
import json
from pathlib import Path
import struct
import tempfile
import uuid

if __package__:
    from .prepare import nodes, memreserve, require, digest
else:
    from prepare import nodes, memreserve, require, digest

DOMAIN=b'G0Q-MAINLINE-RAM-CANARY-v1'
REQUEST=72
RESPONSE=288
FDT_LIMIT=2*1024*1024
DEBIAN_SCHEMA='s22plus-mainline-debian-sysvinit-ram-v1'
SSH_SCHEMA='s22plus-mainline-debian-ssh-ram-v1'
DOWNLOAD_SCHEMA='s22plus-mainline-debian-download-ram-v1'


def has_ssh(manifest):
    return manifest.get('debian_ram',{}).get('schema')==SSH_SCHEMA


def has_download(manifest):
    return manifest.get('debian_ram',{}).get('schema')==DOWNLOAD_SCHEMA


def protocol(manifest=None):
    if manifest is not None and 'debian_ram' in manifest:
        if has_download(manifest):return b'G0Q-DEBIAN-DOWNLOAD-RAM-v1',b'G0QNRQ1\0',b'G0QNRS1\0',352
        if has_ssh(manifest):return b'G0Q-DEBIAN-SSH-RAM-v1',b'G0QSRQ1\0',b'G0QSRS1\0',352
        require(manifest['debian_ram'].get('schema')==DEBIAN_SCHEMA,'unknown Debian wire schema')
        return b'G0Q-DEBIAN-SYSVINIT-RAM-v1',b'G0QDRQ1\0',b'G0QDRS1\0',352
    return DOMAIN,b'G0QREQ1\0',b'G0QRSP1\0',256


def response_size(manifest):
    return protocol(manifest)[3]+32


def tag(key, identity, kind, payload, *, manifest=None):
    return hmac.new(key,protocol(manifest)[0]+identity+bytes([kind])+payload,hashlib.sha256).digest()


def request(key, identity, nonce, *, manifest=None):
    require(len(key)==len(identity)==len(nonce)==32,'request binding length')
    head=protocol(manifest)[1]+nonce
    return head+tag(key,identity,0,head,manifest=manifest)


def verify(raw_path, manifest, nonce, *, vm=False):
    path=Path(raw_path);require(path.stat().st_size<=response_size(manifest)+FDT_LIMIT,'response limit')
    return _verify(path.read_bytes(),manifest,nonce,vm=vm,directory=path.parent)


def verify_capture(handle,manifest,nonce):
    """Physical observation entry accepts only a sealed raw-capture handle."""
    import device_action_raw_capture_v1 as capture
    require(isinstance(handle,capture.RawCaptureHandle),'physical parser requires an immutable capture handle')
    capture.require_success(handle)
    raw=capture.read_stdout(handle,maximum=response_size(manifest)+FDT_LIMIT)
    return _verify(raw,manifest,nonce,vm=False,directory=handle.receipt_path.parent)


def _verify(raw,manifest,nonce,*,vm,directory):
    require(manifest['vm'] is vm,'VM/physical artifact mismatch')
    _,_,magic,body_size=protocol(manifest);size_limit=body_size+32
    require(size_limit<=len(raw)<=size_limit+FDT_LIMIT,'truncated or excessive response')
    body,auth,fdt=raw[:body_size],raw[body_size:size_limit],raw[size_limit:]
    key=Path(manifest['key_path']).read_bytes();identity=bytes.fromhex(manifest['candidate_id'])
    require(len(key)==len(identity)==len(nonce)==32,'response binding length')
    require(hmac.compare_digest(tag(key,identity,1,body,manifest=manifest),auth),'response HMAC')
    require(body[:8]==magic and body[8:40]==identity and body[40:72]==nonce,'response binding')
    extra={}
    if 'debian_ram' in manifest:
        child,parent,ns,level,previous=struct.unpack_from('<IIIII',body,256)
        runtime=manifest['debian_ram']
        require(child>1 and parent==1 and ns==1 and level==ord('2') and previous==ord('N'),
                'Debian PID1/direct-child/runlevel consistency')
        if has_ssh(manifest) or has_download(manifest):
            ready=struct.unpack_from('<I',body,276)[0]
            require(ready in (0,1) and body[280:288]==bytes(8), 'SSH startup field differs')
            extra['download_ready' if has_download(manifest) else 'ssh_ready']=bool(ready)
        else:require(body[276:288]==bytes(12),'reserved Debian fields differ')
        require(body[288:320].hex()==runtime['observer']['sha256'] and
                body[320:352].hex()==runtime['inittab_sha256'],'Debian observer/inittab identity')
        extra.update(runtime_schema=runtime['schema'],responder_pid=child,responder_ppid=parent,
                   pid_namespace_consistent=True,runlevel='2',previous_runlevel='N',
                   actual_observer_sha256=body[288:320].hex(),inittab_sha256=body[320:352].hex())
    uptime,pid,cpus,blocks,health,delta,size,variant=struct.unpack_from('<QIIIIQII',body,216)
    require(0<uptime<120000 and pid==1 and cpus==1 and blocks==0 and health==1,'health fields')
    require(20<=delta<=5000 and size==len(fdt) and 40<=size<=FDT_LIMIT,'timer/FDT fields')
    require(variant==int(vm),'runtime variant')
    require(hashlib.sha256(fdt).digest()==body[88:120],'FDT digest')
    require(body[120:152].hex()==manifest['init']['sha256'],'actual PID1 executable')
    release=manifest['kernel_release'].encode();require(len(release)<64,'release size')
    require(body[152:216]==release+b'\0'*(64-len(release)),'kernel release')
    require(any(body[72:88]),'empty boot identity')
    # libfdt rewrites /chosen and expands the live blob. Compare all semantic
    # properties, not input-file hash vs rewritten-file hash.
    with tempfile.TemporaryDirectory(prefix='g0q-fdt-',dir=directory) as temporary:
        measured=Path(temporary)/'live.dtb';measured.write_bytes(fdt);tree=nodes(measured)
        reservations=memreserve(measured)
    if vm:
        require(b'linux,dummy-virt' in tree['/'].get('compatible',b'').split(b'\0'),'VM FDT identity')
    else:
        expected_path=Path(manifest['dtb']['path'])
        require(digest(expected_path)==manifest['dtb']['sha256'],'expected DTB changed')
        require(reservations==memreserve(expected_path),'live FDT header reservations differ')
        require(fdt[20:32]==expected_path.read_bytes()[20:32], 'live FDT version/boot CPU differs')
        expected=nodes(expected_path)
        chosen=tree['/chosen']
        require(chosen.pop('linux,initrd-start')==struct.pack('>Q',manifest['initrd_address']),'initrd start')
        end=manifest['initrd_address']+manifest['initramfs']['size']
        require(chosen.pop('linux,initrd-end')==struct.pack('>Q',end),'initrd end')
        require(tree==expected,'live DT properties differ from packaged tree')
    status=('PASS_H0_VM_DEBIAN_SYSVINIT_RAM' if vm else 'AUTHENTICATED_DEBIAN_SYSVINIT_RAM_OBSERVATION') if extra else (
        'PASS_H0_VM_PID1_OBSERVER' if vm else 'AUTHENTICATED_CANARY_OBSERVATION')
    return {'status':status,**extra,
            'boot_id':str(uuid.UUID(bytes=body[72:88])),'uptime_ms':uptime,'timer_delta_ms':delta,
            'pid':pid,'online_cpus':cpus,'block_devices':blocks,'kernel_release':release.decode(),
            'live_fdt_sha256':body[88:120].hex(),'actual_pid1_sha256':body[120:152].hex(),
            'raw_sha256':hashlib.sha256(raw).hexdigest(),
            'recovery_proved':False,'hardware_boot_proved':False if vm else None}

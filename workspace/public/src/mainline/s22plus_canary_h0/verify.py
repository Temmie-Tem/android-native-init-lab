#!/usr/bin/env python3
"""Offline H0 canary transcript verifier. No live socket/device entry point."""
import hashlib
import hmac
import json
from pathlib import Path
import struct
import tempfile
import uuid

from prepare import nodes, memreserve, require, digest

DOMAIN=b'G0Q-MAINLINE-RAM-CANARY-v1'
REQUEST=72
RESPONSE=288
FDT_LIMIT=2*1024*1024


def tag(key, identity, kind, payload):
    return hmac.new(key,DOMAIN+identity+bytes([kind])+payload,hashlib.sha256).digest()


def request(key, identity, nonce):
    require(len(key)==len(identity)==len(nonce)==32,'request binding length')
    head=b'G0QREQ1\0'+nonce
    return head+tag(key,identity,0,head)


def verify(raw_path, manifest, nonce, *, vm=False):
    require(manifest['vm'] is vm,'VM/physical artifact mismatch')
    path=Path(raw_path);require(path.stat().st_size<=RESPONSE+FDT_LIMIT,'response limit')
    raw=path.read_bytes();require(len(raw)>=RESPONSE,'truncated response')
    body,auth,fdt=raw[:256],raw[256:288],raw[288:]
    key=Path(manifest['key_path']).read_bytes();identity=bytes.fromhex(manifest['candidate_id'])
    require(len(key)==len(identity)==len(nonce)==32,'response binding length')
    require(hmac.compare_digest(tag(key,identity,1,body),auth),'response HMAC')
    require(body[:8]==b'G0QRSP1\0' and body[8:40]==identity and body[40:72]==nonce,'response binding')
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
    with tempfile.TemporaryDirectory(prefix='g0q-fdt-',dir=path.parent) as temporary:
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
    return {'status':'PASS_H0_VM_PID1_OBSERVER' if vm else 'AUTHENTICATED_CANARY_OBSERVATION',
            'boot_id':str(uuid.UUID(bytes=body[72:88])),'uptime_ms':uptime,'timer_delta_ms':delta,
            'pid':pid,'online_cpus':cpus,'block_devices':blocks,'kernel_release':release.decode(),
            'live_fdt_sha256':body[88:120].hex(),'actual_pid1_sha256':body[120:152].hex(),
            'raw_sha256':hashlib.sha256(raw).hexdigest(),
            'recovery_proved':False,'hardware_boot_proved':False if vm else None}

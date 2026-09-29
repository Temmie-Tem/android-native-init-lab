"""ARM64 system-QEMU rehearsal of the actual parent/prepare/witness exec path."""
import argparse
import gzip
import json
import os
from pathlib import Path
import re
import select
import shutil
import socket
import stat
import subprocess
import sys
import tempfile
import time

import s22plus_native_root_inspect_vm_h0 as vm
import s22plus_native_staged_preflight_vm_h0 as previous
import s22plus_switch_root_h0 as producer
import s22plus_switch_root_protocol_v1 as protocol
from s22plus_native_records_v3 import pin,publish,read,require,verify

ROOT=vm.ROOT
BASE=ROOT/'workspace/private/outputs/s22plus-switch-root-h0-20260930-1'
KERNEL=BASE/'kernel-build/arch/arm64/boot/Image'
NONCE=bytes(range(1,33))
FAULTS={'complete':0,'unknown-child':1,'unknown-wait':2,'fd-holes':3,'early-reap':4,
    'dirty':0,'mismatch':0,'missing-witness':0,'noexec-witness':0,'wrong-root':0,
    'ram-noexec':0,'move-failure':0,'late-exec-failure':0,'checker-timeout':0,'checker-early-zero':0,
    'checker-descendant':0,'checker-wrong-output':0}


def setup(out,helpers,case,*,handoff=False):
    out=out.absolute();require(not out.exists() and out.is_relative_to(ROOT/'workspace/private/outputs'),'fresh VM output required')
    require(case in FAULTS,'unknown switch VM case');out.mkdir(mode=0o700)
    built=read(helpers/'result.json');require(built['virt'] is True,'VM needs virtual discovery helper')
    require((built.get('fault',0),built.get('checker_fault',0))=={
        'ram-noexec':(1,0),'move-failure':(2,0),'late-exec-failure':(3,0),'checker-timeout':(0,5),
        'checker-early-zero':(0,2),'checker-descendant':(0,7),'checker-wrong-output':(0,9)}.get(case,(0,0)),
        'VM case is not joined to its explicit fault build')
    parent=ROOT/'workspace/public/src/native-init/s22plus_switch_root_parent_v1.inc.c'
    (out/'s22plus_switch_root_parent_expanded.h').write_bytes(parent.read_bytes().replace(b'@@NAMESPACE@@',b'swvm'))
    (out/'s22plus_switch_root_vm_seal.h').write_text(producer.array('swvm_nonce',NONCE)+f'static const unsigned swvm_fault={FAULTS[case]};\n')
    vm.run(['aarch64-linux-gnu-gcc','-std=c11','-static','-Os','-ffunction-sections','-fdata-sections','-Wl,--gc-sections',
        '-Wall','-Wextra','-Werror','-Wno-unused-function','-Wno-unused-const-variable','-DS22_ROOT_INSPECT_VIRT_TEST',
        *(['-DS22_DEBIAN_HANDOFF_VM'] if handoff else []),
        '-I',helpers,'-I',out,'-I',producer.NATIVE,ROOT/'tests/s22plus_switch_root_vm_init.c','-o',out/'init'],out,'init-compile')
    entries=[(name,stat.S_IFDIR|0o755,b'') for name in ('bin','dev','proc','sys','run','s22-root-work','config')]
    entries += [('init',stat.S_IFREG|0o500,(out/'init').read_bytes()),
        ('s22-switch-root',stat.S_IFREG|0o500,verify(built['prepare']).read_bytes()),
        ('s22-switch-busybox',stat.S_IFREG|0o500,verify(built['busybox']).read_bytes()),
        ('s22-switch-witness',stat.S_IFREG|0o500,verify(built['witness']).read_bytes()),
        ('s22-root-inspect.table',stat.S_IFREG|0o400,verify(built['table']).read_bytes()),
        ('s22-fs-e2fsck',stat.S_IFREG|0o500,verify(built['checker']).read_bytes())]
    if handoff:
        require(built['schema']=='s22plus-debian-handoff-helpers-h0-v1','VM handoff helper schema differs')
        entries.extend(('s22-debian-'+name,stat.S_IFREG|(0o400 if name=='inittab' else 0o500),verify(row).read_bytes())
            for name,row in built['assets'].items())
    if case=='missing-witness':entries=[r for r in entries if r[0]!='s22-switch-witness']
    if case=='noexec-witness':entries=[(name,stat.S_IFREG|0o400,data) if name=='s22-switch-witness' else (name,mode,data) for name,mode,data in entries]
    (out/'initramfs.cpio.gz').write_bytes(gzip.compress(vm.h0.newc(entries),mtime=0))
    native=out/'native.ext4'
    vm.run(['cp','--reflink=auto','--sparse=always',previous.BASE/'complete.ext4',native],out,'copy-root')
    if case=='dirty':vm.debug(native,out,'dirty','ssv state 0')
    if case=='mismatch':vm.debug(native,out,'mismatch','set_inode_field /etc/lab-rootfs-id mode 0100600')
    if case=='wrong-root':vm.debug(native,out,'wrong-root','ssv uuid 01234567-1234-1234-1234-0123456789ab')
    binding=read(verify(vm.profile.filesystem.BINDING));vm.make_disk(native,out/'disk.img',binding)
    shutil.copyfile(vm.QEMU/'usr/bin/qemu-system-aarch64',out/'qemu-system-aarch64');(out/'qemu-system-aarch64').chmod(0o500)
    return publish(out/'setup.json',dict(schema='s22plus-debian-handoff-vm-v1' if handoff else
        's22plus-switch-root-vm-v1',case=case,helpers=pin(helpers/'result.json'),
        kernel=pin(KERNEL,maximum=128*1024*1024),initramfs=pin(out/'initramfs.cpio.gz',maximum=16*1024*1024),init=pin(out/'init'),
        qemu=pin(out/'qemu-system-aarch64',maximum=128*1024*1024),sources=[pin(p) for p in
            (Path(__file__),ROOT/'tests/s22plus_switch_root_vm_init.c',parent)],device_actions=0))


def run(out,key):
    setup_value=read(out/'setup.json');built=read(verify(setup_value['helpers']));case=setup_value['case']
    require(built['key_sha256']==protocol.health.digest(key),'VM key differs')
    before=vm.fixture_tools.sparse_digest(out/'disk.img');rx=bytearray();tx=b'';records=None;pending=bytearray()
    publish(out/'disk-before.json',dict(digest=before,device_actions=0))
    scratch=Path(tempfile.mkdtemp(prefix='s22-swvm-'));endpoint=scratch/'tty.sock'
    command=[verify(setup_value['qemu'],maximum=128*1024*1024),'-machine','virt','-cpu','cortex-a76','-smp','2','-m','1024',
        '-nic','none','-display','none','-monitor','none','-serial',f'file:{out}/serial.log','-no-reboot',
        '-chardev',f'socket,id=sw,path={endpoint},server=on,wait=off','-device','virtio-serial-device',
        '-device','virtconsole,chardev=sw','-kernel',verify(setup_value['kernel'],maximum=128*1024*1024),
        '-initrd',verify(setup_value['initramfs'],maximum=16*1024*1024),'-append','console=ttyAMA0 rdinit=/init panic=1',
        '-drive',f'if=none,id=root,file={out}/disk.img,format=raw',
        '-device','virtio-blk-device,drive=root,logical_block_size=4096,physical_block_size=4096']
    (out/'command.json').write_text(json.dumps([str(x) for x in command])+'\n')
    try:
        with (out/'qemu.log').open('xb') as log,(out/'rx.bin').open('xb') as raw:
            process=subprocess.Popen([str(x) for x in command],stdout=log,stderr=subprocess.STDOUT,
                env=dict(os.environ,LD_LIBRARY_PATH=str(vm.QEMU/'usr/lib/x86_64-linux-gnu')))
            try:
                deadline=time.monotonic()+150
                while not endpoint.exists() and process.poll() is None and time.monotonic()<deadline:time.sleep(.02)
                with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as stream:
                    stream.connect(str(endpoint));stream.setblocking(False)
                    while time.monotonic()<deadline:
                        ready,_,_=select.select([stream],[],[],.05)
                        if ready:
                            part=stream.recv(4096)
                            if not part:break
                            raw.write(part);raw.flush();os.fsync(raw.fileno());rx.extend(part);pending.extend(part)
                            require(len(rx)<=protocol.MAXIMUM,'VM stream overflow')
                            while len(pending)>=16:
                                size=protocol.frames.HEADER.unpack(pending[:16])[3];require(size<=1023,'VM frame overflow')
                                if len(pending)<16+size:break
                                frame=protocol.frames.decode_frame(bytes(pending[:16+size]));del pending[:16+size]
                                if records is None:
                                    boot=re.findall(rb'SWVM_BOOT ([0-9a-f]{64})\r?\n',(out/'serial.log').read_bytes())
                                    require(len(boot)==1,'VM pre-transition boot evidence absent')
                                    records=protocol.Records(key,bytes.fromhex(built['run_id_hex']),NONCE,
                                        bytes.fromhex(boot[0].decode()),built['witness']['sha256'])
                                records.accept(frame)
                                if records.proof is not None and not tx:
                                    tx=protocol.encode(key,records.run,NONCE,protocol.RETURN,6)
                                    (out/'tx.bin').write_bytes(tx);stream.sendall(tx)
                        if process.poll() is not None:break
                process.wait(timeout=max(1,deadline-time.monotonic()))
            finally:
                if process.poll() is None:process.kill();process.wait()
        require(process.returncode==0,'VM process failed')
        require(not pending,'VM stream ended in a partial frame')
        serial=(out/'serial.log').read_bytes()
        require((b'Kernel panic - not syncing: Attempted to kill init!' in serial) if case=='late-exec-failure'
            else b'reboot: Power down' in serial,'VM terminal boundary differs')
        after=vm.fixture_tools.sparse_digest(out/'disk.img');require(before==after,'switch root changed writable backing disk')
        positive=case in ('complete','fd-holes','early-reap')
        require(bool(records and records.proof and records.returned)==positive,'switch VM outcome differs')
        capture=pin(out/'rx.bin') if rx else dict(path=str(out/'rx.bin'),size=0,sha256=protocol.health.digest(b''))
        return publish(out/'result.json',dict(schema='s22plus-switch-root-vm-result-v1',setup=pin(out/'setup.json'),
            case=case,result=records.projection() if records else dict(status='NO_PROOF_PARENT_REJECTED'),
            rx=capture,serial=pin(out/'serial.log'),disk_before=before,disk_after=after,disk_unchanged=True,
            scope='REAL_ARM64_VIRT_NOT_SAMSUNG',device_actions=0))
    finally:shutil.rmtree(scratch)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=('setup','run'))
    p.add_argument('--output',type=Path,required=True);p.add_argument('--helpers',type=Path);p.add_argument('--case',choices=tuple(FAULTS))
    p.add_argument('--key',type=Path);args=p.parse_args();out=args.output.absolute()
    print((setup(out,args.helpers.absolute(),args.case) if args.command=='setup' else run(out,args.key.read_bytes()))['sha256'])

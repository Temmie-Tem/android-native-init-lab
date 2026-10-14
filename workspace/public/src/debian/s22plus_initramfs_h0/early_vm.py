#!/usr/bin/env python3
"""Real ARM64 producer/consumer with stock vendor + Debian archive extraction.

Board/module/UFS/USB hardware is substituted; actual PID1, dynamic paths,
protected block reads/ioctls, record reads, HMAC frames and failure exits run.
"""
import argparse
from dataclasses import replace
import gzip
import json
import os
from pathlib import Path
import shutil
import socket
import stat
import subprocess
import sys
import tempfile
import time

import early
import fyg8
import fyg8_vm as vm
import h0
import s22plus_debian_early_protocol_v1 as protocol


def prepare(out,build,case):
    request=json.loads((build/'request.json').read_text());out.mkdir(mode=0o700)
    inputs=h0.private(request['inputs']);packages=h0.private(request['packages'])
    helper=out/'helper'
    changed=early.prepare(helper,inputs,packages,run=request['run_id'],key=(build/'key').read_bytes(),virt=True)
    entries=list(fyg8.debian_entries(build/'initramfs-a.cpio.gz'))
    for i,e in enumerate(entries):
        if e.name=='usr/sbin/fyg8-prepare':entries[i]=replace(e,data=(helper/'fyg8-prepare').read_bytes())
        elif e.name=='usr/sbin/early-observer':entries[i]=replace(e,data=(helper/'early-observer').read_bytes())
        elif e.name=='scripts/fyg8-dev':
            text=e.data.decode();h0.require(text.endswith('fyg8_stop\n'),'unexpected physical terminal hook')
            text=text[:-len('fyg8_stop\n')]+'''early_status=$?
printf 'EARLY_VM_TERMINAL observer=%s prepare=%s\\n' "$early_status" "$fyg8_status"
printf 'EARLY_VM_RO native=%s disk=%s userdata=%s\\n' "$(cat /sys/class/block/vda41/ro)" "$(cat /sys/class/block/vda/ro)" "$(cat /sys/class/block/vda40/ro)"
poweroff -f
'''
            entries[i]=replace(e,data=text.encode())
    model=entries[0]
    entries.append(replace(model,name='lab/fault',encoded_name='lab/fault',inode=max(x.inode for x in entries)+1,
        mode=stat.S_IFREG|0o400,nlink=1,data=b'none\n'))
    raw=vm.newc(entries)
    vendor=fyg8.memory.vendor
    retained=fyg8.memory.base.stable(h0.ROOT/vendor.DEFAULT_VENDOR_RAMDISK,
        dict(size=vendor.EXPECTED_VENDOR_RAMDISK_SIZE,sha256=vendor.EXPECTED_VENDOR_RAMDISK_SHA256))
    vendor_raw=fyg8.boot.decompress_lz4_stream_python(retained,maximum=128*1024**2)
    # Separate gzip members preserve the kernel's sequential extraction order.
    (out/'initramfs.cpio.gz').write_bytes(gzip.compress(vendor_raw,mtime=0)+gzip.compress(raw,mtime=0))
    native=out/'native.ext4';disk=out/'disk.img'
    h0.run(['cp','--reflink=auto','--sparse=always',h0.regular(vm.previous.BASE/'complete.ext4'),native],out/'copy.log')
    if case=='dirty':
        with native.open('rb') as stream:stream.seek(1024+0x60);bits=int.from_bytes(stream.read(4),'little')
        vm.fixture.debug(native,out,'dirty',f'ssv feature_incompat {bits|4}')
    binding=json.loads(fyg8.verify(request['binding']['filesystem_binding']).read_text())
    vm.fixture.make_disk(native,disk,binding)
    return changed


def run(out,build,case):
    selection=prepare(out,build,case)
    before=vm.fixture.fixture_tools.sparse_digest(out/'disk.img');h0.publish(out/'disk-before.json',before)
    scratch=Path(tempfile.mkdtemp(prefix='s22-early-vm-'));endpoint=scratch/'wire.sock'
    command=[vm.fixture.QEMU/'usr/bin/qemu-system-aarch64','-machine','virt','-cpu','cortex-a76','-smp','2','-m','512',
        '-nic','none','-display','none','-monitor','none','-serial',f'file:{out}/serial.log','-no-reboot',
        '-chardev',f'socket,id=early,path={endpoint},server=on,wait=off','-device','virtio-serial-device',
        '-device','virtconsole,chardev=early','-kernel',h0.regular(vm.KERNEL),
        '-initrd',out/'initramfs.cpio.gz','-append',vm.KERNEL_COMMAND_LINE,
        '-drive',f'if=none,id=root,file={out}/disk.img,format=raw',
        '-device','virtio-blk-device,drive=root,logical_block_size=4096,physical_block_size=4096']
    h0.publish(out/'command.json',[str(x) for x in command]);rx=bytearray();nonce=bytes(range(1,33))
    key=(build/'key').read_bytes();run_id=bytes.fromhex(selection['run_id'])
    tx=protocol.request(key,run_id,nonce)
    if case=='bad-auth':
        frame=protocol.frames.decode_frame(tx)
        tx=protocol.frames.encode_frame(frame.frame_type,frame.sequence,frame.payload[:-1]+bytes([frame.payload[-1]^1]))
    (out/'tx.bin').write_bytes(tx)
    process=None
    try:
        with (out/'qemu.log').open('xb') as log,(out/'rx.bin').open('xb') as output:
            process=subprocess.Popen([str(x) for x in command],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,
                env=dict(os.environ,LD_LIBRARY_PATH=str(vm.fixture.QEMU/'usr/lib/x86_64-linux-gnu')))
            deadline=time.monotonic()+90
            while not endpoint.exists() and process.poll() is None and time.monotonic()<deadline:time.sleep(.01)
            with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as stream:
                stream.settimeout(90);stream.connect(str(endpoint))
                while time.monotonic()<deadline:
                    if (out/'serial.log').exists() and b'EARLY_VM_WIRE_READY' in (out/'serial.log').read_bytes():break
                    h0.require(process.poll() is None,'VM exited before raw channel preparation')
                    time.sleep(.01)
                else:raise TimeoutError('VM raw channel not prepared')
                stream.sendall(tx)
                while True:
                    try:part=stream.recv(4096)
                    except ConnectionResetError:break  # QEMU closes on guest poweroff; validate raw+terminal below.
                    if not part:break
                    output.write(part);output.flush();os.fsync(output.fileno());rx.extend(part)
                    h0.require(len(rx)<=protocol.MAXIMUM,'wire bound exceeded')
            process.wait(timeout=max(1,deadline-time.monotonic()))
        raw=(out/'serial.log').read_bytes().replace(b'\r',b'')
        h0.require(process.returncode==0 and b'reboot: Power down' in raw,'VM did not finish')
        after=vm.fixture.fixture_tools.sparse_digest(out/'disk.img');h0.require(before==after,'disk changed')
        if case=='bad-auth':
            h0.require(not rx and b'EARLY_VM_TERMINAL observer=1 prepare=0' in raw,'bad request was not rejected')
            result=dict(status='PASS_UNAUTHENTICATED_REQUEST_REJECTED')
        else:
            result=protocol.replay(bytes(rx),tx,key=key,run=run_id,expected=selection['measured'],
                module_names=[m['runtime_name'] for m in fyg8.verify_inventory(h0.private(selection['inputs']))['modules']])
            h0.require(result['metadata_state']==case and b'EARLY_VM_TERMINAL observer=0 ' in raw and
                b'EARLY_VM_RO native=1 disk=0 userdata=0' in raw,'producer/consumer outcome differs')
        value=dict(case=case,status='PASS',proof=result,disk_before=before,disk_after=after,device_actions=0,
            scope='REAL_ARM64_WITH_HARDWARE_SUBSTITUTIONS_AND_VENDOR_OVERLAY',
            rx_sha256=h0.sha(out/'rx.bin'),tx_sha256=h0.sha(out/'tx.bin'),serial_sha256=h0.sha(out/'serial.log'),
            expected=selection['measured'],run_id=selection['run_id'],initramfs_sha256=h0.sha(out/'initramfs.cpio.gz'))
        h0.publish(out/'result.json',value);print(case,'PASS',flush=True);return value
    finally:
        if process is not None and process.poll() is None:process.kill();process.wait()
        shutil.rmtree(scratch)


def suite(out,build):
    out=h0.private(out,fresh=True);build=h0.private(build)
    h0.require((build/'build.json').is_file(),'unqualified initramfs construction')
    sources=early.snapshot(out)
    values=[run(out/case,build,case) for case in ('clean','dirty','bad-auth')]
    for row in sources:h0.require(h0.sha(h0.ROOT/row['path'])==row['sha256'],'VM source changed during run')
    h0.publish(out/'result.json',dict(status='PASS',cases=values,build_sha256=h0.sha(build/'build.json'),
        source_inputs=sources,device_actions=0))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--build',type=Path,required=True)
    args=p.parse_args();suite(args.output,args.build)

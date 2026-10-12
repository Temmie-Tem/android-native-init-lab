#!/usr/bin/env python3
"""Actual ARM64 Debian PID1/stage producer; only board/module binding substituted."""
import argparse
from dataclasses import replace
import gzip
import json
import os
from pathlib import Path
import stat
import subprocess

import fyg8
import fyg8_vm as vm
import h0
import stage_probe as builder
import s22plus_debian_stage_profile_v1 as profile
import s22plus_debian_stage_protocol_v1 as protocol
from s22plus_native_records_v3 import pin


def prepare(out,build,case):
    request=json.loads((build/'request.json').read_text());out.mkdir(mode=0o700)
    selection=builder.prepare(out/'helper',h0.private(request['inputs']),h0.private(request['packages']),
        run=request['run_id'],key=(build/'key').read_bytes(),virt=True)
    entries=list(fyg8.debian_entries(build/'initramfs-a.cpio.gz'))
    for i,e in enumerate(entries):
        if e.name=='usr/sbin/fyg8-prepare':entries[i]=replace(e,data=(out/'helper/fyg8-prepare').read_bytes())
        elif e.name=='scripts/fyg8-dev':
            text=e.data.decode();h0.require(text.endswith('fyg8_stop\n'),'stage terminal hook differs')
            if case=='logger-off':text=text.replace('/sbin/fyg8-prepare\n',
                'printf "off\\n" >/proc/sys/kernel/printk_devkmsg\nprintf "STAGE_VM_LOGGER_MODE=%s\\n" "$(cat /proc/sys/kernel/printk_devkmsg)"\n/sbin/fyg8-prepare\n')
            if case=='bad-parent':text=text.replace('/sbin/fyg8-prepare\n',
                'printf "\\n# VM actual parent script hash mutation\\n" >>/init\n/sbin/fyg8-prepare\n')
            text=text[:-len('fyg8_stop\n')]+'''printf 'STAGE_VM_TERMINAL status=%s\\n' "$fyg8_status"
poweroff -f
'''
            entries[i]=replace(e,data=text.encode())
    model=entries[0]
    entries.append(replace(model,name='lab/fault',encoded_name='lab/fault',inode=max(e.inode for e in entries)+1,
        mode=stat.S_IFREG|0o400,nlink=1,data=(case+'\n').encode() if case in ('insert-error','binding-missing','late') else b'none\n'))
    vendor=fyg8.memory.vendor
    raw=fyg8.memory.base.stable(h0.ROOT/vendor.DEFAULT_VENDOR_RAMDISK,
        dict(size=vendor.EXPECTED_VENDOR_RAMDISK_SIZE,sha256=vendor.EXPECTED_VENDOR_RAMDISK_SHA256))
    overlay=fyg8.boot.decompress_lz4_stream_python(raw,maximum=128*1024**2)
    (out/'initramfs.cpio.gz').write_bytes(gzip.compress(overlay,mtime=0)+gzip.compress(vm.newc(entries),mtime=0))
    with (out/'disk.img').open('xb') as f:f.truncate(64*1024**2)
    return selection


def run(out,build,case):
    selection=prepare(out,build,case);before=h0.sha(out/'disk.img')
    command=[vm.fixture.QEMU/'usr/bin/qemu-system-aarch64','-machine','virt','-cpu','cortex-a76','-smp','2','-m','512',
        '-nic','none','-display','none','-monitor','none','-serial',f'file:{out}/serial.log','-no-reboot',
        '-kernel',h0.regular(vm.KERNEL),'-initrd',out/'initramfs.cpio.gz','-append','console=ttyAMA0 rdinit=/init panic=1',
        '-drive',f'if=none,id=sentinel,file={out}/disk.img,format=raw','-device','virtio-blk-device,drive=sentinel']
    h0.publish(out/'command.json',[str(x) for x in command])
    with (out/'qemu.log').open('xb') as log:
        result=subprocess.run([str(x) for x in command],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,
            timeout=100,env=dict(os.environ,LD_LIBRARY_PATH=str(vm.fixture.QEMU/'usr/lib/x86_64-linux-gnu')))
    serial=(out/'serial.log').read_bytes()
    h0.require(result.returncode==0 and b'reboot: Power down' in serial,'VM did not shut down')
    after=h0.sha(out/'disk.img');h0.require(before==after,'stage VM disk changed')
    proof=protocol.retained(serial,key=(build/'key').read_bytes(),run=bytes.fromhex(selection['run_id']),
        expected=selection['measured'],logger_sha256=builder.LOGGER['sha256'])
    insertions=serial.count(b'STAGE_VM_INSERT_ONCE')
    status='PASS_RETAINED_EARLY_STAGE' if case=='normal' else (
        'NO_AUTHENTICATED_STAGE' if case in ('logger-off','late') else 'RETAINED_STAGE_REJECTED')
    h0.require(proof['status']==status,'VM stage evidence differs')
    h0.require(b'STAGE_VM_TERMINAL status='+ (b'0' if case=='normal' else b'1') in serial,'VM helper exit differs')
    h0.require(insertions==(1 if case in ('normal','insert-error','binding-missing') else 0),'module invocation count differs')
    if case=='logger-off':h0.require(b'STAGE_VM_LOGGER_MODE=off' in serial,'logger-off fixture did not activate')
    if case=='bad-parent':h0.require(not proof['debian_early_pid1'],'changed /init gained parent proof')
    value=dict(case=case,status='PASS',proof=proof,device_actions=0,disk_before=before,disk_after=after,
        scope='ARM64_PID1_PRINTK_CURRENT_RING_WITH_BOARD_MODULE_SUBSTITUTIONS_NOT_PHYSICAL_RETENTION',
        run_id=selection['run_id'],expected=selection['measured'],capture=pin(out/'serial.log',maximum=4*1024**2),
        insertions=insertions)
    h0.publish(out/'result.json',value);print(case,'PASS',flush=True);return value


def suite(out,build):
    out=h0.private(out,fresh=True);build=h0.private(build);sources=builder.snapshot(out)
    built=json.loads((build/'build.json').read_text())
    values=[run(out/case,build,case) for case in profile.CASES]
    for row in sources:h0.require(h0.sha(h0.ROOT/row['path'])==row['sha256'],'stage VM source changed during run')
    result=dict(status='PASS',cases=values,build_sha256=h0.sha(build/'build.json'),source_inputs=sources,device_actions=0)
    profile.vm_results(result,dict(built,key=pin(build/'key',maximum=32)))
    h0.publish(out/'result.json',result)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('output','build'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();suite(args.output,args.build)

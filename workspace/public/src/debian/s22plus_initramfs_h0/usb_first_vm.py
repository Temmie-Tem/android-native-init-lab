#!/usr/bin/env python3
"""Real ARM64 PID1, selected logging and USB protocol; board/gadget substituted."""
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
import tempfile
import time

import fyg8
import fyg8_vm as vm
import h0
import usb_first as build_api
import s22plus_debian_usb_protocol_v1 as protocol


def prepare(out,build,case):
    request=json.loads((build/'request.json').read_text());out.mkdir(mode=0o700)
    mode=build_api.profile_api.usb_logging_mode(request)
    selection=build_api.prepare(out/'helper',h0.private(request['inputs']),h0.private(request['packages']),
        run=request['run_id'],key=(build/'key').read_bytes(),virt=True,logging_mode=mode)
    entries=list(fyg8.debian_entries(build/'initramfs-a.cpio.gz'))
    for i,e in enumerate(entries):
        if e.name in ('usr/sbin/fyg8-prepare','usr/sbin/early-observer'):
            entries[i]=replace(e,data=(out/'helper'/Path(e.name).name).read_bytes())
        elif e.name=='scripts/fyg8-dev':
            text=e.data.decode();h0.require(text.endswith('fyg8_stop\n'),'USB terminal hook differs')
            if case=='logger-off':text=text.replace('/sbin/fyg8-prepare\n',
                'printf "off\\n" >/proc/sys/kernel/printk_devkmsg\nprintf "USB_VM_LOGGER_MODE=%s\\n" "$(cat /proc/sys/kernel/printk_devkmsg)"\n/sbin/fyg8-prepare\n')
            if mode=='ram-only':text=text.replace('/sbin/fyg8-prepare\n',
                '[ ! -e /dev/kmsg ] && printf "USB_VM_NO_KMSG_NODE\\n"\n/sbin/fyg8-prepare\n')
            if case=='ram-log-missing':text=text.replace('/sbin/early-observer "$fyg8_status"\n',
                'rm /run/initramfs/fyg8-events\n/sbin/early-observer "$fyg8_status"\n')
            text=text[:-len('fyg8_stop\n')]+'''observer_status=$?
printf 'USB_VM_TERMINAL observer=%s prepare=%s\\n' "$observer_status" "$fyg8_status"
cat /run/initramfs/fyg8-events
poweroff -f
'''
            entries[i]=replace(e,data=text.encode())
    model=entries[0]
    entries.append(replace(model,name='lab/fault',encoded_name='lab/fault',inode=max(e.inode for e in entries)+1,
        mode=stat.S_IFREG|0o400,nlink=1,data=b'insert-error\n' if case=='insert-error' else b'none\n'))
    vendor=fyg8.memory.vendor
    raw=fyg8.memory.base.stable(h0.ROOT/vendor.DEFAULT_VENDOR_RAMDISK,
        dict(size=vendor.EXPECTED_VENDOR_RAMDISK_SIZE,sha256=vendor.EXPECTED_VENDOR_RAMDISK_SHA256))
    overlay=fyg8.boot.decompress_lz4_stream_python(raw,maximum=128*1024**2)
    (out/'initramfs.cpio.gz').write_bytes(gzip.compress(overlay,mtime=0)+gzip.compress(vm.newc(entries),mtime=0))
    # No root/filesystem fixture is required for a USB-only capability.
    with (out/'disk.img').open('xb') as stream:stream.truncate(64*1024**2)
    return selection


def run(out,build,case):
    selection=prepare(out,build,case);before=h0.sha(out/'disk.img')
    ram_only=build_api.profile_api.usb_logging_mode(selection)=='ram-only'
    positive=case=='normal' or (ram_only and case=='logger-off')
    scratch=Path(tempfile.mkdtemp(prefix='s22-usb-vm-'));endpoint=scratch/'wire.sock'
    command=[vm.fixture.QEMU/'usr/bin/qemu-system-aarch64','-machine','virt','-cpu','cortex-a76','-smp','2','-m','512',
        '-nic','none','-display','none','-monitor','none','-serial',f'file:{out}/serial.log','-no-reboot',
        '-chardev',f'socket,id=early,path={endpoint},server=on,wait=off','-device','virtio-serial-device',
        '-device','virtconsole,chardev=early','-kernel',h0.regular(vm.KERNEL),
        '-initrd',out/'initramfs.cpio.gz','-append',vm.KERNEL_COMMAND_LINE,
        '-drive',f'if=none,id=sentinel,file={out}/disk.img,format=raw','-device','virtio-blk-device,drive=sentinel']
    h0.publish(out/'command.json',[str(x) for x in command]);rx=bytearray();nonce=bytes(range(1,33))
    key=(build/'key').read_bytes();run_id=bytes.fromhex(selection['run_id']);tx=protocol.request(key,run_id,nonce)
    if case=='bad-auth':
        frame=protocol.frames.decode_frame(tx)
        tx=protocol.frames.encode_frame(frame.frame_type,frame.sequence,frame.payload[:-1]+bytes([frame.payload[-1]^1]))
    (out/'tx.bin').write_bytes(tx);process=None
    try:
        with (out/'qemu.log').open('xb') as log,(out/'rx.bin').open('xb') as output:
            process=subprocess.Popen([str(x) for x in command],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,
                env=dict(os.environ,LD_LIBRARY_PATH=str(vm.fixture.QEMU/'usr/lib/x86_64-linux-gnu')))
            deadline=time.monotonic()+90;wire=False
            while time.monotonic()<deadline and process.poll() is None:
                if (out/'serial.log').exists() and b'EARLY_VM_WIRE_READY' in (out/'serial.log').read_bytes():wire=True;break
                time.sleep(.02)
            if case=='logger-off':h0.require(b'USB_VM_LOGGER_MODE=off' in (out/'serial.log').read_bytes(),'logger-off fixture did not activate')
            if case in ('insert-error','ram-log-missing') or (case=='logger-off' and not ram_only):
                h0.require(not wire,'failed preparation published USB')
            else:
                h0.require(wire,'VM did not establish raw USB substitute')
                with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as stream:
                    stream.settimeout(90);stream.connect(str(endpoint));stream.sendall(tx)
                    while time.monotonic()<deadline:
                        try:part=stream.recv(4096)
                        except ConnectionResetError:break
                        if not part:break
                        output.write(part);output.flush();os.fsync(output.fileno());rx.extend(part)
                        h0.require(len(rx)<=protocol.MAXIMUM,'VM wire bound exceeded')
            process.wait(timeout=max(1,deadline-time.monotonic()))
        serial=(out/'serial.log').read_bytes().replace(b'\r',b'')
        h0.require(process.returncode==0 and b'reboot: Power down' in serial,'VM did not shut down')
        if ram_only:h0.require(b'USB_VM_NO_KMSG_NODE' in serial and b'S22USB1 run=' not in serial,
            'RAM-only case acquired a printk dependency')
        after=h0.sha(out/'disk.img');h0.require(before==after,'VM sentinel disk changed')
        if positive:
            result=protocol.replay(bytes(rx),tx,key=key,run=run_id,expected=selection['measured'],
                module_names=[m['runtime_name'] for m in selection['modules']])
            h0.require(b'USB_VM_TERMINAL observer=0 prepare=0' in serial,'VM success exit differs')
            if not ram_only:
                markers=protocol.retained(serial,key=key,run=run_id,boot=result['kernel_boot_identity_sha256'])
                h0.require([r['sequence'] for r in markers['records']]==list(range(1,2*len(selection['modules'])+6))+list(range(200,207)),
                    'kernel-ring marker readback incomplete')
                # Serial is current-boot printk evidence, not a post-reboot snapshot.
                markers['provenance']='VM_CURRENT_BOOT_PRINTK_NOT_PHYSICAL_RETENTION'
                h0.publish(out/'markers.json',markers)
        elif case=='bad-auth':
            h0.require(not rx and b'USB_VM_TERMINAL observer=1 prepare=0' in serial,'bad HMAC accepted')
            result=dict(status='PASS_AUTH_REJECTION')
        else:
            expected=b'USB_VM_TERMINAL observer=1 prepare='+ (b'0' if case=='ram-log-missing' else b'1')
            h0.require(not rx and expected in serial,'preparation/evidence failure not stopped')
            result=dict(status='PASS_PREPARATION_REJECTION')
        value=dict(case=case,status='PASS',proof=result,device_actions=0,disk_before=before,disk_after=after,
            scope='ARM64_PID1_LOGGING_AND_PROTOCOL_WITH_BOARD_MODULE_GADGET_SUBSTITUTIONS',logging_mode=selection['logging_mode'],
            run_id=selection['run_id'],expected=selection['measured'],rx_sha256=h0.sha(out/'rx.bin'),
            tx_sha256=h0.sha(out/'tx.bin'),serial_sha256=h0.sha(out/'serial.log'))
        h0.publish(out/'result.json',value);print(case,'PASS',flush=True);return value
    finally:
        if process is not None and process.poll() is None:process.kill();process.wait()
        shutil.rmtree(scratch)


def suite(out,build):
    out=h0.private(out,fresh=True);build=h0.private(build);sources=build_api.snapshot(out)
    h0.require((build/'build.json').is_file(),'physical construction missing')
    built=json.loads((build/'build.json').read_text())
    values=[run(out/case,build,case) for case in build_api.profile_api.vm_cases(built)]
    for row in sources:h0.require(h0.sha(h0.ROOT/row['path'])==row['sha256'],'VM source changed during run')
    h0.publish(out/'result.json',dict(status='PASS',cases=values,build_sha256=h0.sha(build/'build.json'),source_inputs=sources,device_actions=0))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('output','build'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();suite(args.output,args.build)

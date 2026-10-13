#!/usr/bin/env python3
"""Real Debian /init through installed PID1, services, SSH and clean shutdown.

Only Samsung board/module/provider/UDC discovery and the network device are
substituted. The root, checks, ELF execution, parent evidence, FD ownership,
startup children, liveness sampling and all protocol consumers execute.
"""
import argparse
from dataclasses import replace
import gzip
import ipaddress
import json
import os
from pathlib import Path
import select
import shutil
import socket
import stat
import subprocess
import tempfile
import time

import integrated as build_api
import fyg8_vm as vm
import h0
import s22plus_debian_handoff_vm_h0 as lifecycle
import s22plus_debian_integrated_protocol_v1 as protocol
import device_action_raw_capture_v1 as raw
from s22plus_native_records_v3 import pin,publish,read,require,verify

CASES=('normal','module-byte','provider-missing','parent-byte','bad-auth','ufs-failure','fd-leak','dirty','mismatch')
NONCE=bytes(range(1,33))


def prepare(out,build,helper,case):
    require(case in CASES,'unselected integrated VM case');out.mkdir(mode=0o700)
    physical=read(build/'build.json');virtual=read(helper/'request.json')
    require(virtual['virtual'] is True and physical['virtual'] is False and
        virtual['run_id']==physical['run_id'] and (helper/'key').read_bytes()==(build/'key').read_bytes() and
        virtual['modules']==physical['modules'] and
        virtual['measured']['init_sha256']==physical['measured']['init_sha256'] and
        virtual['measured']['shell_sha256']==physical['measured']['shell_sha256'],
        'VM derivative does not join physical construction')
    payloads=build_api.payloads(helper)
    payloads={('usr/sbin/'+name if name in ('fyg8-prepare','integrated-measure','integrated-init') else name):row
        for name,row in payloads.items()}
    entries=list(build_api.fyg8.debian_entries(build/'initramfs-a.cpio.gz'))
    for i,entry in enumerate(entries):
        if entry.name in payloads:entries[i]=replace(entry,data=verify(payloads[entry.name],maximum=8*1024**2).read_bytes())
        elif entry.name=='scripts/fyg8-dev':
            text=entry.data.decode();require(text==build_api.dev_script(),'VM owner script differs')
            # The physical failure function parks forever. Only this harness
            # prints retained RAM diagnostics and powers off its private VM.
            text=text.replace('    while :; do /bin/busybox sleep 3600; done',
                '    printf "INTEGRATED_VM_EARLY_STOP\\n"\n'
                '    cat /run/initramfs/fyg8-events 2>/dev/null || :\n'
                '    poweroff -f\n    while :; do sleep 1; done')
            if case=='ufs-failure':text=text.replace('exec /sbin/integrated-init',
                'printf "insert-error\\n" >/lab/fault\nexec /sbin/integrated-init')
            if case=='fd-leak':text=text.replace('exec /sbin/integrated-init','exec 8</dev/null\nexec /sbin/integrated-init')
            if case=='parent-byte':text=text.replace('exec /sbin/integrated-init',
                'chmod 600 /run/initramfs/initial-parent\nprintf "X" >/run/initramfs/initial-parent\n'
                'chmod 400 /run/initramfs/initial-parent\nexec /sbin/integrated-init')
            entries[i]=replace(entry,data=text.encode())
        elif case=='module-byte' and entry.name=='lab/modules/sec_log_buf.ko':
            entries[i]=replace(entry,data=bytes([entry.data[0]^1])+entry.data[1:])
    model=entries[0];inode=max(e.inode for e in entries)+1
    for name,body in (('lab/fault',b'none\n'),('lab/integrated-fault',
                     b'provider-missing\n' if case=='provider-missing' else b'none\n')):
        entries.append(replace(model,name=name,encoded_name=name,inode=inode,mode=stat.S_IFREG|0o600,nlink=1,data=body));inode+=1
    vendor=build_api.fyg8.memory.vendor
    source=build_api.fyg8.memory.base.stable(h0.ROOT/vendor.DEFAULT_VENDOR_RAMDISK,
        dict(size=vendor.EXPECTED_VENDOR_RAMDISK_SIZE,sha256=vendor.EXPECTED_VENDOR_RAMDISK_SHA256))
    overlay=build_api.fyg8.boot.decompress_lz4_stream_python(source,maximum=128*1024**2)
    (out/'initramfs.cpio.gz').write_bytes(gzip.compress(overlay,mtime=0)+gzip.compress(vm.newc(entries),mtime=0))
    native=out/'native.ext4'
    h0.run(['cp','--reflink=auto','--sparse=always',vm.previous.BASE/'complete.ext4',native],out/'copy-root.log')
    lifecycle.prepare_root_fixture(native,out,'post-p410')
    if case=='dirty':vm.fixture.debug(native,out,'dirty','ssv state 0')
    if case=='mismatch':vm.fixture.debug(native,out,'mismatch','set_inode_field /etc/lab-rootfs-id mode 0100600')
    binding=read(verify(vm.fixture.profile.filesystem.BINDING));vm.fixture.make_disk(native,out/'disk.img',binding)
    publish(out/'setup.json',dict(case=case,build=pin(build/'build.json'),helper=pin(helper/'request.json'),
        initramfs=pin(out/'initramfs.cpio.gz',maximum=32*1024**2),source=pin(Path(__file__)),device_actions=0))
    return virtual


def run(out,build,helper,case):
    selected=prepare(out,build,helper,case);handoff=read(verify(selected['handoff']))
    before=vm.fixture.fixture_tools.sparse_digest(out/'disk.img');outside=lifecycle.outside_native(out/'disk.img')
    publish(out/'disk-before.json',dict(digest=before,outside_native=outside,device_actions=0))
    key=(build/'key').read_bytes();run_id=bytes.fromhex(selected['run_id'])
    state=protocol.Records(key,run_id,NONCE,selected['measured'],[m['runtime_name'] for m in selected['modules']],handoff)
    _,_,plan=lifecycle.profile.prior_inputs()
    access_inputs=lifecycle.access.inputs(selected['run_id'])
    plan=dict(plan,**{name:access_inputs[name] for name in ('ssh','client_key','known_hosts')},
        root_run_id=lifecycle.profile.prior_inputs()[0]['run_id'],
        candidate=dict(namespace=selected['namespace'],version=selected['version'],run_id=selected['run_id']))
    scratch=Path(tempfile.mkdtemp(prefix='s22-integrated-vm-'));endpoint=scratch/'wire.sock'
    with socket.socket() as reserve:reserve.bind(('127.0.0.1',0));port=reserve.getsockname()[1]
    link=plan['link'];network=ipaddress.ip_interface(link['device_address']).network
    if network.prefixlen>24:network=network.supernet(new_prefix=24)
    net=f'user,id=net,restrict=on,net={network},host={link["host_address"].split("/")[0]},'
    net+=f'dhcpstart={link["ssh_address"]},dns={network.network_address+254},hostfwd=tcp:127.0.0.1:{port}-{link["ssh_address"]}:22'
    command=[vm.fixture.QEMU/'usr/bin/qemu-system-aarch64','-machine','virt','-cpu','cortex-a76','-smp','2','-m','1024',
        '-netdev',net,'-device','virtio-net-device,netdev=net,mac='+link['device_mac'],
        '-display','none','-monitor','none','-serial',f'file:{out}/serial.log','-no-reboot',
        '-chardev',f'socket,id=di,path={endpoint},server=on,wait=off','-device','virtio-serial-device',
        '-device','virtconsole,chardev=di','-kernel',h0.regular(vm.KERNEL),'-initrd',out/'initramfs.cpio.gz',
        '-append','console=ttyAMA0 rdinit=/init panic=1','-drive',f'if=none,id=root,file={out}/disk.img,format=raw',
        '-device','virtio-blk-device,drive=root,logical_block_size=4096,physical_block_size=4096']
    publish(out/'command.json',[str(v) for v in command]);rx=bytearray();tx=bytearray();pending=bytearray()
    process=None;ssh_health=shutdown=None;sent_initial=False;sent=set();deadline=time.monotonic()+360
    try:
        with (out/'qemu.log').open('xb') as log,(out/'rx.bin').open('xb') as receive,(out/'tx.bin').open('xb') as transmit:
            process=subprocess.Popen([str(x) for x in command],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,
                env=dict(os.environ,LD_LIBRARY_PATH=str(vm.fixture.QEMU/'usr/lib/x86_64-linux-gnu')))
            while not endpoint.exists() and process.poll() is None and time.monotonic()<deadline:time.sleep(.02)
            require(endpoint.exists(),'VM did not create serial substitute')
            with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as stream:
                stream.connect(str(endpoint));stream.setblocking(False)
                def send(data):
                    transmit.write(data);transmit.flush();os.fsync(transmit.fileno());tx.extend(data)
                    stream.sendall(data)
                while time.monotonic()<deadline:
                    serial=(out/'serial.log').read_bytes() if (out/'serial.log').exists() else b''
                    if not sent_initial and b'INTEGRATED_VM_WIRE_READY' in serial:
                        data=protocol.request(key,run_id,NONCE)
                        if case=='bad-auth':
                            decoded=protocol.frames.decode_frame(data)
                            payload=decoded.payload[:-1]+bytes([decoded.payload[-1]^1])
                            data=protocol.frames.encode_frame(decoded.frame_type,decoded.sequence,payload)
                        send(data);sent_initial=True
                    readable,_,_=select.select([stream],[],[],.05)
                    if readable:
                        try:part=stream.recv(4096)
                        except ConnectionResetError:break
                        if not part:break
                        receive.write(part);receive.flush();os.fsync(receive.fileno());rx.extend(part);pending.extend(part)
                        require(len(rx)<=protocol.MAXIMUM,'integrated VM transcript overflow')
                        while len(pending)>=16:
                            size=int.from_bytes(pending[6:8],'little');require(size<=1023,'integrated VM oversized frame')
                            if len(pending)<16+size:break
                            state.accept(protocol.frames.decode_frame(bytes(pending[:16+size])));del pending[:16+size]
                            current=state.handoff
                            if current:
                                for kind,sequence,ready in ((protocol.handoff.CONTINUE,6,current.proof),
                                    (protocol.handoff.START,8,current.init_proof),(protocol.handoff.RELEASE,9,current.runtime_proof)):
                                    if ready and kind not in sent:
                                        send(protocol.handoff.encode(key,run_id,NONCE,kind,sequence));sent.add(kind)
                    if state.handoff and (state.handoff.released or state.handoff.stop):break
                    if process.poll() is not None:break
                require(time.monotonic()<deadline,'integrated VM deadline expired')
                if case=='normal':
                    require(state.handoff and state.handoff.released,'integrated VM services/release unproved')
                    for ordinal in range(1,61):
                        handle=raw.acquire_command(lifecycle.ssh_command(plan,port,'health'),out,f'health-{ordinal:03d}',
                            timeout=5,stdout_maximum=65536,stderr_maximum=16384)
                        if handle.returncode==0:
                            ssh_health=lifecycle.access.health_projection(handle,plan,boot_sha256=state.handoff.boot.hex());break
                        require(time.monotonic()<deadline and process.poll() is None,'integrated VM SSH deadline')
                        time.sleep(.5)
                    require(ssh_health is not None,'integrated pinned SSH health missing')
                    handle=raw.acquire_command(lifecycle.ssh_command(plan,port,'shutdown'),out,'shutdown',timeout=20,
                        stdout_maximum=65536,stderr_maximum=16384)
                    shutdown=lifecycle.access.shutdown_projection(handle,plan['link']['ssh_address'])
                process.wait(timeout=max(1,deadline-time.monotonic()))
        require(process.returncode==0 and not pending and b'reboot: Power down' in (out/'serial.log').read_bytes(),
            'VM terminal, framing or explicit poweroff differs')
        after=vm.fixture.fixture_tools.sparse_digest(out/'disk.img')
        require(lifecycle.outside_native(out/'disk.img')==outside,'integrated VM wrote outside native_data')
        filesystem=durable=None
        if case=='normal':
            proof=protocol.replay(bytes(rx),bytes(tx),key=key,run=run_id,expected=selected['measured'],
                module_names=[m['runtime_name'] for m in selected['modules']],selection=handoff)
            filesystem=lifecycle.inspect_after(out,positive=True,negative=False,booted=True,initial_count=1)
            durable=lifecycle.durable_after(out,handoff,key,state.handoff,local_only=False)
            require(ssh_health['boot_id_sha256']==proof['kernel_boot_proof'] and
                state.handoff.runtime_proof['elapsed_ms']>=120000,'service/SSH crossed a boot or shortened sampling')
        else:
            require(before==after and not (state.handoff and state.handoff.proof),
                'pre-admission rejection mutated storage or proved root transition')
            if case in ('module-byte','provider-missing','parent-byte','bad-auth'):require(not rx,'early negative emitted proof')
            elif case=='ufs-failure':require(state.initial.complete and not state.ufs_proof,'UFS failure advanced')
            else:require(state.handoff and state.handoff.stop,'admission negative lacks authenticated stop')
            proof=state.projection()
        value=dict(status='PASS',case=case,proof=proof,ssh_health=ssh_health,shutdown=shutdown,
            filesystem=filesystem,durable=durable,build=pin(build/'build.json'),virtual_helper=pin(helper/'request.json'),
            rx=dict(path=str(out/'rx.bin'),size=len(rx),sha256=protocol.hashlib.sha256(rx).hexdigest()),
            tx=dict(path=str(out/'tx.bin'),size=len(tx),sha256=protocol.hashlib.sha256(tx).hexdigest()),
            serial=pin(out/'serial.log',maximum=4*1024**2),
            disk_before=before,disk_after=after,outside_native_unchanged=True,device_actions=0,
            scope='REAL_DEBIAN_INITRAMFS_TO_SYSVINIT_SSH_WITH_SAMSUNG_HARDWARE_SUBSTITUTIONS')
        publish(out/'result.json',value);print(case,'PASS',flush=True);return value
    finally:
        if process is not None and process.poll() is None:process.kill();process.wait()
        shutil.rmtree(scratch)


def suite(out,build,cases=CASES):
    out=h0.private(out,fresh=True);build=h0.private(build);physical=read(build/'build.json')
    sources=build_api.snapshot(out)
    helper=out/'helper'
    build_api.prepare(helper,Path(physical['inputs']),Path(physical['packages']),
        run=physical['run_id'],key=(build/'key').read_bytes(),virt=True)
    values=[run(out/case,build,helper,case) for case in cases]
    for row in sources:require(h0.sha(h0.ROOT/row['path'])==row['sha256'],'integrated VM source changed')
    publish(out/'result.json',dict(status='PASS',cases=values,build_sha256=h0.sha(build/'build.json'),
        source_inputs=sources,device_actions=0))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True);parser.add_argument('--build',type=Path,required=True)
    parser.add_argument('--case',choices=CASES);args=parser.parse_args()
    suite(args.output,args.build,(args.case,) if args.case else CASES)

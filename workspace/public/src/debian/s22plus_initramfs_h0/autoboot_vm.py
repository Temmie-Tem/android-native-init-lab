#!/usr/bin/env python3
"""ARM64 automatic startup with real Debian and isolated regular-file disks."""
import argparse
from dataclasses import replace
import gzip
import ipaddress
import os
from pathlib import Path
import socket
import stat
import subprocess
import time

import autoboot as build_api
import fyg8_vm as vm
import file_log_vm
import h0
import s22plus_debian_handoff_vm_h0 as lifecycle
import s22plus_debian_autoboot_protocol_v1 as protocol
import device_action_raw_capture_v1 as raw
from s22plus_native_records_v3 import pin,publish,read,require,verify

CASES=build_api.profile.CASES


def prepare(out,build,helper,case):
    require(case in CASES,'unknown automatic VM case');out.mkdir(mode=0o700)
    physical=read(build/'build.json');selected=read(helper/'request.json')
    require(selected['virtual'] is True and physical['virtual'] is False and selected['run_id']==physical['run_id'] and
        selected['modules']==physical['modules'] and
        selected['measured']['init_sha256']==physical['measured']['init_sha256'] and
        selected['measured']['shell_sha256']==physical['measured']['shell_sha256'] and
        verify(selected['key']).read_bytes()==verify(physical['key']).read_bytes(),'automatic VM derivative differs')
    payloads=build_api.payloads(selected);entries=list(build_api.fyg8.debian_entries(build/'initramfs-a.cpio.gz'))
    for i,item in enumerate(entries):
        if item.name in payloads:entries[i]=replace(item,data=verify(payloads[item.name],maximum=8*1024**2).read_bytes())
        elif item.name=='scripts/fyg8-dev':
            text=item.data.decode();require(text==build_api.dev_script(),'automatic shell script differs')
            text=text.replace('    while :; do /bin/busybox sleep 3600; done',
                '    printf "AUTO_VM_EARLY_STOP\\n"\n'
                '    test ! -f /run/initramfs/file-admission || cat /run/initramfs/file-admission\n'
                '    poweroff -f\n    while :; do sleep 1; done')
            if case=='changed-receipt':text=text.replace('exec /sbin/autoboot-init',
                'chmod 600 /run/initramfs/autoboot-early\nprintf X >|/run/initramfs/autoboot-early\n'
                'test "$(wc -c </run/initramfs/autoboot-early)" = 1 || poweroff -f\n'
                'printf AUTO_VM_RECEIPT_MUTATED >|/dev/kmsg\n'
                'chmod 400 /run/initramfs/autoboot-early\nexec /sbin/autoboot-init')
            if case=='fd-leak':text=text.replace('exec /sbin/autoboot-init','exec 8</dev/null\nexec /sbin/autoboot-init')
            entries[i]=replace(item,data=text.encode())
    model=entries[0];inode=max(e.inode for e in entries)+1
    for name in ('lab/fault','lab/integrated-fault','lab/client-fault'):
        entries.append(replace(model,name=name,encoded_name=name,inode=inode,mode=stat.S_IFREG|0o400,nlink=1,data=b'module-error\n' if name=='lab/client-fault' and case=='module-error' else b'none\n'));inode+=1
    vendor=build_api.fyg8.memory.vendor
    source=build_api.fyg8.memory.base.stable(h0.ROOT/vendor.DEFAULT_VENDOR_RAMDISK,
        dict(size=vendor.EXPECTED_VENDOR_RAMDISK_SIZE,sha256=vendor.EXPECTED_VENDOR_RAMDISK_SHA256))
    overlay=build_api.fyg8.boot.decompress_lz4_stream_python(source,maximum=128*1024**2)
    (out/'initramfs.cpio.gz').write_bytes(gzip.compress(overlay,mtime=0)+gzip.compress(vm.newc(entries),mtime=0))
    native=out/'native.ext4'
    h0.run(['cp','--reflink=auto','--sparse=always',vm.previous.BASE/'complete.ext4',native],out/'copy-root.log')
    lifecycle.prepare_root_fixture(native,out,'post-p410')
    history=build_api.profile.history();body=verify(history['source']).read_bytes()
    if case=='changed-history':body=body[:-1]+bytes([body[-1]^1])
    (out/'history.bin').write_bytes(body)
    vm.fixture.debug(native,out,'history-write',f'write {out}/history.bin /{history["path"]}')
    vm.fixture.debug(native,out,'history-mode',f'set_inode_field /{history["path"]} mode 0100600')
    if case=='dirty':vm.fixture.debug(native,out,'dirty','ssv state 0')
    if case in ('foreign-file','existing-early','existing-runtime'):
        path='/etc/unexpected-autoboot' if case=='foreign-file' else '/var/lib/lab/'+(
            's22-early-' if case=='existing-early' else 's22-evidence-')+selected['run_id']
        (out/'sentinel').write_bytes(b'DO_NOT_OVERWRITE\n')
        vm.fixture.debug(native,out,'sentinel',f'write {out}/sentinel {path}')
        vm.fixture.debug(native,out,'sentinel-mode',f'set_inode_field {path} mode 0100600')
    binding=read(verify(vm.fixture.profile.filesystem.BINDING));vm.fixture.make_disk(native,out/'disk.img',binding)
    publish(out/'setup.json',dict(case=case,build=pin(build/'build.json'),helper=pin(helper/'request.json'),
        initramfs=pin(out/'initramfs.cpio.gz',maximum=32*1024**2),source=pin(Path(__file__)),device_actions=0))
    return selected


def ssh_command(plan,port,command):
    require(command in ('health','evidence','shutdown'),'unselected automatic VM SSH command')
    args=lifecycle.ssh_command(plan,port,'health');args[-1]=command;return args


def run(out,build,helper,case):
    selected=prepare(out,build,helper,case)
    before=vm.fixture.fixture_tools.sparse_digest(out/'disk.img');outside=lifecycle.outside_native(out/'disk.img')
    publish(out/'disk-before.json',dict(digest=before,outside_native=outside,device_actions=0))
    key=verify(selected['key']).read_bytes();access=lifecycle.access.inputs(selected['run_id'])
    plan=dict(access,candidate=dict(namespace=selected['namespace'],version=selected['version'],run_id=selected['run_id']))
    with socket.socket() as reserve:reserve.bind(('127.0.0.1',0));port=reserve.getsockname()[1]
    link=plan['link'];network=ipaddress.ip_interface(link['device_address']).network
    if network.prefixlen>24:network=network.supernet(new_prefix=24)
    net=f'user,id=net,restrict=on,net={network},host={link["host_address"].split("/")[0]},'
    net+=f'dhcpstart={link["ssh_address"]},dns={network.network_address+254},hostfwd=tcp:127.0.0.1:{port}-{link["ssh_address"]}:22'
    command=[vm.fixture.QEMU/'usr/bin/qemu-system-aarch64','-machine','virt','-cpu','cortex-a76','-smp','2','-m','1024',
        '-netdev',net,'-device','virtio-net-device,netdev=net,mac='+link['device_mac'],
        '-display','none','-monitor','none','-serial',f'file:{out}/serial.log','-no-reboot',
        '-kernel',h0.regular(vm.KERNEL),'-initrd',out/'initramfs.cpio.gz','-append',vm.KERNEL_COMMAND_LINE,
        '-drive',f'if=none,id=root,file={out}/disk.img,format=raw',
        '-device','virtio-blk-device,drive=root,logical_block_size=4096,physical_block_size=4096']
    if case=='network-absent':
        begin=command.index('-netdev');command[begin:begin+4]=['-nic','none']
    publish(out/'command.json',list(map(str,command)));process=None;proof=health=shutdown=None
    local=None;forced_stop=False;proof_capture=None;runtime_absent=False
    deadline=time.monotonic()+360
    try:
        with (out/'qemu.log').open('xb') as log:
            process=subprocess.Popen(list(map(str,command)),stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,
                env=dict(os.environ,LD_LIBRARY_PATH=str(vm.fixture.QEMU/'usr/lib/x86_64-linux-gnu')))
            if case=='normal':
                for ordinal in range(1,121):
                    require(time.monotonic()<deadline and process.poll() is None,'automatic VM stopped before service proof')
                    handle=raw.acquire_command(ssh_command(plan,port,'evidence'),out,f'evidence-{ordinal:03d}',timeout=5,
                        stdout_maximum=protocol.MAXIMUM,stderr_maximum=16384)
                    if handle.returncode==0:
                        raw.require_success(handle);require(not raw.read_stderr(handle,maximum=16384),'SSH evidence has diagnostics')
                        proof_capture=pin(handle.receipt_path)
                        proof,parts=protocol.envelope(raw.read_stdout(handle,maximum=protocol.MAXIMUM),key=key,selected=selected)
                        for name,data in zip(('early','runtime','transition'),parts):(out/(name+'.bin')).write_bytes(data)
                        break
                    time.sleep(2)
                require(proof is not None,'automatic VM service evidence missing')
                handle=raw.acquire_command(ssh_command(plan,port,'health'),out,'health',timeout=10,
                    stdout_maximum=65536,stderr_maximum=16384)
                health=lifecycle.access.health_projection(handle,plan,boot_sha256=proof['kernel_boot_identity_sha256'],autoboot=True)
                handle=raw.acquire_command(ssh_command(plan,port,'shutdown'),out,'shutdown',timeout=20,
                    stdout_maximum=65536,stderr_maximum=16384)
                shutdown=lifecycle.access.shutdown_projection(handle,plan['link']['ssh_address'])
            if case=='network-absent':
                # Test-only external stop after the full autonomous service
                # window. This is not a target watchdog or shutdown proof.
                until=time.monotonic()+165
                while process.poll() is None and time.monotonic()<until:time.sleep(1)
                require(process.poll() is None,'network-absent VM unexpectedly exited')
                process.kill();process.wait();forced_stop=True
            else:process.wait(timeout=max(1,deadline-time.monotonic()))
        require(forced_stop or process.returncode==0 and b'reboot: Power down' in (out/'serial.log').read_bytes(),'automatic VM did not power off')
        if case=='changed-receipt':require(b'AUTO_VM_RECEIPT_MUTATED' in (out/'serial.log').read_bytes(),'receipt mutation was not exercised')
        after=vm.fixture.fixture_tools.sparse_digest(out/'disk.img')
        require(lifecycle.outside_native(out/'disk.img')==outside,'automatic VM wrote outside native_data')
        filesystem=None
        if case=='normal':filesystem=lifecycle.inspect_after(out,positive=True,negative=False,booted=True,initial_count=1)
        elif case=='network-absent':
            native=file_log_vm.extract_native(out)
            bodies=[]
            for kind,prefix in (('early','s22-early-'),('runtime','s22-evidence-')):
                path=out/(kind+'.bin')
                vm.fixture.debug(native,out,kind+'-dump',f'dump /var/lib/lab/{prefix}{selected["run_id"]} {path}')
                bodies.append(path.read_bytes())
            local=protocol.local_records(*bodies,key=key,selected=selected,root_device=dict(major=259,minor=25))
        elif case not in ('changed-receipt','fd-leak','module-error'):
            require(before==after,'pre-admission rejection changed the disk')
        else:
            # First phase may have completed, but no installed-service record
            # may have been created after a rejected receipt/descriptor.
            native=file_log_vm.extract_native(out);record=out/'unexpected-runtime.bin'
            vm.fixture.debug(native,out,'runtime-absence',f'dump /var/lib/lab/s22-evidence-{selected["run_id"]} {record}')
            require(not record.exists(),'failed automatic entry ran installed services');runtime_absent=True
        value=dict(status='PASS',case=case,proof=proof,ssh_health=health,shutdown=shutdown,filesystem=filesystem,
            build=pin(build/'build.json'),virtual_helper=pin(helper/'request.json'),serial=pin(out/'serial.log',maximum=4*1024**2),
            disk_before=before,disk_after=after,outside_native_unchanged=True,device_actions=0,
            host_start_requests=0,local=local,forced_host_stop=forced_stop,proof_capture=proof_capture,
            runtime_absent=runtime_absent,setup=pin(out/'setup.json'),
            local_files={name:pin(out/(name+'.bin')) for name in ('early','runtime')} if local is not None else None,scope='REAL_DEBIAN_AUTOBOOT_WITH_SAMSUNG_HARDWARE_SUBSTITUTIONS')
        publish(out/'result.json',value);print(case,'PASS',flush=True);return value
    finally:
        if process is not None and process.poll() is None:process.kill();process.wait()


def suite(out,build):
    from concurrent.futures import ThreadPoolExecutor
    out=h0.private(out,fresh=True);build=h0.private(build);built=read(build/'build.json')
    prepared=build_api.prepare(out/'virtual',Path(built['inputs']),Path(built['packages']),
        run=built['run_id'],key=verify(built['key']).read_bytes(),virt=True)
    require(prepared['source_inputs']==built['source_inputs'],'suite sources differ from the physical build')
    with ThreadPoolExecutor(max_workers=2) as pool:
        rows=list(pool.map(lambda case:run(out/case,build,out/'virtual',case),CASES))
    value=dict(status='PASS',cases=rows,build_sha256=h0.sha(build/'build.json'),
        source_inputs=built['source_inputs'],device_actions=0)
    publish(out/'result.json',value);return value


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('output','build','helper'):parser.add_argument('--'+name,type=Path,required=name!='helper')
    parser.add_argument('--case',choices=CASES);args=parser.parse_args()
    if args.case:
        require(args.helper is not None,'single case requires an exact prepared helper')
        run(h0.private(args.output),h0.private(args.build),h0.private(args.helper),args.case)
    else:suite(args.output,args.build)

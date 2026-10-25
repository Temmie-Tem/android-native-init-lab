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
import s22plus_debian_autoboot_transition_v1 as transition_protocol
import device_action_raw_capture_v1 as raw
from s22plus_native_records_v3 import pin,publish,read,require,verify

CASES=tuple(dict.fromkeys(build_api.profile.cases(True,True,True,True)+build_api.profile.SINGLECPU_CASES+build_api.profile.P447_HISTORY_CASES+build_api.profile.P451_HISTORY_CASES+build_api.profile.SCRIPT_FAULTS+build_api.profile.minimal_spec.HISTORY_CASES+build_api.profile.minimal_spec.FAULTS))


def prepare(out,build,helper,case):
    require(case in CASES,'unknown automatic VM case');out.mkdir(mode=0o700)
    physical=read(build/'build.json');selected=read(helper/'request.json')
    transition,rcs,watchdog=build_api.profile.variants(selected)
    phase=build_api.profile.phase_selected(selected)
    single_cpu=build_api.profile.singlecpu_selected(selected)
    post_p447=build_api.profile.post_p447_selected(selected)
    script_channel=build_api.profile.script_channel_selected(selected)
    minimal=build_api.profile.minimal_selected(selected)
    reboot=build_api.profile.reboot_selected(selected)
    cron=build_api.profile.cron_selected(selected)
    require(case in build_api.profile.cases(transition,rcs,watchdog,phase,single_cpu,post_p447,script_channel,minimal,reboot,cron),'case does not belong to selected variant')
    require(selected['virtual'] is True and physical['virtual'] is False and selected['run_id']==physical['run_id'] and
        build_api.profile.variants(physical)==(transition,rcs,watchdog) and
        build_api.profile.phase_selected(physical)==phase and
        build_api.profile.singlecpu_selected(physical)==single_cpu and
        build_api.profile.post_p447_selected(physical)==post_p447 and
        build_api.profile.script_channel_selected(physical)==script_channel and
        build_api.profile.minimal_selected(physical)==minimal and
        physical.get('cron')==selected.get('cron') and
        physical.get('reboot')==selected.get('reboot') and
        physical.get('reboot_baseline')==selected.get('reboot_baseline') and
        physical.get('idle_policy')==selected.get('idle_policy') and
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
            if minimal:
                text=text.replace('exec /sbin/autoboot-init',
                    'test "$(ls -A /dev)" = "$(printf \'console\\nkmsg\\nnull\\n\')" || fyg8_stop\n'
                    'printf AUTO_VM_MINIMAL_SPARSE_DEV >|/dev/kmsg\nexec /sbin/autoboot-init')
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
    for index,history in enumerate(build_api.profile.histories(transition,rcs,watchdog,phase,single_cpu,post_p447,script_channel,minimal,reboot,cron)):
        if case=='missing-second-history' and index==1:continue
        if case=='missing-runtime-history' and index==2:continue
        selected_pair={3:'p437-early',4:'p437-runtime',5:'p441-early',6:'p441-runtime',7:'p445-early',8:'p448-early',9:'p448-runtime',10:'p452-early',11:'p452-runtime',12:'p456-early',13:'p456-runtime'}.get(index)
        if selected_pair and case=='missing-'+selected_pair:continue
        body=verify(history['source']).read_bytes()
        if (case=='changed-history' or case=='changed-runtime-history' and index==2 or
                selected_pair and case=='changed-'+selected_pair):body=body[:-1]+bytes([body[-1]^1])
        file=out/f'history-{index}.bin';file.write_bytes(body)
        vm.fixture.debug(native,out,f'history-write-{index}',f'write {file} /{history["path"]}')
        vm.fixture.debug(native,out,f'history-mode-{index}',f'set_inode_field /{history["path"]} mode 0100600')
        if (case=='linked-second-history' and index==1 or case=='linked-runtime-history' and index==2 or
                selected_pair and case=='linked-'+selected_pair):
            vm.fixture.debug(native,out,'history-links',f'set_inode_field /{history["path"]} links_count 2')
        if case=='mode-runtime-history' and index==2 or selected_pair and case=='mode-'+selected_pair:
            vm.fixture.debug(native,out,'history-bad-mode',f'set_inode_field /{history["path"]} mode 0100644')
    if case in ('extra-runtime-history','unexpected-p445-runtime'):
        (out/'extra-runtime').write_bytes(b'UNQUALIFIED_RUNTIME_FILE\n')
        suffix='f'*32 if rcs else build_api.profile.additional_history()['path'].rsplit('-',1)[1]
        if case=='unexpected-p445-runtime':suffix=build_api.profile.p445_history()['path'].rsplit('-',1)[1]
        path='/var/lib/lab/s22-evidence-'+suffix
        require(path.lstrip('/') not in {row['path'] for row in build_api.profile.histories(True,rcs,watchdog,phase,single_cpu,post_p447,script_channel,minimal)} and
            suffix!=selected['run_id'],'unexpected-history fixture overlaps selected files')
        vm.fixture.debug(native,out,'extra-runtime',f'write {out}/extra-runtime {path}')
        vm.fixture.debug(native,out,'extra-runtime-mode',f'set_inode_field {path} mode 0100600')
    if case=='boot-count-leading-zero':
        (out/'bad-count').write_bytes(b'01\n')
        vm.fixture.debug(native,out,'count-remove','rm /var/lib/lab/boot-count')
        vm.fixture.debug(native,out,'count-write',f'write {out}/bad-count /var/lib/lab/boot-count')
        vm.fixture.debug(native,out,'count-mode','set_inode_field /var/lib/lab/boot-count mode 0100644')
    if case=='dirty':vm.fixture.debug(native,out,'dirty','ssv state 0')
    if case in ('foreign-file','existing-early','existing-runtime'):
        path='/etc/unexpected-autoboot' if case=='foreign-file' else '/var/lib/lab/'+(
            's22-early-' if case=='existing-early' else 's22-evidence-')+selected['run_id']+('-b1' if reboot else '')
        (out/'sentinel').write_bytes(b'DO_NOT_OVERWRITE\n')
        vm.fixture.debug(native,out,'sentinel',f'write {out}/sentinel {path}')
        vm.fixture.debug(native,out,'sentinel-mode',f'set_inode_field {path} mode 0100600')
    if reboot:vm.fixture.debug(native,out,'sealed-count',f'ssv mnt_count {selected["reboot"]["initial_mount_count"]}')
    binding=read(verify(vm.fixture.profile.filesystem.BINDING));vm.fixture.make_disk(native,out/'disk.img',binding)
    publish(out/'setup.json',dict(case=case,build=pin(build/'build.json'),helper=pin(helper/'request.json'),
        initramfs=pin(out/'initramfs.cpio.gz',maximum=32*1024**2),source=pin(Path(__file__)),device_actions=0))
    return selected


def ssh_command(plan,port,command):
    require(command in ('health','evidence','shutdown','reboot'),'unselected automatic VM SSH command')
    args=lifecycle.ssh_command(plan,port,'health');args[-1]=command;return args


def kernel_command_line(selected):
    # The retained VM command line contains "--"; kernel parameters must
    # precede it or they become additional, rejected PID1 arguments.
    return ('maxcpus=1 ' if build_api.profile.singlecpu_selected(selected) else '')+(
        'cpuidle.off=1 ' if selected.get('idle_policy')=='cpuidle-off' else '')+vm.KERNEL_COMMAND_LINE


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
    single_cpu=build_api.profile.singlecpu_selected(selected)
    post_p447=build_api.profile.post_p447_selected(selected)
    script_channel=build_api.profile.script_channel_selected(selected)
    minimal=build_api.profile.minimal_selected(selected)
    command=[vm.fixture.QEMU/'usr/bin/qemu-system-aarch64','-machine','virt','-cpu','cortex-a76','-smp','8' if single_cpu else '2','-m','1024',
        '-netdev',net,'-device','virtio-net-device,netdev=net,mac='+link['device_mac'],
        '-display','none','-monitor','none','-serial',f'file:{out}/serial.log','-no-reboot',
        '-kernel',h0.regular(vm.KERNEL),'-initrd',out/'initramfs.cpio.gz','-append',
        kernel_command_line(selected).removeprefix('maxcpus=1 ') if case=='singlecpu-unlimited' else kernel_command_line(selected),
        '-drive',f'if=none,id=root,file={out}/disk.img,format=raw',
        '-device','virtio-blk-device,drive=root,logical_block_size=4096,physical_block_size=4096']
    if case=='network-absent':
        begin=command.index('-netdev');command[begin:begin+4]=['-nic','none']
    publish(out/'command.json',list(map(str,command)));process=None;proof=health=shutdown=None
    local=None;forced_stop=False;proof_capture=None;runtime_absent=False;ssh_pair=None
    deadline=time.monotonic()+360
    try:
        with (out/'qemu.log').open('xb') as log:
            process=subprocess.Popen(list(map(str,command)),stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,
                env=dict(os.environ,LD_LIBRARY_PATH=str(vm.fixture.QEMU/'usr/lib/x86_64-linux-gnu')))
            if case in ('normal','trace-logger-loss')+build_api.profile.SCRIPT_FAULTS:
                if single_cpu:
                    first_health=None
                    for ordinal in range(1,30):
                        require(time.monotonic()<deadline and process.poll() is None,'VM stopped before initial SSH')
                        handle=raw.acquire_command(ssh_command(plan,port,'health'),out,f'initial-health-{ordinal:03d}',
                            timeout=5,stdout_maximum=65536,stderr_maximum=16384)
                        if handle.returncode==0:
                            from s22plus_debian_autoboot_access_v1 import singlecpu_health_sample
                            singlecpu_health_sample(handle,plan)
                            first_health=handle;first_finished=time.monotonic();break
                        require(not handle.output_exceeded and handle.producer_error_type is None,'initial VM SSH producer failed')
                        time.sleep(3)
                    require(first_health is not None,'initial VM SSH health missing')
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
                if single_cpu:
                    while time.monotonic()-first_finished<120.1:
                        require(time.monotonic()<deadline and process.poll() is None,'VM stopped during SSH interval')
                        time.sleep(0.1)
                handle=raw.acquire_command(ssh_command(plan,port,'health'),out,'health',timeout=10,
                    stdout_maximum=65536,stderr_maximum=16384)
                health=lifecycle.access.health_projection(handle,plan,boot_sha256=proof['kernel_boot_identity_sha256'],autoboot=True)
                if single_cpu:
                    from s22plus_debian_autoboot_access_v1 import singlecpu_health_pair
                    ssh_pair=singlecpu_health_pair(first_health,handle,plan,proof['kernel_boot_identity_sha256'])
                handle=raw.acquire_command(ssh_command(plan,port,'shutdown'),out,'shutdown',timeout=20,
                    stdout_maximum=65536,stderr_maximum=16384)
                shutdown=lifecycle.access.shutdown_projection(handle,plan['link']['ssh_address'])
            if case in ('network-absent','trace-pending','rcs-pending-record','rcs-pending-child'):
                # Test-only external stop after the full autonomous service
                # window. This is not a target watchdog or shutdown proof.
                until=time.monotonic()+(165 if case=='network-absent' else 25)
                while process.poll() is None and time.monotonic()<until:time.sleep(1)
                require(process.poll() is None,'network-absent VM unexpectedly exited')
                process.kill();process.wait();forced_stop=True
            else:process.wait(timeout=max(1,deadline-time.monotonic()))
        require(forced_stop or process.returncode==0 and b'reboot: Power down' in (out/'serial.log').read_bytes(),'automatic VM did not power off')
        if case=='changed-receipt':require(b'AUTO_VM_RECEIPT_MUTATED' in (out/'serial.log').read_bytes(),'receipt mutation was not exercised')
        if minimal and case in ('normal',*build_api.profile.SCRIPT_FAULTS,*build_api.profile.minimal_spec.FAULTS):
            require(b'AUTO_VM_MINIMAL_SPARSE_DEV' in (out/'serial.log').read_bytes(),
                'minimal boot did not start from the physical sparse device namespace')
        after=vm.fixture.fixture_tools.sparse_digest(out/'disk.img')
        require(lifecycle.outside_native(out/'disk.img')==outside,'automatic VM wrote outside native_data')
        filesystem=None
        if case in ('normal','trace-logger-loss')+build_api.profile.SCRIPT_FAULTS:filesystem=lifecycle.inspect_after(out,positive=True,negative=False,booted=True,initial_count=1)
        elif case=='network-absent':
            native=file_log_vm.extract_native(out)
            bodies=[]
            for kind,prefix in (('early','s22-early-'),('runtime','s22-evidence-')):
                path=out/(kind+'.bin')
                vm.fixture.debug(native,out,kind+'-dump',f'dump /var/lib/lab/{prefix}{selected["run_id"]} {path}')
                bodies.append(path.read_bytes())
            local=protocol.local_records(*bodies,key=key,selected=selected,root_device=dict(major=259,minor=25))
        elif case in build_api.profile.RCS_CASES+build_api.profile.minimal_spec.FAULTS:
            require(before!=after,'rcS fault did not reach its owned writable boot')
        elif case not in ('changed-receipt','fd-leak','module-error','singlecpu-disabled') and not case.startswith('trace-'):
            require(before==after,'pre-admission rejection changed the disk')
        else:
            # First phase may have completed, but no installed-service record
            # may have been created after a rejected receipt/descriptor.
            native=file_log_vm.extract_native(out);record=out/'unexpected-runtime.bin'
            vm.fixture.debug(native,out,'runtime-absence',f'dump /var/lib/lab/s22-evidence-{selected["run_id"]} {record}')
            require(not record.exists(),'failed automatic entry ran installed services');runtime_absent=True
        transition=None
        if 'transition_observer' in selected:
            transition=transition_protocol.retained((out/'serial.log').read_bytes(),key=key,
                run=bytes.fromhex(selected['run_id']),expected=transition_protocol.sources(selected),
                phase=build_api.profile.phase_selected(selected),script_channel=build_api.profile.script_channel_selected(selected),minimal=minimal,
                phase_window_ms=selected.get('phase_vm_timing',{}).get('absolute_window_ms',15000))
            transition_protocol.qualify_case(transition,case)
        value=dict(status='PASS',case=case,proof=proof,ssh_health=health,shutdown=shutdown,filesystem=filesystem,
            build=pin(build/'build.json'),virtual_helper=pin(helper/'request.json'),serial=pin(out/'serial.log',maximum=4*1024**2),
            disk_before=before,disk_after=after,outside_native_unchanged=True,device_actions=0,
            host_start_requests=0,local=local,forced_host_stop=forced_stop,proof_capture=proof_capture,
            runtime_absent=runtime_absent,setup=pin(out/'setup.json'),
            local_files={name:pin(out/(name+'.bin')) for name in ('early','runtime')} if local is not None else None,scope='REAL_DEBIAN_AUTOBOOT_WITH_SAMSUNG_HARDWARE_SUBSTITUTIONS')
        if transition is not None:value['transition']=transition
        if ssh_pair is not None:value['ssh_120_seconds']=ssh_pair
        if single_cpu:value['single_cpu_vm']=dict(exposed_cpus=8,watchdog_sysfs='MODEL_ONLY',
            cpu_online='REAL_KERNEL_SYSFS',hardware_pet_proved=False)
        if case in build_api.profile.RCS_CASES+build_api.profile.minimal_spec.FAULTS:value['runtime_observation']='NOT_ACQUIRED_AFTER_RCS_FAULT'
        publish(out/'result.json',value);print(case,'PASS',flush=True);return value
    finally:
        if process is not None and process.poll() is None:process.kill();process.wait()


def suite(out,build):
    from concurrent.futures import ThreadPoolExecutor
    out=h0.private(out,fresh=True);build=h0.private(build);built=read(build/'build.json')
    transition,rcs,watchdog=build_api.profile.variants(built)
    phase=build_api.profile.phase_selected(built)
    single_cpu=build_api.profile.singlecpu_selected(built)
    post_p447=build_api.profile.post_p447_selected(built)
    script_channel=build_api.profile.script_channel_selected(built)
    minimal=build_api.profile.minimal_selected(built)
    prepared=build_api.prepare(out/'virtual',Path(built['inputs']),Path(built['packages']),
        run=built['run_id'],key=verify(built['key']).read_bytes(),virt=True,transition=transition,
        rcs=rcs,watchdog=watchdog,idle_policy=built.get('idle_policy'),phase=phase,single_cpu=single_cpu,post_p447=post_p447,script_channel=script_channel,minimal=minimal)
    require(prepared['source_inputs']==built['source_inputs'],'suite sources differ from the physical build')
    cases=build_api.profile.cases(transition,rcs,watchdog,phase,single_cpu,post_p447,script_channel,minimal)
    def single(case):
        helper=out/'virtual'
        if case in build_api.profile.TRANSITION_CASES+build_api.profile.RCS_CASES+build_api.profile.SINGLECPU_FAULTS+build_api.profile.SCRIPT_FAULTS+build_api.profile.minimal_spec.FAULTS:
            helper=out/(case+'-helper')
            prepared=build_api.prepare(helper,Path(built['inputs']),Path(built['packages']),
                run=built['run_id'],key=verify(built['key']).read_bytes(),virt=True,
                transition=True,transition_fault=case,rcs=rcs,watchdog=watchdog,idle_policy=built.get('idle_policy'),phase=phase,single_cpu=single_cpu,post_p447=post_p447,script_channel=script_channel,minimal=minimal)
            require(prepared['source_inputs']==built['source_inputs'],'fault sources differ from physical build')
        return run(out/case,build,helper,case)
    with ThreadPoolExecutor(max_workers=2) as pool:
        rows=list(pool.map(single,cases))
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

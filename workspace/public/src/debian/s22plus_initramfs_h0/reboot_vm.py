#!/usr/bin/env python3
"""Actual production two-boot runtime in ARM64 QEMU on a full sparse GPT root."""
import argparse
import ipaddress
import os
from pathlib import Path
import socket
import subprocess
import time

import autoboot as builder
import autoboot_vm as automatic
import file_log_vm
import h0
import device_action_raw_capture_v1 as raw
import s22plus_debian_autoboot_protocol_v1 as protocol
import s22plus_debian_reboot_access_v1 as owner
from s22plus_debian_autoboot_access_v1 import singlecpu_health_sample,singlecpu_health_pair
from s22plus_native_records_v3 import pin,publish,read,require,verify


def snapshot(handle,key,selected,phase,command=None):
    output=owner.capture_body(handle,'127.0.0.1',command) if command else raw.read_stdout(handle,maximum=protocol.MAXIMUM)
    if command is None:
        raw.require_success(handle);require(not raw.read_stderr(handle,maximum=16384),'VM evidence has diagnostics')
    return protocol.envelope(output,key=key,selected=selected,phase=phase)


def run(out,build,helper):
    selected=automatic.prepare(out,build,helper,'normal');require('reboot' in selected,'VM requires two-boot selection')
    cron=builder.profile.cron_selected(selected)
    config=cron=='config'
    disk=out/'disk.img';fixture=automatic.vm.fixture;life=automatic.lifecycle
    import reboot_vm_faults as faults
    faults.boundaries(out/'native.ext4',out)
    disk.unlink();fixture.make_disk(out/'native.ext4',disk,read(verify(fixture.profile.filesystem.BINDING)))
    before=fixture.fixture_tools.sparse_digest(disk);outside=life.outside_native(disk)
    with (out/'native.ext4').open('rb') as stream:initial_block=stream.read(4096)
    (out/'initial-block.bin').write_bytes(initial_block)
    initial=builder.baseline.block_projection(initial_block)
    require(initial['initial_mount_count']==selected['reboot']['initial_mount_count'],'VM initial baseline differs')
    key=verify(selected['key']).read_bytes();access=life.access.inputs(selected['run_id'])
    plan=dict(access,candidate=dict(namespace=selected['namespace'],version=selected['version'],run_id=selected['run_id']))
    with socket.socket() as reserve:reserve.bind(('127.0.0.1',0));port=reserve.getsockname()[1]
    link=plan['link'];network=ipaddress.ip_interface(link['device_address']).network
    if network.prefixlen>24:network=network.supernet(new_prefix=24)
    net=f'user,id=net,restrict=on,net={network},host={link["host_address"].split("/")[0]},'
    net+=f'dhcpstart={link["ssh_address"]},dns={network.network_address+254},hostfwd=tcp:127.0.0.1:{port}-{link["ssh_address"]}:22'
    command=[fixture.QEMU/'usr/bin/qemu-system-aarch64','-machine','virt','-cpu','cortex-a76','-smp','8','-m','1024',
        '-netdev',net,'-device','virtio-net-device,netdev=net,mac='+link['device_mac'],
        '-display','none','-monitor','none','-serial',f'file:{out}/serial.log',
        '-kernel',h0.regular(automatic.vm.KERNEL),'-initrd',out/'initramfs.cpio.gz','-append',automatic.kernel_command_line(selected),
        '-drive',f'if=none,id=root,file={disk},format=raw',
        '-device','virtio-blk-device,drive=root,logical_block_size=4096,physical_block_size=4096']
    if config:
        # Stop QEMU only when the guest executes its real ordinary reboot.
        # Preserve the clean first filesystem before the next kernel starts;
        # no post-retirement reconstruction can stand in for this identity.
        command+=['-no-reboot']
        command[command.index('-serial')+1]=f'file:{out}/kernel-1.log'
    publish(out/'command.json',list(map(str,command)));process=None;boots=[];first_control=None
    try:
        with (out/'qemu.log').open('xb') as log:
            process=subprocess.Popen(list(map(str,command)),stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,
                env=dict(os.environ,LD_LIBRARY_PATH=str(fixture.QEMU/'usr/lib/x86_64-linux-gnu')))
            deadline=time.monotonic()+360
            for phase in (1,2):
                folder=out/f'boot-{phase}';folder.mkdir(mode=0o700)
                def current():require(process.poll() is None and time.monotonic()<deadline,'VM boot window expired or kernel stopped')
                def ssh(verb,label):
                    current();return raw.acquire_command(automatic.ssh_command(plan,port,verb),folder,label,
                        timeout=min(10,deadline-time.monotonic()),stdout_maximum=protocol.MAXIMUM,stderr_maximum=16384)
                first=None
                for ordinal in range(1,61):
                    handle=ssh('health',f'initial-health-{ordinal:03d}')
                    if handle.returncode==0:
                        text=raw.read_stdout(handle,maximum=65536)
                        if f'S22_REBOOT_PHASE {phase}\n'.encode() in text:
                            singlecpu_health_sample(handle,plan);first=handle;started=time.monotonic();break
                    require(not handle.output_exceeded and handle.producer_error_type is None,'VM initial health producer failed')
                    time.sleep(2)
                require(first is not None,'VM selected boot health absent')
                proof=values=None
                for ordinal in range(1,121):
                    handle=ssh('evidence',f'evidence-{ordinal:03d}')
                    if handle.returncode==0:
                        proof,values=snapshot(handle,key,selected,phase);proof_capture=pin(handle.receipt_path);break
                    require(not handle.output_exceeded and handle.producer_error_type is None,'VM evidence producer failed')
                    time.sleep(2)
                require(proof is not None,'VM service evidence absent')
                while time.monotonic()-started<120.1:current();time.sleep(.2)
                last=ssh('health','health');pair=singlecpu_health_pair(first,last,plan,proof['kernel_boot_identity_sha256'])
                if phase==2:
                    require(values[3:5]==first_control[:2] and pair['last']['health']['boot_count']==
                        boots[0]['ssh_120_seconds']['last']['health']['boot_count']+1,'VM second boot history/count differs')
                if config and phase==2:require(values[-2]==first_control[-1],'VM configuration snapshot changed across reboot')
                elif cron and phase==2:require(values[-1]==first_control[-1],'VM cron output changed across reboot')
                verb='reboot' if phase==1 else 'shutdown'
                requested=time.monotonic();control=ssh(verb,verb)
                controlled,final=snapshot(control,key,selected,phase,verb)
                require(controlled['runtime'][verb+'_intent'] and final[0]==values[0] and final[2:]==values[2:] and
                    final[1][:-128]==values[1] and len(final[1])==len(values[1])+128,'VM control tail differs')
                extra=('config',)+(('cron',) if phase==2 else ()) if config else ('cron',) if cron else ()
                names=('early','runtime','transition')+(('first-early','first-runtime') if phase==2 else ())+extra
                for name,data in zip(names,final):
                    (folder/(name+'.bin')).write_bytes(data)
                boots.append(dict(phase=phase,proof=proof,proof_capture=proof_capture,control=controlled,
                    control_capture=pin(control.receipt_path),ssh_120_seconds=pair,
                    files={name:pin(folder/(name+'.bin')) for name in ('early','runtime','transition')+extra}))
                if phase==1:
                    first_control=final;deadline=requested+360
                    if config:
                        process.wait(timeout=max(1,deadline-time.monotonic()))
                        require(process.returncode==0 and b'reboot: Restarting system' in (out/'kernel-1.log').read_bytes(),
                            'first kernel did not execute its ordinary reboot')
                        first_native=file_log_vm.extract_native(out);first_native.rename(out/'native-first.ext4')
                        with (out/'native-first.ext4').open('rb') as stream:first_block=stream.read(4096)
                        require(builder.baseline.block_projection(first_block)['initial_mount_count']==selected['reboot']['initial_mount_count']+2,
                            'first snapshot is not the clean two-lifetime root')
                        publish(out/'first-root.json',dict(path=str(out/'native-first.ext4'),
                            sparse_sha256=fixture.fixture_tools.sparse_digest(out/'native-first.ext4'),
                            block=builder.baseline.block_projection(first_block),device_actions=0,
                            origin='ACTUAL_FIRST_KERNEL_REBOOT_EXIT'))
                        command[command.index('-serial')+1]=f'file:{out}/kernel-2.log'
                        publish(out/'second-command.json',list(map(str,command)))
                        process=subprocess.Popen(list(map(str,command)),stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,
                            env=dict(os.environ,LD_LIBRARY_PATH=str(fixture.QEMU/'usr/lib/x86_64-linux-gnu')))
            process.wait(timeout=max(1,deadline-time.monotonic()))
        if config:(out/'serial.log').write_bytes((out/'kernel-1.log').read_bytes()+(out/'kernel-2.log').read_bytes())
        serial=(out/'serial.log').read_bytes()
        require(process.returncode==0 and b'reboot: Power down' in serial and b'reboot: Restarting system' in serial,
            'actual VM reboot and final poweroff not observed')
        require(life.outside_native(disk)==outside,'two-boot VM wrote outside native_data')
        native=file_log_vm.extract_native(out)
        with native.open('rb') as stream:final_block=stream.read(4096)
        (out/'final-block.bin').write_bytes(final_block)
        final_root=builder.baseline.block_projection(final_block)
        persisted={}
        require(final_root['initial_mount_count']==selected['reboot']['initial_mount_count']+4,
            'two-boot VM did not finish exactly four clean RW setups')
        for boot in boots:
            for kind,path in builder.profile.reboot_spec.paths(selected['run_id'],boot['phase']).items():
                destination=out/f'persisted-{boot["phase"]}-{kind}.bin'
                fixture.debug(native,out,f'dump-{boot["phase"]}-{kind}',f'dump /{path} {destination}')
                require(destination.read_bytes()==verify(boot['files'][kind]).read_bytes(),
                    'final disk does not retain exact acknowledged files')
                persisted[f'{boot["phase"]}-{kind}']=pin(destination)
        if cron:
            destination=out/'persisted-cron.bin'
            fixture.debug(native,out,'dump-cron',f'dump /{builder.profile.cron_variant(cron).path(selected["run_id"])} {destination}')
            require(destination.read_bytes()==verify(boots[1]['files']['cron']).read_bytes() and
                (config or destination.read_bytes()==verify(boots[0]['files']['cron']).read_bytes()),
                'final disk does not retain exact cron workload')
            persisted['cron']=pin(destination)
        if config:
            absent=out/'retired-config.bin';path=builder.profile.cron_config_spec.config_path(selected['run_id'])
            faults.debug(native,out,'retired-config',f'dump /{path} {absent}')
            require(not absent.exists(),'configuration survived successful retirement')
        result=dict(status='PASS',case='two-boot-normal',scope='PRODUCTION_RUNTIME_ARM64_WITH_HARDWARE_SUBSTITUTIONS',
            build=pin(build/'build.json'),helper=pin(helper/'request.json'),setup=pin(out/'setup.json'),
            source=pin(Path(__file__)),boots=boots,initial_superblock=initial,final_superblock=final_root,
            serial=pin(out/'serial.log',maximum=8*1024**2),disk_before=before,
            initial_block=pin(out/'initial-block.bin'),final_block=pin(out/'final-block.bin'),
            boundary_fixture=pin(out/'boundary-fixture.json'),persisted=persisted,
            disk_after=fixture.fixture_tools.sparse_digest(disk),outside_native_unchanged=True,
            device_actions=0,physical_boot_proved=False,physical_readiness=False)
        if config:result.update(first_root=pin(out/'first-root.json'),second_command=pin(out/'second-command.json'),
            config_absent_after_retirement=True,config_absence=pin(out/'retired-config.stderr'),
            vm_reboot_boundary='GUEST_REBOOT_EXIT_THEN_FRESH_QEMU_KERNEL')
        publish(out/'result.json',result);print('PASS two-boot-normal',flush=True);return result
    except Exception as error:
        publish(out/'failure.json',dict(error_type=type(error).__name__,message=str(error),device_actions=0))
        raise
    finally:
        if process is not None and process.poll() is None:process.kill();process.wait()


def suite(out,build):
    import reboot_vm_faults as faults
    out=h0.private(out,fresh=True);built=read(build/'build.json')
    selected=builder.prepare(out/'virtual',Path(built['inputs']),Path(built['packages']),
        run=built['run_id'],key=verify(built['key']).read_bytes(),virt=True,transition=True,rcs=True,
        watchdog=True,idle_policy='cpuidle-off',single_cpu=True,post_p447=True,script_channel=True,
        minimal=True,reboot=built['reboot_baseline'],cron=builder.profile.cron_selected(built))
    require(selected['source_inputs']==built['source_inputs'],'reboot suite source closure differs')
    positive=run(out/'normal',build,out/'virtual')
    rejected=faults.suite(out/'rejections',build,out/'virtual',out/'normal')
    runtime=[]
    if builder.profile.cron_selected(built):
        import cron_vm_faults
        runtime=cron_vm_faults.suite(out/'runtime-failures',build,out/'normal')['cases']
    result=dict(schema='s22plus-debian-reboot-vm-v1',status='PASS',cases=[positive,*rejected['cases'],*runtime],
        build_sha256=pin(build/'build.json')['sha256'],source_inputs=built['source_inputs'],device_actions=0)
    publish(out/'result.json',result);return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('output','build','helper'):parser.add_argument('--'+name,type=Path,required=name!='helper')
    args=parser.parse_args()
    if args.helper:run(h0.private(args.output),h0.private(args.build),h0.private(args.helper))
    else:suite(args.output,h0.private(args.build))

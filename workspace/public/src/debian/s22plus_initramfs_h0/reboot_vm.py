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
                    require(values[3:]==first_control[:2] and pair['last']['health']['boot_count']==
                        boots[0]['ssh_120_seconds']['last']['health']['boot_count']+1,'VM second boot history/count differs')
                verb='reboot' if phase==1 else 'shutdown'
                requested=time.monotonic();control=ssh(verb,verb)
                controlled,final=snapshot(control,key,selected,phase,verb)
                require(controlled['runtime'][verb+'_intent'] and final[0]==values[0] and final[2:]==values[2:] and
                    final[1][:-128]==values[1] and len(final[1])==len(values[1])+128,'VM control tail differs')
                for name,data in zip(('early','runtime','transition','first-early','first-runtime'),final):
                    (folder/(name+'.bin')).write_bytes(data)
                boots.append(dict(phase=phase,proof=proof,proof_capture=proof_capture,control=controlled,
                    control_capture=pin(control.receipt_path),ssh_120_seconds=pair,
                    files={name:pin(folder/(name+'.bin')) for name in ('early','runtime','transition')}))
                if phase==1:first_control=final;deadline=requested+360
            process.wait(timeout=max(1,deadline-time.monotonic()))
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
        result=dict(status='PASS',case='two-boot-normal',scope='PRODUCTION_RUNTIME_ARM64_WITH_HARDWARE_SUBSTITUTIONS',
            build=pin(build/'build.json'),helper=pin(helper/'request.json'),setup=pin(out/'setup.json'),
            source=pin(Path(__file__)),boots=boots,initial_superblock=initial,final_superblock=final_root,
            serial=pin(out/'serial.log',maximum=8*1024**2),disk_before=before,
            initial_block=pin(out/'initial-block.bin'),final_block=pin(out/'final-block.bin'),
            boundary_fixture=pin(out/'boundary-fixture.json'),persisted=persisted,
            disk_after=fixture.fixture_tools.sparse_digest(disk),outside_native_unchanged=True,
            device_actions=0,physical_boot_proved=False,physical_readiness=False)
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
        minimal=True,reboot=built['reboot_baseline'])
    require(selected['source_inputs']==built['source_inputs'],'reboot suite source closure differs')
    positive=run(out/'normal',build,out/'virtual')
    rejected=faults.suite(out/'rejections',build,out/'virtual',out/'normal')
    result=dict(schema='s22plus-debian-reboot-vm-v1',status='PASS',cases=[positive,*rejected['cases']],
        build_sha256=pin(build/'build.json')['sha256'],source_inputs=built['source_inputs'],device_actions=0)
    publish(out/'result.json',result);return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('output','build','helper'):parser.add_argument('--'+name,type=Path,required=name!='helper')
    args=parser.parse_args()
    if args.helper:run(h0.private(args.output),h0.private(args.build),h0.private(args.helper))
    else:suite(args.output,h0.private(args.build))

"""Declared ARM64 runtime failures; stop the VM only after actual failure evidence."""
from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
import re
import subprocess
import time

import autoboot_vm as automatic
import h0
import s22plus_debian_cron_v1 as spec
from s22plus_native_records_v3 import pin,publish,read,require,verify


def run(out,build,helper,case):
    require(case in spec.RUNTIME_FAULTS,'unselected cron runtime fault')
    selected=automatic.prepare(out,build,helper,'normal')
    require(selected.get('transition_fault')==case and automatic.build_api.profile.cron_selected(selected),
        'runtime fault helper differs')
    fixture=automatic.vm.fixture;life=automatic.lifecycle;disk=out/'disk.img'
    outside=life.outside_native(disk);before=fixture.fixture_tools.sparse_digest(disk)
    link=life.access.inputs(selected['run_id'])['link']
    command=[fixture.QEMU/'usr/bin/qemu-system-aarch64','-machine','virt','-cpu','cortex-a76','-smp','8','-m','768',
        '-netdev','user,id=net,restrict=on','-device','virtio-net-device,netdev=net,mac='+link['device_mac'],
        '-display','none','-monitor','none','-serial',f'file:{out}/serial.log','-no-reboot',
        '-kernel',h0.regular(automatic.vm.KERNEL),'-initrd',out/'initramfs.cpio.gz',
        '-append',automatic.kernel_command_line(selected),'-drive',f'if=none,id=root,file={disk},format=raw',
        '-device','virtio-blk-device,drive=root,logical_block_size=4096,physical_block_size=4096']
    publish(out/'command.json',list(map(str,command)))
    started=time.monotonic();process=None;parked=False
    try:
        with (out/'qemu.log').open('xb') as log:
            process=subprocess.Popen(list(map(str,command)),stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,
                env=dict(os.environ,LD_LIBRARY_PATH=str(fixture.QEMU/'usr/lib/x86_64-linux-gnu')))
            while time.monotonic()-started<210:
                serial=(out/'serial.log').read_bytes() if (out/'serial.log').exists() else b''
                require(len(serial)<=8*1024**2,'runtime fault serial exceeded bound')
                if re.search(rb'DHVM_HOOK_PARK errno=\d+\r?\n',serial):parked=True;break
                require(process.poll() is None,'VM stopped before the selected hook failure')
                time.sleep(.25)
            require(parked,'cron failure did not reach its bounded observation')
            process.kill();process.wait()
        serial=(out/'serial.log').read_bytes();validate_serial(serial,case)
        require(life.outside_native(disk)==outside,'runtime fault wrote outside native_data')
        result=dict(status='PASS',case=case,scope='H0_ARM64_DECLARED_CRON_FAILURE',
            build=pin(build/'build.json'),helper=pin(helper/'request.json'),setup=pin(out/'setup.json'),
            source=pin(Path(__file__)),command=pin(out/'command.json'),serial=pin(out/'serial.log',maximum=8*1024**2),
            kernel_stopped_by_h0_driver=True,elapsed_seconds=time.monotonic()-started,returncode=process.returncode,
            outside_native_unchanged=True,disk_before=before,disk_after=fixture.fixture_tools.sparse_digest(disk),
            physical_readiness=False,device_actions=0,workload_success=False,replay_authorized=False)
        publish(out/'result.json',result);print('PASS '+case,flush=True);return result
    except Exception as error:
        publish(out/'failure.json',dict(error_type=type(error).__name__,message=str(error),device_actions=0));raise
    finally:
        if process is not None and process.poll() is None:process.kill();process.wait()


def validate_serial(serial,case):
    require(case in spec.RUNTIME_FAULTS,'unselected runtime serial interpretation')
    revocations=re.findall(rb'CRON_RAM_REVOKE claim_errno=(\d+) ready_errno=(-?\d+) schedule_errno=(-?\d+)\r?\n',serial)
    parks=re.findall(rb'DHVM_HOOK_PARK errno=(\d+)\r?\n',serial)
    require(len(revocations)==len(parks)==1 and int(parks[0])>0,'runtime failure lacks one revocation and stop')
    claim,ready,schedule=map(int,revocations[0])
    require(claim==(17 if case in ('cron-partial-write','cron-cached-revocation') else 0) and ready==0 and
        schedule==(5 if case=='cron-revoke-failure' else 0),'RAM revocation result differs')
    require(b'CRON_REPEAT_NO_WRITE partial_bytes=256' in serial if case=='cron-partial-write' else
        b'CRON_REPEAT_NO_WRITE' not in serial,'consumed partial output branch differs')
    require(b'CRON_MANUAL_REJECTED no_intent=1' in serial if case=='cron-manual-invocation' else
        b'CRON_MANUAL_REJECTED' not in serial,'direct invocation rejection differs')
    cached=re.findall(rb'CRON_CACHE_REVOKED elapsed_ms=(\d+) invocations=1 schedule_size=0 schedule_mtime=0 output_absent=1\r?\n',serial)
    require(len(cached)==1 and 65000<=int(cached[0])<300000 if case=='cron-cached-revocation' else not cached,
        'actual cached-cron revocation was not observed across a later minute')
    if case.startswith('cron-start-'):
        require(serial.count(b'Starting periodic command scheduler: cron.')==2 and
            serial.count(b'Stopping periodic command scheduler: cron.')==1 and
            b'Restarting periodic command scheduler' not in serial,'readiness repeated a control or advanced to restart')
        if case=='cron-start-delayed':
            accepted=re.findall(rb'CRON_READY_ACCEPTED phase=2 samples=(\d+)\r?\n',serial)
            require(len(accepted)==1 and int(accepted[0])>=4,'transient readiness did not end in full producer checks')
        elif case=='cron-start-timeout':
            require(b'CRON_READY_TIMEOUT phase=2 ' in serial and int(parks[0])==110,'readiness timeout was accepted')
        else:require(b'CRON_READY_REJECTED phase=2 samples=1 errno=71' in serial,
            'hard readiness identity mismatch was reobserved or accepted')
    if case in ('cron-expired-dispatch','cron-noop-service'):
        require(b'Stopping periodic command scheduler: cron.' not in serial,
            'expired/no-op child unexpectedly executed the packaged stop')
    require(b'reboot: Restarting system' not in serial and b'reboot: Power down' not in serial,
        'a stopped runtime fault performed a control action')
    return True


def suite(out,build):
    out=h0.private(out,fresh=True);built=read(build/'build.json');builder=automatic.build_api
    def single(case):
        helper=out/(case+'-helper')
        value=builder.prepare(helper,Path(built['inputs']),Path(built['packages']),run=built['run_id'],
            key=verify(built['key']).read_bytes(),virt=True,transition=True,transition_fault=case,rcs=True,
            watchdog=True,idle_policy='cpuidle-off',single_cpu=True,post_p447=True,script_channel=True,
            minimal=True,reboot=built['reboot_baseline'],cron=True)
        require(value['source_inputs']==built['source_inputs'],'runtime fault source closure differs')
        return run(out/case,build,helper,case)
    with ThreadPoolExecutor(max_workers=2) as pool:rows=list(pool.map(single,spec.RUNTIME_FAULTS))
    result=dict(status='PASS',cases=rows,device_actions=0);publish(out/'result.json',result);return result

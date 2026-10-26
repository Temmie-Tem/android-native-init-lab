"""Declared ARM64 runtime failures; stop the VM only after actual failure evidence."""
from concurrent.futures import ThreadPoolExecutor
import os
import ipaddress
from pathlib import Path
import re
import subprocess
import socket
import time

import autoboot_vm as automatic
import h0
import s22plus_debian_cron_v1 as spec
import s22plus_debian_cron_config_v1 as config_spec
import s22plus_debian_package_v1 as package_spec
import s22plus_debian_apt_v1 as apt_spec
from s22plus_native_records_v3 import pin,publish,read,require,verify


def run(out,build,helper,case,positive=None):
    package=case in package_spec.PACKAGE_FAULTS
    apt=case in apt_spec.APT_FAULTS
    require(case in spec.RUNTIME_FAULTS or case in config_spec.RUNTIME_FAULTS or package or apt,'unselected runtime fault')
    selected=automatic.prepare(out,build,helper,'normal')
    config=automatic.build_api.profile.cron_config_selected(selected)
    apt_selected=automatic.build_api.profile.apt_selected(selected)
    require(selected.get('transition_fault')==case and automatic.build_api.profile.cron_selected(selected),
        'runtime fault helper differs')
    fixture=automatic.vm.fixture;life=automatic.lifecycle;disk=out/'disk.img'
    extra={}
    if config and case not in config_spec.FIRST_PHASE_FAULTS and not package and not apt:
        require(positive is not None,'second-boot failure needs the actual first root')
        normal=read(positive/'result.json');first=read(verify(normal['first_root']));source=positive/'native-first.ext4'
        require(first['path']==str(source) and first['origin']=='ACTUAL_FIRST_KERNEL_REBOOT_EXIT' and
            source.is_file() and not source.is_symlink() and fixture.fixture_tools.sparse_digest(source)==first['sparse_sha256'] and
            read(verify(normal['helper']))['hook']['sha256']==selected['hook']['sha256'],
            'runtime failure changed the real first-boot producer or root')
        h0.run(['cp','--reflink=auto','--sparse=always',source,out/'native.ext4'],out/'copy-first.log')
        disk.unlink();fixture.make_disk(out/'native.ext4',disk,read(verify(fixture.profile.filesystem.BINDING)))
        extra=dict(positive=pin(positive/'result.json'),first_root=normal['first_root'],
            runtime_basis='ACTUAL_FIRST_KERNEL_REBOOT_ROOT')
    outside=life.outside_native(disk);before=fixture.fixture_tools.sparse_digest(disk)
    plan=life.access.inputs(selected['run_id']);link=plan['link']
    plan['candidate']=dict(namespace=selected['namespace'],version=selected['version'],run_id=selected['run_id'])
    net='user,id=net,restrict=on'
    if apt_selected:
        with socket.socket() as reserve:reserve.bind(('127.0.0.1',0));port=reserve.getsockname()[1]
        network=ipaddress.ip_interface(link['device_address']).network
        if network.prefixlen>24:network=network.supernet(new_prefix=24)
        net=f'user,id=net,restrict=off,net={network},host={link["host_address"].split("/")[0]},'
        net+=f'dhcpstart={link["ssh_address"]},dns={network.network_address+254},hostfwd=tcp:127.0.0.1:{port}-{link["ssh_address"]}:22'
    command=[fixture.QEMU/'usr/bin/qemu-system-aarch64','-machine','virt','-cpu','cortex-a76','-smp','8','-m','768',
        '-netdev',net,'-device','virtio-net-device,netdev=net,mac='+link['device_mac'],
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
            if apt_selected and case!='apt-clock-missing':
                import reboot_vm
                from s22plus_debian_autoboot_access_v1 import singlecpu_health_sample
                from s22plus_debian_apt_access_v1 import state
                folder=out/'clock';folder.mkdir(mode=0o700)
                publish(out/'operation.json',dict(scope='H0_VM_ONLY',device_actions=0,build=pin(build/'build.json')))
                deadline=started+300
                def current():require(process.poll() is None and time.monotonic()<deadline,'APT fault VM window expired')
                def ssh(verb,label):
                    current();return automatic.raw.acquire_command(automatic.ssh_command(plan,port,verb),folder,label,
                        timeout=min(10,deadline-time.monotonic()),stdout_maximum=65536,stderr_maximum=16384)
                first=None
                for ordinal in range(1,61):
                    handle=ssh('health',f'health-{ordinal:03d}')
                    if handle.returncode==0:first=handle;break
                    time.sleep(1)
                require(first is not None,'APT fault initial SSH absent')
                phase=1 if apt or case in config_spec.FIRST_PHASE_FAULTS else 2
                if case=='apt-clock-wrong-boot':
                    for ordinal in range(1,31):
                        value=state(ssh('apt-time-status',f'ready-{ordinal:02d}'))
                        if value=='READY':break
                        require(value=='WAIT','wrong-boot fixture was already claimed');time.sleep(.2)
                    require(value=='READY','wrong-boot fixture readiness absent')
                    boot=singlecpu_health_sample(first,plan)['health']['boot_id_sha256'];sec,ns=divmod(time.time_ns(),1000000000)
                    handle=ssh(f'apt-time {phase} {boot} {sec} {ns}','request');automatic.raw.require_success(handle)
                    extra['clock_request']=pin(handle.receipt_path)
                    extra['clock_first_health']=pin(first.receipt_path)
                    extra['clock_ready']=pin(folder/f'ready-{ordinal:02d}.capture.json')
                else:
                    reboot_vm.apt_clock(out,folder,phase,first,plan,ssh,current,deadline)
                    extra['clock']=reboot_vm.clock_artifacts(out,folder,first)
            limit=305 if apt_selected else 210
            while time.monotonic()-started<limit:
                serial=(out/'serial.log').read_bytes() if (out/'serial.log').exists() else b''
                require(len(serial)<=8*1024**2,'runtime fault serial exceeded bound')
                if re.search(rb'DHVM_HOOK_PARK errno=\d+\r?\n',serial):parked=True;break
                require(process.poll() is None,'VM stopped before the selected hook failure')
                time.sleep(.25)
            require(parked,'cron failure did not reach its bounded observation')
            process.kill();process.wait()
        serial=(out/'serial.log').read_bytes()
        (validate_apt_serial if apt else validate_package_serial if package else validate_config_serial if config else validate_serial)(serial,case)
        require(life.outside_native(disk)==outside,'runtime fault wrote outside native_data')
        if config and case=='config-create-partial':
            # Its marker follows the checked 31-byte write, file/parent fsync
            # and closes. After forced kernel exit, a mountless debugfs read
            # need not see the committed journal's new directory entry.
            extra.update(partial_creation_checked=True,post_stop_configuration_retention_proved=False)
        elif apt:
            # A forced kernel stop can leave the live, checked configuration's
            # inode only in the committed journal. A mountless home-block dump
            # is not a post-stop retention proof. The normal two-boot case
            # separately qualifies retention; these cases qualify the selected
            # failure after the actual native preconditions, without replay.
            extra['post_stop_configuration_retention_proved']=False
        elif config and case!='config-unlink-sync':
            import reboot_vm_faults
            native=automatic.file_log_vm.extract_native(out);destination=out/'config-after.bin'
            reboot_vm_faults.debug(native,out,'config-after',f'dump /{config_spec.config_path(selected["run_id"])} {destination}')
            if case=='config-covering-bind':require(not destination.exists(),'covering mount reached disk creation')
            else:
                expected=config_spec.schedule(selected['run_id'])
                require(destination.read_bytes()==expected,'failed workload changed or retired its configuration')
                extra['configuration_after']=pin(destination)
        result=dict(status='PASS',case=case,scope='H0_ARM64_DECLARED_CRON_FAILURE',
            build=pin(build/'build.json'),helper=pin(helper/'request.json'),setup=pin(out/'setup.json'),
            source=pin(Path(__file__)),command=pin(out/'command.json'),serial=pin(out/'serial.log',maximum=8*1024**2),
            kernel_stopped_by_h0_driver=True,elapsed_seconds=time.monotonic()-started,returncode=process.returncode,
            outside_native_unchanged=True,disk_before=before,disk_after=fixture.fixture_tools.sparse_digest(disk),
            physical_readiness=False,device_actions=0,workload_success=False,replay_authorized=False,**extra)
        if config:result['scope']='H0_ARM64_DECLARED_CRON_CONFIG_FAILURE'
        if package:result['scope']='H0_ARM64_DECLARED_PACKAGE_FAILURE'
        if apt:result['scope']='H0_ARM64_DECLARED_APT_FAILURE'
        publish(out/'result.json',result);print('PASS '+case,flush=True);return result
    except Exception as error:
        publish(out/'failure.json',dict(error_type=type(error).__name__,message=str(error),device_actions=0));raise
    finally:
        if process is not None and process.poll() is None:process.kill();process.wait()


def validate_apt_serial(serial,case):
    require(case in apt_spec.APT_FAULTS,'unselected APT failure')
    parks=re.findall(rb'DHVM_HOOK_PARK errno=(\d+)\r?\n',serial)
    require(len(parks)==1 and int(parks[0])>0 and b'APT_RESULT phase=2' not in serial and
        b'reboot: Restarting system' not in serial and b'reboot: Power down' not in serial,
        'APT failure did not remain in one stopped boot')
    if case in ('apt-clock-missing','apt-clock-wrong-boot'):
        require(parks==[b'110' if case=='apt-clock-missing' else b'71'] and b'APT_CLOCK ' not in serial and
            b'PACKAGE_COMMAND ' not in serial and b'APT_RESULT ' not in serial,'failed clock advanced into workload')
        if case=='apt-clock-missing':
            entered=re.findall(rb'APT_CLOCK_WAIT_MISSING begin_ms=(\d+) deadline_ms=(\d+)\r?\n',serial)
            expired=re.findall(rb'APT_CLOCK_WAIT_MISSING expired_ms=(\d+)\r?\n',serial)
            require(len(entered)==len(expired)==1 and int(entered[0][1])-int(entered[0][0])==5000 and
                int(entered[0][1])<=int(expired[0])<300000,'missing request did not consume the selected wait deadline')
        else:require(serial.count(b'APT_CLOCK_WAIT_REQUEST_REJECTED errno=71')==1,'wrong boot did not reach the fixed request rejection')
        return True
    commands=re.findall(rb'PACKAGE_COMMAND phase=1 step=(\d+) pid=(\d+) status=(\d+) bytes=(\d+) errno=(\d+)\r?\n',serial)
    wanted=[1,6,10]+([] if case=='apt-metadata-changed' else [11])+(
        [] if case in ('apt-metadata-changed','apt-download-changed') else [12])+(
        [2] if case in ('apt-install-failed','apt-orphan-child') else [])
    require([int(r[0]) for r in commands]==wanted and serial.count(b'APT_CLOCK phase=1 complete=1')==1,
        'APT failure repeated or advanced its command sequence')
    terminal=case not in ('apt-metadata-changed','apt-download-changed')
    successful=commands[:-1] if terminal else commands
    require(all(r[2]==r[4]==b'0' for r in successful),'APT fault prerequisites failed before the selected branch')
    corruptions=re.findall(rb'APT_FAULT_CORRUPTED kind=(metadata|archive) bytes=1\r?\n',serial)
    require(corruptions==([b'metadata'] if case=='apt-metadata-changed' else [b'archive'] if case=='apt-download-changed' else []),
        'selected RAM corruption was not reached exactly once')
    rows=re.findall(rb'APT_RESULT phase=1 intent=(\d+) complete=(\d+) errno=(\d+)\r?\n',serial)
    intended=case in ('apt-install-failed','apt-orphan-child')
    require(len(rows)==1 and rows[0][0]==(b'1' if intended else b'0') and rows[0][1]==b'0' and
        rows[0][2]==parks[0] and int(rows[0][2])>0,'APT failed transaction completed or lost intent')
    expected=b'110' if case=='apt-orphan-child' else b'10' if case=='apt-install-failed' else b'71'
    require(parks==[expected],'selected APT rejection errno differs')
    if terminal:
        require(commands[-1][4]==expected and commands[-1][2]==(b'25600' if case=='apt-install-failed' else b'0'),
            'selected APT command outcome differs')
    orphans=re.findall(rb'APT_ORPHAN_OBSERVED direct_reaped=1 eof=1 group_alive=1 status=(\d+)\r?\n',serial)
    require(orphans==([b'0'] if case=='apt-orphan-child' else []),'unsettled successful installer group was not observed')
    outputs=re.findall(rb'APT_INSTALL_FAILURE_OUTPUT bytes=(\d+) hex=([0-9a-f]*)\r?\n',serial)
    if case=='apt-install-failed':
        require(len(outputs)==1,'fixed missing-version failure output is absent')
        output=bytes.fromhex(outputs[0][1].decode())
        require(len(output)==int(outputs[0][0]) and b"E: Version '0' for 'tree' was not found\n" in output,
            'installer did not fail for the selected fixed missing version')
    else:require(not outputs,'unselected install-failure output')
    plans=re.findall(rb'APT_EXTRA_PLAN_OUTPUT bytes=(\d+) hex=([0-9a-f]*)\r?\n',serial)
    if case=='apt-plan-extra-package':
        require(len(plans)==1,'extra-install simulation output is absent')
        output=bytes.fromhex(plans[0][1].decode())
        require(len(output)==int(plans[0][0]) and b'0 upgraded, 2 newly installed, 0 to remove' in output and
            all(len(re.findall(b'^'+kind+b' '+package+rb' \([^\n]+\)$',output,re.M))==1
                for kind in (b'Inst',b'Conf') for package in (b'ed',b'tree')),
            'extra-plan fault did not produce exactly the two selected installs')
    else:require(not plans,'unselected extra-plan output')
    return True


def validate_package_serial(serial,case):
    require(case in package_spec.PACKAGE_FAULTS,'unselected package failure')
    result=re.findall(rb'PACKAGE_RESULT phase=(\d+) intent=(\d+) complete=(\d+) errno=(\d+)\r?\n',serial)
    parks=re.findall(rb'DHVM_HOOK_PARK errno=(\d+)\r?\n',serial)
    expected=10 if case=='package-install-error' else 110 if case in ('package-command-timeout','package-orphan-child') else 5 if case=='package-sync-failure' else 17 if case=='package-transaction-remnant' else 71
    require(result==[(b'1',b'1',b'0',str(expected).encode())] and parks==[str(expected).encode()],
        'package failure did not stop its one consumed transaction')
    commands=re.findall(rb'PACKAGE_COMMAND phase=1 step=(\d+) pid=(\d+) status=(\d+) bytes=(\d+) errno=(\d+)\r?\n',serial)
    steps=[int(r[0]) for r in commands]
    require(steps==([1] if case=='package-repeat-intent' else [1,2] if case in ('package-install-error','package-command-timeout') else [1,2,3,4] if case=='package-transaction-remnant' else [1,2,3,4,5]),
        'package failure repeated or advanced its command list')
    require(b'reboot: Restarting system' not in serial and b'reboot: Power down' not in serial and
        b'PACKAGE_RESULT phase=2' not in serial,'failed package work performed control or another boot')
    return True


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


def validate_config_serial(serial,case):
    require(case in config_spec.RUNTIME_FAULTS,'unselected configuration serial interpretation')
    revoked=re.findall(rb'CRON_RAM_REVOKE claim_errno=(\d+) ready_errno=(-?\d+) schedule_errno=(-?\d+)\r?\n',serial)
    parks=re.findall(rb'DHVM_HOOK_PARK errno=(\d+)\r?\n',serial)
    require(len(revoked)==len(parks)==1 and int(parks[0])>0,'configuration failure lacks one revocation and stop')
    expected=(17,0,0) if case in ('config-done-failure','config-partial-report') else (
        (5,0,0) if case=='config-revoke-failure' else (5,-1,-1) if case=='config-done-abort-claim-failure' else (0,0,0))
    require(tuple(map(int,revoked[0]))==expected,'configuration revocation result differs')
    stopped=case in config_spec.FIRST_PHASE_FAULTS+('config-proc-error','config-orphan-cron','config-unlink-sync')
    require(serial.count(b'Stopping periodic command scheduler: cron.')==int(stopped) and
        serial.count(b'Starting periodic command scheduler: cron.')==1 and
        b'Restarting periodic command scheduler' not in serial,'failed configuration repeated or advanced service controls')
    for selected,marker in (
        ('config-create-partial',b'CF_CREATE_PARTIAL bytes=31'),
        ('config-orphan-cron',b'CF_ORPHAN_CRON_OBSERVED pid='),
        ('config-unlink-sync',b'CF_UNLINK attempts=1 errno=0'),
        ('config-manual-invocation',b'CF_MANUAL_REJECTED no_intent=1'),
        ('config-partial-report',b'CF_REPEAT_NO_WRITE partial_bytes=256')):
        require(serial.count(marker)==int(case==selected),'configuration fault did not exercise its exact branch')
    require(serial.count(b'CF_SUCCESS_REJECTED errno=2')==int(case in ('config-done-failure','config-done-abort-claim-failure')),
        'failed complete-sized receipt was accepted without final publication')
    if case in ('config-expired-retirement','config-orphan-cron'):require(int(parks[0])==110,'deadline did not stop retirement')
    if case=='config-proc-error':require(int(parks[0])==13,'proc read error was treated as quiet')
    require(b'reboot: Restarting system' not in serial and b'reboot: Power down' not in serial,
        'a failed configuration performed a control action')
    return True


def suite(out,build,positive=None):
    out=h0.private(out,fresh=True);built=read(build/'build.json');builder=automatic.build_api
    cron=builder.profile.cron_selected(built);selected_spec=builder.profile.cron_variant(cron)
    def single(case):
        helper=out/(case+'-helper')
        value=builder.prepare(helper,Path(built['inputs']),Path(built['packages']),run=built['run_id'],
            key=verify(built['key']).read_bytes(),virt=True,transition=True,transition_fault=case,rcs=True,
            watchdog=True,idle_policy='cpuidle-off',single_cpu=True,post_p447=True,script_channel=True,
            minimal=True,reboot=built['reboot_baseline'],cron=cron)
        require(value['source_inputs']==built['source_inputs'],'runtime fault source closure differs')
        return run(out/case,build,helper,case,positive)
    with ThreadPoolExecutor(max_workers=2) as pool:rows=list(pool.map(single,selected_spec.RUNTIME_FAULTS))
    result=dict(status='PASS',cases=rows,device_actions=0);publish(out/'result.json',result);return result

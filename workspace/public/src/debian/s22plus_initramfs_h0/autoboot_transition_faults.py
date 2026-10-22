"""Declared VM substitutions in copies of the actual transition producers."""
from pathlib import Path
from s22plus_native_records_v3 import require,pin
from s22plus_debian_autoboot_profile_v1 import TRANSITION_CASES,RCS_CASES,SINGLECPU_FAULTS,SCRIPT_FAULTS
from s22plus_debian_autoboot_minimal_v1 import FAULTS as MINIMAL_FAULTS
CASES=TRANSITION_CASES+RCS_CASES+SINGLECPU_FAULTS+SCRIPT_FAULTS+MINIMAL_FAULTS


def source(out,original,fault,native):
    require(fault in CASES,'unselected transition fault')
    folder=out/(original.stem+'-transition-fault');folder.mkdir()
    here=Path(__file__).parent
    for base in (here,native):
        for path in base.iterdir():
            if path.suffix in ('.c','.h','.def'):(folder/path.name).write_bytes(path.read_bytes())
    def edit(name,old,new,count=1):
        path=folder/name;text=path.read_text()
        require(text.count(old)==count,'transition fixture anchor differs: '+name)
        path.write_text(text.replace(old,new))
    if fault in MINIMAL_FAULTS:
        injection={
            'minimal-missing-program':'if(phase==1 && unlink(AP_DISPATCHER))dh_hook_fail(errno);',
            'minimal-changed-program':'''if(phase==1) {
                int altered=open(AP_DISPATCHER,O_WRONLY|O_CLOEXEC|O_NOFOLLOW);
                if(altered<0 || write(altered,"X",1)!=1 || close(altered))dh_hook_fail(EIO);
            }''',
            'minimal-missing-dependency':'if(phase==1 && umount2("/dev/shm",0))dh_hook_fail(errno);',
            'minimal-script-error':'''if(phase==1) {
                static const char body[]="#!/bin/sh\\nexit 37\\n";
                int fixture=open("/run/s22-debian/fixture-fail",O_WRONLY|O_CREAT|O_EXCL|O_CLOEXEC,0500);
                if(fixture<0 || write(fixture,body,sizeof(body)-1)!=sizeof(body)-1 || close(fixture) ||
                    mount("/run/s22-debian/fixture-fail","/etc/init.d/hostname.sh",NULL,MS_BIND,NULL))dh_hook_fail(EIO);
            }'''}[fault]
        anchor='    if(phase==1 && (error=ap_required_program()))dh_hook_fail(error);'
        edit('s22plus_debian_handoff_observer_v2.inc.c',anchor,'    '+injection+'\n'+anchor)
    elif fault=='script-channel-setup':
        edit('s22plus_autoboot_script_v1.h','ap_expired() ? ETIMEDOUT : ap_dispatcher_prepare()',
            'ap_expired() ? ETIMEDOUT : ENOSPC')
    elif fault=='script-channel-gap':
        edit('s22plus_autoboot_script_channel_v1.h','decoded.sequence!=ap.packet_sequence+1 ||',
            '(decoded.sequence==2 || decoded.sequence!=ap.packet_sequence+1) ||')
    elif fault=='singlecpu-disabled':
        edit('s22plus_autoboot_singlecpu_v1.h','strcpy(disable,"0\\n")','strcpy(disable,"1\\n")')
    elif fault in ('trace-file-close','trace-parent-close','trace-root-close'):
        stage,fd={'trace-file-close':('FILE_CLOSE','fd'),'trace-parent-close':('PARENT_CLOSE','parent'),
            'trace-root-close':('ROOT_CLOSE','root')}[fault]
        edit('file-log.c',f'AT_SYS(AT_{stage},close({fd}))',f'AT_SYS(AT_{stage},close(-1))',2 if fd=='root' else 1)
    elif fault=='trace-unmount':edit('file-log.c','umount2(fl_root,0)','umount2(fl_root,INT_MAX)')
    elif fault in ('trace-ro','trace-post-super'):
        stage,call=('RESTORE_RO','ri_ro(&e,true)') if fault=='trace-ro' else ('SUPER_READ','fs1_read_super(&e,false)')
        edit('file-log.c',f'AT_CHECK(AT_{stage},{call})',
            f'AT_CHECK(AT_{stage},(unlinkat(e.node_fd,"native",0),{call}))')
    elif fault=='trace-receipt':edit('file-log.c','AT_CHECK(AT_RECEIPT,fl_publish())',
        'AT_CHECK(AT_RECEIPT,(mkdir("/run/initramfs/autoboot-early",0400),fl_publish()))')
    elif fault=='trace-second-admission':edit('autoboot-init.c','ri_run(3,args,"staged",sw_next)',
        'ri_run(3,args,"invalid-fixture-command",sw_next)')
    elif fault=='trace-root-activate':edit('s22plus_debian_handoff_prepare_v1.inc.c',
        'mount(fs1_node,ri_root,"ext4",0,"errors=remount-ro,nodiscard")',
        'mount(fs1_node,ri_root,"absent-fixture-filesystem",0,"errors=remount-ro,nodiscard")')
    elif fault=='trace-move-dev':edit('s22plus_switch_root_v1.c','mount(from,to,NULL,MS_MOVE,NULL)',
        'mount(from,stage==AT_MOVE_DEV?"/absent-fixture-destination":to,NULL,MS_MOVE,NULL)')
    elif fault=='trace-switch-exec':edit('s22plus_switch_root_v1.c','execve("/s22-switch-busybox",args,env)',
        'execve("/absent-fixture-busybox",args,env)')
    elif fault=='trace-witness':edit('s22plus_switch_root_witness_v1.c','sw_require(AT_CHECK(AT_WITNESS_CHECK,sw_witness()));',
        'sw.witness_digest[0]^=1;sw_require(AT_CHECK(AT_WITNESS_CHECK,sw_witness()));')
    elif fault=='trace-init-exec':edit('s22plus_debian_handoff_witness_v1.inc.c','execve("/sbin/init",args,env)',
        'execve("/absent-fixture-init",args,env)')
    elif fault=='trace-init-identity':
        edit('s22plus_debian_handoff_hook_v1.c','if((error=AT_CHECK(AT_ACTUAL_INIT_CHECK,dh_actual_init(&state))))',
            'state.hook_sha[0]^=1;\n    if((error=AT_CHECK(AT_ACTUAL_INIT_CHECK,dh_actual_init(&state))))')
        edit('s22plus_debian_handoff_hook_v1.c','dprintf(2,"DHVM_HOOK_PARK errno=%d\\n",error);',
            'dprintf(2,"DHVM_HOOK_PARK errno=%d\\n",error);\n    (void)syscall(SYS_reboot,LINUX_REBOOT_MAGIC1,LINUX_REBOOT_MAGIC2,LINUX_REBOOT_CMD_POWER_OFF,0);')
    elif fault=='trace-logger-loss':edit('s22plus_autoboot_transition_v1.h',
        'at_moved?"/newroot/dev/kmsg":"/dev/kmsg"','"/absent-fixture-kmsg"')
    elif fault=='trace-pending':edit('file-log.c','AT_SYS(AT_FILE_CLOSE,close(fd))',
        'AT_SYS(AT_FILE_CLOSE,({for(;;)pause();close(fd);}))')
    elif fault=='rcs-record-fsync':edit('s22plus_debian_evidence_v1.inc.c',
        'AT_SYS(AT_RCS_RECORD_FSYNC,fsync(fd))','AT_SYS(AT_RCS_RECORD_FSYNC,fsync(-1))')
    elif fault=='rcs-close-range':edit('s22plus_debian_handoff_observer_v2.inc.c',
        'AT_SYS(AT_RCS_CHILD_CLOSE_FDS,syscall(SYS_close_range,first,UINT_MAX,0U))',
        'AT_SYS(AT_RCS_CHILD_CLOSE_FDS,syscall(SYS_close_range,first,UINT_MAX,UINT_MAX))')
    elif fault=='rcs-exec':edit('s22plus_debian_handoff_observer_v2.inc.c',
        'execv(path,args));','execv("/absent-fixture-rcs",args));')
    elif fault=='rcs-wait':edit('s22plus_debian_handoff_observer_v2.inc.c',
        'AT_SYS(AT_RCS_WAIT_FIRST,waitpid(child,&status,WNOHANG))',
        'AT_SYS(AT_RCS_WAIT_FIRST,waitpid(child,&status,INT_MAX))')
    elif fault=='rcs-sleep':
        edit('s22plus_debian_handoff_observer_v2.inc.c',
            'struct timespec delay={0,10000000};','struct timespec delay={0,1000000000};')
        edit('s22plus_debian_handoff_observer_v2.inc.c',
            '\n        if(sw_now()>=sw.deadline_ms)_exit(124);',
            '\n        if(traced)for(;;)pause();\n        if(sw_now()>=sw.deadline_ms)_exit(124);')
    elif fault=='rcs-pending-record':edit('s22plus_debian_evidence_v1.inc.c',
        'AT_SYS(AT_RCS_RECORD_FSYNC,fsync(fd))',
        'AT_SYS(AT_RCS_RECORD_FSYNC,({for(;;)pause();fsync(fd);}))')
    elif fault=='rcs-pending-child':edit('s22plus_debian_handoff_observer_v2.inc.c',
        '\n        if(sw_now()>=sw.deadline_ms)_exit(124);',
        '\n        if(traced)for(;;)pause();\n        if(sw_now()>=sw.deadline_ms)_exit(124);')
    if (fault in RCS_CASES and not fault.startswith('rcs-pending-')) or fault in MINIMAL_FAULTS:
        edit('s22plus_debian_handoff_hook_v1.c','dprintf(2,"DHVM_HOOK_PARK errno=%d\\n",error);',
            'dprintf(2,"DHVM_HOOK_PARK errno=%d\\n",error);\n    (void)syscall(SYS_reboot,LINUX_REBOOT_MAGIC1,LINUX_REBOOT_MAGIC2,LINUX_REBOOT_CMD_POWER_OFF,0);')
    target=folder/original.name
    target.write_text('#ifndef S22_ROOT_INSPECT_VIRT_TEST\n#error "transition fault is VM-only"\n#endif\n'+target.read_text())
    return target,[pin(path) for path in sorted(folder.iterdir())]

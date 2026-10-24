"""Strict raw rederivation of the selected two-boot production VM corpus."""
from pathlib import Path
import re
import device_action_raw_capture_v1 as raw
import s22plus_debian_reboot_v1 as spec
import s22plus_debian_reboot_baseline_v1 as baseline
import s22plus_debian_reboot_access_v1 as owner
import s22plus_debian_autoboot_protocol_v1 as protocol
import s22plus_debian_autoboot_access_v1 as access
from s22plus_native_records_v3 import read,require,verify


def rejection(serial,case):
    """A completed dirty observation is not admission or a writable lifetime."""
    rows=re.findall(rb'^RI1_RESULT complete=(\d+) stage=(\d+) errno=(\d+) cleanup_errno=(\d+) partition_ro=(\d+) clean=(-?\d+) mounted=(\d+) unmounted=(\d+)\r?$',serial,re.M)
    require(len(rows)==1,'root fault lacks one complete terminal observation')
    complete,stage,error,cleanup,ro,clean,mounted,unmounted=map(int,rows[0])
    require(cleanup==0 and ro==1 and (not mounted or unmounted==1),'root fault lacks settled protected cleanup')
    if case=='dirty':
        require((complete,stage,error,clean,mounted,unmounted)==(1,10,0,0,0,0) and
            b'JR1_SKIP clean=0' in serial,'dirty root was not rejected by the clean-only admission')
    else:require(complete==0 and error!=0,'root fault was not rejected')
    return True


def vm_results(tested,built,key):
    from s22plus_debian_autoboot_qualification_v1 import producer
    require(tested['schema']=='s22plus-debian-reboot-vm-v1' and tested['status']=='PASS' and
        tested['device_actions']==0 and tested['source_inputs']==built['source_inputs'] and
        tuple(row['case'] for row in tested['cases'])==('two-boot-normal','clean-error-unmount','second-root-control',*spec.ROOT_CASES),
        'two-boot VM corpus or source closure differs')
    sources={r['path']:r['sha256'] for r in built['source_inputs']}
    positive=None
    for row in tested['cases']:
        require(row['status']=='PASS' and row['device_actions']==0 and row['outside_native_unchanged'] is True and
            row['physical_readiness'] is False,'VM result promoted authority or omitted isolation')
        helper=producer(read(verify(row['helper'])),virtual=True)
        require(helper['source_inputs']==built['source_inputs'] and helper['run_id']==built['run_id'] and
            helper['reboot']==built['reboot'] and helper['reboot_baseline']==built['reboot_baseline'] and
            helper['modules']==built['modules'] and helper['history']==built['history'] and
            verify(helper['key']).read_bytes()==key,'two-boot VM helper does not join physical-format build')
        require(row['build']['sha256']==tested['build_sha256'],'two-boot VM build receipt differs')
        verify(row['build']);setup=read(verify(row['setup']))
        require(setup['helper']==row['helper'] and setup['build']==row['build'] and setup['case']==('changed-receipt' if row['case']=='changed-current-receipt' else 'normal') and
            setup['device_actions']==0,'two-boot VM setup differs')
        verify(setup['initramfs'],maximum=32*1024**2)
        for receipt in (row['source'],setup['source']):
            name=str(Path(receipt['path']).relative_to(spec.ROOT))
            require(sources.get(name)==receipt['sha256'],'VM driver is not frozen in the build')
            verify(receipt)
        serial=verify(row['serial'],maximum=8*1024**2).read_bytes()
        if row['case']=='changed-current-receipt':
            require(row['runtime_absent'] is True and row['disk_before']!=row['disk_after'] and
                b'AUTO_VM_RECEIPT_MUTATED' in serial and b'reboot: Power down' in serial and
                baseline.block_projection(verify(row['final_block']).read_bytes())==row['final_superblock'] and
                row['final_superblock']['initial_mount_count']==built['reboot']['initial_mount_count']+1,
                'changed current receipt advanced beyond early RW')
            continue
        if row['case'] in ('clean-error-unmount','second-root-control'):
            require(helper.get('transition_fault')=='reboot-clean-error' and row['disk_before']!=row['disk_after'] and
                b'RI1_RESULT complete=1' in serial and b'FILE_PILOT result=REJECTED error=5 records=0 bytes=0' in serial and
                b'AUTO_VM_EARLY_STOP' in serial and b'reboot: Power down' in serial and row['current_files_absent'] is True and
                baseline.block_projection(verify(row['final_block']).read_bytes())==row['final_superblock'] and
                row['final_superblock']['initial_mount_count']==built['reboot']['initial_mount_count']+(
                    3 if row['case']=='second-root-control' else 1),
                'clean error-unmount did not consume its one writable setup')
            continue
        require(helper.get('transition_fault')==('reboot-clean-error' if row['case']=='clean-error-retry' else None),
            'unselected VM fault helper')
        if row['case']!='two-boot-normal':
            require(row['scope']=='H0_REGULAR_FILE_PRODUCTION_ROOT_ADMISSION' and
                row['disk_before']==row['disk_after'] and rejection(serial,row['case']) and
                b'AUTO_VM_EARLY_STOP' in serial and b'reboot: Power down' in serial and
                read(verify(row['positive']))==positive,'root rejection evidence differs')
            if row['case']=='clean-error-retry':
                clean=read(verify(row['clean_error']))
                require(clean==tested['cases'][1] and row['fixture']=='ORIGINAL_COUNTED_ERROR_UNMOUNT' and
                    row['helper']==clean['helper'] and
                    setup['initramfs']['sha256']==read(verify(clean['setup']))['initramfs']['sha256'],
                    'retry did not use the original consumed error-unmount')
            continue
        positive=row
        require(row['scope']=='PRODUCTION_RUNTIME_ARM64_WITH_HARDWARE_SUBSTITUTIONS' and
            row['physical_boot_proved'] is False and b'reboot: Restarting system' in serial and
            b'reboot: Power down' in serial and len(row['boots'])==2,'two actual VM boots absent')
        for name in ('initial','final'):
            require(baseline.block_projection(verify(row[name+'_block']).read_bytes())==row[name+'_superblock'],
                'VM superblock does not rederive')
        m=built['reboot']['initial_mount_count']
        require(row['initial_superblock']['initial_mount_count']==m and
            row['final_superblock']['initial_mount_count']==m+4,'four clean RW setups not demonstrated')
        fixture=read(verify(row['boundary_fixture']))
        require(fixture['kind']=='H0_SYNTHETIC' and fixture['device_actions']==0 and
            set(fixture['files'])==set(spec.ROTATIONS)|{'var/lib/lab/shutdown-start','var/lib/lab/boot-count'},
            'positive finite boundary fixture differs')
        for receipt in fixture['files'].values():verify(receipt)
        require(fixture['files']['var/lib/lab/shutdown-start']['sha256']==spec.SHUTDOWN_MARKER_SHA256 and
            verify(fixture['files']['var/lib/lab/boot-count']).read_bytes()==b'99998\n','positive marker/count boundary differs')
        previous=None;first_parts=None
        plan=access.access.inputs(built['run_id']);plan['candidate']=dict(namespace=built['namespace'],
            version=built['version'],run_id=built['run_id'])
        for phase,boot in enumerate(row['boots'],1):
            require(boot['phase']==phase,'VM boot phase ordering differs')
            handle=raw.load_handle(verify(boot['proof_capture']));raw.require_success(handle)
            require(not raw.read_stderr(handle,maximum=16384),'VM evidence has diagnostics')
            proof,parts=protocol.envelope(raw.read_stdout(handle,maximum=protocol.MAXIMUM),key=key,selected=helper,phase=phase)
            require(proof==boot['proof'],'VM service evidence does not rederive')
            pair=boot['ssh_120_seconds']
            observed=access.singlecpu_health_pair(raw.load_handle(verify(pair['first']['health']['capture'])),
                raw.load_handle(verify(pair['last']['health']['capture'])),plan,proof['kernel_boot_identity_sha256'])
            require(pair==observed and pair['last']['health']['boot_count']==99998+phase,
                'VM interval or counter ceiling does not rederive')
            for sample in (pair['first'],pair['last']):
                capture=raw.load_handle(verify(sample['health']['capture']))
                require(raw.read_stdout(capture,maximum=65536).count(f'S22_REBOOT_PHASE {phase}\n'.encode())==1,
                    'VM SSH health phase differs')
            verb='reboot' if phase==1 else 'shutdown'
            handle=raw.load_handle(verify(boot['control_capture']))
            controlled,final=protocol.envelope(owner.capture_body(handle,'127.0.0.1',verb),key=key,selected=helper,phase=phase)
            require(controlled==boot['control'] and controlled['runtime'][verb+'_intent'] and
                final[0]==parts[0] and final[2:]==parts[2:] and final[1][:-128]==parts[1] and
                len(final[1])==len(parts[1])+128,'VM one-shot final control tail differs')
            for index,kind in enumerate(('early','runtime','transition')):
                require(verify(boot['files'][kind]).read_bytes()==final[index],'saved final evidence differs')
                if kind!='transition':require(verify(row['persisted'][f'{phase}-{kind}']).read_bytes()==final[index],
                    'final disk evidence differs from acknowledged bytes')
            if phase==2:
                require(parts[3:]==first_parts[:2] and proof['kernel_boot_identity_sha256']!=previous,
                    'second VM boot did not preserve the exact first pair')
            previous=proof['kernel_boot_identity_sha256'];first_parts=final
    return tested

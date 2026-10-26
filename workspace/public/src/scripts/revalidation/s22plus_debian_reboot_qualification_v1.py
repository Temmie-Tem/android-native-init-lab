"""Strict raw rederivation of the selected two-boot production VM corpus."""
from pathlib import Path
import re
import types
import device_action_raw_capture_v1 as raw
import s22plus_debian_reboot_v1 as spec
import s22plus_debian_reboot_baseline_v1 as baseline
import s22plus_debian_reboot_access_v1 as owner
import s22plus_debian_autoboot_protocol_v1 as protocol
import s22plus_debian_autoboot_access_v1 as access
from s22plus_native_records_v3 import pin,read,require,verify


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


def vm_clock(value,build,plan,phase,folder,proof=None):
    """Consume the actual H0 SSH request/status and its original window."""
    import s22plus_debian_apt_access_v1 as apt_access
    require(set(value)=={'result','window','initial_health','operation'},'VM clock artifact shape differs')
    require(verify(value['result']).parent==folder and verify(value['initial_health']).parent==folder,
        'VM clock evidence belongs to another case or boot folder')
    require(value['result']==pin(folder/'clock.json') and value['window']==pin(folder/'window.json') and
        value['operation']==pin(folder.parent/'operation.json'),'VM clock locations differ')
    operation=read(verify(value['operation']));window=read(verify(value['window']))
    require(operation==dict(scope='H0_VM_ONLY',device_actions=0,build=build) and window['basis']['scope']=='H0_VM',
        'VM clock operation or window scope differs')
    first=raw.load_handle(verify(value['initial_health']));sample=access.singlecpu_health_sample(first,plan)
    require(raw.read_stdout(first,maximum=65536).count(f'S22_REBOOT_PHASE {phase}\n'.encode())==1,'VM clock initial phase differs')
    client=types.SimpleNamespace(adapter=types.SimpleNamespace(directory=folder.parent),reboot_phase=phase,
        basis=lambda:window['basis'])
    result=apt_access.rederive_request(client,folder,sample['health']['boot_id_sha256'])
    if proof is not None:
        require(sample['health']['boot_id_sha256']==proof['kernel_boot_identity_sha256'],'VM clock runtime boot differs')
        require(result==apt_access.rederive(client,folder,proof),'VM clock runtime event differs')
    return result


def vm_results(tested,built,key):
    from s22plus_debian_autoboot_qualification_v1 import producer
    from s22plus_debian_autoboot_profile_v1 import cron_selected,cron_variant
    cron=cron_selected(built)
    cron_spec=cron_variant(cron);config=cron in ('config','download','package','apt')
    require(tested['schema']=='s22plus-debian-reboot-vm-v1' and tested['status']=='PASS' and
        tested['device_actions']==0 and tested['source_inputs']==built['source_inputs'] and
        tuple(row['case'] for row in tested['cases'])==('two-boot-normal','clean-error-unmount','second-root-control',*spec.ROOT_CASES,
            *(cron_spec.ROOT_CASES if cron else ()),*(tuple(cron_spec.RUNTIME_FAULTS) if cron else ())),
        'two-boot VM corpus or source closure differs')
    sources={r['path']:r['sha256'] for r in built['source_inputs']}
    positive=None
    for row in tested['cases']:
        require(row['status']=='PASS' and row['device_actions']==0 and row['outside_native_unchanged'] is True and
            row['physical_readiness'] is False,'VM result promoted authority or omitted isolation')
        helper=producer(read(verify(row['helper'])),virtual=True)
        require(helper['source_inputs']==built['source_inputs'] and helper['run_id']==built['run_id'] and
            helper.get('cron')==built.get('cron') and helper['reboot']==built['reboot'] and helper['reboot_baseline']==built['reboot_baseline'] and
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
        if cron and row['case'] in cron_spec.RUNTIME_FAULTS:
            from cron_vm_faults import validate_serial,validate_config_serial,validate_package_serial,validate_apt_serial
            from s22plus_debian_package_v1 import PACKAGE_FAULTS
            from s22plus_debian_apt_v1 import APT_FAULTS
            package=cron=='package' and row['case'] in PACKAGE_FAULTS
            apt=cron=='apt' and row['case'] in APT_FAULTS
            if cron=='apt':
                plan=access.access.inputs(built['run_id']);plan['candidate']=dict(namespace=built['namespace'],
                    version=built['version'],run_id=built['run_id'])
                if row['case'] not in ('apt-clock-missing','apt-clock-wrong-boot'):
                    phase=1 if row['case'] in cron_spec.FIRST_PHASE_FAULTS else 2
                    case_directory=verify(row['setup']).parent
                    require(verify(row['serial']).parent==case_directory,'VM clock serial owner differs')
                    vm_clock(row['clock'],row['build'],plan,phase,case_directory/'clock')
                elif row['case']=='apt-clock-wrong-boot':
                    from s22plus_debian_apt_access_v1 import state
                    folder=verify(row['setup']).parent/'clock'
                    require(verify(row['serial']).parent==folder.parent and
                        all(verify(row[name]).parent==folder for name in ('clock_first_health','clock_ready','clock_request')),
                        'wrong-boot clock artifacts belong to another VM case')
                    first=raw.load_handle(verify(row['clock_first_health']));access.singlecpu_health_sample(first,plan)
                    require(raw.read_stdout(first,maximum=65536).count(b'S22_REBOOT_PHASE 1\n')==1 and
                        state(raw.load_handle(verify(row['clock_ready'])))=='READY','wrong-boot fixture readiness differs')
                    request=raw.load_handle(verify(row['clock_request']));raw.require_success(request)
                    require(raw.read_stdout(request,maximum=4096)==b'S22_APT_CLOCK_REQUESTED\n' and
                        not raw.read_stderr(request,maximum=16384),'wrong-boot fixture request was not published')
            if apt:
                require(row['scope']=='H0_ARM64_DECLARED_APT_FAILURE' and
                    row['kernel_stopped_by_h0_driver'] is True and row['workload_success'] is False and
                    row['replay_authorized'] is False and row['returncode']==-9 and
                    helper.get('transition_fault')==row['case'] and 0<row['elapsed_seconds']<310,
                    'APT failure was promoted or changed its substitution')
                verify(row['command']);validate_apt_serial(serial,row['case'])
                require(row['post_stop_configuration_retention_proved'] is False and
                    'configuration_after' not in row,
                    'stopped APT fault was promoted to post-stop configuration retention')
                continue
            if package:
                require(row['scope']=='H0_ARM64_DECLARED_PACKAGE_FAILURE' and
                    row['kernel_stopped_by_h0_driver'] is True and row['workload_success'] is False and
                    row['replay_authorized'] is False and row['returncode']==-9 and
                    helper.get('transition_fault')==row['case'] and 0<row['elapsed_seconds']<215,
                    'package failure was promoted or changed its substitution')
                verify(row['command']);validate_package_serial(serial,row['case'])
                require(verify(row['configuration_after']).read_bytes()==cron_spec.schedule(built['run_id']),
                    'failed package operation changed the first configuration')
                continue
            require(row['scope']==('H0_ARM64_DECLARED_CRON_CONFIG_FAILURE' if config else 'H0_ARM64_DECLARED_CRON_FAILURE') and row['kernel_stopped_by_h0_driver'] is True and
                row['workload_success'] is False and row['replay_authorized'] is False and row['returncode']==-9 and
                helper.get('transition_fault')==row['case'] and 0<row['elapsed_seconds']<(310 if cron=='apt' else 215),
                'runtime failure was promoted to success or changed its substitution')
            verify(row['command']);(validate_config_serial if config else validate_serial)(serial,row['case'])
            if config:
                if row['case'] not in cron_spec.FIRST_PHASE_FAULTS:
                    require(row['runtime_basis']=='ACTUAL_FIRST_KERNEL_REBOOT_ROOT' and
                        read(verify(row['positive']))==positive and row['first_root']==positive['first_root'],
                        'second-boot failure did not use the actual first-boot root')
                if row['case']=='config-create-partial':
                    require(row['partial_creation_checked'] is True and row['post_stop_configuration_retention_proved'] is False and
                        'configuration_after' not in row,'partial creation was promoted to post-stop retention')
                elif row['case'] not in ('config-covering-bind','config-unlink-sync'):
                    expected=cron_spec.schedule(built['run_id'])
                    require(verify(row['configuration_after']).read_bytes()==expected,'failed operation retired or changed its configuration')
            continue
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
        if cron in ('download','package','apt'):__import__('s22plus_debian_download_v1').validate_vm_return(serial)
        for name in ('initial','final'):
            require(baseline.block_projection(verify(row[name+'_block']).read_bytes())==row[name+'_superblock'],
                'VM superblock does not rederive')
        m=built['reboot']['initial_mount_count']
        require(row['initial_superblock']['initial_mount_count']==m and
            row['final_superblock']['initial_mount_count']==m+4,'four clean RW setups not demonstrated')
        if config:
            from reboot_vm_faults import automatic
            first=read(verify(row['first_root']));first_path=Path(first['path'])
            require(first_path==verify(row['first_root']).parent/'native-first.ext4' and
                first_path.is_file() and not first_path.is_symlink() and first['device_actions']==0 and
                first['origin']=='ACTUAL_FIRST_KERNEL_REBOOT_EXIT' and
                first['sparse_sha256']==automatic.vm.fixture.fixture_tools.sparse_digest(first_path) and
                first['block']['initial_mount_count']==m+2 and row['config_absent_after_retirement'] is True and
                row['vm_reboot_boundary']=='GUEST_REBOOT_EXIT_THEN_FRESH_QEMU_KERNEL',
                'first-root snapshot or final retirement differs')
            verify(row['second_command'])
            require(verify(row['config_absence']).read_bytes()==b'debugfs 1.47.2 (1-Jan-2025)\n/'+
                cron_spec.config_path(built['run_id']).encode()+b': File not found by ext2_lookup \n',
                'final configuration absence does not rederive')
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
            if cron=='apt':
                folder=verify(row['setup']).parent/f'boot-{phase}'
                require(verify(row['serial']).parent==folder.parent,'positive clock serial owner differs')
                vm_clock(boot['clock'],row['build'],plan,phase,folder,proof)
            pair=boot['ssh_120_seconds']
            observed=access.singlecpu_health_pair(raw.load_handle(verify(pair['first']['health']['capture'])),
                raw.load_handle(verify(pair['last']['health']['capture'])),plan,proof['kernel_boot_identity_sha256'])
            require(pair==observed and pair['last']['health']['boot_count']==99998+phase,
                'VM interval or counter ceiling does not rederive')
            for sample in (pair['first'],pair['last']):
                capture=raw.load_handle(verify(sample['health']['capture']))
                require(raw.read_stdout(capture,maximum=65536).count(f'S22_REBOOT_PHASE {phase}\n'.encode())==1,
                    'VM SSH health phase differs')
            verb='reboot' if phase==1 else 'download' if cron in ('download','package','apt') else 'shutdown'
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
                require(parts[3:5]==first_parts[:2] and proof['kernel_boot_identity_sha256']!=previous,
                    'second VM boot did not preserve the exact first pair')
            if config:
                require(verify(boot['files']['config']).read_bytes()==(final[-1] if phase==1 else final[-2])==
                    cron_spec.schedule(built['run_id']),'configuration snapshot differs from the consumed bytes')
                if phase==2:
                    require(final[-2]==first_parts[-1] and verify(boot['files']['cron']).read_bytes()==final[-1]==
                        verify(row['persisted']['cron']).read_bytes(),'configuration report or preservation differs')
            elif cron:
                require(verify(boot['files']['cron']).read_bytes()==final[-1]==verify(row['persisted']['cron']).read_bytes(),
                    'cron persisted bytes differ from the acknowledged producer')
                if phase==2:require(final[-1]==first_parts[-1],'cron bytes changed across reboot')
            previous=proof['kernel_boot_identity_sha256'];first_parts=final
    return tested

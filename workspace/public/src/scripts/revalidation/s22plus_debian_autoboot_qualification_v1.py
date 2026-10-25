"""Bind automatic boot to its exact physical archive and real ARM64 corpus."""
import hashlib
from dataclasses import replace
import gzip
import io
from pathlib import Path,PurePosixPath
import re
import stat

import device_action_raw_capture_v1 as raw
import s22plus_debian_access_v1 as access
import s22plus_debian_reboot_baseline_v1 as baseline
import s22plus_debian_autoboot_profile_v1 as profile
import s22plus_debian_autoboot_protocol_v1 as protocol
import s22plus_debian_early_profile_v1 as early
import s22plus_debian_integrated_profile_v1 as archive
from s22plus_native_records_v3 import read,require,verify


def copy_readback(row,parts):
    """Validate retained H0 replay evidence; never replay or write here."""
    value=read(verify(row['local_retrieval']))
    require(value['schema']=='s22plus-autoboot-vm-copy-readback-v1' and
        value['scope']=='H0_REGULAR_FILE_COPY_JOURNAL_REPLAY' and value['device_actions']==0 and
        all(value[name] is False for name in ('ssh_access_proved','clean_shutdown_proved','physical_journal_replay_authorized')),
        'VM copy replay was promoted to physical authority or live proof')
    before=read(verify(value['original_before']))
    folder=Path(row['setup']['path']).parent
    require(before==dict(disk=value['original_disk_before'],native=value['original_native_before']) and
        value['original_disk_before']['path']==str(folder/'disk.img') and
        value['original_native_before']['path']==str(folder/'native-after.ext4') and
        value['original_disk_before']==value['original_disk_after'] and
        value['original_native_before']==value['original_native_after'] and
        value['original_disk_after']['extent_sha256']==row['disk_after'] and
        value['original_native_before']['size']==value['copy_before']['size']==value['copy_after']['size'] and
        value['original_native_before']['logical_nonzero_64k_sha256']==value['copy_before']['logical_nonzero_64k_sha256'] and
        value['copy_before']['extent_sha256']!=value['copy_after']['extent_sha256'],
        'VM copy source preservation or pre-replay equality differs')
    for item in (value['original_disk_after'],value['original_native_after'],value['copy_after']):
        path=Path(item['path']);st=path.lstat()
        require(path.is_relative_to(profile.ROOT/'workspace/private') and path.resolve(strict=True)==path and
            stat.S_ISREG(st.st_mode) and st.st_nlink==1 and
            (st.st_dev,st.st_ino,st.st_mode,st.st_size,st.st_mtime_ns,st.st_ctime_ns)==
            tuple(item[k] for k in ('device','inode','mode','size','mtime_ns','ctime_ns')),
            'retained VM copy is no longer the same regular file')
    copy=read(verify(value['copy_command']));replay=read(verify(value['replay_command']));reader=read(verify(value['read_command']))
    for command in (copy,replay,reader):verify(command['tool'],maximum=32*1024**2)
    destination=value['copy_after']['path']
    require(copy['argv']==[copy['tool']['path'],'--reflink=auto','--sparse=always',
            value['original_native_before']['path'],destination] and
        replay['argv']==[replay['tool']['path'],'-p','-E','journal_only',destination] and
        replay['copy_before']==value['copy_before'] and replay['device_actions']==0 and
        reader['argv']==[reader['tool']['path'],'-R','cat /var/lib/lab/s22-evidence-'+row['local']['early']['run_id_hex'],destination] and
        reader['copy_after']==value['copy_after'] and reader['device_actions']==0,
        'VM copy replay or bounded read command differs')
    for label in ('copy_capture','replay_capture'):
        raw.require_success(raw.load_handle(verify(value[label])))
    capture=raw.load_handle(verify(value['runtime_capture']))
    require(capture.returncode==0 and not capture.timed_out and not capture.output_exceeded and
        capture.producer_error_type is None and raw.read_stdout(capture,maximum=16384)==parts[1] and
        raw.read_stderr(capture,maximum=4096)==b'debugfs 1.47.2 (1-Jan-2025)\n','VM recovered record capture differs')
    original=verify(value['original_runtime'],maximum=16384).read_bytes()
    require(len(original)<len(parts[1]) and parts[1].startswith(original),
        'journal replay does not extend the original authenticated prefix')
    verify(value['original_failure'],maximum=65536);verify(value['source'])


def producer(built,*,virtual):
    transition,rcs,watchdog=profile.variants(built)
    phase=profile.phase_selected(built)
    single_cpu=profile.singlecpu_selected(built)
    post_p447=profile.post_p447_selected(built)
    script_channel=profile.script_channel_selected(built)
    minimal=profile.minimal_selected(built)
    reboot=profile.reboot_selected(built)
    cron=profile.cron_selected(built)
    namespace=profile.cron_variant(cron).NAMESPACE if cron else profile.reboot_spec.NAMESPACE if reboot else profile.MINIMAL_NAMESPACE if minimal else profile.SCRIPT_NAMESPACE if script_channel else profile.SINGLECPU_P447_NAMESPACE if post_p447 else profile.SINGLECPU_NAMESPACE if single_cpu else profile.PHASE_NAMESPACE if phase else profile.WATCHDOG_NAMESPACE if watchdog else profile.RCS_NAMESPACE if rcs else profile.TRANSITION_NAMESPACE if transition else profile.NAMESPACE
    version=profile.cron_variant(cron).VERSION if cron else profile.reboot_spec.VERSION if reboot else profile.MINIMAL_VERSION if minimal else profile.SCRIPT_VERSION if script_channel else profile.SINGLECPU_P447_VERSION if post_p447 else profile.SINGLECPU_VERSION if single_cpu else profile.PHASE_VERSION if phase else profile.WATCHDOG_VERSION if watchdog else profile.RCS_VERSION if rcs else profile.TRANSITION_VERSION if transition else profile.VERSION
    require(built['profile']==profile.PROFILE and built['namespace']==namespace and
        built['version']==version and built['virtual'] is virtual and
        built['device_actions']==0 and built['active'] is False and built['deadline_ms']==300000 and
        built['observer_revision']==(6 if single_cpu else 5) and built['trace_maximum']==protocol.TRACE_MAXIMUM and
        'development_derivative' not in built,'automatic producer scope differs')
    require(re.fullmatch('[0-9a-f]{32}',built['run_id']) and
        len(verify(built['key'],maximum=32).read_bytes())==32,'automatic run/key identity differs')
    require(built['history']==profile.history(),'automatic historical input differs')
    if transition:
        require(built['transition_observer']==profile.observer(rcs,watchdog,phase,single_cpu,post_p447,script_channel,minimal,reboot,cron) and
            built['additional_history']==profile.additional_history(),'transition admission/observation differs')
    else:require('additional_history' not in built,'legacy producer cannot adopt new history')
    if rcs:require(built['runtime_history']==profile.runtime_history(),'rcS runtime history differs')
    else:require('runtime_history' not in built,'legacy producer cannot adopt runtime history')
    if watchdog:
        require(built['watchdog_history']==profile.watchdog_history() and
            built['idle_policy'] in profile.IDLE_POLICIES,'watchdog history or idle policy differs')
    else:require('watchdog_history' not in built and 'idle_policy' not in built,
        'legacy producer cannot adopt watchdog history or idle policy')
    if phase:
        require(built['phase_history']==profile.phase_history() and
            built['phase_declaration']==profile.phase_spec.declaration(),
            'phase history or exact observation declaration differs')
        require(verify(built['headers']['installed/s22plus_autoboot_phase_seal_v1.h']).read_bytes()==
            profile.phase_spec.header(virt=virtual),'phase generated seal differs')
        require(built.get('phase_vm_timing')==(profile.phase_spec.VM_TIMING if virtual else None),
            'phase virtual timing adapter differs')
        require([row['sha256'] for row in built['modules'] if row['runtime_name']=='qcom_wdt_core']==
            [profile.phase_spec.MODULE_SHA],'phase callsites do not match the selected module')
    else:require('phase_history' not in built and 'phase_declaration' not in built and 'phase_vm_timing' not in built,
        'legacy producer cannot adopt phase history or observation')
    if script_channel:
        require(built['script_declaration']==profile.script_spec(minimal).script_declaration() and
            verify(built['headers']['installed/s22plus_autoboot_script_seal_v1.h']).read_bytes()==
            profile.script_spec(minimal).script_header(),'script channel generated declaration differs')
    else:require('script_declaration' not in built,'unselected script channel declaration')
    if single_cpu:require(built['current_history']==profile.singlecpu_history(post_p447,script_channel,minimal,reboot,cron),'single CPU authenticated history differs')
    else:require('current_history' not in built,'legacy producer cannot adopt single CPU history')
    if 'transition_fault' in built:
        require(virtual and transition and built['transition_fault'] in profile.TRANSITION_CASES+(profile.RCS_CASES if rcs else ())+
                (profile.SINGLECPU_FAULTS if single_cpu else ())+(profile.SCRIPT_FAULTS if script_channel else ())+(profile.minimal_spec.FAULTS if minimal else ())+(profile.reboot_spec.FAULTS if reboot else ())+ (tuple(profile.cron_variant(cron).RUNTIME_FAULTS) if cron else ()),
            'physical producer includes a test fault')
        for row in built['transition_fault_sources']:verify(row)
    else:require('transition_fault_sources' not in built,'unselected transition fault sources')
    table,count,boot_count=profile.retained_comparison(transition,rcs,watchdog,phase,single_cpu,post_p447,script_channel,minimal,reboot,cron)
    require(verify(built['table']).read_bytes()==table and built['admission']['table']==built['table'] and
        built['admission']['table_count']==count and built['admission']['boot_count']==boot_count,
        'automatic immutable table differs')
    for name in ('helper','writer','entry','hook','witness','busybox','checker'):
        verify(built[name],maximum=8*1024**2)
    for value in built['headers'].values():verify(value)
    verify(built['startup_script'])
    require(built['busybox']['sha256']==profile.handoff.switch.BUSYBOX_SHA256 and built['busybox']['size']==1975064 and
        built['checker']['sha256']==profile.handoff.staged.execution_binding()['checker']['sha256'],
        'automatic fixed tools differ')
    require(built['measured']['helper_sha256']==built['helper']['sha256'] and
        set(built['measured'])=={'shell_sha256','init_sha256','helper_sha256'},'automatic measurements differ')
    init,assets=profile.payloads(built['run_id'],virt=virtual,single_cpu=single_cpu,minimal=minimal,reboot=reboot,cron=cron)
    require(built['installed_init']==dict(size=len(init),sha256=hashlib.sha256(init).hexdigest()) and
        set(built['assets'])==set(assets)|{'hook'} and built['assets']['hook']==built['hook'],
        'automatic installed init/assets differ')
    for name,data in assets.items():
        require(verify(built['assets'][name]).read_bytes()==data,'automatic RAM overlay differs')
    if reboot:
        require(built['reboot_baseline']==baseline.binding(built['reboot_baseline']['receipt']) and
            built['reboot']==profile.reboot_spec.declaration(built['run_id'],built['reboot_baseline']['initial_mount_count']),
            'reboot sealed baseline or declaration differs')
        require(verify(built['headers']['early/s22plus_debian_reboot_seal_v1.h']).read_bytes()==
            profile.reboot_spec.seal(built['run_id'],built['reboot_baseline']['initial_mount_count']),
            'reboot generated seal differs')
    else:require('reboot' not in built and 'reboot_baseline' not in built,'unselected reboot declaration')
    if cron:
        require(built.get('cron')==profile.cron_variant(cron).declaration(built['run_id']) and
            built['reboot']['initial_mount_count']==profile.cron_variant(cron).EXPECTED_MOUNT_COUNT and
            verify(built['headers']['early/s22plus_debian_cron_seal_v1.h']).read_bytes()==profile.cron_variant(cron).seal(built['run_id']),
            'cron declaration or generated seal differs')
    else:require('cron' not in built,'unselected cron declaration')
    if profile.download_selected(built):
        require(built.get('download_return')==profile.download_spec.return_declaration() and
            verify(built['headers']['installed/s22plus_debian_download_seal_v1.h']).read_bytes()==profile.download_spec.return_header(),
            'Download return declaration or seal differs')
    else:require('download_return' not in built,'unselected Download return')
    if reboot and 'initramfs' in built:template_binding(built)
    return built


def vm_results(tested,built,key):
    if profile.reboot_selected(built):
        from s22plus_debian_reboot_qualification_v1 import vm_results as reboot_vm_results
        return reboot_vm_results(tested,built,key)
    transition,rcs,watchdog=profile.variants(built)
    phase=profile.phase_selected(built)
    single_cpu=profile.singlecpu_selected(built)
    post_p447=profile.post_p447_selected(built)
    script_channel=profile.script_channel_selected(built)
    minimal=profile.minimal_selected(built)
    require(tested['status']=='PASS' and tested['device_actions']==0 and
        tuple(row['case'] for row in tested['cases'])==profile.cases(transition,rcs,watchdog,phase,single_cpu,post_p447,script_channel,minimal),'automatic VM corpus differs')
    sources={r['path']:r['sha256'] for r in built['source_inputs']}
    require(len(sources)==len(built['source_inputs']) and
        sources=={r['path']:r['sha256'] for r in tested['source_inputs']},'automatic VM source closure differs')
    for row in tested['cases']:
        require(row['status']=='PASS' and row['device_actions']==0 and row['outside_native_unchanged'] is True and
            row['host_start_requests']==0 and
            row['scope']=='REAL_DEBIAN_AUTOBOOT_WITH_SAMSUNG_HARDWARE_SUBSTITUTIONS',
            'automatic VM hardware substitutions were promoted')
        if single_cpu:
            require(row['single_cpu_vm']==dict(exposed_cpus=8,watchdog_sysfs='MODEL_ONLY',
                cpu_online='REAL_KERNEL_SYSFS',hardware_pet_proved=False),'single CPU VM substitution scope differs')
        helper=producer(read(verify(row['virtual_helper'])),virtual=True)
        require(profile.variants(helper)==(transition,rcs,watchdog) and
            profile.phase_selected(helper)==phase and
            profile.singlecpu_selected(helper)==single_cpu and
            profile.post_p447_selected(helper)==post_p447 and
            profile.script_channel_selected(helper)==script_channel and
            profile.minimal_selected(helper)==minimal and
            helper.get('idle_policy')==built.get('idle_policy') and
            helper['source_inputs']==built['source_inputs'] and helper['run_id']==built['run_id'] and
            helper['modules']==built['modules'] and helper['history']==built['history'] and
            helper['startup_script']['sha256']==built['startup_script']['sha256'] and
            helper['measured']['shell_sha256']==built['measured']['shell_sha256'] and
            helper['measured']['init_sha256']==built['measured']['init_sha256'] and
            verify(helper['key']).read_bytes()==key,'automatic VM producer does not join physical sources')
        setup=read(verify(row['setup']))
        require(setup['helper']==row['virtual_helper'] and setup['build']==row['build'] and
            setup['case']==row['case'] and setup['device_actions']==0,'automatic VM setup differs')
        verify(setup['initramfs'],maximum=32*1024**2)
        source=verify(setup['source'])
        require(sources[str(source.relative_to(profile.ROOT))]==setup['source']['sha256'],
            'VM harness does not join its frozen source')
        verify(row['serial'],maximum=4*1024**2)
        if 'transition_observer' in built:
            from s22plus_debian_autoboot_transition_v1 import retained,sources as transition_sources,qualify_case
            projected=retained(verify(row['serial'],maximum=4*1024**2).read_bytes(),key=key,
                run=bytes.fromhex(built['run_id']),expected=transition_sources(helper),phase=phase,script_channel=script_channel,minimal=minimal,
                phase_window_ms=helper.get('phase_vm_timing',{}).get('absolute_window_ms',15000))
            require(projected==row['transition'],'actual VM transition projection differs')
            qualify_case(projected,row['case'])
            require(helper.get('transition_fault')==(row['case'] if row['case'] in profile.TRANSITION_CASES+profile.RCS_CASES+profile.SINGLECPU_FAULTS+profile.SCRIPT_FAULTS+profile.minimal_spec.FAULTS else None),
                'VM fault producer selection differs')
        if row['case'] in ('normal','trace-logger-loss')+profile.SCRIPT_FAULTS:
            capture=raw.load_handle(verify(row['proof_capture']));raw.require_success(capture)
            require(not raw.read_stderr(capture,maximum=16384),'automatic VM evidence has SSH diagnostics')
            proof,_=protocol.envelope(raw.read_stdout(capture,maximum=protocol.MAXIMUM),key=key,selected=helper)
            plan=access.inputs(built['run_id']);plan['candidate']=dict(namespace=built['namespace'],
                version=built['version'],run_id=built['run_id'])
            require(proof==row['proof'] and row['local'] is None and row['forced_host_stop'] is False and
                access.health_projection(raw.load_handle(verify(row['ssh_health']['capture'])),plan,
                    boot_sha256=proof['kernel_boot_identity_sha256'],autoboot=True)==row['ssh_health'] and
                access.shutdown_projection(raw.load_handle(verify(row['shutdown']['dispatch_capture'])),
                    plan['link']['ssh_address'])==row['shutdown'] and
                row['filesystem']['clean_ext4'] is True and row['filesystem']['home_view_readable'] is True and
                row['filesystem']['boot_count_durability']=='CONTROLLED_SHUTDOWN_VERIFIED' and
                row['disk_before']!=row['disk_after'],'automatic complete VM lifecycle differs')
            if single_cpu:
                from s22plus_debian_autoboot_access_v1 import singlecpu_health_pair
                pair=row['ssh_120_seconds']
                require(pair==singlecpu_health_pair(raw.load_handle(verify(pair['first']['health']['capture'])),
                    raw.load_handle(verify(row['ssh_health']['capture'])),plan,
                    proof['kernel_boot_identity_sha256']),'VM SSH interval does not rederive')
        elif row['case']=='network-absent':
            require(row['forced_host_stop'] is True and row['ssh_health'] is None and row['shutdown'] is None and
                row['filesystem'] is None and row['proof'] is None and row['proof_capture'] is None,
                'network-absent VM claims live access or clean shutdown')
            parts=[verify(row['local_files'][name],maximum=16384).read_bytes() for name in ('early','runtime')]
            if row.get('local_retrieval') is not None:copy_readback(row,parts)
            require(protocol.local_records(*parts,key=key,selected=helper,root_device=dict(major=259,minor=25))==row['local']
                and row['disk_before']!=row['disk_after'],'network absence lost its authenticated local lifecycle')
        else:
            require(row['proof'] is None and row['local'] is None and row['proof_capture'] is None and
                row['ssh_health'] is None and row['shutdown'] is None and row['filesystem'] is None and
                row['forced_host_stop'] is (row['case'] in ('trace-pending','rcs-pending-record','rcs-pending-child')),
                'automatic negative advanced to service or external proof')
            if row['case'] in profile.RCS_CASES+profile.minimal_spec.FAULTS:
                require(rcs and row['runtime_absent'] is False and
                    row['runtime_observation']=='NOT_ACQUIRED_AFTER_RCS_FAULT' and
                    row['disk_before']!=row['disk_after'],'rcS fault was promoted to a pre-write stop or storage read')
            elif row['case'] in ('changed-receipt','fd-leak','module-error','singlecpu-disabled') or row['case'].startswith('trace-'):
                require(row['runtime_absent'] is True,'failed automatic entry ran installed services')
            else:require(row['disk_before']==row['disk_after'],'pre-admission rejection changed storage')
    return tested


def image_binding(image):
    require(set(image)=={'schema','namespace','version','run_id_hex','profile','ap','member','key','runtime_sources',
        'autoboot_boot','gpt','android_return','qualification'} and image['schema']=='s22plus-native-image-v3' and
        image['profile']==profile.PROFILE,'automatic image schema differs')
    qualified=read(verify(image['qualification']));artifact=read(verify(image['autoboot_boot']))
    require(set(qualified)=={'schema','status','image','vm','device_actions'} and
        qualified['schema']==profile.SCHEMA+'-qualification' and qualified['status']=='PASS_H0_ARTIFACT_AND_VM' and
        qualified['image']=={k:v for k,v in image.items() if k!='qualification'} and qualified['device_actions']==0,
        'automatic qualification binding differs')
    require(set(artifact)=={'schema','namespace','version','run_id','ap','member','key','build','expected','runtime_sources',
        'module_names','ab_identical','active','boot','ramdisk_sha256','inventory','vm','device_actions'} and
        artifact['schema']==profile.SCHEMA+'-artifact' and artifact['ab_identical'] is True and
        artifact['active'] is False and artifact['device_actions']==0 and artifact['vm']==qualified['vm'],
        'automatic artifact scope differs')
    for a,b in (('namespace','namespace'),('version','version'),('run_id','run_id_hex'),('ap','ap'),('member','member'),
                ('key','key'),('runtime_sources','runtime_sources')):
        require(artifact[a]==image[b],'automatic artifact/image join differs')
    built=producer(read(verify(artifact['build'])),virtual=False)
    if profile.reboot_selected(built):baseline.binding(built['reboot_baseline']['receipt'],physical=True)
    require(built['schema']=='s22plus-debian-autoboot-h0-v1' and built['status']=='H0_INITRAMFS_BUILT' and
        built['ab_identical'] is True and built['run_id']==image['run_id_hex'] and
        built['namespace']==image['namespace'] and built['version']==image['version'] and
        built['key']==image['key'] and built['measured']==artifact['expected'],'automatic physical producer differs')
    from s22plus_debian_file_first_plan_v1 import modules
    inventory=read(verify(artifact['inventory']));expected=modules(inventory,early.LOGGER)
    require(inventory['platform_count']==73 and len(expected)==82 and built['modules']==expected and
        artifact['module_names']==[m['runtime_name'] for m in expected],'automatic module order differs')
    require({r['path']:r['sha256'] for r in built['source_inputs']}==
        {k:v['sha256'] for k,v in image['runtime_sources'].items()},'automatic runtime source closure differs')
    verify(built['initramfs'],maximum=32*1024**2)
    tested=read(verify(artifact['vm']))
    require(tested['build_sha256']==artifact['build']['sha256'] and
        all(row['build']==artifact['build'] for row in tested['cases']),'automatic VM selected another build')
    vm_results(tested,built,verify(image['key'],maximum=32).read_bytes())
    return artifact


def payload_binding(built):
    """Bind actual archive members to qualified executables and measurements."""
    source=verify(built['initramfs'],maximum=32*1024**2)
    with gzip.GzipFile(fileobj=io.BytesIO(source.read_bytes())) as stream:
        data=stream.read(128*1024**2+1)
    require(len(data)<=128*1024**2 and data[:6]==b'070701','automatic CPIO is oversized or unselected')
    fields=[int(data[6+i*8:14+i*8],16) for i in range(13)];end=(110+fields[11]+3)&~3
    require(data[110:110+fields[11]]==b'.\0' and fields[6]==0 and
        stat.S_ISDIR(fields[1]) and fields[2:4]==[0,0] and not any(data[112:end]),
        'automatic leading CPIO root differs')
    rows=archive.transport.boot_verify.parse_newc(data[end:]);entries={e.name:e for e in rows}
    require(len(entries)==len(rows),'automatic CPIO has duplicate paths')
    expected=profile.ramdisk_payloads(built)
    expected['scripts/fyg8-dev']=built['startup_script']
    for name,target in (('bin',b'usr/bin'),('sbin',b'usr/sbin')):
        item=entries[name]
        require((item.mode,item.uid,item.gid,item.nlink)==(stat.S_IFLNK|0o777,0,0,1) and item.data==target,
            'automatic executable path alias differs')
    required=set(expected)|{'init','usr/bin/sh'}|{'lab/modules/'+row['name'] for row in built['modules']}
    parents={str(parent) for name in required for parent in PurePosixPath(name).parents if str(parent)!='.'}
    require(all(entries[name].file_type=='directory' and entries[name].uid==entries[name].gid==0 for name in parents),
        'automatic payload ancestor is not a root-owned directory')
    for name,pinned in expected.items():
        item=entries[name]
        mode=0o755 if name=='scripts/fyg8-dev' else 0o400 if name in (
            's22-root-inspect.table','s22-debian-inittab','s22-debian-crontab') or name.endswith('.ko') else 0o500
        require(item.file_type=='regular' and (item.uid,item.gid,item.nlink,item.mode&0o7777)==(0,0,1,mode) and
            item.data==verify(pinned,maximum=8*1024**2).read_bytes(),'automatic CPIO payload differs: '+name)
    require(entries['init'].file_type=='regular' and
        (entries['init'].mode,entries['init'].uid,entries['init'].gid,entries['init'].nlink)==(stat.S_IFREG|0o755,0,0,1) and
        hashlib.sha256(entries['init'].data).hexdigest()==built['measured']['init_sha256'],
        'automatic actual initial PID1 differs')
    shell=entries['usr/bin/sh'];group=[e for e in rows if e.inode==shell.inode]
    bodies=[e.data for e in group if e.data]
    require(group and all((e.mode,e.uid,e.gid,e.nlink)==(stat.S_IFREG|0o755,0,0,len(group)) for e in group) and len(bodies)==1 and
        hashlib.sha256(bodies[0]).hexdigest()==built['measured']['shell_sha256'],'automatic actual shell differs')
    require({name for name in entries if name.startswith('lab/modules/')}==
        {'lab/modules/'+row['name'] for row in built['modules']},'automatic CPIO module set differs')
    for row in built['modules']:
        item=entries['lab/modules/'+row['name']]
        require(item.file_type=='regular' and (item.uid,item.gid,item.nlink,item.mode&0o7777)==(0,0,1,0o400) and
            len(item.data)==row['size'] and hashlib.sha256(item.data).hexdigest()==row['sha256'],
            'automatic CPIO module bytes differ')
    return True


def archive_binding(image,artifact):
    archive.archive_binding(image,artifact)
    payload_binding(read(verify(artifact['build'])))


def template_binding(built):
    """Re-derive every repacked member, including undeclared base contents."""
    receipt=read(verify(profile.reboot_spec.P457_RETRIEVAL))['writer_build']
    original=read(verify(receipt))
    require(original['namespace']==profile.MINIMAL_NAMESPACE and original['version']==profile.MINIMAL_VERSION and
        original['transition_observer']==profile.MINIMAL_OBSERVER and original['virtual'] is False and
        original['ab_identical'] is True and original['modules']==built['modules'] and
        all(original['measured'][name]==built['measured'][name] for name in ('init_sha256','shell_sha256')),
        'automatic template identity differs')
    def decode(source):
        with gzip.GzipFile(fileobj=io.BytesIO(verify(source,maximum=32*1024**2).read_bytes())) as stream:
            data=stream.read(128*1024**2+1)
        require(len(data)<=128*1024**2 and data[:6]==b'070701','template CPIO bound differs')
        fields=[int(data[6+i*8:14+i*8],16) for i in range(13)];end=(110+fields[11]+3)&~3
        require(data[110:110+fields[11]]==b'.\0' and fields[6]==0 and stat.S_ISDIR(fields[1]) and
            fields[2:4]==[0,0] and not any(data[112:end]),'template leading root differs')
        position=end
        while position<len(data) and any(data[position:position+110]):
            require(data[position:position+6]==b'070701','template member header differs')
            values=[int(data[position+6+i*8:position+14+i*8],16) for i in range(13)]
            require(values[7:11]==[0,0,0,0] and values[12]==0 and values[11]>0,
                'template archive device or checksum fields differ')
            name=data[position+110:position+110+values[11]]
            start=(position+110+values[11]+3)&~3;position=(start+values[6]+3)&~3
            require(position<=len(data),'template member exceeds archive')
            if name==b'TRAILER!!!\0':break
        rows=archive.transport.boot_verify.parse_newc(data[end:])
        require(len({e.name for e in rows})==len(rows),'template duplicate members')
        return data[:end],rows
    root,old=decode(original['initramfs']);new_root,new=decode(built['initramfs'])
    expected=profile.ramdisk_payloads(built);expected['scripts/fyg8-dev']=built['startup_script']
    additions=profile.download_spec.ramdisk_additions(built)
    extra=profile.download_spec.repack_entries(old,additions,
        {name:verify(expected[name],maximum=8*1024**2).read_bytes() for name in additions})
    require(root==new_root and len(old)+len(extra)==len(new) and
        set(expected)-set(additions)<={e.name for e in old} and not set(additions)&{e.name for e in old} and
        list(new[len(old):])==extra,
        'repack root, member count or vocabulary differs')
    construction=dict(method='EXACT_MEASURED_TEMPLATE_REPACK',template_build=receipt,
        template=original['initramfs'],replaced=sorted(set(expected)-set(additions)),
        unmodified_members=len(old)-len(expected)+len(additions),package_installation=False)
    if additions:construction['added']=additions
    require(built['construction']==construction,'repack construction receipt differs')
    for first,second in zip(old,new):
        body=verify(expected[first.name],maximum=8*1024**2).read_bytes() if first.name in expected else first.data
        require(replace(second,data=first.data)==first and second.data==body,
            'repack changed an undeclared member or metadata')
    return True

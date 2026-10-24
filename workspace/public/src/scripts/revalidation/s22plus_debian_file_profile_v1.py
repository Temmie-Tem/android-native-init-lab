"""One USB-independent early file pilot, followed by physical original A."""
import re
from pathlib import Path
from s22plus_native_records_v3 import read,read_bytes,require,verify

PROFILE='debian-file-pilot-v1'
SCHEMA='s22plus-debian-file-pilot-v1'
POLICY='docs/operations/S22PLUS_DEBIAN_FILE_PILOT_V1.md'
WINDOW_SECONDS=360
TRANSFER_SECONDS=240
RETURN_SECONDS=600
PENDING='AWAITING_OFFLINE_FILE_RECORD'
CASES=('normal','dirty','wrong-uuid','existing-record','insert-error','ram-log-missing',
    'short-write','file-sync-error','parent-sync-error','unmount-error','late-ro-clear','checker-timeout')
PARTIAL_WRITES=('short-write','file-sync-error','parent-sync-error','unmount-error')


def before_transfer(grant,now,*,boots=1):
    require(type(boots) is int and boots in (1,2),'unselected boot window count')
    require(type(now) is int and now>=grant['opened_ns'] and
        grant['deadline_ns']-now>(TRANSFER_SECONDS+boots*WINDOW_SECONDS+RETURN_SECONDS)*1_000_000_000,
        'file pilot lacks remaining transfer, window and physical-return budget')


def validate_adoption(root,details):
    name=Path(POLICY).name.encode()
    require(name in details and name in read_bytes(Path(root)/'docs/operations/targets/S22PLUS_FYG8_TARGET_CONTRACT.md') and
        b'Status: **REVIEW_GATED_CAPABILITY**' in read_bytes(Path(root)/POLICY),
        'file pilot lacks common/target adoption')


def vm_results(tested,built,*,storage_first=False):
    if storage_first:
        import s22plus_debian_file_first_profile_v1 as first
        sources={r['path']:r['sha256'] for r in tested['source_inputs']}
        for row in tested['cases']:first.virtual_artifact(row,built,sources)
    cases=first.CASES if storage_first else CASES
    partial=first.PARTIAL_WRITES if storage_first else PARTIAL_WRITES
    require(tested['status']=='PASS' and tested['device_actions']==0 and
        [row['case'] for row in tested['cases']]==list(cases),'file VM suite differs')
    for row in tested['cases']:
        require(row['status']=='PASS' and row['device_actions']==0 and row['run_id']==built['run_id'] and
            row['outside_before']==row['outside_after'] and
            all(row['expected'][key]==built['measured'][key] for key in ('shell_sha256','init_sha256')),
            'file VM identity or partition confinement differs')
        if row['case']=='normal':
            proof=row['proof']['proof'];reader=read(verify(row['proof']['retrieval']))
            require(proof['pre_unmount_complete'] is True and proof['debian_early_pid1'] is True and
                proof['run_id_hex']==built['run_id'] and proof['live_usb_proved'] is False and
                proof['unmount_return_proved'] is False and reader['disk_unchanged'] is True and
                reader['proof']['source_view_clean'] is True and reader['proof']['mounted'] is False,
                'actual writer/later reader qualification absent')
            from s22plus_debian_file_protocol_v1 import decode
            data=bytes.fromhex(reader['proof']['files'][-1]['raw_hex'])
            require(decode(data,key=verify(built['key'],maximum=32).read_bytes(),run=bytes.fromhex(built['run_id']),
                expected=row['expected'],module_names=[m['runtime_name'] for m in built['modules']],storage_first=storage_first)==proof,
                'recovered VM file does not rederive')
        elif storage_first and row['case']=='module-error':
            proof=row['proof']['proof'];reader=read(verify(row['proof']['retrieval']))
            from s22plus_debian_file_first_protocol_v1 import decode
            require(proof==decode(bytes.fromhex(reader['proof']['files'][-1]['raw_hex']),
                key=verify(built['key'],maximum=32).read_bytes(),run=bytes.fromhex(built['run_id']),
                expected=row['expected'],module_names=[m['runtime_name'] for m in built['modules']],allow_prefix=True) and
                proof['client_return_records']==2 and proof['client_error']==dict(name='i2c_msm_geni',error=5) and
                not proof['pre_unmount_complete'],'module error lost its exact persisted boundary')
        elif row['case'] in partial:
            require(row['proof']['status']=='PASS_CONSUMED_IO_FAILURE' and
                row['proof']['unmount_proved'] is False and row['proof']['retrieval'] is not None,
                'file I/O fault was relabelled successful')
        else:require(row['disk_before']==row['disk_after'] and
            row['proof']['status']=='PASS_REJECTED_WITHOUT_DISK_CHANGE','negative file pilot changed disk')


def image_binding(image,*,storage_first=False,diagnostic=False):
    selected=PROFILE;schema=SCHEMA
    if storage_first:
        import s22plus_debian_file_first_profile_v1 as first
        from s22plus_debian_early_profile_v1 import LOGGER
        if diagnostic:
            import s22plus_debian_failure_profile_v1 as first
        selected=first.PROFILE;schema=first.SCHEMA
    keys={'schema','namespace','run_id_hex','profile','version','ap','member','key','qualification',
        'runtime_sources','early_boot','gpt','android_return'}
    require(set(image)==keys and image['schema']=='s22plus-native-image-v3' and image['profile']==selected and
        re.fullmatch(r'p[0-9]{3,6}',image['namespace']) and re.fullmatch('[0-9a-f]{32}',image['run_id_hex']),
        'file image identity differs')
    require(verify(image['key'],maximum=32).stat().st_size==32,'file key width differs')
    qualified=read(verify(image['qualification']));artifact=read(verify(image['early_boot']))
    require(set(qualified)=={'schema','status','image','vm','device_actions'} and
        qualified['schema']==schema+'-qualification' and qualified['status']=='PASS_H0_ARTIFACT_AND_VM' and
        qualified['image']=={k:v for k,v in image.items() if k!='qualification'} and qualified['device_actions']==0,
        'file qualification differs')
    require(set(artifact)=={'schema','namespace','version','run_id','ap','member','key','build','expected','runtime_sources',
        'module_names','ab_identical','active','boot','ramdisk_sha256','inventory','vm','device_actions'} and
        artifact['schema']==schema+'-artifact' and artifact['ab_identical'] is True and artifact['active'] is False and
        artifact['device_actions']==0 and artifact['vm']==qualified['vm'] and
        artifact['namespace']==image['namespace'] and artifact['run_id']==image['run_id_hex'] and
        all(artifact[key]==image[key] for key in ('version','ap','member','runtime_sources','key')),
        'file artifact does not join image')
    built=read(verify(artifact['build']));inventory=read(verify(artifact['inventory']))
    expected=first.plan.modules(inventory,LOGGER) if storage_first else inventory['modules']
    require(built['schema']==('s22plus-debian-failure-observer-h0-v1' if diagnostic else 's22plus-debian-file-first-h0-v1' if storage_first else 's22plus-debian-file-pilot-h0-v1') and built['virtual'] is False and built['fault'] is None and
        built['profile']==selected and built['namespace']==image['namespace'] and built['version']==image['version'] and
        built['run_id']==image['run_id_hex'] and built['measured']==artifact['expected'] and
        built['ab_identical'] is True and built['active'] is False and built['device_actions']==0 and
        inventory['platform_count']==73 and len(inventory['modules'])==81 and built['modules']==expected and
        artifact['module_names']==[m['runtime_name'] for m in expected] and
        set(built['measured'])=={'shell_sha256','init_sha256','helper_sha256'} and
        built['helper']['sha256']==built['measured']['helper_sha256'] and
        {r['path']:r['sha256'] for r in built['source_inputs']}==
        {key:row['sha256'] for key,row in image['runtime_sources'].items()},'file build source/module binding differs')
    if diagnostic:require(built.get('diagnostic') is True and built.get('diagnostic_fault') is None,'physical observer fault flag differs')
    for field in ('helper','writer'):verify(built[field],maximum=4*1024**2)
    for receipt in built['headers'].values():verify(receipt)
    for field in ('checker','table'):verify(built['admission'][field])
    verify(built['initramfs'],maximum=16*1024**2)
    tested=read(verify(artifact['vm']))
    require(tested['build_sha256']==artifact['build']['sha256'],'file VM tested another build')
    if diagnostic:first.vm_results(tested,dict(built,key=image['key']))
    else:vm_results(tested,dict(built,key=image['key']),storage_first=storage_first)
    return artifact

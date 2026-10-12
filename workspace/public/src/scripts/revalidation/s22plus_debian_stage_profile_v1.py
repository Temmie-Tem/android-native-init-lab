"""One logger-only Debian stage probe; offline evidence, physical A return."""
from pathlib import Path
import re

from s22plus_native_records_v3 import read,read_bytes,require,verify

PROFILE='debian-stage-probe-v1'
SCHEMA='s22plus-debian-stage-probe-v1'
POLICY='docs/operations/S22PLUS_DEBIAN_STAGE_PROBE_V1.md'
WINDOW_SECONDS=90
TRANSFER_SECONDS=240
RETURN_SECONDS=600
PENDING='AWAITING_RETAINED_STAGE_RECORDS'
CASES=('normal','bad-parent','insert-error','binding-missing','logger-off','late')


def before_transfer(grant,now):
    require(type(now) is int and now>=grant['opened_ns'] and
        grant['deadline_ns']-now>(TRANSFER_SECONDS+WINDOW_SECONDS+RETURN_SECONDS)*1_000_000_000,
        'stage probe lacks remaining transfer, window and physical-return budget')


def validate_adoption(root,details):
    name=Path(POLICY).name.encode()
    require(name in details and name in read_bytes(Path(root)/'docs/operations/targets/S22PLUS_FYG8_TARGET_CONTRACT.md') and
        b'Status: **REVIEW_GATED_CAPABILITY**' in read_bytes(Path(root)/POLICY),
        'stage probe lacks common/target adoption')


def vm_results(tested,built):
    from s22plus_debian_stage_protocol_v1 import retained
    from s22plus_debian_early_profile_v1 import LOGGER
    require(tested['status']=='PASS' and tested['device_actions']==0 and
        [r['case'] for r in tested['cases']]==list(CASES),'stage VM suite differs')
    for row in tested['cases']:
        require(row['status']=='PASS' and row['device_actions']==0 and row['run_id']==built['run_id'] and
            row['disk_before']==row['disk_after'] and
            all(row['expected'][k]==built['measured'][k] for k in ('shell_sha256','init_sha256')),
            'stage VM binding or disk changed')
        proof=retained(verify(row['capture'],maximum=4*1024**2).read_bytes(),
            key=verify(built['key'],maximum=32).read_bytes(),run=bytes.fromhex(built['run_id']),
            expected=row['expected'],logger_sha256=LOGGER['sha256'])
        require(proof==row['proof'],'stage VM raw producer/consumer result differs')
        expected_status='PASS_RETAINED_EARLY_STAGE' if row['case']=='normal' else (
            'NO_AUTHENTICATED_STAGE' if row['case'] in ('logger-off','late') else 'RETAINED_STAGE_REJECTED')
        require(proof['status']==expected_status and
            row['insertions']==(1 if row['case'] in ('normal','insert-error','binding-missing') else 0),
            'stage VM outcome or one-shot insertion differs')


def image_binding(image):
    from s22plus_debian_early_profile_v1 import LOGGER
    keys={'schema','namespace','run_id_hex','profile','version','ap','member','key','qualification',
        'runtime_sources','early_boot','gpt','android_return'}
    require(set(image)==keys and image['schema']=='s22plus-native-image-v3' and image['profile']==PROFILE and
        re.fullmatch(r'p[0-9]{3,6}',image['namespace']) and re.fullmatch('[0-9a-f]{32}',image['run_id_hex']),
        'stage image identity differs')
    require(verify(image['key'],maximum=32).stat().st_size==32,'stage key width differs')
    qualified=read(verify(image['qualification']));artifact=read(verify(image['early_boot']))
    require(set(qualified)=={'schema','status','image','vm','device_actions'} and
        qualified['schema']==SCHEMA+'-qualification' and qualified['status']=='PASS_H0_ARTIFACT_AND_VM' and
        qualified['image']=={k:v for k,v in image.items() if k!='qualification'} and qualified['device_actions']==0,
        'stage qualification differs')
    require(set(artifact)=={'schema','namespace','version','run_id','ap','member','key','build','expected','runtime_sources',
        'module_names','ab_identical','active','boot','ramdisk_sha256','inventory','vm','device_actions'} and
        artifact['schema']==SCHEMA+'-artifact' and artifact['ab_identical'] is True and artifact['active'] is False and
        artifact['device_actions']==0 and artifact['vm']==qualified['vm'] and
        artifact['namespace']==image['namespace'] and artifact['run_id']==image['run_id_hex'] and
        all(artifact[k]==image[k] for k in ('version','ap','member','runtime_sources','key')),'stage artifact differs')
    built=read(verify(artifact['build']))
    require(built['schema']=='s22plus-debian-stage-probe-h0-v1' and built['virtual'] is False and
        built['profile']==PROFILE and built['namespace']==image['namespace'] and built['version']==image['version'] and
        built['run_id']==image['run_id_hex'] and built['measured']==artifact['expected'] and
        built['ab_identical'] is True and built['active'] is False and built['device_actions']==0 and
        built['modules']==[LOGGER] and artifact['module_names']==['sec_log_buf'] and
        set(built['measured'])=={'shell_sha256','init_sha256','helper_sha256'} and
        built['helper']['sha256']==built['measured']['helper_sha256'] and
        {r['path']:r['sha256'] for r in built['source_inputs']}==
        {k:v['sha256'] for k,v in image['runtime_sources'].items()},'stage physical source/module binding differs')
    verify(built['helper'],maximum=4*1024**2)
    for receipt in built['headers'].values():verify(receipt)
    verify(built['initramfs'],maximum=16*1024**2);verify(artifact['inventory'])
    tested=read(verify(artifact['vm']))
    require(tested['build_sha256']==artifact['build']['sha256'],'stage VM tested another build')
    vm_results(tested,dict(built,key=image['key']))
    return artifact

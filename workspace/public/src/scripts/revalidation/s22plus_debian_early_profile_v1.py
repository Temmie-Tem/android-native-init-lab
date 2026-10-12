"""Debian-owned initial userspace; fixed evidence only, no native admission."""
from pathlib import Path
import re

import s22plus_native_root_inspect_profile_v1 as retained
from s22plus_native_records_v3 import pin,read,require,verify

SCHEMA='s22plus-debian-early-v1'
PROFILE='debian-owned-early-v1'
USB_PROFILE='debian-usb-first-v1'
USB_SCHEMA='s22plus-debian-usb-first-v1'
FILE_PROFILE='debian-file-pilot-v1'
USB_LOGGING_MODES=('retained','ram-only')
PROFILES=(PROFILE,USB_PROFILE,FILE_PROFILE)
OPERATION='debian-early'
SELECTION='debian-early-evidence'
POLICY='docs/operations/S22PLUS_DEBIAN_EARLY_BOOT_V1.md'
prior_inputs=retained.prior_inputs
ROOT=retained.ROOT


class Profile:
    RESULT_KEY='debian_early'
    MUTATES=False  # All automatic preparation is consumed by the N transfer.


def usb_logging_mode(built):
    require(built['profile']==USB_PROFILE,'not a USB-only build')
    # Frozen P418 builds predate this explicit field and always use retention.
    mode=built.get('logging_mode','retained')
    require(mode in USB_LOGGING_MODES,'unknown USB logging mode')
    return mode


def vm_cases(built):
    if built['profile']==FILE_PROFILE:
        from s22plus_debian_file_profile_v1 import CASES
        return list(CASES)
    if built['profile']==USB_PROFILE:
        cases=['normal','bad-auth','logger-off','insert-error']
        if usb_logging_mode(built)=='ram-only':cases.append('ram-log-missing')
        return cases
    require(built['profile']==PROFILE,'unselected early VM profile')
    return ['clean','dirty','bad-auth']


def image_binding(image):
    if image.get('profile')==FILE_PROFILE:
        from s22plus_debian_file_profile_v1 import image_binding as file_binding
        return file_binding(image)
    usb=image.get('profile')==USB_PROFILE
    schema=USB_SCHEMA if usb else SCHEMA
    keys={'schema','namespace','run_id_hex','profile','version','ap','member','key','qualification',
        'runtime_sources','early_boot','gpt','android_return'}
    require(set(image)==keys and image['schema']=='s22plus-native-image-v3' and image['profile'] in PROFILES and
        re.fullmatch(r'p[0-9]{3,6}',image['namespace']) and re.fullmatch('[0-9a-f]{32}',image['run_id_hex']),
        'early image schema/identity differs')
    key=verify(image['key'],maximum=32);require(key.stat().st_size==32,'early key size differs')
    qualified=read(verify(image['qualification']))
    require(set(qualified)=={'schema','status','image','vm','device_actions'} and
        qualified['schema']==schema+'-qualification' and qualified['status']=='PASS_H0_ARTIFACT_AND_VM' and
        qualified['image']=={k:v for k,v in image.items() if k!='qualification'} and
        qualified['device_actions']==0,'early image qualification is absent or differs')
    artifact=read(verify(image['early_boot']))
    require(set(artifact)=={'schema','namespace','version','run_id','ap','member','key','build','expected','runtime_sources',
        'module_names','ab_identical','active','boot','ramdisk_sha256','inventory','vm','device_actions'} and
        artifact['schema']==schema+'-artifact' and artifact['ab_identical'] is True and artifact['active'] is False and
        artifact['device_actions']==0 and artifact['vm']==qualified['vm'] and
        artifact['namespace']==image['namespace'] and artifact['run_id']==image['run_id_hex'] and
        artifact['version']==image['version'] and artifact['ap']==image['ap'] and artifact['member']==image['member'] and
        artifact['runtime_sources']==image['runtime_sources'] and artifact['key']==image['key'],
        'early artifact does not join actual archive/identity')
    built=read(verify(artifact['build']))
    require(built['schema']==('s22plus-debian-usb-first-h0-v1' if usb else 's22plus-debian-early-h0-v1') and built['virtual'] is False and
        built['run_id']==image['run_id_hex'] and built['measured']==artifact['expected'] and built['ab_identical'] is True,
        'early bootstrap/observer producer differs')
    require(built['namespace']==image['namespace'] and built['version']==image['version'] and
        built['profile']==image['profile'] and built['active'] is False and built['device_actions']==0 and
        set(artifact['expected'])=={'shell_sha256','init_sha256','helper_sha256'} and
        all(re.fullmatch('[0-9a-f]{64}',v) for v in artifact['expected'].values()) and
        built['helper']['sha256']==artifact['expected']['helper_sha256'] and
        {r['path']:r['sha256'] for r in built['source_inputs']}==
        {k:v['sha256'] for k,v in image['runtime_sources'].items()},'early source or measurement join differs')
    for field in ('helper','observer'):verify(built[field],maximum=4*1024*1024)
    for value in built['headers'].values():verify(value)
    verify(built['initramfs'],maximum=16*1024*1024)
    inventory=read(verify(artifact['inventory']))
    expected_names=[r['runtime_name'] for r in inventory['modules']]
    if usb:
        require(inventory['platform_count']==73 and len(expected_names)==81,'USB retained platform differs')
        logging_mode=usb_logging_mode(built)
        expected_names=(['sec_log_buf'] if logging_mode=='retained' else [])+expected_names[:73]
        require([m['runtime_name'] for m in built['modules']]==expected_names,'USB built module declaration differs')
    require(len(artifact['module_names'])==len(expected_names) and len(set(artifact['module_names']))==len(artifact['module_names']) and
        artifact['module_names']==expected_names and
        all(re.fullmatch('[A-Za-z0-9_]+',v) for v in artifact['module_names']), 'early module plan differs')
    tested=read(verify(artifact['vm']))
    require(tested['status']=='PASS' and tested['device_actions']==0 and tested['build_sha256']==artifact['build']['sha256'] and
        [r['case'] for r in tested['cases']]==vm_cases(built) and
        all(r['status']=='PASS' and r['device_actions']==0 and r['run_id']==image['run_id_hex'] and
            (not usb or r.get('logging_mode','retained')==usb_logging_mode(built)) and
            r['disk_before']==r['disk_after'] and r['expected']['shell_sha256']==artifact['expected']['shell_sha256'] and
            r['expected']['init_sha256']==artifact['expected']['init_sha256'] for r in tested['cases']),
        'early actual producer/consumer qualification differs')
    return artifact


def wire_protocol(image):
    require(image['profile'] in (PROFILE,USB_PROFILE),'file pilot has no USB protocol')
    if image['profile']==USB_PROFILE:
        import s22plus_debian_usb_protocol_v1 as selected
    else:
        import s22plus_debian_early_protocol_v1 as selected
    return selected

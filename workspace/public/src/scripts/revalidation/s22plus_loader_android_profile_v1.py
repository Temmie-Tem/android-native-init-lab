"""Exact artifact admission for the FYG8 loader-to-Android comparison."""
import hashlib
import hmac
from pathlib import Path
import re
import struct

from s22plus_native_records_v3 import pin,publish,read,require
from s22plus_native_task_v3 import unchanged,android_artifact
import s22plus_boot_only_f1_transport as transport
import s22plus_boot_verify as boot

ROOT=Path(__file__).resolve().parents[5]
PROFILE='loader-android-v1'
OPERATION='loader-android'
SELECTION='loader-android-evidence'
RETURN='loader-android-download'
POLICY='docs/operations/S22PLUS_LOADER_ANDROID_V1.md'
REVIEW='workspace/public/src/device-action/bindings/s22plus_loader_logm_control_v1_review.json'
NAMESPACE='la001'
VERSION='loader-android-1'
SECONDS=1800
OBSERVATION_NS=240_000_000_000
TASK_SCHEMA='s22plus-loader-android-task-v1'
REVIEW_SCHEMA='s22plus-loader-android-review-v1'
REVIEW_SCOPE='LOADER_ANDROID_F1_CAPABILITY'
MARKER_PROPERTY='codex,uniloader-android-v1'
LOGM_PROPERTY='codex,uniloader-logm-v1'
LOGM_SCHEMA='s22plus-loader-logm-control-v1'
LOGM_MAGIC=b'S22LGM1!'
LOGM_REPORT_MAGIC=b'S22LGR1!'
LOGM_DOMAIN=b'S22PLUS-LOADER-LOGM-CONTROL-V1\0'
LOGM_PAYLOAD=0x200000-16
LOGM_STATES={'SKIP_STATE':1,'SKIP_FDT':2,'SKIP_MAGIC':3,'SKIP_INDEX':4,
             'HEADER_CHANGED':5,'READBACK_MISMATCH':6,'READBACK_MATCH':7}


def logm_configuration(marker,key):
    require(re.fullmatch('[0-9a-f]{64}',marker) and type(key) is bytes and len(key)==32,
            'LOGM candidate identity/key differs')
    prefix=LOGM_MAGIC+struct.pack('<II',1,1)+bytes.fromhex(marker)+bytes(48)
    frame=prefix+hmac.digest(key,LOGM_DOMAIN+prefix,'sha256')
    seed=bytearray(LOGM_REPORT_MAGIC+struct.pack('>II',1,0)+bytes.fromhex(marker)+bytes(80))
    struct.pack_into('>II',seed,56,0xffffffff,0xffffffff)
    return dict(schema=LOGM_SCHEMA,marker=marker,frame_hex=frame.hex(),report_seed_hex=seed.hex(),
        report_property=LOGM_PROPERTY,base=0x800200000,region_size=0x200000,span=256,slot=0)


def logm_report(data,config):
    require(type(data) is bytes and len(data)==128 and data[:12]==LOGM_REPORT_MAGIC+struct.pack('>I',1)
        and data[16:48]==bytes.fromhex(config['marker']) and data[116:]==bytes(12),
        'LOGM FDT report shape or candidate differs')
    status=struct.unpack_from('>I',data,12)[0]
    require(status in LOGM_STATES.values(),'LOGM report has no final writer outcome')
    name=next(k for k,v in LOGM_STATES.items() if v==status)
    el,sctlr,slot,mismatches=struct.unpack_from('>IIII',data,48)
    before=list(struct.unpack_from('>IIII',data,64));check=list(struct.unpack_from('>IIII',data,80))
    after=list(struct.unpack_from('>IIII',data,96));flags=struct.unpack_from('>I',data,112)[0]
    expected_flags={1:0,2:0,3:129,4:129,5:143,6:255,7:255}[status]
    require(flags==expected_flags,'LOGM report flags disagree with outcome')
    require(el in (0,4,8,12) and (el in (4,8) or sctlr==0),
            'LOGM report has an impossible EL or an unobserved SCTLR value')
    if status!=1:require(el in (4,8) and not sctlr&((1<<25)|5),'LOGM report state is ineligible')
    else:require(el not in (4,8) or sctlr&((1<<25)|5),'LOGM state skip is inconsistent')
    if not flags&1:require(before==[0]*4,'unobserved LOGM header was populated')
    if not flags&8:require(check==[0]*4,'unobserved LOGM recheck was populated')
    if not flags&64:require(after==[0]*4,'unobserved LOGM final header was populated')
    if status==3:require(before[1]!=0x4d474f4c,'LOGM magic skip is inconsistent')
    if status==4:require(before[1]==0x4d474f4c and before[2]<256,'LOGM index skip is inconsistent')
    if flags&2:
        cursor=before[2]%LOGM_PAYLOAD
        require(before[1]==0x4d474f4c and before[2]>=256 and
            slot==(cursor-256 if cursor>=256 else LOGM_PAYLOAD-256),'LOGM slot is outside its qualified placement')
    else:require(slot==0xffffffff,'unattempted LOGM slot is populated')
    if status==5:require(check!=before,'LOGM changed-header outcome lacks drift')
    if flags&16:require(check==before,'LOGM commit did not pass header recheck')
    if status==6:require(1<=mismatches<=128,'LOGM readback mismatch count differs')
    elif status==7:require(mismatches==0,'LOGM matching readback has mismatches')
    else:require(mismatches==0xffffffff,'unattempted readback has a count')
    return dict(status=name,current_el=el,sctlr_low32=sctlr,slot_offset=slot if flags&2 else None,
        mismatch_count=mismatches if flags&32 else None,flags=flags,
        header_before=before if flags&1 else None,header_precommit=check if flags&8 else None,
        header_after=after if flags&64 else None,
        header_changed_after_commit=after!=before if flags&64 else None)


def logm_projection(report,data,config):
    require(type(data) is bytes and len(data)<=4*1024*1024,'LOGM snapshot exceeds fixed bound')
    observed=logm_report(report,config);frame=bytes.fromhex(config['frame_hex'])
    require(len(frame)==128,'LOGM frame size differs')
    offsets=[];cursor=0;damaged=foreign=0
    while True:
        offset=data.find(LOGM_MAGIC,cursor)
        if offset<0:break
        piece=data[offset:offset+128]
        if len(piece)!=128:damaged+=1
        elif piece[16:48]!=bytes.fromhex(config['marker']):foreign+=1
        elif not hmac.compare_digest(piece,frame):damaged+=1
        else:offsets.append(offset)
        cursor=offset+len(LOGM_MAGIC)
    return dict(schema='s22plus-loader-logm-observation-v1',writer=observed,
        status=('READBACK_AND_SNAPSHOT_OBSERVED' if observed['status']=='READBACK_MATCH' and offsets
                else 'DIAGNOSTIC_ONLY'),matching_frame_offsets=offsets,
        damaged_candidates=damaged,foreign_candidates=foreign,
        snapshot_bytes=len(data),same_attempt_frame_proved=False,
        reset_retention_proved=False,missing_frame_cause_proved=False,mainline_boot_proved=False)


def retained(receipt,maximum=128*1024*1024):
    unchanged(receipt,maximum=maximum)
    return Path(receipt['path'])


def logm_binding(value,marker):
    require(set(value)=={'configuration','key'},'LOGM configuration receipt shape differs')
    key=retained(value['key'],maximum=32).read_bytes()
    require(value['configuration']==logm_configuration(marker,key),'LOGM frame configuration differs')
    return value['configuration']


def logm_declarations(receipt,build):
    config=logm_binding(build['logm_control'],build['marker']);macros={}
    for line in retained(receipt,maximum=16384).read_text().splitlines():
        match=re.fullmatch(r'#define (G0Q_[A-Z0-9_]+) (.+)',line)
        require(match and match[1] not in macros,'LOGM generated declaration is malformed or duplicated')
        macros[match[1]]=match[2]
    expected={'G0Q_VENDOR_RUNTIME':str(build['kernel_header']['image_size']),
        'G0Q_ANDROID_MARKER':'"'+build['marker']+'"','G0Q_LOGM_CONTROL':'1'}
    expected.update({'G0Q_LOGM_'+name:str(value) for name,value in LOGM_STATES.items()})
    for field,name in [('frame_hex','G0Q_LOGM_FRAME'),('report_seed_hex','G0Q_LOGM_REPORT_SEED')]:
        expected[name]='{'+','.join(str(x) for x in bytes.fromhex(config[field]))+'}'
    require(macros==expected,'retained LOGM selection/frame/seed/enum declarations differ')
    return config


def _source_review(build,tests,entry,package):
    """Current checker review and retained runtime source identity are distinct."""
    from s22plus_mainline_task_v1 import capability
    import s22plus_loader_android_profile_v1 as selected
    review=read(retained(capability(ROOT,selected=selected)))
    approved={r['path']:r for r in review['sources']}
    runtime_suffixes=('s22plus_loader_android_h0/guard.c','s22plus_loader_android_h0/uniloader-android.patch',
                      's22plus_canary_h0/uniloader-g0q-entry.patch')
    if 'logm_control' in build:
        # Generated frame/seed/enum declarations are checked against the actual
        # ELF and instruction/EL results. Retain their original producer pins;
        # later host-only checker changes do not replace runtime provenance.
        runtime_suffixes+=('s22plus_loader_android_h0/logm-control.c',)
    source_rows=[r for r in build['source_pins'] if any(r['path'].endswith(s) for s in runtime_suffixes)]
    require(len(source_rows)==len(runtime_suffixes),'retained loader runtime provenance incomplete')
    source_rows += tests['source_pins']+[entry['source']]
    for row in source_rows:
        relative=str(Path(row['path']).relative_to(ROOT))
        require(relative in approved and all(approved[relative][k]==row[k] for k in ('size','sha256')),
                'runtime or current checker is outside reviewed capability')
    pack='workspace/public/src/mainline/s22plus_canary_h0/package_loader.py'
    require(approved[pack]['sha256']==package['source_sha256'],'package checker review differs')


def image_binding(image,*,artifact_bytes=False,require_review=True):
    keys={'schema','profile','namespace','version','run_id_hex','ap','member','qualification',
          'runtime_sources','marker_sha256','kernel_release','boot_sha256','original_a_sha256'}
    logm='logm_control' in image
    if logm:keys.add('logm_control')
    require(set(image)==keys and image['schema']=='s22plus-loader-android-image-v1' and
        image['profile']==PROFILE and image['namespace']==NAMESPACE and image['version']==VERSION and
        re.fullmatch('[0-9a-f]{32}',image['run_id_hex']),'loader Android image shape differs')
    q=read(retained(image['qualification']))
    qkeys={'schema','status','image','package','loader','loader_tests','entry_tests','device_actions'}
    if logm:qkeys.add('generated_declarations')
    require(set(q)==qkeys and
        q['schema']=='s22plus-loader-android-qualification-v1' and
        q['status']=='PASS_H0_LOADER_ANDROID_CANDIDATE' and q['device_actions']==0 and
        q['image']=={k:v for k,v in image.items() if k!='qualification'},'loader qualification differs')
    package=read(retained(q['package']));build=read(retained(q['loader']))
    tests=read(retained(q['loader_tests']));entry=read(retained(q['entry_tests']))
    require(build['status']=='H0_LOADER_ANDROID_BUILT_NOT_DEVICE_ADMITTED' and
        build['device_actions']==0 and build['activation'] is False and
        build['fdt_capacity']==2*1024*1024 and build['marker_property']==MARKER_PROPERTY and
        re.fullmatch('[0-9a-f]{64}',build['marker']) and build['retained_initrd_preserved'] is True and
        image['run_id_hex']==build['marker'][:32] and
        image['marker_sha256']==build['marker_sha256']==hashlib.sha256(build['marker'].encode()).hexdigest() and
        image['kernel_release']==build['kernel_release'] and
        image['runtime_sources']=={'loader':build['loader'],'kernel':build['kernel']},
        'loader runtime and marker binding differs')
    require(package['status']=='H0_BOOT_V4_PACKAGED_NOT_DEVICE_ADMITTED' and package['profile']==PROFILE and
        package['activation'] is False and package['device_actions']==0 and
        package['outer_ramdisk_inherited_from_abl'] is True and
        package['outer_ramdisk_retained_and_not_used_by_loader'] is False and
        package['loader_sha256']==build['loader']['sha256'] and
        package['original_a_sha256']==build['original_a']['sha256']==image['original_a_sha256'] and
        package['copies'][0]['ap']==image['ap'] and
        package['copies'][0]['boot']['sha256']==package['copies'][1]['boot']['sha256']==image['boot_sha256'] and
        package['copies'][0]['ap']['sha256']==package['copies'][1]['ap']['sha256'] and
        image['boot_sha256']!=image['original_a_sha256'],'loader package join differs')
    for result,receipt,status,field in (
        (tests,q['loader_tests'],'PASS_H0_ACTUAL_ARM64_LOADER_ANDROID','qualification_sha256'),
        (entry,q['entry_tests'],'PASS_H0_QEMU_ACTUAL_EL_LOADER_ANDROID','entry_vm_sha256')):
        require(result['status']==status and result['device_actions']==0 and
            result['loader_sha256']==build['loader']['sha256'] and package[field]==receipt['sha256'],
            'actual-loader qualification join differs')
    require(tests['elf_sha256']==build['elf']['sha256'] and tests['retained_fdt']==entry['retained_fdt']==build['retained_fdt'] and
        tests['physical_entry_proved'] is False and entry['physical_entry_proved'] is False,
        'emulated entry provenance differs')
    require(('logm_control' in build)==logm,'LOGM instrumentation receipt missing or spurious')
    if logm:
        require(image['logm_control']==build['logm_control'],'LOGM build/image join differs')
        config=logm_binding(image['logm_control'],build['marker'])
        logm_declarations(q['generated_declarations'],build)
        require(tests.get('logm_control',{}).get('status')=='PASS_H0_ACTUAL_LOADER_LOGM_CONTROL' and
            tests['logm_control']['configuration']==config and
            entry.get('logm_control',{}).get('status')=='PASS_H0_ACTUAL_EL_LOADER_LOGM_CONTROL' and
            entry['logm_control']['configuration']==config,'LOGM actual-code/EL qualification missing')
    expected=read(ROOT/'workspace/public/src/device-action/profiles/s22plus_fyg8.json')['start_health']['boot_sha256']
    require(image['original_a_sha256']==expected,'control kernel is not from exact original A')
    for receipt in image['runtime_sources'].values():retained(receipt)
    if require_review:_source_review(build,tests,entry,package)
    if artifact_bytes:
        with transport.pin_boot_only_ap(Path(image['ap']['path']),label='loader Android control',
                expected_size=image['ap']['size'],expected_sha256=image['ap']['sha256']) as ap:
            require(transport.boot_only_member_receipt(ap,label='loader Android control')==image['member'],
                    'control AP member differs')
            compressed=transport.read_boot_only_member(ap,label='loader Android control')
        data=boot.decompress_lz4_stream_python(compressed,maximum=128*1024*1024)
        parsed=boot.parse_boot_v4(data)
        # Reopen the actual retained rollback AP. Historical extracted boot
        # provenance can have hard links; it is not the admitted A transfer.
        rollback=android_artifact(ROOT)
        with transport.pin_boot_only_ap(Path(rollback['ap']['path']),label='original Android',
                expected_size=rollback['ap']['size'],expected_sha256=rollback['ap']['sha256'],
                require_deterministic_metadata=False) as original_ap:
            require(transport.boot_only_member_receipt(original_ap,label='original Android',
                    require_deterministic_metadata=False)==rollback['member'],'original A AP member differs')
            original_bytes=boot.decompress_lz4_stream_python(transport.read_boot_only_member(original_ap,
                label='original Android',require_deterministic_metadata=False),maximum=128*1024*1024)
        require(len(original_bytes)==build['original_a']['size'] and
                hashlib.sha256(original_bytes).hexdigest()==build['original_a']['sha256'],
                'original A AP differs from retained build provenance')
        original=boot.parse_boot_v4(original_bytes)
        require(len(data)==96*1024*1024 and hashlib.sha256(data).hexdigest()==image['boot_sha256'] and
            parsed.kernel==retained(build['loader']).read_bytes() and
            original.kernel==retained(build['kernel']).read_bytes() and parsed.ramdisk==original.ramdisk,
            'actual candidate/rollback kernel or ramdisk differs')
    return build


def qualify(package_dir,loader_dir,loader_tests,entry_tests,output):
    package_dir,loader_dir,loader_tests,entry_tests,output=[Path(p).resolve() for p in
        (package_dir,loader_dir,loader_tests,entry_tests,output)]
    require(output.is_relative_to(ROOT/'workspace/private') and not output.exists(),'fresh private qualification')
    package=read(package_dir/'result.json');build=read(loader_dir/'result.json');ap=package['copies'][0]['ap']
    with transport.pin_boot_only_ap(Path(ap['path']),label='H0 loader control',expected_size=ap['size'],
            expected_sha256=ap['sha256']) as handle:
        member=transport.boot_only_member_receipt(handle,label='H0 loader control')
    image=dict(schema='s22plus-loader-android-image-v1',profile=PROFILE,namespace=NAMESPACE,version=VERSION,
        run_id_hex=build['marker'][:32],ap=ap,member=member,
        runtime_sources={'loader':build['loader'],'kernel':build['kernel']},marker_sha256=build['marker_sha256'],
        kernel_release=build['kernel_release'],boot_sha256=package['copies'][0]['boot']['sha256'],
        original_a_sha256=build['original_a']['sha256'])
    if 'logm_control' in build:
        image['logm_control']=build['logm_control']
    output.mkdir(mode=0o700,parents=True)
    q=dict(schema='s22plus-loader-android-qualification-v1',status='PASS_H0_LOADER_ANDROID_CANDIDATE',
        image=image,package=pin(package_dir/'result.json'),loader=pin(loader_dir/'result.json'),
        loader_tests=pin(loader_tests/'result.json'),entry_tests=pin(entry_tests/'result.json'),device_actions=0)
    if 'logm_control' in build:
        q['generated_declarations']=pin(Path(build['elf']['path']).parent/'arch/aarch64/g0q-android-marker.h')
    image=dict(image,qualification=publish(output/'qualification.json',q))
    # This producer has no device path. Task preparation and every normal
    # effect require the separate current source-bound capability review.
    image_binding(image,artifact_bytes=True,require_review=False)
    return publish(output/'image.json',image)

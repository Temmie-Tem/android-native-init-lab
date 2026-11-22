"""Exact artifact admission for the FYG8 loader-to-Android comparison."""
from functools import lru_cache
import hashlib
import hmac
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import re
import struct

from s22plus_native_records_v3 import pin,publish,read,require
from s22plus_native_task_v3 import unchanged,android_artifact
import s22plus_boot_only_f1_transport as transport
import s22plus_boot_verify as boot
import s22plus_loader_prefix_v1 as prefix

ROOT=Path(__file__).resolve().parents[5]
PROFILE='loader-android-v1'
OPERATION='loader-android'
SELECTION='loader-android-evidence'
RETURN='loader-android-download'
POLICY='docs/operations/S22PLUS_LOADER_ANDROID_V1.md'
REVIEW='workspace/public/src/device-action/bindings/s22plus_loader_android_timing_v2_review.json'
NAMESPACE='la001'
VERSION='loader-android-1'
SECONDS=1800
OBSERVATION_NS=240_000_000_000
TASK_SCHEMA='s22plus-loader-android-task-v1'
REVIEW_SCHEMA='s22plus-loader-android-review-v1'
REVIEW_SCOPE='LOADER_ANDROID_F1_CAPABILITY'
MARKER_PROPERTY='codex,uniloader-android-v1'
LOGM_PROPERTY='codex,uniloader-logm-v1'
TIMING_PROPERTY='codex,uniloader-timing-v1'
LOGM_SCHEMA='s22plus-loader-logm-control-v1'
LOGM_MAGIC=b'S22LGM1!'
LOGM_REPORT_MAGIC=b'S22LGR1!'
LOGM_DOMAIN=b'S22PLUS-LOADER-LOGM-CONTROL-V1\0'
LOGM_PAYLOAD=0x200000-16
@lru_cache(maxsize=1)
def timing_codec():
    path=Path(__file__).resolve().parents[2]/'mainline/s22plus_loader_android_h0/timing.py'
    spec=spec_from_file_location('s22plus_loader_timing_codec',path)
    module=module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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
    if 'timing_control' in build:
        timing=timing_codec()
        armed=timing_mode(build['timing_control'])
        expected.update(G0Q_BOOT_TIMING='1',G0Q_TIMING_LOGM=str(int(armed)),
            G0Q_TIMING_SEED='{'+','.join(map(str,timing.seed(build['marker'])))+'}')
    require(macros==expected,'retained LOGM selection/frame/seed/enum declarations differ')
    return config


def timing_mode(descriptor):
    require(type(descriptor) is dict and set(descriptor)=={'logm_enabled','report_property'} and
        descriptor['report_property']==TIMING_PROPERTY and type(descriptor['logm_enabled']) is bool,
        'boot timing descriptor differs')
    return descriptor['logm_enabled']


def timing_projection(timer,writer,config,descriptor):
    timing=timing_codec()
    armed=timing_mode(descriptor)
    writer_seed=bytes.fromhex(config['report_seed_hex'])
    if not armed:
        require(writer==writer_seed,'disabled LOGM writer changed its seed')
    if timer==timing.seed(config['marker']):
        observed=logm_report(writer,config) if armed and writer!=writer_seed else None
        return dict(status='TIMING_UNAVAILABLE',logm_enabled=armed,writer=observed,counter=None)
    sample=timing.project(timer,config['marker'],armed)
    if armed:
        observed=logm_report(writer,config)
        success=observed['status']=='READBACK_MATCH' and not observed['header_changed_after_commit']
    else:
        observed=dict(status='DISABLED')
        success=True
    return dict(status='TIMING_OBSERVED' if success else 'TIMING_WITHOUT_VALID_LOGM_WRITE',
                logm_enabled=armed,writer=observed,counter=sample)


def prefix_binding(value,marker):
    require(set(value)=={'configuration','key','kernel_build','source','image','elf','entry_offset','frame_offset'},
            'prefix descriptor shape differs')
    key=retained(value['key'],maximum=32).read_bytes()
    require(value['configuration']==prefix.configuration(marker,key),'prefix candidate/key configuration differs')
    built=read(retained(value['kernel_build']));source=read(retained(value['source']))
    require(built['status']=='H0_KERNEL_BUILT_NOT_DEVICE_AUTHORITY' and built['device_actions']==0 and
        built['prefix_source']==value['source'] and source['configuration']==value['configuration'] and
        source['key']==value['key'] and source['device_actions']==0 and
        built['sha256']==value['image']['sha256'] and built['file_size']==value['image']['size'],
        'prefix build/source/image provenance differs')
    data=retained(value['image']).read_bytes();retained(value['elf'])
    require(data[56:60]==b'ARMd' and struct.unpack_from('<QQQ',data,8)==(0,built['runtime_size'],10),
            'prefix raw Image header differs')
    require(type(value['entry_offset']) is int and 64<=value['entry_offset']<len(data) and
        value['entry_offset']%4==0 and type(value['frame_offset']) is int and
        0<=value['frame_offset']<=len(data)-128 and
        data[value['frame_offset']:value['frame_offset']+128]==
        prefix.marker_module().frame(marker,key,2,version=1),'prefix actual embedded frame differs')
    return value['configuration']


def prefix_declarations(receipt,writer,build):
    value=build['prefix_control'];cfg=prefix_binding(value,build['marker'])
    macros={}
    for line in retained(receipt,maximum=16384).read_text().splitlines():
        match=re.fullmatch(r'#define (G0Q_[A-Z0-9_]+) (.+)',line)
        require(match and match[1] not in macros,'prefix generated declaration malformed or duplicated')
        macros[match[1]]=match[2]
    expected={'G0Q_VENDOR_RUNTIME':str(build['kernel_header']['image_size']),
        'G0Q_PAYLOAD_RUNTIME':str(build['extents']['kernel'][1]-build['extents']['kernel'][0]),
        'G0Q_ANDROID_MARKER':'"'+build['marker']+'"','G0Q_PREFIX_CONTROL':'1',
        'G0Q_PREFIX_COOKIE':str(prefix.COOKIE),'G0Q_PREFIX_ENTRY_OFFSET':str(value['entry_offset']),
        'G0Q_PREFIX_FRAME_OFFSET':str(value['frame_offset']),
        'G0Q_PREFIX_REPORT_SEED':'{'+','.join(str(x) for x in bytes.fromhex(cfg['report_seed_hex']))+'}'}
    expected.update({'G0Q_PREFIX_'+name:str(number) for name,number in prefix.STATES.items()})
    require(macros==expected and retained(writer,maximum=16384).read_text()==
        prefix.marker_module().render(cfg['retained_marker'],1),'prefix generated header/writer differs')
    return cfg


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
        runtime_suffixes+=('s22plus_loader_android_h0/logm-control.c','s22plus_loader_android_h0/logm-layout.h')
    if 'prefix_control' in build:
        runtime_suffixes+=tuple('s22plus_loader_android_h0/'+name for name in
            ('prefix-control.c','prefix-entry.S','prefix_image.py','logm-layout.h'))
        runtime_suffixes+=('s22plus_canary_h0/retained-marker.S','s22plus_canary_h0/build_kernel.py')
    timed='timing_control' in build
    if timed:
        runtime_suffixes+=tuple('s22plus_loader_android_h0/'+name for name in
            ('boot-timing.c','boot-timing.h','boot-timing.patch','timing.py'))
    source_rows=[r for r in build['source_pins'] if any(r['path'].endswith(s) for s in runtime_suffixes)]
    require(len(source_rows)==len(runtime_suffixes),'retained loader runtime provenance incomplete')
    source_rows += tests['source_pins']+[entry['source']]
    if timed:
        source_rows.append(tests['source'])
        require({Path(row['path']).name for row in tests['source_pins']}==
                {'qualify.py','qualify_loader.py','build.py','timing.py','prepare.py',
                 's22plus_loader_android_profile_v1.py','s22plus_fyg8_retained_snapshot_model.py'},
                'timing qualification harness source closure differs')
    for row in source_rows:
        relative=str(Path(row['path']).relative_to(ROOT))
        if timed:
            # Preserve the isolation-era producer receipt. Match exact bytes to
            # their reviewed repository location, without reissuing that receipt.
            retained(row)
            prefix='workspace/private/'
            if relative.startswith(prefix) and '/workspace/public/' in relative:
                relative='workspace/public/'+relative.rsplit('/workspace/public/',1)[1]
        require(relative in approved and all(approved[relative][k]==row[k] for k in ('size','sha256')),
                'runtime or current checker is outside reviewed capability')
    pack='workspace/public/src/mainline/s22plus_canary_h0/package_loader.py'
    require(approved[pack]['sha256']==package['source_sha256'],'package checker review differs')


def image_binding(image,*,artifact_bytes=False,require_review=True):
    keys={'schema','profile','namespace','version','run_id_hex','ap','member','qualification',
          'runtime_sources','marker_sha256','kernel_release','boot_sha256','original_a_sha256'}
    logm='logm_control' in image
    pfx='prefix_control' in image
    timed='timing_control' in image
    require(not(logm and pfx) and (not timed or logm and not pfx),'mutually exclusive loader diagnostics')
    if timed:
        timing_mode(image['timing_control'])
        keys.add('timing_control')
    if logm:keys.add('logm_control')
    if pfx:keys.add('prefix_control')
    require(set(image)==keys and image['schema']=='s22plus-loader-android-image-v1' and
        image['profile']==PROFILE and image['namespace']==NAMESPACE and image['version']==VERSION and
        re.fullmatch('[0-9a-f]{32}',image['run_id_hex']),'loader Android image shape differs')
    q=read(retained(image['qualification']))
    qkeys={'schema','status','image','package','loader','loader_tests','entry_tests','device_actions'}
    if logm or pfx:qkeys.add('generated_declarations')
    if timed:qkeys.add('timing_comparison')
    if pfx:qkeys.add('prefix_generated_writer')
    require(set(q)==qkeys and
        q['schema']=='s22plus-loader-android-qualification-v1' and
        q['status']=='PASS_H0_LOADER_ANDROID_CANDIDATE' and q['device_actions']==0 and
        q['image']=={k:v for k,v in image.items() if k!='qualification'},'loader qualification differs')
    package=read(retained(q['package']));build=read(retained(q['loader']))
    tests=read(retained(q['loader_tests']));entry=read(retained(q['entry_tests']))
    runtime_sources={'loader':build['loader'],'kernel':build['kernel']}
    if pfx:runtime_sources['prefix']=build['prefix_control']['image']
    require(build['status']=='H0_LOADER_ANDROID_BUILT_NOT_DEVICE_ADMITTED' and
        build['device_actions']==0 and build['activation'] is False and
        build['fdt_capacity']==2*1024*1024 and build['marker_property']==MARKER_PROPERTY and
        re.fullmatch('[0-9a-f]{64}',build['marker']) and build['retained_initrd_preserved'] is True and
        image['run_id_hex']==build['marker'][:32] and
        image['marker_sha256']==build['marker_sha256']==hashlib.sha256(build['marker'].encode()).hexdigest() and
        image['kernel_release']==build['kernel_release'] and
        image['runtime_sources']==runtime_sources,
        'loader runtime and marker binding differs')
    package_status=('H0_LOADER_TIMING_BOOT_V4_PACKAGED_NOT_DEVICE_ADMITTED' if timed else
                    'H0_BOOT_V4_PACKAGED_NOT_DEVICE_ADMITTED')
    require(package['status']==package_status and package['profile']==PROFILE and
        package['activation'] is False and package['device_actions']==0 and
        package['outer_ramdisk_inherited_from_abl'] is True and
        package['outer_ramdisk_retained_and_not_used_by_loader'] is False and
        package['loader_sha256']==build['loader']['sha256'] and
        package['original_a_sha256']==build['original_a']['sha256']==image['original_a_sha256'] and
        package['copies'][0]['ap']==image['ap'] and
        package['copies'][0]['boot']['sha256']==package['copies'][1]['boot']['sha256']==image['boot_sha256'] and
        package['copies'][0]['ap']['sha256']==package['copies'][1]['ap']['sha256'] and
        image['boot_sha256']!=image['original_a_sha256'],'loader package join differs')
    loader_status=('PASS_H0_LOADER_TIMING_PAIR_ARM' if timed else 'PASS_H0_ACTUAL_ARM64_LOADER_ANDROID')
    entry_status=('PASS_H0_QEMU_ACTUAL_EL_LOADER_TIMING' if timed else 'PASS_H0_QEMU_ACTUAL_EL_LOADER_ANDROID')
    for result,receipt,status,field in (
        (tests,q['loader_tests'],loader_status,'qualification_sha256'),
        (entry,q['entry_tests'],entry_status,'entry_vm_sha256')):
        require(result['status']==status and result['device_actions']==0 and
            result['loader_sha256']==build['loader']['sha256'] and package[field]==receipt['sha256'],
            'actual-loader qualification join differs')
    require(entry['retained_fdt']==build['retained_fdt'] and entry['physical_entry_proved'] is False,
        'emulated entry provenance differs')
    if timed:
        _timing_evidence(image,build,tests,entry,package,q,artifact_bytes=artifact_bytes)
    else:
        require(tests['elf_sha256']==build['elf']['sha256'] and
            tests['retained_fdt']==build['retained_fdt'] and tests['physical_entry_proved'] is False,
            'emulated loader provenance differs')
    require(('timing_control' in build)==timed and ('logm_control' in build)==logm,
        'LOGM or timing instrumentation receipt missing or spurious')
    require(('prefix_control' in build)==pfx,'prefix instrumentation receipt missing or spurious')
    if logm:
        require(image['logm_control']==build['logm_control'],'LOGM build/image join differs')
        config=logm_binding(image['logm_control'],build['marker'])
        logm_declarations(q['generated_declarations'],build)
        if not timed:require(tests.get('logm_control',{}).get('status')=='PASS_H0_ACTUAL_LOADER_LOGM_CONTROL' and
            tests['logm_control']['configuration']==config and
            entry.get('logm_control',{}).get('status')=='PASS_H0_ACTUAL_EL_LOADER_LOGM_CONTROL' and
            entry['logm_control']['configuration']==config,'LOGM actual-code/EL qualification missing')
    if pfx:
        require(image['prefix_control']==build['prefix_control'],'prefix build/image join differs')
        config=prefix_declarations(q['generated_declarations'],q['prefix_generated_writer'],build)
        require(tests.get('prefix_control',{}).get('status')=='PASS_H0_ACTUAL_LOADER_PREFIX_CONTROL' and
            tests['prefix_control']['configuration']==config and
            entry.get('prefix_control',{}).get('status')=='PASS_H0_ACTUAL_EL_LOADER_PREFIX_CONTROL' and
            entry['prefix_control']['configuration']==config,'prefix actual-code/EL qualification missing')
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


def _timing_evidence(image,build,tests,entry,package,q,*,artifact_bytes):
    timing=timing_codec()
    descriptor=image['timing_control']
    armed=timing_mode(descriptor)
    require(descriptor==build['timing_control']==tests['timing_control']==entry['timing_control']==package['timing_control']
        and tests['actual_entry']==q['entry_tests'] and
        tests['logm_configuration']==build['logm_control']['configuration'],
        'timing build, ELF and observer receipt differ')
    pair=read(retained(tests['pair']))
    require(pair['schema']=='s22plus-timing-pair-h0-v1' and pair['device_actions']==0 and
        pair['vendor_kernel_sha256']==build['kernel']['sha256'] and pair['retained_fdt']==build['retained_fdt'] and
        pair['physical_counter_access_proved'] is False,'timing comparator provenance differs')
    comparison=read(retained(q['timing_comparison']))
    require(comparison['schema']=='s22plus-loader-timing-comparison-h0-v1' and
        comparison['status']=='H0_PAIR_PACKAGED_NOT_DEVICE_ADMITTED' and comparison['device_actions']==0 and
        comparison['activation'] is False and comparison['normalized_pair']==tests['pair'] and
        comparison['rollback_boot_sha256']==image['original_a_sha256'] and
        set(comparison['arms'])==set(pair['arms'])=={'off','on'},
        'same exact packaged timing pair is required')
    active='on' if armed else 'off'
    writer_proof=read(retained(tests['linked_writer']))
    require(writer_proof['schema']=='s22plus-linked-timing-logm-cases-v1' and
        writer_proof['elf']==pair['arms']['on']['elf'] and writer_proof['loader']==pair['arms']['on']['loader'],
        'writer corpus is not bound to the paired LOGM on ELF')
    writer=read(retained(writer_proof['results']))
    require(writer['status']=='PASS_H0_ACTUAL_LOADER_LOGM_CONTROL' and
        writer['physical_cache_coherence_proved'] is False,
        'actual linked writer qualification differs')
    require(set(pair['data_only_spans'])=={'android_candidate_marker','g0q_timing_seed','g0q_timing_logm',
        'g0q_logm_report_seed','g0q_logm_frame'},'pair data span declaration differs')
    for mode,arm in comparison['arms'].items():
        arm_build=read(retained(arm['build']))
        arm_package=read(retained(arm['package']))
        arm_tests=read(retained(arm['qualification']))
        require(pair['arms'][mode]==dict(loader=arm_build['loader'],elf=arm_build['elf'],marker=arm_build['marker'])
            and arm_build['timing_control']['logm_enabled'] is (mode=='on') and arm_tests['pair']==tests['pair']
            and arm_tests['linked_writer']==tests['linked_writer'] and arm_tests['actual_entry']==arm['vm']
            and arm_package['qualification_sha256']==arm['qualification']['sha256'] and
            arm_package['entry_vm_sha256']==arm['vm']['sha256'] and
            arm_package['copies'][0]['ap']==arm['ap'] and arm_package['copies'][0]['boot']==arm['boot'],
            'packaged pair arm differs from its actual timing qualification')
        if mode=='on':
            require(writer['configuration']==arm_build['logm_control']['configuration'],
                'writer corpus configuration differs')
        if mode==active:
            require(arm['ap']==image['ap'] and arm['member']==image['member'] and
                (arm['build'],arm['package'],arm['qualification'],arm['vm'])==
                (q['loader'],q['package'],q['loader_tests'],q['entry_tests']),
                'candidate does not belong to the exact packaged pair')
    require(comparison['arms']['off']['ap']['sha256']!=comparison['arms']['on']['ap']['sha256'],
        'timing pair arms share an AP identity')
    require([(r['name'],r['terminal'],r['write_bytes']) for r in tests['actual_arm64_guard']]==[
        ('live-tree-valid','guard',0),('malformed-fdt-magic','reject',0),('preexisting-timing-property','reject',0)],
        'timing guard qualification differs')
    cases=entry['cases']
    require([(r['actual_entry_el'],r['terminal']) for r in cases]==[(1,'entry'),(2,'entry'),(3,'reject')],
        'timing entry/negative qualification differs')
    if not artifact_bytes:
        return
    from mainline.s22plus_canary_h0.prepare import nodes
    for row in cases[:2]:
        tree=nodes(retained(row['timing_report']))
        require(timing.project(tree['/chosen'][TIMING_PROPERTY],build['marker'],armed)==row['timing'],
            'actual timing report differs')
        result=timing_projection(tree['/chosen'][TIMING_PROPERTY],tree['/chosen'][LOGM_PROPERTY],
            build['logm_control']['configuration'],descriptor)
        require(result['status']=='TIMING_OBSERVED' and result['writer']==row['logm_writer'],
            'actual QEMU LOGM mode differs')
    elf=retained(build['elf'])
    from elftools.elf.elffile import ELFFile
    with elf.open('rb') as stream:
        table=ELFFile(stream).get_section_by_name('.symtab')
        blob=retained(build['loader']).read_bytes()
        origin=build['runtime_symbols']['_head']
        guard,=table.get_symbol_by_name('_guard_passed')
        entry_offset=guard['st_value']-origin
        require(blob[entry_offset:entry_offset+8]==struct.pack('<II',0xd5033fdf,0xd53be05b),
            'actual guard has no initial ARM virtual counter sample')
        marker=build['marker'].encode()
        require(blob.count(marker)==1,'actual candidate marker span differs')
        spans={'android_candidate_marker':(blob.index(marker),len(marker))}
        config=build['logm_control']['configuration']
        for name,expected in (('g0q_timing_seed',timing.seed(build['marker'])),
                              ('g0q_timing_logm',struct.pack('<I',int(armed))),
                              ('g0q_logm_frame',bytes.fromhex(config['frame_hex'])),
                              ('g0q_logm_report_seed',bytes.fromhex(config['report_seed_hex']))):
            symbol,=table.get_symbol_by_name(name)
            offset=symbol['st_value']-origin
            require(symbol['st_size']==len(expected) and blob[offset:offset+len(expected)]==expected,
                'actual linked timing or LOGM declaration differs')
            spans[name]=(offset,len(expected))
        require({name:list(span) for name,span in spans.items()}==pair['data_only_spans'],
            'actual ELF data spans differ from the pair')
        masked=bytearray(blob)
        for offset,size in spans.values():
            masked[offset:offset+size]=bytes(size)
        require(hashlib.sha256(masked).hexdigest()==pair['masked_loader_sha256'],
            'actual normalized binary differs from the paired code')


def qualify(package_dir,loader_dir,loader_tests,entry_tests,output,*,timing_comparison=None):
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
    if 'timing_control' in build:
        image['timing_control']=build['timing_control']
    require((timing_comparison is not None)==('timing_control' in image),
        'timed qualification requires the exact packaged pair')
    if 'prefix_control' in build:
        image['prefix_control']=build['prefix_control']
        image['runtime_sources']['prefix']=build['prefix_control']['image']
    output.mkdir(mode=0o700,parents=True)
    q=dict(schema='s22plus-loader-android-qualification-v1',status='PASS_H0_LOADER_ANDROID_CANDIDATE',
        image=image,package=pin(package_dir/'result.json'),loader=pin(loader_dir/'result.json'),
        loader_tests=pin(loader_tests/'result.json'),entry_tests=pin(entry_tests/'result.json'),device_actions=0)
    if 'logm_control' in build or 'prefix_control' in build:
        q['generated_declarations']=pin(Path(build['elf']['path']).parent/'arch/aarch64/g0q-android-marker.h')
    if timing_comparison is not None:
        q['timing_comparison']=pin(Path(timing_comparison))
    if 'prefix_control' in build:
        q['prefix_generated_writer']=pin(Path(build['elf']['path']).parent/'arch/aarch64/g0q-prefix-loader-writer.S')
    image=dict(image,qualification=publish(output/'qualification.json',q))
    # This producer has no device path. Task preparation and every normal
    # effect require the separate current source-bound capability review.
    image_binding(image,artifact_bytes=True,require_review=False)
    return publish(output/'image.json',image)

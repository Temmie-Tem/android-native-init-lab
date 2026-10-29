"""Exact artifact admission for the FYG8 loader-to-Android comparison."""
import hashlib
from pathlib import Path
import re

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
REVIEW='workspace/public/src/device-action/bindings/s22plus_loader_android_v1_review.json'
NAMESPACE='la001'
VERSION='loader-android-1'
SECONDS=1800
OBSERVATION_NS=240_000_000_000
TASK_SCHEMA='s22plus-loader-android-task-v1'
REVIEW_SCHEMA='s22plus-loader-android-review-v1'
REVIEW_SCOPE='LOADER_ANDROID_F1_CAPABILITY'
MARKER_PROPERTY='codex,uniloader-android-v1'


def retained(receipt,maximum=128*1024*1024):
    unchanged(receipt,maximum=maximum)
    return Path(receipt['path'])


def _source_review(build,tests,entry,package):
    """Current checker review and retained runtime source identity are distinct."""
    from s22plus_mainline_task_v1 import capability
    import s22plus_loader_android_profile_v1 as selected
    review=read(retained(capability(ROOT,selected=selected)))
    approved={r['path']:r for r in review['sources']}
    runtime_suffixes=('s22plus_loader_android_h0/guard.c','s22plus_loader_android_h0/uniloader-android.patch',
                      's22plus_canary_h0/uniloader-g0q-entry.patch')
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
    require(set(image)==keys and image['schema']=='s22plus-loader-android-image-v1' and
        image['profile']==PROFILE and image['namespace']==NAMESPACE and image['version']==VERSION and
        re.fullmatch('[0-9a-f]{32}',image['run_id_hex']),'loader Android image shape differs')
    q=read(retained(image['qualification']))
    require(set(q)=={'schema','status','image','package','loader','loader_tests','entry_tests','device_actions'} and
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
    output.mkdir(mode=0o700,parents=True)
    q=dict(schema='s22plus-loader-android-qualification-v1',status='PASS_H0_LOADER_ANDROID_CANDIDATE',
        image=image,package=pin(package_dir/'result.json'),loader=pin(loader_dir/'result.json'),
        loader_tests=pin(loader_tests/'result.json'),entry_tests=pin(entry_tests/'result.json'),device_actions=0)
    image=dict(image,qualification=publish(output/'qualification.json',q))
    # This producer has no device path. Task preparation and every normal
    # effect require the separate current source-bound capability review.
    image_binding(image,artifact_bytes=True,require_review=False)
    return publish(output/'image.json',image)

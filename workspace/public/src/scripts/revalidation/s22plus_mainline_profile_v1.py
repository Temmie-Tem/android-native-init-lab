"""Mainline RAM-only artifact admission, independent of vendor native profiles."""
from pathlib import Path
import hashlib
import json
import re
import sys

from s22plus_native_records_v3 import pin,publish,read,require,verify
import s22plus_boot_only_f1_transport as transport
import s22plus_boot_verify as boot

ROOT=Path(__file__).resolve().parents[5]
sys.path.insert(0,str(ROOT/'workspace/public/src'))
from mainline.s22plus_canary_h0 import verify as codec

PROFILE='mainline-ram-v1'
OPERATION='mainline-ram'
SELECTION='mainline-evidence'
POLICY='docs/operations/S22PLUS_MAINLINE_RAM_V1.md'
REVIEW='workspace/public/src/device-action/bindings/s22plus_mainline_retained_v5_review.json'
NAMESPACE='ml001'
VERSION='mainline-ram-1'
SECONDS=1800
OBSERVATION_NS=120_000_000_000
TASK_SCHEMA='s22plus-mainline-task-v1'
REVIEW_SCHEMA='s22plus-mainline-ram-review-v1'
REVIEW_SCOPE='MAINLINE_RAM_F1_CAPABILITY'


def unchanged(receipt,maximum=128*1024*1024):
    from s22plus_native_task_v3 import unchanged as cached
    cached(receipt,maximum=maximum)
    return Path(receipt['path'])


def image_binding(image,*,artifact_bytes=False):
    keys={'schema','profile','namespace','version','run_id_hex','ap','member','key','qualification','runtime_sources'}
    if 'retained_marker' in image:keys.add('retained_marker')
    require(set(image)==keys and image['schema']=='s22plus-mainline-image-v1' and image['profile']==PROFILE and
            image['namespace']==NAMESPACE and image['version']==VERSION and
            re.fullmatch('[0-9a-f]{32}',image['run_id_hex']),'mainline image shape differs')
    qualified=read(unchanged(image['qualification']))
    require(set(qualified)=={'schema','status','image','package','loader','init_manifest','entry_review',
                            'loader_tests','entry_tests','device_actions'} and
            qualified['schema']=='s22plus-mainline-qualification-v1' and
            qualified['status']=='PASS_H0_MAINLINE_CANDIDATE' and qualified['device_actions']==0 and
            qualified['image']=={k:v for k,v in image.items() if k!='qualification'},'mainline qualification differs')
    package=read(unchanged(qualified['package']));loader=read(unchanged(qualified['loader']))
    manifest=read(unchanged(qualified['init_manifest']));review=read(unchanged(qualified['entry_review']))
    require(package['status']=='H0_BOOT_V4_PACKAGED_NOT_DEVICE_ADMITTED' and package['activation'] is False and
            package['device_actions']==0 and package['loader_sha256']==loader['loader']['sha256'] and
            package['copies'][0]['ap']==image['ap'] and
            package['copies'][0]['boot']['sha256']==package['copies'][1]['boot']['sha256'] and
            package['copies'][0]['ap']['sha256']==package['copies'][1]['ap']['sha256'], 'mainline package join differs')
    require(loader['status']=='H0_LOADER_BUILT_RUNTIME_PLACEMENT_GUARDED' and loader['device_actions']==0 and
            loader['physical_entry']=='NOT_ADMITTED_H0_ONLY' and
            loader['initramfs_manifest']==qualified['init_manifest']['path'], 'mainline loader join differs')
    require(manifest['vm'] is False and manifest['status']=='H0_INITRAMFS_BUILT_NOT_DEVICE_AUTHORITY' and
            re.fullmatch('[0-9a-f]{64}',manifest['candidate_id']) and
            image['run_id_hex']==manifest['candidate_id'][:32] and manifest['port']==47649 and
            image['key']['path']==manifest['key_path'] and image['key']['size']==32, 'physical canary identity differs')
    key=unchanged(image['key'],32).read_bytes()
    identity=hashlib.sha256(json.dumps({'inputs':manifest['inputs'],'vm':False,
        'key_commitment':hashlib.sha256(key).hexdigest()},sort_keys=True,separators=(',',':')).encode()).hexdigest()
    require(identity==manifest['candidate_id'],'key does not join the embedded canary identity')
    for record,status,field in [(qualified['loader_tests'],'PASS_H0_ACTUAL_ARM64_LOADER','qualification_sha256'),
                                (qualified['entry_tests'],'PASS_H0_QEMU_ACTUAL_EXCEPTION_LEVELS','entry_vm_sha256')]:
        value=read(unchanged(record))
        require(value['status']==status and value['loader_sha256']==loader['loader']['sha256'] and
                package[field]==record['sha256'] and value['device_actions']==0,'mainline actual-blob tests differ')
    require(review['status']=='PASS_H0_SOURCE_BOUND_LOADER_ENTRY_AND_BOOT_PACKAGE' and not review['findings'],
            'loader/package independent review absent')
    reviewed={r['path']:r for r in review['artifact_and_raw_evidence_pins']}
    for receipt in (qualified['loader'],qualified['package'],qualified['init_manifest'],qualified['loader_tests'],qualified['entry_tests']):
        key=str(Path(receipt['path']).relative_to(ROOT))
        require(key in reviewed and all(reviewed[key][k]==receipt[k] for k in ('size','sha256')),
                'candidate evidence was not covered by retained entry review')
    require(('retained_marker' in image)==('retained_marker' in loader)==('retained_marker' in loader['kernel']),
            'instrumented loader lacks its marker admission')
    if 'retained_marker' in image:
        marked=marker_binding(image,manifest,loader)
        for receipt in (image['retained_marker'],marked['config'],marked['tests'],marked['entry_vm']):
            path=str(Path(receipt['path']).relative_to(ROOT))
            require(path in reviewed and all(reviewed[path][k]==receipt[k] for k in ('size','sha256')),
                    'retained marker evidence lacks exact independent coverage')
    for receipt in image['runtime_sources'].values():unchanged(receipt)
    require(image['runtime_sources']=={
        'loader':dict(path=loader['loader']['path'],size=loader['loader']['size'],sha256=loader['loader']['sha256']),
        'kernel':dict(path=loader['kernel']['image'],size=loader['kernel']['file_size'],sha256=loader['kernel']['sha256']),
        'init':pin(Path(manifest['init']['path']),maximum=4*1024*1024),
        'initramfs':manifest['initramfs'],'dtb':pin(Path(manifest['dtb']['path']))},'mainline runtime identity differs')
    require(image['runtime_sources']['init']['sha256']==manifest['init']['sha256'] and
            image['runtime_sources']['dtb']['sha256']==manifest['dtb']['sha256'],'canary measurements differ')
    if artifact_bytes:
        with transport.pin_boot_only_ap(Path(image['ap']['path']),label='mainline RAM candidate',
                expected_size=image['ap']['size'],expected_sha256=image['ap']['sha256']) as ap:
            require(transport.boot_only_member_receipt(ap,label='mainline RAM candidate')==image['member'],
                    'mainline AP member differs')
    return manifest


def marker_codec():
    # A stopped owner may probe historical USB evidence before selecting A.
    # Candidate-only code must be reviewed before import, and an unavailable
    # decoder is an ordinary failed candidate validation, never a new recovery
    # prerequisite or an uncaught import failure.
    from s22plus_mainline_task_v1 import capability
    capability(ROOT)
    try:
        from mainline.s22plus_canary_h0 import retained_marker
    except (ImportError,SyntaxError) as error:
        raise ValueError('reviewed marker codec is unavailable') from error
    return retained_marker


def marker_binding(image,manifest,loader):
    marker=marker_codec()
    value=read(unchanged(image['retained_marker']))
    require(set(value)=={'schema','status','config','tests','entry_vm','device_actions'} and
            value['schema']=='s22plus-mainline-marker-qualification-v1' and
            value['status']=='PASS_H0_MAINLINE_RETAINED_MARKER' and value['device_actions']==0,
            'marker qualification shape differs')
    require(value['config']==loader['retained_marker']['config'],'loader marker config differs')
    config=read(unchanged(value['config']));key=unchanged(image['key'],32).read_bytes()
    marker.validate(config,manifest['candidate_id'],key)
    tests=read(unchanged(value['tests']));vm=read(unchanged(value['entry_vm']))
    for result,status in ((tests,'PASS_H0_ACTUAL_RETAINED_MARKERS'),(vm,'PASS_H0_ACTUAL_EL_RETAINED_MARKERS')):
        require(result['status']==status and result['config']==value['config'] and
                result['loader_sha256']==image['runtime_sources']['loader']['sha256'] and
                result['kernel_sha256']==image['runtime_sources']['kernel']['sha256'] and
                result['device_actions']==0 and result['physical_retention_proved'] is False,
                'actual marker artifact tests differ')
    require(vm['qualification_sha256']==value['tests']['sha256'],'marker actual EL test input differs')
    if marker.c_stages(config):
        require(tests.get('mmu_on',{}).get('status')=='PASS_H0_ACTUAL_EARLY_C' and
                vm.get('mmu_on',{}).get('status')=='PASS_H0_ACTUAL_KERNEL_MMU_MARKERS' and
                tests['mmu_on']['kernel_sha256']==vm['mmu_on']['kernel_sha256']==
                    image['runtime_sources']['kernel']['sha256'],
                'C marker lacks actual C and MMU-on kernel qualification')
    if marker.version(config) in (3,4,5):
        require(vm['mmu_on'].get('post_paging_no_linear_alias_proved') is True and
                vm['mmu_on'].get('qualified_c_stages')==tests['mmu_on'].get('qualified_c_stages')==list(marker.c_stages(config)),
                'later C marker lacks post-paging no-map and two-site qualification')
    if marker.version(config) in (4,5):
        stages=list(marker.c_stages(config))
        cases=vm['mmu_on'].get('cases',[])
        require(vm['mmu_on'].get('late_fixmap_proved') is True and cases and
                all(r.get('late_context_stages')==r.get('no_linear_alias_stages')==stages and
                    r.get('late_fixmap_proved') is True and r.get('first_c_returned') is True and
                    r.get('mapping_slots_restored') is True for r in cases),
                'late marker lacks both contexts, aliases or cleanup')
        normal={r['case']:r for r in cases if r.get('case') in ('normal','normal-el1')}
        require(set(normal)=={'normal','normal-el1'} and
                normal['normal'].get('actual_c_el')==2 and normal['normal-el1'].get('actual_c_el')==1 and
                all(r.get('temporary_mapping_attribute_stages')==stages for r in normal.values()),
                'late marker lacks actual EL1/EL2 mapping attributes at both sites')
        if marker.version(config)==5:
            expected=[dict(stage=s,initial_task=True,boot_cpu=0,online_cpus=1,
                           preempt_count_low32=1,irq_masked=s==9) for s in stages]
            require(vm['mmu_on'].get('bootstrap_context_proved') is True and
                    all(r.get('bootstrap_contexts')==expected for r in cases),
                    'V5 marker lacks exact bootstrap task/CPU/preemption/IRQ context')
    source=read(unchanged(loader['retained_marker']['kernel_source']))
    require(source['config']==value['config'] and source['init_manifest']['sha256']==
            pin(Path(loader['initramfs_manifest']))['sha256'],'kernel marker provenance differs')
    return value


def qualify(package_dir,loader_dir,output,*,loader_qualification,entry_vm,marker_qualification=None):
    """Revalidate existing immutable artifacts, without building or contacting a device."""
    package_dir,loader_dir,output=[Path(p).resolve() for p in (package_dir,loader_dir,output)]
    require(output.is_relative_to(ROOT/'workspace/private') and not output.exists(),'fresh private qualification required')
    package=read(package_dir/'result.json');loader=read(loader_dir/'result.json')
    base=loader_dir.parent
    loader_tests=pin(Path(loader_qualification).resolve()/'result.json')
    entry_tests=pin(Path(entry_vm).resolve()/'result.json')
    require(package['qualification_sha256']==loader_tests['sha256'] and
            package['entry_vm_sha256']==entry_tests['sha256'],
            'explicit test receipts differ from the packaged qualification')
    manifest=read(Path(loader['initramfs_manifest']))
    ap=package['copies'][0]['ap']
    with transport.pin_boot_only_ap(Path(ap['path']),label='mainline H0 image',
            expected_size=ap['size'],expected_sha256=ap['sha256']) as bound:
        member=transport.boot_only_member_receipt(bound,label='mainline H0 image')
        compressed=transport.read_boot_only_member(bound,label='mainline H0 image')
    data=boot.decompress_lz4_stream_python(compressed,maximum=128*1024*1024)
    parsed=boot.parse_boot_v4(data)
    require(len(data)==96*1024*1024 and parsed.kernel==Path(loader['loader']['path']).read_bytes(),
            'actual AP does not contain qualified loader')
    runtime={'loader':pin(Path(loader['loader']['path']),maximum=128*1024*1024),
             'kernel':pin(Path(loader['kernel']['image']),maximum=128*1024*1024),
             'init':pin(Path(manifest['init']['path']),maximum=4*1024*1024),
             'initramfs':manifest['initramfs'],'dtb':pin(Path(manifest['dtb']['path']))}
    image=dict(schema='s22plus-mainline-image-v1',profile=PROFILE,namespace=NAMESPACE,version=VERSION,
        run_id_hex=manifest['candidate_id'][:32],ap=ap,member=member,key=pin(Path(manifest['key_path']),maximum=32),
        runtime_sources=runtime)
    if marker_qualification is not None:image['retained_marker']=pin(Path(marker_qualification).resolve())
    record=dict(schema='s22plus-mainline-qualification-v1',status='PASS_H0_MAINLINE_CANDIDATE',image=image,
        package=pin(package_dir/'result.json'),loader=pin(loader_dir/'result.json'),
        init_manifest=pin(Path(loader['initramfs_manifest'])),
        entry_review=pin(base/'review/independent-loader-entry-package-review-1.json'),
        loader_tests=loader_tests,entry_tests=entry_tests,device_actions=0)
    output.mkdir(mode=0o700,parents=True)
    image=dict(image,qualification=publish(output/'qualification.json',record))
    image_binding(image,artifact_bytes=True)
    return publish(output/'image.json',image)

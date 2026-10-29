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
REVIEW='workspace/public/src/device-action/bindings/s22plus_mainline_ram_v1_review.json'
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


def qualify(package_dir,loader_dir,output):
    """Revalidate existing immutable artifacts, without building or contacting a device."""
    package_dir,loader_dir,output=[Path(p).resolve() for p in (package_dir,loader_dir,output)]
    require(output.is_relative_to(ROOT/'workspace/private') and not output.exists(),'fresh private qualification required')
    package=read(package_dir/'result.json');loader=read(loader_dir/'result.json')
    base=loader_dir.parent
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
    output.mkdir(mode=0o700,parents=True)
    record=dict(schema='s22plus-mainline-qualification-v1',status='PASS_H0_MAINLINE_CANDIDATE',image=image,
        package=pin(package_dir/'result.json'),loader=pin(loader_dir/'result.json'),
        init_manifest=pin(Path(loader['initramfs_manifest'])),
        entry_review=pin(base/'review/independent-loader-entry-package-review-1.json'),
        loader_tests=pin(base/'qualification-4/result.json'),entry_tests=pin(base/'entry-vm-2/result.json'),device_actions=0)
    image=dict(image,qualification=publish(output/'qualification.json',record))
    image_binding(image,artifact_bytes=True)
    return publish(output/'image.json',image)

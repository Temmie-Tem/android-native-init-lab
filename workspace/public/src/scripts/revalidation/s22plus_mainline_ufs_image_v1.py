"""Exact UFS-link candidates; each keeps its own retained artifact review."""
from pathlib import Path
import gzip
import hashlib
import json

import s22plus_mainline_profile_v1 as profile
from s22plus_native_records_v3 import pin, publish, read, require

ROOT = profile.ROOT
BASE = ROOT/'workspace/private/outputs/s22plus-mainline-ml030-dwell-link-h0-20261105-1'
POLICY = 'docs/operations/S22PLUS_MAINLINE_UFS_LINK_V1.md'
SCHEMA = 's22plus-mainline-debian-ufs-link-ram-v1'
AP = '44ea04f4f7a9aaa09e3ad4e86e5162c08eb6aaba6d4bf5b94632feb95d9d7aba'
KERNEL = '19fc260fc880731167d3612804e34a0ea64c48efb1a46bdf7aee803d35a2bc3c'
MODULE = '7859073e9abfef8cb93202683046bec2878b3210c4703fc36eb6a1474a6615f8'
ARCHIVE = '3c829b6137b10745ad1b0a3d16c227d498f96dbf0ca4c1495058033244a04631'
LOADER = '6be55da7a4d53f18ad6c9129f66bcf24843117662a16b54dcfc03f5ae0b979ed'
MANIFEST = BASE/'init-provisional-5/result.json'
RETAINED_REVIEW = BASE/'independent-h0-guest-close-5.json'
EVIDENCE_SHA = '58ace1c8e7afc1ab43150282857e757996d5451816fc658240be3bbec93b1a5a'
FOLLOWUP_BASE = ROOT/'workspace/private/outputs/s22plus-mainline-ml031-attach-dwell-h0-20261107-1'
FOLLOWUP_POLICY = 'docs/operations/S22PLUS_MAINLINE_UFS_LINK_FOLLOWUP_V1.md'
CUE_REFRESH_BASE = ROOT/'workspace/private/outputs/s22plus-mainline-ml032-cue-refresh-h0-20261109-1'
CUE_REFRESH_POLICY = 'docs/operations/S22PLUS_MAINLINE_UFS_LINK_CUE_REFRESH_V1.md'
TIMED_ATTACH_BASE = ROOT/'workspace/private/outputs/s22plus-mainline-ml033-timed-attach-h0-20261110-1'
TIMED_ATTACH_POLICY = 'docs/operations/S22PLUS_MAINLINE_UFS_LINK_TIMED_ATTACH_V1.md'
DECLARATIONS = {
    'ML030': dict(ap=AP, archive=ARCHIVE, loader=LOADER, policy=POLICY,
        schema='s22plus-ml030-qualification-v1', evidence_sha256=EVIDENCE_SHA,
        paths=dict(manifest=MANIFEST, package=BASE/'package-5/result.json', loader=BASE/'loader-5/result.json',
            component=BASE/'transport-component-4/result.json', kernel=BASE/'transport-build-4/guard-result.json',
            review=RETAINED_REVIEW, evidence=BASE/'final-evidence-check-5.json',
            loader_tests=BASE/'loader-tests-5/result.json', entry_tests=BASE/'loader-entry-vm-5/result.json')),
    'ML031': dict(ap='64131da9daa9358009065f998748a56c7b24a607f5a028ee990cd7c2660027a3',
        archive='c911585477282395579c4d21067baf1ff8b3c6d4aed6107dfb8040f12f4388db',
        loader='752a05d99cf7a9ec9f3a16b12d102bf22ce5537f02bbb741c0b39389e9d85e24',
        policy=FOLLOWUP_POLICY, schema='s22plus-ml031-qualification-v1',
        review_sha256='c657cd199d2b041e4a1e0cb2b3899f530bc9339942767bb03b68221fdef6131f',
        inputs_sha256='e2b69a7ca76858516bf2ae5312d8799749eadc5e73799ce170ab2170686b7277',
        evidence_sha256='5070ede193cc08e14af2486cef74c4464f1e065c2e058f8655c6156c728a92dd',
        paths=dict(manifest=FOLLOWUP_BASE/'init-physical-1/result.json',
            package=FOLLOWUP_BASE/'package-1/result.json', loader=FOLLOWUP_BASE/'loader-1/result.json',
            component=BASE/'transport-component-4/result.json', kernel=BASE/'transport-build-4/guard-result.json',
            review=FOLLOWUP_BASE/'review/independent-review-1.json', evidence=FOLLOWUP_BASE/'qualification-1.json',
            loader_tests=FOLLOWUP_BASE/'loader-tests-1/result.json', entry_tests=FOLLOWUP_BASE/'loader-entry-vm-1/result.json')),
    'ML032': dict(ap='797e10947ba7706367bc04ff0ab170fe808956839235420505ddc42fa2a04f92',
        archive='0ab1ba484aba5dffa171c963feb9718824eee46c726576ef8bfa5999d44c2808',
        loader='b15aeab452d4c88345f13b92cc9c50865906c10359af49a2d96e0f40f7ba066f',
        policy=CUE_REFRESH_POLICY, schema='s22plus-ml032-qualification-v1',
        review_sha256='f05a06429e00e2583dc9648b7a4ca803fae0f847d4aa1e23e31fb4be836481b8',
        inputs_sha256='a9e9393d723a48f0656315281b062a7ea00aeb9a39206f3e649f76d11f026cdc',
        evidence_sha256='af0bd23bee739682cff9f13eaa627fa39bd6feeda114e02a0c87735a3d967b14',
        paths=dict(manifest=CUE_REFRESH_BASE/'init-physical-1/result.json',
            package=CUE_REFRESH_BASE/'package-1/result.json', loader=CUE_REFRESH_BASE/'loader-1/result.json',
            component=BASE/'transport-component-4/result.json', kernel=BASE/'transport-build-4/guard-result.json',
            review=CUE_REFRESH_BASE/'review/independent-review-1.json', evidence=CUE_REFRESH_BASE/'qualification-1.json',
            loader_tests=CUE_REFRESH_BASE/'loader-tests-1/result.json', entry_tests=CUE_REFRESH_BASE/'loader-entry-vm-1/result.json')),
    'ML033': dict(ap='2b4582480df278eb9d704e7356d9c19111d5130764afd968ca644b079ca4ad44',
        archive='b87ee934f39329305d36d027f1721c19cf84f698afb7329b7d0b5ab024aa00a6',
        loader='0f4278b2739eadb7bb6b7f7b36343dfa214f97dcef08ea6335715bcea1863a89',
        policy=TIMED_ATTACH_POLICY, schema='s22plus-ml033-qualification-v1',
        review_sha256='ead43fc443d190c8172acce60ca760e4674e5122edabec5d2fb3c8c3a24b8503',
        inputs_sha256='1939dcab33c87019c708c038a8ffb627a15a1285a9950b9c2ad5103cfdb13a2c',
        evidence_sha256='7d30b921f7544a1e8f7e64a7ed5e0ec80a91032a1fb8132d4618be958c499575',
        paths=dict(manifest=TIMED_ATTACH_BASE/'init-physical-1/result.json',
            package=TIMED_ATTACH_BASE/'package-1/result.json', loader=TIMED_ATTACH_BASE/'loader-1/result.json',
            component=BASE/'transport-component-4/result.json', kernel=BASE/'transport-build-4/guard-result.json',
            review=TIMED_ATTACH_BASE/'review/independent-review-1.json', evidence=TIMED_ATTACH_BASE/'qualification-1.json',
            loader_tests=TIMED_ATTACH_BASE/'loader-tests-1/result.json', entry_tests=TIMED_ATTACH_BASE/'loader-entry-vm-1/result.json')),
}


def selection(image):
    matches=[name for name,value in DECLARATIONS.items() if value['ap']==image.get('ap',{}).get('sha256')]
    require(len(matches)==1, 'unknown or ambiguous UFS-link candidate')
    return matches[0], DECLARATIONS[matches[0]]


def policy_for(image):
    return selection(image)[1]['policy']


def checked(receipt):
    return read(profile.unchanged(receipt))


def runtime(manifest,*,candidate='ML030'):
    from mainline.s22plus_canary_h0 import debian_ram as d
    require(candidate in DECLARATIONS, 'unselected UFS-link runtime')
    declaration=DECLARATIONS[candidate]
    require(manifest['debian_ram']['schema']==SCHEMA and manifest['vm'] is False and
            manifest['physical_admitted'] is False and manifest['status']=='H0_ML030_FIXED_RAM_ARCHIVE',
            'ML030 physical archive declaration')
    value=manifest['debian_ram']
    require(set(value)=={'schema','package_lock','observer','inittab_sha256','members','module'},'ML030 runtime fields')
    root=Path(manifest['init']['path']).parent.parent.parent
    files={}
    for name,(package,expected) in d.MEMBERS.items():
        data=(root/name).read_bytes()
        require(hashlib.sha256(data).hexdigest()==expected and value['members'][name]==
                dict(package=package,sha256=expected,size=len(data)), 'ML030 fixed package file')
        files[name]=data
    require(set(value['members'])==set(d.MEMBERS) and manifest['init']==d.pin(root/'usr/sbin/init'), 'ML030 PID1 closure')
    lock=checked(value['package_lock'])
    require(lock['verdict']=='PASS_SIGNED_PACKAGE_CLOSURE_H0' and lock['count']==4 and len(lock['packages'])==4 and
            {r['package']:(r['version'],r['sha256']) for r in lock['packages']}==d.PACKAGES and
            all(r['architecture']=='arm64' for r in lock['packages']), 'ML030 signed packages')
    module=root/'usr/lib/g0q_ml030.ko'
    require(value['module']==d.pin(module) and value['module']['sha256']==MODULE and
            value['observer']==d.pin(root/d.OBSERVER), 'ML030 module/observer file')
    files.update({d.OBSERVER:profile.unchanged(value['observer']).read_bytes(),
                  'usr/lib/g0q_ml030.ko':module.read_bytes(),'etc/inittab':(root/'etc/inittab').read_bytes()})
    require(files['etc/inittab']==d.INITTAB and value['inittab_sha256']==hashlib.sha256(d.INITTAB).hexdigest(),
            'ML030 once-only inittab')
    spec=({**d.MEMBERS,'usr/lib/g0q_ml030.ko':None},d.INITTAB,d.DIRS,d.LINKS,
          {'etc/inittab':0o644,'usr/lib/g0q_ml030.ko':0o400})
    archive=profile.unchanged(manifest['initramfs']).read_bytes()
    require(manifest['initramfs']['sha256']==declaration['archive'] and archive==gzip.compress(d.pack(files,False,specification=spec),mtime=0),
            'ML030 canonical CPIO differs')
    producer=read(Path(manifest['initramfs']['path']).parent/'producer.json')
    key=Path(manifest['key_path']).read_bytes()
    recipe=producer['recipe']
    require(len(key)==32 and recipe==dict(schema=SCHEMA,vm=False,inputs=manifest['inputs'],
            key_digest=hashlib.sha256(key).hexdigest()) and hashlib.sha256(json.dumps(recipe,
            sort_keys=True,separators=(',',':')).encode()).hexdigest()==manifest['candidate_id'], 'ML030 key/recipe binding')
    return value


def binding(image,*,artifact_bytes=False):
    candidate,declaration=selection(image)
    paths=declaration['paths']
    keys={'schema','profile','namespace','version','run_id_hex','ap','member','key','qualification',
          'runtime_sources','ufs_link','debian_ram','download_return'}
    require(set(image)==keys and image['schema']=='s22plus-mainline-image-v1' and image['ufs_link'] is True and
            image['profile']==profile.PROFILE and image['namespace']==profile.NAMESPACE and image['version']==profile.VERSION,
            'ML030 image shape')
    bundle=checked(image['qualification'])
    require(set(bundle)=={'schema','manifest','package','loader','component','kernel','review','evidence','loader_tests','entry_tests'} and
            bundle['schema']==declaration['schema'] and
            image['debian_ram']==image['download_return']==image['qualification'], 'ML030 qualification join')
    require(all(bundle[name]['path']==str(path) for name,path in paths.items()), 'UFS-link retained artifact identity')
    manifest=checked(bundle['manifest']); package=checked(bundle['package']); loader=checked(bundle['loader'])
    component=checked(bundle['component']); kernel=checked(bundle['kernel']); review=checked(bundle['review'])
    require(review['status']=='PASS_GO' and review['findings']==[] and review['device_actions']==0 and
            bundle['evidence']['sha256']==declaration['evidence_sha256'],
            'ML030 independent H0 coverage')
    evidence=checked(bundle['evidence'])
    if candidate=='ML030':
        require(evidence['status']=='PASS_H0_REDERIVED_FIVE_RAW_GUEST_CASES', 'ML030 raw qualification differs')
        reviewed={r['path']:r['sha256'] for r in review['raw']}
        for name in ('manifest','package','component','kernel','evidence'):
            require(reviewed.get(bundle[name]['path'])==bundle[name]['sha256'], 'ML030 H0 review lacks artifact')
    else:
        require(bundle['review']['sha256']==declaration['review_sha256'] and
                review['schema']==f's22plus-{candidate.lower()}-independent-h0-candidate-cue-scope-review-v1' and
                review['inputs']['sha256']==declaration['inputs_sha256'] and
                review['grants_device_authority'] is False, f'{candidate} retained independent review differs')
        inputs=checked(review['inputs'])
        reviewed={r['path']:r['sha256'] for r in inputs['evidence']}
        for name in ('manifest','package','loader','evidence','loader_tests','entry_tests'):
            require(reviewed.get(bundle[name]['path'])==bundle[name]['sha256'], f'{candidate} H0 review lacks artifact')
        require(evidence['status']==f'PASS_H0_{candidate}_ARTIFACT_AND_PROTOCOL_QUALIFICATION' and
                evidence['candidate']==candidate and evidence['device_actions']==0 and
                evidence['physical_manifest']==bundle['manifest'] and evidence['package']==bundle['package'] and
                evidence['loader']==loader['loader'] and evidence['loader_tests']==bundle['loader_tests'] and
                evidence['entry_tests']==bundle['entry_tests'], f'{candidate} H0 qualification joins differ')
        retained=checked(evidence['retained_review'])
        require(evidence['retained_review']['path']==str(RETAINED_REVIEW) and
                retained['status']=='PASS_GO' and retained['findings']==[] and retained['device_actions']==0,
                f'{candidate} retained machinery review differs')
        machinery={r['path']:r['sha256'] for r in retained['raw']}
        for name in ('component','kernel'):
            require(machinery.get(bundle[name]['path'])==bundle[name]['sha256'], f'{candidate} machinery provenance differs')
    require(package['status']=='H0_BOOT_V4_PACKAGED_NOT_DEVICE_ADMITTED' and package['activation'] is False and
            package['device_actions']==0 and len(package['copies'])==2 and
            all(package['copies'][0][name]['sha256']==package['copies'][1][name]['sha256'] for name in ('ap','boot')),
            'ML030 double package differs')
    require(package['copies'][0]['ap']==image['ap'] and image['ap']['sha256']==declaration['ap'] and
            package['loader_sha256']==loader['loader']['sha256']==declaration['loader'] and
            loader['kernel']['sha256']==kernel['sha256']==component['selected_kernel']==KERNEL and
            component['module_sha256']==MODULE and loader['initramfs_manifest']==str(paths['manifest']) and
            'retained_marker' not in loader and 'retained_marker' not in kernel,
            'ML030 exact linked artifact join')
    for name,status,key in (('loader_tests','PASS_H0_ACTUAL_ARM64_LOADER','qualification_sha256'),
                            ('entry_tests','PASS_H0_QEMU_ACTUAL_EXCEPTION_LEVELS','entry_vm_sha256')):
        result=checked(bundle[name])
        require(result['status']==status and result['device_actions']==0 and result['loader_sha256']==declaration['loader'] and
                package[key]==bundle[name]['sha256'], 'ML030 actual loader checks')
    value=runtime(manifest,candidate=candidate)
    kernel_file=pin(Path(kernel['image']),maximum=128*1024*1024)
    require(kernel_file['sha256']==KERNEL and kernel_file['size']==kernel['file_size'], 'ML030 kernel bytes differ')
    if candidate!='ML030':
        require(evidence['kernel']==kernel_file and evidence['module']['sha256']==MODULE,
                f'{candidate} qualified runtime machinery differs')
    expected={'loader':loader['loader'],'kernel':kernel_file,
              'init':manifest['init'],'initramfs':manifest['initramfs'],'dtb':manifest['dtb'],'observer':value['observer'],
              'module':value['module']}
    require(image['runtime_sources']==expected and image['key']==pin(Path(manifest['key_path']),maximum=32) and
            image['run_id_hex']==manifest['candidate_id'][:32] and manifest['port']==47649,
            'ML030 runtime/key identity')
    for receipt in expected.values():profile.unchanged(receipt)
    if artifact_bytes:
        with profile.transport.pin_boot_only_ap(Path(image['ap']['path']),label='ML030 candidate',
                expected_size=image['ap']['size'],expected_sha256=declaration['ap']) as ap:
            require(profile.transport.boot_only_member_receipt(ap,label='ML030 candidate')==image['member'], 'ML030 boot member')
    else:profile.unchanged(image['ap'])
    return manifest


def prepare(output,*,candidate='ML030'):
    require(candidate in DECLARATIONS, 'unselected UFS-link preparation')
    declaration=DECLARATIONS[candidate]
    output=output.resolve();require(output.is_relative_to(ROOT/'workspace/private') and not output.exists(),'fresh private image output')
    output.mkdir(mode=0o700)
    paths=declaration['paths']
    bundle={name:pin(path) for name,path in paths.items()}
    receipt=publish(output/'qualification.json',dict(schema=declaration['schema'],**bundle))
    manifest=read(paths['manifest']);loader=read(paths['loader']);kernel=read(paths['kernel']);ap=read(paths['package'])['copies'][0]['ap']
    with profile.transport.pin_boot_only_ap(Path(ap['path']),label='ML030 candidate',expected_size=ap['size'],expected_sha256=declaration['ap']) as fd:
        member=profile.transport.boot_only_member_receipt(fd,label='ML030 candidate')
    runtime_sources=dict(loader=loader['loader'],kernel=pin(Path(kernel['image']),maximum=128*1024*1024),
        init=manifest['init'],initramfs=manifest['initramfs'],dtb=manifest['dtb'],observer=manifest['debian_ram']['observer'],
        module=manifest['debian_ram']['module'])
    image=dict(schema='s22plus-mainline-image-v1',profile=profile.PROFILE,namespace=profile.NAMESPACE,version=profile.VERSION,
               run_id_hex=manifest['candidate_id'][:32],ap=ap,member=member,key=pin(Path(manifest['key_path']),maximum=32),
               qualification=receipt,debian_ram=receipt,download_return=receipt,ufs_link=True,runtime_sources=runtime_sources)
    binding(image,artifact_bytes=True)
    return publish(output/'image.json',image)

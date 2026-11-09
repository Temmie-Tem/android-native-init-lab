"""Machine-qualified key-only UFS candidates; shared capability, no live adoption.

Fresh qualification performs producer reproduction and full byte joins once.
Session guards only revalidate immutable pins and declarations. Old candidates
continue through their exact v1 admission and retain their original evidence.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

import s22plus_mainline_profile_v1 as profile
import s22plus_mainline_task_v1 as tasks
from s22plus_native_records_v3 import pin, publish, read, require

ROOT = profile.ROOT
CANDIDATE_SCHEMA = 's22plus-mainline-ufs-candidate-v2'
QUALIFICATION_SCHEMA = 's22plus-mainline-ufs-qualification-v2'
FIXED_FIELDS = {'report_version','kernel','component','dtb','config','network','original_boot',
                'loader_contract','input_template','observer_build','observer_auxiliary'}
CANDIDATE_FIELDS = {'schema','name','capability','capability_review','manifest','producer',
                    'loader','package','loader_tests','entry_tests'}
LOADER_CONTRACT_FIELDS = ('configuration','source_commit','patch_sha256','entry_patch_sha256',
                          'source_ram_ranges','initial_abl_source_and_stub_overlap')
IMAGE_FIELDS = {'schema','profile','namespace','version','run_id_hex','ap','member','key',
                'qualification','runtime_sources','ufs_link','debian_ram','download_return',
                'candidate','capability','capability_review'}


def checked(receipt):
    return read(profile.unchanged(receipt))


def selected_metadata(candidate):
    return dict(schema=tasks.IMAGE_V2, capability=candidate['capability'],
                capability_review=candidate['capability_review'])


def artifact_pin(path,sha256,size=None):
    path=Path(path)
    receipt=dict(path=str(path),size=path.stat().st_size if size is None else size,sha256=sha256)
    profile.unchanged(receipt)
    return receipt


def auxiliary_inputs():
    """Fresh qualification only: GCC also declares a linker plugin/wrapper.

    Original producer receipts are not backfilled. This additional measured
    closure belongs to the new complete-reproduction proof.
    """
    env=dict(PATH='/usr/bin:/bin',LC_ALL='C',SOURCE_DATE_EPOCH='0')
    compiler=Path(shutil.which('aarch64-linux-gnu-gcc',path=env['PATH'])).resolve(strict=True)
    paths={compiler}
    for option in ('-print-file-name=liblto_plugin.so','-print-prog-name=lto-wrapper','-print-file-name=specs'):
        value=subprocess.check_output([compiler,option],env=env,text=True).strip()
        if option=='-print-file-name=specs' and value=='specs':continue
        path=Path(value)
        require(path.is_absolute() and path.is_file(),'compiler auxiliary input not found')
        paths.add(path.resolve(strict=True))
    for path in tuple(paths):
        result=subprocess.run(['/usr/bin/ldd',path],env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        for word in result.stdout.split():
            if word.startswith('/') and Path(word).is_file():paths.add(Path(word).resolve(strict=True))
    specs=subprocess.check_output([compiler,'-dumpspecs'],env=env)
    return dict(compiler=pin(compiler,maximum=128*1024**2),
                inputs=[pin(path,maximum=128*1024**2) for path in sorted(paths)],
                specs_sha256=hashlib.sha256(specs).hexdigest())


def fixed_binding(cap):
    fixed = cap['fixed']
    require(set(fixed)==FIXED_FIELDS and type(fixed['report_version']) is int and
            fixed['report_version']==4, 'v2 fixed capability fields or report mode')
    kernel=checked(fixed['kernel']);component=checked(fixed['component'])
    require(component['status']=='BUILT_H0_COLD_LINK_COMPONENT' and
            component['pre_effect_return'] is True and component['report_version']==4 and
            component['physical_admitted'] is False and component['device_actions']==0 and
            component['selected_kernel']==kernel['sha256'] and
            component['transport']==kernel['transport_sha256'], 'v2 fixed module/kernel mismatch')
    artifact_pin(kernel['image'],kernel['sha256'],kernel['file_size'])
    artifact_pin(component['module_path'],component['module_sha256'])
    for key in ('dtb','config','network','original_boot'):
        profile.unchanged(fixed[key])
    require(fixed['config']['sha256']==kernel['config_sha256'] and
            set(fixed['loader_contract'])==set(LOADER_CONTRACT_FIELDS), 'v2 fixed loader/config scope')
    require(type(fixed['observer_build']) is list and fixed['observer_build'] and
            len({r['path'] for r in fixed['observer_build']})==len(fixed['observer_build']),
            'v2 compiler input closure')
    for row in fixed['observer_build']:
        profile.unchanged(row)
    auxiliary=fixed['observer_auxiliary']
    require(set(auxiliary)=={'compiler','inputs','specs_sha256'} and
            auxiliary['compiler'] in fixed['observer_build'] and
            type(auxiliary['specs_sha256']) is str and re.fullmatch('[0-9a-f]{64}',auxiliary['specs_sha256']) and
            auxiliary['inputs'] and len({r['path'] for r in auxiliary['inputs']})==len(auxiliary['inputs']),
            'v2 compiler auxiliary closure')
    for row in auxiliary['inputs']:profile.unchanged(row)
    # These are immutable raw/source records reviewed once with this capability,
    # not a label that promotes a prior physical run or stale test to new proof.
    evidence=cap['evidence']
    require(type(evidence) is list and evidence and
            len({r['path'] for r in evidence})==len(evidence), 'v2 reused evidence closure')
    for row in evidence:
        profile.unchanged(row)
    return fixed,kernel,component


def candidate_binding(candidate):
    require(set(candidate)==CANDIDATE_FIELDS and candidate['schema']==CANDIDATE_SCHEMA and
            type(candidate['name']) is str and re.fullmatch('[a-z0-9][a-z0-9-]{0,63}',candidate['name']),
            'v2 candidate declaration')
    tasks.capability(ROOT,image=selected_metadata(candidate))
    cap=checked(candidate['capability']);fixed,kernel,component=fixed_binding(cap)
    for key in ('manifest','producer','loader','package','loader_tests','entry_tests'):
        profile.unchanged(candidate[key])
    return cap,fixed,kernel,component


def input_template(manifest):
    """Replace only the two deterministic generated input locations."""
    folder=Path(manifest['initramfs']['path']).parent
    slots={str(folder/'observer.c'):'observer_source',
           manifest['debian_ram']['package_lock']['path']:'package_lock'}
    require(len(slots)==2, 'v2 distinct generated input paths')
    rows=[dict(row,path='$'+slots[row['path']]) if row['path'] in slots else row
          for row in manifest['inputs']]
    require(sum(row['path'].startswith('$') for row in rows)==2, 'v2 generated input slots missing')
    return rows


def runtime_binding(candidate,fixed,component):
    from s22plus_mainline_ufs_image_v1 import _runtime
    manifest=checked(candidate['manifest']);producer=checked(candidate['producer'])
    folder=Path(manifest['initramfs']['path']).parent
    require(set(manifest)=={'status','vm','candidate_id','key_path','network','port','inputs','init',
                'initramfs','kernel_release','dtb','initrd_address','debian_ram','device_actions',
                'physical_admitted','report_version','pre_effect_return'} and
            Path(candidate['manifest']['path'])==folder/'result.json' and
            Path(candidate['producer']['path'])==folder/'producer.json' and
            manifest.get('pre_effect_return') is True and manifest.get('report_version')==4 and
            manifest['kernel_release']==component['vermagic'].split()[0] and
            manifest['device_actions']==0 and manifest['port']==47649 and
            manifest['initrd_address']==0xb6915000 and manifest['dtb']==fixed['dtb'],
            'v2 runtime mode/DT/placement differs')
    require(input_template(manifest)==fixed['input_template'], 'v2 fixed recipe inputs changed')
    for row in manifest['inputs']:profile.unchanged(row)
    value=_runtime(manifest,dict(module=component['module_sha256'],
                                archive=manifest['initramfs']['sha256'],report_version=4))
    require(producer['provenance']['schema']=='s22plus-observer-build-inputs-v1' and
            producer['provenance']['fixed']==fixed['observer_build'], 'v2 observer toolchain changed')
    for name in ('dependency','log'):profile.unchanged(producer['provenance'][name])
    for row in producer['provenance']['generated']:profile.unchanged(row)
    # The only variable network values are derived from this exact recipe/key.
    identity=bytes.fromhex(manifest['candidate_id']);net=checked(fixed['network'])
    net.update(device_mac='02:'+':'.join(f'{n:02x}' for n in identity[:5]),
               host_mac='02:'+':'.join(f'{n:02x}' for n in identity[5:10]),
               serial='g0q-'+identity.hex()[:20],udc='a600000.usb')
    require(manifest['network']==net, 'v2 network exceeds derived identity slots')
    return manifest,producer,value


def artifact_binding(candidate,fixed,kernel,manifest):
    loader=checked(candidate['loader']);package=checked(candidate['package'])
    require(loader['status']=='H0_LOADER_BUILT_RUNTIME_PLACEMENT_GUARDED' and
            loader['device_actions']==0 and loader['physical_entry']=='NOT_ADMITTED_H0_ONLY' and
            {k:loader[k] for k in LOADER_CONTRACT_FIELDS}==fixed['loader_contract'] and
            loader['kernel']['image']==kernel['image'] and
            loader['kernel']['sha256']==kernel['sha256'] and
            loader['kernel']['config_sha256']==fixed['config']['sha256'] and
            loader['initramfs_manifest']==candidate['manifest']['path'] and
            'retained_marker' not in loader and 'entry_park' not in loader,
            'v2 loader capability/manifest mismatch')
    require(package['status']=='H0_BOOT_V4_PACKAGED_NOT_DEVICE_ADMITTED' and
            package['activation'] is False and package['device_actions']==0 and
            package['loader_sha256']==loader['loader']['sha256'] and
            package['original_a_sha256']==fixed['original_boot']['sha256'] and
            len(package['copies'])==2, 'v2 boot package mismatch')
    for field in ('ap','boot'):
        rows=[copy[field] for copy in package['copies']]
        require(all((r['size'],r['sha256'])==(rows[0]['size'],rows[0]['sha256']) for r in rows),
                'v2 independent package copies differ')
        for row in rows:profile.unchanged(row)
    artifact_pin(loader['elf']['path'],loader['elf']['sha256'])
    for name,status,key,source in (
        ('loader_tests','PASS_H0_ACTUAL_ARM64_LOADER','qualification_sha256','qualify_loader.py'),
        ('entry_tests','PASS_H0_QEMU_ACTUAL_EXCEPTION_LEVELS','entry_vm_sha256','loader_entry_vm.py')):
        result=checked(candidate[name])
        require(result['status']==status and result['device_actions']==0 and
                result['loader_sha256']==loader['loader']['sha256'] and
                result['source_sha256']==pin(ROOT/'workspace/public/src/mainline/s22plus_canary_h0'/source)['sha256'] and
                package[key]==candidate[name]['sha256'], 'v2 exact loader qualification differs')
    runtime=dict(loader=loader['loader'],kernel=artifact_pin(kernel['image'],kernel['sha256'],kernel['file_size']),
        init=manifest['init'],initramfs=manifest['initramfs'],dtb=manifest['dtb'],
        observer=manifest['debian_ram']['observer'],module=manifest['debian_ram']['module'])
    for row in runtime.values():profile.unchanged(row)
    return loader,package,runtime


def reproduce(candidate,manifest,producer,fixed,out):
    """Fresh H0 only; never called by a Session guard or recovery."""
    source=ROOT/'workspace/public/src/mainline/s22plus_ufs_link_h0'
    sys.path.insert(0,str(source))
    import link_initramfs as builder
    import build_evidence
    folder=Path(manifest['initramfs']['path']).parent
    key=Path(manifest['key_path']).read_bytes();ident=bytes.fromhex(manifest['candidate_id'])
    module=Path(manifest['debian_ram']['module']['path'])
    require((folder/'observer.c').read_text()==builder.observer_source() and
            (folder/'seal.h').read_text()==builder.seal_text(ident,key,manifest['network'],module),
            'v2 generated source/seal differs')
    expected=builder.compile_command(folder,vm=False,pre_effect_return=True)
    require(producer['compile_command']==expected, 'v2 compiler recipe differs')
    out.mkdir(mode=0o700)
    command=builder.compile_command(folder,vm=False,pre_effect_return=True,destination=out/'observer')
    auxiliary=auxiliary_inputs()
    require(auxiliary==fixed['observer_auxiliary'],'v2 compiler auxiliary/specs changed')
    proof=build_evidence.compile_observer(command,out)
    require(auxiliary_inputs()==auxiliary,'compiler auxiliary changed during reproduction')
    require(proof['fixed']==fixed['observer_build'] and
            proof['generated']==producer['provenance']['generated'] and
            pin(out/'observer')['sha256']==manifest['debian_ram']['observer']['sha256'],
            'v2 complete observer reproduction differs')
    return publish(out/'result.json',dict(schema='s22plus-ufs-observer-reproduction-v2',
        candidate=pin(Path(candidate)),observer=pin(out/'observer'),provenance=proof,auxiliary=auxiliary,
        status='PASS_COMPLETE_PRODUCER_REPRODUCTION',device_actions=0))


def byte_joins(candidate,fixed,loader,package,manifest):
    """Prove actual AP -> boot -> loader -> kernel/DTB/archive, not labels."""
    sys.path.insert(0,str(ROOT/'workspace/public/src/mainline/s22plus_canary_h0'))
    from mainline.s22plus_canary_h0 import package_loader as packager
    blob=profile.unchanged(loader['loader']).read_bytes();symbols=loader['runtime_symbols']
    base=symbols['_head']
    for name,path in (('kernel',checked(fixed['kernel'])['image']),('dtb',manifest['dtb']['path']),
                      ('ramdisk',manifest['initramfs']['path'])):
        data=Path(path).read_bytes();offset=symbols[name]-base
        require(0<=offset and blob[offset:offset+len(data)]==data, 'v2 embedded '+name+' differs')
    original=profile.unchanged(fixed['original_boot']).read_bytes()
    parsed_original=profile.boot.parse_boot_v4(original)
    for copy in package['copies']:
        image=profile.unchanged(copy['boot']).read_bytes();parsed=profile.boot.parse_boot_v4(image)
        require(parsed.kernel==blob and len(image)==len(original) and
                image[:8]+image[12:4096]==original[:8]+original[12:4096] and
                parsed.ramdisk==parsed_original.ramdisk and parsed.signature==parsed_original.signature and
                packager.trailer(image,parsed)==packager.trailer(original,parsed_original),
                'v2 outer boot envelope changed')
        meta,frame=profile.boot.parse_ap_tar_md5(profile.unchanged(copy['ap']).read_bytes())
        require(meta['member']['name']=='boot.img.lz4', 'v2 AP member differs')
        # The fixed packager already qualifies its exact lz4 tool. Decode the
        # actual member here to bind it to the boot bytes, once at qualification.
        lz4=Path(fixed['original_boot']['path']).parents[2]/'tools/lz4/root/usr/bin/lz4'
        require(pin(lz4)['sha256']==package['lz4_sha256']==packager.LZ4_SHA256,'v2 lz4 tool differs')
        actual=subprocess.run([lz4,'-d','-c'],input=frame,stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE,check=True,timeout=30).stdout
        require(actual==image, 'v2 AP decompression differs')


def qualify(candidate_path,output):
    candidate_path=Path(candidate_path).resolve(strict=True);output=Path(output).resolve()
    require(output.is_relative_to(ROOT/'workspace/private') and not output.exists(),'fresh private v2 output')
    candidate=read(candidate_path);cap,fixed,kernel,component=candidate_binding(candidate)
    manifest,producer,_=runtime_binding(candidate,fixed,component)
    loader,package,runtime=artifact_binding(candidate,fixed,kernel,manifest)
    output.mkdir(mode=0o700)
    byte_joins(candidate,fixed,loader,package,manifest)
    # Use the declaration path for the immutable reproduction join.
    reproduction=reproduce(candidate_path,manifest,producer,fixed,output/'reproduction')
    ap=package['copies'][0]['ap']
    with profile.transport.pin_boot_only_ap(Path(ap['path']),label='v2 H0 candidate',
            expected_size=ap['size'],expected_sha256=ap['sha256']) as handle:
        member=profile.transport.boot_only_member_receipt(handle,label='v2 H0 candidate')
    image=dict(schema=tasks.IMAGE_V2,profile=profile.PROFILE,namespace=profile.NAMESPACE,version=profile.VERSION,
        run_id_hex=manifest['candidate_id'][:32],ap=ap,member=member,
        key=pin(Path(manifest['key_path']),maximum=32),runtime_sources=runtime,ufs_link=True,
        candidate=pin(candidate_path),capability=candidate['capability'],capability_review=candidate['capability_review'])
    receipt=publish(output/'qualification.json',dict(schema=QUALIFICATION_SCHEMA,
        status='PASS_H0_KEY_ONLY_CANDIDATE',image=image,reproduction=reproduction,
        device_actions=0,grants_device_authority=False))
    image.update(qualification=receipt,debian_ram=receipt,download_return=receipt)
    binding(image,artifact_bytes=True)
    return publish(output/'image.json',image)


def selection(image):
    require(set(image)==IMAGE_FIELDS and image['schema']==tasks.IMAGE_V2 and image['ufs_link'] is True and
            image['profile']==profile.PROFILE and image['namespace']==profile.NAMESPACE and
            image['version']==profile.VERSION, 'v2 image shape')
    candidate=checked(image['candidate'])
    require(image['capability']==candidate['capability'] and
            image['capability_review']==candidate['capability_review'],'v2 mixed capability/candidate')
    cap,*_=candidate_binding(candidate)
    return cap,candidate


def binding(image,*,artifact_bytes=False):
    cap,candidate=selection(image);fixed=cap['fixed']
    qualification=checked(image['qualification'])
    require(set(qualification)=={'schema','status','image','reproduction','device_actions','grants_device_authority'} and
            qualification['schema']==QUALIFICATION_SCHEMA and qualification['status']=='PASS_H0_KEY_ONLY_CANDIDATE' and
            qualification['device_actions']==0 and qualification['grants_device_authority'] is False and
            image['qualification']==image['debian_ram']==image['download_return'] and
            qualification['image']=={k:v for k,v in image.items() if k not in
                ('qualification','debian_ram','download_return')},'v2 qualification/image join')
    reproduced=checked(qualification['reproduction'])
    require(reproduced['status']=='PASS_COMPLETE_PRODUCER_REPRODUCTION' and
            reproduced['candidate']==image['candidate'] and reproduced['device_actions']==0 and
            reproduced['observer']['sha256']==image['runtime_sources']['observer']['sha256'] and
            reproduced['provenance']['fixed']==fixed['observer_build'] and
            reproduced['auxiliary']==fixed['observer_auxiliary'], 'v2 reproduction join')
    for key in ('dependency','log'):profile.unchanged(reproduced['provenance'][key])
    profile.unchanged(reproduced['observer'])
    # Pure validation only: never compile, build or run a VM inside owner checks.
    manifest,_,_=runtime_binding(candidate,fixed,checked(fixed['component']))
    _,package,runtime=artifact_binding(candidate,fixed,checked(fixed['kernel']),manifest)
    require(image['runtime_sources']==runtime and image['ap']==package['copies'][0]['ap'] and
            image['key']==pin(Path(manifest['key_path']),maximum=32) and
            image['run_id_hex']==manifest['candidate_id'][:32],'v2 image runtime identity')
    if artifact_bytes:
        with profile.transport.pin_boot_only_ap(Path(image['ap']['path']),label='v2 H0 candidate',
                expected_size=image['ap']['size'],expected_sha256=image['ap']['sha256']) as handle:
            require(profile.transport.boot_only_member_receipt(handle,label='v2 H0 candidate')==image['member'],
                    'v2 boot-only member changed')
    return manifest


if __name__=='__main__':
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument('candidate',type=Path);cli.add_argument('output',type=Path)
    args=cli.parse_args();print(qualify(args.candidate,args.output)['path'])

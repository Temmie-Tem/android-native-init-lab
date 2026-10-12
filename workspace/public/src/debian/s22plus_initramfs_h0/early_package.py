#!/usr/bin/env python3
"""Package and qualify the actual Debian early initramfs; no device calls."""
import argparse
import gzip
from pathlib import Path
import shutil
import subprocess

import early
import fyg8
import h0
import s22plus_boot_only_f1_transport as transport
import s22plus_debian_early_profile_v1 as profile
import s22plus_debian_first_boot_v1 as prior_owner
from s22plus_native_records_v3 import pin,publish,read,require,verify


def footer(image,parsed):
    value=fyg8.boot.parse_avb_footer(image)
    end=parsed.header['signature_end'];marker=b'SEANDROIDENFORCE'
    require(image[end:end+len(marker)]==marker and value['original_image_size']==end+len(marker) and
        value['vbmeta_offset']==fyg8.boot.align(end+len(marker),4096) and
        not any(image[end+len(marker):value['vbmeta_offset']]) and
        not any(image[value['vbmeta_offset']+value['vbmeta_size']:-64]),'boot trailer layout differs')
    # Existing unlocked-research carrier retains its signed vbmeta bytes. Its
    # old payload descriptor is not a valid signature for this new ramdisk.
    return {k:value[k] for k in ('version_major','version_minor','vbmeta_size','vbmeta_sha256')}


def package(out,build,vm):
    out=h0.private(out,fresh=True);build=h0.private(build);vm=h0.private(vm)
    built=read(build/'build.json');tested=read(vm/'result.json')
    usb=built['profile']==profile.USB_PROFILE
    file_pilot=built['profile']==profile.FILE_PROFILE
    from s22plus_debian_file_profile_v1 import SCHEMA as file_schema,vm_results
    schema=file_schema if file_pilot else profile.USB_SCHEMA if usb else profile.SCHEMA
    require(built['virtual'] is False and built['ab_identical'] is True and built['device_actions']==0,
        'physical initramfs build required')
    require(tested['status']=='PASS' and tested['device_actions']==0 and
        tested['build_sha256']==h0.sha(build/'build.json') and
        [r['case'] for r in tested['cases']]==profile.vm_cases(built) and
        all(r['status']=='PASS' and (file_pilot or r['disk_before']==r['disk_after']) and
            (not usb or r.get('logging_mode','retained')==profile.usb_logging_mode(built)) for r in tested['cases']),
        'actual producer/consumer VM qualification differs')
    if file_pilot:vm_results(tested,dict(built,key=pin(build/'key',maximum=32)))
    runtime={}
    for row in built['source_inputs']:
        relative=Path(row['path'])
        require(not relative.is_absolute() and '..' not in relative.parts and
            relative.is_relative_to('workspace/public/src'),'build source path differs')
        path=h0.ROOT/relative;receipt=pin(path,maximum=4*1024**2)
        require(receipt['sha256']==row['sha256'],'build source changed')
        runtime[row['path']]=dict(size=path.stat().st_size,sha256=row['sha256'])
    for row in tested['source_inputs']:
        require(h0.sha(h0.ROOT/row['path'])==row['sha256'],'VM source changed')
    inputs=h0.private(built['inputs']);inventory=fyg8.verify_inventory(inputs)
    previous=read(verify(fyg8.retained.RETAINED_RESULT))
    baseline=fyg8.retained.RETAINED/'candidate-a/boot.img'
    expected=previous['candidate']['a']['boot_img']
    verify(dict(path=str(baseline),**expected),maximum=128*1024**2)
    original=baseline.read_bytes();parsed=fyg8.boot.parse_boot_v4(original)
    initramfs=verify(built['initramfs'],maximum=16*1024**2)
    ramdisk=gzip.decompress(initramfs.read_bytes());fyg8.debian_entries(initramfs)
    tools=early.packaging.shared.packager._bind_tools()
    for side in 'ab':
        folder=out/('pack-'+side);folder.mkdir(mode=0o700);shutil.copyfile(baseline,folder/'base.img')
        for argv,name in (([tools['magiskboot'],'unpack','-h','base.img'],'unpack'),):
            with (folder/(name+'.log')).open('xb') as log:
                subprocess.run(argv,cwd=folder,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=60)
        (folder/'ramdisk.cpio').write_bytes(ramdisk)
        with (folder/'repack.log').open('xb') as log:
            subprocess.run([tools['magiskboot'],'repack','base.img','boot.img'],cwd=folder,
                stdout=log,stderr=subprocess.STDOUT,check=True,timeout=60)
        image=(folder/'boot.img').read_bytes();actual=fyg8.boot.parse_boot_v4(image)
        require(len(image)==len(original) and actual.kernel==parsed.kernel and actual.signature==parsed.signature and
            footer(image,actual)==footer(original,parsed) and
            {k:v for k,v in actual.header.items() if k not in ('ramdisk_size','ramdisk_end','signature_start','signature_end')}==
            {k:v for k,v in parsed.header.items() if k not in ('ramdisk_size','ramdisk_end','signature_start','signature_end')} and
            fyg8.boot.decompress_lz4_stream_python(actual.ramdisk,maximum=128*1024**2)==ramdisk,
            'boot header/kernel/signature or exact ramdisk changed')
        h0.run([tools['lz4'],'--content-size','-B6','-f','-q',folder/'boot.img',folder/'boot.img.lz4'],folder/'lz4.log')
        early.packaging.shared.packager._write_deterministic_boot_ap((folder/'boot.img.lz4').read_bytes(),folder/'AP.tar.md5')
    require((out/'pack-a/AP.tar.md5').read_bytes()==(out/'pack-b/AP.tar.md5').read_bytes(),'boot/AP A/B differs')
    ap=pin(out/'pack-a/AP.tar.md5',maximum=128*1024**2)
    with transport.pin_boot_only_ap(Path(ap['path']),label='Debian early',expected_size=ap['size'],expected_sha256=ap['sha256']) as bound:
        member=transport.boot_only_member_receipt(bound,label='Debian early')
    artifact=publish(out/'artifact.json',dict(schema=schema+'-artifact',namespace=built['namespace'],
        version=built['version'],run_id=built['run_id'],ap=ap,member=member,key=pin(build/'key',maximum=32),
        build=pin(build/'build.json'),expected=built['measured'],runtime_sources=runtime,
        module_names=[m['runtime_name'] for m in (built['modules'] if usb else inventory['modules'])],ab_identical=True,active=False,
        boot=pin(out/'pack-a/boot.img',maximum=128*1024**2),ramdisk_sha256=fyg8.digest(ramdisk),
        inventory=pin(inputs/'inventory.json'),vm=pin(vm/'result.json'),device_actions=0))
    _,terminal,plan=profile.prior_inputs();final=verify(terminal['final_health'])
    require(read(final)==prior_owner.android_projection(final.parent,plan),'retained Android32 return does not rederive')
    basis=dict(source_terminal=profile.retained.TERMINAL,target=plan['target'],A=plan['A'],layout='proposed',
        geometry=plan['basis']['geometry'],total_bytes=34357624832)
    image=dict(schema='s22plus-native-image-v3',namespace=built['namespace'],version=built['version'],
        run_id_hex=built['run_id'],profile=built['profile'],ap=ap,member=member,key=pin(build/'key',maximum=32),
        runtime_sources=runtime,early_boot=artifact,gpt=plan['basis']['gpt'],android_return=basis)
    qualification=publish(out/'qualification.json',dict(schema=schema+'-qualification',
        status='PASS_H0_ARTIFACT_AND_VM',image=image,vm=pin(vm/'result.json'),device_actions=0))
    image['qualification']=qualification;profile.image_binding(image)
    return publish(out/'image.json',image)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('output','build','vm'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();result=package(args.output,args.build,args.vm)
    print('PASS: H0 qualified boot-only Debian early image '+result['sha256'])

#!/usr/bin/env python3
"""Qualify automatic Debian's actual boot-only archive and ARM64 corpus."""
import argparse
from pathlib import Path

import autoboot
import early_package as packaging
import s22plus_debian_autoboot_profile_v1 as profile
import s22plus_debian_autoboot_qualification_v1 as qualification
import s22plus_debian_integrated_profile_v1 as archive
from s22plus_native_records_v3 import pin,publish,read,require,verify


def package(out,build,vm):
    h0=autoboot.h0;out=h0.private(out,fresh=True);build=h0.private(build);vm=h0.private(vm)
    built=read(build/'build.json');tested=read(vm/'result.json');key=verify(built['key'],maximum=32).read_bytes()
    qualification.producer(built,virtual=False)
    require(built['ab_identical'] is True and tested['build_sha256']==h0.sha(build/'build.json'),
        'automatic physical/VM selection differs')
    qualification.vm_results(tested,built,key)
    runtime={}
    for row in built['source_inputs']:
        relative=Path(row['path']);require(not relative.is_absolute() and '..' not in relative.parts and
            (relative.is_relative_to('workspace/public/src') or
             relative==Path('docs/operations/S22PLUS_NATIVE_UFS_V1.md')),'automatic source path differs')
        receipt=pin(h0.ROOT/relative,maximum=4*1024**2)
        require(receipt['sha256']==row['sha256'],'automatic physical source changed')
        runtime[row['path']]={name:receipt[name] for name in ('size','sha256')}
    ap,member,boot,ramdisk=packaging.package_archive(out,built)
    artifact=publish(out/'artifact.json',dict(schema=profile.SCHEMA+'-artifact',namespace=built['namespace'],
        version=built['version'],run_id=built['run_id'],ap=ap,member=member,key=built['key'],
        build=pin(build/'build.json'),expected=built['measured'],runtime_sources=runtime,
        module_names=[m['runtime_name'] for m in built['modules']],ab_identical=True,active=False,
        boot=boot,ramdisk_sha256=ramdisk,inventory=pin(Path(built['inputs'])/'inventory.json'),
        vm=pin(vm/'result.json'),device_actions=0))
    _,terminal,plan=profile.prior_inputs();final=verify(terminal['final_health'])
    require(read(final)==packaging.prior_owner.android_projection(final.parent,plan),'retained Android return differs')
    basis=dict(source_terminal=archive.early.retained.TERMINAL,target=plan['target'],A=plan['A'],layout='proposed',
        geometry=plan['basis']['geometry'],total_bytes=34357624832)
    image=dict(schema='s22plus-native-image-v3',namespace=built['namespace'],version=built['version'],
        run_id_hex=built['run_id'],profile=profile.PROFILE,ap=ap,member=member,key=built['key'],
        runtime_sources=runtime,autoboot_boot=artifact,gpt=plan['basis']['gpt'],android_return=basis)
    image['qualification']=publish(out/'qualification.json',dict(schema=profile.SCHEMA+'-qualification',
        status='PASS_H0_ARTIFACT_AND_VM',image=dict(image),vm=pin(vm/'result.json'),device_actions=0))
    qualification.archive_binding(image,profile.image_binding(image))
    return publish(out/'image.json',image)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('output','build','vm'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();result=package(args.output,args.build,args.vm)
    print('PASS: H0 automatic boot-only image '+result['sha256'])

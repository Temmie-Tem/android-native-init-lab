#!/usr/bin/env python3
"""Package a qualified loader in the retained boot-v4 envelope; H0 only."""
import argparse
import json
from pathlib import Path
import shutil
import sys

from prepare import ROOT, digest, require, run

sys.path.insert(0,str(ROOT/'workspace/public/src/scripts/revalidation'))
import s22plus_boot_verify as boot
import s22plus_fyg8_p286_boot_only_packager as packager
import build_s22plus_fyg8_r4w1c_watchdog_carrier as carrier

LZ4_SHA256='4be960d6f6b0d7ef69e01a9e1a056591c17b8687e9851db128018b2ac5f01da0'

def trailer(image,parsed):
    footer=boot.parse_avb_footer(image);end=parsed.header['signature_end']
    require(image[end:end+16]==b'SEANDROIDENFORCE' and footer['original_image_size']==end+16 and
            footer['vbmeta_offset']==boot.align(end+16,4096) and
            not any(image[end+16:footer['vbmeta_offset']]) and
            not any(image[footer['vbmeta_offset']+footer['vbmeta_size']:-64]),'boot trailer geometry')
    return {key:footer[key] for key in ('version_major','version_minor','vbmeta_size','vbmeta_sha256')}


def package(loader,qualification,entry_vm,output):
    loader,qualification,entry_vm,output=[p.resolve() for p in (loader,qualification,entry_vm,output)]
    require(output.is_relative_to(ROOT/'workspace/private'),'private package output')
    record=json.loads((loader/'result.json').read_text());blob=Path(record['loader']['path'])
    android_control=record['status']=='H0_LOADER_ANDROID_BUILT_NOT_DEVICE_ADMITTED'
    require(record['status'] in ('H0_LOADER_BUILT_RUNTIME_PLACEMENT_GUARDED',
                                'H0_LOADER_ANDROID_BUILT_NOT_DEVICE_ADMITTED') and
            digest(blob)==record['loader']['sha256'],'loader input differs')
    statuses=(('PASS_H0_ACTUAL_ARM64_LOADER_ANDROID','PASS_H0_QEMU_ACTUAL_EL_LOADER_ANDROID')
              if android_control else ('PASS_H0_ACTUAL_ARM64_LOADER','PASS_H0_QEMU_ACTUAL_EXCEPTION_LEVELS'))
    for path,status in zip((qualification,entry_vm),statuses):
        value=json.loads((path/'result.json').read_text())
        require(value['status']==status and value['loader_sha256']==digest(blob),'loader qualification differs')
    target=json.loads((ROOT/'workspace/public/src/device-action/profiles/s22plus_fyg8.json').read_text())
    baseline=ROOT/'workspace/private/outputs/s22plus_magisk_root_boot_only/boot.img'
    original=baseline.read_bytes()
    require(len(original)==96*1024*1024 and digest(baseline)==target['final_health']['boot_sha256'],
            'retained original-A boot differs')
    parsed=boot.parse_boot_v4(original);old_trailer=trailer(original,parsed)
    magiskboot=ROOT/'workspace/private/tools/magisk-v30.7/magiskboot'
    lz4=ROOT/'workspace/private/tools/lz4/root/usr/bin/lz4'
    require(digest(magiskboot)==carrier.MAGISKBOOT_SHA256,'retained magiskboot differs')
    require(digest(lz4)==LZ4_SHA256,'selected local lz4 differs')
    output.mkdir(mode=0o700,parents=True,exist_ok=False)
    records=[]
    for side in 'ab':
        folder=output/('pack-'+side);folder.mkdir(mode=0o700)
        shutil.copyfile(baseline,folder/'base.img')
        run([magiskboot,'unpack','-h','base.img'],folder/'unpack.log',cwd=folder)
        shutil.copyfile(blob,folder/'kernel')
        run([magiskboot,'repack','base.img','boot.img'],folder/'repack.log',cwd=folder)
        image=(folder/'boot.img').read_bytes();actual=boot.parse_boot_v4(image)
        require(len(image)==len(original) and actual.kernel==blob.read_bytes(),'boot size or loader bytes differ')
        require(image[:8]+image[12:4096]==original[:8]+original[12:4096] and
                actual.ramdisk==parsed.ramdisk and actual.signature==parsed.signature and
                trailer(image,actual)==old_trailer,'retained outer envelope changed')
        audit=folder/'audit';audit.mkdir(mode=0o700)
        value=packager.package(boot_path=folder/'boot.img',lz4_path=lz4,output_dir=folder,audit_dir=audit)
        ap=folder/value['paths']['ap_tar_md5'];meta,frame=boot.parse_ap_tar_md5(ap.read_bytes())
        require(meta['member']['name']=='boot.img.lz4' and frame==(folder/'boot.img.lz4').read_bytes(),
                'AP member differs')
        records.append({'boot':{'path':str(folder/'boot.img'),'sha256':digest(folder/'boot.img'),'size':len(image)},
                        'ap':{'path':str(ap),'sha256':digest(ap),'size':ap.stat().st_size},'package':value})
    require(records[0]['boot']['sha256']==records[1]['boot']['sha256'] and
            records[0]['ap']['sha256']==records[1]['ap']['sha256'],'independent packaging outputs differ')
    result={'status':'H0_BOOT_V4_PACKAGED_NOT_DEVICE_ADMITTED','loader_sha256':digest(blob),
            'qualification_sha256':digest(qualification/'result.json'),'entry_vm_sha256':digest(entry_vm/'result.json'),
            'original_a_sha256':digest(baseline),'magiskboot_sha256':digest(magiskboot),'lz4_sha256':digest(lz4),
            'source_sha256':digest(__file__),'copies':records,'outer_ramdisk_retained_and_not_used_by_loader':not android_control,
            'signature_note':'Retained signature/vbmeta bytes do not authenticate this modified payload.',
            'device_actions':0,'activation':False}
    if android_control:
        require(record['original_a']['sha256']==digest(baseline),'control kernel baseline differs from packaged A')
        result['profile']='loader-android-v1'
        result['outer_ramdisk_inherited_from_abl']=True
    (output/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'status':result['status'],'boot_bytes':records[0]['boot']['size'],
                      'ap_bytes':records[0]['ap']['size'],'two_packages_identical':True}))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('loader','qualification','entry-vm','output'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();package(a.loader,a.qualification,a.entry_vm,a.output)

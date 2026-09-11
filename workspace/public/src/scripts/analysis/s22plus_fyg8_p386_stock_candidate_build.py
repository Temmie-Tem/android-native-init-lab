"""Package the retained A/B resident artifacts into an exact boot-only AP.

No device contact. Reopen the qualified input closure and both artifact copies;
preserve every ramdisk entry except init, renderer and the read-only provider.
"""
import argparse
import json
from pathlib import Path
import shutil
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[5]
sys.path[:0]=[str(Path(__file__).parent),str(ROOT/'workspace/public/src/scripts/revalidation')]
import s22plus_fyg8_p384_stock_candidate_build as shared
import s22plus_native_resident_build_h0_v1 as resident_build
import s22plus_fyg8_p386_candidate as declaration
import s22plus_native_resident_source_v1 as source

RETAINED=ROOT/'workspace/private/outputs/s22plus-native-resident-h0-v1/build-3'
RETAINED_RESULT=dict(size=59753,sha256='ae3177d642206200a8d49a0d9a8359e6d451e287dbb29cb0815deba847878d18')
DEFAULT_OUTPUT_ROOT=ROOT/'workspace/private/outputs/s22plus-fyg8-v0.2.0-rc.4/candidate-build-final'
REFERENCE_IDENTITY=shared.REFERENCE_IDENTITY
PROVIDER_MEMBER='s22-display-modules/s22plus_max77705_telemetry.ko'
TARGET=dict(shared.TARGET)
identity,stable,write,run,canonical=shared.identity,shared.stable,shared.write,shared.run,shared.canonical


def retained_inputs():
    raw=stable(RETAINED/'result.json',expected=RETAINED_RESULT)
    value=json.loads(raw)
    if (value['verdict']!='PASS_RESIDENT_BUILD_H0' or value['run_id_hex']!=declaration.IDENTITY.run_id_hex
            or value['source_inputs']!=resident_build.closure() or value['profile']!=source.profile_contract()
            or value['ab_identical'] is not True):raise ValueError('retained resident build closure differs')
    for label in ('a','b'):
        for path,pin in ((RETAINED/('userspace-'+label)/'init',value['init']),
                         (RETAINED/('renderer-'+label),value['renderer']),
                         (RETAINED/'provider'/('module-'+label+'.ko'),value['provider']['module'])):
            stable(path,expected=pin)
    for path,pin in value['toolchain_inputs'].items():stable(Path(path),expected=pin)
    for path,pin in value['provider']['inputs'].items():stable(ROOT/path,expected=pin)
    for name,raw in source.provider_sources().items():
        if stable(RETAINED/'provider/module-stage'/name)!=raw:raise ValueError('retained provider source differs')
    telemetry=resident_build.telemetry
    stable(telemetry.IMAGE,expected=value['provider']['image'])
    imports=telemetry.linkage._imports(RETAINED/'provider/module-a.ko')
    exports=telemetry.linkage._image_provider_map(telemetry.IMAGE.read_bytes(),telemetry.linkage.IMAGE_SECTION_LAYOUT)
    if imports!=value['provider']['imports'] or any(exports.get(k)!=v for k,v in imports.items()):
        raise ValueError('retained provider exact linkage differs')
    return value


def source_receipts():
    paths={ROOT/name for name in resident_build.closure()}|{Path(__file__),Path(declaration.__file__)}
    # The retained native artifact closure and new packaging closure are kept
    # distinct from the host-observer execution closure owned by candidate-static.
    return {str(p.relative_to(ROOT)):identity(stable(p)) for p in sorted(paths)}


def check_boot(raw,baseline,image,replacements):
    parsed,rows=shared.entries(raw);_,old=shared.entries(baseline)
    if (set(replacements)!={'init','s22-display',PROVIDER_MEMBER} or len(raw)!=len(baseline)
            or set(rows)!=set(old) or parsed.kernel!=image):raise ValueError('resident boot inventory/layout differs')
    for name,entry in old.items():
        expected=shared.row_identity(entry)
        if name in replacements:expected.update(identity(replacements[name]))
        if shared.row_identity(rows[name])!=expected:raise ValueError('resident boot member differs: '+name)
    return {name:shared.row_identity(row) for name,row in sorted(rows.items())}


def build_package(out,label,baseline,image,replacements,tools):
    scratch=Path(tempfile.mkdtemp(prefix='resident-pack-'+label+'-',dir=out))
    try:
        write(scratch/'base.img',baseline)
        run([tools['magiskboot'],'unpack','-h',scratch/'base.img'],scratch,scratch/'unpack.log')
        (scratch/'kernel').write_bytes(image)
        _,rows=shared.entries(baseline);commands=[]
        for index,(member,raw) in enumerate(replacements.items()):
            path=scratch/('replacement-'+str(index));write(path,raw)
            commands.append('add '+format(rows[member].mode&0o7777,'o')+' '+member+' '+str(path))
        run([tools['magiskboot'],'cpio',scratch/'ramdisk.cpio',*commands],scratch,scratch/'cpio.log')
        run([tools['magiskboot'],'repack',scratch/'base.img',scratch/'boot.img'],scratch,scratch/'repack.log')
        raw=stable(scratch/'boot.img');inventory=check_boot(raw,baseline,image,replacements)
        folder=out/('candidate-'+label);folder.mkdir(mode=0o700);write(folder/'boot.img',raw)
        run([tools['lz4'],'--content-size','-B6','-f','-q',folder/'boot.img',folder/'boot.img.lz4'],scratch,scratch/'lz4.log')
        (folder/'boot.img.lz4').chmod(0o400)
        structure=shared.packager._write_deterministic_boot_ap(stable(folder/'boot.img.lz4'),folder/'odin4/AP.tar.md5')
        (folder/'odin4/AP.tar.md5').chmod(0o400)
        for log in scratch.glob('*.log'):write(out/'packaging-logs'/label/log.name,stable(log))
        value=dict(boot_img=identity(raw),boot_img_lz4=identity(stable(folder/'boot.img.lz4')),
            ap_tar_md5=identity(stable(folder/'odin4/AP.tar.md5')),inventory=inventory,ap_structure=structure)
    except BaseException:
        write(scratch/'FAILED_H0.json',canonical(dict(role=label)));raise
    else:shutil.rmtree(scratch)
    return value


def build_result(output_root=DEFAULT_OUTPUT_ROOT,*,audit_only=False):
    if audit_only:return audit_existing(output_root)
    out=Path(output_root).absolute()
    if out.exists() or out.is_symlink() or not out.resolve().is_relative_to((ROOT/'workspace/private').resolve()):
        raise ValueError('fresh private resident package output required')
    retained=retained_inputs();reference,_=shared.reference_inputs();pins=source_receipts()
    out.mkdir(mode=0o700,parents=True);write(out/'source-inputs.json',canonical(pins))
    image,transform=declaration.artifact.transform_image(stable(shared.REFERENCE/'inputs/fixed-Image',expected=reference['image']))
    write(out/'inputs/fixed-Image',image)
    replacements={'init':stable(RETAINED/'userspace-a/init',expected=retained['init']),
        's22-display':stable(RETAINED/'renderer-a',expected=retained['renderer']),
        PROVIDER_MEMBER:stable(RETAINED/'provider/module-a.ko',expected=retained['provider']['module'])}
    declaration.artifact._validate_init(replacements['init'])
    baseline=stable(shared.REFERENCE/'candidate-a/boot.img',expected=reference['candidate']['a']['boot_img'])
    tools=shared.packager._bind_tools()
    packages={label:build_package(out,label,baseline,image,replacements,tools) for label in ('a','b')}
    if packages['a']!=packages['b']:raise ValueError('resident AP A/B differs')
    inventory=packages['a']['inventory']
    value=dict(schema='s22plus-fyg8-p386-stock-candidate-build-v1',verdict='PASS_P386_STOCK_CANDIDATE_BUILD_H0',
        target=TARGET,run_id_hex=declaration.IDENTITY.run_id_hex,source_inputs=pins,
        retained_result=dict(path=str((RETAINED/'result.json').relative_to(ROOT)),**identity(stable(RETAINED/'result.json'))),
        image=identity(image),image_transform=transform,init=retained['init'],renderer=retained['renderer'],
        provider=retained['provider']['module'],child={k:inventory['s22-e1-child'][k] for k in ('size','sha256')},
        module_plan=identity(stable(RETAINED/'inputs/s22plus_native_display_plan.h')),
        candidate=packages,byte_identical=True,native_artifacts_reused=True,toolchain_inputs=reference['toolchain_inputs'],
        scope=dict(tier='H0',device_contact=False,live_authorized=False,candidate_transfers=0,rollback_transfers=0))
    if source_receipts()!=pins or retained_inputs()!=retained:raise ValueError('resident package inputs changed')
    write(out/'result.json',canonical(value));return audit_existing(out)


def audit_existing(output_root=DEFAULT_OUTPUT_ROOT):
    out=Path(output_root).absolute();value=json.loads(stable(out/'result.json'));retained=retained_inputs()
    if (value['schema']!='s22plus-fyg8-p386-stock-candidate-build-v1' or value['verdict']!='PASS_P386_STOCK_CANDIDATE_BUILD_H0'
            or value['run_id_hex']!=declaration.IDENTITY.run_id_hex or value['source_inputs']!=source_receipts()
            or value['candidate']['a']!=value['candidate']['b']):raise ValueError('resident package binding differs')
    reference,_=shared.reference_inputs()
    baseline=stable(shared.REFERENCE/'candidate-a/boot.img',expected=reference['candidate']['a']['boot_img'])
    image,transform=declaration.artifact.transform_image(stable(shared.REFERENCE/'inputs/fixed-Image',expected=reference['image']))
    if stable(out/'inputs/fixed-Image',expected=value['image'])!=image or value['image_transform']!=transform:
        raise ValueError('resident Image transform differs')
    replacements={'init':stable(RETAINED/'userspace-a/init',expected=retained['init']),
        's22-display':stable(RETAINED/'renderer-a',expected=retained['renderer']),
        PROVIDER_MEMBER:stable(RETAINED/'provider/module-a.ko',expected=retained['provider']['module'])}
    for label in ('a','b'):
        folder=out/('candidate-'+label);package=value['candidate'][label]
        raw=stable(folder/'boot.img',expected=package['boot_img'])
        if check_boot(raw,baseline,image,replacements)!=package['inventory']:raise ValueError('resident retained boot differs')
        stable(folder/'boot.img.lz4',expected=package['boot_img_lz4'])
        declaration.artifact.inspect_ap(folder/'odin4/AP.tar.md5',expected_ap=package['ap_tar_md5'],
            expected_image=image,expected_init=replacements['init'])
        # AP inspection must also prove the new provider and unchanged inventory,
        # not just trust the separately retained boot.img file.
        frame,_=shared.artifacts.reference._INNER._parse_ap(stable(folder/'odin4/AP.tar.md5'),'resident AP')
        decoded=shared.boot.decompress_lz4_frame_python(frame,maximum=128*1024*1024)
        if decoded!=raw or check_boot(decoded,baseline,image,replacements)!=package['inventory']:
            raise ValueError('resident actual AP join differs')
    return value


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument('--audit-only',action='store_true');args=parser.parse_args()
    result=build_result(args.out,audit_only=args.audit_only)
    print(json.dumps(dict(verdict=result['verdict'],ap=result['candidate']['a']['ap_tar_md5']),sort_keys=True))

"""Thermal development packages over the frozen resident N control platform."""
import json
from pathlib import Path
import re
import shutil
import tempfile

import s22plus_native_baseline_v2_build as base
import s22plus_native_thermal_source_v1 as source
import s22plus_thermal_provider_build_h0_v1 as provider

ROOT = base.ROOT
packaging,shared = base.packaging,base.SHARED
EXTRA_SOURCES = base.EXTRA_SOURCES + [
    'workspace/public/src/scripts/revalidation/s22plus_native_thermal_observer_v1.py',
    'workspace/public/src/scripts/revalidation/s22plus_native_thermal_source_v1.py',
    'docs/operations/S22PLUS_NATIVE_THERMAL_V1.md']
ADDED = tuple('s22-display-modules/'+name for name in provider.MODULE_ORDER)


def check_boot(raw,baseline,image,replacements):
    parsed,rows=shared.entries(raw);_,old=shared.entries(baseline)
    expected_replacements={'init','s22-display',packaging.PROVIDER_MEMBER,*ADDED}
    if (set(replacements)!=expected_replacements or len(raw)!=len(baseline) or
        set(rows)!=set(old)|set(ADDED) or parsed.kernel!=image):
        raise ValueError('thermal boot layout/inventory differs')
    for name,row in rows.items():
        expected=shared.row_identity(old[name]) if name in old else dict(mode=0o100400,uid=0,gid=0,nlink=1,mtime=0)
        if name in replacements: expected.update(packaging.identity(replacements[name]))
        if shared.row_identity(row)!=expected: raise ValueError('thermal boot member differs: '+name)
    return {name:shared.row_identity(row) for name,row in sorted(rows.items())}


def build_package(out,label,baseline,image,replacements,tools):
    scratch=Path(tempfile.mkdtemp(prefix='thermal-pack-'+label+'-',dir=out))
    try:
        shared.write(scratch/'base.img',baseline)
        shared.run([tools['magiskboot'],'unpack','-h',scratch/'base.img'],scratch,scratch/'unpack.log')
        (scratch/'kernel').write_bytes(image)
        _,old=shared.entries(baseline);commands=[]
        for index,(member,raw) in enumerate(replacements.items()):
            path=scratch/('replacement-'+str(index));shared.write(path,raw)
            mode=old[member].mode&0o7777 if member in old else 0o400
            commands.append('add '+format(mode,'o')+' '+member+' '+str(path))
        shared.run([tools['magiskboot'],'cpio',scratch/'ramdisk.cpio',*commands],scratch,scratch/'cpio.log')
        shared.run([tools['magiskboot'],'repack',scratch/'base.img',scratch/'boot.img'],scratch,scratch/'repack.log')
        raw=shared.stable(scratch/'boot.img');inventory=check_boot(raw,baseline,image,replacements)
        folder=out/('candidate-'+label);folder.mkdir(mode=0o700);shared.write(folder/'boot.img',raw)
        shared.run([tools['lz4'],'--content-size','-B6','-f','-q',folder/'boot.img',folder/'boot.img.lz4'],scratch,scratch/'lz4.log')
        (folder/'boot.img.lz4').chmod(0o400)
        structure=shared.packager._write_deterministic_boot_ap(shared.stable(folder/'boot.img.lz4'),folder/'odin4/AP.tar.md5')
        (folder/'odin4/AP.tar.md5').chmod(0o400)
        for log in scratch.glob('*.log'): shared.write(out/'packaging-logs'/label/log.name,shared.stable(log))
        result=dict(boot_img=packaging.identity(raw),boot_img_lz4=packaging.identity(shared.stable(folder/'boot.img.lz4')),
            ap_tar_md5=packaging.identity(shared.stable(folder/'odin4/AP.tar.md5')),inventory=inventory,ap_structure=structure)
    except BaseException:
        shared.write(scratch/'FAILED_H0.json',shared.canonical(dict(role=label)));raise
    else: shutil.rmtree(scratch)
    return result


class Builder(base.Builder):
    __file__=__file__
    source=source
    provider_profile=None

    def __init__(self,declaration):
        super().__init__(declaration)
        self.DEFAULT_OUTPUT_ROOT=ROOT/('workspace/private/outputs/s22plus-native-thermal-v1/'+declaration.IDENTITY.namespace+'/build-2')

    def source_receipts(self):
        paths={ROOT/name for name in super().source_receipts()}|set(self.source.source_files())|set(provider.source_files(self.provider_profile))|{Path(__file__)}
        return {str(path.relative_to(ROOT)):packaging.identity(packaging.stable(path)) for path in sorted(paths)}

    def native_selection(self):
        return dict(super().native_selection(),runtime_profile=self.source.profile_contract(),added_modules=list(ADDED))

    def base_runtime(self,out):
        # The inherited builder validates the unmodified resident artifacts;
        # this profile owns only the extra module plan and new renderer.
        return base.Builder(self.declaration).runtime_inputs(Path(out)/'resident')

    def runtime_inputs(self,out=None):
        out=self.DEFAULT_OUTPUT_ROOT/'runtime' if out is None else Path(out).absolute()
        if out.resolve()!=out or not out.is_relative_to(ROOT/'workspace/private/outputs'):
            raise ValueError('thermal runtime must be a direct private output')
        value=json.loads(packaging.stable(out/'result.json'))
        resident=self.base_runtime(out);thermal=provider.audit(out/'thermal-provider',profile=self.provider_profile)
        if packaging.stable(out/'renderer-a')!=packaging.stable(out/'renderer-b'):
            raise ValueError('thermal renderer A/B differs')
        if packaging.stable(out/'inputs/s22plus_native_display_plan.h')!=self.module_plan(resident,thermal,out):
            raise ValueError('thermal fixed module plan differs')
        census=tuple(self.source.resident.common.MemoryModule(*row) for row in shared.memory.manifest())
        if packaging.stable(out/'inputs/renderer.c')!=self.source.render_display(self.declaration.IDENTITY,census):
            raise ValueError('thermal renderer source differs')
        if shared.canonical(value)!=shared.canonical(self.runtime_value(out,resident,thermal)):
            raise ValueError('thermal runtime evidence does not regenerate')
        return value

    def runtime_value(self,out,resident,thermal):
        tools=shared.packager._bind_tools()
        import subprocess
        description=subprocess.check_output([tools['file'],'-b',out/'renderer-a'],text=True).strip()
        elf=subprocess.check_output([tools['readelf'],'-W','-l',out/'renderer-a'])
        if 'ARM aarch64' not in description or 'statically linked' not in description or b'INTERP' in elf:
            raise ValueError('thermal renderer ELF differs')
        return dict(schema='s22plus-native-thermal-runtime-v1',source_inputs=self.source_receipts(),profile=self.source.profile_contract(),
            run_id_hex=self.declaration.IDENTITY.run_id_hex,resident=resident,thermal=thermal,
            renderer=packaging.identity(packaging.stable(out/'renderer-a')),file=description,ab_identical=True)

    def module_plan(self,resident,thermal,out):
        plan=packaging.stable(Path(out)/'resident/inputs/s22plus_native_display_plan.h')
        match=re.findall(rb'#define P350_DISPLAY_MODULE_COUNT ([0-9]+)U',plan)
        if len(match)!=1: raise ValueError('resident module count differs')
        count=int(match[0]);plan=self.source.resident.replace(plan,match[0]+b'U',str(count+len(ADDED)).encode()+b'U')
        rows=b''.join(('    {"/s22-display-modules/'+name+'", '+str(thermal['modules'][name]['identity']['size'])+'ULL, 0},\n').encode()
            for name in provider.MODULE_ORDER)
        return self.source.resident.replace(plan,b'\n};\n',b'\n'+rows+b'};\n')

    def build_runtime(self,out,thermal_input):
        out.mkdir(mode=0o700,parents=True)
        resident=base.resident_build.build(out/'resident',base.PROVIDER_INPUT,selected=self.declaration.IDENTITY)
        thermal=provider.audit(thermal_input,profile=self.provider_profile)
        thermal_out=out/'thermal-provider';thermal_out.mkdir(mode=0o700)
        names=['result.json','module-a.ko','module-b.ko',*('modules/'+name for name in provider.MODULE_ORDER),
            *('module-stage/'+name for name in provider.PARTS)]
        for name in names: shared.write(thermal_out/name,packaging.stable(Path(thermal_input)/name))
        if provider.audit(thermal_out,profile=self.provider_profile)!=thermal: raise ValueError('thermal provider reuse differs')
        plan=self.module_plan(resident,thermal,out);shared.write(out/'inputs/s22plus_native_display_plan.h',plan)
        census=tuple(self.source.resident.common.MemoryModule(*row) for row in shared.memory.manifest())
        shared.write(out/'inputs/renderer.c',self.source.render_display(self.declaration.IDENTITY,census))
        tools=shared.packager._bind_tools()
        compiler=[tools['gcc'],*shared.RENDERER_FLAGS,'-I',out/'inputs','-I',shared.HEADERS,'-I',self.source.NATIVE,out/'inputs/renderer.c']
        for side in ('a','b'): shared.run([*compiler,'-o',out/('renderer-'+side)],out,out/('renderer-'+side+'.log'))
        first=packaging.identity(packaging.stable(out/'renderer-a'))
        if first!=packaging.identity(packaging.stable(out/'renderer-b')): raise ValueError('thermal renderer A/B differs')
        description=shared.run([tools['file'],'-b',out/'renderer-a'],out,out/'renderer-file.log').decode().strip()
        elf=shared.run([tools['readelf'],'-W','-l',out/'renderer-a'],out,out/'renderer-readelf.log')
        if 'ARM aarch64' not in description or 'statically linked' not in description or b'INTERP' in elf:
            raise ValueError('thermal renderer ELF differs')
        self.build_native_init(out,resident)
        result=self.runtime_value(out,resident,thermal)
        shared.write(out/'result.json',shared.canonical(result));return self.runtime_inputs(out)

    def build_native_init(self,out,resident):
        # V1 preserves the inherited init; extended private IPC profiles must
        # override this hook and audit their actual generated init separately.
        pass

    def init_input(self,out,runtime):
        return out/'resident/userspace-a/init',runtime['resident']['init']

    def replacements(self,runtime):
        out=self.DEFAULT_OUTPUT_ROOT/'runtime';resident=runtime['resident']
        init_path,init_pin=self.init_input(out,runtime)
        return {'init':packaging.stable(init_path,expected=init_pin),
            's22-display':packaging.stable(out/'renderer-a',expected=runtime['renderer']),
            packaging.PROVIDER_MEMBER:packaging.stable(out/'resident/provider/module-a.ko',expected=resident['provider']['module']),
            **{member:packaging.stable(out/'thermal-provider/modules'/Path(member).name,
                expected=runtime['thermal']['modules'][Path(member).name]['identity']) for member in ADDED}}

    def build(self,*,thermal_input,runtime_input=None):
        out=self.DEFAULT_OUTPUT_ROOT
        if out.exists() or out.is_symlink(): raise ValueError('fresh thermal package output required')
        pins=self.source_receipts();out.mkdir(mode=0o700,parents=True)
        if runtime_input is None: runtime=self.build_runtime(out/'runtime',Path(thermal_input).absolute())
        else:
            runtime_input=Path(runtime_input).absolute();runtime=self.runtime_inputs(runtime_input)
            if any(path.is_symlink() for path in runtime_input.rglob('*')): raise ValueError('indirect thermal runtime input')
            shutil.copytree(runtime_input,out/'runtime')
        reference,_=shared.reference_inputs()
        image,transform=self.declaration.artifact.transform_image(packaging.stable(shared.REFERENCE/'inputs/fixed-Image',expected=reference['image']))
        shared.write(out/'inputs/fixed-Image',image)
        replacements=self.replacements(runtime);self.declaration.artifact._validate_init(replacements['init'])
        baseline=packaging.stable(shared.REFERENCE/'candidate-a/boot.img',expected=reference['candidate']['a']['boot_img'])
        tools=shared.packager._bind_tools()
        packages={side:build_package(out,side,baseline,image,replacements,tools) for side in ('a','b')}
        if packages['a']!=packages['b']: raise ValueError('thermal boot-only AP A/B differs')
        result=self.result_value(runtime,image,transform,packages)
        if pins!=self.source_receipts(): raise ValueError('thermal source changed during package build')
        shared.write(out/'result.json',shared.canonical(result));return self.audit_existing()

    def audit_existing(self):
        out=self.DEFAULT_OUTPUT_ROOT;value=json.loads(packaging.stable(out/'result.json'));runtime=self.runtime_inputs()
        reference,_=shared.reference_inputs()
        baseline=packaging.stable(shared.REFERENCE/'candidate-a/boot.img',expected=reference['candidate']['a']['boot_img'])
        image,transform=self.declaration.artifact.transform_image(packaging.stable(shared.REFERENCE/'inputs/fixed-Image',expected=reference['image']))
        if packaging.stable(out/'inputs/fixed-Image',expected=value['image'])!=image or value['image_transform']!=transform:
            raise ValueError('thermal Image identity transform differs')
        replacements=self.replacements(runtime)
        packages={}
        for side in ('a','b'):
            folder=out/('candidate-'+side);package=value['candidate'][side]
            raw=packaging.stable(folder/'boot.img',expected=package['boot_img'])
            if check_boot(raw,baseline,image,replacements)!=package['inventory']: raise ValueError('thermal boot inventory differs')
            standalone_frame=packaging.stable(folder/'boot.img.lz4',expected=package['boot_img_lz4'])
            inspected=self.declaration.artifact.inspect_ap(folder/'odin4/AP.tar.md5',expected_ap=package['ap_tar_md5'],
                expected_image=image,expected_init=replacements['init'])
            frame,_=shared.artifacts.reference._INNER._parse_ap(packaging.stable(folder/'odin4/AP.tar.md5'),'thermal AP')
            decoded=shared.boot.decompress_lz4_frame_python(frame,maximum=128*1024*1024)
            if frame!=standalone_frame or decoded!=raw or check_boot(decoded,baseline,image,replacements)!=package['inventory']:
                raise ValueError('thermal actual AP payload join differs')
            structure=inspected['ap_structure']
            packages[side]=dict(boot_img=packaging.identity(raw),boot_img_lz4=packaging.identity(frame),ap_tar_md5=inspected['ap'],
                inventory=check_boot(raw,baseline,image,replacements),ap_structure=dict(
                    members=[structure['member']['name']],**{k:structure[k] for k in ('tar_md5','tar_prefix_size','trailer')}))
        if shared.canonical(value)!=shared.canonical(self.result_value(runtime,image,transform,packages)):
            raise ValueError('thermal package evidence does not regenerate')
        return value

    def result_value(self,runtime,image,transform,packages):
        if packages['a']!=packages['b']: raise ValueError('thermal package A/B differs')
        inventory=packages['a']['inventory']
        return dict(schema='s22plus-native-thermal-build-v1',verdict='PASS_NATIVE_THERMAL_BUILD_H0',
            source_inputs=self.source_receipts(),native_selection=self.native_selection(),run_id_hex=self.declaration.IDENTITY.run_id_hex,
            image=packaging.identity(image),image_transform=transform,init=runtime.get('init',runtime['resident']['init']),renderer=runtime['renderer'],
            provider=runtime['resident']['provider']['module'],thermal_modules=runtime['thermal']['modules'],
            child={k:inventory['s22-e1-child'][k] for k in ('size','sha256')},candidate=packages,byte_identical=True,
            scope=dict(tier='H0',device_contact=False,live_authorized=False,candidate_transfers=0,rollback_transfers=0))


if __name__=='__main__':
    import argparse
    import s22plus_native_baseline_v2_candidates as candidates
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('candidate',choices=tuple(candidates.DECLARATIONS));parser.add_argument('--thermal-input',type=Path)
    parser.add_argument('--runtime-input',type=Path);parser.add_argument('--audit-only',action='store_true')
    args=parser.parse_args();builder=Builder(candidates.DECLARATIONS[args.candidate])
    result=builder.audit_existing() if args.audit_only else builder.build(thermal_input=args.thermal_input,runtime_input=args.runtime_input)
    print(json.dumps(dict(verdict=result['verdict'],candidate=result['candidate']['a']['ap_tar_md5']),sort_keys=True))

#!/usr/bin/env python3
"""Build resident PID1, renderer and read-only gauge provider; host only.

No image/transfer/activation is produced. The frozen P383 platform envelope is
an explicit byte input, shared with the direct P384 builder. New composition and
provider are compiled twice and audited against the exact FYG8 kernel ABI.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[5]
sys.path[:0] = [str(Path(__file__).parent), str(ROOT/'workspace/public/src/scripts/revalidation')]
import s22plus_native_resident_source_v1 as source
import s22plus_native_resident_protocol_v1 as protocol
import s22plus_fyg8_p384_stock_candidate_build as shared
import s22plus_fyg8_telemetry_provider_h0_v3 as telemetry


def canonical(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False)+'\n').encode()


def pin(path):
    return shared.identity(shared.stable(path))


def closure():
    paths = set(source.source_files()) | {Path(__file__), Path(protocol.__file__), Path(shared.__file__),
        Path(telemetry.__file__), Path(shared.packager.__file__), Path(shared.memory.__file__)}
    paths.update(shared.artifacts.reference_source_files())
    return {str(path.relative_to(ROOT)): pin(path) for path in sorted(paths)}


def build_provider(out):
    out.mkdir(mode=0o700)
    if pin(telemetry.IMAGE)['sha256'] != telemetry.IMAGE_SHA:
        raise ValueError('exact FYG8 Image differs')
    base=json.loads(telemetry.COMMAND.read_text());kernel=Path(base['argv'][2])
    inputs=[telemetry.PREPARED/'.config', telemetry.PREPARED/'Module.symvers', telemetry.COMMAND,
        kernel/'include/linux/mfd/max77705-private.h', kernel/'include/linux/timekeeping.h', kernel/'kernel/params.c']
    pins={str(path.relative_to(ROOT)):pin(path) for path in inputs}
    shutil.copytree(telemetry.PREPARED,out/'kernel-out',symlinks=True)
    (out/'module-stage').mkdir(mode=0o700)
    for name,raw in source.provider_sources().items():shared.write(out/'module-stage'/name,raw)
    env=dict(base['env']);env['GIT_CEILING_DIRECTORIES']=str(out)
    argv=['make','-C',str(kernel),f'O={out/"kernel-out"}','-j2',f'M={out/"module-stage"}']
    shared.write(out/'build-command.json',canonical(dict(argv=argv,env=env)))
    for side in ('a','b'):
        with (out/f'build-{side}.log').open('xb') as log:
            if side=='b':subprocess.run([*argv,'clean'],env=env,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=180)
            subprocess.run([*argv,'modules'],env=env,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=180)
        shared.write(out/f'module-{side}.ko',shared.stable(out/'module-stage'/telemetry.MODULE))
    if pin(out/'module-a.ko')!=pin(out/'module-b.ko'):raise ValueError('resident provider A/B differs')
    imports=telemetry.linkage._imports(out/'module-a.ko')
    expected=(telemetry.ALLOWED_IMPORTS-{'ktime_get'})|{'ktime_get_with_offset'}
    if set(imports)!=expected:raise ValueError('resident imports differ: '+repr(set(imports)^expected))
    exports=telemetry.linkage._image_provider_map(telemetry.IMAGE.read_bytes(),telemetry.linkage.IMAGE_SECTION_LAYOUT)
    errors={name:dict(module=crc,image=exports.get(name)) for name,crc in imports.items() if exports.get(name)!=crc}
    if errors:raise ValueError('exact FYG8 export/CRC differs: '+repr(errors))
    for name,before in pins.items():
        if pin(ROOT/name)!=before:raise ValueError('provider inputs changed: '+name)
    description=subprocess.check_output(['file','-b',out/'module-a.ko'],text=True).strip()
    if 'ARM aarch64' not in description or 'relocatable' not in description:raise ValueError('provider ELF differs')
    result=dict(module=pin(out/'module-a.ko'),ab_identical=True,imports=imports,inputs=pins,
                image=pin(telemetry.IMAGE),file=description,boottime_import_crc=imports['ktime_get_with_offset'])
    shared.write(out/'result.json',canonical(result));return result


def reuse_provider(previous, out):
    previous=Path(previous).absolute()
    if not previous.resolve().is_relative_to((ROOT/'workspace/private/outputs').resolve()):
        raise ValueError('provider input must be a private H0 result')
    result=json.loads(shared.stable(previous/'result.json'))
    for name,raw in source.provider_sources().items():
        if shared.stable(previous/'module-stage'/name)!=raw:raise ValueError('provider source bytes changed')
    for name,before in result['inputs'].items():
        if pin(ROOT/name)!=before:raise ValueError('provider kernel inputs changed')
    if pin(telemetry.IMAGE)!=result['image']:raise ValueError('provider Image changed')
    if pin(previous/'module-a.ko')!=result['module'] or pin(previous/'module-b.ko')!=result['module']:
        raise ValueError('retained provider A/B artifact differs')
    imports=telemetry.linkage._imports(previous/'module-a.ko')
    expected=(telemetry.ALLOWED_IMPORTS-{'ktime_get'})|{'ktime_get_with_offset'}
    exports=telemetry.linkage._image_provider_map(telemetry.IMAGE.read_bytes(),telemetry.linkage.IMAGE_SECTION_LAYOUT)
    if imports!=result['imports'] or set(imports)!=expected or any(exports.get(k)!=v for k,v in imports.items()):
        raise ValueError('retained provider import/CRC differs')
    out.mkdir(mode=0o700)
    for name in ('module-a.ko','module-b.ko'):shared.write(out/name,shared.stable(previous/name))
    for name,raw in source.provider_sources().items():shared.write(out/'module-stage'/name,raw)
    shared.write(out/'result.json',canonical(result));return result


def build(out, provider_input=None):
    out=Path(out).absolute()
    if out.exists() or out.is_symlink() or not out.resolve().is_relative_to((ROOT/'workspace/private/outputs').resolve()):
        raise ValueError('fresh private output required')
    inputs=closure();reference,sources=shared.reference_inputs()
    print('SOURCE_KEYS '+json.dumps(sorted(inputs)),flush=True)
    out.mkdir(mode=0o700,parents=True);shared.write(out/'source-inputs.json',canonical(inputs))
    for path,identity in reference['toolchain_inputs'].items():shared.stable(Path(path),expected=identity)
    provider=reuse_provider(provider_input,out/'provider') if provider_input else build_provider(out/'provider')
    identity=source.common.Identity('p386',hashlib.sha256(canonical(inputs)).hexdigest()[:32],'v0.2.0-rc.4')
    runtime=sources[shared.packager.RUNTIME_INCLUDE_NAME]
    match=re.findall(rb'static const uint8_t p328_auth_key\[P328_AUTH_KEY_SIZE\] = \{ ([^}]+) \};',runtime)
    if len(match)!=1:raise ValueError('frozen key declaration differs')
    key=bytes(int(v.strip().removesuffix(b'U'),16) for v in match[0].split(b','))
    joined=source.join_platform(runtime,shared.REFERENCE_IDENTITY,key)
    joined=source.replace(joined,source.materialize_helper(shared.REFERENCE_IDENTITY,key),source.materialize_helper(identity,key))
    if b'p383' in joined or b'P383' in joined or shared.REFERENCE_IDENTITY.run_id_hex.encode() in joined:
        raise ValueError('old namespace remains in resident runtime')
    for name,raw in sources.items():shared.write(out/'stock-sources'/name,joined if name==shared.packager.RUNTIME_INCLUDE_NAME else raw)
    shared.write(out/'inputs/child-source.c',shared.stable(shared.REFERENCE/'inputs/child-source.c',expected=shared.packager.CHILD_SOURCE_IDENTITY))
    # The renderer's fixed module plan consumes the new provider's exact size.
    plan=shared.stable(shared.REFERENCE/'inputs/s22plus_native_display_plan.h',expected=reference['module_plan'])
    matches=re.findall(rb'("/s22-display-modules/s22plus_max77705_telemetry.ko", )([0-9]+)(ULL, 0)',plan)
    if len(matches)!=1:raise ValueError('provider plan entry differs')
    a,b,c=matches[0];plan=source.replace(plan,a+b+c,a+str(provider['module']['size']).encode()+c)
    shared.write(out/'inputs/s22plus_native_display_plan.h',plan)
    census=tuple(source.common.MemoryModule(*row) for row in shared.memory.manifest())
    shared.write(out/'inputs/renderer.c',source.render_display(identity,census))
    tools=shared.packager._bind_tools();previous=shared.packager.RUN_ID
    try:
        shared.packager.RUN_ID=bytes.fromhex(identity.run_id_hex)
        userspace=[shared.packager._compile_userspace(out/'stock-sources',out/('userspace-'+side),label='resident-'+side) for side in ('a','b')]
    finally:shared.packager.RUN_ID=previous
    if userspace[0]!=userspace[1]:raise ValueError('resident native A/B differs')
    compiler=[tools['gcc'],*shared.RENDERER_FLAGS,'-I',out/'inputs','-I',shared.HEADERS,'-I',source.NATIVE,out/'inputs/renderer.c']
    for side in ('a','b'):shared.run([*compiler,'-o',out/('renderer-'+side)],out,out/('renderer-'+side+'.log'))
    if pin(out/'renderer-a')!=pin(out/'renderer-b'):raise ValueError('resident renderer A/B differs')
    descriptions={}
    for name,path in (('init',out/'userspace-a/init'),('renderer',out/'renderer-a')):
        text=shared.run([tools['file'],'-b',path],out,out/(name+'-file.log')).decode().strip()
        elf=shared.run([tools['readelf'],'-W','-l',path],out,out/(name+'-readelf.log'))
        if 'ARM aarch64' not in text or 'statically linked' not in text or b'INTERP' in elf:raise ValueError('resident static ELF differs')
        descriptions[name]=text
    if closure()!=inputs:raise ValueError('resident sources changed during build')
    for path,before in reference['toolchain_inputs'].items():shared.stable(Path(path),expected=before)
    result=dict(schema='s22plus-native-resident-build-h0-v1',verdict='PASS_RESIDENT_BUILD_H0',
        source_inputs=inputs,reference_result=shared.REFERENCE_RESULT,profile=source.profile_contract(),
        run_id_hex=identity.run_id_hex,init=pin(out/'userspace-a/init'),renderer=pin(out/'renderer-a'),
        provider=provider,ab_identical=True,file=descriptions,toolchain_inputs=reference['toolchain_inputs'],
        scope=dict(tier='H0',device_contact=False,live_authorized=False,boot_image_created=False),
        limitations=['not a live soak or sensor exposure proof','no new candidate registration, transfer or recovery qualification'])
    shared.write(out/'result.json',canonical(result));return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--provider-input',type=Path)
    args=parser.parse_args();value=build(args.out,args.provider_input)
    print(json.dumps({key:value[key] for key in ('verdict','init','renderer','ab_identical')},sort_keys=True))

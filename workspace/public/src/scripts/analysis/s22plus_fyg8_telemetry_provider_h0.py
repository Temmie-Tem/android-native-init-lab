#!/usr/bin/env python3
"""Build and qualify the prospective fixed fuel-gauge module on the host only."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[5]
sys.path.insert(0,str(ROOT/'workspace/public/src/scripts/revalidation'))
import s22plus_fyg8_p319_stock_candidate_build as linkage
SOURCE=ROOT/'workspace/public/src/kernel-modules/s22plus_max77705_telemetry'
PREPARED=ROOT/'workspace/private/outputs/s22-display-build-h0/vendor-kernel-out'
COMMAND=ROOT/'workspace/private/outputs/s22-display-provider-h0/scoped-build-command.json'
IMAGE=ROOT/'workspace/private/outputs/s22plus-fyg8-v0.1.1-rc.1/candidate-build-final/inputs/fixed-Image'
IMAGE_SHA='23e816116278d637a33b354f8bf735c550060ba6ee98fea697098795e8aa3074'
DEFAULT=ROOT/'workspace/private/outputs/s22plus-telemetry-provider-qualified-v3'
MODULE='s22plus_max77705_telemetry.ko'
ALLOWED_IMPORTS=frozenset('''module_layout __cfi_slowpath __platform_driver_register
__stack_chk_fail __stack_chk_guard arm64_const_caps_ready cpu_hwcap_keys
i2c_smbus_read_byte_data i2c_smbus_read_word_data i2c_verify_client ktime_get
mutex_lock mutex_trylock mutex_unlock of_device_is_compatible
of_find_node_opts_by_path of_property_read_string of_property_read_variable_u32_array
platform_driver_unregister scnprintf strcmp'''.split())


def identity(path):
    raw=path.read_bytes()
    return {'size':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}


def build(out):
    out=out.absolute()
    if not out.is_relative_to(ROOT/'workspace/private/outputs') or out.exists():
        raise ValueError('fresh private output required')
    assert identity(IMAGE)['sha256']==IMAGE_SHA
    source_paths=[SOURCE/n for n in ('Makefile','telemetry_core.h','s22plus_max77705_telemetry.c')]
    base=json.loads(COMMAND.read_text());kernel=Path(base['argv'][2])
    inputs=source_paths+[PREPARED/'.config',PREPARED/'Module.symvers',COMMAND,
        kernel/'include/linux/mfd/max77705-private.h',Path(linkage.__file__),Path(__file__)]
    pins={str(p.relative_to(ROOT)):identity(p) for p in inputs}
    out.mkdir(parents=True,mode=0o700)
    shutil.copytree(PREPARED,out/'kernel-out',symlinks=True)
    shutil.copytree(SOURCE,out/'module-stage')
    env=dict(base['env']);env['GIT_CEILING_DIRECTORIES']=str(out)
    argv=['make','-C',str(kernel),f'O={out/"kernel-out"}','-j2',f'M={out/"module-stage"}']
    (out/'build-command.json').write_text(json.dumps({'argv':argv,'env':env},indent=2)+'\n')
    modules={}
    for side in ('a','b'):
        with (out/f'build-{side}.log').open('wb') as log:
            if side=='b':subprocess.run([*argv,'clean'],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
            subprocess.run([*argv,'modules'],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
        dest=out/f'module-{side}.ko';shutil.copyfile(out/'module-stage'/MODULE,dest);dest.chmod(0o400)
        modules[side]=identity(dest)
    if modules['a']!=modules['b']:raise ValueError('A/B module mismatch')
    binary=out/'module-a.ko'
    description=subprocess.check_output(['file',binary],text=True)
    assert 'ARM aarch64' in description and 'relocatable' in description
    imports=linkage._imports(binary)
    if set(imports)!=ALLOWED_IMPORTS:raise ValueError('unexpected module imports: '+repr(set(imports)^ALLOWED_IMPORTS))
    exports=linkage._image_provider_map(IMAGE.read_bytes(),linkage.IMAGE_SECTION_LAYOUT)
    errors={name:{'module':crc,'Image':exports.get(name)} for name,crc in imports.items() if exports.get(name)!=crc}
    if errors:raise ValueError('exact Image symbol/CRC mismatch: '+repr(errors))
    for relative,pin in pins.items():
        if identity(ROOT/relative)!=pin:raise ValueError('source changed during build: '+relative)
    result={'schema':'s22plus_fyg8_telemetry_provider_h0_v1','verdict':'PASS_TELEMETRY_PROVIDER_BUILD_H0',
        'device_contact':False,'live_authorized':False,'module':modules['a'],'ab_identical':True,
        'image':identity(IMAGE),'imports':imports,'source_inputs':pins,
        'file':description.strip(),'vermagic':subprocess.check_output(['modinfo','-F','vermagic',binary],text=True).strip(),
        'limitations':['build/linkage is not live probe or hardware-read proof','no new parent, dummy client, IRQ or firmware path','exact child and parent ABI still required at runtime']}
    (out/'result.json').write_text(json.dumps(result,sort_keys=True,indent=2)+'\n')
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,default=DEFAULT)
    result=build(parser.parse_args().out)
    print(json.dumps({'verdict':result['verdict'],'module':result['module']},sort_keys=True))

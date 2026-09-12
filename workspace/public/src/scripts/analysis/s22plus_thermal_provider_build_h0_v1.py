#!/usr/bin/env python3
"""Build exact thermal telemetry and bind inherited ADC modules; no device IO."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[5]
sys.path[:0] = [str(Path(__file__).parent),str(ROOT/'workspace/public/src/scripts/revalidation')]
import s22plus_fyg8_telemetry_provider_h0_v3 as existing
import s22plus_memory_manifest_v1 as memory

SOURCE = ROOT/'workspace/public/src/kernel-modules/s22plus_thermal_telemetry_v1'
PARTS = ('Makefile','thermal_core.h','s22plus_thermal_telemetry.c')
STOCK_MODULES = ('qcom-vadc-common.ko','qcom-spmi-adc5.ko')
MODULE = 's22plus_thermal_telemetry.ko'
MODULE_ORDER = (*STOCK_MODULES,MODULE)
identity = existing.identity


def write(path,raw):
    path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    with path.open('xb') as file: file.write(raw)
    path.chmod(0o400)


def canonical(value):
    return (json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()


def source_files(profile=None):
    return (Path(__file__),*(profile.provider_files() if profile else (SOURCE/name for name in PARTS)))


def staged_sources(profile=None):
    rows=profile.provider_sources() if profile else {name:(SOURCE/name).read_bytes() for name in PARTS}
    if set(rows)!=set(PARTS):raise ValueError('thermal provider source inventory differs')
    return rows


def vendor_modules():
    vendor = memory.vendor
    path = ROOT/vendor.DEFAULT_VENDOR_RAMDISK
    expected = dict(size=vendor.EXPECTED_VENDOR_RAMDISK_SIZE,sha256=vendor.EXPECTED_VENDOR_RAMDISK_SHA256)
    raw = memory.base.stable(path,expected)
    decoded = memory.boot_verify.decompress_lz4_stream_python(raw,maximum=128*1024*1024)
    if len(decoded) != vendor.EXPECTED_VENDOR_NEWC_SIZE: raise ValueError('sealed vendor ramdisk size differs')
    entries = memory.boot_verify.parse_newc(decoded)
    rows = {entry.name:entry for entry in entries}
    if len(rows) != len(entries): raise ValueError('duplicate vendor module entry')
    selected = {}
    for name in STOCK_MODULES:
        row = rows['lib/modules/'+name]
        if (row.mode,row.uid,row.gid,row.nlink) != (0o100644,0,0,1):
            raise ValueError('stock ADC module metadata differs')
        selected[name] = row.data
    return selected,dict(path=str(path.relative_to(ROOT)),**expected)


def inputs(profile=None):
    base = json.loads(existing.COMMAND.read_text());kernel = Path(base['argv'][2])
    paths = [*source_files(profile),Path(existing.__file__),Path(memory.__file__),Path(existing.linkage.__file__),
        existing.COMMAND,existing.PREPARED/'.config',existing.PREPARED/'Module.symvers']
    paths += [kernel/name for name in (
        'include/linux/iio/consumer.h','include/linux/iio/types.h','include/linux/of.h',
        'include/linux/of_platform.h','include/linux/io.h','include/linux/ioport.h',
        'include/linux/timekeeping.h','kernel/params.c','drivers/iio/inkern.c',
        'drivers/iio/adc/qcom-spmi-adc5.c','drivers/iio/adc/qcom-vadc-common.c',
        'drivers/iio/adc/qcom-vadc-common.h','drivers/thermal/qcom/tsens-v2.c',
        'drivers/thermal/qcom/tsens.c',
        'arch/arm64/boot/dts/samsung/rainbow/g0q/g0q_kor_singlex_w00_r12.dts')]
    paths.append(kernel.parent/'qcom/proprietary/devicetree/qcom/waipio-thermal.dtsi')
    return {str(path.relative_to(ROOT)):identity(path) for path in sorted(set(paths))}


def linkage(out):
    exports = existing.linkage._image_provider_map(existing.IMAGE.read_bytes(),existing.linkage.IMAGE_SECTION_LAYOUT)
    result = {}
    for name in MODULE_ORDER:
        path = out/'modules'/name
        imports = existing.linkage._imports(path)
        errors = {symbol:dict(required=crc,provider=exports.get(symbol))
            for symbol,crc in imports.items() if exports.get(symbol) != crc}
        if errors: raise ValueError('thermal exact-Image/module ABI mismatch '+name+': '+repr(errors))
        provided = existing.linkage._exports(path)
        if set(provided)&set(exports): raise ValueError('thermal duplicate exports: '+name)
        exports.update(provided)
        description = subprocess.check_output(['file','-b',path],text=True).strip()
        if 'ARM aarch64' not in description or 'relocatable' not in description:
            raise ValueError('thermal module ELF differs')
        result[name] = dict(identity=identity(path),imports=imports,exports=provided,file=description,
            vermagic=subprocess.check_output(['modinfo','-F','vermagic',path],text=True).strip())
    return result


def result_value(pins,origin,modules,profile=None):
    result=dict(schema='s22plus-thermal-provider-build-h0-v1',verdict='PASS_THERMAL_PROVIDER_BUILD_H0',
        inputs=pins,module_order=list(MODULE_ORDER),modules=modules,stock_origin=origin,image=identity(existing.IMAGE),
        ab_identical=True,device_contact=False,live_authorized=False,
        hardware_effects=dict(tsens='fixed-register-reads-only',battery='one-stock-ADC7-conversion-per-eligible-read',
            adc_configuration_writes=True,adc_eoc_irq=True,battery_driver_binding=False,charger_driver=False),
        limitations=['ABI compatibility does not prove exact stock source correspondence',
            'TSENS hardware conversion age unknown','single ADC conversion is not stock five-read filtering',
            'adc-temp and adc-wpc-temp share the board channel','no live probe or temperature proof'])
    if profile is not None:result['thermal_profile']=profile.THERMAL_PROFILE
    return result


def build(out,*,profile=None):
    out = Path(out).absolute()
    if out.resolve() != out or not out.is_relative_to(ROOT/'workspace/private/outputs') or out.exists():
        raise ValueError('fresh direct private thermal output required')
    pins = inputs(profile);stock,origin = vendor_modules()
    if identity(existing.IMAGE)['sha256'] != existing.IMAGE_SHA: raise ValueError('exact kernel Image changed')
    out.mkdir(parents=True,mode=0o700)
    shutil.copytree(existing.PREPARED,out/'kernel-out',symlinks=True)
    for name,raw in staged_sources(profile).items():write(out/'module-stage'/name,raw)
    base = json.loads(existing.COMMAND.read_text());kernel = Path(base['argv'][2])
    env = dict(base['env']);env['GIT_CEILING_DIRECTORIES'] = str(out)
    argv = ['make','-C',str(kernel),f'O={out/"kernel-out"}','-j2',f'M={out/"module-stage"}']
    write(out/'build-command.json',canonical(dict(argv=argv,env=env)))
    for side in ('a','b'):
        with (out/f'build-{side}.log').open('xb') as log:
            if side == 'b': subprocess.run([*argv,'clean'],env=env,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=180)
            subprocess.run([*argv,'modules'],env=env,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=180)
        write(out/('module-'+side+'.ko'),(out/'module-stage'/MODULE).read_bytes())
    if identity(out/'module-a.ko') != identity(out/'module-b.ko'): raise ValueError('thermal A/B module differs')
    for name,raw in stock.items(): write(out/'modules'/name,raw)
    write(out/'modules'/MODULE,(out/'module-a.ko').read_bytes())
    modules = linkage(out)
    if inputs(profile) != pins: raise ValueError('thermal source changed during build')
    result = result_value(pins,origin,modules,profile)
    write(out/'result.json',canonical(result))
    return audit(out,profile=profile)


def audit(out,*,profile=None):
    out = Path(out).absolute();value = json.loads((out/'result.json').read_text())
    if out.resolve()!=out or not out.is_relative_to(ROOT/'workspace/private/outputs'):
        raise ValueError('thermal provider path must be a direct private output')
    if identity(existing.IMAGE)['sha256'] != existing.IMAGE_SHA: raise ValueError('exact kernel Image changed')
    stock,origin = vendor_modules()
    if value['stock_origin'] != origin: raise ValueError('thermal stock origin differs')
    for name,raw in stock.items():
        if (out/'modules'/name).read_bytes() != raw: raise ValueError('thermal stock module changed')
    for name,raw in staged_sources(profile).items():
        if (out/'module-stage'/name).read_bytes() != raw: raise ValueError('thermal staged source changed')
    for name in ('module-a.ko','module-b.ko'):
        if (out/name).read_bytes() != (out/'modules'/MODULE).read_bytes(): raise ValueError('thermal A/B artifact changed')
    if canonical(value)!=canonical(result_value(inputs(profile),origin,linkage(out),profile)):
        raise ValueError('thermal provider evidence does not regenerate')
    return value


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True);parser.add_argument('--audit-only',action='store_true')
    args = parser.parse_args();result = audit(args.out) if args.audit_only else build(args.out)
    print(json.dumps(dict(verdict=result['verdict'],modules={k:v['identity'] for k,v in result['modules'].items()}),sort_keys=True))

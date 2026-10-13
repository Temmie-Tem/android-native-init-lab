"""Shared storage-first module construction; fixed data, no device calls."""
import json
import early
import fyg8
import h0
import integrated
import usb_first
import s22plus_debian_file_first_plan_v1 as plan


def prepare_modules(out,inputs,inventory,run,key,virt,diagnostic=False,diagnostic_fault=None):
    _,logger=usb_first.modules(inputs,'retained')
    modules=plan.modules(inventory,usb_first.LOGGER)
    (out/usb_first.LOGGER['name']).write_bytes(logger)
    (out/'usb-first-key.h').write_text(early.array('early_key',key)+early.array('early_run',bytes.fromhex(run)))
    (out/'s22plus_native_ext4_seal_v1.h').write_bytes(fyg8.ext4.seal(fyg8.filesystem.BINDING,run,initialize=False))
    text=['struct fyg8_module {const char *path,*runtime,*parameters; uint64_t size; uint8_t hash[32];};',
        'static const char fyg8_release[]='+json.dumps(fyg8.KERNEL_RELEASE)+';',
        'static const char fyg8_model[]='+json.dumps(fyg8.MODEL)+';',
        'static const struct fyg8_module fyg8_modules[]={']
    for row in modules:
        text.append('{'+','.join(json.dumps(v) for v in ('/lab/modules/'+row['name'],row['runtime_name'],row['parameters']))+
            ','+str(row['size'])+'ULL,{'+','.join(map(str,bytes.fromhex(row['sha256'])))+'}},')
    (out/'fyg8-plan.h').write_text('\n'.join(text+['};'])+'\n')
    (out/'file-first-plan.h').write_text('#define FF_STORAGE_COUNT '+str(plan.STORAGE_COUNT)+'U\n'+
        '#define FF_CLIENT_COUNT '+str(len(plan.CLIENTS))+'U\n')
    tail=['static const struct {const char *path,*name;uint64_t size;uint8_t hash[32];} fl_clients[]={']
    for row in modules[plan.STORAGE_COUNT:]:
        tail.append('{'+json.dumps('/lab/modules/'+row['name'])+','+json.dumps(row['runtime_name'])+','+
            str(row['size'])+'ULL,{'+','.join(map(str,bytes.fromhex(row['sha256'])))+'}},')
    (out/'file-first-tail.h').write_text('\n'.join(tail+['};'])+'\n')
    (out/'integrated-provider-plan.h').write_bytes(integrated.provider_plan())
    # Recheck CRC suppliers against actual bytes in the new order, independently
    # of the inventory's descriptive dependency fields.
    providers=fyg8.linkage._image_provider_map((inputs/'fixed-Image').read_bytes(),fyg8.linkage.IMAGE_SECTION_LAYOUT)
    loaded=set();audit=[]
    for row in modules:
        source=out/row['name'] if row==usb_first.LOGGER else inputs/'modules'/row['name']
        depends=fyg8.capture(['modinfo','-F','depends',source],out/(row['name']+'.depends'))
        wanted={v.replace('-','_') for v in depends.split(',') if v}
        h0.require(wanted<=loaded,'actual module dependency follows consumer')
        raw=fyg8.capture(['modprobe','--dump-modversions',source],out/(row['name']+'.imports'))
        imports={symbol:fyg8.linkage._norm_crc(crc) for crc,symbol in [line.split() for line in raw.splitlines()]}
        h0.require(imports and all(providers.get(s)==crc for s,crc in imports.items()),'new order module CRC mismatch')
        raw=fyg8.capture(['aarch64-linux-gnu-nm','-g','--defined-only',source],out/(row['name']+'.exports'))
        for line in raw.splitlines():
            fields=line.split()
            if len(fields)>=3 and fields[-1].startswith('__crc_'):
                symbol=fields[-1][6:];h0.require(symbol not in providers,'duplicate module export')
                providers[symbol]=fyg8.linkage._norm_crc(fields[0])
        loaded.add(row['runtime_name']);audit.append(dict(name=row['runtime_name'],imports=len(imports),dependencies=sorted(wanted)))
    h0.publish(out/'module-order-audit.json',audit)
    includes=['-I',out,'-I',fyg8.ext4.NATIVE,'-I',h0.HERE,
        '-DEARLY_DOMAIN='+json.dumps(('S22PLUS-FYG8-DEBIAN-FAILURE-v1' if diagnostic else plan.DOMAIN.decode()))]
    if diagnostic:includes+=['-DS22_FAILURE_OBSERVER']
    if virt:includes+=['-DFYG8_VM_TEST','-DEARLY_VM_TEST']
    source=h0.HERE/'file-first-prepare.c'
    if diagnostic_fault:
        import failure_faults
        h0.require(virt and diagnostic,'diagnostic faults require virtual diagnostic build')
        source=failure_faults.source(out,source,diagnostic_fault)
    for side in 'ab':
        h0.run(['aarch64-linux-gnu-gcc',*integrated.FLAGS,*includes,source,
            '-o',out/('fyg8-prepare-'+side)],out/('module-compile-'+side+'.log'))
    h0.require((out/'fyg8-prepare-a').read_bytes()==(out/'fyg8-prepare-b').read_bytes(),'storage helper A/B differs')
    (out/'fyg8-prepare').write_bytes((out/'fyg8-prepare-a').read_bytes())
    return modules

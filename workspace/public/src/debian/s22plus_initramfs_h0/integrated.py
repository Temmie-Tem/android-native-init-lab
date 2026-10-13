#!/usr/bin/env python3
"""One Debian-owned platform/root/init/services candidate; H0 construction only."""
import argparse
import json
from pathlib import Path
import re
import secrets
import shutil
import subprocess
import sys
import uuid

import early
import fyg8
import h0
import usb_first
import s22plus_debian_handoff_h0 as handoff
from s22plus_native_records_v3 import pin,read,verify

NAMESPACE='p425'
VERSION='v0.6.0-rc.1'
PROFILE='debian-integrated-v1'
DOMAIN='S22PLUS-FYG8-DEBIAN-INTEGRATED-v1'
NATIVE=fyg8.ext4.NATIVE
FLAGS=('-static','-Os','-Wall','-Wextra','-Werror','-Wno-unused-function','-Wno-unused-const-variable',
       '-ffunction-sections','-fdata-sections','-Wl,--gc-sections','-fno-ident','-Wl,--build-id=none')


def provider_plan():
    source=(NATIVE/'s22plus_fyg8_p317_max77705_runtime.inc.c').read_text().replace('\\\n','')
    declarations=dict(re.findall(r'#define (P317_[A-Z_]+)\s+"([^"\n]+)"',source))
    block=source.split('static const struct p317_provider_spec p317_providers[] = {',1)[1].split('};',1)[0]
    rows=re.findall(r'\{(P317_[A-Z_]+), (P317_[A-Z_]+), "([A-Za-z0-9_-]+)"\}',block)
    h0.require(len(rows)==3,'fixed pre-client provider declaration differs')
    values=[(declarations[root],declarations[dt],driver) for root,dt,driver in rows]
    h0.require([r[2] for r in values]==['spmi_pmic_arb','pmic-spmi','qcom-spmi-gpio'],
        'pre-client driver identity differs')
    return ('static const struct di_provider di_providers_plan[]={\n'+
        ''.join('{'+','.join(json.dumps(s) for s in row)+'},\n' for row in values)+'};\n').encode()


def dev_script():
    text=(h0.HERE/'fyg8-dev').read_text()
    anchor='mknod -m 666 /dev/null c 1 3 || fyg8_stop\n'
    h0.require(text.count(anchor)==1 and text.endswith('fyg8_stop\n'),'Debian RAM hook changed')
    text=text.replace(anchor,anchor+'mknod -m 600 /dev/kmsg c 1 11 || fyg8_stop\n')
    begin=text.index('/sbin/fyg8-prepare\n')
    return text[:begin]+'''/sbin/fyg8-prepare platform
fyg8_status=$?
[ "$fyg8_status" = 0 ] || fyg8_stop
/sbin/integrated-measure "$fyg8_status" || fyg8_stop
exec /sbin/integrated-init
fyg8_stop
'''


def compile_unit(out,name,source,*,virt=False,handoff_headers=None):
    includes=['-I',out,'-I',NATIVE,'-I',h0.HERE]
    if handoff_headers is not None:includes+=['-I',handoff_headers,'-DS22_DEBIAN_HANDOFF']
    if virt:includes+=['-DFYG8_VM_TEST','-DEARLY_VM_TEST',
        *(['-DS22_ROOT_INSPECT_VIRT_TEST'] if handoff_headers is not None else [])]
    for side in 'ab':
        h0.run(['aarch64-linux-gnu-gcc',*FLAGS,*includes,h0.HERE/source,'-o',out/(name+'-'+side)],out/(name+'-'+side+'.compile.log'))
    h0.require((out/(name+'-a')).read_bytes()==(out/(name+'-b')).read_bytes(),'integrated ELF A/B differs')
    shutil.copyfile(out/(name+'-a'),out/name)
    h0.run(['file',out/name],out/(name+'.file.log'))
    return pin(out/name,maximum=8*1024**2)


def prepare(out,inputs,packages,*,run=None,key=None,virt=False,fresh=True):
    out=h0.private(out,fresh=fresh);inputs=h0.private(inputs);packages=h0.private(packages)
    sources=snapshot(out) if fresh else read(out/'source-inputs.json')
    h0.verify_packages(packages,out);inventory=fyg8.verify_inventory(inputs)
    modules,logger=usb_first.modules(inputs,'retained')
    platform_count=len(modules);modules=modules+inventory['modules'][inventory['platform_count']:]
    h0.require(len(modules)==82 and platform_count==74,'integrated module scope differs')
    names=[m['runtime_name'] for m in modules]
    index=names.index('qcom_spmi_pmic')
    h0.require(names[index+1:platform_count]==['msm_geni_se','gpi','i2c_msm_geni',
        'spu_verify','mfd_max77705','pdic_max77705'],
        'pre-client provider insertion boundary differs')
    run=run or uuid.uuid4().hex;key=key or secrets.token_bytes(32)
    h0.require(re.fullmatch('[0-9a-f]{32}',run) and len(key)==32,'integrated identity differs')
    (out/'key').write_bytes(key);(out/'key').chmod(0o400)
    (out/usb_first.LOGGER['name']).write_bytes(logger)
    providers=fyg8.linkage._image_provider_map((inputs/'fixed-Image').read_bytes(),fyg8.linkage.IMAGE_SECTION_LAYOUT)
    raw=fyg8.capture(['modprobe','--dump-modversions',out/usb_first.LOGGER['name']],out/'logger-imports.txt')
    imports={symbol:fyg8.linkage._norm_crc(crc) for crc,symbol in [line.split() for line in raw.splitlines()]}
    h0.require(len(imports)==71 and all(providers.get(s)==c for s,c in imports.items()),'logger/Image ABI differs')
    (out/'usb-first-key.h').write_text(early.array('early_key',key)+early.array('early_run',bytes.fromhex(run)))
    (out/'s22plus_native_ext4_seal_v1.h').write_bytes(fyg8.ext4.seal(fyg8.filesystem.BINDING,run,initialize=False))
    text=['struct fyg8_module {const char *path,*runtime,*parameters; uint64_t size; uint8_t hash[32];};',
        'static const char fyg8_release[]='+json.dumps(fyg8.KERNEL_RELEASE)+';',
        'static const char fyg8_model[]='+json.dumps(fyg8.MODEL)+';',
        '#define DI_PLATFORM_COUNT '+str(platform_count)+'U',
        '#define DI_MODULE_COUNT '+str(len(modules))+'U','static const struct fyg8_module fyg8_modules[]={']
    for row in modules:
        text.append('{'+','.join(json.dumps(v) for v in ('/lab/modules/'+row['name'],row['runtime_name'],row['parameters']))+
            ','+str(row['size'])+'ULL,{'+','.join(map(str,bytes.fromhex(row['sha256'])))+'}},')
    (out/'fyg8-plan.h').write_text('\n'.join(text+['};'])+'\n')
    (out/'integrated-provider-plan.h').write_bytes(provider_plan())
    plan=(inputs/'platform-plan.h').read_text().split('s22plus_o2_bind_gates[] = {',1)[1].split('};',1)[0]
    gates=re.findall(r'"(/sys/[^"\n]+)"',plan);h0.require(len(gates)==12,'USB gate set differs')
    (out/'usb-first-gates.h').write_text('static const char *const usb_gates_paths[]={'+
        ','.join(json.dumps(v) for v in gates)+'};\n')
    helper=compile_unit(out,'fyg8-prepare','integrated-prepare.c',virt=virt)
    original=(packages/'root/usr/share/initramfs-tools/init').read_bytes()
    needle=b'mount -t devtmpfs -o nosuid,mode=0755 udev /dev\n'
    h0.require(original.count(needle)==1,'Debian /init adaptation differs')
    init=original.replace(needle,b'. /scripts/fyg8-dev\n');shell=early.shell_input(packages)
    measured=dict(shell_sha256=fyg8.digest(shell),init_sha256=fyg8.digest(init),helper_sha256=helper['sha256'])
    seal=early.array('early_key',key)+early.array('early_run',bytes.fromhex(run))
    for field,label in (('shell','shell_sha256'),('init','init_sha256'),('helper','helper_sha256')):
        seal+=early.array('early_'+field+'_hash',bytes.fromhex(measured[label]))
    seal+='static const uint64_t early_helper_size='+str(helper['size'])+'ULL;\n'
    seal+='static const char early_release[]='+json.dumps(fyg8.KERNEL_RELEASE)+';\n'
    seal+='static const char early_model[]='+json.dumps(fyg8.MODEL)+';\n'
    # Reuse the already installed exact-run ACM permissions and holder guard.
    # The integrated protocol's distinct domain carries its different meaning.
    seal+='static const char early_serial[]='+json.dumps('S22E3'+run)+';\n'
    seal+='static const char *const early_module_names[]={'+','.join(json.dumps(n) for n in names[:platform_count])+'};\n'
    (out/'early-seal.h').write_text(seal)
    parent=compile_unit(out,'integrated-measure','integrated-measure.c',virt=virt)
    handoff.build(out/'handoff',run,key,namespace=NAMESPACE,version=VERSION,virt=virt)
    installed=read(out/'handoff/result.json')
    entry=compile_unit(out,'integrated-init','integrated-init.c',virt=virt,handoff_headers=out/'handoff')
    result=dict(namespace=NAMESPACE,version=VERSION,profile=PROFILE,run_id=run,virtual=virt,
        inputs=str(inputs),packages=str(packages),modules=modules,platform_count=platform_count,
        provider_barrier_after=names[index],helper=helper,parent_measure=parent,entry=entry,
        handoff=pin(out/'handoff/result.json'),measured=measured,device_actions=0,active=False,
        source_inputs=sources,headers={str(p.relative_to(out)):pin(p) for p in sorted(list(out.glob('*.h'))+list((out/'handoff').glob('*.h')))})
    for row in sources:h0.require(h0.sha(h0.ROOT/row['path'])==row['sha256'],'integrated preparation source changed')
    h0.publish(out/'request.json',result)
    return result


def payloads(out):
    selected=read(verify(read(out/'request.json')['handoff']))
    result={name:pin(out/name) for name in ('fyg8-prepare','integrated-measure','integrated-init')}
    result.update({'s22-switch-witness':selected['witness'],'s22-switch-busybox':selected['busybox'],
        's22-fs-e2fsck':selected['checker'],'s22-root-inspect.table':selected['table']})
    result.update({'s22-debian-'+name:row for name,row in selected['assets'].items()})
    return result


def inside(out):
    selected=read(out/'request.json');inputs=h0.private(selected['inputs']);packages=h0.private(selected['packages'])
    tree=h0.builder_tree(out,packages)
    for name,row in payloads(out).items():
        target=tree/('usr/sbin/'+name if name in ('fyg8-prepare','integrated-measure','integrated-init') else name)
        target.write_bytes(verify(row,maximum=8*1024**2).read_bytes())
        target.chmod(0o400 if name in ('s22-root-inspect.table','s22-debian-inittab','s22-debian-crontab') else 0o500)
    (tree/'lab/modules').mkdir(parents=True)
    for row in selected['modules']:
        path=out/row['name'] if row==usb_first.LOGGER else inputs/'modules'/row['name']
        target=tree/'lab/modules'/row['name'];target.write_bytes(path.read_bytes());target.chmod(0o400)
    conf=tree/'etc/initramfs-tools'
    for directory in ('conf.d','hooks','scripts'):(conf/directory).mkdir(parents=True,exist_ok=True)
    (conf/'initramfs.conf').write_text('MODULES=list\nBUSYBOX=y\nCOMPRESS=gzip\nKEYMAP=n\nRESUME=none\n')
    (conf/'modules').write_text('')
    shutil.copyfile(h0.HERE/'integrated-hook',conf/'hooks/zzzz-integrated');(conf/'hooks/zzzz-integrated').chmod(0o755)
    (conf/'scripts/fyg8-dev').write_text(dev_script());(conf/'scripts/fyg8-dev').chmod(0o755)
    init=tree/'usr/share/initramfs-tools/init';original=init.read_bytes()
    needle=b'mount -t devtmpfs -o nosuid,mode=0755 udev /dev\n';h0.require(original.count(needle)==1,'Debian init changed')
    init.write_bytes(original.replace(needle,b'. /scripts/fyg8-dev\n'))
    (tree/'boot').mkdir(exist_ok=True);shutil.copyfile(inputs/'kernel.config',tree/'boot'/('config-'+fyg8.KERNEL_RELEASE))
    moddir=tree/'usr/lib/modules'/fyg8.KERNEL_RELEASE;moddir.mkdir(parents=True,exist_ok=True)
    for name in ('modules.builtin','modules.builtin.modinfo','modules.order'):(moddir/name).write_text('')
    h0.generate_archives(out,tree,fyg8.KERNEL_RELEASE)


def snapshot(out):
    selected=set(handoff.source_files())|{p for p in h0.HERE.iterdir() if p.is_file() and
        p.suffix in ('.py','.c','.h')}|{h0.HERE/'integrated-hook',h0.HERE/'fyg8-dev',
        NATIVE/'s22plus_fyg8_p317_max77705_runtime.inc.c',NATIVE/'s22plus_fyg8_logger_binding_v1.h'}
    selected.update(h0.ROOT/row['path'] for row in early.snapshot(out))
    records=[]
    for path in sorted(selected):
        target=out/'source-snapshot'/path.relative_to(h0.ROOT);target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(path.read_bytes());records.append(dict(path=str(path.relative_to(h0.ROOT)),sha256=h0.sha(target)))
    h0.publish(out/'source-inputs.json',records);return records


def build(out,inputs,packages):
    out=h0.private(out,fresh=True);sources=snapshot(out)
    selected=prepare(out,inputs,packages,fresh=False)
    h0.run(['unshare','--user','--map-auto','--map-root-user','--mount','--pid','--fork','--mount-proc',
        sys.executable,__file__,'inside','--output',out],out/'namespace-build.log',timeout=700)
    h0.require((out/'initramfs-a.cpio.gz').read_bytes()==(out/'initramfs-b.cpio.gz').read_bytes(),'integrated initramfs A/B differs')
    rows=fyg8.debian_entries(out/'initramfs-a.cpio.gz');entries={e.name:e for e in rows}
    h0.require(len(rows)==len(entries) and entries['lib'].file_type=='directory','vendor overlay layout differs')
    h0.require(fyg8.digest(entries['init'].data)==selected['measured']['init_sha256'] and
        entries['scripts/fyg8-dev'].data==dev_script().encode(),'integrated Debian owner script differs')
    shell=entries['usr/bin/sh']
    bodies=[e.data for e in rows if e.inode==shell.inode and e.file_type=='regular' and e.data]
    h0.require(len(bodies)==1 and fyg8.digest(bodies[0])==selected['measured']['shell_sha256'],
        'integrated actual shell hardlink differs')
    for name,row in payloads(out).items():
        path='usr/sbin/'+name if name in ('fyg8-prepare','integrated-measure','integrated-init') else name
        h0.require(entries[path].data==verify(row,maximum=8*1024**2).read_bytes(),'embedded integrated executable differs')
    h0.require({n for n in entries if n.startswith('lab/modules/')}==
        {'lab/modules/'+row['name'] for row in selected['modules']},'integrated module set differs')
    for row in selected['modules']:
        actual=entries['lab/modules/'+row['name']]
        h0.require(len(actual.data)==row['size'] and fyg8.digest(actual.data)==row['sha256'] and
            (actual.uid,actual.gid,actual.nlink,actual.mode&0o7777)==(0,0,1,0o400),'embedded module differs')
    for row in sources:h0.require(h0.sha(h0.ROOT/row['path'])==row['sha256'],'integrated source changed during build')
    h0.publish(out/'build.json',dict(schema='s22plus-debian-integrated-h0-v1',status='H0_INITRAMFS_BUILT',
        **selected,initramfs=pin(out/'initramfs-a.cpio.gz',maximum=32*1024**2),ab_identical=True))
    print('PASS: integrated A/B initramfs; no device authority')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=('prepare','build','inside'))
    for name in ('output','inputs','packages'):parser.add_argument('--'+name,type=Path,required=name=='output')
    parser.add_argument('--virt',action='store_true');args=parser.parse_args()
    if args.action=='inside':inside(h0.private(args.output))
    elif args.action=='prepare':prepare(args.output,args.inputs,args.packages,virt=args.virt)
    else:build(args.output,args.inputs,args.packages)

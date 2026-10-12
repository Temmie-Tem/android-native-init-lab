#!/usr/bin/env python3
"""H0 Debian shell PID1 / fixed platform / bounded RAM or retained USB evidence."""
import argparse
import difflib
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
from s22plus_native_records_v3 import pin
import s22plus_debian_early_profile_v1 as profile_api

NAMESPACE='p419'
VERSION='v0.5.0-rc.3'
PROFILE='debian-usb-first-v1'
LOGGER=profile_api.LOGGER


def modules(inputs,logging_mode='ram-only'):
    h0.require(logging_mode in profile_api.USB_LOGGING_MODES,'unknown USB logging mode')
    value=fyg8.verify_inventory(inputs)
    platform=value['modules'][:value['platform_count']]
    if logging_mode=='ram-only':return platform,None
    vendor=fyg8.memory.vendor
    raw=fyg8.memory.base.stable(h0.ROOT/vendor.DEFAULT_VENDOR_RAMDISK,
        dict(size=vendor.EXPECTED_VENDOR_RAMDISK_SIZE,sha256=vendor.EXPECTED_VENDOR_RAMDISK_SHA256))
    entries=fyg8.boot.parse_newc(fyg8.boot.decompress_lz4_stream_python(raw,maximum=128*1024**2))
    matches=[e for e in entries if e.name=='lib/modules/'+LOGGER['name']]
    h0.require(len(matches)==1 and len(matches[0].data)==LOGGER['size'] and
        fyg8.digest(matches[0].data)==LOGGER['sha256'],'stock logger bytes differ')
    return [LOGGER,*platform],matches[0].data


def prepare(out,inputs,packages,*,run=None,key=None,virt=False,fresh=True,logging_mode='ram-only'):
    out=h0.private(out,fresh=fresh);inputs=h0.private(inputs);packages=h0.private(packages)
    h0.verify_packages(packages,out);selected,logger=modules(inputs,logging_mode)
    ram_only=logging_mode=='ram-only'
    run=run or uuid.uuid4().hex;key=key or secrets.token_bytes(32)
    h0.require(re.fullmatch('[0-9a-f]{32}',run) and len(key)==32,'USB identity differs')
    (out/'key').write_bytes(key);(out/'key').chmod(0o400)
    (out/'usb-first-key.h').write_text(early.array('early_key',key)+early.array('early_run',bytes.fromhex(run)))
    (out/'s22plus_native_ext4_seal_v1.h').write_bytes(fyg8.ext4.seal(fyg8.filesystem.BINDING,run,initialize=False))
    rows=['struct fyg8_module {const char *path,*runtime,*parameters; uint64_t size; uint8_t hash[32];};',
        'static const char fyg8_release[]='+json.dumps(fyg8.KERNEL_RELEASE)+';',
        'static const char fyg8_model[]='+json.dumps(fyg8.MODEL)+';',
        'static const struct fyg8_module fyg8_modules[]={']
    for m in selected:
        rows.append('{'+','.join(json.dumps(v) for v in ('/lab/modules/'+m['name'],m['runtime_name'],''))+','+
            str(m['size'])+'ULL,{'+','.join(map(str,bytes.fromhex(m['sha256'])))+'}},')
    (out/'fyg8-plan.h').write_text('\n'.join(rows+['};'])+'\n')
    plan=(inputs/'platform-plan.h').read_text().split('s22plus_o2_bind_gates[] = {',1)[1].split('};',1)[0]
    gates=re.findall(r'"(/sys/[^"\n]+)"',plan);h0.require(len(gates)==12,'retained gate set differs')
    (out/'usb-first-gates.h').write_text('static const char *const usb_gates_paths[]={'+
        ','.join(json.dumps(v) for v in gates)+'};\n')
    if not ram_only:
        (out/LOGGER['name']).write_bytes(logger)
        providers=fyg8.linkage._image_provider_map((inputs/'fixed-Image').read_bytes(),fyg8.linkage.IMAGE_SECTION_LAYOUT)
        raw=fyg8.capture(['modprobe','--dump-modversions',out/LOGGER['name']],out/'logger-imports.txt')
        imports={symbol:fyg8.linkage._norm_crc(crc) for crc,symbol in [line.split() for line in raw.splitlines()]}
        h0.require(len(imports)==71 and all(providers.get(s)==c for s,c in imports.items()),'logger/kernel ABI differs')
    h0.run(['aarch64-linux-gnu-gcc','-static','-Os','-Wall','-Wextra','-Werror',
        '-Wno-unused-function','-Wno-unused-const-variable','-ffunction-sections','-fdata-sections',
        '-Wl,--gc-sections','-fno-ident','-Wl,--build-id=none',*(['-DFYG8_VM_TEST'] if virt else []),
        *(['-DFYG8_USB_RAM_ONLY'] if ram_only else []),
        '-I',out,'-I',fyg8.ext4.NATIVE,h0.HERE/'usb-first-prepare.c','-o',out/'fyg8-prepare'],out/'compile.log')
    h0.run(['file',out/'fyg8-prepare'],out/'file.log')
    symbols=subprocess.check_output(['aarch64-linux-gnu-nm',out/'fyg8-prepare']);(out/'symbols.txt').write_bytes(symbols)
    h0.require(not any(re.search(rb'\b'+name+rb'$',symbols,re.M) for name in
        (b'storage',b'fs1_gpt_exact',b'fs1_read_super',b'fs1_open_block',b'ioctl',b'mount',b'execve',b'reboot')),
        'USB-only preparation contains storage/control linkage')
    measured=early.observer(out,inputs,packages,run,key,virt=virt,usb_modules=selected,usb_ram_only=ram_only)
    if ram_only:
        for name in ('fyg8-prepare','early-observer'):
            binary=(out/name).read_bytes()
            h0.require(b'/dev/kmsg' not in binary and b'/proc/last_kmsg' not in binary and b'sec_log_buf' not in binary,
                'RAM-only executable retains a logger path')
    result=dict(namespace=NAMESPACE,version=VERSION,profile=PROFILE,run_id=run,virtual=virt,
        inputs=str(inputs),packages=str(packages),modules=selected,measured=measured,logging_mode=logging_mode)
    h0.publish(out/'request.json',result);return result


def snapshot(out):
    sources=early.snapshot(out)
    for path in sorted(h0.HERE.glob('usb-first-*.h')):
        destination=out/'source-snapshot'/path.relative_to(h0.ROOT)
        destination.parent.mkdir(parents=True,exist_ok=True);destination.write_bytes(path.read_bytes())
        sources.append(dict(path=str(path.relative_to(h0.ROOT)),sha256=h0.sha(path)))
    h0.publish(out/'source-inputs.json',sources);return sources


def inside(out):
    request=json.loads((out/'request.json').read_text());inputs=h0.private(request['inputs'])
    packages=h0.private(request['packages']);mode=profile_api.usb_logging_mode(request);selected,logger=modules(inputs,mode)
    h0.require(selected==request['modules'],'USB module declaration changed')
    tree=h0.builder_tree(out,packages)
    for name in ('fyg8-prepare','early-observer'):
        shutil.copyfile(out/name,tree/'usr/sbin'/name);(tree/'usr/sbin'/name).chmod(0o755)
    (tree/'lab/modules').mkdir(parents=True)
    for m in selected:
        dest=tree/'lab/modules'/m['name'];dest.write_bytes(logger if m==LOGGER else (inputs/'modules'/m['name']).read_bytes());dest.chmod(0o400)
    conf=tree/'etc/initramfs-tools'
    for directory in ('conf.d','hooks','scripts'):(conf/directory).mkdir(parents=True,exist_ok=True)
    (conf/'initramfs.conf').write_text('MODULES=list\nBUSYBOX=y\nCOMPRESS=gzip\nKEYMAP=n\nRESUME=none\n')
    (conf/'modules').write_text('')
    for name,dest in (('fyg8-hook','hooks/fyg8'),('early-hook','hooks/zzzz-early')):
        shutil.copyfile(h0.HERE/name,conf/dest);(conf/dest).chmod(0o755)
    dev=(h0.HERE/'fyg8-dev').read_text();h0.require(dev.endswith('fyg8_stop\n'),'terminal hook changed')
    if mode=='retained':
        dev=dev.replace('mknod -m 666 /dev/null c 1 3 || fyg8_stop\n',
            'mknod -m 666 /dev/null c 1 3 || fyg8_stop\nmknod -m 600 /dev/kmsg c 1 11 || fyg8_stop\n')
    dev=dev[:-len('fyg8_stop\n')]+'/sbin/early-observer "$fyg8_status"\nfyg8_stop\n'
    (conf/'scripts/fyg8-dev').write_text(dev);(conf/'scripts/fyg8-dev').chmod(0o755)
    init=tree/'usr/share/initramfs-tools/init';original=init.read_text()
    needle='mount -t devtmpfs -o nosuid,mode=0755 udev /dev\n';h0.require(original.count(needle)==1,'Debian init changed')
    adapted=original.replace(needle,'. /scripts/fyg8-dev\n');init.write_text(adapted)
    (out/'debian-init.original').write_text(original);(out/'debian-init.adapted').write_text(adapted)
    (tree/'boot').mkdir(exist_ok=True);shutil.copyfile(inputs/'kernel.config',tree/'boot'/('config-'+fyg8.KERNEL_RELEASE))
    moddir=tree/'usr/lib/modules'/fyg8.KERNEL_RELEASE;moddir.mkdir(parents=True,exist_ok=True)
    for name in ('modules.builtin','modules.builtin.modinfo','modules.order'):(moddir/name).write_text('')
    h0.generate_archives(out,tree,fyg8.KERNEL_RELEASE)


def build(out,inputs,packages,*,logging_mode='ram-only'):
    out=h0.private(out,fresh=True);sources=snapshot(out)
    request=prepare(out,inputs,packages,fresh=False,logging_mode=logging_mode)
    h0.run(['unshare','--user','--map-auto','--map-root-user','--mount','--pid','--fork','--mount-proc',
        sys.executable,__file__,'inside','--output',out],out/'namespace-build.log',timeout=700)
    h0.require(h0.sha(out/'initramfs-a.cpio.gz')==h0.sha(out/'initramfs-b.cpio.gz'),'USB A/B archive differs')
    entries=fyg8.debian_entries(out/'initramfs-a.cpio.gz');rows={e.name:e for e in entries}
    h0.require(len(entries)==len(rows) and rows['lib'].file_type=='directory','archive collision or vendor/lib conflict')
    for m in request['modules']:
        e=rows['lab/modules/'+m['name']]
        h0.require(fyg8.digest(e.data)==m['sha256'] and len(e.data)==m['size'] and
            (e.uid,e.gid,e.nlink,e.mode&0o7777)==(0,0,1,0o400),'embedded USB module differs')
    h0.require({n for n in rows if n.startswith('lab/modules/')}=={'lab/modules/'+m['name'] for m in request['modules']},
        'unexpected embedded module')
    h0.require(fyg8.digest(rows['init'].data)==request['measured']['init_sha256'],'actual init differs')
    shell=rows['usr/bin/sh'];body=[e.data for e in entries if e.inode==shell.inode and e.file_type=='regular' and e.data]
    h0.require(len(body)==1 and fyg8.digest(body[0])==request['measured']['shell_sha256'],'actual shell differs')
    for name in ('fyg8-prepare','early-observer'):
        h0.require(rows['usr/sbin/'+name].data==(out/name).read_bytes(),'actual child differs')
    for row in sources:h0.require(h0.sha(h0.ROOT/row['path'])==row['sha256'],'USB source changed during build')
    h0.publish(out/'build.json',dict(schema='s22plus-debian-usb-first-h0-v1',status='H0_INITRAMFS_BUILT',
        **request,initramfs=pin(out/'initramfs-a.cpio.gz',maximum=16*1024**2),helper=pin(out/'fyg8-prepare'),
        observer=pin(out/'early-observer'),ab_identical=True,source_inputs=sources,device_actions=0,active=False,
        headers={name:pin(out/name) for name in ('fyg8-plan.h','usb-first-key.h','usb-first-gates.h',
            's22plus_native_ext4_seal_v1.h','early-seal.h')}))
    print('PASS: USB-first A/B initramfs; H0 only')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=('build','inside'))
    parser.add_argument('--output',type=Path,required=True);parser.add_argument('--inputs',type=Path);parser.add_argument('--packages',type=Path)
    parser.add_argument('--logging-mode',choices=profile_api.USB_LOGGING_MODES,default='ram-only')
    args=parser.parse_args()
    if args.action=='build':build(args.output,args.inputs,args.packages,logging_mode=args.logging_mode)
    else:inside(h0.private(args.output))

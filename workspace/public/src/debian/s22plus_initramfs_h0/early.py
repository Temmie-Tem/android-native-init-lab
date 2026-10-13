#!/usr/bin/env python3
"""Build Debian-owned early-boot evidence artifact; H0 only, no transport."""
import argparse
import gzip
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile
import uuid

import h0
import fyg8
from s22plus_native_records_v3 import pin,verify
import s22plus_native_thermal_build_v1 as packaging

NAMESPACE='p417'
VERSION='v0.5.0-rc.1'
PROFILE='debian-owned-early-v1'


def array(name,raw):
    return 'static const uint8_t '+name+'[]={'+','.join(map(str,raw))+'};\n'


def shell_input(packages):
    # BUSYBOX=y makes /usr/bin/sh a hardlink to the retained Debian BusyBox.
    # The six extra authenticated packages do not supply this executable.
    archive=h0.regular(h0.BASE/'rootfs-d/rootfs.tar')
    h0.require(h0.sha(archive)==h0.ROOTFS_SHA,'retained builder root changed')
    with tarfile.open(archive) as source:
        member=source.getmember('./usr/bin/busybox')
        h0.require(member.isfile() and member.uid==member.gid==0 and 0<member.size<=4*1024*1024,
            'retained shell member differs')
        return source.extractfile(member).read()


def observer(out,inputs,packages,run,key,*,virt=False,usb_modules=None,usb_ram_only=False):
    value=fyg8.verify_inventory(inputs)
    h0.require(not usb_ram_only or usb_modules,'RAM-only mode requires the USB-only plan')
    original=(packages/'root/usr/share/initramfs-tools/init').read_bytes()
    needle=b'mount -t devtmpfs -o nosuid,mode=0755 udev /dev\n'
    h0.require(original.count(needle)==1,'Debian early init changed')
    init=original.replace(needle,b'. /scripts/fyg8-dev\n')
    shell=shell_input(packages)
    text=array('early_key',key)+array('early_run',bytes.fromhex(run))
    text+=array('early_shell_hash',bytes.fromhex(fyg8.digest(shell)))
    text+=array('early_init_hash',bytes.fromhex(fyg8.digest(init)))
    text+=array('early_helper_hash',bytes.fromhex(h0.sha(out/'fyg8-prepare')))
    text+='static const char early_release[]='+json.dumps(fyg8.KERNEL_RELEASE)+';\n'
    text+='static const char early_model[]='+json.dumps(fyg8.MODEL)+';\n'
    text+='static const char early_serial[]='+json.dumps('S22E3'+run)+';\n'
    text+='static const char *const early_module_names[]={'+','.join(json.dumps(m['runtime_name']) for m in (usb_modules or value['modules']))+'};\n'
    if usb_modules:text+='#define EARLY_DOMAIN "S22PLUS-FYG8-DEBIAN-USB-FIRST-v1"\n'
    (out/'early-seal.h').write_text(text)
    h0.run(['aarch64-linux-gnu-gcc','-static','-Os','-Wall','-Wextra','-Werror',
        '-Wno-unused-function','-Wno-unused-const-variable','-ffunction-sections','-fdata-sections',
        '-Wl,--gc-sections','-fno-ident','-Wl,--build-id=none',*(['-DEARLY_VM_TEST'] if virt else []),
        *(['-DEARLY_USB_FIRST'] if usb_modules else []),
        *(['-DEARLY_USB_RAM_ONLY'] if usb_ram_only else []),
        '-I',out,'-I',fyg8.ext4.NATIVE,h0.HERE/'early-observer.c','-o',out/'early-observer'],out/'observer-compile.log')
    h0.run(['file',out/'early-observer'],out/'observer-file.log')
    return dict(shell_sha256=fyg8.digest(shell),init_sha256=fyg8.digest(init),helper_sha256=h0.sha(out/'fyg8-prepare'))


def prepare(out,inputs,packages,*,run=None,key=None,virt=False,fresh=True):
    out=h0.private(out,fresh=fresh);inputs=h0.private(inputs);packages=h0.private(packages)
    h0.verify_packages(packages,out);fyg8.verify_inventory(inputs)
    run=run or uuid.uuid4().hex
    key=key or __import__('secrets').token_bytes(32)
    h0.require(re.fullmatch('[0-9a-f]{32}',run) and len(key)==32,'run/key differs')
    (out/'key').write_bytes(key);(out/'key').chmod(0o400)
    binding=fyg8.compile_helper(out,inputs,run_id=run,virt=virt)
    measured=observer(out,inputs,packages,run,key,virt=virt)
    request=dict(namespace=NAMESPACE,version=VERSION,run_id=run,profile=PROFILE,virtual=virt,
        inputs=str(inputs),packages=str(packages),binding=binding,measured=measured)
    h0.publish(out/'request.json',request)
    return request


def snapshot(out):
    sources=fyg8.snapshot(out)
    extra=[]
    for name in ('early-protocol.h','early-measure.h','pid1-measure.h','early-hook','fyg8-dev','fyg8-hook'):
        path=h0.HERE/name;dest=out/'source-snapshot'/path.relative_to(h0.ROOT)
        dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(path.read_bytes())
        extra.append(dict(path=str(path.relative_to(h0.ROOT)),sha256=h0.sha(dest)))
    sources={r['path']:r for r in sources+extra};sources=sorted(sources.values(),key=lambda r:r['path'])
    h0.publish(out/'source-inputs.json',sources)
    return sources


def build(out,inputs,packages):
    out=h0.private(out,fresh=True)
    sources=snapshot(out)  # Before either compiler or package extraction runs.
    request=prepare(out,inputs,packages,fresh=False)
    h0.run(['unshare','--user','--map-auto','--map-root-user','--mount','--pid','--fork','--mount-proc',
        sys.executable,__file__,'inside','--output',out],out/'namespace-build.log',timeout=700)
    h0.require(h0.sha(out/'initramfs-a.cpio.gz')==h0.sha(out/'initramfs-b.cpio.gz'),'early A/B initramfs differs')
    entries=fyg8.debian_entries(out/'initramfs-a.cpio.gz');rows={e.name:e for e in entries}
    shell=rows['usr/bin/sh']
    bodies=[e.data for e in entries if e.inode==shell.inode and e.file_type=='regular' and e.data]
    h0.require(rows['lib'].file_type=='directory' and len(bodies)==1 and
        fyg8.digest(bodies[0])==request['measured']['shell_sha256'], 'actual shell or vendor/lib compatibility differs')
    h0.require(fyg8.digest(rows['init'].data)==request['measured']['init_sha256'],'actual Debian /init differs')
    h0.require(len(rows)==len(entries),'duplicate Debian archive member')
    for name in ('fyg8-prepare','early-observer'):
        entry=rows['usr/sbin/'+name]
        h0.require(entry.data==(out/name).read_bytes() and entry.uid==entry.gid==0 and
            entry.nlink==1 and entry.mode&0o7777==0o755,'actual early executable differs')
    modules=fyg8.verify_inventory(h0.private(inputs))['modules']
    h0.require({name for name in rows if name.startswith('lab/modules/')}==
        {'lab/modules/'+m['name'] for m in modules},'actual module set differs')
    for module in modules:
        entry=rows['lab/modules/'+module['name']]
        h0.require(fyg8.digest(entry.data)==module['sha256'] and len(entry.data)==module['size'] and
            entry.uid==entry.gid==0 and entry.nlink==1 and entry.mode&0o7777==0o400,'actual module bytes/metadata differ')
    for row in sources:h0.require(h0.sha(h0.ROOT/row['path'])==row['sha256'],'early source changed during build')
    h0.publish(out/'build.json',dict(schema='s22plus-debian-early-h0-v1',status='H0_INITRAMFS_BUILT',
        **request,initramfs=pin(out/'initramfs-a.cpio.gz',maximum=16*1024*1024),helper=pin(out/'fyg8-prepare'),observer=pin(out/'early-observer'),
        ab_identical=True,source_inputs=sources,headers={name:pin(out/name) for name in
        ('fyg8-plan.h','s22plus_native_ext4_seal_v1.h','early-seal.h')},device_actions=0,active=False))
    print('PASS: observed early initramfs A/B; no device authority')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=('build','inside'))
    p.add_argument('--output',type=Path,required=True);p.add_argument('--inputs',type=Path);p.add_argument('--packages',type=Path)
    args=p.parse_args()
    if args.action=='build':build(args.output,args.inputs,args.packages)
    else:
        out=h0.private(args.output);request=json.loads((out/'request.json').read_text())
        fyg8.inside(out,h0.private(request['packages']),h0.private(request['inputs']),observed=True)

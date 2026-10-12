#!/usr/bin/env python3
"""H0 build of a one-module, storage/USB-independent Debian stage probe."""
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
import s22plus_debian_stage_protocol_v1 as protocol
from s22plus_native_records_v3 import pin

NAMESPACE='p423'
VERSION='v0.5.0-rc.7'
PROFILE='debian-stage-probe-v1'
LOGGER=usb_first.LOGGER


def prepare(out,inputs,packages,*,run=None,key=None,virt=False,fresh=True):
    out=h0.private(out,fresh=fresh);inputs=h0.private(inputs);packages=h0.private(packages)
    h0.verify_packages(packages,out);selected,logger=usb_first.modules(inputs,'retained')
    h0.require(selected[0]==LOGGER,'logger declaration differs')
    run=run or uuid.uuid4().hex;key=key or secrets.token_bytes(32)
    h0.require(re.fullmatch('[0-9a-f]{32}',run) and len(key)==32,'stage identity differs')
    (out/'key').write_bytes(key);(out/'key').chmod(0o400)
    (out/LOGGER['name']).write_bytes(logger)
    providers=fyg8.linkage._image_provider_map((inputs/'fixed-Image').read_bytes(),fyg8.linkage.IMAGE_SECTION_LAYOUT)
    raw=fyg8.capture(['modprobe','--dump-modversions',out/LOGGER['name']],out/'logger-imports.txt')
    imports={symbol:fyg8.linkage._norm_crc(crc) for crc,symbol in [line.split() for line in raw.splitlines()]}
    h0.require(len(imports)==71 and all(providers.get(s)==c for s,c in imports.items()),'logger/kernel ABI differs')
    original=(packages/'root/usr/share/initramfs-tools/init').read_bytes()
    needle=b'mount -t devtmpfs -o nosuid,mode=0755 udev /dev\n'
    h0.require(original.count(needle)==1,'Debian init adaptation differs')
    init=original.replace(needle,b'. /scripts/fyg8-dev\n');shell=early.shell_input(packages)
    text=early.array('early_key',key)+early.array('early_run',bytes.fromhex(run))
    text+=early.array('early_shell_hash',bytes.fromhex(fyg8.digest(shell)))
    text+=early.array('early_init_hash',bytes.fromhex(fyg8.digest(init)))
    text+=early.array('stage_logger_hash',bytes.fromhex(LOGGER['sha256']))
    text+='static const char stage_release[]='+json.dumps(fyg8.KERNEL_RELEASE)+';\n'
    text+='static const char stage_model[]='+json.dumps(fyg8.MODEL)+';\n'
    text+='#define STAGE_LOGGER_SIZE '+str(LOGGER['size'])+'ULL\n'
    (out/'stage-seal.h').write_text(text)
    (out/'s22plus_native_ext4_seal_v1.h').write_bytes(fyg8.ext4.seal(fyg8.filesystem.BINDING,run,initialize=False))
    h0.run(['aarch64-linux-gnu-gcc','-static','-Os','-Wall','-Wextra','-Werror',
        '-Wno-unused-function','-Wno-unused-const-variable','-ffunction-sections','-fdata-sections',
        '-Wl,--gc-sections','-fno-ident','-Wl,--build-id=none',*(['-DSTAGE_VM_TEST'] if virt else []),
        '-I',out,'-I',fyg8.ext4.NATIVE,h0.HERE/'stage-probe.c','-o',out/'fyg8-prepare'],out/'compile.log')
    h0.run(['file',out/'fyg8-prepare'],out/'file.log')
    symbols=subprocess.check_output(['aarch64-linux-gnu-nm',out/'fyg8-prepare']);(out/'symbols.txt').write_bytes(symbols)
    h0.require(not any(re.search(rb'\b'+name+rb'$',symbols,re.M) for name in
        (b'storage',b'fs1_gpt_exact',b'fs1_read_super',b'fs1_open_block',b'ioctl',b'mount',b'execve',b'reboot')),
        'stage probe contains a storage/control path')
    binary=(out/'fyg8-prepare').read_bytes()
    h0.require(not any(s in binary for s in (b'/dev/ttyGS',b'/config/usb_gadget',b'/s22-root',b'/dev/.s22-ext4-v1')),
        'stage probe contains excluded workload paths')
    measured=dict(shell_sha256=fyg8.digest(shell),init_sha256=fyg8.digest(init),helper_sha256=h0.sha(out/'fyg8-prepare'))
    request=dict(namespace=NAMESPACE,version=VERSION,profile=PROFILE,run_id=run,virtual=virt,
        inputs=str(inputs),packages=str(packages),modules=[LOGGER],measured=measured)
    h0.publish(out/'request.json',request);return request


def snapshot(out):
    rows={r['path']:r for r in early.snapshot(out)}
    for path in (h0.HERE/'stage-hook',Path(protocol.__file__)):
        dest=out/'source-snapshot'/path.relative_to(h0.ROOT)
        dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(path.read_bytes())
        rows[str(path.relative_to(h0.ROOT))]=dict(path=str(path.relative_to(h0.ROOT)),sha256=h0.sha(dest))
    rows=sorted(rows.values(),key=lambda r:r['path']);h0.publish(out/'source-inputs.json',rows);return rows


def inside(out):
    request=json.loads((out/'request.json').read_text());inputs=h0.private(request['inputs'])
    packages=h0.private(request['packages']);tree=h0.builder_tree(out,packages)
    h0.require(request['modules']==[LOGGER],'stage module set changed')
    shutil.copyfile(out/'fyg8-prepare',tree/'usr/sbin/fyg8-prepare');(tree/'usr/sbin/fyg8-prepare').chmod(0o755)
    (tree/'lab/modules').mkdir(parents=True)
    shutil.copyfile(out/LOGGER['name'],tree/'lab/modules'/LOGGER['name']);(tree/'lab/modules'/LOGGER['name']).chmod(0o400)
    conf=tree/'etc/initramfs-tools'
    for d in ('conf.d','hooks','scripts'):(conf/d).mkdir(parents=True,exist_ok=True)
    (conf/'initramfs.conf').write_text('MODULES=list\nBUSYBOX=y\nCOMPRESS=gzip\nKEYMAP=n\nRESUME=none\n')
    (conf/'modules').write_text('')
    for name,dest in (('fyg8-hook','hooks/fyg8'),('stage-hook','hooks/zzzz-stage')):
        shutil.copyfile(h0.HERE/name,conf/dest);(conf/dest).chmod(0o755)
    dev=(h0.HERE/'fyg8-dev').read_text()
    needle='mknod -m 666 /dev/null c 1 3 || fyg8_stop\n';h0.require(dev.count(needle)==1,'RAM device hook changed')
    dev=dev.replace(needle,needle+'mknod -m 600 /dev/kmsg c 1 11 || fyg8_stop\n')
    (conf/'scripts/fyg8-dev').write_text(dev);(conf/'scripts/fyg8-dev').chmod(0o755)
    init=tree/'usr/share/initramfs-tools/init';original=init.read_text()
    needle='mount -t devtmpfs -o nosuid,mode=0755 udev /dev\n';h0.require(original.count(needle)==1,'Debian init changed')
    adapted=original.replace(needle,'. /scripts/fyg8-dev\n');init.write_text(adapted)
    (out/'debian-init.original').write_text(original);(out/'debian-init.adapted').write_text(adapted)
    (tree/'boot').mkdir(exist_ok=True);shutil.copyfile(inputs/'kernel.config',tree/'boot'/('config-'+fyg8.KERNEL_RELEASE))
    moddir=tree/'usr/lib/modules'/fyg8.KERNEL_RELEASE;moddir.mkdir(parents=True,exist_ok=True)
    for name in ('modules.builtin','modules.builtin.modinfo','modules.order'):(moddir/name).write_text('')
    h0.generate_archives(out,tree,fyg8.KERNEL_RELEASE)


def build(out,inputs,packages,*,run=None,key=None):
    out=h0.private(out,fresh=True);sources=snapshot(out)
    request=prepare(out,inputs,packages,fresh=False,run=run,key=key)
    h0.run(['unshare','--user','--map-auto','--map-root-user','--mount','--pid','--fork','--mount-proc',
        sys.executable,__file__,'inside','--output',out],out/'namespace-build.log',timeout=700)
    h0.require(h0.sha(out/'initramfs-a.cpio.gz')==h0.sha(out/'initramfs-b.cpio.gz'),'stage A/B archive differs')
    entries=fyg8.debian_entries(out/'initramfs-a.cpio.gz');rows={e.name:e for e in entries}
    h0.require(len(entries)==len(rows) and rows['lib'].file_type=='directory','archive/vendor collision')
    h0.require(fyg8.digest(rows['init'].data)==request['measured']['init_sha256'],'actual init differs')
    shell=rows['usr/bin/sh'];bodies=[e.data for e in entries if e.inode==shell.inode and e.file_type=='regular' and e.data]
    h0.require(len(bodies)==1 and fyg8.digest(bodies[0])==request['measured']['shell_sha256'],'actual shell differs')
    helper=rows['usr/sbin/fyg8-prepare'];module=rows['lab/modules/sec_log_buf.ko']
    h0.require(helper.data==(out/'fyg8-prepare').read_bytes() and helper.uid==helper.gid==0 and helper.nlink==1 and
        helper.mode&0o7777==0o755,'actual stage helper differs')
    h0.require(fyg8.digest(module.data)==LOGGER['sha256'] and len(module.data)==LOGGER['size'] and
        (module.uid,module.gid,module.nlink,module.mode&0o7777)==(0,0,1,0o400),'actual logger differs')
    h0.require({n for n in rows if n.startswith('lab/modules/')}=={'lab/modules/sec_log_buf.ko'} and
        not any(n in rows for n in ('usr/sbin/early-observer','usr/sbin/file-log','s22-fs-e2fsck','s22-journal-replay')),
        'stage archive contains an unselected workload')
    for row in sources:h0.require(h0.sha(h0.ROOT/row['path'])==row['sha256'],'stage source changed during build')
    h0.publish(out/'build.json',dict(schema='s22plus-debian-stage-probe-h0-v1',status='H0_INITRAMFS_BUILT',
        **request,initramfs=pin(out/'initramfs-a.cpio.gz',maximum=16*1024**2),helper=pin(out/'fyg8-prepare'),
        ab_identical=True,source_inputs=sources,headers={name:pin(out/name) for name in
            ('stage-seal.h','s22plus_native_ext4_seal_v1.h')},device_actions=0,active=False))
    print('PASS: logger-only A/B initramfs; H0 only')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=('build','inside'))
    parser.add_argument('--output',type=Path,required=True);parser.add_argument('--inputs',type=Path);parser.add_argument('--packages',type=Path)
    args=parser.parse_args()
    if args.action=='build':build(args.output,args.inputs,args.packages)
    else:inside(h0.private(args.output))

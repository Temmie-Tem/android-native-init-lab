"""Real ARM64 execution of the shared early gate and protected preparation."""
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys

import s22plus_native_preflight_h0 as producer
import s22plus_native_root_inspect_vm_h0 as fixture
from s22plus_native_records_v3 import pin, publish, read, require, verify

ROOT = producer.ROOT
P406 = ROOT/'workspace/private/outputs/s22plus-debian-root-state-p406-h0-20260926-1/vm-1'
HARNESS = r'''
#define _GNU_SOURCE
#include <fcntl.h>
#include <stdio.h>
#include <sys/mount.h>
#include <sys/reboot.h>
#include <sys/stat.h>
#include <sys/sysmacros.h>
#include <unistd.h>
#include "preflight-plan.h"
#include "preflight_gate.inc.c"
int main(void) {
    bp_native_enter(bp_run_id, 1);
    if (mount("proc","/proc","proc",0,0) || mount("sysfs","/sys","sysfs",0,0) ||
        mount("tmpfs","/dev","tmpfs",0,0) || bp_native_boot() ||
        mknod("/dev/console",S_IFCHR|0600,makedev(5,1))) bp_native_park();
    int fd=open("/dev/console",O_RDWR);
    if (fd<0) bp_native_park();
    dprintf(fd,"BP_VM_RECORD ");
    unsigned char *p=(unsigned char *)&bp_native_record;
    for (unsigned i=0;i<sizeof(bp_native_record);++i) dprintf(fd,"%02x",p[i]);
    dprintf(fd,"\nBP_VM_LOG_BEGIN\n");
    unsigned char log[BP_LOG_MAX];
    if (pread(BP_FD,log,bp_native_record.log_size,sizeof(bp_native_record)) != bp_native_record.log_size)
        bp_native_park();
    if (write(fd,log,bp_native_record.log_size) != bp_native_record.log_size) bp_native_park();
    dprintf(fd,"\nBP_VM_LOG_END\n");
#ifndef BP_FAULT_TEST
    dprintf(fd,"BP_VM_RO ");
    const char *paths[]={"/sys/class/block/vda41/ro","/sys/class/block/vda/ro","/sys/class/block/vda40/ro"};
    for (unsigned i=0;i<3;++i) {
        char b[8]; int f=open(paths[i],O_RDONLY); ssize_t n=read(f,b,sizeof(b));
        if(n!=2 || close(f)) bp_native_park();
        dprintf(fd,"%c",b[0]);
    }
    dprintf(fd,"\n");
#endif
    dprintf(fd,"BP_VM_DONE\n");
    reboot(RB_POWER_OFF);
    bp_native_park();
}
'''

FAULT_HARNESS=r'''
#define main unused_production_main
#include "handoff.c"
#undef main
int main(void) {
    if(getpid()!=1) return 3;
    bp_begin();
    directory("/proc",0555); directory("/sys",0555); directory("/dev",0755); directory("/run",0755);
    mount_at("proc","/proc","proc",MS_NOSUID|MS_NOEXEC|MS_NODEV,0);
    bp_boot_identity();
    mount_at("sysfs","/sys","sysfs",MS_NOSUID|MS_NOEXEC|MS_NODEV,0);
    mount_at("tmpfs","/dev","tmpfs",MS_NOSUID,"mode=0755");
    mount_at("tmpfs","/run","tmpfs",MS_NOSUID|MS_NODEV,"mode=0755");
    if(mknod("/dev/console",S_IFCHR|0600,makedev(5,1)) || mknod("/dev/null",S_IFCHR|0666,makedev(1,3))) stop("fault-nodes");
    diagnostic_console=open("/dev/console",O_RDWR|O_CLOEXEC);
    if(diagnostic_console<0) stop("fault-console");
    bp_stage(BP_LOADER_VERIFY);
    char *args[]={!strcmp(BP_FAULT_CASE,"exec")?"/missing":"/s22-fault-child",BP_FAULT_CASE,0};
    bp_run_child(0,args,0,0,-1,-1,1);
    bp_finish(0,"fault-child-returned",EPROTO);
    return 2;
}
'''

FAULT_CHILD=r'''
#define _GNU_SOURCE
#include <signal.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
int main(int argc,char **argv) {
    if(argc!=2) return 2;
    if(!strcmp(argv[1],"nonzero")) return 23;
    if(!strcmp(argv[1],"signal")) {raise(SIGKILL);return 4;}
    if(!strcmp(argv[1],"timeout")) {sleep(40);return 0;}
    if(!strcmp(argv[1],"overflow")) {char b[4096];memset(b,'x',sizeof(b));for(int i=0;i<32;i++)if(write(1,b,sizeof(b))<0)return 5;return 0;}
    if(!strcmp(argv[1],"descendant")) {pid_t child=fork();if(child<0)return 6;if(!child){sleep(1);_exit(0);}return 0;}
    return 7;
}
'''


def setup(out, helper):
    require(not out.exists(), 'fresh VM setup required')
    out.mkdir(mode=0o700)
    built=read(helper/'result.json'); producer.audit(helper,built['run_id_hex'])
    for name in ('binding.h','s22plus_native_ext4_seal_v1.h','target-plan.h','preflight-plan.h'):
        shutil.copyfile(helper/name,out/name)
    producer.compile_pair(out,producer.BASE/'handoff.c','producer',virt=True)
    (out/'gate.c').write_text(HARNESS)
    producer.compile_pair(out,out/'gate.c','gate',virt=True,includes=(producer.DEVICE,))
    artifact,_,_=producer.retained.prior_inputs()
    old=Path(artifact['rootfs']['path']).parent
    entries=[(name,stat.S_IFDIR|0o755,b'') for name in ('bin','dev','proc','sys','run','newroot')]
    entries += [('init',stat.S_IFREG|0o500,(out/'gate-a').read_bytes()),
        ('s22-prehandoff',stat.S_IFREG|0o500,(out/'producer-a').read_bytes()),
        ('bin/busybox',stat.S_IFREG|0o500,(old/'busybox').read_bytes())]
    for name in ('s22-fs-e2fsck','rootfs.meta','rootfs.sha256','busybox'):
        row=built['members'][name];entries.append((name,stat.S_IFREG|row['mode'],verify(row['file']).read_bytes()))
    (out/'initramfs.cpio.gz').write_bytes(gzip.compress(producer.h0.newc(entries),mtime=0))
    finish_setup(out,helper)


def finish_setup(out,helper):
    executable=out/'qemu-system-aarch64'
    if not executable.exists():
        shutil.copyfile(fixture.QEMU/'usr/bin/qemu-system-aarch64',executable)
        executable.chmod(0o500)
    publish(out/'setup.json',dict(helper=pin(helper/'result.json'),
        kernel=pin(fixture.KERNEL,maximum=128*1024*1024),
        initramfs=pin(out/'initramfs.cpio.gz',maximum=16*1024*1024),
        qemu=pin(executable,maximum=128*1024*1024),source=pin(Path(__file__)),device_actions=0))


def check(out, case):
    value=read(out/'setup.json'); folder=out/case; folder.mkdir(mode=0o700)
    source=P406/case/'disk.img'
    require(source.is_file(), 'retained writable test fixture missing')
    disk=folder/'disk.img'
    fixture.run(['cp','--reflink=auto','--sparse=always',source,disk],folder,'copy')
    before=fixture.fixture_tools.sparse_digest(disk)
    command=[verify(value['qemu'],maximum=128*1024*1024),'-machine','virt','-cpu','cortex-a76',
        '-smp','2','-m','768','-nic','none','-nographic','-monitor','none','-no-reboot',
        '-kernel',fixture.KERNEL,'-initrd',out/'initramfs.cpio.gz','-append','console=ttyAMA0 rdinit=/init panic=-1',
        '-drive',f'if=none,id=root,file={disk},format=raw',
        '-device','virtio-blk-device,drive=root,logical_block_size=4096,physical_block_size=4096']
    (folder/'command.json').write_text(json.dumps(list(map(str,command)))+'\n')
    env=dict(os.environ,LD_LIBRARY_PATH=str(fixture.QEMU/'usr/lib/x86_64-linux-gnu'))
    with (folder/'serial.raw').open('xb') as log:
        completed=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,env=env,timeout=300)
    require(completed.returncode==0, 'VM did not power off')
    after=fixture.fixture_tools.sparse_digest(disk)
    require(before==after,'preflight modified writable backing disk')
    raw=(folder/'serial.raw').read_bytes().replace(b'\r\n',b'\n')
    import re,struct
    records=re.findall(rb'^BP_VM_RECORD ([0-9a-f]+)$',raw,re.M)
    require(len(records)==1 and raw.count(b'BP_VM_DONE\n')==1, 'shared gate did not admit exactly one record')
    record=bytes.fromhex(records[0].decode());require(len(record)==212,'record length differs')
    fields=struct.unpack('<24I',record[:96])
    complete,error,stage=fields[7],fields[5],fields[4]
    require(fields[19:22]==(1,1,1) and fields[22]==1,'mount/FD/child cleanup proof absent')
    if case=='complete':
        require(complete==1 and error==0 and stage==12 and b'BP_VM_RO 100\n' in raw,
            'full preflight did not complete with partition-only RO')
    else: require(complete==0 and error>0,'negative fixture was not rejected')
    return publish(folder/'result.json',dict(schema='s22plus-preflight-vm-case-h0-v1',case=case,
        status='PASS_H0',record_hex=record.hex(),disk_before=before,disk_after=after,
        serial=pin(folder/'serial.raw'),setup=pin(out/'setup.json'),scope='VIRT_NOT_SAMSUNG',device_actions=0))


def child_fault(out,helper,case):
    import re,struct,time
    require(case in ('exec','nonzero','signal','timeout','overflow','descendant'),'unknown child fault')
    out.mkdir(mode=0o700)
    built=producer.audit(helper,read(helper/'result.json')['run_id_hex'])
    for name in ('binding.h','s22plus_native_ext4_seal_v1.h','target-plan.h','preflight-plan.h'):
        shutil.copyfile(helper/name,out/name)
    (out/'gate.c').write_text('#define BP_FAULT_TEST\n'+HARNESS)
    (out/'producer.c').write_text('#define BP_FAULT_CASE '+json.dumps(case)+'\n'+FAULT_HARNESS)
    (out/'child.c').write_text(FAULT_CHILD)
    producer.compile_pair(out,out/'gate.c','gate',virt=True,includes=(producer.DEVICE,))
    producer.compile_pair(out,out/'producer.c','producer',virt=True,includes=(producer.BASE,))
    producer.compile_pair(out,out/'child.c','child',virt=True)
    entries=[(name,stat.S_IFDIR|0o755,b'') for name in ('dev','proc','sys','run')]
    entries += [('init',stat.S_IFREG|0o500,(out/'gate-a').read_bytes()),
        ('s22-prehandoff',stat.S_IFREG|0o500,(out/'producer-a').read_bytes()),
        ('s22-fault-child',stat.S_IFREG|0o555,(out/'child-a').read_bytes())]
    (out/'initramfs.cpio.gz').write_bytes(gzip.compress(producer.h0.newc(entries),mtime=0))
    command=[fixture.QEMU/'usr/bin/qemu-system-aarch64','-machine','virt','-cpu','cortex-a76',
        '-smp','2','-m','768','-nic','none','-nographic','-monitor','none','-no-reboot',
        '-kernel',fixture.KERNEL,'-initrd',out/'initramfs.cpio.gz','-append','console=ttyAMA0 rdinit=/init panic=-1']
    env=dict(os.environ,LD_LIBRARY_PATH=str(fixture.QEMU/'usr/lib/x86_64-linux-gnu'))
    with (out/'serial.raw').open('xb') as log:
        process=subprocess.Popen(list(map(str,command)),stdout=log,stderr=subprocess.STDOUT,env=env)
        try:
            deadline=time.monotonic()+45
            while time.monotonic()<deadline:
                raw=(out/'serial.raw').read_bytes().replace(b'\r\n',b'\n')
                if process.poll() is not None:break
                if case in ('timeout','overflow','descendant') and b'BOOTSTRAP_STOP stage=' in raw:
                    time.sleep(1);break
                time.sleep(.1)
            raw=(out/'serial.raw').read_bytes().replace(b'\r\n',b'\n')
            records=re.findall(rb'^BP_VM_RECORD ([0-9a-f]+)$',raw,re.M)
            if case in ('exec','nonzero','signal'):
                require(process.wait(timeout=5)==0 and len(records)==1,'settled child failure did not reach observer')
                fields=struct.unpack('<24I',bytes.fromhex(records[0].decode())[:96])
                require(fields[7]==0 and fields[9:11]==(1,1) and fields[19:22]==(1,1,1),
                    'child failure lost cleanup or wait evidence')
                require(fields[11]==(1 if case=='nonzero' else 0),'unproved exec was counted')
                require(fields[12]==(23<<8 if case=='nonzero' else 9 if case=='signal' else 126<<8),
                    'actual child wait status differs')
            else:
                require(not records and process.poll() is None and b'BOOTSTRAP_STOP stage=' in raw,
                    'unsettled/overflow/timeout fault reached observer or lacks actual stop evidence')
        finally:
            if process.poll() is None:process.terminate();process.wait(timeout=5)
    return publish(out/'result.json',dict(schema='s22plus-preflight-child-fault-h0-v1',case=case,
        status='PASS_H0',observer_admitted=case in ('exec','nonzero','signal'),serial=pin(out/'serial.raw'),
        source=pin(Path(__file__)),helper=pin(helper/'result.json'),scope='VIRT_NOT_SAMSUNG',device_actions=0))


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('action',choices=('setup','check'));parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--helper',type=Path);parser.add_argument('--case',default='complete')
    args=parser.parse_args()
    print(setup(args.output.absolute(),args.helper.absolute()) if args.action=='setup' else check(args.output.absolute(),args.case))

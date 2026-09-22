"""Real ARM64 child faults; virtual discovery and a fixture group owner are explicit."""
import argparse
import gzip
import json
import os
from pathlib import Path
import re
import shutil
import stat
import sys

import s22plus_native_root_inspect_vm_h0 as vm
import s22plus_native_userspace_probe_profile_v1 as profile
from s22plus_native_records_v3 import pin, read, require, verify

ROOT = vm.ROOT
FAULTS = {
    'wrong-output': dict(script="/usr/bin/printf 'wrong\\n'", verdict='WORKLOAD_NOT_PROVED'),
    'nonzero': dict(script='exit 17', verdict='WORKLOAD_NOT_PROVED'),
    'setup-error': dict(setup_error=True, verdict='WORKLOAD_NOT_PROVED'),
    'early-zero': dict(early_zero=True, error=71),
    'timeout': dict(script='while :; do :; done', error=110),
    'overflow': dict(script="while :; do printf '01234567890123456789012345678901'; done", error=75),
    'orphan': dict(orphan=True, error=110),
}

# This small fixture owns a process group exactly to test that the actual ARM64
# probe and its descendants remain cancellable in the inherited group. It is
# not substituted for the production ACM implementation or its C/PTY tests.
SUPERVISOR = r'''#define _GNU_SOURCE
#include <errno.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/prctl.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>
static unsigned long long ms(void) { struct timespec t; if(clock_gettime(CLOCK_MONOTONIC,&t))_exit(90); return (unsigned long long)t.tv_sec*1000+t.tv_nsec/1000000; }
int main(int argc,char **argv) {
 if(argc!=2 || prctl(PR_SET_CHILD_SUBREAPER,1,0,0,0)) return 90;
 pid_t child=fork(); if(child<0)return 91;
 if(!child) { if(setsid()<0)_exit(92); char *args[]={"/s22-userspace-probe","probe",argv[1],NULL};execv(args[0],args);_exit(93); }
 unsigned long long start=ms(),stopped=0;int status=0,done=0,killed=0,adopted=0;
 for(;;) {
  int value=0;pid_t found=waitpid(-1,&value,WNOHANG);int wait_error=found<0?errno:0;
  if(found==child) { status=value;done=1;if(!stopped)stopped=ms(); }
  else if(found>0)++adopted;
  else if(found<0 && errno!=ECHILD && errno!=EINTR)return 94;
  if(!stopped && ms()-start>90000)stopped=ms();
  if(stopped) {
   if(!killed) { if(kill(-child,SIGTERM) && errno!=ESRCH)return 95;killed=1; }
   if(ms()-stopped>=250 && killed==1) { if(kill(-child,SIGKILL) && errno!=ESRCH)return 96;killed=2; }
   int group=kill(-child,0),absent=group<0 && errno==ESRCH;
   if(done && found<0 && wait_error==ECHILD && absent) { printf("UP_VM_SCOPE settled=1 status=%d adopted=%d\n",status,adopted);return 0; }
   if(ms()-stopped>=2000)return 97;
  }
  struct timespec delay={0,10000000};nanosleep(&delay,NULL);
 }
}
'''


def run_case(base, helper, name):
    require(name in FAULTS, 'unknown fixed VM fault')
    setup = read(base/'setup.json'); built = read(helper/'result.json')
    require(built['virt'] is True and built['userspace_probe'] == profile.execution_binding(),
        'fault input is not the current explicitly virtual helper')
    for receipt in built['source_inputs']: verify(receipt, maximum=4*1024*1024)
    folder = base/('fault-'+name); require(not folder.exists(), 'fresh VM fault output required'); folder.mkdir(mode=0o700)
    source = folder/'producer-source.py';source.write_bytes(Path(__file__).read_bytes());source.chmod(0o400)
    fault = FAULTS[name]
    header = ('/* H0-only fixed fault. Never packaged for Samsung. */\n'
        'static const char up_fault_script[]='+json.dumps(fault.get('script',profile.WORKLOAD.decode()))+';\n'+
        ''.join(f'static const int up_fault_{field}={int(fault.get(field,False))};\n'
            for field in ('early_zero','setup_error','orphan'))+
        'static const unsigned up_fault_timeout_ms=2000;\n')
    (folder/'s22plus_native_userspace_probe_fault_v1.h').write_text(header)
    compiler=shutil.which('aarch64-linux-gnu-gcc');require(compiler is not None,'ARM64 compiler absent')
    binary=folder/'probe-fault'
    command=[compiler,'-std=c11','-static','-Os','-fno-ident','-ffunction-sections','-fdata-sections','-Wl,--gc-sections',
        '-Wall','-Wextra','-Werror','-Wno-unused-function','-Wno-unused-const-variable',
        '-DS22_ROOT_INSPECT_VIRT_TEST','-DS22_USERSPACE_PROBE_FAULT','-I',folder,'-I',helper,'-I',vm.producer.NATIVE,
        vm.producer.NATIVE/'s22plus_native_userspace_probe_v1.c','-o',binary]
    (folder/'compile-command.json').write_text(json.dumps([str(x) for x in command])+'\n')
    vm.run(command,folder,'compile',timeout=60)
    supervisor=folder/'supervisor.c';supervisor.write_text(SUPERVISOR)
    vm.run([compiler,'-std=c11','-static','-Os','-Wall','-Wextra','-Werror',supervisor,'-o',folder/'supervisor'],folder,'supervisor-compile',timeout=60)
    artifact,_,_=profile.prior_inputs();busybox=Path(artifact['rootfs']['path']).parent/'busybox'
    init=f'''#!/bin/busybox sh
export PATH=/bin
/bin/busybox --install -s /bin
mount -t proc proc /proc || exit 90
mount -t sysfs sysfs /sys || exit 91
mount -t tmpfs -o mode=0755 tmpfs /dev || exit 92
mknod /dev/console c 5 1
mknod /dev/null c 1 3
exec </dev/console >/dev/console 2>&1
mount -t tmpfs -o nodev,nosuid,mode=0700 tmpfs /s22-root-work || exit 93
for n in $(seq 1 100); do [ -e /sys/class/block/vda41/dev ] && break; sleep 0.1; done
printf 'UP_VM_BEGIN\\n'
/supervisor {built['run_id_hex']}
printf 'UP_VM_SUPERVISOR status=%s\\n' "$?"
printf 'UP_VM_RO partition=%s disk=%s userdata=%s\\n' "$(cat /sys/class/block/vda41/ro)" "$(cat /sys/class/block/vda/ro)" "$(cat /sys/class/block/vda40/ro)"
poweroff -f
'''.encode()
    entries=[(item,stat.S_IFDIR|0o755,b'') for item in ('bin','dev','proc','sys','s22-root-work')]
    entries += [('init',stat.S_IFREG|0o750,init),('bin/busybox',stat.S_IFREG|0o755,busybox.read_bytes()),
        ('s22-userspace-probe',stat.S_IFREG|0o500,binary.read_bytes()),
        ('s22-root-inspect.table',stat.S_IFREG|0o400,verify(built['table']).read_bytes()),
        ('supervisor',stat.S_IFREG|0o500,(folder/'supervisor').read_bytes())]
    initramfs=folder/'initramfs.cpio.gz';initramfs.write_bytes(gzip.compress(vm.h0.newc(entries),mtime=0))
    binding=read(verify(vm.profile.filesystem.BINDING));disk=folder/'disk.img'
    vm.make_disk(base/'complete.ext4',disk,binding)
    before=vm.fixture_tools.sparse_digest(disk)
    command=[verify(setup['qemu'],maximum=128*1024*1024),'-machine','virt','-cpu','cortex-a76','-smp','2','-m','768',
        '-nic','none','-nographic','-monitor','none','-no-reboot','-kernel',vm.KERNEL,'-initrd',initramfs,
        '-append','console=ttyAMA0 rdinit=/init panic=-1','-drive',f'if=none,id=root,file={disk},format=raw',
        '-device','virtio-blk-device,drive=root,logical_block_size=4096,physical_block_size=4096']
    (folder/'command.json').write_text(json.dumps([str(x) for x in command])+'\n')
    serial=vm.run(command,folder,'serial',env=dict(os.environ,LD_LIBRARY_PATH=str(vm.QEMU/'usr/lib/x86_64-linux-gnu')),timeout=180)
    after=vm.fixture_tools.sparse_digest(disk);require(before==after,'fault changed the writable backing disk')
    serial=serial.replace(b'\r\n',b'\n')
    require(serial.count(b'UP_VM_BEGIN\n')==1 and b'UP_VM_SUPERVISOR status=0\n' in serial and
        b'UP_VM_RO partition=1 disk=0 userdata=0\n' in serial and b'reboot: Power down' in serial,
        'fixture supervisor, RO or shutdown proof absent')
    scope=re.findall(rb'^UP_VM_SCOPE settled=1 status=([0-9]+) adopted=([0-9]+)$',serial,re.M)
    require(len(scope)==1,'fixture group settlement is absent')
    stdout=b'\n'.join(line for line in serial.splitlines() if line.startswith((b'RI1_',b'UP1_')))+b'\n'
    if 'verdict' in fault:
        require(scope[0][0]==b'0','synchronous negative helper failed')
        value=profile.decode(stdout,b'',dict(table_count=built['table_count'],boot_count=built['boot_count'],max_hashed_bytes=512*1024*1024))
        require(value['verdict']==fault['verdict'] and value['userspace_proved'] is False,'negative child was promoted')
    else:
        require(int(scope[0][0])!=0 and b'RI1_RESULT complete=0 ' in stdout and
            ('error='+str(fault['error'])).encode() in stdout,'uncertain child did not fail closed')
        value=dict(status='PASS_UNCERTAIN_PROBE_REJECTED',expected_errno=fault['error'])
        if name=='orphan':require(int(scope[0][1])>=1,'live inherited-group descendant was not recovered')
    result=dict(case=name,scope='REAL_ARM64_VIRT_ONLY',helper=pin(helper/'result.json'),fault_header=pin(folder/'s22plus_native_userspace_probe_fault_v1.h'),
        fault_binary=pin(binary),supervisor_source=pin(supervisor),supervisor=pin(folder/'supervisor'),producer=pin(source),
        setup=pin(base/'setup.json'),initramfs=pin(initramfs),serial=pin(folder/'serial.stdout'),before=before,after=after,
        unchanged=True,group_settled=True,result=value,device_actions=0)
    (folder/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(name,value['status'],flush=True)
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True);parser.add_argument('--helper',type=Path,required=True)
    parser.add_argument('--case',choices=tuple(FAULTS),required=True)
    args=parser.parse_args();run_case(args.output.absolute(),args.helper.absolute(),args.case)

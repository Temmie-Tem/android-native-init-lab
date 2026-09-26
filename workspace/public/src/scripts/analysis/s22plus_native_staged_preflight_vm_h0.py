"""ARM64 staged preparation with writable disposable regular-file backing."""
import gzip
import json
import os
from pathlib import Path
import shutil
import stat

import s22plus_native_root_inspect_vm_h0 as vm
import s22plus_native_staged_preflight_profile_v1 as profile
from s22plus_native_records_v3 import pin,read,require,verify

ROOT=vm.ROOT
BASE=ROOT/'workspace/private/outputs/s22plus-debian-root-state-p406-h0-20260926-1/vm-1'
FAULTS={'setup':1,'early-zero':2,'nonzero':3,'signal':4,'timeout':5,'overflow':6,'descendant':7,'exec':8,'wrong-output':9}

WATCH = r'''
#include <dirent.h>
#include <string.h>
static int saw_checker;
static void watch_checker(pid_t owner) {
 if(saw_checker)return;
 DIR *directory=opendir("/proc");if(!directory)return;
 struct dirent *entry;
 while((entry=readdir(directory))) {
  char *end;long pid=strtol(entry->d_name,&end,10);if(*end || pid<=1)continue;
  char path[128],link[256];snprintf(path,sizeof(path),"/proc/%ld/exe",pid);
  ssize_t n=readlink(path,link,sizeof(link)-1);if(n<=0)continue;link[n]=0;
  if(strcmp(link,"/s22-fs-e2fsck"))continue;
  snprintf(path,sizeof(path),"/proc/%ld/status",pid);FILE *f=fopen(path,"r");if(!f)continue;
  char line[256];unsigned u[4]={1,1,1,1},g[4]={1,1,1,1},nnp=0;int ppid=-1;
  unsigned long long eff=1,perm=1,inh=1,amb=1;int groups_empty=0;
  while(fgets(line,sizeof(line),f)) {
   (void)sscanf(line,"PPid: %d",&ppid);(void)sscanf(line,"Uid: %u %u %u %u",u,u+1,u+2,u+3);
   (void)sscanf(line,"Gid: %u %u %u %u",g,g+1,g+2,g+3);(void)sscanf(line,"NoNewPrivs: %u",&nnp);
   (void)sscanf(line,"CapEff: %llx",&eff);(void)sscanf(line,"CapPrm: %llx",&perm);
   (void)sscanf(line,"CapInh: %llx",&inh);(void)sscanf(line,"CapAmb: %llx",&amb);
   if(!strncmp(line,"Groups:",7))groups_empty=strspn(line+7," \t\n")==strlen(line+7);
  }
  fclose(f);if(ppid!=owner)continue;
  int exact=!eff&&!perm&&!inh&&!amb&&nnp==1&&groups_empty&&getpgid((pid_t)pid)==owner;
  for(unsigned i=0;i<4;++i)if(u[i]||g[i])exact=0;
  printf("SP_VM_CHECKER_CREDENTIALS exact=%d\n",exact);fflush(stdout);saw_checker=1;
 }
 closedir(directory);
}
'''


def supervisor(out):
    import s22plus_native_userspace_probe_vm_h0 as child_fixture
    text=child_fixture.SUPERVISOR.replace('/s22-userspace-probe','/s22-staged-preflight').replace('"probe",argv[1]','"staged",argv[1]')
    text=text.replace('int main(int argc,char **argv)',WATCH+'\nint main(int argc,char **argv)')
    text=text.replace('for(;;) {','for(;;) {\n  watch_checker(child);',1).replace('UP_VM_SCOPE','SP_VM_SCOPE')
    source=out/'supervisor.c';source.write_text(text)
    vm.run(['aarch64-linux-gnu-gcc','-std=c11','-static','-Os','-Wall','-Wextra','-Werror',source,'-o',out/'supervisor'],out,'supervisor-compile')
    return out/'supervisor'


def setup(out,helper,*,binary=None,supervisor=None):
    require(not out.exists() and out.resolve()==out and out.is_relative_to(ROOT/'workspace/private/outputs'),
        'fresh private staged VM required')
    out.mkdir(mode=0o700)
    built=read(helper/'result.json')
    require(built['virt'] is True and built['staged_preflight']==profile.execution_binding(),
        'staged VM helper differs')
    artifact,_,_=profile.inspection.prior_inputs()
    busybox=Path(artifact['rootfs']['path']).parent/'busybox'
    selected=verify(built['helper']) if binary is None else Path(binary)
    invocation=f'/s22-staged-preflight staged {built["run_id_hex"]}'
    if supervisor:invocation=f'/supervisor {built["run_id_hex"]}'
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
printf 'SP_VM_BEGIN\\n'
{invocation}
result=$?
printf 'SP_VM_EXIT status=%s\\n' "$result"
printf 'SP_VM_RO partition=%s disk=%s userdata=%s\\n' "$(cat /sys/class/block/vda41/ro)" "$(cat /sys/class/block/vda/ro)" "$(cat /sys/class/block/vda40/ro)"
poweroff -f
'''.encode()
    entries=[(name,stat.S_IFDIR|0o755,b'') for name in ('bin','dev','proc','sys','s22-root-work')]
    entries += [('init',stat.S_IFREG|0o750,init),('bin/busybox',stat.S_IFREG|0o755,busybox.read_bytes()),
        ('s22-staged-preflight',stat.S_IFREG|0o500,selected.read_bytes()),
        ('s22-root-inspect.table',stat.S_IFREG|0o400,verify(built['table']).read_bytes()),
        ('s22-fs-e2fsck',stat.S_IFREG|0o500,verify(built['staged_preflight']['checker']).read_bytes())]
    if supervisor:entries.append(('supervisor',stat.S_IFREG|0o500,Path(supervisor).read_bytes()))
    (out/'initramfs.cpio.gz').write_bytes(gzip.compress(vm.h0.newc(entries),mtime=0))
    executable=out/'qemu-system-aarch64'
    shutil.copyfile(vm.QEMU/'usr/bin/qemu-system-aarch64',executable);executable.chmod(0o500)
    snapshot=out/'vm-source.py';snapshot.write_bytes(Path(__file__).read_bytes());snapshot.chmod(0o400)
    vm.producer.publish(out/'setup.json',dict(helper=pin(helper/'result.json'),
        kernel=pin(vm.KERNEL,maximum=128*1024*1024),initramfs=pin(out/'initramfs.cpio.gz',maximum=16*1024*1024),
        qemu=pin(executable,maximum=128*1024*1024),source=pin(snapshot),device_actions=0))


def run_case(out,name,*,negative=False):
    require(name in ('complete','dirty','checksum','mismatch'),'unknown VM root case')
    setup_value=read(out/'setup.json');built=read(verify(setup_value['helper']))
    folder=out/name;folder.mkdir(mode=0o700)
    native=folder/'native.ext4'
    vm.run(['cp','--reflink=auto','--sparse=always',BASE/'complete.ext4',native],folder,'copy')
    if name=='dirty':vm.debug(native,folder,'dirty','ssv state 0')
    if name=='checksum':
        # Corrupt a directory block checksum on this private fixture only.
        raw=vm.run(['debugfs','-R','blocks /etc',native],folder,'directory-blocks').decode().strip()
        numbers=raw.split();require(numbers and all(n.isdigit() for n in numbers),'directory block list differs')
        with native.open('r+b') as stream:
            offset=int(numbers[0])*4096+4092;stream.seek(offset);original=stream.read(1)
            require(len(original)==1,'directory checksum byte absent')
            stream.seek(offset);stream.write(bytes([original[0]^1]));stream.flush();os.fsync(stream.fileno())
    if name=='mismatch':vm.debug(native,folder,'mismatch','set_inode_field /etc/lab-rootfs-id mode 0100600')
    binding=read(verify(vm.profile.filesystem.BINDING));disk=folder/'disk.img'
    vm.make_disk(native,disk,binding)
    before=vm.fixture_tools.sparse_digest(disk)
    command=[verify(setup_value['qemu'],maximum=128*1024*1024),'-machine','virt','-cpu','cortex-a76','-smp','2','-m','1024',
        '-nic','none','-nographic','-monitor','none','-no-reboot','-kernel',vm.KERNEL,'-initrd',out/'initramfs.cpio.gz',
        '-append','console=ttyAMA0 rdinit=/init panic=-1','-drive',f'if=none,id=root,file={disk},format=raw',
        '-device','virtio-blk-device,drive=root,logical_block_size=4096,physical_block_size=4096']
    (folder/'command.json').write_text(json.dumps([str(x) for x in command])+'\n')
    serial=vm.run(command,folder,'serial',env=dict(os.environ,LD_LIBRARY_PATH=str(vm.QEMU/'usr/lib/x86_64-linux-gnu')),timeout=180)
    after=vm.fixture_tools.sparse_digest(disk)
    require(before==after,'staged preparation changed writable backing disk')
    clean=serial.replace(b'\r\n',b'\n')
    require(clean.count(b'SP_VM_BEGIN\n')==1 and b'SP_VM_RO partition=1 disk=0 userdata=0\n' in clean and
        b'reboot: Power down' in clean,'VM completion or RO proof absent')
    stdout=b'\n'.join(line for line in clean.splitlines() if line.startswith((b'SP1_',b'RI1_',b'UP1_')))+b'\n'
    (folder/'helper.stdout').write_bytes(stdout)
    if not negative:
        require(b'SP_VM_EXIT status=0\n' in clean,'staged helper failed')
        result=profile.decode(stdout,b'',dict(table_count=built['table_count'],boot_count=built['boot_count'],max_hashed_bytes=512*1024*1024))
        expected={'complete':'PROVED_PROTECTED_PREPARATION','dirty':'SKIPPED_UNCLEAN_ROOT',
            'checksum':'CHECKER_NOT_PROVED','mismatch':'SKIPPED_ROOT_NOT_EXACT'}[name]
        require(result['verdict']==expected,'staged VM verdict differs')
    else:result=dict(status='FAULT_OBSERVED',progress=profile.progress(stdout))
    value=dict(schema='s22plus-staged-preflight-vm-h0-v1',scope='ARM64_VIRT_NOT_SAMSUNG',case=name,
        helper=setup_value['helper'],setup=pin(out/'setup.json'),stdout=pin(folder/'helper.stdout'),
        serial=pin(folder/'serial.stdout'),before=before,after=after,disk_unchanged=True,result=result,device_actions=0)
    return vm.producer.publish(folder/'result.json',value)


def fault_case(out,helper,name):
    require(name in FAULTS and not out.exists(),'fresh named fault output required')
    build=out.with_name(out.name+'-build');build.mkdir(mode=0o700)
    header=('/* H0-only child fault; virtual discovery is mandatory. */\n'
        'static const char up_fault_script[]="";\n'
        'static const int up_fault_early_zero=0,up_fault_setup_error=0,up_fault_orphan=0;\n'
        'static const unsigned up_fault_timeout_ms=2000;\n'
        f'static const unsigned sp_fault_kind=2,sp_fault_mode={FAULTS[name]};\n')
    (build/'s22plus_native_userspace_probe_fault_v1.h').write_text(header)
    command=['aarch64-linux-gnu-gcc','-std=c11','-static','-Os','-fno-ident','-ffunction-sections','-fdata-sections','-Wl,--gc-sections',
        '-Wall','-Wextra','-Werror','-Wno-unused-function','-Wno-unused-const-variable',
        '-DS22_ROOT_INSPECT_VIRT_TEST','-DS22_STAGED_PREFLIGHT_FAULT','-I',build,'-I',helper,'-I',vm.producer.NATIVE,
        vm.producer.NATIVE/'s22plus_native_staged_preflight_v1.c','-o',build/'helper']
    vm.run(command,build,'compile')
    owner=supervisor(build)
    setup(out,helper,binary=build/'helper',supervisor=owner)
    receipt=run_case(out,'complete',negative=True)
    stdout=(out/'complete/helper.stdout').read_bytes();serial=(out/'complete/serial.stdout').read_bytes().replace(b'\r\n',b'\n')
    require(b'SP_VM_CHECKER_CREDENTIALS exact=1\n' in serial and b'SP_VM_SCOPE settled=1 ' in serial,
        'actual checker credentials or group settlement missing')
    built=read(helper/'result.json');binding=dict(table_count=built['table_count'],boot_count=built['boot_count'],max_hashed_bytes=512*1024*1024)
    if name in ('setup','nonzero','signal','exec','wrong-output'):
        result=profile.decode(stdout,b'',binding)
        require(result['verdict']=='LOADER_NOT_PROVED' and result['preparation_proved'] is False,
            'synchronous negative child was promoted')
    else:
        try:profile.decode(stdout,b'',binding)
        except ValueError:pass
        else:raise ValueError('unsettled/unknown fault was promoted to completion')
        require(b'RI1_RESULT complete=0 ' in stdout,'fault lost its incomplete helper result')
    return vm.producer.publish(out/'fault-result.json',dict(case=name,vm=receipt,helper=pin(build/'helper'),
        compile_source=pin(vm.producer.NATIVE/'s22plus_native_staged_preflight_v1.c'),header=pin(build/'s22plus_native_userspace_probe_fault_v1.h'),
        supervisor=pin(owner),supervisor_source=pin(build/'supervisor.c'),settled=True,checker_credentials=True,device_actions=0))

#!/usr/bin/env python3
"""Two real Debian boots on an isolated disk, with a deliberately H0-only guard.

Board/module/UFS/full-root admission are not qualified by this component.
Every network action is pinned SSH to a loopback-only QEMU forwarding port.
"""
import argparse
from collections import deque
import gzip
import hashlib
import hmac
import ipaddress
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import signal
import socket
import stat
import struct
import subprocess
import sys
import tarfile
import time
import uuid

import mount_probe as shared
from mount_probe import ROOT, HERE, PRIVATE, require, regular, pin, save, run_command, superblock
import s22plus_debian_autoboot_minimal_v1 as minimal
import s22plus_debian_handoff_profile_v1 as handoff
import s22plus_debian_access_v1 as access
import device_action_raw_capture_v1 as raw
from s22plus_native_records_v3 import verify

SEED = PRIVATE/'s22plus-debian-minimal-p456-h0-20261023-1/vm-2/normal/native.ext4'
CRYPTO = ROOT/'workspace/public/src/native-init/s22plus_fyg8_max77705_result_parser.inc.c'
CASES = ('normal','b2-before-mount','b2-after-mount','b2-after-early','b2-clean-error',
         'intent-before-command','rc6-before-remount','failed-root-remount','unexpected-remount')
DOMAIN = b'S22-P458-H0-PHASE-v1'
MAX_SERIAL = 1024*1024


def disk_pin(path):
    path=regular(path)
    return dict(path=str(path),**shared.fixture.fixture_tools.sparse_digest(path))


def disk_verify(receipt):
    require(disk_pin(receipt['path'])==receipt,'immutable sparse VM disk changed')
    return Path(receipt['path'])


def archive_files(archive, names):
    """Resolve only named archive members, without host extraction or execution."""
    result = {}
    with tarfile.open(regular(archive)) as tar:
        members = {m.name.removeprefix('./'): m for m in tar}
        for name in names:
            todo = deque(name.split('/')); parts=[]; hops=0
            while todo:
                piece=todo.popleft()
                if piece in ('', '.'): continue
                if piece=='..':
                    require(parts, 'archive link escapes root'); parts.pop(); continue
                member=members.get('/'.join([*parts,piece]))
                if member and member.issym():
                    hops+=1; require(hops<=40,'archive symlink loop')
                    if member.linkname.startswith('/'):parts=[]
                    todo.extendleft(reversed(member.linkname.split('/')))
                else: parts.append(piece)
            resolved='/'.join(parts); member=members[resolved]
            while member.islnk():
                hops+=1; require(hops<=40,'archive hardlink loop')
                resolved=member.linkname.removeprefix('./'); member=members[resolved]
            require(member.isreg() and member.uid==member.gid==0 and member.size<=4*1024**2,
                    'selected archive member is not bounded/root-owned/regular')
            with tar.extractfile(member) as stream: data=stream.read(member.size+1)
            require(len(data)==member.size, 'short archive member')
            result[name]=dict(resolved=resolved,mode=member.mode,size=len(data),
                              sha256=hashlib.sha256(data).hexdigest(),data=data)
    return result


def build(out):
    require(out.resolve()==out and out.is_relative_to(PRIVATE),'private H0 build required')
    out.mkdir(mode=0o700)
    artifact,_,_=handoff.prior_inputs(); archive=verify(artifact['rootfs'],maximum=256*1024**2)
    names=('etc/inittab','usr/sbin/init','usr/sbin/cron','usr/sbin/sshd','usr/bin/dash',
           'lib/aarch64-linux-gnu/libc.so.6','lib/ld-linux-aarch64.so.1',
           'etc/init.d/rc','etc/init.d/umountroot','etc/init.d/reboot','etc/init.d/halt',
           'etc/init.d/bootlogs','etc/init.d/lab-firstboot')
    files=archive_files(archive,names)
    run=uuid.uuid4().hex; key=secrets.token_bytes(32)
    # Both source and destination are checked regular files; no device syntax.
    seed=out/'seed.ext4'; run_command(['cp','--reflink=auto','--sparse=always',regular(SEED),seed],out/'copy-seed.log')
    with seed.open('rb') as stream:stream.seek(1024+104);fsuuid=stream.read(16)
    require(len(fsuuid)==16,'short fixture UUID')
    def array(name,data):return 'static const uint8_t '+name+'[]={'+','.join(map(str,data))+'};\n'
    header=array('p458_key',key)+array('p458_run',bytes.fromhex(run))+array('p458_uuid',fsuuid)
    header+='static const char p458_run_text[]='+json.dumps(run)+';\n'
    for name,path in [('init','usr/sbin/init'),('cron','usr/sbin/cron'),('sshd','usr/sbin/sshd')]:
        header+=array('p458_'+name+'_sha',bytes.fromhex(files[path]['sha256']))
    (out/'p458-seal.h').write_text(header); (out/'key').write_bytes(key)
    helper=out/'guard'
    run_command(['aarch64-linux-gnu-gcc','-std=c11','-O2','-static','-Wall','-Wextra','-Werror',
                 '-Wno-unused-function','-I',out,'-I',CRYPTO.parent,HERE/'reboot_guard.c','-o',helper],out/'compile.log')
    run_command(['file',helper],out/'file.log')
    assets=out/'assets';assets.mkdir(mode=0o700)
    inittab=files['etc/inittab']['data']
    require(inittab.count(b'si::sysinit:/etc/init.d/rcS\n')==1 and
            inittab.count(b'l2:2:wait:/etc/init.d/rc 2\n')==1 and
            inittab.count(b'l6:6:wait:/etc/init.d/rc 6\n')==1,'inittab shape differs')
    inittab=inittab.replace(b'si::sysinit:/etc/init.d/rcS\n',b'si::sysinit:/run/p458/rc-minimal S\n')
    inittab=inittab.replace(b'l2:2:wait:/etc/init.d/rc 2\n',
        b'l2:2:wait:/etc/init.d/rc 2\nph:2:wait:/run/p458/rc2-ready\n')
    inittab=inittab.replace(b'l6:6:wait:/etc/init.d/rc 6\n',b'l6:6:wait:/run/p458/rc6\n')
    (assets/'inittab').write_bytes(inittab)
    (assets/'rc-minimal').write_bytes(minimal.dispatcher())
    _,old_assets=handoff.payloads(virt=True)
    (assets/'usb').write_bytes(old_assets['usb'])
    (assets/'crontab').write_bytes(old_assets['crontab'])
    (assets/'rc2-ready').write_text('#!/bin/sh\nset -eu\nprintf "ready\\n" >/run/p458/ready\n')
    # Normal executes the packaged dispatcher; failure variants substitute only
    # its terminal sequence to omit or interrupt the root-remount operation.
    with tarfile.open(archive) as tar:
        links=[(m.name,m.linkname) for m in tar if re.fullmatch(r'etc/rc6.d/K[0-9]{2}[^/]+',m.name)]
    require(len(links)==12 and links[-2][1]=='../init.d/umountroot' and links[-1][1]=='../init.d/reboot',
            'rc6 link sequence differs')
    rc6='''#!/bin/sh
PATH=/usr/sbin:/usr/bin:/sbin:/bin
export PATH
case=$(cat /run/p458/case)
case "$case" in
 rc6-before-remount|failed-root-remount) ;;
 *) exec /etc/init.d/rc 6 ;;
esac
'''
    for _,target in links:
        script='/etc/init.d/'+target.rsplit('/',1)[1]
        if script.endswith('/umountroot'):
            rc6+='''if [ "$case" = rc6-before-remount ]; then
 printf 'P458_POINT rc6-before-remount\\n' >/dev/console
 while :; do sleep 3600; done
fi
printf 'P458_INJECT root-remount-omitted\\n' >/dev/console
'''
        else: rc6+=script+' stop\n'
    (assets/'rc6').write_text(rc6)
    qualify='''#!/bin/sh
set -eu
PATH=/usr/sbin:/usr/bin:/sbin:/bin
export PATH
test -f /run/p458/ready
case "${SSH_ORIGINAL_COMMAND:-}" in
 health)
  /run/p458/guard health
  printf 'P458_BOOT_COUNT %s\\n' "$(cat /var/lib/lab/boot-count)"
  printf 'P458_HOST_KEY '
  sha256sum /etc/ssh/ssh_host_ed25519_key.pub | cut -d' ' -f1
  ;;
 complete) /run/p458/guard complete ;;
 reboot)
  /run/p458/guard intent
  snapshot=$(/run/p458/guard health)
  if [ "$(cat /run/p458/case)" = intent-before-command ]; then
   printf 'P458_POINT intent-before-command\\n' >/dev/console
   while :; do sleep 3600; done
  fi
  /sbin/shutdown -r now
  printf 'P458_REBOOT_REQUEST_ACCEPTED\\n%s\\n' "$snapshot"
  ;;
 shutdown)
  /run/p458/guard shutdown
  snapshot=$(/run/p458/guard health)
  /sbin/shutdown -h now
  printf 'P458_SHUTDOWN_REQUEST_ACCEPTED\\n%s\\n' "$snapshot"
  ;;
 *) exit 64 ;;
esac
'''
    (assets/'qualify').write_text(qualify)
    for path in assets.iterdir():path.chmod(0o500 if path.name not in ('inittab','crontab') else 0o400)
    lib=out/'libraries';lib.mkdir(mode=0o700)
    for name in ('usr/bin/dash','lib/aarch64-linux-gnu/libc.so.6','lib/ld-linux-aarch64.so.1'):
        (lib/Path(name).name).write_bytes(files[name]['data'])
    plan=access.inputs(run)
    receipt=dict(schema='s22-p458-reboot-vm-build-v1',run=run,key=pin(out/'key'),guard=pin(helper),
        seed=disk_pin(seed),seed_super=superblock(seed),archive=artifact['rootfs'],kernel=pin(shared.KERNEL),
        busybox=pin(Path(artifact['rootfs']['path']).parent/'busybox'),plan=plan,
        files={k:{a:b for a,b in v.items() if a!='data'} for k,v in files.items()},rc6_links=links,
        sources=[pin(Path(__file__)),pin(HERE/'reboot_guard.c'),pin(HERE/'mount_probe.py'),
                 pin(CRYPTO),pin(Path(minimal.__file__)),pin(Path(shared.fixture.fixture_tools.__file__))],
        assets={p.name:pin(p) for p in assets.iterdir()},
        libraries={p.name:pin(p) for p in lib.iterdir()},
        physical_full_root_admission=False,device_actions=0)
    save(out/'build.json',receipt);print('BUILT_H0_REBOOT_COMPONENT',flush=True)
    return receipt


def make_initramfs(out,built,case):
    require(case in CASES,'unknown H0 case')
    init='''#!/bin/sh
PATH=/bin
export PATH
/bin/busybox --install -s /bin
stop() { printf 'P458_INITIAL_STOP\\n'; poweroff -f; while :; do sleep 3600; done; }
mount -t proc proc /proc || stop
mount -t sysfs sysfs /sys || stop
mount -t tmpfs -o mode=0755 tmpfs /dev || stop
mknod -m 600 /dev/console c 5 1 || stop
mknod -m 666 /dev/null c 1 3 || stop
mknod -m 600 /dev/kmsg c 1 11 || stop
exec </dev/console >/dev/console 2>&1
printf 'P458_INITIAL_PID1 pid=%s exe=%s\\n' "$$" "$(readlink /proc/1/exe)"
mount -t tmpfs -o nodev,nosuid,mode=0755 tmpfs /run || stop
mkdir /run/p458 /run/config /dev/pts /dev/shm || stop
mount -t devpts devpts /dev/pts || stop
mount -t tmpfs tmpfs /dev/shm || stop
mount -t configfs configfs /run/config || stop
cp /assets/* /run/p458/ || stop
cp /guard /run/p458/guard || stop
cp /case /run/p458/case || stop
chmod 500 /run/p458/guard || stop
for n in $(seq 1 100); do [ -e /sys/class/block/vda/dev ] && break; sleep 0.1; done
IFS=: read -r major minor </sys/class/block/vda/dev
mknod -m 600 /dev/vda b "$major" "$minor" || stop
/run/p458/guard boot || stop
for path in dev proc sys run etc/inittab etc/crontab etc/init.d/lab-usb usr/local/sbin/lab-qualify; do
 test -e "/newroot/$path" || stop
done
mount --bind /run/p458/inittab /newroot/etc/inittab || stop
mount --bind /run/p458/crontab /newroot/etc/crontab || stop
mount --bind /run/p458/usb /newroot/etc/init.d/lab-usb || stop
mount --bind /run/p458/qualify /newroot/usr/local/sbin/lab-qualify || stop
mount --move /dev /newroot/dev || stop
mount --move /run /newroot/run || stop
mount --move /sys /newroot/sys || stop
mount --move /proc /newroot/proc || stop
exec /bin/busybox switch_root /newroot /sbin/init
'''.encode()
    entries=[(name,stat.S_IFDIR|0o755,b'') for name in
             ('bin','dev','proc','sys','run','newroot','assets','lib','lib/aarch64-linux-gnu')]
    entries += [('init',stat.S_IFREG|0o750,init),
                ('bin/sh',stat.S_IFREG|0o755,verify(built['libraries']['dash']).read_bytes()),
                ('bin/busybox',stat.S_IFREG|0o755,verify(built['busybox']).read_bytes()),
                ('lib/ld-linux-aarch64.so.1',stat.S_IFREG|0o755,verify(built['libraries']['ld-linux-aarch64.so.1']).read_bytes()),
                ('lib/aarch64-linux-gnu/libc.so.6',stat.S_IFREG|0o755,verify(built['libraries']['libc.so.6']).read_bytes()),
                ('guard',stat.S_IFREG|0o500,verify(built['guard']).read_bytes()),
                ('case',stat.S_IFREG|0o400,(case+'\n').encode())]
    entries += [('assets/'+name,stat.S_IFREG|stat.S_IMODE(Path(item['path']).stat().st_mode),verify(item).read_bytes())
                for name,item in built['assets'].items()]
    archive=out/'initramfs.cpio.gz'
    with archive.open('xb') as stream:stream.write(gzip.compress(shared.fixture.h0.newc(entries),mtime=0))
    return archive


def decode_file(data,key,run,phase,early,first=None):
    require(len(data) in ((256,) if early else (256,512,768)),'bad record-file size')
    previous=bytes(32); rows=[]
    for i in range(len(data)//256):
        record=data[i*256:(i+1)*256]
        version,role,p,base,count,reserved=struct.unpack_from('<6I',record,8)
        expected=1 if early else 2 if i==0 else 3 if i==1 else 4 if phase==1 else 5
        require(record[:8]==b'S22RBH0\0' and version==1 and role==expected and p==phase and
                base<=65531 and count==base+2*phase-(1 if early else 0) and not reserved and
                record[160:176]==bytes.fromhex(run) and not any(record[176:224]) and
                record[104:136]==previous and hmac.compare_digest(record[224:],hmac.digest(key,DOMAIN+record[:224],'sha256')),
                'H0 record authentication/grammar rejected')
        elapsed=struct.unpack_from('<Q',record,32)[0]
        require(elapsed<300000 and (not rows or elapsed>=rows[-1]['elapsed_ms']),'record time rejected')
        if early:require(not any(record[72:104]),'early record has prior-file hash')
        else:
            require(first is not None and record[72:104]==hashlib.sha256(first).digest() and
                    record[40:72]==first[40:72] and base==struct.unpack_from('<I',first,20)[0],
                    'runtime file did not join its early file')
        pids=struct.unpack_from('<3Q',record,136)
        require(pids==(0,0,0) if role<=2 else pids[0]==1 and pids[1]>1 and pids[2]>1 and pids[1]!=pids[2],
                'record process facts differ')
        previous=hashlib.sha256(record).digest()
        rows.append(dict(role=role,phase=phase,base=base,mount_count=count,elapsed_ms=elapsed,
                         boot=record[40:72].hex(),pids=list(pids)))
    if len(rows)>=2:require(rows[1]['elapsed_ms']-rows[0]['elapsed_ms']>=120000,'service span missing')
    return rows


def parse_health(data,built):
    require(len(data)<=32768,'health output too large')
    text=data.decode('ascii'); matches=re.findall(
        r'^P458_HEALTH phase=([12]) base=([0-9]+) boot=([0-9a-f]{64}) uptime_ms=([0-9]+) init_pid=1 cron_pid=([0-9]+) sshd_pid=([0-9]+)$',text,re.M)
    require(len(matches)==1,'one health row required')
    p,b,boot,ms,cron,ssh=matches[0];phase=int(p)
    files={}
    for which,kind,body in re.findall(r'^P458_FILE phase=([12]) kind=(early|runtime) data=([0-9a-f]+)$',text,re.M):
        name=f'b{which}-{kind}';require(name not in files,'duplicate file');files[name]=bytes.fromhex(body)
    require(set(files)=={f'b{i}-{kind}' for i in range(1,phase+1) for kind in ('early','runtime')},'file set differs')
    key=verify(built['key']).read_bytes();decoded={}
    for i in range(1,phase+1):
        first=files[f'b{i}-early'];decoded[f'b{i}-early']=decode_file(first,key,built['run'],i,True)
        decoded[f'b{i}-runtime']=decode_file(files[f'b{i}-runtime'],key,built['run'],i,False,first)
    require(decoded[f'b{phase}-early'][0]['boot']==boot,'health did not join current boot')
    current=decoded[f'b{phase}-runtime']
    require(int(b)==current[0]['base'] and current[-1]['elapsed_ms']<=int(ms)<300000 and
            1<int(cron)<2**31 and 1<int(ssh)<2**31 and int(cron)!=int(ssh),
            'live health fields contradict authenticated phase or bounds')
    if len(current)>=2:
        require(current[-1]['pids']==[1,int(cron),int(ssh)],'live process identity differs from completion')
    if phase==2:
        prior=decoded['b1-runtime']
        require(len(prior)==3 and prior[-1]['role']==4 and prior[0]['base']==current[0]['base'] and
                prior[0]['boot']!=current[0]['boot'],'second boot lacks one exact completed first-boot intent')
    return dict(phase=phase,base=int(b),boot=boot,uptime_ms=int(ms),cron_pid=int(cron),sshd_pid=int(ssh),
                records=decoded,files=files)


class Guest:
    def __init__(self,out,built,case,disk):
        self.out,self.built,self.case,self.disk=out,built,case,regular(disk)
        out.mkdir(mode=0o700);self.serial=out/'serial.log';self.process=None;self.ordinal=0
        with socket.socket() as sock:sock.bind(('127.0.0.1',0));self.port=sock.getsockname()[1]

    def start(self):
        archive=make_initramfs(self.out,self.built,self.case);link=self.built['plan']['link']
        network=ipaddress.ip_interface(link['device_address']).network
        if network.prefixlen>24:network=network.supernet(new_prefix=24)
        net=f'user,id=net,restrict=on,net={network},host={link["host_address"].split("/")[0]},'
        net+=f'dhcpstart={link["ssh_address"]},dns={network.network_address+254},hostfwd=tcp:127.0.0.1:{self.port}-{link["ssh_address"]}:22'
        args=[shared.fixture.QEMU/'usr/bin/qemu-system-aarch64','-machine','virt','-cpu','cortex-a76','-smp','8','-m','1024',
              '-display','none','-monitor','none','-serial','stdio','-kernel',verify(self.built['kernel'],maximum=128*1024**2),'-initrd',archive,
              '-append','maxcpus=1 cpuidle.off=1 console=ttyAMA0 rdinit=/init panic=-1',
              '-drive',f'if=none,id=root,file={self.disk},format=raw,cache=writeback',
              '-device','virtio-blk-device,drive=root','-netdev',net,
              '-device','virtio-net-device,netdev=net,mac='+link['device_mac']]
        save(self.out/'command.json',list(map(str,args)))
        self.stream=self.serial.open('xb')
        self.process=subprocess.Popen(list(map(str,args)),stdin=subprocess.PIPE,stdout=self.stream,stderr=subprocess.STDOUT,
            start_new_session=True,env=dict(os.environ,LD_LIBRARY_PATH=str(shared.fixture.QEMU/'usr/lib/x86_64-linux-gnu')))
        self.started=time.monotonic()

    def log(self):
        require(self.serial.stat().st_size<=MAX_SERIAL,'serial exceeded bound')
        return self.serial.read_bytes().replace(b'\r\n',b'\n')

    def alive(self):
        require(self.process.poll() is None,'VM exited; inspect serial')
        require(b'P458_GUARD_ERROR' not in self.log() and b'P458_INITIAL_STOP' not in self.log(),
                'VM guard or initial boot stopped')

    def ssh(self,command,label,timeout=10):
        require(command in ('health','complete','reboot','shutdown'),'unselected fixture command')
        plan=self.built['plan'];self.ordinal+=1
        args=[verify(plan['ssh']),'-F','/dev/null','-i',verify(plan['client_key']),
              '-o','BatchMode=yes','-o','IdentitiesOnly=yes','-o','StrictHostKeyChecking=yes',
              '-o','UserKnownHostsFile='+str(verify(plan['known_hosts'])),'-o','GlobalKnownHostsFile=/dev/null',
              '-o','HostKeyAlias='+plan['link']['ssh_address'],'-o','LogLevel=ERROR',
              '-o','ConnectTimeout=1','-o','ConnectionAttempts=1','-p',str(self.port),'root@127.0.0.1',command]
        return raw.acquire_command(list(map(str,args)),self.out,f'{self.ordinal:03d}-{label}',timeout=timeout,
                                   stdout_maximum=32768,stderr_maximum=16384)

    def healthy(self,phase,timeout=75):
        deadline=time.monotonic()+timeout
        while time.monotonic()<deadline:
            self.alive();handle=self.ssh('health',f'health-b{phase}')
            if handle.returncode==0:
                result=parse_health(raw.read_stdout(handle,maximum=32768),self.built)
                if result['phase']==phase:
                    result['capture']=pin(handle.receipt_path)
                    text=raw.read_stdout(handle,maximum=32768).decode()
                    count=re.findall(r'^P458_BOOT_COUNT ([1-9][0-9]*)$',text,re.M)
                    host=re.findall(r'^P458_HOST_KEY ([0-9a-f]{64})$',text,re.M)
                    require(len(count)==len(host)==1 and not raw.read_stderr(handle,maximum=16384),'health extra fields differ')
                    result.update(boot_count=int(count[0]),host_key=host[0]);return result
            time.sleep(0.4)
        raise ValueError('SSH health window expired')

    def services(self,phase):
        first=self.healthy(phase);samples=[first];next_at=time.monotonic()+8
        deadline=time.monotonic()+155
        while samples[-1]['uptime_ms']-first['uptime_ms']<120000:
            require(time.monotonic()<deadline,'service window expired');self.alive()
            if time.monotonic()<next_at:
                time.sleep(min(1,next_at-time.monotonic()));continue
            current=self.healthy(phase,timeout=10)
            require(current['boot']==first['boot'] and current['boot_count']==first['boot_count'] and
                    current['cron_pid']==first['cron_pid'] and current['sshd_pid']==first['sshd_pid'],
                    'service/boot identity changed within observation')
            samples.append(current);next_at=time.monotonic()+8
            # Fixed read-only samples are bounded even on a fast guest.
            require(len(samples)<=20,'too many service samples')
        handle=self.ssh('complete',f'complete-b{phase}')
        raw.require_success(handle)
        require(raw.read_stdout(handle,maximum=32768).endswith(f'P458_APPEND role=3 phase={phase}\n'.encode()),'completion not accepted')
        completed=self.healthy(phase,timeout=10)
        require(completed['boot']==first['boot'] and len(completed['files'][f'b{phase}-runtime'])==512 and
                completed['records'][f'b{phase}-runtime'][-1]['role']==3,'completed producer record not observed')
        print('PASS_REAL_DEBIAN_SERVICES',phase,samples[-1]['uptime_ms']-first['uptime_ms'],flush=True)
        return first,completed,samples

    def wait_point(self,point,timeout=40):
        until=time.monotonic()+timeout
        while time.monotonic()<until:
            self.alive()
            if f'P458_POINT {point}\n'.encode() in self.log():return
            time.sleep(0.03)
        raise ValueError('missing guest point: '+point)

    def finish(self,kill=False,timeout=40):
        if self.process.poll() is None:
            if kill:os.killpg(self.process.pid,signal.SIGKILL)
            try:self.process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                os.killpg(self.process.pid,signal.SIGKILL);self.process.wait();raise
        self.stream.flush();os.fsync(self.stream.fileno());self.stream.close();self.serial.chmod(0o400)
        if self.process.stdin:self.process.stdin.close()
        return self.process.returncode


def public_result(row):
    return {k:({name:dict(size=len(body),sha256=hashlib.sha256(body).hexdigest()) for name,body in v.items()}
                if k=='files' else v) for k,v in row.items()}


def once_control(guest,out,operation,boot):
    require(operation in ('reboot','shutdown'),'unselected control')
    # Exclusive durable creation precedes the only transmission. An uncertain
    # transport result leaves this intent in place, including across processes.
    save(out/(operation+'-intent.json'),dict(command=operation,boot=boot,host_monotonic=time.monotonic()))
    return guest.ssh(operation,operation+'-once',timeout=20)


def failure_diagnostic(error,disk):
    result=dict(error_type=type(error).__name__,error=str(error)[:1024])
    try:result['final_super']=superblock(disk)
    except Exception as diagnostic:
        result['final_super']=None
        result['super_diagnostic_error']=dict(type=type(diagnostic).__name__,message=str(diagnostic)[:512])
    return result


def run_normal(out,built,build_receipt):
    out.mkdir(mode=0o700);disk=out/'disk.ext4'
    run_command(['cp','--reflink=auto','--sparse=always',disk_verify(built['seed']),disk],out/'copy.log')
    save(out/'inputs.json',dict(build=build_receipt,driver=pin(Path(__file__)),
        initial_disk=disk_pin(disk),physical_full_root_admission=False,device_actions=0))
    guest=Guest(out/'guest',built,'normal',disk)
    try:
        guest.start()
        first,last,samples1=guest.services(1)
        response=once_control(guest,out,'reboot',first['boot'])
        raw.require_success(response);data=raw.read_stdout(response,maximum=32768)
        require(b'P458_REBOOT_REQUEST_ACCEPTED\n' in data,'normal reboot not acknowledged')
        final1=parse_health(data,built)
        require(len(final1['files']['b1-runtime'])==768,'final intent snapshot incomplete')
        guest.wait_point('snapshot-ready')
        require(superblock(disk)==dict(count=first['base']+2,state=1,recover=False,orphan=0),'boot-1 did not return clean')
        run_command(['cp','--reflink=auto','--sparse=always',disk,out/'boot1-clean.ext4'],out/'snapshot.log')
        guest.process.stdin.write(b'G\n');guest.process.stdin.flush()
        second,last2,samples2=guest.services(2)
        require(second['boot']!=first['boot'] and second['host_key']==first['host_key'] and
                second['boot_count']==first['boot_count']+1,'reboot identity/persistence differs')
        for name in ('b1-early','b1-runtime'):
            require(second['files'][name]==final1['files'][name],'first-boot bytes not retained exactly')
            (out/(name+'.bin')).write_bytes(final1['files'][name])
        response2=once_control(guest,out,'shutdown',second['boot'])
        raw.require_success(response2)
        shutdown_data=raw.read_stdout(response2,maximum=32768)
        require(b'P458_SHUTDOWN_REQUEST_ACCEPTED\n' in shutdown_data,'shutdown not acknowledged')
        final2=parse_health(shutdown_data,built)
        require(final2['phase']==2 and final2['boot']==second['boot'] and
                len(final2['files']['b2-runtime'])==768 and final2['records']['b2-runtime'][-1]['role']==5,
                'final phase-2 authenticated tail absent')
        require(guest.finish()==0 and b'reboot: Power down' in guest.log(),'normal final poweroff absent')
        require(superblock(disk)==dict(count=first['base']+4,state=1,recover=False,orphan=0),'boot-2 did not return clean')
        result=dict(status='PASS_H0_TWO_REAL_DEBIAN_BOOTS',first=public_result(first),last_first=public_result(last),
            second=public_result(second),last_second=public_result(last2),
            first_samples=[public_result(x) for x in samples1],second_samples=[public_result(x) for x in samples2],
            reboot_capture=pin(response.receipt_path),shutdown_capture=pin(response2.receipt_path),
            final_first_snapshot=public_result(final1),final_second_snapshot=public_result(final2),
            boot1_clean=disk_pin(out/'boot1-clean.ext4'),
            serial=pin(guest.serial),final_super=superblock(disk),
            inputs=pin(out/'inputs.json'),initramfs=pin(guest.out/'initramfs.cpio.gz'),
            physical_full_root_admission=False,device_actions=0)
        save(out/'result.json',result)
        require(json.loads((out/'result.json').read_text())==result,'success result did not reopen')
        print(result['status'],flush=True)
        return result
    except Exception as error:
        if getattr(guest,'stream',None) is not None and not guest.stream.closed:
            guest.finish(kill=guest.process is not None and guest.process.poll() is None)
        failure=dict(status='H0_FAILURE_NO_COMMAND_REPLAY',**failure_diagnostic(error,disk),
            reboot_intent=(out/'reboot-intent.json').exists(),
            shutdown_intent=(out/'shutdown-intent.json').exists(),serial=pin(guest.serial) if guest.serial.exists() else None,
            captures=[pin(p) for p in sorted(guest.out.glob('*.capture.json'))],
            inputs=pin(out/'inputs.json'),
            initramfs=pin(guest.out/'initramfs.cpio.gz') if (guest.out/'initramfs.cpio.gz').exists() else None,
            device_actions=0)
        save(out/'failure.json',failure)
        require(json.loads((out/'failure.json').read_text())==failure,'failure result did not reopen')
        raise
    finally:
        if getattr(guest,'stream',None) is not None and not guest.stream.closed:
            guest.finish(kill=guest.process is not None and guest.process.poll() is None)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('phase',choices=('build','normal'))
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--build',type=Path)
    args=parser.parse_args();os.umask(0o077)
    out=args.output.absolute();require(out.resolve()==out and out.is_relative_to(PRIVATE),'private direct output required')
    if args.phase=='build':build(out)
    else:
        require(args.build is not None,'build receipt required')
        built=json.loads(regular(args.build/'build.json').read_text())
        for source in built['sources']:verify(source)
        run_normal(out,built,pin(args.build/'build.json'))


if __name__=='__main__':main()

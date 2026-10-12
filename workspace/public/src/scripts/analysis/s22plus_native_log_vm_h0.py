"""Actual ARM64 helper/ring exercise with explicit board/retention substitutes."""
import gzip
import hashlib
import os
from pathlib import Path
import stat
import shutil
import subprocess

import s22plus_native_log_h0 as producer
import s22plus_native_root_inspect_vm_h0 as vm
import s22plus_native_log_protocol_v1 as protocol
from s22plus_native_records_v3 import pin,private_path,publish,read,require,verify

ROOT=producer.ROOT
CASES=('normal','insert-error','binding-missing','logger-off','backend-absent',
    'backend-missing','existing','bad-module','alias-exists')
EXPECTED={name:(stage,attempts) for name,stage,attempts in (
    ('normal',7,1),('insert-error',3,1),('binding-missing',4,1),('logger-off',2,0),
    ('backend-absent',6,1),('backend-missing',6,1),('existing',1,0),('bad-module',1,0),('alias-exists',1,0))}


def case(out,built,name):
    require(name in CASES,'unknown logger VM case');out.mkdir(mode=0o700)
    artifact,_,_=vm.profile.prior_inputs()
    busybox=Path(artifact['rootfs']['path']).parent/'busybox'
    module=verify(built['module']).read_bytes()
    if name=='bad-module':module=module[:-1]+bytes([module[-1]^1])
    extra=''
    if name=='logger-off':extra='printf "off\\n" >/proc/sys/kernel/printk_devkmsg || exit 96\n'
    if name=='alias-exists':extra='printf "sentinel\\n" >/dev/log-calibration-kmsg || exit 97\n'
    init=f'''#!/bin/busybox sh
export PATH=/bin
/bin/busybox --install -s /bin
mount -t proc proc /proc || exit 90
mount -t sysfs sysfs /sys || exit 91
mount -t tmpfs -o nosuid,mode=0755 tmpfs /dev || exit 92
mknod /dev/console c 5 1
mknod /dev/null c 1 3
exec </dev/console >/dev/console 2>&1
mount -t tmpfs -o nosuid,nodev,mode=0700 tmpfs /s22-root-work || exit 93
mount -t tmpfs -o nosuid,nodev,mode=0700 tmpfs /run || exit 94
printf '1\\n' >/proc/sys/kernel/printk
{extra}printf 'LC_VM_BEGIN\\n'
/s22-log-calibration calibrate {built['run_id_hex']}
result=$?
printf 'LC_VM_EXIT status=%s\\n' "$result"
if [ -e /dev/log-calibration-kmsg ]; then printf 'LC_VM_ALIAS preserved=%s\\n' "$(cat /dev/log-calibration-kmsg)"; else printf 'LC_VM_ALIAS absent=1\\n'; fi
printf 'LC_VM_LOGGER_MODE=%s\\n' "$(cat /proc/sys/kernel/printk_devkmsg)"
poweroff -f
'''.encode()
    entries=[(n,stat.S_IFDIR|0o755,b'') for n in ('bin','dev','sys','proc','run','lab','s22-root-work')]
    entries += [('init',stat.S_IFREG|0o750,init),('bin/busybox',stat.S_IFREG|0o755,busybox.read_bytes()),
        ('s22-log-calibration',stat.S_IFREG|0o500,verify(built['helper']).read_bytes()),
        ('s22-log-module.ko',stat.S_IFREG|0o400,module),('lab/fault',stat.S_IFREG|0o400,(name+'\n').encode())]
    archive=out/'initramfs.cpio.gz';archive.write_bytes(gzip.compress(vm.h0.newc(entries),mtime=0))
    disk=out/'sentinel.img'
    with disk.open('xb') as f:f.truncate(8*1024**2)
    before=hashlib.sha256(disk.read_bytes()).hexdigest()
    command=[out.parent/'qemu-system-aarch64','-machine','virt','-cpu','cortex-a76','-smp','2','-m','256',
        '-nic','none','-display','none','-monitor','none','-serial',f'file:{out}/serial.log','-no-reboot',
        '-kernel',vm.KERNEL,'-initrd',archive,'-append','console=ttyAMA0 rdinit=/init panic=1',
        '-drive',f'if=none,id=sentinel,file={disk},format=raw','-device','virtio-blk-device,drive=sentinel']
    publish(out/'command.json',[str(x) for x in command])
    with (out/'qemu.log').open('xb') as log:
        done=subprocess.run([str(x) for x in command],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,
            timeout=90,env=dict(os.environ,LD_LIBRARY_PATH=str(vm.QEMU/'usr/lib/x86_64-linux-gnu')))
    serial=(out/'serial.log').read_bytes();clean=serial.replace(b'\r\n',b'\n')
    after=hashlib.sha256(disk.read_bytes()).hexdigest()
    require(done.returncode==0 and b'reboot: Power down' in clean and before==after,'VM exit/disk invariant differs')
    require(clean.count(b'LC_VM_BEGIN\n')==1 and clean.count(b'LC_VM_EXIT status=0\n')==1,'helper did not settle once')
    lines=[line for line in clean.splitlines() if line.startswith(b'LC1_')]
    stdout=b'\n'.join(lines)+b'\n';(out/'helper.stdout').write_bytes(stdout)
    proof=protocol.decode(stdout,b'',key=verify(built['key'],maximum=32).read_bytes(),
        run=bytes.fromhex(built['run_id_hex']),helper=built['helper']['sha256'])
    stage,attempts=EXPECTED[name]
    require(proof['live_pair_proved']==(name=='normal') and proof['measurements']['stage']==stage and
        proof['measurements']['attempted']==proof['measurements']['returned']==attempts,
        'VM observed stage or module-call accounting differs')
    require((b'LC_VM_ALIAS preserved=sentinel\n' if name=='alias-exists' else b'LC_VM_ALIAS absent=1\n') in clean,
        'helper removed an unowned alias or failed owned cleanup')
    if name=='logger-off':require(b'LC_VM_LOGGER_MODE=off\n' in clean,'VM logging-disable fault is absent')
    value=dict(case=name,status='PASS',scope='ARM64_RING_WITH_BOARD_MODULE_BACKEND_SUBSTITUTIONS_NOT_PHYSICAL_RETENTION',
        helper=built['helper'],run_id_hex=built['run_id_hex'],proof=proof,serial=pin(out/'serial.log'),
        stdout=pin(out/'helper.stdout'),initramfs=pin(archive),disk_before=before,disk_after=after,
        disk_unchanged=True,device_actions=0)
    publish(out/'result.json',value);print(name,'PASS',flush=True);return value


def suite(out,physical):
    out=private_path(ROOT,out,exists=False);require(not out.exists(),'fresh logger VM suite required');out.mkdir(mode=0o700)
    physical=private_path(ROOT,physical);p=read(physical/'result.json');key=verify(p['key'],maximum=32).read_bytes()
    producer.audit(physical,p['run_id_hex'],key)
    executable=out/'qemu-system-aarch64'
    shutil.copyfile(vm.QEMU/'usr/bin/qemu-system-aarch64',executable);executable.chmod(0o500)
    source=pin(Path(__file__));tools=dict(kernel=pin(vm.KERNEL,maximum=128*1024**2),
        qemu=pin(executable,maximum=128*1024**2))
    built=producer.build(out/'helper',p['run_id_hex'],key,virt=True)
    values=[case(out/name,built,name) for name in CASES]
    require(pin(Path(__file__))==source,'VM source changed')
    result=dict(schema='s22plus-native-log-vm-h0-v1',status='PASS',physical_build=pin(physical/'result.json'),
        virtual_build=pin(out/'helper/result.json'),source=source,tools=tools,cases=values,device_actions=0)
    return publish(out/'result.json',result)

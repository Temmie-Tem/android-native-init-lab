"""Real ARM64, mountless reads of writable private regular-file disk fixtures."""
import argparse
import gzip
import json
import os
from pathlib import Path
import re
import shutil
import stat
import struct
import s22plus_native_root_inspect_vm_h0 as vm
import s22plus_debian_handoff_vm_h0 as handoff
import s22plus_native_evidence_profile_v1 as profile
from s22plus_native_records_v3 import pin,private_path,publish,read,require,verify

ROOT=vm.ROOT
SEED=ROOT/'workspace/private/outputs/s22plus-debian-handoff-p414-h0-20261003-1/vm-positive/native-after.ext4'
CASES=('clean','dirty','journal-only','missing','symlink','hardlink','oversize','directory-checksum','inode-checksum','group-descriptor-checksum','wrong-uuid','gpt-byte')


def setup(out,helper,case):
    out=private_path(ROOT,out,exists=False);helper=private_path(ROOT,helper)
    require(not out.exists() and case in CASES,'fresh selected evidence fixture required')
    built=read(helper/'result.json');require(built['virt'] is True,'VM helper lacks virtual discovery')
    out.mkdir(mode=0o700,parents=True);native=out/'native.ext4'
    vm.run(['cp','--reflink=auto','--sparse=always',SEED,native],out,'copy-root')
    if case in ('missing','symlink','hardlink'):
        vm.debug(native,out,'remove-count','rm /var/lib/lab/boot-count')
        if case=='symlink':vm.debug(native,out,'symlink','symlink /var/lib/lab/boot-count /etc/shadow')
        if case=='hardlink':
            vm.debug(native,out,'hardlink','ln /var/log/wtmp /var/lib/lab/boot-count')
            vm.debug(native,out,'hardlink-count','set_inode_field /var/lib/lab/boot-count links_count 2')
    if case=='oversize':vm.debug(native,out,'oversize','set_inode_field /var/lib/lab/boot-count size 33')
    if case in ('dirty','wrong-uuid'):
        with native.open('r+b') as f:
            f.seek(1024);block=bytearray(f.read(1024))
            if case=='dirty':block[0x60]|=4
            else:block[0x68]^=1
            struct.pack_into('<I',block,0x3fc,vm.fs.crc32c(block[:0x3fc]))
            f.seek(1024);f.write(block);f.flush();os.fsync(f.fileno())
    if case in ('inode-checksum','journal-only'):
        where=vm.run(['/usr/sbin/debugfs','-R','imap /var/lib/lab/boot-count',native],out,'inode-map')
        found=re.search(rb'located at block ([0-9]+), offset 0x([0-9a-f]+)',where)
        require(found is not None,'fixture inode location absent')
        inode_block=int(found[1]);inode_offset=int(found[2],16)
        if case=='inode-checksum':
            with native.open('r+b') as f:
                f.seek(inode_block*4096+inode_offset+124);byte=f.read(1);f.seek(-1,1);f.write(bytes([byte[0]^1]))
        else:
            # Produce a valid alternate inode checksum on a separate file,
            # then place that inode block only in a committed JBD2 transaction.
            shadow=out/'journal-state.ext4'
            vm.run(['cp','--reflink=auto','--sparse=always',native,shadow],out,'copy-journal-state')
            vm.debug(shadow,out,'journal-size','set_inode_field /var/lib/lab/boot-count size 3')
            with shadow.open('rb') as f:f.seek(inode_block*4096);data=f.read(4096)
            require(len(data)==4096,'short journal fixture block')
            payload=out/'journal-inode.bin';payload.write_bytes(data)
            commands=out/'journal.commands';commands.write_text(
                f'journal_open -c -v 3\njournal_write -b {inode_block} {payload}\njournal_close\n')
            vm.run(['/usr/sbin/debugfs','-w','-f',commands,native],out,'journal-producer')
            publish(out/'journal-only.json',dict(checkpointed_boot_count_size=2,committed_inode_size=3,
                inode_block=inode_block,payload=pin(payload),commands=pin(commands),replayed=False))
    if case=='group-descriptor-checksum':
        with native.open('r+b') as f:
            f.seek(4096+30);byte=f.read(1);f.seek(-1,1);f.write(bytes([byte[0]^1]))
    if case=='directory-checksum':
        blocks=vm.run(['/usr/sbin/debugfs','-R','blocks /var/lib/lab',native],out,'directory-blocks').split()
        require(blocks and all(n.isdigit() for n in blocks),'fixture directory blocks invalid')
        with native.open('r+b') as f:
            f.seek(int(blocks[0])*4096+4095);byte=f.read(1);f.seek(-1,1);f.write(bytes([byte[0]^1]))
    binding=read(verify(profile.inspection.filesystem.BINDING));vm.make_disk(native,out/'disk.img',binding)
    if case=='gpt-byte':
        with (out/'disk.img').open('r+b') as f:
            f.seek(400);byte=f.read(1);f.seek(-1,1);f.write(bytes([byte[0]^1]))
    artifact,_,_=profile.inspection.prior_inputs();busybox=Path(artifact['rootfs']['path']).parent/'busybox'
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
printf 'NE_VM_BEGIN\\n'
/s22-root-evidence evidence {built['run_id_hex']}
result=$?
printf 'NE_VM_EXIT status=%s\\n' "$result"
printf 'NE_VM_RO partition=%s disk=%s userdata=%s\\n' "$(cat /sys/class/block/vda41/ro)" "$(cat /sys/class/block/vda/ro)" "$(cat /sys/class/block/vda40/ro)"
poweroff -f
'''.encode()
    entries=[(n,stat.S_IFDIR|0o755,b'') for n in ('bin','dev','proc','sys','s22-root-work')]
    entries += [('init',stat.S_IFREG|0o750,init),('bin/busybox',stat.S_IFREG|0o755,busybox.read_bytes()),
        ('s22-root-evidence',stat.S_IFREG|0o500,verify(built['helper']).read_bytes()),
        ('s22-root-inspect.table',stat.S_IFREG|0o400,verify(built['table']).read_bytes())]
    (out/'initramfs.cpio.gz').write_bytes(gzip.compress(vm.h0.newc(entries),mtime=0))
    qemu=out/'qemu-system-aarch64';shutil.copyfile(vm.QEMU/'usr/bin/qemu-system-aarch64',qemu);qemu.chmod(0o500)
    return publish(out/'setup.json',dict(schema='s22plus-native-evidence-vm-h0-v1',case=case,
        helper=pin(helper/'result.json'),kernel=pin(handoff.base.KERNEL,maximum=128*1024*1024),
        qemu=pin(qemu,maximum=128*1024*1024),initramfs=pin(out/'initramfs.cpio.gz',maximum=16*1024*1024),
        source=pin(Path(__file__)),device_actions=0))


def run(out):
    setup=read(out/'setup.json');built=read(verify(setup['helper']));case=setup['case']
    before=vm.fixture_tools.sparse_digest(out/'disk.img')
    publish(out/'disk-before.json',dict(digest=before,device_actions=0))
    command=[verify(setup['qemu'],maximum=128*1024*1024),'-machine','virt','-cpu','cortex-a76','-smp','2','-m','768',
        '-nic','none','-nographic','-monitor','none','-no-reboot',
        '-kernel',verify(setup['kernel'],maximum=128*1024*1024),
        '-initrd',verify(setup['initramfs'],maximum=16*1024*1024),'-append','console=ttyAMA0 rdinit=/init panic=-1',
        '-drive',f'if=none,id=root,file={out}/disk.img,format=raw',
        '-device','virtio-blk-device,drive=root,logical_block_size=4096,physical_block_size=4096']
    (out/'command.json').write_text(json.dumps(list(map(str,command)))+'\n')
    raw=vm.run(command,out,'serial',env=dict(os.environ,LD_LIBRARY_PATH=str(vm.QEMU/'usr/lib/x86_64-linux-gnu')),timeout=120)
    after=vm.fixture_tools.sparse_digest(out/'disk.img');require(before==after,'mountless reader changed writable disk fixture')
    text=raw.replace(b'\r\n',b'\n')
    require(text.count(b'NE_VM_BEGIN\n')==1 and b'reboot: Power down' in text,'VM completion missing')
    ro=b'0' if case=='gpt-byte' else b'1'
    require(b'NE_VM_RO partition='+ro+b' disk=0 userdata=0\n' in text,'partition-only protection differs')
    stdout=b'\n'.join(line for line in text.splitlines() if line.startswith((b'RI1_',b'UP1_',b'NE1_')))+b'\n'
    (out/'owner.stdout').write_bytes(stdout)
    if case in ('gpt-byte','wrong-uuid'):
        require(b'NE_VM_EXIT status=1\n' in text and b'RI1_RESULT complete=0 ' in stdout and
            b'NE1_READ' not in stdout,'wrong target binding reached the file reader')
        proof=dict(status='PASS_REJECTED_BEFORE_FILE_READ')
    else:
        require(b'NE_VM_EXIT status=0\n' in text,'mountless reader failed')
        proof=profile.decode(stdout,b'',built['root_evidence']);first=proof['files'][0]
        expected={'missing':'ABSENT_IN_HOME_VIEW','symlink':'METADATA_REJECTED','hardlink':'METADATA_REJECTED',
            'oversize':'OVERSIZE','directory-checksum':'READ_ERROR','inode-checksum':'READ_ERROR','group-descriptor-checksum':'READ_ERROR'}.get(case,'READ')
        require(first['status']==expected,'fixture file status differs')
        if expected=='READ':require(first['raw_hex']==b'2\n'.hex() and first['size']==2,'reader did not preserve checkpointed count')
        require(proof['source_view_clean']==(case not in ('dirty','journal-only')),'dirty view was relabelled clean')
        require(not proof['mounted'] and not proof['persistent_writes'],'reader gained mutation/mount claim')
    return publish(out/'result.json',dict(schema='s22plus-native-evidence-vm-result-h0-v1',setup=pin(out/'setup.json'),
        proof=proof,disk_before=before,disk_after=after,disk_unchanged=True,raw=pin(out/'serial.stdout'),
        owner=pin(out/'owner.stdout'),scope='REAL_ARM64_VIRT_NOT_SAMSUNG',device_actions=0))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=('setup','run'))
    p.add_argument('--output',type=Path,required=True);p.add_argument('--helper',type=Path);p.add_argument('--case',choices=CASES)
    a=p.parse_args();print((setup(a.output.absolute(),a.helper.absolute(),a.case) if a.command=='setup' else run(a.output.absolute()))['sha256'])

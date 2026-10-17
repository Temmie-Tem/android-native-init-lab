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
CASES=('clean','dirty','journal-only','missing','symlink','hardlink','oversize','directory-checksum','inode-checksum','group-descriptor-checksum','wrong-uuid','gpt-byte','durable')
PAIR_CASES=('pair-maximum','missing-runtime','runtime-oversize','runtime-hardlink')


def setup(out,helper,case,*,seed=None,pair_files=None):
    out=private_path(ROOT,out,exists=False);helper=private_path(ROOT,helper)
    require(not out.exists() and case in CASES+PAIR_CASES,'fresh selected evidence fixture required')
    built=read(helper/'result.json');require(built['virt'] is True,'VM helper lacks virtual discovery')
    pair=built['root_evidence'].get('selection')==profile.AUTOBOOT_PAIR
    require(case not in PAIR_CASES or pair,'pair fixture requires the pair helper')
    require((pair_files is not None)==pair,'pair input selection differs')
    if case=='durable':
        require(seed is not None and built['root_evidence']['record_run'] is not None,'sealed durable fixture absent')
        seed=private_path(ROOT,seed);require(seed.is_file() and not seed.is_symlink(),'not a regular private VM seed')
    else:
        require(seed is None,'custom seed requires durable fixture');seed=SEED
    out.mkdir(mode=0o700,parents=True);native=out/'native.ext4'
    vm.run(['cp','--reflink=auto','--sparse=always',seed,native],out,'copy-root')
    fixed=profile.paths(built['root_evidence']['record_run'],built['root_evidence'].get('selection'))
    selected_path='/'+fixed[0][0];selected_maximum=fixed[0][3]
    pair_inputs=[]
    if pair:
        require(type(pair_files) in (tuple,list) and len(pair_files)==2,'exactly two pair fixtures required')
        for index,(rule,path) in enumerate(zip(fixed,pair_files)):
            source=private_path(ROOT,Path(path));data=source.read_bytes()
            require(source.is_file() and not source.is_symlink() and 0<len(data)<=rule[3],'pair fixture input exceeds bound')
            if case=='pair-maximum':data=bytes([0x41+index])*rule[3]
            fixture=out/f'pair-{index}.bin';fixture.write_bytes(data);pair_inputs.append(pin(fixture))
            name='/'+rule[0]
            vm.debug(native,out,f'write-pair-{index}',f'write {fixture} {name}')
            for field,value in (('mode','0100600'),('uid','0'),('gid','0')):
                vm.debug(native,out,f'pair-{index}-{field}',f'set_inode_field {name} {field} {value}')
    if case in ('missing','symlink','hardlink'):
        vm.debug(native,out,'remove-count','rm '+selected_path)
        if case=='symlink':vm.debug(native,out,'symlink','symlink '+selected_path+' /etc/shadow')
        if case=='hardlink':
            vm.debug(native,out,'hardlink','ln /var/log/wtmp '+selected_path)
            vm.debug(native,out,'hardlink-count','set_inode_field '+selected_path+' links_count 2')
    if case=='oversize':vm.debug(native,out,'oversize',f'set_inode_field {selected_path} size {selected_maximum+1}')
    if case in ('missing-runtime','runtime-hardlink'):
        second='/'+fixed[1][0];vm.debug(native,out,'remove-runtime','rm '+second)
        if case=='runtime-hardlink':
            vm.debug(native,out,'runtime-link',f'ln {selected_path} {second}')
            vm.debug(native,out,'runtime-links',f'set_inode_field {selected_path} links_count 2')
    if case=='runtime-oversize':vm.debug(native,out,'runtime-oversize',f'set_inode_field /{fixed[1][0]} size {fixed[1][3]+1}')
    if case in ('dirty','wrong-uuid'):
        with native.open('r+b') as f:
            f.seek(1024);block=bytearray(f.read(1024))
            if case=='dirty':block[0x60]|=4
            else:block[0x68]^=1
            struct.pack_into('<I',block,0x3fc,vm.fs.crc32c(block[:0x3fc]))
            f.seek(1024);f.write(block);f.flush();os.fsync(f.fileno())
    if case in ('inode-checksum','journal-only'):
        where=vm.run(['/usr/sbin/debugfs','-R','imap '+selected_path,native],out,'inode-map')
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
            home_size=pair_inputs[0]['size'] if pair else 2
            vm.debug(shadow,out,'journal-size',f'set_inode_field {selected_path} size {home_size+1}')
            with shadow.open('rb') as f:f.seek(inode_block*4096);data=f.read(4096)
            require(len(data)==4096,'short journal fixture block')
            payload=out/'journal-inode.bin';payload.write_bytes(data)
            commands=out/'journal.commands';commands.write_text(
                f'journal_open -c -v 3\njournal_write -b {inode_block} {payload}\njournal_close\n')
            vm.run(['/usr/sbin/debugfs','-w','-f',commands,native],out,'journal-producer')
            publish(out/'journal-only.json',dict(checkpointed_boot_count_size=home_size,committed_inode_size=home_size+1,
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
        source=pin(Path(__file__)),pair_inputs=pair_inputs,seed=dict(path=str(seed),size=seed.stat().st_size,
            sparse_digest=vm.fixture_tools.sparse_digest(seed)),device_actions=0))


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
        expected={'missing':'ABSENT_IN_HOME_VIEW','symlink':'METADATA_REJECTED','hardlink':'METADATA_REJECTED','runtime-hardlink':'METADATA_REJECTED',
            'oversize':'OVERSIZE','directory-checksum':'READ_ERROR','inode-checksum':'READ_ERROR','group-descriptor-checksum':'READ_ERROR'}.get(case,'READ')
        require(first['status']==expected,'fixture file status differs')
        if setup.get('pair_inputs'):
            require(len(proof['files'])==2,'pair reader included unrelated files')
            second=proof['files'][1]
            second_expected={'missing-runtime':'ABSENT_IN_HOME_VIEW','runtime-oversize':'OVERSIZE',
                'runtime-hardlink':'METADATA_REJECTED','directory-checksum':'READ_ERROR',
                'group-descriptor-checksum':'READ_ERROR'}.get(case,'READ')
            require(second['status']==second_expected,'second file status differs')
            for row,receipt in zip(proof['files'],setup['pair_inputs']):
                if row['status']=='READ':
                    require(bytes.fromhex(row['raw_hex'])==verify(receipt).read_bytes() and row['size']==receipt['size'],
                        'pair bytes differ from checkpointed fixture')
            require(len(stdout)<=profile.MAXIMUM,'pair outer output exceeds unchanged cap')
            if case=='pair-maximum':
                require(sum(row['captured'] for row in proof['files'])==32000,'pair maximum capture is short')
        elif expected=='READ':require(first['raw_hex']==(b'1\n' if case=='durable' else b'2\n').hex() and
            first['size']==2,'reader did not preserve checkpointed count')
        if case=='durable':
            last=proof['files'][-1]
            require(last['path']=='var/lib/lab/s22-evidence-'+built['root_evidence']['record_run'] and
                last['status']=='READ' and len(bytes.fromhex(last['raw_hex']))==last['size'],
                'sealed durable file was not fully read')
        require(proof['source_view_clean']==(case not in ('dirty','journal-only')),'dirty view was relabelled clean')
        require(not proof['mounted'] and not proof['persistent_writes'],'reader gained mutation/mount claim')
    return publish(out/'result.json',dict(schema='s22plus-native-evidence-vm-result-h0-v1',setup=pin(out/'setup.json'),
        proof=proof,disk_before=before,disk_after=after,disk_unchanged=True,raw=pin(out/'serial.stdout'),
        owner=pin(out/'owner.stdout'),scope='REAL_ARM64_VIRT_NOT_SAMSUNG',device_actions=0))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=('setup','run'))
    p.add_argument('--output',type=Path,required=True);p.add_argument('--helper',type=Path);p.add_argument('--case',choices=CASES+PAIR_CASES)
    p.add_argument('--pair-early',type=Path);p.add_argument('--pair-runtime',type=Path)
    a=p.parse_args();require((a.pair_early is None)==(a.pair_runtime is None),'both pair inputs are required')
    pair_files=(a.pair_early,a.pair_runtime) if a.pair_early is not None else None
    print((setup(a.output.absolute(),a.helper.absolute(),a.case,pair_files=pair_files) if a.command=='setup' else run(a.output.absolute()))['sha256'])

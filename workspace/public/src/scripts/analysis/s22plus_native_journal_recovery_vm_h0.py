"""Real ARM64 block-device replay and protected admission on private VM disks."""
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
import s22plus_debian_handoff_vm_h0 as previous
import s22plus_native_journal_recovery_profile_v1 as profile
from s22plus_native_records_v3 import pin,private_path,publish,read,require,verify

ROOT=vm.ROOT
SEED=ROOT/'workspace/private/outputs/s22plus-debian-handoff-p411-h0-20261001-1/vm-final-positive-2/native.ext4'
CASES=('replay','clean','orphan-before','orphan-replayed','journal-corrupt','checker-reject')
HISTORY_CASES=('history-missing','history-changed','history-linked','history-mode','history-runtime',
    'history-count-invalid','history-count-maximum')


def setup(out,helper,case,*,binary=None,supervisor=None,fault=None):
    out=private_path(ROOT,out,exists=False);helper=private_path(ROOT,helper)
    require(not out.exists() and case in CASES+HISTORY_CASES,'fresh declared replay VM required')
    built=read(helper/'result.json');require(built['virt'] is True,'explicit virtual discovery helper required')
    out.mkdir(mode=0o700,parents=True)
    native=out/'native.ext4';vm.run(['cp','--reflink=auto','--sparse=always',SEED,native],out,'copy-root')
    if built['journal_recovery'].get('history_selection') is not None:
        import s22plus_debian_autoboot_profile_v1 as automatic
        for index,item in enumerate(automatic.histories(True)):
            if case=='history-missing' and index==1:continue
            body=verify(item['source']).read_bytes()
            if case=='history-changed' and index==1:body=body[:-1]+bytes([body[-1]^1])
            file=out/f'history-{index}.bin';file.write_bytes(body)
            vm.debug(native,out,f'history-write-{index}',f'write {file} /{item["path"]}')
            vm.debug(native,out,f'history-mode-{index}',f'set_inode_field /{item["path"]} mode 0100600')
            if index==1 and case in ('history-linked','history-mode'):
                if case=='history-linked':
                    vm.debug(native,out,'history-alias',f'ln /{item["path"]} /var/lib/lab/unqualified-history-alias')
                field='links_count 2' if case=='history-linked' else 'mode 0100644'
                vm.debug(native,out,'bad-history-metadata',f'set_inode_field /{item["path"]} {field}')
        if case=='history-runtime':
            (out/'runtime.bin').write_bytes(b'NOT_ADMITTED\n')
            path='/var/lib/lab/s22-evidence-'+automatic.additional_history()['path'].rsplit('-',1)[1]
            vm.debug(native,out,'runtime-write',f'write {out}/runtime.bin {path}')
            vm.debug(native,out,'runtime-mode',f'set_inode_field {path} mode 0100600')
        if case in ('history-count-invalid','history-count-maximum'):
            (out/'count.bin').write_bytes(b'01\n' if case=='history-count-invalid' else b'99999\n')
            vm.debug(native,out,'count-remove','rm /var/lib/lab/boot-count')
            vm.debug(native,out,'count-write',f'write {out}/count.bin /var/lib/lab/boot-count')
            vm.debug(native,out,'count-mode','set_inode_field /var/lib/lab/boot-count mode 0100644')
    else:require(case not in HISTORY_CASES,'history case requires the selected comparison')
    if case!='clean':
        if case=='orphan-replayed':
            with native.open('rb') as f:data=bytearray(f.read(4096))
            struct.pack_into('<I',data,1024+0xe8,12)
            struct.pack_into('<I',data,1024+0x60,vm.fs.INCOMPAT|4)
            struct.pack_into('<I',data,1024+0x3fc,vm.fs.crc32c(data[1024:1024+0x3fc]))
            (out/'data.bin').write_bytes(data)
            commands=f'journal_open -c -v 3\njournal_write -b 0 {out}/data.bin\njournal_close\n'
        else:
            (out/'data.bin').write_bytes(b'A'*4096+b'B'*4096);(out/'tail.bin').write_bytes(b'C'*4096)
            commands=f'journal_open -c -v 3\njournal_write -b 40000000,40000001 {out}/data.bin\njournal_write -r 40000001\njournal_write -c -b 40000002 {out}/tail.bin\njournal_close\n'
        (out/'journal.commands').write_text(commands)
        vm.run(['/usr/sbin/debugfs','-w','-f',out/'journal.commands',native],out,'journal-producer')
    if case=='orphan-before':vm.debug(native,out,'orphan','ssv last_orphan 12')
    if case=='journal-corrupt':
        block=int(vm.run(['/usr/sbin/debugfs','-R','bmap <8> 0',native],out,'journal-block').strip())
        with native.open('r+b') as f:f.seek(block*4096);f.write(bytes(4))
    if case=='checker-reject':
        blocks=vm.run(['/usr/sbin/debugfs','-R','blocks /etc',native],out,'etc-blocks').split()
        require(blocks and all(n.isdigit() for n in blocks),'fixture directory blocks invalid')
        with native.open('r+b') as f:
            f.seek(int(blocks[0])*4096+4095);byte=f.read(1);f.seek(-1,1);f.write(bytes([byte[0]^1]))
    binding=read(verify(profile.inspection.filesystem.BINDING));vm.make_disk(native,out/'disk.img',binding)
    artifact,_,_=profile.prior_inputs();busybox=Path(artifact['rootfs']['path']).parent/'busybox'
    invocation=f'/s22-journal-recovery recover-journal {built["run_id_hex"]}'
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
printf 'JR_VM_BEGIN\\n'
{invocation}
result=$?
printf 'JR_VM_EXIT status=%s\\n' "$result"
printf 'JR_VM_RO partition=%s disk=%s userdata=%s\\n' "$(cat /sys/class/block/vda41/ro)" "$(cat /sys/class/block/vda/ro)" "$(cat /sys/class/block/vda40/ro)"
poweroff -f
'''.encode()
    entries=[(n,stat.S_IFDIR|0o755,b'') for n in ('bin','dev','proc','sys','s22-root-work')]
    entries += [('init',stat.S_IFREG|0o750,init),('bin/busybox',stat.S_IFREG|0o755,busybox.read_bytes()),
        ('s22-journal-recovery',stat.S_IFREG|0o500,(Path(binary) if binary else verify(built['helper'])).read_bytes()),
        ('s22-root-inspect.table',stat.S_IFREG|0o400,verify(built['table']).read_bytes()),
        ('s22-journal-replay',stat.S_IFREG|0o500,verify(built['journal_recovery']['replayer']).read_bytes()),
        ('s22-fs-e2fsck',stat.S_IFREG|0o500,verify(built['journal_recovery']['checker']).read_bytes())]
    if supervisor:entries.append(('supervisor',stat.S_IFREG|0o500,Path(supervisor).read_bytes()))
    (out/'initramfs.cpio.gz').write_bytes(gzip.compress(vm.h0.newc(entries),mtime=0))
    qemu=out/'qemu-system-aarch64';shutil.copyfile(vm.QEMU/'usr/bin/qemu-system-aarch64',qemu);qemu.chmod(0o500)
    return publish(out/'setup.json',dict(schema='s22plus-journal-recovery-vm-h0-v1',case=case,
        helper=pin(helper/'result.json'),kernel=pin(previous.base.KERNEL,maximum=128*1024*1024),
        qemu=pin(qemu,maximum=128*1024*1024),initramfs=pin(out/'initramfs.cpio.gz',maximum=16*1024*1024),
        source=pin(Path(__file__)),fault=fault,
        supervisor=pin(supervisor) if supervisor else None,
        fault_helper=pin(binary) if binary else None,device_actions=0))


def run(out):
    out=private_path(ROOT,out);setup=read(out/'setup.json');built=read(verify(setup['helper']));case=setup['case']
    before=vm.fixture_tools.sparse_digest(out/'disk.img');outside=previous.outside_native(out/'disk.img')
    publish(out/'disk-before.json',dict(digest=before,outside=outside,device_actions=0))
    command=[verify(setup['qemu'],maximum=128*1024*1024),'-machine','virt','-cpu','cortex-a76','-smp','2','-m','1024',
        '-nic','none','-nographic','-monitor','none','-no-reboot',
        '-kernel',verify(setup['kernel'],maximum=128*1024*1024),
        '-initrd',verify(setup['initramfs'],maximum=16*1024*1024),'-append','console=ttyAMA0 rdinit=/init panic=-1',
        '-drive',f'if=none,id=root,file={out}/disk.img,format=raw',
        '-device','virtio-blk-device,drive=root,logical_block_size=4096,physical_block_size=4096']
    (out/'command.json').write_text(json.dumps(list(map(str,command)))+'\n')
    raw=vm.run(command,out,'serial',env=dict(os.environ,LD_LIBRARY_PATH=str(vm.QEMU/'usr/lib/x86_64-linux-gnu')),timeout=300)
    after=vm.fixture_tools.sparse_digest(out/'disk.img');outside_after=previous.outside_native(out/'disk.img')
    require(outside==outside_after,'replay modified outside native_data')
    text=raw.replace(b'\r\n',b'\n')
    rejected_admission=case in ('history-missing','history-count-invalid','history-linked')
    require(text.count(b'JR_VM_BEGIN\n')==1 and b'reboot: Power down' in text and
        (b'JR_VM_EXIT status=1\n' if rejected_admission else b'JR_VM_EXIT status=0\n') in text,
        'VM settlement, return or partition-only RO differs')
    stdout=b'\n'.join(line for line in text.splitlines() if line.startswith((b'RI1_',b'UP1_',b'JR1_')))+b'\n'
    (out/'owner.stdout').write_bytes(stdout)
    binding=dict(table_count=built['table_count'],boot_count=built['boot_count'],max_hashed_bytes=512*1024*1024)
    if setup['fault']:
        require(re.search(rb'JR_VM_SCOPE settled=1 status=[1-9][0-9]* adopted=[0-9]+\n',text) and
            b'RI1_RESULT complete=0 ' in stdout,'fault lost failed-helper or settled-group evidence')
        try:profile.decode(stdout,b'',binding)
        except ValueError:pass
        else:raise ValueError('fault was promoted to completed recovery')
        require(re.search(rb'JR_VM_RO partition=[01] disk=0 userdata=0\n',text),'fault changed unrelated RO control')
        if setup['fault']['kind']==1:require(before==after,'pre-exec writer fault changed disk')
        proof=dict(status='NO_PROOF',fault=setup['fault'],outer_group_settled=True)
    elif rejected_admission:
        # The unchanged owner reports an admission error as incomplete. Its
        # live consumer must retain NO_PROOF and choose physical recovery.
        require(b'JR_VM_RO partition=1 disk=0 userdata=0\n' in text and
            b'RI1_RESULT complete=0 stage=8 errno=71 cleanup_errno=0 partition_ro=1 clean=1 mounted=1 unmounted=1\n' in stdout and
            stdout.endswith(b'JR1_RESULT complete=0 attempted=1 writer_complete=1 checker_complete=1 root_match=0 stopped=0 io_error=0\n'),
            'negative comparison lost its actual rejection or cleanup')
        lines=stdout.decode('ascii').splitlines();at=lines.index('JR1_BLOCK_RW partition=1')
        writer=profile._writer(lines[at+1:at+5]);at=lines.index('JR1_CHECKER begin=1')
        checker=profile.staged._child('checker',lines[at+1:at+5])
        require(writer['complete']==1 and checker['proved']==1,'negative comparison lacks settled writer/checker')
        try:profile.decode(stdout,b'',binding)
        except ValueError:pass
        else:raise ValueError('incomplete admission was promoted to completed recovery')
        proof=dict(status='NO_PROOF',recovery_proved=False,writer=writer,checker=checker,
            admission_rejected=True,protected_cleanup_observed=True)
    else:
        require(b'JR_VM_RO partition=1 disk=0 userdata=0\n' in text,'partition RO restore absent')
        proof=profile.decode(stdout,b'',binding)
        require(proof['recovery_proved']==(case in ('replay','clean','history-count-maximum')),'replay VM result differs')
        if case in HISTORY_CASES:
            require(proof['writer']['complete']==1 and proof['checker']['proved']==1,
                'history comparison did not follow completed replay and separate checker')
    if case in ('clean','orphan-before','journal-corrupt'):require(before==after,'rejected/skipped fixture was changed')
    if case=='replay' and not setup['fault']:
        with (out/'disk.img').open('rb') as f:
            for n,expected in ((40000000,b'A'*4096),(40000001,bytes(4096)),(40000002,bytes(4096))):
                f.seek(vm.fs.FIRST_LBA*4096+n*4096);require(f.read(4096)==expected,'kernel replay/revoke/tail differs')
    return publish(out/'result.json',dict(schema='s22plus-journal-recovery-vm-result-h0-v1',setup=pin(out/'setup.json'),
        proof=proof,disk_before=before,disk_after=after,outside_before=outside,outside_after=outside_after,
        raw=pin(out/'serial.stdout'),owner=pin(out/'owner.stdout'),scope='REAL_ARM64_VIRT_NOT_SAMSUNG',device_actions=0))


def fault_case(out,helper,*,kind,mode):
    import s22plus_native_userspace_probe_vm_h0 as child
    require(kind in (1,2) and mode in range(1,8),'unknown child fault')
    out=out.absolute();helper=helper.absolute();build=out.with_name(out.name+'-build')
    require(not build.exists(),'fresh fault build required');build.mkdir(mode=0o700)
    header=('/* H0 only: no physical discovery build can include this. */\n'
        'static const char up_fault_script[]="";\n'
        'static const int up_fault_early_zero=0,up_fault_setup_error=0,up_fault_orphan=0;\n'+
        f'static const unsigned rj_fault_kind={kind},rj_fault_mode={mode};\n'+
        '#define up_fault_timeout_ms (rj_kind==rj_fault_kind ? 2000U : 150000U)\n')
    (build/'s22plus_native_userspace_probe_fault_v1.h').write_text(header)
    vm.run(['aarch64-linux-gnu-gcc','-std=c11','-static','-Os','-fno-ident','-ffunction-sections',
        '-fdata-sections','-Wl,--gc-sections','-Wall','-Wextra','-Werror','-Wno-unused-function',
        '-Wno-unused-const-variable','-DS22_ROOT_INSPECT_VIRT_TEST','-DS22_JOURNAL_RECOVERY_FAULT',
        '-I',build,'-I',helper,'-I',vm.producer.NATIVE,
        vm.producer.NATIVE/'s22plus_native_journal_recovery_v1.c','-o',build/'helper'],build,'compile')
    text=child.SUPERVISOR.replace('/s22-userspace-probe','/s22-journal-recovery').replace('"probe",argv[1]','"recover-journal",argv[1]').replace('UP_VM_SCOPE','JR_VM_SCOPE')
    (build/'supervisor.c').write_text(text)
    vm.run(['aarch64-linux-gnu-gcc','-std=c11','-static','-Os','-Wall','-Wextra','-Werror',
        build/'supervisor.c','-o',build/'supervisor'],build,'supervisor-compile')
    setup(out,helper,'replay',binary=build/'helper',supervisor=build/'supervisor',fault=dict(kind=kind,mode=mode))
    return run(out)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=('setup','run'))
    p.add_argument('--output',type=Path,required=True);p.add_argument('--helper',type=Path);p.add_argument('--case',choices=CASES)
    a=p.parse_args();print(setup(a.output,a.helper,a.case) if a.command=='setup' else run(a.output))

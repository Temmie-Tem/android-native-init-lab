#!/usr/bin/env python3
"""H0 derivative of packaged Debian /init, over writable regular-file disks.

Only board guard, finit_module/sys-module presence, and UFS sysfs discovery are
substituted. Module files/hashes/order, GPT, superblock, BLKROSET/GET, and RAM
records run as real ARM64 code. Terminal export/poweroff is VM-only harness.
"""
import argparse
from dataclasses import replace
import gzip
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys

import fyg8
import h0
import s22plus_native_root_inspect_vm_h0 as fixture
import s22plus_native_staged_preflight_vm_h0 as previous

KERNEL=h0.PRIVATE/'outputs/s22plus-switch-root-h0-20260930-1/kernel-build/arch/arm64/boot/Image'
# The physical FYG8 kernel passes these operands to /init. Force them past
# the generic VM kernel's own bootconfig handling with the argument separator.
KERNEL_COMMAND_LINE='console=ttyAMA0 rdinit=/init panic=1 -- bootconfig nohyp_uart'
CASES=('clean','dirty','wrong-uuid','gpt-byte','module-byte','module-symlink',
       'insert-error','existing','ro-error','existing-record','no-console')


def newc(entries):
    result=bytearray()
    for e in entries:
        name=e.name.encode()+b'\0'
        fields=[e.inode,e.mode,e.uid,e.gid,e.nlink,e.mtime,len(e.data),0,0,0,0,len(name),0]
        result.extend(b'070701'+''.join(f'{v:08x}' for v in fields).encode()+name)
        result.extend(b'\0'*(-len(result)%4));result.extend(e.data);result.extend(b'\0'*(-len(result)%4))
    name=b'TRAILER!!!\0';fields=[0,0,0,0,1,0,0,0,0,0,0,len(name),0]
    result.extend(b'070701'+''.join(f'{v:08x}' for v in fields).encode()+name)
    result.extend(b'\0'*(-len(result)%4))
    return bytes(result)


def derivative(build,helper,case,out):
    entries=list(fyg8.debian_entries(build/'initramfs-a.cpio.gz'))
    source=(h0.HERE/'fyg8-dev').read_text()
    h0.require(source.endswith('fyg8_stop\n'),'terminal hook changed')
    terminal='''printf 'FYG8_VM_EXIT status=%s\\n' "$fyg8_status"
cat /run/initramfs/fyg8-events
printf 'FYG8_VM_RO native=%s disk=%s userdata=%s\\n' "$(cat /sys/class/block/vda41/ro)" "$(cat /sys/class/block/vda/ro)" "$(cat /sys/class/block/vda40/ro)"
[ ! -e /dev/.s22-ext4-v1 ] && printf 'FYG8_VM_ALIASES_REMOVED\\n'
printf 'FYG8_VM_MOUNTS_BEGIN\\n'
cat /proc/self/mountinfo
printf 'FYG8_VM_MOUNTS_END\\n'
poweroff -f
'''
    if case=='no-console':
        terminal='''mknod -m 600 /dev/vm-console c 5 1
exec </dev/vm-console >/dev/vm-console 2>&1
'''+terminal
    script=source[:-len('fyg8_stop\n')]+terminal
    if case=='no-console':
        script=script.replace('mknod -m 600 /dev/console c 5 1','mknod -m 600 /dev/console c 5 127')
    if case=='existing-record':
        script=script.replace('/sbin/fyg8-prepare\n',"printf 'SENTINEL\\n' >/run/initramfs/fyg8-events\n/sbin/fyg8-prepare\n")
    module='lab/modules/'+fyg8.verify_inventory(INPUTS)['modules'][0]['name']
    for i,e in enumerate(entries):
        if e.name=='usr/sbin/fyg8-prepare':entries[i]=replace(e,data=(helper/'fyg8-prepare').read_bytes())
        elif e.name=='scripts/fyg8-dev':
            h0.require(e.data==source.encode(),'packaged dev hook differs from test source')
            entries[i]=replace(e,data=script.encode())
        elif e.name==module and case=='module-byte':entries[i]=replace(e,data=bytes([e.data[0]^1])+e.data[1:])
        elif e.name==module and case=='module-symlink':entries[i]=replace(e,mode=stat.S_IFLNK|0o777,data=b'/dev/null')
    fault=case if case in ('insert-error','existing','ro-error','no-console') else 'none'
    e=entries[0]
    entries.append(replace(e,name='lab/fault',encoded_name='lab/fault',inode=max(x.inode for x in entries)+1,
        mode=stat.S_IFREG|0o400,nlink=1,data=(fault+'\n').encode()))
    raw=newc(entries)
    h0.require(len(fyg8.boot.parse_newc(raw))==len(entries),'VM derivative archive malformed')
    (out/'initramfs.cpio.gz').write_bytes(gzip.compress(raw,mtime=0))


def check(out,build,helper,case,binding):
    out.mkdir(mode=0o700)
    native=out/'native.ext4';disk=out/'disk.img'
    h0.run(['cp','--reflink=auto','--sparse=always',h0.regular(previous.BASE/'complete.ext4'),native],out/'copy.log')
    if case=='dirty':
        with native.open('rb') as stream:
            stream.seek(1024+0x60);features=int.from_bytes(stream.read(4),'little')
        fixture.debug(native,out,'dirty',f'ssv feature_incompat {features|4}')
    if case=='wrong-uuid':fixture.debug(native,out,'wrong-uuid','ssv uuid 01234567-1234-1234-1234-0123456789ab')
    fixture.make_disk(native,disk,binding)
    if case=='gpt-byte':
        with disk.open('r+b') as stream:
            # PMBR boot-code byte: leaves kernel partition discovery valid,
            # but must fail the exact sealed metadata comparison before RO.
            stream.seek(100);byte=stream.read(1);stream.seek(-1,1);stream.write(bytes([byte[0]^1]))
    derivative(build,helper,case,out)
    before=fixture.fixture_tools.sparse_digest(disk)
    h0.publish(out/'disk-before.json',before)
    command=[fixture.QEMU/'usr/bin/qemu-system-aarch64','-machine','virt','-cpu','cortex-a76','-smp','2','-m','512',
        '-nic','none','-display','none','-monitor','none','-serial','stdio','-no-reboot','-kernel',h0.regular(KERNEL),
        '-initrd',out/'initramfs.cpio.gz','-append',KERNEL_COMMAND_LINE,
        '-drive',f'if=none,id=root,file={disk},format=raw',
        '-device','virtio-blk-device,drive=root,logical_block_size=4096,physical_block_size=4096']
    h0.publish(out/'command.json',[str(x) for x in command])
    h0.run(command,out/'serial.log',env=dict(os.environ,LD_LIBRARY_PATH=str(fixture.QEMU/'usr/lib/x86_64-linux-gnu')),timeout=90)
    raw=(out/'serial.log').read_bytes().replace(b'\r',b'')
    after=fixture.fixture_tools.sparse_digest(disk)
    h0.require(before==after,'writable backing disk changed')
    h0.require((b'VM_PID1_NULL_FDS descriptors=3' in raw if case=='no-console' else
        b'FYG8_DEBIAN_PID1 pid=1 ' in raw) and b'reboot: Power down' in raw,'VM semantic lifetime incomplete')
    statuses=re.findall(rb'^FYG8_VM_EXIT status=(\d+)$',raw,re.M)
    wanted=0 if case in ('clean','no-console') else 2 if case=='dirty' else 102 if case=='existing-record' else 1
    h0.require(statuses==[str(wanted).encode()],'wrong helper exit semantics: '+case)
    records=re.findall(rb'^FYG8_H0 seq=(\d+) (.+)$',raw,re.M)
    h0.require([int(n) for n,_ in records]==list(range(1,len(records)+1)),'partial/duplicate RAM records')
    begins=sum(b'MODULE_BEGIN ' in row for _,row in records)
    done=sum(b'MODULE_DONE ' in row for _,row in records)
    count=len(fyg8.verify_inventory(INPUTS)['modules'])
    wanted_begin=0 if case in ('module-byte','module-symlink','existing-record') else 1 if case in ('insert-error','existing') else count
    h0.require(begins==wanted_begin and done==(0 if begins<=1 else count),'module retry/order failure')
    for tag,amount in ((b'MODULE_BEGIN',begins),(b'MODULE_DONE',done)):
        actual=[row for _,row in records if row.startswith(tag+b' ')]
        expected=[tag+f" ordinal={m['ordinal']} name={m['runtime_name']}".encode()
            for m in fyg8.verify_inventory(INPUTS)['modules'][:amount]]
        h0.require(actual==expected,'module event order/name differs')
    if case=='gpt-byte':
        h0.require(any(row==b'STORAGE_BOUND' for _,row in records) and
            not any(row==b'RO_BEGIN' for _,row in records),'exact GPT rejection was not exercised')
    terminals=[row for _,row in records if row.startswith(b'TERMINAL ')]
    if case=='existing-record':
        h0.require(not records and b'\nSENTINEL\n' in raw,'existing evidence was overwritten')
    else:
        result=b'METADATA_CLEAN' if case in ('clean','no-console') else b'METADATA_DIRTY' if case=='dirty' else b'REJECTED'
        h0.require(len(terminals)==1 and b'result='+result+b' ' in terminals[0],'wrong terminal classification')
    ro=re.findall(rb'^FYG8_VM_RO native=(\d) disk=(\d) userdata=(\d)$',raw,re.M)
    h0.require(ro==[(b'1' if case in ('clean','dirty','wrong-uuid','no-console') else b'0',b'0',b'0')],'RO scope differs')
    h0.require(b'FYG8_VM_ALIASES_REMOVED' in raw,'owned aliases leaked')
    mounts=raw.split(b'FYG8_VM_MOUNTS_BEGIN\n',1)[1].split(b'FYG8_VM_MOUNTS_END',1)[0]
    h0.require(b' - ext4 ' not in mounts,'unexpected filesystem mount')
    value=dict(case=case,scope='ARM64_VM_WITH_DECLARED_HARDWARE_SUBSTITUTIONS',status='PASS',
        helper_exit=wanted,module_begin=begins,module_done=done,native_ro=ro[0][0].decode(),
        disk_before=before,disk_after=after,sparse_disk_unchanged=True,
        serial_sha256=h0.sha(out/'serial.log'),initramfs_sha256=h0.sha(out/'initramfs.cpio.gz'),device_actions=0)
    h0.publish(out/'result.json',value);print(case,'PASS',flush=True)
    return value


def suite(out,build,inputs,case=None):
    global INPUTS
    INPUTS=h0.private(inputs);out=h0.private(out,fresh=True);build=h0.private(build)
    receipt=json.loads(h0.regular(build/'build.json').read_text())
    h0.require(h0.sha(h0.regular(build/'initramfs-a.cpio.gz'))==receipt['initramfs_sha256'],'build archive changed')
    helper=out/'helper';helper.mkdir()
    fyg8.compile_helper(helper,INPUTS,virt=True)
    sources=fyg8.snapshot(out)
    binding=json.loads(fyg8.verify(receipt['filesystem_binding']).read_text())
    results=[check(out/name,build,helper,name,binding) for name in ((case,) if case else CASES)]
    for source in sources:
        h0.require(h0.sha(h0.ROOT/source['path'])==source['sha256'],'VM source changed during suite')
    h0.publish(out/'result.json',dict(scope='H0 only',device_actions=0,status='PASS',cases=results,
        source_inputs=sources,build_sha256=h0.sha(build/'build.json'),helper_sha256=h0.sha(helper/'fyg8-prepare'),
        kernel_sha256=h0.sha(KERNEL),qemu_sha256=h0.sha(fixture.QEMU/'usr/bin/qemu-system-aarch64')))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('output','build','inputs'):parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--case',choices=CASES)
    args=parser.parse_args();suite(args.output,args.build,args.inputs,args.case)

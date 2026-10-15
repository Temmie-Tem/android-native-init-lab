#!/usr/bin/env python3
"""Actual ARM64 file writer and a later mountless-reader boot, with no USB."""
import argparse
from dataclasses import replace
import gzip
import json
import os
from pathlib import Path
import stat
import sys
import uuid

import file_log as build_api
import fyg8
import fyg8_vm as archive
import h0
import s22plus_native_journal_recovery_vm_h0 as recovery
import s22plus_debian_handoff_vm_h0 as disk_tools
import s22plus_debian_file_protocol_v1 as protocol
from s22plus_native_records_v3 import pin,read,verify

from s22plus_debian_file_profile_v1 import CASES,PARTIAL_WRITES
import s22plus_debian_file_first_profile_v1 as first_profile
import s22plus_debian_file_first_protocol_v1 as first_protocol


def prepare(out,build,case):
    out.mkdir(mode=0o700);built=read(build/'build.json')
    diagnostic=built.get('diagnostic',False)
    first=diagnostic or built['profile']==first_profile.PROFILE
    selection=build_api.prepare(out/'helper',Path(built['inputs']),Path(built['packages']),
        run=built['run_id'],key=(build/'key').read_bytes(),virt=True,
        namespace=built['namespace'],version=built['version'],
        fault=case if case in build_api.file_log_faults.NAMES else None,storage_first=first,diagnostic=diagnostic,
        diagnostic_fault=case if diagnostic and case in __import__('failure_faults').NAMES else None)
    entries=list(fyg8.debian_entries(build/'initramfs-a.cpio.gz'))
    for i,e in enumerate(entries):
        if e.name in ('usr/sbin/fyg8-prepare','usr/sbin/file-log'):
            entries[i]=replace(e,data=(out/'helper'/Path(e.name).name).read_bytes())
        elif e.name=='scripts/fyg8-dev':
            source=e.data.decode()
            stop='''    printf 'FILE_VM_TERMINAL prepare=%s writer=%s\\n' "${fyg8_status:-unset}" "${file_status:-unset}"
    [ ! -e /dev/ttyGS0 ] && [ ! -d /config/usb_gadget ] && printf 'FILE_VM_USB_ABSENT\\n'
    [ -f /run/initramfs/file-admission ] && cat /run/initramfs/file-admission
    printf 'FILE_VM_RO partition=%s disk=%s userdata=%s\\n' "$(cat /sys/class/block/vda41/ro)" "$(cat /sys/class/block/vda/ro)" "$(cat /sys/class/block/vda40/ro)"
    printf 'FILE_VM_MOUNTS_BEGIN\\n'
    cat /proc/self/mountinfo
    printf 'FILE_VM_MOUNTS_END\\n'
    poweroff -f
    while :; do /bin/busybox sleep 3600; done'''
            if diagnostic:stop='''    [ -f /run/initramfs/file-admission ] && /bin/busybox head -c 65536 /run/initramfs/file-admission
    poweroff -f
    while :; do /bin/busybox sleep 3600; done'''
            needle='    while :; do /bin/busybox sleep 3600; done'
            h0.require(source.count(needle)==1,'file stop function differs')
            source=source.replace(needle,stop)
            if case=='ram-log-missing':source=source.replace('umask 077\n','rm /run/initramfs/fyg8-events\numask 077\n')
            entries[i]=replace(e,data=source.encode())
    model=entries[0]
    entries.append(replace(model,name='lab/fault',encoded_name='lab/fault',inode=max(e.inode for e in entries)+1,
        mode=stat.S_IFREG|0o400,nlink=1,data=b'insert-error\n' if case=='insert-error' else b'none\n'))
    if first:
        for name,data in (('lab/integrated-fault',b'none\n'),('lab/client-fault',b'module-error\n' if case=='module-error' else b'none\n')):
            entries.append(replace(model,name=name,encoded_name=name,inode=max(e.inode for e in entries)+1,
                mode=stat.S_IFREG|0o400,nlink=1,data=data))
    vendor=fyg8.memory.vendor
    raw=fyg8.memory.base.stable(h0.ROOT/vendor.DEFAULT_VENDOR_RAMDISK,
        dict(size=vendor.EXPECTED_VENDOR_RAMDISK_SIZE,sha256=vendor.EXPECTED_VENDOR_RAMDISK_SHA256))
    overlay=fyg8.boot.decompress_lz4_stream_python(raw,maximum=128*1024**2)
    (out/'initramfs.cpio.gz').write_bytes(gzip.compress(overlay,compresslevel=1,mtime=0)+
        gzip.compress(archive.newc(entries),compresslevel=1,mtime=0))
    native=out/'native.ext4'
    h0.run(['cp','--reflink=auto','--sparse=always',recovery.SEED,native],out/'copy.log')
    vm=archive.fixture
    if case=='dirty':
        with native.open('rb') as f:f.seek(1024+0x60);features=int.from_bytes(f.read(4),'little')
        vm.debug(native,out,'dirty',f'ssv feature_incompat {features|4}')
    if case=='wrong-uuid':vm.debug(native,out,'wrong-uuid','ssv uuid 01234567-1234-1234-1234-0123456789ab')
    if case=='existing-record':
        (out/'sentinel').write_bytes(b'DO_NOT_OVERWRITE\n')
        name='/var/lib/lab/s22-evidence-'+built['run_id']
        vm.debug(native,out,'existing-record',f'write {out}/sentinel {name}')
        vm.debug(native,out,'existing-mode',f'set_inode_field {name} mode 0100600')
    binding=read(verify(build_api.admission.profile.inspection.filesystem.BINDING))
    vm.make_disk(native,out/'disk.img',binding)
    return selection


def extract_native(out):
    """Only regular VM files; the physical disk is never an input."""
    source=out/'disk.img';destination=out/'native-after.ext4'
    h0.require(source.is_file() and not source.is_symlink(),'VM disk is not a regular file')
    first=archive.fixture.fs.FIRST_LBA*4096;end=first+archive.fixture.fs.SIZE_BYTES
    with source.open('rb',buffering=0) as src,destination.open('xb',buffering=0) as dst:
        dst.truncate(archive.fixture.fs.SIZE_BYTES);position=first
        while position<end:
            try:start=os.lseek(src.fileno(),position,os.SEEK_DATA)
            except OSError as error:
                if error.errno==6:break
                raise
            if start>=end:break
            stop=min(end,os.lseek(src.fileno(),start,os.SEEK_HOLE));src.seek(start);dst.seek(start-first)
            while start<stop:
                data=src.read(min(1024*1024,stop-start));h0.require(data,'short VM extract')
                h0.require(dst.write(data)==len(data),'short VM partition write');start+=len(data)
            position=stop
        dst.flush();os.fsync(dst.fileno())
    return destination


def retrieve(out,selection,build,*,complete=True):
    seed=extract_native(out)
    # A fresh interpreter keeps the native VM's h0 module distinct from this
    # Debian builder's h0. Both producer and consumer are the existing tools.
    code='''from pathlib import Path
import sys
root=Path(sys.argv[1]);out=Path(sys.argv[2]);run=sys.argv[3];record=sys.argv[4]
sys.path[:0]=[str(root/'workspace/public/src/scripts/analysis'),str(root/'workspace/public/src/scripts/revalidation')]
import s22plus_native_evidence_h0 as reader
import s22plus_native_evidence_vm_h0 as vm
reader.build(out/'reader-helper',run,virt=True,record_run=record)
vm.setup(out/'reader-boot',out/'reader-helper','durable',seed=out/'native-after.ext4')
vm.run(out/'reader-boot')
print('PASS: separate ARM64 mountless reader boot')
'''
    reader_run=uuid.uuid4().hex
    h0.run([sys.executable,'-c',code,h0.ROOT,out,reader_run,selection['run_id']],out/'retrieval.log',timeout=300)
    acquired=read(out/'reader-boot/result.json');row=acquired['proof']['files'][-1]
    h0.require(acquired['disk_unchanged'] and acquired['proof']['source_view_clean'] and row['status']=='READ' and
        row['path']=='var/lib/lab/s22-evidence-'+selection['run_id'],'post-boot clean file retrieval differs')
    data=bytes.fromhex(row['raw_hex']);(out/'recovered-record.bin').write_bytes(data)
    arguments=dict(key=(build/'key').read_bytes(),run=bytes.fromhex(selection['run_id']),
        expected=selection['measured'],module_names=[m['runtime_name'] for m in selection['modules']])
    if selection.get('diagnostic'):
        import s22plus_debian_failure_profile_v1 as decoder
    else:decoder=first_protocol if selection['profile']==first_profile.PROFILE else protocol
    if complete:
        proof=decoder.decode(data,**arguments)
        h0.require(proof['pre_unmount_complete'] and proof['debian_early_pid1'] and
            not proof['live_usb_proved'] and not proof['unmount_return_proved'],'file proof meaning differs')
    else:
        try:proof=decoder.decode(data,**arguments,allow_prefix=True)
        except ValueError as error:proof=dict(status='NO_AUTHENTICATED_FILE_PREFIX',error=str(error))
    h0.publish(out/'file-proof.json',proof)
    return dict(proof=proof,retrieval=pin(out/'reader-boot/result.json'),seed=str(seed),reader_run=reader_run)


def run(out,build,case):
    first=read(build/'build.json')['profile']==first_profile.PROFILE
    h0.require(case in (first_profile.CASES if first else CASES),'unknown file VM case')
    selection=prepare(out,build,case);vm=archive.fixture
    before=vm.fixture_tools.sparse_digest(out/'disk.img');outside=disk_tools.outside_native(out/'disk.img')
    h0.publish(out/'disk-before.json',dict(digest=before,outside=outside))
    command=[vm.QEMU/'usr/bin/qemu-system-aarch64','-machine','virt','-cpu','cortex-a76','-smp','2','-m','768',
        '-nic','none','-display','none','-monitor','none','-serial','stdio','-no-reboot','-kernel',archive.KERNEL,
        '-initrd',out/'initramfs.cpio.gz','-append',archive.KERNEL_COMMAND_LINE,
        '-drive',f'if=none,id=root,file={out}/disk.img,format=raw',
        '-device','virtio-blk-device,drive=root,logical_block_size=4096,physical_block_size=4096']
    h0.publish(out/'command.json',list(map(str,command)))
    h0.run(command,out/'serial.log',env=dict(os.environ,LD_LIBRARY_PATH=str(vm.QEMU/'usr/lib/x86_64-linux-gnu')),timeout=360)
    raw=(out/'serial.log').read_bytes().replace(b'\r',b'')
    after=vm.fixture_tools.sparse_digest(out/'disk.img');outside_after=disk_tools.outside_native(out/'disk.img')
    h0.require(outside==outside_after,'file writer modified outside native_data')
    h0.require(raw.count(b'FILE_VM_TERMINAL ')==1 and b'FILE_VM_USB_ABSENT\n' in raw and
        b'reboot: Power down' in raw and b'/s22-root-work/file-root ' not in raw,
        'VM completion, no-USB scope or mount cleanup differs')
    if case=='normal':
        h0.require(b'FILE_VM_TERMINAL prepare=0 writer=0\n' in raw and
            (b'FILE_PILOT result=CLOSED error=0 records=14 ' if first else b'FILE_PILOT result=CLOSED error=0 records=8 ') in raw and
            b'FILE_VM_RO partition=1 disk=0 userdata=0\n' in raw,'file writer did not close cleanly')
        proof=retrieve(out,selection,build)
        if first:h0.require(b'FILE_VM_CLIENTS inserted=6\n' in raw,'normal VM did not perform six calls')
    elif first and case=='module-error':
        h0.require(b'FILE_PILOT result=REJECTED error=5 records=7 ' in raw and
            b'FILE_VM_CLIENTS inserted=2\n' in raw,'failed client was skipped or retried')
        proof=retrieve(out,selection,build,complete=False)
        h0.require(proof['proof']['client_error']==dict(name='i2c_msm_geni',error=5) and
            proof['proof']['client_return_records']==2 and not proof['proof']['pre_unmount_complete'],
            'client failure prefix lost its exact result')
    elif case in (first_profile.PARTIAL_WRITES if first else PARTIAL_WRITES):
        h0.require(b'FILE_VM_TERMINAL prepare=0 writer=1\n' in raw and
            b'FILE_PILOT result=REJECTED ' in raw and b'FILE_PILOT result=CLOSED' not in raw,
            'I/O fault reached successful writer completion')
        recovered=retrieve(out,selection,build,complete=False)
        if first and case!='unmount-error':h0.require(b'FILE_VM_CLIENTS inserted=0\n' in raw,
            'failed BEGIN/header synchronization reached a module call')
        if case=='short-write':h0.require(len(recovered['proof']['records'])==1 and recovered['proof']['tail_error'],
            'short write was retried or torn tail accepted')
        elif case in ('file-sync-error','readback-error'):h0.require(len(recovered['proof']['records'])==2 and
            not recovered['proof']['pre_unmount_complete'],'failed sync advanced later records')
        elif case=='parent-sync-error':h0.require(recovered['proof']['status']=='NO_AUTHENTICATED_FILE_PREFIX',
            'failed parent sync continued writing')
        else:h0.require(recovered['proof']['pre_unmount_complete'] and
            not recovered['proof']['unmount_return_proved'] and
            b'FILE_VM_RO partition=0 disk=0 userdata=0\n' in raw,'failed unmount gained a protection proof')
        proof=dict(recovered,status='PASS_CONSUMED_IO_FAILURE',unmount_proved=False)
    else:
        h0.require(before==after,'rejected pilot changed its disk')
        h0.require(b'FILE_PILOT result=CLOSED' not in raw,'negative VM reached writer success')
        if case=='insert-error':h0.require(b'prepare=1 writer=unset\n' in raw,'failed module reached writer')
        elif case=='ram-log-missing':h0.require(b'prepare=0 writer=102\n' in raw,'missing RAM evidence not rejected')
        elif case=='late-ro-clear':h0.require(b'prepare=0 writer=1\n' in raw and b'error=110 records=0 bytes=0' in raw,
            'expired RO clear started a filesystem write')
        else:h0.require(b'prepare=0 writer=103\n' in raw,'failed root admission reached writable phase')
        if case=='checker-timeout':h0.require(b'FILE_CHECKER_SETTLED owner_reaped=1 children=0\n' in raw,
            'timed-out checker was not conclusively killed/reaped')
        proof=dict(status='PASS_REJECTED_WITHOUT_DISK_CHANGE')
    value=dict(case=case,status='PASS',run_id=selection['run_id'],expected=selection['measured'],proof=proof,
        disk_before=before,disk_after=after,outside_before=outside,outside_after=outside_after,
        raw=pin(out/'serial.log'),device_actions=0,scope='ARM64_VIRT_NOT_SAMSUNG')
    if first:value.update(helper_request=pin(out/'helper/request.json'),initramfs=pin(out/'initramfs.cpio.gz',maximum=32*1024**2))
    h0.publish(out/'result.json',value);print(case,'PASS',flush=True);return value


def suite(out,build):
    out=h0.private(out,fresh=True);build=h0.private(build);sources=build_api.snapshot(out)
    first=read(build/'build.json')['profile']==first_profile.PROFILE
    results=[run(out/case,build,case) for case in (first_profile.CASES if first else CASES)]
    for row in sources:h0.require(h0.sha(h0.ROOT/row['path'])==row['sha256'],'file VM source changed')
    h0.publish(out/'result.json',dict(status='PASS',cases=results,build_sha256=h0.sha(build/'build.json'),
        source_inputs=sources,device_actions=0))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('output','build'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--case',choices=first_profile.CASES);a=p.parse_args()
    if a.case:run(h0.private(a.output),h0.private(a.build),a.case)
    else:suite(a.output,a.build)

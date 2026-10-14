#!/usr/bin/env python3
"""Real ARM64 diagnostic bytes; VM terminal/footer text cannot prove outcomes."""
import argparse
import json
import os
from pathlib import Path
import subprocess

import file_log_vm as vm
import file_log
import failure_faults
import h0
import s22plus_debian_failure_protocol_v1 as protocol
import s22plus_debian_failure_profile_v1 as profile
from s22plus_native_records_v3 import pin,read

CASES=profile.CASES


def run(out,build,case):
    h0.require(case in CASES,'unknown diagnostic VM case')
    selection=vm.prepare(out,build,case)
    h0.require(selection['diagnostic'],'VM requires actual diagnostic build')
    fixture=vm.archive.fixture
    before=fixture.fixture_tools.sparse_digest(out/'disk.img')
    outside=vm.disk_tools.outside_native(out/'disk.img')
    command=[fixture.QEMU/'usr/bin/qemu-system-aarch64','-machine','virt','-cpu','cortex-a76','-smp','2','-m','768',
        '-nic','none','-display','none','-monitor','none','-serial','stdio','-no-reboot','-kernel',vm.archive.KERNEL,
        '-initrd',out/'initramfs.cpio.gz','-append',vm.archive.KERNEL_COMMAND_LINE,
        '-drive',f'if=none,id=root,file={out}/disk.img,format=raw',
        '-device','virtio-blk-device,drive=root,logical_block_size=4096,physical_block_size=4096']
    h0.publish(out/'command.json',list(map(str,command)))
    # Preserve raw even when QEMU times out. Termination is host-only and is
    # never used as evidence that a physical worker was collected or cancelled.
    timed_out=False
    with (out/'serial.log').open('xb') as stream:
        try:
            result=subprocess.run(list(map(str,command)),stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT,
                env=dict(os.environ,LD_LIBRARY_PATH=str(fixture.QEMU/'usr/lib/x86_64-linux-gnu')),
                timeout=20 if case in ('pending','late-return') else 120)
            code=result.returncode
        except subprocess.TimeoutExpired:timed_out=True;code=None
    raw=(out/'serial.log').read_bytes()
    h0.require(b'FILE_VM_TERMINAL' not in raw and b'FILE_VM_RO' not in raw,'VM semantic footer leaked into diagnostic evidence')
    proof=protocol.decode(raw,key=(build/'key').read_bytes(),run=bytes.fromhex(selection['run_id']))
    h0.publish(out/'diagnostic-proof.json',proof)
    from s22plus_debian_usb_protocol_v1 import retained
    primary=retained(raw.replace(b'\r',b''),key=(build/'key').read_bytes(),run=bytes.fromhex(selection['run_id']),domain=protocol.DOMAIN)
    h0.publish(out/'primary-proof.json',primary)
    after=fixture.fixture_tools.sparse_digest(out/'disk.img')
    outside_after=vm.disk_tools.outside_native(out/'disk.img')
    h0.require(outside==outside_after,'diagnostic VM changed outside native_data')
    value=dict(status='PASS',case=case,run_id=selection['run_id'],expected=selection['measured'],scope='ARM64_VIRT_NOT_SAMSUNG',device_actions=0,
        raw=pin(out/'serial.log'),proof=proof,primary=primary,helper_request=pin(out/'helper/request.json'),
        initramfs=pin(out/'initramfs.cpio.gz',maximum=32*1024**2),host_exit=code,host_timeout=timed_out,
        disk_before=before,disk_after=after,outside_before=outside,outside_after=outside_after)
    profile.validate_case(value,dict(selection,key=pin(build/'key',maximum=32)))
    if case in ('normal',*profile.PARTIAL_WRITES,'module-error'):
        value['file_retrieval']=vm.retrieve(out,selection,build,complete=case=='normal')
    h0.publish(out/'result.json',value);print(case,'PASS',flush=True);return value


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--case',choices=CASES);args=parser.parse_args()
    if args.case:run(h0.private(args.output),h0.private(args.build),args.case)
    else:
        out=h0.private(args.output,fresh=True);build=h0.private(args.build)
        sources=file_log.snapshot(out)
        results=[run(out/case,build,case) for case in CASES]
        for row in sources:h0.require(h0.sha(h0.ROOT/row['path'])==row['sha256'],'source changed during VM suite')
        h0.publish(out/'result.json',dict(status='PASS',cases=results,source_inputs=sources,build_sha256=h0.sha(build/'build.json'),device_actions=0))

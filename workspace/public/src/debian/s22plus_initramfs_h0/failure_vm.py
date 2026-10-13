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
from s22plus_native_records_v3 import pin,read

CASES=('normal','insert-error',*failure_faults.NAMES,'short-write','file-sync-error','parent-sync-error','unmount-error')


def run(out,build,case):
    h0.require(case in CASES,'unknown diagnostic VM case')
    selection=vm.prepare(out,build,case)
    h0.require(selection['diagnostic'],'VM requires actual diagnostic build')
    fixture=vm.archive.fixture
    before=fixture.fixture_tools.sparse_digest(out/'disk.img')
    outside=vm.disk_tools.outside_native(out/'disk.img')
    command=[fixture.QEMU/'usr/bin/qemu-system-aarch64','-machine','virt','-cpu','cortex-a76','-smp','2','-m','768',
        '-nic','none','-display','none','-monitor','none','-serial','stdio','-no-reboot','-kernel',vm.archive.KERNEL,
        '-initrd',out/'initramfs.cpio.gz','-append','console=ttyAMA0 rdinit=/init panic=1',
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
    terminal={r['helper']:r for r in proof['records'] if r['sequence']==2}
    prep=terminal.get(1);writer=terminal.get(2)
    expected_unknown=case in ('lost-diagnostic','parent-death')
    if expected_unknown:
        # Lost preparation diagnostics can coexist with independent writer
        # evidence. Parent death cannot authorize the next helper.
        h0.require(prep is None,'lost parent channel manufactured a terminal')
        if case=='parent-death':h0.require(writer is None and before==after,'dead parent advanced file writer')
    else:
        h0.require(prep is not None,'real preparation diagnostic terminal missing')
        fields=prep['fields']
        if case in ('normal','interrupted','short-write','file-sync-error','parent-sync-error','unmount-error'):
            h0.require(prep['semantic_success'] and writer is not None,'normal preparation did not reach measured writer')
            if case in ('normal','interrupted'):h0.require(writer['semantic_success'],'normal writer not semantically complete')
            else:
                h0.require(not writer['semantic_success'] and writer['fields']['result']==1,'writer fault lost its outcome')
                if case=='parent-sync-error':h0.require(writer['fields']['first_log_failure_stage']==7 and
                    writer['fields']['first_log_failure_errno']==5,'parent synchronization failure lost')
        else:
            h0.require(writer is None and before==after,'failed preparation advanced file writer')
            h0.require(not prep['semantic_success'],'negative preparation is successful')
            if case=='insert-error':h0.require(fields['call_returned']==1 and fields['call_rc']==-1 and
                fields['call_errno']==5 and fields['call_returns']==1,'module errno lost')
            elif case in ('begin-log','ram-sync'):h0.require(fields['call_returns']==0 and
                fields['first_log_failure_errno']==5,'failed BEGIN evidence reached insertion')
            elif case in ('done-log','kernel-readback'):h0.require(fields['call_returns']==1 and
                fields['call_returned']==1 and fields['call_rc']==0 and fields['call_errno']==0 and
                fields['first_log_failure_errno'] in (5,110),'evidence failure misclassified as module failure')
            elif case=='worker-exit':h0.require(prep['exit_code']==77 and not fields['semantic_done'],'unexpected exit treated as completion')
            elif case=='worker-signal':h0.require(prep['signal']==15,'signal outcome lost')
            elif case=='unstable':h0.require(not prep['stable'] and fields is None and prep['signal']==15,'torn state asserted')
            elif case in ('pending','late-return'):h0.require(timed_out and
                prep['observation']=='WORKER_NOT_COLLECTED_AT_DEADLINE' and fields['phase']==3 and
                fields['call_returned']==0,'pending call gained returned/cancelled proof')
    if case=='late-return':
        events=[r['event'].split(' ',2)[2] for r in primary['records']]
        h0.require(sum(e.startswith('MODULE_BEGIN ') for e in events)==1 and
            sum(e.startswith('MODULE_DONE ') for e in events)==1 and
            events[-1]=='TERMINAL result=REJECTED error=110','late return performed later module effects')
    value=dict(status='PASS',case=case,scope='ARM64_VIRT_NOT_SAMSUNG',device_actions=0,
        raw=pin(out/'serial.log'),proof=proof,primary=primary,helper_request=pin(out/'helper/request.json'),
        initramfs=pin(out/'initramfs.cpio.gz',maximum=32*1024**2),host_exit=code,host_timeout=timed_out,
        disk_before=before,disk_after=after,outside_before=outside,outside_after=outside_after)
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
        h0.publish(out/'result.json',dict(status='PASS',cases=results,source_inputs=sources,device_actions=0))

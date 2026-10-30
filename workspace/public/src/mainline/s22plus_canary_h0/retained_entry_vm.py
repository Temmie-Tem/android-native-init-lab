#!/usr/bin/env python3
"""Actual EL fixtures for exact linked marker bytes; no physical I/O."""
import argparse
import json
import os
from pathlib import Path
import socket
import struct
import subprocess

from prepare import ROOT,digest,require
import retained_marker as marker

def qualify(qualification,gdb,output,reuse_probe_vm=None):
    qualification,gdb,output=[p.resolve() for p in (qualification,gdb,output)]
    require(output.is_relative_to(ROOT/'workspace/private'),'private emulator output')
    record=json.loads((qualification/'result.json').read_text())
    require(record['status']=='PASS_H0_ACTUAL_RETAINED_MARKERS','marker producer tests absent')
    config=json.loads(Path(record['config']['path']).read_text())
    require(reuse_probe_vm is None or marker.version(config) in (9,10),'probe VM reuse needs a probe format')
    output.mkdir(mode=0o700,parents=True,exist_ok=False)
    seed=output/'log-seed.bin'
    seed.write_bytes(struct.pack('<IIII',7,0x4d474f4c,marker.PAYLOAD+300,123)+b'\xa5'*marker.PAYLOAD)
    qroot=ROOT/'workspace/private/tools/qemu-arm64-10.2.1/root';qemu=qroot/'usr/bin/qemu-system-aarch64'
    env=dict(os.environ,LD_LIBRARY_PATH=str(qroot/'usr/lib/x86_64-linux-gnu'))
    rows=[]
    for routine in record['routines']:
        code=Path(routine['code_path']);require(digest(code)==routine['code_sha256'],'linked routine changed')
        for el,options in [(1,'virtualization=off,secure=off'),(2,'virtualization=on,secure=off'),(3,'virtualization=on,secure=on')]:
            folder=output/f"stage-{routine['stage']}-el{el}";folder.mkdir()
            with socket.socket() as listener:listener.bind(('127.0.0.1',0));port=listener.getsockname()[1]
            # File-backed sparse RAM includes the actual high physical slice
            # without committing a 36 GiB anonymous allocation on the host.
            sparse=folder/'guest-ram.sparse'
            command=[str(qemu),'-object',f'memory-backend-file,id=vmram,size=36G,mem-path={sparse},share=on,reserve=off,prealloc=off,dump=off',
                '-nodefaults','-machine','virt,memory-backend=vmram,'+options,'-cpu','cortex-a76','-smp','1','-m','36G',
                '-display','none','-monitor','none','-serial','none','-no-reboot','-S','-gdb',f'tcp:127.0.0.1:{port}',
                '-device',f"loader,file={code},addr={routine['address']},force-raw=on",
                '-device',f'loader,file={seed},addr={marker.BASE},force-raw=on',
                '-device',f"loader,addr={routine['address']},cpu-num=0"]
            stop=0x40010000;expected=bytearray(seed.read_bytes())
            if el!=3:
                start=marker.HEADER+44+marker.slot(config,routine['stage'])
                expected[start:start+marker.SLOT]=bytes.fromhex(config['frames'][str(routine['stage'])])
            expected_path=folder/'expected.bin';expected_path.write_bytes(expected)
            script=f'''set pagination off
set confirm off
set architecture aarch64
set tcp auto-retry on
set tcp connect-timeout 10
target remote 127.0.0.1:{port}
python
import gdb,json
assert int(gdb.parse_and_eval('$pc'))=={routine['address']}
cpsr=int(gdb.parse_and_eval('$cpsr'))
assert (cpsr>>2)&3=={el}, 'actual initial EL differs'
protected={{i:0x1234567800000000+i for i in list(range(9))+list(range(18,30))}}
for i,v in protected.items(): gdb.execute('set $x%d = %d' % (i,v))
gdb.execute('set $x30 = {stop}')
gdb.execute('set $sp = {stop+2048}')
end
hbreak *{stop}
continue
python
assert int(gdb.parse_and_eval('$pc'))=={stop}
for i,v in protected.items(): assert int(gdb.parse_and_eval('$x%d'%i))==v, 'startup register changed'
assert int(gdb.parse_and_eval('$sp'))=={stop+2048}
actual=bytes(gdb.selected_inferior().read_memory({marker.BASE},{marker.REGION}))
assert actual==open({str(expected_path)!r},'rb').read(), 'marker RAM/header/extent differs'
result=dict(stage={routine['stage']},actual_entry_el={el},state_registers_modified=False,
            argument_register_fixture=True,header_and_outside_slot_preserved=True,
            marker_committed={el!=3},startup_registers_preserved=True)
open({str(folder/'result.json')!r},'x').write(json.dumps(result,indent=2)+'\\n')
end
detach
quit
'''
            (folder/'fixture.gdb').write_text(script)
            (folder/'command.json').write_text(json.dumps(dict(qemu=command,gdb=str(gdb)),indent=2)+'\n')
            with (folder/'qemu.stderr').open('xb') as err:
                proc=subprocess.Popen(command,env=env,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=err)
                try:
                    with (folder/'gdb.log').open('xb') as log:
                        check=subprocess.run([gdb,'-q','-nx','-batch','-x',folder/'fixture.gdb'],stdout=log,stderr=subprocess.STDOUT,timeout=45)
                    require(check.returncode==0 and (folder/'result.json').is_file(),'actual EL marker fixture failed: '+str(folder))
                    rows.append(json.loads((folder/'result.json').read_text()))
                finally:
                    proc.terminate()
                    try:proc.wait(timeout=5)
                    except subprocess.TimeoutExpired:proc.kill();proc.wait(timeout=5)
                    if sparse.exists():sparse.unlink()
    result=dict(schema='s22plus-mainline-marker-entry-vm-v1',status='PASS_H0_ACTUAL_EL_RETAINED_MARKERS',
        loader_sha256=record['loader_sha256'],kernel_sha256=record['kernel_sha256'],config=record['config'],
        qualification_sha256=digest(qualification/'result.json'),source_sha256=digest(__file__),
        qemu_sha256=digest(qemu),gdb_sha256=digest(gdb),cases=rows,
        physical_retention_proved=False,cache_coherency_proved=False,device_actions=0)
    if marker.c_stages(config):
        if marker.version(config) in (9,10):
            from retained_probe_vm import qualify as qualify_kernel
            if reuse_probe_vm is not None:
                prior=Path(reuse_probe_vm).resolve();mapped=json.loads((prior/'result.json').read_text())
                require(mapped['status']=='PASS_H0_ACTUAL_KERNEL_MMU_DEFERRED_PROBE' and
                        mapped['source_sha256']==digest(marker.HERE/'retained_probe_vm.py') and
                        mapped['kernel_sha256']==record['kernel_sha256'] and
                        mapped['qemu_sha256']==digest(qemu) and mapped['gdb_sha256']==digest(gdb) and
                        mapped['mapping_initramfs']==record['mmu_on']['mapping_initramfs'] and
                        mapped['declared_span']==config['span'] and mapped['device_actions']==0,
                        'retained V9 VM evidence inputs differ')
                for case in mapped['cases']:
                    folder=prior/case['case']
                    require(json.loads((folder/'result.json').read_text())==case and
                            (folder/'observed.bin').read_bytes()==(folder/'expected.bin').read_bytes(),
                            'retained V9 VM raw/terminal differs')
                result['mmu_on']=mapped
                result['reused_kernel_vm']=dict(path=str(prior/'result.json'),sha256=digest(prior/'result.json'))
        elif marker.version(config)==8:
            from retained_trace_vm import qualify as qualify_kernel
        else:
            from retained_kernel_vm import qualify as qualify_kernel
        if 'mmu_on' not in result:result['mmu_on']=qualify_kernel(record,gdb,output/'early-c-kernel')
    (output/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(status=result['status'],cases=len(rows),device_actions=0)))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('qualification','gdb','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--reuse-probe-vm',type=Path)
    a=p.parse_args();qualify(a.qualification,a.gdb,a.output,a.reuse_probe_vm)

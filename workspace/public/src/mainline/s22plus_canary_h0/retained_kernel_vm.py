#!/usr/bin/env python3
"""Run the exact marked kernel through real MMU setup and early mapping APIs."""
import json
import os
from pathlib import Path
import socket
import struct
import subprocess

from prepare import ROOT,digest,require
from qualify_retained import symbols
import retained_marker as marker


def qualify(record,gdb,output):
    output.mkdir(mode=0o700,parents=True,exist_ok=False)
    artifact=record['mmu_on'];kernel=Path(artifact['kernel_path']);elf=Path(artifact['elf_path'])
    require(digest(kernel)==artifact['kernel_sha256'] and digest(elf)==artifact['elf_sha256'], 'MMU fixture inputs changed')
    raw=kernel.read_bytes();syms=symbols(elf);base=syms['_text']
    cfg=json.loads(Path(record['config']['path']).read_text())
    switch=syms['__primary_switch']-base
    branch=raw.index(struct.pack('<I',0xd61f0100),switch,switch+128)
    qroot=ROOT/'workspace/private/tools/qemu-arm64-10.2.1/root';qemu=qroot/'usr/bin/qemu-system-aarch64'
    env=dict(os.environ,LD_LIBRARY_PATH=str(qroot/'usr/lib/x86_64-linux-gnu'))
    rows=[]
    specs=[('normal',marker.PAYLOAD+300,0x4d474f4c,0,None),
           ('normal-el1',marker.PAYLOAD+300,0x4d474f4c,0,None),
           ('page-crossing',marker.PAYLOAD+4196,0x4d474f4c,0,None),
           ('bad-header',marker.PAYLOAD+300,0,0,None),
           ('short-index',255,0x4d474f4c,0,None),
           ('header-map-full',marker.PAYLOAD+300,0x4d474f4c,1,None),
           ('slot-map-full',marker.PAYLOAD+300,0x4d474f4c,2,None)]
    specs += [('changed-'+str(i),marker.PAYLOAD+300,0x4d474f4c,0,i) for i in (0,4,8,12)]
    for label,idx,magic,fail_map,change in specs:
        folder=output/label;folder.mkdir();sparse=folder/'guest-ram.sparse'
        seed=folder/'seed.bin';seed.write_bytes(struct.pack('<IIII',7,magic,idx,123)+b'\xa5'*marker.PAYLOAD)
        cursor=idx%marker.PAYLOAD;position=cursor-256 if cursor>=256 else marker.PAYLOAD-256
        expected=bytearray(seed.read_bytes());valid=idx>=256 and magic==0x4d474f4c
        if valid:
            expected[16+position:16+position+128]=bytes.fromhex(cfg['frames']['3'])
            if not fail_map:
                frame=bytes.fromhex(cfg['frames']['4'])
                expected[16+position+128:16+position+256]=frame if change is None else bytes(8)+frame[8:]
                if change is not None:struct.pack_into('<I',expected,change,0x12345678)
        expectation=folder/'expected.bin';expectation.write_bytes(expected)
        with socket.socket() as listener:listener.bind(('127.0.0.1',0));port=listener.getsockname()[1]
        virtual='off' if label=='normal-el1' else 'on'
        command=[str(qemu),'-object',f'memory-backend-file,id=vmram,size=36G,mem-path={sparse},share=on,reserve=off,prealloc=off,dump=off',
            '-nodefaults','-machine',f'virt,memory-backend=vmram,virtualization={virtual},dtb-randomness=off','-cpu','cortex-a76',
            '-smp','1','-m','36G','-display','none','-monitor','none','-serial','file:'+str(folder/'serial.log'),
            '-no-reboot','-S','-gdb',f'tcp:127.0.0.1:{port}','-kernel',str(kernel),
            '-device',f'loader,file={seed},addr={marker.BASE},force-raw=on']
        script=f'''set pagination off
set confirm off
set architecture aarch64
set tcp auto-retry on
set tcp connect-timeout 10
target remote 127.0.0.1:{port}
python
import gdb,json,struct
inferior=gdb.selected_inferior()
def pointer(register):
    # GDB exposes PC as a signed pointer on this host, while general X
    # registers are unsigned. Compare their exact 64-bit address patterns.
    return int(gdb.parse_and_eval(register)) & ((1<<64)-1)
header=bytes.fromhex({raw[:64].hex()!r})
places=[a for a in (0x40000000,0x40080000,0x40200000) if bytes(inferior.read_memory(a,64))==header]
assert len(places)==1, 'actual QEMU Image placement differs'
physical=places[0]
b=gdb.Breakpoint('*%d'%(physical+{branch}),type=gdb.BP_HARDWARE_BREAKPOINT,internal=True)
gdb.execute('continue')
assert pointer('$pc')==physical+{branch}
b.delete()
delta=pointer('$x8')-{syms['__primary_switched']}
entry={syms['s22_retained_early_c']}+delta
b=gdb.Breakpoint('*%d'%entry,type=gdb.BP_HARDWARE_BREAKPOINT,internal=True)
gdb.execute('continue')
assert pointer('$pc')==entry, 'early C entry breakpoint differs'
actual_el=(int(gdb.parse_and_eval('$cpsr'))>>2)&3
print('Actual early C exception level:',actual_el)
assert actual_el in (1,2), 'early C actual EL is outside the writer contract'
assert actual_el=={1 if virtual=='off' else 2}, 'selected QEMU exception-level fixture differs'
b.delete()
returned=pointer('$x30')
prev={syms['prev_map']}+delta
assert bytes(inferior.read_memory(prev,56))==bytes(56), 'real early map slots already occupied'
occupied=([1]*7 if {fail_map}==1 else [0]+[1]*6 if {fail_map}==2 else [0]*7)
inferior.write_memory(prev,struct.pack('<7Q',*occupied))
if {change!r} is not None:
    b=gdb.Breakpoint('*%d'%({syms['s22_retained_early_c_recheck']}+delta),type=gdb.BP_HARDWARE_BREAKPOINT,internal=True)
    gdb.execute('continue')
    assert pointer('$pc')=={syms['s22_retained_early_c_recheck']}+delta
    b.delete()
    with open({str(sparse)!r},'r+b',buffering=0) as f:
        f.seek({marker.BASE-0x40000000+(change or 0)});f.write(struct.pack('<I',0x12345678))
b=gdb.Breakpoint('*%d'%returned,type=gdb.BP_HARDWARE_BREAKPOINT,internal=True)
gdb.execute('continue')
assert pointer('$pc')==returned
assert bytes(inferior.read_memory(prev,56))==struct.pack('<7Q',*occupied), 'real early mapping leaked'
with open({str(sparse)!r},'rb') as f:
    f.seek({marker.BASE-0x40000000});actual=f.read({marker.REGION})
open({str(folder/'observed.bin')!r},'xb').write(actual)
assert actual==open({str(expectation)!r},'rb').read(), 'actual MMU writer bytes/header/extent differs'
result=dict(case={label!r},kernel_physical=physical,relocation=delta,actual_c_el=actual_el,
            real_mmu_boot=True,real_mapping_api=True,mapping_pressure_fixture={fail_map},
            mapping_slots_restored=True,header_and_outside_span_preserved=True,
            early_c_committed={valid and not fail_map and change is None})
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
                    check=subprocess.run([str(gdb),'-q','-nx','-batch','-x',str(folder/'fixture.gdb')],
                                         stdout=log,stderr=subprocess.STDOUT,timeout=45)
                require(check.returncode==0 and (folder/'result.json').exists(),'actual MMU fixture failed: '+str(folder))
                rows.append(json.loads((folder/'result.json').read_text()))
            finally:
                proc.terminate()
                try:proc.wait(timeout=5)
                except subprocess.TimeoutExpired:proc.kill();proc.wait(timeout=5)
                if sparse.exists():sparse.unlink()
    require(digest(kernel)==artifact['kernel_sha256'],'MMU kernel changed during qualification')
    result=dict(status='PASS_H0_ACTUAL_KERNEL_MMU_MARKERS',kernel_sha256=digest(kernel),
        source_sha256=digest(__file__),qemu_sha256=digest(qemu),gdb_sha256=digest(gdb),
        cases=rows,cache_coherency_proved=False,physical_retention_proved=False,device_actions=0)
    (output/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    return result

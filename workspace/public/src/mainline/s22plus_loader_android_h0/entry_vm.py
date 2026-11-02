#!/usr/bin/env python3
"""Actual-EL QEMU entry with an instruction-fed synthetic ABL FDT argument."""
import argparse
import json
import os
from pathlib import Path
import socket
import struct
import subprocess

from build import ROOT, STATUS, digest, pin, require
import s22plus_loader_android_profile_v1 as profile


def qualify(loader,gdb,output):
    loader,gdb,output=[Path(p).resolve() for p in (loader,gdb,output)]
    require(output.is_relative_to(ROOT/'workspace/private') and not output.exists(),'fresh private QEMU output')
    record=json.loads((loader/'result.json').read_text())
    require(record['status']==STATUS and pin(record['loader']['path'])==record['loader'] and
            pin(record['retained_fdt']['path'])==record['retained_fdt'],'QEMU input differs')
    blob=Path(record['loader']['path']);fdt=Path(record['retained_fdt']['path']);s=record['runtime_symbols']
    output.mkdir(mode=0o700,parents=True)
    logm=record.get('logm_control')
    if logm:
        config=profile.logm_binding(logm,record['marker'])
        # Same sparse high-RAM fixture used by the existing mainline marker VM.
        sparse=output/'vm-memory.bin'
        with sparse.open('xb') as stream:stream.truncate(36*1024**3)
        seed=struct.pack('<IIII',7,0x4d474f4c,profile.LOGM_PAYLOAD+257,19)+bytes([0xa5])*profile.LOGM_PAYLOAD
        (output/'logm-seed.bin').write_bytes(seed)
    # QEMU's virt machine reserves its own first-MiB DTB at RAM base.
    source=0x80000000;fdt_address=0xb4000000;entry=0x41000000
    # ldr x0, literal-FDT; ldr x1, literal-source; br x1; nop; two literals.
    trampoline=struct.pack('<IIIIQQ',0x58000080,0x580000a1,0xd61f0020,0xd503201f,fdt_address,source)
    (output/'fixture-entry.bin').write_bytes(trampoline)
    qroot=ROOT/'workspace/private/tools/qemu-arm64-10.2.1/root'
    qemu=qroot/'usr/bin/qemu-system-aarch64'
    env=dict(os.environ,LD_LIBRARY_PATH=str(qroot/'usr/lib/x86_64-linux-gnu'))
    rows=[]
    for el,options in [(1,'virtualization=off,secure=off'),(2,'virtualization=on,secure=off'),
                       (3,'virtualization=on,secure=on')]:
        work=output/f'el{el}';work.mkdir(mode=0o700)
        with socket.socket() as listener:listener.bind(('127.0.0.1',0));port=listener.getsockname()[1]
        memory=(['-object',f'memory-backend-file,id=vmram,size=36G,mem-path={sparse},share=on,reserve=off,prealloc=off,dump=off'] if logm else [])
        machine='virt,'+options+(',memory-backend=vmram' if logm else '')
        command=[str(qemu),*memory,'-nodefaults','-machine',machine,'-cpu','cortex-a76','-smp','1','-m','36G' if logm else '3G',
            '-display','none','-monitor','none','-serial','none','-no-reboot','-S','-gdb',f'tcp:127.0.0.1:{port}',
            '-device',f'loader,file={blob},addr={source},force-raw=on',
            '-device',f'loader,file={fdt},addr={fdt_address},force-raw=on',
            '-device',f'loader,file={output/"fixture-entry.bin"},addr={entry},force-raw=on',
            '-device',f'loader,addr={entry},cpu-num=0']
        if logm:command+=['-device',f'loader,file={output/"logm-seed.bin"},addr=0x800200000,force-raw=on']
        success=record['extents']['kernel'][0] if logm else s['_start']
        expected=success if el!=3 else source+s['_reloc_rejected']-s['_head']
        logm_check=''
        if logm:
            logm_check=f'''
import struct
seed=open({str(output/'logm-seed.bin')!r},'rb').read()
ring=bytes(gdb.selected_inferior().read_memory(0x800200000,len(seed)))
if {el}==3:
    assert ring==seed, 'rejected EL3 changed LOGM'
else:
    assert [int(gdb.parse_and_eval('$x'+str(n))) for n in range(4)]==[{record['extents']['fdt'][0]},0,0,0], 'kernel arguments changed'
    kernel=open({record['kernel']['path']!r},'rb').read()
    assert bytes(gdb.selected_inferior().read_memory({record['extents']['kernel'][0]},len(kernel)))==kernel, 'vendor kernel copy changed'
    dtaddr={record['extents']['fdt'][0]}
    length=struct.unpack('>I',bytes(gdb.selected_inferior().read_memory(dtaddr+4,4)))[0]
    assert 40<=length<={record['fdt_capacity']}, 'final FDT length exceeds buffer'
    final_fdt=bytes(gdb.selected_inferior().read_memory(dtaddr,length))
    open({str(work/'final.dtb')!r},'xb').write(final_fdt)
    frame=bytes.fromhex({config['frame_hex']!r})
    expected_ring=bytearray(seed);expected_ring[17:145]=frame
    assert ring==expected_ring, 'actual EL writer changed header or escaped unaligned 128-byte slot'
open({str(work/'logm.bin')!r},'xb').write(ring)
'''
        script=f'''set pagination off
set confirm off
set architecture aarch64
set tcp auto-retry on
set tcp connect-timeout 10
target remote 127.0.0.1:{port}
python
import gdb,json
pc=int(gdb.parse_and_eval('$pc'));cpsr=int(gdb.parse_and_eval('$cpsr'))
assert pc=={entry} and (cpsr>>2)&3=={el}, 'actual initial PC/EL differs'
initial_cpsr=cpsr
end
hbreak *{success}
hbreak *{source+s['_reloc_rejected']-s['_head']}
continue
python
pc=int(gdb.parse_and_eval('$pc'));cpsr=int(gdb.parse_and_eval('$cpsr'))
assert pc=={expected}, 'wrong entry terminal'
assert int(gdb.parse_and_eval('$x28'))=={fdt_address}, 'actual incoming x0 was lost'
if {el}!=3:
    assert cpsr&0x3c0==0x3c0, 'DAIF masks missing'
    if {not bool(logm)!r}:
        raw=open({str(blob)!r},'rb').read()[{s['_start']-s['_head']}:]
        assert bytes(gdb.selected_inferior().read_memory({s['_start']},len(raw)))==raw, 'relocated bytes differ'
assert bytes(gdb.selected_inferior().read_memory({fdt_address},{fdt.stat().st_size}))==open({str(fdt)!r},'rb').read(), 'input FDT changed'
{logm_check}
result=dict(actual_entry_el={el},initial_cpsr=initial_cpsr,final_cpsr=cpsr,final_pc=pc,
    terminal='entry' if {el}!=3 else 'reject',debugger_modified_registers=False,
    synthetic_fdt_argument_set_by_fixture_instructions=True)
open({str(work/'result.json')!r},'x').write(json.dumps(result,indent=2)+'\\n')
end
detach
quit
'''
        (work/'entry.gdb').write_text(script)
        (work/'command.json').write_text(json.dumps(dict(qemu=command,gdb=str(gdb)),indent=2)+'\n')
        with (work/'qemu.stderr').open('xb') as err:
            proc=subprocess.Popen(command,env=env,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=err)
            try:
                with (work/'gdb.log').open('xb') as log:
                    check=subprocess.run([gdb,'-q','-nx','-batch','-x',work/'entry.gdb'],
                                         stdout=log,stderr=subprocess.STDOUT,timeout=45)
                require(check.returncode==0 and (work/'result.json').is_file(),'QEMU entry failed: '+str(work))
                row=json.loads((work/'result.json').read_text());rows.append(row);print(json.dumps(row),flush=True)
                if logm and el!=3:
                    from prepare import nodes,memreserve
                    tree=nodes(work/'final.dtb');report=tree['/chosen'].pop(profile.LOGM_PROPERTY)
                    require(tree['/chosen'].pop(record['marker_property'])==record['marker'].encode(),
                            'actual EL immutable loader marker differs')
                    require(tree==nodes(fdt) and memreserve(work/'final.dtb')==memreserve(fdt) and
                            (work/'final.dtb').read_bytes()[20:32]==fdt.read_bytes()[20:32],
                            'actual EL handoff changed existing FDT semantics')
                    observed=profile.logm_report(report,config)
                    require(observed['status']=='READBACK_MATCH' and observed['current_el']==el*4 and
                            observed['slot_offset']==1,'actual EL LOGM report differs')
                    row['logm_writer']=observed
            finally:
                proc.terminate()
                try:proc.wait(timeout=5)
                except subprocess.TimeoutExpired:proc.kill();proc.wait(timeout=5)
    result=dict(status='PASS_H0_QEMU_ACTUAL_EL_LOADER_ANDROID',loader_sha256=digest(blob),
        source=pin(__file__),qemu=pin(qemu),gdb=pin(gdb),retained_fdt=record['retained_fdt'],
        fixture=pin(output/'fixture-entry.bin'),cases=rows,cache_coherency_proved=False,
        physical_entry_proved=False,device_actions=0)
    if logm:
        result['logm_control']=dict(status='PASS_H0_ACTUAL_EL_LOADER_LOGM_CONTROL',configuration=config,
            final_fdt_and_header_preserved=True,unaligned_payload_slot=1,actual_entry_els=[1,2],el3_rejected=True)
    (output/'result.json').write_text(json.dumps(result,indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('loader','gdb','output'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();qualify(a.loader,a.gdb,a.output)

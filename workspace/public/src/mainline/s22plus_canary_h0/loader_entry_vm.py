#!/usr/bin/env python3
"""Run the pinned loader at actual QEMU EL1/EL2/EL3; no physical transport."""
import argparse
import json
import os
from pathlib import Path
import socket
import subprocess

from prepare import ROOT, digest, require


def qualify(loader,gdb,output):
    source_sha256=digest(__file__)
    loader,gdb,output=[p.resolve() for p in (loader,gdb,output)]
    require(output.is_relative_to(ROOT/'workspace/private'),'private QEMU output')
    output.mkdir(mode=0o700,parents=True,exist_ok=False)
    record=json.loads((loader/'result.json').read_text());blob=Path(record['loader']['path'])
    require(digest(blob)==record['loader']['sha256'],'loader changed')
    s=record['runtime_symbols'];source=0x80000000
    qroot=ROOT/'workspace/private/tools/qemu-arm64-10.2.1/root'
    qemu=qroot/'usr/bin/qemu-system-aarch64'
    env=dict(os.environ,LD_LIBRARY_PATH=str(qroot/'usr/lib/x86_64-linux-gnu'))
    rows=[]
    for el,options in [(1,'virtualization=off,secure=off'),
                       (2,'virtualization=on,secure=off'),(3,'virtualization=on,secure=on')]:
        work=output/f'el{el}';work.mkdir()
        with socket.socket() as listener:listener.bind(('127.0.0.1',0));port=listener.getsockname()[1]
        command=[str(qemu),'-nodefaults','-machine','virt,'+options,'-cpu','cortex-a76','-smp','1','-m','3G',
                 '-display','none','-monitor','none','-serial','none','-no-reboot','-S',
                 '-gdb',f'tcp:127.0.0.1:{port}',
                 '-device',f'loader,file={blob},addr={source},force-raw=on',
                 '-device',f'loader,addr={source},cpu-num=0']
        expected=s['_start'] if el!=3 else source+s['_reloc_rejected']-s['_head']
        # This GDB script reads registers/RAM and sets hardware breakpoints in
        # the local emulator. It never changes entry state to obtain a PASS.
        script=f'''set pagination off
set confirm off
set architecture aarch64
set tcp auto-retry on
set tcp connect-timeout 10
target remote 127.0.0.1:{port}
python
import gdb,json,hashlib
pc=int(gdb.parse_and_eval('$pc'));cpsr=int(gdb.parse_and_eval('$cpsr'))
assert pc=={source} and (cpsr>>2)&3=={el}, 'actual entry PC/EL differs'
initial_cpsr=cpsr
end
hbreak *{s['_start']}
hbreak *{source+s['_reloc_rejected']-s['_head']}
continue
python
pc=int(gdb.parse_and_eval('$pc'));cpsr=int(gdb.parse_and_eval('$cpsr'))
assert pc=={expected}, 'wrong entry terminal'
if {el}!=3:
    assert cpsr&0x3c0==0x3c0, 'DAIF masks missing'
    raw=open({str(blob)!r},'rb').read()[{s['_start']-s['_head']}:]
    actual=bytes(gdb.selected_inferior().read_memory({s['_start']},len(raw)))
    assert actual==raw, 'actual relocated bytes differ'
result=dict(actual_entry_el={el},initial_cpsr=initial_cpsr,final_cpsr=cpsr,final_pc=pc,
            terminal='entry' if {el}!=3 else 'reject',register_state_modified=False)
open({str(work/'result.json')!r},'x').write(json.dumps(result,indent=2)+'\\n')
end
detach
quit
'''
        (work/'entry.gdb').write_text(script)
        (work/'command.json').write_text(json.dumps({'qemu':command,'gdb':str(gdb)},indent=2)+'\n')
        with (work/'qemu.stderr').open('xb') as err:
            proc=subprocess.Popen(command,env=env,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=err)
            try:
                with (work/'gdb.log').open('xb') as log:
                    check=subprocess.run([gdb,'-q','-nx','-batch','-x',work/'entry.gdb'],
                                         stdout=log,stderr=subprocess.STDOUT,timeout=45)
                require(check.returncode==0 and (work/'result.json').is_file(),'QEMU entry failed; inspect '+str(work))
                row=json.loads((work/'result.json').read_text());rows.append(row);print(json.dumps(row),flush=True)
            finally:
                proc.terminate()
                try:proc.wait(timeout=5)
                except subprocess.TimeoutExpired:proc.kill();proc.wait(timeout=5)
    require(digest(__file__)==source_sha256,'entry-test source changed during execution')
    result={'status':'PASS_H0_QEMU_ACTUAL_EXCEPTION_LEVELS','loader_sha256':digest(blob),
            'source_sha256':source_sha256,'qemu_sha256':digest(qemu),'gdb_sha256':digest(gdb),
            'cases':rows,'cache_coherency_proved':False,'physical_entry_proved':False,'device_actions':0}
    (output/'result.json').write_text(json.dumps(result,indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('loader','gdb','output'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();qualify(a.loader,a.gdb,a.output)

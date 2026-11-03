#!/usr/bin/env python3
"""Run the actual ordinary loader and parked Image at real QEMU EL1/EL2."""
import argparse
import json
import os
from pathlib import Path
import socket
import struct
import subprocess

from prepare import ROOT, digest, require
import entry_park as park
import retained_marker as marker


CASES = ((1, 'valid', 0x4d474f4c, marker.PAYLOAD+300),
         (2, 'valid', 0x4d474f4c, marker.PAYLOAD+300),
         (1, 'bad-magic', 0, marker.PAYLOAD+300),
         (1, 'short-index', 0x4d474f4c, 255))


def qualify(loader, gdb, output):
    loader, gdb, output = (Path(p).resolve() for p in (loader, gdb, output))
    require(output.is_relative_to(ROOT/'workspace/private') and not output.exists(), 'fresh private park output')
    record = json.loads((loader/'result.json').read_text())
    linked = park.linked(record); blob = Path(record['loader']['path'])
    require(park.pin(blob) == record['loader'], 'park loader changed')
    cfg = json.loads(Path(record['retained_marker']['config']['path']).read_text())
    require(marker.version(cfg) == 1, 'park requires V1 markers')
    output.mkdir(mode=0o700, parents=True)
    qroot = ROOT/'workspace/private/tools/qemu-arm64-10.2.1/root'
    qemu = qroot/'usr/bin/qemu-system-aarch64'
    env = dict(os.environ, LD_LIBRARY_PATH=str(qroot/'usr/lib/x86_64-linux-gnu'))
    source = 0x80000000; syms = record['runtime_symbols']; rows = []
    source_ref = park.pin(__file__)
    for el, name, magic, idx in CASES:
        work = output/f'el{el}-{name}'; work.mkdir()
        seed = work/'seed.bin'
        seed.write_bytes(struct.pack('<IIII', 7, magic, idx, 123)+b'\xa5'*marker.PAYLOAD)
        expected = bytearray(seed.read_bytes())
        admitted = name == 'valid'
        if admitted:
            for stage in (1, 2):
                pos = marker.HEADER+44+marker.slot(cfg, stage)
                expected[pos:pos+marker.SLOT] = bytes.fromhex(cfg['frames'][str(stage)])
        expected_path = work/'expected.bin'; expected_path.write_bytes(expected)
        with socket.socket() as listener:
            listener.bind(('127.0.0.1', 0)); port = listener.getsockname()[1]
        sparse = work/'guest-ram.sparse'
        command = [str(qemu), '-object',
            f'memory-backend-file,id=vmram,size=36G,mem-path={sparse},share=on,reserve=off,prealloc=off,dump=off',
            '-nodefaults', '-machine', f'virt,memory-backend=vmram,virtualization={"on" if el==2 else "off"},secure=off',
            '-cpu', 'cortex-a76', '-smp', '1', '-m', '36G', '-display', 'none', '-monitor', 'none',
            '-serial', 'none', '-no-reboot', '-S', '-gdb', f'tcp:127.0.0.1:{port}',
            '-device', f'loader,file={blob},addr={source},force-raw=on',
            '-device', f'loader,file={seed},addr={marker.BASE},force-raw=on',
            '-device', f'loader,addr={source},cpu-num=0']
        reject = source+syms['_reloc_rejected']-syms['_head']
        script = f'''set pagination off
set confirm off
set architecture aarch64
set tcp auto-retry on
set tcp connect-timeout 10
target remote 127.0.0.1:{port}
python
import gdb,json
reg=lambda n:int(gdb.parse_and_eval('$'+n))
assert reg('pc')=={source} and (reg('cpsr')>>2)&3=={el}, 'actual initial EL differs'
end
hbreak *{linked['park_pc']}
hbreak *{linked['record_mmu_state_pc']}
hbreak *{reject}
continue
python
assert reg('pc')=={linked['park_pc']}, 'did not reach fixed entry park'
assert (reg('cpsr')>>2)&3=={el}, 'entry EL changed before park'
assert reg('cpsr')&0x3c0==0x3c0, 'loader DAIF masks missing'
registers=[r.name for r in gdb.selected_frame().architecture().registers()]
sctlr_name=next(n for n in registers if n.lower()=='sctlr_el{el}')
sctlr=reg(sctlr_name)
assert sctlr&0x2001005==0, 'MMU/cache/endian state differs at park'
actual=bytes(gdb.selected_inferior().read_memory({marker.BASE},{marker.REGION}))
open({str(work/'log-at-park.bin')!r},'xb').write(actual)
assert actual==open({str(expected_path)!r},'rb').read(), 'header, slot or outside-slot bytes differ'
image=open({str(linked['kernel']['path'])!r},'rb').read()
assert bytes(gdb.selected_inferior().read_memory({record['extents']['kernel-runtime'][0]},len(image)))==image, 'copied Image differs'
before={{n:reg(n) for n in ['cpsr','sp','x0','x1','x2','x3',sctlr_name]}}
pc_trace=[reg('pc')]
end
delete 1
stepi
python
pc_trace.append(reg('pc'))
assert reg('pc') in ({linked['park_pc']},{linked['park_pc']+4}), 'execution escaped fixed park'
end
stepi
python
pc_trace.append(reg('pc'))
assert reg('pc') in ({linked['park_pc']},{linked['park_pc']+4}), 'execution escaped fixed park'
assert before=={{n:reg(n) for n in before}}, 'park changed context'
assert bytes(gdb.selected_inferior().read_memory({marker.BASE},{marker.REGION}))==actual, 'park changed log bytes'
row=dict(actual_entry_el={el},final_el=(reg('cpsr')>>2)&3,case={name!r},park_pc={linked['park_pc']},
         record_mmu_state_reached=False,park_wait_observed=True,park_pc_trace=pc_trace,sctlr=sctlr,
         expected_frames_present={admitted},header_and_outside_slots_preserved=True,
         whole_actual_image_copied=True,register_state_modified=False)
open({str(work/'result.json')!r},'x').write(json.dumps(row,indent=2)+'\\n')
end
detach
quit
'''
        (work/'fixture.gdb').write_text(script)
        (work/'command.json').write_text(json.dumps(dict(qemu=command, gdb=str(gdb)), indent=2)+'\n')
        with (work/'qemu.stderr').open('xb') as err:
            proc = subprocess.Popen(command, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=err)
            try:
                with (work/'gdb.log').open('xb') as log:
                    check = subprocess.run([gdb, '-q', '-nx', '-batch', '-x', work/'fixture.gdb'],
                                           stdout=log, stderr=subprocess.STDOUT, timeout=90)
                require(check.returncode == 0 and (work/'result.json').is_file(), 'actual park fixture failed: '+str(work))
            finally:
                proc.terminate()
                try: proc.wait(timeout=5)
                except subprocess.TimeoutExpired: proc.kill(); proc.wait(timeout=5)
                sparse.unlink(missing_ok=True)
        # QEMU may append its termination message while the process stops.
        # Seal raw output only after both producers and their streams close.
        row = json.loads((work/'result.json').read_text())
        row['raw'] = [park.pin(work/n) for n in ('result.json','gdb.log','qemu.stderr','command.json','fixture.gdb','seed.bin','expected.bin','log-at-park.bin')]
        rows.append(row); print(json.dumps({k:v for k,v in row.items() if k!='raw'}), flush=True)
    require(park.pin(__file__) == source_ref and park.linked(record) == linked and
            park.pin(blob) == record['loader'], 'qualification input changed')
    result = dict(schema=park.QUALIFICATION, status=park.STATUS, loader=record['loader'],
                  linked=linked, checker=source_ref, qemu=park.pin(qemu), gdb=park.pin(gdb),
                  cases=rows, physical_entry_proved=False, physical_park_proved=False,
                  pid1_proved=False, device_actions=0)
    (output/'result.json').write_text(json.dumps(result, indent=2)+'\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('loader','gdb','output'): parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args(); qualify(args.loader, args.gdb, args.output)

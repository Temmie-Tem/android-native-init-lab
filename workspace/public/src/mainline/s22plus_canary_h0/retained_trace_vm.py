#!/usr/bin/env python3
"""Real-MMU, full-initcall trace fixtures with separate uninstrumented timings."""
import json
import os
from pathlib import Path
import socket
import struct
import subprocess

from prepare import ROOT, digest, require
from qualify_retained import symbols
from retained_kernel_vm import nomap_fixture, task_layout
import retained_trace as trace


def qualify(record, gdb, output):
    output.mkdir(mode=0o700, parents=True, exist_ok=False)
    artifact = record['mmu_on']; kernel = Path(artifact['kernel_path']); elf = Path(artifact['elf_path'])
    require(digest(kernel) == artifact['kernel_sha256'] and digest(elf) == artifact['elf_sha256'],
            'trace VM inputs changed')
    cfg = json.loads(Path(record['config']['path']).read_text())
    raw = kernel.read_bytes(); syms = symbols(elf); base = syms['_text']
    layout = task_layout(kernel, output / 'task-layout', artifact['layout_compiler'], artifact['layout_config_sha256'])
    offsets = layout['offsets']; initrd = artifact['mapping_initramfs']; initrd_path = Path(initrd['path'])
    require(initrd_path.stat().st_size == initrd['size'] and digest(initrd_path) == initrd['sha256'],
            'trace VM physical initramfs changed')
    switch = syms['__primary_switch'] - base
    branch = raw.index(struct.pack('<I', 0xd61f0100), switch, switch + 128)
    qroot = ROOT / 'workspace/private/tools/qemu-arm64-10.2.1/root'
    qemu = qroot / 'usr/bin/qemu-system-aarch64'
    env = dict(os.environ, LD_LIBRARY_PATH=str(qroot / 'usr/lib/x86_64-linux-gnu'))
    dtbs = {v: nomap_fixture(qemu, env, output, v, calibration=True) for v in ('off', 'on')}
    kernel_config = (kernel.parents[3] / '.config').read_text()
    va_bits = int(next(x.split('=')[1] for x in kernel_config.splitlines() if x.startswith('CONFIG_ARM64_VA_BITS=')))
    total = trace.event_count(cfg['initcall_count']); payload = trace.REGION - 16
    order = [0, 1, 2] + list(range(6, total)) + [3, 4, 5]
    middle = 6 + 2 * (cfg['initcall_count'] // 2)
    specs = [('normal-el1', 'off', payload + cfg['span'] + 300, 0x4d474f4c, 0, None, None, False),
             ('normal-el2', 'on', payload + cfg['span'] + 300, 0x4d474f4c, 0, None, None, False),
             ('page-crossing', 'on', payload + cfg['span'] + 4000, 0x4d474f4c, 0, None, None, False),
             ('short-history', 'on', 768, 0x4d474f4c, 0, None, None, False),
             ('bad-header', 'on', payload + cfg['span'] + 300, 0, 0, None, None, False),
             ('header-map-full', 'on', payload + cfg['span'] + 300, 0x4d474f4c, 1, None, None, False),
             ('slot-map-full', 'on', payload + cfg['span'] + 300, 0x4d474f4c, 2, None, None, False),
             ('drift-before', 'on', payload + cfg['span'] + 300, 0x4d474f4c, 0, 'before', 8, False),
             ('drift-commit', 'on', payload + cfg['span'] + 300, 0x4d474f4c, 0, 'commit', 12, False),
             ('timing-el1', 'off', payload + cfg['span'] + 300, 0x4d474f4c, 0, None, None, True),
             ('timing-el2', 'on', payload + cfg['span'] + 300, 0x4d474f4c, 0, None, None, True)]
    rows = []
    for label, virtual, idx, magic, fail, drift, changed_word, timing in specs:
        folder = output / label; folder.mkdir()
        sparse = folder / 'guest-ram.sparse'
        seed = folder / 'seed.bin'; seed.write_bytes(struct.pack('<IIII', 7, magic, idx, 123) + b'\xa5' * payload)
        span = min(idx, cfg['span']) // 128 * 128
        cursor = idx % payload; window = cursor - span if cursor >= span else payload - span
        expected = bytearray(seed.read_bytes()); disabled = False
        for event in order:
            if event == middle and drift:
                struct.pack_into('<I', expected, changed_word, 0x12345678)
                disabled = True
                if drift == 'commit':
                    frame = bytes.fromhex(cfg['frames'][str(event)])
                    expected[16 + window + event * 128:16 + window + (event + 1) * 128] = bytes(8) + frame[8:]
            if disabled or magic != 0x4d474f4c or (event + 1) * 128 > span or (event == 0 and fail):continue
            expected[16 + window + event * 128:16 + window + (event + 1) * 128] = bytes.fromhex(cfg['frames'][str(event)])
        expectation = folder / 'expected.bin'; expectation.write_bytes(expected)
        with socket.socket() as listener:listener.bind(('127.0.0.1', 0)); port = listener.getsockname()[1]
        command = [str(qemu), '-object', f'memory-backend-file,id=vmram,size=36G,mem-path={sparse},share=on,reserve=off,prealloc=off,dump=off',
                   '-nodefaults', '-machine', f'virt,memory-backend=vmram,virtualization={virtual},dtb-randomness=off',
                   '-cpu', 'cortex-a76', '-smp', '1', '-m', '36G', '-display', 'none', '-monitor', 'none',
                   '-serial', 'file:' + str(folder / 'serial.log'), '-no-reboot', '-S', '-gdb', f'tcp:127.0.0.1:{port}',
                   '-kernel', str(kernel), '-initrd', str(initrd_path), '-dtb', str(dtbs[virtual]),
                   '-device', f'loader,file={seed},addr={trace.BASE},force-raw=on']
        for side, address, byte in [('below', trace.BASE - 4096, 0x6c), ('above', trace.BASE + trace.REGION, 0x6d)]:
            sentinel = folder / (side + '.bin'); sentinel.write_bytes(bytes([byte]) * 4096)
            command += ['-device', f'loader,file={sentinel},addr={address},force-raw=on']
        script = f'''set pagination off
set confirm off
set architecture aarch64
set tcp auto-retry on
set tcp connect-timeout 10
target remote 127.0.0.1:{port}
python
import gdb,json,struct,time
inferior=gdb.selected_inferior()
def pointer(register):return int(gdb.parse_and_eval(register)) & ((1<<64)-1)
def at(address):
    b=gdb.Breakpoint('*%d'%address,type=gdb.BP_HARDWARE_BREAKPOINT,internal=True)
    gdb.execute('continue')
    assert pointer('$pc')==address, ('unexpected stop',hex(pointer('$pc')),hex(address))
    b.delete()
header=bytes.fromhex({raw[:64].hex()!r})
places=[a for a in (0x40000000,0x40080000,0x40200000) if bytes(inferior.read_memory(a,64))==header]
assert len(places)==1
physical=places[0]
at(physical+{branch})
delta=pointer('$x8')-{syms['__primary_switched']}
at({syms['kernel_init']}+delta)
init_thread_task=pointer('$SP_EL0')
def physical_read(address,length):
    assert 0x40000000<=address<=address+length<=0x940000000
    with open({str(sparse)!r},'rb') as f:
        f.seek(address-0x40000000);value=f.read(length)
    assert len(value)==length
    return value
def context():
    global active_root
    el=(pointer('$cpsr')>>2)&3
    assert el=={1 if virtual=='off' else 2}
    suffix='EL2' if el==2 else 'EL1'
    tcr=pointer('$TCR_'+suffix)
    assert ((tcr>>30)&3)==2 and ((tcr>>16)&63)==16 and not(tcr&(1<<59))
    if el==2:assert pointer('$HCR_EL2')&(1<<34)
    active_root=pointer('$TTBR1_'+suffix)&(((1<<48)-1)&~4095)
    return suffix
def translation(address):
    table=active_root
    for level,shift in enumerate((39,30,21,12)):
        descriptor=struct.unpack('<Q',physical_read(table+((address>>shift)&511)*8,8))[0]
        if not descriptor&1:return None,None
        if level==3 or descriptor&3==1:
            assert level in (1,2,3) and descriptor&3==(3 if level==3 else 1)
            span=(1<<shift)-1
            return ((descriptor&(((1<<48)-1)&~4095))&~span)|(address&span),descriptor
        assert descriptor&3==3
        table=descriptor&(((1<<48)-1)&~4095)
    raise AssertionError('unterminated translation')
def linear(physical):
    memstart=struct.unpack('<q',inferior.read_memory({syms['memstart_addr']}+delta,8))[0]
    return ((physical-memstart)|((-1<<{va_bits})&((1<<64)-1)))&((1<<64)-1)
alias_stages=[];attributes=[];contexts=[]
def no_alias(event):
    context()
    for address,byte in (({trace.BASE-4096},0x6c),({trace.BASE+trace.REGION},0x6d)):
        assert translation(linear(address))[0]==address
        assert bytes(inferior.read_memory(linear(address),1))==bytes([byte])
    for address in range({trace.BASE},{trace.BASE+trace.REGION},4096):
        assert translation(linear(address))[0] is None
    alias_stages.append(event)
def thread_context(event,phase):
    context()
    task=pointer('$SP_EL0')
    kthreadd=struct.unpack('<Q',inferior.read_memory({syms['kthreadd_task']}+delta,8))[0]
    reaper=struct.unpack('<Q',inferior.read_memory({syms['init_pid_ns']}+delta+{offsets['NS_CHILD_REAPER']},8))[0]
    def pid(address):return struct.unpack('<i',inferior.read_memory(address+{offsets['TSK_PID']},4))[0]
    assert task==init_thread_task==reaper and kthreadd and pid(task)==1
    assert pid({syms['init_task']}+delta)==0 and pid(kthreadd)==2
    count=struct.unpack('<I',inferior.read_memory(task+{offsets['TSK_TI_PREEMPT']},4))[0]
    cpu=struct.unpack('<I',inferior.read_memory(task+{offsets['TSK_TI_CPU']},4))[0]
    online=struct.unpack('<i',inferior.read_memory({syms['__num_online_cpus']}+delta,4))[0]
    state=struct.unpack('<i',inferior.read_memory({syms['system_state']}+delta,4))[0]
    late=struct.unpack('<i',inferior.read_memory({syms['after_paging_init']}+delta,4))[0]
    assert count==0 and cpu==0 and online==1 and state==1 and late==1 and not pointer('$cpsr')&(1<<7)
    contexts.append(dict(event=event,phase=phase,pid=1,initial_namespace_reaper=True,same_task_as_kernel_init_entry=True,
        init_task_pid=0,kthreadd_pid=2,boot_cpu=0,online_cpus=1,preempt_count_low32=0,irq_masked=False,system_state=1,late_selector=1))
def mapping_attributes(event):
    mapped=struct.unpack('<7Q',inferior.read_memory({syms['prev_map']}+delta,56))
    mair=pointer('$MAIR_'+context())
    slot={trace.BASE+16+window}+128*event
    for address,physical in ((mapped[0],{trace.BASE}),(mapped[0]+15,{trace.BASE+15}),(mapped[1],slot),(mapped[1]+127,slot+127)):
        actual,descriptor=translation(address)
        assert actual==physical
        assert (mair>>(((descriptor>>2)&7)*8))&255==0x44
        assert descriptor&(1<<53) and descriptor&(1<<54)
    attributes.append(event)
def cleared():
    context()
    for address in struct.unpack('<7Q',inferior.read_memory({syms['slot_virt']}+delta,56))[:2]:
        assert translation(address)[0] is None and translation(address+4096)[0] is None
def mutate(word):
    with open({str(sparse)!r},'r+b',buffering=0) as f:
        f.seek({trace.BASE-0x40000000}+word);f.write(struct.pack('<I',0x12345678))
counts=[0]*{total};order=[]
sample_events=[0,{middle},5]
class TraceCounter(gdb.Breakpoint):
    def stop(self):
        event=pointer('$x0')
        assert event<{total}
        counts[event]+=1;order.append(event)
        assert counts[event]==1, ('repeated event',event)
        return event in sample_events
elapsed=None
if {timing}:
    at({artifact['placement']['fixed_calls'][0]}+delta)
    no_alias(0);thread_context(0,'entry')
    t0=time.monotonic()
    at({artifact['placement']['final_return_pc']}+delta)
    elapsed=time.monotonic()-t0
    no_alias(5);thread_context(5,'return')
else:
    counter=TraceCounter('*%d'%({syms['s22_retained_trace']}+delta),type=gdb.BP_HARDWARE_BREAKPOINT,internal=True)
    for event in sample_events:
        gdb.execute('continue')
        assert pointer('$pc')=={syms['s22_retained_trace']}+delta and pointer('$x0')==event
        no_alias(event);thread_context(event,'entry')
        returned=pointer('$x30')
        prev={syms['prev_map']}+delta
        assert bytes(inferior.read_memory(prev,56))==bytes(56)
        occupied=([1]*7 if {fail}==1 else [0]+[1]*6) if event==0 and {bool(fail)} else [0]*7
        inferior.write_memory(prev,struct.pack('<7Q',*occupied))
        disabled=bytes(inferior.read_memory({syms['s22_trace_disabled']}+delta,1))!=bytes(1)
        if event=={middle} and {drift=='before'}:mutate({changed_word or 0});disabled=True
        eligible={magic==0x4d474f4c} and (event+1)*128<={span} and not disabled and not(event==0 and {bool(fail)})
        if eligible:
            at({syms['s22_retained_trace_recheck']}+delta)
            mapping_attributes(event)
            if event=={middle} and {drift=='commit'}:mutate({changed_word or 0})
        at(returned)
        assert bytes(inferior.read_memory(prev,56))==struct.pack('<7Q',*occupied)
        cleared();thread_context(event,'return')
        inferior.write_memory(prev,bytes(56))
    counter.delete()
    assert counts==[1]*{total} and order=={order!r}, 'complete traversal count/order differs'
    assert pointer('$pc')=={artifact['placement']['final_return_pc']}+delta
assert bytes(inferior.read_memory({syms['prev_map']}+delta,56))==bytes(56)
cleared()
actual=physical_read({trace.BASE},{trace.REGION})
open({str(folder/'observed.bin')!r},'xb').write(actual)
assert actual==open({str(expectation)!r},'rb').read(), 'complete trace/header/outside-window bytes differ'
disabled=bytes(inferior.read_memory({syms['s22_trace_disabled']}+delta,1))!=bytes(1)
assert disabled=={bool(drift)}
result=dict(case={label!r},actual_c_el={1 if virtual=='off' else 2},real_mmu_boot=True,real_mapping_api=True,
    full_pre_free_init_traversal=True,terminal_pc=pointer('$pc'),mapping_slots_restored=True,
    header_and_outside_window_preserved=True,post_paging_no_linear_alias_proved=True,
    no_linear_alias_events=alias_stages,temporary_mapping_attribute_events=attributes,
    init_thread_contexts=contexts,per_event_counts=counts if not {timing} else None,
    event_order=order if not {timing} else None,counter_breakpoints_used={not timing},
    wall_seconds_between_boundaries=elapsed,physical_timing_proved=False,guest_counter_status='not sampled')
open({str(folder/'result.json')!r},'x').write(json.dumps(result,indent=2)+'\\n')
end
detach
quit
'''
        (folder / 'fixture.gdb').write_text(script)
        (folder / 'command.json').write_text(json.dumps(dict(qemu=command, gdb=str(gdb)), indent=2) + '\n')
        with (folder / 'qemu.stderr').open('xb') as err:
            proc = subprocess.Popen(command, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=err)
            try:
                with (folder / 'gdb.log').open('xb') as log:
                    check = subprocess.run([str(gdb), '-q', '-nx', '-batch', '-x', str(folder / 'fixture.gdb')],
                                           stdout=log, stderr=subprocess.STDOUT, timeout=60)
                require(check.returncode == 0 and (folder / 'result.json').is_file(), 'trace MMU fixture failed: ' + str(folder))
                rows.append(json.loads((folder / 'result.json').read_text()))
            finally:
                proc.terminate()
                try:proc.wait(timeout=5)
                except subprocess.TimeoutExpired:proc.kill();proc.wait(timeout=5)
                if sparse.exists():sparse.unlink()
    require(digest(kernel) == artifact['kernel_sha256'] and digest(initrd_path) == initrd['sha256'],
            'trace VM inputs changed during qualification')
    result = dict(status='PASS_H0_ACTUAL_KERNEL_MMU_INITCALL_TRACE', kernel_sha256=digest(kernel),
                  source_sha256=digest(__file__), qemu_sha256=digest(qemu), gdb_sha256=digest(gdb),
                  cases=rows, declared_slots=total, declared_span=cfg['span'],
                  post_paging_no_linear_alias_proved=True, late_fixmap_proved=True,
                  init_thread_context_proved=True, task_layout=layout, mapping_initramfs=initrd,
                  fixture_dtbs={k:dict(path=str(v),sha256=digest(v)) for k,v in dtbs.items()},
                  cache_coherency_proved=False, physical_retention_proved=False, device_actions=0)
    (output / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    return result

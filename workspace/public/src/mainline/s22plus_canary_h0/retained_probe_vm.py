#!/usr/bin/env python3
"""Real-MMU PID1/kworker probe fixtures; timing runs exclude counter stops."""
import json
import os
from pathlib import Path
import socket
import struct
import subprocess

from prepare import ROOT, digest, require
from qualify_retained import symbols
from retained_kernel_vm import nomap_fixture, task_layout
import retained_probe as trace
import retained_probe_v10 as priority
from prepare import nodes


def probe_dtb(qemu, env, output, virtual, paths):
    original = nomap_fixture(qemu, env, output, virtual, calibration=True)
    current = nodes(original)
    existing = {'/'}
    for path in current:
        while True:
            existing.add(path)
            if path == '/': break
            path = path.rsplit('/', 1)[0] or '/'
    tree = {}
    for path in paths:
        cursor = tree
        for component in path.strip('/').split('/') if path != '/' else []:
            cursor = cursor.setdefault(component, {})
    def render(branch, prefix=''):
        result = []
        for name, children in sorted(branch.items()):
            path = prefix + '/' + name
            result.append(name + ' {')
            if path not in existing: result.append('status = "disabled";')
            result.append(render(children, path))
            result.append('};')
        return '\n'.join(result)
    source = output / ('probe-' + virtual + '.dts')
    final = source.with_suffix('.dtb')
    with (output / ('probe-' + virtual + '-dtc.log')).open('xb') as log:
        subprocess.run(['dtc','-I','dtb','-O','dts','-o',str(source),str(original)],stdout=log,stderr=subprocess.STDOUT,check=True)
        with source.open('a') as stream: stream.write('\n/ {\n' + render(tree) + '\n};\n')
        subprocess.run(['dtc','-I','dts','-O','dtb','-o',str(final),str(source)],stdout=log,stderr=subprocess.STDOUT,check=True)
    after = nodes(final)
    for path, properties in current.items():
        require(after[path] == properties, 'catalog fixture changed an existing QEMU node')
    require(all(after[p].get('status') == b'disabled\0' for p in paths if p not in existing),
            'new catalog fixture node was not disabled')
    return final


def qualify(record, gdb, output):
    output.mkdir(mode=0o700, parents=True, exist_ok=False)
    artifact = record['mmu_on']; kernel = Path(artifact['kernel_path']); elf = Path(artifact['elf_path'])
    require(digest(kernel) == artifact['kernel_sha256'] and digest(elf) == artifact['elf_sha256'],
            'trace VM inputs changed')
    cfg = json.loads(Path(record['config']['path']).read_text())
    is_v10 = cfg['schema'] == priority.SCHEMA
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
    dtbs = {v: probe_dtb(qemu, env, output, v, cfg['node_paths']) for v in ('off', 'on')}
    kernel_config = (kernel.parents[3] / '.config').read_text()
    va_bits = int(next(x.split('=')[1] for x in kernel_config.splitlines() if x.startswith('CONFIG_ARM64_VA_BITS=')))
    total = len(cfg['frames']); payload = trace.REGION - 16
    fixed_count = len(priority.FIXED) if is_v10 else 20
    sparse_base = priority.SPARSE_BASE if is_v10 else 20
    mandatory = list(range(fixed_count)) + list(range(sparse_base, sparse_base + 2 * len(cfg['initcall_ordinals'])))
    middle = priority.FIXED.index('phase-1-worker-enter') if is_v10 else 16
    first_late = priority.FIXED.index('pre-basic-setup') if is_v10 else 0
    final_event = priority.FIXED.index('post-async-sync') if is_v10 else 5
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
    if is_v10:
        specs += [('earliest-only-short-history', 'on', 128, 0x4d474f4c, 0, None, None, False),
                  ('early-drift-before', 'on', payload + cfg['span'] + 300, 0x4d474f4c, 0, 'before', 0, False),
                  ('early-drift-commit', 'on', payload + cfg['span'] + 300, 0x4d474f4c, 0, 'commit', 4, False)]
    rows = []
    for label, virtual, idx, magic, fail, drift, changed_word, timing in specs:
        drift_event = 1 if label.startswith('early-drift-') else middle
        sampled = ([0, 1] if is_v10 else []) + [first_late, middle, final_event]
        if drift:
            sampled = sampled[:sampled.index(drift_event) + 1]
        folder = output / label; folder.mkdir()
        sparse = folder / 'guest-ram.sparse'
        seed = folder / 'seed.bin'; seed.write_bytes(struct.pack('<IIII', 7, magic, idx, 123) + b'\xa5' * payload)
        span = min(idx, cfg['span']) // 128 * 128
        cursor = idx % payload; window = cursor - span if cursor >= span else payload - span
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
def read_fdt(address):
    magic,length=struct.unpack('>II',inferior.read_memory(address,8))
    assert magic==0xd00dfeed and 40<=length<=2097152
    return bytes(inferior.read_memory(address,length))
def fdt_paths(blob):
    pos=struct.unpack_from('>I',blob,8)[0];stack=[];paths=set()
    while pos<len(blob):
        token=struct.unpack_from('>I',blob,pos)[0];pos+=4
        if token==1:
            end=blob.index(bytes(1),pos);name=blob[pos:end].decode('ascii');pos=(end+4)&~3
            stack.append(name);paths.add('/'+'/'.join(stack[1:]))
        elif token==2:stack.pop()
        elif token==3:
            length=struct.unpack_from('>I',blob,pos)[0];pos=(pos+8+length+3)&~3
        elif token==4:pass
        elif token==9:
            assert not stack
            return paths
        else:raise AssertionError(('bad FDT token',token))
    raise AssertionError('FDT has no end')
boot_blob=read_fdt(pointer('$x21'))
open({str(folder/'entry-fixture.dtb')!r},'xb').write(boot_blob)
boot_paths=fdt_paths(boot_blob)
catalog_missing=[p for p in {cfg['node_paths']!r} if p not in boot_paths]
assert all(p.startswith('/memory@') and p.count('/')==1 for p in catalog_missing), catalog_missing
delta=pointer('$x8')-{syms['__primary_switched']}
init_thread_task=None
if {not is_v10 or timing}:
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
alias_stages=[];attributes=[];contexts=[];bootstrap_returns=[]
early_table_roots=[]
def early_no_alias():
    suffix=context()
    tcr=pointer('$TCR_'+suffix)
    assert (tcr&63)==16 and ((tcr>>14)&3)==0, ('lower-root geometry',hex(tcr))
    roots=[pointer('$TTBR0_'+suffix),pointer('$TTBR1_'+suffix)]
    seen=set()
    def walk(table,level):
        table &= ((1<<48)-1)&~4095
        if (table,level) in seen:return
        seen.add((table,level))
        assert len(seen)<4096
        for descriptor in struct.unpack('<512Q',physical_read(table,4096)):
            if not descriptor&1:continue
            if level==3 or descriptor&3==1:
                assert level in (1,2,3) and descriptor&3==(3 if level==3 else 1)
                span=1<<(39-9*level)
                start=(descriptor&(((1<<48)-1)&~4095))&~(span-1)
                assert start+span<={trace.BASE} or start>={trace.BASE+trace.REGION}, ('early alias',hex(start),span)
            else:
                assert descriptor&3==3 and level<3
                walk(descriptor,level+1)
    for root in roots:walk(root,0)
    early_table_roots.append(dict(roots=roots,tcr=tcr,lower_t0sz=16,lower_tg0=0,walked_tables=len(seen)))
def no_alias(event):
    context()
    if {is_v10} and event==0:
        early_no_alias();alias_stages.append(event);return
    for address,byte in (({trace.BASE-4096},0x6c),({trace.BASE+trace.REGION},0x6d)):
        assert translation(linear(address))[0]==address
        assert bytes(inferior.read_memory(linear(address),1))==bytes([byte])
    for address in range({trace.BASE},{trace.BASE+trace.REGION},4096):
        assert translation(linear(address))[0] is None
    alias_stages.append(event)
def thread_context(event,phase):
    context()
    task=pointer('$SP_EL0')
    if {is_v10} and event in (0,1):
        assert task=={syms['init_task']}+delta
        count=struct.unpack('<I',inferior.read_memory(task+{offsets['TSK_TI_PREEMPT']},4))[0]
        cpu=struct.unpack('<I',inferior.read_memory(task+{offsets['TSK_TI_CPU']},4))[0]
        pid=struct.unpack('<i',inferior.read_memory(task+{offsets['TSK_PID']},4))[0]
        online=struct.unpack('<i',inferior.read_memory({syms['__num_online_cpus']}+delta,4))[0]
        state=struct.unpack('<i',inferior.read_memory({syms['system_state']}+delta,4))[0]
        late=struct.unpack('<i',inferior.read_memory({syms['after_paging_init']}+delta,4))[0]
        assert (pid,cpu,online,state,late,count)==(0,0,1,0,event,2), ('bootstrap',event,pid,cpu,online,state,late,count)
        assert pointer('$cpsr')&(1<<7)
        contexts.append(dict(event=event,phase=phase,pid=0,initial_task=True,boot_cpu=0,online_cpus=1,
            preempt_count_low32=count,irq_masked=True,system_state=state,late_selector=late))
        return
    kthreadd=struct.unpack('<Q',inferior.read_memory({syms['kthreadd_task']}+delta,8))[0]
    reaper=struct.unpack('<Q',inferior.read_memory({syms['init_pid_ns']}+delta+{offsets['NS_CHILD_REAPER']},8))[0]
    def pid(address):return struct.unpack('<i',inferior.read_memory(address+{offsets['TSK_PID']},4))[0]
    assert reaper==init_thread_task and kthreadd
    if event=={middle}:
        assert task not in (init_thread_task,kthreadd,{syms['init_task']}+delta) and pid(task)>2
    else:
        assert task==init_thread_task and pid(task)==1
    assert pid({syms['init_task']}+delta)==0 and pid(kthreadd)==2
    count=struct.unpack('<I',inferior.read_memory(task+{offsets['TSK_TI_PREEMPT']},4))[0]
    cpu=struct.unpack('<I',inferior.read_memory(task+{offsets['TSK_TI_CPU']},4))[0]
    online=struct.unpack('<i',inferior.read_memory({syms['__num_online_cpus']}+delta,4))[0]
    state=struct.unpack('<i',inferior.read_memory({syms['system_state']}+delta,4))[0]
    late=struct.unpack('<i',inferior.read_memory({syms['after_paging_init']}+delta,4))[0]
    wanted_count=0 if phase.endswith('timing') else 1
    assert count==wanted_count and cpu==0 and online==1 and state==1 and late==1 and not pointer('$cpsr')&(1<<7), (event,phase,pid(task),count,wanted_count,cpu,online,state,late,hex(pointer('$cpsr')))
    contexts.append(dict(event=event,phase=phase,pid=pid(task),initial_namespace_reaper=task==reaper,same_task_as_kernel_init_entry=task==init_thread_task,
        init_task_pid=0,kthreadd_pid=2,boot_cpu=0,online_cpus=1,preempt_count_low32=count,irq_masked=False,system_state=1,late_selector=1))
def mapping_attributes(event):
    mapped=struct.unpack('<7Q',inferior.read_memory({syms['prev_map']}+delta,56))
    mair=pointer('$MAIR_'+context())
    slot={trace.BASE+16+window}+({span}-(event+1)*128 if {is_v10} else 128*event)
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
sample_events={sampled!r}
class TraceCounter(gdb.Breakpoint):
    def stop(self):
        event=pointer('$x0')
        assert event<{total}
        counts[event]+=1;order.append(event)
        assert counts[event]==1, ('repeated event',event)
        return event in sample_events
elapsed=None
if {timing}:
    at({artifact['placement']['prepare_call']}+delta)
    no_alias({first_late});thread_context({first_late},'entry-timing')
    t0=time.monotonic()
    at({artifact['placement']['final_return_pc']}+delta)
    elapsed=time.monotonic()-t0
    no_alias({final_event});thread_context({final_event},'return-timing')
else:
    counter=TraceCounter('*%d'%({syms['s22_retained_probe_write']}+delta),type=gdb.BP_HARDWARE_BREAKPOINT,internal=True)
    for event in sample_events:
        gdb.execute('continue')
        assert pointer('$pc')=={syms['s22_retained_probe_write']}+delta and pointer('$x0')==event, ('sample',event,hex(pointer('$pc')),pointer('$x0'))
        no_alias(event);thread_context(event,'entry')
        if event=={first_late}:
            live_fdt=struct.unpack('<Q',inferior.read_memory({syms['initial_boot_params']}+delta,8))[0]
            fdt_magic,fdt_size=struct.unpack('>II',inferior.read_memory(live_fdt,8))
            assert fdt_magic==0xd00dfeed and 40<=fdt_size<=2097152
            open({str(folder/'live-fixture.dtb')!r},'xb').write(bytes(inferior.read_memory(live_fdt,fdt_size)))
            node_pointers=struct.unpack('<{len(cfg['node_paths'])}Q',inferior.read_memory({syms['s22_probe_nodes']}+delta,{8*len(cfg['node_paths'])}))
            assert all(bool(v)==(p in boot_paths) for p,v in zip({cfg['node_paths']!r},node_pointers)), ('catalog lookup',[i for i,v in enumerate(node_pointers) if not v])
            assert len(set(v for v in node_pointers if v))==sum(bool(v) for v in node_pointers)
        returned=pointer('$x30')
        # Advance the stopped instruction before changing the breakpoint set.
        # A repeated stop at the same instruction is not a second invocation;
        # real later re-entry still reaches the enabled counter and fails its
        # unchanged once-per-event assertion. No PC/register value is injected.
        entry_pc=pointer('$pc')
        counter.enabled=False
        gdb.execute('stepi')
        assert pointer('$pc')==entry_pc+4, ('writer entry did not advance',hex(pointer('$pc')))
        counter.enabled=True
        prev={syms['prev_map']}+delta
        assert bytes(inferior.read_memory(prev,56))==bytes(56)
        occupied=([1]*7 if {fail}==1 else [0]+[1]*6) if event==0 and {bool(fail)} else [0]*7
        inferior.write_memory(prev,struct.pack('<7Q',*occupied))
        disabled=bytes(inferior.read_memory({syms['s22_probe_disabled']}+delta,1))!=bytes(1)
        if event=={drift_event} and {drift=='before'}:mutate({changed_word or 0});disabled=True
        eligible={magic==0x4d474f4c} and (event+1)*128<={span} and not disabled and not(event==0 and {bool(fail)})
        if eligible:
            at({syms['s22_retained_probe_recheck']}+delta)
            mapping_attributes(event)
            if event=={drift_event} and {drift=='commit'}:mutate({changed_word or 0})
        at(returned)
        assert bytes(inferior.read_memory(prev,56))==struct.pack('<7Q',*occupied)
        cleared();thread_context(event,'return')
        inferior.write_memory(prev,bytes(56))
        if {is_v10} and event in (0,1):
            caller_return=({artifact['placement'].get('early_c_call', 0)} if event==0 else {artifact['placement'].get('post_setup_call', 0)})+delta+4
            at(caller_return)
            task=pointer('$SP_EL0')
            count=struct.unpack('<I',inferior.read_memory(task+{offsets['TSK_TI_PREEMPT']},4))[0]
            assert task=={syms['init_task']}+delta and count==1 and pointer('$cpsr')&(1<<7)
            bootstrap_returns.append(dict(event=event,initial_task=True,preempt_count_low32=count,irq_masked=True))
        if {is_v10} and event==1 and not {label.startswith('early-drift-')}:
            at({syms['kernel_init']}+delta)
            init_thread_task=pointer('$SP_EL0')
    counter.delete()
    at({artifact['placement']['final_return_pc']}+delta)
    if not {bool(drift)}:
        assert all(counts[e]==1 for e in {mandatory!r}), 'required body/worker/sparse events missing'
        assert [e for e in order if {sparse_base}<=e<{sparse_base+2*len(cfg['initcall_ordinals'])}]==list(range({sparse_base},{sparse_base+2*len(cfg['initcall_ordinals'])})), 'sparse initcall order differs'
    else:
        assert counts[{drift_event}]==1 and not any(counts[e] for e in ({final_event-2},{final_event-1},{final_event})), 'drift continued writes'
    assert all(n<=1 for n in counts), 'duplicate write attempt'
assert bytes(inferior.read_memory({syms['prev_map']}+delta,56))==bytes(56)
cleared()
actual=physical_read({trace.BASE},{trace.REGION})
open({str(folder/'observed.bin')!r},'xb').write(actual)
frames=json.load(open({str(Path(record['config']['path']))!r}))['frames']
expected=bytearray(open({str(seed)!r},'rb').read())
if {timing}:
    order=[]
    for event in range({total}):
        off=16+{window}+({span}-(event+1)*128 if {is_v10} else 128*event)
        if actual[off:off+128]==bytes.fromhex(frames[str(event)]):order.append(event)
    assert all(event in order for event in {mandatory!r})
sticky=False
for event in order:
    if event=={drift_event} and {bool(drift)}:
        struct.pack_into('<I',expected,{changed_word or 0},0x12345678)
        sticky=True
        if {drift=='commit'}:
            off=16+{window}+({span}-(event+1)*128 if {is_v10} else 128*event)
            expected[off:off+128]=bytes(8)+bytes.fromhex(frames[str(event)])[8:]
    if sticky or {magic!=0x4d474f4c} or (event+1)*128>{span} or (event==0 and {bool(fail)}):continue
    off=16+{window}+({span}-(event+1)*128 if {is_v10} else 128*event)
    expected[off:off+128]=bytes.fromhex(frames[str(event)])
open({str(folder/'expected.bin')!r},'xb').write(expected)
assert actual==expected, 'complete probe/header/outside-window bytes differ'
assert bytes(inferior.read_memory({syms['s22_probe_dispatch']}+delta,8))==bytes(8)
assert bytes(inferior.read_memory({syms['s22_probe_nodes']}+delta,{8*len(cfg['node_paths'])}))==bytes({8*len(cfg['node_paths'])})
disabled=bytes(inferior.read_memory({syms['s22_probe_disabled']}+delta,1))!=bytes(1)
assert disabled=={bool(drift)}
result=dict(case={label!r},actual_c_el={1 if virtual=='off' else 2},real_mmu_boot=True,real_mapping_api=True,
    full_pre_free_init_traversal=True,worker_dispatch_closed=True,catalog_refs_released=True,fixture_catalog_resolved=None if {timing or label.startswith('early-drift-')} else {len(cfg['node_paths'])}-len(catalog_missing),catalog_lookup_checked={not timing and not label.startswith('early-drift-')},fixture_catalog_unresolved=catalog_missing,incoming_fdt_captured_before_c_setup=True,terminal_pc=pointer('$pc'),mapping_slots_restored=True,
    header_and_outside_window_preserved=True,post_paging_no_linear_alias_proved=True,
    no_linear_alias_events=alias_stages,temporary_mapping_attribute_events=attributes,
    writer_contexts=contexts,bootstrap_mark_returns=bootstrap_returns,early_no_alias_page_tables=early_table_roots,per_event_counts=counts if not {timing} else None,
    event_order=order if not {timing} else None,counter_breakpoints_used={not timing},
    wall_seconds_between_boundaries=elapsed,timing_window='preparation-to-final-pre-free',physical_timing_proved=False,guest_counter_status='not sampled')
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
    result = dict(status='PASS_H0_ACTUAL_KERNEL_MMU_DEFERRED_PROBE', kernel_sha256=digest(kernel),
                  source_sha256=digest(__file__), qemu_sha256=digest(qemu), gdb_sha256=digest(gdb),
                  cases=rows, declared_slots=total, declared_span=cfg['span'],
                  post_paging_no_linear_alias_proved=True, late_fixmap_proved=True,
                  pid1_and_worker_context_proved=True, task_layout=layout, mapping_initramfs=initrd,
                  fixture_dtbs={k:dict(path=str(v),sha256=digest(v)) for k,v in dtbs.items()},
                  cache_coherency_proved=False, physical_retention_proved=False, device_actions=0)
    (output / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    return result

#!/usr/bin/env python3
"""Final ELF identity and actual ARM64 bounded-writer/dispatch fixtures."""
import json
from pathlib import Path
import struct
import subprocess

from elftools.elf.elffile import ELFFile
from unicorn import arm64_const as regs
from prepare import digest, nodes, require
from qualify_retained import symbols
from qualify_retained_trace import Machine as TraceMachine, pin
import retained_probe as probe


def inventory(image, elf, config, dtb):
    raw = image.read_bytes(); syms = symbols(elf)
    with elf.open('rb') as stream:
        entries = [(s.name, s['st_value'], s['st_size'], s['st_info']['type'])
                   for s in ELFFile(stream).get_section_by_name('.symtab').iter_symbols()]
    sizes = {name: size for name, _, size, _ in entries}; funcs = {}
    for name, address, _, kind in entries:
        if kind == 'STT_FUNC': funcs.setdefault(address, []).append(name)
    boundaries = [syms['__initcall' + str(i) + '_start'] for i in range(8)] + [syms['__initcall_end']]
    require(all(a < b and (b - a) % 4 == 0 for a, b in zip(boundaries, boundaries[1:])) and
            boundaries[-1] - boundaries[0] == 4 * config['initcall_count'], 'fresh PREL32 table differs')
    require(sizes['initcall_levels'] == 72 and
            list(struct.unpack_from('<9Q', raw, syms['initcall_levels'] - syms['_text'])) == boundaries,
            'actual level array differs')
    rows = []
    for level, (start, end) in enumerate(zip(boundaries, boundaries[1:])):
        for address in range(start, end, 4):
            target = address + struct.unpack_from('<i', raw, address - syms['_text'])[0]
            require(target in funcs, 'final initcall has no exact function symbol')
            rows.append(dict(ordinal=(address - boundaries[0]) // 4, level=level,
                             entry_address=address, target_address=target, functions=sorted(funcs[target])))
    matches = [r['ordinal'] for r in rows if 'boot_wait_for_devices' in r['functions']]
    require(len(matches) == 1, 'sparse tail anchor ambiguous')
    first = matches[0]
    require('sync_state_resume_initcall' in rows[first + 1]['functions'] and
            'deferred_probe_initcall' in rows[first + 2]['functions'], 'tail source function order differs')
    selected = sorted({(a - boundaries[0]) // 4 for a in boundaries[:-1]} | set(range(first, len(rows))))
    require(config['initcall_ordinals'] == selected, 'sparse ordinals are not the fresh final table selection')
    ordinal_bytes = struct.pack('<' + str(len(selected)) + 'I', *selected)
    require(sizes['s22_probe_ordinals'] == len(ordinal_bytes) and
            raw[syms['s22_probe_ordinals'] - syms['_text']:syms['s22_probe_ordinals'] - syms['_text'] + len(ordinal_bytes)] == ordinal_bytes,
            'actual ordinal selection array differs')
    require(config['node_paths'] == probe.catalog(nodes(dtb)), 'node catalog is not derived from exact DTB')
    pointers = struct.unpack_from('<' + str(len(config['node_paths'])) + 'Q', raw, syms['s22_probe_paths'] - syms['_text'])
    require(sizes['s22_probe_paths'] == len(pointers) * 8, 'linked path table size differs')
    for pointer, path in zip(pointers, config['node_paths']):
        offset = pointer - syms['_text']; encoded = path.encode() + b'\0'
        require(0 <= offset <= len(raw) - len(encoded) and raw[offset:offset + len(encoded)] == encoded,
                'actual linked OF path differs')
    frames = b''.join(bytes.fromhex(config['frames'][str(i)]) for i in range(len(config['frames'])))
    offset = syms['s22_probe_frames'] - syms['_text']
    require(sizes['s22_probe_frames'] == len(frames) and raw[offset:offset + len(frames)] == frames,
            'actual probe frame array differs')
    init_names = ['s22_probe_' + n for n in ('frames', 'paths', 'ordinals', 'nodes', 'seen', 'owner',
                  'header', 'window', 'span', 'phase', 'latched', 'disabled', 'armed', 'prepared', 'handle')]
    init_names += ['s22_retained_probe_' + n for n in ('write', 'mark', 'prepare', 'finish', 'initcall')]
    init_names += ['prev_map', 'prev_size', 'slot_virt', 'after_paging_init']
    require(all(syms['__init_begin'] <= syms[name] < syms['__init_end'] for name in init_names),
            'probe init lifetime extent differs')
    require(all(not syms['__init_begin'] <= syms[n] < syms['__init_end']
                for n in ('s22_probe_hook', 's22_probe_dispatch')), 'persistent gate is in init memory')
    return dict(schema='s22plus-mainline-probe-table-v9', status='PASS_H0_FINAL_PROBE_TABLE',
                image=pin(image), elf=pin(elf), dtb=pin(dtb), regular_count=len(rows),
                counts_by_level=[(b-a)//4 for a,b in zip(boundaries,boundaries[1:])],
                entries=rows, boundaries=boundaries, selected_ordinals=selected,
                node_paths=config['node_paths'], frame_array_matches=True,
                init_lifetime_symbols=init_names, persistent_gate_symbols=['s22_probe_hook','s22_probe_dispatch'],
                device_actions=0), syms, sizes


def placement(raw, syms, sizes):
    def word(pc): return struct.unpack_from('<I', raw, pc - syms['_text'])[0]
    def calls(name):
        result = []
        for pc in range(syms[name], syms[name] + sizes[name], 4):
            v = word(pc)
            if v >> 26 != 0b100101: continue
            n = v & 0x3ffffff
            if n & (1 << 25): n -= 1 << 26
            result.append((pc, pc + 4 * n))
        return result
    def unique(rows, name):
        pcs = [pc for pc, target in rows if target == syms[name]]
        require(len(pcs) == 1, 'linked call count differs: ' + name)
        return pcs[0]
    freeable = calls('kernel_init_freeable'); parent = calls('kernel_init')
    direct = [pc for pc, target in freeable if target == syms['s22_retained_probe_mark']]
    tail = unique(parent, 's22_retained_probe_mark')
    require(len(direct) == 5 and all(word(pc - 4) == 0x52800000 | (i << 5) for i,pc in enumerate(direct)) and
            word(tail - 4) == 0x528000a0, 'fixed probe milestone arguments differ')
    prepare = unique(freeable, 's22_retained_probe_prepare')
    finish = unique(parent, 's22_retained_probe_finish')
    wrappers = [pc for pc,t in freeable if t == syms['s22_retained_probe_initcall']]
    dispatches = [pc for pc,t in freeable if t == syms['do_one_initcall']]
    require(len(wrappers) == len(dispatches) == 2 and
            dispatches[0] < prepare < direct[0] < direct[2] < wrappers[0] < dispatches[1] < wrappers[1] < direct[3],
            'sparse loop wrapper or untouched early traversal differs')
    require(unique(freeable,'page_alloc_init_late') < prepare < direct[0] < unique(freeable,'cpuset_init_smp') and
            unique(freeable,'driver_init') < direct[1] < unique(freeable,'init_irq_proc') and
            unique(freeable,'kfree') < direct[3] < unique(freeable,'wait_for_initramfs') < direct[4],
            'fixed source boundary order differs')
    require(unique(parent,'async_synchronize_full') < tail < finish < unique(parent,'free_initmem'),
            'finish does not precede actual init freeing')
    # The compiler's complete dd CFG is retained for independent review; the
    # guarded actual-code fixtures exercise its dispatch implementation too.
    require(any(t == syms['s22_probe_hook'] for _,t in calls('deferred_probe_initcall')) and
            any(t == syms['s22_probe_hook'] for _,t in calls('deferred_probe_work_func')),
            'deferred body/worker lacks persistent hook')
    return dict(fixed_calls=direct+[tail], prepare_call=prepare, finish_call=finish,
                final_return_pc=finish+4, initcall_wrapper_calls=wrappers,
                early_dispatch_call=dispatches[0], regular_dispatch_call=dispatches[1],
                init_memory_free_call=unique(parent,'free_initmem'))


class Machine(TraceMachine):
    """Reuse the V8 instruction engine; V9 state and function labels are explicit."""
    def __init__(self, raw, syms, sizes, config, idx, magic=0x4d474f4c):
        aliases = {'s22_retained_trace':'s22_retained_probe_write',
                   's22_retained_trace_recheck':'s22_retained_probe_recheck',
                   's22_retained_initcall':'s22_retained_probe_initcall'}
        aliases.update({'s22_trace_'+s:'s22_probe_'+s for s in ('header','window','span','latched','disabled')})
        names = dict(syms); lengths = dict(sizes)
        for old,new in aliases.items():
            names[old] = syms[new]
            if new in sizes: lengths[old] = sizes[new]
        super().__init__(raw,names,lengths,config,idx,magic)
        self.state_ranges.append((syms['s22_probe_seen'],syms['s22_probe_seen']+sizes['s22_probe_seen']))


def qualify(record, config, output):
    output.mkdir(mode=0o700,parents=True,exist_ok=False)
    image=Path(record['kernel']['image']);elf=image.parents[3]/'vmlinux'
    require(digest(image)==record['kernel']['sha256'],'probe kernel changed')
    manifest=json.loads(Path(record['initramfs_manifest']).read_text())
    dtb=Path(manifest['dtb']['path'])
    require(set(manifest['dtb'])=={'path','sha256'} and digest(dtb)==manifest['dtb']['sha256'],
            'probe DTB changed')
    table,syms,sizes=inventory(image,elf,config,dtb)
    (output/'initcall-table.json').write_text(json.dumps(table,indent=2)+'\n')
    raw=image.read_bytes();sites=placement(raw,syms,sizes)
    names=('kernel_init_freeable','kernel_init','deferred_probe_initcall','deferred_probe_work_func',
           'really_probe','call_driver_probe','s22_probe_hook','s22_probe_handle',
           's22_retained_probe_write','s22_retained_probe_prepare','s22_retained_probe_finish',
           's22_retained_probe_initcall','__set_fixmap')
    for name in names:
        text=subprocess.check_output(['aarch64-linux-gnu-objdump','-d','--disassemble='+name,elf],text=True)
        (output/(name+'.txt')).write_text(text)
        if name=='s22_retained_probe_write':
            require(all(t in text for t in ('paciasp','autiasp','__stack_chk_fail')),'probe writer protections lost')
        if name=='__set_fixmap':require(all(t in text for t in ('tlbi','dsb','isb')),'fixmap barriers lost')
    total=len(config['frames']);payload=probe.REGION-16;rows=[]
    def exercise(event=0,idx=payload+config['span']+300,magic=0x4d474f4c,**kwargs):
        m=Machine(raw,syms,sizes,config,idx,magic);after=m.run(event,**kwargs);expected=bytearray(m.before)
        eligible=(0<=event<total and kwargs.get('el',1) in (1,2) and
                  kwargs.get('state',1)&0x2000001==1 and magic==0x4d474f4c and
                  (event+1)*128<=m.span and not kwargs.get('fail'))
        offset=m.target_slot-probe.BASE
        if kwargs.get('cut') is not None:
            require(after[:offset]==expected[:offset] and after[offset+128:]==expected[offset+128:] and
                    after[offset:offset+128]!=bytes.fromhex(config['frames'][str(event)]),'torn probe frame escaped/committed')
        else:
            if eligible:
                frame=bytes.fromhex(config['frames'][str(event)])
                expected[offset:offset+128]=frame if kwargs.get('change') is None else bytes(8)+frame[8:]
                if kwargs.get('change') is not None:struct.pack_into('<I',expected,kwargs['change'],0x12345678)
            require(after==expected,'actual probe bytes/header/outside-window differ')
            if not eligible:require(not m.writes,'ineligible probe wrote payload')
        rows.append(dict(event=event,idx=idx,**kwargs,slot_writes=len(m.writes),map_calls=len(m.calls)))
    for event in (0,5,20+2*len(config['initcall_ordinals']),total//2,total-1):
        for idx in (0,127,128,255,768,config['span']-1,config['span'],payload-1,payload,payload+1,
                    payload+config['span']+4196,0xffffffff): exercise(event,idx)
    for el in (0,2,3):exercise(el=el)
    for state in (0,4,5,1|(1<<25)):exercise(state=state)
    exercise(magic=0)
    for fail in (1,2):exercise(fail=fail)
    for event in (0,total-1):
        for change in (0,4,8,12):exercise(event=event,change=change)
        for cut in range(1,136):exercise(event=event,cut=cut)
    for event in (total,0xffffffff):exercise(event=event)
    for fail in (0,1,2):
        m=Machine(raw,syms,sizes,config,payload+config['span']+300)
        first=m.run(0,fail=fail)
        require(m.run(0)==first and not m.calls and not m.writes,'seen event was attempted twice')
        later=m.run(1)
        offset=16+m.window+128
        require(later[offset:offset+128]==bytes.fromhex(config['frames']['1']),'later distinct event failed')
        rows.append(dict(sequence='seen-once-including-failed-map',failed_mapping=fail))
    for change in (0,4,8,12):
        for timing in ('before','commit'):
            m=Machine(raw,syms,sizes,config,payload+config['span']+300);m.run(0)
            if timing=='before':m.u.mem_write(probe.BASE+change,struct.pack('<I',0x12345678))
            drift=m.run(1,change=change if timing=='commit' else None)
            m.u.mem_write(probe.BASE,m.before[:16]);expected=bytearray(drift);expected[:16]=m.before[:16]
            require(m.run(5)==expected and not m.calls and not m.writes,'probe header drift was not sticky')
            rows.append(dict(sequence='sticky-drift',word=change,timing=timing))
    initrd=manifest['initramfs'];require(manifest['vm'] is False and pin(initrd['path'])==initrd,'physical initramfs required')
    result=dict(status='PASS_H0_ACTUAL_DEFERRED_PROBE_C',kernel_path=str(image),elf_path=str(elf),
                kernel_sha256=digest(image),elf_sha256=digest(elf),source_sha256=digest(__file__),
                table=pin(output/'initcall-table.json'),placement=sites,cases=rows,
                declared_slots=total,declared_span=config['span'],mapping_api_mocked=True,
                mmu_translation_proved=False,layout_compiler=record['kernel']['command']['compiler'],
                layout_config_sha256=record['kernel']['config_sha256'],mapping_initramfs=initrd,device_actions=0)
    (output/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    return result

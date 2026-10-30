#!/usr/bin/env python3
"""Qualify the final initcall table and actual parameterized ARM64 writer."""
import json
from pathlib import Path
import struct
import subprocess

from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM64, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn import arm64_const as regs
from prepare import digest, require
from qualify_retained import symbols
import retained_trace as trace


def pin(path):
    path = Path(path).resolve()
    return dict(path=str(path), size=path.stat().st_size, sha256=digest(path))


def inventory(image, elf, config):
    raw = image.read_bytes()
    syms = symbols(elf)
    with elf.open('rb') as stream:
        table = ELFFile(stream).get_section_by_name('.symtab')
        entries = [(s.name, s['st_value'], s['st_size'], s['st_info']['type'])
                   for s in table.iter_symbols()]
    sizes = {name: size for name, _, size, _ in entries}
    funcs = {}
    for name, address, _, kind in entries:
        if kind == 'STT_FUNC':
            funcs.setdefault(address, []).append(name)
    boundaries = [syms['__initcall' + str(i) + '_start'] for i in range(8)] + [syms['__initcall_end']]
    require(all(a <= b and (b - a) % 4 == 0 for a, b in zip(boundaries, boundaries[1:])) and
            boundaries[-1] - boundaries[0] == 4 * config['initcall_count'],
            'fresh linked PREL32 table count/boundaries differ')
    require(sizes['initcall_levels'] == 72 and
            list(struct.unpack_from('<9Q', raw, syms['initcall_levels'] - syms['_text'])) == boundaries,
            'actual loop level array differs from linker boundaries')
    rows = []
    counts = []
    for level, (start, end) in enumerate(zip(boundaries, boundaries[1:])):
        counts.append((end - start) // 4)
        for address in range(start, end, 4):
            relative = struct.unpack_from('<i', raw, address - syms['_text'])[0]
            target = address + relative
            require(target in funcs, 'fresh initcall destination has no exact function symbol')
            rows.append(dict(ordinal=(address - boundaries[0]) // 4, level=level,
                             entry_address=address, target_address=target,
                             functions=sorted(funcs[target])))
    frame_bytes = b''.join(bytes.fromhex(config['frames'][str(i)])
                           for i in range(trace.event_count(config['initcall_count'])))
    offset = syms['s22_trace_frames'] - syms['_text']
    require(sizes['s22_trace_frames'] == len(frame_bytes) and raw[offset:offset + len(frame_bytes)] == frame_bytes,
            'actual linked trace frame array differs')
    state_names = ('s22_trace_header', 's22_trace_window', 's22_trace_span',
                   's22_trace_latched', 's22_trace_disabled')
    init_names = (*state_names, 's22_trace_frames', 's22_retained_trace', 's22_retained_initcall',
                  'kernel_init_freeable', 'prev_map', 'prev_size', 'slot_virt', 'after_paging_init')
    require(all(syms['__init_begin'] <= syms[name] < syms['__init_end'] for name in init_names),
            'trace or mapping state is outside retained init lifetime')
    return dict(schema='s22plus-mainline-initcall-table-v8', status='PASS_H0_FINAL_PREL32_TABLE',
                image=pin(image), elf=pin(elf), regular_count=len(rows), counts_by_level=counts,
                entries=rows, boundaries=boundaries, frame_array_matches=True,
                init_lifetime_symbols=list(init_names), device_actions=0), syms, sizes


def placement(raw, syms, sizes):
    def word(pc):return struct.unpack_from('<I', raw, pc - syms['_text'])[0]
    def signed(value, bits):return value - (1 << bits) if value & (1 << (bits - 1)) else value
    def calls(name):
        return [(pc, pc + 4 * signed(word(pc) & 0x3ffffff, 26))
                for pc in range(syms[name], syms[name] + sizes[name], 4) if word(pc) >> 26 == 0b100101]
    def unique(rows, name):
        values = [pc for pc, target in rows if target == syms[name]]
        require(len(values) == 1, 'trace linked call count differs: ' + name)
        return values[0]
    parent = calls('kernel_init')
    freeable = calls('kernel_init_freeable')
    direct = [pc for pc, target in freeable if target == syms['s22_retained_trace']]
    tail = unique(parent, 's22_retained_trace')
    require(len(direct) == 5 and all(word(pc - 4) == 0x52800000 | (event << 5)
                                   for event, pc in enumerate(direct)) and
            word(tail - 4) == 0x528000a0,
            'actual fixed milestone arguments differ')
    wrappers = [pc for pc, target in freeable if target == syms['s22_retained_initcall']]
    dispatches = [pc for pc, target in freeable if target == syms['do_one_initcall']]
    require(len(wrappers) == len(dispatches) == 2 and
            dispatches[0] < direct[0] < direct[2] < wrappers[0] < dispatches[1] < wrappers[1] < direct[3],
            'regular wrapper pair or untouched early traversal differs')
    require(unique(freeable, 'page_alloc_init_late') + 8 == direct[0] and
            direct[0] + 4 == unique(freeable, 'cpuset_init_smp') and
            unique(freeable, 'driver_init') + 8 == direct[1] and
            direct[1] + 4 == unique(freeable, 'init_irq_proc') and
            unique(freeable, 'kfree') + 8 == direct[3] and
            unique(freeable, 'wait_for_initramfs') + 8 == direct[4] and
            direct[4] + 4 == unique(freeable, 'console_on_rootfs'),
            'actual fixed milestone boundaries differ')
    require(unique(parent, 'kernel_init_freeable') < unique(parent, 'async_synchronize_full') and
            unique(parent, 'async_synchronize_full') + 8 == tail < unique(parent, 'free_initmem'),
            'last trace is not after async return and before init freeing')
    require(word(tail + 4) == 0x52800040, 'freeing state value differs')
    store = word(tail + 8)
    require(store & 0xffc00000 == 0xb9000000 and store & 31 == 0, 'freeing state store differs')
    base_register = (store >> 5) & 31
    pages = [pc for pc in range(unique(parent, 'kernel_init_freeable') + 4, tail, 4)
             if word(pc) & 0x9f000000 == 0x90000000 and word(pc) & 31 == base_register]
    require(len(pages) == 1, 'freeing state address derivation differs')
    pc = pages[0]; insn = word(pc)
    page = (pc & ~4095) + (signed(((insn >> 5) & 0x7ffff) << 2 | ((insn >> 29) & 3), 21) << 12)
    require(page + ((store >> 10) & 0xfff) * 4 == syms['system_state'], 'freeing store target differs')
    # The actual pointer argument must be saved before the induction update.
    # The independent artifact review also inspects the complete loop/guard CFG.
    require(word(wrappers[0] - 4) == 0x52800001 and
            word(wrappers[1] - 8) == 0x52800021,
            'actual entry/return phase arguments differ')
    require(not any(name in syms for name in ('s22_retained_pre_basic_setup', 's22_retained_post_basic_setup',
                                               's22_retained_post_kthreadd_wait', 's22_retained_post_async_sync')),
            'trace retains an old marker site')
    return dict(fixed_calls=direct + [tail], initcall_wrapper_calls=wrappers,
                early_dispatch_call=dispatches[0], regular_dispatch_call=dispatches[1],
                final_return_pc=tail + 4, freeing_state_store=tail + 8,
                regular_loop_entry_pc=wrappers[0], regular_loop_exit_pc=unique(freeable, 'kfree'),
                init_memory_free_call=unique(parent, 'free_initmem'))


class Machine:
    """Actual linked writer with only CPU-state reads and mapping APIs mocked."""
    def __init__(self, raw, syms, sizes, config, idx, magic=0x4d474f4c):
        self.syms, self.config = syms, config
        self.u = u = Uc(UC_ARCH_ARM64, UC_MODE_ARM)
        u.reg_write(regs.UC_ARM64_REG_PSTATE, 5)
        u.mem_map(syms['_text'], (len(raw) + 0x100000 + 4095) & ~4095)
        u.mem_write(syms['_text'], raw)
        self.stack, self.stop = 0x20000000, 0x20010000
        u.mem_map(self.stack, 0x11000)
        u.mem_map(trace.BASE, trace.REGION)
        u.cpr_write(3, 0, 4, 1, 0, syms['init_task'])
        self.before = struct.pack('<IIII', 7, magic, idx, 123) + b'\xa5' * (trace.REGION - 16)
        u.mem_write(trace.BASE, self.before)
        self.state_ranges = [(syms[name], syms[name] + sizes[name]) for name in
                             ('s22_trace_header', 's22_trace_window', 's22_trace_span',
                              's22_trace_latched', 's22_trace_disabled')]
        self.span = min(idx, config['span']) // 128 * 128
        cursor = idx % (trace.REGION - 16)
        self.window = cursor - self.span if cursor >= self.span else trace.REGION - 16 - self.span
        self.active, self.calls, self.writes = [], [], []
        self.event, self.fail, self.change, self.cut, self.el, self.state = 0, 0, None, None, 1, 1
        self.target_slot = 0
        u.hook_add(UC_HOOK_CODE, self.code)
        u.hook_add(UC_HOOK_MEM_WRITE, self.write)

    def code(self, uc, pc, size, user):
        instruction = struct.unpack('<I', uc.mem_read(pc, 4))[0]
        system = {0xd5384240: self.el * 4, 0xd5381000: self.state, 0xd53c1000: self.state}
        if instruction & ~31 in system:
            uc.reg_write(getattr(regs, 'UC_ARM64_REG_X' + str(instruction & 31)), system[instruction & ~31])
            uc.reg_write(regs.UC_ARM64_REG_PC, pc + 4)
            return
        if pc == self.syms['early_memremap_prot']:
            phys, length, prot = [uc.reg_read(getattr(regs, 'UC_ARM64_REG_X' + str(i))) for i in range(3)]
            number = len(self.calls) + 1
            require(number <= 2 and (phys, length) == ((trace.BASE, 16) if number == 1 else (self.target_slot, 128)),
                    'trace mapping escaped fixed header/selected slot')
            require((prot >> 2) & 7 == 2 and prot & (1 << 53) and prot & (1 << 54),
                    'trace mapping is not Normal-NC/XN')
            self.calls.append((phys, length))
            if number != self.fail:self.active.append((phys, length))
            uc.reg_write(regs.UC_ARM64_REG_X0, 0 if number == self.fail else phys)
            uc.reg_write(regs.UC_ARM64_REG_PC, uc.reg_read(regs.UC_ARM64_REG_LR))
        elif pc == self.syms['early_memunmap']:
            pair = (uc.reg_read(regs.UC_ARM64_REG_X0), uc.reg_read(regs.UC_ARM64_REG_X1))
            require(self.active and pair == self.active.pop(), 'trace mapping cleanup order differs')
            uc.reg_write(regs.UC_ARM64_REG_PC, uc.reg_read(regs.UC_ARM64_REG_LR))
        elif pc == self.syms['s22_retained_trace_recheck'] and self.change is not None:
            uc.mem_write(trace.BASE + self.change, struct.pack('<I', 0x12345678))

    def write(self, uc, kind, address, size, value, user):
        if self.stack <= address < address + size <= self.stop:return
        if any(start <= address < address + size <= end for start, end in self.state_ranges):return
        require(self.target_slot <= address < address + size <= self.target_slot + 128 and size == 1,
                'trace write escaped selected slot/declared state/stack')
        self.writes.append(address)
        if self.cut is not None and len(self.writes) == self.cut:uc.emu_stop()

    def run(self, event, *, el=1, state=1, fail=0, change=None, cut=None, entry=None, phase=0):
        self.event, self.el, self.state = event, el, state
        self.fail, self.change, self.cut = fail, change, cut
        self.calls, self.writes = [], []
        self.target_slot = trace.BASE + 16 + self.window + self.event_offset(event)
        u = self.u
        u.reg_write(regs.UC_ARM64_REG_SP, self.stop - 16)
        u.reg_write(regs.UC_ARM64_REG_LR, self.stop)
        protected = {i: 0x1234000000000000 + i for i in range(19, 30)}
        for i, value in protected.items():u.reg_write(getattr(regs, 'UC_ARM64_REG_X' + str(i)), value)
        u.reg_write(regs.UC_ARM64_REG_X0, event if entry is None else entry)
        u.reg_write(regs.UC_ARM64_REG_X1, phase)
        start = self.syms['s22_retained_trace' if entry is None else 's22_retained_initcall']
        u.emu_start(start, self.stop, count=20000)
        if cut is None:
            require(u.reg_read(regs.UC_ARM64_REG_PC) == self.stop and not self.active and
                    u.reg_read(regs.UC_ARM64_REG_SP) == self.stop - 16, 'trace did not return with complete cleanup')
            require(all(u.reg_read(getattr(regs, 'UC_ARM64_REG_X' + str(i))) == value for i, value in protected.items()),
                    'trace changed callee-saved register')
        return bytes(u.mem_read(trace.BASE, trace.REGION))

    def event_offset(self, event):
        return event * 128


def qualify(record, config, output):
    output.mkdir(mode=0o700, parents=True, exist_ok=False)
    image = Path(record['kernel']['image']); elf = image.parents[3] / 'vmlinux'
    require(digest(image) == record['kernel']['sha256'], 'trace kernel changed')
    table, syms, sizes = inventory(image, elf, config)
    (output / 'initcall-table.json').write_text(json.dumps(table, indent=2) + '\n')
    raw = image.read_bytes(); sites = placement(raw, syms, sizes)
    for name in ('kernel_init_freeable', 'kernel_init', 's22_retained_trace', 's22_retained_initcall', '__set_fixmap'):
        text = subprocess.check_output(['aarch64-linux-gnu-objdump', '-d', '--disassemble=' + name, elf], text=True)
        (output / (name + '.txt')).write_text(text)
        if name == 's22_retained_trace':
            require(all(x in text for x in ('paciasp', 'autiasp', '__stack_chk_fail')), 'trace protections lost')
        if name == '__set_fixmap':require(all(x in text for x in ('tlbi', 'dsb', 'isb')), 'fixmap barriers lost')
    rows = []
    total = trace.event_count(config['initcall_count'])
    payload = trace.REGION - 16
    def exercise(event=0, idx=payload + config['span'] + 300, magic=0x4d474f4c, **kwargs):
        machine = Machine(raw, syms, sizes, config, idx, magic)
        after = machine.run(event, **kwargs)
        expected = bytearray(machine.before)
        admitted = (0 <= event < total and kwargs.get('el', 1) in (1, 2) and
                    kwargs.get('state', 1) & 0x2000001 == 1 and magic == 0x4d474f4c and
                    (event + 1) * 128 <= machine.span and not kwargs.get('fail'))
        offset = machine.target_slot - trace.BASE
        if kwargs.get('cut') is not None:
            require(after[:offset] == expected[:offset] and after[offset + 128:] == expected[offset + 128:] and
                    after[offset:offset + 128] != bytes.fromhex(config['frames'][str(event)]),
                    'interrupted trace escaped slot or committed full frame')
        else:
            if admitted:
                frame = bytes.fromhex(config['frames'][str(event)])
                expected[offset:offset + 128] = frame if kwargs.get('change') is None else bytes(8) + frame[8:]
                if kwargs.get('change') is not None:struct.pack_into('<I', expected, kwargs['change'], 0x12345678)
            require(after == expected, 'trace bytes/header/outside-window differ')
            if not admitted:require(not machine.writes, 'ineligible trace wrote payload')
        rows.append(dict(event=event, idx=idx, **kwargs, slot_writes=len(machine.writes), map_calls=len(machine.calls)))
    for event in (0, 5, 6, total // 2, total - 1):
        for idx in (0, 127, 128, 255, 256, 767, 768, config['span'] - 1, config['span'],
                    payload - 1, payload, payload + 1, payload + config['span'] + 4196, 0xffffffff):
            exercise(event, idx)
    for el in (0, 2, 3):exercise(el=el)
    for state in (0, 4, 5, 1 | (1 << 25)):exercise(state=state)
    exercise(magic=0)
    for fail in (1, 2):exercise(fail=fail)
    for event in (0, total - 1):
        for change in (0, 4, 8, 12):exercise(event=event, change=change)
        for cut in range(1, 136):exercise(event=event, cut=cut)
    for event in (total, 0xffffffff):exercise(event=event)
    for change in (0, 4, 8, 12):
        for timing in ('before', 'commit'):
            machine = Machine(raw, syms, sizes, config, payload + config['span'] + 300)
            machine.run(0)
            if timing == 'before':machine.u.mem_write(trace.BASE + change, struct.pack('<I', 0x12345678))
            at_drift = machine.run(1, change=change if timing == 'commit' else None)
            # Restoring the original header must not reopen a disabled trace.
            machine.u.mem_write(trace.BASE, machine.before[:16])
            expected = bytearray(at_drift);expected[:16] = machine.before[:16]
            require(machine.run(5) == expected and not machine.calls and not machine.writes,
                    'header drift did not permanently disable this attempt')
            rows.append(dict(sequence='sticky-drift', header_word=change, timing=timing))
    for fail in (1, 2):
        machine = Machine(raw, syms, sizes, config, 768)
        machine.run(0); machine.run(1, fail=fail)
        observed = machine.run(5)
        offset = 16 + machine.window + 5 * 128
        require(observed[offset:offset + 128] == bytes.fromhex(config['frames']['5']), 'later short-window milestone lost')
        require(machine.run(6) == observed and not machine.writes, 'short-window event escaped capacity')
        rows.append(dict(sequence='latched-map-failure-short-prefix', failed_mapping=fail))
    first = syms['__initcall0_start']; end = syms['__initcall_end']
    for entry, phase in ((first - 4, 0), (first + 1, 0), (end, 0), (first, 2)):
        machine = Machine(raw, syms, sizes, config, payload + config['span'] + 300)
        require(machine.run(0, entry=entry, phase=phase) == machine.before and not machine.calls,
                'invalid ordinal/phase accessed log')
        require(machine.run(0) == machine.before and not machine.calls, 'invalid ordinal did not disable trace')
        rows.append(dict(sequence='invalid-ordinal', relative_entry=entry - first, phase=phase))
    for ordinal in (0, config['initcall_count'] // 2, config['initcall_count'] - 1):
        for phase in (0, 1):
            event = 6 + 2 * ordinal + phase
            machine = Machine(raw, syms, sizes, config, payload + config['span'] + 300)
            after = machine.run(event, entry=first + 4 * ordinal, phase=phase)
            expected = bytearray(machine.before);offset = machine.target_slot - trace.BASE
            expected[offset:offset + 128] = bytes.fromhex(config['frames'][str(event)])
            require(after == expected, 'actual ordinal wrapper selected the wrong frame')
            rows.append(dict(sequence='ordinal-wrapper', ordinal=ordinal, phase=phase))
    manifest = json.loads(Path(record['initramfs_manifest']).read_text())
    initrd = manifest['initramfs']
    require(manifest['vm'] is False and pin(initrd['path']) == initrd, 'trace fixture needs physical candidate initramfs')
    result = dict(status='PASS_H0_ACTUAL_INITCALL_TRACE_C', kernel_path=str(image), elf_path=str(elf),
                  kernel_sha256=digest(image), elf_sha256=digest(elf), source_sha256=digest(__file__),
                  table=pin(output / 'initcall-table.json'), placement=sites, cases=rows,
                  declared_slots=total, declared_span=config['span'], mapping_api_mocked=True,
                  mmu_translation_proved=False, layout_compiler=record['kernel']['command']['compiler'],
                  layout_config_sha256=record['kernel']['config_sha256'], mapping_initramfs=initrd, device_actions=0)
    (output / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    return result

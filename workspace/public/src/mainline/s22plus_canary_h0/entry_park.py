"""Fixed V1 entry-park source and linked-image checks; H0 only."""
import json
from pathlib import Path
import struct

from prepare import HERE, digest, require

SCHEMA = 's22plus-mainline-entry-park-source-v1'
QUALIFICATION = 's22plus-mainline-entry-park-qualification-v1'
STATUS = 'PASS_H0_ACTUAL_ENTRY_PARK'
LOOP = ('SYM_INNER_LABEL(s22_entry_park, SYM_L_GLOBAL)\n'
        '\twfe\n\tb\ts22_entry_park\n'
        'SYM_INNER_LABEL(s22_entry_park_end, SYM_L_GLOBAL)\n')


def pin(path):
    path = Path(path).resolve()
    return dict(path=str(path), size=path.stat().st_size, sha256=digest(path))


def declaration():
    return dict(schema=SCHEMA, stop='after-v1-before-record_mmu_state',
                source=pin(HERE/'entry_park.py'))


def instrument(marked):
    site = '\tbl\ts22_retained_kernel\n\tbl\trecord_mmu_state\n'
    require(marked.count(site) == 1 and 's22_entry_park' not in marked,
            'entry park requires the exact V1 entry hook')
    return marked.replace(site, '\tbl\ts22_retained_kernel\n'+LOOP+'\tbl\trecord_mmu_state\n')


def linked(loader):
    """Measure the actual Image, not an unparked substitute or source label."""
    from qualify_retained import symbols
    kernel = loader['kernel']
    require(loader.get('entry_park') == kernel.get('entry_park') == kernel.get('retained_marker')
            and kernel.get('entry_park') is not None, 'entry-park source joins differ')
    source_ref = kernel['entry_park']
    source_path = Path(source_ref['path'])
    require(pin(source_path) == source_ref, 'entry-park source receipt changed')
    source = json.loads(source_path.read_text())
    require(source.get('entry_park') == declaration(), 'entry-park declaration differs')
    image = Path(kernel['image']); raw = image.read_bytes()
    require(len(raw) == kernel['file_size'] and digest(image) == kernel['sha256'], 'park Image changed')
    elf = image.parents[3]/'vmlinux'; syms = symbols(elf)
    base = syms['_text']; entry = syms['primary_entry']; park = syms['s22_entry_park']
    end = syms['s22_entry_park_end']
    require(park == entry+4 and end == park+8, 'park is not immediately after the V1 call')
    require(raw[park-base:end-base] == struct.pack('<II', 0xd503205f, 0x17ffffff),
            'actual park is not exactly WFE and back-branch')
    for address, target in ((entry, syms['s22_retained_kernel']), (end, syms['record_mmu_state'])):
        word = struct.unpack_from('<I', raw, address-base)[0]
        immediate = word & 0x3ffffff
        if immediate & (1 << 25): immediate -= 1 << 26
        require(word >> 26 == 0b100101 and address+4*immediate == target, 'entry call target differs')
    physical = loader['extents']['kernel-runtime'][0]
    return dict(kernel=pin(image), elf=pin(elf), source=source_ref,
                entry_pc=physical+entry-base, park_pc=physical+park-base,
                park_end_pc=physical+end-base, record_mmu_state_pc=physical+syms['record_mmu_state']-base,
                loop_bytes=raw[park-base:end-base].hex())

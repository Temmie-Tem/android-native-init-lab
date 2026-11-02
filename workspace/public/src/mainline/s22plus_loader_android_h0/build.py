#!/usr/bin/env python3
"""Build the exact FYG8 Android loader control in private storage; H0 only."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import struct
import subprocess
import sys

from elftools.elf.elffile import ELFFile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
COMMON = HERE.parent / 's22plus_canary_h0'
sys.path.insert(0, str(COMMON))
from prepare import config_values, digest, fixed_reservations, memreserve, nodes, require, run, uncovered
from build_loader import DTB, PAYLOAD, TEXT, range_include
sys.path.insert(0, str(ROOT / 'workspace/public/src/scripts/revalidation'))
import s22plus_boot_verify as boot
import s22plus_loader_android_profile_v1 as profile

FDT_CAPACITY = 2 * 1024 * 1024
MARKER_PROPERTY = 'codex,uniloader-android-v1'
STATUS = 'H0_LOADER_ANDROID_BUILT_NOT_DEVICE_ADMITTED'


def pin(path):
    path = Path(path).resolve(strict=True)
    return dict(path=str(path), size=path.stat().st_size, sha256=digest(path))


def symbols(path):
    with Path(path).open('rb') as stream:
        elf = ELFFile(stream)
        table = elf.get_section_by_name('.symtab')
        return {s.name: (s['st_value'], s['st_size']) for s in table.iter_symbols() if s.name}


def guard_instructions(elf, syms, output):
    start, size = syms['loader_guard']
    dis = subprocess.check_output(['aarch64-linux-gnu-objdump', '-d',
        '--start-address='+str(start), '--stop-address='+str(start+size), str(elf)], text=True)
    (output/'guard-disassembly.txt').write_text(dis)
    instructions = []
    for line in dis.splitlines():
        match = re.match(r'\s*([0-9a-f]+):\s+[0-9a-f]{8}\s+(\S+)\s*(.*)', line)
        if not match:
            continue
        _, op, args = match.groups()
        require(not op.startswith('st') and op not in
            ('bl','blr','br','eret','msr','mrs','svc','hvc','smc','dc','ic','at','tlbi') and
            not re.search(r'\b(?:sp|wsp)\b', args), 'pre-store guard contains a store, stack or control effect')
        if op not in ('ret','cmp','cmn','tst') and not op.startswith(('b.','cb','tb')):
            require(not re.match(r'[xw](?:28|29|30)\b', args), 'guard clobbers preserved entry registers')
        instructions.append((op,args))
    require(len(instructions)*4 == size and any(op == 'ret' for op,_ in instructions),
            'guard instructions incompletely decoded')
    # No indirect GOT loads: all symbol addresses in this leaf use ADRP/ADD
    # under the entry's explicit 4 KiB source-alignment requirement.
    obj = elf.parent/'arch/aarch64/guard.o'
    reloc = subprocess.check_output(['aarch64-linux-gnu-readelf','-rW',str(obj)], text=True)
    (output/'guard-relocations.txt').write_text(reloc)
    types = re.findall(r'\b(R_AARCH64_\w+)\b', reloc)
    require(types and set(types) <= {'R_AARCH64_ADR_PREL_PG_HI21','R_AARCH64_ADD_ABS_LO12_NC',
                                    'R_AARCH64_PREL32'}, 'guard has a non-PC-relative address dependency')
    return dict(instruction_count=len(instructions), no_stack=True, no_stores=True,
                no_calls=True, entry_x28_and_return_x30_preserved=True,
                source_page_alignment=4096, relocation_types=sorted(set(types)))


def build(base, prepared, output, *, logm_control=False):
    base, prepared, output = [Path(p).resolve() for p in (base, prepared, output)]
    require(output.is_relative_to(ROOT/'workspace/private') and not output.exists(),
            'fresh private build directory required')
    lock = json.loads((COMMON/'sources.json').read_text())
    upstream = base/'uniloader-upstream'
    head = subprocess.check_output(['git','-C',str(upstream),'rev-parse','HEAD'], text=True).strip()
    require(head == lock['uniloader']['commit'] and not subprocess.check_output(
        ['git','-C',str(upstream),'status','--porcelain']), 'retained upstream differs')
    port_patch = base/'r0q-port/kernel/uniloader-patches/0001-dtb-relocate.patch'
    require(digest(port_patch) == lock['files']['r0q-port/kernel/uniloader-patches/0001-dtb-relocate.patch'],
            'retained port patch differs')
    prep = json.loads((prepared/'prepared.json').read_text())
    live_path = Path(prep['live_fdt']['path'])
    require(digest(live_path) == prep['live_fdt']['sha256'], 'retained FDT changed')
    live = nodes(live_path)
    require(live['/']['model'].startswith(b'Samsung G0Q PROJECT'), 'retained FDT is not g0q')
    # Keep the original five tuple boundaries/order for live-FDT equality.
    # The shared mainline source_ranges() merges adjacent banks for coverage.
    banks = [tuple(r) for r in prep['memory_banks']]
    require(len(banks) == 5 and all(0 <= a < b <= 2**48 for a,b in banks),
            'fixed five-bank shape differs')
    baseline = ROOT/'workspace/private/outputs/s22plus_magisk_root_boot_only/boot.img'
    target = json.loads((ROOT/'workspace/public/src/device-action/profiles/s22plus_fyg8.json').read_text())
    require(digest(baseline) == target['final_health']['boot_sha256'] and baseline.stat().st_size == 96*1024*1024,
            'original-A provenance differs')
    parsed = boot.parse_boot_v4(baseline.read_bytes())
    kernel = parsed.kernel
    offset, runtime, flags = struct.unpack_from('<QQQ', kernel, 8)
    require(kernel[56:60] == b'ARMd' and offset == 0 and flags == 10 and
            len(kernel) <= runtime <= 64*1024*1024 and PAYLOAD % (2*1024*1024) == offset,
            'exact vendor raw Image geometry differs')
    releases = set(re.findall(rb'Linux version ([A-Za-z0-9._+@-]{1,160}) ', kernel))
    require(len(releases) == 1, 'vendor kernel release is ambiguous')
    release = releases.pop().decode('ascii')
    output.mkdir(mode=0o700, parents=True)
    marker = secrets.token_hex(32)
    (output/'marker.txt').write_text(marker)
    logm = None
    if logm_control:
        key = secrets.token_bytes(32)
        (output/'logm-key.bin').write_bytes(key)
        logm = dict(configuration=profile.logm_configuration(marker,key),key=pin(output/'logm-key.bin'))
    source = output/'source'
    shutil.copytree(upstream, source)
    patches = [port_patch, COMMON/'uniloader-g0q-entry.patch', HERE/'uniloader-android.patch']
    for i, patch in enumerate(patches):
        log = output/f'patch-{i}.log'
        run(['patch','--batch','--fuzz=0','-p1','-i',patch],log,cwd=source)
        require('fuzz' not in log.read_text().lower(), 'fuzzy patch application')
    (source/'arch/aarch64/g0q-source-ram.inc').write_text(range_include(banks))
    generated=f'#define G0Q_VENDOR_RUNTIME {runtime}\n#define G0Q_ANDROID_MARKER "{marker}"\n'
    if logm:
        generated+='#define G0Q_LOGM_CONTROL 1\n'
        for field,label in [('frame_hex','G0Q_LOGM_FRAME'),('report_seed_hex','G0Q_LOGM_REPORT_SEED')]:
            generated+='#define '+label+' {'+','.join(str(x) for x in bytes.fromhex(logm['configuration'][field]))+'}\n'
        generated+=''.join(f'#define G0Q_LOGM_{name} {value}\n' for name,value in profile.LOGM_STATES.items())
    (source/'arch/aarch64/g0q-android-marker.h').write_text(generated)
    shutil.copyfile(HERE/'guard.c',source/'arch/aarch64/guard.c')
    if logm:shutil.copyfile(HERE/'logm-control.c',source/'arch/aarch64/logm-control.c')
    else:(source/'arch/aarch64/logm-control.c').write_text('/* LOGM control is not selected. */\n')
    config = (upstream/'configs/r0q_defconfig').read_text()
    settings = dict(CONFIG_TEXT_BASE=hex(TEXT), CONFIG_PAYLOAD_ENTRY=hex(PAYLOAD),
        CONFIG_DTB_RELOCATE='y',CONFIG_DTB_ENTRY=hex(DTB),CONFIG_FDT_BUF_SIZE=str(FDT_CAPACITY),
        CONFIG_FDT_BUF_ADDR='0x0',CONFIG_RAMDISK_NO_COPY='y',CONFIG_SIMPLE_FB='n')
    for key, value in settings.items():
        config = re.sub(r'^(?:'+key+r'=.*|# '+key+r' is not set)\n?', '', config, flags=re.M)
        config += (f'# {key} is not set\n' if value == 'n' else f'{key}={value}\n')
    (source/'configs/r0q_defconfig').write_text(config)
    (source/'blob/Image').write_bytes(kernel)
    # Linker compatibility only. The true incoming FDT is used, and no ramdisk
    # is linked or copied. Tests assert neither placeholder is a runtime input.
    (source/'blob/dtb').write_bytes(bytes(8))
    (source/'blob/ramdisk').write_bytes(bytes(1))
    make = ['make','ARCH=aarch64','CROSS_COMPILE=aarch64-linux-gnu-',
            'BUILD_DATE=1970-01-01 00:00:00','GIT_VERSION_TAG='+head]
    env = dict(os.environ, SOURCE_DATE_EPOCH='0')
    run(make+['r0q_defconfig'],output/'config.log',cwd=source,env=env)
    effective = config_values((source/'.config').read_text())
    for key, value in settings.items():
        actual = effective.get(key,'n')
        require(int(actual,0) == int(value,0) if value[0].isdigit() else actual == value,
                'effective loader configuration differs: '+key)
    run(make+['-j4'],output/'build.log',cwd=source,env=env)
    elf, blob = source/'uniLoader.o', source/'uniLoader'
    raw = blob.read_bytes(); syms = symbols(elf)
    required = ('_head','_start','_stub_end','_file_end','_copy_size','_stack_end',
        '__bss_start','__bss_end','fdt_buf','kernel','kernel_size','dtb','_g0q_source_ram',
        '_g0q_source_ram_end','_g0q_guard_plan','_reloc_entry','_reloc_rejected',
        '_guard_passed','_reloc_branch','loader_guard','load_kernel_and_jump')
    require(all(k in syms for k in required), 'loader symbols incomplete')
    if logm:
        for symbol,field in [('g0q_logm_frame','frame_hex'),('g0q_logm_report_seed','report_seed_hex')]:
            require(symbol in syms and syms[symbol][1]==128 and
                raw[syms[symbol][0]-TEXT:syms[symbol][0]-TEXT+128]==bytes.fromhex(logm['configuration'][field]),
                'linked LOGM frame/report seed differs')
        require('g0q_logm_control' in syms,'LOGM writer missing')
    values = {k:syms[k][0] for k in required}
    require(values['_head'] == TEXT and values['_stub_end'] == values['_start'] and
        values['_file_end']-TEXT == len(raw) and
        values['_copy_size'] == values['_file_end']-values['_stub_end'] and
        values['_copy_size'] % 16 == 0 and values['kernel_size'] == len(kernel) and
        values['_file_end'] <= values['__bss_start'] <= values['fdt_buf'] and
        values['fdt_buf']+FDT_CAPACITY <= values['__bss_end'] <= values['_stack_end'],
        'linked runtime geometry differs')
    require(raw[values['kernel']-TEXT:values['kernel']-TEXT+len(kernel)] == kernel,
            'linked exact vendor Image differs')
    extents = dict(staging=(TEXT,values['_stack_end']),kernel=(PAYLOAD,PAYLOAD+runtime),
                   fdt=(DTB,DTB+FDT_CAPACITY))
    reserved = fixed_reservations(live)+memreserve(live_path)
    for name,(a,b) in extents.items():
        require(not uncovered([(a,b)],banks) and all(b <= c or d <= a for c,d in reserved),
                'write extent conflicts with retained RAM/reservations: '+name)
    for i,(a,b) in enumerate(extents.values()):
        require(all(b <= c or d <= a for c,d in list(extents.values())[i+1:]),'write extents overlap')
    table = b''.join(struct.pack('<QQ',a,b) for a,b in [*extents.values(),*banks])
    require(raw[values['_g0q_guard_plan']-TEXT:values['_g0q_source_ram_end']-TEXT] == table,
            'linked pre-store plan differs from qualified extents')
    image_offset,image_size,image_flags = struct.unpack_from('<QQQ',raw,8)
    require(raw[56:60] == b'ARMd' and image_offset == 0 and
        image_size == values['_stack_end']-TEXT and image_flags == 10,'outer loader Image header differs')
    with elf.open('rb') as stream:
        parsed_elf = ELFFile(stream)
        for sec in parsed_elf.iter_sections():
            if sec['sh_flags'] & 2 and sec['sh_size'] and sec['sh_type'] != 'SHT_NOBITS':
                a,b=sec['sh_addr'],sec['sh_addr']+sec['sh_size']
                require(TEXT <= a < b <= values['_file_end'] and raw[a-TEXT:b-TEXT] == sec.data(),
                        'ELF and raw section disagree: '+sec.name)
    guard = guard_instructions(elf,syms,output)
    run(['file',elf,blob,source/'blob/Image'],output/'file.log')
    run(['aarch64-linux-gnu-readelf','-h','-l','-r',elf],output/'elf.log')
    run(['aarch64-linux-gnu-objdump','-d',elf],output/'disassembly.txt')
    sources = [HERE/'build.py',HERE/'guard.c',HERE/'logm-control.c',Path(profile.__file__),*patches,COMMON/'sources.json',
               COMMON/'prepare.py',COMMON/'build_loader.py']
    result = dict(status=STATUS,loader=pin(blob),elf=pin(elf),kernel=pin(source/'blob/Image'),
        original_a=pin(baseline),retained_fdt=pin(live_path),retained_preparation=pin(prepared/'prepared.json'),
        source_commit=head,source_pins=[pin(p) for p in sources],configuration=effective,
        extents=extents,source_ram_ranges=banks,runtime_symbols=values,guard=guard,
        fdt_capacity=FDT_CAPACITY,marker_property=MARKER_PROPERTY,marker=marker,
        marker_sha256=hashlib.sha256(marker.encode()).hexdigest(),kernel_release=release,
        kernel_header=dict(text_offset=offset,image_size=runtime,flags=flags,file_size=len(kernel)),
        loader_image_header=dict(text_offset=image_offset,image_size=image_size,flags=image_flags,file_size=len(raw)),
        retained_initrd_preserved=True,device_actions=0,activation=False)
    if logm:result['logm_control']=logm
    (output/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(status=STATUS,loader_bytes=len(raw),kernel_bytes=len(kernel),
                         guard_instructions=guard['instruction_count'],device_actions=0)))


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('base','prepared','output'): p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--logm-control',action='store_true')
    a=p.parse_args();build(a.base,a.prepared,a.output,logm_control=a.logm_control)

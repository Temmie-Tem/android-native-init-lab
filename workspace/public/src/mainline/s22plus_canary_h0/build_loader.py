#!/usr/bin/env python3
"""Build and statically qualify the g0q loader; never authorize device entry."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
from elftools.elf.elffile import ELFFile

from prepare import HERE, ROOT, digest, require, run, config_values, uncovered, merged, audit_candidate
import retained_marker as marker

# Keep staging above the retained FYG8 ABL source envelope. Its normal EFI
# placement overlaps the former staging base; the live-stub guard stays intact.
TEXT=0xab000000
PAYLOAD=0x80ba00000
DTB=0xb6000000
INITRD=0xb6915000


def source_ranges(prepared):
    # Reservations constrain new destination writes, not this already-loaded image read.
    result=merged(prepared['memory_banks'])
    require(result and all(0 <= a < b <= 2**48 for a,b in result),'source RAM geometry')
    return result


def range_include(ranges):
    return '/* Private retained g0q source RAM; generated, never commit. */\n'+''.join(
        f'\t.quad {a:#x}, {b:#x}\n' for a,b in ranges)


def build(base,prepared,init,output,reuse=False,kernel_label='kernel-1'):
    base,prepared,init,output=[p.resolve() for p in (base,prepared,init,output)]
    require(output.is_relative_to(ROOT/'workspace/private'),'private loader output')
    lock=json.loads((HERE/'sources.json').read_text())
    upstream=base/'uniloader-upstream'
    head=subprocess.check_output(['git','-C',upstream,'rev-parse','HEAD'],text=True).strip()
    require(head==lock['uniloader']['commit'],'loader source revision')
    require(not subprocess.check_output(['git','-C',upstream,'status','--porcelain']),'loader upstream dirty')
    patch=base/'r0q-port/kernel/uniloader-patches/0001-dtb-relocate.patch'
    require(digest(patch)==lock['files']['r0q-port/kernel/uniloader-patches/0001-dtb-relocate.patch'],'loader patch changed')
    local_patch=HERE/'uniloader-g0q-entry.patch'
    ir=json.loads((init/'result.json').read_text());require(ir['vm'] is False,'VM image forbidden in carrier')
    require(bool(kernel_label) and all(c.isalnum() or c=='-' for c in kernel_label),'kernel label')
    kr=json.loads((prepared/(kernel_label+'-result.json')).read_text())
    prep=json.loads((prepared/'prepared.json').read_text())
    ranges=source_ranges(prep)
    require(kr['command']['prepared_sha256']==digest(prepared/'prepared.json'),'kernel preparation differs')
    require(kr['config_sha256']==prep['config_sha256']==digest(Path(prep['kernel_build'])/'.config'),
            'kernel/config preparation differs')
    require(ir['dtb']['sha256']==prep['dtb_sha256'] and ir['initrd_address']==INITRD,'initramfs/DT placement preparation differs')
    config_inputs=[x for x in ir['inputs'] if Path(x['path']).resolve()==Path(prep['kernel_build'])/'.config']
    require(len(config_inputs)==1 and config_inputs[0]['sha256']==prep['config_sha256'],'initramfs config preparation differs')
    require(ir['kernel_release']==(Path(prep['kernel_build'])/'include/config/kernel.release').read_text().strip(),
            'initramfs kernel release differs')
    for item in ir['inputs']:require(digest(item['path'])==item['sha256'],'initramfs source/input changed')
    require(digest(prep['live_fdt']['path'])==prep['live_fdt']['sha256'],'retained live FDT changed')
    dt_audit=audit_candidate(prep['live_fdt']['path'],ir['dtb']['path'])
    for record in [ir['initramfs'],ir['dtb']]:require(digest(record['path'])==record['sha256'],'member changed')
    require(digest(kr['image'])==kr['sha256'],'kernel changed')
    marked=kr.get('retained_marker')
    marker_source=None
    if marked:
        require(digest(marked['path'])==marked['sha256'],'kernel marker provenance differs')
        marker_source=json.loads(Path(marked['path']).read_text())
        cfgref=marker_source['config']
        require(digest(cfgref['path'])==cfgref['sha256'] and
                marker_source['init_manifest']==dict(path=str(init/'result.json'),size=(init/'result.json').stat().st_size,
                    sha256=digest(init/'result.json')),'kernel/loader marker identity differs')
        cfg=json.loads(Path(cfgref['path']).read_text())
        marker.validate(cfg,ir['candidate_id'],Path(ir['key_path']).read_bytes())
    loader_marked=bool(marked) and marker.version(cfg)==1
    if not reuse:output.mkdir(mode=0o700,parents=True,exist_ok=False)
    require(not (output/'result.json').exists(),'result already published')
    source=output/'source'
    if not reuse:
        shutil.copytree(upstream,source)
        run(['patch','--batch','--fuzz=0','-p1','-i',patch],output/'patch.log',cwd=source)
        run(['patch','--batch','--fuzz=0','-p1','-i',local_patch],output/'entry-patch.log',cwd=source)
        (source/'arch/aarch64/g0q-source-ram.inc').write_text(range_include(ranges))
        if loader_marked:
            start=source/'arch/aarch64/start.S';text=start.read_text()
            hook='ENTRY(load_kernel_and_jump)\n'
            require(text.count(hook)==1 and 's22_retained_' not in text,'loader marker hook differs')
            start.write_text(text.replace(hook,hook+'\tbl s22_retained_loader\n')+'\n'+marker.render(cfg,1))
    require('fuzz' not in (output/'patch.log').read_text().lower(),'fuzzy patch application')
    require('fuzz' not in (output/'entry-patch.log').read_text().lower(),'fuzzy entry patch')
    require((source/'arch/aarch64/g0q-source-ram.inc').read_text()==range_include(ranges),'source RAM table changed')
    if loader_marked:
        text=(source/'arch/aarch64/start.S').read_text()
        require(text.endswith(marker.render(cfg,1)) and
                text.count('ENTRY(load_kernel_and_jump)\n\tbl s22_retained_loader\n')==1,
                'linked loader marker source differs')
    else:
        require('s22_retained_' not in (source/'arch/aarch64/start.S').read_text(),
                'undeclared loader marker source')
    config=(upstream/'configs/r0q_defconfig').read_text()
    config=re.sub(r'^CONFIG_TEXT_BASE=.*$',f'CONFIG_TEXT_BASE={TEXT:#x}',config,flags=re.M)
    config=re.sub(r'^CONFIG_PAYLOAD_ENTRY=.*$',f'CONFIG_PAYLOAD_ENTRY={PAYLOAD:#x}',config,flags=re.M)
    config+='\nCONFIG_DTB_RELOCATE=y\nCONFIG_DTB_ENTRY=0xb6000000\n# CONFIG_SIMPLE_FB is not set\n'
    if not reuse:(source/'configs/r0q_defconfig').write_text(config)
    require((source/'configs/r0q_defconfig').read_text()==config,'loader defconfig changed')
    for name,path in [('Image',kr['image']),('dtb',ir['dtb']['path']),('ramdisk',ir['initramfs']['path'])]:
        if not reuse:shutil.copyfile(path,source/'blob'/name)
        require(digest(source/'blob'/name)==digest(path),'embedded input changed')
    env=dict(os.environ,SOURCE_DATE_EPOCH='0')
    make=['make','ARCH=aarch64','CROSS_COMPILE=aarch64-linux-gnu-',
          'BUILD_DATE=1970-01-01 00:00:00','GIT_VERSION_TAG='+head]
    if not reuse:
        (output/'command.json').write_text(json.dumps({'make':make,'patch_sha256':digest(patch),
                                                     'entry_patch_sha256':digest(local_patch),
                                                     'config':config},indent=2)+'\n')
        run(make+['r0q_defconfig'],output/'config.log',cwd=source,env=env)
    command=json.loads((output/'command.json').read_text())
    require(command['entry_patch_sha256']==digest(local_patch),'entry patch receipt differs')
    effective=config_values((source/'.config').read_text())
    for key,value in {'CONFIG_TEXT_BASE':hex(TEXT),'CONFIG_PAYLOAD_ENTRY':hex(PAYLOAD),
                      'CONFIG_RAMDISK_ENTRY':hex(INITRD),'CONFIG_DTB_ENTRY':hex(DTB),
                      'CONFIG_DTB_RELOCATE':'y','CONFIG_SIMPLE_FB':'n','CONFIG_LIBFDT':'y',
                      'CONFIG_POSITION_INDEPENDENT':'y','CONFIG_LINUX_KRNL_HEADER_IMG':'y',
                      'CONFIG_FDT_BUF_ADDR':'0x0'}.items():
        actual=effective.get(key,'n')
        require(int(actual,16)==int(value,16) if value.startswith('0x') else actual==value,'loader config '+key)
    if not reuse:run(make+['-j4'],output/'build.log',cwd=source,env=env)
    # Artifact names are fixed by the pinned upstream Makefile.
    elf=source/'uniLoader.o';blob=source/'uniLoader'
    require(elf.is_file() and blob.is_file(),'loader artifacts absent')
    symbol_text=subprocess.check_output(['aarch64-linux-gnu-nm','-n',elf],text=True)
    (output/'symbols.txt').write_text(symbol_text)
    symbols={m[3]:int(m[1],16) for line in symbol_text.splitlines()
             if (m:=re.fullmatch(r'([0-9a-fA-F]+)\s+(\w)\s+(\S+)',line))}
    required=['_head','_start','_stub_end','_file_end','_copy_size','_reloc_start','_reloc_end',
              '_stack_end','__bss_start','__bss_end','fdt_buf','kernel','kernel_size',
              'ramdisk','ramdisk_size','dtb','_g0q_source_ram','_g0q_source_ram_end',
              '_reloc_entry','_reloc_rejected','load_kernel_and_jump']
    require(all(k in symbols for k in required),'missing linker geometry')
    reloc_size=symbols['_file_end']-symbols['_stub_end']
    stage_end=symbols['_stack_end']
    require(symbols['_head']==symbols['_reloc_start']==TEXT and
            symbols['_start']==symbols['_stub_end']>TEXT and reloc_size==symbols['_copy_size']>0 and
            reloc_size%16==0 and symbols['_file_end']-TEXT==blob.stat().st_size and
            symbols['kernel_size']==Path(kr['image']).stat().st_size,'embedded kernel geometry')
    require(symbols['ramdisk_size']==ir['initramfs']['size'],'embedded initrd size')
    require(symbols['dtb']%8==0 and DTB%8==0 and
            Path(ir['dtb']['path']).stat().st_size<int(effective['CONFIG_FDT_BUF_SIZE']), 'DTB alignment/buffer geometry')
    header=blob.read_bytes()[:64]
    require(len(header)==64 and header[56:60]==b'ARM\x64','loader ARM64 Image header')
    offset,declared_size,flags=struct.unpack_from('<QQQ',header,8)
    require(offset==0 and declared_size>=blob.stat().st_size and
            declared_size==symbols['_stack_end']-symbols['_head'], 'loader Image header geometry')
    raw=blob.read_bytes()
    require(any(f['magic'] in raw for f in marker.FORMATS.values())==bool(marked),
            'linked marker bytes lack declared scope')
    if marked:require(marker.FORMATS[marker.version(cfg)]['magic'] in raw,'selected marker bytes absent')
    with elf.open('rb') as stream:
        parsed=ELFFile(stream)
        for section in parsed.iter_sections():
            if section['sh_flags'] & 2 and section['sh_size'] and section['sh_type']!='SHT_NOBITS':
                a,b=section['sh_addr'],section['sh_addr']+section['sh_size']
                require(TEXT<=a<b<=symbols['_file_end'],'file-backed section outside copy: '+section.name)
                require(raw[a-TEXT:b-TEXT]==section.data(),'ELF/raw section mismatch: '+section.name)
    table=b''.join(struct.pack('<QQ',a,b) for a,b in ranges)
    require(raw[symbols['_g0q_source_ram']-TEXT:symbols['_g0q_source_ram_end']-TEXT]==table,
            'linked source RAM table differs')
    fdt_buffer=(symbols['fdt_buf'],symbols['fdt_buf']+int(effective['CONFIG_FDT_BUF_SIZE']))
    require(symbols['_file_end']<=symbols['__bss_start']<=fdt_buffer[0]<fdt_buffer[1]<=
            symbols['__bss_end']<=stage_end,'FDT buffer outside qualified loader BSS')
    c_commands=[p.read_text() for p in source.rglob('*.o.cmd')
                if 'aarch64-linux-gnu-gcc' in p.read_text() and '-D__ASSEMBLY__' not in p.read_text()]
    require(c_commands and all(all(flag in cmd for flag in
            ['-mstrict-align','-mgeneral-regs-only','-fno-builtin']) for cmd in c_commands),
            'C compiler alignment/register/builtin flags missing')
    payload_end=PAYLOAD+kr['runtime_size'];dtb_end=DTB+int(effective['CONFIG_FDT_BUF_SIZE'])
    extents={'loader-runtime-and-copy':(TEXT,stage_end),'kernel-runtime':(PAYLOAD,payload_end),
             'rewritten-dtb':(DTB,dtb_end),'initramfs':(INITRD,INITRD+ir['initramfs']['size'])}
    reserved=prep['candidate_reservations']
    for name,(start,end) in extents.items():
        require(not uncovered([(start,end)],prep['memory_banks']),name+' outside RAM')
        require(all(end<=a or start>=b for a,b in reserved),name+' intersects reservation')
    for i,(name,(start,end)) in enumerate(extents.items()):
        for other,(a,b) in list(extents.items())[i+1:]:require(end<=a or start>=b,name+' overlaps '+other)
    require(PAYLOAD%(2*1024*1024)==0,'unaligned Image placement')
    run(['file',elf,blob],output/'file.log')
    run(['aarch64-linux-gnu-readelf','-h','-l','-r',elf],output/'elf.log')
    run(['aarch64-linux-gnu-objdump','-d',elf],output/'disassembly.txt')
    result={'status':'H0_LOADER_BUILT_RUNTIME_PLACEMENT_GUARDED','loader':{'path':str(blob),'sha256':digest(blob),'size':blob.stat().st_size},
            'elf':{'path':str(elf),'sha256':digest(elf)},'extents':extents,
            'relocation_copy_bytes':reloc_size,'runtime_symbols':{k:symbols[k] for k in required},
            'configuration':effective,'source_commit':head,'patch_sha256':digest(patch),
            'entry_patch_sha256':digest(local_patch),'source_ram_ranges':ranges,'fdt_buffer':fdt_buffer,
            'strict_alignment_c_commands':len(c_commands),
            'loader_image_header':{'text_offset':offset,'image_size':declared_size,'flags':flags,
                                   'file_size':len(raw),'copy_start_offset':symbols['_stub_end']-TEXT},
            'candidate_dt_audit':dt_audit,
            'kernel':kr,'initramfs_manifest':str(init/'result.json'),
            'initial_abl_source_and_stub_overlap':'RUNTIME_GUARD_REJECTS_LIVE_STUB_OVERWRITE',
            'physical_entry':'NOT_ADMITTED_H0_ONLY',
            'device_actions':0}
    if marked:
        result['retained_marker']=dict(config=marker_source['config'],kernel_source=marked,
            source_sha256=digest(HERE/'retained-marker.S'),codec_sha256=digest(HERE/'retained_marker.py'))
    require(('entry_park' in kr)==bool(marker_source and 'entry_park' in marker_source),
            'entry-park declaration omitted')
    if 'entry_park' in kr:
        import entry_park
        result['entry_park']=kr['entry_park']
        entry_park.linked(result)
    (output/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'status':result['status'],'loader_bytes':blob.stat().st_size,'fixed_reservation_overlap':False}))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['base','prepared','init','output']:p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--reuse',action='store_true',help='qualify an existing successful H0 build; no rebuild')
    p.add_argument('--kernel-label',default='kernel-1')
    a=p.parse_args();build(a.base,a.prepared,a.init,a.output,a.reuse,a.kernel_label)
